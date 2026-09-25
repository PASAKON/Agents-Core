# Brief: Infisical — create the `setup` client secret and save it without anyone seeing it

Owner: CTO cto-885ae930 · Plan: `docs/design/secrets-infisical/PLAN.md` §6 phase 1 (CEO approved
2026-09-25). Machine: **Contabo** (you run here).

## The job (one sentence)
In the Infisical web app, make sure org identity `setup` exists (org role **Admin**, auth method
**Universal Auth**), create one client secret for it, and get its Client ID + Client Secret into
`/etc/infisical/setup.env` by piping them into
`python3 /opt/MoonieXHQ/Agents/Core/tools/infisical_setup.py save setup --stdin` — **the secret
value never appears on screen in a screenshot, in any output you read, or in your context.**

## What is already done
- The CEO has an Infisical Cloud account (org `MoonieX`, US region, app.infisical.com).
- A Browser Home is running for you: CDP **http://127.0.0.1:9281**, profile id `infisical`
  (`node scripts/relay-home.mjs url infisical` in `/opt/MoonieXHQ/Projects/MoonieX/Console`).
  It shows `https://app.infisical.com/login`. The CEO logs in from his phone through the relay.
  **You do not log in.** Poll the tab URL (no screenshots) every 20 s, up to 20 min, until it
  leaves `/login` and any 2FA page. If 20 min pass, stop and report `relay-login: contabo:9281`.
- The CEO may already have created `setup` and even a secret. Reuse the identity; create a new
  secret regardless (the old one's value is unknown to us).

## Steps
1. Logged in → go to the org's Access Control → Identities (the left menu "Organization" /
   "Access Control" → tab "Identities"; the URL is typically
   `https://app.infisical.com/organization/access-management?selectedTab=identities` or
   `/organizations/<orgId>/access-management` — read it from the page, do not guess twice).
2. If `setup` is missing: Create Identity → name `setup`, role **Admin**.
3. Open `setup`. If there is no Universal Auth method: add it with the defaults.
4. Note the **Client ID** (not a secret; you may read it).
5. Open the create-client-secret form: description `setup-2026-09-25`, TTL `1209600`
   (14 days), max uses empty.
6. **Before clicking Create**, start a capture script over CDP that:
   - enables `Network`, waits for the response to
     `POST …/api/v1/auth/universal-auth/identities/<id>/client-secrets`,
   - reads its body with `Network.getResponseBody`, takes `clientSecret` from the JSON,
   - spawns `python3 /opt/MoonieXHQ/Agents/Core/tools/infisical_setup.py save setup --stdin`
     and writes `<clientId>\n<clientSecret>\n` to its stdin,
   - prints **only** the tool's own output (`saved /etc/infisical/setup.env (0600) · login OK …`)
     and never the body, the secret, or its length.
   The script may click Create itself. Save it as
   `scripts/infisical/capture_client_secret.mjs` (Node 22, global `WebSocket`; args: CDP URL,
   identity name, client id) so the Mac and winbox cutovers reuse it with zero model.
7. The Create dialog then shows the secret. **Close it (its close/Done button or Escape) before
   any screenshot.** Never press its copy button (clipboard), never select its text.
8. Stop as soon as the tool prints `login OK`.

## Do not
- create projects, environments or other identities (the CTO runs `apply` afterwards);
- revoke or delete anything; just count other client secrets on `setup` and list their
  descriptions in the report;
- put any value in REPORT.md, a commit, a log file or a message.

## Budgets
40 steps, 5 screenshots, none while a secret is visible.

## Report (REPORT.md, text only)
1. The click path you used, as a short numbered list of the menu/button names exactly as the page
   labels them (the CEO will use it next time).
2. The tool's output line.
3. Whether `setup` / Universal Auth existed before you; how many other client secrets `setup` has.
4. Skill learning (WRONG / MISSING / COSTLY / none), per the org format.
