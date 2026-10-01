# keyfetch · Tailscale · OAuth client (trust credential)

First run: task-3b9ae9d0, 2026-10-01. Result: one client created, both values (client id, client secret)
captured by `scripts/keyfetch/capture_key.mjs` straight into Infisical, no model saw either. No value, last4
or screenshot of the key dialog is recorded here.

## Where things are

| | |
|---|---|
| Admin host | `console.tailscale.com` (login.tailscale.com redirects there after sign-in; match `--tab` on `console\.tailscale\.com`) |
| Key page | `https://console.tailscale.com/admin/settings/trust-credentials` (the old `/admin/settings/oauth` redirects to it) |
| New client wizard | `…/admin/settings/trust-credentials/add` — step 1 "Settings" (type + Description), step 2 "Scopes" |
| Browser | Contabo Browser Home `tailscale`, CDP `http://127.0.0.1:9284`, CEO logs in through the relay (`relay-login`) |
| ACL editor | `…/admin/acls/file` — CodeMirror 5 |

## Before the client: the tag must be owned

An OAuth client can only be scoped to a tag the tailnet policy already owns. Add the owner to the policy
file first, keep every other line byte-identical, save, re-read:

```
"tagOwners": {
	"tag:org-node": ["autogroup:admin"],
},
```

The ACL page is a CodeMirror 5 editor. Setting its `<textarea>` does nothing (Save stays disabled); edit
through the instance: `document.querySelector('.CodeMirror').CodeMirror.replaceRange(text, {line, ch})`.
That enables Save. Re-read with `cm.getValue()` and compare line count and the untouched lines.

## The create request (wire mode)

`POST /public/tailnet/-/keys/` with `{keyType:"client", description, scopes:[ids], tags:[…]}`. Answer is
`{data:{id, key, …}}`: `data.id` is the client id, `data.key` the client secret (`tskey-client-…`). The admin JS
shows the dialog from the same object, so the wire and the page agree. The scope ids behind the two checkboxes
are `devices:core` (Devices → Core → Write) and `auth_keys` (Keys → Auth Keys → Write); each Write implies and
locks its Read box.

## Filling the wizard (before the script runs)

The script only clicks Generate; the form is filled first. Four things cost time, all on this SPA:

1. **Wait for the mount.** Setting an input right after `Page.navigate` throws "Uncaught" (the SPA has not
   mounted). Poll for the input, then set it.
2. **Description** is `input:not([type=radio]):not([type=checkbox])`, React-controlled: call the native
   `HTMLInputElement.prototype.value` setter, then dispatch an `input` event (bubbles). It survives Continue and
   Back. `input[type=text]` found nothing on step 1.
3. **Scopes need a real mouse press.** `checkbox.click()` and `label.click()` from `Runtime.evaluate` leave the
   Write boxes unchecked in React state (they flip, then revert). Expand the "Devices" and "Keys" accordions
   (30 checkboxes appear), scroll the Write label for "Core" / "Auth Keys" into view, and send
   `Input.dispatchMouseEvent` mouseMoved + mousePressed + mouseReleased at the **label's centre** (the 16 px box
   itself gets a bare DIV click and does nothing). Both Reads then show checked and locked.
4. **Tags**: "Tags (required for write scope)" appears once a Write scope is ticked, and "Generate credential"
   stays disabled until one tag is chosen. Real-click the first "Add tags" input, then real-click the
   `tag:org-node` suggestion. Nothing else is selectable until the tag is owned (see above).

Description for this client: `mooniex-orgjoin-prod-keys-exp2027-10-01` (PLAN §4d name; the page has no expiry
field for OAuth clients, the expiry lives in the name and in the Infisical metadata).

## Check, then capture

```bash
# --check: exactly one enabled "Generate credential" button, nothing created
node scripts/keyfetch/capture_key.mjs http://127.0.0.1:9284 --tab 'console\.tailscale\.com' \
  --project Agents-Core --env prod --path /org-join --click '^generate credential' --check

# the capture (Contabo, from the repo that holds this script)
INFISICAL_SETUP_PY=tools/infisical_setup.py PYTHON=.venv/bin/python \
node scripts/keyfetch/capture_key.mjs http://127.0.0.1:9284 \
  --tab 'console\.tailscale\.com' \
  --project Agents-Core --env prod --path /org-join --as setup \
  --click '^generate credential' \
  --match '/tailnet/-/keys/?$' \
  --field 'data.id=TAILSCALE_OAUTH_CLIENT_ID' \
  --field 'data.key=TAILSCALE_OAUTH_CLIENT_SECRET' \
  --new-only \
  --comment '<purpose, one sentence>' \
  --meta 'provider_name=<page name>' \
  --meta 'console_url=https://login.tailscale.com/admin/settings/oauth' \
  --meta 'scope=auth_keys:write+devices:core:write tag:org-node' \
  --meta 'expires=<YYYY-MM-DD>' --meta 'owner=ceo'
```

- `--new-only` refuses before the click when either secret already exists, so a Run Inbox card run or an
  earlier attempt is never overwritten.
- `--as setup`: the machine identities (`contabo`, `mac`, `winbox`) are read-only viewers on Agents-Core, so
  `put` needs the write identity. It retires 2026-10-10; after that mint a one-project write identity.
- `--match '/tailnet/-/keys/?$'` and the default `--method POST` leave the list `GET …/keys?all=true…` alone.
- Output of the real run: `provider answered HTTP 200; … present · … present`, `dialogs still open: 0`,
  two `created …` lines from `put`, `saved 2/2`, exit 0.
- Exit 7 with a "response shape (key names and types only)" line means the field paths are wrong: the client
  exists at Tailscale with its secret unsaved. Revoke it on the list page, fix the paths, rerun.
- After the run, press Escape once (`Input.dispatchKeyEvent`, key `Escape`): the dialog closes and the SPA
  returns to the list (`?highlightedClient=<id>`).

## Verify without seeing the value

1. `python3 tools/infisical_setup.py last4 Agents-Core prod <NAME> --path /org-join --as setup` for both names.
2. The credential list row shows the client id in full: compare its **last four characters** only (do not
   print the row). The secret is never shown again, so only its Infisical metadata can be checked.
3. Zero side-effect proof, token exchange only (`POST /api/v2/oauth/token`, grant `client_credentials`) through
   `lib.tailscale_api.TailscaleClient.access_token()` under
   `infisical_setup.py run Agents-Core prod --as contabo --path /org-join -- python3 <script>`; print the HTTP
   status and nothing else (200 on 2026-10-01). Do not mint an auth key and do not delete a device to "prove" it.

## Quirks

- A Chrome "Sign in" intercept tab (`chrome://signin-dice-web-intercept…`) reappears after a login: ignore it,
  target the admin tab by host.
- The page heading reads "Your web browser is unsupported." in the headless Browser Home; the wizard works.
- Revoke / delete a client from its row's action menu on the list page (not exercised in this run).
