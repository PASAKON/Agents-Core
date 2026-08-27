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

---

## 🔄 IN FLIGHT — verify the worker is actually alive, every check

| # | What | Element | Worker |
|---|---|---|---|
| 9 | **S1 — Dupe cleaning.** Long take 12s + jump cut + long take 8s. No dialogue. 9 refs. | — | `task-f822499f` |
| 10 | **Wall POV v2** — ghosted wall, crack + plaque floating at true positions, **plaque text MIRROR-REVERSED**, no hole | `loc_wall_pov_b` | `task-fe200749` |
| 11 | **Art student redesign** — real art-student clothes, **dyed hair in an odd colour**, upright not hunched | `char_student_c` | `task-d988c30c` |
| 12 | **Museum exterior** — entrance, forecourt, gold V on the building, open sky for the helicopter | `loc_exterior` | `task-d988c30c` |
| 13 | **Parrot woman** — crest hair, parrot silhouette and texture, single cobalt, **must not read comic** | `char_woman_b` | `task-d988c30c` |
| 14 | **Valder Element** from the existing 18 Aug asset `6edafc56` — no generation, no cost | `char_valder` | `task-d988c30c` |

---

## 📋 ORDERED, NOT STARTED

**Plates**

| # | What | Needed for |
|---|---|---|
| 15 | `char_guard_private` — personal bodyguard. **CEO: black IS allowed for guards** | $20M tier |
| 16 | `char_guard_valder` — Valder's own guards, multiplying as the price rises | $20M tier |
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
| A | **What is `char_woman` for now?** Her line went to `visitor_b`. She stands still, hand at her mouth, and says nothing. — **CEO: decide later** |
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
