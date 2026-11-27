---
owner: CMO
aka: [mooniex-video-editor]
audience: [video_editor, worker]
created_by: human
origin: mooniex-org
name: VIDEO_EDITOR_Protocol_Playbook
kind: protocol
description: >-
  PROTOCOL — MoonieX org process layer for the `video_editor` role (owned by CMO,
  created 2026-08-03). Use this whenever a video_editor task arrives — cutting
  a talking-head clip into a finished vertical reel — to know: which brand
  rules apply, where to find/source B-roll assets, what the deliverable
  folder/format contract is, and which parts of the work are CTO's
  responsibility (the tool) vs CMO's (the direction) vs yours (the execution).
  The actual editing mechanics live in the `CMO_Procedure_ReelEditor_TH` skill — read that
  one for the how; this one is the org-specific what/why/where. Trigger on
  any task titled/described as cutting, editing, or producing a MoonieX reel,
  or when role=video_editor.
---

# MoonieX Video Editor — process layer

You are the `video_editor` role. This role sits under **CMO** (content
production execution) — CMO directs *what* to make (topic, brand voice,
which script), you execute the cut, and **CTO maintains the underlying tool**
(`CMO_Procedure_ReelEditor_TH` — bugs in the pipeline itself are a CTO concern, not
something to route around ad-hoc). Registered 2026-08-03 in
`policies/agents.yaml` / `config/projects.yaml`.

## Step 0: read `CMO_Procedure_ReelEditor_TH` first

That skill has the actual mechanics: transcription, `timeline.py` schema,
the cut-rhythm rule (avatar/footage/animation every 1.5-3.5s), the two-layer
scene→subs render, and `references/cutaway-authoring.md` for the
`CUTAWAYS`/`COUNTERS`/`SFX_EVENTS` syntax with a worked example. Don't
duplicate that work — this doc only adds what's specific to MoonieX.

## Brand rules that apply to every MoonieX reel

- **No crude language** in on-screen text or a caption doc (IRON-RULES §37).
  Casual and direct is fine; มึง/กู and profanity are not.
  **Exception: BLACK LIQUIDITY.** Its มึง/กู voice is a CEO-confirmed brand
  carve-out in IRON-RULES §37 (2026-08-03/04). On a BL episode the captions
  follow the recorded audio word for word, including มึง/กู. Approved EP53 and
  EP54 carry มึง on screen, and on EP55 the CEO's own hook line is
  "เดี๋ยววันนี้กูจะมาแฉให้ฟัง". Profanity is still out on BL too.
  - [SUPERSEDED 2026-09-23] "never มึง/กู … even if the source clip's own script
    uses it (the BLACK LIQUIDITY content series' written briefs sometimes do —
    clean it up on-screen)". Beaten by the §37 carve-out, a CEO ruling. Evidence:
    task-52c669bb stripped them from EP55's captions, including the CEO's hook,
    so the screen disagreed with the audio.
- **No em dash** in any caption, hook, CTA, or cover text (IRON-RULES §39) —
  reads as an AI tell.
- **Style = `clean`** by default for trading/finance content — it reads as
  premium/editorial, matching MoonieX's brand positioning better than the
  loud `bold` TikTok style. Only switch styles if CMO explicitly asks.
- **Don't invent structure the source audio doesn't support.** If a script
  promises "3 traps" but the clip cuts off before the 3rd is explained, or a
  clip ends mid-sentence, don't fabricate a punchline/checklist-completion
  that wasn't said. Flag the gap instead (see "Known source-truncation
  issue" below).
- **Only tag/count what's actually spoken** — a `COUNTERS` tag like "1/3"
  when the clip only covers 2 of 3 items is a false claim; use plain labels
  instead ("กับดัก: Revenge Trade") when a full count can't be verified.

## Asset sourcing order (cheapest/safest first)

1. **MoonieX Cross-Channel Timecode Footage Catalog (`tools/footage_catalog.py` + `prototypes/bl-broll-catalog/FOOTAGE_INDEX.jsonl`, CEO Q-20261117-0922-99fe)** —
   Indexes all **758 videos (796 timecode segments `start_s..end_s`)** across `ALL DRAFT/ASSETS` (`1LJreOD8H3jUNzypxTnPwvq-pS7jkQNRd`), `00_PRODUCT_LIBRARY`, and `วิธีการใช้งาน APPs MT5` for **`MYPASAKON`**, **`BLACK LIQUIDITY`**, and **`TRADE TO THE MOON`** (Phase 1: 57 real MT5/Exness Desktop/Exness Mobile/IQ Option screen recordings + 245 AI/Product clips; Phase 2: 148 real Lifestyle/Porsche/Starbucks/Cafe/MyRoom clips tagged with `person_shown: HANDS_ONLY|NONE|CEO_PASAKON`; Phase 3: 308 Broker Event/Gala clips tagged with `broker_lock`).
   - **Never read the entire catalog file into context.** Query top matching segments via CLI:
     ```bash
     python3 tools/footage_catalog.py search --channel <MYPASAKON|BL|TTTM> --mode <CHART_VIEWPORT|FOOTAGE_FOCUS|CALM_TEXT_BG> --q "<คำพูดหรือภาพที่ต้องการ>" --limit 5
     python3 tools/footage_catalog.py match-script --channel <MYPASAKON|BL|TTTM> --clauses clauses.json
     python3 tools/footage_catalog.py fetch --drive-id <id> --start <s0> --end <s1> --out cut.mp4 [--frame-viewport]
     python3 tools/footage_catalog.py sync   # incremental check for newly uploaded Drive videos by drive_id + md5
     ```
2. `~/.claude/skills/CMO_Procedure_ReelEditor_TH/assets/mooniex-broll/` — already-vetted,
   no-baked-text trader mood photos + 2 motion b-roll clips (candle/smoke,
   dark cinematic) + their pre-extracted 9:16 frame sequences.
3. Google Drive, folder tree **"BLACK LIQUIDITY"** (owner
   pass.gob1@gmail.com) — the CEO's own trading-psychology content series,
   ~50 numbered episode folders, each with a `Brief` doc (full script +
   editing template + suggested Pexels B-roll URLs) and usually an `Audio` +
   `Final Draft` subfolder. Several numbered episodes can share the exact
   same brief/topic (duplicates from an earlier automation run) — if you
   need a SPECIFIC episode's assets and more than one folder matches the
   topic, ask CMO/CEO which one rather than guessing.
   - Files >10MB fail through the Drive MCP's `download_file_content` (hard
     10MB relay limit) — use `python3 tools/footage_catalog.py fetch` (streams only `[start_s, end_s]` via HTTP Range) or the direct link pattern:
     `curl -sL "https://drive.google.com/uc?export=download&id=<fileId>"`
     (works for anything the requesting account can already view).
4. If none of the above has a fitting asset, ask CMO before sourcing new stock/AI-gen
   images — don't spend budget/time hunting without a green light.

## Known source-truncation issue (flag if you hit it)

Several BLACK LIQUIDITY briefs describe a full ~60-65s script, but the raw
recorded clip you're handed may be a shorter excerpt that cuts off
mid-sentence (confirmed on the "ทำไมนักเทรดที่เก่งกว่าคุณ ยังขาดทุนอยู่ทุกวัน"
family, episodes 20-26 — clip only reaches ~40s of a much longer script and
stops before naming trap #3 "FOMO" or the checklist/CTA close). If your
source clip appears to stop short of its brief's full script, say so in your
report rather than silently treating the excerpt as complete.

## Minimalist Core Motion Explainer (`mode="motion"`, CEO rulings Q-20261118-0816-a8e9, Q-20261118-0829-d794 & Q-20261118-0857-cd08)

- **Use `mode="motion"` ONLY for the single most essential mechanism moment in a video ("ใส่เฉพาะส่วนที่สำคัญจริงๆ")** — typically 1–2 short windows (7–10s each) where B-roll or raw charts cannot visually explain the underlying cause-and-effect (e.g., B-Book zero-sum money transfer, or how spread widening + a stop-hunt wick sweeps retail Stop Loss before reversing).
- **Strict Minimalist Visual Rules ("อยากได้แบบ Minimal กว่านี้")**:
  1. **Zero outer container boxes, zero dashboard chrome, zero top header bars, zero grid clutter** — float clean geometric nodes/candlesticks directly over the darkened ambient background (`>65%` pure negative space).
  2. **Maximum 2–3 focal elements per scene** and **2–4 words per label** (`พอร์ตคุณ -$1,000 ━━●━━▶ โบรก B-BOOK +$1,000`, `แนวรับ`, `จุดตั้ง STOP LOSS ➔ STOP LOSS แตก!`) so the viewer grasps the core mechanic in `< 0.5 seconds`.
  3. **True Optical Center & Balanced Box Padding**: Every card (`.mm-card`, `padding: 42px 48px`) and pill (`.mm-pill`, `padding: 22px 44px`) must center its text vertically and horizontally via `display: flex; align-items: center; justify-content: center;` with generous, equal Top / Bottom / Left / Right spacing so text never crowds a border.
  4. **Zero Unicode Emoji — Use Locked Brand Icons**: Never use Unicode emojis (`🎯`, `💥`, `🚀`, `✕`, `⚠️`) in motion graphics; for BLACK LIQUIDITY, always use the CEO-selected **`STYLE 1: Neon Wireframe`** icon pack in `.claude/skills/CMO_Procedure_BlackLiquidity_Cut/assets/icons/01_target.png..09_padlock.png` (`Q-20261118-0857-cd08`).
  5. **Use real Chart/B-Roll footage (`mode="chart"` / `mode="footage"`) everywhere else** — never stack complex multi-row radars or multi-panel dashboards when a real MT5/Exness screen recording or clean 2-node animation says it faster.

## SFX discipline

Keep it sparse — see `CMO_Procedure_ReelEditor_TH`'s SKILL.md preferences. A prior draft
of this exact pipeline whooshed on every single cut (10+ identical samples)
and it read as repetitive/annoying on CEO review; the fix was removing it
down to 2-4 sounds tied to distinct UI moments only. Don't regress to the
"whoosh on every cut" pattern.

## Channel Background Music (BGM) & `-24.0 dB` Envelope (`tools/bgm_bed.py`, CEO rulings Q-20261118-1023-871c, Q-20261118-1046-3f25 & Q-20261118-1120-5270)

- **10-Track BLACK LIQUIDITY BGM Library (`BL01–BL10`, Google Flow Music `Lyria 3.5`, `2:28–3:03` full length)**:
  - Stored on Google Drive in `ALL DRAFT/BLACK LIQUIDITY/BLACK LIQUIDITY [62]/Audio` (`1kpG9wATvy0i3mGWz0pmcPCLaWv6xHWjO`, 10 `.wav` + 10 `.m4a` + `BGM_MANIFEST.json` `1kTIABrsSbYPP7ukO4UpuaoKfgCbHfjBI`) and `ALL DRAFT/ASSETS/Audio` (`1QxYqKsn2AqwujTH4It9NXKAsQvXmAOXH`), named using `BL_BGM_{NN}_({Title-EN})_({สถานการณ์ที่ใช้-TH})_({BPM}BPM)_({MMmSSs})_({DD-MM-YYYY})_(FlowMusic-Lyria3.5).{wav|m4a}`.
  - Query and mix by Track ID (`--track BL01..BL10`) or by situation (`--situation bbook|dealing_desk|drawdown|volatility|late_night|reset|sniper|math|survivor|basket`):
    ```bash
    python3 tools/bgm_bed.py --list
    python3 tools/bgm_bed.py --track BL01 --vo voice_and_sfx.wav --ceiling-db -24.0 --speech-duck-db -3.0 --fade-in 4.0 --fade-out 4.0 --out mixed.wav
    ```
  - **Mandatory Volume & Loop Rules (`Q-20261118-1120-5270`)**:
    1. **Strict Ceiling (`ceiling_db = -24.0 dB` below active `-14.0 LUFS` VO)** + **Voiceover Sidechain Ducking (`speech_duck_db = -3.0 dB` -> `-27.0 dB` during speech)**.
    2. **Progressive Fade-In (`0.0s -> 4.0s` from `-40 dB`)** and **Smooth Cosine Fade-Out (`last 4.0s` to `-60 dB`)**.
    3. **Seamless Beat-Matched Loop (`loop_to_duration`)**: Whenever a video is longer than the song (e.g., `2:00` video with a `1:44` song), `tools/bgm_bed.py` trims the decaying tail (`6.0s`), aligns bar/beat phase via cross-correlation, and joins copies with a `3.0s` equal-power cosine crossfade.
    4. **Adding New Tracks**: Use `python3 tools/flow_music_gen.py` (`CMO_Procedure_BlackLiquidity_Cut` `§6h-8`).

## Deliverable contract

- Render output (`reel_clean.mp4`, `cover.jpg`, a caption+hashtag `.txt`)
  goes to the folder named in your task description — do NOT commit these
  binaries into the git branch/PR (repo bloat; this org's `output/`
  convention leaves generated media untracked locally).
- DO commit/leave the authored `timeline.py` (and any new/changed skill
  files) in your worktree so there's a lightweight paper trail of what was
  decided — that's the reviewable artifact for CMO/CTO, not the mp4 itself.
- QC every beat before calling it done (see `CMO_Procedure_ReelEditor_TH`'s step 5) — a
  screenshot-per-beat pass, not just "it built without error".
- Report back: which CUTAWAYS assets you used and from where (skill assets
  vs Drive vs new sourcing), any brand-rule judgment calls you made, and any
  source-truncation or asset-gap issues you flagged.

## Field notes
- 2026-10-11 [MISSING] §Deliverable contract — narrated cut (voice over H3 clips) shipped v1 with cuts placed by time and last-frame holds; CEO heard it jerky and saw frames stall (his words: 'คุณไม่ได้วัดความถี่ของเสียงเลย ไม่ได้ตัดในช่วงที่เงียบจริงๆ' and 'คุณค้างรออะไรบ้างอย่างให้ตรงล็อกหรือป่าวมันเลยดูกระตุก'). v1 QC (LUFS, black frames, silence over 2.5 s) could not see either. Measured on v1: 45 of 198 narration window edges inside speech, 40 of 93 windows overlapping, 38 of 88 bed joins stepping more than 12 dB, 14 `tpad=stop_mode=clone` holds = 5.79 s. What worked in v2 (shared code `docs/prompts/the-old-telling-ep1/edit_lib.py`): (1) cut each narration window at the quietest 8 ms RMS plateau, snapped to a zero crossing, one shared cut between neighbours, 12 ms fades; (2) lengthen a shot with its own next frames, let the rest of the sentence spill into the next shot, the next sentence waits; freeze only the last shot of an ACT under the closing fade; (3) level-match each shot's own sound to the median shot and join with `acrossfade d=0.12 c1=qsin c2=qsin`, bed extended 0.12 s past each cut so picture and sound stay in step; (4) two-pass linear `loudnorm`, not one-pass dynamic. Add to QC: `freezedetect=n=0.00005:d=0.2` (the default noise floor flags hundreds of dark or slow shots) and the edge-level, overlap and join-step numbers, old next to new. Result: edges 45 to 0, overlaps 40 to 0, joins over 12 dB 38 to 11 (the rest sit beside near-silent or deliberately loud shots), freezes 14 to 0 · evidence: cmo-f76492bf, EP1 v2 `edit8/*_audit.json`, CEO messages 2026-10-11 · status: pending
- 2026-09-23 [SUPERSEDED] §Brand rules (No crude language) — the BL มึง/กู line was flipped to follow IRON §37's CEO-confirmed carve-out: BL captions match the audio. The old line made the EP55 editor strip มึง/กู from 9 captions, including the CEO's own hook · evidence: task-52c669bb, IRON-RULES §37 carve-out 2026-08-03/04 · status: superseded
- 2026-11-17 [MISSING] §Asset sourcing order — CEO approved building a cross-channel timecode footage catalog (`tools/footage_catalog.py` + `prototypes/bl-broll-catalog/FOOTAGE_INDEX.jsonl`, 758 videos / 796 segments across `ALL DRAFT/ASSETS`, `00_PRODUCT_LIBRARY`, and `วิธีการใช้งาน APPs MT5`) with `channel_fit` (`MYPASAKON`, `BL`, `TTTM`), `person_shown` (`HANDS_ONLY`, `NONE`, `CEO_PASAKON`, `BL_AVATAR`), and `broker_lock` so editors query top matching `[start_s, end_s]` segments via CLI instead of reading or downloading full Drive folders · evidence: Q-20261117-0922-99fe, `tools/footage_catalog.py`, `prototypes/bl-broll-catalog/FOOTAGE_INDEX.jsonl` → §Asset sourcing order · status: promoted
- 2026-11-18 [MISSING] §Minimalist Core Motion Explainer / §Channel Background Music — CEO approved V6.3 Minimalist Core Motion Explainer (`mode="motion"`, >65% negative space, True Optical Centering, `STYLE 1: Neon Wireframe` icons) and the 10-track BLACK LIQUIDITY Channel BGM Library (`BL01–BL10`, Google Flow Music `Lyria 3.5`, `-24.0 dB` ceiling, `-3.0 dB` speech ducking, `4.0s` fade-in/out, 3.0s beat-matched loop via `tools/bgm_bed.py`) · evidence: Q-20261118-0816-a8e9, Q-20261118-0829-d794, Q-20261118-0857-cd08, Q-20261118-1023-871c, Q-20261118-1046-3f25, Q-20261118-1120-5270 → §Minimalist Core Motion Explainer, §Channel Background Music · status: promoted
