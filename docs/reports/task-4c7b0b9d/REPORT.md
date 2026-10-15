# REPORT — task-4c7b0b9d: the secretary units leave a trace in the journal

Branch `agent/devops_engineer-task-4c7b0b9d`, on top of `c0df4ef7`. Nothing installed, reloaded or restarted; nothing
pushed. Every fact below was measured on Contabo (`vmi3371421`) on 2026-10-15 between 14:15 and 14:35 CEST, read-only.
"old :N" means the line in `c0df4ef7`.

## 1. Why `journalctl -u mooniex-secretary` says "-- No entries --"

It is **not** a redirect and **not** Python buffering. Four causes stack up:

1. **Output does reach journald.** `systemctl show` gives `StandardOutput=journal`, `StandardError=inherit` for both
   units (systemd defaults; no `Standard*=` in any drop-in). fd 1 and fd 2 of `python` pid 2564201 (secretary) and pid
   2564204 (waker) are sockets whose peers are `/run/systemd/journal/stdout` (`ss -xp`). The `+infisical_setup.py run …
   setpriv …` ExecStart keeps those fds: `tools/infisical_setup.py:923` is an `os.execvpe`, and setpriv execs. The same
   drop-in shape on `mooniex-watchdog` has 1495 lines in its journal. The logger flushes: `lib/logger.py:68`
   `logging.StreamHandler(sys.stdout)` calls `flush()` after every record. The new subprocess test shows the start line
   arriving on a pipe while the server keeps running, with `PYTHONUNBUFFERED` unset.
2. **The start lines were rotated out.** Both units: `ActiveEnterTimestamp=Thu 2026-10-01 23:56:50 CEST`, `NRestarts=0`.
   The journal's oldest entry is `2026-10-09 04:40:22 CEST` (512.3M on disk, `/etc/systemd/journald.conf` has an empty
   `[Journal]` section, so the defaults apply). The file logs agree: the last line of
   `/home/secretary/runtime/logs/secretary.log` is `[2026-10-02T04:56:53] INFO secretary listening …`, and
   `secretary_waker.log` ends with `secretary_waker starting` at the same moment. (The file times are Bangkok time, the
   same instant as 23:56:53 CEST.)
3. **When idle they write nothing.** The secretary logs once at start (old `runners/secretary_server.py:1704`) and once
   per HTTP request (old :1601 `log_message`). Its last request in the file log is `2026-10-01T16:01:26`, before the
   restart. The waker's `_tick_locked` returns at old `runners/secretary_waker.py:355` (`if not pending: return 0`)
   without a line.
4. **Swallowed exceptions, and one is firing right now.** `state/inbox/secretary-sompong/20261002T221744067206Z-cto-4bb20df8.json`
   is `root:secretary` mode `600`, mtime 2026-10-03 00:17 CEST. As user `secretary`, reading it raises `PermissionError`
   (root can read and parse it). Old `runners/secretary_waker.py:178` `except Exception: continue` drops it with no line,
   every 60 s, for 12 days. A CTO report has not reached the CEO, and no log says so. The mode comes from
   `lib/mailbox.py:151`: `tempfile.mkstemp` creates the file 0600, and `:155` `os.replace`s it with no chmod. So every
   letter a root-run C-level sends is unreadable to `secretary` (see §6).
   This is also the case `docs/ops/state-dir-perms.md` watches for. Its 2026-10-14 baseline (:23, "0 permission
   errors" in `journalctl -u mooniex-secretary -u mooniex-secretary-waker --since -7d`) was read off a journal that
   could not hold one, while this PermissionError was firing every 60 s.

A fifth cause would have broken the "0 errors" check even with lines in the journal. The stdout format is
`lib/logger.py:69` `"[name] %(message)s"`, with no level word, and journald stores every stdout line at PRIORITY=6. I
measured it on a unit that uses the same logger. The branch_poller WARNING `artefact gate REFUSED … task-2e0718d9`
(file log 2026-10-15T13:29:42) is `PRIORITY=6` in the mooniex-watchdog journal, and `journalctl -u mooniex-watchdog -p err`
returns 0 of 1495 lines.

## 2. What changed

| Commit | What |
|---|---|
| `130129f7` ops | `deploy/systemd/mooniex-secretary.service.d/journal.conf` and `…-waker.service.d/journal.conf`: `StandardOutput=journal`, `StandardError=journal`, `SyslogIdentifier=<unit>`, `SyslogLevelPrefix=yes`, `Environment=PYTHONUNBUFFERED=1` |
| `99e78bdd` secretary | `use_journal_levels()` (`runners/secretary_server.py:840`): when the handler's stream **is** the journal (`JOURNAL_STREAM` dev:ino matches its fd, :823), each line gets a `<N>` priority prefix and the level name. Elsewhere the format is unchanged. Both runners use it. Start line `secretary started (pid uid python bind)` (:1814), written before the API-key check; the refusal also logs at ERROR (:1449). The waker's start line gains the pid (`secretary_waker.py:408`). One line per exception that used to be swallowed (table below). Tests. |
| `2505d572` secretary | **Beyond the brief, own commit so it can be dropped alone.** An hourly heartbeat: `secretary heartbeat: up Ns, K turn(s) in flight` (`_Server.service_actions`, :1793–:1809, no thread) and `secretary_waker heartbeat: up Ns, T tick(s), L letter(s) sent` (:422). Why: the start line alone does not make a 24 h check able to fail. An idle unit writes nothing after it, and this box keeps about 6 days of journal. |

Log lines carry no secret values. Exceptions are logged by class plus errno and strerror (`_exc_brief`, :857), never
`str(exc)`. A requests error's text holds the full URL, and an image URL can be a signed link. The credential file and
letter bodies are never echoed. Tests assert both points.

### Exception sites

| Site (old line) | Was | Now |
|---|---|---|
| server :997 credential read (OSError/ValueError/KeyError/TypeError) | returned False, nothing logged | WARNING, class only (new :1058) |
| server :1031 `_claude_auth_available` | `except Exception: return False` | WARNING (:1093) |
| server :1121 `ProcessLookupError` on SIGKILL | `pass` | INFO (:1185) |
| server :1125 second `TimeoutExpired` | output dropped silently | WARNING (:1189) |
| server :1496/:1498 image download | reason went to the model only | WARNING, class only, no URL (:1564/:1567) |
| server :1522 image save `OSError` | same | ERROR with errno (:1592) |
| server :1525 image last-resort net | same | ERROR, class only (:1597) |
| server :1569 `rmtree(ignore_errors=True)` | swallowed | same best effort through `onexc`/`onerror`, WARNING per failure; FileNotFoundError stays quiet (already gone) (:1649) |
| waker :135 lock `os.open` | returned None, then tick said "still in flight" | ERROR (:144) |
| waker :139 `flock` | returned None | ERROR unless EWOULDBLOCK/EAGAIN, which is plain contention (:151) |
| waker :150 `os.close` | `pass` | WARNING (:162) |
| waker :178 unreadable letter | `continue` | ERROR every tick while it stays (:193). mailbox writes by atomic rename, so this is never a half-written file. |
| waker :194 failcounts | `{}` on any error | FileNotFoundError stays quiet (no failures yet); anything else WARNING (:213) |
| server :1003 `_as_float`, :1172 `_extract_api_error` | parse probes returning None | unchanged: "not a number / no API error here", not errors. The caller logs rc + stderr (old :1317). |
| server :1200, :1676; waker :313/:321/:326, :394 | already logged | unchanged |

`_claude_auth_status` and `_claude_auth_available` have no production caller, only tests. Their new lines are there so
the inventory is complete.

## 3. Tests

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest scripts/test_secretary_server.py scripts/test_secretary_waker.py -o addopts="" -q`
  → **127 passed** (109 before, plus 18 new: 10 server, 8 waker). `99e78bdd` alone: 124 passed.
- New: start line before refusal (caplog); start line read off a **pipe while the server runs** (subprocess,
  `PYTHONUNBUFFERED` unset, `ORG_LOG_DIR` and `SECRETARY_MCP_CONFIG` in tmp, no secret in output); journal priority
  prefix on and off; image save OSError; request error log without URL or token; staging cleanup failure and
  already-gone; credential parse error without content; heartbeat once per interval (server and waker); waker start
  line; corrupt letter; lock open failure; contention not an error; close failure; failcounts missing vs corrupt.
- Drop-ins: `systemd-analyze verify` on scratch copies (blueprint unit + all drop-ins) returns rc 0 for both units with
  no warnings. Control: a typo key in a scratch drop-in in the same directory is reported, so `verify` does read it.
- `<N>` → PRIORITY under real journald, probed with `systemd-cat -t task-4c7b0b9d-probe` (two lines in the system
  journal under that tag): ERROR → `PRIORITY=3 MESSAGE=[t4c7b0b9d_probe] ERROR probe error line`, INFO → `PRIORITY=6`,
  and `journalctl -p err` counts 1.

## 4. Install on Contabo: root commands (NOT run, for the PH's Run card)

The drop-ins work alone. The code changes (start line, priorities, exception lines, heartbeat) reach the units only
after the PR is merged **and** the live checkout `/opt/MoonieXHQ/Agents/Core` is fast-forwarded, because both units run
from there. Order: merge → live tree ff → this card.

```bash
set -eu
REPO=/opt/MoonieXHQ/Agents/Core
# 0a. abort if either unit holds the tmux server or a pane (CLAUDE.md §Contabo tmux)
if { for p in $(pgrep -f '^tmux'); do tail -1 /proc/$p/cgroup; done
     for pp in $(tmux list-panes -a -F '#{pane_pid}' 2>/dev/null); do tail -1 /proc/$pp/cgroup; done
   } | grep -qE '/mooniex-secretary(-waker)?\.service$'; then
  echo "ABORT: a secretary unit holds tmux"; exit 1
fi
# 0b. abort if a claude turn is in flight (anything beside the python pid in the secretary's cgroup)
n=$(wc -l < /sys/fs/cgroup/system.slice/mooniex-secretary.service/cgroup.procs)
[ "$n" -le 1 ] || { echo "ABORT: mooniex-secretary has $n processes, a turn is in flight"; exit 1; }
# 0c. the live tree carries the change
grep -q 'def use_journal_levels' "$REPO/runners/secretary_server.py" || { echo "ABORT: live tree lacks the change"; exit 1; }
# 1. install + reload + restart
install -m 0644 -o root -g root "$REPO/deploy/systemd/mooniex-secretary.service.d/journal.conf" \
  /etc/systemd/system/mooniex-secretary.service.d/journal.conf
install -m 0644 -o root -g root "$REPO/deploy/systemd/mooniex-secretary-waker.service.d/journal.conf" \
  /etc/systemd/system/mooniex-secretary-waker.service.d/journal.conf
systemctl daemon-reload
systemctl restart mooniex-secretary mooniex-secretary-waker
# 2. verify
sleep 5
systemctl show mooniex-secretary mooniex-secretary-waker -p ActiveState -p StandardError -p SyslogIdentifier
journalctl -u mooniex-secretary -n 5 --no-pager
journalctl -u mooniex-secretary-waker -n 5 --no-pager
```

Expected right after: `mooniex-secretary[…]: [infisical run] Agents-Core/prod as contabo: ORG_DB_URL -> …` (secret
**names** only, as today), `[secretary] INFO secretary started (pid=… uid=… python=3.12.3 bind=172.18.0.1:8643)`,
`[secretary] INFO secretary listening …`, and `[secretary_waker] INFO secretary_waker starting (pid=…)`. **Within 60 s
the waker will also log `ERROR unreadable letter 20261002T221744067206Z-cto-4bb20df8.json skipped: PermissionError
(errno 13: Permission denied)`, at PRIORITY 3, every 60 s, until that letter is dealt with** (§6). That is the check
working, not a regression. It also matches the `grep -ciE "permission denied|EPERM|EACCES"` check in
`docs/ops/state-dir-perms.md:39`, so that check will read non-zero until the letter is handled.

Rollback: `rm /etc/systemd/system/mooniex-secretary.service.d/journal.conf /etc/systemd/system/mooniex-secretary-waker.service.d/journal.conf
&& systemctl daemon-reload && systemctl restart mooniex-secretary mooniex-secretary-waker`. Code: revert `2505d572`
and/or `99e78bdd`, then ff the live tree.

### Does either restart touch a tmux-holding unit?

- **From the repo alone: unknown.** Neither runner calls tmux. The secretary runs `claude`, which spawns
  `runners/relay_mcp_server.py`. That server only runs `tmux ls` (:609), and it dispatches `spawn_c_level` through a queue
  or the mesh (:1143–:1197). I did not trace the mesh transport on Contabo to its end, so I cannot rule out from code a
  future tmux server starting inside `mooniex-secretary.service`.
- **Measured 2026-10-15 14:31 CEST: no.** The one tmux server (pid 2818096) is in `org-tmux.scope`, and so are 10 of 10
  panes. The secretary's cgroup holds 1 process (python 2564201), the waker's holds 1 (python 2564204).
  `/etc/tmux.conf` has the org-tmux-adopt hook. Step 0a re-checks this at run time and aborts otherwise.

## 5. The 24 h check, once this is live

```bash
# the logging path is alive first (about 24 per unit per day)
journalctl -u mooniex-secretary        --since -24h -o cat | grep -c 'secretary heartbeat:'
journalctl -u mooniex-secretary-waker  --since -24h -o cat | grep -c 'secretary_waker heartbeat:'
# only then trust a zero here
journalctl -u mooniex-secretary -u mooniex-secretary-waker --since -24h -p warning -o cat | wc -l
```

Without `2505d572` (heartbeat), the first two lines have nothing to count, and the check is back to unable to fail
after the start line ages out.

## 6. Outside my declared paths: for the CTO

1. **`lib/mailbox.py:151`/`:155` writes letters 0600.** Root-sent letters are unreadable to `secretary` (and to any
   non-root reader). Proposed fix: `os.fchmod(fd, 0o640)` before the replace (the box is setgid group `secretary`). It
   needs `lib/mailbox.py` in a task's touches; the guard refused `lib/`.
   **The stuck letter is a decision, not a chmod:** once it is readable, the waker runs a claude turn and sends a 12-day-old
   CTO report to the CEO on Telegram. The other choice is moving it to `failed/` as root. That is the PH's or CTO's call.
   I did not touch it and did not read its content.
2. **`lib/logger.py:69`: every other `get_logger` unit has the same blind spot** (watchdog/branch_poller measured above).
   `use_journal_levels` could move into `lib/logger.py` and run inside `get_logger` when stdout is the journal. That
   needs `lib/` touches, and it changes what `-p` shows on those units, so their owners should hear about it first.
3. Existing lines left as they were: on failure the secretary logs claude's `stderr[:500]` / `stdout[:500]` (old
   :1317, :1323). The `image N: download failed ({e})` *reason* still carries the URL into the model prompt (old :1499;
   that goes to the model, not the journal). I did not check whether claudeflow sends signed URLs.
4. `PYTHONUNBUFFERED=1` also reaches the `claude` children and their MCP servers (harmless; the relay MCP entry already
   sets it). `SyslogIdentifier` changes the journal tag from `python`/`python3` to the unit name. Nothing in the repo
   filters on the old tag (grep).

## Not checked / risk

- Nothing installed. Real-unit behaviour is inferred from `verify` + the `systemd-cat` probe + the live fd/cgroup reads.
- That `JOURNAL_STREAM` survives `+infisical_setup.py run` → setpriv → python is read from code
  (`tools/infisical_setup.py:912` passes `{**os.environ, **secrets}`), not observed. I did not read the live process
  environment, because it holds secrets. If the variable does not pass, lines still reach the journal, at PRIORITY 6
  with no level word, the same as today.
