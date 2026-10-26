"""Collect the browser-free Node seat suite; no live Infisical calls."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_writer_seat_node_suite():
    # node:test runs on import; avoid the extra fork/IPC required by --test in this sandbox.
    run = subprocess.run(["node", "tests/keyfetch/keyfetch_writer_seat.test.mjs"],
                         capture_output=True, text=True, timeout=180, cwd=ROOT)
    summary = {k: int(v) for k, v in re.findall(r"^[ℹ#]\s*(pass|fail|skipped)\s+(\d+)",
                                              run.stdout + run.stderr, re.M)}
    assert run.returncode == 0, (run.stdout + run.stderr)[-6000:]
    assert "sk-test-NEVER-PRINT-THIS-SECRET-123456789" not in run.stdout + run.stderr
    assert summary.get("fail", 1) == 0 and summary.get("pass", 0) >= 16, summary


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("ttl", ["2", "0", "-1", "NaN", "Infinity"])
def test_bootstrap_writer_rejects_bad_ttl_before_browser_access(ttl):
    run = subprocess.run(["node", "scripts/infisical/bootstrap_setup_identity.mjs",
                          "--identity", "keyfetch-writer", "--ttl-days", ttl],
                         capture_output=True, text=True, timeout=10, cwd=ROOT)
    assert run.returncode == 64
    assert "at most 1" in run.stderr
