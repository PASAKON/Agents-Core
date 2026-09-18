#!/usr/bin/env python3
"""Rewrite a BLACK LIQUIDITY script into something a Thai TTS can actually read.

THE RULE THAT MATTERS MOST, learned the hard way on 2026-09-18:

    In Thai, a space IS a pause instruction. Thai is written with no spaces
    between words; the Royal Society reserves the small space (wak lek) for
    separating phrases and the large space (wak yai) for ending a sentence,
    and Thai TTS engines derive their pause positions from exactly those
    spaces and punctuation. So spacing a phrase out word by word - "ฟอเร็กซ์
    ทรี ดี" - orders the model to stop twice in the middle of a single name.
    A version written that way ran 47.8s where the same sentences written
    Thai-style ran 38.2s, and the CEO could hear every one of those stops.

    Therefore: write each phrase CLOSED UP, and spend a space only where a
    human reader would actually draw breath - between clauses, between items
    in a list, at the end of a sentence.

The other two fixes, in order:
  1. Latin words become Thai transliterations. A Thai TTS switches phonology
     mid-sentence for a Latin token and the seam is audible every time. But
     keep short letter+digit tokens (V2, 3D) OUT of this - transliterating
     those made them worse, not better ("วีทู" came back as "วิทูล").
  2. Digits become Thai words, written closed up: "เก้าพันแปดร้อยยี่สิบห้า",
     never spaced into pieces. "9825" is otherwise free to be read digit by
     digit, and often is.
"""
import re

TRANSLIT = {
    # brands / platforms
    "TikTok": "ติ๊กต๊อก", "Facebook": "เฟซบุ๊ก", "LINE OA": "ไลน์ โอเอ", "LINE": "ไลน์",
    "Telegram": "เทเลแกรม", "WikiFX": "วิกิ เอฟเอ็กซ์", "Forex 3D": "ฟอเร็กซ์ ทรีดี",
    "Forex 4D": "ฟอเร็กซ์ โฟร์ดี", "Forex 5D": "ฟอเร็กซ์ ไฟฟ์ดี",
    "Trade AI Pro": "เทรด เอไอ โปร", "Quantum Forex Bot": "ควอนตัม ฟอเร็กซ์ บอท",
    "St. Vincent": "เซนต์ วินเซนต์", "XM": "เอ็กซ์เอ็ม", "Exness": "เอ็กซ์เนส",
    # finance / tech vocabulary
    "Ponzi": "พอนซี", "Quant Bot": "ควอนท์ บอท", "drawdown": "ดรอว์ดาวน์",
    "deepfake": "ดีปเฟก", "free signal": "ฟรี ซิกนัล", "signal": "ซิกนัล",
    "score": "สกอร์", "Lot": "ล็อต", "case": "เคส", "funnel": "ฟันเนล",
    "return rate": "รีเทิร์น เรต", "AI": "เอไอ", "KOL": "เค โอ แอล",
    "IB": "ไอ บี", "FCA": "เอฟ ซี เอ", "ASIC": "เอ ซิก", "ก.ล.ต.": "กอ ลอ ตอ",
    "DJ": "ดีเจ",   # NB: V2 / V3 / 3D deliberately NOT here - see the docstring
}
ONES = "ศูนย์ หนึ่ง สอง สาม สี่ ห้า หก เจ็ด แปด เก้า".split()
UNITS = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"]

def thai_number(n: int) -> str:
    if n == 0: return "ศูนย์"
    if n >= 10_000_000:                      # keep very large numbers readable
        return thai_number(n // 1_000_000) + "ล้าน" + (thai_number(n % 1_000_000) if n % 1_000_000 else "")
    s, out = str(n), ""
    for i, ch in enumerate(s):
        d, place = int(ch), len(s) - i - 1
        if d == 0: continue
        if place == 1 and d == 1: out += "สิบ"
        elif place == 1 and d == 2: out += "ยี่สิบ"
        elif place == 0 and d == 1 and len(s) > 1: out += "เอ็ด"
        else: out += ONES[d] + UNITS[place]
    return out

def prep(text: str, pauses: bool = False, pause_s: float = 0.35) -> str:
    for latin, thai in sorted(TRANSLIT.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(re.escape(latin), thai, text, flags=re.IGNORECASE if latin.isupper() is False else 0)
    # years read as a whole number, then every remaining run of digits
    # letter+digit tokens (V2, V3, 3D) are names, not quantities - protect them
    # before the number pass or "V2" becomes "Vสอง"
    keep = []
    def _stash(m):
        keep.append(m.group())
        return chr(0xE000 + len(keep) - 1)   # private-use char: carries no digits
    text = re.sub(r"\b[A-Za-z]+\d+[A-Za-z]*\b|\b\d+[A-Za-z]+\b", _stash, text)
    # numbers go in CLOSED UP - a space here is a pause inside the number
    text = re.sub(r"\d+", lambda m: thai_number(int(m.group())), text)
    text = re.sub(r"[\uE000-\uE0FF]", lambda m: keep[ord(m.group()) - 0xE000], text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [l.strip() for l in text.split("\n")]
    if pauses:
        lines = [l + f" <#{pause_s}#>" if l else l for l in lines]
    return "\n".join(lines).strip()

if __name__ == "__main__":
    import sys
    print(prep(open(sys.argv[1], encoding="utf-8").read(), pauses="--pauses" in sys.argv))
