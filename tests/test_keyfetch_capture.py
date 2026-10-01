"""Skill CTO_Procedure_KeyFetch: scripts/keyfetch/capture_key.mjs captures TWO values from one create
(client id + secret), passes --path through to `infisical_setup.py put`, and reports both-or-nothing.

The suite is node:test (tests/keyfetch/keyfetch.test.mjs): argument parsing, the put/last4 plumbing
with a stub tool, and capture_key.mjs itself against a fake CDP browser on 127.0.0.1. No Chrome, no
Tailscale, no Infisical, no secret. This wrapper lets pytest collect it; skipped when node is absent.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_keyfetch_capture.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "tests" / "keyfetch" / "keyfetch.test.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_keyfetch_node_suite():
    run = subprocess.run(["node", "--test", str(SUITE)], capture_output=True, text=True, timeout=180, cwd=ROOT)
    summary = {k: int(v) for k, v in re.findall(r"^[ℹ#]\s*(pass|fail|skipped)\s+(\d+)", run.stdout + run.stderr, re.M)}
    assert run.returncode == 0, (run.stdout + run.stderr)[-4000:]
    assert summary.get("fail", 1) == 0 and summary.get("pass", 0) >= 20, summary
