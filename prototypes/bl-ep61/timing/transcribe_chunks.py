"""Re-transcribe chosen [t0,t1] stretches of the voice that transcribe.py dropped (EP61: 21.4-50.9 s, the arithmetic).
Greedy decode, 4 threads, a short Thai prompt of the script's own vocabulary (alignment only; captions come from SCRIPT.tsv).
    transcribe_chunks.py audio.wav out.json t0:t1 [t0:t1 ...]"""
import json, subprocess, sys, time
import numpy as np
from faster_whisper import WhisperModel
MODEL = "/root/.cache/huggingface/hub/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f"
audio, out = sys.argv[1], sys.argv[2]
chunks = [tuple(float(x) for x in a.split(":")) for a in sys.argv[3:]]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
wav = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
m = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=4)
PROMPT = "คอมมิชชัน สเปรด ล็อต พิป ดอลลาร์ สว็อป ติ๊กมิลล์ บัญชี คูณ รวม"
res = {"segments": []}
t00 = time.time()
for a, b in chunks:
    seg = wav[int(a * 16000): int(b * 16000)]
    segs, _ = m.transcribe(seg, language="th", word_timestamps=True, vad_filter=False, condition_on_previous_text=False,
                           beam_size=1, temperature=0.0, initial_prompt=PROMPT, no_speech_threshold=0.9, compression_ratio_threshold=3.0,
                           repetition_penalty=1.3, no_repeat_ngram_size=3)
    for s in segs:
        res["segments"].append({"start": s.start + a, "end": s.end + a, "text": s.text,
                                "words": [{"w": w.word, "start": w.start + a, "end": w.end + a, "p": w.probability} for w in (s.words or [])]})
    print(f"chunk {a}-{b} done at {time.time()-t00:.0f}s", flush=True)
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print("done", round(time.time() - t00, 1), "s;", len(res["segments"]), "segments")
