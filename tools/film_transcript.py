#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read back what a shot ACTUALLY says, and line it up against what the sheet asked for.

Built 2026-09-23 after a whole evening of wrong diagnoses. Until this existed the
only audio signal available was `silencedetect` — where the sound is, never what
it is — and every conclusion drawn from it was a guess dressed as a measurement:

  * shot 139 was reported as a probable repeat; the CEO listened and it was clean.
  * shot 122 was reported as "deliberate, good writing"; it is a character saying
    "208 งวด" then "208" inside four seconds, which is the defect he was hearing.
  * a builder change, five paid proof shots and a contradicted-by-the-community
    prompt rewrite all followed from that misreading.

faster-whisper is already installed and runs on the CPU in ~3 s per clip, so the
whole 173-shot film transcribes in about ten minutes for nothing. There was never
a reason to guess.

    python3 tools/film_transcript.py <clip-dir> [<clip-dir> ...] --out FILE.tsv
    python3 tools/film_transcript.py ~/Desktop/banchi-ALL/ACT5 --shot 122

Columns: shot, t_start, t_end, heard, scripted, match
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_sheet_data(path: Path):
    spec = importlib.util.spec_from_file_location("sheetdata_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scripted_lines() -> dict[int, list[tuple[str, str]]]:
    """{shot number: [(speaker, line), ...]} across every act that exists."""
    out: dict[int, list[tuple[str, str]]] = {}
    for act in range(1, 8):
        p = REPO / "docs" / "scripts" / f"banchi-ACT{act}.data.py"
        if not p.exists():
            continue
        for sh in load_sheet_data(p).SHOTS:
            out[sh[0]] = [(sp, line) for sp, _dir, line in sh[7]]
    return out


def thai_digits(s: str) -> str:
    """Whisper writes numbers as digits; the script spells them in Thai words.
    Normalise the obvious ones so a match is a match and not a false mismatch."""
    words = {
        "0": "ศูนย์", "1": "หนึ่ง", "2": "สอง", "3": "สาม", "4": "สี่",
        "5": "ห้า", "6": "หก", "7": "เจ็ด", "8": "แปด", "9": "เก้า",
    }
    return re.sub(r"\d", lambda m: words[m.group()], s)


def norm(s: str) -> str:
    s = thai_digits(s)
    return re.sub(r"[\s\.\,\!\?…]+", "", s)


def similarity(a: str, b: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path, help="folder(s) of shot-N.mp4")
    ap.add_argument("--out", type=Path, help="write a TSV here as well as printing")
    ap.add_argument("--shot", type=int, action="append",
                    help="only this shot number (repeatable)")
    ap.add_argument("--lang", default="th",
                    help="spoken language (default th); an English film read as th comes back as garbage")
    ap.add_argument("--model", default="small",
                    help="faster-whisper model size (default: small)")
    args = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("faster-whisper is not installed in this interpreter — "
              "pip install faster-whisper", file=sys.stderr)
        return 2

    script = scripted_lines()
    clips: list[tuple[int, Path]] = []
    for d in args.dirs:
        for f in sorted(d.glob("shot-*.mp4")):
            m = re.match(r"shot-0*(\d+)\.mp4$", f.name)
            if not m:
                continue
            n = int(m.group(1))
            if args.shot and n not in args.shot:
                continue
            clips.append((n, f))
    clips.sort()
    if not clips:
        print("no shot-N.mp4 found in those folders", file=sys.stderr)
        return 1

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    rows = []
    for n, f in clips:
        segs, _info = model.transcribe(str(f), language=args.lang, vad_filter=True)
        heard = [(s.start, s.end, s.text.strip()) for s in segs]
        want = script.get(n, [])
        for i, (t0, t1, text) in enumerate(heard):
            line = want[i][1] if i < len(want) else ""
            who = want[i][0] if i < len(want) else ""
            sim = similarity(text, line) if line else 0.0
            rows.append((n, round(t0, 2), round(t1, 2), text, who, line, round(sim, 2)))
        # a scripted line with nothing heard for it is its own finding
        for i in range(len(heard), len(want)):
            rows.append((n, "", "", "(ไม่ได้ยิน)", want[i][0], want[i][1], 0.0))
        extra = len(heard) - len(want)
        flag = ""
        if extra > 0:
            flag = f"  ⚠️ ได้ยิน {len(heard)} ช่วง บทมี {len(want)} บรรทัด"
        elif extra < 0:
            flag = f"  ⚠️ ขาด {-extra} บรรทัด"
        print(f"ฉาก {n:>3}: {len(heard)} ช่วง / บท {len(want)} บรรทัด{flag}")
        for t0, t1, text in heard:
            print(f"        {t0:6.2f}–{t1:6.2f}  «{text}»")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("shot\tt_start\tt_end\theard\tspeaker\tscripted\tmatch\n")
            for r in rows:
                fh.write("\t".join(str(x) for x in r) + "\n")
        print(f"\nเขียน {args.out} ({len(rows)} แถว)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
