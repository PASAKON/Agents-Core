# task-df0541aa — research-gate + cwd-guard hooks

## Summary
Built two PreToolUse hooks per ADR 0028 §6: `hook-research-gate.py` blocks
WebSearch/WebFetch until the session has checked `Agents/Wikis/research/`,
and `hook-cwd-guard.py` simulates a Bash command's cwd and blocks anything
that would leave the session's home directory. Both registered in
`.claude/settings.json`, documented, and covered by 33 new tests.

## Files Changed
- `scripts/hook-research-gate.py` — new. Blocks WebSearch/WebFetch while
  unarmed; arms a 12h `~/.gateguard/research-gate-<session>.ok` marker on
  `mcp__org__wiki_search`, a Read/Grep of a `research/`-containing path, or
  a Bash command mentioning `research/`/`RESEARCH-INDEX`. `RESEARCH_GATE=off`
  escape hatch; fails open on bad/missing input.
- `scripts/hook-cwd-guard.py` — new. Tokenizes a Bash command into top-level
  segments (splitting on `;`, `&&`, `||`, `|`, newlines; ignoring quotes,
  `(...)`/`$(...)` depth, and heredoc bodies), simulates `cd`/`pushd`/`popd`/
  `cd -` against `$CLAUDE_PROJECT_DIR` (fallback: event `cwd`), and blocks
  (exit 2) if the simulated end isn't home or is UNKNOWN (variable in path).
  `CWD_GUARD=off` escape hatch; fails open on non-JSON/no-command/no-home.
- `scripts/test_hook_research_gate.py` — new, 15 tests.
- `scripts/test_hook_cwd_guard.py` — new, 18 tests (all 4 BLOCK + all 9
  ALLOW cases named in the brief, plus escape-hatch/fail-open/message-shape).
- `.claude/settings.json` — two new PreToolUse entries (matchers per brief).
  Valid JSON confirmed with `python3 -c "import json; json.load(...)"`.
- `docs/ops/hooks-research-gate-cwd-guard.md` — new, 48 lines (≤ 60 limit).

No other file touched. No skill edited.

## Commits
- 853f3370 — hooks: research-gate + cwd-guard PreToolUse hooks (ADR 0028 §6)

## Tests
- ran: `pytest scripts/test_hook_research_gate.py scripts/test_hook_cwd_guard.py -v`
- passed: 33 (15 research-gate, 18 cwd-guard)
- failed: 0
- skipped: 0

Full existing suite after registration, run in the FOREGROUND (synchronous,
no backgrounding) inside this worktree:
```
$ /Users/gob/Projects/Agents/.venv/bin/python3 -m pytest scripts/ -x \
    --ignore=scripts/test_skill_doctrine_lint.py \
    --deselect scripts/test_install_claude_home.py::test_fresh_install_links_every_entry_and_check_is_then_clean \
    --deselect scripts/test_install_claude_home.py::test_install_captures_a_differing_real_file_into_the_repo_then_links \
    --deselect scripts/test_install_claude_home.py::test_install_is_idempotent \
    -p no:warnings
...
1180 passed, 3 skipped, 3 deselected in 50.34s
```
- passed: 1180
- failed: 0
- skipped: 3
- deselected: 3 (the pre-existing `test_install_claude_home.py` failures
  below, plus the brief's own excluded `test_skill_doctrine_lint.py`)

The 3 deselected `test_install_claude_home.py` cases all fail on a shared
root cause unrelated to this change: a missing 210MB
`reel-editor-th/assets/mooniex-broll` Drive asset that ADR 0027's installer
expects but this worktree doesn't have on disk. Confirmed via `git log` that
the installer/its test were last touched in `0918dcd5`, before this task
started — my diff never touches `scripts/install-claude-home.sh` or its
test. The very first `pytest scripts/ -q -x --ignore=...doctrine_lint.py`
run (exactly the acceptance command) stopped at the first of these three
for the same reason, before this rerun deselected all three to show the
rest is fully green.

## Hand-run transcripts

research-gate, unarmed WebSearch:
```
$ echo '{"session_id":"hand-1","tool_name":"WebSearch","tool_input":{"query":"seedance prices"}}' | python3 scripts/hook-research-gate.py
BLOCKED — research cache rule (ADR 0028 §6): check the cache before any web search.
First: mcp__org__wiki_search (namespace mooniex:) on `research/`, or Read research/RESEARCH-INDEX.md. A fresh hit (refresh_after in the future) answers it — no web search needed.
After you do web search: WRITE the answer as a research file per research/README.md (one question, one file, frontmatter incl. refresh_after). Then retry this exact call.
exit=2
```

research-gate, armed via wiki_search then allowed:
```
$ echo '{"session_id":"hand-1","tool_name":"mcp__org__wiki_search","tool_input":{"query":"seedance prices"}}' | python3 scripts/hook-research-gate.py
exit=0
$ echo '{"session_id":"hand-1","tool_name":"WebSearch","tool_input":{"query":"seedance prices"}}' | python3 scripts/hook-research-gate.py
exit=0
```

cwd-guard, blocked (compound cd leaves session elsewhere):
```
$ echo '{"tool_name":"Bash","tool_input":{"command":"cd /a && x; cd /b && y"},"cwd":"'"$PWD"'"}' | CLAUDE_PROJECT_DIR="$PWD" python3 scripts/hook-cwd-guard.py
BLOCKED — this command would leave the session in /b (home is /Users/gob/Projects/Agents/worktrees/mooniex-agents__developer__task-df0541aa).
Every later call in this session runs there, not in the repo you expect (measured 5x on 2026-09-22).
Use `git -C <path> ...`, absolute paths, a subshell `(cd X && ...)`, or end the command with `&& cd /Users/gob/Projects/Agents/worktrees/mooniex-agents__developer__task-df0541aa`.
exit=2
```

cwd-guard, allowed (no cd, stays home):
```
$ echo '{"tool_name":"Bash","tool_input":{"command":"pytest scripts/ -q"},"cwd":"'"$PWD"'"}' | CLAUDE_PROJECT_DIR="$PWD" python3 scripts/hook-cwd-guard.py
exit=0
```

## Issues / Blockers
- (none)

## Notes for Reviewer
- Earlier in this session I ran the full suite via `run_in_background`
  (the Bash tool auto-backgrounds after its 120s foreground cap) and got
  identical counts (1180/3/3/0) from those runs. The CTO flagged that no
  pytest process was visible on the machine and asked for a synchronous
  foreground run — that's because those background runs had already
  finished (the suite takes ~50s, well under both the 120s cap and by the
  time the CTO checked), not because they were fake. This report's numbers
  are from the foreground rerun above, done after that message.
- `pytest.ini`'s `addopts` already carries `-q`; passing `-q` again on the
  CLI doubles to `-qq`, which silently drops pytest's final summary line
  (no effect on pass/fail — just no human-readable count printed). Cost
  ~10 min chasing a phantom truncation before finding this. Avoided in the
  final runs above by using `-p no:warnings` instead of a second `-q`.

## Skill learning
- MISSING [dev-spawn-protocol §none] : no skill/doc flags that this repo's `pytest.ini` addopts already injects `-q`, so a worker's own `-q` silently becomes `-qq` and drops the final pass/fail summary line (reads like a hang/truncation) · evidence: task-df0541aa, compare /tmp/p3.log (no summary, `-q -q`) vs the foreground run above (summary present, no extra `-q`)
- (none) beyond the above — precedent files (`hook-gdrive-skill-gate.py`, `test_hook_skill_log.py`, `test_hook_inbox.py`) matched this task exactly as described, no SKILL-OVERRIDE needed.
