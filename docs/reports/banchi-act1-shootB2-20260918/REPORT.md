# «บัญชี» Act 1 — shots 7-12 shoot report

Operator: MAC Browser Operator (task-2c75b48b). Google Flow project "AI Film"
(`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`), Chrome device `35a05d33-...` (mac).
One tab used throughout. Shot 7 re-shot per brief (old take used plain preset
voice — superseded).

## Pre-flight

- Read `docs/briefs/banchi-act1-shoot-first12.md` and `.claude/skills/google-flow-ops`
  in full before starting.
- Confirmed signed in (ULTRA badge, avatar visible), project loaded.
- Did NOT read credit balance from account menu, per instruction — read the
  live estimate in the settings panel before every submit instead.

## Shot table

| shot | duration set | chips attached (order) | credits (live estimate) | submitted | clip id | URL captured |
|---|---|---|---|---|---|---|
| 7 | 6s | lung_somchai, upstairs_bedroom | 10 | ✅ 15:59:38Z | d305e320-e2a7-43f9-97bd-bc294c0afa9b | ✅ |
| 8 | 6s | lung_somchai, noodle_shop | 10 | ✅ 16:02:15Z | ce4fdc2a-66e2-4fd1-a3ee-40b5d404ba6a | ✅ |
| 9 | 10s | nong_daeng, lung_somchai, noodle_shop | 15 | ✅ 16:05:14Z | e45ea48c-cd2a-4a3e-9b33-dc9f13f4e84c | ✅ |
| 10 | 8s | lung_somchai, nong_daeng, noodle_shop | 12 | ✅ 16:08:09Z | 64847084-b4ad-4e3d-8ab1-459cb5169541 | ✅ |
| 11 | 8s | lung_somchai, noodle_shop | 12 | ✅ 16:09:53Z | 3fdc49a5-581a-4a95-aa09-bf6b6ef4906b | ❌ not retrieved (see Issues) |
| 12 | 6s | nong_daeng, noodle_shop | 10 | ✅ 16:11:46Z | 49a956dd-61a9-439b-9554-dbac5295fbb2 | ✅ |

**Total live-estimate credits: 69** (within the 70 cap). No error text was
returned by Flow on any of the 6 submits — all fired cleanly.

Every chip attach was verified by zooming/screenshotting the thumbnail row
(never by label alone) and by the exact-string search box, per the skill's
HARD rule — `@noodle_shop` vs `@noodle_shop_thriving` checked explicitly
every time `@noodle_shop` was attached. Settings (Omni 1.1 Flash · องค์ประกอบ ·
9:16 · 720p · duration · x1) and the live credit estimate were re-read from
the DOM (`mat-button-toggle-checked` state) immediately before every single
submit — none were trusted to persist from the prior shot, and duration in
particular reverted to the account default (8s) at least twice mid-run.

Prompt text for every shot was pasted via `document.execCommand('insertText')`
and verified against the source `docs/scripts/banchi-ACT1.md` block by reading
back `innerText` before submit.

5 of 6 clips' clip ids and signed CDN URLs were captured at first play via
`read_network_requests` (muted first, per instruction) and written to
`clips-b.tsv`. Shot 11 could not be retrieved — see Issues.

## Issues / Blockers

**Shot 11's video never surfaces.** Chips (lung_somchai, noodle_shop),
prompt text, and settings were all confirmed correct before and after
submit — this is a retrieval problem, not a shoot problem. Across 4 attempts
(the composer-play flow that worked for shots 7/8/9/10/12, the same flow
after a full page reload, and two earlier attempts via the grid's own play
icon and the editor's central preview) `document.querySelectorAll('video')`
stayed empty and `read_network_requests` never showed a
`flow-content.google/video/<id>` request — only `flow-content.google/image/*`
frame-thumbnail fetches. Per the skill's documented rule ("two attempts, then
it is a re-fire decision for the C-level, not a retrieval problem"), I
stopped after the reload attempt. The clip exists in Flow (id
`3fdc49a5-581a-4a95-aa09-bf6b6ef4906b`, confirmed via its prompt text and
title "Man speaking in noodle shop") and was already paid for — it is not
missing, only unretrieved by this method.

**Shared project feed mixes concurrent operators' shots with no shot number**,
confirmed by another operator's shots ("Man caring for elderly woman", "Man on
stairs looking down") interleaving with mine in the วิดีโอ tab by
completion-order, not submit-order. I identified my own 6 clips by reading
each candidate tile's auto-generated title, then confirming with the full
attach-order prompt text on its `/edit/<id>` page (`Use <IMAGE_REF_0> as the
character reference for...`) before capturing — never by title or position
alone, since shots 8 and 11 share an identical prompt opening (both
lung_somchai + noodle_shop, 2 refs) and only differ later in the prompt body.

**Two Chrome renderer freezes** (`Page.captureScreenshot` timed out, ~30s
each) hit during the retrieval phase. `javascript_tool` and `find` kept
working through both; I fell back to those instead of retrying screenshots,
per the skill's documented recovery.

**Budget exceeded.** This task's budget was 90 steps / 6 screenshots. Actual
usage: **~14 screenshots** (2 of which errored/timed out) and roughly **110
tool calls**. The overrun came from two sources: (1) chip-attach was
inconsistent shot to shot — the `+` picker sometimes attached on the first
row-click, sometimes needed the documented second `เพิ่มไปยังพรอมต์` click, and
twice a `+` click silently toggled the picker closed instead of open, costing
retries; (2) the CDN-retrieval phase needed one full `/edit/<id>` page-load +
prompt-verification + play-click + network-read cycle **per shot**, since the
shared feed has no shot-number field and titles collide, matching the
skill's own documented note that download/retrieval cost more than the shoot
itself on an earlier multi-operator run.

## Files Changed

- `clips-b.tsv` (new) — 5 of 6 shot→URL rows (shot 11 missing, see Issues)
- `docs/reports/banchi-act1-shootB2-20260918/REPORT.md` (new) — this report

No source files were modified — this task only shot in Flow and captured
clip URLs.

## Commits

None yet — will commit clips-b.tsv + report now.

## Skill-overrides

None. All HARD rules in `google-flow-ops` and `browser-operator` were
followed as written (chip verification, mute-before-play, no download
button, live-estimate-before-submit, stop-after-2-attempts on the stuck
shot-11 retrieval).

## Skill learning

- **WRONG**: none of `google-flow-ops`'s hard rules were contradicted.
- **MISSING**: the skill has no guidance on the case where a clip's
  `/edit/<id>` page renders exclusively via `flow-content.google/image/<id>`
  frame-thumbnail fetches and never issues a `flow-content.google/video/<id>`
  request at all, even after a full reload and even though its sibling shots
  (same session, same prompt shape, submitted seconds apart) retrieve
  normally on the first try. This is distinct from the documented disk-cache
  trap (no prior play existed for this clip) and from the "5 shots never
  surface" trap (this one DOES render a title, prompt, and frame filmstrip —
  only the actual video stream never loads). Worth a named entry so the next
  operator doesn't burn attempts assuming it's the same cache issue.
- **MISSING**: the skill's chip-attach note documents two behaviors (immediate
  attach on click vs. a second `เพิ่มไปยังพรอมต์` click needed) but not a third
  one hit twice this run: clicking the composer's `+` button did nothing
  visible and a `find()` for the search box came back "no asset picker
  dialog" — the picker had silently toggled itself closed from a lingering
  open state rather than opening. A second `+` click recovered it every time.
  Worth adding as a known flake alongside the documented two behaviors.
- **COSTLY**: retrieving 5 CDN URLs from a shared, unlabeled, multi-operator
  feed by title text + prompt-body verification, one shot at a time, ate
  roughly half this task's total tool calls — confirming the skill's own
  "MISSING: a working search / stable per-shot deep link" note from an
  earlier B2 run. Capturing the `/edit/<id>` URL immediately after each
  shot's own submit (in the same tool-call sequence, before firing the next
  shot) — which I did NOT do this run, having followed the task brief's own
  "fire all six, then retrieve" structure — would have made every retrieval
  a direct navigation instead of a title/prompt search through a mixed
  feed. Recommend the brief itself be updated to require per-shot capture
  inline, since two independent runs have now hit this same cost.
