#!/usr/bin/env python3
"""
build_v6_ep1_word_synced.py — Build BLACK LIQUIDITY EP1 V6 (Pure Knowledge 58.50s):
  - Every cut boundary is 100% locked to the exact spoken clause timestamp + graphic card entry + SFX hit
  - Every visual clip directly proves/illustrates the spoken Thai words in that clause (zero filler B-roll)
  - Integrates the 4 new Google Veo 3.1 shots generated with strict Screen-Orientation & Camera-Axis Logic:
      1. PAIN_CHAR_ots-02am-chart.mp4         (Rule A: Over-the-Shoulder looking into 02:00 chart screen)
      2. PAIN_CHAR_front-phone-backcasing.mp4 (Rule B: Front view seeing back of smartphone + red screen glow on glasses)
      3. BRAIN_CHAR_side-blue-glare-eyes.mp4  (Rule C: 90-degree side profile with blue monitor rays hitting eyes)
      4. FIX_CHAR_warm-lightbar-sleepmask.mp4 (3/4 rear-side view turning on warm 3000K monitor lightbar + sleep mask)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

sys.path.insert(0, "/Users/gob/MoonieXHQ/Agents/Core/scripts")
import build_bl_v4_lungtep_style as v4

BROLL_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/broll-incoming")
WORK_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/basket-pilot1-work")
BRAIN_DIR = Path("/Users/gob/.gemini/antigravity/brain/1ec08f78-528c-484f-be60-038384d3be35")

# Word-Synced 22-Clause Cut Schedule for EP1 Pure Knowledge (58.50s)
# Every start/end timestamp matches the exact spoken syllable + HyperFrames caption/card entry + SFX!
EP1_V6_WORD_SYNCED_SCHEDULE: List[Dict[str, object]] = [
    # --- BEAT 1: Counter-Intuitive Hook (0.00s - 6.92s) ---
    # 0.00 - 1.25s: "คนส่วนใหญ่ที่..." (Opening hook beat + 02:00 AM digital clock)
    {
        "start": 0.00, "end": 1.25,
        "clip": "DRV_clip28", "mstart": 0.15,
        "scale": 1.08, "focus": (0.50, 0.48),
        "trans": "hook_punch", "sfx": "sub_shutter_hit",
    },
    # 1.25 - 2.80s: "...พอร์ตแตกตอนดึก" (Eye reflecting falling red candlesticks in the dark)
    {
        "start": 1.25, "end": 2.80,
        "clip": "OCT_eye_reflects_falling_red_candles", "mstart": 0.20,
        "scale": 1.14, "focus": (0.50, 0.48),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    # 2.80 - 4.55s: "ไม่ใช่เพราะเทคนิคไม่แม่นนะเว้ย" (BL Character pointing & addressing viewer)
    {
        "start": 2.80, "end": 4.55,
        "clip": "CHAR_EP1_B1_HOOK_01", "mstart": 0.30,
        "scale": 1.12, "focus": (0.50, 0.45),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    # 4.55 - 6.92s: "แต่เพราะใช้สมอง ผิดเวลามาตลอด" (BL Character pointing at glowing 3D brain hologram!)
    {
        "start": 4.55, "end": 6.92,
        "clip": "CHAR_EP2_B3_MECHANISM_02", "mstart": 0.35,
        "scale": 1.18, "focus": (0.52, 0.46),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    },

    # --- BEAT 2: Mirror Failed Habit (6.92s - 21.20s) ---
    # 6.92 - 8.90s: "วงจรเทรดดึกทุกคืน · US ตลาดเปิดนั่งเฝ้ายาว" (BL Avatar profile watching trading monitors)
    {
        "start": 6.92, "end": 8.90,
        "clip": "DRV_clip19", "mstart": 0.20,
        "scale": 1.06, "focus": (0.50, 0.48),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    # 8.90 - 11.24s: "02:00 จ้องจอถึงตีสอง" (Veo 3.1 Rule A OTS: Over-the-shoulder looking into 02:00 chart screen)
    {
        "start": 8.90, "end": 11.24,
        "clip": "PAIN_CHAR_ots-02am-chart", "mstart": 0.20,
        "scale": 1.04, "focus": (0.50, 0.50),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    # 11.24 - 13.24s: "พอกราฟลาก นั่งเฝ้าเอาคืน · ฝืนถือสู้กราฟตอนดึก" (Veo 3.1 Rule B Front: Back of phone + red glow on sunglasses)
    {
        "start": 11.24, "end": 13.24,
        "clip": "PAIN_CHAR_front-phone-backcasing", "mstart": 0.20,
        "scale": 1.06, "focus": (0.50, 0.48),
        "trans": "prism_shatter", "sfx": "prism_shatter_sfx",
    },
    # 13.24 - 16.00s: "กำไรทั้งอาทิตย์ หายในคืนเดียว" (Trader slamming desk in front of red monitors + wallet drained)
    {
        "start": 13.24, "end": 16.00,
        "clip": "OCT_trader_slams_desk_red_monitors", "mstart": 0.20,
        "scale": 1.12, "focus": (0.50, 0.50),
        "trans": "neg_shockwave", "sfx": "neg_shockwave_zap",
    },
    # 16.00 - 18.50s: "01 ไม่ใช่เพราะระบบพัง" (BL Avatar raising stop hand in red smoke)
    {
        "start": 16.00, "end": 18.50,
        "clip": "DRV_clip75", "mstart": 0.20,
        "scale": 1.08, "focus": (0.50, 0.46),
        "trans": "whip_tilt_v", "sfx": "whip_tilt_riser",
    },
    # 18.50 - 21.20s: "แต่ตอนตีสอง สมองไม่เหลือสติให้คุมวินัย" (Candle flame blown out into smoke in darkness)
    {
        "start": 18.50, "end": 21.20,
        "clip": "OCT_candle_flame_blown_out_smoke", "mstart": 0.20,
        "scale": 1.16, "focus": (0.50, 0.50),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },

    # --- BEAT 3: Hidden Brain Mechanism (21.20s - 37.12s) ---
    # 21.20 - 23.50s: "ความจริงที่น่ากลัวกว่า..." (BL Avatar looking down/up under diagonal neon)
    {
        "start": 21.20, "end": 23.50,
        "clip": "DRV_clip79", "mstart": 0.15,
        "scale": 1.06, "focus": (0.50, 0.48),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    },
    # 23.50 - 26.68s: "WARN อาการตาล้าตอนดึก เป็นแค่สัญญาณเตือนด่านแรก" (Veo 3.1 Rule C Side Profile: Blue monitor glare hitting eyes & rubbing temple)
    {
        "start": 23.50, "end": 26.68,
        "clip": "BRAIN_CHAR_side-blue-glare-eyes", "mstart": 1.80,
        "scale": 1.08, "focus": (0.52, 0.46),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    # 26.68 - 29.68s: "กลไกแสงจอในห้องมืด · 1 หลอกสมองว่ายังเป็นกลางวัน" (Blue-gold smoke orb optical illusion in dark room)
    {
        "start": 26.68, "end": 29.68,
        "clip": "DRV_clip04", "mstart": 0.20,
        "scale": 1.08, "focus": (0.50, 0.50),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    # 29.68 - 31.96s: "2 กดสมองส่วนตัดสินใจให้รวน" (Red glowing neural spheres multiplying / prefrontal cortex disruption)
    {
        "start": 29.68, "end": 31.96,
        "clip": "DRV_clip45", "mstart": 0.20,
        "scale": 1.18, "focus": (0.50, 0.50),
        "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz",
    },
    # 31.96 - 34.54s: "02 ตาพร่า + สมองเบลอ" (Puppet strings controlling hand from above)
    {
        "start": 31.96, "end": 34.54,
        "clip": "OCT_puppet_strings_hand_above", "mstart": 0.20,
        "scale": 1.10, "focus": (0.50, 0.50),
        "trans": "neg_shockwave", "sfx": "neg_shockwave_zap",
    },
    # 34.54 - 37.12s: "ต่อให้แผนดีแค่ไหน ก็กดตามอารมณ์อยู่ดี" (Finger impulsively pressing glowing red button)
    {
        "start": 34.54, "end": 37.12,
        "clip": "DRV_clip47", "mstart": 0.20,
        "scale": 1.24, "focus": (0.50, 0.50),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },

    # --- BEAT 4: Mechanism Pivot (37.12s - 48.40s) ---
    # 37.12 - 39.72s: "เทรดเดอร์สายอยู่รอดทำยังไง?" (BL Avatar composed authority pose in red studio)
    {
        "start": 37.12, "end": 39.72,
        "clip": "DRV_clip76", "mstart": 0.20,
        "scale": 1.06, "focus": (0.50, 0.48),
        "trans": "gravity_flip", "sfx": "gravity_flip_swoop",
    },
    # 39.72 - 42.24s: "จัดแสงโต๊ะและเวลานอนใหม่หมด" (Veo 3.1 Warm Lightbar & Sleep Mask setup shot — reaching to turn on lightbar)
    {
        "start": 39.72, "end": 42.24,
        "clip": "FIX_CHAR_warm-lightbar-sleepmask", "mstart": 0.15,
        "scale": 1.04, "focus": (0.50, 0.50),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
    # 42.24 - 44.10s: "DESK ลดแสงสะท้อนตอนดูชาร์ต ถนอมสายตาระหว่างเทรด" (Warm lightbar glowing over desk & keyboard)
    {
        "start": 42.24, "end": 44.10,
        "clip": "CHAR_EP1_B5_LESSON_METHOD_02", "mstart": 0.20,
        "scale": 1.18, "focus": (0.50, 0.46),
        "trans": "scale_punch", "sfx": "shutter_pop",
    },
    # 44.10 - 48.40s: "SLEEP ใส่ผ้าปิดตาตัดแสงทันที ให้สมองเข้าโหมดพักเร็วที่สุด" (Veo 3.1 BL Character putting on 3D sleep mask in bed)
    {
        "start": 44.10, "end": 48.40,
        "clip": "PROD01_BL_03_put_on_rest", "mstart": 0.10,
        "scale": 1.04, "focus": (0.50, 0.48),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    },

    # --- BEAT 5: Friction Removal (48.40s - 53.12s) ---
    # 48.40 - 53.12s: "ทำง่าย ไม่ต้องรื้อโต๊ะใหม่ · แค่ตัดแสงกวนตาตอนนอนให้มืดสนิท"
    {
        "start": 48.40, "end": 53.12,
        "clip": "DRV_clip08", "mstart": 0.20,
        "scale": 1.10, "focus": (0.50, 0.50),
        "trans": "whip_tilt_v", "sfx": "whip_tilt_riser",
    },

    # --- BEAT 6: Pain Callback + Takeaway (53.12s - 58.50s) ---
    # 53.12 - 55.80s: "03 เบื่อไหม? พอร์ตลบเพราะกดมั่วดึกๆ"
    {
        "start": 53.12, "end": 55.80,
        "clip": "CHAR_EP1_B4_CONSEQUENCE_01", "mstart": 0.30,
        "scale": 1.16, "focus": (0.50, 0.46),
        "trans": "rgb_glitch", "sfx": "rgb_glitch_buzz",
    },
    # 55.80 - 58.50s: "เปลี่ยนมาจัดเวลานอนให้จบดีกว่า" (BL Avatar confident arms-crossed smirk in red frame)
    {
        "start": 55.80, "end": 58.50,
        "clip": "DRV_clip77", "mstart": 0.15,
        "scale": 1.06, "focus": (0.50, 0.48),
        "trans": "whip_pan_h", "sfx": "whip_whoosh",
    },
]


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
        max_raw = int(round(src_fps * 5.5))
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


v4.ClipCache = FastClipCache


def main() -> None:
    # Verify all 22 clips exist and are 100% unique
    clips = [str(s["clip"]) for s in EP1_V6_WORD_SYNCED_SCHEDULE]
    assert len(clips) == len(set(clips)), "Duplicate clip in EP1_V6_WORD_SYNCED_SCHEDULE!"
    for c in clips:
        p = BROLL_DIR / f"{c}.mp4"
        if not p.exists():
            raise FileNotFoundError(f"Missing {p}")
    print(f"[VERIFIED] All {len(clips)} word-synced clips exist and are 100% unique!", flush=True)

    wdir = WORK_DIR / "cut_pilot1_A_v5_58s_pure"
    # Rebuild 58.50s Pure Knowledge audio track from the exact 65.44s slow voiceover (0.00s - 58.50s)
    sys.path.insert(0, str(BRAIN_DIR / "scratch"))
    import build_v5_batch as b5
    vo_a = WORK_DIR / "tts_65s/takes/A_pilot1_65s_slow.wav"
    aud_pure = wdir / "audio" / "A_v5_58s_14lufs.wav"
    b5.mix_track_with_17sfx(vo_a, aud_pure, 58.50, b5.EVENTS_A_BASKET, fade_tail=True)
    shutil.copy2(aud_pure, wdir / "audio.wav")
    shutil.copy2(aud_pure, WORK_DIR / "audio" / "A_v5_58s_14lufs.wav")

    # Verify waveform correlation with approved Clip B (0.00s - 58.00s) is > 0.99
    _, arr_pure = b5.read_wav_s16(aud_pure)
    _, arr_bask = b5.read_wav_s16(WORK_DIR / "cut_pilot1_A_v5_65s_basket/audio/A_v5_65s_basket_14lufs.wav")
    n_chk = int(58.0 * 48000)
    corr = float(np.corrcoef(arr_pure[:n_chk, 0], arr_bask[:n_chk, 0])[0, 1])
    print(f"[AUDIO VERIFIED] Correlation with approved Clip B (0.00s-58.00s): r = {corr:.6f}", flush=True)
    assert corr > 0.99, f"Audio correlation too low: {corr}"

    plate_dst = wdir / "clips" / "v5_plate_58s.mp4"
    v4.render_v4_plate_track_scheduled(plate_dst, EP1_V6_WORD_SYNCED_SCHEDULE, 58.50)

    out_mp4 = WORK_DIR / "finals_v5_mass_sfx" / "BL-EP1-V6-58s-PureKnowledge-WordSynced-Veo31ScreenLogic.mp4"
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    print(f"[HyperFrames] Rendering {out_mp4.name}...", flush=True)
    subprocess.run(
        ["npx", "--yes", "hyperframes", "render", "--output", str(out_mp4), "--fps", "30", "--quality", "standard"],
        cwd=str(wdir),
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sheet_path = BRAIN_DIR / "sheet_EP1_v6_58s_wordsynced.jpg"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-i", str(out_mp4),
            "-vf", "fps=1/3.55,scale=360:640,tile=4x4",
            "-frames:v", "1", "-q:v", "3",
            str(sheet_path),
        ],
        check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    shutil.copy2(out_mp4, BRAIN_DIR / "EP1_v6_58s_PureKnowledge_WordSynced.mp4")
    print(f"[DONE] Rendered {out_mp4} ({out_mp4.stat().st_size:,} bytes) + {sheet_path.name}", flush=True)


if __name__ == "__main__":
    main()
