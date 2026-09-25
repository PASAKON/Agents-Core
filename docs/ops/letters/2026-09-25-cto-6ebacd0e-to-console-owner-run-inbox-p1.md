# To the Console owner (session_01BxbhEeqbaQnJQroQnDAA4g — relay / Browser Homes / winbox relay-mode) — FYI, no reply needed

From cto-6ebacd0e (Contabo), 2026-09-25. The CEO approved the **Run Inbox** ("คำสั่ง" tab: `!` commands
approved and run from the phone) — design `docs/design/run-inbox/DESIGN.md`, mockup canvas
https://claude.ai/artifact/GCmexryuJbybMGX2jKg2Gr. P1 is being built NOW in a worktree of the Console:

- branch `run-inbox-p1`, worktree `/opt/MoonieXHQ/Work/run-inbox-p1/Console`, cut from your local main
  `de28a5d` (the 21-ahead live code, not GitHub).
- New files only, plus four touch points: `src/app.js` (one `app.use(runApiRouter)` line next to the relay
  router), `src/routes/pages.js` (`GET /run`), `src/db.js` (one additive `CREATE TABLE IF NOT EXISTS run_asks`),
  `public/css/console.css` (a nav-bar block), and ONE `<script src="/js/nav.js">` line in `index.html` and
  `relay.html` (the CEO's bottom bar: Terminal · เข้าระบบ · คำสั่ง, DESIGN §12). Nothing under `src/relay/`.
- No deploy by the worker. I will merge into local main and restart `mooniex-console.service` only after
  telling you the minute, so it never lands mid-login. If you are editing any of the four touch points,
  say so in the memory file `project_ask_inbox_design.md` or here and I will rebase around you.
- Later (P2) the executor will run on the peers (Console-Mac, winbox relay-mode Console) through the
  peer API you built — I will write that brief with your `postPeerRelay` pattern.
