---
name: google-flow-ops
description: >-
  Operating rules for driving Google Flow (labs.google / flow.google.com, Veo
  3.1) — the measured click path, the credit costs, the traps that silently
  waste a generation, and what the product simply does not have. Trigger on
  /google-flow-ops and proactively whenever a C-level is about to delegate or
  drive browser work on Google Flow, or the request mentions "Google Flow",
  "Veo", "Ingredients to Video", "Scenebuilder", "Flow credits", or generating
  video on the CEO's Google AI subscription. Supplements — does not replace —
  `browser-operator` (generic browser cost discipline) and
  `dev-spawn-protocol`. Do NOT fire for Higgsfield/Seedance work
  (`higgsfield-unlimited-gen` owns that) or for fal.ai / Grok / Kling.
---

# Google Flow — operating rules

**v1, seeded 2026-09-07 from task-796a93f6 (one full recon walk, 40 credits).**
Everything below was measured on the CEO's own account, not read off a blog.
Where a number is unmeasured it says so.

This file is the Flow equivalent of `higgsfield-unlimited-gen`. It exists so the
second worker does not have to rediscover what the first one paid to learn.

## ⛔ Mute the page before you do anything else

`browser-operator` carries the rule and the paste-once snippet. Short version:
**a worker has no ears, so audio is never information — it is only noise in the
room where the CEO is working.** Silence every Flow page as the first action
after it loads, not at the moment you press play, and re-run the snippet after
every navigation. Reviewing a clip by ear is a human's job; capture the file and
say so.

## ⛔ A policy refusal comes from the DIALOGUE, not from your reference chips (measured 2026-09-19)

Three shots were refused **eight times between them**, always with the same card
that explains nothing:

```
ล้มเหลว
การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```

**Every refusal is refunded**, so finding the cause costs time and nothing else.
That is what makes bisection the right tool and guessing the wrong one.

### What was measured

| test | result |
|---|---|
| baseline, unchanged | refused |
| **all spoken dialogue removed**, both chips still attached, everything else byte-identical | **passed** |
| dialogue put back, nothing else changed | refused again, immediately |
| dialogue reworded, chips and everything else held identical | **passed, all three shots** |

So: **the chips were never the trigger.** Two reference chips stayed attached
right through the passing runs. Anyone reaching for "detach the plate and write
it as prose" — the fix that worked on Higgsfield for a different failure — is
solving the wrong problem here and losing face consistency for nothing.

### The two phrasings that actually tripped it

1. **A dependent named alongside a demand or a warning.**
   `อย่าเพิ่งไปที่ร้านเลยครับ ลูกผมอยู่ที่นั่น` — "don't go to the shop, my son
   is there." Nobody is threatened on screen and no child appears; the sentence
   alone is enough.
2. **Money framed as an absolute prohibition.**
   `อันนี้ค่ายาแม่ ห้ามแตะเด็ดขาด` — "this is mother's medicine money, never
   touch it." The absolute is what reads badly, not the money and not the mother.

### The fix: same beat, positive surface

Say the same thing forward instead of backward. This is the CEO's instruction
and it produced better dialogue, not weaker:

| refused | passed |
|---|---|
| don't come to the shop, my son is there | **I'll bring it to you myself tomorrow** |
| still 300 short for mother's medicine | **another 300 and this month's medicine is covered** |
| this is medicine money, never touch it | **this is set aside for this month's medicine** |
| I don't like having to chase people | I don't like bothering anyone |
| the interest doesn't wait for anyone | time doesn't wait for anyone |
| I know there's a sick woman upstairs … the doctor's bill next month | **I heard your mother isn't well … I worry on your behalf** |

That last pair is the important one. A villain who says he is *worried about
you* while naming your weak point is more frightening than one who threatens,
and polite menace is what this format's villains do anyway. **Softening the
surface improved the scene.**

### How to work when a shot is refused

0. **Re-fire the byte-identical prompt once, unchanged, before touching anything.**
   It is refunded, so it is free, and it is the only way to learn whether the
   refusal repeats at all. A single refusal of a prompt is an observation, not a
   finding. (Added 2026-09-19 after the CTO floated "medicine + cash in one shot"
   as a trigger from n=1 per arm and retracted it the same afternoon — the
   wording in question had in fact already passed in the table above and was
   simply never shot at 720p. Do not let that hypothesis back in without a
   repeat.)
1. **Do not reword and re-fire.** That is what cost eight refusals and taught
   nothing, because each rewrite changed several things at once.
2. **Bisect, one variable per attempt**, at 360p so a pass costs 6 credits.
   Remove all dialogue first — it is the most likely half and the cheapest cut.
3. **Confirm by reverting.** A pass that does not re-fail when you put the thing
   back proves nothing; the classifier could simply be noisy.
4. Google publishes **no list** of what Flow refuses. Its Generative AI
   Prohibited Use Policy names "harassment, bullying, intimidation, abuse" among
   four broad categories, and nothing matching "a poor man counting money for a
   sick parent" — so the policy text will not tell you which line to change.
   Only the ladder will.

## Money — the rules that come before everything

- Flow spends the CEO's **monthly Google AI credit pool**. There is no separate
  Flow subscription. Credits **do not roll over**.
- **Never click Upgrade / Subscribe / Buy credits / Get more credits.** A
  paywall or upsell gets closed with its own `x` and quoted verbatim in the
  report.
- **Read the balance before you start and after every action that might cost.**
  The balance lives in the account menu as `เครดิต Google Flow N เครดิต`.
  Record the delta. The deltas are a deliverable, not a formality.
- **Read the live credit estimate in the settings panel immediately before
  clicking Submit.** It updates as model / resolution / duration / quantity
  change, and those settings are not sticky (see Traps).
- Never select **Quality** unless the task names it. One Quality click is 100
  credits — five Fast shots.

## Google AI Ultra — what the CEO is actually paying for (2026-09-18)

Read off the CEO's own one.google.com page and Google's plan page
(support.google.com/googleone/answer/16286513) on 2026-09-18, the day he
subscribed. Not marketing copy from a blog.

| | Pro | **Ultra** |
|---|---|---|
| THB/month | 750 | **3,500** |
| Flow video credits/month | 1,000 | **10,000** (฿0.35/credit — 2.1x cheaper than Pro) |
| **Flow Music** credits/month | — | **30,000** (separate pool, separate product — see below) |
| Storage | 5 TB | 20 TB (30 TB on some variants) |

**Credits do not roll over.** ฿3,500 is charged whether 10,000 or 300 are used.
On 2026-09-17 the READ-ONLY audit (task-9e2dadfd) read the balance at **0** —
so the org's real failure mode is forgetting Flow for three weeks, not
overspending. **Pace: ~2,325 credits/week.** A week under ~1,500 means the
month will expire credit.

What 10,000 buys at the measured rates: Omni 1.1 Flash 720p 8 s = 12 → **833
clips = 111 min raw**. Finished film is set by the keep rate, not the credits:
1-in-3 keep = ~37 min/month (three 12-min episodes at ~3,240 credits each,
฿1,167/EP); 1-in-2 = ~55 min. The keep rate is an estimate until someone logs
it per shoot — the 12-credit figure is measured, the ratio is not.

Ultra also lists "Google Flow with highest filmmaking tool limits". Measured
2026-09-18 (task-68653632, docs/ops/google-flow-ultra-audit.md): it changed
**nothing visible** — same 4 models, no 1080p, reference-chip cap 10, Omni
10 s / Veo 8 s ceilings unchanged. Balance read 9,413 that day after another
session's 48 shots (48 x 12 = 576), which is the pacing arithmetic in practice.

Beyond Flow, Ultra bundles Colab premium GPU (1,000–2,000 CU), Jules and
Antigravity at their highest limits, YouTube Premium Individual ("limited
availability"), Gemini Deep Think — none of which is Flow's concern, but a
C-level planning spend should know the same ฿3,500 covers them. Measured
notes on those live in docs/ops/ (antigravity-cli-test.md, the benefits audit).

## Measured costs (2026-09-07)

| Action | Credits |
|---|---|
| Create a project | **0** |
| Generate a Character / Ingredient image (Nano Banana Pro, 4:5) | **0** — measured 4 times |
| Generate a SCENE / LOCATION plate | **0** — confirmed 2026-09-07, task-46e7c41b, cost-probe first |
| Attach ingredient chips | 0 |
| Navigate any tab (Scenes, Tools, Agent) | 0 |
| **Veo 3.1 Fast — 8s, 720p, 9:16, x1** | **10** — live panel read on the Ultra account 2026-09-18 (task-68653632). Was **20** on 2026-09-07, measured twice. One read so far: confirm before re-planning budgets |
| **Omni 1.1 Flash — 4s, 360p, 9:16, x1** | **4** — measured 2026-09-19 (task-a09ed18a) by balance delta 8,552 → 8,548, not by the panel's estimate. Five times cheaper than a 720p/8s fire: use this for every selector and plumbing test. |
| Veo 3.1 Lite | **5** — live panel read 2026-09-18 (task-68653632); the published table said 10 |
| Veo 3.1 Quality | 100 (published; visible in the panel, never selected) |
| Download / re-export a clip | 0 |

## Anything that must look a specific way needs an Element, not a sentence

**Measured 2026-09-22, «จุดจบของเจ้าหนี้นอกระบบ», 6 clips lost.** Every money
shot in Act 3 rendered a **recognisable Thai 500-baht note carrying the royal
portrait** — in a drama about illegal moneylending. The prompt had asked for the
opposite, positively *and* negatively, in 40 careful words:

> The banknotes are obvious theatrical prop money of an invented place: soft
> pastel paper in even tones, one plain printed numeral in a corner, a simple
> abstract line pattern at the edges, and nothing else on them. No portrait or
> face of any kind, and no national emblem, crest, flag or country name — this is
> not the currency of any real country.

That wording is not the problem. What it was up against is: a Bangkok shophouse,
Thai dialogue, a Thai cast, Thai signage. The model's prior for "banknotes in a
Thai noodle shop" is Thai banknotes, and no amount of description outweighs it.

**The same film proves the fix.** Its three characters and six locations render
correctly across all 74 clips, because each is bound to an `@chip` and attached
as `<IMAGE_REF_N>`. The money was words only — shot 75 attached exactly two
chips, both of them people and places. Cast and sets got references; the prop got
a paragraph; only the prop went wrong.

**So, before any shoot:** list everything the prompt merely *describes*, and ask
which of those the scene's own context would pull toward a default — currency,
signage, uniforms, food, vehicles, documents, anything with a strong local prior.
Each one needs an Element.

**And the Elements are free.** A still costs nothing (see below), so there is no
budget argument for describing a prop instead of binding it. Generate the plate,
make it an Element, attach it. The CEO's rule, 2026-09-22: *"ต้องแก้ตั้งแต่ Prop
Element เลย — ถ้าแก้ที่ต้นตอ ต่อให้ Generate Video ยังไง ก็จะได้ตาม Prop ใหม่"*
— fix the source and every later generation inherits it; fix the prompt and you
are re-arguing with the model's prior on every single shot.

Generalises beyond props: a **time of day** behaves the same way. The word
`night` appended to a 60-word description of a lit, open, busy shop produced
daylight in all 71 clips of the same film. A cue that contradicts the paragraph
around it loses to the paragraph.

### ⛔ Every shoot ends with a mechanical audit. Look at frames to CONFIRM, never to FIND.

**Standing rule, CEO 2026-09-23:** *"ต้องเชคตลอด Audit แบบไม่ต้องดูภาพ หรือดูให้
น้อยที่สุด"* — after every batch, before anything is assembled or uploaded as
final, run the three free local checks below. Frames are opened only for the
shots a check has already named.

| check | tool | catches | cost |
|---|---|---|---|
| what the clip **says** | `tools/film_transcript.py` | line said twice, line dropped, script repeating itself | ~3 s/clip |
| text **burned into the picture** | `tools/burned_text_scan.py` | Veo writing its own Thai captions, mangled (pixel gate, not OCR) | ~0.4 s/clip |
| duration / audio present | `tools/clip_review.py` | wrong length, silent clip | fast |

```bash
python3 tools/burned_text_scan.py <act dirs...> --out audit/burned.tsv
python3 tools/film_transcript.py  <act dirs...> --out audit/transcript.tsv
```

**Why this is not optional.** On 2026-09-23 the finished film had **3 of 173
shots (29, 43, 115) carrying mangled Thai subtitles Veo invented** — «ไม่ใส่ถั่วทอกใช่ไห
เวิทย์», «แล้วมูลนนั่ติกินหู้ร้กาอกิทย์» — and nobody had asked for subtitles.
The CEO found them by watching. **It survives a re-shoot**: shot 43 was re-fired
for this exact defect and came back with different garbage in the same place, so
a re-fire alone is not a fix and every re-fire has to be re-scanned.

**The free fix comes before the paid one.** Veo puts the caption in the bottom
~81–90% of the height, below every face. Crop the top 80% of the frame, centred,
and scale back up (`crop=trunc(iw*0.8/2)*2:trunc(ih*0.8/2)*2:trunc(iw*0.1/2)*2:0,scale=<w>:<h>:flags=lanczos`):
the shot becomes a slightly tighter close-up, the caption is gone, 0 credits.
Re-fire only a shot whose action lives in that bottom band (hands on a counter,
a phone held low) — and re-scan it after.

**⛔ OCR is not a caption detector.** The first version of the scan called
"tesseract read ≥ 8 Thai characters in the band" a caption and reported **14**.
Eleven were a floral nightgown, table grain, an apron and stair treads —
tesseract reads Thai out of any texture — and it missed shot 115 because four
samples a clip fell between two lines. That number went to the CEO before
anyone looked. A caption is a **pixel** fact: near-white glyphs beside a
near-black outline or box, which texture almost never has. The tool now counts
exactly that (white > 225 with black < 90 three pixels away, band scaled to
360×80); real captions scored 160–326, the worst texture 38, the gate is 80.
tesseract only prints what the caption says.

**How the scan stays cheap — keep these when changing it:**
- **crop first**: captions live in the bottom 18%; the other 82% is never read.
- **2 fps, not 4 samples a clip**: the pixel test is cheap enough to sample
  every half second, and a caption lasts as long as a line — 173 clips in ~1 min.
- **no model in the filter**: a pixel count decides. A model is only for the
  shortlist, and usually the shortlist is obvious enough without one.
- **a new detector is calibrated on known positives AND known negatives** before
  its count is reported. One contact sheet of the hit strips is the calibration;
  a count off an uncalibrated detector is an estimate, and is labelled one.

**What none of these can see:** the wrong person in frame, wrong wardrobe, a
prop that should not be there, a character lying down who should be sitting.
Those still need eyes. Keep the eyes for exactly those questions.

### ⛔ Never diagnose audio you have not read back. Transcribe it.

**The rule: if a claim is about what a clip SAYS, produce the transcript first.**
`tools/film_transcript.py` does it — faster-whisper, already installed, on the
CPU, ~3 seconds a clip, no credits, no network. The whole 173-shot film reads
back in ten minutes. There is no budget excuse for guessing.

**What guessing cost, 2026-09-23.** The only audio signal in use was
`silencedetect` — where sound is, never what it is. Every conclusion built on it
was an inference presented as a measurement:

| claim | reality |
|---|---|
| "shot 139 probably repeats a line" | the CEO listened: it is clean |
| "shot 122's repeated number is deliberate, good writing" | it is a man saying "208 งวด" then "208" in four seconds — **the actual defect** |
| "111 shots repeat the speaker block, that is the cause" | the community documents the opposite: the speaker description *should* be restated per line |

On the strength of that reading I rewrote `build_shotsheet.py`, fired five paid
proof shots, and picked all five from a text analysis rather than from anything
anyone had heard. The proof shots landed on scenes that did not have the problem.
One transcript of one clip settled it afterwards in three seconds.

**So, before any claim about dialogue:**

1. `python3 tools/film_transcript.py <clip-dir> --out transcript.tsv` — gives
   `shot · t_start · t_end · heard · scripted · match` for every line.
2. **Read the `heard` column against the `scripted` column.** Three different
   defects fall out, and they have three different fixes:
   - heard ≈ scripted, and the script itself says it twice → **the script is
     wrong**, fix the writing, do not touch the prompt.
   - heard repeats something the script says once → **the render is wrong**,
     re-fire, then look at the prompt.
   - a scripted line has nothing heard for it → **a line was dropped**, which no
     silence-based check can see at all.
3. Only then reach for a prompt change, and say which of the three you are fixing.

A script can read beautifully on the page and land as a stutter in four seconds
of audio. Reading it is not hearing it. Related: [[judge-craft-by-eye-not-metrics]].

### Which things get a chip when slots are scarce

**Measured on the live product 2026-09-22: four chips attach and all four bind.**
`tools/build_shotsheet.py` had refused anything past three with the comment "the
4th is silently disabled" — a number with no source, while this file's own Ultra
audit (task-68653632) had already recorded a **reference-chip cap of 10**. Never
inherit a limit from a comment; the DOM will tell you.

When slots genuinely run out, the CEO's rule (2026-09-22) is to spend them on
**what is biggest in frame and reused most**, because that is where drift shows:

| | shots | in frame | verdict |
|---|---|---|---|
| `@noodle_shop` | **97 of 173** | fills it | chip, always |
| `@upstairs_bedroom` | 36 | fills it | chip |
| a location used **once** | 1 | fills it | prose is fine |
| a banknote | — | centimetres, in a hand | prose is fine |

His reasoning, and it is right: *"ใช้ซ้ำจะดูปลอมทันที"* — prose gives a slightly
different shop every time, and across 97 shots that reads as fake immediately. A
prop seen for a second in someone's hand survives being described. **Characters
are never the thing you drop:** a wrong face is the one error no viewer forgives.

### A prohibition is not an inventory

Do not automate "this shot declares X, therefore attach X's Element". Tried and
reverted the same day: `NOT["money"]` looks like a marker for shots containing
banknotes and is carried by 22 of them, but it is a **prohibition** — its text
ends *"also no notebook, no pen, no paper, no ledger of any kind"* — and most of
those 22 have no money in frame at all. Shot 133 is two people looking at empty
tables. Attaching the money Element to all 22 would have put banknotes into
scenes written to be empty of them: worse than the bug it was meant to fix.

**Which shots actually hold a prop is a reading of the action line, and belongs
to a human.**

**Image generation being free is the most valuable fact in this file.** Make
every character, prop and location plate in Flow, download them, and spend
credits only on video.

Scene/location plates were confirmed free on 2026-09-07 (task-46e7c41b) by
generating one image first and re-reading the balance: 210 -> 210. Still
unmeasured: whether Lite video is really 10.

**Every still this production needs is free.** Spend credits only on video.

## Test fires run at 360p / 8 seconds — never at full quality (CEO 2026-09-18)

When the thing being tested is **behaviour** — does the character speak, does
the voice bind, does the reference hold, does the prompt grammar work — shoot it
at **360p and the real 8 seconds**. Not 720p. Not a shortened 4 s.

| | credits, Omni 1.1 Flash, 8 s | |
|---|---|---|
| 720p | **12** | production |
| 360p | **6** | every test |

**Why 360p:** the only thing that changes is detail. Framing, motion, timing,
lip-sync, audio and whether the model obeys the prompt all come out identical.
Testing those at 720p pays double for pixels nobody looks at.

**Why the full 8 seconds and not 4:** a short clip is not the same experiment.
The model fills whatever runtime it is given, so a 4 s test can stay silent
purely because it ran out of time, and the same prompt then talks at 8 s in
production. The test length must be the production length or the result does
not transfer.

So: **real footage, real duration, lower detail.** Half the credits, same answer.

Only go to 720p once the behaviour is settled and the shot is being kept.

## Concurrency: the backend runs ~3 at once (measured 2026-09-18, task-6403cbb4)

Measured on the Ultra account at 360p / 8s, everything held identical except
quantity:

| quantity | wall-clock | credits |
|---|---|---|
| x1 | **~30 s** | 6 |
| x2 | **~20–25 s**, both | 12 |
| x4 | **~26–36 s** for three of them | 18 charged, not 24 |

If this were serialised, x4 would take four times x1. It does not. While x4 ran,
all four progress badges advanced in lockstep in the same ~8 s window
(5/6/5/6 % → 11/12/12/12 %), which is what concurrent rendering looks like.

**But there is a ceiling, and it is about three.** In the x4 run, three clips
finished in ~30 s and the fourth stalled at 56–58 %, jumped to 99 %, sat there,
and then failed outright. Flow never used the words queued, waiting or in line
anywhere — the only signal was a percentage that stopped moving.

So: **x3 is the useful maximum. x4 buys a failure.**

### A failed generation is not charged

The failure card reads, verbatim:

```
ล้มเหลว
ขออภัย สร้างวิดีโอนี้ไม่สำเร็จ
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```

The credit maths confirms it: x4 should have cost 24 and only 18 was deducted.
(For successful clips the balance was only read after they appeared, so whether
the charge lands at submit or at completion is still unknown.)

### What this does and does not license

Quantity gives **N variants of ONE prompt**, never N different shots — Flow has
no control for that at all. So:

**CEO 2026-09-18, correcting a policy first written here and wrong:**

> "การ Generate x2 x3 x4 มันคือการ Generate Video ซ้ำจากเดิม ซึ่งความเป็นจริงไม่ควรทำ
> เพราะเราจะ Generate แบบ x1 แบบ parallel 2 tab 3 tab maximum"

**Quantity is the wrong lever for this production, and the ceiling is the right
number for the right lever.** An episode is 180 *different* shots. We are not
choosing the best of several takes of one shot — we are trying to finish 180 of
them. Paying double for a second version of a shot that was already fine is
waste, and it does not move the only number that matters, which is how many
distinct shots exist by the end of the day.

So:

- **Default is x1.** Reach for x2 only when a specific shot has already failed
  review once and the fault looks like a dice roll rather than a prompt problem.
  Never x4 — the fourth slot fails.
- **Throughput comes from firing different shots at once**, and the measured
  ~3-concurrent ceiling is per ACCOUNT, not per tab or per machine. So two
  operators on two machines sharing one Google account both render, and that is
  the path.
- Sequential, 180 shots at ~90 s of real handling each is roughly 4.5 hours per
  episode. Three in flight brings that to about 1.5.
- **The org's tab guard allows one tab per task** (`scripts/browser/tab_guard.py`,
  `MAX_TABS_PER_TASK = 1`) and that limit exists because twenty-five Higgsfield
  tabs once accumulated behind it. Raising it is a CEO decision, not something an
  operator or a C-level routes around for convenience. Two machines, one tab
  each, needs no change to anything.

## The shortest path — 12 steps, do them in this order

1. Open a **fresh tab**. `flow.google.com` (labs.google/fx/tools/flow redirects
   there). Chromium browsers only.
2. `resize_window` to 1024x768 — **and know it only takes effect after a full
   page navigation**, not on the initial load. Resize, then navigate.
3. Read and record the credit balance from the account menu.
4. New project → type the name.
5. Characters tab → New Character → paste the reference prompt → model
   **Nano Banana Pro** → generate (free) → rename to the handle. Repeat per
   character/prop/location.
6. Back in the composer, set the model to **Veo 3.1 - Fast**. It does not
   persist — see Traps.
7. Set aspect ratio **9:16** and quantity **x1**. Neither is sticky.
8. **Attach the ingredients — and this is the hardest thing in the product.**
   Clicking a character tile in the `+` picker **navigates to that character's
   editor page**; it does not insert a chip. The only path that inserts a real
   chip (`<span class="mention-chip" data-entity-id="...">`) is:

   > tile's `⋮ more options` menu → click the **inner
   > `<span class="label">เพิ่มไปยังพรอมต์</span>` node**, not the outer
   > `<button>`

   The outer button carries stray `mat-mdc-menu-trigger` / `aria-expanded`
   attributes and **silently no-ops** on every method tried: real click, JS
   `.click()`, pointerdown/up+click dispatch, and ArrowDown+Enter keyboard nav.
   Even the correct inner-span target succeeded roughly **once in fifteen
   attempts** on 2026-09-07 — the insertion is racy in a way no operator has
   characterised yet. Budget for this. It cost task-46e7c41b most of its hour
   and blocked six planned stills entirely.

   The earlier recon (task-796a93f6) attached chips, including four at once,
   without difficulty — so this is flaky, not impossible. Treat a failed
   attach as normal and retry rather than as a blocker.
8b. **Reference-chip cap is 10** (measured 2026-09-18 without spending: attach
   one character at a time from the picker; the 11th attach is silently
   absorbed — no error, no chip). Plan shots to ≤10 references.
9. **Count the chips before you fire.** The picker hides characters that are
   already attached, so an attached character is one that has *disappeared*
   from the list. A missing chip means the shot generates with no reference
   and nobody finds out until the frames are reviewed.
10. Paste the prompt. Verify the Thai text survived, byte for byte, by reading
    `innerText` of the `[contenteditable="true"]` element — do not trust the
    visual.
11. Re-read the live credit estimate, then click Submit (icon-only,
    `aria-label="Submit"`).
12. Wait, then download via the top-toolbar download icon or right-click →
    ดาวน์โหลด.

## Measured timings — extend this table on every run

| Action | Time | Source |
|---|---|---|
| Veo 3.1 Fast 8s render, run 1 | **~51 s** | task-796a93f6 |
| Veo 3.1 Fast 8s render, run 2 | **~94 s** | task-796a93f6 |
| Second clip's export | hung indefinitely; a full page reload then a retry completed it ~15 s later | task-796a93f6 |
| Full walk: project + 4 characters + 2 videos + downloads | ~40 min, well over a 30-action budget | task-796a93f6 |
| First page load of flow.google.com incl. resize | 50 s | task-46e7c41b |
| Reading the credit balance from the account menu | ~115 s (2 failed menu-toggle attempts) | task-46e7c41b |
| **Still image generation, submit -> image visible** | **32 / 38 / 40 / 48 s** (4 samples, Nano Banana Pro) | task-46e7c41b |
| Renaming a Character | 286 s (UI fought back) | task-46e7c41b |
| Downloading one image | 25 / 82 / 85 / 266 s — wildly variable; two needed a fresh tab | task-46e7c41b |
| Full still-plate session (4 images made, 6 blocked) | **~70 min**, over its 60-min budget | task-46e7c41b |

**Every Flow task must record wall-clock per action and append to this table.**
An operator that reports "it took a while" has failed the reporting bar.

## The settings panel — measured against the live DOM (2026-09-19, task-a09ed18a)

Everything below was wrong in this file until a Playwright dry-run checked it.

- The composer's collapsed pill has **no per-facet aria-labels.** "Ratio",
  "Duration", "Resolution" never existed. Every real control lives in the
  `<flow-prompt-box-settings>` overlay, opened by `aria-label="ทริกเกอร์การตั้งค่า"`.
- **That panel opens on the `รูปภาพ` (Image) tab.** `วิดีโอ` must be selected
  first or you are setting an image's options. Both the open and the tab switch
  are racy — poll, never trust one click.
- **Every toggle label is always in the DOM** — 720p and 360p, x1 through x4,
  every duration. Only the wrapper's `mat-button-toggle-checked` class says which
  is active. So "is '360p' in the body text?" answers **true no matter what is
  selected**; a read-back written that way confirms whatever you hoped for.
- **The credit estimate exists only while the panel is open** — genuinely absent
  from the DOM when closed, not merely hard to find. Reopen, read, close.
- **The submit button is `aria-label="เริ่มสร้าง"`**, never "Submit".
- **`[aria-label="Download"]` / `[aria-label="ดาวน์โหลด"]` match ZERO elements.**
  A runner waiting on them reports a clip as failed while Google has generated it
  and charged for it. Verify the real control before believing any "it failed"
  that came from automation.
- **A stray `.cdk-overlay-backdrop` left open by an earlier script blocks every
  later click**, chip attach included, with Playwright reporting "element is
  visible, enabled and stable" and then "subtree intercepts pointer events".
  Read that twice: the "chip attach works about 1 in 15 times" folklore in this
  file may be partly this. Close what you opened.

## Traps — each one silently costs a generation

| Trap | What happens | What to do |
|---|---|---|
| **Chips drop silently** | Expanding the prompt textbox, or clicking the composer's `x`, clears **every attached ingredient chip** with no warning. Happened twice in one hour. | Re-count chips via the `+` picker immediately before every Submit. Never fire off a remembered chip state. |
| **Model resets** | Switching tabs or reloading silently returns the model to the account default (Omni 1.1 Flash). | Re-select Veo 3.1 - Fast and read it back before every fire. |
| **Aspect and quantity are not sticky** | 9:16 and x1 revert across prompt sessions. | Set and verify both every time. |
| **Export hangs** | "Exporting your scene…" can sit forever. | Full page reload, then click download again. Costs nothing but time. |
| **resize_window is late** | Applies only after a navigation; early screenshots come out at ~1456x840 and cost far more visual tokens. | Resize, navigate, then screenshot. |
| **The viewport reverts mid-session** | A correctly-resized tab silently went back to 2280x722 with no navigation in between. Screenshot pixels and `window.innerWidth` then disagreed by a ~0.688 scale factor (1568px shot for a 2280px CSS viewport). | Never click from raw `getBoundingClientRect()` coordinates. Click by element handle, or convert by the measured ratio. |
| **Settings panel and ingredient picker are overlays that text reads miss** | `get_page_text` / `body.innerText` frequently return the page *underneath* the open panel, not the dropdown values. task-68653632 burned ~22 screenshots (budget 5) falling back to pixels to read four prices. | Read dropdown state by element handle (`find`/`read_page` on the overlay node) or take ONE screenshot per open panel and read everything from it; budget the screenshots up front. |
| **The model dropdown closes after every pick** | Reading N model prices costs ~3N clicks (open, pick, read). | Read all prices from one open dropdown if it shows them; otherwise accept 3 clicks per model and budget for it. |
| **A focused contenteditable still drops the first keystroke** | A `.ProseMirror` composer confirmed as `document.activeElement` lost the next keystroke about half the time — text stayed as the placeholder, no error, no state change. | `el.focus()` via `javascript_tool` and the first keystroke via `computer` **in the same `browser_batch` call**, with no intervening tool call, not even a read. This single behaviour cost most of one task's budget. |

## Google Flow Music — a different product, do not look for it inside Flow

**URL: `flowmusic.app`** — and that IS Google's domain: `flowmusic.google`
(the URL in blog.google's post) 301-redirects to `flowmusic.app` →
`www.flowmusic.app`, and Flow's own top-nav "Flow Music" button links to
`www.flowmusic.app/?utm_source=flow`, page title "Google Flow Music"
(task-68653632, 2026-09-18). An earlier version of this section called
`flowmusic.app` a clone — that was an inference from a search-result page,
never verified, and it was wrong. Verify a product domain by following the
official link's redirect (`curl -sIL`), not by comparing domain names.
It is a **separate sign-in** from Flow; the audit stopped at the login wall
(credentials are a hard stop for a worker), so balance/price/download are
still unmeasured.

From the official pages only (blog.google, deepmind.google/models/lyria),
read 2026-09-18 — nothing below is measured on our account yet:
- Model: Lyria 3 Pro / Lyria 3.5. Songs with vocals in many languages;
  lengths of 60 s, half, or full ~3 min; section-level edits (highlight a
  part, rewrite/translate lyrics, restyle the drop); style transform keeping
  the melody; iOS app shipped, Android "coming soon".
- **Every track carries a SynthID watermark.** Commercial-use rights are NOT
  stated on the official pages — verify before putting a track on a
  monetised page.
- **It does not do sound effects or foley.** Neither official page mentions
  SFX at all. Ambience/foley for a shot comes baked into Omni/Veo output;
  anything else is a free SFX library, not a model.
- Ultra grants 30,000 Flow Music credits/month; per-track cost, download
  format and stem export are unmeasured until the audit opens it.

The org already has a Suno baseline to A/B against: task-f69d6442 (three
horror cues, on Drive). Listening beats reading reviews.

## What Flow does NOT have — stop looking for these

Verified absent across the toolbar, right-click menu, share panel, fullscreen
player, model dropdown and filter panel:

- ~~No first-frame or last-frame slot~~ — **WRONG, retracted 2026-09-07.**
  See "Start and end frames" below. The CTO inferred this from an operator's
  silence rather than from a measurement, told the CEO frame control was
  API-only, and the CEO found the control himself in about a minute. Do not
  repeat the mistake: an operator not mentioning a feature is not evidence the
  feature is absent.
- **No 1080p and no upscale control** — re-verified on the **Ultra** account
  2026-09-18 (task-68653632): composer resolution facet, asset filter facet,
  clip toolbar and right-click menu all offer only 720p/360p; exports are
  720x1280. Google's own credit table lists "1080p upscale = 0 credits" — it
  cannot be reproduced on Pro or Ultra. 1080p+ means Topaz (or equivalent)
  outside Flow.
- **No shot-list style storyboard.** There is still no way to type a shot list
  or order empty slots. But the Scenes ("ฉาก") tab is **not** the passive
  gallery the first recon called it — it is where the frames that feed the
  start/end slots are made. See below.
- **No whole-episode export.** Per-clip download only. Assembly happens outside.
- ~~No batch or queue~~ — **WRONG, retracted 2026-09-18 (task-6403cbb4).** There is
  no way to submit two DIFFERENT prompts together, but the quantity control fires
  several generations of one prompt and the backend renders them concurrently.
  See "Concurrency" below.
- **No saved prompt templates.** Google's example cards are presets, not
  user-savable.
- **No audio upload.** Dialogue and ambience are prompt text only; you cannot
  supply a voice track.
- **No public API from inside the product.** The closest surface is the in-app
  **Agent** mode with an "Instructions for Agent" panel and a global Agent
  Settings page offering confirm-every-time vs fully-autonomous. Unexplored —
  the next operator with budget should map it, because it is the only
  automation-shaped thing in the UI.

## Start and end frames — they DO exist in the web UI

Confirmed by the CEO from his own screen, 2026-09-07. The composer carries two
chips side by side with a swap arrow between them, sitting directly above the
"คุณต้องการสร้างอะไร" prompt field:

```
[ เริ่ม ]  ⇄  [ สิ้นสุด ]          เริ่ม = start frame,  สิ้นสุด = end frame
```

### The exact path (task-ecca0bc3, measured)

```
composer → settings pill (bottom-right, shows model/mode)
        → วิดีโอ tab
        → submode toggle:  [ เฟรม ]  [ องค์ประกอบ ]
```

**The default is `องค์ประกอบ` (Ingredients).** That single default is why the
first recon reported the feature as absent — it is one click away from the
chip UI, not hidden in a menu.

Click **`เฟรม`** and the composer's whole attach area is replaced by two slots:
`เริ่ม` (start) and `สิ้นสุด` (end), with a swap control between them whose
accessible name is `สลับเฟรมแรกและเฟรมสุดท้าย` — "swap first frame and last
frame".

### ⛔ THE CONSTRAINT THAT SHAPES EVERY SHOT: เฟรม and องค์ประกอบ are mutually exclusive

They are a **single-select toggle**. Choosing `เฟรม` removes the chip row and
the `+` ingredient picker entirely. Choosing `องค์ประกอบ` removes the frame
slots.

**In Flow you get consistent faces OR a consistent set. Never both in one
generation.**

| Mode | You lock | You lose |
|---|---|---|
| `องค์ประกอบ` | up to 3 characters/props | frame control — the set drifts |
| `เฟรม` | the exact opening (and closing) image | character references — faces drift |

This is a **Flow UI limit, not a Veo limit**. The API takes `image`,
`lastFrame` and `referenceImages` as separate parameters and accepts all of
them together. For any production that needs recurring faces in a recurring
place, that difference is the whole argument for scripting against the API.

Per-shot workaround inside Flow: pick the mode by what matters in that shot.
A face held in frame needs `องค์ประกอบ`. A wide, a cutaway, an object, a back
of a head, a shot that must cut cleanly from the last one — `เฟรม`.

### What the frame picker will actually show you

Clicking `เริ่ม` opens a dialog titled `เลือกรูปภาพเฟรม` with a project-scoped
dropdown, a search box and a sort control. It has **no upload button and no
drop zone**.

**Character/Ingredient-tagged images are EXCLUDED from this picker.** A project
holding only Characters shows `ไม่พบชิ้นงาน` — "no items found". A plain
untagged image generated in Image mode appears immediately and is selectable.

So: **a plate you want to use as a frame must be generated as a plain image in
Image mode, NOT saved as a Character.** An image can serve one role or the
other, not both. Plan which role each plate plays before you make it.

Uploading from disk: the project's `เมนูเพิ่มสื่อ` (Add media) menu has an
`อัปโหลด` item, but a trusted click on it opens an **OS-native file dialog**
(`document.hasFocus()` goes false, no `<input type="file">` ever enters the
DOM — consistent with `showOpenFilePicker()`). Neither the extension's
`file_upload` tool nor a synthetic JS click can drive it. Whether an uploaded
file then appears in the frame picker is **plausible but unverified**. Do not
plan around disk upload until someone proves it.

### Cost in เฟรม mode

The live estimate reads `การสร้างใช้ 20 เครดิต` — identical to `องค์ประกอบ`
mode for the same Veo 3.1 Fast / 9:16 / x1 config. Measured with both slots
empty; a before/after delta with an image actually attached is still unmeasured.

## Two assets per location, if a location must also be a start frame (2026-09-18)

Confirmed a second time, on `@street_front`, in task-115ae41c: the เฟรม picker
`เลือกรูปภาพเฟรม` shows **only plain, untagged images.** Searching for a plate
that was created as a Character/Ingredient returns `ไม่พบชิ้นงาน`.

So a location cannot be both. If a production wants a location that is
- referenceable as a chip in `องค์ประกอบ` (to lock the set while faces are locked), **and**
- usable as a frame-locked start image in `เฟรม`,

it needs **two assets generated from the same prompt** — one saved as an
Ingredient, one left as a plain image. Decide which a given location needs
before generating it, and generate both when in doubt; images are free.

## Capture each clip's id at SUBMIT, not in a second pass (2026-09-18, Act 1 shoot)

Two operators shot 24 shots each into one project. Both finished the shoot phase
cleanly. Both then lost **five clips each** in the download phase — ten paid
clips sitting in Flow that neither could retrieve — and both reported that
re-locating their own shots cost more than the entire shoot had.

Why: the project feed is one reverse-chronological list with no shot number,
mixing both operators' clips and older tests; the search box does not reliably
filter prompt text; the grid virtualises to ~7 visible items; and two operators'
prompts share boilerplate for the same characters. "Shoot all, then download
all" was the brief's design, and it was the mistake.

**The rule:** the moment a shot's Submit is accepted, in the same tool-call
sequence, capture its `/edit/<uuid>` URL (the composer navigates to it) and
write it to the report table next to the shot number. Download from that URL,
by id, never by hunting the feed.

**The cache trap, which is the other half of the loss:** a clip that has been
played once **in this Chrome profile** is served from disk cache on every later
play, with **no network entry at all** — not in `read_network_requests`, not in
`performance.getEntriesByType('resource')`. The CDN-sniff method then finds
nothing and looks exactly like the "player never loads" trap from the opposite
side.

**A later "fresh session" does not fix it** (task-f93e0f84, 0/10 recovered).
Chrome's disk cache is keyed by URL and shared by every tab and every operator
in the profile; a new Claude session is not a new cache. The only fix is
**capture the `flow-content.google/video/...` URL the first time the clip is
ever fetched, by whoever fetches it first**, muted
(`HTMLMediaElement.prototype.play` overridden to mute first), and keep it. A URL
captured at first play still curls later.

**If the first play was already missed, the clip is unrecoverable by an operator
— and a C-level must not brief one to try.** That happened on 2026-09-19: the
CTO sent an operator after seven clips that earlier operators had already
played, which this very paragraph says cannot work, and the run returned 0/7.
The rule existed; the brief was written without reading it.

**The C-level escape hatch, which is a CTO action and never an operator's:**
Chrome's disk cache is a directory. Quit Chrome, delete it, restart, then play
the clip once — the fetch is real again and the URL is capturable.

```bash
# Nothing may be driving Chrome while this runs, or you kill that run.
osascript -e 'tell application "Google Chrome" to quit'; sleep 4
pkill -9 -f "Google Chrome"; sleep 2
rm -rf ~/Library/Caches/Google/Chrome/Default/Cache
open -a "Google Chrome"
```

This removes cached **assets only** — not cookies, not logins, not history, not
site data — so the Flow session survives it. It is still the CEO's browser: do it
when no operator is mid-run, and say afterwards that you did.

**And some clips never surface at all:** five of operator A's shots showed zero
`<video>` elements and zero requests on a direct `/edit/<id>` open, in three
separate runs across an hour. That is Flow-side, not ours. Two attempts, then
it is a re-fire decision for the C-level, not a retrieval problem.

**Two attempts, then stop.** If a clip will not surface after one reload and one
fresh tab, it is stuck for this session. Report the ids and move on — thirty
tool calls were spent on five stuck clips because the skill implied the CDN
pull always works eventually. It does not.

**Finding your own clip when you must:** search the feed for a distinctive
fragment of the shot's Thai dialogue line, not its prompt. Dialogue is unique
per shot; prompt openings are not.

## Clips do not live in git (2026-09-18)

48 clips at 720p is ~120 MB. Two shoots landed 49 MB of mp4 in the repo under
`docs/reports/` before anyone said otherwise. Video goes to Drive under the
ILAG rules in `gdrive-filing`; the repo keeps the report, the shot table and
the review ledger. A worker's `clips/` directory is a staging area that the
C-level files and then removes from the branch before merge.

## Never press play (CEO 2026-09-18)

A clip played inside Flow comes out of the machine's speakers, and the CEO works
at that machine. Two operators downloading 48 clips turned the office into a
noodle shop for an hour.

**Playback is not part of any task.** An operator has no ears and is forbidden
from judging a take; the CTO checks clips with ffmpeg on the downloaded file. So:

- never click play, never scrub the timeline to "check" a clip
- if a preview autoplays, mute and pause it at once:
  `document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})`
- get the file via the CDN pull; look at nothing in the player

## The in-page video player can fail completely — pull from the CDN instead (2026-09-18)

Distinct from the dead download button. On task-115ae41c the clip editor never
rendered a frame: black box, and `document.querySelector('video')` returned
`null` across seek, play and retry, while the timeline's filmstrip thumbnails
loaded normally. The render itself was fine.

**The workaround is better than the UI anyway, and should be the default way to
check a clip:**

1. `read_network_requests` on the tab — the `flow-content.google/video/<id>`
   URL is requested even when the player never shows it.
2. `curl` it.
3. `ffprobe` to confirm duration, `ffmpeg` to extract the exact frames you need.

Reading frame 0 and the last frame locally with ffmpeg is frame-accurate.
Scrubbing Flow's own timeline is not, and a report that says "the last frame
looks right" after scrubbing a UI is not evidence. **Verify clips with ffmpeg.**

## Left sidebar — what each tab is for

`สื่อทั้งหมด` all media · `วิดีโอ` videos · `ตัวละคร` characters (Ingredients) ·
**`ฉาก` scenes — the start/end frame source** · `เครื่องมือ` tools ·
`ถังขยะ` trash · `ยุบ` collapse.

## Composer settings row — what it shows

`Agent` toggle on the left; on the right `วิดีโอ · 720p · 8 วินาที · [aspect] · x1`
and the submit arrow. 720p is the ceiling shown on a PLUS account.

## Account tier

**ULTRA since 2026-09-18** — the CEO paid ฿3,500 and the badge top-right beside
the avatar now reads `ULTRA`. That is **10,000 credits per month**, not 200.

Read the badge; do not carry a number in from a previous run. Every earlier
paragraph in this file that plans a shoot "against 200" was written on the PLUS
plan and is obsolete. Credits still do not roll over, and every rule under
"Money" still binds — a bigger pool is not permission to spend loosely.

## Two ceilings that were never real — SETTLED 2026-09-18

Both of these shaped how every scene in this project was written, and both were
wrong. Neither is a constraint any more.

| what we believed | what is true |
|---|---|
| **3 references per generation** | **still 3 in the Flow UI** (the 4th chip is silently disabled) — the API's 10 is API-only; see the Omni grammar section |
| **one speaking character per shot** | **every character in frame can speak** — it is decided by the prompt |

So a shot can now carry a cast, a location AND props together, and a scene with
three people talking is one generation, not three cuts stitched around the
limit. Any scene broken up to dodge either ceiling should be reconsidered.

## ⛔ THE PROMPT OVERRIDES THE REFERENCE IMAGE — this is the most important rule in this file (CEO 2026-09-18)

A reference chip is not a lock on appearance. **Where the prompt and the picture
disagree, the prompt wins, silently, every time.**

Measured on the CEO's own characters:

- The character image wears sunglasses pushed up on his head. The prompt does
  not mention them → **they are gone.**
- The character image has long hair. The prompt says short hair → **the hair is
  short.**

Nothing errors. Nothing warns. The chip is attached, the face is broadly right,
and one detail after another quietly drifts away from the character we built —
which is exactly the "drift" this project has been chasing for two weeks.

### What follows: the ASSET SHEET, and the rule that every prompt quotes it

> **Look at each asset once. Write down what is in it. From then on, every
> prompt describes that asset by quoting the sheet — never from memory, never
> from imagination, never by omission.**

**Omission is the trap.** A detail you do not mention is not "left as the
image" — it is left to the model, and the model will change it. The sheet must
therefore be complete enough that a prompt built from it has nothing to invent.

One sheet per production, holding, for every character, location and prop:

```
@lung_somchai
  face / build   : <exactly what the reference image shows>
  hair           : <length, colour, how it sits>
  carried items  : <glasses on head? watch? apron ties?>
  default outfit : <the wardrobe item, by name>
```

Then a prompt for that character is assembled from the sheet, not written fresh.
The sheet is the single source of truth about how anyone looks, the same way the
script's APPEARANCE LOCK is the ground truth about which shot is wrong.

### Wardrobe — a character needs several outfits, and the model must never guess

One character appears in different places, at different times, in different
roles. Clothing changes with all three, and **an unspecified outfit is an
invented outfit**.

The obvious fix — generate a second character image wearing the other clothes —
**does not work: a regenerated character comes back with a different face.**
Faces are the one thing we cannot afford to lose.

So build the wardrobe as its own assets instead:

- Make each outfit a **prop / image asset** in Flow, generated once.
- Keep the character asset untouched, so the face stays fixed.
- In the prompt, name the character AND describe the outfit from the sheet —
  and where the outfit matters, attach it as one of the (now 10) references.

Every shot in the script therefore carries an explicit costume. "He is wearing
the same as before" is not a costume; the model has no "before".

### Why this is the difference between AI slop and a real short film

Everything above is bookkeeping, and bookkeeping is the entire gap. A drama
where the father's hair length changes between two shots of the same
conversation reads as AI slop no matter how good any single frame is. A drama
where it never changes reads as a film. The sheet is what makes the second one
possible, and it is cheap — it is written once and read forever.

## Mid-session Google sign-out — it looks exactly like Flow being flaky

Observed 2026-09-07, task-4a59a1a4. The Chrome profile lost its Google session
part-way through a run. Every route — the direct project URL, the bare root,
a reload, a brand-new tab — silently redirected to the `/about` marketing
splash. Flow's own chrome never said "please sign in". It reads as a routing
bug and can burn ten minutes of debugging.

**The one-second test:** open `google.com` and look at the top-right corner.
An avatar means signed in; a "Sign in" button means the session is gone.
`myaccount.google.com` and `accounts.google.com/ServiceLogin` confirm it.

If signed out: **do not sign in.** File a blocker and stop — credentials are a
hard stop for this role, and only the CEO can restore the session.

Note that Higgsfield and other sites in the same Chrome keep working normally
when this happens, so "another operator is fine" is not evidence your session
is fine. Each site's login is independent.

## The MCP tab group can be destroyed mid-action

Once during the same run, `tabs_context_mcp` returned "No tab group exists for
this session" immediately after a submit click. The submit never reached
Google. Recovery: open a fresh tab, re-navigate, and **re-verify the composer
state from scratch** — the prompt text, the mode, and every chip. Never assume
a pre-destruction state survived.

Suspected contributing factor: four browser_operators were sharing this Chrome
at the time. Two is the org's working limit; beyond that, expect tab churn.

## How this file changes

A worker who finds a rule here to be wrong does **not** edit this file — workers
cannot write skills. It reports the contradiction in its own report, in this
shape, and the C-level updates the skill:

```
SKILL-CONTRADICTION: google-flow-ops :: <the rule as written>
  :: <what actually happened, with the evidence>
  :: <date, task id>
```

A contradiction backed by a screenshot or a DOM read wins over anything written
here. A contradiction backed by a memory does not.


## Voices — lock one per character BEFORE shooting any dialogue (CEO 2026-09-08)

A drama dies if the father sounds like a different man each scene. Flow can fix
that, and the fix is a setup step, not a per-shot step. **Install a voice on
every speaking character first. Only then shoot dialogue.** A series that starts
shooting before its voices are fixed pays for those shots twice.

What Google documents (support.google.com/flow/answer/16353334):

- **Add (+) → Voices**, in the ingredients section.
- Preset voices, each with a free 10-second sample: hover, then click Play.
- **Custom voice**: choose a base preset, name it, and *describe* the change
  ("Make the voice sound slightly raspy with a New York accent").
- "To maintain a specific character's voice across multiple video clips, add a
  single-speaker voice reference to your prompt."
- Voice references work **only on generations that use ingredients**. A
  frame-only (เฟรม) shot cannot carry one, and errors if you try.
- Requires the model **Gemini Omni Flash 1.1**, not Veo 3.1 Fast.

Two rules that follow, and are not negotiable:

1. **A worker has no ears.** Never pick a voice by listening, never infer a
   voice's gender or age from its name, never write "sounds about right" in a
   report. Either use the custom-voice path and *describe* the voice in words
   (the description is text, which a worker can write and verify), or capture
   the preset list verbatim and let the CEO listen and name the choice. Copy UI
   strings exactly; do not translate them.
2. **One voice, one character, written down.** Record the chosen voice name (and
   the exact custom description) next to that character's APPEARANCE LOCK in the
   script, the same way the look is locked. A voice that lives only in someone's
   memory of a preview will not survive the next session.

## Casting a voice — the rules, the whole voice list, and the ledger (CEO 2026-09-08)

Everything needed to cast a voice is on this page. **Do not search the web for
it** — Google's own API docs are thinner than what is here (one adjective per
voice, no gender, no pitch), and the Flow UI labels below were read off the
CEO's own account.

### Rules

1. **One voice per character, and never the same voice twice in one story.**
   Two characters sharing a preset will read as the same person the moment they
   share a scene. Check the cast ledger before assigning.
2. **The C-level casts, not the worker.** The voice goes into the brief by name;
   a worker may only report that a preset is missing, never substitute on taste.
   A worker has no ears and must never claim it heard anything.
3. **Write it into the script** as a `VOICE LOCK:` line under the character's
   `APPEARANCE LOCK`, before any dialogue shot is fired.
4. **The CEO's ear is the only real evidence.** The labels get us a shortlist;
   the 10-second previews are free and speak Thai, so a doubtful cast is settled
   by listening, not by arguing from adjectives.
5. **Score every verdict in the ledger.** A voice the CEO keeps earns +1. A voice
   the CEO orders changed earns −1. At −2 a voice is retired for that kind of
   role and must not be proposed again.

### Casting criteria, and which parts are guesses

In priority order:

1. **Sex must match the character.** The one field that is unambiguous data.
2. **Pitch band as a stand-in for age** — low for an older man, mid-low for a
   young man. **This is an inference, not data.** Nothing in Google's labels ties
   pitch to age; it is simply the best proxy available.
3. **The tone word separates characters who share a scene.** The father is
   gravelly and the lender smooth so they never blur together.
4. **Reject tone words that fight the character.** No "lively", "upbeat" or
   "excitable" for a man who is exhausted.

**What the labels do not contain: age, accent, or how well the voice handles
Thai.** Only three of the thirty carry any age signal at all — Gacrux "mature",
Leda "youthful", Fenrir "younger pitch" — and none of those three is a male
voice, so there is no documented "old man" preset to pick. Thai is listed as a
supported language, with nothing said per voice.

### All 30 presets, as the Flow picker labels them

| Voice | Label (verbatim) |
|---|---|
| Achernar | Female, soft, high pitch |
| Achird | Male, friendly, mid pitch |
| Algenib | Male, gravelly, low pitch |
| Algieba | Male, easy-going, mid-low pitch |
| Alnilam | Male, firm, mid-low pitch |
| Aoede | Female, breezy, mid pitch |
| Autonoe | Female, bright, mid pitch |
| Callirrhoe | Female, easy-going, mid pitch |
| Charon | Male, informative, lower pitch |
| Despina | Female, smooth, mid pitch |
| Enceladus | Male, breathy, lower pitch |
| Erinome | Female, clear, mid pitch |
| Fenrir | Male, excitable, younger pitch |
| Gacrux | Female, mature, mid pitch |
| Iapetus | Male, clear, mid-low pitch |
| Kore | Female, firm, mid pitch |
| Laomedeia | Female, upbeat, mid-high pitch |
| Leda | Female, youthful, mid-high pitch |
| Orus | Male, firm, mid-low pitch |
| Puck | Male, upbeat, mid pitch |
| Pulcherrima | Ungendered, forward, mid-high pitch |
| Rasalgethi | Male, informative, mid pitch |
| Sadachbia | Male, lively, low pitch |
| Sadaltager | Male, knowledgeable, mid pitch |
| Schedar | Male, even, mid-low pitch |
| Sulafat | Female, warm, mid pitch |
| Umbriel | Male, smooth, lower pitch |
| Vindemiatrix | Female, gentle, mid pitch |
| Zephyr | Female, bright, mid-high pitch |
| Zubenelgenubi | Male, casual, mid-low pitch |

### Cast ledger

Added 2026-09-18 (cast by the CTO in the asset brief, bound by task-a55713c5,
confirmed on the character pages by task-70d351e4):

| character | preset | verdict |
|---|---|---|
| `@cop_wit` วิทย์ | **Achird** — Male, friendly, mid pitch | pending ear |
| `@jae_muay` เจ๊หมวย | **Laomedeia** — Female, upbeat, mid-high pitch | pending ear |
| `@staff_a` น้องเอ | **Achernar** — Female, soft, high pitch | pending ear |
| narrator (voice only, `_Shared Element`) | **Sulafat** — Female, warm, mid pitch | pending ear |
| `@lender_cherd` | currently bound to **algieba**, the script records Umbriel — a CEO decision is open | — |

⛔ **An asset that the `ตัวละคร` grid does not show may still exist.** On
2026-09-18 task-36507a6a scrolled that grid top to bottom **twice** and reported
`@cop_wit` and `@side_wall` absent from the project. Both were there the whole
time; task-75926848 found them on the next run. The cause is the same
`document.hidden` virtual-scroll freeze already recorded above for the voice
picker: **in a background tab the grid stops re-rendering, so scrolling walks
past rows that are never painted.** A `scrollTop` assignment does not thaw it —
only a real wheel-scroll through the `computer` tool forces the re-render.

So: **a negative from that grid is not evidence.** Confirm an asset is missing
with the tab in the foreground and a real scroll, or do not claim it at all.
This cost a briefed generation of two assets that did not need generating, and
it is the second time this exact freeze has produced a false "not found" — the
rule existed for the voice picker and nobody carried it across to the grid.

The weaker claim is still true and still worth checking: a row in the cast
ledger means a voice was **cast**, never that the character asset exists.
`tools/build_shotsheet.py` closes this at the other end — it refuses to render a
sheet whose handles have no downloaded plate.


Update this the moment the CEO reacts to a voice. Score starts at 0 and moves
±1 per verdict; the "verdict" column stays "pending ear" until a human has
actually listened.

| Story | Character | Voice | Score | Verdict |
|---|---|---|---|---|
| เงินที่พ่อตั้งใจหา | @lung_somchai (M, 58) | Algenib | 0 | pending ear — heard in shot58-omni |
| เงินที่พ่อตั้งใจหา | @nong_daeng (M, 24) | Iapetus | **+1** | **KEPT — CEO listened 2026-09-18, "เสียงถูกแล้ว"** |
| เงินที่พ่อตั้งใจหา | @grandma_pranom (F, 79) | Gacrux | 0 | pending ear |
| เงินที่พ่อตั้งใจหา | @lender_cherd (M, 45) | **algieba** — live account 2026-09-18 (task-68653632 + banchi-assets REPORT); the ledger said Umbriel and was wrong. Re-bind to Umbriel or accept algieba: CEO ear-check before any of his dialogue is shot | 0 | ledger≠account, pending ear |

Shortlist held in reserve for an older-sounding man, if Algenib is rejected:
Enceladus (breathy, lower), Charon (informative, lower). Sadachbia is the only
other male at the lowest pitch band but "lively" fights the character.

## Sound: what can be steered and what cannot (2026-09-08)

The CEO's plan is to score the series in Suno and ElevenLabs, so what Flow needs
to deliver is the sound that genuinely happens in the scene, and nothing else.

**There is no off switch.** Omni Flash does not support negative prompts at all,
the Gemini API's Veo parameters carry no negativePrompt, and there is no mute,
no level control and no way to separate the audio Veo bakes into the clip.

What works instead:

- **Name only the diegetic sounds, positively.** Keep the script's
  `Ambient noise: ladle in broth.` line and let it carry the whole audio brief.
- **Delete "No music." from the prompt.** Google's own prompting guide says to
  describe what you do not want rather than instruct with "no" or "don't", and
  naming music at all is a way to invite it. Our shot prompts still carry that
  line; strip it on the next pass.
- **Silent shots get muted in the edit.** A shot with no dialogue loses nothing
  by having its whole track replaced with our own ambience and score, which
  removes any risk of an unwanted bed. Only dialogue shots have to keep Veo's
  audio, because the voice is welded to it.

## Which model for a drama: Omni Flash, not Veo 3.1 Fast (2026-09-08)

Veo 3.1 **Quality** is out of the question for a character series regardless of
budget: it cannot use ingredients at all, so it cannot hold a face. The real
choice is between the two that can.

| | Gemini Omni Flash 1.1 | Veo 3.1 Fast |
|---|---|---|
| Voice lock | yes | no |
| Max length | 10s | 8s |
| Video-to-video editing | yes | no |
| Cheap draft | 360p at half cost | none |
| Ingredients (face lock) | yes | yes (8s only) |
| Raw visual finish | second | first |
| Cost, 720p 8s | **12 credits** | 20 credits |
| Cost, 720p 10s | 15 credits | n/a |
| Cost, 360p draft | 6 at 8s, 7 at 10s | none |

Veo Fast makes the prettier frame. Omni Flash makes the thing a viewer can
follow: the same voice every scene, a quarter more story per credit, and a way
to fix a near-miss without re-rolling it. For a dialogue-driven series the
features outweigh the finish, and the gap in finish is small — one third-party
matched test of eight prompts scored Omni 4.124 against Veo 3.1 Fast's 4.009.
That is a blog, not a measurement of our own material; the settling test is one
shot we already own, re-shot on Omni with the same ingredients, compared side by
side against the Veo version.

Unverified as of 2026-09-08, and each one can change this: whether the AI PLUS
plan exposes Voices at all, what Omni Flash costs per generation on this
account, and whether the Gemini/Vertex **API** can set a voice (no voice
parameter is documented — if the API cannot, an API-scale episode loses voice
lock and the whole plan changes).

### Chip attach: the ⋮ menu is gone (2026-09-08, task-0793785a)

The "open the tile's more-options menu, click the inner label node, expect it to
work about once in fifteen tries" path no longer exists — an asset row is a bare
`<button class="asset-item" role="option">` with no nested menu button. **Single
-click the row; a preview pane opens to the right with its own full-width
`เพิ่มไปยังพรอมต์` button; click that.** Three attachments, three first-try
successes, including the voice preset. If a future session sees the ⋮ menu
again, both paths belong here — but do not spend a 7-fail streak hunting for a
menu that is not on screen.

A voice chip reports `disabled: false` as soon as two other ingredients sit
beside it, which is the practical confirmation that a voice is live for that
generation. Check it before firing.

### Measured on the account, 2026-09-08 (task-e3bf2fa9, read-only, 0 credits)

- **Voices is live on the PLUS tier.** The Add-ingredient picker's categories
  are ทั้งหมด · รูปภาพ · วิดีโอ · **เสียง** · ตัวละคร · รูปโปรไฟล์ · การอัปโหลด.
  No upgrade wall anywhere near it.
- **The model is called "Omni 1.1 Flash" in the UI**, not "Gemini Omni Flash
  1.1". It is the account default and reappears on every project reload, so a
  task that wants Veo must select Veo every time.
- **Omni Flash undercuts Veo 3.1 Fast**: 12 credits at 720p/8s against Veo's
  20, 15 at 720p/10s, and a 360p draft at 6 and 7. Ingredient chips and the
  เฟรม/องค์ประกอบ toggle are unchanged when it is selected.
- **The 30 presets carry written labels** — name plus "Male, gravelly, low
  pitch" and so on. Nobody has to listen to choose one. Pick from the label,
  record the name.
- **A voice attaches as a CHIP, not as text.** `เพิ่มไปยังพรอมต์` adds a
  `<flow-audio-ingredient-chip>` to the ingredient bar and leaves the prompt box
  untouched (its innerText still reads the placeholder). The chip is **inert on
  its own** — tooltip "องค์ประกอบเสียงต้องมีองค์ประกอบอื่นๆ จึงจะทำงานได้" — so a voice
  only works alongside a Character or other ingredient in the same generation.
- **The customize-performance path is dead on this account (2026-09-08).**
  Typing into `ปรับแต่งประสิทธิภาพ` removes `เพิ่มไปยังพรอมต์` and reveals a save
  flow: a name field pre-filled `"<Preset> คัสตอม"`, `รีเซ็ต`, and
  `บันทึกเสียงใหม่` — and that save button was found **permanently disabled**,
  across two characters, ~10 minutes of attempts, after editing the name, after
  previewing. `รีเซ็ต` reliably restores the working plain-preset flow. So:
  **attach the plain preset, and write the performance direction into the shot's
  own prompt text.** That is better anyway — the direction then lives in the
  script, under version control, instead of inside Google's account state.
  ⛔ **RETRACTED 2026-09-18 — this whole bullet was wrong.** The save works; the
  runs behind it all left `ตัวอย่างบทสนทนา` empty, which is mandatory even
  though the UI never says so. **Attaching a plain preset is still a perfectly
  good option**, and the direction-in-the-prompt technique is still correct and
  still lives in the script under version control. But it is a choice now, not a
  workaround for something broken. See the "Custom voices" section for the real
  procedure and for how four runs talked themselves into the opposite.
- **One "not found" is not proof a preset is gone.** A search for Algenib
  returned ไม่พบชิ้นงาน and the list skipped it alphabetically; a freshly opened
  picker minutes later showed it in place. Same `document.hidden` virtual-scroll
  trap. Reopen before concluding anything is missing.
- **Selecting a preset opens a panel, it does not attach immediately**:
  a preview button, `ตัวอย่างบทสนทนา` (example dialogue, maxlength 120),
  `ปรับแต่งประสิทธิภาพ` (customize performance, a free-text description with no
  DOM length cap), then `เพิ่มไปยังพรอมต์` (add to prompt). **There is no name
  field in the plain flow** (one appears only in the broken save flow above) — the voice is not a saved named object, it is
  text added to the prompt. So the durable artifact is the preset name plus the
  performance description, written into the script beside the APPEARANCE LOCK.
- **Long virtualized lists can be unreadable on winbox.** The tab reported
  `document.hidden === true` for a whole session on two different tabs, which
  froze `cdk-virtual-scroll-viewport` rendering (scrollTop and scrollIntoView
  did nothing) and made screenshots time out about half the time. The fix that
  works: use the panel's own search box, which substring-matches the full data
  set and re-renders regardless of scroll state.

## winbox findings 2026-09-07 (task-ef3995a1, first real shoot on Windows Chrome)

Measured on winbox; the rest of this skill was measured on the Mac. Full
report: `docs/reports/teaser-shoot-winbox-20260907.md`.

- **`resize_window` never takes effect on winbox** — innerWidth stayed 1920
  through repeated resize+navigate cycles. Screenshots cost 1.5–2.3k tokens
  each there, not ~800. Prefer JS reads over screenshots on that host.
- **Money buttons need a trusted click.** JS `element.click()` opens pickers
  and menus but did NOT fire เริ่มสร้าง (no card, no balance change). Submit
  with the `computer` tool's click, then confirm the balance moved.
- **An `@` eats typed text in ANY field, on any platform** — not just the
  ProseMirror composer. The @-autocomplete swallows the typing around the `@`:
  in the composer it drops everything after it, and in the plain `<input>` for
  a custom voice's name it dropped everything *before* it, leaving
  `@lung_somchai` out of `Algenib @lung_somchai` (task-36507a6a, Mac Chrome).
  Originally recorded as a ProseMirror/winbox trap; it is neither.
  For prompt text, place the caret at the end and use
  `document.execCommand('insertText', false, text)`, then verify `innerText`
  before submit. **But not in a form you intend to submit** — a programmatic
  write leaves an Angular form invalid (see the custom-voice status banner).
  There, type with real keys and dismiss the autocomplete with `Escape`.
- **Agent mode can be ON by default** (chip text exactly `Agent`,
  aria-pressed true). While on, the settings icon opens การตั้งค่า Agent, not
  the per-shot panel. Click the Agent chip off first.
- **Export hang can take 2 reloads / ~9 min.** And ดาวน์โหลดฉาก inside the
  Scenebuilder saves a direct `.mp4`, not the grid card's `.zip` — check
  Downloads for both.
- **A tab can collapse to 98x74 / hidden mid-session** and then time out on
  screenshots. Open a fresh tab, close the broken one, continue there.
- **Chip attach in องค์ประกอบ mode had a 7-fail streak** (coordinates verified
  each time, reload did not help). Budget for it: 3-chip shots took ~10 min
  each. Stop at 5 consecutive failures and reload the project, not the tab.
- **Plates must be 9:16.** A landscape start frame is padded with grey bars
  and the whole clip inherits them (shot 1). Check the plate's aspect in the
  รูปภาพ tab before binding it as เริ่ม.

### winbox, run 2 additions (task-5d0bd2fa, 2026-09-07)

Second shoot on the same box, 39 minutes for 4 clips against the first run's 76
for 4 — the findings above are what made the difference. Three more:

- **Never click at a `getBoundingClientRect()` coordinate on winbox.** The
  screenshot is scaled down from the real viewport by a ratio that changes with
  tab state (~0.688 one run, ~0.82 the next), so a DOM rect points somewhere
  else entirely. Click only at coordinates read off a fresh screenshot. On this
  box a `find()` ref click failed to toggle the Agent chip for the same reason;
  a pixel click at the chip worked. This is a better explanation of the run-1
  "money buttons need a trusted click" finding than trustedness is.
- **A download can silently walk to another clip.** Clicking download on a
  clip's edit page starts the preview playing, and Flow's own carousel can
  auto-advance to an unrelated clip mid-export; the export toast then belongs to
  whatever is now on screen. Re-check the page title against the intended shot
  right after clicking download, and re-navigate to `/edit/<id>` if it drifted.
- **Budget the export hang per download, not per session.** It hit all four
  downloads, 1-2 reload cycles each, worst case ~7 minutes.

**Verify grade, not just geometry.** Run 2's bonus re-fire of shot 1 against a
fresh 9:16 plate came back correct in every mechanical check the worker ran
(8.00 s, 720x1280, audio present, no padding) and still unusable: the clip is
black-and-white while the rest of the teaser is colour. A shot only passes if it
also matches the neighbouring shots' colour and grade, and a plate generated from
a prompt that does not pin the look will drift. Say the look in the plate prompt,
and compare frame 0 against a neighbouring shot before calling a re-fire good.

## ⛔ Chrome itself can block downloads, and it looks exactly like Flow being broken (2026-09-18, task-75926848)

A *different* failure from the CDN trap below, with an identical symptom: you
click download, nothing lands, no error anywhere.

After a handful of files in one session, Chrome trips its per-site
**"automatic downloads blocked"** permission for `flow.google.com`. Once it
trips, **every** download path dies at once — Flow's own per-tile button, a
blob anchor, a burst of anchors — and it **survives a full page reload**. On
task-75926848 it stopped an image harvest dead at 2 of 20.

**How to tell it apart from the CDN trap:** the CDN trap is video-only and the
CDN pull still works. This one kills image downloads too, and no page-side
method works, because the block is in the browser, not the page.

**The fix is a one-time human click and there is no way around it.** A person
clicks the blocked-downloads indicator in Chrome's address bar and chooses
*"Always allow multiple automatic downloads from flow.google.com"*. No agent
tool can reach it: `claude-in-chrome` only ever sees page content, and
computer-use holds browsers at read tier, so it cannot click browser chrome
either. **Do not build a workaround for this** — a local HTTP sink was tried on
that task and is exactly the kind of route-around a security permission that
does not get kept. Stop, say what click is needed, and hand it to the CEO.

Budget note: diagnosing this cost ~15 of that task's ~20 minutes. Recognise it
from the symptom — *several downloads worked, then all of them stopped* — and
stop immediately.

## The download button is dead — go straight to the CDN URL (2026-09-18, task-860620fc)

**On this account the toolbar download icon is a silent no-op.** Across roughly
six attempts in one session — ref-based clicks, DOM text-node clicks, and
coordinate clicks, including the resolution flyout (270p/720p/1080p/4K) —
**Chrome's own downloads history recorded zero entries.** No error, no toast, no
feedback of any kind.

This is **not** the documented "export hangs, reload and retry" trap. That one
at least shows `Exporting your scene…`. This shows nothing at all, which means
an operator can spend ten minutes believing a download is in flight when nothing
was ever started.

**Do not use the download button. Do this instead:**

1. Play the clip. Flow's own player fetches a signed CDN URL
   (`flow-content.google/video/<id>?...`).
2. `read_network_requests` to capture that URL.
3. `curl` it.
4. `ffprobe` the result to confirm it is the clip you wanted.

Verified byte-identical to what the player streams. Three clips pulled this way
on 2026-09-18 with no failures, against a download button that never produced a
single file.

## Chip attach is inconsistent, not fixed (correction to the 2026-09-08 note)

The 2026-09-08 entry says single-clicking an asset row opens a preview pane with
its own `เพิ่มไปยังพรอมต์` button, three first-try successes. **Both behaviours
occur, in the same session, on the same account:** the first attach of a session
on a fresh tab attached the chip immediately with no preview pane and no second
click; every attach after that opened the preview pane and needed the documented
second click.

So: **click the row, then look at what actually happened** rather than assuming
either path. Count the chips afterwards — the picker hides what is already
attached, so a successful attach is an item that has disappeared from the list.
Neither behaviour is a failure; assuming one of them is what cost time.

## Chrome tab-group destruction is routine when sessions share a browser

The tab group was destroyed three times in one session on 2026-09-18, with other
browser_operator and developer sessions live in the same Chrome. Each recovery
followed the existing protocol — fresh tab, re-navigate, re-verify composer state
from scratch — and none of them cost a generation. **Treat it as weather, not as
an incident**, but never assume composer state survived one.

## Prompt syntax: Omni is not Seedance — `<IMAGE_REF_N>` goes INSIDE the sentence (2026-09-18)

Three shots were fired on 2026-09-18 with chips correctly attached — Flow's own
post-hoc ingredient panel confirmed all of them, voice included — and the
character's face, hair and the entire location still drifted between shots.

The chips were never the problem. **The prompts were written in Seedance
grammar.** We wrote `@nong_daeng speaks in Thai` and attached chips without
telling the model what each one was for. Google's own Omni guide names that as
the common failure: *"uploading several references and assuming the model knows
which one controls the face, which one controls the outfit, which one controls
the scene."*

**Omni's documented convention is `<IMAGE_REF_N>` written inline, at the point in
the sentence where that subject is mentioned.** Google's own example:

```
"in the style of <IMAGE_REF_0> a woman <IMAGE_REF_1> is walking"
"[0-3s] Starting with woman <IMAGE_REF_0>, she is holding <IMAGE_REF_1>
 [3-6s] Then we see the man <IMAGE_REF_2>"
```

Four rules follow, and all four were being broken:

1. **`<IMAGE_REF_N>` is indexed by ATTACH ORDER.** Attach deliberately, in the
   order the prompt references them, and verify each one landed before the next.
2. **Say what each reference is for** — "use `<IMAGE_REF_0>` as the character
   reference for the face and hair, `<IMAGE_REF_1>` as the location reference for
   the interior and its layout."
3. **The chip is a hint, not a lock. Describe the appearance in text anyway** —
   hair length, clothing, build, the set's fixed features. The shot that came out
   right had a rich set description; the shot that drifted had a thin one, and
   neither described the character at all.
4. **Drop "No music."** Google's guide says describe what you want rather than
   instruct with negatives, and naming music invites it. Our prompts carried that
   line for months.

~~Up to 10 image references per generation~~ — **WRONG for the Flow UI, retracted
2026-09-18 (task-f0f67322, shot 46).** Ten is the Gemini API's ceiling. In this
Flow project the composer **silently disables the 4th ingredient chip**: it
renders as `chip-image-wrapper inactive` with a `disabled-error-icon` overlay,
no banner, no change to the chip count, and the picker still hides it as
"attached". A shot written for four references fires with three honoured and
one ignored, and nothing tells you which. **Plan every shot for at most three
chips: usually two characters and one location, or one character, one prop and
one location.** A fourth reference goes into the prompt as text, never as a chip. And *"attach everything before the first
generation, because adding references mid-conversation destabilizes a scene that
was holding together."*

## Custom voices — build one per character, off a base preset (CEO 2026-09-18)

> ✅ **This works. It took four runs to find out how, because three fields must
> be filled and only two of them look required.** Everything below was read off
> the CEO's own screen on 2026-09-18.
>
> ### Fill ALL THREE fields BEFORE pressing preview
>
> | field | what goes in it |
> |---|---|
> | `ตัวอย่างบทสนทนา` (example dialogue, `0/120`) | **MANDATORY, and nothing in the UI says so.** A real line the character speaks. This is the text the preview actually synthesises. **Leaving it empty is why four runs concluded the feature was broken.** |
> | `ปรับแต่งประสิทธิภาพ` (customize performance) | the voice description — **in English** |
> | `ชื่อของเสียง` | pre-filled `<Preset> คัสตอม`. Replace with `<base preset> @<handle>`, e.g. `Algenib @lung_somchai` |
>
> ### Then, and the order matters
>
> 1. Press **`แสดงตัวอย่าง`** — the big gradient tile.
> 2. Its icon goes **hourglass → play**. While the hourglass shows,
>    `บันทึกเสียงใหม่` is grey. When the play icon returns, **the save button
>    turns white and is clickable.** The button is a faithful mirror of the
>    preview state — it was never "hardcoded disabled", it was correctly
>    disabled for a form that was incomplete.
>
>    **Measured: ~18–20 s** (still disabled at a 10 s poll, enabled by 20 s, three
>    timed runs, 5/5 saved). **Do not wait a minute** — an earlier brief guessed
>    30–60 s from the CEO's description and a run burned 120–147 s per voice
>    proving nothing. The wait was never the problem; the empty field was.
> 3. Press **`บันทึกเสียงใหม่`**.
> 4. The saved voice appears as a **new row at the top of the preset list**, and
>    the button changes to **`เพิ่มลงในตัวละคร`**. Press that to bind it.
>    **Saving and binding are two separate steps** — a saved voice that was never
>    bound does nothing.
> 5. Reload and read the binding back. A voice that does not survive a reload did
>    not save.
>
> ### Two real bugs in this dialog, both measured
>
> - **`ชื่อของเสียง` defaults to the wrong preset.** With Umbriel selected it
>   pre-filled `Achernar คัสตอม` — Achernar being merely first alphabetically.
>   **Did NOT reproduce across 5 saves once all three fields were filled**, so it
>   may itself have been a symptom of the incomplete form rather than a separate
>   bug. Cheap either way: **always read the name field back before saving.**
> - **`Escape` closes the whole dialog**, not just the `@`-autocomplete popup.
>   Losing everything typed. Dismiss the autocomplete some other way.
> - **The MCP tab group can die mid-dialog** and take everything typed with it
>   (hit once on `@cop_wit`). Recover the documented way — fresh tab, re-navigate,
>   and **re-verify the character's bound voice from scratch** to confirm nothing
>   half-saved — then redo that voice. It worked on the second attempt.
>
> ### ⚠ How four runs got this wrong, so nobody repeats it
>
> Runs on 2026-09-08, task-36507a6a, task-881f8f0c and task-f7bb8a7b all left
> `ตัวอย่างบทสนทนา` empty — an early report had called it "optional, not
> required for preview or save state" and every later run inherited that line.
> With it empty the preview still appears to run and returns in ~18 s, so each
> run watched the icon, called it complete, found the save button disabled, and
> reported the feature dead. The last of them waited **120–147 seconds** to rule
> out a slow backend, which only made the wrong conclusion look better tested.
>
> The CTO then wrote "SETTLED: a custom voice CANNOT BE SAVED on this account"
> into this file, into a commit message, and told the CEO twice. **The CEO, who
> uses the feature, corrected it.** Three lessons, all cheap to apply:
>
> 1. **A first-hand user beats N runs of your own probe.** Their one real
>    observation outranks your instrument.
> 2. **"Optional" in an old report is a claim, not a fact.** This one was wrong
>    and propagated through four briefs unchallenged.
> 3. **Reproducing something four times proves nothing if all four share one
>    wrong assumption.** Vary the assumption, not the attempt.

The 30 presets are raw material, not the cast. Two of our men measured 148 and
150 Hz and read as the same person; the grandmother's preset reads decades too
young. The fix is Flow's own voice customisation, reached from the **character
page's `เลือกเสียง` flow**, not from the picker.

The path, as the CEO describes it:

1. Open the character → `เลือกเสียง`.
2. **Pick the base preset closest to the character** — do not wait to be told
   which; the C-level casts, and the base only has to be in the right register.
3. **Describe the voice in English, in detail**: age, build of the voice, pace,
   what it does under pressure, and what it must NOT sound like.
4. Press preview and **wait for the model to finish**.
5. **Name it `<base preset> @<character handle>`** — e.g. `Aoede @grandma_pranom`
   — so the origin is readable months later, and save.

Naming this way matters: the base is what you fall back to when a custom voice
drifts, and a bare nickname loses it.

**Separate the bands on purpose.** Cast the register first (low / mid / younger),
then let the description do the character work. Two characters in the same band
will read as one person however different the adjectives are.

## ⛔ A speaker whose face is not in frame gets a random voice (CEO 2026-09-18)

The CEO heard it first, on the grandmother scene: the grandson's chip was
attached, he spoke from off-frame, and the voice was not his. A pitch check on
all 38 Act 1 clips (median f0 per clip, grouped by scripted speaker) points the
same way:

| speaker | in-frame shots | off-frame / face-absent shots |
|---|---|---|
| ต้น (Iapetus, ~148 Hz) | 126–160 Hz | **28: 175 Hz · 31: 172 Hz** — both off-frame, both the two highest |
| สมชาย (Algenib, ~132 Hz) | 108–162 Hz | **9: 185 Hz** — only his hand and arm in frame when he speaks |
| วิทย์ (Achird, ~150 Hz) | 127–155 Hz | **39: 296 Hz** — his entrance, spoken while walking in from the street |

Hands-only shots where the body and apron were still in frame (7, 15, 35, 36,
47) held the right pitch — the model knows who is there. What breaks it is a
speaker the model cannot see.

**So the chip is necessary but not sufficient.** For a line to come out in the
bound voice:

1. the speaker's chip is attached, **and**
2. **the speaker's face is in frame while the line is spoken.**

Which is also what the 1.9M-view reference reel does on almost every shot: the
camera is on the face of whoever is talking. Off-frame dialogue, voice-over
across a cutaway, and "he calls from the next room" are not available in this
product. Write the shot so the camera is on the mouth.

## ⛔ A voice belongs to the CHARACTER, not to the shot (CEO 2026-09-18)

This is the step every worker so far has missed, and it invalidates the
"attach a voice chip per shot" habit written further up this file.

Open a character — click it in `ตัวละคร`, or in the media picker — and its own
page carries a **`เลือกเสียง`** button on the left, directly above the
`ข้อมูลตัวละคร (ไม่บังคับ)` box. Pick a voice there and it is **bound to that
character permanently**:

```
before:   [  ♪) เลือกเสียง                        ]
after:    [ (♪) algieba            ▶   นำออก      ]
```

`นำออก` removes it. `▶` plays the sample. That is the whole control.

### Binding a voice does NOT make the character talk (tested 2026-09-18)

The obvious fear, and the CEO's own first hypothesis: a character carrying a
voice will be *made* to speak whenever it is on screen, even with no dialogue
written. **Tested and false.** A voice-bound `@lung_somchai` in a prompt that
described him working in silence stayed silent.

The rule the test actually produced is bigger than the question it answered:

> **The model follows the prompt. Write the prompt strongly enough and it obeys.**

So binding voices costs nothing in scenes where nobody speaks. There is no need
for a second, voiceless copy of any character.

### Why this matters more than it looks

**A shot with two people talking cannot be solved with voice chips.** One voice
chip in a prompt is one voice for the generation — it cannot tell the father
from the son. Bind the voice to the character and the model knows which mouth
each voice belongs to, however many characters are in frame. Any scene with
more than one speaker REQUIRES this path.

### The rules that follow

1. **Bind the voice at character-creation time, before any shot is fired.** It
   is part of building the character, like the reference image — not part of
   setting up a generation.
2. **Verify it from the picker, not from memory.** Selecting a character in the
   media picker shows its bound voice in the preview pane, with its own `▶`.
   A character whose preview pane shows no voice row has no voice bound, no
   matter what any report claims.
3. **The character page also has a free-text `ข้อมูลตัวละคร` box** —
   "อธิบายบุคลิกของตัวละคร…". Flow's own hint says Agent Flow uses it to help
   build scenes with that character. Put the APPEARANCE LOCK's personality
   line there.
4. `เสร็จสิ้น` (top right) commits the character page.

## ⛔ `<IMAGE_REF_N>` is numbered by ADD ORDER — and the UI will not tell you (CEO 2026-09-18)

The numbering is positional and starts at zero:

```
the 1st chip you add  ->  <IMAGE_REF_0>
the 2nd chip you add  ->  <IMAGE_REF_1>
the 3rd chip you add  ->  <IMAGE_REF_2>
```

### How a chip is added

`+` in the composer → the media picker opens with its own tabs
(`ทั้งหมด · รูปภาพ · วิดีโอ · เสียง · ตัวละคร · รูปโปรไฟล์ · การอัปโหลด`) →
click the **row** → the preview pane fills on the right → press the white
**`เพิ่มไปยังพรอมต์`** button at the bottom of that pane.

Added chips appear as small thumbnails in a row above the prompt text. **That
row is the index.** Leftmost is `<IMAGE_REF_0>`.

### The trap, demonstrated by the CEO's own screen

The thumbnail row showed, left to right: the **shop interior**, then the
**young man**. The prompt read:

```
Use <IMAGE_REF_0> as the character reference for the young man's face and hair.
Use <IMAGE_REF_1> as the location reference for the shop interior and its …
```

So `<IMAGE_REF_0>` pointed at the location and `<IMAGE_REF_1>` at the person —
**both references inverted**, while the chip count, the chip types and the
prompt's own wording all look perfectly correct. Nothing in the UI flags it.
The face drifts and the set drifts and every check still passes. This is the
same class of silent failure as binding a chip by its row label.

### The rule

**Decide the order first, add in that order, then write the prompt to match —
and re-read the thumbnail row against the prompt before Submit.**

The thumbnail row is the only evidence of the mapping. Reading the prompt back
proves nothing: the prompt is what you *believe*, the row is what is *true*.

## The APPEARANCE LOCK is the ground truth, not the neighbouring shot

When three shots disagree, "which one is wrong" is unanswerable by comparing them
to each other — there is no reference among them. The script's `APPEARANCE LOCK`
line for that character IS the reference. Check each shot against that text, item
by item (apron colour, whether it is over or under the shirt, hair, stubble,
watch, which wrist), and the answer is a count, not an opinion.

This costs nothing and can be run retroactively on every clip ever shot.

## Voice: the API cannot do it at all, so Flow's UI is the only path

`gemini-omni-1.1-flash` went GA on 2026-08-27 and its documentation states
**"Uploading audio references is unsupported"** and **"Voice editing is not
supported."** The API does accept `<IMAGE_REF_N>`, `<FIRST_FRAME>` and
`<LAST_FRAME>` together, which the Flow UI refuses to do — so the trade is real
and it cuts both ways:

| | face + set lock together | voice lock |
|---|---|---|
| Flow UI | no — `เฟรม` and `องค์ประกอบ` are mutually exclusive | yes, via the chip |
| Gemini API | **yes** | **no, documented as unsupported** |

A dialogue-driven series therefore cannot use the API for its speaking shots, and
cannot frame-lock them in Flow. If voice lock turns out unreliable in practice,
the better architecture is silent generation with frame lock plus a TTS voice we
own — which locks the voice completely instead of steering it.

### Price, for the same model, measured 2026-09-18

| route | per second of finished video |
|---|---|
| Flow on Ultra (฿3,500 / 10,000 credits, Omni at 1.5 cr/s) | **฿0.53** |
| Flow on Pro (฿750 / 1,000 credits) | ฿1.13 |
| Gemini Omni API, 720p | $0.10 ≈ **฿3.50** |

**The subscription is several times cheaper than the API for the same model.**
Going API-first is a capability decision (frame lock), never a cost one.

## Thai text: the IMAGE model can write, the VIDEO model is unproven (2026-09-18)

**Corrected the same day it was written.** The first version of this section said
flatly that the model cannot write Thai. That is wrong for stills, and the CEO
caught it by reading a plate off his own screen.

### What Nano Banana Pro actually does with Thai

Measured on `@street_front`, a Bangkok street plate:

| element | result |
|---|---|
| the large central shop sign `ก๋วยเตี๋ยว - เครื่องดื่ม` | **correct and fully legible** |
| the second sign, a shop name | name right, the tail of the phrase drifts |
| every small distant sign | Thai-shaped, reads as nonsense |

The pattern is consistent and useful: **the model gets ONE short, prominent,
common phrase right, and degrades into convincing gibberish for everything
smaller or further away.**

That failure is not a problem in itself — real signage at that distance is
unreadable anyway, so the gibberish is set dressing doing its job. It only
matters when a viewer is meant to *read* something.

### So the rule is now

1. **Thai text in a still plate is a real tool. Use it.** Shop signs, menu
   boards, a price list on the wall — they make the world specific in a way a
   description cannot. Generate them in the plate, not in the shot.
2. **Whatever must be readable gets ONE short common phrase, placed prominently**,
   and is verified by actually reading it back off the generated image. Never
   assume; look.
3. **Anything smaller is decoration.** Do not fight it, do not re-fire for it.
4. **SETTLED, in two runs. Quote the words and you get them.**

   *task-6403cbb4:* `@street_front` carries a legible `ก๋วยเตี๋ยว - เครื่องดื่ม`.
   A clip generated with that plate attached, in a prompt that never named the
   sign's words, came back with Thai-shaped nonsense on the **first frame** —
   not a degraded version of the plate's text, a different invented string, and
   a different one again by the last frame.

   *task-115ae41c:* the same plate, the same mode, the same everything — except
   the prompt now said the sign reads exactly `"ก๋วยเตี๋ยว - เครื่องดื่ม"`, in
   quotation marks. Frame 0 and t=7.0s both came back **correct, every
   consonant, vowel and tone mark clean.** The final frame lost the top of the
   glyphs only because the push-in had physically carried the sign's top edge
   out of frame — cropped, not garbled.

   **The mechanism is the same rule as everything else here: Omni does not copy
   the plate's pixels, it re-renders the scene. An unnamed sign is a sign the
   model invents. A named one is a sign it writes.**

   So Thai signage inside a shot is **available**, on three conditions:
   - **the exact words are in the prompt, in quotation marks**
   - **the sign stays inside frame for as long as it must be read** — a push-in
     that crops it is a composition problem, not a model problem
   - **you verify by reading the rendered frame**, never by assuming

   No caption or subtitle side effect appeared from the quotes. Google's older
   Veo guidance warned that quotation marks get rendered as on-screen text;
   that did not fire in this Omni 1.1 Flash / องค์ประกอบ configuration. One
   clip, so treat it as a data point rather than a settled rule.

5. **Numbers a plot turns on stay in the dialogue.** Amounts, dates, counts. Not
   because the model cannot draw them but because a spoken number cannot warp,
   cannot be missed by a viewer scrolling with sound on and no attention, and
   costs nothing to re-fire. This one is a story rule, not a model limitation —
   see `thai-moral-drama`.

### Settled, and what it cost

12 credits across two runs. The first proved an unnamed sign is invented; the
second proved a named one is written correctly. Rule 4 above carries both.

## The set drifts exactly as much as the face does, and for the same reason (2026-09-18, Act 1 shoot)

First 15 shots of «บัญชี» Act 1, checked frame by frame:

| what drifted | count | why |
|---|---|---|
| a character's face | **0** | every prompt carried the full appearance block |
| the **set**, same location chip, adjacent shots | 1 (bedroom: plaster+lamp+grey blanket → concrete+beams+bulb+red plaid) | the location got 5–6 words, different ones each shot |
| a character's **posture** | 1 (bedridden grandmother sat up on the bed edge) | the shot never restated "lying propped on pillows" |
| an accessory the plate does not have | 1 (glasses) | nothing said "no glasses" |
| a prop the story forbids | 1 (a ledger and pen under the hands of a man who never writes anything down) | "counting money" let the model add what counting usually needs |

Same rule every time — **what the prompt does not say, the model decides** — but
the shoot proved it applies with equal force to the set, the posture and the
props, not only to the face. Writing the face out in full every shot worked
perfectly. Writing the location out in six words did not.

### So: three fixed blocks, pasted verbatim into every shot that uses them

- **SET BLOCK** per location — walls, light source, bedding, furniture, window.
  Identical text in every shot in that room. Not paraphrased, not shortened.
- **POSTURE BLOCK** per character whose body state is part of the story —
  "lying propped on two pillows, nasal cannula over her ears" in every
  grandmother shot until the episode's epilogue changes it.
- **NOT-LIST** per scene — the things the model reaches for and must not:
  `no glasses` on the grandmother, `no notebook, no pen, no paper` wherever
  money is counted, `no readable text` on anything the audience must not read.

A shot sheet whose location line is shorter than its character line is a shot
sheet that will drift.

## ⛔ Verify a chip by its THUMBNAIL, never by its row label (2026-09-18, task-8ea0576a)

**Flow tags the location plate as `ตัวละคร` (character) in this project.** All
three of `@nong_daeng`, `@lung_somchai` and `@noodle_shop` carry the identical
category label in the `+` picker, and the composer's ingredient panel exposes
**no `@handle` name anywhere in its DOM** — every character icon carries only the
generic `alt="รูปภาพองค์ประกอบตัวละคร"`.

So a natural-language or label-based click picks the wrong asset **silently**.
Measured: a `find()` match for "the @nong_daeng row" attached the **noodle-shop
interior plate** instead, and every check that had been trusted up to that point
still passed — the chip count was right, the type was right, the picker-exclusion
was right. Only zooming into the chip's thumbnail showed it was the wrong image.

**This almost certainly explains the character drift blamed on prompt syntax.**
An earlier shoot verified its chips by count and type, reported "3 chips, matches
the script exactly", and came back with the wrong character in the wrong shop.
Its own report had already admitted the limit — *"the DOM count check only proves
type and count, not which character"* — and nobody acted on that sentence.

### The rule

1. **Use the picker's search box**, not a label match or a natural-language row
   reference. Type the handle.
2. **Look at the preview image before you click add**, and at the chip's
   thumbnail after. Zoom if the thumbnail is small. A face must look like a face,
   a location like a location.
3. **Then** confirm picker-exclusion (the item disappears from the list).
4. Record the attach ORDER, because `<IMAGE_REF_N>` is indexed by it.

Count, type and exclusion together still do not tell you *which* asset bound.
Only the image does.

### Both, every time

Write the prompt in Omni grammar **and** verify every chip by its thumbnail.
Neither replaces the other. Both are free.

## Field notes

- 2026-09-22 [WRONG] §Which things get a chip — `build_shotsheet.py` refused a 4th chip with the comment "the 4th is silently disabled". Never sourced, and contradicted by this file's own Ultra audit (task-68653632, 2026-09-18) recording a reference-chip cap of 10. A dry run against the live UI returned `chips=['@jae_muay','@lung_somchai','@noodle_shop','@money_fold'] prompt_verified=True`. On the strength of that comment I had already proposed dropping a location chip to fit the money in — a real loss of quality to satisfy a limit that did not exist. Cap raised to 10, with the audit cited beside it. · evidence: task-68653632 / f563c707 / tools/build_shotsheet.py · status: promoted
- 2026-09-22 [COSTLY] §A prohibition is not an inventory — automated "shot declares X therefore attach X's Element", keyed off `NOT["money"]`. That key is a prohibition ("…also no notebook, no pen, no paper, no ledger of any kind") carried by 22 shots, most with no money in frame. Caught by shooting shot 133 at 360p (4 credits): two people looking at empty tables. Reverted the same day. Cost would have been banknotes inserted into 22 scenes written to be empty of them. · evidence: f563c707 / tools/build_shotsheet.py · status: rejected
- 2026-09-22 [MISSING] §Anything that must look a specific way needs an Element — six Act 3 clips rendered a real Thai 500-baht note with the royal portrait, in a drama about illegal moneylending, against 40 words of prompt forbidding exactly that. The project's 3 characters and 6 locations were correct across 148 clips because each is chip-bound; the money was the one thing described rather than referenced. Five of the six prop Elements in the project had never been attached to any shot. · evidence: task-e960f3ca / 3f57cd1e / docs/scripts/banchi-ACT1.data.py · status: promoted
- 2026-09-22 [MISSING] §time of day — the word `night` appended to a 60-word description of a lit, open, busy shop produced daylight in all 71 clips shot to that point. Every automated check passed; a frame-0 look found it in seconds. CEO ruled the film stays daylight rather than re-shoot. · evidence: LungNote 87c9507d / docs/scripts/banchi-ACT5.md · status: pending
- 2026-09-23 [WRONG] §Never diagnose audio you have not read back — spent an evening attributing a dialogue defect to prompt structure using `silencedetect` (where sound is, not what it is). Rewrote the sheet builder, fired five paid proof shots chosen from a text analysis, and contradicted the published Veo guidance, all before transcribing a single clip. faster-whisper was already installed: 3s per clip settled it. The real defect was the script telling a character to say "208 งวด" then "208" in a four-second shot. · evidence: research/veo-dialogue-repeats.md / tools/film_transcript.py · status: promoted
- 2026-09-23 [SUPERSEDED] §Every shoot ends with a mechanical audit — (was MISSING; the count was 3 not 14, see the WRONG note below) 14 of 173 finished shots carried Thai captions Veo invented and mangled; found by the CEO watching, not by any check. A crop-and-OCR scan (bottom 18%, 4 frames a clip, tesseract) found all 14 in two minutes. Shot 43 had already been re-fired for this defect and came back with different garbage, so re-fires need re-scanning. · evidence: tools/burned_text_scan.py · status: promoted
- 2026-09-23 [WRONG] §Every shoot ends with a mechanical audit — the OCR scan's "14 of 173" was 3 of 173 (29, 43, 115): 11 hits were texture (floral nightgown, table grain, apron, stair treads) and 115 was missed by 4-samples-a-clip. Replaced by a pixel gate (white glyph beside black outline, 360×80 band, 2 fps; real 160–326 vs texture ≤38, gate 80), calibrated on one contact sheet of known hits. Free fix: crop top 80% and scale back — 0 credits instead of ~180 for re-fires. · evidence: session cto-8c06958c, tools/burned_text_scan.py · status: promoted
- 2026-09-23 [COSTLY] §zero-model runner — on the Mac, bare `python3` has no playwright: `tools/flow_shoot.py run` logs "cannot attach … ModuleNotFoundError('No module named playwright')" and returns 1, which reads like Chrome being down. Run it as `/Users/gob/Projects/Agents/.venv/bin/python tools/flow_shoot.py …`. Also: a wrapper ending in `; echo EXIT=$?` makes the background task report exit 0 — read the EXIT line, not the task status. · evidence: session cto-8c06958c refire 106/122 02:46 · status: pending
- 2026-09-23 [WRONG] §Chrome itself can block downloads — task-f78ca70e measured the block as a per-tab allowance (one silent download per fresh tab, >20 files, no human click) and rewrote scripts/browser/banchi-plates-download.js to open one fresh tab per file. CTO: NOT promoted — it conflicts with this section's own "do not build a workaround" rule for a browser security permission; the CEO rules whether one-tab-per-file is acceptable or whether the one-time "Always allow" click stays the method. Until then the section stands. · evidence: task-f78ca70e, merge 381687ba · status: pending
- 2026-09-23 [MISSING] §assets — a plain Flow image generation can be renamed (tile right-click → เปลี่ยนชื่อ) into a named asset the + picker finds by search; it lands in the รูปภาพ category, never ตัวละคร, and there is no convert action. Picker rows for such assets show the name without "@", so flow_shoot's row match must not require it (fixed cdb27f9f). · evidence: task-f78ca70e, @cop_wit_uniform_A · status: pending
- 2026-09-23 [WRONG] §zero-model runner — attach_chip matched picker rows by substring, so "@cop_wit" also matched "@cop_wit_uniform_A" and "@noodle_shop" matched "@noodle_shop_thriving"; .first picked either, and the chip-COUNT gate cannot see a wrong-but-present chip. Now word-bounded (picker_row_pattern). Whether any Act 1–6 shop shot got the thriving-shop plate is unchecked. · evidence: cdb27f9f on agent/codex-winbox-runner · status: pending
- 2026-09-23 [MISSING] §references — shot 106 drifted ต้น's hair (longer, fringe forward) in BOTH takes, on two different runners, with prompt text identical to 105 except framing. Pattern: close-up + ต้น as REF_1 + his face in profile. 107 (same close-up framing, same room, same two men) held the plate with ต้น as REF_0 facing camera; shot 22 (the only other close-up with him as REF_1) pushed him to the frame edge. Hypothesis n=3: in a close-up the second reference holds weaker, and a face seen only in profile has its hair invented from a frontal plate. Test: 106 take 3 with ต้น REF_0 facing camera. · evidence: session cto-8c06958c, ACT4 106 · status: pending
- 2026-09-23 [WRONG] §Every shoot ends with a mechanical audit — NOT["nosubs"] ("No subtitles, no captions…") + rewriting the line as spoken aloud did NOT stop shot 43 captioning: 3 of 3 takes captioned. It held on 29 and 115 (n=2 clean), so the negative is not a fix for a shot that keeps doing it — crop it (0 cr) after the second captioned take instead of paying for a third. · evidence: session cto-8c06958c, ACT2 43 take 3 04:0x, burned_text_scan score 286 · status: pending
