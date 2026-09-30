# Brief — Chatudo, October build (G0 16 Oct → G1 31 Oct)

Written by CTO session `cto-56f2156e` (Contabo), 2026-09-28, after the CEO approved the plan and
said "ทำเลย". This brief is the whole hand-off. Read it, then `/session-open`.

- **Plan (source of truth):** `docs/plans/chatudo-build-plan-2026-09-28.html` →
  https://claude.ai/artifact/T3ZK3rbSZzo7D4zYyr64At (work-package codes O*/C*/N* come from it)
- **CMO plan it implements:** https://claude.ai/artifact/RGs4f2GGoffxXSjX7vxTQf §#plan
- **Audit of the code it builds on:** memory `project_chatudo_build_plan_2026_09.md` (ClaudeFlow `42590d5`)

## Suggested Entry Problem
"Chatudo พร้อมรับร้านนำร่องบน LINE ภายใน ศ. 23 ต.ค. 18:00 โดยยื่น Meta ทัน ศ. 9 ต.ค. และผ่าน G0 ศ. 16 ต.ค."
DoD: (1) Meta Business Verification + App Review submitted, screenshot of the submitted state;
(2) G0 report: ≥70% sendable without edit, 0 price errors, 100% handoff on 200 replayed chats;
(3) a non-MoonieX tenant on the Chatudo instance answers a LINE message in draft mode and its
admin approves it from the shop's own inbox page; (4) security_engineer sign-off on tenant isolation.

## CEO decisions 2026-09-28 (do not re-ask)
| # | Decision |
|---|---|
| D1 | Separate Chatudo **instance** on the existing Chatudo Supabase `gcjdirrtvybhvghjtscf` (account pass.gob2). Code stays in **MoonieX-ClaudeFlow** (no repo split, CEO 2026-07-31). Same image, own container, own env, own DB, own domain (plan: `api.chatudo.com`). |
| D2 | Public site in **PASAKON/Chatudo-Webapp**. HQ row approved + pushed (HQ `8b24b45`); cloned at `/opt/MoonieXHQ/Projects/Chatudo/Webapp` (README only). Site only; never bot code or customer data. |
| D3 | Meta submission through **Dorsine Gobb** (winbox FB identity that holds the Chatudo page; the Mac PASAKON identity is ads-banned). CEO presses the final submit. |
| D4 | AI spend cap **$20** for now. Use Claude Code sessions / Gemini subscription / ChatGPT subscription instead of API in the early phase; move to API when the market grows. Dev work and anything internal runs on subscriptions ($0). |
| D5 | **No demo yet.** O5 and C4 are parked until the CEO says otherwise. |

## Still open with the CEO (asked in cto-56f2156e; answers get forwarded here — do not ask again)
1. Legal identity for Meta Business Verification (company or individual) + the documents.
2. chatudo.com: registered at Namecheap 2026-08-02, parked. Confirm it is his + give DNS access
   (relay login, or he points the nameservers to Cloudflare).
3. Live pilot-shop chats (from 23 Oct) and the G0 run on a **paid API** inside the $20 cap.
   CTO's reason: my understanding is that consumer subscriptions (Claude, ChatGPT, Gemini) are
   for the subscriber's own use. They do not cover a service to third parties. A ban would take
   down the Claude account the whole org runs on. G0 must also test the same model the shops will
   get. Estimate (not measured): ~$0.004/turn on a Flash-class model → G0 ≈ $4. **Until he answers,
   spend $0 on API.**

## October work, in dependency order (dates are the plan's)
| Code | Work | Due | Repo | Notes |
|---|---|---|---|---|
| O2 | Generic shop agent: per-tenant persona, scope, hours, handoff contact; no forex tools | Wed 7 Oct | ClaudeFlow | Foundation. Today's agent (`src/webhook/claude.js`) has ~190 broker refs, `APP_NAMES`, MoonieX flex templates. Build a separate agent profile. Leave the MoonieX one alone. |
| O3 | chatudo.com v0: home, pricing (CMO table: Founding ฿990 · Starter ฿1,990 · Pro ฿3,990 · Business ฿9,900), privacy, terms, data-deletion | Tue 6 Oct | Chatudo-Webapp | Thai public copy: **no em dash** (IRON §39). Positioning: "ระบบผู้ช่วยแอดมิน" (it helps the admin and does not replace them). Hosting is the CTO's call; a static build served from Contabo behind Traefik needs no new account. |
| O4 | Chatudo instance: compose service, env, all migrations onto `gcjdirrtvybhvghjtscf`, Traefik route | Tue 13 Oct | ClaudeFlow | Secrets into `.env` may need the CEO → ALL_Protocol_RunInbox, never a `!` in chat. Keep `COMPOSE_PROJECT_NAME` distinct from MoonieX's. |
| O6 | Draft-everything mode per tenant + store every draft vs the text actually sent | Fri 9 Oct | ClaudeFlow | Today `approvalGate.js` holds only low-confidence LINE replies for one slug; `assist/draft.js:draftReply` is test-only; `claudeflow_assist_examples` already has `suggested_answer/final_answer/outcome`. |
| C1 | Meta Business Verification + App Review (Messenger + IG) for app "Chatudo" | **Fri 9 Oct 18:00** | ClaudeFlow + winbox browser | Needs O3 URLs live + native Messenger working on our own Chatudo page (native Graph path exists in `src/webhook/meta.js`, never carried traffic) + screencast. Browser work on winbox = browser_operator + ALL_Rules_Winbox_PCLease + a replay script (IRON §42). |
| C2 | Replay test on 200 MoonieX chats, criteria 1–3, CEO eyeballs 30 | **Fri 16 Oct 18:00** (G0) | ClaudeFlow | Harness Tue 13, run Wed 14, fix Thu 15, report Fri 16. Chats live in MoonieX Supabase `tlokhyqpthvxabweekps` (`claudeflow_conversations`, `claudeflow_lunar_turns`); read-only export. Price check needs a price list → label set. |
| O7 | Tenant isolation: inbox API + SSE filter by tenant, 7 unscoped tables, encrypt shop tokens, per-shop admin login | Fri 16 Oct | ClaudeFlow | **No outside shop before security_engineer signs this off.** Shared `x-api-key` today, no tenant filter. |
| C3 | Onboard an outside shop on LINE (tenant + KB from its page/site) + the shop's own approval page | **Fri 23 Oct 18:00** | ClaudeFlow (+ UI) | Inbox UI today lives in mooniex.com (Vercel). The shop-facing page must not be on mooniex.com. Time every install step; the target is ≤1 hour. |
| O8 | Handoff per shop (alert that shop's admin on LINE) | Fri 23 Oct | ClaudeFlow | Today hard-coded to pass.gob1 email + one Telegram chat. |
| O9 | PDPA: data-processing agreement draft + retention/auto-delete | Fri 23 Oct | ClaudeFlow + site | No purge job exists today. CEO approves the text. |
| O10 | Uptime check, alert, DB backup, outage runbook | Fri 23 Oct | ClaudeFlow | Before the first pilot. |
| O1 | Outreach tracker (Google Sheet: 450 shops, 4 segments, day-3/day-7 follow-ups, funnel counts for Monday 10:00) | Wed 30 Sep | — | CTO directly, no DEV. CEO starts outreach 1 Oct. |
| O11 | Install ≥7 pilots, time each, same-day bug fixes | Sat 31 Oct | — | G1. |

Serialize tasks that touch `approvalGate.js`, `adminInboxApi.js` or the agent files (O2 → O6 → O7).
O3 and O4 are disjoint from them and can run in parallel from day 1.

## Plan from 1 Oct (CTO cto-4bb20df8, written 30 Sep 21:30 Thai time)

### Status on 30 Sep

- **Merged:** O1 (live Sheet), O2, O3 (code only), O4 (code only), O6, O7a and O7b.
- **In progress:** O7b-4 security fixes (task-d0ba070f). Items 1–7 are done, items 8–11 are running.
- **DoD:** 0/4.

At most **2 sonnet workers run at the same time**, because the weekly limit stopped a worker on 29 Sep. Mechanical items may go to Jules instead: ClaudeFlow is on the allowlist and marked prod_adjacent.

### Build waves

| Wave | Work | Start | Done by | After |
|---|---|---|---|---|
| 1a | O7b-4: finish, review, merge | now | Thu 1 Oct | — |
| 1b | **C2 G0 harness** (details below) | Thu 1 | Tue 13 | — (new files only) |
| 2a | **Bring-up prep** (details below) | O7b-4 merged | Tue 6 | 1a |
| 2b | **C3 shop inbox page** (details below) | O7b-4 merged | Fri 9 | 1a |
| 3a | **Meta native draft gate** (details below) | O7b-4 merged | Tue 6 | 1a |
| 3b | **O8 per-shop handoff:** alert the shop's own admin on LINE, replacing the hard-coded pass.gob1 email and single Telegram chat | 3a merged | Mon 12 | 3a (both touch `approvalGate.js`) |
| 4 | **O9 + O10** (details below) | Mon 12 | Fri 16 | — |

**Wave 1b, C2 G0 harness:**
- Replays 200 MoonieX chats through the shop agent, using a MoonieX-as-shop profile and a price list.
- Scores the G0 criteria: sendable without edit ≥70%, wrong price 0, handoff 100%. The CEO also checks a sample of 30 by eye.
- Tests use a mocked LLM.
- The real drafting runs on a Claude Code session at $0 (CEO 28 Sep).
- The export from MoonieX Supabase is read-only and runs under `infisical run`.

**Wave 2a, bring-up prep:**
- O4 F2: add a `.dockerignore`. There is none on main, so `COPY . .` copies any env file into the image.
- Change `scripts/chatudo/compose.sh` to run under `infisical_setup.py run … --path /chatudo`.
- Specify the Run Inbox card that mints the encryption key.
- List the values the CEO has to enter, matched against `.env.chatudo.example`.

**Wave 2b, C3 shop inbox page:**
- A page in `/app`: the list of held drafts, with approve, edit-then-send and reject, all through the existing API.
- The shop's knowledge base, taken from its page or site text. Ingestion is offline and tested.
- This page is DoD 3's "approves from the shop's own inbox page".

**Wave 3a, Meta native draft gate:**
- This is the O6 GAP: native Messenger and IG replies are held as drafts too.
- The C1 screencast needs it.
- Until it merges, no shop may be on Messenger or IG.

**Wave 4, O9 + O10:**
- O9: a retention and auto-delete job, and a draft data-processing agreement. The CEO approves the agreement text.
- O10: uptime check, alert, Chatudo DB backup and an outage runbook.

### Gates on the calendar

- **Fri 9 Oct, C1 Meta submit.**
  - It needs the answers to Q1 and Q2 by **Mon 5 Oct 10:00**. Otherwise C1 slips past 9 Oct, because the site needs DNS by Tue 6 for the privacy and data-deletion URLs.
  - O3 goes live on Tue 6. Its 11 `site.config.json` placeholders need the legal name and contact details from Q1.
  - The screencast is recorded on winbox with the Dorsine Gobb Facebook account, by a browser_operator that leaves a replay script (IRON §42).
- **Tue 13 Oct, O4 bring-up.**
  - The CEO enters the values in Infisical `/chatudo`.
  - DNS: `app.chatudo.com` and `api.chatudo.com`.
  - Apply the schema, then run the security smoke test (task-8ae7a7c6, steps 0–7). A pass there is **DoD 4**.
- **Wed 14 – Fri 16 Oct, G0.**
  - Run on Wed 14, fix on Thu 15, report on Fri 16. The report is **DoD 2**.
  - If G0 fails, the pilot moves back 2 weeks (CMO plan).
- **Mon 19 – Fri 23 Oct, first outside shop on LINE in draft mode.**
  - Time the install; the target is ≤1 hour.
  - The shop's admin approves a draft from the page built in 2b. That is **DoD 3**.
  - It needs a shop that agreed during outreach, which is the CEO's and CMO's lane.

### Path to ฿15,000 MRR (CEO 30 Sep: "เป้าหมายเดือนหน้าฉันอยากได้อย่างน้อย 15000 บาท … ทำให้เสร็จทีละ Step")

**Target:** paying shops × price ≥ ฿15,000 at the CMO's first-money checkpoint, **Mon 30 Nov 2026 18:00**. That checkpoint is November because the CMO plan (artifact RGs4f2GGoffxXSjX7vxTQf `#plan`) bills no shop in October. The CMO's own November target is 8 shops and ฿12,000 (pass ≥6 / ฿8,000, stretch ≥11).

**Math.** Everything marked (O) is the CMO model's estimate; nothing has been measured yet.

| Pricing | Paying shops needed | Pilots (80% pay, O) | Owners reached (22% → pilot, O) | Shops contacted (10% reach owner, O) |
|---|---|---|---|---|
| Average ฿1,500 (CMO model ARPU) | 10 | 13 | ~59 | ~590 |
| All Founding ฿990 | 16 | 20 | ~90 | ~900 |

The CMO price table sets Founding at ฿990 for the first 2 months and the first 30 shops. So every shop billed in November is a Founding shop, and the ฿1,500 ARPU in the model does not hold in November. Priced as Founding, 8 shops = ฿7,920, which is below the CMO's own pass line. The CMO decides whether November goes to 16 Founding shops or a mix that includes Starter at ฿1,990.

| # | Step | Owner | Due | Done when |
|---|---|---|---|---|
| 1 | Lock the target and the math; tell the CMO | CTO | Wed 30 Sep | The CMO letter is sent and this table is committed |
| 2 | Outreach from the O1 Sheet, 20–30 a day, 3 messages × 4 segments; ~590–900 contacts by mid-Nov instead of 450 | CEO + CMO | from Thu 1 Oct | The Monday 10:00 funnel counts, computed in Thai time |
| 3 | O7b-4 security fixes merged | CTO | Thu 1 Oct | Merge sha on ClaudeFlow main |
| 4 | Meta submit, needed for the Pro tier and for Messenger shops | CTO + CEO (Q1, Q2) | Fri 9 Oct | Submission id |
| 5 | Chatudo instance live and the security smoke test passed | CTO + CEO (secrets, DNS) | Tue 13 Oct | Smoke-test steps 0–7 pass (DoD 4) |
| 6 | G0 passed | CTO + CEO (checks 30 by eye) | Fri 16 Oct | ≥70% sendable, 0 wrong prices, 100% handoff |
| 7 | First outside shop live on LINE; install timed at ≤1 h | CTO | Fri 23 Oct | DoD 3. Live chats need Q3 (a model) before this date |
| 8 | Pilots installed: ≥7 (G1), aiming for 13–20 | CTO installs, CEO closes | Sat 31 Oct | `tenants.js` list, lifecycle active |
| 9 | **C5 moved earlier:** usage and AI cost per shop, plus a PromptPay QR invoice sent on LINE, confirmed by the CEO | CTO | **Fri 30 Oct** (was 13 Nov) | Invoice test to one tenant |
| 10 | Pilots switch to paid on 1 Nov; the CMO sets the price mix | CEO + CMO | Sun 1 Nov | Invoices sent |
| 11 | New shops keep coming through November (outreach continues) | CEO + CTO installs | through Mon 30 Nov | Paying count every Monday |
| 12 | Count at the checkpoint: paying shops × price ≥ ฿15,000 | CTO reports | Mon 30 Nov 18:00 | Sum of confirmed PromptPay payments |

**Risks specific to money:**
- The CMO funnel assumed a demo link in the first message, but the CEO parked the demo (D5). Contact-to-owner conversion may therefore come in below 10%. Measure it on Monday 5 Oct.
- Many target shops buy Click-to-Messenger ads, but November is LINE-only unless Meta approves in time.

### Risks

1. **Q1 and Q2 answered late.** C1 misses 9 Oct. Nothing else in October waits on them except the O3 go-live.
2. **The weekly limit.** Mitigation: at most 2 workers at once, plus Jules for mechanical work.
3. **G0 may test a different model than the shops get.** G0 runs on a Claude Code session. If Q3 moves live chats to an API model, the G0 report has to say that the model differs.
4. **No outside shop by 19 Oct.** Then DoD 3 slips, even with the code ready.

## Guardrails
- Build only what the next gate needs. Nothing from Nov onward starts in October.
- MoonieX's own bot must keep working: every ClaudeFlow change ships with the MoonieX path unchanged and the suite green (~1,355 cases).
- Money, secrets, and speaking in the CEO's name need the CEO (ALL_Rules_Approvals). Deploys are the CTO's call.
- Report to the CEO every Monday 10:00 (with the CMO review). Report the work done vs this table and the $ spent against $20.
- **Secrets follow the Infisical rules** (Agents-Core CLAUDE.md §Secrets, in force 2026-09-28). The O4
  artefacts (ClaudeFlow `0fd38d4`) were designed around a `.env.chatudo` file. At bring-up (O4 apply, 13 Oct),
  do not create that file. Instead, put the Chatudo values in Infisical (project for ClaudeFlow, env `prod`,
  Chatudo-specific variable names). Run `chatudo-api`/`chatudo-cron` under `infisical run`, adapting
  `scripts/chatudo/compose.sh`. `.env.chatudo.example` stays as the list of names. The CEO enters the values;
  a value never goes in chat or a Run Inbox card.
  - **Location (ruled by the Infisical owner cto-885ae930, 2026-09-28):** project `MoonieX-ClaudeFlow`, env
    `prod`, folder **`/chatudo`**, with the same variable names as MoonieX (MoonieX stays at `/`). Create the folder
    in the Infisical UI. Run with
    `python3 tools/infisical_setup.py run MoonieX-ClaudeFlow prod --path /chatudo -- <compose command>`.
    `put`, `import-env` and `last4` also take `--path`.
  - **Pattern:** follow `docs/ops/infisical-p2-pilot-2026-09-28.md` (the LINE queue already runs this way).
  - **Keys we mint ourselves** (O7b `CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET`):
    - KIND `SECRET`; metadata `provider_name=self`, `console_url=n/a`, `scope` = what it encrypts, `expires` =
      the rotation date.
    - Made by a zero-model Run Inbox card:
      `openssl rand -base64 32 | infisical_setup.py put … --stdin --path /chatudo`.
- **O7b design (security_engineer, task-f50d0c4c):** `docs/briefs/chatudo-o7b-security-design.md` is the O7b
  build brief. Its §8 is the DoD-4 sign-off checklist.
- **Every date and time you report is Thai time (Asia/Bangkok)** (CEO 2026-09-28). The outreach Sheet
  (`1kqCYwXOJ2rdnOwAtitICTtoZ3WW01aBuz1cMP6Ta7e0`) may keep Google's US Pacific clock, so before 14:00 Thai time its
  TODAY() shows yesterday and "ต้องทำต่อ" lags a day. The CEO said not to chase the Sheet's
  setting: an agent summarising the Sheet works out "today", due follow-ups and weekly buckets in Thai time itself.
