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
aka: []
---

# YouTube Multi-Language Publish & A/B/C Test Rules — Jade Tally (`ลูกคิดประเมินฟ้า` / `YT: คลิปจีน`)

> **Authored by:** Antigravity (`AGY` session `f22cf62a`) on **2026-11-09** per explicit CEO ruling (*"เขียนเป็นกฏให้หน่อยได้ไหม ว่า ปกต้องมี 3 แบบ และชื่อ A/B Test ต้องมี 3 ชื่อ ในทุกๆ ภาษา และห้ามพลาดอีก ... เอาใส่และ Update ไว้ใน Skills ดีกว่าไหม แล้วรายงานด้วยว่าคุณเป็นคนเขียนไว้ CMO จะได้รู้"*).

This skill governs every episode published on the multi-language 3D Chinese cultivation/fantasy YouTube channel **Jade Tally (`@JadeTally`, channel ID `UCR_-P9I4Cyp5iDCltw7fk5w`, Drive branch `ALL DRAFT/YT: คลิปจีน/`)**. It binds the **CMO**, **CTO**, **CGO**, and any worker or AGY session preparing, cutting, translating, or publishing an episode.

## When to invoke / when NOT to

- **Invoke** before designing thumbnails, writing titles/descriptions, uploading audio tracks, or setting any video on **Jade Tally (`YT: คลิปจีน`)** to `PUBLIC` (`สาธารณะ`).
- **Do NOT invoke** for `RED SEAL ARCHIVE` (`@redsealarchive`, which uses its own 8-language + 6 foreign audio tracks pipeline in `CMO_Standard_GhostChannel_DNA`) or for single-language Thai channels (`BLACK LIQUIDITY`, `บ้านนี้มีมีมี่`, `เอาชีวิตรอดกับข้าวหอม`), which follow their own workflow skills (`CMO_Workflow_BlackLiquidity`, `CMO_Workflow_MimiPage_Weekly`, `CMO_Workflow_KhaoHomEpisode`).

## Rules

1. **HARD — Every episode must ship with 3 Universal International A/B/C Thumbnails (`univ_A.jpg`, `univ_B.jpg`, `univ_C.jpg` at `1280x720`) containing zero local-language sentence banners.**
   - **Variant A (`Pure Cinematic Key Art`)**: High-contrast facial emotion + glowing artifact + top-right corner ribbon `EP1` / `EP2` / `EP3` (no bottom HUD bar).
   - **Variant B (`Universal Appraisal Twist HUD`)**: Glowing Jade Abacus / treasure + bottom-center universal value twist badge (painted gold coin or spirit gem icon + fake value crossed out in red ➜ true value in Arabic numerals, e.g. `10,000 ➜ 3`, `0 ➜ 999,999+`, `1,000 ➜ 0`) + `EP<N>` corner ribbon.
   - **Variant C (`Dramatic Climax / Reveal Scene`)**: High-stakes confrontation or split-open treasure reveal in front of the crowd + subtle golden edge frame + `EP<N>` corner ribbon.
   - All 3 universal covers are uploaded into YouTube Studio's **A/B/C Test (`การทดสอบ A/B` -> `ชื่อและภาพปก` `chip-2`)**, and `univ_A.jpg` is also set on all 5 localized rows under `/video/<id>/translations`.
   **Why hard:** scope & irreversible CTR loss — YouTube's A/B/C test serves the same 3 test thumbnails globally across all viewer locales (`TH`, `EN`, `ZH`, `VI`, `ES`). A Thai sentence banner on the cover causes non-Thai viewers to scroll past immediately (CEO ruling 2026-11-09: *"ปกคลิปด้วย อยากให้ใช้แบบ สากล ที่สุด ออกแบบใหม่ ให้ทุกๆ ชาติดูแล้วเข้าใจตรงกันได้"*).

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

6. **Release Timing Advice (measured from Channel Analytics 2026-11-09)**:
   - `90.1%` of Jade Tally's audience sits in `GMT+7` (`TH 73.4%`, `VI 14.3%`, `LA 2.4%`) and `85.7%` are aged `25–54`.
   - Publishing `EP03` at `05:21 AM GMT+7` yielded only `5` impressions and `4` views in the first 4 hours (`05:21–09:20`), whereas `EP02` (published at `13:58`) and `EP01` (published at `23:28`) hit peak active windows and reached `4,115` and `1,080` views. Schedule or flip `PUBLIC` during **`11:30–14:00` or `18:00–22:00 GMT+7`**, never during `01:00–07:00 AM` unless explicitly ordered by the CEO.

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

## Field notes

- 2026-11-09 [MISSING] §Rules — EP01, EP02, and EP03 initially launched with single-title setups, inconsistent translated series names (`แคลคูลัสหยก` vs `ลูกคิดหยก` vs `ลูกคิดประเมินฟ้า`, `The Jade Abacus` vs `Jade Tally`), Thai-script cover banners that locked out non-Thai viewers in global A/B tests, and `"สร้างเป็นแอนิเมชันด้วย AI"` / `"Made with AI"` lines in channel and video descriptions; authored this skill + `validate_publish_pack.py` gate by Antigravity (AGY session f22cf62a) → §Rules 1-4 · evidence: f22cf62a-b227-4201-a5c4-5af72edf44e9, Q-20261109-0236-a2f2 · status: promoted
