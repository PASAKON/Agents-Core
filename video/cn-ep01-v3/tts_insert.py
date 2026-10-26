"""EP01 v3 narrator inserts. ElevenLabs v4 on fal, same settings as voice/tts_chunks_lang.py (voice Brian, stability 0.5, seed 7).
Reads FAL_MEDIA_API_KEY_RW from env; never prints it. One call per (line, take); take N uses seed 6+N (take 1 = seed 7).
Usage: infisical run ... -- python tts_insert.py <lang th|en> <line-id> <take 1-3>   (text is read from lines/<lang>_<id>.txt)
Appends one JSON line per call to v3/ledger.jsonl (chars, request id, take). Refuses a 4th take of a line."""
import json, os, sys, time, urllib.request, urllib.error
V3 = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("FAL_MEDIA_API_KEY_RW") or sys.exit("key not set")
lang, lid, take = sys.argv[1], sys.argv[2], int(sys.argv[3])
assert lang in ("th", "en") and 1 <= take <= 3, "max 3 takes per line"
VOICE, MODEL = "Brian", "elevenlabs/tts/eleven-v4"
H = {"Authorization": f"Key {KEY}", "Content-Type": "application/json"}
led = [json.loads(l) for l in open(f"{V3}/ledger.jsonl")] if os.path.exists(f"{V3}/ledger.jsonl") else []
if sum(1 for r in led if r["lang"] == lang and r["line"] == lid) >= 3: sys.exit("3 takes already used for this line")
out = f"{V3}/takes/{lang}_{lid}_t{take}.mp3"
if os.path.exists(out): sys.exit("take exists")
text = open(f"{V3}/lines/{lang}_{lid}.txt").read().strip()
def req(url, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=H,
                               method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=120) as f: return json.loads(f.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read()[:300].decode(errors='replace').replace(KEY, '<redacted>')}")
sub = req(f"https://queue.fal.run/{MODEL}", {"text": text, "voice": VOICE, "stability": 0.5, "language_code": lang, "seed": 6 + take})
for _ in range(150):
    if req(sub["status_url"]).get("status") == "COMPLETED": break
    time.sleep(2)
os.makedirs(f"{V3}/takes", exist_ok=True)
urllib.request.urlretrieve(req(sub["response_url"])["audio"]["url"], out)
rec = {"lang": lang, "line": lid, "take": take, "seed": 6 + take, "chars": len(text), "request_id": sub.get("request_id"), "file": out}
open(f"{V3}/ledger.jsonl", "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
print("saved", os.path.basename(out), len(text), "chars", sub.get("request_id"), flush=True)
