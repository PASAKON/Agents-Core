"""tools/fal_lipsync.py: priced per second of input audio before sending; stops at cap; no network."""
import ast
import fcntl
import http.client
import io
import json
import struct
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

import pytest

from tools import fal_lipsync

KEY = "fal-test-key-not-real-0123456789"


def write_mp3(path: Path, seconds: float = 6.0, id3: bool = False) -> Path:
    """Write MPEG-1 Layer III 128 kbps 48 kHz mono frames (384 bytes and 0.024 s per frame)."""
    frames = round(seconds / 0.024)
    header = bytes([0xFF, 0xFB, 0x94, 0xC0])
    frame = header + b"\x00" * (384 - 4)
    prefix = b"ID3\x03\x00\x00\x00\x00\x00\x04test" if id3 else b""
    path.write_bytes(prefix + frame * frames)
    return path


def write_wav(path: Path, seconds: float = 4.0, rate: int = 8000) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * round(seconds * rate))
    return path


class FakeFal:
    """Stands in for queue.fal.run and fal storage; records every URL the key was sent to."""

    def __init__(self, fail=None):
        self.fail = fail or (lambda body: None)
        self.submits = []
        self.keyed_urls = []
        self.uploads = []
        self.downloads = []

    def http_json(self, url, key, body=None):
        assert key == KEY
        self.keyed_urls.append(url)
        if body is not None:
            self.submits.append(dict(body))
            code = self.fail(body)
            if code:
                raise fal_lipsync.FalError(code, f"refused, echoing {key}")
            return {"request_id": f"r{len(self.submits)}", "status_url": fal_lipsync.QUEUE + "x/status",
                    "response_url": fal_lipsync.QUEUE + "x"}
        if url.endswith("/status"):
            return {"status": "COMPLETED"}
        return {"video": {"url": "https://v3.fal.media/files/out.mp4", "content_type": "video/mp4"}}

    def upload(self, path, key):
        assert key == KEY
        self.uploads.append(path)
        return f"https://v3.fal.media/files/{path.name}"

    def download(self, url, dest):
        self.downloads.append(url)
        dest.write_bytes(b"\x00\x00\x00\x18ftypmp42")


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_lipsync, "WORK", tmp_path)
    monkeypatch.setattr(fal_lipsync, "fetch_key", lambda: KEY)
    return tmp_path


@pytest.fixture
def fal(monkeypatch):
    fake = FakeFal()
    monkeypatch.setattr(fal_lipsync, "http_json", fake.http_json)
    monkeypatch.setattr(fal_lipsync, "upload", fake.upload)
    monkeypatch.setattr(fal_lipsync, "download", fake.download)
    return fake


def make_job(work, n=3, seconds=6.0, model=fal_lipsync.V1, wav=False, **extra):
    video = work / "avatar.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    calls = []
    for i in range(1, n + 1):
        a = work / f"part{i}.{'wav' if wav else 'mp3'}"
        (write_wav if wav else write_mp3)(a, seconds=seconds)
        calls.append({"name": f"p{i}", "audio_file": str(a), "sync_mode": "cut_off"})
    job = {"model": model, "reference_video": str(video), "out_dir": str(work / "parts"),
           "calls": calls, **extra}
    p = work / "job.json"
    p.write_text(json.dumps(job), encoding="utf-8")
    return p


def attempts(work):
    led = work / "job.ledger.jsonl"
    rows = [json.loads(line) for line in led.read_text().splitlines()] if led.exists() else []
    return [r for r in rows if r["what"] == "attempt"]


def test_v1_prices_per_second_of_input_audio_and_stops_before_cap(work, fal):
    # 6.0 s * $0.0117/s = $0.0702 per call; 2 calls = $0.1404; 3 calls = $0.2106 > $0.15
    job = make_job(work, n=3, seconds=6.0, model=fal_lipsync.V1)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.15"]) == fal_lipsync.EXIT_CAP
    assert len(fal.submits) == 2 and len(attempts(work)) == 2
    assert attempts(work)[0]["usd"] == round(6.0 * 0.0117, 6)
    assert fal.uploads == [work / "avatar.mp4", work / "part1.mp3", work / "part2.mp3"]
    assert sorted(p.name for p in (work / "parts").glob("*.mp4")) == ["p1.mp4", "p2.mp4"]


def test_lipsync2_prices_at_five_cents_per_second_and_sends_model_to_queue(work, fal):
    # 4.0 s WAV * $0.05/s = $0.20 per call
    job = make_job(work, n=2, seconds=4.0, model=fal_lipsync.V2, wav=True)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.25"]) == fal_lipsync.EXIT_CAP
    assert len(fal.submits) == 1
    assert fal.submits[0] == {"model": "lipsync-2", "sync_mode": "cut_off",
                              "video_url": "https://v3.fal.media/files/avatar.mp4",
                              "audio_url": "https://v3.fal.media/files/part1.wav"}
    assert fal.keyed_urls[0] == fal_lipsync.QUEUE + "fal-ai/sync-lipsync"
    assert attempts(work)[0]["usd"] == 0.2


def test_reruns_share_the_cap_through_the_ledger(work, fal):
    job = make_job(work, n=3, seconds=6.0, model=fal_lipsync.V1)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.15"]) == fal_lipsync.EXIT_CAP
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.15"]) == fal_lipsync.EXIT_CAP
    assert len(fal.submits) == 2
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.22"]) == 0
    assert len(fal.submits) == 3


def test_an_existing_part_is_skipped_and_costs_nothing(work, fal):
    job = make_job(work, n=2, seconds=6.0)
    (work / "parts").mkdir()
    (work / "parts" / "p1.mp4").write_bytes(b"mp4")
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.08"]) == 0
    assert len(fal.submits) == 1 and fal.submits[0]["audio_url"].endswith("part2.mp3")
    assert len(attempts(work)) == 1


def test_two_server_errors_in_a_row_stop_the_job(work, fal, capsys):
    fal.fail = lambda body: 500
    job = make_job(work, n=4, seconds=6.0)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_FAIL
    assert len(fal.submits) == 2 and len(attempts(work)) == 2
    assert "2 server errors in a row" in capsys.readouterr().out


def test_a_good_call_between_server_errors_keeps_the_job_going(work, fal):
    fal.fail = lambda body: 500 if body["audio_url"].endswith(("part1.mp3", "part3.mp3")) else None
    job = make_job(work, n=4, seconds=6.0)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_FAIL
    assert len(fal.submits) == 4
    assert sorted(p.name for p in (work / "parts").glob("*.mp4")) == ["p2.mp4", "p4.mp4"]


def test_a_refused_key_stops_the_whole_job_and_redacts_key(work, fal, capsys):
    fal.fail = lambda body: 403
    job = make_job(work, n=3, seconds=6.0)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_FAIL
    out = capsys.readouterr()
    assert len(fal.submits) == 1 and KEY not in out.out + out.err and "<redacted>" in out.out
    assert KEY not in (work / "job.ledger.jsonl").read_text()


def test_dry_run_calls_nothing_and_writes_nothing(work, fal, monkeypatch):
    monkeypatch.setattr(fal_lipsync, "fetch_key", lambda: pytest.fail("a dry run must not fetch the key"))
    job = make_job(work, n=3, seconds=6.0)
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.22", "--dry-run"]) == 0
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "0.15", "--dry-run"]) == fal_lipsync.EXIT_CAP
    assert not fal.uploads and not fal.submits and not (work / "job.ledger.jsonl").exists()


@pytest.mark.parametrize("args", [["--max", "1"], ["--max-u", "1"], ["--max-usd", "1e3"],
                                  ["--max-usd", "nan"], ["--max-usd", "-1"], ["--max-usd", "1 "],
                                  ["--max-usd", "1\n"], ["--max-usd", "1", "--max-usd", "2"]])
def test_only_the_exact_cap_flag_with_a_plain_number(work, fal, args):
    job = make_job(work, n=1)
    with pytest.raises(SystemExit) as e:
        fal_lipsync.main(["--job", str(job), *args])
    assert e.value.code == 2 and not fal.submits


def test_paths_must_stay_under_work(work, fal, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    write_mp3(outside / "a.mp3", 2.4)
    (outside / "v.mp4").write_bytes(b"mp4")
    job = make_job(work, n=1)
    data = json.loads(job.read_text())
    for patch in (
        {"reference_video": str(outside / "v.mp4")},
        {"reference_video": "relative.mp4"},
        {"out_dir": str(outside)},
    ):
        bad = {**data, **patch}
        job.write_text(json.dumps(bad))
        assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_BAD
    link = work / "link.mp3"
    link.symlink_to(outside / "a.mp3")
    data["calls"][0]["audio_file"] = str(link)
    job.write_text(json.dumps(data))
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_BAD
    assert not fal.uploads and not fal.submits


@pytest.mark.parametrize("change", [
    {"model": "fal-ai/other"}, {"model": []}, {"calls": []}, {"extra": 1},
    {"video_file": "/opt/MoonieXHQ/Work/both.mp4"},
])
def test_a_bad_job_spends_nothing(work, fal, change):
    job = make_job(work, n=1)
    data = {**json.loads(job.read_text()), **change}
    job.write_text(json.dumps(data))
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_BAD
    assert not fal.uploads and not fal.submits


@pytest.mark.parametrize("call_change", [
    {"sync_mode": "invalid"}, {"sync_mode": 1}, {"name": "../x"}, {"name": "p1\n"}, {"extra": 1},
])
def test_a_bad_call_spends_nothing(work, fal, call_change):
    job = make_job(work, n=1)
    data = json.loads(job.read_text())
    data["calls"][0].update(call_change)
    job.write_text(json.dumps(data))
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_BAD
    assert not fal.uploads and not fal.submits


def test_mp3_with_id3_and_xing_header_and_float_wav_durations(tmp_path):
    mp3 = write_mp3(tmp_path / "tagged.mp3", seconds=2.4, id3=True)
    assert fal_lipsync.audio_seconds(mp3) == pytest.approx(2.4)

    # Xing VBR header frame with 250 total frames (250 * 0.024 = 6.0 s)
    header = bytes([0xFF, 0xFB, 0x94, 0xC0])
    xing = header + b"\x00" * 17 + b"Xing" + struct.pack(">II", 1, 250)
    xing += b"\x00" * (384 - len(xing))
    vbr = tmp_path / "vbr.mp3"
    vbr.write_bytes(xing + (header + b"\x00" * 380))
    assert fal_lipsync.audio_seconds(vbr) == pytest.approx(6.0)

    # IEEE float WAV (format 3, rejected by stdlib wave module, parsed by RIFF fallback)
    fmt = struct.pack("<HHIIHH", 3, 1, 8000, 32000, 4, 32)
    pcm = b"\x00" * 96000  # 3.0 s at 32000 bytes/s
    riff = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack("<I", len(pcm)) + pcm
    fwav = tmp_path / "float.wav"
    fwav.write_bytes(riff)
    assert fal_lipsync.audio_seconds(fwav) == pytest.approx(3.0)

    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"not audio")
    with pytest.raises(fal_lipsync.JobError):
        fal_lipsync.audio_seconds(bad)


def test_an_unreadable_ledger_or_locked_ledger_refuses(work, fal):
    job = make_job(work, n=1)
    with open(work / "job.ledger.jsonl", "a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_BAD
    (work / "job.ledger.jsonl").write_text('{"what": "attempt", "usd": "bad"}\n')
    assert fal_lipsync.main(["--job", str(job), "--max-usd", "1"]) == fal_lipsync.EXIT_BAD
    assert not fal.submits


class FakeAnswer:
    def __init__(self, raw, length=-1):
        self.raw = raw
        self.headers = {} if length is None else {"Content-Length": str(len(raw) if length == -1 else length)}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self.raw if n < 0 else self.raw[:n]


def test_upload_and_http_json_keep_key_and_media_on_fal_only(tmp_path, monkeypatch):
    with pytest.raises(fal_lipsync.FalError):
        fal_lipsync.http_json("https://evil.example/status", KEY)

    vid = tmp_path / "avatar.mp4"
    vid.write_bytes(b"mp4-bytes")
    seen = []

    def fake_open(req, timeout):
        seen.append(req)
        if req.full_url == fal_lipsync.UPLOAD_URL:
            return FakeAnswer(json.dumps({"upload_url": "https://v3.fal.media/upload/avatar.mp4",
                                          "file_url": "https://v3.fal.media/files/avatar.mp4"}).encode())
        return FakeAnswer(b"")

    monkeypatch.setattr(fal_lipsync, "_queue_open", fake_open)
    assert fal_lipsync.upload(vid, KEY) == "https://v3.fal.media/files/avatar.mp4"
    assert seen[0].get_header("Authorization") == f"Key {KEY}"
    assert not seen[1].has_header("Authorization") and seen[1].get_method() == "PUT"

    monkeypatch.setattr(fal_lipsync, "_queue_open", lambda req, timeout: FakeAnswer(
        json.dumps({"upload_url": "https://evil.example/up", "file_url": "https://v3.fal.media/f"}).encode()))
    with pytest.raises(fal_lipsync.FalError):
        fal_lipsync.upload(vid, KEY)


def test_standard_library_only():
    root = Path(fal_lipsync.__file__).resolve().parent.parent
    for rel in ("tools/fal_lipsync.py", "tools/infisical_setup.py"):
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        assert mods - set(sys.stdlib_module_names) - {"tools", "__future__"} == set(), rel
