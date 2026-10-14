"""EP1 Thai dub, ACT 4 to 6: Teller narration (Daniel, one call per ACT, word timestamps) + three voice-only character lines.
fal elevenlabs/tts/eleven-v4. Text = SCRIPT-TH-FULL.md ACT 4 to 6 section 'ข้อความที่เสียงจะอ่าน' (CEO 2026-10-10: 'ทำ ARCT 4-6 ต่อได้เลย ... ไว้ใจคุณ').
Nothing is bought without `--approved <usd>`: the amount the CEO said OK to, which must cover the estimate of the parts asked for.
Key read inside this process from Core/.env, never printed.
Usage: python -I make_voice_act456.py <outdir> --part act4|act5|act6|chars|all [--dry | --approved 0.30]
"""
import json, re, sys, time, urllib.request, urllib.error, pathlib, hashlib

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
PART = sys.argv[sys.argv.index("--part") + 1]
DRY = "--dry" in sys.argv
APPROVED = float(sys.argv[sys.argv.index("--approved") + 1]) if "--approved" in sys.argv else 0.0
PRICE = 0.08  # per 1000 characters

ACT4 = [
    ("4.01", "ที่ขอบประตูแห่งแสงวัน เหลืออีกเพียงครึ่งก้าว."),
    ("4.02", "ถ้าเดินขึ้นไปในความเงียบ โดยไม่รู้ว่าคนที่รักยังตามมาอยู่หรือไม่ จะทนได้นานเท่าใด?"),
    ("4.03", "เวอร์จิลเขียนว่า ความบ้าอย่างหนึ่งจู่ ๆ ก็ครอบงำเขา. เป็นความผิดที่น่าให้อภัย ถ้ายมโลกรู้จักให้อภัย."),
    ("4.04", "เขาหยุด. เขาหันกลับ. เขามองยูริไดซี ผู้เป็นของเขาอีกครั้ง."),
    ("4.05", "ทันทีที่เขามอง ข้อตกลงก็ขาด. เสียงฟ้าร้องดังขึ้นสามครั้ง จากหนองน้ำแห่งนรก."),
    ("4.06", "โอวิดบอกว่า เธอไม่ได้ตำหนิเขา. แต่ในฉบับของเวอร์จิล เธอพูดว่า"),
    ("4.07", "เธอหายไปเหมือนควันที่จางหายในอากาศว่าง."),
    ("4.08", "เขาคว้าได้แต่เงา. เขาอยากพูดอีกมาก แต่เธอไม่เห็นเขาอีกแล้ว."),
    ("4.09", "เขากลับไปที่ฝั่งแม่น้ำ. แต่คนพายเรือแห่งยมโลก ไม่ยอมให้เขาข้ามเป็นครั้งที่สอง."),
    ("4.10", "เธอเย็นเฉียบเป็นศพ ล่องไปบนเรือข้ามสติกซ์แล้ว."),
    ("4.11", "เล่ากันว่า เจ็ดเดือนเต็ม เขาร้องไห้ใต้หน้าผาสูง ริมแม่น้ำสไตรมอน."),
    ("4.12", "เขาเล่าเรื่องของตนในถ้ำเย็น เสียงนั้นทำให้เสือใจอ่อน และพาต้นโอ๊กเดินตามมา."),
    ("4.13", "เขาเหมือนนกไนติงเกลใต้ร่มต้นป็อปลาร์ ที่ร้องครวญทั้งคืน เพราะลูกถูกคนใจร้ายฉกไปจากรัง."),
]
ACT5 = [
    ("5.01", "หลังจากนั้นเขาไม่รับความรักใหม่อีก."),
    ("5.02", "เวอร์จิลเล่าว่า เขาเดินเตร็ดเตร่คนเดียว ผ่านหิมะและน้ำแข็งทางเหนือ."),
    ("5.03", "โอวิดเล่าว่า สามปีเต็มเขาหลีกเลี่ยงผู้หญิงทุกคน."),
    ("5.04", "วันหนึ่ง หญิงชาวเทรซกลุ่มหนึ่ง นุ่งห่มหนังสัตว์ เห็นเขาจากยอดเนิน กำลังดีดพิณ."),
    ("5.05", "หนึ่งในพวกนางตะโกนขึ้น"),
    ("5.06", "นางขว้างหอกใส่เขา. ปลายหอกพันใบไม้ไว้ จึงเพียงกระแทกเขา ไม่เป็นแผล."),
    ("5.07", "ก้อนหินที่ขว้างมา พ่ายต่อเสียงเพลง ตกลงแทบเท้าเขา ราวกับขออภัย."),
    ("5.08", "แต่ความบ้าของพวกนางยิ่งแรงขึ้น. ปี่ กลอง ฉาบ และเสียงกรีดร้อง กลบเสียงพิณและเสียงร้องของเขาจนหมด."),
    ("5.09", "เมื่อหินไม่ได้ยินเพลงอีก มันก็ตกลงมา เปื้อนเลือดของกวีแห่งเทรซ."),
    ("5.10", "โอวิดเขียนว่า นั่นคือครั้งแรกและครั้งเดียว ที่เสียงของเขาไม่สามารถโน้มน้าวใคร."),
    ("5.11", "เวอร์จิลเขียนว่า พวกนางฉีกร่างเขาออกเป็นชิ้น และโปรยไปทั่วท้องทุ่ง."),
    ("5.12", "แม่น้ำเฮบรัสรับศีรษะและพิณของเขาไป."),
    ("5.13", "พิณลอยตามกระแสน้ำ ยังครวญเพลงเศร้า. ลิ้นที่ไร้ชีวิตยังเปล่งเสียง."),
    ("5.15", "ริมฝั่งสองข้างขานรับชื่อนั้น."),
    ("5.16", "กระแสพาไปถึงเมืองเมทิมนา บนเกาะเลสบอส. งูตัวหนึ่งพุ่งเข้าใส่. อะพอลโลทำให้ขากรรไกรของมันแข็งเป็นหิน."),
    ("5.17", "บัคคัสไม่ยอมให้ผู้ฆ่าลอยนวล. เขาผูกเท้าของหญิงเหล่านั้นด้วยราก. รากชอนลงดิน ขากับแขนของนางกลายเป็นไม้. พวกนางกลายเป็นต้นโอ๊ก."),
]
ACT6 = [
    ("6.01", "แต่โอวิดไม่ได้จบเรื่องที่ความตายของเขา."),
    ("6.02", "เงาของออร์เฟียสลงไปใต้ดิน ผ่านแดนที่เขาเคยเห็น. เขาตามหายูริไดซีในทุ่งของผู้มีสุข และพบเธอ."),
    ("6.03", "เขากอดเธอ. ทั้งสองเดินเคียงกัน. บางครั้งเขาเดินนำ และหันกลับมามองเธอได้ อย่างปลอดภัย."),
    ("6.04", "นั่นคือฉบับที่อ่อนโยนที่สุด."),
    ("6.05", "แต่ก่อนโอวิดหลายร้อยปี เพลโตเล่าไว้ต่างออกไป."),
    ("6.06", "ในฉบับของเพลโต เหล่าเทพส่งเขากลับมามือเปล่า. พวกเขาให้เห็นเพียงภาพลวงของเธอ."),
    ("6.07", "เหตุผลคือ เขาไม่มีใจกล้า. เขาไม่กล้าตายเพื่อความรัก เหมือนอัลเคสติส ที่ยอมตายแทนสามี."),
    ("6.08", "เขาเลือกหาทางลงไปยมโลกทั้งที่ยังมีชีวิต."),
    ("6.09", "เพลโตเขียนว่า เหล่าเทพจึงให้เขาตายด้วยมือของผู้หญิง."),
    ("6.10", "สามฉบับ. สามผู้ชาย."),
    ("6.11", "เวอร์จิลให้เขาเสียเธอไปเพราะความรัก. โอวิดให้เขาได้เธอคืน. เพลโตให้เขาไม่ได้อะไรเลย."),
    ("6.12", "เขาหันกลับเพราะขี้ขลาด หรือเพราะรัก?"),
    ("6.13", "นี่คือ The Old Telling. สิ่งที่ฉบับที่ทุกคนรู้ ตัดทิ้งไป."),
    ("6.14", "ติดตามช่องไว้ เพื่อฟังเรื่องต่อไป."),
]
# voice-only character lines, one call each; the first voice that works is kept (Eurydice kept Alice in ACT 1)
CHARS = [
    ("act4_406_eurydice", "ออร์เฟียส ความบ้าของท่านทำลายข้า และทำลายท่านด้วย. ลาก่อน. ราตรีอันมหึมาพาข้าไปแล้ว.", ["Alice", "Matilda", "Lily"], {"stability": 0.35, "similarity_boost": 0.75}),
    ("act5_505_thrace_woman", "ดูสิ! นั่นคือกวีที่ดูถูกความรักของพวกเรา!", ["Matilda", "Lily", "Alice"], {"stability": 0.3, "similarity_boost": 0.75}),
    ("act5_514_head_liam", "ยูริไดซี.", ["Liam"], {"stability": 0.35, "similarity_boost": 0.75}),
]
JOBS_ALL = [(f"act{n}_teller_daniel", " ".join(t for _, t in L), ["Daniel"], {"stability": 0.5, "similarity_boost": 0.75, "timestamps": True})
            for n, L in ((4, ACT4), (5, ACT5), (6, ACT6))] + CHARS
SEL = {"act4": [0], "act5": [1], "act6": [2], "chars": [3, 4, 5], "all": [0, 1, 2, 3, 4, 5]}[PART]
JOBS = [JOBS_ALL[i] for i in SEL]

chars = {n: len(t) for n, t, _, _ in JOBS}
est = round(PRICE * sum(chars.values()) / 1000, 4)
print("part", PART, "chars", chars, "est USD", est, "approved", APPROVED)
(OUT / "sentences-act456.json").write_text(json.dumps({"act4": ACT4, "act5": ACT5, "act6": ACT6, "chars": [(n, t) for n, t, _, _ in CHARS]}, ensure_ascii=False, indent=1), encoding="utf-8")
if DRY:
    sys.exit(0)
if est > APPROVED:
    sys.exit(f"STOP: estimate {est} USD is over the approved {APPROVED} USD (pass --approved only with the CEO's OK for this amount)")

k = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open("/Users/gob/MoonieXHQ/Agents/Core/.env", encoding="utf-8").read(), re.M).group(1)
ledger_path = OUT / "ledger-act456.json"
ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []
for name, text, voices, extra in JOBS:
    for voice in voices:
        body = json.dumps({"text": text, "voice": voice, "language_code": "th", **extra}).encode()
        req = urllib.request.Request("https://fal.run/elevenlabs/tts/eleven-v4", data=body, method="POST",
                                     headers={"Authorization": "Key " + k, "Content-Type": "application/json", "User-Agent": "MoonieX-research/1.0"})
        row = {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "task": "cmo-f76492bf", "runner": "make_voice_act456.py", "endpoint": "elevenlabs/tts/eleven-v4",
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
ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
print("billed est USD", round(sum(r["est_usd"] for r in ledger if r["status"] == "ok"), 4))
