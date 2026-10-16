# Run Watch driver

The timer reads the hub once per minute and manages only `runwatch-<host>`.
The first active run starts the watcher; one unexpected exit permits one restart.
A second exit records a notice in `state/steward/<host>/open.md` until the next
run cycle. Once all runs end, the watcher closes after 600 seconds by default.
An unreachable hub changes nothing. Launch requires an existing tmux server and
700 MB MemAvailable (`RUN_WATCH_MIN_AVAIL_MB` overrides this). tmux `-N` also
prevents creating a server if the existing server exits during the tick.

Name updates take priority over batched Thai event summaries. Each tick types at
most one line, checks the empty, idle prompt twice, and retains undelivered events.
Summaries are at most 100 characters, with `+N more` for omitted events.
Every `RUN_WATCH_*` environment setting is forwarded to the launched watcher.
The watcher uses only Bash, user settings (no project hooks), and a standalone role system prompt with strict status-only dispatch.
When no runs remain, batches release immediately; stopping defers for up to three flush ticks (`reason=flush`), preserving rename priority and one typed action per tick.

Install after the code lands (operator Run card):

```sh
cp deploy/systemd/run-watch-driver.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now run-watch-driver.timer
```

Do not enable PrivateTmp: the root tmux socket is under `/tmp`. This oneshot is
a tmux client; stopping/restarting its unit does not terminate watcher sessions.

For faster testing, create `/etc/systemd/system/run-watch-driver.service.d/test.conf`:

```ini
[Service]
Environment=RUN_WATCH_QUIET_S=60 RUN_WATCH_CLOSE_AFTER_S=60
```

Run `systemctl daemon-reload`. New watcher launches inherit these values; an
already running watcher retains its launch environment. Remove the drop-in and
reload to restore defaults. No test drop-in is shipped.

State lives in `state/run-watch/<host>/driver.json`, alongside `ack.json`.
`RUN_WATCH_STATE_DIR` uses the same host-directory resolution as `run_watch.py`;
when it names an ack JSON file, driver state is its sibling `driver.json`.
Driver state is replaced atomically and includes the persisted follower batch and
pending output. Logs: `journalctl -u run-watch-driver` (one line per tick, no DSN).
Preview with `bash scripts/hub/org-python.sh tools/run_watch_driver.py tick --dry-run`:
it reads current status and pane readiness but writes no state or keys.

Rollback:

```sh
systemctl disable --now run-watch-driver.timer
systemctl stop run-watch-driver.service
tmux kill-session -t runwatch-contabo
rm /etc/systemd/system/run-watch-driver.service /etc/systemd/system/run-watch-driver.timer
# If created for testing, also remove run-watch-driver.service.d/test.conf.
systemctl daemon-reload
```
