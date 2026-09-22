"""tests/conftest.py — no test may reach a paid endpoint through the gitignored .env.

Born 2026-09-22: tools/decide.py reads OPENROUTER_API_KEY / DECIDE_PROVIDER / DECIDE_BUDGET_USD
from os.environ and then from the repo-root .env (lib.config._read_dotenv_var). A test that only
`monkeypatch.delenv()`s those vars still falls through to the real .env and makes LIVE Jev calls —
task-a6129a75 hit it twice while iterating, then tests/test_decide_browser_sites.py (written
before the fallback existed) hit it on main: 2 paid calls per suite run, invisible because the
ledger was redirected to tmp. This fixture is autouse for the whole tests/ tree so the class of
bug cannot come back: the dotenv reader itself is neutralised, not just the variables.
A test that is about the reader itself opts out with `@pytest.mark.allow_dotenv` (and must point the
reader at a tmp .env, never the real one). Live smoke is a CLI verb (DECIDE_LIVE=1), never pytest.
"""
from __future__ import annotations

import importlib
import pytest

_PAID_VARS = ("OPENROUTER_API_KEY", "DECIDE_PROVIDER", "DECIDE_BUDGET_USD", "DECIDE_JEV_MODEL", "JEV_API_KEY", "JEV_API_URL")


@pytest.fixture(autouse=True)
def _no_dotenv_no_paid_calls(request, monkeypatch):
    if request.node.get_closest_marker("allow_dotenv"):
        yield  # the test is ABOUT the reader; it points ROOT at a tmp .env itself
        return
    for var in _PAID_VARS:
        monkeypatch.delenv(var, raising=False)
    for modname in ("tools.decide", "lib.config"):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        if hasattr(mod, "_read_dotenv_var"):
            monkeypatch.setattr(mod, "_read_dotenv_var", lambda name: None)
    yield
