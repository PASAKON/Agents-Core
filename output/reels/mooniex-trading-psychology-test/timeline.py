# -*- coding: utf-8 -*-
"""timeline.py for mooniex-trading-psychology-test (source: 5s4YPgZzVy6GUbae6TW2E_output.mp4)

Transcribed with mlx-whisper (th, word_timestamps=True, condition_on_previous_text=False).
Segment boundaries below are the ASR's, with a few obvious ASR typos corrected by ear/context
(ขัดทุน -> ขาดทุน, กรับ -> กลับ, ไซซ์ -> ไซส์). Style = clean (brand default for trading content).

KNOWN GAP (flagged per mooniex-video-editor SKILL.md "source-truncation" note): the speaker
promises "สามกับดักหลัก" (3 main traps) at 24.48s but the clip only actually names/explains two
(Revenge Trade, Overconfidence) before the recording stops mid-sentence at 40.0s -- the 3rd trap
is never named and Overconfidence's own explanation is itself cut off ("รู้สึกว่าตัวเองอ่านกราฟแม่น"
has no closing clause). Nothing below invents a 3rd trap, a completed Overconfidence payoff, or a
spoken CTA/close -- see report.md for the full judgment-call writeup.
"""

import os

W, H, FPS, DUR = 1080, 1920, 30, 40.0

_INS = os.path.expanduser("~/.claude/skills/reel-editor-th/assets/mooniex-broll")

# ---- CAPTIONS: (start, end, "phrase", [emphasis words]) ---------------------
# Chunked 2-4 words, timed within each ASR segment's reliable start/end span.
CAPTIONS = [
    # S1 0.00-7.32  "รู้ไม่ว่า 90% ของนักเทรดที่ขาดทุน ไม่ได้ขาดทุนเพราะระบบแย่ แต่เพราะอารมณ์ชนะระบบ"
    (0.00, 1.80, "รู้ไม่ว่า 90%", ["90%"]),
    (1.80, 3.60, "ของนักเทรดที่ขาดทุน", ["ขาดทุน"]),
    (3.60, 5.46, "ไม่ได้ขาดทุนเพราะระบบแย่", []),
    (5.46, 7.32, "แต่เพราะอารมณ์ชนะระบบ", ["อารมณ์"]),
    # S2 7.74-13.18  "ผมเจอนักเทรดมาเยอะมาก บางคน ระบบดีมาก แบคเทสต์ผ่านมาหลายปี"
    (7.74, 9.55, "ผมเจอนักเทรดมาเยอะมาก", []),
    (9.55, 11.36, "บางคน ระบบดีมาก", ["ดีมาก"]),
    (11.36, 13.18, "แบคเทสต์ผ่านมาหลายปี", ["แบคเทสต์"]),
    # S3 13.42-18.90  "แต่พอเทรดจริง กดเข้าผิดไซส์ ถือนานเกินกำหนด ตัด SL ไม่ได้"
    (13.42, 14.79, "แต่พอเทรดจริง", []),
    (14.79, 16.16, "กดเข้าผิดไซส์", ["ผิดไซส์"]),
    (16.16, 16.80, "ถือนานเกินกำหนด", []),
    (16.80, 18.90, "ตัด SL ไม่ได้", ["SL"]),  # suppressed on-screen (kinetic beat below owns this line)
    # S4 18.90-24.06  "สุดท้าย พอร์ตก็ยังหายอยู่ดี ปัญหาอยู่ที่สภาวะทางอารมณ์ตอนเทรด"
    (18.90, 20.62, "สุดท้าย พอร์ตยังหาย", []),
    (20.62, 22.34, "อยู่ดี ปัญหาอยู่ที่", []),
    (22.34, 24.06, "สภาวะทางอารมณ์", ["อารมณ์"]),
    # S5 24.48-26.78  "มีสามกับดักหลักที่ทุกคนเจอ"
    (24.48, 26.78, "มีสามกับดักหลัก", ["สาม", "กับดัก"]),  # suppressed (kinetic beat below owns this line)
    # S6 27.22-30.14  "Revenge Trade แพ้แล้วรีบเข้าใหม่ทันที"
    (27.22, 28.68, "Revenge Trade", ["Revenge", "Trade"]),
    (28.68, 30.14, "แพ้แล้วรีบเข้าใหม่", []),
    # S7 30.36-32.78  "เพื่อเอาเงินคืน แทนที่จะหยุดคิด"
    (30.36, 31.57, "เพื่อเอาเงินคืน", []),
    (31.57, 32.78, "แทนที่จะหยุดคิด", []),
    # S8 32.98-34.60  "กลับยิ่งขาดทุนหนักขึ้น"
    (32.98, 34.60, "กลับยิ่งขาดทุนหนักขึ้น", ["ขาดทุนหนักขึ้น"]),  # suppressed (kinetic beat below owns this line)
    # S9 35.62-38.14  "Overconfidence ชนะมาหลายไม้ติดกัน"
    (35.62, 36.88, "Overconfidence", ["Overconfidence"]),
    (36.88, 38.14, "ชนะมาหลายไม้ติดกัน", []),
    # S10 38.14-40.00  "รู้สึกว่าตัวเองอ่านกราฟแม่น" (clip cuts off here, no closing clause spoken)
    (38.14, 40.00, "รู้สึกว่าอ่านกราฟแม่น", ["แม่น"]),
]

# ---- HOOK (0-4.6s cold open) --------------------------------------------------
# Overrides the pipeline's leftover default kicker tag (was "ทริค AI ที่ออฟฟิศไม่บอก",
# a different demo clip's copy -- found by reading render_captions.py, not documented
# in either skill doc as something to check/override per clip).
HOOK_TAG = "จิตวิทยาการเทรด"
HOOK_TEXT = (0.0, 4.6, "90% นักเทรดขาดทุน\nเพราะอารมณ์ ไม่ใช่ระบบ")

# ---- PUNCH (payoff line, yellow) ----------------------------------------------
# Recaps the thesis actually stated at 5.46-7.32s ("แต่เพราะอารมณ์ชนะระบบ") rather than
# inventing a closing line for the 3rd trap / consequence the clip never reaches.
# NOTE (QC catch): draw_punch (render_captions.py) has NO auto-fit like draw_hook does --
# fixed font(92,"bold"), no width check. Neither skill doc flags this; a first-draft
# longer line here rendered cut off at both screen edges. Keep PUNCH_TEXT under ~900px
# at that font (check with render_lib.font(92,"bold").getlength(text) before finalizing).
PUNCH_TEXT = (36.5, 40.0, "อารมณ์คือกับดักจริง")

REVEAL_T = 5.46  # "แต่เพราะอารมณ์ชนะระบบ" -- the thesis reveal

# render_cards.py reads T.INSERTS unconditionally (crashes with AttributeError if
# missing) even though cutaway-authoring.md doesn't mention this legacy variable
# still being required for a CUTAWAYS-only timeline with no demo cards -- doc gap,
# flagged in report.md. No cards fit this clip's content, so this stays empty.
INSERTS = []

# ---- CUTAWAYS: full-frame hard cuts (avatar is the default; only list the rest) -
CUTAWAYS = [
    (4.60, 7.32, "video", (f"{_INS}/frames-candlestorm-2.72s", 30)),
    (10.30, 13.18, "video", (f"{_INS}/frames-candleglow-2.88s", 30)),
    (16.80, 18.90, "kinetic", (["ตัด SL", "ไม่ได้"], {0})),
    (18.90, 21.30, "photo", f"{_INS}/trader-laptop-cash-risk.jpg"),
    # NOTE: the reference "card" cutaway (draw_traps_card) hardcodes a completed
    # "3 กับดักจิตวิทยา" checklist with rows ["Revenge Trade", "Overconfidence", "ตัด SL ไม่ได้"].
    # Using it here would visually confirm all 3 traps as delivered, but the clip only ever
    # explains 2 of them (see module docstring) -- "ตัด SL ไม่ได้" was a separate earlier
    # symptom (S3), never re-confirmed as the named 3rd trap. Per the "don't invent
    # structure/counts the source doesn't support" brand rule, swapped this beat for a
    # kinetic beat that shows only the literal spoken line (no claimed count of confirmed items).
    (24.48, 26.78, "kinetic", (["มีสามกับดักหลัก", "ที่ทุกคนเจอ"], set())),
    (30.36, 32.78, "photo", f"{_INS}/trader-silhouette-red-tradingfloor.jpg"),
    (32.98, 34.60, "kinetic", (["กลับยิ่ง", "ขาดทุนหนักขึ้น"], {1})),
    (36.50, 38.14, "photo", f"{_INS}/trader-victory-confetti.jpg"),
]

# ---- COUNTERS: top-right tag, only for traps actually named+explained --------
# No "1/3"/"2/3" count used (can't verify a completed count) -- plain labels only,
# per the brand rule + the exact scenario the skill doc's truncation note warns about.
COUNTERS = [
    (27.22, 34.60, "กับดัก: Revenge Trade"),
    (35.62, 40.00, "กับดัก: Overconfidence"),
]

# ---- CTA windows (rescaled from the 53s reference to this 40s clip's tail) ----
CTA = {
    "save_sticker": (3.0, 6.0),
    "follow":       (34.5, 40.0),
    "comment":      (36.5, 40.0),   # bio-offer slot
    "save_big":     (37.5, 40.0),
}

# ---- SFX: sparse, tied to 4 distinct discrete moments (not a per-cut whoosh) --
SFX_EVENTS = [
    (5.46, "chime", 0.30),   # thesis reveal line lands
    (16.80, "pop", 0.28),    # "ตัด SL ไม่ได้" kinetic beat pops in
    (27.22, "pop", 0.28),    # "Revenge Trade" counter tag pops in
    (35.62, "pop", 0.28),    # "Overconfidence" counter tag pops in
]

GREEN = (11, 222, 133)
INK = (12, 14, 18)
