# Brief — IQ Option bot control panel, localhost first (MoonieX-Option `web/`)

CEO 2026-09-29: "เอา UX UI เดียวกันกับ MoonieX WebAPP มาใช้ได้เลย นะ — เราจะเปิดให้ใช้ใน
{prefix}.mooniex.com — ตอนนี้ mooniex.com vercel ยังไม่จ่ายเงิน คุณจำลองบน Localhost ให้ก่อน
เมื่อทดสอบแล้ว ใช้งานแล้วได้ผลจริง ค่อยเอาขึ้น Production + จ่ายเงิน"

Target domain later: `autotrade.mooniex.com` (CTO pick). **Nothing is deployed in this task** — no
Vercel, no DNS, no Supabase writes, no paid API. Localhost only.

## Job
CREATE a Next.js control panel in `web/` of MoonieX-Option that looks and feels like MoonieX WebApp,
runs on `http://localhost:3710`, and is fully usable today in **simulation mode** (no broker, no
network). The real trader will implement the same HTTP contract later (task T4); switching must be
one env var, not a rewrite.

## Look — copy MoonieX WebApp once, read-only
Read these by ABSOLUTE path (they are not in your worktree). Copy what you need into `web/`; never
import from, symlink to, or write into the WebApp folder. One-time vendored copy, no runtime link.

- `/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp/src/app/globals.css` — Tailwind v4 `@theme` tokens
  (brand navy `#0c1c2b`, sand `#cdac65`, surfaces, fg-1..3). Copy the token block; drop what you do not use.
- `/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp/src/app/layout.tsx` — fonts: Prompt, Inter, Manrope
  via `next/font/google`, same variables.
- `/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp/src/components/ui/` — button, card, badge, tabs,
  dropdown-menu, form-field, empty-state… (Radix + tailwind-merge). Copy only the ones you use.
- `/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp/src/components/dashboard/` — `Shell.tsx`,
  `Sidebar.tsx`, `TopBar.tsx`, `MobileDrawer.tsx`, `EquityCurve.tsx`: the dashboard layout pattern
  (navy sidebar, top bar, mobile drawer). Rebuild the same pattern for our pages; strip WebApp-only
  wiring (auth, credits, brokers, i18n, Sentry, Supabase).
- `/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp/src/components/brand/Wordmark.tsx` — MoonieX wordmark.

Same stack as WebApp: Next 16, React 19, TypeScript, Tailwind v4, Radix, `lucide-react`. Use pnpm.
Rules: **icons only, never emoji** in the UI (✓ ✕ ⏳ 🔒 ↗ count as emoji — use lucide). Thai-first
labels (the competitor app is Thai); numbers in tables. Must work at **390 px** phone width with no
horizontal scroll (`document.documentElement.scrollWidth === 390`). Next 16 dev: open
`http://localhost:3710`, not `127.0.0.1` (127.0.0.1 blocks dev resources and hydration hangs silently).

## Pages
1. **แดชบอร์ด** `/` — status cards: balance, session P/L, trades, win rate **with the break-even line
   `1/(1+payout)`** (54.1% at 85%) shown next to it, profit factor, max drawdown; account badge
   ("PRACTICE"); Start / Stop; equity curve; live trade list (time, asset, UP/DOWN, stake, result,
   profit, strategy, MM level, probe flag).
2. **ตั้งค่า** `/settings` — asset, expiry (sec), base stake, payout;
   strategy picker (4): `follow_prev` ตามตัวก่อนหน้า, `ping_pong` ตามปิงปอง, `pattern` ตามแพทเทิร์น
   (pattern text e.g. `UUUD` / `▲▲▲▼`), `wait_n_play_n` รอ n เล่น n (n, mode reverse|follow);
   MM picker (9): manual, martingale, anti_martingale, fibonacci, dalembert, labouchere, flat,
   oscars_grind, one_three_two_six, with maxStake / maxLevels, and a **ladder preview table**
   (the next 8 stakes on an all-loss streak and on an all-win streak) computed by the real
   `previewLadder` from `trader/mm`;
   probe trade (ไม้ตรวจ) on/off + probe stake; take-profit $ and stop-loss $ per session; max trades.
3. **รายงาน** `/reports` — past sessions (start, end, trades, W/L/D, win rate, P/L, PF, max DD,
   stop reason: tp|sl|max_trades|manual), one session's trade list, CSV download.

**Real money is off.** Show the account as PRACTICE / SIM only. There is no control that switches to a
real account — render it disabled with the text "บัญชีจริงปิดอยู่ — ต้องผ่าน 500 เทรด practice +
CEO อนุมัติ". A small risk line in the footer: "การเทรด binary option มีความเสี่ยงสูง อาจสูญเงินทั้งหมด".

## Data contract v0 — write it to `docs/control-api.md`
Base URL from env `TRADER_API_URL`. Unset = the built-in simulator (Next route handlers under
`web/app/api/sim/…` serving the same paths). All JSON, times ISO-8601 UTC.

| Method + path | Body / query | Returns |
|---|---|---|
| `GET /status` | — | `{ running, mode: "sim"\|"practice", balance, payout, session: { id, started_at, trades, wins, losses, draws, win_rate, break_even, pnl, profit_factor, max_drawdown }, current: { strategy, mm, level, next_stake } }` |
| `GET /config` | — | `Config` |
| `PUT /config` | `Config` | `Config` (400 + `{error}` on invalid; refuse while running) |
| `POST /start` | — | `{ running: true, session_id }` |
| `POST /stop` | — | `{ running: false, stop_reason: "manual" }` |
| `GET /trades` | `?session_id&limit` | `[{ id, at, asset, direction: "UP"\|"DOWN", stake, result: "win"\|"loss"\|"tie", profit, strategy, mm_level, probe }]` |
| `GET /sessions` | — | `[{ id, started_at, ended_at, trades, wins, losses, draws, win_rate, pnl, profit_factor, max_drawdown, stop_reason }]` |

`Config = { asset, expiry_sec, base_stake, payout, strategy: { name, params }, mm: { name, config }, probe: { enabled, stake }, tp_usd, sl_usd, max_trades }`

## Simulator (the "จำลอง" the CEO asked for)
- Random-walk candles (seeded, so a test can reproduce a run), one candle per tick; a UI speed setting
  (1× real time … 60×) so a 100-trade session can be watched in a couple of minutes.
- Decisions come from the **real** modules in this repo: `trader/strategies/index.js`
  (`createStrategy`), `trader/strategies/probe.js`, `trader/mm/index.js` (`createMM`, `previewLadder`),
  `trader/strategies/candles.js`. Import them read-only (CommonJS; you may need `createRequire` and
  a Turbopack/`outputFileTracingRoot` setting because they sit outside `web/`). **Do not edit
  anything under `trader/`** — another task owns `trader.js` right now.
- Win/loss = did the next candle close in the bet direction; tie on equal close; profit = stake×payout
  on win, −stake on loss. TP/SL/max_trades stop the session and record `stop_reason`.
- The MM can return a stake below the broker minimum (Oscar's Grind near its goal gives fractions of a
  unit): clamp every stake to `min_stake` (default $1) and show it in the trade row.
- State lives in memory plus a JSON file under `web/.data/` (gitignored) so a dev-server restart keeps
  the session list.

## Tests (append-as-you-go log: `docs/reports/<task-id>/PROGRESS.md`, one line per step)
- `web/` vitest: simulator math (win/loss/tie profit, TP/SL/max_trades stop, win rate, PF, max DD,
  break-even = 1/(1+payout), min-stake clamp); config validation; contract shapes. Expected numbers
  hand-written in the test, never computed by the code under test.
- Root suite must stay green: `node --test "test/**/*.test.js"` (do not add web tests to it).
- One Playwright (or headless Chrome) pass at 390 px and 1280 px on all 3 pages: save screenshots to
  `docs/reports/<task-id>/` and state the measured `scrollWidth`. Quit any browser you start.

## Report
`docs/reports/<task-id>/REPORT.md`: files, commands + counts, screenshots, how to run
(`cd web && pnpm install && pnpm dev` → `http://localhost:3710`), every assumption, and the usual
`## Skill learning` block.
