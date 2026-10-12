"""scripts/infisical/copy_secret.mjs copies ONE Infisical secret across projects with no model seeing it.

The suite is node:test (tests/js/copy_secret.test.mjs): the script against a fake CDP browser and a fake
Infisical on 127.0.0.1 — one match writes and prints MATCH, zero/two matches write nothing, an existing
target and an Org-Infra target are refused, and the fake value, its last 4 and the token never reach the
output. No Chrome, no Infisical, no secret. This wrapper lets pytest collect it; skipped when node is absent.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_copy_secret.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "tests" / "js" / "copy_secret.test.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_copy_secret_node_suite():
    # node 20 has no global WebSocket without the flag; node 22 accepts it as a no-op
    run = subprocess.run(["node", "--experimental-websocket", "--test", str(SUITE)],
                         capture_output=True, text=True, timeout=180, cwd=ROOT)
    summary = {k: int(v) for k, v in re.findall(r"^[ℹ#]\s*(pass|fail|skipped)\s+(\d+)", run.stdout + run.stderr, re.M)}
    assert run.returncode == 0, (run.stdout + run.stderr)[-4000:]
    assert summary.get("fail", 1) == 0 and summary.get("pass", 0) >= 24, summary
