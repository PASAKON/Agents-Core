---
from: cto-885ae930 (Contabo, Infisical secrets migration)
to: the MoonieX-Console owner (Mac session 01BxbhEeqbaQnJQroQnDAA4g) and cto-d7dca03f (relay author, closed)
date: 2026-09-26 (04:1x TH)
kind: heads-up — one commit sits on Contabo's live Console main; pull it before the next Mac→Contabo ship
---

# Relay: "Continue with Google" was reported as สำเร็จ — fixed on Contabo's live main (d127273)

**What happened (measured 03:30 TH, contabo:9281, Infisical login).** The CEO tapped *Continue with
Google*. The tab went to `accounts.google.com`, and the relay's default result rule ("off the login
URL, stable 5 s") read that as a successful login: `result:success` after ~14 s while he was still
on Google's sign-in page. Three tries, three false successes. The CEO: "ทั้งที่มันไม่สำเร็จจริง".

**Fix (`src/relay/sites.js` + `src/relay/manager.js`, +2 tests, 35/35 relay tests green).**
- `IDP_HOSTS` + `isIdentityProviderHost()` in sites.js: accounts.google.com, github.com, gitlab.com,
  login.microsoftonline.com, login.live.com, appleid.apple.com, facebook.com, auth0.com, okta.com.
- In `runResultCheckTick`: while the page is on one of those (and the login site is not that provider
  itself, so a Google login on accounts.google.com is unchanged), it is neither "off the login URL"
  nor a 45 s timeout — the result window is pushed forward each tick, and the phone gets one
  `result:challenge` notice: "เว็บส่งไป login กับผู้ให้บริการอื่น (เช่น Google) ทำต่อได้เลย". Success
  fires when the tab is back on the site.

**How it was shipped.** Committed directly on `/opt/MoonieXHQ/Projects/MoonieX/Console` main as
`d127273` (the live checkout was `556b963`, 25 ahead of GitHub) and `systemctl restart mooniex-console`
at 22:09 CEST with 0 sessions worth keeping (the CEO's own stuck one). Contabo cannot push to GitHub
(dead token), so **your next `push ssh://mooniex-vps` + ff-merge will not fast-forward until you pull
`d127273` into the Mac's main first.** `git -C Console log -1 d127273` on the box shows it.

**Two more things I saw, not fixed:**
1. The full vitest run on the box fails 19 *files* at collection: `process.getBuiltinModule('node:sqlite')`
   is undefined under plain `/opt/node-v22/bin/node` (needs `--experimental-sqlite`, as the deploy memory
   says). No individual test fails; the relay files run clean.
2. A relaunched Browser Home restores its previous tabs (Chrome session restore): after the false
   successes the `infisical` home came back with three `Sign in - Google Accounts` tabs plus the login
   tab, so the phone showed four pills. `relay-home.mjs launch` could pass `--no-restore-session-state`
   / close every page but the start URL after launch; I closed the extras over `/json/close/<id>` by hand.

Context: Agents-Core `docs/design/secrets-infisical/PLAN.md` (CEO-approved 2026-09-25) and LungNote
todo f60ff5d5.
