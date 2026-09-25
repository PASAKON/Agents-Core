# Infisical: one online home for every secret

**Status:** plan for CEO decision (2026-09-25, cto-885ae930). Nothing created yet: no account,
no project, no identity.
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
- `Org-Infra` — keys that belong to no single project and can break everything: Cloudflare DNS,
  Vercel team token, GitHub PATs/deploy keys, Tailscale auth keys, the Drive token, Contabo
  Postgres superuser. Readable by the Mac identity and the CEO only.

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
| MoonieX-WebApp | | read (dev) | | prod |
| LungNote-MCP | read | read | | |
| LungNote-Webapp, WarpClip-Webapp, LinkReed-Webapp | | | | prod |

Identities (5 on Free): `ceo` (human, org admin) · `contabo` · `mac` · `winbox` · one spare.
Each machine identity is a **Viewer** (read-only) on exactly the projects in its column. Import
day only: the machine that holds a `.env` gets write on that one project, imports straight from
its own file (the value never crosses a chat or another machine), then drops back to Viewer.
Vercel syncs use an app connection, not an identity; 4 web apps × prod = 4 of the 10 syncs.

Shared values (finding 2) end: **one provider key per project** — OpenRouter, Supabase secret
keys, fal, Anthropic, OpenAI and Deepgram can all issue several named keys. A secret the provider
issues only once (a bot token, an app secret) lives in the project that owns it; another project
that needs it calls that project's API (ADR 0028). Where that cannot happen yet, the value is
copied into the second project with tag `shared` and `also_in` metadata naming every copy.

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
  (`ag-core`, `ag-infra`).
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
| 1 | Sign up (Cloud, org "MoonieX"), create the projects in §3 and the 3 machine identities; the client secret goes into each machine's root-only file via `!`, never chat | CEO ~15 min + CTO | $0 |
| 2 | Pilot: MoonieX-LineAutomation (2 secrets) on Contabo, 1:1 import, restart from Infisical, delete its `.env` | CTO | $0 |
| 3 | Cut over project by project (ClaudeFlow 123 lines, Option, AlphaTrader, Console, LungNote-MCP, Agents-Core incl. secretary + org-db, Mac, winbox, Vercel sync). Each `.env` deleted 7 days after its service runs green from Infisical. `_env-bundle` imported, then deleted with CEO OK (GH #177) | CTO | $0 |
| 4 | Rotation sweep with the new provider names: the 7 leaked keys, the shared values (one new key per project), the FAL duplicate | CEO logs in (phone relay) + CTO | $0 |
| 5 | Expiry radar: a tool reads `expires` from Infisical and files a LungNote to-do 14 days before (the SessionStart hook then surfaces it). `api-key-registry.md` becomes a generated view; IRON §34 points at Infisical | CTO | $0 |
| 6 | Renames to the §4b grammar, one code PR per project | CTO/DEV | $0 |

## 7. Decisions for the CEO

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
