"""Spend guard/pricing tests; every fal boundary is replaced with a fake."""
import json
import struct

import pytest

from tools import fal_image as fi


def png(path, w, h):
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", w, h) + b"\0" * 8)
    return path


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(fi, "WORK", tmp_path)
    return tmp_path


@pytest.mark.parametrize("w,h,price", [(1024,1024,.27),(1536,1536,.27),(1537,1024,.54),(2048,2048,.54)])
def test_layerize_pricing_uses_image_area_tier(tmp_path, w, h, price):
    assert fi.price_layerize(png(tmp_path / "in.png", w, h), 8) == pytest.approx(price)


@pytest.mark.parametrize("size,quality,refs,expected", [
    ("1920x1072","low",1,.01641), ("1920x1072","medium",2,.03351),
    ("1920x1072","high",1,.05145), ("1024x1024","low",1,.01788),
    ("1024x1024","medium",1,.02517), ("1024x1024","high",3,.08868)])
def test_edit_prices(size, quality, refs, expected):
    assert fi.price_edit(size, quality, refs) == pytest.approx(expected)


@pytest.mark.parametrize("quality", ["auto", "xhigh", "max"])
def test_edit_forbids_unpriced_quality(quality):
    with pytest.raises(fi.JobError): fi.price_edit("1024x1024", quality, 1)


def test_cap_refusal_happens_before_key_upload_or_ledger_attempt(work, monkeypatch, capsys):
    image = png(work / "in.png", 1024, 1024)
    monkeypatch.setattr(fi, "fetch_key", lambda: pytest.fail("cap refusal must precede key lookup"))
    monkeypatch.setattr(fi, "upload", lambda *x: pytest.fail("cap refusal must precede upload"))
    args = ["--job", "paperclip", "--max-usd", "0.26", "--out", str(work / "out"), "--fire",
            "layerize", "--image", str(image), "--prompt", "layers"]
    assert fi.main(args) == fi.EXIT_CAP
    assert "spend cap reached: spent 0 of 0.26" in capsys.readouterr().out
    ledger = work / "paperclip.ledger.jsonl"
    assert ledger.read_text() == ""


def test_dry_run_default_sends_nothing_and_writes_no_attempt(work, monkeypatch, capsys):
    image = png(work / "in.png", 1024, 1024)
    monkeypatch.setattr(fi, "fetch_key", lambda: pytest.fail("dry-run must not read key"))
    monkeypatch.setattr(fi, "upload", lambda *x: pytest.fail("dry-run must not upload"))
    args = ["--job", "paperclip", "--max-usd", "1", "--out", str(work / "out"),
            "layerize", "--image", str(image), "--prompt", "layers"]
    assert fi.main(args) == 0
    assert "dry run: no upload" in capsys.readouterr().out
    assert not (work / "paperclip.ledger.jsonl").read_text()


@pytest.mark.parametrize("quality", ["auto", "xhigh", "max"])
def test_cli_refuses_unpriced_quality_before_api(work, monkeypatch, capsys, quality):
    ref = png(work / "ref.png", 32, 32)
    monkeypatch.setattr(fi, "fetch_key", lambda: pytest.fail("invalid request must not read key"))
    assert fi.main(["--job", "edit", "--max-usd", "1", "--out", str(work / "out"), "edit",
                    "--prompt", "edit", "--ref", str(ref), "--quality", quality, "--size", "1024x1024"]) == 2
