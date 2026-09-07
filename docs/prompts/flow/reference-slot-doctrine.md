# Reference-slot doctrine — how to spend the 5 image inputs on every 8s shot

CEO's production rule, 2026-09-07, reconciled with the measured API limits.

## The five inputs (official Veo 3.1 API)

```
image           1 slot   first frame          does NOT count against the 3
referenceImages 3 slots  characters / props   THE scarce resource
lastFrame       1 slot   final frame          does NOT count against the 3
```

Flow's web UI exposes only the middle three. **The first/last frame slots exist
only through the API** — which is the single strongest reason to script the
generation rather than click it.

## Rule 1 — LOCATION placement is UNDECIDED. Do not treat this as settled.

**Status: open question, being A/B tested. See `docs/tests/ab-location-slot.md`.**

The first draft of this doctrine said the first frame carries the location and a
reference slot must never be spent on it. The CEO raised a counter-argument that
is stronger than the original rule:

> A 9:16 first frame shows one vertical strip of a room. The moment the camera
> moves, Veo has to invent everything outside that strip — and it invents
> something different every shot. A location reference gives it the whole set,
> so the invented parts stay consistent across shots.

That is a real mechanism, not a preference, and it cannot be settled by reading
docs. Until the test in `docs/tests/ab-location-slot.md` returns a result, treat
the allocation below as the **working default**, not the rule:

Working default (unproven):
```
image           = the composed opening frame -> LOCATION + blocking + background props
referenceImages = speaking character 1, speaking character 2, hero prop
lastFrame       = where the shot must end (optional)
```
If the test shows a location reference measurably reduces set drift, the default
becomes: speaking character 1, speaking character 2, LOCATION — and the hero prop
moves into the first frame instead.

```
image           = the composed opening frame -> LOCATION + blocking + background props
referenceImages = speaking character 1, speaking character 2, hero prop
lastFrame       = where the shot must end (optional)
```

Two speakers plus one hero prop is exactly three. That is why the two-speaker
limit below is not a style preference — it is what makes the arithmetic close.

## Rule 2 — slot priority, in this order

| Priority | What | Why it must be a reference, not just described |
|---|---|---|
| **P1** | every character who SPEAKS in this shot | the face is on screen, held, and lip-synced. Drift here is unwatchable |
| **P2** | the hero prop that is handled and recurs | an envelope that changes colour between shots breaks the story |
| **P3** | location | demoted — it lives in the first frame |
| — | silent background people | no slot. They may drift; keep them out of focus |

If a shot needs two speakers and two hero props, you are over budget. Put the
second prop **into the first-frame image** and let the frame carry it.

## Rule 3 — at most two speaking characters per shot

More than two and the three slots cannot hold the speakers plus the prop, and
Thai dialogue for three people will not fit in eight seconds anyway (Thai runs
4-5 syllables per second; 8 seconds is 30-35 syllables total).

Background characters are unlimited and cost nothing — they simply get no
reference and no lines. **An unreferenced extra who appears in two consecutive
shots will look like a different person.** Either keep extras out of focus and
in motion, or promote one to a reference slot and accept the cost.

## Rule 4 — anything that appears in more than one shot MUST have an image

No exceptions. A character, a prop, or a location used twice without a locked
reference will come back different, and the audience reads that as a mistake
before they read it as a story.

The reference image itself must be: single subject, plain light-grey ground,
flat frontal light, no shadow on the subject, no other objects in frame.
A busy reference degrades consistency measurably.

## Rule 5 — chain the frames, do not re-plate every shot

Within one continuous scene, extract the last frame of shot N with ffmpeg and
pass it as the first frame of shot N+1:

```bash
ffmpeg -y -sseof -0.05 -i shot_N.mp4 -frames:v 1 -q:v 2 frame_for_shot_N1.jpg
```

Free, exact, and it makes the cut invisible. Generate a **new** plate only when
the camera changes setup or the story cuts to a different place or time.

Practical effect on an 8-minute episode: 60 shots need roughly **20-25 generated
plates**, not 60. The remaining 35-40 first frames are chained.

## Rule 6 — generate the plates in Flow, generate the video through the API

Measured on 2026-09-07 (task-796a93f6): **image/Ingredient generation inside
Flow cost 0 credits** — four portraits, all free. Video generation charged 20
credits every time.

So the cheap architecture is:

```
Flow web  ->  make every plate and every character reference   (0 credits)
              download them
API       ->  fire the video with image + 3 referenceImages     (paid, scriptable)
```

Caveat: 0 credits was measured for **character** images specifically. Verify the
same holds for scene/location plates before relying on it for 25 of them.

## Rule 7 — download immediately

Generated videos are deleted from Google's servers after **2 days**. Any script
that fires and does not fetch within that window has burned the money for
nothing.

## Per-shot record the script must carry

Every shot in the shot list states all five, explicitly:

| field | example |
|---|---|
| `image` | `plates/p04-shop-counter-afternoon.jpg` — or `CHAIN from shot 12` |
| `ref1` | `@father_somchai` (speaks) |
| `ref2` | `@son_ton` (speaks) |
| `ref3` | `@prop_envelope` |
| `lastFrame` | none — or `plates/p05-...jpg` when the cut must land exactly |

A shot whose on-screen speaker is missing from ref1/ref2 is a bug, not a style
choice. Audit for it before spending anything.
