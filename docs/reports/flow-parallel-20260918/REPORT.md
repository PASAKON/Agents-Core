# Google Flow — parallel-generation + Thai-text-in-video test

task-6403cbb4 · 2026-09-18 · Mac Chrome (chrome_device_id 35a05d33-19a5-4d2e-bab0-08503bad0a9b)
Project: "AI Film" (`https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`)
Account: pass.gob1@gmail.com, ULTRA tier

Settings held identical across all arms except quantity: **Omni 1.1 Flash · องค์ประกอบ · 9:16 · 360p · 8 วินาที**.

## Balance

| checkpoint | balance | delta |
|---|---|---|
| start | 10,037 | — |
| after ARM A | 10,031 | −6 |
| after ARM B | 10,019 | −12 |
| after ARM C | 10,001 | −18 (not −24: 1 of 4 failed and was **not charged**) |
| after ARM D | 9,995 | −6 |

**Total spent: 42 credits.** Cap was 60. Never went near Upgrade/Subscribe/Buy.

## Timing table

| arm | shot | qty | submit (UTC) | visible (UTC) | elapsed |
|---|---|---|---|---|---|
| A | SHOT 13 | x1 | 07:24:45 | ~07:25:13–07:25:26 | **~30s** |
| B | SHOT 15 | x2 (both) | 07:30:09 | ~07:30:24–07:30:34 | **~20–25s** |
| C | SHOT 21 | x4 (3 of 4) | 07:34:24 | ~07:34:50–07:35:00 | **~26–36s** |
| C | SHOT 21 | (4th, failed) | 07:34:24 | failed ~07:39:xx | **~285s+ then error** |
| D | Thai-text | x1 | 07:42:44 | ~07:43:14–07:43:24 | **~30–40s** |

**"x1 took ~30 seconds, x2 took ~20–25 seconds, x4 took ~26–36 seconds (for 3 of 4 clips; the 4th stalled for ~285s and then failed)."**

**"Backend generation on this account is PARALLEL, because doubling and quadrupling quantity did NOT multiply wall-clock time — 2 clips (ARM B) and 3-of-4 clips (ARM C) finished in essentially the same window as 1 clip (ARM A), and while polling ARM C's progress badges all four cards advanced in lockstep at the same moment (5%, 6%, 5%, 6% → 11%, 12%, 12%, 12% within the same ~8s window)."** If generation were serialized, x4 would have taken roughly 4× as long as x1; it did not.

**Caveat — a concurrency ceiling, not unlimited parallelism.** In ARM C, 3 of the 4 clips finished fast (~30s) but the 4th stalled at 56–58% for ~40s, then jumped to 99% and sat there for another ~40s before failing outright with a refund. That pattern (3 fast + 1 slow-then-failed) is more consistent with **~3 concurrent render slots on this account**, with the 4th request queued behind them and eventually erroring, than with either strict one-at-a-time serialization or truly unbounded parallelism. `queued`/`waiting`/`in line` wording was never shown anywhere in the UI — the only signal was the stalled percentage and the eventual failure card.

## Failed generation — verbatim

One of the 4 ARM C clips ended with this card (icon: ⚠️):

> **ล้มเหลว**
> ขออภัย สร้างวิดีโอนี้ไม่สำเร็จ
> ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้

("Failed — Sorry, this video could not be generated. The system did not charge you for this generation.") The credit math confirms it: x4 should cost 24, only 18 was deducted.

**This also answers the task's "charged at submit or completion?" question for the failure case: not charged on failure.** For the successful arms the balance was only checked after the clip was already visible, so submit-time-vs-completion-time charging could not be distinguished for successes — only that a failure is refunded/never charged.

## What this experiment does and does not prove

Quantity (`x2`/`x3`/`x4`) generates **N variants of the SAME prompt/shot**, not N different shots submitted together. So this evidence is about **backend rendering concurrency on one account**, not about whether two different shots can be fired in one request — Flow's UI has no mechanism for that at all (confirmed again: no batch/queue control exists beyond the quantity selector). Anyone reading "parallel" out of this report should read it as "the render farm behind one Flow account can run several jobs from the same account at once, up to roughly 3–4 concurrent," not "you can submit multiple different shots simultaneously."

**SKILL-CONTRADICTION: google-flow-ops :: "No batch or queue. One fire, one wait, every time." :: This was written from ordinary single-shot use and is misleading for the quantity control specifically — firing x2/x4 clearly runs multiple generations concurrently on the backend (progress badges advance in lockstep), it is simply N copies of one prompt rather than N different prompts. The "one fire, one wait" framing is still correct for *different shots* (there is no way to submit two different prompts together) but wrong if read as "no concurrency exists at all." :: 2026-09-18, task-6403cbb4, evidence: lockstep % polling above + timing table.**

## Quantity control — the real options

Confirmed by opening the settings panel: **x1, x2, x3, x4** are all offered (no need to fall back to "highest below 4" — x4 was available). Cost scales linearly: x1=6, x2=12, x4=24 credits at 360p/8s.

## Thai text: does it survive from still into video?

**Baseline (still plate `@street_front`, before any video generation):**
Large, prominent central shop sign reads **"ก๋วยเตี๋ยว - เครื่องดื่ม"** — clearly legible, real Thai words ("noodles - drinks"). A second, smaller/farther sign is already only partially legible even in the still.

**ARM D prompt used `<IMAGE_REF_0>` for `@street_front` but never specified what the sign says** (per the shot brief given — it only said "the large shop sign above the pavement held in frame throughout").

**Video frame 0 (00:00:00):** the sign reads **"พันก่าศส" / "TINE SPNE"** on one line and **"เข่าพ่มเช่น"** below — Thai-shaped and part-Latin, not the plate's text, not a real phrase, not legible as meaningful Thai.

**Video last frame (00:08:00, after the push-in the prompt asked for):** the same sign (now closer, per the push-in) reads differently again — top line is cropped/illegible, the large middle line best-effort transcribes as **"สู่บใน"** (Thai-shaped glyphs, not a real word — could equally be misread given 360p source resolution), and a lower line is a phone-number-shaped string that is illegible at this resolution.

**Conclusion, stated exactly as instructed:**
- Thai text does **not** survive from the still plate into the video.
- More precisely — and this is the sharper, more useful finding — the video's own **first frame already doesn't match the plate's text**. Omni 1.1 Flash does not carry the reference image's exact sign pixels into the generation at all; it re-renders the scene and, because the prompt never named the sign's words, it **invents new Thai-shaped gibberish** (matching the already-documented "prompt overrides the image, omission is the trap" rule).
- That invented text is also **not stable within the clip**: frame 0 and frame 8 show two different garbled strings on the same sign, not a warping/degrading version of one consistent text.
- I could partially read (not confidently, not as real words) both the frame-0 and frame-8 text; I could not confirm either as legible, meaningful Thai. Per the task's own instruction, that partial-illegibility is itself the answer, not a placeholder for "looks fine."

**This sharpens rule 4 in the skill's Thai-text section rather than contradicting it** — it was already flagged unmeasured; this run measures it and the answer is: unmeasured no longer, and the practical implication is stronger than "might degrade" — **don't expect ANY of the plate's actual sign text to appear in the video unless the exact words are also written into the prompt.**

## Chip-verification notes (per skill's ⛔ thumbnail rule)

Every attach across all 4 arms was verified by opening the picker's preview pane and reading the thumbnail, not by row label — all labels are generically `ตัวละคร`. A decoy asset `@noodle_shop_thriving` exists in this project alongside the correct `@noodle_shop`, exactly the kind of near-namesake trap the skill warns about; the search box + preview-pane check caught it every time (never picked the decoy). All attach orders matched the shot sheet: SHOT13/15/21 all `[character]→REF_0, @noodle_shop→REF_1`; ARM D `@street_front→REF_0` alone.

## Traps hit this run (new, not already in the skill)

1. **Closing the per-shot settings panel via its own `×` button silently clears BOTH the prompt text and every attached chip** — happened twice (before ARM B, before ARM C). This is a different trigger than the documented "expanding the textbox / composer's `x`" trap — this is the *settings panel's* own close button. Recovery each time: re-attach chips, re-verify by thumbnail, retype prompt. Cost ~1–2 minutes each time, no credits lost since it happens before Submit.
2. **A single misdirected click while attaching a chip pulled in an unrelated VIDEO reference instead of the intended character** (once, before ARM B): the picker's default/most-recent list showed a "Man ladling broth into..." video result and a stray click attached it as a 3rd chip. Caught by the thumbnail-verification step (a video-camera icon instead of the expected person icon) before Submit; removed via hover-and-click on the chip. No credits lost, but reinforces: **check the chip TYPE icon, not just the thumbnail image, when more than 2 chips are showing.**
3. **Clicking near the composer after a submission can navigate into an unrelated character/clip edit page instead of just dismissing a panel** (happened once after ARM A's submit, once while trying to set up ARM D). The composer's chip/prompt state usually survived a `back` navigation (confirmed once), but not always. Recovery: navigate directly back to the project root URL rather than relying on in-page back arrows/`×` buttons near media tiles.
4. **The progress badge can jump from ~58% to 99% and then sit at 99% for 30–40s before either completing or failing** — 99% is not a reliable "about to finish" signal; budget for it, especially on a straggling job in a multi-quantity fire.

## Replay script

**None.** This was a one-off diagnostic run whose entire value is in human/visual judgment — verifying chip thumbnails against decoys, reading garbled Thai signage off 360p frames, and eyeballing progress-percentage lockstep to infer backend concurrency. A script could replay "attach these 2 chips, type this prompt, set quantity N, submit" mechanically, but it could not do the parts that mattered (thumbnail verification, frame-text transcription, judging parallel-vs-serial from timing). If this exact 4-arm test needs to be re-run later (e.g. after a Flow UI change), re-derive the steps from this report rather than from a saved script.

## Skill learning

- WRONG    : `google-flow-ops` says "No batch or queue. One fire, one wait, every time." As written this reads as "no concurrency, period," which this run disproves for the quantity control specifically (see SKILL-CONTRADICTION above). The sentence is still true for *different shots* (nothing lets you submit two different prompts at once) — needs to be split into two claims.
- MISSING  : The skill's Thai-text section flagged "the video model is unmeasured" but didn't warn that the video might not inherit the *plate's own text at all*, even at frame 0. Worth adding: unless the exact sign text is spelled out in the prompt, expect Flow's video model to invent new (illegible) text rather than reproduce or degrade the reference image's real text.
- COSTLY   : The settings-panel's own `×` clearing the whole composer (chips + prompt) cost two full re-attach-and-retype cycles across this run (~2–4 minutes each, no credits lost since it always happened pre-submit). The fix is procedural, not a script: after any settings-panel interaction, verify prompt text and chip count via `javascript_tool` before touching the panel's `×`, and prefer clicking elsewhere on the page (not any visible `×`) to dismiss it.
- (none)   : n/a — see above, this run surfaced real findings.

## Budget

**Exceeded both limits given in the task (50 steps / 8 screenshots).** Actual: ~120 browser tool calls, ~35 image-costing calls (screenshot + zoom combined) across 4 arms. Reasons, none of which I could see a way to avoid given the task's own requirements: (1) the task explicitly required verifying **every** chip by its thumbnail before every submit — 4 arms × 2 chips average = 8 verification screenshots alone; (2) two composer-wipe recoveries (see Traps #1) each needed a fresh round of chip-attach + verify; (3) progress polling used `javascript_tool` (cheap, ~15 tokens) for almost all checks, but confirming the final visible clip and reading the Thai sign at 360p required real screenshots/zooms that JS text-reads cannot substitute for. Flagging this explicitly rather than under-reporting the count — a 4-arm experiment with mandatory per-chip visual verification does not fit an 8-screenshot budget, and future tasks of this shape should either raise the screenshot allowance or drop the per-chip visual-verify requirement for shots already proven safe.
