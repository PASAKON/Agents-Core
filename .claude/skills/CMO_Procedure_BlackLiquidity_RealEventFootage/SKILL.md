---
name: CMO_Procedure_BlackLiquidity_RealEventFootage
kind: procedure
owner: CMO
aka: [bl-real-event-footage]
description: 'PROCEDURE — Build 9:16 Mobile View real-event news broadcast & live web footage REFs for BLACK LIQUIDITY (Script-First, fact-checked, 0.00px centered Theme BL + Kanit highlight boxes, + credit pills on news only). Trigger on /CMO_Procedure_BlackLiquidity_RealEventFootage, "ทำ Footage BL จากเหตุการณ์จริง", "หา REF ข่าวจริง BL". Not for WikiFX censor.'
created_by: agent
author: {role: project_head, date: "2026-11-19"}
audience: [cmo, cto, developer, browser_operator, video_editor]
improved_by: []
---

# BLACK LIQUIDITY Real-Event Footage — 9:16 Mobile View News & Live-Web REFs

Input: A locked BLACK LIQUIDITY episode script (`CMO_Standard_BlackLiquidity_Script`) with its clause-by-clause claim list · Output: Verified `9:16` Vertical Mobile View (`1080×1920`) stills (`curated_stills/REF*.jpg`), a `4×2` `9:16` Master Board, and a `28s` `9:16` (`540×960`) moving video preview reel with `0.00px` auto-centered `Theme BL + Kanit` highlight boxes · Tool: `tools/bl_real_event_refs.py`

When a BLACK LIQUIDITY episode explains a real market crash, central-bank decision, or economic-calendar tutorial (such as `EP.11` `XAUUSD` `-43,500 จุด` crash & Fed Chair Kevin Warsh speeches), viewers need to see authentic real-human news broadcasts and real live web screens (`TradingView`, `ForexFactory`, `TradingEconomics`, `th.investing.com`) formatted in `9:16` Mobile View with dead-center `Theme BL` highlight boxes that prove each spoken line. This procedure builds and verifies that package before cutting the episode (`CMO_Procedure_BlackLiquidity_Cut`).

## When to invoke

- Preparing real-event news broadcasts, real-person speeches (e.g., Federal Reserve Chair, Bloomberg/CNBC/C-SPAN clips), or live financial-web tutorial screens (`TradingView`, `ForexFactory`, `TradingEconomics`, `Investing.com`) for a BLACK LIQUIDITY episode.
- The CEO asks for `"ทำ Footage BL จากเหตุการณ์จริง"`, `"หา REF ข่าวจริง BL"`, `"หา Footage จริง คนจริง"`, or `"สอนเช็คข่าวจากเว็บจริง"`.

## When NOT to invoke

- Capturing a broker's website or WikiFX watchdog profile that requires PII, promo, and competitor-broker pixelation censorship: use `CMO_Procedure_RealFootageCapture` (`tools/bl_realfootage.py`).
- Generating AI B-roll plates (`Veo 3.1` / `Flow Omni 1.2` / `Seedance`) or cutting the final timeline: use `CMO_Procedure_BlackLiquidity_Cut`.

## Steps

1. **Write and lock the script FIRST (Script-First Gate — CEO ruling 2026-11-19).**
   - Always write the episode script (`CMO_Standard_BlackLiquidity_Script`) and break it into numbered spoken clauses/claims **before** searching for or capturing any real-event footage (`"รอบหน้าแนะนำให้เขียนบทก่อนนะ เวลาหา Footage จริงจะได้หาตามบทที่มี จะดีกว่า"`).
   - Map every spoken claim that needs real-world proof to a specific `REF ##` slot (`covers: ["CLAUSE-ID"]`) so the visual on screen and the spoken words match 1:1 (`"ที่สำคัญคือ ภาพกับเนื้อหาต้องตรงกันด้วย"`).
   - *Stop if* no script or clause-level claim table exists yet: write and lock the script first instead of hunting random news clips.

2. **Fact-check current truth and verify video metadata (`ffprobe` + chyron check — CEO ruling 2026-11-19).**
   - Verify current officeholders, dates, and market numbers before downloading footage. Never assume old officeholders still hold office (for example, in November 2026 the Federal Reserve Chair is **Kevin Warsh**, who succeeded Jerome Powell in May 2026; gold `XAUUSD` trades at `$3,722–$4,157/oz`, not 2018's `$1,200/oz`).
   - Run `ffprobe` on every downloaded video clip to verify its upload/creation year and inspect the on-screen broadcast chyron (`FEDERAL RESERVE CHAIR KEVIN WARSH`, date, yield/price figure) at full resolution.
   - *Stop if* a clip comes from an outdated year or contradicts current facts. Replace it immediately before building base frames.

3. **Build `9:16` Vertical Mobile View (`1080×1920`) base canvases with dedicated Top/Bottom `Theme BL` zones.**
   - Every card uses a `1080×1920` (`9:16`) canvas divided into:
     - **Top Header Zone (`y = 0..116`, height `116px`)**: Dedicated Obsidian `#07080A` header with `3px solid #FF2D40` bottom divider, holding the `REF ##` badge, title, and (on news broadcast footage only) the credit pill.
     - **Active Footage Viewport (`y = 116..1804`, `1080×1688`)**: The clean web screen or focal-cropped video frame — never covered by the top header or bottom footer.
     - **Bottom Footer Zone (`y = 1804..1920`, height `116px`)**: Dedicated Obsidian `#07080A` footer with `3px solid #FF2D40` top divider, holding the `Theme BL` takeaway summary pill.
   - **For live public web apps (`TradingView.com`, `TradingEconomics.com`, `th.investing.com`)**:
     - Capture natively in a `9:16` mobile viewport (`viewport={"width": 540, "height": 960}, device_scale_factor=2` -> `1080×1920`) via Playwright + Google Chrome (`executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`).
     - Remove all login/cookie/app-download overlays (`Google One-Tap` iframes, `ดาวน์โหลดแอป Investing.com ฟรี!`) from the DOM via `page.evaluate(...)` before taking the screenshot.
   - **For horizontal `16:9` videos (`Bloomberg`, `Yahoo Finance`, `C-SPAN`, `Federal Reserve`, `ForexFactory` screen recordings)**:
     - Crop **only the focal region(s)** (`"ถ้า Video มันแนวนอน เราสามารถ Crop เอาเฉพาะส่วนที่เป็นจุดเน้นได้นะ"`) into the `1080×1688` active viewport using strictly uniform aspect-ratio scaling (`scale_x == scale_y`).
     - When combining a speaker portrait with a wide lower-third broadcast chyron (`FEDERAL RESERVE CHAIR KEVIN WARSH...` or `WARSH CONTENDS WITH BOND MARKET PRESSURE`) or splitting a two-column dialog (`ForexFactory` `Expected Impact` vs `Currencies`), split cleanly along the exact boundary coordinate so **zero letters are clipped** and **no headless torso of the same camera angle is duplicated**.

4. **Compute every highlight box mathematically with OpenCV (`tools/bl_real_event_refs.py measure`).**
   - Never guess highlight box coordinates `(bx, by, bw, bh)` by eye.
   - Run `tools/bl_real_event_refs.py measure` on the `1080×1920` base image with a scoped search `--roi rx0,ry0,rx1,ry1`:
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python tools/bl_real_event_refs.py measure \
       --image mobile_base_1080x1920/mob_base02.jpg \
       --roi 80,1500,475,1600 --pad-x 16 --pad-y 12 --rule white_190
     ```
   - The detector finds the exact foreground ink pixels `(ix0, iy0, ix1, iy1)`, asserts positive 4-side clearance from the ROI boundary (`min(cL, cR, cT, cB) >= 1` so no letter is clipped by the search window), and computes:
     - `bx = ix0 - pad_x - 5`
     - `by = iy0 - pad_y - 5`
     - `bw = (ix1 - ix0 + 1) + 2 * (pad_x + 5)`
     - `bh = (iy1 - iy0 + 1) + 2 * (pad_y + 5)`
     guaranteeing **`pad_L == pad_R == pad_x`**, **`pad_T == pad_B == pad_y`**, and **`center_err == (0.00px, 0.00px)`**.
   - Place the floating callout pill (`hl-tag`) **outside** the highlight box (`top`, `bottom`, `left`, or `right`), never overlapping the highlighted letters.

5. **Render with `Theme BL + Kanit` (30% smaller text) and apply the Credit Pill Rule.**
   - **Font**: Embed local `Kanit` (`600` SemiBold & `800` ExtraBold) via `@font-face`.
   - **30% Smaller, Optically Centered Text**:
     - Header title: `22.5px` (`font-weight: 800`, `#F4F6F7`)
     - Credit pill: `16.5px` (`font-weight: 600`, `#F4DF14`)
     - Floating callout tag (`hl-tag`): `18.5px` (`font-weight: 800`, `#F4DF14`, `height: 36px`, `display: inline-flex; align-items: center; justify-content: center`)
     - Bottom takeaway pill (`bot-pill`): `21.5px` (`font-weight: 800`, `#F4DF14`, `height: 72px`)
   - **High-Contrast Double-Keyline Highlight Frame (`Theme BL`)**:
     - `border: 3.5px solid #FF2D40; outline: 1.5px solid #07080A; box-shadow: 0 0 0 2px rgba(7,8,10,0.92), inset 0 0 0 1.5px rgba(7,8,10,0.85), 0 0 14px rgba(255,45,64,0.55)` so the red highlight frame is unmistakably visible on both white web pages and red/orange TV chyrons.
   - **Credit Pill Rule (`ขอบคุณภาพจาก` — CEO ruling 2026-11-19)**:
     - **Public web apps anyone can access (`TradingView`, `ForexFactory`, `TradingEconomics`, `Investing.com`)**: Omit `ขอบคุณภาพจาก` completely (`credit: None`).
     - **News agencies & copyrighted broadcasts (`Bloomberg TV`, `Yahoo Finance`, `C-SPAN`, `Federal Reserve`, `CNBC`, `Reuters`)**: Include `ขอบคุณภาพจาก @SourceA + @SourceB` using **` + `** as the separator (never `.` or `·`).

6. **Verify every full-size `9:16` still by eye, build the `4×2` Master Board & `9:16` Moving Video Preview Reel, and send to `/run`.**
   - Run `tools/bl_real_event_refs.py verify --dir <episode-refs-dir>` and inspect every rendered `1080×1920` still via `read_file`.
   - Render transparent `1080×1920` RGBA Playwright overlays (`omit_background=True` with `.bg { display: none; }`) and alpha-composite them over the real `24 fps` moving focal-cropped video frames to produce the `9:16` (`540×960`) moving video preview reel (`< 900 KB`) for `/run` approval (`tools/ask_run.py ask`).

## Rules

1. **HARD — Never search for or capture real-event footage before the episode script and its clause-level claim table are written and locked (CEO ruling 2026-11-19).**
   **Why hard:** scope and wasted work — hunting real footage without a locked script forces re-shoots when the script's spoken clauses change (`"รอบหน้าแนะนำให้เขียนบทก่อนนะ เวลาหา Footage จริงจะได้หาตามบทที่มี จะดีกว่า"`).

2. **HARD — Never include unverified or outdated real-person/news footage; verify current officeholders, dates, and on-screen figures before presenting any REF (CEO ruling 2026-11-19).**
   **Why hard:** safety and channel credibility — using an outdated clip (such as calling Jerome Powell the current Fed Chair in November 2026 when Kevin Warsh is Fed Chair, or showing 2018 `$1,200` gold prices during a 2026 `$4,157 ➔ $3,722` crash) destroys viewer trust (`"ก่อนจะส่งข้อมูล ช่วยค้นหาหน่อยว่าข้อมูลนั้นมันเป็นความจริงแค่ไหน ก่อนจะเอามาใช้เป็น Footage เดี๋ยวคนดูจะว่าเอานะ"`).

3. **HARD — Never guess highlight box coordinates by eye; every highlight box must be computed from the target's exact pixel ink bounds (`pad_L == pad_R`, `pad_T == pad_B`, `center_err == 0.00px`, zero letter overlap) (CEO ruling 2026-11-19).**
   **Why hard:** scope — CEO explicitly rejected eye-guessed boxes that sit off-center or cross through letters (`"จะได้เป็น Center จริงๆ ช่องว่าง บน ล่าง ขวา ซ้าย ต้องเท่ากัน จุดที่เน้น ต้องอยู่ตรงกลาง อย่าให้ทับตัวอักษร"`).

4. Put `ขอบคุณภาพจาก @SourceA + @SourceB` (separated by `+`, never `.`) ONLY on news agency / broadcast footage; omit credit pills on public web apps (`TradingView`, `ForexFactory`, `TradingEconomics`, `Investing.com`) that anyone can capture directly.

5. Format all stills (`1080×1920`) and video previews (`540×960` / `1080×1920`) in `9:16` Vertical Mobile View, cropping horizontal `16:9` videos strictly around their focal regions with uniform aspect ratio (`scale_x == scale_y`).

## Verify

```bash
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python tools/bl_real_event_refs.py verify \
  --dir /Users/gob/MoonieXHQ/Assets/BlackLiquidity/ep11-real-news-refs
```
Done looks like:
- Every `REF*.jpg` prints `PASS: REF... -> 1080x1920 (9:16 Mobile View)`.
- Every highlight box prints `pad_L == pad_R`, `pad_T == pad_B`, `clearance >= 1` on all 4 sides, and `center_err=(0.00px,0.00px)`.
- The moving preview video prints `PASS: ... -> 540x960 (9:16 Mobile View)` and every full-size still has been inspected via `read_file`.

## Failure modes seen

- **2026-11-19 (Outdated YouTube search hits)**: Searching YouTube for `"CNBC gold drop dollar"` without `"2026"` / `"Kevin Warsh"` returned a 2018 CNBC clip (`$1,200/oz`) and a 2023 Jerome Powell clip. Fixed by checking `ffprobe` `creation_time: 2026-...` and verifying the on-screen chyron (`FEDERAL RESERVE CHAIR KEVIN WARSH`, `Nov 16, 2026`, `US 30-YEAR YIELD 5.1993`).
- **2026-11-19 (Non-uniform crop aspect ratio & eye-guessed coordinates)**: Cropping a non-16:9 rectangle and resizing to `1280×720` distorted `y` coordinates, and hand-estimated boxes touched letters. Fixed by uniform-aspect-ratio focal cropping into `1080×1920` (`9:16`) and running `measure_exact_ink_box()` with a 4-side ROI boundary clearance assertion (`min(cL, cR, cT, cB) >= 1`).
- **2026-11-19 (2-panel split of the same camera angle)**: Splitting a single podium shot into top and bottom halves produced a headless torso of Kevin Warsh in the bottom half, and splitting `ForexFactory` with overlapping `x` ranges duplicated columns. Fixed by cropping the bottom strip strictly to the wooden podium seal + official lower-third chyron (`y = 462..698`), and splitting `ForexFactory` cleanly along the exact column divider (`x = 782` on Filter, `x = 730` on Specs vs History).

## Field notes
