# Chatudo O7b-4: security fixes from the DoD-4 review

- **Project:** MoonieX-ClaudeFlow. Base: `origin/main` `2ee74fe`.
- **Source:** the security_engineer sign-off, task-8ae7a7c6, 2026-09-29 07:05 Thai time. Verdict: SIGN-OFF WITH CONDITIONS.
- **Deadlines:**
  - Item 1 (F1) blocks the Chatudo schema apply on Tue 13 Oct.
  - Items 2–5 must land before pilot shops go live on Fri 23 Oct.
  - Items 6–11 go in the same branch, because they are small and touch the same files.
- **Author:** CTO cto-4bb20df8, 2026-09-29.

## Rules (same as O7b-3)

- Allowed: code, tests, docs and migration **files** only. Never apply a migration.
- Forbidden: network calls, DB access, and reading, copying or creating any `.env*` file (the tracked `*.example` files are fine). No API spend ($0). Do not push.
- The MoonieX bot must not change behaviour. Anything Chatudo-only is gated on the existing `isShopOnlyInstance` helper.
- Run the suite with dummy env:
  `SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SERVICE_KEY=dummy SUPABASE_KEY=dummy OPENAI_API_KEY=dummy OPENROUTER_API_KEY=dummy npm test`
  - The result must be 0 failures, apart from the known flake in `tests/lineSompongGroup.test.js`, which passes when run alone.
  - Every new test file must be listed in `package.json` `test`.
- One commit per numbered item, with a message starting `o7b4 itemN:`.

## Items

### 1. [HIGH · blocks 13 Oct] RLS on the four identity tables (F1)

`claudeflow_web_admins`, `claudeflow_web_admin_members`, `claudeflow_web_admin_sessions` and `claudeflow_web_admin_invites` are created in `202609281204` without RLS. Nothing in 1205, 1206 or 900 enables it either. The effect: anyone holding the anon key can insert a member row and a session row through PostgREST, then log in as staff of any shop.

- **Fix:** add four `ALTER TABLE … ENABLE ROW LEVEL SECURITY;` lines to `supabase/bootstrap/900_chatudo_hardening.sql`, next to the `tenant_profiles` line, with a one-line comment.
- **Test (new, mechanical):** a test that reads the apply-schema `ORDER` (`scripts/chatudo/apply-schema.js`) and parses every `CREATE TABLE [IF NOT EXISTS] public.<name>` across those files.
  - It asserts that each table has an `ENABLE ROW LEVEL SECURITY` for the same name in some file of `ORDER`.
  - It fails with the list of uncovered tables.
  - It must fail on `2ee74fe` and pass after the fix. Say so in the report.
  - This is the second time the list has missed tables (O7a missed `tenant_profiles`), so the rule becomes a test.

### 2. [MED] `reset-owner` and pending-Verify (F2)

`scripts/chatudo/tenants.js` `reset-owner` (~`:271-275`) sets only `active:false, verified_at:null`. That leaves three holes:

- **(a) Live shop:** the next real customer message, signed with the old secret, passes `getPendingVerifyCreds` (`src/integrations/accountStore.js` ~`:263-300`). `tryLinePendingVerify` (`src/webhook/server.js` ~`:285-289`) then moves the shop from `awaiting_owner` to `pending_operator`, so the new owner's setup gets 404 and `approve` fails.
- **(b) Squatter:** anyone who signs `{destination: <their bot>, events: []}` with their own secret holds the slug hostage.
- **(c) Ex-owner:** credentials the removed owner staged in the last 24 h survive, and `getRotationCandidate` (~`:354-410`) never checks that `pending_by` is still an owner. The ex-owner can therefore promote them over the new owner's credentials.

**Fix:**
- `reset-owner` sets `bot_user_id`, `pending_credentials`, `pending_credentials_at` and `pending_by` to null. It throws on `{error}` and reports failure. Today it prints ok even when the write fails (F9).
- `setupStore.finalizeSubmit` also nulls `pending_credentials`, `pending_credentials_at` and `pending_by`.
- `tryLinePendingVerify` advances the lifecycle only when the tenant has a **pending owner claim**: a `claudeflow_web_admin_members` row with `role='owner'` and `state='pending'`. Otherwise it does nothing and logs `line/<slug> pending-verify ignored: no owner claim`.
- `getRotationCandidate` returns null unless `pending_by` is an **active owner** of that tenant (fresh read; a read error means null, never a pass).

**Tests:**
- After `reset-owner`, a signed webhook leaves the lifecycle at `awaiting_owner`.
- No owner claim means no advance.
- Pending credentials from a removed owner are not promoted.
- `reset-owner` with a DB error exits non-zero.

### 3. [MED] `logout-others` closes every stream in the process (F3)

In `src/webhook/adminInboxApi.js` (~`:1149-1151`), the handler loops over **all** of `sseStreamsBySession`. Any staff member of any shop can drop every other shop's live inbox. `adminSessions.revokeOthers` (~`:386-398`) returns 0 on a DB error, and the route still answers `ok:true`.

- **Fix:**
  - `revokeOthers` returns the revoked session ids and throws on `{error}`.
  - The route calls `closeStreamsForSessions(ids)` for exactly those ids.
  - Give the route a write rate limit. It is `rate: null` today; use the existing `LIMITS` pattern.
  - A DB error answers 500.
- **Tests:**
  - Shop B's stream stays open when shop A's user calls logout-others.
  - The caller's other sessions are closed.
  - A DB error returns 500, not `ok`.

### 4. [MED] Rate-limit and idempotency memory never shrinks (F4)

`src/lib/rateLimit.js` `hit` never deletes a key. `setupSubmit` (~`:1237`) calls `hit` keyed on the raw body `shop` string **before** the slug check (~`:1240`). The reviewer measured +196 MB of heap after GC for 2,000 keys of ~100 KB each. `idempotencyCache` (~`:117-133`) has a 24 h TTL, is swept only on read, and takes a caller-chosen Idempotency-Key of any length.

**Fix:**
- Check `isValidSlug(shop)` before `hit`.
- In `rateLimit.hit`, delete a bucket whose hit list is empty after the shift.
- Add a bounded sweep of expired buckets, and a hard cap on the key count that evicts the oldest.
- Hash keys longer than 128 characters (sha256) before use.
- Cap the Idempotency-Key at 128 characters (longer → 400 `invalid_idempotency_key`).
- Sweep expired idempotency entries on write, and cap the entry count.

**Tests:**
- An invalid slug does not create a bucket.
- The bucket count stays bounded after 10,000 distinct keys.
- A long key is hashed.
- An over-long Idempotency-Key gets 400.
- The idempotency cache stays bounded.

### 5. [MED · PDPA] Customer text goes to stdout (F6)

`src/webhook/line.js` `:295` logs `Text from ${senderId}: "${text}"` for every LINE message. `src/webhook/meta.js` `:289` and `:382` do the same for Meta.

- **Fix:** on `isShopOnlyInstance`, log only `len=<n>` with no text and no senderId. MoonieX keeps its current lines unchanged.
- **Test:** on Chatudo, the captured console output does not contain the message text or the senderId. On MoonieX the output is unchanged.

### 6. [LOW] A malformed cookie returns 500 with a stack (F7)

`src/lib/adminAuth.js` `parseCookies` (~`:134`) calls `decodeURIComponent` unguarded, so `Cookie: __Host-cu_sid=%E0%A4%A` returns 500 with a stack trace, without authentication.

- **Fix:**
  - Skip any cookie pair that fails to decode.
  - Add a JSON error handler (`{error:'internal'}`, no stack) on the admin inbox router only. The MoonieX webhook paths keep their behaviour.
  - Set `NODE_ENV=production` in the environment of both chatudo services in `docker-compose.chatudo.yml`.
- **Test:** the bad cookie gets 401 JSON, and the body contains no `adminAuth`.

### 7. [LOW] The OAuth code is written to stdout (F8)

`src/lib/lineLogin.js` (~`:339` and `:447`) passes `route: req.originalUrl`, so `?code=…&state=…` ends up in the log.

- **Fix:** pass the route template instead.
- **Test:** the log line contains no `code=`.

### 8. [LOW] `{error}` treated as "none" (F9)

Three places need to throw on `{error}`:
- `tenants.js` `create` (~`:95`).
- `reset-owner` (already covered in item 2).
- `setupStore.recordBotInfoFailure` (~`:162-176`). If saving the lock fails, the submit answers 503 and does not continue.

Test each one.

### 9. [LOW] A removed member's stream outlives the removal (F10)

The SSE 60-second re-check (~`:1051-1060`) checks only the session.

- **Fix:** also re-read the membership. If it is not an active member of that tenant, close the stream.
- **Test:** a member is revoked while the session row stays → the stream closes at the next tick.

### 10. [LOW] Stop Meta at the edge until the draft gate exists (residual 5)

Messenger and IG have no draft gate, so no Chatudo shop may be on them. Today only convention holds that line.

- **Fix:**
  - Drop `facebook|instagram|meta` from the api router rule in `docker-compose.chatudo.yml`.
  - `scripts/onboard-account.js` refuses any platform other than `line` when `isShopOnlyInstance` is true, with a clear message.
- **Test:** onboard-account with `--platform facebook` on a shop-only instance exits non-zero with no write. Any compose test/lint that exists still passes.

### 11. [LOW] Runbook and comments (F11, N1, residuals 1, 2, 4)

Edit `docs/chatudo/instance.md`:
- **§2:** replace the stale counts (21 files / 13 tables) with the real numbers taken from `ORDER`. Derive them; do not copy them by hand. Add a test that the doc's numbers equal `ORDER`'s, if that is cheap.
- **Row 6c:** 500 → 503.
- **Unlock:** `unlock` clears the DB lock but **not** the in-process 5-per-hour bucket, so the runbook says "wait 1 h or restart `chatudo-api`". Fix the same wrong claim in the `src/lib/rateLimit.js` `:57` comment.
- **Stop the bot:** name `reset-owner` as the operator's lever (after item 2), because `suspend` does not stop LINE replies.
- **Approve:** add a step. The operator confirms that the shop's OA sits under its **own** LINE provider (the mute key is shared across shops until O8), and reads `userid_collision` rows with `audit-tail` weekly during the pilot.
- **Known gap for C3:** `approval-timeout` emits `timed_out` inside `chatudo-cron`, but the SSE bus lives in `chatudo-api`, so browsers never see those events.

## Report (required shape)

1. A table with one row per numbered item above: **item → commit sha → test name(s) → pass evidence**. A missing row counts as not done.
2. For item 1: the new RLS test's result on `2ee74fe` (must be red) and on your branch (green).
3. The full suite line, plus the solo re-run line for any flake.
4. Any deviation from this brief and why.
5. End with `## Skill learning`.
