---
name: relay-login
owner: CTO
origin: mooniex-org
scope: >-
  How any org session gets a browser login done by the CEO from his phone
  through the MoonieX Console login relay (https://terminal.mooniex.com/relay):
  exposing a Chrome on the Mac, Contabo or winbox, telling the CEO which pill
  to tap, and recording a page pattern once so the next visit needs no one.
  Not for driving a browser yourself (that is browser-operator) and not for
  deciding whether a login is needed.
description: Get a login done by the CEO from his phone via the Console login relay. Trigger on /relay-login, "login relay", "ให้ CEO login", "ขอ login", "session หมดอายุ", "cookie หมดอายุ", "ต้อง login ใหม่", "QR login", or whenever a task is blocked on a browser login on any machine. Use instead of asking the CEO to type a code into chat, and instead of taking the CEO's desk browser.
created_by: agent
author: CTO
audience: [cto, cxo, browser_operator, devops_engineer, developer, qa]
---

# relay-login — a login the CEO does from his phone

The relay streams a machine's own automation Chrome to the CEO's phone over
CDP and never moves a session. The CEO fills a **mirrored form** (the page's
fields and buttons drawn as phone controls) or taps the live screen; the vault
saves the account behind Face ID. Your job is to put the right Chrome on the
right port, name the pill, and get out of the way. Console docs: `docs/relay.md`
(§1 targets, §6 vault, §7 form mirror + patterns).

## 0. Who does what

- **Worker (any role) blocked on a login:** do §1 on the machine you run on,
  then put ONE line in your report or in a letter to your CTO —
  `relay-login: <machine>:<port> — <tab title> · account: <which> · why: <one clause>` —
  and carry on with whatever does not need the login. You never contact the
  CEO yourself and never wait at a prompt for him.
- **CTO:** forward that line to the CEO in chat (or answer the SomPong order),
  read the relay's result, and tell the worker via its mailbox when the
  session is live. If the mirror showed the page badly, you write the pattern (§4).
- **CEO:** taps the pill on https://terminal.mooniex.com/relay and logs in.

## 1. Expose the Chrome (one per account, a dedicated profile)

| machine | port | how |
|---|---|---|
| Contabo | 9222–9299 on 127.0.0.1 | `chrome --headless=new --remote-debugging-port=92xx --user-data-dir=<profile> --window-size=390,844 --user-agent="<a normal Chrome UA>"` — Google refuses the HeadlessChrome UA (E_BLOCKED, measured 2026-09-24) |
| Mac | 9222–9299 on 127.0.0.1 | `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=92xx --user-data-dir=<profile>`; each running Chrome costs a ~1.4 GB code-sign clone — quit it after the login |
| winbox | **9220–9229** on 127.0.0.1 | Contabo holds the tunnel (systemd `mooniex-relay-tunnel-winbox`, Contabo 9270–9279 → winbox 9220–9229). ssh lands in session 0, so open Chrome on the desktop through an interactive scheduled task; recipe + two registered tasks (`MooniexRelayChrome9224` ChatGPT, `MooniexRelayChrome9225` Google home) in memory `reference_winbox_desktop_chrome_relaunch` |

Never `--remote-debugging-address=0.0.0.0`, never the CEO's everyday profile,
never touch another CTO's automation Chrome without a letter first (IRON §33).
Ports already taken: Mac 9223 ChatGPT (8c06958c), Mac 9224 BL TikTok
(3d312dd6), winbox 9224 ChatGPT (8c06958c), winbox 9225 Google home, Contabo
9250 fake login test page, 9251 layout render rig.

## 2. Tell the CEO which pill

Open the login page in that Chrome first, then write in chat (or a
`[CEO via SomPong]` reply) the exact pill text: `<machine>:<port> — <tab title>`,
e.g. `winbox:9225 — Sign in - Google Accounts`, plus which account. A page that
does not look like a login sits under "Chrome อื่นที่กำลังทำงานอัตโนมัติ" and needs
two taps — say so. The relay then reports success/failure itself with an Error
ID (`RLY-…`, `data/relay-errors.jsonl` on the Console host) — read that, never
ask the CEO what he saw.

## 3. Traps that are not the relay's fault

- **OS windows are invisible**: Windows Hello / passkey sheets / Chrome's
  save-password bubble. Google's passkey step is already patterned (Continue
  disabled, "Try another way" preferred). If a page freezes, the CEO's Reload
  button cancels the pending prompt. Steer flows to password/SMS, not passkey.
- **QR logins** (TikTok, LINE): the relay switches to QR mode itself; TikTok
  then needs an in-app confirm tap and the QR lives 1–2 min — start the Chrome
  only when the CEO is holding the phone.
- **"กดไม่ติด"**: read the tab's host+path first (`node scripts/relay-inspect.mjs
  --port N` on the Console host), then think about coordinates.

## 4. Record a page pattern once (layer 2) — you, the requesting session

If the mirror shows the page badly (wrong primary button, clutter, a div
button without a label, a native prompt), write a pattern so the next visit is
right without anyone:

```bash
# on the Console host (Contabo for winbox/Contabo Chromes; the Mac for Mac Chromes)
node scripts/relay-inspect.mjs --port 9275        # prints the mirror + a skeleton
```

Fill `rules` (label regexes → `prefer` / `hide` / `disabled` + `hint` / `labelTh`,
pattern-level `note` / `nativePrompt`), drop the file as
`data/relay-patterns/<id>.json` next to `console.db` — live within 3 s, no
restart. Good ones go into the repo as seeds (`src/relay/patterns/`, PR to
MoonieX-Console). A pattern only decorates what the page has; it can never add
a control, so a wrong one degrades to the plain mirror. Labels and hints only —
never a value, cookie or QR payload.

## 5. After the login

- Confirm from your side (the site's API/page), not from the relay's banner.
- Quit a Mac Chrome you started. Leave winbox/Contabo ones only if the task
  keeps using them; say which port you left up.
- Report in your Skill learning what the mirror got wrong — that is where the
  next seed pattern comes from.

## Field notes
- 2026-09-25 [MISSING] rollout test: two live sessions (Mac cto-95cbbb28, Contabo cto-e1e3d3ef) got the letter cold and both answered in the §0 one-line format within 2 min (one real request — Facebook Dorsine Gobb on mac:9230 — one "not blocked"); the format needs no further explanation in the letter · evidence: GH MoonieX-Console#9 comment 2026-09-25 05:1x · status: pending
- 2026-09-25 [MISSING] after a Google login Chrome's own "Sign in to Chrome" intercept (`chrome://signin-dice-web-intercept.top-chrome`) shows up as the first page target, so `relay-inspect` and the pill list can pick it before the real tab; skip `chrome://` / `*.top-chrome` targets · evidence: winbox:9225 04:4x, GH MoonieX-Console#9 · status: pending
- 2026-09-25 [MISSING] the mirror's first real-site login (Google on winbox:9225) is still unverified; the fake form on Contabo:9250 passed the CEO's test and winbox:9224 ChatGPT came up signed in after his phone flow · evidence: MoonieX-Console 62ea287, GH MoonieX-Console#9 · status: pending
