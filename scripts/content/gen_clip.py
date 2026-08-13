#!/usr/bin/env python3
"""Generate one MoonieX promo clip via fal.ai Seedance 2.0 (queue API).

Usage:
    FAL_API_KEY=... python gen_clip.py prompts/win-moment.txt \
        [--fast] [--res 720p] [--aspect 9:16] [--duration auto] [--out out/clip.mp4]

Reads the prompt from a text file, submits to the fal queue, polls until the
video is ready, then downloads the mp4. No third-party deps (stdlib urllib).
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
import urllib.error

FAL_HOST = "https://queue.fal.run"
MODEL_STD = "bytedance/seedance-2.0/text-to-video"
MODEL_FAST = "bytedance/seedance-2.0/fast/text-to-video"
MODEL_REF = "bytedance/seedance-2.0/reference-to-video"
MODEL_REF_FAST = "bytedance/seedance-2.0/fast/reference-to-video"


def _data_uri(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def _req(url: str, key: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Key {key}")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"fal HTTP {e.code}: {detail}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file")
    ap.add_argument("--fast", action="store_true", help="use fast (cheaper) tier")
    ap.add_argument("--ref", action="append", default=[],
                    help="reference image path (repeatable) -> reference-to-video")
    ap.add_argument("--res", default="720p")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--duration", default="auto")
    ap.add_argument("--out", default="out/clip.mp4")
    a = ap.parse_args()

    key = os.environ.get("FAL_API_KEY")
    if not key:
        sys.exit("FAL_API_KEY not set in env")

    with open(a.prompt_file, encoding="utf-8") as f:
        prompt = f.read().strip()

    if a.ref:
        model = MODEL_REF_FAST if a.fast else MODEL_REF
    else:
        model = MODEL_FAST if a.fast else MODEL_STD
    submit = f"{FAL_HOST}/{model}"
    body = {
        "prompt": prompt,
        "duration": a.duration,
        "resolution": a.res,
        "aspect_ratio": a.aspect,
    }
    if a.ref:
        body["image_urls"] = [_data_uri(p) for p in a.ref]
    print(f"[submit] {model} res={a.res} aspect={a.aspect} dur={a.duration}")
    job = _req(submit, key, "POST", body)
    status_url = job["status_url"]
    response_url = job["response_url"]
    print(f"[queued] request_id={job.get('request_id')}")

    for _ in range(180):  # ~15 min max
        st = _req(status_url, key)
        s = st.get("status")
        if s == "COMPLETED":
            break
        print(f"[poll] {s} ...")
        time.sleep(5)
    else:
        sys.exit("timeout waiting for fal job")

    result = _req(response_url, key)
    video_url = (result.get("video") or {}).get("url")
    if not video_url:
        sys.exit(f"no video url in result: {json.dumps(result)[:400]}")

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    print(f"[download] {video_url}")
    urllib.request.urlretrieve(video_url, a.out)
    print(f"[done] saved -> {a.out}")


if __name__ == "__main__":
    main()
