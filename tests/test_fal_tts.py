"""tools/fal_tts.py: the cap holds across calls, retries and reruns; nothing reaches fal or Infisical."""
import ast
import fcntl
import json
import sys
from pathlib import Path

import pytest

from tools import fal_tts

KEY = "fal-test-key-not-real-0123456789"
PRICE = fal_tts.PRICES["elevenlabs/tts/eleven-v4"]


class FakeFal:
    """Stands in for queue.fal.run and the file host; records every URL the key was sent to."""

    def __init__(self, fail=None):
        self.fail = fail or (lambda body: None)
        self.submits = []
        self.keyed_urls = []
        self.downloads = []

    def http_json(self, url, key, body=None):
        assert key == KEY
        self.keyed_urls.append(url)
        if body is not None:
            self.submits.append(dict(body))
            code = self.fail(body)
            if code:
                raise fal_tts.FalError(code, f"refused, echoing {key}")
            return {"request_id": f"r{len(self.submits)}", "status_url": fal_tts.QUEUE + "x/status",
                    "response_url": fal_tts.QUEUE + "x"}
        if url.endswith("/status"):
            return {"status": "COMPLETED"}
        return {"audio": {"url": "https://v3.fal.media/files/a.mp3"}, "timestamps": []}

    def download(self, url, dest):
        self.downloads.append(url)
        dest.write_bytes(b"ID3")


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_tts, "WORK", tmp_path)
    monkeypatch.setattr(fal_tts, "fetch_key", lambda: KEY)
    return tmp_path


@pytest.fixture
def fal(monkeypatch):
    fake = FakeFal()
    monkeypatch.setattr(fal_tts, "http_json", fake.http_json)
    monkeypatch.setattr(fal_tts, "download", fake.download)
    return fake


def make_job(work, n=3, chars=100, timestamps=False, **extra):
    calls = []
    for i in range(1, n + 1):
        t = work / f"line{i}.txt"
        t.write_text(str(i) + "ก" * (chars - 1), encoding="utf-8")
        calls.append({"name": f"t{i}", "text_file": str(t), "voice": "Brian", "stability": 0.5,
                      "language_code": "th", "seed": 7, "timestamps": timestamps})
    job = {"model": "elevenlabs/tts/eleven-v4", "out_dir": str(work / "takes"), "calls": calls, **extra}
    p = work / "job.json"
    p.write_text(json.dumps(job), encoding="utf-8")
    return p


def attempts(work):
    led = work / "job.ledger.jsonl"
    rows = [json.loads(line) for line in led.read_text().splitlines()] if led.exists() else []
    return [r for r in rows if r["what"] == "attempt"]


def test_stops_before_the_call_that_would_pass_the_cap(work, fal):
    job = make_job(work, n=3, chars=100)  # $0.008 a call
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.02"]) == fal_tts.EXIT_CAP
    assert len(fal.submits) == 2 and len(attempts(work)) == 2
    assert sorted(p.name for p in (work / "takes").glob("*.mp3")) == ["t1.mp3", "t2.mp3"]


def test_reruns_share_the_cap_through_the_ledger(work, fal):
    job = make_job(work, n=3, chars=100)
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.02"]) == fal_tts.EXIT_CAP
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.02"]) == fal_tts.EXIT_CAP
    assert len(fal.submits) == 2, "the second run must not spend: two calls are already in the ledger"
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.03"]) == 0
    assert len(fal.submits) == 3


def test_an_existing_take_is_skipped_and_costs_nothing(work, fal):
    job = make_job(work, n=2, chars=100)
    (work / "takes").mkdir()
    (work / "takes" / "t1.mp3").write_bytes(b"ID3")
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.008"]) == 0
    assert [s["text"][:1] for s in fal.submits] == ["2"] and len(attempts(work)) == 1


def test_422_with_timestamps_retries_once_without_and_both_count(work, fal):
    fal.fail = lambda body: 422 if body.get("timestamps") else None
    job = make_job(work, n=1, chars=100, timestamps=True)
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.02"]) == 0
    assert [("timestamps" in s) for s in fal.submits] == [True, False]
    assert len(attempts(work)) == 2


def test_the_retry_is_capped_too(work, fal):
    fal.fail = lambda body: 422 if body.get("timestamps") else None
    job = make_job(work, n=1, chars=100, timestamps=True)
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.01"]) == fal_tts.EXIT_CAP
    assert len(fal.submits) == 1


def test_a_refused_key_stops_the_whole_job(work, fal):
    fal.fail = lambda body: 403
    job = make_job(work, n=3, chars=100)
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_FAIL
    assert len(fal.submits) == 1 and len(attempts(work)) == 1


def test_the_key_is_never_printed(work, fal, capsys):
    fal.fail = lambda body: 500
    job = make_job(work, n=1, chars=100)
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_FAIL
    out = capsys.readouterr()
    assert KEY not in out.out + out.err and "<redacted>" in out.out
    assert KEY not in (work / "job.ledger.jsonl").read_text()


def test_the_key_goes_only_to_the_queue(work, fal):
    job = make_job(work, n=2, chars=100)
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == 0
    assert fal.keyed_urls and all(u.startswith(fal_tts.QUEUE) for u in fal.keyed_urls)
    assert fal.downloads == ["https://v3.fal.media/files/a.mp3"] * 2


def test_http_json_refuses_a_foreign_url_before_any_request():
    with pytest.raises(fal_tts.FalError) as e:
        fal_tts.http_json("https://example.com/status", KEY)
    assert "refusing" in str(e.value)


def test_dry_run_calls_nothing_and_writes_nothing(work, fal, monkeypatch):
    monkeypatch.setattr(fal_tts, "fetch_key", lambda: pytest.fail("a dry run must not fetch the key"))
    job = make_job(work, n=3, chars=100)
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.03", "--dry-run"]) == 0
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.02", "--dry-run"]) == fal_tts.EXIT_CAP
    assert not fal.submits and not (work / "job.ledger.jsonl").exists() and not (work / "takes").exists()


@pytest.mark.parametrize("args", [["--max", "1"], ["--max-u", "1"], ["--max-usd", "1e3"],
                                  ["--max-usd", "nan"], ["--max-usd", "-1"], ["--max-usd", "1 "],
                                  ["--max-usd", "1\n"]])
def test_only_the_exact_cap_flag_with_a_plain_number(work, fal, args):
    job = make_job(work, n=1)
    with pytest.raises(SystemExit) as e:
        fal_tts.main(["--job", str(job), *args])
    assert e.value.code == 2 and not fal.submits


def test_paths_must_stay_under_work(work, fal, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "x.txt").write_text("hello", encoding="utf-8")
    job = make_job(work, n=1)
    data = json.loads(job.read_text())
    for field, value in (("text_file", str(outside / "x.txt")), ("text_file", "relative.txt")):
        data["calls"][0][field] = value
        job.write_text(json.dumps(data))
        assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    link = work / "link.txt"
    link.symlink_to(outside / "x.txt")
    data["calls"][0]["text_file"] = str(link)
    job.write_text(json.dumps(data))
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    data["calls"][0]["text_file"] = str(work / "line1.txt")
    data["out_dir"] = str(outside)
    job.write_text(json.dumps(data))
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    assert not fal.submits


@pytest.mark.parametrize("change", [
    {"model": "fal-ai/some-other-model"},
    {"model": []},
    {"calls": []},
    {"extra": 1},
])
def test_a_bad_job_spends_nothing(work, fal, change):
    job = make_job(work, n=1)
    data = {**json.loads(job.read_text()), **change}
    job.write_text(json.dumps(data))
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    assert not fal.submits


@pytest.mark.parametrize("call_change", [
    {"voice": "Brian; rm -rf /"}, {"stability": 2}, {"stability": True}, {"seed": -1},
    {"language_code": "thai"}, {"timestamps": "yes"}, {"name": "../x"}, {"url": "x"},
    {"name": "t1\n"}, {"voice": "Brian\n"}, {"language_code": "th\n"},
])
def test_a_bad_call_spends_nothing(work, fal, call_change):
    job = make_job(work, n=1)
    data = json.loads(job.read_text())
    data["calls"][0].update(call_change)
    job.write_text(json.dumps(data))
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    assert not fal.submits


def test_an_unreadable_ledger_row_refuses_instead_of_reading_zero(work, fal):
    job = make_job(work, n=1)
    (work / "job.ledger.jsonl").write_text('{"what": "attempt", "usd": "lots"}\n')
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    assert not fal.submits


def test_a_second_run_is_refused_while_one_holds_the_ledger(work, fal):
    job = make_job(work, n=1)
    with open(work / "job.ledger.jsonl", "a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    assert not fal.submits


def test_no_key_spends_nothing(work, fal, monkeypatch):
    monkeypatch.setattr(fal_tts, "fetch_key", lambda: None)
    job = make_job(work, n=1)
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_KEY
    assert not fal.submits and not attempts(work)


def test_standard_library_only():
    """A script card runs the file with the system python3, so neither it nor what it imports may need the venv."""
    root = Path(fal_tts.__file__).resolve().parent.parent
    for rel in ("tools/fal_tts.py", "tools/infisical_setup.py"):
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        assert mods - set(sys.stdlib_module_names) - {"tools", "__future__"} == set(), rel


GEMINI_PRICE = fal_tts.PRICES[fal_tts.GEMINI]
STYLE = "A Thai storyteller in his fifties, deep and warm, unhurried."


def make_gemini_job(work, n=1, chars=100, **call):
    calls = []
    for i in range(1, n + 1):
        t = work / f"g{i}.txt"
        t.write_text(str(i) + "ก" * (chars - 1), encoding="utf-8")
        calls.append({"name": f"g{i}", "text_file": str(t), "voice": "Charon", "style_instructions": STYLE,
                      "language_code": "th", "temperature": 1.0, **call})
    p = work / "job.json"
    p.write_text(json.dumps({"model": fal_tts.GEMINI, "out_dir": str(work / "takes"), "calls": calls}),
                 encoding="utf-8")
    return p


def test_gemini_sends_its_own_fields_and_prices_the_voice_block_too(work, fal):
    job = make_gemini_job(work, n=1, chars=100)
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == 0
    assert fal.submits == [{"prompt": "1" + "ก" * 99, "voice": "Charon", "output_format": "mp3",
                            "style_instructions": STYLE, "language_code": "Thai (Thailand)", "temperature": 1.0}]
    assert attempts(work)[0]["usd"] == round((100 + len(STYLE)) * GEMINI_PRICE, 6)
    assert (work / "takes" / "g1.mp3").exists()


def test_gemini_cap_counts_the_voice_block(work, fal):
    job = make_gemini_job(work, n=2, chars=100)  # (100 + 61) chars a call, $0.00805 each
    assert fal_tts.main(["--job", str(job), "--max-usd", "0.01"]) == fal_tts.EXIT_CAP
    assert len(fal.submits) == 1


@pytest.mark.parametrize("call_change", [
    {"voice": "Brian"}, {"voice": "charon"}, {"stability": 0.5}, {"seed": 7}, {"timestamps": True},
    {"language_code": "Thai (Thailand)"}, {"language_code": "xx"}, {"temperature": 3}, {"temperature": True},
    {"style_instructions": "x" * (fal_tts.MAX_STYLE + 1)}, {"style_instructions": "line\rbreak"},
    {"style_instructions": 7}, {"language_code": ["th"]}, {"language_code": {}},
])
def test_a_bad_gemini_call_spends_nothing(work, fal, call_change):
    job = make_gemini_job(work, n=1, **call_change)
    assert fal_tts.main(["--job", str(job), "--max-usd", "1"]) == fal_tts.EXIT_BAD
    assert not fal.submits
