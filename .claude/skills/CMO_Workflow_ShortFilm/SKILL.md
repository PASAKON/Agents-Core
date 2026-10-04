---
name: CMO_Workflow_ShortFilm
kind: workflow
owner: CMO
aka: [CTO_Film_Workflow]
description: >-
  WORKFLOW — The ordered, day-by-day workflow for making an ILAG short film end to end with Seedance 2.5 (Higgsfield),
  MiniMax H3 (our ComfyRunpod studio) and Wan 3.0 (TopView): brief and rules → market and idea → story →
  characters and plates → shot plan → previz (Blender, H3) → prompts → generation waves → QC → edit and
  finish (grade, subtitles, end credits) → posters and the YouTube A/B test → challenge rules check →
  publish → Drive filing and cleanup. Each step names its gate, the skill that owns its rules and the tool
  that does it; the rules themselves live in those skills, not here. Trigger on /CMO_Workflow_ShortFilm and
  whenever a new short film, trailer or challenge entry starts or an agent joins one mid-way: "ทำหนังสั้น",
  "เริ่มโปรเจคหนังใหม่", "Workflow ทำ Short Movie", "วางแผนทำหนัง", "ส่งประกวด", "short film workflow",
  "ตอนนี้หนังอยู่ขั้นไหน". Do NOT use it for engine details (read the engine skill) or for BLACK LIQUIDITY
  talking-head episodes (CMO_Procedure_BlackLiquidity_Cut).
created_by: agent
author: {role: cto, date: "2026-09-27"}
audience: [cmo, cto, cxo, script_writer, prompt_engineer, browser_operator, video_editor]
---

# The short-film workflow

Written from «Sorry, Sir» (Seedance 2.5, Aug–Sep 2026), «Do Not Disturb» (Seedance), «จุดจบของเจ้าหนี้นอกระบบ»
(Google Flow) and THE SHADOW BELOW (MiniMax H3 previz → Wan 3.0 finals, steps 0–13 in five days,
23–27 Sep 2026). This file holds the ORDER, the GATE that ends each step, and the POINTER to the skill
or tool that owns it. It repeats no rule from those skills (CEO 2026-09-25: film skills are engine-scoped
and say each thing once). Read the owner skill before doing a step.

## How an agent joins a film

1. Open the film's `STATUS.md` (template at the end). No file → the film is at Step 0; create it.
2. Find the current step and its gate below. A gate that has not passed means that step is the work.
3. Read the owner skill of that step, do the step, then update `STATUS.md` (step, gate, spend, what waits
   on the CEO) and file the outputs (Step 13 runs after every step, not only at the end).
4. Report to the CEO in the chat he is in; anything that needs him goes as ONE list with a recommended
   answer each.

## Rules that hold on every step

1. **HARD — money (org rule: `ALL_Rules_Approvals`).** Every paid generation, RunPod pod hour or paid image: the CEO sees the exact credits
   and $ first, one capped round at a time; a second round needs a second OK (CEO rules).
   Dry runs and prompt rendering are free and need no OK.
   **Why hard:** money; a fired generation cannot be taken back, and a pod bills by the hour.
2. **HARD — a competition's platform rule.** Final footage comes only from the engine the rules require:
   Higgsfield festival = everything generated on Higgsfield, no edited uploads (`CMO_Knowledge_Seedance2.5_Higgsfield`
   Rule 00); TopView challenge = the primary video is Wan 3.0 on TopView, in our TopView project
   (`CMO_Knowledge_Wan3.0_TopView` rule 2). Previz from other tools is fine as previz, never as footage.
   **Why hard:** scope; a breach disqualifies the entry and the organizers verify the process.
3. The director decides story, characters, every line, the ending and the order (`CMO_Knowledge_Film_Production`
   §10). Write his words down verbatim in the film's notes the moment he says them.
4. Look before you measure: review from one numbered contact sheet, then confirm with numbers
   (`CMO_Knowledge_Film_Production` §8); the CEO answers by number, full-size files wait on Drive.
5. Browser work that repeats more than 3 times runs through a zero-model runner or a `browser_operator`,
   never in a C-level's own tab (IRON-RULES §42, §53).
6. Commit every task id and asset id before downloading; commit prompts, scripts and ledgers to the repo:
   the scratchpad is not storage.

## Which engine does what

| Tool | Where it runs | Cost | Use it for | Owner |
|---|---|---|---|---|
| Blender | winbox, exec bridge | free | camera blocking and hard camera moves as a depth previz; the MP4 becomes a `@Video` reference | `CMO_Procedure_Blender_Previz` |
| MiniMax H3 | our ComfyRunpod studio (Mac) on a RunPod H100, reached at `100.64.2.37:4100` | pod hours ($3.29/h); the CEO opens the pod | a whole-cut animatic at 360p to lock order, timing and staging cheaply; never contest footage | `CMO_Knowledge_MiniMax_H3` |
| Seedance 2.5 | Higgsfield | Unlimited lane for video; images cost credits | finals for Higgsfield festivals; takes a previz as `@Video 1` | `CMO_Knowledge_Seedance2.5_Higgsfield` |
| Wan 3.0 | TopView board | per second + 4K upscale charged at start | finals for the TopView challenge; multi-shot 4–6 s per shot, up to 30 s | `CMO_Knowledge_Wan3.0_TopView` |
| GPT Image | ChatGPT web on winbox (`tools/chatgpt_images.py`) or fal `gpt-image-2` | plan / paid | character sheets, plates, cover backgrounds, title logos (not for Higgsfield festival entries) | `CMO_Procedure_CharacterSheet` |
| Google Flow Music | flowmusic.app (`tools/flow_music.py`) | plan | the score, with a rights record | `docs/promo/topview-trailer/MUSIC-RIGHTS.md` |
| Google Flow (Veo / Omni) | flow.google.com | credits | optional engine for Thai dramas | `CMO_Knowledge_Flow_Omni1.1` + `_Continuity` + `_FilmQC` |

## Day plan

Standard: 7 working days. THE SHADOW BELOW ran the compressed plan in 5. A step never starts before the
gate of the step it depends on; within a day, steps without a dependency run in parallel.

| Day | Steps | Gate at the end of the day | CEO time |
|---|---|---|---|
| D0 (2 h) | 0 Brief, rules, budget | engine, budget ceiling and deadline confirmed | 10 min |
| D1 | 1 Market and idea · 2 Story | one logline picked; script approved | 30 min |
| D2 | 3 Characters and plates | every plate approved by number | 20 min |
| D3 | 4 Shot plan · 5 Previz | continuity questions answered; animatic approved | 30 min |
| D4 | 6 Prompts · 7 Wave 1 | cost table approved; every clip collected and filed | 10 min |
| D5 | 8 QC · 7 Wave 2 (retakes) | keepers marked; shot list locked | 30 min |
| D6 | 9 Edit and finish | master approved on a full watch | the CEO's edit day |
| D7 | 10 Posters · 11 Rules check · 12 Publish · 13 File and clean | public link plays; form reads Submitted | 20 min |

Compressed (5 days): D1 = steps 0–2 · D2 = 3–5 · D3 = 6–7 · D4 = 8–9 · D5 = 10–13. Back-plan from the
deadline in Thai time and keep 12 hours of slack before it: servers time out, renders take 25–60 minutes,
and the CEO's own edit needs a day.

## The steps

### Step 0 · Brief, rules and budget
- **Do:** read the challenge rules at the source (page, Terms, FAQ) into `docs/promo/<CHALLENGE>-RULES.md`:
  dates converted to Thai time, which tools are eligible, watermark, hashtags and account tags, where the
  post must be public and for how long, form fields, file limits, judging criteria. Where sources disagree,
  write both and plan on the earlier date. Example: `docs/promo/TOPVIEW-WAN3-RULES.md`.
- Pick the engine from the rules; propose the budget ceiling (credits and $) and the deadline.
- Ask the CEO for the Drive project folder (`CXO_Rules_GDrive_Filing`, YT: ILAG layout: `logs.txt`, `All Scene/`,
  `Element/`, `Soundtrack/`, `Previz/`, `Poster/`, `Meta (<platform>)/`, `Final Draft/`).
- **Output:** RULES.md, STATUS.md, Drive folder. **Gate:** the CEO confirms engine, budget and deadline.

### Step 1 · Market and idea
- **Do:** check the demand before the competition (few rivals usually means few viewers, not an opening): what is
  watched in this genre on the target platform (top videos, views against age), what our own past films
  earned (Studio analytics for «Sorry, Sir», «Do Not Disturb»), and for a challenge the judging criteria
  and the entries already posted. Study reference trailers with `video-ad-analysis`; frame ideas with
  `content-idea-generator` and `marketing-principles`. Copy a genre's identity, not just its layout
  (Thai lakorn titles are custom logos; a stock font reads as a news thumbnail).
- Write the research to `docs/research/<date>-<slug>.md` with sources and a refresh date (format:
  `docs/research/2026-09-26-youtube-shorts-income-model.md`). Label every estimate as an estimate.
- **Output:** 3–5 loglines, each with one line on why it can win (`docs/promo/topview-trailer/STORY-OPTIONS.md`
  is the shape). **Gate:** the CEO picks one.

### Step 2 · Story
- **Do:** pass the structure gate before any shot exists: `CMO_Gate_Story_SceneEngine` (goal, obstacle, tactic,
  reversal, value shift) — IRON-RULES §51; Thai moral dramas use `CMO_Standard_Story_ThaiMoralDrama`.
- Write the story bible and the script with every spoken line locked; plan length as shots × seconds and
  turn it into a first credit estimate. Examples: `docs/promo/topview-trailer/BIBLE.md`, `SCRIPT.md`.
- **Know what the viewer must understand before anything is shot (CEO 2026-10-04).** Write it in one line for the
  whole film and one line per scene: what the audience learns there. A scene that tells the viewer nothing the story
  needs is cut, however good it looks.
- **Output:** BIBLE.md, SCRIPT.md, beat list. **Gate:** the CEO approves the script.

### Step 3 · Characters, locations and props (the @Element registry)
- **Do:** `CAST.md` first (`CMO_Knowledge_Film_Production` §2), one row per character with colours named, then the
  plates (§3): one character per plate, locations without people, a separate element for every state the
  story needs (lit / dead lamp). Names follow the @TAG the prompts will use (`@ANA`).
- Make sheets with `CMO_Procedure_CharacterSheet` or `tools/chatgpt_images.py`; for a Higgsfield festival,
  generate them on Higgsfield. A $0 mockup goes to the CEO before any paid image; poverty, age and wear
  are written in concrete materials (zinc, patches, clutter), because image models prettify them.
- H3 needs one photograph per reference: crop single panels out of any sheet (`CMO_Knowledge_MiniMax_H3` rule 4).
- **Output:** plates filed to `Element/Character|Location|Prop` on Drive the moment they exist.
  **Gate:** the CEO approves every plate by its number on one contact sheet.

### Step 4 · Shot plan and continuity
- **Do:** from the beats, a shot list with the camera mode per shot (locked, long take, multi-cut,
  montage), length, who and where. Then the continuity table in cut order (`CMO_Knowledge_Film_Production` §9; Flow
  films: `CMO_Gate_Flow_Omni1.1_Continuity`; tools: `tools/build_shotsheet.py`, `tools/continuity_sheet.py`,
  `tools/shotsheet_lint.py`). Say the tolerance out loud (§5).
  Shot size, angle, move, lens, light and colour per shot: `CMO_Knowledge_Cinematography_ShortMovie`
  (Short Movie only; ละครสั้น / lakorn never borrows from it, CEO 2026-10-03).
- **Every cut from shot A to shot B must be explainable (CEO 2026-10-04).** His words: *"การทำหนัง 1 เรื่องเราต้อง
  รู้ก่อนว่าจะสื่ออะไรให้คนดูได้รู้ และ A -> B ได้ยังไง สมเหตุสมผลหรือป่าว ถ้าอธิบายไม่ได้ แปลว่า เราทำมันได้ไม่ดี"*.
  His example, THE LAST BELL: the girl sits with her grandmother, and the next shot has her already in a boat. Who
  called her, did she get up, did she climb aboard? Write a cut-logic table in cut order, one row per pair: the IN
  and OUT of each shot (place, who, doing what, light), then the one line that takes the viewer from A to B. Accepted
  links: the same action continues; B is caused by A; the move between places is shown (gets up, leaves, boards,
  arrives); a look or a sound in A motivates B; time passing is marked (light change, a dissolve). A row without
  a link is a missing **bridge shot**: add it to the shot list (a call from outside, getting up, boarding, arriving),
  4–7 s of cut, generated like any other shot. Run the table on the shot list before prompts and again on the real
  takes' first and last frames before the edit, because a take can start somewhere the board did not say.
- **Output:** STORYBOARD.md + continuity table. **Gate:** every open question asked at once, each with a
  recommended answer; the CEO's answers written into the notes before any prompt changes.

### Step 5 · Previz
- **Do (free):** Blender camera previz for the shots whose camera move is hard to get from words
  (`CMO_Procedure_Blender_Previz`: rigs, EEVEE render to MP4, handoff as `@Video` reference).
- **Do (pod hours, CEO opens the pod):** the H3 animatic of the whole cut at 360p (`CMO_Knowledge_MiniMax_H3`):
  queue every shot at once (an empty queue stops the pod), assemble with
  `docs/prompts/ilag-topview/assemble_cut.py`, and send the cut to the CEO.
- **Video-to-video:** Seedance takes the previz as `@Video 1` for camera and motion; on Wan 3.0 a video
  reference is allowed by TopView but its effect is not yet measured — test it on one shot first.
- **Gate:** the CEO approves the animatic (order, timing, camera). Finals are paid only after this.

### Step 6 · Prompts
- **Do:** write every shot in the house format (`CMO_Standard_Film_PromptFormat`): notes / paste zones, references
  as `@TAG — NAME: what to take; what to ignore.`, timed beats, sound, the film's look line, aimed
  negatives. Generate the files from data (`docs/prompts/ilag-topview/build.py`; Wan 3.0:
  `wan3_prompt.py`), never hand-edit them. An AI without our skills can use
  `docs/prompts/MASTER-PROMPT-cinematic.md`.
- Engine specifics come from the engine skill: the Wan 3.0 Direction box limit and 4–6 s shots, the
  Seedance duration slider and `@Video`, the H3 audio marker.
- Dry run (free): render every prompt, run the 60-second check (`CMO_Standard_Film_PromptFormat` §4) and
  `tools/shotsheet_lint.py`, count references against mentions.
- **Gate (HARD money):** a cost table per shot and in total, credits and $ → the CEO's OK.

### Step 7 · Generation waves
- **Do:** fire through the runner, never by hand: Wan 3.0 `tools/topview_wan3.py` (collect by task id with
  `tools/topview_collect_tasks.py`, read the balance with `tools/topview_fresh_balance.py`), Seedance
  `scripts/higgsfield/gen_loop.py`, H3 `docs/prompts/ilag-topview/h3_fire.py`, Flow `tools/flow_shoot.py`.
- Wave 1 fires every shot once. Commit the ids, download, file to `All Scene/S<n>/` with the names in
  `CXO_Rules_GDrive_Filing`, log each file.
- A refire, even of a refunded server failure, is a new spend and needs a new OK.
- **Gate:** every clip collected, ids committed, Drive logged.

### Step 8 · QC: continuity and drift
- **Do:** one numbered contact sheet (start / middle / end frame per clip); judge by eye, then give the CEO
  one table per number: what failed against the brief (`CMO_Knowledge_Film_Production` §8; Flow: `CMO_Gate_Flow_Omni1.1_FilmQC`; champa Seedance short movie: `CMO_Gate_Champa_Seedance2.0_ShortMovieQC`, whose 14-item eye checklist is the gate).
- Mechanical checks find what frames cannot: `tools/film_transcript.py` (the line was said, no stage
  direction spoken), `tools/burned_text_scan.py` (text or subtitles burned into the picture). Look for the
  known drifts listed in the engine skill's field notes (wrong species, missing mount, lamp state).
- Retakes change one variable at a time; when a retake passes, write the A/B entry (§11); a changed
  reference means every shot bound to it is re-shot (§4).
- **Gate:** the CEO marks the keepers; wave 2 only with a new cost OK; then the shot list is locked.

### Step 9 · Edit and finish
- **First 3 seconds (CEO 2026-10-01, every film and channel):** before export play 0–3 s alone and trim the lead-in until
  frame 0 is already inside the hook (a face, movement, the question said or shown; no black, no title or logo card, no
  back of the head). The rule and its tests are `CMO_Standard_Story_FamilyDogSeries` §2 item 10.
- **Edit:** the CEO cuts in CapCut. Send him an edit kit (keepers, music, credits roll, subtitle file) over
  Drive or Taildrop, and remind him to delete the kit on the Mac afterwards.
- **The «บ้านนี้มีมีมี่» cut (CEO 2026-10-01: v2 approved, "save เป็น workflow"):** one manifest per episode, built by
  `tools/film_cut_assemble.py <manifest> --var PROD=… --var CARDS=… --var OUT=…` (ffmpeg only, 0 tokens; the EP1 manifest is
  `docs/scripts/khaoniao-ep1-cut-manifest.json` and re-renders the approved cut bit-for-bit, video md5 equal). The recipe:
  1. **Trim the first shot's lead-in** so frame 0 is inside the hook: dump the first 2 s as 50 ms RMS, start at the first
     sound burst (EP1: 0.8 s), then check a face is on screen by ~0.3 s.
  2. **Time label** («เมื่อเช้า») = transparent PNG from `docs/reports/khaoniao-family-style/cover/card.html?mode=morning`,
     laid over the first 2.4 s of the flashback shot, fade 0.3 s in and out, placed at y=60 (lower covers the heads).
  3. **Title card** (`mode=title`, 2.6 s) right after a shot that leaves a question open, placed so **1:00 falls inside it**
     (the manifest's `mid_roll_s` check prints what lands there); never before 3 s.
  4. **End card** (`mode=end`, 3.5 s): the page mark + only a promise we keep («ติดตามตอนใหม่ทุกวัน 19:30»).
  5. Then the music step below, a 540x960 crf-28 preview (3 min ≈ 14 MiB; the chat send limit is 30 MiB) and the full file
     to `Assets/Agents/Core/khaoniao-family/ep1/` + the winbox cut folder.
  Cards render on winbox with `render_cards.py` (Chrome headless; real Itim from Google Fonts; `--default-background-color=00000000`
  gives the transparent label). Traps: a space between inline-block Thai spans collapses (use `&nbsp;`); the page-mark PNG is
  mostly transparent padding (size it at 2400 px or the name prints tiny); look at the cards once on one sheet over a real frame.
- **Music:** Flow Music tracks with the rights record (`MUSIC-RIGHTS.md`, `MUSIC-LEDGER.json`).
  **The «บ้านนี้มีมีมี่» recipe (CEO 2026-10-01, "ผ่านแล้ว … ต้องใส่เพลงด้วยแบบนี้เลย"): every episode of that channel
  carries a quiet solo-piano bed made exactly like M1.** One track per episode:
  1. *Make it* (zero-model, 5 credits from the separate Flow Music pool of 30,000/month, ~50 s):
     `tools/flow_music.py <prompts.json> --out <dir> --max-credits-per-track 10 --length 3:00 --no-title --cdp-url http://127.0.0.1:9224`
     on winbox (9224 is the Chrome signed in to Flow Music; the default 9226 is not). `--dry-run` first, it is free.
     Prompt = the M1 text in `docs/scripts/khaoniao-ep1-music-prompts.json` (tender lullaby piano, ~66 BPM, pp–mp,
     solo piano only: no drums, strings, vocals, pads or effects), adapted by one scene line per episode. Instrumental
     ON, Lyria 3.5. Length is clamped to 1:00–3:00, so order 3:00 for a 3-minute episode (came back 2:55).
  2. *Mix it* with `tools/film_music_mix.sh <cut> <music> <out>`: -4 dB, starts at 3 s, fade-in 3 s, fade-out 5 s, ducked
     by the dialogue (sidechain, ratio 2.5) = music ~16 dB under speech and a gentle swell in the pauses. The CEO
     approved this level; do not make it louder. Never `alimiter` with its default `level`.
  3. *Keep the record:* the runner's `ledger.json` (clip id, md5) beside the prompts, one `credit_ledger.py` row
     (engine `flow-music`), the master WAV on winbox, an mp3 in `Assets/Agents/Core/khaoniao-family/music/`.
  M1 itself (`M1-tender-lullaby.mp3`, 2:55) is the approved house sound: a new episode may reuse it, or make a fresh
  track with the same recipe when the story's mood differs.
- **Grade:** `docs/prompts/ilag-topview/looks.py` builds custom 3D LUTs and a comparison sheet; the CEO
  picks; applied with ffmpeg `lut3d` (trilinear).
- **Subtitles:** `docs/prompts/ilag-topview/finish.py --subs-only` (faster-whisper word timings matched to
  the script) → hand-check every cue against the audio → burn in the «Sorry, Sir» style (Arial 78 at 4K,
  white, no outline, centred, MarginV 174) → a 5-second 720p sample to the CEO before the full render.
- **End credits:** `docs/prompts/ilag-topview/credits.py` (the «Sorry, Sir» roll: font, order, 7 px per
  frame at 4K). **Before appending anything, look at the last minute of the CEO's cut**: THE SHADOW BELOW's
  cut already held the credits and the film shipped them twice (`CMO_Knowledge_Film_Production` field note
  2026-09-27).
- **Watermark** when the rules demand it (TopView: official mark top-right over the whole film).
- **Render:** winbox `tools/ilag_publish/render.cmd` (ffmpeg): a master at CRF 16 and a contest copy under
  the form's size limit; check `ffprobe nb_frames` equals the cut's frame count.
- **Gate:** the CEO approves the master on a full watch.

### Step 10 · Posters and the YouTube A/B test
- **Do:** the CEO picks the key frame; ChatGPT makes the background and the title logo;
  `docs/prompts/ilag-topview/cover.py`
  composes the rest (title logo, the challenge watermark, "AI SHORT FILM", the 4K badge). Make four
  designs; export 1920×1080 PNG (forms) and 1280×720 JPG (YouTube).
- YouTube's Test & Compare takes three covers and slot 1 is the current thumbnail: upload A as the
  thumbnail, then add only two others (`tools/ilag_publish/yt_ab_set.py`, README). Keep badges and marks
  out of the bottom-right corner, where YouTube prints the duration.
- **Gate:** the CEO picks cover A and the two test covers.

### Step 11 · Rules check (challenges)
- **Do:** walk `RULES.md` line by line against the finished file, the post and the form: duration,
  resolution, watermark, eligible tools, hashtags, account tags, the post's platform and visibility, form
  fields, file size, the deadline in Thai time, licence records (ChatGPT chat links, music rights).
- **Output:** a checklist with pass / fail and the evidence for each. **Gate:** nothing fails.

### Step 12 · Publish
- **Do:** the CTO writes the post text and hashtags (`docs/promo/topview-trailer/POST.md` is the shape).
- YouTube (ILAG Studio): `tools/yt_studio_upload.py` → `tools/ilag_publish/yt_publish_draft.py` (the first Done leaves a
  draft) → `yt_set_lang.py` (language and category) → `yt_ab_set.py` → confirm the watch page plays for an
  anonymous viewer. Upload the `.srt` caption track by hand (`yt_subs_upload.py` does not work yet).
- Challenge form: `tools/ilag_publish/tv_submit.py` and `tv_finish.py`; replace a submitted video with
  `tv_edit_video.py`; fix a published video's length with `yt_trim_end.py` (keeps URL, views and the test).
- **Gate:** the public link plays anonymously, the form reads Submitted, the CEO has the report.

### Step 13 · File and clean (after every step, and once at the end)
- **After each step:** file the outputs to the Drive project (`CXO_Rules_GDrive_Filing`: 9-field `logs.txt`, scene
  naming, append-only, md5 checked by file id; big files with `ilag_rest.upload_stream`), and commit
  prompts, scripts, ledgers and ids to the repo.
- **At the end:** list every temp folder (Contabo `/tmp/<film>-*`, winbox `C:\mooniex\<film>`), confirm each
  file has a Drive copy with a matching md5, ask the CEO, then delete (`ALL_Rules_DiskHygiene`). Remind him to delete
  the Mac edit kit. Keep the post public and the platform project intact until the results.
- Fold the session's Skill learning lines into the owner skills.

## STATUS.md (one per film, beside its prompts)

```
# <FILM> — status
Deadline: <date, Thai time> · Engine: <engine> · Budget: <credits / $>, approved by the CEO on <date>
Step: <n · name> · Gate: <open | passed on date> · Waiting on the CEO: <list, each with a recommended answer>
Spend so far: <credits / $> · Balance: <read fresh on date>
Drive: <project folder id> · Prompts: docs/prompts/<film>/ · Rules: docs/promo/<CHALLENGE>-RULES.md
Last agent: <session id> · Next action: <one line>
```

## Field notes

- 2026-10-03 [MISSING] Step 4 output — plates have `Element/Character|Location|Prop`, but key art (a poster-style frame that is not an element) has no folder in the YT: ILAG layout. THE LAST BELL's two key frames went to the film root · evidence: docs/prompts/last-bell/NOTES.md (key_bell_naga, key_storm_city), session 671f688f · status: pending
- 2026-10-03 [MISSING] engine limits before writing prompts — champa Seedance 2.0 takes at most 9 reference images and a 2,000-character prompt (2,001 is refused with "ข้อมูลไม่ถูกต้อง"; the textarea itself keeps 12,000+). A storyboard written before measuring would have overflowed: the first build of THE LAST BELL had shots up to 2,846 characters. Measure the engine's slot and length caps with free jobs before the storyboard step, and have the build script assert them · evidence: docs/prompts/last-bell/REFS.md, build_shots.py LIMIT, lb_out/queue.jsonl reject rows lb-t3-len2001…len8000 · status: pending
- 2026-10-03 [MISSING] before a render wave, read the engine's quality default and per-quality price into REFS — on champa Seedance 2.0 the menu defaults to 720p (480p/720p free on Unlimited, 1080p = 106 credits per 15 s clip), and card meta reads `Standard` whatever is picked; the CTO first told the CEO the clips were 480p, a claim nobody had measured · evidence: last-bell NOTES §Rough cut v1, 47 clips fired before the check · status: pending
- 2026-10-04 [MISSING] Step 8 — the step named only the Flow lakorn gate; a champa Seedance short movie fails in the picture (weather from a reference, creature geometry, named states) where that gate's cheap stage is blind: 0 defects at stage 1 vs 15 of 41 shots failing by eye on THE LAST BELL. Pointer added to the new gate CMO_Gate_Champa_Seedance2.0_ShortMovieQC · evidence: session cto-671f688f, commit e5e898f3 · status: promoted
- 2026-10-04 [COSTLY] Step 2 — THE LAST BELL went to the queue (40 shots, 2026-10-03) on a bible still marked "plot draft v1, not yet a locked script" and without `CMO_Gate_Story_SceneEngine`; the audit found scenes A, C and D failing (inert twist: the Naga only hurt the villain, the storm came before the bell, the chain broke after the Naga was loose). Round 2 needed 9 new shots plus re-cuts. Prevented by: the builder (`build_shots.py`) refusing to emit prompts while BIBLE.md says draft or no per-scene engine table exists · evidence: docs/prompts/last-bell/STORY-AUDIT-2026-10-04.md, STORY-V2.md (origin 2d339689) · status: pending
