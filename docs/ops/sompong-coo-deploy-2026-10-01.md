# SomPong COO session — deploy record + runbook (Contabo, 2026-10-01)

Design: `docs/design/sompong-coo-session.md`. Owner: CTO cto-e106b78b. Went live 2 Oct ~00:10 BKK.

## What runs

| Piece | Where | Runs as |
|---|---|---|
| `mooniex-sompong.service` (supervisor → `scripts/cxo-claude.sh --role coo`, tmux `sompong`) | Agents-Core `deploy/systemd/` → `/etc/systemd/system/` | root supervisor; claude runs as unix user `sompong` |
| `sompong-inbox.service` (durable queue `state/inbox.db`, wake listener 172.18.0.1:8644, socket `state/inbox.sock`) | SomPong repo `ops/` + drop-in `10-session-user.conf` | root, under `infisical_setup.py run MoonieX-SomPong prod --as contabo` |
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

## Acceptance (probes 1, 4, 5 passed 2 Oct 00:15–00:50 BKK)

| Probe | Result |
|---|---|
| 1 Telegram DM + LINE DM + LINE group | PASS — 2 TG answered (26 s, 109 s), LINE DM answered, group event answered (7-day summary to the CEO's DM) |
| 2 family `@สมพงษ์` in the group, risky ask → CEO | not run yet |
| 3 kill the session, messages queue, restart drains | not run yet |
| 4 `/spawn-coo` refuses a second session | PASS — `SomPong already online (tmux sompong, since 2026-10-02 00:11)`, rc 0, still 1 tmux + 1 claude |
| 5 session cannot read the inbox keys | PASS — as `sompong`, `test -r` denied on `/etc/infisical/contabo.env`, `state/inbox.db`, ClaudeFlow `.env` (all root 600); inbox process is root |
| 6 red Run card from SomPong, 15-min wait | not run yet |

## Known gaps (follow-ups)

- No `chats` tool: the session learns a group's id only when that group sends an event (SomPong saved targets in
  its git-ignored `work/memory/private/chat-targets.md`). LINE has no history API before the first event.
- Non-root session has no org MCP (tasks.db read-only), no `send_to_cxo` (mailbox perms), no LungNote.
- SomPong installer default user is still root; Console `names.js` and `windows/cxo-claude.ps1` don't know `coo`.
- Contabo RAM: 7.9 GB, swap 4 GB full during the BL EP58 render; the session slows (an 11 s `date`).
