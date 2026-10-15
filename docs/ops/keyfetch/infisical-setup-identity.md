# keyfetch · Infisical · the write identity `setup`

Task-b1b251f0, 2026-10-13. What the keyfetch runs need from Infisical, and what was learned minting it.

- The `contabo` identity is a viewer: `put --as contabo` is refused. `put --as setup` needs a live client secret.
- `setup`'s old secret was dead (HTTP 401). Mint a 1-day one through the CEO's logged-in Infisical Browser Home:
  `node scripts/infisical/bootstrap_setup_identity.mjs http://127.0.0.1:9281 --identity setup --ttl-days 1`
  (borrows the session cookie with one in-page fetch, creates the secret over the API, pipes it into `infisical_setup.py save setup --stdin`).
- **The Browser Home can still hold the CEO's Infisical session** (the profile kept it): launch it, read the tab host+path
  (`/organizations/<id>/projects` = logged in) and run `--dry`. No new relay login was needed on 2026-10-13.
- `--revoke` (added): `… bootstrap_setup_identity.mjs <cdp> --identity setup --revoke` revokes every live client secret of the identity
  through the same session and prints counts only. Run it after the last put verifies. `/etc/infisical/setup.env` then
  holds a dead secret (HTTP 401), which is the normal resting state.
- **The folder must exist before the first `put`.** `put` does not create folders; `infisical_setup.py apply` creates the ones in
  `PROJECT_FOLDERS`. `/spend-guard` in Agents-Core prod was created with a one-off call (`Org.send POST /api/v2/folders`) because it
  is not in that table yet; add it there if `apply` should own it.
- Do not open `/etc/infisical/*.env`; the tools read them.
- 2026-10-15 (task-fb4b47df): on Contabo (Node 20.20) the script dies with `ReferenceError: WebSocket is not defined`; run it with `NODE_OPTIONS=--experimental-websocket`. Browser Home `infisical` was on :9281 and still signed in; dry, mint, 2 puts and revoke (1 of 1) all passed.
