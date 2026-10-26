"""Session-name shapes (CEO 2026-10-14, card QG-20261014-0326-8968; the 2026-10-15 ruling and plan N of
state/handoff/2026-10-15/plan-names-watch-macoff.md): lib/session_names.py writes and reads them; lib/config
re-exports the writers.

C-level "<ROLE> (<Name>) — <topic>" and PH "PH#<id3> (<LANE>) - <Project>" keep every part they have and are
never cut; workers "<Short>·<M>#<id3> <Head>: <job>" and Watch "Watch#<id3> Runs: <N><light>" are new names,
cut to 32 characters. Every reader takes the old, the compact and the ruling shapes."""
from __future__ import annotations

import sys
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
from lib import session_names as sn  # noqa: E402
from tools import node_dispatch  # noqa: E402


def _name_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "lib.session_names", *args], cwd=ROOT,
        capture_output=True, env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )


@pytest.mark.parametrize("role,persona", [("cto", "Kavin"), ("cmo", "Ging"), ("coo", "SomPong")])
def test_name_cli_clevel(role, persona):
    proc = _name_cli("name", "--host", "winbox", "--role", role, "--sid", "2c6b9f03")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.isascii() and len(proc.stdout.splitlines()) == 1
    assert json.loads(proc.stdout) == sn.clevel_name(role, persona, "winbox")


def test_name_cli_project_head():
    proc = _name_cli("name", "--host", "winbox", "--role", "project_head", "--sid", "ba3f3fe1",
                     "--lane", "cto", "--project", "CookieRun")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.isascii() and len(proc.stdout.splitlines()) == 1
    assert json.loads(proc.stdout) == sn.ph_session_name("ba3f3fe1", "cto", "CookieRun", "winbox")


@pytest.mark.parametrize("role,extra", [
    ("unknown", []), ("developer", []), ("project_head", []),
    ("project_head", ["--lane", "cto"]), ("project_head", ["--project", "CookieRun"]),
    ("project_head", ["--lane", " ", "--project", "CookieRun"]),
])
def test_name_cli_bad_input(role, extra):
    proc = _name_cli("name", "--host", "winbox", "--role", role, "--sid", "ba3f3fe1", *extra)
    assert proc.returncode == 2
    assert b"usage:" in proc.stderr
    assert proc.stdout == b""


@pytest.mark.parametrize("host", ["winbox", "mac", "contabo", "unknown"])
def test_prefix_module_cli_unchanged(host):
    proc = subprocess.run([sys.executable, "-m", "lib.session_names", "prefix", host],
                          cwd=ROOT, capture_output=True,
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert proc.returncode == 0
    assert proc.stdout.decode("utf-8") == sn.HOST_EMOJI.get(host, "")


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
    ("PH#6c4 CTO - x", ("project_head", "6c4")),     # a compact PH name: "PH#<id3> <text>"
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin)", ("cto", "")),
    ("Dev·S#afe Org: x", ("developer", "afe")), ("Dev.S#afe Org: x", ("developer", "afe")),
    ("Dev#afe Org: x", ("developer", "afe")),
    ("CTO#c34 Main", ("cto", "c34")), ("COO SomPong", ("coo", "")),
    ("PH#7cf OrgRestructure", ("project_head", "7cf")), ("Watch#a1b Runs: 2🟢", ("watch", "a1b")),
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main", ("cto", "")), ("CFO", ("cfo", "")),
    ("MAC CTO #671f688f (PH LastBell + Scriptable)", ("cto", "671")),
    ("CTO Main", None), ("CEO", None), ("CEO#c34 Main", None), ("Watch#a1b", None),
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
    assert not node_dispatch._PS_SESSION_NAME_RE.fullmatch("Dev·S#abc Org: x")     # the ASCII-only pattern stays


# --- M9: host emoji (CEO 2026-10-14, relayed by COO SomPong) ------------------------

MAC, CONTABO, WINBOX = "\U0001F4BB", "\U0001F310", "\U0001F5A5\uFE0F"


def test_the_host_emoji_table():
    assert sn.HOST_EMOJI == {"mac": MAC, "contabo": CONTABO, "winbox": WINBOX}
    assert sn.host_prefix("contabo") == CONTABO + " "
    for unknown in ("", None, "MAC", "laptop", "contabo "):
        assert sn.host_prefix(unknown) == ""


@pytest.mark.parametrize("name,bare", [
    (CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "CTO (\U0001F468\u200d\U0001F4BB: Kavin)"),
    (WINBOX + " PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"),
    ("\U0001F5A5 PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"),     # typed without FE0F
    (MAC + "Dev#afe - x", "Dev#afe - x"),                                    # no space
    ("PH#f35 (CTO) - CookieRun", "PH#f35 (CTO) - CookieRun"),               # no emoji
    ("\u23f8 " + CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin) \u2014 t", "\u23f8 CTO (\U0001F468\u200d\U0001F4BB: Kavin) \u2014 t"),  # state glyph kept
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
    assert sn.with_host("winbox", CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin)") == WINBOX + " CTO (\U0001F468\u200d\U0001F4BB: Kavin)"
    assert config.worker_session_name("contabo", "developer", "task-afe57b21", "x",
                                      head="OrgRestructure") == CONTABO + " Dev·S#afe Org: x"
    assert config.worker_session_name("nowhere", "developer", "task-afe57b21", "x") == "Dev.S#afe x"   # unknown: ASCII, no emoji


def test_a_windows_worker_name_has_no_emoji_and_still_passes_the_ascii_pattern():
    # winbox spawns cross cmd.exe (tools/delegate.py) and node_dispatch's ASCII-only
    # pattern; neither is widened for the emoji (M8's fullmatch stays as it was).
    name = config.worker_session_name("winbox", "browser_operator", "task-4a59a1a4",
                                      "SHOOT the teaser", head="MimiPage")
    assert name == "Browser.S#4a5 Mimi: SHOOT the..."      # "." for "·", "..." for "…": ASCII only, 32 characters
    assert name.isascii() and len(name) == 32
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
    (CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto", "c34459eb", "contabo", "Kavin", None),
    ("⏸ " + CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin) — t", "cto", "c34459eb", "contabo", "Kavin", None),
    (WINBOX + " CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto", "x", "winbox", "Kavin", None),
    ("\U0001F5A5 CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto", "x", "winbox", "Kavin", None),            # typed, no FE0F
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto", "x", "nowhere", "Kavin", None),                      # unknown host: none
    (CONTABO + " PH#7cf (CTO) - OrgRestructure — M10", "project_head", "7cf528f0", "contabo", None, None),
    ("Browser#4a5 - MimiPage: x", "browser_operator", "4a59a1a4", "winbox", None, None),         # old worker shape
    (CONTABO + " Dev#afe - OrgRestructure: x", "developer", "afe57b21", "contabo", None, None),
    ("Browser.S#4a5 Mimi: x", "browser_operator", "4a59a1a4", "winbox", None, None),            # compact worker shape
    (CONTABO + " Dev·S#49b Org: sparse worktrees", "developer", "49b1d2e3", "contabo", None, None),
    (CONTABO + " Dev#49b Org: x", "developer", "49b1d2e3", "contabo", None, None),             # a model with no letter
    (CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main", "cto", "c34459eb", "contabo", "Kavin", None),        # the CEO's own rename
    (CONTABO + " PH#7cf (CTO) - OrgRestructure", "project_head", "7cf528f0", "contabo", None, None),
    (CONTABO + " PH#13d (CMO) - BlackLiquidity — a topic that is longer than any cap could allow",
     "project_head", "13d90a1b", "contabo", None, None),                                          # no cap on a PH name
    (CONTABO + " CTO (\U0001F468\u200d\U0001F4BB: Kavin) — " + "t" * 80, "cto", "c34459eb", "contabo", "Kavin", None),     # nor on a C-level's
    (CONTABO + " CFO", "cfo", "x", "contabo", None, None),                                      # no persona: the bare role
    (CONTABO + " COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong)", "coo", "fde4c4ca", "contabo", "SomPong", None),
    (CONTABO + " CTO#c34 Main", "cto", "c34459eb", "contabo", "Kavin", None),                  # compact shapes are read too
    (CONTABO + " COO SomPong", "coo", "fde4c4ca", "contabo", "SomPong", None),
    (CONTABO + " PH#7cf OrgRestructure", "project_head", "7cf528f0", "contabo", None, None),
    ("anything", "unknown", "x", "contabo", None, None),
    ("CEO", "ceo", "x", "contabo", None, None),
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto", "x", "contabo", "Kavin", "no host emoji"),
    ("CONTABO CTO #e106b78b (x)", "cto", "e106b78b", "contabo", None, "no host emoji"),
    (MAC + " CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto", "x", "contabo", "Kavin", "wrong host emoji"),
    (CONTABO + " CMO (Ging)", "cto", "x", "contabo", None, 'not "CTO (<Name>)"'),
    (CONTABO + " CTO (Ging)", "cto", "x", "contabo", "Kavin", 'not "CTO (Kavin)"'),
    (CONTABO + " PH#abc (CTO) - X", "project_head", "7cf528f0", "contabo", None,
     "PH#abc is not this session (#7cf)"),
    (CONTABO + " PH#abc OrgRestructure", "project_head", "7cf528f0", "contabo", None,
     "PH#abc is not this session (#7cf)"),
    (CONTABO + " Project Head #7cf528f0", "project_head", "7cf528f0", "contabo", None,
     'not "PH#<id3> (<LANE>) - <Project>"'),
    (WINBOX + " Browser#4a5 - M: x", "browser_operator", "4a59a1a4", "winbox", None,
     "a host emoji where none belongs"),
    (WINBOX + " Browser.S#4a5 M: x", "browser_operator", "4a59a1a4", "winbox", None,
     "a host emoji where none belongs"),
    (CONTABO + " Test#afe - x", "developer", "afe57b21", "contabo", None,
     'not "Dev·<O|S|H>#<id3> <Head>: <job>"'),
    (CONTABO + " Dev·S#afe Org: " + "x" * 30, "developer", "afe57b21", "contabo", None,
     "body is 45 characters (max 32)"),                                  # a new worker name is cut ...
    (CONTABO + " Dev#afe - OrgRestructure: " + "x" * 60, "developer", "afe57b21", "contabo", None, None),  # ... an old one is not
    (CONTABO + " Dev·S#abc Org: x", "developer", "afe57b21", "contabo", None, "Dev#abc is not this session (#afe)"),
    ("CTO#c34 Main", "cto", "c34459eb", "contabo", None, "no host emoji"),
    (CONTABO + " CTO#abc Main", "cto", "c34459eb", "contabo", None, "CTO#abc is not this session (#c34)"),
    (CONTABO + " CTO Main", "cto", "c34459eb", "contabo", None, 'not "CTO#<id3> <topic>"'),
    (CONTABO + " COO#a7e SomPong", "coo", "a7eb4963", "contabo", None, 'not "COO <topic>"'),
    (CONTABO + " CTO (Kavin)", "cfo", "x", "contabo", None, 'not "CFO (<Name>)"'),
])
def test_rule_problem(name, role, sid, host, persona, why):
    assert sn.rule_problem(name, role, sid, host, persona=persona,
                           windows=(host == "winbox")) == why


def test_every_name_the_writers_make_is_on_the_rule():
    assert sn.rule_problem(config.ph_session_name("7cf528f0", "cto", "OrgRestructure", "contabo"),
                           "project_head", "7cf528f0", "contabo") is None
    assert sn.rule_problem(sn.clevel_name("cto", "Kavin", "contabo"), "cto", "c34459eb", "contabo",
                           persona="Kavin") is None
    assert sn.rule_problem(sn.clevel_name("cfo", "", "mac"), "cfo", "x", "mac") is None
    for host in ("mac", "contabo", "winbox"):
        for job, head in (("x", "H"), ("x" * 60, "H" * 20)):
            name = config.worker_session_name(host, "developer", "task-afe57b21", job, head=head)
            assert sn.rule_problem(name, "developer", "afe57b21", host,
                                   windows=(host == "winbox")) is None, name


# --- N1: the writers (CEO ruling 2026-10-15: C-level and PH as before; compact for workers and Watch) ----

DOT = "·"


def body(name: str) -> str:
    return sn.split_name(name)[2]


@pytest.mark.parametrize("made,expect", [
    (lambda: sn.clevel_name("cto", "Kavin", "contabo"), f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin)"),
    (lambda: sn.clevel_name("cmo", "Ging", "mac"), f"{MAC} CMO (\U0001F469\U0001F3FB\u200d\U0001F3A8: Ging)"),
    (lambda: sn.clevel_name("coo", "SomPong", "contabo"), f"{CONTABO} COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong)"),
    (lambda: sn.clevel_name("cfo", "", "contabo"), f"{CONTABO} CFO"),
    (lambda: sn.clevel_name("cto", "Kavin"), "CTO (\U0001F468\u200d\U0001F4BB: Kavin)"),
    (lambda: sn.ph_session_name("7cf528f0", "cto", "OrgRestructure", "contabo"), f"{CONTABO} PH#7cf (CTO) - OrgRestructure"),
    (lambda: sn.worker_name("Dev", "task-49b1d2e3", "OrgRestructure", "sparse worktrees", "claude-sonnet-5-5"),
     f"Dev{DOT}S#49b Org: sparse worktrees"),
    (lambda: sn.worker_name("Sec", "task-afe57b21", "SpendGuard", "audit", "claude-opus-5-5[1m]"),
     f"Sec{DOT}O#afe Spend: audit"),
    (lambda: sn.worker_name("Res", "afe57b21", "CTO", "x", "claude-haiku-4-5-20251001"), f"Res{DOT}H#afe CTO: x"),
    (lambda: sn.worker_name("Dev", "afe57b21", "CTO", "x", "glm-5.2"), "Dev#afe CTO: x"),   # no letter for another model
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
def test_N1_a_new_worker_name_is_at_most_32_characters_and_a_cut_marks_itself(total, cut):
    name = sn.worker_name("Dev", "afe57b21", "", "x" * (total - 10), "S")      # "Dev·S#afe " is 10 characters
    assert len(body(name)) == min(total, sn.NAME_BODY_MAX)
    assert body(name).endswith("…") == cut
    if cut:
        assert body(name) == "Dev·S#afe " + "x" * 21 + "…"


@pytest.mark.parametrize("n,cut", [(5, False), (12345678901234567890, True)])
def test_N1_a_watch_name_is_cut_the_same_way(n, cut):
    name = sn.watch_name("a1b00000", n, "\U0001F7E2", "contabo")
    assert len(body(name)) <= sn.NAME_BODY_MAX and body(name).endswith("…") == cut


def test_N1_a_windows_worker_name_is_ascii_only_with_no_emoji_and_cuts_with_dots():
    name = config.worker_session_name("winbox", "browser_operator", "task-4a59a1a4",
                                      "SHOOT the teaser", head="MimiPage")
    assert name == "Browser.S#4a5 Mimi: SHOOT the..." and name.isascii() and len(name) == 32
    assert node_dispatch._PS_SESSION_NAME_RE.fullmatch(name)
    assert not node_dispatch._PS_SESSION_NAME_RE.fullmatch(WINBOX + " " + name)
    short = config.worker_session_name("winbox", "developer", "task-49b1d2e3", "sparse worktrees",
                                       head="OrgRestructure")
    assert short == "Dev.S#49b Org: sparse worktrees" and node_dispatch._PS_SESSION_NAME_RE.fullmatch(short)


def test_N1_a_c_level_or_ph_name_is_never_cut():
    long_project = "P" * 40
    ph = sn.ph_session_name("7cf528f0", "cto", long_project, "contabo")
    assert body(ph) == f"PH#7cf (CTO) - {long_project}" and len(body(ph)) > sn.NAME_BODY_MAX
    assert "…" not in ph


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
    assert config.worker_session_name("nowhere", "developer", "task-afe57b21", "x") == "Dev.S#afe x"


# --- N2: the 11 live names of 15 Oct 04:42 TH, as the CEO keeps them ----------------------------------------
# (name, registry role, sid, host, persona).  Under the ruling an existing name keeps every part: with its host
# emoji it is on the rule exactly as it is, and without one the emoji is the only thing missing.

N2_ROWS = [
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main", "cto", "c34459eb", "contabo", "Kavin"),
    ("CMO (\U0001F469\U0001F3FB\u200d\U0001F3A8: Ging) — CMO Main", "cmo", "ef04792e", "contabo", "Ging"),
    ("COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong)", "coo", "fde4c4ca", "contabo", "SomPong"),
    ("PH#7cf (CTO) - OrgRestructure", "project_head", "7cf528f0", "contabo", None),
    ("PH#6c4 (CTO) - SpendGuard", "project_head", "6c487e37", "contabo", None),
    ("PH#f35 (CTO) - CookieRun", "project_head", "f35c0ffe", "contabo", None),
    ("PH#13d (CMO) - BlackLiquidity", "project_head", "13db8720", "contabo", None),
    ("PH#36c (CMO) - MimiPage", "project_head", "36c49776", "contabo", None),
    ("Dev#49b - OrgRestructure: Item 5: sparse worktrees for the hub and more tex…", "developer", "49b1d2e3", "contabo", None),
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin) — PH LastBell + Scriptable", "cto", "671f688f", "mac", "Kavin"),
    ("PH#f39 (CTO) - LuminaSkies — V2.6 push + M-R", "project_head", "f39cb080", "mac", None),
]


@pytest.mark.parametrize("name,role,sid,host,persona", N2_ROWS, ids=[r[0][:28] for r in N2_ROWS])
def test_N2_an_existing_name_is_on_the_rule_once_it_has_its_emoji_and_needs_nothing_else(name, role, sid, host, persona):
    emoji = sn.HOST_EMOJI[host]
    assert sn.rule_problem(name, role, sid, host, persona=persona) == "no host emoji"
    assert sn.rule_problem(f"{emoji} {name}", role, sid, host, persona=persona) is None
    assert sn.rule_problem(f"⏸ {emoji} {name}", role, sid, host, persona=persona) is None    # a state glyph leads
    assert sn.strip_host(f"{emoji} {name}") == name                                         # adding the emoji adds nothing else
    assert sn.with_host(host, name) == f"{emoji} {name}"


@pytest.mark.parametrize("name,role,sid,expect", [
    ("CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main", "cto", "c34459eb", ("cto", "")),
    ("PH#7cf (CTO) - OrgRestructure", "project_head", "7cf528f0", ("project_head", "7cf")),
    ("Dev#49b - OrgRestructure: Item 5", "developer", "49b1d2e3", ("developer", "49b")),
    (f"Dev{DOT}S#49b Org: Item 5", "developer", "49b1d2e3", ("developer", "49b")),
    ("CTO#c34 Main", "cto", "c34459eb", ("cto", "c34")),
    ("PH#7cf OrgRestructure", "project_head", "7cf528f0", ("project_head", "7cf")),
])
def test_N2_old_compact_and_ruling_shapes_all_parse_and_pass_the_rule(name, role, sid, expect):
    assert sn.parse_short(name) == expect
    assert sn.rule_problem(CONTABO + " " + name, role, sid, "contabo") is None


def test_N2_the_old_long_form_is_not_on_the_rule_and_the_sweep_never_rebuilds_it():
    long_form = CONTABO + " MAC CTO #671f688f (PH LastBell + Scriptable)"
    assert sn.rule_problem(long_form, "cto", "671f688f", "mac", persona="Kavin") == "wrong host emoji"
    assert sn.rule_problem(MAC + " MAC CTO #671f688f (PH LastBell + Scriptable)", "cto", "671f688f", "mac",
                           persona="Kavin") == 'not "CTO (Kavin)"'
