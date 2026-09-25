# Infisical: one online home for every secret

**Status:** APPROVED by the CEO 2026-09-25 ("ok ทั้ง 5", plus: write the Org-Infra writing and
naming rules → §3b). Phase 1 next. Owner: CTO (cto-885ae930).
**Lineage:** GH Agents-Core#16 (2026-06-13, "Centralize secrets → Infisical self-host", closed
into the LungNote roadmap note 177b1658 on 2026-09-23) · CEO ruling 2026-09-19 ("ศูนย์กลางของ
.env โดยไม่เก็บไว้ที่เครื่องใดเครื่องนึงอีกต่อไป", Vercel included; backend Contabo, frontend
Vercel) · Ask Inbox plan 2026-09-23 (Infisical = phase 4) · IRON §34 key registry
(`mooniex:playbooks/api-key-registry.md`), which this plan turns from a hand-kept page into a
view of Infisical.
**Research:** every Infisical and provider fact below was read from the vendor's own page on
2026-09-25 by a research pass. Rows marked UNVERIFIED were not confirmed.

## 1. Why: measured on Contabo, 2026-09-25 (names and value hashes only, no value printed)

| # | Finding | Evidence |
|---|---|---|
| 1 | One name, three different secrets | `TELEGRAM_BOT_TOKEN` in AlphaTrader, ClaudeFlow and `/etc/mooniex/secretary-secrets.env`: three different values (three bots), and the name says which bot in none of them |
| 2 | One value, several projects | the same value under `SUPABASE_SERVICE_KEY` (ClaudeFlow = Option), `OPENROUTER_API_KEY` (ClaudeFlow = Option), `NOTION_API_KEY` + `SUPABASE_KEY` (AlphaTrader = ClaudeFlow), `GOOGLE_OAUTH_*` (ClaudeFlow = Option), `ZAI_API_KEY` (ClaudeFlow = secretary), LungNote `SUPABASE_SECRET_KEY` (Agents/Core/mcp = LungNote/Mcp). A leak or rotation hits every project at once; spend cannot be split by project |
| 3 | Silent override | ClaudeFlow `.env` sets `FAL_API_KEY` twice with different values; the second wins and nothing says so |
| 4 | Name drift | `SUPABASE_SERVICE_ROLE_KEY` (webapp) = `SUPABASE_SERVICE_KEY` (claudeflow), per the registry |
| 5 | Copies on disk | 9 live env files on Contabo plus 10 archived copies (`Archive/mooniex-vps/…/_env-bundle` + the project dirs, GH #177). Mac, winbox and Vercel not counted from here |
| 6 | Leaked, not yet rotated | Cloudflare token (chat 08-07), Jules key (09-18), `NINEROUTER_API_KEY` (09-19), R2 token (screenshot), Meta CAPI token, Google Translate key …hSA, Z.ai keys (plan cancelled 09-20, still in two Contabo files) |
| 7 | Expired without warning | Contabo GitHub token (`gh` → 401 today), SomPong's Claude OAuth (08-16), Meta Ads token |

What Infisical changes: one place per value, every machine pulls at start, a rotation is one edit
that reaches every consumer (and Vercel through a sync), and each secret carries who/what/when as
metadata instead of in someone's memory.

## 2. Hosting: Infisical Cloud, Free tier, to start

| Option | Cost | For | Against |
|---|---|---|---|
| **Cloud Free (recommended)** | $0 | nothing to run; works when Contabo is down; Vercel sync included | 5 identities; no version history, no audit log, no IP allowlist, no custom roles; cross-project references need Pro |
| Cloud Pro | $20 per identity per month billed yearly, $23 monthly (4 identities ≈ $80–92/month) | + version history / point-in-time recovery, 30-day audit log, IP allowlist, cross-project references | money; ask the CEO first |
| Self-host on Contabo | $0 licence | values stay on our box | Contabo has 7.8 GB RAM with 3.0 GB free; Infisical documents 2 vCPU/4 GB for the app + 4 GB for Redis (+ Postgres). Contabo becomes the one box every machine needs at boot; losing its encryption key loses every secret; audit log, PITR, custom roles still need a paid licence |

Free limits that shape this plan (infisical.com/pricing, 2026-09-25): 5 identities, 3
environments per project, 10 secret syncs, no versioning, no audit log. Project count on Free is
not stated on the page (UNVERIFIED). Whether a human user counts against the 5 identities is
UNVERIFIED; the plan assumes it does.

Consequence of "no version history": a changed value is gone. Rule: **rotate forward only** —
mint the new key at the provider, put it in Infisical, verify the consumer, then revoke the old
key. Never overwrite a value that cannot be re-issued (passwords) without writing it at the
provider first.

## 3. Projects: one Infisical project per repo

The permission wall on Free is the **project** (no custom roles, so no env- or folder-level
limits). So the split follows `hq.yaml`: **Infisical project name = the GitHub repo name**
(`MoonieX-ClaudeFlow`), created only for rows that hold secrets. Two rows are not repos:

- `Agents-Core` — the org runtime on all three machines: SomPong/secretary, org Postgres,
  Run Inbox tokens, Jules, Jev/OpenRouter, LungNote MCP client creds.
- `Org-Infra` — keys whose job is to change an account rather than run a service, and whose
  leak can break everything: DNS, deploys, repo admin, the tailnet, the Drive app, the Postgres
  superuser. Rules of its own in §3b.

Environments: `prod` and `dev` (Free allows 3). `prod` = touches real customers, money or public
channels. Machine is never an environment. No folders until a project needs two access levels.

| Infisical project | Contabo | Mac | winbox | Vercel sync |
|---|---|---|---|---|
| Agents-Core | read | read | read | |
| Org-Infra | | read | | |
| MoonieX-ClaudeFlow | read | | | |
| MoonieX-Option | read | | | |
| MoonieX-AlphaTrader | read | | | |
| MoonieX-LineAutomation | read | | | |
| MoonieX-Console | read | read | read | |
| MoonieX-ComfyRunpod | | read | | |
| MoonieX-CookierunBot | | | read | |
| MoonieX-WebApp | | (later) | | prod |
| LungNote-MCP | read | read | | |
| LungNote-Webapp, WarpClip-Webapp, LinkReed-Webapp | | | | prod |

Identities (5 on Free; the pricing page counts the human user as one): `ceo` (human, org
admin) · `contabo` · `mac` · `winbox` · the fifth slot is the temporary `setup` identity during
the migration. Each machine identity is a **Viewer** (read-only) on exactly the projects in its
column; on Free a Viewer sees every environment of the project, so the Mac gets
`MoonieX-WebApp` only when local development needs it. Imports are done by `setup` on the
machine that holds the `.env`, straight from that file (the value never crosses a chat or
another machine). `setup` never writes an Org-Infra value (§3b rule 1) and is retired
(`tools/infisical_setup.py retire-setup`) when Contabo's cutover ends, at most 14 days after it
was created.
Vercel syncs use an app connection, not an identity; 4 web apps × prod = 4 of the 10 syncs.

Shared values (finding 2) end: **one provider key per project** — OpenRouter, Supabase secret
keys, fal, Anthropic, OpenAI and Deepgram can all issue several named keys. A secret the provider
issues only once (a bot token, an app secret) lives in the project that owns it; another project
that needs it calls that project's API (ADR 0028). Where that cannot happen yet, the value is
copied into the second project with tag `shared` and `also_in` metadata naming every copy.

## 3b. Org-Infra: what goes in, who writes, how it is named (CEO, 2026-09-25)

**Goes in.** A key that changes an account: Cloudflare DNS, Vercel deploy/project settings,
GitHub repo administration, Tailscale API and auth keys (adding a machine), the Postgres
superuser, Infisical's own app connections (Vercel sync).

**Stays out.**
- A key a service needs at runtime goes into that service's project, even when it touches
  infrastructure: ClaudeFlow's R2 key → `MoonieX-ClaudeFlow`; the Drive OAuth client and each
  machine's Drive token (used while the upload job runs) → `Agents-Core`.
- A credential that *is* a machine (SSH private key, Tailscale node key, a repo deploy key) stays
  on that machine and is re-made when the machine is rebuilt (ADR 0031). Org-Infra keeps only a
  record of it: value = the public fingerprint, KIND `ID`, with `expires` so the radar sees it.

**Readers.** The CEO and the `mac` identity. Adding a reader is a CEO decision written into this
section. A Contabo or winbox session that needs an infra action asks for it (Run Inbox card);
it does not read the key.

**Write rules.**
1. Only the CEO writes to Org-Infra, in the Infisical web page, copying the value straight from
   the provider's page. No machine identity gets write here, not even on an import day, and no
   agent types, pastes or sees an Org-Infra value. The CTO prepares everything else: the name,
   the metadata, the scope to choose at the provider.
2. Smallest scope the provider offers: one zone, one repo, one project, one bucket. A wider key
   carries tag `wide` and metadata `why_wide`.
3. Expiry is mandatory. `admin` ≤ 90 days; `rw` and `ro` ≤ 1 year. Set it at the provider when
   the provider can; the radar (phase 5) enforces the rest.
4. One key per job × machine. The same key never sits on two machines, so a lost machine means
   revoking exactly its keys and nothing else.
5. The §4c metadata plus three infra fields: `blast_radius` (one line: what a thief could do),
   `revoke_url` (the exact page), `used_by` (host + script path).
6. Every create / rotate / revoke adds a line to the registry Changelog (IRON §34 rule 2: date ·
   name · action · who · why · old-last4 → new-last4). On the Free tier that line is the only
   history there is.
7. Rotate forward only (§2): new key at the provider → Infisical → verify the consumer → revoke
   the old one.
8. Never: in chat, in git, in a screenshot, in a second place (notes app, `.env` backup), or an
   account-wide key where a scoped one exists.
9. The CEO's Infisical login uses 2FA. Its recovery codes stay offline with the CEO, never in
   Infisical, a repo or a chat. If Infisical is unreachable, services run from the CLI cache and
   infra work waits.

**Naming.**
- Infisical: project `Org-Infra`, environment `prod` only (infra has no test copy), one folder
  per job from a closed list: `/dns` `/deploy` `/repo` `/net` `/db` `/vault`. A new job
  is a plan edit the CEO approves.
- Variable: JOB and HOST are mandatory here because every Org-Infra key is per job × machine.
  ```
  <PROVIDER>_<JOB>_<HOST>_<KIND>[_<ACCESS>]
  CLOUDFLARE_DNS_MAC_TOKEN_RW · VERCEL_DEPLOY_MAC_TOKEN_RW · GITHUB_REPO_MAC_TOKEN_ADMIN
  TAILSCALE_NET_MAC_API_KEY_ADMIN · POSTGRES_DB_CONTABO_PASSWORD_ADMIN
  ```
- Provider page:
  ```
  infra-<job>-<host>-<access>-exp<YYYY-MM-DD>
  infra-dns-mac-rw-exp2026-12-24               (30 characters)
  infra-deploy-contabo-admin-exp2026-12-24     (40, the longest possible)
  ```
  Jobs ≤ 6 characters and hosts ≤ 7 keep every name within GitHub's 40.
- Hosts (closed list): `mac` `contabo` `winbox` `ci` (GitHub Actions) `ceo` (the CEO's own manual
  use).

**Known Org-Infra items to bring in (phase 3/4):** the Cloudflare DNS token (leaked 08-07, rotate),
the Vercel `mooniexofficials` token (Mac), the Mac `gh` token, Contabo's dead GitHub PAT (replace
with per-repo deploy keys that stay on Contabo; record fingerprints), the Postgres superuser,
the Tailscale keys if any exist.

## 4. Naming: four places, four rules

The CEO's ask: read a name and know the permission, the project, the expiry. Where each fact can
live depends on where the name is shown.

### 4a. Infisical project and environment
Project = repo name (§3). Environment = `prod` | `dev`.

### 4b. Secret name = the environment variable the code reads
```
<PROVIDER>_[<WHICH>_]<KIND>[_<ACCESS>]
```
- `PROVIDER` — who issued it: `OPENROUTER`, `SUPABASE`, `CLOUDFLARE`, `R2`, `TELEGRAM`, `LINE`,
  `META`, `FAL`, `GOOGLE`… For our own service-to-service tokens, the service that checks it:
  `CLAUDEFLOW`, `CONSOLE`, `RUN_INBOX`.
- `WHICH` — only when one provider gives us several: the bot, bucket, channel or account.
  `TELEGRAM_SOMPONG_BOT_TOKEN`, `R2_MEDIA_…`, `LINE_LUNAR_…`.
- `KIND` — closed list: `API_KEY` `TOKEN` `BOT_TOKEN` `SECRET` `CLIENT_ID` `CLIENT_SECRET`
  `REFRESH_TOKEN` `PASSWORD` `PRIVATE_KEY` `WEBHOOK_SECRET` `URL` `ID`.
- `ACCESS` — closed list, only when the provider has levels: `RO` (read only), `RW` (use and
  write, may spend), `ADMIN` (can create or delete keys, billing). `FAL_API_KEY` +
  `FAL_API_KEY_ADMIN`; `SENTRY_TOKEN_RO` / `SENTRY_TOKEN_RW`.
- **Not in the variable name, and why:** project (the Infisical project is the namespace; the
  same code runs in two projects), environment (Infisical's env), expiry or date (every rotation
  would force a code change), machine. This matches 12-factor, Doppler, AWS and GitLab practice:
  the name says what it is; the metadata says who, when and how much.
- `NEXT_PUBLIC_` = shipped to the browser. A `NEXT_PUBLIC_` name with KIND `SECRET`, `TOKEN`,
  `PASSWORD` or `PRIVATE_KEY` is refused by the lint.
- Existing names move **1:1** at import (no code change). A rename is that project's own code PR
  later (phase 6).

### 4c. Metadata on every secret in Infisical (required)
Infisical stores a comment, tags and key-value metadata per secret (API: `secretComment`,
`tags`, `secretMetadata`), plus a rotation reminder (`secretReminderRepeatDays`, tier
UNVERIFIED).

| Field | Where | Example |
|---|---|---|
| purpose | comment | `ClaudeFlow วิดีโอ gen (fal queue)` |
| provider_name | metadata | `mx-claudeflow-prod-rw-exp2027-03-31` (4d, the link to the provider page) |
| console_url | metadata | where to rotate or revoke |
| scope | metadata | `bucket mooniex-media, Object R/W` |
| expires | metadata | `2027-03-31` (provider-enforced, or our rotate-by date) |
| owner | metadata | `CTO` / `CEO` / `CMO` |
| created | metadata | `2026-09-25 cto-885ae930` |
| spend_cap | metadata | `$20/month` when the provider caps |
| also_in | metadata | other projects holding a copy (tag `shared`) |
| status | tag | `active` · `leaked` · `retiring` |
| provider, access | tags | `provider:openrouter`, `access:rw` |

### 4d. Name on the provider's API-key page
The provider page shows nothing of ours except this string, so it carries the most:
```
<brand>-<project>-<env>-<access>-exp<YYYY-MM-DD>
mx-claudeflow-prod-rw-exp2027-03-31          (35 characters)
```
- brand: `mx` MoonieX · `ln` LungNote · `wc` WarpClip · `lr` LinkReed · `ag` Agents
  (`ag-core`). Org-Infra has its own pattern (§3b).
- project: the repo suffix, lowercase (`claudeflow`, `webapp`, `lineautomation`).
- env `prod|dev`, access `ro|rw|admin`, as in 4b.
- `exp`: the provider-enforced expiry when the provider has one (Cloudflare, GitHub PAT, Vercel,
  Supabase PAT, Anthropic, Deepgram, Meta 60-day, LINE ≤ 30 days); otherwise our rotate-by date,
  default one year after creation.
- Optional last part `-<host>` only for a key bound to one machine (deploy key, IP-locked).
- Limit 40 characters (GitHub fine-grained PAT names cap at 40; the longest project,
  `mx-lineautomation-prod-rw-exp2027-03-31`, is 39).
- Providers with no name field (Telegram, LINE channel token, Omise, SerpApi, Twelve Data, Pexels,
  Jules, Supabase publishable/secret keys, Gemini AI Studio — UNVERIFIED for the last two): the
  Infisical metadata is the only record. For Telegram, `WHICH` = the bot's @username.
- Machine identities in Infisical are named by host: `contabo`, `mac`, `winbox`; each client
  secret's description = `<host>-<YYYY-MM-DD>`.

## 5. How machines read secrets

- Services on Contabo (docker compose, systemd, pm2): `infisical run --env=prod --projectId=<id>
  -- <cmd>`; the CLI caches and falls back to the cache if Infisical is unreachable. For a
  container that needs a file: `infisical export` to tmpfs at start, never to disk.
- Mac and winbox: the same CLI (brew / winget-scoop).
- Vercel: Infisical → Vercel sync, one way. Editing an env var in the Vercel UI is forbidden
  after cutover (the next sync overwrites it).
- Agents: a worker gets secrets only through `infisical run` at spawn, for its own project; no
  agent reads or echoes a value (Run Inbox already rejects secret-shaped text).
- The one secret left on each machine: that machine's identity client secret, root-only 0600
  (`/etc/infisical/<host>.secret`, `C:\ProgramData\Infisical\` on winbox). It can only read, and
  the CEO revokes it with one click if the machine is lost.

## 6. Phases

| Phase | What | Who | Cost |
|---|---|---|---|
| 0 | CEO approves §2–§4 | CEO | $0 |
| 1 | CEO: sign up (Cloud US, pass.gob1, org `MoonieX`, 2FA on, recovery codes offline), create one temporary identity `setup` (org Admin, Universal Auth), then tap Run on a Run Inbox card that runs `scripts/infisical-save-secret.sh setup` on Contabo and type its Client ID + Secret into the card's input (never stored, echo masked). CTO: `tools/infisical_setup.py apply --mint contabo` creates the projects, environments, Org-Infra folders, the `contabo` / `mac` / `winbox` identities with their Viewer memberships and the CEO as admin of every project, and saves Contabo's own client secret (0600). Mac and winbox secrets are minted at their cutover | CEO ~15 min + CTO | $0 |
| 2 | Pilot: MoonieX-LineAutomation (2 secrets) on Contabo, 1:1 import, restart from Infisical, delete its `.env` | CTO | $0 |
| 3 | Cut over project by project (ClaudeFlow 123 lines, Option, AlphaTrader, Console, LungNote-MCP, Agents-Core incl. secretary + org-db, Mac, winbox, Vercel sync). Each `.env` deleted 7 days after its service runs green from Infisical. `_env-bundle` imported, then deleted with CEO OK (GH #177) | CTO | $0 |
| 4 | Rotation sweep with the new provider names: the 7 leaked keys, the shared values (one new key per project), the FAL duplicate | CEO logs in (phone relay) + CTO | $0 |
| 5 | Expiry radar: a tool reads `expires` from Infisical and files a LungNote to-do 14 days before (the SessionStart hook then surfaces it). `api-key-registry.md` becomes a generated view; IRON §34 points at Infisical | CTO | $0 |
| 6 | Renames to the §4b grammar, one code PR per project | CTO/DEV | $0 |

## 7. Decisions (CEO: "ok ทั้ง 5", 2026-09-25)

1. Cloud Free to start (Pro only if we want the audit log or version history: ≈ $80–92/month).
2. One Infisical project per repo + `Agents-Core` + `Org-Infra`, access by machine.
3. The naming rules in §4b (variable), §4c (metadata) and §4d (provider page).
4. Move names 1:1 now, rename later per project.
5. Pilot = MoonieX-LineAutomation.

## 8. Not verified yet

- Whether the human user counts toward the 5 Free identities.
- Project limit on Free.
- Which tier the secret reminder needs.
- Name-field presence/limits for Supabase API keys, Gemini AI Studio, Cloudflare R2 tokens, and
  max name lengths for most providers (only GitHub's 40 is documented).
- Infisical SOC 2 type and incident history (trust.infisical.com, not read).
