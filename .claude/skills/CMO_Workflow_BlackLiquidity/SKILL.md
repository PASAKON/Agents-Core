---
name: CMO_Workflow_BlackLiquidity
kind: workflow
description: "WORKFLOW — The ordered workflow for one BLACK LIQUIDITY episode end to end, as a Flow the ClaudeFlow Control Room draws: script, CEO approval, ClaudeFlow stage run (Drive folder, TTS, transcript, scene prompts, catalogue B-roll, lipsync, hand-off), real footage, Jev calls, scripter, compose, checker, editor, CEO review, publish. Each step names its node in flow.yaml and the skill that owns its rules; the rules live there, not here. Trigger on /CMO_Workflow_BlackLiquidity and whenever a BL episode starts or an agent joins one mid-way: \"ทำ BL EP ใหม่\", \"BL ตอนนี้อยู่ขั้นไหน\", \"รัน stage 2 BL\", \"BL episode workflow\". Use instead of CMO_Procedure_BlackLiquidity_Cut when the question is the order of the whole episode, not how to cut it; do NOT use for the ILAG short film (CMO_Workflow_ShortFilm) or ละครสั้น serials (CMO_Workflow_LakornSerial)."
owner: CMO
created_by: agent
author: {role: cto, date: "2026-10-02"}
audience: [cmo, cto, video_editor, browser_operator, developer]
---

# BLACK LIQUIDITY episode — end to end

One run turns one approved script into a TikTok episode on @black_liquidity (the AI-avatar channel that
exposes Forex and Ponzi scams), with the cut and its sources filed on Drive. The CEO starts every run by hand;
the BL CMO on Contabo watches it. One run may spend at most the `budget.cash_usd` in `flow.yaml` in API
credit. Order, tools, providers, costs, verify commands and stages live in `flow.yaml` beside this file; this
file says how to work each step and points to the skill that owns its rules. Written 2026-10-02 by the CTO
from the EP57–EP60 runs (task-8ba088ce, task-47ab0231, task-8f940c57, task-c32c40e8) for the CMO, who owns it.

## How an agent joins a run

1. Open the run's `STATUS.md` (template below). No file means the run is at `script`; create it.
2. Read its `node:`, then that node in `flow.yaml` (tool, owner skill, verify, gate), then the matching step
   below, then the owner skill.
3. Do the step, run its verify, update `STATUS.md` (node, state, done, blocker, spent) and file the outputs.
4. Anything that needs the CEO goes out as one list, each item with a recommended answer.

## Rules that hold on every step

1. **HARD — money (`ALL_Rules_Approvals`).** No paid stage runs before `approve` passes, and a run stays
   under its cash cap. A retry of a paid stage needs room under that cap; work out the room before you
   retry, and ask the CEO with the exact amount when there is none.
   **Why hard:** money. A fired API call cannot be taken back, and a truncated `prompts` call still bills
   (EP59, $0.167 sunk).
2. Compliance on what the episode says belongs to `CMO_Standard_BlackLiquidity_Script` (§Compliance). Every
   step that changes a spoken word or an on-screen claim goes back through it.
3. Drive: read `CXO_Rules_GDrive_Filing` before the first Drive action of the session. md5 is the proof of
   an upload.
4. Media never goes in git: scripts, beats and reports go in the repo, renders and clips go on Drive.
5. A render on Contabo runs one at a time and needs `free -m` checked first: the box has 7.9 GB for every
   session (field note 2026-10-02 in `CXO_Protocol_DevSpawn` §3d).

## The steps

### Step 1 · Script [node: script]
Do: write the script to `CMO_Standard_BlackLiquidity_Script`, one `[SECTION-n] spoken line` per row in
`prototypes/bl<ep>-script/SCRIPT.tsv`. Forecast the voice length at about 11.4 spoken non-space characters
per second (EP57–EP60 ran 14.2, 12.1, 11.5, 11.4: the rate is falling). TODO(cmo): who picks the topic today
(the CEO hands one over, or the CMO proposes), and whether a topic node belongs before this one.
Gate: the standard's own check passes, and the forecast is inside the episode target.

### Step 2 · Script approval [node: approve]
Do: send the CEO the exact text, plus the forecast length and the forecast cost of the paid stages (lipsync
≈ chars ÷ 11.4 × 0.5 × $0.0117 × 1.028, plus about $0.16 for `prompts`). Commit the approved file and
quote the CEO's words in `STATUS.md`. A later wording change goes back through this step.
Gate: the approval names this text; the sha is in `STATUS.md`.

### Step 3 · Row and Drive folder [node: drive]
Do: `node scripts/run-bl-script.js --title=… --script-file=…` in the ClaudeFlow checkout caches the script
verbatim (status `MANUAL_RUN`, which the automatic crons never pick up). Then run
`node scripts/resume-video.js <row> --stages=drive_setup`. Read `row.script` back and compare it to the
approved file before any paid stage. The `script` stage then reports `skipped`; that is correct, because the
LLM writer must never run on an approved script.
Gate: byte-equal read-back and a Drive folder id, both in `STATUS.md`.

### Step 4 · Voice (TTS) [node: tts]
Do: `resume-video.js <row> --stages=tts`, one stage per call. Log the ffprobe duration. The cost ledger
over-counts TTS and leaves OpenRouter out, so the real spend is the fal and OpenRouter balance delta
(numbers only, never a key).
Gate: duration within 5% of the forecast; a bigger miss goes back to the CEO before lipsync.

### Step 5 · Scene prompts [node: prompts]
Do: `--stages=scene_prompts`. The call uses about 15k of its hard 16,384 output tokens. A truncated reply
fails with "Unterminated string in JSON" and saves nothing, so check the room under the cap before the
single retry (Rule 1).
Gate: one item per script line in `_MANIFEST.json`.

### Step 6 · Transcript [node: transcript]
Do: `--stages=transcript` after `tts`.
Gate: every script line is found in `row.transcript`; lipsync splits its parts on these timings.

### Step 7 · Lipsync [node: lipsync]
Do: `--stages=lipsync`. It needs `row.transcript` and the voice track, and it bills on the real seconds of
the avatar parts (about half the episode). It is the biggest cash item of a run, so spot-check each part.
Gate: every part is on Drive and its mouth is in sync.

### Step 8 · B-roll scenes [node: scenes]
Do: `--stages=scenes`. Clips come from the B-roll catalogue first (EP59 38/40 and EP60 40/40 matched,
none generated). A scene with no clip that is a real-footage beat stays empty on purpose; name it in
`STATUS.md`. A Kling generation costs money, so it needs the CEO's OK on the exact cost first.
Gate: every non-real-footage scene has a clip.

### Step 9 · Editor hand-off [node: handoff]
Do: `--stages=editor_handoff` marks the row DONE. Run it only when the edit is ready to start: a brief that
stops before it (EP58–EP60) leaves this node open on purpose. `resume-video.js --dry-run` shows `scenes` as
missing after every stage-by-stage run; that is a gap in the diagnoser, not a failure.
Gate: voice, transcript, lipsync parts and scene clips are all on Drive.

### Step 10 · Real footage [node: footage]
Do: capture the pages the script cites with `tools/bl_realfootage.py run --shots <shots.yaml> --episode
bl<ep> --drive-parent <folder>`, which censors by the DOM, never logs in, and writes `REAL_MANIFEST.json`.
`CMO_Procedure_BlackLiquidity_Cut` §5a owns how real footage is used in the cut. TODO(cmo): who writes `shots.yaml`
from the script today, and which machine runs the capture (EP59's 14 stills were uploaded by a helper
script, not by this runner).
Gate: every real-footage line has its clip or still, and each upload's md5 matches.

### Step 11 · Jev editorial calls [node: jev]
Do: follow `CMO_Procedure_BlackLiquidity_JevEditor`: run `plan` on `SCRIPT.tsv` with
`--manifest real/REAL_MANIFEST.json`, then `storyboard`. Check that the decision provider is configured
before trusting the output. On EP58 every one of 127 answers came back null at $0 because no provider was
set, and the tool gave no warning.
Gate: no answered row is null, and every flagged row has been looked at.

### Step 12 · Scripter [node: scripter]
Do: `tools/bl_scripter.py` reads the script, the timings, the Jev decisions and one frame per line, and
writes `beats.json` in one `claude -p` call on the plan (no API key). Alone it does not ship: in the
2026-09-25 A/B its output failed the checker (`docs/ops/bl-ab-2026-09-25/REPORT.md`), so it feeds the editor.
Gate: one beats row per script line.

### Step 13 · Compose and render [node: compose]
Do: `tools/bl_compose.py --beats … --generator-dir … --t-max …` per `CMO_Procedure_BlackLiquidity_Cut`. On
Contabo a window of 9 s or less renders in 5–11 min. Render the windows one at a time (Rule 5).
Gate: a full render; `check_pieces_landed` passed.

### Step 14 · Checker [node: checker]
Do: `tools/bl_checker.py --video … --beats … --composition …`. Add `--face-box` when a face is on screen,
or the text-over-face gate passes without checking anything (Cut skill field note). Hand the editor every
failure by name.
Gate: exit 0, or the failures are listed for Step 15.

### Step 15 · Editor [node: editor]
Do: a `video_editor` works the cut under `CMO_Procedure_BlackLiquidity_Cut`. It fixes what the checker and
the CEO's taste flag, re-renders from `compose`, and merges with `tools/bl_merge.py` (KIN-entry grace via
`--beats`). It reads 8 spread frames and writes `REPORT.md`. The stage is `agent`: a candidate and a scorer
exist (`tools/bl_scripter.py`, `tools/bl_score.py`), but the candidate failed the checker, so it does not
run in shadow yet. TODO(cmo): confirm the watcher (`CMO@contabo` in `flow.yaml`); today the CTO delegates
and watches the editor run.
Gate: the checker passes on the final, and the report names every change from `beats.json`.

### Step 16 · CEO review [node: review]
Do: send the CEO the final as one link, with the checker result and anything the editor could not fix.
A fix sends the run back to `compose` or `editor`, never to an earlier paid stage unless the CEO asks.
Gate: the CEO's approval, quoted in `STATUS.md`.

### Step 17 · Publish [node: publish]
Do: no tool in the repo posts to TikTok. `tools/bl_tiktok_watch.py` only reads, and `tools/bl_tiktok_cta.py`
decides the replies to comments and DMs after the post. The post is made by hand with the cart link, and its URL goes into
`STATUS.md`. File the final on Drive under `CXO_Rules_GDrive_Filing`. TODO(cmo): who posts and from which
device and account session.
Gate: the post is live and its URL is recorded.

## STATUS.md template

```
flow: bl · run: <YYYY-MM-DD>-ep<NN>
node: <current node id> · state: running | waiting:CEO | blocked:<blocker code>
done: [<node ids>]
blocker: <code> — <one line>
spent: $<cash> API · <turns> turns
```

## Field notes
