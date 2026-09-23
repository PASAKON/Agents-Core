# EP57 up-skill proposal — for the CTO to apply to config/decisions/bl.*.yaml

Held-out criteria-example candidates drawn from EP57's own lines (task-501f1d89). I did not
touch config/decisions myself — these are proposals, per the skill's own split (worker reports,
CTO folds in).

## 1. bl.beat — attribution vs. display (CURIOSITY-3, the one real miss)

Jev answered `bl.beat`="show" at confidence 0.46 for CURIOSITY-3
("วิกิเอฟเอ็กซ์เขียนไว้ด้วยว่าหน่วยงานการเงินของอังกฤษไม่พบข้อมูลเจ้านี้เหมือนกัน" — "WikiFX also wrote that
the UK's financial regulator found no record of this firm"). The writer's own `beat` column says
`verdict`, and that is correct: the line reports what a THIRD PARTY (WikiFX) wrote, it is not itself
introducing a new thing on screen right now — the actual FCA-search evidence for that claim already
aired two lines earlier at MAIN-12. Never applied (confidence was below the 0.95 gate either way), so
this is not a `jev_wrong_at_gate` case, but it is a clean miss worth a criteria example:

**Proposed example for `bl.beat`:** a line that paraphrases/reports what another source (WikiFX, a
regulator, etc.) said elsewhere is `verdict`, even when its subject sounds visual — only the line that
actually puts new evidence on screen for the first time is `show`.

## 2. bl.entry — the site has no gate, but its accuracy is bottlenecked by the PRECEDING line's bl.beat

All 3 of my bl.entry overrides (CURIOSITY-3, CURIOSITY-4, SUMMARY-4) trace to the same root cause:
Jev's own state for line N's `bl.entry` question is built from Jev's own (ungated, sometimes wrong)
guess of line N-1's beat, not the writer's beat. When CURIOSITY-3's beat flips from Jev's "show" guess
to the correct "verdict", CURIOSITY-4's entry (which follows it) flips too (composite-swap "other" →
leaving-composite "hard_cut"), purely as a downstream consequence.

**Proposed fix, not just an example:** feed `bl.entry`'s state builder the PRECEDING line's writer
`beat` (SCRIPT.tsv column, already authoritative and free) instead of re-deriving it from a fresh,
ungated `bl.beat` call. This removes an entire class of error at zero extra Jev cost.

## 3. bl.beat (th) — MAIN-8, the one line that cleared the measured 0.95 gate

MAIN-8 ("คะแนนความน่าเชื่อถือที่วิกิเอฟเอ็กซ์ให้ อยู่ที่หนึ่งจุดเก้าเก้าจากสิบ") was answered `show` at
confidence 0.98 and matched the writer's own beat exactly — the one row where the gate applied Jev's
answer as-is, and it was right. Worth keeping as a positive held-out example: a line stating a specific
number that is about to appear on screen (a score, a count) is the channel's clearest `show` signal.

## 4. SUMMARY-4/5/6 — a "show" line with no real footage is not always avatar-composite

The script itself flagged these three as "GRAPHIC checklist card ... no real footage" rather than
avatar+evidence composite. `bl.entry`'s options (shrink/hard_cut/other) assume a composite-avatar
outcome; there is currently no way to say "this show line renders as a pure kinetic graphic, no avatar
at all." Not a wrong answer exactly, but a missing option worth a criteria note if graphic-checklist
beats become common across episodes.
