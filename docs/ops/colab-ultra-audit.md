# Colab on Google AI Ultra — measured, 2026-09-18

Measured by `browser_operator` on winbox (task-78b45604) against the CEO's Ultra
subscription (pass.gob1@gmail.com). **Everything in the "measured" table was read
off the screen.** Anything derived from it is marked as such, and the one number
that carries real uncertainty says so.

Ordered by the CEO (relayed CTO→CTO from MAC CTO #b98a15db): decide whether
Cookie Run detector training moves off RunPod onto Colab.

## Verdict

**Yes — move Cookie Run training to Colab. RunPod is not needed for this
workload.**

The job we actually want to run costs **under 1% of one month's allowance**, on
a GPU better than anything we were renting.

## Measured

| | Reading |
|---|---|
| Colab plan badge | **`CO PRO+`** — Colab's UI has no "Ultra" badge at all |
| Entitlement (Settings → Subscription) | "ยินดีด้วย คุณได้สมัครใช้บริการแพ็กเกจ Google AI Ultra แล้ว…" |
| Compute units | **1001.32** at first read → the **1,000/month** tier, not 2,000 |
| Accelerators offered | CPU · **H100** · **G4** · **A100** · **L4** · **T4** · v6e-1 TPU · v5e-1 TPU · High-RAM toggle (present, default off) |
| Requested | H100 (strongest listed) |
| **Actually got** | **G4 = NVIDIA RTX PRO 6000 Blackwell Server Edition** |
| | Colab toast: "ประเภท GPU ที่เลือกไม่พร้อมใช้งาน คุณเชื่อมต่อกับ G4 อยู่ในขณะนี้" |
| VRAM | `nvidia-smi` 0 MiB / **97 887 MiB** · driver 580.82.07 · CUDA 13.0 |
| | torch total_memory **101.97 GB** |
| Burn test | balance 1000.73 → 999.23 over **606.995 s** measured in-notebook |
| **Burn rate** | **≈ 8.90 CU/hour** on G4 |
| Billing tail after delete | 999.23 → 998.48 over ~2 min, then **flat** (998.48 at +4 min) |

Not measured: idle-timeout warn/disconnect behaviour — would have needed a
connected-idle runtime held 60–90 min, which did not fit the window.

## The one number to distrust slightly

8.90 CU/hour is the honest arithmetic on the honest readings, but the operator
flagged that the balance was **already drifting before the loop started**:
1001.32 → 1000.73 across ~3–4 min of setup. That implies an idle rate of about
**10.1 CU/hour** — *higher* than the rate measured while the GPU was saturated,
which cannot be literally true.

So the balance readings are coarse or lag behind usage. Treat the real figure as
**roughly 9–10 CU/hour** and do not quote 8.90 as if it were tight. Pinning it
would take a longer run (30–60 min) and a separate pure-idle measurement; not
worth doing until something depends on the third digit.

## What that buys (derived)

| | at 8.9 CU/h | at 10.1 CU/h |
|---|---|---|
| GPU-hours per month | **112** | **99** |

| Job | CU | Share of month |
|---|---|---|
| IDM retrain, full corpus (est. 1 GPU-h) | ~9 | **0.9 %** |
| Policy training, large (est. 30 GPU-h) | ~267 | 27 % |

For comparison, ~112 h of RunPod L40 at $0.69/h (our own survey, RUNPOD-SURVEY.md)
is about **$78/month** — and the Colab hours are already inside the ฿3,500 Ultra
subscription, on a 98 GB Blackwell rather than a 48 GB L40.

**The money was never the constraint on this job.** The IDM retrain is about one
GPU-hour either way — under a dollar on RunPod, under 1 % of a month on Colab.
Colab matters for the job *after* it, and for not having to think about pod cost
again.

## Operating rules that follow from the measurements

1. **Delete the runtime, never just close the tab.** Idle connection burns CU at
   roughly the same rate as compute, and there is a **~2-minute billing tail**
   past the delete click.
2. **Ask for H100, expect not to get it.** We asked and were given G4. That is
   fine — G4 is the better card here anyway — but no schedule may assume a
   specific accelerator. Colab's own FAQ says resources are not guaranteed.
3. **Checkpoint any run over ~20 minutes.** Idle timeout is unmeasured, so an
   unattended long run is an unquantified risk. Our ~1 h IDM retrain should be
   written to resume from a checkpoint in Drive rather than restart.
4. **A fresh notebook is gated behind a Colab "Accept Terms of Service" modal.**
   The operator did not click it unilaterally — it asked its user and got explicit
   authorization first. Whoever opens the next notebook on this account hits the
   same gate; that is the correct instinct and should stay the norm.
5. **18+ work never touches this account.** Standing CEO ruling, unchanged by
   anything here: a suspension costs Ultra + 20 TB Drive + Gmail + YouTube + the
   Flow production; RunPod loses a $0.30 pod. Cookie Run training is the safe
   workload — plain notebook, no web UI, no faces, no adult content.

## Still open

- **Storage.** The 20 TB Drive plausibly settles LungNote a86c1bc6 (winbox
  modelplay hit frames, 15.6 GB and growing 2–4 GB/day, CEO-ruled tier A "never
  delete"): tar-per-session to Drive with a few days kept locally now costs
  nothing, and the ฿4–5K NVMe may be unnecessary. Not decided here — it changes
  a CEO ruling and belongs to him.
- **Idle timeout**, per above.
