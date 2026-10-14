"""EP1 ACT 1 Thai dub: the spoken line for the black time card T1 ('Seven months later').
CEO 2026-10-10: picture text that carries story meaning must also be spoken. One call, Teller voice (Daniel),
fal elevenlabs/tts/eleven-v4, appended to ledger.json. Key read inside this process from Core/.env, never printed.
Usage: python -I make_voice_t1.py <outdir> [--dry]
"""
import json, re, sys, time, urllib.request, urllib.error, pathlib, hashlib

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
LEDGER = pathlib.Path(__file__).with_name("ledger.json")
PRICE = 0.08  # USD per 1000 characters
NAME, VOICE, TEXT = "act1_t1_teller_daniel", "Daniel", "เจ็ดเดือนต่อมา."
est = round(PRICE * len(TEXT) / 1000, 5)
print("chars", len(TEXT), "est USD", est)
assert est <= 0.01, "over the cap set for this line"
if "--dry" in sys.argv:
    sys.exit(0)

k = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open("/Users/gob/MoonieXHQ/Agents/Core/.env", encoding="utf-8").read(), re.M).group(1)
body = json.dumps({"text": TEXT, "voice": VOICE, "language_code": "th", "stability": 0.5, "similarity_boost": 0.75, "timestamps": True}).encode()
req = urllib.request.Request("https://fal.run/elevenlabs/tts/eleven-v4", data=body, method="POST",
                             headers={"Authorization": "Key " + k, "Content-Type": "application/json", "User-Agent": "MoonieX-research/1.0"})
row = {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "task": "cmo-f76492bf", "runner": "make_voice_t1.py", "endpoint": "elevenlabs/tts/eleven-v4",
       "name": NAME, "voice": VOICE, "chars": len(TEXT), "input_sha256": hashlib.sha256(TEXT.encode()).hexdigest()[:16], "est_usd": est,
       "review": "pending CEO ear"}
try:
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.load(r)
    audio = urllib.request.urlopen((data.get("audio") or {})["url"], timeout=120).read()
    (OUT / f"{NAME}.mp3").write_bytes(audio)
    if "timestamps" in data:
        (OUT / f"{NAME}.timestamps.json").write_text(json.dumps(data["timestamps"], ensure_ascii=False), encoding="utf-8")
    row.update(status="ok", bytes=len(audio), sha256=hashlib.sha256(audio).hexdigest()[:16])
except urllib.error.HTTPError as e:
    row.update(status=f"http {e.code}", error=e.read().decode("utf-8", "replace")[:200], est_usd=0.0)
except Exception as e:
    row.update(status="error", error=str(e)[:200], est_usd=0.0)
rows = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
rows.append(row)
LEDGER.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(NAME, row["status"], row.get("bytes", ""), row.get("error", ""))
