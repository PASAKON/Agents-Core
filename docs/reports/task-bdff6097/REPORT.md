# REPORT task-bdff6097

S1 of `docs/design/mooniex-care.md`: outbox, reply/push sender, push quota gate, dry-run, tests against fakes.

## Files changed
- `lib/care/outbox.py`: `care_outbox` store (+ `care_state` flag table). Idempotent enqueue (`INSERT OR IGNORE` on unique key), atomic `claim_sending` (`queued|deferred -> sending`, before any send), terminal markers, crash-leftover listing (`stuck_sending`, never auto-retried).
- `lib/care/care_outbox.pg.sql`: Postgres migration (not applied here).
- `lib/care/quota.py`: pure `decide_push` + `read_consumption` (GET `/v2/bot/message/quota/consumption`).
- `lib/care/sender.py`: `ReplyBackend` (POST `/v2/bot/message/reply`), `PushBackend` (POST `/v2/bot/message/push`, `X-Line-Retry-Key` derived from the idempotency key), `CareSender` router.
- `config/care.yaml`: TBD placeholders (null) for reply-token lifetime, reset timezone, critical reserve, S2 ceilings; `dry_run: true`.
- `tests/test_care_s1.py`: 13 tests with fake HTTP and in-memory sqlite.

## Behaviour
- Reply token valid (or expiry unknown) -> reply path, no quota read. LINE 400 -> token cleared, row `deferred`.
- Token expired/absent: `care_reply` -> `deferred` (waits for S2 browser sender, no push). `important_announcement` -> push, only after quota gate.
- Gate: consumption read before every push; COO alert once per month at projected >= 240 (deduped in `care_state`); hard stop when projected > 300; non-critical pushes also stop inside the critical reserve; HTTP 429 sets a monthly halt flag and stops all further pushes and quota reads.
- Network errors are never retried blindly: row -> `failed` (`*_network_unconfirmed`).
- Token is a constructor parameter, only put in the Authorization header handed to the injected `http`; never logged or stored (test dumps DB for it).
- Dry-run: no claim, no state change, no POST (consumption GET only).

## Validation performed
- **Tests were NOT executed**: the AGY contract forbids running pytest. The code and tests were reviewed by hand only. Reviewer please run `python -m pytest tests/test_care_s1.py`.

## Risk
- Not yet run, so first run may show small test or sqlite/SQL issues.
- The store uses sqlite-style qmark SQL. The Postgres hub needs a thin adapter (`%s`, `ON CONFLICT DO NOTHING`, JSONB); the SQL is not yet proven on PG. The migration file is untested.
- Reply-token lifetime is TBD: with no expiry set, a reply is attempted and an HTTP 400 is treated as expiry. If LINE returns another code for an expired token, the row goes `failed`.
- The month key and quota reset use a UTC placeholder; reset timezone is TBD, so the 240 alert and halt flag may re-arm up to hours off.
- `critical_reserve` is null, treated as 0 (reason `ok_reserve_unset`); a CEO value is needed.
- The `critical` flag is an addition to the design schema (column on `care_outbox`).
- Not wired to `src/webhook/line.js`, to the account-store loader, or to a real COO alert channel (all injected). No live LINE calls, no browser sender, no winbox.

## Blockers
- (none)

## Skill learning
- (none)
