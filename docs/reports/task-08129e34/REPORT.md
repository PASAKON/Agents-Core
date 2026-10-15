# REPORT task-08129e34

## 1. Root Cause Analysis: Why Nothing Reaches the Systemd Journal (`file:line`)

A `"0 errors in 24 h"` journal check (`journalctl -u mooniex-secretary -n 2` returning `-- No entries --`) had no teeth due to four compounding causes across the systemd unit files, Python stdio buffering, logger configuration, and silent `except` blocks:

1. **Buffered Python `stdout` without `-u` / `PYTHONUNBUFFERED=1` and no `StandardOutput=` / `StandardError=` directives in unit files or drop-ins**:
   - The base unit files (`state/contabo-blueprint-20260924/systemd-mooniex-units/mooniex-secretary.service:6-16` and `state/contabo-blueprint-20260924/systemd-mooniex-units/mooniex-secretary-waker.service:6-15`) and existing drop-ins (`deploy/systemd/mooniex-secretary.service.d/no-zai.conf:9-10`, `deploy/systemd/mooniex-secretary.service.d/org-db.conf:18-21`, and `deploy/systemd/mooniex-secretary-waker.service.d/org-db.conf:17-20`) invoke `/usr/bin/python3` and `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` without `-u`, without `Environment=PYTHONUNBUFFERED=1` (contrast `deploy/systemd/mooniex-watchdog.service:21` and `runners/secretary_server.py:844`), and without explicit `StandardOutput=journal` / `StandardError=journal`.
   - Under systemd, stdout is a non-TTY stream socket (`AF_UNIX`), so CPython defaults `sys.stdout` to 8 KiB block-buffering. In addition, the Infisical launcher (`tools/infisical_setup.py:910-923`) prints `[infisical] running ...` to `sys.stderr` without `flush=True` immediately before replacing the process image via `os.execvpe()` (`tools/infisical_setup.py:923`).
   - Sparse startup-only output (`runners/secretary_server.py:1704-1705` logged only once at startup and nothing while idle; `runners/secretary_waker.py:354-356, 388-389` logged once at startup and nothing on empty ticks every 30s) plus Contabo's journal vacuuming (`docs/ops/contabo-hq-migration-plan-2026-09-23.md:101`) leaves `journalctl -u mooniex-secretary -n 2` with `-- No entries --`.

2. **`stdout`/`stderr` routing and file logger configuration**:
   - Both services log through `lib/logger.py:47-72` (`get_logger`), called by `runners/secretary_server.py:800-804` (`get_logger("secretary")`) and `runners/secretary_waker.py:112-116` (`get_logger("secretary_waker")`).
   - `get_logger` configures a lazy rotating file handler (`_LazyRotatingFileHandler`, `lib/logger.py:57-65`) writing to `LOG_DIR / f"{name}.log"` (`lib/logger.py:15, 49`, `/var/log/mooniex/secretary.log` on Contabo when `ORG_LOG_DIR=/var/log/mooniex` is set in the base unit) and a `StreamHandler(sys.stdout)` (`lib/logger.py:67-70`), while setting `logger.propagate = False` (`lib/logger.py:55`, which also blocked pytest `caplog` from capturing records on the root logger).
   - `runners/secretary_server.py:1601-1602` (`Handler.log_message`) overrides `BaseHTTPRequestHandler.log_message` to route HTTP access logs into `_log().info(...)` instead of `sys.stderr`.
   - `runners/secretary_server.py:1109-1110` (`_run_claude_once`) captures child `claude` subprocess `stdout` and `stderr` into pipes (`subprocess.PIPE`) rather than letting child stderr flow to the unit's stderr/journal.
   - `runners/relay_mcp_server.py:110` calls `get_logger("relay", stdout=False)` so MCP stdio traffic is not corrupted, writing only to `relay.log`.

3. **Caught `OSError` and `Exception` blocks that swallowed errors silently**:
   - `lib/logger.py:42-43` (`_LazyRotatingFileHandler._open`): `except OSError: pass` silently swallowed symlink creation/unlink errors on `<role>_latest.log`.
   - `runners/secretary_server.py:997-998` (`_claude_auth_status`): `except (OSError, ValueError, KeyError, TypeError):` returned `(False, ...)` without logging when `~/.claude/.credentials.json` was missing, unreadable, or malformed.
   - `runners/secretary_server.py:1003-1004` (`_claude_auth_status._as_float`): `except (TypeError, ValueError): return None` silently swallowed non-numeric expiry fields.
   - `runners/secretary_server.py:1031-1032` (`_claude_auth_available`): `except Exception: return False` silently swallowed unexpected exceptions.
   - `runners/secretary_server.py:1121-1122, 1125-1126` (`_run_claude_once`): `except ProcessLookupError: pass` (an `OSError` subclass) and `except subprocess.TimeoutExpired:` during `SIGKILL` cleanup swallowed errors without logging.
   - `runners/secretary_server.py:1172-1173` (`_extract_api_error`): `except (json.JSONDecodeError, TypeError): return None` swallowed non-JSON stdout on failed `claude` runs without logging.
   - `runners/secretary_server.py:1496-1499, 1522-1526` (`_download_image`): caught `requests.exceptions.Timeout`, `requests.exceptions.RequestException`, `OSError` (on `dest.write_bytes`), and `Exception` and returned failure strings without logging to `_log()`.
   - `runners/secretary_server.py:1569` (`cleanup_staging_dir`): `shutil.rmtree(staging_dir, ignore_errors=True)` silently ignored all `OSError`s when removing per-turn image staging directories.
   - `runners/secretary_server.py:1628-1630` (`Handler.do_POST`): `except json.JSONDecodeError:` returned HTTP 400 without logging.
   - `runners/secretary_server.py:1708-1709` (`main`): `except KeyboardInterrupt: pass` exited without logging shutdown.
   - `runners/secretary_waker.py:135-136, 139-141` (`_try_lock`): caught `OSError` on `os.open` and `fcntl.flock` and returned `None` silently, causing `tick()` (`runners/secretary_waker.py:342-344`) to misreport lock-file permission/open `OSError`s as `"previous tick still in flight -- skipping"`.
   - `runners/secretary_waker.py:150-151` (`_unlock`): `except OSError: pass` silently swallowed errors on `os.close(fd)`.
   - `runners/secretary_waker.py:178-179` (`_peek_with_paths`): `except Exception: continue` silently skipped unreadable or corrupt `*.json` inbox letters.
   - `runners/secretary_waker.py:194-195` (`_load_failcounts`): `except Exception: return {}` silently swallowed `OSError` / corrupt JSON when reading `failcounts.json`.
   - `runners/secretary_waker.py:313-328` (`_invoke_secretary`): caught `requests.RequestException`, `ValueError`, and `(KeyError, IndexError, TypeError)` without logging inside `_invoke_secretary`.

---

## 2. Changes Made

- **`deploy/systemd/mooniex-secretary.service.d/journal.conf`** (new):
  Adds `[Service]`, `StandardOutput=journal`, `StandardError=journal`, and `Environment=PYTHONUNBUFFERED=1`. Kept in a separate `journal.conf` drop-in (like `no-zai.conf`) so `org-db.conf` remains byte-for-byte identical to the W1.8 design pinned by `tests/test_w18_contabo_consumers.py:360-383`.
- **`deploy/systemd/mooniex-secretary-waker.service.d/journal.conf`** (new):
  Adds `[Service]`, `StandardOutput=journal`, `StandardError=journal`, and `Environment=PYTHONUNBUFFERED=1` for `mooniex-secretary-waker.service`.
- **`lib/logger.py`**:
  - Logs `OSError` in `_LazyRotatingFileHandler._open()` to `sys.stderr` (with `flush()`) instead of `pass`.
  - Enables `logger.propagate = True` so pytest's `caplog` fixture captures records emitted via `get_logger(...)`.
  - Replaces static `logging.StreamHandler(sys.stdout)` with `_StdoutStreamHandler` that binds `self.stream = sys.stdout` on `emit()`/`flush()`, ensuring `capsys` captures stdout logs even when module-level `_LOGGER` instances were cached in an earlier test.
- **`runners/secretary_server.py`**:
  - Emits `"secretary started — listening on %s:%s (max_concurrent=%s workdir=%s)"` at startup in `main()`.
  - Logs a warning/error line on every previously silent `OSError`/exception in `_claude_auth_status`, `_claude_auth_available`, `_run_claude_once`, `_extract_api_error`, `_download_image`, `cleanup_staging_dir`, `Handler.do_POST`, and `main`, with zero secret values in any log line (credential parse errors log only the exception class name, never file contents or token values).
- **`runners/secretary_waker.py`**:
  - Emits `"secretary started (secretary_waker poll=%ss max_batch=%s once=%s)"` at startup in `main()`.
  - Logs a warning/error line on every previously silent `OSError`/exception in `_try_lock`, `_unlock`, `_peek_with_paths`, `_load_failcounts`, and `_invoke_secretary`.
- **`scripts/test_secretary_server.py` & `scripts/test_secretary_waker.py`**:
  - Added unit tests verifying both `journal.conf` drop-in files, the `"secretary started …"` startup log line, and caught `OSError`/exception log lines through both `caplog` and `capsys`, including assertions that secret values (`SECRETARY_API_KEY` and OAuth token material) never appear in any log output.

---

## 3. Contabo Root Commands (for PH Run Card — NOT Executed)

```bash
install -d -m 755 \
  /etc/systemd/system/mooniex-secretary.service.d \
  /etc/systemd/system/mooniex-secretary-waker.service.d

install -m 644 \
  /opt/MoonieXHQ/Agents/Core/deploy/systemd/mooniex-secretary.service.d/journal.conf \
  /etc/systemd/system/mooniex-secretary.service.d/journal.conf

install -m 644 \
  /opt/MoonieXHQ/Agents/Core/deploy/systemd/mooniex-secretary-waker.service.d/journal.conf \
  /etc/systemd/system/mooniex-secretary-waker.service.d/journal.conf

systemctl daemon-reload
systemctl restart mooniex-secretary.service mooniex-secretary-waker.service
journalctl -u mooniex-secretary.service -u mooniex-secretary-waker.service -n 20 --no-pager
```

### Tmux-Holding Unit Check (`CLAUDE.md §Contabo tmux`)

- **Neither restart touches a tmux-holding unit.**
- Evidence from the repo:
  - `state/contabo-blueprint-20260924/systemd-mooniex-units/mooniex-secretary.service:6-16` and `deploy/systemd/mooniex-secretary.service.d/org-db.conf:18-21` run `secretary_server.py` (`ThreadingHTTPServer`) directly as `Type=simple` under `User=secretary`.
  - `state/contabo-blueprint-20260924/systemd-mooniex-units/mooniex-secretary-waker.service:6-15` and `deploy/systemd/mooniex-secretary-waker.service.d/org-db.conf:17-20` run `secretary_waker.py` directly as `Type=simple` under `User=secretary`.
  - `scripts/org-tmux-adopt.sh:3-5` and `tests/test_w18_contabo_consumers.py:856-871` (`test_restart_rule_watchdog_holds_no_tmux_and_has_no_killmode_process`) confirm that the tmux-holding unit is `mooniex-tmux.service` (which holds the `org` tmux server with `KillMode=process`), whereas `mooniex-secretary.service` and `mooniex-secretary-waker.service` hold no tmux server and are safe to `systemctl restart`.

---

## 4. Validation Performed & Commands for Review

Per the AGY Remote Worker Contract (`For AGY, use file tools only; leave shell validation to the review process`), no shell commands were executed during this run. All changes were verified by static inspection against existing test contracts (`tests/test_w18_contabo_consumers.py`, `tests/test_w19b_cutover_fixes.py`, `scripts/test_secretary_server.py`, `scripts/test_secretary_waker.py`, and `tests/test_sompong_route.py`).

Reviewers can run:

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest \
  scripts/test_secretary_server.py \
  scripts/test_secretary_waker.py \
  tests/test_w18_contabo_consumers.py \
  tests/test_w19b_cutover_fixes.py \
  tests/test_sompong_route.py
```

## Blockers

- (none)

## Skill learning

- `tests/test_w18_contabo_consumers.py:360-383` asserts exact line-for-line equality on `deploy/systemd/<unit>.service.d/org-db.conf`, while `:432-435` (`test_only_the_three_dropins_exist`) explicitly scopes its glob to `deploy/systemd/*/org-db.conf` so orthogonal drop-ins (`no-zai.conf`, `journal.conf`) do not conflict with W1.8 cutover tests. New systemd settings for these units should be placed in dedicated drop-in files rather than modifying `org-db.conf`.
