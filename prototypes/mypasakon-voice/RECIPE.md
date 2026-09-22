# MYPASAKON — the CEO's cloned voice, the recipe that got approved

**Run it with `tts_clone.py`, do not re-implement it by hand:**

```bash
python3 prototypes/mypasakon-voice/tts_clone.py <script.md> \
        prototypes/mypasakon-voice/reference/REF-D2-approved.mp3 out.mp3
```

It refuses a band-limited reference, refuses a script containing `กู`/`มึง`,
re-splits any chunk that renders over 25 s, strips dead air, and refuses to hand back
a file that still has a silence over 0.6 s in it. The prose below is why each of those
exists.

CEO signed off on `reference/APPROVED-sample-120s.mp3` on 2026-09-23 ("Perfect เคาะ
อันนี้ผ่าน"). Everything below is what produced it. Every number here was measured,
not estimated.

## The call

```python
endpoint = 'bytedance/seed-audio-1.0'        # fal, queue API
body = {
  'prompt':        <one chunk of the script>,
  'audio_urls':    [<REF-D2 uploaded to fal storage>],
  'multilingual':  True,
  'output_format': 'mp3',
}
# submit to the full endpoint, poll the SAME path (this endpoint is two segments,
# so base == full; other fal models need the first TWO segments only)
```

**No `voice` field.** Passing a preset voice id alongside `audio_urls` is what the
reference is for; passing a BytePlus catalogue id returns 422 "voice does not belong
to this user" — that field only accepts voices this account owns.

**No prompt directive.** An accent instruction inside `prompt` measurably *hurt* once
a reference was attached (it reads as text to speak against, not as direction), and
the effect we thought we saw without a reference turned out to be run-to-run noise.

## The reference — this is the part that mattered most

`reference/REF-D2-approved.mp3` — 15 s cut from **27.5 s** into the audio of
`ทำไมกราฟถึง กระโดดเป็นกบ Roughcut.mp4`, Drive id `1Sgy4ewEBsL0DRpKUrExSltOG8Q0ybshu`,
in that clip's **Rawcut** folder under `ALL DRAFT/MYPASAKON`.

**A Rawcut beats an edited `Audio/` file, and the reason is bandwidth:**

| reference | boxiness | air 6-12k | bandwidth |
|---|---|---|---|
| old, from an `Audio/` folder (A) | 1.89 | 5.8 % | 10,154 Hz |
| old, from an `Audio/` folder (C) | 1.53 | 7.4 % | 10,260 Hz |
| **Rawcut D2 (approved)** | **1.25** | 6.7 % | **13,377 Hz** |
| Rawcut D1 (alt, more voiced) | 1.58 | 7.7 % | 13,494 Hz |

The edited files had been band-limited to ~10 kHz, so the model never heard the top
of the CEO's voice. The Rawcut carries 30 % more. `boxiness` = energy 200-500 Hz over
2-5 kHz; it is the number that tracks what the CEO calls "กล้อง ๆ".

Pick a window by measurement, not by ear: 100 ms RMS frames, take the 15 s window
maximising (fraction of frames above floor+12 dB) minus (local floor). D2 scored
65 % voiced at a −47.8 dB local floor.

## Chunking

Split the script on **blank lines**, pack paragraphs up to **330 characters** per
chunk, one API call each, then loudnorm `I=-18:TP=-2:LRA=11` per chunk, decode to
WAV, `concat`, re-encode. 1,470 characters became 7 chunks and 120.58 s.

Blank lines in the script are therefore breath points, and they are load-bearing —
they decide where the model is allowed to restart.

## What this beats, and why it is worth +$0.27 an episode

| | CEO's own voice | keeps `นะครับ` | timbre drift | per EP |
|---|---|---|---|---|
| **Seed Audio + Rawcut** | yes | **16/16 = 100 %** | 0.44 | $0.41 |
| MiniMax Speech 2.8 | no, preset | yes | untested | $0.17 |
| Gemini 3.1 Flash TTS | no | **drops them** | — | $0.14 |

**Gemini silently swallows `นะครับ` and `ครับ`.** Same sentence, same whisper pass:
MiniMax and Seed Audio both return them, Gemini returns neither. That particle runs
at 14.9 per 1,000 characters in the CEO's real speech — it is his breath, not his
politeness — so a model that eats it can never sound like him.

Timbre drift is the spread in boxiness *between* chunks. It halved when the reference
changed from an edited file (0.81) to the Rawcut (0.44). **That spread, not the mean,
is what reads as hollow** — the average of the rejected take was actually *better*
than the two 8 s takes the CEO had already approved, which is how we learned the mean
was measuring the wrong thing.

## Dead air — the defect that the first approved take still had

The CEO listened again and heard a long gap. It was **12.50 s of silence, from 86.96 s
to 99.46 s**, and it was NOT a join: the joins we make are clean (all seven chunks'
head and tail silence together came to 3.0 s of a 120 s file). **Seed Audio invents
silent holes inside a single long generation.** Chunk 6 ran 27.09 s and contained
14.83 s of speech; chunk 4 ran 28.20 s and hid eight smaller holes worth 3.01 s.

Every chunk under 19 s came back with none.

So the cap is a duration, not a character count. Characters were the wrong unit all
along — the same 330-character budget produced chunks between 8.1 s and 28.9 s,
because the model's speaking rate swings by a factor of three.

`tts_clone.py` enforces this: any chunk that renders longer than **25 s** is split at
the nearest `นะครับ`/`ครับ` and re-fired, every chunk is stripped of head/tail silence
and of any internal pause over 0.55 s, and the joined file is re-measured — if any
silence over 0.6 s survives, the script refuses to hand it over.

Stripping the existing take took it from 120.58 s to 104.38 s with no speech touched.

**A measurement trap worth remembering:** when boxiness was measured per 5 s window,
chunk 6 scored `1.40 · 0.05 · 1.31 · 1.28 · 1.10` and the 0.05 was read as "this
chunk got better". Silence has almost no energy at 200-500 Hz, so it scores as
excellent on a ratio metric. The dead air was in the numbers the whole time, wearing
the costume of a good result. Always check for silence before interpreting a
spectral score.

## Still open

- `Claude Code` renders as "Cloud Code" and `Grok` as "Grog" every time. Fix by
  respelling them phonetically in the script; not yet tested.
- Per-chunk spectral matching before the join, to close the remaining 0.44 spread.

## Register — non-negotiable

MYPASAKON is **ผม / เพื่อนๆ / ครับ**. Never `กู` or `มึง`; those belong to BLACK
LIQUIDITY's avatar and putting them in the CEO's cloned voice makes him swear at his
own audience. Measured in his real speech: `นะครับ` 14.9 per 1,000 characters,
`เนี่ย` 2.1, `ก็คือ` 1.5, `กู`/`มึง` exactly 0.

Written scripts in the channel's Drive folders are NOT a style guide — they run
`นะครับ` at 0.4 per 1,000. He adds the spoken texture live. Write from transcripts.
