> ## 🔴 CEO OVERRIDE 22:35 — S15 IS NOW THE TOP PRIORITY (editor needs it)
> The editor is waiting on S15. Jump the queue in this exact order:
> 1. **NOW, in parallel with whatever video is rendering** — generate the
>    `char_registrar` plate (image gens do NOT hold the video slot). Spec in
>    ASSETS below. ONE face, 4 panels. Report its mention string.
> 2. **The very next TWO free video slots = S15a then S15b.** Not S1B, not S2.
>    Prompt: `s6-s18.txt` → SCENE 15a, then SCENE 15b. **20s each.**
>    ⚠️ CEO 22:45: 25s IS NOT AVAILABLE — **20s is the hard ceiling for every
>    clip in this film.** S15 was split into two 20s halves (40s total, no
>    line cut). S15b continues S15a unbroken — same frame, same positions.
>    Refs trimmed to 10 chips; `char_woman`/`char_critic_b` deliberately
>    dropped — do not re-add. `char_workman` was missing and is now in.
> 3. Deliver each half the moment it lands: review → Drive `All Scene/S15/`
>    (both halves, same folder, named S15a / S15b) → Telegram to CEO. Do not
>    batch them behind anything.
> 4. Then resume the normal FIRE ORDER from where you left off.
> Note: renders are in the SLOW window until ~08:00 ICT, expect 50+ min.
> If either half comes back with drifted dialogue, re-fire ONCE immediately —
> do not queue other scenes ahead of a usable S15.
>
> **STANDING GATE — 20s MAX, applies to every clip, forever.** All five 25s
> scenes are now SPLIT and committed: S8c→S8c+S8d · S12→S12a+S12b ·
> S13→S13a+S13b · S15→S15a+S15b · S18→S18a+S18b. Every "b" half continues
> its "a" half unbroken: same frame, same light, same positions, no
> re-staging. Film is now 27 clips, not 22.

> **CTO NOTICE 22:26 — PRIORITY 1 NOT YET SEEN DONE.** Before firing A1 you MUST have:
> 1. `char_registrar` plate generated (spec in ASSETS below) — blocks S5/S10b/S12/S14/S15/P1-P3.
> 2. `loc_wall_pov_e` uploaded as an Element via the composer's uploader (PNG at Element/Location/absence-loc-wall-pov-e.png) — A1–A5 all bind it.
> Report BOTH mention strings in your next report. If already done, just report the mention strings.
> Also: after each scene wraps, send the keeper clip to the CEO via Telegram (lib.telegram_out.send_media_to_ceo) — S1 not yet confirmed sent.

# VIDEO QUEUE — authoritative · rebuilt clean 2026-08-28 20:50

**This file is the source of truth. Ignore any pane message that disagrees.**
Long tmux relays fragment — substantial changes land HERE, then a short ping.

## STANDING RULES
- **Never let the generate slot sit idle.** A re-shot clip is free; an idle
  hour is not.
- **One take per scene.** The CEO's review notes drive re-shoots, not spares.
- Tolerance: things must READ the same, 10–20% drift is fine — EXCEPT: no
  people in a location plate · duration on dialogue scenes · 720p · the
  Generate price.
- **Pre-fire gate, every clip:** 720p · 16:9 · duration set via the ArrowRight
  slider AND read back (`aria-valuenow` + visible label) · reference chips
  COUNTED against mentions, thumbnails zoomed · Generate price read off a
  ZOOMED SCREENSHOT, never a JS scrape.
- Rights-verification banner = standing CEO approval, click Confirm and carry
  on (skill rule 3b). Purchases/renewals/ToS still stop.
- Files: download → `…/ALL DRAFT/YT: ILAG/Sorry, Sir (The Valder Collection)/
  All Scene/<SCENE>/` (folder per scene, create only if missing) → verify
  byte-exact → delete local. **Never recreate the old "Sorry, Sir" folder.**
- **Commit every asset id BEFORE downloading.** Watch every clip; describe it
  shot by shot against the prompt's named beats.

## ASSETS — all exist unless marked
`loc_hall_big_e` · `loc_mansion_b` · `prop_cart` (original, S1 only) ·
`prop_cart_b` (S2 onward) · `char_woman_c` · `char_gentleman_e` ·
`char_grandmother` (never char_grandma) · `char_press_a/b` · `char_workman` ·
`char_husband` · `char_guard_private` · `char_guard_valder` · `char_valder` ·
`char_registrar` **← DOES NOT EXIST YET — plate it first, spec below** ·
`loc_wall_pov_e` **← hand-built PNG at Element/Location/absence-loc-wall-pov-e.png
— UPLOAD via the composer's uploader and file as Element `loc_wall_pov_e`; never
regenerate it; report the exact mention string.**

### char_registrar — plate spec (GPT Image 2 · 16:9 · 2K · Medium · ~2.5cr)
The museum's own official — bid-recorder and plaque-keeper in one. Composed man
~50s, immaculate IVORY staff livery with subtle orange piping, **small GOLD V at
the chest** (staff mark), **WHITE GLOVES**, slim brass-cornered leather ledger +
fountain pen. Calm, ceremonial, zero emotion, NOT sinister. **One face only**,
four panels incl. back view, real age and skin, face resembling no real person.

## THE FILM — current structure (CEO's Dupe-POV cut)
S1 silent solo → S2 accident → S2b phone call → A1–A5 arrivals → P1 → S4 → S5
(registrar, no press) → S6 → P2 → S7 → S8a → S8b → S8c → S8d → S9 → S10 → S10b (the
war) → S12 (grandmother, ledger-close = the gavel) → P3 → S11 (press arrive) →
S13a/b → S14 → S15a/b (confession live; the 100M goes to Dupe) → S16 → S17 → S18a/b.

Prompt files: `s1-multicut.txt` `s1-angles.txt` `s2-accident.txt`
`s-arrivals.txt` (S2b + A1–A5) `s4-s5.txt` `s6-s18.txt` `s7-s9.txt`
`s13-the-back-door.txt` `s-price-inserts.txt` (P1–P3)
`s-dupe-inserts.txt` (D1–D5). S3 files are DEAD — do not fire anything named S3.

## CANON RULINGS (CEO)
- S1 and all S1 angles: EMPTY museum, silent, original `prop_cart`, no extras
  (extras debut in S4).
- The painting rides the cart in plain sight from S2 to the end; **nobody ever
  looks at it, Valder included** — deliberate.
- Greetings only in A1 ("Excuse me, sir."), A3 ("Excuse me. Just a moment."),
  A5 ("Sorry, madam.").
- S17's stepping-back visitor = `char_visitor_a`, the same man as S4.
- "Then the artist is the building." = a faceless voice, nobody shown speaking.
- Collector A = the woman in cobalt. S10b ends with the parrot woman at eighty.

## FIRE IN THIS ORDER
1. **char_registrar plate** (S5 blocks without him) + **upload loc_wall_pov_e**
2. **S1** → **S1A–S1G** (all rewritten — restage from the files, never from memory)
3. **S2** (re-fire, Anderson pass) → **S2b**
4. **A1 → A2 → A3 → A4 → A5** — strict order, the row accumulates
5. **D1–D5** whenever the slot would idle
6. **P1 → S4 → S5 → S6 → P2 → S7 → S8a → S8b → S8c → S8d → S9 → S10 → S10b → S12 →
   P3 → S11 → S13a → S13b → S14 → S15a → S15b → S16 → S17 → S18a → S18b**
   → spares S1D/S1E last.
