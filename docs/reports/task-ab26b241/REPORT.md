# REPORT task-ab26b241

**Leak check first: no value showed in my context.** No screenshot was taken. Every page scan redacted
token-shaped strings in code and never read an input's value. The network learning step printed only key names
and types. Only last4 values were printed: from `put`, from `last4`, and computed inside the page.
Two things outside my context still need saying:
- (a) The relay screencast showed the CEO the token PixelLab auto-creates at signup, because the login landed on
  `/account`. That token has since been replaced twice.
- (b) My learning click minted one token that nobody captured. The real capture replaced it seconds later.

```
keyfetch · pixellab · MoonieX-Bedrock/prod PIXELLAB_API_KEY
created MoonieX-Bedrock/prod PIXELLAB_API_KEY · last4=b25a · expires=2027-10-06 · owner=CTO
provider page: none (no name field) · last4 on page: b25a · MATCH
smoke: GET https://api.pixellab.ai/v2/balance HTTP 200 · credits=$0.00 · status=trial · generations 40/40 left
flags saved: docs/ops/keyfetch/pixellab.md
```

## Summary
I created the Infisical project `MoonieX-Bedrock` (dev and prod; contabo and mac as viewers). Then I generated
a new PixelLab API token by script and captured it off the wire (`POST api.pixellab.ai/generate-new-token` →
`token`). It went straight into `put --stdin --as setup --new-only` with the full §4c metadata. The last4
matches the page, and the zero-cost balance call returns HTTP 200. The Browser Home `pixellab` (Contabo:9288) is
left running and logged in, on `www.pixellab.ai/` (not the key page).

- **Account:** PixelLab free trial (page shows "Trial Active", API shows `status=trial`, `plan=null`).
  Generations: 0/40 used (40 fast ones). Credits: $0.00.
- **Spend limit:** none on the page. The only money control is "Buy Credits"; nothing was bought.
- **Commercial use:** https://www.pixellab.ai/termsofservice (updated 2025-11-23).
  - §1.3/§3.3: you own the copyright to outputs, and commercial and non-commercial use is allowed without
    permission, except training other models.
  - §2.2: the API is "designed for vibe coding and in-game live asset creation". Building your own service or
    reselling means contacting them first.
  - §4: the Open RAIL-M licence applies.
  - The account page's plan table lists "Use generated images commercially" for the free trial too.

## Files Changed
- `docs/design/secrets-infisical/PLAN.md`: one §3 row, `| MoonieX-Bedrock | read | read | | |`.
- `docs/ops/keyfetch/pixellab.md`: new replay file: deep link, `--tab`, how the click works (aria-label), `--match` +
  `--field`, quirks, verification, close-out. No value and no last4.

## Commits
- `83f173c5`: security: PLAN §3 row for MoonieX-Bedrock (contabo + mac read), project created in Infisical
- `00df9357`: security: keyfetch flags for PixelLab (wire capture of generate-new-token, aria-label click), task-ab26b241

## Tests
- ran: `.venv/bin/python -m pytest scripts/test_infisical_setup.py tests/test_keyfetch_capture.py tests/test_infisical_user_scope.py`: 32 passed, 0 failed
- ran: `node --test tests/keyfetch/keyfetch.test.mjs`: 29 passed, 0 failed. My first attempt passed the directory
  (`node --test tests/keyfetch/`), which Node 22 cannot resolve; that "1 fail" came from my invocation, not the code.
- ran: `infisical_setup.py last4` against the page last4: MATCH. `infisical_setup.py run MoonieX-Bedrock prod --as contabo -- <balance script>`: HTTP 200.
- ran: a secret scan of my diff (token-shaped strings and the last4): nothing found.
- dependency audit: skipped. `pip-audit` and `osv-scanner` are not installed on Contabo, and this task changed no
  dependencies (docs only). Nothing was installed.
- passed: 61 · failed: 0 · skipped: 1 (dependency audit)

## Findings
- severity: medium
  title: The PixelLab account page shows the full API token, unmasked, on every load. A logged-in Browser Home therefore exposes it to any local CDP client.
  location: https://www.pixellab.ai/account (`p.chakra-text.css-1una8gt`, possibly `script#__NEXT_DATA__`); Contabo Browser Home `pixellab`, 127.0.0.1:9288
  recommendation: Keep the home off `/account` (done) and quit it when no PixelLab browser work is planned (`relay-home.mjs quit pixellab`; the CEO's phone can relaunch it). Any agent that opens `/account` must use the redacting scan described in the keyfetch doc.
- severity: low
  title: The token is account-wide, with no scope, no expiry and no spend limit at the provider.
  location: PixelLab account (Infisical meta `wide=yes`, `why_wide`, `expires=2027-10-06` = our rotate-by date)
  recommendation: Exposure is $0 while credits stay at $0 (free-trial quota only). Leave auto top-up off, and record a `spend_cap` if credits are ever bought.
- severity: low
  title: `capture_key.mjs` FIND matches visible text only, so it cannot click or `--check` icon-only buttons.
  location: scripts/keyfetch/capture_key.mjs:93 (`label = innerText || textContent || value`)
  recommendation: Fall back to `aria-label` / `title` in `label()`. That would make `--check` pass on PixelLab and remove the external click helper from the doc.
- severity: low
  title: `tools/infisical_setup.py` PROJECTS and MACHINES do not list `MoonieX-Bedrock` (nor the existing `MoonieX-SomPong` and `Org-Coo`), so `status` hides it and `apply` would not keep its memberships in step.
  location: tools/infisical_setup.py:91 (PROJECTS), :124 (MACHINES)
  recommendation: Add the row in code in a separate change. The brief limited my commits to two files, so I did not.

## Issues / Blockers
- None blocking.
- **Registry Changelog (IRON §34 rule 2): I cannot write the wiki.** The CTO should append to `mooniex:playbooks/api-key-registry.md`:
  `2026-10-06 · PIXELLAB_API_KEY (Infisical MoonieX-Bedrock/prod) · create · security_engineer task-ab26b241 for cto-f39cb080 · CEO order (Bedrock texture lane, PixelLab drafts) · — → b25a`
- **Infisical tag `wide`:** `put` has no tag option, so `wide=yes` and `why_wide=PixelLab offers one account token` are stored as metadata. Add the tag in the UI if a real tag is wanted.
- **Metadata dates:** `updated=2026-10-05` uses Contabo's clock (CEST date), while `created=2026-10-06 cto-f39cb080` is the Thai date from the brief.

## Notes for Reviewer
- threat model touched: no code change. A new secret store (`MoonieX-Bedrock`) and a new logged-in browser session on Contabo (see the medium finding).
- secrets reviewed: yes. Nothing printed but last4. My diff was scanned clean.
- CVEs introduced/removed: none (no dependency change).
- **Project creation:** the `plan` run was clean apart from the known `Agents-Core: staging` line. I ran the tool's own `reconcile()` with
  Bedrock added in memory only, through a dry-run guard that refuses if any action names another project. Result:
  project, dev and prod environments, the CEO as project admin (reconcile adds this to every project), contabo
  viewer, mac viewer. The CEO admin membership goes slightly beyond the brief's "viewer memberships for mac and
  contabo", but every other project has it. No other project and no identity was touched, and Org-Infra was not touched.
- **The login wait:** detached shell rounds (`relay-request wait --timeout 1` plus the tab's host and path every 20 s). The model woke only at the end of each round, to re-arm and touch HEARTBEAT. The relay request was `rq-c36fac20` and closed as done by the CEO.
- **Mailbox:** the relay-login line went to `MAC CTO #f39cb080` through SendMessage (Remote Control). `lib.mailbox` only writes to boxes on its own host.
- SKILL-OVERRIDE: CTO_Procedure_KeyFetch :: step 3 "`--check` must report exactly one enabled button matching `--click`" :: I checked uniqueness with a CDP helper that clicks by `aria-label="Generate new API key"` and refuses unless exactly one visible button matches, and ran `capture_key.mjs --wait` in wire mode while that helper clicked :: capture_key's FIND reads `innerText` only, and PixelLab's button is an icon (`--click '^$'` matched 4), so `--check` cannot pass on this page. The value path was unchanged: wire → `put --stdin`, zero model.
- SKILL-OVERRIDE: CTO_Procedure_KeyFetch :: step 3 "find the element on a dummy key that you revoke at once" :: I learned the create request with one regenerate click and a listener that printed method, path, status and key names/types only; the real capture replaced that uncaptured token :: PixelLab has one account token and regenerate is the only create step, so a separate dummy key cannot exist.
- I did not use page mode (`--dom`): the element already shows the OLD token, so capture_key's read loop would have saved it before the new one painted.

## Skill learning
- MISSING [CTO_Procedure_KeyFetch §Steps 3] : capture_key's FIND matches visible text only, so an icon-only create button (`aria-label`) can be neither `--check`ed nor clicked. Workaround: `--wait` plus an external click by aria-label. Fix: let `label()` fall back to `aria-label`/`title` · evidence: task-ab26b241, docs/ops/keyfetch/pixellab.md §"The page"
- MISSING [CTO_Procedure_KeyFetch §Steps 3/4] : page mode on a page that already shows the current token captures the OLD token at once, because the READ loop stops at the first non-empty value. Single-token providers need wire mode, or a page mode that waits for the value to change (comparing in code) · evidence: task-ab26b241
- MISSING [CTO_Procedure_KeyFetch §Steps 3] : "a dummy key you revoke at once" does not exist for single-token providers. Regenerate is the create step, and each regenerate replaces the last token, so one learning click with a names/types-only listener costs nothing · evidence: task-ab26b241 (`POST /generate-new-token` → `{code, token}`)
- MISSING [CTO_Procedure_KeyFetch §Rules 1] : a provider that shows the full key on load (PixelLab `/account`) makes every page read a leak risk, the relay screencast after login included. The skill should require a redacting structure scan (labels redacted, no `input.value`, token-shaped holders by CSS path) and moving the tab off the key page afterwards · evidence: task-ab26b241
- MISSING [relay-login §0] : a Contabo worker owned by a Mac CTO cannot "letter" it through `lib.mailbox`, which is host-local. What worked was SendMessage to the ListAgents Remote Control name (`MAC CTO #f39cb080 (...)`) · evidence: task-ab26b241, msg 0707ce9e
- COSTLY  [no owner] : writing and testing a redacting page scanner, a click-learning listener and an aria click helper from scratch took the most time · evidence: task-ab26b241 scratchpad · prevented by: commit them as `scripts/keyfetch/scan_page.mjs` / `learn_click.mjs` (or `capture_key --scan` / `--learn`)
- MISSING [no owner] : `tools/infisical_setup.py` cannot create one project on its own. `apply` reconciles the whole hard-coded PROJECTS list, and `status` hides projects that are not in it (MoonieX-Bedrock, MoonieX-SomPong, Org-Coo). I used an in-memory reconcile wrapper with a dry-run guard · evidence: task-ab26b241, `83f173c5`
