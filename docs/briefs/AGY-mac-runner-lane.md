# Brief: let the Mac spawn an `agy` worker (Mac runner lane)

## What this is
This repo is a task orchestrator. `runners/worker_init.py` claims a task and starts a worker
in its git worktree. Today it only starts `claude`; for any other runner it marks the task
failed (see the block starting `runner = (task.get("runner") or "claude")` in `main()`).
Goal: when `runner == "agy"`, run the Antigravity CLI (`agy`) headless in the task's worktree,
then commit what it changed and hand the task to review. `codex` stays refused on the Mac
(it is not signed in here) with a clear message.

Finished means: the code below exists, the new test file exists, nothing else changed.

## Work ONLY in this worktree
`/Users/gob/MoonieXHQ/Agents/Core/worktrees/runner-lanes-mac`. Do not touch any other folder.
Use your file-editing tool. Do not try to run shell commands (they are blocked in this mode).

## Read these first
| path | why |
|---|---|
| `runners/worker_init.py` (functions `main`, `_build_prompt`) | where the refusal is and how the prompt/role doc are built |
| `lib/db.py` function `update_status(task_id, status, *, actor, force, **fields)` | the only way to change task status; extra fields are column names like `report`, `pid` |
| `config/hosts.yaml` host `mac` | `runners:` list gates which runners the Mac may spawn |
| `docs/ops/agent-runners.md` §6 and §6b | how agy is invoked headless and why it is edit-only |
| `tests/test_runner_workdir_dest.py` | example of the test style used here (pytest) |

## Changes
1. **New file `runners/agy_local.py`** with one public function
   `run_agy_task(task: dict, worktree: str, prompt: str, role: str) -> int` that:
   - finds the binary: env `AGY_BIN`, else `~/.local/bin/agy`, else `agy` on PATH;
   - appends this contract to the prompt: "You can only edit files. Do not run shell
     commands. Work only inside <worktree>. When finished, write REPORT.md at the worktree
     root with three headings: Files changed, What was done, Blockers.";
   - runs `[agy, "-p", prompt, "--mode", "accept-edits", "--add-dir", worktree]` with
     `cwd=worktree`, `stdin=subprocess.DEVNULL`, stdout+stderr appended to
     `<worktree>/.agy-run.log`, timeout 3600 s;
   - records its own pid first: `db.update_status(task_id, "in_progress", pid=os.getpid(), actor=role)`;
   - NEVER trusts agy's exit code alone. After agy returns, run `git -C <worktree> add -A`,
     then `git -C <worktree> reset -q -- .agy-run.log` (the log must never be committed),
     then `git -C <worktree> diff --cached --quiet`. Nothing staged →
     `update_status(task_id, "failed", report="agy produced no file changes (exit N)" + last 40 log lines, actor=role)`
     and return 6.
   - otherwise commit with
     `git -C <worktree> -c user.name=agy-worker -c user.email=agy-worker@localhost commit -q -m "agy(<task_id>): <task title>"`,
     then `update_status(task_id, "review", report=<REPORT.md text or "(no REPORT.md)"> + "\n\n--- agy log tail ---\n" + <last 40 log lines>, actor=role)`
     and return 0.
   - Keep subprocess calls in small helpers so tests can monkeypatch them.
2. **`runners/worker_init.py` `main()`**: replace the single `if runner != "claude":` refusal with:
   - `runner == "agy"` → build the same prompt the claude path builds (`_build_prompt` +
     the role doc text that `main()` already reads), then `sys.exit(agy_local.run_agy_task(...))`.
     Place this AFTER the project/role doc are loaded but BEFORE any claude-specific exec.
   - `runner == "codex"` → keep failing, report text: `runner='codex' not signed in on the Mac — use host contabo`.
   - any other non-claude runner → keep today's failure.
   Update the comment above the block so it no longer says "winbox-only".
3. **`config/hosts.yaml`** host `mac`: `runners: [claude, agy]`, and update its comment to say
   agy is wired via `runners/agy_local.py` (2026-09-29).
4. **New test `tests/test_agy_local.py`** (pytest, no network, no real agy):
   - use `tmp_path` to create a git repo as the "worktree";
   - fake agy = a small executable script written into `tmp_path` that creates a file, pointed
     to by `AGY_BIN`;
   - monkeypatch the `update_status` that `runners.agy_local` uses, to record calls;
   - case 1: fake agy writes a file + REPORT.md → return 0, one commit exists, last status "review";
   - case 2: fake agy writes nothing and exits 0 → return 6, last status "failed", no commit;
   - case 3: `.agy-run.log` is never in the commit.

## Traps already paid for
- agy exits 0 in some failure modes; the git diff is the only proof of work.
- agy print mode cannot run shell; that is why the Python side commits.
- Never use `--dangerously-skip-permissions`.

## Report
Write `REPORT.md` at the worktree root: Files changed / What was done / Blockers.
Do not edit any file not listed above.
