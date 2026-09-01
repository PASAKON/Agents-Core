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
