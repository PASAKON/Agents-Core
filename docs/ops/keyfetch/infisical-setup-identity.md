# keyfetch · Infisical · write identity

## keyfetch-writer (from 2026-10-27)

CEO ruling Q-20261026-1118-4d3d: on Free, each repository's project is the wall.
`keyfetch-writer` replaces `setup` in the five-seat allowance (users count too).
It has org role `no-access` and project Developer (slug `member`) only on
Agents-Core, MoonieX-Bedrock and MoonieX-ClaudeFlow. Never Org-Infra or Org-Node.
The reviewed allowlist is `config/keyfetch-writer.yaml`; add projects by PR, then
have the CEO run the seat card again. Names must exist in the live org project list.

Only the CEO's Run card on Contabo runs the seat script through his signed-in
Infisical Browser Home, with the organization already selected. From the repo root,
the card runs the dry plan first, then the approved change:

```sh
NODE_OPTIONS=--experimental-websocket node scripts/infisical/keyfetch_writer_seat.mjs http://127.0.0.1:9281
NODE_OPTIONS=--experimental-websocket node scripts/infisical/keyfetch_writer_seat.mjs http://127.0.0.1:9281 --go
```

The dry plan reads only (apart from session refresh). The change revokes setup's
client secrets, deletes setup, creates the writer with no org access and attaches
Universal Auth without minting a secret. Existing project roles are printed and
left alone; an existing writer with another org role stops the run. Failed runs
can be retried. The CLI trusts the Run card's authorization; it does not verify
the card's provenance itself. CTO reviews the script before the CEO runs it.

Immediately before a KeyFetch run, mint a client secret (default and maximum one day):

```sh
NODE_OPTIONS=--experimental-websocket node scripts/infisical/bootstrap_setup_identity.mjs http://127.0.0.1:9281 --identity keyfetch-writer --ttl-days 1
```

Bootstrap never creates this identity; if absent, run the seat script first.
It pipes the pair directly to `save keyfetch-writer --stdin`. Save guards the
access-token TTL; client-secret expiry is enforced at mint time by bootstrap.
Use `put ... --as keyfetch-writer` (also the default). After the last put verifies,
revoke all its live client secrets, leaving only dead credentials at rest:

```sh
NODE_OPTIONS=--experimental-websocket node scripts/infisical/bootstrap_setup_identity.mjs http://127.0.0.1:9281 --identity keyfetch-writer --revoke
```

Org-Infra credentials are the CEO's to enter. The seat script creates neither
folders nor project secrets; needed folders must already exist.

## [SUPERSEDED 2026-10-27] setup

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
