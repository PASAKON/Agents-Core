#!/usr/bin/env python3
"""Ask Gemini about a video clip. The only tool in the org that actually
watches motion and hears audio -- video-see.sh samples frames, whisper reads
words, this sees the clip.

    python3 scripts/video-ask.py <clip.mp4> "question"
    python3 scripts/video-ask.py <clip.mp4> -f checks/s15a.txt

Sends the CLIP plus a short checklist. Deliberately NOT the screenplay: the
generated clips are public on Higgsfield, the script is not, and the key is a
free-tier key whose inputs Google may train on and have humans review
(CEO decision 2026-08-29). Keep questions specific and self-contained.
"""
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
# Free tier, video-capable. Overridable when a better one lands.
MODEL = os.environ.get("GEMINI_VIDEO_MODEL", "gemini-flash-latest")
INLINE_LIMIT = 18 * 1024 * 1024  # request cap is 20MB; leave headroom for base64


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("GEMINI_API_KEY not set (env or .env)")


def post(path: str, payload: dict, key: str) -> dict:
    req = urllib.request.Request(
        f"{API}/{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}\n{e.read().decode()[:600]}")


def upload(clip: pathlib.Path, key: str) -> str:
    """Files API, for clips too big to inline. Returns a file URI."""
    size = clip.stat().st_size
    # Media upload lives under /upload/, not the plain API root -- the plain
    # root answers 200 with JSON and no X-Goog-Upload-URL, which reads as a
    # success right up until the header is None.
    start = urllib.request.Request(
        "https://generativelanguage.googleapis.com/upload/v1beta/files",
        data=json.dumps({"file": {"display_name": clip.name}}).encode(),
        headers={
            "x-goog-api-key": key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(start, timeout=120) as r:
        session = r.headers["X-Goog-Upload-URL"]
    put = urllib.request.Request(
        session,
        data=clip.read_bytes(),
        headers={
            "Content-Length": str(size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
    )
    with urllib.request.urlopen(put, timeout=600) as r:
        info = json.load(r)["file"]
    # ACTIVE means Google finished decoding it; asking while PROCESSING answers empty.
    for _ in range(60):
        if info.get("state") == "ACTIVE":
            return info["uri"]
        time.sleep(2)
        q = urllib.request.Request(
            f"{API}/{info['name']}", headers={"x-goog-api-key": key}
        )
        with urllib.request.urlopen(q, timeout=60) as r:
            info = json.load(r)
    sys.exit(f"file stuck in state {info.get('state')}")


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    clip = pathlib.Path(args[0])
    if not clip.exists():
        sys.exit(f"no such clip: {clip}")
    question = (
        pathlib.Path(args[2]).read_text(encoding="utf-8")
        if args[1] == "-f"
        else " ".join(args[1:])
    )

    key = load_key()
    size = clip.stat().st_size
    if size <= INLINE_LIMIT:
        part = {
            "inline_data": {
                "mime_type": "video/mp4",
                "data": base64.b64encode(clip.read_bytes()).decode(),
            }
        }
    else:
        part = {"file_data": {"mime_type": "video/mp4", "file_uri": upload(clip, key)}}

    out = post(
        f"models/{MODEL}:generateContent",
        {
            "contents": [{"parts": [part, {"text": question}]}],
            "generationConfig": {"temperature": 0},
        },
        key,
    )
    try:
        text = out["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        sys.exit(json.dumps(out)[:800])
    usage = out.get("usageMetadata", {})
    print(text.strip())
    print(
        f"\n-- {MODEL} · {size/1e6:.1f}MB · "
        f"in {usage.get('promptTokenCount','?')} / out {usage.get('candidatesTokenCount','?')} tokens"
    )


if __name__ == "__main__":
    main()
