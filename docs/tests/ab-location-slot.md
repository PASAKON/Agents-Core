# A/B test — does the location deserve a reference slot?

Status: **designed, not yet run.** Blocked on Gemini API access (see Cost).
Raised by the CEO 2026-09-07 against the CTO's first-draft doctrine.

## The question

On a vertical 9:16 shot, the first frame shows one narrow strip of the set.
Any camera move forces Veo to invent the space outside that strip, and it
invents differently every time. Does spending reference slot 3 on a **location
plate** hold the invented space steady across shots — enough to be worth the
slot it costs?

This cannot be answered from documentation. Both positions are coherent:

- **The first frame is enough.** It already fixes set, light, lens height and
  blocking. A location reference is paying twice for the same information.
- **The first frame is not enough.** It carries a strip; the model needs the
  room. Consistency across shots is the whole point of a serial.

## What is being measured

Not "does one clip look good". The production question is: **do three different
camera setups of the same room agree with each other about what the room is?**

## Design

**One location:** the noodle-shop counter area, `@noodle_shop`.

**Three camera setups, each of which reveals off-frame space** (a locked-off
shot tests nothing — the move is the instrument):

| Setup | Shot | Move | What it forces the model to invent |
|---|---|---|---|
| S1 | Medium on the counter | slow dolly back | ceiling, shelves behind |
| S2 | Reverse from behind the counter | pan left | the street doorway |
| S3 | Wide from the doorway | slow push in | the back of the shop |

**Three arms.** Everything is identical except reference slot 3:

| Arm | ref1 | ref2 | ref3 |
|---|---|---|---|
| **A** | @father_somchai | @son_ton | **@noodle_shop (location plate)** |
| **B** | @father_somchai | @son_ton | **@prop_envelope** |
| **C** | @father_somchai | @son_ton | *(empty — only two refs)* |

C is the control for "does location help at all". B is the control for "what
you give up to find out".

**Held constant across every generation:** the same first-frame plate per setup,
the same prompt text, the same two character references, Veo 3.1 Fast, 8s,
9:16, 720p. If the API exposes a seed, fix it — the docs we read do not mention
one, so verify at implementation and record whether it was available.

**Runs:** 3 setups x 3 arms = **9 clips**. One pass. Extend to a second pass
only if the result lands inside the noise band below.

**The location plate itself must be ONE clean wide photograph of the room.**
Never a contact sheet or a multi-panel layout — a grid going in produces a grid
coming out, which cost the org real money on a previous project.
Open sub-question, do not confound it into this test: whether that plate should
be 16:9 (more spatial information) or 9:16 (matches the output). Fix it at 16:9
for this run and note it; vary it only if arm A wins.

## Scoring — binary, five questions, per arm

Lay the three setups of one arm side by side and answer yes/no. Score 0-5.

1. Are the walls the same colour and material in all three?
2. Are the shelves / fridge in the same position relative to the counter?
3. Is the doorway on the same side in all three?
4. Does the light come from the same direction in all three?
5. Are the floor and counter the same material in all three?

The CTO scores from extracted frames (0s, 4s, 7.9s of each clip). The CEO
watches the nine clips and makes the final call — the score exists to stop the
call being made on vibes, not to replace it.

## Decision rule — fixed BEFORE the test runs

| Result | What changes |
|---|---|
| **A beats C by >= 2 points** | Location earns a permanent slot. New default: 2 speakers + location; the hero prop moves into the first frame. Rule 1 of the doctrine is rewritten. |
| **A and C within 1 point** | The first frame is sufficient. Current working default stands, and it stops being provisional. |
| **B beats A** | The prop matters more than the room. Current default stands, and props are confirmed as the right occupant of slot 3. |
| **All three score <= 2** | Set drift is not solvable at the reference layer at all. Escalate: build the set once, then chain every frame (`lastFrame` -> next `image`) and never cut to a fresh plate inside a scene. |

## Cost

9 clips x Veo 3.1 Fast 720p 8s at $0.10/s = **$7.20 ≈ THB 256.**
A second pass, if needed, doubles it.

**This test requires the API** — Flow's web UI has no first-frame slot, so the
variable under test cannot even be set there. That means a Gemini API key with
billing enabled, which the org does not have yet. **CEO approval required before
any spend.**

## Sequencing

- **Phase 0 — free, do now.** Finish the EP1 script. Generate the character,
  prop and location plates inside Flow (measured at 0 credits) and download
  them. The location plate is an input to this test anyway.
- **Phase 1 — THB ~256, needs approval.** Run the nine clips, score, decide.
- **Phase 2 — free.** Rewrite Rule 1 with the answer and re-audit the shot table.

The answer is reusable for every episode and every future series, which is why
it is worth settling properly before shooting sixty shots on a guess.
