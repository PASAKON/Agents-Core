#!/usr/bin/env python3
"""BLACK LIQUIDITY Compose -- beats.json -> rendered final.mp4 (task-aae4f843).

Adapter between a beats.json ({tag,t0,t1,mode,extra} objects, the Scripter's
and any Editor's shared output shape) and the human cut's own generator
(prototypes/bl57-cut/build_cut.py + assemble.py, on branch
origin/agent/video_editor-task-501f1d89). That branch's `BEATS` is a
hardcoded, whole-episode Python literal with a flat top-level emission loop
-- not a function -- so it cannot be driven by different data without
editing it, and this task's rule is: never edit build_cut.py/assemble.py.

So this tool:
  1. Pulls ONLY the pure geometry/lookup functions out of build_cut.py
     (img_placement, box_to_canvas, pick_lip, lip_offset, pct, esc) plus a
     few constants (CANVAS_W/H, LIP_DUR, PLATE_TRACK, AVATAR_TRACK), by
     parsing its AST and exec'ing exactly those top-level nodes verbatim.
     build_cut.py's own hardcoded BEATS/CHECK_ITEMS, its sys.argv-driven
     WINDOW_START/END, its emission loop and its hardcoded output path
     never execute -- the file itself is read-only and untouched.
  2. Re-drives the SAME per-mode emission shape (FF/COMP/EVID/KIN) from the
     caller's own beats instead of the hardcoded episode. This part cannot
     be literally imported -- build_cut.py's loop isn't factored as a
     callable -- so it mirrors that loop body beat for beat using the
     functions imported in step 1; the geometry math itself has exactly one
     source (build_cut.py), never duplicated by hand here.
  3. Writes the same cut_pieces.json shape build_cut.py writes, and calls
     assemble.py (UNMODIFIED, as a subprocess, the same way
     render_windows.sh does) to splice it into a copy of the clean
     template.
  4. Renders with `npx hyperframes@0.8.40 render`, then muxes the real
     narration audio on top with ffmpeg (-c:v copy).

--generator-dir must hold: build_cut.py, assemble.py, index.html (the CLEAN
template -- e.g. .claude/skills/blackliquidity-cut/template/index.html, NOT
a branch copy that has already been spliced), hyperframes.json,
package.json, assets/, and media/ (the stills/avatar clips the beats'
`extra.img` / mode reference, flat under media/ exactly as build_cut.py's
f'media/{img}' expects).

Usage:
    python3 tools/bl_compose.py \\
        --beats beats.json --generator-dir <dir> --t-max 30.78 \\
        --audio audio-hq.mp3 --out-dir <workdir> --out final.mp4
    # --no-render stops after writing the composed index.html (tests/dry-run)
"""
from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CANVAS_W, CANVAS_H = 1080, 1920

# Exactly the names this tool borrows from build_cut.py -- nothing else in
# that file ever runs.
_ALLOWED_FUNCS = {"lip_offset", "pick_lip", "img_placement", "box_to_canvas", "pct", "esc"}
_ALLOWED_CONSTS = {"CANVAS_W", "CANVAS_H", "LIP_DUR", "PLATE_TRACK", "AVATAR_TRACK"}


class ComposeError(RuntimeError):
    pass


def load_generator_functions(generator_dir: Path) -> dict[str, Any]:
    """AST-selective exec of build_cut.py: only the pure helper functions and
    constants named above run. The file's own hardcoded BEATS/CHECK_ITEMS,
    its sys.argv-driven WINDOW_START/END, its emission loop and its
    hardcoded output path never execute -- build_cut.py is parsed, its
    matching top-level statements are exec'd byte-for-byte (never rewritten),
    and everything else in it is simply never selected."""
    src_path = generator_dir / "build_cut.py"
    if not src_path.is_file():
        raise ComposeError(f"generator-dir missing build_cut.py: {src_path}")
    tree = ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))
    keep: list[ast.stmt] = []
    found_funcs: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _ALLOWED_FUNCS:
            keep.append(node)
            found_funcs.add(node.name)
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & _ALLOWED_CONSTS:
                keep.append(node)
    missing = _ALLOWED_FUNCS - found_funcs
    if missing:
        raise ComposeError(f"build_cut.py is missing expected function(s): {sorted(missing)}")
    module = ast.Module(body=keep, type_ignores=[])
    ns: dict[str, Any] = {}
    exec(compile(module, str(src_path), "exec"), ns)  # noqa: S102 -- selected, trusted source
    return ns


def compute_ext_end(beats: list[dict], t_max: float) -> dict[str, float]:
    """Hold-until-next: a beat's effective end is the NEXT beat's start (or
    t_max for the last one), same rule build_cut.py itself uses so a plate
    never goes empty during a TTS pause between two lines."""
    markers = sorted(((b["t0"], b["tag"]) for b in beats), key=lambda m: m[0])
    ext_end: dict[str, float] = {}
    for i, (_t0, tag) in enumerate(markers):
        nxt = markers[i + 1][0] if i + 1 < len(markers) else t_max
        ext_end[tag] = nxt
    return ext_end


def emit_pieces(beats: list[dict], t_max: float, funcs: dict[str, Any]) -> dict:
    """Beats -> the same cut_pieces.json shape build_cut.py writes (plates,
    script_lines, check_call, check_override_js, caps_js, total_dur).

    Mirrors build_cut.py's per-mode emission (lines ~175-264 on the branch)
    beat for beat, always as a single WINDOW_START=0..t_max window (this
    experiment never needs the branch's multi-window split-render). CHECK
    mode (the SUMMARY-4/5/6 checklist card) is out of scope -- every arm
    here cuts only 0-30.78s, well before that block starts at t=129.4s --
    so a CHECK-mode beat is a hard error rather than a silent no-op.
    """
    img_placement = funcs["img_placement"]
    box_to_canvas = funcs["box_to_canvas"]
    pick_lip = funcs["pick_lip"]
    lip_offset = funcs["lip_offset"]
    esc = funcs["esc"]
    LIP_DUR = funcs["LIP_DUR"]
    PLATE_TRACK = funcs.get("PLATE_TRACK", 0)
    AVATAR_TRACK = funcs.get("AVATAR_TRACK", 1)

    ext_end = compute_ext_end(beats, t_max)
    plates: list[str] = []
    script_lines: list[str] = []
    caps_js: list[str] = []

    for b in sorted(beats, key=lambda b: b["t0"]):
        tag, abs_t0, mode = b["tag"], b["t0"], b["mode"]
        ex = b.get("extra") or {}
        if abs_t0 < -0.001 or abs_t0 >= t_max - 0.001:
            continue
        t0 = round(abs_t0, 3)
        t1 = round(min(ext_end[tag], t_max), 3)
        dur = round(t1 - t0, 3)
        safe_id = tag.lower().replace("-", "")

        if mode == "FF":
            lipname = pick_lip(abs_t0)
            media_start = round(abs_t0 - lip_offset(lipname), 3)
            clip_dur = min(dur, round(LIP_DUR[lipname] - media_start, 3))
            plates.append(
                f'<video class="clip" id="v_{safe_id}" src="media/{lipname}.mp4" muted playsinline '
                f'data-start="{t0}" data-duration="{clip_dur}" data-media-start="{media_start}" '
                f'data-track-index="{PLATE_TRACK}"></video>')
            caps_js.append(
                f'addCap({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)}, "chip-ff", null);')

        elif mode == "COMP":
            place = img_placement(ex)
            dw, dh, top, left, scale = place
            img = ex["img"]
            shift = ex.get("shift", 0)
            plate_dur = dur
            avatar_dur = dur
            if "avatar_until" in ex:
                avatar_dur = round(ex["avatar_until"] - abs_t0, 3)
            lipname = pick_lip(abs_t0)
            media_start0 = round(abs_t0 - lip_offset(lipname), 3)
            avatar_dur = min(avatar_dur, round(LIP_DUR[lipname] - media_start0, 3))
            style = (f'top:{top - shift}px;left:{left}px;right:auto;bottom:auto;'
                     f'width:{dw}px;height:{dh}px;transform:none')
            plates.append(
                f'<img class="clip" id="v_{safe_id}" src="media/{img}" '
                f'style="{style}" data-start="{t0}" data-duration="{plate_dur}" '
                f'data-track-index="{PLATE_TRACK}">')
            media_start = round(abs_t0 - lip_offset(lipname), 3)
            plates.append(
                f'<video class="avatar-comp" id="av_{safe_id}" src="media/matte/{lipname}-matte.webm" '
                f'muted playsinline data-start="{t0}" data-duration="{avatar_dur}" '
                f'data-media-start="{media_start}" data-track-index="{AVATAR_TRACK}"></video>')
            box_c = box_to_canvas(ex.get("box"), place)
            if box_c:
                bx, by, bw, bh = box_c
                by -= shift
                box_bottom = by + bh
                cap_y = None
                if by - 150 >= 150:
                    cap_y = round(by - 150)
                elif 845 - (box_bottom + 15) >= 100:
                    cap_y = round(box_bottom + 15)
                if cap_y is not None:
                    caps_js.append(
                        f'addCap({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)}, "chip-comp", {cap_y});')
                script_lines.append(
                    f'spotlight("sp_{safe_id}", {t0 + 0.15}, {t1}, '
                    f'{round(bx)}, {round(by)}, {round(bw)}, {round(bh)});')
            else:
                caps_js.append(
                    f'addCap({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)}, "chip-comp", 700);')
            if ex.get("credit"):
                script_lines.append(f'credit("cr_{safe_id}", {t0 + 0.1}, {t1}, "{esc(ex["credit"])}");')

        elif mode == "EVID":
            place = img_placement(ex)
            dw, dh, top, left, scale = place
            img = ex["img"]
            style = f'top:{top}px;left:{left}px;right:auto;bottom:auto;width:{dw}px;height:{dh}px'
            plates.append(
                f'<img class="clip" id="v_{safe_id}" src="media/{img}" '
                f'style="{style}" data-start="{t0}" data-duration="{dur}" '
                f'data-track-index="{PLATE_TRACK}">')
            box_c = box_to_canvas(ex.get("box"), place)
            if box_c:
                bx, by, bw, bh = box_c
                script_lines.append(
                    f'spotlight("sp_{safe_id}", {t0 + 0.25}, {t1}, '
                    f'{round(bx)}, {round(by)}, {round(bw)}, {round(bh)});')
            if ex.get("credit"):
                script_lines.append(f'credit("cr_{safe_id}", {t0 + 0.1}, {t1}, "{esc(ex["credit"])}");')
            caps_js.append(f'addCap({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)}, "rail", null);')

        elif mode == "KIN":
            if ex.get("broll"):
                plates.append(
                    f'<video class="clip plate-darkened" id="v_{safe_id}" src="media/{ex["broll"]}" '
                    f'muted playsinline data-start="{t0}" data-duration="{dur}" data-media-start="0" '
                    f'data-track-index="{PLATE_TRACK}"></video>')
            lines_js = ", ".join(
                '{c:"%s", h:%s}' % (c, json.dumps(h, ensure_ascii=False)) for c, h in ex["lines"])
            script_lines.append(f'kinetic(760, {t0 + 0.05}, {t1}, [{lines_js}], 0);')

        else:
            raise ComposeError(
                f"beat {tag!r}: unsupported mode {mode!r} -- this tool covers FF/COMP/EVID/KIN, "
                "not CHECK (out of range for a 0-30.78s cut)")

    total_dur = round((round(t_max * 30) / 30) - 0.0003, 6)
    return {
        "plates": plates,
        "script_lines": script_lines,
        "check_call": "",
        "check_override_js": [],
        "caps_js": caps_js,
        "total_dur": total_dur,
    }


def build_render_workdir(generator_dir: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copy2(generator_dir / "index.html", out_dir / "index.html")
    for name in ("hyperframes.json", "package.json"):
        src = generator_dir / name
        if src.is_file():
            shutil.copy2(src, out_dir / name)
    assets_src = generator_dir / "assets"
    if assets_src.is_dir():
        shutil.copytree(assets_src, out_dir / "assets")
    media_src = generator_dir / "media"
    if media_src.is_dir():
        (out_dir / "media").symlink_to(media_src.resolve())


def compose(beats: list[dict], generator_dir: Path, t_max: float, out_dir: Path) -> Path:
    """Beats -> a composed index.html in out_dir, via the unmodified
    assemble.py (subprocess, exactly as render_windows.sh calls it). Returns
    out_dir/index.html. Does not render or mux -- callers that only need the
    HTML (tests, dry-run) can stop here."""
    funcs = load_generator_functions(generator_dir)
    pieces = emit_pieces(beats, t_max, funcs)
    build_render_workdir(generator_dir, out_dir)
    pieces_path = out_dir / "cut_pieces.json"
    pieces_path.write_text(json.dumps(pieces, ensure_ascii=False, indent=2), encoding="utf-8")
    index_path = out_dir / "index.html"
    assemble_py = generator_dir / "assemble.py"
    if not assemble_py.is_file():
        raise ComposeError(f"generator-dir missing assemble.py: {assemble_py}")
    subprocess.run(
        [sys.executable, str(assemble_py), str(index_path), str(pieces_path), "0.0"],
        check=True, cwd=out_dir,
    )
    return index_path


def render(out_dir: Path, mp4_name: str = "rendered.mp4") -> Path:
    out_path = out_dir / mp4_name
    subprocess.run(
        ["npx", "--yes", "hyperframes@0.8.40", "render", "-o", str(out_path)],
        check=True, cwd=out_dir,
    )
    if not out_path.is_file():
        raise ComposeError(f"hyperframes render did not produce {out_path}")
    return out_path


def mux_audio(video_path: Path, audio_src: Path, t_max: float, out_path: Path) -> Path:
    """Replace whatever audio the render baked in with the real narration
    track, trimmed to the same 0..t_max window, video re-encode-free."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_path),
        "-ss", "0", "-t", f"{t_max}", "-i", str(audio_src),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-shortest",
        str(out_path),
    ], check=True)
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--beats", required=True)
    ap.add_argument("--generator-dir", required=True)
    ap.add_argument("--t-max", type=float, required=True)
    ap.add_argument("--audio", default=None, help="narration mp3 to mux onto the render (-c:v copy)")
    ap.add_argument("--out-dir", required=True, help="scratch dir to build the composition + render into")
    ap.add_argument("--out", default=None, help="final muxed mp4 path (default: <out-dir>/final.mp4)")
    ap.add_argument("--no-render", action="store_true",
                     help="stop after composing index.html -- no npx/ffmpeg call")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    beats = json.loads(Path(args.beats).read_text(encoding="utf-8"))
    generator_dir = Path(args.generator_dir)
    out_dir = Path(args.out_dir)

    index_path = compose(beats, generator_dir, args.t_max, out_dir)
    print(f"wrote {index_path}")
    if args.no_render:
        return 0

    rendered = render(out_dir)
    final_path = Path(args.out) if args.out else out_dir / "final.mp4"
    if args.audio:
        mux_audio(rendered, Path(args.audio), args.t_max, final_path)
    else:
        shutil.copy2(rendered, final_path)
    print(f"wrote {final_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ComposeError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)
