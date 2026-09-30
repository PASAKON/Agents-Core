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


_UNSET = object()


class FakeComposerPage:
    """Fake adapter implementing ComposerPage interface for offline testing."""

    def __init__(
        self,
        label: object = _UNSET,
        label_before_typing: str | None = None,
        label_after_typing: str | None = None,
        label_delay_polls: int = 0,
        settings: dict[str, str] | None = None,
        has_textbox: bool = True,
        poll_result: dict | None = None,
        newest_ts_val: str = "20260101_000000",
        opened_by_script: bool = False,
    ):
        if label is not _UNSET:
            self.label = label
            self.label_before_typing = label
            self.label_after_typing = label
        elif label_before_typing is not None or label_after_typing is not None:
            self.label = label_before_typing
            self.label_before_typing = label_before_typing
            self.label_after_typing = label_after_typing
        else:
            self.label = "Generate"
            self.label_before_typing = "Generate"
            self.label_after_typing = "Generate 80 60"

        self.label_delay_polls = label_delay_polls
        self._polls_since_typing = 0
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
        if not self.typed_prompts:
            return self.label_before_typing
        if (
            self.label_delay_polls > 0
            and self._polls_since_typing < self.label_delay_polls
        ):
            self._polls_since_typing += 1
            return self.label_before_typing
        return self.label_after_typing

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
        self._polls_since_typing = 0
        if self.label_delay_polls == 0:
            self.label = self.label_after_typing

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


@pytest.fixture(autouse=True)
def fast_wait_price(monkeypatch):
    monkeypatch.setattr(cf, "WAIT_PRICE_TIMEOUT_S", 0.05)
    monkeypatch.setattr(cf, "WAIT_PRICE_POLL_S", 0.01)


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


def test_dry_run_types_but_makes_zero_submit_clicks(tmp_path, prompts_3_clips, capsys):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(
        label_before_typing="Generate",
        label_after_typing="Generate 80 60",
    )

    # Fake label returns "Generate" before typing
    assert fake.read_label() == "Generate"

    ret = cf.main(
        ["--prompts", str(prompts_3_clips), "--out", str(out_dir)],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 0
    assert fake.typed_prompts == [
        "Prompt for clip 1",
        "Prompt for clip 2",
        "Prompt for clip 3",
    ]
    assert not (out_dir / "spend.jsonl").exists()
    assert fake.read_label() == "Generate 80 60"

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
    assert fake.typed_prompts == [
        "Prompt for clip 1",
        "Prompt for clip 2",
        "Prompt for clip 3",
    ]
    assert not (out_dir / "spend.jsonl").exists()

    captured = capsys.readouterr()
    assert "DRY clip_id=c1 price=60 would_fire=yes reason=ok" in captured.out
    assert "DRY clip_id=c2 price=60 would_fire=yes reason=ok" in captured.out
    assert "DRY clip_id=c3 price=60 would_fire=no" in captured.out
    assert "budget 120" in captured.out


def test_label_never_gets_price_dry_run_reports_unreadable_and_fire_returns_4(
    tmp_path, prompts_3_clips, capsys
):
    # Dry-run path: prints would_fire=no reason=unreadable label
    out_dir_dry = tmp_path / "out_dry"
    fake_dry = FakeComposerPage(label="Generate")

    ret_dry = cf.main(
        ["--prompts", str(prompts_3_clips), "--out", str(out_dir_dry)],
        adapter=fake_dry,
    )

    assert ret_dry == 0
    assert fake_dry.submit_clicks == 0
    assert len(fake_dry.typed_prompts) == 3
    assert not (out_dir_dry / "spend.jsonl").exists()

    captured_dry = capsys.readouterr()
    assert (
        "DRY clip_id=c1 price=None would_fire=no reason=unreadable label"
        in captured_dry.out
    )
    assert (
        "DRY clip_id=c2 price=None would_fire=no reason=unreadable label"
        in captured_dry.out
    )
    assert (
        "DRY clip_id=c3 price=None would_fire=no reason=unreadable label"
        in captured_dry.out
    )

    # Fire path: returns 4 with zero clicks
    out_dir_fire = tmp_path / "out_fire"
    fake_fire = FakeComposerPage(label="Generate")

    ret_fire = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir_fire),
            "--fire",
            "--max-per-clip",
            "60",
            "--budget",
            "200",
        ],
        adapter=fake_fire,
    )

    assert ret_fire == 4
    assert fake_fire.submit_clicks == 0
    assert len(fake_fire.typed_prompts) == 1
    assert not (out_dir_fire / "spend.jsonl").exists()


def test_wait_for_price_polls_until_label_updates(tmp_path, capsys):
    p = tmp_path / "prompts_1.csv"
    p.write_text("clip_id,c1_prompt\nc1,Prompt 1\n", encoding="utf-8")
    # CSV must have clip_id,prompt
    p.write_text("clip_id,prompt\nc1,Prompt 1\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(
        label_before_typing="Generate",
        label_after_typing="Generate 80 60",
        label_delay_polls=2,
    )

    ret = cf.main(
        ["--prompts", str(p), "--out", str(out_dir)],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 0
    captured = capsys.readouterr()
    assert "DRY clip_id=c1 price=60" in captured.out


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
