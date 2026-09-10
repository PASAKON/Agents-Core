---
name: ai-film-production
description: >
  Production discipline for running a MULTI-SCENE AI film — twenty-plus shots that
  must stay continuous in face, wardrobe, geometry and props across days of
  generation. Trigger on /ai-film-production and proactively whenever a C-level is
  directing a short film or ad built from many AI-generated scenes: writing scene
  prompts against shared character and location references, ordering plates,
  running browser_operator lanes, or deciding what to re-shoot after a prompt or
  Element changes. Supplements — does not replace — `higgsfield-unlimited-gen`
  (the platform's buttons and money) and `browser-operator` (generic browser cost
  discipline). Do NOT fire for a single standalone clip, for storyboarding with no
  generation attached (that is `ai-video-storyboard`), or for still-image work.
created_by: human
audience: [cxo]
---

# Running a multi-scene AI film

Every rule below was paid for on «Sorry, Sir» — 2026-08-27/28, seventeen scenes,
one CEO, two operator lanes. None of it is speculative. Tool-level rules — which
button costs money, how to read the price — live in `higgsfield-unlimited-gen`.
This skill is the layer above: **how to keep a film coherent while a model
generates it one scene at a time.**

---

## 1 · ONE FACE PER PLATE

The most expensive lesson of the wave. Content scanners match on human faces.
**Three plates died permanently in one day**, each with a terminal verdict and no
re-check control left in the UI:

| Plate | Faces in it | The fix that worked |
|---|---|---|
| a *location* plate | six people standing in it | regenerate the location **with nobody in it** |
| a character plus his two bodyguards | three | regenerate as a **solo portrait**, guards bound separately |
| two journalists sharing a camera | two | **split into two plates, one face each** — both passed first try |

**Design every plate with at most one face** and let each scene assemble its cast
from separate Elements. That is what a reference system is for.

**A location plate should contain no people at all.** Two wins at once: it removes
what the scanner catches, and it stops the cast being frozen at the wardrobe they
had the day the plate was made. A location plate with people in it silently serves
stale character designs into every scene that binds it.

**The scan is retroactive.** A plate that passed at 10:41 was terminally dead by
11:47 with nothing changed. **A plate is never banked.** So: **make a plate and
fire every scene that needs it in one unbroken loop, same operator, no handoff.**
The gap between creating a plate and using it is pure risk.

---

## 2 · NEVER LET THE GENERATION SLOT SIT IDLE

Where video generation is unlimited, **a clip costs nothing and an idle slot costs
time — and time is the only thing a deadline actually spends.**

I once paused a video lane to avoid making clips that would later be re-shot. The
CEO corrected it in four words: *"อย่าให้คิว Generate ว่าง"*. He was right. A
re-shot clip is free; the hour the slot sat empty is not.

- Keep a standing list of shots that depend on **no** pending asset, and fire
  those whenever the queue would otherwise stall.
- Paid image generation usually does **not** contend with the unlimited video
  slot. Verify once, then run both lanes in parallel. Standing an image operator
  down "until the video clears" cost forty minutes of two workers.
- Pre-stage the next prompt while the current one renders.

---

## 3 · BRIEF WORKERS THROUGH A FILE, NOT THE TERMINAL

Long instructions typed into a worker's pane **arrive fragmented**. A worker's own
commit read *"reconstruct scattered CEO relays"* — it had been guessing my orders
from pieces, and had spent half an hour firing the wrong scene.

**The pattern that works:**

1. Write the full instruction to a file in the worker's worktree — `QUEUE.md`,
   `PLATES.md`, whatever fits.
2. Send **one short line** in the pane pointing at it.
3. State in the file: *this file is the source of truth; ignore any partial pane
   message that disagrees with it.*

**Two more delivery traps:**

- **The mailbox delivers empty bodies.** A worker sees a ping with no content and
  correctly dismisses it. The pane is the channel that lands — subject to the
  length problem above.
- **Every pane message kills the worker's background wait.** Workers time render
  polls with a background `sleep`; typing interrupts it. One worker eventually
  stopped polling altogether and sat idle waiting for me, with the slot free.
  **Relay only to change something. Never to ask for status** — read its reports,
  its worktree commits, or `tmux capture-pane`.

---

## 4 · A WORKTREE FREEZES WHEN THE TASK IS CREATED

A worker's checkout is cut at task creation. **Anything committed to main
afterwards does not exist for it.**

This produced the sharpest failure of the wave: I committed a rule to main, told
the worker it was now authorised, and the worker checked, found nothing, and
refused — **four times.** It was right every time. Its `git log` was telling the
truth; my instruction described a file it could not see.

**Copy changed files into every live worktree and verify by checksum.**

```bash
cp docs/prompts/<film>/*.txt "$W/docs/prompts/<film>/"
md5 -q docs/prompts/<film>/s7-s9.txt "$W/docs/prompts/<film>/s7-s9.txt"   # must match
```

**When a worker refuses an instruction because it cannot verify it, that worker is
behaving correctly.** Do not repeat yourself louder. Find out why it cannot see
what you can.

---

## 5 · CHANGE AN ELEMENT, RE-SHOOT EVERYTHING BOUND TO IT

Director's rule, and it is the right one:

> Whenever a prompt or an Element changes, every scene that depends on it is
> re-shot. No "close enough".

Enforceable only if the dependency map is **written down and regenerated from the
prompt files**, never remembered:

```bash
grep -oE "(loc|char|prop)_[a-z_0-9]+" docs/prompts/<film>/s*.txt | sort -u
```

On this film one location Element fed **twelve of seventeen scenes**. Replacing it
re-shot most of the picture — a fact the director must be given *before* the plate
is ordered, not after.

**Never re-point an existing Element to a new image.** A scene that already bound
it keeps serving the old asset, silently. **Always a new name**, then sweep the
prompts.

---

## 6 · SET A TOLERANCE OUT LOUD, EARLY

Without one, an operator will chase an exactness nobody asked for and block
everything behind it. Mine spent two re-fires trying to match a crack pixel for
pixel; the director ended it with *"ขอเหมือนที่สุดก็พอ ประมาณ 10-20% Error
ได้ไม่ว่ากัน"* — close enough, 10–20% drift is fine.

**Put the tolerance in the brief**, and separately name **what it does not
cover** — where a miss breaks a scene rather than looking slightly off:

- **no people in a location plate** (§1)
- **duration on any shot carrying dialogue** — lines get cut off, not softened
- **resolution** — one 480p insert in a 720p film reads visibly soft
- **the money check** — the price on the generate button

---

## 7 · THE MODEL FOLLOWS YOUR PROSE OVER YOUR REFERENCE

When a bound reference fails to attach, the model does not error — **it follows
the words.** A scene fired with a reference silently unbound produced the exact
design the director had rejected twice, because my prose still described the old
idea.

- **Count reference chips against mentions before every fire.** A short count is
  the only signal you get.
- **Element naming is not uniform.** Most carried a shared prefix; one did not,
  and the mention silently failed to bind. Read the real mention off the panel.
- **Keep prose and reference in agreement.** They disagree, the prose wins — so
  when a plate is redesigned, sweep every prompt that describes it.
- **Anything the audience must read as identical** — a crack, a doorway, a prop —
  comes from a bound reference, not from description. Describe it anyway, matching
  the plate, as the fallback for when binding fails.

---

### 7a · AN ELEMENT'S NAME IS NOT ITS CONTENT — read what the plate DEPICTS before binding it (2026-09-11)

Rule 7 says the model follows prose over a failed reference. This is the uglier
sibling: **the reference bound fine, and it was the wrong picture.**

S2AC v2 was written to a director's note naming `project_absence_loc_hall_big_d`
as the wall to face. I bound it and wrote "THE CAMERA FACES THE WALL SQUARE ON"
over the top. That plate is **HALL D, a corridor seen down its length.** The
reference's geometry won, as it always does, and the take came back as a corridor
with no wall in it — the director's reaction was "v2 ไม่เห็นมีกำแพงเลย".

Nothing errored. The chip was green, the id was real, the count was right, the
lint was clean. **Every check I ran was a check on the STRING.**

The catch costs one command. The sheets describe their own plates, so:

```bash
grep -rh "@project_absence_loc_wall_crack" docs/prompts/<film>/*.txt | head -3
#  -> "THE HERO WALL. Flat white, no painting on it. ONE SMALL CRACK in the
#      MIDDLE of the wall at picture-hanging height…"   <- that is a wall
#  -> "HALL D, the richer hall: a corridor opening…"    <- that is not
```

Rules:
- **Before binding any location plate, read one line of prose describing it** —
  from a sheet that already used it, from CAST.md, or by opening the image.
  Never from the id alone.
- **A name handed to you by anyone, including the director, is a pointer, not a
  verification.** He is naming it from memory of a picture he can see; you are
  binding a string. Those two things fail differently.
- **A prose sentence that contradicts the plate's own geometry is the tell.** If
  you find yourself writing "the camera faces X" over a reference that does not
  face X, stop — you have the wrong plate, and no wording will fix it (§7, §11).

### 7b · Depth words are a size instruction; state size IN THE FRAME (2026-09-06)

A small mark rendered 4-5x too big on two consecutive takes while the prose
said "SMALL… about the size of a hand". The same prose also said "the nearest
thing to the lens / extreme foreground / floating at the very front". The
model was doing perspective correctly: a near object is big in frame, and "a
hand" is a world size it cannot place. The take that passed (S2M 3b, ledger
entry) removed every depth word and anchored the size to something visible
in the same frame: "NO WIDER THAN THE RED DOOR AND NO TALLER THAN THE RED
DOOR, exactly as the picture has it". Rules:

- Give an object's size relative to another thing IN THE FRAME (the door, a
  head, a plinth), never as a world measurement (a hand, 30 cm).
- Use no depth words (nearest, foreground, in front, floating at the front)
  unless you want the object BIG. Layering ("in front of everyone") is fine
  once; emphasis ("the nearest thing to the lens") is a size order.
- Do not tie people's gaze to an object whose depth you left ambiguous —
  "turned toward the mark" sent a whole crowd to face the far door. Say
  where their faces point in camera terms: "FACING THE CAMERA".
- Emphasis sentences ("the whole joke is this tiny mark") make the thing
  bigger, not smaller. Cut them.

## 8 · WHAT THE DIRECTOR DECIDES, AND WHAT YOU MUST NOT

Story, plot, who a character is, what anyone says, the ending, shooting order.
**Even while he sleeps — especially then.** I once overrode his chosen shooting
order on my own schedule reasoning and reverted within the minute; the margin did
not justify it and it was not mine to change.

**But do not let that stall the work.** Do everything that does not depend on the
open question, state your assumption in writing where it does, and put the
question where he will see it. This film stayed entirely fireable with one scene's
dialogue outstanding, because everything else was written under flagged
assumptions.

**Write his words down verbatim, in his language, the moment he says them.** Every
detail is load-bearing; rewriting a brief from memory is how details quietly
disappear. **After any renumbering, re-attach his original messages to the new
numbers before marking anything missing** — a scene I recorded as "waiting on the
director" for a full day turned out to have been written by him all along, in a
message whose scene numbers had since shifted.

---

## 9 · YOUR OPERATORS ARE THE ONLY EYES

A C-level cannot watch video. **Require a shot-by-shot description of every
delivered clip**, against the specific beats of the brief. On this wave those
reviews caught: a scene rendered as the one design the director had rejected; a
clip at 480p inside a 720p film; a missing physical beat that a later scene was
written to rhyme with; and clips silently returning at half their requested
length.

Ask for named beats — *"does he look left and right", "do the gold teeth show",
"is the plaque reversed"* — never for a general impression.

**Check delivery, not just generation.** A finished clip sat uncollected on the
platform for two hours while everyone believed it was done. Uncollected work is
the only work that can actually be lost: **commit the asset id before
downloading**, because ids cannot be recovered and files always can.

---

## 10 · A CHARACTER'S NAME CAN BLOCK THE CLIP, AND NOTHING TELLS YOU WHICH ONE

**Names are not the risk. A COLLISION is.** A generator's copyright filter
reads proper nouns in your prompt text and matches them against real people and
real works. Invented names pass all day — in the same film `Valder` and
`Carrington` are spoken out loud in a dozen rendered clips and nothing has ever
objected to them. What gets refused is the invented name that happens to land on
somebody or something notable. The refusal never names the string it objected
to. It looks random, so the first instinct is to re-fire, then to blame the
reference plate.

The director's framing, and it is the correct one: **do not stop using names —
find the one that collided.**

Measured 2026-09-05 on «Sorry, Sir». One scene was refused twice for copyright.
The suspicion fell on the character's image plate. It was the name: with three
strings changed and **nothing else** — a reference description, one blocking
line and one spoken line — the identical prompt, identical sixteen references,
identical blocking and identical cuts generated clean on the first try.

**Diagnose it from the files you already have, before you fire anything.**

1. **List every proper noun in the paste block.** There are usually about four.
   Strip `@handles` first so Element ids do not pollute the scan.
   ```bash
   python3 - <<'PY'
   import re,pathlib
   b = pathlib.Path(SHEET).read_text().split("PASTE FROM HERE",1)[1].split("PASTE STOPS HERE",1)[0]
   print(sorted(set(re.findall(r"(?<!^)\b([A-Z][a-z]{2,})\b", re.sub(r"@\S+"," ",b), re.M))))
   PY
   ```
2. **Cross the list against what has already rendered.** A name that appears in
   a clip sitting on the drive is cleared by evidence and needs no test. On that
   wave two of the four names had rendered in seven scenes and three scenes
   respectively; the two untested names appeared in six sheets, **and not one of
   those six had ever rendered.** The untested strings and the blocked clips
   were the same set. That is the diagnosis, and it costs nothing.
3. **Change only the names.** One variable, or the result means nothing.
4. **A full strip proves the name was the trigger. It does not tell you WHICH
   WORD.** An honorific and a surname are two variables — clear both at once and
   you have a working clip and no knowledge. If the answer matters, split them
   across clips you have to fire anyway: keep the honorific and change the
   surname on the next scene, and one render answers it at no extra cost. Never
   spend a render on a test you could have piggybacked.

**A name in the prose counts, not just a name in dialogue.** Sister scenes were
assumed to be a free control because nobody says the name out loud in them — but
it was written into their blocking lines, position maps and reference
descriptions, and a filter reads the whole prompt. They were carrying the same
risk, not testing it. **Grep the paste block, never reason from the dialogue.**

**When one name is cleared, sweep every sheet that carries it** — the string
lives in more prompts than the one in your hand.

Give the invented name a plain descriptive stand-in (`THE WOMAN IN GREEN`) and
keep the real one in the sheet's notes so the story is not lost. The director
decides whether to keep hunting for a usable name or ship the descriptive one.

---

## 11 · A PROHIBITION WITH NOTHING PUT IN ITS PLACE DOES NOT HOLD

The most common wasted take is not a prompt that forgot to ban something. It is
a prompt that banned it clearly, in capitals, and got it anyway. **A negative
tells the model what not to render; it does not tell it what to render instead,
and the gap fills itself.**

Four measured instances in one night on «Sorry, Sir»:

| what was banned | what came back | what actually fixed it |
|---|---|---|
| "no looking at camera by anybody" | four of twenty seconds are the cleaner squared to the lens | give him a specific thing to look at *off* to one side, and a body angle that makes front-on wrong |
| "no running, no jogging, no scurrying" | he ran | the previz was showing 5.67 m/s; fix the reference, then write the number and *one foot always on the ground* |
| character's cart "at the very back" with him | cart at the front of the line, its owner empty-handed at the back | ban the SEPARATION — no cart at the front, not near anyone else, not separated by other people |
| a bodyguard described as "plain dark suit" | a generic businessman in a black suit and white shirt, front and centre | the full description: heavily built, dark glasses, white gloves, black shirt |

The shape is always the same. Prefer these, in order:

1. **Replace, don't forbid.** Somewhere specific to look, a named body angle, a
   hand on a specific object. The model needs a thing to do.
2. **Ban the RELATIONSHIP, not the absence.** "The cart is with him and only
   with him" beats "no missing cart" — the failure is rarely deletion, it is
   drift.
3. **Name the exact wrong thing you actually got.** "No straight lines
   radiating from a centre" and "no black suit with a white shirt" outperform
   "no geometric crack" and "no extras". A banned specific beats a banned
   category.
4. **A vague description is a blank the model fills.** Four words invite an
   invention. If a character has a plate, paste that plate's full description in.

**And check the reference before you rewrite the words at all.** Twice the words
were already right and the video reference was overriding them — see rule 7 and
[[feedback-proxy-in-previz-beats-the-plate]]. Hardening prose against a
reference that disagrees with it is the most expensive way to lose a take.

### 11b · An adjective is not a direction — make the motion COUNTABLE (2026-09-11)

The same failure wearing different clothes: not a banned thing that appeared,
but a *described* thing that never did. S2AC asked for a scrum — "IT NEVER
SETTLES AND IT NEVER PAUSES. Somebody is always crossing somebody else." The
take came back with five people standing in the same spots at 1 s, 8 s and
15.5 s, waving their arms. It read as a posed group photograph with busy hands.

The model was not disobeying. **"Chaotic", "restless", "never settles" contain
nothing that can be scored right or wrong**, so it satisfied them the cheapest
way available — gestures — and left the blocking untouched. Position is
expensive; hands are free.

✅ **PROVEN 2026-09-11 — and the confound was the real story.** This fix looked
dead: v2 carried all four counted crossings verbatim and came back exactly as
static as the takes before it. The wording was not the problem. **v2 was also
bound to the wrong location** — a corridor instead of a flat wall (§7a) — and a
corridor funnels a crowd into a clump no instruction can undo. v3 changed the
plate and nothing else about the crossings, and the group genuinely rearranged:
the student crossed from far-left to front-centre by 4 s, Dupe walked from
far-left to dead centre by 11 s, the magenta and cobalt pair swapped sides.

**The lesson is bigger than the wording.** Before rewriting an instruction that
failed, ask whether the SET can physically host what you are asking for. A
narrow space, a deep corridor, a frame with one visual anchor — these stage a
crowd for you, and they will beat any adjective and any counted list. **Staging
is a location problem first and a prose problem second.**

The proposed fix states the arrangement changes as **counted events with
deadlines**:

> Count the crossings — THERE ARE FOUR … by 5 s the student has crossed the
> full width; by 8 s the magenta woman and the cobalt woman **have swapped
> sides**, passing each other mid-frame; by 12 s Dupe has mopped from one end
> to the other through the middle; by 15 s the student has crossed back.

Rules for any multi-person scene:

- **Say how many position changes there are, who swaps with whom, and by when.**
  Never "they mill about".
- **Give the review a falsifiable test.** Here: *if the arrangement at 15 s
  matches the arrangement at 1 s, the shot failed* — regardless of how busy the
  hands look. A review order that only says "check it feels chaotic" passes
  anything.
- **Motion a reviewer cannot COUNT is motion the model will not render.** This
  generalises past crowds: a walk, a search, a pace, a fidget — if the beat
  matters, it needs a number and a timestamp.

**LOOK AT IT FIRST. The number is a footnote, never the verdict (CEO 2026-09-11:
"อย่าวัดจากตัวเลข วัดจากสายตา").** I reported a failing take as "10% versus 44%"
and the director corrected it, rightly. A film is judged by looking, and on this
same production the eye has twice overruled the spec — S21 broke two written rules
and was better for it (§ the S21 ledger entry). A metric cannot tell you that.

What looking gave that the number could not, on the very same clip: the cast was
**bunched in one knot left of centre in a wide empty hall**, standing in a rough
line behind the cart like a queue at a counter, with the object of the argument
the least visible thing in frame. "10% change" says *it did not move*. The eye
says *the staging is timid, they are not using the room, and the prop is buried* —
which is the note you can actually act on. Diagnose from the frames; reach for a
number only to confirm what you already saw, or to compare two takes of one shot.

With that established — `scripts/shot-motion.sh <clip>` compares the people-band
of the opening frame against later ones. Measured 2026-09-11:

| clip | 7 s | 12 s | 15.5 s | |
|---|---|---|---|---|
| S2AC take 1 (failed) | 10% | — | 10% | flat |
| S2AC take 2 (failed) | 11% | 9% | 11% | flat |
| S2PT take 4 (real movement) | 44% | 46% | 54% | rising |

**The TREND is the signal, not the level.** A real scene drifts progressively
further from its opening frame as it runs. A tableau sits the same distance from
its opening forever — which is exactly what a still image with waving hands looks
like to this measurement. Two takes of the same sheet returned 10% and 11%: that
reproducibility is what proves the prompt is the cause and not the dice.

Caveat: the number is only comparable **on a locked camera**. A tracking shot
changes its whole background and inflates the reading (S2PT's camera moves, which
is part of why it scores so high) — use it to compare takes of one shot, never to
rank different shots against each other.

## 12 · WHEN A RE-FIRE PASSES, WRITE THE A/B ENTRY (CEO 2026-09-06)

Every job that had to be sent back for a fix gets a ledger entry the moment
the fixed take passes review: **Prompt A** (the prose that produced the
defect) against **Prompt B** (the prose that fixed it), quoted, with the
defect as it was seen in the clip and the reason B worked. The point is
comparison — the next writer reads what actually changed, not a summary.

The ledger lives beside this file: `AB-LEDGER.md`. Entry shape:

    ### <scene> · takes N → M · <date passed>
    DEFECT SEEN: what the clip did (from frames, not from the report)
    PROMPT A:   "…the exact lines…"           (commit <sha>)
    PROMPT B:   "…the exact lines…"           (commit <sha>)
    WHY B HELD: the mechanism, one or two sentences
    LESSON:     one line, general enough to reuse; cite the § it belongs to

Rules: the entry is written by whoever reviewed the passing take (the CTO),
never by the operator; A and B are quoted from git, not paraphrased; a fix
that has not passed goes under PENDING with its A already quoted, so the B is
filled in the day it lands. Creative restages ordered by the director are
not defects and do not go in.

## 13 · EVERY PROJECT HAS A CAST.md FROM DAY ONE, AND EVERY PROMPT MATCHES IT (CEO 2026-09-08)

**Rule:** before the first video prompt is written, the project has one file —
`CAST.md` beside the prompt sheets — with ONE ROW PER CHARACTER: the Element
chip name that is canon, what they wear (colours named), what they carry and
what they never carry, their acting register in five words, and their locked
lines. A prompt sheet may not describe a character in words that disagree with
that row. When the director changes a character, the row changes first and
every sheet bound to it is re-checked (§5). Two chips for one character is a
defect in CAST.md, not a style choice.

**Why (in the CEO's words): "CAST.md ฉันคิดว่าควรมีแต่แรก … โปรเจคหน้าจะต้องมีการ
CAST ตัวละครให้เหมือนกันทุก ๆ PROMPT."** On «Sorry, Sir» the late-film cast —
Dupe, the registrar, the workman, the guards, the bodyguard, Carrington, the
grandmother, the Madame — existed only inside individual sheets. Two registrar
Elements (white and black) and two grandmother wardrobes (grey knit and purple
with sunglasses) shipped into Draft 3 without anyone seeing the split, because
there was no single page where the split would have been visible. Finding it
cost a full judge review of the cut, two aborted spawns and three hours of
sheet surgery on 2026-09-08.

**How to apply:** the sheet-writing gate is "does every character line in this
paste block match its CAST.md row?" — grep the FLATTENED paste block (phrases
wrap) for each character's colour and carried object against the row. The
first commit of a new film's prompt directory is CAST.md; a sheet that binds a
chip absent from CAST.md fails lint.

## 14 · CHOOSE THE MODEL BY WHAT THE SHOT HAS TO CARRY (CEO 2026-09-10)

Measured on Higgsfield the same afternoon, same 15-second prompt, same three Elements, fired
back to back on the credit lane (`s2rq15-lab-the-bids-jumpcut-15s.txt`, AB-LEDGER 16:35):

| | Seedance 2.5 | 2.0 Fast | 2.0 Mini |
|---|---|---|---|
| credits, 15 s 720p | 98 | **53** | **38** |
| max duration | 30 s | 15 s | 15 s |
| render | 11-19 min | **~4.5 min** | **~3.5 min** |
| bitrate, same 720p/15 s | — | **17.0 Mbps** | **4.3 Mbps** |
| file size | — | 32 MB | 8 MB |
| `@Element` chips | yes | **yes** | yes |
| Unlimited grant covers it | yes | no | no |

**Both cheap tiers bind Elements.** That was the question that could have ruled them out and it
did not. 2.0 Fast held a face from an Element across three hard cuts, and held a second character
from PROSE alone across two more, with the five spoken lines in the right order.

**The CEO's read, which is the one that decides casting a model to a scene (2026-09-10):**
"Fast ดีกว่า Mini มาก และเห็นได้ชัดว่าถูก Upscale มา สีสันสดใสกว่าต้นฉบับมาก เหมาะกับการเป็นฉากที่
ไม่ควรมีตัวละครเป็นฉากในจินตนาการ และฉากที่ไม่มีผลกับผล เป็นฉากเริ่ม"

So: **2.0 Fast looks upscaled — colour reads more saturated and the image sharper than the
source grade.** That is a feature for some shots and a defect for others.

- **Give 2.0 Fast:** establishing shots, opening images, imagined or dreamed scenes, inserts
  with no cast, anything where a heightened look is welcome and continuity with the graded
  footage does not matter.
- **Keep 2.5 for:** any shot that has to cut against other 2.5 footage inside the same scene,
  and any beat carrying the story.
- **2.0 Mini** is the cheapest, the fastest and visibly the weakest — treat it as a draft tier.
Measured against Fast on the identical prompt: **a quarter of the bitrate** (4.3 vs 17.0 Mbps),
**16-18% less colour saturation**, higher edge energy at lower bitrate (over-sharpening and
compression, not real detail), skin that reads waxy on a large face, and it **ignored the
framing spec** — asked for a face filling sixty percent of frame height it pulled back to
roughly forty-five. Its cut timing drifted furthest too (cuts at 1.7 / 3.5 / 5.4 / 7.5 / 10.4 s
against a script of 2.5 / 5 / 7.5 / 10 / 12.5, leaving a 4.6-second final shot). It still bound
all three Elements, held both faces across every cut, and spoke all five bids in order — so it
is usable, just not for anything a viewer looks at closely.

**Never mix models inside one scene** — on the colour and bitrate numbers above, which were
measured like-for-like on an identical prompt. That part stands.

**⚠️ The background argument for it is WITHDRAWN (2026-09-11, S2R-Q).** This rule used to say the
tiers stage the background differently — that asked for "a plain cream wall, softly out of focus,
nothing else in frame", 2.5 gave a plain soft wall while 2.0 Fast rendered the whole hall with its
columns. **S2R-Q disproves it: one 2.5 generation rendered BOTH.** The full hall with chromium
columns and hanging lights sits behind Carrington's three close-ups and Valder's, and a plain warm
out-of-focus wall sits behind Madame's two — same model, same prompt, same fire, one continuous clip.

So **background staging is a per-shot variable, not a model discriminator.** Never use it to infer
which tier produced a clip, and never accept "the background looks like the hall" as evidence a
sheet was fired on the wrong model. The original observation was a single-sample coincidence read
as a rule.

**When the free queue is jammed, render time beats price.** On a day when the Unlimited lane
returned nothing for six hours, a paid 2.0 Fast fire came back in four and a half minutes.
Getting the shot at all is worth more than the discount.
