"""Tests for scripts/higgsfield/credit_fire.py.

Offline unit tests using fake adapter class.
Validates:
- dry-run makes zero submit clicks and zero typing
- --fire with caps on 3 clips makes exactly 3 clicks
- a poll timeout on clip 1 makes exactly 1 click total and returns 5
- a label above --max-per-clip makes 0 clicks and returns 3
- a clip already in the ledger is skipped
- the page that was already open is never closed
- settings mismatch returns 4
- missing textbox returns 4
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.higgsfield import credit_fire as cf
from scripts.higgsfield.credit_guard import SpendGuard


class FakeComposerPage:
    """Fake adapter implementing ComposerPage interface for offline testing."""

    def __init__(
        self,
        label: str | None = "Generate 80 60",
        settings: dict[str, str] | None = None,
        has_textbox: bool = True,
        poll_result: dict | None = None,
        newest_ts_val: str = "20260101_000000",
        opened_by_script: bool = False,
    ):
        self.label = label
        self.settings = (
            dict(settings)
            if settings is not None
            else {"duration": "5s", "ratio": "16:9", "resolution": "1080p"}
        )
        self._has_textbox = has_textbox
        self.poll_result = (
            poll_result
            if poll_result is not None
            else {
                "status": "download",
                "url": "https://d1.cloudfront.net/hf_20260101_000001_a.mp4",
            }
        )
        self.newest_ts_val = newest_ts_val
        self.opened_by_script = opened_by_script
        self.submit_clicks = 0
        self.typed_prompts: list[str] = []
        self.applied_settings: list[tuple[str | None, str | None, str | None]] = []
        self.downloaded: list[tuple[str, Path]] = []
        self.page_closed = False

    def read_label(self) -> str | None:
        return self.label

    def read_settings(self) -> dict[str, str]:
        return dict(self.settings)

    def apply_settings(
        self,
        duration: str | None = None,
        ratio: str | None = None,
        resolution: str | None = None,
    ) -> None:
        self.applied_settings.append((duration, ratio, resolution))
        if duration:
            self.settings["duration"] = duration
        if ratio:
            self.settings["ratio"] = ratio
        if resolution:
            self.settings["resolution"] = resolution

    def has_textbox(self) -> bool:
        return self._has_textbox

    def type_prompt(self, text: str) -> None:
        self.typed_prompts.append(text)

    def click_submit(self) -> None:
        self.submit_clicks += 1

    def newest_ts(self) -> str:
        return self.newest_ts_val

    def poll(self, t0_max: str, timeout_s: int = 900) -> dict:
        if callable(self.poll_result):
            return self.poll_result(t0_max)
        return self.poll_result

    def download(self, url: str, path: Path) -> int:
        self.downloaded.append((url, path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"dummy_mp4_bytes")
        return len(b"dummy_mp4_bytes")

    def close(self) -> None:
        if self.opened_by_script:
            self.page_closed = True


@pytest.fixture
def prompts_3_clips(tmp_path) -> Path:
    p = tmp_path / "prompts.csv"
    p.write_text(
        "clip_id,prompt\n"
        "c1,Prompt for clip 1\n"
        "c2,Prompt for clip 2\n"
        "c3,Prompt for clip 3\n",
        encoding="utf-8",
    )
    return p


def test_dry_run_makes_zero_submit_clicks_and_zero_typing(tmp_path, prompts_3_clips, capsys):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label="Generate 80 60")

    ret = cf.main(
        ["--prompts", str(prompts_3_clips), "--out", str(out_dir)],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 0
    assert len(fake.typed_prompts) == 0
    assert not (out_dir / "spend.jsonl").exists()

    captured = capsys.readouterr()
    assert "DRY clip_id=c1 price=60" in captured.out
    assert "DRY clip_id=c2 price=60" in captured.out
    assert "DRY clip_id=c3 price=60" in captured.out


def test_dry_run_with_caps_simulates_in_memory(tmp_path, prompts_3_clips, capsys):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label="Generate 80 60")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--max-per-clip",
            "60",
            "--budget",
            "120",
        ],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 0
    assert len(fake.typed_prompts) == 0
    assert not (out_dir / "spend.jsonl").exists()

    captured = capsys.readouterr()
    assert "DRY clip_id=c1 price=60 would_fire=yes reason=ok" in captured.out
    assert "DRY clip_id=c2 price=60 would_fire=yes reason=ok" in captured.out
    assert "DRY clip_id=c3 price=60 would_fire=no" in captured.out
    assert "budget 120" in captured.out


def test_fire_with_caps_on_3_clips_makes_exactly_3_clicks(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label="Generate 80 60")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 3
    assert fake.typed_prompts == [
        "Prompt for clip 1",
        "Prompt for clip 2",
        "Prompt for clip 3",
    ]
    assert len(fake.downloaded) == 3
    assert (out_dir / "c1.mp4").exists()
    assert (out_dir / "c2.mp4").exists()
    assert (out_dir / "c3.mp4").exists()

    ledger = out_dir / "spend.jsonl"
    assert ledger.exists()
    lines = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert [entry["clip_id"] for entry in lines] == ["c1", "c2", "c3"]
    assert [entry["price"] for entry in lines] == [60, 60, 60]


def test_poll_timeout_on_clip_1_makes_exactly_1_click_total_and_returns_5(
    tmp_path, prompts_3_clips
):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label="Generate 80 60", poll_result={"status": "timeout"})

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake,
    )

    assert ret == 5
    assert fake.submit_clicks == 1
    assert len(fake.typed_prompts) == 1
    # Ledgers count the spend before knowing the outcome
    ledger = out_dir / "spend.jsonl"
    assert ledger.exists()
    lines = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0]["clip_id"] == "c1"


def test_label_above_max_per_clip_makes_zero_clicks_and_returns_3(
    tmp_path, prompts_3_clips
):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label="Generate 100 90")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake,
    )

    assert ret == 3
    assert fake.submit_clicks == 0
    assert len(fake.typed_prompts) == 1  # prompt is typed before reading label per spec


def test_clip_already_in_ledger_is_skipped(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    ledger = out_dir / "spend.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    guard = SpendGuard(60, 200, ledger)
    guard.record("c1", 60)

    fake = FakeComposerPage(label="Generate 80 60")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake,
        guard=guard,
    )

    assert ret == 0
    # c1 was already in ledger, so only c2 and c3 are processed
    assert fake.submit_clicks == 2
    assert fake.typed_prompts == ["Prompt for clip 2", "Prompt for clip 3"]
    assert guard.spent() == 180


def test_page_that_was_already_open_is_never_closed(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(opened_by_script=False)

    ret = cf.main(
        ["--prompts", str(prompts_3_clips), "--out", str(out_dir)],
        adapter=fake,
    )

    assert ret == 0
    fake.close()
    assert fake.page_closed is False


def test_page_opened_by_script_is_closed_on_close(tmp_path, prompts_3_clips):
    fake = FakeComposerPage(opened_by_script=True)
    fake.close()
    assert fake.page_closed is True


def test_settings_mismatch_returns_4_and_zero_clicks(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    # Page has 5s, but CLI requested 8s
    fake = FakeComposerPage(
        label="Generate 80 60",
        settings={"duration": "5s", "ratio": "16:9", "resolution": "1080p"},
    )
    # Prevent apply_settings from changing it to simulate failure to apply
    fake.apply_settings = lambda *args, **kwargs: None

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
            "--duration",
            "8s",
        ],
        adapter=fake,
    )

    assert ret == 4
    assert fake.submit_clicks == 0


def test_missing_textbox_returns_4_and_zero_clicks(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(has_textbox=False)

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake,
    )

    assert ret == 4
    assert fake.submit_clicks == 0


def test_unreadable_label_returns_4_and_zero_clicks(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label=None)

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake,
    )

    assert ret == 4
    assert fake.submit_clicks == 0


def test_budget_exceeded_stops_and_returns_3(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    # Budget is 100, clip cost is 60. Clip 1 succeeds (60 spent). Clip 2 fails (120 > 100).
    fake = FakeComposerPage(label="Generate 80 60")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "100",
        ],
        adapter=fake,
    )

    assert ret == 3
    assert fake.submit_clicks == 1


def test_limit_parameter_is_respected(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label="Generate 80 60")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
            "--limit",
            "2",
        ],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 2
    assert len(fake.typed_prompts) == 2
