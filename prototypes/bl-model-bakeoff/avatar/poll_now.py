#!/usr/bin/env python3
"""Wait on the already-submitted OmniHuman render and save it."""
import re, json, time, urllib.request, pathlib, shutil
k=re.search(r'^FAL_API_KEY=(.+)$',open("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env").read(),re.M).group(1).strip()
H={"Authorization":"Key "+k,"Accept":"application/json"}
RID=json.load(open("_last_request.json"))["request_id"]
B="fal-ai/bytedance"
def g(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60).read())
t0=time.time()
while time.time()-t0<2700:
    st=g(f"https://queue.fal.run/{B}/requests/{RID}/status")["status"]
    if st=="COMPLETED":
        d=g(f"https://queue.fal.run/{B}/requests/{RID}")
        u=(d.get("video") or {}).get("url") or d.get("video_url")
        f=pathlib.Path("BL-avatar-reference-v2-1080x1920-20s.mp4")
        urllib.request.urlretrieve(u,f); shutil.copy2(f,pathlib.Path.home()/"Desktop"/f.name)
        print(f"  DONE after {time.time()-t0:.0f}s -> {f}",flush=True); break
    if st=="FAILED": print("  FAILED",flush=True); break
    time.sleep(20)
else: print(f"  TIMEOUT rid={RID}",flush=True)
