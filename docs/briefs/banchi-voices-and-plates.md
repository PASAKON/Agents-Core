# «บัญชี» — bind 3 voices, then download every plate. ZERO credits.

Two parts, **in this order**. Part 1 cannot be blocked by anything in Part 2, so
do it first and do not skip it if Part 2 goes wrong.

Project: **"AI Film"** on `flow.google.com`. Read the balance at the start and
at the end and report both. Everything here is free — no video generation, never
press Submit in the composer, never open a clip, never press play.

## Part 1 — re-bind three characters to new presets

The CTO re-cast these because the three men measured 132 / 148 / 150 Hz and read
as the same person. Bind the **plain preset** — do not use
`ปรับแต่งประสิทธิภาพ`, do not try to save a custom voice. That save button is
disabled on this account and three runs have already proved it; anyone who tries
a fourth is wasting the run.

| character | currently | bind to |
|---|---|---|
| `@grandma_pranom` | **nothing at all** | **Vindemiatrix** |
| `@cop_wit` | Achird | **Rasalgethi** |
| `@lender_cherd` | algieba | **Umbriel** |

Leave `@lung_somchai` (Algenib) and `@nong_daeng` (Iapetus) exactly as they are.

Path: character page → the voice row → dialog `เลือกเสียง` → search the preset →
select it → `เพิ่มลงในตัวละคร`. Then **reload the page and read the binding back**
— a binding that does not survive a reload did not happen. Report the read-back
value for all five characters, including the two you did not touch.

## Part 2 — download every plate, once

The CEO reports no download-blocked indicator in Chrome, so the permission that
stopped the last run is not showing. Try again.

`scripts/browser/banchi-plates-download.js` has the proven method and the
virtual-scroll fix. Read it before you start.

Download one image per asset tile in the `ตัวละคร` tab — characters, locations
and props — to `~/Desktop/banchi-plates/<handle>.png`, named for the handle
without the `@`. `side_wall.png` and `grandma_pranom.png` are already there from
the last run; skip those two.

Expect roughly 20 assets. Known present: `@grandma_pranom` `@nong_daeng`
`@lung_somchai` `@cop_wit` `@side_wall` `@money_fold` `@empty_pill_pack`
`@qr_sign` `@fathers_phone` `@bedrail_marks` `@noodle_shop_thriving`
`@staircase` `@street_front` `@back_alley` `@upstairs_bedroom` `@staff_a`
`@jae_muay` `@lender_cherd` `@noodle_shop` `@prop_envelope`. Skip
`@test_char3`. Report anything on that list you cannot find.

**Two traps, both already paid for:**
- The `ตัวละคร` grid **stops re-rendering in a background tab**. Scrolling then
  walks past rows that are never painted, and the last run wrongly reported two
  assets missing because of it. Keep the tab in the foreground and scroll with
  a real wheel action — a `scrollTop` assignment does not thaw it.
- If downloads start working and then **all** of them stop at once and survive a
  reload, that is Chrome's own per-site automatic-downloads permission, not
  Flow. **Stop immediately and report it** — it needs one human click on the
  browser's address bar that no tool here can reach. Do not build a workaround;
  the last attempt at one was deleted rather than merged.

## Budget

70 steps, 4 screenshots. Answer in text.

## Deliverable

`docs/reports/banchi-voices-plates-20260918/REPORT.md`:
1. the five characters' voice bindings **as read back after a reload**
2. a table: handle → downloaded yes/no → file size on disk
3. credit balance before and after
4. anything missing or unexpected
