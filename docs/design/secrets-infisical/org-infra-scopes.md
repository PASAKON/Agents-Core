# Org-Infra scopes — proposal, 2026-10-26

## 1. Layout

Mandate: CEO card Q-20261026-0814-e94a (choice "ทุก project รวม Org-Infra"): every project belongs in Org-Infra with explicit scopes, and C-levels may create/delete provider keys through KeyFetch. Recorded in `.claude/skills/ALL_Rules_Approvals/SKILL.md` rule 2 and `CLAUDE.md` §Secrets; until this design lands the tools refuse Org-Infra.
Use one Infisical project, `Org-Infra`, environments `dev` and `prod`, project namespaces `/<Project>`; preserve existing subfolders beneath them.
Keep existing infrastructure job folders `/dns`, `/deploy`, `/repo`, `/net`, `/db`, `/vault` in prod only, avoiding a disruptive rename; current list: `tools/infisical_setup.py:110`.
Runtime names and metadata move unchanged, following `docs/design/secrets-infisical/PLAN.md:203` and `docs/design/secrets-infisical/PLAN.md:206`; retain infra naming/expiry/blast-radius rules from `docs/design/secrets-infisical/PLAN.md:127`.
Within each namespace, isolate provider API keys in explicitly registered `/<Project>/<existing-subpath>/provider-keys` folders; non-provider credentials remain outside these folders. Infra provider keys use `/<job>/provider-keys`.
Preserve `/MoonieX-ClaudeFlow/chatudo` as a separate instance; today's instance rule is `docs/design/secrets-infisical/PLAN.md:61`.
**Blocking prerequisite:** documented Free tier has no folder/environment permission wall (`docs/design/secrets-infisical/PLAN.md:50`; `tools/infisical_setup.py:80`). Folder selection is not authorization.
Do not consolidate under blanket Viewer access. CEO must first obtain and verify a tier/deployment with environment/path-scoped custom roles; exact current entitlement and permission semantics: not found in the repo.
If unavailable, keep separate projects temporarily; naming alone cannot satisfy the mandate. This proposal supersedes the old runtime exclusion and CEO-only writer rule only after approval (`docs/design/secrets-infisical/PLAN.md:110`, `docs/design/secrets-infisical/PLAN.md:122`).

## 2. Readers

Inventory below is checked-in wiring or documented host/role coverage, not a live deployment assertion. Paths are proposed Org-Infra destinations; prod unless stated. A root path means that folder's secrets, never recursive access.
Where provider keys are split out, a reader receives only its explicitly inventoried provider-key subfolder as well; no namespace-wide wildcard. Each listed service gets a separate scoped runtime identity at cutover; current shared identities are shown for traceability.
Host rows cover documented project access beyond individually listed services; replace their broad Agents-Core access with reviewed secret lists before granting. Hosts cannot retain a shared credential that bypasses service isolation.
Default host selection is winbox on Windows, mac on Darwin, contabo otherwise (`tools/infisical_setup.py:308`). “Host default” below means that selection, not a verified deployment host.

| Consumer (existing source) | Proposed path(s) it reads | Identity used now |
|---|---|---|
| secretary (`deploy/systemd/mooniex-secretary.service.d/org-db.conf:21`) | `/Agents-Core` | contabo |
| secretary-waker (`deploy/systemd/mooniex-secretary-waker.service.d/org-db.conf:20`) | `/Agents-Core` | contabo |
| watchdog (`deploy/systemd/mooniex-watchdog.service.d/org-db.conf:15`) | `/Agents-Core` | contabo |
| household-reminders (`deploy/systemd/household-reminders.service:35`) | `/MoonieX-SomPong` | contabo |
| sompong-reminders (`deploy/systemd/sompong-reminders.service:13`) | `/LungNote-MCP`, `/MoonieX-SomPong` | contabo |
| Gmail broker, provisioning gated (`scripts/install-gmail-broker.sh:41`; `docs/design/gmail-broker.md:77`) | `/MoonieX-SomPong/gmail-broker` | contabo |
| spend-guard check (`deploy/systemd/spend-guard.service:7`; `tools/spend_guard.py:678`) | `/Agents-Core/spend-guard/provider-keys` | host default |
| org-join API (`deploy/join/org-join.service:52`) | `/Agents-Core/org-join` | contabo |
| org-node-token API (`deploy/node-token/org-node-token.service:49`) | `/Agents-Core/node-token`, `/Org-Node` | contabo |
| org-coo-gate (`deploy/coo-gate/org-coo-gate.service:32`) | `/Org-Coo/<configured SECRET_PATH>`; concrete deployed path not found in the repo | contabo |
| org-snapshot (`deploy/systemd/org-snapshot.service:20`) | `/Agents-Core` via wrapper (`scripts/hub/with-org-db-env.sh:60`) | host default |
| node-probe (`deploy/systemd/node-probe.service:30`) | `/Agents-Core` via same wrapper | host default |
| escalation-watch (`deploy/systemd/escalation-watch.service:17`) | `/Agents-Core` via same wrapper | host default |
| tool-value-collect (`deploy/systemd/tool-value-collect.service:29`) | `/Agents-Core` via same wrapper | host default |
| tool-value-report (`deploy/systemd/tool-value-report.service:31`) | `/Agents-Core` via same wrapper | host default |
| join drill (`scripts/drill-join.sh:67`) | `/Agents-Core/org-join` | host default |
| join door (`deploy/join/door.sh:276`) | `/Agents-Core` | contabo |
| cutover helper (`scripts/hub/contabo-cutover-remote.sh:50`) | `/Agents-Core` | contabo |
| org MCP launcher (`scripts/lib/cxo_mcp_config.py:339`; `scripts/lib/cxo_mcp_config.py:41`) | `/Agents-Core` | winbox directly; host default through wrapper |
| Contabo project workloads (`tools/infisical_setup.py:129`) | `/MoonieX-ClaudeFlow`, `/MoonieX-Option`, `/MoonieX-AlphaTrader`, `/MoonieX-LineAutomation`, `/MoonieX-Console`, `/LungNote-MCP`; `/Agents-Core` residual usage must be inventoried | contabo |
| Mac project workloads (`tools/infisical_setup.py:131`) | `/Agents-Core`, `/MoonieX-Console`, `/MoonieX-ComfyRunpod`, `/LungNote-MCP`; infra only separately approved job paths | mac |
| winbox project workloads (`tools/infisical_setup.py:134`) | `/Agents-Core`, `/MoonieX-Console`, `/MoonieX-CookierunBot`, `/LungNote-MCP`, `/MoonieX-Option` | winbox |
| Bedrock host roles, PLAN only (`docs/design/secrets-infisical/PLAN.md:82`) | `/MoonieX-Bedrock` | contabo, mac per PLAN; absent from setup mapping (`tools/infisical_setup.py:92`) |
| MoonieX-WebApp sync, PLAN only (`docs/design/secrets-infisical/PLAN.md:81`) | `/MoonieX-WebApp` | Vercel app connection, not identity (`docs/design/secrets-infisical/PLAN.md:95`) |
| LungNote-Webapp sync, PLAN only (`docs/design/secrets-infisical/PLAN.md:84`) | `/LungNote-Webapp` | Vercel app connection, same source |
| WarpClip-Webapp sync, PLAN only (`docs/design/secrets-infisical/PLAN.md:84`) | `/WarpClip-Webapp` | Vercel app connection, same source |
| LinkReed-Webapp sync, PLAN only (`docs/design/secrets-infisical/PLAN.md:84`) | `/LinkReed-Webapp` | Vercel app connection, same source |
| Approved nodes, mediated readers (`tools/infisical_setup.py:80`) | `/Org-Node` through token API only; no direct vault access | none |
| CEO administration (`docs/design/secrets-infisical/PLAN.md:86`) | all, exceptional human administration | ceo human org admin |

For dev, grant separate dev identities only on confirmed development needs; the old Viewer grants span environments (`tools/infisical_setup.py:125`). Do not duplicate prod grants automatically.
Source runtime reads use one explicit folder and inject into the process (`tools/infisical_setup.py:892`). Proposed split-folder reads require explicit chained runs or a reviewed allowlisted loader, with duplicate variable names rejected.
Before grants, resolve host aggregate rows into per-workload identities and exact paths; unresolved workloads stay in old projects. No direct vault grants to nodes, no root/all-path Viewer grant to mac or contabo in Org-Infra.

## 3. Writer

Create `keyfetch-writer` with no org-admin role: create/delete secrets only in a per-task allowlist of provider-key folders and environments; deny reads elsewhere, identity/role management, sync management, and folder creation.
Prefer no secret reads at all if supported; permit minimal folder discovery only if required. Exact create/delete-without-read support: not found in the repo; verify before activation, never compensate with project Developer.
If reads are required, scope them to those same provider-key folders only, time-limit the grant, and record the exception. Unrelated passwords, OAuth refresh tokens, DB credentials and identity credentials are excluded.
Provider-side creation/revocation is separate from deleting an Infisical entry: use the C-level-authorized provider session, record provider key handle, and revoke only the selected key after successful replacement verification.
Current writer is capture → stdin put (`.claude/skills/CTO_Procedure_KeyFetch/SKILL.md:15`); default identity is setup (`scripts/keyfetch/keyfetch_lib.mjs:16`). Both parser and put reject Org-Infra (`scripts/keyfetch/keyfetch_lib.mjs:34`; `tools/infisical_setup.py:682`).
Current put reads before writing (`tools/infisical_setup.py:737`); new-only verification also reads via last4 (`scripts/keyfetch/keyfetch_lib.mjs:146`). A write-only identity needs a new create-only path and separate scoped-reader verification, not just removal of guards.
Contabo is documented Viewer on every project as measured Oct 23 (`docs/design/gmail-broker.md:78`); earlier contradictory Developer notes exist (`.claude/skills/CTO_Procedure_KeyFetch/SKILL.md:148`), so do not assume write permission.
Setup's old secret returned 401 (`docs/ops/keyfetch/infisical-setup-identity.md:6`); Gmail provisioning requires a writer grant (`docs/design/gmail-broker.md:77`). Exact stalled execution record: not found in the repo; stall is task-supplied context.
Do not revive setup as a permanent writer. Retire any remaining setup identity/seat through CEO account; expiry alone did not free a seat (`.claude/skills/CTO_Procedure_KeyFetch/SKILL.md:139`).
Gmail bootstrap needs a separate temporary grant limited to its OAuth folder, outside KeyFetch's provider-key permission. Never widen keyfetch-writer to unblock it.
Implementation follow-up must update guards, copy tooling, reader launchers and policy tests together; copy currently also refuses Org-Infra (`scripts/infisical/copy_secret.mjs:113`). This document changes none of them.

## 4. Move order

Proposed risk order below is a planning judgment, not measured traffic. Gate each project on exact source-folder inventory, named owner, reviewed destination grants and successful deny tests for sibling paths and wrong environments.
**Every project step:** copy values/metadata in a zero-model process into its Org-Infra namespace; switch all its consumers/syncs; perform one real read per new consumed path as its new reader (status-only result), then service health check; remove old write grants and leave old project read-only. On failure restore its consumer before continuing.
Never print values or suffixes into this public repo. Keep the old secrets; deletion requires a separate CEO instruction, regardless of elapsed days. Avoid dual writes: freeze provisioning for the short copy/switch window.
1. MoonieX-LineAutomation dev then prod: proposed pilot, matching the older two-secret pilot (`docs/design/secrets-infisical/PLAN.md:267`); apply the full copy/switch/read/read-only sequence.
2. MoonieX-ComfyRunpod, then MoonieX-CookierunBot: one project at a time, dev first; same sequence, verify on the respective host.
3. MoonieX-Console, then MoonieX-Bedrock: same sequence, each host switched independently; Bedrock inventory discrepancy must be resolved first.
4. MoonieX-WebApp, LungNote-Webapp, WarpClip-Webapp, LinkReed-Webapp: separately apply the sequence and verify each sync destination before freezing the old project.
5. MoonieX-ClaudeFlow (including chatudo), then MoonieX-Option, then MoonieX-AlphaTrader: same sequence; schedule customer/trading windows and verify every instance before the next project.
6. LungNote-MCP, then MoonieX-SomPong: same sequence for reminders and broker; coordinate the two-source reminders reader. Gmail stays gated until its separate bootstrap writer is ready.
7. Org-Coo, then Agents-Core, then Org-Node: same sequence, last because gate/DB/join/token consumers are shared dependencies; stage dual-source readers while projects cross over separately.
8. Existing infra job folders: keep paths, split approved provider keys, replace mac's broad role with explicit job grants, verify one read per approved path; no legacy infrastructure secret deletion.
9. Any additional project discovered in the authorized inventory: require an owner and risk placement, then repeat the same sequence; the setup list is not asserted exhaustive (`tools/infisical_setup.py:92` versus `scripts/install-gmail-broker.sh:41`).
No source project is deleted. New projects must register namespaces, owners, exact consumers and provider-key folders before their first secret is stored.

## 5. What only the CEO does — one sitting

Prepare the concrete grants manifest and implementation review first; the CEO performs these account-level changes, with no credential pasted into chat or this repository.
1. [ ] Confirm supported path/environment custom roles and sufficient identity capacity in his account; select entitlement before consolidation. Current documented cap is five including users (`tools/infisical_setup.py:87`).
2. [ ] Remove residual expired setup identity/credentials; create a short-lived migration identity with source read and destination create only for the first project's exact paths, no IAM administration.
3. [ ] Approve Org-Infra dev/prod and namespace/folder manifest; preserve CEO human administrative access and remove any inherited broad machine grants before adding runtime data.
4. [ ] Create per-consumer/env reader identities from the resolved table; assign exact-path read-only custom roles with no sibling, parent-recursive or cross-env read. Scope Vercel connections separately to their own prod paths.
5. [ ] Create keyfetch-writer with the restricted role in §3; approve any strictly necessary provider-folder read exception, TTL and authorized C-level operators. Create a separate short-lived Gmail bootstrap writer if needed.
6. [ ] Review allowed-read/denied-read and denied-write results before enabling each prepared consumer switch; pre-authorize sequential migration-grant replacements, never an all-project migration wildcard.
7. [ ] At each completed cutover revoke old writer grants, preserving rollback read grants; expire migration/bootstrap identities at completion and remove old runtime grants after the observation window. Retain old secrets pending his deletion instruction.

## 6. Risks and rollback

Risks: unsupported path ACLs, shared-host credential bypass, stale inventory, sync leakage, variable collisions and a failed bootstrap writer can defeat isolation or availability; block cutover until resolved and test negative access explicitly.
Rollback: restore the previous consumer command/sync source and retained read-only project grants, restart and health-check; do not revoke old provider keys during migration, and rotate forward if a key was separately revoked (existing rule: `docs/design/secrets-infisical/PLAN.md:137`).

## 7. Decisions for the CEO

1. Permission boundary: **recommended — supported custom path/env roles with sufficient identity capacity**, subject to account verification and quoted cost; alternative — defer consolidation and retain isolated projects. Blanket Viewer is not a safe option.
2. Reader granularity: **recommended — per-service/per-env identities**, resolving host rows before migration; alternative — per-project/per-host identities with an explicitly accepted larger within-project exposure.
3. Writer reads: **recommended — create/delete-only with independent reader verification** where supported; alternative — time-limited read/create/delete on approved provider-key folders only, with no read elsewhere.
