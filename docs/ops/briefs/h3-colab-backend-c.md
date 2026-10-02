# H3 Colab backend — Task C: the studio sends safe takes to Colab for real

CTO brief, 2026-10-03. Project: MoonieX-ComfyRunpod (studio). Role: developer.

## Why

CEO 2026-10-03: "รัน Google Colab ให้ได้ วันนี้". Two pieces exist on main (49c0c5c):

- **Router (task-541e46b2).** `safeSplit.ts` `routeTakes` marks a whole Auto Cut take `backend: "colab"` only when all four layers pass (writer rating, Jev, deny list, NudeNet ref scan). The switch is the setting `safeSplit.allowColab`, default false.
- **Runner (task-c99d48d6).** `scripts/colab/run_take.py` renders a take spec on a Colab G4 and pulls the clips back. Measured: ~3 min setup per VM, ~52 s per extra 5 s scene, 8.9 CU/h. See `docs/COLAB.md`.

Between them, `studio/src/lib/colabBackend.ts` is a stub that always answers `{available:false}`, so `settleColabTakes()` sends every take to RunPod. Task C replaces the stub with the real thing.

## Build

1. **`runColabTake(head)` for real.**
   - Available only when all three hold: the colab CLI is installed, `~/.config/colab-cli/token.json` exists, and `allowColab` is true. Otherwise it returns `{available:false}` exactly as today.
   - When available, build a take spec from the head and its chained followers, then start `run_take.py` detached. Return a started result; this widens `ColabTakeResult` as the stub's comment describes.
2. **Parity with the RunPod path.** A scene rendered on Colab must get the same graph inputs a RunPod render gets for the same queue item:
   - prompt constraints (the runner's docs say "no prompt constraints are added" today);
   - LoRAs, quality tier, aspect, seed and steps.
   Read how `queueRunner.ts` and `renderRuntime.ts` / `render_job.py` build them, and reuse that code rather than copying it.
3. **Chains on the VM.** Followers continue from the previous clip exactly as on RunPod: i2v from the last frame, or r2v continuation with refs (`--continue-from`). The previous clip stays on the VM, with no round trip. Add this to `run_take.py` / `remote_take.py`.
4. **Queue state.**
   - While a scene renders on Colab, its item shows `running`, then `done`.
   - Each clip lands where a RunPod clip lands (`findClipPath`, take versions), so stitch / hard-cut and the episode join work unchanged.
   - Progress and errors are published on the event bus the same way RunPod jobs are.
5. **Failure means RunPod, never lost.**
   - If a Colab take fails or hits its cap, every scene of that take not yet done goes back to pending with `backend: "runpod"` and `routeReason: "colab_failed"`.
   - Scenes already done keep their clips.
   - One Colab attempt per take; no retry loop.
   - A failure must never cascade skips.
6. **Post-render tripwire.**
   - Scan frames of each Colab clip with the same NudeNet path the L4 ref scan uses.
   - If a clip is flagged, stop that take on Colab, discard the flagged clip, and send the take's remaining and flagged scenes to RunPod (`routeReason: "colab_tripwire"`).
   - Report counts only.
7. **Caps.**
   - Each take gets a CU cap and a minutes cap from settings: defaults 6 CU and 45 min, editable on the settings page next to `allowColab`.
   - The guard from `scripts/colab/guard.py` enforces them, and a VM is never left running.
   - `/render` shows "Colab" on items rendering there.

## Rules

- **Never touch the live studio.**
  - No `:4100`.
  - No main checkout.
  - No live `studio/data`.
  - No real RunPod mutation.
  - Tests run on ports **4195–4199** only.
- **Tests use a fake colab CLI**, the pattern in `scripts/colab/test_run_take.py`, and enter through the real queue tick.
- **One live acceptance take only.**
  - Content: synthetic safe prompts and the synthetic ref (`scripts/colab/make_ref.py`); 2 chained scenes.
  - Cap: 5 CU.
  - Never H3 data, never a real H3 ref.
- **Never print a key or the OAuth token, and never print prompt / story / scene text.** Status fields and counts only.
- **Never open or describe any image in `studio/data`.** On the synthetic clip, frame checks are fine.
- **Switch-off parity.** With `allowColab` false (the default), the queue behaves exactly as before, and existing suites keep their counts.
- **UI:** inline SVG icons, never emoji.

## Done when

- New `scripts/test_colab_backend.py`, through the real tick with a fake colab CLI, covers:
  - unavailable falls back to RunPod as today;
  - a started take moves its scenes running → done, with clips where stitch expects them;
  - chain inputs are passed (seed, continue-from);
  - a failure mid-take sends the rest to RunPod with no skips;
  - tripwire;
  - caps;
  - switch off means no change.
- These suites pass, and `tsc --noEmit` exits 0:
  - `test_colab_backend`, `test_run_take`, `test_safe_split`, `test_pod_restore`, `test_pod_lost`, `test_balance`, `test_auto_cut`;
  - `test_writer_skill`, `test_scene_auto`, `test_scene_gen`, `test_scene_aspect`.
- The live acceptance take is done. Report stage times, CU charged, and both clips' frames / fps / duration. The second clip must continue from the first.
- `docs/COLAB.md` and `docs/STUDIO-API.md` describe the backend, the settings and the fallback reasons.
- The report lists files, commits, per-suite counts, and a Skill learning section.
