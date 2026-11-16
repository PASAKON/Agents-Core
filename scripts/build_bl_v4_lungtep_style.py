#!/usr/bin/env python3
"""
build_bl_v4_lungtep_style.py — Build the BLACK LIQUIDITY V4 (@lungtepuniverse-upgraded) edit:
  1. 100% Character-in-Scene Element Footage (CHAR_EP1_*.mp4 with BL Main Character in every shot)
  2. Hook 0.00s - 3.55s Rapid-Fire Montage (0.50s x 5 + 1.05s = 6 cuts) + Multi-Layer Hook SFX
  3. All 8 Varied Transition Motions (Scale Punch 1.38x, Horizontal Whip-Pan Blur, Vertical Speed-Warp,
     Exposure Flash Pop, Diagonal Prism Shard Burst, Chromatic Negative Shockwave, 180° Gravity Flip,
     RGB Chromatic Glitch Split) + Interactive Red Callout Box & Pointer
  4. Matched Transition SFX Engine synced to exact cut timestamps + -14.0 LUFS loudness normalization
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

BROLL_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/broll-incoming")
WORK_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/basket-pilot1-work")
CUT_A_DIR = WORK_DIR / "cut_pilot1_A_65s"
AUDIO_DIR = WORK_DIR / "audio"

FPS = 30
WIDTH = 1080
HEIGHT = 1920
TOTAL_DUR = 65.44
TOTAL_FRAMES = int(round(TOTAL_DUR * FPS))
SR = 48000


# ============================================================================
# 1. CUT SCHEDULE (28 Cuts: 6 Rapid Hook Cuts in 0.00-3.55s + 22 Body Cuts)
# ============================================================================
# Each segment: (start_s, end_s, clip_id, media_start_s, zoom_scale, focus_xy, trans_in)
# trans_in is the transition effect applied across the cut boundary at `start_s`:
#   - "hook_punch"      : Hook 0.00s initial zoom-in impact (1.16x -> 1.0x)
#   - "whip_pan_h"      : Horizontal whip-pan directional blur + slide (0.16s)
#   - "scale_punch"     : Instant 1.0x -> 1.38x jump-zoom cut-in on same/paired shot
#   - "prism_shatter"   : Diagonal prism shard split + neon edge bloom (0.18s)
#   - "rgb_glitch"      : RGB chromatic channel split + horizontal scanline glitch (0.16s)
#   - "exposure_flash"  : Exposure flash pop (+45% brightness + red-white bloom, 0.14s)
#   - "neg_shockwave"   : Chromatic negative inversion shockwave (0.20s)
#   - "whip_tilt_v"     : Vertical speed-warp whip-tilt + directional blur (0.16s)
#   - "gravity_flip"    : 180-degree vertical gravity flip whip (0.16s)

CUT_SCHEDULE: List[Dict[str, object]] = [
    # --- HOOK: 0.00s - 3.55s (6 rapid cuts: 0.50s x 5 + 1.05s) ---
    {
        "start": 0.00, "end": 0.50,
        "clip": "CHAR_EP1_B1_HOOK_01", "mstart": 0.20,
        "scale": 1.08, "focus": (0.50, 0.45),
        "trans": "hook_punch", "sfx": "sub_shutter_hit",
    },
    {
        "start": 0.50, "end": 1.00,
        "clip": "CHAR_EP1_B2_MISTAKE_01", "mstart": 0.60,
        "scale": 1.12, "focus": (0.50, 0.46),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    {
        "start": 1.00, "end": 1.50,
        "clip": "CHAR_EP1_B3_MECHANISM_01", "mstart": 0.80,
        "scale": 1.34, "focus": (0.50, 0.46),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    {
        "start": 1.50, "end": 2.00,
        "clip": "CHAR_EP1_B3_MECHANISM_02", "mstart": 1.00,
        "scale": 1.15, "focus": (0.50, 0.45),
        "trans": "prism_shatter", "sfx": "swish_tom",
    },
    {
        "start": 2.00, "end": 2.50,
        "clip": "CHAR_EP1_B4_CONSEQUENCE_01", "mstart": 0.80,
        "scale": 1.22, "focus": (0.50, 0.45),
        "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz",
    },
    {
        "start": 2.50, "end": 3.55,
        "clip": "CHAR_EP1_B6_DISCIPLINE_FIX_01", "mstart": 0.40,
        "scale": 1.10, "focus": (0.50, 0.52),
        "trans": "whip_tilt_v", "sfx": "riser_build",
    },

    # --- BEAT 1 BODY (3.55s - 6.92s): Counter-Intuitive Hook ("ใช้สมอง ผิดเวลามาตลอด") ---
    {
        "start": 3.55, "end": 5.25,
        "clip": "CHAR_EP1_B1_HOOK_01", "mstart": 1.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    },
    {
        "start": 5.25, "end": 6.92,
        "clip": "CHAR_EP1_B3_MECHANISM_01", "mstart": 1.50,
        "scale": 1.36, "focus": (0.50, 0.48),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },

    # --- BEAT 2 (6.92s - 21.20s): Mirror Failed Habit ("จ้องจอถึงตีสอง / กำไรหาย / สมองไม่เหลือสติ") ---
    {
        "start": 6.92, "end": 9.08,
        "clip": "CHAR_EP1_B2_MISTAKE_01", "mstart": 0.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    {
        "start": 9.08, "end": 11.24,
        "clip": "CHAR_EP1_B3_MECHANISM_02", "mstart": 0.40,
        "scale": 1.34, "focus": (0.50, 0.42),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    {
        "start": 11.24, "end": 13.60,
        "clip": "CHAR_EP1_B2_MISTAKE_02", "mstart": 0.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "neg_shockwave", "sfx": "neg_shockwave_zap",
    },
    {
        "start": 13.60, "end": 16.00,
        "clip": "CHAR_EP1_B4_CONSEQUENCE_01", "mstart": 1.20,
        "scale": 1.36, "focus": (0.52, 0.46),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    {
        "start": 16.00, "end": 18.60,
        "clip": "CHAR_EP1_B3_MECHANISM_01", "mstart": 0.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "whip_tilt_v", "sfx": "whip_tilt_riser",
    },
    {
        "start": 18.60, "end": 21.20,
        "clip": "CHAR_EP1_B3_MECHANISM_01", "mstart": 3.00,
        "scale": 1.38, "focus": (0.50, 0.48),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },

    # --- BEAT 3 (21.20s - 37.12s): Hidden Mechanism ("ตาล้าตอนดึก / แสงจอหลอกสมอง / กดสมองส่วนตัดสินใจ") ---
    {
        "start": 21.20, "end": 23.94,
        "clip": "CHAR_EP1_B2_MISTAKE_01", "mstart": 3.20,
        "scale": 1.24, "focus": (0.50, 0.48),
        "trans": "prism_shatter", "sfx": "prism_shatter_sfx",
    },
    {
        "start": 23.94, "end": 26.68,
        "clip": "CHAR_EP1_B1_HOOK_01", "mstart": 3.20,
        "scale": 1.36, "focus": (0.52, 0.44),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    {
        "start": 26.68, "end": 29.32,
        "clip": "CHAR_EP1_B3_MECHANISM_02", "mstart": 1.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    {
        "start": 29.32, "end": 31.96,
        "clip": "CHAR_EP1_B3_MECHANISM_01", "mstart": 2.40,
        "scale": 1.38, "focus": (0.50, 0.48),
        "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz",
    },
    {
        "start": 31.96, "end": 34.54,
        "clip": "CHAR_EP1_B4_CONSEQUENCE_01", "mstart": 0.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "neg_shockwave", "sfx": "neg_shockwave_zap",
    },
    {
        "start": 34.54, "end": 37.12,
        "clip": "CHAR_EP1_B4_CONSEQUENCE_01", "mstart": 3.00,
        "scale": 1.38, "focus": (0.50, 0.44),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },

    # --- BEAT 4 (37.12s - 48.40s): Mechanism Pivot ("จัดแสงโต๊ะ + ใส่ผ้าปิดตาตัดแสงทันที") ---
    {
        "start": 37.12, "end": 39.68,
        "clip": "CHAR_EP1_B5_LESSON_METHOD_01", "mstart": 0.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "gravity_flip", "sfx": "gravity_flip_swoop",
    },
    {
        "start": 39.68, "end": 42.24,
        "clip": "CHAR_EP1_B5_LESSON_METHOD_02", "mstart": 0.40,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    {
        "start": 42.24, "end": 45.00,
        "clip": "CHAR_EP1_B5_LESSON_METHOD_01", "mstart": 3.00,
        "scale": 1.36, "focus": (0.50, 0.42),
        "trans": "prism_shatter", "sfx": "prism_shatter_sfx",
    },
    {
        "start": 45.00, "end": 48.40,
        "clip": "CHAR_EP1_B6_DISCIPLINE_FIX_01", "mstart": 0.20,
        "scale": 1.00, "focus": (0.50, 0.50),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    },

    # --- BEAT 5 (48.40s - 53.12s): Friction Removal ("แค่ตัดแสงกวนตาตอนนอนให้มืดสนิท") ---
    {
        "start": 48.40, "end": 50.76,
        "clip": "CHAR_EP1_B6_DISCIPLINE_FIX_01", "mstart": 2.40,
        "scale": 1.38, "focus": (0.50, 0.62),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    {
        "start": 50.76, "end": 53.12,
        "clip": "CHAR_EP1_B5_LESSON_METHOD_02", "mstart": 2.80,
        "scale": 1.34, "focus": (0.50, 0.46),
        "trans": "whip_tilt_v", "sfx": "whip_tilt_riser",
    },

    # --- BEAT 6 (53.12s - 65.44s): Pain Callback + Smart-Value CTA ---
    {
        "start": 53.12, "end": 55.60,
        "clip": "CHAR_EP1_B2_MISTAKE_02", "mstart": 2.40,
        "scale": 1.24, "focus": (0.50, 0.45),
        "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz",
    },
    {
        "start": 55.60, "end": 58.08,
        "clip": "CHAR_EP1_B1_HOOK_01", "mstart": 4.20,
        "scale": 1.26, "focus": (0.50, 0.45),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    {
        "start": 58.08, "end": 62.16,
        "clip": "CHAR_EP1_B6_DISCIPLINE_FIX_01", "mstart": 0.60,
        "scale": 1.12, "focus": (0.50, 0.54),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    },
    {
        "start": 62.16, "end": 65.44,
        "clip": "CHAR_EP1_B6_DISCIPLINE_FIX_01", "mstart": 3.60,
        "scale": 1.38, "focus": (0.50, 0.58),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
]

# Interactive Red Callout Boxes (t_in, t_out, x, y, w, h, label)
CALLOUT_BOXES = [
    (3.75, 5.15, 290, 560, 480, 440, "02:00 AM · สมองล้า"),
    (37.35, 39.55, 260, 520, 520, 460, "จัดแสงโต๊ะ + พักสายตา"),
    (58.30, 61.85, 260, 540, 520, 460, "ผ้าปิดตา 3D · ตัดแสง 100%"),
]


# ============================================================================
# 2. VIDEO FRAME LOADER & CROP/ZOOM ENGINE
# ============================================================================
class ClipCache:
    def __init__(self, broll_dir: Path):
        self.broll_dir = broll_dir
        self.cache: Dict[str, List[np.ndarray]] = {}

    def get_frames(self, clip_id: str) -> List[np.ndarray]:
        if clip_id in self.cache:
            return self.cache[clip_id]
        path = self.broll_dir / f"{clip_id}.mp4"
        if not path.exists():
            # Fallback to any available CHAR_EP1_*.mp4 if one is missing
            avail = sorted(self.broll_dir.glob("CHAR_EP1_*.mp4"))
            if not avail:
                raise FileNotFoundError(f"No CHAR_EP1_*.mp4 found in {self.broll_dir}")
            path = avail[0]
            print(f"[warn] {clip_id}.mp4 missing, falling back to {path.name}")
        cap = cv2.VideoCapture(str(path))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        raw_frames: List[np.ndarray] = []
        while True:
            ok, frm = cap.read()
            if not ok:
                break
            if frm.shape[1] != WIDTH or frm.shape[0] != HEIGHT:
                frm = cv2.resize(frm, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
            raw_frames.append(frm)
        cap.release()
        if not raw_frames:
            raise RuntimeError(f"Zero frames decoded from {path}")
        # Resample to target FPS (30 fps)
        dur = len(raw_frames) / src_fps
        n_out = max(1, int(round(dur * FPS)))
        resampled: List[np.ndarray] = []
        for i in range(n_out):
            t = i / FPS
            src_idx = min(len(raw_frames) - 1, int(round(t * src_fps)))
            resampled.append(raw_frames[src_idx])
        self.cache[clip_id] = resampled
        return resampled


def sample_cropped_frame(
    frames: List[np.ndarray],
    media_t: float,
    scale: float,
    focus_xy: Tuple[float, float],
) -> np.ndarray:
    idx = int(round(media_t * FPS)) % len(frames)
    frm = frames[idx]
    if scale <= 1.001:
        return frm.copy()
    crop_w = int(round(WIDTH / scale))
    crop_h = int(round(HEIGHT / scale))
    cx = int(round(focus_xy[0] * WIDTH))
    cy = int(round(focus_xy[1] * HEIGHT))
    x0 = max(0, min(WIDTH - crop_w, cx - crop_w // 2))
    y0 = max(0, min(HEIGHT - crop_h, cy - crop_h // 2))
    cropped = frm[y0 : y0 + crop_h, x0 : x0 + crop_w]
    return cv2.resize(cropped, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)


# ============================================================================
# 3. 8 VARIED TRANSITION MOTION SHADERS (OpenCV / NumPy)
# ============================================================================
def directional_blur(img: np.ndarray, ksize: int, horizontal: bool = True) -> np.ndarray:
    k = max(3, int(ksize) | 1)
    if horizontal:
        return cv2.blur(img, (k, 1))
    return cv2.blur(img, (1, k))


def apply_transition_effect(
    prev_frm: np.ndarray,
    curr_frm: np.ndarray,
    trans_type: str,
    rel_t: float,
) -> np.ndarray:
    """
    Apply transition motion across the cut boundary where `rel_t` is time since cut start (seconds).
    Also we pre-transition the last 0.08s of the outgoing segment in the main render loop.
    Here `rel_t` is normalized progress `p in [0.0, 1.0]` across the transition window.
    """
    p = max(0.0, min(1.0, rel_t))
    # Smooth ease-out cubic
    ease = 1.0 - (1.0 - p) ** 3

    if trans_type == "hook_punch":
        # Fast punch-in zoom from 1.18x -> 1.0x with subtle top-frame red flash
        z = 1.18 - 0.18 * ease
        out = sample_cropped_frame([curr_frm], 0.0, z, (0.5, 0.45))
        flash = max(0.0, 1.0 - p * 2.2) * 0.35
        if flash > 0:
            overlay = np.zeros_like(out)
            overlay[:, :] = (35, 30, 240)  # BGR red-white bloom
            out = cv2.addWeighted(out, 1.0, overlay, flash, 0)
        return out

    if trans_type == "whip_pan_h":
        # Horizontal whip-pan slide + heavy horizontal motion blur (boxblur 55x1)
        if p < 0.45:
            q = p / 0.45
            shift = int(round(q * WIDTH * 0.65))
            rolled = np.roll(prev_frm, -shift, axis=1)
            return directional_blur(rolled, int(15 + 65 * q), horizontal=True)
        else:
            q = (p - 0.45) / 0.55
            inv = 1.0 - (1.0 - q) ** 3
            shift = int(round((1.0 - inv) * WIDTH * 0.65))
            rolled = np.roll(curr_frm, shift, axis=1)
            blur_k = int(1 + 65 * (1.0 - inv))
            return directional_blur(rolled, blur_k, horizontal=True) if blur_k >= 3 else rolled

    if trans_type == "whip_tilt_v":
        # Vertical speed-warp whip-tilt + vertical streak blur + midpoint brightness bloom
        if p < 0.45:
            q = p / 0.45
            shift = int(round(q * HEIGHT * 0.55))
            rolled = np.roll(prev_frm, -shift, axis=0)
            blurred = directional_blur(rolled, int(15 + 75 * q), horizontal=False)
        else:
            q = (p - 0.45) / 0.55
            inv = 1.0 - (1.0 - q) ** 3
            shift = int(round((1.0 - inv) * HEIGHT * 0.55))
            rolled = np.roll(curr_frm, shift, axis=0)
            blur_k = int(1 + 75 * (1.0 - inv))
            blurred = directional_blur(rolled, blur_k, horizontal=False) if blur_k >= 3 else rolled
        bloom = math.sin(p * math.pi) * 55.0
        return np.clip(blurred.astype(np.float32) + bloom, 0, 255).astype(np.uint8)

    if trans_type == "scale_punch":
        # Instant 1.38x jump-zoom cut-in with a 0.08s radial zoom burst + subtle brightness pop
        z = 1.08 - 0.08 * ease
        out = sample_cropped_frame([curr_frm], 0.0, z, (0.5, 0.45))
        pop = max(0.0, 1.0 - p * 2.5) * 32.0
        return np.clip(out.astype(np.float32) + pop, 0, 255).astype(np.uint8)

    if trans_type == "exposure_flash":
        # Exposure flash pop (+45% brightness bloom + warm red-white highlight)
        base = prev_frm if p < 0.35 else curr_frm
        peak = math.sin(p * math.pi)
        f = base.astype(np.float32) * (1.0 + 0.55 * peak)
        f[:, :, 2] += 75.0 * peak  # Red channel boost
        f[:, :, 1] += 45.0 * peak
        f[:, :, 0] += 45.0 * peak
        return np.clip(f, 0, 255).astype(np.uint8)

    if trans_type == "neg_shockwave":
        # Chromatic Negative Shockwave (electric cyan/ultraviolet color inversion on crash/pain beats)
        base = curr_frm.copy()
        if 0.10 <= p <= 0.78:
            inv = 255 - base
            # Boost electric cyan/blue & magenta tint like @lungtepuniverse t=42.72s
            inv_f = inv.astype(np.float32)
            inv_f[:, :, 0] = np.clip(inv_f[:, :, 0] * 1.25 + 30, 0, 255)  # Blue/Cyan
            inv_f[:, :, 1] = np.clip(inv_f[:, :, 1] * 1.10 + 15, 0, 255)
            alpha = math.sin(((p - 0.10) / 0.68) * math.pi)
            out = cv2.addWeighted(base, 1.0 - alpha * 0.88, inv_f.astype(np.uint8), alpha * 0.88, 0)
            return out
        return base

    if trans_type == "prism_shatter":
        # Diagonal glass/prism shard split sliding apart over incoming scene
        out = curr_frm.copy()
        if p < 0.85:
            q = p / 0.85
            yy, xx = np.meshgrid(np.arange(HEIGHT), np.arange(WIDTH), indexing="ij")
            diag = (xx * HEIGHT + yy * WIDTH) > (WIDTH * HEIGHT)
            dx = int(round(q * 260))
            dy = int(round(q * 340))
            shard1 = np.roll(np.roll(prev_frm, -dx, axis=1), -dy, axis=0)
            shard2 = np.roll(np.roll(prev_frm, dx, axis=1), dy, axis=0)
            comp = np.where(diag[:, :, None], shard2, shard1)
            alpha = 1.0 - q ** 1.6
            out = cv2.addWeighted(out, 1.0 - alpha, comp, alpha, 0)
            # Draw glowing diagonal prism seam
            seam = np.abs((xx * HEIGHT + yy * WIDTH) - (WIDTH * HEIGHT)) < (WIDTH * 18)
            out[seam] = np.clip(out[seam].astype(np.int32) + np.array([90, 90, 220]), 0, 255).astype(np.uint8)
        return out

    if trans_type == "gravity_flip":
        # 180-degree vertical flip whip (like @lungtepuniverse t=44.93s)
        if p < 0.55:
            flipped = cv2.flip(prev_frm, 0)
            return directional_blur(flipped, 35, horizontal=False)
        else:
            q = (p - 0.55) / 0.45
            blur_k = int(1 + 35 * (1.0 - q))
            return directional_blur(curr_frm, blur_k, horizontal=False) if blur_k >= 3 else curr_frm

    if trans_type == "rgb_glitch":
        # RGB Chromatic Glitch Split + horizontal slice displacement
        base = curr_frm.copy()
        shift = int(round(math.sin(p * math.pi) * 42))
        if shift > 0:
            b, g, r = cv2.split(base)
            r_sh = np.roll(r, shift, axis=1)
            b_sh = np.roll(b, -shift, axis=1)
            base = cv2.merge([b_sh, g, r_sh])
            # Horizontal glitch bars
            for bar_y in (360, 720, 1080, 1440):
                bar_Shift = shift * (2 if (bar_y // 360) % 2 == 0 else -2)
                base[bar_y : bar_y + 48, :] = np.roll(base[bar_y : bar_y + 48, :], bar_Shift, axis=1)
        return base

    return curr_frm


def render_v4_plate_track(out_mp4: Path) -> None:
    print(f"[v4_plate] Loading Character-in-Scene clips from {BROLL_DIR}…", flush=True)
    cache = ClipCache(BROLL_DIR)

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    # Pre-map each frame index to its segment index
    seg_for_frame: List[int] = [0] * TOTAL_FRAMES
    for s_idx, seg in enumerate(CUT_SCHEDULE):
        f0 = max(0, int(round(float(seg["start"]) * FPS)))
        f1 = min(TOTAL_FRAMES, int(round(float(seg["end"]) * FPS)))
        for f in range(f0, f1):
            seg_for_frame[f] = s_idx

    def raw_seg_frame(s_idx: int, global_t: float) -> np.ndarray:
        seg = CUT_SCHEDULE[s_idx]
        frames = cache.get_frames(str(seg["clip"]))
        local_t = max(0.0, global_t - float(seg["start"]))
        media_t = float(seg["mstart"]) + local_t
        base_scale = float(seg["scale"])
        # Subtle living camera push (+4% over the cut) so no frame is ever frozen
        live_scale = base_scale * (1.0 + 0.018 * min(local_t, 3.0))
        return sample_cropped_frame(frames, media_t, live_scale, tuple(seg["focus"]))

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        s_idx = seg_for_frame[f_idx]
        seg = CUT_SCHEDULE[s_idx]
        seg_start = float(seg["start"])
        trans_type = str(seg["trans"])

        curr_frm = raw_seg_frame(s_idx, t)

        # Transition durations per type
        trans_dur = {
            "hook_punch": 0.22,
            "whip_pan_h": 0.18,
            "whip_tilt_v": 0.18,
            "scale_punch": 0.12,
            "exposure_flash": 0.16,
            "neg_shockwave": 0.24,
            "prism_shatter": 0.20,
            "gravity_flip": 0.18,
            "rgb_glitch": 0.18,
        }.get(trans_type, 0.16)

        dt = t - seg_start
        if 0.0 <= dt < trans_dur:
            prev_frm = raw_seg_frame(max(0, s_idx - 1), t) if s_idx > 0 else curr_frm
            rel_p = dt / trans_dur
            frm = apply_transition_effect(prev_frm, curr_frm, trans_type, rel_p)
        else:
            frm = curr_frm

        assert proc.stdin is not None
        proc.stdin.write(frm.tobytes())

    assert proc.stdin is not None
    proc.stdin.close()
    proc.wait()
    print(f"[v4_plate] Rendered {out_mp4} ({out_mp4.stat().st_size:,} bytes, {TOTAL_FRAMES} frames)", flush=True)


# ============================================================================
# 4. STUDIO MULTI-LAYER TRANSITION & HOOK SFX SYNTHESIZER (48 kHz Stereo)
# ============================================================================
def make_sfx_event(kind: str) -> np.ndarray:
    """Synthesize a stereo 48kHz float32 SFX array shape (N, 2) matching @lungtepuniverse's spectral profile."""
    rng = np.random.default_rng(abs(hash(kind)) % (2**32))

    if kind == "sub_shutter_hit":
        # 0.24s: 90Hz -> 36Hz sub punch + 3,550Hz camera shutter double-snap
        n = int(0.24 * SR)
        t = np.linspace(0, 0.24, n, endpoint=False)
        freq = 90.0 * np.exp(-t * 10.0) + 34.0
        phase = 2 * np.pi * np.cumsum(freq) / SR
        sub = np.tanh(np.sin(phase) * 2.2) * np.exp(-t * 11.0) * 0.75
        # High shutter snap at t=0.00 and t=0.028
        noise = rng.standard_normal(n)
        snap_env = np.exp(-t * 95.0) + 0.65 * np.exp(-np.maximum(0, t - 0.028) * 110.0) * (t >= 0.028)
        carrier = np.sin(2 * np.pi * 3550.0 * t) + 0.5 * np.sin(2 * np.pi * 5100.0 * t)
        snap = noise * carrier * snap_env * 0.55
        sig = sub + snap
        return np.column_stack([sig, sig * 0.96]).astype(np.float32)

    if kind == "whip_whoosh":
        # 0.20s: Stereo-panned resonant whip-whoosh (350Hz -> 3600Hz -> 450Hz) + 115Hz midpoint thump
        n = int(0.20 * SR)
        t = np.linspace(0, 0.20, n, endpoint=False)
        env = np.sin(np.pi * (t / 0.20)) ** 1.4
        f_sweep = 380.0 + 3200.0 * (np.sin(np.pi * (t / 0.20)) ** 1.8)
        phase = 2 * np.pi * np.cumsum(f_sweep) / SR
        noise = rng.standard_normal(n)
        # Moving average smoothing + modulated sweep
        whoosh = (0.55 * noise * np.cos(phase) + 0.45 * np.sin(phase)) * env * 0.52
        # Midpoint low thump
        thump = np.sin(2 * np.pi * 115.0 * t) * np.exp(-((t - 0.09) ** 2) / (2 * 0.028**2)) * 0.58
        pan = np.linspace(0.25, 0.85, n)
        left = (whoosh + thump) * np.sqrt(1.0 - pan)
        right = (whoosh + thump) * np.sqrt(pan)
        return np.column_stack([left, right]).astype(np.float32)

    if kind == "shutter_pop":
        # 0.12s: Crisp camera aperture pop (950Hz->180Hz pop + 4,700Hz crisp click)
        n = int(0.12 * SR)
        t = np.linspace(0, 0.12, n, endpoint=False)
        f_pop = 920.0 * np.exp(-t * 48.0) + 160.0
        pop = np.sin(2 * np.pi * np.cumsum(f_pop) / SR) * np.exp(-t * 36.0) * 0.65
        click = rng.standard_normal(n) * np.sin(2 * np.pi * 4700.0 * t) * np.exp(-t * 140.0) * 0.48
        sig = pop + click
        return np.column_stack([sig, sig]).astype(np.float32)

    if kind == "swish_tom":
        # 0.18s: Fast air swish + 145Hz->62Hz punchy low tom
        n = int(0.18 * SR)
        t = np.linspace(0, 0.18, n, endpoint=False)
        f_tom = 145.0 * np.exp(-t * 16.0) + 58.0
        tom = np.tanh(np.sin(2 * np.pi * np.cumsum(f_tom) / SR) * 1.8) * np.exp(-t * 16.0) * 0.68
        swish = rng.standard_normal(n) * np.sin(2 * np.pi * 3100.0 * t) * np.sin(np.pi * t / 0.18) * 0.38
        sig = tom + swish
        return np.column_stack([sig * 0.95, sig * 1.05]).astype(np.float32)

    if kind == "rgb_glitch_buzz":
        # 0.16s: 3-burst digital FM glitch + micro-whoosh (4,024Hz centroid)
        n = int(0.16 * SR)
        t = np.linspace(0, 0.16, n, endpoint=False)
        gate = ((np.sin(2 * np.pi * 28.0 * t) > -0.15).astype(np.float32)) * np.exp(-t * 9.0)
        fm = np.sign(np.sin(2 * np.pi * 1950.0 * t + 4.0 * np.sin(2 * np.pi * 320.0 * t)))
        hi = np.sin(2 * np.pi * 4150.0 * t) * rng.standard_normal(n)
        sig = (0.42 * fm + 0.45 * hi) * gate * 0.48
        return np.column_stack([sig, np.roll(sig, 180)]).astype(np.float32)

    if kind == "riser_build":
        # 1.05s tension riser (2.50s -> 3.55s): initial pop + pitch-rising shimmer sweep
        n = int(1.05 * SR)
        t = np.linspace(0, 1.05, n, endpoint=False)
        # Initial pop at 2.50s
        f_pop = 850.0 * np.exp(-t * 45.0) + 150.0
        pop = np.sin(2 * np.pi * np.cumsum(f_pop) / SR) * np.exp(-t * 35.0) * 0.55
        # Rising sweep 280Hz -> 4,600Hz
        env = (t / 1.05) ** 2.2
        f_rise = 280.0 * (16.0 ** (t / 1.05))
        phase = 2 * np.pi * np.cumsum(f_rise) / SR
        riser = (0.5 * np.sin(phase) + 0.5 * rng.standard_normal(n) * np.cos(phase)) * env * 0.58
        sig = pop + riser
        pan = 0.5 + 0.35 * np.sin(2 * np.pi * 3.0 * t)
        return np.column_stack([sig * np.sqrt(1 - pan), sig * np.sqrt(pan)]).astype(np.float32)

    if kind == "sub_drop_flash":
        # 0.48s: Massive 98Hz->32Hz sub-bass drop + bright crystal flash shimmer
        n = int(0.48 * SR)
        t = np.linspace(0, 0.48, n, endpoint=False)
        f_sub = 98.0 * np.exp(-t * 9.5) + 32.0
        sub = np.tanh(np.sin(2 * np.pi * np.cumsum(f_sub) / SR) * 2.5) * np.exp(-t * 5.8) * 0.85
        shimmer = (
            np.sin(2 * np.pi * 3400.0 * t)
            + 0.7 * np.sin(2 * np.pi * 5100.0 * t)
            + 0.4 * rng.standard_normal(n)
        ) * np.exp(-t * 18.0) * 0.38
        sig = sub + shimmer
        return np.column_stack([sig, sig]).astype(np.float32)

    if kind == "neg_shockwave_zap":
        # 0.30s: Electric plasma zap + heavy sub shockwave (for chromatic negative inversion)
        n = int(0.30 * SR)
        t = np.linspace(0, 0.30, n, endpoint=False)
        f_sub = 82.0 * np.exp(-t * 11.0) + 34.0
        sub = np.tanh(np.sin(2 * np.pi * np.cumsum(f_sub) / SR) * 2.2) * np.exp(-t * 8.0) * 0.78
        f_zap = 3800.0 * np.exp(-t * 18.0) + 420.0
        zap = np.tanh(np.sin(2 * np.pi * np.cumsum(f_zap) / SR + 3.0 * np.sin(2 * np.pi * 95.0 * t)) * 1.9)
        zap = zap * np.exp(-t * 14.0) * 0.42
        sig = sub + zap
        return np.column_stack([sig, np.roll(sig, 120)]).astype(np.float32)

    if kind == "whip_tilt_riser":
        # 0.20s: Fast upward Doppler speed-whoosh + tight lock-in thud
        n = int(0.20 * SR)
        t = np.linspace(0, 0.20, n, endpoint=False)
        env = np.sin(np.pi * (t / 0.20)) ** 1.3
        f_sw = 420.0 + 3800.0 * ((t / 0.20) ** 1.7)
        sw = (0.6 * np.sin(2 * np.pi * np.cumsum(f_sw) / SR) + 0.4 * rng.standard_normal(n)) * env * 0.50
        thud = np.sin(2 * np.pi * 125.0 * t) * np.exp(-((t - 0.14) ** 2) / (2 * 0.022**2)) * 0.55
        sig = sw + thud
        return np.column_stack([sig, sig]).astype(np.float32)

    if kind == "prism_shatter_sfx":
        # 0.24s: High-frequency crystalline prism chime/shatter + fast air whoosh
        n = int(0.24 * SR)
        t = np.linspace(0, 0.24, n, endpoint=False)
        chime = (
            np.sin(2 * np.pi * 3180.0 * t) * np.exp(-t * 22.0)
            + 0.8 * np.sin(2 * np.pi * 4720.0 * np.maximum(0, t - 0.018)) * np.exp(-np.maximum(0, t - 0.018) * 26.0)
            + 0.6 * np.sin(2 * np.pi * 6350.0 * np.maximum(0, t - 0.036)) * np.exp(-np.maximum(0, t - 0.036) * 30.0)
        ) * 0.36
        whoosh = rng.standard_normal(n) * np.sin(np.pi * t / 0.24) * np.exp(-t * 14.0) * 0.32
        sig = chime + whoosh
        return np.column_stack([sig, np.roll(sig, 90)]).astype(np.float32)

    if kind == "gravity_flip_swoop":
        # 0.18s: Reverse-suction swoop ending in a crisp snap
        n = int(0.18 * SR)
        t = np.linspace(0, 0.18, n, endpoint=False)
        env = ((t / 0.18) ** 2.4) * np.exp(-np.maximum(0, t - 0.14) * 90.0)
        f_sw = 520.0 + 2600.0 * ((t / 0.18) ** 2.0)
        sig = (0.65 * np.sin(2 * np.pi * np.cumsum(f_sw) / SR) + 0.35 * rng.standard_normal(n)) * env * 0.65
        return np.column_stack([sig, sig]).astype(np.float32)

    if kind == "ui_click_ding":
        # 0.26s: Crisp UI click + clean two-tone bell chime (for Red Callout Box)
        n = int(0.26 * SR)
        t = np.linspace(0, 0.26, n, endpoint=False)
        click = np.sin(2 * np.pi * 3900.0 * t) * np.exp(-t * 180.0) * 0.55
        t2 = np.maximum(0.0, t - 0.025)
        mask = (t >= 0.025).astype(np.float32)
        ding = (
            np.sin(2 * np.pi * 1760.0 * t2) * np.exp(-t2 * 16.0)
            + 0.65 * np.sin(2 * np.pi * 2637.0 * t2) * np.exp(-t2 * 22.0)
        ) * mask * 0.42
        sig = click + ding
        return np.column_stack([sig, sig]).astype(np.float32)

    return np.zeros((int(0.1 * SR), 2), dtype=np.float32)


def build_v4_audio_master(voice_wav: Path, out_wav: Path) -> None:
    """Mix existing voice + ambient track with the synced Hook & Transition SFX bus and normalize to -14.0 LUFS."""
    tmp_f32 = out_wav.parent / "_tmp_voice_48k.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(voice_wav), "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(tmp_f32)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with wave.open(str(tmp_f32), "rb") as wf:
        n_frames = wf.getnframes()
        raw = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0
        base = raw.reshape(-1, 2)
    tmp_f32.unlink(missing_ok=True)

    target_len = int(round(TOTAL_DUR * SR))
    if len(base) < target_len:
        pad = np.zeros((target_len - len(base), 2), dtype=np.float32)
        base = np.vstack([base, pad])
    else:
        base = base[:target_len]

    sfx_bus = np.zeros_like(base)

    def place_sfx(at_s: float, kind: str, gain_db: float = 0.0) -> None:
        arr = make_sfx_event(kind)
        gain = 10.0 ** (gain_db / 20.0)
        idx0 = max(0, int(round(at_s * SR)))
        idx1 = min(len(sfx_bus), idx0 + len(arr))
        if idx1 > idx0:
            sfx_bus[idx0:idx1] += arr[: idx1 - idx0] * gain

    # 1. Place Hook + Body Transition SFX at every cut timestamp
    for seg in CUT_SCHEDULE:
        at_s = float(seg["start"])
        sfx_kind = str(seg["sfx"])
        # Hook cuts (0.00 - 3.55s) sit slightly hotter (-1.0 dB) for maximum thumb-stop punch;
        # body transitions sit at -3.5 dB so they never mask the spoken Thai voice!
        gain_db = -0.5 if at_s <= 3.60 else -3.5
        place_sfx(at_s, sfx_kind, gain_db=gain_db)

    # 2. Place UI Click + Ding SFX at every Interactive Red Callout Box
    for t_in, _, _, _, _, _, _ in CALLOUT_BOXES:
        place_sfx(t_in, "ui_click_ding", gain_db=-4.0)

    mixed = np.clip(base + sfx_bus * 0.52, -0.98, 0.98)
    raw_mix_wav = out_wav.parent / "_tmp_v4_pre_lufs.wav"
    pcm16 = (mixed * 32767.0).astype(np.int16)
    with wave.open(str(raw_mix_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm16.tobytes())

    # Loudness-normalize to -14.0 LUFS, TP -1.5 dBTP
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(raw_mix_wav),
            "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=11",
            "-ar", str(SR),
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(out_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    raw_mix_wav.unlink(missing_ok=True)
    print(f"[v4_audio] Built {out_wav} ({out_wav.stat().st_size:,} bytes, -14.0 LUFS + 33 synced SFX events)", flush=True)


# ============================================================================
# 5. UPDATE HYPERFRAMES index.html WITH V4 PLATE, AUDIO, AND RED CALLOUT BOXES
# ============================================================================
def update_index_html_v4(index_path: Path, plate_rel: str, audio_rel: str, dur: float, is_fast: bool = False) -> None:
    html = index_path.read_text(encoding="utf-8")

    # 1. Add .plate-clear, .bl-callout, and dark glass backing on .bl-rulecard
    callout_css = """
      .plate-clear { filter: brightness(.84) contrast(1.08) saturate(1.06); }
      .bl-rulecard { background: rgba(7,8,10,.78); border: 2px solid var(--line);
                     border-left: 10px solid var(--neon); border-radius: 22px;
                     padding: 26px 30px; box-shadow: 0 22px 50px rgba(0,0,0,.55); }
      .bl-callout { position: absolute; z-index: 28; pointer-events: none; opacity: 0;
                    border: 4px solid var(--neon); border-radius: 16px;
                    box-shadow: 0 0 24px rgba(255,45,64,.75), inset 0 0 18px rgba(255,45,64,.22); }
      .bl-callout .tag { position: absolute; left: -4px; top: -48px;
                         background: var(--red); color: #fff; font-weight: 800; font-size: 26px;
                         padding: 5px 16px; border-radius: 10px 10px 10px 2px;
                         white-space: nowrap; box-shadow: var(--glow-s); letter-spacing: .02em; }
      .bl-callout .ptr { position: absolute; right: -26px; bottom: -32px;
                         font-size: 46px; filter: drop-shadow(0 4px 10px rgba(0,0,0,.9)); }
"""
    if ".bl-callout" not in html:
        html = html.replace(
            ".plate-dim { filter: brightness(.42) contrast(1.08) saturate(.92); }",
            ".plate-dim { filter: brightness(.42) contrast(1.08) saturate(.92); }\n" + callout_css,
        )
    elif ".bl-rulecard {" not in html:
        html = html.replace(
            ".plate-clear { filter: brightness(.84) contrast(1.08) saturate(1.06); }",
            ".plate-clear { filter: brightness(.84) contrast(1.08) saturate(1.06); }\n"
            "      .bl-rulecard { background: rgba(7,8,10,.78); border: 2px solid var(--line); "
            "border-left: 10px solid var(--neon); border-radius: 22px; padding: 26px 30px; "
            "box-shadow: 0 22px 50px rgba(0,0,0,.55); }",
        )

    # 2. Replace all <video class="clip"...> and <audio id="va"...>
    import re

    new_media_block = (
        f'      <video class="clip plate-clear" id="v1" src="{plate_rel}" muted playsinline '
        f'data-start="0.00" data-duration="{dur:.2f}" data-media-start="0.00" data-track-index="0"></video>\n'
        f'      <audio id="va" src="{audio_rel}" data-start="0" data-duration="{dur:.2f}" '
        f'data-track-index="5" data-volume="1"></audio>'
    )
    html = re.sub(
        r'(\s*<video class="clip[^\n]+\n)+(\s*<audio id="va"[^\n]+)',
        "\n" + new_media_block,
        html,
    )

    # 3. Inject or update calloutBox() calls
    if is_fast:
        calls = (
            '      calloutBox(0.55, 3.45, 250, 440, 480, 400, "02:00 AM · ใช้สมองผิดเวลา");\n'
            '      calloutBox(30.40, 33.75, 220, 360, 540, 300, "จัดแสงโต๊ะ + พักสายตา");\n'
            '      calloutBox(47.45, 50.30, 220, 760, 460, 280, "ผ้าปิดตา 3D · ตัดแสง 100%");'
        )
    else:
        calls = (
            '      calloutBox(0.55, 3.45, 250, 440, 480, 400, "02:00 AM · ใช้สมองผิดเวลา");\n'
            '      calloutBox(37.35, 42.05, 220, 360, 540, 300, "จัดแสงโต๊ะ + พักสายตา");\n'
            '      calloutBox(58.30, 61.95, 220, 760, 460, 280, "ผ้าปิดตา 3D · ตัดแสง 100%");'
        )

    callout_js = (
        """
      var CALLN = 0;
      function calloutBox(at, out, x, y, w, h, label) {
        var id = "cbox" + (++CALLN);
        var node = el('<div class="bl-callout" id="' + id + '" style="left:' + x + 'px;top:' + y +
          'px;width:' + w + 'px;height:' + h + 'px"><div class="tag">' + label +
          '</div><div class="ptr">↖</div></div>');
        stage.appendChild(node);
        tl.fromTo("#" + id, { opacity: 0, scale: 1.18 },
          { opacity: 1, scale: 1.0, duration: 0.22, ease: "back.out(1.8)", transformOrigin: "50% 50%" }, at);
        hide("#" + id, out);
      }
"""
        + calls
        + "\n"
    )
    if "function calloutBox" not in html:
        html = html.replace(
            'tl.set("#bug", { x: 0, opacity: 1 }, 0);',
            'tl.set("#bug", { x: 0, opacity: 1 }, 0);\n' + callout_js,
        )
    else:
        html = re.sub(
            r'(\s*calloutBox\([^\n]+\n)+',
            "\n" + calls + "\n",
            html,
        )

    index_path.write_text(html, encoding="utf-8")
    print(f"[v4_html] Updated {index_path}", flush=True)


def scale_schedule_for_duration(target_dur: float) -> List[Dict[str, object]]:
    """Keep the 0.00 - 3.55s Hook identical and scale body cuts (3.55s - 65.44s) to `target_dur`."""
    if abs(target_dur - TOTAL_DUR) < 0.05:
        return [dict(s) for s in CUT_SCHEDULE]
    out: List[Dict[str, object]] = []
    ratio = (target_dur - 3.55) / (TOTAL_DUR - 3.55)
    for s in CUT_SCHEDULE:
        d = dict(s)
        st = float(d["start"])
        en = float(d["end"])
        if en <= 3.551:
            out.append(d)
        else:
            d["start"] = round(3.55 + max(0.0, st - 3.55) * ratio, 2)
            d["end"] = round(3.55 + (en - 3.55) * ratio, 2)
            out.append(d)
    out[-1]["end"] = target_dur
    return out


def render_v4_plate_track_scheduled(out_mp4: Path, schedule: List[Dict[str, object]], dur: float) -> None:
    print(f"[v4_plate] Rendering {out_mp4.name} (dur={dur}s) from {BROLL_DIR}…", flush=True)
    cache = ClipCache(BROLL_DIR)
    n_frames = int(round(dur * FPS))

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    seg_for_frame: List[int] = [0] * n_frames
    for s_idx, seg in enumerate(schedule):
        f0 = max(0, int(round(float(seg["start"]) * FPS)))
        f1 = min(n_frames, int(round(float(seg["end"]) * FPS)))
        for f in range(f0, f1):
            seg_for_frame[f] = s_idx

    def raw_seg_frame(s_idx: int, global_t: float) -> np.ndarray:
        seg = schedule[s_idx]
        frames = cache.get_frames(str(seg["clip"]))
        local_t = max(0.0, global_t - float(seg["start"]))
        media_t = float(seg["mstart"]) + local_t
        base_scale = float(seg["scale"])
        live_scale = base_scale * (1.0 + 0.018 * min(local_t, 3.0))
        return sample_cropped_frame(frames, media_t, live_scale, tuple(seg["focus"]))

    for f_idx in range(n_frames):
        t = f_idx / FPS
        s_idx = seg_for_frame[f_idx]
        seg = schedule[s_idx]
        seg_start = float(seg["start"])
        trans_type = str(seg["trans"])

        curr_frm = raw_seg_frame(s_idx, t)
        trans_dur = {
            "hook_punch": 0.22,
            "whip_pan_h": 0.18,
            "whip_tilt_v": 0.18,
            "scale_punch": 0.12,
            "exposure_flash": 0.16,
            "neg_shockwave": 0.24,
            "prism_shatter": 0.20,
            "gravity_flip": 0.18,
            "rgb_glitch": 0.18,
        }.get(trans_type, 0.16)

        dt = t - seg_start
        if 0.0 <= dt < trans_dur:
            prev_frm = raw_seg_frame(max(0, s_idx - 1), t) if s_idx > 0 else curr_frm
            rel_p = dt / trans_dur
            frm = apply_transition_effect(prev_frm, curr_frm, trans_type, rel_p)
        else:
            frm = curr_frm

        assert proc.stdin is not None
        proc.stdin.write(frm.tobytes())

    assert proc.stdin is not None
    proc.stdin.close()
    proc.wait()
    print(f"[v4_plate] Rendered {out_mp4} ({out_mp4.stat().st_size:,} bytes, {n_frames} frames)", flush=True)


def build_v4_audio_master_scheduled(
    voice_wav: Path,
    out_wav: Path,
    schedule: List[Dict[str, object]],
    callouts: List[float],
    dur: float,
) -> None:
    tmp_f32 = out_wav.parent / "_tmp_voice_48k.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(voice_wav), "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(tmp_f32)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with wave.open(str(tmp_f32), "rb") as wf:
        n_frames = wf.getnframes()
        raw = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0
        base = raw.reshape(-1, 2)
    tmp_f32.unlink(missing_ok=True)

    target_len = int(round(dur * SR))
    if len(base) < target_len:
        pad = np.zeros((target_len - len(base), 2), dtype=np.float32)
        base = np.vstack([base, pad])
    else:
        base = base[:target_len]

    sfx_bus = np.zeros_like(base)

    def place_sfx(at_s: float, kind: str, gain_db: float = 0.0) -> None:
        arr = make_sfx_event(kind)
        gain = 10.0 ** (gain_db / 20.0)
        idx0 = max(0, int(round(at_s * SR)))
        idx1 = min(len(sfx_bus), idx0 + len(arr))
        if idx1 > idx0:
            sfx_bus[idx0:idx1] += arr[: idx1 - idx0] * gain

    for seg in schedule:
        at_s = float(seg["start"])
        sfx_kind = str(seg["sfx"])
        gain_db = -0.5 if at_s <= 3.60 else -3.5
        place_sfx(at_s, sfx_kind, gain_db=gain_db)

    for t_in in callouts:
        place_sfx(t_in, "ui_click_ding", gain_db=-4.0)

    mixed = np.clip(base + sfx_bus * 0.52, -0.98, 0.98)
    raw_mix_wav = out_wav.parent / "_tmp_v4_pre_lufs.wav"
    pcm16 = (mixed * 32767.0).astype(np.int16)
    with wave.open(str(raw_mix_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm16.tobytes())

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(raw_mix_wav),
            "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=11",
            "-ar", str(SR),
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(out_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    raw_mix_wav.unlink(missing_ok=True)
    print(f"[v4_audio] Built {out_wav} ({out_wav.stat().st_size:,} bytes, -14.0 LUFS)", flush=True)


def main() -> int:
    # 1. Update Cut A (65.44s)
    out_plate_a = CUT_A_DIR / "clips" / "v4_plate_track.mp4"
    out_audio_a = CUT_A_DIR / "audio" / "A_v4_65s_14lufs.wav"
    out_audio_a.parent.mkdir(parents=True, exist_ok=True)
    if not out_plate_a.exists():
        render_v4_plate_track_scheduled(out_plate_a, CUT_SCHEDULE, 65.44)
    if not out_audio_a.exists():
        build_v4_audio_master_scheduled(AUDIO_DIR / "A_65s_14lufs.wav", out_audio_a, CUT_SCHEDULE, [0.55, 37.35, 58.30], 65.44)
    update_index_html_v4(CUT_A_DIR / "index.html", "clips/v4_plate_track.mp4", "audio/A_v4_65s_14lufs.wav", 65.44, is_fast=False)

    # 2. Build Cut B (53.40s fast 1.24x variant)
    cut_b_dir = WORK_DIR / "cut_pilot1_B_65s"
    sched_b = scale_schedule_for_duration(53.40)
    out_plate_b = cut_b_dir / "clips" / "v4_plate_track.mp4"
    out_audio_b = cut_b_dir / "audio" / "B_v4_53s_14lufs.wav"
    out_audio_b.parent.mkdir(parents=True, exist_ok=True)
    render_v4_plate_track_scheduled(out_plate_b, sched_b, 53.40)
    build_v4_audio_master_scheduled(AUDIO_DIR / "B_65s_14lufs.wav", out_audio_b, sched_b, [0.55, 30.40, 47.45], 53.40)
    update_index_html_v4(cut_b_dir / "index.html", "clips/v4_plate_track.mp4", "audio/B_v4_53s_14lufs.wav", 53.40, is_fast=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
