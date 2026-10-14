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


# --- M9: host emoji (CEO 2026-10-14, relayed by COO SomPong) ------------------------

MAC, CONTABO, WINBOX = "\U0001F4BB", "\U0001F310", "\U0001F5A5\uFE0F"


def test_the_host_emoji_table():
    assert sn.HOST_EMOJI == {"mac": MAC, "contabo": CONTABO, "winbox": WINBOX}
    assert sn.host_prefix("contabo") == CONTABO + " "
    for unknown in ("", None, "MAC", "laptop", "contabo "):
        assert sn.host_prefix(unknown) == ""


@pytest.mark.parametrize("name,bare", [
    (CONTABO + " CTO (Kavin)", "CTO (Kavin)"),
    (WINBOX + " PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"),
    ("\U0001F5A5 PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"),     # typed without FE0F
    (MAC + "Dev#afe - x", "Dev#afe - x"),                                    # no space
    ("PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"),               # no emoji
    ("\u23f8 " + CONTABO + " CTO (Kavin) \u2014 t", "\u23f8 CTO (Kavin) \u2014 t"),  # state glyph kept
    (CONTABO + " " + MAC + " CTO", MAC + " CTO"),                            # only one is stripped
    ("CONTABO CTO #e106b78b (x)", "CONTABO CTO #e106b78b (x)"),
])
def test_strip_host_drops_one_leading_host_emoji(name, bare):
    assert sn.strip_host(name) == bare


@pytest.mark.parametrize("name", [
    CONTABO + " PH#f35 (CTO) - CookieRun", WINBOX + " PH#f35 (CTO) - CookieRun",
    "\U0001F5A5 PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"])
def test_a_ph_name_parses_with_any_emoji_or_none(name):
    assert sn.parse_short(name) == ("project_head", "f35")


def test_writers_put_the_right_emoji_and_none_for_an_unknown_host():
    assert config.ph_session_name("f35aaaaa", "cto", "CookieRun", "contabo") == \
        CONTABO + " PH#f35 (CTO) - CookieRun"
    assert config.ph_session_name("f35aaaaa", "cto", "CookieRun") == "PH#f35 (CTO) - CookieRun"
    assert config.ph_session_name("f35aaaaa", "cto", "CookieRun", "nowhere") == \
        "PH#f35 (CTO) - CookieRun"
    assert sn.with_host("winbox", CONTABO + " CTO (Kavin)") == WINBOX + " CTO (Kavin)"
    assert config.worker_session_name("contabo", "developer", "task-afe57b21", "x",
                                      head="OrgRestructure") == CONTABO + " Dev#afe - OrgRestructure: x"
    assert config.worker_session_name("nowhere", "developer", "task-afe57b21", "x") == "Dev#afe - x"


def test_a_windows_worker_name_has_no_emoji_and_still_passes_the_ascii_pattern():
    # winbox spawns cross cmd.exe (tools/delegate.py) and node_dispatch's ASCII-only
    # pattern; neither is widened for the emoji (M8's fullmatch stays as it was).
    name = config.worker_session_name("winbox", "browser_operator", "task-4a59a1a4",
                                      "SHOOT the teaser", head="MimiPage")
    assert name == "Browser#4a5 - MimiPage: SHOOT the teaser"
    assert node_dispatch._PS_SESSION_NAME_RE.fullmatch(name)
    assert not node_dispatch._PS_SESSION_NAME_RE.fullmatch(WINBOX + " " + name)


def test_the_cli_prints_only_a_known_hosts_emoji():
    import subprocess
    run = lambda h: subprocess.run([sys.executable, str(ROOT / "lib" / "session_names.py"), "prefix", h],
                                   capture_output=True)
    assert run("contabo").stdout == CONTABO.encode()
    assert run("winbox").stdout == WINBOX.encode()
    assert run("guess").stdout == b"" and run("guess").returncode == 0


# --- M10: rule_problem, the validator live-sessions flags names with -----------------

@pytest.mark.parametrize("name,role,sid,host,persona,why", [
    (CONTABO + " CTO (Kavin)", "cto", "c34459eb", "contabo", "Kavin", None),
    ("⏸ " + CONTABO + " CTO (Kavin) — t", "cto", "c34459eb", "contabo", "Kavin", None),
    (WINBOX + " CTO (Kavin)", "cto", "x", "winbox", "Kavin", None),
    ("\U0001F5A5 CTO (Kavin)", "cto", "x", "winbox", "Kavin", None),            # typed, no FE0F
    ("CTO (Kavin)", "cto", "x", "nowhere", "Kavin", None),                      # unknown host: none
    (CONTABO + " PH#7cf (CTO) - OrgRestructure — M10", "project_head", "7cf528f0", "contabo", None, None),
    ("Browser#4a5 - MimiPage: x", "browser_operator", "4a59a1a4", "winbox", None, None),
    (CONTABO + " Dev#afe - OrgRestructure: x", "developer", "afe57b21", "contabo", None, None),
    ("anything", "unknown", "x", "contabo", None, None),
    ("CEO", "ceo", "x", "contabo", None, None),
    ("CTO (Kavin)", "cto", "x", "contabo", "Kavin", "no host emoji"),
    ("CONTABO CTO #e106b78b (x)", "cto", "e106b78b", "contabo", None, "no host emoji"),
    (MAC + " CTO (Kavin)", "cto", "x", "contabo", "Kavin", "wrong host emoji"),
    (CONTABO + " CMO (Ging)", "cto", "x", "contabo", None, 'not "CTO (<Name>)"'),
    (CONTABO + " CTO (Ging)", "cto", "x", "contabo", "Kavin", 'not "CTO (Kavin)"'),
    (CONTABO + " PH#abc (CTO) - X", "project_head", "7cf528f0", "contabo", None,
     "PH#abc is not this session (#7cf)"),
    (CONTABO + " Project Head #7cf528f0", "project_head", "7cf528f0", "contabo", None,
     'not "PH#<id3> (<LANE>) - <Project>"'),
    (WINBOX + " Browser#4a5 - M: x", "browser_operator", "4a59a1a4", "winbox", None,
     "a host emoji where none belongs"),
    (CONTABO + " Test#afe - x", "developer", "afe57b21", "contabo", None,
     'not "Dev#<id3> - <Head>: <job>"'),
])
def test_rule_problem(name, role, sid, host, persona, why):
    assert sn.rule_problem(name, role, sid, host, persona=persona,
                           windows=(host == "winbox")) == why


def test_every_name_the_writers_make_is_on_the_rule():
    assert sn.rule_problem(config.ph_session_name("7cf528f0", "cto", "OrgRestructure", "contabo"),
                           "project_head", "7cf528f0", "contabo") is None
    for host in ("mac", "contabo", "winbox"):
        name = config.worker_session_name(host, "developer", "task-afe57b21", "x", head="H")
        assert sn.rule_problem(name, "developer", "afe57b21", host,
                               windows=(host == "winbox")) is None, name
