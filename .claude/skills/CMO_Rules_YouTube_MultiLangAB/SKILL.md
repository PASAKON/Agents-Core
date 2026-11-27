---
name: CMO_Rules_YouTube_MultiLangAB
kind: rules
description: >-
  RULES — Mandatory YouTube multi-language publish & A/B/C test rules for Jade Tally (YT: คลิปจีน): 3 universal covers (A/B/C), 3 A/B/C titles per language (6 langs = 18 titles), and zero AI words/tells in descriptions or tags. Trigger on /CMO_Rules_YouTube_MultiLangAB, "Jade Tally", "ลูกคิดประเมินฟ้า", "A/B Test ชื่อคลิป", "ปกสากล", "ปล่อยคลิปจีน".
owner: CMO
audience: [cmo, cto, cgo]
created_by: agent
author: {role: cmo, date: "2026-11-09", agent: "Antigravity (AGY session f22cf62a)"}
improved_by:
  - {role: cmo, date: "2026-11-09", what: "Authored by Antigravity (AGY session f22cf62a) per CEO ruling 2026-11-09: 3 Universal A/B/C Thumbnails, 3 A/B/C Titles in all 6 languages (18 titles/ep), zero AI mentions/AI-tells in descriptions & tags, and automated validate_publish_pack.py gate"}
  - {role: cmo, date: "2026-11-16", what: "Updated Rule 1 per CEO ruling Q-20261116-0618-8b22: Jade Tally A/B/C covers now use the GhostRules thumb_text.py skill (left-aligned 2-line Prompt hook text + left dark gradient) + Top-Center EPx pill badge + Top-Right Real Jade Tally Circular Channel Logo (setD_avatar_800.png), and the same real circular logo is used as the top-right watermark in all episode videos"}
  - {role: cmo, date: "2026-11-16", what: "Promoted Rule 6 to HARD Release Timing & Pre-Indexed Schedule rule from 2026-11-16 Studio Analytics across EP01-EP04: 12:00-14:00 GMT+7 (EP02 13:58 = 36,000 impressions, 4,304 views) or 19:00-23:30 GMT+7 (EP01 23:28 = 28,000 impressions, 1,467 views, 214.1h watch time); strictly ban 00:00-11:00 GMT+7 (EP03 00:14 = 1,300 impressions, 260 views; 05:21 = 5 impressions)"}
aka: []
---

# YouTube Multi-Language Publish & A/B/C Test Rules — Jade Tally (`ลูกคิดประเมินฟ้า` / `YT: คลิปจีน`)

> **Authored by:** Antigravity (`AGY` session `f22cf62a`) on **2026-11-09** per explicit CEO ruling (*"เขียนเป็นกฏให้หน่อยได้ไหม ว่า ปกต้องมี 3 แบบ และชื่อ A/B Test ต้องมี 3 ชื่อ ในทุกๆ ภาษา และห้ามพลาดอีก ... เอาใส่และ Update ไว้ใน Skills ดีกว่าไหม แล้วรายงานด้วยว่าคุณเป็นคนเขียนไว้ CMO จะได้รู้"*).

This skill governs every episode published on the multi-language 3D Chinese cultivation/fantasy YouTube channel **Jade Tally (`@JadeTally`, channel ID `UCR_-P9I4Cyp5iDCltw7fk5w`, Drive branch `ALL DRAFT/YT: คลิปจีน/`)**. It binds the **CMO**, **CTO**, **CGO**, and any worker or AGY session preparing, cutting, translating, or publishing an episode.

## When to invoke / when NOT to

- **Invoke** before designing thumbnails, writing titles/descriptions, uploading audio tracks, or setting any video on **Jade Tally (`YT: คลิปจีน`)** to `PUBLIC` (`สาธารณะ`).
- **Do NOT invoke** for `RED SEAL ARCHIVE` (`@redsealarchive`, which uses its own 8-language + 6 foreign audio tracks pipeline in `CMO_Standard_GhostChannel_DNA`) or for single-language Thai channels (`BLACK LIQUIDITY`, `บ้านนี้มีมีมี่`, `เอาชีวิตรอดกับข้าวหอม`), which follow their own workflow skills (`CMO_Workflow_BlackLiquidity`, `CMO_Workflow_MimiPage_Weekly`, `CMO_Workflow_KhaoHomEpisode`).

## Rules

1. **HARD — Every episode must ship with 3 `GhostRules`-Style A/B/C Thumbnails (`ep0X_univ_A.jpg`, `ep0X_univ_B.jpg`, `ep0X_univ_C.jpg` at `1280x720`) built with the `thumb_text.py` skill + Top-Center `EP<N>` Badge + Top-Right Real Jade Tally Channel Logo (`Q-20261116-0618-8b22`).**
   - **Layout & Typography (`GhostRules` `thumb_text.py` standard)**:
     - **Left Dark Gradient**: `a = int(190 * max(0.0, 1 - x / (W * 0.58)) ** 1.35)` on the left half so the 2-line Thai hook text pops cleanly while the character/treasure on the right (`x = 600..1260`) stays the hero.
     - **2-Line Hook Text (`Prompt` font, left-aligned at `X = 52`)**:
       - Line 1: `Prompt-SemiBold.ttf` (`56px`, White `#F5F2EB`)
       - Line 2: `Prompt-Bold.ttf` (`74–128px` auto-fitted to `≤ 575px` width, Red `#E61E24` or Gold `#FFD74B`) with soft Gaussian drop shadow (`GaussianBlur(7)`), no heavy stroke outline.
     - **Top-Center `EP<N>` Pill Badge (`Center`, `x = 640, y = 24`)**: Bold white `EP1` / `EP2` / `EP3` / `EP4` (`Prompt-Bold 62px`) inside a rounded crimson pill (`#C31616`) with a `4px` gold border (`#FFD74B`).
     - **Top-Right Real Channel Logo (`x = 1280 - 118 - 28, y = 24`)**: The official Set D Jade Tally circular emblem (`setD_avatar_800.png` cropped to its gold ring -> `jade_tally_real_logo_circle.png`, `118x118` px). This exact circular channel logo (`82x82` on `720p` / `116x116` on `1080p`) must also be used as the persistent top-right watermark in every episode video (never a text pill like `@JadeTally`).
   - `[SUPERSEDED 2026-11-16 by Q-20261116-0618-8b22]` Previous Rule 1 (`2026-11-09`): *"Every episode must ship with 3 Universal International A/B/C Thumbnails containing zero local-language sentence banners + top-right corner ribbon EP1/EP2/EP3 + Variant B bottom-center appraisal twist HUD."*
   - All 3 A/B/C covers are uploaded into YouTube Studio's **A/B/C Test (`การทดสอบ A/B` -> `ชื่อและภาพปก` `chip-2`)**.
   **Why hard:** scope — CEO ruling `Q-20261116-0618-8b22` (*"แผ่นปก ปรับ EP4 ให้อยู่ Center ได้ไหม แล้ว Logo มุม ขวาบน ใส่ Logo จริงๆ ของ ช่องแบบเดียวกับ Ghost Rule ได้ไหม อันนั้นมันไม่ใช่ Logo ช่องนะ ... ปกคลิปอยากให้ใช้ Skills เดียวกัน กับ Ghost Rule ทำได้ไหม แค่คำว่า EP แบบ Center ต้องมีเหมือนเดิม ... ผ่านแล้ว ทำ A/B test ปกหลายๆ แบบได้เลยนะ และตังเวลาลงได้เลย อยากให้เพิ่มปกแบบใหม่ลงใน Skill ด้วยและ update A/B test แบบปกใหม่ ลงใน EP1-3 ด้วยนะ"*).

2. **HARD — Every episode must have 3 A/B/C Test Titles (`แบบ A, B, C`) in all 6 languages (`TH`, `EN`, `ZH_TW`, `ZH_CN`, `VI`, `ES` = 18 titles per episode), each `≤ 100` characters and ending with the locked series brand suffix.**
   - **The 3 Title Archetypes (`A / B / C`)**:
     - **Variant A (`Story / Conflict Hook`)**: Stakes, humiliation, blood contract, or life-or-death gamble.
     - **Variant B (`Value / Shock Reveal Hook`)**: Extreme numerical contrast between what everyone believed and what the Jade Abacus exposed.
     - **Variant C (`Question / Secret Artifact Hook`)**: Curiosity gap or secret power of the Seven-Star Jade Abacus.
   - **Locked Series Brand Suffixes (mandatory on every title so returning viewers recognise the series)**:
     - `TH`: `... | ลูกคิดประเมินฟ้า EP<NN>`
     - `EN`: `... | Jade Tally EP<NN>`
     - `ZH_TW`: `... | 天機算盤 EP<NN>【3D國漫】`
     - `ZH_CN`: `... | 天机算盘 EP<NN>【3D国漫】`
     - `VI`: `... | Bàn Tính Định Thiên EP<NN>`
     - `ES`: `... | Jade Tally EP<NN>`
   - **Character Cap**: Every title in every language must be **`≤ 100` characters**. Exceeding `100` characters silently disables YouTube Studio's `เสร็จสิ้น` (`#set-test-button`) and `อัปเดต` buttons (hit on `EP03 ES` at `103c` and `EP02 TH-B` at `108c` on 2026-11-09).
   - **How the 6 languages are tested**:
     - The 3 `TH` titles run live alongside the 3 Universal Covers inside YouTube Studio's native **A/B/C Test (`ชื่อและภาพปก`)**.
     - All 18 titles (`6 languages × 3 variants`) are stored in `/opt/MoonieXHQ/Work/cn-series/publish/title_ab_test_matrix.json`. The 5 translated rows on `/video/<id>/translations` launch with **Variant A** and rotate to **Variant B** -> **Variant C** after 72 hours if a locale's CTR lags.
   **Why hard:** scope — CEO ruling 2026-11-09 (*"เขียนเป็นกฏให้หน่อยได้ไหม ว่า ปกต้องมี 3 แบบ และชื่อ A/B Test ต้องมี 3 ชื่อ ในทุกๆ ภาษา และห้ามพลาดอีก"*).

3. **HARD — Never include the word `"AI"` / `"IA"` or AI-tell punctuation (`—`, `–`, `·`, `“ ”`) in Channel Descriptions, Channel Keywords, Video Descriptions, Video Titles, or Video Tags across any of the 6 languages.**
   - Banned phrases across all 6 languages: `"สร้างเป็นแอนิเมชันด้วย AI"`, `"แอนิเมชัน AI"`, `"Made with AI"`, `"created with AI"`, `"AI 動畫"`, `"AI 动画"`, `"tạo bằng AI"`, `"sản xuất bằng AI"`, `"creada con IA"`, `"generada con IA"`.
   - Platform disclosure is satisfied strictly by selecting the YouTube Studio radio button `tp-yt-paper-radio-button[name=VIDEO_HAS_ALTERED_CONTENT_YES]` on the video edit page — never by writing `"Made with AI"` in user-facing descriptions or tags.
   - All descriptions and titles must also pass `CMO_Standard_HumanVoice_TH` (zero em-dashes `—`, en-dashes `–`, middle dots `·`, or curly quotes `“ ”`), and line 1 of every episode description must list the chronological episode links (`EP01` -> `EP02` -> `EP03`).
   **Why hard:** scope — CEO ruling 2026-11-09 (*"เข้าไปดู Description ของช่องให้หน่อย ว่ามีคำว่า AI หรือการใช้คำที่ดูเหมือน AI ไหม ปรับใหม่ให้หมดเลย"*).

4. **HARD — Run the automated Pre-Publish Gate (`validate_publish_pack.py`) before setting any episode to `PUBLIC`, and refuse to publish if it exits non-zero.**
   - Command on Contabo:
     ```bash
     /opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Work/cn-series/publish/validate_publish_pack.py <EP_KEY|ALL>
     ```
   - If the gate prints `PUBLISH GATE FAILED:`, fix every listed violation first; never bypass the gate.
   **Why hard:** irreversible once public impressions are served — the gate caught 6 stray em-dashes (`—`), 1 `101`-char English title, 3 shortened Vietnamese series names, and 1 leftover `"sản xuất bằng AI"` line on 2026-11-09 before final sign-off.

5. **HARD — Every episode (`EP04+`) must end with an 8-second Custom End Frame (`epXX_endframe_8s.mp4`) using the 100% Language-Free Universal Icon Template (`endframe_universal_overlay.png`) over a custom background matching that episode's climax/setting (`1 EP = 1 Custom End Screen Background`).**
   - **Zero Text on the End Frame (`100% Universal Pictograms`)**:
     - Left 16:9 Box: `[ ▶▶| ]` (Next Episode)
     - Center Circle: `[ 🔔+ ]` (Subscribe + Notification)
     - Right 16:9 Box: `[ ☰▶ ]` (Full Series Playlist)
     - Bottom Bar: `[ 🎧 ] ➔ [ ⚙️ ] ➔ [ 🔊 ] | 🇹🇭 🇺🇸 🇨🇳 🇻🇳 🇪🇸` (Language-free visual guide to switch multi-language audio tracks)
   - **Template Builder Command on Contabo**:
     ```bash
     python3 /opt/MoonieXHQ/Work/cn-series/publish/endframe/build_ep_endframe.py \
       --bg <path/to/epXX_custom_plate.jpg> \
       --out-jpg /opt/MoonieXHQ/Work/cn-series/publish/endframe/epXX_endframe.jpg \
       --out-mp4 /opt/MoonieXHQ/Work/cn-series/publish/endframe/epXX_endframe_8s.mp4
     ```
   - Concat `epXX_endframe_8s.mp4` to the end of the master video before uploading, and enable YouTube Studio `End Screen` (`วิดีโอ 1 รายการ, 1 การติดตาม` / `1 playlist`) + Channel Watermark (`ตลอดทั้งวิดีโอ`).
   **Why hard:** scope — CEO rulings `Q-20261109-0454-6f18` & `Q-20261109-0459-262f` (*"ภาพควรเป็นสากล มากกว่านี้ เอาที่คนดู ไม่รู้ภาษาดูออก"* / *"คิดว่า 1 EP ทำ 1 อันไม่น่าจะทำยากนะ ทำ template มาแล้ว เพิ่มฉากหลังแค่นั้น"*).

6. **HARD — Release Timing & Pre-Indexed Schedule (`12:00–14:00` or `19:00–23:30 GMT+7` ONLY, NEVER `00:00–11:00 GMT+7`, CEO 2026-11-16)**:
   - **Measured Studio Analytics Evidence (`2026-11-16`, `UCR_-P9I4Cyp5iDCltw7fk5w`)**:
     - **`EP02` (`spzN_YBkrAg`, published `13:58 GMT+7`)**: **`36,000` impressions**, **`4,304` views**, **`4.0%` CTR**, `146.1h` watch time (`72.1%` / `3,100` views from **Browse Features / Home Page** during the midday lunch/afternoon break).
     - **`EP01` (`o8in1boXAf0`, published `23:28 GMT+7`)**: **`28,000` impressions**, **`1,467` views**, **`2.4%` CTR**, **`214.1h` watch time**, **`6:24` AVD**, **`+21` subscribers** (`71.0%` / `1,000` views from **Suggested Videos** during prime-time evening/night viewing).
     - **`EP03` (`-YJQm-IG4kE`, published `00:14 GMT+7` after midnight)**: Dropped to **`1,300` impressions** and **`260` views** (**21–27x fewer impressions** than `EP01` and `EP02` because 30–40 min 3D donghua viewers do not start a new 30-minute episode after midnight).
     - **`EP03` first upload (`h9-Oaa6ThJE`, published `05:21 GMT+7` early morning)**: Only **`5` impressions** and **`4` views** in 4 hours.
   - **Mandatory Publish Procedure for Jade Tally**:
     1. Upload as **`ส่วนตัว` (`PRIVATE`)** at least 3–6 hours in advance so HD processing, 6-language audio tracks, 5 translated metadata rows, and the 3 A/B/C covers + 3 A/B/C titles (`ชื่อและภาพปก`) are 100% active before release.
     2. Schedule (`กำหนดเวลาไว้`) for either **`19:00 GMT+7`** (evening prime-time, matching `EP04 rNdlhy9Es_w`) or **`13:00–14:00 GMT+7`** (midday Browse peak, matching `EP02`).
     3. **Refuse any `PUBLIC` release between `00:00–11:00 GMT+7` (after midnight through morning).**
   **Why hard:** irreversible initial impression velocity — releasing after midnight (`00:14`) or early morning (`05:21`) cost `EP03` over `95%` of its initial impression pool compared to `EP01` (`23:28`) and `EP02` (`13:58`).

## Execution & Verification Steps

1. **Generate the 3 Universal Covers (`univ_A.jpg`, `univ_B.jpg`, `univ_C.jpg`) and `3x3` sheet**:
   - Run `/opt/MoonieXHQ/Work/cn-series/publish/build_universal_covers.py` on Contabo.
2. **Add the 18 A/B/C Titles (`6 languages × 3 variants`) to `title_ab_test_matrix.json`** and clean all 6 language `description.txt` + `TH/tags.txt` files.
3. **Run the mandatory Pre-Publish Gate**:
   ```bash
   /opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Work/cn-series/publish/validate_publish_pack.py ALL
   ```
   Expected output:
   ```text
   PUBLISH GATE PASSED (EP01, EP02, EP03): 3 Universal Covers + 18 A/B/C Titles (6 langs x 3) + 0 AI-tells!
   ```
4. **Apply Universal Covers + 3 Titles + 5-Language Translations on YouTube Studio** (via raw CDP in a dedicated background tab on Winbox Chrome `9224`, tunnel `9273`, never `bring_to_front`):
   - Run `/opt/MoonieXHQ/Work/cn-series/publish/apply_universal_covers_all.py`.

## When the CEO changes a rule

- **2026-11-09 (CEO):** *"เขียนเป็นกฏให้หน่อยได้ไหม ว่า ปกต้องมี 3 แบบ และชื่อ A/B Test ต้องมี 3 ชื่อ ในทุกๆ ภาษา และห้ามพลาดอีก ต่อมาเข้าไปดู Description ของช่องให้หน่อย ว่ามีคำว่า AI หรือการใช้คำที่ดูเหมือน AI ไหม ปรับใหม่ให้หมดเลย และ ปกคลิปด้วย อยากให้ใช้แบบ สากล ที่สุด ออกแบบใหม่ ให้ทุกๆ ชาติดูแล้วเข้าใจตรงกันได้"*
- **2026-11-09 (CEO):** *"เอาใส่และ Update ไว้ใน Skills ดีกว่าไหม แล้วรายงานด้วยว่าคุณเป็นคนเขียนไว้ CMO จะได้รู้"*
- **2026-11-16 (CEO, `Q-20261116-0618-8b22`):** *"แผ่นปก ปรับ EP4 ให้อยู่ Center ได้ไหม แล้ว Logo มุม ขวาบน ใส่ Logo จริงๆ ของ ช่องแบบเดียวกับ Ghost Rule ได้ไหม อันนั้นมันไม่ใช่ Logo ช่องนะ ... ปกคลิปอยากให้ใช้ Skills เดียวกัน กับ Ghost Rule ทำได้ไหม แค่คำว่า EP แบบ Center ต้องมีเหมือนเดิม ... ผ่านแล้ว ทำ A/B test ปกหลายๆ แบบได้เลยนะ และตังเวลาลงได้เลย อยากให้เพิ่มปกแบบใหม่ลงใน Skill ด้วยและ update A/B test แบบปกใหม่ ลงใน EP1-3 ด้วยนะ"*

## Field notes

- 2026-11-09 [MISSING] §Rules — EP01, EP02, and EP03 initially launched with single-title setups, inconsistent translated series names (`แคลคูลัสหยก` vs `ลูกคิดหยก` vs `ลูกคิดประเมินฟ้า`, `The Jade Abacus` vs `Jade Tally`), Thai-script cover banners that locked out non-Thai viewers in global A/B tests, and `"สร้างเป็นแอนิเมชันด้วย AI"` / `"Made with AI"` lines in channel and video descriptions; authored this skill + `validate_publish_pack.py` gate by Antigravity (AGY session f22cf62a) → §Rules 1-4 · evidence: f22cf62a-b227-4201-a5c4-5af72edf44e9, Q-20261109-0236-a2f2 · status: promoted
- 2026-11-16 [WRONG] §Rule 6 Release Timing — `EP03` (`-YJQm-IG4kE`) was published at `00:14 GMT+7` (after midnight) and stalled at `1,300` impressions / `260` views, whereas `EP02` (`spzN_YBkrAg`, published `13:58 GMT+7`) reached `36,000` impressions / `4,304` views (72.1% Browse Features) and `EP01` (`o8in1boXAf0`, published `23:28 GMT+7`) reached `28,000` impressions / `1,467` views / `214.1h` watch time (71.0% Suggested Videos). Promoted Rule 6 to a HARD rule: upload Private first with all A/B covers/titles and schedule only in `12:00–14:00` or `19:00–23:30 GMT+7`, strictly banning `00:00–11:00 GMT+7` · evidence: Jade Tally Studio Analytics 2026-11-16 (`o8in1boXAf0`, `spzN_YBkrAg`, `-YJQm-IG4kE`, `rNdlhy9Es_w`) · status: promoted
