# H3 Scene Generator: written scenes do not show, and Generate looks frozen

CTO brief, 2026-10-03. Project: MoonieX-ComfyRunpod (studio). Role: developer.

## CEO report (verbatim)

> บัคนะ เขยน Seence ไม่ขึ้น เลย แล้วเวลา กด Generate มันชอบค้างนาน โดยไม่มี Indicator บอกเลยว่าตอนนี้ถึง Progress ไหนแล้ว

(Bug: written scenes do not show up at all. When Generate is pressed it hangs for a long time, with no indicator of how far it has got.)

## What the CTO measured on the live studio (status fields only)

| Fact | Evidence |
|---|---|
| The writer works server-side. | Job `528e43fb` ran 10:27–10:34 TH: 9/9 scenes `done`, audit `done`. |
| A second job ran on the same 9-scene plan. | Job `fecd9490` started 10:35 TH. At 10:47 TH it was still `status: running` / `auditStatus: running`. Scenes 9/9 done, 6 amber, $0.18. Its audit plus rewrites ran 6+ minutes after the last scene. |
| The page shows none of these scenes. | All 5 saved drafts are `mode: auto`, `jobId: null`, `cards: 0`. The latest plan has 10 scenes and `chainLength: 8`. `/scenes` renders "No scenes yet" and never calls `GET /api/scenes/write-all`, because the poller only runs with a `jobId`. |
| Re-plan drops a finished or running job. | `doPlan()` calls `setJobId(null)` (page.tsx ~845). Nothing on the page can find the job again, although `GET /api/scenes/write-all` with no id returns the latest job. |
| A new Write-all is refused while that job audits. | `startWriteAllJob` throws "a write-all job is already running (id …)" until the audit ends. |
| During audit the progress line stays frozen. | While `status === "running"` after the last scene, the line reads "Writing 9/9" for minutes. "auditing..." shows only when `status === "done"`. |
| No spinner actually spins. | Every `Loader2` on `/scenes` (10 uses) has no spin class, and no CSS rotates it. Plan, Generate N, Write all, Regenerate and Resume show a still icon. There is no elapsed time and no stage label. |
| Autosave makes duplicates. | 4 of the 5 drafts are identical, so each save made a new draft instead of updating one. |

Note for probes: Next 16 dev refuses `/_next/*` from the `127.0.0.1` origin, so a headless page opened on `http://127.0.0.1:<port>` never hydrates. Use `http://localhost:<port>`.

## Build

1. **Reproduce first, through the real page.**
   - Write `scripts/test_scenes_ui.py`: Playwright plus the fake OpenRouter from `scripts/test_scene_auto.py`, on a throwaway `next dev` (ports 4195–4199, temp data dir).
   - Drive the page:
     1. Plan.
     2. Write all.
     3. Assert that cards appear one by one while the job runs.
     4. Re-plan while a job is running or finished, and assert the job's scenes are still reachable.
     5. Reload the page, and assert the same.
   - Commit the failing run before the fix.
2. **Never lose a job.**
   - When the draft has no `jobId`, or the plan is replaced, the page finds the latest job (`GET /api/scenes/write-all`) and offers it: "Show last written batch (N scenes, <status>)".
   - A running job is always shown, with a Stop button. A second Write all while it runs shows the refusal and offers to show the running job; no silent no-op.
   - Re-plan while a job is running asks first, and never orphans it.
3. **A progress indicator on every long action.**
   - **Spinner:** every busy `Loader2` actually spins.
   - **Plan, Generate N, Regenerate, Write all start:** a stage label plus elapsed seconds, for example "Planning with deepseek-v4-pro · 47 s".
   - **Write all:** "Writing 3/9 · 1:12".
   - **Audit:** after the last scene, the line moves to "Auditing · rewrite 2/6 · 0:40". Expose the counters on the job record if they are missing, and update `docs/STUDIO-API.md`.
   - **Done, error or stopped:** each shows its own state. Nothing reads "Writing 9/9" once writing has ended.
4. **Autosave updates one draft.** Keep the draft id after the first save, so later saves update it.

## Rules

- **Never touch the live studio.** No `:4100`, no main checkout, no live `studio/data`, no real OpenRouter. Tests use the fake server only.
- **Never print story, prompt, scene or plan text** in logs, tests or reports. Print counts and status fields only. HARD rule from the CEO.
- **UI icons are inline SVG / lucide, never emoji.**
- **Switch-off parity:** fixed-count Generate and Auto mode behave as before, apart from the indicator. The existing suites keep their counts: `test_scene_auto`, `test_scene_gen`, `test_scene_aspect`, `test_writer_skill`, `test_auto_cut`, `test_safe_split`. `tsc --noEmit` exits 0.

## Done when

- `scripts/test_scenes_ui.py` failed before the fix and passes after it. Its cases:
  - cards appear while the job runs;
  - Re-plan keeps the job reachable;
  - a reload re-attaches;
  - a second Write all is refused with a visible message;
  - the spinner has a running animation (computed style);
  - elapsed time advances;
  - the audit stage is labelled.
- The suites above pass, and `tsc` passes.
- The report lists files, commits, test counts, the root cause of "scenes do not show" in one paragraph, and a Skill learning section.
