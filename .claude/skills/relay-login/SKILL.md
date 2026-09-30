---
name: relay-login
kind: protocol
owner: CTO
origin: mooniex-org
scope: >-
  How any org session gets a browser login done by the CEO from his phone
  through the MoonieX Console login relay (https://terminal.mooniex.com/relay):
  exposing a Chrome on the Mac, Contabo or winbox, telling the CEO which pill
  to tap, and recording a page pattern once so the next visit needs no one.
  Not for driving a browser yourself (that is BROWSER_OPERATOR_Protocol_Playbook) and not for
  deciding whether a login is needed.
description: PROTOCOL — Get a login done by the CEO from his phone via the Console login relay. Trigger on /relay-login, "login relay", "ให้ CEO login", "ขอ login", "session หมดอายุ", "cookie หมดอายุ", "ต้อง login ใหม่", "QR login", or whenever a task is blocked on a browser login on any machine. Use instead of asking the CEO to type a code into chat, and instead of taking the CEO's desk browser.
created_by: agent
author: CTO
audience: [cto, cxo, browser_operator, devops_engineer, developer, tester]
---

# relay-login — a login the CEO does from his phone

The relay streams a machine's own automation Chrome to the CEO's phone over
CDP and never moves a session. The CEO fills a **mirrored form** (the page's
fields and buttons drawn as phone controls) or taps the live screen; the vault
saves the account behind Face ID. Your job is to put the right Chrome on the
right port, name the pill, and get out of the way. Console docs: `docs/relay.md`
(§1 targets, §6 vault, §7 form mirror + patterns).

Not for a CLI login (`claude auth login`, `gh auth login`, a device code):
the relay serves only a Chrome page, and steering a CLI's own browser-open
into a relay Chrome was refused by the auto-mode classifier as a bypass
(cto-3156a56c, 2026-09-27). Those go through `ALL_Protocol_RunInbox`
(`--expects-input`); on the Mac or winbox before its P2, its §Hosts route.

## 0. Who does what

- **Worker (any role) blocked on a login:** do §1 on the machine you run on,
  then put ONE line in your report or in a letter to your CTO —
  `relay-login: <machine>:<port> — <tab title> · account: <which> · why: <one clause>` —
  and carry on with whatever does not need the login. You never contact the
  CEO yourself and never wait at a prompt for him. Work that must follow the
  login waits in a detached shell loop, never a model: two workers polling a
  login tab spent ~165k tokens on a login that came the next day, and
  `scripts/infisical/watch_login.sh` (poll every 20 s up to 12 h, run the
  follow-up script, wake the CTO's pane with one line) replaced them (297fa49c).
- **CTO:** forward that line to the CEO in chat (or answer the SomPong order),
  read the relay's result, and tell the worker via its mailbox when the
  session is live. If the mirror showed the page badly, you write the pattern (§4).
- **CEO:** taps the pill on https://terminal.mooniex.com/relay and logs in.

## 1. Expose the Chrome (one per account, a dedicated profile)

**Preferred since 2026-09-25: a Browser Home** — a headless Chrome the Console
on that box launches and owns, with every out-of-page prompt disabled, so the
relay sees 100% of what the site shows (Console docs/relay.md §8):

```bash
node scripts/relay-home.mjs create <id> --label "<account>" --url <login url>   # once
node scripts/relay-home.mjs launch <id>      # prints http://127.0.0.1:92xx — your CDP URL
```

It appears on the CEO's phone as "<machine> · <label>", and a stopped home is
an "เปิด" button there. A launch restores the profile's previous tabs — after
OAuth attempts the infisical home came back with three extra "Sign in - Google
Accounts" tabs, four pills (cto-885ae930 letter, 2026-09-26) — so close every
page but the login tab (`curl http://127.0.0.1:<port>/json/close/<id>`) and
count what is left, titles and ids only (§3). The hand-launched table below is
the exception (a site that refuses headless).

| machine | port | how |
|---|---|---|
| Contabo | 9222–9299 on 127.0.0.1 | `chrome --headless=new --remote-debugging-port=92xx --user-data-dir=<profile> --window-size=390,844 --user-agent="<a normal Chrome UA>"` — Google refuses the HeadlessChrome UA (E_BLOCKED, measured 2026-09-24) |
| Mac | 9222–9299 on 127.0.0.1 | `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=92xx --user-data-dir=<profile>`; each running Chrome costs a ~1.4 GB code-sign clone — quit it after the login |
| winbox | 9222–9299 on 127.0.0.1 | winbox runs a relay-only Console (task `MooniexConsole`, peer `winbox-4a7c2e91`) since 2026-09-25 — the ssh tunnel is gone. Preferred: a Browser Home — `cd C:\Users\passg\MoonieXHQ\Projects\MoonieX\Console && node scripts\relay-home.mjs launch <id>` (or the phone's เปิด button). A HEADED Chrome still needs the desktop scheduled-task recipe in memory `reference_winbox_desktop_chrome_relaunch` |

Never `--remote-debugging-address=0.0.0.0`, never the CEO's everyday profile,
never touch another CTO's automation Chrome without a letter first (IRON §33).
Ports already taken: Mac 9223 ChatGPT (8c06958c), Mac 9224 BL TikTok
(3d312dd6), Mac 9230 Facebook Dorsine Gobb / ILAG Page (95cbbb28, profile ~/.fb-automation/chrome-profile), winbox 9224 ChatGPT (8c06958c), winbox 9225 Google home, Contabo
9250 fake login test page, 9251 layout render rig.

**Keep the profile: it holds the CEO's login.** He wants to log in as seldom
as possible (CEO 2026-09-28: "ไม่อยาก login บ่อยไป ยกเว้นแต่ มันจำเป็นมากๆ"), so
reuse the account's existing profile or Browser Home and check whether it is
still signed in before you ask. Never delete a profile or its Cookies / Login
Data / Local Storage / IndexedDB / Session Storage without asking him first;
only its `Cache`, `Code Cache`, `GPUCache` are free (rule owner:
`ALL_Rules_DiskHygiene`).

## 2. Tell the CEO which pill

Open the login page in that Chrome first, then write in chat (or a
`[CEO via SomPong]` reply) the exact pill text: `<machine>:<port> — <tab title>`,
e.g. `winbox:9225 — Sign in - Google Accounts`, plus which account. A page that
does not look like a login sits under "Chrome อื่นที่กำลังทำงานอัตโนมัติ" and needs
two taps — say so. The relay then reports success/failure itself with an Error
ID (`RLY-…`, `data/relay-errors.jsonl` on the Console host) — read that, never
ask the CEO what he saw. Exception: a site that hands the login to Google,
GitHub, Microsoft, Apple, Facebook, Auth0 or Okta ("Continue with Google") —
a Console without d127273 (on Contabo's live main since 2026-09-25; the Mac and
winbox Consoles have it only once pulled) reports สำเร็จ on the provider's own
page (three times on contabo:9281). Tell the CEO the phone stays on that page;
the site's own dashboard is the success (§5).

## 3. Traps that are not the relay's fault

- **Chrome's own bubbles and OS windows are outside the page.** A permission
  bubble ("facebook.com wants to show notifications"), a save-password bubble,
  a sign-in intercept, a macOS Keychain prompt, Windows Hello or a passkey
  sheet: the screencast never shows them and a tap never reaches them. Prevent
  most of them at launch —
  `--disable-notifications --use-mock-keychain --no-first-run --no-default-browser-check`
  (`--use-mock-keychain` stops the macOS Keychain dialog the first Facebook
  login on mac:9230 raised) — the relay pre-denies web notifications for the
  login origin on its own. Google's passkey step is patterned (Continue
  disabled, "Try another way" preferred); steer flows to password/SMS. If a
  page freezes, the CEO's Reload button cancels the pending prompt; on a Mac
  the phone's **จอเครื่อง** button shows an OS-level capture of the Chrome
  window (Screen Recording granted to the Console once on that Mac).
- **"Sign in to Chrome" intercept.** After a Google login Chrome may open
  `chrome://signin-dice-web-intercept.top-chrome` as the FIRST page target: it
  adds a pill, and `relay-inspect` takes the first page unless given `--page
  <id>`. Pick the real tab by title (winbox:9225, GH MoonieX-Console#9).
- **HARD — on a login or token page, a driver prints tab titles and ids,
  never URLs or raw `/json/list`,** and closes a token-bearing tab by id right
  after use. Meta's Access Token Debugger carries the token in its own URL
  (`?access_token=…`); a worker's error that listed every tab URL printed a
  live user token into its transcript (task-5a0ed790).
  **Why hard:** a credential in a transcript cannot be unshown.
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
- Quit a Mac Chrome you started — the process, never its profile (§1). Leave
  winbox/Contabo ones only if the task keeps using them; say which port you left up.
- Report in your Skill learning what the mirror got wrong — that is where the
  next seed pattern comes from.

## Field notes
- 2026-09-25 [MISSING] rollout test: two live sessions (Mac cto-95cbbb28, Contabo cto-e1e3d3ef) got the letter cold and both answered in the §0 one-line format within 2 min (one real request — Facebook Dorsine Gobb on mac:9230 — one "not blocked"); the format needs no further explanation in the letter · evidence: GH MoonieX-Console#9 comment 2026-09-25 05:1x → §0 (confirms the line as written; no edit needed) · status: promoted
- 2026-09-25 [MISSING] after a Google login Chrome's own "Sign in to Chrome" intercept (`chrome://signin-dice-web-intercept.top-chrome`) shows up as the first page target, so `relay-inspect` and the pill list can pick it before the real tab; skip `chrome://` / `*.top-chrome` targets · evidence: winbox:9225 04:4x, GH MoonieX-Console#9 → §3 "Sign in to Chrome" intercept (relay-inspect still takes the first page target, Console 567c6f9) · status: promoted
- 2026-09-25 [MISSING] the mirror's first real-site login (Google on winbox:9225) is still unverified; the fake form on Contabo:9250 passed the CEO's test and winbox:9224 ChatGPT came up signed in after his phone flow · evidence: MoonieX-Console 62ea287, GH MoonieX-Console#9 — rejected: a later note records a real-site login through the relay (Facebook on mac:9230, 2026-09-25, session verified by CTO 95cbbb28) · status: rejected
- 2026-09-25 [MISSING] §1 Mac — the first Facebook login through the relay (mac:9230) raised a native macOS Keychain dialog the relay cannot show; start Mac automation Chromes with `--use-mock-keychain` (plus --no-first-run --no-default-browser-check). After the login the tab sat on facebook.com/two_factor/remember_browser/ with the session already valid (c_user + xs present) · evidence: CTO d7dca03f letter 05:24, CTO 95cbbb28 verified Business Suite for asset 1319535331240503 opens → §3 first bullet (flags were already there; incident added) and §5 confirm-from-your-side · status: promoted
- 2026-09-26 [WRONG] §2 "the relay then reports success/failure itself" — for a site that hands the login to Google ("Continue with Google") the default result rule ("off the login URL, stable 5 s") reported สำเร็จ on Google's own sign-in page, three times on contabo:9281 (Infisical). Fixed in Console d127273 (IDP_HOSTS: Google/GitHub/Microsoft/Apple/Facebook/Auth0/Okta pages hold the window open, notice "เว็บส่งไป login กับผู้ให้บริการอื่น"); shipped on Contabo's live main, the Mac owner must pull before the next ff ship. Until every box has it, tell the CEO the phone will stay on Google's page and that the site's own dashboard is the real success · evidence: cto-885ae930, letter docs/ops/letters/2026-09-26-cto-885ae930-to-console-owner-relay-idp-fix.md → §2 exception (fix d127273, artefact) · status: promoted
- 2026-09-26 [MISSING] §1 Browser Home — `relay-home.mjs launch` restores the profile's previous tabs: after OAuth attempts the infisical home came back with three "Sign in - Google Accounts" tabs plus the login tab, four pills on the phone. After a relaunch, `curl http://127.0.0.1:<port>/json/close/<id>` every page but the start URL and confirm `/json/list` shows one · evidence: cto-885ae930 22:09 CEST (same letter, item 2) → §1 Browser Home · status: promoted
- 2026-09-26 [COSTLY] §0 worker blocked on a login — two model workers each polled a login tab for 20–25 min (about 165k tokens) for a login the CEO did not do that night, and everything after the login still needed a model. What replaced it: a detached watcher (`scripts/infisical/watch_login.sh`: `wait_login.mjs --once` every 20 s, up to 12 h) that runs the post-login script and wakes the CTO's tmux pane with one line; the post-login work itself became API calls through the page's own session (`bootstrap_setup_identity.mjs`), so no model waits and none sees a value. A login wait is a shell loop, never a model · evidence: cto-885ae930 workers ac0e7ca4/ac561017, commit 297fa49c → §0 worker line · status: promoted
- 2026-09-26 [MISSING] §0 credentials in tab URLs — Meta's Access Token Debugger puts the debugged token in its own tab URL (`?access_token=…`). A worker's scratch CDP driver raised an "AMBIGUOUS tabs" error that listed every tab URL and printed a live user token into the transcript. Rule for any driver that touches a login/token page: print tab titles and ids only, never URLs or raw /json/list; close token-bearing tabs by id right after use · evidence: task-5a0ed790 REPORT.md line 32 → §3 HARD bullet (irreversible credential exposure) · status: promoted
- 2026-09-27 [MISSING] §0 scope — a Claude Code CLI login (`claude auth login`, needed before Remote Control works) is not a browser login the relay can serve. Over ssh the CLI shows the manual-code URL and waits for the code on stdin, so an agent would hold the auth code; steering the CLI's own browser-open into a relay Chrome was refused by the auto-mode classifier as a bypass (cto-3156a56c), and an interactive scheduled task to open a login window on the desktop was refused as persistence (cto-83a61127). Until Run Inbox P2 lands on winbox (the CEO types the code on the phone), the only route is a person at the desk: desktop shortcut "WINDOWS CTO", /login in its window, accept folder trust · evidence: cto-3156a56c + cto-83a61127 2026-09-27, winbox `claude auth status` loggedIn:false → intro scope line (CLI logins → ALL_Protocol_RunInbox); the "person at the desk" route is NOT folded — it contradicts RunInbox §Hosts (CEO 2026-09-26, commands from the phone only) and is on the CEO list · status: promoted
- 2026-09-28 [WRONG] §4 — "on the Console host (Contabo for winbox/Contabo Chromes)" is out of date: winbox has run its own relay-only Console since 2026-09-25 · evidence: relay-login §1 winbox row, the Console row in hq.yaml (fold worker, session 14cc900f) · status: pending
- 2026-09-30 [MISSING] §1 Browser Home — `node scripts/relay-home.mjs` is given without its repo: the script lives in MoonieX-Console (Mac `/Users/gob/MoonieXHQ/Projects/MoonieX/Console`, Contabo `/opt/MoonieXHQ/Projects/MoonieX/Console`), not Agents-Core. A browser_operator worker in an Agents-Core worktree looked for it there, concluded "scripts/relay-home.mjs does not exist", and drove the signed-out extension Chrome instead. Write the full path (run it in a subshell `(cd <Console> && node scripts/relay-home.mjs …)`) · evidence: task-195da9cc REPORT (Skill learning, 3rd line) · status: pending
- 2026-09-30 [MISSING] §0 CTO — the requesting CTO launched the champa Browser Home (mac:9280) 14 min AFTER delegating the browser_operator and never sent it the CDP URL, so the worker never knew a login Chrome existed. Launch the Browser Home before `delegate_task` and put `http://127.0.0.1:<port>` in the brief, or send it by mailbox the moment it is up · evidence: session 98e5101f (Sonnet 5.5 CTO) 06:13 delegate vs 06:27 launch, task-195da9cc · status: pending
- 2026-09-30 [WRONG] §2 "The relay then reports success/failure itself with an Error ID" — a drop at the Contabo peer proxy writes NO `RLY-…` row. What the CEO sees: every tap shows 4102 "เครื่องปลายทางตอบช้าหรือหลับอยู่"; what the Mac Console stdout log shows (`~/Library/Logs/mooniex-console-mac.stdout.log`): `session started` → `session ended` 0.4 s apart, over and over. Cause: `sendScanFrame()` sends an unbounded full-page PNG (1,117,791 B on champa.io) past the proxy's 1 MiB `PEER_WS_MAX_PAYLOAD`, and `proxy.js:165-166` maps every non-terminal close to 4102. Same 0.4 s pattern on flow.google.com mac:9223 2026-09-25. Until MoonieX-Console#12 lands, read the started/ended lines, not relay-errors.jsonl · evidence: session 98e5101f 06:33–06:40Z (7 sessions), GH MoonieX-Console#12 · status: pending
- 2026-09-30 [WRONG] §2/§3 — the phone text "เครื่องปลายทางตอบช้าหรือหลับอยู่" (close 4102) does not mean the peer is asleep or Tailscale is off: src/peer/proxy.js maps EVERY non-terminal upstream close to 4102. On mac:9280 the Mac accepted the session and closed it 0.4 s later because the first `scan:frame` (full-res PNG, 1,117,791 B on champa.io at 1280x757) exceeded the proxy's 1 MiB maxPayload (close 1009). Read the Mac's `[relay] session started/ended` lines before blaming the network; shrink the Browser Home window (800x700 = 579,571 B) as the workaround · evidence: session cto-8a3b20f6, GH MoonieX-Console#12, LungNote 42a1216f · status: pending
- 2026-09-30 [MISSING] §1 — a Browser Home is HEADLESS (`--headless=new`): there is no window on the desktop, so a CEO at the Mac who is told "Chrome is open" sees nothing; say so and point at the phone pill. Also the Chrome a worker drives through the claude-in-chrome extension has no CDP port and cannot be served by the relay: create a Browser Home (`node scripts/relay-home.mjs create <id> --label … --url …`, run from the Console repo) and have the worker drive it over CDP (worker's report: relay-home.mjs is absent from the agents worktree) · evidence: task-195da9cc (GH Agents-Core#187), relay-home champa pid 13942 · status: pending
