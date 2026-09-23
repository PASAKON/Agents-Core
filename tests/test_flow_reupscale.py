from pathlib import Path

import pytest

from tools import flow_reupscale


def _shot(number: int) -> dict:
    return {"shot": number, "dur_s": 6, "prompt": 'says: "unique"'}


def test_select_targets_requires_verified_720_source(tmp_path, monkeypatch):
    source = tmp_path / "shot-35.mp4"
    source.write_bytes(b"old")
    monkeypatch.setattr(flow_reupscale.flow_ledger, "parse_sheet",
                        lambda _path: [_shot(35)])
    monkeypatch.setattr(flow_reupscale.flow_ledger, "load_ledger",
                        lambda _path: {35: {"status": "verified",
                                            "file": str(source),
                                            "prompt_sha": "abc"}})
    monkeypatch.setattr(flow_reupscale, "probe_video_dimensions",
                        lambda _path: (720, 1280))

    result = flow_reupscale.select_targets(
        Path("sheet.md"), Path("ledger.tsv"), "35", 5)
    assert result[0]["shot"]["shot"] == 35
    assert result[0]["source"] == source


def test_select_targets_enforces_batch_safety_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(flow_reupscale.flow_ledger, "parse_sheet",
                        lambda _path: [])
    monkeypatch.setattr(flow_reupscale.flow_ledger, "load_ledger",
                        lambda _path: {})
    with pytest.raises(RuntimeError, match="safety limit"):
        flow_reupscale.select_targets(
            Path("sheet.md"), Path("ledger.tsv"), "35-40", 5)


def test_completed_entry_requires_file_resolution_and_checksum(tmp_path,
                                                                monkeypatch):
    output = tmp_path / "shot-35.mp4"
    output.write_bytes(b"upscaled")
    monkeypatch.setattr(flow_reupscale, "probe_video_dimensions",
                        lambda _path: (1080, 1920))
    digest = flow_reupscale.sha256_file(output)
    assert flow_reupscale.valid_completed_entry({
        "status": "verified",
        "output_file": str(output),
        "output_sha256": digest,
    })
    assert not flow_reupscale.valid_completed_entry({
        "status": "verified",
        "output_file": str(output),
        "output_sha256": "wrong",
    })
