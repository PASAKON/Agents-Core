# task-97d0f7e8 (W3.1) — org core imports and runs on Windows

Branch `agent/developer-task-97d0f7e8`, based on `7485c9c8`. Nothing pushed, nothing installed, no ssh to winbox (the live winbox run is W3.4).

## Files changed

| File | Change |
|---|---|
| `lib/proc.py` (new) | `pid_alive(pid, *, denied_is_alive=True)`. POSIX `os.kill(pid, 0)`; Windows `OpenProcess(0x1000)` + `GetExitCodeProcess == 259` through ctypes. `pid <= 0`, non-int, bool, and `> 0xFFFFFFFF` (Windows) are False. Stdlib only. |
| `tools/delegate.py` | `_pid_alive` and `_operator_counts_as_live` use `pid_alive`. `_spawn_local` on `win32` fails the row with a reason instead of dying in `tmux.create`. Three bare `read_text()` got `encoding="utf-8"`. |
| `tools/worker_reap.py` | `_pid_alive` uses `pid_alive(pid, denied_is_alive=False)` (the reaper never treats a stranger's pid as its own). |
| `scripts/session_list.py` | `tmux_lock_live` uses `pid_alive(pid, denied_is_alive=False)`; `live_ids()` returns `(set(), False)` off the Mac (no osascript call). |
| `tools/session_cap.py` | `_alive` uses `pid_alive`; lock read has `encoding="utf-8"`. |
| `tools/tmux_session.py` | `has_session` False, `capture` "", `create` raises `RuntimeError("tmux is not available on Windows")` on `win32`. `send_keys`, `kill`, `start_ttyd` degrade through `has_session`. |
| `lib/db.py` | `OD_ROOT` constant removed (no other user). New `_od_root()`: `$CLAUDESIGN_OD_ROOT`, else `project_path_for_host("mooniex-claudesign", self_host()) / ".od"`. No checkout on the host: designer context off, one stderr warning per process. Looked up per call, never at import. |
| `lib/telegram_out.py` | `CLAUDEFLOW_ENV_DEFAULT` literal removed. New `_claudeflow_env_default()`: Mac only, from the `mooniex-claudeflow` row of `config/projects.yaml`; elsewhere None plus one warning. `CLAUDEFLOW_ENV` override unchanged. |
| `scripts/lib/cxo_mcp_config.py` | `_venv_python` falls back to `.venv\Scripts\python.exe` (and names the Windows path when no venv exists on Windows). Every call site already used it (`_org_tool_names`, `_build("org")`, `main`); pinned by an AST test. `write_text` got `encoding="utf-8"`. |
| `config/wikis.yaml` | Comment only: winbox sets `WIKI_ROOT_ORG` / `WIKI_ROOT_MOONIEX` / `WIKI_ROOT_LUNGNOTE`. `tools/wiki.py` already resolves by env, skips missing roots in list/search, and raises `WikiError("... not available in this environment")` otherwise, so nothing crashes at import. `path:` keys unchanged. |
| `lib/notify.py` | Verified, no edit: osascript is already behind `sys.platform == "darwin"`. |
| `tests/test_w31_windows_portability.py` (new) | 58 tests, see below. |

## What was done

- **pid probe.** On Windows `os.kill(pid, 0)` is `CTRL_C_EVENT`, not a probe, so the four sites now share one helper. The per-site EPERM reading is kept through `denied_is_alive` (delegate and session_cap treat "denied" as alive; worker_reap and session_list treat it as not ours).
- **Behaviour deltas on Mac/Linux** (all in edge cases the old code got wrong or could not reach): `pid <= 0` and non-int now False (the old `os.kill(0/-1, 0)` probed a process group); an `OSError` other than ESRCH/EPERM now False everywhere (delegate's old `_pid_alive` returned True); `delegate._operator_counts_as_live` still returns True on `TypeError`/`ValueError`.
- **Windows caveats:** a process that itself exits with code 259 reads as alive (`STILL_ACTIVE`). `worker_reap._pid_matches_task` shells out to POSIX `ps`, so on Windows it reads "does not match" and never reaps (safe direction).
- **Found while testing:** ctypes truncates a pid to a DWORD, so `2**32 + 4242` would have probed pid 4242. Fixed with a range guard.
- **Found while testing:** `delegate._scope_owners` catches `(OSError, yaml.YAMLError)`, so a `UnicodeDecodeError` from `config/storage-policy.yaml` (461 non-ASCII bytes) escaped under a non-UTF-8 locale, which is what winbox has by default. Fixed with `encoding="utf-8"`. Measured with `LC_ALL=C LANG=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 python -X utf8=0`.
- **Not touched, still probe with `os.kill(<x>, 0)`** (outside the declared touches or owned by another task): `tools/node_dispatch.py:113` (W3.3), `tools/maintab.py:351` and `:505`, `runners/cto_chat.py:78`, `scripts/browser/tab_registry.py:107` (winbox-relevant), `scripts/session_orphans.py:154/163/168`, `claude-home/tools/prune_transcripts.py:109`; tests `scripts/test_depends_on_enforcement.py:85`, `scripts/test_spawn_tab_routing.py:338`.
- **Other Windows notes (not fixed, not in scope):** `tools/credit_ledger.py` imports `fcntl` at module top (Mac-only CLI, nothing imports it; used as the control in the smoke test). `delegate` `WORKER_LAUNCHER` is bash. `session_list.py` prints emoji glyphs (cp1252 stdout). `npx`/`mcp-server-supabase` are `.cmd` shims on Windows.

### Tests added (`tests/test_w31_windows_portability.py`)

- Real `pid_alive`: this process, a live child, a killed child, `0`/`-1`/`None`/`True`/`"123"`/`12.0`/`2**70`, EPERM on pid 1 (skipped for root/Windows).
- Windows branch with a fake kernel32 and `os.kill` replaced by a function that fails the test: running, exited, exit-code query failing, no such pid, access denied both ways, non-pids never open a process, handle always closed.
- The four sites route through it, each with its own EPERM reading; `session_list.tmux_lock_live` against a temp lock dir.
- Static AST check: no `os.kill(<x>, 0)` in the four files. The checker is proven to find one: run on `git show 7485c9c8:<file>` it reports lines 386/779 (delegate), 114 (worker_reap), 89 (session_list), 65 (session_cap).
- Import smoke in a subprocess: warm imports, drop `lib`/`tools`/`scripts`/`runners`, set `sys.platform="win32"`, block `fcntl termios pwd grp resource`, import the 12 touched modules; control `tools.credit_ledger` must fail on `fcntl`.
- Guards: tmux helpers, `live_ids`, `notify` never reach subprocess; `_spawn_local` on win32 fails the row (driven with `coro.send(None)` against a fake db, never the real ledger/worktree/spawn).
- Paths: `_od_root` (override, Mac, winbox with one warning), `resolve_od_project`/`designer_kickoff_suffix` degrade, claudeflow `.env` fallback (Mac, winbox, override wins), `_venv_python` (both OS layouts, POSIX wins when both exist), AST pin that no interpreter path is built outside `_venv_python`, missing wiki roots degrade.
- Encoding: no bare `read_text`/`write_text` in the ten touched files (AST), and `delegate` policy reads under an ASCII locale in a subprocess.

## Tests (quoted)

Final commit `9d5aca02`, interpreter `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` (the worktree has no venv), run one after the other:

```
python -m pytest -p no:warnings                  -> 4017 passed, 27 skipped in 307.09s (0:05:07)   exit=0
ORG_HOST=contabo python -m pytest -p no:warnings -> 4017 passed, 27 skipped in 306.16s (0:05:06)   exit=0
python scripts/test_org_tools_registry.py        -> ALL PASS   (29 [PASS], 0 [FAIL])                exit=0
python scripts/test_mcp_role_config.py           -> OK — 0 failure(s)   (57 [PASS], 0 [FAIL])       exit=0
```

New file alone: `tests/test_w31_windows_portability.py` 58 passed in 0.77s. Suites that pin the edited helpers (`scripts/test_tmux_session.py`, `scripts/test_session_list_liveness.py`, `scripts/test_telegram_out.py`, `tests/test_w03b_local_launcher.py`): 94 passed when run alone, and they are inside the 4017. The 27 skipped are identical on both hosts; I did not run a baseline at `7485c9c8`, so I cannot say how many of the 27 predate this change.

Not run: anything on real Windows (W3.4). The Windows branch is proven against a fake kernel32 only, the win32 import against a faked `sys.platform` on a Mac.

## Blockers

1. **`lib/config.py` is outside the declared touches and unreadable under a non-UTF-8 locale.** Measured on the worktree with `LC_ALL=C LANG=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 python -X utf8=0`: `lib.config.projects()`, `agents()` and `hosts()` each raise `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2` (the yaml files hold Thai and typographic characters). Seven bare `.read_text()` at `lib/config.py` lines 28, 40, 52, 147, 173, 209, 342 need `encoding="utf-8"`. `self_repo_guard` refused my edit (ADR 0020) and I sent `dev_message` asking for the path to be added to `touches`; no answer yet, so I did not work around it. Consequence: unless the winbox launcher exports `PYTHONUTF8=1`, `delegate`, `db` and `router` on winbox fail as soon as they call `projects()`. Either declare `lib/config.py` for a follow-up, or have W3.3/W3.4's launcher set `PYTHONUTF8=1` (which also covers every other bare read in the repo I did not touch).
2. Nothing else blocking.

## Skill learning

- MISSING [self_repo_guard / CXO_Protocol_DelegateExternal §touches]: a Windows-portability task needs `lib/config.py` in `touches` (7 bare `read_text()`); the W3.1 brief did not list it and the fix was refused mid-task · evidence: task-97d0f7e8, `lib/config.py` guard refusal
- MISSING [CXO_Protocol_DelegateExternal §windows-worker-env]: every winbox worker launcher should export `PYTHONUTF8=1`; a locale-default read of any Thai-bearing yaml is a crash there · evidence: `LC_ALL=C ... python -X utf8=0` repro in Blockers 1
- COSTLY [no owner]: proving a Windows branch on a Mac. Patch only `sys.platform` (not `os.name`), warm the stdlib imports first (patching before import breaks `subprocess`/`ssl`), patch a `_last_error()` helper because `ctypes.get_last_error` is Windows-only, and drive an `async def` with `coro.send(None)` instead of `asyncio.run` · evidence: `tests/test_w31_windows_portability.py` · prevented by: a short "faking win32 in pytest" note in the tester playbook
- COSTLY [no owner]: a mid-run edit corrupts a full-suite run; the whole suite takes ~5 min here, so run it once after the last edit · evidence: first baseline run killed, re-run after final commit
