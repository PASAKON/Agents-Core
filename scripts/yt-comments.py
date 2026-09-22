#!/usr/bin/env python3
"""List YouTube comments on a channel that the channel has not replied to yet.

Headless (yt-dlp, no API key, no browser). Usage:
    python3 scripts/yt-comments.py                      # @ILAGStudio, unanswered only
    python3 scripts/yt-comments.py --all                # include answered ones
    python3 scripts/yt-comments.py --json out.json      # machine-readable
"""
import argparse, datetime, json, subprocess, sys, tempfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("channel", nargs="?", default="https://www.youtube.com/@ILAGStudio/videos")
ap.add_argument("--all", action="store_true")
ap.add_argument("--json")
a = ap.parse_args()

ids = subprocess.run(["yt-dlp", "--flat-playlist", "--no-warnings", "--print", "%(id)s", a.channel],
                     capture_output=True, text=True, timeout=180).stdout.split()
if not ids:
    sys.exit("no videos listed - the probe failed, this is NOT 'no comments'")

out = []
with tempfile.TemporaryDirectory() as tmp:
    for vid in ids:
        subprocess.run(["yt-dlp", "--skip-download", "--write-comments", "--no-warnings", "-q",
                        "--extractor-args", "youtube:comment_sort=new;max_comments=all,all,all,all",
                        "-o", f"{tmp}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, timeout=600)
        f = Path(tmp, f"{vid}.info.json")
        if not f.exists():
            print(f"!! {vid}: comments not fetched", file=sys.stderr)
            continue
        d = json.loads(f.read_text())
        cs = d.get("comments") or []
        reps = [c for c in cs if c.get("parent") != "root"]
        answered = {c["parent"] for c in reps if c.get("author_is_uploader")}
        for c in cs:
            if c.get("author_is_uploader"):
                continue
            done = c["id"] in answered or (c.get("parent") != "root" and any(
                r.get("author_is_uploader") and (r.get("timestamp") or 0) > (c.get("timestamp") or 0)
                for r in reps if r["parent"] == c["parent"]))
            if done and not a.all:
                continue
            out.append({"video": d.get("title"), "video_id": vid, "comment_id": c["id"],
                        "parent": c.get("parent"), "author": c.get("author"),
                        "likes": c.get("like_count", 0), "answered": done,
                        "date": datetime.datetime.fromtimestamp(c.get("timestamp") or 0).strftime("%Y-%m-%d"),
                        "text": c.get("text") or ""})

if a.json:
    Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1))
for i, c in enumerate(out, 1):
    tag = "reply" if c["parent"] != "root" else "top"
    print(f"{i:>3}. [{c['date']}] {c['video'][:24]} · {tag} · {c['author']} ♥{c['likes']}"
          f"{' ✅' if c['answered'] else ''}\n     " + c["text"].replace("\n", " / "))
print(f"\n{len(out)} comment(s) across {len(ids)} video(s)")
