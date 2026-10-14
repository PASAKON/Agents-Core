# H3 Colab + RunPod: end-to-end test plan, after Task C merges

CTO, 2026-10-03. CEO approved: "หลังจากเสร็จแล้ว อนุมัติให้ทดสอบได้เลย ที่ความละเอียด 360p". The CTO runs this on the live studio (:4100) after task-1a8338d9 merges and the live queue is idle.

Content: every scene is a synthetic test prompt written for this test. The ref is the synthetic image from `scripts/colab/make_ref.py`, in a test entity named `TEST-colab`. There is no H3 story text and no H3 entity. All clips are 360p and 124 frames (5 s).

## Before the merge (already in Task C, done by the worker)

- Offline, fake CLI, through the real tick. These cases are covered:
  - unavailable falls back to RunPod;
  - chain inputs;
  - a failure mid-take goes to RunPod;
  - the tripwire;
  - the CU and minutes caps;
  - warm VM reuse and the idle stop;
  - the dead-man switch, with a fake clock;
  - a mixed-backend episode, where finish order is not join order;
  - the new five risky rules;
  - the preview route;
  - with the switch off, nothing changes.
- One live batch, on Colab only, at 360p: 6 scenes, N=3, so 2 takes on one warm VM. It proves the take stitch and the episode join live, plus one dead-man proof. Cap 6 CU (item 14).

## After the merge (CTO, live)

| # | What | How | Pass when | Cost |
|---|---|---|---|---|
| T1 | Every routing rule | Preview route, 12 synthetic scenes: ordinary adults; child extra; kiss; "ถอดรองเท้า"; "ถอดเสื้อ"; swimwear with no nudity; bed with no nudity; child + romance with no deny word; gore; writer rating risky; an empty prompt; N=1 per scene | Each one gets the expected backend and layer | under $0.01 (Jev) |
| T2 | Colab path, warm VM | 6 safe scenes, N=3, so 2 takes, both Colab | Pill goes off → setting up → rendering → idle. Take 2 does not launch a second VM. The clips chain. The episode joins 2 takes in order. CU per take is reported | about 1–2 CU (estimate) |
| T3 | Both backends at once | 6 scenes, N=3. Take 1 has a kiss, so it goes to RunPod. Take 2 is safe, so it goes to Colab | Both render at the same time. The episode orders the takes by scene number, whichever finished first | RunPod about $1 (estimate), Colab about 1 CU |
| T4 | Stop button | During a T3 Colab take, press "ปิด Colab" | `colab sessions` = 0. The take's unfinished scenes go to RunPod and finish there. The episode still forms | inside T3 |
| T5 | Idle stop | After T2/T3, leave Colab idle | The VM is gone after `colabIdleStopMin` (default 10 min) | about 1.5 CU |
| T6 | End state | — | `colab sessions` = 0. The RunPod pod has stopped. Totals are reported: $ and CU | — |

**Never tested live, on purpose:** the post-render tripwire and the NudeNet ref flag. Testing them would mean sending nude content to Colab, which is the exact thing the rules forbid. The offline tests cover both.

**Money cap:** RunPod $1.50 for the whole run (balance $2.60, gate margin $0.50). Colab: 6 CU in total. Stop and ask the CEO if either is reached.

## CEO rulings 2026-10-03 06:0x

- "Ok": the RunPod cap of $1.50 for T3–T4 is approved.
- **"ห้ามแอบดูคลิปที่ทำก่อนหน้านั้นของฉันในคลัง":** never open, play, frame-grab, ffprobe or describe any clip, take or episode in the studio library that is not from this test's own `TEST-colab` batch.
  - When the CTO reads `/api/queue`, `/api/takes` or `/api/episodes`, filter by the test batch id BEFORE printing anything.
  - Every check runs only on files named after the test batch's own ids.
