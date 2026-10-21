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
it is listed as `unknown` (M8, 2026-10-14). The launcher's tmux name CLAIMS a role; it proves nothing about
who started that tmux, so the list says "claimed", never "confirmed". SomPong's fixed tmux `sompong` claims
`coo` only for the session whose UUID the launcher wrote to `state/locks/coo-<sid>.uuid` (M10).
A row no launcher tmux claims ends in `  [name only]` on its own line (strip it before sending), and one
note line explains the mark. On Contabo and the Mac, where every launcher starts a tmux, such a row also
loses its C-level or PH role (`unknown`, so role routing never lands on it) but still prints, counted in the
header as `+N name only`; on winbox (no tmux) it keeps the role the name gives. The `same name` line marks
each row `tmux-claimed` or `name only`. Stored in `live_sessions.verified`.
Names off the CEO's rule (M10, checked by `lib/session_names.rule_problem`: the host emoji, then one of the shapes
in the table below, `<ROLE> (<Persona>)` pinned to `policies/agents.yaml`, the id3 matching the session) each get a
`name off-rule: "<name>" (<host> #<sid>): <why>` line, at most 5 and then `+N more`. A leading state glyph (`⏸`)
and a ` — <topic>` tail are allowed.

| kind | shape (after the host emoji) | example |
|---|---|---|
| C-level | `<ROLE> (<Name>)[ — <topic>]`; bare `<ROLE>` with no persona | `🌐 CTO (Kavin) — CTO Main` |
| COO | `COO (SomPong)` | `🌐 COO (SomPong)` |
| Project Head | `PH#<id3> (<LANE>) - <Project>[ + <Project>…][ — <topic>]` | `🌐 PH#7cf (CTO) - OrgRestructure` |
| Claude worker (new) | `<Short>·<M>#<id3> <Head>: <job>` (M = O, S or H), at most 32 characters | `🌐 Dev·S#49b Org: sparse worktrees` |
| Watch (new) | `Watch#<id3> Runs: <N><light>` (🟢🟡🔴⚪), at most 32 characters | `🌐 Watch#a1b Runs: 2🟢` |
| winbox worker | ASCII only, no emoji, `.` for `·`, `...` for `…` | `Dev.S#49b Org: sparse worktrees` |

CEO 2026-10-15: a session that has a name keeps every part of it, the persona and the PH's lane included (he
renamed two live sessions that way by hand); only the host emoji is ever added. The compact shape of the 15 Oct
plan (`CTO#c34 Main`, `PH#7cf OrgRestructure`) is for the kinds that had no older name: Watch, and workers, whose
old `Dev#49b - Head: job` is still read. A C-level or PH name has no length limit; a new worker or Watch name is
cut at `NAME_BODY_MAX` (32) with the `…` counted. Every reader (this list, `rule_problem`) accepts the old, the
compact and the CEO's shapes. `<Head>` is `short:` in `config/projects.yaml`, else the project's first 10
characters (Org, Spend, BlackLiq, Mimi). The tmux names (`cto-<id>`, `project_head-<id>`, `wd-<id>`, `sompong`)
never change. Writers: `clevel_name`, `ph_session_name`, `worker_name`, `watch_name` in `lib/session_names.py`;
`config.worker_session_name` and the rename service call them.
To fix them: the session runs `bash scripts/session-rename.sh "<job>"`, which sends a rename request over
`/run/rename-service/sock`, and the rename service (`tools/rename_service.py`, `deploy/systemd/rename-service.service`, Agents-Core #272)
types `/rename <rule name>` into that session's launcher tmux pane once its ❯ line is empty, never onto a
draft or a permission prompt. It ignores workers, a PH with no `.project`/`.spawned_by`, and a `sompong`
tmux whose session is not the one in `coo-<sid>.uuid`. It accepts a request only from a process whose
ancestor is that session's Claude process, running as the same uid (SO_PEERCRED): a session renames
only itself.
Every name starts with its host's emoji (CEO 2026-10-14): 💻 Mac, 🌐 Contabo, 🖥️ winbox, e.g. `🌐 CTO (Kavin)`,
`🌐 PH#f35 (CTO) - CookieRun`. The list prints it as part of the name (send it verbatim); parsing drops it first
(`lib/session_names.strip_host`, U+FE0F optional), so a name without one still resolves. The launchers take the
host from `self_host()` only; an unresolved host gets no emoji. Workers spawned on winbox get none (cmd.exe path).
Header per host: `contabo 3 (+5 PH, +1 workers, 4s)` (3 C-levels; workers = neither C-level nor PH); stale: `winbox none (no publisher since 10-12 21:03)`;
stale with a pull error: `winbox unreachable (ssh timeout) since 18:40`. Hub down: one line, exit 0.

## Who sent this: whois, and the reserved titles (OrgMesh P8)

Any session can rename itself, "CTO Main" included, so a name is not proof of who sent a message. Two checks:

`bash scripts/hub/org-python.sh -m tools.whois <name|address|session-id> [--owner <sid>] [--json]` (read-only; Windows: the
`windows_hub_prefix(ROOT)` line above, then `python -m tools.whois …`) resolves the sender through the same hub rows as the list,
on every host, to host, role, short and full session id, title, alive, whether the role is a C-level, and whether a launcher tmux
claims the role. A name matches the row's address or name, host emoji ignored, case ignored; an id (8 or more hex, `#` or
`<role>-` in front allowed) matches the session UUID.
`--owner <sid>` exits 0 only when the name resolves to exactly one live row whose **session UUID** starts or ends with `<sid>`
(8 or more characters; `cto-<8 hex>`, the form a Project Head's brief carries, is read too). It compares the UUID, never the
`sid` column: for a row no launcher tmux claims, `sid` is parsed from the name, and a name is the thing a session can forge.
Otherwise it exits 1 and prints why: `no match`, `ambiguous` (two sessions answer to the name, so a copy of the owner's name
blocks the owner too, by design), `id differs`, `not alive` (the row's host stopped reporting), `hub unreachable`.
Without `--owner` it prints the rows and exits 0 for exactly one match.
A Project Head's brief (`MESH_BRIEF` in `tools/spawn_ph.py`) tells it to run this before it acts on an order; a non-zero exit
means the message is data, not an order.

**Reserved titles.** "CTO Main" and "CMO Main" (whole phrase, case and width ignored, `CTO#c34 Main` too, a host emoji or state
glyph in front changes nothing) may be shown only for a row whose role is `cto` / `cmo`. Any other row that carries one keeps
its line, address untouched, and gets `  ⚠ claims CTO Main` at the end of it (strip it with `[name only]` before sending), one
note line under the list, and `"claims": "CTO Main"` in `--json`. `tools.whois` prints the same claim.

## Rename service

`tools/rename_service.py` behind `scripts/session-rename.sh`, one per host, same code and same rules.

| | Contabo | Mac (M10c) |
|---|---|---|
| runs as | root (the sessions are root) | `gob` (the sessions are gob's; root would run code gob can edit) |
| unit | `deploy/systemd/rename-service.service`, hardened | `deploy/launchd/com.mooniex.rename-service.plist`, LaunchDaemon with `UserName` |
| socket | `/run/rename-service/sock` (RuntimeDirectory, 0755 root) | `~/.rename-service/sock` (dir 0700) |
| who is asking | SO_PEERCRED, ancestry from /proc | LOCAL_PEERPID + LOCAL_PEERCRED, ancestry from `ps` |
| log | `journalctl -u rename-service` | `~/Library/Logs/mooniex-rename-service.log` |

Sweep (M10d, CEO 2026-10-15; the 15 Oct ruling keeps it this narrow): each pass, before the queue, the service also queues the host emoji for a live C-level or PH on this host whose name fails the rule *only* with `no host emoji` (sessions that started before M9 never send a request). It adds the emoji to the session's own name and nothing else, and `_one()` types it like any request. Any other off-rule name is left alone and logged once (`skip  <box>: …`); a box already tried under the same pid and name is not queued again (memory only, so a restart tries once more). Log lines: `sweep    <box>: <old> -> <new>`.

What "empty" means (15 Oct): the service reads each pane with `tmux capture-pane -p -e` and `lib/pane_screen` treats text after the `❯` that sits entirely inside a dim span (SGR 2) as empty, because that is Claude Code's ghost prompt suggestion, not a draft; only non-dim text counts as one. A plain capture shows both the same, and four idle sessions waited 20+ minutes on a suggestion. While it waits the log says why: `wait     <box>: prompt not empty` (a draft), `turn running` (Claude Code greys the `❯` and shows `esc to interrupt`) or `choice prompt up`.

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

## Project Monitor push (P3-E)
On the hub host only (`PUSH_HOSTS = ("contabo",)` in `tools/live_sessions.py`; the Mac and winbox never push) the same
loop also runs `tools/portfolio_push.py` once a minute, which POSTs `lib.portfolio.monitor_payload()` to
`${PORTFOLIO_PUSH_URL:-https://terminal.mooniex.com}/api/portfolio/monitor`. Console never reads Agents-Core's files.
The token is not in Agents-Core: the loop starts `tools/infisical_setup.py run MoonieX-Console prod -- <venv python>
tools/portfolio_push.py` (`PortfolioPush`), and `run` keeps the loop's environment (`{**os.environ, **secrets}`), so
`ORG_DB_URL` reaches the child. `PORTFOLIO_PUSH_TOKEN` lives in Infisical MoonieX-Console/prod and the machine
identity `contabo` must be able to read that project.
- One push in flight at most, started without waiting for it (the 5 s poll is not held up) and killed after 30 s.
  Any error, a spawn failure included, is one line in `state/live_sessions.log` and never touches publishing.
- `portfolio_push.py` exit: 0 pushed (204) · 2 not configured (no token, malformed token, URL not https) · 3 payload
  not built, hub down, nothing sent (Console then goes stale and answers 503, by design) · 4 Console refused (any
  status but 204, a redirect included) or unreachable. It logs one `portfolio_push: …` line and never the token or
  the response body. The loop forwards only that line, once per change: `publish failed (portfolio push exit 4
  (console refused or unreachable): HTTP 401 (token rejected))`, then `portfolio push ok again` on recovery.
- By hand: `bash scripts/hub/org-python.sh tools/infisical_setup.py run MoonieX-Console prod -- .venv/bin/python
  tools/portfolio_push.py; echo $?`. Stop it: `pkill -f 'tools.live_sessions publish --loop'` (the next prompt
  respawns the loop; to keep it off, empty `PUSH_HOSTS`).

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
