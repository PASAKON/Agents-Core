# Banchi (AI Film) download — 2026-09-19

Task: pull 12 already-paid clips from the AI Film Flow project onto disk via
Flow's own download button. Zero generation, zero credits spent, no Submit
ever pressed.

## Method

Per the task's reversed instruction, did NOT play clips / read network logs
for the CDN URL. For each shot: navigated to `/edit/<id>`, muted the page
(script from the brief, re-run after every navigation), clicked the download
icon with a real `computer` click, picked **720p (ขนาดดั้งเดิม / original
size)** from the resolution flyout — never 1080p/4K/GIF, since 4K explicitly
showed "50 เครดิต" and the task forbids any credit spend — then confirmed the
"ดาวน์โหลดวิดีโอแล้ว" toast and read the new file off `~/Downloads` via `ls -t`.
Waited ≥8s between clips.

## Result: 10 of 12 downloaded, 2 blocked

| shot | id | status | filename |
|---|---|---|---|
| 1 | 33b9b33a-53ad-4f5d-8dad-d0836605d01b | **BLOCKED** | — |
| 2 | c9ed8094-65e7-4564-9d6c-6572f6e1438f | downloaded | Man_crouching_against_wall_20260919033819.mp4 |
| 3 | 97073410-4c33-4a2f-b8f1-5ec78f7c09ad | downloaded | Man_on_stairs_looking_down_20260919033904.mp4 |
| 4 | 72adbdb4-65f5-4407-9639-9d0990e84290 | downloaded | Man_caring_for_elderly_woman_20260919033943.mp4 |
| 5 | c9dd7934-9c1b-4f83-a05d-54af9de4478a | downloaded | Man_caring_for_elderly_woman_20260919034023.mp4 |
| 6 | e513be94-693c-4fc1-a935-44560a08d4f1 | **BLOCKED** | — |
| 11 | 3fdc49a5-581a-4a95-aa09-bf6b6ef4906b | downloaded | Man_speaking_in_noodle_shop_20260919034147.mp4 |
| 13 | 7f865343-874d-463b-a002-a51f738bb4c6 | downloaded | Men_working_in_noodle_shop_20260919034226.mp4 |
| 14 | e07eb86b-6928-436b-83d5-032fb87dad4d | downloaded | Shopkeeper_serving_noodles_in_shop_20260919034305.mp4 |
| 15 | 49759b5b-44dc-436d-82ef-b713ed2312d6 | downloaded | Man_reading_phone_on_staircase_20260919034346.mp4 |
| 16 | cda89bb8-3d90-42ce-a8ac-770555ffb0d5 | downloaded | Man_leaning_against_stairwell_wall_20260919034427.mp4 |
| 17 | 4efd06e8-31eb-402f-b463-9b652fcd83f4 | downloaded | Man_speaking_in_noodle_shop_20260919033732.mp4 |

(Shots 4/5 and 11/17 share a base filename — same prompt/title, distinguished
by the timestamp suffix Chrome appended; both are correctly logged against
their own shot number in `downloads.tsv`, each verified by `ls -t` immediately
after its own download.)

## Shots 1 and 6 — blocked, and why

Both `/edit/<id>` pages loaded the toolbar chrome (download/delete/history
icons) but **zero content**: `document.querySelectorAll('video').length` was
`0` and `document.body.innerText` came back as just the header/nav labels plus
Google's generic "อาจทำงานผิดพลาดได้" banner — no prompt text, no thumbnail, no
ingredient chips, nothing. This is exactly the `<!---->` failure the task
brief already knew about for shot 1, but it turned out to affect shot 6 too.

Followed the task's fallback ("reach it by clicking its card in the project
grid") for both:

- Retried direct navigation for shot 6 a second time (6s wait) — same result.
- Scanned the project's media feed (`สื่อทั้งหมด`), which turned out to hold
  far more than 12 clips — a real production project with dozens of shots,
  characters, and one-off test generations. Checked every unmatched card and
  every card with a broken/blank thumbnail (there are several others besides
  1 and 6) by clicking through and reading the resulting `/edit/<id>` URL:
  `235c8a10`, `49a956dd`, `64847084`, `ce4fdc2a`, `d305e320`, `212fdbd8`,
  `43455c8a`, `d744fe99` — none of these matched `33b9b33a` or `e513be94`.
- Tried the project search box with the raw shot-id substring (`33b9b33a`) —
  Flow's search indexes prompt text, not asset ids, so it returned nothing.

Per `google-flow-ops`: "Two attempts, then it is a re-fire decision for the
C-level, not a retrieval problem." Stopped there rather than continuing an
open-ended scan of an unbounded project feed.

**No Chrome download-block indicator appeared at any point** — all 10
successful downloads went through cleanly with no blocked-downloads banner.

## SKILL-CONTRADICTION

`google-flow-ops` :: "Shot 1 rendered as `<!---->` on a direct visit for one
operator — if that happens, reach it by clicking its card in the project grid
instead." :: Shot 6 (`e513be94-693c-4fc1-a935-44560a08d4f1`) exhibits the
identical zero-video/zero-content failure on direct `/edit/<id>` visit, not
just shot 1. The grid-click fallback also did not locate either shot 1 or
shot 6 — this project's media feed contains many more clips than the 12
target shots (confirmed via `[aria-label]` DOM scan turning up titles like
"Men talking in noodle shop", "Man taking noodle order", "Father and son
talking noodle sh…", none of which map to any of the 12 target ids), and
several *other* cards in the same feed also render with blank thumbnails/zero
content, so a blind visual/title-based scan cannot reliably distinguish the
2 missing target clips from that pool. :: 2026-09-19, task-a0c8e9ca.

## Files landed

All 10 in `~/Downloads` (which already held 74+ unrelated `.mp4`s per the
brief — nothing there was moved, renamed, or deleted). Exact filenames are in
`downloads.tsv` at the worktree root.
