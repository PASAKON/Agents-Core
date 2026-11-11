# CLI logins from a phone

Review/deploy tools/cli_login.py to the normal Core checkout on each host before
running these cards. Python 3.11 and the CLI must be installed. This helper uses
POSIX PTYs on Linux/macOS and native ConPTY via ctypes on Windows 10 1809+.
No packages are required. Windows ConPTY still needs on-host acceptance testing.

## Status and login

`python3 tools/cli_login.py status --json` prints only CLI name, yes/no, credential
path, Unix mtime and a fixed reason. Exit status is 1 if any CLI is no; use
`--cli codex` to check one. Claude uses `claude auth status` JSON, Codex uses
`codex login status`. AGY requires a nonempty token file and a successful
`agy models` listing; this makes no model call. It suppresses all raw output.

The login helper emits one physical `OPEN: <url>` line (a phone may visually wrap
it) and, for Codex, `CODE: <device-code>`. Open the link on the phone. Paste the
Claude/AGY authorization code into the card input once. For Codex, enter its code
on the website; no card input is needed. The helper suppresses other CLI output,
including echoed input and account identity. It selects AGY's Google menu with
Enter. Completion requires the CLI's status check to return yes. The helper has
an approximately 1700-second login deadline inside the 1800-second card timeout.

### Exact login cards

Run the following commands from the deployed Core checkout on Contabo. They
create cards only; approving the card starts the login. No cards were raised by
this implementation task. The Winbox cards use Contabo's Run token and SSH.
The Mac cards execute on the Mac peer, not through its restricted inbound SSH.

**contabo**

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Refresh claude login on contabo" --expected "claude status yes" --command '/opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/tools/cli_login.py login claude'
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Refresh codex login on contabo" --expected "codex status yes" --command '/opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/tools/cli_login.py login codex'
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Refresh agy login on contabo" --expected "agy status yes" --command '/opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/tools/cli_login.py login agy'
```

**mac**

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host mac --expects-input --risk amber --timeout 1800 --why "Refresh claude login on mac" --expected "claude status yes" --command '/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/cli_login.py login claude'
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host mac --expects-input --risk amber --timeout 1800 --why "Refresh codex login on mac" --expected "codex status yes" --command '/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/cli_login.py login codex'
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host mac --expects-input --risk amber --timeout 1800 --why "Refresh agy login on mac" --expected "agy status yes" --command '/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/cli_login.py login agy'
```

**winbox**

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Refresh claude login on winbox" --expected "claude status yes" --command 'ssh -t winbox python C:/Users/passg/mooniex/repo/MoonieX-Agents/tools/cli_login.py login claude'
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Refresh codex login on winbox" --expected "codex status yes" --command 'ssh -t winbox python C:/Users/passg/mooniex/repo/MoonieX-Agents/tools/cli_login.py login codex'
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Refresh agy login on winbox" --expected "agy status yes" --command 'ssh -t winbox python C:/Users/passg/mooniex/repo/MoonieX-Agents/tools/cli_login.py login agy'
```

The Winbox AGY card is a documented acceptance command, **not a verified working
login**: repository evidence says its auth is stored in the session-1 keyring,
not the Linux token location. A session-0 SSH login may not authenticate workers
in session 1. See the blockers below before deploying that card.

## Credential locations and storage limits

| CLI | Linux | Windows (user passg) | Mac |
|---|---|---|---|
| Codex | ~/.codex/auth.json | C:\\Users\\passg\\.codex\\auth.json | ~/.codex/auth.json when file storage is configured |
| Claude | ~/.claude/.credentials.json | C:\\Users\\passg\\.claude\\.credentials.json | Keychain; no file transfer |
| AGY | ~/.gemini/antigravity-cli/antigravity-oauth-token (legacy documented path) | No verified portable path; documented session keyring | Same legacy file candidate; verify installed version |

CODEX_HOME and CLAUDE_CONFIG_DIR override their respective defaults. Actual
Windows paths could not be stat-verified: the sandbox denied the metadata-only
SSH discovery command. AGY resolves its executable through PATH or
%LOCALAPPDATA%\\agy\\bin\\agy.exe. No Windows AGY token path is guessed.
An operator can set CLI_LOGIN_AGY_TOKEN_FILE to a verified portable token file;
set it in both local and remote execution environments when transferring AGY.
Without it Windows AGY status reports no/unsupported and transfer refuses.

The installed Linux AGY binary contains the name plugin-secrets.json next to
antigravity.plugins/keychain messages, but does not contain the legacy
antigravity-oauth-token filename. This is evidence of version drift, not proof
that plugin secrets are login credentials. The helper deliberately does not
copy plugin-secrets.json: its necessity, scope and portable format have not been
verified. Do not copy unrelated plugin secrets speculatively. Existing workers'
authentication was neither inspected nor changed.

### Claude on the Mac

Do not write the Keychain. Proposed organization route: run `claude setup-token`
once in a separate, secret-safe capture flow, store the resulting long-lived
OAuth token in the approved secret manager, and inject CLAUDE_CODE_OAUTH_TOKEN
into workers on all three hosts at launch. Do not place the token in a command
argument, a Run-card output log, or git. The existing org-mesh design already
specifies this approach. The helper does not implement setup-token capture or
secret-manager writes; its `login claude` performs ordinary interactive auth.
A Mac login can work locally, but `push/pull claude` on the Mac fails without
reading or changing the Keychain. The three-login objective is therefore not
fully achievable with file copying alone.

## Transfer after CTO review

`push` is an explicit overwrite operation: do not run it while workers may be
refreshing the same file. There is no automatic post-login fan-out. Review and
run the transfer cards after the source login succeeds. Transfer failures after
installation leave the new file in place and return nonzero; there is no rollback.

Contabo to Winbox (substitute claude or agy only when its storage is supported):

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host contabo --expects-input --risk amber --timeout 1800 --why "Copy reviewed Codex login to winbox" --expected "Remote status yes" --command '/opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/tools/cli_login.py push codex --to winbox'
```

The payload is a bounded base64 JSON envelope on SSH stdin, never argv. SSH uses
no PTY for transfers. The remote helper accepts only the selected CLI's fixed
local path, writes an owner-only temporary file, atomically replaces the target,
and runs status there. POSIX mode is 0600; Windows additionally removes inherited
ACLs and grants only the current user SID full access before writing bytes.
Remote stdout/stderr are captured and never forwarded to the card log.

The mesh permits Mac-to-Contabo SSH (`mooniex-vps` alias). Inbound Mac SSH is
forced to node_dispatch (ADR 0034), so `push --to mac` refuses before reading a
credential. Use this Mac-side pull card instead:

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/ask_run.py create --host mac --expects-input --risk amber --timeout 1800 --why "Pull reviewed Codex login onto Mac" --expected "Mac status yes" --command '/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/cli_login.py pull codex --from contabo'
```

Pull captures a private SSH stdout pipe into memory, installs locally, then runs
status. Those bytes never reach the parent/card stdout. The internal _export
endpoint refuses a terminal and requires SSH_CONNECTION; never invoke it manually
or redirect its output into logs. _receive is also an internal endpoint.
Mac can push supported portable files to Contabo or Winbox; Contabo uses
`ssh winbox`. Source/target helpers must both be deployed. No SSH permissions or
forced-command policy are changed by this tool.

## Codex refresh-token risk

[Official authentication documentation](https://learn.chatgpt.com/docs/auth)
describes copying the cache to a headless host. However, the
[official CI/CD guide](https://learn.chatgpt.com/docs/auth/ci-cd-auth) warns against
using one auth.json across concurrent machines: refresh can replace its tokens,
and another host may hold an invalidated copy. Therefore one login for three
concurrent hosts is not a reliable supported promise. Prefer independent
sessions, or a serialized workflow retaining the latest refreshed cache.

The helper reports no when `codex login status` returns nonzero, including after
the CLI removes/rejects invalid local auth. But that command can report cached
login presence without validating refresh against the server. A revoked copied
refresh token can remain a **false yes** until a real worker request fails.
Do not treat a green status as proof of simultaneous cross-host refresh health.
The helper does not refresh tokens itself or make a billable model call.

## Evidence and remaining acceptance

- Empty-HOME Claude probe reached exactly `Paste code here > ` without signing in.
- Empty-HOME AGY probe failed before its menu: local listener socket denied by
  this sandbox. Installed binary strings include `Enter the authorization code:`
  and `Paste the authorization code below:`; these are parser fixtures, not a
  successful runtime measurement. Repo's older probe records a different prompt.
- Empty-HOME Codex probe reached a device-auth network error; outbound connection
  was blocked. No actual device code or login was completed.
- Fake-CLI tests cover wrapped URLs, PTY input, AGY Enter selection, device codes,
  failure status, private transfers and file permissions. Native Windows/macOS,
  current AGY token location, keyring portability and real Run-card input remain
  acceptance work for the CTO. No live push was attempted.

References: [mesh](../design/org-mesh.md),
[Windows session evidence](agent-runners.md#6a-on-windows-agys-sign-in-is-session-scoped-2026-09-22),
[legacy AGY probe](antigravity-cli-test.md).
