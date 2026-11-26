# MoonieX Care — LINE Official Account Hybrid Messaging & Browser Sender Design

- **Status:** Design Specification (Phase 0 — Do NOT build sender or outbox in this task)
- **Account:** `MoonieX Officials` (name: `@mooniex`, `basicId`: `@587kfqpt` — confirmed by CEO)
- **Primary Inbound / Webhook:** `src/webhook/line.js` + LuNar chat flow
- **Quota Reference:** `docs/research/line-messaging-quota.md`
- **Desktop Lease Reference:** `.claude/skills/ALL_Rules_Winbox_PCLease/SKILL.md`

---

## 1. End-to-End Message Flow (`@mooniex` & LuNar Chat Flow)

MoonieX Care handles customer conversations for the LINE Official Account **`MoonieX Officials`** (`name`: `@mooniex`, `basicId`: `@587kfqpt`, confirmed by CEO) across two coordinated paths: the **LINE Messaging API webhook (`src/webhook/line.js`)** integrated with the **LuNar chat flow**, and the **LINE OA Manager browser sender (`chat.line.biz`)** running on `winbox`.

```
Customer (LINE App)
   │
   ▼  (1) Webhook Event (message + replyToken)
src/webhook/line.js  ──►  LuNar Chat Flow (Inbound Queue & Reply Generation)
                                 │
                                 ▼  (2) Enqueue outbound response
                          care_outbox (PostgreSQL / Hub)
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼ (Path A: Fast / Free)                         ▼ (Path B: Post-Expiry / 1-on-1 Chat)
  Reply Token Valid?                              Reply Token Expired or Manual Follow-up
  POST /v2/bot/message/reply                      LINE OA Manager Browser Sender (winbox)
  (0 quota consumed)                              chat.line.biz (0 API push quota consumed)
                                                         │
                                                         ├─► If winbox offline: wait for winbox online
                                                         │   (or webhook reply-token fallback on next user turn)
                                                         ▼
                                                  Push API (POST /v2/bot/message/push)
                                                  ONLY after token expiry AND ONLY for
                                                  important announcements (consumes 300/mo Free quota)
```

### 1.1 Account Identity & Credential Hygiene

| Attribute | Value / Rule |
| :--- | :--- |
| **Account Name** | `@mooniex` |
| **Display Name** | `MoonieX Officials` |
| **Basic ID (`basicId`)** | `@587kfqpt` (confirmed by CEO) |
| **Current Token Location** | Stored in the account store. **Note:** `.env` line 12 is malformed and must not be parsed or relied upon. |
| **Phase 1 (P1) Secret Migration** | **P1 moves the channel token to Infisical** (`ALL_Rules_Secrets`). |
| **Token Redaction Rule** | **Never print, log, echo, or store the token** in code, git, reports, or logs. |
| **Customer Privacy Rule** | **No screenshots of customer chats in git.** Any diagnostic capture must be excluded from version control and purged after verification. |

---

## 2. `care_outbox` Table & State Machine

All outbound care messages emitted by the LuNar chat flow are persisted in `care_outbox` before any network or browser action is taken.

### 2.1 Schema Definition

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `BIGSERIAL` / `UUID` | `PRIMARY KEY` | Unique outbox row identifier. |
| `idempotency_key` | `TEXT` | `UNIQUE NOT NULL` | Deterministic key (e.g., `sha256(channel_id : recipient_id : source_event_id : template_or_seq)`) preventing duplicate queueing or double sends. |
| `channel_basic_id` | `TEXT` | `NOT NULL DEFAULT '@587kfqpt'` | Target OA basic ID (`@587kfqpt` / `@mooniex`). |
| `recipient_id` | `TEXT` | `NOT NULL` | LINE `userId` or OA Manager chat thread identifier. |
| `recipient_display_name` | `TEXT` | `NOT NULL` | Expected display name verified during browser recipient readback. |
| `message_kind` | `TEXT` | `NOT NULL` | `care_reply` \| `important_announcement` |
| `payload_json` | `JSONB` | `NOT NULL` | Message body / bubbles to deliver. |
| `reply_token` | `TEXT` | `NULL` | Webhook `replyToken` captured from `src/webhook/line.js` (never logged in plaintext). |
| `reply_token_expires_at` | `TIMESTAMPTZ` | `NULL` | Computed from webhook event timestamp + reply-token lifetime (**TBD**). |
| `state` | `TEXT` | `NOT NULL DEFAULT 'queued'` | One of: `queued`, `sending`, `sent`, `deferred`, `dropped`, `failed`, `fallback`. |
| `delivery_via` | `TEXT` | `NULL` | `api_reply` \| `oa_browser` \| `api_push` |
| `attempt_count` | `INTEGER` | `NOT NULL DEFAULT 0` | Number of delivery attempts recorded. |
| `last_error` | `TEXT` | `NULL` | Sanitized error code/reason (no tokens, no PII). |
| `sending_started_at` | `TIMESTAMPTZ` | `NULL` | Timestamp written **before** the send click or API call. |
| `sent_at` | `TIMESTAMPTZ` | `NULL` | Timestamp when delivery is confirmed. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Row creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Last state transition timestamp. |

### 2.2 Outbox States (`queued`, `sending`, `sent`, `deferred`, `dropped`, `failed`, `fallback`)

| State | Meaning & Transition Rule |
| :--- | :--- |
| `queued` | Ready for delivery. Created with a unique `idempotency_key`. |
| `sending` | **Marked `sending` BEFORE clicking Send** in `chat.line.biz` (or before firing the HTTP request). Prevents a crashed worker from blindly re-clicking Send on restart without first inspecting the chat history. |
| `sent` | Confirmed delivered (HTTP `200 OK` from `/v2/bot/message/reply` or `/push`, or verified rendered bubble in `chat.line.biz`). |
| `deferred` | Temporarily postponed without error: e.g., `winbox` is offline (sender **waits for `winbox` online**), `PC: CEO` hold is active, or per-hour/per-day throttle ceiling is reached. |
| `dropped` | Intentionally skipped and never sent (e.g., superseded by a newer conversation turn, non-important push blocked by quota policy, or cancelled by operator). |
| `failed` | Terminal failure after retry/inspection (e.g., recipient readback mismatch, kill-switch tripped by captcha/warning/logout, or unrecoverable payload error). |
| `fallback` | Primary path unavailable (e.g., `winbox` browser sender unavailable or kill-switched) and message is handed over to / fulfilled via **fallback reply token via webhook** (or flagged for fallback webhook reply on the customer's next inbound event). |

### 2.3 Pre-Click `sending` Transition & Idempotency Guarantee

1. **Deduplication at Enqueue:** `INSERT INTO care_outbox ... ON CONFLICT (idempotency_key) DO NOTHING` ensures webhook retries or LuNar replays cannot create duplicate rows.
2. **Mark `sending` Before Click:** In the browser sender, after typing/staging the message and verifying both the channel (`@587kfqpt` / `MoonieX Officials`) and the recipient header, the worker executes `UPDATE care_outbox SET state = 'sending', sending_started_at = NOW() WHERE id = $1 AND state IN ('queued', 'deferred')` **before** issuing the click/Enter event.
3. **Crash Recovery:** Any row already in `sending` is never auto-retried blindly; recovery must either inspect the last outbound bubble in `chat.line.biz` for a match or transition the row to `failed` / operator review.

---

## 3. Reply-First Policy, Push Restrictions & Monthly Quota (300/Month Free)

Per `docs/research/line-messaging-quota.md`:

### 3.1 Reply Token First

1. **Zero Quota Cost:** `POST /v2/bot/message/reply` does **not** consume the monthly message quota.
2. **Primary Fast Path:** Whenever an inbound event arrives via `src/webhook/line.js`, MoonieX Care attempts to respond using the webhook `replyToken` first while the token is still valid.
3. **Reply-Token Lifetime:** **TBD** (not numerically specified in `docs/research/line-messaging-quota.md`, which notes only that `replyToken` is single-use and expires shortly after webhook event generation).
4. **Post-Expiry Routing:** Once the `replyToken` has expired:
   - Standard 1-on-1 care follow-ups are routed to the **LINE OA Manager browser sender (`chat.line.biz`)** on `winbox` (1-on-1 manual/OA Manager chat is also free of Messaging API push quota).
   - **API Push (`POST /v2/bot/message/push`) is used ONLY after `replyToken` expiry AND ONLY for important announcements.** Routine conversational replies must never burn push quota.

### 3.2 Quota Budget, Pre-Batch Check & One-Time 240 Alert

| Policy Parameter | Value | Notes |
| :--- | :--- | :--- |
| **Plan & Monthly Limit** | **300 / month (Thailand Free Plan)** | Hard cap at 300 quota-consuming messages (`GET /v2/bot/message/quota` returns `{"type": "limited", "value": 300}`). |
| **Pre-Batch Consumption Read** | `GET /v2/bot/message/quota/consumption` | Read **before each push batch** to obtain `totalUsage` (`projectedUsage = totalUsage + batchSize`). |
| **80% Alert Threshold** | **240 messages** (`ceil(300 * 0.80)`) | Fires **once** per billing month when `totalUsage` or `projectedUsage >= 240`, keyed by `(channel_id, YYYY_MM, 300, "80pct")`. |
| **Hard Stop** | `projectedUsage > 300` (or HTTP `429` monthly limit) | Halt all push batches immediately; reply-token and OA Manager 1-on-1 chat remain available. |
| **Quota Reset Time** | **TBD** | Exact reset timestamp/timezone handling marked **TBD** (`docs/research/line-messaging-quota.md` notes 1st of month 00:00 local account timezone, to be confirmed on live OA). |

---

## 4. Browser Sender Architecture (`winbox` LINE OA Manager)

For 1-on-1 care messages after `replyToken` expiry, the sender drives **LINE Official Account Manager (`chat.line.biz`)** inside the CEO's already logged-in browser session on `winbox`.

### 4.1 Wait for `winbox` Online

- The sender **waits for `winbox` online** before attempting any browser discovery or send cycle.
- If `winbox` is unreachable or offline, outbox rows remain in `deferred` (or use **fallback reply token via webhook** when a fresh inbound webhook turn provides a valid `replyToken`). The sender polls/waits for `winbox` connectivity to return rather than failing the queue or attempting to send from another machine.

### 4.2 (a) Browser Discovery via `relay-inventory.mjs` — No New Login

- Discover the CEO's existing authenticated browser session on `winbox` using:
  ```bash
  node scripts/relay-inventory.mjs --site chat.line.biz
  ```
- **No New Login:** The sender attaches only to an already logged-in `chat.line.biz` session. It must **never** enter credentials, trigger a login flow, or open a new unauthenticated session. If no logged-in session is present, trip the logout/session-expiry guard (see §4.6).
- **CDP Port:** **TBD**.

### 4.3 (b) Screen Claim per `ALL_Rules_Winbox_PCLease` vs. Headless/CDP

- **Headless / Pure CDP Needs No Lease:** As governed by `ALL_Rules_Winbox_PCLease`, work that operates purely over CDP / background DOM inspection without touching the physical `winbox` foreground window, mouse, keyboard, or desktop screen capture **needs no PC lease**.
- **Foreground / Screen-Touching Work Must Claim the Lease:** If the sender ever touches the physical screen (foreground window focus, OS-level click/keystroke, or desktop screenshot):
  1. Check `./scripts/pc-lease.sh status` first. If `PC: CEO`, **hands off immediately** and defer (`state = 'deferred'`).
  2. Claim with `./scripts/pc-lease.sh take --who "mooniex-care: OA chat batch"`.
  3. Call `./scripts/pc-lease.sh gate --as "mooniex-care: OA chat batch"` before each stage and stop immediately on exit `3` (CEO pressed **ใช้คอม**).
  4. Release immediately after the batch with `./scripts/pc-lease.sh give-back`.

### 4.4 (c) Process & Host Safety — Never Restart MT5 or `winbox`

- **HARD RULE:** A live real-money MetaTrader 5 Expert Advisor runs on `winbox` (`terminal64.exe`).
- The MoonieX Care sender must **never restart, kill, or interfere with `terminal64.exe` (MT5)** and must **never reboot or restart `winbox`**.

### 4.5 (d) Risk Table & Webhook Reply-Token Fallback

| # | Risk | Failure Mode / Impact | Mitigation & Control | Fallback |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Account suspension for automation** | LINE detects rapid or robotic browser activity on `chat.line.biz` and restricts or suspends `@mooniex` (`@587kfqpt`). | Enforce per-hour and per-day throttle ceilings (**TBD**), human-like jittered pacing, and immediate kill switch on any warning or captcha page. | Stop browser sender; use **fallback reply token via webhook** (`POST /v2/bot/message/reply`). |
| 2 | **Wrong recipient** | Chat list reorders dynamically as new messages arrive, causing a message to be sent to the wrong customer. | Mandatory **channel check** (`@587kfqpt` / `MoonieX Officials` / `@mooniex`) and **recipient readback** from the active chat header immediately before marking `sending` and clicking Send. Abort on mismatch. | Mark row `failed`, alert operator, and wait for webhook reply token or manual review. |
| 3 | **Session expiry** | CEO's `chat.line.biz` session cookie expires or redirects to `account.line.biz` login screen. | `relay-inventory.mjs --site chat.line.biz` check + DOM logout fixture detector. Never attempt automated login; trip kill switch and alert COO once. | Transition eligible rows to `fallback` (webhook reply token) or `deferred` until session is restored. |
| 4 | **UI change** | LINE updates `chat.line.biz` DOM selectors, breaking channel verify, recipient readback, or Send button location. | Strict selector assertions validated against saved DOM fixtures (`normal chat`, `warning`, `captcha`, `logout`). Fail closed before `sending` if any selector is missing or ambiguous. | Trip kill switch / fail closed; use **fallback reply token via webhook**. |
| 5 | **Double send** | Worker crashes right after clicking Send, or retries an in-flight message, sending duplicate texts to the customer. | Unique `idempotency_key` on `care_outbox`, **mark `sending` before click**, and require post-crash verification (or `X-Line-Retry-Key` UUIDv4 on API pushes). | Do not auto-retry `sending` rows without chat history check. |
| 6 | **PII in screenshots** | Diagnostic screenshots capture customer names, phone numbers, or financial/chat details and get committed or leaked. | **Never commit customer chat screenshots to git** (`.gitignore` all capture paths); prefer DOM text readback over pixel screenshots; purge ephemeral debug captures. | Log only redacted state and hashed/internal IDs. |
| 7 | **`winbox` contention** | CEO is actively using `winbox` (`PC: CEO`), or Cookie Run farm / another browser operator holds the desktop lease. | Use headless/CDP (needs no lease); if foreground GUI is ever required, obey `ALL_Rules_Winbox_PCLease` (`status`, `take`, per-stage `gate`, `give-back`) and yield immediately on exit `3`. | Keep rows `deferred` until contention clears, or fulfil via **fallback reply token via webhook**. |
| 8 | **`winbox` offline** | `winbox` is powered off, asleep, or unreachable over Tailscale/SSH. | Pre-flight reachability check. **Sender waits for `winbox` online** and leaves browser-bound rows in `deferred`. Never reboot `winbox` or touch MT5. | **Fallback reply token via webhook** (`src/webhook/line.js`) handles immediate replies while `winbox` is offline. |

### 4.6 (e) Inbound/Outbound Pipeline, Safety Checks, Throttling, Kill Switch & Fixtures

#### Inbound vs. Outbound Separation
- **Inbound:** Arrives exclusively from `src/webhook/line.js` into the LuNar chat flow / inbound queue (capturing `userId`, message payload, and `replyToken`). The browser sender does not scrape inbound chat lists as the primary ingestion source.
- **Outbound:** Drains strictly from `care_outbox`.

#### Channel Check & Recipient Readback (Pre-Send Gate)
Before every send in `chat.line.biz`:
1. **Channel Check:** Read the active Official Account header/switcher in `chat.line.biz` and assert that it matches **`MoonieX Officials`** / **`@mooniex`** / **`@587kfqpt`**. If another OA is open, abort immediately.
2. **Recipient Readback:** Open/select the target user thread, then read back the active chat header display name and thread ID from the DOM. Assert exact agreement with `care_outbox.recipient_display_name` and `care_outbox.recipient_id`.
3. **Pre-Click Commit:** Only after both assertions pass, update `care_outbox.state = 'sending'`, then trigger the send action.

#### Throttle Ceilings & Human-Like Jittered Pacing
- **Per-Hour and Per-Day Ceilings:** Outbound browser sends are gated by rolling **per-hour** and **per-day** message ceilings (exact numeric ceilings **TBD**). When a ceiling is reached, remaining `queued` rows transition to `deferred`.
- **Human-Like Jittered Pacing:** Between thread selection, focus, text entry, and send, the sender inserts randomized, non-uniform delays (e.g., jittered pause before opening thread, proportional typing/staging pause, and jittered inter-message cooldown) so event timing never exhibits fixed-interval bot signatures.

#### Kill Switch (Captcha / Warning / Logout)
- Before and after every navigation or send step, the sender runs the page state detector against the live DOM/URL:
  - **Trigger Conditions:** Any **`captcha`** challenge, LINE policy/rate **`warning`** banner/modal, or **`logout`** / login redirect (`account.line.biz`).
  - **Immediate Halt:** The sender stops all browser actions immediately and flips a persistent kill-switch flag (`care_sender_enabled = false`).
  - **Alert COO Once:** Sends a single deduplicated alert to the **COO** describing which trigger (`captcha`, `warning`, or `logout`) fired.
  - **Manual Re-Enable Only:** The kill-switch **flag stays off until a person re-enables it** after inspecting `chat.line.biz` on `winbox`. No cron, watchdog, or agent may auto-reset the flag.

#### Offline Test Fixtures (`captcha`, `warning`, `logout`, `normal chat`)
To test the DOM detector, channel/recipient readback, and kill switch deterministically without touching live customer chats (and with zero customer PII in git), the test suite maintains four sanitized HTML/DOM fixtures:
1. **`captcha` fixture:** Simulates a challenge / verification gate in `chat.line.biz`; must trip the kill switch, leave outbox row unsent, and emit the one-time COO alert.
2. **`warning` fixture:** Simulates an OA Manager warning banner/modal (e.g., automated activity or rate warning); must trip the kill switch and alert COO once.
3. **`logout` fixture:** Simulates an expired session or redirect to login; must trip the kill switch, forbid any login attempt, and alert COO once.
4. **`normal chat` fixture:** Synthetic, PII-free `chat.line.biz` conversation view for `@mooniex` (`@587kfqpt`, `MoonieX Officials`) verifying channel check, recipient readback, pre-click `sending` transition, and post-send bubble confirmation.

---

## 5. Open Parameters Marked TBD

| Item | Current Status | Source / Dependency |
| :--- | :--- | :--- |
| **CDP Port** | **TBD** | Port exposed by the logged-in browser on `winbox` discovered via `relay-inventory.mjs --site chat.line.biz`. |
| **Reply-Token Lifetime** | **TBD** | `docs/research/line-messaging-quota.md` notes single-use short expiry after webhook event generation, but exact seconds/TTL cut-off is **TBD**. |
| **Quota Reset Time** | **TBD** | Exact monthly quota reset boundary/timezone verification on the live `@587kfqpt` account is **TBD**. |
| **Exact Throttle Ceilings** | **TBD** | Exact per-hour and per-day outbound message ceilings for the `chat.line.biz` browser sender are **TBD**. |

---

## 6. Care Session + Escalation (`docs/plans/2026-11-19-mooniex-care-team.md` §2–3)

This section defines the **care session + escalation** architecture from `docs/plans/2026-11-19-mooniex-care-team.md` (§2–3, SomPong repo), specifying how customer answers are built, gated, escalated, and handed over to `care_outbox`.

### 6.1 `care` Role (`น้องมูน`, Sonnet 5.5, Own Unix User & Gate) and LuNar Cutover

| Attribute | Specification |
| :--- | :--- |
| **Role Key & Persona** | `care` — Customer Care Agent (แอดมินดูแลลูกค้า), persona **"น้องมูน" (Moon)**. |
| **Model** | **Sonnet 5.5** |
| **Team Lead / Supervisor** | SomPong (`coo`, Opus 5.5) — Head of Customer Care (หัวหน้าทีมดูแลลูกค้า); owns the playbook, reviews the queue and 21:00 TH digest daily, resolves escalations, and routes money/promises to the CEO. |
| **Isolation & Runtime** | Dedicated role row, separate tmux session, **own Unix user**, and **own gate** (`care` gate, following `docs/design/sompong-coo-session.md` and `family_gate`: events in, `reply`/`skip` out, plain text). Does **not** share SomPong's session. |
| **Answer Builder** | The **`care` role builds the answers** for customer threads and enqueues outbound message batches (up to 5 short bubbles per call) into `care_outbox` (§2). `care` never calls the LINE Messaging API directly. |
| **LuNar Cutover Rule** | **The old LuNar chat flow / `@mooniex` LINE agent is switched off ONLY after `care` answers live** (verified answering real chats in production during Phase 1 cutover). Until `care` is live and verified, the existing flow is not removed. |

### 6.2 Inbound `care_queue`, Immediate Ack & Hourly Round (`08:00–22:00 TH`)

1. **Webhook Ingest (`care_queue`, No Model at Ingest):**
   - When a customer writes to `@mooniex` (`@587kfqpt`), `src/webhook/line.js` records the inbound event in `care_queue` (`customer_id`, `text`, `media`, `received_at`, `reply_token`). No LLM runs during webhook ingestion.
2. **Immediate Ack (No Model, Free via Webhook `replyToken`):**
   - The first message in a quiet thread triggers an immediate fixed acknowledgement sent via the LINE webhook `replyToken` (`POST /v2/bot/message/reply`, 0 monthly quota consumed; sent immediately before the token expires):
     > `"ได้รับข้อความแล้วครับ แอดมินจะตอบภายใน 1 ชั่วโมง (เวลาทำการ 08:00–22:00 น.)"`
   - **Outside hours (before `08:00` or after `22:00` TH):** the ack must not promise "within 1 hour". It uses the night text instead (draft wording; the rule is from CTO 26 Nov; final text needs CEO OK):
     > `"ได้รับข้อความแล้วครับ แอดมินจะตอบในช่วงเช้า เริ่มตอบตั้งแต่ 08:00 น. ครับ"`
   - Rate-limited to **once per thread per `N` quiet hours** (**TBD**), never once per message.
3. **Hourly Round (`08-22 TH` / `08:00–22:00 TH`):**
   - A timer runs every hour on the hour from **`08:00` to `22:00` TH** (`Asia/Bangkok`). Messages arriving overnight after `22:00 TH` wait in `care_queue` for the `08:00 TH` round.
   - If `care_queue` has pending items, the timer wakes the `care` session **once** for the round, passing **one grouped event per customer thread** containing all messages received from that customer since the last round.
   - `care` processes all active threads in that turn and writes each outbound response (grouped up to 5 bubbles per API call) into `care_outbox`, which the sender drains under the reply-first and quota rules in §1–4.
4. **Active-Case Live Turns (Reply-Token Fast Path):**
   - While a customer thread is in an active goal-driven case (see §6.4), follow-up messages from that customer can wake `care` within a few minutes (**TBD**) so `care` can reply using the free webhook `replyToken` while it is still valid, continuing turn-by-turn until the goal is met, escalated, or the chat goes quiet.

### 6.3 Escalation to `coo` -> 3 Ranked Answers on One CEO Card -> Goal & FAQ Rule

`care` escalates to **`coo` (SomPong)** whenever a thread involves:
- **Money, rebates, complaints, or promises**; or
- **Anything `care` is unsure of, has never answered before, or cannot find in approved knowledge** (FAQ, memory, skills, or permitted systems).

The end-to-end escalation workflow is:
1. **Customer Holding Line:** `care` invokes `escalate` and sends a short holding reply to the customer: `"ขอเช็คให้ก่อนนะครับ"`.
2. **`coo` Fact Lookup & Analysis:** SomPong (`coo`) analyses the escalated thread and looks up the facts across partner tools, research, and customer history.
3. **3 Ranked Answers on One CEO Question Card:** `coo` raises **one CEO Run Inbox question card** (`ask_ceo` / `tools/ask_run.py ask`) presenting **the 3 most likely answers, ranked (`1`, `2`, `3`)**.
4. **CEO Selection or Policy Instruction:** The CEO taps `1`, `2`, or `3` (or selects none and writes his own). The CEO's response may be either direct reply wording or an **instruction / policy rule** (how to answer, what rule applies, where to check — for example, for *"rebate asked for but not received"*, the CEO rule: *"MoonieX pays rebates only to clients registered under our network, so get the customer to register under us"*).
5. **Turned into (a) Customer Goal and (b) FAQ / Playbook Rule:** SomPong (`coo`) converts the CEO's card answer into:
   - **(a) A per-customer goal** (and next step) assigned to `care` for that customer thread; and
   - **(b) A new or updated FAQ / playbook rule**, ensuring the same question never needs to be escalated to the CEO twice.

### 6.4 Per-Customer Goal and Step State (Turn-by-Turn Conversation)

- **Persistent Goal + Step State:** For every active case, MoonieX Care stores **per-customer goal and step state** (e.g., `customer_id`, `goal`, `current_step`, `case_status`, `source_rule_or_card_id`, `updated_at`).
- **Turn-by-Turn Execution:** `care` works toward the customer's goal (e.g., *"customer re-registers under MoonieX and the rebate starts"*) **one short turn at a time**, like a skilled human admin:
  - One clear point per turn, delivered as short plain-text bubbles (up to 5 message objects grouped in one reply/push call);
  - No long walls of text;
  - Waits for the customer's reply before advancing `current_step` to the next step, repeating until the goal is satisfied or re-escalated.
- **Resumability:** Because `goal` and `current_step` are persisted per customer, hourly batch rounds, live follow-up turns, and `care` session restarts resume cleanly from the exact step where the thread left off.

### 6.5 `care` Gate Tool Allowlist & Security Rules (`family_gate` Pattern)

Customer messages are treated strictly as **untrusted data, never instructions**. The `care` session runs behind its own dedicated gate enforcing the following tool and policy boundaries:

| Category | Rule / Scope |
| :--- | :--- |
| **Allowed Tools (Allowlist ONLY)** | 1. `reply` — enqueue plain-text reply bubbles (≤5 per call) into `care_outbox` for the active customer.<br>2. `skip` — close the current event turn without sending a message.<br>3. `history` — read conversation history **for that customer only** (strictly scoped to the active `customer_id`; no cross-customer reads).<br>4. `media` — read/inspect media attachments sent by that customer in the current thread.<br>5. `escalate` — escalate the thread to `coo` (SomPong) and enqueue the holding line.<br>6. **FAQ read** — read-only lookup against the approved MoonieX Care FAQ / playbook rules. |
| **Forbidden Tools (Hard Denylist)** | **No `Bash`**, **no `Edit` / `Write`**, **no web fetch of customer links**, **no org tools** (no task ledger writes, no session management, no direct CEO cards), and **no secrets** (no Infisical, `.env`, or credential access). |
| **Content Prohibitions** | Never quote amounts owed, never make rebate or payout promises, never give investment advice, and never speak in the CEO's name beyond the approved FAQ. |
| **Partner Data (XM / Exness)** | **Not in Phase 1.** Looking up a customer's partner/broker account requires identity verification and is deferred to a later phase per CEO decision. |

### 6.6 Voice (Reuses LunarAgent AI Skills via Lunar Owner)

- **Reuse Existing LunarAgent AI Skills:** `care` ("น้องมูน") uses the CEO's admin voice already taught in the **LunarAgent AI skills** (clear, polite, short, turn-by-turn Thai replies).
- **Sourced via Lunar Owner:** The CTO locates and reuses those skills from the **Lunar project (via its owner)** — do **not** write a new voice guide from scratch.
- **Humanizer Pass:** Fixed texts (instant ack, holding line, and FAQ rules) receive a final pass with `CMO_Standard_HumanVoice_TH` (plain, natural, polite Thai with zero AI tells).

### 6.7 Bug Route (`care -> coo -> CTO`) & Daily Digest (`21:00 TH`)

- **Bug & System-Change Route (`care -> coo -> CTO`):**
  - When `care` hits a bug, tool failure, or needed system adjustment, `care` reports it to **`coo` (SomPong)**.
  - **`coo` sends the bug/fix request straight to the `CTO` to fix**, with **no CEO round-trip**.
  - Exception: Anything involving money, secrets, or permanent deletion still goes to the CEO (`ALL_Rules_Approvals`).
- **Daily Digest (`21:00 TH`):**
  - Every day at **`21:00 TH`**, a digest is sent to **`coo` (SomPong)** covering:
    1. Total chats received that day;
    2. Counts and status of **answered / escalated / open** threads;
    3. Top customer questions and candidate **FAQ updates**.

### 6.8 Care Session & Escalation Risk Table and Additional TBDs

| # | Risk | Failure Mode / Impact | Mitigation & Control |
| :--- | :--- | :--- | :--- |
| 1 | **Prompt injection via customer chat** | A customer sends adversarial text attempting to run shell commands, read other customers' chats, or extract secrets. | Customer text is data only; the `care` gate enforces a strict allowlist (`reply`, `skip`, per-customer `history`, `media`, `escalate`, FAQ read) with **no `Bash`, `Edit`, web fetch, org tools, or secrets**, running under its **own Unix user**. |
| 2 | **Premature LuNar switch-off or dual-reply overlap** | Switching off the old LuNar chat flow before `care` is verified drops customer chats; running both without cutover coordination causes double replies. | **Old LuNar chat flow is switched off only after `care` answers live** (verified on real chats in P1); cutover flips the outbound producer atomically once `care` is confirmed healthy. |
| 3 | **Unauthorized financial / rebate promise** | `care` guesses an unverified rebate rule or promises a payout. | Hard rule to `escalate` money, rebates, complaints, promises, and any unknown question to `coo` → 3 ranked answers on one CEO card → codified into a per-customer goal and FAQ rule. |
| 4 | **Context loss across hourly rounds** | Multi-turn troubleshooting forgets what step the customer was on between hourly batches or after a restart. | Persist **per-customer goal and step state** in the hub so every hourly round, live turn, or session restart resumes at the exact step. |
| 5 | **Push quota exhaustion from multi-line replies** | Sending multiple separate push API calls per turn burns the 300/month free quota rapidly. | Group up to 5 bubbles into one API call, prioritize valid webhook `replyToken` (free instant ack + active-case live turns) and `chat.line.biz` browser sender (§3–4), and confirm LINE per-call vs. per-bubble quota counting (**TBD**). |

**Additional §6 Parameters Marked TBD** (preserving all §1–5 TBDs above):
- **Instant-Ack Quiet-Thread Window (`N` hours):** **TBD** (minimum quiet interval before a returning thread receives another automatic instant ack).
- **Active-Case Live-Turn Window:** **TBD** (exact minute cut-off and trigger threshold for answering active-case turns immediately via webhook `replyToken` between hourly rounds).
- **LINE Push Quota Counting (Per Call vs. Per Bubble up to 5):** **TBD** (CTO to verify from LINE Messaging API documentation whether one push request carrying up to 5 message bubbles counts as 1 message or `k` messages against the 300/month free quota).

