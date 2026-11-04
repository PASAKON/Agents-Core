# Run Watch driver

The timer reads the hub once per minute and manages only `runwatch-<host>`.

**One pinned Watch session per host (CEO 3 Nov).** The CEO pins the Watch session in
the Claude app, so it is never re-created and never closed for being idle:
- The name is `<host emoji> Watch Runs: <N><light>` (`🌐 Watch Runs: 0🔴`; winbox
  `Watch Runs: 0 idle`), with no id. A changed count or light is a typed `/rename`.
- The conversation is one uuid per host, kept in `driver.json` (`uuid`). The first
  start launches `claude --session-id <uuid>`; every later start launches
  `claude -r <uuid>` with the same `--remote-control <name>`. If claude has no stored
  transcript for the uuid (a first launch that died before its first message), the
  start uses `--session-id` again, because `-r` would fail.
- A host with no session starts one, with or without runs, and a live one is never
  stopped when idle (an idle session costs no tokens). The one kill is low memory:
  below `RUN_WATCH_KILL_AVAIL_MB` (350) the driver kills the tmux session, and the next
  tick resumes the same uuid once `RUN_WATCH_MIN_AVAIL_MB` (700) is free again. The
  gap between 350 and 700 keeps the kill and the start from flapping. A kill the driver
  chose is not counted as a death.
- Context stays small: when the transcript has grown by `RUN_WATCH_COMPACT_TOKENS`
  (60000) since the last compaction, estimated as bytes / 4, the driver types
  `/compact` instead of the next event line, only at a ready prompt; the event line
  follows on a later tick. `compact_base` in `driver.json` is the size at that moment.

A session started before this change has no `uuid`: the driver adopts it (renames it,
keeps it up, cannot compact it), and the first start after it exits creates the pinned
conversation. To switch at once an operator kills `runwatch-<host>`; the next tick starts it.

One unexpected exit permits one restart. A second exit in a row records a notice in
`state/steward/<host>/open.md` and stops starting for `RUN_WATCH_RETRY_S` (3600 s), then
tries again. A session that stays up `RUN_WATCH_STABLE_S` (600 s) clears earlier exits.
An unreachable hub changes nothing. Launch requires an existing tmux server and
700 MB MemAvailable. tmux `-N` also
prevents creating a server if the existing server exits during the tick.

Name updates take priority over batched Thai event summaries. Each tick types at
most one line, checks the empty, idle prompt twice, and retains undelivered events.
Summaries are at most 100 characters, with `+N more` for omitted events.
Every `RUN_WATCH_*` environment setting is forwarded to the launched watcher.
The watcher uses only Bash, user settings (no project hooks), and a standalone role system prompt with strict status-only dispatch.
When no runs remain, batches release immediately, preserving rename priority and one typed action per tick. Events wait in `pending_out` for as long as the prompt is not ready.
External runners (`codex`/`agy`) whose pid and tmux session are gone skip `RUN_WATCH_REPORT_GRACE_S` and read as `dead` immediately (after `RUN_WATCH_SPAWN_GRACE_S`) when `<worktree>/docs/reports/<task-id>/REPORT.md` is absent.
Any follower batch containing a `dead` or `failed` event releases into `pending_out` immediately without waiting for `RUN_WATCH_BATCH_S`, keeping rename priority and one typed action per tick.

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
Environment=RUN_WATCH_QUIET_S=60 RUN_WATCH_BATCH_S=30
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
