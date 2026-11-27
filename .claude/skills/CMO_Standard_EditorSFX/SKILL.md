---
name: CMO_Standard_EditorSFX
kind: standard
description: 'STANDARD — Mass-editor free SFX library, situation mapping, pre-roll peak alignment, and -14 LUFS mixing rules for vertical reels and shorts. Trigger on /CMO_Standard_EditorSFX, "SFX Mass", "Editor SFX", "ใส่เสียง SFX", "เลือกเสียงเอฟเฟกต์", "transition sfx". Not for 16:9 horror ambient mixes (CMO_Standard_GhostChannel_DNA).'
owner: CMO
audience: [cmo, video_editor, script_writer, developer]
created_by: agent
author: {role: cmo, date: "2026-11-09"}
improved_by:
  - {role: project_head, date: "2026-11-18", what: "§4 BLACK LIQUIDITY 10-Track Channel BGM Library (BL01–BL10, Google Flow Music Lyria 3.5), BGM Semantic Naming Standard, -24.0 dB Ceiling + -3.0 dB Sidechain Ducking + Seamless Beat-Matched Loop (tools/bgm_bed.py), and How to Add New Tracks (tools/flow_music_gen.py) (CEO rulings Q-20261118-1023-871c, Q-20261118-1046-3f25, Q-20261118-1120-5270)"}
aka: []
---

# What a good Mass-Editor SFX pass on a vertical reel or short is

This standard defines the **17 CEO-Approved Mass-Editor Sound Effects (SFX)** (`Q-20261109-0523-6020`, `Q-20261109-0523-6b09`, `Q-20261109-0523-8802`) selected by listening test from top open-source editor SFX libraries, along with their exact situational triggers, pre-roll peak alignment math, and mixing hierarchy (CEO ruling 2026-11-09: *"ใช้เสียงที่เขาแจกฟรีแล้วเสียง Mass จะดีกว่า เอาที่คนส่วนใหญ่ใช้กัน Editor ใช้กันแล้วมันแจกฟรี ... เขียนนิยามว่าเสียงนั้นควรใช้ในสถานการณ์ไหนได้บ้าง เอามาเป็น Skill สำหรับ Editor SFX เลย"*).

The audio library is sourced from three open-source GitHub editor SFX repositories and free creator packs:
1. **`Barty-Bart/motion-graphics` (`skills/sound-effects/`)** — Vox's (`@Voxyz_ai`) measured sound-pass standard with CC0 Freesound/Kenney sounds and Mixkit free creator sounds.
2. **`remotion-dev/remotion` (`packages/sfx`)** — `@remotion/sfx` official creator WAV library (`shutter-modern`, `shutter-old`, `vine-boom`, `mouse-click`, `switch`, `page-turn`, `ding`, `record-scratch`).
3. **`JesseEisenbart/video-effects-skill` (`public/sfx/`)** — vertical-reel editor SFX (`whoosh`, `bubble`, `stamp`, `shatter`, `typing`).

All 17 CEO-approved sounds are pre-normalized to **48 kHz Stereo PCM WAV (`-3.0 dBFS` peak, leading silence trimmed)** with measured `peak_time_ms` in `/Users/gob/MoonieXHQ/Assets/BlackLiquidity/sfx-mass-pack/curated-48k/manifest.json` (the 9 rejected sounds are quarantined in `rejected-by-ceo/` and must never be used).

## When to invoke / when NOT to

- **Invoke** whenever cutting, scoring, or reviewing a vertical `9:16` (`1080x1920`) short-form video (BLACK LIQUIDITY, MYPASAKON, Khao Hom, or any talking-head / B-roll reel) that needs hook impacts, transition whooshes, UI callout pops, pattern interrupts, or foley.
- **Do NOT invoke** for 16:9 horror soundscapes (`CMO_Standard_GhostChannel_DNA`) or for voice TTS generation.
- **Refusal precondition:** If a build script synthesizes SFX in code using sine waves, white noise, or oscillator chirps, or references any of the 9 CEO-rejected files (`hit_punch_04`, `whip_snap_04`, `whoosh_fast_01`, `swoosh_deep_05`, `pop_clean_01`, `riser_subtle_01`, `riser_short_02`, `glitch_digital_01`, `chime_soft_02`), refuse the render and use only the 17 CEO-approved WAV files in `curated-48k/`.

## The spec

### 1. Core laws (tiered)

1. **HARD — Use ONLY the 17 CEO-Approved WAV files in `curated-48k/` (never synthesize SFX in code, and never use the 9 rejected files).**
   **Why hard:** CEO listening-test selection (`Q-20261109-0523-6020`, `Q-20261109-0523-6b09`, `Q-20261109-0523-8802`). The CEO audited all 26 candidates on `/run`, approved 17 specific sounds, and rejected 9 (`hit_punch_04`, `whip_snap_04`, `whoosh_fast_01`, `swoosh_deep_05`, `pop_clean_01`, `riser_subtle_01`, `riser_short_02`, `glitch_digital_01`, `chime_soft_02`).
2. **Pre-Roll Peak Alignment (`t_start = t_visual_event - peak_time_ms / 1000`).**
   Every whoosh and deep impact has an attack build-up before its loudest transient peak (`peak_time_ms` in `manifest.json`). Always subtract `peak_time_ms` so the acoustic peak lands dead-on the visual transition frame (`±15ms`).
3. **No Back-to-Back Sample Repetition.**
   Never fire the exact same `sfx_id` on two consecutive cuts. Alternate between `whoosh_arrow_02` and `whoosh_clean_03` on whip/slide cuts, and between `shutter_modern_01` and `shutter_old_02` on scale-punch/flash cuts.
4. **Loudness Hierarchy (Voiceover is King).**
   - **Voiceover (Narrator):** `0 dB` reference anchor (`-14.0 LUFS` integrated).
   - **Hero Impact / Hook Boom (Family 1):** `-6 dB` to `-8 dB` (felt in the chest, never masks a spoken consonant).
   - **Transition Whoosh / Camera Shutter (Families 2 & 3):** `-8 dB` to `-10 dB`.
   - **UI Pop / Click / Switch / Ding (Families 4 & 6):** `-9 dB` to `-11 dB`.
   - **Typing Underlay:** `-11 dB` to `-14 dB` (ducks under speech).
   - **Channel Background Music (BGM Bed):** **`-24.0 dB` ceiling** below active Voiceover RMS, with **`-3.0 dB` sidechain ducking** (`-27.0 dB` during speech), `4.0s` raised-cosine Fade-In from `-40 dB`, and `4.0s` cosine Fade-Out to `-60 dB` (`tools/bgm_bed.py`, CEO ruling `Q-20261118-1120-5270`).
   - **Final Master Export:** `-14.0 LUFS` (`±0.4 LU`), True Peak `<= -1.5 dBFS`.

---

### 2. Situational Dictionary of the 17 CEO-Approved Mass-Editor SFX (`curated-48k/`)

#### Family 1 · Hook Impacts, Sub Drops & Rule Stamps (4 เสียงที่ผ่าน — `Q-20261109-0523-6020`: A, B, C, E)

| SFX ID (`curated-48k/`) | Dur | Peak Offset (`pre_roll`) | Gain | สถานการณ์ที่ควรใช้ (When to Use) | สถานการณ์ที่ห้ามใช้ (When NOT to Use) |
|---|---|---|---|---|---|
| `boom_vine_01.wav`<br>*(@remotion/sfx vine-boom)* | `1.19s` | `297 ms` | `-6.0 dB` | **ใส่เฟรมแรก `0.00s` กระแทกหยุดนิ้ว** หรือจังหวะเปิดความผิดพลาด/พอร์ตแดง | ห้ามใช้เกิน 2–3 ครั้งต่อคลิป |
| `impact_sub_03.wav`<br>*(Mixkit #2908)* | `3.02s` | `988 ms` | `-6.5 dB` | **ใส่ตอนขึ้นหัวข้อใหญ่** หรือเน้นประโยคเตือนสติที่หนักแน่น (`Beat 1 Body`) | ห้ามวางซ้อนกับ `boom_vine_01` ในวินาทีเดียวกัน |
| `impact_deep_whoosh_02.wav`<br>*(Mixkit #1143)* | `1.91s` | `536 ms` | `-6.5 dB` | **ใส่ตอนเปลี่ยนเข้าท่อนสำคัญ (`Beat 3` กลไกสมอง / `Beat 4` พอร์ตพัง / `Beat 5` ทางออก)** | ห้ามใช้กับคัตย่อยที่เปลี่ยนภาพเร็วทุก 0.5 วินาที |
| `stamp_thud_05.wav`<br>*(video-effects-skill stamp)* | `0.20s` | `26 ms` | `-7.5 dB` | **ใส่ตอนประทับตรากฎเหล็กบนหน้าจอ** (เช่น กฎข้อ `01`, `02`, `03` หรือกฎพักสมอง 15 นาที) | ห้ามใช้แทนเสียงเปลี่ยนฉากทั่วไป |

#### Family 2 · Whip & Whoosh Transitions (2 เสียงที่ผ่าน — `Q-20261109-0523-6020`: H, I)

| SFX ID (`curated-48k/`) | Dur | Peak Offset (`pre_roll`) | Gain | สถานการณ์ที่ควรใช้ (When to Use) | สถานการณ์ที่ห้ามใช้ (When NOT to Use) |
|---|---|---|---|---|---|
| `whoosh_arrow_02.wav`<br>*(Mixkit #1491)* | `0.42s` | `226 ms` | `-8.5 dB` | **ใส่คู่ `Whip Pan` / `Whip Tilt` สลับฉากไว** หรือลูกศรชี้กราฟพุ่ง (หางเสียงสั้น กระชับ) | ห้ามใช้ซ้ำติดกันโดยไม่สลับกับ `whoosh_clean_03` |
| `whoosh_clean_03.wav`<br>*(video-effects-skill whoosh)* | `1.00s` | `368 ms` | `-8.5 dB` | **ใส่คู่ `Gravity Flip` หมุนกล้อง 180 องศา** หรือเลื่อนการ์ด/สลับฉากต่อเนื่องแบบนุ่มแน่น | ห้ามใช้ในจังหวะตกใจหรือกระจกแตก |

#### Family 3 · Camera Shutter & Page Turn (3 เสียงที่ผ่าน — `Q-20261109-0523-6b09`: A, B, C)

| SFX ID (`curated-48k/`) | Dur | Peak Offset (`pre_roll`) | Gain | สถานการณ์ที่ควรใช้ (When to Use) | สถานการณ์ที่ห้ามใช้ (When NOT to Use) |
|---|---|---|---|---|---|
| `shutter_modern_01.wav`<br>*(@remotion/sfx shutter-modern)* | `0.32s` | `113 ms` | `-8.0 dB` | **ใส่คู่ `Scale Punch` ซูมกระแทก `1.38x`** หรือ `Exposure Flash` เน้นใบหน้าตัวละคร/กราฟจริง | ห้ามใช้ถ้าภาพไม่มีการซูมกระแทกหรือแฟลช |
| `shutter_old_02.wav`<br>*(@remotion/sfx shutter-old)* | `0.22s` | `60 ms` | `-8.5 dB` | **ใส่ตอนโชว์ภาพแคปหน้าจอหลักฐาน** หรือหยุดภาพพฤติกรรมที่ทำผิด (เช่น ลากเส้น Stop Loss ทิ้ง) | ห้ามใช้กับฉากวิดีโอปกติที่ไม่มีหลักฐานบนจอ |
| `page_turn_01.wav`<br>*(@remotion/sfx page-turn)* | `0.40s` | `160 ms` | `-8.5 dB` | **ใส่ตอนเปิดสมุดวางแผนเทรด (`Trading Journal`)** หรือพลิกการ์ดกฎข้อ `01 → 02 → 03` | ห้ามใช้ถ้าบนจอไม่มีสมุดหรือการ์ดข้อมูล |

#### Family 4 · UI Callouts, Clicks & Data Reveal (5 เสียงที่ผ่าน — `Q-20261109-0523-6b09`: E, F, G, H, I)

| SFX ID (`curated-48k/`) | Dur | Peak Offset (`pre_roll`) | Gain | สถานการณ์ที่ควรใช้ (When to Use) | สถานการณ์ที่ห้ามใช้ (When NOT to Use) |
|---|---|---|---|---|---|
| `bubble_pop_02.wav`<br>*(video-effects-skill bubble)* | `0.36s` | `34 ms` | `-10.0 dB` | **ใส่ตอนหัวข้อย่อยใน `Checklist` เด้งขึ้นทีละบรรทัด** | ห้ามใช้กับฉากดราม่าพอร์ตพัง |
| `pop_alert_03.wav`<br>*(Mixkit #2354)* | `0.10s` | `27 ms` | `-9.5 dB` | **ใส่ตอนป้าย `Tag` สีแดง หรือกรอบแดง `Callout Box` เด้งชี้จุดอันตรายบนจอ** | ห้ามใส่ทุกบรรทัดซับไตเติลปกติ |
| `click_mouse_04.wav`<br>*(@remotion/sfx mouse-click)* | `0.20s` | `110 ms` | `-9.0 dB` | **ใส่ตรงจังหวะมือในภาพกดเมาส์เปิดออเดอร์** หรือกดคัตออเดอร์/ตั้งจุดตัดขาดทุน | ห้ามใช้ถ้าในภาพไม่ได้กดเมาส์หรือปุ่ม |
| `switch_ui_05.wav`<br>*(@remotion/sfx switch)* | `0.33s` | `123 ms` | `-9.5 dB` | **ใส่ตอนสลับสถานะจากพฤติกรรมผิดเป็นถูก** (เช่น ปิดแสงสีฟ้า → เปิดไฟอุ่น `3000K` บนโต๊ะเทรด) | ห้ามใช้กับการตัดภาพ B-Roll ทั่วไป |
| `typing_fast_02.wav`<br>*(video-effects-skill typing)* | `3.50s` | `487 ms` | `-11.5 dB` | **ใส่คลอเบาๆ ตอนตัวเลขสถิติ (เช่น `US 02:00` หรือ `-84.5%`) กำลังพิมพ์วิ่งขึ้นจอ** | ห้ามเปิดดังเกิน `-11 dB` เพื่อไม่ให้กวนเสียงพูด |

#### Family 5 · Pattern Interrupt & Shatter (2 เสียงที่ผ่าน — `Q-20261109-0523-8802`: B, D)

| SFX ID (`curated-48k/`) | Dur | Peak Offset (`pre_roll`) | Gain | สถานการณ์ที่ควรใช้ (When to Use) | สถานการณ์ที่ห้ามใช้ (When NOT to Use) |
|---|---|---|---|---|---|
| `record_scratch_03.wav`<br>*(@remotion/sfx record-scratch)* | `1.23s` | `647 ms` | `-8.0 dB` | **ใส่เบรกอารมณ์กะทันหัน ตอนพูดสวนความเชื่อของรายย่อย** (*"ไม่ใช่เพราะระบบเทรดพัง!"*) | ห้ามใช้ในส่วนสรุปท้ายคลิป |
| `shatter_glass_02.wav`<br>*(video-effects-skill shatter)* | `1.36s` | `23 ms` | `-8.0 dB` | **ใส่คู่เอฟเฟกต์กระจกแตก (`Prism Shatter`)** ตอนพูดคำว่า *"พอร์ตแตก / ล้างพอร์ต / สมองเบลอ"* | ห้ามใช้เกิน 1–2 ครั้งต่อคลิป |

#### Family 6 · Checklist Lock & Resolution (1 เสียงที่ผ่าน — `Q-20261109-0523-8802`: E)

| SFX ID (`curated-48k/`) | Dur | Peak Offset (`pre_roll`) | Gain | สถานการณ์ที่ควรใช้ (When to Use) | สถานการณ์ที่ห้ามใช้ (When NOT to Use) |
|---|---|---|---|---|---|
| `ding_bright_01.wav`<br>*(@remotion/sfx ding)* | `1.27s` | `88 ms` | `-9.5 dB` | **ใส่ตอนติ๊กถูกสีเขียว `✓` หน้าข้อวินัยที่ทำสำเร็จในท้ายคลิป (`Beat 5–6`)** | ห้ามใช้ในฉากปัญหาช่วงต้นคลิป (`Beat 1–2`) |

---

### 3. Never Use — 9 Sounds Rejected by CEO on `/run` (Quarantined in `rejected-by-ceo/`)

Do NOT load or substitute any of these 9 rejected files:
- `hit_punch_04.wav` (rejected on `Q-20261109-0523-6020`) → use `boom_vine_01.wav` or `stamp_thud_05.wav` instead.
- `whip_snap_04.wav`, `whoosh_fast_01.wav`, `swoosh_deep_05.wav` (rejected on `Q-20261109-0523-6020`) → use `whoosh_arrow_02.wav` and `whoosh_clean_03.wav` instead.
- `pop_clean_01.wav` (rejected on `Q-20261109-0523-6b09`) → use `pop_alert_03.wav` or `bubble_pop_02.wav` instead.
- `riser_subtle_01.wav`, `riser_short_02.wav` (rejected on `Q-20261109-0523-6b09` & `8802`) → do not use risers; use `whoosh_clean_03.wav` or `impact_deep_whoosh_02.wav` pre-rolled into the cut.
- `glitch_digital_01.wav` (rejected on `Q-20261109-0523-8802`) → use `record_scratch_03.wav` or `shatter_glass_02.wav` instead.
- `chime_soft_02.wav` (rejected on `Q-20261109-0523-8802`) → use `ding_bright_01.wav` instead.

---

### 4. Channel Background Music (BGM) Library (`BL01–BL10`), Semantic Naming & `-24.0 dB` Envelope (`tools/bgm_bed.py` & `tools/flow_music_gen.py`)

Full specification and Drive IDs live in `CMO_Procedure_BlackLiquidity_Cut` `§6h-8`:
1. **Semantic Naming Rule**:
   `BL_BGM_{NN}_({Title-EN})_({สถานการณ์ที่ใช้-TH})_({BPM}BPM)_({MMmSSs})_({DD-MM-YYYY})_(FlowMusic-Lyria3.5).{wav|m4a}`
2. **Where the 10 Tracks Live**:
   - **Google Drive**: `ALL DRAFT/BLACK LIQUIDITY/BLACK LIQUIDITY [62]/Audio` (`1kpG9wATvy0i3mGWz0pmcPCLaWv6xHWjO`, 10 `.wav` + 10 `.m4a` + `BGM_MANIFEST.json` `1kTIABrsSbYPP7ukO4UpuaoKfgCbHfjBI`) and `ALL DRAFT/ASSETS/Audio` (`1QxYqKsn2AqwujTH4It9NXKAsQvXmAOXH`, 10 `.m4a` + `BL_BGM_MANIFEST.json` `1_QDyIeuhct_WVPzgJzjf7PZ1mA8pYRdF`).
   - **Local Cache**: `/Users/gob/MoonieXHQ/Assets/BlackLiquidity/channel-music-10/BGM_MANIFEST.json`.
3. **10-Track Situational Summary (`BL01`..`BL10`, full `2:28–3:03` lengths)**:
   - `BL01` (`bbook`, `92 BPM`, `02m28s`) — **Dark Liquidity Pulse (Default Signature)**: แฉกลไกโบรกเกอร์ B-Book, Dealing Desk, สเปรดถ่าง
   - `BL02` (`dealing_desk`, `88 BPM`, `02m55s`) — **Shadow Dealing Desk**: ความลับหลังบ้านตลาด, Liquidity Provider, Order Book ลับ
   - `BL03` (`drawdown`, `96 BPM`, `03m03s`) — **Margin Call Tension**: พอร์ตติดลบหนัก, กราฟลากกวาด Stop Loss (`Stop Hunt`)
   - `BL04` (`volatility`, `100 BPM`, `02m50s`) — **Midnight Volatility**: ตลาดอเมริกาเปิด, ข่าวแรง `Non-Farm` / `CPI`, ทองคำสวิงแรง
   - `BL05` (`late_night`, `82 BPM`, `02m47s`) — **02AM Chart Glare**: จิตวิทยาเทรดดึกตี 2, แสงจอหลอกสมอง, อาการล้าสะสม
   - `BL06` (`reset`, `85 BPM`, `02m54s`) — **Cortisol Reset**: กลไกสมอง (`Cortisol` / `Dopamine`), หยุดหัวร้อน (`Revenge Trade`), ตั้งสติ
   - `BL07` (`sniper`, `104 BPM`, `02m32s`) — **Sniper Execution**: วางแผนเทรดคมกริบ, จุดเข้าแม่นยำ, ตั้ง `Pending Order` / `SL`
   - `BL08` (`math`, `98 BPM`, `02m41s`) — **The 1 Percent Math**: คำนวณ `Spread`, `Swap`, `Rebate`, `Risk-to-Reward`, สถิติคนรอด 1%
   - `BL09` (`survivor`, `90 BPM`, `02m34s`) — **Disciplined Survivor**: กฎเหล็ก 3 ข้อเอาตัวรอดระยะยาว, `Money Management`
   - `BL10` (`basket`, `94 BPM`, `02m50s`) — **Obsidian Gold Signature**: คลิปปักตะกร้าสินค้า (`Basket 5:1`), ไอเทมจัดโต๊ะเทรดโทน `Dark Luxury`
4. **How to Mix & How to Add New Tracks**:
   - Mix with `tools/bgm_bed.py --track BL01 --vo voice_and_sfx.wav --ceiling-db -24.0 --speech-duck-db -3.0 --fade-in 4.0 --fade-out 4.0 --out mixed.wav` (automatically loops via 3.0s beat-phase equal-power cosine crossfade if the video is longer than the song).
   - Generate and register new tracks via `tools/flow_music_gen.py` on `winbox:9226` (`Google Flow Music` `Lyria 3.5`, `Instrumental = ON`).

## The check

Run the verification check before delivering any cut:
```bash
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python \
  /Users/gob/MoonieXHQ/Agents/Core/scripts/skill-lint.py check \
  /Users/gob/MoonieXHQ/Agents/Core/.claude/skills/CMO_Standard_EditorSFX/SKILL.md
```
And verify on the rendered MP4:
1. Integrated loudness is **`-14.0 LUFS` (`±0.4 LU`)** and True Peak is **`<= -1.5 dBFS`**.
2. Every cue in the build log references one of the **17 CEO-approved `.wav` files** in `/Users/gob/MoonieXHQ/Assets/BlackLiquidity/sfx-mass-pack/curated-48k/manifest.json`.
3. No two adjacent cuts use the same `sfx_id`.

## Good vs bad

- **Good (17 CEO-Approved Mass-Editor SFX with Pre-Roll Alignment):**
  - At `t = 0.50s` (`whip_pan_h` cut + Red Callout Tag at `0.58s`), `whoosh_arrow_02.wav` (`peak_time_ms = 226ms`) starts at `0.274s` (`-7.5 dB`) so its swish peak hits `0.500s` on the exact frame the image whips across, followed at `0.553s` by `pop_alert_03.wav` (`peak_time_ms = 27ms`, `-8.5 dB`) as the red warning tag snaps onto the frame.
- **Bad (Synthesized Beeps, Rejected Risers, or Unaligned Starts):**
  - Generating a `np.sin(2 * np.pi * freq * t)` frequency sweep in Python, using a rejected riser (`riser_subtle_01` / `riser_short_02`) or rejected glitch (`glitch_digital_01`), or starting a whoosh file at `t_cut` without subtracting `peak_time_ms`.

## Field notes
- 2026-11-09 [MISSING] §1-3 — CEO audited all 26 candidate sounds across 3 multi-pick media cards on `/run` (`Q-20261109-0523-6020` picked `A,B,C,E,H,I`; `Q-20261109-0523-6b09` picked `A,B,C,E,F,G,H,I`; `Q-20261109-0523-8802` picked `B,D,E`), locking the 17 approved sounds and quarantining the 9 rejected ones · evidence: Run Inbox records `Q-20261109-0523-6020`, `Q-20261109-0523-6b09`, `Q-20261109-0523-8802` · status: promoted
- 2026-11-18 [MISSING] §4 — CEO approved the 10-track BLACK LIQUIDITY Channel BGM Library (`BL01–BL10`, generated on Google Flow Music `Lyria 3.5` at `2:28–3:03` full length), selected `BL01` (`Dark Liquidity Pulse`) as the primary signature track (`Q-20261118-1046-3f25`), and locked `ระดับ A: -24.0 dB` ceiling + `-3.0 dB` speech ducking + `4.0s` fade-in/out + 3.0s beat-phase crossfade loop (`tools/bgm_bed.py`, `Q-20261118-1023-871c` & `Q-20261118-1120-5270`) · evidence: Run Inbox `Q-20261118-1023-871c`, `Q-20261118-1046-3f25`, `Q-20261118-1120-5270` → §1.4, §4 · status: promoted
