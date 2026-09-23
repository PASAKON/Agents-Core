# BL reply-bot research — task-35176126

**Why:** EP54 asked viewers to comment a keyword; one person commented "เช็คโบรค" and
nobody answered. CEO wants EP56+ to ship with the facts a bot needs to answer
comments and DMs correctly. This doc answers what a bot can actually do on
TikTok today, before that pack gets designed. **Read-only research — nothing
built, posted, replied to, or configured.**

---

## Q1. Today's DM bot for `black_liquidity`

### Is it live?
- **Wired: yes.** `mooniex-claudeflow` (`/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow`)
  `src/webhook/tiktok.js` handles the flow described in the task: SendPulse
  webhook → buffer 3s+1.5s grace → `generateReply()` (`src/webhook/claude.js`)
  → SendPulse push. Docker container `mooniex-claudeflow-claudeflow-webhook-1`
  confirmed running on Contabo VPS (`docker ps`, "Up 5 days", started
  2026-09-17T14:02:52Z).
- **Traffic: dead for 50 days.** Direct read-only query against Supabase
  `claudeflow_conversations` (`platform='tiktok'`, `page_id='black_liquidity'`,
  run from the VPS 2026-09-23 using the app's own deployed Supabase client, no
  writes) — **182 messages total, ever.** The single most recent row is a
  **user** message from **2026-08-04T03:27:36 UTC**, with no assistant reply
  logged after it (the last logged assistant reply was 2026-07-29). So either
  the bot errored silently on that message (its error path pushes an apology
  via `sendPushMessage` directly, which is never written to
  `claudeflow_conversations` — `tiktok.js` lines 119-125), or it was never
  answered. Either way: **zero BL TikTok DM traffic in the 50 days before this
  task**, spanning EP54 and EP55.
- **Confidence: HIGH** — two independent read-only checks (docker log grep,
  live Supabase query) agree.

### What system prompt/knowledge does it use? Does it know about episodes?
**It is not a BL bot. It is the shared MoonieX/"Lunar" broker-onboarding and
rebate assistant running under the `black_liquidity` account slug.**
- Live system prompt pulled directly from Supabase
  `claudeflow_webhook_accounts` (query run 2026-09-23): **28,357 chars.**
  Opens "You are Black Liquidity's Admin Assistant" but its own IRON-RULE
  self-identity block instructs it to introduce itself as **"ผมชื่อ Lunar
  ครับ เป็น AI admin ของทีม MoonieX ดูแลเรื่องสมัครบัญชี + Rebate + ห้อง
  VIP"** — contradicting its own opening line.
- Contains (line numbers from the closest full copy on disk,
  `ops/backups/system_prompt_tiktok_black_liquidity_2026-09-17T14-01-48-815Z_pre_broker_sweep.txt`,
  609 lines, which git history confirms is still live today — see below):
  broker registration/affiliate links for Exness (`one.exnessonelink.com/a/mvwpif5crx`,
  L411/465) and XM (`clicks.pipaffiliates.com/...`, L425/480) with affiliate
  codes `MOONIEX`/`MNFUNDS` (L406/435/483); a per-lot rebate rate table
  (L515-529, e.g. XM Gold $15/lot); an MT4/MT5 account-number collection flow
  for "verification" (L56-72, L453-502); explicit broker-recommendation
  language ("Recommend ONLY XM first," L49; "แนะนำให้เปิดบัญชีใหม่กับโบรคอื่น
  เช่น XM ครับ," L495); and, at the bottom, a sponsor rate card that belongs
  to a **different channel** (`@mypasakon`, L577-609).
- **Episodes/BL content: none.** `episode`/`EP5` and BL-script framing do not
  appear anywhere in the prompt. Knowledge base (`claudeflow_knowledge`) has
  no `black_liquidity`-specific rows either — `accountStore.getTenantSlug()`
  falls back to the shared `'mooniex'` tenant whenever an account has no
  `tenant_slug` of its own, and no seed/onboarding script sets one for this
  account (`grep -rl black_liquidity scripts/` matches only unrelated
  video-pipeline files).
- **Confidence: HIGH** — confirmed both by a live Supabase read (system
  prompt contains `XM`✓ `Exness`✓ `rebate`✓, `QRS`✗ `Interstellar`✗) and
  independently by reading the on-disk backup + git history.

### Does it respect BL compliance?
**No.** `.claude/skills/blackliquidity-script/SKILL.md` §Compliance requires:
never name a broker the channel earns from; teach the check, don't rank
brokers; CTA points at knowledge, never an account. The live prompt breaks
all three right now — active XM/Exness affiliate links, a rebate table, and
an account-number collection flow, sent to anyone who DMs the account.
- **Why it's still like this:** a 2026-09-17 "broker sweep" did touch this
  exact prompt, but only removed **regulator-flagged** brokers (QRS Global,
  Interstellar/FISG, Axi Select — named in DSI's June 2026 raid, see
  `project-forex-thai-legal-exposure` memory), across commits `4dd3ea77`,
  `290d6d16`, `0bb418e3`/`5c6d0503` (all 2026-09-17). Every one of those
  commit messages explicitly states XM/Exness were kept: *"kept XM/Exness
  untouched."* This was a regulator-compliance pass for the whole
  MoonieX/Lunar bot fleet, not a BL-specific compliance pass — nobody has
  ever separated BL's account from that shared prompt.
- No commit since 2026-09-18 touches this account's prompt, backups, or
  tenant scoping — **this is the prompt live today, 2026-09-23.**
- **Confidence: HIGH.**

---

## Q2. Comments

### 2a. Does SendPulse deliver comment events, or only DMs?
**DM-only.** SendPulse's TikTok flow-builder supports exactly 4 trigger
types: Welcome message, Standard reply, Unsubscribe, Custom
(Keyword/A360 event) — [sendpulse.com/knowledge-base/chatbot/tiktok/create-flow](https://sendpulse.com/knowledge-base/chatbot/tiktok/create-flow).
No comment trigger exists; SendPulse's own marketing page lists "Stay on top
of comments" as **"Soon"** (unshipped) —
[sendpulse.com/features/chatbot/tiktok](https://sendpulse.com/features/chatbot/tiktok).
This matches the code: `tiktok.js` only branches on
`eventType === 'incoming_message' || eventType === 'new_subscriber'`.
**Confidence: HIGH.**

### 2b. Can we read/reply to organic comments via any official API?
**Not for a normal creator/business account on organic (non-ad) video
comments, as far as could be confirmed.**
- TikTok API for Business has a "Reply to a Comment" endpoint, but it's
  documented as **ads-scoped**: replies to first-level comments under an
  advertiser's *ads*, keyed by `advertiser_id`+`ad_id`+`tiktok_item_id` —
  [business-api.tiktok.com/portal/docs/reply-to-a-comment/v1.3](https://business-api.tiktok.com/portal/docs/reply-to-a-comment/v1.3).
  **Confidence: MEDIUM** (portal page is a JS-rendered SPA; read via search
  snippet + the SDK's markdown docs, not the raw page).
- A separate "reply to a mention in comments" endpoint exists for organic
  mentions of the business handle; its exact scope (own videos vs. mentions
  elsewhere) could not be confirmed — portal requires an authenticated
  login. **Confidence: LOW, unresolved.**
- TikTok's Research API has a read-only "Query Video Comments" endpoint
  (`research.data.basic` scope, max 100/request, PII redacted) —
  [developers.tiktok.com/doc/research-api-specs-query-video-comments](https://developers.tiktok.com/doc/research-api-specs-query-video-comments).
  **Read-only, no reply**, and generally gated to qualified
  researchers/academic use rather than ordinary business accounts.
  **Confidence: MEDIUM.**
- **Net: no confirmed general-availability path today for BL to
  programmatically read-and-reply to organic comments on its own videos.**

### 2c. Cost
No published price found for comment-reply access — it's gated by app
review/business verification, not a metered paid tier, in everything
surfaced. **Confidence: LOW-MEDIUM** (absence of evidence, not strong
confirmation — a human should check the Business Center portal directly).

---

## Q3. Messaging a commenter

### 3a. Can BL DM someone who only commented, never messaged?
**No — TikTok requires the user to message first.** Corroborated across three
independent integration-platform docs describing TikTok's own Business
Messaging API rules (TikTok's own portal pages are JS-rendered and blocked
direct fetch, so these are secondary sources quoting the primary rule):
business accounts can only reply within a **48-hour window** opened by the
user's own first message, capped at **~10 business messages per open
window** (anti-spam), and **cannot proactively initiate** a conversation with
someone who hasn't messaged first — [SleekFlow](https://help.sleekflow.io/en_US/tiktok-business-messaging/tiktok-business-messaging-channel-overview),
[Qiscus](https://documentation.qiscus.com/omnichannel-chat/tiktok-direct-message),
[Respond.io](https://respond.io/help/tiktok/tiktok-overview). This is the
same shape as Meta/Instagram's known messaging-window rule. Thailand is APAC,
which TikTok's Business Messaging API covers region-wise.
**Confidence: MEDIUM-HIGH.**

### 3b. Compliant path
**Public comment reply / pinned comment that tells the viewer to DM a
keyword themselves** — the viewer has to be the one to open the DM, which
satisfies the user-initiated rule. A comment-triggered auto-DM is not a
supported or compliant flow. TikTok's Community Guidelines (Integrity/
Authenticity) also generally discourage comment-automation "tricks," which
argues against any workaround. Practitioner source (not TikTok's own docs):
[instantdm.com/blog/tiktok-comment-to-dm](https://instantdm.com/blog/tiktok-comment-to-dm).
**Confidence: MEDIUM, third-party sourced.**

### 3c. Caveat
TikTok's own policy pages (`business-api.tiktok.com/portal/docs/*`,
`developers.tiktok.com`) are JS-rendered SPAs that returned only page titles
to automated fetch. Every Q2b/Q3 finding rests on search snippets of those
pages plus independent secondary sources that quote the same rules — not a
direct read of TikTok's raw doc text. **Before this becomes load-bearing for
a compliance decision, a human should verify directly in a logged-in TikTok
Business Center portal.**

---

## Q4. Where a promised deliverable can live

EP54's actual CTA (from `prototypes/bl54-worker/project/line_timing_raw.json`):
comment **"เช็ครีเบต"** → promised **"ลิสต์คำถามที่ถามโบรกเองได้"**.
EP55's CTA (`prototypes/bl55-script/SCRIPT.md` line 59, `[SUMMARY-8]`):
comment **"เช็กก่อนฝาก"** → promised **"ลิสต์เว็บหน่วยงานกำกับที่เช็กใบอนุญาตได้จริง"**.

Given Q2/Q3: BL cannot see either keyword today (SendPulse is DM-only, no
comment webhook exists) — this is structurally why EP54's commenter got no
reply, not a one-off bug. And even with a comment-reading API, BL still
couldn't auto-DM that commenter; TikTok requires the user to message first.

The deliverable content itself (a question checklist / a list of regulator
websites) is compliant on **any** channel — it never names a broker BL earns
from. The risk is which **channel** carries it, not the content:

| Option | What it is | Compliance angle |
|---|---|---|
| **Image card in the DM reply** | Bot sends a checklist graphic when a user DMs the keyword | Fine content-wise, but `tiktok.js` is explicitly **text only — no image support** (file docstring, line 8) — needs dev work; SendPulse's push API supports images generally, just not wired here |
| **Text reply in DM** | Bot sends the checklist as plain text | Already works mechanically (text sending is live) — but only reaches someone who DMs first, so still needs a pinned-comment/caption CTA telling viewers to *DM* the keyword, not comment it |
| **Link to a page** | DM/pinned-comment sends a link to a static checklist page | Closest to the "affiliate link" line the CEO's ruling targets — must be a pure content page, no broker link, or it reads exactly like what the ruling forbids |
| **LINE OA** | CEO's designated channel for anything affiliate-adjacent (closed channel) | Lowest compliance risk long-term, but BL has **no existing LINE OA** (not found anywhere in code or wiki) — net-new build, and unnecessary for content that carries no broker link in the first place |

**The channel that's actually broken right now isn't a missing deliverable
format — it's that the one channel BL already has (TikTok DM) is not safe to
hand anything to**, because it shares infrastructure and prompt with the
MoonieX rebate bot. Sending a compliant checklist from an account that will,
in the same conversation, also push XM/Exness rebate talk defeats the
purpose and is a screenshot risk against BL's own on-screen disclaimer.

---

## Build options

**Option A — Decouple BL's DM bot from the shared Lunar/rebate prompt, then
answer in DM (recommended, do first)**
- *Effort:* small-medium. Give `black_liquidity` its own `tenant_slug` and a
  BL-specific system prompt (no broker tools, no rebate/account content) in
  `claudeflow_webhook_accounts`; seed the EP54/EP55 checklists as content the
  bot can serve on keyword match. DM text-sending already works.
- *Cost:* $0 — no new paid API, dev time only.
- *Risk:* LOW once decoupled. Reach is capped to people who actively DM
  after seeing a pinned-comment/caption CTA — comments themselves stay
  invisible to the bot (Q2a), so some viewers (like EP54's commenter) will
  still be missed unless they take that extra step.
- This is not optional scope creep — the account is *live right now* pushing
  broker-affiliate content under the BL brand, independent of whether EP56's
  pack gets built.

**Option B — Public/pinned comment reply carrying the content directly (do
alongside A, no bot needed)**
- *Effort:* tiny — a human (or, later, an approved TikTok-for-Business
  comment-reply integration, which is ads-scoped per Q2b and not confirmed
  available for organic video comments) replies to or pins a comment with
  the checklist text itself.
- *Cost:* $0 for a manual reply; unknown/unconfirmed for automated comment
  reply via TikTok API for Business (app review required, no published
  price found).
- *Risk:* LOW compliance risk (public, no broker names) but ongoing labor
  cost if done manually, since automated comment reply on organic videos
  isn't confirmed to exist.

**Option C — Stand up a BL-specific LINE OA (future, not needed for EP56)**
- *Effort:* large — new OA, new webhook, new tooling.
- *Cost:* LINE OA itself is free to create; per-message costs apply at
  volume under LINE's own pricing tiers.
- *Risk:* LOW compliance risk (matches the CEO's closed-channel ruling) but
  is more infrastructure than a comment-promised checklist needs today —
  worth keeping in mind only if BL ever wants to do anything monetizable,
  which its own compliance rules currently forbid.

**Recommendation: A + B, not C.** Fix the account that's live and
non-compliant right now (A), and cover comments the only way TikTok/SendPulse
actually allow today — content in the public reply itself (B) — since
neither SendPulse nor TikTok's messaging rules let BL auto-DM a commenter.
LINE OA (C) is future scope; nothing here requires it yet.
