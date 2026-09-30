# REPORT task-49f70bc6

W4.4 probe `provides_measured`, W3.5 wake wiring behind `ORG_WIN_WAKE` (off), W2.7 F3b win32 disk floor.
All three are in `tools/node_dispatch.py`. `lib/router.py`, `config/hosts.yaml`, `lib/mesh.py`, `windows/*.ps1` and winbox were not touched.

## Summary

`probe` now reports `provides_measured` (OS family, chrome, ffmpeg, nvidia gpu, node20, playwright_chromium, runner_claude, runner_codex, runner_agy) and `probe_errors`, found on the node; credential files are checked by `os.stat` only and never opened. A C-level letter on Windows calls `wake_windows_tab` only when `ORG_WIN_WAKE` is exactly `1` (anything else is today's `woke: false`, pinned). Win32 `spawn_worker` now refuses, before any PowerShell, when free disk on the worktrees drive is below `delegate`'s own floor.

## What changed

### 1. W4.4 probe (`verb_probe`, new `_measure_provides` + detectors)

| name | detected by |
|---|---|
| `macos`/`linux`/`windows` | `_os_name()` (`darwin` mapped to `macos`), always first |
| `chrome` | regular file at the usual per-OS paths (macOS `/Applications`, `~/Applications`; Linux PATH names, `/opt/google/chrome/chrome`, `/snap/bin/chromium`; Windows `PROGRAMFILES`, `PROGRAMFILES(X86)`, `LOCALAPPDATA`) |
| `ffmpeg` | on PATH and `ffmpeg -version` exits 0, 5 s |
| `gpu` | `nvidia-smi -L` exits 0 and prints a `GPU ` line, 5 s. NVIDIA only |
| `node20` | `node --version` exits 0, major >= 20, 5 s |
| `playwright_chromium` | browsers folder holds a `chromium*` dir (`PLAYWRIGHT_BROWSERS_PATH`, else per-OS default) |
| `runner_claude` / `runner_codex` / `runner_agy` | `os.stat`: regular file, size > 0, at `$CLAUDE_CONFIG_DIR/.credentials.json` (default `~/.claude`), `$CODEX_HOME/auth.json` (default `~/.codex`), `~/.gemini/antigravity-cli/antigravity-oauth-token` |

- Children: argv list, no shell, stdin and stderr `/dev/null`, `timeout=PROBE_CHILD_TIMEOUT_S` (5). Worst case 3 children = 15 s; measured 0.5 s on this Mac. `lib/mesh.py` gives `probe` the 30 s default.
- A detector that raises or times out is absent and adds one `probe_errors` entry, `"<name>: <ExceptionType>"` (type only, never the message).
- Reported only. Not written to the `hosts` row (no new column; `lib/db.py` untouched).
- Real run on this Mac (detector function only, no DB write): `['macos','chrome','ffmpeg','node20','playwright_chromium','runner_agy']`, no errors.

**How the router should merge measured vs declared (proposal, nothing built):**

```
MEASURABLE = {macos, linux, windows, chrome, ffmpeg, gpu, node20, playwright_chromium,
              runner_claude, runner_codex, runner_agy}
effective  = measured  U  (declared - MEASURABLE)
```

- For a name in `MEASURABLE`, the measurement wins in both directions. A declared `chrome` with no measured `chrome` is dropped and logged as drift; a measured name nobody declared is added.
- Declared-only names pass through: `macos_cu`, `blender_bridge`, `blender`, `win_gui`, `always_on`, `api` (`blender` is declared for winbox in `hosts.yaml` and is not in the brief's list; it cannot be measured either).
- Use `provides_measured` only from a probe the router already accepts as fresh. A stale or missing probe falls back to declared, flagged as unmeasured.
- Persist it in a new `hosts` column (`provides_measured`, JSON, next to `provides` in `lib/db.py`) so the router reads one row. That is a `lib/db.py` + `lib/router.py` change for a later task.
- `runner_*` means "credential file present". Intersect with `hosts.runners` (installed CLIs) before routing a task to a runner.

### 2. W3.5 wiring (`_windows_wake`, called from `_write_clevel_letter`)

- `ORG_WIN_WAKE` exactly `"1"`: after the letter is on disk, call `agent_transport.wake_windows_tab(f"{role}-{sid}", from_role.upper())` once; return its `woke` (only a real `True`) and `why` (redacted, capped at `MAX_ERROR_CHARS`).
- Unset or any other value (`0`, `true`, `yes`, `" 1"`, `"1\n"`, fullwidth `1`, ...): exactly today's `{"woke": False}`, and `wake_windows_tab` is never called (pinned: 14 values + the unset case).
- A wake that returns false or raises: `woke: false` + `why`, the letter stays delivered, no `last_error`.
- Worker letters (`MAILBOX.md`) stay `woke: false`. POSIX path untouched (tmux wake).
- `docs/ops/windows-wake.md` said `agent_transport` "is already imported in that module". It was not (only a lazy import inside `_write_worker_letter`), so the patch as written there would have raised `NameError`. The wiring imports it inside `_windows_wake`. The doc's Wiring section now describes what was built.

### 3. W2.7 F3b (`_windows_disk_floor_gate`, called last in `_windows_spawn_gate`)

- Uses `delegate._free_gb` (the test seam), `delegate._disk_orange_floor_gb()` (`gauge.orange` of `config/storage-policy.yaml`), a strict `<`, and `delegate._scope_applies("disk_floor", owner_cto)`. No number in the function (pinned by an AST test).
- Reads the drive of `_worktrees_root()`, or its nearest existing ancestor on a first spawn.
- Refusal: `Refusal`, exit 2, `disk red on <host>: <free> GB free < <floor> GB floor ...`. The row stays `pending` (queueing for disk is the hub's).
- Runs after the host, dependency and conflict checks, before `_spawn_worker_windows` (so before any PowerShell).
- Browser cap: untouched, still the hub's.

## Files Changed

- `tools/node_dispatch.py` - `_measure_provides` + detectors, `provides_measured`/`probe_errors` in `verb_probe`; `_windows_wake`; `_windows_disk_floor_gate`, `_nearest_existing`; `import stat`.
- `tests/test_w44_probe_provides.py` (new, 60 cases) - every detector faked, hang/raise, win32, credential tripwire.
- `tests/test_w35_wire.py` (new, 31 cases) - the flag, the call, failure/raise, workers, POSIX.
- `tests/test_w27_security.py` - 12 F3b test functions next to the F3 tests; `Disk`, `_policy`, `disk` fixtures; `winbox` fixture takes `disk`; `ORG_WIN_WAKE` cleared in `_isolated`.
- `tests/test_w33_node_dispatch_windows.py` - `_stub_machine` stubs `_measure_provides` (its `win.calls == []` assertion saw a real `ffmpeg` call); `_isolated` fakes `delegate._free_gb` and clears `ORG_WIN_WAKE`.
- `tests/test_node_dispatch.py` - probe test stubs `_measure_provides` and asserts the two new fields.
- `docs/ops/node-dispatch.md` - probe fields, `ORG_WIN_WAKE`, disk floor, tests line.
- `docs/ops/windows-wake.md` - Wiring section rewritten (was "not done").
- `docs/reports/task-49f70bc6/REPORT.md` - this report.

## Commits

- 34c7ddea - node_dispatch: probe provides_measured (W4.4) + ORG_WIN_WAKE flag (W3.5) + win32 disk floor (F3b)
- 3a2d72c7 - tests: W3.5 wire flag pins (test_w35_wire) and W2.7 F3b disk-floor pins next to F3
- 5e0fb9fa - docs: node-dispatch probe fields, ORG_WIN_WAKE, win32 disk floor; windows-wake wiring now done (flag off) (also carries the `tests/test_node_dispatch.py` edit)
- 005a4dc6 - tests: keep test_w35_wire.py ASCII (fullwidth digit as an escape)
- the report commit on top of these (see `git log`)

## Tests

- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite, once, from this worktree; the worktree has no `.venv` of its own)
- passed: 4853
- failed: 0
- skipped: 28
- `scripts/test_org_tools_registry.py`: `ALL PASS`
- `scripts/test_mcp_role_config.py`: `OK — 0 failure(s)`
- `tests/test_w27_security.py` is green with every W2.7 test unchanged; the only edits there are additions plus the `ORG_WIN_WAKE` delenv and the `disk` fixture wiring.
- Mutation check: 20 deliberate breakages of `tools/node_dispatch.py` (flag accepts `true`; wake exception escapes; `woke` truthy not `True`; `why` not redacted; `<=` instead of `<`; disk gate not called; floor hard-coded 5.0; scope ignored; read error passes; root not walked up; credential `read_text()`; detector error escapes; child unbounded; `shell=True`; node 19 passes; gpu with no device list; playwright any folder; empty credential counts; error leaks message; extra key on the win32 letter). **20 of 20 caught**, source restored (`git status` clean).
- Invisible-character scan of all 8 changed files: none (Cf/Cc, NBSP, zero-width, BOM, line/paragraph separators). Added lines with non-ASCII: none after the fullwidth-digit fix.

## Issues / Blockers

- No blocker. Sonnet 5.5 was enough for this task.
- **`runner_claude` is a false negative on macOS.** Claude Code keeps its login in the Keychain on a Mac, not in `~/.claude/.credentials.json`. This Mac has no such file and `runner_claude` came back absent, though Claude Code runs here. The brief said files only, so I did not add a Keychain lookup. The router must not read "no `runner_claude`" on a darwin host as "not signed in". Options for the CTO: keep it declared for darwin, or allow a `security find-generic-password` exit-code check (no `-w`, so no secret is read). `runner_codex` is also absent on this Mac (no `~/.codex/auth.json`); I did not check where, if anywhere, codex keeps a login here.
- **Nothing ran on winbox.** The Windows paths are faked (platform, env dirs). The real Windows Chrome / playwright / credential locations come from convention, not measurement there.
- **`ORG_WIN_WAKE` must reach the sshd-launched process.** I did not try how a machine-level variable reaches the forced command on winbox.
- **Timeout when the flag goes on.** A worst-case wake blocks `deliver_letter` about 30 s (`schtasks` 15 s + 15 s wait). `lib/mesh.py` gives `deliver_letter` the 30 s default (it has no `VERB_TIMEOUT_S` entry), so a slow wake could make the hub see a timeout for a letter that was delivered (a retry then returns `already_delivered`). Typical is 4 s. Consider `VERB_TIMEOUT_S["deliver_letter"] = 45` in `lib/mesh.py` before enabling the flag (out of scope here).
- **F3b fails closed on a read error** (`Refusal`), unlike `delegate._remote_free_gb`, which fails open on an unreachable host. Reason: this is a local `disk_usage` on a path that exists (or its nearest ancestor), so a failing read is a real fault, and the hub's gate stays the primary. Say so if you prefer fail-open.
- **Commit split:** the first commit holds all three code changes (same file, shared hunks) with the W4.4 tests; W3.5 and F3b tests came in the second.
- Nothing pushed.

## Notes for Reviewer

- Read first: `_measure_provides` and `_file_has_content` (stat only, never opens), then `_windows_wake` (`!= "1"` is the whole gate), then `_windows_disk_floor_gate`.
- `test_no_credential_file_is_opened_read_or_echoed` arms a tripwire on `open`, `io.open`, `os.open`, `Path.open/read_text/read_bytes` for the three credential paths; `test_the_detector_source_never_opens_or_reads_a_file` is the AST twin. A `read_text()` mutation in the detector was caught.
- `test_w33`'s probe test failed the moment probe ran children (its `win.calls == []`); fixed by stubbing `_measure_provides` there, not by loosening the assertion. Any future test that fakes `subprocess.run` around `probe` needs the same stub.
- The probe's existing `os` field stays `_os_name()` (`darwin` on a Mac); the new family name in `provides_measured` is `macos`.

## Skill learning

- WRONG   [no owner - docs/ops/windows-wake.md §Wiring] : "`agent_transport` is already imported in that module" is false; `tools/node_dispatch.py` imported it only lazily inside `_write_worker_letter`, so the documented 3-line patch would raise `NameError` in `_write_clevel_letter` · evidence: `tools/node_dispatch.py` at 024bf79a, this task's `_windows_wake` · fix: section rewritten in commit 5e0fb9fa
- MISSING [no owner - delegation brief for DEV workers] : a DEV worktree has no `.venv`, so the brief's `.venv/bin/python -m pytest` fails; the brief should give the absolute venv path (`/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`) · evidence: first pytest call of this task (n=1)
- COSTLY  [no owner]  : a test that fakes the OS (macOS) on a real Mac still sees the real `/Applications/Google Chrome.app`; the faked-macOS probe test failed until filesystem existence checks went through a seam (`nd._is_file`) limited to tmp_path plus named fakes · evidence: `tests/test_w44_probe_provides.py` fixture, first run 2 failed · prevented by: a test that fakes a platform must also fake the filesystem probes that platform branch reads
- COSTLY  [no owner]  : an existing test that recorded `subprocess.run` and asserted `calls == []` broke the moment `probe` started running `ffmpeg`/`node`; · evidence: `tests/test_w33_node_dispatch_windows.py::test_probe_answers_on_windows` first run · prevented by: grep tests for the function's name and `calls == []` before adding a subprocess to it
- MISSING [CLAUDE.md (global) §GateGuard fact protocol] : the section lists the Bash, Write and Edit gates but not the extra Bash gate for a destructive command (hit on `git commit --amend`), which asks for the files modified, a one-line rollback and the instruction verbatim · evidence: this task, the amend of the W3.5/F3b commit (n=1)
