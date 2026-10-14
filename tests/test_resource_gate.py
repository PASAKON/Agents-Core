"""lib/resource_gate.py: the spawn gate of org restructure P2 (plan §7.3)."""
from __future__ import annotations

import json
from collections import namedtuple

import pytest

from lib import resource_gate as rg

_Statvfs = namedtuple("_Statvfs", "f_blocks f_bfree f_bavail f_frsize")


def _meminfo(tmp_path, available_kb):
    p = tmp_path / "meminfo"
    p.write_text(f"MemTotal:        8131584 kB\nMemFree:          172032 kB\n"
                 f"MemAvailable:    {available_kb} kB\nBuffers:           1024 kB\n")
    return p


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("ORG_SPAWN_GATE", "ORG_SPAWN_RAM_FLOOR_MB", "ORG_SPAWN_DISK_MAX_PCT"):
        monkeypatch.delenv(k, raising=False)


def _disk(monkeypatch, used_pct):
    # 1000 blocks; df's Use% = used / (used + avail); no reserved blocks here
    used = int(used_pct * 10)
    monkeypatch.setattr(rg.os, "statvfs", lambda path: _Statvfs(1000, 1000 - used, 1000 - used, 4096))


def test_gate_off_reads_nothing_and_passes(monkeypatch, tmp_path):
    def boom(path):
        raise AssertionError("the gate is off; it must not read the disk")
    monkeypatch.setattr(rg.os, "statvfs", boom)
    assert rg.check(meminfo=tmp_path / "nope") is None


def test_low_ram_refuses(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    _disk(monkeypatch, 50)
    why = rg.check(meminfo=_meminfo(tmp_path, 700 * 1024))
    assert why and "RAM available 700 MB" in why and "800 MB" in why


def test_full_disk_refuses(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    _disk(monkeypatch, 91)
    why = rg.check(meminfo=_meminfo(tmp_path, 3000 * 1024))
    assert why and "disk 91% used" in why and "90%" in why


def test_both_reasons_are_named(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    _disk(monkeypatch, 95)
    why = rg.check(meminfo=_meminfo(tmp_path, 100 * 1024))
    assert "RAM" in why and "disk" in why


def test_at_the_limits_it_passes(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    _disk(monkeypatch, 90)
    assert rg.check(meminfo=_meminfo(tmp_path, 800 * 1024)) is None


def test_limits_come_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    monkeypatch.setenv("ORG_SPAWN_RAM_FLOOR_MB", "2000")
    monkeypatch.setenv("ORG_SPAWN_DISK_MAX_PCT", "80")
    _disk(monkeypatch, 85)
    why = rg.check(meminfo=_meminfo(tmp_path, 1500 * 1024))
    assert "2000 MB" in why and "80%" in why


def test_bad_env_falls_back_to_the_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    monkeypatch.setenv("ORG_SPAWN_RAM_FLOOR_MB", "lots")
    monkeypatch.setenv("ORG_SPAWN_DISK_MAX_PCT", "-5")
    assert rg.ram_floor_mb() == 800 and rg.disk_max_pct() == 90


def test_no_meminfo_means_ram_unknown_and_only_disk_counts(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    _disk(monkeypatch, 50)
    assert rg.ram_available_mb(tmp_path / "absent") is None
    assert rg.check(meminfo=tmp_path / "absent") is None


def test_df_style_percent_counts_reserved_blocks_as_not_available(monkeypatch):
    # 1000 blocks, 100 free of which 50 are root-reserved: df says 900/(900+50)
    monkeypatch.setattr(rg.os, "statvfs", lambda path: _Statvfs(1000, 100, 50, 4096))
    assert rg.disk_used_pct("/") == pytest.approx(94.74, abs=0.01)


def test_cli_check_exit_codes(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    monkeypatch.setattr(rg, "MEMINFO", _meminfo(tmp_path, 100 * 1024))
    monkeypatch.setattr(rg.check, "__defaults__", ("/",))
    monkeypatch.setattr(rg.read, "__defaults__", ("/",))
    monkeypatch.setattr(rg.check, "__kwdefaults__", {"meminfo": rg.MEMINFO})
    monkeypatch.setattr(rg.read, "__kwdefaults__", {"meminfo": rg.MEMINFO})
    _disk(monkeypatch, 50)
    assert rg.main(["check"]) == 1
    assert "RAM available 100 MB" in capsys.readouterr().err
    monkeypatch.delenv("ORG_SPAWN_GATE")
    assert rg.main(["check"]) == 0


def test_cli_show_is_one_json_line(monkeypatch, tmp_path, capsys):
    _disk(monkeypatch, 42)
    assert rg.main(["show"]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["disk_used_pct"] == 42.0 and row["gate_on"] is False and row["refusal"] is None
