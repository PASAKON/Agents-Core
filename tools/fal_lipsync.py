"""Lipsync on fal (fal-ai/sync-lipsync: lipsync-1.9.0-beta and lipsync-2) that stops at its own spend cap:
a declared spend tool for Run Inbox script cards (Console docs/run.md §Spend label, config/spend-tools.txt).
CMO Ging, 2026-11-05.

A job file lists the calls against one reference video. Before each call the tool prices it from the duration
in seconds of its local input audio file (seconds times the model's price in PRICES) and stops if the running
total would pass --max-usd. The total starts from the attempts already in the job's ledger, so every run of
one job shares one cap. Every attempt counts as spent, failed or not, so two server errors (HTTP 5xx) in a row
stop the job: the model is down. A call whose output video file already exists is skipped and costs nothing.

The fal key comes from FAL_MEDIA_API_KEY_RW in the environment, or, on a Run card, from Infisical
(Agents-Core prod /cmo-media) as this host's machine identity. It is never printed, and it goes only to
queue.fal.run and rest.alpha.fal.ai (to initiate a fal storage upload), never to the file host the media
comes from or goes to, and never through a redirect: the queue's and storage upload's redirects are refused,
and the file host's downloads are followed to https only, their bodies unread. Reference video and input audio
are uploaded to fal storage only. A key holding anything but printable ASCII is refused unseen. fal's answers
are read up to MAX_ANSWER bytes and the video up to MAX_VIDEO, and a video file shorter than its
Content-Length is refused. Standard library only: a script card runs this file with the system python3.

Job file (JSON). Every path is absolute and under /opt/MoonieXHQ/Work/:
  {"model": "lipsync-1.9.0-beta", "reference_video": "/opt/MoonieXHQ/Work/<job>/avatar.mp4",
   "out_dir": "/opt/MoonieXHQ/Work/<job>/parts",
   "calls": [{"name": "part_01", "audio_file": "/opt/MoonieXHQ/Work/<job>/takes/part_01.mp3",
              "sync_mode": "cut_off"}]}
Each call writes <out_dir>/<name>.mp4 (or the .mov or .webm that fal's content type names) and <name>.json.
The ledger is <job file name without .json>.ledger.jsonl, next to the job file.

Usage: python3 tools/fal_lipsync.py --job /opt/MoonieXHQ/Work/<job>/job.json --max-usd 1.50 [--dry-run]
Exit: 0 every call saved or skipped · 1 a call failed · 2 bad job, ledger or arguments ·
      3 stopped before the cap · 4 no key
"""
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
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path("/opt/MoonieXHQ/Work")
ENDPOINT = "fal-ai/sync-lipsync"
V1, V2 = "lipsync-1.9.0-beta", "lipsync-2"
# USD per second of input audio, read off fal-ai/sync-lipsync model page ($0.70/min = $0.0117/s; $3.00/min = $0.05/s).
PRICES = {V1: 0.0117, V2: 0.05}
# cut_off only: it ends the output at the shorter of video and audio, so the audio seconds priced above are an
# upper bound. loop/bounce/silence/remap can run the output to the video's length, which this tool does not price
# (CTO review of PR #664, 5 Nov 2026).
SYNC_MODES = frozenset({"cut_off"})
CALL_KEYS = {"name", "audio_file", "sync_mode"}
QUEUE = "https://queue.fal.run/"
UPLOAD_URL = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"
STORAGE_HOSTS = ("https://v3.fal.media/", "https://v3b.fal.media/", "https://fal.media/")
KEY_NAME = "FAL_MEDIA_API_KEY_RW"
KEY_PROJECT, KEY_ENV, KEY_PATH = "Agents-Core", "prod", "/cmo-media"
# Printable ASCII only: http.client puts a header value holding CR or LF in its error text, which redact misses.
KEY_RE = re.compile(r"^[!-~]{8,1024}$")
MAX_ANSWER, MAX_AUDIO, MAX_VIDEO = 1 << 20, 64 << 20, 128 << 20
MAX_CALLS = 60
MAX_SECONDS = 600.0
POLL_S, POLL_N = 4, 225
MAX_SERVER_ERRORS = 2  # in a row; every attempt counts as spent, so a model that is down stops the job here
AUDIO_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav"}
VIDEO_TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
MEDIA_TYPES = {**AUDIO_TYPES, **VIDEO_TYPES}
VIDEO_EXT = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"}
VIDEO_EXTS = sorted(set(VIDEO_EXT.values()))
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
CAP_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")  # the hub's own cap number (tools/ask_run.py _CAP_NUMBER)
EXIT_FAIL, EXIT_BAD, EXIT_CAP, EXIT_KEY = 1, 2, 3, 4

_MP3_BR_V1 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
_MP3_BR_V2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)
_MP3_SR = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}


class JobError(ValueError):
    """The job file, a path in it or its ledger is not usable; nothing was spent."""


class FalError(Exception):
    def __init__(self, code: int, text: str) -> None:
        super().__init__(f"HTTP {code}: {text}")
        self.code = code


class _Redirects(urllib.request.HTTPRedirectHandler):
    """urllib reads a redirect's whole body before it follows it, with no limit. This closes the body unread
    (that read then gets nothing) and follows only to https; with `follow` false it refuses every redirect."""
    follow = True

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not self.follow or not newurl.startswith("https://"):
            return None  # urllib then returns before that read and raises HTTPError(code)
        fp.close()
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _NoRedirects(_Redirects):
    follow = False


_queue_open = urllib.request.build_opener(_NoRedirects).open  # fal's queue and storage PUT answer in place
_file_open = urllib.request.build_opener(_Redirects).open     # the file host may send us on, to https only


def under_work(p: object, what: str) -> Path:
    """The real path of `p` when it is absolute and lies under WORK once symlinks are followed."""
    if not isinstance(p, str) or not os.path.isabs(p):
        raise JobError(f"{what} must be an absolute path")
    real = Path(os.path.realpath(p))
    if Path(os.path.realpath(WORK)) not in real.parents:
        raise JobError(f"{what} must be under {WORK}")
    return real


def _media_file(p: object, what: str, allowed: dict[str, str], max_bytes: int) -> Path:
    real = under_work(p, what)
    if real.suffix.lower() not in allowed:
        raise JobError(f"{what} must be one of {sorted(allowed)}")
    try:
        st = real.stat()
    except OSError as e:
        raise JobError(f"cannot read {what} ({e.__class__.__name__})") from None
    if not os.path.isfile(real) or not 1 <= st.st_size <= max_bytes:
        raise JobError(f"{what} must be a regular file of 1 to {max_bytes} bytes")
    return real


def _wav_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            frames = w.getnframes()
            if rate > 0 and frames > 0:
                return frames / rate
    except (wave.Error, EOFError, OSError):
        pass
    try:
        data = path.read_bytes()
    except OSError as e:
        raise JobError(f"cannot read {path.name} ({e.__class__.__name__})") from None
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise JobError(f"cannot read duration of {path.name}")
    pos, byte_rate, data_size = 12, 0, 0
    while pos + 8 <= len(data):
        cid = data[pos : pos + 4]
        csz = struct.unpack_from("<I", data, pos + 4)[0]
        if pos + 8 + csz > len(data):
            break
        if cid == b"fmt " and csz >= 16:
            byte_rate = struct.unpack_from("<I", data, pos + 16)[0]
        elif cid == b"data":
            data_size = csz
        pos += 8 + csz + (csz & 1)
    if byte_rate <= 0 or data_size <= 0:
        raise JobError(f"cannot read duration of {path.name}")
    return data_size / byte_rate


def _mp3_seconds(path: Path) -> float:
    try:
        data = path.read_bytes()
    except OSError as e:
        raise JobError(f"cannot read {path.name} ({e.__class__.__name__})") from None
    pos = 0
    if len(data) >= 10 and data[:3] == b"ID3":
        if any(b & 0x80 for b in data[6:10]):
            raise JobError(f"cannot read duration of {path.name}")
        tag_sz = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        pos = 10 + tag_sz + (10 if (data[5] & 0x10) else 0)
    end = len(data) - 128 if len(data) >= 128 and data[-128:-125] == b"TAG" else len(data)
    frames = 0
    seconds = 0.0
    while pos + 4 <= end:
        if data[pos : pos + 3] == b"TAG":
            break
        h0, h1, h2, h3 = data[pos : pos + 4]
        if h0 != 0xFF or (h1 & 0xE0) != 0xE0:
            break
        ver = (h1 >> 3) & 0x03
        layer = (h1 >> 1) & 0x03
        br_idx = (h2 >> 4) & 0x0F
        sr_idx = (h2 >> 2) & 0x03
        pad = (h2 >> 1) & 0x01
        mode = (h3 >> 6) & 0x03
        if ver == 1 or layer != 1 or not 1 <= br_idx <= 14 or sr_idx == 3:
            break
        br = (_MP3_BR_V1 if ver == 3 else _MP3_BR_V2)[br_idx]
        sr = _MP3_SR[ver][sr_idx]
        spf = 1152 if ver == 3 else 576
        fsz = ((144 if ver == 3 else 72) * br * 1000) // sr + pad
        if fsz < 4 or pos + fsz > end:
            break
        if frames == 0:
            side = (17 if mode == 3 else 32) if ver == 3 else (9 if mode == 3 else 17)
            xoff = pos + 4 + side
            if xoff + 8 <= pos + fsz and data[xoff : xoff + 4] in (b"Xing", b"Info"):
                flags = struct.unpack_from(">I", data, xoff + 4)[0]
                if (flags & 0x01) and xoff + 12 <= pos + fsz:
                    total_frames = struct.unpack_from(">I", data, xoff + 8)[0]
                    if total_frames > 0:
                        return (total_frames * spf) / sr
                pos += fsz
                continue
        seconds += spf / sr
        frames += 1
        pos += fsz
    if frames == 0 or seconds <= 0:
        raise JobError(f"cannot read duration of {path.name}")
    return seconds


def audio_seconds(path: Path) -> float:
    sec = _wav_seconds(path) if path.suffix.lower() == ".wav" else _mp3_seconds(path)
    if not 0 < sec <= MAX_SECONDS:
        raise JobError(f"{path.name}: duration must be > 0 and at most {MAX_SECONDS:g} s")
    return sec


def load_job(job_path: Path) -> dict:
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise JobError(f"cannot read the job file ({e.__class__.__name__})") from None
    if not isinstance(job, dict) or set(job) - {"model", "out_dir", "calls", "reference_video", "video_file"}:
        raise JobError("the job file holds one object with model, reference_video, out_dir and calls")
    if ("reference_video" in job) == ("video_file" in job):
        raise JobError("the job file must specify reference_video (or video_file)")
    model = job.get("model")
    if not isinstance(model, str) or model not in PRICES:
        raise JobError(f"model must be one of {sorted(PRICES)}")
    vkey = "reference_video" if "reference_video" in job else "video_file"
    video_path = _media_file(job.get(vkey), vkey, VIDEO_TYPES, MAX_VIDEO)
    out_dir = under_work(job.get("out_dir"), "out_dir")
    calls = job.get("calls")
    if not isinstance(calls, list) or not 1 <= len(calls) <= MAX_CALLS:
        raise JobError(f"calls must be a list of 1 to {MAX_CALLS} calls")
    seen: set[str] = set()
    out = []
    for i, c in enumerate(calls, 1):
        if not isinstance(c, dict) or set(c) - CALL_KEYS:
            raise JobError(f"call {i} must be an object with only {sorted(CALL_KEYS)}")
        name = c.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name in seen:
            raise JobError(f"call {i}: name must be unique and match {NAME_RE.pattern}")
        seen.add(name)
        audio_path = _media_file(c.get("audio_file"), f"call {i} audio_file", AUDIO_TYPES, MAX_AUDIO)
        seconds = audio_seconds(audio_path)
        body: dict = {"model": model}
        if "sync_mode" in c:
            sm = c["sync_mode"]
            if not isinstance(sm, str) or sm not in SYNC_MODES:
                raise JobError(f"call {i}: sync_mode must be one of {sorted(SYNC_MODES)}")
            body["sync_mode"] = sm
        out.append({"name": name, "audio": audio_path, "seconds": seconds, "body": body})
    return {"model": model, "price": PRICES[model], "video": video_path, "out_dir": out_dir, "calls": out}


def ledger_path(job_path: Path) -> Path:
    return job_path.with_name(job_path.name.removesuffix(".json") + ".ledger.jsonl")


def ledger_spent(lf) -> float:
    """USD of every attempt in the open ledger. An unreadable row refuses: it must never read as $0."""
    lf.seek(0)
    total = 0.0
    for n, line in enumerate(lf, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if row["what"] == "attempt":
                usd = float(row["usd"])
                if not usd >= 0:
                    raise ValueError
                total += usd
        except (ValueError, KeyError, TypeError):
            raise JobError(f"ledger row {n} is unreadable; fix the ledger by hand before spending") from None
    return total


def write_row(lf, row: dict) -> None:
    lf.seek(0, os.SEEK_END)
    lf.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **row},
                        ensure_ascii=False) + "\n")
    lf.flush()
    os.fsync(lf.fileno())


def fetch_key() -> str | None:
    key = os.environ.get(KEY_NAME, "").strip()
    if not key:
        try:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from tools import infisical_setup as inf
            org = inf.Org(inf.self_host())
            secret = inf._get_secret(org, inf._project(org, KEY_PROJECT)["id"], KEY_ENV, KEY_NAME, KEY_PATH)
        except (Exception, SystemExit) as e:  # _project() exits when the project is missing
            print(f"no key: Infisical lookup failed ({e.__class__.__name__})", file=sys.stderr)
            return None
        value = (secret or {}).get("secretValue")
        key = value.strip() if isinstance(value, str) else ""
    if not key:
        print(f"no key: {KEY_NAME} is empty", file=sys.stderr)
        return None
    if not KEY_RE.fullmatch(key):
        print("no key: the stored key is not one line of printable ASCII", file=sys.stderr)
        return None
    return key


def http_json(url: object, key: str, body: dict | None = None) -> dict:
    if not isinstance(url, str) or not (url.startswith(QUEUE) or url == UPLOAD_URL):
        raise FalError(0, "refusing to send the key off queue.fal.run")
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    # urllib copies ordinary headers to a redirect's target, which may be another host; this one stays behind.
    req.add_unredirected_header("Authorization", f"Key {key}")
    try:
        with _queue_open(req, timeout=120) as f:
            raw = f.read(MAX_ANSWER + 1)
    except urllib.error.HTTPError as e:
        text = e.read(MAX_ANSWER).decode(errors="replace").replace(key, "<redacted>")
        raise FalError(e.code, text[:300]) from None
    if len(raw) > MAX_ANSWER:
        raise FalError(0, f"the answer is larger than {MAX_ANSWER} bytes")
    res = json.loads(raw)
    if not isinstance(res, dict):
        raise FalError(0, "the answer is not a JSON object")
    return res


def upload(path: Path, key: str) -> str:
    """Upload a local media file to fal storage only; the PUT carries no key and follows no redirect."""
    suffix = path.suffix.lower()
    ct = MEDIA_TYPES.get(suffix)
    if not ct:
        raise FalError(0, f"unsupported media file type {path.suffix}")
    limit = MAX_VIDEO if suffix in VIDEO_TYPES else MAX_AUDIO
    data = path.read_bytes()
    if not 1 <= len(data) <= limit:
        raise FalError(0, f"{path.name} must be 1 to {limit} bytes")
    ini = http_json(UPLOAD_URL, key, {"content_type": ct, "file_name": path.name})
    up, file_url = ini.get("upload_url"), ini.get("file_url")
    if (not isinstance(up, str) or not up.startswith(STORAGE_HOSTS)
            or not isinstance(file_url, str) or not file_url.startswith(STORAGE_HOSTS)):
        raise FalError(0, "refusing to upload off fal storage")
    req = urllib.request.Request(up, data=data, headers={"Content-Type": ct}, method="PUT")
    try:
        with _queue_open(req, timeout=300) as f:
            f.read(MAX_ANSWER)
    except urllib.error.HTTPError as e:
        text = e.read(MAX_ANSWER).decode(errors="replace").replace(key, "<redacted>")
        raise FalError(e.code, text[:300]) from None
    return file_url


def download(url: object, dest: Path) -> None:
    """The output video file, fetched with no key, written whole or not at all."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise FalError(0, "the video URL is not https")
    with _file_open(url, timeout=300) as f:
        want = None if getattr(f, "chunked", False) else str(f.headers.get("Content-Length") or "").strip()
        data = f.read(MAX_VIDEO + 1)
    if len(data) > MAX_VIDEO:
        raise FalError(0, f"the video file is larger than {MAX_VIDEO} bytes")
    # A bounded read returns a short body without IncompleteRead, so the length is checked here.
    if not data or (want and want.isdigit() and int(want) != len(data)):
        raise FalError(0, f"the video file arrived empty or cut off ({len(data)} of {want or '?'} bytes)")
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)


def video_ext(video: object) -> str:
    if not isinstance(video, dict):
        raise ValueError("fal's answer holds no video file")
    ext = VIDEO_EXT.get(str(video.get("content_type") or "").split(";")[0].strip().lower())
    if ext:
        return ext
    suffix = urllib.parse.urlsplit(str(video.get("url") or "")).path.rpartition(".")[2].lower()
    return suffix if suffix in VIDEO_EXTS else "mp4"


def one_call(key: str, body: dict) -> tuple[str | None, dict]:
    sub = http_json(QUEUE + ENDPOINT, key, body)
    for _ in range(POLL_N):
        if http_json(sub["status_url"], key).get("status") == "COMPLETED":
            break
        time.sleep(POLL_S)
    else:
        raise FalError(0, f"not COMPLETED after {POLL_S * POLL_N} s, request {sub.get('request_id')}")
    return sub.get("request_id"), http_json(sub["response_url"], key)


def cap_number(s: str) -> float:
    if not CAP_RE.fullmatch(s):
        raise argparse.ArgumentTypeError("a plain number such as 1.50")
    return float(s)


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    ap.add_argument("--job", required=True, help="the job file, an absolute path under /opt/MoonieXHQ/Work/")
    ap.add_argument("--max-usd", required=True, type=cap_number, help="never spend more than this, in USD")
    ap.add_argument("--dry-run", action="store_true", help="price the job; call nothing, write nothing")
    a = ap.parse_args(raw_argv)
    if sum(v == "--max-usd" or v.startswith("--max-usd=") for v in raw_argv) != 1:
        ap.error("--max-usd must occur exactly once")
    try:
        job_path = under_work(a.job, "--job")
        job = load_job(job_path)
    except JobError as e:
        print(f"bad job: {e}", file=sys.stderr)
        return EXIT_BAD
    model, price, video_path, out_dir = job["model"], job["price"], job["video"], job["out_dir"]
    led = ledger_path(job_path)
    if a.dry_run and not led.exists():
        lf = None
        spent = 0.0
    else:
        lf = open(led, "a+", encoding="utf-8")
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another run of this job holds its ledger", file=sys.stderr)
            lf.close()
            return EXIT_BAD
        try:
            spent = ledger_spent(lf)
        except JobError as e:
            print(f"bad ledger: {e}", file=sys.stderr)
            lf.close()
            return EXIT_BAD
    print(f"{ENDPOINT} ({model}): {len(job['calls'])} calls, ${price:g} per second; "
          f"ledger ${spent:.4f}; cap ${a.max_usd:g}", flush=True)
    key = None
    if not a.dry_run:
        key = fetch_key()
        if not key:
            return EXIT_KEY
    redact = (lambda s: s.replace(key, "<redacted>")) if key else (lambda s: s)
    saved = skipped = fails = server_errors = 0
    uploaded: dict[Path, str] = {}
    try:
        for c in job["calls"]:
            name = c["name"]
            have = [p for p in (out_dir / f"{name}.{x}" for x in VIDEO_EXTS) if p.exists()]
            if have:
                skipped += 1
                print(f"skip {name}: {have[0].name} exists", flush=True)
                continue
            cost = c["seconds"] * price
            if spent + cost > a.max_usd + 1e-12:
                print(f"STOP before {name}: ${spent + cost:.4f} would pass the cap ${a.max_usd:g}", flush=True)
                return EXIT_CAP
            spent += cost
            if a.dry_run:
                print(f"dry run: {name} {c['seconds']:.2f} s ${cost:.4f}, total ${spent:.4f}", flush=True)
                continue
            write_row(lf, {"what": "attempt", "name": name, "model": model, "seconds": round(c["seconds"], 3),
                           "usd": round(cost, 6)})
            try:
                if video_path not in uploaded:
                    uploaded[video_path] = upload(video_path, key)
                audio_path = c["audio"]
                if audio_path not in uploaded:
                    uploaded[audio_path] = upload(audio_path, key)
                body = {**c["body"], "video_url": uploaded[video_path], "audio_url": uploaded[audio_path]}
                rid, res = one_call(key, body)
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
                video_out = out_dir / f"{name}.{video_ext(res.get('video') if isinstance(res, dict) else None)}"
                download(res["video"]["url"], video_out)
            except FalError as e:
                write_row(lf, {"what": "result", "name": name, "ok": False, "code": e.code})
                print(f"FAIL {name}: {redact(str(e))}", flush=True)
                fails += 1
                if e.code in (401, 403):
                    print("the key or the account was refused; stopping the job", flush=True)
                    return EXIT_FAIL
                server_errors = server_errors + 1 if e.code >= 500 else 0
                if server_errors >= MAX_SERVER_ERRORS:
                    print(f"{server_errors} server errors in a row: the model looks down; stopping the job",
                          flush=True)
                    return EXIT_FAIL
                continue
            except (OSError, ValueError, KeyError, TypeError, RecursionError, http.client.HTTPException) as e:
                write_row(lf, {"what": "result", "name": name, "ok": False, "code": e.__class__.__name__})
                print(f"FAIL {name}: {e.__class__.__name__}: {redact(str(e))[:200]}", flush=True)
                fails += 1
                server_errors = 0
                continue
            write_row(lf, {"what": "result", "name": name, "ok": True, "request_id": rid})
            saved += 1
            server_errors = 0
            print(f"saved {video_out.name}: {c['seconds']:.2f} s ${cost:.4f}, request {rid}", flush=True)
    finally:
        print(f"done: {saved} saved, {skipped} skipped, {fails} failed; job ${spent:.4f} of cap "
              f"${a.max_usd:g}{' (dry run)' if a.dry_run else ''}; ledger {led}", flush=True)
        if lf:
            lf.close()
    return EXIT_FAIL if fails else 0


if __name__ == "__main__":
    sys.exit(main())
