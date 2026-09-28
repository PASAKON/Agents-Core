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

## Guardrails
- Build only what the next gate needs. Nothing from Nov onward starts in October.
- MoonieX's own bot must keep working: every ClaudeFlow change ships with the MoonieX path unchanged and the suite green (~1,355 cases).
- Money, secrets, and speaking in the CEO's name need the CEO (ALL_Rules_Approvals). Deploys are the CTO's call.
- Report to the CEO every Monday 10:00 (with the CMO review). Report the work done vs this table and the $ spent against $20.
- **Every date and time you report is Thai time (Asia/Bangkok)** (CEO 2026-09-28). The outreach Sheet
  (`1kqCYwXOJ2rdnOwAtitICTtoZ3WW01aBuz1cMP6Ta7e0`) may keep Google's US Pacific clock, so before 14:00 Thai time its
  TODAY() shows yesterday and "ต้องทำต่อ" lags a day. The CEO said not to chase the Sheet's
  setting: an agent summarising the Sheet works out "today", due follow-ups and weekly buckets in Thai time itself.
