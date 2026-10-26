# keyfetch · OpenRouter · Management key

First run: task-b1b251f0, 2026-10-13/14. One management key created by `scripts/browser/keyfetch_openrouter_mgmt.mjs`
(wraps `scripts/keyfetch/capture_key.mjs`), straight into Infisical, no model saw it. No value, last4 or
screenshot is recorded here.

## Where things are

| | |
|---|---|
| Key page | `https://openrouter.ai/settings/management-keys` (Settings → Management Keys; "provisioning key" is the old name) |
| Browser | Contabo Browser Home `openrouter`, CDP `http://127.0.0.1:9289`, the CEO logs in through the relay (`relay-login`) |
| Dialog | "New Key" → "Create a Management Key": `input[name=name]`, "Expiration" select, **Create** |
| Expiration options | 1 hour · 1 day · 7 days · 30 days · 90 days · 180 days · 1 year · No expiration (there is no free date) |
| Credit limit | none on this dialog (a management key cannot run inference) |

The page name carries the expiry (`…-exp2027-01-12`): pick **90 days** on 2026-10-13/14 so the page's own date
(Jan 11 22:xx GMT+1 = Jan 12 TH) agrees with the name.

## Flags that worked (wire mode)

```bash
INFISICAL_SETUP_PY=tools/infisical_setup.py PYTHON=python3 \
node scripts/keyfetch/capture_key.mjs http://127.0.0.1:9289 \
  --tab 'openrouter\.ai/settings/management-keys' \
  --project Agents-Core --env prod --path /spend-guard --as keyfetch-writer --new-only \
  --click '^create$' --match 'keys' \
  --field 'key|data.key|data.secret|secret|data.token|token|data.api_key|api_key=OPENROUTER_API_KEY_ADMIN' \
  --comment '<purpose>' --meta provider_name=<page name> --meta console_url=<key page> \
  --meta scope=management-keys-list-patch-credits --meta expires=2027-01-12 --meta owner=CTO
```

- Create answers HTTP 200 and the value is in the response under the first alternative of `--field`
  (the `a|b|c` form tries each path until one yields a string; added in this task).
- After Create, two dialogs stay open (the "key created" sheet). Escape closes them; the script presses it. Do not read them.
- The list shows a hint `sk-or-v1-xxx...yyy` (prefix + last 3). Compare the **last 3** to the last 3 of the
  stored `last4` in code (`/…ffb\b/.test(body)`), never print the row.
- The same replay, form included: `node scripts/browser/keyfetch_openrouter_mgmt.mjs http://127.0.0.1:9289 [--check]`.

## Verify without seeing the value

1. `python3 tools/infisical_setup.py last4 Agents-Core prod OPENROUTER_API_KEY_ADMIN --as contabo --path /spend-guard`.
2. Provider page: reload the page, text ends `1 management key`, the hint's last 3 characters equal the last 3 of the last4.
3. Side-effect-free proof under `infisical_setup.py run … -- python3 …`: `GET https://openrouter.ai/api/v1/credits` and
   `GET /api/v1/keys` with `Authorization: Bearer <key>`; print the HTTP status only (200 and 200 on 2026-10-14).

## Quirks

- Base UI select: `element.click()` does nothing. Use `Input.dispatchMouseEvent` at the element's centre (the replay script does).
- The Chrome "Sign in" intercept (`chrome://signin-dice-web-intercept…`) is listed as a page; ignore it, target by host.
- **`--new-only` did not check the Infisical folder.** The first run created a key, then `put` answered
  "Folder … not found" (the value was gone, the key orphaned). `/spend-guard` now exists and
  `infisical_setup._get_secret` raises on a missing folder, so `--new-only` stops before the click.
- Delete a stray key from its row's "Row actions" menu → Delete → Delete (used once, to remove that orphan).
