---
name: seedance-scene-prompt
owner: CMO
origin: mooniex-org
scope: >-
  Cinematic scene prompts in REFERENCE + VISUAL + (DIALOGUE) + AUDIO/SFX format for
  Seedance 2.0 and similar audio-capable video models. Not for static images (see
  meigen), product or UI shots (see mooniex-tool-builder), or prose writing with no
  video-gen intent.
description: Write copyright-safe, character-consistent cinematic scene prompts for Seedance 2.0. Trigger on /seedance-scene-prompt, "เขียน prompt ฉากนี้", "ขอ prompt ฉาก", "write me a scene prompt", "video prompt สำหรับ Seedance", "@Image1 @Image2". Not for static-image prompts.
---

# Seedance Scene Prompt

Write single-shot, audio-capable video-gen prompts in a proven three/four-block
format. Developed and battle-tested writing ~15 scenes for a copyright-safe
mythic/historical parody-trailer project — every rule below exists because a
specific failure happened first and got fixed.

## When to invoke

- User asks to write/rewrite a prompt for an AI video generator (Seedance 2.0,
  Kling, Veo, or similar)
- User says "เขียน prompt ฉากนี้", "ขอ prompt ฉาก...", "write me a scene prompt",
  "video prompt for this scene", pastes `@Image1`/`@Image2` reference tags, or
  shares reference images asking for a matching scene
- User is iterating on a generated clip that "didn't work" (wrong character,
  copyright flag, AI attributed a line/action to the wrong character, format
  broke) — diagnose against the rules below before rewriting

## When NOT to invoke

- Static image-only prompts with no motion/video intent
- Non-cinematic asset requests (product shots, UI mockups, social graphics,
  logos) — those are a different skill's job
- Pure prose/story writing with no stated intent to feed a video generator

## Output format

Always these blocks, in this order. Omit `DIALOGUE` if the scene has no
spoken lines. `REFERENCE` is optional — include it only when reference
images/characters exist for this scene.

```
REFERENCE
@Image1 [what this image depicts — full detailed description: is it a
character or a scene? Describe it like the character-consistency rule below.]
@Image2 ...
(up to @Image8, or @Character1/@Character2... for a previously-generated and
saved character reference)

VISUAL
[Flowing prose. One continuous shot. Explicit subject-noun repetition
(see Rule 3). Ends with: "No modern elements, no text, no on-screen
graphics."]

DIALOGUE (spoken audio, not rendered as on-screen text)
[Only if the scene has lines. Format:
CHARACTER NAME (parenthetical performance direction):
"The line, in quotes."
Never render dialogue as on-screen text/captions — audio only.]

AUDIO/SFX
[Diegetic sound only. Almost always opens with: "Sound effects only, no
music, no score, no dialogue." (Drop "no dialogue" if a DIALOGUE block
exists — SFX is the ambient bed under it, not silent.) Diegetic
in-scene music — a lyre player performing, hand drums at a dance — is
allowed since it's part of the action, not an overlaid score. Layer each
sound as: SOURCE (what's making it) + TEXTURE/material quality, tied to
something visible in the VISUAL block.]
```

## Hard rules

**1. Character consistency — describe before you use.**
Before a character's first appearance in any prompt, write an extremely
detailed description regardless of whether a reference image exists: face,
personality read, age, hair color, eye color, facial hair, skin
tone/complexion, distinguishing marks, height, build. This is what lets the
model hold the character steady across separate generations. On every later
appearance, anchor with a phrase like *"consistent with his established
look"* rather than re-describing from scratch.

**2. Copyright safety — generic description, not real names.**
Never include: real director names, real film titles, real actor names, or
real trademarked brand/format names (e.g. "IMAX" → "large-format 65mm
film"). Beyond keyword-avoidance, watch for **scene-similarity/fingerprint
flagging** — some tools flag prompts that too closely recreate an actual
real, currently-trending copyrighted scene's staging even with zero proper
nouns in the text. If adapting from a real reference image/trailer, vary at
least a few concrete staging details (framing, prop, color, blocking) so it
reads as inspired-by, not a 1:1 recreation.

**3. Flowing prose with explicit subject repetition, not screenplay labels.**
The `VISUAL` block must be continuous prose — heavy screenplay-style headers
(`MAN:`, `WOMAN:`, `Framing:`, `Negative prompt:`) as the primary structure
has broken parsing on at least one real tool. Instead, repeat the subject
noun across sentences ("The hero... The hero... The islanders...") rather
than relying on pronouns once multiple characters are in frame — ambiguous
pronouns cause the model to misattribute actions/lines to the wrong
character. `DIALOGUE` blocks are the one place short character-name labels
are fine and expected.

**4. No burned-in captions, ever.**
Spoken dialogue is audio only. Never describe or request on-screen
text/subtitles for dialogue — the user adds subs themselves in post. In-world
diegetic text (a sign, a prop screen like a phone UI) is fine and different
from this rule — that's part of the shot, not a caption overlay.

**5. One scene, one shot.**
Each prompt is a single continuous take, not a multi-shot edited sequence.
Avoid instructing hard mid-clip cuts ("the edit cuts to...") inside one
prompt — describe continuous camera movement (push-in, handheld, pan)
instead. If the user's brief genuinely needs multiple distinct shots, that's
multiple separate prompts, not one.

**6. Seedance 2.0 specifics.**
- Has a native audio toggle — AUDIO/SFX blocks are used, not wasted (confirmed
  across 300 CEO-generated videos; do not assume it's silent).
- Reference images: up to 8, tagged `@Image1`...`@Image8`.
- A generated character can be saved once and reused via `@Character1` instead
  of re-uploading a raw image every time.
- Kling reportedly enforces fewer prompt-structure rules than Seedance 2.0
  (less detail confirmed so far — treat as looser, not documented).

## Refusal / clarification conditions

- **No character description yet and the scene needs one:** stop and ask for
  (or generate and confirm) the detailed character description before writing
  the scene prompt. Don't invent a first-time character silently.
- **Real name/title/brand slipped into the brief:** don't pass it through —
  generalize it in the output and tell the user what was substituted and why
  (per Rule 2), same way each copyright fix this session was surfaced.
- **Scene brief looks like a near-1:1 recreation of a specific real, current
  film's shot:** flag the specific similar details and adjust staging before
  writing, don't wait for a rejection to fix it reactively.
- **Language ambiguous (Thai brief, unclear if output should be Thai or
  English):** default to English for the final copy-paste-ready block unless
  the user has asked for Thai in this exchange — but state the assumption.

## Worked examples

### Example 1 — dialogue scene, no reference images

Input: *"ขอฉากพระเอกคุยกับหญิงในเต็นท์เก่าๆ ถามว่าติดเกาะมานานแค่ไหน เธอตอบ 20 วัน"*

Output:

```
REFERENCE
(none supplied — character described inline instead)

VISUAL
Inside a rough castaway shelter built from weathered driftwood and old
bent branches, roofed and walled with strips of once-fine silk now faded,
torn, and sun-bleached. Warm late-afternoon light filters through the thin
worn fabric.

The hero is a bearded, weathered man in his forties, dark hair streaked
with grey, deep-set tired eyes, sun-worn olive skin, broad but leaner than
before, roughly 180cm, wearing a dark bronze-and-leather sleeveless
cuirass over a linen tunic. The hero sits near the shelter's opening,
looking out at the sea, then turns to the woman beside him.

The island woman has natural, sun-warmed blonde hair falling loose over
her shoulders, calm grey eyes, early thirties, self-possessed and at ease
in this place. The island woman sits close to the hero, both facing the
shelter's opening and the sea beyond.

The hero asks her quietly, hoarse, how long he has been stranded here.
The island woman takes a long moment before answering, studying his face —
the pause stretches like it's building toward something serious. Then she
answers simply, and after a small beat adds one more word, deflating the
tension instead of confirming it.

Camera: intimate, static-to-slow-drift two-shot, both faces visible,
shallow depth of field. Fine film grain, large-format realistic
epic-adventure look, warm golden-hour palette. No modern elements, no
text, no on-screen graphics.

DIALOGUE (spoken audio, not rendered as on-screen text)
THE HERO (quiet, hoarse, almost afraid to ask):
"How long... am I here?"

[she thinks for a moment before answering]

THE ISLAND WOMAN (calm, measured, delivered like it's significant):
"Twenty..."

[a small beat]

THE ISLAND WOMAN (continuing, deflating it):
"...days."

AUDIO/SFX
Sound effects only, no music, no score. Distant surf rolling steadily
outside, faint wind moving through the loose silk walls making them
ripple and snap softly, occasional creak of the old driftwood frame
settling, a few birds far off. Hold the pause before "days" long enough
for the silence itself to feel like the joke's setup.
```

### Example 2 — pure b-roll, no dialogue, no reference

Input: *"scam broker office being cleared out at night, for the scam-news b-roll batch — no characters, just the room"*

Output:

```
VISUAL
A dark corporate office being cleared out at night. Rows of identical
office chairs sit empty at abandoned desks, their monitors dead and
unlit. Stacked cardboard moving boxes crowd the far wall and a side
aisle, some still open, others taped shut. A single red emergency-exit
sign glows at the far end of the room, the only source of color in the
space. Structural support pillars break up the room into deep shadowed
bays.

Camera: slow lateral tracking shot moving past the empty chairs and
stacked boxes at desk height, drifting toward the glowing exit sign.
Realistic 4K, dark moody cinematic, high contrast, neon-red accent
lighting. No modern text overlays, no logos, no faces, no brand.

AUDIO/SFX
Sound effects only, no music, no score, no dialogue. The low electrical
hum of the building's remaining lights, a soft rolling squeak of one
office chair wheel catching a floor seam, the dry cardboard-on-cardboard
scrape of a box shifting under its own weight, distant traffic murmur
bleeding faintly through the windows, the faint buzz of the exit sign's
failing ballast.
```

Note: this is the pattern our overnight scam-news b-roll batch (Black
Liquidity, 30-clip queue) *should* use going forward — those clips were
generated with VISUAL only, no AUDIO/SFX block, before this skill
confirmed Seedance 2.0's native audio toggle actually works. Retrofit
AUDIO/SFX onto future batches in this series.

### Example 3 — reference-image reuse with `@Character1`

Input: *"ฉากต่อไปของ Black Liquidity — พระเอกเดินเข้าไปหาต่อหน้าต้นฉากเดิม แล้วเงยหน้ามองกล้อง ใช้ตัวละครเดิม"*

Output:

```
REFERENCE
@Character1 The established Black Liquidity male avatar: young adult
male, 18 years old but still visibly teenage/youthful, Caucasian, fair
skin, smooth clean-shaven face with no facial hair or stubble, slim
build, medium height, short dark hair mostly hidden under a black ribbed
knit beanie worn straight (not slouchy), with a rectangular black fabric
patch centered on the front reading "RICH" in bold white sans-serif
all-caps condensed lettering. Black rectangular Wayfarer-style
sunglasses, fully opaque dark lenses, black frame. Black tailored suit
blazer with structured shoulders over a white button-down polo shirt,
collar visible, top button open. Expression serious, calm, confident,
closed-mouth, direct posture.

VISUAL
A dark home-office trading desk at night, three monitors glowing behind
with abstract candlestick charts, a bookshelf partially visible at the
frame edge. The man, consistent with his established look, walks slowly
into frame from the shadows toward the desk. Neon red LED rim light
traces his beanie, shoulders, and blazer edge against the dark
background as he moves. The man stops beside the desk, turns, and tilts
his head up to look directly into the camera, calm and unhurried.

Camera: slow low tracking shot following him in from the side, settling
into a static push-in as he meets the camera's gaze. Realistic 4K, dark
moody, neon red accents, cinematic, high contrast, photorealistic. No
text overlay, no logo, no brand, no readable chart data.

AUDIO/SFX
Sound effects only, no music, no score, no dialogue. Soft footsteps on
hardwood, the faint electronic hum of the monitors, a subtle creak of
a leather chair being brushed past, quiet ambient room tone, the faint
click of a desk lamp's switch just off-frame.
```

Note: `@Character1` assumes this exact avatar was already generated once
and saved as a character reference in Seedance — don't re-describe from
a raw `@Image1` upload once a saved character exists. This is the
Black Liquidity brand avatar (see `blackliquidity-character.json` in
`scripts/higgsfield/prompts/`) — keep the locked_description fields
identical across every clip that uses this character; only the scene
context changes.

## Reference

- [[reference_visual_audio_sfx_prompt_pattern]] — memory note this skill was
  distilled from; keep both in sync if the Seedance/Kling capability picture
  changes.
