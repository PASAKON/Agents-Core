# Live sessions — who can I SendMessage to right now

`python -m tools.live_sessions` prints ONE list of the live C-level and Project Head sessions on Contabo, Mac and
winbox (~1.3k chars for 15 rows, under 1k tokens) so a sender does not call ListAgents (83 rows,
~70 dead, ~5k tokens) or send to a name from memory. Built for task-9c563bea (CEO question 13 Oct).

## Data path
Claude Code writes `<config>/sessions/<pid>.json` per live process (skip `<pid>.<hash>.key`).
`ensure_publisher()` runs from `scripts/hook-inbox.py` on every prompt of a C-level session (CXO_ROLE
set, no WORKER_TASK_ID) and starts `publish --loop` if none is alive. The loop reads the registry
(alive = pid exists AND start time matches `procStart`, so a reused pid is not alive) and writes the hub
tables `live_sessions` (host, uuid) and `live_hosts` (host). The reader joins them with the hub's own
clock, so host clock skew never shows. Tables are created by `PG_SCHEMA` on the next `db.init()`.

## Blast radius
- One standalone process per host. No MCP-server thread, nothing inside a session.
- Hub writes: one transaction when the registry changes (checked every 5 s), plus one per minute.
- The hook adds one open + non-blocking flock of `state/locks/live_sessions.publisher.lock` per C-level
  prompt (~0.1 ms) and a spawn at most once per 60 s (`state/locks/live_sessions.spawned`).
- Fails open: hub down or no ORG_DB_URL means one line in `state/live_sessions.log` and a 30 s retry;
  the hook swallows every error and prints nothing (its stdout is the model's context).

## Reading it
`scripts/live-sessions.sh [--all] [--id <sid>] [--json] [--local]` (org-python, infisical banner
filtered). Without a hub route, or to see this box only: `--local`. Windows: run
`windows_hub_prefix(ROOT)` (scripts/lib/cxo_mcp_config.py) + `python -m tools.live_sessions`.
Rows: `running|idle  <address>`, running first, then host, C-levels before Project Heads, then name.
Workers show only with `--all` (a PH was hidden until 2026-10-14, PH OrgRestructure). Send with
`SendMessage(to=<text after the status>, verbatim)`. "N agents are named X" → re-send with the `[ref]`
the error marks active. The COO's address is `SomPong` (its own name returns "not found"; CTO 13 Oct) while
it runs under an old-style name; from its first start with the CEO's 14 Oct names it is `COO (SomPong)`.
C-level names (CEO 2026-10-14) are `<ROLE> (<Name>)`, no machine, no #id: the role and the id come from the
launcher's tmux name `<role>-<sid>` in the session record, else from the name plus the session UUID's last
8 hex (the launchers make it the short id). One name on two rows (a Mac and a Contabo `CTO (Kavin)`) adds a
`same name on N rows` line with each host and sid: take the `[ref]` from the ListAgents row whose
`tmux` ends `-<sid>`, or use `send_to_cxo(role=…)`, which routes by tmux name, not display name.
A session in any other tmux (a worker's `wd-<sid>`) never takes a C-level or PH role from its own name:
it is listed as `unknown` (M8, 2026-10-14). A row no launcher tmux confirms (winbox, a bare terminal, an old
publisher) still prints, and a `name only (no launcher tmux confirms the role): <host> #<sid>` line names it;
the `same name` line marks each row `tmux-confirmed` or `name only`. Stored in `live_sessions.verified`.
Header per host: `contabo 3 (+5 PH, +1 workers, 4s)` (3 C-levels; workers = neither C-level nor PH); stale: `winbox none (no publisher since 10-12 21:03)`;
stale with a pull error: `winbox unreachable (ssh timeout) since 18:40`. Hub down: one line, exit 0.

## winbox
winbox has no venv, so no hub route. Contabo's loop pulls its registry over ssh once a minute
(`hosts.contabo.live_sessions_pull: [winbox]`, ssh target `hosts.winbox.ssh`): `ssh -o BatchMode=yes
-o ConnectTimeout=5 winbox powershell -NoProfile -NonInteractive -EncodedCommand <b64>`, 25 s cap.
On failure the rows stay, `live_hosts.error` is set, `published_at` is kept. If winbox's key becomes
forced-command-only (issue #238) the pull fails and the reader shows "unreachable".

## Rollout
`git pull` on each host; the next C-level prompt starts the loop (a hook script is read from disk on
every prompt). The CTO applies `GRANT SELECT ON live_sessions, live_hosts TO org_coo;` by hand
(`deploy/hub/org_coo_role.sql` is not in this base). Nothing is written to the hub before that run.

## Stop
`ORG_LIVE_SESSIONS=off` stops the hook spawning. Stop the loop with
`pkill -f 'tools.live_sessions publish --loop'`. The lock file also holds its pid for reading; never
feed a file's content to `kill`. The loop exits by itself, code 0, when `tools/live_sessions.py`
changes on disk, and the next prompt respawns it on the new code.

## Hostile input
The loop runs as root over paths other accounts can write (`state/` is group-writable by the
secretary service; the `sompong` user writes its own registry dir). So: the lock, the spawn stamp and
the log open with O_NOFOLLOW + O_NONBLOCK and must be regular single-link files, else no spawn (log:
child stderr goes to /dev/null). Registry files must be regular, not a symlink, at most 64 KiB. Names
lose control, bidi and line-separator characters and are cut at 120 characters; status is only
running, idle or unknown. A hook run from a worktree never starts a publisher, only the main checkout.
