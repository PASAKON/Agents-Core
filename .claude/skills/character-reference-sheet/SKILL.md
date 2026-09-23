---
name: character-reference-sheet
description: Generate a neutral, reusable AI character reference sheet (white-background emotion grid + one full-body panel) for any film/video project character — human, alien, monster, anything. Locked to fal.ai openai/gpt-image-2 only (no other model). Trigger on /character-reference-sheet and proactively whenever the user wants to create/generate a character, character sheet, character reference, or turnaround for a story/film — says "สร้าง character", "ทำ character sheet", "generate ตัวละคร", "character reference sheet", "turnaround", "ตัวละครใหม่", or hands you a character description with the intent to reuse it across multiple scenes via @CharacterN. Do NOT fire for a single in-scene cinematic character portrait with baked-in mood/lighting for one specific shot (that's seedance-scene-prompt's job) or for logo/brand mascot work (that's the claudesign/mooniex-tool-builder pipeline).
---

# Character Reference Sheet

Generates the **neutral base asset** a character needs before it can be reused
across scenes via `@CharacterN` — not a moody in-story shot. Confirmed against
a real production reference by the CEO (2026-08-08); the first attempt at this
(a single cinematic portrait) was rejected for exactly this reason.

## What it does

Builds one `fal.ai openai/gpt-image-2` prompt that produces a single image
containing: a plain white-background emotion grid (3–6 labeled panels) plus
one full-body panel, all of the same character, same lighting, same identity
— so the model can re-light and re-pose this character correctly in any later
scene prompt instead of dragging one scene's mood into every future shot.

## When to invoke

- "สร้าง character ตัวใหม่ให้หน่อย"
- "ทำ character sheet ของ [ตัวละคร]"
- "generate ตัวละคร [ชื่อ] ไว้ใช้ในหนัง"
- "character reference sheet" / "turnaround"
- User pastes a character description and says they want to reuse it across
  scenes / tag it as `@CharacterN`

## When NOT to invoke

- A single cinematic shot of a character **inside a specific scene** (mood
  lighting, in-world action) — that's `seedance-scene-prompt`'s job. If the
  user already has a reference sheet and wants a scene, redirect there.
- Logo, brand mascot, or wordmark character work — that's the
  `mooniex-tool-builder` / claudesign pipeline, not this skill.
- If the user names a different image model explicitly (not GPT Image Gen2)
  — stop and ask. This skill is locked to one model on purpose (see below).

## Hard rules — the 3 things that make a sheet correct

Get any of these wrong and the output is a cinematic portrait, not a
reference sheet — worthless as a reusable base.

1. **Plain white/light-grey studio background only.** No props, no scene, no
   environment. Even, soft, flat studio lighting — no dramatic shadows, no
   colored gels, no mood lighting of any kind. The whole point is a neutral
   base a later scene prompt can re-light however that scene needs.
2. **3–6 numbered, labeled emotion close-up panels in a grid.** Each panel:
   bold number + emotion name top-left (e.g. `01 NEUTRAL/NORMAL`,
   `02 SUBTLE SMILE`, `03 LAUGHING`, `04 CRYING`, `05 TERROR/HORROR`). Pick
   the actual emotions this character needs across the story — don't default
   to a generic set if the character's arc calls for something specific
   (fear, pleading, curiosity, rage, etc.).
3. **Exactly one full-body panel**, larger than the emotion-grid panels,
   standing straight in a neutral pose, arms at sides, full wardrobe and
   body visible head to toe, same plain background as the grid.

Every panel must be the **same character** — identical face, hair, skin,
build — only expression and pose differ panel to panel.

## Model — locked to GPT Image Gen2 only

This skill uses **`fal.ai openai/gpt-image-2` and no other model**, per
standing instruction (2026-08-08: "อันนี้ไว้สำหรับ GPT Image Gen2 เท่านั้น
และเราจะใช้มันแค่ Model เดียวก่อน" — this is for GPT Image Gen2 only, one
model for now). Do not substitute nano-banana, seedance, or any other fal.ai
model for this skill even if it seems similar — ask first if the user wants
to change that.

**There is no MCP server for fal.ai in this org.** Every fal.ai call is a
direct REST script reading a local `.env` file — this is proven working
across multiple production scripts, not a workaround.

- Endpoint: `https://fal.run/openai/gpt-image-2`
- Auth: header `Authorization: Key <FAL_API_KEY>` — **variable name is
  `FAL_API_KEY`, not `FAL_KEY`** (a generic fal.ai skill/MCP config may
  assume the wrong name).
- Key location (this org): `/Users/gob/MoonieXHQ/Agents/Core/.env`, line
  `FAL_API_KEY=...`
- Payload: `{"prompt": ..., "image_size": "square_hd", "quality": "medium",
  "num_images": 1, "output_format": "png"}`
- Cost: **~$0.053/image at `quality: "medium"`** (org-standard rate, same as
  every other gpt-image-2 call in this repo). `quality: "high"` is ~$0.25 —
  do not use high unless the user asks for it specifically.
- Reference implementations in this repo:
  `scripts/gen-brandprompt-scenes.py`, `scripts/gen-alien-character.py`

## Steps

1. **Confirm the character isn't already covered.** If a reference sheet for
   this character already exists (check the project's character-prompt
   template / prior `@CharacterN` assignments), don't regenerate — ask
   whether this is a correction or a genuinely new character.
2. **Pick 3–6 emotions** the character actually needs in the story (not a
   generic default set) — ground this in the actual scenes/story beats
   already written, if any exist.
3. **Write the prompt** following the exact structure in the Output Format
   below — grid side + full-body side + one shared character description
   block covering face/hair/skin/build/wardrobe, identical across panels.
4. **State the cost** (~$0.053) and get explicit confirmation before calling
   the API, unless the user has already given standing authorization for
   this specific generation in the current conversation.
5. **Generate via the direct REST call** (see Model section) — write a
   small one-off script following `scripts/gen-alien-character.py`'s
   pattern if one doesn't already exist for this character, save the output
   under the project's character-assets folder.
6. **Show the result** — `open <path>` to launch it in Preview (chat cannot
   render images inline), and sanity-check against the 3 hard rules before
   declaring it done.
7. **Refuse and stop** if the character description is too thin to fill
   face/hair/skin/build/wardrobe/personality — ask for the missing detail
   rather than inventing a character from nothing.

## Operating rules

- **Never bake scene mood into a reference sheet.** If a prompt draft
  mentions dramatic lighting, a location, or an action beat, that's the
  seedance-scene-prompt skill's job, not this one — strip it back to plain
  white/neutral before generating.
- **Never swap the image model** without the user explicitly asking to.
- **Always confirm the `.env` key exists** (`grep FAL_API_KEY
  /Users/gob/MoonieXHQ/Agents/Core/.env`) before assuming the call will work — if
  missing, stop and say so rather than let the API call fail silently.
- **State the exact cost before every generation.** Standing authorization
  for one character does not carry over to the next character.

## Output format

```
Character reference sheet, plain white/light-grey studio background, even
soft studio lighting, no shadows, no props, no scene — identical character
in every panel, only expression and pose change.

LEFT SIDE — N emotion close-ups in a labeled grid, each panel numbered and
titled top-left in bold sans-serif:
01 <EMOTION NAME> — <short performance note>
02 <EMOTION NAME> — <short performance note>
... (3-6 total, chosen for what this character actually needs in the story)

RIGHT SIDE — 1 full-body panel, larger than the emotion grid, character
standing straight in a neutral pose, arms at sides, full wardrobe and body
visible head to toe, same plain white background.

CHARACTER (identical across all panels): <face> <hair> <skin> <build>
<wardrobe>. High resolution, detailed textures, no text other than the
panel labels, no watermark.
```

## Worked example — @Character4 The Alien (ประตูวาป, generated 2026-08-08)

```
Character reference sheet, plain white/light-grey studio background, even
soft studio lighting, no shadows, no props, no scene — identical character
in every panel, only expression and pose change.

LEFT SIDE — 5 emotion close-ups in a labeled grid, each panel numbered
and titled top-left in bold sans-serif:
01 NEUTRAL/NORMAL — calm, unreadable, resting alien expression
02 CURIOUS — head tilted slightly, watching
03 PAIN — eyes tightened, jaw clenched from captivity
04 PLEADING — eyes wide, searching, silently asking for help
05 FEAR — recoiling, eyes wide with alarm

RIGHT SIDE — 1 full-body panel, larger than the emotion grid, character
standing straight in a neutral pose, arms at sides, full wardrobe and body
visible head to toe, same plain white background.

CHARACTER (identical across all 6 panels): a sexless, ageless humanoid
alien being. Gaunt, elongated face, no hair, smooth hairless scalp. Pale,
near-translucent, sickly grey-white skin, faint teal bioluminescent veins
visible near cable connection points on the neck and forearms. Thin,
frail, slightly stooped build. Torn lab-issue containment wrap, medical
tubing and cables connecting its body to external ports, restraint marks
on the wrists. High resolution, detailed textures, no text other than the
panel labels, no watermark.
```

Result: `output/warp-door/character4-alien.png` — CEO-approved, matches all
3 hard rules exactly.

## Reference

- `scripts/gen-alien-character.py` — working end-to-end implementation
- `scripts/gen-brandprompt-scenes.py` — original proven fal.ai call pattern
- `output/content/character-prompt-template.md` (Agents repo) — project-level
  character roster using this format
- [[seedance-scene-prompt]] — the sibling skill for in-scene cinematic shots
  once a character has a reference sheet

## How to write a GPT Image prompt — it is NOT a video prompt

Moved here from the org memory index 2026-08-25. Applies to every paid
gpt-image-2 call, including storyboard plates, not only reference sheets.

CEO, 2026-08-21, on a plate where the character came out in the wrong clothes:
the prompt was a 1,219-word video-style wall with ~25 negatives and seven
reference tags dropped inline under one blanket sentence, "as exact references,
unchanged". He was right that the method was wrong. **The long CAPS-heavy prose
that works for Seedance actively defeats GPT Image.**

OpenAI's cookbook and fal's GPT Image 2 guide agree on five rules:

1. **Index and role-label every reference, then say how they interact.**
   `Image 1: the room. Image 2: the man at the far end — keep his wardrobe.`
   Without the labels the model guesses which attachment is content and which is
   style. This was the single biggest defect.
2. **Short labelled sections with line breaks** — scene → subject → details →
   intended artefact → constraints. Never one paragraph.
3. **Positive preservation beats negation.** `keep`, `preserve`, `do not
   redesign the character`, `change only X and keep everything else the same`.
   Negatives are for watermark / text / border-class exclusions, not for
   carrying the description.
4. **Repeat the preserve list every iteration** — the cookbook's own advice for
   reducing drift.
5. **Fewer, deliberate references — one image per role.** Conflicting references
   produce conflicting output; seven refs competing is why the wardrobe drifted.
   Cut to four and the attention lands.

The principle behind all five: the best prompt is not the longest one, it is the
one that makes the model spend attention on the details that matter.

**Distance trap, worth its own line:** a character rendered small in frame loses
wardrobe first, because the reference has too few pixels to bind. Counter it
explicitly — *render him small but crisp, with his Image 2 wardrobe clearly
legible at that distance* — and name the wardrobe in words rather than leaving
it to the plate alone.

Sources: OpenAI cookbook, multimodal image-gen prompting guide; fal.ai's
prompting guide for GPT Image 2.
