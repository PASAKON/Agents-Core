# keyfetch · fal.ai · BILLING-preset key

First run: task-b1b251f0, 2026-10-13/14. One key created by `scripts/browser/keyfetch_fal_billing.mjs`
(wraps `scripts/keyfetch/capture_key.mjs`), straight into Infisical, no model saw the secret. No value or last4 recorded.

## Where things are

| | |
|---|---|
| Key page | `https://fal.ai/dashboard/keys` (Settings → Developer → API Keys) |
| Browser | Contabo Browser Home `fal`, CDP `http://127.0.0.1:9290`, the CEO logs in through the relay |
| Dialog | "Add key" → "Create API key": Name (first `<input>`), Expiration select, Description, **Presets**, **Create preset key** |
| Presets | API · Deploy · Read-only · **Billing** (8 permissions: read-only usage, invoices, FOCUS reports) · Compute · Serverless · Full access · Custom |
| Expiration options | 1 hour · 1 day · 7 days · 30 days · 60 days · 90 days · 180 days · **1 year** · No expiration (1 year is the longest) |

Pick **1 year** on 2026-10-14 for `…-exp2027-10-14`. The preset is a `button[role=radio]` (value `BILLING`) whose
`<label>` reads "Billing 8 permissions …"; click the label with a real mouse event and read `aria-checked`.

## Flags that worked (wire mode, two fields joined)

```bash
INFISICAL_SETUP_PY=tools/infisical_setup.py PYTHON=python3 \
node scripts/keyfetch/capture_key.mjs http://127.0.0.1:9290 \
  --tab 'fal\.ai/dashboard/keys' --project Agents-Core --env prod --path /spend-guard --as setup --new-only \
  --click '^create preset key' --match '/keys' --field 'key_id+key_secret=FAL_BILLING_API_KEY_RO' \
  --comment '<purpose>' --meta provider_name=<page name> --meta console_url=https://fal.ai/dashboard/keys \
  --meta scope=BILLING-preset --meta expires=2027-10-14 --meta owner=CTO
```

- Create answers **HTTP 201** with `{key_id, key_secret}` (two strings, top level). fal's credential is
  `key_id:key_secret` (the `Authorization: Key <id>:<secret>` form), so the `a+b` extractor joins them with a colon.
- After Create the "key created" dialog stays open and **Escape does not close it**: click its **Done** button
  (a real mouse event; never read the dialog). The page then lists the key.
- The replay incl. form: `node scripts/browser/keyfetch_fal_billing.mjs http://127.0.0.1:9290 [--check]`.

## Verify without seeing the value

- The list shows the Key ID only; the secret is never shown again, so **last4 cannot be matched to the page**.
  Compare the Key ID instead: the part before `:` in the stored value must appear in the list row (strip whitespace,
  the id wraps across two lines), checked in code and printed as a boolean.
- Authentication proof: `GET https://rest.alpha.fal.ai/billing/user_balance` with `Authorization: Key <value>` answers
  200 for the real key and 401 for a garbage key (status only).
- **`api.fal.ai` and `fal.ai` answer HTTP 403 `challenge` ("This request requires a challenge to be completed",
  server Vercel) from Contabo's IP, even with no key.** `https://api.fal.ai/v1/account/billing?expand=credits`
  (what `tools/spend_guard.py` reads) therefore could not be tested from this box. `rest.alpha.fal.ai` is not challenged.

## Quirks

- Revoke from the row's Actions menu → "Revoke key" → confirm; it is an `alertdialog` (not `dialog`), so a
  `[role=dialog]` selector misses it. Used to remove the first run's unsaved key.
- The first run guessed `--field key=…`; the shape line printed `key_id:string key_secret:string` and exit 7 left a key
  at fal with its secret lost. A guess is a free key only if you can revoke it: use the shape from this file.
- A fresh account shows `Credits: $0.00`; the key still creates and authenticates.
