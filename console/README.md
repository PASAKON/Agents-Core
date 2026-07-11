# MoonieX Console

Mobile-first web console that lets the operator (CEO/CTO) open and attach
to org agent tmux sessions (CTO/CMO/CFO/CXO chat) from a browser — iTerm2
Dark Background look, xterm.js terminal, WebAuthn passkey login.

Design spec: wiki `projects/mooniex-console.md`. Approved mockup:
`Agents/output/console-design/iterm-mobile-console.html`.

This is the **P1 local MVP** — deployment (Contabo, traefik, Tailscale, DNS)
is a separate devops task. Everything here runs locally via `npm run dev`.

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
   `tmux new-session -d -s {role}-{slug} '<python> -m runners.cto_chat'`
   with cwd = `ORG_ROOT` (no-op if that session name already exists).
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

TASK.md's backend spec says every agent session runs
`python -m runners.cto_chat` regardless of which role was picked — only
`runners/cto_chat.py` exists today (see `src/tmux/command.js`). Role still
drives the session name / badge / list grouping; only the runtime command
is shared for now. When `runners/cmo_chat.py` etc. ship, add them to the
`ROLE_MODULES` map in `src/tmux/command.js` — one line each.

## Tests

```bash
npm test
```

Covers session-list parsing (`tmux ls` output → role/slug objects) and the
auth-guard middleware (unauthenticated `/` and `/agent/*` redirect to
`/login`; unauthenticated API calls get 401 JSON instead).

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
