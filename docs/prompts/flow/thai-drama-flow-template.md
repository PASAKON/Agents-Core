# Google Flow / Veo 3.1 — Thai short-drama production template

For a long-running vertical Thai moral-drama series shot entirely in Flow.
Every rule here comes from Google's own Veo 3.1 prompting guide or from the
Flow help pages, except where marked COMMUNITY.

---

## 0. Hard limits — design around these, they do not bend

| Thing | Real value |
|---|---|
| Clip length | **4, 6 or 8 seconds only** (three discrete choices) |
| Aspect ratio | 16:9 or **9:16** (vertical is native, no cropping) |
| Resolution | 720p / 1080p — **1080p upscale costs 0 credits** on Plus/Pro/Ultra |
| Ingredients per prompt | **3 maximum** |
| Negative prompts | **Do not exist.** Describe what you want, never "no X" |
| Custom voice / uploaded audio | Not supported — audio is model-generated only |
| Real identifiable people as reference | Blocked by policy |
| Extend | Costs a full generation (Fast 20, Quality 100) |
| Credits | Do not roll over |

Consequences for the series:
- A scene with 4+ locked characters **must** be split across shots. Three faces
  per shot is the ceiling.
- An 8-second ceiling means the episode is built from 8s bricks. Write to the brick.
- "No music" works. "No cars, no buildings" does not — say what IS there instead.

---

## 1. Series setup — do this once, then never again

### 1.1 Ingredients (one per character, plus one for the main location)

Generate or upload one clean portrait per character. COMMUNITY: cut the
background out, or shoot on plain grey — it measurably improves consistency.

Reference-image prompt shape:

```
Photorealistic portrait of <APPEARANCE LOCK>. Neutral expression, looking
straight at camera, head and shoulders, plain light grey background, soft even
frontal lighting, no shadows on the face, sharp focus, 4:5.
```

**APPEARANCE LOCK** = one paragraph of camera-visible facts only: age, build,
face shape, hair, skin, eyes, exact clothing with colours and materials, one
distinctive prop. No emotion, no backstory, no lighting or camera words. Write
it once, store it in the series bible, and **never paste it into a shot prompt
again** — the Ingredient carries it, and repeating it fights the reference.

Name each one with a short handle: `@somchai`, `@daeng`, `@shophouse`.

### 1.2 One project per series
One Flow project holds the whole series. Ingredients live at project level, so
every episode reuses the same locked faces.

---

## 2. Shot prompt template — the default brick

Google's official formula is:

**`[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]`**

Fill it like this:

```
[SHOT n - 8s - 9:16]
INGREDIENTS: @somchai, @daeng

<Shot size>, <camera move>. <Subject doing the one action>, <where>, <when>.
<Lighting>. <Style / film reference>.
@somchai speaks in Thai. He says, in Thai: "<บทพูด>" <tone> tone.
Ambient noise: <soundscape>. No music.
```

Worked example:

```
[SHOT 3 - 8s - 9:16]
INGREDIENTS: @somchai, @daeng

Medium two-shot, slow dolly in. A man in a shopkeeper's apron pushes a folded
envelope across a wooden counter toward a younger man who will not take it,
inside a narrow Bangkok shophouse, late afternoon. Warm low sun through a
doorway, deep shadows at the back of the room. Contemporary Thai realist
drama, shot on 35mm, muted colour.
@somchai speaks in Thai. He says, in Thai: "เก็บไว้เถอะ พ่อไม่ได้ให้ยืม" firm but tired tone.
Ambient noise: street traffic outside, a ceiling fan. No music.
```

Rules:
- **One action per shot.** Two actions is two shots.
- Every character on screen appears on the INGREDIENTS line. A face on screen
  that is not on that line will drift.
- Never say "closest to the lens" or "in the foreground" to mean *big* — Veo
  reads those as size instructions and will oversize the subject. Anchor size to
  something else in frame instead.
- Dialogue only counts as dialogue inside double quotes. Without quotes the
  model narrates instead of speaking.

---

## 3. Timestamp variant — the credit multiplier

Veo accepts timed beats inside one clip. This is the single biggest saving on a
small credit budget: four beats for one generation charge instead of four.

```
[SHOT 5 - 8s - 9:16]
INGREDIENTS: @somchai, @daeng

[00:00-00:02] Close-up on a hand hesitating over the envelope on the counter.
[00:02-00:04] Reverse shot, the younger man's face, jaw tightening.
[00:04-00:06] Medium two-shot, he pushes the envelope back without a word.
[00:06-00:08] Wide shot from the doorway, both men still, the street bright behind them.
Warm low sun, deep shadows. Contemporary Thai realist drama, 35mm, muted colour.
@daeng speaks in Thai. He says, in Thai: "ผมทำเองได้ครับ" quiet, controlled tone.
Ambient noise: street traffic, a ceiling fan. No music.
```

Use it for reaction chains, montages, and anything where the camera changes but
the location does not. Do **not** use it to cross locations — that is what
`Jump To` is for.

---

## 4. Two-hander dialogue variant

Three Ingredients is the ceiling, so a conversation between two people plus a
location reference is exactly at the limit.

```
[SHOT 7 - 8s - 9:16]
INGREDIENTS: @somchai, @daeng, @shophouse

Medium two-shot, locked camera, both men facing each other in profile.
<one physical beat>. <lighting>. <style>.
@somchai speaks in Thai. He says, in Thai: "<บรรทัดที่ 1>" <tone> tone.
Then @daeng answers in Thai. He says, in Thai: "<บรรทัดที่ 2>" <tone> tone.
Ambient noise: <soundscape>. No music.
```

Thai speech runs roughly 4-5 syllables per second. Two lines will not fit in
8 seconds unless both are short — count the syllables before you spend the credit.

---

## 5. What actually breaks a shoot — COMMUNITY-reported

| Failure | What to do |
|---|---|
| **"Audio Generation Failed"** - video does not generate at all | Known bug, worse when stitching in Scenebuilder. Regenerate; check the credit came back |
| **Dialogue flagged even though the visuals passed** | The audio layer has its own content filter. Rewrite the line, do not fight it |
| **Age-detection false positives** - the most-reported classifier problem | Avoid youthful-looking characters in any charged situation; state adult ages in the Ingredient |
| Ingredient with a busy background | Cut the background out. Plain grey reference = far better consistency |
| Missing audio after Scenebuilder stitch | Check every clip's audio before assembling, not after |

---

## 6. Credit plan on Google AI Pro (฿750 / 1,000 credits per month)

| Model | Credits | Clips/month | 1080p upscale |
|---|---|---|---|
| Veo 3.1 Lite | 10 | 100 | free |
| **Veo 3.1 Fast** | 20 | **50** | free |
| Veo 3.1 Quality | 100 | 10 | free |

Veo charges the same for a 4s and an 8s clip — **always generate 8s.**

Recommended split for one episode (~75s = ten 8s bricks):

```
35 x Fast      = 700 credits   blocking, dialogue, everything
 3 x Quality   = 300 credits   opening shot, closing shot, the emotional beat
------------------------------
                1,000 credits  then upscale everything to 1080p for free
```

With a realistic 3x retry rate that is roughly **one finished episode per month**
on this plan — enough to prove the format, not enough to run a series. Timestamp
prompting (section 3) is what stretches it furthest.
