"""Tests for quota snapshot history recorder (tools/quota.py --record).

Covers:
- two providers -> returns 2, file has 2 lines, each line parses as JSON with exactly 8 fields
- now=datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc) -> ts == "2026-09-29T10:00:00+00:00"
- a naive datetime(2026, 9, 29, 10, 0, 0) gives the same ts
- a Quota with error="boom" and fractions None -> line has "weekly_remaining": null and "error": "boom"
- calling twice appends (4 lines), never truncates
- a path in a directory that does not exist yet is created
- ensure_ascii=False: a source string "ทดสอบ" is written as-is
- DEFAULT_HISTORY constant and CLI --record option
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import DEFAULT_HISTORY, Quota, record_snapshot

EXPECTED_FIELDS = {
    "ts",
    "provider",
    "weekly_remaining",
    "daily_remaining",
    "weekly_resets_at",
    "daily_resets_at",
    "source",
    "error",
}


def test_four_buckets(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    quotas = {
        "claude": Quota(
            provider="claude",
            weekly_remaining=0.5,
            daily_remaining=0.8,
            weekly_resets_at="2026-10-06T00:00:00+00:00",
            daily_resets_at="2026-09-30T00:00:00+00:00",
            source="vps",
            error=None,
        ),
        "codex": Quota(
            provider="codex",
            weekly_remaining=0.7,
            daily_remaining=0.9,
            weekly_resets_at="2026-10-05T00:00:00+00:00",
            source="session",
            error=None,
        ),
        "agy-gemini": Quota(
            provider="agy-gemini",
            weekly_remaining=1.0,
            daily_remaining=0.75,
            weekly_resets_at="2026-10-06T00:05:38Z",
            daily_resets_at="2026-09-29T12:00:00Z",
            source="cli",
            error=None,
        ),
        "agy-claude": Quota(
            provider="agy-claude",
            weekly_remaining=0.95,
            daily_remaining=0.85,
            weekly_resets_at="2026-10-06T00:05:38Z",
            daily_resets_at="2026-09-29T12:00:00Z",
            source="cli",
            error=None,
        ),
    }
    ret = record_snapshot(quotas, path)
    assert ret == 4

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4

    for line in lines:
        entry = json.loads(line)
        assert set(entry.keys()) == EXPECTED_FIELDS

    entry0 = json.loads(lines[0])
    entry1 = json.loads(lines[1])
    entry2 = json.loads(lines[2])
    entry3 = json.loads(lines[3])
    assert entry0["provider"] == "claude"
    assert entry0["weekly_remaining"] == 0.5
    assert entry0["daily_remaining"] == 0.8
    assert entry1["provider"] == "codex"
    assert entry1["weekly_remaining"] == 0.7
    assert entry2["provider"] == "agy-gemini"
    assert entry2["weekly_remaining"] == 1.0
    assert entry3["provider"] == "agy-claude"
    assert entry3["weekly_remaining"] == 0.95


def test_now_utc(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    now = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    quotas = {"claude": Quota(provider="claude")}
    record_snapshot(quotas, path, now=now)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["ts"] == "2026-09-29T10:00:00+00:00"


def test_now_naive(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    now = datetime(2026, 9, 29, 10, 0, 0)
    quotas = {"claude": Quota(provider="claude")}
    record_snapshot(quotas, path, now=now)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["ts"] == "2026-09-29T10:00:00+00:00"


def test_error_and_null_fractions(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    quotas = {
        "claude": Quota(
            provider="claude",
            weekly_remaining=None,
            daily_remaining=None,
            error="boom",
        )
    }
    record_snapshot(quotas, path)

    raw_text = path.read_text(encoding="utf-8")
    assert '"weekly_remaining": null' in raw_text
    assert '"error": "boom"' in raw_text

    entry = json.loads(raw_text.strip())
    assert entry["weekly_remaining"] is None
    assert entry["error"] == "boom"


def test_calling_twice_appends(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    quotas = {
        "claude": Quota(provider="claude"),
        "agy-gemini": Quota(provider="agy-gemini"),
    }
    first_ret = record_snapshot(quotas, path)
    assert first_ret == 2
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2

    second_ret = record_snapshot(quotas, path)
    assert second_ret == 2
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4


def test_create_missing_directory(tmp_path: Path):
    nested_dir = tmp_path / "non_existent_dir" / "sub"
    path = nested_dir / "quota-history.jsonl"
    assert not nested_dir.exists()

    quotas = {"claude": Quota(provider="claude")}
    ret = record_snapshot(quotas, path)
    assert ret == 1
    assert nested_dir.exists()
    assert path.exists()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_ensure_ascii_false_utf8(tmp_path: Path):
    path = tmp_path / "history.jsonl"
    quotas = {"claude": Quota(provider="claude", source="ทดสอบ")}
    record_snapshot(quotas, path)

    raw_text = path.read_text(encoding="utf-8")
    assert "ทดสอบ" in raw_text
    assert "\\u" not in raw_text


def test_default_history_constant():
    assert DEFAULT_HISTORY.name == "quota-history.jsonl"
    assert DEFAULT_HISTORY.parent.name == "reports"
    assert DEFAULT_HISTORY.parent.parent.name == "state"


def test_main_record_flag(tmp_path: Path, monkeypatch, capsys):
    from tools import quota as quota_mod

    history_file = tmp_path / "custom-history.jsonl"
    fake_quotas = {
        "claude": Quota(provider="claude", weekly_remaining=0.5, daily_remaining=0.8),
        "codex": Quota(provider="codex", weekly_remaining=0.7, daily_remaining=0.9),
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=1.0, daily_remaining=0.75),
        "agy-claude": Quota(provider="agy-claude", weekly_remaining=0.95, daily_remaining=0.85),
    }

    monkeypatch.setattr(quota_mod, "load_plans", lambda path=None: {})
    monkeypatch.setattr(quota_mod, "fetch_all_quotas", lambda cfg, now=None: fake_quotas)
    monkeypatch.setattr(sys, "argv", ["quota.py", "--record", str(history_file)])

    quota_mod.main()

    captured = capsys.readouterr()
    assert f"recorded 4 lines -> {history_file}" in captured.err
    assert history_file.exists()
    assert len(history_file.read_text(encoding="utf-8").splitlines()) == 4


def test_main_record_default_history(monkeypatch, capsys):
    from tools import quota as quota_mod

    fake_quotas = {
        "claude": Quota(provider="claude", weekly_remaining=0.5, daily_remaining=0.8),
        "codex": Quota(provider="codex", weekly_remaining=0.7, daily_remaining=0.9),
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=1.0, daily_remaining=0.75),
        "agy-claude": Quota(provider="agy-claude", weekly_remaining=0.95, daily_remaining=0.85),
    }
    recorded_calls = []

    def fake_record(quotas, path, now=None):
        recorded_calls.append((quotas, path))
        return len(quotas)

    monkeypatch.setattr(quota_mod, "load_plans", lambda path=None: {})
    monkeypatch.setattr(quota_mod, "fetch_all_quotas", lambda cfg, now=None: fake_quotas)
    monkeypatch.setattr(quota_mod, "record_snapshot", fake_record)
    monkeypatch.setattr(sys, "argv", ["quota.py", "--record"])

    quota_mod.main()

    captured = capsys.readouterr()
    assert f"recorded 4 lines -> {quota_mod.DEFAULT_HISTORY}" in captured.err
    assert len(recorded_calls) == 1
    assert recorded_calls[0][1] == str(quota_mod.DEFAULT_HISTORY)
