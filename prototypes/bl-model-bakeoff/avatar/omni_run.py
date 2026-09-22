#!/usr/bin/env python3
"""Generate the BL avatar lipsync reference on OmniHuman v1.5.

Two things this script exists to get right, both learned by getting them wrong
on 2026-09-18:

  1. SUBMIT TO THE QUEUE, NEVER `fal.run`. This render takes ~14.5 minutes. The
     synchronous endpoint holds the socket open for the whole thing and when it
     drops you have paid in full and the output URL is gone from the response.
     (Recoverable - `GET rest.fal.ai/requests?start_time=&end_time=` keeps
     `json_output` with the video URL - but only if you know to look.)

  2. ALWAYS PASS A PROMPT. The endpoint has one and it governs motion. With no
     prompt the model invents its own performance: our first take put hands in
     frame from 7s and a hand across the face at 19.5s, which is exactly what a
     lipsync reference must not contain.
"""
import json, re, time, urllib.request, mimetypes, pathlib, shutil

KEY = re.search(r'^FAL_API_KEY=(.+)$', open("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env").read(), re.M).group(1).strip()
H = {"Authorization": "Key " + KEY, "Content-Type": "application/json"}
APP = "fal-ai/bytedance/omnihuman/v1.5"
# Poll the first TWO path segments of the app id, not the app id and not one
# segment less: fal-ai/kling-video/v3/pro/... -> fal-ai/kling-video, and
# fal-ai/bytedance/omnihuman/v1.5 -> fal-ai/bytedance. Anything else 405s, and
# a 405 looks exactly like a dead render. Simpler still: the submit response
# hands you status_url and response_url - use those and skip the guessing.
BASE = "/".join(APP.split("/")[:2])
OUT = pathlib.Path(__file__).parent

# "ไม่นิ่ง แต่ก็ไม่ดุ๊กดิ๊ก เหมือนคนพูดหน้ากล้องปกติ ขยับมือได้" - CEO, 2026-09-18.
# The negatives are the load-bearing half: a hand near the mouth ruins the
# reference, and sync-lipsync cannot repair a face that has turned away.
PROMPT = (
    "A locked-off static medium shot, camera does not move. The man speaks directly to "
    "camera with calm confident presenter energy, like a host delivering a piece to camera. "
    "Natural relaxed upper-body movement and occasional small hand gestures kept low, near "
    "chest level. He faces the lens throughout. His hands never rise to his face, he never "
    "touches his glasses or his hat, no large or rapid arm movements, no turning away from "
    "camera, no leaning in or out. Steady framing, consistent distance."
)

def post(url, body, t=120):
    r = urllib.request.Request(url, method="POST", data=json.dumps(body).encode(), headers=H)
    return json.loads(urllib.request.urlopen(r, timeout=t).read())

def get(url, t=60):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read())

def upload(p: pathlib.Path) -> str:
    ct = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    ini = post("https://rest.fal.ai/storage/upload/initiate", {"content_type": ct, "file_name": p.name})
    urllib.request.urlopen(urllib.request.Request(ini["upload_url"], method="PUT",
        data=p.read_bytes(), headers={"Content-Type": ct}), timeout=600)
    return ini["file_url"]

def main():
    img, aud = upload(OUT / "A-topaz.png"), upload(OUT / "achird_20s.mp3")
    print("  uploaded image + audio", flush=True)
    sub = post(f"https://queue.fal.run/{APP}",
               {"image_url": img, "audio_url": aud, "prompt": PROMPT,
                "resolution": "1080p", "turbo_mode": False})
    rid = sub["request_id"]
    status_url = sub.get("status_url") or f"https://queue.fal.run/{BASE}/requests/{rid}/status"
    result_url = sub.get("response_url") or f"https://queue.fal.run/{BASE}/requests/{rid}"
    print(f"  submitted {rid}", flush=True)
    (OUT / "_last_request.json").write_text(json.dumps({"request_id": rid, "prompt": PROMPT}, indent=2))
    t0 = time.time()
    while time.time() - t0 < 2700:
        st = get(status_url)["status"]
        if st == "COMPLETED":
            d = get(result_url)
            url = (d.get("video") or {}).get("url") or d.get("video_url")
            f = OUT / "BL-avatar-reference-v2-1080x1920-20s.mp4"
            urllib.request.urlretrieve(url, f)
            shutil.copy2(f, pathlib.Path.home() / "Desktop" / f.name)
            print(f"  DONE {f.name} after {time.time()-t0:.0f}s", flush=True); return
        if st == "FAILED":
            print(f"  FAILED {rid}", flush=True); return
        time.sleep(20)
    print(f"  TIMEOUT - recover with request_id {rid}", flush=True)

if __name__ == "__main__":
    main()
