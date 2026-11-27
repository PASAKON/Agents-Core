#!/usr/bin/env python3
"""
build_v6_1_ep7_chart_hierarchy.py — Build BLACK LIQUIDITY V6.1 Pure Knowledge EP.07 (65.88s)
Addressing all 4 CEO review points on Q-20261116-1150-6fed:
  1. Real MT4/MT5 Chart Screen Recordings from Google Drive synced to trading clauses:
     - DRV_MT5_gold_m1_chart_buy_lines (0.70 - 2.60s)
     - DRV_MT5_swap_loss_history (2.60 - 4.65s)
     - DRV_MT5_red_drawdown_orders (8.10 - 9.85s)
     - DRV_MT5_xauusd_m15_sl_chart (9.85 - 13.20s)
     - DRV_MT5_xauusd_h1_chart_pan (19.65 - 21.90s)
     - DRV_MT5_candle_crash_m1 (34.35 - 35.75s)
     - DRV_MT5_close_all_positions_popup (42.60 - 44.80s)
     - DRV_MT5_xauusd_set_sl_close_profit (44.80 - 47.00s)
     - DRV_MT5_gold_m1_green_candles (54.80 - 59.70s)
  2. Single-Focus Visual Hierarchy (Text vs. Footage — Never Compete):
     - mode="chart" / mode="footage": 100% clear center (y=240..1230px unobstructed), ONLY compact lower-third subtitle (.cap at y=1315px).
     - mode="text_bg": Calm dark-blurred ambient background (GaussianBlur + 0.35x dim, zero focal point) + ONE clean center card (and ZERO lower-third .cap).
  3. 100% Unified Font ('Kanit' across all headings, cards, badges, numbers, and subtitles; zero Archivo/system fallback).
  4. Zero Overlapping Boxes/Text (.badge is static flex pill above .nm, zero calloutBox, strict mutual exclusion between .cap and center cards).
"""
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

sys.path.insert(0, "/Users/gob/MoonieXHQ/Agents/Core/scripts")
import build_bl_v4_lungtep_style as v4

BRAIN_DIR = Path("/Users/gob/.gemini/antigravity/brain/1ec08f78-528c-484f-be60-038384d3be35")
sys.path.insert(0, str(BRAIN_DIR / "scratch"))
import build_v5_batch as b5

BROLL_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/broll-incoming")
WORK_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/basket-pilot1-work")
SRC_TEMPLATE_DIR = WORK_DIR / "cut_pilot1_A_v5_58s_pure"


class FastClipCache:
    """Memory-bounded (LRU=4) clip loader."""
    def __init__(self, broll_dir: Path):
        self.broll_dir = broll_dir
        self.cache: Dict[str, List[np.ndarray]] = {}

    def get_frames(self, clip_id: str) -> List[np.ndarray]:
        if clip_id in self.cache:
            return self.cache[clip_id]
        if len(self.cache) >= 4:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        path = self.broll_dir / f"{clip_id}.mp4"
        if not path.exists():
            raise FileNotFoundError(f"Missing clip: {path}")
        cap = cv2.VideoCapture(str(path))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        max_raw = int(round(src_fps * 6.5))
        raw_frames: List[np.ndarray] = []
        while len(raw_frames) < max_raw:
            ok, frm = cap.read()
            if not ok:
                break
            if frm.shape[1] != v4.WIDTH or frm.shape[0] != v4.HEIGHT:
                frm = cv2.resize(frm, (v4.WIDTH, v4.HEIGHT), interpolation=cv2.INTER_LINEAR)
            raw_frames.append(frm)
        cap.release()
        if not raw_frames:
            raise RuntimeError(f"Zero frames decoded from {path}")
        dur = len(raw_frames) / src_fps
        n_out = max(1, int(round(dur * v4.FPS)))
        resampled: List[np.ndarray] = []
        for i in range(n_out):
            t = i / v4.FPS
            src_idx = min(len(raw_frames) - 1, int(round(t * src_fps)))
            resampled.append(raw_frames[src_idx])
        self.cache[clip_id] = resampled
        return resampled


def render_v6_1_plate_track(out_mp4: Path, schedule: List[Dict[str, object]], dur: float) -> None:
    """Render plate track with mode-aware visual hierarchy:
       - mode == 'chart': 1.0x scale (no crop), boosted +16% brightness so MT5 UI is crisp after .plate-clear
       - mode == 'footage': normal living camera push, clear focal subject
       - mode == 'text_bg': Gaussian blur (45x45) + 0.34x darkened calm background with zero focal clutter
    """
    cache = FastClipCache(BROLL_DIR)
    n_frames = int(round(dur * v4.FPS))
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{v4.WIDTH}x{v4.HEIGHT}", "-r", str(v4.FPS),
        "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "18",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    seg_for_frame: List[int] = [0] * n_frames
    for s_idx, seg in enumerate(schedule):
        f0 = max(0, int(round(float(seg["start"]) * v4.FPS)))
        f1 = min(n_frames, int(round(float(seg["end"]) * v4.FPS)))
        for f in range(f0, f1):
            seg_for_frame[f] = s_idx

    def raw_seg_frame(s_idx: int, global_t: float) -> np.ndarray:
        seg = schedule[s_idx]
        mode = str(seg.get("mode", "footage"))
        frames = cache.get_frames(str(seg["clip"]))
        local_t = max(0.0, global_t - float(seg["start"]))
        media_t = float(seg["mstart"]) + local_t
        base_scale = float(seg["scale"])
        if mode == "chart":
            live_scale = 1.00
        else:
            live_scale = base_scale * (1.0 + 0.015 * min(local_t, 3.0))
        frm = v4.sample_cropped_frame(frames, media_t, live_scale, tuple(seg["focus"]))
        if mode == "chart":
            # Compensate for .plate-clear brightness(.84) so MT5 chart screen is 100% native brightness
            frm = np.clip(frm.astype(np.float32) * 1.18, 0, 255).astype(np.uint8)
        elif mode == "text_bg":
            # Calm, soft-blurred, low-contrast dark ambient plate so center text card has 100% focus
            blurred = cv2.GaussianBlur(frm, (45, 45), 18)
            frm = np.clip(blurred.astype(np.float32) * 0.34, 0, 255).astype(np.uint8)
        return frm

    for f_idx in range(n_frames):
        t = f_idx / v4.FPS
        s_idx = seg_for_frame[f_idx]
        seg = schedule[s_idx]
        seg_start = float(seg["start"])
        trans_type = str(seg["trans"])

        curr_frm = raw_seg_frame(s_idx, t)
        trans_dur = {
            "hook_punch": 0.20,
            "whip_pan_h": 0.16,
            "whip_tilt_v": 0.16,
            "scale_punch": 0.12,
            "exposure_flash": 0.14,
            "neg_shockwave": 0.20,
            "prism_shatter": 0.18,
            "gravity_flip": 0.16,
            "rgb_glitch": 0.16,
        }.get(trans_type, 0.14)

        dt = t - seg_start
        if 0.0 <= dt < trans_dur:
            prev_frm = raw_seg_frame(max(0, s_idx - 1), t) if s_idx > 0 else curr_frm
            rel_p = dt / trans_dur
            frm = v4.apply_transition_effect(prev_frm, curr_frm, trans_type, rel_p)
        else:
            frm = curr_frm

        assert proc.stdin is not None
        proc.stdin.write(frm.tobytes())

    assert proc.stdin is not None
    proc.stdin.close()
    proc.wait()
    print(f"[v6.1_plate] Rendered {out_mp4.name} ({out_mp4.stat().st_size:,} bytes, {n_frames} frames)", flush=True)


# ============================================================================
# EP.07 V6.1 (65.88s) — Single-Focus Hierarchy + Real MT5 Chart Screen Footage
# ============================================================================
SCHED_EP7_V6_1: List[Dict[str, object]] = [
    # Beat 1: Hook (0.00 - 8.10s)
    {"start": 0.00, "end": 0.70, "mode": "footage", "clip": "DRV_clip67", "mstart": 0.10, "scale": 1.06, "focus": (0.50, 0.46), "trans": "hook_punch", "sfx": "sub_shutter_hit"},
    {"start": 0.70, "end": 2.60, "mode": "chart",   "clip": "DRV_MT5_gold_m1_chart_buy_lines", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 2.60, "end": 4.65, "mode": "chart",   "clip": "DRV_MT5_swap_loss_history", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 4.65, "end": 6.50, "mode": "footage", "clip": "PAIN_CHAR_ots-04am-swap-fee", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "exposure_flash", "sfx": "sub_drop_flash"},
    {"start": 6.50, "end": 8.10, "mode": "text_bg", "clip": "DRV_clip03", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},

    # Beat 2: Mirror Failed Habit (8.10 - 24.15s)
    {"start": 8.10, "end": 9.85, "mode": "chart",   "clip": "DRV_MT5_red_drawdown_orders", "mstart": 0.05, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 9.85, "end": 13.20, "mode": "chart",  "clip": "DRV_MT5_xauusd_m15_sl_chart", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 13.20, "end": 15.65, "mode": "footage", "clip": "PAIN_CHAR_front-phone-backcasing", "mstart": 0.20, "scale": 1.05, "focus": (0.50, 0.48), "trans": "prism_shatter", "sfx": "prism_shatter_sfx"},
    {"start": 15.65, "end": 17.60, "mode": "text_bg", "clip": "DRV_clip19", "mstart": 0.20, "scale": 1.06, "focus": (0.50, 0.48), "trans": "neg_shockwave", "sfx": "neg_shockwave_zap"},
    {"start": 17.60, "end": 19.65, "mode": "text_bg", "clip": "DRV_clip28", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.48), "trans": "whip_tilt_v", "sfx": "whip_tilt_riser"},
    {"start": 19.65, "end": 22.10, "mode": "chart",   "clip": "DRV_MT5_xauusd_h1_chart_pan", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 22.10, "end": 24.15, "mode": "footage", "clip": "OCT_sand_slips_through_fingers", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},

    # Beat 3: Hidden Brain Mechanism (24.15 - 40.25s)
    {"start": 24.15, "end": 26.50, "mode": "text_bg", "clip": "DRV_clip79", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "exposure_flash", "sfx": "sub_drop_flash"},
    {"start": 26.50, "end": 29.40, "mode": "text_bg", "clip": "DRV_clip45", "mstart": 0.20, "scale": 1.12, "focus": (0.50, 0.50), "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz"},
    {"start": 29.40, "end": 32.95, "mode": "footage", "clip": "BRAIN_CHAR_front-bed-03am-phone-back", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 32.95, "end": 34.40, "mode": "footage", "clip": "BRAIN_CHAR_side-blue-glare-eyes", "mstart": 1.50, "scale": 1.06, "focus": (0.52, 0.46), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 34.40, "end": 35.75, "mode": "chart",   "clip": "DRV_MT5_candle_crash_m1", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 35.75, "end": 40.25, "mode": "text_bg", "clip": "OCT_trader_slams_desk_red_monitors", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.50), "trans": "neg_shockwave", "sfx": "neg_shockwave_zap"},

    # Beat 4: Mechanism Pivot (40.25 - 52.30s)
    {"start": 40.25, "end": 42.60, "mode": "footage", "clip": "DRV_clip84", "mstart": 0.20, "scale": 1.06, "focus": (0.50, 0.48), "trans": "gravity_flip", "sfx": "gravity_flip_swoop"},
    {"start": 42.60, "end": 44.85, "mode": "chart",   "clip": "DRV_MT5_close_all_positions_popup", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 44.85, "end": 47.00, "mode": "chart",   "clip": "DRV_MT5_xauusd_set_sl_close_profit", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 47.00, "end": 49.60, "mode": "footage", "clip": "FIX_CHAR_ots-close-laptop-5pct-limit", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 49.60, "end": 52.30, "mode": "footage", "clip": "FIX_CHAR_warm-lightbar-sleepmask", "mstart": 0.15, "scale": 1.04, "focus": (0.50, 0.50), "trans": "exposure_flash", "sfx": "sub_drop_flash"},

    # Beat 5: Friction Removal (52.30 - 59.70s)
    {"start": 52.30, "end": 54.80, "mode": "footage", "clip": "PROD01_BL_03_put_on_rest", "mstart": 0.10, "scale": 1.04, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 54.80, "end": 59.70, "mode": "chart",   "clip": "DRV_MT5_gold_m1_green_candles", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_tilt_v", "sfx": "whip_tilt_riser"},

    # Beat 6: Pain Callback + Takeaway Summary (59.70 - 65.88s)
    {"start": 59.70, "end": 62.50, "mode": "text_bg", "clip": "DRV_clip18", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.48), "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz"},
    {"start": 62.50, "end": 65.88, "mode": "text_bg", "clip": "DRV_clip77", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
]

# STRICT SINGLE-FOCUS JS:
# - During mode="chart" or mode="footage": ONLY lower-third caption(at, out, text, 1315) is shown; center of screen is 100% clear!
# - During mode="text_bg": ONLY ONE center card is shown (kinetic, check, cards, or rules); ZERO lower-third caption!
# - ZERO calloutBox anywhere!
JS_EP7_V6_1 = """
      // Beat 1 (0.00 - 8.10s): Hook
      // 0.00 - 4.65s [CHART: GOLD M1 Buy Lines + Swap History] -> Lower-third subtitle only
      caption(0.14, 4.60, 'คนเทรดทองที่<span class="y nb">ถือออเดอร์ค้างคืน</span> ไม่ได้เสียแค่<span class="n nb">ค่า Swap ตอนตี 4</span>', 1315);
      // 4.65 - 6.50s [FOOTAGE: Veo 3.1 OTS 04:00 AM Swap Fee] -> Lower-third subtitle only
      caption(4.65, 6.45, 'แต่กำลังจ่าย<span class="y nb">ต้นทุนแฝงที่แพงที่สุด</span>โดยไม่รู้ตัว', 1315);
      // 6.50 - 8.10s [TEXT_BG: Blurred calm ambient] -> Center kinetic punchline only
      kinetic(680, 6.52, 8.06, [
        { c: "bl-md", h: 'ต้นทุนที่แพงที่สุด', d: 0.35, g: 0.35 },
        { c: "bl-lg", h: 'คือ<span class="n nb">สมองตัวเองพัง</span>ต่างหาก', d: 0.38, g: 0.38 }
      ], 420);

      // Beat 2 (8.10 - 24.15s): Mirror Failed Habit
      // 8.10 - 13.20s [CHART: MT5 Red Drawdown -25.01 USD + XAUUSD M15 SL Chart] -> Lower-third subtitle only
      caption(8.15, 13.15, 'พอไม้ติดลบก็<span class="n nb">ไม่กล้าคัดลอส</span> หวังว่าตื่นมากราฟจะกลับตัว', 1315);
      // 13.20 - 15.65s [FOOTAGE: Veo 3.1 Front Phone Backcasing] -> Lower-third subtitle only
      caption(13.22, 15.60, 'พอถึง <span class="y nb">04:00 น.</span> โบรกก็หัก<span class="n nb">ค่า Swap ซ้ำทุกคืน</span>', 1315);
      // 15.65 - 19.65s [TEXT_BG: Blurred calm ambient] -> Center check card only
      check(640, 15.68, 19.60, 'ยิ่งถือข้ามคืน <span class="n nb">ต้นทุนยิ่งรั่ว</span>', [
        { k: "3x", x: 'คืนวันพุธ <span class="n nb">โดนหักค่า Swap คูณสาม</span>', t: 15.78 },
        { k: "✗", x: 'กำไรที่ควรได้ <span class="n nb">โดนค่าธรรมเนียมกินเรียบ</span>', t: 17.65 }
      ]);
      // 19.65 - 24.15s [CHART: MT5 XAUUSD H1 Chart + Sand] -> Lower-third subtitle only
      caption(19.68, 24.10, 'ไม่ใช่เพราะกราฟไม่วิ่ง แต่ยอมจ่าย<span class="n nb">ค่าเช่าออเดอร์</span>แลกความหวัง', 1315);

      // Beat 3 (24.15 - 40.25s): Hidden Brain Mechanism
      // 24.15 - 29.40s [TEXT_BG: Blurred calm ambient] -> Center single card only
      cards(620, 24.20, 29.35, 'ผลกระทบต่อ<span class="n nb">สมองตอนนอน</span>', [
        { b: "NO DEEP SLEEP", n: "สมองไม่เคยเข้าโหมดหลับลึก", c: "จิตใต้สำนึกพะวงกราฟตลอดทั้งคืน", t: 24.45 }
      ], 1);
      // 29.40 - 32.95s [FOOTAGE: Veo 3.1 Waking Up 03:00 AM in Bed] -> Lower-third subtitle only
      caption(29.45, 32.90, 'สะดุ้งตื่นมา<span class="y nb">หยิบมือถือเช็กกราฟตี 3</span> ทุกคืน', 1315);
      // 32.95 - 35.75s [FOOTAGE + CHART: Side Blue Glare + MT5 M1 Crash] -> Lower-third subtitle only
      caption(33.00, 35.70, 'แสงจอพุ่งเข้าตา <span class="n nb">คอร์ติซอลพุ่งปรี๊ด</span>ตั้งแต่เช้ามืด', 1315);
      // 35.75 - 40.25s [TEXT_BG: Blurred calm ambient] -> Center rule card only
      rules(620, [
        {
          n: "01",
          t: 35.85,
          o: 40.18,
          h: 'พอตื่นมาเทรด<span class="y nb">วันรุ่งขึ้น</span>',
          d: 'สมองส่วนตัดสินใจพังยับ <span class="n nb">และกดมั่วหนักกว่าเดิม</span>'
        }
      ]);

      // Beat 4 (40.25 - 52.30s): Mechanism Pivot (22:30 Cutoff + Phone Out of Bed)
      // 40.25 - 42.60s [FOOTAGE: Focused Trader] -> Lower-third subtitle only
      caption(40.30, 42.55, 'กฎเหล็ก 2 ข้อของ<span class="y nb">เทรดเดอร์สายอยู่รอด</span>', 1315);
      // 42.60 - 47.00s [CHART: MT5 Close All Positions Popup + Set SL/Close Profit] -> Lower-third subtitle only
      caption(42.65, 46.95, 'ข้อ 1: <span class="y nb">เคลียร์ไม้หรือบังหน้าทุน</span>ก่อน 22:30 น. ห้ามแบกไม้ติดลบ', 1315);
      // 47.00 - 52.30s [FOOTAGE: Veo 3.1 Close Laptop + Sleep Mask] -> Lower-third subtitle only
      caption(47.05, 52.25, 'ข้อ 2: <span class="y nb">ปิดแจ้งเตือนและคว่ำมือถือ</span>ห่างเตียง ให้สมองหลับลึก 100%', 1315);

      // Beat 5 (52.30 - 59.70s): Friction Removal
      // 52.30 - 59.70s [FOOTAGE + CHART: Rest + MT5 Gold Green Candles] -> Lower-third subtitle only
      caption(52.35, 59.65, 'ประหยัดทั้ง<span class="y nb">ค่า Swap</span> และตื่นมาเทรดด้วย<span class="y nb">สมองคมกริบ</span>ทันที', 1315);

      // Beat 6 (59.70 - 65.88s): Takeaway Summary Card
      // 59.70 - 65.88s [TEXT_BG: Blurred calm ambient] -> Center 2-card summary only
      cards(560, 59.75, 65.78, 'สรุปกฎ<span class="y nb">ตัดวงจรค่า Swap ข้ามคืน</span>', [
        { b: "RULE 01 · 22:30", n: "เคลียร์ไม้หรือบังหน้าทุนก่อนนอน", c: "ห้ามปล่อยไม้ติดลบข้ามคืนเด็ดขาด", t: 59.95 },
        { b: "RULE 02 · SLEEP", n: "คว่ำมือถือห่างเตียง พักสมอง 100%", c: "ตื่นมาเทรดเช้าวันใหม่ด้วยสติเต็มร้อย", t: 62.55 }
      ], 2);
"""

CUSTOM_CSS_PATCH = """
      /* V6.1 Single-Font ('Kanit' everywhere) & Non-Overlapping Card Layout */
      #root, #root *, .bl-card .nm, .bl-card .cl, .bl-card .badge,
      .bl-rulecard .idx, .bl-rulecard .hd, .bl-rulecard .dt,
      .bl-row .tick, .bl-row .tx, .bl-stat .big, .bl-stat .lb,
      .cap, .bl-legal, .bug .b1, .bug .b2, .bug .dt2 {
        font-family: 'Kanit', sans-serif !important;
      }
      .bl-card {
        position: relative;
        background: rgba(10,11,13,.88) !important;
        border: 2px solid rgba(255,255,255,.16) !important;
        border-left: 10px solid var(--neon) !important;
        border-radius: 20px !important;
        padding: 24px 30px !important;
        text-align: left !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 8px !important;
      }
      .bl-card .badge {
        position: static !important;
        display: inline-block !important;
        background: var(--red) !important;
        color: #fff !important;
        font-weight: 800 !important;
        font-size: 22px !important;
        padding: 4px 14px !important;
        border-radius: 8px !important;
        letter-spacing: .03em !important;
        margin-bottom: 2px !important;
      }
      .bl-card .nm {
        font-weight: 800 !important;
        font-size: 44px !important;
        line-height: 1.24 !important;
        color: #FFFFFF !important;
        width: 100% !important;
      }
      .bl-card .cl {
        font-weight: 600 !important;
        font-size: 34px !important;
        line-height: 1.30 !important;
        color: #D7DCE0 !important;
        margin-top: 0 !important;
        width: 100% !important;
      }
      .bl-rulecard .hd {
        font-size: 58px !important;
        line-height: 1.28 !important;
      }
      .bl-rulecard .dt {
        font-size: 40px !important;
        line-height: 1.34 !important;
      }
      .cap {
        font-size: 44px !important;
        line-height: 1.28 !important;
        background: rgba(5,6,8,.92) !important;
        border: 1.5px solid rgba(255,255,255,.14) !important;
        padding: 18px 28px !important;
        border-radius: 18px !important;
      }
"""


def build_workdir_ep7_v6_1(dst_dir: Path, duration_s: float, plate_mp4: Path, audio_wav: Path, js_body: str) -> None:
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    for fn in ["hyperframes.json", "package.json"]:
        shutil.copy2(SRC_TEMPLATE_DIR / fn, dst_dir / fn)
    for sym in ["node_modules", "assets"]:
        s = SRC_TEMPLATE_DIR / sym
        if s.exists():
            os.symlink(s.resolve(), dst_dir / sym)

    (dst_dir / "clips").mkdir(exist_ok=True)
    (dst_dir / "audio").mkdir(exist_ok=True)

    os.symlink(plate_mp4.resolve(), dst_dir / "clips" / "v4_plate_track.mp4")
    shutil.copy2(audio_wav, dst_dir / "audio" / audio_wav.name)
    shutil.copy2(audio_wav, dst_dir / "audio.wav")

    html = (SRC_TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'\s*<div class="bl-ai-pill">[^<]*</div>', "", html)
    html = html.replace("9 พ.ย. 69", "16 พ.ย. 69")
    html = html.replace("font-family: Archivo, sans-serif;", "font-family: 'Kanit', sans-serif;")
    html = html.replace("overflow:hidden", "overflow:visible")
    html = html.replace('wrap.style.height = (pitch * visible) + "px";', '// wrap height unlocked for full card visibility')
    html = html.replace("</style>", CUSTOM_CSS_PATCH + "\n    </style>")
    html = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{duration_s:.2f}"', html)
    html = re.sub(r'src="clips/[^"]+"', 'src="clips/v4_plate_track.mp4"', html)
    html = re.sub(r'src="audio/[^"]+"', f'src="audio/{audio_wav.name}"', html)

    marker_start = "      calloutBox("
    marker_end = '      window.__timelines["main"] = tl;'
    idx0 = html.find(marker_start)
    idx1 = html.find(marker_end)
    assert idx0 != -1 and idx1 != -1 and idx1 > idx0, f"Markers invalid in template index.html ({idx0}, {idx1})"
    html = html[:idx0] + js_body.strip("\n") + "\n\n" + html[idx1:]

    (dst_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"[OK] Built workdir {dst_dir.name} (dur={duration_s:.2f}s)", flush=True)


def main() -> int:
    dur = 65.88
    clips = [str(s["clip"]) for s in SCHED_EP7_V6_1]
    assert len(clips) == len(set(clips)), f"Duplicate clip in EP7 V6.1: {clips}"
    for c in clips:
        p = BROLL_DIR / f"{c}.mp4"
        if not p.exists():
            raise FileNotFoundError(f"Missing clip for EP7 V6.1: {p}")
    print(f"[VERIFIED] EP7 V6.1: all {len(clips)} clips exist and are 100% unique (including 9 real MT5 chart cuts)!", flush=True)

    plate_mp4 = WORK_DIR / "clips" / "v6_1_plate_EP7.mp4"
    render_v6_1_plate_track(plate_mp4, SCHED_EP7_V6_1, dur)

    mixed_wav = WORK_DIR / "audio" / "EP7_v6_66s_14lufs.wav"
    assert mixed_wav.exists(), f"Missing mixed audio: {mixed_wav}"

    workdir = WORK_DIR / "cut_ep7_v6_1_66s_pure"
    build_workdir_ep7_v6_1(workdir, dur, plate_mp4, mixed_wav, JS_EP7_V6_1)

    out_dir = WORK_DIR / "finals_v5_mass_sfx"
    out_mp4 = out_dir / "BL-EP7-V6.1-66s-PureKnowledge-MT5Chart-SingleFocus.mp4"
    print(f"[HyperFrames] Rendering {out_mp4.name}...", flush=True)
    subprocess.run(
        ["npx", "--yes", "hyperframes", "render", "--output", str(out_mp4), "--fps", "30", "--quality", "standard"],
        cwd=str(workdir),
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    sheet_path = BRAIN_DIR / "sheet_EP7_v6_1_66s_mt5chart.jpg"
    # Extract 1 frame at the midpoint of each of the first 25 segments (5x5 grid)
    from PIL import Image, ImageDraw
    tiles = []
    for idx, seg in enumerate(SCHED_EP7_V6_1):
        mid_t = (float(seg["start"]) + float(seg["end"])) / 2.0
        jpg = workdir / f"seg_{idx:02d}.jpg"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-ss", f"{mid_t:.2f}", "-i", str(out_mp4), "-frames:v", "1", "-vf", "scale=360:640", str(jpg)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        im = Image.open(jpg).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 360, 32], fill=(0, 0, 0))
        d.text((6, 8), f"#{idx+1:02d} [{seg['mode'].upper()}] @{mid_t:.1f}s {str(seg['clip'])[:18]}", fill=(255, 230, 0))
        tiles.append(im)

    cols = 6
    rows = (len(tiles) + cols - 1) // cols
    grid = Image.new("RGB", (cols * 360, rows * 640), (10, 10, 14))
    for i, im in enumerate(tiles):
        grid.paste(im, ((i % cols) * 360, (i // cols) * 640))
    grid.save(sheet_path, quality=90)
    print(f"[DONE] {out_mp4.name} ({out_mp4.stat().st_size:,} bytes) + {sheet_path.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
