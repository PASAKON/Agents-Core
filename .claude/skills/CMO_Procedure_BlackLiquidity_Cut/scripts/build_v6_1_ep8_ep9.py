#!/usr/bin/env python3
"""
build_v6_1_ep8_ep9.py — Build BLACK LIQUIDITY V6.1 Pure Knowledge EP.08 (67.68s) & EP.09 (66.11s)
Following the CEO-approved V6.1 architecture (Q-20261116-1315-f2f8):
  1. 8–9 Framed Real MT5 Chart & Order Screen Recordings (mode="chart", y=430..1200px) per episode.
  2. Strict Single-Focus Hierarchy:
     - mode="chart" / mode="footage": 100% clear center (no boxes covering chart/character), ONLY compact lower-third .cap at cy=1315px.
     - mode="text_bg": Softly blurred & darkened (GaussianBlur 45x45 + 0.34x) background + ONE center card (and ZERO lower-third .cap).
  3. 100% Unified 'Kanit' font across all elements.
  4. Zero overlapping boxes or clipped cards (static flex-pill .badge, overflow:visible wrapper, zero calloutBox).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "/Users/gob/MoonieXHQ/Agents/Core/scripts")
import build_bl_v4_lungtep_style as v4

BRAIN_DIR = Path("/Users/gob/.gemini/antigravity/brain/1ec08f78-528c-484f-be60-038384d3be35")
sys.path.insert(0, str(BRAIN_DIR / "scratch"))
import build_v6_1_ep7_chart_hierarchy as v61

BROLL_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/broll-incoming")
WORK_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/basket-pilot1-work")


# ============================================================================
# EP.08 V6.1 (67.68s) — กับดัก 2 ทุ่มครึ่ง! ทำไมเทรดทองช่วงข่าว US เปิด ถึงโดนลากกินทั้งขา Buy และ Sell
# ============================================================================
SCHED_EP8_V6_1: List[Dict[str, object]] = [
    # Beat 1: Hook (0.00 - 10.95s)
    {"start": 0.00, "end": 1.65, "mode": "footage", "clip": "DRV_clip28", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "hook_punch", "sfx": "sub_shutter_hit"},
    {"start": 1.65, "end": 3.70, "mode": "chart",   "clip": "DRV_MT5_m15_whipsaw_drop", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 3.70, "end": 5.95, "mode": "footage", "clip": "PAIN_CHAR_ots-2030-news-whipsaw", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 5.95, "end": 7.45, "mode": "footage", "clip": "CHAR_EP5_B1_HOOK_01", "mstart": 0.25, "scale": 1.08, "focus": (0.50, 0.46), "trans": "exposure_flash", "sfx": "sub_drop_flash"},
    {"start": 7.45, "end": 10.95, "mode": "text_bg", "clip": "DRV_clip07", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},

    # Beat 2: Mirror Failed Habit (10.95 - 27.35s)
    {"start": 10.95, "end": 13.40, "mode": "chart",   "clip": "DRV_MT5_gold_m1_chart_buy_lines", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 13.40, "end": 15.80, "mode": "chart",   "clip": "DRV_MT5_m15_sell_buy_buttons_spike", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 15.80, "end": 18.60, "mode": "chart",   "clip": "DRV_MT5_candle_crash_m1", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "prism_shatter", "sfx": "prism_shatter_sfx"},
    {"start": 18.60, "end": 22.05, "mode": "chart",   "clip": "DRV_MT5_red_drawdown_orders", "mstart": 0.05, "scale": 1.00, "focus": (0.50, 0.50), "trans": "neg_shockwave", "sfx": "neg_shockwave_zap"},
    {"start": 22.05, "end": 24.50, "mode": "footage", "clip": "OCT_eye_reflects_falling_red_candles", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.48), "trans": "whip_tilt_v", "sfx": "whip_tilt_riser"},
    {"start": 24.50, "end": 27.35, "mode": "footage", "clip": "OCT_soap_bubble_bursts_gold_dust", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},

    # Beat 3: Hidden Market & Brain Mechanism (27.35 - 42.90s)
    {"start": 27.35, "end": 30.45, "mode": "text_bg", "clip": "DRV_clip38", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "exposure_flash", "sfx": "sub_drop_flash"},
    {"start": 30.45, "end": 33.50, "mode": "text_bg", "clip": "DRV_clip20", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.48), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 33.50, "end": 36.10, "mode": "chart",   "clip": "DRV_MT5_xauusd_m5_sl_lines", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 36.10, "end": 38.45, "mode": "footage", "clip": "OCT_gold_coin_bait_fish_hook", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.50), "trans": "neg_shockwave", "sfx": "neg_shockwave_zap"},
    {"start": 38.45, "end": 42.90, "mode": "text_bg", "clip": "DRV_clip45", "mstart": 0.20, "scale": 1.12, "focus": (0.50, 0.50), "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz"},

    # Beat 4: Mechanism Pivot (42.90 - 54.80s)
    {"start": 42.90, "end": 46.10, "mode": "footage", "clip": "FIX_CHAR_ots-hands-off-mouse-15min", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "gravity_flip", "sfx": "gravity_flip_swoop"},
    {"start": 46.10, "end": 49.00, "mode": "footage", "clip": "DRV_clip75", "mstart": 0.20, "scale": 1.06, "focus": (0.50, 0.46), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 49.00, "end": 51.90, "mode": "chart",   "clip": "DRV_MT5_xauusd_m15_sl_chart", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 51.90, "end": 54.80, "mode": "chart",   "clip": "DRV_MT5_xauusd_h1_chart_pan", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "exposure_flash", "sfx": "sub_drop_flash"},

    # Beat 5: Friction Removal (54.80 - 61.95s)
    {"start": 54.80, "end": 58.10, "mode": "footage", "clip": "OCT_gold_watch_wrist_closeup", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "whip_tilt_v", "sfx": "whip_tilt_riser"},
    {"start": 58.10, "end": 61.95, "mode": "chart",   "clip": "DRV_MT5_gold_m1_green_candles", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},

    # Beat 6: Takeaway Summary Card (61.95 - 67.68s)
    {"start": 61.95, "end": 64.80, "mode": "text_bg", "clip": "DRV_clip18", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.48), "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz"},
    {"start": 64.80, "end": 67.68, "mode": "text_bg", "clip": "DRV_clip77", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
]

JS_EP8_V6_1 = """
      // Beat 1 (0.00 - 10.95s): Counter-Intuitive Hook
      caption(0.16, 5.90, 'ทำไมตอน <span class="y nb">20:30 น.</span> ข่าวออกทีไร โดนลากกิน SL <span class="n nb">ทั้งขา Buy และ Sell</span>', 1315);
      caption(5.98, 7.40, 'ไม่ใช่เพราะ<span class="y nb">เดาทางข่าวผิด</span>นะเว้ย', 1315);
      kinetic(680, 7.48, 10.88, [
        { c: "bl-md", h: 'แต่เพราะกระโดดเข้าตอน<span class="n nb">สเปรดถ่าง</span>', d: 0.38, g: 0.38 },
        { c: "bl-lg", h: 'และสมองกำลัง<span class="y nb">เมาโดพามีน</span>', d: 0.42, g: 0.42 }
      ], 420);

      // Beat 2 (10.95 - 27.35s): Mirror Failed Habit (Chart & Footage Focus)
      caption(11.00, 15.75, 'เห็นแท่งทองกระชากขึ้นตอน <span class="y nb">20:30 น.</span> ก็รีบกด <span class="y nb">Buy ตามทันที</span>', 1315);
      caption(15.82, 22.00, 'พอกดปุ๊บโดนตบกิน SL <span class="n nb">กด Sell สวนก็ไส้แตกทั้งสองฝั่ง</span>', 1315);
      caption(22.08, 27.30, 'ไม่ใช่เพราะเจ้ามือแกล้ง แต่วินาทีข่าวออก <span class="n nb">สภาพคล่องหายวับพร้อมกัน</span>', 1315);

      // Beat 3 (27.35 - 42.90s): Hidden Market & Brain Mechanism
      cards(600, 27.42, 33.45, 'กลไกตลาดวินาที<span class="n nb">ข่าวประกาศ</span>', [
        { b: "SPREAD 3-5x", n: "โบรกถ่างสเปรดกว้างขึ้น 3-5 เท่า", c: "กดถูกทางก็ติดลบต้นทุนสเปรดตั้งแต่วินาทีแรก", t: 27.65 }
      ], 1);
      caption(33.52, 38.40, 'โดนบวกต้นทุนสเปรด แถมเจอ <span class="n nb">Slippage ลากไปติดปลายไส้</span>', 1315);
      rules(620, [
        {
          n: "01",
          t: 38.50,
          o: 42.82,
          h: 'ยิ่งกราฟวิ่งเร็ว <span class="y nb">สมองหลั่งโดพามีน</span>',
          d: 'กระตุ้นให้กดรัว <span class="n nb">โดยไม่ทันคำนวณระยะ Stop Loss</span>'
        }
      ]);

      // Beat 4 (42.90 - 54.80s): Mechanism Pivot (15-Minute Hands-Off Rule)
      caption(42.95, 48.95, 'กฎเหล็กมืออาชีพ: <span class="y nb">ล็อกมือ 15 นาทีหลังข่าวออก</span> รอจนสเปรดแคบปกติ', 1315);
      caption(49.02, 54.75, 'รอให้กราฟปิดแท่ง <span class="y nb">M15</span> จบก่อน เพื่อดูว่าฝั่งไหน<span class="n nb">โดนกวาดสภาพคล่องไปแล้ว</span>', 1315);

      // Beat 5 (54.80 - 61.95s): Friction Removal
      caption(54.85, 61.88, 'ตั้งเตือน <span class="y nb">20:25 น.</span> แล้ววางมือจากเมาส์ถึง <span class="y nb">20:45 น.</span> ได้จุดเข้าที่ปลอดภัยกว่า', 1315);

      // Beat 6 (61.95 - 67.68s): Takeaway Summary Card
      cards(560, 62.00, 67.58, 'สรุปกฎ<span class="y nb">รอดกับดักข่าว 20:30 น.</span>', [
        { b: "RULE 01 · WAIT 15M", n: "ห้ามกดในนาทีข่าวออก รอ 15 นาที", c: "ปล่อยให้สเปรดทองคำกลับมาแคบปกติก่อน", t: 62.18 },
        { b: "RULE 02 · M15 CLOSE", n: "รอปิดแท่ง 15 นาทีค่อยหาจุดเข้า", c: "เห็นชัดว่าฝั่งไหนโดนกวาด Stop Loss ไปแล้ว", t: 64.85 }
      ], 2);
"""


# ============================================================================
# EP.09 V6.1 (66.11s) — พอร์ตติดลบ -50% ต้องทำกำไรคืน +100%! กับดักคณิตศาสตร์ที่โบรกไม่เคยเตือน
# ============================================================================
SCHED_EP9_V6_1: List[Dict[str, object]] = [
    # Beat 1: Hook (0.00 - 8.55s)
    {"start": 0.00, "end": 2.20, "mode": "footage", "clip": "DRV_clip66", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "hook_punch", "sfx": "sub_shutter_hit"},
    {"start": 2.20, "end": 4.50, "mode": "chart",   "clip": "DRV_MT5_history_balance_minus363", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 4.50, "end": 7.10, "mode": "footage", "clip": "BRAIN_CHAR_ots-drawdown-50-to-100-math", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 7.10, "end": 8.55, "mode": "text_bg", "clip": "DRV_clip75", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.46), "trans": "exposure_flash", "sfx": "sub_drop_flash"},

    # Beat 2: Mirror Failed Habit (8.55 - 24.70s)
    {"start": 8.55, "end": 11.20, "mode": "chart",   "clip": "DRV_MT5_swap_loss_history", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 11.20, "end": 15.05, "mode": "footage", "clip": "PAIN_CHAR_front-phone-backcasing", "mstart": 0.20, "scale": 1.05, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 15.05, "end": 17.60, "mode": "chart",   "clip": "DRV_MT5_red_drawdown_orders", "mstart": 0.05, "scale": 1.00, "focus": (0.50, 0.50), "trans": "prism_shatter", "sfx": "prism_shatter_sfx"},
    {"start": 17.60, "end": 19.90, "mode": "chart",   "clip": "DRV_MT5_candle_crash_m1", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "neg_shockwave", "sfx": "neg_shockwave_zap"},
    {"start": 19.90, "end": 22.30, "mode": "footage", "clip": "OCT_domino_chain_falls_black_red", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.50), "trans": "whip_tilt_v", "sfx": "whip_tilt_riser"},
    {"start": 22.30, "end": 24.70, "mode": "chart",   "clip": "DRV_MT5_xauusd_m15_sl_chart", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},

    # Beat 3: Hidden Math & Brain Mechanism (24.70 - 42.65s)
    {"start": 24.70, "end": 27.80, "mode": "text_bg", "clip": "DRV_clip79", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "exposure_flash", "sfx": "sub_drop_flash"},
    {"start": 27.80, "end": 31.05, "mode": "text_bg", "clip": "DRV_clip16", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 31.05, "end": 34.60, "mode": "text_bg", "clip": "DRV_clip13", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 34.60, "end": 38.30, "mode": "text_bg", "clip": "DRV_clip78", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.46), "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz"},
    {"start": 38.30, "end": 42.65, "mode": "footage", "clip": "OCT_house_of_cards_collapses", "mstart": 0.20, "scale": 1.10, "focus": (0.50, 0.50), "trans": "neg_shockwave", "sfx": "neg_shockwave_zap"},

    # Beat 4: Mechanism Pivot (42.65 - 55.85s)
    {"start": 42.65, "end": 46.30, "mode": "footage", "clip": "DRV_clip84", "mstart": 0.20, "scale": 1.06, "focus": (0.50, 0.48), "trans": "gravity_flip", "sfx": "gravity_flip_swoop"},
    {"start": 46.30, "end": 48.70, "mode": "chart",   "clip": "DRV_MT5_xauusd_set_sl_close_profit", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
    {"start": 48.70, "end": 52.05, "mode": "footage", "clip": "FIX_CHAR_ots-close-laptop-5pct-limit", "mstart": 0.20, "scale": 1.04, "focus": (0.50, 0.48), "trans": "scale_punch", "sfx": "shutter_pop"},
    {"start": 52.05, "end": 55.85, "mode": "chart",   "clip": "DRV_MT5_close_all_positions_popup", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "exposure_flash", "sfx": "sub_drop_flash"},

    # Beat 5: Friction Removal (55.85 - 60.70s)
    {"start": 55.85, "end": 58.20, "mode": "chart",   "clip": "DRV_MT5_xauusd_m5_sl_lines", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "whip_tilt_v", "sfx": "whip_tilt_riser"},
    {"start": 58.20, "end": 60.70, "mode": "chart",   "clip": "DRV_MT5_gold_m1_green_candles", "mstart": 0.10, "scale": 1.00, "focus": (0.50, 0.50), "trans": "scale_punch", "sfx": "shutter_pop"},

    # Beat 6: Takeaway Summary Card (60.70 - 66.11s)
    {"start": 60.70, "end": 63.50, "mode": "text_bg", "clip": "DRV_clip05", "mstart": 0.20, "scale": 1.08, "focus": (0.50, 0.50), "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz"},
    {"start": 63.50, "end": 66.11, "mode": "text_bg", "clip": "DRV_clip77", "mstart": 0.15, "scale": 1.06, "focus": (0.50, 0.48), "trans": "whip_pan_h", "sfx": "whip_whoosh"},
]

JS_EP9_V6_1 = """
      // Beat 1 (0.00 - 8.55s): Counter-Intuitive Hook
      caption(0.14, 4.45, 'ถ้าปล่อยพอร์ต<span class="n nb">ติดลบ -50%</span> ไม่ได้ต้องทำคืน 50% นะเว้ย', 1315);
      caption(4.52, 7.05, 'แต่มึงต้องทำกำไรถึง <span class="y nb">+100% เต็ม</span>', 1315);
      kinetic(680, 7.12, 8.50, [
        { c: "bl-md", h: 'ต้องบวกคืน <span class="y nb">+100% เต็ม</span>', d: 0.32, g: 0.32 },
        { c: "bl-lg", h: 'ถึงจะ<span class="n nb">กลับไปเท่าทุนเดิม!</span>', d: 0.35, g: 0.35 }
      ], 420);

      // Beat 2 (8.55 - 24.70s): Mirror Failed Habit (Chart & Footage Focus)
      caption(8.60, 15.00, 'พอร์ต $1,000 ลากติดลบเหลือ $500 <span class="n nb">นึกว่าเอาคืนครึ่งทางก็เท่าทุน</span>', 1315);
      caption(15.08, 19.85, 'เลยปล่อยไม้ติดลบลากลึก จาก <span class="y nb">-10%</span> เป็น <span class="n nb">-30% จนถึง -50%</span>', 1315);
      caption(19.92, 24.65, 'ไม่ใช่เทรดไม่เก่ง แต่สมองคิดเปอร์เซ็นต์ขาลงกับขาขึ้น <span class="n nb">เป็นเส้นตรงเหมือนกัน</span>', 1315);

      // Beat 3 (24.70 - 42.65s): Hidden Math & Brain Mechanism
      cards(600, 24.75, 31.00, 'ความจริงของ<span class="n nb">คณิตศาสตร์พอร์ตเทรด</span>', [
        { b: "CAPITAL BASE", n: "ขาดทุนคิดจากฐานเงินต้นที่เล็กลง", c: "ยิ่งปล่อยลากลึก แรงกู้พอร์ตยิ่งทวีคูณ", t: 25.00 }
      ], 1);
      check(620, 31.08, 38.25, 'ตาราง<span class="n nb">นรก Drawdown</span> <span class="nb">ที่โบรกไม่บอก</span>', [
        { k: "-10%", x: 'พอร์ตลบ 10% → ทำคืนแค่ <span class="y nb">+11% ก็หลุดดอย</span>', t: 31.20 },
        { k: "-50%", x: 'พอร์ตลบ 50% → ต้องทำคืน <span class="n nb">+100% เต็ม!</span>', t: 34.70 }
      ]);
      caption(38.32, 42.60, 'และถ้าปล่อยติดลบถึง <span class="n nb">-80%</span> ต้องทำกำไรคืนถึง <span class="y nb">+400%</span>!', 1315);

      // Beat 4 (42.65 - 55.85s): Mechanism Pivot (5% Daily Drawdown Cap)
      caption(42.70, 48.65, 'กฎเหล็กมืออาชีพ: <span class="y nb">ซอยความเสี่ยงไม้ละ 1-2%</span> และตั้ง Stop Loss ทุกไม้', 1315);
      caption(48.72, 55.80, 'ถ้าวันไหนพอร์ตยุบครบ <span class="n nb">5%</span> ต้อง<span class="y nb">ปิดจอหยุดเทรดทันที</span>ในวันนั้น', 1315);

      // Beat 5 (55.85 - 60.70s): Friction Removal
      caption(55.90, 60.65, 'คัดลอสตั้งแต่ <span class="y nb">-2%</span> ใช้แรงกู้พอร์ตน้อยกว่า <span class="n nb">-50%</span> ถึง 50 เท่า!', 1315);

      // Beat 6 (60.70 - 66.11s): Takeaway Summary Card
      cards(560, 60.75, 66.02, 'สรุปกฎ<span class="y nb">ป้องกันหลุมคณิตศาสตร์</span>', [
        { b: "RULE 01 · RISK 1-2%", n: "ซอยความเสี่ยงไม้ละ 1-2% เท่านั้น", c: "ตัดขาดทุนตั้งแต่แผลยังเล็ก กู้คืนง่ายที่สุด", t: 60.95 },
        { b: "RULE 02 · 5% DAILY CAP", n: "พอร์ตยุบครบ 5% ปิดจอพักทันที", c: "รักษาฐานเงินต้น ไม่ให้ตกลงไปในหลุม +400%", t: 63.55 }
      ], 2);
"""


def render_episode(ep_num: int, dur: float, sched: List[Dict[str, object]], js_body: str, out_mp4_name: str, sheet_name: str) -> None:
    clips = [str(s["clip"]) for s in sched]
    assert len(clips) == len(set(clips)), f"Duplicate clip in EP{ep_num} V6.1: {clips}"
    for c in clips:
        p = BROLL_DIR / f"{c}.mp4"
        if not p.exists():
            raise FileNotFoundError(f"Missing clip for EP{ep_num} V6.1: {p}")
    n_charts = sum(1 for s in sched if s.get("mode") == "chart")
    print(f"[VERIFIED] EP{ep_num} V6.1: all {len(clips)} clips exist & unique ({n_charts} real MT5 chart cuts)!", flush=True)

    plate_mp4 = WORK_DIR / "clips" / f"v6_1_plate_EP{ep_num}.mp4"
    v61.render_v6_1_plate_track(plate_mp4, sched, dur)

    mixed_wav = WORK_DIR / "audio" / f"EP{ep_num}_v6_{int(round(dur))}s_14lufs.wav"
    assert mixed_wav.exists(), f"Missing mixed audio: {mixed_wav}"

    workdir = WORK_DIR / f"cut_ep{ep_num}_v6_1_{int(round(dur))}s_pure"
    v61.build_workdir_ep7_v6_1(workdir, dur, plate_mp4, mixed_wav, js_body)

    out_dir = WORK_DIR / "finals_v5_mass_sfx"
    out_mp4 = out_dir / out_mp4_name
    print(f"[HyperFrames] Rendering {out_mp4.name}...", flush=True)
    subprocess.run(
        ["npx", "--yes", "hyperframes", "render", "--output", str(out_mp4), "--fps", "30", "--quality", "standard"],
        cwd=str(workdir),
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    sheet_path = BRAIN_DIR / sheet_name
    tiles = []
    for idx, seg in enumerate(sched):
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
    print(f"[DONE] EP{ep_num} V6.1: {out_mp4.name} ({out_mp4.stat().st_size:,} bytes) + {sheet_path.name}", flush=True)


def main() -> int:
    render_episode(
        8,
        67.68,
        SCHED_EP8_V6_1,
        JS_EP8_V6_1,
        "BL-EP8-V6.1-68s-PureKnowledge-MT5Chart-SingleFocus.mp4",
        "sheet_EP8_v6_1_68s_mt5chart.jpg",
    )
    render_episode(
        9,
        66.11,
        SCHED_EP9_V6_1,
        JS_EP9_V6_1,
        "BL-EP9-V6.1-66s-PureKnowledge-MT5Chart-SingleFocus.mp4",
        "sheet_EP9_v6_1_66s_mt5chart.jpg",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
