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
7. **HARD — a key that a scan or review finds is reported by place, never by value.** Write `path:line`, the
   key type and the scanner's rule id. Never quote the value, a prefix of it or its last4: a found key has no
   Infisical entry to compare against, so last4 proves nothing and only leaks more. Run the scanner with
   `--redact` (gitleaks) and never `cat` or `grep -o` the line. If the key is real, tag it `leaked` in
   Infisical and rotate it (new key at the provider → Infisical through this procedure → verify → revoke the
   old one). **Why hard:** irreversible, for the same reason as rule 1. It applies the CEO's secrets rule of
   2026-09-25/26 to scan hits (`CTO_Gate_MergeChecklist` Gate 2b). The 2026-10-10 scan of the held Contabo
   commits was reported at file level, and the classifier refused to read the value.

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
- 2026-10-02 [MISSING] §Steps.1 — the PLAN §4b lint accepts only _RO/_RW/_ADMIN as the ACCESS suffix; a scope word there is refused (`GMAIL_REFRESH_TOKEN_INSERT` → "must end with a KIND"). Put the scope in WHICH: `GMAIL_INSERT_REFRESH_TOKEN`. Check with `lint_name()` before writing code that reads the name · evidence: Core 71ecb8f3, Console aae193d · status: pending
- 2026-10-03 [MISSING] §Rules 4 — the per-task write identity needs a free Infisical slot, and Free has 5 counting the CEO's own user account. With contabo, mac, winbox and setup the org is full: `POST /api/v1/identities` answered HTTP 400 in join drill run 5. So the task identity can exist only once `setup` is deleted, and only while nothing else takes the fifth slot. ADR 0035 keeps it free: nodes get their token from the hub, with no `org-node` identity. Rule 4 does not say who mints the task identity once the admin `setup` is gone · evidence: RUN-20261003-1425-1343, Agents-Rules d9de2c1 (ADR 0035), task-edc8d76f · status: pending
- 2026-10-06 [MISSING] §Steps 3 — `capture_key.mjs` FIND reads visible text only (`innerText || textContent || value`), so an icon-only create button (PixelLab: `aria-label="Generate new API key"`) can be neither `--check`ed nor clicked (`--click '^$'` matched 4). Worked: `--wait` in wire mode plus an external click helper that refuses unless exactly one visible button carries that aria-label. Fix: let `label()` fall back to `aria-label`/`title` · evidence: task-ab26b241, docs/ops/keyfetch/pixellab.md · status: pending
- 2026-10-06 [MISSING] §Steps 3/4 — single-token providers (PixelLab: regenerate replaces the one account token) have no "dummy key you revoke at once"; one learning click with a listener that prints only method, path, status and key names/types costs nothing, since the real capture replaces it. Page mode on a page that already shows the current token would save the OLD token (the read loop stops at the first non-empty value): use wire mode, or a page mode that waits for the value to change · evidence: task-ab26b241 (`POST /generate-new-token` → `{code, token}`) · status: pending
- 2026-10-06 [MISSING] §Rules 1 — a provider page that shows the full key on every load (PixelLab `/account`) makes every page read a leak risk, including the relay screencast right after login (the CEO saw the signup token; it was replaced twice). Require a redacting structure scan (labels redacted, no `input.value`, token-shaped holders by CSS path) and move the tab off the key page afterwards · evidence: task-ab26b241 · status: pending
- 2026-10-06 [COSTLY] no owner — the worker wrote a redacting page scanner, a click-learning listener and an aria click helper from scratch; prevented by committing them as `scripts/keyfetch/scan_page.mjs` / `learn_click.mjs` (or `capture_key --scan` / `--learn`) · evidence: task-ab26b241 · status: pending
- 2026-10-12 [MISSING] §When to invoke — no path for COPYING a key that already sits in Infisical into a second project (PLAN §3: a copy carries `shared` + `also_in`). Built `scripts/infisical/copy_secret.mjs` (session borrowed from the Browser Home `infisical`, exactly one regex match across the source's real folder tree, target must be absent, never Org-Infra, prints MATCH/MISMATCH only). Its first `--dry` found Org-Infra/prod empty (env prod only, 7 folders, 0 names; control: the same listing sees MoonieX-Bedrock/prod's 1 name), so the brief's "the fal key sits in Org-Infra" had never been checked: a copy brief must quote a `--dry` match line for its source · evidence: task-5b2a7baa · status: pending
- 2026-10-12 [MISSING] §Steps 1 — the brief cannot say where an existing key sits until something has looked: twice a fal key was assumed to be in a project (Org-Infra, then "likely MoonieX-ClaudeFlow") and neither held it. `copy_secret.mjs --find '/FAL/i'` walks all 22 projects, 37 envs and 45 folders in one run, names only, and found the one key in MoonieX-ComfyRunpod/prod. Step 1 should run `--find` first and quote its stdout; copy on one match or `values identical: yes`, create a new key only on zero · evidence: task-eb8bcf81 · status: pending
- 2026-10-12 [MISSING] §Rules 4 — an Infisical identity whose client secret expired still holds a seat: `setup` (org admin, secret dead since 2026-10-10) kept the org at 5 of 5 identities (users count too), so the task identity this rule asks for could not be created and the keyfetch stopped at its own gate. Retiring `setup` means deleting the identity, not letting its secret lapse; `retire-setup` cannot do it once the secret is dead (it logs in as setup, 401) · evidence: task-494414fc (cancelled), Agents-Core issue #246 · status: pending
- 2026-10-12 [MISSING] §When to invoke — no sanctioned path to move one key between projects. A Mac CTO Write of a copy script was refused by the auto-mode classifier ("Credential Exploration"), and granting `contabo` Viewer on Org-Infra is an access-control change a model does not make; the CEO chose "copy the one key, send a DEV" and task-5b2a7baa builds `scripts/infisical/copy_secret.mjs` on the CEO's Browser Home session · evidence: task-5b2a7baa · status: pending
- 2026-10-14 [MISSING] §Steps — no Infisical writer identity existed: `setup`'s client secret is dead (HTTP 401) and `contabo` is a Viewer, so `put --as setup` cannot work as written. A KeyFetch into Agents-Core first needs the CEO's relay login to app.infisical.com, then `node scripts/infisical/bootstrap_setup_identity.mjs <cdp> --identity setup --ttl-days 1`. That makes three relay logins (Infisical plus the two providers) for one job · evidence: task-b1b251f0 (spend-guard keys, CEO Q-20261013-2026-f2ac), session cto-e2f1563f · status: pending
- 2026-10-14 [WRONG] §Steps 3/4 — wire mode makes the operator guess the response field, and a wrong guess loses the secret of a key that has already been minted. fal returns `key_id` + `key_secret`, so `--field key=…` exited 7 and left a key at fal with no stored secret; it had to be revoked. Extractors now take `a|b` alternatives and `a+b` joins with `:`. Read the shape from `docs/ops/keyfetch/<provider>.md` first · evidence: task-b1b251f0, e2c968a3 · status: pending
- 2026-10-14 [MISSING] §Steps 1/4 — the brief must name the Infisical folder, and the run must check it exists. `--new-only` treated a missing folder as a free path, so OpenRouter minted a key that `put` could not store (the key was then deleted). `_get_secret` now raises on "folder … not found" · evidence: task-b1b251f0, f1c00036 + tests/test_infisical_get_secret_folder.py · status: pending
- 2026-10-14 [MISSING] §Steps 5 — "last4 equals the provider's last four" cannot hold for fal or OpenRouter. fal's list shows only the Key ID, so match the part before `:`. OpenRouter's list shows the prefix + last 3, so match the last 3. Add a status-only authenticated call: 200 for the real key, 401 for a garbage one · evidence: task-b1b251f0, docs/ops/keyfetch/fal.md + openrouter.md · status: pending
- 2026-10-14 [MISSING] §Steps 2 — a stopped Browser Home can still hold the CEO's login (Infisical's did), so read its host and path before opening a relay request. That saved one of three logins · evidence: task-b1b251f0 · status: pending
- 2026-10-14 [COSTLY] §Steps 1 — before minting, probe the endpoint the key's consumer will call, with no key, from the consumer's machine. `api.fal.ai` answers a Vercel challenge (403, HTML) from Contabo's IP, which was found only after the key was stored. The spend guard then had to move to `rest.alpha.fal.ai/billing/user_balance` · evidence: task-b1b251f0, CTO keyless probe 2026-10-14 (403 text/html vs 401 application/json) · status: pending
- 2026-10-14 [MISSING] §Steps — second independent sighting of "no Infisical writer identity": `contabo` got HTTP 403 "You are not allowed to create on secret-folders" on project Org-Coo at 21:0x and 21:2x Z, after the CEO answered card Q-20261013-2053-bf0f that he would make contabo a Developer there himself. Until his change lands, a write fails even with his yes; check with one harmless call (folder list/create) before planning the rotation around it · evidence: cto-afe760fe COO gate rotation (first sighting cto-e2f1563f, task-b1b251f0) · status: pending
- 2026-10-14 [MISSING] §Steps — follow-up to the note above: the CEO set `contabo` as Developer on Org-Coo and MoonieX-SomPong (Q-20261014-0842-7aff, sha256 9007a39a…), so `put --as contabo` works there; other projects stay Viewer until he grants them. `tools/openrouter_mint_key.py` writes with `--put-as` (default contabo) since #303 6e6c229b · evidence: Q-20261014-0842-7aff, RUN-20261014-0851-4196 · status: pending
- 2026-10-14 [WRONG] §Steps — the follow-up note above ("the CEO set contabo as Developer…, so `put --as contabo` works") was false. perms still showed ["viewer"]; his UI change did not land three times (Q-…0842-7aff, Q-…0902-249c, Q-…0910-b0d8). Developer's slug is `member`, and a PATCH with "developer" answers 404 on every route. A worker's UI click was refused [Permission Grant]. What worked: `scripts/infisical/set_project_role.mjs --identity contabo --role developer --project … --go` on a red Run card. It borrows the CEO's signed-in Browser Home, changes viewer→member, and re-reads the row. M4 then ran clean · evidence: task-0bbb27f9, RUN-20261014-0954-e61a (404), RUN-20261014-1002-ca7c (member OK), RUN-20261014-1004-0c03 (M4 exit 0), #308 3edba82d, #311 601c22b1 · status: pending
