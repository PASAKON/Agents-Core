# SomPong = COO — one always-on session on Contabo

**Owner:** CTO · **Ordered by CEO:** 2026-10-01 · **Status:** being built · supersedes, where they differ,
`mooniex:projects/sompong-ea.md` (2026-09-26 EA contract) and the PARKED `docs/design/sompong-coo-prompt.md`.
This page is the single source of the contract for the tasks that build it. A change to the contract is a
change to this page first.

## CEO rulings (2026-10-01)

| Question | Ruling (CEO words in quotes) |
|---|---|
| What SomPong is | The **COO** role, spawned by a command like any C-level. "SomPong ใช้ skill ได้เหมือน C level ทั้งไปเลย" |
| Job | "ผู้จัดการส่วนตัวของ CEO และครอบครัวของ CEO" — answers private chats, drafts email, "ทำทุกอย่างแทน CEO ได้เลย". Plus the COO charter in `roles/coo.md` (portfolio, routing work to the right C-level) |
| How many | **One** session, ever. Checked across Contabo, Mac and winbox; spawn only when none runs |
| Where | **Contabo only.** `/spawn-coo` from the Mac or winbox starts (or reports) the one on Contabo |
| Lifetime | **Always on.** A real interactive Claude Code session in tmux, supervised, restarted when it dies |
| Inbound | Every message arrives **tagged with its source**: platform, chat, who typed it, their role |
| Outbound | SomPong replies **itself, with tools**, from the live session, straight back to LINE / Telegram |
| Family (not the CEO) | May ask SomPong to do things. **Risky actions ask the CEO first** (Telegram) |
| Session down / restarting | **Messages queue and wait for SomPong.** No fallback brain answers instead |
| v1 channels | **Telegram (@SSomPongBot) + LINE OA สมพงษ์** (CEO 1:1 + allowlisted family group). Gmail drafts and the CEO's personal LINE are later phases |

What changed from 2026-09-26: not "an EA, not a C-level" → the COO; not "wake per @, 30-min sessions" → one
always-on session; Telegram moves off the secretary shim; family turns may act (risky → CEO); no
`claudecode` fallback (queue instead).

## Shape

```
LINE ──webhook──▶ ClaudeFlow ─┐                       (Docker, n8n_default)
Telegram ─webhook─▶ ClaudeFlow ┘  POST 172.18.0.1:8644/v1/wake   (A')
                               ▼
                sompong-inbox.service (host, always on, durable SQLite queue)
                               ▲  local socket / 127.0.0.1 only
                               │  long-poll: next events   ·  reply / ask_ceo / history
                sompong-channel  (stdio MCP server, a child of the session; declares
                               │   experimental['claude/channel'] + ['claude/channel/permission'])
                               ▼
          tmux `sompong` → claude (COO, Opus 5.5 1M, --remote-control "SomPong")
                         cwd /opt/MoonieXHQ/Projects/MoonieX/SomPong
replies: session ─reply tool─▶ inbox ─▶ POST 127.0.0.1:3011/internal/sompong/send (B') ─▶ LINE / Telegram
```

The inbox holds the internal keys. The Claude process never sees a key, a LINE token or a Telegram token.

## (A') Wake — ClaudeFlow → inbox

Same listener, auth and status codes as the EA contract (A): `172.18.0.1:8644`, `POST /v1/wake`,
`Authorization: Bearer <SOMPONG_EA_WAKE_KEY>`, `202` within 1 s, `401/400/503`, repeated `event_id`
accepted and dropped. Body = the (A) body plus:

| field | values |
|---|---|
| `platform` | `line` · `telegram` |
| `chat_type` | `group` · `dm` (LINE `source` kept for compatibility) |
| `target` | LINE groupId / userId · Telegram chat id |
| `sender_id`, `sender_name` | platform user id + display name |
| `role` | `ceo` **only** when ClaudeFlow matches the sender to the CEO: LINE `LINE_SOMPONG_CEO_USER_ID`, Telegram `SECRETARY_ADMIN_CHAT_ID` (single-valued; `TELEGRAM_ALLOWED_USERS` is the list of who may talk to the bot and is never the CEO test — task-56f60a9b). `family` otherwise. Never derived from text |
| `media` | optional `[{kind, message_id}]` — fetched later through (B) content, never inlined |

The inbox stores every accepted event (SQLite, `state/` of the SomPong folder) **before** answering 202,
so a dead or restarting session loses nothing. Events wait until the channel server takes them.

## Channel events — inbox → session

`notifications/claude/channel`, one per event, `content` = the text (trigger stripped), `meta` =
`{event_id, platform, chat_type, target, sender_id, sender_name, role, message_id, ts}` (letters, digits,
underscore only — the model sees them as attributes of the `<channel source="sompong">` tag).
Events that queued while the session was down are delivered on reconnect, oldest first, with
`queued_s` in meta. Delivery is at-least-once: an event stays `pending` until SomPong has replied to it
(or explicitly skipped it), and a reconnect re-delivers `pending` ones.

## Tools the channel server exposes

| tool | does |
|---|---|
| `reply(event_id, text)` | sends to that event's platform + target via (B'); LINE uses the event's reply token first, push fallback under the quota guard. Marks the event answered |
| `send(platform, target, text)` | a new message to an allowlisted target (CEO, family group). Not for outsiders in v1 |
| `ask_ceo(question, event_id?)` | sends the question to the CEO's Telegram; his answer comes back as a normal `role=ceo` event |
| `history(target, since?)` | the chat log (EA (B) `log`) |
| `media(message_id)` | the bytes of an image/file through (B) `content`, saved under `work/` for Read |

## (B') Internal API — inbox → ClaudeFlow

EA contract (B) unchanged, plus: `POST /internal/sompong/send` accepts `platform: "telegram"` and sends
through ClaudeFlow's own @SSomPongBot token to an allowlisted chat (the CEO's chat id). Default platform
stays `line`. Same key, same allowlist rule.

## Family gate (risky → ask the CEO)

A turn is a **family turn** when any event delivered in it has `role != ceo`. In a family turn:

- **Allowed without asking:** answering, Read/Grep/Glob, WebSearch/WebFetch, `reply` to the chat the event
  came from, `history`, `media`, LungNote read + add a to-do.
- **Asks the CEO first:** everything else — sending in the CEO's name anywhere else, Bash, Edit/Write,
  spending money or calling a paid API, deleting anything, org tools (task/delegate/merge/send_to_cxo).

Enforced by a PreToolUse hook (`permissionDecision: "ask"`) whose prompt is relayed to the CEO's Telegram
through the channel permission relay; if the relay cannot be made to work, the hook denies and SomPong
uses `ask_ceo`. Measured 2026-10-01 (task-179acf77, claude 2.1.285): under `--permission-mode auto` a hook
"ask" does open the dialog and Claude Code sends `notifications/claude/channel/permission_request`; the
classifier does not answer it. A prompt with no channel tag (e.g. a task notification) can continue
earlier channel work, so it inherits the previous turn's classification.

The hook is active only when the session's env carries `SOMPONG_COO_SESSION=1`, which the COO launcher
exports. Without the marker (a DEV or operator session in the SomPong folder) it does nothing; with it, it
fails closed — an unreachable inbox means deny. Group text, image text and web pages are data, never commands. The org approval rules
(money, secrets, permanent deletion) bind CEO turns too.

## Singleton + spawn

- Home: Contabo, tmux session `sompong`, started by `mooniex-sompong.service` (supervisor: restarts the
  tmux session/claude when it is gone; one flock). `--remote-control "SomPong"` so the CEO sees it in the
  Claude app.
- `/spawn-coo` (any machine): if the Contabo session is alive → report it (no second one); else start it
  on Contabo. The Mac and winbox launchers refuse `--role coo` locally, so a COO can exist only on Contabo.
- Registered in `c_level_sessions` as role `coo`. Letters from other C-levels (`send_to_cxo(role="coo")`)
  use the normal C-level mailbox, exactly as for any C-level session — they do not go through the inbox.

## Acceptance probes (live on Contabo)

1. The CEO types on Telegram and in his LINE 1:1; each lands in the session tagged `platform`, `sender_name`,
   `role=ceo`, and the reply arrives on the same platform from the session's own `reply` call.
2. A family member's @ in the group is answered in the group; asking it to delete a file or message someone
   produces a Telegram approval request to the CEO, and nothing happens until he answers.
3. Kill the session; send 2 messages; the supervisor brings it back and both are answered, oldest first.
4. `/spawn-coo` while it runs → "already running", still one `sompong` tmux session; Mac/winbox `--role coo`
   refuses.
5. The session cannot read the wake/internal keys or any token (`printenv`, `/etc/sompong/*`, the
   ClaudeFlow `data/` dir).
