# S2R Jump-Cut — THE BATTLE — t1 — 2026-09-07

Scene: S2R JUMP-CUT · THE BATTLE. Sheet: `docs/prompts/absence/s2r-fix1-the-battle-jumpcut.txt`
(paste block only). No previz — deliberate, per this sheet.

## Pre-fire gates

- `git merge main`: already up to date with origin/main (main >= d098746), nothing to merge.
- Paste-block gate greps (`awk '/PASTE FROM HERE/.../PASTE STOPS HERE/'` piped to grep):
  - `nearest|extreme foreground|very front|floating|toward the mark|backs to the room` → 0
  - `Video 1|previz` → 0
  - `@project_absence_prop_croc_bag` → 0 (crocodile-bag Element correctly absent)
- `python3 scripts/prompt-lint.py --chips <sheet>`: exit 0, EXPECTED 13 Element chips, names match the sheet exactly.

## Browser session

- innerWidth readback below 1280 (1024) at session start — shared Chrome window was shrunk by
  another worker. Followed task brief: waited 5 min, still 1024; CTO authorized a one-time
  maximize after 09:25 ICT. `resize_window(1600,1000)` returned success but the readback stayed
  at 1024 (known lie per skill) — released/closed that tab and opened a fresh one instead, which
  read back 1600x754, later 2280x722 after the CEO maximized the real window by hand. All
  state-changing actions (Unlimited toggle, Generate) happened only after a readback ≥1280.
- Tab claimed via `scripts/browser/tab_registry.py` for task-facd467d throughout; released at end.
- Banner "Credits are running low! Over 90% already used" closed with its own (x) as the first
  composer action, before touching Unlimited or pasting.
- Composer: switched Image→Video tab (confirmed via DOM `data-state="active"` on the Video tab,
  not just visual read — the two tabs render near-identically for this model). Selected model
  Seedance 2.5 explicitly (defaulted to Cinema Studio 4.0).
- Six fields set and verified fresh immediately before Generate: Seedance 2.5 · 16:9 · 720p ·
  20s (ARIA slider, thumb click + 13x ArrowRight from 7→20, never typed) · High · Sound On.
- Unlimited toggled ON **after** the six fields (duration reset it once, per playbook); price
  zoomed at the button itself: `✦ ~~140~~ 0` — struck-through price + live 0, confirmed by pixel
  zoom, not DOM text-scrape.
- Prompt: base64-encoded synthetic `ClipboardEvent` paste of the exact PASTE FROM HERE/STOPS HERE
  block (9,010 bytes source) into the visible (non-decoy) contenteditable node, filtered by
  `getComputedStyle(el).visibility === 'visible'`. Followed by End → space → Backspace to force
  Lexical state sync.
- Chip gate: `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')]`
  filtered to leaf `@`-prefixed spans → 18 chip nodes, 13 unique names, exact match to
  `prompt-lint.py --chips` output. 0 unresolved/red `@` text (separately verified: 18/18 `@`
  leaf nodes in the editor carry `text-font-brand`). `@project_absence_prop_croc_bag` absent, as
  required.
- Asset baseline read immediately before firing: **687** ("All assets" count in the project
  sidebar).
- **Fire**: clicked Generate at **09:37:57 ICT (02:37:57 UTC)**. Verified by the "Generation
  started" toast (top-left) AND a new "Processing"/spinner card at the top of the grid in the
  same action; asset count ticked 687→688 in the same read.
- Zero paid actions. The CEO's `SEEDANCE 2.5 CREDIT` cards and every other card in the grid were
  left untouched throughout.

## Render / poll

Polled every 5 minutes with a full reload, per playbook, from 09:38 through past 70 minutes —
well beyond the 30–55 min normal range for this window (01:00–07:00 UTC / 08:00–14:00 ICT).
At ~69 minutes the CTO flagged that another Unlimited fire (a different worker's S2M-B/S2R-B
scene) had been accepted mid-poll, meaning a stale tab could no longer be trusted to show this
card's true state. Followed the mandated recovery: released the tab, opened a fresh one, read
`window.innerWidth` again, and re-identified cards by their own Info/hover-preview text rather
than by grid position (several visually similar gallery-scene cards from sibling takes —
`s2r-fix1-the-battle.txt`'s non-jump-cut base take, both with and without previz — are present
in the same project and were ruled out individually by their distinct prompt openers: "ONE
LOCKED SHOT..." vs this sheet's "The camera is LOCKED... the take is CUT: THREE HARD JUMP
CUTS..."). The CTO, watching the account state directly, subsequently confirmed the fired card's
identity and final status.

## Result

**Card status: Rejected due to copyright restrictions.** (Higgsfield's own banner text, exact.)
No thumbnail, no download — nothing to file. Screenshot of the exact rejection text saved to
`docs/reports/frames-s2r-jc-t1/rejection-notice.jpg`.

Per the FIRE-PLAYBOOK gate ("A card ending 'Rejected due to copyright restrictions' ... →
screenshot the exact text, do NOT re-fire, report, STOP") — no re-fire was attempted.

## CTO's cross-session finding (reported to me directly, not independently re-verified this
session)

The 13-chip cast on this scene, when the previz (`Video 1`) is attached, rendered clean at
07:50 (fire 4) earlier the same day. Both no-previz variants of this scene fired today — the
locked-shot base take (`s2r-fix1-the-battle.txt`) and this jump-cut take — were rejected for
copyright. The working signal so far is: previz attached → clean; previz absent → rejected,
regardless of jump-cuts. Next attempt on this scene should carry the previz, which contradicts
this sheet's own "deliberately previz-free" design and is therefore a call for the CTO/CEO, not
something to act on unilaterally in this task.

## Frame/review checks

Not applicable — no video was produced. The sheet's REVIEW ORDER (three cuts at 3/9/15s, twelve
people, Valder dead centre, etc.) could not be run.

## Chip/gate summary

- 13/13 unique Element chips bound, 0 unresolved `@`, 0 `.text-icon-error`.
- Gate greps: 0/0/0 as specified.
- Price: struck `140` → `0`, confirmed by zoomed screenshot.
- Asset count: 687 (baseline) → 688 (post-fire).

## Files Changed

- `docs/prompts/absence/s2r-fix1-the-battle-jumpcut.txt` — appended dated t1 take note (fired
  09:38, rejected, previz finding) to the NOTES section only; the PASTE block is untouched.
- `docs/reports/absence-wave-20260907-s2r-jc-t1.md` — this report.
- `docs/reports/frames-s2r-jc-t1/rejection-notice.jpg` — screenshot of the exact rejection banner.

## Issues / Blockers

- The scene was rejected for copyright with no previz attached, consistent with the sibling
  no-previz take's failure the same session. Whether to re-run this scene WITH a previz
  (overriding the sheet's explicit previz-free design) is a CEO/CTO call, not mine to make.
- Mid-task, identifying "my" card among several visually similar sibling-take cards in the same
  shared project consumed a large share of the browser-action budget (repeated hover/click/View
  more probes, one JS timeout on an over-broad DOM scroll query). The CTO's direct confirmation
  of card identity, from watching the account, was what actually resolved it — worth noting for
  future briefs: when multiple near-identical prompt variants of the same scene are in flight in
  the same project on the same day, a stronger per-card identifier (e.g. asset id in the fire
  confirmation) would save this.

## Notes for Reviewer

- SKILL-OVERRIDE: none — followed FIRE-PLAYBOOK.md and higgsfield-unlimited-gen skill as written,
  including the CEO/CTO's live window-width and card-identification guidance mid-task.
- The `docs/reports/frames-s2r-jc-t1/rejection-notice.jpg` screenshot shows a sibling card's own
  "ONE LOCKED SHOT ... 20-second grey previz" prompt preview alongside the "Rejected due to
  copyright restrictions." banner in the same screenshot region — the banner text itself is
  what's evidentiary; the visible prompt snippet in that particular screenshot belongs to the
  adjacent sibling card, not this take (both were rejected, and both are visible in the grid at
  that scroll position). This is called out explicitly so the CTO doesn't misread the screenshot
  as this take's own prompt text.
