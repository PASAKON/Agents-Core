"""Text to speech on fal (ElevenLabs v4, Gemini 3.1 and 3.8 Flash TTS) that stops at its own spend cap:
a declared spend tool for Run Inbox script cards (Console docs/run.md §Spend label, config/spend-tools.txt).
CMO Ging, 2026-10-26; Gemini 3.1 and 3.8 added 2026-10-27.

A job file lists the calls. Before each call the tool prices it from its text (characters times the
model's price in PRICES) and stops if the running total would pass --max-usd. The total starts from the
attempts already in the job's ledger, so every run of one job shares one cap. Every attempt counts as
spent, failed or not, so two server errors (HTTP 5xx) in a row stop the job: the model is down. A call whose
audio file already exists is skipped and costs nothing.

The fal key comes from FAL_MEDIA_API_KEY_RW in the environment, or, on a Run card, from Infisical
(Agents-Core prod /cmo-media) as this host's machine identity. It is never printed, and it goes only to
queue.fal.run, never to the file host the audio comes from. Standard library only: a script card runs
this file with the system python3.

Job file (JSON). Every path is absolute and under /opt/MoonieXHQ/Work/:
  {"model": "elevenlabs/tts/eleven-v4", "out_dir": "/opt/MoonieXHQ/Work/<job>/takes",
   "calls": [{"name": "t1_Brian_s0.5", "text_file": "/opt/MoonieXHQ/Work/<job>/narration.txt",
              "voice": "Brian", "stability": 0.5, "language_code": "th", "seed": 7, "timestamps": true}]}
Gemini 3.1 Flash TTS takes one of its 30 preset voices and a voice block in style_instructions (age, timbre,
pace, accent; the same presets as Google Flow's voices). Its calls are priced on the text plus the
style_instructions, so the cap holds even if fal bills both:
  {"model": "fal-ai/gemini-3.1-flash-tts", "out_dir": "/opt/MoonieXHQ/Work/<job>/takes",
   "calls": [{"name": "v1_Charon", "text_file": "/opt/MoonieXHQ/Work/<job>/narration.txt", "voice": "Charon",
              "style_instructions": "A Thai storyteller in his fifties ...", "language_code": "th",
              "temperature": 1.0}]}
Gemini 3.8 Flash TTS (listed on fal as google/gemini-3.8-flash-tts) takes the same 30 voices and
style_instructions, and no language_code, temperature or output format: it reads the language from the text.
  {"model": "fal-ai/gemini-3.8-flash-tts", "out_dir": "/opt/MoonieXHQ/Work/<job>/takes",
   "calls": [{"name": "v1_Charon", "text_file": "/opt/MoonieXHQ/Work/<job>/narration.txt", "voice": "Charon",
              "style_instructions": "A Thai storyteller in his fifties ..."}]}
Each call writes <out_dir>/<name>.mp3 (or the .wav, .ogg or .flac that fal's content type names) and
<name>.json (fal's whole answer, timestamps included).
The ledger is <job file name without .json>.ledger.jsonl, next to the job file.

Usage: python3 tools/fal_tts.py --job /opt/MoonieXHQ/Work/<job>/job.json --max-usd 0.07 [--dry-run]
Exit: 0 every call saved or skipped · 1 a call failed · 2 bad job, ledger or arguments ·
      3 stopped before the cap · 4 no key
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path("/opt/MoonieXHQ/Work")
# USD per character sent. Add a model only with its price read off its fal model page.
ELEVEN, GEMINI = "elevenlabs/tts/eleven-v4", "fal-ai/gemini-3.1-flash-tts"
# fal lists 3.8 as google/gemini-3.8-flash-tts; its OpenAPI schema serves the queue at this path (read 2026-10-27).
GEMINI38 = "fal-ai/gemini-3.8-flash-tts"
PRICES = {ELEVEN: 0.08 / 1000,     # "$0.08 per 1000 character", read 2026-10-26
          GEMINI: 0.05 / 1000,     # "Your request will cost $0.05 per 1000 character.", read 2026-10-27
          GEMINI38: 0.045 / 1000}  # "Your request will cost $0.045 per 1000 character.", read 2026-10-27
QUEUE = "https://queue.fal.run/"
KEY_NAME = "FAL_MEDIA_API_KEY_RW"
KEY_PROJECT, KEY_ENV, KEY_PATH = "Agents-Core", "prod", "/cmo-media"
MAX_CALLS = 60
MAX_CHARS = 5000
POLL_S, POLL_N = 2, 150
CALL_KEYS = {ELEVEN: {"name", "text_file", "voice", "stability", "similarity_boost", "language_code", "seed",
                      "timestamps"},
             GEMINI: {"name", "text_file", "voice", "style_instructions", "language_code", "temperature"},
             GEMINI38: {"name", "text_file", "voice", "style_instructions"}}
# The voice enum of fal-ai/gemini-3.1-flash-tts, the same for 3.8 (queue OpenAPI schemas, read 2026-10-27).
GEMINI_VOICES = frozenset("""Achernar Achird Algenib Algieba Alnilam Aoede Autonoe Callirrhoe Charon Despina Enceladus
    Erinome Fenrir Gacrux Iapetus Kore Laomedeia Leda Orus Pulcherrima Puck Rasalgethi Sadachbia Sadaltager Schedar
    Sulafat Umbriel Vindemiatrix Zephyr Zubenelgenubi""".split())
# Gemini takes the language's display name; "th-TH" is refused with 422.
GEMINI_LANGS = {"th": "Thai (Thailand)", "en": "English (US)"}
MAX_STYLE = 2000
MAX_SERVER_ERRORS = 2  # in a row; every attempt counts as spent, so a model that is down stops the job here
# The saved file's extension by the content type fal reports, else by the URL's own suffix, else mp3.
AUDIO_EXT = {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/x-wav": "wav",
             "audio/wave": "wav", "audio/ogg": "ogg", "audio/flac": "flac"}
AUDIO_EXTS = sorted(set(AUDIO_EXT.values()))
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
VOICE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,47}$")
LANG_RE = re.compile(r"^[a-z]{2}$")
CAP_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")  # the hub's own cap number (tools/ask_run.py _CAP_NUMBER)
EXIT_FAIL, EXIT_BAD, EXIT_CAP, EXIT_KEY = 1, 2, 3, 4


class JobError(ValueError):
    """The job file, a path in it or its ledger is not usable; nothing was spent."""


class FalError(Exception):
    def __init__(self, code: int, text: str) -> None:
        super().__init__(f"HTTP {code}: {text}")
        self.code = code


def under_work(p: object, what: str) -> Path:
    """The real path of `p` when it is absolute and lies under WORK once symlinks are followed."""
    if not isinstance(p, str) or not os.path.isabs(p):
        raise JobError(f"{what} must be an absolute path")
    real = Path(os.path.realpath(p))
    if Path(os.path.realpath(WORK)) not in real.parents:
        raise JobError(f"{what} must be under {WORK}")
    return real


def _unit(c: dict, k: str, i: int) -> float:
    v = c[k]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1:
        raise JobError(f"call {i}: {k} must be a number from 0 to 1")
    return float(v)


def load_job(job_path: Path) -> dict:
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise JobError(f"cannot read the job file ({e.__class__.__name__})") from None
    if not isinstance(job, dict) or set(job) - {"model", "out_dir", "calls"}:
        raise JobError("the job file holds one object with model, out_dir and calls")
    model = job.get("model")
    if not isinstance(model, str) or model not in PRICES:
        raise JobError(f"model must be one of {sorted(PRICES)}")
    out_dir = under_work(job.get("out_dir"), "out_dir")
    calls = job.get("calls")
    if not isinstance(calls, list) or not 1 <= len(calls) <= MAX_CALLS:
        raise JobError(f"calls must be a list of 1 to {MAX_CALLS} calls")
    seen: set[str] = set()
    out = []
    keys = CALL_KEYS[model]
    for i, c in enumerate(calls, 1):
        if not isinstance(c, dict) or set(c) - keys:
            raise JobError(f"call {i} must be an object with only {sorted(keys)}")
        name = c.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name in seen:
            raise JobError(f"call {i}: name must be unique and match {NAME_RE.pattern}")
        seen.add(name)
        text_path = under_work(c.get("text_file"), f"call {i} text_file")
        try:
            text = text_path.read_text(encoding="utf-8").strip()
        except (OSError, ValueError) as e:
            raise JobError(f"call {i}: cannot read text_file ({e.__class__.__name__})") from None
        if not 1 <= len(text) <= MAX_CHARS:
            raise JobError(f"call {i}: the text must be 1 to {MAX_CHARS} characters")
        voice = c.get("voice")
        if not isinstance(voice, str) or not VOICE_RE.fullmatch(voice):
            raise JobError(f"call {i}: voice must match {VOICE_RE.pattern}")
        if model in (GEMINI, GEMINI38):
            out.append(_gemini_call(model, c, i, name, text, voice))
            continue
        body: dict = {"text": text, "voice": voice}
        for k in ("stability", "similarity_boost"):
            if k in c:
                body[k] = _unit(c, k, i)
        if "language_code" in c:
            if not isinstance(c["language_code"], str) or not LANG_RE.fullmatch(c["language_code"]):
                raise JobError(f"call {i}: language_code must be two small letters")
            body["language_code"] = c["language_code"]
        if "seed" in c:
            seed = c["seed"]
            if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2 ** 31:
                raise JobError(f"call {i}: seed must be a whole number from 0 to 2^31-1")
            body["seed"] = seed
        ts = c.get("timestamps", False)
        if not isinstance(ts, bool):
            raise JobError(f"call {i}: timestamps must be true or false")
        if ts:
            body["timestamps"] = True
        out.append({"name": name, "body": body, "chars": len(text)})
    return {"model": model, "price": PRICES[model], "out_dir": out_dir, "calls": out}


def _gemini_call(model: str, c: dict, i: int, name: str, text: str, voice: str) -> dict:
    if voice not in GEMINI_VOICES:
        raise JobError(f"call {i}: voice must be one of the 30 Gemini voices")
    body: dict = {"prompt": text, "voice": voice}
    if model == GEMINI:
        body["output_format"] = "mp3"
    style = c.get("style_instructions", "")
    if not isinstance(style, str) or len(style) > MAX_STYLE or any(ord(ch) < 32 and ch != "\n" for ch in style):
        raise JobError(f"call {i}: style_instructions must be text of at most {MAX_STYLE} characters")
    if style.strip():
        body["style_instructions"] = style.strip()
    if "language_code" in c:
        if not isinstance(c["language_code"], str) or c["language_code"] not in GEMINI_LANGS:
            raise JobError(f"call {i}: language_code must be one of {sorted(GEMINI_LANGS)}")
        body["language_code"] = GEMINI_LANGS[c["language_code"]]
    if "temperature" in c:
        t = c["temperature"]
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= 2:
            raise JobError(f"call {i}: temperature must be a number from 0 to 2")
        body["temperature"] = float(t)
    return {"name": name, "body": body, "chars": len(text) + len(body.get("style_instructions", ""))}


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
    key = os.environ.get(KEY_NAME)
    if key:
        return key
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tools import infisical_setup as inf
        org = inf.Org(inf.self_host())
        secret = inf._get_secret(org, inf._project(org, KEY_PROJECT)["id"], KEY_ENV, KEY_NAME, KEY_PATH)
    except (Exception, SystemExit) as e:  # _project() exits when the project is missing
        print(f"no key: Infisical lookup failed ({e.__class__.__name__})", file=sys.stderr)
        return None
    return (secret or {}).get("secretValue") or None


def http_json(url: str, key: str, body: dict | None = None) -> dict:
    if not url.startswith(QUEUE):
        raise FalError(0, "refusing to send the key off queue.fal.run")
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as f:
            return json.loads(f.read())
    except urllib.error.HTTPError as e:
        raise FalError(e.code, e.read()[:300].decode(errors="replace")) from None


def download(url: str, dest: Path) -> None:
    """The audio file, fetched with no key, written whole or not at all."""
    if not url.startswith("https://"):
        raise FalError(0, "the audio URL is not https")
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=120) as f:
        tmp.write_bytes(f.read())
    tmp.replace(dest)


def audio_ext(audio: object) -> str:
    if not isinstance(audio, dict):
        raise ValueError("fal's answer holds no audio file")
    ext = AUDIO_EXT.get(str(audio.get("content_type") or "").split(";")[0].strip().lower())
    if ext:
        return ext
    suffix = urllib.parse.urlsplit(str(audio.get("url") or "")).path.rpartition(".")[2].lower()
    return suffix if suffix in AUDIO_EXTS else "mp3"


def one_call(model: str, key: str, body: dict) -> tuple[str | None, dict]:
    sub = http_json(QUEUE + model, key, body)
    for _ in range(POLL_N):
        if http_json(sub["status_url"], key).get("status") == "COMPLETED":
            break
        time.sleep(POLL_S)
    else:
        raise FalError(0, f"not COMPLETED after {POLL_S * POLL_N} s, request {sub.get('request_id')}")
    return sub.get("request_id"), http_json(sub["response_url"], key)


def cap_number(s: str) -> float:
    if not CAP_RE.fullmatch(s):
        raise argparse.ArgumentTypeError("a plain number such as 0.07")
    return float(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    ap.add_argument("--job", required=True, help="the job file, an absolute path under /opt/MoonieXHQ/Work/")
    ap.add_argument("--max-usd", required=True, type=cap_number, help="never spend more than this, in USD")
    ap.add_argument("--dry-run", action="store_true", help="price the job; call nothing, write nothing")
    a = ap.parse_args(argv)
    try:
        job_path = under_work(a.job, "--job")
        job = load_job(job_path)
    except JobError as e:
        print(f"bad job: {e}", file=sys.stderr)
        return EXIT_BAD
    model, price, out_dir = job["model"], job["price"], job["out_dir"]
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
    print(f"{model}: {len(job['calls'])} calls, ${price * 1000:g} per 1,000 characters; "
          f"ledger ${spent:.4f}; cap ${a.max_usd:g}", flush=True)
    key = None
    if not a.dry_run:
        key = fetch_key()
        if not key:
            return EXIT_KEY
    redact = (lambda s: s.replace(key, "<redacted>")) if key else (lambda s: s)
    saved = skipped = fails = server_errors = 0
    try:
        for c in job["calls"]:
            name = c["name"]
            have = [p for p in (out_dir / f"{name}.{x}" for x in AUDIO_EXTS) if p.exists()]
            if have:
                skipped += 1
                print(f"skip {name}: {have[0].name} exists", flush=True)
                continue
            body = c["body"]
            while True:
                cost = c["chars"] * price
                if spent + cost > a.max_usd + 1e-12:
                    print(f"STOP before {name}: ${spent + cost:.4f} would pass the cap ${a.max_usd:g}", flush=True)
                    return EXIT_CAP
                spent += cost
                if a.dry_run:
                    print(f"dry run: {name} {c['chars']} chars ${cost:.4f}, total ${spent:.4f}", flush=True)
                    break
                write_row(lf, {"what": "attempt", "name": name, "model": model, "chars": c["chars"],
                               "usd": round(cost, 6), "voice": body["voice"],
                               "timestamps": bool(body.get("timestamps"))})
                try:
                    rid, res = one_call(model, key, body)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
                    audio = out_dir / f"{name}.{audio_ext(res.get('audio'))}"
                    download(res["audio"]["url"], audio)
                except FalError as e:
                    write_row(lf, {"what": "result", "name": name, "ok": False, "code": e.code})
                    print(f"FAIL {name}: {redact(str(e))}", flush=True)
                    if e.code == 422 and body.get("timestamps"):
                        print(f"{name}: refused as invalid, once more without timestamps", flush=True)
                        body = {k: v for k, v in body.items() if k != "timestamps"}
                        continue
                    fails += 1
                    if e.code in (401, 403):
                        print("the key or the account was refused; stopping the job", flush=True)
                        return EXIT_FAIL
                    server_errors = server_errors + 1 if e.code >= 500 else 0
                    if server_errors >= MAX_SERVER_ERRORS:
                        print(f"{server_errors} server errors in a row: the model looks down; stopping the job",
                              flush=True)
                        return EXIT_FAIL
                    break
                except (OSError, ValueError, KeyError, TypeError) as e:
                    write_row(lf, {"what": "result", "name": name, "ok": False, "code": e.__class__.__name__})
                    print(f"FAIL {name}: {e.__class__.__name__}: {redact(str(e))[:200]}", flush=True)
                    fails += 1
                    server_errors = 0
                    break
                write_row(lf, {"what": "result", "name": name, "ok": True, "request_id": rid})
                saved += 1
                server_errors = 0
                print(f"saved {audio.name}: {c['chars']} chars ${cost:.4f}, request {rid}", flush=True)
                break
    finally:
        print(f"done: {saved} saved, {skipped} skipped, {fails} failed; job ${spent:.4f} of cap "
              f"${a.max_usd:g}{' (dry run)' if a.dry_run else ''}; ledger {led}", flush=True)
        if lf:
            lf.close()
    return EXIT_FAIL if fails else 0


if __name__ == "__main__":
    sys.exit(main())
