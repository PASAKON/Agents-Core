"""EP1 Thai dub, ACT 3: Orpheus line (Liam) and Teller narration (Daniel, one call, word timestamps).
fal elevenlabs/tts/eleven-v4. Text = SCRIPT-TH-FULL.md ACT 3 section 'ข้อความที่เสียงจะอ่าน' (CEO 2026-10-10: 'ทำ ARC3 ต่อเลยได้อณุมติงบ').
Two parts so the Orpheus line (needed first, H3 binds it as <Audio 1>) is bought alone; the Teller waits for the CEO's OK on the exact figure
(0.0735 USD, over the 0.25 voice cap by about 0.016).
Key read inside this process from Core/.env, never printed.
Usage: python -I make_voice_act3.py <outdir> --part orpheus|teller [--dry]
"""
import json, re, sys, time, urllib.request, urllib.error, pathlib, hashlib

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
PART = sys.argv[sys.argv.index("--part") + 1]
DRY = "--dry" in sys.argv
PRICE = 0.08  # per 1000 characters
CAP = {"orpheus": 0.01, "teller": 0.08}[PART]

ACT3 = [  # (id, text): narrator lines in order; 3.09 is Orpheus and is a separate call
    ("3.01", "ทางลงในถ้ำมืดสนิท จนถึงแม่น้ำสติกซ์ ที่วนล้อมยมโลกเก้ารอบ."),
    ("3.02", "ริมฝั่งมีผู้ตายยืนเป็นเงาซีด ทั้งแม่ เด็ก และหญิงสาวที่ยังไม่เคยแต่งงาน."),
    ("3.03", "ออร์เฟียสเดินผ่านพวกเขา ไปหยุดหน้าฮาเดส ราชาแห่งยมโลก และเพอร์เซโฟนี ราชินีของเขา."),
    ("3.04", "หัวใจของผู้ปกครองที่นั่น ไม่เคยอ่อนให้คำขอของมนุษย์."),
    ("3.05", "เขาดีดพิณ แล้วร้อง."),
    ("3.06", "เขาไม่ได้มาดูความน่ากลัวของที่นี่. เขามาเพราะภรรยาถูกงูกัดตาย."),
    ("3.07", "แล้วเขาพูดกับราชาแห่งความตายว่า ถ้าเรื่องเล่าเก่าเป็นจริง ท่านเคยลักพาภรรยามาจากโลกข้างบน ความรักผูกท่านไว้เหมือนผูกเขา."),
    ("3.08", "ทุกคนต้องลงมาที่นี่ในที่สุด. เธอจะเป็นของท่านอยู่แล้ว. เขาขอเพียงให้เธออยู่ต่ออีกช่วงหนึ่ง."),
    ("3.10", "ผู้ตายทั้งยมโลกร้องไห้."),
    ("3.11", "แทนทาลัสหยุดคว้าน้ำที่ไหลหนี. ล้อของอิกซิออนหยุดหมุน. ซิซิฟัสนั่งลงบนก้อนหินของเขา."),
    ("3.12", "เซอร์เบอรัส สุนัขสามหัว อ้าปากค้าง."),
    ("3.13", "เล่ากันว่า เทพีล้างแค้นผู้โหดเหี้ยม ร้องไห้เป็นครั้งแรก และครั้งเดียว."),
    ("3.14", "ยูริไดซีถูกเรียกมา. เธอเดินกะเผลก เพราะแผลที่ข้อเท้ายังอยู่."),
    ("3.15", "ฮาเดสยอม. เธอขึ้นไปกับเขาได้ ถ้าเขาไม่หันไปมองเธอ."),
    ("3.16", "ทั้งสองเริ่มเดินขึ้นบนทางชันมืด ไม่มีใครพูดสักคำ."),
]
ORPHEUS = ("act3_309_orpheus_liam", "ถ้าท่านไม่ให้ ข้าจะไม่ขึ้นไปอีก. ท่านจะได้ชนะ ด้วยความตายของสองคน.", ["Liam"], {"stability": 0.35, "similarity_boost": 0.75})
TELLER = ("act3_teller_daniel", " ".join(t for _, t in ACT3), ["Daniel"], {"stability": 0.5, "similarity_boost": 0.75, "timestamps": True})
JOBS = [ORPHEUS] if PART == "orpheus" else [TELLER]

chars = {n: len(t) for n, t, _, _ in JOBS}
est = round(PRICE * sum(chars.values()) / 1000, 4)
print("part", PART, "chars", chars, "est USD", est, "cap", CAP)
assert est <= CAP, "over cap"
(OUT / "sentences-act3.json").write_text(json.dumps({"act3": ACT3, "orpheus": ORPHEUS[1]}, ensure_ascii=False, indent=1), encoding="utf-8")
if DRY:
    sys.exit(0)

k = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open("/Users/gob/MoonieXHQ/Agents/Core/.env", encoding="utf-8").read(), re.M).group(1)
ledger_path = OUT / "ledger-act3.json"
ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []
for name, text, voices, extra in JOBS:
    for voice in voices:
        body = json.dumps({"text": text, "voice": voice, "language_code": "th", **extra}).encode()
        req = urllib.request.Request("https://fal.run/elevenlabs/tts/eleven-v4", data=body, method="POST",
                                     headers={"Authorization": "Key " + k, "Content-Type": "application/json", "User-Agent": "MoonieX-research/1.0"})
        row = {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "task": "cmo-f76492bf", "runner": "make_voice_act3.py", "endpoint": "elevenlabs/tts/eleven-v4",
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
