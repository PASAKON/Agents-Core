"""Session-name shapes (CEO 2026-10-14 host emoji; 2026-10-15 the new shape, plan N of
state/handoff/2026-10-15/plan-names-watch-macoff.md): lib/session_names.py writes and
reads them; lib/config re-exports the writers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
from lib import session_names as sn  # noqa: E402
from tools import node_dispatch  # noqa: E402

MAC, CONTABO, WINBOX = "\U0001F4BB", "\U0001F310", "\U0001F5A5️"
DOT = "·"


def body(name: str) -> str:
    return sn.split_name(name)[2]


# --- N1: the writers ----------------------------------------------------------------------

@pytest.mark.parametrize("made,expect", [
    (lambda: sn.clevel_name("cto", "c34459eb", "", "contabo"), f"{CONTABO} CTO#c34 Main"),
    (lambda: sn.clevel_name("cmo", "ef04792e", "", "contabo"), f"{CONTABO} CMO#ef0 Main"),
    (lambda: sn.clevel_name("cto", "task-c34459eb", "Console fix", "mac"), f"{MAC} CTO#c34 Console fix"),
    (lambda: sn.clevel_name("cto", "c34459eb", "  ", None), "CTO#c34 Main"),
    (lambda: sn.clevel_name("coo", None, "", "contabo", "SomPong"), f"{CONTABO} COO SomPong"),
    (lambda: sn.clevel_name("coo", "fde4c4ca", "x", "contabo", "SomPong"), f"{CONTABO} COO x"),    # no org sid: no id
    (lambda: sn.ph_session_name("7cf528f0", "OrgRestructure", "contabo"), f"{CONTABO} PH#7cf OrgRestructure"),
    (lambda: sn.ph_session_name("6c487e37", ["MimiPage", "B", "C"]), "PH#6c4 MimiPage+B+C"),
    (lambda: sn.ph_session_name("7cf528f0", "OrgRestructure", "contabo", "test"), f"{CONTABO} PH#7cf test"),
    (lambda: sn.ph_session_name("6c487e37", ["", "  "]), "PH#6c4"),
    (lambda: sn.ph_session_name("f35aaaaa", "CookieRun", "nowhere"), "PH#f35 CookieRun"),
    (lambda: sn.worker_name("Dev", "task-49b1d2e3", "OrgRestructure", "sparse worktrees", "claude-sonnet-5-5"),
     f"Dev{DOT}S#49b Org: sparse worktrees"),
    (lambda: sn.worker_name("Sec", "task-afe57b21", "SpendGuard", "audit", "claude-opus-5-5[1m]"),
     f"Sec{DOT}O#afe Spend: audit"),
    (lambda: sn.worker_name("Res", "afe57b21", "CTO", "x", "claude-haiku-4-5-20251001"), f"Res{DOT}H#afe CTO: x"),
    (lambda: sn.worker_name("Dev", "afe57b21", "CTO", "x", "glm-5.2"), "Dev#afe CTO: x"),     # no letter for another model
    (lambda: sn.worker_name("Dev", "afe57b21", "", "just a job", "S"), f"Dev{DOT}S#afe just a job"),
    (lambda: sn.worker_name("Dev", "afe57b21", "BlackLiquidity", "", "S"), f"Dev{DOT}S#afe BlackLiq"),
    (lambda: sn.worker_name("Dev", "afe57b21", "MimiPage", "x", "claude-sonnet-5-5", windows=True), "Dev.S#afe Mimi: x"),
    (lambda: sn.worker_name("Dev", "task-49b1d2e3", "OrgRestructure", "sparse worktrees", "S", windows=True),
     "Dev.S#49b Org: sparse worktrees"),
    (lambda: sn.watch_name("a1b00000", 2, "\U0001F7E2", "contabo"), f"{CONTABO} Watch#a1b Runs: 2\U0001F7E2"),
    (lambda: sn.watch_name("a1b00000", 0, "⚪"), "Watch#a1b Runs: 0⚪"),
])
def test_N1_the_writers_make_exactly_these_strings(made, expect):
    assert made() == expect


@pytest.mark.parametrize("total,cut", [(31, False), (32, False), (33, True), (80, True)])
def test_N1_the_body_is_at_most_32_characters_and_a_cut_marks_itself(total, cut):
    name = sn.worker_name("Dev", "afe57b21", "", "x" * (total - 10), "S")     # "Dev·S#afe " is 10 characters
    assert len(body(name)) == min(total, sn.NAME_BODY_MAX)
    assert body(name).endswith("…") == cut
    topic = sn.clevel_name("cto", "c34459eb", "y" * (total - 8), "contabo")   # "CTO#c34 " is 8 characters
    assert len(body(topic)) == min(total, sn.NAME_BODY_MAX) and body(topic).endswith("…") == cut


def test_N1_the_32_character_edge_is_exact():
    exactly = sn.clevel_name("cto", "c34459eb", "y" * 24, "contabo")           # 8 + 24 = 32: untouched
    assert body(exactly) == "CTO#c34 " + "y" * 24
    over = sn.clevel_name("cto", "c34459eb", "y" * 25, "contabo")              # 33: 31 characters and the mark
    assert body(over) == "CTO#c34 " + "y" * 23 + "…" and len(body(over)) == 32


def test_N1_a_windows_worker_name_is_ascii_only_with_no_emoji_and_cuts_with_dots():
    name = config.worker_session_name("winbox", "browser_operator", "task-4a59a1a4",
                                      "SHOOT the teaser", head="MimiPage")
    assert name == "Browser.S#4a5 Mimi: SHOOT the..." and name.isascii() and len(name) == 32
    assert node_dispatch._PS_SESSION_NAME_RE.fullmatch(name)
    assert not node_dispatch._PS_SESSION_NAME_RE.fullmatch(WINBOX + " " + name)
    assert not node_dispatch._PS_SESSION_NAME_RE.fullmatch(f"Dev{DOT}S#abc Org: x")   # the ASCII-only pattern stays
    short = config.worker_session_name("winbox", "developer", "task-49b1d2e3", "sparse worktrees",
                                       head="OrgRestructure")
    assert short == "Dev.S#49b Org: sparse worktrees" and node_dispatch._PS_SESSION_NAME_RE.fullmatch(short)


def test_the_head_is_the_project_shortened():
    assert [sn.head_short(p) for p in ("OrgRestructure", "SpendGuard", "BlackLiquidity", "MimiPage")] == \
        ["Org", "Spend", "BlackLiq", "Mimi"]
    assert sn.head_short("CookieRun") == "CookieRun" and sn.head_short("LuminaSkiesLong") == "LuminaSkie"
    assert sn.head_short("Org") == "Org" and sn.head_short("") == ""
    assert config.head_short("OrgRestructure") == "Org" and config.head_short("CTO") == "CTO"


def test_the_model_letter():
    assert [sn.model_letter(m) for m in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5-20251001",
                                         "claude-opus-5-5[1m]", "O", "s", "glm-5.2", "", None)] == \
        ["O", "S", "H", "O", "O", "S", "", "", ""]


def test_a_worker_name_takes_its_model_from_the_role_when_not_told():
    assert config.worker_session_name("contabo", "developer", "task-afe57b21", "x", head="OrgRestructure") == \
        f"{CONTABO} Dev{DOT}S#afe Org: x"
    assert config.worker_session_name("contabo", "developer", "task-afe57b21", "x", head="CTO",
                                      model="claude-opus-5-5") == f"{CONTABO} Dev{DOT}O#afe CTO: x"
    assert config.worker_session_name("nowhere", "developer", "task-afe57b21", "x") == f"Dev.S#afe x"


# --- N2: the readers take the old and the new shape --------------------------------------

def test_every_worker_role_has_a_unique_short_word():
    agents = config.agents()
    roles = [r for r in agents["roles"] if not config.is_c_level(r)
             and r not in ("ceo", "project_head", "cxo")]
    assert sorted(roles) == sorted(sn.WORKER_SHORT), "add the new role to WORKER_SHORT"
    words = list(sn.WORKER_SHORT.values())
    assert len(set(words)) == len(words)
    for w in words:
        assert sn.WORKER_NAME_RE.match(f"{w}#abc - x"), w                    # old
        assert sn.WORKER_NAME_RE.match(f"{w}{DOT}S#abc Org: x"), w           # new
        assert w != "PH" and w != "Watch" and not (len(w) == 3 and w[0] == "C" and w[2] == "O")


@pytest.mark.parametrize("name,expect", [
    ("Dev#afe - OrgRestructure: identity strict", ("developer", "afe")),
    (f"Dev{DOT}S#afe Org: identity strict", ("developer", "afe")),
    ("Dev.S#afe Org: identity strict", ("developer", "afe")),
    ("Sec#afe", ("security_engineer", "afe")),
    ("⏸ Res#0a1 - x", ("researcher", "0a1")),
    (f"{CONTABO} CTO#c34 Main", ("cto", "c34")),
    (f"{CONTABO} COO SomPong", ("coo", "")),
    (f"{CONTABO} PH#7cf OrgRestructure", ("project_head", "7cf")),
    (f"{CONTABO} Watch#a1b Runs: 2\U0001F7E2", ("watch", "a1b")),
    ("CTO (Kavin)", ("cto", "")), ("CTO (Kavin) — CTO Main", ("cto", "")), ("CFO", ("cfo", "")),
    ("MAC CTO #671f688f (PH LastBell + Scriptable)", ("cto", "671")),
    ("Boss#afe - x", None),          # not a known short word
    ("Dev#AFE - x", None), ("Dev#afe5 - x", None), ("Dev #afe", None),
    ("CTO Main", None), ("CEO", None), ("CEO#c34 Main", None),
])
def test_parse_short(name, expect):
    assert sn.parse_short(name) == expect


# the live sessions of plan N.3 (15 Oct 04:42 TH): (old name, what it parses to, new name, what that
# parses to, the registry's role, sid, host). The Contabo worker's new name is the one the sweep writes
# from the old name's own, already cut job; the plan's "…sparse wo…" is 33 characters, one over the body limit.
N2_ROWS = [
    ("CTO (Kavin) — CTO Main", ("cto", ""), f"{CONTABO} CTO#c34 Main", ("cto", "c34"), "cto", "c34459eb", "contabo"),
    ("CMO (Ging) — CMO Main", ("cmo", ""), f"{CONTABO} CMO#ef0 Main", ("cmo", "ef0"), "cmo", "ef04792e", "contabo"),
    ("COO (SomPong)", ("coo", ""), f"{CONTABO} COO SomPong", ("coo", ""), "coo", "fde4c4ca", "contabo"),
    ("PH#7cf (CTO) - OrgRestructure", ("project_head", "7cf"), f"{CONTABO} PH#7cf OrgRestructure",
     ("project_head", "7cf"), "project_head", "7cf528f0", "contabo"),
    ("PH#6c4 (CTO) - SpendGuard", ("project_head", "6c4"), f"{CONTABO} PH#6c4 SpendGuard",
     ("project_head", "6c4"), "project_head", "6c4a1b2c", "contabo"),
    ("PH#f35 (CTO) - CookieRun", ("project_head", "f35"), f"{CONTABO} PH#f35 CookieRun",
     ("project_head", "f35"), "project_head", "f35c0ffe", "contabo"),
    ("PH#13d (CMO) - BlackLiquidity", ("project_head", "13d"), f"{CONTABO} PH#13d BlackLiquidity",
     ("project_head", "13d"), "project_head", "13d90a1b", "contabo"),
    ("PH#36c (CMO) - MimiPage", ("project_head", "36c"), f"{CONTABO} PH#36c MimiPage",
     ("project_head", "36c"), "project_head", "36c49776", "contabo"),
    (f"{CONTABO} Dev#49b - OrgRestructure: Item 5: sparse…", ("developer", "49b"),
     f"{CONTABO} Dev{DOT}S#49b Org: Item 5: sparse…", ("developer", "49b"), "developer", "49b1d2e3", "contabo"),
    ("MAC CTO #671f688f (PH LastBell + Scriptable)", ("cto", "671"), f"{MAC} CTO#671 LastBell+Scriptable",
     ("cto", "671"), "cto", "671f688f", "mac"),
    ("MAC CTO #f39cb080 (PH LuminaSkies V2.6 push + M-R)", ("cto", "f39"), f"{MAC} PH#f39 LuminaSkies",
     ("project_head", "f39"), "project_head", "f39cb080", "mac"),
]


@pytest.mark.parametrize("old,old_parse,new,new_parse,role,sid,host", N2_ROWS, ids=[r[2] for r in N2_ROWS])
def test_N2_both_shapes_parse_and_only_the_old_one_is_off_the_rule(old, old_parse, new, new_parse, role, sid, host):
    assert sn.parse_short(old) == old_parse
    assert sn.parse_short(new) == new_parse
    assert sn.rule_problem(old, role, sid, host) == "old shape"
    assert sn.rule_problem(new, role, sid, host) is None
    assert len(body(new)) <= sn.NAME_BODY_MAX
    # a leading state glyph and the host emoji change neither answer
    assert sn.parse_short("⏸ " + new) == new_parse and sn.rule_problem("⏸ " + new, role, sid, host) is None
    assert sn.rule_problem("⏸ " + old, role, sid, host) == "old shape"


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


# --- M9: host emoji (CEO 2026-10-14, relayed by COO SomPong) ------------------------

def test_the_host_emoji_table():
    assert sn.HOST_EMOJI == {"mac": MAC, "contabo": CONTABO, "winbox": WINBOX}
    assert sn.host_prefix("contabo") == CONTABO + " "
    for unknown in ("", None, "MAC", "laptop", "contabo "):
        assert sn.host_prefix(unknown) == ""


@pytest.mark.parametrize("name,bare", [
    (CONTABO + " CTO#c34 Main", "CTO#c34 Main"),
    (WINBOX + " PH#f35 CookieRun", "PH#f35 CookieRun"),
    ("\U0001F5A5 PH#f35 CookieRun", "PH#f35 CookieRun"),                 # typed without FE0F
    (MAC + f"Dev{DOT}S#afe x", f"Dev{DOT}S#afe x"),                       # no space
    ("PH#f35 CookieRun", "PH#f35 CookieRun"),                            # no emoji
    ("⏸ " + CONTABO + " CTO#c34 t", "⏸ CTO#c34 t"),             # state glyph kept
    (CONTABO + " " + MAC + " CTO", MAC + " CTO"),                        # only one is stripped
    ("CONTABO CTO #e106b78b (x)", "CONTABO CTO #e106b78b (x)"),
])
def test_strip_host_drops_one_leading_host_emoji(name, bare):
    assert sn.strip_host(name) == bare


def test_split_name_separates_the_state_glyph_the_host_and_the_body():
    assert sn.split_name("⏸ " + CONTABO + " CTO#c34 t") == ("⏸ ", CONTABO, "CTO#c34 t")
    assert sn.split_name(WINBOX + " PH#f35 x") == ("", "\U0001F5A5", "PH#f35 x")
    assert sn.split_name("CTO#c34 t") == ("", "", "CTO#c34 t")
    assert sn.split_name("") == ("", "", "")


@pytest.mark.parametrize("name", [
    CONTABO + " PH#f35 CookieRun", WINBOX + " PH#f35 CookieRun", "\U0001F5A5 PH#f35 CookieRun",
    "PH#f35 CookieRun", CONTABO + " PH#f35 (CTO) - CookieRun"])
def test_a_ph_name_parses_with_any_emoji_or_none_in_either_shape(name):
    assert sn.parse_short(name) == ("project_head", "f35")


def test_the_cli_prints_only_a_known_hosts_emoji_and_the_launchers_birth_names():
    import subprocess
    cli = lambda *a: subprocess.run([sys.executable, str(ROOT / "lib" / "session_names.py"), *a],
                                    capture_output=True)
    assert cli("prefix", "contabo").stdout == CONTABO.encode()
    assert cli("prefix", "winbox").stdout == WINBOX.encode()
    assert cli("prefix", "guess").stdout == b"" and cli("prefix", "guess").returncode == 0
    assert cli("clevel", "cto", "c34459eb", "contabo").stdout.decode() == f"{CONTABO} CTO#c34 Main"
    assert cli("clevel", "coo", "fde4c4ca", "mac", "SomPong").stdout.decode() == f"{MAC} COO SomPong"
    assert cli("ph", "7cf528f0", "contabo", "OrgRestructure").stdout.decode() == f"{CONTABO} PH#7cf OrgRestructure"
    for bad in (("clevel", "ceo", "c34459eb", "contabo"), ("ph", "7cf528f0", "contabo", "a b"),
                ("ph", "7cf528f0", "contabo", "x;rm"), ("clevel", "cto")):
        r = cli(*bad)
        assert r.returncode == 2 and r.stdout == b""


# --- M10 + N2: rule_problem, the validator live-sessions flags names with -----------------

@pytest.mark.parametrize("name,role,sid,host,why", [
    # the new shape, on the rule
    (CONTABO + " CTO#c34 Main", "cto", "c34459eb", "contabo", None),
    ("⏸ " + CONTABO + " CTO#c34 t", "cto", "c34459eb", "contabo", None),
    (WINBOX + " CTO#c34 Main", "cto", "c34459eb", "winbox", None),
    ("\U0001F5A5 CTO#c34 Main", "cto", "c34459eb", "winbox", None),                  # typed, no FE0F
    ("CTO#c34 Main", "cto", "c34459eb", "nowhere", None),                             # unknown host: none
    (CONTABO + " COO SomPong", "coo", "fde4c4ca", "contabo", None),
    (CONTABO + " PH#7cf OrgRestructure", "project_head", "7cf528f0", "contabo", None),
    (CONTABO + " PH#7cf test", "project_head", "7cf528f0", "contabo", None),
    (CONTABO + " PH#671 LastBell+Scriptable", "project_head", "671f688f", "contabo", None),
    (f"Browser.S#4a5 Mimi: x", "browser_operator", "4a59a1a4", "winbox", None),
    (f"{CONTABO} Dev{DOT}S#49b Org: sparse worktrees", "developer", "49b1d2e3", "contabo", None),
    (f"{CONTABO} Dev#49b Org: x", "developer", "49b1d2e3", "contabo", None),          # a model with no letter
    ("anything", "unknown", "x", "contabo", None),
    ("anything", "watch", "x", "contabo", None),
    ("CEO", "ceo", "x", "contabo", None),
    # the old shapes: "old shape", whatever else they lack
    ("CTO (Kavin)", "cto", "c34459eb", "contabo", "old shape"),
    (CONTABO + " CTO (Kavin)", "cto", "c34459eb", "contabo", "old shape"),
    (CONTABO + " CTO (Kavin) — CTO Main", "cto", "c34459eb", "contabo", "old shape"),
    (CONTABO + " CFO", "cfo", "x", "contabo", "old shape"),
    (CONTABO + " COO (SomPong)", "coo", "fde4c4ca", "contabo", "old shape"),
    ("CONTABO CTO #e106b78b (x)", "cto", "e106b78b", "contabo", "old shape"),
    (MAC + " MAC CTO #671f688f (PH LastBell + Scriptable)", "cto", "671f688f", "mac", "old shape"),
    (CONTABO + " PH#7cf (CTO) - OrgRestructure — M10", "project_head", "7cf528f0", "contabo", "old shape"),
    ("PH#36c (CMO) - MimiPage", "project_head", "36c49776", "contabo", "old shape"),
    (CONTABO + " Dev#afe - OrgRestructure: x", "developer", "afe57b21", "contabo", "old shape"),
    ("Browser#4a5 - MimiPage: x", "browser_operator", "4a59a1a4", "winbox", "old shape"),
    # the new shape, off the rule
    ("CTO#c34 Main", "cto", "c34459eb", "contabo", "no host emoji"),
    (MAC + " CTO#c34 Main", "cto", "c34459eb", "contabo", "wrong host emoji"),
    (CONTABO + " CMO#c34 Main", "cto", "c34459eb", "contabo", 'not "CTO#<id3> <topic>"'),
    (CONTABO + " CTO#c34", "cto", "c34459eb", "contabo", 'not "CTO#<id3> <topic>"'),
    (CONTABO + " CTO Main", "cto", "c34459eb", "contabo", 'not "CTO#<id3> <topic>"'),
    (CONTABO + " CTO#abc Main", "cto", "c34459eb", "contabo", "CTO#abc is not this session (#c34)"),
    (CONTABO + " COO#a7e SomPong", "coo", "a7eb4963", "contabo", 'not "COO <topic>"'),
    (CONTABO + " PH#abc X", "project_head", "7cf528f0", "contabo", "PH#abc is not this session (#7cf)"),
    (CONTABO + " Project Head #7cf528f0", "project_head", "7cf528f0", "contabo", 'not "PH#<id3> <Project>"'),
    (WINBOX + " Browser.S#4a5 M: x", "browser_operator", "4a59a1a4", "winbox", "a host emoji where none belongs"),
    (CONTABO + " Test.S#afe x", "developer", "afe57b21", "contabo", 'not "Dev·<O|S|H>#<id3> <Head>: <job>"'),
    (CONTABO + f" Dev{DOT}S#afe Org: " + "x" * 30, "developer", "afe57b21", "contabo",
     "body is 45 characters (max 32)"),
    (CONTABO + " CTO#c34 " + "x" * 25, "cto", "c34459eb", "contabo", "body is 33 characters (max 32)"),
    (CONTABO + " CTO#c34 " + "x" * 24, "cto", "c34459eb", "contabo", None),              # 32 is the edge
])
def test_rule_problem(name, role, sid, host, why):
    assert sn.rule_problem(name, role, sid, host, windows=(host == "winbox")) == why


def test_a_windows_worker_name_with_the_middle_dot_is_off_the_rule_and_the_other_way_round():
    assert sn.rule_problem(f"Dev{DOT}S#afe x", "developer", "afe57b21", "winbox", windows=True) == \
        'not "Dev.<O|S|H>#<id3> <Head>: <job>"'
    assert sn.rule_problem(CONTABO + " Dev.S#afe x", "developer", "afe57b21", "contabo") == \
        'not "Dev·<O|S|H>#<id3> <Head>: <job>"'


def test_every_name_the_writers_make_is_on_the_rule():
    assert sn.rule_problem(sn.ph_session_name("7cf528f0", "OrgRestructure", "contabo"),
                           "project_head", "7cf528f0", "contabo") is None
    assert sn.rule_problem(sn.clevel_name("cto", "c34459eb", "", "contabo"), "cto", "c34459eb", "contabo") is None
    assert sn.rule_problem(sn.clevel_name("coo", None, "", "contabo", "SomPong"), "coo", "fde4c4ca", "contabo") is None
    for host in ("mac", "contabo", "winbox"):
        name = config.worker_session_name(host, "developer", "task-afe57b21", "x" * 60, head="H" * 20)
        assert sn.rule_problem(name, "developer", "afe57b21", host, windows=(host == "winbox")) is None, name


# --- the topic readers the rename sweep rebuilds from ---------------------------------------

@pytest.mark.parametrize("name,role,topic", [
    ("CTO (Kavin) — CTO Main", "cto", "Main"),
    ("CTO (Kavin) — Item 5", "cto", "Item 5"),
    ("CTO (Kavin)", "cto", ""), ("CFO", "cfo", ""), ("COO (SomPong)", "coo", ""),
    ("MAC CTO #671f688f (PH LastBell + Scriptable)", "cto", "LastBell+Scriptable"),
    ("MAC CTO #671f688f", "cto", ""),
    ("CTO#c34 Main", "cto", "Main"), ("CTO#c34 Console fix", "cto", "Console fix"),
    ("COO SomPong", "coo", "SomPong"),
    ("my own label", "cto", "my own label"),                  # typed by hand: all topic
    ("CTO something", "cto", "something"),
])
def test_clevel_topic(name, role, topic):
    assert sn.clevel_topic(name, role) == topic


def test_ph_topic_and_worker_parts():
    assert sn.ph_topic("PH#7cf (CTO) - OrgRestructure") == ("OrgRestructure", "")
    assert sn.ph_topic("PH#6c4 (CMO) - MimiPage + B — a topic") == ("MimiPage+B", "a topic")
    assert sn.ph_topic("PH#7cf OrgRestructure") == ("", "OrgRestructure")
    assert sn.ph_topic("CTO#c34 Main") == ("", "")
    assert sn.worker_parts("Dev#49b - OrgRestructure: Item 5: sparse…") == ("Dev", "OrgRestructure", "Item 5: sparse…")
    assert sn.worker_parts(f"Dev{DOT}S#49b Org: sparse worktrees") == ("Dev", "Org", "sparse worktrees")
    assert sn.worker_parts("Dev#49b - Item 5: sparse") == ("Dev", "", "Item 5: sparse")   # "Item 5" is two words: no head
    assert sn.worker_parts("Dev#49b - fix the thing") == ("Dev", "", "fix the thing")
    assert sn.worker_parts("Dev#49b") == ("Dev", "", "")
    assert sn.worker_parts("CTO#c34 Main") is None
