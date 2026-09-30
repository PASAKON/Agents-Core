# Chatudo O7b-3b · developer · staff invites, team page, member removal, owner credential update

> CTO brief, 2026-09-29 (Thai time). Repo MoonieX-ClaudeFlow, based on main `ec9a6dd` (O7b-3a merged).
> Design, final and reviewed: `docs/briefs/chatudo-o7b-security-design.md` §2 "Staff", "Removal and revocation", §4 R7/R8, §5 "If the key is lost", §6, §7 rows "Leaked login link" and "Shared LINE provider".
> Previous piece: `docs/briefs/chatudo-o7b3a-build.md` (identity sessions, access classes, setupStore pattern, Verify handshake).

## Job (BUILD)

- **Staff invites.** A shop owner can invite staff with a single-use link. The staff member logs in with LINE, redeems the link, and the owner confirms them.
- **Removal.** The owner can remove a member, and that member is cut off at once.
- **Credential update.** The owner can replace the shop's LINE credentials (after a lost key, or after reissuing them in the LINE console). The new credentials go live only after they prove they belong to the same LINE OA.
- **Everything is fail-closed** and 404 on MoonieX. MoonieX behaviour and its golden tests are unchanged.

## CTO rulings for this piece (do not re-decide)

1. **No role-change endpoint.**
   - A shop has exactly one owner, enforced by `uq_web_admin_members_one_owner` from O7b-3a. Changing a role would therefore mean transferring ownership.
   - Ownership moves only through the operator's `tenants.js reset-owner`. The roles are owner (one) and staff (many).
   - Record this in `docs/chatudo/tenant-isolation.md` as a deliberate narrowing of design §2.
2. **No QR code in this piece.**
   - The invite is shared as a link: a "copy link" button plus a "share on LINE" link.
   - No external script and no vendored QR library. QR is a later nice-to-have.
3. **One LINE OA belongs to one shop.**
   - Add a partial unique index on `claudeflow_webhook_accounts (bot_user_id) WHERE bot_user_id IS NOT NULL`.
   - `setup/submit` (O7b-3a code) and the new credential update both answer 409 `channel_in_use` when the bot userId is already bound to another account. Catch the 23505 as well as pre-checking.

## Build

### 1. Migration `supabase/migrations/202609291206__chatudo_o7b3b_team_credentials.sql` (idempotent, file only)
- `claudeflow_webhook_accounts`: add
  - `pending_credentials jsonb`
  - `pending_credentials_at timestamptz`
  - `pending_by uuid`, the web admin id
  - `credentials_rotated_at timestamptz`
- Add the `bot_user_id` partial unique index from ruling 3.
- `claudeflow_web_admin_invites`: check that O7b-1 already has `code_hash`, `tenant_slug`, `role`, `state`, `expires_at`, `redeemed_by`. Add `created_by uuid` and `redeemed_at timestamptz` if they are missing. Do not change existing columns.
- `900_chatudo_hardening.sql`: the `chatudo_credentials_encrypted` CHECK must also cover `pending_credentials`. Every sensitive field present in it must be `IS NULL OR LIKE 'enc:v1:%'`.
- Add ORDER and README rows.

### 2. Scoping
- Add `claudeflow_web_admin_members` and `claudeflow_web_admin_invites` to `scopedDb`'s `TABLE_TENANT_COLUMN`. Owner routes read and write them only through `scopedDb(principal)` (R1/R3/R4).
- `claudeflow_web_admins` (LINE name and picture) is global.
  - Read it in a new `src/lib/teamStore.js` with explicit `.in('id', ids)`.
  - The `ids` must come from rows that the scoped read returned. Never take them from the request (R5).
- `teamStore.js` also owns the identity-side redeem, the same way `setupStore.js` does: an explicit `.eq()` in every function, and a thrown error on `{error}` (read error ≠ "none").

### 3. Routes (all declared in `ROUTE_DECLARATIONS`, all Chatudo-only → 404 on MoonieX)

| Route | Access | Notes |
|---|---|---|
| `GET /admin/inbox/team` | owner | Returns `members[]`: `{member_id, line_name, picture_url, role, state}`, pending and active only. Returns `invites[]`: `{id, created_at, expires_at}` for open invites only, never the code or its hash. |
| `POST /admin/inbox/team/invites` | owner | Mints 32 random bytes and stores only the sha256. Role is staff. Valid 24 h. At most 5 open per shop, else 409 `invite_limit`. Returns `{url: "https://app.chatudo.com/app/join#<code>"}` **once**. Audit `invite_created` (no code). |
| `POST /admin/inbox/team/invites/:id/revoke` | owner | open → revoked. An id from another shop or a missing id gets the same 404 (R8). Audit `invite_revoked`. |
| `POST /admin/inbox/team/join` `{code}` | identity, owner, staff | See below. Rate limit `LIMITS.inviteRedeem` (10/h/IP), checked first. |
| `POST /admin/inbox/team/members/:id/confirm` | owner | pending → active, staff only. Audit `member_confirmed`. |
| `POST /admin/inbox/team/members/:id/remove` | owner + `requireRecentLogin(10)` | See below. |
| `POST /admin/inbox/setup/credentials` `{channel_secret, channel_access_token}` | owner + `requireRecentLogin(10)` | See below. |

A stale login answers 403 `recent_login_required`, the same as O7b-3a's setup/submit.

**Join (redeem):**
1. Refuse a malformed code (not 43 base64url characters) with 410. Hash the code.
2. Read the invite by `code_hash`. Unknown, revoked, redeemed or expired all get **410 `invite_invalid`, the same body**.
3. If the caller already holds a pending or active membership in that shop (the owner included), answer 409 `already_member` **without consuming the code**.
4. Consume atomically: `update … set state='redeemed', redeemed_by, redeemed_at where id=? and state='open' and expires_at > now()`, then check the affected row. Zero rows means 410. Two concurrent redeems give exactly one winner.
5. Create a pending staff membership. A revoked row for the same (admin, shop) already exists under the O7b-1 unique constraint, so reopen it to `pending`/`staff` instead of inserting.
6. Audit `invite_redeemed`. The caller's session stays as it is: they get access only after the owner confirms and they switch shop.

**Remove:**
- The target must be a member of the owner's shop, read through scopedDb (another shop's id → 404).
- The owner row cannot be removed: 409 `cannot_remove_owner`.
- In this order:
  1. Set the membership to `revoked`, with `revoked_at`.
  2. Revoke every session of that web admin **for this tenant**, and collect their ids.
  3. Close every open SSE stream of those sessions **in the same tick**, through the O7b-1 registry (`sseStreamsBySession`). Add a `closeStreamsForSessions(ids)` helper next to it.
  4. Audit `member_removed`.
- The removed member's next request answers 401 (membership re-read, O7b-1).

**Credential update** (owner, recent login, shop `active`):
1. Both fields are required strings. Reject a `channel_secret` that is not `^[0-9a-f]{32}$` with 400. Values stay in memory only, the same as setup/submit.
2. Call `GET /v2/bot/info` with the new token.
   - Failure → 422 `line_verification_failed`.
   - `userId` ≠ the stored `bot_user_id` → **422 `channel_mismatch`, no write**. This stops a swap to another OA.
3. Encrypt with the same `encryptCredentials` and AAD as the live row. Write `pending_credentials`, `pending_credentials_at=now()` and `pending_by`. **Do not touch `credentials`.** Audit `credentials_submitted`.
4. Reply `{ok:true, webhook_url, next:"press Verify in the LINE console"}`.

### 4. Promotion via LINE Verify (`server.js`; no bypass anywhere in `line.js`)
Pending credentials become live only when a LINE webhook request proves them. Add `accountStore.getRotationCandidate('line', slug)`:
- It reads fresh from the DB (active **or** inactive row).
- It returns `{accountId, tenantSlug, botUserId, pendingSecret}`, with the secret decrypted there, and **only** when `pending_credentials` is set and `pending_credentials_at` is under 24 h old. Otherwise it returns null.
- Log `platform:slug kid=` only.

In `multiAccountWebhook`, Chatudo + LINE only, try promotion in both of these places:
- **(a) The active account was found**, but `verifyLineSignature(rawBody, sig, acct.secret)` is false.
- **(b) No active account was found in the cache.** This covers key loss, where the live row fails to decrypt and is dropped. Keep O7b-3a's `tryLinePendingVerify` for inactive setup rows. Try the rotation candidate as well.

Promotion happens only if the HMAC verifies under `pendingSecret` **and** `body.destination === botUserId`. Then:
1. Set `credentials = pending_credentials`, clear `pending_*`, and set `credentials_rotated_at`. This is one update, with its `{error}` checked.
2. Audit `credentials_rotated`.
3. Call `accountStore.refresh()`.
4. Re-dispatch the request through the **normal** path: `getAccount`, then `handleLine`, which checks the signature again under the new live secret. An empty Verify body answers 200.

If promotion fails, fall through to today's behaviour (401 or 404). Never process an event on any path that has not passed `verifySignature` against the credentials it uses.

### 5. `userid_collision` audit (design §7, F8 runbook rule)
- In the Chatudo inbound contact path (`src/webhook/contactTracker.js` or wherever the LINE contact row is created with `tenant_slug`): when a new contact is created for (platform, sender_id) and the same sender_id already exists as a contact of **another** tenant, write one audit row per contact.
  - The row carries: `action 'userid_collision'`, the current shop as `tenantSlug`, `targetType 'contact'`, and `targetId` = this shop's contact id.
  - Never write the raw userId into meta.
- Dedupe in memory per process.
- It must not throw into the webhook path and must not run on MoonieX.

### 6. `/app` pages (same rules as O7b-3a: CSP, no inline script, textContent only, Thai, no em dash, no emoji, icons as inline SVG if needed)
- `join.html` + `join.js`:
  - Read the code from `location.hash`, then **immediately** `history.replaceState` to drop the hash.
  - If there is no session, keep the code in `sessionStorage` (never `localStorage`) and send the user to LINE Login with `return_to=/app/join`.
  - POST `/team/join`, show pending status, and clear `sessionStorage`.
- `team.html` + `team.js`, owner only: the member list with LINE name and picture; confirm and remove buttons (remove asks for confirmation); an invite button that shows the link once with copy and "share on LINE" (`https://line.me/R/share?text=` + encoded URL); the open invites with revoke.
- `settings.html` + `settings.js`, owner only: webhook URL, @basicId, and the credential update form. Show the 3 steps: reissue in the LINE console, paste, press Verify.
- Add links from `index.html` for owners.

### 7. Docs
- `docs/chatudo/shop-setup.md`: the staff invite flow, and credential rotation and key-loss recovery from the owner's side.
- `docs/chatudo/credential-encryption.md`: the key-loss path now points at the owner's credential update.
- `docs/chatudo/tenant-isolation.md`: an O7b-3b section with the rulings above, the new routes and their access, and the promotion path.

## Security checks the CTO will grep for (all six have bitten earlier O7b pieces)
1. No `throw`, log or response echoes a code, a token, a secret or an id_token. Any test that feeds a malformed secret or code asserts that no 8-character substring of it appears in the output.
2. Fail-closed:
   - A missing or unknown principal kind denies.
   - There is no `? … : 'super'`.
   - A read `{error}` throws. Only an empty result means "none".
   - supabase-js returns `{error}` and does not throw: check it on **every** write.
3. A tenant check after a read covers every row. A narrow select still carries `tenant_slug` (scopedDb does this, so don't bypass it).
4. Identity, role and tenant come from a fresh read, never from a copy stored earlier.
5. Every "only one" rule has a DB unique index, and the code claims before it writes. The rules here: one redeem per code, one OA per shop, at most 5 open invites. A count check is fine for the cap, but test the race for the first two.
6. No unauthenticated request writes to the DB unboundedly. `/team/join` needs a session, and it is rate-limited before any read.

## Tests (all in `npm test`; add each new file to the `test` script; $0; no network; Supabase and LINE stubbed)
- **A route × user matrix for every new route.** Users: A owner, A staff, B owner, identity, no session, expired, revoked, shared key on Chatudo (503), MoonieX (404).
- **Invites:**
  - The 6th open invite → 409.
  - The response carries the code once, and `GET /team` never shows it.
  - A revoke from B → 404.
  - Redeem: expired, used, revoked and unknown all give 410 with the same body.
  - An `already_member` answer does not consume the code.
  - Two concurrent redeems of one code give exactly one winner.
  - A revoked member re-invited gets their row reopened.
  - Rate limit → 429.
- **Remove:**
  - The member's next request → 401.
  - Their SSE stream closes in the same tick (assert on the registry).
  - The owner row → 409.
  - A stale login → 403.
  - B's member id → 404.
- **Credential update:**
  - A wrong OA → 422 with no write.
  - A secret that is not hex → 400.
  - Success writes only `pending_*` and leaves `credentials` untouched.
  - The pending ciphertext passes the CHECK format (`enc:v1:`).
- **Promotion:**
  - (a) An active account signs with the new secret: promoted, an audit row, and the event is processed with the new secret after refresh.
  - (b) The live row fails to decrypt (key loss) and the pending creds were made under the new key: promoted.
  - A pending entry older than 24 h is ignored → 401.
  - A wrong destination → no promotion.
  - The old secret still works until promotion.
- **One OA per shop:** submitting or updating with a bot userId already bound elsewhere → 409 `channel_in_use`, including the 23505 race.
- **userid_collision:** the same sender at shops A and B writes one row, at B, with no raw userId. Nothing is written on MoonieX.
- **Static:**
  - No inline script, em dash or emoji in the new pages.
  - `join.js` reads `location.hash` and calls `history.replaceState`.
  - Every new route is declared.
  - No raw `.from(` in the new handlers except through teamStore and setupStore.
- **Log capture** across the new tests: 0 hits for fixture codes, tokens and secrets.
- **MoonieX golden** tests stay green, unchanged.

## Acceptance
- The full suite is green on the dummy env: `SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SERVICE_KEY=dummy SUPABASE_KEY=dummy OPENAI_API_KEY=dummy OPENROUTER_API_KEY=dummy npm test`
- The only tolerated failure is the known timing flake in `tests/lineSompongGroup.test.js`. Re-run it alone to confirm it.
- MoonieX paths are unchanged.

## Rules
- Build only this piece. The approval UI is C3, and F8 is O8.
- Never copy or create a `.env` anywhere.
- No network calls and no DB access. Write SQL files only and never apply them. $0 spend.
- Commit on your branch in small commits. Do not push or merge; the CTO merges.
- Every date and time you report is Thai time (Asia/Bangkok).
- Where the design is ambiguous, pick the more closed option and list it under "Design deviations".

## Report (last message)
- Files changed.
- Commits (sha + one line).
- The suite line (`# tests/pass/fail/skipped`).
- Design deviations.
- What the security_engineer sign-off should look at first.
- What is still open.
- End with `## Skill learning`: one line per item, in the form `WRONG|MISSING|COSTLY [<skill> §<section> | no owner] : … · evidence: …`, or exactly `- (none)`.
