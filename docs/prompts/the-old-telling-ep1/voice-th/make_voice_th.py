"""EP1 Thai dub, ACT 1 + ACT 2: Teller narration (one call per ACT, word timestamps) + character lines.
fal elevenlabs/tts/eleven-v4. CEO passed the text on 2026-10-10 ('ผ่านแล้ว ทำ TTS ออกมาได้เลย').
Cap: USD 0.13 for this batch (voice total cap 0.25 minus ~0.069 already spent). Key read inside this process
from Core/.env, never printed.   Usage: python -I make_voice_th.py <outdir> [--dry]
"""
import json, re, sys, time, urllib.request, urllib.error, pathlib, hashlib

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
DRY = "--dry" in sys.argv
PRICE = 0.08  # per 1000 characters
CAP = 0.13

ACT1 = [  # (id, text) narrator lines in order; the king, Orpheus and Eurydice lines are separate calls
    ("N1", "ในกรีซโบราณ มีนักดนตรีคนหนึ่งชื่อออร์เฟียส."),
    ("N2", "เมื่อเขาเล่นพิณ แม้สัตว์ป่าก็หยุดฟัง."),
    ("N3", "ในวันแต่งงาน งูกัดภรรยาของเขา เธอตาย."),
    ("N4", "นี่คือ The Old Telling ฉบับที่พวกเขาทำให้เบาลง."),
    ("N5", "ออร์เฟียสเดินลงสู่ยมโลกทั้งที่ยังมีชีวิต เขาเล่นพิณจนราชาแห่งความตายยอมอ่อน."),
    ("N6", "เขาไต่ขึ้นบันไดมืด เขาไม่ได้ยินเสียงฝีเท้าของเธอตามหลังมา."),
    ("N7", "ใกล้ถึงแสงสว่าง เขาทนความเงียบไม่ไหว เขาหันกลับไป."),
    ("N8", "เธอไม่ได้โทษเขา เธอหายไปแล้ว."),
    ("N9", "ออร์เฟียสนั่งร้องไห้อยู่ริมแม่น้ำ."),
    ("N10", "และนี่เป็นเพียงครึ่งแรก ตอนจบจริงของเขาเลวร้ายกว่านี้มาก."),
]
ACT2 = [
    ("2.01", "เรื่องนี้มาถึงเราผ่านกวีโรมันสองคน."),
    ("2.02", "เวอร์จิลเขียนไว้ราว 29 ปีก่อนคริสตกาล. โอวิดเขียนตามมาราว คริสต์ศักราช 8."),  # ค.ศ. spelled out so TTS does not read letters
    ("2.03", "ทั้งสองเล่าสามอย่าง ที่ฉบับที่ทุกคนรู้ไม่เล่า."),
    ("2.04", "เธอตายเพราะอะไร. ยมโลกทำอะไรเมื่อได้ยินเพลง. และเขาจบชีวิตอย่างไร."),
    ("2.05", "เริ่มที่วันแต่งงาน."),
    ("2.06", "เทพแห่งการแต่งงานมาร่วมพิธี แต่ไม่ได้นำคำอวยพรมาด้วย."),
    ("2.07", "คบไฟในมือเทพแตกปะทุ มีแต่ควันแสบตา. ไม่ว่าจะโบกเท่าไร ก็ไม่ติดไฟ."),
    ("2.08", "โอวิดเล่าว่า เจ้าสาวเดินกับนางไม้ในทุ่งหญ้า. งูฝังเขี้ยวที่ข้อเท้า. เธอตาย."),
    ("2.09", "เวอร์จิลเล่าต่างออกไป."),
    ("2.10", "เธอกำลังวิ่งหนีชายคนหนึ่งชื่ออริสเทอัส ไปตามริมแม่น้ำ."),
    ("2.11", "ในหญ้าสูงตรงหน้าเท้า มีงูน้ำตัวใหญ่ซ่อนอยู่. เธอไม่เห็น."),
    ("2.12", "เจ้าสาวตายในวันแต่งงาน ขณะวิ่งหนีผู้ชายอีกคน."),
    ("2.13", "ผึ้งทุกรังของอริสเทอัสตาย. ผู้พยากรณ์บอกว่า นั่นคือหนี้ที่ต้องจ่าย."),
    ("2.14", "ออร์เฟียสนั่งบนชายฝั่งเปล่า ร้องเพลงถึงเธอ."),
    ("2.16", "เพลงไม่ได้พาเธอกลับมา. เขาจึงไปหาเธอเอง."),
    ("2.17", "ที่ปลายใต้สุดของกรีซ มีแหลมเทนารอน. ถ้ำที่นั่น เล่ากันว่าเป็นประตูสู่ยมโลก."),
    ("2.18", "ออร์เฟียสเดินเข้าไป ถือพิณเพียงตัวเดียว."),
]
j = lambda items: " ".join(t for _, t in items)
# name, text, voice candidates (first that answers ok wins), settings
JOBS = [
    ("act1_teller_daniel", j(ACT1), ["Daniel"], {"stability": 0.5, "similarity_boost": 0.75, "timestamps": True}),
    ("act1_c1_king_brian", "พาเธอไปเถิด แต่ห้ามมองกลับมา.", ["Brian"], {"stability": 0.4, "similarity_boost": 0.75}),
    ("act1_c3_eurydice", "ลาก่อน.", ["Alice", "Matilda", "Lily"], {"stability": 0.35, "similarity_boost": 0.75}),
    ("act2_teller_daniel", j(ACT2), ["Daniel"], {"stability": 0.5, "similarity_boost": 0.75, "timestamps": True}),
    ("act2_215_orpheus_liam", "ที่รัก ยามรุ่งสางข้าร้องถึงเจ้า. ยามค่ำข้าก็ร้องถึงเจ้า.", ["Liam"], {"stability": 0.35, "similarity_boost": 0.75}),
]
# ACT 1 Orpheus 'ยูริไดซี!' is already made (voice1/out/orpheus_liam.mp3, 9 chars, same text): reused, not re-bought.
chars = {n: len(t) for n, t, _, _ in JOBS}
est = round(PRICE * sum(chars.values()) / 1000, 4)
print("chars", chars, "total", sum(chars.values()), "est USD", est, "cap", CAP)
assert est <= CAP, "over cap"
(OUT / "sentences.json").write_text(json.dumps({"act1": ACT1, "act2": ACT2}, ensure_ascii=False, indent=1), encoding="utf-8")
if DRY:
    sys.exit(0)

k = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open("/Users/gob/MoonieXHQ/Agents/Core/.env", encoding="utf-8").read(), re.M).group(1)
ledger = []
for name, text, voices, extra in JOBS:
    for voice in voices:
        body = json.dumps({"text": text, "voice": voice, "language_code": "th", **extra}).encode()
        req = urllib.request.Request("https://fal.run/elevenlabs/tts/eleven-v4", data=body, method="POST",
                                     headers={"Authorization": "Key " + k, "Content-Type": "application/json", "User-Agent": "MoonieX-research/1.0"})
        row = {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "task": "cmo-f76492bf", "runner": "make_voice_th.py", "endpoint": "elevenlabs/tts/eleven-v4",
               "name": name, "voice": voice, "chars": len(text), "input_sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
               "est_usd": round(PRICE * len(text) / 1000, 4), "review": "pending CEO ear"}
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.load(r)
            audio = urllib.request.urlopen((data.get("audio") or {})["url"], timeout=120).read()
            (OUT / f"{name}.mp3").write_bytes(audio)
            if "timestamps" in data:
                (OUT / f"{name}.timestamps.json").write_text(json.dumps(data["timestamps"], ensure_ascii=False), encoding="utf-8")
            row.update(status="ok", bytes=len(audio), sha256=hashlib.sha256(audio).hexdigest()[:16])
            ledger.append(row); print(name, voice, "ok", len(audio))
            break
        except urllib.error.HTTPError as e:
            row.update(status=f"http {e.code}", error=e.read().decode("utf-8", "replace")[:200], est_usd=0.0)
        except Exception as e:
            row.update(status="error", error=str(e)[:200], est_usd=0.0)
        ledger.append(row); print(name, voice, row["status"], row.get("error", ""))
(OUT / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
print("billed est USD", round(sum(r["est_usd"] for r in ledger if r["status"] == "ok"), 4))
