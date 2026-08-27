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
| 35 | **SCENE 2 — THE ACCIDENT fired** — Dupe dusting, painting slips, crack in the wall, painting leaned on cart facing out. Seedance 2.5, 20s/720p/16:9/High/Sound On, Unlimited (struck `140`→`0`). Refs: `loc_hall_big_d` + `char_cleaner_c` + `prop_cart`, 3/3 bound clean. Not yet reviewed — still rendering | asset `56ace68c-ffd0-47ec-a7f6-d24bf523496a` · task-a13469e9 |

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

## 📋 ORDERED, NOT STARTED

**Plates**

| # | What | Needed for |
|---|---|---|
| 15 | `char_guard_private` — personal bodyguard. **CEO: black IS allowed for guards** | $20M tier |
| 16 | **`char_guard_valder` — DONE.** Uniform identical across all six, gold V on chest and cap, black only on belts and shoes, real range of builds. Route A worked: uniform study first, then re-dressed the existing six.  ~~original brief:~~ CEO: reuse the existing blue 6-guard plate **if it already has the gold V** — check first, generate nothing if so. If no V: generate the UNIFORM alone, then re-dress the existing six so faces stay varied and the uniform stays identical. Single plate first, six-guard plate second. | $20M tier |
| 17 | `char_press` — journalists | $100M tier |
| 18 | Helicopter — decide: part of the exterior plate, or its own | $100M tier |
| 19 | `char_visitor_c` — **currently has NO reference image**, content-flagged, prose-only | face consistency across scenes |

**The cleaner's later life**

| # | What |
|---|---|
| 20 | `char_cleaner_rich` — a good suit that finally fits |
| 21 | `loc_mansion` — **furnished by someone else, nothing in it is his**, his old cart in one corner as the only thing that is |
| 22 | `prop_camera_rig` — retrofuturist interview camera, nothing digital |

**Valder's five pieces** — full spec in [VALDER.md](VALDER.md)

| # | What | Element |
|---|---|---|
| 15a | The chair — "in the room where the armistice was signed. Not at the table." | `prop_valder_chair` |
| 15b | The hanging fish trap — "caught nothing for forty years" | `prop_valder_trap` |
| 15c | The millstone ring — "somebody stood it upright and it stopped being a tool" | `prop_valder_millstone` |
| 15d | The lidded vessel — "seventeen made, he destroyed sixteen" | `prop_valder_vessel` |
| 15e | The painting — "painted in one afternoon to test a colour" | `prop_valder_study` |

**Scenes**

| # | What |
|---|---|
| 23 | S2 — the interpretations scene. Written, not fired. Dialogue is the CEO's own. |
| 24 | S3 — not written |
| 25 | The three wall-POV escalation shots — see the price ladder |

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

## ❓ WAITING ON THE CEO — these block work

| # | Question |
|---|---|
| A | ~~What is `char_woman` for?~~ — **ANSWERED.** She declares it art, longer line, delivered perfectly still, and the room agrees. Written into `s2-interpretations.txt`. |
| F | ~~Parrot woman blue-hair collision~~ — **RESOLVED by CEO orders #64/#65.** Hair now carries three colours (green/white/blue); the garment stays a single green. Multi-colour lives in the hair only, so the one-colour-per-person rule survives. Original note: **Parrot woman came out with BLUE HAIR**, which collides with the student's signature ("dyed hair in an odd colour"). Not rejected — it passes every written rule, and the two read as different registers (couture colouring vs a student dying her own hair). **CEO to confirm** whether dyed hair should belong to the student alone. |
| B | ~~How do the guards dress?~~ — **ANSWERED: black is allowed for guards** |
| C | ~~Who is Valder as a person?~~ — **ANSWERED, see [VALDER.md](VALDER.md).** Deadpan permanent smile, stands perfectly straight, speaks a lot in Phase 2. |
| E | **Valder's sixth line** — the improvised story of the crack. The pivot of the film. Five rehearsal stories are written; this one is the CEO's. |
| D | Scene numbering — the sheet's 15-scene table predates the rewrite and no longer matches what is being shot. |

---

## 🔒 STANDING RULES — check before every fire

- **8 named characters. No crowd, no extras** unless a price tier calls for more.
- **Gold V is staff only** — Dupe's cap, Dupe's chest, the cart. Nobody else, ever.
- **One saturated colour per person, never black.** The student alone gets two. Valder wears all of them, which is the point.
- **Unlimited covers Seedance video only.** On VIDEO any live price means STOP. On IMAGES ~3 credits is correct and expected.
- **Never click Rerun.** Recreate is the safe one.
- **Commit the asset id before downloading** — ids cannot be recovered, files always can.
- **Look at every plate before writing a prompt that uses it.**
- **Ask before building** — counts, heights, who-wears-what. Ask first, not after the render.
