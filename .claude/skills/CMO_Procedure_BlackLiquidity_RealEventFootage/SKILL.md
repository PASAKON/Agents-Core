---
name: CMO_Procedure_BlackLiquidity_RealEventFootage
kind: procedure
owner: CMO
aka: [bl-real-event-footage]
description: 'PROCEDURE — Build 9:16 Mobile View real-event news broadcast & live web footage REFs for BLACK LIQUIDITY (Script-First, fact-checked, 0.00px centered Theme BL + Kanit highlight boxes, + credit pills on news only). Trigger on /CMO_Procedure_BlackLiquidity_RealEventFootage, "ทำ Footage BL จากเหตุการณ์จริง", "หา REF ข่าวจริง BL". Not for WikiFX censor.'
created_by: agent
author: {role: project_head, date: "2026-11-19"}
audience: [cmo, cto, developer, browser_operator, video_editor]
improved_by:
  - {role: project_head, date: "2026-11-22", what: "§8-§10 V7.5/V7.6 Daily Viral Real-Event Video Standard: No-account Viral Radar (TikTok yt-dlp + Reddit Arctic Shift), V7.6 2-Layer Storytelling Cover Architecture (Layer 1 Pure Storytelling Background without character + Layer 2 Chroma-Keyed Cutout RICH Narrator Sprite with 2.5D Parallax & 3D drop shadow + Layer 3 top:1215px 3-Layer Headline), 100% distinct story-specific frames per episode, real broadcast video + archival news integrated, ultra-minimal 3-5 words, raw กู/มึง Achird voice (fal-ai/gemini-3.8-flash-tts @ 1.24x + BL01 BGM), and Run + TikTok API + Telegram description delivery (CEO rulings Q-20261121-1814-2d43..Q-20261122-0911-ba7c)"}
  - {role: project_head, date: "2026-11-23", what: "§9/§Rules-9 Q-20261122-1706-dd92 1-Card Pure Auto-Clean Flow via CMO_Procedure_MoonieXPoster_Queue (removed Card [2/2])"}
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

6. **Render 100% Full-Bleed Image/Chart/Video (`0..1080, 0..1920`, zero black margins & zero outer border), keep ONLY our Text & Highlight Boxes inside the verified TikTok Safe Zone (`X = 65..918px, Y = 226..1690px`), and place the original `EP.1`–`EP.10` `#bug` Watermark Logo BL at `right: 150px, top: 310px` scaled down by 30% (`0.70×`) — CEO final ruling 2026-11-20.**
   - Measured across 5 real iPhone TikTok screenshots (`472×1024`, active video player `472×880` at `phone_y = 53..933`), TikTok iOS scales a `1080×1920` video by `933 / 1920 = 0.4859375`, cropping `X < 54.3px` on the left, `X > 1025.7px` on the right, and masking `Y < 109.1px` at the top status bar, with the top search bar at `Y = 121..223px`, right-side interaction icons at `X = 907..1008px`, and bottom caption/scrub UI below `Y = 1690px`.
   - Use the verified V6.6 Safe-Zone base (`X = 65..918px, Y = 226..1690px`) for all text and highlight boxes while extending the underlying photo, chart, or broadcast video **100% Full-Bleed (`0..1080, 0..1920`)** (`build_v6_7_fullbleed_safe_text_15s.py`):
     - **100% Full-Bleed Image / Chart / Video (`0..1080, 0..1920`, NO Black Margins & NO Outer `3px` Screen Frame)**:
       - `"ภาพ กราฟ และ Video ที่คุณเว้นขอบถือว่าโอเครแล้ว ใช้อันนี้เป็น Base ได้เลย แต่ภาพและ video ไม่ต้องเว้น บน ล่าง ซ้าย ขวา นะ ให้มันเต็มๆ จอได้เลย แต่ตัวหนังสือที่เราใส่ และการตีกรอบ ให้มันเว้นไว้ก็พอ"`
       - Seat the active focal content inside `X = 65..925px, Y = 356..1580px` (`860×1224px` uniform aspect ratio) and extend the native web page background or full-frame broadcast video continuously across the top (`Y = 0..356px`), bottom (`Y = 1580..1920px`), left (`X = 0..65px`), and right (`X = 925..1080px`) so the image/video fills 100% of `1080×1920` edge-to-edge with zero black bars and zero outer red frame.
     - **Exact Original `EP.1`–`EP.10` `#bug` Watermark Logo BL Style & Position (`right: 150px; top: 310px; align-items: flex-end;`), Scaled Down by 30% (`0.70×`)**:
       - `"ส่วน Black Liquidity Logo ใส่ให้เหมือนกับ EP อื่นๆ ก่อนหน้าได้เลยนะ ขนาดให้เล็กลง 30% ของ EP อื่นๆ ก็เช่นกัน แต่ตำแหน่งเดิมมันจะทับกับข้อมูลเล็กน้อยไม่เป็นไรนะ"`
       - Place `#bug` at `position: absolute; right: 150px; top: 310px; z-index: 45; display: flex; flex-direction: column; align-items: flex-end; gap: 7px;` with every `EP.1`–`EP.10` dimension scaled by `0.70×`:
         - `.bug .logo`: `60px × 0.70 =` **`42px`** (`height: 42px; width: auto;`)
         - `.bug .rl`: `74×5px × 0.70 =` **`52×3.5px`** (`background: #FF2D40`)
         - `.bug .dt2`: `24px × 0.70 =` **`17px`** (`padding: 2px 8px; border-radius: 5px; background: rgba(7,8,10,0.76);`)
     - **Safe-Zone Text & Highlight Boxes Only (`X = 65..918px, Y = 226..1690px`)**:
       - **Floating Top-Left `REF` + Credit Pill (`left: 68px; top: 226px;`)**: Translucent dark floating pill (`background: rgba(7,8,10,0.86); border: 2px solid #FF2D40`) below TikTok's search bar (`Y > 224px`), with no black header bar behind it.
       - **Highlight Boxes (`.hl-box`) & Callout Tags (`.hl-tag`)**: All mathematically centered (`0.00px` error) and clamped inside `X = 65..918px, Y = 360..1575px`.
       - **Spoken Subtitle Pill (`.cap`) & Legal Disclaimer (`.bl-legal`)**: Seat `.cap` at **`cy = 1618px`** (`left: 84px; right: 170px;`) and `.bl-legal` at **`top = 1668px`** (`left: 84px; right: 170px;`), floating cleanly over the full-bleed background above TikTok's bottom caption area.

7. **Rotate across the 5 Minimal Icon-Only News & Financial Storytelling Templates (`V7.0 StockRichter × BLACK LIQUIDITY Grammar`) so consecutive episodes never use the same visual template — CEO rulings 2026-11-21.**
   - Measured across 10 real `@stockrichter` videos (`01_TrumpThaiTariff` through `10_AppleDivergence`), every centered graphic uses an **optical horizontal center at `cx = 520px` (`left: 80px, width: 880px`)** inside the TikTok Safe Zone, alternating every `3.5–5.5s` between **Full-Bleed Real Photo/Video Beats** (with top-left chapter pill at `x = 90, y = 392`, left red-bar person nameplate `border-left: 8px solid #D4282D`, 2-part split keyword chip `[Dark Box | Solid Red Box]` at `y = 1170`, and clean dark subtitle card at `y = 1395`) and **Bespoke Dark Minimalist Vector Infographic Beats (`#0A0C10` + `#141923` radial glow)**.
   - **Strict Minimal & Icon-Only Rule (`"อย่าลืมนะว่าของเราต้อง Minimal และ ใช้ ICON แทน Emoji เท่านั้น"`)**:
     - **ZERO Unicode emojis** (`👑`, `⭐⭐⭐`, `🔥`, `💰`, `⚠️`, etc.) anywhere in headlines, badges, charts, or checklists.
     - Always use **Minimal Vector SVG Icons (`stroke-width: 2.2..2.6`, `#FFFFFF` / `#F4DF14` / `#FF3B47`)** or the channel's **Minimal Neon Red-Gold Rim PNG Icons** (`.claude/skills/CMO_Procedure_BlackLiquidity_Cut/assets/icons/01_target.png` .. `09_padlock.png`).
   - **The 5 Rotating V7.0 Minimal News Templates (Never repeat the same template on two consecutive episodes)**:
     - **Template 1 — `Domino Chain & Podium Crash` (โดมิโนล้มต่อเนื่อง + แท่น Podium เปรียบเทียบ)**:
       - *Best for*: Multi-factor market crashes & macro chain reactions (e.g., `EP.12` Tech Stocks ➔ Bond Yields ➔ Fed Chair Warsh ➔ Gold `-43,500 จุด`).
       - *Signature Visuals*: `4-Layer Hook Poster` (`0–4.4s`) ➔ `Diagonal Red Slash Wipe` ➔ `3-Bar Podium Comparison (#1 / #2 / #3 with Minimal SVG Star/Crest Icon above #1)` ➔ `4-Domino Tipping Chain Animation` ➔ `Bespoke SVG Crash Line Chart` ➔ `High-Impact News Console (with Minimal SVG Bar-Chart Icon)` ➔ `3-Row Numbered Checklist`.
     - **Template 2 — `Balance Scale & Cost Breakdown Stack` (ตาชั่งใครได้-ใครเสีย + แท่งชำแหละโครงสร้างต้นทุน)**:
       - *Best for*: Trade deals, tariff shocks, broker fee exposes (`Spread + Swap + Commission`), or two-sided winners vs losers (`ใครได้ vs ใครเสีย`).
       - *Signature Visuals*: `4-Layer Hook Poster` ➔ `Broadcast Quote Overlay (Crimson SVG Quote Mark + English/Thai Quote)` ➔ `Animated SVG Balance Scale (ตาชั่งเอียงเทียบ 2 ฝั่ง)` ➔ `Animated Vector Coin Flow Arc ($0 ➔ $2,600M)` ➔ `Stacked Cost Breakdown Bar (แท่งสี่เหลี่ยมแยกชั้นสีขาว/เทา/แดง ชำแหละต้นทุนทีละชั้น)`.
     - **Template 3 — `Order Ticket & System Terminal Log` (หน้าจอส่งคำสั่งซื้อขาย + กราฟแท่งสัดส่วนสุดขั้ว + Terminal Error)**:
       - *Best for*: Flash crashes, fat-finger trades, Stop Hunt / Liquidity Sweep mechanics, and B-Book broker execution traps.
       - *Signature Visuals*: `4-Layer Hook Poster` ➔ `Bespoke Minimal Order Ticket UI (SYMBOL · XAUUSD [SELL/BUY], Lot Size, Price)` ➔ `Extreme Ratio Horizontal Bar (เทียบสภาพคล่องจริง 1x vs คำสั่งกวาดล้างพอร์ต ~42 เท่า)` ➔ `Dark System Terminal Log (> ORDER ACCEPTED / > STOP LOSS TRIGGERED / > CANCEL ... FAILED)` ➔ `V-Reversal SVG Line Chart`.
     - **Template 4 — `Head-to-Head VS & Schematic Reveal` (เทียบ 2 ขั้ว VS + ไดอะแกรมเส้นขาวเปิดโปงกลไกเบื้องหลัง)**:
       - *Best for*: Hype vs reality, Ponzi/scam broker anatomy, overvalued bubble vs real cash flow, or a single speech/event that wiped out `-90%`.
       - *Signature Visuals*: `4-Layer Hook Poster` ➔ `Giant Price Drop Counter ($100 ➔ $9 / −90% with Red Underline)` ➔ `Head-to-Head VS Power Bars (เทียบ 2 ฝั่งพร้อมแถบสัดส่วนแนวนอน)` ➔ `Minimal Red-Bordered Evidence Frame` ➔ `White-Line Vector Schematic Diagram on #0A0C10 (ไดอะแกรมเส้นขาว Minimal เฉลยกลไกเบื้องหลัง)`.
     - **Template 5 — `Vicious Cycle Loop & Danger Threshold Line` (วงจรอุบาทว์ 3 จังหวะ + กราฟเส้นทะลุขีดอันตราย + การ์ดโปรไฟล์เขียว/แดง)**:
       - *Best for*: Trading psychology traps (Revenge Trading, Overtrade, Margin Call spiral) and macro debt/interest-rate spirals.
       - *Signature Visuals*: `4-Layer Hook Poster` ➔ `Green vs Red Profile Split Cards (การ์ดขอบเขียว vs ขอบแดง พร้อม Minimal Vector Profile/Brain Icon)` ➔ `Danger Threshold SVG Line Chart (กราฟเส้นสีแดงพุ่งทะลุเส้นประแนวนอน "เส้นอันตราย")` ➔ `3-Node Circular Vicious Cycle SVG (ลูกศรโค้ง 3 ทิศทางหมุนวนเป็นวงกลมระหว่าง 3 กล่อง)` ➔ `3-Node Supply/Liquidity Radar Map`.

8. **Build Daily Viral Real-Event Episodes (`V7.5 Standard`: No-Account Viral Radar + `RICH` Character Cover + 100% Distinct Story Frames + Real Broadcast/Archival Footage + Raw `กู / มึง` `Achird` Voice + Ultra-Minimal Text) — CEO rulings 2026-11-21 & 2026-11-22.**
   - **Step 8a · Discover Viral Financial Stories Without Login (`bl_viral_radar.py`)**:
     - Scan viral TikTok finance creators via `yt-dlp --dump-json --flat-playlist` and public Reddit threads (`r/Gold`, `r/Forex`, `r/stocks`, `r/Economics`, `r/wallstreetbets`) via the zero-account Arctic Shift API (`https://arctic-shift.photon-reddit.com/api/posts/search`).
     - Rewrite the viral topic 100% originally in BLACK LIQUIDITY's structure: **Real Historical/Current Financial Scandal or Market Shock (`65%`) ➔ Direct Retail Gold (`XAUUSD`) / Forex / Crypto Trading Trap & 3 Survival Rules (`35%`)**.
   - **Step 8b · V7.6 2-Layer Storytelling Cover (`0.00–7.5s`, 2.5D Parallax Composite) & Story Scene Plates (`Q-20261122-0911-ba7c`)**:
     - **Never generate the Cover in a single flat pass with a plain dark background behind `RICH`.** Build every episode's opening cover (`0.00–7.5s`) as a **True 2-Layer Composite (`build_v7_6_2layer_cover_15s_demo.py`)** inspired by `Ghost Rules` storytelling thumbnails:
       - **Layer 1 · Pure Storytelling Background Plate (`1080×1920`, generated WITHOUT `RICH` in the prompt)**:
         - Tells the entire story of the episode in one vivid, high-contrast scene (e.g., for `EP.13` Tokyo Stock Exchange: the blazing crimson circular ticker ring at `y = 180..465px` at the top, `SELL 610,000 @ ¥1` on the left wall, `CANCEL FAILED` on the right wall, and panicked Japanese traders clutching their heads on the left & right desks at `y = 650..1020px`, leaving the center aisle open for Layer 2).
       - **Layer 2 · Chroma-Keyed Cutout `RICH` Narrator Sprite (`layer2_rich_narrator_cutout_rgba.png`)**:
         - Our recurring narrator **`RICH`** (mid-20s Western male, black rectangular sunglasses, black ribbed knit beanie with bold white `"RICH"` patch on the front cuff, white polo collar under a sharp black blazer) extracted from a pure `#00FF00` chroma-green studio plate with green-spill suppression (`extract_rich_layer2_rgba()`), cropped to his tight alpha bounding box, scaled to **`width = 630..650px`** (centered at `cx = 525px`), and seated with his beanie top at **`y = 468..472px`** (and bottom 18% torso smoothly alpha-ramped into the `#0A0C10` lower third).
         - This exact geometry guarantees: (a) the upper background focal point (`y = 180..465px`) sits 100% clear **above** `RICH`'s beanie, (b) left and right background story elements (`x = 55..220px` and `x = 830..1020px`) remain 100% visible **around** `RICH`'s shoulders, and (c) the `"RICH"` beanie patch sits at `y = 540..605px`, far below TikTok's top search bar (`y < 224px`).
       - **2.5D Parallax & 3D Contact Shadow (`composite_2layer_parallax_frame()`)**:
         - Cast a soft Gaussian drop shadow (`51×51`, `sigma=20`, `0.62` opacity) from Layer 2 onto Layer 1, and animate independent parallax zoom (`Layer 1 Background` scales `1.000× ➔ 1.055×` while `Layer 2 Foreground RICH` scales `630px ➔ 650px` width and lifts `-8px`).
       - **Layer 3 · Approved 3-Layer Cover Headline (`top: 1215px`) & Top-Right `#bug` Dated BL Logo (`right: 150px, top: 310px`)**:
         - Seated cleanly over the smooth dark lower-third vignette (`bot_start_y = 1145px`).
   - **Step 8c · 100% Distinct Episode-Specific Visual Frames (Keep the BL Theme, NEVER Reuse Previous Episode Frames)**:
     - Keep the BLACK LIQUIDITY Theme (`#0A0C10` obsidian canvas, `#D4282D` crimson & `#F5B841` gold accents, `Kanit` + `JetBrains Mono`, top-right `#bug` Gold Crest Logo at `right: 150px, top: 310px` scaled `0.70×` with the daily date `22 NOV 2026` .. `26 NOV 2026`, diagonal crimson slash wipes, 2-part Split Keyword Chip `[Dark Box | Red Box]`, and single-line bottom subtitle pill at `y = 1395`).
     - **Build 100% bespoke visual frames for each episode's specific narrative** — never copy the previous episode's graphic frames (`"โทนโอเคแล้ว แต่อย่าทำ frame ให้เหมือนกันแบบนี้ ลองดูช่องนี้ แต่ละคลิปเขาแตกต่างกันนะ"`). Proven 5-day slate examples:
       - `EP.12` (`22 NOV 2026`): Gold & Stocks Simultaneous Crash (`3-Bar Podium`, `4-Domino Chain`, `Warsh Quote`, `XAUUSD -$43,500 pts Curve`).
       - `EP.13` (`23 NOV 2026`): Mizuho / J-Com Fat-Finger (`Swapped White/Crimson Order Form 610,000 @ ¥1`, `~42 เท่า Supply Shock Bar`, `> CANCEL ... FAILED Terminal`, `0.10 vs 10.00 Lot MT5 Comparison`).
       - `EP.14` (`24 NOV 2026`): 2010 Flash Crash & Bedroom Spoofing (`-998.5 PTS Plunge Meter`, `Wall Street Suspect vs Bedroom Trader Reality`, `2-Column BID vs $200M ASK Spoof Order Book Ladder`, `3-Step 0.01s Spoof-Cancel-Buy Loop`).
       - `EP.15` (`25 NOV 2026`): 15-Second Pre-Release Newswire Hack (`-15 SEC Server Upload vs 20:30:00 Public Release`, `Hacker-to-Trader Syndicate Flow`, `0.002s Fiber Laser vs 1.500s Mobile Latency Bars`, `15 -> 450+ pts Broker Spread Gauge`, `Dual-Wick Whipsaw Candle`).
       - `EP.16` (`26 NOV 2026`): Bill Hwang / Archegos `$20B` Margin Call (`Hidden Total Return Swaps Card`, `6-Bank 5x Leverage Matrix -> 3.5 ล้านล้าน`, `ViacomCBS -9% to -23% Averaging-Down Waterfall`, `6-Bank Backstabbing Race`, `0.10 -> 0.80 Lot Martingale Death Spiral`).
   - **Step 8d · Weave Real Moving Broadcast Footage & Archival News Captures into Every Episode**:
     - Include 2–3 real moving broadcast news clips (`@BloombergTV`, `@NipponTVNews24`, `@AssociatedPress`, `@Reuters`, `@BloombergBusinessweek`) cropped full-bleed `9:16` with `apply_stockrichter_vignette()`, top-left red chapter pill + `ขอบคุณภาพจาก @Handle`, and 2-part Split Keyword Chip, plus 1 archival newsprint + court/DOJ indictment card (`REAL_*.jpg`) so viewers immediately see the story is based on a real event (`"แบบนี้เลย เพิ่มเติม footage จริงลงไปด้วยนะ จะดีมากเลย คนจะได้รู้ว่ามาจากเรื่องจริง"`).
   - **Step 8e · Ultra-Minimal On-Screen Text (3–5 Words Max) & Never Stack Split Chips on `#0A0C10` Graphic Scenes**:
     - Limit every center graphic row to **3–5 words max** so viewers read it in 1 second (`"และที่สำคัญ minimal นะดีที่สุด บางช่วง ข้อความเยอะ user อ่านไม่ทันและอ่านไม่หมด"`).
     - Show the 2-part Split Keyword Chip (`[Dark Box | Red Box]`) **only** on `RICH` full-bleed plates, archival news cards, and real broadcast video clips — **never** stack a Split Keyword Chip on top of a `#0A0C10` bespoke graphic scene.
   - **Step 8f · Authentic Channel Voice (`Achird` via `fal-ai/gemini-3.8-flash-tts`) in Raw Hard-Hitting `กู / มึง` Tone**:
     - Synthesize all voiceovers via `tools/fal_tts.py` on `mooniex-contabo` with `model: "fal-ai/gemini-3.8-flash-tts"` and `voice: "Achird"` (never `edge_tts`) in raw, punchy `กู / มึง` friend-warning-friend tone (`"แต่เสียงต้องใช้แบบเดิมนะ อย่าลืม ... ขอสไตล์ดุดันกว่านี้นะ มี กูมึง จริงๆ"`).
     - Post-process each segment with `silenceremove=start_periods=1:start_silence=0.06:start_threshold=-38dB:stop_periods=-1:stop_duration=0.14:stop_threshold=-38dB,atempo=1.24,loudnorm=I=-14.0:TP=-1.5:LRA=11,apad=pad_dur=0.45`, mix the 17 CEO-approved Mass SFX (`mix_track_with_17sfx`), and mix `BL01` BGM via `tools/bgm_bed.py --track BL01` to `-14.0 LUFS`.

9. **Verify every full-size `9:16` still and `4×2` iPhone TikTok UI simulation sheet by eye, then submit the episode into the shared 1-Card `CMO_Procedure_MoonieXPoster_Queue` pipe (`tools/mooniex_poster.py submit --channel "Black Liquidity" --account black_liquidity ...`).**
   - First, inspect the `4×2` iPhone TikTok UI simulation sheet (`sheet_EP*_V7_6_*_iphone_sim.jpg`) via `read_file`.
   - Submit the master video, `t=2.5s` cover JPG, and pure 5-hashtag description via `tools/mooniex_poster.py submit` (`bl-flow-daemon.service` on `mooniex-contabo`):
     - **Single Review Card (`ตรวจคลิป & ยืนยันลง TikTok` — `Q-...` with `--media black_liquidity_EPxx.mp4 --expires-h 168`)**:
       - **Option 1 (`ยืนยัน — ส่งขึ้น TikTok Draft + ส่งปก & Description เข้า Telegram`)**: `bl-flow-daemon.service` runs automatically (`0` AI tokens): (1) refreshes any expiring token and uploads the video ONLY to TikTok API `--draft` (`SEND_TO_USER_INBOX`) or queues in `QUEUED_FOR_TIKTOK_SLOT` until the rolling 24-hour slot opens; (2) ONLY after TikTok accepts, sends `cover.jpg` with the 100% pure copy-ready Description (`≤5` `#tags` starting with `#blackliquidity`, NEVER sending the `.mp4` video) to Telegram; (3) sends 1 unread **`MoonieX Poster`** Gmail (`พร้อมโพสต์! [Black Liquidity] EP.X ...`); and (4) **immediately logs completion in `bl_completed_log` and auto-deletes staged files + the `bl_episodes` row with zero second card** (`Q-20261122-1706-dd92`).
       - **Option 2 (`แก้ไข / ทำใหม่`)**: wakes the AI session via `tools/send_to_agy.py` with the CEO's revision note to rebuild the clip and re-submit until approved.

## Rules

1. **HARD — Never search for or capture real-event footage before the episode script and its clause-level claim table are written and locked (CEO ruling 2026-11-19).**
   **Why hard:** scope and wasted work — hunting real footage without a locked script forces re-shoots when the script's spoken clauses change (`"รอบหน้าแนะนำให้เขียนบทก่อนนะ เวลาหา Footage จริงจะได้หาตามบทที่มี จะดีกว่า"`).

2. **HARD — Never include unverified or outdated real-person/news footage; verify current officeholders, dates, and on-screen figures before presenting any REF (CEO ruling 2026-11-19).**
   **Why hard:** safety and channel credibility — using an outdated clip (such as calling Jerome Powell the current Fed Chair in November 2026 when Kevin Warsh is Fed Chair, or showing 2018 `$1,200` gold prices during a 2026 `$4,157 ➔ $3,722` crash) destroys viewer trust (`"ก่อนจะส่งข้อมูล ช่วยค้นหาหน่อยว่าข้อมูลนั้นมันเป็นความจริงแค่ไหน ก่อนจะเอามาใช้เป็น Footage เดี๋ยวคนดูจะว่าเอานะ"`).

3. **HARD — Never guess highlight box coordinates by eye; every highlight box must be computed from the target's exact pixel ink bounds (`pad_L == pad_R`, `pad_T == pad_B`, `center_err == 0.00px`, zero letter overlap) (CEO ruling 2026-11-19).**
   **Why hard:** scope — CEO explicitly rejected eye-guessed boxes that sit off-center or cross through letters (`"จะได้เป็น Center จริงๆ ช่องว่าง บน ล่าง ขวา ซ้าย ต้องเท่ากัน จุดที่เน้น ต้องอยู่ตรงกลาง อย่าให้ทับตัวอักษร"`).

4. **HARD — Render the underlying image, chart, or broadcast video 100% Full-Bleed (`0..1080, 0..1920`, zero black margins and zero outer `3px` red screen border), keep ONLY our text overlays and `.hl-box` highlight frames inside the verified TikTok Safe Zone (`X = 65..918px, Y = 226..1690px`), and place the exact `EP.1`–`EP.10` `#bug` Watermark Logo BL at its original position (`right: 150px; top: 310px; align-items: flex-end;`) scaled down by 30% (`0.70×`: logo `42px`, red bar `52×3.5px`, date `17px`) (CEO final ruling 2026-11-20).**
   **Why hard:** readability & brand consistency — the CEO confirmed the `V6.6` safe-zone positioning works as the Base for focal content, text, and highlight boxes, but directed that the background photo/chart/video itself must fill 100% of the screen without top/bottom/left/right margins or an outer screen border, and `#bug` must sit at its exact `EP.1`–`EP.10` position (`right: 150px, top: 310px`) at `-30%` size (`"ส่วน Black Liquidity Logo ใส่ให้เหมือนกับ EP อื่นๆ ก่อนหน้าได้เลยนะ ขนาดให้เล็กลง 30% ของ EP อื่นๆ ก็เช่นกัน แต่ตำแหน่งเดิมมันจะทับกับข้อมูลเล็กน้อยไม่เป็นไรนะ ต่อมาคือ ภาพ กราฟ และ Video ที่คุณเว้นขอบถือว่าโอเครแล้ว ใช้อันนี้เป็น Base ได้เลย แต่ภาพและ video ไม่ต้องเว้น บน ล่าง ซ้าย ขวา นะ ให้มันเต็มๆ จอได้เลย แต่ตัวหนังสือที่เราใส่ และการตีกรอบ ให้มันเว้นไว้ก็พอ"`).

5. **HARD — Keep all bespoke V7.0/V7.5 infographics strictly Ultra-Minimal (3–5 words max per card/row, zero stacked Split Chips on `#0A0C10` graphic scenes), use Custom Vector SVG / PNG Icons ONLY (NEVER Unicode Emojis), and build 100% distinct story-specific visual frames for every episode so no two episodes share the same graphic frames (CEO rulings 2026-11-21 & 2026-11-22).**
   **Why hard:** brand identity & viewer retention — Unicode emojis (`👑`, `⭐⭐⭐`, `🔥`) break BLACK LIQUIDITY's dark institutional aesthetic (`"อย่าลืมนะว่าของเราต้อง Minimal และ ใช้ ICON แทน Emoji เท่านั้น"`), dense text blocks cannot be read in 1 second (`"และที่สำคัญ minimal นะดีที่สุด บางช่วง ข้อความเยอะ user อ่านไม่ทันและอ่านไม่หมด"`), and reusing the previous episode's graphic frames makes consecutive videos look identical (`"โทนโอเคแล้ว แต่อย่าทำ frame ให้เหมือนกันแบบนี้ ลองดูช่องนี้ แต่ละคลิปเขาแตกต่างกันนะ"`).

6. **HARD — Always use the authentic channel voice `Achird` on `fal-ai/gemini-3.8-flash-tts` (`tools/fal_tts.py`, post-processed at `atempo=1.24` and `-14.0 LUFS` with `BL01` BGM) in raw `กู / มึง` tone, open every episode with the V7.6 2-Layer Storytelling Cover (`0.00–7.5s`: Layer 1 pure storytelling background scene generated without `RICH` + Layer 2 cutout `RICH` narrator sprite at `width = 630..650px, y_top = 468..472px` with 2.5D parallax & 3D drop shadow + Layer 3 headline at `top: 1215px`), and integrate real moving broadcast footage + archival news captures into every episode (CEO rulings 2026-11-22, `Q-20261122-0911-ba7c`).**
   **Why hard:** spend & channel identity — substituting a generic TTS voice (`edge_tts`) was rejected immediately by the CEO (`"แต่เสียงต้องใช้แบบเดิมนะ อย่าลืม"`), a single-layer cover with a plain dark background fails to tell the episode's story at a glance (`"ปกคลิปจะทำเป็นเหมือนตัวบอกว่าเนื้อหาที่ผู้ชมจะเจอมีอะไร บอกเล่าในภาพเดียว ส่วนตัวละคร Rich จะเป็นเหมือนผู้เล่าเรื่อง ... ทำภาพพื้นหลังมาแล้วเอาตัวละครไปซ้อนไว้ฉากหน้าอีกรอบจะสวยมากนะ เป็น 2 Layer"`), and real broadcast/archival footage is mandatory so viewers know every episode is grounded in a real event (`"แบบนี้เลย เพิ่มเติม footage จริงลงไปด้วยนะ จะดีมากเลย คนจะได้รู้ว่ามาจากเรื่องจริง"`).

7. Put `ขอบคุณภาพจาก @SourceA + @SourceB` (separated by `+`, never `.`) ONLY on news agency / broadcast footage; omit credit pills on public web apps (`TradingView`, `ForexFactory`, `TradingEconomics`, `Investing.com`) that anyone can capture directly.

8. Format all stills (`1080×1920`) and video previews (`540×960` / `1080×1920`) in `9:16` Vertical Mobile View, cropping horizontal `16:9` videos strictly around their focal regions with uniform aspect ratio (`scale_x == scale_y`).

9. **HARD — Deliver every episode through the 1-Card Zero-Trigger Auto-Publish & Auto-Cleanup Flow (`CMO_Procedure_MoonieXPoster_Queue` / `tools/mooniex_poster.py` -> `bl-flow-daemon.service` on `mooniex-contabo`): 1 Review Card (`Q-...` with `--media`) previews the video and, upon approval, (1) uploads the video ONLY to TikTok API `--draft` (queuing automatically across rolling 24h slots if full), (2) ONLY after TikTok succeeds, sends `cover.jpg` with the pure 5-hashtag Description (`#blackliquidity` first, NEVER sending the `.mp4` video) to Telegram, (3) sends 1 unread `MoonieX Poster` Gmail (`พร้อมโพสต์! [Black Liquidity] EP.X ...`), and (4) immediately auto-deletes staged files and clears the `bl_episodes` row with zero second card (CEO rulings 2026-11-22 & 2026-11-23, `Q-20261122-1706-dd92`).**
   **Why hard:** operator speed, zero token waste & TikTok 5-pending-share safety — never send duplicate videos to Telegram, only wake the AI when Option 2 (`แก้ไข / ทำใหม่`) is tapped, and never add a redundant `[2/2]` confirmation card because TikTok's 5-clip/24h quota unlocks strictly by server timestamp (`"ตัดใบ [2/2] ออกเลย — ส่งเข้า TikTok+TG+Gmail เสร็จแล้วเคลียร์ตาราง Auto ทันที"`).

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
- **2026-11-20 (Black top/bottom/side margins around footage vs full-bleed background + `#bug` position/scale)**: Shrinking footage into a floating center box (`V6.5`) or leaving black top/bottom header/footer bars (`V6.6`) reduced screen immersion. Fixed in `V6.7` (`build_v6_7_fullbleed_safe_text_15s.py`) by keeping the verified `V6.6` safe zone (`X = 65..918px, Y = 226..1690px`) as the Base for all focal data, highlight boxes (`.hl-box`), callout tags (`.hl-tag`), floating `REF` pill, subtitle (`.cap`), and legal disclaimer (`.bl-legal`), while extending the background image/chart/video 100% full-bleed across `0..1080, 0..1920` with zero black margins and zero outer red frame, and placing the `EP.1`–`EP.10` `#bug` Watermark Logo BL at its original position (`right: 150px; top: 310px; align-items: flex-end;`) scaled down by 30% (`0.70×`: logo `42px`, red bar `52×3.5px`, date `17px`).

## Field notes

- 2026-11-20 [MISSING] §6/§Rules-4 — CEO final ruling on 100% Full-Bleed Image/Chart/Video (`0..1080, 0..1920`, zero black margins and zero outer `3px` screen border), keeping ONLY text overlays and `.hl-box` highlight boxes inside the verified TikTok Safe Zone (`X = 65..918px, Y = 226..1690px`), and restoring the exact `EP.1`–`EP.10` `#bug` Watermark Logo BL position (`right: 150px; top: 310px; align-items: flex-end;`) scaled down by 30% (`0.70×`: logo `42px`, red bar `52×3.5px`, date `17px`) · evidence: build_v6_7_fullbleed_safe_text_15s.py → §6, §Rules-4 · status: promoted
- 2026-11-21 [MISSING] §7/§Rules-5 — CEO ruling on adopting `@stockrichter` script and editing grammar into 5 rotating V7.0 Minimal Icon-Only News Templates (`Template 1` Domino Chain & Podium Crash, `Template 2` Balance Scale & Cost Breakdown Stack, `Template 3` Order Ticket & System Terminal Log, `Template 4` Head-to-Head VS & Schematic Reveal, `Template 5` Vicious Cycle Loop & Danger Threshold Line), strictly Minimal and using Custom Vector SVG / PNG Icons ONLY (zero Unicode Emojis) · evidence: build_v7_0_stockrichter_style_draft.py → §7, §Rules-5 · status: promoted
- 2026-11-22 [MISSING] §8/§Rules-5/§Rules-6 — CEO rulings across the 5-day viral slate (`EP.12`–`EP.16`, `22–26 NOV 2026`): (1) never use `edge_tts`; always use `fal-ai/gemini-3.8-flash-tts` voice `Achird` at `1.24x` in raw `กู / มึง` tone with `BL01` BGM; (2) open with signature `RICH` character cover (`top: 1215px` 3-layer headline, `"RICH"` beanie patch clear at `y = 360..460px`); (3) keep graphics ultra-minimal (3–5 words max, no Split Keyword Chip stacked on `#0A0C10` graphic scenes); (4) make every episode's visual frames 100% distinct to its story while keeping the BL theme; (5) weave real broadcast footage + archival news captures into every episode · evidence: Q-20261121-1814-2d43, Q-20261121-1905-c1b3, Q-20261121-1946-baf1, Q-20261121-2020-f52b, Q-20261122-0810-d333 → §8, §9, §Rules-5, §Rules-6 · status: promoted
- 2026-11-22 [MISSING] §8b/§Rules-6 — CEO ruling on V7.6 2-Layer Storytelling Cover Architecture (`Q-20261122-0911-ba7c`, `"ผ่านเลย! ใช้โครงสร้างปก 2 Layer นี้ใน Skill และทุกคลิปต่อไป"`): generate Layer 1 as a pure full-frame storytelling background scene (with no `RICH` inside the prompt) that tells the episode's entire story in one picture, and composite Layer 2 (`layer2_rich_narrator_cutout_rgba.png`, chroma-keyed `#00FF00` cutout of `RICH` as the foreground storyteller, scaled to `width = 630..650px` at `cx = 525px, y_top = 468..472px` with 3D drop shadow and independent 2.5D parallax zoom) in front of Layer 1 so top/left/right background story details remain 100% visible around `RICH` · evidence: build_v7_6_2layer_cover_15s_demo.py, Q-20261122-0911-ba7c → §8b, §Rules-6 · status: promoted
- 2026-11-22 [MISSING] §9/§Rules-9 — CEO ruling on Zero-Trigger Auto-Publish & Auto-Cleanup Flow (`Q-20261122-1208-14fb`, `bl_flow_manager.py` / `bl-flow-daemon.service` on `mooniex-contabo`) *(Card 2 `[2/2]` `[SUPERSEDED 2026-11-23]` by `Q-20261122-1706-dd92`)* · evidence: /opt/MoonieXHQ/Work/bl-tiktok-queue/bl_flow_manager.py, Q-20261122-1208-14fb → §9, §Rules-9 · status: promoted
- 2026-11-23 [WRONG] §9/§Rules-9 — CEO ruled in `Q-20261122-1706-dd92` (`"ตัดใบ [2/2] ออกเลย — ส่งเข้า TikTok+TG+Gmail เสร็จแล้วเคลียร์ตาราง Auto ทันที"`) to eliminate Card `[2/2]` so 1 Clip = 1 Review Card via `CMO_Procedure_MoonieXPoster_Queue` · evidence: Q-20261122-1706-dd92 → §9, §Rules-9 · status: promoted
