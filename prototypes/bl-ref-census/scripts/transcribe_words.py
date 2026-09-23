"""Word-level Thai transcription with faster-whisper `small`, word_timestamps=True.
Thai words come back character-split (a known faster-whisper Thai quirk) — this
just dumps raw words; joining into real words happens downstream when matching
against visual events, per seed/README.md's note.

Usage: python transcribe_words.py ref_16k_mono.wav > measurements/words_raw.tsv
Output columns: seg_id, word_idx, t0, t1, prob, word
"""
import sys
from faster_whisper import WhisperModel

WAV = sys.argv[1]
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(WAV, language="th", word_timestamps=True, vad_filter=False)

print("seg_id\tword_idx\tt0\tt1\tprob\tword")
for si, seg in enumerate(segments):
    print(f"#SEG\t{si}\t{seg.start:.3f}\t{seg.end:.3f}\t\t{seg.text.strip()}", file=sys.stderr)
    if seg.words:
        for wi, w in enumerate(seg.words):
            print(f"{si}\t{wi}\t{w.start:.3f}\t{w.end:.3f}\t{w.probability:.3f}\t{w.word}")
