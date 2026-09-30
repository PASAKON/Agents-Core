"""Tests for scripts/champa/champa_fire.py.

Offline unit tests using a fake adapter class.
Validates:
- dry-run makes zero submit clicks and writes no ledger
- --fire --max-jobs 3 on 5 clips makes exactly 3 clicks
- a priced label makes zero clicks and returns 3 or 4
- Unlimited switch off returns 4 with zero clicks
- a clip already in the ledger is skipped
- harvest downloads only done clips and records done
- the page that was already open is never closed
- a balance drop stops the run with exit 3
- missing textbox returns 4
- settings mismatch returns 4
- --wait timeout returns 5 when jobs still running
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.champa import champa_fire as cf


class FakeComposerPage:
    """Fake adapter implementing ComposerPage interface for offline testing."""

    def __init__(
        self,
        label_before_typing: str | None = "ส่งเข้าคิว",
        label_after_typing: str | None = "ส่งเข้าคิว Unlimited 0",
        settings: dict[str, str] | None = None,
        has_textbox_val: bool = True,
        unlimited_switch_val: str | None = "true",
        balance_val: str = "1,350",
        balance_sequence: list[str] | None = None,
        finished_urls: dict[str, str] | None = None,
        opened_by_script: bool = False,
    ):
        self.label_before_typing = label_before_typing
        self.label_after_typing = label_after_typing
        self.current_prompt = ""
        self.settings = (
            dict(settings)
            if settings is not None
            else {
                "model": "Seedance 2.0",
                "ratio": "16:9",
                "duration": "4s",
                "resolution": "720p",
            }
        )
        self.has_textbox_val = has_textbox_val
        self.unlimited_switch_val = unlimited_switch_val
        self.balance_val = balance_val
        self.balance_sequence = list(balance_sequence) if balance_sequence else None
        self.finished_urls = dict(finished_urls) if finished_urls else {}
        self.opened_by_script = opened_by_script

        self.submit_clicks = 0
        self.filled_prompts: list[str] = []
        self.cleared_prompts_count = 0
        self.applied_settings: list[tuple[str | None, str | None]] = []
        self.downloaded: list[tuple[str, Path]] = []
        self.page_closed = False

    def has_textbox(self) -> bool:
        return self.has_textbox_val

    def fill_prompt(self, text: str) -> None:
        self.filled_prompts.append(text)
        self.current_prompt = text

    def clear_prompt(self) -> None:
        self.cleared_prompts_count += 1
        self.current_prompt = ""

    def read_label(self) -> str | None:
        if not self.current_prompt:
            return self.label_before_typing
        return self.label_after_typing

    def read_unlimited_switch(self) -> str | None:
        return self.unlimited_switch_val

    def read_balance(self) -> str | None:
        if self.balance_sequence:
            if len(self.balance_sequence) > 1:
                return self.balance_sequence.pop(0)
            return self.balance_sequence[0]
        return self.balance_val

    def read_settings(self) -> dict[str, str]:
        return dict(self.settings)

    def apply_settings(
        self,
        model: str | None = None,
        resolution: str | None = None,
    ) -> None:
        self.applied_settings.append((model, resolution))
        if model:
            self.settings["model"] = model
        if resolution:
            self.settings["resolution"] = resolution

    def click_submit(self) -> None:
        self.submit_clicks += 1

    def find_finished_job(self, prompt: str) -> str | None:
        # Check by full prompt or first 60 characters
        if prompt in self.finished_urls:
            return self.finished_urls[prompt]
        prefix = prompt[:60].strip()
        for k, v in self.finished_urls.items():
            if k[:60].strip() == prefix:
                return v
        return None

    def download(self, url: str, path: Path) -> int:
        self.downloaded.append((url, path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_mp4_bytes")
        return len(b"fake_mp4_bytes")

    def close(self) -> None:
        if self.opened_by_script:
            self.page_closed = True


@pytest.fixture(autouse=True)
def fast_timeouts(monkeypatch):
    """Speed up poll timeouts in tests."""
    monkeypatch.setattr(cf, "WAIT_LABEL_TIMEOUT_S", 0.05)
    monkeypatch.setattr(cf, "WAIT_LABEL_POLL_S", 0.01)
    monkeypatch.setattr(cf, "HARVEST_POLL_INTERVAL_S", 0.01)


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


@pytest.fixture
def prompts_5_clips(tmp_path) -> Path:
    p = tmp_path / "prompts_5.csv"
    p.write_text(
        "clip_id,prompt\n"
        "c1,Prompt for clip 1\n"
        "c2,Prompt for clip 2\n"
        "c3,Prompt for clip 3\n"
        "c4,Prompt for clip 4\n"
        "c5,Prompt for clip 5\n",
        encoding="utf-8",
    )
    return p


def test_dry_run_makes_zero_submit_clicks_and_writes_no_ledger(
    tmp_path, prompts_3_clips, capsys
):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage()

    ret = cf.main(
        ["--prompts", str(prompts_3_clips), "--out", str(out_dir)],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 0
    assert fake.filled_prompts == [
        "Prompt for clip 1",
        "Prompt for clip 2",
        "Prompt for clip 3",
    ]
    assert fake.cleared_prompts_count == 3
    assert not (out_dir / "queue.jsonl").exists()

    captured = capsys.readouterr()
    assert "DRY clip_id=c1 free=yes label=ส่งเข้าคิว Unlimited 0 settings=ok" in captured.out
    assert "DRY clip_id=c2 free=yes label=ส่งเข้าคิว Unlimited 0 settings=ok" in captured.out
    assert "DRY clip_id=c3 free=yes label=ส่งเข้าคิว Unlimited 0 settings=ok" in captured.out


def test_fire_max_jobs_3_on_5_clips_makes_exactly_3_clicks(tmp_path, prompts_5_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage()

    ret = cf.main(
        [
            "--prompts",
            str(prompts_5_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 3
    assert fake.filled_prompts == [
        "Prompt for clip 1",
        "Prompt for clip 2",
        "Prompt for clip 3",
    ]

    ledger = out_dir / "queue.jsonl"
    assert ledger.exists()
    rows = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 3
    assert [r["clip_id"] for r in rows] == ["c1", "c2", "c3"]
    assert all(r["event"] == "submit" for r in rows)


def test_priced_label_makes_zero_clicks_and_returns_3_or_4(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(label_after_typing="ส่งเข้าคิว 120")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret in (3, 4)
    assert fake.submit_clicks == 0
    ledger = out_dir / "queue.jsonl"
    assert not ledger.exists() or len(ledger.read_text(encoding="utf-8").strip()) == 0


def test_unlimited_switch_off_returns_4_with_zero_clicks(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(unlimited_switch_val="false")

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret == 4
    assert fake.submit_clicks == 0


def test_clip_already_in_ledger_is_skipped(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    ledger = out_dir / "queue.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    # Pre-seed clip c1 in ledger
    ledger.write_text(
        json.dumps({
            "event": "submit",
            "clip_id": "c1",
            "label": "ส่งเข้าคิว Unlimited 0",
            "ts": "2026-10-01T00:00:00+00:00",
        })
        + "\n",
        encoding="utf-8",
    )

    fake = FakeComposerPage()
    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 2
    assert "Prompt for clip 1" not in fake.filled_prompts
    assert fake.filled_prompts == ["Prompt for clip 2", "Prompt for clip 3"]

    rows = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["clip_id"] for r in rows] == ["c1", "c2", "c3"]


def test_harvest_downloads_only_done_clips_and_records_done(
    tmp_path, prompts_3_clips
):
    out_dir = tmp_path / "out"
    ledger = out_dir / "queue.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)

    # Pre-seed c1, c2, c3 as submitted
    entries = [
        {
            "event": "submit",
            "clip_id": "c1",
            "label": "ส่งเข้าคิว Unlimited 0",
            "ts": "2026-10-01T00:00:00+00:00",
        },
        {
            "event": "submit",
            "clip_id": "c2",
            "label": "ส่งเข้าคิว Unlimited 0",
            "ts": "2026-10-01T00:00:01+00:00",
        },
        {
            "event": "submit",
            "clip_id": "c3",
            "label": "ส่งเข้าคิว Unlimited 0",
            "ts": "2026-10-01T00:00:02+00:00",
        },
    ]
    ledger.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
    )

    # c1 and c3 are done, c2 is still in progress
    fake = FakeComposerPage(
        finished_urls={
            "Prompt for clip 1": "https://champa.io/videos/c1.mp4",
            "Prompt for clip 3": "https://champa.io/videos/c3.mp4",
        }
    )

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--harvest",
        ],
        adapter=fake,
    )

    assert ret == 0
    assert fake.submit_clicks == 0
    assert (out_dir / "c1.mp4").exists()
    assert (out_dir / "c3.mp4").exists()
    assert not (out_dir / "c2.mp4").exists()

    rows = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    done_ids = [r["clip_id"] for r in rows if r["event"] == "done"]
    assert done_ids == ["c1", "c3"]


def test_the_page_that_was_already_open_is_never_closed(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(opened_by_script=False)

    ret = cf.main(
        ["--prompts", str(prompts_3_clips), "--out", str(out_dir)],
        adapter=fake,
    )

    assert ret == 0
    assert fake.page_closed is False

    # Conversely, a page opened by script IS closed on cleanup
    fake_opened = FakeComposerPage(opened_by_script=True)
    cf.cleanup_cdp(fake_opened, None)
    assert fake_opened.page_closed is True


def test_balance_drop_stops_the_run_with_exit_3(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    # Balance sequence: initial read "1,350", then "1,340" after first submit
    fake = FakeComposerPage(
        balance_sequence=["1,350", "1,340"]
    )

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret == 3
    assert fake.submit_clicks == 1


def test_settings_mismatch_returns_4(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    # Duration cannot be changed by page menu (fixed 4s); if page has 5s, it returns 4
    fake = FakeComposerPage(
        settings={
            "model": "Seedance 2.0",
            "ratio": "16:9",
            "duration": "5s",
            "resolution": "720p",
        }
    )

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret == 4
    assert fake.submit_clicks == 0


def test_missing_textbox_returns_4(tmp_path, prompts_3_clips):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(has_textbox_val=False)

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "3",
        ],
        adapter=fake,
    )

    assert ret == 4
    assert fake.submit_clicks == 0


def test_wait_timeout_returns_5_when_jobs_still_running(
    tmp_path, prompts_3_clips
):
    out_dir = tmp_path / "out"
    fake = FakeComposerPage(finished_urls={})  # Nothing finishes

    ret = cf.main(
        [
            "--prompts",
            str(prompts_3_clips),
            "--out",
            str(out_dir),
            "--fire",
            "--max-jobs",
            "1",
            "--wait",
            "--wait-max-min",
            "0.0001",
        ],
        adapter=fake,
    )

    assert ret == 5
    assert fake.submit_clicks == 1
