#!/usr/bin/env python3
"""Fetch results for jobs already submitted (and already paid for).

fal's queue splits the two paths: you SUBMIT to the full endpoint
(fal-ai/kling-video/v3/pro/text-to-video) but you POLL the base app
(fal-ai/kling-video). Polling the full path returns 405 and looks like
a dead job when the render is fine.
"""
import re, json, time, urllib.request, pathlib, shutil
k = re.search(r'^FAL_API_KEY=(.+)$', open("/Users/gob/Projects/mooniex-claudeflow/.env").read(), re.M).group(1).strip()
H = {"Authorization": "Key " + k}
BASE = {"fal-ai/kling-video/v3/pro/text-to-video": "fal-ai/kling-video",
        "alibaba/wan-3.0/text-to-video": "alibaba/wan-3.0",
        "fal-ai/sync-lipsync": "fal-ai/sync-lipsync"}
def g(u, t=60): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=t).read())
rows = json.load(open("out/submitted.json"))
live, done, t0 = list(rows), [], time.time()
while live and time.time() - t0 < 2400:
    for r in list(live):
        n, w, m, rid, e = r
        b = BASE[m]
        try: st = g(f"https://queue.fal.run/{b}/requests/{rid}/status")["status"]
        except Exception as ex: print(f"  {n:<16} status err {ex}", flush=True); continue
        if st == "COMPLETED":
            d = g(f"https://queue.fal.run/{b}/requests/{rid}")
            u = (d.get("video") or {}).get("url") or d.get("video_url") or d.get("url")
            urllib.request.urlretrieve(u, f"out/{n}.mp4")
            print(f"  DONE   {n:<16} ({time.time()-t0:.0f}s)", flush=True)
            done.append({"file": n, "what": w, "model": m, "request_id": rid, "est_usd": e}); live.remove(r)
        elif st == "FAILED":
            print(f"  FAILED {n:<16}", flush=True)
            done.append({"file": n, "what": w, "request_id": rid, "error": "FAILED"}); live.remove(r)
    json.dump(done, open("out/ledger.json", "w"), indent=2, ensure_ascii=False)
    if live: time.sleep(20)
if live: print("  still queued:", [r[0] for r in live], flush=True)
D = pathlib.Path.home() / "Desktop"
for f in pathlib.Path("out").glob("BL-*.mp4"): shutil.copy2(f, D / f.name)
print("  copied to Desktop", flush=True)
