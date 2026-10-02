# H3 RunPod restore — R2: requeue on pod_lost, balance gate, resume

CTO brief, 2026-10-03. Project: MoonieX-ComfyRunpod (studio). Role: developer.

## Why

At 00:29 TH on 2026-10-03, the RunPod balance hit $0 and RunPod stopped the H3 pod mid-render.

- R1 (task-7da0e6e4) makes `render_job.py` fail fast with `errorCode: "pod_lost"` and adds `lib/runpodBalance.ts` (`getBalance`, `canAfford`).
- R2 makes the queue runner act on both:
  - it retries a lost clip instead of skipping its chain;
  - it does not start a clip the balance cannot pay for.

Base: this branch starts after task-541e46b2 (safe split) and task-7da0e6e4 (R1) are merged. Both are in `queueRunner.ts` / `renderRuntime.ts` on main.

## Build

1. **Requeue on `pod_lost`.** When a running item's job ends with `errorCode === "pod_lost"`:
   - Put the item back to `pending`. Clear `jobId` and `error`; keep its seed.
   - Do NOT call `cascadeSkips` for it. Its chained followers stay `pending`.
   - Count the retries on the item (`podLostRetries`). After 3, it becomes a normal `error` and cascades as today.
   - Mark the pod runtime as lost (state `off` or `error`, whichever `podRuntime.ts` already treats as "boot a new pod"), so the next tick boots a pod and does not send a job to the dead URL.
   - Read `podRuntime.ts` first. Do not terminate or start pods anywhere new; reuse the existing boot path.
2. **Balance gate before each clip.** In the tick, right before `startRender`, call `canAfford(<this clip's estimated render seconds>)`.
   - Estimate from the same learned average the ETA uses. If none exists, use the clip length × the current per-frame default.
   - If it answers false, do not start the clip. Set a runner flag `paused: "low_balance"` with the balance and runway at that moment.
   - Then stop the pod once nothing is running (drain, then the existing `stopPod`), so an idle pod does not bill.
   - Keep `canAfford`'s fail-open behaviour (an unreadable balance answers true).
3. **Resume.**
   - Add the setting `autoResumeAfterTopUp`, default **false**, on the existing settings page/API.
   - When false: `/render` shows a banner while paused (reason, balance, runway) and a "รันต่อ" button. The button calls `POST /api/queue/resume`, which clears the pause.
   - When true: while paused, the runner re-reads the balance every 2 minutes and clears the pause itself once `canAfford` passes for the next clip.
   - In both cases the next tick boots the pod as usual.
4. **Events.** Publish the pause and the resume on the existing event bus, so `/render` updates without a reload.

## Rules

- **Never touch the live studio.**
  - No `:4100`.
  - No main checkout.
  - No live `studio/data`.
  - No real RunPod mutation.
  - Tests use fake GraphQL and fake ComfyUI (see `scripts/test_pod_lost.py`, `scripts/test_balance.py`) and run on ports **4195–4199** only.
- **Never print a key**, and never print prompt, story or scene text, in logs, tests or reports. Print status fields only.
- **Switch-off parity:** with a healthy balance and no pod loss, the queue must behave exactly as before. The existing suites must keep their counts.

## Done when

- New `scripts/test_pod_restore.py` covers the cases below, each through the real tick (enter through `queueRunner`, not by calling helpers directly):
  - pod_lost requeue, chain kept, no skip;
  - the retry cap;
  - the low-balance pause before start, then drain and stop;
  - resume by button;
  - auto-resume ON;
  - auto-resume OFF stays paused.
- `test_pod_lost.py`, `test_balance.py`, `test_safe_split.py`, `test_auto_cut.py`, `test_scene_auto.py`, `test_scene_gen.py`, `test_scene_aspect.py` pass. `tsc --noEmit` exits 0.
- `docs/STUDIO-API.md` documents `POST /api/queue/resume`, the pause event and the setting.
- The report lists files, commits, test counts, and a Skill learning section.
