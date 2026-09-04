# Protected-content bisect on S2L-Fix1 — 2026-09-04 (task-acb8d73f)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
("The Valder Collection No.7" in the UI) — confirmed via address bar and
page title before touching anything.

`git merge main` at task start pulled the local (unpushed) `main` ref
forward, same as the previous session (task-952e647e): `origin/main` merge
was a no-op, the prior session's S2L/S2M prompts, previz MP4s and the
`absence-s2l-s2m-20260904.md` report landed via the local-`main` merge.

## Context this session started from

A prior session (task-952e647e) had already fired S2L once with all 10
references bound (9 Elements + `@Video 1`) and been refused instantly:
*"Some assets may contain protected content. Remove or replace them to
proceed."* $0 cost, no render started. It could not identify which of the
10 assets triggered the scanner. This task's job was to bisect the 5
references that had never appeared in a video fire before:
`char_woman`, `char_student_c`, `char_visitor_b`, `char_visitor_a`,
`char_critic_b` — by staging each alone in a fresh composer (never
clicking Generate) and watching for a warning at the chip/page level.

## Job 1 — per-Element staging results

Each candidate was bound as the ONLY reference in a fresh Seedance 2.5
composer (Cinema Studio 4.0 default switched to Seedance 2.5 explicitly),
via the plain `@project_absence_char_*` mention → dropdown selection. For
each, checked: mention resolved to a real chip (not left as red/unresolved
text), and the entire page text scanned for `protected|sensitive|remove or
replace` immediately after binding, before ever touching Generate.

| Element | Chip resolved? | Warning on chip/page? |
|---|---|---|
| `@project_absence_char_woman` | Yes, clean chip + thumbnail | **None** |
| `@project_absence_char_student_c` | Yes, clean chip + thumbnail | **None** |
| `@project_absence_char_visitor_b` | Yes, clean chip + thumbnail | **None** |
| `@project_absence_char_visitor_a` | Yes, clean chip + thumbnail | **None** |
| `@project_absence_char_critic_b` | Yes, clean chip + thumbnail | **None** |

**All five stage completely clean, individually.** No red/unresolved text,
no warning-triangle overlay, no `protected`/`sensitive`/`remove or replace`
string anywhere on the page after binding any of them.

**The "bind all five together" sub-test was not completed** — an
accidental generation fired partway through building that combined prompt
(see Incident below), and per the standing "stop after one clean attempt
near a priced control" doctrine in `higgsfield-unlimited-gen`, it was not
retried this session.

## Incident — accidental 45-credit Seedance 2.5 fire, real money, unrelated to the bisect

**GH issue filed:** https://github.com/PASAKON/MoonieX-Agents/issues/128
(full forensic writeup there; summarized here for the record).

While clearing the composer and typing the second candidate
(`@project_absence_char_student_c`) to build the combined-five prompt, a
`find()`-returned element `ref` for the first mention's dropdown item had
gone stale after the DOM re-rendered (a trailing space closed/reopened the
typeahead). Clicking that stale ref actually clicked the sidebar's
"Project brief" nav link instead (URL changed to `?brief=1`). The next
typed text landed somewhere during that navigation, and navigating back to
the composer URL showed a **"Generation started" toast**, `All assets`
count 622→623, and a new card rendering.

**This was never an intentional Generate click.** The composer's Generate
button had never been switched to Unlimited during Job 1 (correctly — Job
1 never needed it, since no fire was ever planned), so it was showing a
**live 45-credit price the entire time**. Confirmed via Account → Manage
Account → Usage:

> `45 credits · Seedance 2.5 · Spent · Sep 4, 2026 8:31 AM`

The generated asset's own saved prompt (checked via its Info panel) is a
single tag, **`@project_absence_char_woman`, rendered in red** — i.e.
never actually bound to the real Element at submission time, matching the
paste/mention-desync failure mode already documented in
`higgsfield-unlimited-gen`. The clip itself is a generic invented woman in
a dim hallway, nothing to do with the S2L cast, wardrobe, or scene. **No
protected-content refusal occurred on this fire** — it rendered fully, so
this data point says nothing about the bisect question; it is pure wasted
spend.

**Cost: 45 credits ≈ $1.80** at the documented $0.04/credit rate. Current
balance 1,309.85 credits (Usage History entry is the authoritative record
for the charge itself).

## Job 2 — did not fire

Per the brief: *"If Job 1 finds NO culprit — every chip stages clean
individually and together — then do NOT fire."* All five candidates stage
clean individually. The "together" half of that condition was not tested
(interrupted by the incident above), so strictly no culprit was
identified either way. **Job 2 was not attempted.** No `docs/S2L-Render.MP4`
upload, no reference binding beyond the Job 1 tests above, no Generate
click for the real S2L-Fix1 take. No chip was dropped — Job 2 never
started, so there is no six-field / price / verdict table to report.

## Money summary

- Job 1 (as designed): $0, read-only, no Generate click ever made for any
  of the 5 individual candidate tests.
- Incident: 1 unintended Seedance 2.5 fire, 45 credits (~$1.80), confirmed
  via Usage History, unrelated content, no refusal.
- Job 2: never attempted, $0.

## Files Changed

- `docs/reports/absence-protected-content-bisect-20260904.md` — this report

## Commits

- (this commit)

## Issues / Blockers

- **GH #128** — full incident writeup, including a proposed skill
  addendum: re-run `find()` immediately before every dropdown-item click
  in a fast-changing mention menu rather than reusing a `ref` captured
  before a subsequent `type()` call, since a stale ref can resolve to an
  unrelated page element (here, sidebar navigation) and the resulting
  focus/typing confusion can end in a real Generate click even when the
  operator's actual clicks never touched the button.
- **The bisect is still open.** Individually, none of the 5 candidates
  trigger the scanner. The combined-5 test (and the video-ref hypothesis
  the prior session flagged as "most likely, but inference not confirmed")
  remain untested. Needs a CTO/CEO call on whether to retry the combined
  staging test in a fresh session, or move straight to a click-time test
  (which is real money either way, since the scanner's only observed
  trigger point so far is Generate itself, not staging).

## Notes for Reviewer

- The account's Unlimited toggle was never touched this session — by
  design, since Job 1 never needed it. That is also exactly why the
  accidental fire cost real credits instead of $0: worth flagging for
  future read-only Higgsfield tasks that even a **staging-only** session
  sits next to a live-priced button unless something Job-1-shaped forces
  otherwise.
- Composer left cleared (no chip, no prompt text) and in a normal, non-priced
  idle state — not a "protected tab," no CEO manual fix was involved, so no
  special handling needed for whoever picks this up next.
- The prior session's S2L-Render.MP4 previz asset and the s2l-fix1 prompt
  file are both present and correct in the repo (verified after merge) —
  ready for whichever operator continues the bisect or fires Job 2 once a
  culprit is named.

## SKILL-OVERRIDE

None declared as an override — the incident above was not a deliberate
choice to deviate from `higgsfield-unlimited-gen`; it was the concrete
failure the "stop after one clean attempt" and "check Usage History after
any anomaly" hard rules exist to catch, and both were followed once the
anomaly (the "Generation started" toast) was noticed: stopped further
combined-chip testing immediately, checked Usage History before any other
action, and did not retry the interaction pattern that caused it.
