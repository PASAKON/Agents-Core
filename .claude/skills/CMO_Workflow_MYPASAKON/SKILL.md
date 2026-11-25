---
name: CMO_Workflow_MYPASAKON
kind: workflow
description: 'WORKFLOW — End-to-end MYPASAKON (@mypasakon) TikTok episode loop: script & client handoff -> raw CEO voice (.mp4/.mov) Dead-Air & retake trim -> Gate 1 /run audio approval -> 3 x 15s Lipsync (or $0 demo sync) -> BL-grade full-length Style A Neon Green (#040A07 x #7CFF00) cut -> Gate 2 /run video approval -> Drive & MoonieX Poster publish. Trigger on /CMO_Workflow_MYPASAKON, "ทำคลิป MYPASAKON", "ตัดคลิป MYPASAKON", "ตัด Death Air MYPASAKON", "MYPASAKON workflow", "ทำ EP MYPASAKON". Not for BLACK LIQUIDITY (CMO_Workflow_BlackLiquidity) or ILAG short films (CMO_Workflow_ShortFilm).'
owner: CMO
audience: [cmo, cto, project_head, video_editor, developer]
created_by: agent
author: {role: project_head, date: "2026-11-25"}
improved_by: []
aka: [mypasakon-workflow]
---

# MYPASAKON episode — end to end (`@mypasakon`)

One run turns the CEO's real recorded voice (`.mp4`/`.mov`/`.m4a` dropped into `Audio/` on Drive) plus the episode `Script` & client brief into a finished `1080×1920 @ 30fps` TikTok episode in **`MYPASAKON` Minimalist Luxury Neon Green (`Style A: RAZOR CHAMFER`, `#040A07 × #7CFF00`)**, modeled on `CMO_Workflow_BlackLiquidity`'s full-loop discipline with **two mandatory CEO checkpoints on `terminal.mooniex.com/run`** (`Q-20261125-1010-e3b0`) and **full-content length** (`Q-20261125-1010-88f9`, typically `2:30–4:00` covering the complete tutorial/brief, never truncated to 60s unless requested).

Order, tools, dependencies, cost ceiling, verify checks and node ids live in `flow.yaml` beside this file; visual tokens live in `CMO_Standard_MYPASAKON_NeonDNA`; client script handoff rules live in `CMO_Procedure_ClientScript_Handoff`; 5-hashtag rules live in `CMO_Rules_TikTok_Hashtags`.

## How an agent joins a run

1. Open or create the episode's `STATUS.md` (template below).
2. Read `node:`, look up that node in `flow.yaml`, read the matching `### Step` below, and read its owner skill.
3. Send all CEO media approvals (`Gate 1` audio and `Gate 2` final video) to `terminal.mooniex.com/run` via `tools/ask_run.py ask --project "MYPASAKON" --lane "cmo" --media ...` (`ALL_Protocol_RunInbox`). Never ask in chat or spend paid Lipsync credits before `gate1_audio` passes.

## Rules that hold on every step

1. **HARD — Gate 1 before Lipsync (`ALL_Rules_Approvals`, `Q-20261125-1010-e3b0`).** Never fire paid Lipsync API calls until the CEO taps `ใช้ได้` on the trimmed master `.mp3` in `gate1_audio`. Why: Lipsync bills per second; trimming Dead Air and retakes first plus slicing `3 × 15s` avatar windows saves 60–80% of Lipsync spend and prevents re-billing on rejected cuts.
2. **Spoken-meaning fidelity over verbatim reading.** The CEO speaks naturally and does not read the `Script` word-for-word. During `audio_trim`, keep natural conversational phrasing (`นะครับ`, `เนี่ย`, spontaneous examples) while pruning:
   - **Dead Air** (`> 0.25s` pauses tightened to natural `0.06–0.16s` breaths),
   - **False starts & tongue-slips** (`"ใน และ..."`, `"เขาเรา..."`, `"อาจจะมี เอ่อ..."`),
   - **Repeated takes** (when the CEO says the same sentence twice, keep the cleaner, more confident delivery),
   - **Looping tangents** that drift away from the `Script` / client brief.
3. **Zero mid-syllable clips.** Snap every cut to a zero-crossing (`±5ms`) with `10ms` raised-cosine fades (`tools/mypasakon_audio_trim.py render`) and **listen to the rendered seams by ear** (`read_file` on verification `.mp3` halves) before raising `gate1_audio`.
4. **Drive & Disk Hygiene.** Read `CXO_Rules_GDrive_Filing` before touching Google Drive (`ALL DRAFT/MYPASAKON`, folder ID in `CXO_Knowledge_GDrive_FolderMap`). Never commit media to git; delete temporary raw `.mov` downloads and intermediate segment MP4s once the final cut passes QC (`ALL_Rules_DiskHygiene`).

## The steps

### Step 1 · Script and folder [node: script]
Do: create `ALL DRAFT/MYPASAKON/<ClientOrCode> | <Topic>/` with `Audio/`, `AI Drafts/`, `Finals/`, write the shared Google Doc `Script`, and deliver the pure 5-hashtag `Topic / Tags / Script` block (`#MYPASAKON` in Slot #1 + 4 search-matched viral tags per `CMO_Rules_TikTok_Hashtags`) following `CMO_Procedure_ClientScript_Handoff`. For non-sponsored episodes, follow the same spoken Hook -> Step-by-Step Value -> Trader Discipline / Risk Disclaimer arc.
Gate: shared Script Doc and Drive subfolders exist, and client brief compliance (banned words, required CTAs/tie-ins) is verified.

### Step 2 · Script approval [node: script_ok]
Do: wait for CEO approval (and client/broker sign-off on sponsored campaigns). Any client revision note goes back through `CMO_Procedure_ClientScript_Handoff` (update Google Doc in place + resend all pure blocks to Telegram and chat).
Gate: approved script version recorded in `STATUS.md`.

### Step 3 · Raw voice upload [node: raw_voice]
Do: the CEO records voice (often as an audio-only `.mp4`/`.mov` + optional pickup `.m4a` + screen recording `.mov`) into the episode's `Audio/` folder on Drive. Download into local scratch (`ilag_sync.py download`).
Gate: raw voice file (and any screen capture) verified locally via `ffprobe`.

### Step 4 · Voice dead-air trim [node: audio_trim]
Do:
1. Run `tools/mypasakon_audio_trim.py inspect --input <raw.mp4> [--insert <pickup.m4a>] --out-dir <work>` to extract `raw_44k.wav`, `raw_extracted.mp3`, and `speech_islands.json`.
2. Transcribe with timestamps (e.g., `mlx_whisper` locally at $0; purge HF cache right after if disk is tight) and compare every island against `Script` + client brief.
3. Build `edl_spec.json` dropping dead air, false starts, stumbles, repeated sentences, and looping explanations (gain-matching any pickup insert), then run `tools/mypasakon_audio_trim.py render --out-dir <work> --edl-spec edl_spec.json --out-prefix MYPASAKON_<EP>_Trimmed_Clean` (`highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11`).
4. **Ear-check mandatory:** listen to the rendered `.mp3` via `read_file` to catch any clipped Thai finals (`ครับ`, `ต่างประเทศ`, `เริ่มต้น`) or leftover filler (`เอ่อ`, `แล้วๆ`) and refine `edl_spec.json` before Gate 1.
Gate: clean `-14.0 LUFS` `.mp3`/`.m4a` + `edit_decision_list.json` with zero clipped words and 100% brief fidelity.

### Step 5 · Gate 1 audio approval [node: gate1_audio]
Do: send `MYPASAKON_<EP>_Trimmed_Clean.mp3` to `/run` as a single-media Question Card (`tools/ask_run.py ask --project "MYPASAKON" --lane "cmo" --media <trimmed.mp3> --caption "..."`, single media item without `--pick` so `/run` renders `ใช้ได้ / แก้ / ไม่เอา`). Print Card ID + URL and stop turn.
Gate: CEO taps `ใช้ได้` (`ask_run.py wait <Q-id> --max-wait 1` verified). If `แก้`, apply the CEO's timestamp notes in `edl_spec.json` and re-run Step 4.

### Step 6 · 15s avatar chunks [node: chunks_15s]
Do:
- **Production run:** slice `3 × ~15s` clean avatar voice chunks (`Hook` `0–15s`, `Mid Core Insight` ~45% mark, `Closing CTA/Discipline` tail `15s`) snapped to natural phrase boundaries in `edit_decision_list.json`:
  `tools/mypasakon_audio_trim.py chunks --audio <trimmed.mp3> --edl edit_decision_list.json --out-dir <work>/chunks --chunk-sec 15 --count 3`
- **Zero-cost `--demo` run (reusing pre-rendered raw-timed `lip_1..3.mp4`):** pass `"lip_ranges"` in `edl_spec.json` and run `tools/mypasakon_audio_trim.py sync-lip --edl edit_decision_list.json --master <trimmed.mp3> --lip sync_lip1=lip_1.mp4 --lip sync_lip2=lip_2.mp4 --lip sync_lip3=lip_3.mp4 --out-dir <work>/synced_lips` so every dead-air/retake cut inside the avatar clips stays `0`-frame locked at `30fps`.
Gate: `lipsync_chunks.json` (3 chunks) or `sync_manifest.json` (`frames == expected_frames` on all 3 tracks).

### Step 7 · Avatar lipsync [node: lipsync]
Do: in production runs, send the 3 `~15s` chunks (`~45s` total ≈ `$0.53`) through Lipsync using the episode's `MYPASAKON` talking-head reference plate, and save `lip_1.mp4`, `lip_2.mp4`, `lip_3.mp4` to `AI Drafts/` on Drive. In `--demo` runs with `sync_manifest.json`, skip paid generation (`$0.00`).
Gate: all 3 avatar clips verified in mouth sync at `30fps`.

### Step 8 · Screen and Flow B-roll [node: broll_footage]
Do: map every non-avatar scene (`~15s`–`208s` across the episode) to real screen recordings, progressive kinetic cards, or `Google Flow Omni 1.2 Flash` dark-emerald B-roll (`CMO_Standard_MYPASAKON_NeonDNA` §6):
- ** Focal-crop Retina desktop captures (`2880×1800`):** crop directly onto the active chart, headline, or button (`crop=1840:1360:...` or `crop=1960:1420:...`) so mobile viewers can read UI text effortlessly; speed-ramp `2.2×` (`setpts=0.45*PTS`) on slow typing waits.
- **White-background `TradingView` -> Dark Neon conversion:** apply `negate,hue=h=180:s=1.3,eq=contrast=1.18:brightness=-0.03` so white charts turn `#000000` obsidian while preserving green/red candles and blue trend arrows.
- **Leak scrub:** inspect timestamps on every screen recording to exclude macOS Launchpad, Dock popups, notifications, personal tabs, or competitor broker ads.
Gate: every scene timestamp has clean dark-mode visual coverage with zero OS/PII leaks.

### Step 9 · Neon DNA full cut [node: compose_cut]
Do: assemble the full `30fps` `1080×1920` cut in **`Style A: RAZOR CHAMFER`** (`#040A07` obsidian canvas × `#7CFF00` electric lime, `12px–4px–1px` chamfered corner brackets, `Prompt` + `JetBrains Mono`) alternating the 4 `MYPASAKON` layout modes (`CMO_Standard_MYPASAKON_NeonDNA` + `CMO_Procedure_BlackLiquidity_Cut` pacing):
- **Mode 1 (Avatar Hero + Top `Style A` Window):** for close-up selfie plates (`1080×1920`), shift avatar down (`crop=1080:1680:0:0,pad=1080:1920:0:240:#040A07`) so headwear/forehead clears the `y=120..560` top window; place subtitle pill at `y=1610`.
- **Mode 2 (50/50 Split — Avatar Top + Live App Bottom):** `crop=1080:1240:0:320,scale=760:872` at `(160, 18)` so chin stays `>120px` above the `y=770` divider subtitle pill; `Style A` screen window at `y=900..1720`.
- **Mode 3 (`380×380` Neon Ring Avatar + Progressive Numbered Cards):** `crop=1060:1060:10:320,scale=380:380` inside a `4px` `#7CFF00` ring at `(350, 90)`, subtitle pill at `y=508`, and progressive `01 / 02 / 03` Razor Chamfer cards below (`y=660+`).
- **Mode 4 (Full-Focus Screen / Dual Comparison / Kinetic Cards):** zoomed live app windows (`y=150..1240` + bottom callout card `y=1290`), dual `AI Chart vs TradingView` stacked comparison, or red `✕ Myth` vs neon green `✓ Truth` cards with curved SVG connector arrows + subtle risk disclaimer pill at `y=1818`.
- **Audio design (`CMO_Standard_EditorSFX`):** pre-roll peak-aligned SFX from `Assets/BlackLiquidity/sfx-mass-pack/curated-48k` (sparse, purposeful, zero consecutive duplicates) + `BL07` dark-tech BGM (`tools/bgm_bed.py`, `-24.0 dB` ceiling + `-3.0 dB` speech ducking + `4s` fade-in/out), mastered to **`-14.0 LUFS` / `-1.5 dBTP`**.
Gate: exact frame count `round(trimmed_audio_dur * 30)` with zero frame gaps across all concatenated scenes.

### Step 10 · Cut and visual QC [node: qc_check]
Do: run `tools/mypasakon_audio_trim.py verify-cut --video <final.mp4> --audio <trimmed.mp3> --sheet <qc_8frame_sheet.jpg>` AND visually inspect a multi-mode contact sheet via `read_file` covering every avatar mode and every screen-capture scene. Fix and re-render individual scenes (`seg_XX_*.mp4`) if any text touches a face, clips inside the `380×380` circle, or shows a desktop artifact.
Gate: `verify-cut` returns `"ok": true` (`1080×1920`, `30.0 fps`, `-16.5..-11.5 LUFS`) and visual inspection passes 100%.

### Step 11 · Gate 2 video approval [node: gate2_video]
Do: send `MYPASAKON_<EP>_NeonFull_1080p.mp4` to `/run` (`tools/ask_run.py ask --project "MYPASAKON" --lane "cmo" --media <final.mp4> ...`), print Card ID + URL, and end turn. Note: when reading multi-media card picks back, always verify via `ask_run.py wait <Q-id> --max-wait 1` (`picked:` line) rather than trusting the mailbox wake summary's `choice` fallback.
Gate: CEO taps `ใช้ได้` on `/run`.

### Step 12 · Queue and Drive archive [node: publish]
Do: upload the approved `MYPASAKON_<EP>_NeonFull_1080p.mp4` and `MYPASAKON_<EP>_Trimmed_Clean.mp3` to the episode's `Finals/` and `Audio/` folders on Drive (`ilag_sync.py upload`, verify `md5`), then submit to `MoonieX Poster` (`tools/mooniex_poster.py`, `CMO_Procedure_MoonieXPoster_Queue`) with the approved 5-hashtag caption (`#MYPASAKON` first). Clean local intermediate scratch files (`ALL_Rules_DiskHygiene`).
Gate: Drive `md5` verified and `MoonieX Poster` 1-Card TikTok queue delivered.

## STATUS.md template

```
flow: mypasakon · run: <YYYY-MM-DD>-<ep-slug>
node: <current node id> · state: running | waiting:CEO | blocked:<blocker code>
done: [<node ids>]
blocker: <code> — <one line>
spent: $<cash> API · <turns> turns
gate1_card: <Q-id or pending>
gate2_card: <Q-id or pending>
```

## Field notes
- 2026-11-25 [MISSING] §Step 8 & §Step 10 OS leak scrub — on the initial `IUX24` full-loop Demo, raw `320.38s` voice + `5.01s` pickup trimmed `-29.4%` (`95.76s` dead air & 18 retakes removed) -> `229.63s` (`3:50`) master passed Gate 1 on first listen, and 8-frame visual QC caught a brief macOS Launchpad transition at `IUX24.mov` `t=157.6s` in `s24_warning_m2` (re-pointed to `t=138.5s` and re-rendered `seg_23` in 4s) · evidence: Q-20261125-1010-88f9, Q-20261125-1010-e3b0, Q-20261125-1018-c6f1, Q-20261125-1059-e579 · status: promoted
