# REPORT task-5b2a7baa

## Summary
`scripts/infisical/copy_secret.mjs` is built, committed and tested: 17/17 node tests on node 22 and node 20, and 3 of 3 planted bugs caught. On Contabo the `--dry` found that **Org-Infra/prod holds no secret at all**: one env (`prod`), exactly the 7 §3b folders, 0 names in each. A control listing of MoonieX-Bedrock/prod with the same session returned 1 name, so the listing works. The fal key the brief names is not in Org-Infra. I stopped before any write, as the brief says. `MoonieX-Bedrock/prod FAL_API_KEY` was **not created**, steps 3 and 4 did not run, and the Lumina Skies sound batch is still blocked.

## Files Changed
- `scripts/infisical/copy_secret.mjs`: new. Borrows the session (one in-page `POST /api/v1/auth/token`, as `bootstrap_setup_identity.mjs` §1–2, signed-out → exit 4). Looks up both projects by name. Walks the source env's real folder tree (`/api/v2/folders`, names only), plus the §3b list for Org-Infra. Requires exactly one shared name matching the regex. The target must be absent (404) and is never Org-Infra (checked at parse time and again after lookup). POSTs with `type:'shared'`, comment and metadata (`source`, `rotate_with=source`, `owner=CTO`, `created`, `status=active` plus `--meta`; a real run needs `provider_name console_url scope expires`, as `put` does). Verifies by an in-memory compare and prints MATCH or MISMATCH. Prints names, paths and HTTP statuses only, never a response body.
- `tests/js/copy_secret.test.mjs`: new, 17 tests against a fake CDP browser and a fake Infisical on 127.0.0.1.
- `tests/test_copy_secret.py`: new pytest wrapper so CI (`pytest`) collects the node suite.
- `docs/ops/keyfetch/README.md`: a paragraph on cross-project copy (dry run first, and its match line goes in the brief).
- `.claude/skills/CTO_Procedure_KeyFetch/SKILL.md`: one Field note, `2026-10-12 [MISSING] §When to invoke … status: pending`.
- `docs/reports/task-5b2a7baa/REPORT.md` and `BLOCKER.md`: this report and the blocker.

## Commits
- 0e4d3f0b security: copy_secret.mjs — copy one Infisical secret across projects, zero-model
- a75a0b83 security: copy_secret walks the source env's real folder tree (names only)
- 926879b5 docs(keyfetch): cross-project copy with copy_secret.mjs; dry run first
- 2cbd047a skill(CTO_Procedure_KeyFetch): note — cross-project copy path; Org-Infra/prod was empty — evidence task-5b2a7baa
- (this report and BLOCKER.md: the last commit on the branch)

## Tests
- ran: `find tests/js -name 'copy_secret.test.mjs' | xargs node --experimental-websocket --test`, with PATH `node` v22.23.3 and `/usr/bin/node` v20.20.2
- passed: 17 (both versions)
- failed: 0
- skipped: 0
- last lines (node 22): `# pass 17` · `# fail 0` · `# skipped 0` · `# duration_ms 5592.57308`
- pytest: `tests/test_copy_secret.py tests/test_keyfetch_capture.py` gave 2 passed (the keyfetch suite is unchanged and still green).
- Mutation check on a scratch copy: three planted bugs, each caught. (1) Printing the value's last 4 failed 7 tests on the leak assertion. (2) Dropping the parse-time Org-Infra refusal failed the Org-Infra test (the browser had been contacted). (3) Dropping the target-exists refusal failed the target-exists test.
- The 17 cases: one match → write and MATCH · zero match → exit 8 · two matches → exit 8 with both names · target exists → exit 9 · Org-Infra target (two spellings) → exit 64 before any CDP or API call · `--dry` · MISMATCH → exit 12 · unreadable folder → exit 7 (its error body echoes the value and is not printed) · failed write → exit 11 (same echo test) · signed-out `/login` tab and 401 refresh → exit 4 · org selection uses the new token · nested folder outside the §3b list is found · unreadable folder tree → exit 7 · zero match names the envs · personal secrets ignored · 11 usage refusals · non-loopback API or CDP refused. Every run asserts that the fake value, its last 4 and all three fake tokens are absent from stdout and stderr.
- Dependency audit: no dependency added or changed (node built-ins only, no manifest touched), so there was nothing to audit.

## Gates
| Gate | Result |
|---|---|
| `node --test` passes | PASS 17/17, last line `# duration_ms 5592.57308` |
| Step 3 prints MATCH | **NOT RUN.** Blocked: the source does not exist |
| Step 4 prints `last4=<present>` | **NOT RUN.** Blocked |
| `git log -p` of my commits has no key-shaped string | PASS. A regex scan for fal / JWT / sk- / ghp_ / AKIA shapes over `327f7664..HEAD` found 0. gitleaks is not installed on Contabo, so it was not run |

## Dry and real output lines (names only, complete stdout and stderr)
Browser Home `infisical` launched at `http://127.0.0.1:9281`. The tab was on `/organizations/<org>/projects`, so it was signed in. It was quit afterwards and port 9281 is down.

Dry run 1 (`--from 'Org-Infra:prod:^FAL' --to 'MoonieX-Bedrock:prod:FAL_API_KEY' --dry`, §3b list only):
```
[copy] session token OK · org c519f604
[copy] source Org-Infra/prod: HTTP 200 · 0 names · 0 match
[copy] source Org-Infra/prod/dns: HTTP 200 · 0 names · 0 match
[copy] source Org-Infra/prod/deploy: HTTP 200 · 0 names · 0 match
[copy] source Org-Infra/prod/repo: HTTP 200 · 0 names · 0 match
[copy] source Org-Infra/prod/net: HTTP 200 · 0 names · 0 match
[copy] source Org-Infra/prod/db: HTTP 200 · 0 names · 0 match
[copy] source Org-Infra/prod/vault: HTTP 200 · 0 names · 0 match
[copy] 0 names match /^FAL/ — need exactly one; nothing written        exit=8
```
Dry run 2 (same arguments, after the folder walk, a75a0b83):
```
[copy] source Org-Infra/prod: 7 folder(s)
[copy] source Org-Infra/prod{,/db,/deploy,/dns,/net,/repo,/vault}: HTTP 200 · 0 names · 0 match   (7 lines)
[copy] source project Org-Infra has environments: prod
[copy] 0 names match /^FAL/ — need exactly one; nothing written        exit=8
```
Control (`--from 'MoonieX-Bedrock:prod:^NO_SUCH_NAME_XYZ$' … --dry`, matches nothing by design):
```
[copy] source MoonieX-Bedrock/prod: 1 folder(s)
[copy] source MoonieX-Bedrock/prod: HTTP 200 · 1 names · 0 match
[copy] source project MoonieX-Bedrock has environments: dev prod
[copy] 0 names match /^NO_SUCH_NAME_XYZ$/ — need exactly one; nothing written   exit=8
```
Real run: not run.

## Findings
- severity: medium
- title: the brief's source does not exist, because Org-Infra/prod holds no secret, so there is no fal key to copy from it
- location: Infisical project Org-Infra, env prod (all 7 folders)
- recommendation: the CTO finds where "MoonieX's fal key" actually lives and quotes a `--dry` match line in the next brief. Re-running is two commands with a new `--from`. Creating a NEW fal key instead is a provider-side create (KeyFetch procedure, §34 registry-first) and needs the CEO's go. This tool does not do that.

- severity: low
- title: a copy cannot carry `also_in` on its source when the source is in Org-Infra
- location: PLAN §3 ("copied … with tag `shared` and `also_in` metadata naming every copy")
- recommendation: the target records `source=` and `rotate_with=source`. The source's `also_in` is a CEO-only edit in Org-Infra. If the eventual source is not Org-Infra, a follow-up `put` of metadata only would close it.

- severity: low
- title: the §34 rule 2 registry line must land with the copy
- location: `mooniex:playbooks/api-key-registry.md` (wiki, which workers cannot write)
- recommendation: when the copy lands, add `2026-10-12 · FAL_API_KEY (MoonieX-Bedrock/prod) · create (copy of <source>) · task-5b2a7baa for cto-369faf85 · Lumina Skies sound gen · — → <same last4 as source>`.

- severity: info
- title: hardening in the new tool
- location: `scripts/infisical/copy_secret.mjs`
- recommendation: none. CDP and `INFISICAL_API_URL` are loopback-only (the borrowed admin token comes back over the plaintext CDP socket, and a test override must not send token or value off the box). No overwrite path exists. API error bodies are never printed, because a validation error can echo the value it rejected.

## What I could not check
- The live write and verify path (`POST /api/v3/secrets/raw/<NAME>` with `type`, `secretComment` and `secretMetadata`, then the read-back) ran only against the fake. Live Infisical did prove the token borrow (org claim present), `GET /api/v2/organizations/<org>/workspaces` including `environments`, `GET /api/v2/folders` and `GET /api/v3/secrets/raw` listing.
- The live target-absent check (`GET …/raw/FAL_API_KEY` → 404) was never reached, because both runs stopped at the source.
- Where the fal key really is: not searched. The brief forbids touching other projects.
- gitleaks: not installed on Contabo.

## Issues / Blockers
- **BLOCKED:** Org-Infra/prod has no secrets, so `--from 'Org-Infra:prod:^FAL'` can never match. I need the real `<Project>:<env>:<name>` of the fal key the CEO meant. Then: `--dry` with that `--from`, the step 3 command unchanged, and step 4. The Browser Home must be launched again; its login was still valid at 03:45 UTC.
- The brief's claim "Contabo node is v20.20.2" is half true. PATH `node` here is v22.23.3 (`/opt/MoonieXHQ/Agents/Core/.tools/node/bin/node`) and `/usr/bin/node` is v20.20.2. Both pass with the flag.

## Notes for Reviewer
- threat model touched: yes. The new tool borrows the CEO's Infisical user session (org admin) from the Browser Home, the same trust boundary as `bootstrap_setup_identity.mjs`. Mitigations are listed under Findings/info.
- secrets reviewed: yes. Three live runs printed no value, length, last 4 or token (complete output above). The suite asserts this on every run.
- CVEs introduced/removed: none (no dependencies).
- Scope: I extended the brief once. After dry run 1 returned 0 names, the source scan was made to walk the real folder tree (names only), `--dry` was rerun, and one control listing ran on the target project. Nothing was written. No identity, access, role or membership changed. No other project, no service restart, no call to fal.
- SKILL-OVERRIDE: worker rules :: "you do not edit the skill file yourself" :: added the Field note to CTO_Procedure_KeyFetch (2cbd047a) :: brief step 6 asked for it, from the skill's owner (CTO).
- `bootstrap_setup_identity.mjs` was not touched. The borrow code is duplicated, as it already is between capture/bootstrap. A shared module is a possible follow-up.

## Skill learning
- MISSING [CTO_Procedure_KeyFetch §When to invoke] : no path for copying an existing Infisical key into a second project. Field note added (2cbd047a), and the tool is `scripts/infisical/copy_secret.mjs` · evidence: task-5b2a7baa
- MISSING [CXO_Protocol_DevSpawn §3d Every brief — what the worktree will not tell the worker] : a brief that states where a secret lives must quote the evidence it was seen there (a `--dry` or list line). This brief said "sits in Infisical project Org-Infra (prod)", and Org-Infra/prod holds 0 secrets · evidence: task-5b2a7baa dry runs 1–2 and the control
- WRONG   [no owner] : "Contabo node is v20.20.2" (brief, from task-494414fc) · evidence: `which -a node` → .tools/node v22.23.3 first on PATH, /usr/bin/node v20.20.2 · fix: name the path. Both work with `--experimental-websocket`
- COSTLY  [no owner] : the fake-CDP WebSocket framing (`frame`/`readFrames`) is now copy-pasted in two test files (tests/keyfetch, tests/js) · evidence: tests/js/copy_secret.test.mjs · prevented by: a shared `tests/js/fake_cdp.mjs` helper
