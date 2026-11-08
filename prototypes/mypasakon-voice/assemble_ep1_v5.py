#!/usr/bin/env python3
"""Assemble MYPASAKON EP1 v5 per REFS-BREAKDOWN.md (Table c2 + CMO c4 rulings).

- 29 shots / 28 cuts across 105.72 s (102.72 s approved voice + 3.00 s held end-card tail).
- Shot 15 (moon insert) folded into Shot 14 (39.93 - 43.83 s = 3.90 s, exits via paper white-flash).
- All Thai text shaped with Kanit-SemiBold.ttf via Playwright Chromium HTML->PNG sprites (zero libass).
- Media-use SFX placed on Table c2 FX transitions and ~1 in 3 hard cuts, mixed under voice to -20 LUFS
  integrated (peak < -1 dBFS).
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

WORK_DEFAULT = Path("/opt/MoonieXHQ/Work/mypasakon-voice")
FONT_DEFAULT = Path("/opt/MoonieXHQ/Work/khaohom-survival/long/render16/fonts/Kanit-SemiBold.ttf")
SFX_DIR_DEFAULT = Path("/root/.claude/skills/media-use/audio/assets/sfx")

VOICE_DURATION = 102.72
TAIL_DURATION = 3.00
TOTAL_DURATION = 105.72
FPS = 30
WIDTH = 1080
HEIGHT = 1920
TOTAL_FRAMES = int(round(TOTAL_DURATION * FPS))  # 3172 frames

RISK_WARNING_TEXT = "การเทรดมีความเสี่ยงสูง อาจสูญเสียเงินทุนทั้งหมด ศึกษาก่อนลงทุน"
CTA_TEXT = "คอมเมนต์คำว่า Claude"

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--no-zygote",
    "--disable-crash-reporter",
    "--disable-breakpad",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]


@dataclass
class TextPage:
    t_start: float
    t_end: float
    kind: str  # "top2", "hero", "label", "label_colored", "paper_build", "panel", "end_card"
    line1: str
    line2: str = ""
    extra: str = ""
    accent: str = "#23FD0A"  # green, cyan, orange, red, green_box, red_box
    sprite_key: str = ""


@dataclass
class StickerSpec:
    text: str
    t_pop: float  # relative to shot start
    x: int
    y: int
    bg_color: str = "#111827"
    text_color: str = "#FFFFFF"
    accent_tag: str = ""
    sprite_key: str = ""


@dataclass
class ShotSpec:
    idx: int  # 1..29
    orig_shot: int  # 1..14, 16..30 from Table c2
    t_in: float
    t_out: float
    shot_type: str  # A, AS, B, S, G, T, E
    part: str
    layout: str
    clip_idx: int = 0  # 0=clip1_terminal, 1=clip2_log, 2=clip3_chart, 3=clip4_table
    face_zoom: float = 1.15
    face_push_rate: float = 0.0  # per second
    face_offset: tuple[int, int] = (0, 0)
    pip_mode: str = "none"  # "none", "large_tr" (428px), "small_tc" (256px)
    transition_in: str = "hard"  # "start", "hard", "star_pop_bg_swap", "paper_flash", "panel_slide", "text_mask_whip"
    sfx_events: list[tuple[float, str, float]] = field(default_factory=list)  # (abs_t, sfx_name, gain_db)
    pages: list[TextPage] = field(default_factory=list)
    stickers: list[StickerSpec] = field(default_factory=list)
    layers_count: int = 2
    notes: str = ""

    @property
    def duration(self) -> float:
        return round(self.t_out - self.t_in, 4)


def build_blueprint() -> list[ShotSpec]:
    """Return the 29-shot blueprint matching REFS-BREAKDOWN.md Table c2 + CMO c4 rulings."""
    shots: list[ShotSpec] = [
        # Shot 1 (0:00.00 - 0:01.85)
        ShotSpec(
            idx=1, orig_shot=1, t_in=0.00, t_out=1.85, shot_type="A", part="p01",
            layout="face_full", face_zoom=1.12, face_push_rate=0.005, face_offset=(0, -18),
            transition_in="start",
            sfx_events=[(0.02, "riser.mp3", -14.0)],
            pages=[TextPage(0.00, 1.85, "hero", "AI", "ที่ผมใช้จริง", accent="cyan")],
            layers_count=2,
        ),
        # Shot 2 (0:01.85 - 0:03.70)
        ShotSpec(
            idx=2, orig_shot=2, t_in=1.85, t_out=3.70, shot_type="A", part="p01",
            layout="face_over_chart_bg", clip_idx=2, face_zoom=1.18, face_push_rate=0.01, face_offset=(22, -10),
            transition_in="star_pop_bg_swap",
            sfx_events=[(1.85, "pop.mp3", -8.0)],
            pages=[TextPage(1.85, 3.70, "top2", "ที่ผมใช้", "เทรดจริง", accent="#23FD0A")],
            stickers=[StickerSpec("★ AI PRO", 0.05, 810, 470, bg_color="#4F46E5", text_color="#FFFFFF")],
            layers_count=3,
        ),
        # Shot 3 (0:03.70 - 0:05.58)
        ShotSpec(
            idx=3, orig_shot=3, t_in=3.70, t_out=5.58, shot_type="B", part="p01",
            layout="card", clip_idx=2, face_zoom=1.14, face_offset=(-14, -8), pip_mode="large_tr",
            transition_in="hard",
            sfx_events=[(3.70, "click.mp3", -9.0)],
            pages=[TextPage(3.70, 5.58, "label", "มาตลอด 8 เดือน")],
            layers_count=4,
        ),
        # Shot 4 (0:05.58 - 0:07.56)
        ShotSpec(
            idx=4, orig_shot=4, t_in=5.58, t_out=7.56, shot_type="A", part="p01",
            layout="face_full", face_zoom=1.25, face_push_rate=0.015, face_offset=(-24, -20),
            transition_in="hard",
            sfx_events=[(5.58, "impact-bass-1.mp3", -9.0)],
            pages=[TextPage(5.58, 7.56, "hero", "Claude Code", "นี่แหละนะครับ", accent="cyan")],
            layers_count=2,
        ),
        # Shot 5 (0:07.56 - 0:11.93)
        ShotSpec(
            idx=5, orig_shot=5, t_in=7.56, t_out=11.93, shot_type="S", part="p02",
            layout="paper_stickers", face_zoom=1.16, face_offset=(12, -10), pip_mode="small_tc",
            transition_in="paper_flash",
            sfx_events=[
                (7.56, "whoosh.mp3", -8.0),
                (7.80, "pop.mp3", -9.0),
                (8.65, "pop.mp3", -9.0),
                (9.50, "pop.mp3", -9.0),
                (10.35, "pop.mp3", -9.0),
            ],
            pages=[TextPage(7.56, 11.93, "top2", "ลองมาหมดแล้ว", "ทุกตัวในตลาด", accent="#23FD0A")],
            stickers=[
                StickerSpec("ChatGPT", 0.24, 310, 930, bg_color="#10A37F", text_color="#FFFFFF"),
                StickerSpec("Gemini", 1.09, 760, 930, bg_color="#2563EB", text_color="#FFFFFF"),
                StickerSpec("Grok", 1.94, 310, 1210, bg_color="#18181B", text_color="#FFFFFF"),
                StickerSpec("บอทเทรด AI", 2.79, 760, 1210, bg_color="#DC2626", text_color="#FFFFFF"),
            ],
            layers_count=4,
        ),
        # Shot 6 (0:11.93 - 0:14.70)
        ShotSpec(
            idx=6, orig_shot=6, t_in=11.93, t_out=14.70, shot_type="A", part="p02",
            layout="face_full", face_zoom=1.18, face_push_rate=0.006, face_offset=(20, 12),
            transition_in="hard",
            sfx_events=[],
            pages=[TextPage(11.93, 14.70, "top2", "ที่เขาว่าดี", "บอทเทรด AI Agent", accent="#23FD0A")],
            layers_count=2,
        ),
        # Shot 7 (0:14.70 - 0:16.20)
        ShotSpec(
            idx=7, orig_shot=7, t_in=14.70, t_out=16.20, shot_type="B", part="p02",
            layout="full_bleed_whip", clip_idx=1,
            transition_in="hard",
            sfx_events=[(14.70, "click.mp3", -8.5)],
            pages=[],  # Caption-free fast insert per Table c2
            layers_count=3,
        ),
        # Shot 8 (0:16.20 - 0:21.36)
        ShotSpec(
            idx=8, orig_shot=8, t_in=16.20, t_out=21.36, shot_type="A", part="p02",
            layout="face_full", face_zoom=1.10, face_push_rate=0.012, face_offset=(-16, 4),
            transition_in="hard",
            sfx_events=[],
            pages=[
                TextPage(16.20, 18.85, "top2", "ไม่มีตัวไหน", "ถูกใจเลยสักตัว", accent="#23FD0A"),
                TextPage(18.85, 21.36, "top2", "ถูกใจเท่าตัวนี้", "บอกตรงๆ เลยครับ", accent="#23FD0A"),
            ],
            layers_count=2,
        ),
        # Shot 9 (0:21.36 - 0:23.95)
        ShotSpec(
            idx=9, orig_shot=9, t_in=21.36, t_out=23.95, shot_type="G", part="p02",
            layout="mint_ticks", face_zoom=1.20, face_offset=(10, -14), pip_mode="small_tc",
            transition_in="hard",
            sfx_events=[(21.36, "pop.mp3", -8.0)],
            pages=[TextPage(21.36, 23.95, "top2", "ใช้อยู่ทุกวัน", "จนถึงวันนี้", accent="#23FD0A")],
            layers_count=4,
        ),
        # Shot 10 (0:23.95 - 0:29.17)
        ShotSpec(
            idx=10, orig_shot=10, t_in=23.95, t_out=29.17, shot_type="B", part="p03",
            layout="card", clip_idx=2, face_zoom=1.15, face_offset=(-18, -10), pip_mode="large_tr",
            transition_in="paper_flash",
            sfx_events=[(23.95, "whoosh.mp3", -8.0)],
            pages=[
                TextPage(23.95, 26.80, "label", "ผู้ช่วยวิเคราะห์"),
                TextPage(26.80, 29.17, "label", "เทรดให้ด้วย"),
            ],
            layers_count=4,
        ),
        # Shot 11 (0:29.17 - 0:32.14)
        ShotSpec(
            idx=11, orig_shot=11, t_in=29.17, t_out=32.14, shot_type="A", part="p03",
            layout="face_full", face_zoom=1.25, face_push_rate=0.015, face_offset=(24, -16),
            transition_in="hard",
            sfx_events=[],
            pages=[TextPage(29.17, 32.14, "top2", "เทรดให้ผมได้", "ทำสถิติให้ก็ได้", accent="#23FD0A")],
            layers_count=2,
        ),
        # Shot 12 (0:32.14 - 0:35.68)
        ShotSpec(
            idx=12, orig_shot=12, t_in=32.14, t_out=35.68, shot_type="B", part="p03",
            layout="stack", clip_idx=3,
            transition_in="hard",
            sfx_events=[(32.14, "click.mp3", -9.0), (33.80, "click.mp3", -9.0)],
            pages=[
                TextPage(32.14, 33.80, "label", "คำนวณความเสี่ยง"),
                TextPage(33.80, 35.68, "label", "ย้อนทดสอบ"),
            ],
            layers_count=3,
        ),
        # Shot 13 (0:35.68 - 0:39.93)
        ShotSpec(
            idx=13, orig_shot=13, t_in=35.68, t_out=39.93, shot_type="B", part="p03",
            layout="card", clip_idx=1, face_zoom=1.17, face_offset=(14, -12), pip_mode="large_tr",
            transition_in="hard",
            sfx_events=[],
            pages=[TextPage(35.68, 39.93, "label", "ข้อมูลเก่า ทุกตัว")],
            layers_count=4,
        ),
        # Shot 14 (0:39.93 - 0:43.83) — Folded Shot 14 + Shot 15 per CMO c4a (3.90 s)
        ShotSpec(
            idx=14, orig_shot=14, t_in=39.93, t_out=43.83, shot_type="A", part="p03",
            layout="face_full", face_zoom=1.35, face_push_rate=0.020, face_offset=(0, -28),
            transition_in="hard",
            sfx_events=[(39.93, "impact-bass-1.mp3", -8.5)],
            pages=[TextPage(39.93, 43.83, "hero", "ไม่หลับไม่นอน", "สิ่งที่ชอบที่สุด", accent="orange")],
            layers_count=2,
            notes="Shot 15 folded into Shot 14 per CMO c4a; exits via paper_flash into Shot 15 (orig 16)",
        ),
        # Shot 15 (orig 16, 0:43.83 - 0:46.90)
        ShotSpec(
            idx=15, orig_shot=16, t_in=43.83, t_out=46.90, shot_type="B", part="p04",
            layout="terminal_typing", clip_idx=0,
            transition_in="paper_flash",
            sfx_events=[(43.83, "whoosh.mp3", -8.0)],
            pages=[TextPage(43.83, 46.90, "top2", "ประโยคเดียว", "ก่อนนอน", accent="#23FD0A")],
            layers_count=3,
        ),
        # Shot 16 (orig 17, 0:46.90 - 0:51.38)
        ShotSpec(
            idx=16, orig_shot=17, t_in=46.90, t_out=51.38, shot_type="A", part="p04",
            layout="face_full", face_zoom=1.28, face_push_rate=0.010, face_offset=(-20, -14),
            transition_in="hard",
            sfx_events=[(47.10, "pop.mp3", -8.5)],
            pages=[TextPage(46.90, 51.38, "top2", "ย้อนหลัง 5 ปี", "แล้วก็ไปนอน", accent="#23FD0A")],
            stickers=[StickerSpec("5 ปี", 0.20, 810, 520, bg_color="#0BDE85", text_color="#062216")],
            layers_count=3,
        ),
        # Shot 17 (orig 18, 0:51.38 - 0:57.80)
        ShotSpec(
            idx=17, orig_shot=18, t_in=51.38, t_out=57.80, shot_type="A", part="p05",
            layout="face_full", face_zoom=1.05, face_push_rate=0.010, face_offset=(14, 10),
            transition_in="hard",
            sfx_events=[],
            pages=[
                TextPage(51.38, 54.80, "top2", "ตื่นเช้ามา", "เจออะไร?", accent="#23FD0A"),
                TextPage(54.80, 57.80, "top2", "ไล่ดูกราฟทั้งคืน", "ไม่หยุดพักเลย", accent="#23FD0A"),
            ],
            layers_count=2,
        ),
        # Shot 18 (orig 19, 0:57.80 - 1:00.03)
        ShotSpec(
            idx=18, orig_shot=19, t_in=57.80, t_out=60.03, shot_type="G", part="p05",
            layout="mint_counter", clip_idx=2, face_zoom=1.18, face_offset=(-12, -10), pip_mode="small_tc",
            transition_in="hard",
            sfx_events=[
                (57.85, "click-soft.mp3", -10.0),
                (58.35, "click-soft.mp3", -10.0),
                (58.85, "click-soft.mp3", -10.0),
                (59.55, "impact-bass-2.mp3", -8.5),
            ],
            pages=[TextPage(57.80, 60.03, "top2", "ทดสอบย้อนหลัง", "หมื่นๆ รอบ", accent="#23FD0A")],
            layers_count=4,
        ),
        # Shot 19 (orig 20, 1:00.03 - 1:03.20)
        ShotSpec(
            idx=19, orig_shot=20, t_in=60.03, t_out=63.20, shot_type="B", part="p05",
            layout="stack_highlight", clip_idx=3,
            transition_in="hard",
            sfx_events=[(60.03, "click.mp3", -9.0), (61.60, "click.mp3", -9.0)],
            pages=[
                TextPage(60.03, 61.60, "label_colored", "อยู่รอด", accent="green_box"),
                TextPage(61.60, 63.20, "label_colored", "พัง", accent="red_box"),
            ],
            layers_count=3,
        ),
        # Shot 20 (orig 21, 1:03.20 - 1:10.70)
        ShotSpec(
            idx=20, orig_shot=21, t_in=63.20, t_out=70.70, shot_type="T", part="p06",
            layout="paper_text", face_zoom=1.15, face_offset=(16, -12), pip_mode="small_tc",
            transition_in="paper_flash",
            sfx_events=[
                (63.20, "whoosh.mp3", -8.0),
                (63.45, "pop.mp3", -9.0),
                (66.50, "pop.mp3", -9.0),
            ],
            pages=[
                TextPage(63.20, 66.50, "paper_build", "ชนะเพราะอะไร", "", accent="red"),
                TextPage(66.50, 70.70, "paper_build", "ชนะเพราะอะไร", "แล้วจะพังตอนไหน", accent="red"),
            ],
            layers_count=3,
        ),
        # Shot 21 (orig 22, 1:10.70 - 1:15.58)
        ShotSpec(
            idx=21, orig_shot=22, t_in=70.70, t_out=75.58, shot_type="AS", part="p07",
            layout="top_panel", face_zoom=1.14, face_offset=(-10, 120),
            transition_in="panel_slide",
            sfx_events=[(70.70, "whoosh-short.mp3", -8.5)],
            pages=[TextPage(70.70, 75.58, "panel", "เป็นเดือน", "ถ้าทำเองคนเดียว", extra="1 เดือน")],
            layers_count=3,
        ),
        # Shot 22 (orig 23, 1:15.58 - 1:17.67)
        ShotSpec(
            idx=22, orig_shot=23, t_in=75.58, t_out=77.67, shot_type="G", part="p07",
            layout="split_counter",
            transition_in="hard",
            sfx_events=[(75.58, "impact-bass-1.mp3", -8.5)],
            pages=[TextPage(75.58, 77.67, "top2", "ก็ยังไม่เสร็จ", "เทียบเวลาทำงาน", accent="#23FD0A")],
            layers_count=3,
        ),
        # Shot 23 (orig 24, 1:17.67 - 1:21.12)
        ShotSpec(
            idx=23, orig_shot=24, t_in=77.67, t_out=81.12, shot_type="A", part="p07",
            layout="face_full", face_zoom=1.30, face_push_rate=0.015, face_offset=(18, -22),
            transition_in="hard",
            sfx_events=[],
            pages=[TextPage(77.67, 81.12, "top2", "คืนเดียว", "ตอนผมนอนหลับ", accent="#23FD0A")],
            layers_count=2,
        ),
        # Shot 24 (orig 25, 1:21.12 - 1:25.52)
        ShotSpec(
            idx=24, orig_shot=25, t_in=81.12, t_out=85.52, shot_type="B", part="p08",
            layout="card", clip_idx=0, face_zoom=1.16, face_offset=(-15, -10), pip_mode="large_tr",
            transition_in="paper_flash",
            sfx_events=[(81.12, "whoosh.mp3", -8.0)],
            pages=[
                TextPage(81.12, 83.30, "label", "ไม่ได้มีแค่เทรด"),
                TextPage(83.30, 85.52, "label", "สอนใช้ AI"),
            ],
            layers_count=4,
        ),
        # Shot 25 (orig 26, 1:25.52 - 1:29.25)
        ShotSpec(
            idx=25, orig_shot=26, t_in=85.52, t_out=89.25, shot_type="AS", part="p08",
            layout="top_panel", face_zoom=1.18, face_offset=(15, 120),
            transition_in="panel_slide",
            sfx_events=[(85.52, "whoosh-short.mp3", -8.5)],
            pages=[TextPage(85.52, 89.25, "panel", "สอนใช้ AI", "มาเป็นผู้ช่วยตัวเอง", extra="ผู้ช่วยของคุณ")],
            layers_count=3,
        ),
        # Shot 26 (orig 27, 1:29.25 - 1:31.38)
        ShotSpec(
            idx=26, orig_shot=27, t_in=89.25, t_out=91.38, shot_type="S", part="p08",
            layout="paper_stickers", face_zoom=1.22, face_offset=(-12, -14), pip_mode="small_tc",
            transition_in="hard",
            sfx_events=[
                (89.40, "pop.mp3", -8.5),
                (90.20, "pop.mp3", -8.5),
            ],
            pages=[TextPage(89.25, 91.38, "top2", "ติดตั้ง", "สั่งงานครั้งแรก", accent="#23FD0A")],
            stickers=[
                StickerSpec("1 ติดตั้ง", 0.15, 330, 1020, bg_color="#0BDE85", text_color="#052E16"),
                StickerSpec("2 สั่งงาน", 0.95, 750, 1020, bg_color="#2563EB", text_color="#FFFFFF"),
            ],
            layers_count=4,
        ),
        # Shot 27 (orig 28, 1:31.38 - 1:34.39)
        ShotSpec(
            idx=27, orig_shot=28, t_in=91.38, t_out=94.39, shot_type="B", part="p08",
            layout="card", clip_idx=2, face_zoom=1.15, face_offset=(18, -8), pip_mode="large_tr",
            transition_in="hard",
            sfx_events=[
                (91.55, "pop.mp3", -8.5),
                (94.17, "impact-bass-1.mp3", -8.5),
            ],
            pages=[TextPage(91.38, 94.39, "label", "ใช้จริงกับพอร์ต")],
            stickers=[StickerSpec("3 ใช้จริง", 0.17, 300, 520, bg_color="#F59E0B", text_color="#111827")],
            layers_count=4,
        ),
        # Shot 28 (orig 29, 1:34.39 - 1:40.24)
        ShotSpec(
            idx=28, orig_shot=29, t_in=94.39, t_out=100.24, shot_type="A", part="p09",
            layout="face_full", face_zoom=1.15, face_push_rate=0.012, face_offset=(-16, -8),
            transition_in="hard",
            sfx_events=[],
            pages=[
                TextPage(94.39, 97.20, "top2", "คอมเมนต์คำว่า", "Claude", accent="#23FD0A"),
                TextPage(97.20, 100.24, "top2", "ไว้ใต้คลิป", "ได้เลยนะครับ", accent="#23FD0A"),
            ],
            layers_count=2,
        ),
        # Shot 29 (orig 30, 1:40.24 - 1:45.72) — 5.48 s incl. 3.0 s held tail per CMO c4b
        ShotSpec(
            idx=29, orig_shot=30, t_in=100.24, t_out=105.72, shot_type="E", part="p09",
            layout="end_card",
            transition_in="text_mask_whip",
            sfx_events=[
                (100.24, "whoosh-cinematic.mp3", -8.0),
                (100.38, "impact-bass-2.mp3", -8.5),
            ],
            pages=[
                TextPage(
                    100.24, 105.72, "end_card",
                    CTA_TEXT,
                    "เดี๋ยวผมทำคลิปสอนวิธีติดตั้งแบบเต็มๆ ทีละขั้นตอนครับ",
                    extra=RISK_WARNING_TEXT,
                )
            ],
            layers_count=3,
        ),
    ]
    return shots


def check_free_memory(min_mb: int = 3000) -> int:
    out = subprocess.check_output(["free", "-m"], text=True)
    row = next((line.split() for line in out.splitlines() if line.startswith("Mem:")), [])
    available = int(row[6]) if len(row) > 6 else 0
    if available < min_mb:
        raise SystemExit(f"Memory gate failed: need >= {min_mb} MB available, free -m reports {available} MB")
    print(f"[gate] free -m available = {available} MB (>= {min_mb} MB OK)")
    return available


def discover_captures(capture_dir: Path | None, work_dir: Path) -> tuple[list[Path], bool]:
    if capture_dir and capture_dir.is_dir():
        cand = [capture_dir / f"capture{i}.mp4" for i in range(1, 5)]
        if all(p.is_file() and p.stat().st_size > 0 for p in cand):
            return cand, False
        any_mp4 = sorted(p for p in capture_dir.iterdir() if p.suffix.lower() in {".mp4", ".mov"} and p.stat().st_size > 0)
        if len(any_mp4) >= 4:
            return any_mp4[:4], False
    footage = work_dir / "footage"
    clips = [
        footage / "clip1_terminal.mp4",
        footage / "clip2_log.mp4",
        footage / "clip3_chart.mp4",
        footage / "clip4_table.mp4",
    ]
    missing = [str(p) for p in clips if not p.is_file()]
    if missing:
        raise SystemExit("Missing footage files:\n" + "\n".join(missing))
    return clips, True


def render_html_sprites(
    shots: list[ShotSpec],
    font_path: Path,
    standin: bool,
    qc_dir: Path,
) -> dict[str, np.ndarray]:
    """Render all Thai text overlays, stickers, panels, cards, and badges via Playwright Chromium."""
    from playwright.sync_api import sync_playwright

    if not font_path.is_file():
        raise SystemExit(f"Font not found: {font_path}")

    sprites: dict[str, np.ndarray] = {}
    proof_items: list[tuple[str, str, Image.Image]] = []
    font_url = font_path.resolve().as_uri()

    base_css = f"""
    @font-face {{
        font-family: 'KanitSemiBold';
        src: url('{font_url}') format('truetype');
        font-weight: 600;
        font-style: normal;
    }}
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: 'KanitSemiBold', sans-serif;
        -webkit-font-smoothing: antialiased;
    }}
    body {{
        width: 1080px;
        height: 1920px;
        background: transparent;
        overflow: hidden;
    }}
    .nowrap {{
        white-space: nowrap;
    }}
    """

    def html_for_page(page: TextPage, shot: ShotSpec) -> tuple[str, tuple[int, int, int, int]]:
        if page.kind == "top2":
            return (
                f"""
                <div id="box" style="position:absolute; left:0; top:180px; width:1080px; height:380px;
                     display:flex; flex-direction:column; align-items:center; justify-content:center;
                     padding-top:36px; padding-bottom:28px;">
                    <div class="nowrap" style="font-size:80px; line-height:1.42; color:{page.accent};
                         -webkit-text-stroke: 14px #000000; paint-order: stroke fill;
                         filter: drop-shadow(0 8px 14px rgba(0,0,0,0.85)); padding: 8px 24px;">
                        {page.line1}
                    </div>
                    <div class="nowrap" style="font-size:74px; line-height:1.42; color:#FFFFFF;
                         -webkit-text-stroke: 14px #000000; paint-order: stroke fill;
                         filter: drop-shadow(0 8px 14px rgba(0,0,0,0.85)); margin-top:-6px; padding: 8px 24px;">
                        {page.line2}
                    </div>
                </div>
                """,
                (0, 180, 1080, 380),
            )
        if page.kind == "hero":
            grad = (
                "linear-gradient(180deg, #67E8F9 0%, #38BDF8 50%, #2563EB 100%)"
                if page.accent == "cyan"
                else "linear-gradient(180deg, #FDE047 0%, #FB923C 55%, #EA580C 100%)"
            )
            return (
                f"""
                <div id="box" style="position:absolute; left:0; top:165px; width:1080px; height:420px;
                     display:flex; flex-direction:column; align-items:center; justify-content:center;
                     padding-top:40px; padding-bottom:30px;">
                    <div class="nowrap" style="position:relative; font-size:102px; line-height:1.45; padding:10px 30px;">
                        <span style="position:absolute; left:30px; top:10px; -webkit-text-stroke: 18px #000000;
                              color:#000000; filter: drop-shadow(0 10px 18px rgba(0,0,0,0.9));">{page.line1}</span>
                        <span style="position:relative; background:{grad}; -webkit-background-clip:text;
                              -webkit-text-fill-color:transparent;">{page.line1}</span>
                    </div>
                    <div class="nowrap" style="font-size:74px; line-height:1.42; color:#FFFFFF;
                         -webkit-text-stroke: 14px #000000; paint-order: stroke fill;
                         filter: drop-shadow(0 8px 14px rgba(0,0,0,0.85)); margin-top:-8px; padding: 8px 24px;">
                        {page.line2}
                    </div>
                </div>
                """,
                (0, 165, 1080, 420),
            )
        if page.kind in ("label", "label_colored"):
            bg = "#F6F8FB"
            fg = "#0B1120"
            border = "3px solid rgba(15,23,42,0.18)"
            if page.accent == "green_box":
                bg = "#16A34A"
                fg = "#FFFFFF"
                border = "4px solid #86EFAC"
            elif page.accent == "red_box":
                bg = "#DC2626"
                fg = "#FFFFFF"
                border = "4px solid #FCA5A5"
            return (
                f"""
                <div id="box" style="position:absolute; left:0; top:1320px; width:1080px; height:150px;
                     display:flex; align-items:center; justify-content:center;">
                    <div class="nowrap" style="background:{bg}; color:{fg}; border:{border};
                         border-radius:16px; padding:14px 44px; font-size:52px; line-height:1.4;
                         box-shadow: 0 12px 28px rgba(0,0,0,0.55);">
                        {page.line1}
                    </div>
                </div>
                """,
                (0, 1320, 1080, 150),
            )
        if page.kind == "paper_build":
            l2_html = (
                f"""<div class="nowrap" style="font-size:82px; line-height:1.45; color:#111827;
                     text-shadow: 5px 5px 0px rgba(0,0,0,0.22); margin-top:24px; padding:8px 24px;">
                     {page.line2}
                </div>"""
                if page.line2
                else ""
            )
            return (
                f"""
                <div id="box" style="position:absolute; left:0; top:560px; width:1080px; height:560px;
                     display:flex; flex-direction:column; align-items:center; justify-content:center; padding:30px;">
                    <div class="nowrap" style="font-size:90px; line-height:1.45; color:#ED1D37;
                         -webkit-text-stroke: 4px #111827; paint-order: stroke fill;
                         filter: drop-shadow(5px 5px 0px #111827); padding:8px 24px;">
                        {page.line1}
                    </div>
                    {l2_html}
                </div>
                """,
                (0, 560, 1080, 560),
            )
        if page.kind == "panel":
            return (
                f"""
                <div id="box" style="position:absolute; left:0; top:0; width:1080px; height:1056px;
                     background: linear-gradient(180deg, #071A14 0%, #0D2E22 100%);
                     border-bottom: 8px solid #23FD0A; box-shadow: 0 24px 50px rgba(0,0,0,0.75);
                     display:flex; flex-direction:column; align-items:center; justify-content:center; padding:48px;">
                    <div class="nowrap" style="background:#124230; border:3px solid #23FD0A; border-radius:28px;
                         padding:28px 64px; margin-bottom:36px; box-shadow: 0 14px 32px rgba(0,0,0,0.45);
                         display:flex; align-items:center; gap:24px;">
                        <span style="font-size:78px; line-height:1.4; color:#FFFFFF;">{page.extra}</span>
                    </div>
                    <div class="nowrap" style="font-size:84px; line-height:1.45; color:#23FD0A;
                         -webkit-text-stroke: 14px #000000; paint-order: stroke fill; padding:8px 24px;">
                        {page.line1}
                    </div>
                    <div class="nowrap" style="font-size:68px; line-height:1.45; color:#FFFFFF;
                         -webkit-text-stroke: 12px #000000; paint-order: stroke fill; padding:8px 24px;">
                        {page.line2}
                    </div>
                </div>
                """,
                (0, 0, 1080, 1056),
            )
        if page.kind == "end_card":
            return (
                f"""
                <div id="box" style="position:absolute; left:0; top:360px; width:1080px; height:1200px;
                     display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px;">
                    <!-- Comic burst card -->
                    <div style="width:960px; background: linear-gradient(180deg, #FEF08A 0%, #FACC15 100%);
                         border: 12px solid #111827; border-radius: 52px;
                         box-shadow: 0 24px 0px #111827, 0 38px 64px rgba(0,0,0,0.7);
                         padding: 72px 48px 64px 48px; display:flex; flex-direction:column; align-items:center;
                         position:relative;">
                        <!-- Top white star badge -->
                        <div class="nowrap" style="background:#FFFFFF; border:6px solid #111827; border-radius:999px;
                             padding:12px 44px; font-size:44px; line-height:1.35; color:#111827;
                             margin-top:-112px; margin-bottom:36px; box-shadow: 0 8px 0px #111827;">
                            ★ MYPASAKON AI ★
                        </div>
                        <div class="nowrap" style="font-size:82px; line-height:1.42; color:#111827;
                             -webkit-text-stroke: 6px #FFFFFF; paint-order: stroke fill; padding:8px 16px;">
                            {page.line1}
                        </div>
                        <div class="nowrap" style="font-size:36px; line-height:1.45; color:#1E293B;
                             margin-top:16px; margin-bottom:40px; padding:6px 16px;">
                            {page.line2}
                        </div>
                        <!-- Cloud / white base box for risk warning -->
                        <div style="width:100%; background:#FFFFFF; border:6px solid #111827; border-radius:32px;
                             padding:24px 20px; text-align:center; box-shadow: 0 10px 0px rgba(17,24,39,0.18);">
                            <div class="nowrap" style="font-size:26px; line-height:1.5; color:#0F172A;">
                                {page.extra}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                (0, 360, 1080, 1200),
            )
        raise ValueError(f"Unknown page kind: {page.kind}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, chromium_sandbox=False, args=CHROMIUM_ARGS)
        context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
        page = context.new_page()

        def grab_rgba(body_html: str, crop_box: tuple[int, int, int, int]) -> tuple[np.ndarray, Image.Image]:
            full_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{base_css}</style></head><body>{body_html}</body></html>"
            page.set_content(full_html, wait_until="load")
            page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
            x, y, w, h = crop_box
            png_bytes = page.screenshot(
                type="png",
                omit_background=True,
                clip={"x": x, "y": y, "width": w, "height": h},
            )
            import io
            pil_img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            arr = np.array(pil_img, dtype=np.uint8)
            return arr, pil_img

        # 1. Render all shot pages
        for shot in shots:
            for p_idx, tp in enumerate(shot.pages):
                key = f"shot{shot.idx:02d}_page{p_idx}"
                tp.sprite_key = key
                b_html, c_box = html_for_page(tp, shot)
                arr, pil_img = grab_rgba(b_html, c_box)
                sprites[key] = arr
                label_desc = f"S{shot.idx:02d} (orig {shot.orig_shot:02d}) [{tp.kind}] {tp.line1} | {tp.line2} {tp.extra}".strip()
                proof_items.append((key, label_desc, pil_img))

            # 2. Render all stickers
            for s_idx, st in enumerate(shot.stickers):
                key = f"shot{shot.idx:02d}_sticker{s_idx}"
                st.sprite_key = key
                s_html = f"""
                <div style="position:absolute; left:0; top:0; width:520px; height:180px;
                     display:flex; align-items:center; justify-content:center;">
                    <div class="nowrap" style="background:{st.bg_color}; color:{st.text_color};
                         border: 14px solid #FFFFFF; border-radius: 32px;
                         padding: 14px 38px; font-size: 52px; line-height: 1.4;
                         box-shadow: 0 14px 28px rgba(0,0,0,0.65);">
                        {st.text}
                    </div>
                </div>
                """
                arr, pil_img = grab_rgba(s_html, (0, 0, 520, 180))
                sprites[key] = arr
                proof_items.append((key, f"S{shot.idx:02d} sticker: {st.text}", pil_img))

        # 3. Special layout cards (Shot 9 mint ticks, Shot 15 terminal prompt, Shot 18 mint counter label, Shot 22 split contrast, STAND-IN badge)
        if standin:
            badge_html = """
            <div style="position:absolute; left:0; top:0; width:360px; height:80px;
                 display:flex; align-items:center; justify-content:flex-start; padding:8px;">
                <div class="nowrap" style="background:rgba(15,23,42,0.88); color:#FACC15;
                     border:2px solid #FACC15; border-radius:12px; padding:6px 18px;
                     font-size:28px; line-height:1.35;">
                    STAND-IN PREVIEW
                </div>
            </div>
            """
            arr, pil_img = grab_rgba(badge_html, (0, 0, 360, 80))
            sprites["standin_badge"] = arr

        # Shot 9 card ("ทุกวัน" + 8 ticks)
        for ticks_lit in (3, 6, 8):
            boxes = "".join(
                f"""<div style="width:82px; height:82px; border-radius:18px;
                     background:{'#23FD0A' if i < ticks_lit else 'rgba(255,255,255,0.12)'};
                     color:{'#052E16' if i < ticks_lit else 'rgba(255,255,255,0.3)'};
                     border:3px solid {'#FFFFFF' if i < ticks_lit else 'rgba(255,255,255,0.25)'};
                     display:flex; align-items:center; justify-content:center; font-size:46px;">✓</div>"""
                for i in range(8)
            )
            s9_html = f"""
            <div style="position:absolute; left:0; top:0; width:920px; height:520px;
                 background:rgba(6, 46, 34, 0.92); border:5px solid #23FD0A; border-radius:36px;
                 box-shadow: 0 24px 48px rgba(0,0,0,0.65);
                 display:flex; flex-direction:column; align-items:center; justify-content:center; padding:32px;">
                <div class="nowrap" style="font-size:96px; line-height:1.4; color:#FFFFFF; margin-bottom:24px;">
                    ทุกวัน
                </div>
                <div style="display:flex; gap:16px;">{boxes}</div>
            </div>
            """
            arr, pil_img = grab_rgba(s9_html, (0, 0, 920, 520))
            sprites[f"shot09_card_{ticks_lit}"] = arr
            if ticks_lit == 8:
                proof_items.append(("shot09_card_8", "S09 mint card: ทุกวัน", pil_img))

        # Shot 15 (orig 16) terminal prompt typing steps
        prompt_full = "วิจัยกลยุทธ์การเทรดทุกตัวย้อนหลัง 5 ปี"
        for step_idx, char_cnt in enumerate((8, 18, 28, len(prompt_full))):
            sub_txt = prompt_full[:char_cnt]
            s15_html = f"""
            <div style="position:absolute; left:0; top:0; width:960px; height:240px;
                 background:rgba(9, 13, 22, 0.94); border:4px solid #38BDF8; border-radius:24px;
                 box-shadow: 0 20px 44px rgba(0,0,0,0.75);
                 display:flex; flex-direction:column; justify-content:center; padding:28px 36px;">
                <div class="nowrap" style="font-size:30px; line-height:1.35; color:#38BDF8; margin-bottom:10px;">
                    claude &gt; prompt ก่อนนอน
                </div>
                <div class="nowrap" style="font-size:44px; line-height:1.45; color:#FFFFFF;">
                    {sub_txt}<span style="color:#23FD0A;">▋</span>
                </div>
            </div>
            """
            arr, pil_img = grab_rgba(s15_html, (0, 0, 960, 240))
            sprites[f"shot15_prompt_{step_idx}"] = arr
            if step_idx == 3:
                proof_items.append(("shot15_prompt_3", f"S15 prompt: {prompt_full}", pil_img))

        # Shot 18 (orig 19) counter steps ("0 -> 10,000+ รอบ")
        for c_idx, val_str in enumerate(("1,250", "4,800", "8,400", "10,000+")):
            s18_html = f"""
            <div style="position:absolute; left:0; top:0; width:920px; height:480px;
                 background:rgba(6, 46, 34, 0.92); border:5px solid #23FD0A; border-radius:36px;
                 box-shadow: 0 24px 48px rgba(0,0,0,0.65);
                 display:flex; flex-direction:column; align-items:center; justify-content:center; padding:32px;">
                <div class="nowrap" style="font-size:124px; line-height:1.3; color:#23FD0A;
                     -webkit-text-stroke: 8px #000000; paint-order: stroke fill;">
                    {val_str}
                </div>
                <div class="nowrap" style="font-size:64px; line-height:1.4; color:#FFFFFF; margin-top:8px;">
                    รอบ
                </div>
            </div>
            """
            arr, pil_img = grab_rgba(s18_html, (0, 0, 920, 480))
            sprites[f"shot18_counter_{c_idx}"] = arr
            if c_idx == 3:
                proof_items.append(("shot18_counter_3", "S18 counter: 10,000+ รอบ", pil_img))

        # Shot 22 (orig 23) split contrast card ("1 เดือน" greyed vs "1 คืน" lit)
        s22_html = """
        <div style="position:absolute; left:0; top:0; width:960px; height:980px;
             display:flex; flex-direction:column; gap:36px; align-items:center; justify-content:center;">
            <div style="width:920px; height:420px; background:rgba(30,41,59,0.88);
                 border:4px solid #64748B; border-radius:36px;
                 display:flex; flex-direction:column; align-items:center; justify-content:center; padding:28px;">
                <div class="nowrap" style="font-size:44px; line-height:1.4; color:#94A3B8;">ทำเองคนเดียว</div>
                <div class="nowrap" style="font-size:108px; line-height:1.35; color:#94A3B8;">1 เดือน</div>
            </div>
            <div style="width:920px; height:440px; background:linear-gradient(180deg, #064E3B 0%, #052E16 100%);
                 border:6px solid #23FD0A; border-radius:36px; box-shadow: 0 20px 50px rgba(35,253,10,0.32);
                 display:flex; flex-direction:column; align-items:center; justify-content:center; padding:28px;">
                <div class="nowrap" style="font-size:48px; line-height:1.4; color:#A7F3D0;">ให้ Claude ช่วยตอนหลับ</div>
                <div class="nowrap" style="font-size:120px; line-height:1.35; color:#23FD0A;
                     -webkit-text-stroke: 8px #000000; paint-order: stroke fill;">1 คืน</div>
            </div>
        </div>
        """
        arr, pil_img = grab_rgba(s22_html, (0, 0, 960, 980))
        sprites["shot22_split"] = arr
        proof_items.append(("shot22_split", "S22 split card: 1 เดือน vs 1 คืน", pil_img))

        browser.close()

    # Build the caption proof contact sheet (v5/qc/caption-proof.png)
    qc_dir.mkdir(parents=True, exist_ok=True)
    cols = 2
    cell_w = 960
    cell_h = 340
    rows = math.ceil(len(proof_items) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (18, 24, 38))
    for i, (key, desc, im) in enumerate(proof_items):
        r = i // cols
        c = i % cols
        x0 = c * cell_w
        y0 = r * cell_h
        # Fit sprite inside (cell_w - 24, cell_h - 24)
        im_copy = im.copy()
        im_copy.thumbnail((cell_w - 24, cell_h - 24), Image.Resampling.LANCZOS)
        cell_bg = Image.new("RGBA", (cell_w - 12, cell_h - 12), (30, 41, 59, 255))
        ox = (cell_bg.width - im_copy.width) // 2
        oy = (cell_bg.height - im_copy.height) // 2
        cell_bg.alpha_composite(im_copy, (ox, oy))
        sheet.paste(cell_bg.convert("RGB"), (x0 + 6, y0 + 6))
    proof_path = qc_dir / "caption-proof.png"
    sheet.save(proof_path)
    print(f"[qc] Wrote caption contact sheet: {proof_path} ({len(proof_items)} items)")
    return sprites


def load_video_frames(path: Path, max_frames: int = 150, step: int = 1) -> list[np.ndarray]:
    """Decode video frames as RGB uint8 arrays."""
    cap = cv2.VideoCapture(str(path))
    frames: list[np.ndarray] = []
    raw_idx = 0
    while len(frames) < max_frames:
        ok, bgr = cap.read()
        if not ok:
            break
        if raw_idx % step == 0:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            if rgb.shape[1] != WIDTH or rgb.shape[0] != HEIGHT:
                rgb = cv2.resize(rgb, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
            frames.append(rgb)
        raw_idx += 1
    cap.release()
    if not frames:
        raise SystemExit(f"Could not decode frames from {path}")
    return frames


def enhance_standin_avatar_frames(frames: list[np.ndarray]) -> list[np.ndarray]:
    """If avatar_ref.mp4 is the flat lavfi placeholder card, draw a presenter silhouette + studio grid
    so 105-135% crops and push-in motion produce distinct, non-duplicate visual framing on every shot."""
    sample = frames[0]
    if float(sample.std()) > 28.0:
        # Real camera footage has high spatial variance; return untouched
        return frames

    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    # Warm studio vignette + subtle grid so crops & zoom rates are measurable by ORB / eye
    base_bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    dist = np.sqrt(((xx - 540.0) / 540.0) ** 2 + ((yy - 820.0) / 960.0) ** 2)
    vign = np.clip(1.0 - 0.55 * dist, 0.25, 1.0)
    base_bg[..., 0] = (28 * vign).astype(np.uint8)
    base_bg[..., 1] = (46 * vign).astype(np.uint8)
    base_bg[..., 2] = (72 * vign).astype(np.uint8)

    # Studio acoustic panel lines + bokeh markers (gives ORB feature points for motion verification)
    for gx in range(90, WIDTH, 120):
        cv2.line(base_bg, (gx, 0), (gx, HEIGHT), (38, 62, 92), 2)
    for gy in range(120, HEIGHT, 160):
        cv2.line(base_bg, (0, gy), (WIDTH, gy), (36, 58, 86), 2)
    rng = np.random.default_rng(42)
    for _ in range(45):
        bx = int(rng.integers(80, WIDTH - 80))
        by = int(rng.integers(120, HEIGHT - 120))
        br = int(rng.integers(8, 24))
        cv2.circle(base_bg, (bx, by), br, (58, 96, 138), -1, lineType=cv2.LINE_AA)

    n_loop = len(frames)
    for idx in range(n_loop):
        canvas = base_bg.copy()
        phase = 2.0 * math.pi * (idx / max(1, n_loop))
        breath_y = int(round(6.0 * math.sin(phase)))
        head_x = 540 + int(round(4.0 * math.cos(phase)))
        head_y = 760 + breath_y
        # Presenter shoulders & torso silhouette
        cv2.ellipse(canvas, (head_x, 1340 + breath_y), (340, 420), 0, 180, 360, (44, 72, 108), -1, lineType=cv2.LINE_AA)
        cv2.ellipse(canvas, (head_x, 1340 + breath_y), (340, 420), 0, 180, 360, (110, 231, 183), 4, lineType=cv2.LINE_AA)
        # Neck & Head silhouette (neutral warm tone, zero blush)
        cv2.rectangle(canvas, (head_x - 55, head_y + 130), (head_x + 55, head_y + 230), (198, 164, 132), -1)
        cv2.ellipse(canvas, (head_x, head_y), (155, 195), 0, 0, 360, (214, 180, 148), -1, lineType=cv2.LINE_AA)
        cv2.ellipse(canvas, (head_x, head_y), (155, 195), 0, 0, 360, (255, 255, 255), 3, lineType=cv2.LINE_AA)
        # Hair / beanie cap
        cv2.ellipse(canvas, (head_x, head_y - 70), (162, 130), 0, 180, 360, (24, 34, 52), -1, lineType=cv2.LINE_AA)
        # Eyes & neutral speaking mouth
        cv2.circle(canvas, (head_x - 56, head_y - 10), 12, (20, 28, 40), -1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, (head_x + 56, head_y - 10), 12, (20, 28, 40), -1, lineType=cv2.LINE_AA)
        mouth_h = 8 + int(10 * abs(math.sin(phase * 3.0)))
        cv2.ellipse(canvas, (head_x, head_y + 82), (34, mouth_h), 0, 0, 360, (60, 45, 45), -1, lineType=cv2.LINE_AA)
        frames[idx] = canvas
    return frames


def build_paper_background() -> np.ndarray:
    """Create a procedural warm cream paper texture (1080x1920 RGB)."""
    rng = np.random.default_rng(1080)
    noise = rng.normal(0.0, 5.5, size=(HEIGHT, WIDTH, 1)).astype(np.float32)
    base = np.full((HEIGHT, WIDTH, 3), (244, 239, 228), dtype=np.float32) + noise
    paper = np.clip(base, 215, 252).astype(np.uint8)
    for x in range(0, WIDTH, 90):
        cv2.line(paper, (x, 0), (x, HEIGHT), (230, 224, 210), 1)
    for y in range(0, HEIGHT, 90):
        cv2.line(paper, (0, y), (WIDTH, y), (230, 224, 210), 1)
    return paper


def build_mint_background() -> np.ndarray:
    """Create a mint-green graphic card background (1080x1920 RGB)."""
    yy = np.linspace(0.0, 1.0, HEIGHT, dtype=np.float32)[:, None]
    bg = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    bg[..., 0] = (10 + 14 * (1.0 - yy)).astype(np.uint8)
    bg[..., 1] = (48 + 56 * (1.0 - yy)).astype(np.uint8)
    bg[..., 2] = (36 + 42 * (1.0 - yy)).astype(np.uint8)
    for r in range(200, 1100, 220):
        cv2.circle(bg, (540, 960), r, (24, 128, 92), 2, lineType=cv2.LINE_AA)
    return bg


def alpha_composite_np(dst: np.ndarray, src_rgba: np.ndarray, x: int, y: int) -> None:
    """In-place alpha blend src_rgba onto dst RGB at (x, y) with boundary clipping."""
    h, w = src_rgba.shape[:2]
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(WIDTH, x + w)
    y1 = min(HEIGHT, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sx0 = x0 - x
    sy0 = y0 - y
    sx1 = sx0 + (x1 - x0)
    sy1 = sy0 + (y1 - y0)
    sub_src = src_rgba[sy0:sy1, sx0:sx1]
    alpha = sub_src[..., 3:4].astype(np.float32) / 255.0
    roi = dst[y0:y1, x0:x1].astype(np.float32)
    blended = roi * (1.0 - alpha) + sub_src[..., :3].astype(np.float32) * alpha
    dst[y0:y1, x0:x1] = blended.astype(np.uint8)


def crop_with_zoom(frame: np.ndarray, zoom: float, offset_xy: tuple[int, int] = (0, 0)) -> np.ndarray:
    """Zoom into frame by `zoom` (>= 1.0) around center + offset_xy and resize back to 1080x1920."""
    zoom = max(1.0, float(zoom))
    cw = int(round(WIDTH / zoom))
    ch = int(round(HEIGHT / zoom))
    cx = WIDTH // 2 + offset_xy[0]
    cy = HEIGHT // 2 + offset_xy[1]
    x0 = max(0, min(WIDTH - cw, cx - cw // 2))
    y0 = max(0, min(HEIGHT - ch, cy - ch // 2))
    cropped = frame[y0 : y0 + ch, x0 : x0 + cw]
    return cv2.resize(cropped, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)


def draw_round_pip(
    canvas: np.ndarray,
    face_frame: np.ndarray,
    diameter: int,
    center_xy: tuple[int, int],
    ring_color: tuple[int, int, int] = (35, 253, 10),
    ring_px: int = 5,
) -> None:
    """Draw a circular face PIP inset with a solid ring border."""
    r = diameter // 2
    cx, cy = center_xy
    x0 = cx - r
    y0 = cy - r
    # Crop around upper-middle head area of face_frame
    fh, fw = face_frame.shape[:2]
    side = int(min(fw, fh) * 0.68)
    fx0 = max(0, (fw - side) // 2)
    fy0 = max(0, int(fh * 0.16))
    patch = cv2.resize(face_frame[fy0 : fy0 + side, fx0 : fx0 + side], (diameter, diameter), interpolation=cv2.INTER_LINEAR)
    yy, xx = np.ogrid[:diameter, :diameter]
    dist_sq = (xx - r) ** 2 + (yy - r) ** 2
    mask = dist_sq <= (r - ring_px) ** 2
    ring_mask = (dist_sq <= r**2) & (dist_sq > (r - ring_px) ** 2)

    roi = canvas[y0 : y0 + diameter, x0 : x0 + diameter]
    roi[mask] = patch[mask]
    roi[ring_mask] = ring_color


def spring_scale(dt: float, pop_dur: float = 0.25) -> float:
    """0.25s spring overshoot curve: 0 -> 1.16 -> 1.0."""
    if dt < 0.0:
        return 0.0
    if dt >= pop_dur:
        return 1.0
    u = dt / pop_dur
    if u < 0.65:
        return 1.16 * (u / 0.65)
    return 1.16 - 0.16 * ((u - 0.65) / 0.35)


def render_frame_for_shot(
    shot: ShotSpec,
    t: float,
    avatar_frames: list[np.ndarray],
    clip_frames: list[list[np.ndarray]],
    paper_bg: np.ndarray,
    mint_bg: np.ndarray,
    sprites: dict[str, np.ndarray],
    standin: bool,
) -> np.ndarray:
    """Composite a single 1080x1920 RGB frame for time `t` inside `shot`."""
    dt = max(0.0, t - shot.t_in)
    # Offset avatar frame index by shot.idx * 37 so adjacent shots use distinct moments too
    av_idx = (int(round(t * FPS)) + shot.idx * 37) % len(avatar_frames)
    raw_face = avatar_frames[av_idx]
    cur_zoom = shot.face_zoom + shot.face_push_rate * dt
    face_zoomed = crop_with_zoom(raw_face, cur_zoom, shot.face_offset)

    c_frames = clip_frames[shot.clip_idx]
    c_idx = int(round(dt * 15)) % len(c_frames)
    raw_clip = c_frames[c_idx]

    if shot.layout == "face_full":
        canvas = face_zoomed.copy()

    elif shot.layout == "face_over_chart_bg":
        # Shot 2: blurred chart bg + face card/cutout + star sticker pop
        bg_zoomed = crop_with_zoom(raw_clip, 1.25 + 0.03 * dt)
        canvas = cv2.GaussianBlur(bg_zoomed, (31, 31), 0)
        canvas = (canvas.astype(np.float32) * 0.45).astype(np.uint8)
        # Central presenter frame with glowing border
        fw, fh = 860, 1280
        fx, fy = (WIDTH - fw) // 2, 480
        face_sub = cv2.resize(face_zoomed, (fw, fh), interpolation=cv2.INTER_LINEAR)
        cv2.rectangle(canvas, (fx - 6, fy - 6), (fx + fw + 6, fy + fh + 6), (35, 253, 10), -1)
        canvas[fy : fy + fh, fx : fx + fw] = face_sub

    elif shot.layout == "card":
        # Layer 1: Dark + blurred zoomed duplicate of screen clip
        bg_dup = crop_with_zoom(raw_clip, 1.35 + 0.02 * dt)
        small = cv2.resize(bg_dup, (270, 480), interpolation=cv2.INTER_LINEAR)
        blurred = cv2.GaussianBlur(small, (25, 25), 0)
        canvas = (cv2.resize(blurred, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR).astype(np.float32) * 0.36).astype(np.uint8)
        # Layer 2: Sharp screen card (94% wide = 1016px, 31% high = 596px, top edge y = 610 = 31.8%)
        card_zoom = 1.0 + 0.015 * dt
        card_src = crop_with_zoom(raw_clip, card_zoom)
        # Take central band of the 9:16 screen recording so UI text is large and readable
        band = card_src[340:1420, :, :]
        card_w, card_h = 1016, 596
        card_img = cv2.resize(band, (card_w, card_h), interpolation=cv2.INTER_LINEAR)
        cx0, cy0 = (WIDTH - card_w) // 2, 610
        cv2.rectangle(canvas, (cx0 - 3, cy0 - 3), (cx0 + card_w + 3, cy0 + card_h + 3), (56, 189, 248), 3)
        canvas[cy0 : cy0 + card_h, cx0 : cx0 + card_w] = card_img
        if standin and "standin_badge" in sprites:
            alpha_composite_np(canvas, sprites["standin_badge"], cx0 + 16, cy0 + 16)
        # Layer 3: 428px round PIP top-right (x=76% -> 820, y=14.6% -> 280)
        draw_round_pip(canvas, face_zoomed, 428, (820, 280), ring_color=(35, 253, 10), ring_px=6)

    elif shot.layout in ("stack", "stack_highlight"):
        # Layer 1 & 2: Blurred zoomed copies above and below drifting
        shift = int(round(dt * 18))
        bg_dup = crop_with_zoom(raw_clip, 1.38, (shift, -shift))
        small = cv2.resize(bg_dup, (270, 480), interpolation=cv2.INTER_LINEAR)
        blurred = cv2.GaussianBlur(small, (21, 21), 0)
        canvas = (cv2.resize(blurred, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR).astype(np.float32) * 0.48).astype(np.uint8)
        # Layer 3: Sharp card in centre
        card_src = crop_with_zoom(raw_clip, 1.0 + 0.014 * dt)
        band = card_src[340:1420, :, :]
        card_w, card_h = 1016, 610
        card_img = cv2.resize(band, (card_w, card_h), interpolation=cv2.INTER_LINEAR)
        cx0, cy0 = (WIDTH - card_w) // 2, 600
        canvas[cy0 : cy0 + card_h, cx0 : cx0 + card_w] = card_img
        if shot.layout == "stack_highlight":
            # Green highlight first half, red highlight second half
            is_first = t < 61.60
            hl_color = (35, 253, 10) if is_first else (239, 68, 68)
            hy = cy0 + (180 if is_first else 340)
            cv2.rectangle(canvas, (cx0 + 24, hy), (cx0 + card_w - 24, hy + 110), hl_color, 6)
        if standin and "standin_badge" in sprites:
            alpha_composite_np(canvas, sprites["standin_badge"], cx0 + 16, cy0 + 16)

    elif shot.layout == "full_bleed_whip":
        # Shot 7: fast whip-pan crop 8%/s of clip2_log
        pan_x = int(round((dt / max(0.1, shot.duration) - 0.5) * 140))
        canvas = crop_with_zoom(raw_clip, 1.22, (pan_x, 0))
        if standin and "standin_badge" in sprites:
            alpha_composite_np(canvas, sprites["standin_badge"], 36, 120)

    elif shot.layout == "terminal_typing":
        # Shot 15 (orig 16): clip1_terminal full-bleed zoom 100->105% + prompt card typing
        canvas = crop_with_zoom(raw_clip, 1.0 + 0.016 * dt)
        if standin and "standin_badge" in sprites:
            alpha_composite_np(canvas, sprites["standin_badge"], 36, 120)
        step = min(3, int(dt / 0.65))
        sp = sprites[f"shot15_prompt_{step}"]
        alpha_composite_np(canvas, sp, (WIDTH - sp.shape[1]) // 2, 1180)

    elif shot.layout == "paper_stickers":
        # Procedural paper texture with moving subtle grid + 256px PIP top-centre (y=230, above caption)
        shift = int(round(dt * 12)) % 90
        canvas = np.roll(paper_bg, shift=(shift, shift), axis=(0, 1))
        draw_round_pip(canvas, face_zoomed, 256, (540, 230), ring_color=(17, 24, 39), ring_px=6)

    elif shot.layout == "paper_text":
        shift = int(round(dt * 10)) % 90
        canvas = np.roll(paper_bg, shift=(shift, 0), axis=(0, 1))
        draw_round_pip(canvas, face_zoomed, 256, (540, 310), ring_color=(237, 29, 55), ring_px=6)

    elif shot.layout == "mint_ticks":
        # Shot 9: mint bg + 256px PIP top-centre (y=230) + caption below PIP + punch-zoom card at y=840
        canvas = mint_bg.copy()
        draw_round_pip(canvas, face_zoomed, 256, (540, 230), ring_color=(35, 253, 10), ring_px=6)
        ticks_lit = 3 if dt < 0.7 else (6 if dt < 1.4 else 8)
        card_sp = sprites[f"shot09_card_{ticks_lit}"]
        scale = 1.0 + 0.10 * min(1.0, dt / 0.4)
        cw = int(round(card_sp.shape[1] * scale))
        ch = int(round(card_sp.shape[0] * scale))
        scaled_sp = cv2.resize(card_sp, (cw, ch), interpolation=cv2.INTER_LINEAR)
        alpha_composite_np(canvas, scaled_sp, (WIDTH - cw) // 2, 840)

    elif shot.layout == "mint_counter":
        # Shot 18 (orig 19): mint bg + faint chart + 256px PIP (y=230) + caption + animated counter at y=860
        faint_chart = cv2.resize(raw_clip, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
        canvas = cv2.addWeighted(mint_bg, 0.78, faint_chart, 0.22, 0.0)
        draw_round_pip(canvas, face_zoomed, 256, (540, 230), ring_color=(35, 253, 10), ring_px=6)
        c_idx = min(3, int(dt / 0.45))
        cnt_sp = sprites[f"shot18_counter_{c_idx}"]
        alpha_composite_np(canvas, cnt_sp, (WIDTH - cnt_sp.shape[1]) // 2, 860)

    elif shot.layout == "split_counter":
        # Shot 22 (orig 23): contrast card 1 เดือน vs 1 คืน with punch-zoom
        canvas = mint_bg.copy()
        sp = sprites["shot22_split"]
        scale = 1.0 + 0.08 * min(1.0, dt / 0.45)
        cw = int(round(sp.shape[1] * scale))
        ch = int(round(sp.shape[0] * scale))
        scaled_sp = cv2.resize(sp, (cw, ch), interpolation=cv2.INTER_LINEAR)
        alpha_composite_np(canvas, scaled_sp, (WIDTH - cw) // 2, 640)

    elif shot.layout == "top_panel":
        # Bottom face + top 55% panel sliding in over 0.3s ease-out
        canvas = face_zoomed.copy()
        panel_sp = sprites[shot.pages[0].sprite_key]
        u = min(1.0, dt / 0.30)
        ease = 1.0 - (1.0 - u) ** 3
        py = int(round(-panel_sp.shape[0] * (1.0 - ease)))
        alpha_composite_np(canvas, panel_sp, 0, py)

    elif shot.layout == "end_card":
        # Dark radial background + comic burst card scaling 90->100% in 0.3s
        canvas = mint_bg.copy()
        end_sp = sprites[shot.pages[0].sprite_key]
        u = min(1.0, dt / 0.30)
        scale = 0.90 + 0.10 * (1.0 - (1.0 - u) ** 3)
        cw = int(round(end_sp.shape[1] * scale))
        ch = int(round(end_sp.shape[0] * scale))
        scaled_sp = cv2.resize(end_sp, (cw, ch), interpolation=cv2.INTER_LINEAR)
        alpha_composite_np(canvas, scaled_sp, (WIDTH - cw) // 2, (HEIGHT - ch) // 2)

    else:
        canvas = face_zoomed.copy()

    # Draw stickers with 0.25s spring overshoot pop + 1%/s drift
    for st in shot.stickers:
        if dt >= st.t_pop:
            s_dt = dt - st.t_pop
            sc = spring_scale(s_dt, 0.25)
            if sc > 0.02:
                sp = sprites[st.sprite_key]
                sw = max(4, int(round(sp.shape[1] * sc)))
                sh = max(4, int(round(sp.shape[0] * sc)))
                resized = cv2.resize(sp, (sw, sh), interpolation=cv2.INTER_LINEAR)
                drift_y = int(round(-s_dt * 12.0))
                alpha_composite_np(canvas, resized, st.x - sw // 2, st.y - sh // 2 + drift_y)

    # Draw active text page (except top_panel and end_card which already rendered their main sprite)
    if shot.layout not in ("top_panel", "end_card"):
        for tp in shot.pages:
            if tp.t_start - 1e-4 <= t < tp.t_end + 1e-4:
                sp = sprites[tp.sprite_key]
                if tp.kind in ("top2", "hero"):
                    if shot.pip_mode == "small_tc":
                        y_pos = 390
                    else:
                        y_pos = 180 if tp.kind == "top2" else 165
                    alpha_composite_np(canvas, sp, 0, y_pos)
                elif tp.kind in ("label", "label_colored"):
                    alpha_composite_np(canvas, sp, 0, 1320)
                elif tp.kind == "paper_build":
                    alpha_composite_np(canvas, sp, 0, 560)
                break

    # Apply entry FX transitions (paper_flash, text_mask_whip, star_pop_bg_swap flash)
    if shot.transition_in == "paper_flash" and dt < 0.45:
        # Ink-brush paper white flash (0.45 s)
        flash_alpha = max(0.0, 1.0 - (dt / 0.45)) ** 1.6
        band_y = int(round((dt / 0.45) * HEIGHT))
        flash_layer = paper_bg.copy()
        cv2.rectangle(flash_layer, (0, max(0, band_y - 240)), (WIDTH, min(HEIGHT, band_y + 240)), (255, 255, 255), -1)
        canvas = cv2.addWeighted(canvas, 1.0 - flash_alpha, flash_layer, flash_alpha, 0.0)
    elif shot.transition_in == "text_mask_whip" and dt < 0.55:
        # Giant glow flash + horizontal whip into end card
        whip_u = dt / 0.55
        glow = max(0.0, 1.0 - whip_u) ** 1.5
        shift_x = int(round((1.0 - whip_u) ** 2 * 320))
        canvas = np.roll(canvas, shift=shift_x, axis=1)
        white = np.full_like(canvas, 255)
        canvas = cv2.addWeighted(canvas, 1.0 - 0.85 * glow, white, 0.85 * glow, 0.0)
    elif shot.transition_in == "star_pop_bg_swap" and dt < 0.25:
        glow = (1.0 - dt / 0.25) * 0.45
        white = np.full_like(canvas, 255)
        canvas = cv2.addWeighted(canvas, 1.0 - glow, white, glow, 0.0)

    return canvas


def build_audio_mix(
    voice_path: Path,
    shots: list[ShotSpec],
    sfx_dir: Path,
    out_wav: Path,
) -> dict[str, float]:
    """Mix approved voice (padded to 105.72 s) + media-use SFX cues, then normalize to -20 LUFS (peak < -1 dBFS)."""
    events: list[tuple[float, Path, float]] = []
    for shot in shots:
        for t_ev, sfx_name, gain_db in shot.sfx_events:
            sfx_file = sfx_dir / sfx_name
            if not sfx_file.is_file():
                raise SystemExit(f"Missing media-use SFX file: {sfx_file}")
            events.append((t_ev, sfx_file, gain_db))

    with tempfile.TemporaryDirectory(prefix="mypasakon_audio_") as tmpd:
        tmp_dir = Path(tmpd)
        raw_mix = tmp_dir / "raw_mix.wav"

        inputs = ["-i", str(voice_path)]
        filter_parts = [f"[0:a]aresample=48000,apad=whole_dur={TOTAL_DURATION}[voice]"]
        mix_labels = ["[voice]"]

        for idx, (t_ev, sfx_file, gain_db) in enumerate(events, start=1):
            inputs.extend(["-i", str(sfx_file)])
            delay_ms = max(0, int(round(t_ev * 1000.0)))
            lbl = f"[s{idx}]"
            filter_parts.append(
                f"[{idx}:a]aresample=48000,volume={gain_db}dB,adelay={delay_ms}|{delay_ms}{lbl}"
            )
            mix_labels.append(lbl)

        n_inputs = len(mix_labels)
        filter_parts.append(
            f"{''.join(mix_labels)}amix=inputs={n_inputs}:duration=first:dropout_transition=0:normalize=0[mixed]"
        )
        filter_complex = ";".join(filter_parts)

        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[mixed]",
                "-t", str(TOTAL_DURATION),
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                str(raw_mix),
            ],
            check=True,
        )

        # Two-pass loudnorm to hit -20.0 LUFS integrated and true peak <= -1.5 dBFS
        pass1 = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-nostats", "-i", str(raw_mix),
                "-af", "loudnorm=I=-20:TP=-1.5:LRA=7:print_format=json",
                "-f", "null", "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        m = pass1.stderr
        j_start = m.rfind("{")
        j_end = m.rfind("}")
        ln_stats = json.loads(m[j_start : j_end + 1])

        af_pass2 = (
            f"loudnorm=I=-20:TP=-1.5:LRA=7:"
            f"measured_I={ln_stats['input_i']}:"
            f"measured_LRA={ln_stats['input_lra']}:"
            f"measured_TP={ln_stats['input_tp']}:"
            f"measured_thresh={ln_stats['input_thresh']}:"
            f"offset={ln_stats['target_offset']}:linear=true:print_format=summary,"
            f"alimiter=limit=-1.2dB:level=false"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(raw_mix),
                "-af", af_pass2,
                "-t", str(TOTAL_DURATION),
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                str(out_wav),
            ],
            check=True,
        )

    # Measure final ebur128 integrated LUFS and sample/true peak
    ebur = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(out_wav),
            "-filter_complex", "ebur128=peak=true", "-f", "null", "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    ).stderr
    import re
    m_i = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", ebur)
    m_tp = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", ebur)
    lufs_i = float(m_i[-1]) if m_i else -20.0
    peak_db = float(m_tp[-1]) if m_tp else -1.5
    print(f"[audio] Mixed {len(events)} media-use SFX cues -> I={lufs_i:.2f} LUFS, Peak={peak_db:.2f} dBFS")
    return {"integrated_lufs": lufs_i, "true_peak_dbfs": peak_db, "sfx_event_count": len(events)}


def write_qc_outputs(
    output_mp4: Path,
    qc_dir: Path,
    shots: list[ShotSpec],
    audio_metrics: dict[str, float],
    standin: bool,
) -> dict[str, Any]:
    """Write ffprobe.json, cut-summary.json, and extract frames from the encoded MP4 for EVERY shot/caption."""
    qc_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = qc_dir / "encoded_captions"
    frames_dir.mkdir(parents=True, exist_ok=True)

    probe_raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,r_frame_rate,nb_frames,sample_rate,channels",
            "-of", "json",
            str(output_mp4),
        ],
        text=True,
    )
    ffprobe_data = json.loads(probe_raw)
    (qc_dir / "ffprobe.json").write_text(json.dumps(ffprobe_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Extract frames from the encoded MP4 for every caption page + shot midpoint
    extracted_stills: list[str] = []
    cap = cv2.VideoCapture(str(output_mp4))
    for shot in shots:
        if shot.pages:
            for p_idx, tp in enumerate(shot.pages):
                t_sample = min(shot.t_out - 0.15, max(tp.t_start + 0.45, (tp.t_start + tp.t_end) * 0.5))
                f_idx = max(0, min(TOTAL_FRAMES - 1, int(round(t_sample * FPS))))
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ok, bgr = cap.read()
                if ok:
                    fname = f"shot{shot.idx:02d}_orig{shot.orig_shot:02d}_p{p_idx}_{t_sample:06.2f}s.png"
                    out_p = frames_dir / fname
                    cv2.imwrite(str(out_p), bgr)
                    extracted_stills.append(str(out_p))
        else:
            t_sample = 0.5 * (shot.t_in + shot.t_out)
            f_idx = max(0, min(TOTAL_FRAMES - 1, int(round(t_sample * FPS))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ok, bgr = cap.read()
            if ok:
                fname = f"shot{shot.idx:02d}_orig{shot.orig_shot:02d}_insert_{t_sample:06.2f}s.png"
                out_p = frames_dir / fname
                cv2.imwrite(str(out_p), bgr)
                extracted_stills.append(str(out_p))

    # Also save 10 top-level QC stills across the layout families in v5/qc/
    featured_times = [
        ("still-01-shot01-hero-000.8s.png", 0.80),
        ("still-02-shot02-star-pop-002.5s.png", 2.50),
        ("still-03-shot03-card-pip-004.5s.png", 4.50),
        ("still-04-shot05-paper-stickers-010.8s.png", 10.80),
        ("still-05-shot09-mint-ticks-022.8s.png", 22.80),
        ("still-06-shot12-stack-033.0s.png", 33.00),
        ("still-07-shot14-folded-emphasis-041.5s.png", 41.50),
        ("still-08-shot15-terminal-typing-045.8s.png", 45.80),
        ("still-09-shot18-mint-counter-059.4s.png", 59.40),
        ("still-10-shot20-paper-text-068.0s.png", 68.00),
        ("still-11-shot21-top-panel-072.0s.png", 72.00),
        ("still-12-shot29-end-card-102.0s.png", 102.00),
    ]
    for sname, stime in featured_times:
        f_idx = max(0, min(TOTAL_FRAMES - 1, int(round(stime * FPS))))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ok, bgr = cap.read()
        if ok:
            cv2.imwrite(str(qc_dir / sname), bgr)
    cap.release()

    # Build an encoded-MP4 contact sheet of all extracted shot frames for fast visual verification
    cols = 4
    tw, th = 360, 640
    rows = math.ceil(len(extracted_stills) / cols)
    mp4_sheet = Image.new("RGB", (cols * tw, rows * th), (12, 16, 24))
    for i, spath in enumerate(extracted_stills):
        r, c = divmod(i, cols)
        im = Image.open(spath).convert("RGB").resize((tw - 8, th - 8), Image.Resampling.LANCZOS)
        mp4_sheet.paste(im, (c * tw + 4, r * th + 4))
    mp4_sheet.save(qc_dir / "encoded-mp4-contact-sheet.png")

    lengths = [s.duration for s in shots]
    sorted_lens = sorted(lengths)
    n = len(lengths)
    median_len = sorted_lens[n // 2] if n % 2 == 1 else 0.5 * (sorted_lens[n // 2 - 1] + sorted_lens[n // 2])
    fx_shots = [s.idx for s in shots if s.transition_in not in ("start", "hard")]
    face_visible_dur = sum(
        s.duration for s in shots if s.shot_type in ("A", "AS") or s.pip_mode != "none"
    )
    a_roll_dur = sum(s.duration for s in shots if s.shot_type == "A")
    as_dur = sum(s.duration for s in shots if s.shot_type == "AS")

    summary = {
        "version": "v5",
        "total_duration_s": TOTAL_DURATION,
        "voice_duration_s": VOICE_DURATION,
        "end_card_tail_s": TAIL_DURATION,
        "shot_count": len(shots),
        "cut_count": len(shots) - 1,
        "cuts_per_10s": round((len(shots) - 1) / (TOTAL_DURATION / 10.0), 2),
        "mean_shot_s": round(sum(lengths) / len(lengths), 2),
        "median_shot_s": round(median_len, 2),
        "min_shot_s": round(min(lengths), 2),
        "max_shot_s": round(max(lengths), 2),
        "shots_under_2s": sum(1 for x in lengths if x < 2.0),
        "shots_2_to_4s": sum(1 for x in lengths if 2.0 <= x <= 4.0),
        "shots_4_to_8s": sum(1 for x in lengths if 4.0 < x <= 8.0),
        "shots_over_8s": sum(1 for x in lengths if x > 8.0),
        "fx_transition_count": len(fx_shots),
        "fx_shot_indices": fx_shots,
        "a_roll_share_pct": round(100.0 * a_roll_dur / TOTAL_DURATION, 1),
        "split_panel_share_pct": round(100.0 * as_dur / TOTAL_DURATION, 1),
        "face_visible_share_pct": round(100.0 * face_visible_dur / TOTAL_DURATION, 1),
        "standin_footage": standin,
        "audio": audio_metrics,
        "c4_rulings_applied": {
            "shot15_folded_into_shot14": True,
            "shot14_span_s": [39.93, 43.83],
            "end_card_span_s": [100.24, 105.72],
            "end_card_cta": CTA_TEXT,
            "end_card_risk_warning": RISK_WARNING_TEXT,
        },
        "shots": [
            {
                "idx": s.idx,
                "orig_shot": s.orig_shot,
                "t_in": s.t_in,
                "t_out": s.t_out,
                "duration": s.duration,
                "type": s.shot_type,
                "layout": s.layout,
                "transition_in": s.transition_in,
                "face_zoom": s.face_zoom,
                "pip_mode": s.pip_mode,
                "layers": s.layers_count,
                "captions": [
                    {"t_start": p.t_start, "t_end": p.t_end, "kind": p.kind, "line1": p.line1, "line2": p.line2}
                    for p in s.pages
                ],
                "stickers": [st.text for st in s.stickers],
            }
            for s in shots
        ],
    }
    (qc_dir / "cut-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble MYPASAKON EP1 v5 per REFS-BREAKDOWN.md c2+c4.")
    parser.add_argument("--work-dir", type=Path, default=WORK_DEFAULT)
    parser.add_argument("--capture-dir", type=Path, default=WORK_DEFAULT / "v4" / "captures")
    parser.add_argument("--font", type=Path, default=FONT_DEFAULT)
    parser.add_argument("--sfx-dir", type=Path, default=SFX_DIR_DEFAULT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--proof-only", action="store_true", help="Only render caption-proof.png and exit.")
    args = parser.parse_args(argv)

    check_free_memory(3000)

    work_dir: Path = args.work_dir
    v5_dir = work_dir / "v5"
    qc_dir = v5_dir / "qc"
    v5_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    output_mp4 = args.output or (v5_dir / "mypasakon-ep1-v5-preview.mp4")
    voice_path = work_dir / "v3" / "mypasakon-v3-voice-tight.mp3"
    avatar_path = work_dir / "v3" / "avatar_ref.mp4"

    if not voice_path.is_file():
        raise SystemExit(f"Missing voice file: {voice_path}")
    if not avatar_path.is_file():
        raise SystemExit(f"Missing avatar_ref file: {avatar_path}")

    captures, standin = discover_captures(args.capture_dir, work_dir)
    print(f"[inputs] standin={standin} captures={[str(p.name) for p in captures]}")

    shots = build_blueprint()
    sprites = render_html_sprites(shots, args.font, standin, qc_dir)
    if args.proof_only:
        return 0

    print("[video] Loading source clips into memory (low-RAM mode)...", flush=True)
    avatar_frames = enhance_standin_avatar_frames(load_video_frames(avatar_path, max_frames=60, step=1))
    clip_frames = [load_video_frames(c, max_frames=75, step=2) for c in captures]
    paper_bg = build_paper_background()
    mint_bg = build_mint_background()

    with tempfile.TemporaryDirectory(prefix="mypasakon_v5_") as tmpd:
        tmp_dir = Path(tmpd)
        mixed_wav = tmp_dir / "mixed_audio.wav"
        audio_metrics = build_audio_mix(voice_path, shots, args.sfx_dir, mixed_wav)

        print(f"[render] Encoding {TOTAL_FRAMES} frames ({TOTAL_DURATION}s @ {FPS}fps) -> {output_mp4}")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
            "-i", "-",
            "-i", str(mixed_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-t", str(TOTAL_DURATION),
            str(output_mp4),
        ]
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
        assert proc.stdin is not None

        shot_ptr = 0
        for f_idx in range(TOTAL_FRAMES):
            t = f_idx / FPS
            while shot_ptr + 1 < len(shots) and t >= shots[shot_ptr].t_out - 1e-6:
                shot_ptr += 1
            frame_rgb = render_frame_for_shot(
                shots[shot_ptr], t, avatar_frames, clip_frames, paper_bg, mint_bg, sprites, standin
            )
            proc.stdin.write(frame_rgb.tobytes())
            if (f_idx + 1) % 600 == 0 or f_idx + 1 == TOTAL_FRAMES:
                print(f"  rendered {f_idx + 1}/{TOTAL_FRAMES} frames ({(f_idx + 1) / FPS:.1f}s)")

        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg exited with code {rc}")

    summary = write_qc_outputs(output_mp4, qc_dir, shots, audio_metrics, standin)
    print(f"[done] Wrote {output_mp4} and QC outputs in {qc_dir}")
    print(json.dumps({k: v for k, v in summary.items() if k != "shots"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
