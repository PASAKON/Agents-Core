#!/usr/bin/env python3
"""cookierun_teacher_collect.py -- winbox side of the daily teacher loop.

Picks the navigator's saved unknown frames since an epoch, keeps only the ones
that were a real problem, and packs them (downscaled) with what the bot thought
of each, for tools/cookierun_teachers.py `daily` on Contabo to label.

"A real problem" is measured from the trace, not guessed: a frame is dropped
when the navigator named a screen within SETTLED_S of it and no restart
followed -- that frame was an animation caught mid-way, and the 8 s settle rule
already handled it. 2026-09-23 22:12: the one unknown frame of a 90-minute run
was the congrats panel at ~45% of its scale-in; 2 s later it matched 0.993.
Spending a teacher on such a frame buys nothing.

    python cookierun_teacher_collect.py <since_epoch> <out_dir> [settled_s]
"""
import json
import sys
import zipfile
from pathlib import Path

import cv2

DATA = Path.home() / "Documents" / "CookieRunScript"
SETTLED_S = 12.0      # the navigator's settle window is 8 s; allow one more pass
RESTART_S = 90.0


def trace_events(since: float) -> list[dict]:
    out = []
    for tf in ("trace.jsonl.1", "trace.jsonl"):
        p = DATA / tf
        if not p.exists():
            continue
        for line in p.open(encoding="utf-8", errors="replace"):
            if '"see.screen"' not in line and '"restart.begin"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("t", 0) >= since:
                out.append(r)
    return sorted(out, key=lambda r: r["t"])


def main() -> int:
    since, out = float(sys.argv[1]), Path(sys.argv[2])
    settled = float(sys.argv[3]) if len(sys.argv) > 3 else SETTLED_S
    out.mkdir(parents=True, exist_ok=True)
    evs = trace_events(since - 5)
    kept, dropped = [], 0
    for f in sorted((DATA / "unknown").glob("*.jpg"), key=lambda p: p.stat().st_mtime):
        if f.stat().st_mtime < since:
            continue
        side = f.with_suffix(".json")
        meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
        t = float(meta.get("t") or f.stat().st_mtime)
        nxt = next((e for e in evs if e["t"] > t and e.get("ev") == "see.screen" and e.get("ok")), None)
        resolved_s = None if nxt is None else round(nxt["t"] - t, 1)
        restart = any(e.get("ev") == "restart.begin" and t < e["t"] <= t + RESTART_S for e in evs)
        if resolved_s is not None and resolved_s <= settled and not restart:
            dropped += 1
            continue
        im = cv2.imread(str(f))
        if im is None:
            continue
        h, w = im.shape[:2]
        cv2.imwrite(str(out / f.name), cv2.resize(im, (800, int(h * 800 / w)), interpolation=cv2.INTER_AREA),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        kept.append({"frame": f.name, "t": t, "top": meta.get("top") or [], "where": meta.get("where"),
                     "resolved_s": resolved_s,
                     "resolved_as": None if nxt is None else (nxt.get("d") or {}).get("name"),
                     "restart_followed": restart})
    (out / "manifest.json").write_text(json.dumps(kept, indent=1), encoding="utf-8")
    with zipfile.ZipFile(str(out) + ".zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, p.name)
    print(json.dumps({"kept": len(kept), "dropped_as_settled": dropped, "zip": str(out) + ".zip"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
