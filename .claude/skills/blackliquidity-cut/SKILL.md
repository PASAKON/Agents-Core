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
| `real/` + `real/REAL_MANIFEST.json` | REAL footage (from EP55 on): the broker's logo, its website and the WikiFX pages, already censored; see step 5a |
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

### 5a. Real footage first — `real/` outranks every plate and every B-roll clip
**CEO, 2026-09-23: "Realfootage สำคัญกว่า B-Roll".** From EP55 on, the project
folder can carry a `real/` subfolder: screen recordings and stills of the named
broker's logo, its real website and the real WikiFX page with the real numbers.
They are produced by `tools/bl_realfootage.py` and are already censored. Signup
buttons, bonus offers, promo codes and complainants' names are pixelated, and
part of the logo is too.

Before placing any scene plate or catalogue clip, read `real/REAL_MANIFEST.json`.
Every entry lists the script tags it proves (`covers: ["CONTEXT-3"]`). Wherever a
tag has real footage, the real clip or still goes on screen for that line.
A generated plate or a B-roll clip may fill only the lines no real footage covers.
A real still of a number (the WikiFX score, a complaint amount) is the strongest
shot the episode has. Give it the full frame long enough to read, and never shrink
it into a corner behind a kinetic text block.

Never re-crop a real clip in a way that pulls a censored region back into view or
cuts a censor box off the element it hides. Never add an uncensored copy from
anywhere else. If a censor looks wrong, stop and report it. Do not fix it in the
cut.

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

### 6a. The brand bug — same logo, same place, every clip

The template carries the channel's real logo as an image, `assets/bl-logo.png`
(698x256, already transparent — do not re-key it, do not recolour it, do not
substitute a CSS text version):

```html
<div class="bug" id="bug">
  <img class="logo" src="assets/bl-logo.png" alt="BLACK LIQUIDITY">
  <div class="rl"></div>
  <div class="dt2">D MMM YY</div>
</div>
```

`right: 150px; top: 310px`, logo `height: 60px`, date stacked underneath,
right-aligned. **These numbers do not change between episodes.** The audience
recognises the mark by where it sits; a bug that drifts reads as a different
channel. If a text block would collide with it, move the text, never the bug.

It used to be `left: 84px; top: 150px` at `height: 118px`. On 2026-09-18 the CEO
sent a screenshot of a real post and the bug was sitting directly under TikTok's
own `เพื่อน | กำลังติดตาม | สำหรับคุณ` nav — the app's text and the channel's mark
overlapping each other. The top right is the one part of the frame the app's
chrome leaves alone above the rail, so that is where it now lives, at half the
height. See 6c for the box it has to stay inside.

**Why 150 and not 240** (measured on the CEO's phone, then approved on a render
of the real cut, 2026-09-19). The 240 margin exists for the like/comment rail,
and the rail only starts at `y≈960`. Up here the sole obstacle is TikTok's
search icon at `x 904-946, y 146-186`. At `right: 150` the mark ends at `x 930`
and still leaves **54px** of visible frame before the crop edge at `x 983` — the
CEO's words were "จดเกือบชิดขอบจอ แต่ห้ามชิดจนเกินไป ให้มีช่องว่างดูลอดผ่านได้".
At `top: 310` it clears the nav by 109px. A first attempt at `top: 350` was
rejected as too low, and 310 is exactly half that move — do not drift back.

**The date is the day the episode was MADE, not the day it is posted.** Posting
lands zero to two days later, and every other record — the Drive folder, the
manifest, the file names — references the made-on date. Take it from the
project's `created_at`, Thai short form with the Buddhist year: `20 พ.ค. 69`.

Source file and its uncropped original are on Drive in `ALL DRAFT/BLACK
LIQUIDITY`, beside the lipsync reference videos.

### 6b. The legal label — every clip, no exceptions

The kit carries `.bl-legal`, a one-line label at y=1430 that is present on every
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

The script you were handed should already obey the compliance rules in the
`blackliquidity-script` skill — no broker the channel earns from, no link, no
account CTA. If it does not, say so in your report instead of cutting around it.

The full-length version belongs in the post caption, where there is room:

> คลิปนี้จัดทำเพื่อให้ความรู้และวิเคราะห์ข้อมูลสาธารณะเท่านั้น ไม่ใช่คำแนะนำการลงทุน
> และไม่มีเจตนาชักชวนให้ลงทุนหรือซื้อขายผลิตภัณฑ์ทางการเงินใด ๆ ผู้จัดทำไม่ได้รับ
> ใบอนุญาตเป็นที่ปรึกษาการลงทุนจาก ก.ล.ต. การลงทุนมีความเสี่ยง ผู้ลงทุนควรศึกษาข้อมูล
> และตรวจสอบใบอนุญาตของผู้ให้บริการก่อนตัดสินใจทุกครั้ง

### 6c. The TikTok safe area — the frame is not what the viewer sees

A 9:16 video on a 19.5:9 phone is scaled to **cover** the screen, not to fit it.
Measured on the CEO's own device from a real post (1188x2576, 2026-09-18):

| what | in this canvas's pixels |
|---|---|
| cropped off each side, never rendered | `x < 97` and `x > 983` |
| app nav (For You / Following / search) | `y 138-186` |
| right rail (avatar, like, comment, share) | `x 873-983`, from `y ~960` down |
| caption + username block | `y 1550-1700` |
| scrub bar | `y ~1789` |

TikTok's published safe area is a 540x960 reference with margins 126 top / 60
left / 120 right / 378 bottom. Doubled onto this canvas and widened at the
bottom to the measured organic figure (the spec's 378 exists to clear an ad
unit's CTA button, which an organic post does not have):

```
--safe-left: 120px    --safe-top: 252px
--safe-right: 240px   (content ends at x=840)
--safe-bottom:        (content ends at y=1500)
```

`.blk` is already bound to those variables, so a block written the normal way is
safe by construction. `.blk.wide` pulls the right margin back to 120 and is only
for a block that **ends above y=900**, before the rail starts.

**Apply `wide` from the block's own top, do not decide it by eye.** The right
margin of 240 is there for the rail; above the rail it only pushes the line
off-centre. On EP52 every block sat in the narrow box, so an upper line was
centred on 480 while the frame's centre is 540 — the CEO saw it immediately as
"เบี้ยวไปทางซ้าย" and asked why the right-hand space was going unused. Put the
rule in the `block()` helper so it cannot be forgotten:

```js
var wide = (top < 900) ? " wide" : "";
```

Measured on EP52: 18 of 40 blocks are above the rail and belong wide; the other
22 sit at y 1090-1320 and must keep 240 or they run under the like/comment
icons. Widening all of them is not the fix — that was the first wrong attempt.

Three real defects this found the day it was written, all of them invisible in
the preview and obvious on the phone:

- `.blk` sat at `left: 62px` — inside the 97px the phone crops, so the first
  characters of every left-aligned line were cut off the screen entirely
- the legal label sat at `y=1790`, which is the scrub bar
- the subtitle layer sat at `y=1600`, inside TikTok's own caption block

Check it, do not eyeball it:

```bash
python3 scripts/bl_tools.py safezone cut/index.html
```

It reads every absolutely-positioned rule in the composition and names each one
that leaves the box. Descendant rules (`.bl-card .badge`) are positioned against
their own parent and are skipped.

### 6b. Thai breaks mid-word, and only `nowrap` stops it

Thai writes without spaces between words. The render's Chrome has no ICU Thai
dictionary, so it breaks a line wherever it runs out of room. On EP54 that split
**สเปรด** across two lines as `...ของส` / `เปรด...`.

Two things that look like the fix and are NOT, both measured on that frame:

- **`lang="th"`** — already set on the template and on every delivered cut. The
  breaking happens in the render's Chrome, not in ours.
- **`word-break: keep-all`** — CSS Text 3 scopes it to the CJK line-break
  classes (NU / AL / AI / ID). Thai is class SA and is untouched. The identical
  break rendered with and without it. A ZWSP does not help either: it *adds* a
  break opportunity without removing the others.

What works is `white-space: nowrap` on the run itself. The template carries a
`.nb` utility for this — wrap any Thai word that must never split:

```js
{ c: "bl-md", h: '<span class="y">Rebate</span> คือส่วนหนึ่งของ<span class="nb">สเปรด</span>หรือค่าคอม' }
```

**No gate can see this defect.** `npm run check`, `hyperframes inspect`,
`bl_tools.py safezone` and the contrast audit all passed the EP54 frame before
and after the fix — the frame was correct in every respect except which
characters sat on which line. The only check that works is step 8: read the Thai
in the rendered frame **as words**, not as pixels, and read it off the encoded
MP4 (`ffmpeg -ss <t> -frames:v 1`), not off a DOM snapshot.

### 7. Gate the composition
```bash
npm run check                                        # lint + runtime + layout + motion + contrast
python3 scripts/bl_tools.py safezone cut/index.html  # nothing under the app's own UI
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

`verify` also measures **loudness** and fails outside **-16..-12 LUFS**. TikTok
and YouTube normalise toward -14: a quieter file gets turned UP by the platform,
which lifts its noise floor, and in a feed it just sounds weak beside everything
else. EP52 shipped at -20.2 with every other gate green because nothing measured
it — while the hired TRADER UNCUT edit we criticised on craft hit -14.0 exactly.
Fix it on the master, never by touching the mix:

```bash
ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy out.mp4
```
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

## Field notes
- 2026-09-23 [MISSING] §5a — CEO ruling: real footage (broker logo, real site, real WikiFX page with real numbers, partly censored) outranks B-roll; the runner is task-67f82679 (tools/bl_realfootage.py). Written into the rule body directly because it is a CEO ruling, not an n=1 sighting · evidence: CEO message 2026-09-23 "Realfootage สำคัญกว่า B-Roll", commit 6f4a7658 · status: promoted
