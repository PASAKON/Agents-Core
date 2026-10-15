# REPORT task-33a2c506

## Summary

Hardened `scripts/infisical/copy_secret.mjs` to address all six LOW findings in `PASAKON/Agents-Core#279`, extended the Node test suite in `tests/js/copy_secret.test.mjs` with dedicated test cases for each item and stricter output assertions (`NEVER_PRINTED` extended with value prefixes and lengths across all modes), and updated the pass count floor in `tests/test_copy_secret.py`.

Suggested neutral commit message:
`fix(infisical): harden copy_secret.mjs input and state checks (closes #279)`

## Files Changed

- `scripts/infisical/copy_secret.mjs` — Implemented the six hardening checks for `PASAKON/Agents-Core#279`.
- `tests/js/copy_secret.test.mjs` — Extended `NEVER_PRINTED` with value prefixes (`VALUE.slice(0, 4)`, `OTHER.slice(0, 4)`) and lengths (`String(VALUE.length)`, `String(OTHER.length)`), set `COPY_SECRET_TEST: '1'` in the test runner environment, and added six tests (`#279(1)` through `#279(6)`).
- `tests/test_copy_secret.py` — Updated the expected passing test floor from `>= 24` to `>= 30`.
- `docs/reports/task-33a2c506/REPORT.md` — Task report.
- `REPORT.md` — Root worktree task report.

## Findings

### Mapping of Issue #279 Items to Changes and Tests

| # | Item (`PASAKON/Agents-Core#279`) | Change in `scripts/infisical/copy_secret.mjs` | Test in `tests/js/copy_secret.test.mjs` |
|---|----------------------------------|-----------------------------------------------|-----------------------------------------|
| 1 | `INFISICAL_API_URL` honoured only under an explicit test marker | Lines 139–142: Refuse with exit 64 (`usage('refused: INFISICAL_API_URL requires COPY_SECRET_TEST=1 (tests only)')`) when `process.env.INFISICAL_API_URL` is set without `process.env.COPY_SECRET_TEST === '1'`. | `#279(1): INFISICAL_API_URL is refused unless COPY_SECRET_TEST=1 is set` (lines 501–511): Verifies both copy and `--find` modes exit 64 with 0 CDP and 0 API requests when `COPY_SECRET_TEST` is unset/empty, `'0'`, or `'true'`. |
| 2 | `--find` / `--dry` must write nothing when token has no `organizationId` | Lines 194–195: When `!orgId` and `findRe || opt.dry`, exit 6 immediately (`die(6, 'session token has no organizationId; --find and --dry write nothing (no select-organization)')`) before `GET /api/v1/organization` or `POST /api/v3/auth/select-organization`. Also prefixes `die()` output with `[find]` when `toStderr` is active (line 61). | `#279(2): --find and --dry with a token that has no organizationId exit 6 without calling select-organization` (lines 513–525): Verifies `--find` and `--dry` with `TOKEN_NO_ORG` exit 6 with 0 API calls. |
| 3 | Write-failure message maps `error` field to an allowlist of HTTP error names | Lines 49–57, 359–361: Added `HTTP_ERRORS` `Map` allowlist of standard HTTP error names and mapped `wrote.json?.error` via `HTTP_ERRORS.get(wrote.json.error)`, omitting any unrecognised value from the exit 11 message. | `#279(3): write failure maps response error field through HTTP_ERRORS allowlist and drops unallowlisted strings` (lines 527–540): Verifies arbitrary strings (including alphabetic strings matching the former regex) and echoed values are omitted, while allowlisted error names (`UnprocessableEntity`, `BadRequest`) are preserved. |
| 4 | `webSocketDebuggerUrl` from `/json/list` requires a loopback host and the same port as `<cdp-url>` | Lines 131, 155–160: Added `portOf(u)` and validated that `tab.webSocketDebuggerUrl` parses as a `ws:` or `wss:` URL with `LOOPBACK.has(wsUrl.hostname)` and `portOf(wsUrl) === portOf(cdp)` before opening `new WebSocket(wsUrl.href)`, exiting 3 on mismatch. | `#279(4): webSocketDebuggerUrl from /json/list must be a loopback ws(s) URL on the same port as <cdp-url>` (lines 542–556): Verifies non-loopback hosts, different loopback ports, and non-WebSocket schemes exit 3 with 0 WebSocket upgrades and 0 API calls. |
| 5 | Secret and project names from the API must match `/^[\w.-]{1,256}$/` before printing | Lines 47–48, 153, 175, 197, 209–210, 214, 218, 230, 259, 322: Added `SAFE_NAME = /^[\w.-]{1,256}$/` and `safeName()`, filtering project names/IDs/slugs/types, organization IDs/names, environment slugs, and secret keys (`s.secretKey`) in both `--find` and copy modes before any output or matching. | `#279(5): secret and project names not matching /^[\w.-]{1,256}$/ are dropped before printing` (lines 558–592): Verifies secret and project names containing newlines or exceeding 256 characters are ignored and never printed in both copy and `--find` modes. |
| 6 | `secretValueHidden === true`: refuse to copy and exclude from `--find` identical grouping | Lines 265–266, 277–288, 325, 333–337, 366: In copy/`--dry` mode, records `hidden: s.secretValueHidden === true` on matched source secrets and exits 8 before any target write; also checks `secretValueHidden !== true` on read-back verify. In `--find` mode, skips hidden secrets when building `groups`, increments `hiddenCount`, and reports `values identical across matches: no` when any match is hidden. | `#279(6): secretValueHidden === true refuses to copy and is excluded from --find identical grouping` (lines 594–619): Verifies copy and `--dry` exit 8 with 0 writes when the matched secret has `secretValueHidden: true`, and verifies `--find` prints `values identical across matches: no` while omitting masked secrets from all `value group` lines. |
| — | Extend `NEVER_PRINTED` to value length and prefix in every mode | No script change needed; script already suppresses value output. | Lines 22–26, 194, 472–480: Extended `NEVER_PRINTED` in `run()` with `VALUE.slice(0, 4)`, `String(VALUE.length)`, `OTHER.slice(0, 4)`, and `String(OTHER.length)` so every test invocation in copy, `--dry`, `--find`, and error modes asserts they never appear on stdout or stderr. |

## Commits

- Uncommitted changes in worktree (to be committed by the launcher after completion per worker contract).

## Tests

Added 6 new `node:test` cases (`#279(1)` through `#279(6)`) to `tests/js/copy_secret.test.mjs` (bringing the suite from 24 to 30 tests) and updated `tests/test_copy_secret.py` to assert `pass >= 30`.

Commands to run during review (not executed in this session per the AGY file-tools-only contract and command restrictions):
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings tests/test_copy_secret.py`
- `node --experimental-websocket --test tests/js/copy_secret.test.mjs`

## Issues / Blockers

- None.

## Blockers

- None.

## Notes for Reviewer

- `tests/js/copy_secret.test.mjs` now passes `COPY_SECRET_TEST: '1'` in `run()`'s default environment alongside `INFISICAL_API_URL: inf.url`. Any external test harness invoking `copy_secret.mjs` with `INFISICAL_API_URL` must also set `COPY_SECRET_TEST=1`.
- In `--find` mode, secrets with `secretValueHidden === true` still have their `<Project>/<env>[/<path>]/<NAME>` reference printed to stdout and counted in `scanned: … match`, as `--find` lists matching names, but their values are never compared or included in `value group <n>:` lines, and `values identical across matches` is reported as `no`.

## Not checked / risk

- Shell test execution (`pytest` / `node --test`) was not run directly because the AGY Remote Worker Contract specifies: *"For AGY, use file tools only; leave shell validation to the review process"*, and `node` is outside the shell command allowlist in `TASK.md`. Please run `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings tests/test_copy_secret.py` during review.

## Skill learning

- (none)
