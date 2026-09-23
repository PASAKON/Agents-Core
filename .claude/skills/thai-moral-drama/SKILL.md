---
name: thai-moral-drama
description: >
  The story format for the ILAG Studio Facebook page «ละครสั้นคุณธรรม» — Thai
  stand-alone moral short films in the ฟ้ามีตา tradition, 18–24 minutes, one
  complete story per episode, made with AI video. Covers the beat structure, the
  rules about who the wrongdoer is and how karma lands, the requirement that the
  spoken lines alone carry the whole story, and the production constraints that
  follow from shooting it in Google Flow. Trigger on /thai-moral-drama and
  whenever anyone writes, audits, expands or briefs a story for that page, or
  mentions ฟ้ามีตา, ละครสั้นคุณธรรม, «บัญชี», «เงินที่พ่อตั้งใจหา», or a new
  episode for the ILAG drama channel. Use ALONGSIDE `tig-scene-engine`, which
  owns scene-level structure (Goal/Obstacle/Tactic/Reversal/Value Shift) and is
  never replaced by this file — this one owns the episode shape and the format's
  promises to the audience. Not for the ILAG festival films (Do Not Disturb,
  Sorry Sir) — those are a different product with a different channel.
---

# ละครสั้นคุณธรรม — the format

Derived 2026-09-18 from four real ฟ้ามีตา episodes (ศาลเตี้ย · เด็กในบ้าน ·
ปีศาจ · เจ้าที่) plus the CEO's own rulings while «บัญชี» was being written.
Everything marked **CEO** is a ruling, not a suggestion.

ฟ้ามีตา has run since 9 June 2007 on Channel 7, Saturdays 14:30, sixty minutes
including ads. **Two hosts across its whole life; the cast rotates every week.**
That is the first lesson and it is a business one: the narrator is the brand, the
actors are not.

---

## The nine rules

### 1. One episode is one complete story (CEO)
No arcs, no cliffhangers, no "ตอนที่แล้ว". A viewer who lands on episode seven
must lose nothing. This is the whole reason the format works on a Facebook feed:
every clip stands alone, so every clip can be promoted alone, and one weak
episode does not poison the next three.

### 2. The wrongdoer has a reason, and it is almost acceptable
พี่จี๋ pressures a junior to steal because she is in trouble herself. พิม abuses
her own mother while sincerely believing she is a good person. **Nobody is evil
because they are evil.** A villain the audience cannot argue with in their own
head turns the episode into a lecture.

### 3. The wrong is possible because of a power gap
Servant vs the employer's son. Bedridden mother vs her grown daughter. Junior vs
supervisor. Debtor with no contract vs the man who keeps the only ledger. The
victim is not merely sympathetic — **they structurally cannot fight back.** That
gap is what makes an audience angry rather than sad.

### 4. The turning point is an ACT, not a speech
ยายกลั่น fights back. แต้ว refuses. สมชาย stops paying. In none of the source
episodes does the turn arrive as a monologue.

### 5. The reversal comes from a witness who had no obligation to speak
ศาลเตี้ย turns because the wrongdoer's **own sister** testifies. เด็กในบ้าน turns
because the **neighbour's mother** says one sentence. The person who breaks it
open is someone who could have stayed quiet and did not.

**Plant that witness in the first two minutes.** ฟ้ามีตา has sixty minutes and can
introduce anyone at any point; an 18-minute episode cannot. A witness who first
appears at minute nine reads as a cheat.

### 6. Karma is poetic, and it must be EARNED, not administered (CEO)
Ote is not jailed — he is left disabled and his mother must care for him
forever, which is exactly what he inflicted on others. พิม's entire punishment is
realising she is the villain.

The law may appear, but **it is never the thing that arrives to fix the story.**
In «บัญชี» a policeman makes the arrest — and he works only because he has eaten
free at the father's shop since he was a boy. **The good the hero did years ago
is the mechanism.** Strip that out and the same scene is a deus ex machina.

Test: *if this instrument had not been planted and paid for earlier, would the
ending still happen?* If yes, the ending is unearned.

### 7. ทำดีได้ดี ทำชั่วได้ชั่ว — and EVERY named character gets a conclusion (CEO)
> "เส้นเรื่องความสมเหตุสมผล ที่มาที่ไปของตัวละคร บทสรุปของทุกๆ ตัวละคร"

Not just the hero and the villain. Anyone with a name and a line is owed an
ending. Before a script is finished, write the table out and look for a blank:

| character | what they did | what it got them |
|---|---|---|

A blank cell is a rewrite, not a rounding error.

### 8. The family must visibly come through it (CEO)
> "คนดูรู้สึกให้ครอบครัวนี้ผ่านมันไปให้ได้ และคนร้ายต้องถูกลงโทษ ไม่งั้นคนดูจะนั่งดูทำไม"

Dignity is not a resolution. An audience that gives you twenty minutes is owed a
material change: the money back, the illness treated, the shop alive, the child
employed. **A good man who ends the film exactly as poor as he started has lost,
whatever the last shot implies.**

This rule killed a draft of «บัญชี» in which the hero, having proved he was
cheated, refused the money back on principle. That is an art-film ending in a
morality-tale format.

### 9. Show it, never claim it (CEO)
A line asserting something about a character is worth nothing without a scene
that proves it. «บัญชี» had a policeman saying he had eaten free at this shop his
whole life — and the audience had never once seen the father refuse his money.

**Every claim in dialogue needs a scene.** Better: play it twice, and make the
second one cost something. The father refusing payment in a normal week is
characterisation; the father refusing it while his shop is dying and his mother
has no medicine is the reason the ending is allowed to happen.

---

## ⛔ Money on screen is invented prop money (CEO 2026-09-18)

A prop plate asked for "worn folded Thai banknotes, no readable text" came back
as a fully legible 20-baht note — `รัฐบาลไทย` readable, the denomination
readable, serial numbers readable, and a recognisable portrait of King Rama IX.
Four of four money shots in the first Act 1 shoot did the same thing: the model
draws a real Thai note whenever a prompt says "banknotes", whether or not a money
chip is attached.

My first fix was to hide the money — closed hands, sealed envelopes, the edge of
a fold. The CEO replaced it with a better one:

> "เราไม่ต้องทำเหมือนของจริงก็ได้ มันเหมือนเกินไป ... ให้เป็นเงินกาโม้แทนได้เลย"

**Change what the notes ARE, and the scene can be shot openly.** A father
counting money at his counter is good drama; hiding it in every shot was solving
a legal problem by amputating a storytelling one.

The block, pasted into every shot where money appears:

```
The banknotes are plain fictional prop money, not the currency of any real
country: soft pastel paper in even tones, a simple printed numeral in one corner,
a plain abstract line pattern at the edges, and nothing else. No portrait or face
of any kind on the notes. No national emblem, crest, seal, flag or country name.
No real-world currency symbol, no serial numbers, no signatures, no microtext, no
watermark. Worn and soft with handling.
```

**Foreign currency is not the safer option.** Dollars, euro, yen and yuan all
carry portraits, landmarks and protected security designs; swapping one country's
note for another's trades a Thai problem for someone else's. Invented money
belongs to nobody.

Two things this does not change: the amount is still **spoken**, never read off a
note — a spoken number cannot warp and cannot be missed. And a man whose whole
story is that he never writes anything down still gets `no notebook, no pen, no
paper` in the same block, because the model reaches for a ledger whenever someone
counts.

## ⛔ Look at every plate before writing a shot sheet (CEO 2026-09-18)

> "คุณเขียนบทหนัง แต่คุณไม่เคยดูภาพจริงของตัวละครและสถานที่นั้นๆ เลย"

Act 1 was written twice — 48 shots, then 34 — from appearance blocks I had typed
myself. Those blocks were my memory of the plates, not the plates. Opening one
montage afterwards found three errors in ninety seconds:

- the grandmother's hair was written "cropped very short and thinning"; the plate
  has a thick short white bob
- the lender was written "going soft at the waist" with "slicked-back" hair; the
  plate is a lean man with ordinary short hair
- **the shop's staircase was written "at the back"; in the plate it is in the
  middle of the room** — and the plate's loudest features, a central pillar and
  bright red, blue and green plastic stools, appear nowhere in any prompt

The last one is the dangerous kind: every prompt was describing a room that does
not exist, and the model was filling the gap by inventing one. That is exactly
the bedroom-drift we spent the day chasing.

**The rule: before writing or revising any shot sheet, look at every plate the
episode uses — characters, locations, props — at least once.**

### How to look, without burning the context

Do NOT open plates one at a time. An image costs context whether or not it
earned it, and fifteen separate looks cost fifteen times one look.

```bash
python3 tools/plate_montage.py <out.jpg> docs/reports/<plate-dir>/ [more dirs...]
```

It tiles everything into one labelled sheet, sized so faces stay readable — it
picks the column count from the plate count and targets ~1600px wide. Look at
that single image, write the appearance blocks **from what you see**, then write
the sheet.

If the montage has fallen out of context by the time you are revising, build it
and look again. Once per writing session is the cost, and it is cheap.

### Where the plates live

Plates are downloaded **once** and kept — the repo for now, Drive under the ILAG
rules once the folder is approved. Do not send an operator to re-download them
for every script; that is a paid browser run to fetch files we already have.

**When a character or location plate is regenerated, the stored copy must be
replaced in the same turn.** A stale plate is worse than none: it will be
believed, and every later script inherits the error.

## The spoken lines carry everything (CEO, and this is the hard one)

> "ตัวละครขับเนื้อเรื่อง คนดูเข้าใจแม้ไม่ได้ดูภาพ บทพูดต้องสมเหตุสมผล
> คนดูได้รับข่าวสารตรงไปตรงมา เป็นเส้นตรง"

**THE RULE (CEO 2026-09-18, refined the same day), three parts:**

1. **At least 80–90% of shots carry a spoken line.** Not 100% — that over-corrects
   into chatter. A line can be one word.
2. **Never two silent shots in a row.** One silent shot is allowed; the shot
   after it MUST speak. The CEO's phrase is *dead air*: `S1 พูด · S2 เงียบ · S3
   บังคับพูด · S4 แล้วแต่` — the moment there is silence, the next shot owes a line.
3. **A character doing something says what they are doing.** Carrying a bowl up
   to the grandmother? They talk on the way up. It re-explains the scene on a
   second channel, and a viewer who is only half-watching still follows.

Silence is a beat between lines, never a stretch of the film.

### DENSITY, not presence — measured the hard way, 2026-09-18

Act 1 was rewritten so that **every one of 48 shots carried a line**, the linter
said PASS, the words came out of the model correctly (84% verbatim by
speech-to-text), and the CEO watched the rough cut and said *"ดูไม่รู้เรื่องเลย"* —
the same verdict as the teaser the day before.

The measurement that explained it:

```
บทที่เขียน   ~7 พยางค์ ต่อช็อต 8 วินาที   =  พูด ~2 วิ  เงียบ ~6 วิ
คนไทยคุยปกติ  ~4-5 พยางค์/วินาที          =  ช็อต 8 วิ พูดเต็มได้ ~32-40 พยางค์
→ พูดแค่ 21% ของเวลา  ·  26 จาก 38 ช็อต มีบทไม่เกิน 8 พยางค์
```

**One short line per shot is dead air with a word in it.** The rule the CEO gave —
*"ตัวละครทำอะไรอยู่ให้พูดไปด้วย"* — was about **time**, not shot count: a
character talks for most of the shot, narrating what they do, replying, adding
the second thought. Three or four short lines, or one long one, **20–34
syllables per 8-second shot.**

The ceiling is real too: shot 48 carried ~40 syllables in four lines and the
model dropped the last two. Stay under ~34.

`tools/shotsheet_lint.py` now fails a shot under 20 syllables and warns over 34,
counted from the quoted Thai in the shot header. A sheet can pass the presence
rule and the dead-air rule and still be unwatchable; this is the check that
catches it.

### Two more, from the same day, both about *what* the line says

**Say it plainly. The listener never decodes.** `"...อีกแล้ว"` asks the audience to
work out that a job was refused; `"โดนปฏิเสธอีกแล้ว...เฮ้อ ที่นี่ก็ไม่รับ"` tells them.
A line that needs interpreting is a line that half the audience will miss. Put
the meaning in the character's mouth, in full.

**Before a character speaks, ask who is in earshot.** A plain line is a loud
line, and if two characters share a room, the other one hears it. That is the
trap the plain-speaking rule sets: the son saying "rejected again" out loud at
the counter would hand his secret to the father he is hiding it from, and the
next shot — him hiding it — collapses. The fix is staging, not mumbling: **move
the speaker out of earshot first** (he reads the phone in the back stairwell),
then let him say it in full.

The same question runs the other way, on purpose: the father counting coins
aloud in his mother's room is *meant* to be overheard — it is why she starts
counting too. So the check is not "is anyone listening" but "should this person
hear this, and does the story know it."

Both are in the shot sheet's header rules and are checked at the ledger stage
(who is in the room is a column, not an afterthought).

**These numbers are the CEO's and they bend to the story** — *"กฎนี้เปลี่ยนได้
ทุกเมื่อ ขึ้นอยู่กับเนื้อเรื่อง ตามประสงค์ของฉัน"*. A sheet that needs different
thresholds carries them on one line near its top, and that line must name the
CEO and the date, or the linter ignores it:

```
<!-- lint: min_spoken=0.70 max_silent_run=2 (CEO 2026-10-02: ฉากไล่ล่าเงียบ) -->
```

Nobody loosens the rule for convenience; the CEO loosens it for a scene.

**The test:** strip every image, every caption, every stage direction. Read the
dialogue cold. If it does not read like the film, the script fails — no matter
how good the shots are.

### The rule and the test are not the same thing, and confusing them cost a day

This file used to carry only the test. On 2026-09-18 that was enough to let Act 1
of «บัญชี» reach camera **50% silent, with two unbroken 48-second stretches** in
which a job rejection was hidden and a debt was split into three piles — both
plot the audience could only get by watching.

A test you run afterwards does not stop you building it wrong. And the artefact
used to run it — a transcript file holding only the spoken lines — **cannot show a
gap. It passes by construction.** The check could never fail, so it never did.

So the check now reads the SHOT SHEET, where gaps are visible, and it is a
script rather than a paragraph:

```bash
python3 tools/shotsheet_lint.py docs/scripts/<sheet>.md
```

It exits non-zero if fewer than 80% of shots speak OR any two silent shots sit
back to back, and prints the dead-air stretches worst-first. **Run it before a single credit is spent.**

### The rule makes the script better, it does not pad it

Every silent shot that had to be given a line came back stronger, because a shot
that cannot justify one line is usually a shot that is not doing anything:

- hands counting coins → the father counting **aloud**, which plants that he
  never writes a single figure down — the whole theme, in a mutter
- a face falling at a phone screen → `"...อีกแล้ว"`, and now a listener knows
  the son was rejected again
- an old woman staring at a gap in the floorboards → her grandson asking
  `"ข้างล่างเสียงดังไปไหมครับย่า"`, which plants that she hears everything below
- her hand gripping his sleeve → `"ย่าจะบอกอะไรผมเหรอ"`, which plants the
  reversal in words instead of hoping the audience reads a gesture

Consequences that bite in practice:

- **A reversal staged as an image is a failed reversal.** An insert of a bedframe
  covered in tally marks "carrying the whole turn with no line of exposition" was
  written into «บัญชี» and had to be thrown out. The marks stayed; the words that
  introduce them are what do the work.
- **Every number is spoken.** Not shown on a screen, not read off a phone. This
  is both a story rule and a production rule — see the Flow constraints below.
- **Every step follows from the one before, out loud.** If a character knows
  something, the audience heard how.

### Plausibility is part of the dialogue, not a note on it

Three holes that had to be closed in «บัญชี», as a checklist for the next script:

1. **How does the character get access?** The son reads his father's bank
   history because he installed the app years ago and his father hands him the
   phone to check the balance. The father gives away the evidence himself. No
   snooping, no contrivance.
2. **Where does the figure come from?** Derived out loud from two numbers the
   father states. Nobody does silent arithmetic on screen.
3. **Why is one source not enough?** The bank app only reaches back two years,
   which is what Thai banking apps really do. The rest comes from the
   grandmother. **Two insufficient sources are better than one convenient one** —
   and it turns a technology beat into a human one.

### Straight line, one flashback allowed
The spine runs forward. A flashback is permitted when a character is telling
someone what happened, and it must add no information the dialogue does not
already carry. If it costs shots, it is the first thing cut.

---

## ⛔ The character acts WHILE speaking, never before speaking (measured 2026-09-19)

Dead air does not come from short dialogue. It comes from the **action line**.

Twelve Act 1 shots were rendered and measured. The one shot that matched the
1.9M-view reference reel for silence was the one whose action happens *during*
the line. Every shot with a gap had an action the model performed first, in
silence, before anyone spoke:

| shot | action as written | result |
|---|---|---|
| 8 | "hauls the roll-up shutter open **and** turns to the street" — while calling out | **11% silent** ✅ |
| 12 | "leans toward a customer with a notepad, **then** calls the order back" | 56% silent |
| 7 | "**lets a breath out and** looks toward the doorway" | 44% |
| 10 | "**sets down a ladle and turns to face** his son properly" | 43% |
| 9 | three lines = two speaker changes | 40% |

Counter-evidence worth keeping in view: by a *second* measure (whisper speech
spans) every one of those shots carried **more** speech than the reference —
66–80% against its 49%, at 2.0–2.9 syllables per second against its 1.7. So this
is not "write more words". The dialogue is already denser than the thing that
worked. What differs is where the model puts the performance.

**So, when writing an action line:**

1. **Never write "then".** A "then" is a sequence, and the model renders the
   first half in silence. If two things genuinely happen in order, that is two
   shots.
2. **Put the action and the line in the same instant** — he says it *while*
   hauling the shutter, *while* ladling, *while* writing. Not after.
3. **No action that is itself a silence.** "lets a breath out", "pauses",
   "looks up and considers" — the model performs exactly that, and it costs a
   second every time.
4. **Every speaker change costs a beat.** Two speakers in a 6s shot is fine;
   three lines across two changes needs 10s, not 8.
5. One more, from the same measurement: the reference reel runs music and
   ambience under everything, so its gaps never sound empty. Ours are bare
   dialogue over room tone. **Some of the remaining difference is a score, not a
   script** — do not keep cutting the script to fix something the edit fixes.

## ⛔ Thai TTS stutters when a numeral, a classifier and a vocative collide

Rendered, then heard by the CEO, then confirmed by transcribing the clip:

- written: `เมื่อคืนผมส่งใบสมัครไปอีกสองที่พ่อ`
- spoken: `เมื่อคืนผมส่งใบสมัครไปอีก 2 ไปอีก 2 ที่พ่อ`

`สอง` + `ที่` + `พ่อ` run together with nothing between them, and the synthesiser
repeated the fragment. Rewritten as `…ไปอีกสองแห่งแล้วนะพ่อ` — a particle
between the count and the vocative.

**Put a particle between a number and the person being addressed.** A scan of
every other line in that act found no second instance, so this is a trap to
avoid rather than a common failure — but it is invisible on the page and costs a
re-shoot when it fires.

## Length, and where the money is

**18–24 minutes** (CEO: *"คนดูระหว่างกินข้าวไปด้วยได้"*). At 8-second shots:

| runtime | shots | mid-roll marks | Flow credits @12/shot |
|---|---|---|---|
| 18:24 | 138 | 9 | ~1,656 |
| 20:00 | 150 | 10 | ~1,800 |
| 24:00 | 180 | 11 | ~2,160 |

Facebook mid-rolls land at 1:00 and every two minutes after. **Every mark must
fall on a live question, a threat, or a turn in progress — never on atmosphere.**
Map them before writing prompts, and list what is unresolved at each one. Going
from 12 to 24 minutes does not double the work of selling the episode; it doubles
the ad inventory in a clip the viewer was going to finish anyway.

Budget roughly **1.4× the raw credit figure** for re-fires. That multiplier is an
estimate until a full episode has been shot — label it as one.

---

## The recurring assets — the channel's economics

An anthology throws away its cast every episode, which is expensive. ฟ้ามีตา
solves it with a fixed host and we copy that, harder:

- **A narrator, voice only.** No face, no reference image, no wardrobe. It cannot
  drift, it costs nothing to keep, and it does the host's entire job. It opens
  and closes every episode and it is the one thing viewers recognise.
- **One neighbourhood.** The same soi, the same street, the same shophouse
  exterior, different families. Half the location plates carry over for free.
- **The same opening and closing grammar** every week.

Everything else — cast, props, interiors — is built per story, and that is the
format working as intended, not waste.

---

## Production constraints that shape the writing (Google Flow)

The full operating manual is `google-flow-ops`. Three things belong here because
they change what you are allowed to write:

1. **Text and numbers render as garbage.** The model cannot write Thai script or
   digits legibly. Never write a shot that requires reading a screen, a sign, a
   receipt or a document. Our own dialogue rule already solves this — the numbers
   are spoken — so design around it deliberately: the phone is face down, the
   sign is out of focus, the ledger is scratches rather than writing.
2. **The prompt overrides the reference image, silently.** A detail a prompt does
   not mention is not preserved, it is surrendered. So every character, location
   and prop gets an **asset sheet** entry written by looking at the plate once,
   and every later prompt is assembled by quoting that sheet.
3. **A voice binds to the character, not the shot** — which is why this format
   can have three people arguing in one shot at all. Cast every speaking part
   before the first frame is generated, and never reuse a preset inside one
   story.

---

## Writing a new episode — the order of work

1. Pick the wrong. Everyday, recognisable, the kind of thing a viewer has seen a
   neighbour go through. Not a crime spectacular.
2. Name the power gap that makes it possible.
3. Choose the witness, and decide what they have to lose by speaking.
4. Choose the karma, and check it mirrors the wrong in FORM.
5. Choose the instrument of that karma — then go back to act one and **plant it**,
   as an ordinary scene with no signalling.
6. Write the conclusion table. Fill every row.
7. Write the dialogue. Only the dialogue.
8. **Read the dialogue cold.** If it does not read like the film, stop here.
9. Run `tig-scene-engine` over every sequence. An inert reversal — one that turns
   the plot but does not move the audience's verdict on a character — is the
   failure to hunt first.
10. Map the mid-roll marks and check each lands on tension.
11. **Pass the Structure gate below.**
12. Only now: shots, prompts, plates — then `CTO_Flow_Omni1.1_Continuity` over the sheet.

Steps 1–11 cost nothing. Step 12 costs credits. The order is the point.

## Structure gate — before the first shot is written (CEO 2026-09-23)

The CEO approved these after «จุดจบของเจ้าหนี้นอกระบบ», where four whole threads —
the hook, the police line, the lender's ending, the happy ending — were ordered by
the CEO AFTER a full cut existed, and each cost an insert, a re-shoot and a re-cut.
Every item is about the story, so it holds on any generator; only 8 depends on
Flow's free stills.

1. **Conflict on screen in the first 10 seconds.** Not mood, not the shop at dawn — a
   threat, a loss, a lie in progress. The film opened on a man alone at a wall; the
   CEO asked for the lender, the rain and the threat on screen.
2. **Every act ends on an open question — inside the episode.** At 18-24 minutes a
   Facebook viewer decides again every few minutes; the last line of an act is a
   reason to keep watching. This is not a cliffhanger into the next episode (rule 1
   still holds: the episode itself always closes).
3. **Every named character has want · turn · ending written down before shot 1** —
   the conclusion table (step 6) extended to every name. เชิด had no on-screen ending
   until the CEO asked for one; วิทย์'s reveal had no uniform.
4. **Every plant has its payoff shot numbered, and every payoff its plant.** A two-
   column table (plant shot → payoff shot); an empty cell is a hole. The scene ledger's
   rumour thread had no payoff and was caught by reading, not by the table.
5. **A reveal character is planted three times, without comment.** วิทย์ facing the
   door, never taking off his bag — so "he is police" lands as "of course".
6. **A change of place or time opens on a shot that says so.** A wide establishing
   shot on a new place; a jump in time ("หนึ่งปีต่อมา") gets a card or an unmistakable
   visual marker. `continuity_sheet.py` prints every such TRANSITION.
7. **The story is checked against what the generator refuses before it is locked.** On
   Flow: no handcuffs, no uniform next to police lights, no real currency, a night
   plate for every night scene, nobody healthy on a sickbed (see
   `CTO_Flow_Omni1.1_Continuity`). A beat the generator deletes is a beat to rewrite
   on paper, not after the credits are spent.
8. **One free still per scene before any video** (Flow's image model costs 0 credits).
   Staging, wardrobe, who is in frame and day/night are visible in a still; seeing
   them there is free, seeing them in a 720p clip costs ~12 credits a take.

## Field notes

- 2026-09-23 [MISSING] §Structure gate — four threads (hook, police line, lender's ending, happy ending) were ordered by the CEO after a full cut existed; each cost an insert + re-shoot + re-cut. Gate of 8 items added on the CEO's explicit approval ("OK เพิ่ม SKill ได้", 2026-09-23). · evidence: docs/scripts/banchi-RETRO.md, banchi shots 1-2, 174-190 · status: promoted
- 2026-09-24 [MISSING] cover — the skill says nothing about the episode cover. First try (ChatGPT, title in the prompt) put the title across the TOP; CEO: "คนแบบนี้ถูกแล้ว ติดแค่ข้อความ … มันจะมีจุดที่อยู่ประจำของมัน". Real Ch3 lakorn posters (ลายกินรี, คลื่นชีวิต, ลดา, เลือดเจ้าพระยา, 18 มงกุฎ) share one layout: channel logo top-left, producer top-right, faces in the upper 2/3, title logo big and centred in the lower third (small line over big gold line), English title under it, tagline near it, tiny billing at the very bottom. Generate the people only, then letter it with `tools/lakorn_poster.py` ($0, exact Thai, keeps the title inside Facebook's 4:5 feed crop, `--scale` when a low face would sit under the title). No face-changing cop clothes on a cover — it spoils the ending · evidence: task-d206afca, b5296b42 · status: pending
