# REPORT task-1178951e

Implemented a stdlib Python 3.11 login/status/transfer helper and nine exact
login Run-card commands. Fake-credential tests pass. The full three-logins-for-
three-hosts outcome is **not verified or guaranteed**: current AGY storage and
Windows session behavior need on-host acceptance; shared Codex refresh tokens
conflict with the official concurrent-host guidance. No live login, credential
inspection, logout, overwrite, push, Run card, or Keychain write was performed.

## Files changed

- `tools/cli_login.py`: sanitized status; POSIX PTY and ctypes Windows ConPTY;
  wrapped URL reconstruction; device-code display; one-line stdin forwarding;
  AGY menu selection; status-gated success; bounded SSH transfer envelopes;
  atomic owner-only installation; Mac-side pull; restricted internal endpoints.
- `tests/test_cli_login.py`: fake CLIs on PATH under a temporary HOME, fake
  credentials and mocked SSH. Covers all four requested cases plus delayed
  wrapping, OSC hyperlinks, AGY menu/device-code flows, redaction, pull,
  permissions, unsupported Keychain, export guard and symlink rejection.
- `docs/ops/cli-login.md`: exact Run-card commands for three CLIs on three hosts,
  transfer cards/routes, storage limitations, proposed Claude setup-token flow,
  status semantics and acceptance work.
- This report.

## Validation performed

- Ran exactly:
  `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_cli_login.py`
  (no `-q` argument): **16 passed**. All test credentials were fake and under a
  temporary HOME. SSH was mocked in transfer tests.
- `git diff --check` and per-file `git diff --no-index --check /dev/null`:
  no whitespace errors after removing one trailing blank line in the ops guide.
- Empty-home runtime probes used a minimal environment, temporary config/data
  roots, temporary cwd and browser suppression. No authorization code was
  submitted and no real account was authenticated.
  - Claude reached `Paste code here > ` after the OAuth URL.
  - AGY failed before its menu: `listen tcp 127.0.0.1:0: socket: operation not
    permitted`. Its actual prompt could not be measured in this sandbox.
  - Codex initially required its temporary CODEX_HOME directory to exist; after
    creating that empty directory it reached a device-auth network error.
- Inspected only the installed AGY executable's strings (not credentials):
  `Enter the authorization code:` and `Paste the authorization code below:`
  are present. `plugin-secrets.json` appears near `antigravity.plugins` and
  keychain messages. The legacy `antigravity-oauth-token` name is absent.
- Attempted metadata-only Windows path discovery through `ssh winbox`.
  The sandbox denied sockets before any remote command ran. No Windows files
  were read or changed.
- Read `docs/design/org-mesh.md`, `config/hosts.yaml`,
  `docs/ops/agent-runners.md` and the legacy AGY probe documentation.
  MAILBOX.md was checked between implementation/validation steps; absent.

## Not checked / risk

- **Codex refresh-token question:** Can one auth.json support concurrent workers
  on three hosts after refresh? The [official CI/CD authentication guide](https://learn.chatgpt.com/docs/auth/ci-cd-auth)
  explicitly advises against sharing it across multiple machines/concurrent
  jobs and identifies another machine rotating the token first as a failure
  cause. The [general authentication guide](https://learn.chatgpt.com/docs/auth)
  permits bootstrap copying to a headless host; that does not establish safe
  concurrent refresh. No live rotation experiment was performed. The helper
  catches a failure when `codex login status` returns nonzero, but cached status
  may remain yes until the CLI encounters the invalid refresh token on a real
  request. Thus status alone cannot reliably detect server-side revocation.
- Native Windows ConPTY, Windows owner-only ACL installation, macOS PTY and real
  phone-card input are implemented/documented but not tested on those hosts.
- AGY's current storage is unresolved. Linux/macOS use the task's legacy file
  path unless CLI_LOGIN_AGY_TOKEN_FILE points to a verified file. Windows has
  no guessed token path: status/transfer fail closed without that override.
  Repository evidence says AGY auth there is in the session-1 keyring, not the
  Linux location; plain SSH is session 0 and may not authenticate workers.
- `plugin-secrets.json` is not copied. Its name occurs in the executable's
  plugin/keychain context; no evidence established it as necessary OAuth auth.
  Current AGY could require a different store. No real secret file was inspected.
- Windows Claude/Codex default paths are derived from the documented home layout
  and supported environment overrides, not a successful live filesystem probe.
- Mac Claude remains in the Keychain. No Keychain writer exists. The ops guide
  proposes `claude setup-token` plus secret-manager-backed
  CLAUDE_CODE_OAUTH_TOKEN injection, consistent with org-mesh. Secure setup-token
  capture/distribution is a separate deployment step; do not log its output in
  an ordinary Run card. File transfer cannot deliver Mac Claude credentials.
- Explicit push/pull overwrites the destination atomically, without rollback
  after a failed status check. Do not overlap with active credential refresh.
  No automatic fan-out was enabled and no live transfer was attempted.
- Mac pull uses an SSH stdout **private pipe captured in memory**, never the
  card/parent stdout. Push sends bytes only on SSH stdin. The internal export
  endpoint must not be manually redirected into a log.

## Blockers

- CTO/on-host acceptance is needed to measure the current AGY empty-home prompt,
  discover its Windows token metadata/storage API and determine whether its
  OAuth store is portable at all. Sandbox networking prevented those probes.
- Validate ConPTY and Run-card input on Winbox, including the session-1 boundary,
  before treating the Winbox AGY command as operational.
- One Codex login shared by concurrent hosts is not a reliable supported plan;
  independent sessions or serialized use with persistence of refreshed auth
  needs an operational decision. No request/card was raised in this build task.
- Mac Claude needs the reviewed long-lived-token distribution route rather than
  file copying. These limitations prevent claiming the entire CEO outcome done.

## Skill learning

- Used the OpenAI Docs skill at
  `/root/.codex/skills/.system/openai-docs/SKILL.md` for the refresh-token question.
  Evidence: the official CI/CD guide distinguishes one-time cache copying from
  concurrent multi-host use. A local `login status` result is insufficient proof
  that a copied refresh token remains usable. No skill file was modified.
