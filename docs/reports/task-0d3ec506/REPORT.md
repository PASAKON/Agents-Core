# task-0d3ec506 · HQSecurity M1 · rules, IRON draft, KeyFetch guard

Security_engineer report for PH HQSecurity #0de446ff, order O-20261027-1347-4e62. No secret value appears in
any file, test or line of this report. The tests use only obviously fake strings.

## Summary

All three deliverables are on one branch, cut from origin/main:
- **A.** New RULES skill `ALL_Rules_Secrets`: 9 rules, all HARD, each with `Why hard:`.
- **B.** Draft IRON §65, with the §34 item 5 amendment that the CEO's free-plan ruling 4d3d needs, and a
  25-line Thai summary for the CEO.
- **C.** `capture_key.mjs` / `keyfetch_lib.mjs` refuse, with exit 64 and before anything is clicked, a planned
  key write that lacks:
  - a §4d `provider_name`: ≤40 characters, env equal to `--env`, a real calendar date;
  - `scope`;
  - `expires`: an ISO date equal to the name's exp, or `none-offered`;
  - `console_url`, `owner` or `--comment`.

  Org-Infra is refused in every spelling. KeyFetch tests: 63/63 pass (17 new).

## Files Changed

- `scripts/keyfetch/keyfetch_lib.mjs`: adds `checkKeyMeta`, `metaMap`, `BRANDS` and `NO_EXPIRY`.
  - `parseArgs` runs the gate whenever extractors are present, so a `--check` rehearsal is gated too and a
    bare `--check` is not. It also refuses a key whose expiry, or rotate-by date, is not after today.
  - `runPuts` runs the gate again before its first spawn.
  - The Org-Infra test is normalised (`org_infra`, `OrgInfra`, ` Org-Infra `).
- `scripts/keyfetch/capture_key.mjs`: header and usage text list the required metadata. When
  `expires=none-offered`, it prints a line saying so.
- `tests/keyfetch/keyfetch_meta_gate.test.mjs` (new): 14 unit tests for the gate.
- `tests/keyfetch/keyfetch.test.mjs`: the existing fixtures now carry valid metadata, plus 3 end-to-end tests
  through the fake CDP browser: missing scope, Org-Infra, none-offered.
- `docs/ops/keyfetch/pixellab.md`: the replay used `provider_name=none (no name field)`, which the gate refuses.
  It now uses `mx-bedrock-prod-rw-exp<rotate-by>` with `expires=none-offered`.
- `.claude/skills/ALL_Rules_Secrets/SKILL.md` (new): RULES kind, owner CTO, audience all. The description is
  317 characters and carries the brief's trigger words.
- `docs/org/SKILL-INDEX.md`: regenerated with `scripts/skill-curator.py index`.
- `docs/plans/hqsecurity-rules-draft/IRON-65.md` (new): the §65 text and the §34 item 5 amendment.
- `docs/plans/hqsecurity-rules-draft/CEO-summary-th.md` (new): 25 lines, 2 tables, no « ».
- `docs/reports/task-0d3ec506/REPORT.md`: this file.

## Commits

- `0dbf7325` security: KeyFetch metadata gate - refuse a key write without §4d name, scope, expires
- `6aa26744` skill(ALL_Rules_Secrets): new — one rule set for every credential — evidence O-20261027-1347-4e62
- `99cfd1ad` docs(hqsecurity): IRON §65 draft + one-page Thai summary for the CEO
- `77e88d00` skill(ALL_Rules_Secrets): rule 7 steps as bullets so the HARD block keeps its Why hard
- (this report's commit)

## Tests

- ran: `NODE_OPTIONS=--experimental-websocket node --test tests/keyfetch/` (Node 20.20.2 on Contabo)
  - before the change: 46 passed, 0 failed
  - after: 63 passed, 0 failed
- ran: pytest on the skill, index and inventory tests: `tests/test_thai_inventory.py`, `test_skill_rename.py`,
  `test_path_owners.py`, `test_worktree_keep_paths.py`, `scripts/test_skill_curator.py`, `test_skill_lint.py`,
  `test_skill_doctrine_lint.py`, `test_hook_skill_write_reminder.py`
  - 125 passed, 0 failed
  - the first run failed 1 (`test_real_corpus_reports_zero_defects`, my rule 7); fixed in 77e88d00
- ran: full `pytest` with a 25-minute bound. It stopped at the bound (exit 124) after 5,285 of 12,909 tests:
  5,187 passed, 54 skipped, 44 failed, spread over 12 files. None of the 12 files touches a file this branch
  changes.
  - rerun of those 12 files: 465 tests, 448 passed, 2 skipped, 15 failed. The other 29 (`test_skill_lint`
    and the `scripts/test_session_*` files among them) passed on the rerun, so they depend on run order.
  - 14 of the 15 (`test_email_ceo` 13, `test_coo_gate` 1) are refused because this process is a worker
    (`WORKER_TASK_ID` is set). With `env -u WORKER_TASK_ID`, both files pass 165/165.
  - the last one, `test_h3_runner_model_launch::test_script_org_tools_registry_verdict`, is refused by the
    ADR 0021 guard ("tests must not touch a real checkout's tasks.db"). This is a local-environment effect
    and has nothing to do with this branch.
  - the other 7,624 tests did not run locally; CI runs them.
- ran: `scripts/skill-lint.py check` → 35 findings, none in `ALL_Rules_Secrets`, all already on origin/main (the
  stale-index finding cleared after the index was regenerated)
- ran: `scripts/skill-doctrine-lint.py check` → clean
- ran: `gitleaks git --no-banner --redact --log-opts=origin/main..HEAD` → 4 commits, no leaks
- ran: the two existing wrappers' argument lists (`scripts/browser/keyfetch_fal_billing.mjs`,
  `keyfetch_openrouter_mgmt.mjs`) through `parseArgs` → both PASS the gate unchanged
- dependency audit: none run. The change adds no dependency (Node stdlib only), and the repo has no
  `package.json` for `scripts/keyfetch`.

## Findings

- severity: high · title: GitHub secret scanning and push protection are OFF on both public repos ·
  location: repo settings of PASAKON/Agents-Core and PASAKON/Agents-Rules (`gh api repos/PASAKON/<repo>`
  `.security_and_analysis`: `secret_scanning`, `secret_scanning_push_protection` = `disabled`, read
  2026-10-27) · recommendation: turn both on (free for public repos). This is a repo-settings change for the
  CTO/CEO; I did not change it.
- severity: medium · title: IRON §34 item 5 still says provider keys go "in every project including Org-Infra"
  and that every project's keys move into Org-Infra · location: Agents-Rules `IRON-RULES.md` §34 item 5 ·
  recommendation: amend in the same PR as §65 (text in IRON-65.md). Q-20261026-1118-4d3d replaced it.
- severity: medium · title: the session hook does not block reads of `/etc/infisical/*` (each machine
  identity's credential) · location: `scripts/hook-secret-env-guard.py` `check_bash` and the Read/Grep path
  check · recommendation: add the path to the Bash, Read and Grep checks. A hook PR goes to the CEO
  (`ALL_Rules_Approvals` rule 5).
- severity: medium · title: there is no gitleaks pre-push hook; only pre-commit and CI exist · location:
  `scripts/install-git-hooks.sh` · recommendation: add a pre-push stanza that runs
  `gitleaks git --redact --log-opts=<remote>..HEAD`.
- severity: low · title: on a rotation, `put` merges the old metadata, so a direct `infisical_setup.py put` keeps
  a stale `expires` and `provider_name` · location: `tools/infisical_setup.py` `_write_secret` (the
  `existing is not None` branch) · recommendation: on PATCH, require `expires` and `provider_name` again. The
  KeyFetch gate now forces them, but only for KeyFetch.
- severity: low · title: the KeyFetch node tests do not run in CI · location: `.github/workflows/ci.yml` runs
  pytest and gitleaks only · recommendation: add a `node --test tests/keyfetch/` job on Node 22. As it stands, a
  regression in the gate keeps CI green.
- severity: low · title: PLAN §4d has no brand code for Chatudo · location:
  `docs/design/secrets-infisical/PLAN.md` §4d, `keyfetch_lib.mjs` `BRANDS` · recommendation: if a
  `Chatudo-Webapp` key is ever fetched, add the brand to the PLAN first, then to `BRANDS`. The gate refuses
  it until then, before any click.
- severity: info · title: `scripts/infisical/copy_secret.mjs` writes secrets on its own path, outside this gate ·
  recommendation: make it call `checkKeyMeta` when it is next touched.

## UNBUILT (marked in the skill as well)

- Expiry radar (PLAN §6 phase 5). Interim, in skill rule 4: the C-level files a LungNote to-do,
  `[key-expiry] …`, due 14 days before the date. The SessionStart deadline hook and
  `tools/email_ceo.py deadlines` (kind `deadline`) carry it from there.
- gitleaks pre-push hook.
- GitHub secret scanning and push protection on Agents-Core and Agents-Rules (they exist on GitHub but are
  off).
- Session-hook coverage of `/etc/infisical/*`.
- KeyFetch node tests in CI.
- IRON §65 itself: a draft only. The order text was not in my brief, so the CEO's verbatim words are a
  placeholder for the PH to fill in. The separate Agents-Rules PR is the PH's/CTO's.

## Issues / Blockers

- The PR is not opened by me. My worker Hard Rule 2 says never `git push`, and the brief asks for a PR. I told
  the PH earlier today (dev_message, acked) and got no instruction to push. The work is committed on
  `agent/security_engineer-task-0d3ec506`, and a local ref `hqsec/m1-rules` points at the same head. To open
  the PR: `git push origin hqsec/m1-rules`, then `gh pr create --base main --head hqsec/m1-rules` (do not
  merge).
- I am confident in this work at the current tier and effort.

## Notes for Reviewer

- threat model touched: yes. The gate moves the metadata checks before the provider click. Before this change,
  missing metadata was caught only by `put`, after the key existed at the provider, which left an orphan key
  to revoke. It now also forces a fresh `expires`/`provider_name` on every rotation.
- secrets reviewed: yes. No value in code, tests, docs or this report. The refusal messages name the field and
  never the value; a test feeds a fake key into each field and asserts that no 8-character piece of it comes
  back.
- CVEs introduced/removed: none (no dependency change).
- Choices made beyond the brief:
  - The gate also requires `console_url`, `owner` and `--comment`, because `put` refuses a new secret without
    them only after the click.
  - It refuses a duplicate `--meta` key and a malformed `--meta` item.
  - `provider_name`'s env must equal `--env`.
  - `expires` must equal the exp in the name. PLAN §4c and §4d define both as the provider's expiry.
  - A date not after today is refused ("dead on arrival").

  Revert any of these if the PH disagrees.
- The brand list is closed (PLAN §4d: mx ln wc lr ag), as is the host list (§3b: mac contabo winbox ci ceo).

## Not checked / risk

- The full pytest suite did not finish locally; 7,624 of 12,909 tests did not run (see Tests). This branch
  changes no Python file. The only Python-visible changes are a new skill and the regenerated index, and
  the skill tests cover those (125/125). CI is the first full run.
- The gate has not been run against a real provider page. The existing replay docs carry placeholders
  (`<page name>`), so the first real KeyFetch after this merge may be refused at parse time if its brief writes
  `expires` in a different form from the exp in the name. The refusal comes before any click, so the cost is
  a re-run, not an orphan key.
- `today` is computed in UTC. Between 00:00 and 07:00 TH, a key whose expiry is "today in Thailand" still passes
  the dead-on-arrival check. This edge does not matter for real one-year keys.

## Skill learning

- MISSING [ALL_Protocol_SkillAuthor §9 Rules template] : a numbered sub-list inside a HARD rule ends the block
  for `scripts/skill-doctrine-lint.py` before its `Why hard:`, and `test_real_corpus_reports_zero_defects`
  fails. The template should say "steps inside a rule are bullets, not 1. 2. 3." · evidence: 6aa26744 → fixed
  77e88d00
- MISSING [CTO_Procedure_KeyFetch §Steps 1] : step 1 says "`put` refuses a new secret without them". The script
  itself now refuses, with exit 64 and before the click, a write without a §4d `provider_name` (env = `--env`),
  `scope`, `expires` (= the name's exp, or `none-offered`), `console_url`, `owner` and `--comment`. A provider
  with no name field still needs a §4d `provider_name`: pixellab.md had `provider_name=none` · evidence: 0dbf7325
- MISSING [CXO_Protocol_DevSpawn §brief] : a brief that asks for an IRON section in the CEO's name has to carry
  his verbatim words, or the order text. This brief named O-20261027-1347-4e62 without its text, so IRON-65.md
  holds a placeholder · evidence: task-0d3ec506
- COSTLY [no owner] : IRON §34 item 5 contradicts Q-20261026-1118-4d3d. Nothing flags an IRON line after a CEO
  card supersedes it, and I found it only by reading §34 for style · evidence: Agents-Rules 3bc1f97 §34 item 5
