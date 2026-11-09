---
name: CMO_Standard_GhostChannel_DNA
kind: standard
description: 'STANDARD — Story-synced beat-by-beat visual DNA, episode-specific cast generation, Hook-to-Full-Bleed framing, -14 LUFS horror SFX, and 8-lang/6-audio publish for RED SEAL ARCHIVE (@redsealarchive). Trigger on /CMO_Standard_GhostChannel_DNA, "ช่องผี", "เรื่องผี", "RED SEAL ARCHIVE", "กรอบกระดาษฉีก", "ใส่เสียงผี". Not for lakorn.'
owner: CMO
audience: [cmo, video_editor, script_writer, developer]
created_by: agent
author: {role: cmo, date: "2026-11-08"}
improved_by:
  - {role: cto, date: "2026-11-09", what: "Three-phase Hook border -> THREE DAYS EARLIER + spoken cue -> Full-Bleed Cinema architecture, 4-frame character sprite sheets, YouTube native watermark, and Mass Horror SFX rule (CEO Q-20261109-0509-b6b4, Q-20261109-0544-1bc3, Q-20261109-0653-1c8d, Q-20261109-0730-27e6)"}
  - {role: cto, date: "2026-11-09", what: "Story-synced sentence-pause beat cutting (find_pause_in_wav), 32+ unique scene-specific plates per episode, zero old character reuse across episodes/scenes, and 8-language + 6 foreign audio tracks + 19:00 schedule pipeline (CEO Q-20261109-0933-0c3a, Q-20261109-1008-f4ae)"}
aka: []
---

# What a good RED SEAL ARCHIVE (`@redsealarchive`) episode is

This standard defines the visual identity, **Story-Synced Beat-by-Beat Visual Architecture (`find_pause_in_wav`)**, **Episode- & Scene-Specific Character Generation**, three-phase Hook-to-Full-Bleed cinema transition, spatial camera-axis continuity, `-14.0 LUFS` Mass Horror SFX soundscape, and **8-Language + 6 Foreign Audio Tracks + 3-Way A/B/C Thumbnail Publishing Pipeline** for the **RED SEAL ARCHIVE (`@redsealarchive`, channel `UCA3806sh7qlV1S_oCIxlnjg`)** 16:9 YouTube horror channel (CEO rulings `Q-20261108-1604-6e38`, `Q-20261108-1650-0d81`, `Q-20261108-1707-774c`, `Q-20261108-1944-71db`, `Q-20261109-0509-b6b4`, `Q-20261109-0544-1bc3`, `Q-20261109-0653-1c8d`, `Q-20261109-0730-27e6`, `Q-20261109-0933-0c3a`, and `Q-20261109-1008-f4ae`).

## When to invoke / when NOT to

- **Invoke** whenever writing, storyboarding, generating plates/sprites, mixing sound, cutting a `16:9` (`1920x1080`) horror episode, or publishing multi-language metadata/audio/thumbnails for **RED SEAL ARCHIVE (`@redsealarchive`)** (`Work/ghost-pilot/`).
- **Do NOT invoke** for Thai moral drama / lakorn (`CMO_Standard_Story_ThaiMoralDrama`), vertical family-dog shorts (`CMO_Standard_Story_FamilyDogSeries`), or BLACK LIQUIDITY (`CMO_Workflow_BlackLiquidity`).
- **Refusal precondition:** Refuse any episode render that:
  1. Loops a small pool of plates (`8–10` images) on a fixed timer (`6.0–6.5s` `shot_cycles`) instead of cutting at the exact spoken sentence pauses (`find_pause_in_wav`) with a dedicated plate (`32–45+` unique plates per episode) matching the exact narrated sentence (`Q-20261109-0933-0c3a`);
  2. Reuses a protagonist sprite or character plate from an earlier episode or unrelated scene instead of generating a new character for each new episode and scene action (`Q-20261109-0933-0c3a`);
  3. Keeps static still images without 24fps camera motion, particles (rain/dust/mist), dynamic lighting, and 2–3 depth layers;
  4. Burns top-left timestamp/`///` text into the Hook or burns the bottom-right Red Seal logo into the video frames (YouTube Studio's native Channel Watermark handles the bottom-right corner across the entire video);
  5. Keeps the Torn-Paper border after the `THREE DAYS EARLIER` transition into the Main Story;
  6. Synthesizes horror SFX in Python using sine waves or white noise instead of using CEO-selected Mass Horror SFX WAV files (`Q-20261109-0653-1c8d` & `Q-20261109-0730-27e6`).

## The spec

### 1. Channel identity & YouTube native watermark
1. **Channel Name & Handle:** `RED SEAL ARCHIVE` (`@redsealarchive`, Channel ID `UCA3806sh7qlV1S_oCIxlnjg`).
2. **HARD — Do NOT burn the bottom-right Red Seal logo into the video frames (`Q-20261109-0509-b6b4`).**
   **Why hard:** CEO ruling `Q-20261109-0509-b6b4` (*"เรื่อง Logo ตรงล่างขวา เราใช้ของ Youtube ที่มีให้ใส่ไหม ของเรามันจะได้ไม่ต้องใส่ในคลิปเอง"*). The `400x400` RGBA octagonal Red Seal (`redseal_youtube_watermark.png`) is uploaded once in YouTube Studio (`การปรับแต่ง -> โปรไฟล์ -> ลายน้ำของวิดีโอ -> ตลอดทั้งวิดีโอ`), so burning a duplicate logo into the MP4 causes double-stacking.
3. **HARD — Zero top-left text or `///` symbols during the Hook (`Q-20261109-0544-1bc3`).**
   **Why hard:** CEO ruling `Q-20261109-0544-1bc3` (*"ใส่กรอบไว้ดีแล้ว แต่ ข้อความ /// ไม่ต้องใส่มา บนซ้ายนะ"*). Keep the top-left corner completely clean (no red recording dot, no `03:17 AM`, no `EVIDENCE /// 01`).

### 2. Three-Phase Episode Framing Architecture (`Q-20261109-0544-1bc3` & `Q-20261109-0730-27e6`)

Every RED SEAL ARCHIVE episode follows a strict **Three-Phase Framing Architecture** so viewers immediately feel when the cold-open Hook ends and the full theatrical movie begins:

| Phase | Timeline Window | Border & HUD Rules | Pacing & Visual Content |
|---|---|---|---|
| **Phase 1 · Cold-Open Hook** | `0:00 – ~1:25` (`c01`–`c02`) | **Torn-Paper Border (`TORN_OV`) + Bottom Center Crimson Waveform (`by = H-48`) ONLY.** Zero top-left text, zero `///`, zero bottom-right logo. | Rapid story-synced cuts (`4.5–8.0s` per spoken clause, `10–15` distinct shots in the first `85s`). Build curiosity and dread without spoiling the climax. Use Type C (bordered scene), Type D (evidence macro with crimson focal circle), and Type E (dual split screen). |
| **Phase 2 · Pre-Story Transition Card** | `~1:25 – ~1:28.5` (`3.3–3.8s`) | **Full-Bleed `1920x1080` (NO Torn-Paper Border, NO HUD).** | Narrator speaks **`"ย้อนกลับไปเมื่อสามวันก่อน..."`** synced with a full-bleed dark drifting mist card displaying tracked-out serif English text **`THREE DAYS EARLIER`** (`LiberationSerif-Bold`, `64px`, `+16px` tracking) + expanding crimson underline + deep sub-bass boom (`Q-20261109-0544-1bc3`). |
| **Phase 3 · Main Story (`เข้าเรื่องเต็ม`)** | `~1:28.5 – End` (`~12:50–13:10`) | **100% Full-Bleed `1920x1080` Widescreen Cinema (`ฉากเต็มเหมือนดูหนังจริงได้เลย` — ZERO Torn-Paper Border, ZERO bottom waveform HUD, ZERO top-left text).** | **Story-Synced Beat-by-Beat Cuts (`55–65+` shots per episode)** aligned to exact spoken sentence pauses (`find_pause_in_wav`), where every cut displays the exact character action, prop, or horror event being narrated at that second (`Q-20261109-0933-0c3a` & `Q-20261109-1008-f4ae`). Act chapter cards also render as full-bleed dark mist serif typography without torn-paper boxes. |

### 3. Story-Synced Beat-by-Beat Visuals & Episode-Specific Cast (`Q-20261109-0933-0c3a` & `Q-20261109-1008-f4ae`)

1. **HARD — Episode-Specific Cast & Scene-Specific Character Generation (`Q-20261109-0933-0c3a`).**
   **Why hard:** CEO ruling `Q-20261109-0933-0c3a` (*"ฉันคิดว่า คุณใช้ชายคนเก่า บ่อยไปนะ แนะนำให้ generate คนใหม่เมื่อเปลื่ยนฉากใหม่"*): Never reuse a protagonist sprite (`SPRITES_WALK_BACK`) or character image from a previous episode or paste the same static cutout into unrelated scenes. Every episode and every distinct scene action must generate its own distinct character matching the script's exact age, clothing, posture, and emotion (e.g., EP.1 = Natee in the rubber plantation; EP.2 = Keng at the highway convenience store; EP.3 = 26-year-old factory worker Karn in a soaked navy windbreaker + 70-year-old hunched landlady counting wooden prayer beads).
2. **HARD — Story-Synced Beat-by-Beat Visuals, Zero Fixed-Timer Plate Looping (`Q-20261109-0933-0c3a`).**
   **Why hard:** CEO ruling `Q-20261109-0933-0c3a` (*"ภาพมันแทบจะฟรี แต่คุณใส่ภาพมา ซ้ำๆ แต่ไม่จริงกับ เนื้อเรื่องทหรือ ท่อนที่กำลังเล่าเลย อย่าอิงตามเวลาที่ต้องเปลื่ยนกี่วอเปลื่ยนรอบนึง แต่ให้อิงตามจังหวะว่า วินาทีนี้ควรแสดงภาพอะไรให้คนดู"*): Image generation is virtually free — never generate only 8 plates and loop them on a fixed timer (`6.5s` `shot_cycles`).
   - `[SUPERSEDED 2026-11-09]` "Cuts every `6.0–6.5s` across 8 base plates using `shot_cycles`" — replaced by CEO ruling `Q-20261109-0933-0c3a` and validated in `Q-20261109-1008-f4ae` (`ep03` v5 Master).
3. **Mandatory Beat-by-Beat Visual Pipeline (`/opt/MoonieXHQ/Work/ghost-pilot/ep03/build_ep03_full_v5.py`):**
   - **Step A · Map Spoken Sub-Beats per Voice Block (`c01..c22`):** Read each voice block's Thai transcript and break it into `2–3` concrete visual sub-beats (`50–65` total shots across the episode) so every new noun, prop, rule, or character action triggers a visual cut.
   - **Step B · Detect Exact Sentence Pauses in Each WAV (`find_pause_in_wav`):** Compute 50ms RMS energy windows on `voice/cXX.wav` and locate the local silence valley closest to each sentence boundary (`ratios=[0.33, 0.67]` or `[0.48]`). Cut the visual sub-shots at those exact timestamps (`start_sec .. end_sec`) so the image changes at the exact instant the narrator finishes one clause and begins the next.
   - **Step C · Generate 32–45+ Unique `16:9` Story-Beat Plates (`epXX_s01..s32+`):** Generate a dedicated photorealistic `16:9` plate for every spoken sub-beat (parallelized across 3 `image-generator` subagents). Every plate must show the exact object or action being narrated at that second (e.g., `s03` Karn soaked in rain reading the `"ว่างห้องเดียว 404 — 1,500 บาท/เดือน"` sign -> `s04` 70-year-old landlady counting prayer beads -> `s05` macro of brass key with faded red thread -> `s08` Karn holding the 5-rules notebook page inside the open teak wardrobe -> `s11` Karn's eye pressed to the brass peephole -> `s14` Karn lying on his side staring at the wall while black water drips beside his pillow -> `s18` macro of blood-scratched warning under the red wax seal -> `s20` Karn wrapping sacred white thread around the bathroom doorknob).
   - **Step D · 24fps Living Motion + Action-Specific FX Overlays:** Every story-beat shot renders at `24fps` with continuous camera motion (`pan_right`, `push_in`, `pull_back`, `dolly_left`, plus damped sinusoidal `shake` on horror hits), atmospheric particles (`RAIN_RGB`, `DUST_24`, `FOG_STRIP`), dynamic lighting (`lantern_flicker`, `red_pulse`, `lightning`, `sunrise_warm`), and beat-specific overlays (`peephole_eye_zoom`, `black_drip` falling from the ceiling crack, `blood_seep` under the wardrobe, `3way_flash` during the 04:30 AM siege, `evidence_circle` on clues).
4. **HARD — Every episode must define its `CAST-PROPS-LOCATIONS-STATES.md` registry before rendering.**
   **Why hard:** Separating characters, props, and locations into state-driven layers prevents baked-in background artifacts and ensures visual continuity across all 32+ plates.
5. **4-Frame Isolated Character Sprite Sheets (`sprites/*_4f_*.jpg`) — Optional Layer for New Episode-Specific Characters Only:**
   - When a shot uses a multi-layer walking or door-interaction rig, generate a **new episode-specific** `16:9` (`1376x768`) 4-frame horizontal sprite sheet on a pure solid `#FFFFFF` studio background (`extract_4_sprites()` + `sample_sprite_cycle()`). Never reuse another episode's sprite sheet.
6. **HARD — 100% Photorealistic Base Plates (No flat vector prop drawings).**
   **Why hard:** Close-up shots of amulets, sacred white thread (`สายสิญจน์`), keys, notebook rules, and rooms must come from photorealistic plates rather than drawing flat `ImageDraw.ellipse` / `rectangle` vector shapes.

### 4. Spatial camera-axis continuity (`Q-20261108-1604-6e38`)
Every threshold scene (door, window, corridor, mirror, wardrobe) must pass 4 spatial checks before rendering:
1. **Interior vs Exterior lock:** Establish clearly whether the camera is inside looking out (`ภายในมองออก`) or outside looking in (`ภายนอกมองเข้า`). Never flip dry wood flooring and rain-soaked porch planks between cuts.
2. **Left / Right / Front / Back (`ซ้าย/ขวา/หน้า/หลัง`) hardware lock:** If the door handle/latch is on the **right** from the interior POV, it stays on the **right** in every interior close-up and shifts to the **left** only on a true 180° reverse shot from outside.
3. **Closed-to-Open state rig:** Show the door/wardrobe **closed** before the knock or creak opens it. Never start an opening-door beat with the door already ajar.
4. **Directional motion vector:** Footprints, shadows, or entities entering from outside must point **inward** (`toe-box facing into the room, heel toward the threshold`) and progress step-by-step across the threshold.

### 5. Single Narrator (`Jade Tally` tone) & Mass Horror SFX Library (`-14.0 LUFS`)
1. **Single Narrator Rule (CEO ruling 2026-11-09):**
   - Every episode is narrated by **ONE single storyteller (`ผู้บรรยายคนเดียวตลอดทั้งเรื่อง`)** using `fal-ai/gemini-3.8-flash-tts` (`tools/fal_tts.py`), preset voice **`Algenib`**, with the `Jade Tally` storytelling pace (`9.0–11.0 chars/s`, `105–125 Hz` median F0).
2. **HARD — Use ONLY the 24 CEO-Approved Mass Horror SFX (`horror-curated-48k/` / `sfx-horror-pack/`, `Q-20261109-0750-e968` & `Q-20261109-0750-57ad`) + 17 Approved Editor SFX (`CMO_Standard_EditorSFX`).**
   **Why hard:** CEO listening-test approvals `Q-20261109-0750-e968` (`A–L`) and `Q-20261109-0750-57ad` (`A–L`, *"ได้ทั้งหมดเลย Update skill ได้เลยนะ ฝาก โพส แก้ EP 1 ด้วยและ ตัดต่อ EP2 ต่อได้เลย"*). Never synthesize wood knocks, creaks, footsteps, thunder, rain, or impacts in Python with sine waves/noise; always load the real 48 kHz WAV files in `/Users/gob/MoonieXHQ/Assets/BlackLiquidity/sfx-mass-pack/horror-curated-48k/` (mirrored on Contabo at `/opt/MoonieXHQ/Work/ghost-pilot/sfx-horror-pack/`):

   | # | SFX ID (`horror-curated-48k/`) | Mixkit Source | Dur | Gain | สถานการณ์ที่ใช้ในช่องผี (When to Use) |
   |---|---|---|---|---|---|
   | `01` | `wood_door_knock_01.wav` | `#197` | `1.15s` | `-6.5 dB` | เสียงผีเคาะประตูไม้หนา ตู้เสื้อผ้า หรือกระจกตู้แช่ 3 ครั้งกลางดึก |
   | `02` | `door_slam_heavy_02.wav` | `#194` | `1.69s` | `-6.0 dB` | จังหวะผีทุบหรือกระแทกบานประตูไม้สะเทือนทั้งบ้าน/หอพัก |
   | `03` | `scary_wood_door_open_03.wav` | `#190` | `3.52s` | `-8.0 dB` | บานประตูไม้หรือบานตู้เสื้อผ้าค่อยๆ แง้มเปิดเองในความมืด |
   | `04` | `creaky_door_close_04.wav` | `#189` | `2.40s` | `-8.0 dB` | บานประตูค่อยๆ ปิดลงเองช้าๆ ขังตัวละครไว้ข้างใน |
   | `05` | `old_iron_door_lock_05.wav` | `#187` | `5.21s` | `-7.5 dB` | มือสั่นๆ บิดลูกบิด คล้องแม่กุญแจ หรือสับกลอนประตูเหล็กเก่าขวางผี |
   | `06` | `wood_floor_creak_06.wav` | `#337` | `1.02s` | `-8.5 dB` | เสียงพื้นไม้/เพดานลั่นเอี๊ยดตามก้าวเดินบนชั้นบนหรือระเบียง |
   | `07` | `mud_footsteps_07.wav` | `#537` | `31.6s` | `-9.5 dB` | ฝีเท้าเดินลุยทางโคลนเปียกฝนเข้าสวนยางหรือซอยเปลี่ยว |
   | `08` | `mud_puddle_steps_08.wav` | `#536` | `3.75s` | `-8.5 dB` | เสียงฝีเท้าเปียกน้ำเดินย่ำหรือเสียงน้ำดำหยดลงบนพื้นกระเบื้อง |
   | `09` | `forest_dry_leaves_09.wav` | `#1222` | `31.8s` | `-10.0 dB` | เสียงเดินสำรวจรอบบ้านพักหรือได้ยินคนเดินวนนอกหน้าต่าง |
   | `10` | `run_in_forest_10.wav` | `#1236` | `11.2s` | `-8.0 dB` | ฉากเปิดเรื่อง (Hook) หรือฉากวิ่งหนีตายลงบันไดตอนรุ่งสาง |
   | `11` | `slow_heartbeat_11.wav` | `#494` | `45.3s` | `-10.5 dB` | คลอเบาๆ ตอนตัวละครกลั้นหายใจแอบมองตาแมวหรือคลุมโปงบนเตียง |
   | `12` | `fast_heartbeat_12.wav` | `#493` | `9.87s` | `-8.5 dB` | เร่งจังหวะกดดันช่วงพีคก่อนผีประชิดตัวหรือเคาะพร้อมกัน 3 ทิศทาง |
   | `13` | `rain_metal_roof_13.wav` | `#1265` | `113.1s` | `-18.0 dB` | เสียงบรรยากาศหลัก (Bed) ฝนตกกระทบหลังคาสังกะสี/ระเบียงหอพักยามดึก |
   | `14` | `jungle_thunderstorm_14.wav` | `#2415` | `49.0s` | `-17.0 dB` | ปูบรรยากาศฉากภายนอกอาคารท่ามกลางพายุฝนและฟ้าร้องไกลๆ |
   | `15` | `close_thunder_strike_15.wav` | `#1300` | `8.87s` | `-6.5 dB` | ใส่คู่จังหวะแสงแฟลชฟ้าแลบส่องให้เห็นเงาร่างที่ระเบียงหรือหน้าบ้าน |
   | `16` | `deep_thunder_rumble_16.wav` | `#1296` | `18.2s` | `-9.5 dB` | ฟ้าร้องคำรามทุ้มต่ำคลอหลังประโยคคำเตือนเรื่องกฎต้องห้าม |
   | `17` | `scary_graveyard_wind_17.wav` | `#1157` | `12.4s` | `-12.0 dB` | ลมหนาวหวีดหวิวพัดผ้าม่านระเบียงหรือตอนประตูเปิดเอง |
   | `18` | `horror_ambience_drone_18.wav` | `#2482` | `82.1s` | `-19.0 dB` | คลื่นความถี่ต่ำหลอนกดดันประสาทปูพื้นช่วงหลังเที่ยงคืนถึงตีสี่ครึ่ง |
   | `19` | `creepy_tomb_ambience_19.wav` | `#2500` | `41.2s` | `-18.0 dB` | บรรยากาศโถงทางเดินชั้น 4 ห้องน้ำกระจกปิดถุงดำ หรือห้องปิดตาย |
   | `20` | `deep_whoosh_impact_20.wav` | `#1143` | `4.06s` | `-6.0 dB` | บูมทุ้มลึกตัดเข้าป้ายย้อนเวลา (`THREE DAYS EARLIER`) และป้ายเปลี่ยนบท `ACT` |
   | `21` | `hard_horror_hit_drum_21.wav` | `#565` | `4.14s` | `-6.5 dB` | กลองทุ้มกระแทกจังหวะตกใจเมื่อเห็นลูกตาในตาแมวหรือเงาผีบนเพดาน |
   | `22` | `horror_heartbeat_swoosh_22.wav` | `#489` | `51.0s` | `-8.5 dB` | เสียงวูบหัวใจกระตุกเชื่อมฉากตอนตัวละครเริ่มรู้ตัวว่าทำผิดกฎหรือเจอกับดักหมึกแดง |
   | `23` | `terror_sweep_darkness_23.wav` | `#2630` | `7.95s` | `-8.0 dB` | เสียงกวาดความมืดตอนไฟดับทั้งชั้นหรือเงาผีเคลื่อนผ่านหน้าต่าง |
   | `24` | `horror_swish_cut_24.wav` | `#1495` | `2.84s` | `-7.5 dB` | เสียงตวัดคมๆ จังหวะตัวละครหันขวับไปมองประตู ตู้เสื้อผ้า หรือกระจกเงา |

3. **Five-Layer Audio Stem Hierarchy (`loudnorm=I=-14.0:TP=-1.5:LRA=11`):**
   - **L1 · Single Narrator VO (`Algenib`):** `0 dB` anchor (`-14.0 LUFS` integrated).
   - **L2 · Sub-bass Drone & Chapter Impacts:** `-24 dBFS` continuous drone (`-4 dB` sidechain-ducked under VO); `-6.0 dB` chapter impact boom (`deep_whoosh_impact_20.wav`) on `THREE DAYS EARLIER` and Act cards.
   - **L3 · Environment Bed (Monsoon Rain, Wind, Corridor Ambience):** `-22 dBFS` (`2.5 kHz` low-pass indoors; full-spectrum outdoors).
   - **L4 · Hard Horror Foley (Panned):** `-10 to -6 dBFS` real WAV recordings of 3 slow wood knocks, rusted iron latch, creaking teak door, wet footsteps, and heartbeat spikes aligned to exact story beats.
   - **L5 · Micro-Silence Drop:** Pull L2+L3 down `-60 dBFS` for `0.4–0.7s` right before the 3rd knock or ghost reveal.

### 6. 3-Way A/B/C Thumbnails, 8-Language Metadata & 6 Foreign Audio Tracks (`Q-20261108-1944-71db` & `Q-20261109-1008-f4ae`)
Every approved episode master (`redseal-epXX-master-v5.mp4`, transcoded with `-c:v libx264 -preset veryfast -crf 21 -c:a copy` so file size is `~250–300 MB` and Contabo `/` free space stays `> 6.5 GB`) is published to `@redsealarchive` (`UCA3806sh7qlV1S_oCIxlnjg`) via `/opt/MoonieXHQ/Work/ghost-pilot/build_ep03_multilang_and_thumbs.py` and `/opt/MoonieXHQ/Work/ghost-pilot/publish_ep03_v5_master.py`:
1. **3-Way A/B/C Thumbnails (`1280x720`, both `TH` and `EN` editions in `thumb_study/final/`):**
   - **Variant A (`epX_gpt_reallens_TH.jpg` / `_EN.jpg`):** `Real Lens` composition — terrified episode protagonist on right 40% + horror entity/clue in background with crimson focal circle + top-left red pill badge + bottom-left 2-line stacked `Kanit-ExtraBold` title.
   - **Variant B (`epX_varB_lhondiary_TH.jpg` / `_EN.jpg`):** `ไดอารี่ผีหลอน` style — dramatic close-up encounter with bold high-contrast typography.
   - **Variant C (`epX_varC_miti6_TH.jpg` / `_EN.jpg`):** `มิติที่ 6` style — atmospheric wide occult/folklore scene with sacred thread / yantra visual hook.
2. **8-Language Titles, Descriptions & Localized Covers (`multilang_pack.json` -> `/video/<vid>/translations`):**
   - Attach localized title, chapter-timestamped description, and localized `EN` cover across all **8 target languages**: English (`en`), Indonesian (`id`), Hindi (`hi`), Japanese (`ja`), Vietnamese (`vi`), Spanish (`es`), Traditional Chinese (`zh-TW`), and Simplified Chinese (`zh-CN`).
3. **6 Foreign Audio Tracks (`epXX_<lang>_audio.m4a`, `192k` AAC at `-14.0 LUFS`):**
   - Synthesize full 22-block foreign narrations (`c01..c22`) for **`en`, `id`, `hi`, `ja`, `vi`, `es`**, time-fitted to each Thai voice slot (`mp3_to_fitted_wav`), and mix them over the episode's ducked horror soundscape bed (`bed_ducked = mix_full - th_voice * 0.85`) so foreign viewers hear every rain streak, thunderclap, heartbeat, and wood knock.
   - **Edge TTS Vietnamese (`vi`) reliability rule:** Microsoft Edge TTS rejects non-zero prosody tags (`rate`/`pitch`) on `vi-VN` (`No audio was received`) and rate-limits high concurrency. Always use `rate="+0%", pitch="+0Hz"`, `asyncio.Semaphore(2)`, and alternate `vi-VN-NamMinhNeural` / `vi-VN-HoaiMyNeural` on retry, with zero stray Thai characters in the Vietnamese script.
4. **Release Timing (`19:00` Bangkok Time):**
   - Publish immediately as `สาธารณะ` (`PUBLIC`) or schedule (`กำหนดเวลาเป็นสาธารณะ` / `SCHEDULE`) for **`19:00` (`19:00 น.`)** prime-time horror viewing as directed by the CEO (`Q-20261109-1008-f4ae`).

## The check

Run the skill linter and verify every rendered episode (`<video.mp4>`) before raising a `/run` card:

```bash
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python \
  /Users/gob/MoonieXHQ/Agents/Core/scripts/skill-lint.py check \
  /Users/gob/MoonieXHQ/Agents/Core/.claude/skills/CMO_Standard_GhostChannel_DNA/SKILL.md
```

And on the rendered episode master (e.g., `/opt/MoonieXHQ/Work/ghost-pilot/ep03/out/redseal-ep03-master-v5.mp4`):
1. Resolution is `1920x1080` at `24 fps`, integrated loudness `I:` is `-14.0 LUFS` (`±1.0 LU`), True Peak `<= -1.0 dBTP`.
2. Contact sheet (`ep03_full_v5_contact_sheet.jpg`) confirms:
   - Hook (`0:00 – ~1:25`) has the Torn-Paper border + bottom waveform bar, with **ZERO top-left text/`///`** and **ZERO bottom-right burned-in logo**.
   - Transition (`~1:25 – ~1:28.8`) shows full-bleed **`THREE DAYS EARLIER`** synced to spoken `"ย้อนกลับไปเมื่อสามวันก่อน"`.
   - Main Story (`~1:28.8 – End`) is **100% Full-Bleed `1920x1080` cinema** with zero border, zero HUD, and **55–65+ story-synced shots** built from **32+ unique episode-specific 16:9 plates** cut at exact spoken sentence pauses (`find_pause_in_wav`), with zero reused characters from older episodes.

## Good vs bad

- **Good (`/opt/MoonieXHQ/Work/ghost-pilot/ep03/out/redseal-ep03-master-v5.mp4`, video ID `o18rg9QYs0I`, approved by CEO in `Q-20261109-1008-f4ae`):**
  - Generated 32 unique 16:9 photorealistic plates (`ep03_s01..s24` + 8 base plates) featuring EP.3's own cast (26-year-old factory worker **Karn** and the **70-year-old landlady** counting prayer beads — zero reuse of Natee from EP.1).
  - Cut across **57 story-synced shots** using `find_pause_in_wav()` so every spoken sentence displays the exact visual described at that second (Karn soaked in the rain reading the `ห้อง 404 — 1,500 บาท/เดือน` sign -> landlady handing over the brass key tied with faded red thread -> Karn reading the 5 rules inside the teak wardrobe -> eye pressed to the brass peephole at 01:30 AM -> lying on his side watching black water drip beside his pillow at 02:15 AM -> fifth broken-necked figure between four white shirts on the balcony -> blood-scratched warning under the red wax seal -> chaining the wardrobe with a wooden chair and brass padlock -> wrapping sacred white thread on the bathroom doorknob -> praying inside the red talisman boundary until 06:00 AM golden dawn).
  - Uploaded with 3-way A/B/C thumbnails, 8-language titles/descriptions/covers, 6 foreign audio tracks (`en`, `id`, `hi`, `ja`, `vi`, `es`), and scheduled for `19:00`.
- **Bad (`ep03` `v4` draft rejected in `Q-20261109-0933-0c3a`, and `ep01` `v1`–`v3` drafts rejected in `Q-20261108-1425-709d`, `Q-20261109-0509-b6b4`, `Q-20261109-0544-1bc3`):**
  - Reused the old character sprite from EP.1 (`ชายคนเก่า`) across scenes/episodes; generated only 8 plates and cycled them on a fixed `6.5s` timer (`shot_cycles`) so the image on screen did not match the sentence being narrated; held static stills without 24fps motion/particles; or burned top-left `///` text and a duplicate bottom-right logo into the frames.

## Field notes
- 2026-11-09 [MISSING] §1-6 — CEO approved `ep01_1min_motion_v4.mp4` (`Q-20261109-0653-1c8d`), full 13:08 master `redseal-ep01-master-v4.mp4` (`Q-20261109-0730-27e6`), and all 24 Mass Horror SFX across `Q-20261109-0750-e968` (`01–12` Foley) and `Q-20261109-0750-57ad` (`13–24` Storm, Ambience & Horror Impacts: *"ได้ทั้งหมดเลย Update skill ได้เลยนะ ฝาก โพส แก้ EP 1 ด้วยและ ตัดต่อ EP2 ต่อได้เลย"*) · evidence: Run Inbox records `Q-20261109-0653-1c8d`, `Q-20261109-0730-27e6`, `Q-20261109-0750-e968`, `Q-20261109-0750-57ad` · status: promoted
- 2026-11-09 [MISSING] §2-6 — CEO ruling on `Q-20261109-0933-0c3a` and approval of `ep03` v5 (`Q-20261109-1008-f4ae`, `o18rg9QYs0I`): never reuse an old character across episodes/scenes (*"คุณใช้ชายคนเก่า บ่อยไปนะ แนะนำให้ generate คนใหม่เมื่อเปลื่ยนฉากใหม่"*) and never loop a small pool of plates on a fixed timer — generate 32+ dedicated plates synced to the exact spoken beat/sentence pause (`find_pause_in_wav`) at each second (*"ภาพมันแทบจะฟรี แต่คุณใส่ภาพมา ซ้ำๆ แต่ไม่จริงกับ เนื้อเรื่องทหรือ ท่อนที่กำลังเล่าเลย อย่าอิงตามเวลาที่ต้องเปลื่ยนกี่วอเปลื่ยนรอบนึง แต่ให้อิงตามจังหวะว่า วินาทีนี้ควรแสดงภาพอะไรให้คนดู"*), then publish with 8 languages + 6 foreign audio tracks (`en`, `id`, `hi`, `ja`, `vi`, `es`) + 19:00 schedule · evidence: Run Inbox records `Q-20261109-0933-0c3a`, `Q-20261109-1008-f4ae`, `/opt/MoonieXHQ/Work/ghost-pilot/ep03/build_ep03_full_v5.py` → §2, §3, §6, §Good vs bad · status: promoted
