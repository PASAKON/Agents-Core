# TASK — build the phone login relay in MoonieX Console

Repo: **`/Users/gob/Projects/mooniex-console`** (GitHub `PASAKON/MoonieX-Console`).
Node ≥22.5, Express + `ws`, ESM. Deployed to Contabo, served at
`https://terminal.mooniex.com`, reachable over Tailscale only.

Everything you need is below. Build it in this repo, on a branch. Do not deploy.

---

## 1. The problem this solves

Today every browser login is done by sitting at the machine. The CEO is often
out, so automation that needs a logged-in browser waits for him to come home.

**He wants: log into any site, on any machine — Mac, winbox, Contabo — from his
phone alone, from anywhere.**

The answer is **not** to store sessions. Storing a cookie jar solves the easy
half; the hard halves are acquiring a session (needs a human at a real login
form) and using it (Google ties a session to device and IP, so a moved session
gets kicked). So:

> **Relay the screen. Never move the session.**

The page shows him the *target machine's own browser*. He types into the real
login form, on the machine that will keep the session. No credential ever passes
through our storage, and there is no secret blob to leak.

---

## 2. What to build

A new authenticated page `/relay` plus its backend.

```
phone ──HTTPS/WSS──► terminal.mooniex.com/relay      (existing passkey auth)
                        │  choose machine: mac · winbox · contabo
                        ▼
                     CDP over the tailnet to that machine's Chrome
                        Page.startScreencast   → frames out to the phone
                        Input.dispatchMouseEvent → his taps
                        Input.insertText         → his typed text
```

### 2a. Make it phone-shaped BEFORE relaying — this is the whole usability story
A raw 1920×1080 desktop screencast on a phone is unusable: pinch-zoom, thumb-
sized targets, keyboard covering the field. Do not build that. Instead, on
connect, call on the remote browser:

- `Emulation.setDeviceMetricsOverride` → width 390, height 844, deviceScaleFactor 3, `mobile: true`
- `Emulation.setUserAgentOverride` → an iPhone Safari UA

Google then serves its **mobile** login page, which is already designed for
thumbs, and the screencast arrives in the phone's own aspect ratio. The mapping
becomes 1:1 — a tap lands where he tapped, with no coordinate maths and no zoom.

### 2b. Typing is local, not keystroke-by-keystroke
Put a real `<input>` on the relay page. He types with his own keyboard, so iOS
autofill and his password manager work normally. On submit, send the whole
string once and apply it remotely with `Input.insertText` into the focused
field. Never stream individual keydowns across the network — it feels broken on
mobile latency.

Provide buttons for the few keys that matter: **Enter**, **Tab**, **Back**.

### 2c. Screencast cheaply
`Page.startScreencast` with `format: "jpeg", quality: 60, maxWidth: 390`, and ack
each frame with `Page.screencastFrameAck`. A login form barely moves; keep it
light enough for mobile data.

---

## 3. Where things go in this repo

Follow the layout that exists — do not invent a new structure.

| what | where | pattern to copy |
|---|---|---|
| page route | `src/routes/pages.js` | it already uses `requireAuth` |
| API + WS route | `src/relay/` (new dir) | mirror `src/tmux/bridge.js` for the WS shape |
| CDP client | `src/relay/cdp.js` (new) | `src/peer/client.js` for outbound-connection style |
| machine list | `src/config.js` | add a `relayTargets` map: name → CDP url |
| front end | `public/relay.html` + `public/js/relay.js` | `public/chat.html` for markup/CSS conventions |
| tests | `test/relay-*.test.js` | vitest, as the existing tests do |

**Auth is not optional and not yours to design.** Use the existing
`requireAuth` / `requireAuthApi` from `src/auth/middleware.js`. The relay page
and every relay endpoint sit behind it, exactly like the terminal does. Do not
add a second auth scheme, a query-string token, or a "temporary" bypass.

`ws` is already a dependency. Do not add Playwright or Puppeteer — talk to CDP
directly over a WebSocket (`ws://<host>:9223/devtools/page/<id>`); it is a small
JSON protocol and pulling in a browser driver here would be a large dependency
for three method calls.

---

## 4. Machine targets

| name | CDP endpoint | note |
|---|---|---|
| `mac` | `http://100.64.2.37:9223` | profile `~/.flow-automation/chrome-profile`, launched by `scripts/flow/launch-chrome-debug.sh` in the Agents repo |
| `winbox` | `http://100.123.83.75:9223` | **a bot owns that desktop.** The relay must not start Chrome there; assume a human or another tool did |
| `contabo` | `http://127.0.0.1:9223` | not set up yet — headless Chrome is fine, `Page.startScreencast` works without a display |

Chrome binds its debug port to localhost by default, so reaching it across the
tailnet needs either an SSH tunnel from the console host or a deliberate bind.
**Prefer an SSH tunnel; do not tell Chrome to listen on 0.0.0.0.** A debug port
open on a LAN is full control of that browser with no authentication. Say in
your report which approach you implemented and why.

If a target is unreachable, the page shows it greyed out with the reason. It
must never look available and then hang.

---

## 5. Scope — keep it this small on purpose

**This is a login relay, not a remote desktop, and it should refuse to be one.**

- Show the login flow, let him finish it, close the relay.
- Idle timeout: close the WS and stop the screencast after 5 minutes of no input.
- One relay session at a time. A second connection is refused, not queued.
- Log every relay session: who, when, which machine, which origin was on screen.

Keeping the scope this narrow is what keeps it simple and safe. Do not add file
transfer, clipboard sync, multi-tab, or a full desktop view.

---

## 6. Hard rules

- **Never store, log, or transmit a password, cookie, or session token.** The
  typed value goes straight to `Input.insertText` and is not written anywhere —
  not to a log line, not to an error message, not to the DB.
- **Do not deploy.** Branch `agent/antigravity-login-relay`, push, stop. A human
  reviews and deploys.
- **Do not touch** `src/auth/**` beyond importing the middleware, `src/tmux/**`,
  or anything under `deploy/`.
- **Do not log in to anything yourself.** If testing needs a logged-in browser,
  say so and stop.
- No new runtime dependencies without saying why in the report.

---

## 7. What done looks like

1. `npm test` green, including new tests for: auth is required; a tap maps 1:1
   at 390-width; `Input.insertText` is used rather than per-key events; idle
   timeout closes the socket; an unreachable target degrades instead of hanging.
2. A short manual check against the **Mac** target (it is running now): open
   `/relay`, pick `mac`, see the page, tap a link, type into a field. Describe
   exactly what you saw.
3. Nothing deployed, nothing merged to `main`.

---

## 8. Report back

```
branch: agent/antigravity-login-relay   commit: <sha>
tests: X passed / Y total  (new: N)
manual check on mac: <what you actually saw, step by step>
CDP reachability: <tunnel or bind, and why>
new dependencies: <none, or name + reason>
not done / unsure: <be specific>
```

Report what you **verified**, separately from what you **believe** works. On
this project a status message has been wrong three times in one evening while
the underlying number was right — so if you did not watch it happen, say so.

---

## 9. Ask before

- adding any dependency beyond `ws`
- anything that would make Chrome listen on a non-loopback address
- touching auth, deploy config, or `main`
- any change that widens this beyond a login relay
