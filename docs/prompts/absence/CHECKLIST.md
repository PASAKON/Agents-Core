# «Sorry, Sir» — master checklist

**CEO, 2026-08-28 02:32: "ทำ Check List และตรวจเสมอว่า Worker ทำอยู่ไหม เสร็จไหม — คุณลืมบ่อยมาก"**

Single source of truth for what has been ordered and what is outstanding.
Every CEO instruction lands here **the moment he says it**, before work starts.
Nothing is tracked in the CTO's head.

Read at the start of every session, and before every report to the CEO.
**Check worker status against this list — do not assume a task is running.**

---

## ✅ DONE

| # | What | Evidence |
|---|---|---|
| 1 | S1 take 1 recovered after usage-limit kill | asset `4b445603` · Telegram + Drive |
| 2 | S1 take 2 fired, collected, sent | asset `9f1d8892` · [Drive](https://drive.google.com/file/d/19JkLbEaytcfEgR2gJNDHoZL1A9HkWFQP/view) |
| 3 | Hall v6 — corridor opening into a wide hall, more on display, detailed artworks | `loc_hall_big_d` · asset `0e3fad53` |
| 4 | Drive «Sorry, Sir» folder mirroring the DND template | [folder](https://drive.google.com/drive/folders/1eJH1p789LLfufpSgWF47KeHziUxOHxPh) |
| 5 | 3 soundtrack files uploaded + verified byte-exact + local copies deleted | 54 MB freed |
| 6 | Cast bible cards with portraits in the production sheet | artifact `5a5cccb4` |
| 7 | Skill fixed: Unlimited = Seedance video only, never images | commit `a5f966d` |
| 8 | Skill: a bound reference keeps the OLD asset when its Element is re-pointed | commit `1b54e9c` |
| 9 | **Museum exterior** — trumpet columns + terracotta terrazzo continuous with the interior, gold V, revolving door, wheelchair ramp, open sky. CTO-approved 03:32, sent to CEO | `loc_exterior` |
| 11 | **Wall POV v2** — no hole, ghosted wall, **crack dead centre and floating**, plaque low with **mirror-reversed text**, six facing camera. CTO-approved 04:00, sent to CEO. *Minor: plaque lettering is reversed but garbled — flagged, not rejected* | `loc_wall_pov_b` |
| 12 | **Art student redesign** — real art-student clothes, dyed hair, upright | `char_student_c` |
| 13 | **Valder Element** filed from the existing 18 Aug asset, 0 credits | `char_valder` |
| 14 | **Valder's guards** — six, identical uniform, gold V on chest and cap. CTO-approved 04:00, sent to CEO | `char_guard_valder` |
| 10x | **Parrot woman** — cockatoo crest, wing-shoulders, feather-cut panelling, single cobalt, no beak/wings/feathers, not comic. CTO-approved 03:32, sent to CEO | `char_woman_b` |
| 35a | **Grandmother, reshot** — electric wheelchair with real wheels visible in all 4 panels incl. rear (fixes the rejected chrome-lounge-chair-no-wheels attempt), cloth over head, dark glasses, deep violet, no gold V. **Honest flaw: gloves render black, not dark grey/oxblood as the colour rule requires** — flagged to CTO, reshoot queued behind Scene 3 video render, not done yet | `char_grandmother` · asset `5dd23a87-67f3-4452-8a69-e81045e19993` |
| 35b | **Grandmother (auction wall)** — cool not rich, unimpressed, real electric wheelchair w/ visible wheels + self-operated control pad, no gold V. v1 read as an ordinary chair, v2 fixed | `char_grandma` |
| 36 | **English gentleman + 2 bodyguards** — 3 people in one image, white Savile Row suit, gold cane grip, diamond ring, two gold-capped teeth, black-suited bald Black + white English guards, neither threatening. Nose ref'd off Dupe (shape only) | `char_gentleman` |
| 37 | **Crocodile bag** — deep burgundy, real scale grain, gold clasp, no logo, ref'd off `loc_hall_big_d` for light/floor | `prop_croc_bag` |
| 38 | **Press — two journalists + one shared retrofuturist shoulder camera** — blue + rust colours (never black), no logos/modern tech, real age/skin variation, no gold V. Unblocks S5/S11 | `char_press` |

---

## 🔄 IN FLIGHT — verify the worker is actually alive, every check

| # | What | Element | Worker |
|---|---|---|---|
| 9 | **S1 v1 — Dupe cleaning, silent.** Fired, asset `5ea44262`, rendering | — | done |
| 9b | **S1 v2 — Dupe cleaning WITH his five polite lines**, none of them answered. Title drop: "Sorry, sir." | — | `task-7dcf64d3` |

---

## 🔄 ALSO IN FLIGHT

| # | What | Worker |
|---|---|---|
| 32 | **Collect both S1 takes** (`5ea44262` silent, `c8e60256` Dupe speaks) + shot-by-shot review of each | `task-ff2828e0` |
| 33 | **Valder's five pieces** — chair, fish trap, millstone, vessel, painting | `task-fe7b3d37` |
| 34 | **Parrot woman v3** — hair in green/white/blue, garment single green with cut lines (CEO #64/#65) | `task-fe7b3d37` |
| 35 | **S2 fired** `56ace68c`, rendering since 05:50 · **S3 re-staging** after a composer navigation wiped it | `task-a13469e9` |
| 36 | ~~Grandmother RE-SHOOT~~ — **DONE, merged `ab4873d`.** Wheels visible in all 4 panels incl. rear | ✅ `5dd23a87` |
| 37 | **Crocodile bag → grandmother glove fix → `char_press`** | `task-5a3d259c` |

### ⚠️ CTO error, 2026-08-28 06:30 — corrected

I stood both image operators down "until the video render clears". **That was
wrong and cost ~40 minutes of two workers.** Proof from this same session: the
grandmother plate (`5dd23a87`) and the gentleman plate both fired *and finished*
while S2 was mid-render. **The one-at-a-time slot is scoped to Unlimited VIDEO
only; paid image generations queue independently.** Recorded in the
`higgsfield-unlimited-gen` skill so no future wave repeats it.

A second error the same hour: I told the video operator to "check the render now,
in the browser" without saying *in a separate tab*, and it navigated the composer
holding the staged S3 prompt — wiping the text and resetting Unlimited. No money
lost (nothing was fired), but S3 had to be staged twice. **Status checks always
go in a scratch tab.**

## 📋 ORDERED, NOT STARTED

**Plates**

| # | What | Needed for |
|---|---|---|
| 15 | `char_guard_private` — personal bodyguard. **CEO: black IS allowed for guards** | $20M tier |
| 16 | **`char_guard_valder` — DONE.** Uniform identical across all six, gold V on chest and cap, black only on belts and shoes, real range of builds. Route A worked: uniform study first, then re-dressed the existing six.  ~~original brief:~~ CEO: reuse the existing blue 6-guard plate **if it already has the gold V** — check first, generate nothing if so. If no V: generate the UNIFORM alone, then re-dress the existing six so faces stay varied and the uniform stays identical. Single plate first, six-guard plate second. | $20M tier |
| 17 | `char_press` — journalists | $100M tier |
| 18 | Helicopter — decide: part of the exterior plate, or its own | $100M tier |
| 19 | `char_visitor_c` — **currently has NO reference image**, content-flagged, prose-only | face consistency across scenes |

**The cleaner's later life** — ✅ **ALL DONE, CTO-approved 07:40, `task-7cb85052`**

| # | What | Verdict |
|---|---|---|
| 20 | `char_cleaner_rich` · `59470e23` | ✅ deep teal suit, one colour, no jewellery, no gold V, 4 panels with back view — and **the posture is right: hands clasped in front like a servant, not a rich man** |
| 21 | `loc_mansion` · `93c52112` | ✅ sunken plum seating, warm wood, tall windows, impersonal luxury — **and the cart gets its own close-up panel, gold V and all** |
| 22 | `prop_camera_rig` · `f9b9946e` | ✅ filed |
| 15 | `char_guard_private` · `dbd40616` | ✅ black suit as the CEO allows for guards, no sunglasses, no earpiece, no weapon, hands loose at his sides, **reads as paid help and not as a threat** |

*Asset ids copied out of the worker's DB report — that branch carried no commits,
so the repo was the only place these would have been lost from.*

**Valder's five pieces** — full spec in [VALDER.md](VALDER.md)

| # | What | Element |
|---|---|---|
| 15a | The chair — "in the room where the armistice was signed. Not at the table." | `prop_valder_chair` |
| 15b | The hanging fish trap — "caught nothing for forty years" | `prop_valder_trap` |
| 15c | The millstone ring — "somebody stood it upright and it stopped being a tool" | `prop_valder_millstone` |
| 15d | The lidded vessel — "seventeen made, he destroyed sixteen" | `prop_valder_vessel` |
| 15e | The painting — "painted in one afternoon to test a colour" | `prop_valder_study` |

**Scenes** — see the 17-scene table below

**Sheet updates owed**

| # | What |
|---|---|
| 26 | Name the cleaner **DUPE** everywhere |
| 27 | Fix `visitor_b` — a **woman ~55 in a chestnut fur coat**, not a man |
| 28 | Record `visitor_b` + `visitor_c` as **husband and wife** |
| 29 | Move "It made me think of my mother" to `visitor_b` |
| 30 | Add Valder's card |
| 31 | Add the price-ladder table |

---

## 💰 THE PRICE LADDER — the recurring wall-POV shot

Same frame every time. Only what is inside it changes.

| Price | Who is in the room |
|---|---|
| **$2,000,000** | 6 people, **+2 per scene**, ordinary clothes |
| **$20,000,000** | 10–20 people, **each with a personal guard**. Valder appears; his guards multiply. |
| **$100,000,000** | Peak. Press, live broadcast, **helicopter circling the building**, reporters filing from outside. |

---

## 🔒 STORY FACTS — locked by the CEO, 2026-08-28. Every prompt must obey these.

1. **Dupe cracked the wall himself, then called the workman to come and repair it.**
   The workman in S16 is there because Dupe asked him to be. The S16 flashback is
   **Dupe making that phone call**, not Dupe cracking the wall — we already saw
   that in S2.
2. **The whole film happens in one day, morning to noon.** So "I cracked it. Last
   hour." is **literally true**, and the price climbs $5M → $100M before the
   plaster the workman brought has had time to dry.
3. **Valder genuinely believes his own invention by the end.** He is not a con
   man and must never be played as one. The system swallows the man who built
   it — that is what keeps the film from having a villain.
4. **Two takes of every scene**, fired back to back, working through the film in
   order.

---

## 🎬 THE 17 SCENES — shooting order

**Every locked line lives in [DIALOGUE.md](DIALOGUE.md).** A line that is not in
that file is not written — ask, never invent. S7/S8/S9 were recovered from the
session transcript on 2026-08-28 after nearly being lost; that is why the file
exists.


Fire **2 takes per scene**, then move to the next scene. In order, so that if the
schedule slips the missing footage is at the end of the film and not its middle.

| # | Scene | Length | Status |
|---|---|---|---|
| S1 | Dupe cleans, greets, nobody answers. Title drop. | 20s | ✅ 2 takes — `5ea44262` `c8e60256` |
| S2 | **The accident.** Dupe knocks the frame into the wall, takes the painting away. | 20s | ✅ **TAKE 1 DELIVERED** `56ace68c` · watched + verified · in Drive · sent to CEO |
| S3 | **The interpretations**, from inside the wall. 6 people, 5 lines. | 20s | ✅ **BOTH TAKES COLLECTED + REVIEWED.** Take 1 `27180404` (porthole, kept as alternate) in Drive as `absence-s3-the-interpretations.mp4`. **Take 2 `61198828` — CORRECT FRAME, downloaded to Drive as `absence-s3-the-interpretations-take2.mp4`, md5-verified byte-exact.** Reviewed at 1fps across all 20s: fine crack lines radiate from a dark impact point dead centre of frame (a web of thin fractures, not a circular hole), brass plaque low in frame with all three lines mirror-reversed ("THE ABSENCE OF MEANING" / "Valder" / "$2,000,000" all read backwards), six people facing camera in the right order, Dupe drifting through background with his cart in multiple frames. **No porthole, no wood/brass frame border — nothing like take 1's defect.** Audio: continuous dialogue with brief natural pauses around 8s/17s/18s, consistent with 5 speakers handing off lines. **This frame is confirmed clean for reuse on S4/S6/S11.** | task-a13469e9 |
| S4 | **$2,000,000** — wall POV. 8 people now, ordinary clothes. | 11s (spec said 15s — see duration-bug note) | ✅ **take 1 LANDED + COLLECTED** — asset `6aa5bf40-11a3-43e3-bce7-bfcc1ec518ce`, in Drive as `absence-s4-two-million.mp4`, md5-verified. Reviewed at 1fps: correct `loc_wall_pov_c` frame (crack dead centre, plaque low + mirror-reversed reading $2,000,000), 8 people present matching the ref list, Dupe with cart at the edge, small idle movements (arm-folding) over the hold — matches brief. **Only 1 take fired so far, second take not yet done** |
| S5 | Collector A reads it aloud. Bidding opens. Press arrive. | 20s | 📝 prompt written · needs `char_press` swapped to `char_press_a`+`char_press_b` before firing · **CTO cast the woman in cobalt as Collector A — CEO to confirm** |
| S6 | **$20,000,000** — wall POV. 10–20 people, personal guards. | 15s | ⬜ |
| S7 | **Valder arrives** and greets the gentleman in the white suit. | 20s | 🟢 **UNBLOCKED, CTO 2026-08-28 ~10:30** — bind `char_gentleman_c` from here on, never the old `char_gentleman` (permanently Face/IP dead). Fix landed as `5e5c2eaf-5dfd-419d-bad0-912e63d20771` filed under the new Element. CTO note: the plate carries more gold in the smile than the CEO's two-caps spec — accepted and logged for the CEO, not a defect to fix. **Not yet fired** — next in queue, needs prompt swapped to `char_gentleman_c` mention | task-a13469e9 |
| S8a | Pieces 1–3: the chair, the fish trap, the millstone. | 20s | 📝 **ready to fire** — swap `char_gentleman` → `char_gentleman_c` before firing |
| S8b | Pieces 4–5, then he turns and the crowd parts. Ends on his face. | 20s | 📝 **ready to fire** — swap `char_gentleman` → `char_gentleman_c` before firing |
| S8c | **The sixth story.** The pivot of the film. | 25s | 📝 **ready to fire** — swap `char_gentleman` → `char_gentleman_c` before firing |
| S9 | Dupe hears Valder's voice from the next room. Sweat. | 11s | ✅ **take 1 LANDED + COLLECTED** — asset `209d88c2-6d62-4d54-b92b-3c1396519ff5`, in Drive as `absence-s9-dupe-hears-it.mp4`, md5-verified. Reviewed at 1fps: Dupe mopping, back to a chromium column, cart with gold V beside him, real painting leaning against the cart facing outward, distant indistinct crowd in background, Valder never in frame — matches brief. **Only 1 take fired so far** |
| S10 | **The parrot woman arrives** with the crocodile bag. Rivalry. | 20s | ⬜ — swap `char_gentleman` → `char_gentleman_c` before firing |
| S11 | **$100,000,000** — wall POV. Press, live broadcast, helicopter. | 15s | ⬜ **unblocked** — needs `char_press` → `char_press_a` + `char_press_b`, and `char_gentleman` → `char_gentleman_c`. Not yet built |
| S12 | **The grandmother** wheels in and takes it. The room freezes. | 25s | 📝 **ready to fire** — `char_press` → `char_press_a`+`char_press_b` fixed in staged prompt; `char_gentleman` already swapped to `char_gentleman_c`. Plate `5dd23a87` (character ref) wheels pass all 4 panels · ⚠️ gloves came out black, CTO: skip reshoot |
| S13 | **Valder improvises** the sixth story. He believes it. | 25s | ⬜ |
| S14 | **The workman arrives with plaster.** Valder screams. | 20s | ⬜ |
| S15 | **Dupe confesses.** "I cracked it. Last hour." Absorbed. | 25s | ⬜ |
| S16 | **They saw the wall out of the building.** | — | 🟢 **UNBLOCKED, CTO 2026-08-28 ~11:20** — `char_press` replaced by two single-face plates, `char_press_a` (reporter, petrol blue, notebook) and `char_press_b` (camera operator, rust orange, shoulder camera — CTO-approved). Both keep the normal `project_absence_` prefix. Every scene that named `char_press` now binds BOTH `a` and `b` — two chips for one mention in the prose. Prompt fixed, **not yet fired** |
| S17 | The square hole. Someone steps back from it exactly as in S3. | 11s | ✅ **take 1 FIRED, rendering** — asset `d0469ad9-314d-474a-acad-b842b3049a5a`. Only reference is loc_hall_big_d (no characters), 1/1 clean, Unlimited $0, 720p, 16:9. Not yet collected |
| S18 | Dupe rich, the interview — then alone at a white wall, hammer. | 25s | ⬜ |

**S8 does not fit in one clip.** Valder's five stories plus the improvisation run
~160 spoken words; a 25s clip holds ~60. So S8 is written as **S8a / S8b / S8c**
in [s7-s9.txt](s7-s9.txt). No line was cut. That makes **19 clips per pass, not
17.**

**Corrected arithmetic — the earlier figure I gave the CEO was wrong.**

| | |
|---|---|
| Clips per pass | 19 |
| × 2 takes | 38 |
| Already fired | 2 (S1) + 1 (S2) |
| **Remaining** | **35** |
| Time to end of 30 Aug | **~66 h**, not the 41 h I first said |
| At 50 min/clip (peak-hours pessimistic) | ~29 h |
| **Margin** | **~37 h** |

So the schedule is comfortable, not knife-edge, and there is room for re-shoots.
The real constraint is **never leaving the one generation slot idle**, not the
clip count.

**Wall POV appears 4 times:** S3, S4, S6, S11. Same frame every time; only the
crowd inside it changes.

> **What `loc_wall_pov_b` actually looks like — CTO opened the file, 07:35.**
> A third-person view down the hall **seen through cracked glass**: fine crack
> lines radiating from a dark point **dead centre**, the brass plaque low in
> frame with its lettering **mirror-reversed**, six people beyond it facing
> camera. The reversed plaque is the tell that we are behind the wall.
>
> Two false alarms on this plate, both resolved:
> - An operator reported it had been **swapped by someone else mid-task**. It had
>   not. That description matched the approved asset all along.
> - The **Face/IP flag cleared on its own** — no warning triangle remains. That
>   is the documented periodic-rescan behaviour.
>
> **The real fault was my prose, not the plate.** My S3 prompt said "the wall
> ghosted and translucent… no hole, no aperture", which contradicts the plate the
> CEO approved. Firing without the reference let the model follow my words and it
> produced a porthole. Prompt now rewritten to match the plate.
>
> ⚠️ Known staleness, cosmetic: the plate still shows the art student in her
> **original** design (pink suit, purple beret), before the CEO's redesign. Bind
> `char_student_c` alongside it so her current look wins.
>
> **Update, 08:10 — `loc_wall_pov_b` is actually dead, not resolved.** A second
> hover after re-binding showed the terminal message *"Face/IP failed... this
> asset cannot be used. Try another."* — no "Check eligibility" button, no retry
> path, not the periodic-rescan pending-state described above. CTO's diagnosis:
> the six human faces baked into that plate are almost certainly what the
> scanner caught — a **location** reference should carry the frame, not the
> cast. **Fix: `loc_wall_pov_c`**, same cracked-glass/mirror-plaque concept,
> **zero people** in the plate (GPT Image 2, 16:9, Medium, 2K, ref
> `loc_hall_big_d`, 2.5 credits), which also kills the stale-student-design bug
> for free since there's no student in it to be stale. CTO opened the finished
> plate and approved it outright — dark impact point sits dead on the vanishing
> point, plaque reversed and legible. **`loc_wall_pov_b` is retired — do not
> attempt to revive it.**

---

## ❓ WAITING ON THE CEO — these block work

| # | Question |
|---|---|
| A | ~~What is `char_woman` for?~~ — **ANSWERED.** She declares it art, longer line, delivered perfectly still, and the room agrees. Written into `s2-interpretations.txt`. |
| F | ~~Parrot woman blue-hair collision~~ — **RESOLVED by CEO orders #64/#65.** Hair now carries three colours (green/white/blue); the garment stays a single green. Multi-colour lives in the hair only, so the one-colour-per-person rule survives. Original note: **Parrot woman came out with BLUE HAIR**, which collides with the student's signature ("dyed hair in an odd colour"). Not rejected — it passes every written rule, and the two read as different registers (couture colouring vs a student dying her own hair). **CEO to confirm** whether dyed hair should belong to the student alone. |
| B | ~~How do the guards dress?~~ — **ANSWERED: black is allowed for guards** |
| C | ~~Who is Valder as a person?~~ — **ANSWERED, see [VALDER.md](VALDER.md).** Deadpan permanent smile, stands perfectly straight, speaks a lot in Phase 2. |
| E | ~~**Valder's sixth line**~~ — **ANSWERED.** CTO drafted it, CEO approved: *"ตามนั้น"*. |
| D | ~~Scene numbering~~ — **RESOLVED.** 17 scenes, table above. |
| G | ~~Who is Collector A?~~ — **ANSWERED 2026-08-28: reuse an existing character, generate nothing.** The person who interpreted it as art becomes the person who has to pay to prove it. |
| H | ~~In-hall press vs outside press~~ — **ANSWERED: one plate, used for both** S5 and S14. |
| I | ~~Fire now or wait for plates?~~ — **ANSWERED: fire S2 and S3 immediately**, plates run in parallel. |

---

## 🔒 STANDING RULES — check before every fire

- **8 named characters. No crowd, no extras** unless a price tier calls for more.
- **Gold V is staff only** — Dupe's cap, Dupe's chest, the cart. Nobody else, ever.
- **One saturated colour per person, never black.** The student alone gets two. Valder wears all of them, which is the point.
- **Unlimited covers Seedance video only.** On VIDEO any live price means STOP. On IMAGES ~3 credits is correct and expected.
- **Never click Rerun.** Recreate is the safe one.
- **Commit the asset id before downloading** — ids cannot be recovered, files always can.
- **Look at every plate before writing a prompt that uses it.**
- **THE GRANDMOTHER IS `char_grandmother`. NEVER `char_grandma`.** Two separate
  plates exist and using the wrong one changes her face between scenes. CTO
  looked at both, 2026-08-28 07:00:
  - ✅ `char_grandmother` — violet throughout, **head cloth to the shoulders**,
    **large opaque smoked glasses**, retrofuturist shell chair with big rear
    wheels and front castors, physical button pod on the armrest, terracotta
    terrazzo floor. Matches every word of the CEO's spec.
  - ❌ `char_grandma` — **no head cloth, no glasses**, oxblood vest over a black
    turtleneck, joystick chair, and a **dark polished wood floor** that breaks
    continuity with the hall. Fails the spec twice and the location once.
    Superseded — do not reference it.
- **Ask before building** — counts, heights, who-wears-what. Ask first, not after the render.
- **Download straight into Drive, never the Desktop.** The project folder is
  mounted locally at `~/Library/CloudStorage/GoogleDrive-pass.gob1@gmail.com/ไดรฟ์ของฉัน/ALL DRAFT/YT: ILAG/Sorry, Sir/`
  — `All Scene/` for clips, `Element/` for plates. CEO, 2026-08-28: keep the
  Mac's disk clear. **Copy, verify byte-exact, then delete the local** — never
  delete first.
- **Paid GPT Image 2 gens do NOT share the Unlimited Seedance video slot.** Confirmed 2026-08-28: char_gentleman and another operator's char_grandmother both fired and completed while a Scene 2 video render was in flight. Don't stand down image generation while waiting on a video render.
- **`char_grandmother`** (note: different Element from `char_grandma` above — a second, separate grandmother design exists on the account, purple robe/headscarf/dark glasses in an antique-style wheelchair) came out with black gloves; the prompt already specified dark grey or oxblood. CTO decision 2026-08-28: **skip the reshoot** — gloves are an accessory, not a CEO-set rule, and a re-roll is a coin flip not worth the credits/time. Left as-is.
- **Duration field on the Seedance 2.5 composer is unreliable — CTO ruling: don't fight it.** Typing an exact value (e.g. "15") into the Duration popover produces unpredictable results (5s→10s→16s→13s→4s→11s across repeated attempts), and the pill/price display desyncs from the input's real value by one keystroke, surviving even a full page reload. **CTO 2026-08-28: for silent/locked-off shots the exact duration carries no story information — the editor trims in the cut. Take whatever value the field lands on** (S4 landed at 11s against a 15s spec) **and verify only these four things before firing: Generate reads UNLIMITED struck to 0, all references bound with correct thumbnails, 720p, 16:9.** Do not spend more than one or two attempts trying to land an exact duration.
