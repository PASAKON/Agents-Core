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
  4. Renders with `npx hyperframes@0.8.40 render`. With no `--t0` (the
     whole-episode case), muxes the real narration audio on top with ffmpeg
     (-c:v copy). With `--t0` > 0 (task-99f3d2e8's range render, PLAN.md's
     segment contract), instead trims to a frame-exact, video-only,
     fixed-encoder clip via trim_range() -- no audio, ready for
     tools/bl_merge.py to concat with every other range's own output.

--generator-dir must hold: build_cut.py, assemble.py, index.html (the
FIXED template -- .claude/skills/blackliquidity-cut/template/index.html,
task-1678d38e's one `caption(at, out, text)` generator, no per-mode
`addCap` branch -- NOT a branch copy that has already been spliced),
hyperframes.json, package.json, assets/, and media/ (the stills/avatar
clips the beats' `extra.img` / mode reference, flat under media/ exactly
as build_cut.py's f'media/{img}' expects). Every caption this tool emits
calls that template's `caption()` -- see emit_pieces()'s own docstring.
Optionally SCRIPT.tsv at the generator-dir's own root (tag -> 1-based
script line number) -- when present, a KIN beat with no plate named
defaults to that line's own `media/broll/S{n:02d}.mp4` (task-9a4f1029,
see default_kin_broll()); its absence is not an error, it just means no
default is available.

task-9a4f1029 fixed three gaps every editor using this tool would hit
again (found by task-1a5eb073's Arm 1 pilot, the first real end-to-end
render against the actual EP57 fixture):
  - a KIN beat with no plate named now defaults to its own line's broll
    (darkened), never the bare kit background (see default_kin_broll());
  - COMP/EVID's spotlight() now exits exactly when its own plate does --
    a deliberate, documented divergence from build_cut.py's own mirrored
    call (see SPOTLIGHT_EXIT_LEAD below), because assemble.py itself
    (where spotlight() is actually defined) stays off-limits;
  - an FF/COMP beat outside every recorded avatar window now fails fast
    with a clear message (see check_avatar_window()) instead of burning a
    60s+ render before hyperframes' own media_start_out_of_range surfaces.

Usage:
    python3 tools/bl_compose.py \\
        --beats beats.json --generator-dir <dir> --t-max 30.78 \\
        --audio audio-hq.mp3 --out-dir <workdir> --out final.mp4
    # --no-render stops after writing the composed index.html (tests/dry-run)

    # range render (PLAN.md segment contract) -- video-only, [t0, t-max):
    python3 tools/bl_compose.py \\
        --beats beats.json --generator-dir <dir> --t0 39.3 --t-max 65.8333 \\
        --out-dir <workdir> --out seg02.mp4
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CANVAS_W, CANVAS_H = 1080, 1920
FPS = 30


def frame_floor(t: float, fps: int = FPS) -> float:
    """Floor `t` to the nearest fps frame boundary (tools/bl_split.py's own
    frame_floor -- duplicated here rather than imported so this module has
    no import-time dependency on bl_split.py's ffmpeg/argparse surface)."""
    return math.floor(t * fps + 1e-6) / fps


# Exactly the names this tool borrows from build_cut.py -- nothing else in
# that file ever runs.
_ALLOWED_FUNCS = {"lip_offset", "pick_lip", "img_placement", "box_to_canvas", "pct", "esc"}
_ALLOWED_CONSTS = {"CANVAS_W", "CANVAS_H", "LIP_DUR", "PLATE_TRACK", "AVATAR_TRACK"}


class ComposeError(RuntimeError):
    pass


# assemble.py's own spotlight() (defined in its `helpers` string, off-limits
# per this module's docstring) calls `hide(id, out-0.1)`, and index.html's
# shared `hide()` has a hard-coded 0.18s duration -- so the fade actually
# FINISHES at out-0.1+0.18 = out+0.08, i.e. 0.08s AFTER the beat's own plate
# hard-cuts to the next beat. Measured on task-1a5eb073's pilot: 5 empty-
# frame clusters, every one an EVID/COMP->KIN cut, each ~0.06-0.08s (the
# 30fps sampling grid's own granularity accounts for the small spread).
# Never edit assemble.py -- tune the ARGUMENT instead: pass `t1 -
# SPOTLIGHT_EXIT_LEAD` as spotlight()'s own `out` so its unmodified formula
# finishes exactly when the plate does (SKILL.md §6d: "exits hard cut").
SPOTLIGHT_EXIT_LEAD = 0.08


def load_script_line_map(generator_dir: Path) -> dict[str, int]:
    """tag -> 1-based script line number, from the generator-dir's own
    SCRIPT.tsv (fixture-full stages one; the older 30.78s fixture does not
    -- an empty map there just means default_kin_broll() has nothing to
    default from, never an error). SCRIPT.tsv has NO line-number column of
    its own (confirmed against the real fixture, task-9a4f1029): each row
    is `tag \t Thai caption \t shot basename \t category \t note`, and
    "line n" (SKILL.md, the brief's "line n <-> S{n:02d}.mp4") means the
    row's own 1-based POSITION in the file, counting only non-blank rows."""
    script_path = generator_dir / "SCRIPT.tsv"
    if not script_path.is_file():
        return {}
    mapping: dict[str, int] = {}
    n = 0
    for line in script_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n += 1
        tag = line.split("\t", 1)[0]
        if tag:
            mapping[tag] = n
    return mapping


def default_kin_broll(tag: str, script_line_map: dict[str, int]) -> str | None:
    """SKILL.md §6d plate table: a KIN beat never shows the bare kit
    background. This episode's own scene clip (line n <-> media/broll/
    S{n:02d}.mp4, task-9a4f1029, one clip per SCRIPT.tsv line) is the
    default plate whenever the beat's own `extra` names none. Returns None
    (no default) when the tag isn't in the map -- the caller then falls
    back to the old bare-background behaviour rather than guessing a path
    that doesn't exist."""
    n = script_line_map.get(tag)
    return f"broll/S{n:02d}.mp4" if n else None


def check_avatar_window(tag: str, mode: str, abs_t0: float, lipname: str, funcs: dict[str, Any]) -> None:
    """FF/COMP can only render where a recorded lipsync take actually
    covers `abs_t0` -- outside that, hyperframes refuses at render time
    (media_start_out_of_range / VIDEO_SOURCE_UNRENDERABLE) after a full
    60s+ render attempt (task-1a5eb073's pilot hit this on its first
    draft, 12 beats). Catch it here instead: fast, in Python, before any
    render is attempted, naming every valid window so the caller can move
    the beat to EVID or KIN. A generator whose build_cut.py exposes no
    LIP_DUR (older fixtures) skips this check entirely -- there is nothing
    to validate against."""
    lip_offset = funcs["lip_offset"]
    lip_dur: dict[str, float] = funcs.get("LIP_DUR") or {}
    if not lip_dur:
        return
    start = lip_offset(lipname)
    dur = lip_dur.get(lipname)
    media_start = abs_t0 - start
    if dur is not None and -1e-6 <= media_start < dur - 1e-6:
        return
    windows = ", ".join(
        f"{name} [{lip_offset(name):g}, {lip_offset(name) + d:g})"
        for name, d in sorted(lip_dur.items(), key=lambda kv: lip_offset(kv[0])))
    raise ComposeError(
        f"beat {tag!r} ({mode}) at t0={abs_t0:g}s has no avatar footage there -- "
        f"pick_lip() maps it to {lipname!r}, "
        f"{'which this generator exposes no LIP_DUR for' if dur is None else f'valid only in [{start:g}, {start + dur:g})'}. "
        f"Valid avatar windows: {windows}. Use EVID or KIN for this beat instead of FF/COMP.")


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


def emit_pieces(beats: list[dict], t_max: float, funcs: dict[str, Any], t0_window: float = 0.0,
                 script_line_map: dict[str, int] | None = None) -> dict:
    """Beats -> the same cut_pieces.json shape build_cut.py writes (plates,
    script_lines, check_call, check_override_js, caps_js, total_dur).

    Mirrors build_cut.py's per-mode emission (lines ~175-264 on the branch)
    beat for beat. `t_max` and every beat's `t0`/`t1` are ABSOLUTE episode
    time (matching timings.tsv). `t0_window` (task-99f3d2e8's range render,
    PLAN.md's segment contract) shifts only the COMPOSITION-PLACEMENT
    timestamps (data-start/data-duration, caption/spotlight/credit/kinetic
    calls) so a segment's own render starts at composition-local t=0 --
    `pick_lip`/`lip_offset`/`media_start` keep using the beat's true
    ABSOLUTE time, because those seek into a media file whose own timeline
    never shifts. CHECK mode (the SUMMARY-4/5/6 checklist card) is out of
    scope here -- a CHECK-mode beat is a hard error rather than a silent
    no-op.

    One caption style, every mode -- SKILL.md §6f (CEO ruling 2026-09-25):
    every beat with a `cap` calls the template's single `caption(at, out,
    text)` generator. No `addCap(..., kind, ...)` branch, no per-mode chip/
    rail/strip, no inline style -- that per-mode branch is exactly the bug
    the CEO rejected (EP57 shipped three different caption looks).

    Plates hold by construction -- SKILL.md §6g: a beat's plate always
    spans the full [t0, ext_end) computed by compute_ext_end() above,
    never trimmed to the underlying media's own remaining length. A video
    source shorter than its plate's duration holds on its last decoded
    frame rather than leaving a gap; a gap (the plate disappearing before
    the next one starts) is the actual defect, not a frozen frame -- the
    30fps empty-frame gate (tools/bl_checker.py) is the backstop that would
    catch a source so short it decodes to nothing.

    `script_line_map` (task-9a4f1029, from load_script_line_map()) is the
    generator-dir's own SCRIPT.tsv tag -> line-number map, used only to
    default a bare KIN beat's plate (see default_kin_broll()); every other
    mode ignores it.
    """
    img_placement = funcs["img_placement"]
    box_to_canvas = funcs["box_to_canvas"]
    pick_lip = funcs["pick_lip"]
    lip_offset = funcs["lip_offset"]
    esc = funcs["esc"]
    PLATE_TRACK = funcs.get("PLATE_TRACK", 0)
    AVATAR_TRACK = funcs.get("AVATAR_TRACK", 1)
    script_line_map = script_line_map or {}

    ext_end = compute_ext_end(beats, t_max)
    plates: list[str] = []
    script_lines: list[str] = []
    caps_js: list[str] = []

    for b in sorted(beats, key=lambda b: b["t0"]):
        tag, abs_t0, mode = b["tag"], b["t0"], b["mode"]
        ex = b.get("extra") or {}
        if abs_t0 < t0_window - 0.001 or abs_t0 >= t_max - 0.001:
            continue
        t0 = round(abs_t0 - t0_window, 3)
        t1 = round(min(ext_end[tag], t_max) - t0_window, 3)
        dur = round(t1 - t0, 3)
        safe_id = tag.lower().replace("-", "")

        if mode == "FF":
            lipname = pick_lip(abs_t0)
            check_avatar_window(tag, mode, abs_t0, lipname, funcs)
            media_start = round(abs_t0 - lip_offset(lipname), 3)
            plates.append(
                f'<video class="clip" id="v_{safe_id}" src="media/{lipname}.mp4" muted playsinline '
                f'data-start="{t0}" data-duration="{dur}" data-media-start="{media_start}" '
                f'data-track-index="{PLATE_TRACK}"></video>')
            if ex.get("cap"):
                caps_js.append(f'caption({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)});')

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
            check_avatar_window(tag, mode, abs_t0, lipname, funcs)
            media_start = round(abs_t0 - lip_offset(lipname), 3)
            style = (f'top:{top - shift}px;left:{left}px;right:auto;bottom:auto;'
                     f'width:{dw}px;height:{dh}px;transform:none')
            plates.append(
                f'<img class="clip" id="v_{safe_id}" src="media/{img}" '
                f'style="{style}" data-start="{t0}" data-duration="{plate_dur}" '
                f'data-track-index="{PLATE_TRACK}">')
            plates.append(
                f'<video class="avatar-comp" id="av_{safe_id}" src="media/matte/{lipname}-matte.webm" '
                f'muted playsinline data-start="{t0}" data-duration="{avatar_dur}" '
                f'data-media-start="{media_start}" data-track-index="{AVATAR_TRACK}"></video>')
            box_c = box_to_canvas(ex.get("box"), place)
            if box_c:
                bx, by, bw, bh = box_c
                by -= shift
                script_lines.append(
                    f'spotlight("sp_{safe_id}", {t0 + 0.15}, {round(t1 - SPOTLIGHT_EXIT_LEAD, 3)}, '
                    f'{round(bx)}, {round(by)}, {round(bw)}, {round(bh)});')
            if ex.get("cap"):
                caps_js.append(f'caption({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)});')
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
                    f'spotlight("sp_{safe_id}", {t0 + 0.25}, {round(t1 - SPOTLIGHT_EXIT_LEAD, 3)}, '
                    f'{round(bx)}, {round(by)}, {round(bw)}, {round(bh)});')
            if ex.get("credit"):
                script_lines.append(f'credit("cr_{safe_id}", {t0 + 0.1}, {t1}, "{esc(ex["credit"])}");')
            if ex.get("cap"):
                caps_js.append(f'caption({t0}, {t1}, {json.dumps(ex["cap"], ensure_ascii=False)});')

        elif mode == "KIN":
            # SKILL.md §6d plate table: never a bare kit background. An
            # editor can still name their own plate (`extra["broll"]`,
            # including an explicit falsy value to opt out of one entirely)
            # -- only a beat that names NONE falls back to its own line's
            # scene clip, darkened (task-9a4f1029; task-1a5eb073's pilot put
            # 15 of 40 KIN lines on bare background for lack of this).
            broll = ex["broll"] if "broll" in ex else default_kin_broll(tag, script_line_map)
            if broll:
                plates.append(
                    f'<video class="clip plate-darkened" id="v_{safe_id}" src="media/{broll}" '
                    f'muted playsinline data-start="{t0}" data-duration="{dur}" data-media-start="0" '
                    f'data-track-index="{PLATE_TRACK}"></video>')
            lines_js = ", ".join(
                '{c:"%s", h:%s}' % (c, json.dumps(h, ensure_ascii=False)) for c, h in ex["lines"])
            script_lines.append(f'kinetic(760, {t0 + 0.05}, {t1}, [{lines_js}], 0); // {tag}')

        else:
            raise ComposeError(
                f"beat {tag!r}: unsupported mode {mode!r} -- this tool covers FF/COMP/EVID/KIN, not CHECK")

    window_dur = t_max - t0_window
    total_dur = round((round(window_dur * FPS) / FPS) - 0.0003, 6)
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


def compose(beats: list[dict], generator_dir: Path, t_max: float, out_dir: Path, t0: float = 0.0) -> Path:
    """Beats -> a composed index.html in out_dir, via the unmodified
    assemble.py (subprocess, exactly as render_windows.sh calls it). Returns
    out_dir/index.html. Does not render or mux -- callers that only need the
    HTML (tests, dry-run) can stop here. `t0` (task-99f3d2e8 range render):
    the composition covers only [t0, t_max) of ABSOLUTE episode time,
    starting at composition-local t=0 -- see emit_pieces()'s own docstring."""
    funcs = load_generator_functions(generator_dir)
    script_line_map = load_script_line_map(generator_dir)
    pieces = emit_pieces(beats, t_max, funcs, t0_window=t0, script_line_map=script_line_map)
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


TRIM_ENCODER_ARGS = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18"]


def trim_range(video_path: Path, dur: float, out_path: Path, fps: int = FPS) -> Path:
    """PLAN.md's range render (task-99f3d2e8, item 4): a segment's own
    render already starts at composition-local t=0 (emit_pieces's
    `t0_window` shift) and needs no start-side cut -- this is a
    NORMALIZATION pass every range goes through, so every part bl_merge.py
    concats shares identical codec params and an exact 30fps frame count:
    video-only (`-an`, the segment contract -- the master narration audio
    is muxed once, across the whole episode, at merge time), forced CFR at
    `fps`, hard-capped to `round(dur*fps)` frames (frame-exact on the grid,
    never rounding up past what the range actually covers), same encoder
    settings on every call so `ffmpeg -c copy` concat never re-encodes."""
    frame_count = int(round(frame_floor(dur, fps) * fps))
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(video_path),
        "-an", "-r", str(fps), "-vsync", "cfr", "-frames:v", str(frame_count),
        *TRIM_ENCODER_ARGS, str(out_path),
    ], check=True)
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--beats", required=True)
    ap.add_argument("--generator-dir", required=True)
    ap.add_argument("--t-max", type=float, required=True, help="absolute episode end time this call composes to")
    ap.add_argument("--t0", type=float, default=0.0,
                     help="range render (PLAN.md segment contract): absolute episode start time "
                          "of this call's own window -- composes/renders ONLY [t0, t-max), video-only, "
                          "frame-exact, no audio mux even if --audio is given")
    ap.add_argument("--audio", default=None, help="narration mp3 to mux onto the render (-c:v copy); "
                                                    "ignored when --t0 > 0 (range render is video-only)")
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

    index_path = compose(beats, generator_dir, args.t_max, out_dir, t0=args.t0)
    print(f"wrote {index_path}")
    if args.no_render:
        return 0

    rendered = render(out_dir)
    final_path = Path(args.out) if args.out else out_dir / "final.mp4"
    if args.t0 > 0.0:
        if args.audio:
            print("note: --audio ignored -- range render (--t0 > 0) is always video-only", file=sys.stderr)
        trim_range(rendered, args.t_max - args.t0, final_path)
    elif args.audio:
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
