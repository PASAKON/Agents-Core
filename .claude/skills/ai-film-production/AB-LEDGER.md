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

### prop_van (image plate) · Carrington's van · takes 1 → 4 · CEO APPROVED 2026-09-07 16:02
DEFECT SEEN: take 1 rendered a low black WEDGE COUPÉ, not a van at all. Take 2
  swung the other way — a tiny cab under a windowless box roughly three times
  the cab's height, a vehicle that does not exist.
PROMPT A (t1, 058dc40): "Retro-futuristic 1970s concept-car design language,
  the same era as a wedge-shaped limousine: a long GLOSS BLACK VAN — a sleek
  streamlined box on wheels, sharp creased body lines, low flat roof…"
  t2 (402c98c) led with the body but sized it by a human landmark: "a tall boxy
  one-box panel van… a high flat roof as tall as a standing man's shoulder".
PROMPT B (t3, b6c1562): "THE VEHICLE IS A CLASSIC 1970s PANEL VAN in gloss
  black, with ORDINARY VAN PROPORTIONS: about 5 metres long and 2 metres tall —
  only a little taller than a car, the roof one flat line from the windscreen
  to the tail, the body a long low box two and a half times as long as it is
  high", negatives "no tall box, no high roof, no camper, no truck, no lorry,
  no bus… no low wedge body".
  t4 (8fad09d) kept t3's proportion sentences verbatim and added only the
  luxury dressing the CEO asked for ("mirror-polished piano-black… a broad
  polished chrome band… a thin GOLD pinstripe… deep-dish chrome wire wheels
  with whitewall tyres… cream silk curtains… quilted cream leather lounge
  seats").
WHY B HELD: two independent failures, one cause each.
  1. ERA BEFORE CLASS. Take 1's first content clause was the era, and the era
     was illustrated with "a wedge-shaped limousine" — the model rendered the
     illustration. The object's CLASS must be the first thing the sentence
     says; the era is dressing applied to that class, never the other way up.
  2. A HUMAN LANDMARK IS NOT A MEASUREMENT. "As tall as a standing man's
     shoulder" gave take 2 a licence to grow: there is no man in frame to
     scale against, so the phrase only says "tall". Metres plus a RATIO
     (2.5 : 1 long-to-high) is checkable inside the picture and held on the
     first try.
LESSON: name the object class first, size it in metres and ratios, and put the
  banned silhouettes in the negatives by name. Once the proportions render
  right, do NOT rewrite them for a style change — copy those sentences across
  verbatim and add only the new dressing (t4 did exactly that and kept the
  shape).

### SC2 · a flagged prop Element vs the same prop in prose · credit lane · fired clean 2026-09-07 13:44
DEFECT SEEN: SC2 staged with @project_absence_prop_car raised the pre-fire
  toast "Some reference elements may contain protected content. Check
  eligibility or remove them to proceed", and the chip carried a
  warning-triangle badge. There is no per-Element eligibility control to clear
  it. One click at 13:24 was refused client-side; credits unchanged (461).
PROMPT A: 4 chips including "@project_absence_prop_car — THE CAR: the emerald
  green retro-futuristic sports coupé…".
PROMPT B (028c131): the chip dropped to 3 and the car carried as prose in the
  same slot — "an emerald-green retro-futuristic sports coupé, low and
  angular, chrome trim, the only car in the shot".
WHY B HELD: fired first click, "Generation started", credits 461 → 409 exactly
  (-52), no warning. Second data point for the same rule the croc bag gave on
  S2R: a flagged Element is not negotiable and not fixable from the composer —
  the object survives as prose with no loss on screen. Flagged so far:
  prop_croc_bag, prop_car, char_guard_private (v1, retired).
LESSON: when a chip shows the warning triangle, do not click twice hoping —
  move that object into prose in the same sentence position and re-verify the
  chip count before firing.

### S15a-1 · an unnamed side of frame gets filled by mirroring the chip beside it · CONFIRMED by take 2 · 2026-09-08
DEFECT SEEN: twice in one night, on two unrelated sheets, in the same shape.
  1. S15a-1 t1 (52 credits): the Registrar — one man, one chip — appeared at
     BOTH frame edges, black suit, white gloves, gold V, ledger, twice.
  2. S2S-B t2 (free lane): @project_absence_char_guard_valder_two, whose whole
     text is "VALDER'S TWO GUARDS … ONE TALL AND THIN, ONE SHORT AND HEAVY.
     This one picture is both of them", rendered as FOUR navy uniforms — the
     tall/heavy pair on Valder's left and the same pair again on the woman in
     green's right, mirrored across the group. Three named characters
     (Registrar, art student, Dupe) were missing from the same frame.
WHAT BOTH SHEETS ALREADY SAID: the count, in capitals, correctly. S2S-B even
  said "This one picture is both of them" and carried a "no face is repeated
  anywhere" negative. Saying the number does not stop the duplication.
WHAT THE TWO FAILING SHEETS HAD IN COMMON: one side of the frame had nothing
  named standing in it. The model filled the empty side by copying the closest
  chip it had. It is not a counting failure, it is a composition failure — an
  unoccupied region is an instruction to invent an occupant, and the cheapest
  occupant is the one already on screen.
FIX APPLIED (S15a-1, d0d19f9): anchor BOTH sides by name. The three bodyguards
  are placed one by one at the LEFT edge with shoulders touching; the Registrar
  is stated as exactly one man on the RIGHT, "the only person in the entire
  frame wearing a black suit with white gloves and a gold V". Neither side is
  left for the model to fill.
LESSON: a count is not a placement. For any chip that depicts more than one
  person, or any chip whose costume is visually distinctive, say WHERE its
  people stand and say what stands on the opposite side of frame. If a region
  of the frame has no named occupant, expect the nearest distinctive costume to
  be copied into it.

### S15a-2 vs S2G · the mark rendered as an insect when the sheet only named it · 2026-09-08
DEFECT SEEN: S15a-2 t1 put the mark on the wall as fine GREY hairlines with thin
  legs radiating from a dark dot. At the scale it rendered it reads as a mosquito
  or a spider sitting on the plaster, not as masonry damage. Size was arguably
  right (about a head wide); weight and colour were not.
PROMPT A (S15a-2, failed): the mark appears once, inside the location chip's
  description, as a shorthand — "the brass plaque and the small black mark on the
  axis". Four words, no shape, no weight, no negatives.
PROMPT B (S2G, the insert whose entire subject is the mark): the full canon —
  "IT IS A CRACK, NOT A STAR: a BLACK crack in the plaster… COPY THAT MARK EXACTLY
  AS THE PICTURE SHOWS IT… It is IN the wall, a break in the surface, not a thing
  in front of it and not a drawn shape… no spiderweb, no thick heavy arms, no pale
  or grey mark, no glowing mark — solid black only."
LESSON: the mark has a canon and the canon has to travel with it. A sheet that
  merely NAMES the mark while describing something else will get whatever the
  model imagines a small black mark to be, and what it imagines is an insect.
  Every sheet in which the mark is visible carries the full description, even when
  the mark is background and the scene is about people.
WATCH: S2G says "thin short lines" in the same breath as "solid black only" and
  "no thick heavy arms". If S2G comes back spidery too, "thin" is the word doing
  the damage and the canon needs rewriting to lead with weight, not with size.

### S15a-1 take 1 → take 2 · anchoring both sides of frame · free lane · PASSED 2026-09-08 02:10
DEFECT SEEN (t1, 52 credits, fired 22:31): (b) the three bodyguards did not group —
  Valder's two navy guards stayed at the left edge while Carrington's man in black
  stood alone at the right edge; (e) the Registrar appeared at BOTH frame edges,
  black suit, white gloves, gold V and ledger, twice.
PROMPT A (t1), the guards: "THE THREE BODYGUARDS STAND TOGETHER, shoulder to shoulder
  in one small group at the frame edge nearest their masters — Valder's two navy
  guards and Carrington's man in black side by side, close enough to touch, all three
  facing the room and none of them moving for the whole clip."
  And the Registrar, in full: "@project_absence_char_registrar_b — THE REGISTRAR: a
  formal BLACK suit, white gloves, a GOLD V, the leather ledger. Present, still."
PROMPT B (d0d19f9), the guards, placed one by one with a side named: "THE THREE
  BODYGUARDS STAND IN ONE GROUP AT THE LEFT EDGE OF FRAME — COUNT THEM: THREE, and
  all three in the SAME place. VALDER'S TALL THIN NAVY GUARD stands at the left edge.
  VALDER'S SHORT HEAVY NAVY GUARD stands directly beside him with their shoulders
  touching. CARRINGTON'S BODYGUARD IN BLACK stands directly beside the short guard…
  Every bodyguard in this film is in that group at the left edge; the right side of
  frame holds ordinary guests only."
  And the Registrar, given the other side to hold: "THERE IS EXACTLY ONE REGISTRAR —
  one man, standing on the RIGHT side of the room, still, holding the ledger. He is
  the only person in the entire frame wearing a black suit with white gloves and a
  gold V; every other guest wears something different."
WHY B HELD (measured on t2's own frames, fired 01:40, landed ~02:10, free lane):
  at 0.2s the three bodyguards are one unbroken group at the LEFT edge, navy, navy,
  black; exactly ONE registrar, at the RIGHT edge, with no copy on the left; exactly
  TWO navy uniforms in the whole frame. The shield still reads at 3.3s with the
  workman in shot, four press at 5.9s, and every face different.
WHY IT WORKS: take 1's prose already said "TOGETHER", "one small group", "close enough
  to touch" and gave the correct count. None of that binds, because none of it says
  WHERE. What changed is that both sides of frame now have a named occupant — guards
  left, registrar right — so there is no empty region for the model to fill by copying
  the nearest distinctive costume.
LESSON: a count is not a placement, and "together" is not a location. Name the side of
  frame each group stands on, and name who holds the opposite side. Confirmed three
  times over as a defect (S15a-1 t1 registrar, S2S-B t2 guard pair, S15a-2 t1 fourth
  guard) and once as a fix.
STILL OPEN on this take: the wall mark renders as spidery hairlines and reads as an
  insect. Canon rules 6 and 7 (weight before size; the canon travels with the mark)
  were added at 01:32, eight minutes before this fired, and were not yet in this
  sheet. Not a counter-example to the fix above — a separate defect with its own fix.

### S15a-2 take 1 → take 2 · weight before size on the mark · PASSED ONCE, THEN FAILED — see the correction at the end of this entry · 2026-09-08
DEFECT SEEN (t1, 52 credits, fired 00:33): the wall mark rendered as fine GREY
  hairlines with thin legs radiating from a dark dot. At the rendered scale it reads
  as a mosquito or spider sitting on the plaster, not as masonry damage.
PROMPT A (t1) — the mark is NAMED and never described, four words inside the location
  chip: "@project_absence_loc_hall_big_d — THE HALL … white plinths, the brass plaque
  and the small black mark on the axis."
PROMPT B (a80e193) — the mark gets its own sentences, weight stated BEFORE size:
  "THE MARK ABOVE THE PLAQUE IS A CRACK IN PLASTER AND IT IS DRAWN IN SOLID BLACK:
  one short thick black line about as wide as a man's hand, with three or four shorter
  thick black lines breaking off it, every line solid and heavy like ink, the whole
  thing star shaped and flat against the wall. Take 1 rendered it as fine grey
  hairlines with thin legs and it read as an insect on the wall. It is masonry damage:
  thick, black, angular, and part of the plaster."
WHY B HELD, measured on t2's own opening frame rather than eyeballed: the mark is
  solid black, thick, angular and star-shaped, sitting IN the plaster. Dark-pixel
  bounding box 96 x 125 px on a 1280 x 720 frame; Dupe's head is 108 px wide at face
  level, so the crack is 0.89 of a head across — about a hand, which is canon. Worth
  recording that the first visual impression was "too big" and the measurement said
  otherwise: the heaviness reads as size, but the extent is right. Measure before
  flagging a size.
WHY IT WORKS: "thin" and "solid black" had been sitting in the same breath in five
  sheets, and thin won every time. Leading with weight — solid, heavy like ink, dark
  for its whole length — and only then giving the hand-across size, reverses that.
  Predicted in this ledger before S2G landed, confirmed by S2G's tan tendrils, fixed
  here on the first attempt.
LESSON: canon rules 6 and 7 in PLATE-loc_wall_pov_e.md now carry this. Weight before
  size, and the full description travels into every sheet where the mark is visible —
  naming it is not describing it.
ALSO FIXED on this take: exactly TWO navy uniforms across the full frame width, so
  take 1's mirrored fourth guard is gone.
STILL OPEN: the three bodyguards are not one group — the two navy are together at the
  left edge but Carrington's man in black stands across the frame on the right.

### SC5 take 2 → take 3 · the wide shot was copying the plate's sky · free lane · PASSED 2026-09-08 04:05
DEFECT SEEN (t1 credits, t2 free): shot one's sky came back flat blue-grey while shots
  two and three were correctly amber. Two takes in a row, and the sheet already said
  sunset in a global paragraph AND inside shot one's own line.
PROMPT A (t2): "SHOT ONE · [0s-3s] · locked wide from the forecourt, the whole
  entrance in frame with the sunset sky above the roofline — amber and rose low down,
  gold on the cloud, long shadows raking across the terrazzo…"
PROMPT B (3a3d4d2): the light stated first, and the SHOT MOVED so the sky is barely
  present — "THE LIGHT IN THIS SHOT IS SUNSET, and it is the first thing to get right:
  low amber sun raking in from the camera side… Locked wide, but taken LOW and CLOSE —
  the camera is down at shoulder height in among the back of the crowd, not standing
  off across an empty forecourt. Heads and raised arms fill the bottom two thirds of
  frame… and the sky is only a thin band of amber and rose along the top."
WHY B HELD: at 0.5s the facade is raked with low amber light, the cream stone burns
  gold where it catches, every figure throws a long shadow. The diagnosis was that
  shot one is the widest and most closely resembles the four-panel reference plate, so
  it was copying the plate's midday sky wholesale; shots two and three, being less
  plate-like, invented their own light and got it right. Lowering the camera did not
  make the sunset instruction louder — it removed the surface the plate was being
  copied onto.
LESSON: when a wide shot ignores a stated light, the reference plate is winning.
  Adding adjectives loses to a picture. Change the framing so the contested area — the
  sky here — occupies little of the frame, and the plate has nothing left to impose.
SAME TAKE, second fix that held: SIX GUARDS WITH REAL FLANK COVER.
  A: "GUARD 1 at the far left… GUARDS 2, 3, 4 and 5 shoulder to shoulder across the
  middle… GUARD 6 at the far right… six navy uniforms in the line". They bunched at
  the doors, because "in the line" reads as one line.
  B: "THEY ARE NOT ONE TIGHT LINE — they are a middle block of four with a lone man on
  each flank… GUARD 1 STANDS ALONE… several metres of empty step between him and the
  middle four; his job is the left-hand wall and he turns back everyone who tries to
  squeeze along it… GUARD 6 STANDS ALONE… his job is the rail."
  Held on the first try: one alone at the wall with arms out, four across the doors,
  one alone at the rail with arms out, empty step visible either side.
  LESSON: give a figure a JOB, not just a coordinate. "Stands at the far right" is
  decoration; "his job is the rail and he pulls back anyone who climbs it" is blocking.
STILL OPEN: shot two broke location a third time — an open horizon with trees and
  floodlights. Cause found and fixed in 6d0f21e, and it was a contradiction in the
  prompt, not a model failure: the camera was told to look DOWN the steps into the
  crush while the museum was asked to sit BEHIND the crowd. Standing at the doors
  looking down, the building is at your back. Turning the camera to look ALONG the
  facade makes both true at once. LESSON: before adding words to fix a background,
  check that the camera position you asked for can physically see it.

CORRECTION 2026-09-08 07:00, after S15a-2 take 3. The entry above was written from a
single take and it overclaimed. Take 3 fired from the SAME sheet with the mark
description untouched — only the shot-two guard line changed between them — and the
mark came back GREY and wire-thin again, reading as an insect exactly as take 1 did.
Measured on the opening frames:
  take 2: registers as dark at threshold <80, bbox 96 x 125 px, 7.5% of frame width,
          fill 0.12 — solid black, thick, angular.
  take 3: does NOT register at <80 at all; only appears at 150-190 against a
          background of 220. Bbox 59 x 56 px, 4.6% of frame width, fill 0.091.
Take 3's mark is SMALLER than take 2's and still failed, so the causal story in canon
rule 8 — bigger in frame means thinner — does not survive this data point. What
actually differs is blackness, and it differed with no change to the words.
WHAT THIS MEANS IN PRACTICE: the mark is not deterministic from the prompt. Two takes
of one sheet give opposite results, so the remedy is not another rewrite. Fire, MEASURE
against the rule 8 numbers, and keep the take that passes. Rule 8 remains a good
acceptance TEST; it is not a reliable recipe.

### S2R-JC · nothing can change ACROSS a cut — the model has no cut · FAILED TWICE, diagnosed 2026-09-08
DEFECT SEEN: the scene's own core beat, "THE HEADS SWING", has not rendered in three
  takes. Take 2 was flagged for it; take 3, after a full rewrite aimed at exactly that
  beat, failed identically.
MEASURED, take 3, greyscale mean absolute difference between frames:
  WITHIN one shot, as a baseline:   2.0s vs 2.9s  = 6.74
  ACROSS the cut at 3s:             2.9s vs 3.2s  = 3.31
  ACROSS the cut at 9s:             8.9s vs 9.2s  = 5.64
  ACROSS the cut at 15s:           14.9s vs 15.2s = 1.76
  Every cut is LESS different than two frames inside the same uncut shot. Nothing
  happens at any cut. This is the cheap test for any "jump cut" sheet and it takes
  thirty seconds: if the across-cut diff does not beat the within-shot diff, the cut
  is not doing anything.
PROMPT A (take 2): "EVERY HEAD IN THE ROOM SWINGS TO THE LEFT… a ragged wave of them."
PROMPT B (take 3, d0d19f9) — MY REWRITE, AND IT MADE IT WORSE: "THE HEADS ARE THE
  WHOLE POINT OF THIS CUT… not an animated movement but a DIFFERENCE between the frame
  before the cut and the frame after it… Put a frame from 2s beside a frame from 4s
  and you see the same twelve people with their heads pointing the opposite way."
WHY B FAILED, and it is a general fact about the tool, not about this scene:
  Seedance generates twenty CONTINUOUS seconds. It has no concept of a cut. A "hard
  cut" in the prompt buys, at best, a small discontinuity that the model then smooths
  over. So asking twelve people to flip head direction instantly at a cut boundary is
  asking for a teleport — precisely the artefact a video model is trained to erase.
  Worse, prompt B explicitly told it NOT to animate the turn, which is the one thing
  it can do well. I steered it away from the only available mechanism.
PROMPT C (take 4, f67e866): every swing moved INSIDE its shot — "WE WATCH THEM DO IT.
  It takes about half a second and every part of it is on screen: the necks rotate,
  the chins travel, the faces sweep across." The cuts stay, but they only jump the
  clock between bids; the 15s beat becomes the one where nobody turns, so that after
  four visible sweeps the stillness is the event.
LESSON, and it applies to every multi-cut sheet in this film: A CUT CANNOT CARRY A
  CHANGE. Anything that must happen has to be a movement the camera sees happen inside
  a shot. Use cuts for what they can do — jump the clock, change the angle — and never
  to hold the difference between two states.

---

### The mark's darkness test is SIZE-DEPENDENT — three greys in one day with identical prose · measured 2026-09-08
DEFECT SEEN: S16 t1 and S15b2 t1 (both credit lane, both wide room shots) rendered
  the mark as a pale brown spiderweb — darkest pixel 116 and 94, zero pixels under
  threshold 80. S15a-2 t3 failed the same way earlier. Each is a re-fire candidate
  on canon rule 8.
PROMPT A = PROMPT B: the mark paragraph is byte-identical across the two that failed
  (S16, S15b2) and the two that passed today (S15a-1 t2, S15b1 t1): "THE MARK ABOVE
  THE PLAQUE IS A CRACK IN PLASTER AND IT IS DRAWN IN SOLID BLACK" plus the same
  ban list ("no pale, grey, brown or tan mark"). The words did not vary. The result
  did. So the words are not the variable.
WHAT VARIED: pixel size. Failing marks measured 0.4-0.5% of frame width at 1280 px
  = a 5-7 px core. Passing S15a-1 t2 measured 1.0% / fill 0.538 — twice the width.
  A 5 px stroke on a 224-grey wall cannot contain a fully dark interior pixel; the
  anti-aliased edge IS the whole mark. Threshold-80 is therefore a test the mark
  can only pass above roughly 0.8-1.0% of frame width, whatever the prompt says.
LESSON: do not re-edit the colour sentence on a wide shot — it is already correct
  and it will fail again. The choice is the CEO's, and it is a framing choice:
  (a) accept a faint mark in wides (it is the same crack, just far away), (b) frame
  the wall tighter so the mark clears ~1% of width, or (c) allow the mark to be
  written larger in wides only. Canon rule 8 stays an acceptance test; this entry
  records the size below which it cannot be met.

---

### S15b · a bound character with no assigned position takes the most salient slot · take 2 FLAGGED → take 3 PASSED 2026-09-08 22:40
DEFECT SEEN: Dupe never rendered. The workman — bound as a chip, described with a
  float and a bucket, given NO place to stand — occupied Dupe's centre position
  at the wall for all 20 seconds, and the grandmother turned at 12s and paid a
  hundred million to the plasterer. Her wardrobe, the registrar's suit, the turn,
  the twelve words and the absence of cuts all held; only the casting of the slot
  failed.
PROMPT A (take 2, 69a3c8f): `@project_absence_char_workman — THE CONTRACTOR: NAVY
  overalls, a rag over one shoulder, a float in one hand and a bucket of wet
  plaster in the other…` — wardrobe and props, no position. Dupe's position lived
  only in the beat line "[0s] Hold on Dupe centred".
PROMPT B (take 3): the workman's chip gains "HE IS NOT THE MAN AT THE WALL. He
  stands FAR LEFT beside the two navy guards, the bucket on the floor at his feet";
  Dupe's chip gains "HE IS THE MAN AT THE WALL — dead centre … the one the old woman
  rolls up beside and, at 12s, turns her head to. Not the man in overalls"; the
  [12s] beat names him by wardrobe.
HYPOTHESIS: two men, one slot, and the man holding the tools looked more like "the
  man at the wall" to the model than the man with the mop. Same family as the
  ledger bleed and the gold teeth: an attribute or a place with no named owner
  goes to whoever is nearest. Fix by naming who owns the slot and where the other
  man is instead — not by dropping the workman, who is in the room in the script.
RESULT (take 3, 0c2799f, free lane, ~60 min): Dupe at the wall dead centre at 0.5s and
  12s; the workman far left beside the guards, bucket on the floor; the grey-knit
  grandmother turns at 12s to DUPE; registrar cream-white writing at 18s; twelve
  words; no cuts. Only Valder is out of frame at 18s. PASS — supersedes take 2.
WHY B HELD: both men were given a place, and the place was tied to the wardrobe the
  model can see. Naming who owns the slot beats describing the slot.
LESSON: a bound character with props and no position will take the most salient
  slot in the frame. Every chip that is a person gets a WHERE, not only a WHAT.


Only entries whose take has NOT yet been fired or judged belong under this
header. Ten finished entries had drifted below it because new material was
appended to the end of the file, which made the section read as though the
crack, the van and the copyright gate were still open questions. Moved back
up on 2026-09-08; append new PASSED entries ABOVE this header from now on.

---

### S2S · RETRACTED 2026-09-08 23:12 — the "take 2" the worker reviewed was S2S-B's card, not S2S's
WHAT ACTUALLY HAPPENED: the S2S worker (fired 20:22) identified a card "Created 8:56 PM"
  as its own landed take and reviewed it — camera behind the grandmother, her back in
  the foreground, rolling into the group. That is the B angle. Asset `ad847559` is
  S2S-B's card (S2S-B fired 20:56:59; Higgsfield's Created time is the FIRE time,
  not the landing time). The S2S-B worker later identified the same asset correctly
  and it PASSES S2S-B's review order. S2S's real take 2 (created ~20:22) has not been
  reviewed by anyone. The "no previz → foreground" causal story above was drawn from
  the wrong clip and is withdrawn; whether S2S t2 needs the previz is UNKNOWN until
  its real card is looked at.
LESSON (this one stands): IDENTIFY A CARD BY ITS CREATED TIME EQUALLING YOUR FIRE
  TIME, never "the newest New badge" and never "prompt looks like mine" — sibling
  scenes share most of their prompt text. A Created time 34 minutes after your fire
  is somebody else's card. Added to FIRE-PLAYBOOK §2.

---

### The grandmother · a character whose CLOTHES the sheet never named wore someone else's · S2S-B take 3 PASSED 2026-09-08 23:07
DEFECT SEEN: in Draft 3 (S2S at 4:33 and 5:42) the woman who bids a hundred million
  wore a PURPLE headscarf and dark sunglasses, while every other scene had her in
  grey knit. Two grandmothers on screen at the climax.
PROMPT A (S2S / S2S-B before bffdf60): the chip block described her WHEELCHAIR for
  eight lines — "a RETROFUTURIST ELECTRIC WHEELCHAIR — a genuine powered mobility
  chair with a chromium tubular frame…" — and her clothes for none. The only
  sunglasses in the sheet belong to the Madame.
PROMPT B (bffdf60, every sheet that binds her): "SHE WEARS EXACTLY WHAT HER PICTURE
  SHOWS AND NOTHING ELSE: a GREY knitted headscarf tied under the chin, a GREY
  knitted cardigan, a knitted bag on her lap, brown boots. NO sunglasses on her —
  the sunglasses in this room belong to other people. NO purple, NO coat, NO hat."
RESULT: S2S-B take 3 (free lane, ~70 min, fired WITHOUT previz): grey knit headscarf
  and cardigan from behind for all 20 s, camera behind her, the group turns to the
  lens at ~3 s, she rolls away, one line, no cuts — PASS, filed to Fix-2 over
  take 2. S15b takes 2 and 3 the same evening: grey, no sunglasses, both times.
WHY B HELD: the plate was already bound; what the model lacked was a sentence that
  OWNED her wardrobe. Into that gap it borrowed the nearest striking attribute in
  the prompt — the Madame's sunglasses and a saturated colour. Naming what she
  wears, and naming whose the sunglasses are, closed the gap.
LESSON: a bound character with no wardrobe sentence will be dressed from the rest
  of the prompt. Every person-chip gets a WHAT-SHE-WEARS as well as a WHERE (see
  the S15b entry above). CAST.md now carries both per character.

---

## S16 THEY SAW THE WALL OUT — take 1 → take 2 (2026-09-09, PASSED)

**Defect seen (take 1, credit lane 2026-09-08):** the cutting tool rendered as a
CHAINSAW (orange body, long bar, chain, top handle); the two navy guards merged
into ONE body at the left edge; the mark measured grey (size-dependent, see the
mark entry above).

**Prompt A (0f5f5ff):**
> THE ELECTRIC SAW (no picture — describe it, do not look for one): a hand-held
> electric wall saw with a round toothed blade and a moulded grip, cutting through
> plaster and leaving a clean kerf.
> … SECOND the short heavy navy guard with his shoulder against the first …

**Prompt B (608a6e2):**
> THE CUTTING TOOL (no picture — describe it, do not look for one): a hand-held
> ANGLE GRINDER — a short grey motor body gripped in both hands, and at its front a
> FLAT ROUND STEEL DISC as wide as a man's spread hand, spinning inside a
> half-moon guard, its rim biting into the plaster and throwing a low fan of sparks
> … the tool has no bar, no chain, no orange body and no top handle.
> … SECOND the short heavy navy guard, a full head shorter and twice as wide,
> standing half a step IN FRONT of the tall one so that BOTH navy tunics and BOTH
> gold V's are seen whole, side by side, neither hiding the other …

The word "saw" was removed from the whole paste block ("the grinder", "its
spinning disc", "THE GRINDER STOPS").

**Why B held (take 2, FREE lane, 00:20 → 00:55):** a grinder with a fan of
sparks rendered exactly; three distinct bodies at the left edge (tall navy, short
heavy navy, black-suited bodyguard); items 1, 3, 4, 6 unchanged from take 1.

**Lesson:** "electric wall saw" is a WORD the model resolves to its most common
picture (a chainsaw) — name a tool by its unmistakable SILHOUETTE (angle grinder,
flat disc, sparks) and never use the generic word again in the block. And two
characters sharing one reference picture need two POSITIONS, not a count:
"shoulder against the first" invited the merge; "half a step in front, both
tunics whole" gave each man his own place. Same family as the S15b "every
person-chip gets a WHERE" entry.

## S2R-JC THE BATTLE — take 3 → take 4 (2026-09-09, PARTIAL PASS, best of four)

**Defects seen (takes 2 and 3):** the "heads swing" core beat scored 0/12 across
every jump cut; take 3 also rendered ELEVEN people — the registrar merged into
Carrington (one figure holding the cane AND the ledger).

**Prompt A (474b653, take 3):** the head swing was written as a DIFFERENCE across
a hard jump cut ("put a frame from 2s beside a frame from 4s and see the same
twelve people with their heads pointing the opposite way"); the registrar was
"@char_registrar, near left, writing".

**Prompt B (f67e866 + d27064f, take 4):**
> [6s] AND WE WATCH THEM ALL TURN BACK, right there in the shot: every head sweeps …
> - @char_registrar, near left — a SEPARATE man from Carrington, standing two
>   paces nearer the lens than him and a pace further left, on his own, writing
> … HE IS NOT CARRINGTON AND HE DOES NOT STAND WITH HIM: a second, separate man,
> two paces nearer the camera, no cane, no white hair swept back. The ledger and
> the pen are his alone; Carrington's hands hold nothing but the cane.

**What held (take 4, FREE lane, 00:55 → 01:35):** two separate men, ledger in
the registrar's hands; five bids in order ("Ten million / Fifteen / Twenty
million / Twenty-five / Fifty"), nothing else spoken; ~12 people; heads now
MOVE on screen (registrar, critic, Carrington turn during the shot) — partial,
not the full twelve-head sweep.

**What did not hold:** the three "HARD JUMP CUT, same frame" beats rendered as
NO cut at all (0.2s sweep: no spike above 15x; only raised runs at ~3/6/9.5/12.5s).

**Lessons:** (1) a cut described as "same frame, the clock jumps" gives Seedance
nothing to cut TO — it renders continuous motion; a cut needs a visible change
of framing or subject. (2) Separating two characters is done with distance and
ownership ("two paces nearer the lens … the ledger is his alone"), the same
rule as S16's guards and S15b's workman. (3) Head turns rendered as motion only
once they were written as motion inside the shot, never as a before/after.

## PENDING — Prompt A quoted now, Prompt B on the day the take passes

### S2R-F · THE BATTLE, FACES · take 1 rejected by moderation 2026-09-09 16:30 → take 2 PENDING
DEFECT SEEN: take 1 (fired 13:19, 20s, 13 chips = the S2R-JC t4 set that rendered on
  this lane on 2026-09-08) sat queued 185 min, went in_progress at 16:24 and came
  back "NSFW · Credits refunded · Rejected due to copyright restrictions" with no
  frames. Chips ruled out by the S2R lesson (identical set rendered) → the new TEXT.
PROMPT A (2b8c3ab): "he says it quietly, the way a man throws a punch he has been
  saving" · "Carrington is smiling again, gold teeth bared" · "a single flinch
  that runs through everybody at once: mouths open, a hand flies to a mouth".
PROMPT B (bf00af7 / 12c6431 for the SPLIT twin): "the way a man lays down the card
  he has been holding all night" · "the gold teeth showing" · "a single start …
  a hand rises to a mouth". Nothing else changed.
WHY B SHOULD HOLD: the gate has twice been an image (croc bag) and once a random
  output-filter hit (S2M t3 → identical 3b rendered); this is the first case where
  the only new variable is violence-adjacent prose. Verdict on take 2 not yet
  recorded — if take 2 also rejects with the same chips, the prose theory is wrong
  and the next diff is the previz-less close-up framing itself.


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

## 2026-09-09 21:15 — S2AJ take 1 PASS · S2R-F take 2 REJECTED (moderation)
- **S2AJ "THE INTERPRETATIONS, JUMP CUT" t1** (task-b69ade88, free lane, fired 20:28:30, asset count 754→755, rendered ~21:05): CTO review PASS — 20.04s 720p, jump cuts land (critic in by 4s, student by 8s, cobalt at ~16s), black from 19s, camera locked, six lines in order, quarrel = fur (crying) / critic / student, husband silent with the tissue, row cobalt·student·fur+maroon·critic as Draft 5 @1:52. Filed Fix-2 `S2AJ-InterpretationsJumpCut-Fix1.MP4` (id 1m7joCqg5uotB94o-jr5ZluqBCAAcgx2T, md5 21251fe0e7548eac6882b56ad04cb03c). Replaces Draft 5 1:31–1:42.
- **S2R-F "THE BATTLE, FACES" t2** (task-8a6c456a, fired 17:05): Usage History "Unlimited Seedance 2.5 Refunded Sep 9 8:11 PM" = moderation rejection, second time for the five-close-up design with prose already softened. Reading: the close-up framing (not the words) trips the likeness check — every wide/medium clip with the same chips passes. Worker never reported; replaced. **CEO 20:35 select: retry as V1 five-strip split, LAST in the free queue after the safe clips.** No third close-up take.
- Queue after this: S2PT → S2PU (task-d188f5bc, spawned 21:10) → AB → S18 → S2X → S3a t2 → S2R-F V1 split.
- **CEO 2026-09-09 21:38: previz S2PT + S2PU approved ("ผ่านแล้ว ยิงได้เลย")** — task-d188f5bc fires both in order on the free lane.
## 2026-09-09 22:45 — S2PT take 1 FAIL (duplicate bodyguard) → take 2 pending; S2PU t1 in flight
- **S2PT t1** (task-dcaef051, fired 22:21, rendered ~22:30, Fix-2 `S2PT-TourTogether-Fix1.MP4` id 1FlzSY1WZwQCyCIdOt3eEPtrzrWLeBibn, md5 7b8778a39ecabf5c193368775c4420b3): track, lines, Dupe-with-cart all correct, BUT two Black bodyguards in black suits (7 people + Dupe) — the worker caught it at full resolution after the CTO had passed it on 426-px tiles. CTO verdict corrected to FAIL on cast. Carrington half a step ahead of Valder; a second mustard chair passes 3-6s. Sheet v2 (countable cast, ONE man in black, Carrington behind the shoulder, ONE chair far wall) → take 2 after S2PU lands.
- Lesson: review frames at FULL resolution for headcounts; tiles hide a duplicate standing in line.
## 2026-09-10 00:10 — S2PU take 1 PASS · S2PT take 2 spawned
- **S2PU "ARE YOU FOLLOWING US" t1** (task-dcaef051, fired 23:20, asset 757, rendered ~23:50): CTO review at full resolution PASS — locked camera (corner diff mean 2.9), party walks in from the right and stops by 5s, six exactly (ONE bodyguard), three lines in order (0-5 / 5-8 / 8-12s), Valder turns to Dupe at ~9s, Dupe caught at 12s, cap-touch at 15s, mopping beside the turned cart by 19s, no blush, no twinkle. First/last frame carry a black leader (spikes at 0.2s / 19.6s) — editor trims. Filed Fix-2 `S2PU-AreYouFollowingUs-Fix1.MP4` (id 1I1tLISK9kFSBc1zjlar0Hv1O6IfRo9v8, md5 f09fe15bd062a69746cb1e79cfc3284f). Replaces Draft 5 3:39-3:52.
- **S2PT t2** (task-ad30beb8, spawned 00:09) on sheet v2 (0b052de) — pending.
- Skill fix shipped (2a974f3): video-ref uploads go through "+" → Uploads → Videos.
## 2026-09-10 01:35 — S2PT take 2 PASS
- **S2PT "THE TOUR, TOGETHER" t2** (task-ad30beb8, sheet v2, fired 00:41, rendered ~01:22): CTO full-res review PASS — six exactly (ONE bodyguard), Valder front-most, Carrington half a step behind, two guards, Dupe last with the cart, continuous lateral track, ONE mustard chair on the blue rug 13-19s, six lines in order. Note: Valder carries a cane (wardrobe drift, minor). Filed Fix-2 `S2PT-TourTogether-Fix1-take2.MP4` (id 1bFqcnPGJCs_OEsZHxhXQvq3CpY8GlAgd, md5 cc6fe1ae841e67bc9327ea731f00729a). USE THIS, not take 1. Draft 5 3:18-3:52 now fully covered by S2PT t2 + S2PU t1.
- Lesson confirmed: counting the cast by clothes + "ONE man in black" stated three ways removed the duplicate on the first retry.
## 2026-09-10 02:20 — S15e-AB take 1 PASS · overnight plan
- **S15e-AB "SORRY, AND THE CHEQUE" t1** (task-958e2561 chain, fired 01:30:25, asset 758→759, rendered ~02:12): CTO review PASS — two hard cuts at 6.2/15.8s, five lines in order, Dupe single (crack + plaque behind), grandmother cheque two-shot with "100,000,000" legible at 14s, three-shot with Valder, Dupe takes it with both hands. Filed Fix-2 `S15e-AB-SorryAndTheCheque-Fix1.MP4` (id 175BlZe-DCtng9PdkSR9Vh71iY_r-8RvT, md5 28870c71a2a2ed9ee34140883d482b92).
- CEO 01:55 (before sleeping): S2AJ take 1 matches the brief but "หลุดธีม Wes Anderson" → redesign freely, any number of clips, done before he wakes (10-12). Built: **S2AW** tableau (20s, planimetric even row, deadpan turn-taking, unison head-turns) + **S2AP** portraits (15s, five waist-up frontal portraits, hard cuts) — sheets fe8fb44, previz on Drive.
- CEO 01:50: after the queue, keep the free lane busy with CTO-designed add-ons, one prepared ahead at a time. Add-on #1 = **S19 THE PAINTING GOES BACK** (10s, ending gag; insert at 7:24 or as the last image) — sheet c1ca1e2.
- Queue order from here: S18 → S2X (chain in flight) → S3a t2 → S2AW → S2AP → S2R-F V1 split → S19 → next add-on.
## 2026-09-10 03:10 — S18 PASS · S2X fired · plaque regeneration plan (CEO 02:40)
- **S18 "THE HAMMER" t1** (chain task-958e2561, fired 02:22:56, rendered ~02:55): CTO review PASS — Dupe alone frontal waist-up, hammer hangs → rises → stops at the shoulder → lowers → at his side by 8s; no mark/plaque/hole; locked; no words. Filed Fix-2 `S18-TheHammer-Fix1.MP4` (id 19xznXXGhzBVMqfYdALdZdk8ydjB9hpxS, md5 64b4d23caa46ea73dd12da5acf098368).
- **S2X** fired 03:04:21 by the same chain.
- **CEO 02:40:** every in-focus brass plaque in Draft 5 is unreadable because no sheet bound the plaque Element. Audit (frames at full res): 6:08 S14 plasterer, 6:44-6:58 S15b/S15c grandmother, tonight's S15e-AB Dupe single → garbled, in focus → REGENERATE. Legible/keep: P1 2:15 ($2,000,000), P3 5:17 ($100,000,000). Far/skip: 7:15. 0:38-0:46 opening = medium, offered to the CEO as optional.
- Post-sale plaques must read $100,000,000: CTO composed `docs/plates/project_absence_prop_tag_100m.png` from the CEO's $2,000,000 plate (same Times serif, engraved). Sheets S14 / S15b / S15c / S15e-AB now bind `@project_absence_prop_tag_100m` (press moved to prose to keep 12 chips) — commits be5a80f, 7264a48. Chain 3 (after chain 2): create the Element from the PNG, then S15e-AB t2 → S14 t2 → S15b t4 → S15c t2.
## 2026-09-10 03:45 — chain 1 closed · S2X PASS · B2 resolved
- **S2X "THE CRACK" insert t1** (task-958e2561, fired 03:04:21, rendered ~03:25): CTO review PASS — locked medium-wide of the hero wall, one small black mark upper-middle, plaque dead centre below (small, out of the CEO's in-focus rule), nobody in frame, sweep flat. Worker flagged the mark's darkness numbers (rule 8) as information. Filed Fix-2 `S2X-TheCrackInsert-Fix1.MP4` (id 1XPvnL3In_Fz69mgavZr01V19GlA5WVb_, md5 f128a29a5030f42a5c0858b4b4b29477).
- **S15e-B2 take 2**: card absent from the grid — per task-1439c7af's report it was cancelled at ~13:19 on 2026-09-09 after sitting queued past 90 min. Nothing to harvest. B2 stays as-is unless the CEO re-orders it.
- Chain 1 (AB → S18 → S2X) closed 03:45; chain 2 (S3a t2 → S2AW → S2AP → V1 split → S19) in flight; chain 3 = task-54e019e3 (plaque Element + AB t2 → S14 t2 → S15b t4 → S15c t2, then V3 wide only if V1 rejected).
## 2026-09-10 04:05 — S3a take 2 PASS
- **S3a "THE FIRST CUSTOMER" t2** (chain 2 task-c72d5ba5, fired ~03:50 with previz S3A as Video 1, 5/5 chips): CTO review PASS — shot 1 locked wide, old man in through the red door, Dupe mid-distance with the cart; ONE hard cut at 5.0s; shot 2 LOCKED side-on (corner diff 1.1, the take-1 drift is gone), old man walks through left→right past the plinth and the vitrine, Dupe behind; whisper empty. Filed Fix-2 `S3a-FirstCustomer-Fix1-take2.MP4` (id 1IQzUmkbQJD3qlYxc7mV1UorPcB8At4Nq, md5 bb78f5ef9a008be235593a2be27cc082). USE THIS, not take 1.
- Lesson: a two-camera marker-bound previz as Video 1 fixes "locked camera" where prose alone did not.
## 2026-09-10 04:50 — PLAQUE PLAN WITHDRAWN (Rule 00 + protected-content flag)
- Chain 3 spawn 1 (task-54e019e3): created Element `project_absence_prop_tag_100m` from the CTO's PIL-edited PNG and staged S15e-AB t2 — Generate refused: "Some reference elements may contain protected content. Check eligibility or remove them to proceed." The CEO's original `project_absence_prop_tag` raised the same toast. Per this ledger's §10 (croc bag, car): a flagged Element is not fixable from the composer.
- **CTO error:** the $100,000,000 plate was composed locally (PIL) and uploaded — Rule 00 (festival: externally created or edited pictures are DISQUALIFYING, may not be uploaded as Elements; the same mistake was made and undone on 2026-08-30). Cleanup worker task-2bbdd10b deletes the Element and its upload from the project; the edited PNG is removed from the repo; the four sheets are restored to their pre-plaque versions (be5a80f^); task-9ce0e0b0 (eligibility retry) cancelled unfired. No generated asset ever used the Element.
- Open for the CEO: the plaque Element (even the original) is flagged, so binding cannot fix the garbled text. Options: (a) on-platform image generation of a plaque plate (credits; may still be flagged — the flag reads text/brand, not origin); (b) an overlay of the plaque in post by the editor (check the festival rule on graphics); (c) accept prose plaques (P1/P3 close-ups read fine; medium shots garble).
- 05:05 cleanup task-2bbdd10b DONE: Element `project_absence_prop_tag_100m` deleted ("Element deleted."), its source upload deleted ("Upload deleted."), both verified absent; the CEO's original `project_absence_prop_tag` untouched. Project is clean of the edited plate. Worker note for the skill: a single click on an Uploads-tab image tile ADDS it as a reference chip — remove via its × before anything else.
## 2026-09-10 05:20 — S2AW take 1 PASS (Wes Anderson tableau)
- **S2AW "THE INTERPRETATIONS, TABLEAU" t1** (chain 2 task-c72d5ba5, fired ~04:36 with previz S2AW as Video 1, 9/9 chips, rendered ~05:15): CTO full-res review PASS — planimetric: five in ONE even row facing the lens (cobalt · student · fur · maroon · magenta), Dupe dead centre far back under the red door mopping, camera locked (sweep 0.6 / corner 0.5), five lines one at a time in order with gaps, deadpan. Mark over the door is larger than the plate's (as in the other wall-POV takes). Filed Fix-2 `S2AW-InterpretationsTableau-Fix1.MP4` (md5 f54539bc4d7698df9cbb49da653fafb1). Editor's alternative to S2AJ for Draft 5 1:31-1:42; S2AP portraits next.
## 2026-09-10 05:45 — S2AP take 1 PASS (portraits, no moderation flag)
- **S2AP "THE INTERPRETATIONS, PORTRAITS" t1** (chain 2, fired ~05:20 with previz S2AP as Video 1, 7/7 chips, rendered ~05:40): CTO full-res review PASS — five frontal WAIST-UP portraits, one person each, dead centre, face ≈20% of frame height, the hall's one-point perspective behind; cuts land ~3.0 / 5.5 / 9.0 / 12.0 s; five lines in order, deadpan. Rendered clean on the same account where the 60%-face close-ups (S2R-F V2) were rejected twice → the framing hypothesis holds. Filed Fix-2 `S2AP-InterpretationsPortraits-Fix1.MP4` (md5 87c8ac6e6a9e795ccd36e6d6f7a05756).
## 2026-09-10 06:50 — S2R-F V1 split REJECTED (copyright) → V3 wide queued · add-on S20
- **S2R-F SPLIT t1** (chain 2, fired ~06:05 with previz + 14 chips, rejected ~06:44): card "NSFW · Credits refunded · Rejected due to copyright restrictions." — third rejection for this scene, all on large-face framings (V2 close-ups ×2, V1 five strips). Not re-fired. **S2R-W wide (13 chips, no close-up) goes next** on a new worker after chain 2's S19.
- Add-on #2 written: **S20 THE WALL ON A PLINTH** (8 s; the cut-out square with the crack exhibited on a plinth, two guards flanking, Dupe mopping round it) — queued after S2R-W.
## 2026-09-10 10:05 — S19 take 1 PASS (add-on, ending gag)
- **S19 "THE PAINTING GOES BACK" t1** (chain 2, fired ~06:50 after a 1080p settings drift was caught, queued ~3 h in the European daytime jam, rendered ~09:55): CTO full-res review PASS — the square hole, Dupe alone with the cart, lifts the abstract painting from the rack, hangs it squarely over the hole (the hole disappears), steps back, straightens it by a fingertip, mops the dust; locked camera; no words. Filed Fix-2 `S19-ThePaintingGoesBack-Fix1.MP4` (md5 43497f0273b77946a58e29d3a791d624). Editor: insert at ~7:24 before the bookend, or as the last image.
- Chain 2 complete (S3a t2 ✓, S2AW ✓, S2AP ✓, V1 split ✗ rejected, S19 ✓). V3 wide + S20 worker (task-a9adf20c) takes the slot next.
## 2026-09-10 11:45 — CEO orders a paid A/B ladder for the auction rejections
- CEO: "ลองแยกฉากประมูลมายิงเลน Create ให้เลย แล้วค่อยหยิบเข้าหยิบออกเพื่อหาสาเหตุจริง … ยิงกี่ครั้งก็ได้ เมื่อติดแล้วให้หยุด แล้วมาเทียบ Prompt" — credit lane (140 per passing fire; rejections refunded), fire variants one at a time, stop at the first rejection, compare.
- Ladder: L0 = V2 faces sheet as-is (13 chips, expected rejection) → L1 = no bidder chips (prose) → L2 = + Carrington chip → L3 = + woman-in-green chip (= V2). First rejection names the variable. Sheets: `s2rf-lab-l1-…`, `s2rf-lab-l2-…`; L0/L3 = `s2rf-fix1-the-battle-faces.txt`.
- V3 wide (free lane, task-a9adf20c) continues in parallel as the framing test.

## 2026-09-10 12:25 — EDITOR INSTRUCTIONS, collected (CEO 12:10: "เดี๋ยวค่อยใส่มาทีเดียวนะ รอฉันสั่งให้จบก่อน" — do NOT send yet)
- CEO asked 12:20 for the clip where Dupe apologises and takes all the blame: Draft 5 only carries the 4-s Fix-1 beat "Sorry, sir. I cracked it. Last hour." at 6:32–6:36. The full apology exists in Fix-2 (ids re-read from Drive, read-only): **S15e-AB** first 6.2 s ("I cracked the wall myself, sir. I will pay for all the damage. I am sorry.", id 175BlZe-DCtng9PdkSR9Vh71iY_r-8RvT) and **S15e-A** 8 s single locked close-up, same three lines (id 1VGx4TGS9SC7qa9fmmATFBkpjoekVQhvK); S15e-ALL (1-teR9Ty1pUifVthEawiySbppd42Yl2Xg) opens with the one-line version. Plaque behind Dupe is garbled in both singles (plaque plan withdrawn 04:50).
- Rows so far (Draft 5 timecodes; REPLACE unless marked INSERT):
  1. 0:10–0:16 → **S0b** cart with castors — sheet a147e52, not generated yet (free lane after S20).
  2. 1:11–1:21 → **S3a t2** (first customer, two-camera).
  3. 1:21 → **S3b FULL 20 s** (cane-tap laugh) — CEO: "อยากใส่เต็มฉากเลย".
  4. 1:31–1:55 → **S2AW + S2AP** (Wes Anderson interpretations; S2AJ as fallback).
  5. 3:18–3:39 → **S2PT t2**; 3:39–3:52 → **S2PU**.
  6. INSERT **S2X** crack insert at 0:44 / 1:36 / 1:48 / 3:58 (editor's choice of length).
  7. 4:42–5:06 auction → pending V3 wide (free lane) or the credit-lane ladder winner.
  8. 6:32–6:36 → **S15e-AB 0–6 s** (or S15e-A 8 s) — the full apology, NEW today.
  9. 6:40–7:16 duplicated cheque takes → **S15e-AB 6–20 s** (keep S15d 6:36–6:40).
  10. INSERT **S19** at 7:24 (painting goes back); INSERT **S18** after the 7:36 bookend; **S20** pending (~7:22).
## 2026-09-10 12:45 — LADDER: L0 REJECTED (expected) · L1 PASSED → the bidder Elements, not the close-up framing
- Worker task-1755ef77 (winbox spawn 2, branch head a90fa41): **L0** = V2 sheet as-is, 13 chips, fired 11:57 → `NSFW · Credits refunded · Rejected due to copyright restrictions` (asset 11e1da83…). **L1** = same five close-ups + full shot, 11 chips, bidders as prose (no `@gentleman_e`, no `@project_absence_char_woman_c`), fired 12:06 → PASSED, landed 12:25 (~19 min), **130 credits spent** (first paid fire of the project). Asset 3d33d133-a919-4477-9cf7-f74e6b3fb386, `hf_20260910_050627_3d33d133-….mp4` 19,929,436 B md5 c8774351b5c8e11ddff30c289510c7dc.
- CTO review at full res (sweep cuts 2.8 / 5.6 / 8.6 / 11.8 / 14.4 s = five close-ups then the full shot; whisper: "10 million | 15 | 20 million | 25 | 50 | Oh, my God!" — all six lines, in order): close-ups clean — one face each, Carrington-by-prose (white hair swept back, cream stand-collar suit, two gold front teeth) ×3 and the woman in green ×2, both consistent shot to shot; full shot 14.4–20 s: Valder centre with cane, guards, visitors, cleaner + cart on the far left, woman in green on the right — but **no separate Carrington**: the front-left figure is the registrar (ledger, pen, gloves), so the full shot is 12 figures and the bidder on the left is missing. Verdict: **PASS for the five close-ups (0–14.4 s), full shot usable only as a crowd reaction**.
- What this settles: the same large-face framing passes when the two bidder chips are absent → the close-up framing alone is NOT the trigger (correction to the 09:45 answer). The likeness check fires on a face generated from one of the two bidder Elements at close-up size (they pass in wide shots, S2R-W-style). L2 (Carrington's chip back) is firing now; L3 (woman in green's chip) follows if L2 passes.
- Repo note: the worker committed the 19.9 MB MP4 under `docs/reports/frames-s2rf-lab/L1/` — drop it from the tree at close (keep the frames).
- 12:50 Filed Fix-2 `S2RF-L1-TheBattleFaces-Fix1.MP4` (id 1ykJnHS2eDxoVUw1vjV0TUhbI12pe3NJi, md5 c8774351b5c8e11ddff30c289510c7dc) — an option for the auction row (close-ups 0–14.4 s). **L2** (Carrington's chip back, 12 chips) fired ~12:40 (a4ea95d).
## 2026-09-10 13:10 — L2 PASSED (Carrington's Element cleared) · L3 fired · CEO orders S2R-Q, the 10-s bids-only cut
- **L2** (Carrington's chip back, Madame as prose, 12 chips) fired 12:32 → PASSED 12:43, 130 credits. CTO review at full res: cuts 2.8/5.8/8.6/11.8/15.4 s; whisper with word timestamps: 10 million · 15 · 20 million · 25 · 50 · "Oh my God!" in order (a "No!" in the first pass was a misread of "Twenty-five" — one energy burst at 10.0–10.75 s); close-ups clean, Carrington now from his Element (white hair, gold teeth) — the bodyguard's black shoulder intrudes at the right edge of his first close-up; full shot: Carrington distinct on the far left with cane and bodyguard, registrar separate, 11 of 12 cast (Dupe missing, his cart present), no duplicates. Verdict: **PASS — the best auction take so far**. Filed Fix-2 `S2RF-L2-TheBattleFaces-Fix1.MP4` (id 1EzlOVgRvHjMGWs7x6h4DNmc93QcBTys3, md5 07ea7a91277ade60d7505fdb5ad9c340). So Carrington's Element is NOT the trigger either.
- **L3** (= L0 sheet, both bidder chips, 13) fired 12:49 (asset 380b3f37…) — the last rung; it tests Madame's Element (`project_absence_char_woman_c`). Credits so far 260.
- **CEO 13:00**: "ฉากนี้เอาแค่เป็นฉากประมูลอย่างเดียว ตัดฉาก Valder ดีใจเอง เอาแบบ Cut แบบนี้เลย ใส่ Valder @Element + Madam @Element" + "Copy ClipBoard ให้เลย … ขอแบบสลับกันพูดไวๆ ขอ 5s-10s ไม่เกินนี้" → sheet `s2rq-fix2-the-bids-quick.txt`: 10 s, six close-ups / five hard cuts at 1.6-s intervals, five bids (10M · 15 · 20M · 25 · 50), Valder's Element used as a silent deadpan head-turn in the last shot (the delighted beat dropped), cast 3 + room, 4 chips. Paste block copied to the CEO's clipboard in the composer's `@[name](id)` form (ids: gentleman_e 4da73a7b…, woman_c 2a48c5d1…, valder 0a7ee130…, loc_hall_big_e aba3af6d…). Madame = MADAME THIBAULT = `@project_absence_char_woman_c` (s2q sheet).
- **Free lane**: worker task-0fe8ed87 raised a BLOCKER 13:00 — S2R-W (asset d58ee0c0…, fired 10:02 by the earlier operator) still `queued` after 3 h; it did not cancel (correct). Decision: keep waiting; replace the worker with a patient harvester.
## 2026-09-10 13:15 — CEO STOPS credit-lane firing ("ตอนนี้ให้ Worker หยุด Generate โดยใช้ credit ก่อน")
- Ladder worker task-1755ef77 killed on winbox (pid 26544), tab claim released, task cancelled, branch merged. **L3 (asset 380b3f37…, fired 12:49, both bidder Elements) was still in flight** — it will land on its own in the grid; nobody harvests it. If it shows `NSFW / Credits refunded` the refund is automatic and the ladder's answer is complete (Madame's Element = the trigger); if it PASSES, 130 more credits were spent and the trigger is the *pair* of bidder Elements together. Read the card later, do not re-fire either way.
- **Credits spent today: 260** (L1 + L2, 130 each; L0 refunded). No further credit-lane fires without a new CEO order.
- Standing rule restored: FREE lane (Unlimited) only.
## 2026-09-10 13:20 — CAUSE FOUND: `@project_absence_char_woman_c` (Madame's Element) is the moderation trigger
Two more cards landed and closed the question — five data points, one variable:

| fire | chips | Madame's Element | framing | result |
|---|---|---|---|---|
| L0 (11:57) | 13 | **bound** | close-ups | REJECTED |
| L1 (12:06) | 11 | absent (prose) | close-ups | PASSED |
| L2 (12:32) | 12 (+Carrington) | absent (prose) | close-ups | PASSED |
| L3 (12:49) | 13 | **bound** | close-ups | **REJECTED** (asset 380b3f37…, credits refunded) |
| S2R-W (10:02) | 13 | **bound** | **WIDE, no close-ups** | **REJECTED** (asset d58ee0c0…, `NSFW / Credits refunded / Rejected due to copyright restrictions.`) |

- Every rejection has her Element bound; every pass has it absent. **Framing is not the variable** — S2R-W was the wide test and it was rejected anyway. Carrington's Element (`gentleman_e`) is cleared by L2. This also explains the three earlier auction rejections (07-09 Sep), all of which bound her.
- **Rule from here: never bind `@project_absence_char_woman_c` again.** Madame is written as prose — the exact L1/L2 wording, which renders her consistently (green leather gown, pompadour, cat-eye sunglasses) shot to shot. Her Element should be treated as dead; do not re-create it from the same plate.
- Credits: **260 total** (L1 + L2). L0, L3 and S2R-W were all refunded. No credit-lane fire since the CEO's 13:15 stop order.
- `s2rq-fix2-the-bids-quick.txt` patched to v2 the same minute: Madame's chip removed, prose in, 3 chips (loc_hall_big_e, gentleman_e, project_absence_char_valder). The CEO's clipboard was re-copied before he fired it.
- **Free lane**: S2R-W's rejection freed the slot; harvester task-3b2070ff fired **S20** at 13:1x (asset 7a1c376d-5bc6-477e-9173-340be87c0663, 4/4 chips), S0b next.
### 13:40 — CORRECTION to the 13:20 entry (CEO challenged it: "ใช่หรอ")
The 13:20 claim was overstated. Two counter-facts I failed to check before writing it:
- **`@project_absence_char_woman_c` has PASSED on this lane, twice.** The S2R jump-cut sheet
  (`s2r-fix1-the-battle-jumpcut.txt`) binds her, and it rendered — PROMPT B on 2026-09-08
  ("13 chips, previz on. Rendered.") and again as **S2R-JC take 4** on 2026-09-09 (partial pass,
  best of four). Same Element, same lane, same 13-chip set as today's L0/L3/S2R-W.
- **Chip count is also perfectly correlated** with today's outcomes (13 → rejected 3/3, ≤12 →
  passed 2/2) because her chip was always the 13th one added. The ladder never separated
  "her Element" from "the 13th chip". Only the 8-9 Sep renders break that tie, and they break
  it against the chip-count theory too (13 chips rendered fine then).
What actually survives:
1. **Framing is ruled out** — same 13 chips, wide (S2R-W) and close-up (L0/L3), all rejected;
   L1/L2 close-ups passed. This is solid and does not depend on the rest.
2. **Chip count is ruled out** — 13 chips rendered on 2026-09-08.
3. **Her Element is a strong risk factor, not a proven cause.** The check reads the OUTPUT
   (that is why the same prompt can go either way): binding her plate raises the chance the
   rendered face trips the likeness check, but it is not deterministic. Something may also have
   tightened on the platform between 09-09 and today — five straight rejections today vs two
   passes on 08-09 — but that is a hypothesis, not measured.
4. **What IS measured: the prose version passes.** L1 and L2, two for two, and the rendered
   Madame is consistent shot to shot. That is the reason to use prose — a measured pass rate,
   not a proven law.
Sheets and the memory entry corrected accordingly; the "never bind her again" rule is downgraded
to "prefer prose for her in this scene; if a future sheet needs the Element, expect a coin flip."
### 14:05 — S2PT take 2 re-review (CEO asked whether the cart has wheels): wheels YES, but a SECOND CART I missed
- **Wheels: correct.** Four swivel castors with rubber tyres, clearly visible at full res at 7 / 11 / 19 s (3× crop of frame 11 kept at `scratchpad/review/cart/`). The wheel-less-cart defect is specific to Draft 5's 0:10-0:16 shot, which S0b replaces — S2PT is fine on that count.
- **DEFECT I missed on the 01:35 PASS: there are TWO carts in frame** from ~7 s to the end. Dupe pushes the red one; a second cleaning cart — its own chrome frame, its own bottles, its own orange bucket, its own painting standing in the rack, its own castors — stands at frame right beside the mustard armchair. Not a reflection: both are visible together at different depths on the blue rug in the same frame. This violates the sheet's own negative "no second cart".
- **How I missed it:** the 01:35 review counted PEOPLE (the take-1 defect was a duplicate bodyguard) and never counted PROPS. Same class of error as the tile-level review that missed the duplicate bodyguard. **Review rule extended: count every named prop the way we count cast — by its parts, at full resolution, in at least two frames.**
- Impact: mild on its own (frame edge, reads as another trolley parked in the gallery) but it undercuts the cart's uniqueness, which matters more now that S2AC makes the cart the object the collectors worship.
- Options put to the CEO: accept as-is · reframe in the edit (costly, the shot is a lateral track at 720p) · take 3 with "ONE cart" stated three ways, the same fix that removed the duplicate bodyguard on the first retry (cost: one free-lane slot).
### 14:30 — CEO orders S2PT take 3 and a queue jump ("ยิงเทค 3 ใส่ 'รถเข็นคันเดียว' ย้ำ 3 แบบในบท" · "ใช้เลนฟรี แทรกคิวก่อนได้เลย")
- Sheet bumped to **v3** (cb18797): the countable-cast paragraph now has a countable-PROPS twin, and ONE CART is stated three ways — a count ("Count the carts: ONE"), an ownership rule ("if Dupe is not pushing it, it is not there"), and a placement ban ("nothing on castors stands parked anywhere — not by the armchair, not by the rug, not at the edge of the frame"). The old one-clause negative grew to eleven. Nothing else in the sheet changed; take 2 stays usable as the fallback.
- Free-lane order is now **S20 (queued, asset 7a1c376d…) → S2PT t3 → S0b**. Worker task-3b2070ff was killed and merged to insert the jump (remote workers cannot be messaged); replacement **task-fc063e0e** spawned on winbox with the previz-reuse instruction (`S2PT-Previz` should still be in the composer's Uploads → Videos panel; Drive copy 1LYJcwt7N77JXOFYFmBfDpiikZHvswrL0 if not, and a BLOCKER rather than firing without it).
- The take-3 review order now leads with **count the carts in every frame, and crop the right third at 7/15/19 s** — the exact check that would have caught the defect on take 2.
## 2026-09-10 16:10 — MODEL LAB: Seedance 2.0 Fast + Mini at 15 s (CEO authorized the credit spend)
- CEO 16:05: "ทดสอบยิงจริง 15s เลย … ทดสอบด้วย Mini ได้เลย … Mini 15s แค่ 38 credit … ลองจริงได้เลย" then "ลองฉากประมูลนะ แบบ Jump Cut นะ".
- Measured prices already on file (composer, 720p, credit lane): **2.5** 5s 33 · 10s 65 · 15s 98 · 20s 130 · **2.0** 5s 23 · 10s 45 · 15s 68 · **20s not offered, the model caps at 15s** · **2.0 Fast** ~17/5s. Unlimited does NOT cover 2.0 — toggling it opens a purchase modal, so 2.0 costs credits while the 2.5 grant is still free until 11 ก.ย. 06:59.
- Test payload `s2rq15-lab-the-bids-jumpcut-15s.txt` (213506c): the auction jump cut compressed 20 s → 15 s with all five bids kept (2.5 s each); only the 20 s version's full-shot ending was dropped, and the editor can take that beat from the 2.5 footage. 3 chips (loc_hall_big_e, gentleman_e, valder); Madame stays prose.
- Worker **task-ce0d3be7** on winbox, credit lane, TWO fires only: 2.0 Fast then Mini. Caps written into the brief — abort above 70 credits (Fast) or 55 (Mini). Runs alongside task-fc063e0e, which owns the free lane; the two lanes do not share a slot.
- **The finding that matters most is not the picture:** whether the cheap models accept `@Element` chips at all. If they refuse or drop them, the cheap models are ruled out for this film no matter the price, because the whole film depends on the same faces across 40+ clips. The brief tells the worker to stop and report rather than fire if that happens.
- Review order is built around likeness drift across hard cuts (Carrington's three close-ups at 0/5/10 s), not general prettiness.
## 2026-09-10 16:35 — MODEL LAB fire 1: Seedance 2.0 Fast 15 s — PASS, and it is not a downgrade
- Exact model names in the picker: **"Seedance 2.0 Fast"** and **"Seedance 2.0 Mini"**, both capped at 15 s. **Both accept `@Element` chips normally** — 3/3 bound, 0 error chips. That was the gating question and it is answered: the cheap tiers are not ruled out.
- Fired 16:01, **53 credits** (predicted ~51), landed **~4.5 min later**. `hf_20260910_090100_37476944-….mp4`, 32,031,067 B, md5 92eda84b43fb5ce5d5a414ae3eba5820, 1280×720, 15.0 s.
- **CTO verification (I did not trust the worker's frame mapping and was right to check, then wrong about what I found).** The worker sampled at 1.2/3.7/6.2/8.7/11.2/14 s; two of those land exactly on cut boundaries, and the 6.2 s frame showed Madame where the sheet wants Carrington, which looked like a swapped alternation. Cut sweep (fps 10, grey 64×36, diff > 15) gives the real cuts at **2.0 / 4.0 / 6.2 / 8.7 / 11.4 s**; re-sampling each shot's true mid-point (1.0 / 3.0 / 5.1 / 7.4 / 10.0 / 13.2) shows **C · M · C · M · C · Valder — the alternation is exactly right.** My suspicion was a sampling artefact, not a model defect.
- Review: six shots, five hard cuts, no dissolve · Carrington identical across his three shots (Element) · **Madame identical across her two from PROSE alone** · one face per shot, no intruding shoulder · Valder deadpan, correct blazer/scarf/round tinted glasses, does not speak · whisper: "10 million, 15, 20 million, 25, 50" — five bids, right order · detail (skin, hair, leather sheen) reads as high, not cheap.
- **The one real deviation from the sheet: the background.** The sheet asks for "a plain warm cream gallery wall softly out of focus, nothing else in frame"; the model rendered the full hall with chromium columns receding, noticeably sharper and more symmetrical than either 2.5 take. It looks good — arguably more Wes Anderson — but it does **not match the 2.5 L1/L2 footage**, so 2.0 Fast and 2.5 clips cannot be intercut inside the same scene without a visible jump. Pick one model per scene.
- **Numbers that matter more than the picture:** 53 vs 98 credits at 15 s (**-46%**) and **~4.5 min vs 11-19 min render**. With the free lane jammed all day (0 usable clips since morning, S20 queued 162 min), the render speed may be worth more than the discount for finishing before the 11 ก.ย. 06:59 cutoff.
- Fire 2 (Mini, 38 credits) next. Running total for the lab: 53 credits.
## 2026-09-10 16:50 — MODEL LAB fire 2: Seedance 2.0 Mini 15 s — works, but it is the draft tier
- Fired 16:12, **38 credits**, landed in **under 4 min**. `hf_20260910_091234_c6f16959-….mp4`, 8,140,097 B, md5 b9571603e39b9b8c536bf6dc92cc6ddc. Model switch preserved the pasted prompt and all 3 chips — no re-paste needed. **Mini has no High/Medium/Low quality control at all**; that row is simply absent from its settings.
- **CTO verification** (cut sweep + true mid-points + whisper, same method as Fast): cuts at **1.7 / 3.5 / 5.4 / 7.5 / 10.4 s** — furthest drift of the three, leaving a 4.6 s final Valder shot. Audio clean: "10 million | 15 | 20 million | 25 | 50", five bids, right order, better separated than Fast's. Both faces identical across every cut; 3/3 chips bound.
- **Measured against Fast on the identical prompt** — bitrate **4.31 vs 16.97 Mbps** (Fast is 3.9×), file 8 MB vs 32 MB, saturation **0.408/0.484 vs 0.475/0.571** (Fast +16-18%), edge energy slightly HIGHER on Mini at a quarter the bitrate = over-sharpening and compression, not detail. Skin reads waxy on a large face. **Mini also ignored the framing spec**, pulling back to ~45% face height where the sheet asked for 60%.
- This confirms the CEO's eye-read at 16:40 ("Fast ดีกว่า Mini มาก … เห็นได้ชัดว่าถูก Upscale มา สีสันสดใสกว่าต้นฉบับมาก") with numbers: Fast is both more saturated and genuinely higher-bitrate; Mini is cheap-looking in the literal sense.
- **Lab total: 91 credits (~$3.8).** Both cheap tiers bind Elements and hold identity across hard cuts — the question that could have ruled them out is settled. Rule 14 in the skill now carries the full table.
## 2026-09-10 17:10 — lab closed · S20 landed after 193 min · S2PT take 3 hit the viewport lock-up twice
- Model lab **task-ce0d3be7 closed and merged** (3f0967e). Verdict on the branch: both cheap tiers usable, Fast is the one to reach for. Lab cost 91 credits total.
- **S20 left the queue at ~193 min and COMPLETED** — the free lane's first delivery since morning. Worker is harvesting; CTO review at full res still to come.
- **S2PT take 3 could not be staged: the composer tab hit the documented ~126×67 "MOBILE ACCESS COMING SOON" viewport collapse TWICE**, on two different fresh tabs. The worker recovered correctly each time (fresh tab, never resize) and has pivoted to harvesting S20 first, leaving S2PT to a later attempt — the right call, harvest needs no composer.
- Load check on winbox at the time: **15 claude.exe processes totalling ~1.2 GB and 18 Chrome processes.** Cross-referenced every pid against tasks.db: none of them are orphans from this session's terminal tasks (all of those are dead), so they belong to other sessions or are children of the live worker — **not mine to kill (IRON §33)**. Killing the finished lab worker did free one session's worth of tabs and memory, which is the only lever this session had.
- Free-lane order from here is unchanged: **S2PT take 3 → S0b**, with the Unlimited grant ending 11 ก.ย. 06:59.
## 2026-09-10 17:20 — S20 "THE WALL ON A PLINTH" take 1 PASS (add-on)
- Fired 13:15 on the free lane, queued **193 min**, rendered ~17:00. Asset 7a1c376d-5bc6-477e-9173-340be87c0663, `hf_20260910_062355_7a1c376d-….mp4`, 7,130,077 B, md5 6a5ac768e5fd6082d33f81663d9d9f7d, 1280×720 @ 24 fps, 8.05 s.
- **CTO review at full resolution, verified independently of the worker's summary:** cut sweep (fps 8) finds **NO cut — one continuous shot**; ceiling-corner crop drift **1.13/255** (locked, threshold 3); whisper finds **no speech**, audio rms 264 = room tone only, as the sheet demanded.
- REVIEW ORDER: (1) locked symmetrical wide down the hall, red doors at the vanishing point, plinth dead centre ✓ (2) rough-edged cream plaster slab upright on the plinth, black crack on its face, nothing else on it ✓ (3) two navy guards, one each side, at attention, motionless ✓ (4) Dupe mopping a slow circle around the plinth — behind it at 0.5 s, in front at 3.5 s, behind again at 7.9 s ✓ (5) no plaque, no price, no crowd, no dialogue ✓.
- **Prop count (the S2PT lesson applied): exactly ONE cart**, parked left of the plinth, one bucket, one mop. No duplicates anywhere in frame. Cast exactly three.
- One deviation, judged an improvement: the sheet asked for "one short thick black crack… small and dead centre"; the model rendered a tall jagged crack running most of the slab's height. At this camera distance the specified small mark would have been invisible, so the larger crack is the right call for the shot. Not a re-shoot.
- **Verdict PASS.** Filed Fix-2 `S20-TheWallOnAPlinth-Fix1.MP4` (id 12TydkMqXusvLoyuDbkHvyoC5h4iNLBRh). Editor row: INSERT at ~7:22.
## 2026-09-10 18:41 — EDITOR INSTRUCTIONS SENT (LINE, on the CEO's order "ส่งให้ได้เลย" / "เข้า Line ได้เลย")
- Full sheet committed at `docs/reports/absence-editor-instructions-20260910.md` (d2c17b1). Sent to the editor in the Oikill LINE chat at 18:41 as one message; LINE rendered the Drive link with a "Fix-2 – Google ไดรฟ์" preview card, which confirms the folder id resolves.
- **CEO's decisions, recorded verbatim in effect:** hold 1:31–1:55 (interpretations) and 3:18–3:39 (tour) — "รอฉากที่ดีที่สุดก่อน" · S2PU keep only through the startled beat, **cut before Dupe resumes mopping** ("ไม่ต้องเอาฉากที่ dupe ทำความสะอาดมา ตัดภาพไปฉากอื่นได้เลย") · auction **L2, 15 s only, tightened** · **"อย่าลืมซ้อนฉาก Dupe ขอโทษและจะรับผิดชอบลงไปด้วย"** — sent as its own emphasised row · everything else he did not comment on: send.
- Ten rows are actionable now; three are marked as coming (S0b, S21, S22); two are held. The message also warns off the two non-take2 files that are failed takes.
- Method note: typed line by line with shift+Return (clipboard paste never lands in LINE desktop), verified the whole body on screen before the single Return that sends. The Drive folder link was sent once instead of ten per-file links — far fewer characters to mistype, and the preview card proved it resolved.
## 2026-09-10 19:35 — S21 "THE NEWS WALL" take 1 PASS, and its "defects" are improvements
- Fired 19:03 on the credit lane, **28 credits** (predicted 28), Seedance 2.0 Fast, 8 s, 2 chips. `hf_20260910_120334_71ccced9-….mp4`, 10,945,410 B, md5 8b89868b7d47d0aa10c6a58c061dd9cf, 1280×720.
- **CTO verification, independent of the worker:** cut sweep — **no cut, one continuous shot**; top-left corner crop drift **1.15/255** (locked, threshold 3); whisper — **"$100 million for a crack in a wall." / "The collector, Maximilian Valder, declined to comment."**, both scripted lines, in order, matching the audio already in Draft 5 at that slot. Wall matches the CEO's chosen variant A exactly: same uneven stack, same chrome ball, same credenza and cardboard box, nothing rearranged. Nobody in the room, no reflection of a person, no readable word anywhere.
- **The operator flagged two deviations from my sheet and both make the shot better.** (1) The screens go OUT OF SYNC — at 4 s some carry the building while others still carry the newsreader, at 7.8 s most carry Valder while a few lag. My sheet forbade that; a real shop wall of second-hand sets is exactly that untidy, and the stagger reads as life rather than error. (2) The inserts render FULL-FRAME on each set instead of as a small square beside the newsreader's head. At this camera distance the inset I specified would have been a few pixels and invisible; full-frame makes the museum, then Valder's face multiplied across thirty screens, land instantly — which is the whole point of the shot, that the press has decided whose story this is.
- **Verdict PASS.** Filed Fix-2 `S21-TheNewsWall-Fix1.MP4` (id 1y2i7LCjjdcqgYYPQ0Dp5gelrzOcTsjw4).
- **Sent to the editor on LINE at 19:35** as row [11]: replaces 5:19–5:27, the clip is 8 s and the slot is 8 s so it goes in whole, no trim. The previous message (18:41) had already been read.
- Lesson worth keeping: a sheet's negatives encode what I *predicted* would go wrong, not what the shot needs. When a model breaks one and the result is better, the sheet was wrong — say so plainly instead of re-firing to enforce it. Credits today: **379**.
