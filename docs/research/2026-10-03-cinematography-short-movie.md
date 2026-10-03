# Cinematography for AI short films: lighting and camera

**Compiled** 2026-10-03 for the MoonieX CTO. **Scope:** cinematic short-film craft only. Lakorn, soap and
vertical short-drama (短剧 / micro-drama) material is excluded. One GitHub source (GH1) ships a
`micro-drama.md` template, and it was not used.
**Method:** I read local org research and skills first, then made 25 WebSearch calls (the cap) plus direct
WebFetch and `gh api` reads. Reddit and X could not be reached, as the 2026-09-03 sweep also found (L1). Every
line carries a source tag that resolves in §9.
**Tags:** `[unverified]` means only a search-engine summary or my own reading supports it, with no
primary page read. `[secondary]` means a blog that reports someone else's work. `[suggested]` marks
prompt wording I derived and no engine has tested. The org's measured engine facts are in §8A.

---

## 1. Lighting

### 1.1 The building blocks

| Setup | Look | Story / emotional use | Prompt words | Src |
|---|---|---|---|---|
| **Three-point** | Key, fill and back light around the subject at about 60° each. Shapes the face and separates it from the background | The neutral, controlled baseline. Amélie is cited as an example | "three-point lighting, soft key camera-left, gentle fill, thin backlight" [suggested] | SB4 |
| **Key light** | The brightest light on the subject | Guides the eye and sets the primary direction | State the direction and the source: "hard shaft of cold daylight through the half-open rear ramp" | SB4, HF1 |
| **Fill** | Lifts the shadows while they "still plainly" read | Its level relative to the key sets the mood (see ratios, 1.3) | "cool pale blue skylight fill from above" | SB4, HF1 |
| **Back / rim / kicker** | An edge of light from behind, often from above. "Rim light is a separation tool, not a key light strategy" | Separation; an angelic or mysterious read | Wan official keywords: `Backlight`, `Rim Light`. Also "neon rim light" | SB4, MC, WAN1 |
| **High-key** | Strong key plus generous fill, "almost no shadow" | Cheerful, open, safe | "bright high-key lighting, minimal shadows" [suggested] | SB4 |
| **Low-key** | Little or no fill, high contrast | "Dramatic, suspicious, or even scary" | Wan official: `High contrast`, `Side light` | SB4, WAN1 |
| **Hard light** | Small or undiffused source (bare sun) with crisp shadows | Drama, noir. Blade Runner is cited | Wan official: `Hard light`. "harsh noon sun" | SB4, WAN1 |
| **Soft light** | Large or diffused source with gentle shadows | Flattering, romantic, gentle | Wan official: `Soft light`. Veo example: "Soft morning light" | SB4, WAN1, G2 |
| **Motivated** | Light that seems to come from a logical source in the scene. Jesse James uses lanterns, Moonlight uses overhead bulbs | Invisible artifice. Deakins: unmotivated light "always takes me out of the movie" | Name the source *in* the scene: "lit only by the bedside lamp" [suggested] | SB4 |
| **Practicals** | Lamps and fixtures that appear in frame and are modified to light the scene. Moonlight's diner swapped bulbs | Realism and longer takes. Lets the set light itself | "warm tungsten practicals", "harsh fluorescent overhead lights" (Veo example) | SB4, G2 |
| **Available / natural** | Existing light shaped with bounce boards and flags | Authentic and cheap. The Revenant used magic hour | "natural window light" [suggested] | SB4 |
| **Bounce / book light** | Source → bounce → through silk, which gives a big soft source | Soft key with control | (forum member advice; Deakins did not post in that thread) | RD2 |
| **Negative fill** | Black flag or duvetyne on the shadow side to *remove* light | Adds contrast and shape without adding a light | "deep shadow side, no fill" [suggested] | RD2 |
| **Silhouette** | Key directly behind the subject (180°). The subject becomes a shape | Anonymity, withheld identity, a reveal | Wan official: `Silhouette` | MC, WAN1 |
| **Top / bottom light** | Light from overhead, or from below | Top: interrogation or isolation. Bottom: uncanny, horror [unverified] | Wan official: `Top Light`, `Bottom Light` | WAN1 (aesthetic list via search summary) |

### 1.2 Portrait patterns (key position decides the shadow)

| Pattern | Key position | Shadow signature | Mood | Src |
|---|---|---|---|---|
| **Flat** | Under 30° from the camera axis, head height | No face shadows | Clean, clinical (news, corporate) | MC |
| **Loop** | About 25–50° to the side (MC says about 45°), slightly above eye | Small nose shadow loops toward the mouth corner | Natural, flattering, "mimics how natural window light falls" | LP, MC |
| **Rembrandt** | 45–60° to the side (MC: about 60° horizontal, about 45° up) | Inverted triangle of light on the shadow-side cheek | Drama, gravitas. "Lines, texture, and bone structure are revealed" | LP, MC |
| **Split** | 90° to the side, face height | Half the face lit, half dark | "Feels directed". Villains, antiheroes, moral ambiguity | LP, MC |
| **Butterfly / Paramount** | In front and above, about 45° down, on the camera axis | Symmetric shadow under the nose | Glamour, the Golden-Age Hollywood look. Clamshell adds a bounce below | LP, MC |
| **Rim** | About 120° behind the subject | Only the edges lit | Separation, mystery | MC |
| **Broad / short** | Key lights the side of the face turned toward camera (broad) or away from it (short) | Broad widens the face, short slims and dramatises it | [unverified: standard photo teaching, not read in this sweep] | — |

### 1.3 Contrast ratios (key + fill : fill)

| Ratio | Stops difference | Look | Use | Src |
|---|---|---|---|---|
| 1:1 | 0 | Flat, no modelling | Sitcom, corporate | SB5 |
| 2:1 | 1 | Moderate contrast | Balanced realism and drama, general drama | SB5 |
| 4:1 | 2 | Strong shadows | Dramatic scenes, fashion | SB5 |
| 8:1 | 3 | "Highly dramatic and stylized" | Noir, horror, B&W | SB5 |

Physics a prompt can borrow, from David Mullen ASC on the Deakins forum: softness depends on "source size relative
to subject". Fall-off is steeper the *closer* a source is (inverse square), so a "large soft source close to the face"
gives strong fall-off into darkness (RD2). Deakins on a low-key thread: "Make the decision when you shoot not in post" (RD1).
For AI this means putting the look in the prompt and not planning to grade it in later (GH1 cases: AI footage has "low color
bitrate", so grading banding appears fast).

### 1.4 Colour temperature and time of day

| Source | Kelvin | Src |
|---|---|---|
| Match flame / low-pressure sodium streetlight | ~1,700 K (sodium is near-monochrome yellow) | WK-CT |
| Candle, sunrise/sunset | ~1,850 K | WK-CT |
| Household incandescent | ~2,400 K | WK-CT |
| Studio tungsten / photoflood (tungsten film balance) | 3,200 K | WK-CT |
| Golden-hour sun | ~3,500 K | WK-GH |
| Daylight film balance / midday sun | 5,500–5,600 K | WK-CT, WK-GH |
| Overcast | ~6,500 K | WK-CT |

- **Golden hour** is roughly the hour after sunrise or before sunset. The sun sits at about 10–12° altitude (LA).
  The light is soft, warm and low-contrast with long shadows. *Days of Heaven* was shot "almost entirely during the
  golden hour" (WK-GH). Engine words: "golden hour" (KL1), "warm golden hour side-lighting" (Wan sites, secondary).
- **Blue hour** comes before the golden hour at dawn and after it at dusk. Residual light is "predominantly blue",
  with no sharp shadows (WK-GH).
- **Mixed colour temperature** is a stylistic tool. Khondji dims tungsten to amber against a "very blue" exterior (ASC2).
  [suggested] prompt: "warm amber tungsten interior, cold blue dusk through the window".
- **Day-for-night**: underexpose 2–3 stops and backlight with the sun so it reads as moonlight rim. Keep the bright sky
  out of frame, and shoot at dusk so practicals are on. *Mad Max: Fury Road* did the opposite: it overexposed on digital,
  then darkened and graded blue in post to keep shadow detail (DFN). AI wording [suggested]: "moonlit night, cold blue
  backlight rimming shoulders, dark sky, no daylight sky".

### 1.5 Brown's "goals of good lighting"
Blain Brown, *Cinematography: Theory and Practice*, has a section titled "The Goals of Good Lighting" (BB, search
summary). The list itself (full range of tones, colour control, shape, separation, depth, texture, mood and tone,
exposure) is **[unverified]**: the book pages were unreachable (O'Reilly and Blinkist returned 403).

---

## 2. Shot sizes

| Size | Framing | Story use | Engine vocabulary seen | Src |
|---|---|---|---|---|
| Establishing | Shows the location, no fixed size | Tone and context | Veo: "aerial view"; Kling: "establishing wide shot" | SB1, G2, KL1 |
| **EWS** extreme wide | Subject small in the location | Location dominates; relation of person to world, isolation | Wan official: `Extreme full shot`; Kling "wide shot" | SB1, WAN1, KL1 |
| **WS / LS** wide/long | Whole subject plus surroundings | Character vs surroundings, narrative distance | Veo "Wide shot"; Wan `Wide-angle` | SB1, G2, WAN1 |
| **FS** full | Head to toe, some scenery | Physical presence, blocking of several people | Kling "full body shot" | SB1, KL1 |
| **MWS** medium wide | Knees up | Between full and medium | — | SB1 |
| **Cowboy** | Mid-thigh up | Western holster; action and emotion together | — | SB1 |
| **MS** medium | Waist up | Dialogue "buffer", balances subject and setting | Veo "Medium shot" | SB1, G2 |
| **MCU** | Chest up | Body language plus face | Kling "medium close-up"; Wan example tag | SB1, KL1 |
| **CU** | Face fills frame | Emotion and reaction | Veo "Close-up"; Wan `Close-up` | SB1, G2, WAN1 |
| **ECU** | Eyes, lips, a trigger | Tiny details, intensity | Veo "Extreme close-up" | SB1, G2 |
| Two-shot | Two subjects in frame | Relationship in one frame | Veo "Two-shot" | G2 |
| Insert | An object detail | Plot information | [unverified, standard] | — |

**AI note:** shot-size words are soft. Seedance 2.0 Mini was asked for a face "filling sixty percent of frame
height" and pulled back to about 45% (K1, measured 2026-09-10). Higgsfield's own guide replaces size words
with field of view and distance: "84° diagonal field of view, classic wide", "29° … short telephoto portrait",
"camera 4 meters from the face", "lens 40 centimeters above the wet asphalt" (HF1). Untested in-house.

---

## 3. Camera angles

| Angle | Psychological effect | Example / note | Src |
|---|---|---|---|
| **Eye level** | Neutral, "breaks down boundaries"; equality and empathy | *Game of Thrones*; *Nightcrawler* eye-level CUs | SB2, SB9 |
| **Shoulder level** | "Much more standard than eye level", the default cinematic height | *Black Panther* | SB2 |
| **Low angle** | Power, "superiority", or fear of the subject | *The Matrix*; Welles, Anderson | SB2 |
| **High angle** | "Inferiority", vulnerable, powerless | *Avengers* | SB2 |
| **Overhead / bird's-eye** | "Neutral or sometimes divine point of view"; vulnerability, surveillance | — | SB2, SB3 |
| **Aerial** | Establishes a large expanse | *Black Hawk Down* | SB2 |
| **Hip / cowboy level** | Action at the waist (guns, pockets) | *Punch-Drunk Love* | SB2 |
| **Knee level** | Emphasises a character's superiority | *Home Alone* | SB2 |
| **Ground level / worm's-eye** | Features without faces; engages the viewer | *Burn After Reading* | SB2 |
| **Dutch / canted** | "Unease or disorientation"; madness, tension | *The Third Man* (Wyler sent Reed a spirit level). Overuse warning: *Battlefield Earth* ("learned … that directors sometimes tilt their cameras, but he has not learned why", Ebert) | SB2, WK-DA |
| **Over-the-shoulder (OTS)** | Establishes spatial relation in dialogue | Wan official `Over-the-shoulder shot`. GH1: "long-lens over-the-shoulder, focus on the far face, foreground shoulder soft" | M5C, WAN1, GH1 |
| **POV** | Identification with the character | Veo vocabulary "POV shot". One weak source says vague "POV camera" wording drew Veo rejections [weak] | M5C, G2, L3 (yapper) |

Mascelli groups angles as **objective / subjective / point-of-view**, and treats subject size, subject angle and camera
height as separate choices (M5C, secondary summary).

---

## 4. Camera movement

| Move | What it is | When to use it | AI note | Src |
|---|---|---|---|---|
| **Static / locked-off** | Tripod, the frame never moves | Dialogue, performance, dread by stillness. *Wolf of Wall Street* improvisation | Hardest move for models; see §8 | SB3, RW1 |
| **Pan** | Horizontal rotation | Reveal, follow, energy; "often motivated by a character's actions" | Kling word list: "pan left / pan right" | SB3, KL2 |
| **Tilt** | Vertical rotation | Scale, awe. *Jurassic Park* tilt-up to the dinosaur | Kling: "tilt up / tilt down" | SB3, KL2 |
| **Whip / swish pan** | Very fast pan, motion-blur transition | Energy, linking characters. *La La Land* | Runway lists it | SB3, RW1 |
| **Push-in (dolly in)** | Camera moves closer | Tension, intimacy, an inner decision. *The Godfather* (Michael's power move) | Reported as "the most reliable Veo move" | SB3, AVB |
| **Pull-out (dolly out)** | Camera moves away | Isolation, loneliness, reveal. *The Shining* | Kling: "pull back" | SB3, KL2 |
| **Zoom** | Changes focal length, the camera stays put | Unease; "can feel artificial". *Full Metal Jacket* | Wan official I2V wording uses "camera pushes in / pulls out" not zoom | SB3, WAN1 |
| **Dolly zoom (Vertigo)** | Push in while zooming out, or the reverse | Surreal, psychological shock. *Fellowship of the Ring* | Vendor and SEO claims only that models do it well [unverified] | SB3 |
| **Truck** | Lateral camera move (vs a pan, which rotates) | Parallax, walking beside a subject | Org measured: "lateral track stitches easier than 3-D moves" (L1 §5.10) | MV, L1 |
| **Pedestal** | Camera moves straight up or down | Reveal height | Kling defines it ("like a drone taking off") [secondary] | MV, KL3 |
| **Crane / boom / jib** | Large vertical or sweeping move | Grandeur, opening and closing reveals | Veo "Crane shot", "high-angle crane shot" | SB3, G2 |
| **Tracking** | The camera travels with the action | Immersion. *1917* (Steadicam, single-take illusion) | Veo, Kling, Wan all list "tracking shot" | SB3, G2, KL1, WAN1 |
| **Arc / orbit** | The camera circles the subject | Builds tension. *The Dark Knight* Joker arc "create[s] uneasiness" | Veo "180-degree arc shot"; Wan "Orbiting camera movement"; Kling "orbit slowly" | SB3, G2, WAN1, KL2 |
| **Roll** | Rotation about the lens axis | Instability. *Black Panther* throne | Kling camera-control axis | SB3, KL2 |
| **Handheld** | The operator's body movement shows | Documentary subjectivity, chaos. *The Big Short* | Runway example: "Handheld camera … Natural camera shake". GH1: "extremely subtle, breath-like camera float" | SB3, RW2, GH1 |
| **Steadicam / gimbal** | Stabilised walk-and-talk | Smooth following through space. *Rocky* steps, *The Shining* low mode | "steadicam glide" [secondary list] | WK-SC |
| **Drone / aerial / FPV** | Flying camera | Scale; FPV = kinetic | Wan official "Drone shot", "Fast fly-through" | WAN1 |
| **Rack focus** | Focus shifts between depth planes | Hands the viewer a clue in one beat. *Casino Royale* | GH1 suspense SOP phrasing | SB9, GH1 |

Genre defaults from GH1's cinema SOP (450★, practitioner, untested by us):
- **Horror**: an extremely slow creep-in, or a locked-off frame with off-screen sound.
- **Action**: tracking sprint, or a low-angle hero rise.
- **Romance**: a breath-float two-shot, or a pull-back to leave the couple.
- **Suspense**: frame-within-frame, a slow reverse pull reveal, or a high-angle surveillance frame.
- **Epic**: a reveal crane-up, or a locked-off extreme wide with the subject in the lower fifth.
- GH1's advice: keep one lens and one grade across a sequence.

---

## 5. Lens and depth of field

| Class | mm (35 mm-equivalent) | Effect | Story use | Src |
|---|---|---|---|---|
| Ultra-wide / fisheye | under 23 mm | Strong distortion, near-180° view | Unease, grotesque, enriched space. *The Favourite* | SB8 |
| Wide | 23–35 mm | Exaggerated depth; near things huge, background "further away"; movement toward the lens exaggerated | Immersion, energy, intimacy-with-environment | SB8 |
| Normal | 35–55 mm (50 mm "clean, honest") | Close to how the eye sees | Neutral observation | SB8, LN |
| Telephoto | 55 mm and up (85/135 portrait, 2000 mm in *Tinker Tailor*) | Background looks compressed toward the subject, shallow DoF | Isolation, voyeurism, surveillance; exaggerates lateral speed | SB8 |

- **Compression is contested between sources.** Search-cited teaching material (In Depth Cine, Medium) says the look comes
  from **camera distance**: a long lens forces the camera back, so subject and background sit relatively closer (LN).
  The fetch summary of SB8 claimed the opposite. Physics favours distance; focal length only decides the crop. In a
  prompt, say both: "shot from far away on a long telephoto lens, background compressed close behind her"
  [suggested].
- **Depth of field** depends on aperture, focal length, subject distance and sensor size (SB8). Longer lenses look
  shallower at the same framing (LN).
  - Deep focus or deep-space staging: *Citizen Kane*, where the far-away child foreshadows separation (SB9).
  - Shallow focus or bokeh isolates the subject. *Nightcrawler* keeps others soft to show alienation (SB9).
- Engine vocabulary:
  - Veo 3.1: "Shallow depth of field", "Very shallow depth of field", "Deep focus", "Wide-angle lens", "Macro lens",
    "Soft focus" (G2).
  - Wan official: `Long-focus lens`, `Short-focus lens`, `Ultra-wide-angle fisheye` (WAN1).
- **mm numbers in prompts.**
  - Morphic: "combining the numerical specification with a description of the characteristic visual quality it produces
    tends to yield more accurate results than using the number alone", e.g. "85mm portrait lens, flattering facial
    compression" (MO).
  - GH1 goes further and names real bodies and lenses: "simulated IMAX film camera, Panavision C-series lens, 35mm
    focal, f/4 aperture". Its stated reason is "AI training data binds those exact strings to real movie aesthetics".
    That reason is the repo's claim, **[unverified]** mechanism.
  - HF1 locks lenses per segment ("LENS LOCK SEGMENT 1: 84° … SEGMENT 2: 29°") and asks for "anamorphic look
    throughout, oval out-of-focus highlights".
- **Depth words change size.** In-house measurement: "the nearest thing to the lens" rendered a "small" mark 4–5×
  too big. Anchor size to an object in the same frame instead (K1, K2 rule 5).

---

## 6. Composition and continuity grammar

**Composition**
- **Rule of thirds**: key elements on the grid lines. Off-centre placement shows the character's relation to
  the world; Lou in *Nightcrawler* is framed as alienated (SB9). Kling vocabulary: "centered", "rule of thirds",
  "off center" (KL1). Wan: `Center / Left-heavy / Right-heavy / Balanced composition` (WAN1).
- **Headroom** is the space above the head. Too much makes the subject look small or isolated; too little makes the
  frame claustrophobic (WK-HR).
- **Lead room** is space in the direction of movement. **Look / nose room** is space in front of the face, and implies
  someone just off-screen (WK-HR, search summary). Short-siding, putting the space behind the face, is the deliberate
  break that signals unease [unverified].
- **Leading lines** guide the eye to the key element. *Nightcrawler* uses diagonals from Lou's feet to the police cars (SB9).
- **Symmetry and balance**: centred frames suggest control or dread (*Full Metal Jacket*, *2001*) (SB9).
- **Deep-space staging, frame-within-frame and negative space** are listed in GH2's 80-plus composition rules. Using frame
  within frame for suspense is GH1's SOP.
- **Blocking**: actor movement steers the viewer's eye (SB9).

**Continuity (Mascelli's "Continuity" and "Cutting" Cs, M5C)**
- **180° rule**: keep the camera on one side of the axis between subjects, so each always faces the same screen
  direction (SB6). Kubrick broke it deliberately in *The Shining* to disorient (SB6).
- **30° rule**: a cut to the same subject needs at least 30° of angle change (or a clear size change), or it reads as
  a jump cut (SB6).
- **Eyeline match**: the person on the left looks camera-right and the person on the right looks camera-left. It can
  also match vertically for height (SB6, search summary of SB eyeline page).
- **Screen direction**: a subject who exits frame-right enters the next shot frame-left and keeps moving the same
  way. GH1 reports that two AI clips "read as two separate videos" until shots were designed with matching exit and
  entry edges ("motion-direction continuity, not matching static frames").
- **Shot / reverse shot**: alternate opposite angles with reaction shots and keep the eyelines matched (SB-search,
  SB7). Veo 3.1 accepts "Reverse shot" as a term (G2).
- **Coverage**: establishing shot, then master, mediums, close-ups, OTS and shot/reverse shot. SB7's "V strategy" goes
  from widest to tightest.
- **Match on action**: cut during the movement for invisible editing. *Fury Road* is the example (SB6).
- **Match cut / graphic match**: matched shape or motion across a cut. Examples: the *2001* bone to satellite, the
  *Psycho* drain to eye, the *North by Northwest* cliff to train bunk, and *Citizen Kane*'s window held in the same
  frame position (WK-MC).
- **AI caveat**: models score about 0.5 on spatial relations and confuse left and right (L2). Seedance needs geography
  stated outright: "Left-right geography holds through all cuts", and screen direction "requires explicit statement to
  hold" (HF1).

---

## 7. Colour and grading for mood

### 7.1 General palettes (NFS unless noted)
- **Sepia vs Technicolor**: *The Wizard of Oz* separates reality from fantasy.
- **Underexposed amber**: *The Godfather* (Gordon Willis) for weight and nostalgia.
- **Bleach-bypass bronze with crushed blacks**: *300*, "like an ancient fresco".
- **Hyper-saturated orange and teal**: *Fury Road* (John Seale) for relentless energy.
- **Blue and neon purple**: *Moonlight* (James Laxton) for intimacy and vulnerability.
- **Selective colour on near-B&W**: *Sin City*.

### 7.2 Stylised yellow-green and surreal colour worlds

| Film / DP | Look | How it was made | Story purpose | Src |
|---|---|---|---|---|
| *Delicatessen* (1991), Darius Khondji | Gold/yellow-sepia against "very strong, inky blacks". Jeunet: "We couldn't have possibly imagined a film so _gold_!" | Khondji chose gold over the planned blue/dark green. **Bleach bypass**: skipping the bleach in printing leaves silver on the positive, which raises contrast. Agfa stock and telecine refinement [secondary] | Absurd post-apocalyptic fairy tale | ASC1, search summary |
| Khondji's method (general) | Gold made by *adding green*: "you have to add green" | "1/8 or 1/4 green gels with tracing paper on tungsten lights at 3200 or 3400 K … a little bit of blue … at a very low level". Dims tungsten bulbs to amber (≤50%) against blue exteriors | Green is his "second friend" | ASC2 |
| *The City of Lost Children* (1995), Khondji | Pitch blacks vs Caro's green | A variation of the silver-retention process | Dream-nightmare world | ASC1 |
| *Se7en* (1995), Khondji | "Dark, darker and darker still", with detail in the blacks | Deluxe **CCE** silver retention, "more radical bleach-bypass" | Decay, moral rot | ASC1 |
| *Amélie* (2001), Bruno Delbonnel | Lime greens, mustard yellows, saturated reds | Painter Juarez Machado as reference (NFS). Shot on 35 mm, then an early digital intermediate with hue-by-hue grading: blues/cyans desaturated and pushed toward green, reds boosted, yellows kept [secondary]. Colourist Didier Le Fouest on Lustre, plus an 81EF warming filter on some exteriors [unverified, search summary] | Whimsy; "softened the harshness of the urban environment" | NFS, AM |
| *The Matrix* (1999), Bill Pope | "Sickly monochromatic green" inside the simulation | Graded to evoke old monitors | "Nothing is authentic" | NFS |
| *Fight Club* (1999), Jeff Cronenweth | Desaturated, faded scenes tinted green; shiny skin | Based on the green fluorescent light of a 7-Eleven at night | Soul-sucking corporate world vs Tyler's | FC [secondary] |
| *Traffic* (2000), Soderbergh as "Peter Andrews" | Mexico storyline: hot yellow, grainy, contrasty | Tobacco filter, 45° shutter, Ektachrome step. This became the "Mexican filter" **trope** to avoid | Story-line colour coding | TR [secondary] |
| *Fallen Angels* / *Happy Together*, Christopher Doyle | Dirty greens and yellows under neon; dark yellowish tones | Neon and fluorescent practicals, complementary pairs (yellow/purple, green/red). Lower-contrast Kodak stocks on *In the Mood for Love*; Doyle says colour "emerge[s] from an accumulation of elements" | Urban loneliness, dream-time | WKW [secondary] |
| Sodium-vapour night | Near-monochrome orange-yellow | Low-pressure sodium at ~1,700 K | Industrial, sickly night | WK-CT |

### 7.3 Turning a colour world into an AI prompt
1. **Say where the colour comes from in the scene, then name the grade.** This mirrors how Khondji and Doyle worked:
   colour lives in the light sources first (ASC2, WKW). [suggested]: "overhead green fluorescent tubes, amber tungsten
   practicals dimmed low, inky crushed blacks, bleach-bypass contrast, lime and mustard palette, blues desaturated
   toward teal".
2. **Use proportions and anti-looks**, as HF1 does: "60 percent cold steel-blue … 30 percent matte black … 10 percent
   warm focal pop" and "NOT golden-hour Hollywood, NOT teal-and-orange blockbuster" (HF1).
   - Official Wan tone words: `Warm tones`, `Cool tones`, `Low/High saturation`, `High/Low contrast` (WAN1).
   - Secondary Wan sites add "teal-and-orange", "bleach-bypass", "kodak portra" (search summary).
3. **Lock the grade in the prompt, not in post.** AI footage has low colour bitrate and bands when pushed (GH1
   cases). Deakins agrees for live action: "Make the decision when you shoot not in post" (RD1).
4. **Paste one grade block verbatim into every shot of a film.** This is K2 §2 item 7, and GH1 says the same:
   "color drift wrecks the cut".

---

## 8. AI-video specifics

### 8A. Already in org skills (measured in-house, keep)
1. **Tech header first, with a camera lock** ("ONE CONTINUOUS TAKE, NO CUTS"), and state what the camera is NOT
   doing (no cut, no zoom). "Without the lock, Seedance invents cuts." (K2 §2.1, K3 rule 4)
2. **Each beat = shot type → subject + physical action → camera → atmosphere**, with 3–4 beats at most per clip
   (K2 §2.5). The order matches the official Seedance 2.0 per-shot fields (L1).
3. **Operator vocabulary only**: dolly, push-in, locked-off, whip pan, lateral track. Never "the camera moves" (K1
   §Camera and cuts, from Higgsfield's guide). "Cinematic" is not a camera move (L1, official 2.0/2.5).
4. **One camera move per shot.** Vendor-stated for 2.0, "cheap, no downside" (L2 R17). The bad example compounds two
   moves: "slow dolly-in … while craning down and pushing past the table".
5. **Front-load the beats and put optics, grade, lens and film stock at the END.** They are "the cheapest content to
   lose". VGIF-Score across 14 models including Seedance 2.0 found constraints in the first 20% of a prompt followed
   67.9% of the time, against 10.1% in the last 20% (L2 R4). Caveat: that is an unvalidated proxy for long prompts (L2).
6. **A cut cannot carry a change.** "Same frame, the clock jumps" renders as no cut at all. A cut needs a visible
   change of framing or subject (K1, S2R-JC 2026-09-09).
7. **A video reference beats prose for camera.** A two-camera Blender previz as `@Video 1` fixed "locked camera"
   where prose did not (S3a t2). Describe the video's camera in words too, end with "No other camera movement exists
   in this shot.", and declare the reference camera-only so its grey look does not bleed in (K1). Multi-cut
   references are averaged, not obeyed, so use one continuous camera per reference (L2).
8. **Reference images carry lighting.** Subject-to-video models "directly transfer the pose, lighting, and
   contours from the reference image" (L2). Give each reference a job and an exclusion, e.g. "Do not take lighting from
   @x" (L1, fal pattern).
9. **Size and gaze**: depth words inflate size; anchor size to an object in frame; give face direction in camera terms
   ("facing the camera", "their backs to us") (K1, K2 rule 5).
10. **Never mix models inside one scene.** Light, colour and bitrate differ. 2.0 Mini had 16–18% less saturation and
    ignored the framing spec. Locations from two image models "will not cut together" (K1).
11. **Seedance 2.0 reads shot numbers, not timestamps. 2.5 reads integer-second timestamps** (official, L1), so
    match the syntax to the engine version.
12. **Motion measurement only works on a locked camera.** A tracking shot inflates `shot-motion.sh`'s drift reading (K1).

### 8B. What vendors officially recommend

| Engine | Official prompt order | Camera / lighting notes | Src |
|---|---|---|---|
| **Veo 3.1** | `[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]` | Terms: dolly, tracking, crane, aerial, slow pan, POV, 180-degree arc, wide/medium/CU/ECU, low angle, two-shot, reverse shot, shallow/deep focus, macro. Multi-shot as `[00:00-00:02] …` timestamp blocks. Exclusions written as positive description ("a desolate landscape with no buildings or roads") | G2 (2025-10-16) |
| **Runway** (Gen-4 / 4.5) | `[Camera Movement] + [Scene] + [Action] + [Details]`; the help center gives "The camera [motion] as the subject [action]." | "Choose one primary movement per prompt." "One action per prompt." Negative wording backfires: "When you write 'No camera shake,' the AI might focus on the word 'shake'". Use "Smooth, stable camera movement" | RW1 (2025-11-04), RW2 |
| **Kling** (3.0) | subject, action, setting, camera language, lighting, mood | Nine "useful camera words": push in, pull back, pan left, pan right, tilt up, tilt down, track forward, orbit slowly, static camera. The camera-control panel has 6 axes (horizontal, vertical, zoom, pan, tilt, roll) plus 4 "Master Shots". That panel predates 3.0 and has not been republished since | KL1 (2026-08-07), KL2 |
| **Wan** (2.x–3.0) | T2V: Entity + Scene + Motion + Aesthetic control + Stylization. **I2V: Motion + Camera movement only** (the image already defines subject, scene and style). Multi-shot (2.6+): Overall description + Shot number + Timestamp + Shot content | Official keyword lists for light source, lighting type, time, shot size, composition, lens, angle and movement (`Fixed camera`, `Camera pushes in`, `Orbiting camera movement`, …). Rapid scene changes inside one clip fail: "cuts occur between clips, not within". For a single shot, write "Generate single shot." | WAN1 (updated 2026-09-28) |
| **Seedance 2.5** | 4 blocks: references → one-sentence summary "Subject + Location + Event + Genre/Style + Camera movement" → timed plot → constants | Official 2.0 guide: "strong understanding of camera movement terms". No `negative_prompt` field in the API. Higgsfield's guide uses FOV degrees, metres, lens locks, "HARD CUT", explicit geography locks | L1, HF1 |

### 8C. What the community and measurements found models do and do not follow

**Static shots are the least reliable instruction.**
- Runway: "Video models are designed to create immersive, high-fidelity motion, which can make achieving static
  shots challenging." The fix is to describe the motion inside the scene, plus "The camera is entirely motionless for
  the duration of the scene, with movement only occurring from the subject." (RW2)
- Wan 2.1, GitHub issue #429: "Static camera", "Fixed camera" and "Steady camera" were "all can not 100% be
  successful" (WAN2).
- If camera behaviour is left unspecified, models default to "subtle drift, sway, or a slow push-in" (PA, secondary).
- The org's fix is the camera lock in the header plus a previz video reference (8A.1, 8A.7).

**Measured camera-motion adherence is low and uneven.**
- VBench-2.0 (v2, 2025-08-20) tested pan left/right, tilt up/down, zoom in/out, dolly forward, orbit and oblique
  aerial (VB):
  - Kling 1.6: 61.73%
  - HunyuanVideo: 33.95%
  - CogVideoX-1.5: 33.33%
  - Sora: 27.16%
- These are older models. No 2026 engine was measured there.

**Some moves are easier than others.**
- A real-estate test (8 moves on one photo, about $48 of API spend) found (AVB):
  - Veo 3.1: push-in is "the most reliable Veo move". Subject-targeted orbit works. "Broad spatial pans (rotate to
    reveal the next room)" are a weakness.
  - Kling 3.0: best with "deliberate, slow movement; aggressive multi-axis paths produce drift".
- Another test of 5 prompts across 6 models, with no numbers published (GG):
  - Wan 3.0 had "the clearest front tracking move".
  - Seedance 2.5 kept the event order.
  - Veo 3.1's event order was "less clear".

**One move per shot, two or three at most when chaining.**
- Runway: "Choose one primary movement per prompt" (RW1). Org rule R17 (L2). GH2 bakes in "one camera movement per
  clip, one main action per clip".
- A secondary source claims more than 2–3 chained moves makes motion "unstable" [unverified].

**Vague style words do nothing.**
- "Cinematic dramatic camera move around the hero" fails.
- "IMAX + Panavision C 35mm. Medium close-up, low-angle 30° from left. Orbit clockwise, very slow, with a 0.1s reactive
  micro-shake." works better (GH1 cases).

**Lucky camera work does not reproduce.** GH1's author reports 20+ rerolls for hard shots and 2–3 for simple ones,
with about 200 video shots for about 40 final clips. "Treat one prompt as a ticket to draw" (GH1).

**Negative phrasing about the camera backfires on some engines.**
- Runway: "no X" can summon X (RW1, GH1).
- Veo: a negative field takes plain nouns, not commands (GH1). The Google blog prefers positive description (G2).
- Seedance has no negative field (L1).
- Org practice: keep negatives few and aimed, never describing the unwanted image (K2 rule 6).

**Lighting words that appear in official engine vocabularies.**
- Wan: Soft/Hard/Side/Top/Bottom/Back/Rim light, Silhouette, High/Low contrast, Daylight, Firelight, Overcast,
  Dawn, Night (WAN1).
- Veo: "harsh fluorescent overhead lights", "single, dramatic spotlight", "lens flare", "cool blue tones" (G2).
- Kling: "golden hour", "cold blue night", "soft haze", "god rays" (KL1).
- Rembrandt, chiaroscuro and practical appear in GH2's 80-plus lighting list, but **no source here tested whether
  pattern names (Rembrandt, butterfly) change the output** [unverified]. A safer form describes the geometry: "key
  from 45° camera-left above eye level, a triangle of light on the shadow cheek" [suggested].

**Image-to-video.** Describe only motion and camera. The image already fixes subject, style and light (WAN1 I2V
formula). The org's reference-job rule covers what to exclude (8A.8).

**Kling naming quirk.** One search summary says Kling's camera-control "pan" is a vertical rotation, i.e. a classic
tilt [unverified, KL3]. Use plain words ("tilt up", "pan left") in text prompts, which match Kling's own word list (KL2).

**Per-engine phrasing (GH1, practitioner).**
- Seedance: concrete moves ("slow push-in" not "dramatic camera").
- Kling: strongest at smooth orbits and follow-tracking. A single banned word rejects the whole prompt.
- Veo: strong at crane and parallax establishing shots.
- Runway: describe only the move you want.

**Wan 2.2 vs 2.1.** Community testing (Bilibili digest on GitHub) says 2.2 14B has "enhanced camera movement and
dynamics" (WAN3).

### 8D. Working synthesis for our prompts [suggested, built on 8A + 8B, not separately A/B-tested]
- Write **one** named move per shot, early, in operator words. Add speed ("very slow") and direction
  ("clockwise", "camera-left").
- **Static**: lock it in the header, put the motion in the subject, and use a previz video reference when it matters.
- **Lighting**: give the source, the direction (degrees or camera-left/right), the quality (hard or soft), and the
  colour/kelvin words, sourced in the scene.
- Put lens and grade in the shared end block (8A.5), worded the same in every shot.
- Use geometry and distance (FOV, metres, "no wider than X") rather than emphasis words.

---

## 9. Sources

| ID | Source (URL or path) | Publisher / repo | Date / stars |
|---|---|---|---|
| L1 | /Users/gob/MoonieXHQ/Agents/Wikis/research/2026-09-03-seedance-prompt-structure.md | MoonieX CTO research (cites BytePlus ModelArk 2607689 / 2222480) | 2026-09-03 |
| L2 | /Users/gob/MoonieXHQ/Agents/Core/docs/research/2026-09-04-multi-character-action-control.md | MoonieX research (VGIF-Score, T2V-CompBench) | 2026-09-03/04 |
| L3 | /Users/gob/MoonieXHQ/Agents/Core/docs/research/2026-09-19-flow-policy-refusals.md (cites yapper.so 2025-07-19) | MoonieX research | 2026-09-19 |
| K1 | /Users/gob/MoonieXHQ/Agents/Core/.claude/skills/CMO_Knowledge_Seedance2.5_Higgsfield/SKILL.md | Org skill | measured 2026-08/09 |
| K2 | /Users/gob/MoonieXHQ/Agents/Core/.claude/skills/CMO_Standard_Film_PromptFormat/SKILL.md | Org skill | 2026-09-25 |
| K3 | /Users/gob/MoonieXHQ/Agents/Core/docs/prompts/absence/PROMPT-STYLE.md | Org evidence file | 2026-08 |
| SB1 | https://www.studiobinder.com/blog/types-of-camera-shots-sizes-in-film/ | StudioBinder (SC Lannom) | 2025-02-24 |
| SB2 | https://www.studiobinder.com/blog/types-of-camera-shot-angles-in-film/ | StudioBinder (SC Lannom) | 2025-01-07 |
| SB3 | https://www.studiobinder.com/blog/different-types-of-camera-movements-in-film/ | StudioBinder (Kyle DeGuzman) | 2025-02-02 |
| SB4 | https://www.studiobinder.com/blog/film-lighting-techniques/ | StudioBinder (AJ Detisch) | 2025-01-13 |
| SB5 | https://www.studiobinder.com/blog/lighting-ratios/ | StudioBinder | 2020-06-13 |
| SB6 | https://www.studiobinder.com/blog/what-is-continuity-editing-in-film/ | StudioBinder (Kyle DeGuzman) | 2021-03-21 |
| SB7 | https://www.studiobinder.com/blog/film-coverage/ | StudioBinder (Brandon Night) | 2024-09-24 |
| SB8 | https://www.studiobinder.com/blog/focal-length-camera-lenses-explained/ | StudioBinder (Nick LaRovere) | 2025-03-05 |
| SB9 | https://www.studiobinder.com/blog/rules-of-shot-composition-in-film/ | StudioBinder (Alyssa Maio) | 2025-01-14 |
| SB-search | https://www.studiobinder.com/blog/what-is-an-eyeline-match/ (search summary only) | StudioBinder | — |
| MC | https://www.maccam.tv/blogs/lighting-guides/the-7-lighting-patterns-every-filmmaker-needs-to-know | MACCAM | undated |
| LP | slrlounge.com/common-key-light-patterns, photoworkout.com/lighting-patterns, fstoppers (search summary) | photo-teaching sites | — |
| LN | indepthcine.com/videos/focal-length; medium.com @abhinavgopal (search summary) | In Depth Cine / Medium | — |
| MV | storyblocks.com/resources/tutorials/7-basic-camera-movements; videomaker.com (search summary) | — | — |
| RD1 | https://www.rogerdeakins.com/forums/topic/about-low-key-lighting/ | Roger Deakins forum (Deakins reply) | 2024-02-15 |
| RD2 | https://www.rogerdeakins.com/forums/topic/a-soft-warm-light-source-with-strong-falloff/ | Deakins forum (David Mullen ASC reply; Deakins absent) | 2026-05-28 |
| M5C | robertcmorton.com/the-5-cs-of-cinematography; aaft.com (search summaries of Mascelli 1965) | secondary | — |
| BB | Blain Brown, *Cinematography: Theory and Practice* 4th ed. (Routledge); O'Reilly/Blinkist returned 403 | book (not read) | — |
| ASC1 | https://theasc.com/article/darius-khondji-cinematic-rhythms/ | American Cinematographer (Max Weinstein) | 2023-05-15 |
| ASC2 | https://theasc.com/post/the-film-book/visit-with-darius-khondji-1-dimming-colors-direction/ | ASC | 2019-02-11 |
| NFS | https://nofilmschool.com/iconic-film-color-grades | No Film School | undated |
| AM | colorculture.org (Amélie analysis), evanerichards.com, yellowbrick.co (search summary) | secondary | — |
| FC | cinephiliabeyond.org (Fight Club), reyfilm.com (search summary) | secondary | — |
| TR | https://en.wikipedia.org/wiki/Mexican_filter ; Traffic (2000 film) (search summary) | Wikipedia | — |
| WKW | wolfcrow.com/understanding-cinematography-christopher-doyle; academia.edu Doyle colour paper (search summary) | secondary | — |
| DFN | https://en.wikipedia.org/wiki/Day_for_night + search summary | Wikipedia | — |
| WK-CT | https://en.wikipedia.org/wiki/Color_temperature | Wikipedia | read 2026-10-03 |
| WK-GH | https://en.wikipedia.org/wiki/Golden_hour_(photography) | Wikipedia | read 2026-10-03 |
| WK-MC | https://en.wikipedia.org/wiki/Match_cut | Wikipedia | read 2026-10-03 |
| WK-DA | https://en.wikipedia.org/wiki/Dutch_angle | Wikipedia | read 2026-10-03 |
| WK-SC | https://en.wikipedia.org/wiki/Steadicam | Wikipedia | read 2026-10-03 |
| WK-HR | https://en.wikipedia.org/wiki/Headroom_(photographic_framing) + lead/look-room search summary | Wikipedia | — |
| G1 | https://deepmind.google/models/veo/prompt-guide/ | Google DeepMind (thin; little camera detail) | undated |
| G2 | https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 | Google Cloud (Davaajav, Chinoy) | 2025-10-16 |
| RW1 | https://runway.com/resources/ai-video-prompting-guide | Runway | 2025-11-04 |
| RW2 | https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide (403 to fetch; quoted via search) and /47313504791059-Camera-Terms-Prompts-Examples | Runway help center | — |
| KL1 | https://kling.ai/blog/kling-ai-prompt-guide | Kling AI | 2026-08-07 |
| KL2 | https://prompt-architects.com/blog/199-motion-and-camera-control-in-kling (cites kling.ai/quickstart/ai-camera-control-guide 2025-11-24; kling.ai/blog/kling-ai-camera-control-video-guide 2026-08-13) | prompt-architects | 2026-08-27 |
| KL3 | Search summary (titanxt.io / glbgpt Kling camera pages) | secondary | [unverified] |
| WAN1 | https://www.alibabacloud.com/help/en/model-studio/text-to-video-prompt | Alibaba Cloud Model Studio (official) | updated 2026-09-28 |
| WAN2 | https://github.com/Wan-Video/Wan2.1/issues/429 | GitHub issue | 2025-06-04 |
| WAN3 | https://github.com/Wan-Video/Wan2.2/issues/20 | GitHub issue (community digest) | 2025-07-29 |
| HF1 | https://higgsfield.ai/blog/seedance-2-5-prompting-guide | Higgsfield | undated |
| VB | https://arxiv.org/html/2503.21755 (VBench-2.0) | arXiv | v2 2025-08-20 |
| AVB | https://aivideobootcamp.com/blog/ai-video-tours-real-estate-kling-veo-seedance/ | AI Video Bootcamp (M. Starcevic Filipovic) | 2026-04-29 |
| GG | https://glbgpt.com/hub/ai-video-prompt-adherence-comparison | GlobalGPT (Chloe Murphy) | 2026-09-29 |
| PA | https://prompt-architects.com/blog/25-30-cinematic-camera-prompts-for-veo3-and-kling (search summary) | prompt-architects | 2026 |
| MO | https://morphic.com/ai-glossary/focal-length | Morphic | undated |
| GH1 | https://github.com/jnMetaCode/ai-shortfilm-prompts (README, cases.md, templates/genre-camera-sop.md; micro-drama template excluded) | jnMetaCode | 450★, pushed 2026-09-28 |
| GH2 | https://github.com/Rylaispirit/cinematic-video-prompt-skill | Rylaispirit | 137★, pushed 2026-09-27 |
| GH3 | https://github.com/ai9app/AI-Cinematic-Prompt-Director | ai9app | 19★, 2026-06-21 |
| GH4 | https://github.com/HuyLe82US/awesome-seedance-prompts | HuyLe82US | 69★, 2026-02-26 |
| GH5 | https://github.com/Anil-matcha/awesome-seedance-2.5-api-prompts | Anil-matcha | 320★, 2026-09-28 |
| GH6 | https://github.com/ZeroLu/awesome-seedance-2.5 | ZeroLu | 126★, 2026-10-02 |
| GH7 | https://github.com/ishandutta2007/veo_prompts | ishandutta2007 | 25★, 2026-10-01 |

**Gaps.**
- Reddit and X were unreachable, so no first-hand r/aivideo threads are included.
- The BytePlus Seedance 2.5 page and the Vertex AI Veo guide are JS-rendered and returned no body. Seedance facts come
  from L1's earlier recovery.
- The Blain Brown text was not reachable.
- No source A/B-tested lighting-pattern names (Rembrandt etc.) on any engine.
- GH3–GH7 were catalogued by star count only; their content was not read.
