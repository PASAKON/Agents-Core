"""Short-movie clip QC: the zero-image stage and the contact sheets of CMO_Gate_Champa_Seedance2.0_ShortMovieQC.

  shortmovie_qc.py stage1 --clips DIR --jobs a.json [b.json ...] --out stage1.tsv [--glob 'lb-*.mp4']
  shortmovie_qc.py sheets --clips DIR --cuts list.txt --prefix lb- --out DIR

stage1, per clip: duration, audio present + mean level, caption-band pixel score (burned_text_scan.band_scores) and a
read-back of every quoted line in the clip's prompt (faster-whisper small, language chosen per line, VAD on), scored
0-1 by best-window similarity. A clip whose prompt quotes no line is transcribed in auto mode, so unexpected speech
shows up in the `heard` column. Whisper writes "Thanks for watching!" over music: re-read such a clip with VAD off
before calling it speech (THE LAST BELL C10/D03 2026-10-04 were bell and thunder hits, heard as "BOOM!").

sheets: 3 frames per take inside the used cut (0.5 s, cut/2, cut-0.5 s), 8 takes per image, label at the left.
`--cuts` lines read `<shot> <cut seconds> [path]`. Every <prefix><shot>*.mp4 is a take: the bare name is labelled t1,
any suffix is shown as written (-hd, -rs1). Jobs files are JSON lists of {"id", "prompt", ...}; id = clip file stem.
"""
import argparse, difflib, json, re, subprocess, sys
from pathlib import Path

QUOTE = re.compile(r'["“]([^"”]{2,})["”]')
THAI = re.compile(r"[฀-๿]")


def norm(s):
    return re.sub(r"[^฀-๿a-z0-9]", "", s.lower())


def best_window(line, heard):
    ln, hn, best = norm(line), norm(heard), 0.0
    for i in range(0, max(1, len(hn) - len(ln) + 1), 2):
        best = max(best, difflib.SequenceMatcher(None, ln, hn[i:i + len(ln)]).ratio())
    return round(best, 2)


def stage1(a):
    import numpy as np
    sys.path.insert(0, str(Path(__file__).parent))
    from burned_text_scan import band_scores, GATE
    from faster_whisper import WhisperModel
    prompts = {j["id"]: j["prompt"] for f in a.jobs for j in json.load(open(f))}
    model = WhisperModel("small", device="cpu", compute_type="int8")
    rows = []
    for clip in sorted(Path(a.clips).glob(a.glob)):
        cid = clip.stem
        p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json",
                                       str(clip)], capture_output=True, text=True).stdout)
        dur = float(p["format"]["duration"]); has_a = any(s["codec_type"] == "audio" for s in p.get("streams", []))
        vol = subprocess.run(["ffmpeg", "-nostdin", "-i", str(clip), "-vn", "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        mv = (re.findall(r"mean_volume: (-?[\d.]+)", vol) or ["nan"])[0]
        sc = band_scores(clip, 2.0); top = max(sc, key=lambda x: x[1]) if sc else (0, 0)
        pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True).stdout
        want = QUOTE.findall(prompts.get(cid, "").split("CRITICAL NEGATIVES")[0])
        lang = ("th" if any(THAI.search(x) for x in want) else "en") if want else None
        segs, info = model.transcribe(np.frombuffer(pcm, dtype=np.float32), language=lang, vad_filter=True)
        heard = " | ".join(f"{s.start:.1f}-{s.end:.1f} {s.text.strip()}" for s in segs)
        scores = [best_window(x, heard) for x in want]
        rows.append([cid, f"{dur:.1f}", "audio" if has_a else "SILENT", mv, f"{top[1]}@{top[0]}", "CAPTION?" if top[1] >= GATE else "",
                     str(len(want)), ",".join(map(str, scores)), lang or "auto:" + str(info.language), heard[:400]])
        print("\t".join(rows[-1][:9]) + "\t" + rows[-1][9][:120], flush=True)
    Path(a.out).write_text("clip\tdur\taudio\tmean_db\tband_max\tflag\tlines\tline_match\tlang\theard\n"
                           + "\n".join("\t".join(r) for r in rows) + "\n")
    print("wrote", a.out)


def sheets(a):
    from PIL import Image, ImageDraw, ImageFont
    clips, out = Path(a.clips), Path(a.out); (out / "fr").mkdir(parents=True, exist_ok=True)
    cuts = {l.split()[0]: float(l.split()[1]) for l in open(a.cuts) if l.strip()}
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except OSError:
        font = ImageFont.load_default()
    rows = []
    for sid in sorted(cuts):
        for clip in sorted(clips.glob(f"{a.prefix}{sid}*.mp4"), key=lambda p: (p.stem != f"{a.prefix}{sid}", p.stem)):  # t1 first
            tag = clip.stem[len(a.prefix) + len(sid):]
            if tag and not tag.startswith("-"): continue  # lb-A1 must not pick up lb-A10
            c, frames = cuts[sid], []
            for k, t in enumerate((0.5, c / 2, c - 0.5)):
                png = out / "fr" / f"{sid}{tag}_{k}.png"
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(clip), "-frames:v", "1",
                                "-vf", "scale=400:-2", str(png)])
                frames.append(Image.open(png))
            rows.append((f"{sid} {tag.lstrip('-') or 't1'}", frames))
    acts = {}
    for lab, fr in rows: acts.setdefault(lab[0], []).append((lab, fr))
    for act, rs in acts.items():
        for n in range(0, len(rs), 8):
            chunk = rs[n:n + 8]; h = chunk[0][1][0].height
            sheet = Image.new("RGB", (130 + 3 * 404, len(chunk) * (h + 4)), "black"); d = ImageDraw.Draw(sheet)
            for r, (lab, fr) in enumerate(chunk):
                y = r * (h + 4); d.text((6, y + h // 2 - 12), lab, font=font, fill="white")
                for k, im in enumerate(fr): sheet.paste(im, (130 + k * 404, y))
            dest = out / f"act{act}-{n // 8 + 1}.jpg"; sheet.save(dest, quality=85); print(dest.name, sheet.size, [l for l, _ in chunk])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s1 = sp.add_parser("stage1"); s1.add_argument("--clips", required=True); s1.add_argument("--jobs", nargs="+", required=True)
    s1.add_argument("--out", required=True); s1.add_argument("--glob", default="*.mp4")
    sh = sp.add_parser("sheets"); sh.add_argument("--clips", required=True); sh.add_argument("--cuts", required=True)
    sh.add_argument("--prefix", default=""); sh.add_argument("--out", required=True)
    a = ap.parse_args()
    stage1(a) if a.cmd == "stage1" else sheets(a)
