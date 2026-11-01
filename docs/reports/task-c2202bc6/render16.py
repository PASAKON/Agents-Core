#!/usr/bin/env python3
"""render16.py - Fast 16:9 render pipeline for 10-15 minute episodes.

Usage:
  python render16.py <episode.json> <out.mp4> [--from S --to S]

Pipeline Steps:
  1. Ken Burns Stills: ffmpeg zoompan (slow move, 1920x1080 @ 30 fps, 2x scale first for smoothness), joined with 0.4s xfades.
  2. Rain Layer: PIL-generated 4-second seamless loop video, blended with `screen` at 35%.
  3. Overlays: Transparent 1920x1080 PNGs via Playwright + overlay.html in ep04 look (rendered per state change, not per frame).
  4. Subtitles: Burned via ASS file (Kanit font, white with dark ink outline, bottom centre at y≈930, max width 1500).
  5. Audio: Voice + optional music ducked by `sidechaincompress`, normalized with `loudnorm` I=-14.
  6. Encoding: -preset veryfast -crf 20 -threads 2. Prints timing for each step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Auto re-exec in Agents-Core virtualenv if playwright or PIL missing
VENV_PY = '/opt/MoonieXHQ/Agents/Core/.venv/bin/python'
try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    if os.path.exists(VENV_PY) and not os.environ.get('RENDER16_REEXEC'):
        os.environ['RENDER16_REEXEC'] = '1'
        os.execv(VENV_PY, [VENV_PY] + sys.argv)
    raise


# Standard font and asset search directories
FONT_DIRS = [
    '/opt/MoonieXHQ/Work/khaohom-survival/ep01/assets/fonts',
    '/opt/MoonieXHQ/Work/khaohom-survival/design-v3/mock/fonts',
    '/opt/MoonieXHQ/Work/khaohom-survival/ep04/build/s1/assets/fonts',
]


def log_timing(step_name: str, duration_sec: float) -> None:
    print(f"[{step_name}] completed in {duration_sec:.2f} s")


def run_cmd(cmd: list[str], desc: str | None = None) -> subprocess.CompletedProcess:
    """Run a subprocess command and handle failures with clear output."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res
    except subprocess.CalledProcessError as e:
        msg = f"Command failed: {' '.join(cmd)}\nStderr: {e.stderr}\nStdout: {e.stdout}"
        if desc:
            msg = f"Error in {desc}:\n{msg}"
        raise RuntimeError(msg) from e


def clean_thai_text(text: str) -> str:
    """Ensure text adheres to project rules: Thai text only, no guillemets « », trimmed."""
    if not text:
        return ""
    cleaned = text.replace("«", "").replace("»", "").strip()
    return cleaned


# ==============================================================================
# Step 1: Ken Burns Stills & xfade
# ==============================================================================

def build_zoompan_expr(move: str, duration_frames: int) -> str:
    """Generate zoompan filter expression for a smooth move.

    Operates on 3840x2160 scaled input and outputs 1920x1080 @ 30fps.
    """
    d = max(1, duration_frames)
    if move == "in":
        # Slow zoom in: 1.00 -> 1.08 centered
        return f"zoompan=z='min(1.0+0.08*(on/{d}),1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s=1920x1080:fps=30"
    elif move == "out":
        # Slow zoom out: 1.08 -> 1.00 centered
        return f"zoompan=z='max(1.08-0.08*(on/{d}),1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s=1920x1080:fps=30"
    elif move == "left":
        # Slow camera pan to the left (content moves right)
        return f"zoompan=z='1.06':x='(1.0-(on/{d}))*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={d}:s=1920x1080:fps=30"
    elif move == "right":
        # Slow camera pan to the right (content moves left)
        return f"zoompan=z='1.06':x='(on/{d})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={d}:s=1920x1080:fps=30"
    else:
        # Default gentle push
        return f"zoompan=z='min(1.0+0.06*(on/{d}),1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s=1920x1080:fps=30"


def render_stills_video(
    stills_data: list[dict],
    t_start: float,
    t_end: float,
    work_dir: Path,
) -> Path:
    """Render each still with zoompan and join with 0.4s xfade transitions."""
    total_duration = t_end - t_start
    active_stills = []

    for s in stills_data:
        s_start = float(s["s"])
        s_end = float(s["e"])
        if s_end <= t_start or s_start >= t_end:
            continue
        # Trim boundaries to the time window
        win_s = max(0.0, s_start - t_start)
        win_e = min(total_duration, s_end - t_start)
        dur = win_e - win_s
        if dur > 0.01:
            active_stills.append({
                "id": s.get("id", "still"),
                "path": s["path"],
                "s": win_s,
                "e": win_e,
                "dur": dur,
                "move": s.get("move", "in"),
            })

    if not active_stills:
        raise ValueError(f"No active stills found in window [{t_start}, {t_end}]")

    num_stills = len(active_stills)
    clips_dir = work_dir / "still_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_files = []

    # 1. Render each still clip
    for i, still in enumerate(active_stills):
        is_last = (i == num_stills - 1)
        # Add 0.4s overlap for crossfade (except last clip)
        clip_dur = still["dur"] + (0.0 if is_last else 0.40)
        frames = int(round(clip_dur * 30.0))
        zoom_expr = build_zoompan_expr(still["move"], frames)

        clip_out = clips_dir / f"clip_{i:04d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", f"{clip_dur:.3f}",
            "-i", str(still["path"]),
            "-vf", f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,{zoom_expr},format=yuv420p",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-threads", "2",
            str(clip_out)
        ]
        run_cmd(cmd, desc=f"rendering still clip {i} ({still['id']})")
        clip_files.append((clip_out, still["dur"]))

    # 2. Join clips with xfade
    base_video_path = work_dir / "base_stills.mp4"
    if num_stills == 1:
        shutil.copyfile(clip_files[0][0], base_video_path)
        return base_video_path

    # Build progressive xfade filter graph
    # Offset of transition k is the sum of nominal durations up to clip k
    inputs = []
    for cf, _ in clip_files:
        inputs.extend(["-i", str(cf)])

    filter_lines = []
    curr_input = "[0:v]"
    accum_offset = 0.0

    for k in range(num_stills - 1):
        accum_offset += clip_files[k][1]
        next_input = f"[{k+1}:v]"
        out_label = f"[v{k+1}]" if k < num_stills - 2 else "[base_video]"
        filter_lines.append(
            f"{curr_input}{next_input} xfade=transition=fade:duration=0.4:offset={accum_offset:.3f} {out_label};"
        )
        curr_input = f"[v{k+1}]"

    xfade_script = work_dir / "xfade_script.txt"
    xfade_script.write_text("\n".join(filter_lines))

    join_cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex_script", str(xfade_script),
        "-map", "[base_video]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-threads", "2",
        str(base_video_path)
    ]
    run_cmd(join_cmd, desc="joining stills with xfade")
    return base_video_path


# ==============================================================================
# Step 2: Rain Layer Generation
# ==============================================================================

def generate_rain_loop_video(work_dir: Path) -> Path:
    """Generate a 4-second seamless rain loop video (120 frames @ 30fps) using PIL.

    Streaks wrap around periodically so frame 119 connects smoothly to frame 0.
    """
    rain_video_path = work_dir / "rain_loop.mp4"
    if rain_video_path.exists():
        return rain_video_path

    rain_frames_dir = work_dir / "rain_frames"
    rain_frames_dir.mkdir(parents=True, exist_ok=True)

    width, height = 1920, 1080
    total_frames = 120  # 4 seconds @ 30 fps
    h_cycle = height + 300  # 1380 px cycle height

    # Seed pseudo-random generation deterministically
    import random
    rng = random.Random(20261101)

    # 1. Far rain streaks (finer, higher density)
    far_streaks = []
    for _ in range(110):
        far_streaks.append({
            "x0": rng.uniform(-100, width + 100),
            "y0": rng.uniform(0, h_cycle),
            "len": rng.uniform(40, 70),
            "width": rng.uniform(1.2, 1.8),
            "cycles": rng.choice([2, 3, 4]),  # integer cycle count over 120 frames
            "color": (195, 215, 240, 180),
        })

    # 2. Near rain streaks (thicker, brighter, faster)
    near_streaks = []
    for _ in range(40):
        near_streaks.append({
            "x0": rng.uniform(-100, width + 100),
            "y0": rng.uniform(0, h_cycle),
            "len": rng.uniform(90, 140),
            "width": rng.uniform(2.4, 3.2),
            "cycles": rng.choice([4, 5, 6]),
            "color": (230, 242, 255, 255),
        })

    all_streaks = far_streaks + near_streaks
    tilt_dx = -0.28  # ~16 degree slant to the left

    for f in range(total_frames):
        # Draw on black background (screen blend: black is fully transparent)
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        progress = f / float(total_frames)

        for s in all_streaks:
            # Periodic y coordinate wrap
            y_curr = (s["y0"] + s["cycles"] * h_cycle * progress) % h_cycle - 150
            x_curr = s["x0"] + (y_curr - s["y0"]) * tilt_dx

            x_end = x_curr + s["len"] * tilt_dx
            y_end = y_curr + s["len"]

            # Only draw if streak overlaps visible screen
            if y_end >= 0 and y_curr <= height and x_curr >= -50 and x_curr <= width + 50:
                draw.line(
                    [(x_curr, y_curr), (x_end, y_end)],
                    fill=s["color"][:3],
                    width=int(round(s["width"]))
                )

        frame_file = rain_frames_dir / f"frame_{f:04d}.png"
        img.save(frame_file)

    # Encode into seamless loop video
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "30",
        "-i", str(rain_frames_dir / "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-threads", "2",
        str(rain_video_path)
    ]
    run_cmd(cmd, desc="encoding rain loop video")

    # Clean up individual frame PNGs to save space
    shutil.rmtree(rain_frames_dir, ignore_errors=True)
    return rain_video_path


# ==============================================================================
# Step 3: Overlays (Playwright + overlay.html in 16:9)
# ==============================================================================

def compute_overlay_timeline(
    hud_data: dict,
    cards_data: list[dict],
    t_start: float,
    t_end: float,
) -> list[tuple[float, float, dict]]:
    """Discretize timeline into intervals of constant visual state."""
    total_dur = t_end - t_start
    change_times = {0.0, total_dur}

    # Helper to check if event falls in window
    def in_window(t_val: float) -> float | None:
        if t_start <= t_val <= t_end:
            return round(t_val - t_start, 3)
        return None

    # Clock timestamps
    clocks = hud_data.get("clock", [])
    for c in clocks:
        w_t = in_window(float(c.get("t", 0)))
        if w_t is not None:
            change_times.add(w_t)

    # Bar timestamps
    bars = hud_data.get("bars", [])
    for b in bars:
        w_t = in_window(float(b.get("t", 0)))
        if w_t is not None:
            change_times.add(w_t)

    # Inventory timestamps
    inv_list = hud_data.get("inv", [])
    for iv in inv_list:
        w_t = in_window(float(iv.get("t", 0)))
        if w_t is not None:
            change_times.add(w_t)

    # Popup timestamps (active for 2.4s)
    popups = hud_data.get("popups", [])
    for p in popups:
        pt = float(p.get("t", 0))
        t1 = in_window(pt)
        t2 = in_window(pt + 2.4)
        if t1 is not None:
            change_times.add(t1)
        if t2 is not None:
            change_times.add(t2)

    # Cards timestamps
    for card in cards_data:
        cs = float(card.get("s", 0))
        ce = float(card.get("e", 0))
        t1 = in_window(cs)
        t2 = in_window(ce)
        if t1 is not None:
            change_times.add(t1)
        if t2 is not None:
            change_times.add(t2)

    sorted_times = sorted(change_times)

    # Query active state for a given absolute episode time
    def get_state_at(abs_time: float) -> dict:
        # 1. Clock
        active_clock = {"day": "วันที่ 4", "time": "06:00 น."}
        for c in clocks:
            if float(c.get("t", 0)) <= abs_time:
                active_clock = {
                    "day": clean_thai_text(c.get("day", "วันที่ 4")),
                    "time": clean_thai_text(c.get("clock", "06:00 น."))
                }

        # 2. Bars
        active_bars = {"hp": 100, "hunger": 100}
        for b in bars:
            if float(b.get("t", 0)) <= abs_time:
                active_bars = {
                    "hp": float(b.get("hp", 100)),
                    "hunger": float(b.get("hunger", 100)),
                }

        # 3. Inventory
        active_inv = {"slots": []}
        for iv in inv_list:
            if float(iv.get("t", 0)) <= abs_time:
                raw_slots = iv.get("slots", [])
                formatted_slots = []
                for s in raw_slots:
                    if not s:
                        formatted_slots.append(None)
                    else:
                        cnt = s.get("count")
                        if cnt is None and "value" in s:
                            cnt = f"{s['value']}%" if s.get("unit") == "pct" else f"×{s['value']}"
                        formatted_slots.append({
                            "id": s.get("id", "default"),
                            "count": cnt or "",
                            "held": bool(s.get("equipped", False)),
                        })
                active_inv = {"slots": formatted_slots}

        # 4. Popups (within 2.4s)
        active_popups = []
        for p in popups:
            pt = float(p.get("t", 0))
            if pt <= abs_time < pt + 2.4:
                active_popups.append({
                    "kind": p.get("kind", "gain"),
                    "item": p.get("item", "canfish"),
                    "text": clean_thai_text(p.get("text", ""))
                })

        # 5. Cards
        active_card = None
        for card in cards_data:
            cs = float(card.get("s", 0))
            ce = float(card.get("e", 0))
            if cs <= abs_time < ce:
                active_card = {
                    "kind": card.get("kind", "world"),
                    "title": clean_thai_text(card.get("title", "")),
                    "lines": [clean_thai_text(ln) for ln in card.get("lines", [])]
                }
                break

        return {
            "clock": active_clock,
            "bars": active_bars,
            "inv": active_inv,
            "popups": active_popups,
            "card": active_card,
        }

    # Form raw slices
    slices = []
    for i in range(len(sorted_times) - 1):
        s_time = sorted_times[i]
        e_time = sorted_times[i + 1]
        if e_time - s_time < 0.03:
            continue
        mid = (s_time + e_time) / 2.0
        abs_t = mid + t_start
        st = get_state_at(abs_t)
        slices.append((s_time, e_time, st))

    # Merge consecutive identical states
    merged = []
    for s_time, e_time, st in slices:
        if merged and merged[-1][2] == st:
            merged[-1] = (merged[-1][0], e_time, st)
        else:
            merged.append((s_time, e_time, st))

    return merged


def render_overlay_pngs(
    timeline: list[tuple[float, float, dict]],
    template_path: Path,
    work_dir: Path,
) -> Path:
    """Render unique overlay states as transparent 1920x1080 PNGs via Playwright.

    Returns the path to the ffmpeg concat demuxer script file.
    """
    overlays_dir = work_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    # Map state hash -> saved PNG path
    state_cache: dict[str, Path] = {}
    concat_entries: list[tuple[Path, float]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--allow-file-access-from-files"]
        )
        try:
            page = browser.new_page(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1
            )
            page.goto(f"file://{template_path.resolve()}")
            page.wait_for_selector("html[data-ready='1']", timeout=20000)

            for s_time, e_time, state in timeline:
                dur = e_time - s_time
                state_json = json.dumps(state, sort_keys=True)
                st_hash = hashlib.md5(state_json.encode("utf-8")).hexdigest()[:12]

                png_path = overlays_dir / f"ov_{st_hash}.png"
                if st_hash not in state_cache:
                    # Update DOM with current state
                    page.evaluate("renderState", state)
                    # Screenshot with transparent background
                    page.screenshot(path=str(png_path), omit_background=True)
                    state_cache[st_hash] = png_path

                concat_entries.append((png_path, dur))
        finally:
            browser.close()

    # Write ffmpeg concat file
    concat_file = work_dir / "overlays_concat.txt"
    lines = ["ffconcat version 1.0"]
    for path, dur in concat_entries:
        lines.append(f"file '{path.resolve()}'")
        lines.append(f"duration {dur:.3f}")
    if concat_entries:
        # Repeat last file to satisfy ffmpeg concat demuxer convention
        lines.append(f"file '{concat_entries[-1][0].resolve()}'")

    concat_file.write_text("\n".join(lines))
    return concat_file


# ==============================================================================
# Step 4: ASS Subtitles
# ==============================================================================

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp H:MM:SS.cs."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def generate_ass_file(
    subs_data: list[dict],
    t_start: float,
    t_end: float,
    work_dir: Path,
) -> Path:
    """Write ASS file adhering to brief: Kanit, white with dark outline, bottom centre at y≈930, max width 1500."""
    total_dur = t_end - t_start
    ass_path = work_dir / "subtitles.ass"

    # PlayRes 1920x1080.
    # Max width 1500 -> MarginL: 210, MarginR: 210 ((1920-1500)/2).
    # Bottom centre at y≈930 -> MarginV: 120 (1080 - 120 = 960 baseline).
    # PrimaryColour: &H00FFFFFF (white)
    # OutlineColour: &H00281412 (#121428 ink)
    header = """[Script Info]
Title: KhaoHom Survival 16:9
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Kanit,42,&H00FFFFFF,&H000000FF,&H00281412,&H80121428,-1,0,0,0,100,100,0,0,1,3.5,0,2,210,210,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for sub in subs_data:
        s = float(sub.get("s", 0))
        e = float(sub.get("e", 0))
        if e <= t_start or s >= t_end:
            continue
        s_win = max(0.0, s - t_start)
        e_win = min(total_dur, e - t_start)
        if e_win - s_win < 0.05:
            continue
        text = clean_thai_text(sub.get("text", ""))
        events.append(
            f"Dialogue: 0,{format_ass_time(s_win)},{format_ass_time(e_win)},Default,,0,0,0,,{text}"
        )

    ass_path.write_text(header + "\n".join(events))
    return ass_path


# ==============================================================================
# Step 5 & 6: Audio Processing & Final Composite Assembly
# ==============================================================================

def render_final_composite(
    base_video: Path,
    rain_video: Path,
    overlays_concat: Path,
    ass_subtitles: Path,
    voice_path: str | None,
    music_path: str | None,
    total_duration: float,
    t_start: float,
    out_mp4: Path,
) -> None:
    """Composite video layers, duck audio with sidechaincompress, loudnorm I=-14, and encode."""
    inputs = [
        "-i", str(base_video),
        "-stream_loop", "-1", "-i", str(rain_video),
        "-f", "concat", "-safe", "0", "-i", str(overlays_concat),
    ]

    # Resolve fonts dir for subtitles filter
    fonts_dir = ""
    for fd in FONT_DIRS:
        if os.path.isdir(fd):
            fonts_dir = fd
            break

    # Build video filter chain:
    # 1. Screen blend rain loop at 35% opacity
    # 2. Overlay transparent HUD/cards
    # 3. Burn Kanit ASS subtitles
    ass_escaped = str(ass_subtitles.resolve()).replace("\\", "/").replace(":", "\\:")
    fontsdir_arg = f":fontsdir='{fonts_dir}'" if fonts_dir else ""

    v_filter = (
        "[0:v][1:v] blend=all_mode='screen':all_opacity=0.35 [rained]; "
        "[rained][2:v] overlay=0:0:shortest=0 [overlaid]; "
        f"[overlaid] subtitles='{ass_escaped}'{fontsdir_arg} [vout]"
    )

    # Build audio filter chain
    has_voice = voice_path and os.path.exists(voice_path)
    has_music = music_path and os.path.exists(music_path)

    audio_idx = 3
    if has_voice:
        inputs.extend(["-ss", f"{t_start:.3f}", "-t", f"{total_duration:.3f}", "-i", str(voice_path)])
        voice_in = f"[{audio_idx}:a]"
        audio_idx += 1
    else:
        voice_in = None

    if has_music:
        inputs.extend(["-stream_loop", "-1", "-i", str(music_path)])
        music_in = f"[{audio_idx}:a]"
        audio_idx += 1
    else:
        music_in = None

    if has_voice and has_music:
        # Music ducked by voice using sidechaincompress, then loudnorm I=-14
        a_filter = (
            f"{music_in} atrim=0:{total_duration:.3f},asetpts=PTS-STARTPTS [m_trimmed]; "
            f"[m_trimmed]{voice_in} sidechaincompress=threshold=0.08:ratio=4:attack=50:release=400 [m_ducked]; "
            f"{voice_in}[m_ducked] amix=inputs=2:duration=first:dropout_transition=2 [a_mixed]; "
            "[a_mixed] loudnorm=I=-14:TP=-1.5:LRA=11 [aout]"
        )
    elif has_voice:
        a_filter = f"{voice_in} loudnorm=I=-14:TP=-1.5:LRA=11 [aout]"
    elif has_music:
        a_filter = f"{music_in} atrim=0:{total_duration:.3f},loudnorm=I=-14:TP=-1.5:LRA=11 [aout]"
    else:
        # Fallback silent audio track
        a_filter = f"aevalsrc=0:d={total_duration:.3f} [aout]"

    filter_complex = f"{v_filter}; {a_filter}"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-t", f"{total_duration:.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_mp4)
    ]
    run_cmd(cmd, desc="rendering final composite video")


# ==============================================================================
# Main Orchestrator
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="KhaoHom Survival 16:9 Fast Render Pipeline")
    parser.add_argument("episode", help="Path to episode.json")
    parser.add_argument("output", help="Path to output mp4")
    parser.add_argument("--from", dest="from_s", type=float, default=None, help="Start time (seconds)")
    parser.add_argument("--to", dest="to_s", type=float, default=None, help="End time (seconds)")
    parser.add_argument("--keep-temp", action="store_true", help="Do not delete temporary workspace")
    args = parser.parse_args()

    ep_path = Path(args.episode)
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not ep_path.exists():
        sys.exit(f"Error: episode file not found: {ep_path}")

    episode = json.loads(ep_path.read_text(encoding="utf-8"))

    # Resolve HTML overlay template
    script_dir = Path(__file__).resolve().parent
    template_path = script_dir / "overlay.html"
    if not template_path.exists():
        sys.exit(f"Error: overlay template missing: {template_path}")

    # Determine timeline bounds
    stills = episode.get("stills", [])
    if not stills:
        sys.exit("Error: 'stills' list is empty in episode.json")

    max_still_end = max(float(s["e"]) for s in stills)
    t_start = max(0.0, args.from_s if args.from_s is not None else 0.0)
    t_end = min(max_still_end, args.to_s if args.to_s is not None else max_still_end)

    if t_end <= t_start:
        sys.exit(f"Error: invalid time window [--from {t_start}, --to {t_end}]")

    total_duration = t_end - t_start
    print(f"--- KhaoHom Survival 16:9 Render Pipeline ---")
    print(f"Episode: {ep_path.name}")
    print(f"Time Window: {t_start:.2f} s -> {t_end:.2f} s (Duration: {total_duration:.2f} s)")
    print(f"Output: {out_path}")
    print("---------------------------------------------")

    work_dir = Path(tempfile.mkdtemp(prefix="render16_"))
    overall_start = time.time()

    try:
        # Step 1: Ken Burns Stills
        t0 = time.time()
        base_video = render_stills_video(stills, t_start, t_end, work_dir)
        log_timing("Step 1/6: Ken Burns Stills (zoompan + xfade)", time.time() - t0)

        # Step 2: Rain Layer
        t0 = time.time()
        rain_video = generate_rain_loop_video(work_dir)
        log_timing("Step 2/6: Rain Loop Video", time.time() - t0)

        # Step 3: Overlays
        t0 = time.time()
        timeline = compute_overlay_timeline(
            episode.get("hud", {}),
            episode.get("cards", []),
            t_start,
            t_end
        )
        overlays_concat = render_overlay_pngs(timeline, template_path, work_dir)
        log_timing(f"Step 3/6: Overlays (Playwright, {len(timeline)} states)", time.time() - t0)

        # Step 4: Subtitles
        t0 = time.time()
        ass_path = generate_ass_file(
            episode.get("subs", []),
            t_start,
            t_end,
            work_dir
        )
        log_timing("Step 4/6: ASS Subtitles", time.time() - t0)

        # Step 5 & 6: Audio & Final Composite Render
        t0 = time.time()
        render_final_composite(
            base_video=base_video,
            rain_video=rain_video,
            overlays_concat=overlays_concat,
            ass_subtitles=ass_path,
            voice_path=episode.get("voice"),
            music_path=episode.get("music"),
            total_duration=total_duration,
            t_start=t_start,
            out_mp4=out_path,
        )
        log_timing("Step 5-6/6: Composite Render & Audio Normalization", time.time() - t0)

        total_elapsed = time.time() - overall_start
        print(f"=== Render Finished Successfully in {total_elapsed:.2f} s ===")
        print(f"Delivered file: {out_path} ({out_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return 0

    finally:
        if not args.keep_temp:
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            print(f"[Debug] Kept temporary files in: {work_dir}")


if __name__ == "__main__":
    sys.exit(main())
