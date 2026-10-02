---
name: CMO_Knowledge_Cinematography_ShortMovie
kind: knowledge
description: "KNOWLEDGE — Professional cinematography for a SHORT MOVIE (หนังสั้น, cinema grammar) made with AI video engines: lighting setups, portrait patterns, contrast ratios, colour temperature and time of day, shot sizes, camera angles, camera movement, lens and depth of field, composition and continuity grammar (180°, 30°, eyeline, screen direction, match cut), colour worlds and grading (stylised yellow-green: Khondji, Delicatessen, Amélie), and what Veo, Runway, Kling, Wan and Seedance officially accept and measurably follow for camera and light; every fact sourced (StudioBinder, ASC, Deakins forum, vendor guides, VBench-2.0, GitHub). Trigger on /CMO_Knowledge_Cinematography_ShortMovie and on \"จัดแสง\", \"มุมกล้อง\", \"ภาษาภาพ\", \"cinematography\", \"lighting setup\", \"shot size\", \"camera angle\", \"camera movement\", \"เลนส์\", \"color grade\", \"Short Movie\", \"หนังสั้น\". Do NOT fire for ละครสั้น / lakorn / short drama / 短剧 / vertical micro-drama (CMO_Workflow_LakornSerial, CMO_Standard_Story_ThaiMoralDrama, CTO_ILAG_LakornTheme), for engine buttons and money (the engine skills), or for how a prompt file is laid out (CMO_Standard_Film_PromptFormat)."
owner: CMO
created_by: agent
author: {role: cto, date: "2026-10-03"}
improved_by: []
aka: []
audience: [cmo, cto, cxo, script_writer, browser_operator]
verified: "2026-10-03"
refresh_after: "2027-01-03"
---

# Cinematography for a Short Movie: light, camera, lens, colour

Verified 2026-10-03 at the sources in the Sources table (session cto-671f688f). The full tables, quotes and
links are in `docs/research/2026-10-03-cinematography-short-movie.md`; this file keeps what a shot needs.
Tags: **[unverified]** only a search summary supports it · **[secondary]** a blog reporting someone else's
work · **[suggested]** wording derived here, not tested on any engine. Untagged = read at the primary page.

## 0 · Scope: Short Movie only (CEO 2026-10-03)

> "ที่สำคัฐ อันนี้คือShort Movie ไม่ใช่ ละครสั้นนะ อย่าเอามา ปนกัร" (verbatim, typos kept)

- **Covers** a Short Movie (หนังสั้น): one story in cinema grammar, landscape 16:9 or wider, made to be
  watched as a film. First user: THE LAST BELL (`docs/prompts/last-bell/`).
- **Does not cover** ละครสั้น, lakorn serials, short drama, 短剧 or vertical micro-drama. They have their own
  skills (CMO_Workflow_LakornSerial, CMO_Standard_Story_ThaiMoralDrama, CTO_ILAG_LakornTheme). The one
  GitHub repo here that ships a micro-drama template (GH1 `micro-drama.md`) was read with that file excluded.
- **Does not repeat** what other skills own: measured engine behaviour (§8.1 points to it), the prompt-file
  layout (CMO_Standard_Film_PromptFormat), the film pipeline and gates (CMO_Workflow_ShortFilm,
  CMO_Knowledge_Film_Production).

## 1 · Lighting

### 1.1 Setups (SB4 unless tagged)

| Setup | Look | Story use | Words an engine knows |
|---|---|---|---|
| Three-point | Key, fill, back around the subject | Neutral, controlled baseline | "soft key camera-left, gentle fill, thin backlight" [suggested] |
| High-key | Strong key + generous fill, almost no shadow | Cheerful, open, safe | "bright high-key lighting, minimal shadows" [suggested] |
| Low-key | Little or no fill, high contrast | "Dramatic, suspicious, or even scary" | Wan: `High contrast`, `Side light` (WAN1) |
| Hard light | Small or bare source, crisp shadows | Drama, noir | Wan: `Hard light`; "harsh noon sun" |
| Soft light | Large or diffused source | Flattering, romantic | Wan: `Soft light`; Veo: "Soft morning light" (G2) |
| Motivated | Light seems to come from a source in the scene | Invisible artifice; Deakins: unmotivated light "always takes me out of the movie" | Name the source: "lit only by the bedside lamp" [suggested] |
| Practicals | Lamps that appear in frame and light the scene (Moonlight's diner bulbs) | Realism, longer takes | "warm tungsten practicals", "harsh fluorescent overhead lights" (G2) |
| Available | Existing light shaped with bounce and flags | Authentic, cheap (The Revenant, magic hour) | "natural window light" [suggested] |
| Negative fill | Black flag on the shadow side removes light | Shape and contrast without a lamp | "deep shadow side, no fill" [suggested] (RD2) |
| Rim / back | Edge light from behind; "a separation tool, not a key light strategy" (MC) | Separation, mystery | Wan: `Backlight`, `Rim Light` |
| Silhouette | Key straight behind the subject | Withheld identity, reveal | Wan: `Silhouette` |
| Top / bottom | From overhead / from below | Isolation / uncanny [unverified] | Wan: `Top Light`, `Bottom Light` |

### 1.2 Portrait patterns: where the key sits decides the shadow (LP, MC)

| Pattern | Key position | Shadow | Mood |
|---|---|---|---|
| Flat | Under 30° off the lens axis | None | Clean, clinical |
| Loop | ~25–50° to the side, a little above the eye | Small nose shadow toward the mouth corner | Natural, like window light |
| Rembrandt | ~45–60° to the side, ~45° up | Inverted triangle of light on the shadow cheek | Gravitas, drama |
| Split | 90° to the side | Half the face dark | Villain, moral doubt |
| Butterfly | In front, ~45° above, on the lens axis | Symmetric shadow under the nose | Glamour, Golden-Age look |
| Rim | ~120° behind | Only the edges | Separation, mystery |

No source tested whether a pattern NAME ("Rembrandt", "butterfly") changes an AI engine's output. Describe
the geometry instead: "key from 45° camera-left above eye level, a triangle of light on the shadow cheek"
[suggested].

### 1.3 Contrast ratio, key + fill : fill (SB5)

| Ratio | Stops | Look | Use |
|---|---|---|---|
| 1:1 | 0 | Flat | Sitcom, corporate |
| 2:1 | 1 | Moderate | General drama |
| 4:1 | 2 | Strong shadows | Dramatic scenes |
| 8:1 | 3 | "Highly dramatic and stylized" | Noir, horror |

### 1.4 Colour temperature and time of day (WK-CT, WK-GH, DFN)

| Source | Kelvin |
|---|---|
| Low-pressure sodium streetlight (near-monochrome yellow) | ~1,700 K |
| Candle, sunrise / sunset | ~1,850 K |
| Household bulb | ~2,400 K |
| Studio tungsten | 3,200 K |
| Golden-hour sun | ~3,500 K |
| Midday sun, daylight balance | 5,500–5,600 K |
| Overcast | ~6,500 K |

- **Golden hour:** about the hour after sunrise or before sunset; soft, warm, low contrast, long shadows.
  *Days of Heaven* was shot almost entirely in it. **Blue hour** sits outside it: predominantly blue, no
  sharp shadows.
- **Mixed temperatures are a tool:** Khondji dims tungsten to amber against a "very blue" exterior (ASC2).
- **Day for night:** underexpose 2–3 stops, backlight with the sun as a moon rim, keep the sky out of frame.
  *Fury Road* overexposed instead and darkened in post to keep shadow detail (DFN). AI wording [suggested]:
  "moonlit night, cold blue backlight rimming shoulders, dark sky, no daylight sky".

### 1.5 Physics a prompt can borrow (RD1, RD2)

- Softness comes from **source size relative to the subject**; fall-off is steeper the **closer** the source
  is. "A large soft source close to the face" gives soft light that drops fast into darkness (David Mullen ASC).
- Deakins on low-key: "Make the decision when you shoot not in post." For AI this means the look goes in the
  prompt: AI footage has a low colour bitrate and bands when it is graded hard (GH1 cases).

## 2 · Shot sizes (SB1; engine words G2, KL1, WAN1)

| Size | Framing | Story use |
|---|---|---|
| Establishing / EWS | Subject small in the place | Place dominates; isolation, scale |
| WS / LS | Whole subject plus surroundings | Character against the world |
| FS | Head to toe | Presence, blocking several people |
| Cowboy | Mid-thigh up | Action and emotion together |
| MS | Waist up | Dialogue buffer |
| MCU | Chest up | Body language plus face |
| CU | Face fills frame | Emotion, reaction |
| ECU | Eyes, lips, a trigger finger | Detail, intensity |
| Two-shot / insert | Two people / an object detail | Relationship / plot information |

Size words are soft on AI engines: Seedance 2.0 Mini, asked for a face "filling sixty percent of frame
height", pulled back to ~45% (CMO_Knowledge_Seedance2.5_Higgsfield, 2026-09-10). Higgsfield's own guide
uses field of view and distance instead: "84° diagonal field of view", "camera 4 meters from the face"
(HF1); untested in-house.

## 3 · Camera angles (SB2 unless tagged)

| Angle | Effect |
|---|---|
| Eye level | Neutral, equal, empathetic |
| Shoulder level | "Much more standard than eye level", the default cinema height |
| Low angle | Power, superiority, or fear of the subject |
| High angle | Inferiority, vulnerability |
| Overhead / bird's-eye | Neutral or "divine" view; surveillance |
| Ground / worm's-eye | Engages the viewer, features without faces |
| Dutch / canted | Unease, madness; overuse reads as a gimmick (*Battlefield Earth*, WK-DA) |
| Over-the-shoulder | Places two people in dialogue (Wan official term, WAN1) |
| POV | Identification with the character (Veo term, G2) |

## 4 · Camera movement (SB3 unless tagged)

| Move | What it is | Use | AI note |
|---|---|---|---|
| Static / locked-off | Frame never moves | Performance, dread by stillness | The hardest move for every engine (§8.3) |
| Pan / tilt | Rotation, horizontal / vertical | Reveal, follow / scale, awe | Kling words: "pan left", "tilt up" (KL2) |
| Whip pan | Very fast pan, motion blur | Energy, a transition | Runway lists it (RW1) |
| Push-in (dolly in) | Camera moves closer | Tension, an inner decision | "The most reliable Veo move" (AVB) |
| Pull-out | Camera moves away | Isolation, reveal | Kling: "pull back" |
| Zoom | Focal length changes, camera stays | Unease; "can feel artificial" | Wan official I2V words are "camera pushes in / pulls out" (WAN1) |
| Dolly zoom | Push in while zooming out | Psychological shock | Vendor claims only [unverified] |
| Truck | Camera slides sideways | Parallax, walking beside someone | In-house: a lateral track stitches easier than 3-D moves (L1) |
| Crane / boom | Large vertical sweep | Grandeur, opening and closing reveals | Veo: "Crane shot" (G2) |
| Tracking | Camera travels with the action | Immersion (*1917*) | Veo, Kling, Wan all list "tracking shot" |
| Arc / orbit | Camera circles the subject | Builds tension (the *Dark Knight* Joker arc) | Veo "180-degree arc shot"; Kling "orbit slowly" |
| Handheld | Operator's body shows | Subjectivity, chaos | GH1: "extremely subtle, breath-like camera float" |
| Drone / FPV | Flying camera | Scale / kinetic | Wan: "Drone shot", "Fast fly-through" |
| Rack focus | Focus shifts between planes | Hands the viewer a clue | GH1 suspense SOP |

Genre defaults from a 450★ practitioner repo, untested by us (GH1): horror, a very slow creep-in or a
locked frame with off-screen sound; action, a tracking sprint or low-angle hero rise; romance, a breath-float
two-shot or a pull-back leaving the couple; suspense, frame-within-frame or a high surveillance angle; epic,
a reveal crane-up or a locked extreme wide with the subject in the lower fifth. One lens and one grade per
sequence.

## 5 · Lens and depth of field (SB8, LN, MO)

| Class | mm (35 mm equivalent) | Effect | Use |
|---|---|---|---|
| Ultra-wide | under 23 | Distortion, near-180° | Unease, grotesque (*The Favourite*) |
| Wide | 23–35 | Exaggerated depth, near things huge | Immersion, energy |
| Normal | 35–55 (50 "clean, honest") | Close to the eye | Neutral observation |
| Telephoto | 55 and up (85/135 portrait) | Background close behind, shallow focus | Isolation, surveillance |

- **Compression comes from camera distance**, not focal length; the long lens only forces the camera back
  (LN; one StudioBinder summary said the opposite). Say both: "shot from far away on a long telephoto lens,
  background compressed close behind her" [suggested].
- **Depth of field** depends on aperture, focal length, distance and sensor. Deep focus stages meaning in
  depth (*Citizen Kane*); shallow focus isolates (*Nightcrawler*) (SB9).
- **A mm number works better with its look described:** "85mm portrait lens, flattering facial compression"
  beats "85mm" alone (MO). GH1 names real bodies and lenses ("Panavision C-series lens, 35mm focal, f/4");
  the claim that training data binds those strings to a look is the repo's, unverified.
- Veo words: "Shallow depth of field", "Deep focus", "Wide-angle lens", "Macro lens" (G2). Wan words:
  `Long-focus lens`, `Short-focus lens`, `Ultra-wide-angle fisheye` (WAN1).

## 6 · Composition and continuity

**Composition (SB9, WK-HR, KL1, WAN1)**
- Rule of thirds; off-centre framing shows a character's relation to the world (Kling: "rule of thirds",
  "off center"; Wan: `Left-heavy / Right-heavy / Balanced composition`).
- Headroom: too much shrinks the subject, too little is claustrophobic. Lead room in the direction of
  movement, look room in front of the face; short-siding breaks it on purpose for unease [unverified].
- Leading lines, symmetry for control or dread (*2001*), deep-space staging, frame within frame,
  negative space. Actor blocking steers the eye.

**Continuity grammar (SB6, SB7, M5C, WK-MC)**
- **180° rule:** keep the camera on one side of the line between two people, so each keeps a screen side.
  Kubrick broke it on purpose in *The Shining*.
- **30° rule:** a cut to the same subject needs at least 30° of angle change or a clear size change, or it
  reads as a jump cut.
- **Eyeline match:** the person on the left looks camera-right, the person on the right looks camera-left.
- **Screen direction:** exit frame-right, enter the next shot frame-left, keep moving the same way. GH1: two
  AI clips "read as two separate videos" until the exit and entry edges matched.
- **Coverage** runs establishing, master, mediums, close-ups, OTS, shot / reverse shot (Veo accepts "Reverse
  shot", G2). **Match on action** cuts during the movement. **Match cut** carries a shape or motion across the
  cut (the *2001* bone to satellite).
- AI engines confuse left and right (~0.5 on spatial relations, L2): state geography outright, e.g.
  "Left-right geography holds through all cuts" (HF1).

## 7 · Colour worlds, including yellow-green

### 7.1 Reference films

| Film / DP | Look | How it was made | Purpose | Src |
|---|---|---|---|---|
| *Delicatessen* (1991), Darius Khondji | Gold and yellow-sepia against inky blacks | Gold chosen over a planned blue / dark green; bleach bypass (silver left in the print raises contrast) | Absurd post-apocalyptic fairy tale | ASC1 |
| Khondji's method | Gold made by adding green | "1/8 or 1/4 green gels with tracing paper on tungsten lights at 3200 or 3400 K"; tungsten dimmed to amber against blue exteriors | Green is his "second friend" | ASC2 |
| *The City of Lost Children* (1995), Khondji | Pitch blacks against green | A silver-retention variant | Dream-nightmare | ASC1 |
| *Se7en* (1995), Khondji | Dark with detail in the blacks | Deluxe CCE, "more radical bleach-bypass" | Decay | ASC1 |
| *Amélie* (2001), Bruno Delbonnel | Lime greens, mustard yellows, saturated reds | Early digital intermediate: blues pushed toward green, reds boosted [secondary] | Whimsy | NFS, AM |
| *The Matrix* (1999), Bill Pope | Sickly green inside the simulation | Graded to evoke old monitors | "Nothing is authentic" | NFS |
| *Fight Club* (1999), Jeff Cronenweth | Desaturated, green-tinted | From 7-Eleven fluorescent light at night | Soul-sucking routine | FC [secondary] |
| *Fallen Angels*, *Happy Together*, Christopher Doyle | Dirty greens and yellows under neon | Neon and fluorescent practicals, complementary pairs | Urban loneliness | WKW [secondary] |
| *Traffic* (2000) | Hot yellow Mexico strand | Tobacco filter, Ektachrome | Became the "Mexican filter" trope: avoid | TR [secondary] |

Other palettes (NFS): *The Godfather* underexposed amber, *300* bleach-bypass bronze, *Fury Road* saturated
orange and teal, *Moonlight* blue and neon purple, *Sin City* selective colour.

### 7.2 Turning a colour world into a prompt

1. **Put the colour in the light sources first, then name the grade.** Khondji and Doyle made colour with
   the lamps (ASC2, WKW). [suggested]: "overhead green fluorescent tubes, amber tungsten practicals dimmed
   low, inky crushed blacks, bleach-bypass contrast, lime and mustard palette".
2. **Give proportions and anti-looks**, as HF1 does: "60 percent cold steel-blue … 30 percent matte black …
   10 percent warm focal pop" and "NOT golden-hour Hollywood, NOT teal-and-orange blockbuster". Wan tone
   words: `Warm tones`, `Cool tones`, `Low/High saturation`, `High/Low contrast` (WAN1).
3. **Lock the grade in the prompt, not in post** (§1.5).
4. **Paste one grade block verbatim into every shot of the film** (CMO_Standard_Film_PromptFormat; GH1:
   "color drift wrecks the cut").

## 8 · AI engines: what they accept and what they follow

### 8.1 Already measured in the org: read there, not here

Camera lock in the tech header, beat order, operator vocabulary, one move per shot, grade and lens at the
end, a cut needs a visible change, a video reference beats prose for camera, reference images carry lighting,
size anchored to an object, no model mixing inside a scene, Seedance 2.0 shot numbers against 2.5 timestamps:
CMO_Standard_Film_PromptFormat, CMO_Knowledge_Seedance2.5_Higgsfield, CMO_Knowledge_Film_Production,
`docs/prompts/MASTER-PROMPT-cinematic.md`. Evidence: L1, L2, K1–K3 in the research file §8A.

### 8.2 Vendor-stated prompt order

| Engine | Order | Camera and light notes | Src |
|---|---|---|---|
| Veo 3.1 | Cinematography + Subject + Action + Context + Style | Multi-shot as `[00:00-00:02]` blocks; exclusions written as positive description | G2 (2025-10-16) |
| Runway Gen-4 / 4.5 | Camera movement + Scene + Action + Details | "Choose one primary movement per prompt"; "No camera shake" can summon shake, write "Smooth, stable camera movement" | RW1 (2025-11-04), RW2 |
| Kling 3.0 | Subject, action, setting, camera, lighting, mood | Nine camera words: push in, pull back, pan left/right, tilt up/down, track forward, orbit slowly, static camera | KL1 (2026-08-07), KL2 |
| Wan 2.x–3.0 | T2V: entity + scene + motion + aesthetics + style. **I2V: motion + camera only** | Cuts happen between clips, not inside one; write "Generate single shot." | WAN1 (2026-09-28) |
| Seedance 2.5 | References → one-line summary → timed plot → constants | No negative field in the API; Higgsfield uses FOV degrees, metres, lens locks, "HARD CUT" | L1, HF1 |

Vendors disagree on where the camera goes: Veo and Runway put it first, Wan later. The org's long-prompt
finding (instructions early followed 67.9%, late 10.1%, L2) reconciles them: the move early, lens and grade
in the shared end block. Not A/B-tested.

### 8.3 What benchmarks and practitioners measured

- **Static shots are the least reliable instruction.** Runway: static shots are "challenging"; its fix is
  "The camera is entirely motionless for the duration of the scene, with movement only occurring from the
  subject." (RW2). Wan 2.1: "Static", "Fixed" and "Steady camera" never held 100% (WAN2, GitHub #429).
  Unspecified camera defaults to drift or a slow push-in (PA [secondary]).
- **Camera adherence is low.** VBench-2.0 (2025-08-20): Kling 1.6 61.73%, HunyuanVideo 33.95%,
  CogVideoX-1.5 33.33%, Sora 27.16%. Older models; no 2026 engine measured (VB).
- **Some moves are easier.** Veo 3.1: push-in most reliable, subject-targeted orbit works, broad reveal pans
  are weak. Kling 3.0: slow deliberate moves hold, aggressive multi-axis paths drift (AVB, ~$48 test).
  Wan 3.0 had the clearest front tracking move; Seedance 2.5 kept event order (GG, no numbers published).
- **Vague style words do nothing.** "Cinematic dramatic camera move around the hero" fails; "Medium
  close-up, low-angle 30° from left. Orbit clockwise, very slow" works better (GH1).
- **A lucky take does not reproduce.** GH1's author: 20+ rerolls for hard shots, ~200 generations for ~40
  final clips; "treat one prompt as a ticket to draw".
- **Lighting words in official vocabularies:** Wan `Soft/Hard/Side/Top/Bottom/Back/Rim light`,
  `Silhouette`, `Daylight`, `Firelight`, `Overcast`, `Dawn`, `Night` (WAN1); Veo "single, dramatic
  spotlight", "lens flare" (G2); Kling "golden hour", "cold blue night", "god rays" (KL1).

## 9 · Writing camera and light into one shot [suggested, built on §8, not A/B-tested]

1. **One named move**, early, in operator words, with speed and direction ("very slow push-in",
   "orbit clockwise"). Static: lock it in the header, put the motion in the subject, use a previz video
   reference when it matters.
2. **Size and angle as geometry**: "medium close-up, camera at shoulder height, 30° camera-left", or FOV and
   metres.
3. **Light as source + direction + quality + colour**, sourced in the scene: "single oil lamp low
   camera-right, hard warm light, deep olive shadow on the far cheek, no fill".
4. **Lens and grade** in the shared end block, word for word in every shot.

Worked example for THE LAST BELL's yellow-green world (BIBLE.md §2) [suggested]: put the colour in sources
the city owns (sodium-like gold lamps, green-gelled lanterns, a chartreuse sky) before naming the grade,
then the anti-look "NOT orange-and-teal, NOT the Mexico yellow filter", per §7.2.

## Rules that exist because of this

- **HARD — A Short Movie rule and a lakorn rule never cross without the CEO's yes.** **Why hard:** scope —
  the CEO's ruling of 2026-10-03 (§0); the two formats are judged by different viewers, and a mixed rule
  silently changes both.
- **One camera move per shot** (advice; vendor-stated by Runway, measured in-house as rule R17, L2).
- **Lock the look in the prompt, never plan to fix it in the grade** (advice; RD1, GH1).
- **Describe light geometry, not pattern names, until an A/B proves the names work** (advice; §1.2).

## Org rules that apply here

Any paid generation: the exact $ first and the CEO's OK (`ALL_Rules_Approvals`). A $0 mockup before paid
image generation (memory feedback_mockup_before_image_gen).

## Sources

| ID | Source | Date |
|---|---|---|
| SB1–SB9 | studiobinder.com/blog: types-of-camera-shots-sizes-in-film, types-of-camera-shot-angles-in-film, different-types-of-camera-movements-in-film, film-lighting-techniques, lighting-ratios, what-is-continuity-editing-in-film, film-coverage, focal-length-camera-lenses-explained, rules-of-shot-composition-in-film | 2020–2025 |
| MC | maccam.tv/blogs/lighting-guides/the-7-lighting-patterns-every-filmmaker-needs-to-know | undated |
| LP | slrlounge.com, photoworkout.com, fstoppers (lighting patterns, search summary) | — |
| LN | indepthcine.com/videos/focal-length; Medium (search summary) | — |
| RD1 | rogerdeakins.com/forums/topic/about-low-key-lighting/ (Deakins) | 2024-02-15 |
| RD2 | rogerdeakins.com/forums/topic/a-soft-warm-light-source-with-strong-falloff/ (David Mullen ASC) | 2026-05-28 |
| M5C | Mascelli, *The Five C's of Cinematography* (1965), secondary summaries | — |
| ASC1 | theasc.com/article/darius-khondji-cinematic-rhythms/ | 2023-05-15 |
| ASC2 | theasc.com/post/the-film-book/visit-with-darius-khondji-1-dimming-colors-direction/ | 2019-02-11 |
| NFS | nofilmschool.com/iconic-film-color-grades | undated |
| AM, FC, WKW, TR | Amélie, Fight Club, Doyle, Mexican-filter pages (secondary) | — |
| WK-CT, WK-GH, WK-MC, WK-DA, WK-HR, DFN | Wikipedia: Color temperature, Golden hour, Match cut, Dutch angle, Headroom, Day for night | read 2026-10-03 |
| G2 | cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 | 2025-10-16 |
| RW1, RW2 | runway.com/resources/ai-video-prompting-guide; help.runwayml.com Gen-4 guide + camera terms | 2025-11-04 |
| KL1, KL2 | kling.ai/blog/kling-ai-prompt-guide; prompt-architects.com Kling camera control | 2026-08-07, 2026-08-27 |
| WAN1 | alibabacloud.com/help/en/model-studio/text-to-video-prompt | updated 2026-09-28 |
| WAN2 | github.com/Wan-Video/Wan2.1/issues/429 | 2025-06-04 |
| HF1 | higgsfield.ai/blog/seedance-2-5-prompting-guide | undated |
| VB | arxiv.org/html/2503.21755 (VBench-2.0) | v2 2025-08-20 |
| AVB | aivideobootcamp.com/blog/ai-video-tours-real-estate-kling-veo-seedance/ | 2026-04-29 |
| GG | glbgpt.com/hub/ai-video-prompt-adherence-comparison | 2026-09-29 |
| PA | prompt-architects.com Veo/Kling cinematic camera prompts (search summary) | 2026 |
| MO | morphic.com/ai-glossary/focal-length | undated |
| GH1 | github.com/jnMetaCode/ai-shortfilm-prompts (450★; micro-drama template excluded) | pushed 2026-09-28 |
| GH2 | github.com/Rylaispirit/cinematic-video-prompt-skill (137★) | pushed 2026-09-27 |
| L1, L2 | Wikis/research/2026-09-03-seedance-prompt-structure.md; docs/research/2026-09-04-multi-character-action-control.md | 2026-09-03/04 |

**Gaps (2026-10-03):** Reddit and X were unreachable, so no first-hand community threads; the official
BytePlus Seedance 2.5 and Vertex Veo pages rendered empty; Blain Brown's *Cinematography: Theory and
Practice* was not reachable; GitHub repos GH3–GH7 (listed in the research file) were catalogued by stars
only; no engine was A/B-tested on lighting-pattern names.

## Field notes
