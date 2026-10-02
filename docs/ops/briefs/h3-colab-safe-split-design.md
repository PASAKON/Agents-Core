# H3 render split: safe takes on Colab, risky takes on RunPod

Design by MAC CTO #addb58de on 2026-10-02. Project: comfy-runpod-worker (ComfyRunpod, `studio/`).
Status: design only. Builds after Auto Cut (task-1a461483) merges, because both touch `queueRunner.ts` and `enqueue.ts`.

## CEO ask (2026-10-02)
- Send scenes with no risk (ordinary dialogue, no 18+) to Google Colab.
- Keep every risky scene on RunPod.
- Use an 18+ scan to decide. Jev may help.

## Ground rules
- **Default is RunPod.** Colab is opt-in per take, never per default.
- **Fail closed.** Any error, timeout, refusal, missing rating or low confidence routes to RunPod.
- **Nobody reads the text or looks at the images.** The CTO and workers see labels, probabilities and counts only. Classifiers run in code.
- **Colab runs on a dedicated Google account only.** Never pass.gob1 (see `Wikis/research/2026-10-02-colab-as-render-backend.md`).

## Unit of routing = one take
- A take is one Auto Cut chain (scenes k..k+N-1). Inside a take every scene uses the previous clip's last frames.
- Splitting a take across two backends would mean moving clips between them mid-chain. Do not do that.
- A take goes to Colab only if **every** scene in it passes and **every** reference image it uses passes.
- Shorter takes (smaller N) mean more takes can qualify.

## The scan, four layers
| Layer | What | Cost | Verdict rule |
|---|---|---|---|
| L1 writer tag | The scene writer adds `rating: "safe" \| "risky"` to each scene's JSON. Same call that already writes the scene. | ~0 (a few output tokens) | `risky` or missing = RunPod |
| L2 Jev | New `decide` site `h3_scene_rating`, options `safe` / `risky`, with written criteria. Jev returns a probability. | ~$0.00002 per scene (measured 2026-09-22 for a 475-token call) | Colab only if P(safe) >= 0.95 |
| L3 deny list | Code-side word/regex list over the scene prompt (Thai + English). | free | any hit = RunPod |
| L4 image scan | Local NSFW image classifier (for example NudeNet or an open nsfw detector) over every reference image of the take, run on the Mac. | free | any flag = RunPod |

Post-render tripwire: run the L4 classifier over sampled frames of every Colab output. A flag stops all further Colab routing for that batch and raises an alert. It cannot undo the render; it stops the next one.

## Facts measured 2026-10-03 (were open)
- Jev probe, 8 synthetic cases (3 safe, 1 borderline first date, 4 risky incl. 2 Thai and a school uniform): 8/8 correct, no refusal, no moderation block. P(safe) was 1.000 on safe cases, 0.980 on the first date, 0.000 to 0.020 on risky ones. Cost $0.000186 total, 366-1264 ms per call. Criteria text is in the task-541e46b2 brief.
- Retention: TypeSafe (Jev's provider) does not train on inputs but keeps them "as long as reasonably necessary"; no ZDR. Real H3 scene text sent to Jev is therefore retained. L2 provider is a setting: `jev` (default, CEO's pick) or `deepseek` (V4 Flash ZDR).
- Account: CEO 2026-10-03 chose Google AI Ultra on pass.gob1 for safe takes only (overrides "never pass.gob1" for safe takes).

## Build (2026-10-03)
- task-541e46b2: studio safe-split router, 4 layers, colab stub backend.
- task-c99d48d6: Colab CLI spike, one synthetic safe clip, cap 20 CU, leaves scripts/colab/run_take.py.
- One probe with synthetic, non-CEO text answers both. Cost under $0.001. Needs CEO OK of the amount.

## UI
- `/scenes`: each take shows its route (RunPod / Colab) and a one-word reason (`writer`, `jev`, `words`, `ref`). No text, no scores beyond the label.
- A per-batch switch "allow Colab" in Settings, default off.
- The user can force any take to RunPod. The user cannot force a take with a failed scan to Colab.

## Colab backend (separate build, after the account exists)
- `colab run` per job, outbound pull from our queue. No web UI, no tunnel.
- Weights from Hugging Face, timed on the first run.
- Outputs return to our storage, then the same take stitching and the hard-cut episode join as RunPod.
- Same model, same workflow, same seed rule as RunPod, so a Colab take and a RunPod take cut together cleanly.

## Prerequisites the CEO owns
1. A dedicated Google account (own phone, own card), never signed into the CEO's browser profile.
2. Which Google AI plan is held (AI Pro ฿750 or Ultra ฿3,500), and any CU pack spend.
3. OK for the Jev probe amount.

## Tests (when built)
- Fake classifiers: every layer's fail-closed path routes to RunPod.
- A take with one risky scene stays whole on RunPod.
- A take with a flagged reference image stays on RunPod.
- Switch off = byte-identical to today's queue.
- Synthetic fixtures only, own temp `STUDIO_DATA_DIR`, ports 4190-4199, never :4100.
