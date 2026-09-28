## Chatudo O7b-3a · developer · LINE Login + first-owner setup + operator CLI + /app login/setup pages

## Job (BUILD)
Build the path by which a new shop's owner logs in with LINE, proves they control the shop's LINE OA, and gets a working session on `app.chatudo.com` once the operator approves. The target is under an hour, and no secret ever passes through a chat.

This is the first half of O7b-3. Staff invites, the team page, member removal, role changes and credential updates are O7b-3b, which comes later. Do not build them.

The design is final (security_engineer):
`/opt/MoonieXHQ/Agents/Core/docs/briefs/chatudo-o7b-security-design.md`. Read the whole file. Your scope is:
- §1 (host, Traefik, mount order, CSP);
- §2 (first owner, steps 1–4, and the operator CLI);
- §3 (OAuth, login rate limit, recent login);
- §7 rows: leaked login link (setup part), slug squatting, login CSRF/open redirect, stored XSS on your pages, the catch-all swallowing new paths.

Where this brief is more specific than the design, follow this brief. It is the CTO's addendum.

## What already exists (ClaudeFlow origin/main `f638e21`; read these files and the O7b-1 section of `docs/chatudo/tenant-isolation.md` first)
- O7a (`src/lib/instance.js`): `isShopOnlyInstance()` is true on Chatudo.
- O7b-1:
  - `src/lib/adminSessions.js`: `create`/`resolve`/`rotate`/`revoke`/`revokeAllForAdmin`/`revokeOthers`, cookie `__Host-cu_sid`.
  - `src/lib/adminAuth.js`: principal resolution, fresh membership check, lifecycle `active` check, CSRF.
  - `src/lib/scopedDb.js`, `src/lib/adminAudit.js`, `src/lib/rateLimit.js` (with `LIMITS.login`/`setupSubmit`/`inviteRedeem` already defined).
  - The route registry in `src/webhook/adminInboxApi.js`: `ROUTE_DECLARATIONS` + `mount()`.
  - Migration `202609281204` (web_admins, members, sessions, invites, audit, `tenant_profiles.lifecycle`, `webhook_accounts.bot_user_id`/`basic_id`/`verified_at`).
- O7b-2 (`src/lib/credentialCrypto.js`): `encryptCredentials(creds, {tenant_slug, platform, account_slug})`. Decryption happens only in `src/integrations/accountStore.js`.
- `src/webhook/line.js` has an O7a seam, `isSetupVerifyRequest(req)`, OR-ed with `verifySignature` in `handleWebhook`. That shape is a signature bypass, and you replace it (item 4).

## Build
1. **Migration** `supabase/migrations/202609281205__chatudo_o7b3_identity_sessions.sql`. Make it idempotent, add it to `supabase/bootstrap/ORDER` after `…1204`, and add a README row.
   - **`claudeflow_web_admin_sessions`:**
     - `member_id`, `tenant_slug` and `role` become nullable, with a CHECK that all three are null or all three are set. Keep `role IN ('owner','staff')` and `tenant_slug <> 'mooniex'` when set.
     - Add `authenticated_at timestamptz NOT NULL DEFAULT now()`: the time of the LINE login, carried across rotations.
   - **`claudeflow_tenant_profiles`:** add `setup_failures int NOT NULL DEFAULT 0`, `setup_locked_at timestamptz` and `awaiting_owner_until timestamptz`.
2. **Identity sessions.** A session with no member is a logged-in LINE user who has no active shop yet.
   - `adminAuth` gives it the principal kind **`identity`**: `{webAdminId, sessionId, sessionRef, csrfToken, authenticatedAt}`, with no tenant.
   - A member session resolves exactly as today.
   - `scopedDb` already throws for unmapped kinds; keep it that way, so an `identity` principal can never read shop data.
   - **Access classes in the registry:**
     - `anon`: no session needed. Only the two OAuth routes use it.
     - `identity`: the setup routes, `me`, `logout`, `switch`.
     - The existing `owner`/`staff`/`super`.
   - Make principal resolution follow the route's declaration: an `anon` route does not demand a cookie, and every other route does, exactly as today. A route with no declaration still stops the router from building.
   - **`POST /admin/inbox/auth/switch {shop}`** (`identity` or member): requires an active membership for (webAdminId, shop) and a shop lifecycle of `active`. It rotates the session into a member session (a new session id, the member's tenant and role, the same `authenticated_at`). Audit it.
   - **`GET /admin/inbox/me`** for `identity` returns the memberships: shop slug, shop name, role, state. The page uses this as a shop picker.
   - **`requireRecentLogin(principal, 10 min)`** is a helper based on `authenticated_at`. Setup submit uses it now; O7b-3b will use it for sensitive actions.
3. **LINE Login (OIDC).** Put it in `src/lib/lineLogin.js` and use an injectable `fetch`. Tests make no network calls.
   - **`GET /admin/inbox/auth/line/start?return_to=`:**
     - Generate state, nonce and PKCE S256.
     - Set the `__Host-cu_oauth` cookie (HttpOnly, Secure, SameSite=Lax, Path=/, Max-Age=600). It holds an opaque id that points to an in-process map entry `{state, nonce, verifier, return_to, expiresAt}`, usable once.
     - 302 to `https://access.line.me/oauth2/v2.1/authorize` with `scope=openid profile` and redirect `https://app.chatudo.com/admin/inbox/auth/line/callback`.
   - **`GET /admin/inbox/auth/line/callback`:**
     - Check the cookie and `state` in constant time, use the entry once, and check it has not expired.
     - Exchange the code at `https://api.line.me/oauth2/v2.1/token` with `LINE_LOGIN_CLIENT_ID`, `LINE_LOGIN_CLIENT_SECRET` and the verifier. The secret comes from env only and is never logged.
     - Verify the `id_token` yourself:
       - `alg` must be HS256 (HMAC with the channel secret) or ES256 (JWKS from `https://api.line.me/oauth2/v2.1/certs`, cached 1 h, matched by `kid`). Reject everything else, including `none`.
       - Check `iss === 'https://access.line.me'`, `aud === LINE_LOGIN_CLIENT_ID`, `exp` in the future, `iat` within 10 minutes, and `nonce` matching.
     - Upsert `claudeflow_web_admins` (`idp` 'line', `subject = sub`, `line_name`, `picture_url`).
     - Issue a new session, with a new id even if the browser had one:
       - if the user has exactly one active membership in an `active` shop, a member session;
       - otherwise an identity session.
     - Redirect to `return_to` only when it is a path that starts with `/app/` and contains no `//`, no backslash and no scheme. Otherwise redirect to `/app/`.
     - Any failure redirects to `/app/?error=login` with no detail, plus an audit row carrying the reason.
     - Rate limit: 20 per 10 minutes per IP, using `req.ip` (trust proxy is already set on Chatudo).
4. **First-owner setup** (design §2, steps 1–4).
   - **`GET /admin/inbox/setup/status?shop=`** (`identity`):
     - Returns shop name, lifecycle, the current step, the webhook URL once submitted, and whether the Verify call arrived.
     - Only when the shop is in `awaiting_owner` or `pending_operator` and, once claimed, only to the claimant.
     - Otherwise it returns the same 404 body as a missing shop.
   - **`POST /admin/inbox/setup/submit {shop, channel_secret, channel_access_token}`** (`identity`, recent login ≤ 10 min, CSRF). Rejected unless all of these hold:
     - the shop is `awaiting_owner`;
     - `now < awaiting_owner_until`;
     - the shop is not locked;
     - nobody else holds a pending or active owner membership for it (409).

     Then:
     - Call `GET https://api.line.me/v2/bot/info` with the token to get `userId`, `basicId` and `displayName`. A failure counts toward `setup_failures`; at 5, set `setup_locked_at`. Audit both.
     - Encrypt with `encryptCredentials`.
     - Upsert the `claudeflow_webhook_accounts` row: platform `line`, `account_slug` = shop, `tenant_slug` = shop, `active=false`, `bot_user_id`, `basic_id`, `verified_at` null.
     - Create the membership `(web_admin_id, shop, 'owner', 'pending')`.
     - Return the webhook URL `https://api.chatudo.com/webhook/line/<shop>`.
     - Rate limit: 5 per hour per shop.
     - Secrets never appear in a response, a log or an audit row.
     - Put the data access for these routes in one module, `src/lib/setupStore.js`. Every function takes the shop slug and the web admin id explicitly. Add it to the static test's named allowlist, the same way the MoonieX review-queue handlers are allowed.
   - **Verify: replace the seam.**
     - Delete `isSetupVerifyRequest` and the `&& !isSetupVerifyRequest(req)` term. The signature check in `handleWebhook` is never skipped.
     - Add a separate step before `handleWebhook`, Chatudo only: when a LINE webhook arrives for an account slug that is not active, call a new `accountStore.getPendingVerifyCreds('line', slug)`. It decrypts inside accountStore, so decryption still lives only there.
     - Accept the call only if all three hold:
       - `x-line-signature` matches HMAC-SHA256 of the raw body under the pending `channel_secret` (constant time, with a length guard);
       - `body.destination === row.bot_user_id`;
       - no event is processed.
     - On accept: set `verified_at`, set lifecycle to `pending_operator`, audit `channel_verified`, and answer 200.
     - Anything else answers 401, as today. MoonieX is unchanged.
5. **Operator CLI `scripts/chatudo/tenants.js`.**
   - It refuses to run unless `SHOP_AGENT_REQUIRED=true`. It reads the Supabase URL and key from env; on the box it runs under `infisical run`.
   - Verbs:
     - `create <slug> --name "<ชื่อร้าน>"`: a `tenant_profiles` row with `agent_profile='shop'`, `shop_name`, lifecycle `awaiting_owner` and `awaiting_owner_until = now+48h`. Prints the setup URL `https://app.chatudo.com/app/setup?shop=<slug>`.
     - `show <slug>`: basicId, OA name, the owner's LINE name, lifecycle, verified_at. Never a secret.
     - `approve <slug>`: requires `verified_at`. Sets the account `active=true`, the owner membership `active` and lifecycle `active`.
     - `suspend <slug>`: lifecycle `suspended`, and revokes every session of the shop.
     - `reset-owner <slug>`: revokes the owner membership and their sessions, sets lifecycle back to `awaiting_owner` for +48 h, makes the account inactive and clears `verified_at`.
     - `revoke-sessions <slug>`.
     - `unlock <slug>`: `setup_failures=0`, `setup_locked_at=null`.
     - `audit-tail <slug> [-n 50]`.
   - Every verb writes an audit row with `actor_kind='operator'`.
   - **Slug rule, enforced everywhere a slug comes in** (CLI, setup routes, Verify path): `^[a-z0-9][a-z0-9-]{1,30}$`. The reserved slugs `mooniex`, `sompong`, `app`, `api`, `www`, `admin`, `webhook` and `health` are refused.
6. **Pages** (static files under `src/webhook/app/`, served at `/app/`, mounted before the `/:platform/:account` catch-all; on MoonieX `/app` is 404).
   - **`index.html`:**
     - Logged out: a "เข้าสู่ระบบด้วย LINE" button that goes to `/admin/inbox/auth/line/start?return_to=/app/`.
     - An identity session: the shop picker from `/me`, which calls `switch`.
     - A member session: shop name, role, logout, and a placeholder where the approval page will go (C3).
     - The shop picker, logout and the placeholder go on `index.html` only; `setup.html` keeps only what its bullet lists.
   - **`setup.html?shop=`:**
     1. Log in with LINE.
     2. Paste the Channel secret and the long-lived Channel access token, with short Thai instructions on where to find them in the LINE Developers Console, including "create a new provider for this shop".
     3. Show the webhook URL with a copy button, plus the instruction to turn on "Use webhook" and press Verify.
     4. Poll the status every 5 s until it reaches `pending_operator`, then show "รอทีมงานยืนยันร้าน". Once the shop is `active`, `switch` and go to `/app/`.
   - **Rules for every page:**
     - External `.js` files only, no inline script.
     - The CSP header exactly as in design §1.
     - Render with `textContent` only.
     - Mobile-first; they are used inside LINE's in-app browser.
     - Thai copy with **no em dash** (IRON §39) and **no emoji**, which includes ✓ ✕ ⏳ 🔒. Inline SVG icons are fine.
     - Tone: plain and short for a non-technical shop owner.
7. **Traefik labels** in `docker-compose.chatudo.yml`, exactly as in design §1: the api router loses `/admin/inbox`, and a new `chatudo-app` router gets the headers and ratelimit middlewares. If an existing compose test asserts the old rule, update it.
8. **Docs:**
   - `docs/chatudo/instance.md`:
     - the app host;
     - DNS `app.chatudo.com` A `194.233.80.26`, DNS-only;
     - the LINE Login channel steps from design §9 (new provider "Chatudo", callback URL, scopes `openid profile`, Published);
     - `LINE_LOGIN_CLIENT_ID`/`LINE_LOGIN_CLIENT_SECRET` in Infisical `MoonieX-ClaudeFlow`/`prod`/`/chatudo`.
   - New `docs/chatudo/shop-setup.md`: the operator's install walkthrough, in Thai time, in this order: create → send the URL → the owner's steps → show → check the @basicId with the shop → approve.
   - `docs/chatudo/tenant-isolation.md`: identity sessions and the access classes.

## Tests (all in `npm test`; add new files to the `test` script; LINE and Supabase stubbed; $0; no network)
- **OAuth:**
  - bad, reused and expired state;
  - wrong nonce, aud, iss;
  - expired token;
  - `alg: none` rejected;
  - valid HS256 and valid ES256 (generate a P-256 key in the test);
  - `return_to` values `//evil.com`, `/\evil`, `https://evil.com` and `/admin/inbox/x` all fall back to `/app/`;
  - the session id rotates at login;
  - the login rate limit.
- **Setup end to end, through the router and the line.js webhook with fakes:**
  - create → login → submit → a signed Verify call → show → approve → switch → `/me` shows owner of the shop → the inbox contacts route works for that shop only.
- **Setup negatives:**
  - Verify signed with the wrong secret → 401, not verified;
  - `destination` mismatch → not verified;
  - a Verify-shaped call to an active account follows the normal path;
  - setup on a shop that is not `awaiting_owner`, or past the window → 404;
  - a second claimant → 409;
  - 5 failures → locked; `unlock` resets;
  - submit without a recent login → 401/403;
  - an identity principal on any shop-data route → 403.
- **Static tests:**
  - no `isSetupVerifyRequest`, and no expression that ORs anything with `verifySignature(`;
  - no inline `<script>` in `src/webhook/app/*.html`;
  - no em dash (U+2014) and no emoji or dingbat characters (U+2600–27BF, U+1F300–1FAFF) in `src/webhook/app/*`;
  - every new route declared.
- **Headers:** the CSP header is asserted on `/app/` and `/app/setup.html`.
- **MoonieX:**
  - `/app/*`, `/admin/inbox/auth/*` and `/admin/inbox/setup/*` → 404;
  - the existing MoonieX golden call-chain test still passes unmodified.
- **Log capture across your tests:** the fixture channel secret, access token, client secret, id_token and session cookie appear 0 times in stdout or stderr.

## Acceptance
- The full suite is green on the dummy env:
  `SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SERVICE_KEY=dummy SUPABASE_KEY=dummy OPENAI_API_KEY=dummy OPENROUTER_API_KEY=dummy npm test`
  The only tolerated failure is a timing flake in `tests/lineSompongGroup.test.js` (it also flakes on main); re-run it alone.
- The MoonieX path is unchanged.

## Rules
- Build only this piece.
- Never copy or create a `.env` file. Make no network calls and no database access; write SQL files only and never apply them. $0 spend.
- Fail closed everywhere: a missing or unknown identity denies, never defaults to more access. An error message never quotes a secret or a token.
- Commit on your branch in small commits. Do not push or merge; the CTO merges.
- Every date and time you report is Thai time (Asia/Bangkok).
- If the design and this brief leave something ambiguous, choose the more closed option and list it under "Design deviations".

## Report (last message)
Include: files changed, commits (sha + one line), the suite line (`# tests/pass/fail/skipped`), design deviations, what O7b-3b needs to know, and what is still open.

End with `## Skill learning`: one line per item, in the form `WRONG|MISSING|COSTLY [<skill> §<section> | no owner] : … · evidence: …`, or exactly `- (none)`.
