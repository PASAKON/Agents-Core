---
question: What is MYPASAKON's real speaking-style signature (particle frequency, n-grams, opener/closer patterns, sentence rhythm, disfluency rate) measured from actual spoken clips, versus what a script written to sound natural actually produces?
date: 2026-09-23
sources:
  - internal — 19 MYPASAKON rawcut clips (Drive, transcribed via fal-ai/whisper, language=th)
  - internal — SPOKEN_A.txt / SPOKEN_C.txt (2 pre-existing transcripts supplied with the task)
  - mooniex-agents prototypes/mypasakon-voice/analysis.md (full numbers)
  - mooniex-agents prototypes/mypasakon-voice/SCRIPT-v3.md (the script rewritten to this signature)
measured_by_us: yes
refresh_after: 2027-09-23
confidence: high
---

## 🟢 DURABLE — measured from the CEO's own real speech, not felt

Method: 19 MYPASAKON rawcut clips downloaded from Drive one at a time (video
deleted immediately after audio extraction), transcribed via `fal-ai/whisper`
(`language=th`), combined with 2 pre-existing sample transcripts
(SPOKEN_A/C) into one 45,998-character corpus (21 files). Word segmentation
for n-grams via pythainlp `newmm` (Thai has no whitespace word boundaries).
Full script and output: `mooniex-agents` repo, `prototypes/mypasakon-voice/`
(`transcribe_clip.py`, `analyze_style.py`, `analysis.md`).

**A 2-file sample overstates a filler-particle rate by 64%.** The task's own
starting assumption — "นะครับ 14.9 per 1,000 characters in real speech" —
came from measuring only the 2 small pre-supplied sample files (6,693
chars). Across the full 21-file, 46K-char corpus the real rate is **9.11 per
1,000**, 39% lower. Small samples of spoken-style corpora can badly
overstate a rate; the fix was simply measuring more of it.

**"ครับ" almost never stands alone in real speech — it is glued to "นะ"
95%+ of the time.** Standalone ครับ (not preceded by นะ) measures **0.39 per
1,000 characters**, versus นะครับ's 9.11/1,000. A script written to "sound
natural" (SCRIPT-v2, an earlier ClaudeCode draft for this same channel) used
bare ครับ at 5.61/1,000 — 14x the real rate. Bare ครับ reads as written
Thai; real MYPASAKON essentially always says นะครับ.

**First-person "ผม" is used far less in real speech than a written script
assumes.** Real rate: 1.85/1,000. SCRIPT-v2 used it at 19.65/1,000 — over
10x too much. Thai naturally drops the subject pronoun in speech more than
in writing; explicit "ผม" turned out to be the single strongest tell that a
line was scripted rather than spoken.

**Average sentence length (cut at นะครับ/ครับ) is 102.5 characters** across
447 sentences — nearly double a deliberately-paced script line. He rarely
lands นะครับ as a hard stop; the dominant bigrams are `นะครับและ...`
(37 occurrences) and `นะครับแล้วก็...` (22), i.e. he chains the next clause
onto the particle instead of pausing there. The breath rhythm is long
run-ons connected by และ/แล้วก็, not short punchy beats.

**Openers: 4 distinct types across 19 clips, zero greeting warm-ups.** No
clip opens with สวัสดี/หวัดดี. The 4 real patterns: listicle tease ("นี่เป็น
N ข้อ/เทคนิค/สัญญาณ...", 4/19), conditional "ถ้าคุณ..." (3/19),
narrative/biography hook about a named trader or event (5/19), and direct
question or flat declarative straight into content (7/19).

**Closers: 4 distinct CTA moves, often stacked two-deep as the final beat.**
Comment-below (6/19), risk disclaimer as the literal last sentence — "การ
เทรด/ลงทุนมีความเสี่ยงสูง ศึกษาให้มากพอ..." — (6/19), share-with-a-friend
(4/19), broker link/promo (4/19).

**Accidental back-to-back repetition is rare, not a constant tic — 7
occurrences in 45,998 characters (~1 per 6,570 chars).** Only 2 of the 7 are
genuine verbal stutters (e.g. SPOKEN_A's "และที่สําคัญนะครับ" ×2
back-to-back, the CEO's own cited example of what to avoid); the rest are
short-phrase coincidences from the tokenizer, not real disfluency. A script
asked to avoid repeated sentences does not need to work hard to stay
faithful to the real thing — the real thing rarely does it either.

## Frequency table (per 1,000 characters), real corpus vs. a written script

| term | real (46K-char corpus) | SCRIPT-v2 (an earlier written draft) |
|---|---|---|
| นะครับ | 9.11 | 11.23 |
| ครับ (all occurrences) | 9.50 | 16.84 |
| — standalone ครับ only | 0.39 | 5.61 |
| ผม | 1.85 | 19.65 |
| คุณ | 2.43 | 0.00 |
| เพื่อนๆ | 0.48 | 2.81 |
| เลย | 1.50 | 6.32 |
| ก็คือ | 0.48 | 1.40 |
| เนี่ย | 0.59 | 0.70 |
| นะฮะ | 0.11 | 0.00 |
| ทุกคน | 0.43 | 0.00 |
| จริงๆ | 0.26 | 0.70 |
| แบบ | 1.61 | 2.11 |
| คือ | 1.33 | 2.11 |

Top n-grams (2-5 words) by frequency, beyond นะครับ itself (411): การเทรด
(44), ในการ (42), จะเป็น (35), มากๆ (29), ข้อที่ (28), ไม่ได้ (27), ใครที่
(25), นักเทรด (23), ก็คือ (22), เราจะ (22), ที่ผม (20), เพื่อนๆ (19),
ไม่มี (19), ไม่ว่า (17), หลายคน (17), ถ้าคุณ (17).

## Method note worth keeping

Word-level n-gram and phrase-repetition analysis on Thai text requires
tokenization — there are no whitespace word boundaries. `pythainlp` is not
installed system-wide on the Mac (Homebrew-managed Python refuses global
`pip install` per PEP 668); it was installed into an isolated venv inside
the session's scratchpad directory instead, leaving the system Python
untouched. Simple substring frequency counts (§ frequency table above) don't
need tokenization at all — only the n-gram and repeated-phrase detection do.
