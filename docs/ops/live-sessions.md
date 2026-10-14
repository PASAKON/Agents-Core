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
it runs under an old-style name; under the 15 Oct names it is `COO SomPong` (after the host emoji).
C-level names (CEO 2026-10-15) are `<ROLE>#<id3> <topic>` (topic `Main` by default; the COO has no org sid, so no
`#<id3>`): the role and the id come from the launcher's tmux name `<role>-<sid>` in the session record, else from
the name plus the session UUID's last 8 hex (the launchers make it the short id). One name on two rows (the
older `CTO (Kavin)` of a Mac and a Contabo session, which both read as one name) adds a
`same name on N rows` line with each host and sid: take the `[ref]` from the ListAgents row whose
`tmux` ends `-<sid>`, or use `send_to_cxo(role=…)`, which routes by tmux name, not display name.
A session in any other tmux (a worker's `wd-<sid>`) never takes a C-level or PH role from its own name:
it is listed as `unknown` (M8, 2026-10-14). The launcher's tmux name CLAIMS a role; it proves nothing about
who started that tmux, so the list says "claimed", never "confirmed". SomPong's fixed tmux `sompong` claims
`coo` only for the session whose UUID the launcher wrote to `state/locks/coo-<sid>.uuid` (M10).
A row no launcher tmux claims ends in `  [name only]` on its own line (strip it before sending), and one
note line explains the mark. On Contabo and the Mac, where every launcher starts a tmux, such a row also
loses its C-level or PH role (`unknown`, so role routing never lands on it) but still prints, counted in the
header as `+N name only`; on winbox (no tmux) it keeps the role the name gives. The `same name` line marks
each row `tmux-claimed` or `name only`. Stored in `live_sessions.verified`.
Names off the CEO's rule (M10, checked by `lib/session_names.rule_problem`: the host emoji, then the shape in the
table below, the id3 matching the session, the body after the emoji at most `NAME_BODY_MAX` = 32 characters) each
get a `name off-rule: "<name>" (<host> #<sid>): <why>` line, at most 5 and then `+N more`. A leading state glyph
(`⏸`) is allowed. A name still in the shape of 14 Oct (`CTO (Kavin) — topic`, `PH#7cf (CTO) - Project`,
`Dev#49b - Head: job`, `MAC CTO #671f688f (topic)`) is read as before, so the session is still found, and
is off-rule with the reason `old shape`; the rename service rewrites it (sweep, below).

| kind | shape (after the host emoji) | example |
|---|---|---|
| C-level | `<ROLE>#<id3> <topic>` (topic `Main`) | `🌐 CTO#c34 Main` |
| COO | `COO <topic>` (no org sid, so no id; topic = persona) | `🌐 COO SomPong` |
| Project Head | `PH#<id3> <Project>[+<Project>]` | `🌐 PH#7cf OrgRestructure` |
| Claude worker | `<Short>·<M>#<id3> <Head>: <job>` (M = O, S or H) | `🌐 Dev·S#49b Org: sparse worktrees` |
| Watch | `Watch#<id3> Runs: <N><light>` (🟢🟡🔴⚪) | `🌐 Watch#a1b Runs: 2🟢` |
| winbox worker | ASCII only, no emoji, `.` for `·`, `...` for `…` | `Dev.S#49b Org: sparse worktrees` |

`<Head>` is `short:` in `config/projects.yaml`, else the project's first 10 characters (Org, Spend, BlackLiq, Mimi).
The persona (Kavin, Ging) and a PH's lane are not in the name. A body over 32 characters is cut and ends in `…`.
One constant, `NAME_BODY_MAX` in `lib/session_names.py`, changes the limit; the tmux names (`cto-<id>`,
`project_head-<id>`, `wd-<id>`, `sompong`) never change. Writers: `clevel_name`, `ph_session_name`, `worker_name`,
`watch_name`; the launchers and `config.worker_session_name` call them, none builds a string by hand.
To fix them: the session runs `bash scripts/session-rename.sh "<job>"`, which sends a rename request over
`/run/rename-service/sock`, and the rename service (`tools/rename_service.py`, `deploy/systemd/rename-service.service`, Agents-Core #272)
types `/rename <rule name>` into that session's launcher tmux pane once its ❯ line is empty, never onto a
draft or a permission prompt. A request never reaches a worker (the sweep below does), and it ignores a PH with no `.project`/`.spawned_by` and a `sompong`
tmux whose session is not the one in `coo-<sid>.uuid`. It accepts a request only from a process whose
ancestor is that session's Claude process, running as the same uid (SO_PEERCRED): a session renames
only itself.
Every name starts with its host's emoji (CEO 2026-10-14): 💻 Mac, 🌐 Contabo, 🖥️ winbox, e.g. `🌐 CTO#c34 Main`,
`🌐 PH#f35 CookieRun`. The list prints it as part of the name (send it verbatim); parsing drops it first
(`lib/session_names.strip_host`, U+FE0F optional), so a name without one still resolves. The launchers take the
host from `self_host()` only; an unresolved host gets no emoji. Workers spawned on winbox get none (cmd.exe path).
Header per host: `contabo 3 (+5 PH, +1 workers, 4s)` (3 C-levels; workers = neither C-level nor PH); stale: `winbox none (no publisher since 10-12 21:03)`;
stale with a pull error: `winbox unreachable (ssh timeout) since 18:40`. Hub down: one line, exit 0.

## Rename service

`tools/rename_service.py` behind `scripts/session-rename.sh`, one per host, same code and same rules.

| | Contabo | Mac (M10c) |
|---|---|---|
| runs as | root (the sessions are root) | `gob` (the sessions are gob's; root would run code gob can edit) |
| unit | `deploy/systemd/rename-service.service`, hardened | `deploy/launchd/com.mooniex.rename-service.plist`, LaunchDaemon with `UserName` |
| socket | `/run/rename-service/sock` (RuntimeDirectory, 0755 root) | `~/.rename-service/sock` (dir 0700) |
| who is asking | SO_PEERCRED, ancestry from /proc | LOCAL_PEERPID + LOCAL_PEERCRED, ancestry from `ps` |
| log | `journalctl -u rename-service` | `~/Library/Logs/mooniex-rename-service.log` |

Sweep (M10d, then the 15 Oct shape; CEO 2026-10-15, retroactive to every live session): each pass, before the queue, the service looks at this host's live C-levels, PHs and Claude workers (`wd-<sid>`) and, for one whose name fails the rule (old shape, no or the wrong host emoji, a name typed by hand), queues the same job a request queues: the rule name with the topic the old name carried (`rebuild()`). The topic comes from the old name: the part after ` — `, the text in `( )` of `MAC CTO #id (topic)` (a leading `PH ` there is dropped), or the PH's project. A worker keeps its head and job; its role comes from its tmux name and its model letter from the model it already shows, else `policies/agents.yaml` (the service has no hub route, so it never reads the task row). `_one()` types it like any request: only into an empty prompt, never onto a draft or a running turn, retried on the next pass. A name that cannot be rebuilt on the rule is logged once (`skip  <box>: …`); a box already decided under the same pid and name is not looked at again (memory only, so a restart tries once more), so a name is fixed once or reported once, never in a loop. The `ceo` and unknown roles are never touched. Log lines: `sweep    <box>: <old> -> <new>`.

Install, after the PR lands. Contabo: a Run card (bytes in docs/plans/org-restructure-STATUS.md). Mac, the CEO
pastes one line in a Mac terminal (no Run Inbox executor there yet), after a smoke test on a throwaway pane.
The line is pinned: the Mac checkout must already hold `<MERGE_SHA>` (main after the PR lands; reach it with
the Mac's own sync first) and carry no local change under the code the daemon runs. No `git pull` in it:

```
cd /Users/gob/MoonieXHQ/Agents/Core && git merge-base --is-ancestor <MERGE_SHA> HEAD && git diff --quiet HEAD -- tools lib config policies deploy && sudo install -m 0644 -o root -g wheel deploy/launchd/com.mooniex.rename-service.plist /Library/LaunchDaemons/com.mooniex.rename-service.plist && sudo launchctl bootstrap system /Library/LaunchDaemons/com.mooniex.rename-service.plist && sleep 5 && sudo launchctl print system/com.mooniex.rename-service | grep -E "^\s+(state|pid) =" && tail -3 ~/Library/Logs/mooniex-rename-service.log
```

Expected: `state = running` and a pid. Remove: `sudo launchctl bootout system/com.mooniex.rename-service &&
sudo rm /Library/LaunchDaemons/com.mooniex.rename-service.plist`. Check from a Mac session:
`bash scripts/session-rename.sh "<job>"` prints `requested: …`; with the service down it prints
`not requested (rename service not reachable …) — rename by hand: /rename <name>`.

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
