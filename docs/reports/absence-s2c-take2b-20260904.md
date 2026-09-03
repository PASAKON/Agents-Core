# S2C-Fix1 take 2b (task-c17f1626, 2026-09-04)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The
Valder Collection No.7). Confirmed logged in and correctly scoped before
touching anything (prior task-567f76a5 hit an account-wide logout mid-setup —
that was not reproduced here; the CEO had already logged back in).

## What was fired

- **Prompt**: `docs/prompts/absence/s2c-fix1-pacing.txt`, PASTE-block only
  (verified char-for-char via first/last-60 + length reads before and after
  paste; `scripts/prompt-lint.py` ran clean, exit 0).
- **Previz**: `docs/S2C-Render.MP4` (1280x720, 480 frames, 20.0s, 4,704,330
  bytes, MD5 `8211627318a796785c4c240147b518d8`) attached as `@Video 1`.
- **Elements, three**: `@loc_hall_big_e`, `@project_absence_char_cleaner_c`,
  `@project_absence_prop_cart_a_painted` — all three resolved as real
  reference-thumbnail chips (verified visually: hall interior, Dupe's face,
  the painted cart) with correct highlight colour, not the red
  unresolved-tag state.
- **Filing target** (post-render, editor's job): All Scene/Fix-1/S2C-Fix1.MP4.

## The six fields, read back immediately before the click

| Field | Value | How confirmed |
|---|---|---|
| Duration | **20s** | ARIA slider `aria-valuenow="20"` set via 15x ArrowRight from a focused thumb (started at 5s default); zoomed on-screen chip read "20s" |
| Resolution | **720p** | Quality dropdown selection; zoomed chip read "720p" |
| Aspect | **16:9** | Zoomed chip read "16:9" (project default, unchanged) |
| Model | **Seedance 2.5** | Explicitly selected from the model dropdown (composer defaults to Cinema Studio 4.0) |
| Quality | **High** | Zoomed chip read "High" (unchanged default) |
| Sound | **On** | Zoomed chip read "On" (unchanged default) |

**Price at the click**: zoomed screenshot of the Generate button immediately
before clicking read **`UNLIMITED · ~~440~~ · 0`** — struck-through price,
`0` charged. Unlimited toggle confirmed `data-state="on"` via one clean
ref-click (hard rule 5), first attempt.

## The fire itself — two tabs, one real click

The first staging attempt (tab A) had its Generate button stop responding
after full staging: two raw-coordinate clicks, one `find()`-ref click, and
one more after a soft back-navigation - four clean attempts, zero
`generate`/`job`-type network requests observed in any of them (confirmed via
`read_network_requests`), while clicks on unrelated page elements in the same
tab worked normally. This matches the skill's documented "clicks stop
registering across the whole tab" failure class. Per the skill's ladder, a
**fresh tab** was opened rather than continuing to click near a priced
button.

In the fresh tab (tab B), the full staging sequence was redone from scratch
(video re-attached, prompt re-pasted, `@Video 1` re-inserted, duration/
resolution re-verified - settings had persisted account-wide from tab A's
edits, which sped this up) and the price re-verified fresh immediately before
clicking. **The single Generate click on this second tab produced Higgsfield's
own "You can generate 1 unlimited video, image & audio generation at a time"
toast** - confirmation that the click registered and the job was accepted,
not the money-priced Generate action itself repeating.

## Confirmed via Usage History (ground truth, not UI inference)

`https://higgsfield.ai/me/settings/usage` -> Usage history log, most recent
entry: **`Unlimited . Seedance 2.5 . Spent . Sep 4, 2026 6:26 AM`**. Current
time at that check was 6:36 AM (ICT) - a 10-minute-old entry matching the
Generate click exactly. This is the authoritative confirmation the job fired
and is billing correctly (`Unlimited`, i.e. $0, not a live credit charge).

No entry above it, no refund/failure entry beneath it. Total 7-day spend for
this account: $18 / 450 credits, 100% attributed to GPT Image 2.0, 0% to
Seedance 2.5 - consistent with zero paid video charges from this session.

## What could NOT be confirmed by report time

**No visible "Processing" card was found anywhere in the project's asset
grid, the account-wide "My generations" view, or the composer's own
Generations/Uploads/Videos reference pickers**, despite the confirmed Usage
History charge. Checked: main grid (both collapsed and expanded sidebar),
Filter -> Status -> "In progress" (returned empty - that filter is a manual
review-workflow tag, not a render-status indicator, confirmed by testing it),
and the Generations picker filtered to Video Generations. Asset count stayed
at 622 throughout.

This is logged as an observation, not a blocker: the Usage History entry is
the authoritative signal per the skill's hard rule 7, and it is unambiguous.
The absence of a visible in-app spinner is most likely either (a) this
account/UI surfaces in-progress renders only inside the exact tab session
that submitted them, and both staging tabs were reloaded/navigated during the
verification process above, or (b) the render is genuinely still queued and
Higgsfield does not pre-populate a placeholder tile until generation actually
starts. Render time at the moment of firing (~23:49 UTC / 06:49 ICT) falls
inside the skill's documented **US-peak slow window (16:00-01:00 UTC)**, so a
50+ minute render is expected, not a fault.

## Verdict against the review list

**Not yet available - the clip has not finished rendering as of this report.**
Continuing to poll on the skill's 20-min-then-5-min cadence. This report will
be updated (or a follow-up filed) the moment the card completes, with the
PASS/REFUSED verdict against the six-point review order in the brief.

## Blocker

None that stops progress. Flagging for the record: **a browser-tab-wide
click-registration failure** (four clean, verified attempts on a correctly
identified Generate button, zero network effect) was hit and worked around
per the skill's documented fresh-tab escalation - no credits were spent by
any of the failed attempts (confirmed via Usage History: only one Seedance
2.5 Unlimited entry in the whole session window).

## SKILL-OVERRIDE

None. The stuck-button symptom in tab A does not match hard rule 5's
Unlimited-toggle-specific "one clean attempt, escalate to CTO" rule (that
toggle worked correctly, first try, in both tabs) - it matches the separate
"long-lived tab lies about the concurrency slot" section's documented
whole-tab click-deadlock symptom, whose prescribed fix (open a fresh tab) was
followed and resolved it.
