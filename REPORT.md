## Summary

Read-only browsing task on winbox Chrome (`815ddf16-36ea-4e0d-827a-f51e9ff85351`).
Collected every rule, date, timezone, requirement, limit, and disqualification
condition from the Higgsfield Global Film Festival's four target pages, verbatim
with source URLs, into `docs/reports/higgsfield-festival-rules-20260909.md`. All
16 FAQ accordions on the contest General tab and all 16 on the Create-in-Public
page were expanded and quoted in full; the Rules tab's complete legal text
(Official Rules §1-19 + Create-in-Public Rules §1-15, 55,287 characters) and the
blog post were captured and quoted in full. Flagged two real cross-source
discrepancies (PT-vs-UTC final deadline; Sep15-Oct5 vs Oct5-Oct15 screening
window) rather than silently picking one. Nothing was submitted, generated, or
changed on the account — no Submit/Enter/Publish/Join/Accept control was
clicked, only FAQ-accordion and tab-switch buttons.

## Files Changed

- `docs/reports/higgsfield-festival-rules-20260909.md` — new. The full
  deliverable: 12 sections (Deadlines, MVS, Social post, Watermark/packshot,
  Length/content, Tools/AI-only, Eligibility, Create in Public, Submission
  flow, Licensing/ownership, Disqualification, Open questions), every bullet a
  verbatim quote + source URL, plus a discrepancy-warning box at the top.
- `.scratch/higgsfield-rules-tab-raw.txt` — not committed (scratch/local only).
  Raw `innerText` export of the Rules tab (55,287 chars) used as the source of
  truth for the verbatim Official Rules + Create-in-Public Rules quotes; kept
  locally in the worktree for cross-checking, not part of the deliverable.

## Commits

- a5d265d — docs: compile every Higgsfield Global Film Festival rule, verbatim (task-21464a2e)

## Tests

- N/A — documentation-only task, no code changed, no test suite applies.

## Issues / Blockers

- None. Task completed within scope: no login walls hit, no terms-acceptance
  prompts encountered, no generate/project pages opened, no tab owned by
  another operator touched.
- Two genuine rules-content discrepancies were found between Higgsfield's own
  pages (not a task blocker, but worth the CEO's attention before the org
  commits to a specific deadline number) — both are called out explicitly at
  the top of the deliverable doc rather than silently resolved by guessing:
  1. Final-submission deadline stated as "11:59 PM UTC" on the Official Rules
     page but as "11:59 PM PT" in the Create-in-Public Rules' re-submission
     clause (same document, `?tab=rules`) — a possible 7-hour gap.
  2. "Screening & shortlist compilation" is dated Sep 15 - Oct 5, 2026 on the
     Official Rules page but Oct 5 - Oct 15, 2026 on the blog post.

## Notes for Reviewer

- Technique used to extract the ~55K-character Rules tab cheaply: after
  reading `document.body.innerText.length`, the full text was saved to a
  local file via a page-triggered `Blob` + synthetic `<a download>` click
  (the page's own already-rendered, already-read text — not a third-party or
  untrusted download), then read from `~/Downloads` off disk. This kept the
  browser-action budget low (well under the 40-call cap; 2 screenshots total,
  well under the 10-screenshot cap) while still getting exact, unretyped
  verbatim text. The same download trick stopped working for two subsequent
  smaller pages (Chrome's repeated-download throttling, most likely); those
  were read via chunked `javascript_tool` `.slice()` calls instead, with
  overlapping windows to guarantee no gaps — verified by eye at each seam.
- All FAQ accordions on both the contest General tab and the Create-in-Public
  page use a Radix-style single-DOM-node-per-item accordion where a closed
  item's answer is not in the DOM at all until its button is clicked
  (`data-state="closed"` → empty child). Both sets of accordions (16 + 16)
  were clicked open via `button.click()` in `javascript_tool`, not via the
  `computer` tool, since that was cheaper and the buttons are ordinary
  disclosure controls, not Submit/Enter/Publish/Join/Accept.
  `python scripts/browser/tab_registry.py claim/done` was used around every
  navigation; the tab was closed before writing this report, so nothing is
  left open in the shared winbox Chrome for the S2R-F harvester's tab to
  collide with.
- Please double-check the two flagged discrepancies with someone at
  Higgsfield or by re-reading the live pages closer to the deadline in case
  either gets silently corrected — this report is a snapshot as of 2026-09-09.
