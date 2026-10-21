"""tools/whois.py (OrgMesh P8): who sent this message, checked against the hub's live_sessions rows.

No hub, no ssh, no files: `check()` and `resolve()` take rows, and `main()` is run with
`whois._snapshot` replaced, so the one thing the hub would give is a list of dicts shaped like
`live_sessions._snapshot_from_hub(...)["rows"]`.
"""
from __future__ import annotations

import json

import pytest

from tools import live_sessions as ls
from tools import whois

OWNER = "671f688f"
OWNER_NAME = "🌐 CTO (Kavin) — CTO Main"


def row(name=OWNER_NAME, role="cto", sid=OWNER, host="contabo", uuid=None, verified=True, stale=False):
    return {"host": host, "uuid": uuid or f"11111111-2222-3333-4444-5555{sid}", "sid": sid, "role": role,
            "name": name, "address": name, "status": "stale" if stale else "running", "pid": 1,
            "verified": verified, "age": 4.0, "stale": stale}


ROWS = [
    row(),
    row("💻 CMO (Ging)", role="cmo", sid="ef04792e", host="mac"),
    row("🌐 PH#7cf (CTO) - OrgRestructure", role="project_head", sid="7cf528f0"),
]


@pytest.fixture
def hub(monkeypatch):
    """whois.main() reads rows from `whois._snapshot`: hand it a list, or an exception to raise."""
    def serve(rows):
        def snap():
            if isinstance(rows, BaseException):
                raise rows
            return rows
        monkeypatch.setattr(whois, "_snapshot", snap)
    return serve


# --- resolving ---------------------------------------------------------------

@pytest.mark.parametrize("query", [
    OWNER_NAME,                       # the address, verbatim
    "CTO (Kavin) — CTO Main",         # no host emoji
    "cto (kavin) — cto main",         # case
    "  🌐   CTO (Kavin)  —  CTO Main ",   # spaces
    "⏸ 🌐 CTO (Kavin) — CTO Main",    # a state glyph in front
    OWNER, f"#{OWNER}", f"cto-{OWNER}", "11111111-2222-3333-4444-5555" + OWNER,
])
def test_one_session_resolves_by_name_or_by_id(query):
    got = whois.check(ROWS, query)
    assert got["ok"] is True, got
    [m] = got["matches"]
    assert (m["host"], m["role"], m["sid"], m["title"]) == ("contabo", "cto", OWNER, OWNER_NAME)
    assert m["uuid"] == f"11111111-2222-3333-4444-5555{OWNER}"
    assert (m["alive"], m["c_level"], m["tmux_claimed"], m["claims"]) == (True, True, True, None)


def test_no_match():
    for q in ("CTO (Nobody)", "deadbeef", "cto", "1234567", ""):   # 7 hex is not an id
        got = whois.check(ROWS, q, owner=OWNER)
        assert got["ok"] is False and got["why"].startswith("no match") and got["matches"] == [], q


def test_a_project_head_is_not_a_c_level_and_a_name_with_no_id_in_it_still_resolves():
    [m] = whois.check(ROWS, "PH#7cf (CTO) - OrgRestructure")["matches"]
    assert (m["role"], m["c_level"], m["sid"]) == ("project_head", False, "7cf528f0")


def test_two_sessions_with_one_name_are_ambiguous_and_the_copy_blocks_the_real_owner_too():
    copy = row(OWNER_NAME, role="unknown", sid="0badc0de", verified=False)
    got = whois.check(ROWS + [copy], OWNER_NAME, owner=OWNER)
    assert got["ok"] is False and got["why"].startswith("ambiguous: 2 live sessions")
    assert "contabo #671f688f" in got["why"] and "contabo #0badc0de" in got["why"]
    assert len(got["matches"]) == 2


def test_the_same_name_on_two_hosts_is_ambiguous():
    got = whois.check([row("CTO (Kavin)"), row("CTO (Kavin)", host="mac", sid="f39cb080")], "CTO (Kavin)")
    assert got["ok"] is False and "contabo #671f688f" in got["why"] and "mac #f39cb080" in got["why"]


# --- --owner -----------------------------------------------------------------

@pytest.mark.parametrize("owner", [OWNER, f"cto-{OWNER}", f"#{OWNER.upper()}",
                                   "11111111-2222-3333-4444-5555" + OWNER, "11111111-2222-3333"])
def test_the_owner_is_confirmed_by_the_session_uuid(owner):
    got = whois.check(ROWS, OWNER_NAME, owner=owner)
    assert got["ok"] is True and got["why"] == "owner confirmed: contabo #671f688f"


def test_another_sessions_name_is_not_the_owner():
    got = whois.check(ROWS, "💻 CMO (Ging)", owner=OWNER)
    assert got["ok"] is False and got["why"].startswith("id differs") and "mac #ef04792e" in got["why"]


def test_a_forged_name_cannot_carry_the_owners_id():
    """A session no launcher tmux claims gets its `sid` from its own name ("... #671f688f"): the owner
    check reads the UUID, which the name does not set."""
    forged = row("MAC CTO #671f688f (hello)", role="unknown", sid=OWNER, host="mac",
                 uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", verified=False)
    got = whois.check([forged], "MAC CTO #671f688f (hello)", owner=OWNER)
    assert got["ok"] is False and got["why"].startswith("id differs")
    assert whois.check([forged], OWNER)["matches"] == []     # and the id alone does not find it


def test_a_dead_owner_is_not_the_owner():
    got = whois.check([row(stale=True)], OWNER_NAME, owner=OWNER)
    assert got["ok"] is False and got["why"].startswith("not alive")
    assert got["matches"][0]["alive"] is False
    assert whois.check([row(stale=True)], OWNER_NAME)["ok"] is True      # plain whois reports, owner decides


@pytest.mark.parametrize("owner", ["", "1234567", "cto-1234567", "not-an-id", "zzzzzzzz"])
def test_an_owner_id_shorter_than_8_hex_or_not_hex_never_confirms(owner):
    got = whois.check(ROWS, OWNER_NAME, owner=owner)
    assert got["ok"] is False and "at least 8 hex" in got["why"]


def test_a_title_claim_is_reported_for_a_row_that_is_not_that_c_level():
    liar = row("🌐 Dev·S#49b Org — CTO Main", role="unknown", sid="49b00000", verified=False)
    [m] = whois.check([liar], "Dev·S#49b Org — CTO Main")["matches"]
    assert m["claims"] == "CTO Main" and m["c_level"] is False and m["tmux_claimed"] is False
    assert "WARNING: the title says CTO Main but the role is unknown" in whois.format_text(
        whois.check([liar], "Dev·S#49b Org — CTO Main"))


# --- the command ---------------------------------------------------------------

def test_exit_0_only_for_the_owner(hub, capsys):
    hub(ROWS)
    assert whois.main([OWNER_NAME, "--owner", f"cto-{OWNER}"]) == 0
    assert "owner: YES — owner confirmed: contabo #671f688f" in capsys.readouterr().out
    for args in ([OWNER_NAME, "--owner", "ef04792e"],           # id differs
                 ["💻 CMO (Ging)", "--owner", OWNER],             # a real session, not the owner
                 ["CTO (Nobody)", "--owner", OWNER],              # no match
                 [OWNER_NAME, "--owner", "short"]):               # not an id
        assert whois.main(args) == 1, args
        assert "owner: NO — " in capsys.readouterr().out


def test_exit_1_when_the_hub_cannot_be_read_and_nothing_secret_is_printed(hub, capsys):
    hub(ls.HubUrlUnset())
    assert whois.main([OWNER_NAME, "--owner", OWNER]) == 1
    out = capsys.readouterr().out
    assert "hub unreachable (HubUrlUnset): cannot verify" in out and "owner: NO" in out
    hub(RuntimeError("postgresql://user:NOT-A-PASSWORD@hub.invalid/db"))
    assert whois.main([OWNER_NAME]) == 1
    out = capsys.readouterr().out
    assert "NOT-A-PASSWORD" not in out and "hub.invalid" not in out and "RuntimeError" in out


def test_plain_whois_prints_the_fields_and_exits_0_for_one_match(hub, capsys):
    hub(ROWS)
    assert whois.main([OWNER_NAME]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "host: contabo", "role: cto (C-level)", "sid: 671f688f",
        "uuid: 11111111-2222-3333-4444-5555671f688f", f"title: {OWNER_NAME}", "alive: yes",
        "tmux-claimed: yes", "", "whois: YES — one live session"]
    assert whois.main(["CTO (Nobody)"]) == 1


def test_json_carries_the_verdict_and_the_matches(hub, capsys):
    hub(ROWS)
    assert whois.main([OWNER_NAME, "--owner", OWNER, "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["why"] == "owner confirmed: contabo #671f688f"
    assert out["matches"][0]["uuid"].endswith(OWNER) and out["matches"][0]["c_level"] is True
    assert whois.main(["CTO (Nobody)", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["matches"] == []
