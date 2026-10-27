# Run Inbox question cards — the contract

**Status:** contract for build, 2026-10-13, CTO cto-3c1f65ae (Contabo).
**Order:** CEO 13 Oct via SomPong: "Session ไหนติด blocker ตอนการให้ฉันอนุญาต ก่อนเริ่มส่ง มาใน /run ได้เลย
หรือถ้ามีคำถาม ส่งคำถามทิ้งไว้ จะเข้าไปกดตอบ เป็นคำถามแบบกดตอบได้นะ"
**Not PR #226.** #226 ("CEO says to session") pushes the CEO's own words INTO a pane, Face-ID signed; it is
design only and waits on the CEO. A question card goes the other way: a C-level session asks, the CEO taps an
answer on `/run`, the session reads the answer from the hub. Nothing here is typed into a pane.

One file, three builders: Console API (`src/run/questions*.js`), the `/run` page (`public/js/run.js`), and the
requester (`tools/ask_run.py`, MCP `ask_ceo`). Nobody restates this contract; everybody links it. A change to
it is a change to this file first.

## 1. The rules (security, binding on every builder)

1. **Only the CEO answers.** The answer route accepts the operator's passkey session cookie and nothing else.
   An org token (C-level or worker) gets `403 operator_only`, whatever it sends. A session can create, read
   and cancel its own question; it can never write an answer. There is no answer verb in `tools/ask_run.py`
   and no MCP tool that answers.
2. **A question can never pre-fill its answer.** A create body that carries any of `answer`, `answer_choice`,
   `answer_label`, `answer_text`, `answered_by`, `answered_at`, `choice`, `status` is refused
   `400 answer_not_allowed {field}`.
3. **The record is the hub, not the letter.** The mailbox letter is a wake-up. `ask_run wait Q-…` reads
   `GET /api/run/questions/:id` and that record (`answer.answered_by`, `answer.answered_at`, `sha256`) is
   what a session cites as the CEO's decision. A root process on the box can write a letter; it cannot make
   the hub say the CEO answered.
4. **What the CEO tapped on is what was shown.** The page hashes the canonical text (§4) of the card it
   displayed and sends that sha256 with the answer; the hub refuses `409 sha256_mismatch` unless it equals
   the stored one.
5. **A question card never stands in for a command card.** Anything that runs a command, spends money or
   touches a secret goes on a command card (`ask_run`, red = fresh Face ID). The hub and the requester both
   refuse a question whose text or options are command-shaped (§5) or name a money amount (§6). Answering
   a question never spawns anything: questions live in their own table (`run_questions`), and the executor
   only ever reads `run_asks`.
6. **C-level only.** Workers report to their C-level; the worker token gets `403 question_needs_c_level`
   on create, and `tools/ask_run.py ask` refuses a non-C-level role before sending.
7. **No Face ID for an answer** (CEO: a question is not a command run). Command cards keep their Face ID
   exactly as today; nothing in `run_asks`, `approve` or `stepup` changes.

## 2. Ids, states, time

- Id: `Q-YYYYMMDD-HHMM-xxxx` (UTC, 4 lowercase hex), regex `^Q-\d{8}-\d{4}-[0-9a-f]{4}$`. Phone link
  `https://terminal.mooniex.com/run#Q-…`.
- `status`: `pending` → `answered` | `expired` | `cancelled`. All three are terminal.
- `expires_in_s`: default 86400 (24 h), min 600, max 604800 (7 days). The CEO leaves questions and comes
  back; a 30-minute life (command cards) is too short.
- The Run Inbox sweep (boot + every 60 s + before each list/read) expires pending questions past
  `expires_at`.

## 3. API (Console, under `/api/run`, same auth middleware as cards)

| method + path | who | body | answer |
|---|---|---|---|
| `POST /api/run/questions` | operator, C-level token | §3.1 | `201 {id, status:"pending", expires_at, url}` |
| `GET /api/run/questions?status=pending\|answered\|done\|all&limit=50` | operator: all · token: own | — | `{questions:[q…]}` newest first |
| `GET /api/run/questions/:id` | operator · token: own (else 404) | — | the bare question (§3.3) |
| `POST /api/run/questions/:id/answer` | **operator only** | `{sha256, choice?, text?}` | `200 {id, status:"answered"}` |
| `POST /api/run/questions/:id/cancel` | operator · token: own, pending only | — | `200 {id, status:"cancelled"}` |
| `GET /api/run/asks/count` | operator | — | `{pending, questions}` (`questions` = pending, unexpired questions; new field) |

"Own" is exactly what cards use today (`canSee`): same token class, narrowed to `X-Run-Session` / `?session=`
when sent. `done` = `answered` + `expired` + `cancelled`.

### 3.1 Create body

```json
{
  "question": "Ship the Console fix tonight or tomorrow morning?",
  "why": "one or more lines of context the CEO reads before tapping",
  "options": [
    {"label": "Tonight", "recommended": true},
    {"label": "Tomorrow 09:00"}
  ],
  "free_text": true,
  "expires_in_s": 86400,
  "requester": {"session": "cto-3c1f65ae", "role": "cto", "host": "contabo", "task": "task-…"}
}
```

- `question`: required, one line, ≤ 300 chars.
- `why`: required, ≤ 1000 chars, may span lines.
- `options`: 2–4 items, each `{label, recommended?}`; label one line, 1–120 chars, unique (case-insensitive,
  trimmed); at most one `recommended: true`.
- `free_text`: default `true`: the page offers a text box, and the CEO may answer with an option, with text,
  or both. `false`: an option is required and text is refused.
- `requester.session` / `role` / `task`: as cards (`SEGMENT`, `ROLE_RE`). `requester.host`: required,
  `^[a-z0-9][a-z0-9-]{0,31}$` (the machine the asking session runs on: `contabo`, `mac`, `winbox`). Role and
  host are claims shown on the card, never used to grant anything.
- Text checks: no hidden characters (the cards' `HIDDEN_PROSE` rule) in any field.

### 3.2 Refusals, in this order (all 400 unless noted)

1. `secret_shaped_value {field, what}`: the cards' `findSecretField` over the whole body.
2. `answer_not_allowed {field}`: rule 1.2.
3. `403 question_needs_c_level`: the worker token.
4. `requester_required` · `invalid_requester_session` · `invalid_requester_role` · `invalid_requester_host` ·
   `invalid_requester_task`.
5. `question_required` · `invalid_question` · `why_required` · `invalid_why` · `invalid_options {detail}` ·
   `invalid_free_text` · `invalid_expires_in_s`.
6. `command_shaped {field}`: §5 matched the question, an option label or a line of `why` (`field` is `why`, no line index).
7. `money_needs_command_card {field}`: §6 matched the question or an option label.
8. `429 too_many_open_questions`: 50 pending questions already (all sessions), or 5 pending from this
   `requester.session`. `429 too_many_questions`: 10 created by this `requester.session`, or 30 in all, in the
   last 60 minutes, counting every status (a cancelled question still counts). Security review 2026-10-13: a
   create → cancel loop kept the open count at 0, and every create queued a `new` mail that buzzes the CEO.

`field` names the place: `question`, `options[1].label`, never the value.

### 3.3 The question record (GET)

```json
{
  "id": "Q-20261013-1102-a3f9", "kind": "question",
  "question": "…", "why": "…",
  "options": [{"label": "Tonight", "recommended": true}, {"label": "Tomorrow 09:00", "recommended": false}],
  "recommended": 0, "free_text": true,
  "requester": {"session": "cto-3c1f65ae", "role": "cto", "host": "contabo"},
  "created_via": "clevel", "status": "answered", "sha256": "<64 hex>",
  "expires_at": "…", "created_at": "…", "finished_at": "…", "letter_at": "…",
  "answer": {"choice": 0, "label": "Tonight", "text": null,
             "answered_by": "<operator username>", "answered_at": "…", "via": "operator_passkey_session"}
}
```

`recommended` is the option index or `null`. `answer` is `null` until answered. `answered_by` is the operator's
username as the hub stores it, whatever its case; never compare it to a fixed string. The marker that an answer came
from the CEO's tap is `answer.via == "operator_passkey_session"`, which only the operator-only route writes. `answer.label` is the
option's label copied at answer time (`null` when only text was given).

### 3.4 Answer body

`{"sha256": "<hex of §4 as shown>", "choice": 0, "text": "optional note"}`

- `choice`: 0-based option index, or `null`/absent. `text`: one line, ≤ 500 chars, hidden-character and
  secret-shape checked; absent/empty = none.
- Refusals: `400 sha256_required` · `409 sha256_mismatch` · `409 not_pending {status}` · `409 expired` ·
  `400 answer_required` (no choice and no text) · `400 invalid_choice` · `400 free_text_not_allowed` ·
  `400 invalid_text` · `400 secret_shaped_value {field:"text"}`.
- The pending → answered change is conditional (one winner, like `store.transition`).

## 4. The canonical text the sha256 covers

The server computes it at create; the page computes it from the record it displays. Both use exactly:

```js
JSON.stringify({
  v: 1,
  id: q.id,
  question: q.question,
  why: q.why,
  options: q.options.map((o) => o.label),
  recommended: q.recommended,            // index or null
  free_text: q.free_text,                // boolean
  requester: { role: q.requester.role, session: q.requester.session, host: q.requester.host },
})
```

`sha256` = lowercase hex SHA-256 of that string's UTF-8 bytes (WebCrypto on the page, `node:crypto` on the
hub). Key order is part of the contract.

**Pinned example** (both sides test against it, byte for byte). The question:
id `Q-20261013-1102-a3f9`; question `Ship the Console fix tonight or tomorrow morning?`; why
`The fix is tested.` + newline + `Tonight means a restart at 22:00.`; options `Tonight` (recommended),
`Tomorrow 09:00`, `ส่งพรุ่งนี้เช้า`; free_text true; requester role `cto`, session `cto-3c1f65ae`,
host `contabo`. Canonical string (one line; `\n` is the two JSON escape characters):

```
{"v":1,"id":"Q-20261013-1102-a3f9","question":"Ship the Console fix tonight or tomorrow morning?","why":"The fix is tested.\nTonight means a restart at 22:00.","options":["Tonight","Tomorrow 09:00","ส่งพรุ่งนี้เช้า"],"recommended":0,"free_text":true,"requester":{"role":"cto","session":"cto-3c1f65ae","host":"contabo"}}
```

sha256 = `f0784abe125b12ce5dc3993d0f1a7f1e6769e89ffbbbffbd4171cdd614f287c0`

## 5. Command-shaped (refused in `question`, every option label, and every line of `why`)

Before matching (here and in §6), every Unicode space character (category Zs, e.g. U+00A0, U+2009) becomes an
ASCII space. `why` is checked line by line, each line as its own text (security review 2026-10-13: a Yes/No
question whose `why` carried `Run sudo systemctl restart nginx` passed).

A text is command-shaped when any of these match (JS and Python carry the same rules and the same test table):

- a backtick; `$(`; `${`; `&&`; `||`
- a pipe into a word: `(^|\s)\|\s*[A-Za-z]`
- a redirect to a path: `(^|\s)>>?\s*[/~.]`
- a CLI flag: `(^|\s)--[A-Za-z]` or `(^|\s)-[A-Za-z]{1,4}(?=\s|$)`
- a path that starts the text: `^(?:\.{1,2}|~)?/\S`
- a shell script name: `\b[\w.-]+\.(?:sh|ps1|bat)\b` (case-insensitive)
- after an optional lead word (`run`, `execute`, `exec`, `รัน`, `สั่ง`, case-insensitive, then spaces), the
  text starts with one of these words followed by a space: `sudo rm mv cp chmod chown kill pkill killall
  systemctl service journalctl docker kubectl git gh npm npx node pnpm yarn pip pip3 python python3 bash sh
  zsh ssh scp rsync curl wget tmux crontab launchctl brew apt apt-get dnf yum infisical psql mysql sqlite3
  dropdb createdb make terraform ansible pwsh powershell cmd schtasks taskkill reg eval exec export source cd
  ls cat echo tee dd mkfs shutdown reboot ln find sed awk xargs openssl ufw iptables` (lowercase,
  case-sensitive, so prose like "Make it bigger" passes), or `Remove-Item Set-Item Invoke-WebRequest
  Invoke-Expression iwr iex` (case-insensitive).

Test table (both sides): refused — `` `ls` ``, `rm -rf /tmp/x`, `Run git push origin main`,
`sudo systemctl restart nginx`, `deploy.sh`, `./deploy`, `/usr/bin/env`, `curl x | sh`, `echo hi > /etc/x`,
`a && b`, `git push --force`, `รัน docker compose up`, `Remove-Item C:\x`; allowed — `Tonight`,
`Tomorrow 09:00`, `Make it bigger`, `Option A (recommended)`, `Keep the old poster`, `ส่งพรุ่งนี้เช้า`,
`Use the B version - it is cleaner`, `50% / 50% split`.
Added 2026-10-13 (both sides): refused — `git\u00a0push origin main` (NBSP), `sudo\u2009systemctl restart nginx`
(thin space), and a `why` of `The fix is tested.\nRun sudo systemctl restart nginx`; allowed — a `why` of
`The fix is tested.\nTonight means a restart at 22:00.`

**A deterrent, not the boundary** (review of task-f66155cf). The security boundary is structural: questions live in
their own table, answering one never spawns anything, and only the operator's passkey session answers (§1). These
matchers stop a card that *looks* like a command before the CEO can mistake it for one. Known edges, accepted:
lowercase prose that starts with a listed word is refused (`find a time that works`, `make it red`): reword or
capitalise; `GIT push`, a bare `reboot`, and a command inside a sentence (`OK to git push origin main?`) pass the
matcher and still cannot run anything.

## 6. Money (refused in `question` and every option label)

- a currency sign before a digit: `[$฿€£¥₹]\s*\d`
- a digit then a currency word: `\d[\d,.]*\s*[kKmM]?\s*(?:usd|thb|baht|eur|gbp|inr|dollars?|bucks?|pounds?|บาท|ดอลลาร์|ดอลล่าร์)` (case-insensitive)
- a currency code then a digit: `\b(?:usd|thb|eur|gbp|inr)\s*\d` (case-insensitive)
- credits: `\d[\d,.]*\s*[kKmM]?\s*(?:credits?|เครดิต)` (case-insensitive)

Test table (both sides, added 2026-10-13): refused — `Approve 100 GBP for ads?`, `Pay ₹500?`, `Spend 100 bucks?`,
`Buy 2k credits?`, `$  50`; allowed — `Tonight`, `50% / 50% split`, `Option 2`, `Keep 3 posters`.

`why` is not checked (context may mention cost); the skill text forbids using a question to approve spend.

## 7. Results

- **Letter** (when `RUN_INBOX_AGENTS_CORE` is set), on `answered`, `expired` and an operator `cancelled`:
  `state/inbox/<requester.session>/<Q-id>.json`, the cards' envelope (`from.role = "run-inbox"`), plus
  `{id, kind:"question", status, answer}`. `body` (one line, what hook-inbox prints):
  - answered: `Q-… answered by the CEO on /run: "<label>" (+ note: "<text ≤120>") — record: ask_run wait Q-…`
  - expired: `Q-… expired unanswered — <question ≤80>`
  - cancelled: `Q-… cancelled — <question ≤80>`
- **Mail** (the outbox the sender already delivers): one `event:"new"` line per question,
  subject `[ASK][<ROLE>] <question ≤80> — Q-…`, thread = the id, body = who · session · host, the why,
  the numbered options with `(แนะนำ)` on the recommended one, the link. No result mail (he answered it).
- **Ledger**: `run-ledger.jsonl`, one line per state change (`{id, ts, state, sha256, exit:null, ms:null}`).
- **08:00 digest**: pending questions are listed with the open cards.

## 8. The page (`/run`)

- Inbox: a group **คำถามรอตอบ · N** above รอกดยืนยัน; a row shows role + session, host chip, time left, the
  question, the why's first line.
- `#Q-…` opens the question view: ผู้ถาม (ROLE (session) · host), เหตุผล (the why, all lines), the question
  large, one full-width button per option (the recommended one carries an **แนะนำ** badge), a text box when
  `free_text`, and **ส่งคำตอบ** (enabled once an option is picked or text typed, and the sha256 of §4
  verified). A tap selects; ส่งคำตอบ sends. No Face ID.
- Footer line: `คำถามไม่รันคำสั่ง — คำสั่ง / เงิน / secret ต้องมาเป็นการ์ดคำสั่ง (Face ID)`.
- Answered / expired / cancelled: read-only, the chosen option highlighted, `answered_at`, and
  `ส่งคำตอบถึง <ROLE (session)> แล้ว` when `letter_at` is set.
- Icons are inline SVG, never emoji. Everything server-supplied goes through `textContent`. 390 px wide
  with no horizontal scroll.
- The nav badge counts `pending + questions`.

## 9. Requester (Agents-Core)

- CLI: `python3 tools/ask_run.py ask --question "…" --option "A" --option "B" [--recommended 1]
  --why "…" [--no-free-text] [--expires-h 24] [--session …] [--role …] [--host …] [--dry-run] [--json]`;
  prints the id and the URL. `wait`, `cancel` and `list --questions` take `Q-…` ids (or the `/run#Q-…` URL).
  `wait` exits 0 answered, 1 expired/cancelled, 4 max-wait.
- MCP: `ask_ceo(question, options, why, recommended=0 (1-based, 0 = none), free_text=True, expires_h=24,
  session, role, host, task, dry_run)` → `{id, url, expires_at}`. `ask_run_wait` accepts `Q-…` ids and
  returns `{terminal, status, answer, …}`.
- `requester.host`: `--host`, else `ORG_HOST`, else `lib.config.self_host()` when importable, else the
  lowercased short hostname.

## 10. Several questions, one send (CEO 14 Oct)

**Order:** CEO 14 Oct ~03:55 TH via SomPong: "เวลามีมากกว่า 1 คำถาม ระบบจะส่งมาทีละอันเวลากด … อยากให้มีการส่ง
คำถามแบบเป็นชุด … ตอบให้ครบแล้ว กดส่ง trigger แค่รอบเดียวพอ ประหยัด token ด้วย". Each answer used to write its
own letter, and each letter wakes its asker for a model turn: N answers cost N wakes. The CEO's tap is now the
boundary: what he sends at once reaches each asker as one letter. No time window.

- **Group.** `POST /api/run/question-groups` `{questions:[{question, why, options, free_text?}…] (1–6),
  expires_in_s?, requester}` → `201 {group_id, status:"pending", expires_at, url, questions:[{id, status,
  expires_at, url}…]}`. Group id `QG-YYYYMMDD-HHMM-xxxx`. All or nothing: every item passes §3.2 exactly as a
  lone question (a refusal adds `index`), an item may not carry `requester` or `expires_in_s`, and nothing is
  stored if one item fails. Every question keeps its own row, id, sha256 (§4, unchanged) and record; a grouped
  record adds `group_id` as its last key, a lone record has no such key. One `new` mail lists every question.
  `GET /api/run/question-groups/:id` → `{id, kind:"question_group", status:"pending"|"done", requester, total,
  answered, open, questions:[record…]}` (own / operator, like a question). There is no group cancel: cancel each
  `Q-…`.
- **Caps (§3.2 item 8).** The per-session open cap (5) counts cards (a group is one card); the 50 open, 30/h and
  10/h per session caps count questions (a group of 6 counts 6).
- **One send.** `POST /api/run/questions/answers` `{answers:[{id, sha256, choice?, text?}…] (1–50)}`, operator
  only, like §3.4. Every item is checked first (§3.4 per item, plus `invalid_id`, `duplicate_id`, `not_found`);
  one bad item refuses the whole send with `{index, id}` and writes nothing. Then one transaction. A question
  that ended in the meantime is reported, not refused: `{id, status:"expired"}` (expired on the spot) or
  `{id, status, error:"not_pending"}`. → `200 {answered, results, letters}`.
- **Letters (§7).** The rows that changed are grouped by `requester.session`. One row → the §7 letter
  (`<Q-id>.json`), unchanged. Several → one letter `QB-YYYYMMDD-HHMM-xxxx.json`, `kind:"question_batch"`,
  `questions:[{id, group_id, status, answer}]`, and a one-line summary (`the CEO answered k of n questions in one
  send on /run: … — records: ask_run wait QG-…`). One letter = one wake. The 60 s sweep writes the same batch
  letter when a group's questions expire together. A grouped question answered on its own card gets its own
  §7 letter. The letter still only wakes: the record is the hub's (§1.3).
- **Page (§8).** A pick is a draft until sent. `#Q-…` sends one, as before. `#questions` (every pending question)
  and `#QG-…` (one group) list the drafts card by card (a group under one asker line) with **ส่งทั้งหมด (k)**,
  which sends every ready draft in one request, each with the sha256 the page computed for what it showed. The
  inbox shows **ตอบทั้งชุด · N ข้อ** from two pending questions, **ส่งร่างทั้งหมด (k)** once drafts exist, and a
  `ร่าง:` line on a drafted row. Only the picked option survives a reload (localStorage, best effort); typed text
  stays in the page.
- **Requester (§9).** `ask_run.py ask --batch FILE` (a JSON list, `-` = stdin; each item `{question, why,
  options:[labels], recommended (1-based, 0 = none), free_text}`; the flags give requester, host and expiry once;
  `--batch` with `--question/--option/--why/--recommended/--no-free-text` is a usage error) prints the group id,
  its URL and each question id. Every item gets every local check of a lone `ask`, before any call. `wait QG-…`
  polls the group until none is pending (exit 0 all answered, 1 otherwise), checks every question as §1.3 and
  fails closed on a question from another group or a "done" group with a pending question. MCP:
  `ask_ceo(questions=[…], session, role, host, task, expires_h, dry_run)` → `{group_id, url, expires_at,
  questions:[{id, url}]}`; giving `questions` and a one-card field is refused. `ask_run_wait` takes `QG-…`.
- **Code + tests.** Console `src/run/questions.js` (`createQuestionGroup`, `answerBatch`, `sendLetters`),
  `src/run/notify.js` (`writeQuestionBatchLetter`), `test/run-questions-batch.test.js` (3 questions from 2
  sessions → one send → one letter per session). Agents-Core `tools/ask_run.py`,
  `tests/test_ask_run_questions.py` §groups.

## 11. Media: pictures, videos and sounds on a card (CEO 27 Oct)

A card may carry 1 to 12 **items** the CEO looks at or listens to and picks from. The Console builds the hub half
(upload route, serving, sweep, the page); this section is the requester's side (`tools/ask_run.py`) and the wire
shape both sides keep. The card shows a **preview**: the sender keeps the master.

- **Wire.** `POST /api/run/question-media`: the file's raw bytes, `Content-Type: application/octet-stream`, header
  `X-Run-Session` (the card's `requester.session`; missing or malformed = 400 `invalid_requester_session`) and
  `X-Media-Name` (the base name); answers 201 `{media_id: "M-" + 24 hex, kind, mime, bytes, sha256}`, 413
  `too_large`, 415 `unsupported_media`, 429 `rate_limited` (40 uploads per session per hour), 507 `store_full` /
  `disk_low`. An upload belongs to the session that made it and is attached by one card only. `POST
  /api/run/questions` then carries `media:[{id, caption?, poster_id?}]` and `pick` (400 `invalid_media`,
  `options_not_allowed`; `media_not_in_groups` in a group). The sha256 of the question covers `pick` and each item's
  `{n, kind, mime, bytes, sha256, caption}` when media is present; a card without media keeps today's canonical text.

- **Kinds and caps** (read from the first bytes, never the name; an SVG, an HTML page or a PDF named `.jpg` is
  refused before any call). Picture JPEG/PNG/GIF/WebP, at most 10 MB. Video MP4/MOV/WebM, at most 50 MB. Audio
  MP3/M4A/AAC/WAV/OGG, at most 20 MB. At most 12 items. The caps hold for what is **uploaded**, after the shrink.
- **Shrink before upload** (ffprobe decides, ffmpeg does it, temp dir removed afterwards): a picture with a long edge
  over 2048 px becomes 2048 (JPEG, a WebP stays WebP); a video becomes a 720p H.264/AAC MP4 with `+faststart` (one
  that already is that is only re-wrapped) plus a **poster** JPEG at 0.5 s, uploaded as its own image and sent as
  `media[i].poster_id`; audio that is not MP3/M4A/AAC becomes M4A AAC 128k. No ffmpeg: refused with an install
  hint, never uploaded untranscoded. A frame over 100 megapixels is refused.
- **Requester.** `ask_run.py ask ... --media PATH` (repeat 1-12 times) `--caption TEXT` (by order, at most 60
  characters, one line) `--pick one|many`. Every file is checked and shrunk **before the first upload**, so a bad
  third file leaves nothing behind. Then each file goes to `POST /api/run/question-media` (raw bytes,
  `application/octet-stream`, header `X-Run-Session` = the card's `requester.session`, header `X-Media-Name` = the
  file's base name, percent-encoded when it is not printable ASCII), then `POST /api/run/questions` with `media:[{id, caption?, poster_id?}]` and `pick`. A caption and a file
  name pass the secret check, §5 (command-shaped) and, for captions, §6 (money).
- **Pick rules.** One item: `--pick` absent or `one`; options default to ใช้ได้ / แก้ / ไม่เอา, or give 2-4 `--option`s;
  the answer is a `choice`. Two or more items: `--pick` is required (`one` = he taps one, `many` = he ticks any,
  none allowed), `--option` and `--recommended` are refused (`options_not_allowed`), items are A, B, C ... L. A media
  card always has the optional note. `--batch` with media, and `ask_ceo(questions=...)` with media, are refused.
- **Answer.** A set card: `answer.picks:[n...]` (0-based), `answer.picked:["B", ...]` (letters) and
  `answer.picked_names:[...]` (the files' display names, text only, never a path); a redo (ขอรอบใหม่) is `redo:true,
  picks:[]` with the note required. `wait` prints `picked: B (cover_b.png) · note: ...`, `picked: A (a.jpg), C (c.jpg)`,
  `picked: none · note: ...` (a redo, or nothing ticked) and, for one item, `picked: ใช้ได้ · note: ...`; the note
  part only when there is one. `--json` keeps `picks`, `picked`, `picked_names`, `redo`. A `picks` that names an
  item the card does not have, repeats one, or disagrees with `picked` is a failed check (the §1.3 fail-closed rule).
- **Keeping and reading.** Files are kept 7 days after the card closes (answered, expired or cancelled), then
  deleted by the Console sweep; an open card's files are never deleted and an upload nobody attached goes after
  1 hour. The store is capped at 2 GB; over it the oldest closed cards' files go first, and if it is still full or
  the disk is under 6 GB free the upload is refused with the hub's own message (`store_full`, `disk_low`), which
  the tool prints as it came. The decision record (names, captions, sha256, sizes, picks, note, time) stays in
  the hub database for good. Files are served only to the CEO's signed-in session (`operatorOnly`); an org token
  gets 403. The folder is `<hq>/Assets/MoonieX/Console/run-media`, class DISPOSABLE (`config/machine-contract.yaml`,
  cap in `config/storage-policy.yaml` `run_media`).
- **MCP.** `ask_ceo(media=[{path, caption?}], pick=...)` runs the same code as the CLI.
- **Code + tests.** Agents-Core `tools/ask_run.py` (media section), `tests/test_ask_run_media.py`.
