# SomPong COO session — deploy record + runbook (Contabo, 2026-10-01)

Design: `docs/design/sompong-coo-session.md`. Owner: CTO cto-e106b78b. Went live 2 Oct ~00:10 BKK.

## What runs

| Piece | Where | Runs as |
|---|---|---|
| `mooniex-sompong.service` (supervisor → `scripts/cxo-claude.sh --role coo`, tmux `sompong`) | Agents-Core `deploy/systemd/` → `/etc/systemd/system/` | root supervisor; claude runs as unix user `sompong` |
| `sompong-inbox.service` (durable queue `/var/lib/sompong-inbox/inbox.db`, wake listener 172.18.0.1:8644, socket `/var/lib/sompong-inbox/inbox.sock`) | Agents-Core `deploy/systemd/sompong-inbox.service`; code = root-owned release `/opt/sompong-inbox/current` (since 2 Oct 19:11 TH) | root, under `infisical_setup.py run MoonieX-SomPong prod --as contabo` |
| ClaudeFlow webhook container | image `mooniex-claudeflow-claudeflow-webhook:sompong-session-e639d4e` | Docker, `n8n_default` |

ClaudeFlow is **not** built from main: branch `deploy/sompong-session-2026-10-01` = 42590d5 (the previous
prod commit) + the SomPong commits. Main carries Chatudo migrations (202609281200+) that MoonieX prod never got.

## Bring ClaudeFlow up (session mode)

From `/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow`:

```bash
python3 /opt/MoonieXHQ/Agents/Core/tools/infisical_setup.py run MoonieX-ClaudeFlow prod --as contabo -- \
  docker compose -f docker-compose.webhook.yml -f docker-compose.sompong-session.yml up -d --no-build claudeflow-webhook
```

Without the override or without `infisical run`, `SOMPONG_BRAIN` is unset and SomPong silently falls back to the
old secretary path. Logs to expect: `[sompong/internal] listening on :3011`, then per message
`[sompong] wake accepted platform=… chat=… event=…`.

**Rollback:** `docker tag mooniex-claudeflow-claudeflow-webhook:pre-sompong-2026-10-01 mooniex-claudeflow-claudeflow-webhook:latest`
(fda17237ff93), then the same command without `-f docker-compose.sompong-session.yml`.

## Secrets (Infisical, values never displayed)

- `MoonieX-SomPong/prod`: `SOMPONG_EA_WAKE_KEY`, `SOMPONG_INTERNAL_KEY`, `SOMPONG_CEO_TELEGRAM_CHAT_ID`.
- `MoonieX-ClaudeFlow/prod`: the same two keys (must be equal), plus `SOMPONG_BRAIN=session`.
- Rotate = new value in both projects, then restart the inbox and re-up ClaudeFlow.

## A new unix user for the session (traps hit on 2026-10-01)

1. **Login without terminal copy/paste:** Run Inbox card with `--expects-input --timeout 1800`, command
   `runuser -u sompong -- env -i HOME=/home/sompong PATH=/home/sompong/.local/bin:/usr/bin:/bin claude auth login --claudeai`.
   The card shows the URL; the CEO pastes the code into the card's input (RUN-20261001-1658-a23b).
2. **Onboarding loop:** a fresh `~/.claude.json` sends claude to the theme picker, then back to "Select login
   method" even with valid credentials. Set `hasCompletedOnboarding: true` (and `theme`) in `/home/sompong/.claude.json`
   as that user, then `systemctl restart mooniex-sompong.service`. The supervisor does not handle the theme picker.
3. The Run Inbox token for `ask_run.py` was copied to `/home/sompong/.config/mooniex/run-inbox.token` (600) by a
   CEO-approved card (RUN-20261001-1622-c71a).
4. **Re-own what root created before the switch.** `install-contabo.sh` ran as root on 1 Oct and left
   `work/` and `work/memory` as `root:root`. As `sompong`, the `media` tool could not create `work/media`, and the
   channel server reported only "tool media failed" (2 Oct). Fixed with `chown -R sompong:sompong work/`. After any
   user switch, `find <repo> -not -user sompong -not -path '*/.git/*'` must list only `__pycache__`, `state/` and the
   installer's root-owned skill symlink.

## Root boundary (CEO 2 Oct: SomPong edits itself and codes; root only through his Face ID)

The SomPong repo belongs to user `sompong`. Nothing that runs as root may run its code or its git:
git as root runs whatever `.git/config` names, pytest as root runs its tests, a root merge leaves
root-owned files in `.git`. So:

- **Inbox code** runs from a root-owned release. To ship SomPong's inbox changes: a **red Run card**
  (Face ID) with `bash /opt/MoonieXHQ/Agents/Core/scripts/sompong-inbox-deploy.sh [<rev>]` — git archive
  as `sompong`, data-filter extract as root (regular files + dirs only), atomic `current` switch,
  health check, rollback, keep 5. `ExecStart` never points into the repo again.
- **Inbox state** lives in `/var/lib/sompong-inbox` (moved 2 Oct 19:11 TH; the old file is
  `SomPong/state/inbox.db.pre-move-2026-10-02`). `SomPong/state/inbox.sock` is a compat link for the
  session started before the move; from its next start the launcher sets `SOMPONG_INBOX_SOCKET`.
- **Root tooling refuses the repo on Contabo:** `config/projects.yaml` has no contabo path for
  `mooniex-sompong`, so delegate / merge_task / worktree fail fast. SomPong commits and pushes itself.
  Read as root only via `runuser -u sompong -- git -C /opt/MoonieXHQ/Projects/MoonieX/SomPong …`.
- Never run the SomPong repo's `ops/install-contabo.sh` as root again.

## The org MCP for the COO (CEO 2 Oct: "ให้ SomPong มีกุญแจ")

- `[SUPERSEDED 2026-10-13]` The role, its grants and its rotation now live in `deploy/coo-gate/`
  (`org_coo_role.sql`, `org_coo_role.py`, README §Install, rotate, remove). The 2 Oct role file
  `deploy/hub/org_coo_role.sql` was removed on 30 Oct: re-running it would reset the password and
  widen the grants (security review task-ee9f3e40, F1). The 2 Oct design, for the record:
- Hub role **`org_coo`** (2 Oct, removed file `deploy/hub/org_coo_role.sql`): no superuser (the `org` role is one, and
  `COPY … TO PROGRAM` would be root-equivalent); rw on tasks/events/locks/c_level_sessions/letters,
  read on hosts, nothing on join_tokens/node_secrets. Not the owner: schema migrations still need a
  root process first. Re-run the file after adding a table the COO needs.
- DSN in **Infisical `Org-Coo/prod` `ORG_DB_URL`**, read by `contabo` only. `sompong` has **no
  Infisical identity**: Free counts the CEO's user against its 5, so the org is full (HTTP 400
  "identity limit reached", 2 Oct). `mooniex-sompong.service` `ExecStartPre` writes the DSN to
  `/run/sompong-coo/org-db.url` (RuntimeDirectory, dir root 0711, file root:sompong 0440, gone on stop)
  via `scripts/coo-org-db-cred.sh`; `scripts/hub/with-org-db-env.sh` leg (a2) reads it into the org
  MCP's environment only (`MOONIEX_ORG_DB_URL_FILE` in COO_ENV).
- Rotate: follow `deploy/coo-gate/README.md` §Install, rotate, remove. `[SUPERSEDED 2026-10-13]`
  "re-run `org_coo_role.sql` with a new password (env `ORG_COO_PASSWORD`), `put` the new DSN,
  restart `mooniex-sompong.service`": that file is gone (30 Oct).
- Face ID: SomPong's own Run Inbox token (`~sompong/.config/mooniex/run-inbox.token`) + `coo` in
  `c_level` → `ask_run --risk red --command …` reaches the CEO's phone.

## Acceptance (probes 1 + 4 passed, 5 file-level only — 2 Oct 00:15–00:50 BKK)

| Probe | Result |
|---|---|
| 1 Telegram DM + LINE DM + LINE group | PASS — 2 TG answered (26 s, 109 s), LINE DM answered, group event answered (7-day summary to the CEO's DM) |
| 2 family `@สมพงษ์` in the group, risky ask → CEO | GATE PASS (2 Oct 19:3x TH, hook against the live inbox as `sompong`, made-up session id): CEO turn → no gate; family-classified turn → Edit `ask`, Bash `ask`, Read `allow`. No family event is stored yet (all 9 are role=ceo), so the family turn was the fail-closed path (unknown id); a real family message is still to be seen |
| 3 kill the session, messages queue, restart drains | not run yet |
| 4 `/spawn-coo` refuses a second session | PASS — `SomPong already online (tmux sompong, since 2026-10-02 00:11)`, rc 0, still 1 tmux + 1 claude |
| 5 session cannot read the inbox keys | FILE-LEVEL ONLY — as `sompong`, `test -r` denied on `/etc/infisical/contabo.env`, `state/inbox.db`, ClaudeFlow `.env` (all root 600). **Not a full pass:** `sompong-inbox.service` runs as root from the SomPong repo, which `sompong` owns and can edit, so its next restart runs that code as root (open CEO decision, 2 Oct) |
| 6 red Run card from SomPong, 15-min wait | PASS (2 Oct 20:04 TH) — card RUN-20261002-1303-316b created as `sompong` (risk red, `id -u; id -un`), CEO approved with Face ID, output `0` / `root`, exit 0; the result letter came back to the requester box. (First card 3e80 expired unapproved 19:57.) |

## Known gaps (follow-ups)

- No `chats` tool: the session learns a group's id only when that group sends an event (SomPong saved targets in
  its git-ignored `work/memory/private/chat-targets.md`). LINE has no history API before the first event.
- Org MCP: after G1 the hub URL comes from Infisical `Agents-Core/prod` through `/etc/infisical/contabo.env` (root 700),
  so the `sompong` user's org server dies on the archived `state/tasks.db`. Open: how a non-root client gets
  `ORG_DB_URL` (Org Mesh lane). Root's `~/.config/mooniex/org-db.env` holds `POSTGRES_*`, not `ORG_DB_URL` — copying it
  does nothing (a copy made by RUN-20261002-0234-f4ec was removed the same day).
- Card RUN-20261002-0234-f4ec (2 Oct) gave `sompong` read on the LungNote MCP `.env` (ACL) and rw on
  `state/inbox` (ACL, default ACL on each mailbox dir). Cross-session `SendMessage`/`ListAgents` work without it.
- SomPong installer default user is still root; Console `names.js` and `windows/cxo-claude.ps1` don't know `coo`.
- `install-contabo.sh:147` links `.claude/skills/gdrive-filing` (root-owned, untracked) to the Core stub that says
  "MOVED to CXO_Rules_GDrive_Filing" and is deleted after 2026-10-27. The link should point at the new skill, and git
  should ignore it.
- **Fixed 2 Oct (SomPong dcc1bcf, task-f965b035):** a bare "@สมพงษ์" arrives with `text=""`. The inbox used to answer
  400, and ClaudeFlow moved the event to `wake-outbox/rejected/` permanently (event 01M3XRJB… 14:34 TH, never
  replayed). The inbox now stores a marker telling the session to read the sender's next message in history.
  `rejected/` is never retried: check it after any inbox validation change.
- Contabo RAM: 7.9 GB, swap 4 GB full during the BL EP58 render; the session slows (an 11 s `date`).

## Restarting a service on this box (incident 2 Oct 09:38 TH)

`systemctl restart mooniex-sompong.service` killed every tmux session on Contabo: the shared root tmux server had been
started from inside that unit and lived in its cgroup. Fixed 16:27 TH by the Mac CTO: the server now runs in its own
unit `org-tmux.scope`. Before restarting any unit, check `tail -1 /proc/$(pgrep -x 'tmux: server')/cgroup` reads
`org-tmux.scope`.
