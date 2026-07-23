# MoonieX Console

Mobile-first web console that lets the operator (CEO/CTO) open and attach
to org agent tmux sessions (CTO/CMO/CFO/CXO chat) from a browser — iTerm2
Dark Background look, xterm.js terminal, WebAuthn passkey login.

Design spec: wiki `projects/mooniex-console.md`. Approved mockup:
`Agents/output/console-design/iterm-mobile-console.html`.

Local dev runs via `npm run dev`. Production deployment (Contabo, Tailscale,
TLS) is scripted — see **Deployment** below.

## Setup

```bash
cd console
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:4300 — you'll be redirected to `/login`.

Requires:
- Node ≥ 22.5 (uses the built-in `node:sqlite` module — no native DB driver).
- `tmux` on PATH (real agent sessions run inside real tmux sessions).
- Xcode Command Line Tools (macOS) / `build-essential` (Linux) + Python 3,
  for `node-pty`'s native build. `npm install` runs
  `scripts/ensure-node-pty.js` afterwards, which force-rebuilds `node-pty`
  from source if the install step didn't leave a compiled binary — this was
  observed on this dev machine's Node build (see script comment for why).

## First sign-in (bootstrap)

No operators are provisioned by default. The **first** successful passkey
registration or TOTP setup on `/login` becomes the console operator; after
that, registration endpoints require you to already be signed in (adding a
second passkey to your own account), so this isn't an open signup form.

- **Passkey (primary):** enter an operator name, tap "Register this device
  (Face ID / Passkey)". Works in any browser with a platform authenticator
  (Touch ID / Face ID / Windows Hello) as long as `WEBAUTHN_ORIGIN` matches
  the URL you're actually loading the page from.
- **TOTP (fallback):** tap "Show TOTP QR text instead" to get a base32
  secret + `otpauth://` URI, add it to any authenticator app (Google
  Authenticator, 1Password, etc.), then enter the 6-digit code.

## Environment

See `.env.example`. Key ones:

- `WEBAUTHN_RP_ID` / `WEBAUTHN_ORIGIN` — must match the hostname/URL you
  open in the browser exactly, or the passkey ceremony will fail. Default
  is `localhost:4300` for local dev.
- `ORG_ROOT` — repo root tmux sessions run from (defaults to one level up,
  i.e. the `Agents/` repo root where `runners/` lives).
- `PYTHON_BIN` — interpreter used to launch the agent chat REPL; defaults
  to `<ORG_ROOT>/.venv/bin/python` if present, else `python3`.

## How a session works

"Create New Session" picks a role (cto/cmo/cfo/cxo) and an optional name,
then:

1. `POST /api/sessions` slugifies the name and runs
   `tmux new-session -d -s {role}-{slug} 'bash <ORG_ROOT>/scripts/cto-claude.sh'`
   with cwd = `ORG_ROOT` (no-op if that session name already exists). This is
   the same launcher a real Mac iTerm CTO tab uses — the actual `claude` CLI
   with the CTO system prompt + MCP tools appended, not a custom REPL.
2. Browser redirects to `/agent/{role}/{slug}`, which opens a WebSocket to
   `/ws/agent/{role}/{slug}`.
3. The server keeps **one** `node-pty` process per tmux session name
   (`tmux attach-session -t {name}`), fanned out to every connected
   WebSocket client. Two tabs open on the same session both read from that
   one pty, so they see identical live output — and the bridge never spawns
   a second tmux session for a slug that already exists.
4. Composer text and helper keys (Esc/Tab/⌃C/↑/↓/Enter) write raw bytes
   into that pty, same as typing into a real terminal.

Closing the browser doesn't kill the tmux session — it keeps running until
its process exits or someone kills it with `tmux kill-session`.

## Known P1 simplification

Every agent session runs `scripts/cto-claude.sh` (the real `claude` CLI,
CTO system prompt + MCP tools) regardless of which role was picked — no
role-specific launcher (`cmo-claude.sh` etc.) exists yet (see
`src/tmux/command.js`). Role still drives the session name / badge / list
grouping; only the runtime command is shared for now. When per-role
launchers ship, add them to the `ROLE_SCRIPTS` map in `src/tmux/command.js`
— one line each.

## Tests

```bash
npm test
```

Covers session-list parsing (`tmux ls` output → role/slug objects) and the
auth-guard middleware (unauthenticated `/` and `/agent/*` redirect to
`/login`; unauthenticated API calls get 401 JSON instead).

## Deployment (Contabo, Tailscale-only)

The console is deployed to the Contabo VPS reachable **only over the tailnet** —
it is intentionally unreachable from the public internet. The Node server binds
directly to the tailnet interface IP (`100.118.171.23`), never `0.0.0.0`, so the
public interface (`194.233.80.26`) simply has nothing listening. No public ufw
port is opened.

Deploy is scripted and idempotent — `scripts/console-deploy.sh` (run from the
Mac, which is on the same tailnet):

```bash
scripts/console-deploy.sh all      # node -> sync -> install -> cert -> env -> service
scripts/console-deploy.sh verify   # acceptance checks
```

Stages (`node|sync|install|cert|env|service|verify`) can also be run one at a
time. What each does:

- **node** — installs an isolated Node 22 at `/opt/node-v22`. The box's system
  Node is 20.x, too old for the app's `node:sqlite` (needs ≥ 22.5). System Node
  is left untouched; the systemd unit points at the isolated one.
- **sync** — `rsync`es `console/` to `/opt/mooniex-console` (excludes
  `node_modules`, `.env`, `data/`, `certs/`).
- **install** — `npm ci` on the box; the `ensure-node-pty.js` postinstall guard
  rebuilds node-pty from source if no prebuild matches the box's Node ABI.
- **cert** — issues a tailscale Let's Encrypt cert for the MagicDNS name and
  installs the renewal timer (below).
- **env** — writes `/opt/mooniex-console/.env` (see keys below); the
  `SESSION_SECRET` is generated once on the box and preserved on redeploys.
- **service** — installs, enables, and starts `mooniex-console.service`.

### Bookmark

**`https://mooniex-contabo.tail400676.ts.net:8443/`** — open on any device on
the tailnet (iPhone with the Tailscale app connected). Port `8443` because
`443` on the box is already taken by the webapp's docker-proxy. The cert is a
real, publicly-trusted Let's Encrypt cert (no browser warning).

### TLS cert renewal

Tailscale certs are valid ~90 days. A systemd timer
(`mooniex-console-cert-renew.timer`, weekly) runs `tailscale cert` again — a
cheap no-op until the cert is near expiry — then restarts the console so it
reloads the new cert. Reference unit files live in `console/deploy/`; the
authoritative copies are generated on the box by the deploy script's `cert`
and `service` stages.

### Production `.env` keys

Set by the `env` stage (values are box-specific; secret is never committed):

| key | value |
| --- | --- |
| `PORT` | `8443` |
| `HOST` | `100.118.171.23` (tailnet IP — bind target) |
| `TLS_CERT_FILE` / `TLS_KEY_FILE` | tailscale cert/key under `certs/` |
| `WEBAUTHN_RP_ID` | `mooniex-contabo.tail400676.ts.net` |
| `WEBAUTHN_ORIGIN` | `https://mooniex-contabo.tail400676.ts.net:8443` |
| `SESSION_SECRET` | random 32-byte hex, generated once on the box |
| `COOKIE_SECURE` | `true` (served over HTTPS) |

`HOST`, `TLS_CERT_FILE`, `TLS_KEY_FILE` are new deploy-only env knobs read by
`src/config.js` / `src/server.js`. When unset (local dev) the server keeps its
original behaviour: plain HTTP on all interfaces.

### `console.mooniex.com` (deferred)

The prettier custom domain is **not** set up — it needs a DNS-01 ACME challenge
(GoDaddy API) because the A record points at a private tailnet IP that public
HTTP-01 validators can't reach. The MagicDNS URL above already satisfies "open
it from the iPhone", so this is a lower-priority follow-up.

## Project layout

```
console/
  src/
    config.js          env / paths
    db.js               node:sqlite — operators, webauthn_credentials, totp_secrets
    auth/                cookies, webauthn, totp, guard middleware, routes
    tmux/                session naming, tmux shell-outs, node-pty bridge
    routes/              page routes (login/list/chat), JSON API routes
    ws.js                 WebSocket upgrade + auth guard + bridge wiring
    app.js / server.js    express app assembly / http + ws boot
  public/                login.html, index.html, chat.html + their JS/CSS
  test/                   vitest + supertest
```
