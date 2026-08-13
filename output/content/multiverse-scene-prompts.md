# The Multiverse — Full Scene Prompt Library

All scenes written to the `seedance-scene-prompt` skill format (REFERENCE +
VISUAL + DIALOGUE + AUDIO/SFX). Character sheets defined once below — every
scene references them by `@CharacterN` tag instead of re-describing from
scratch. Generate each `@CharacterN` once in Seedance 2.0 (start from the
character reference sheet prompt if one hasn't been generated yet), save it,
and reuse the tag across every scene that character appears in.

Source: `THE MULTIVERSE — Concept Sheet` artifact, Act 1 "Ordinary Earth."

---

## Character Sheets

### @Character1 — Mother
Real woman, early 40s. **Face:** rounded and warm, large expressive dark
eyes, soft full cheeks, gentle laugh lines. **Hair:** shoulder-length dark
hair, loosely tied back, a few loose strands. **Skin:** warm, lived-in,
no heavy stylization. **Build:** sturdy, capable, medium height. **Personality
read:** warm, unhurried, comfortable running a busy kitchen, confident
half-smile as her default expression. **Default wardrobe:** cream blouse
under a flour-dusted apron, sleeves pushed up to the forearm.

### @Character2 — Father
Real man, mid-40s. **Face:** lanky, slightly oversized round glasses, big
expressive eyebrows usually mid-panic. **Hair:** disheveled short dark hair.
**Build:** lanky, rushed energy, kind eyes underneath the flustered surface.
**Personality read:** endearing, always running late, well-meaning but
distracted, means it when he tells his son to talk to Mother. **Default
wardrobe:** half-buttoned white dress shirt, loosened striped tie crooked to
one side, one dress sock visible (mid dressing-in-a-hurry), shoes usually in
hand rather than on his feet.

### @Character3 — Son
Real boy, Asian, around 11 years old. **Face:** big round dark eyes, a
stubborn cowlick in short black hair, a light spray of freckles, a faint
gap in his smile. **Build:** slouched shoulders, morning-grumpy posture,
moves in a rushed half-awake scramble in the mornings. **Personality
read:** on autopilot at breakfast, answers without really engaging — "It
was okay, I guess" energy — not sullen, just eleven and half-asleep; more
animated when actually rushing to get out the door. **Default wardrobe:**
Asian-style school uniform — button shirt slightly untucked/half-buttoned
in morning scenes, a necktie that starts the day looped on but unknotted,
tied on the move; school bag.

**Shared style lock for every scene below:** photoreal with warm
animated-character-inspired exaggeration — real performers styled like a
hand-painted late-1990s family-film aesthetic brought to life. Vivid
saturated warm color grading. Palette: Ink Teal `#1F3B3A`, Warm Paper
`#F3E6CE`, Mustard Gold `#E8A93D`, Sage `#7A8B6F`, Warm Rust `#C15B3D`.

---

## Scene 1 — Mother Cooks Breakfast (20s LONG TAKE, second-by-second frantic multitasking, ends pushed into the fridge door as a match point into Scene 2)

**Music leak fix (2026-08-07):** an earlier generation of this scene came
back with unwanted piano underscore despite "no music, no score" in the
AUDIO/SFX block — the warm family-kitchen mood likely biases the model
toward a piano score by default. Fixed by adding a blunt "NO BACKGROUND
MUSIC" directive as the very first line of the prompt (before REFERENCE),
and naming "piano" explicitly as excluded in the AUDIO/SFX block. Apply
the same opening line to any other warm/domestic scene in this project
if music leaks in again.

```
NO BACKGROUND MUSIC. NO SCORE. NO PIANO. NO INSTRUMENTAL TRACK OF ANY
KIND. Audio is diegetic sound effects only — nothing else in the mix.

REFERENCE
@Character1 — Mother (see Character Sheet)

VISUAL
LONG TAKE — one single unbroken 20-second handheld shot, the camera
never stopping and never breaking away for the entire duration, in a
cozy suburban kitchen at sunrise, warm painterly saturated color
grading, wood-paneled walls, soft golden morning light through
gingham curtains, counter crowded with mismatched mugs, a fruit bowl,
a child's drawing taped to the fridge. Mother, consistent with her
established look, never stops moving for the full twenty seconds, and
the camera never stops moving with her — this is one continuous take
from first frame to last. The pacing below is second-by-second timing
for that single continuous take, not on-screen text or graphics.

0-1s: Mother's hand is already reaching for the microwave handle as it
beeps.
1-2s: She yanks the door open, a burst of steam escaping.
2-3s: She pulls a bowl out one-handed, sets it down hard on the
counter.
3-4s: In the same beat, her other hand is already grabbing a pot lid.
4-5s: She lifts the lid, peeks underneath, sets it aside with a clank.
5-6s: She grabs a wooden spoon and clamps it between her teeth.
6-7s: Both hands free now, she cracks an egg one-handed into a bowl.
7-8s: Her other hand grabs a spatula off the counter mid-crack.
8-9s: She flicks the pan's contents with a sharp practiced wrist-snap.
9-10s: She takes the spoon from her mouth without looking and stirs a
pot once.
10-11s: She reaches back and yanks the fridge door open without
turning around.
11-12s: She grabs a milk carton from inside one-handed, eyes still on
the stove.
12-13s: She pours a quick stream into a glass on the counter while
already turning back to the pan.
13-14s: She checks the pan again and flips its contents with the
spatula.
14-15s: Toast pops from the toaster — she catches it barehanded
without flinching.
15-16s: Two fast strokes of butter across the toast, never slowing
down.
16-17s: She plates the final dish and wipes the counter edge in the
same sweep.
17-18s: She turns back to the fridge, sliding the milk carton back
inside with one hand.
18-19s: She pushes the fridge door shut and the camera keeps pushing
forward with her hand, moving in tight on the door as it swings closed,
the door's pale surface steadily filling more of the frame.
19-20s: The camera's forward push continues in the same unbroken
motion until the fridge surface fills the entire frame and the image
settles into total, even blackness — the shot ending inside that
darkness, still moving, never stopping.

Camera: handheld, one continuous take throughout — close and kinetic,
moving fluidly from station to station following Mother's hands
without ever breaking the shot, then in the final two seconds settling
into a single sustained forward push into the fridge door that carries
the shot all the way to black. The whole twenty seconds is one
uninterrupted camera move — nothing about it is edited or reset
partway through. Fine film grain, vivid saturated warm palette, soft
painterly late-1990s-family-film warmth brought into photoreal detail.
No text, no on-screen graphics, no timestamps rendered in frame.

AUDIO/SFX — SOUND EFFECTS ONLY, ABSOLUTELY NO MUSIC OF ANY KIND
No music. No score. No piano. No strings. No ambient instrumental bed
under the scene — the mix is 100% diegetic kitchen sound and nothing
else. A microwave beep cutting off sharply as the door yanks open, the
clatter of a bowl set down hard, a pot lid clanging against the
counter, the sharp crack of an egg against a bowl's rim, a spoon
clicking against teeth, a quick sizzle-flip in the pan, the
suction-seal pop of the fridge door opening, the glug of milk pouring,
the toaster's pop and the soft catch of toast in a bare hand — rapid
and overlapping start to finish, right up until the final beat, where
all of it drops away into the single low thud-and-click of the fridge
door sealing shut, then near-silence as the frame settles into black.
At no point does a musical instrument of any kind play.
```

**Continuity note for Scene 2 (Son opens the fridge) — also write Scene 2
as its own LONG TAKE:** open Scene 2 from that same settled blackness —
the very first frame is the fridge surface in darkness, then in one
continuous unbroken push the door swings open toward camera (Son's POV
or a shot from just past him), so the two clips read as one continuous
move through the fridge door when placed back to back. Match the
fridge's exact look (pale/steel surface, kitchen behind it) from this
scene when writing Scene 2's opening beat, and keep Scene 2's own
camera move single and unbroken start to finish, the same as this one.

---

## Scene 2 — Son Rushes Out (LONG TAKE, continues out of Scene 1's blackout, camera tracks Son throughout)

```
NO BACKGROUND MUSIC. NO SCORE. NO PIANO. NO INSTRUMENTAL TRACK OF ANY
KIND. Audio is diegetic sound effects and dialogue only — nothing else
in the mix.

REFERENCE
@Character1 — Mother (see Character Sheet)
@Character3 — Son (see Character Sheet)

VISUAL
LONG TAKE — one single unbroken handheld shot, the camera never
stopping and never breaking away for the entire duration, continuing
directly out of the previous scene's blackout. The very first frame is
near-total darkness — the same pale fridge surface from before — then
Son's hand shoves the door open toward camera, light flooding in as the
door swings past and reveals the same cozy suburban kitchen, warm
painterly saturated color grading, golden morning light through
gingham curtains.

The camera swings around with the door's motion and picks Son up
already moving — consistent with his established look, half into his
Asian-style school uniform, shirt still half-buttoned, his necktie
looped on but not yet knotted. Son spots Mother across the kitchen and
calls out a quick greeting without slowing down. Mother, consistent
with her established look, glances up from the counter and tells Son
to hurry, he's going to be late for school. Son grabs the two ends of
his tie and starts knotting it one-handed as he walks, the camera
tracking alongside him at a jog, staying close on his hands and face.
Mother adds, still moving herself, that he's going to make his father
late too.

Son reaches the fridge, still tying the knot, and yanks the door open
with his free hand. He grabs the milk carton and, tucked beside it, the
dish Mother packed for him earlier, then kicks the fridge door shut
with his heel without looking back, the tie now knotted crooked but
done. A car horn blares from outside, sharp and impatient. Son's head
snaps toward the sound and he's already moving, breaking into a run
toward the front door, the camera chasing him from behind, the kitchen
blurring past at the edges of frame. Son reaches the front door and
shoves it open one-handed, his school bag swinging. The door swings
back on its hinge toward camera, its surface filling more and more of
the frame until it eclipses the entire shot, plunging the take into the
same clean, total blackout that closed the scene before it.

Camera: handheld throughout, one continuous take — swings with the
fridge door on the opening beat, tracks tight alongside Son as he moves
and ties his tie, chases him from behind as he runs for the door, and
ends on a single push into the front door's surface all the way to
black. Nothing about the shot is edited or reset partway through. Fine
film grain, vivid saturated warm palette, soft painterly
late-1990s-family-film warmth brought into photoreal detail. No text,
no on-screen graphics, no timestamps rendered in frame.

DIALOGUE (spoken audio, not rendered as on-screen text)
SON (bright, quick, already moving):
"Morning, Mom!"

MOTHER (warm but urgent, calling after him without stopping her own
work):
"Hurry up, you're going to be late for school!"

MOTHER (a beat later, still moving):
"You're going to make your dad late too!"

[a car horn blares outside]

SON (shouting back over his shoulder, already running):
"Coming, Dad!"

AUDIO/SFX — SOUND EFFECTS ONLY BESIDES DIALOGUE, ABSOLUTELY NO MUSIC OF
ANY KIND
No music, no score, no piano, no strings, no ambient instrumental bed
— only diegetic sound and the dialogue above. The suction-seal pop of
the fridge door opening, fabric rustling as Son moves in his
half-buttoned uniform, the fridge door thudding shut from a heel-kick,
quick footsteps changing rhythm from a walk to a run, a sharp car horn
from outside, the front door's hinge creak and a hard thud as it swings
shut into the lens, then near-silence as the frame settles into black.
```

**Continuity note for a possible Scene 3:** this scene also ends on a
blackout (the front door swinging into camera), so a Scene 3 picking up
outside — Son running to the car, Father waiting — can open the same
way: first frame in darkness, then the door swings open away from
camera to reveal the front yard/car in morning light.

---
