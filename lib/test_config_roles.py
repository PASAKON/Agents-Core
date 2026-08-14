"""Tests for lib.config's C-level roster helpers. Plain-script style (no
pytest dependency), matching lib/test_toon.py / lib/test_recall.py.

Guards the one subtle thing about `live_c_level_roles()`: it drops ``ceo``
while `is_c_level("ceo")` keeps saying yes. Those two answers look
contradictory, and a future edit "simplifying" one into the other would
reintroduce exactly the bug the helper exists to prevent -- a broadcast loop
trying to deliver to a CEO session that cannot exist.

Run:  python -m lib.test_config_roles
"""
from __future__ import annotations

from . import config


def _check(name: str, cond: bool) -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return cond


def test_ceo_is_c_level_but_not_a_live_session() -> bool:
    """The CEO is C-level for authority, never a spawned session."""
    ok = True
    ok &= _check("is_c_level('ceo') is still True",
                 config.is_c_level("ceo") is True)
    ok &= _check("live_c_level_roles() excludes ceo",
                 "ceo" not in config.live_c_level_roles())
    return ok


def test_matches_the_tuples_it_replaces() -> bool:
    """Behaviour-preserving today: the helper returns exactly the roster that
    runners/relay_mcp_server.py and runners/mac_agent.py hardcode, so
    swapping them over changes nothing until agents.yaml itself changes."""
    ok = True
    roles = config.live_c_level_roles()
    ok &= _check("same members as the hardcoded tuples",
                 set(roles) == {"cto", "cmo", "cgo", "cfo"})
    ok &= _check("returns a tuple (safe as a default arg)",
                 isinstance(roles, tuple))
    return ok


def test_derives_from_config_not_a_literal() -> bool:
    """The whole point: adding a C-level to policies/agents.yaml must show up
    here with no code edit. Proven by patching the parsed config rather than
    the file, so the test never writes to policies/."""
    ok = True
    original = config.agents
    try:
        config.agents = lambda: {"c_level": ["ceo", "cto", "cxx"]}  # type: ignore[assignment]
        ok &= _check("a new c_level role appears with no code change",
                     config.live_c_level_roles() == ("cto", "cxx"))
    finally:
        config.agents = original  # type: ignore[assignment]
    ok &= _check("restored after patch",
                 "cmo" in config.live_c_level_roles())
    return ok


def main() -> int:
    print("lib.config C-level roster")
    ok = True
    ok &= test_ceo_is_c_level_but_not_a_live_session()
    ok &= test_matches_the_tuples_it_replaces()
    ok &= test_derives_from_config_not_a_literal()
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
