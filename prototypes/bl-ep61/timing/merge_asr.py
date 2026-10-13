"""EP61: stitch the ASR passes into one asr-merged.json for align_timings.py.
transcribe.py (whole voice) dropped 21.4-52.0 s; transcribe_chunks.py re-did that stretch (asr-mid.json; its 29.6-38.7 chunk looped,
so asr-mid2.json redid 29.1-38.8 with a repetition guard); asr-gap.json (offset 20.9 s) supplies the word at 50.9 s.
Each window takes the words whose start falls inside it, so no word is counted twice."""
import json, sys
W = "/opt/MoonieXHQ/Work/bl-ep61/timing/"
def words(path, off=0.0):
    d = json.load(open(W + path))
    return [dict(w, start=w["start"] + off, end=w["end"] + off) for s in d["segments"] for w in s["words"]]
plan = [("asr.json", 0.0, 0.0, 21.2), ("asr-mid.json", 0.0, 21.2, 29.1), ("asr-mid2.json", 0.0, 29.1, 38.7),
        ("asr-mid.json", 0.0, 38.7, 50.9), ("asr-gap.json", 20.9, 50.9, 52.0), ("asr.json", 0.0, 52.0, 999)]
segs = []
for path, off, lo, hi in plan:
    ws = [w for w in words(path, off) if lo <= w["start"] < hi]
    if ws:
        segs.append({"start": ws[0]["start"], "end": ws[-1]["end"], "text": "".join(w["w"] for w in ws), "words": ws})
json.dump({"language": "th", "segments": segs}, open(W + "asr-merged.json", "w"), ensure_ascii=False, indent=1)
for s in segs: print(f"{s['start']:6.2f}-{s['end']:6.2f} {s['text'][:70]}")
