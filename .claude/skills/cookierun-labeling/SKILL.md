---
owner: CTO
created_by: human
origin: mooniex-org
name: cookierun-labeling
description: >-
  How to label frames and train the Cookie Run obstacle detector without
  repeating the mistakes of 2026-09-02 (owned by CTO). Read this before
  labelling a Cookie Run frame, building a training set, choosing classes, or
  launching a detector train run. It is the hard-won reasoning — what counts as
  each class, how to draw a box, why auto-labels are untrustworthy, why tiny
  datasets break training, and the train/eval/deploy gate. Trigger on any task
  about labelling Cookie Run frames, the label studio (vision/label_tool.py),
  the obstacle detector, or retraining it. The mechanics live in
  cookierun-bot/vision/; this is the what/why.
metadata:
  owner: CTO
  created: 2026-09-02
---

# Cookie Run obstacle-detector labelling & training doctrine

The bot avoids obstacles by (a) following the **jelly line** — jellies mark the
safe path and are found by a **colour rule**, not the model — and (b) a **model**
that detects the hazards themselves. This skill is about that model: the labels
that teach it and the training that must not make it worse.

## Classes — by FUNCTION, not art

- **spike** — anything sitting on the GROUND that hurts → the planner JUMPS it
  (pumpkins in EP1, flaming pillars / fire pits in EP3). All one class.
- **hang** — anything hanging from the CEILING → the planner SLIDES under it
  (the fork-and-pancakes). All one class.
- **line** — the route markers: jellies, coins, HP potions. One class, because
  they share a FUNCTION (they mark where to run) and a run will happily swap
  jellies for coins on the same path. Split coin out only when something
  downstream actually needs the distinction.

  **Superseded 2026-09-04:** this used to read "NOT the model's job, the colour
  rule already finds them". Measured against the CEO's 111 hand-drawn boxes,
  the colour rule found **32%** of them with a 23.5 px centre error, because it
  gated on saturation — and inside a real jelly the median S is 111 while the
  BACKGROUND sits at 146. Brightness is the separator (jelly V 223 vs
  background 86). Retuned to `S>=0, V>=170, area 800-9000` it reaches 83% and
  8.5 px, which is good enough to PROPOSE boxes for a human to confirm but not
  to label unattended: it cannot tell a jelly from a coin or an HP potion, and
  it fires on the HUD avatar and bright walls. Hence the model.

Prefer **the fewest classes that solve the problem** — the CEO's rule
(2026-09-02): one object class is far easier to debug than two or three, because
a miss is unambiguous (saw it / didn't) with no class confusion. Only split a
class (e.g. coin out of jelly) when a downstream decision actually needs it, and
only after there are enough examples of the new class (tens of boxes minimum).

## How to draw a box

- **One box per object.** Three touching jellies = three boxes, not one long
  box. A long box teaches "the object is a bar" and the model then draws one
  giant box over every row.
- **Box the VISIBLE part.** A half-hidden object gets a half box. Be consistent
  — always visible-only, never sometimes-whole.
- **Exclude the HUD.** A hanging fork whose stem runs up behind the HP bar / the
  score / the BONUSTIME text: box only the part BELOW the HUD, down to the
  lowest tip. Including the HP bar teaches "obstacle = has an HP bar" and the
  model then fires on the HUD every frame. The low tip is what collides anyway.
- **Box the distinctive + collision-relevant part.** The fork tines + pancakes,
  not a plain grey bar. Overlapping boxes are fine (NMS handles them at play).

## Real object vs background — the CEO's discriminator (2026-09-02)

The single best test for "is this a real object or a background false positive":

- **A real game object (jelly, coin, spike, fork) has a bold, dark OUTLINE and
  saturated fill.** Cookie Run draws every interactive sprite with a heavy dark
  border. If a candidate box has that crisp dark edge around a bright/saturated
  shape, it is real.
- **Background decorations are washed out — faded colour, low saturation, and
  NO dark outline.** A potion bottle on a back shelf, a wall carving, a
  spiderweb in a menu corner: the model boxed these as "hang 0.49 / 0.94" but
  they are scenery. Reject them.

So a detection is trusted when it has (a) a strong edge/gradient along the box
border AND (b) high interior saturation; it is a background false positive when
the border is soft and the fill is desaturated. This is checkable by eye and by
code (Sobel edge magnitude on the border ring + mean HSV saturation inside), and
it is the cheapest way to clean the model's pre-labels before a human ever looks.

Measured 2026-09-02, this separates cleanly: a real pumpkin box read border-edge
(mean Sobel magnitude) **144** and interior saturation **174**; a menu spiderweb
the model wrongly boxed read edge **26**, sat **106**. A working reject rule is
**edge >= 60 AND saturation >= 130** — keep boxes above both, drop the rest as
background. Re-check these thresholds on a handful of frames per new theme.

## Confirmed by 44 CEO reviews (2026-09-02, the /review queue)

- **The edge/sat rule holds.** The CEO agreed with essentially every verdict it
  produced — every "background" reject (edge ~19-46, sat ~68-75) and every
  "real object" keep (edge ~85-140, sat ~142-179). Keep using it.
- **ONE false reject to respect:** a hang box at edge 33 / sat 75 was judged
  REAL by the CEO even though the rule rejected it. The rule is a strong prior,
  not a law — when a detection sits at a known obstacle position with a familiar
  silhouette, the human still overrules the numbers. Send borderline cases to
  the human rather than auto-dropping them.
- **THE MODEL'S HANG BOXES ARE SYSTEMATICALLY TOO SMALL AND TOO HIGH.** Across
  10 independent corrections the CEO redrew them almost identically:
  **width x1.70, height x1.38, centre moved DOWN by ~0.098** (the top edge stays,
  the bottom extends to ~0.72 of frame height). The model boxes only the fork
  STEM; the correct box also covers **the pancakes hanging below it — the part
  that actually hits the cookie's head.** Any hang label taken from the model
  must be widened and extended downward before training, or the planner ducks
  too late.
- **Spike boxes need no correction** — every pumpkin box (edge 137-140,
  sat 145-155) was accepted exactly as drawn.

## The two-variant fork — and why a blanket correction is wrong (69 reviews)

After the first batch I applied the hang correction to EVERY hang box. The CEO
overruled that **14 times** with one reason:

> "ส้อมน่าจะมี 2 ขนาด แบบที่มีของเสียบอยู่ อีกแบบไม่มี อันนี้เป็นแบบที่ไม่มีของเสียบ"
> (the fork comes in two sizes: one with food skewered on it, one bare — this is the bare one)

**The hanging fork has TWO variants and they need DIFFERENT boxes:**
- **Fork WITH food on it (the pancakes):** the box must extend DOWN to cover the
  food, because the food is the lowest part and it is what hits the head.
- **BARE fork (nothing skewered):** the box is SHORTER — the fork only. The CEO
  shrank my over-extended boxes back (height 0.97 -> 0.74, centre 0.46 -> 0.34).

**Lesson bigger than the fork: never apply a measured correction blanket across a
class.** A correction learned from one variant silently corrupts the other. Before
generalising a box fix, check whether the class actually has sub-variants; if it
does, either detect which variant a box is (is there food below the tines?) or
send both kinds to the human rather than guessing.

Also re-confirmed in this batch: every low edge/sat rejection was agreed (the
rule holds), and spikes were accepted across a wide range — including at
confidence as low as **0.23** and saturation as high as **221** — so a low
confidence score alone is not a reason to drop a spike.

Two more rules that fell out of the same batch:
- **Low confidence (~0.5 or below) skews toward background false positives.**
  Trust high-confidence obstacle boxes; scrutinise low-confidence ones with the
  outline test.
- **Non-gameplay frames must be excluded entirely.** Menu / leaderboard /
  "unknown" captures are not gameplay; the model false-fires on their
  decorations. Keep only real in-run frames in the set.

## Data quality — the mistakes that cost 2026-09-02

- **Auto-labels are not to be trusted.** Colour template-matching at >=0.62
  boxed forks, pink pigs and background as "jelly"; harvested "templates" were
  half junk (fences, empty background). Later, matching the CEO's clean pumpkin
  crops back across frames was **useless**: 0.60 flooded false positives, 0.72
  matched nothing. Template propagation does NOT scale a human's few labels into
  many good ones. The human's eye is the ground truth; a matcher is not.
- **Console-window contamination.** Frames captured while a black console sat
  over the game carry a big flat dark rectangle. They (1) hide real objects and
  (2) make the auto-labeller box the console edge. Filter them out — detect a
  large, near-uniform, rectangular dark region (NOT just darkness; EP1 night and
  EP3 lava are legitimately dark). `contaminated()` in vision/label_tool.py.
- **Tiny datasets BREAK training.** Two retrains on ~30-35 frames both came out
  WORSE than the existing model: confidence collapsed to <0.1, so at a usable
  conf (0.35) the new model detected ZERO — while the OLD model detected 49 of
  52 pumpkins (94%). A few dozen frames is not "a little better", it is a
  regression. Need HUNDREDS of clean labelled frames before a retrain can win.
- **Resolution must match play.** Training frames were half-res (790 px) while
  the bot plays at full-res (1580 px), so objects appear half the trained size
  at play time. Capture and train at the resolution the bot actually sees.
- **Don't retrain what already works.** The old 3-class model already detects
  EP1 pumpkins at 94%. EP1 obstacle detection was never the problem — the hits
  came from jelly-line timing / world-speed. Spend labels where the model
  actually fails (found by the live loop below), not on what it already knows.

## Generalising to a new obstacle (CEO, 2026-09-03)

EP1 alone has 15+ stages and stage 1's object list is nowhere near complete, so
new obstacle types keep arriving. The point of this skill is that **each new one
costs less than the last.** What carries over unchanged:

- the pipeline: dedup → model proposes → edge/sat filter → human reviews only
  the borderline cases → learn → retrain → gate;
- the **real-object vs background discriminator** (bold dark outline + saturated
  fill) — it is about how Cookie Run DRAWS interactive sprites, not about any
  particular sprite, so it transfers to every skin;
- the box rules (one per object, visible part only, exclude the HUD, box the
  collision-relevant part);
- every failure mode: contamination, inconsistent labels, tiny-data collapse.

What must be relearned per object, and only this:

1. **The skin** — the model has to SEE examples of the new artwork; nothing
   substitutes for that.
2. **The box proportion** — how wide and how far down the box should reach. Ten
   to twenty human corrections is enough to measure it (the fork gave a clean
   width x1.70 from ten), then apply it to the rest.
3. **Whether it has variants** — CHECK THIS FIRST, before generalising any
   proportion. The fork taught that the hard way: with food skewered vs bare
   needed different heights, and one blanket ratio corrupted the other variant
   and collapsed a whole training run.

So the per-object recipe is: collect frames with it → have the human confirm and
redraw ~10-20 → ask "does this thing come in more than one shape?" → measure the
proportion per variant → apply to the archive → retrain → gate. The human's time
per new object should fall each round; if it is not falling, the pipeline is
asking about things the model already knows.

## Training recipe

- Train on **RunPod only** (CEO 2026-09-02) — `vision/runpod_train.py run`.
  ~$0.02-0.04 a run, auto-terminates the pod on every exit path. Never train on
  the Mac (disk) or the Windows box (it is the game machine).
- Fine-tune from the **generic `yolov8n.pt`** base, not from a previous
  cookie model — starting from a jelly-biased model made spike confidence
  collapse. Enough epochs (>=40).
- **Always eval before deploy.** Val mAP on a 5-frame set is noisy and can read
  0.96 while the model detects 0 in practice. The real gate is: run BOTH the old
  and the candidate on the same real frames and count detections at conf 0.35.
  A candidate replaces the deployed model only if it detects MORE, not fewer.

## The active-learning loop (what actually improves it)

1. Train → **eval on real frames**: does it detect MORE than the current model?
   If no → keep the old model, do not deploy.
2. If yes → run the bot live → until it HITS something.
3. The HIT frame is the lesson: label THAT (the obstacle it missed), not frames
   the model already handles. Queue it for the human as one card: "is this
   right? keep / reject / fix." (vision/label_tool.py card mode at localhost.)
4. Human answers when free → add to the training set → retrain → back to 1.

The human labels only the genuine failures the loop surfaces; the model
pre-draws so the human confirms rather than draws from scratch; and the eval
gate stops a bad retrain from ever shipping. Scaling to hundreds of frames is
only worth it once the labels are clean and the gate is in place — accuracy
first, volume second.

## Measuring the cookie's own physics (2026-09-03)

Detection was never the blocker — the planner was, and it was running on four
guessed numbers that were all short. Measured values now live in
`cookierun-bot/vision/jumpmodel.py`; its docstring carries the method. What
generalises beyond this game:

- **Check the STATE before you believe a measurement.** Three separate attempts
  were thrown away because the capture landed in BONUSTIME or a pet party,
  where the cookie flies and normal physics do not apply. On a high-level
  account those states are frequent, so gate the capture: only fire while the
  bonus banner is dim, and print the state value with every burst so a bad one
  is obvious afterwards rather than silently averaged in.
- **Measure by what does NOT move.** The whole world scrolls at one rate; the
  player sprite is the single thing holding station. That is the cleanest
  discriminator for finding it, and it beats colour or blob rules that keep
  locking onto jellies. Scroll rate itself comes from `cv2.phaseCorrelate` on
  consecutive frames, not feature matching — tiled scenery aliases.
- **Track the part that is rigid, then verify the part that collides.** The head
  template tracks well; the feet are what hits. Check once, by eye, that they
  rise by the same amount (they did: 230 vs 228 px). Do not assume it.
- **Buffer frames in RAM, write them after.** Writing a JPEG per frame during
  capture stretched the sampling gap from 17 ms to ~290 ms and destroyed three
  runs before anyone noticed.
- **Two identical runs mean a TABLE, not a fit.** Both single jumps matched at
  every sampled millisecond, so the game is deterministic and a measured lookup
  is strictly better than a fitted parabola. It also captures behaviour a
  parabola cannot: the double jump hovers near its apex, so any ballistic model
  that reproduces its airtime overshoots its height by ~90 px.
- **State every pixel figure in ONE reference resolution.** Review images are
  saved at half size; an unscaled guide drawn on them is twice as long as the
  real jump. Same failure as training on half-res frames — see the data-quality
  section above.
- **A guide must never show a motion the game does not make.** Frames where the
  tracker slipped and read a sudden mid-flight drop were removed from the table:
  a false dip reads as "it falls here" and teaches the wrong jump point.

## Measure the sight, not the aim (2026-09-03)

Two days went into the planner and the physics. Both were genuinely wrong and
both were fixed and verified. Neither reduced collisions, because neither was
the reason for them.

The measurement that settled it: `play()` now keeps a rolling second of
full-resolution frames and dumps it at 50 ms steps whenever the HP drops
(`PRE_*.jpg` + `precrash.json` in the run's debug dir; the /hits page in
vision/label_tool.py steps through them). Re-running the detector over those
frames gave the answer in one pass -- **in 4 of 6 collisions it returned ZERO
boxes for the entire second before impact**, and in a fifth it saw something
in 1 frame of 15.

The bot was not mistiming jumps over obstacles it could see. It was running
into obstacles it never saw, in a stage whose spikes are not the EP1 pumpkins
the model was trained on.

The general rule this earns:

- **Before tuning a control loop, prove the loop can SEE its input.** A planner
  fed an empty obstacle list behaves exactly like a planner with bad timing:
  it runs straight into things. The two are indistinguishable from the outcome
  alone, and only distinguishable by replaying the detector on the frames
  leading up to the failure.
- **Capture the window before the failure, not the failure.** Event-triggered
  debug snapshots (only on a decision CHANGE) miss it entirely -- they fired
  about once a second, and the interesting window is 300 ms wide.
- **Store those frames at the resolution the bot plays at.** Half-size costs
  less RAM and makes the frames useless for the one other thing they are for:
  re-running the detector and labelling them. They are the highest-value
  training data the project produces, because they are precisely the cases the
  model fails on.

## The CEO reviewed the collisions and half of them were not collisions (2026-09-03)

Nine pre-crash windows went to the human. **Five came back "ไม่ชน เลือดไม่ลด"** —
nothing was hit. One added the reason the rest of the day had been measuring
fog: *"Cookie น่าจะใส่ Ability อมตะอยู่"*.

That invalidated every collisions-per-minute figure produced that day, and the
old-vs-new A/B built on them. **A metric nobody has checked against a human is
not a measurement.** Before optimising against a counter, show the human ten of
the events it counted and ask whether they are what the counter claims.

### The counter was firing on a misread, and the fix is confirmation

`HitWatch` flagged an energy drop of 0.06-0.12 on those five. Re-measuring the
SAME bar from the saved frames showed 0.28 → 0.28 (no change at all), 0.70 →
0.68, 0.16 → 0.15. The live poll grabs the screen independently of the play
loop and had caught a transient; nothing checked whether the value stayed down.

Re-measuring from the recorded frames and requiring a **sustained** drop of
>= 0.05 reproduces the human's verdict on **6 of 6**. So:

- a real hit's energy steps down and STAYS down;
- a misread recovers within a poll or two;
- the confirmation is free, because the pre-crash ring already holds a second
  of frames on both sides of the candidate.

General form: **an event detector that samples once has no way to tell an event
from a glitch.** Give it a before and an after from the same source it will be
judged on.

### Two things the human taught that the planner does not model

- *"เส้นการกระโดดมันจะต้องตรงกับ Line ของ Jelly พอดี"* — the jump arc is
  supposed to LIE ALONG the jelly line. That is the whole premise of this bot,
  and the drawn landing guide finally makes it checkable by eye: if the arc and
  the jelly row do not coincide, the jump is wrong regardless of what it scores.
- *"Model กระโดดไปแล้วก่อนหน้านั้นทำให้สไลด์ไม่ได้"* — an unnecessary jump
  FORECLOSES the next action; you cannot slide while airborne. The planner
  scores each trajectory in isolation and so cannot see this cost. A jump taken
  for one jelly can be what causes the collision two obstacles later.

## Reading a collision: the three-way split (2026-09-03, 11 human-judged hits)

When the bot hits something, exactly one of three things went wrong, and they
need completely different fixes. Sorting a collision into the right bucket is
the whole job, and it takes about a minute per hit with the /hits page.

| bucket | how to tell | fix |
|---|---|---|
| **not a collision** | the Energy bar does not actually step down and stay down | fix the counter, not the bot |
| **blind** | replay the detector on the pre-crash frames: zero boxes | label those frames, retrain |
| **saw it, did not act** | boxes track the obstacle in, and the planner still says "wait" | planner bug |

Of 11 collisions the CEO judged: 6 blind, 1 saw-but-idle, and separately 6 more
candidates that were not collisions at all. **Do not guess which bucket you are
in — replay the detector.** "It hit something" is compatible with all three, and
two full days went into fixing the wrong bucket because nobody replayed it.

### What the human's answers showed that no metric would have

Sorting the 11 by the action that was actually required:

    slide  5    the planner chose wait 4x and jump 1x -- it never slid in time
    double 4    the planner chose wait every time
    jump   1    the planner got this one right
    too late 1  it had jumped earlier, so it could not slide when it needed to

**Nearly half of all collisions were hanging obstacles needing a SLIDE, and the
bot never once slid in time.** A hits-per-minute number cannot show that. One
afternoon of a human answering "what should it have done here" did.

### The action rule is fixed, not situational (CEO, 2026-09-03)

**Hanging thing → SLIDE. Thing on the floor → JUMP. No exceptions.** Asked
whether the jelly line or the obstacle height should ever override this, the
CEO chose the fixed rule for the reason that governs this whole project: a
rule with no exceptions is debuggable, and a situational one is not. Encode it
as a rule, not as a score to be outbid.

### Ask before writing, and design the tool so the answer is not needed twice

The CEO's instruction for this pass was to **explain what I saw, say what I
thought, and ask, before writing any of it into this file.** That caught a
real ambiguity: clicks in the /hits page landed at x 0.16-0.26 (on the cookie)
while clicks in the /decide page landed at 0.41-0.54 (on the obstacle), and the
answer to what they meant was *"ยังตอบไม่ได้เพราะจำไม่ได้ว่าทำอะไรไปบ้าง"*.

That is not a human failing, it is a **tool** failing: a control whose meaning
has to be remembered later was under-labelled. Two rules fall out:

- **Never write a guessed interpretation of human input into a rule.** An
  unremembered answer is a missing answer; mark the data uncertain and move on.
- **A labelling control must state its meaning ON the control**, so the record
  is self-describing weeks later. If you find yourself asking the human what
  their own earlier click meant, fix the UI first.

## Partial detection is the dangerous failure, and this pipeline was blind to it

The CEO, after one afternoon of looking at collisions (2026-09-03):

> "ใน 1 หน้ามีสิ่งกีดขวางเข้ามาเยอะ Model เลือกที่จะลืมบางอันใน 1 หน้า ซึ่งไม่ควร
> ... เช่นในหน้านั้นมีสิ่งกีดขวาง 3 Model ทายมา 2 และชนอันที่ไม่ได้ทายมา"

This is the worst case, not a mild one. **A detector that finds two of three
obstacles looks healthy from every angle we were measuring.** Boxes appear, the
planner plans, the logs are clean, and the cookie dies on the third object. Zero
detections at least look broken; partial detection lies.

### The review pipeline could only ever measure precision

Every tool built here so far shows the human a box the MODEL proposed and asks
"is this right?" Keep/Reject measures **precision** — of what it found, how much
is correct. It is structurally incapable of measuring **recall** — of what is
there, how much did it find — because a missed object generates no card to
review. That is why the model could read "94% on EP1 pumpkins" while the bot
kept dying: the 94% was precision on the things it already saw.

**Any labelling loop built on reviewing proposals needs a second mode that asks
the opposite question: what is in this frame that the model did NOT box?** Build
it before trusting any accuracy number.

### Lowering confidence does not recover them — measured

The obvious first guess is that the objects are found but scored under the
threshold. Swept on 77 pre-crash frames from six collisions:

    conf 0.35 (live)   23% of frames had ANY box   0.23 boxes/frame
    conf 0.20          27%                          0.30
    conf 0.10          34%                          0.39
    conf 0.05          45%                          0.56

At a threshold so low it would flood false positives, still fewer than half the
frames produce a single box. **The objects are not in the model at all.** This
is a recall problem to be fixed with training data, not a threshold to tune, and
the sweep is worth running before every "just lower the confidence" suggestion.

## The escalation rule: decide, don't re-ask (CEO, 2026-09-03)

> "รอบหน้า ในวัตถุที่คล้ายกัน หลังจากนี้คุณตัดสินใจเองได้ จากข้อมูลที่ฉันสอน
> ถ้าไม่มั่นใจจริงๆ เอามาให้ดู ห้ามส่งมาทั้งหมด และห้ามส่งข้อมูลเดิมซ้ำๆ แบบที่สอนแล้ว
> คุณไม่จำ และไม่จดไว้ ไม่ Update Skills แบบนั้นเราจะไม่ได้ทำงานแบบ Scaling
> เราทำกำลังทำแบบ Hard work"

The standing contract for every future round:

1. **Decide it yourself** when the case resembles one already taught. A new
   obstacle with a different skin but the same behaviour is a decided case.
2. **Escalate only genuine uncertainty**, and only the specific frames that are
   uncertain — never the whole batch "to be safe". A batch sent for review is a
   batch the human has to work through; sending everything is the opposite of
   help.
3. **Never re-ask a taught question.** If the answer is not in this file, the
   failure was not remembering it — it was not writing it down.
4. **Every round must cost the human less than the last.** If it does not, the
   loop is not learning, it is just being executed.

Applying it the same afternoon: the CEO's boxes ran over the HUD, which the
box rules above forbid for a measured reason. That is a decided case — clip
below PLAY_TOP, note it, move on. It was not sent back as a question.

## One box in, a hundred out: propagate by measured geometry

The human draws an obstacle ONCE on one frame of a collision. Every other frame
in that window shows the same object, and the world scrolls at a speed that was
measured (794 px/s), so the rest is arithmetic:

    x_at(t) = x_drawn - SPEED * (t - t_drawn)      y unchanged

**15 boxes drawn on 10 frames became 208 boxes on 149 frames** — the multiplier
that makes a human afternoon worth a training set. `vision/build_hitset.py`.

This is not the template propagation that failed on 2026-09-02 and is warned
against above, and the difference is the point:

- **template matching asks an appearance question** — "does this look like the
  thing?" — and a matcher that is wrong in both directions cannot be trusted
  to scale one label into many;
- **this asks a geometry question** — "where has the world moved?" — whose
  answer is a constant that was measured, not guessed, and whose output is
  verifiable at a glance on a contact sheet (the boxes either stay locked to
  the objects across the window or they visibly drift).

Before trusting a propagation run, render one collision's frames with the
boxes drawn and LOOK at it. Drift shows up immediately.

Two things that make the resulting set usable rather than merely large:

- **Frames the human checked and found nothing in are negatives**, written as
  empty label files. Without them a set teaches only "find things" and never
  "not that".
- **Merge the previous verified set, never replace it.** Training only on the
  new objects buys them at the cost of whatever the deployed model already
  handles.

## The eyes improved, the collisions did not — and that is the useful result

Trained hitl3 on 201 images built from 15 human boxes (2026-09-03, $0.019,
3.9 min on a rented 4090). Measured against the same labels:

    new obstacles   hitl2   0/208 (0%)    ->  hitl3 137/208 (66%)
    EP1 pumpkins    hitl2  99/111 (89%)   ->  hitl3 108/111 (97%)
    false boxes on empty frames    20     ->  0

Then 15 live runs, 8 new against 7 old, same machine, same hour, same fixed
collision counter:

    hits/min   hitl2 3.65 (30 hits / 492 s)  ->  hitl3 3.07 (32 hits / 626 s)
    survival   hitl2 70.4 s/run              ->  hitl3 78.3 s/run

**That 16% looks like a win and is not one.** Rate ratio 0.84, 95% CI 0.51 to
1.38 — anywhere from 49% fewer collisions to 38% more. Reporting "16% better"
from this would be inventing a result. Detecting a difference that size needs
hundreds of collisions per arm, which is hours of running, not fifteen runs.

**What DID move is which failure happened.** Re-running the detector over the
pre-crash frames of all 32 new collisions:

    fully blind (0 boxes in the whole second before impact)
        hitl2 era   4 of 6   (67%)
        hitl3 era  11 of 32  (34%)

So two thirds of collisions are now cases where **the model saw the obstacle
and the bot hit it anyway**. The bottleneck moved from the eyes to the planner.

Two lessons worth more than the model:

- **A deterministic metric can prove a change that a noisy one cannot.** Frame
  recall is exact and moved from 0% to 66%; collisions per minute is Poisson
  with a handful of events per run and could not resolve a 16% shift. When a
  live number refuses to move, check whether it has the power to move at all
  before concluding the change did nothing.
- **Fixing the binding constraint reveals the next one, and the collision rate
  need not drop until that one is fixed too.** Track the FAILURE MIX, not just
  the failure count: "blind" falling from 67% to 34% is the real evidence the
  training worked, and it points at where the next work is.

## Propagated labels fail by SOURCE, not by distance (2026-09-03)

Carrying a human's boxes to neighbouring frames by the measured scroll speed
multiplies one afternoon into a training set. It also multiplies mistakes, and
the CEO judging 36 propagated frames showed which way that goes.

The obvious hypothesis — error grows with how far you carry a box — is real but
secondary:

    shift    0-149 ms   40% rejected
           150-299 ms   33%
           300-449 ms   75%
           450-599 ms   83%

The dominant term is WHICH FRAME the boxes came from:

    source A   7 of 7 usable, 72 of 72 boxes kept
    source B   3 of 3 usable, 44 of 44 kept
    source C   4 usable / 3 rejected, 36 of 61 kept
    source D   3 usable / 7 rejected, 47 of 90 kept
    source E   0 of 9 usable, 0 of 30 boxes kept

Source E was rejected at EVERY distance, including 70 ms. Its boxes were wrong
where they were drawn, and propagation faithfully reproduced that wrongness
across every derived frame. That is the whole lesson: **propagation is an
amplifier, and it amplifies a bad source into dozens of bad labels while the
count on the dashboard goes up.**

So the rule for any propagation pass:

1. **Verify a sample from EACH source, not a sample of the pool.** A random
   sample across the pool hides a bad source inside good ones; a sample per
   source finds it immediately. Two frames per source is enough to see it.
2. **Drop a whole source when its derivatives are rejected**, and drop its
   ORIGINAL boxes too — they are the thing that was wrong.
3. **Cap the distance anyway** (here ~300 ms), because the two failures
   compound.
4. Frames marked "boxes right but incomplete" are still good positives. Do not
   throw them away for missing objects; just do not treat their empty space as
   negative evidence.

## Field notes

- 2026-09-23 [MISSING] §Auto-labels — the distrust above is measured on colour template-matching; a VERIFY question to vision teachers ("the bot thinks this is X — right?") behaved differently: gemma-4-26b + qwen3.7-flash agreed on 181/186 screen/badge questions and all 181 were right, Sonnet 5 settled the 5 splits 5/5. Screens and box badges only — not boxes around obstacles · evidence: Agents docs/ops/cookierun-teachers-2026-09-23/ab-20260923-122814.json, sha 2cce1f51 · status: pending
