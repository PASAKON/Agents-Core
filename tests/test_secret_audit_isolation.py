"""The root conftest keeps every test's secret-door audit spool out of the main checkout."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import infisical_setup as inf  # noqa: E402


def test_audit_dir_is_under_tmp(tmp_path):
    got = Path(inf.audit_dir()).resolve()
    assert got == (tmp_path / "secret-audit").resolve()
    assert Path(inf._checkout_root()).resolve() / "state" / "secret-audit" != got
