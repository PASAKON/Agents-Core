# -*- coding: utf-8 -*-
"""timeline.py for mypasakon-ref-2 (Tesla/Trump-Musk stock-crash news clip).
20s, 1080x1920, 30fps. Content: Tesla stock drops 15% in a day after a
Trump-Musk public spat; clip is cut off mid-sentence at 20.0s (source
truncation -- Musk's rebuttal quote never finishes). Handled as an
intentional cliffhanger/"to be continued" close, not a fabricated payoff."""

import os

W, H, FPS, DUR = 1080, 1920, 30, 20.0

_BROLL = os.path.expanduser("~/.claude/skills/reel-editor-th/assets/mooniex-broll")
_WORK = os.path.dirname(os.path.abspath(__file__))

# ---- CAPTIONS -----------------------------------------------------------
# 0.0-4.6 suppressed by the hook (hardcoded in render_captions.py). No
# entries needed there. 16.2-17.8 is a kinetic beat (suppresses captions).
CAPTIONS = [
    (4.6, 5.7, "มูลค่าหายไป", []),
    (5.7, 6.8, "กว่าล้านล้านบาท", ["ล้านล้านบาท"]),
    (6.8, 7.7, "ในชั่วข้ามคืน", []),

    (7.7, 9.2, "เมื่อวันที่ 5 มิถุนา 2025", ["5", "มิถุนา", "2025"]),
    (9.2, 11.2, "เวลา 3 ทุ่ม 30 นาที", ["3", "ทุ่ม", "30"]),

    (11.2, 12.4, "Trump พูดว่า", ["Trump"]),
    (12.4, 14.0, "ผิดหวังใน Elon Musk มาก", ["ผิดหวัง", "Elon Musk"]),

    (14.0, 15.3, "แต่แน่นอน Elon Musk", ["Elon Musk"]),
    (15.3, 16.2, "ก็ออกมาโต้ตอบ", ["โต้ตอบ"]),

    # 16.2-17.8 kinetic beat owns the screen (suppressed automatically)

    (17.8, 19.0, "Elon Musk บอกว่า", ["Elon Musk"]),
    (19.0, 20.0, "ถ้าไม่ใช่ผมเนี่ย...", ["ถ้าไม่ใช่ผมเนี่ย..."]),
]

# ---- HOOK (0-4.2s, matches segment 1 exactly; captions stay suppressed
# until the hardcoded 4.6s regardless) -------------------------------------
HOOK_TAG = "ข่าวหุ้นด่วน"
HOOK_TEXT = (0.0, 4.2, "Tesla ร่วง 15%\nในคืนเดียว")

# ---- PUNCH -- the real last line of the clip (cut off mid-thought), used
# honestly as the cliffhanger beat rather than inventing a resolution ------
PUNCH_TEXT = (17.9, 20.0, "\"ถ้าไม่ใช่ผมเนี่ย...\"")

REVEAL_T = None  # SFX_EVENTS below is an explicit override; this is unused

# ---- CUTAWAYS -- avatar / footage / animation cut rhythm -----------------
CUTAWAYS = [
    (4.2, 7.7, "video", (f"{_WORK}/broll_candlestorm", 30)),
    (11.2, 14.0, "photo", f"{_BROLL}/trader-laptop-cash-risk.jpg"),
    (14.0, 16.2, "photo", f"{_BROLL}/trader-silhouette-red-tradingfloor.jpg"),
    (16.2, 17.8, "kinetic", (["4 ทุ่ม 45", "ตอบโต้ทันที"], {0})),
]

INSERTS = []  # no demo cards for this news-style clip

# ---- CTA (compressed for a 20s clip; scaled from the 53s reference) ------
CTA = {
    "save_sticker": (4.5, 7.0),
    "follow":       (17.0, 20.0),
    "comment":      (18.2, 20.0),
    "save_big":     (19.0, 20.0),
}

# ---- SFX (sparse -- 4 distinct moments, not a whoosh-on-every-cut) -------
SFX_EVENTS = [
    (4.2, "whoosh-short", 0.30),   # hard cut into the candle b-roll
    (11.2, "chime", 0.32),         # reveal: Trump's quote / the conflict begins
    (16.2, "pop", 0.30),           # kinetic time-stat pops in
    (17.0, "pop", 0.28),           # follow chip appears
]

GREEN = (11, 222, 133)
INK = (12, 14, 18)

# This speaker's framing is tight (beanie brim near top edge, eyes sit low
# in frame) -- the default clean-style y=1215 caption bar lands right on
# top of the eyes in every avatar beat. Move it up onto the forehead/brim
# band instead (checked visually, see qc/).
CAPTION_Y = 1000
