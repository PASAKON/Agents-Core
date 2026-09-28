# Infisical phase 2 — the first live consumer (2026-09-28, cto-885ae930)

CEO 2026-09-28: "บังคับใช้ตั้งแต่ตอนนี้". Rules: `CLAUDE.md` §Secrets · plan: `docs/design/secrets-infisical/PLAN.md`
· adding a key: skill `CTO_Procedure_KeyFetch` · tool: `tools/infisical_setup.py` (stdlib, every machine).

## What is live

| piece | state |
|---|---|
| `mooniex-line-queue.service` (Contabo) | starts under `infisical_setup.py run MoonieX-LineAutomation prod --as contabo -- uvicorn …` — drop-in `/etc/systemd/system/mooniex-line-queue.service.d/infisical.conf`; `EnvironmentFile` cleared; `.env` stays until **2026-10-05** (7 green days), then is deleted (LungNote 1b063336) |
| Secrets | `MoonieX-LineAutomation/prod`: `VPS_QUEUE_TOKEN`, `VPS_QUEUE_DB` (legacy name, metadata `naming=legacy`, rename in phase 6); imported 1:1 with `import-env`, verified MATCH by last4 |
| Contabo identity | `/etc/infisical/contabo.env` (root 0600, 365 d) — Viewer on its 7 projects; `run` proven |
| Mac / winbox identities | exist in Infisical (Viewer), **no client secret on the machine yet** → see below |

Rollback: delete the drop-in, `systemctl daemon-reload`, `systemctl restart mooniex-line-queue` — the unit is
back on `.env`.

## How a service or launcher uses secrets (the interface — no skill needed)

```
python3 tools/infisical_setup.py run <Project> <env> [--as <host>] -- <command...>
```
The command's environment carries the project's secrets; nothing is written to disk; stderr names the
keys, never a value. `--as` defaults to this machine (contabo / mac / winbox). If Infisical is
unreachable at start the command does not start (systemd `Restart=on-failure` retries).

- systemd: a drop-in that clears `EnvironmentFile=` and re-points `ExecStart=` through `run` (above).
- docker compose: `run … -- docker compose up` (values reach compose through the environment;
  `env_file:` lines are removed).
- a C-level or worker launcher: wrap `claude` the same way for `Agents-Core prod` once the org-db
  values live there (Org Mesh W1) — the org MCP then finds `ORG_DB_URL` in its environment.

## Adding, rotating, importing

- one key from a provider page → skill `CTO_Procedure_KeyFetch` (worker + `capture_key.mjs` → `put`).
- one value already in hand on a machine (file, never chat) → `put <Project> <env> <NAME> --stdin …`.
- a whole `.env` → `import-env <Project> <env> <path> [--legacy] --comment … --meta …`; then the
  service moves to `run`; `.env` deleted after 7 green days; every key that ever sat in two places or in
  chat is rotated (PLAN §6 phase 4).

## Mac and winbox — one login each, zero typing

On the machine itself (its CTO session), after the CEO's relay login to app.infisical.com in that
machine's Browser Home (`relay-login`):

```
node scripts/infisical/bootstrap_setup_identity.mjs http://127.0.0.1:<cdp-port> --identity mac      # or winbox
```
It mints a 365-day client secret for the existing identity through the page's own session and hands it
to `infisical_setup.py save <name> --stdin` → `/etc/infisical/<name>.env` (winbox:
`%ProgramData%\Infisical\<name>.env`). Nobody sees the value. Then `run` works there exactly as on
Contabo. Never create the secret in the UI and paste it; never copy a machine's file to another
machine.

## Identity budget (Free tier 5/5)

CEO + setup + contabo + mac + winbox. `retire-setup` (right after the first imports, before 2026-10-10)
frees one slot for a fourth machine (Org Mesh §6.4); a fifth machine needs a decision (shared node
identity or Pro).
