# REPORT task-cd645deb

## Summary

Wrote the design specification `docs/design/mooniex-care.md` for MoonieX Care (`@mooniex`, `basicId`: `@587kfqpt`, display name: `MoonieX Officials`, confirmed by CEO). No sender or outbox code was built, per task instructions.

Key design elements covered in `docs/design/mooniex-care.md`:
- **Flow & Credential Hygiene:** Inbound via `src/webhook/line.js` into the LuNar chat flow; notes `.env` line 12 is malformed, current token resides in the account store, and P1 migrates the token to Infisical. Enforces never printing/storing the token and never committing customer chat screenshots to git.
- **`care_outbox` Table & State Machine:** Defines schema with `idempotency_key`, states (`queued`, `sending`, `sent`, `deferred`, `dropped`, `failed`, `fallback`), and the mandatory pre-click transition to `sending`.
- **Reply-First & Quota Policy:** Uses webhook `replyToken` first (0 quota consumed; lifetime **TBD** per `docs/research/line-messaging-quota.md`), restricts API push to post-token-expiry **important announcements only**, tracks the 300/month Thailand Free plan quota via `GET /v2/bot/message/quota/consumption` before each batch, alerts once at 240 (80%), and marks quota reset time **TBD**.
- **`winbox` LINE OA Manager Browser Sender:** Waits for `winbox` online; locates the CEO's logged-in browser via `relay-inventory.mjs --site chat.line.biz` with no new login (CDP port **TBD**); claims the screen per `ALL_Rules_Winbox_PCLease` only if touching the foreground GUI (headless/CDP needs no lease); never restarts MT5 (`terminal64.exe`) or `winbox`; enforces channel check (`@587kfqpt` / `MoonieX Officials` / `@mooniex`) and recipient readback; throttles with per-hour and per-day ceilings (**TBD**) and human-like jittered pacing; halts via a manual-reset kill switch on `captcha`, `warning`, or `logout` (alerting COO once); and defines sanitized test fixtures for `captcha`, `warning`, `logout`, and `normal chat`.

## Files Changed

- `docs/design/mooniex-care.md` (created)
- `docs/reports/task-cd645deb/REPORT.md` (created)

## Risk Section

Summary of the 8 operational risks and mitigations documented in `docs/design/mooniex-care.md` §4.5:

1. **Account suspension for automation:** Mitigated by per-hour/per-day throttle ceilings (**TBD**), human-like jittered pacing, and immediate kill switch on any warning/captcha; falls back to webhook reply token.
2. **Wrong recipient:** Mitigated by mandatory channel check (`@587kfqpt` / `MoonieX Officials` / `@mooniex`) and DOM recipient readback before marking `sending` and clicking Send.
3. **Session expiry:** Detected via `relay-inventory.mjs --site chat.line.biz` and the `logout` detector; never attempts automated login, trips the kill switch, alerts COO once, and falls back to webhook reply tokens.
4. **UI change:** Mitigated by strict DOM selector checks validated against offline fixtures (`captcha`, `warning`, `logout`, `normal chat`), failing closed before `sending` on mismatch.
5. **Double send:** Prevented by unique `idempotency_key` on `care_outbox`, marking `sending` before clicking Send, and never blindly auto-retrying `sending` rows after a crash.
6. **PII in screenshots:** Prevented by prohibiting customer chat screenshots in git, preferring DOM readback over pixel capture, and purging any temporary diagnostic captures.
7. **`winbox` contention:** Avoided by operating headless/CDP (which requires no PC lease per `ALL_Rules_Winbox_PCLease`), or strictly obeying `pc-lease.sh` (`status`, `take`, per-stage `gate`, `give-back`) and yielding immediately on `PC: CEO` (exit `3`).
8. **`winbox` offline:** Sender waits for `winbox` online (leaving browser-bound rows `deferred`), never reboots `winbox` or restarts MT5, and relies on the **fallback reply token via webhook** for active inbound turns.

## Validation Performed

- Verified quota endpoints, Thailand Free plan limit (300/month), 80% threshold math (240), and reply-token quota exemption against `docs/research/line-messaging-quota.md`.
- Verified `winbox` screen lease rules, headless/CDP exemption, and `PC: CEO` hold behavior against `.claude/skills/ALL_Rules_Winbox_PCLease/SKILL.md`.
- Verified all required sections, states, risk table entries, fixtures, and TBD markers (`CDP port`, `reply-token lifetime`, `quota reset`, `exact ceilings`) are present in `docs/design/mooniex-care.md`, and confirmed no sender or outbox implementation files were created.

## Limitations

- Four parameters remain explicitly marked **TBD** pending live inspection/measurement: CDP port on `winbox`, exact webhook `replyToken` lifetime, exact monthly quota reset time, and exact per-hour/per-day browser sender throttle ceilings.

## Blockers

- (none)

## Skill learning

- (none)
