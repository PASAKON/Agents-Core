# Spend guard: phase 1 shipped, plan for phases 2–3 (2026-10-14)

Order: CEO card Q-20261013-1958-bc81, option 1, "สร้าง เริ่มที่กันใช้เงินเกินก่อน (OpenRouter, fal, Google)"
(build it, start with stopping overspend). Spec: SomPong's design
`MoonieX/SomPong/docs/reports/api-key-and-spend-guard-design-2026-10-14.md`, which has §1 key broker,
§2 discovery, §3 spend guard and §4 debug. Phase 1 is §3 only. Ops: `docs/ops/spend-guard.md`.
API facts: `docs/research/2026-10-13-spend-monitor-apis-openrouter-fal-gcp.md`.
Owner: CTO.

## 1. Phase 1: what exists

- **Done:** `tools/spend_guard.py` (no model call) and `spend-guard.timer`, every 15 min. It alerts on caps
  (50/80/100 %), a 3× spike, runway under 3 days and a provider it cannot read ("blind"). It pauses an
  OpenRouter key once armed. 53 offline tests cover it in `tests/test_spend_guard.py`.
- **Keys:** `OPENROUTER_API_KEY_ADMIN` (management) and `FAL_BILLING_API_KEY_RO` (fal BILLING preset), in
  Infisical `Agents-Core/prod/spend-guard`. A worker creates them through relay logins with the zero-model
  KeyFetch (CEO, Q-20261013-2026-f2ac: "ไม่ copy เอง ให้ worker สร้างผ่าน relay login" — no copy-paste by him;
  a worker creates them via relay login).
- **First live day:** alert-only. After that it is armed, but only for keys mapped to their services (§2).
- **fal:** has a billing API, so the guard reads its balance. fal has no pause and revoke is permanent, so fal
  is alert-only.
- **Google Cloud:** nothing yet (§5).

## 2. Who uses which key: what a pause takes down

Inventory taken read-only on Contabo, 2026-10-14. Only the names of env vars were read, never their values.
Every OpenRouter consumer reads the same variable name, `OPENROUTER_API_KEY`. None of the live services loads
it from Infisical: journald's `[infisical run]` lines for the last 30 days show no OpenRouter name. Each reads
a legacy env file instead.

| Env file (legacy) | Live service | Product | What a pause breaks |
|---|---|---|---|
| ClaudeFlow `.env` | container `claudeflow-webhook` (up) | LuNar chatbot (customers), LuNar Assist draft + reasoner, SomPong's LINE/Telegram brain | customer replies on LINE |
| same | `src/index.js` jobs (trigger not confirmed) | content autogen, TradeTech/TradeTool posters, video scripts, approval refine | daily posts |
| Option `.env` (**the same value as ClaudeFlow**, `docs/design/secrets-infisical/PLAN.md` §inventory) | container `mooniex-option-channel` (up 3 months) | Option trade-signal parser | trade signals |
| secretary env file | `mooniex-secretary.service` | SomPong route decision: Jev (`/api/alpha/decisions`), then the Haiku rung | SomPong's routing (falls back to rules) |
| same, as a fallback | CLI `jev_lab`, `jev_bench`, `cookierun_teachers` | Jev lab, Cookie Run teachers | ad-hoc runs |
| Infisical `MoonieX-ClaudeFlow/prod/chatudo` (planned) | none: Chatudo is parked, no containers | Chatudo chatbots | nothing today |
| unknown | the H3 studio on the Mac | `{}` prompt filler | Mac studio prompts |
| n8n credential store | `n8n` (up) | not checked | unknown |

fal: ClaudeFlow `.env` sets `FAL_API_KEY` twice with different values (the last one wins) for autogen images
and video TTS/STT/lipsync. `FAL_ADMIN_API_KEY` feeds ClaudeFlow's own balance monitor. Chatudo's fal keys are
not live.

**What the numbers say:** in `docs/ops/jev-lab-2026-09-23/balance.jsonl` the gap between the account's usage
and the secretary key's usage stays constant, so on 13 Oct one key (Jev/secretary) carried all the spend.

**What is not known yet:** which OpenRouter key name sits behind each env file. Only the management key lists
the names, together with `last_used_at` and per-day usage. So:

1. After the keys land, run `spend_guard.py keys` on a green Run card. It prints names, hash8 and usage, never a value.
2. Fill `providers.openrouter.keys` in `config/spend_guard.yaml` with `consumers:` for each key. The key that
   serves LuNar and Option gets `pause: false` until the broker (§3) splits it. A customer chatbot going quiet
   costs more than a few dollars of overspend.
3. Until a key has a row, the armed guard alerts on it but never pauses it (`unmapped_keys: alert`).

## 3. Phase 2: key broker (design §1) and better baselines

- **One key per service.** Separate OpenRouter keys for LuNar (ClaudeFlow), Option, SomPong/Jev, workers and
  the studio, each with its own `limit` and `limit_reset: monthly` set by the CFO. A pause then takes down one
  service, not three.
  - **How:** management API `POST /keys` writes the value straight to that project's Infisical folder, with
    the same zero-model pattern as `scripts/keyfetch/capture_key.mjs`, but API-only. No browser is needed
    once the management key exists.
  - **Then:** each service moves to `infisical run` in `PLAN.md`'s project order, after its owner is told.
    The old shared key is revoked last.
  - **Gates:** a secret needs no new CEO input (the management key does it). Restarting a service under
    Infisical needs its owner told first.
- **Better baselines:**
  - **Day-one baseline:** `POST /analytics/query` (management key) returns `total_usage` per hour by
    `api_key_id`. It gives a real 7-day hourly baseline from the first run, replacing the counter estimate.
  - **Account guardrails:** OpenRouter `budgets[]` / `effective_budget`, read by the guard.
  - **fal per key:** `GET /v1/models/usage?api_key_id=…&expand=time_series`, which the BILLING preset covers.
    It gives a fal spike per key and per endpoint (alert only).
- **Telegram:** add a reference to SomPong's `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CEO_CHAT_ID` in
  `/spend-guard` once they are in Infisical (`MoonieX-SomPong/prod`). No code change, no new bot.

## 4. Phase 3: discovery (design §2) and debug (design §4)

- **Weekly discovery, names only.**
  - **Inputs:** every repo and env file on Contabo, the Mac and winbox; Infisical's folders; each provider's
    key list (name, created, last used).
  - **Output:** keys nobody uses (revoke candidates, CEO card), keys with no owner, the same value in two
    places, keys near `expires`.
  - **Delivery:** one report on Monday with the tool-value report. No model is needed to collect the data.
- **Debug on a spike.** The alert carries the last hour's top models and keys from OpenRouter analytics, and
  the top endpoints from fal `models/usage`, so the CEO sees *what* burned without asking.

## 5. Google Cloud (blocked on a billing account: the CEO's call, cto-dd03bac1)

When a billing account exists:

1. A budget on the billing account with thresholds at 50 / 80 / 100 % of actual spend plus 100 % forecast.
   Billing Account Costs Manager is enough to create it.
2. A Pub/Sub topic connected to the budget, and a **pull** subscription. The 15-minute timer pulls it with a
   service account that has `pubsub.subscriber` only, its JSON key in `/spend-guard` (a CEO card).
   - **Why pull:** no public endpoint to defend. Messages arrive several times a day, at least once each, and
     the guard's dedup handles the repeats.
3. Alerts only. Google's documented "cap" is a function that unlinks billing. It stops every service, may
   delete resources, lags on cost data and needs `roles/billing.admin`, so it is **not recommended**. A
   runaway on GCP goes to the CEO as an alert and he decides.

## 6. Open money items for the CFO

- `monthly_cap_usd` for OpenRouter and fal (config). Until set, caps come from key limits and the prepaid balance.
- Per-key limits once the broker splits keys (§3).
- Top-up: the guard only alerts. On 13 Oct OpenRouter had $6.75 left at ~$7.4/day (LungNote e3c6efab).
