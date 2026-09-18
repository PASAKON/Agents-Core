---
name: blackliquidity-cut
description: >-
  Cut a BLACK LIQUIDITY episode — an AI-avatar talking-head video for the
  channel's TikTok — from a delivered Drive project folder into a finished
  1080x1920 30fps MP4 with Thai kinetic graphics, using HyperFrames HTML and
  the channel's measured motion grammar. Use this whenever a task says cut,
  edit, or finish a BLACK LIQUIDITY / BL clip, names a BL episode number, or
  points at a Drive folder holding `_MANIFEST.json`, `lipsync_part_*.mp4` and
  `S##` scene clips. Do NOT use it for MYPASAKON, LUNGNOTE, TRADER UNCUT or
  ILAG (different channels, different look), for a plain phone-shot talking
  head with no manifest (that is `reel-editor-th`), or for a still image.
created_by: agent
audience: [video_editor]
---

# BLACK LIQUIDITY — cutting an episode

This produces a specific look on purpose. Every constant below was measured
off an edit the CEO paid a human ฿1300 for; none of it is taste. The first cut
made this way was approved with no changes ("นี่คือคลิปการตัดต่อมืออาชีพเลยนะ"),
so **match the constants before you improve on them.**

Reference for the bar: `reference/bl51-140s-reference.jpg` — 24 frames of the
approved cut in one image. **Read that image, not a video.** Reading frames out
of an MP4 costs far more than reading one contact sheet, and it is the reason
`bl_tools.py sheet` exists.

## What you are given

A Google Drive folder containing:

| file | what it is |
|---|---|
| `_MANIFEST.json` | the project: script lines, categories, which scenes rendered |
| `audio-hq-*.mp3` | the full voice track — **this is the clock** |
| `lipsync_part_*.mp4` | the avatar with a matched mouth, usually 3 × 15 s |
| `S## - <role> (~Ns).mp4` | generated scene plates, some with the avatar, some pure b-roll |
| `Finals/` | a previous editor's cut — **ignore it, it is not the bar** |

Read `_MANIFEST.json` first: `stages.scene_prompts.items[]` gives every script
line with its true wording and `has_character`; `stages.scenes.items[]` says
which ones actually rendered (`drive_file_id` present) and which were skipped.

## The pipeline — do these in order

### 1. Pull the project and read the manifest
Files download with `curl -sL "https://drive.google.com/uc?export=download&id=<id>"`.
Note which scenes exist. On BL51 only 12 of 37 had footage; the gaps become
motion-graphic blocks, which is normal, not a blocker.

### 2. Find the REAL lipsync offsets — never trust the filenames
```bash
python3 <skill>/scripts/bl_tools.py offsets \
  --master audio-hq.mp3 \
  --parts A=lipsync_part_a_0s-15s.mp4 B=lipsync_part_b_63s-78s.mp4 \
  --json offsets.json
```
On BL51 the names said 0 s / 63 s / 125 s and the parts really sat at
**0.00 / 62.71 / 125.42** — 9 and 13 frames of lip error if you believe the
name. If a part comes back with `r < 0.9` the tool warns. Before assuming a
different take, correlate the part directly at its filename's nominal offset
(the tool's own `pcm`/`nrm` helpers, 10 s window): on BL50 the scan returned
84.39 s at r=0.031 for a part that really sat at 145.49 s (r=0.999) because it
ran to the last sample of the track — fixed in the tool 2026-09-18, and the
worker who caught it did exactly this. If the direct check is also weak, stop
and ask.

### 3. Transcribe for timing
```bash
source ~/.claude/skills/reel-editor-th/.venv/bin/activate
python3 -c "import mlx_whisper,json; r=mlx_whisper.transcribe('audio16k.wav', \
 path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='th', \
 word_timestamps=True, condition_on_previous_text=False, verbose=False); \
 json.dump(r, open('transcript.json','w'), ensure_ascii=False)"
```
**Use the ASR for timings and the manifest's `script_text` for wording.** The
ASR mishears the channel's vocabulary — on BL51 it produced "แชร์" for "แฉ",
"ทันวา" for "ธันวา" and "Forex CD" for "Forex 4D".

**Never time anything from the manifest's `recommended_sec`.** On BL51 those
summed to 157 s against a 140.36 s track.

### 4. Measure where text may sit on each plate
```bash
python3 <skill>/scripts/bl_tools.py safearea lipsync_part_a.mp4
```
It prints the chin and a `SAFE TEXT TOP`. A block whose `top` is above that
number crosses the speaker's face. Run it per clip — do not assume two parts
of one set are framed alike, and do not decide this by looking at two frames
(that is exactly how a wrong rule got written the first time).

### 5. Normalise the media to one format
```bash
# lipsync is 640x1024 @24fps against a 1080x1920 @30 target
ffmpeg -i lip.mp4 -an -vf "scale=-2:1920:flags=lanczos,crop=1080:1920,\
unsharp=5:5:0.7:5:5:0.0,fps=30" -c:v libx264 -crf 16 -pix_fmt yuv420p out.mp4
# scene plates are 1076 or 1080 wide - same filter without the unsharp
ffmpeg -i s04.mp4 -an -vf "scale=-2:1920:flags=lanczos,crop=1080:1920,fps=30" ...
```
Keep the ORIGINAL lipsync files too: step 9 needs their audio.

### 5b. Pull B-roll from the channel's catalogue — grep, do not browse
The manifest's own scene clips cover about half the runtime; the rest is text on
the kit background, and that is the approved look (BL51 ran 61 % that way). But a
long text-only stretch whose claim has a matching clip is a hole, so start by
listing them:
```bash
python3 <skill>/scripts/bl_tools.py coverage cut/index.html
```
For every flagged hole grep the catalogue for the claim on screen at that time.
A match with `fit=BL` goes in; no match means keep the kinetic plate — never
force an unrelated clip in to fill time (BL50 round 3: 16 s and 32 s holes on
"Deepfake" and "เช็กก่อนโอน", both of which the catalogue covers).

The channel has 65 catalogued Seedance clips (plus the 19 Kling ones). They live
in Drive `AI Assets/BLACK LIQUIDITY (9:16)`, but you never list that folder:
```bash
C=/Users/gob/Projects/Agents/prototypes/bl-broll-catalog
grep -i "ล็อกถอน\|deadline\|lock" $C/CATALOG.md        # Thai or English, either works
```
Shortlist at most three. Open ONE `$C/sheets/<drive_id>.jpg` (4 frames, ~40 KB;
the file is named by the row's `drive_id`, every one of the 84 rows has one) to
confirm — that is the whole "look", never the video. Then fetch ONE clip by the
`drive_id` column of that same catalogue line:
```bash
curl -sL "https://drive.google.com/uc?export=download&id=<drive_id>" -o media/raw/<purpose>.mp4
```
Normalise it like any plate (step 5). Rules: `fit=BL` first for this channel;
`fit=GEN` only when nothing BL fits; a row with `caution` says exactly how it may
be used (e.g. #48 has readable Thai text baked in — never full-frame). Avatar rows
(`AV`) are non-speaking poses and are fine as cutaways; see trap 8.

### 6. Copy the template and write the cut
The kit background `#bg` is always on and sits under the clips (z-index 0): a
footage plate covers it, a text-only plate shows it. Do not window it with
`show/hide` — the list goes stale the moment you add a plate (BL50 round 4: new
B-roll rendered invisible behind the grid while `npm run check` stayed green).

```bash
cp -r <skill>/template <workdir> && cd <workdir>
```
`index.html` already holds the kit, the fonts and five block generators.
**Copy it from the skill, never from a sibling `prototypes/bl51-*` project** —
a sibling carries another episode's video track, timings and copy, and you will
spend longer deleting them than writing your own.

**The kit is the CSS and the five generator functions. Everything else is
content and you are expected to replace it:** the `<video>` plates, the
`<audio>` element, the composition's `data-duration`, the `#bg` windows, and
every block call below the `THE CUT` banner. Do not rewrite the generators
themselves, and do not invent a sixth block type without a reason.

| generator | use it for |
|---|---|
| `kinetic(top, in, out, lines, ruleW)` | 1-3 lines of headline text |
| `cards(top, in, out, title, items, visibleRows)` | a list that builds and scrolls |
| `check(top, in, out, title, items)` | a numbered or ticked checklist |
| `rules(top, items)` | one big numbered rule at a time |
| `stats(top, in, out, title, items)` | one or two large figures |

Video plates are `<video class="clip" muted playsinline data-start data-duration
data-media-start>`; the audio is one separate `<audio>`. Put `#bg` up only over
the stretches where no plate is underneath.

A worked cut with all five types and real timings lives in the Agents repo at
`prototypes/bl51-first30/index.html`. **It is there to read, not to copy.** On the
second test run a worker found it in its worktree and reused it wholesale, which
produced a perfect BL51 and proved nothing about cutting the next episode. The one
case where reuse is right: the task is a re-render of the *same* episode that
composition was built for — then say so in your report and reuse it. For any
other episode, author from the template.

### 6b. The legal label — every clip, no exceptions

The kit carries `.bl-legal`, a one-line label at y=1790 that is present on every
frame and is never animated, never moved, never faded and never covered:

> เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง

It is already in the template. Do not remove it to make room, do not shorten it,
do not schedule it. A cut that ships without it is not finished.

**Why it is not decoration.** The CEO made it a requirement on every Forex
surface on 2026-09-17, and the statute it answers to aims at the marketing layer
specifically: BOT's 25 Jun 2026 statement puts anyone who "โฆษณา ประกาศ หรือ
ชักชวนประชาชน" to trade FOREX under พ.ร.ก. การกู้ยืมเงินที่เป็นการฉ้อโกงประชาชน
2527, and it writes no carve-out for people who promise no returns.

**What the label cannot do.** It states intent; it does not change conduct. If
the script itself offers an affiliate link in a public post — "เปิดผ่านลิงก์กู
รีเบทเต็ม …" — the label does not cover that, and the CEO's own rule from the
same ruling says those links belong in closed channels only. If the script you
were handed does that, say so in your report rather than cutting around it.

The full-length version belongs in the post caption, where there is room:

> คลิปนี้จัดทำเพื่อให้ความรู้และวิเคราะห์ข้อมูลสาธารณะเท่านั้น ไม่ใช่คำแนะนำการลงทุน
> และไม่มีเจตนาชักชวนให้ลงทุนหรือซื้อขายผลิตภัณฑ์ทางการเงินใด ๆ ผู้จัดทำไม่ได้รับ
> ใบอนุญาตเป็นที่ปรึกษาการลงทุนจาก ก.ล.ต. การลงทุนมีความเสี่ยง ผู้ลงทุนควรศึกษาข้อมูล
> และตรวจสอบใบอนุญาตของผู้ให้บริการก่อนตัดสินใจทุกครั้ง

### 7. Gate the composition
```bash
npm run check          # lint + runtime + layout + motion + contrast
```
Fix every error. This catches overlap, occlusion and WCAG failures you will
not see by reading the code.

### 8. Look at it — the gates do not see everything

First thing to look for: the legal label is on the frame and nothing covers it.
```bash
npx hyperframes snapshot --at 5,12,20,35,50,65,80,95,110,125,135 --no-end -o snapshots
```
Then **open `snapshots/contact-sheet.jpg` and actually look.** On the first
build the gates were green while the text sat across the avatar's sunglasses,
every beat printed its line twice, and the card stack was sliced in half. None
of that is machine-detectable; all of it is obvious in one image.

### 9. Render and verify the FILE, not the preview
```bash
npm run render
python3 <skill>/scripts/bl_tools.py verify <render.mp4> \
  --audio audio-hq.mp3 --duration <track length> \
  --seat A=<ORIGINAL lipsync_a>=0.00 B=<ORIGINAL lipsync_b>=62.71
```
`verify` fails on wrong resolution, wrong fps, missing audio, audio drift over
one frame, and a lipsync part seated more than a frame out. Seating is checked
by audio because frame differencing waves a 9-frame error through — a talking
head barely moves in 9 frames. Pass the ORIGINAL lipsync files here; the
normalised copies were made with `-an` and have no audio to compare.

### 10. Deliver — outside the worktree, before you report
`merge_task` deletes the worktree and `renders/` is gitignored, so an MP4 left
there is gone the moment the task is accepted. On BL51 the worker's render was
lost exactly this way. Before `submit_report`:
```bash
mkdir -p ~/Projects/Agents/output/bl/<episode>
cp renders/<final>.mp4 ~/Projects/Agents/output/bl/<episode>/<episode>-WORKER.mp4
python3 <skill>/scripts/bl_tools.py sheet ~/Projects/Agents/output/bl/<episode>/<episode>-WORKER.mp4 \
  --at 5,20,40,60,80,100,120,135 --out ~/Projects/Agents/output/bl/<episode>/<episode>-WORKER-sheet.jpg
```
Never `git add` anything under `output/`. Name both paths in your report so the
reviewer reads one image and opens one file.

## The constants — measured, not chosen

**Motion.** Every reveal is `expo.out`. Fitted against eight standard curves on
the paid editor's cut: a strikethrough at RMSE 0.0078 and a text wipe at 0.0479,
against 0.1104 for the next-best curve. Text arrives by a left-anchored
`clip-path` wipe and reaches full luminance on its first visible frame — it is
never a fade. Rules, strikes and connectors scale from a left or top origin.
Chips and cards stagger at 110-160 ms.

**Theme** (CEO 2026-09-18): black, red, white; the red is always emissive neon.
`--ink #07080A` · `--red #E0202F` · `--neon #FF2D40` · `--yellow #F4DF14`
(measured off the reference) · `--white #F4F6F7`. A flat red line is off-theme;
anything neon carries a glow. Full catalogue: `BL-KIT.md`.

**Rhythm.** The reference cuts hard only about every 6 s but moves a graphic
roughly every second — 91 animation events against 13 cuts across 85 s. Change
comes from graphics building, not from cutting. Do not cut faster to compensate
for having no footage; build a block instead.

**Captions.** A bottom caption and a kinetic block never carry the same line.
The kinetic text *is* the caption. Use the rail only where no block is up.

**Copy must describe what is actually on screen.** If you are cutting a shorter
edit than the full episode, retitle the blocks to match what fits: a header
reading "10 ตัว" over a list that only has room to reveal two is wrong, even
though the script says ten. Call it "2 ตัวแรก" instead.

## Traps, each one a real defect

1. **Lipsync filenames lie.** Step 2 exists for this. A fine scan around the
   nominal offset is not enough — on BL51 part B scored r=0.025 there and had
   to be found by scanning the whole track.
2. **Thai needs more line-height than Latin.** Upper vowels and tone marks sit
   above the Latin ascender and collide with the line above. The template is
   already set to 1.26-1.38; do not tighten it back.
3. **A scroll pitch must be measured, not assumed.** `cards()` reads the
   rendered card's real height. Hard-coding it sliced cards in half.
4. **Translucent surfaces fail over the avatar.** Rows and cards use a dark
   scrim (`rgba(10,11,13,.78)`), not a white wash — the bright shirt shows
   through anything lighter and the copy loses its ground.
5. **A scrolling stack escapes upward** over the brand bug unless its window
   is clipped.
6. **`el()` returns `firstElementChild`.** A multi-root HTML string silently
   drops everything after the first node; wrap it in one `<div>`.
7. **Don't put copy over a busy plate.** Rule text over a bright laptop screen
   was unreadable despite the outline; the rules now run on a clean ground.
8. **An avatar clip whose mouth moves without matching lipsync is unusable.**
   Viewers catch it instantly. That is the episode's own `S##` avatar plates,
   which are generated mid-speech. The catalogue's `AV` rows are different: the
   avatar walking, arms crossed, drawing in the air — mouth closed. Those are
   proper cutaways. Check the sheet; if the mouth is open in any frame, skip it.
9. **A finished sibling composition is not a starting point.** It carries that
   episode's plates, offsets and copy; every one of them is wrong for yours, and
   the ones that look right (a 62.71 s seat, a "10 ตัว" header) are the most
   dangerous because they pass the gates.

10. **The manifest is not the whole B-roll.** Round 3 of BL50 used the 16 scene
   clips it was given and left 83 s of text on black, including one 32 s stretch,
   while the catalogue held clips for exactly those claims. The folder you are
   given is the editor's material; the channel's library is step 5b, every time.

## What this cannot do

The reference edit mattes its avatar and composites it over a darkened plate.
A lipsync file with a baked background cannot do that, so text goes **below**
the face rather than above a shrunken avatar. Changing that needs a matting
model, which is not part of this skill.

Sound effects are deliberately out of scope until the channel has a licensed,
human-annotated library. An AI placing SFX blind is what made earlier attempts
sound wrong.
