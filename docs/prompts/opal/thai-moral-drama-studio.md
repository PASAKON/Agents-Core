# Opal app prompt — "Thai Moral Drama Studio"

Paste everything below the line into Google Opal (opal.withgoogle.com) as the
app description. Opal turns it into a visual multi-step workflow you can then
edit block by block.

---

Build me a mini-app called **Thai Moral Drama Studio**.

It turns one idea into a complete, production-ready package for a vertical
Thai moral-drama series that I will shoot in Google Flow with Veo. It never
generates video itself — its job is to produce the text I paste into Flow.

## What the user types in

1. `theme` — the moral at the heart of the series, in Thai (e.g. "ความซื่อสัตย์", "กตัญญู", "โลภมากลาภหาย")
2. `setting` — where and when (default: ชุมชนเมืองไทยปัจจุบัน)
3. `episodes` — how many episodes (default 6)
4. `seconds_per_episode` — target length in seconds (default 420 = 7 minutes)
5. `cast_size` — how many named characters (default 4)

## Steps the app runs, in order

### Step 1 — SERIES BIBLE
Write the series bible in Thai:
- ชื่อซีรีส์ + logline หนึ่งประโยค
- แก่นคุณธรรม และ "บทเรียน" ที่ผู้ชมต้องรู้สึกเอง ไม่ใช่ถูกสั่งสอน
- โลกของเรื่อง: ย่าน อาชีพ ฐานะ ฤดู
- โทนภาพ: อ้างอิงหนังไทยร่วมสมัย ระบุแสง สี เลนส์

**PREMISE ENGINE — mandatory, state all three explicitly.** The premises that
sustain a long serial all contain the same three parts, so that every episode
has something to reveal, something to run out of, and someone to walk in:

- **ความลับ (the secret)** — one fact that, if it came out, breaks someone
- **นาฬิกา (the clock)** — a deadline already running: a debt due, an illness,
  a court date, a wedding, a shop lease
- **พยาน (the witness)** — a character who could expose the secret at any moment

If you cannot name all three in one line each, the premise will die around
episode 5. Rewrite it before continuing.

### Step 2 — CHARACTER BIBLE
For each of `cast_size` characters output a block containing:
- ชื่อไทย, อายุ, อาชีพ, ปมในใจ, สิ่งที่ต้องการ, สิ่งที่กลัว
- **APPEARANCE LOCK** — one dense English paragraph describing ONLY things a
  camera can see: age, build, face shape, hair, skin, eyes, exact clothing with
  colours and materials, one distinctive prop. No emotions, no backstory, no
  camera or lighting words. This paragraph must be identical every time the
  character is mentioned anywhere later in the output.
- **REFERENCE IMAGE PROMPT** — a prompt for one clean portrait to upload into
  Flow as an Ingredient. Always this shape:
  `Photorealistic portrait of <APPEARANCE LOCK>. Neutral expression, looking
  straight at camera, head and shoulders, plain light grey background, soft
  even frontal lighting, no shadows on the face, sharp focus, 4:5.`
- **INGREDIENT NAME** — a short @handle I will use in prompts, e.g. `@somchai`

### Step 3 — EPISODE MAP (Beat Engine, adapted to 6-8 minutes)

The Chinese vertical-drama standard is one Beat Engine per 60-120 second
episode: HOOK -> FRICTION -> TURN -> CLIFFHANGER. At 6-8 minutes an episode
needs **four chained engines**, not one, or the middle sags and viewers leave.

Lay every episode out on this spine and give me the timecodes:

```
[0:00-0:15]  HOOK - the explosion point
             Open mid-conflict. No establishing shot, no title card, nobody
             walking into a room. TEST: a stranger who knows nothing about this
             series must understand WHAT IS AT STAKE within 3 seconds. If they
             would need backstory, it is not a hook yet - rewrite it.

[0:15-2:00]  BLOCK A   friction -> small turn -> micro-hook
[2:00-4:00]  BLOCK B   friction -> small turn -> micro-hook
[4:00-6:00]  BLOCK C   friction -> THE EPISODE'S BIG TURN

[6:00-6:45]  PAYOFF - the moral beat lands. A character CHOOSES, and the choice
             costs them something visible. Never a speech explaining the lesson.
             The audience must see the price being paid.

[6:45-7:00]  CLIFFHANGER - see the four shapes below
```

Each micro-hook is a small unresolved question placed at a block boundary. It is
what carries a viewer across the moment they would otherwise scroll away.

**THE FOUR CLIFFHANGER SHAPES - rotate them, never repeat two episodes running.**

| Shape | What it is | Thai-drama example |
|---|---|---|
| **REVELATION** | a fact lands that reframes everything | ซองเงินนั้นไม่ใช่ของพ่อ |
| **REVERSAL** | someone does the opposite of who they have been | คนที่ยอมมาตลอด ลุกขึ้นปฏิเสธ |
| **DEADLINE** | the clock reaches zero, on screen | ป้ายยึดร้านถูกติดหน้าประตู |
| **INTRUSION** | someone walks in at the worst possible second | ลูกสาวยืนอยู่ที่ประตูมาตั้งแต่เมื่อไหร่ |

Why rotate: a season that ends every episode on a REVELATION trains the audience
to expect one, and by episode 15 the reveals carry no weight. Output a rotation
table for the whole season showing which shape each episode ends on, and verify
no shape repeats back to back.

For each episode also give me:
- ชื่อตอน
- the one-line HOOK, written as an image, not as a summary
- the three micro-hooks with their timecodes
- the big turn
- the payoff choice and exactly what it costs the character
- the cliffhanger, tagged with its shape
- continuity carried in from the previous episode (wardrobe, time of day, props)
- which part of the premise engine moved this episode: did the secret leak, did
  the clock advance, did the witness get closer?

### Step 4 — SHOT LIST
For the requested episode, break it into shots. Rules:
- Each shot is **8 seconds or less** — Veo's ceiling. Prefer 5-7.
- Total shot seconds must land within 10% of `seconds_per_episode`.
- At 7 minutes that is about 53 shots of 8 seconds. Build to the spine's
  timecodes: HOOK is roughly shots 1-2, each BLOCK about 15 shots, PAYOFF
  about 6, CLIFFHANGER 2.
- Vertical 9:16, always.
Output a table with: shot number - seconds - shot size - camera move -
characters in frame (as @handles) - location - time of day - Thai dialogue -
tone of delivery - sound.

### Step 5 — VEO PROMPT WRITER
Turn every shot into a Flow-ready prompt, in this exact shape:

```
[SHOT n - Ns - 9:16]
INGREDIENTS: @handle1, @handle2
<shot size>, <camera move>, <location>, <time of day>, <lighting>.
<What physically happens, in plain visual English.>
<@handle1> speaks in Thai. He/She says, in Thai: "<บทพูดไทย>" <tone> tone.
Audio: <ambience>. No music.
```

Hard rules for every prompt you write:
- English for everything except the spoken line. The spoken line stays in Thai
  script, inside double quotes, and is always preceded by `speaks in Thai`.
- Name every character by @handle and list them on the INGREDIENTS line. A
  character who is on screen but not on that line is a bug — fix it.
- Never write a character's appearance again in the prompt body. The Ingredient
  carries it. Repeating it fights the reference.
- Never use depth words like "closest to the lens" or "in the foreground" to
  mean size — they change how big the model draws things. Anchor size to
  something else in frame instead.
- No real people, no brands, no logos, no copyrighted characters, no text
  on screen.
- One action per shot. Two actions is two shots.

### Step 6 — CONTINUITY AUDIT
Before showing me anything, check the whole episode and report violations:
- a character on screen missing from an INGREDIENTS line
- wardrobe, time of day, weather or location changing without a cut motivating it
- a prop appearing that was never established
- any shot over 8 seconds
- any dialogue line too long to speak in its shot's seconds (Thai speech runs
  roughly 4-5 syllables per second — count it)
List each violation with its shot number and the fix. Do not silently repair
them; show me.

## How the output is laid out

Show me, in this order, each in its own copyable block:
1. Series bible
2. Character bible + the reference image prompts (these go into Flow's
   Ingredients first, before any video)
3. Episode map
4. The shot list table for episode 1
5. Every Veo prompt for episode 1, numbered, each on its own so I can copy one
   at a time into Flow
6. The continuity audit

Then let me ask for any other episode number and regenerate steps 4-6 for it,
reusing the same bible unchanged.

## Voice

Write all story content in natural spoken Thai — the way people actually talk,
not translated English. Dialogue should be short. A moral drama earns its
lesson through what a character chooses, never through a speech explaining
the lesson.
