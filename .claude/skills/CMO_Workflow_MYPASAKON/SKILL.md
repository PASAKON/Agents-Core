---
name: CMO_Workflow_MYPASAKON
kind: workflow
description: 'WORKFLOW — End-to-end MYPASAKON (@mypasakon) TikTok episode loop: script & client handoff -> raw CEO voice (.mp4/.mov) Dead-Air & retake trim -> Gate 1 /run audio approval -> 3 x 15s Lipsync -> Google Flow Omni 1.2 Flash 1080p winter knit sweater & studio restyle -> Viral x BL V7.8 Smart-Zoom cut -> Gate 2 /run video approval -> Drive & MoonieX Poster publish. Trigger on /CMO_Workflow_MYPASAKON, "ทำคลิป MYPASAKON", "ตัดคลิป MYPASAKON", "ตัด Death Air MYPASAKON", "MYPASAKON workflow", "ทำ EP MYPASAKON". Not for BLACK LIQUIDITY (CMO_Workflow_BlackLiquidity) or ILAG short films (CMO_Workflow_ShortFilm).'
owner: CMO
audience: [cmo, cto, project_head, video_editor, developer]
created_by: agent
author: {role: project_head, date: "2026-11-25"}
improved_by:
  - {role: project_head, date: "2026-11-26", note: "Added mandatory Step 8 (omni12_restyle: Google Flow Omni 1.2 Flash 1080p winter knit sweater + sharp studio upgrade + sync-omni FFT lock) and centered 304x304 Circular PiP per Q-20261126-1038-beb0"}
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
Do: in production runs, send the 3 `~15s` chunks (`~45s` total ≈ `$0.53`) through Lipsync using the episode's `MYPASAKON` talking-head reference plate, and save `lip_1.mp4`, `lip_2.mp4`, `lip_3.mp4` to `AI Drafts/` on Drive. In `--demo` runs with `sync_manifest.json`, skip paid fal generation (`$0.00`).
Gate: all 3 avatar clips verified in mouth sync at `30fps`.

### Step 8 · Omni 1.2 1080p restyle [node: omni12_restyle]
Do: upgrade all `3 × ~15s` avatar Lipsync clips (`lip_1..3.mp4`) through **Google Flow `Omni 1.2 Flash`** (`องค์ประกอบ` video-ingredient mode on `winbox:9226`, project `ee8f1998-bf36-4f01-9aa9-e9fc37e4c25b`, CEO ruling `Q-20261126-1038-beb0`):
1. Upload the `720p` Lipsync `.mp4` clips into the Flow project (`0` credits; ensure no frozen empty `flow.google.com` landing tab blocks CDP attach).
2. Stage `sheet.md` + `ledger.tsv` on Contabo (`/opt/MoonieXHQ/Work/mypasakon/<ep>/in/`) attaching `@lip_1`..`@lip_3` as `<VIDEO_REF_0>`, run `tools/flow_shoot_card.py --dry-run --model "Omni 1.2 Flash"` (`0` credits), then raise one exact-credit Command Card (`ask_run.py create --host contabo --script Agents-Core@<TIP>:tools/flow_shoot_card.py --spend-provider google-flow --spend-billing account --spend-unit credits ...`, `~4 cr/s` at `720p` + `1080p` export; measured `12 cr` for `4s` on `RUN-20261126-1015-8e87`).
3. Prompt contract: strictly preserve the CEO's exact face, `RICH` black beanie, eye gaze, frame-by-frame Thai lip-sync mouth movements, and handheld mic while restyling ONLY clothing into a **smart-casual Western winter charcoal-black ribbed merino wool mock-neck knit sweater** (no logos) and upgrading the background into a **crisp `1080×1920` architectural wood-slat & subtle emerald-teal rim-lit studio**.
4. **Mandatory Phase-Lock (`sync-omni`):** Flow adds a `~280–310ms` silent lead-in (`+292.7ms` measured on `RUN-20261126-1015-8e87`). Run `tools/mypasakon_audio_trim.py sync-omni --omni <shot.mp4> --ref <lip.mp4> --out omni_lip<N>_1080p.mp4` on all 3 clips so FFT waveform cross-correlation strips the lead-in, resamples `24fps -> 30fps`, and locks mouth sync to `0.0ms` drift.
Gate: all 3 `omni_lip1..3_1080p.mp4` verified `1080×1920 @ 30fps` (`waveform_corr >= 0.30`), intact facial identity, winter knit sweater, and `docs/ops/credit-ledger.jsonl` updated.

### Step 9 · Screen and Flow B-roll [node: broll_footage]
Do: map every non-avatar scene (`~15s`–`208s` across the episode) to Smart-Zoom desktop screen captures, progressive kinetic cards, or `Google Flow Omni 1.2 Flash` dark-emerald B-roll (`CMO_Procedure_MYPASAKON_Cut` Rule 5, `Q-20261125-1324-fa7a`):
- **1:1 Full-Screen Establish -> `cubic_in_out` True-Center Smart-Zoom:** strip macOS menu bar, Dock, and sidebar PII (`extract_clean_desktop_window`), show the full `1:1` desktop window first (`0.00–1.15s`), then smoothly zoom (`3u² - 2u³`) so the exact mouse click / spoken UI element lands **dead-center at `x = 540px`** with `20–30%` surrounding UI context (`0%` sliced Thai/English words) + peripheral spotlight dim (`76%` outer, `100%` target) + source-locked Neon-Emerald focus frame.
- **White-background `TradingView` -> Dark Neon conversion:** apply `255 - bgr` + HSV `+90` hue rotation so white charts turn `#000000` obsidian while preserving green/red candles and blue trend arrows.
Gate: pre-flight crosshair (`x = 540`) preview sheet verified across all screen beats with zero OS/PII leaks.

### Step 10 · Viral x BL V7.8 cut [node: compose_cut]
Do: cut the full `30fps` `1080×1920` episode strictly following `CMO_Procedure_MYPASAKON_Cut` using the upgraded `omni_lip1..3_1080p.mp4` clips:
- **2-Layer RVM Parallax Viral Hook (`0.0–4.8s`):** `RVM mobilenetv3` cutout CEO (in winter knit sweater) + 3D shadow over full-bleed dark-emerald chart + Giant 2-Line `Kanit 800` Hook Headline & floating market chips.
- **Full-Screen `1080p` Talking-Head + Headroom Headlines (`y = 255–485px`):** shift down `+148px` so bold headlines & pop cards sit above the `RICH` beanie (never boxed into 50/50 splits and never over the mic hand at `y > 1400px`).
- **Smooth `sine.out` RVM Avatar Shrink (`BL §6d`) & Smart-Zoom Screen + Centered `304×304` Circular PiP (`Q-20261126-1038-beb0`):** RVM cutout CEO shrinking to chest-up bottom-left (`cx=310px`) in front of live news, and **`304×304px` Circular Neon-Emerald PiP** at `(856, 266)` fed by a `1340×1340px` mirror-padded square centered on `(head_cx=505, head_cy=815)` so `100%` of the face, `RICH` beanie, and sweater shoulders sit dead-center with **zero ring overlap**.
- **BL V7.8 GSAP Motion, SFX, BGM & CTA:** Diagonal Emerald Slash Wipes (`fireSlashWipe`), 2-part Split Keyword Chips, bespoke vector-icon GSAP infographics (`2–5 words`, zero emoji), real moving chart cutaways (`tools/footage_catalog.py`), ending `CMO_Procedure_TikTok_CTAMotion` (`ctaSave` & `ctaFollow`), 17 curated SFX, and `BL07` `-24.0 dB` ducked BGM (`tools/bgm_bed.py`) at **`-14.0 LUFS`**.
Gate: exact frame count `round(trimmed_audio_dur * 30)` with zero frame gaps.

### Step 11 · Cut and visual QC [node: qc_check]
Do: run `tools/mypasakon_audio_trim.py verify-cut --video <final.mp4> --audio <trimmed.mp3> --sheet <qc_8frame_sheet.jpg>` AND inspect a `4×2` **iPhone TikTok Viewer UI Simulation Sheet** (`scale = 933/1920`, `54.34px` side crop, right-rail icons blended on top) via `read_file` to verify zero face/beanie overlap, zero ring collision in PiP, true-center Smart-Zoom targets, zero TikTok UI collision, and bullseye CTA ring fit.
Gate: `verify-cut` returns `"ok": true` (`1080×1920`, `30.0 fps`, `-16.5..-11.5 LUFS`) and iPhone UI simulation passes 100%.

### Step 12 · Gate 2 video approval [node: gate2_video]
Do: send `MYPASAKON_<EP>_NeonFull_1080p.mp4` to `/run` (`tools/ask_run.py ask --project "MYPASAKON" --lane "cmo" --media <final.mp4> ...`), print Card ID + URL, and end turn. Note: when reading multi-media card picks back, always verify via `ask_run.py wait <Q-id> --max-wait 1` (`picked:` line) rather than trusting the mailbox wake summary's `choice` fallback.
Gate: CEO taps `ใช้ได้` on `/run`.

### Step 13 · Queue and Drive archive [node: publish]
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
- 2026-11-25 [MISSING] §Step 9 & §Step 11 OS leak scrub — on the initial `IUX24` full-loop Demo, raw `320.38s` voice + `5.01s` pickup trimmed `-29.4%` (`95.76s` dead air & 18 retakes removed) -> `229.63s` (`3:50`) master passed Gate 1 on first listen, and 8-frame visual QC caught a brief macOS Launchpad transition at `IUX24.mov` `t=157.6s` in `s24_warning_m2` (re-pointed to `t=138.5s` and re-rendered `seg_23` in 4s) · evidence: Q-20261125-1010-88f9, Q-20261125-1010-e3b0, Q-20261125-1018-c6f1, Q-20261125-1059-e579 · status: promoted
- 2026-11-26 [MISSING] §Step 8 `omni12_restyle` + `sync-omni` — CEO approved upgrading all `15s` Lipsync clips through Google Flow `Omni 1.2 Flash` (`องค์ประกอบ` `<VIDEO_REF_0>`) into a smart-casual Western winter charcoal-black ribbed merino sweater + sharp `1080×1920` architectural wood-slat studio (`RUN-20261126-1015-8e87` `12 cr` for `4s` `1080p`, `Q-20261126-1038-beb0`: `"ผ่านเลย! บรรจุเข้า MYPASAKON Workflow ใช้กับคลิปจริงทุกตอน"`); measured a `+292.7ms` silent lead-in (`0.407` raw 16kHz waveform correlation) added by Flow, handled automatically by `tools/mypasakon_audio_trim.py sync-omni` · evidence: Q-20261125-1618-f177, RUN-20261126-1015-8e87, Q-20261126-1038-beb0 · status: promoted
