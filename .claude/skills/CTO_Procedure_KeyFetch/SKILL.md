---
name: CTO_Procedure_KeyFetch
kind: procedure
description: "PROCEDURE — A worker creates a new API key and pipes it straight into Infisical; the CEO only logs in via the relay; no model ever sees the value. Trigger on /CTO_Procedure_KeyFetch and on \"worker ไปเอา KEY\", \"เอา key จาก provider\", \"สร้าง API key ใหม่\", \"fetch a new API key\", \"rotate a key\". Not for the login (relay-login) or Org-Infra (CEO only)."
owner: CTO
created_by: agent
author: {role: cto, date: "2026-09-28"}
audience: [cxo, browser_operator, developer]
improved_by: []
aka: []
---

# A new API key, fetched by a worker, never seen by a model

Input: provider, Infisical project + env, variable name, provider-page name, scope, expiry, metadata (the
C-level's brief) · Output: the secret in Infisical with PLAN §4c metadata, and one report line
`created <project>/<env> <NAME> · last4=…` · Tool: `scripts/keyfetch/capture_key.mjs` →
`tools/infisical_setup.py put` (the value travels on stdin only).

## What it does

The CEO logs in on his phone through the relay; that browser's session cookie is the only credential in play.
A zero-model script attaches to that browser over CDP, clicks the provider's Create button (or waits for a
person to), takes the new key off the wire (the create response) or off the page (the element that shows it),
pipes it into `infisical_setup.py put`, presses Escape on the dialog, and prints only name · last4 · expiry.
The operator's context holds selectors and status lines, never the value. Proven 2026-09-26 on Infisical's own
client secret with the ancestor script `scripts/infisical/capture_client_secret.mjs` (cto-885ae930).

## When to invoke / when not

- Invoke for a new key, a rotation or an extra scope on any provider with a web page. A C-level writes the
  brief; a `browser_operator` runs it (a `developer` when the provider mints keys by API and no browser is
  needed — then it is a plain script ending in `put`).
- Not for the login itself (`relay-login` owns it), not for Org-Infra values (PLAN §3b: the CEO enters them;
  both the script and `put` refuse that project), and not for a value someone pasted to you — that is already a
  leak: tag it `leaked` in Infisical and rotate it (`ALL_Protocol_RunInbox` explains why a card refuses it).

## Steps (numbered; each with the stop condition)

1. **C-level: the brief.** The deep link to the provider's key page; Infisical project + env; the variable name
   per PLAN §4b (`<PROVIDER>_[<WHICH>_]<KIND>[_<ACCESS>]`); the provider-page name per §4d
   (`<brand>-<project>-<env>-<access>-exp<YYYY-MM-DD>`, ≤40 chars); scope, expiry, spend cap; the §4c metadata
   (purpose, provider_name, console_url, scope, expires, owner). Stop if any is missing: `put` refuses a new
   secret without them.
2. **Login through the relay** (`relay-login`): a Browser Home for that account; the CDP URL is what
   `relay-home.mjs launch` printed; the CEO taps the pill. Stop until the login has landed. Never type a
   password, a code or a 2FA answer yourself.
3. **Learn the page before any key exists.** Open the key page in that browser, fill the provider-page name,
   scope and expiry, then run `capture_key.mjs … --check`: it must report exactly one enabled button matching
   `--click`. If the provider shows the key only on screen, find that element (`--dom`) on a dummy key that you
   revoke at once. Stop if the button or the element cannot be found; do not create the real key by hand.
4. **Create and capture, zero model.** Wire mode: `--match <regex of the create request URL> --field
   <json.path>`; page mode: `--dom <css selector>`. The script clicks, captures, hands the value to `put`,
   presses Escape. Exit ≠ 0 means nothing was saved: read the status line, fix, rerun. Exit 7 after a 2xx means
   the key exists at the provider but not in Infisical: revoke it on the page, then rerun.
5. **Verify without seeing it.** `python3 tools/infisical_setup.py last4 <project> <env> <NAME>` must equal the
   last four characters the provider's list shows for the new key. Mismatch = revoke + rerun.
6. **Report and close out.** One line per key (name · last4 · expires · project/env); on a rotation, one
   registry line (`docs/design/secrets-infisical/PLAN.md` §3b: name · action · who · why · old-last4 →
   new-last4); revoke the old key at the provider only after its consumer restarted green.

## Verify (the command, and what "done" looks like)

```
python3 tools/infisical_setup.py last4 MoonieX-LineAutomation prod LINE_CHANNEL_ACCESS_TOKEN
MoonieX-LineAutomation/prod LINE_CHANNEL_ACCESS_TOKEN · last4=k9Qw     ← equals the provider page
```

Done also means: the task report holds no value, no length, no screenshot of the key dialog, and
`docs/ops/keyfetch/<provider>.md` holds the flags that worked.

## Rules

1. **HARD — a model never holds the value: no screenshot, DOM read, tool output or log once the key exists.**
   **Why hard:** irreversible — a value in a transcript or a screenshot on disk is leaked for good and forces a
   rotation (seven keys are on that list from chat pastes, PLAN §1). Explore on a dummy key; create only by
   script.
2. **HARD — the value enters Infisical only through `put --stdin`**: never an argument, a file a model reads, a
   Run Inbox card or chat. **Why hard:** argv sits in the process list and in the transcript; the worker sandbox
   classifier refuses credential-shaped commands anyway (measured 2026-09-18, GH #156).
3. **HARD — Org-Infra keys are the CEO's to enter** (PLAN §3b rule 1); the script and `put` refuse the project.
   **Why hard:** scope of authorisation — the CEO drew that line on 2026-09-25.
4. The write identity is time-boxed: `setup` until it retires (2026-10-10); afterwards an identity minted for
   the task with write on ONE project and deleted after (`--as <identity>`); machine identities stay read-only.
5. Least privilege at the provider: minimal scope, an expiry (default one year), a spend cap when offered. The
   page name carries all three, so a human reading the provider's key list knows what each key is (PLAN §4d).
6. The first run on a provider is the expensive one. Save the working flags as
   `docs/ops/keyfetch/<provider>.md` (deep link, --tab, --click, --match + --field or --dom, quirks); the next
   key is a replay with no exploration — `BROWSER_OPERATOR_Protocol_Playbook`: every repeatable flow leaves a
   replay script.

## Output format (the operator's report)

```
keyfetch · fal.ai · MoonieX-ClaudeFlow/prod FAL_API_KEY_RW
created MoonieX-ClaudeFlow/prod FAL_API_KEY_RW · last4=Qw9k · expires=2027-09-28 · owner=CTO
provider page: mx-claudeflow-prod-rw-exp2027-09-28 · last4 on page: Qw9k · MATCH
flags saved: docs/ops/keyfetch/fal.md · old key: revoke after the consumer restarts green
```

## Worked example (2026-09-26, the ancestor run)

Infisical identity `setup`, client secret. The CEO logged in on his phone; the script attached to that browser
(`http://127.0.0.1:9223`), clicked Create, read `clientSecret` from the `POST …/client-secrets` response in
memory, pressed Escape, and piped `<client-id>\n<secret>` into `infisical_setup.py save setup --stdin`. Stdout
was three status lines and `login OK`; the file landed as `/etc/infisical/setup.env` (0600). No person and no
model saw the value.

## Failure modes seen (dated)

- 2026-09-26 — Infisical's "copy your secret" dialog can stay open after creation; the script presses Escape
  and reports `dialogs still open: n` when it did not close. Close it without reading it.
- 2026-09-28 — a tab that is not logged in (`app.infisical.com/login`) reports `buttons=0` and `--check` exits 1:
  the relay login has not landed, go back to step 2.
- 2026-09-18 — a worker told to type a pasted code hit the sandbox classifier twice (`Credential Leakage`) and
  two single-use codes expired (task-13bfcd4d): never route a value through a worker's keyboard.

## Field notes

- 2026-09-28 [MISSING] §When to invoke / when not — no path for a secret that has no provider page (a random key we generate ourselves, e.g. an AES key ring). Step 5's last-4 check against the provider cannot apply. The design proposed a zero-model Run Inbox card (`openssl rand` → `infisical_setup.py put --stdin`) whose output shows only the name and kid · evidence: task-f50d0c4c §9 (`CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET`), docs/briefs/chatudo-o7b-security-design.md · status: pending
- 2026-10-01 [MISSING] §When to invoke — the key-ring case from the 2026-09-28 note is now built: `node -e randomBytes(32).base64 | node scripts/chatudo/keyring-add.js --emit | infisical_setup.py put MoonieX-ClaudeFlow prod CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET --path /chatudo --stdin` (ClaudeFlow `docs/chatudo/bring-up.md` §(a)). Two gaps in the generic mint template: it has no transform step (the ring is `kid=base64[,kid=…]`, not the raw key), and a NEW secret's `put` refuses without all 5 metas `provider_name console_url scope expires owner` (`provider_name=self console_url=n/a` for a self-made key) · evidence: task-256542ef worker Skill learning, ClaudeFlow e983665 · status: pending
- 2026-10-01 [MISSING] §Steps 1/4 — two traps on the first Tailscale run. (a) The provider's create returned TWO values (OAuth client id + secret) from one dialog, but capture_key took one `--name` and no `--path`; the worker added repeatable field=VAR pairs, `--path` and `--new-only` (both-or-nothing puts). (b) `put --as contabo` is refused on Agents-Core (that identity is a viewer); the puts needed `--as setup`, which retires 2026-10-10, so the brief must name a writer identity. Also: the Tailscale admin now lives on host console.tailscale.com, not login.tailscale.com, so `--tab` must match that host · evidence: task-3b9ae9d0, merged 23624f5f · status: pending
- 2026-10-01 [MISSING] §Rules 1 — while comparing last4, the worker printed the full OAuth client ID from the provider's credential list into its transcript (the secret never). A brief must say "compare last4 only, mask the list row in code" for IDs too, since the ID is stored as a secret · evidence: task-3b9ae9d0 report · status: pending
