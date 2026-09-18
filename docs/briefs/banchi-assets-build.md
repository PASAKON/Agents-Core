# «บัญชี» — asset build sheet (Google Flow, 0 credits)

Everything in this file is **free**: image generation in Flow costs 0 credits
(measured many times) and so does binding a voice. **Generate NO video.** If any
action shows a credit estimate above 0, stop and report it.

Work in the Flow project that **already contains `@lung_somchai`**. Do not create
a new project. Report the project's name and URL first.

---

## PHASE 0 — inventory before you build anything (read-only)

List and report, as text:

1. Every item under `ตัวละคร` — its `@handle`, and **the voice bound to it**.
   Read the voice by selecting the character in the media picker and reading the
   voice row in the preview pane. If a character has no voice row, say so.
2. Every item under `ฉาก` and every plain image in `รูปภาพ`.
3. The credit balance.

**Do not create anything that already exists.** If an asset below is already
there, say so and move on.

**If a character's bound voice does not match the table in PHASE 2, DO NOT
change it.** Report the mismatch and continue. Casting is the CTO's call, never
the worker's.

---

## PHASE 1 — three new characters

Create each as a Character (`ตัวละคร`), model **Nano Banana Pro**, then rename it
to the handle exactly as written.

### `@cop_wit` — วิทย์, 32
```
Photorealistic portrait of a Thai man, 32 years old, medium athletic build,
short neat black hair, clean-shaven, calm steady eyes, a small pale scar
through the left eyebrow, wearing a plain dark-grey polo shirt, a simple steel
wristwatch on the left wrist. Neutral expression, looking straight at camera,
head and shoulders, plain light grey background, soft even frontal lighting, no
shadows on the face, sharp focus, 4:5.
```

### `@jae_muay` — เจ๊หมวย, 55
```
Photorealistic portrait of a Thai-Chinese woman, 55 years old, stout build,
short permed black hair greying at the temples, round face with laugh lines,
reading glasses pushed up onto her head, wearing a floral short-sleeve blouse
and a thin gold chain. Neutral expression, looking straight at camera, head and
shoulders, plain light grey background, soft even frontal lighting, sharp focus,
4:5.
```

### `@staff_a` — น้องเอ, 20
```
Photorealistic portrait of a Thai woman, 20 years old, slim, long black hair
tied back in a low ponytail, no makeup, wearing a plain light-blue short-sleeve
shirt under a clean dark apron. Neutral expression, looking straight at camera,
head and shoulders, plain light grey background, soft even frontal lighting,
sharp focus, 4:5.
```

---

## PHASE 2 — bind one voice to each NEW character

Open the character, click **`เลือกเสียง`** on the left, choose the preset by the
exact name below, and confirm the row afterwards reads that name with a `▶`.

| Character | Voice preset |
|---|---|
| `@cop_wit` | **Achird** |
| `@jae_muay` | **Laomedeia** |
| `@staff_a` | **Achernar** |

**Touch nothing on the four existing characters.** Their voices are already cast
(Algenib / Iapetus / Gacrux / Umbriel) and are not yours to change even if one
looks wrong — report, do not fix.

Also confirm, without binding it to anything, that a preset named **Sulafat**
exists in the voice list. It is the series narrator and will be attached as a
standalone voice later.

---

## PHASE 3 — six locations

Create each the same way `@noodle_shop` was created, so they attach as
ingredients in `องค์ประกอบ` mode. Rename to the handle exactly.

### `@upstairs_bedroom`
```
Interior of a small upstairs bedroom in an old narrow Bangkok shophouse. A
single low wooden bed against a bare plaster wall, a folded blanket, a small
side table holding medicine bottles and a glass of water, a standing fan, one
bare bulb hanging from the ceiling, wooden floorboards with visible gaps between
them, a shuttered window letting in one thin band of daylight. Empty, no people.
Contemporary Thai realist drama, shot on 35mm, warm desaturated colour, soft
natural light, 4:5.
```

### `@back_alley`
```
A narrow back alley behind an old Bangkok shophouse at night. Rough concrete and
brick walls, stacked plastic crates, a closed steel rear door, a drain grate in
the wet ground, tangled overhead cables, a single distant streetlamp throwing
hard side shadows. Empty, no people. Contemporary Thai realist drama, shot on
35mm, desaturated colour, 4:5.
```

### `@side_wall`
```
The side exterior wall of an old Bangkok shophouse just before dawn. Rough grey
concrete with peeling paint and long water stains, an air-conditioner bracket, a
rusted pipe running down the wall to the ground. Near-total darkness lit only by
a distant streetlamp. Empty, no people. Contemporary Thai realist drama, shot on
35mm, desaturated colour, 4:5.
```

### `@street_front`
```
A narrow busy street in an old Bangkok neighbourhood in daylight, seen from the
pavement outside a shophouse. Parked motorcycles, power poles with tangled
cables, small shopfronts on the opposite side, hot hazy sunlight, dust in the
air. Any passers-by are distant and out of focus. Contemporary Thai realist
drama, shot on 35mm, warm desaturated colour, 4:5.
```

### `@staircase`
```
A narrow steep wooden staircase inside an old Bangkok shophouse, running from a
ground-floor shop up to the living floor. Worn treads, a painted wooden
handrail, a single bulb on the landing above, shadows falling across the
stairwell wall. Empty, no people. Contemporary Thai realist drama, shot on 35mm,
warm desaturated colour, 4:5.
```

### `@noodle_shop_thriving`
```
Interior of a small family noodle shop in an old Bangkok shophouse at lunchtime,
every table taken. Steam rising from the wok station, a second stock pot added
beside the first, clean stools, freshly painted walls, a row of hanging ladles.
Bright, warm and busy. Customers are seen only from behind and out of focus, no
faces. Contemporary Thai realist drama, shot on 35mm, warm colour, 4:5.
```

---

## PHASE 4 — five props

Same method. **Every prop prompt deliberately forbids text and numbers** — the
model renders Thai text and digits as garbage, and this production's rule is
that the spoken lines carry every number anyway.

### `@bedrail_marks` — the most important asset in the film
```
Extreme close-up of the wooden side rail of an old low bed, covered in dense
hand-cut tally marks: hundreds of short vertical scratches gouged into the wood
in uneven rows, some pale and fresh, some darkened with age and dust settled in
the grooves. Worn varnish, bare timber showing through. Dim warm light from a
single bulb. No people, no text, no numbers, no writing of any kind.
Contemporary Thai realist drama, shot on 35mm, 4:5.
```

### `@fathers_phone`
```
A plain black budget Android smartphone lying face down on a scratched wooden
counter beside a folded cloth. Screen not visible. A small crack in one corner
of the rubber case. Warm overhead light, shallow depth of field. No people, no
text. Contemporary Thai realist drama, shot on 35mm, 4:5.
```

### `@qr_sign`
```
A small laminated payment sign in a thin metal stand, standing on a noodle-shop
counter beside a stack of melamine bowls and a jar of chopsticks. The sign is
plain, slightly sun-faded and curled at one corner. Warm overhead light, shallow
depth of field. No people, no readable text. Contemporary Thai realist drama,
shot on 35mm, 4:5.
```

### `@empty_pill_pack`
```
An empty blister pack of pills lying on a bedside table beside a half-full glass
of water, every bubble popped and the foil torn open. Dim warm light. No people,
no text, no printing on the foil. Contemporary Thai realist drama, shot on 35mm,
4:5.
```

### `@money_fold`
```
A small folded stack of worn Thai banknotes held with a rubber band, lying on a
dark wooden counter. Soft warm light from above, shallow depth of field. No
people, no readable text. Contemporary Thai realist drama, shot on 35mm, 4:5.
```

---

## PHASE 5 — the report, and the one thing that makes it worth anything

For **every** asset you created, write one line saying what the image **actually
shows** — and inside that line, **name at least three things the model put in
that the prompt never asked for.**

That last requirement is the whole point. This production's governing rule is
that **the prompt overrides the reference image**: any detail a later prompt
fails to mention will be silently changed by the model. So the asset sheet has
to record what is really there, not what we asked for. A report that simply
repeats the prompt back is useless and will be rejected.

Example of an acceptable line:

> `@fathers_phone` — phone face down on the counter as asked. Not in the prompt:
> a blue rubber band around the case, a chipped enamel mug at the top-left edge
> of frame, and a water ring on the wood under the phone.

Also report: the credit balance before and after (it must be unchanged), and the
wall-clock time each phase took.
