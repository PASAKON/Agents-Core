#!/usr/bin/env python3
"""Keep docs/previz-elements.tsv in step with the previz renders on disk.

Why this exists
---------------
Previz used to reach Higgsfield as an attached video ("@Video 1"), uploaded by
the same operator that then wrote the prompt and fired the clip. The upload is
the slow, flaky half — one clip sat 36 minutes on a stalled upload on
2026-09-04 — and it blocked generation behind it.

CEO 2026-09-04: split the roles. One operator uploads previz to Higgsfield as
VIDEO ELEMENTS and verifies them; another writes prompts and fires, referring to
the previz by @handle. The generator never touches a file input.

That only works if a handle unambiguously names one exact video. This script is
what makes that true: it hashes every render, assigns the handle, and bumps the
version whenever the bytes change, so a re-rendered previz can never be fired
against its old Element by accident.

Handle format
-------------
    project_absence_previz_<scene>_v<n>

<scene>  the scene id lowercased, with the reverse angle as its own token:
         S2N -> s2n,  S2NB -> s2n_b,  S2b -> s2b,  S2b-Split -> s2b_split
         Keeping "_b" a separate token is deliberate. Lowercasing S2B and S2b
         to the same string would collide the reverse angle of S2 with the
         phone-call scene, which are different films' worth of blocking. The
         uniqueness check below refuses to write a registry where two files
         claim one handle, so a collision fails here rather than in Higgsfield.

<n>      integer from 1, bumped on every byte change, never reused. CEO
         confirmed a video Element's file cannot be swapped in place, so a
         re-render is always a NEW Element.

Usage
-----
    python3 scripts/previz/register.py            # report drift, write nothing
    python3 scripts/previz/register.py --write    # update the registry
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PREVIZ_DIR = REPO / "docs"
REGISTRY = REPO / "docs" / "previz-elements.tsv"
PREFIX = "project_absence_previz"

FIELDS = ["handle", "scene", "angle", "file", "md5",
          "frames", "duration_s", "status", "updated"]

# S2NB / S2LB / S2OB ... are reverse angles of S2N / S2L / S2O. S10b, S2Eb,
# S12a and friends are NOT — the lowercase suffix is part of the scene id
# itself. Only an uppercase trailing B on an uppercase stem is an angle.
ANGLE_RE = re.compile(r"^(S\d+[A-Z]?)B$")


def scene_and_angle(stem: str) -> tuple[str, str]:
    """'S2NB' -> ('s2n_b', 'b');  'S2b' -> ('s2b', 'a')."""
    m = ANGLE_RE.match(stem)
    if m:
        return f"{m.group(1).lower()}_b", "b"
    return stem.lower().replace("-", "_"), "a"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path: Path) -> tuple[str, str]:
    """(frames, duration_s) via ffprobe; ('?', '?') if ffprobe is unavailable."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=nb_frames:format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=30, check=True).stdout.split()
        frames = out[0] if out else "?"
        duration = f"{float(out[1]):.1f}" if len(out) > 1 else "?"
        return frames, duration
    except Exception:
        return "?", "?"


def load() -> dict[str, dict]:
    if not REGISTRY.exists():
        return {}
    with REGISTRY.open(newline="") as fh:
        return {r["file"]: r for r in csv.DictReader(fh, delimiter="\t")}


def save(rows: list[dict]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["scene"], r["angle"])))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="update the registry; without it, only report")
    args = ap.parse_args()

    today = dt.date.today().isoformat()
    known = load()
    rows: list[dict] = []
    new, bumped, unchanged = [], [], 0

    # Case-insensitive, and not only "-Render": docs/ also holds
    # S7_previz_16x9.mp4 and S7-Blender.MP4, which a "*-Render.MP4" glob
    # silently skipped. A previz that is not in the registry is a previz an
    # operator cannot reference, so the net is cast wide and the odd extra row
    # can be marked cancelled by hand.
    candidates = sorted(
        p for p in PREVIZ_DIR.iterdir()
        if p.suffix.lower() == ".mp4" and p.is_file()
    )
    for path in candidates:
        rel = str(path.relative_to(REPO))
        # Strip ONLY the canonical "-Render" suffix. Stripping more (say
        # "-Blender" too) collapsed docs/S7-Blender.MP4 and
        # docs/S7_previz_16x9.mp4 onto one handle — caught by the uniqueness
        # check below, which is what it is for.
        stem = re.sub(r"-render$", "", path.stem, flags=re.IGNORECASE)
        scene, angle = scene_and_angle(stem)
        digest = md5(path)
        prev = known.get(rel)

        if prev is None:
            version = 1
            new.append(rel)
            status = "pending"
        elif prev["md5"] != digest:
            version = int(prev["handle"].rsplit("_v", 1)[1]) + 1
            bumped.append(f"{rel}  v{version - 1} -> v{version}")
            status = "pending"
        else:
            version = int(prev["handle"].rsplit("_v", 1)[1])
            status = prev["status"]
            unchanged += 1

        frames, duration = (probe(path) if status == "pending"
                            else (prev["frames"], prev["duration_s"]))
        rows.append({
            "handle": f"{PREFIX}_{scene}_v{version}",
            "scene": scene, "angle": angle, "file": rel, "md5": digest,
            "frames": frames, "duration_s": duration, "status": status,
            "updated": today if status == "pending" else prev["updated"],
        })

    # A handle must name exactly one video. Fail loudly rather than let two
    # scenes share one Element in Higgsfield, which would be invisible there.
    seen: dict[str, str] = {}
    clashes = []
    for r in rows:
        if r["handle"] in seen:
            clashes.append(f"{r['handle']}: {seen[r['handle']]} vs {r['file']}")
        seen[r["handle"]] = r["file"]
    if clashes:
        print("HANDLE COLLISION — refusing to write:", file=sys.stderr)
        for c in clashes:
            print("  " + c, file=sys.stderr)
        return 2

    gone = sorted(set(known) - {r["file"] for r in rows})

    print(f"{len(rows)} previz · {len(new)} new · {len(bumped)} re-rendered "
          f"· {unchanged} unchanged")
    for rel in new:
        print(f"  NEW      {rel}")
    for line in bumped:
        print(f"  BUMPED   {line}")
    for rel in gone:
        print(f"  MISSING  {rel} (row dropped)")

    pending = [r for r in rows if r["status"] == "pending"]
    if pending:
        print(f"\n{len(pending)} awaiting upload to Higgsfield:")
        for r in pending:
            print(f"  {r['handle']:<44} {r['file']}")

    if args.write:
        save(rows)
        print(f"\nwrote {REGISTRY.relative_to(REPO)}")
    else:
        print("\n(dry run — pass --write to update the registry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
