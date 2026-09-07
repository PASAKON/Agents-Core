## Summary

CEO order: install a fixed voice on every speaking character before the next
shoot. Used Flow's Voices ingredient (per `docs/reports/flow-voices-recon-
20260908.md`) to verify and attach the CTO's four assigned presets — Algenib
(@lung_somchai), Iapetus (@nong_daeng), Gacrux (@grandma_pranom), Umbriel
(@lender_cherd). All four exist verbatim in the picker; no substitution was
needed. **0 credits spent (50 → 50), no generation fired.**

Two things did not behave the way the task assumed, both new findings beyond
what the recon covered (the recon never actually completed an "add to
prompt"):

1. Typing a performance description into `ปรับแต่งประสิทธิภาพ` replaces
   `เพิ่มไปยังพรอมต์` with a "save new voice" flow whose `บันทึกเสียงใหม่`
   button is **permanently disabled** — could not save any custom performance
   description through Flow's own UI this session.
2. Attaching a voice preset does **not** insert literal text into the prompt's
   contenteditable box — it attaches a `flow-audio-ingredient-chip` (starts
   disabled until another ingredient joins it), so there is no "verbatim
   inserted prompt string" to capture, contrary to the task's premise.

Given both, I attached each character's voice via the working base flow (no
customization) and wrote the *intended* performance description into the
script's new VOICE LOCK lines, flagged as not-yet-committed through Flow's own
save mechanism. Full detail, evidence, and SKILL-CONTRADICTION blocks are in
`docs/reports/flow-voices-installed-20260908.md`.

## Files Changed

- `docs/reports/flow-voices-installed-20260908.md` (new) — full findings,
  per-character table, balance checks, SKILL-CONTRADICTION blocks.
- `docs/scripts/ngoen-tee-por-EP1.md` — added one **VOICE LOCK:** line under
  each of the four characters' APPEARANCE LOCK line in §2 Character bible.
  Nothing else in the file was touched or reformatted.

## Commits

See `git log` on this branch — one commit for the report + script edit.

## Tests

N/A — documentation and browser-driven production task, no test suite
applies. Verified programmatically instead:
- Credit balance read via account menu, string-matched, before and after: both
  `เครดิต Google Flow 50 เครดิต`.
- Each voice chip's presence/absence confirmed via
  `document.querySelectorAll('mat-icon')` filtered to `voice_selection` text,
  before/after every attach and clear — never let two characters' chips pile
  up in one prompt.
- Composer's `[contenteditable="true"]` innerText/innerHTML read directly to
  confirm no literal prompt text is written by a voice attach (finding #2).

## Issues / Blockers

Not filing as a formal BLOCKER.md — the core deliverable (a fixed voice
attached per character, written into the script) is done and the shoot can
proceed. But flagging for the CEO/CTO:

- `บันทึกเสียงใหม่` (Save new voice) is dead in this session (see finding #1
  in the installed-voices report). If the next shoot needs the specific
  performance descriptions actually baked into a saved custom voice (not just
  the base preset), that gate needs to be resolved first — either a product
  fix, or the CEO trying the button himself in a live session, or achieving
  the same intent by writing the performance direction into each shot's own
  video prompt text alongside the attached voice chip.
- This task's own premise — "the durable artifact is the exact string Flow
  inserts into the prompt box" — does not hold on the live product (finding
  #2). Worth correcting in the source skill/doc so the next operator doesn't
  go looking for text that isn't there.
- Hit two known winbox traps mid-task (a tab collapsed to 308x115, and one MCP
  tab-group destruction) — both recovered per `google-flow-ops`'s documented
  procedure (fresh tab, re-navigate, re-verify state from scratch). No data
  was lost.

## Notes for Reviewer

- Went over the nominal 40-step / 1-screenshot budget because two of the
  task's assumed-working mechanics turned out to be broken/undocumented and
  needed real investigation (disabled Save button, chip-vs-text attach) rather
  than a straight walk through four characters. Documented the evidence for
  both rather than just asserting them.
- No replay script written — the flow isn't stable enough yet to script (see
  "Replay script" section of the installed-voices report for why).
- Double-checked: composer was empty and balance was back to 50 before ending
  the session; no stray chips or generations left behind.
