---
name: CMO_Workflow_BlackLiquidity
kind: workflow
description: "WORKFLOW — One BLACK LIQUIDITY episode end to end as a Flow: script to publish, through ClaudeFlow stages, Jev, compose, checker and editor. Trigger on /CMO_Workflow_BlackLiquidity, \"ทำ BL EP ใหม่\", \"BL ตอนนี้อยู่ขั้นไหน\". Use instead of CMO_Procedure_BlackLiquidity_Cut for the episode order; not for ILAG short films (CMO_Workflow_ShortFilm)."
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
   retry, and ask the CEO with the exact amount when there is none. The watcher holds the cap by the fal +
   OpenRouter balance delta: ClaudeFlow's own guard (`EP_BUDGET_USD`, default $3.00, `src/lib/cost-ledger.js`)
   stops only at its own ledger total and does not count the OpenRouter `prompts` call.
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
Do: `--stages=editor_handoff` as soon as Steps 4–8 pass their gates, before any edit work starts. It costs
nothing: it only sets the row to DONE and marks the manifest stage (`runEditorHandoff` in `videogen.js`).
The scripter waits on it, so a run that skips it never reaches the edit. EP58–EP60 briefs stopped before it;
later runs do not. `resume-video.js --dry-run` shows `scenes` as missing after every stage-by-stage run;
that is a gap in the diagnoser, not a failure.
Gate: voice, transcript, lipsync parts and scene clips are all on Drive, and the row reads DONE.

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
- 2026-10-13 [WRONG] §Step 1 length forecast — "the rate is falling" (14.2, 12.1, 11.5, 11.4) broke on EP61: 852 spoken characters came out at 68.0 s after the pipeline's 1.15x speed-up, 12.5 chars/s. The series is not monotone; forecast with the 11.4 to 12.5 range and expect 68 to 75 s for 852 characters · evidence: Mac CTO 671f688f report on row 487a79be (voice md5 4e8cd994), EP61 task-d002e35e · status: pending
- 2026-10-13 [MISSING] §Step 4 voice gate — "within 5% of the forecast, a bigger miss goes back to the CEO" stopped EP61 for a CEO question although the voice was SHORTER (68.0 s against 74.7 s), inside the 75 s cap and cheaper (lipsync bills on seconds). A miss that is longer than forecast or over the cap goes to the CEO; a shorter one inside the cap is the CMO's call, logged as decided-for-CEO · evidence: EP61 hold 13 Oct, CMO decision to the Mac CTO · status: pending
- 2026-10-13 [MISSING] §Step 3 to 9 who runs it — every paid stage has `host: mac` in flow.yaml, so a Contabo CMO cannot run them; the hand-off to the live Mac CTO is a message with the origin/main sha of the approved script, the exact approved spend, the stop rule (balance delta passes the approved total) and the voice gate. Say so in the steps · evidence: EP61 hand-off to Mac CTO 671f688f, a16ca562 · status: pending
- 2026-10-13 [MISSING] real-footage step where the raw stills go — `tools/bl_realfootage.py` writes the raw, uncensored captures to the repo-relative `output/bl-realfootage/<ep>/` (DEFAULT_OUT_ROOT), untracked inside the worker's worktree, so they sit in a directory that is removed with the worktree and show as untracked on a merge. Brief the worker with `--out /opt/MoonieXHQ/Work/<task>/out` (Work/RULES: out/ goes to Assets or Drive); after the run copy to `Assets/Agents/Core/bl-realfootage/<ep>/` and md5-check before anything is removed · evidence: task-d002e35e (16 files, 8.7 MB, copied 13 Oct, md5 all match), CTO e106b78b's close-out letter · status: pending
- 2026-10-14 [MISSING] publish / A-B read — how to read post times and views from TikTok Studio without the CEO: with the BL Chrome logged in (Browser Home `tiktok-bl`, CDP 9282) open `tiktokstudio/content` (the list is virtualised: step the scroll container by ~500 px and collect rows, a single scroll-to-bottom shows only 2023 posts) and `tiktokstudio/analytics/<video id>` (text gives views, watch time, full-watch %, traffic source, search queries; the 7-day chart does not come out as text, so a 48 h split is not readable that way). The Chrome's zone is Europe/Berlin, so the dates shown are CEST (Thai = +5 h). Lifetime views of the 6 posts before EP58 sit at 337–481, the yardstick for "did the cover change anything". The arm a post carries is not in Studio; match the cover to frame 0 of the two finals, or ask the CEO · evidence: CMO c4432bad 14 Oct, EP58 post 7693208243417402645 (365 views after 9 days; EP59 and EP60 not posted) · status: pending
- 2026-10-14 [MISSING] publish / A-B read — which arm a post carries: the Studio analytics page of a post has no `<video>`, no poster and no cover in its DOM (a spinner after 14 s), so a cover cannot be fetched from there. The content list does show every post's thumbnail, but only after ~10 s and not as an `<img>` the script can list: take a viewport screenshot of `tiktokstudio/content` after the rows paint and crop the thumbnail from that. Match it to the finals with a 60x80 grayscale normalised correlation (centre-crop the 9:16 frame to 3:4, drop the bottom strip that holds the duration label), run the same match against every other final as a control, and confirm on one side-by-side sheet. EP58: arm A 0.78 at 46.5 s, arm B 0.42, controls 0.26 to 0.49. It only works when the two arms differ at the cover frame (EP58's do, mean pixel difference 72 at that second); check that before trusting it. A script that wraps each route in its own try returns a partial result; one without it cost a card to a `document.images.forEach` bug (an HTMLCollection has no forEach) · evidence: Run cards RUN-20261013-1959-ad26, -2003-8cb6 (failed), -2026-ff6a; `prototypes/bl-tiktok-ops/AB_POSTS.md` 0c2805a3 · status: pending
- 2026-10-14 [MISSING] §publish — how to fill and schedule a post in TikTok Studio from the `tiktok-bl` Browser Home (CDP 9282) when nobody is at the desk: CDP mouse and keyboard events do nothing in that Chrome (the dialog Cancel, the pencil icon, Backspace and Enter all failed), only DOM clicks (`el.click()`, a MouseEvent sequence on the right element) and `Input.insertText` work. The description is a Draft.js editor prefilled with the file name; Enter is swallowed by a custom `handleReturn` and select-all keys are dead, so set Draft's own selection to the whole document through the React fiber (`editorState.constructor.forceSelection`, then `props.onChange`) and dispatch ONE synthetic paste event: it gives real paragraphs and replaces the file name (check block by block, counter 651/4000). Schedule: click the `schedule` radio input, then the 'Allow your video to be saved' dialog needs 'Allow'; time = click the `.tiktok-timepicker-option-text` SPANS (hours list, minutes list), not the item div; date = click the date input then `.calendar-wrapper .day.valid`. 'AI-generated content' switch opens a 'Turn on' dialog; the content-checks dialog is closed by JS-clicking Cancel. `set_input_files` needs `timeout=240000` when the box is loaded (load 17). A scheduled post shows in the content list with its future date and no 'Scheduled' word; read the list in a NEW tab so an open form survives · evidence: EP61 and EP59 scheduled 14 Oct 04:20 and 04:30 Thai, tools `prototypes/bl-tiktok-ops/studio_post_flow.py` + `studio_post_confirm.py`, list read 14 Oct · status: pending
- 2026-10-14 [MISSING] §publish — the question card before posting has to list every open gate AND every account setting that carries risk: EP59 legal review, EP60 CySEC unverified and the 'AI-generated content' label were each found after a card was already answered and cost a second or third card · evidence: Q-20261013-2041-ae68, Q-20261013-2044-865f, Q-20261013-2114-267a · status: pending
- 2026-10-14 [MISSING] §publish — the auto-mode classifier refused two Studio actions with no reason (turning the AI label on, then the final Schedule click for EP60) although the same script had clicked Schedule for EP61 and EP59 minutes earlier; do not retry or split the call, put the decision on a question card or a Run card with the exact command and leave the filled form tab open · evidence: Q-20261013-2114-267a answered, then RUN-20261013-2136-69c9 raised for the EP60 click · status: pending
- 2026-10-13 [WRONG] Step 4 voice gate — the forecast in STATUS.md is made from the raw speaking rate (11.4 chars/s, 74.7 s for 852 chars), but the pipeline speeds the joined track up 1.15x with ffmpeg before upload (`[videotts] FFmpeg speed 1.15x`), so the delivered voice ran 68.0 s (raw 78.2 s), -8.9% and outside the ±5% gate. Measured delivered rate: 852 / 68.0 = 12.5 chars/s. Forecast against the delivered track (chars / 12.5), or gate on the raw length the log prints · evidence: EP61 row 487a79be, Drive voice md5 4e8cd994…, session cto-671f688f · status: pending
- 2026-10-14 [COSTLY] Step 8 scenes — on Contabo `BROLL_CATALOG_DIR` is unset, so `--stages=scenes` skips the catalogue for every scene and silently generates the hook scenes with Seedream + Kling (EP62: S01–S03, $1.78, outside a $0.90 CEO GO that named tts+prompts+transcript+lipsync only; the other 23 scenes skipped). Nothing in the stage asks before spending, and it emails the CEO per clip. Before Step 8, check the env (`BROLL_CATALOG_DIR` set and the catalogue readable); if it is not, skip `scenes` and run `editor_handoff`, and the cut fills scenes from real stills and cards. Kling needs the CEO's exact-cost OK first · evidence: row cc13ea6b-4009-4050-aaa1-da208294d711 cost_breakdown kling 1.68 + seedream 0.10, /opt/MoonieXHQ/Work/bl-ep62/scenes.log · status: pending
- 2026-10-14 [WRONG] flow.yaml host — the tts, scene_prompts, transcript, lipsync, scenes and editor_handoff nodes say `host: mac`, but EP62 ran all of them on Contabo (ClaudeFlow checkout /opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow, /opt/node-v22/bin/node, cwd = checkout for .env) by CTO Main c34459eb ruling 14 Oct 10:45 TH: «option (b) … nothing in these stages needs the Mac». `run-bl-script.js --row=` also needs `--title=` or it prints usage and changes nothing · evidence: row cc13ea6b…, STATUS.md bl-tiktok-ops 14 Oct · status: pending
