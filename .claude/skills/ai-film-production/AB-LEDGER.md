# A/B LEDGER — «Sorry, Sir» prompt fixes, failing prose vs passing prose

Kept per §12 of SKILL.md. Quotes are from git; the clip verdicts are the
CTO's own frame reviews. PENDING entries carry their Prompt A now and get
their Prompt B on the day the fixed take passes.

---

### S2C · Dupe's pacing · takes 1 → 4 · passed 2026-09-05 (S2C-Fix1-take4.MP4, 5/5)
DEFECT SEEN: take 1-3 — Dupe RUNS across the frame (both feet off the floor),
  and in take 1 he looks straight into the lens while crossing.
PROMPT A (t1, cc8cdb0 → t2 cb3059f):
  "HE WALKS QUICKLY AND HE NEVER RUNS — a fast, purposeful, long-strided walk,
  the walk of a man late for something, never a jog, never a scurry, never a
  trot… THREE crossings in the first five seconds"
  t2 added a number and still ran: "about 1.7 metres per second… roughly two
  and a half steps a second, both feet in contact with the floor in turn and
  never both off it at once… No jog, no trot, no scurry, no speed-up."
  (t2 did fix the eyes: "HIS EYES GO WHERE HIS FEET GO… never at the camera,
  not for a single frame" — held from t2 on.)
PROMPT B (t4, 3a3545b):
  "HE IS WORRIED AND HE IS WALKING — slowly, back and forth, the way a man
  walks when he is turning a problem over and getting nowhere with it. NOT
  FAST. Slower than an ordinary walk, not quicker… HIS LEGS ARE THE CALMEST
  PART OF HIM. Everything that shows the panic happens above the waist, and
  none of it makes him move faster."
  — and the previz proxy was re-cut to walking speed in the same commit ("the
  previz was telling Dupe to run while the prompt said not to").
WHY B HELD: the video reference sets the speed and beats prose (§7); "never
  runs" is a prohibition with nothing in its place (§11). B put a slower
  POSITIVE in the sentence, moved the panic above the waist so speed was no
  longer how the emotion was shown, and made the previz agree.
LESSON: negatives cannot slow a character. Name the slower action, take the
  emotion off the legs, and measure the previz in m/s before blaming the prose.
  (§7, §11; memory feedback-previz-motion-beats-prompt-words)

### S2E → S2Eb · the fake cleaning · takes 1 → 2 · S2Eb-Fix1.MP4 filed 2026-09-03 21:50, no further take ordered
DEFECT SEEN: S2E take 1 — performance passed on every point, but the wall
  mark beside his face rendered as an insect-like figure.
PROMPT A (S2E, s2e-fix1-fake-cleaning.txt):
  "@project_absence_loc_hall_big_d — THE MUSEUM… It is a four-panel sheet —
  take NOTHING of its arrangement… at the hero wall, close enough that HIS
  FACE AND THE PATCH OF WALL HE IS CLEANING ARE BOTH IN SHOT AT ONCE… The
  mark is on the wall beside him with the brass plaque level beneath it… he
  wipes the wall beside the mark in slow steady circles"
PROMPT B (S2Eb, 0bb4a82):
  "@loc_hall_big_e — THE ROOM, and this shot happens inside it: a long
  gallery with CHROMIUM TRUMPET COLUMNS in receding pairs… working in the
  colonnade, close enough that HIS FACE AND THE THING HE IS CLEANING ARE BOTH
  IN SHOT AT ONCE… HE IS CLEANING THE ROOM, NOT A WALL. Cloth in hand, he
  works the polished chromium of a column and the white edge of a plinth"
  — the mark and the plaque are not in the shot at all.
WHY B HELD: at the time no plate showed the mark, so the model had to invent
  it, and it invented a creature. B moved the action to surfaces the room
  plate does show and took the un-referenced object out of frame.
LESSON: an object with no reference is an object the model will invent. Give
  it a plate or keep it out of the shot; a description is not a reference.
  (§7)

### S2Q · the Madame's entrance · blocked ×2 → passed the gate 2026-09-05 (S2Q-Fix1-Credit-NONAME.mp4)
DEFECT SEEN: Generate refused twice by the protected-content gate — no clip
  at all. (The passing clip's staging was separately flagged by the CTO and
  the CEO closed the scene; this entry is about the gate.)
PROMPT A: the full S2Q prompt with the character named — dialogue "Madame
  Thibault.", and "MADAME THIBAULT" in the reference description, the position
  map and the blocking lines.
PROMPT B: byte-identical prompt with the name removed everywhere — she is THE
  WOMAN IN GREEN. Passed first try. (S2R/S2S/-B carried the same name and were
  stripped before firing, 1f50a7d.)
WHY B HELD: the filter reads the whole prompt, and a name that collides with
  a protected person or title blocks the clip silently. Which word collided —
  "Madame" or the surname — is still unknown; Valder and Carrington are proven
  safe.
LESSON: a proper name is a risk only when it collides; when the gate refuses,
  strip proper names first and re-fire before touching anything else. (§10)

---

## PENDING — Prompt A quoted now, Prompt B on the day the take passes

### S2K / S2M / S2N / S2L · the crack · S2K t1 FLAGGED 2026-09-06, S2M/S2N t1 and S2L t1-5 pre-canon
DEFECT SEEN (S2K t1): the crack is the right idea — a black star-shaped mark
  floating in front of the far red door — but about five times too big, with
  heavy arms drawn across two women's faces.
PROMPT A (until 3ca9420 / dd6e0de): two descriptions of one object in one
  paste block. The reference paragraph said "SMALL. A delicate star about
  the size of a hand", while the shot lines said "THE CAMERA IS INSIDE THE
  BROKEN WALL, looking out through the break… The jagged edges of the hole
  sit in the extreme foreground as a hard black silhouette… THE FRAME…: the
  ragged black opening frames the picture". The model rendered the vivid one.
PROMPT B (dd6e0de, 136f8ef, fb1e32e, b6984f5): one description — "IT IS A
  CRACK, NOT A STAR: a BLACK crack in the wall… COPY THAT MARK EXACTLY AS THE
  PICTURE SHOWS IT AND NEVER CHANGE IT… It is SMALL… IT IS THE NEAREST THING
  TO THE LENS… THE WALL ITSELF IS NOT VISIBLE — no plaster, no edges, no hole,
  no black surround". Canon: PLATE-loc_wall_pov_e.md.
VERDICT: S2M t2 (canon prose, 2026-09-06 10:22) FAILED THE SAME WAY — crack
  ~4-5x the plate, black core across a face; everything else passed. Prompt B
  did not move the size at all. New hypothesis: "nearest thing to the lens /
  extreme foreground / floating at the very front" is a DEPTH cue, and a near
  object is big in frame — the model did perspective correctly; "size of a
  hand" is a world size, not a frame size.
PROMPT C (S2M t3): no depth words; size anchored in the frame — "NO WIDER
  THAN THE RED DOOR AND NO TALLER THAN THE RED DOOR, exactly as the picture has
  it"; the crack-shape negatives removed.
  t3 (12:15) was NSFW-REJECTED by the platform's OUTPUT filter — zero output,
  credits refunded, "Output may contain sensitive content". Not a verdict on
  Prompt C (take 2 with the same cast and scene rendered fine). Re-fired as
  take 3b with the prompt unchanged; a second rejection would mean a trigger
  in the new prose. If 3b renders and is still oversized, the plate/model is
  the driver → editor overlay, not a prompt.

### S2P · Valder's tour · t1 no Valder, t2 cart separated from Dupe and Valder at the back
PROMPT A (t2, 10ba858 era): the cart and Dupe described in separate lines;
  Valder's position given once among thirteen references.
PROMPT B (db41c9b): numbered line order with Valder in front, "the cart WITH
  Dupe — separation banned", review order 1b/1c added.
VERDICT: awaiting t3.

### The projector plate (image) · take 1 not Dupe (prose-only), take 2 not Dupe (image reference attached)
PROMPT A: prose-only face description, no image reference.
PROMPT B: the same prose with ELEMENT-dupe-interview-house.png attached — still
  rejected by the CEO 2026-09-06. No Prompt C from us: the CEO supplies the
  next plate. Recorded so nobody fires a third.

### IV2c · the crew reveal · takes 1 → 4 → 5, verdict on take 5 not recorded
PROMPT A (t4, 6ec846e): the man who knocked the stand over "STANDING FROZEN
  and STARING at the floor… ARMS COMPLETELY STILL. He is not gesturing, not
  explaining, not shrugging, not talking" (a stillness written as a list of
  bans).
PROMPT B (t5, 4f04928): "CROUCHED DOWN ON ONE KNEE… picking his light stand
  back up" — an action in place of a stillness. Also from t4: the fallen
  stand made visible ("unmistakably DOWN and on the floor") and two of Dupe's
  furnishings required in frame so the room reads as his house.
VERDICT: take 5 landed 2026-09-05 04:39; the interview is being re-shot with
  the projector (IVR1/2/3), so this entry closes only if IV2c t5 is used.
