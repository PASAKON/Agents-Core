#!/usr/bin/env python3
"""BLACK LIQUIDITY real-footage capture — RUNNER (task-67f82679, IRON-RULES §53).

Drives Playwright against a broker's real site + the real WikiFX page for it,
captures vertical 1080x1920 30fps MP4 clips and PNG evidence stills, censors
ad/PII regions BY THE DOM (not pixel guesses), and writes REAL_MANIFEST.json
so the editor can look up footage by script tag.

Pure censor/frame maths (importable without Playwright installed, same
convention as scripts/higgsfield/gen_loop.py):
    compute_censor_pixel_box, clamp_box, partial_box, pixelate_region,
    nine_sixteen_crop_around, lerp_rect, shot_content_hash

Usage:
    python tools/bl_realfootage.py run --shots prototypes/bl55-realfootage/shots.yaml \
        --episode bl55 [--cdp] [--drive-parent <folder-id>] [--dry-run]

Prereqs for a live run:
    playwright install chromium   (one-time; ~/.cache managed by Playwright itself)
    ffmpeg on PATH (frame-sequence -> H.264 MP4)

If the target site blocks headless Chromium (Cloudflare et al.), re-run with
--cdp against a dedicated automation Chrome profile: bring it up first with
    bash scripts/bl_realfootage/launch-chrome-debug.sh
same pattern as scripts/higgsfield/gen_loop.py -- never log in, never click
signup, never accept anything beyond a cookie banner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FRAME_W, FRAME_H, FPS = 1080, 1920, 30
TH_TZ = timezone(timedelta(hours=7))
CDP_URL = "http://127.0.0.1:9333"
DEFAULT_OUT_ROOT = ROOT / "output" / "bl-realfootage"


# ═══════════════════════════════════════════════════════════════════════════
# Pure maths — no Playwright, no filesystem. Unit-tested directly.
# ═══════════════════════════════════════════════════════════════════════════

def compute_censor_pixel_box(doc_box: dict, scroll_offset: dict, device_pixel_ratio: float
                              ) -> tuple[int, int, int, int]:
    """A DOM box + the scroll offset + devicePixelRatio in, frame pixels out.

    doc_box: {"x","y","width","height"} in CSS px, DOCUMENT-relative
        (getBoundingClientRect() + the scrollX/scrollY that was in effect at
        the moment this box was *measured* -- i.e. a position fixed to the
        page's content, not to the viewport).
    scroll_offset: {"x","y"} -- window.scrollX/scrollY at the moment THIS
        FRAME was captured. May differ from the scroll position at measure
        time (continuous scroll, or a later frame reusing an older
        measurement) -- that difference is exactly what this function
        corrects for.
    device_pixel_ratio: window.devicePixelRatio. Playwright screenshots are
        rasterised at device pixels, so CSS px must be scaled up to land on
        the right pixels in the captured frame.

    Returns (left, top, right, bottom) in RASTER PIXEL coordinates of the
    frame image. Not clamped to the frame bounds -- call clamp_box() for that.
    """
    left_css = doc_box["x"] - scroll_offset["x"]
    top_css = doc_box["y"] - scroll_offset["y"]
    right_css = left_css + doc_box["width"]
    bottom_css = top_css + doc_box["height"]
    dpr = device_pixel_ratio
    return (
        round(left_css * dpr),
        round(top_css * dpr),
        round(right_css * dpr),
        round(bottom_css * dpr),
    )


def clamp_box(box: tuple[int, int, int, int], frame_w: int, frame_h: int
              ) -> tuple[int, int, int, int] | None:
    """Clamp a pixel box to the frame. Returns None if it clamps to nothing
    (fully off-frame) -- caller should skip pixelating in that case."""
    left, top, right, bottom = box
    left = max(0, min(left, frame_w))
    top = max(0, min(top, frame_h))
    right = max(0, min(right, frame_w))
    bottom = max(0, min(bottom, frame_h))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def partial_box(box: tuple[int, int, int, int], fraction: float = 0.4, side: str = "right"
                 ) -> tuple[int, int, int, int]:
    """Shrink a box to just one side of itself -- e.g. the right 40% of a
    logo wordmark, for the "keep it recognisable but partly pixelated" rule."""
    left, top, right, bottom = box
    if side in ("right", "left"):
        span = (right - left) * fraction
        if side == "right":
            return (round(right - span), top, right, bottom)
        return (left, top, round(left + span), bottom)
    span = (bottom - top) * fraction
    if side == "bottom":
        return (left, round(bottom - span), right, bottom)
    return (left, top, right, round(top + span))


def pixelate_region(img: Image.Image, box: tuple[int, int, int, int], block: int = 18
                     ) -> Image.Image:
    """Mosaic-pixelate box in place on a COPY of img (RGB). block is the
    mosaic cell size in source pixels."""
    left, top, right, bottom = box
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        return img
    out = img.copy()
    region = out.crop((left, top, right, bottom))
    small_w = max(1, w // block)
    small_h = max(1, h // block)
    region = region.resize((small_w, small_h), Image.BILINEAR).resize((w, h), Image.NEAREST)
    out.paste(region, (left, top))
    return out


def nine_sixteen_crop_around(box: tuple[int, int, int, int], img_w: int, img_h: int,
                              pad: float = 1.8) -> tuple[int, int, int, int]:
    """A 9:16 crop rect centered on box, padded by `pad`x the box's own size,
    clamped to the image. Used for evidence zoom stills / Ken-Burns end frames."""
    left, top, right, bottom = box
    bw, bh = right - left, bottom - top
    cx, cy = (left + right) / 2, (top + bottom) / 2
    target_ratio = 9 / 16

    half_h = max(bh, bw / target_ratio) * pad / 2
    half_w = half_h * target_ratio

    crop_left = cx - half_w
    crop_right = cx + half_w
    crop_top = cy - half_h
    crop_bottom = cy + half_h

    # shift back into frame before clamping size (keeps aspect ratio exact
    # unless the frame itself is smaller than the requested crop)
    if crop_left < 0:
        crop_right -= crop_left
        crop_left = 0
    if crop_right > img_w:
        crop_left -= (crop_right - img_w)
        crop_right = img_w
    if crop_top < 0:
        crop_bottom -= crop_top
        crop_top = 0
    if crop_bottom > img_h:
        crop_top -= (crop_bottom - img_h)
        crop_bottom = img_h

    crop_left = max(0, crop_left)
    crop_top = max(0, crop_top)
    crop_right = min(img_w, crop_right)
    crop_bottom = min(img_h, crop_bottom)
    return (round(crop_left), round(crop_top), round(crop_right), round(crop_bottom))


def region_box(box: tuple[int, int, int, int], top: float = 0.0, bottom: float = 1.0,
                left: float = 0.0, right: float = 1.0) -> tuple[int, int, int, int]:
    """A fractional sub-rect of box, e.g. the top 15% of a review card where
    an avatar + username sit -- used to censor PII inside a card whose exact
    avatar/username selector varies per broker/site, while the rest of the
    card (the complaint text, the evidence) stays untouched."""
    l, t, r, b = box
    w, h = r - l, b - t
    return (round(l + w * left), round(t + h * top), round(l + w * right), round(t + h * bottom))


def lerp_rect(r0: tuple[float, float, float, float], r1: tuple[float, float, float, float],
              t: float) -> tuple[float, float, float, float]:
    """Linear-interpolate a crop rect between r0 (t=0) and r1 (t=1). t is
    clamped to [0, 1]. Used for the Ken-Burns push-in clip."""
    t = max(0.0, min(1.0, t))
    return tuple(a + (b - a) * t for a, b in zip(r0, r1))


def shot_content_hash(shot: dict) -> str:
    """Deterministic hash of a shot's config, for resumability: a re-run
    with the same shot list skips shots whose stored hash still matches."""
    canonical = json.dumps(shot, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════
# Shot list model
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CensorRule:
    label: str
    kind: str = "full"          # "full" | "partial"
    selector: str | None = None  # comma-separated CSS candidates, first visible wins
    text: str | None = None      # substring to locate via smallest-containing-visible-element
    fraction: float = 0.4
    side: str = "right"
    min_w: float = 0
    min_h: float = 0
    ancestor: str | None = None   # "nearest_with_img" -- walk up to the nearest ancestor holding an <img>
    region: dict | None = None    # {"top","bottom","left","right"} fractions of the (possibly ancestor-walked) box

    @classmethod
    def from_dict(cls, d: dict) -> "CensorRule":
        return cls(
            label=d.get("label", d.get("selector") or d.get("text") or "?"),
            kind=d.get("kind", "full"),
            selector=d.get("selector"),
            text=d.get("text"),
            fraction=d.get("fraction", 0.4),
            side=d.get("side", "right"),
            min_w=d.get("min_w", 0),
            min_h=d.get("min_h", 0),
            ancestor=d.get("ancestor"),
            region=d.get("region"),
        )


@dataclass
class Shot:
    id: str
    url: str
    covers: list[str]
    action: str = "capture"     # "capture" | "scroll"
    kind: str = "still"         # "still" | "clip"
    duration: float = 0.0
    wait_selector: str | None = None
    wait_ms: int = 1200
    crop: dict | None = None    # {"selector"|"text": ..., "pad": 1.8, "min_w":..,"min_h":..}
    animate: bool = False
    scroll_to_frac: float = 0.6  # scroll shots: how far down the page to travel, 0..1
    censor: list[CensorRule] = field(default_factory=list)
    source_note: str | None = None
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict, profiles: dict[str, list[dict]]) -> "Shot":
        censor_dicts = list(d.get("censor") or [])
        for prof in d.get("censor_profiles") or []:
            censor_dicts += profiles.get(prof, [])
        return cls(
            id=d["id"],
            url=d["url"],
            covers=list(d["covers"]),
            action=d.get("action", "capture"),
            kind=d.get("kind", "still"),
            duration=float(d.get("duration", 0.0)),
            wait_selector=d.get("wait_selector"),
            wait_ms=int(d.get("wait_ms", 1200)),
            crop=d.get("crop"),
            animate=bool(d.get("animate", False)),
            scroll_to_frac=float(d.get("scroll_to_frac", 0.6)),
            censor=[CensorRule.from_dict(c) for c in censor_dicts],
            source_note=d.get("source_note"),
            note=d.get("note", ""),
        )

    def hashable(self) -> dict:
        return {
            "id": self.id, "url": self.url, "covers": self.covers, "action": self.action,
            "kind": self.kind, "duration": self.duration, "wait_selector": self.wait_selector,
            "wait_ms": self.wait_ms, "crop": self.crop, "animate": self.animate,
            "scroll_to_frac": self.scroll_to_frac,
            "censor": [c.__dict__ for c in self.censor],
        }


def load_shots(path: Path) -> tuple[list[Shot], dict]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    profiles = raw.get("censor_profiles", {}) or {}
    shots = [Shot.from_dict(s, profiles) for s in raw["shots"]]
    return shots, raw


# ═══════════════════════════════════════════════════════════════════════════
# Browser-side measurement JS (batched: one round trip per capture instant)
# ═══════════════════════════════════════════════════════════════════════════

MEASURE_JS = r"""
(targets) => {
  function visibleRect(el) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return null;
    return r;
  }
  function findByText(needle) {
    const stack = [document.body];
    let best = null, bestLen = Infinity;
    while (stack.length) {
      const el = stack.pop();
      if (el.children) for (const c of el.children) stack.push(c);
      const t = el.innerText || el.textContent || "";
      if (!t || !t.includes(needle)) continue;
      const r = visibleRect(el);
      if (!r) continue;
      if (t.length < bestLen) { best = el; bestLen = t.length; }
    }
    return best;
  }
  function findBySelectors(selCsv, minW, minH) {
    const sels = selCsv.split(",").map(s => s.trim()).filter(Boolean);
    for (const sel of sels) {
      let nodes;
      try { nodes = document.querySelectorAll(sel); } catch (e) { continue; }
      for (const el of nodes) {
        const r = visibleRect(el);
        if (r && r.width >= (minW || 0) && r.height >= (minH || 0)) return el;
      }
    }
    return null;
  }
  function walkToAncestorWithImg(el) {
    let cur = el;
    for (let i = 0; i < 10 && cur; i++) {
      if (cur.querySelector('img')) return cur;
      cur = cur.parentElement;
    }
    return el;
  }
  const scrollX = window.scrollX, scrollY = window.scrollY, dpr = window.devicePixelRatio || 1;
  const out = targets.map(t => {
    let el = null;
    if (t.text) el = findByText(t.text);
    else if (t.selector) el = findBySelectors(t.selector, t.min_w, t.min_h);
    if (!el) return { ok: false };
    if (t.ancestor === "nearest_with_img") el = walkToAncestorWithImg(el);
    const r = el.getBoundingClientRect();
    return { ok: true, x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height };
  });
  return { scrollX, scrollY, dpr, targets: out };
}
"""

BLOCKED_MARKERS = re.compile(
    r"just a moment|attention required|verify you are human|cf-browser-verification",
    re.I,
)


def is_blocked(page) -> bool:
    try:
        title = page.title() or ""
        snippet = page.content()[:2000]
    except Exception:
        return False
    return bool(BLOCKED_MARKERS.search(title + " " + snippet))


# ═══════════════════════════════════════════════════════════════════════════
# ffmpeg helpers
# ═══════════════════════════════════════════════════════════════════════════

def encode_frames_to_mp4(frame_glob: Path, in_fps: int, out_path: Path, out_fps: int = FPS) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-framerate", str(in_fps), "-i", str(frame_glob),
        "-vf", f"fps={out_fps},scale={FRAME_W}:{FRAME_H}:force_original_aspect_ratio=decrease,"
               f"pad={FRAME_W}:{FRAME_H}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-an", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def encode_static_image_to_mp4(image_path: Path, duration: float, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", str(duration), "-r", str(FPS),
        "-vf", f"scale={FRAME_W}:{FRAME_H}:force_original_aspect_ratio=decrease,"
               f"pad={FRAME_W}:{FRAME_H}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-an", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def ffprobe_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out or 0.0)


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

class RealFootageRunner:
    def __init__(self, episode: str, out_dir: Path, drive_real_prefix: str = "real"):
        self.episode = episode
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.out_dir / ".state.json"
        self.state: dict[str, dict] = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.drive_real_prefix = drive_real_prefix
        self.runlog_lines: list[str] = []

    # -- state / resumability -------------------------------------------------
    def outputs_exist(self, entry: dict) -> bool:
        for f in entry.get("outputs", []):
            if not (self.out_dir / f).exists():
                return False
        return True

    def save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    def build_manifest(self) -> list[dict]:
        entries: list[dict] = []
        for shot_id, rec in self.state.items():
            entries.extend(rec.get("manifest_entries", []))
        return entries

    # -- browser lifecycle ------------------------------------------------------
    def get_page(self, pw, use_cdp: bool):
        if use_cdp:
            browser = pw.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context(
                viewport={"width": FRAME_W, "height": FRAME_H})
            page = ctx.new_page()
            return browser, ctx, page
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": FRAME_W, "height": FRAME_H},
                                   locale="th-TH", device_scale_factor=1)
        page = ctx.new_page()
        return browser, ctx, page

    # -- one shot -----------------------------------------------------------
    def run_shot(self, page, shot: Shot) -> dict:
        page.goto(shot.url, wait_until="networkidle", timeout=30000)
        if shot.wait_selector:
            try:
                page.wait_for_selector(shot.wait_selector, timeout=8000)
            except Exception:
                pass
        page.wait_for_timeout(shot.wait_ms)

        if shot.action == "scroll":
            return self._run_scroll(page, shot)
        return self._run_capture(page, shot)

    def _measure(self, page, targets: list[dict]) -> dict:
        return page.evaluate(MEASURE_JS, targets)

    def _censor_image(self, img: Image.Image, censor_boxes: list[tuple[str, tuple, tuple]]
                       ) -> tuple[Image.Image, list[dict]]:
        censored_meta = []
        for rule, raw_box, applied_box in censor_boxes:
            if applied_box is None:
                continue
            img = pixelate_region(img, applied_box, block=18)
            censored_meta.append({"what": rule.label, "rule": f"{rule.kind}"
                                   + (f" {rule.fraction:.0%} {rule.side}" if rule.kind == "partial" else "")})
        return img, censored_meta

    def _resolve_censor_boxes(self, measured: dict, shot: Shot, crop_target_idx: int | None,
                               img_w: int, img_h: int):
        scroll = {"x": measured["scrollX"], "y": measured["scrollY"]}
        dpr = measured["dpr"]
        boxes = []
        for i, rule in enumerate(shot.censor):
            t = measured["targets"][i]
            if not t["ok"]:
                continue
            pixel_box = compute_censor_pixel_box(
                {"x": t["x"], "y": t["y"], "width": t["width"], "height": t["height"]}, scroll, dpr)
            if rule.kind == "partial":
                pixel_box = partial_box(pixel_box, rule.fraction, rule.side)
            elif rule.kind == "region" and rule.region:
                pixel_box = region_box(pixel_box, **rule.region)
            clamped = clamp_box(pixel_box, img_w, img_h)
            boxes.append((rule, pixel_box, clamped))
        crop_pixel_box = None
        if crop_target_idx is not None:
            t = measured["targets"][crop_target_idx]
            if t["ok"]:
                crop_pixel_box = compute_censor_pixel_box(
                    {"x": t["x"], "y": t["y"], "width": t["width"], "height": t["height"]}, scroll, dpr)
        return boxes, crop_pixel_box

    def _run_capture(self, page, shot: Shot) -> dict:
        targets = [{"selector": r.selector, "text": r.text, "min_w": r.min_w, "min_h": r.min_h,
                    "ancestor": r.ancestor} for r in shot.censor]
        crop_idx = None
        if shot.crop:
            crop_idx = len(targets)
            targets.append({"selector": shot.crop.get("selector"), "text": shot.crop.get("text"),
                             "min_w": shot.crop.get("min_w", 0), "min_h": shot.crop.get("min_h", 0)})

        measured = self._measure(page, targets) if targets else {"scrollX": 0, "scrollY": 0, "dpr": 1, "targets": []}
        png_bytes = page.screenshot(type="png")
        shot_dir = self.out_dir / shot.id
        shot_dir.mkdir(parents=True, exist_ok=True)
        raw_path = shot_dir / "raw.png"
        raw_path.write_bytes(png_bytes)

        img = Image.open(raw_path).convert("RGB")
        censor_boxes, crop_box = self._resolve_censor_boxes(measured, shot, crop_idx, img.width, img.height)
        img, censored_meta = self._censor_image(img, censor_boxes)

        outputs = []
        manifest_entries = []
        captured_at = datetime.now(TH_TZ).isoformat(timespec="seconds")

        final_crop = None
        if shot.crop and crop_box is not None:
            final_crop = nine_sixteen_crop_around(crop_box, img.width, img.height,
                                                   shot.crop.get("pad", 1.8))

        end_frame = img.crop(final_crop) if final_crop else img
        end_frame = end_frame.resize((FRAME_W, FRAME_H), Image.LANCZOS)

        still_path = shot_dir / f"{shot.id}.png"
        end_frame.save(still_path)
        outputs.append(str(still_path.relative_to(self.out_dir)))
        manifest_entries.append({
            "file": f"{self.drive_real_prefix}/{shot.id}.png", "kind": "still",
            "covers": shot.covers, "source_url": shot.url, "captured_at": captured_at,
            "seconds": 0, "censored": censored_meta,
        })

        if shot.kind == "clip" and shot.duration > 0:
            clip_path = shot_dir / f"{shot.id}.mp4"
            if shot.animate and final_crop:
                full_rect = (0, 0, img.width, img.height)
                frame_dir = shot_dir / "kb_frames"
                if frame_dir.exists():
                    shutil.rmtree(frame_dir)
                frame_dir.mkdir(parents=True)
                in_fps = 10
                n_frames = max(1, int(shot.duration * in_fps))
                for i in range(n_frames):
                    t = i / max(1, n_frames - 1)
                    ease = t * t * (3 - 2 * t)  # smoothstep push-in
                    rect = lerp_rect(full_rect, final_crop, ease)
                    rect_i = tuple(round(v) for v in rect)
                    frame = img.crop(rect_i).resize((FRAME_W, FRAME_H), Image.LANCZOS)
                    frame.save(frame_dir / f"f_{i:04d}.png")
                encode_frames_to_mp4(frame_dir / "f_%04d.png", in_fps, clip_path)
                shutil.rmtree(frame_dir)
            else:
                encode_static_image_to_mp4(still_path, shot.duration, clip_path)
            outputs.append(str(clip_path.relative_to(self.out_dir)))
            manifest_entries.append({
                "file": f"{self.drive_real_prefix}/{shot.id}.mp4", "kind": "clip",
                "covers": shot.covers, "source_url": shot.url, "captured_at": captured_at,
                "seconds": round(shot.duration, 1), "censored": censored_meta,
            })

        return {"outputs": outputs, "manifest_entries": manifest_entries,
                "crop_missing": bool(shot.crop and final_crop is None)}

    def _run_scroll(self, page, shot: Shot) -> dict:
        shot_dir = self.out_dir / shot.id
        frame_dir = shot_dir / "frames"
        if frame_dir.exists():
            shutil.rmtree(frame_dir)
        frame_dir.mkdir(parents=True)

        page_height = page.evaluate("document.body.scrollHeight")
        target_y = max(0, int((page_height - FRAME_H) * shot.scroll_to_frac))
        in_fps = 8
        n_frames = max(1, int(shot.duration * in_fps))
        targets = [{"selector": r.selector, "text": r.text, "min_w": r.min_w, "min_h": r.min_h,
                    "ancestor": r.ancestor} for r in shot.censor]
        all_censored_meta: dict[str, dict] = {}

        for i in range(n_frames):
            t = i / max(1, n_frames - 1)
            ease = t * t * (3 - 2 * t)
            y = round(target_y * ease)
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(120)  # let lazy-loaded content settle before measuring/shooting

            measured = self._measure(page, targets) if targets else {"scrollX": 0, "scrollY": y, "dpr": 1, "targets": []}
            png_bytes = page.screenshot(type="png")
            img = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGB")
            censor_boxes, _ = self._resolve_censor_boxes(measured, shot, None, img.width, img.height)
            img, censored_meta = self._censor_image(img, censor_boxes)
            for m in censored_meta:
                all_censored_meta[m["what"]] = m
            img.save(frame_dir / f"f_{i:04d}.png")

        clip_path = shot_dir / f"{shot.id}.mp4"
        encode_frames_to_mp4(frame_dir / "f_%04d.png", in_fps, clip_path)
        shutil.rmtree(frame_dir)

        captured_at = datetime.now(TH_TZ).isoformat(timespec="seconds")
        outputs = [str(clip_path.relative_to(self.out_dir))]
        manifest_entries = [{
            "file": f"{self.drive_real_prefix}/{shot.id}.mp4", "kind": "clip",
            "covers": shot.covers, "source_url": shot.url, "captured_at": captured_at,
            "seconds": round(shot.duration, 1), "censored": list(all_censored_meta.values()),
        }]
        return {"outputs": outputs, "manifest_entries": manifest_entries, "crop_missing": False}

    # -- top level ------------------------------------------------------------
    def run_all(self, shots: list[Shot], pw, use_cdp: bool) -> None:
        browser, ctx, page = self.get_page(pw, use_cdp)
        try:
            for shot in shots:
                h = shot_content_hash(shot.hashable())
                prior = self.state.get(shot.id)
                if prior and prior.get("hash") == h and self.outputs_exist(prior):
                    self._log(f"SKIP {shot.id} (unchanged, outputs present)")
                    continue
                try:
                    result = self.run_shot(page, shot)
                    self.state[shot.id] = {"hash": h, **result}
                    self.save_state()
                    status = "ok" if not result.get("crop_missing") else "ok (crop target not found, used full frame)"
                    self._log(f"{shot.id} {status} -> {', '.join(result['outputs'])}")
                except Exception as e:
                    self._log(f"{shot.id} FAIL {type(e).__name__}: {e}")
        finally:
            try:
                ctx.close()
            except Exception:
                pass
            if not use_cdp:
                browser.close()

    def _log(self, line: str) -> None:
        stamp = datetime.now(TH_TZ).isoformat(timespec="seconds")
        entry = f"{stamp} | {line}"
        print(entry)
        self.runlog_lines.append(entry)

    def flush_runlog(self, runlog_path: Path) -> None:
        with open(runlog_path, "a", encoding="utf-8") as f:
            for line in self.runlog_lines:
                f.write(line + "\n")
        self.runlog_lines = []


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def cmd_run(args) -> int:
    shots_path = Path(args.shots)
    shots, raw = load_shots(shots_path)
    covers_seen = {c for s in shots for c in s.covers}
    print(f"loaded {len(shots)} shots covering {len(covers_seen)} tags")

    if args.dry_run:
        for s in shots:
            print(f"  [{s.id}] action={s.action} kind={s.kind} url={s.url} covers={s.covers}")
        return 0

    out_dir = Path(args.out) if args.out else DEFAULT_OUT_ROOT / args.episode
    runner = RealFootageRunner(args.episode, out_dir)

    from playwright.sync_api import sync_playwright
    use_cdp = args.cdp
    with sync_playwright() as pw:
        if not use_cdp:
            try:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(viewport={"width": FRAME_W, "height": FRAME_H}, locale="th-TH")
                probe = ctx.new_page()
                probe.goto(shots[0].url, wait_until="domcontentloaded", timeout=20000)
                probe.wait_for_timeout(1500)
                blocked = is_blocked(probe)
                ctx.close()
                browser.close()
                if blocked:
                    print(f"BLOCKED headless on {shots[0].url} -- retry with --cdp against a "
                          f"launched automation Chrome (scripts/bl_realfootage/launch-chrome-debug.sh)")
                    return 2
            except Exception as e:
                print(f"probe failed: {e!r} -- continuing with headless run")
        runner.run_all(shots, pw, use_cdp)

    manifest = runner.build_manifest()
    missing = covers_seen - {c for e in manifest for c in e["covers"]}
    manifest_path = Path(args.manifest) if args.manifest else out_dir / "REAL_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {manifest_path} ({len(manifest)} entries)")
    if missing:
        print(f"WARNING: tags with no footage: {sorted(missing)}")

    if args.runlog:
        runner.flush_runlog(Path(args.runlog))

    return 0 if not missing else 1


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="capture every shot in a shot list")
    run.add_argument("--shots", required=True, help="path to shots.yaml/json")
    run.add_argument("--episode", required=True, help="episode id, e.g. bl55")
    run.add_argument("--out", help="output dir (default output/bl-realfootage/<episode>)")
    run.add_argument("--manifest", help="REAL_MANIFEST.json path (default <out>/REAL_MANIFEST.json)")
    run.add_argument("--runlog", help="RUNLOG.md path to append shot-by-shot progress to")
    run.add_argument("--cdp", action="store_true",
                      help="attach to a dedicated automation Chrome over CDP instead of headless")
    run.add_argument("--dry-run", action="store_true", help="print resolved shots, capture nothing")
    run.set_defaults(func=cmd_run)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
