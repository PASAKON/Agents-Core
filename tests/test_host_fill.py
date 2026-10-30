import json
import subprocess
import threading
from types import SimpleNamespace

import pytest

from tools import host_fill as hf
from tools import node_dispatch as nd


@pytest.mark.parametrize("platform,total,free,cpu,volume", [
    ("linux", 8, 2, 50, "/"),
    ("darwin", 8, 2, 50, "/System/Volumes/Data"),
    ("win32", 16, 8, 35, "C:/"),
])
def test_os_sources(monkeypatch, platform, total, free, cpu, volume):
    monkeypatch.setattr(nd.sys, "platform", platform)
    monkeypatch.setattr(nd, "_is_windows", lambda: platform == "win32")
    monkeypatch.setattr(nd, "_cpu_facts", lambda: (4, .5))
    monkeypatch.setattr(nd.Path, "read_text", lambda self: "MemTotal: 8388608 kB\nMemAvailable: 2097152 kB\n")
    def disk(path):
        assert path == volume
        return SimpleNamespace(total=100 * 1024**3, free=40 * 1024**3)
    monkeypatch.setattr(nd.shutil, "disk_usage", disk)
    def run(argv, **kwargs):
        output = {"sysctl": str(8 * 1024**3),
                  "memory_pressure": "System-wide memory free percentage: 25%",
                  "powershell.exe": json.dumps({"total": 16 * 1024**2,
                                                "free": 8 * 1024**2, "cpu": 35})}[argv[0]]
        if argv[0] == "powershell.exe":
            assert "FreePhysicalMemory" in argv[-1] and "LoadPercentage" in argv[-1]
            assert kwargs["timeout"] <= 10
        return subprocess.CompletedProcess(argv, 0, output, "")
    monkeypatch.setattr(nd.subprocess, "run", run)
    facts = nd._fill_facts()
    assert facts["ram_total_gb"] == total
    assert facts["ram_free_gb"] == free
    assert facts["cpu_pct"] == cpu
    assert hf.fill(facts) == ((75., "ram", []) if platform != "win32" else (60., "disk", []))


def test_legacy_and_invalid_sensors():
    assert hf.fill({"load_per_core": .8}) == (80., "cpu", ["ram", "disk"])
    assert hf.fill({"cpu_pct": float("nan"), "ram_total_gb": 0}) == (None, None, ["ram", "cpu", "disk"])


def test_parallel_offline_and_output(monkeypatch, capsys):
    barrier = threading.Barrier(2)
    monkeypatch.setattr(hf.config, "self_host", lambda: "contabo")
    monkeypatch.setattr(nd, "_fill_facts", lambda: {"cpu_pct": 25})
    monkeypatch.setattr(nd, "_running_workers", lambda host: 2)
    def remote(host, verb, timeout):
        assert verb == "probe" and timeout == 10
        barrier.wait(timeout=2)
        if host == "mac":
            raise hf.mesh.MeshUnreachable("timeout")
        return {"ok": True, "result": {"load_per_core": .5, "running": 1}}
    monkeypatch.setattr(hf.mesh, "dispatch", remote)
    assert hf.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert "contabo · online" in lines[0]
    assert "winbox · online" in lines[1]
    assert "mac · offline" in lines[2]
    assert hf.main(["--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[2]["online"] is False
    assert rows[1]["missing"] == ["ram", "disk"]
