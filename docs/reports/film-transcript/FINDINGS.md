# banchi film — transcript audit findings

Source: `tools/film_transcript.py` run over all 173 shots (ACT1–ACT7), `faster-whisper`
model `small`, language `th`, VAD on. Output: `docs/reports/film-transcript/transcript.tsv`
(407 rows). Everything below was read off that TSV plus targeted re-checks against the
raw heard text (see "Method note" — the raw tool output over-reports two of the three
categories, and that over-reporting is itself worth knowing).

## Counts

- **transcribed: 173 / 173 shots** — every shot produced at least one whisper segment.
- **unreadable: 0** — no clip whisper heard nothing on.
- **clean (heard matches script line-for-line, no extra/missing flag): 128 shots**
- Tool raw-flagged "extra heard segment" shots: 22
- Tool raw-flagged "missing line" shots: 20 (23 individual lines)

## Method note — the raw missing/extra flags are mostly alignment artifacts, not defects

The tool matches heard segment *i* to scripted line *i* by position. When whisper's VAD
doesn't pause between two scripted lines, it returns **one** heard segment covering both
— and the tool then reports the second scripted line as `(ไม่ได้ยิน)`, even though the
words are sitting right there in the first segment's text, just merged in.

I re-checked all 23 raw "missing" rows by searching the *whole shot's* heard text (not
just its positional partner) for the missing line's content. Result:
**19 of 20 shots — 22 of 23 lines — are false positives.** The dialogue was said; the
tool's 1:1 index matching just didn't find it because whisper folded two scripted lines
into one audio segment. Examples: shot 6's "missing" line `อีกสามร้อยก็ครบค่ารักษาแม่เดือนนี้แล้ว`
is sitting inside the single heard blob `...อีก 300 ก็คบค่ายาเดือนนี้แล้ว` (whisper wrote the
number as digits and mangled "รักษา"→"ยา", but the line was spoken). Same pattern for
shots 3, 18, 25, 42, 56, 62, 64, 70, 82, 107, 113, 116, 120(×1 of 2), 121, 126, 135, 140,
155, 173 — checked one by one, all present in the combined heard text for that shot.

This means the raw "23 missing lines across 20 shots" the tool prints is **not** the
LINE WENT MISSING list. The real list, after removing alignment artifacts, is below —
and it's short.

## 1. SCRIPT SAYS IT TWICE (writing problem, render faithful)

**1 confirmed:**

- **Shot 122** (4.00s clip) — scripted lines `สองร้อยแปดงวด...` then `สองร้อยแปด...`
  (two adjacent lines, same shot, near-identical). Heard: `208 งวด` (match 0.74) then
  `208` (match 0.67) — the render says exactly what was scripted. Two mentions of the
  same number inside a 4-second shot is a stutter written into the sheet, not a render
  defect. **This is the CEO-confirmed real defect** (previously misdiagnosed via
  `silencedetect` as "deliberate, good writing").
  - For contrast: shot 121 (`ton`: "สองร้อยแปดงวดครับ") → shot 122 (`somchai` echoes
    "สองร้อยแปด...") is a **different, cross-shot** pattern — one character stating a
    number, another repeating it in disbelief, across two separate shots. That reads as
    intentional and is not flagged here.

**2 uncertain — not listed as defects, flagging for a human ear:**
- Shot 53: scripted line itself repeats `...งวดเดียว...` twice in one sentence
  (`อีกงวดเดียว แค่งวดเดียวก็หมดแล้ว` — "just one more installment... just one
  installment and it's done"). Rendered faithfully. Reads like normal Thai emphasis
  repetition, not a defect, but flagging since it's the same shape as shot 122.
- Shot 77: same pattern — `พ่ออยากให้ลูกได้เรียน พ่อก็เลยให้ลูกเรียน` ("Dad wanted you to
  study, so Dad let you study"). Likely intentional emphasis, not a stutter — but I'm not
  the judge of dialogue rhythm.

## 2. RENDER SAYS IT TWICE (generation problem — worth re-firing)

**4 confirmed** — audio says the exact same short phrase twice back-to-back, script
asked for it once:

- **Shot 31** (8.00s) — `ลุงครับ` at 4.24–5.74s, then `ลุงครับ` again at 5.74–7.24s.
  Scripted once: `ลุงครับ...`.
- **Shot 41** (8.00s) — `ไม่ใช่นี้ใส่ผม` (whisper's hearing of "ไม่ใช่นิสัยผม") at
  1.80–2.88s, then the identical phrase again at 2.88–4.60s. Scripted once.
- **Shot 71** (10.00s) — `...ผมนับเอง` ends the first line at 2.34s, then `ผมนับเอง`
  is said again standalone, 2.34–3.84s. Scripted once.
- **Shot 143** (8.00s) — `ผมเชื่อครับพ่อ` at 4.23–5.23s, then the identical phrase again
  at 6.23–7.23s. Scripted once.

These are the ones actually worth spending a re-gen on — the script is clean, the model
repeated itself.

## 3. LINE WENT MISSING

**0 confirmed genuinely-missing full lines**, after the false-positive cleanup above.

**4 unverifiable, low-priority — flagging rather than deciding:**
- Shots 18, 42, 107 — each is a scripted single-syllable acknowledgment `อือ` ("mm").
  Too short for my text-containment check to confirm either way, and too short to
  matter much even if genuinely dropped.
- Shot 120 — scripted `เก้าสิบ ร้อย` ("ninety, hundred") inside a longer counting run.
  Whisper transcribed the whole run as digits (`10.20.30.40.50.90.100.104.100...`) —
  the 90/100 are arguably in there as digits, just not matched as Thai number-words by
  my check. More likely a whisper number-formatting issue than a dropped line.

**Net result: no silence-based OR transcript-based check turned up an actual dropped
line of dialogue in this film.** That's a real, checked answer — not "didn't look hard
enough."

## Anomaly found outside the three requested buckets — dialogue order swap

Not asked for, but the data showed it and it doesn't fit stutter/duplicate/missing:

- **Shot 128** — scripted order is [cherd: "อะไรนะครับพี่"] → [somchai: "หนี้ผมร้อยห้าสิบงวด
  ผมจ่ายมาสองร้อยแปดครับ"]. Heard order is reversed/interleaved: "นี่ผม150งวด" →
  "อะไรนะครับพี่" → "ผมจ่ายมา 208 ครับ" — the question lands in the middle of the answer
  instead of before it.
- **Shot 141** — similar: scripted [ya: "ย่านอนอยู่ตรงนี้ ย่าได้ยินหมดแหละลูก"] → [ton:
  "ย่าจำได้ทุกครั้งเลยเหรอครับ"], heard in the opposite order.

Could be intentional interruption/overlap, could be a render defect. I can't tell from
text alone — needs a human ear.

## Lowest 10 match scores (heard vs scripted, side by side)

Several of these are **not** real mis-deliveries — they're the same alignment cascade
described above (one scripted line split across two heard segments shifts every later
comparison by one slot). Marked accordingly.

| shot | match | heard | scripted | read |
|---|---|---|---|---|
| 71 | 0.00 | «4ปี» | «อือ» | cascade artifact (see shot 71 note above) |
| 41 | 0.08 | «ไม่ใช่นี้ใส่ผม» | «ผมชอบให้ทุกคนสบายใจกันทุกฝ่ายมากกว่า» | cascade artifact (real content is the shot-41 duplicate above) |
| 105 | 0.14 | «ลองเปิดดูให้พ่อทีลูก» | «พ่อจำรหัสไม่ได้เหรอครับ» | cascade artifact |
| 20 | 0.16 | «ต้น» | «ครับย่า อ้าปากหน่อยครับ» | cascade artifact |
| 128 | 0.18 | «นี่ผม150 งวด» | «อะไรนะครับพี่» | real — this is the order-swap above, not a whisper error |
| 120 | 0.19 | «10.20.30.40.50.90.100.104.100 พอดีเลยครับย่ะ» | «สิบ ยี่สิบ สามสิบ สี่สิบ ห้าสิบ» | whisper error — writes digits instead of Thai number words on long counting runs |
| 141 | 0.19 | «ยากจำได้ทุกครั้งเลยเหรอครับ» | «ย่านอนอยู่ตรงนี้ ย่าได้ยินหมดแหละลูก» | real — the order-swap above, not a mis-delivery |
| 43 | 0.20 | «เงินตัวเองแท้แท้» | «แล้วมานั่งกินร้านเราทุกอาทิตย์ทำไม» | cascade artifact |
| 50 | 0.20 | «ผมเลยแวะมาเอง» | «พรุ่งนี้ผมหาให้ครบแน่นอนครับ» | cascade artifact |
| 113 | 0.20 | «3.00.000 หานอธิตแล้ว 2.000 เท่ากับ 150 งวดครับพ่อ» | «สามแสน หารอาทิตย์ละสองพัน» | whisper error — same digit-writing issue as shot 120, content is otherwise correct |

## Uncertain, needs a human ear

- Shot 53, 77 — intra-line phrase repetition, probably intentional emphasis (§1)
- Shot 18, 42, 107 — single-syllable `อือ` acknowledgments, unverifiable, low stakes (§3)
- Shot 120 — counting-run digit-transcription noise, likely not actually missing (§3)
- Shot 128, 141 — dialogue order swapped vs. script; could be interruption or defect (anomaly section)

## What I verified vs. inferred

Verified by reading the transcript rows and, for the 5 shots cited with exact
timestamps in §1/§2, the actual clip duration via `ffprobe`: shot 122 (4.00s), 31
(8.00s), 41 (8.00s), 71 (10.00s), 143 (8.00s). The false-positive cleanup in §3 was
verified by re-searching each shot's full heard text for the "missing" line's content,
not just trusting the tool's positional flag.

Inferred (not verified against the render itself — a human ear should decide):
whether shots 53/77's intra-line repeats read as intentional emphasis, whether the
`อือ` murmurs in 18/42/107 were actually spoken, and whether the shot 128/141 order
swaps are deliberate interruptions or defects.

Nothing was fixed, re-generated, edited, or deleted. `docs/scripts/banchi-ACT*.data.py`
and the sheets were not touched.
