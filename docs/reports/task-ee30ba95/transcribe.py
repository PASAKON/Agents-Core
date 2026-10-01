import json, subprocess, sys, time
import numpy as np
from faster_whisper import WhisperModel
MODEL = "/root/.cache/huggingface/hub/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f"
audio = sys.argv[1]; out = sys.argv[2]
t0 = time.time()
# PyAV 19 breaks faster-whisper 1.2.1's own decode (metadata_errors kwarg) -> decode with ffmpeg, pass the array
raw = subprocess.run(["ffmpeg","-v","error","-i",audio,"-f","s16le","-ac","1","-ar","16000","-"],capture_output=True,check=True).stdout
wav = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
m = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=2)
segs, info = m.transcribe(wav, language="th", word_timestamps=True, vad_filter=False,
                          condition_on_previous_text=False, beam_size=5)
res = {"language": info.language, "duration": info.duration, "segments": []}
for s in segs:
    res["segments"].append({"start": s.start, "end": s.end, "text": s.text,
                            "words": [{"w": w.word, "start": w.start, "end": w.end, "p": w.probability} for w in (s.words or [])]})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print("done", round(time.time() - t0, 1), "s;", len(res["segments"]), "segments")
