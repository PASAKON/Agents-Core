# Agent runners — who can be driven headless, from where

Measured 2026-09-20. Rerun the probes in §5 before trusting this table; auth
expires and installs drift.

## 1. The table

| runner | headless invocation | installed on | auth state | verdict |
|---|---|---|---|---|
| `claude` | `claude -p` / positional prompt | Mac ✅, winbox ✅ (`%USERPROFILE%\.local\bin\claude.exe`) | signed in both | **working** — this is what `windows/spawn-worker.ps1` drives |
| `codex` (codex-cli 0.153.4) | `codex exec [PROMPT]` | **winbox only** (`%APPDATA%\npm\codex.cmd`) — NOT on the Mac | `Logged in using ChatGPT` | **model runs; file/shell tools blocked over SSH** — see §3 |
| `agy` (Antigravity CLI 1.2.6) | `agy -p --output-format json` | **Mac only** (`~/.local/bin/agy`) — NOT on winbox | ❌ OAuth never completed | blocked — see `antigravity-cli-test.md` |
| Antigravity **IDE** | none (GUI) | winbox (`%LOCALAPPDATA%\Programs\antigravity`) | — | no CLI surface; install `agy` there instead of automating the GUI |

Useful `codex exec` flags (verified present): `-s {read-only,workspace-write,danger-full-access}`,
`-C <dir>`, `--skip-git-repo-check`, `--json` (JSONL events), `-o <file>`
(final message to a file), `resume <id> | --last`, `fork`.

Session continuation, all three: `codex exec resume <id>` / `agy --conversation <ID>` /
`claude -p --resume <id>`. **A session id is an OUTPUT of a run, not an input you
must prepare.** Nothing needs to "create a session" before dispatch.

## 2. Two things that are NOT true, however plausible they sound

- **"Codex is a desktop GUI app with an Active button."** It is a Node CLI. There
  is no window, no session template under `AppData` to clone, and no
  `--load_session` flag. Any plan built on injecting a template file or clicking
  a button is solving a problem that does not exist.
- **"Antigravity can only be driven through its IDE."** It ships `agy`, a headless
  CLI with `-p`, JSON output and `--dangerously-skip-permissions`. The blocker is
  one interactive Google OAuth, not the absence of an interface.

## 3. The session-0 trap (why `codex exec` fails over SSH)

Running `codex exec -s workspace-write` on winbox **over `ssh`**:

```
tokens used 11,940                                    <- auth fine, model ran
ERROR codex_core::tools::router: error=exec_command failed:
  CreateProcess { message: "Rejected(\"Failed to create unified exec process:
  timed out after 15000ms connecting runner pipe-in\")" }
ERROR ... windows sandbox failed: timed out after 15000ms connecting runner pipe-in
codex: "Unable to create PONG.txt because the workspace file runner repeatedly timed out."
ssh exit code: 0
```

Same root cause `windows/spawn-worker.ps1:317` already documents for `claude.exe`
(2026-09-07, task-1289db7b): **a process started from an SSH shell lives in
Windows session 0 and never reaches the logged-in desktop (session 1).** Codex's
sandbox helper cannot connect its named pipe across that boundary.

**The fix is not `--dangerously-bypass-approvals-and-sandbox`.** It is the channel
the repo already uses: a one-shot scheduled task with `LogonType Interactive`
running as the desktop user (`New-ScheduledTaskPrincipal -LogonType Interactive`).
A Codex adapter reuses that launcher rather than inventing one.

## 4. 🔴 `codex exec` returns exit 0 after total failure

Every file write failed, the agent said so in plain English, and the process
still exited **0**. Never gate a Codex run on its exit code. Gate on the
artefact: the file exists, the test is green, the commit landed. This is the
"report outcome not intent" rule with a concrete instance attached.

## 5. Probes to re-run

```bash
# which binaries exist, and where
ssh winbox 'cd C:\Users\UsEr && where.exe codex & where.exe agy & where.exe claude'
command -v claude agy codex

# codex auth (prints "Logged in using ChatGPT" when good)
ssh winbox 'cd C:\Users\UsEr && codex.cmd login status'

# round-trip — expect this to FAIL over plain ssh until the adapter uses
# an interactive scheduled task (see §3)
ssh winbox 'cd C:\mooniex\codex-probe && codex.cmd exec --skip-git-repo-check \
  -s workspace-write -C C:\mooniex\codex-probe "Create PONG.txt containing PONG."'
ssh winbox 'cd C:\mooniex\codex-probe && dir /b'      # the only honest check
```

macOS has no `timeout`/`gtimeout`; bound long probes with
`perl -e 'alarm N; exec @ARGV' -- <cmd>`.

## Related

`delegate-external-agent` skill (the brief contract and the review discipline),
`docs/ops/antigravity-cli-test.md` (the `agy` OAuth block in full),
`windows/spawn-worker.ps1` (the interactive-scheduled-task launcher),
IRON-RULES §42/§53 (repeated GUI work is a script, not a model).
