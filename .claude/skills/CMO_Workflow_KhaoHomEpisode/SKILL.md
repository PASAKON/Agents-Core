---
name: CMO_Workflow_KhaoHomEpisode
kind: workflow
description: WORKFLOW — Make one episode of "เอาชีวิตรอดกับข้าวหอม" (vertical 9:16 Short, ข้าวหอม vs a foil) from facts to a posted clip, the way EP1 shipped on 29 Oct 2026. Trigger on /CMO_Workflow_KhaoHomEpisode and on "ข้าวหอม EP", "ทำตอนต่อไป", "EP2 ข้าวหอม", "ทำ Short ข้าวหอม". Do NOT use for BLACK LIQUIDITY, ILAG or lakorn.
owner: CMO
audience: [cmo, project_head, video_editor, browser_operator, researcher, script_writer, content_strategist]
created_by: agent
author: {role: project_head, date: "2026-10-30"}
improved_by: []
aka: []
---

# เอาชีวิตรอดกับข้าวหอม — one episode, end to end

Goal: one ~2-minute vertical Short per episode, in which **ข้าวหอม** (the fixed lead) shows the smart way to survive one
disaster situation and a **foil** (a mystery person, new every episode) does the comically wrong thing. Output: the
clip posted on the FB Page / YouTube channel "เอาชีวิตรอดกับข้าวหอม" after the CEO approves it. Started by the CMO
(on the CEO's order); watched by the CMO. Graph, tools and costs: `flow.yaml` beside this file. The model run is EP1
"น้ำมาแล้ว" (PH#b2ff34d1, 23–30 Oct 2026): final `Work/khaohom-survival/ep01/shorts/out/khaohom-s7-v2m2.mp4`,
1080x1920, 2:07, −14.4 LUFS, $0.35 of voice in all, samples and retakes included
(the final voice alone was $0.105).

## How an agent joins
`Work/khaohom-survival/STATUS.md` (the newest dated lines) → its `node:` → that node in `flow.yaml` → the Step below.
Project folder `K=/opt/MoonieXHQ/Work/khaohom-survival`; episode folder `$K/epNN/`; Short sources in `$K/epNN/shorts/`.
Copy the previous episode's files as the start (`s7.tpl`, `s7-voice/timing.py`, `patch_tpl.py`, `post/`): the
look is approved, so a new episode changes text, stills and timing, not the layout.

## Rules that hold on every step
1. **HARD — ข้าวหอม never changes; the foil and the situation change every episode** (CEO 2026-10-30: "ตัวละคร Unknow
   สามารถเปลื่ยนไปได้ทุกครั้งแล้ว แต่ สถาณะการ นะ แต่ ข้าวหอม ไม่ต้องเปลื่ยน"). ข้าวหอม = sheet
   `$K/design-v2/chars/C1.png` (yellow raincoat, bob), theme 3 "Survival Badge" colours #FFD23F / #14B8A6 / #121428.
   **Why hard:** scope — it is the series identity the CEO picked (Q-20261029-0500-2784, Q-20261029-0500-2553).
2. **HARD — Our own work only.** Nothing from jaysurvivals or any other channel: no cat, condo blackout, their lines,
   "90 litres", door knock, red-tag rule card, black end card, pill chips, peephole rings, captions at 64% height.
   **Why hard:** legal / CEO ruling "build ours from the start" (memory feedback_build_ours_from_the_start).
3. **HARD — Facts only from the episode's fact sheet** (`$K/facts/FACTS-ep*.md`, each fact with a named source). No
   new number on screen or in the voice that the sheet does not carry. **Why hard:** safety — this is survival advice.
4. **HARD — Picture prompts never ask for blush, red cheeks or red ears** (หน้าแดง/หูแดง); show feeling by action.
   **Why hard:** CEO ruling 2026-09-28 (memory feedback_h3_no_red_face_ears).
5. On screen: Thai only, no « », no channel name or handle inside the video, no English words.
   `scripts/check-post-text.sh <file>` checks text files.
6. Money: voice is the only paid step, under 5 THB per episode unless the CEO says more; it runs only on a labelled
   spend script card (`ALL_Rules_Approvals`, memory feedback_echo_card_not_spend_auth). Images (ChatGPT) and music
   (Flow Music free credits) are $0.
7. Contabo renders: one at a time under `flock /opt/MoonieXHQ/Work/.bl-render.lock`, `free -m` first
   (memory feedback_contabo_one_render_at_a_time). Light work under `nice -n 19` + `timeout`.
8. Every pick goes to the CEO as a media question card (`ask_ceo`, `pick='one'`, one numbered sheet per item);
   quote the `Q-…` id in STATUS.md when you act on it.
9. winbox runs a live-money MT5 EA: never kill `terminal64.exe`, never reboot it, never close or reload a Chrome tab
   you did not open (repo `CLAUDE.md` §winbox).

## The steps

### Step 1 · Fact sheet [node: facts]
Do: pick ONE situation for the episode (EP1 flood night; EP2 "เรือเที่ยวสุดท้าย" evacuation by boat; EP3 "กลับบ้าน"
returning home). Hand a researcher worker a brief to collect 6–10 facts, each with a Thai government or CDC/WHO
source and the raw quote; mark CONFIRMED / CHANGED / PARTIAL. Spot-check two quotes yourself. A PARTIAL fact is
never shown. Gate: every line the script will use maps to a CONFIRMED fact id.

### Step 2 · Script smart vs foil [node: script]
Do: write `shorts/sN-script.md` as a table `| # | still | line |`, ~1,000–1,300 Thai chars (≈1:40–2:10). Shape, which
the CEO set for EP1 (Q-20261029-1356-8798, approved Q-20261029-1438-fe4e):
- Hook ≤4 s: "…คืนแรกนี้ คุณจะทำแบบข้าวหอม หรือแบบชายคนนี้".
- Three dangers of the situation, each a pair: "ถ้าเป็นข้าวหอม จะ… แบบนี้" (bright stills) then "แต่สำหรับชายคนนี้แล้ว
  …ไม่ดีเลย" (dark stills). The foil is played for laughs and never lectured, and the voice never says "อย่าทำ" about
  him. Keep the screen safe: no injury, no electrocution, no death. At most a comic splash, a spark icon, a yawn bubble.
- Each danger closes on ข้าวหอม's rule card "ข้อหนึ่ง/ข้อสอง/ข้อสาม …", stated positively.
- Recap of the three, then "มาเอาชีวิตรอดกับข้าวหอมด้วยกันนะ", then a silent end card "เอาชีวิตรอดกับข้าวหอม · ดูตอนเต็ม…".
- ข้าวหอม talks to คุณ, friendly and a bit cheeky.
Argon drafts it well from a brief (`$K/ep01/shorts/BRIEF-s6.md` is the model). Check every claim against the fact
sheet yourself. Gate: every claim traced to a CONFIRMED fact.

### Step 3 · CEO script OK [node: script_ok]
Do: send the script table as a question card; a cut-off note gets a new card asking only for the missing part. Gate: the CEO approves the script BEFORE any voice spend.

### Step 4 · Foil character [node: foil]
Do: a NEW foil each episode. Write `shorts/sN-stills/char-fool.json` with one plate: a character sheet in the same
illustration style as C1 (attach C1.png), a different person (EP1: lanky Thai man in his 30s, messy hair, sleepy
cheerful face, grey tank top, floral swim shorts, flip-flops; front / side / back + 3 comic expressions; plain
background; no text). Run it through `tools/chatgpt_images.py` on the signed-in ChatGPT Chrome (winbox :9224) under
`home_lock`. Gate: one sheet, a person clearly not ข้าวหอม, no text on it.

### Step 5 · Stills [node: stills]
Do: `plates.json` per side. ข้าวหอม plates attach C1.png and keep the approved framing block (head at ~40% height,
clear of the top HUD, lower band y 1000–1410 kept free for cards). Foil plates attach the foil sheet and add "darker,
colder colour grade: blue-grey, low light", comic poses. 12 smart + 6 foil stills was enough for 2:07. Reuse an
earlier ข้าวหอม still when the action is the same. Gate: a numbered contact sheet checked by eye; faces clear of the
card band; no blush.

### Step 6 · Voice v4 Jessica [node: voice]
Do: ElevenLabs v4 voice **Jessica** (CEO pick Q-20261029-1211-5742), `stability 0.5`, `language_code th`, `seed 7`,
`timestamps true`, the script split into 6–7 chunks of ≤260 chars (copy `ep01/shorts/s7-voice/job.json`). Dry-run
`tools/fal_tts.py` for the exact cost, then raise a labelled spend SCRIPT card with `--max-usd` about 25% over it,
pinned to origin/main after `git fetch`. EP1 S7: 1,312 chars = $0.105. Gate: every take present, duration within the
script estimate, the ledger row written.

### Step 7 · Timing table [node: timing]
Do: `timing.py` (copy it from the previous episode's `sN-voice/`) lays the chunks end to end (start 0.5 s, 0.8 s gap), cuts subtitles of ≤38 chars at word gaps from
the v4 character timestamps, and maps each subtitle to its script row; it writes `timing.json`, and `patch_tpl.py`
writes those times into the template's one `T` table. A retime is one edit, never a hand edit of times in the
template. Gate: `timing.json` covers every row; total length = voice length + the 3 s end card.

### Step 8 · Template [node: template]
Do: copy the previous `sN.tpl`; Argon changes only text, stills and the row keys (brief pattern
`ep01/shorts/BRIEF-s6-tpl.md`). The approved look, set over four CEO fix rounds on 29 Oct: centred subtitles that hug
the text; compact cards in the lower band over the dimmed still; small corner clock + thin supply bars shown only in
their windows; a side tag "ข้าวหอม" (sunflower) / foil (slate, "?") for 1.2 s on each side change; foil stills get a
`#0b1830` multiply at 0.25 and no torch glow; ข้าวหอม stills keep the warm torch glow, rain, dust and water shimmer so
nothing is ever still. Snapshot a few frames (`npx --yes hyperframes@0.8.40 snapshot …`) before the full render.
Gate: snapshots checked by eye, no card over a face, Thai only.

### Step 9 · Render [node: render]
Do: `$K/tools/render_short.sh sN` (builds `kit/build.py`, renders under the lock). 2:07 took ~25 min on Contabo. Then
mux the voice and normalise to −14 LUFS. Gate: 1080x1920, the length of the timing, a contact sheet checked by eye.

### Step 10 · Music bed [node: music]
Do: Flow Music (flowmusic.app) on winbox Chrome :9226, signed in to Google; prompt a soft instrumental bed for the
mood, two or three takes, free credits only (EP1 used none of its 30 daily credits). Tunnel
`ssh -f -N -L 9276:127.0.0.1:9226 winbox`, Playwright `connect_over_cdp`, kill the tunnel after. Mix the bed well
under the voice with fades in and out, then loudnorm −14 LUFS; one file per take. Licence: Google claims no
ownership; commercial use needs a paid AI plan, so swap or license the music before the channel is monetised
(`$K/ep01/post/LICENCE-flowmusic.md`). Gate: 2–3 mixed takes ready; the CEO picks one in the next step.

### Step 11 · CEO final OK [node: approve]
Do: one media card with the mixed takes (pick one), then the finished file if anything changed. A "แก้" answer becomes a fix brief (`BRIEF-sN-fixK.md`) and goes back to
the step it names, never a reshuffle of the whole look. If a card note arrives cut mid-word, ask only for the
missing part on a new card. Gate: the CEO's OK, with its `Q-…` id in STATUS.md.

### Step 12 · Post kit [node: postkit]
Do: copy `ep01/post/`: `TEXT.md` (2 captions with hashtags, the bio), 3 Reel covers 1080x1920 from `cover-*.tpl`
built with the episode's best still, and the episode title. Channel assets (avatar, banner, FB cover) are made once
and reused. `scripts/check-post-text.sh` on every text file. Gate: the check passes and the covers are checked by eye.

### Step 13 · Drive Final Draft [node: drive]
Do: the episode folder `ALL DRAFT/FB: เอาชีวิตรอดกับข้าวหอม/EPnn <title>/Final Draft/` (series folder created 30 Oct;
its id is in `CXO_Knowledge_GDrive_FolderMap`). A new EP folder needs the CEO's OK with its full path first
(`CXO_Rules_GDrive_Filing` rule 3), and the map gets a tree line and an ID-table row in the same turn (rule 6). Upload
with `scripts/gdrive-bridge/ilag_rest.py` `upload()`, which reads back the md5 by id (rule 12). Gate: Drive md5 =
local md5 for every file.

### Step 14 · Post [node: post]
Do: the CMO lane posts, only after the CEO's OK to post. FB Page "เอาชีวิตรอดกับข้าวหอม" (under the CEO's second
Facebook profile; ids in `$K/workers/W1/REPORT.md`) and YouTube @khaohomsurvival (a brand channel on the CEO's main Google account). IG was not
linked yet on 30 Oct (Facebook offered only an unrelated existing IG account). TikTok waits for a new email and phone
(CEO 29 Oct). Gate: the post URL opens and shows the clip.

## After the post · disk clean-up
 when the episode is posted, back up the keepers (final, alternates the CEO saw) to that EP's Final Draft with md5
by id, then put the superseded renders (`build/*/out/*.mp4`, old `shorts/out/*`, snapshot frames) in one list and
delete them through ONE red Run card that checks the sha256 of the delete script and the list (Contabo's classifier
refuses deletes, even Green-list ones). Keep the final, all stills and the sources. EP1: 3.6 GB → 512 MB
(RUN-20261029-1833-6c82). Gate: the project folder ≤1 GB, the final still present.

## Lessons from EP1 (dated)
- 2026-10-29 Contabo allows ONE browser_operator at a time, and `delegate_task` refuses the project slugs
  khaohom-survival / khao-hom-survival: file workers under project `mooniex-agents`.
- 2026-10-30 A worker spawned ON winbox died at start with "Login expired" (its Claude login) and made nothing for
  2 hours. Drive winbox Chromes from a Contabo worker over an ssh CDP tunnel instead, and check a new worker's first
  output within ~15 minutes.
- 2026-10-30 When the CEO is at the winbox desk, open the login page as a new tab in the headed Chrome
  (`curl -X PUT http://127.0.0.1:9226/json/new?<url>` over ssh, then `/json/activate/<id>`): he logs in on the
  screen, faster than a relay request.
- 2026-10-29 Disk over 90% blocks every spawn: check `df -h /` before delegating, and clean up after each episode.

## STATUS.md template
```
flow: khaohom_ep · run: <YYYY-MM-DD>-epNN
node: <node id> · state: running | waiting:CEO | blocked:<code>
done: [<node ids>]
blocker: <code> — <one line>
spent: $<cash> API · <turns> turns
```

## Field notes
