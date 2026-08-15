# Prompts for task-cda4f469 — supplied by the CTO

**REVISED by the CEO, 12 Aug 10:40. This supersedes the earlier version of this
file and anything in TASK.md about Scene 4A / 4B.**

Copy these VERBATIM into Higgsfield. Do not edit, shorten, or paraphrase them.
Paste with a synthetic `ClipboardEvent` (text/plain only) — never keystroke
simulation, which silently truncates and has already produced unusable footage.
Verify the pasted length matches the source before touching Generate.

## ELEMENT MAP — read this before writing or pasting any prompt

**32 `@Element` plates exist. Prompts referenced only 12 of them until 2026-08-13.**
Twenty plates the CEO built were never referenced by any prompt, so the model
invented those objects and locations from the text instead of using the real
plate. That is the single biggest cause of wasted re-renders on this project.

**Write every prompt from this table, never from memory.** If a scene contains
a thing that has a plate, the plate must be tagged. "อันไหนที่จำเป็นต้องใส่ มันต้องใส่."

### The room distinction that has already caused errors

| Element | What it actually is |
|---|---|
| `@Room-Guest` | The rooms she goes in to **work** — 209, 213. Clean, serviced. |
| `@Room-Clean` | **Room 214, her own room**, before. Never cleaned by her. **Not the same room as `@Room-Guest`.** |
| `@Room-Wreck` | **Room 214 after** — torn bedding, chair over, glass shattered, suitcase spilling. |

Every Scene 9 and Scene 10 shot happens in **214**, so they take
`@Room-Clean` or `@Room-Wreck` — never `@Room-Guest`.

### Cancelled plates — never reference these

`@Room-Clean-Rev`, `@Room-Wreck-Rev` (use `@Room-Clean` / `@Room-Wreck`),
`@Room-DoorOut-Down` (use `@Room-DoorOut`), `@Prop-Glasses` (the CEO removed
reading glasses from the film entirely).

**⚠️ Scenes 4, 5, 6, 7 and 8 still tag `@Motel-Walkway` and therefore CANNOT be
generated as written** — the plate is copyright-flagged and blocks the render
outright. Those five scenes already have delivered clips, so nothing is queued
and nothing is broken today. **Do not queue any of them without asking the CEO
first.** They were left alone deliberately rather than rewritten: dropping the
plate means the model invents the walkway, and these clips are already
consistent with each other. If the CEO ever wants one re-rendered, the walkway
gets described in plain words the way Scene 9A now does, and he should expect
the exterior to look different from the existing takes.

### HARD CAP — Seedance 2.0's real working maximum is 9 DISTINCT elements, not 10

**Confirmed 2026-08-14 (task-0ee4a20a).** 10-D sat at exactly 10 and failed
3/3 with `Something went wrong. Please try again, or change your input files
or prompt.` — a generic error Higgsfield never attributes to the count, and
which reads identically to a content rejection. Dropping one element (same
beat, same plates, same NEGATIVE section) generated first try. **Treat 9 as
the ceiling. Never write or attach 10.**

| Scene | Distinct elements | Headroom |
|---|---|---|
| 9C, 10-B, 10-C, 10-D | 9 | zero — at the real ceiling |
| everything else | 1-5 | plenty |

**The cap is on elements ATTACHED to the composer, not on mentions in the
text.** A composer carrying leftover chips from an earlier scene will blow past
ten as soon as the new scene's set is attached, and the platform then reports
it sees no usable prompt at all. **Clear every existing chip before attaching a
new scene's set.**

If a scene ever needs more than ten, drop in this order — last dropped first:

1. **Characters** — never drop. They must match across the whole film.
2. **Location** — never drop. It defines the entire frame.
3. **Props the shot turns on** — the photograph, the wallet, the thing the
   story is about. Never drop.
4. **Props that are set dressing** — drop these first and describe them in
   plain words instead. `@Prop-Lamp` and `@Prop-Vase` are the usual candidates:
   they establish the room but the shot does not depend on them.

### Scene → element map

| Scene | Location | Characters | Props |
|---|---|---|---|
| 4 | `@Room-Guest` | `@Mother` | `@Prop-Caddy` `@Prop-Vase` `@Prop-Lamp` |
| 5 | `@Motel-Walkway` | `@Mother` | `@Prop-Caddy` `@Prop-RoomKey` |
| 6 | `@Room-Guest` | `@Mother` | `@Prop-Caddy` `@Prop-Towels` |
| 7 | `@Motel-Walkway` `@Room-Window214` | `@Mother` | `@Prop-DNDTag` |
| 8 | `@Motel-Walkway` `@Room-DoorOut` | `@Mother` | `@Prop-DNDTag` |
| 9A | `@Room-Clean` `@Room-DoorOut` | `@Mother` | `@Prop-DNDTag` `@Prop-Handbag` `@Prop-Phone` |
| 9B | `@Room-Bathroom` | `@Mother` | — |
| 9C | `@Room-Clean` | `@Mother` | `@Prop-Ring` `@Prop-Phone` `@Prop-Handbag` `@Prop-Wallet` `@Prop-OldPhoto` `@Prop-Lamp` `@Prop-Vase` |
| 9D-A/B/C | `@Room-Clean` | `@Mother` | `@Prop-Wallet` `@Prop-OldPhoto` `@Prop-Lamp` |
| 10-A | `@Room-Clean` → `@Room-Wreck` | `@Mother` | `@Prop-OldPhoto` `@Prop-Glass` `@Prop-Handbag` |
| 10-B/C | `@Room-Clean` → `@Room-Wreck` `@Room-DoorOut` | `@Mother` `@Daughter` | `@Prop-OldPhoto` `@Prop-Glass` `@Prop-Handbag` `@Prop-Lamp` |
| 10-D | `@Room-Clean` → `@Room-Wreck` `@Room-DoorOut` | `@Mother` `@Mother-Soul` `@Daughter` | `@Prop-OldPhoto` `@Prop-Glass` `@Prop-Lamp` |
| 10-D (Seedance 2.5) | `@Room-Clean` → `@Room-Wreck` `@Room-DoorOut` | `@Mother` `@Mother-Soul` `@Daughter` | `@Prop-OldPhoto` `@Prop-Glass` `@Prop-Lamp` `@Prop-Handbag` |
| 11A | `@Room-Wreck` `@Room-DoorOut` | `@Mother` `@Daughter` | `@Prop-Glass` |
| 11B | `@Room-Wreck` | `@Mother` `@Mother-Soul` `@Daughter` | `@Prop-Glass` |
| 11C | `@Room-Wreck` | `@Mother` `@Mother-Soul` `@Daughter` | `@Prop-OldPhoto` `@Prop-Glass` `@Prop-Lamp` |
| 11D | `@Room-Wreck` | `@Mother-Soul` `@Daughter` | — |
| 11D-B | `@Room-Wreck` | `@Mother-Soul` `@Daughter` | — |
| 12-A | `@Stop-Work` | `@Mother` `@Father` | — |
| 12-FB1 (Seedance 2.5) | `@Stop-Work` `@Bus-Interior` `@House-Night` `@House-Day` | `@Mother` `@Father` `@Daughter` | `@Prop-Handbag` `@Prop-BusCord` `@Prop-Ring` |
| 12-FB2 (Seedance 2.5) | `@Motel-Front` `@Motel-Lobby` `@Room-DoorOut` `@Room-Clean` → `@Room-Wreck` | `@Mother` `@Father` | `@Prop-RoomKey` `@Prop-Lamp` `@Prop-Glass` `@Prop-DNDTag` |
| 12-FB (Seedance 2.5, alternate to FB1+FB2) | `@Stop-Work` `@Bus-Interior` `@House-Night` `@House-Day` `@Motel-Front` `@Motel-Lobby` `@Room-DoorOut` `@Room-Clean` → `@Room-Wreck` `@Motel-Walkway` | `@Mother` `@Father` `@Daughter` | `@Prop-Handbag` `@Prop-BusCord` `@Prop-Ring` `@Prop-RoomKey` `@Prop-Lamp` `@Prop-Glass` `@Prop-DNDTag` |

### Plates that exist but no written scene uses yet — CEO to confirm

`@Motel-Stairs` `@Motel-Utility` `@House-Day` `@Prop-DinnerPlates`
`@Stop-Motel` `@Prop-Checklist` `@Prop-PhonePhoto`

(`@Motel-Front`, `@Motel-Lobby`, `@House-Night`, `@Bus-Interior`,
`@Prop-BusCord`, `@Father`, `@Stop-Work` are now used, by 12-A through 12-E
above. `@House-Day` and `@Prop-DinnerPlates` are used by Scene 13, already
written earlier in this file — not re-listed here since that block predates
this map row and wasn't captured when the map was first built.)

These read like her journey to work and a home/family thread — Scenes 1-3 and
possibly 12-16, none of which have prompts written. **Do not guess where they
belong.** They are listed here so nobody forgets they exist.

### The trap in Scene 9

In the Scene 9 blocks the daughter appears **only as the child inside
`@Prop-OldPhoto`**, never as a person in the room. **Do not tag `@Daughter`
in any Scene 9 prompt** — it would put the actual character into room 214 and
destroy the whole premise, which is that she is alone.

## HOW TO WRITE A PROMPT — the rules, in order

Every rule below exists because breaking it cost us a re-render or a wasted
day. Follow them in this order.

**1. Start from the ELEMENT MAP above, never from memory.** Look up the scene,
read what is in it, and tag every one of those elements. Writing from memory is
what produced prompts referencing 12 of 32 plates.

**2. If a thing has a plate, it must be tagged.** Not "a plain gold ring" —
`@Prop-Ring`. Not "guest room 214" — `@Room-Clean`. Not "her daughter" —
`@Daughter`. An untagged thing is a thing the model invents from scratch, and
it will invent a different one every take.

**3. Tag the LOCATION in the opening line of every prompt.** It is the single
most-forgotten tag and the most expensive one to get wrong.

**4. Check the room.** `@Room-Guest` is where she works (209, 213).
`@Room-Clean` / `@Room-Wreck` is room 214, her own. Scenes 9 and 10 are all 214.

**5. Never reference a cancelled plate**: `@Room-Clean-Rev`, `@Room-Wreck-Rev`,
`@Room-DoorOut-Down`, `@Prop-Glasses`.

**6. Never reference `@Motel-Walkway`.** It is flagged for copyright and blocks
generation outright — it killed Scenes 7 and 8. Describe walkway light as
"the open doorway" or "corridor light" in plain words instead.

**7. Structure, always in this order:** `VISUAL` with timecoded beats →
`NEGATIVE — strictly avoid:` → the grounded-camera / lighting / grade line →
`AUDIO-SFX`.

**8. Write NEGATIVE against what the model will add on its own,** not against
what you already said. The model reaches for the shot it has seen a thousand
times, so forbid it by name: a hand pushing an object that should move by
itself, a face where the film hides faces, a glow on a character who must read
solid, eyes in a darkness that must stay empty, a push-in during a held beat.

**9. Put the reason in the prompt when it changes the image.** "She has been
dead more than a day and the image must read that way" does more work than any
adjective about the stain.

**10. Say what must NOT repeat.** Two identical framings before and after a
change is the most recognisable horror device there is, and it is what tripped
the copyright filter on the original Scene 10-A Jump Cut.

**11. Contradictions between variants are deliberate.** 10-B forbids any glow;
10-D requires it. 9D-A hides her face; 9D-B reveals it. Never "harmonise" them.

**12. The operator pastes VERBATIM.** No appended lines, no timecode
adjustments, no fixing anything that reads oddly. Only settings change. If a
prompt is wrong, it is fixed here, in this file, by the CTO or the CEO.

## The rule for every shot

Every scene gets exactly **two prompts**, and **each prompt is generated twice** —
once for real, once as a spare in case the first comes out unusable. Same prompt
text both times, no edits between runs.

| Scene | Prompt | Runs |
|---|---|---|
| 4 | Long Take 20s | ×2 |
| 4 | Jump Cut 20s | ×2 |
| 5 | Long Take 20s | ×2 |
| 5 | Jump Cut 20s | ×2 |
| 6 | Long Take 20s | ×2 |
| 6 | Jump Cut 20s | ×2 |
| 7 | Long Take 20s | ×2 |
| 7 | Jump Cut 20s | ×2 |
| 8 | Long Take 20s | ×2 |
| 8 | Jump Cut 20s | ×2 |

**20 generations total.** One at a time. Settings every time: Seedance 2.5 ·
**20s** · 720p · High · Sound ON · **Unlimited Mode ON**. Re-verify the toggle
before every single click — it silently resets on page reload, and it was
showing a live "130" earlier today.

## Scene 4 is being REPLACED

The four existing Scene 4 clips (the old 4A/4B interior and exterior 9-second
splits) are **retired**. The CEO is replacing all four with the two 20-second
prompts below, which merge the interior and exterior beats into one shot each.
**Generate them fresh. Ignore every earlier instruction about never regenerating
4A.** Leave the old clips in the folder; do not delete anything.

Save each finished clip into the folder matching its scene in the left sidebar
(`Sence 4`, `Sence 5`, `Sence 6`, `Sence 7`, `Sence 8`); create the folder if absent.

---

## Scene 4 — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. @Mother's face is never seen clearly at any point. Use @Room-Guest for the room interior and @Motel-Walkway for the exterior walkway.

0–6s: Inside guest room 209. Camera behind @Mother at shoulder height. She stands at the dresser beside @Prop-Lamp, adjusting the dry stems in @Prop-Vase, then wipes the mirror with a cloth. Warm lamp light, everything calm and ordinary.
6–10s: One hard percussive BANG from outside, close but muffled through the wall. Her hands stop. She straightens slowly and looks toward the door. A second BANG, louder and flatter. She sets the cloth down.
10–14s: She crosses to the room door. The camera follows her in the same unbroken move, staying behind her shoulder.
14–20s: She opens the door a hand's width and leans her head and one shoulder out into the amber sconce light of the open-air walkway, the rest of her still inside the dark room. She looks off to the RIGHT along the walkway. Several doors down, two people in their late twenties stand outside their own door, both in plain black — one in a black leather jacket, the other in a dark hooded top and heavy boots. They are mid-conversation, one gesturing while the other turns half away. Neither ever looks toward her. She withdraws and the door closes quietly.

CRITICAL — the two people must NEVER look toward @Mother, never glance down the walkway, never pause, never react to her door opening or closing. They behave exactly as if that doorway were empty. There is a clear gap of several rooms between them.

WARDROBE — no printed logos, no band graphics, no brand marks, no slogans, no text of any kind on any clothing. Plain black garments only.

NEGATIVE — strictly avoid: no interior corridor, no doors facing across a passage, no ceiling panels, no fluorescent light. The walkway is OPEN-AIR against black night.

Grounded real-camera look, no lens flare, no haze, no whip pans. Warm amber bare-bulb sconces and the room's table lamp are the only light sources. Muted and desaturated.

AUDIO-SFX
Ceramic scraping softly on wood. Dry stems rustling. Cloth squeaking on glass. Then one hard percussive BANG — a heavy door slammed outside, close but wall-muffled, no sting or riser. Room tone. A second BANG, louder and flatter. A door hinge. Two raised voices overlapping outside, clipped, words never intelligible. A door closing quietly underneath them. No music. No dialogue from @Mother.
```

## Scene 4 — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. @Mother's face is never seen clearly in any cut.

Cut 1 (0–5s): Inside guest room 209, tight on @Mother's hands adjusting the dry stems in @Prop-Vase on the dresser beside @Prop-Lamp.
Cut 2 (5–9s): Close on a cloth wiping the mirror. A hard BANG lands and the hand stops dead against the glass.
Cut 3 (9–13s): Exterior. From the parking lot of @Motel-Front, low and wide on wet asphalt and the lit ground-floor office window. Still. A second BANG, flatter.
Cut 4 (13–17s): Same position, now tilted up to the second-floor walkway. On the LEFT, a room door open a hand's width, @Mother's head and one shoulder leaning out into the amber light, the rest of her hidden inside. She looks off RIGHT.
Cut 5 (17–20s): Tighter on the RIGHT end of the walkway: two people in their late twenties outside their own door, both in plain black — one in a black leather jacket, the other in a dark hooded top and heavy boots. Mid-conversation, one gesturing while the other turns half away. They never look left, never react. At the far edge of frame, @Mother's door closes.

CRITICAL — the two people must NEVER look toward @Mother, never glance down the walkway, never pause, never react to her door.

WARDROBE — no printed logos, no band graphics, no brand marks, no slogans, no text of any kind on any clothing. Plain black garments only.

NEGATIVE — strictly avoid: no interior corridor, no facing doors, no ceiling panels, no fluorescent light. OPEN-AIR walkway only.

Grounded real-camera look, no whip pans, no lens flare, no haze. Warm amber bulbs and the lit office window are the only light against black night. Muted and desaturated.

AUDIO-SFX
Ceramic scraping on wood, dry stems rustling, cloth squeaking on glass. One hard percussive BANG, close but wall-muffled, no sting or riser. Ringing silence over distant road noise and dripping water. A second BANG, louder and flatter. A soft door hinge. Two raised voices overlapping, clipped, words never intelligible. A door closing quietly. Cuts land on the bangs. No music. No dialogue from @Mother.
```

> **Content-flag history for Scene 4 — read before retrying.** The old 4B was
> rejected twice. Two causes, both already fixed above: conflict language
> ("arguing", "fighting") read as domestic violence, and "band tee" / rock-band
> clothing is an IP violation under the festival's Section 5. If it flags again,
> soften the two people further — describe posture and gesture only, and drop
> "clipped" and "raised" from the audio line. Retry ONCE, then skip and log it.

---

## Scene 5 — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Camera sits on the exterior walkway of @Motel-Walkway, framed on two adjacent doors: room 213 on the LEFT and room 214 on the RIGHT with @Prop-DNDTag hanging on its handle. Both doors stay in frame the entire shot. The camera never moves. @Mother's face is never seen clearly.

0–6s: @Mother walks in from the LEFT carrying @Prop-Caddy, stops at door 213, unlocks it and pushes it open. Warm lamp light spills out onto the concrete.
6–10s: @Mother steps inside 213 and is gone from frame for a beat. Then a slow, deliberate KNOCK sounds from inside 214 — three spaced beats, unhurried.
10–15s: @Mother backs out of 213 onto the walkway, still holding @Prop-Caddy, and turns to face door 214. She stands looking at it, at a clear distance of at least an arm's length, never closer. @Prop-DNDTag hangs still on the handle.
15–20s: She holds there, weight shifting once as if about to step forward, then does not. She turns away, steps back into 213 and pulls that door closed behind her. The walkway is left empty, both doors shut.

NEGATIVE — strictly avoid: @Mother must NEVER touch, brush against, bump or make contact with door 214, its handle, @Prop-DNDTag, the doorframe or the guardrail. @Prop-DNDTag does not move at all in this shot. No other people anywhere in frame. This is an OPEN-AIR walkway — no interior corridor, no doors facing across a passage, no ceiling panels, no fluorescent light.

Grounded real-camera look, locked-off, no lens flare, no haze. Warm amber bare-bulb sconces against black night. Muted and desaturated.

AUDIO-SFX
Bottles shifting in the caddy. A key in a lock, a door opening. Her footsteps stopping. Then THREE slow knocks from behind door 214 — dry, wooden, evenly spaced, coming from inside the room. Dead silence after them. Her shoes turning on concrete. A door pulled shut. Very distant road noise underneath. No music. No dialogue.
```

## Scene 5 — JUMP CUT (20s)

```
VISUAL
Handheld, five cuts across 20 seconds. @Mother's face is never seen clearly at any point.

Cut 1 (0–5s): Close on @Mother's hand turning a key in the lock of door 213 on the walkway of @Motel-Walkway, @Prop-Caddy hanging from her other hand.
Cut 2 (5–8s): From inside room 213 looking back at its open doorway as @Mother steps through into the room.
Cut 3 (8–12s): Tight on @Mother's shoes on the carpet, stopping mid-step. Held. Three slow knocks land off-screen — the sound is coming through the wall to her right.
Cut 4 (12–16s): Out on the walkway of @Motel-Walkway: @Mother stands facing door 214, seen from behind at a clear arm's length distance. @Prop-DNDTag hangs perfectly still on the handle. She does not move.
Cut 5 (16–20s): Close on her shoes turning away on the concrete, then the door of 213 pulled closed. Hold a beat on the two shut doors.

NEGATIVE — strictly avoid: @Mother must NEVER touch, brush against, bump or make contact with door 214, its handle, @Prop-DNDTag, the doorframe or the guardrail. @Prop-DNDTag does not move at all in this scene. No other people in any frame. OPEN-AIR walkway only — no interior corridor, no facing doors, no ceiling panels, no fluorescent light.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Warm amber sconces against black night. Muted and desaturated.

AUDIO-SFX
A key in a lock. A door opening. Footsteps on carpet stopping dead. THREE slow dry knocks through a wall — evenly spaced, unhurried, unmistakably from the next room. Long silence. Shoes turning on concrete. A door pulled shut. Cuts land on the knocks, never before them. No music. No dialogue.
```

---

## Scene 6 — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. @Mother's face is never seen clearly. Spoken dialogue is heard but her mouth is never in clear view.

0–7s: Inside room 213, camera behind @Mother at shoulder height as she works at the bed. A heavy BANG hits the wall to her right — the wall she shares with 214. She flinches, a small sharp jolt of the shoulders, not a scream. She straightens and looks at that wall.
7–12s: @Mother sets what she is holding down and walks out of frame toward the door. The shot continues without cutting as the camera follows her out onto the exterior walkway of @Motel-Walkway and settles behind her, framing her from the back as she stands facing door 214 with @Prop-DNDTag on its handle.
12–20s: @Mother raises a hand and knocks twice on door 214, then speaks. She waits. Nothing answers — no sound, no movement, @Prop-DNDTag does not stir. She stands in the silence until the shot ends on her back and the closed door.

DIALOGUE (spoken by @Mother, calm and professional, slightly raised so it carries through a door):
"Housekeeping."
(pause)
"Everything okay in there?"

NEGATIVE — strictly avoid: apart from her two knocks, @Mother must NEVER touch, push, lean on or make contact with door 214, its handle, @Prop-DNDTag or the doorframe. She does not try the handle. She does not press her ear to the door. No other people in frame. OPEN-AIR walkway — no interior corridor, no doors facing across a passage, no ceiling panels, no fluorescent light.

Grounded real-camera look, no lens flare, no haze. Warm amber sconces against black night. Muted and desaturated.

AUDIO-SFX
Quiet work sounds. Then one heavy dull BANG against a shared wall — percussive, close, no sting or riser before it. Her sharp intake of breath. Footsteps to the door, hinge, shoes onto concrete. Two firm knuckle knocks on a hollow door. Her line, then room tone. Absolute silence in reply — no shuffle, no breath, nothing. Distant road noise far underneath. No music.
```

## Scene 6 — JUMP CUT (20s)

```
VISUAL
Handheld, five cuts across 20 seconds. @Mother's face is never seen clearly; her mouth is never in clear view when she speaks.

Cut 1 (0–4s): Tight on @Mother's hands working at the bed inside room 213. A heavy BANG lands and her hands jolt.
Cut 2 (4–8s): Close on the bare wall to her right — the wall shared with 214 — still faintly trembling, a picture frame on it settling.
Cut 3 (8–12s): Low on her shoes crossing the carpet fast and stepping out onto the concrete of @Motel-Walkway.
Cut 4 (12–16s): From behind @Mother, framed on door 214 with @Prop-DNDTag on the handle. Her hand comes up and knocks twice. She speaks.
Cut 5 (16–20s): Hold on the closed door and @Prop-DNDTag, perfectly still, no answer. Her shoulder sits at the edge of frame, unmoving.

DIALOGUE (spoken by @Mother, calm and professional, slightly raised so it carries through a door):
"Housekeeping."
(pause)
"Everything okay in there?"

NEGATIVE — strictly avoid: apart from her two knocks, @Mother must NEVER touch, push, lean on or make contact with door 214, its handle, @Prop-DNDTag or the doorframe. She does not try the handle. @Prop-DNDTag never moves in this scene. No other people in any frame. OPEN-AIR walkway only — no interior corridor, no facing doors, no ceiling panels, no fluorescent light.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Warm amber sconces against black night. Muted and desaturated.

AUDIO-SFX
Work sounds, then one heavy dull BANG against a shared wall — percussive, close, no sting or riser. A frame rattling on the wall. Fast footsteps, carpet to concrete. Two firm knuckle knocks on a hollow door. Her line. Then absolute silence in reply — no shuffle, no breath, nothing at all. Cuts land on the impacts and the knocks. No music.
```

---

## Scene 7 — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. On the open-air walkway of @Motel-Walkway outside room 214. @Mother's face is never seen clearly — for most of the shot it is pressed toward the glass and away from camera. @Prop-DNDTag hangs on the door handle throughout and never moves.

0–8s: Camera sits low and to the side, framing @Mother from behind and slightly below as she steps to the WINDOW beside door 214 — not the door itself. She cups both hands against the glass to block the sconce glare and leans in, trying to see through a narrow gap in the drawn curtains. She holds there, very still, shoulders tight.
8–12s: From inside the room, a sharp CRASH of breaking glass. She jerks back hard, one full step, hands coming off the window. The curtains do not move. Nothing else changes.
12–20s: Knocking begins from inside the room — slow at first, then faster and more insistent, building steadily through the rest of the shot. @Mother turns toward the door. Her hand rises and hovers a few inches above the handle, trembling slightly, and never touches it. Hold on the hovering hand and the still @Prop-DNDTag as the knocking keeps building.

NEGATIVE — strictly avoid: there is NO peephole and she never uses one. She must NEVER touch the door, the handle, @Prop-DNDTag or the doorframe in this shot — the hand only hovers. @Prop-DNDTag does not move or swing at any point. No other people in frame. No face at the window from the inside, nothing visible through the curtain gap. OPEN-AIR walkway — no interior corridor, no doors facing across a passage, no ceiling panels, no fluorescent light.

Grounded real-camera look, no lens flare, no haze, no whip pans. Warm amber bare-bulb sconces against black night. Muted and desaturated.

AUDIO-SFX
Shoes on concrete. Palms settling on glass. Her breathing, shallow and close. Then a sharp CRASH of a glass breaking on a hard floor inside the room — no sting, no riser, no music under it. Her sharp intake of breath and a scuff as she steps back. Silence. Then knuckles on a hollow door from the inside — slow, then quickening, then hammering, louder through to the end. Distant road noise far underneath. No music. No dialogue.
```

## Scene 7 — JUMP CUT (20s)

```
VISUAL
Handheld, five cuts across 20 seconds. @Mother's face is never seen clearly in any cut. @Prop-DNDTag never moves.

Cut 1 (0–5s): Close on @Mother's cupped hands pressed against the window glass beside door 214, blocking the sconce glare. Her reflection is broken and unreadable.
Cut 2 (5–8s): Reverse, from just behind her shoulder — the narrow gap in the drawn curtains, dark and giving nothing away.
Cut 3 (8–12s): A sharp CRASH inside. Tight on her hands snapping back off the glass, one full step of retreat.
Cut 4 (12–16s): Low on the door of 214 with @Prop-DNDTag hanging perfectly still, as knocking starts from inside — slow, then quickening.
Cut 5 (16–20s): Tight on her hand hovering a few inches above the door handle, trembling, never touching it. The knocking hammers on to the end of the shot.

NEGATIVE — strictly avoid: there is NO peephole and she never uses one. She must NEVER touch the door, the handle, @Prop-DNDTag or the doorframe — the hand only hovers. @Prop-DNDTag does not move or swing. No other people in any frame. Nothing visible through the curtain gap, no face at the window. OPEN-AIR walkway only — no interior corridor, no facing doors, no ceiling panels, no fluorescent light.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Warm amber sconces against black night. Muted and desaturated.

AUDIO-SFX
Palms settling on glass. Shallow close breathing. A sharp CRASH of a glass breaking on a hard floor inside the room — no sting, no riser. Her intake of breath, a scuff of retreat, silence. Then knuckles on a hollow door from the inside, slow then quickening then hammering. Cuts land on the crash and on the knocks. No music. No dialogue.
```

---

## Scene 8 — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. On the open-air walkway of @Motel-Walkway outside room 214. @Mother's face is never seen clearly — the camera stays behind and slightly below her throughout. @Prop-DNDTag hangs on the handle and must still be hanging there at the end of the shot.

0–6s: Tight on @Mother's hand hovering a few inches above the door handle. Knocking hammers from inside the room, fast and insistent. She does not move.
6–10s: The knocking stops dead, mid-beat. Complete silence. Her hand stays where it is. Her shoulders rise and fall once.
10–15s: Her hand closes on the handle and turns it slowly. The latch gives. The door swings inward away from camera into darkness. Warm amber light from the walkway falls in a widening wedge across the floor just inside.
15–20s: The camera follows her from behind as she steps up to the threshold and stops there, framed in the doorway with the dark room ahead of her. Hold on her back and the open door. The interior stays dark and unresolved — we never see what she is looking at.

NEGATIVE — strictly avoid: do NOT reveal the room interior, do not light it, do not show furniture, a bed, a body, or any person inside. Everything past the threshold stays in darkness. @Prop-DNDTag must remain hanging on the handle and must not fall off or be removed. No other people in frame. No peephole. OPEN-AIR walkway — no interior corridor, no doors facing across a passage, no ceiling panels, no fluorescent light.

Grounded real-camera look, no lens flare, no haze, no whip pans, no push-in past the threshold. Warm amber bare-bulb sconces against black night. Muted and desaturated.

AUDIO-SFX
Knuckles hammering on a hollow door from the inside, fast and insistent — then stopping dead mid-beat. Absolute silence. Her breathing, close and unsteady. A latch turning, slow and mechanical. A door hinge opening long and dry. Then nothing at all from inside the room — no shuffle, no breath, no movement. Her shoes on the concrete as she steps to the threshold. Distant road noise far underneath. No music. No dialogue.
```

## Scene 8 — JUMP CUT (20s)

```
VISUAL
On the open-air walkway of @Motel-Walkway outside room 214. Handheld, five cuts across 20 seconds. @Mother's face is never seen clearly in any cut. @Prop-DNDTag stays on the handle throughout.

Cut 1 (0–5s): Tight on @Mother's hand hovering above the door handle of 214, trembling, as knocking hammers from inside.
Cut 2 (5–8s): Close on @Prop-DNDTag hanging on the handle, perfectly still. The knocking stops dead mid-beat. Silence.
Cut 3 (8–12s): Her hand closes on the handle and turns it. Tight on the latch giving.
Cut 4 (12–16s): Low and behind her, the door swinging inward into darkness, warm walkway light spreading in a wedge across the floor just inside.
Cut 5 (16–20s): From behind, @Mother stopped at the threshold, framed in the open doorway with the dark room ahead. Hold on her back. The interior stays dark.

NEGATIVE — strictly avoid: do NOT reveal the room interior, do not light it, do not show furniture, a bed, a body, or any person inside. Everything past the threshold stays in darkness. @Prop-DNDTag must remain hanging on the handle. No other people in any frame. No peephole. OPEN-AIR walkway only — no interior corridor, no facing doors, no ceiling panels, no fluorescent light.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze, no push past the threshold. Warm amber sconces against black night. Muted and desaturated.

AUDIO-SFX
Knuckles hammering on a hollow door from the inside — then stopping dead mid-beat. Absolute silence. Close unsteady breathing. A latch turning slowly. A long dry hinge. Nothing at all from inside the room. Shoes on concrete. Cuts land on the silence and on the latch. No music. No dialogue.
```

---

# SCENE 9 — NEW, added by the CEO 2026-08-12 23:20

Scene 9 is split into sub-shots `S9-A`, `S9-B`, `S9-C`, `S9-D` — siblings, with
no bare `S9`. 9D itself has three variants, 9D-A / 9D-B / 9D-C, all generated.

Same rule as everything above: **each prompt runs twice**, real plus spare, same
text both times, Recreate for the second run.

## SHE TOUCHES NOTHING — hard rule, governs every shot in Scene 9 (CEO 2026-08-13)

**Why she is in the room at all: she heard a loud noise from 214 and came to
check what it was.** She is a housekeeper and she is a decent person. She would
not handle a guest's belongings, and the film must never give an audience a
reason to wonder whether she might.

So, without exception, across 9A, 9B, 9C and every 9D variant:

- **She never picks up, lifts, holds, opens, turns over, moves or pockets
  anything that belongs to the guest.** Not the ring, not the phone, not the
  wallet, not the photograph, not the handbag. Her hand may come near an object
  and withdraw. That is the entire vocabulary.
- **Every object that moves, moves by itself.** The wallet tips off the
  nightstand on its own. The photograph slides across the carpet on its own.
  Nothing visible pushes any of it — no hand, no arm, no sleeve, no wind, no
  curtain, no shadow, no tilt of the furniture.
- **The handbag stays closed and untouched** for the whole scene.

A generator will reach for the object on its own, because a hand picking
something up is the shot it has seen a thousand times. Every 9-series NEGATIVE
block states this explicitly for that reason. **A clip in which she touches any
guest property is wrong and needs a regen, however good it looks.**

## She is investigating, not cleaning — governs Scenes 7, 8 and 9 (CEO 2026-08-13)

From the moment she goes to the window in Scene 7, **she has stopped working.**
She is not servicing room 214 and never was — she is checking on a sound. Every
shot from 7 onward must read that way.

Concretely, and this is the part a generator gets wrong on its own:

- **@Prop-Caddy is not in her hands.** She carried it in Scene 5; by Scene 7 she
  has set it down. No caddy, no cloth, no bin bag, no towels, no cart anywhere in
  frame for the rest of the film.
- **She never cleans, tidies, straightens or services anything** in 214. She
  looks and she listens. She does not handle what she finds.
- Her hands move like someone checking a room, not working one.

The 9A dialogue is still right — announcing yourself is what a housekeeper does
before entering any room, including one she is worried about. The words sell the
professionalism; her hands have to sell that the job has stopped.

## The one rule that governs all three

**Scene 9 must not reveal the wreckage or the body.** The room reads as an
ordinary occupied guest room: lived-in, personal things lying about, nothing
violent. No blood, no corpse, no broken glass, no overturned furniture, no
disturbed bedding. All of that is Scene 10's reveal, and showing it early
destroys the ending the same way revealing the interior would have destroyed
Scene 8.

The horror here is **sound and absence**, never a visible threat. Nothing
supernatural appears on camera at any point — no figure, no face, no shadow that
moves on its own.

## Scene 9A — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Clean — room 214 — entered through @Room-DoorOut from the open-air corridor outside. @Prop-DNDTag hangs from the outside handle of @Room-DoorOut and swings as the door opens. @Mother's face is never seen clearly — the camera stays behind her shoulder throughout.

0–5s: @Room-Clean is pitch dark. @Mother is a silhouette in @Room-DoorOut, lit only from behind by the amber corridor light. She reaches to the wall switch and presses it. Nothing happens.
5–10s: She presses again. The ceiling light stutters — three false starts, each flash showing a fragment of @Room-Clean, which reads as an ordinary occupied guest room, before dropping back to black. On the fourth it holds, weak and warm and uneven.
10–15s: She takes two slow steps in and stops, scanning the room. She speaks.
15–20s: She stands still, listening. @Room-Clean is lived-in and quiet: @Prop-Handbag closed on the nightstand, @Prop-Phone lying face-down beside it, a jacket over the chairback. Hold on her back and the still room.

DIALOGUE (spoken by @Mother, calm and professional — the standard announce a hotel housekeeper uses before entering):
"Housekeeping. I'm coming in."
(pause)
"Hello? Anybody in here?"
(pause)
"Sorry to disturb."

NEGATIVE — strictly avoid: no blood, no body, no person other than @Mother, no broken glass, no overturned furniture, no disturbed or bloodied bedding, no signs of a struggle of any kind. The room is tidy and ordinary. Nothing supernatural is visible — no figure, no face, no shadow moving by itself. Do not show the bathroom interior. No mirror reflection of anyone.

Grounded real-camera look, no lens flare, no haze, no whip pans. The only light sources are the amber corridor light behind her through @Room-DoorOut and the weak ceiling light once it holds. Muted and desaturated.

AUDIO-SFX
A door swinging wide on a dry hinge. Her shoes on carpet. A wall switch clicking — once, twice, a third time. Electrical ticking and a low hum as the light stutters, then settles to a faint buzz. Her line, spoken into an empty room. Room tone. Absolute silence in reply. Distant road noise far underneath. No music.
```

## Scene 9A — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Clean — room 214 — entered through @Room-DoorOut. @Mother's face is never seen clearly in any cut.

Cut 1 (0–4s): A black frame with a thin amber edge — her silhouette filling @Room-DoorOut, corridor light behind her, @Prop-DNDTag hanging from the outside handle.
Cut 2 (4–8s): Tight on her hand at the wall switch. Press. Nothing. Press again.
Cut 3 (8–12s): The ceiling light stuttering — three hard flashes, each showing a slice of @Room-Clean as an ordinary occupied guest room, black between them. On the last it holds.
Cut 4 (12–16s): From behind her shoulder as she takes two steps into @Room-Clean and stops. She speaks.
Cut 5 (16–20s): Slow hold on the quiet room past her — @Prop-Handbag closed on the nightstand, @Prop-Phone face-down beside it. Nothing moves.

DIALOGUE (spoken by @Mother, calm and professional — the standard announce a hotel housekeeper uses before entering):
"Housekeeping. I'm coming in."
(pause)
"Hello? Anybody in here?"
(pause)
"Sorry to disturb."

NEGATIVE — strictly avoid: no blood, no body, no person other than @Mother, no broken glass, no overturned furniture, no disturbed bedding, no signs of a struggle. Nothing supernatural visible — no figure, no face, no self-moving shadow. Do not show the bathroom interior. No mirror reflection of anyone.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Amber corridor light through @Room-DoorOut and a weak ceiling light only. Muted and desaturated.

AUDIO-SFX
A dry hinge. Shoes on carpet. A wall switch clicking three times. Electrical ticking and hum as the light stutters, settling to a faint buzz. Her line into an empty room. Room tone, then silence. Cuts land on the switch clicks and on the flashes. No music.
```

## Scene 9B — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Clean — room 214 — lit by one weak warm ceiling bulb. Use @Room-Bathroom as the reference for the ensuite bathroom behind the door — same tile, same fittings, same layout. @Mother's face is never seen clearly.

0–6s: Camera behind @Mother at shoulder height as she moves slowly through @Room-Clean, looking rather than cleaning. She has not touched anything yet.
6–9s: From the bathroom, a sudden hard CLATTER — something small and solid dropping into a basin, followed by a slap of water on tile. She freezes mid-step, shoulders jolting once.
9–14s: She turns and crosses to the bathroom door, which stands ajar on a black gap. The camera follows her in the same unbroken move and settles behind her at the threshold.
14–20s: She pushes the door wide. The bathroom is empty, dry, everything in its place — nothing running, nothing fallen, nothing out of order. She holds there. A single slow drip falls from the tap. Hold on her back framed in the doorway.

NEGATIVE — strictly avoid: nothing is in the bathroom — no person, no figure, no face, no reflection of anyone in the mirror, no shape behind the shower curtain, no hand, no movement. The bathroom is completely ordinary and completely empty. No blood, no body, no broken glass anywhere in this shot. No sign of a struggle in the main room behind her. Nothing supernatural is ever visible on camera.

Grounded real-camera look, no lens flare, no haze, no whip pans, no sudden zoom. One weak warm ceiling light in the room, one cold tile-light in the bathroom. Muted and desaturated.

AUDIO-SFX
Quiet footsteps on carpet, her breathing steady. Then from the bathroom one sharp CLATTER of a hard small object landing in a ceramic basin and a slap of water on tile — sudden, close, loud, with no sting, no riser and no music before or after it. Her sharp intake of breath. Footsteps to the door, a hinge. Then nothing at all, until one single slow drop lands at the very end. Room tone. Distant road noise far underneath. No music. No dialogue.
```

## Scene 9B — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Clean — room 214 — and its bathroom; use @Room-Bathroom as the reference for the bathroom, same tile, same fittings, same layout. @Mother's face is never seen clearly in any cut.

Cut 1 (0–5s): From behind her shoulder as she moves slowly through the lit @Room-Clean, looking rather than working.
Cut 2 (5–8s): A hard CLATTER off-screen. Tight on her hands stopping dead mid-air, then her shoulder turning toward the bathroom.
Cut 3 (8–12s): Low on her shoes crossing the carpet fast toward the ajar bathroom door and its black gap.
Cut 4 (12–16s): From behind her as she pushes the door wide. The bathroom is empty, dry, undisturbed.
Cut 5 (16–20s): Hold on the empty bathroom past her shoulder. One slow drop falls from the tap into the basin.

NEGATIVE — strictly avoid: nothing is in the bathroom — no person, no figure, no face, no reflection of anyone in the mirror, no shape behind the shower curtain, no hand, no movement of any kind. No blood, no body, no broken glass anywhere. No sign of a struggle in the room behind her. Nothing supernatural is ever visible on camera.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Weak warm room light, cold tile-light in the bathroom. Muted and desaturated.

AUDIO-SFX
Quiet footsteps on carpet, steady breathing. One sharp CLATTER of a hard small object into a ceramic basin plus a slap of water on tile — sudden, close, loud, no sting, no riser, no music. Her sharp intake of breath. Fast footsteps, a hinge. Then complete silence, until one slow drop lands at the very end. Cuts land on the clatter and on the door opening. No music. No dialogue.
```

## Scene 9C — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Clean — room 214, her own room, never serviced. @Prop-Lamp stands unlit on the nightstand; the only light is one weak warm ceiling bulb. @Prop-Vase sits on the dresser with its dry stems. @Mother's face is never seen clearly — the shot stays low and close on her hands and the objects.

0–6s: Her hands move slowly across the surfaces of @Room-Clean, taking things in rather than tidying them. @Prop-Ring sits alone on the nightstand beside @Prop-Lamp. She does not pick @Prop-Ring up; her hand hovers over it and moves on.
6–11s: @Prop-Phone lies face-down on the nightstand. Her hand comes near it, hesitates, and withdraws without turning it over. It stays exactly as it was.
11–15s: @Prop-Wallet lies out in the open on the nightstand, beside @Prop-Handbag, which stays closed. Her hand comes near @Prop-Wallet, stops short, and withdraws without touching it. She straightens slightly and begins to turn away.
15–20s: With nothing near it, @Prop-Wallet tips off the edge of the nightstand on its own and drops straight down — heavy, dead weight, one short fall, landing flat on the carpet by her feet and falling open. @Prop-OldPhoto is thrown loose in the air as it opens, and falls completely differently: thin paper catching the air, tipping onto one edge, gliding sideways, stalling, turning over once slowly, drifting the way a dry leaf comes off a branch. It touches the carpet face-down and slides on a little further, toward the dark gap beneath the bed, and stops there. Hold on the fallen photograph as the shot ends.

NEGATIVE — strictly avoid: no blood, no body, no person other than @Mother, no broken glass, no overturned furniture, no disturbed bedding, no signs of a struggle. She never touches, lifts, holds or opens @Prop-Wallet at any point, and never reaches into the handbag — the handbag stays closed and untouched for the whole shot. Nothing visible causes the wallet to fall: no hand, no arm, no sleeve, no wind, no moving curtain, no shadow crossing it, no tilt of the furniture. No eyeglasses, reading glasses or spectacles anywhere in frame, on any surface or on anyone. Do not show @Mother's face, and do not make her recognisable as the young woman in the photograph — the audience must be able to wonder. Nothing supernatural is visible. No mirror reflection of anyone. The photograph shows exactly two people, an adult woman and a small girl, and no one else.

Grounded real-camera look, locked and low, no lens flare, no haze, no whip pans. One weak warm ceiling light, deep shadow at the edges. Muted and desaturated — except the photograph, which carries the faded warm colour of an old print.

AUDIO-SFX
Fabric and leather moving under her hands. A phone lifted and set back down on wood. Then a small soft leather object tipping off wood and landing flat on carpet, dull and close. A single sheet of old photographic paper sliding free and settling, almost too quiet to hear. Her breathing stops for a beat. Room tone. Distant road noise far underneath. No music. No dialogue.
```

## Scene 9C — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Clean — room 214. @Mother's face is never seen clearly in any cut — every frame stays on hands and objects.

Cut 1 (0–4s): Macro on @Prop-Ring sitting alone on the nightstand of @Room-Clean. Her hand enters, hovers over it, withdraws without touching.
Cut 2 (4–8s): @Prop-Phone lying face-down on the nightstand. Her hand enters, stops short of it, withdraws. @Prop-Phone is never turned over and never leaves the nightstand.
Cut 3 (8–12s): @Prop-Wallet lying out in the open on the nightstand, beside @Prop-Handbag, which stays closed. Her hand enters frame, stops short of it, and withdraws.
Cut 4 (12–16s): @Prop-Wallet alone in frame, still, no hands anywhere near it. It tips on its own and falls out of the bottom of frame. Hold a beat on the empty nightstand.
Cut 5 (16–20s): Low on the carpet by her feet — @Prop-Wallet lying where it landed, fallen open, and @Prop-OldPhoto settling face-up against her shoe: the small faded snapshot of a young woman with a small girl. Hold on it.

NEGATIVE — strictly avoid: no blood, no body, no person other than @Mother, no broken glass, no overturned furniture, no disturbed bedding, no signs of a struggle. She touches nothing in this room at any point — she never touches, lifts, holds, turns over or opens @Prop-Ring, @Prop-Phone, @Prop-Handbag or @Prop-Wallet in any cut. @Prop-Handbag stays closed and untouched throughout. Her hands come near and withdraw; every object that moves, moves on its own. Nothing visible causes the wallet to fall: no hand, no arm, no sleeve, no wind, no moving curtain, no shadow crossing it, no tilt of the furniture. No eyeglasses, reading glasses or spectacles anywhere in frame, on any surface or on anyone. Do not show @Mother's face, and do not make her recognisable as the young woman in the photograph. Nothing supernatural visible. No mirror reflection of anyone. The photograph shows exactly two people, an adult woman and a small girl, and no one else.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. One weak warm ceiling light, deep shadow at the edges. Muted and desaturated — except the photograph, which keeps the faded warm colour of an old print.

AUDIO-SFX
Room tone and her breathing, close. No handling sounds at all — nothing is picked up, nothing is set down, because she touches nothing. Then, unprompted, a small soft leather object tipping off wood and landing flat on carpet, dull and close. A sheet of old photographic paper sliding free and settling, almost inaudible. Her breathing stopping for a beat. Cuts land on the wallet leaving frame and on the photograph settling. No music. No dialogue.
```

## Scene 9D — three variants, all generated, best one chosen in the edit

Scene 9 now ends on **recognition**: she understands the photograph is her and
her daughter. Her face has been withheld for the entire film up to this point,
so 9D-B and 9D-C spend that withheld face here, at the exact moment she knows.
9D-A is the quieter version that never shows it. Generate all three, real plus
spare each. The edit picks.

## Scene 9D-A — LONG TAKE (20s) — the under-bed hold

Built on one idea: the camera is already under the bed when the shot begins, so
the audience is placed as whatever is in there, and she comes down toward them.
Nothing is ever actually under the bed — the dread is entirely the audience's
own projection, and putting anything there would collapse it.

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Clean — room 214, her own room, never serviced. @Prop-Lamp stands unlit on the nightstand above; one weak warm ceiling bulb somewhere above and behind camera is the only light. The camera sits ON THE FLOOR, lens at carpet height, tilted a few degrees up — the angle you only get by putting your cheek against the ground. The underside edge of the bed frame cuts across the upper third of frame, and behind it the gap beneath the bed is a solid horizontal band of black running the full width of the shot. Everything is composed so the audience is looking OUT from under the bed, never at it.

0–5s: Nothing moves at all. @Prop-Wallet lies open on the carpet in the near foreground, exactly where it fell. @Prop-OldPhoto lies FACE-DOWN a little beyond it, right at the edge of the darkness, half in the weak warm light and half swallowed by the black — only its blank back is visible. Past them both, the band of black under the bed. The frame is completely still. Room tone only.

5–11s: @Mother's shoes enter at the far edge of frame. She lowers herself slowly — one knee down onto the carpet, then a hand planted flat beside the photograph to take her weight. The movement is careful and tired, not frightened: she is only picking up what fell. Her body fills the right of frame, but the black band behind her stays unbroken and visible across the whole width.

11–16s: She lowers her head toward the fallen wallet to look at it, without reaching for it and without touching it — and at that level her eyeline lands square on the dark under the bed. She stops. Her hand, still flat on the carpet, stops. She does not recoil, does not flinch, does not look away. She simply goes still — far too still — looking into the black.

16–20s: Hold. The camera does not move, does not push in, does not rack focus, does not cut. The black band under the bed fills the back of frame and stays perfectly uniform: no shape resolves out of it, nothing emerges, nothing catches light. Only fine carpet dust drifting in the light at the very edge of the gap. Her breathing has stopped. The shot ends on the darkness, not on her.

NEGATIVE — strictly avoid: nothing whatsoever is under the bed. No creature, no face, no eyes, no eyeshine, no hand, no fingers, no silhouette, no reflection, no glint, no movement, no shape emerging or receding. The gap must read as ordinary empty darkness for the entire 20 seconds — the moment anything is visible there, the shot is worthless. No jump scare, no sudden motion, no camera push-in, no zoom, no rack focus, no music sting, no bass drop. No blood, no body, no broken glass, no overturned furniture, no disturbed bedding, no signs of a struggle. No person other than @Mother. She never opens @Prop-Wallet. No eyeglasses, reading glasses or spectacles anywhere in frame, on any surface or on anyone. Do not show @Mother's face clearly, and do not make her recognisable as the young woman in the photograph. No mirror, no reflection of anyone. Nothing supernatural is visible. The photograph shows exactly two people, an adult woman and a small girl, and no one else.

Grounded real-camera look, locked off on the floor, no handheld drift, no lens flare, no haze, no vignette added. One weak warm ceiling light from behind camera, deep true black under the bed with no lift and no detail recovered in it. Muted and desaturated — except the photograph, which keeps the faded warm colour of an old print.

AUDIO-SFX
Room tone, close and dry, carrying the whole shot. A knee settling onto carpet. A palm pressing flat into carpet pile. Her breathing, audible and steady, then stopping mid-cycle and not resuming. Distant road noise far underneath. Deliberately NO sound from under the bed at any point — no breath, no shift, no scrape, no low tone, no rumble. The silence where a sound belongs is the effect. No music, no sting, no riser, no dialogue.
```

## Scene 9D-B — LONG TAKE (20s) — the photograph, the dark, and her face

The photograph slides toward the dark on its own, something builds under the
bed as if it is finally coming out, the dark takes it and then gives it back to
her, and the camera turns to her face for the first time in the film. **Her face
is deliberately revealed here** — this shot inverts the rule every earlier scene
obeyed. She never touches the photograph.

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Clean — room 214, her own room, never serviced. @Prop-Lamp stands unlit on the nightstand; the only light is one weak warm ceiling bulb. The camera begins low, at carpet height, and does not cut at any point.

0–4s: THE FALL, in full. @Prop-OldPhoto comes off the edge of the nightstand and does not drop. It is thin old paper and it behaves like thin old paper: it tips onto one corner, catches the air, and swings out flat. It glides sideways for a moment, stalls, tips the other way, and turns over once, slowly, showing its blank back and then its face and then its back again. It sinks in small stages rather than a single fall, the way a dry leaf comes off a branch and takes its time about reaching the ground.

4–9s: It touches the carpet at last, edge first, and skids. It does not stop where it lands. It slides on across the pile, still moving, toward the band of solid black beneath the bed that runs across the back of frame. As it travels, the room tone thins away and a low sound rises out from under the bed — not a growl, not a voice, something felt in the chest more than heard, building steadily and getting closer.

9–13s: The photograph slides into the dark and comes to rest there FACE-DOWN, half in the weak warm light and half swallowed by the black. The sound stops dead the same instant — total silence, no decay, no tail. Nothing comes out of the gap. Nothing moves in it.

13–17s: @Mother lowers herself onto the carpet, one knee then a flat palm. She reaches into the dark under the bed — her hand and forearm are the only part of her that enters the black — finds the photograph, closes on it, and draws it back out into the light. She turns it face-up in her fingers.

17–20s: The camera rises and turns, for the first time in the film, to find her FACE, lit only by the weak ceiling bulb, looking down at what she is holding. She is the young woman in the picture, older now, unmistakably the same person. Her expression changes — no scream, no tears, just a slow arrival of understanding and then something worse behind it. End on her face.

NEGATIVE — strictly avoid: nothing is ever visible under the bed. No creature, no face, no eyes, no eyeshine, no silhouette, no shape emerging, no movement in the dark. Her own hand and forearm reaching in at 13-17s are the ONLY things that ever enter or leave that gap — nothing else, and nothing reaches back, touches her, or follows her hand out. The gap reads as ordinary empty blackness for the whole shot. During the fall itself nothing visible moves the photograph: no hand, no arm, no wind, no curtain, no shadow crossing it, no tilt of the floor — it falls and slides entirely on its own. She does not touch @Prop-Wallet or any other guest property at any point; the photograph is the one thing she picks up. The room stays completely ordinary — no blood, no body, no wreckage, no broken glass, no disturbed bedding, no signs of a struggle. No person other than @Mother. Nothing glows, nothing is translucent, no ghost, no double exposure. No jump scare, no sting, no flash, no camera shake. The photograph shows exactly two people, an adult woman and a small girl, and no one else.

DELIBERATE EXCEPTION TO THE FILM'S USUAL RULE: in this shot her face IS shown, clearly lit and clearly readable, and she MUST be recognisable as the same woman as the young woman in the photograph. Do not hide, shadow, blur or crop her face in the final beats.

Grounded real-camera look, no lens flare, no haze, no whip pans. One weak warm ceiling light, deep true black under the bed with no detail recovered in it. Muted and desaturated — except the photograph, which keeps the faded warm colour of an old print.

AUDIO-SFX
Room tone, close and dry. The photograph in the air makes almost nothing — a faint dry flutter of old paper turning over, twice, barely there. Then its edge touching carpet, and a longer papery slide across the pile. Under all of it a low tone rising from beneath the bed — building, felt in the chest, no melody, no growl, no voice, no words. It cuts to complete silence the instant the photograph comes to rest in the dark, with no tail and no reverb, and it never returns at any point after. Then only her: a knee settling onto carpet, a palm pressing flat, the small dry scrape of her hand finding paper in the dark, and her breathing, close, stopping once when she turns it face-up. No music, no sting, no riser, no dialogue.
```

## Scene 9D-C — JUMP CUT (20s) — same beat, harder

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Clean — room 214 — one weak warm ceiling bulb. @Prop-Lamp stands unlit on the nightstand and never comes on.

Cut 1 (0–4s): Macro, carpet height. @Prop-OldPhoto face-up on the carpet of @Room-Clean — a young woman with a small girl. @Prop-Wallet lies open on the carpet just behind it, where it fell. The photograph begins to slide away from camera on its own.
Cut 2 (4–8s): The gap under the bed filling the frame, a wall of solid black. @Prop-OldPhoto enters at the bottom edge, still sliding toward it.
Cut 3 (8–12s): @Prop-OldPhoto stopped at the very lip of the darkness, half lit, half black. Held. Nothing comes out.
Cut 4 (12–16s): @Prop-OldPhoto sliding back OUT of the darkness on its own, face-up, coming to rest on the carpet in front of her feet, @Prop-Wallet still lying where it fell. No hand in frame.
Cut 5 (16–20s): Her FACE, close, lit by the weak ceiling bulb, looking down at @Prop-OldPhoto on the floor then up into the empty room. She never touches it. She is unmistakably the woman in the picture, older. Hold on her.

NEGATIVE — strictly avoid: nothing visible under the bed at any point — no creature, face, eyes, eyeshine, hand, silhouette or movement; the gap is ordinary empty blackness. Nothing visible moves the photograph. The room stays ordinary — no blood, no body, no wreckage, no broken glass, no disturbed bedding. No person other than @Mother. Nothing glows, nothing translucent, no ghost, no double exposure. No sting, no flash, no camera shake. The photograph shows exactly two people and no one else.

DELIBERATE EXCEPTION: her face IS shown in Cut 5, clearly lit and clearly readable, and she MUST be recognisable as the same woman as in the photograph.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Deep true black under the bed with no detail recovered. Muted and desaturated except the photograph.

AUDIO-SFX
Room tone. Paper sliding on carpet. A low tone rising from under the bed across cuts 1 to 3, building, felt more than heard, no growl and no voice. Dead silence from the moment the photograph disappears into the black, and it never returns. Only her breathing over Cut 5. Cuts land on the silence, never on the sound. No music, no sting, no riser, no dialogue.
```

---

# SCENE 10 and SCENE 11 — the two-layer reveal

Scene numbering does not change: **10 is the mirror**, **11 is the daughter**,
exactly as the original outline had them. Scene 11 is now split into `S11-A`,
`S11-B`, `S11-C` as siblings, no bare `S11`.

**Order matters and it is the whole design.** She learns the truth in 10, alone,
before anyone else arrives. The audience gets it with her. Then 11 shows the
world confirming it. Reversing these turns the film from something the viewer
reasons alongside into a surprise ending.

**Scene 10 is the first frame in the film allowed to show the wreckage.**
Everything before it — including all of Scene 9 — keeps the room ordinary.

## Scene 10-A — LONG TAKE (20s) — the mirror (she learns alone)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of room 214 — it begins as @Room-Clean and ends as @Room-Wreck. @Prop-Lamp stands unlit on the nightstand. @Mother's face is never seen clearly, including in reflection — the mirror shows her from behind and to the side, her features soft and unreadable.

0–5s: @Mother straightens from the carpet where @Prop-OldPhoto fell. She turns slowly toward a tall full-length mirror on the wall. Behind her is @Room-Clean, ordinary and occupied — tidy bed, @Prop-Handbag closed on the nightstand, everything in place.
5–10s: She stops in front of the mirror and stands very still, looking at her own reflection. Her shoulders drop. She has understood something.
10–16s: Still in the same unbroken shot, the room reflected in the mirror changes from @Room-Clean into @Room-Wreck around her, gradually and without any cut or flash: the bedding pulls into a violent tangle, the armchair goes over onto its side, @Prop-Glass lies shattered across the carpet, the suitcase gapes open with clothes spilling out. The reflection becomes the room as it truly is.
16–20s: The camera holds as the real room behind her catches up to match its own reflection and becomes @Room-Wreck too. She does not move. Hold on her back, the wrecked room, and her unreadable reflection.

NEGATIVE — strictly avoid: no body, no corpse, no person other than @Mother anywhere in frame or in the reflection. No blood. Her face is never clearly readable, in the room or in the mirror. The change must be a continuous physical transformation of the set — no cut, no flash, no dissolve, no ghost, no double exposure, no second figure appearing. Nothing glows.

Grounded real-camera look, locked off, no lens flare, no haze, no whip pans. One weak warm ceiling light. Muted and desaturated.

AUDIO-SFX
Her clothes shifting as she straightens. Slow footsteps on carpet, stopping. A long silence with only room tone. Then, under the transformation, fabric dragging, wood tipping and settling, glass fragments ticking against each other on the floor — quiet, close, physical, arriving as if these sounds had always been in the room and are only now audible. No sting, no riser, no music. Her breathing, once, at the end.
```

## Scene 10-A — JUMP CUT (20s) — the mirror (she learns alone)

```
VISUAL
Five cuts across 20 seconds. Interior of room 214 — it begins as @Room-Clean and ends as @Room-Wreck. @Mother's face is never seen clearly in any cut, including in reflection.

Cut 1 (0–4s): Low, @Prop-OldPhoto face-up on the carpet of @Room-Clean. Her shoes enter frame and stop beside it.
Cut 2 (4–8s): From behind her as she turns toward a tall full-length mirror. In the reflection the room is @Room-Clean, ordinary — tidy bed, @Prop-Handbag closed on the nightstand.
Cut 3 (8–12s): Closer on the mirror. Her reflection stands still, features soft and unreadable. Her shoulders drop.
Cut 4 (12–16s): The same mirror framing — the reflected room is now @Room-Wreck: bedding tangled, armchair on its side, @Prop-Glass shattered across the carpet, the suitcase open and spilling.
Cut 5 (16–20s): The real room behind her is @Room-Wreck too, matching its reflection. She has not moved. Hold.

NEGATIVE — strictly avoid: no body, no corpse, no person other than @Mother in frame or in the reflection. No blood. Her face is never clearly readable. No ghost, no double exposure, no second figure, no glow. The change is a change of set state between cuts, nothing more.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. One weak warm ceiling light. Muted and desaturated.

AUDIO-SFX
Shoes stopping on carpet. Long room tone. Then fabric dragging, wood tipping, glass ticking on the floor — quiet, close, physical, no sting, no riser, no music. Cuts land on the silence, never on the sounds. Her breathing once at the end.
```

## Scene 10-A — JUMP CUT (rev) (20s) — same beat, different visual grammar

**Use this only if the original 10-A Jump Cut keeps failing.** That block was
rejected once for copyright at 24 minutes and then overran past 107 minutes on
its retry, while the 10-A Long Take — same scene, same elements, same mirror,
same wreckage — rendered clean twice at 20-25 minutes. So the mirror and the
wrecked room are NOT the problem; something about the Jump Cut's specific
framing is.

What changed here: the original repeated an identical mirror framing before and
after the change, which is an extremely recognisable horror device and the most
likely thing an output-side copyright check would match. This version never
repeats a composition, comes at the mirror obliquely and in pieces rather than
head-on, and carries the reveal on different parts of the room instead of one
hero shot. The story beat is untouched.

```
VISUAL
Five cuts across 20 seconds. Interior of room 214 — it begins as @Room-Clean and ends as @Room-Wreck. @Prop-Lamp stands unlit on the nightstand. @Mother's face is never clearly readable in any cut, including in reflection. No two cuts share a camera position or focal length.

Cut 1 (0–4s): Very low and close on the carpet, @Prop-OldPhoto face-up at the edge of frame. Her shoes enter, stop, and she begins to straighten — we follow only to her knees.
Cut 2 (4–8s): Behind her shoulder, tight, as she turns. A mirror edge cuts into the right of frame at an angle; we see a sliver of reflected room, not a full reflection. It reads as @Room-Clean and ordinary — made bed, @Prop-Handbag closed on the nightstand.
Cut 3 (8–12s): Her hands hanging at her sides, framed at waist height. They open slowly, then still. Behind her, out of focus, the sliver of mirror. Nothing has changed yet.
Cut 4 (12–16s): A different corner of the real room entirely, now @Room-Wreck — the armchair on its side and @Prop-Glass in pieces across the carpet, shot from floor level. No mirror in this frame at all.
Cut 5 (16–20s): Wide and high, the whole of @Room-Wreck settled: bedding pulled into a tangle, suitcase open and spilling, @Mother standing small in the middle of it with her back to camera. Hold.

NEGATIVE — strictly avoid: no body, no corpse, no person other than @Mother anywhere in frame or in any reflection. No blood, no stain, no wound. Her face is never clearly readable. No ghost, no double exposure, no second figure, no transparency, nothing glowing. Never show the same framing twice, and never show a full head-on view of a full-length mirror with a figure centred in it. No cut, flash or dissolve used to depict the change itself — the room simply IS wrecked from Cut 4 onward. No jump scare, no camera push-in, no zoom, no whip pan, no lens flare, no haze.

Grounded real-camera look, natural handheld weight, varied angles. One weak warm ceiling light, deep shadow at the edges. Muted and desaturated.

AUDIO-SFX
Her clothes shifting as she straightens. Slow footsteps on carpet, stopping. A long silence carried on room tone alone. From Cut 4, fabric dragging, wood settling, glass fragments ticking against each other on the floor — quiet, close, physical, arriving as if these sounds had always been in the room and are only now audible. Cuts land in the silence, never on a sound. No sting, no riser, no music. Her breathing, once, at the end.
```

## Scene 10-B — LONG TAKE (20s) — police burst in, GROUNDED (nothing supernatural)

The reveal delivered from outside instead of by the mirror. The jump scare is
the door; everything after it is slow motion in total silence. **In this variant
@Mother is photographed as an ordinary solid person** and the daughter simply
never sees her — no glow, no transparency. 10-D is the opposite treatment of
this same beat; generate both and choose.

```
VISUAL
Single continuous take, 20 seconds. Interior of room 214, at night — it begins as @Room-Clean and ends as @Room-Wreck. @Prop-Lamp stands unlit on the nightstand; the only light is one weak warm ceiling bulb until the door opens.

0–3s: Behind @Mother, tight on the back of her head and shoulders — we look past her at what she is looking at, and her face is not in frame at all. @Prop-OldPhoto is held low in her hands and readable over her shoulder. Beyond her the room is @Room-Clean and ordinary — tidy bed, @Prop-Handbag closed on the nightstand. Three hard impacts land on @Room-DoorOut and a muffled shout comes through it. Real time, real sound.

3–5s: @Room-DoorOut bursts inward. At the exact frame it opens the image drops into SLOW MOTION and every sound falls away to nothing.

5–10s: Two police officers come through the doorway first, moving slowly, faces NEVER visible — framed from behind, or from the chest down, or with the head cropped out of frame. Corridor light throws hard shapes past them and dust turns slowly in it.

10–14s: @Daughter enters behind them — a young woman now, not the small girl in @Prop-OldPhoto, her face streaming with tears. She runs forward toward @Mother, arms already opening to take hold of her.

14–17s: @Daughter passes @Mother without touching her and drops onto the bed — and the room is no longer @Room-Clean, it is @Room-Wreck. The bedding is torn and tangled, the armchair is over on its side, @Prop-Glass lies shattered across the carpet, the suitcase gapes open with clothes spilling out. @Mother's body lies on the bed, and the white sheet beneath it carries a wide dark rust-brown stain, long dried into the weave and stiff at its edges — old, not recent. @Daughter takes hold of the body and holds it.

17–20s: Hold, still in slow motion and still in total silence, on @Daughter holding the body, with @Mother standing untouched in the same frame, @Prop-OldPhoto still in her hand, watching.

NEGATIVE — strictly avoid: no police officer's face is ever visible, in any framing, at any moment. No wounds, no injury detail, no gore of any kind. The stain on the sheet is OLD and DRY — rust-brown, matte, absorbed into the fabric, with nothing wet, glossy, red, fresh, pooling or spreading anywhere in frame. She has been dead more than a day and the image must read that way. No weapon in frame. @Daughter never touches, bumps, acknowledges or looks at @Mother standing. @Mother does NOT glow, is NOT translucent, does NOT blur, does NOT scatter and casts a normal shadow — she is photographed as an ordinary solid person and nothing in the image marks her as a ghost. No double exposure, no lens flare, no light rays, no particles, no floating dust motes treated as magic. No sound at all after the door opens. No music, no sting, no riser. No camera shake, no whip pan, no zoom.

Grounded real-camera look, locked or on a slow steady move, no handheld shake. Weak warm ceiling light plus hard cold light spilling in from the open doorway. Muted and desaturated — except the dried stain on the sheet and the faded warm colour of @Prop-OldPhoto.

AUDIO-SFX
Three hard impacts on the door, a muffled shout, wood splitting and the lock giving — close, real, loud. Then, from the exact frame the door opens, ABSOLUTE SILENCE for the remaining seventeen seconds: no footsteps, no crying, no cloth, no room tone, no breath, no music, no sting. The silence is the effect and it must be complete.
```

## Scene 10-C — JUMP CUT (20s) — police burst in, five cuts

```
VISUAL
Five cuts across 20 seconds. Interior of room 214 — it begins as @Room-Clean and ends as @Room-Wreck. No two cuts share a camera position.

Cut 1 (0–3s): Behind @Mother, tight on the back of her head and shoulders, her face not in frame — we look past her at @Prop-OldPhoto held low in her hands. Beyond her @Room-Clean is ordinary, @Prop-Handbag closed on the nightstand beside @Prop-Lamp. Three hard impacts on @Room-DoorOut. Real time, real sound.
Cut 2 (3–7s): @Room-DoorOut bursting inward, shot from inside the room. From this frame on everything is SLOW MOTION and silent.
Cut 3 (7–11s): Two police officers moving through the doorway, faces never visible — cropped, backlit or shot from behind. Dust turning in the hard light from outside.
Cut 4 (11–16s): @Daughter running forward in tears, arms opening — then past @Mother entirely, dropping onto the bed and taking hold of a body. The room in this cut is @Room-Wreck: bedding torn, armchair over, @Prop-Glass shattered across the carpet, suitcase spilling. The white sheet under the body carries a wide dark rust-brown stain, dried into the weave and stiff at its edges.
Cut 5 (16–20s): Wide, held. @Daughter holding the body. @Mother standing in the same frame, untouched, unlooked-at, @Prop-OldPhoto still in her hand.

NEGATIVE — strictly avoid: no police face visible in any cut. No wounds, no injury detail, no gore of any kind. The stain on the sheet is OLD and DRY — rust-brown, matte, absorbed into the fabric, with nothing wet, glossy, red, fresh, pooling or spreading anywhere in frame. She has been dead more than a day and the image must read that way. No weapon. @Daughter never touches or acknowledges @Mother standing. @Mother does NOT glow, is NOT translucent and does NOT scatter — she is an ordinary solid person in the image. No double exposure, no light rays, no particles. No sound after Cut 2 begins. No music, no sting, no riser.

Grounded real-camera look, natural weight, no whip pans, no zoom. Weak warm ceiling light plus hard cold corridor light. Muted and desaturated except the blood and the photograph.

AUDIO-SFX
Impacts on the door, a muffled shout, the lock giving — real and close over Cut 1 and the start of Cut 2. Then absolute silence for Cuts 3, 4 and 5: no footsteps, no crying, no room tone, no breath. Cuts land inside the silence. No music, no sting, no dialogue.
```

## Scene 10-D — LONG TAKE (20s) — the daughter passes THROUGH her, glowing

Same beat as 10-B, opposite treatment. Here the film says it out loud: @Mother
is visibly not solid, and the daughter runs straight through her. **This variant
deliberately breaks the no-glow rule that every other shot in the film obeys.**

**Diagnostic edit, 2026-08-14 (CTO):** this block failed 3/3 with an
unattributed generic Higgsfield error while sitting at exactly 10 distinct
elements — the only queue item at the hard cap, and the only block tonight
using the untested `@Mother-Soul` plate. Dropped `@Prop-Handbag` (background
dressing only in this shot, described in plain words below) to bring it to
**9 elements** as a test of the count-ceiling theory, per the CEO's direct
go-ahead. If this succeeds, the drop stays. If it still fails identically,
the cause is elsewhere (most likely the `@Mother-Soul` plate itself) and this
note should be updated rather than removed.

```
VISUAL
Single continuous take, 20 seconds. Interior of room 214 — it begins as @Room-Clean and ends as @Room-Wreck. @Prop-Lamp stands unlit on the nightstand; one weak warm ceiling bulb is the only light until the door opens.

0–3s: Behind @Mother, tight on the back of her head and shoulders, her face not in frame — we look past her at @Prop-OldPhoto held low in her hands. Beyond her @Room-Clean is ordinary, a closed handbag sits undisturbed on the nightstand. Three hard impacts land on @Room-DoorOut and a muffled shout comes through. Real time, real sound.

3–5s: @Room-DoorOut bursts inward. At the exact frame it opens the image drops into SLOW MOTION and all sound falls away to nothing.

5–9s: Two police officers move through the doorway first, faces NEVER visible — cropped, backlit, or shot from behind. As the hard light from outside crosses @Mother she becomes @Mother-Soul: faintly translucent, a soft cool luminance under her skin and clothes, with @Room-Wreck dimly readable straight through her body.

9–14s: @Daughter enters behind them in tears, a young woman now, and runs forward with her arms opening to take hold of her mother.

14–17s: @Daughter runs straight THROUGH @Mother-Soul. At the moment of contact @Mother-Soul comes apart into slow drifting motes of pale light and fine grey dust, which hang in the air and turn in the light from the doorway. @Daughter does not stop, does not feel it, and drops onto the bed beyond — where the room is now @Room-Wreck: bedding torn, armchair over, @Prop-Glass shattered across the carpet, suitcase spilling open. @Mother's body lies on the bed, the white sheet beneath it carrying a wide dark rust-brown stain, long dried into the weave and stiff at its edges. The daughter takes hold of the body and holds it.

17–20s: Hold, still slow, still silent. @Daughter holding the body. The drifting motes settle slowly through the frame around them and go out one by one. @Prop-OldPhoto lies on the carpet where @Mother-Soul was standing.

NEGATIVE — strictly avoid: no police officer's face is ever visible. No wounds, no injury detail, no gore of any kind. The stain on the sheet is OLD and DRY — rust-brown, matte, absorbed into the fabric, with nothing wet, glossy, red, fresh, pooling or spreading anywhere in frame. She has been dead more than a day and the image must read that way. No weapon. The daughter never stops, never reacts and never acknowledges @Mother — she does not see her and does not feel the contact. The glow stays FAINT and cool: no bright halo, no beam, no god rays, no lens flare, no sparkle, no glitter, no fire, no embers, no CG energy effect, no colour shift into blue or green. @Mother's face stays recognisable as the woman in the photograph right up to the moment she comes apart. No music, no sting, no riser, no sound of any kind after the door opens. No camera shake, no whip pan, no zoom.

Grounded real-camera look, locked or slow steady move. Weak warm ceiling light plus hard cold light from the open doorway. Muted and desaturated — except the dried stain, the faded warm colour of @Prop-OldPhoto, and the pale motes.

AUDIO-SFX
Three hard impacts on the door, a muffled shout, wood splitting and the lock giving — close, real, loud. Then, from the exact frame the door opens, ABSOLUTE SILENCE for the remaining seventeen seconds. No footsteps, no crying, no room tone, no breath, and specifically NO sound for the moment she comes apart — no whoosh, no chime, no shimmer. The silence is the effect and it must be complete.
```

## Scene 10-D — LONG TAKE (20s, Seedance 2.5) — all 10 elements tagged

**Added 2026-08-14 (CEO).** Identical to the 9-element block above except
`@Prop-Handbag` is tagged again instead of being described in plain words.
The CEO is running this himself on **Seedance 2.5**, which accepts up to 50
reference images — the 9-element ceiling is a Seedance 2.0 limit only, so
nothing has to be dropped here.

**Two real differences from the 2.0 version, both worth watching:**

- **The timing finally matches.** This block is written to 20 seconds, but
  every 2.0 attempt ran at 15s, compressing all five beats. On 2.5 at 20s
  the timecodes above are the timecodes on screen for the first time.
- **720p, not 1080p.** Every other Scene 10 clip in Drive's `S10-1080P` is
  1080p. The "softer 720p reads as old memory" argument covers the Scene 12
  flashback act; it does **not** cover Scene 10, which is present-tense. If
  this take is kept, the resolution mismatch is the editor's problem to
  solve, so judge the result on that too, not only on the performance.

**Content-filter note.** Nothing in this block breaks a festival rule
(Section 5 bans violence against *real* individuals; fictional characters are
fine) or the platform's ToU (no direct violence clause). The residual risk is
the platform's own filter, which has rejected this project three times on
wording alone. The VISUAL section is clean — no strike/fight/kill language,
and the stain is described as old and dry. The exposure is in NEGATIVE, which
contains `gore`, `weapon`, `red`, `pooling` and `spreading` as *prohibitions*
— filters routinely scan raw text without parsing the "no". If it gets
rejected, soften in this order and re-run: `no gore of any kind` →
`nothing graphic`; delete the `No weapon.` sentence entirely (VISUAL never
mentions a weapon, so it defends against nothing); `red, fresh, pooling or
spreading` → `wet or glossy`.

```
VISUAL
Single continuous take, 20 seconds. Interior of room 214 — it begins as @Room-Clean and ends as @Room-Wreck. @Prop-Lamp stands unlit on the nightstand; one weak warm ceiling bulb is the only light until the door opens.

0–3s: Behind @Mother, tight on the back of her head and shoulders, her face not in frame — we look past her at @Prop-OldPhoto held low in her hands. Beyond her @Room-Clean is ordinary, @Prop-Handbag closed on the nightstand. Three hard impacts land on @Room-DoorOut and a muffled shout comes through. Real time, real sound.

3–5s: @Room-DoorOut bursts inward. At the exact frame it opens the image drops into SLOW MOTION and all sound falls away to nothing.

5–9s: Two police officers move through the doorway first, faces NEVER visible — cropped, backlit, or shot from behind. As the hard light from outside crosses @Mother she becomes @Mother-Soul: faintly translucent, a soft cool luminance under her skin and clothes, with @Room-Wreck dimly readable straight through her body.

9–14s: @Daughter enters behind them in tears, a young woman now, and runs forward with her arms opening to take hold of her mother.

14–17s: @Daughter runs straight THROUGH @Mother-Soul. At the moment of contact @Mother-Soul comes apart into slow drifting motes of pale light and fine grey dust, which hang in the air and turn in the light from the doorway. @Daughter does not stop, does not feel it, and drops onto the bed beyond — where the room is now @Room-Wreck: bedding torn, armchair over, @Prop-Glass shattered across the carpet, suitcase spilling open. @Mother's body lies on the bed, the white sheet beneath it carrying a wide dark rust-brown stain, long dried into the weave and stiff at its edges. The daughter takes hold of the body and holds it.

17–20s: Hold, still slow, still silent. @Daughter holding the body. The drifting motes settle slowly through the frame around them and go out one by one. @Prop-OldPhoto lies on the carpet where @Mother-Soul was standing.

NEGATIVE — strictly avoid: no police officer's face is ever visible. No wounds, no injury detail, no gore of any kind. The stain on the sheet is OLD and DRY — rust-brown, matte, absorbed into the fabric, with nothing wet, glossy, red, fresh, pooling or spreading anywhere in frame. She has been dead more than a day and the image must read that way. No weapon. The daughter never stops, never reacts and never acknowledges @Mother — she does not see her and does not feel the contact. The glow stays FAINT and cool: no bright halo, no beam, no god rays, no lens flare, no sparkle, no glitter, no fire, no embers, no CG energy effect, no colour shift into blue or green. @Mother's face stays recognisable as the woman in the photograph right up to the moment she comes apart. No music, no sting, no riser, no sound of any kind after the door opens. No camera shake, no whip pan, no zoom.

Grounded real-camera look, locked or slow steady move. Weak warm ceiling light plus hard cold light from the open doorway. Muted and desaturated — except the dried stain, the faded warm colour of @Prop-OldPhoto, and the pale motes.

AUDIO-SFX
Three hard impacts on the door, a muffled shout, wood splitting and the lock giving — close, real, loud. Then, from the exact frame the door opens, ABSOLUTE SILENCE for the remaining seventeen seconds. No footsteps, no crying, no room tone, no breath, and specifically NO sound for the moment she comes apart — no whoosh, no chime, no shimmer. The silence is the effect and it must be complete.
```

## Scene 11A — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Wreck — room 214 after. @Mother stands in the middle of @Room-Wreck facing @Room-DoorOut, her back three-quarters to camera; her face is never seen clearly. @Daughter is a woman in her twenties.

0–6s: @Room-Wreck is still. @Mother stands motionless facing @Room-DoorOut, closed. Nothing moves.
6–12s: @Room-DoorOut bursts inward. A hard white torch beam sweeps in from outside and rakes across @Room-Wreck, throwing it into sharp relief — the tangled bed, the overturned chair, @Prop-Glass shattered across the carpet. Police radio chatter crackles from the corridor outside. No officer's face is ever seen: only the beam, moving shadows across the frame of @Room-DoorOut, and a shoulder passing at the edge of frame.
12–20s: @Daughter comes through @Room-DoorOut ahead of them and stops dead. She scans @Room-Wreck, and her eyes pass across @Mother without stopping — as though the space @Mother occupies were empty. Hold there: @Mother facing her daughter, @Daughter looking straight through her.

NEGATIVE — strictly avoid: do not show any police officer's face — torch beam, shadow, radio and a shoulder at frame edge only. Do not show a body in this shot. No blood. @Mother's face is never clearly readable. @Daughter must NEVER make eye contact with @Mother and must never react to her. @Mother is completely solid and ordinary here — no transparency, no glow, no smoke, nothing supernatural yet.

Grounded real-camera look, no lens flare, no haze, no whip pans. Hard white torch light cutting through a weak warm room light. Muted and desaturated.

AUDIO-SFX
Dead room tone. Then a door striking the wall hard, boots on concrete, a police radio squawking with clipped unintelligible traffic. Fast breathing from @Daughter. Under it all, nothing at all from @Mother — no footsteps, no breath, no cloth. Silence where her sounds should be. No music.
```

## Scene 11A — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Wreck — room 214 after. @Mother's face is never seen clearly. @Daughter is a woman in her twenties.

Cut 1 (0–4s): @Mother from behind, motionless, facing @Room-DoorOut, closed, the wreckage of @Room-Wreck around her.
Cut 2 (4–8s): @Room-DoorOut bursting inward, a hard white torch beam raking across @Prop-Glass shattered on the carpet.
Cut 3 (8–12s): Shadows crossing the frame of @Room-DoorOut, a shoulder passing at frame edge, a police radio unit on a belt. No faces.
Cut 4 (12–16s): @Daughter stopping dead just inside @Room-DoorOut, scanning @Room-Wreck.
Cut 5 (16–20s): Over @Mother's shoulder toward @Daughter — @Daughter's eyes travel across the space @Mother occupies and keep going, with no flicker of recognition. Hold.

NEGATIVE — strictly avoid: no police officer's face at any point. No body in this shot. No blood. @Mother's face is never clearly readable. @Daughter must NEVER make eye contact with @Mother or react to her presence. @Mother is completely solid here — no transparency, no glow, no smoke.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Hard white torch light against weak warm room light. Muted and desaturated.

AUDIO-SFX
Dead room tone. A door striking a wall. Boots on concrete. A police radio squawking, words never intelligible. @Daughter's fast breathing. Nothing at all from @Mother — no footstep, no breath, no cloth. Cuts land on the door and on the torch beam. No music.
```

## Scene 11B — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Camera locked off and completely still for the whole shot. Interior of @Room-Wreck — room 214 after. @Mother stands centre frame, solid, seen from behind and slightly to the side; her face is never clearly readable. @Daughter is a woman in her twenties.

0–6s: @Daughter's face changes — she has seen something past @Mother. She starts forward at a run, straight toward @Mother.
6–11s: @Mother slowly opens her arms to receive her, calm, her expression unreadable. She does not brace or flinch. She is waiting to be held.
11–15s: @Daughter runs THROUGH her without slowing and without touching her, continuing past camera. At the instant of contact @Mother's solid body gives way to @Mother-Soul in the same pose, arms open: translucent, like drifting smoke and fine dust hanging in the air, and @Room-Wreck behind her — the overturned chair, @Prop-Glass shattered across the carpet — is clearly visible straight through her body.
15–20s: @Mother-Soul stays exactly where @Mother was standing, arms still open, drifting very slightly like smoke in still air. She does not turn. Hold on her, transparent, alone in frame.

NEGATIVE — strictly avoid: @Daughter must NEVER slow down, flinch, look at @Mother, or react to her in any way — she passes through as though the space were empty. There must be NO collision, no impact, no push. No glow, no light rays, no lens flare, no particles that sparkle, no digital shimmer, no ghost double, no motion blur trails. The camera never moves. No body is shown in this shot. @Mother and @Mother-Soul are never both in frame as two separate figures — one becomes the other in place.

DELIBERATE: @Mother-Soul is played DRY in this shot — smoke and fine dust, physical and unlit, never luminous. This is the opposite of the treatment in 10-D, and the difference is intentional; do not reconcile them.

Grounded real-camera look, locked off, no lens flare, no haze. Hard white torch light crossing a weak warm room light. Muted and desaturated.

AUDIO-SFX
Running footsteps on carpet, closing fast, then continuing past and away without any impact sound at all — the absence where a collision should be is the point. @Daughter's breathing, ragged, receding. Police radio far off. From @Mother: nothing. No whoosh, no chime, no sting, no riser, no music at the moment she becomes transparent — silence carries it.
```

## Scene 11B — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Wreck — room 214 after. @Mother's face is never clearly readable. @Daughter is a woman in her twenties.

Cut 1 (0–4s): Tight on @Daughter's face as it changes — she has seen something past @Mother — and she starts to run.
Cut 2 (4–8s): From behind @Mother, her arms slowly opening to receive her daughter, calm and unhurried.
Cut 3 (8–12s): Locked wide. @Daughter runs THROUGH @Mother without slowing and continues past camera. At the moment of contact @Mother gives way to @Mother-Soul in the same pose — smoke and fine dust — and the overturned chair and @Prop-Glass shattered on the carpet behind her show clearly through the body.
Cut 4 (12–16s): Close on @Mother-Soul's translucent arm and shoulder, still open, @Room-Wreck legible straight through them.
Cut 5 (16–20s): Wide again. @Mother-Soul transparent, arms still open, alone in frame, drifting very slightly. Hold.

NEGATIVE — strictly avoid: @Daughter must NEVER slow, flinch, look at @Mother or react to her. No collision, no impact, no push. No glow, no light rays, no lens flare, no sparkling particles, no digital shimmer, no ghost double, no motion trails. No body shown in this shot. @Mother and @Mother-Soul are never both in frame as two figures — one becomes the other in place.

DELIBERATE: @Mother-Soul is played DRY here — smoke and fine dust, unlit, never luminous. The opposite of 10-D on purpose; do not reconcile them.

Grounded real-camera look, no whip pans, no lens flare, no haze. Hard white torch light against weak warm room light. Muted and desaturated.

AUDIO-SFX
Running footsteps closing fast, then continuing past and away with no impact sound whatsoever. @Daughter's ragged breathing receding. Police radio far off. From @Mother, nothing at all. No whoosh, no chime, no sting, no riser, no music. Cuts land on the run and on the pass-through.
```

## Scene 11C — LONG TAKE (20s)

```
VISUAL
Single continuous take, 20 seconds, no cuts. Interior of @Room-Wreck — room 214 after. A slow, steady mechanical pan, one direction only, never reversing.

0–5s: Start on @Mother-Soul, arms still open, @Room-Wreck visible straight through her. She is motionless.
5–11s: The camera begins a slow pan away from her, left to right across @Room-Wreck, and she drifts out of frame. It travels over the evidence of what happened here: the overturned armchair, @Prop-Glass shattered across the carpet, the suitcase open and spilling clothes, @Prop-Lamp knocked askew, a smear of disturbed bedding.
11–17s: The pan continues and reaches the bed. @Mother lies on it, still, fully clothed in the same housekeeping uniform, turned away from camera so her face is not visible. @Daughter is collapsed over her, holding her, shoulders shaking.
17–20s: The pan stops there and holds. On the floor beside the bed, @Prop-OldPhoto lies face-up where it fell.

NEGATIVE — strictly avoid: no blood anywhere, no wound, no injury, no violence on screen. @Mother on the bed is turned away and her face is never visible. Do not show a police officer's face. Nothing glows — @Mother-Soul is dry smoke and dust, unlit. No double exposure, no second translucent figure once @Mother-Soul has left frame — after the pan passes her she is simply gone from the shot. @Mother-Soul and @Mother's body are never in frame together. The camera pans once, steadily, in one direction, and never reverses or returns to her.

Grounded real-camera look, slow mechanical pan, no lens flare, no haze, no handheld shake. Hard white torch light crossing a weak warm room light. Muted and desaturated, except the old photograph on the floor, which keeps the faded warm colour of an old print.

AUDIO-SFX
Room tone. The pan carries no sound of its own. @Daughter crying, close and unguarded, growing as the camera reaches the bed. A police radio in the doorway, clipped, unintelligible. No sound at all from @Mother — the silence she leaves behind is the loudest thing in the shot. No music.
```

## Scene 11C — JUMP CUT (20s)

```
VISUAL
Five cuts across 20 seconds. Interior of @Room-Wreck — room 214 after.

Cut 1 (0–4s): @Mother-Soul, arms still open, @Room-Wreck visible straight through her. Motionless.
Cut 2 (4–8s): The overturned armchair and @Prop-Glass shattered across the carpet.
Cut 3 (8–12s): The suitcase open and spilling clothes, @Prop-Lamp knocked askew.
Cut 4 (12–17s): The bed. @Mother lies on it, still, in a housekeeping uniform, turned away so her face is not visible. @Daughter collapsed over her, holding her, shoulders shaking.
Cut 5 (17–20s): Low on the carpet beside the bed — @Prop-OldPhoto, face-up where it fell. Hold.

NEGATIVE — strictly avoid: no blood, no wound, no injury, no violence on screen. @Mother on the bed is turned away and her face is never visible. No police officer's face. Nothing glows — @Mother-Soul is dry smoke and dust, unlit. No double exposure, no translucent figure in any cut after the first, and @Mother-Soul never shares a frame with @Mother's body.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare, no haze. Hard white torch light against weak warm room light. Muted and desaturated, except @Prop-OldPhoto, which keeps the faded warm colour of an old print.

AUDIO-SFX
Room tone. @Daughter crying, close and unguarded, growing across the cuts. A police radio in the doorway, clipped and unintelligible. No sound at all from @Mother. Cuts land in the silences, never on the crying. No music.
```

---

# SCENE 11D and SCENE 12 — the flashback act (added 2026-08-14, CEO)

**11D is the bridge.** It picks up the instant 11C ends and pushes into
@Mother's eye until the frame goes black; that black resolves directly into
12-A. Nothing sits between them — no title card, no fade, the push itself is
the transition. **Nested inside 12 is Scene 13**, already written above,
triggered when she sees her own house lit up from the bus. Order on screen:
11D → 12-A → 12-B → [13, unedited] → 12-C1 → 12-C2 → 12-D → 12-E.

**11D deliberately breaks the never-see-her-face rule that every Scene 9-11
block has followed until now.** It has to — the device only works if the
audience finally sees her eyes. Treat this as the one and only exception,
same as 10-D's deliberate glow.

**12's colour is a third, distinct grade — do not confuse it with 13's.**
The muted present (1-11) stays muted. 13 is warm and golden, the happiest
memory in the film. 12 sits between them: real streetlight sodium-orange at
night, harder and colder than 13, more saturated than the present — this is
true memory, not delusion, but it is a frightening night, not a happy one.

**12-E is the most sensitive shot in the film — write and generate it with
care.** Scene 4's original cut was rejected twice for "conflict language"
reading as literal domestic-violence description. Every beat of struggle in
12-D and 12-E stays off-screen by design: shadows, sound, objects breaking,
never a shown blow. This is not a softening choice, it is the same
negative-space horror grammar the whole film already uses for its violence.

## Scene 11D — LONG TAKE (15s) — push into her eye

No jump-cut variant — this is a single continuous camera move by nature; a
cut would break the transition it exists to perform.

**Corrected 2026-08-14 (CEO): the eye is @Mother-Soul's, not @Mother's** —
this is the spirit form, dry and unlit exactly as established in 11B/11C
(never luminous — that treatment belongs only to 10-D). Two police officers
are now visible in the background, faces never shown, per the house rule
every other scene already follows.

```
VISUAL
Single continuous take. Interior of @Room-Wreck, continuing directly from the end of 11C — @Daughter still holding the body. In the background near the doorway, two police officers move through the room, torch beams sweeping, radios crackling — their faces are never seen, only silhouettes and beams at the edge of frame.

0–4s: The camera moves slowly around from the angle 11C held (her face turned away) to find @Mother-Soul's face directly for the first time in the film — her translucent spirit form, dry and unlit. Her eyes are open, glassy, unseeing. No visible mark or injury anywhere on her face.

4–10s: A slow, steady push toward one eye. Nothing else moves. The pupil grows to fill more and more of the frame.

10–15s: The pupil fills the entire frame and goes to pure black. Hold on the black for the last beat — this black is the cut point into Scene 12-A.

NEGATIVE — strictly avoid: no wound, no mark, no discolouration anywhere on her face. No CGI eye effect, no twitch, no flash, no reflection of anything in the eye. No officer's face ever visible — silhouette, beam and shoulder only, and both officers stay peripheral, never crossing into the main frame. The push is slow and continuous — no speed ramp, no whip, no cut within the take. No music, no sting at the moment it goes black.

Grounded real-camera look, no lens flare, no haze. Hard white torch light (from the two officers' beams) and weak warm room light, both fading to nothing as the black takes over. Muted and desaturated until the frame is pure black.

AUDIO-SFX
@Daughter's crying and the police radio continue from 11C, both fading steadily as the push continues. By the moment the frame goes black, there is total silence — that silence carries straight into 12-A's first sound. No music, no sting, no whoosh.
```

## Scene 11D-B — LONG TAKE (15s) — just her, close and quiet

**Added 2026-08-14 (CEO).** A second, intimate treatment of the same
transition — no police, no wider room, just @Mother-Soul and @Daughter.
Same cut point into 12-A; the CEO/editor chooses between this and 11D.

```
VISUAL
Single continuous take. Interior of @Room-Wreck, continuing directly from the end of 11C. @Daughter holds @Mother-Soul, face buried against her, shoulders shaking. No police anywhere in frame — this version stays entirely on the two of them.

0–4s: The camera finds @Mother-Soul's face directly — her translucent spirit form, dry and unlit. Her hands are empty; @Prop-OldPhoto already fell from them and lies on the carpet, out of frame. Her eyes are open, glassy, unseeing. No visible mark or injury anywhere on her face.

4–10s: A slow, steady push toward one eye. Nothing else moves. The pupil grows to fill more and more of the frame.

10–15s: The pupil fills the entire frame and goes to pure black. Hold on the black for the last beat — this black is the cut point into Scene 12-A.

NEGATIVE — strictly avoid: no wound, no mark, no discolouration anywhere on her face. No CGI eye effect, no twitch, no flash, no reflection of anything in the eye. No police, no torch beam, no radio chatter — this shot is quieter than 11D on purpose. Nothing in her hands. The push is slow and continuous — no speed ramp, no whip, no cut within the take. No music, no sting at the moment it goes black.

Grounded real-camera look, no lens flare, no haze. Weak warm room light only, fading to nothing as the black takes over. Muted and desaturated until the frame is pure black.

AUDIO-SFX
@Daughter's crying, close and unguarded, fading steadily as the push continues — no distant police radio in this version. By the moment the frame goes black, there is total silence — that silence carries straight into 12-A's first sound. No music, no sting, no whoosh.
```

## Scene 12-A — LONG TAKE (15s) — the bus stop

```
VISUAL
Single continuous take. Night, @Stop-Work — the bus stop outside her real workplace. @Father stands beside a black sedan parked at the curb. The bus has not arrived yet.

0–5s: @Mother walks up from her shift, sees him, stops short. He steps toward her, hand out — asking for money.
5–9s: She refuses. He steps in closer, his voice rising, and grabs her arm, not letting go.
9–12s: The bus pulls in right behind them, brakes hissing, doors opening.
12–15s: She pulls free and steps straight onto the bus. Doors close behind her.

NEGATIVE — strictly avoid: no strike, no punch, no shove, no fall. The arm-grab is firm, held, not a blow. No visible mark on her arm. No text or logo readable on the sedan or anywhere in frame. No printed logos or brand text on either character's clothing.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare. Hard sodium-orange streetlight at night — harder and more saturated than the muted present, colder than Scene 13's gold. 

AUDIO-SFX
Distant traffic, a car engine idling. His voice, low and demanding, hers clipped and refusing. Bus air brakes, door hydraulics. No music.
```

## Scenes 12-FB1 and 12-FB2 replace 12-B through 12-E — CEO pivot, 2026-08-14

**Spec change for this act only: Seedance 2.5 / 720p / 20s / Unlimited**, not
the film's usual 2.0 / 1080p / 15s. Seedance 2.0's Unlimited allotment ran out
mid-session (confirmed via a real paid-upsell modal, not a bug); 2.5's is
separate and untouched. The CEO's own reframe: softer 720p reads as
intentional "old memory" texture rather than a technical downgrade, and
Seedance 2.5 accepts up to 50 reference images, far past the 9-cap that
governs 2.0 — no need to economize elements on these two blocks.

**These two 20-second jump-cut blocks replace all of 12-B, 12-C1, 12-C2,
12-D and 12-E** (no separate Scene 13 prompt existed yet — its story content
is folded in here). Every beat from the original 5-block breakdown is
present in one of the two blocks below, per the CEO's explicit requirement —
none dropped for time. Cut lengths are short (1.5-4s) matching real
fast-cutting technique for flashback/memory sequences, researched and
confirmed against real film-craft sources earlier this session.

## Scene 12-FB1 — JUMP CUT (20s, Seedance 2.5) — the confrontation and the memory

```
VISUAL
Eleven cuts across 20 seconds. Night.

Cut 1 (0–1.5s): @Mother leaves work, carrying @Prop-Handbag, tired. Exterior @Stop-Work.
Cut 2 (1.5–3s): @Father stands beside a black sedan at the curb, hand out, asking for money.
Cut 3 (3–4.5s): She refuses. He steps in close and grabs her arm, holding on.
Cut 4 (4.5–6s): The bus pulls in right behind them; she pulls free and boards, @Prop-Handbag still in hand.
Cut 5 (6–7.5s): Interior @Bus-Interior. Through the rear window, the black sedan follows at a steady distance in traffic.
Cut 6 (7.5–9s): Through the side window she sees @House-Night, every window lit warm, porch light on.
Cut 7 (9–11s): Flash of memory — warm golden afternoon, @House-Day. @Father, healthy, spins @Daughter as a small child in the front yard; she laughs.
Cut 8 (11–13s): @Mother stands on the porch watching them, smiling, open-hearted. The three of them plant a tree together, dirt on small hands.
Cut 9 (13–15s): The three of them eat dinner on the porch steps, plates on their laps, laughing together.
Cut 10 (15–17s): Close-up: @Mother's and @Father's hands joined, wearing @Prop-Ring — the same ring seen on the nightstand in Scene 9.
Cut 11 (17–20s): Cut back hard to the dark bus interior. Her hand hovers near @Prop-BusCord, then drops — she does not pull it. The bus continues past her stop.

NEGATIVE — strictly avoid: no strike, no punch, no shove, no fall in cuts 2-3 — the arm-grab is firm and held, not a blow, no visible mark on her arm. No printed logos or brand text anywhere. The memory cuts (7-10) read distinctly warmer and more saturated than the bus/present cuts — never blend the two grades. @Father in the memory is healthy, not gaunt or unwell. @Prop-BusCord is never actually pulled.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare. Present-tense cuts: hard sodium-orange streetlight and cold bus interior light. Memory cuts: warm golden-hour light, slightly softer focus, matching an old photograph's palette. Cuts land hard on the light change between present and memory — no dissolve, no cross-fade.

AUDIO-SFX
Distant traffic, engine idle, his voice low and demanding, her clipped refusal. Bus air brakes, door hydraulics, engine hum. The memory cuts carry no dialogue, only muffled, distant, warm ambient sound — wind, faint laughter, no clear words, like a memory heard through glass. Cut back to the bus: near-silence, only the faint chain-tick of @Prop-BusCord swinging. No music anywhere in this block.
```

## Scene 12-FB2 — JUMP CUT (20s, Seedance 2.5) — the motel room

```
VISUAL
Seven cuts across 20 seconds. Night, continuing directly from 12-FB1.

Cut 1 (0–3s): @Mother runs across the street toward @Motel-Front, glancing back once. The black sedan pulls up behind her; @Father gets out but stays back near the entrance.
Cut 2 (3–5s): Interior @Motel-Lobby. She's breathless at the front counter, talking with the hotel clerk (unremarkable, no plate, invented by the model). Through the glass behind her, @Father is visible outside, not entering.
Cut 3 (5–8s): @Room-DoorOut, then @Room-Clean. She unlocks the door with @Prop-RoomKey, steps in, starts to push it shut — his hand catches it from outside and forces it open. He steps in.
Cut 4 (8–10s): A sharp argument, voices overlapping, words not intelligible. Shadows cross the wall, fast and wrong.
Cut 5 (10–14s): @Prop-Lamp knocked from the nightstand. @Prop-Glass tips and shatters. Bed sheets pull loose and tangle. A chair goes over. The struggle itself stays off-camera the entire time — the camera holds on the room, never on contact between them.
Cut 6 (14–17s): The room holds still. It is now @Room-Wreck. Silence.
Cut 7 (17–20s): @Father steps back into frame, breathing hard, and leaves. At the door he hangs @Prop-DNDTag on the outside handle, then walks away. A car door, an engine, driving off.

NEGATIVE — strictly avoid: no readable hotel name or logo anywhere in frame. @Father stays outside the glass in Cut 2, never crosses the threshold. In Cut 3, contact is limited to his hand catching and forcing the door — no shove, no grab beyond the door itself. Cuts 4-5: absolutely no physical blow, no visible wound, no blood shown anywhere. The violence is entirely implied through the room, shadow and sound — never shown directly. No face-on shot of contact between the two of them at any point.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare. Hard sodium-orange streetlight outside, warm interior lobby/room light within. Muted and desaturated, consistent with the film's present-day grade — this block is not a memory, it stays grounded.

AUDIO-SFX
Footsteps running on pavement, breathing hard, a car door closing unhurried. The clerk's voice, calm and routine, not fully intelligible, a key card printer. The key in the lock, the door forced open, two raised voices overlapping. The lamp hitting the floor, glass shattering, furniture scraping and falling — then dead silence. His slower breathing, footsteps to the door, the DND tag swinging once, a car door, an engine driving away into distance. No music, no score, anywhere in this block.
```

## Scene 12-FB — JUMP CUT (30s, Seedance 2.5) — everything in one

**Revised 2026-08-14 (CEO).** Extended from 20s to 30s for more room per
cut and more narrative detail. **Alternate to FB1+FB2, not additional
footage** — the CEO/editor picks one version of this act, not both. Two
deliberate departures from every other scene's negative-space rule, both
requested directly:

**The memory cuts (7-10) are written as a montage, not discrete shots** —
quick, slightly overlapping impressions, like photographs coming alive one
after another, rather than fully separate scenes.

**Cut 17 now shows the moment of contact, not just its aftermath.** Every
other violence beat in this film cuts away entirely; this one shows his arm
moving and her reaction, then the camera immediately breaks to another
angle at the instant of contact — an object, a shadow, a different part of
the room — rather than holding on a frontal blow. The broken objects are
now caused directly by that motion (his swing catching the nightstand, her
body driven into it), not falling on their own. **This raises content-flag
risk above every other scene tonight** — Scene 4's original cut was
rejected twice for language reading as domestic violence, and this is
closer to that line than anything else in the film. If it gets rejected,
work down toward the fully-implied version (the original 20s cut, still
above this block in git history) rather than escalating language further.

**Added 2026-08-14 (CEO): the handbag is now a through-line, not a static
prop.** She carries it protectively from the moment she leaves work through
the bus, the run to the motel, the lobby, and the door (cuts 1, 4-6, 11-14).
Cut 16 makes that protectiveness explicit — he grabs for the bag itself
before the violence starts, and she resists — reframing the confrontation:
part of what he wants from her tonight is the money in that bag, not just
an argument. Cut 19, after the killing, pays that off — he takes the cash
out of it. **`@Motel-Walkway` is tagged in Cut 20** — previously forbidden
(copyright-flagged reference image, blocked the render outright in Scenes
4/6/7/8/9A) but the CEO replaced the reference image 2026-08-14 and
confirmed it renders now; unblocked in `scripts/audit_prompts.py` the same
day.

```
VISUAL
Twenty cuts across 30 seconds. Night.

Cut 1 (0.0–1.7s): @Mother steps out of @Stop-Work at the end of a long shift, @Prop-Handbag heavy on her shoulder, her uniform creased, exhaustion in how she carries herself.

Cut 2 (1.7–3.2s): @Father is already waiting beside a black sedan at the curb. He steps toward her, hand out, voice low — asking for money again.

Cut 3 (3.2–4.7s): She shakes her head, refuses. His hand closes around her arm, firm, not letting go — she tries to pull back and can't.

Cut 4 (4.7–6.0s): The bus brakes hiss right behind them. She wrenches free and steps up into it, @Prop-Handbag pulled tight against her chest.

Cut 5 (6.0–7.3s): Interior @Bus-Interior, in motion. Through the rear window, the black sedan holds a steady distance in the traffic behind.

Cut 6 (7.3–8.6s): Through the side glass, @House-Night passes as it is right now, present-day — every window lit warm, the porch light on, seen from the moving bus, before anything else changes. Her face changes, softens.

Cut 7 (8.6–10.6s): The image shifts — same house, but memory now, not present: warm and slightly soft-focus, like an old photograph stirring — @House-Day, golden afternoon light. Both parents read visibly younger here than anywhere else in the film — this is years earlier. @Father wears a plain casual shirt, open-collared, sleeves rolled, clean, healthy, unworn, no gauntness in his face. He spins @Daughter as a small child in the front yard; her laugh carries.

Cut 8 (10.6–12.6s): The impression shifts, overlapping — @Mother on the porch, watching, an open, unguarded smile. She wears a simple everyday home dress, younger and lighter than her present-day self. The three of them kneeling together, planting a tree, dirt on small hands.

Cut 9 (12.6–14.6s): Another impression — the three of them on the porch steps at dusk, plates on their laps, eating together, laughing at something none of them will remember later. Same younger versions of @Mother and @Father, same casual home clothes as the cuts before this one.

Cut 10 (14.6–16.6s): Close and slow — @Mother's and @Father's hands finding each other, still in their casual home clothes, both younger, @Prop-Ring catching the light. The same ring that will still be sitting on the nightstand in Scene 9.

Cut 11 (14.2–15.4s): Hard cut back to the dark bus. Her hand rises toward @Prop-BusCord, hesitates, drops. She doesn't pull it. @Prop-Handbag sits clutched in her lap, both arms crossed over it. The bus carries her past her stop.

Cut 12 (15.4–16.6s): She runs across the empty street toward @Motel-Front, @Prop-Handbag held tight against her side with both hands, breath visible, glancing back once. The sedan pulls up behind her; @Father gets out but holds back, unhurried.

Cut 13 (16.6–17.6s): Interior @Motel-Lobby. She's breathless at the counter, @Prop-Handbag still gripped in both arms, talking fast and low to the hotel clerk — a woman in her fifties, greying hair pulled back in a low bun, reading glasses pushed up on her head, wearing a plain navy uniform vest over a white blouse, no name tag readable. This is a new character, invented by the model, no plate — she must not resemble @Mother, @Daughter or any other established character in the film. Through the glass behind @Mother, @Father stands outside, watching, not entering.

Cut 14 (17.6–18.6s): @Room-DoorOut, then @Room-Clean. Key in the lock, door open, @Prop-Handbag still slung across her body, she starts to swing the door shut — his hand catches the edge and forces it back. He's inside.

Cut 15 (18.6–19.4s): The argument breaks open, voices overlapping, words lost to the volume of it. Both of them moving now, not standing still.

Cut 16 (19.4–21.2s): His hand shoots out and closes on the strap of @Prop-Handbag. She grabs it back with both hands, refusing to let go — a short, ugly tug-of-war over the bag itself, both of them wrenched off balance, neither saying anything now, just breathing and pulling.

Cut 17 (21.2–23.7s): His arm rises — cut immediately to a different angle at the instant it lands: over his shoulder, or the wall, or her face taking the impact off-frame. In the same motion his arm or her stumbling body catches the nightstand — @Prop-Lamp and @Prop-Glass go with it, knocked off by the collision, not falling on their own. This cut alone carries a harsh, chaotic filter — heavy motion blur, desaturated toward grey, contrast pushed hard — the image itself is disorienting, deliberately harder to read clearly than any other cut in the piece.

Cut 18 (23.7–24.9s): The room holds still. It is now @Room-Wreck. Dead silence. @Prop-Handbag lies open on the floor near her, spilled slightly where it fell in the struggle.

Cut 19 (24.9–26.7s): @Father kneels beside @Prop-Handbag, opens it the rest of the way, and pulls the folded cash out — the same money she refused him at the start. He counts it once, cold and quick, and pockets it. No plain readable currency detail, no dialogue.

Cut 20 (26.7–30.0s): @Father steps back, breathing hard, straightens his collar. At the door he hangs @Prop-DNDTag on the outside handle, then walks out along @Motel-Walkway — open-air, bare concrete, a metal rail, one flickering light overhead — to the sedan, and drives off into the dark.

NEGATIVE — strictly avoid: cuts 2-3 stay at a grabbed arm, not a blow — no punch, no fall, no visible mark yet. No printed logos or brand text anywhere. Cuts 7-10 read distinctly warmer, softer-focus and more saturated than every other cut in the piece — never let that grade bleed into the present-tense cuts. @Father in the memory is healthy, never gaunt or unwell. @Prop-BusCord never actually pulled. No readable hotel name or logo in cut 13; @Father never crosses the lobby threshold. Cut 16 (the bag struggle) stays hands-only — no blow, no fall, no injury, just the pull over the strap. Cut 17 is the one exception to the film's usual violence rule and stays exactly as written — no second angle, no additional blow, no blood, no wound, nothing beyond the single motion described. The harsh filter belongs to Cut 17 alone — no blur or desaturation bleeding into cuts 16 or 18, both stay clean. Cut 19: no visible reaction beyond cold and quick, no dialogue, no close-up on individual bills. Cuts 18-20: no dialogue, no second confrontation.

Grounded real-camera look, natural handheld weight, no whip pans, no lens flare except the intentional cut-away on Cut 17. Present-tense cuts: hard sodium-orange streetlight, cold bus interior light, warm interior lobby/room light once inside. Memory cuts (7-10): warm golden-hour light, soft-focus, an old photograph's palette, slight overlap between them as if one is still fading as the next arrives. Cuts land hard on every grade change elsewhere — no dissolve, no cross-fade anywhere except that deliberate overlap inside the memory montage itself.

AUDIO-SFX
Distant traffic, engine idle, his voice low and demanding, her clipped refusal, bus air brakes and door hydraulics. The memory cuts carry no dialogue, only muffled, warm, distant ambient sound — wind, faint laughter, no clear words, like a memory heard through glass, one impression's sound bleeding softly into the next. Cut back to the bus: near-silence, the faint chain-tick of @Prop-BusCord. Footsteps running, breathing hard, a car door. The clerk's voice, calm and routine, not fully intelligible, a key card printer. The key in the lock, the door forced open, voices rising and overlapping. On cut 16: fabric and strap strain, quick scuffling breath, no words. On cut 17: a single sharp sound of contact, then the lamp and glass hitting the floor in the same motion — no music, no sting, no riser over it, the sound itself is the only impact allowed. Then dead silence. The soft rustle of the bag opening, paper notes counted once. His slower breathing, footsteps, the DND tag swinging once, a car door, an engine driving away. No music, no score, anywhere in this piece.
```
