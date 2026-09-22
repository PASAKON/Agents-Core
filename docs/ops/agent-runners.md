# Agent runners — who can be driven headless, from where

Measured 2026-09-20. Rerun the probes in §5 before trusting this table; auth
expires and installs drift.

## 1. The table

| runner | headless invocation | installed on | auth state | verdict |
|---|---|---|---|---|
| `claude` | `claude -p` / positional prompt | Mac ✅, winbox ✅ (`%USERPROFILE%\.local\bin\claude.exe`) | signed in both | **working** — this is what `windows/spawn-worker.ps1` drives |
| `codex` (codex-cli 0.153.4) | `codex exec [PROMPT]` | **winbox only** (`%APPDATA%\npm\codex.cmd`) — NOT on the Mac | `Logged in using ChatGPT` | **model runs; file/shell tools blocked over SSH** — see §3 |
| `agy` (Antigravity CLI 1.2.6) | `agy -p "<prompt>" --mode accept-edits --add-dir <dir> < /dev/null` | **Mac only** (`~/.local/bin/agy`) — NOT on winbox | ✅ signed in 2026-09-20 on the Ultra account | **WORKING — writes files headless, no API key** — see §6 |
| Antigravity **IDE** | none (GUI) | winbox (`%LOCALAPPDATA%\Programs\antigravity`) | — | no CLI surface; install `agy` there instead of automating the GUI |

Codex `mcp-server` is a dead end: deprecated in v0.149.1, **removed in v0.154.0**
(PR #42993). It still exists on winbox's 0.153.4 and is gone from the Mac's
0.154.0 — verified side by side. Never build on it. Codex is an MCP **client**
only; the supported route into Claude Code is the official `openai/codex-plugin-cc`
plugin, or shelling out to `codex exec`.

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

**This is an open upstream bug, not our misconfiguration**: `openai/codex#43327`
(2026-09-07, no maintainer response), plus `#22834` and `#7466` in the same
family. There is no config key that fixes it — `--disable unified_exec` was
tried and failed identically (2026-09-20).

The one clue that narrows it: `LAST.txt` (written by the CLI itself via `-o`)
**does** land, while every file the sandboxed tool runner tries to write does
not. So it is not permissions, not the path, and not Defender blocking
`codex.exe` — it is specifically the sandbox helper failing to spawn a process.

**The fix is not `--dangerously-bypass-approvals-and-sandbox`.** It is the channel
the repo already uses: a one-shot scheduled task with `LogonType Interactive`
running as the desktop user (`New-ScheduledTaskPrincipal -LogonType Interactive`).
A Codex adapter reuses that launcher rather than inventing one.

**Proven 2026-09-20.** The identical `codex exec` that writes nothing over ssh,
launched instead through an interactive scheduled task as
`DESKTOP-3NQB2QO\UsEr`:

```
type PONG3.txt   ->  SESSION1-OK
s1.log           ->  +++ b/PONG3.txt / +SESSION1-OK      (codex's own diff)
                     tokens used 6,390
```

So session 0 is the cause, full stop — not Defender (its exclusions are empty
and its event log shows no codex block in 24 h), not `unified_exec`, not config.
`#43327`'s reporter asked for a fix that avoids "Desktop switching"; switching to
the desktop is exactly what works, and this repo already has the mechanism.

Footnote worth keeping: on that successful run the wrapper's trailing
`EXITCODE=` line never made it into the log. The artefact was the only honest
signal in both directions — failure *and* success. Gate on it.

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

## 6. `agy` on the Ultra subscription, headless — PROVEN 2026-09-20

The thing `antigravity-cli-test.md` could not settle. Three measured steps:

```
agy -p "Reply with exactly: PONG-AGY" < /dev/null   →  PONG-AGY   exit 0
agy models < /dev/null                              →  full list (see below)
agy -p "<create a file>" --mode accept-edits --add-dir <dir> < /dev/null
                                                    →  file on disk, exact content
```

No TTY, no human, stdin closed, **no `GEMINI_API_KEY`, no separate billing, no
`--dangerously-skip-permissions`.** The session persists after one sign-in.

**Getting signed in is the only human step, and it has exactly one working
shape.** The OAuth URL carries a PKCE challenge bound to *that process*, the
auto-callback window is 60 s, and the fallback is pasting a code into the same
process's stdin. So:

| route | result |
|---|---|
| Claude runs `agy`, user pastes the code into chat | ✗ the sandbox refuses any command carrying a credential-shaped string; chat is not connected to that process's stdin |
| `! agy -p …` from inside Claude Code | ✗ `!` runs to completion, it is not an interactive stdin — always times out at 60 s |
| **a real Terminal window** | ✅ `osascript -e 'tell application "Terminal" to do script "agy -p \"…\""'`, then the user pastes the code there |

Opening the OAuth URL in the user's Chrome for them (`navigate` + one screenshot)
removes the copy/paste race; **let the user click the consent button** — granting
OAuth consent is theirs, not ours.

**Models reachable through the subscription** (`agy models`, 2026-09-20):
`gemini-3.8-flash` (high/medium/low), `gemini-3.7-flash`, `gemini-3.6-flash`,
`gemini-3.1-pro` (high/low), **`claude-sonnet-4-6`**, **`claude-opus-4-6-thinking`**,
`gpt-oss-120b-medium`. The two Claude models here do **not** draw on the
Anthropic quota.

**Permissions**: the default is `toolPermission=request-review`, and in print
mode a `RunCommand` step is soft-denied with
`no output produced — a tool required the "command" permission`. `--mode
accept-edits` covers the *edit* tools but not shell. Prefer steering the prompt
at the file-editing tool ("use your file-editing tool, not a shell command") over
loosening permissions; if shell is genuinely needed, add a narrow
`permissions.allow` entry (`command(<target>)`) rather than
`--dangerously-skip-permissions`.

**Failure signalling beats Codex's**: `agy` exits non-zero and prints the reason
(v1.2.6 added `AGY_ERROR` JSON on stderr and exit 3). Codex exits 0 — see §4.

### 6a. On Windows, `agy`'s sign-in is session-scoped (2026-09-22)

`agy.exe` installed on winbox from `https://antigravity.google/cli/install.ps1`
(download and inspect it, then run the file — the classifier refuses a raw
`irm … | iex`). It lands in `%LOCALAPPDATA%\agy\bin` and updates the user PATH
registry.

Two facts that will otherwise waste an hour:

- **The CLI does not inherit the Antigravity IDE's sign-in.** The IDE was logged
  in on that box the whole time; `agy models` still said "Please sign in". Each
  binary signs in for itself.
- **After signing in, `agy models` succeeds in session 1 and still says
  "Please sign in" over `ssh`.** The credential lives in the logon session's
  keyring, which session 0 cannot read. So the screen saying
  `AGY IS SIGNED IN` and ssh saying otherwise are *both* true — check it the way
  you will actually run it, through `windows/s1probe.ps1`, not over ssh.

This is the same session-0 boundary as §3, reached through auth instead of a
sandbox pipe. Every runner on that box goes through session 1; nothing changes
in the launcher.

**Signing in without a race**: put a loop in the .cmd — `agy models` as the
success probe, otherwise print a fresh OAuth URL and wait — and launch it with
`s1probe.ps1 -Cmd "start cmd /k …"` so it is a visible, persistent window on the
desktop. The user reads the URL there, approves, and pastes the code into that
same window. An expired URL is simply replaced by the next loop, which removes
the 60 s clock the earlier attempts kept losing to.

## Related

`delegate-external-agent` skill (the brief contract and the review discipline),
`docs/ops/antigravity-cli-test.md` (the `agy` OAuth block in full),
`windows/spawn-worker.ps1` (the interactive-scheduled-task launcher),
IRON-RULES §42/§53 (repeated GUI work is a script, not a model).
