<!-- Chatudo O7b security design: task-f50d0c4c (security_engineer, in-session opus), 2026-09-28 Thai time,
     read-only pass on ClaudeFlow origin/main 3192107. The builder brief for O7b; sign-off checklist = DoD item 4. -->

# O7b design: Chatudo shop admin login, tenant isolation and token encryption (security_engineer, task-f50d0c4c)

I read everything at origin/main `3192107` on 2026-09-28 (Asia/Bangkok). This was a read-only pass: no file changed, no database was touched, nothing was spent.

## Decisions

| # | Decision | Why | Rejected options (one line each) |
|---|---|---|---|
| 1 | Serve the page from **`app.chatudo.com`**, out of the same `chatudo-api` container. The pages are static files under `/app/*` in ClaudeFlow, and the API is on the same origin at `/admin/inbox/*`. `api.chatudo.com` keeps only the webhooks and `/health`. | The session cookie is host-only and never reaches the webhook host, which logs request bodies. Same origin means no CORS, and the SSE stream gets the cookie. No new repo, no new HQ row, $0. | `api.chatudo.com/app` (the cookie and CSP would be shared with the webhook host) · a new Chatudo-App repo or container (needs an HQ row plus CORS; fine later) · mooniex.com or Chatudo-Webapp (forbidden) |
| 2 | **Identity is LINE Login (OIDC).** The first owner proves control of the shop's OA (see §2), then the operator activates the shop. Staff join through a single-use invite that the owner must confirm. | No secret passes through the operator or any chat. The proof is work the owner already does during install. Free, and one tap inside LINE's in-app browser. | A claim link sent by the operator (a live credential in a person's or agent's hands; a leak means takeover) · a per-admin API token (a bearer secret on phones, with no revocation UX) · email one-time code (shops live on LINE, and it needs a mail sender) · LIFF (same LINE Login channel; add it later for a rich-menu entry) |
| 3 | **Server-side opaque session in a `__Host-` cookie.** The SSE stream uses the same cookie. | Revocation is instant, and no token ever sits in a URL. | Bearer token in localStorage (XSS can steal it, and SSE would need `?token=`) · stateless JWT (cannot be revoked) |
| 4 | **Every `/admin/inbox` route goes through a principal-scoped DB wrapper.** `isShopOnlyInstance()` picks the auth mode: Chatudo accepts sessions only, MoonieX accepts the shared key only. | A missing filter becomes structurally impossible, and the MoonieX path stays byte-identical. | Adding `.eq()` in each handler (one forgotten line is a leak) · Supabase RLS with user JWTs (needs Supabase Auth and a rewrite of the data layer) |
| 5 | **AES-256-GCM per credential field**, stored as `enc:v1:<kid>:…`. The key ring is in `CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET`. Decryption happens only in `accountStore.refresh()`. Chatudo refuses to boot without the key. | Built into Node, authenticated, coexists with MoonieX's plaintext rows, and has one choke point. | pgcrypto or Supabase Vault (the key is reachable from the same DB or service role) · libsodium (a new dependency) · a KMS (costs money) |
| 6 | **Append-only `claudeflow_admin_audit` table** plus one stdout line per action. No message text, no secrets. | Queryable per shop, and it survives log rotation. | stdout only (rotated away after 10 MB × 5) · a paid log service |

## 1. Host and Traefik (labels in `docker-compose.chatudo.yml`)

```
chatudo-api.rule = Host(`api.chatudo.com`) && (Path(`/health`) || PathRegexp(`^/webhook/(line|facebook|instagram|meta)/[^/]+`))   # /admin/inbox removed
chatudo-app.rule = Host(`app.chatudo.com`) && (Path(`/`) || PathPrefix(`/app/`) || PathRegexp(`^/admin/inbox(/|$)`))
chatudo-app: entrypoints=websecure · tls.certresolver=mytlschallenge · service=chatudo-api
  middlewares=chatudo-app-hdr (stsSeconds=31536000, frameDeny, contentTypeNosniff, referrerPolicy=no-referrer),
              chatudo-app-rl (ratelimit average=30 burst=60)
```

**Mount order.** `/app` and every new route must be mounted before the `/:platform/:account` catch-all at `server.js:298-299`. Otherwise `/app/setup` is handled as the account lookup `app/setup`. Put the new endpoints under `/admin/inbox/{auth,setup,team,me}`.

**CSP.** The app sets this on `/app`: `default-src 'self'; script-src 'self'; img-src 'self' https://profile.line-scdn.net; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`. No `unsafe-inline`.

**Split of work.** O7b ships the login, setup, join and team pages. C3 (due Fri 23 Oct) builds the approval UI in the same `/app/`, using the same session.

## 2. Identity, enrolment, staff, revocation

The identity is the LINE Login `sub` under Chatudo's own LINE provider. It is not the same number as that person's userId as seen by the shop's OA. So it must never be joined to `claudeflow_admins`, which stays the per-shop list of in-chat command admins that O7a is building.

**New tables** (one O7b migration, nullable so it is safe for MoonieX; the strict rules go in `900_chatudo_hardening.sql`):
- `claudeflow_web_admins` (idp, subject unique)
- `claudeflow_web_admin_members` (admin_id, tenant_slug, role owner|staff, state pending|active|revoked)
- `claudeflow_web_admin_sessions`
- `claudeflow_web_admin_invites`
- `claudeflow_admin_audit`
- a lifecycle column on `claudeflow_tenant_profiles`: `awaiting_owner | pending_operator | active | suspended`
- on the account row: `bot_user_id`, `basic_id`, `verified_at`
- on `claudeflow_admin_questions`: `claim_id`, `claimed_at` (see the approve-replay row in §7)

**First owner, within the ≤1 h install:**
1. **Operator** runs `scripts/chatudo/tenants.js create <slug> --name …`. The shop goes to `awaiting_owner` for 48 h. The script prints `https://app.chatudo.com/app/setup?shop=<slug>`. That URL holds no secret, so sending it by chat is fine.
2. **Owner, on the phone:**
   - creates the Messaging API channel under a new provider just for this shop (F8);
   - opens the URL and logs in with LINE;
   - pastes the Channel secret and the long-lived Channel access token.
3. **Server:**
   - calls `GET /v2/bot/info` with the token, which returns the bot's `userId`, `basicId` and name;
   - encrypts both values and keeps the account inactive;
   - shows the owner the webhook URL. The owner presses **Verify** in the LINE console;
   - accepts that signed call only if the HMAC checks out under the submitted secret **and** `destination` equals the bot `userId`. That proves the secret and the token belong to the same channel. It then sets `verified_at`, and the owner's membership becomes `pending`.
4. **Operator** runs `tenants.js show <slug>`, which prints the basicId, OA name and the owner's LINE name (no secrets). He confirms the @basicId with the shop, then runs `tenants.js approve <slug>`. A squatter who claimed the slug with their own OA fails here, and `tenants.js reset-owner` reopens the claim.

**Staff.** The owner opens Team and taps Invite. The invite is:
- a 32-byte code, stored only as a sha256;
- single use, valid 24 h, at most 5 open per shop;
- shared as a QR code or through LINE as `https://app.chatudo.com/app/join#<code>`. The code sits after the `#`, so it never reaches Traefik, the app logs or a Referer header.

The staff member logs in and redeems the code, which makes them `pending`. The owner sees their LINE name and picture and taps Confirm.

**Removal and revocation.** When the owner removes someone, their membership is revoked, their sessions are deleted and their open SSE streams close at once (single process). A role change, a credential update or a removal needs a LINE login no older than 10 minutes.

**Owner lost the phone or left.** The operator runs `reset-owner`. The new owner re-proves control with a freshly issued channel token, which must match the stored bot `userId`.

**Operator (CTO/CEO).** The operator works only through the CLI: `create`, `show`, `approve`, `suspend`, `reset-owner`, `revoke-sessions`, `unlock`, `audit-tail`. Each verb is audited with `actor_kind=operator`. There is no web super-admin on Chatudo. If the operator needs to support a shop, the owner invites them as staff, which is consented, visible and removable.

## 3. Session

**Cookie.** `__Host-cu_sid`, 32 random bytes, HttpOnly, Secure, `SameSite=Lax` (Strict would drop it on the redirect back from LINE Login), `Path=/`. The DB stores only its sha256, and the id rotates at login.

**Lifetime.** Idle timeout 7 days, absolute 30 days. `last_seen` is written at most once an hour. The session is loosely bound to the browser family (LINE-iOS, Chrome-Android and so on); a change revokes it.

**OAuth.** State, nonce and PKCE S256 travel in a 10-minute `__Host-cu_oauth` cookie that points to a server-side map. The server checks the id_token's `iss`, `aud`, `exp` and `nonce`. `return_to` may only be a path under `/app/`.

**CSRF.** Every non-GET request needs all three of:
- `Origin: https://app.chatudo.com`;
- an `X-CSRF-Token` header equal to the per-session token returned by `GET /admin/inbox/me`;
- `Content-Type: application/json`. The router rejects form-encoded bodies, which `server.js:50` parses for every route.

GET requests must stay free of side effects.

**Logout.** A POST that deletes the session row, expires the cookie and sends `Clear-Site-Data: "cookies"`. There is also "log out other devices".

**Rate limits** (in-process; `trust proxy=1` on Chatudo only):

| Action | Limit |
|---|---|
| Login | 20 per 10 min per IP |
| Setup submit | 5 per hour per shop; 5 failures lock setup until `tenants.js unlock` |
| Invite redeem | 10 per hour per IP |
| Approve, edit, reject, message, reply, tags | 60 per min per session; 300 per min per shop |
| Reads | 300 per min per session |

There is no password, so there is no account lockout; LINE handles credential brute force.

**SSE.** The page opens `new EventSource('/admin/inbox/events')`. On the same origin the browser sends the cookie, so no token goes in the URL. The session is checked when the stream opens and every 60 s after that. Limits: 3 streams per session, 20 per shop. The server closes a stream after 30 minutes, and the client's reconnect logs in again. Logout or removal closes the stream through a session-to-stream registry.

## 4. Authorization rule (fails closed)

- **R1.** Handlers never see the raw Supabase client. They get `db = scopedDb(principal)`.
- **R2.** The wrapper holds a fixed map from table to `tenant_slug`. A table missing from the map throws, which gives a 500 and an audit row `scope_error`. Example: `claudeflow_user_facts` does not exist on Chatudo, so skip it for shop users.
- **R3.** For a shop user, the wrapper adds `.eq('tenant_slug', p.tenant)` to every select, update and delete, and forces `tenant_slug` on every insert. Callers cannot pass a shop.
- **R4.** After every read, each row's `tenant_slug` must equal the user's shop. If not: 500, audit row `tenant_violation`, and nothing is returned.
- **R5.** Side-effect calls take the row that came back from the scoped read, never an id from the request. That covers `resolveApproval`, `resolveWithKb`, `sendParts`, `saveMessage`, `handoffStore.deactivate` and `markDecided`.
- **R5b.** `decided_by` comes from the session, never from the request body. Today the browser sets it through `body.admin_id` at `adminInboxApi.js:379`, `:492` and `:522`.
- **R6.** The shared-key super-admin exists only when the `x-api-key` header is used and `!isShopOnlyInstance()`. In that mode the wrapper filters nothing, so MoonieX is byte-identical. On Chatudo, a non-empty `ADMIN_INBOX_API_KEY` makes every inbox route answer 503 and logs one line. Row 6 of the runbook's secrets table (`instance.md` §0.2) must change accordingly.
- **R7.** Every route declares who may call it; a route without a declaration stops the router from building.
  - Owner and staff: contacts list, detail, tags, reply, approve, message, events.
  - Owner only: team, setup, credentials.
  - `/assist-examples*`: MoonieX shared key only; shops get 403.
- **R8.** An id from another shop returns 404 with the same body as an id that does not exist, so it cannot be used to probe.
- **R9.** Every bus event carries `tenant_slug`. The emitters are `approvalGate.js:364` and `:560`, `approval-timeout.js:112` and `:267`, and the four `resolved` events in `adminInboxApi.js`. A shop's stream gets an event only if `event.tenant_slug` equals its shop. An event without `tenant_slug` is never sent to a shop; the MoonieX shared key still gets everything.

**O7a must provide:**
- `isShopOnlyInstance()`;
- `tenant_slug` NOT NULL on Chatudo for contacts, admin_questions, conversations, user_memory, handoffs and reply_drafts, with indexes `contacts(tenant_slug, last_message_at desc)` and `admin_questions(tenant_slug, platform, sender_id, status)`;
- contact ids per shop;
- no `'mooniex'` fallback when the shop cannot be found;
- refusal of unsigned webhooks (F4), with a hook that lets the setup Verify call through for a not-yet-active account.

F8 (the mute key shared across shops) stays with O8; see §7.

## 5. Encryption at rest

- **Algorithm.** AES-256-GCM with a random 12-byte IV per value and a 16-byte tag. The additional authenticated data is `tenant_slug|platform|account_slug|field`, so a ciphertext copied into another shop's row does not decrypt.
- **Format.** One string per field inside the existing `credentials` jsonb: `enc:v1:<kid>:<b64url iv>:<b64url ct‖tag>`.
  - Encrypted fields: `channel_secret`, `channel_access_token`, `app_secret`, `verify_token`, `page_token`, `bot_token`.
  - A value without the `enc:v1:` prefix is MoonieX's legacy plaintext.
  - The existing `chatudo_line_requires_channel_secret` check still passes.
  - `900_chatudo_hardening.sql` adds a Chatudo-only check that every sensitive field present is `LIKE 'enc:v1:%'`, so the database itself refuses plaintext.
- **Key.** `CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET` holds a key ring: `kid=base64(32 bytes)[,kid=…]`. The first key encrypts; every key decrypts.
- **Decryption.** Only in `accountStore.refresh()`. A row with an unknown kid, a bad tag or a malformed value is dropped from the cache and logged as `platform:slug kid=` only. The account then returns 404 or the send fails. An `enc:` string never reaches LINE or the env fallback.
- **Missing or malformed key.** Both `chatudo-api` and `chatudo-cron` exit at boot with a log line naming the variable. MoonieX runs as today and drops any `enc:` row.
- **Rotation** (yearly, or on suspicion):
  1. A script adds the new key to the front of the ring, passing it on stdin.
  2. Restart.
  3. `rekey-credentials.js --apply` re-encrypts every row; it prints counts per kid only.
  4. `--check` shows 0 rows on the old kid.
  5. Remove the old key and restart.
- **If the key is lost,** it is recoverable: each owner reissues the token in the LINE console and enters it through the owner-only credentials update, with the same Verify step.
- **Writes** happen only through the setup/update endpoints or a CLI that reads stdin. `scripts/onboard-account.js:48-49` takes secrets as command-line arguments, where they show in `ps` and shell history; refuse those flags on Chatudo. The plaintext SQL insert in runbook §3 goes away.

## 6. Audit

**Storage.** Table `claudeflow_admin_audit`, RLS on with no policies. `REVOKE UPDATE, DELETE` from service_role, anon and authenticated makes it append-only for the app. Retention is 1 year; the operator purges older rows.

**Columns:** `at`, `tenant_slug`, `actor_kind` (owner, staff, super, operator, system, anon), `actor_id`, `session_ref` (first 12 hex of the session hash), `action`, `target_type`, `target_id`, `result` (ok, denied, conflict, error, rate_limited), `reason`, `request_id`, `idempotency_key`, `ip_prefix` (/24 for IPv4, /48 for IPv6), `ua_family`, and `meta`. `meta` may hold only these keys: `decision`, `text_len`, `parts_count`, `role`, `kid`.

**Actions logged:** login ok/fail, logout, session_revoked, setup_submitted, channel_verified, credentials_rotated, invite created/revoked/redeemed, member confirmed/removed/role_changed, contact_viewed, tags_updated, approve/edit/reject/message/reply, sse_opened, denied_cross_tenant, csrf_rejected, rate_limited, and every operator CLI verb.

**Never logged:** message, draft or edit text, tag values, tokens, codes, session ids, id_tokens, full IP addresses, LINE display names.

**stdout — a new finding.** `server.js:53-58` logs the first 400 characters of every request body. On Chatudo that already means customer LINE messages. It would also log the admin's edited answer, invite codes and the pasted channel tokens. Fix: log no bodies for `/admin/inbox/*` or `/app/*`, and none at all when `isShopOnlyInstance()`. An admin log line should hold only: method, route template, status, ms, tenant, actor, request_id.

## 7. Threat model

| Threat | Mitigation | Test |
|---|---|---|
| Cross-shop read/write by guessing contact or question ids | R1–R8: scoped wrapper, check after every read, 404 | Shop A's session × every route × shop B's ids → 404, 0 B rows returned, 0 sends |
| Stolen session | HttpOnly `__Host-` cookie; server-side revocation; browser-family binding; 7-day idle timeout; recent login needed for sensitive actions; IP prefix and browser in the audit | Replay the cookie from a different browser → 401; after removal or logout → 401 |
| Leaked login link | The setup URL holds no secret (proof = OA credentials + operator approval). Invite code after `#`, single use, 24 h, owner must confirm | Reused or expired code → 410; redeemed but unconfirmed → no data; captured logs never contain the code |
| SSE cross-shop leak | R9 filter; events without a shop are dropped for shops; revocation closes the stream | Emit A, B and no-shop events → A's stream sees only A; revoke closes it within 1 s |
| Shared LINE provider, same userId in two shops (F8/F14) | O7a per-shop contact ids; every query scoped. **F8 stays open (O8): approving at shop A unmutes the same userId at shop B.** Runbook rule: one provider per shop, plus an audit row `userid_collision` when a sender_id appears in two shops | Same U1 in A and B: approving at A touches only A's rows; the collision audit row fires |
| Insider on the box (every agent session on Contabo runs as root) | Secrets only through `infisical run`, with no `.env.chatudo` on disk after cutover; append-only audit; no web super-admin. Recommend a PreToolUse hook denying `docker inspect`/`docker exec` on `chatudo-*` and reads of `/proc/*/environ`. **Residual: root can read process memory — the CEO must accept this** | Hook test; no secret file under the checkout |
| DB dump or leaked service key | Tokens are ciphertext and the key is not in the DB; session and invite values are hashed. Message text stays plaintext (Supabase disk encryption only). Rotate the service key on a leak | Dump fixture: nothing decrypts without the key |
| Replay or double tap of approve | Claim the row before sending: `UPDATE … SET claim_id, claimed_at WHERE id AND tenant_slug AND status='awaiting_approval' AND (claim_id IS NULL OR claimed_at < now()-2 min) RETURNING`; clear the claim if the send fails. An `Idempotency-Key` (unique per shop) returns the first result. Plus CSRF | 2 parallel approves → 1 `sendParts`; same key twice → 1 send; failed send → still approvable |
| Stored XSS through a customer message or display name | Render with textContent only; CSP without inline scripts; show flex parts as types only | `<img onerror>` renders inert; CSP header asserted |
| Login CSRF or open redirect | State + nonce + PKCE; `return_to` limited to `/app/` | Bad or reused state, wrong nonce or aud, `return_to=//evil` → rejected |
| MoonieX's shared key set on Chatudo | R6 answers 503 | Key set on Chatudo → every inbox route 503 |
| Someone claims a shop's slug at setup | Proof of OA control + operator basicId check + 48 h window | A claim with a foreign OA stays pending; `reset-owner` reopens |
| New paths swallowed by the `/:platform/:account` catch-all | Mount order (§1) | `GET /app/join` returns the page |

**The approve race also exists on MoonieX today.** `kb-checker.js:412` sends before the unconditional status update at `:425`, so a double tap can send twice. I left MoonieX unchanged in this design; the CTO should decide whether to fix it there.

## 8. Builder's tests and my sign-off checklist

**The builder adds, all in `npm test`, with Supabase and LINE stubbed ($0):**
- (a) A route × user matrix. Users: A owner, A staff, B, no session, expired, revoked, shared key on Chatudo, shared key on MoonieX.
- (b) The route-declaration registry, plus a static test that no handler calls the raw client's `.from(`.
- (c) The check after every read.
- (d) Every test in the §7 table.
- (e) Crypto: round trip, tampering, a ciphertext moved to another row, unknown kid, ring rotation, rekey printing counts only, refusal to boot without the key.
- (f) Log capture across the whole suite: 0 hits for fixture tokens, codes or message text.
- (g) MoonieX golden tests: shared-key requests produce the same query chain and response bodies as `3192107`, and `/app` and `/admin/inbox/auth` return 404 on MoonieX.

**I will check before signing DoD item 4:**
- [ ] Full suite has 0 failures, and the new test files are in `package.json`.
- [ ] Every handler goes through the scoped wrapper and declares who may call it; grep finds 0 raw `.from(` calls in handlers.
- [ ] Every `adminInboxBus.emit` carries `tenant_slug` (grep count equals the number of emitters).
- [ ] O7a: no `'mooniex'` fallback reachable on Chatudo; `tenant_slug` NOT NULL in `900_chatudo_hardening.sql`; contact ids per shop; unsigned webhooks refused (F4).
- [ ] `body.admin_id` is ignored for shop users; the approve claim and the idempotency key are in place.
- [ ] Decryption happens only in `accountStore`; an `enc:` string is never used as a token; the plaintext-refusing check is in `900_chatudo_hardening.sql`; both containers refuse to boot without the key.
- [ ] Audit grants are append-only; `meta` accepts only the allowed keys; no body logging on Chatudo.
- [ ] Compose labels match §1. `.env.chatudo.example` has no `ADMIN_INBOX_API_KEY` value and does list the two new names. Runbook §0.2 and §3 are updated. `onboard-account.js` refuses secrets as arguments.
- [ ] I read the output of a pre-launch smoke test the CTO runs on the live instance with two test shops: A's session gets 404 on B's contact id, A's stream shows only A, and a removed member is cut off within 1 s.

O7b is due Fri 16 Oct.

## 9. Secrets the CEO must enter

Proposed Infisical location: project MoonieX-ClaudeFlow, environment `prod`, folder `/chatudo`. This is open: PLAN §3 has no rule for two running copies of one repo that need different prod values under the same names. The CTO should confirm.

| Name | What | Where he gets it |
|---|---|---|
| `LINE_LOGIN_CLIENT_SECRET` | Chatudo's LINE Login channel secret (the OIDC client secret) | LINE Developers Console → a new provider "Chatudo" (not any shop's) → Create channel → LINE Login, web app → Basic settings → Channel secret. On the same channel: Callback URL `https://app.chatudo.com/admin/inbox/auth/line/callback`, scopes `openid profile` (no email), then set it to Published (while in Developing, only listed testers can log in). A worker captures the value with `CTO_Procedure_KeyFetch`: the CEO only logs in through the relay, and nobody sees it. The Channel ID goes in `LINE_LOGIN_CLIENT_ID`, which is not a secret. |
| `CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET` | The AES key ring for shop tokens | No provider. A zero-model script (`openssl rand` → `infisical_setup.py put --stdin`) runs from a Run Inbox card the CEO taps. Its output is the name and kid only. |
| `ADMIN_INBOX_API_KEY` | Remove it. It must be absent on Chatudo. | — |
| (none) | No key is needed for sessions, CSRF or invites | Each is random per record and stored hashed |

**Also for the CEO, not secrets:** add a DNS A record `app.chatudo.com` → `194.233.80.26`, DNS-only. Each shop's LINE channel secret and token are entered by the shop owner on the setup page — never by the CEO, never in Infisical, never in chat.

## Skill learning
- MISSING [no owner] : Infisical `docs/design/secrets-infisical/PLAN.md` §4b has no KIND for a data-encryption key we mint ourselves (no `KEY`), so the variable had to be named `…_SECRET` · evidence: task-f50d0c4c §5/§9 (`CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET`)
- MISSING [no owner] : PLAN.md §3 (one project per repo, no folders until needed) has no rule for two prod instances of one repo that need different values under the same names · evidence: `docker-compose.chatudo.yml` + `docs/chatudo/instance.md` §0.2 (MoonieX and Chatudo both run ClaudeFlow)
- MISSING [CTO_Procedure_KeyFetch §When to invoke / when not] : no path for a secret with no provider (a random key we generate); step 5's last4 check against a provider page cannot apply · evidence: task-f50d0c4c §9 encryption key
