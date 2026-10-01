# task-1c0b6f9a - W4.6b: node side and endpoint side of the join security review

Source: `docs/reports/task-79219f24/REPORT.md` (merged ac78e53d). Branch `agent/developer-task-1c0b6f9a`,
developer worker, Sonnet 5.5. Claude only (IRON section 59). The parallel task W4.6a owns
`hq_join approve` and the provisioning wait; nothing of it was touched here.

## Per-finding status

| Finding | Status | What was done | Where |
|---|---|---|---|
| F1 node side | done | Step order is now keys (2), accept (3), install (4), tailnet (5), wait (6), clone (7), identity (8), probe (9). After accept: `fingerprint: <last 8 chars of the age recipient> - the operator approves this in the Run Inbox`. The poll says `waiting for the operator to approve fingerprint <fp> in the Run Inbox (N s)`. Step 2 installs only the tools keys and hub calls need (curl, ssh-keygen, age, python+venv; on Windows age and Git for its ssh-keygen). | join.sh, join.ps1 |
| F9 | done | No `--token` and no `ORG_JOIN_TOKEN`: read from `/dev/tty`, `stty -echo`, restored on normal return, `die`, EXIT, INT, TERM, HUP. Windows: `Read-Host -AsSecureString`, `SecureStringToBSTR` then `ZeroFreeBSTR`. No-argument form documented as preferred in both script headers and the README. argv form still works. | join.sh, join.ps1, README |
| F7 | done | `write_known_hosts` / `Write-KnownHosts` fetch `https://api.github.com/meta` over TLS, keep only `ssh_keys` entries that match `(ssh-ed25519\|ecdsa-sha2-nistp256\|ssh-rsa) <base64>`, and REPLACE `$CONF_DIR/known_hosts`. Clone and pull use `StrictHostKeyChecking=yes`. Fetch failure or zero usable keys: `die`, git never starts, no `accept-new` anywhere in code. | join.sh, join.ps1 |
| F6 minimum | done | Every python call in join.sh is `-I`. Probe runs `-I -B` and by path (see "Probe under -I"). Residual: root still runs code from the user-owned clone (see Issues). | join.sh |
| F11 | done | Module-level `threading.BoundedSemaphore(4)` (`_DB_GATE`, `DB_SLOTS`), `DB_WAIT_S = 2.0`, contextmanager `_db_slot()`. Wraps `hq_join.accept` in `_route_accept` and the two DB sections in `_route_sealed`. No slot: `503 {"error":"busy"}` + `Retry-After`. Body is read and shape-checked BEFORE the slot, so slow clients hold none and a bad-shape request still gets its old 403/400. join.sh and join.ps1 now have a 503 branch (accept and sealed fallback: "hub is busy, run the same command again, token not used up"); the poll treats a 503 as "retrying". | join_api.py, join.sh, join.ps1 |
| F3 part | done | Unit gets `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp`, `ProtectKernelTunables`, `ProtectKernelModules`, `ProtectControlGroups`, `RestrictSUIDSGID`, `LockPersonality`, each with a comment. No `ReadWritePaths=`: nothing in the service writes to disk (Postgres over the network, stderr to journald, reads of /etc/infisical and the checkout). No secret or DB-role change (CEO decision, left open). | org-join.service |

## Probe under -I (what I did, as asked)

`python -I` puts no current directory on `sys.path`. Reproduced: from the checkout,
`python -I -B -m tools.node_dispatch probe` fails with `No module named 'tools'`. So `do_probe`
now starts the probe BY PATH: `"$CORE/.venv/bin/python" -I -B "$CORE/tools/node_dispatch.py" probe`,
and `infisical_setup.py` by path too. `tools/node_dispatch.py` already does `sys.path.insert(0, ROOT)`
at import time (line 49), so `lib` and the other `tools` modules resolve. Checked by running the file's
module body under `-I` with `runpy` (no ledger opened): imports fine. `-B` is added because `-I` ignores
`PYTHONDONTWRITEBYTECODE`; the variable is dropped. The w44c control test that replaces
` env HOME="$HOME" ORG_HOST="$HOST" ` still finds that exact substring.

## Files changed

- `deploy/join/join.sh` - reorder, fingerprint, tty prompt, known_hosts, `-I`, 503 branches, split install.
- `deploy/join/join.ps1` - same set, PowerShell 5.1, ASCII, LF.
- `tools/join_api.py` - DB gate, 503, `Retry-After`, docstring paragraph.
- `deploy/join/org-join.service` - sandbox directives with comments.
- `deploy/join/README.md` - preferred no-argument form, new flow, "What root runs" (F6), GitHub host keys (F7), unit sandbox and load gate, test list.
- `tests/test_w46b_node_fixes.py` - new, 49 tests.
- `tests/test_w43_join_scripts.py` - `_run` uses `start_new_session=True` (no controlling tty, so the new prompt cannot stop a run); probe string is now `tools/node_dispatch.py probe`.
- `tests/test_w44c_join_followups.py` - stub python finds the JSON reader by scanning all args for `-c` (calls are now `-I -c`); probe string updated.
- `tests/test_w43_join_api.py`, `tests/test_w45_bind.py` - not edited: no rule they assert changed, and both still pass.

## Commits

- a91d8af2 join: keys+accept before installs, token from tty, pinned known_hosts, python -I, DB slot gate (W4.6b)
- aa89e3d5 join: join.ps1 keys+accept before installs, hidden token prompt, pinned known_hosts; org-join.service sandbox (W4.6b)
- 2a4e6420 join: README for W4.6b (no-arg token form, accept before install, known_hosts, -I, unit sandbox)
- 05d3af50 tests: W4.6b node and endpoint fixes (order, fingerprint, tty, known_hosts, -I, 503 gate, unit)
- one more commit carries this report.

## Tests

- New file: `tests/test_w46b_node_fixes.py` - 48 passed, 1 skipped (`systemd-analyze` absent). Covers: main order, dry-run order with the fingerprint text between steps 3 and 4, real fingerprint line through the real endpoint, repeat-token path, refused token (no fingerprint), wait-step wording, 503 at accept / sealed fallback / poll, pty tests on a real controlling terminal (echo off while waiting, token never echoed, echo restored after a normal read, TERM, INT, EOF and a bad token, argv token never prompts), ps1 as text, known_hosts (written before git, strict ssh command, failed fetch, unusable reply, stale file replaced, junk entries dropped, second run pulls strictly, no `accept-new` in either script), `-I` (static scan, recording python, `-m` reproduction, by-path import), the gate (type and constants, which routes take a slot via AST, 503 shape, same 503 for good/fake/other-host tokens, malformed request still refused the old way, max 4 concurrent with 8 callers, slot returned after a handler exception), unit directives and comments, `ExecStart` untouched, no writable path, `config.hosts()` with an unreadable home.
- Full suite, run once: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` - 5431 passed, 205 skipped, 0 failed, 442.50 s.
- Scripts: `scripts/test_org_tools_registry.py` 29 PASS / 0 FAIL; `scripts/test_mcp_role_config.py` 57 PASS / 0 FAIL; `scripts/test_tool_parity.py` 2 PASS / 0 FAIL. Exit 0 each.
- `sh -n` and `shellcheck -s sh` clean on join.sh.
- Not run, not available here: `pwsh` (join.ps1 was read as text, never parsed or executed), `systemd-analyze verify` (unit never started). Both need a Contabo or winbox check before rollout.

## Issues / blockers

- join.ps1 is untested beyond text checks. First real Windows run is the test.
- The unit is unverified on a live systemd. Before `daemon-reload` on Contabo: `readlink -f /opt/MoonieXHQ/Agents/Core/.venv/bin/python` must not resolve under /home or /root (`ProtectHome=yes` would hide it), then `systemd-analyze verify`, then the two checks in the README.
- F6 is only the minimum. Root still executes user-writable clone code in steps 8 and 9, and `-I` does not block a `.pth` in the venv's or Homebrew's own site-packages. The real fix is a model change (dedicated user, or root-owned copy, or dropping to `SUDO_USER` before `run`). Documented in README "What root runs".
- F3 is partial by design: the service still holds all Agents-Core prod secrets and connects as the full `org` role. CEO decision.
- Out of my touches, for W4.6a or the CTO: `docs/ops/hq-join.md` does not yet describe the approval step or the new node step order.
- No blockers.

## Notes for reviewer

- ASCII deviation: the task text has an em dash in the fingerprint line. Scripts and unit are asserted ASCII-only by the existing tests (PS 5.1 reads BOM-less files as ANSI), so the line reads `fingerprint: <8 chars> - the operator approves this in the Run Inbox` with a hyphen. W4.6a should not match on the dash.
- The fingerprint is `AGE_PUB` last 8 characters, exactly what `hq_join approve --fingerprint` is specified to compare. Dry run prints a placeholder instead.
- known_hosts is fetched at the start of step 7 (literally "before cloning"). A fail-fast fetch before accept would show a network problem earlier; a failed step 7 is resumable because a used token is recognised through `/sealed`. Say if you want it moved.
- No env override exists for the GitHub meta URL on purpose (it would weaken the trust anchor). Tests use a `curl` shim.
- `ProtectHome=yes` and the accept path: `lib.config.hosts()` catches `OSError`, verified by a test with a mode-0000 home (Python 3.12 raises `PermissionError` from `Path.exists()`; Contabo runs 3.12, local tests 3.14).
- A 503 from the gate happens before any DB work, so a refused accept leaves the token unused. Tested end to end.
- Flaky-test guard: the 8-caller concurrency test staggers thread starts by 20 ms; one earlier full-file run lost a response, most likely a burst into the server's small listen backlog (I did not prove the cause). It passed in the full-suite run.

## Skill learning

- MISSING [pty test helper | no owner] : a session leader that exits on macOS revokes the terminal, so `termios.tcgetattr(slave)` raises ENOTTY afterwards, and it does not finish exiting until someone drains its output from the master (`proc.wait()` without reading hangs). Fix pattern: an outer `sh` session leader held open by a release file; drain the master while waiting. evidence: tests/test_w46b_node_fixes.py `_Pty`, task-1c0b6f9a
- MISSING [test-writing | no owner] : `python -I` drops cwd AND script dir from `sys.path`, ignores `PYTHONDONTWRITEBYTECODE` (needs `-B`), so `-m pkg.mod` from a checkout breaks while running the file by path works if it inserts its own ROOT. evidence: tests/test_w46b_node_fixes.py `test_dash_I_breaks_dash_m_...`, task-1c0b6f9a
- COSTLY [no owner] : I extrapolated the full-suite runtime from 3% after 90 s (about 50 min) and killed a run bounded at 590 s; the real run took 442 s, so the first run would have fit. The early percentage is slow (collection plus the slow first tests). Restart cost about 2 min. prevented by: start the suite once in the background with no bound and read the percentage only after 10%+. evidence: task-1c0b6f9a, full-suite.txt
- COSTLY [no owner] : the CTO message arrived as `[New message from CTO]` with an empty body and no inbox `file_id`, so nothing could be acted on. evidence: task-1c0b6f9a, mid-session. prevented by: the sender includes the text, or the harness shows the body.
- (GateGuard note, already in CLAUDE.md) : one error per new file, answered once each; nothing new.
