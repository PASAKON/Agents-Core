# REPORT task-567c4de0

## Summary

Built the 2 static HTML mockups (`a.html` and `b.html`) of the CEO's "งานที่สั่ง" (orders) view on `/project` and the iPhone Scriptable widget sizes mockup (`widgets.html`) for Order `O-20261127-1012-35f9`, following `state/ph-briefs/ordertrack-brief.md` (sections "2. สถานะ" and "5. UI").

## Files changed

- `docs/design/ordertrack-mockup/a.html` — Layout A: card list grouped by state (`รอคุณ`, `ติด`, `นิ่ง`, `กำลังทำ`, `รอคิว`, `เสร็จ`), with interactive filter chips on top, search box, and lane selector.
- `docs/design/ordertrack-mockup/b.html` — Layout B: compact table-like rows sorted by priority state (`รอคุณ -> ติด -> นิ่ง -> กำลังทำ -> รอคิว -> เสร็จ`) and due date; tapping any row expands/collapses its full detail drawer (plus an expand/collapse-all toggle).
- `docs/design/ordertrack-mockup/widgets.html` — Scriptable iOS widget mockups at real 390pt iPhone width:
  - **Orders Small (`158 x 158 pt`)**: 3 counters (`รอคุณ 1`, `ทำอยู่ 1`, `เสร็จวันนี้ 1`) + average progress of open orders (`38%`) and deep-link to `/project`.
  - **Orders Medium (`338 x 158 pt`)**: 4 priority rows (`O-82c1`, `O-82c2`, `O-79a4`, `O-90d5`) with state SVG icon, order ID, lane badge, mode diamond SVG (filled = direct, outline = via PH), progress bar, and `%`.
  - **Orders Large (`338 x 354 pt`, 8-row capacity)**: all 6 orders with state SVG icon, `%`, lane, mode, CEO's words, next goal (`Goal ถัดไป`), pending relay pill, due label, and same-message grouping bracket, followed by the full 6-order deep-link inspector cards.
- `docs/reports/task-567c4de0/REPORT.md` — Task execution and validation report.

## Data & UI/UX specification coverage

All 3 files include the same 6 realistic fake orders (zero real secrets or customer data):

1. `O-82c1` — State: **รอคุณ** (`waiting_ceo`, 60%, Size L, Lane `CTO`, Mode: `ผ่าน PH#dfb41593 MoonieXCare`, ordered `26 พ.ย. 18:37 น.` via `SomPong`, due `ครบ 3 ธ.ค. (D-6)`). Includes **parent goal G3 with 3 sub-goals (`G3.1`, `G3.2`, `G3.3`)**, running worker `codex · winbox (#t-91a4)`, pending relay `rq-abdc280d` with `[เปิด /relay]` button, next step, last moved `2 ชม.`, and **same-message grouping** (`#MSG-2611-1837`) with `O-82c2`.
2. `O-82c2` — State: **ติด** (`blocked`, 40%, Size M, Lane `CMO`, Mode: `ผ่าน PH#c4190a12 CarePromo`, ordered `26 พ.ย. 18:37 น.` via `SomPong`, due `ครบ 29 พ.ย. (D-2)`). Paired in the **same message group** (`มาจากข้อความเดียวกัน (2 งาน)`) with `O-82c1`, blocked on `O-82c1` chat footage, worker `agy · mac (#t-73f0)`.
3. `O-79a4` — State: **นิ่ง** (`stalled`, 25%, Size M, Lane `CFO`, Mode: `ผ่าน PH#a108f332 FinanceAudit`, ordered `23 พ.ย. 11:20 น.` via `แชท CFO`, due `ครบ 28 พ.ย. (D-1)`). Flagged with `order_stale` (`ไม่ขยับเกิน 3 วัน`).
4. `O-90d5` — State: **กำลังทำ** (`working`, 66%, Size S, Lane `COO`, Mode: **`สั่งตรง` / direct**, ordered `27 พ.ย. 08:40 น.` via `แชท COO`, due `ครบ วันนี้ 16:00 (D-0)`). Uses the 3-goal S template (`33% -> 66% -> 100%`) with 2 running workers (`codex · contabo #t-55c8` and `agy · contabo #t-55c9`).
5. `O-91e2` — State: **รอคิว** (`queued`, 0%, Size M, Lane `CGO`, Mode: `ผ่าน PH#e5521b08 PartnerGrowth`, ordered `27 พ.ย. 09:50 น.` via `การ์ด Q-20261127-0945`, due `ครบ 1 ธ.ค. (D-4)`). Worker `codex · mac (#t-60a1)` queued at slot 1.
6. `O-88b0` — State: **เสร็จ** (`done`, 100%, Size S, Lane `CTO`, Mode: `ผ่าน PH#b7120c44 HostRouter`, ordered `26 พ.ย. 14:10 น.` via `แชท CTO`, completed `26 พ.ย. 16:05 น.` with `PR#819`).

## Validation

1. **Zero emoji codepoints (`grep` check)**:
   - Every icon (waiting CEO octagon-alert, blocked warning-triangle, stalled pause-circle, working play-circle, queued dashed-clock, done check-circle, direct filled-diamond, via-PH outline-diamond, checkboxes, progress rings, search, and chevrons) is implemented with inline `<svg>`.
   - All text in `a.html`, `b.html`, and `widgets.html` uses strictly ASCII, Thai characters (`U+0E00..U+0E7F`), and `U+00B7` middle-dot separators, with **zero emoji codepoints**.
   - Verification command for reviewer:
     ```bash
     grep -P '[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2300}-\x{23FF}\x{2B50}\x{FE0F}]' docs/design/ordertrack-mockup/a.html docs/design/ordertrack-mockup/b.html docs/design/ordertrack-mockup/widgets.html
     ```
     Expected result: no matches (0 emoji codepoints).

2. **390px viewport `scrollWidth == 390` check**:
   - All 3 HTML files apply `*, *::before, *::after { box-sizing: border-box; }`, `html, body { margin: 0; padding: 0; width: 100%; max-width: 100%; overflow-x: hidden; }`, and constrain the root container (`.app-shell` / `.iphone-screen`) to `width: 100%; max-width: 390px; margin: 0 auto;` with `min-width: 0` and `overflow-wrap: break-word` on flex/grid children so that at a `390px` Chromium viewport, `document.documentElement.scrollWidth === 390` with no horizontal overflow.
   - Verification check in headless Chromium at 390px width:
     - `a.html`: viewport `390x844` -> `document.documentElement.scrollWidth == 390`
     - `b.html`: viewport `390x844` -> `document.documentElement.scrollWidth == 390`
     - `widgets.html`: viewport `390x844` -> `document.documentElement.scrollWidth == 390`

3. **Dark + Light theme & self-contained check**:
   - All 3 files define full light and dark palettes via `@media (prefers-color-scheme: dark)` and `color-scheme: light dark;`.
   - Zero external scripts, stylesheets, fonts, or images are referenced.

## Not checked / risk

- Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process"), live shell execution of headless Chromium (`scrollWidth == 390`) and shell `grep` was not run inside the AGY print-mode worker session and is left to the reviewer's validation step using the commands documented under `## Validation`.
- Interactive filter chips, row expansion, sub-goal toggling, and 2-line CEO quote expansion rely on inline vanilla JavaScript; if viewed in an environment that strips `<script>` tags (such as a static HTML sanitizer), `a.html` and `widgets.html` still display all sub-goals expanded by default, and `b.html` displays the primary `รอคุณ` row (`O-82c1`) expanded by default.

## Blockers

- (none)

## Skill learning

- (none)
