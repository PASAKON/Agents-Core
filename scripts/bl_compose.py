#!/usr/bin/env python3
"""bl_compose.py — layers -> index.html, deterministically (task-42e3b6af).

CEO ruling 2026-09-23: no single AI writes the whole cut's HTML any more.
Different workers fill P1-P4 (.claude/skills/blackliquidity-cut/edl/SCHEMA.md);
this script is the one place that turns them into `index.html`, built on
`template/index.html`.

Only P1 renders. P2/P3/P4 are schema-validated -- unknown `type` or a
dangling `refs` id fails loudly -- but produce no HTML yet; later tasks add
one renderer per event type.

Usage:
  bl_compose.py <edl-dir> --media-root DIR --out FILE [--template FILE]

Stdlib only (see bl_edl.py's own note).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import bl_edl  # noqa: E402


VIDEO_TRACK_RE = re.compile(r"<!--\s*VIDEO TRACK.*?-->", re.DOTALL)
AUDIO_TAG_RE = re.compile(r'<audio id="va".*?</audio>', re.DOTALL)
ROOT_DURATION_RE = re.compile(
    r'(<div id="root"[^>]*?data-duration=")[^"]*(")', re.DOTALL)
BUG_DATE_RE = re.compile(r'(<div class="dt2">)[^<]*(</div>)')


def render_plate(ev: dict, offsets: dict, idx: int) -> list[str]:
    p = ev["params"]
    if p.get("role") == "bg":
        return []  # the kit's #bg is always on underneath -- nothing to place
    t0, t1 = ev["t0"], ev["t1"]
    dur = round(t1 - t0, 3)
    cls = "clip" + (" plate-darkened" if p.get("darken") else "")
    out = []

    if p["kind"] == "video":
        media_start = bl_edl.p1_media_start(ev, offsets)
        out.append(
            f'<video class="{cls}" id="v{idx}" src="{p["media"]}" muted playsinline '
            f'data-start="{t0:.2f}" data-duration="{dur:.2f}" '
            f'data-media-start="{media_start:.2f}" data-track-index="0"></video>')
    else:  # image — a still needs no ffmpeg Ken-Burns pass to be placed by P1
        out.append(
            f'<div class="{cls}" id="v{idx}" '
            f'style="background-image:url(\'{p["media"]}\');background-size:cover;'
            f'background-position:center" '
            f'data-start="{t0:.2f}" data-duration="{dur:.2f}"></div>')

    if p.get("avatar_mode") == "composite":
        av_start = bl_edl.p1_avatar_media_start(ev, offsets)
        out.append(
            f'<video class="avatar-comp" id="v{idx}a" src="{p["avatar"]["media"]}" '
            f'muted playsinline data-start="{t0:.2f}" data-duration="{dur:.2f}" '
            f'data-media-start="{av_start:.2f}" data-track-index="1"></video>')
    return out


def compose_p1(p1: dict, template_text: str) -> str:
    bl_edl.validate_p1(p1)
    offsets = p1.get("lipsync_offsets", {})
    events = sorted(p1["events"], key=lambda e: e["t0"])

    plate_lines: list[str] = []
    for idx, ev in enumerate(events, start=1):
        plate_lines.extend(render_plate(ev, offsets, idx))
    plates_html = "\n      ".join(plate_lines)

    duration = float(p1["duration"])
    audio_tag = (
        f'<audio id="va" src="{p1["audio"]["media"]}" data-start="0" '
        f'data-duration="{duration:.2f}" data-track-index="5" data-volume="1"></audio>')

    html = VIDEO_TRACK_RE.sub(plates_html, template_text, count=1)
    html = AUDIO_TAG_RE.sub(audio_tag, html, count=1)
    html = ROOT_DURATION_RE.sub(rf"\g<1>{duration:.2f}\g<2>", html, count=1)
    if p1.get("bug_date"):
        html = BUG_DATE_RE.sub(rf"\g<1>{p1['bug_date']}\g<2>", html, count=1)
    return html


def validate_p2_p4(edl_dir: Path, p1_ids: set[str]) -> None:
    registry = bl_edl.load_registry()
    known_ids = set(p1_ids)
    for layer_name, filename in (("p2", "p2_focus.json"), ("p3", "p3_text.json"), ("p4", "p4_audio.json")):
        path = edl_dir / filename
        if not path.exists():
            print(f"  {layer_name}: {filename} not present, skipped")
            continue
        doc = bl_edl.load_json(path)
        new_ids = bl_edl.validate_layer(layer_name, doc, registry, known_ids)
        print(f"  {layer_name}: {filename} OK ({len(new_ids)} events validated, renders nothing yet)")
        known_ids |= new_ids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl_dir", type=Path, help="directory holding p1_layout.json (+ optional p2/p3/p4)")
    ap.add_argument("--media-root", type=Path, required=True, help="directory 'media' paths are relative to")
    ap.add_argument("--out", type=Path, required=True, help="where to write the composed index.html")
    ap.add_argument("--template", type=Path, default=bl_edl.DEFAULT_TEMPLATE, help="template/index.html to build on")
    a = ap.parse_args(argv)

    try:
        p1 = bl_edl.load_json(a.edl_dir / "p1_layout.json")
        template_text = Path(a.template).read_text(encoding="utf-8")
        html = compose_p1(p1, template_text)
    except bl_edl.EDLError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(html, encoding="utf-8")
    p1_ids = {ev["id"] for ev in p1["events"]}
    print(f"p1: {len(p1_ids)} plates composed -> {a.out}")

    try:
        validate_p2_p4(a.edl_dir, p1_ids)
    except bl_edl.EDLError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print("(media root:", a.media_root, "-- not copied, referenced as-is; run bl_check.py p1 to gate it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
