# BLOCKER task-494414fc
Infisical has no free identity seat (5 of 5), so the task identity keyfetch-bedrock cannot be created. The CEO must pick a route before any fal key is made.

## Summary
Step 1 of the brief stopped at its own gate: "If there is no free slot … STOP and report the options."
Infisical's plan endpoint returns `identityLimit: 5`. The org holds 4 identities (`contabo`, `mac`,
`winbox`, `setup`) plus 1 user (the CEO). Users count against the same cap (drill run 5,
2026-10-03, `tools/infisical_setup.py` IDENTITY_CAP). So I created nothing at Infisical and nothing
at fal.ai. No value exists, so none was seen.

## What I checked (read-only, 2026-10-12 ~03:00 TH = 2026-10-11 ~22:00 CEST)
- `setup` login: HTTP 401 "Invalid credentials". **The identity still exists, as org `admin`.** Only
  its 14-day client secret expired (minted 2026-09-26). "Retired 2026-10-10" means the secret died.
  The identity was never deleted, so it still holds a seat. `/etc/infisical/setup.env` (a dead
  credential, 0600) is still on Contabo.
- `contabo` (viewer) cannot count seats: listing identities and listing members both return HTTP
  403. The count therefore went through the CEO's Infisical session, which is still signed in on
  the Contabo Browser Home `infisical` (port 9281), so no relay login was needed. That was one
  token refresh inside the page. Only identity names, roles and a user count were printed.
- `GET /api/v1/organizations/<org>/plan` returned `identityLimit 5`. `memberLimit` is null.
- The 4 identities and their org roles: contabo no-access, mac no-access, setup admin,
  winbox no-access. Users: 1 (admin, active).
- MoonieX-Bedrock/prod has no FAL_API_KEY (`last4 --as contabo` answers "has no secret"). `contabo`
  can see the project.
- I started Browser Home `infisical` for the check and stopped it again (`relay-home.mjs quit`; the
  profile and its login are kept).

## Options for the CEO (recommendation first)
- **A (recommended): delete the dead `setup` identity.** This frees one seat (4 of 5 used).
  - It is an org admin whose secret has been dead since 2026-10-10. PLAN §6 already ends the
    migration with retire-setup.
  - `infisical_setup.py retire-setup` cannot do it, because it logs in as `setup` (401). The delete
    has to go through the CEO's session: either his one click (Organization → Access Control →
    Identities → setup → Delete), or the extended bootstrap script once he says yes. The dead
    `/etc/infisical/setup.env` goes too.
  - Then the brief runs as written: `keyfetch-bedrock` (org role no-access, `member` on
    MoonieX-Bedrock only, 1-day secret) → fal key → delete `keyfetch-bedrock`. Seats return to
    4 of 5, so every later KeyFetch task has room.
- **B: a 1-day client secret on `setup`, then `put --as setup`.** Nothing is deleted and no new
  identity is needed. But an org-admin credential sits on Contabo for a day, and the brief told me
  not to take that route on my own.
- **C: no identity at all.** `put` would write with the CEO's own Infisical browser session (the
  same session that would mint a task identity). The token stays in memory for seconds; nothing
  goes on disk and nothing needs cleaning up. Costs: a code change (put takes a bearer token from
  the page instead of a credential file) plus tests, and skill rule 4 changes. It writes the least
  to disk, but the write is done by an org-admin session.
- **D (not recommended): free the `mac` seat.** The Mac has no `/etc/infisical`, so that identity's
  credential is unused. But it is in PLAN §3 `MACHINES`, and `apply` expects it.
- **E (not recommended): a paid Infisical plan.** That is money, and the CEO's call.
- Ruled out by the brief: write access for `contabo`, and copying the Org-Infra fal value.

## What the next run needs (whichever option)
- Whatever the option, `bootstrap_setup_identity.mjs` cannot yet create a project-scoped identity.
  Today it creates only `setup` (org admin), or mints a secret for an identity that already
  exists. Under A it still needs flags for: org role no-access, ONE project as `member`, TTL ≤ 1
  day, a seat check before the POST, and a delete. Tests are needed too. I did not build this:
  the gate said STOP.
- No fal Browser Home exists on Contabo yet:
  `(cd /opt/MoonieXHQ/Projects/MoonieX/Console && node scripts/relay-home.mjs create fal --label "fal.ai (Bedrock key)" --url https://fal.ai/login)`,
  then `launch fal` and a `relay-request.mjs open --home fal …` for the CEO.
- fal key options, from fal's docs (`docs/research/2026-10-12-fal-api-key-options.md`):
  - Smallest scope: preset `API` plus **Allowed models** = `fal-ai/elevenlabs/sound-effects/v2`.
    The model list is fixed at creation, and the key is then stored as a custom policy.
  - Expiry can be set from 1 hour to 1 year.
  - No per-key spend cap appears in the docs. Confirm on the page.
  - The key is `key_id:key_secret`. The docs say the list shows aliases and dates, so the brief's
    step 4 (last4 compared against fal's list) may have nothing to compare against. Look at the
    page before creating the key, and plan another check if needed (for example the key_id part,
    masked in code).

## Files Changed
- docs/research/2026-10-12-fal-api-key-options.md: new. fal key presets, allowed models, expiry,
  no per-key spend cap in the docs (research gate, ADR 0028 §6).
- BLOCKER.md: this file.

## Commits
- 02c9d218 — research: fal.ai API key options (presets, allowed models, expiry, no per-key spend cap in docs)
- (this commit) — keyfetch: blocker, no free Infisical identity seat

## Tests
- ran: `node --test tests/keyfetch/keyfetch.test.mjs` (baseline, no script changed): 29 passed, 0 failed, 0 skipped
- ran: `.venv/bin/python -m pytest -q tests/test_keyfetch_capture.py tests/test_infisical_user_scope.py`: 16 passed, 0 failed
- dep audit: skipped. Neither pip-audit nor osv-scanner is installed, and no dependency changed.
- gate "presence check prints last4=<present>": not reached (no key).
- gate "no key-shaped string in report or commits": grep run before the push, see Notes.

## Findings
- severity: low
  title: the retired `setup` identity (org admin) still exists and still holds a seat; its dead credential file is still on disk
  location: Infisical org identities; Contabo /etc/infisical/setup.env
  recommendation: option A. Delete it through the CEO's session and remove the file.
- severity: low
  title: write commands still default to the dead `setup` identity
  location: scripts/keyfetch/keyfetch_lib.mjs:16 (`as: 'setup'`); tools/infisical_setup.py main() (`--as` default SETUP for put/last4/import-env)
  recommendation: make `--as` required for put/import-env, so a run names its writer identity
  (KeyFetch Field note 2026-10-01 b).

## Issues / Blockers
- BLOCKED: no free Infisical identity seat. The CEO picks A, B, C, D or E (above). Nothing was
  created, so there is nothing to revoke or clean up.

## Notes for Reviewer
- threat model touched: no. Nothing was created or changed at Infisical or fal.
- secrets reviewed: yes, presence only. No value, length or last4 was printed. Masked output used
  `sed` over 32+-char tokens.
- CVEs introduced/removed: none.
- Brief date vs box: the brief says 2026-10-12 (Thai). The Contabo clock is CEST (2026-10-11).
- I asked the CEO for no relay login: the Infisical session was alive, and a fal login would be
  wasted until the seat question is ruled.

## Skill learning
- MISSING [CTO_Procedure_KeyFetch §Rules 4] : rule 4 ("an identity minted for the task") cannot be followed while the org is full. Infisical Free has 5 seats, the CEO's user takes one, and contabo/mac/winbox/setup take the other four. A brief should give the seat count, or the skill should say "delete `setup` first" · evidence: task-494414fc, plan endpoint identityLimit 5, 4 identities + 1 user
- WRONG   [CTO_Procedure_KeyFetch §Rules 4] : "`setup` until it retires (2026-10-10)" reads as if `setup` disappears that day. Only its 14-day client secret expired; the org-admin identity still exists and holds a seat · evidence: task-494414fc (login 401 "Invalid credentials", identity listed as admin) · fix: "after 2026-10-10 `setup` cannot log in; delete it (CEO session) to free its seat"
- MISSING [CTO_Procedure_KeyFetch §Steps 5] : "must equal the last four characters the provider's list shows" assumes the list shows them. fal's docs say its list shows aliases and dates, and the key is `key_id:key_secret`. Look at the list before creating the key and decide how to verify · evidence: docs/research/2026-10-12-fal-api-key-options.md
- MISSING [no owner] : a seat check needs an org-level reader. `contabo` gets 403 on both identities and members, so the only zero-model counter is the CEO's browser session (`/api/v1/identities` + `/api/v2/organizations/<org>/memberships`, or `/api/v1/organizations/<org>/plan` for the limit) · evidence: task-494414fc
