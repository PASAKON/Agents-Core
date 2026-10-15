# H3 studio: /api/events loses render events in its first moments

CTO brief, 2026-10-03. Project: MoonieX-ComfyRunpod (studio). Role: developer.
Base: origin/main at 5ba9253 or later (W4 merged; it changed scripts/test_pod_lost.py).

## What is wrong

`studio/src/app/api/events/route.ts` does three things in this order:

1. ~line 25: takes the job list (`listJobs`) and sends it.
2. ~line 28: awaits `currentColabStatus()`, which is about three file reads.
3. ~line 31: subscribes to new events (`bus.on`).

A render event published between steps 1 and 3 never reaches that connection, and the stream never sends it again.

- **Live symptom:** a /render tab that connects or reconnects just as a job sends its last event shows that job stuck until the page is reloaded.
- **Test symptom:** `scripts/test_pod_lost.py` section (i) failed the same 3 checks in 2 of 4 runs on a busy machine. Both jobs were still `starting` when its 20 s window closed, because the fake render scripts finish within milliseconds of starting.

The review that found this read `studio/.next/dev/trace`:

- /api/events compiled in 0.27 s, so this is not a cold compile.
- A longer window cannot help, because a lost event is never sent again.

## Build

1. **Reproduce first.**
   - Add a check that fails on the current route. It must enter through the real door: a throwaway `next dev` on ports 4195–4199 and a GET on `/api/events`.
   - One way: an env-only test hook (for example `STUDIO_TEST_EVENTS_DELAY_MS`, read only when set) that widens the gap between step 1 and step 3. Publish a job event inside the gap, then assert the stream delivers it.
   - Commit the failing check first.
2. **Fix the route.**
   - Do every await (getStatus, currentColabStatus) first. Then subscribe and take the job list in one synchronous step, with no await between them.
   - Or subscribe first and buffer events until the snapshot is sent. Dedupe by job id + stage, so nothing is sent twice in a way the page mis-handles.
   - Keep the event names and payload shapes exactly as they are. Read `studio/src/app/render/page.tsx` (and any other EventSource user) to confirm.
3. **Make test_pod_lost (i) honest.**
   - Open `/api/events` before the two POSTs and read until the first snapshot line. That proves the listener exists.
   - Wait until both jobs reach a final stage by reconnecting: short per-connection windows (about 10 s) inside a total budget of 60–90 s. Stop as soon as both ids are final.
   - Move `requests.get` inside the try.
   - Print numbers: time to first byte of /api/events, and seconds from POST to final stage per job.
   - After `wait_for`, check that `next_proc.poll()` is None, so a port collision cannot send the test to someone else's server.

## Rules

- **Never touch the live studio.** No `:4100`, no main checkout, no live `studio/data`. Tests use fakes only, on ports 4195–4199.
- **Shared suite lock** for every suite run:
  - take: `until mkdir /tmp/h3-suite.lock 2>/dev/null; do sleep 15; done; echo $$ > /tmp/h3-suite.lock/pid`
  - release: `rm -f /tmp/h3-suite.lock/pid; rmdir /tmp/h3-suite.lock`
- **Never print prompt, story or scene text**, and never a key. Status fields only.
- **Switch-off parity:** with no event in the gap, the stream sends exactly what it sends today.

## Done when

- The new check failed before the fix and passes after it.
- These suites pass, with counts: `test_pod_lost` (run it 3 times; every run passes), `test_balance`, `test_safe_split`, `test_auto_cut`, `test_scene_auto`, `test_pod_restore`. `tsc --noEmit` exits 0.
- The report lists files, commits, test counts and a Skill learning section.
- Do not commit this brief, TASK.md or CTO-FEEDBACK.md into the project branch.
