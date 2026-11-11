"""Capped fal image generation/editing. Dry-run is the default; --fire is required to spend."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import http.client
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

WORK = Path("/opt/MoonieXHQ/Work")
LAYERIZE = "bytedance/seedream/v5/pro/layerize"
EDIT = "openai/gpt-image-2.5/flare/edit"
QUEUE = "https://queue.fal.run/"
UPLOAD_URL = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"
STORAGE = ("https://v3.fal.media/", "https://v3b.fal.media/", "https://fal.media/")
KEY_NAME, KEY_PROJECT, KEY_ENV, KEY_PATH = "FAL_MEDIA_API_KEY_RW", "Agents-Core", "prod", "/cmo-media"
KEY_RE = re.compile(r"^[!-~]{8,1024}$")
CAP_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
MAX_BYTES, MAX_ANSWER, POLL_N, POLL_S = 30 << 20, 1 << 20, 150, 2
MAX_5XX = 2
MAX_LAYERS = 17  # base image + up to 16 layers; the reserve is always the worst case
EXIT_FAIL, EXIT_BAD, EXIT_CAP, EXIT_KEY = 1, 2, 3, 4
EDIT_BASE = {("1920x1072", "low"): .00441, ("1920x1072", "medium"): .00951,
             ("1920x1072", "high"): .03945, ("1024x1024", "low"): .00588,
             ("1024x1024", "medium"): .01317, ("1024x1024", "high"): .05268}


class JobError(ValueError): pass


class FalError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(f"HTTP {code}: {message}")
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        return None


_no_redirect = urllib.request.build_opener(_NoRedirect()).open


class _StorageRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not isinstance(newurl, str) or not newurl.startswith(STORAGE):
            fp.close()
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def under_work(p: str, label: str) -> Path:
    if not isinstance(p, str) or not os.path.isabs(p):
        raise JobError(f"{label} must be an absolute path")
    real = Path(os.path.realpath(p))
    if Path(os.path.realpath(WORK)) not in real.parents:
        raise JobError(f"{label} must be under {WORK}")
    return real


def image_info(path: Path) -> tuple[int, int, str]:
    """Read dimensions and MIME from common raster headers without a third-party decoder."""
    try:
        b = path.read_bytes()
    except OSError as e:
        raise JobError(f"cannot read image ({e.__class__.__name__})") from None
    if not 1 <= len(b) <= MAX_BYTES:
        raise JobError(f"image must be 1 to {MAX_BYTES} bytes")
    if b.startswith(b"\x89PNG\r\n\x1a\n") and len(b) >= 24:
        w, h = struct.unpack(">II", b[16:24]); mime = "image/png"
    elif b[:3] == b"\xff\xd8\xff":
        w = h = 0; i = 2
        while i + 4 <= len(b):
            if b[i] != 0xff: i += 1; continue
            marker = b[i + 1]; i += 2
            if marker in (0xd8, 0xd9) or 0xd0 <= marker <= 0xd7: continue
            if i + 2 > len(b): break
            n = int.from_bytes(b[i:i+2], "big")
            if n < 2 or i + n > len(b): break
            if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                if n >= 7: h, w = struct.unpack(">HH", b[i+3:i+7])
                break
            i += n
        mime = "image/jpeg"
    elif len(b) >= 30 and b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        kind = b[12:16]
        if kind == b"VP8X": w = 1 + int.from_bytes(b[24:27], "little"); h = 1 + int.from_bytes(b[27:30], "little")
        elif kind == b"VP8L" and b[20] == 0x2f:
            bits = int.from_bytes(b[21:25], "little"); w = (bits & 0x3fff) + 1; h = ((bits >> 14) & 0x3fff) + 1
        else: raise JobError("unsupported or malformed WebP image")
        mime = "image/webp"
    else: raise JobError("image must be PNG, JPEG or WebP")
    if not w or not h: raise JobError("could not read image dimensions")
    return w, h, mime


def price_layerize(path: Path, layers: int) -> float:
    w, h, _ = image_info(path)
    return layers * (.03375 if w <= 1536 and h <= 1536 else .0675)


def price_edit(size: str, quality: str, refs: int) -> float:
    if quality not in ("low", "medium", "high"):
        raise JobError("quality must be low, medium or high")
    if size not in ("1920x1072", "1024x1024"):
        raise JobError("unsupported size")
    if not 1 <= refs <= 16: raise JobError("edit needs 1 to 16 references")
    return EDIT_BASE[(size, quality)] + .012 * refs


def fetch_key() -> str | None:
    key = os.environ.get(KEY_NAME, "").strip()
    if not key:
        try:
            root = Path(__file__).resolve().parent.parent
            if str(root) not in sys.path: sys.path.insert(0, str(root))
            from tools import infisical_setup as inf
            org = inf.Org(inf.self_host())
            secret = inf._get_secret(org, inf._project(org, KEY_PROJECT)["id"], KEY_ENV, KEY_NAME, KEY_PATH)
            key = (secret or {}).get("secretValue", "").strip()
        except (Exception, SystemExit) as e:
            print(f"no key: Infisical lookup failed ({e.__class__.__name__})", file=sys.stderr); return None
    if not key or not KEY_RE.fullmatch(key):
        print("no key: stored key is empty or invalid", file=sys.stderr); return None
    return key


def http_json(url: str, key: str, body: dict | None = None) -> dict:
    if not (url.startswith(QUEUE) or url == UPLOAD_URL): raise FalError(0, "refusing to send key off fal queue")
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type":"application/json"}, method="GET" if body is None else "POST")
    req.add_unredirected_header("Authorization", f"Key {key}")
    try:
        with urllib.request.urlopen(req, timeout=120) as f: raw = f.read(MAX_ANSWER + 1)
    except urllib.error.HTTPError as e:
        raise FalError(e.code, e.read(MAX_ANSWER).decode(errors="replace").replace(key, "<redacted>")[:300]) from None
    if len(raw) > MAX_ANSWER: raise FalError(0, "fal answer too large")
    res = json.loads(raw)
    if not isinstance(res, dict): raise FalError(0, "fal answer is not an object")
    return res


def upload(path: Path, key: str) -> str:
    _, _, mime = image_info(path); data = path.read_bytes()
    init = http_json(UPLOAD_URL, key, {"content_type": mime, "file_name": path.name})
    up, dest = init.get("upload_url"), init.get("file_url")
    if not isinstance(up, str) or not up.startswith(STORAGE) or not isinstance(dest, str) or not dest.startswith(STORAGE):
        raise FalError(0, "refusing upload outside fal storage")
    req = urllib.request.Request(up, data=data, headers={"Content-Type":mime}, method="PUT")
    try:
        with _no_redirect(req, timeout=120) as f: f.read(MAX_ANSWER)
    except urllib.error.HTTPError as e: raise FalError(e.code, "fal storage upload failed") from None
    return dest


def download(url: object, dest: Path) -> None:
    if not isinstance(url, str) or not url.startswith(STORAGE): raise FalError(0, "image URL is not fal storage")
    with urllib.request.build_opener(_StorageRedirect()).open(url, timeout=120) as f:
        final = urllib.parse.urlsplit(f.geturl())
        if final.scheme != "https" or not f.geturl().startswith(STORAGE): raise FalError(0, "image redirect left fal storage")
        data = f.read(MAX_BYTES + 1); want = f.headers.get("Content-Length")
    if not data or len(data) > MAX_BYTES or (want and want.isdigit() and int(want) != len(data)):
        raise FalError(0, "image download empty, oversized or incomplete")
    tmp = dest.with_name(dest.name + ".part"); tmp.write_bytes(data); tmp.replace(dest)


def one_call(model: str, key: str, body: dict) -> tuple[str | None, dict]:
    sub = http_json(QUEUE + model, key, body)
    for _ in range(POLL_N):
        if http_json(sub["status_url"], key).get("status") == "COMPLETED": break
        time.sleep(POLL_S)
    else: raise FalError(0, "fal request timed out")
    return sub.get("request_id"), http_json(sub["response_url"], key)


def cap_number(s: str) -> float:
    if not CAP_RE.fullmatch(s): raise argparse.ArgumentTypeError("a plain number such as 0.07")
    return float(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("--job", required=True); ap.add_argument("--max-usd", required=True, type=cap_number)
    ap.add_argument("--out", required=True); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fire", action="store_true", help="send paid calls; default is dry-run")
    subs = ap.add_subparsers(dest="kind", required=True)
    lp = subs.add_parser("layerize", allow_abbrev=False); lp.add_argument("--image", required=True); lp.add_argument("--prompt", required=True)
    ep = subs.add_parser("edit", allow_abbrev=False); ep.add_argument("--prompt", required=True); ep.add_argument("--ref", action="append", required=True); ep.add_argument("--quality", required=True); ep.add_argument("--size", required=True)
    a = ap.parse_args(argv)
    if a.fire and a.dry_run: ap.error("--fire and --dry-run cannot be combined")
    if not NAME_RE.fullmatch(a.job): ap.error("--job must be a short ledger name")
    try:
        out = under_work(a.out, "--out")
        if a.kind == "layerize":
            # fal returns a base image plus up to 16 layers and has no count input: reserve all 17 (CTO review).
            image = under_work(a.image, "--image")
            model = LAYERIZE; cost = price_layerize(image, MAX_LAYERS)
            refs = [image]; body = {"image_url": None, "prompt": a.prompt}
        else:
            if a.quality not in ("low", "medium", "high"): raise JobError("quality must be low, medium or high (auto/xhigh/max refused)")
            refs = [under_work(p, "--ref") for p in a.ref]
            for p in refs: image_info(p)
            cost = price_edit(a.size, a.quality, len(refs)); model = EDIT
            body = {"prompt": a.prompt, "quality": a.quality, "image_size": {"1920x1072": {"width":1920,"height":1072}, "1024x1024":{"width":1024,"height":1024}}[a.size], "output_format":"png"}
    except (JobError, KeyError) as e:
        print(f"bad request: {e}", file=sys.stderr); return 2
    led = WORK / f"{a.job}.ledger.jsonl"
    try:
        led.parent.mkdir(parents=True, exist_ok=True); lf = led.open("a+", encoding="utf8")
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lf.seek(0); spent = 0.0
        for n, line in enumerate(lf, 1):
            try:
                row = json.loads(line)
                if row.get("what") == "attempt":
                    usd = float(row["usd"])
                    if not usd >= 0: raise ValueError
                    spent += usd
            except (ValueError, KeyError, TypeError): raise JobError(f"ledger row {n} unreadable")
    except (OSError, BlockingIOError, JobError, ValueError, TypeError, KeyError) as e:
        print(f"bad ledger: {e.__class__.__name__}", file=sys.stderr); return 2
    print(f"{model}: worst-case ${cost:.5f}; ledger ${spent:.5f}; cap ${a.max_usd:g}")
    if spent + cost > a.max_usd + 1e-12:
        print(f"spend cap reached: spent {spent:.10g} of {a.max_usd:.10g}"); lf.close(); return EXIT_CAP
    if not a.fire:
        print("dry run: no upload, key lookup, ledger write or generation call"); lf.close(); return 0
    key = fetch_key()
    if not key: lf.close(); return EXIT_KEY
    server_errors = 0
    try:
        try:
            urls = [upload(p, key) for p in refs]
            if model == LAYERIZE: body["image_url"] = urls[0]
            else: body["image_urls"] = urls
            lf.seek(0, os.SEEK_END); lf.write(json.dumps({"at":dt.datetime.now(dt.timezone.utc).isoformat(),"what":"attempt","model":model,"usd":cost})+"\n"); lf.flush(); os.fsync(lf.fileno())
            rid, res = one_call(model, key, body)
            images = res.get("images")
            if not isinstance(images, list) and isinstance(res.get("layers"), list): images = [x.get("image") for x in res["layers"] if isinstance(x, dict)]
            if not isinstance(images, list) or not images: raise FalError(0, "fal answer has no images")
            out.mkdir(parents=True, exist_ok=True)
            for i, img in enumerate(images, 1):
                if not isinstance(img, dict): raise FalError(0, "invalid image entry")
                url = img.get("url"); ext = "png"
                path = out / f"{a.job}-{i:02d}.{ext}"; download(url, path); print(path)
            lf.write(json.dumps({"at":dt.datetime.now(dt.timezone.utc).isoformat(),"what":"result","ok":True,"request_id":rid})+"\n"); lf.flush(); os.fsync(lf.fileno())
            return 0
        except FalError as e:
            lf.write(json.dumps({"at":dt.datetime.now(dt.timezone.utc).isoformat(),"what":"result","ok":False,"code":e.code})+"\n"); lf.flush(); os.fsync(lf.fileno())
            print(f"FAIL: {str(e).replace(key, '<redacted>')}", file=sys.stderr)
            if e.code >= 500: server_errors += 1
            if server_errors >= MAX_5XX: return 1
            return 1
    finally: lf.close()


if __name__ == "__main__": sys.exit(main())
