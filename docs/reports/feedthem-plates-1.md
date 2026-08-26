# Feed Them, Feed Me — Scene 1 Plates, Wave 1

Project: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-2

## Credits

- Opening balance: **1,918**
- Closing balance: **1,878**
- Total spent: **40 credits** (20 successful paid generations at 2 credits each)
- Plus 1 flagged/refused generation that was refunded (Cass sheet, attempt 1) — 0 net cost
- Hit the task's 40-credit hard cap exactly on the last plate (prop_cooler, white background).
  No further generation was attempted after this.

## What happened, in order

1. Created the 5 required folders (Character, Location, Prop, Scene 1, Scene 2) before
   generating anything, per the CEO's instruction. IDs recorded in ELEMENTS.md.
2. Generated the original 3-character single-pose plates + fish x3 + location x2 + prop x2 per
   the literal TASK.md brief.
3. **Mid-run, three rapid amendments arrived from the CEO** (relayed via the CTO), each expanding
   or correcting the previous one:
   - Amendment 1: character plates must be reference sheets, not single portraits (first spec:
     8-panel grid — quickly superseded).
   - Amendment 2 (replacing #1): concrete DND-format spec — one wide ~2.4:1 image, 4 panels
     (front/portrait/profile/back), DRY in 1&3, WET in 2&4, one signature relationship-to-camera
     pose per character. Applied to Milo, and the two named characters at the time (Nadia, Ash).
   - Amendment 3 (major, arrived after #2 was already executed): **cast expanded from 3 to 4**
     with new names/personalities — June (camera operator, new), Milo (unchanged), Cass
     (replaces Nadia, different personality), Theo (replaces Ash, similar role). Locations
     corrected from "sea, very shallow" to "freshwater reservoir, clear but DEEP (8-10m)".
     Props redone with a plain-white "Do Not Disturb technique" background for later compositing.
4. Per the CEO's explicit instruction each time ("if you already generated it, keep it, generate
   the new version too, report both ids"), **nothing was deleted.** Every superseded plate
   (Nadia, Ash, sea-locations, grey-bg props) is kept in its folder, undeleted, and marked
   OBSOLETE in ELEMENTS.md/PLATES.md so the CEO can pick without confusion.
5. A separate CTO message put a temporary HOLD on regenerating loc_pier/loc_camp pending a
   sea-vs-freshwater decision; that hold was superseded minutes later by amendment 3 confirming
   freshwater, so the location regeneration proceeded.

## Final plate count (paid generations)

- Character: 5 original (Milo single+sheet, Nadia single+sheet, Ash sheet) + 4 new-cast (June,
  Cass attempt 2, Theo — Cass attempt 1 flagged/refunded) = 9 successful generations
- Fish: 3 variants + 1 accidental duplicate of fish_c (browser-automation double-click race,
  disclosed honestly in PLATES.md, not an authorized 4th variant) = 4 generations
- Location: 2 original (sea) + 2 corrected (freshwater) = 4 generations
- Prop: 2 original (grey bg) + 2 corrected (white bg) = 4 generations
- **Total: 21 paid attempts, 20 successful (2cr each = 40cr), 1 flagged/refunded (0cr)**

## Blockers / anomalies encountered

- **Higgsfield ToS re-consent gate.** On first load, the account hit an "Our terms have changed"
  blocking screen (effective 2026-08-27). Per my hard-stop rules I asked the user before
  accepting; got explicit "yes" and proceeded.
- **Screenshot timeouts (CDP `Page.captureScreenshot`), twice.** Per the Higgsfield skill's rule,
  checked the credit balance immediately both times — no side effect either time.
- **One accidental duplicate generation** (fish_c) from a browser-automation double-click race:
  the first click's result was delayed, looked like a no-op, and a second click landed before the
  first had actually registered. Caught via the "All assets" counter jumping by 2 and the credit
  delta. Both renders kept and disclosed in PLATES.md; cost 2 extra credits.
- **One safety-system flag** (Cass sheet, attempt 1) — the phrase "cropped tank top" + "one hand
  on her hip" most likely tripped it. Credits were auto-refunded. Retried once (of the task's
  allowed 2 attempts) with softened wording ("fitted crew-neck t-shirt," "arms loosely crossed")
  and it generated cleanly. No warning-triangle re-check control existed on this account's UI for
  a post-generation safety flag (only Copy prompt / Delete / NSFW-visibility-toggle) — that
  control appears to be for a different, pre-generation "protected content" gate, not this
  post-hoc safety review. Retried via a new prompt instead, per the task's own "content refusal
  = hard failure, max 2 attempts" rule.
- **Chrome window repeatedly dropped into a locked "mobile access" viewport (728x420)** after tab
  closures, requiring fresh tabs and window recreation several times. No cost impact, just extra
  steps.
- **Composer settings (quality/resolution/aspect/model) reset unpredictably** across folder
  navigations, sometimes persisting, sometimes not — re-verified and re-set before every single
  Generate click, per the established replay-script discipline.

## What I did NOT do (explicitly out of scope)

- Did not generate `loc_under`, `loc_open`, or `loc_bottom` — these were named in the CEO's
  water-depth correction message but were never part of this task's Scene-1 plate list. Per the
  original brief ("only what Scene 1 needs... the rest of the film's plates come in a later
  task"), generating them would have been scope creep beyond what was authorized here.
- Did not judge, regenerate for taste, or delete any plate. The CEO approves.
- Did not attempt Downloading or writing final video prompts — explicitly a separate later step
  per TASK.md.
