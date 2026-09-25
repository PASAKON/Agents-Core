# RTK A/B (task-9ea68924)

Measures whether [rtk-ai/rtk](https://github.com/rtk-ai/rtk) v0.50.0 (PreToolUse
Bash-rewrite hook) is worth adopting org-wide. Decision rule (CEO-approved plan
2026-09-25): **ADOPT** if arm B (RTK) uses ≤ 0.8× arm A's total tokens (cache
read + cache write + fresh input + output, deduped by `message.id`) with equal
graded correctness on ≥ 2 of 3 paired runs. Full writeup + verdict:
`docs/ops/rtk-ab-2026-09-25.md`.

## Layout

- `PROMPT.md` — the one read-only, Bash-heavy job both arms run (10 questions:
  pytest counts, a commit-subject grep, file-size/`find`/`grep`/`ls -R` facts,
  a `git show --stat` fact). Identical text for both arms.
- `ANSWER_KEY.json` — the 10 answers, computed by plain shell against the
  fixture commit before any run (`commands_used` shows exactly how).
- `grade.py <result-file>` — finds the last JSON-object line in a run's output
  and scores it against `ANSWER_KEY.json`, out of 10 (q1's passed/failed/skipped
  count as one question).
- `run_ab.py` — drives `claude -p` against the two arm checkouts.
  - `--smoke`: 1 run each (A then B) — sanity check before spending the budget.
  - `--measured`: 3 runs each, alternating start order (`i=1`: A,B · `i=2`:
    B,A · `i=3`: A,B) — 6 headless calls.
  - Saves each run's `--output-format json` result + stdout to
    `results/<arm>-<i>.json`.
- `arms/A/`, `arms/B/` — **gitignored.** `git worktree add --detach` checkouts
  of the fixture commit, `git sparse-checkout` cone-mode to `tools scripts
  tests lib .claude` (full checkout is 916 MB; sparse is ~11 MB per arm).
  `.claude` is kept in **both** arms so the project's own PreToolUse hooks
  (cwd-guard, self-repo-guard, gdrive-skill-gate, research-gate) apply
  identically — only arm B additionally gets an RTK hook, so the hook is the
  only delta between arms.
- `bin/rtk` — **gitignored.** The v0.50.0 macOS-arm64 release binary,
  checksum-verified against `checksums.txt` from the GitHub release (not
  `brew install` — see "Install" below).

## Install (what was actually done here)

```bash
gh release download v0.50.0 --repo rtk-ai/rtk \
  --pattern 'rtk-aarch64-apple-darwin.tar.gz' --pattern 'checksums.txt' --dir /tmp/rtk_dl
shasum -a 256 -c <(grep darwin /tmp/rtk_dl/checksums.txt | grep aarch64)   # verify
tar -xzf /tmp/rtk_dl/rtk-aarch64-apple-darwin.tar.gz -C /tmp/rtk_dl
cp /tmp/rtk_dl/rtk tools/rtk_ab/bin/rtk && chmod +x tools/rtk_ab/bin/rtk
```

`rtk` is also in homebrew-core at the exact required version (`brew info rtk`
→ stable 0.50.0) — a legitimate fallback if `gh release download` isn't
available — but a local binary avoids any change to global brew state.
**Never `rtk init -g` and never edit `~/.claude/*`** (hard rule) — see "Hook
wiring" below for why that's not actually needed.

## Hook wiring

`rtk init` (no `-g`) for the default "claude" agent only writes `CLAUDE.md`
prose instructions + a `.rtk/filters.toml` template — **no PreToolUse hook**.
Per RTK's own README platform table, the real interception (`PreToolUse hook
(native binary)`) is only wired by `rtk init -g`, which is forbidden here
(global, touches `~/.claude/settings.json`). Solution: Claude Code's hook
schema is agent-agnostic and project-scoped hooks work the same whether
written by `rtk init -g` or by hand, so the hook JSON was hand-verified against
`rtk hook claude`'s actual stdin/stdout contract (confirmed working, see
below) and placed directly in **arm B's own** `.claude/settings.local.json`
(never touched in arm A, never touched at the real repo root, never global):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "<abs-path-to-worktree>/tools/rtk_ab/bin/rtk hook claude"
          }
        ]
      }
    ]
  }
}
```

Verified directly against a simulated PreToolUse payload:

```bash
$ echo '{"session_id":"test","cwd":"'"$PWD"'","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git log --oneline -30","description":"log"}}' | tools/rtk_ab/bin/rtk hook claude
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecisionReason":"RTK auto-rewrite","updatedInput":{"command":"rtk git log --oneline -30","description":"log"}}}
```

stdout is clean JSON (no stray warning lines mixed in — verified with stdout/
stderr captured separately). A command RTK doesn't recognize (a `python -m
pytest ...` invocation, any piped/compound command like `find ... | wc -l`)
produces **empty stdout** — Claude Code's convention for "no hook output = run
the original command unchanged." This matches the survey's prediction almost
exactly: RTK only rewrites simple, single, recognized command forms; most of
this org's Bash is python heredocs / piped filters it will never touch.

**Bug found by the smoke run, fixed before the measured runs:** RTK's rewrite
hardcodes the bare literal `rtk` (not its own install path) as the new
command's argv[0]. Since `tools/rtk_ab/bin` isn't on the default `PATH`, every
rewritten command in the first B smoke run failed `exit 127: command not
found: rtk` — the tested agent didn't see an error message about RTK, just a
command that mysteriously failed, and burned many extra turns working around
it (falling back to `/bin/ls`, redirecting `wc -l` output to a file to dodge
the rewrite, etc. — see `docs/ops/rtk-ab-2026-09-25.md` for the full trace).
Fix: `run_ab.py` prepends `tools/rtk_ab/bin` to the child `claude` process's
`PATH` for every run (harmless no-op for arm A, which never invokes `rtk`).
This mirrors RTK's own README: "Installs to `~/.local/bin`. Add to PATH if
needed."

## Running it

```bash
# one-time setup (see Install above), then:
python3 tools/rtk_ab/run_ab.py --smoke      # 1 run each, sanity check
python3 tools/rtk_ab/run_ab.py --measured   # 3 runs each, alternating order

# grade a run:
python3 -c "import json; d=json.load(open('tools/rtk_ab/results/A-1.json')); print(d['claude_result']['result'])" > /tmp/r.txt
python3 tools/rtk_ab/grade.py /tmp/r.txt

# per-run token measurement (dedup by message.id, imports tools/token_profile.py):
python3 - <<'PY'
import sys, json
sys.path.insert(0, 'tools')
from token_profile import scan
sid = json.load(open('tools/rtk_ab/results/A-1.json'))['claude_result']['session_id']
# transcript lives at ~/.claude/projects/<slug-of-arm-dir>/<sid>.jsonl
PY
```

## Cleanup

```bash
git worktree remove --force tools/rtk_ab/arms/A
git worktree remove --force tools/rtk_ab/arms/B
```

`bin/rtk` is left in place (gitignored, 4 MB, no state) for reproducibility;
delete it too if reclaiming the disk fully.
