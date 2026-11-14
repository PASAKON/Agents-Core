"""Offline image-runner acceptance tests: no browser, network or credits."""
import json
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts.champa import champa_image as ci


class FakePage:
    def __init__(self, balances=None, label="สร้าง ⚡2", finished=None, crash=False):
        self.balances = iter(balances or [1026, 1024, 1024, 1022, 1022, 1020])
        self.label = label
        self.finished = finished or {}
        self.crash = crash
        self.clicks = 0
        self.fills = []
        self.settings = []
        self.closed = False

    def configure(self, settings):
        self.settings.append(settings)

    def has_textbox(self):
        return True

    def fill_prompt(self, prompt):
        self.fills.append(prompt)

    def clear_prompt(self):
        pass

    def read_balance(self):
        value = next(self.balances)
        return None if value is None else str(value)

    def read_label(self):
        return self.label

    def click_submit(self):
        self.clicks += 1
        if self.crash:
            raise RuntimeError("ambiguous click result")

    def find_finished_job(self, prompt):
        return self.finished.get(prompt)

    def download(self, url, path):
        if url == "invalid":
            path.write_bytes(b"<html>not an image</html>")
        else:
            Image.new("RGB", (3, 2)).save(path, format=url)

    def close(self):
        self.closed = True


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    def forbidden(*args):
        pytest.fail("real CDP connection attempted")
    monkeypatch.setattr(ci, "connect_over_cdp", forbidden)
    prompts = tmp_path / "prompts.json"
    prompts.write_text(json.dumps([
        {"name": f"r5-{i}", "prompt": f"Design {i}"} for i in range(3)
    ]))
    return ["--prompts", str(prompts), "--out", str(tmp_path / "out")]


def test_dry_run_is_offline_and_spends_nothing(inputs, tmp_path, capsys):
    page = FakePage()
    assert ci.main(inputs, adapter=page) == 0
    assert not page.fills and not page.settings and page.clicks == 0
    assert not (tmp_path / "out" / "image_queue.jsonl").exists()
    assert "Total credits: 6" in capsys.readouterr().out
    assert ci.main(inputs) == 0


@pytest.mark.parametrize("extra", [[], ["--max-credits", "nan"], ["--max-credits", "-1"], ["--max-cred", "2"]])
def test_fire_requires_valid_full_cap_before_connect(inputs, extra):
    assert ci.main(inputs + ["--fire"] + extra) == 2


def test_cap_stops_before_extra_submit(inputs):
    page = FakePage()
    assert ci.main(inputs + ["--fire", "--max-credits", "3"], adapter=page) == 3
    assert page.clicks == 1
    assert page.settings == [{"model": "Nano Banana 2", "ratio": "16:9", "resolution": "1K"}]
    assert page.closed


def test_zero_cap_never_fills(inputs):
    page = FakePage()
    assert ci.main(inputs + ["--fire", "--max-credits", "0"], adapter=page) == 3
    assert page.clicks == 0 and not page.fills


def test_expected_price_override(inputs):
    page = FakePage(label="สร้าง ⚡4", balances=[1026, 1022])
    assert ci.main(inputs + ["--fire", "--max-credits", "4", "--expected-credits", "4"], adapter=page) == 3
    assert page.clicks == 1


def test_concurrent_runner_refused_before_connection(inputs, tmp_path):
    with ci.ledger_lock(tmp_path / "out"):
        assert ci.main(inputs + ["--fire", "--max-credits", "6"]) == 3


def test_windows_ledger_lock_and_refusal(inputs, tmp_path, monkeypatch):
    held = set()
    events = []

    def locking(fd, mode, nbytes):
        assert nbytes == 1
        events.append(mode)
        if mode == fake_msvcrt.LK_NBLCK:
            if held:
                raise OSError("locked")
            held.add(fd)
        elif mode == fake_msvcrt.LK_UNLCK:
            held.remove(fd)

    fake_msvcrt = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=locking)
    monkeypatch.setattr(ci, "fcntl", None)
    monkeypatch.setattr(ci, "msvcrt", fake_msvcrt)

    with ci.ledger_lock(tmp_path / "out"):
        assert ci.main(inputs + ["--fire", "--max-credits", "6"]) == 3
    assert events == [2, 2, 0]
    assert not held

    page = FakePage()
    assert ci.main(inputs + ["--fire", "--max-credits", "6"], adapter=page) == 0
    assert page.clicks == 3
    assert events == [2, 2, 0, 2, 0]
    assert not held


def test_unreadable_balance_prevents_submit(inputs):
    page = FakePage(balances=[None])
    assert ci.main(inputs + ["--fire", "--max-credits", "6"], adapter=page) == 4
    assert page.clicks == 0


@pytest.mark.parametrize("balances", [[1026, 1023], [1026, None], [1026, 1024, 1024, 1021]])
def test_balance_drop_stops(inputs, balances):
    page = FakePage(balances=balances)
    assert ci.main(inputs + ["--fire", "--max-credits", "6"], adapter=page) == 3
    assert page.clicks == len(balances) // 2


def test_resume_skips_done_and_submitted(inputs, tmp_path):
    guard = ci.ImageGuard(8, tmp_path / "out" / "image_queue.jsonl")
    guard.record_done("r5-0", "handmade.png")
    guard.record_submit("r5-1", "สร้าง ⚡2")
    page = FakePage()
    assert ci.main(inputs + ["--fire", "--max-credits", "2"], adapter=page) == 0
    assert page.fills == ["Design 2"]


def test_uncertain_click_is_never_retried(inputs):
    first = FakePage(crash=True)
    assert ci.main(inputs + ["--fire", "--max-credits", "6"], adapter=first) == 4
    second = FakePage()
    assert ci.main(inputs + ["--fire", "--max-credits", "4"], adapter=second) == 0
    assert second.fills == ["Design 1", "Design 2"]


@pytest.mark.parametrize("names", [["../bad"], ["a.png"], [""], ["a b"], ["a", "a"], [123]])
def test_bad_names_rejected_before_connect(inputs, names):
    from pathlib import Path
    Path(inputs[1]).write_text(json.dumps([{"name": n, "prompt": "design"} for n in names]))
    assert ci.main(inputs) == 2


@pytest.mark.parametrize("label", [None, "สร้าง", "สร้าง ⚡20", "สร้าง ⚡2.5", "สร้าง 12 ลด 2", "ส่งเข้าคิว Unlimited 0"])
def test_wrong_price_refused(inputs, label):
    page = FakePage(label=label)
    assert ci.main(inputs + ["--fire", "--max-credits", "6"], adapter=page) == 3
    assert page.clicks == 0


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
def test_harvest_manual_history_without_submitting(inputs, tmp_path, format):
    page = FakePage(finished={"Design 0": format})
    assert ci.main(inputs + ["--harvest"], adapter=page) == 0
    assert page.clicks == 0 and not page.fills and not page.settings
    with Image.open(tmp_path / "out" / "r5-0.png") as image:
        assert image.format == "PNG"
        image.verify()
    guard = ci.ImageGuard(8, tmp_path / "out" / "image_queue.jsonl")
    assert guard.done_ids() == {"r5-0"}


def test_invalid_download_is_not_done(inputs, tmp_path):
    page = FakePage(finished={"Design 0": "invalid"})
    assert ci.main(inputs + ["--harvest"], adapter=page) == 4
    assert not list((tmp_path / "out").glob("*.png"))
    assert not ci.ImageGuard(8, tmp_path / "out" / "image_queue.jsonl").done_ids()


def test_corrupt_ledger_fails_closed(inputs, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "image_queue.jsonl").write_text('{"event":')
    assert ci.main(inputs + ["--fire", "--max-credits", "6"]) == 4


@pytest.mark.parametrize("existing,fail_navigation", [(True, False), (False, False), (False, True)])
def test_fake_cdp_cleanup(existing, fail_navigation, monkeypatch, capsys):
    class Tab:
        url = "https://champa.io/private"
        closed = False
        def goto(self, url):
            if fail_navigation:
                raise RuntimeError("navigation failed")
        def close(self):
            self.closed = True
    tab = Tab()
    context = SimpleNamespace(pages=[tab] if existing else [], new_page=lambda: tab)
    browser = SimpleNamespace(contexts=[context])
    stopped = []
    pw = SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=lambda _: browser), stop=lambda: stopped.append(True))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", SimpleNamespace(sync_playwright=lambda: SimpleNamespace(start=lambda: pw)))
    if fail_navigation:
        with pytest.raises(RuntimeError):
            ci.connect_over_cdp("fake")
    else:
        adapter, resources = ci.connect_over_cdp("fake")
        ci.video.cleanup_cdp(adapter, resources)
    assert tab.closed is (not existing)
    assert stopped == [True]
    assert "https://" not in capsys.readouterr().out
