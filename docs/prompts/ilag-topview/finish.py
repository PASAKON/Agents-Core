"""Finish THE SHADOW BELOW from the CEO's CapCut export (CEO 2026-09-27: "ทำสี -> ใส่ Sub title ให้ตรงกับปากตัวละคร ->
ติดลายน้ำของ TopView"), in this order, in one encode per deliverable:

    python3 finish.py CUT.mp4 [--look Glow] [--credits ILAG-Credits-4K.mp4] [--out DIR] [--subs-only]

  1. subtitles: faster-whisper (word timestamps) on the cut's own audio, so each line sits on the lips; every heard
     line is matched against the script's lines (LINES) and the script's wording is used when it matches, the heard
     wording otherwise (listed as UNMATCHED for a look). Writes <out>/THE-SHADOW-BELOW.en.srt (also for YouTube).
  2. grade: the chosen custom 3D LUT (looks.py, CEO picked Glow), lut3d trilinear, applied first so the subtitles, the
     watermark and the credits are not tinted.
  3. subtitles burned in, white with a black outline, bottom centre.
  4. the official TopView watermark top-right over the whole video, credits included (Terms §3: every entry "must
     include the official challenge watermark"; its example puts it top-right at about 17% of the width).
  5. the end-credits roll appended (credits.py).
Two files: a YouTube master (CRF 16) and a TopView upload under the form's 500 MB limit (capped bitrate if needed).
--subs-only stops after step 1, so the SRT can be checked before the long encode.
"""
import argparse, difflib, importlib.util, json, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATERMARK = HERE.parents[1] / "promo" / "topview-trailer" / "cover" / "TopView-Watermark.png"
# Every scripted line (build.py beats + the Wan3 retakes), for matching what whisper hears.
LINES = [
    "Chief! There are no fish. None left.", "We're starving. Please, do something.",
    "He's right. Not one fish, all week.", "So... the day has come.", "We need the child with the gift.",
    "It's time.", "You are the chosen one.", "You two will go with the child.",
    "The fish went past the line.", "Only a child's eyes can still find them.",
    "No one has crossed it in a hundred years.", "Something sleeps out there.",
    "So this is it. The line of death.", "There's nothing here... not one.", "We need your light now.",
    "Hold on!", "Sorry!", "I can see them... inside it.", "Wake up... look!", "Wowww.",
]
TOPVIEW_LIMIT_MB = 480  # the form takes 500 MB; keep a margin


def norm(s):
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def transcribe(cut, model="small.en"):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(cut), language="en", word_timestamps=True, vad_filter=True, beam_size=5)
    # Whisper groups several lines into one segment (the assembly test gave one segment from 40 s to 138 s holding
    # three lines), so the unit here is the sentence, cut at the words' own end punctuation, timed by its words.
    sentences, cur = [], []
    for seg in segs:
        for w in seg.words or []:
            if not w.word.strip():
                continue
            cur.append(w)
            if re.search(r"[.!?]$", w.word.strip()):
                sentences.append(cur); cur = []
        if cur:
            sentences.append(cur); cur = []
    # A first word can carry a start stuck far back (assembly test: "So" of "So this is it..." at 40.6 s, the line at
    # ~113 s); start no earlier than 0.6 s before the second word.
    return [(ws[0].start if len(ws) < 2 else max(ws[0].start, ws[1].start - 0.6), ws[-1].end,
             "".join(w.word for w in ws).strip()) for ws in sentences]


def group(sentences):
    """Join consecutive sentences that together are one scripted line ("Chief! There are no fish. None left.")."""
    out, i = [], 0
    while i < len(sentences):
        best = (1, *match(sentences[i][2]))
        for k in (2, 3):
            if i + k <= len(sentences) and sentences[i + k - 1][0] - sentences[i][1] < 4.0:
                text = " ".join(x[2] for x in sentences[i:i + k])
                t, sc = match(text)
                if sc >= 0.6 and sc > best[2] + 0.05:
                    best = (k, t, sc)
        k = best[0]
        out.append((sentences[i][0], sentences[i + k - 1][1], " ".join(x[2] for x in sentences[i:i + k])))
        i += k
    return out


def match(heard):
    best, score = None, 0.0
    for line in LINES:
        r = difflib.SequenceMatcher(None, norm(heard), norm(line)).ratio()
        if r > score:
            best, score = line, r
    return (best, score) if score >= 0.6 else (heard, score)


def write_srt(segments, path):
    cues, report = [], []
    for start, end, heard in segments:
        text, score = match(heard)
        report.append({"start": round(start, 2), "end": round(end, 2), "heard": heard, "text": text,
                       "score": round(score, 2), "matched": score >= 0.6})
        end = max(end + 0.25, start + 1.0)  # readable: at least 1 s, and a beat after the last word
        if cues and start < cues[-1][1]:
            cues[-1] = (cues[-1][0], start - 0.04, cues[-1][2])
        cues.append((start, end, text))
    with open(path, "w", encoding="utf-8") as f:
        for i, (s, e, t) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n\n")
    return report


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    j = json.loads(out.stdout)
    st = j["streams"][0]
    num, den = (int(x) for x in st["r_frame_rate"].split("/"))
    return st["width"], st["height"], num / den, float(j["format"]["duration"])


def render(cut, lut, srt, credits, out_path, video_args):
    w, h, fps, _ = probe(cut)
    ww = round(0.17 * w)
    margin = round(0.025 * w)
    font_px = round(0.045 * h)
    style = (f"FontName=DejaVu Sans,Bold=1,FontSize={font_px},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             f"BorderStyle=1,Outline={max(2, round(font_px / 12))},Shadow=0,Alignment=2,MarginV={round(0.06 * h)}")
    srt_esc = str(srt).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    graph = (f"[0:v]lut3d=file='{lut}':interp=trilinear,"
             f"subtitles=filename='{srt_esc}':original_size={w}x{h}:force_style='{style}',format=yuv420p[g];"
             f"[2:v]scale={ww}:-1[wm];[wm]split[wm1][wm2];"
             f"[1:v]scale={w}:{h},fps={fps},format=yuv420p[c];"
             f"[g][wm1]overlay=W-w-{margin}:{margin}[gw];[c][wm2]overlay=W-w-{margin}:{margin}[cw];"
             f"[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
             f"[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
             f"[gw][a0][cw][a1]concat=n=2:v=1:a=1[v][a]")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(cut), "-i", str(credits), "-loop", "1", "-i", str(WATERMARK),
           "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
           *video_args, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest"]
    subprocess.run(cmd + [str(out_path)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cut", type=Path)
    ap.add_argument("--look", default="Glow")
    ap.add_argument("--credits", type=Path, default=Path("/tmp/ilag-credits/ILAG-Credits-4K.mp4"))
    ap.add_argument("--out", type=Path, default=Path("/tmp/ilag-final"))
    ap.add_argument("--subs-only", action="store_true")
    ap.add_argument("--srt", type=Path, help="use this (checked, maybe hand-fixed) SRT instead of transcribing")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    srt = a.out / "THE-SHADOW-BELOW.en.srt"
    if a.srt:
        srt = a.srt
    else:
        report = write_srt(group(transcribe(a.cut)), srt)
        (a.out / "subs-report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
        for r in report:
            print(f"{r['start']:7.2f}-{r['end']:7.2f} {'OK ' if r['matched'] else 'UNMATCHED'} {r['score']:.2f} "
                  f"heard={r['heard']!r} -> {r['text']!r}")
    if a.subs_only:
        return
    spec = importlib.util.spec_from_file_location("looks", HERE / "looks.py")
    looks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(looks)
    lut = a.out / f"TSB_{a.look}.cube"  # a pure function of looks.py, rebuilt every run so it cannot drift
    looks.cube(a.look, lut, 33)
    master = a.out / "THE-SHADOW-BELOW-4K-master.mp4"
    render(a.cut, lut, srt, a.credits, master, ["-crf", "16"])
    dur = probe(master)[3]
    kbps = int(TOPVIEW_LIMIT_MB * 8 * 1024 / dur - 192)
    tv = a.out / "THE-SHADOW-BELOW-4K-topview.mp4"
    if master.stat().st_size / 1e6 <= TOPVIEW_LIMIT_MB:
        tv.write_bytes(master.read_bytes())  # the master already fits the form
    else:
        render(a.cut, lut, srt, a.credits, tv, ["-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.3)}k",
                                                 "-bufsize", f"{kbps * 2}k"])
    for p in (master, tv):
        print(p, f"{p.stat().st_size / 1e6:.0f} MB", f"{probe(p)[3]:.1f} s")


if __name__ == "__main__":
    main()
