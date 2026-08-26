# Valder video wave 3 (task-80379c92)

Project: The Valder Collection No.7
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/`

Takes over from `task-b7224c38`, whose handoff report lives ONLY on the
unmerged branch `agent/browser_operator-task-b7224c38` at
`docs/reports/valder-video-wave2.md` (NOT on `main` — the task brief's stated
path was wrong; found it by inspecting the still-live worktree/branch).

## Correction to the task brief's own claims

- The brief's stated path `docs/reports/valder-video-wave2.md` on `main` does
  not exist on `main`. It exists only on the unmerged branch
  `agent/browser_operator-task-b7224c38`. Read directly from that worktree.
- The brief's suspicion about S1 take C's id colliding with an image-plate
  asset (`8195c8b3-316f-490e-9c78-ac3bb39952bc`) is corroborated by wave2's own
  handoff note, which independently flagged the exact same collision and could
  never re-verify it before running out of time. Treating it as bad data per
  the brief's instruction — not chasing it further. It belongs to the
  pre-rewrite S1 anyway, which is being refired regardless.

## Carried over from wave2 (task-b7224c38) — OLD PROMPT VERSIONS, do not count as done

These clips exist and are real footage for the editor's pile, but they used
the S1/S1B prompt files from BEFORE the CEO's rewrite (9-element opening chain
+ slow-motion shot 3). Per this task's brief, S1 and S1B must be refired
regardless of this table:

| Scene | Take | Clip asset id | Status |
|---|---|---|---|
| S1 | A | `57453ca1-2a4a-438f-8f10-def379c01ad1` | complete, OLD prompt (8 elements) |
| S1 | B | `43762082-cc8c-4325-b9fa-d5b337c81d46` | complete, OLD prompt |
| S1 | C | `8195c8b3-316f-490e-9c78-ac3bb39952bc` | **UNVERIFIED/bad data** — this UUID is also recorded elsewhere as the image-plate asset `project_valder_prop_dress_c2`. Two assets cannot share a UUID. Not chasing further per brief; OLD prompt regardless. |
| S1B | A | `423b2b6f-99c4-4fb4-acaf-43207294e999` | complete, OLD prompt (pre slow-motion-shot-3 version) |
| S1B | B | `35dbf2d6-3586-4faf-b6e3-9c06ed9a5edf` | complete, OLD prompt |
| S1B | C | `22cc1930-6fd7-4038-b7c4-9cb83c041818` | complete, OLD prompt |

## Carried over from wave2 — CURRENT prompt version, counts as done

| Scene | Take | Clip asset id | Elements | Notes |
|---|---|---|---|---|
| S3 | 1 | `6d01ad10-572e-41d1-876f-58093c0f5b56` | 8/8, 0 errors | Fired with the rewritten S3 file (post-thesis-rewrite). CTO confirmed via chat this counts as S3 take 1 — dropped from this wave's first pass. |

## Blocked in wave2, still blocked (per CTO diagnosis mid-session)

- **S2**: protected-content gate on `prop_frame` + `prop_mark`, hit TWICE
  (once with old S2 file, once with rewritten S2 file after the 07:05 sync).
  0 cost both times. S3 fired clean with the same `prop_mark` minutes after
  one of the S2 blocks, so CTO believes it's transient — will retry once when
  reached, skip if it gates again.
- **S4A / S5**: blocked on `@project_valder_loc_neighbor_door` — 4/4 bind
  failures in wave2, non-transient. **Root cause found this wave** (see
  below): the Element's real bound mention-ID is
  `@loc_project_valder_loc_neighbor_door` (malformed double `loc_` prefix),
  not `@project_valder_loc_neighbor_door` like every other tag and like the
  prompt files use. The Element's thumbnail IS a real photo (a teal door) —
  not empty/broken as one hypothesis suggested. Reported to CTO; skipping
  S4A/S5 until the Element ID is fixed or the prompt files are updated to use
  the literal malformed string.

## This wave's queue order (per task brief + CTO amendment mid-session)

CTO amendment received during this session: drop S3 from the first pass
(already fired with current prompt, see above), and skip S4A/S5 pending the
Element-ID fix. Revised order: S1, S2, S4, S1B, S4B, S4C, S5B, S6, S7A, S7B.

## Setup

All 13 prompt files synced fresh from `main` via `git show main:<path>` and
byte-verified against `git cat-file -s` (all matched exactly — sizes 27,382 /
19,904 / 17,456 / 14,386 / 15,522 / 14,600 / 14,532 / 14,495 / 13,048 / 13,213
/ 14,238 / 14,133 / 13,163 bytes for s1/s1b/s2/s3/s4/s4a/s4b/s4c/s5/s5b/s6/s7a/s7b).

Credits before wave: **1,932** (matches task brief exactly).

## Per-clip table (this wave)

| Scene | Take | Clip asset id | Settings confirmed | Elements | Generate button text at fire | Render minutes |
|---|---|---|---|---|---|---|
| S1 | 1 | `e4c958ae-7249-4fc6-ab83-8b17b13a86f3` | Seedance 2.5 / References / 16:9 / 720p / 20s / High / Sound On / Unlimited ON | 9/9, 0 errors | `UNLIMITED / ~~140~~ / 0` (zoom-confirmed struck-through) | fired, render in progress |

Credits after S1 fire: **1,932** (unchanged, confirmed via account menu).

### Note on S1's first fire attempt

The very first Generate click on S1 (on the original composer tab, `53464554`)
was correctly blocked by the platform's "1 unlimited generation at a time"
toast while S3 (`6d01ad10-...`) was still finishing — 0 cost, 0 side effect.
That tab then started giving inconsistent concurrency-toast readings even
after fresh-tab checks showed the slot was free (matches the skill's
documented "long-lived tab lies about the concurrency slot" finding). Per
that guidance, opened a brand-new tab (`53464577`), left the original
untouched, rebuilt the full composer from scratch there, re-pasted S1,
and fired successfully once S3 genuinely finished. S3's card also flickered
between "Processing"/"Generating"/complete several times right at the tail
of its render — matches the wave2 script's documented inconsistent-label
finding, not a new bug.

## Live browser state

- Two tabs open in the group:
  - `53464554` (original composer tab) — left untouched since the stale-toast
    symptom appeared. Still holds an earlier staged S1 prompt (now stale/
    irrelevant). Not touched further; will let it sit or repurpose later.
  - `53464577` (active composer tab, current) — logged in, Seedance 2.5 /
    720p / 20s / 16:9 / High / Sound On / Unlimited ON confirmed. S1 fire
    confirmed via toast + asset-count delta. This is now the primary working
    tab going forward.
- Next: stage S2 (`docs/prompts/valder/s2-multicut.txt`, 8 elements) while
  S1 renders.

## S2 — blocked again, skipped per CTO instruction

S2 staged cleanly (8/8 elements, 0 errors) once S1 finished. Generate hit the
protected-content banner ("Some reference elements may contain protected
content. Check eligibility or remove them to proceed.") — 0 cost. Identified
the flagged reference visually: `@project_valder_prop_frame` (the gilt frame)
shows a warning-triangle overlay in the reference tray; `@project_valder_prop_mark`
(the gold V) does not. Per CTO's mid-session instruction ("give S2 one plain
retry when you reach it; if it gates again, skip and move on"), dismissed the
banner, re-verified 8/8 with 0 errors, re-applied the desync fix, re-confirmed
`UNLIMITED / ~~140~~ / 0`, and retried Generate once. Gated again, identical
banner. Credits unchanged (1,932) both times. Skipping S2 per instruction —
moving to S4.

| Scene | Take | Clip asset id | Elements | Notes |
|---|---|---|---|---|
| S2 | — | BLOCKED (2 attempts this wave) | 8/8, 0 errors | protected-content gate on `@project_valder_prop_frame`; 0 cost both times; CTO-authorized skip |
