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

### S2M · the crack's SIZE · takes 1 → 3b · size passed 2026-09-06 13:55 (S2M-Fix1-take3.MP4)
DEFECT SEEN: S2K t1 and S2M t2 — the crack 4-5x the plate's, thick black core
  drawn across a woman's face; everything else in both shots passed.
PROMPT A (S2M t2, dd6e0de): "IT IS THE NEAREST THING TO THE LENS — it floats
  at the very front of the frame, in the plane where the wall was… It is
  SMALL: about the size of a hand, a mark you could cover with your palm" and
  "one small solid black crack, star-shaped, floating in the extreme
  foreground, the nearest thing to the lens".
PROMPT B (S2M t3b, c082768 + 48ec434): "THE MARK, from that picture and only
  from it. SAME PLACE IN THE FRAME: over the far red door, in the upper middle
  of the picture. SAME SIZE IN THE FRAME: a small patch, NO WIDER THAN THE RED
  DOOR AND NO TALLER THAN THE RED DOOR, exactly as the picture has it and not
  one bit larger" — and every depth word removed from the paste block.
WHY B HELD: depth words are a size instruction. "Nearest to the lens / extreme
  foreground" makes a near object BIG in frame — the model did perspective
  correctly — and "size of a hand" is a world size the model cannot place.
  Anchoring the size to something visible in the same frame (the door) gave
  it a scale it could honour: the mark came out about 1x the door.
LESSON: give an object's size relative to another thing IN THE FRAME, never as
  a world measurement, and never with depth words unless you want it big.
  (§7, and a new rule for §12's readers.)
SIDE EFFECT → see PENDING (S2M orientation): B's "turned toward the mark" plus
  "over the far red door" turned the five toward the DOOR with their backs to
  the lens for 0-6s. Take 3 itself was NSFW-rejected by the output filter
  with zero output; 3b was the identical prompt and rendered.

### S2M · the five's ORIENTATION · take 3b → 4 · passed 2026-09-06 15:10 (S2M-Fix1-take4.MP4)
DEFECT SEEN: take 3b — for 0-6s the five stood with backs and profiles to the
  lens, looking at the far door; the crack itself was right.
PROMPT A (t3b, c082768): "the five standing in it at uneven distances, turned
  toward the mark" and "[0s] … FACING THE MARK — which means facing the lens,
  not standing side-on in profile".
PROMPT B (t4, 8537f04): "the five standing in it at uneven distances, FACING
  THE CAMERA — full face to the lens, not backs, not profiles" and "[0s] …
  FACING THE CAMERA — their faces toward the lens, nobody's back to us, nobody
  side-on in profile". The people's orientation is never tied to the mark.
WHY B HELD: once the mark's depth was left to the picture ("over the far red
  door"), "toward the mark" meant toward the door. Saying where the faces
  point in camera terms removed the dependency — and the mark stayed about 1x
  the door, so the size anchor and the gaze fix do not fight.
LESSON: state gaze and body orientation in camera terms ("facing the camera",
  "backs to the room"), never relative to an object whose depth the prompt
  leaves to a reference. (§7b)
RESULT: S2M-Fix1 closed on take 4 — mark 1x the door, faces to the lens,
  registrar's entrance and ledger, cast of seven, camera locked.
CONFIRMED on S2K take 2 (2026-09-06 16:19, S2K-Fix1-take2.MP4): same two
  sentences carried over — mark about 1x the door and off every face, the
  four women full-face to the lens, the couple two women, the man in maroon
  alone far off, Dupe at his cart. S2K-Fix1 closed. The prose is now the
  template for S2N t2 and S2L t6.
CONFIRMED AGAIN on S2N take 2 (17:38): mark about 1x the door. But S2N t2
  inverted the gaze — backs to the lens from 0s (see PENDING: S2N gaze).
VARIANCE, five takes on the same anchor (2026-09-06): S2M t4 1x, S2K t2 1x,
  S2N t4 1.5x, S2N t3 2x, S2L t6 3x the door. The frame anchor removes the 5x
  monster and the face-crossing arms every time, but the size still rolls
  between 1x and 3x. If the editor needs one identical crack across cuts, an
  overlay at edit time is the only exact tool; the prompt gets you "small".

### S2N · the five's gaze · take 2 → 3 · gaze passed 2026-09-06 18:55 (S2N-Fix1-take3.MP4)
DEFECT SEEN: take 2 — backs to the lens from 0s, facing the far door before it
  opened; the beat (faces → door opens at 1s → the turn at 6s) inverted.
PROMPT A (t2, 3b6294f): "the five stand FACING THE CAMERA — full face to the
  lens, not backs, not profiles — with their backs to the room" (+ previz).
PROMPT B (t3, 75108b8): "…not backs, not profiles, their faces toward us until
  the door opens" — "with their backs to the room" removed (+ no previz).
WHY B HELD: the model places the camera in the room, so "backs to the room"
  read as backs to us and overrode "facing the camera". Two variables were
  changed together (phrase and previz); t4 put the previz back and the gaze
  stayed correct — the phrase was the culprit.
LESSON: never describe orientation relative to the room or the wall when the
  camera stands where the wall was — camera terms only. (§7b)
RESULT: t3 gaze correct in every beat; t3 not accepted for other reasons (see
  PENDING: S2N cast count).

### S2N · cast count · take 3 → 4 · passed 2026-09-06 21:10 (S2N-Fix1-take4.MP4)
DEFECT SEEN: take 3 (no previz) — the woman in magenta missing, 8 of 9; the
  mark about 2x the door.
PROMPT A (t3): "[0s] Nobody has moved. The five are at the wall." with no
  video reference for the position map to point at.
PROMPT B (t4, f0c0a7b): "[0s] Nobody has moved. THE FIVE ARE AT THE WALL, left
  to right: the young woman in the blue coat, the art student, the woman in
  the chestnut fur, the man in maroon, and THE WOMAN IN MAGENTA at the far
  right — all five present, nobody missing" + the previz attached again.
WHY B HELD: a character who exists only in the POSITION MAP and the REFERENCES
  has no beat; naming all five in the first beat gives the model a count it
  has to honour, and the previz gives the map something to point at. The
  gaze stayed correct with the previz back on — so the "backs to the room"
  phrase, not the previz, was the gaze culprit (the open question from the
  entry above is answered).
LESSON: every character gets a beat line that names them; a position map
  alone does not hold when there is no video to map against. (§7, §12)
RESULT: S2N-Fix1 closed on take 4 — nine people, faces to the lens then the
  turn, the old man stopped inside the door, the registrar's walk and bow,
  camera locked; mark about 1.5x the door (accepted — thin, black, off every
  face, same place).

---

## PENDING — Prompt A quoted now, Prompt B on the day the take passes

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

### S2R · the copyright gate · fires 1-3 rejected → fire 4 rendered 2026-09-07 07:50 (S2R-Fix1.MP4)
PROMPT A (d53060d sheet): 14 Element chips including
  `@project_absence_prop_croc_bag — HER BAG, held in one gloved hand the whole
  time…`. Three fires — two with the previz, one without, same text — every
  card ended `Rejected due to copyright restrictions` (card title attr).
PROMPT B (4e461a1): byte-identical text with that one chip removed and the
  bag carried as prose — `HER BAG (no picture — describe it, do not look for
  one): a dark crocodile-skin handbag…` — 13 chips, previz on. Rendered.
DEFECT SEEN: the filter is not reading names (Carrington/Valder are proven on
  this lane) and not the previz; it rejected an IMAGE — the crocodile-handbag
  plate reads as protected trade dress.
WHY B HELD: the trigger was a reference, so removing the reference removed the
  rejection; the prose keeps the prop in the scene.
LESSON (§10 amended): on a copyright rejection, diff the sheet's chips against
  every sheet that rendered ON THE SAME LANE and drop the never-rendered props
  first. S2Q's "it was the name" entry above is confounded — the name strip and
  the move to the credit lane happened in the same fire — so keep names as the
  second suspect, not the first.

### S2M-B · the mark from the ROOM side (reverse angle) · prose fixed before the first fire · PASS 2026-09-07 11:00 (S2M-B-Fix1.MP4)
PROMPT A (never fired — the sheet as written 2026-09-05): "IT IS THE NEAREST
  THING TO THE LENS — it floats at the very front of the frame … about the
  size of a hand, a mark you could cover with your palm" — the same depth
  words that made S2K/S2M/S2N draw a 5x mark, and wrong for a reverse angle
  where the wall is in the background.
PROMPT B (30f3a59): "seen here FROM THE ROOM SIDE … it sits on the wall they
  face, above the brass plaque. SAME SIZE AS IN THE PICTURE: a small patch, NO
  WIDER THAN THE BRASS PLAQUE BENEATH IT AND NO TALLER THAN THAT PLAQUE".
RESULT: first fire — one small solid-black crack about the plaque's width,
  above the plaque, off every body. PASS.
LESSON: size lives in the FRAME — anchor it to an object that is in the same
  shot (the plaque for the room side, the red door for the wall side), and
  say which side of the wall the camera is on.
