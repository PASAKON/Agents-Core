#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Steps 2-4 of BRIEF-ep07-build.md: Build Ghost Rules EP07 Master, Sheet, Sample, and Scare Clip.

All inputs are on disk under /opt/MoonieXHQ/Work/ghost-pilot/ep07/ and
/opt/MoonieXHQ/Work/ghost-pilot/sfx-horror-pack/. No network, no browser, no paid call, no upload.

Reference code copied (no cross-folder imports):
  - Plate motion: /opt/MoonieXHQ/Work/tool4-demo/plate/render.py
    * inpaint hole = dilate(alpha > 140, 11x11), cv2.INPAINT_TELEA
    * object alpha = GaussianBlur(clip((a - 30) / 90, 0, 1), 1.0)
    * warpAffine creep/sway/breathe/parallax; fog, flicker, vignette, grain
  - Jump scare (P38): /opt/MoonieXHQ/Work/tool4-demo/scare/render.py
    * FACE = (W * 0.52, H * 0.44), CALM 3.0 s (P38.png) then REVEAL (P38_REVEAL.png)
  - Voices: /opt/MoonieXHQ/Work/tool4-demo/voices/render.py
    * silence trim both ends (silenceremove via areverse), 0.35 s gaps
  - Full-EP builder: /opt/MoonieXHQ/Work/ghostrules-full/ep06/build_ep06_timeline_audio_render.py
    * timeline, audio master -14 LUFS / TP -1.2, phase overlays (CMO_Standard_GhostChannel_DNA §2), concat

Deliverables in /opt/MoonieXHQ/Work/ghost-pilot/ep07/out/:
  - ep07_master.mp4
  - sheet_24.jpg (24 evenly spaced frames, numbered)
  - sample_60s.mp4 (first 60 s)
  - scare_15s.mp4 (P37 end .. P39 start)
Per-shot intermediates are deleted after ep07_master.mp4's MD5 is printed.
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

cv2.setNumThreads(1)

BASE = Path("/opt/MoonieXHQ/Work/ghost-pilot/ep07")
PLATES_DIR = BASE / "plates"
CUTOUTS_DIR = BASE / "cutouts"
TAKES_DIR = BASE / "voice" / "takes"
JOB_JSON = BASE / "voice" / "job.json"
SFX_PACK = Path("/opt/MoonieXHQ/Work/ghost-pilot/sfx-horror-pack")
OUT_DIR = BASE / "out"
TMP_DIR = BASE / "tmp"
TRIM_DIR = TMP_DIR / "trimmed_voices"
SHOTS_DIR = TMP_DIR / "shots"

W, H, FPS = 1920, 1080, 24
SR = 48000
GAP_S = 0.35
TRANS_CARD_DUR_S = 3.30
MIN_FREE_GIB = 8.0


def say(*args) -> None:
    print(time.strftime("%H:%M:%S"), *args, flush=True)


def check_resources_before_shot(shot_id: str) -> None:
    """Run `free -m` before each shot and stop if `/` has < 8 GiB free."""
    free_out = subprocess.check_output(["free", "-m"], text=True).strip()
    mem_line = next((ln for ln in free_out.splitlines() if ln.startswith("Mem:")), free_out.splitlines()[-1])
    usage = shutil.disk_usage("/")
    free_gib = usage.free / float(1024 ** 3)
    say(f"[{shot_id}] free -m -> {mem_line} | / free={free_gib:.2f} GiB")
    if free_gib < MIN_FREE_GIB:
        raise RuntimeError(f"ABORT: / has only {free_gib:.2f} GiB free (< {MIN_FREE_GIB} GiB floor)")


def run_nice_ff(args: list[str]) -> None:
    subprocess.run(
        ["nice", "-n", "10", "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


def get_wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def find_pause_in_wav(wav_path: Path, target_rel_sec: float, window_search: float = 1.4) -> float:
    """Locate the lowest-RMS speech pause near `target_rel_sec` inside a mono WAV."""
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
        sw = wf.getsampwidth()
    if sw == 2:
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        arr = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    total_s = len(arr) / float(sr)
    lo_s = max(1.0, min(total_s - 1.0, target_rel_sec - window_search))
    hi_s = max(lo_s + 0.15, min(total_s - 0.6, target_rel_sec + window_search))
    win = max(1, int(0.12 * sr))
    step = max(1, int(0.03 * sr))
    best_t = target_rel_sec
    min_rms = 999.0
    for s_i in range(int(lo_s * sr), max(int(lo_s * sr) + 1, int(hi_s * sr) - win), step):
        rms = float(np.sqrt(np.mean(arr[s_i:s_i + win] ** 2)))
        if rms < min_rms:
            min_rms = rms
            best_t = s_i / float(sr)
    return round(best_t, 3)


# ==============================================================================
# Self-Contained Phase 1 Torn-Paper Border & Phase 2 Transition Typography
# ==============================================================================
def _fbm_1d(n_pts: int, rng: np.random.Generator, octaves=(80.0, 32.0, 12.0, 4.0), weights=(0.48, 0.28, 0.16, 0.08)) -> np.ndarray:
    x = np.arange(n_pts, dtype=np.float32)
    total = np.zeros(n_pts, dtype=np.float32)
    for wl, w in zip(octaves, weights):
        n_grid = int(math.ceil(n_pts / wl)) + 3
        knots = rng.normal(0, 1.0, n_grid)
        if wl == 32.0:
            notch = rng.random(n_grid) < 0.16
            knots[notch] *= 2.2
        total += w * np.interp(x / wl, np.arange(n_grid), knots)
    return total


def build_torn_border_rgba() -> Image.Image:
    """Build 1920x1080 RGBA Torn-Paper border (Phase 1 Hook only; zero top-left text, zero logo)."""
    rng = np.random.default_rng(303)
    margin = 34
    tear_amp = 10.0
    pulp_w = 6.5
    step = 3
    edges = [
        ((margin, margin), (W - margin, margin), (0, -1)),
        ((W - margin, margin), (W - margin, H - margin), (1, 0)),
        ((W - margin, H - margin), (margin, H - margin), (0, 1)),
        ((margin, H - margin), (margin, margin), (-1, 0)),
    ]
    outer_pts, inner_pts = [], []
    for (x1, y1), (x2, y2), (nx, ny) in edges:
        dist = math.hypot(x2 - x1, y2 - y1)
        n_pts = max(8, int(dist / step))
        f_base = _fbm_1d(n_pts, rng) * tear_amp
        f_pulp = np.clip(
            pulp_w + _fbm_1d(n_pts, rng, octaves=(50.0, 16.0, 5.0), weights=(0.55, 0.30, 0.15)) * (pulp_w * 0.6),
            2.0,
            pulp_w * 2.1,
        )
        for i in range(n_pts):
            t = i / float(n_pts)
            bx = x1 + (x2 - x1) * t
            by = y1 + (y2 - y1) * t
            d_in = float(f_base[i])
            d_out = d_in + float(f_pulp[i])
            outer_pts.append((bx + nx * d_out, by + ny * d_out))
            inner_pts.append((bx + nx * d_in, by + ny * d_in))

    # Surround outside outer_pts is dark Nero charcoal (5, 5, 7); between outer_pts and inner_pts is ash pulp fiber
    outer_mask = Image.new("L", (W, H), 255)
    ImageDraw.Draw(outer_mask).polygon(outer_pts, fill=0)
    outer_mask = outer_mask.filter(ImageFilter.GaussianBlur(radius=0.8))

    inner_hole = Image.new("L", (W, H), 255)
    ImageDraw.Draw(inner_hole).polygon(inner_pts, fill=0)
    inner_hole = inner_hole.filter(ImageFilter.GaussianBlur(radius=0.6))

    pulp_ring = np.clip(
        (np.asarray(inner_hole, dtype=np.float32) - np.asarray(outer_mask, dtype=np.float32)) / 255.0,
        0.0,
        1.0,
    )
    outer_arr = np.asarray(outer_mask, dtype=np.float32) / 255.0

    rgba = np.zeros((H, W, 4), dtype=np.float32)
    # Dark surround
    rgba[..., 0] = 5.0 * outer_arr
    rgba[..., 1] = 5.0 * outer_arr
    rgba[..., 2] = 7.0 * outer_arr
    rgba[..., 3] = 255.0 * outer_arr

    # Ash-cream paper pulp rim
    grain = rng.normal(0, 10.0, (H, W))
    for c, bv in enumerate((168.0, 162.0, 154.0)):
        val = np.clip(bv + grain, 90.0, 235.0)
        rgba[..., c] = rgba[..., c] * (1.0 - pulp_ring) + val * pulp_ring
    rgba[..., 3] = np.clip(rgba[..., 3] + pulp_ring * 245.0, 0.0, 255.0)

    ov = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
    # Soft red inner glow + drop shadow along the torn edge
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.polygon(outer_pts, outline=(232, 22, 34, 130), width=4)
    gd.polygon(inner_pts, outline=(0, 0, 0, 210), width=3)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=7))
    ov.alpha_composite(glow)
    return ov


def load_serif_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_tracked_text(draw: ImageDraw.ImageDraw, text: str, cx: int, cy: int, font, tracking: float, fill: tuple) -> None:
    widths = [draw.textlength(ch, font=font) for ch in text]
    total_w = sum(widths) + tracking * max(0, len(text) - 1)
    x = cx - total_w * 0.5
    for ch, w in zip(text, widths):
        draw.text((x, cy), ch, font=font, fill=fill, anchor="lm")
        x += w + tracking


# ==============================================================================
# Step 2: Voice Trimming & Timeline Construction
# ==============================================================================
def trim_voices_and_build_timeline() -> dict:
    """Trim silence from all 56 voice takes and build 1-to-1 plate timeline with 0.35 s gaps."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRIM_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    job = json.loads(JOB_JSON.read_text(encoding="utf-8"))
    calls = job["calls"]
    if len(calls) != 56:
        raise RuntimeError(f"Expected 56 calls in {JOB_JSON}, found {len(calls)}")

    shots: list[dict] = []
    voice_spans: list[dict] = []
    t_cursor = 0.0

    for idx, call in enumerate(calls, start=1):
        pid = f"P{idx:02d}"
        take_name = call["name"]
        raw_wav = TAKES_DIR / f"{take_name}.wav"
        trim_wav = TRIM_DIR / f"{pid}_{take_name}.wav"
        if not raw_wav.exists():
            raise FileNotFoundError(f"Missing voice take: {raw_wav}")

        if not (trim_wav.exists() and trim_wav.stat().st_size > 1000):
            # Silence trim both ends (silenceremove via areverse), copied from tool4-demo/voices/render.py
            run_nice_ff([
                "-i", str(raw_wav),
                "-af", (
                    "silenceremove=start_periods=1:start_threshold=-45dB,"
                    "areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,"
                    "areverse,"
                    f"aresample={SR}"
                ),
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(trim_wav),
            ])

        voice_dur = get_wav_duration(trim_wav)
        voice_start = t_cursor
        voice_spans.append({
            "plate": pid,
            "name": take_name,
            "voice": call.get("voice", "Algenib"),
            "wav": str(trim_wav),
            "start_s": round(voice_start, 4),
            "voice_dur_s": round(voice_dur, 4),
        })

        if pid == "P05":
            # P05 (c02_02_narrator_omen) ends with "... ย้อนกลับไปเมื่อสามวันก่อน..."
            # Split at the spoken pause before "ย้อนกลับไปเมื่อสามวันก่อน..." so Phase 1 ends on P05
            # and Phase 2 (3.3s full-bleed THREE DAYS EARLIER card) plays over the transition phrase.
            pause_rel = find_pause_in_wav(trim_wav, max(2.5, voice_dur - 2.6), window_search=1.2)
            p05_dur = max(2.5, round(pause_rel, 4))
            rem_voice = max(0.0, voice_dur - p05_dur)
            card_dur = round(max(TRANS_CARD_DUR_S, rem_voice + GAP_S), 4)

            p05_frames = max(1, round(p05_dur * FPS))
            shots.append({
                "id": "P05",
                "plate": "P05",
                "take_name": take_name,
                "phase": 1,
                "start_s": round(t_cursor, 4),
                "duration_s": round(p05_frames / float(FPS), 4),
                "frames": p05_frames,
            })
            t_cursor += p05_frames / float(FPS)

            card_frames = max(1, round(card_dur * FPS))
            shots.append({
                "id": "CARD_THREE_DAYS_EARLIER",
                "plate": "CARD_THREE_DAYS_EARLIER",
                "take_name": take_name,
                "phase": 2,
                "start_s": round(t_cursor, 4),
                "duration_s": round(card_frames / float(FPS), 4),
                "frames": card_frames,
            })
            t_cursor += card_frames / float(FPS)
        else:
            shot_dur = voice_dur + GAP_S
            # Ensure P38 is at least 7.5s so the 3.0s CALM + >=4.5s REVEAL plays completely
            if pid == "P38" and shot_dur < 7.5:
                shot_dur = 7.5
            n_frames = max(1, round(shot_dur * FPS))
            phase = 1 if idx <= 5 else 3
            shots.append({
                "id": pid,
                "plate": pid,
                "take_name": take_name,
                "phase": phase,
                "start_s": round(t_cursor, 4),
                "duration_s": round(n_frames / float(FPS), 4),
                "frames": n_frames,
            })
            t_cursor += n_frames / float(FPS)

    shot_by_id = {s["id"]: s for s in shots}
    p37 = shot_by_id["P37"]
    p38 = shot_by_id["P38"]
    p39 = shot_by_id["P39"]

    tl = {
        "episode": "EP07",
        "title_th": "โรงสีข้าวร้างคลองเจ็ด กับกฎเหล็ก 5 ข้อของยุ้งไซโลหมายเลข 4",
        "fps": FPS,
        "total_frames": sum(s["frames"] for s in shots),
        "duration_s": round(t_cursor, 4),
        "transition_card_start_s": shot_by_id["CARD_THREE_DAYS_EARLIER"]["start_s"],
        "transition_card_dur_s": shot_by_id["CARD_THREE_DAYS_EARLIER"]["duration_s"],
        "scare_calm_start_s": p38["start_s"],
        "scare_sting_s": round(p38["start_s"] + 3.0, 4),
        "scare_end_s": round(p38["start_s"] + p38["duration_s"], 4),
        "scare_15s_window": [
            round(max(0.0, p38["start_s"] - 2.0), 4),
            round(min(t_cursor, p38["start_s"] + 13.0), 4),
        ],
        "p37_end_s": round(p37["start_s"] + p37["duration_s"], 4),
        "p39_start_s": p39["start_s"],
        "voice_spans": voice_spans,
        "shots": shots,
    }
    (OUT_DIR / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"Timeline built: {len(shots)} shots, {tl['total_frames']} frames ({tl['duration_s']:.2f}s)")
    return tl


# ==============================================================================
# Step 3A: Plate-Motion & Jump-Scare Per-Shot Renderer (1920x1080 @ 24fps)
# ==============================================================================
class PlateMotionEngine:
    def __init__(self) -> None:
        self.rng = np.random.default_rng(7)
        noise = cv2.resize(self.rng.random((27, 48)).astype(np.float32), (W * 2, H), interpolation=cv2.INTER_CUBIC)
        noise = cv2.GaussianBlur(noise, (0, 0), 40)
        self.noise = (noise - noise.min()) / (np.ptp(noise) + 1e-6)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx = xx
        self.yy = yy
        self.vig = 1.0 - 0.55 * (((xx - W / 2.0) / W) ** 2 + ((yy - H / 2.0) / H) ** 2) * 2.0
        self.vig_scare = 1.0 - 0.60 * (((xx - W / 2.0) / W) ** 2 + ((yy - H / 2.0) / H) ** 2) * 2.0
        self.torn_rgba = build_torn_border_rgba()
        self.torn_np = np.asarray(self.torn_rgba, dtype=np.float32)
        self.font_serif_64 = load_serif_font(64)
        self.font_serif_26 = load_serif_font(26)

    def fog(self, t: float, speed: float, amt: float) -> np.ndarray:
        off = int((t * speed) % W)
        return self.noise[:, off:off + W][..., None] * amt

    @staticmethod
    def warp(img: np.ndarray, cx: float, cy: float, ang: float, sc: float, dx: float, dy: float, reflect: bool = True) -> np.ndarray:
        M = cv2.getRotationMatrix2D((cx, cy), ang, sc)
        M[0, 2] += dx
        M[1, 2] += dy
        border = cv2.BORDER_REFLECT if reflect else cv2.BORDER_CONSTANT
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)

    @staticmethod
    def comp(bg: np.ndarray, obj: np.ndarray) -> np.ndarray:
        a = obj[..., 3:4] / 255.0
        return bg * (1.0 - a) + obj[..., :3] * a

    def load_plate_pair(self, pid: str) -> tuple[np.ndarray, np.ndarray | None]:
        """Load plate and optional cutout; inpaint hole = dilate(alpha>140, 11x11), cv2.INPAINT_TELEA."""
        p_path = PLATES_DIR / f"{pid}.png"
        bgr = cv2.imread(str(p_path))
        if bgr is None:
            raise FileNotFoundError(f"Cannot read plate {p_path}")
        rgb = bgr[:, :, ::-1]
        fg_path = CUTOUTS_DIR / f"{pid}_fg.png"
        up = lambda im: cv2.resize(im.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)

        if not fg_path.exists():
            return up(rgb), None

        fg = np.asarray(Image.open(fg_path).convert("RGBA"))
        if fg.shape[:2] != rgb.shape[:2]:
            fg = cv2.resize(fg, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
        a = fg[..., 3]
        fg_cov = float((a > 140).mean())
        if fg_cov > 0.55 or fg_cov < 0.003:
            return up(rgb), None

        hole = cv2.dilate((a > 140).astype(np.uint8) * 255, np.ones((11, 11), np.uint8))
        clean_bgr = cv2.inpaint(np.ascontiguousarray(bgr), hole, 12, cv2.INPAINT_TELEA)
        clean = clean_bgr[:, :, ::-1].astype(np.float32)
        hole_f = hole[..., None].astype(np.float32) / 255.0
        clean = cv2.GaussianBlur(clean, (0, 0), 1.2) * hole_f + clean * (1.0 - hole_f)

        al = np.clip((a.astype(np.float32) - 30.0) / 90.0, 0.0, 1.0)
        al = cv2.GaussianBlur(al, (0, 0), 1.0)
        obj = np.dstack([fg[..., :3].astype(np.float32), al * 255.0])
        return up(clean), up(obj)

    def apply_phase1_overlay(self, frame_rgb: np.ndarray, t: float) -> np.ndarray:
        """Apply Phase 1 Torn-Paper Border + bottom-center crimson waveform (by = H - 48)."""
        a = self.torn_np[..., 3:4] / 255.0
        out = frame_rgb * (1.0 - a) + self.torn_np[..., :3] * a
        im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")
        dr = ImageDraw.Draw(im)
        w_cx, w_cy = W // 2, H - 48
        for i in range(-18, 19):
            bx = w_cx + i * 9
            env = math.exp(-((i / 9.5) ** 2))
            bh = int(3 + 16 * env * (0.55 + 0.45 * abs(math.sin(t * 11.0 + i * 0.55))))
            dr.line([(bx, w_cy - bh), (bx, w_cy + bh)], fill=(235, 28, 36), width=3)
        return np.asarray(im, dtype=np.float32)

    def render_transition_card(self, shot: dict, out_path: Path) -> dict:
        """Render Phase 2 full-bleed THREE DAYS EARLIER transition card (3.3s)."""
        n_frames = shot["frames"]
        dur = shot["duration_s"]
        ff = subprocess.Popen(
            [
                "nice", "-n", "10", "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                str(out_path),
            ],
            stdin=subprocess.PIPE,
        )
        for fi in range(n_frames):
            t = fi / float(FPS)
            u = t / max(0.01, dur)
            if t < 0.45:
                alpha = 0.5 - 0.5 * math.cos((t / 0.45) * math.pi)
            elif t < dur - 0.55:
                alpha = 1.0
            else:
                alpha = 0.5 + 0.5 * math.cos(((t - (dur - 0.55)) / 0.55) * math.pi)

            # Full-bleed dark drifting mist background
            base = np.zeros((H, W, 3), dtype=np.float32) + np.array([7.0, 7.0, 10.0], dtype=np.float32)
            mist = self.fog(t, 38.0, 0.22)
            glow = np.exp(-(((self.xx - W * 0.5) / 520.0) ** 2 + ((self.yy - H * 0.5) / 230.0) ** 2))[..., None]
            base = base + mist * 95.0 * alpha + glow * np.array([85.0, 14.0, 18.0], dtype=np.float32) * (0.45 * alpha)
            base = base * self.vig[..., None] + self.rng.normal(0, 3.5, (H, W, 1))

            im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")
            txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            td = ImageDraw.Draw(txt)
            a_int = int(round(255 * alpha))
            tracking = 16.0 + 3.0 * u
            draw_tracked_text(td, "THREE DAYS EARLIER", W // 2 + 2, H // 2 - 18 + 3, self.font_serif_64, tracking, (0, 0, 0, int(a_int * 0.85)))
            draw_tracked_text(td, "THREE DAYS EARLIER", W // 2, H // 2 - 18, self.font_serif_64, tracking, (240, 235, 226, a_int))

            line_half = int(round((140 + 220 * min(1.0, t / 1.6)) * alpha))
            if line_half > 4:
                td.line(
                    [(W // 2 - line_half, H // 2 + 36), (W // 2 + line_half, H // 2 + 36)],
                    fill=(220, 26, 34, int(a_int * 0.92)),
                    width=3,
                )
            im.alpha_composite(txt)
            ff.stdin.write(im.convert("RGB").tobytes())
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError("ffmpeg failed on CARD_THREE_DAYS_EARLIER")
        return {"id": shot["id"], "kind": "phase2_card", "frames": n_frames}

    def render_jump_scare_p38(self, shot: dict, out_path: Path) -> dict:
        """Render P38 jump scare using exact math from /opt/MoonieXHQ/Work/tool4-demo/scare/render.py."""
        load = lambda fn: cv2.resize(
            cv2.imread(str(PLATES_DIR / fn))[:, :, ::-1].astype(np.float32),
            (W, H),
            interpolation=cv2.INTER_CUBIC,
        )
        calm = load("P38.png")
        rev = load("P38_REVEAL.png")
        face_cx, face_cy = W * 0.52, H * 0.44
        calm_dur = 3.0
        n_frames = shot["frames"]
        rng = np.random.default_rng(5)

        ff = subprocess.Popen(
            [
                "nice", "-n", "10", "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                str(out_path),
            ],
            stdin=subprocess.PIPE,
        )
        for i in range(n_frames):
            t = i / float(FPS)
            if t < calm_dur:
                u = t / calm_dur
                f = self.warp(calm, W / 2.0, H * 0.45, 0.0, 1.0 + 0.08 * u, math.sin(t * 7.0) * 1.5, math.sin(t * 5.3) * 1.2, reflect=True)
                f = f * (0.93 + 0.07 * math.sin(t * 50.0) * (1.0 if u > 0.7 else 0.0))
                if t > calm_dur - 0.25:
                    f = f * 0.55
            else:
                s = t - calm_dur
                k = min(s / 0.18, 1.0)
                e = 1.0 - (1.0 - k) ** 3
                sc = 1.55 - 0.55 * e + 0.06 * min(s / 6.0, 1.0)
                sh = 26.0 * math.exp(-s * 4.5)
                f = self.warp(
                    rev,
                    face_cx,
                    face_cy,
                    float(rng.uniform(-1.0, 1.0) * sh * 0.08),
                    sc,
                    float(rng.uniform(-sh, sh)),
                    float(rng.uniform(-sh, sh)),
                    reflect=True,
                )
                if s < 0.5:
                    b = int(1 + 30 * (1.0 - e))
                    if b > 1:
                        f = cv2.blur(f, (b, 1))
                    off = int(18 * (1.0 - s / 0.5))
                    f[..., 0] = np.roll(f[..., 0], off, axis=1)
                    f[..., 2] = np.roll(f[..., 2], -off, axis=1)
                if s < 2.0 / FPS:
                    f = f * 0.3 + 255.0 * 0.7
                elif s < 5.0 / FPS:
                    f = f * 0.75 + np.array([150.0, 0.0, 0.0], dtype=np.float32) * 0.25
                if s > 0.6:
                    f = f * (0.8 + 0.2 * (1.0 if (int(s * 24) % 7 != 0) else 0.0))

            f = f * self.vig_scare[..., None] + rng.normal(0, 5, (H, W, 1))
            ff.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError("ffmpeg failed on P38 jump scare")
        return {"id": "P38", "kind": "jump_scare_python", "frames": n_frames}

    def eval_plate_frame(self, pid: str, bg: np.ndarray, obj: np.ndarray | None, u: float, t: float, dur: float) -> np.ndarray:
        """Evaluate exact per-plate camera, cutout, fog, and lighting recipe from plates.md."""
        idx = int(pid[1:])
        # Default parameters
        bz = 1.0 + 0.045 * u
        bg_dx = 0.0
        bg_dy = 0.0
        bg_ang = 0.0
        cx, cy = W * 0.50, H * 0.50

        obj_ang = 0.0
        obj_sc = bz * 1.012
        obj_dx = 0.0
        obj_dy = 0.0
        obj_cx, obj_cy = W * 0.50, H * 0.55

        fog_speed, fog_amt = 26.0, 0.10
        fl = 1.0
        extra_glow = None
        flash_add = 0.0

        if idx == 1:
            bz = 1.0 + 0.045 * u
            obj_ang = 1.8 * math.sin(t * 2.3) * (1.0 - 0.25 * u)
            obj_dy = 2.5 * math.sin(t * 2.3 + 0.8)
            obj_sc = bz
            fl = 0.84 if (int(t * 12) % 19 in (3, 4)) else 1.0
            fog_speed, fog_amt = 24.0, 0.09
        elif idx == 2:
            bz = 1.0 + 0.04 * u
            bg_dx = -8.0 * u
            obj_sc = 1.015 + 0.055 * u
            obj_dx = -22.0 * u
            fog_speed, fog_amt = 32.0, 0.11
            g = np.exp(-(((self.xx - W * 0.28) / 180.0) ** 2 + ((self.yy - H * 0.62) / 110.0) ** 2))[..., None]
            extra_glow = g * np.array([95.0, 12.0, 12.0], dtype=np.float32) * (0.7 + 0.3 * math.sin(t * 8.0))
        elif idx == 3:
            bz = 1.0 + 0.06 * u
            obj_dy = 9.0 * u + math.sin(t * 19.0) * 0.8
            obj_sc = bz * (1.0 + 0.025 * u)
            if dur - t < 0.4:
                fl = 0.65
        elif idx == 4:
            bz = 1.08 - 0.05 * u
            bg_dx = 10.0 * u
            obj_ang = 1.1 * math.sin(t * 1.6)
            obj_dx = 18.0 * u
            obj_sc = bz
            fog_speed, fog_amt = 35.0, 0.14
        elif idx == 5:
            bz = 1.0 + 0.06 * u
            obj_ang = 0.8 * math.sin(t * 3.1)
            obj_sc = bz * (1.01 + 0.008 * math.sin(t * 3.1))
            fog_speed, fog_amt = 28.0, 0.11
        elif idx == 6:
            bz = 1.0 + 0.035 * u
            obj_dx = 26.0 * u
            obj_dy = -6.0 * u
            obj_sc = bz * (1.0 + 0.006 * math.sin(t * 2.2))
            obj_ang = 1.2 * math.sin(t * 1.4)
            fog_speed, fog_amt = 50.0, 0.14
        elif idx == 7:
            bz = 1.0 + 0.05 * u
            obj_dx = -18.0 * u
            obj_dy = 2.0 * math.sin(t * 2.0)
            obj_ang = 2.0 * math.sin(t * 3.2)
            obj_sc = bz * 1.012
        elif idx == 8:
            bz = 1.0 + 0.045 * u
            obj_sc = bz * (1.0 + 0.007 * math.sin(t * 2.1))
            obj_dy = 3.5 * u
            obj_ang = -0.6 * u
        elif idx == 9:
            bz = 1.0 + 0.04 * u
            bg_dx = 10.0 * u
            obj_dx = 22.0 * u
            obj_ang = 0.5 * math.sin(t * 1.9)
            obj_sc = bz * (1.0 + 0.006 * math.sin(t * 2.4))
        elif idx == 10:
            bz = 1.0 + 0.055 * u
            obj_sc = bz * 1.015
            obj_dx = -16.0 * u + math.sin(t * 14.0) * 0.6
            if u > 0.75:
                fl = 0.80
        elif idx == 11:
            bz = 1.0 + 0.03 * u
            obj_sc = 1.0 - 0.18 * u
            obj_dx = -42.0 * u
            obj_dy = -8.0 * u
            fog_speed, fog_amt = 55.0, 0.16
        elif idx == 12:
            bz = 1.0 + 0.06 * u
            obj_ang = -1.2 * (1.0 - u)
            obj_sc = bz * 1.018
            obj_dy = -10.0 * u
        elif idx == 13:
            bz = 1.0 + 0.05 * u
            obj_dx = 28.0 * u
            obj_dy = 3.0 * u
            obj_sc = bz * 1.015
        elif idx == 14:
            bz = 1.0 + 0.04 * u
            bg_dx = -10.0 * u
            obj_dx = -28.0 * u
            obj_dy = -8.0 * u
            obj_sc = bz * (1.0 + 0.03 * u)
            obj_ang = 2.5 * math.sin(t * 1.5)
            fog_speed, fog_amt = 22.0, 0.11
        elif idx == 15:
            bz = 1.06 - 0.04 * u
            obj_ang = -1.4 * u
            obj_dy = 4.0 * u
            obj_sc = bz * (1.0 + 0.006 * math.sin(t * 2.3))
            if int(t * 12) % 23 == 7:
                fl = 0.88
        elif idx == 16:
            bz = 1.0 + 0.07 * u
            bg_dx = 16.0 * u
            obj_dx = -14.0 * u
            obj_sc = bz * 1.015
            if u >= 0.18:
                g = np.exp(-(((self.xx - W * 0.22) / 160.0) ** 2 + ((self.yy - H * 0.58) / 110.0) ** 2))[..., None]
                extra_glow = g * np.array([120.0, 15.0, 15.0], dtype=np.float32) * (0.75 + 0.25 * math.sin(t * 10.0))
        elif idx == 17:
            bz = 1.0 + 0.065 * u
            obj_dx = -24.0 * u
            obj_sc = bz * 1.02
            fog_speed, fog_amt = 45.0, 0.15
        elif idx == 18:
            bz = 1.0 + 0.05 * u
            obj_dx = -26.0 * min(u * 1.4, 1.0) + math.sin(t * 28.0) * 0.9
            obj_sc = bz * 1.015
        elif idx == 19:
            bz = 1.0 + 0.045 * u
            obj_ang = 2.2 * math.sin(t * 3.0) * u
            obj_dy = 3.0 * math.sin(t * 3.0) * u
            obj_sc = bz
            if int(t * 12) % 21 == 5:
                fl = 0.86
        elif idx == 20:
            bz = 1.06 - 0.04 * u
            obj_sc = bz * (1.0 + 0.045 * u)
            obj_dy = 12.0 * u
            obj_ang = 1.8 * math.sin(t * 1.7)
            fog_speed, fog_amt = 28.0, 0.12
        elif idx == 21:
            bz = 1.0 + 0.055 * u
            obj_ang = 4.8 * math.sin(t * 4.2)
            obj_dy = 5.0 * math.sin(t * 4.2)
            obj_sc = bz
        elif idx == 22:
            bz = 1.0 + 0.04 * u
            obj_dy = -18.0 * u
            obj_dx = -14.0 * u
            obj_ang = -3.5 * u
            obj_sc = bz * 1.015
        elif idx == 23:
            bz = 1.0 + 0.065 * u
            obj_dx = 20.0 * u + math.sin(t * 9.0) * 1.4
            obj_dy = 14.0 * u
            obj_sc = bz * 1.015
        elif idx == 24:
            bz = 1.0 + 0.055 * u
            obj_ang = 3.2 * math.sin(t * 2.6) * (1.0 - 0.2 * u)
            obj_sc = bz
            fog_speed, fog_amt = 65.0, 0.18
        elif idx == 25:
            bz = 1.0 + 0.05 * u
            obj_dx = -22.0 * u + math.sin(t * 11.0) * 0.9
            obj_dy = 8.0 * u
            obj_sc = bz * 1.015
        elif idx == 26:
            bz = 1.0 + 0.05 * u
            jud = sum(5.5 * math.exp(-(((u - u0) * 25.0) ** 2)) * math.sin(t * 55.0) for u0 in (0.18, 0.45, 0.72))
            bg_dx = jud * 0.5
            obj_dx = jud
            obj_dy = jud * 0.6
            obj_sc = bz
            if abs(jud) > 1.2:
                fl = 0.78
        elif idx == 27:
            bz = 1.0 + 0.06 * u
            obj_dy = 12.0 * u
            obj_ang = -1.5 * u + 1.4 * math.sin(t * 4.5)
            obj_sc = bz * 1.015
        elif idx == 28:
            bz = 1.06 - 0.04 * u
            obj_dx = -18.0 * u
            obj_sc = bz * (1.0 - 0.02 * u) * (1.0 + 0.008 * math.sin(t * 3.4))
        elif idx == 29:
            bz = 1.0 + 0.055 * u
            cyc = (t * 0.9) % 1.0
            obj_dy = 28.0 * (cyc ** 2)
            obj_sc = bz * (1.0 + 0.08 * cyc)
            fog_speed, fog_amt = 20.0, 0.10
        elif idx == 30:
            bz = 1.0 + 0.045 * u
            obj_dx = 8.0 * abs(math.sin(t * 2.4))
            obj_ang = 1.6 * math.sin(t * 2.4)
            obj_dy = 4.0 * math.cos(t * 2.4)
            obj_sc = bz
            fog_speed, fog_amt = 42.0, 0.18
        elif idx == 31:
            bz = 1.0 + 0.05 * u
            obj_ang = 2.4 * math.sin(t * 2.1)
            obj_dx = 3.0 * math.sin(t * 2.1)
            obj_sc = bz
            g = np.exp(-(((self.xx - W * 0.46) / 220.0) ** 2 + ((self.yy - H * 0.38) / 160.0) ** 2))[..., None]
            extra_glow = g * np.array([20.0, 95.0, 75.0], dtype=np.float32) * (0.7 + 0.3 * math.sin(t * 7.0))
            fog_speed, fog_amt = 36.0, 0.16
        elif idx == 32:
            bz = 1.0 + 0.06 * u
            obj_dy = 7.0 * abs(math.sin(t * 3.5))
            obj_dx = -5.0 * u
            obj_ang = -1.2 * math.sin(t * 3.5)
            obj_sc = bz
            fog_speed, fog_amt = 52.0, 0.20
        elif idx == 33:
            bz = 1.0 + 0.055 * u
            obj_dy = -10.0 * u + 3.0 * math.sin(t * 2.0)
            obj_dx = 12.0 * u
            obj_ang = 1.1 * math.sin(t * 1.8)
            obj_sc = bz * 1.015
            fog_speed, fog_amt = 38.0, 0.16
        elif idx == 34:
            bz = 1.0 + 0.05 * u
            obj_dy = 16.0 * u
            obj_ang = -2.0 * u
            obj_sc = bz * 1.015
        elif idx == 35:
            bz = 1.05 - 0.03 * u
            obj_ang = 9.0 * math.exp(-t * 1.4) * math.sin(t * 14.0)
            obj_sc = bz
        elif idx == 36:
            bz = 1.0 + 0.07 * u
            sh = 9.0 * abs(math.sin(t * 9.5))
            bg_dx = math.sin(t * 28.0) * (sh * 0.25)
            bg_dy = math.cos(t * 24.0) * (sh * 0.20)
            obj_dx = math.sin(t * 48.0) * 3.5
            obj_dy = math.cos(t * 42.0) * 3.0
            obj_ang = 2.8 * math.sin(t * 35.0)
            obj_sc = bz * 1.015
            fog_speed, fog_amt = 44.0, 0.15
        elif idx == 37:
            bz = 1.0 + 0.065 * u
            obj_dy = -12.0 * u + math.sin(t * 9.0) * 1.2
            obj_dx = 14.0 * u
            obj_sc = bz * 1.015
        elif idx == 39:
            bz = 1.10 - 0.07 * u
            sh = 6.0 * math.exp(-t * 3.0) * math.sin(t * 25.0)
            bg_dx = sh * 0.5
            obj_dx = -32.0 * u + sh
            obj_dy = 14.0 * u
            obj_sc = bz * 1.015
        elif idx == 40:
            bz = 1.0 + 0.055 * u
            bg_dy = -14.0 * u
            obj_ang = 18.0 * u
            obj_dy = -22.0 * u + math.sin(t * 32.0) * 1.4
            obj_sc = bz
            fog_speed, fog_amt = 48.0, 0.16
        elif idx == 41:
            bz = 1.0 + 0.06 * u
            bg_dx = 14.0 * u + math.sin(t * 36.0) * 1.0
            obj_ang = 2.2 * math.sin(t * 3.8)
            obj_dx = 14.0 * u
            obj_sc = bz * 1.012
        elif idx == 42:
            bz = 1.0 + 0.045 * u
            obj_dy = -34.0 * u
            obj_dx = 12.0 * u
            obj_sc = bz * (1.0 + 0.03 * u)
            if abs(u - 0.55) < 0.035:
                flash_add = 55.0
        elif idx == 43:
            bz = 1.0 + 0.065 * u
            obj_ang = 6.0 * u
            obj_dy = -24.0 * u + math.sin(t * 40.0) * 1.5
            obj_sc = bz * 1.015
            fog_speed, fog_amt = 60.0, 0.19
        elif idx == 44:
            bz = 1.0 + 0.06 * u
            obj_dy = -30.0 * u + math.sin(t * 17.0) * 0.9
            obj_sc = bz * (1.0 + 0.035 * u)
        elif idx == 45:
            bz = 1.0 + 0.075 * u
            obj_dy = -26.0 * u
            obj_dx = -16.0 * u
            obj_ang = -4.5 * u
            obj_sc = bz * 1.02
            if abs(u - 0.35) < 0.03 or abs(u - 0.65) < 0.03:
                flash_add = 65.0
        elif idx == 46:
            bz = 1.0 + 0.05 * u
            bg_dx = 18.0 * u
            obj_dx = -38.0 * u
            obj_dy = -6.0 * u
            obj_sc = bz * 1.025
        elif idx == 47:
            bz = 1.0 + 0.065 * u
            obj_dx = -32.0 * u + math.sin(t * 35.0) * 1.3
            obj_dy = -8.0 * u
            obj_sc = bz * 1.02
        elif idx == 48:
            bz = 1.0 + 0.05 * u
            k = min(u * 1.6, 1.0)
            obj_dy = 34.0 * (k ** 2)
            obj_ang = -14.0 * k
            obj_sc = bz * 1.015
            sh = 12.0 * math.exp(-abs(u - 0.55) * 15.0) * math.sin(t * 45.0)
            bg_dx = sh * 0.5
            bg_dy = sh * 0.5
            if abs(u - 0.55) < 0.035:
                g = np.exp(-(((self.xx - W * 0.32) / 220.0) ** 2 + ((self.yy - H * 0.48) / 180.0) ** 2))[..., None]
                extra_glow = g * np.array([180.0, 110.0, 35.0], dtype=np.float32)
        elif idx == 49:
            bz = 1.08 - 0.05 * u
            obj_ang = 2.5 * math.exp(-t * 0.4) * math.sin(t * 3.0)
            obj_sc = bz
            fog_speed, fog_amt = 30.0, 0.16
        elif idx == 50:
            bz = 1.0 + 0.065 * u
            obj_ang = 1.8 * math.sin(t * 4.0)
            obj_dx = -12.0 * u
            obj_sc = bz * 1.015
        elif idx == 51:
            bz = 1.06 - 0.04 * u
            obj_dx = -28.0 * u
            obj_sc = bz * (1.0 - 0.025 * u) * (1.0 + 0.007 * math.sin(t * 2.8))
        elif idx == 52:
            bz = 1.0 + 0.04 * u
            bg_dx = -14.0 * u
            obj_dx = -26.0 * u
            obj_sc = bz * 1.015
            fog_speed, fog_amt = 18.0, 0.08
        elif idx == 53:
            bz = 1.0 + 0.045 * u
            obj_dx = -16.0 * u
            obj_dy = math.sin(t * 12.0) * 0.7
            obj_sc = bz * 1.015
        elif idx == 54:
            bz = 1.0 + 0.035 * u
            obj_sc = bz * (1.0 - 0.05 * u)
            obj_dy = -16.0 * u
            fog_speed, fog_amt = 18.0, 0.09
        elif idx == 55:
            bz = 1.06 - 0.04 * u
            obj_sc = bz * (1.0 + 0.05 * u)
            obj_dx = -24.0 * u
            obj_dy = 10.0 * u
            fog_speed, fog_amt = 20.0, 0.11
        elif idx == 56:
            bz = 1.0 + 0.07 * u
            obj_ang = 1.5 * math.sin(t * 2.0)
            obj_sc = bz
            if t > 2.8 and int(t * 14) % 9 in (1, 2):
                fl = 0.76

        bgw = self.warp(bg, cx, cy, bg_ang, bz, bg_dx, bg_dy, reflect=True)
        if obj is not None:
            ow = self.warp(obj, obj_cx, obj_cy, obj_ang, obj_sc, obj_dx, obj_dy, reflect=False)
            f = self.comp(bgw, ow)
        else:
            f = bgw

        f = f * fl
        fg_layer = self.fog(t, fog_speed, fog_amt)
        f = f * (1.0 - 0.14 * fg_layer) + 155.0 * fg_layer
        if extra_glow is not None:
            f = f + extra_glow
        if flash_add > 0.0:
            f = f + np.array([flash_add * 0.75, flash_add * 0.88, flash_add], dtype=np.float32)

        # Smooth dip across cuts (0.12 s each side), fade-in on P01, fade-out on P56
        edge = min(t, max(0.0, dur - t))
        if idx == 1 and t < 0.45:
            f = f * (t / 0.45)
        elif idx == 56 and (dur - t) < 0.85:
            f = f * max(0.0, (dur - t) / 0.85)
        elif edge < 0.12:
            f = f * (edge / 0.12)

        f = f * self.vig[..., None] + self.rng.normal(0, 5.0, (H, W, 1))
        return f

    def render_standard_shot(self, shot: dict, out_path: Path) -> dict:
        pid = shot["plate"]
        n_frames = shot["frames"]
        dur = shot["duration_s"]
        phase = shot["phase"]
        bg, obj = self.load_plate_pair(pid)

        ff = subprocess.Popen(
            [
                "nice", "-n", "10", "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                str(out_path),
            ],
            stdin=subprocess.PIPE,
        )
        for fi in range(n_frames):
            t = fi / float(FPS)
            u = fi / float(max(1, n_frames - 1))
            f = self.eval_plate_frame(pid, bg, obj, u, t, dur)
            if phase == 1:
                f = self.apply_phase1_overlay(f, shot["start_s"] + t)
            ff.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError(f"ffmpeg failed on shot {shot['id']}")
        return {
            "id": shot["id"],
            "plate": pid,
            "kind": "plate_motion" if obj is not None else "camera_only",
            "phase": phase,
            "frames": n_frames,
        }


def render_all_shots(tl: dict) -> dict:
    engine = PlateMotionEngine()
    audits: dict[str, dict] = {}
    shots = tl["shots"]

    for idx, s in enumerate(shots, start=1):
        sid = s["id"]
        out_p = SHOTS_DIR / f"{idx:03d}_{sid}.mp4"
        if out_p.exists() and out_p.stat().st_size > 20000:
            audits[sid] = {"id": sid, "kind": "cached", "frames": s["frames"], "file": str(out_p)}
            say(f"[{idx}/{len(shots)}] cached {sid} ({s['frames']} frames)")
            continue

        check_resources_before_shot(sid)
        tmp_p = SHOTS_DIR / f"{idx:03d}_{sid}.tmp.mp4"
        if sid == "CARD_THREE_DAYS_EARLIER":
            info = engine.render_transition_card(s, tmp_p)
        elif sid == "P38":
            info = engine.render_jump_scare_p38(s, tmp_p)
        else:
            info = engine.render_standard_shot(s, tmp_p)
        tmp_p.replace(out_p)
        info["file"] = str(out_p)
        audits[sid] = info
        say(f"[{idx}/{len(shots)}] rendered {sid}: {info['kind']} ({s['frames']}f, {s['duration_s']:.2f}s)")

    (OUT_DIR / "render_checks.json").write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding="utf-8")
    return audits


# ==============================================================================
# Step 3B: Full Episode Audio Mix & -14.0 LUFS / TP -1.2 Master
# ==============================================================================
def load_pcm(path: Path) -> np.ndarray:
    raw = subprocess.run(
        ["nice", "-n", "10", "ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def write_pcm(path: Path, arr: np.ndarray) -> None:
    subprocess.run(
        [
            "nice", "-n", "10", "ffmpeg", "-v", "error", "-y",
            "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
            "-c:a", "pcm_f32le", str(path),
        ],
        input=arr.astype(np.float32).tobytes(),
        check=True,
    )


def fade_clip(a: np.ndarray, fi: float = 0.012, fo: float = 0.025) -> np.ndarray:
    a = a.copy()
    i = min(len(a), round(fi * SR))
    o = min(len(a), round(fo * SR))
    if i > 0:
        a[:i] *= np.linspace(0.0, 1.0, i, dtype=np.float32)
    if o > 0:
        a[-o:] *= np.linspace(1.0, 0.0, o, dtype=np.float32)
    return a


def loop_bed_crossfade(src: np.ndarray, total_samples: int, gain: float, xf_sec: float = 1.8) -> np.ndarray:
    bed = np.zeros(total_samples, dtype=np.float32)
    clip = src.astype(np.float32) * float(gain)
    xf = min(len(clip) // 4, round(xf_sec * SR))
    step = len(clip) - xf
    for pos in range(0, total_samples, step):
        seg = clip.copy()
        if pos > 0 and xf > 0:
            seg[:xf] *= np.linspace(0.0, 1.0, xf, dtype=np.float32)
        if pos + len(seg) < total_samples and xf > 0:
            seg[-xf:] *= np.linspace(1.0, 0.0, xf, dtype=np.float32)
        end = min(total_samples, pos + len(seg))
        bed[pos:end] += seg[:end - pos]
    return bed


def smooth_vec(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def build_audio_master(tl: dict) -> tuple[Path, dict]:
    """Assemble 56 trimmed voices + rain (0.10) + drone (0.18) + P38 stings -> -14.0 LUFS master WAV."""
    total_dur = tl["duration_s"]
    n_samples = round(total_dur * SR)
    nar = np.zeros(n_samples, dtype=np.float32)

    for sp in tl["voice_spans"]:
        clip = fade_clip(load_pcm(Path(sp["wav"])))
        start = round(sp["start_s"] * SR)
        count = min(len(clip), n_samples - start)
        if count > 0:
            nar[start:start + count] += clip[:count]

    # SFX beds from BRIEF-ep07-build.md: rain_metal_roof_13 at 0.10, horror_ambience_drone_18 at 0.18
    rain_raw = load_pcm(SFX_PACK / "rain_metal_roof_13.wav")
    drone_raw = load_pcm(SFX_PACK / "horror_ambience_drone_18.wav")
    bed = loop_bed_crossfade(rain_raw, n_samples, gain=0.10) + loop_bed_crossfade(drone_raw, n_samples, gain=0.18)

    # Dip ambience bed to 35% during the 3.0s calm before P38 jump scare, recover over 2.0s after sting
    calm_s = tl["scare_calm_s"] if "scare_calm_s" in tl else tl["scare_calm_start_s"]
    sting_s = tl["scare_sting_s"]
    s0 = max(0, round((calm_s - 0.8) * SR))
    s1 = min(n_samples, round((sting_s + 2.0) * SR))
    times = np.arange(s0, s1, dtype=np.float32) / float(SR)
    env = np.where(
        times < calm_s,
        1.0 - 0.65 * smooth_vec((times - (calm_s - 0.8)) / 0.8),
        np.where(times < sting_s, 0.35, 0.35 + 0.65 * smooth_vec((times - sting_s) / 2.0)),
    )
    bed[s0:s1] *= env.astype(np.float32)
    # 0.8s fade-out at end
    fo = min(n_samples, round(0.8 * SR))
    bed[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)

    sfx = np.zeros(n_samples, dtype=np.float32)
    sfx_events: list[dict] = []

    def add_sfx(wav_name: str, start_s: float, max_dur_s: float, gain: float, zero_on_voice: bool = False) -> None:
        p = SFX_PACK / wav_name
        if not p.exists():
            return
        raw = load_pcm(p)[:round(max_dur_s * SR)]
        clip = fade_clip(raw, 0.005, 0.08) * float(gain)
        pos = max(0, round(start_s * SR))
        end = min(n_samples, pos + len(clip))
        if end <= pos:
            return
        seg = clip[:end - pos]
        if zero_on_voice:
            mask = (np.abs(nar[pos:end]) <= 1e-4).astype(np.float32)
            seg = seg * mask
        sfx[pos:end] += seg
        sfx_events.append({"name": wav_name, "start_s": round(start_s, 3), "dur_s": round((end - pos) / float(SR), 3)})

    # Phase 2 transition boom (`THREE DAYS EARLIER`)
    add_sfx("deep_whoosh_impact_20.wav", tl["transition_card_start_s"], 3.2, gain=0.45)

    # P38 jump scare stings named in plates.md P38: scare_sting_07 + hard_horror_hit_drum_21 at t = calm + 3.0s
    add_sfx("scare_sting_07_fs712416.wav", sting_s, 2.2, gain=0.75)
    add_sfx("hard_horror_hit_drum_21.wav", sting_s, 2.5, gain=0.65)

    mix_wav = TMP_DIR / "mix_raw.wav"
    master_wav = TMP_DIR / "master_14lufs.wav"
    write_pcm(mix_wav, nar + bed + sfx)

    # 2-pass loudnorm to -14.0 LUFS / TP -1.2 dBTP
    p1 = subprocess.run(
        [
            "nice", "-n", "10", "ffmpeg", "-hide_banner", "-nostats",
            "-i", str(mix_wav),
            "-af", "loudnorm=I=-14:TP=-1.2:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    m1 = json.loads(p1.stderr[p1.stderr.rfind("{"):p1.stderr.rfind("}") + 1])
    filt = "loudnorm=I=-14:TP=-1.2:LRA=11:linear=true:" + ":".join([
        f"measured_I={m1['input_i']}",
        f"measured_TP={m1['input_tp']}",
        f"measured_LRA={m1['input_lra']}",
        f"measured_thresh={m1['input_thresh']}",
        f"offset={m1['target_offset']}",
    ])
    run_nice_ff(["-i", str(mix_wav), "-af", filt, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_f32le", str(master_wav)])
    mix_wav.unlink(missing_ok=True)

    p2 = subprocess.run(
        [
            "nice", "-n", "10", "ffmpeg", "-hide_banner", "-nostats",
            "-i", str(master_wav),
            "-af", "loudnorm=I=-14:TP=-1.2:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    m2 = json.loads(p2.stderr[p2.stderr.rfind("{"):p2.stderr.rfind("}") + 1])
    audio_info = {
        "duration_s": round(n_samples / float(SR), 3),
        "sfx_events": sfx_events,
        "loudness_pass1": m1,
        "loudness_master": m2,
    }
    (OUT_DIR / "audio_checks.json").write_text(json.dumps(audio_info, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"Audio mastered: I={m2['input_i']} LUFS, TP={m2['input_tp']} dBTP")
    return master_wav, audio_info


# ==============================================================================
# Step 4: Concat, Deliverables (master, sheet_24, sample_60s, scare_15s), Cleanup
# ==============================================================================
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def measure_file_loudness(path: Path) -> dict:
    p = subprocess.run(
        [
            "nice", "-n", "10", "ffmpeg", "-hide_banner", "-nostats",
            "-i", str(path),
            "-af", "loudnorm=I=-14:TP=-1.2:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1])


def build_sheet_24(master_mp4: Path, duration_s: float, out_jpg: Path) -> None:
    """Extract 24 evenly spaced frames across master_mp4, numbered 01..24 in a 6x4 contact sheet."""
    tw, th = 320, 180
    cols, rows = 6, 4
    sheet = Image.new("RGB", (tw * cols, th * rows), (10, 10, 12))
    font = load_serif_font(20)
    frames_tmp = TMP_DIR / "sheet_frames"
    frames_tmp.mkdir(parents=True, exist_ok=True)

    for i in range(24):
        ts = duration_s * (i + 0.5) / 24.0
        f_jpg = frames_tmp / f"f_{i + 1:02d}.jpg"
        run_nice_ff(["-ss", f"{ts:.3f}", "-i", str(master_mp4), "-frames:v", "1", "-q:v", "2", str(f_jpg)])
        im = Image.open(f_jpg).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        dr = ImageDraw.Draw(im)
        mm = int(ts // 60)
        ss = ts - mm * 60
        label = f"#{i + 1:02d}  {mm:02d}:{ss:04.1f}"
        dr.rectangle([6, 6, 138, 32], fill=(0, 0, 0))
        dr.text((12, 19), label, font=font, fill=(245, 240, 230), anchor="lm")
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))

    sheet.save(out_jpg, quality=92)
    shutil.rmtree(frames_tmp, ignore_errors=True)


def assemble_and_deliver(tl: dict, master_wav: Path) -> dict:
    shots = tl["shots"]
    shot_files = [SHOTS_DIR / f"{idx:03d}_{s['id']}.mp4" for idx, s in enumerate(shots, start=1)]
    for sf in shot_files:
        if not sf.exists():
            raise FileNotFoundError(f"Missing rendered shot file: {sf}")

    concat_list = TMP_DIR / "concat.txt"
    concat_list.write_text("".join(f"file '{sf}'\n" for sf in shot_files), encoding="utf-8")

    master_mp4 = OUT_DIR / "ep07_master.mp4"
    say("Concatenating shots and muxing with -14 LUFS master audio...")
    run_nice_ff([
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(master_wav),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
        "-movflags", "+faststart", "-shortest",
        str(master_mp4),
    ])

    master_md5 = md5_file(master_mp4)
    master_loudness = measure_file_loudness(master_mp4)
    say(f"MASTER READY: {master_mp4} | MD5={master_md5} | I={master_loudness['input_i']} LUFS | TP={master_loudness['input_tp']} dBTP")

    # Delete per-shot intermediates immediately after master's MD5 is printed (Step 4)
    for sf in shot_files:
        sf.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)
    master_wav.unlink(missing_ok=True)
    shutil.rmtree(SHOTS_DIR, ignore_errors=True)
    shutil.rmtree(TRIM_DIR, ignore_errors=True)
    say("Deleted per-shot intermediates after master MD5 verification.")

    # 1. sheet_24.jpg (24 evenly spaced frames, numbered)
    sheet_jpg = OUT_DIR / "sheet_24.jpg"
    build_sheet_24(master_mp4, tl["duration_s"], sheet_jpg)
    sheet_md5 = md5_file(sheet_jpg)
    say(f"SHEET READY: {sheet_jpg} | MD5={sheet_md5}")

    # 2. sample_60s.mp4 (first 60 s)
    sample_mp4 = OUT_DIR / "sample_60s.mp4"
    run_nice_ff([
        "-ss", "0", "-t", "60", "-i", str(master_mp4),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(sample_mp4),
    ])
    sample_md5 = md5_file(sample_mp4)
    say(f"SAMPLE 60S READY: {sample_mp4} | MD5={sample_md5}")

    # 3. scare_15s.mp4 (P37 end .. P39 start, 15s window covering P38 jump scare)
    scare_mp4 = OUT_DIR / "scare_15s.mp4"
    w0, w1 = tl["scare_15s_window"]
    run_nice_ff([
        "-ss", f"{w0:.3f}", "-t", f"{w1 - w0:.3f}", "-i", str(master_mp4),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(scare_mp4),
    ])
    scare_md5 = md5_file(scare_mp4)
    say(f"SCARE 15S READY: {scare_mp4} ({w0:.2f}s..{w1:.2f}s) | MD5={scare_md5}")

    summary = {
        "episode": "EP07",
        "duration_s": tl["duration_s"],
        "total_frames": tl["total_frames"],
        "measured_lufs": master_loudness["input_i"],
        "measured_tp": master_loudness["input_tp"],
        "measured_lra": master_loudness["input_lra"],
        "files": {
            "ep07_master.mp4": {"path": str(master_mp4), "bytes": master_mp4.stat().st_size, "md5": master_md5},
            "sheet_24.jpg": {"path": str(sheet_jpg), "bytes": sheet_jpg.stat().st_size, "md5": sheet_md5},
            "sample_60s.mp4": {"path": str(sample_mp4), "bytes": sample_mp4.stat().st_size, "md5": sample_md5},
            "scare_15s.mp4": {
                "path": str(scare_mp4),
                "bytes": scare_mp4.stat().st_size,
                "md5": scare_md5,
                "window_s": [w0, w1],
            },
        },
    }
    (OUT_DIR / "build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    tl = trim_voices_and_build_timeline()
    if mode == "timeline":
        return 0
    if mode in ("all", "render"):
        render_all_shots(tl)
    if mode in ("all", "audio", "mux"):
        master_wav, _ = build_audio_master(tl)
        if mode in ("all", "mux"):
            assemble_and_deliver(tl, master_wav)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
