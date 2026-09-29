# Brief: let Contabo (Linux) spawn codex and agy workers

## What this is
`scripts/spawn-worker-remote.sh` starts a worker on the Linux VPS "contabo" inside tmux.
Today it refuses any runner except claude (`if [ "$RUNNER" != "claude" ]`). The Windows
launcher `windows/spawn-worker.ps1` already supports `-Runner codex|agy` — port that logic
to the Linux launcher. On contabo both CLIs are installed and signed in:
`/usr/bin/codex` (codex-cli 0.155.1, "Logged in using ChatGPT") and `/root/.local/bin/agy` (1.2.12).

Finished = the changes below + tests; nothing else changed.

## Work ONLY in this worktree
`/Users/gob/MoonieXHQ/Agents/Core/worktrees/contabo-lane`. File-editing tool only; do not run shell.

## Read these first
| path | why |
|---|---|
| `scripts/spawn-worker-remote.sh` (whole file) | the launcher to change; keep the claude path byte-identical |
| `windows/spawn-worker.ps1` — the `elseif ($Runner -eq 'codex')` branch and the agy branch (search "§6b: THE HUB commits and pushes") | the exact argv and the rule that the launcher (hub), not agy, commits and pushes |
| `docs/ops/agent-runners.md` §1, §4, §6b | codex exits 0 after failure; agy is edit-only |
| `tools/delegate.py` `_render_remote_runner_args`, `gate_codex_turn_completed` | what the hub passes and how codex output is judged |
| `runners/branch_poller.py` `_codex_transcript_remote_path` | WHERE the poller expects the codex JSONL transcript on the remote host — write it exactly there |
| `tests/test_spawn_worker_ps1_runners.py` | test style for runner launchers |

## Changes
1. `scripts/spawn-worker-remote.sh`:
   - accept `--runner claude|codex|agy`; anything else keeps the current refusal.
   - codex launch line (inside the generated launch.sh, in the worktree):
     `codex exec "$(cat TASK.md)" -C "$WT" -s workspace-write --skip-git-repo-check --json -o <final-msg file> > <transcript path the poller reads> 2>&1`
     then the same commit+push step the claude remote contract uses if codex left changes
     (codex may also commit itself; handle both: only commit when `git status --porcelain` is non-empty).
   - agy launch line: `/root/.local/bin/agy -p "$(cat TASK.md)" --model gemini-3.8-flash-high --mode accept-edits --add-dir "$WT" < /dev/null >> <log> 2>&1`,
     then THE LAUNCHER does `git add -A`, excludes the log and REPORT.md, commits as `agy-worker`, pushes the branch.
   - Never gate on the CLI's exit code; the branch on origin + artefact gate decide.
   - `--dry-run` must print the runner's command line.
2. `config/hosts.yaml` host `contabo`: `runners: [claude, codex, agy]`; update the comment
   (2026-09-29, CLIs verified on the box).
3. Update `docs/ops/agent-runners.md` §1 table: winbox = codex/agy LOST in the 2026-09-29 reset
   (needs reinstall + sign-in on the desktop); Mac = agy wired (`runners/agy_local.py`), codex not signed in;
   contabo = codex + agy wired via `scripts/spawn-worker-remote.sh`.
4. Tests (new file `tests/test_spawn_worker_remote_runners.py`): run the script with `--dry-run`
   through `subprocess` for each runner and assert the printed command; an unknown runner still exits
   non-zero; the claude dry-run output is unchanged from today (compare to the fixed strings you read).
   Update any existing test that asserts contabo is claude-only.

## Traps already paid for
- codex `exec` exits 0 after doing nothing (§4). agy cannot run shell (§6b).
- Never add `--dangerously-bypass-approvals-and-sandbox` or `--dangerously-skip-permissions`.

## Report
`REPORT.md` at worktree root: Files changed / What was done / Blockers.
