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
`bl_tools.py sheet` exists. For the avatar-composite constants specifically,
read `reference/avatar-composite-reference.jpg` — see §6d.

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
C=/Users/gob/MoonieXHQ/Agents/Core/prototypes/bl-broll-catalog
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
`index.html` already holds the kit, the fonts, five block generators and one
caption generator.
**Copy it from the skill, never from a sibling `prototypes/bl51-*` project** —
a sibling carries another episode's video track, timings and copy, and you will
spend longer deleting them than writing your own.

**The kit is the CSS, the five block generators and the one caption generator.
Everything else is content and you are expected to replace it:** the
`<video>` plates, the `<audio>` element, the composition's `data-duration`,
the `#bg` windows, and every block/caption call below the `THE CUT` banner.
Do not rewrite the generators themselves, do not invent a sixth block type
without a reason, and never give `caption()` a mode/kind parameter or an
inline style override (§6f — that is exactly how EP57's three-caption-look
bug happened).

| generator | use it for |
|---|---|
| `kinetic(top, in, out, lines, ruleW)` | 1-3 lines of headline text |
| `cards(top, in, out, title, items, visibleRows)` | a list that builds and scrolls |
| `check(top, in, out, title, items)` | a numbered or ticked checklist |
| `rules(top, items)` | one big numbered rule at a time |
| `stats(top, in, out, title, items)` | one or two large figures |
| `caption(at, out, text)` | the spoken-line caption band — same look in every mode, §6f |

Video plates are `<video class="clip" muted playsinline data-start data-duration
data-media-start>`; the audio is one separate `<audio>`. Put `#bg` up only over
the stretches where no plate is underneath. Every plate's `data-duration` (and
every block/caption's `out` argument) must reach to the START of the next
plate, not stop at its own line's end — see §6g.

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

### 6e. Brand names and image credits on screen (CEO rulings 2026-09-23)

**A brand appears on screen in its real spelling, even when the voice reads a
Thai transliteration.** The script spells `วิกิเอฟเอ็กซ์` so the TTS pronounces
it right, but the caption shows `WikiFX`. The captions otherwise still follow
the audio word for word (the BL carve-out in `mooniex-video-editor`); a
brand's spelling is the one exception. Apply
`brand-display.yaml` (spoken form → display form) to every caption and text
block. When a script introduces a brand that has no row yet, add the row
rather than hand-fixing one caption.

**A picture taken from someone else carries a credit in its own top-left
corner**, small: `ขอบคุณภาพจาก <source>` (e.g. `ขอบคุณภาพจาก WikiFX`). The credit sits
on the image plate, not on the frame. That keeps it clear of the brand bug,
which lives top-right (§6a), and it stays attached to the image when the
image zooms. Use the same dark backing as `.bl-legal`, so it reads on a light
image. Screenshots we captured ourselves (`real/`) need no credit. A
publisher's own artwork (a WikiFX review card, a news graphic) always does.

### 6d. Avatar composite — matte the avatar, lower it onto a plate

The reference edit (the CEO's ฿1300 editor cut, `reference/avatar-composite-reference.jpg`,
measured 2026-09-23, task-4bce29e5) doesn't stay full-frame the whole time. It
switches, shot by shot, between two modes:

| mode | when | measured (n, mean ± stdev) |
|---|---|---|
| **full-frame avatar** | pure talking-head beats, no evidence to show | height **88.7%** of the 1920 frame, top at **11.3%**, x-center **52.4%** (n=2) |
| **composited avatar** | a website screenshot, chart, or other evidence has to stay on screen while the avatar keeps talking | height **55.8% ± 3.1** (min 52.9 max 64.0), top at **44.2% ± 3.1** (y≈850px), x-center **≈37%** (left of centre), **always cut off by the frame bottom** — chest-up, never full body (n=10) |

#### How the avatar moves — measured frame by frame (2026-09-23, CEO-directed)

Tracked on every frame of the reference (TikTok `@black_liquidity/video/7612158317695159573`,
85 s) with a multi-scale head matcher (beanie + sunglasses, NCC 0.77-0.91 on every
frame). Strips: `reference/avatar-shrink-motion.jpg` (four switches, every 2nd
frame) and `reference/hook-avatar-drop.jpg`.

**Going INTO composite = an animated shrink, not a cut** (3 of 4 switches):

| switch | plate swaps behind the full avatar | shrink runs | frames | scale | head centre y | head centre x | best easing (RMSE) |
|---|---|---|---|---|---|---|---|
| 9 s | 8.93-9.13 | 9.33 → 10.23 | 27 | 1.04 → 0.69 | 608 → 1056 px | 564 → 349 px | sine.out 0.035 · power1.out 0.040 |
| 19 s | 18.87-18.93 | 19.13 → 19.83 | 21 | 1.11 → 0.68 | 581 → 1040 px | 528 → 318 px | sine.out 0.067 · linear 0.088 |
| 51 s | 50.87-51.13 | 51.27 → 52.17 | 27 | 1.12 → 0.67 | 572 → 1051 px | 493 → 327 px | sine.out 0.032 · power1.out 0.062 |
| 64.5 s | — | hard cut | 0 | 1.07 → 0.68 | 603 → 1085 px | 539 → 321 px | — |

Build it this way:
1. **The plate changes first, behind the still full-size avatar** (a quick
   dissolve, ~0.2 s). The headline or question for that section lands too
   ("ค่า SPREAD สูงเพราะ?" at 9.07 s). The viewer sees that something new is
   behind the presenter.
2. **~0.2 s later the avatar shrinks out of the way.** Tween scale + position
   together over **0.7-0.9 s** with **`sine.out`** (`power1.out` is the close second).
   It ends at **~62% of its full size**, moves down by about a quarter of the
   frame, and moves left to a head centre at x≈30% (≈320-350 px). The first
   frames move fastest: 32-36 px per frame, with a visible motion blur.
3. **Coming back to full frame is a hard cut** (46.2 s: 0 in-between frames).
   The return lands on a new spoken sentence in the red studio plate.
4. A hard cut *into* composite also happens once (64.5 s). It sits where a new
   section starts ("ใครฟังมาถึงตรงนี้", the CTA block). Use the animated shrink
   by default, and a hard cut when the script turns to a new section.

**The hook opening is a third move, a slide rather than a shrink.** From
0.23 → 1.43 s the avatar slides straight down at the same size: scale
1.00 → 1.00, x unchanged, head centre y 839 → 1137 px (+298 px ≈ 15.5% of the
frame). The curve is **`power1.out`** (RMSE 0.056, sine.out 0.072), with a peak of
20 px/frame in the first frames. The space it opens above the head is where the
hook text sits, and the brand logo pops into it at 0.60 s, on the frame the
voice says "XM". It then holds until the hard cut to the first evidence plate
at 1.87 s.

- [SUPERSEDED 2026-09-23] "Composite mode is a **hard cut**, not an animated
  shrink … don't tween scale/position." Beaten by frame-by-frame tracking of
  the reference (3 of 4 entries are 21-27-frame `sine.out` shrinks). The CEO
  also saw it by eye: "การเอาลง เอาลงแบบ smooth ด้วย มี Animation". The
  original n=10 measurement sampled the settled shots, not the transitions.

#### Focus devices on the evidence plate — measured

The plate is never just placed behind the avatar. Every screenshot is worked
so that the viewer's eye lands on one spot at the moment the voice names it:

- **Scroll and zoom the page so the focus row sits in the free band above the
  head**, at **25-40% of the frame height**. Across the clip the yellow focus marks
  centre at y 25-33% and x 45-60%. The centre of the space the avatar left
  open, not the centre of the whole frame. The XM page (2.0-4.4 s) is panned
  and pushed in continuously, not held (zoom amount read by eye, not measured).
- **Spotlight circle.** The page dims to grey except a bright circle around
  the one value being talked about ("สเปรดต่ำสุด GOLD 3", 4.40-5.15 s, circle
  centre ≈ x 25% / y 28%, radius ≈ 20% of the width), with the recorded mouse
  cursor resting on the number. See `reference/focus-spotlight-circle.jpg`.
- **Yellow highlighter, left → right, on the spoken word.** Table rows get a
  yellow bar that sweeps left to right in ~0.9 s (the centroid runs x 40% → 55-60%).
  Measured onset against the word: SPREAD 9.07 vs spoken 9.22 · REBATE chip
  34.47 vs 34.40 · Exness row 57.20 vs 57.18 · logo pop 0.60 vs 0.60. **Land the
  highlight on the word, ±0.15 s, never late.** The only yellow is the kit's
  `--yellow` #F4DF14.
- [SUPERSEDED 2026-09-25] "In composite mode the spoken caption is a small
  dark chip just above the head (≈37-40% of the height), directly under the
  focus spot. In full-frame mode it sits at chest height. The chip reads as a
  label on the evidence, not as a subtitle." Beaten by the CEO rejecting the
  episode built on this rule: "sub title style ที่ขึ้น มันไม่ใช่แบบเดียวกับที่
  EP ก่อนหน้าทำไว้ … Skill issue แน่นอน" — EP57's per-mode chip produced three
  different caption looks in one episode (a 38px chip whose height changed
  per line and collided with the page text and the brand bug, a flat
  full-width strip, and plain outlined text with no backing on plain avatar
  lines). There is now exactly ONE caption look in every mode — see §6f and
  the `caption(at, out, text)` generator in `template/index.html`.

**Why the switch happens (script → mode), from the transcript:** the avatar
is full frame for **verdict and emotion** lines ("ผมบอกความจริงที่ไม่มีใครบอกมึง",
"มึงเป็นคนกด มึงเป็นคนเสี่ยง แต่คนอื่นกินเงินมึงเงียบ", the closing "เงินทุกล็อต…
ควรเป็นของมึง"). Those blocks run 4-5 s each and total ~24 s of 85 (28%), all on
the same red studio plate. It is composited for every line that names
something that can be **shown**: a website, a number, a table row, a wallet
balance, a tier ladder (~61 s, 72%). The rhythm is show (composite) → verdict
(full frame) → show again. Tag each script line as show or verdict before
cutting, and the modes follow from the tags.

**Where the text goes:** always above the avatar's head (above y≈850px on the
1920 canvas), never overlapping it — the composite exists precisely to free
that space.

**HARD — the avatar must never cover the evidence element on a real-footage
plate.** A score, an amount, a licence line — whatever `real/REAL_MANIFEST.json`
says that still proves — has to stay fully visible once the avatar is
composited on top of it. On the first cut of this demo the avatar's head sat
directly on the "1" of a WikiFX **1.69/10** score, the single most important
number in the shot; the CTO caught it by reading 6 frames and rejected the cut
on sight (task-4bce29e5, 2026-09-23 17:40 review). Why hard: the composite's
whole purpose is to keep evidence AND the avatar both on screen — if it hides
the evidence instead, the composite is actively worse than just cutting to the
still full-frame with no avatar. **Fix by moving the plate, not the avatar** —
the evidence box and the avatar's box are usually each wider than half the
frame, so sliding the avatar left/right rarely clears a wide box; shifting the
still vertically (crop/pad it so the evidence sits above y≈800, with margin
above the avatar's y≈845 top) does. Check it by eye before it ever reaches a
render — read the still against the avatar's fixed box (bottom-anchored,
56% of the 1920 height, ≈24-37% of the width from the left edge) — there is no
automated check for this yet; `bl_tools.py safezone` only knows about kinetic
text blocks, not arbitrary evidence coordinates inside a still. Verified clear
in `reference/avatar-composite-evidence-clear.jpg` (v2, 2026-09-23): shifting
the WikiFX still up 380px moved the score box to y 395-770, well above the
avatar's y=845 top.

**The fix itself can re-create the same bug one level up.** After shifting the
still, a kinetic caption placed at top=560 (in the space the shift freed)
landed squarely on the now-relocated score box — same defect, moved, not
fixed. There is no scrap of the frame that is simultaneously clear of a wide
evidence box (usually the top half) AND the avatar (the bottom 56%) AND still
has room for two lines of caption text; on this still there wasn't one, so the
right call was to drop the caption on that segment entirely rather than force
one in. Check any new text block you add against the evidence box too, not
just against the avatar.

**Plate darkening — measured, not assumed, and it's NOT uniform:**

| plate type | measured mean luminance (0-255) | treatment |
|---|---|---|
| real-footage screenshot (bright/white UI) | **227-237** — essentially undarkened | **none.** Rule 5a already says real footage outranks B-roll and must stay legible; darkening it would fight that rule. |
| B-roll / chart / graphic plate | **17-42** | naturally dark source material in the reference, not necessarily graded darker on top — use `.plate-darkened` (brightness 0.4, slight blur) only on this kind of plate |

Do not apply one rule to both. Two of the ten composite frames measured were
real-footage screenshots at 227+ luminance; treating them like the dark ones
would directly violate rule 5a.

**The matte edge:** feathered, not hard — a thin (~8px) ring right at the
cutout boundary measured **~15-20% darker** than the plate immediately behind
it in every sample (ratio 0.48-1.01, mostly 0.83-0.92), consistent with a soft
contact-shadow/feather blend, not a razor cutout and not a bright glow.

#### The matte command

```bash
# needs torch - this ONE bl_tools.py command isn't numpy+Pillow-only
/Users/gob/.claude/skills/reel-editor-th/.venv/bin/python3 <skill>/scripts/bl_tools.py matte \
  lipsync_part_a.mp4 --out media/matte/lip_a-matte.webm --preview check.jpg
```

Picked **RVM (Robust Video Matting, mobilenetv3, MPS)** over rembg(u2net) and
an attempted mediapipe selfie-segmenter, compared 2026-09-23 on EP55's real
`lipsync_part_a/b/c.mp4` (beanie, sunglasses, moving hands, dark/red-lit
background — the hard case):

| | edge quality | speed |
|---|---|---|
| **RVM mobilenetv3** | clean on every scene incl. the red-lit set; ~1% of frame pixels soft/fractional | 481.8s for 350 frames (25fps, 14s clip) — 1.4s/frame steady state |
| rembg (u2net) | **leaked badly on the red-lit set specifically** — 15-17× more soft-alpha pixels than RVM on the exact same frames (300k+ vs 17-20k out of 2.07M), a visible diagonal semi-transparent tear across the jacket. Fine on the darker b/c scenes. | slower too (1.1s/frame vs RVM's ~0.65s in a shorter test) |
| mediapipe selfie-segmenter | not evaluated — the bundled Tasks API in this mediapipe version (1.0.1) threw on `ImageSegmenterOptions`/`segment()` before producing a mask, and RVM already won decisively | — |

Model: `rvm_mobilenetv3.pth`, **14.5 MB**, lives at
`~/.cache/torch/hub/checkpoints/` (the default torch.hub cache — no
`TORCH_HOME` override needed). No paid API was needed or evaluated.

#### Traps hit building this — all measured, not guessed

- **A WebM with `-pix_fmt yuva420p` written to `ffmpeg`'s DEFAULT decoder on
  read comes back fully opaque (alpha≡255).** `ffmpeg -i x.webm -pix_fmt rgba`
  silently drops the alpha side-stream. Force it: `ffmpeg -c:v libvpx-vp9 -i
  x.webm ...`. `bl_tools.py matte`'s own output is correct — this only bites
  anyone reading it back with a bare `ffmpeg -i`.
- **Without `-disposition:v default` on the muxer, a real `<video>` element
  never leaves `readyState 0`.** No error, no console warning — it just spins
  forever. `bl_tools.py matte` now sets this flag itself; if you ever hand-roll
  the ffmpeg command, don't skip it.
- **This skill's own sandboxed Chrome (claude-in-chrome) cannot play ANY WebM
  at all** — confirmed against a known-good public test file, not just the
  matte output. Don't debug alpha-webm problems by loading them in that
  browser; it will look broken even when the file is fine. The REAL check is
  `hyperframes render` (its own headless Chrome), which played this skill's
  matte output correctly end to end — verified live 2026-09-23 building
  `DEMO-avatar-composite.mp4`.
- **A full-frame real-footage plate breaks the standing legal label's and
  brand-bug date's contrast, and a text-shadow does NOT fix it.** Both were
  tuned for the kit's normal dark/red backgrounds; a bright white real-footage
  plate under them (new since rule 5a) drops `.bl-legal` to 1.1:1 against the
  WCAG-required 3:1. First attempt — give `.bl-legal` the kit's own `--outline`
  4-way stroke, same as `.bug .dt2` already had — **measured to still fail**,
  same 1.6-2.1:1 numbers, because `hyperframes check`'s contrast pass reads the
  text's own `color` against the background and does not credit a shadow.
  What actually works, verified (`check` went from 9 errors to 9/9 pass): a
  real opaque backing, `background: rgba(7,8,10,.72)` behind the text — the
  same technique `.bl-card`/`.bl-row` already use. Both `.bl-legal` and
  `.bug .dt2` now carry it. A kinetic caption over a bright plate needs the
  same treatment on its own block — see the field note below.

Sound effects are deliberately out of scope until the channel has a licensed,
human-annotated library. An AI placing SFX blind is what made earlier attempts
sound wrong.

### 6f. One caption style, every mode (CEO ruling 2026-09-25)

**The template's `caption(at, out, text)` generator is the only way any
episode writes a spoken-line caption, full stop.** It takes no mode/kind
argument and produces exactly one look every time — EP55's approved band
(`.cap`: `rgba(5,6,8,.90)` background, `padding: 20px 30px`, `border-radius:
18px`, `48px`/weight 600 text, max two lines, sitting in the standing
`.caplayer` at `top: 1300px`, the same safe-box width every other overlay
uses). Call it for a full-frame avatar line, a composited line, and a line
over a real-footage screenshot alike — the caption never changes shape
because of what's behind it.

This replaces the §6d rule above (now [SUPERSEDED]) and the per-episode
`addCap(t0, t1, text, kind, y)` pattern some episodes hand-rolled (EP57's
`kind` took `"chip-ff"` / `"chip-comp"` / `"rail"`, each its own inline style
— that is precisely the bug). **Do not reintroduce a kind/mode parameter or
an inline `style=` override on a `.cap` element** — if a caption needs to
move because it collides with something, move the *evidence plate* instead
(§6d's own fix for the score-box collision is the pattern: shift the still,
never restyle the caption). `tools/bl_checker.py`'s one-caption-style gate
(`--composition <index.html>`) fails a render that violates this — it reads
every `addCap()`/`caption()` call in the composed script and counts distinct
style signatures; more than one is a hard fail, same as an empty frame.

Reference frame: `reference/caption-ep55.jpg` — a full-res still rendered
from the template with a sample Thai caption over a white real-footage
screenshot (EP55's own final render is on Drive and not reachable from a
worker session, so this is the template's `caption()` output on a
representative background, not a frame pulled from the delivered EP55 file).

### 6g. Plates hold until the next plate

**A plate's end is the next plate's start.** Nothing on screen — a video
clip, a still, a kinetic block, the avatar composite — may end at its own
spoken line's `t1`; it holds until whatever comes next actually begins.
Promoted from the 2026-09-24 field note below: EP57's first render went
empty (only the dark kit background, the bug and the legal label — no
plate, no avatar, no text) for 0.25-1.0 s at almost every line boundary, 35
stretches totalling 16.8 s (11% of the episode), because every plate/block
stopped exactly at the end of its own line and the TTS pause before the next
line was left uncovered. The reference edit the CEO paid for never goes
empty — a shot is always still or already changing to the next one.

Build every composition's timing this way: compute each entry's *effective*
end as `min(next entry's t0, total duration)`, not its own line's `t1`, and
drive every `data-duration` / block `out` argument from that extended value.
`prototypes/bl57-cut/build_cut.py`'s `EXT_END` map (origin/agent/video_editor
-task-501f1d89, read-only reference, do not copy its caption code) is a
worked example of this exact computation. `tools/bl_checker.py`'s empty-frame
gate (§ below) now checks for this mechanically at 30fps, including a
single-frame dip — it is not a substitute for building the timing right in
the first place, but it will catch it if you don't.

## Field notes
- 2026-09-23 [MISSING] §5a — CEO ruling: real footage (broker logo, real site, real WikiFX page with real numbers, partly censored) outranks B-roll; the runner is task-67f82679 (tools/bl_realfootage.py). Written into the rule body directly because it is a CEO ruling, not an n=1 sighting · evidence: CEO message 2026-09-23 "Realfootage สำคัญกว่า B-Roll", commit 6f4a7658 · status: promoted
- 2026-09-23 [MISSING] §5a — real footage is usually a LIGHT web page, and the kit's captions were tuned for dark AI plates. On EP55 a standing top/bottom vignette passed `npm run check` contrast, but captions still sat on the page's own text: a tab row, an article paragraph, a heading. Unreadable text-over-text; the same defect the CEO rejected a clip for that day. On a real-page plate put the caption on a solid, near-opaque band, or place the still so the caption lands on empty page space · evidence: task-52c669bb frames t=34.5/52.5/57.5/63 s · status: pending
- 2026-09-23 [WRONG] §5a/§6d — confirms the pending note above on a second, independent task, and extends it two ways. First: it isn't only kinetic captions that lose contrast over a bright real-footage plate — the STANDING legal label and brand-bug date do too (`.bl-legal` measured 1.1:1, need 3:1). Second, and the real trap: a text-shadow does NOT fix this, not even the kit's own `--outline` 4-way stroke — tried it, `hyperframes check` still failed at the same 1.6-2.1:1 numbers, because the checker reads the text's flat `color` against the background and gives a shadow no credit. Only an actual opaque `background` band (same trick `.bl-card`/`.bl-row` already use) passed — verified 9 errors → 9/9 · evidence: task-4bce29e5, `hyperframes check` on a white-plate fixture, before (9 errors incl. `.bl-legal`/`.bug .dt2` at t=0.833-2.833s) and after (9/9 pass) · status: promoted
- 2026-09-23 [MISSING] §6d — n=1, flag for confirmation: `bl_tools.py matte` on RVM mobilenetv3+MPS runs at ~1.4s/frame steady state (~8 min for a 14s/25fps lipsync part), so mattes all 3 parts of one episode before render eats 25-40 min. Budget for it; don't start it as the last step before a deadline · evidence: task-4bce29e5, full `lipsync_part_a_0s-14s.mp4` matte run, 481.8s/350 frames · status: pending
- 2026-09-23 [MISSING] §6d — CTO caught the avatar covering a WikiFX 1.69/10 score on the first cut of the demo by reading 6 frames; the HARD evidence-overlap rule above and `reference/avatar-composite-evidence-clear.jpg` came from fixing it. Fixing it by shifting the still up then re-introduced the exact same bug one level up — a kinetic caption placed in the newly-freed space landed on the relocated score box · evidence: task-4bce29e5, CTO-FEEDBACK.md 17:40 review; fix verified `hyperframes check` 10/10 contrast, DEMO-avatar-composite-v2.mp4 (Drive, EP55 folder) read at 9 timestamps full-res · status: promoted
- 2026-09-23 [COSTLY] no owner — `hyperframes render` stalled twice at the identical frame (353/466) with the exact same composition, both times with the Mac down to ~110-150 MB free RAM (`top -l 1`, PhysMem). Not a composition bug — a clean retry on the third attempt, unchanged, completed in 5m29s (vs ~2m30s when memory is free). If a render stalls ("no frame progress for 60000ms"), check system memory before touching the composition · evidence: task-4bce29e5, render_v2.log timestamps 17:47-17:57, renderJobIds be0a6e61/ca6082c3 · status: pending
- 2026-09-23 [WRONG] §6d — "composite mode is a hard cut, don't tween scale/position" was false. Frame-by-frame head tracking of the reference shows 3 of 4 entries into composite are 21-27-frame sine.out shrinks after the plate swaps behind the full avatar; only exits (and one section-change entry) are hard cuts. Rule flipped to the measured motion; the old line is kept [SUPERSEDED] in §6d · evidence: CEO ruling 2026-09-23 ("เอาลงแบบ smooth ด้วย มี Animation") + reference/avatar-shrink-motion.jpg, commit 1eb280fa · status: promoted
- 2026-09-23 [MISSING] §6e — no rule for a brand's on-screen spelling (captions showed the TTS transliteration) or for crediting a third-party image; both set by the CEO for EP57 (WikiFX XXLMARKETS review card) · evidence: CEO ruling 2026-09-23 · status: promoted
- 2026-09-24 [MISSING] §9 verify — no gate catches EMPTY frames between shots. EP57's first render went bare (only the dark plate, bug and legal label) for 0.25-1.0 s at almost every line boundary: 35 stretches, 16.8 s = 11 % of the episode, because plates ended with their line and the TTS pauses between lines were left uncovered. The reference never goes through empty. Hold each plate until the next begins. Check it mechanically: fps=4 gray frames, mask the bug (y 12-24 %, x > 55 %) and the legal band (y 66-74 %), flag std < 12; the target is 0 stretches after 0.25 s. It belongs in `bl_tools.py verify` as a gate · evidence: task-501f1d89 render #4, the CTO's detector, frames 31 s / 80 s · status: promoted (§6g rule text; gate moved from `bl_tools.py verify` into `tools/bl_checker.py`'s `detect_empty_frames`, task-1678d38e)
- 2026-09-24 [MISSING] §9 render — on this 8 GB Mac, with several Claude sessions live, a HyperFrames render of EP57 died at ~frame 400 five times, whatever the window length and even when it started at 38 % memory_pressure: memory grows during a render. The editor's `vm_stat` free ≥ 500 MB gate never clears (macOS keeps free pages low). Gate on `memory_pressure` ≥ 25 %, render windows of ≤ 9 s cut at line boundaries with a fresh process each, concat with -c copy, and mux the audio once at the end · evidence: task-501f1d89 renders #1-#5 · status: pending
- 2026-09-25 [MISSING] §budget — the EP57 cut worker (task-501f1d89, Sonnet 5) ran 1,418 turns while its context grew 316k → 844k tokens/turn (max 913k); 873M cache-read tokens = $175 of a ≈$189 API-equivalent bill, machine time is cents (render 15 min on the Mac, ≈€0.05 on hourly Hetzner). Split a cut into plan → render → verify tasks or compact near 200k; never trust cost-guardian's per-session $ (ignores cache reads, 5.6× under) · evidence: transcript 5b6517b0, mooniex:research/2026-09-25-cost-per-bl-episode-cut-ep57.md · status: pending
- 2026-09-25 [MISSING] §gate/§render — why EP57 took 4 h (measured): first cut submitted at 1 h 46; the other 2 h 14 were rework. Chain: the Mac (8 GB, six Claude sessions) killed the headless browser near frame ~400 → 13 full-render launches, ~5 deaths → the render was re-engineered mid-task into 24 windows (12 launches) → two new bugs (per-window frame rounding = 300 ms lipsync drift; GSAP negative-position tween = 3.1 s empty window). The review defects (35 empty stretches = 11 % of the episode; clipped credit) had no pre-submit detector — the CTO wrote one at review time. 122 poll-only turns (ReadNotifications/Monitor) at ~740k context = 90M cache-read tokens ≈ $18 spent waiting. Thinking was not the cost: median 243 output tokens/turn. Fix candidates: render on a box with free RAM (Contabo/Hetzner), a `bl_gate` detector required before submit_report, one synchronous render call instead of polling, split plan → render → verify into fresh tasks · evidence: transcript 5b6517b0 (task-501f1d89), worktree CTO-FEEDBACK.md, mooniex:research/2026-09-25-cost-per-bl-episode-cut-ep57.md · status: pending
- 2026-09-25 [WRONG] §budget — the note above quotes 1,418 turns / 873M cache read; that is a raw line sum. Claude Code writes each assistant message.id on ~2 lines; deduped the EP57 cut worker is **760 turns, 467.7M tokens (466M cache read), $99.79**, not $189. Count with `jev_edit_lib.sum_transcript_usage` · evidence: session 5b6517b0 (1,418 lines / 760 ids) · status: pending
- 2026-09-25 [WRONG] §budget — the A/B/C numbers first reported (arm A $7.54/161 turns, B $3.59/83, C $1.10/10) came from `tools/bl_scripter.py::usage_from_transcript`, which summed raw transcript lines; deduplicated by message.id they are A $3.73/82, B $1.66/46 (Scripter $0.26/3 + Editor $1.40/43), C $0.26/3 — ranking unchanged, checker verdicts unchanged. Tool fixed (dedup; returns `lines` beside `turns`), docs corrected · evidence: docs/ops/bl-ab-2026-09-25/REPORT.md §Correction; transcripts task-9ba58d91 / task-4ccc2495 (Contabo), 440ba051 (Mac), every repeat byte-identical · status: pending
- 2026-09-25 [MISSING] §gate — the 4 fps std<12 empty-frame check misses a ONE-frame black flash: BL-EP57-final.mp4 has an empty dark frame at 76.37 s between two identical WikiFX plates (whole-frame mean 13 vs 147 either side). Also check per-frame mean drop at 30 fps; and the final still shows 7 empty 0.25-0.75 s moments (0:00, 0:31, 0:55, 1:02, 1:45, 1:48, 2:00) the worker had called "fade frames" · evidence: task-501f1d89 final 03:49 +07 09-24 · status: promoted (`tools/bl_checker.py::detect_empty_frames` now samples at 30fps with a whole-frame-mean single-frame-dip check on top of std<12, task-1678d38e)
- 2026-09-25 [WRONG] §6d composite caption — "in composite mode the spoken caption is a small dark chip just above the head (≈37-40 % of the height)" came from the ฿1300 reference, not from this channel. EP57's worker followed it: 38 px chips whose height changes every line, up where they collide with the page text and the BLACK bug (t=13 s, 78 s), while full-frame lines got plain outlined text with no chip, and screenshot lines got a flat full-width strip: three caption looks in one episode. CEO 2026-09-25: "sub title style ที่ขึ้น มันไม่ใช่แบบเดียวกับที่ EP ก่อนหน้าทำไว้ … Skill issue แน่นอน" · evidence: BL-EP57-final.mp4 t=4.2/13/78 s vs EP55-NoLicense-FINAL-v2.mp4 t=12 s; rule change proposed to the CEO · status: promoted (§6d marked [SUPERSEDED], §6f written, task-1678d38e)
- 2026-09-25 [MISSING] template — the caption the CEO approved on EP55 (`.cap.band`: rgba(5,6,8,.90), padding 20px 30px, radius 18px, 48 px/600, two lines, fixed at chest height top 1300 px, safe-box width) was a CTO-review fix written only into `prototypes/bl55-cut/index.html:291`. It never went back into `template/index.html`, whose `.cap` (line 306) is plain outlined text, so the next worker started without it and re-invented a backing per line kind · evidence: the two files · status: promoted (`.cap` in `template/index.html` now IS the EP55 band, plus a `caption()` generator so no worker has to hand-roll one again, task-1678d38e)
- 2026-09-25 [COSTLY] CTO review — the 09-24 review note about a watermark left uncovered at 98 s was read as a rule for EVERY screenshot caption: the worker made the whole "rail" kind full-bleed (`left:0;right:0`), which is the flat strip the CEO saw. A review fix must say its scope (this one line) · evidence: task-501f1d89 index.html addCap() comment "CTO review 2026-09-24" · status: pending
