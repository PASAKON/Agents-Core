"""Every C-level collection the code uses holds every C-level in the policy.

The roster lives in one place: `c_level` in policies/agents.yaml (minus the
CEO, a human who never runs a session). Wiring the COO (CEO 2026-09-27)
meant grepping for `cgo` across twenty files, because four Python tuples,
three shell patterns and a routing rule each carried their own copy. The
Python ones now read lib/roles.py; the shell ones cannot. This file fails
when any of them -- or a new hardcoded list anywhere in the runtime code --
misses a role, so the next C-level is one YAML line plus whatever this test
names, never half-wired.

Run: .venv/bin/python -m pytest tests/test_c_level_roles.py
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config  # noqa: E402
from lib import roles  # noqa: E402

POLICY = yaml.safe_load((ROOT / "policies" / "agents.yaml").read_text(encoding="utf-8"))
EXPECTED = tuple(r for r in POLICY["c_level"] if r != "ceo")
DISPLAYS = tuple(POLICY["roles"][r]["display"] for r in EXPECTED)


def _missing(found) -> list[str]:
    found = {str(x).strip().lower() for x in found}
    return [r for r in EXPECTED if r not in found]


# --------------------------------------------------------------------------
# the policy itself
# --------------------------------------------------------------------------

def test_policy_roster_is_complete() -> None:
    assert "coo" in EXPECTED  # the role this file was written for
    for r in EXPECTED:
        entry = POLICY["roles"].get(r)
        assert entry, f"c_level lists {r!r} but policies/agents.yaml has no roles.{r}"
        assert entry["level"] == "c"
        assert entry.get("model"), f"{r} has no model -- it could not run a session"
        assert entry.get("display")
        assert (ROOT / "roles" / f"{r}.md").is_file(), f"roles/{r}.md missing"


# --------------------------------------------------------------------------
# the helper
# --------------------------------------------------------------------------

def test_helper_reads_the_policy() -> None:
    assert config.live_c_level_roles() == EXPECTED
    assert roles.c_level_roles() == EXPECTED
    assert roles.c_level_displays() == DISPLAYS


def test_static_fallback_holds_the_same_roles() -> None:
    """The fallback is only used where the policy cannot be read; it must
    still say the same thing, or a PyYAML-less launcher sees a smaller org."""
    assert sorted(roles.STATIC_C_LEVEL_ROLES) == sorted(EXPECTED)


def test_fallback_without_pyyaml(monkeypatch) -> None:
    # sys.modules[name] = None makes `from lib.config import ...` raise
    # ImportError -- what a system python3 with no PyYAML hits.
    monkeypatch.setitem(sys.modules, "lib.config", None)
    assert roles.c_level_roles() == roles.STATIC_C_LEVEL_ROLES
    assert roles.c_level_displays() == tuple(r.upper() for r in roles.STATIC_C_LEVEL_ROLES)


def test_fallback_without_policy_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "AGENTS_CONFIG", tmp_path / "absent.yaml")
    config.agents.cache_clear()
    try:
        assert roles.c_level_roles() == roles.STATIC_C_LEVEL_ROLES
        assert roles.c_level_displays() == tuple(r.upper() for r in roles.STATIC_C_LEVEL_ROLES)
    finally:
        config.agents.cache_clear()


# --------------------------------------------------------------------------
# module constants that used to be hardcoded tuples
# --------------------------------------------------------------------------

@pytest.mark.parametrize("module, attr", [
    ("runners.relay_mcp_server", "C_LEVEL_ROLES"),
    ("runners.mac_agent", "C_LEVEL_ROLES"),
    ("tools.session_name", "ROLES"),
])
def test_module_roster_constant(module: str, attr: str) -> None:
    mod = importlib.import_module(module)
    assert not _missing(getattr(mod, attr)), f"{module}.{attr} misses {_missing(getattr(mod, attr))}"


def test_session_name_regex_accepts_every_role() -> None:
    from tools import session_name
    for r in EXPECTED:
        assert session_name.ROLE_RE.match(f"{r}-1a2b3c4d"), r
        assert session_name.id_from_tmux_session(f"{r}-1a2b3c4d", role=r) == "1a2b3c4d"


def test_itermtab_never_touches_any_c_level_tab() -> None:
    from tools import itermtab
    assert itermtab._CLEVEL_PREFIXES == tuple(f"{d} " for d in DISPLAYS)
    guard = itermtab._clevel_title_guard()
    for d in DISPLAYS:
        assert f'and not (nm contains "{d} ")' in guard
        assert f'and not (tn contains "{d} ")' in guard


def _cxo_mcp_config():
    path = ROOT / "scripts" / "lib" / "cxo_mcp_config.py"
    spec = importlib.util.spec_from_file_location("cxo_mcp_config_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_role_has_an_explicit_mcp_server_set() -> None:
    mod = _cxo_mcp_config()
    assert not _missing(mod.ROLE_SERVERS), f"ROLE_SERVERS misses {_missing(mod.ROLE_SERVERS)}"
    for r in EXPECTED:
        assert "org" in mod.ROLE_SERVERS[r], f"{r} would launch without the org server"


def test_coo_server_set_is_the_read_only_base() -> None:
    """COO (2026-09-27): org + lungnote only -- no database, no ad spend."""
    mod = _cxo_mcp_config()
    assert mod.ROLE_SERVERS["coo"] == mod.BASE_SERVERS
    assert not {"supabase", "meta-ads-135"} & set(mod.ROLE_SERVERS["coo"])


# --------------------------------------------------------------------------
# send_to_cxo: the CLI and its errors name every role
# --------------------------------------------------------------------------

def test_send_to_cxo_accepts_and_names_every_role(monkeypatch, tmp_path, capsys) -> None:
    import tools.send_to_cxo as sc

    with pytest.raises(ValueError) as e:
        sc.send("cxx", "hello")
    assert "not a C-level role" in str(e.value)
    assert not _missing(re.findall(r"[a-z]+", str(e.value).split("Known C-level:")[1]))

    # A real role gets PAST the role check: with no live session it fails
    # on the session lookup instead (nothing is written on either path).
    monkeypatch.setattr(sc, "LOCKS_DIR", tmp_path)
    for r in EXPECTED:
        with pytest.raises(ValueError) as e:
            sc.send(r, "hello")
        assert "not a C-level role" not in str(e.value)
        assert "no active" in str(e.value)

    monkeypatch.setattr(sys, "argv", ["send_to_cxo", "--help"])
    assert sc.main() == 0
    usage = capsys.readouterr().out
    listed = usage.split("<target_role>:")[1].strip().split("|")
    assert not _missing(listed), f"--help misses {_missing(listed)}"


# --------------------------------------------------------------------------
# SomPong's router sends an order naming any C-level to a C-level lane
# --------------------------------------------------------------------------

def test_sompong_routes_an_order_for_every_role() -> None:
    from tools import decide
    cfg = yaml.safe_load(
        (ROOT / "config" / "decisions" / "sompong.route.yaml").read_text(encoding="utf-8"))
    for r in EXPECTED:
        verdict = decide._rules_provider(cfg, f"ให้ {r} ช่วยดูเรื่องนี้หน่อย")
        assert verdict and verdict["choice"] in ("order_for_cto", "order_for_other_cxo"), r
    verdict = decide._rules_provider(cfg, "เรื่องการจัดการโปรเจค ช่วยสรุปสถานะให้หน่อย")
    assert verdict and verdict["choice"] == "order_for_other_cxo"


# --------------------------------------------------------------------------
# shell: the role alternatives the launchers pattern-match on
# --------------------------------------------------------------------------

def _sh(name: str) -> str:
    return (ROOT / "scripts" / name).read_text(encoding="utf-8")


def test_terminal_open_patterns() -> None:
    src = _sh("terminal-open.sh")
    roles_re = re.search(r"^ROLES_RE='\^\(([a-z|]+)\)-'$", src, re.M)
    awk_re = re.search(r"awk '\$2 ~ /\^\(([a-z|]+)\)-/'", src)
    case_line = re.search(r"^\s*((?:[a-z]+-\*\|)+[a-z]+-\*)\) SESSION=\"\$1\" ;;$", src, re.M)
    assert roles_re and awk_re and case_line, "terminal-open.sh changed shape; update this test"
    for label, found in (
        ("ROLES_RE", roles_re.group(1).split("|")),
        ("live_sessions awk", awk_re.group(1).split("|")),
        ("case", [p[:-2] for p in case_line.group(1).split("|")]),
    ):
        assert not _missing(found), f"terminal-open.sh {label} misses {_missing(found)}"


@pytest.mark.parametrize("script", ["cxo-claude.sh", "spawn-cxo.sh"])
def test_launcher_usage_names_every_role(script: str) -> None:
    m = re.search(r"--role <([a-z|]+)>", _sh(script))
    assert m, f"{script}: usage line changed shape; update this test"
    found = m.group(1).split("|")
    assert not _missing(found), f"{script} usage misses {_missing(found)}"


# --------------------------------------------------------------------------
# no new hardcoded roster anywhere in the runtime code
# --------------------------------------------------------------------------

# A literal that lists three or more C-level roles is a roster copy; it must
# list them all. Deliberate subsets are named here with the reason.
_ALLOWED_SUBSETS = {
    # The memory cap counts cto/cmo/cfo (+ cxo) only -- cgo and coo sessions
    # are not capped (see tools/session_name.py's docstring). A capacity
    # decision, not a roster copy.
    ("tools/session_cap.py", ("cto", "cmo", "cfo", "cxo")),
}
_QUOTED_SEQ = re.compile(
    r"[(\[{]\s*((?:[\"'][A-Za-z_ ]+[\"']\s*,\s*){2,}[\"'][A-Za-z_ ]+[\"'])\s*,?\s*[)\]}]")
_ALTERNATION = re.compile(r"(?<![A-Za-z])((?:[a-z]+(?:-\*)?\|){2,}[a-z]+(?:-\*)?)(?![A-Za-z])")


def _runtime_files():
    for top in ("lib", "runners", "tools", "scripts"):
        for p in sorted((ROOT / top).rglob("*")):
            if p.suffix not in (".py", ".sh") or "__pycache__" in p.parts:
                continue
            if p.name.startswith("test_"):
                continue
            yield p


def _literals(text: str):
    for m in _QUOTED_SEQ.finditer(text):
        yield tuple(s.strip().lower() for s in re.findall(r"[\"']([A-Za-z_ ]+)[\"']", m.group(1)))
    for m in _ALTERNATION.finditer(text):
        yield tuple(t.removesuffix("-*") for t in m.group(1).split("|"))


def test_no_partial_roster_literal_in_runtime_code() -> None:
    offenders = []
    for p in _runtime_files():
        rel = p.relative_to(ROOT).as_posix()
        for items in _literals(p.read_text(encoding="utf-8", errors="replace")):
            named = [i for i in items if i in EXPECTED]
            if len(named) >= 3 and _missing(items) and (rel, items) not in _ALLOWED_SUBSETS:
                offenders.append(f"{rel}: {items} misses {_missing(items)}")
    assert not offenders, (
        "hardcoded C-level list(s) missing a role -- read lib/roles.py instead "
        "(or add the role):\n  " + "\n  ".join(offenders))
