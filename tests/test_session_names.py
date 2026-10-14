"""Session-name shapes (CEO 2026-10-14, card QG-20261014-0326-8968): lib/session_names.py
writes and reads them; lib/config re-exports the writers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
from lib import session_names as sn  # noqa: E402
from tools import node_dispatch  # noqa: E402


@pytest.mark.parametrize("sid,lane,projects,expect", [
    ("6c487e37", "cto", "SpendGuard", "PH#6c4 (CTO) - SpendGuard"),
    ("6c487e37", "CMO", ["MimiPage", "B", "C"], "PH#6c4 (CMO) - MimiPage + B + C"),
    ("6c487e37", "cto", ["", "  "], "PH#6c4 (CTO)"),
])
def test_ph_name(sid, lane, projects, expect):
    assert config.ph_session_name(sid, lane, projects) == expect
    assert sn.parse_short(expect) == ("project_head", "6c4")


def test_every_worker_role_has_a_unique_short_word():
    agents = config.agents()
    roles = [r for r in agents["roles"] if not config.is_c_level(r)
             and r not in ("ceo", "project_head", "cxo")]
    assert sorted(roles) == sorted(sn.WORKER_SHORT), "add the new role to WORKER_SHORT"
    words = list(sn.WORKER_SHORT.values())
    assert len(set(words)) == len(words)
    for w in words:
        assert sn.WORKER_NAME_RE.match(f"{w}#abc - x"), w
        assert w != "PH" and not (len(w) == 3 and w[0] == "C" and w[2] == "O")


@pytest.mark.parametrize("name,expect", [
    ("Dev#afe - OrgRestructure: identity strict", ("developer", "afe")),
    ("Sec#afe", ("security_engineer", "afe")),
    ("⏸ Res#0a1 - x", ("researcher", "0a1")),
    ("Boss#afe - x", None),          # not a known short word
    ("Dev#AFE - x", None), ("Dev#afe5 - x", None), ("Dev #afe", None),
    ("PH#6c4 CTO - x", None), ("CTO (Kavin)", None),
])
def test_parse_short(name, expect):
    assert sn.parse_short(name) == expect


def test_worker_head_reads_the_ph_project_else_the_c_level(tmp_path):
    (tmp_path / "project_head-7cf528f0.project").write_text("OrgRestructure\n", encoding="utf-8")
    (tmp_path / "project_head-0000000b.project").write_text("bad; rm -rf\n", encoding="utf-8")
    head = config.worker_head
    assert head({"owner_role": "project_head", "owner_cto": "7cf528f0"}, tmp_path) == "OrgRestructure"
    assert head({"owner_role": "project_head", "owner_cto": "0000000a"}, tmp_path) == ""   # no file
    assert head({"owner_role": "project_head", "owner_cto": "0000000b"}, tmp_path) == ""   # bad text
    assert head({"owner_role": "project_head", "owner_cto": "../../x"}, tmp_path) == ""
    assert head({"owner_role": "cmo", "owner_cto": "ef04792e"}, tmp_path) == "CMO"
    assert head({}, tmp_path) == ""


def test_a_worker_name_passes_the_windows_launcher_pattern():
    name = config.worker_session_name("winbox", "browser_operator", "task-4a59a1a4",
                                      "SHOOT the teaser", head="MimiPage")
    assert node_dispatch._PS_SESSION_NAME_RE.fullmatch(name)
    assert not node_dispatch._PS_SESSION_NAME_RE.fullmatch("Dev#abc - it's")
