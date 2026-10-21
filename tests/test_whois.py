"""tools/whois.py (OrgMesh P8c): is this message from my owner? Checked against the hub's live_sessions rows.

No hub, no ssh: `verify_owner()` and `lookup()` take rows, and `main()` is run with `whois._snapshot`
and `whois._here` replaced, so the one thing the hub would give is a list of dicts shaped like
`live_sessions._snapshot_from_hub(...)["rows"]`. The launcher's .uuid lock is a real file in tmp_path.

The verdict never reads a name (the sender chooses it); the probes of the second review are in
tests/test_whois_probes.py.
"""
from __future__ import annotations

import json

import pytest

from tools import live_sessions as ls
from tools import whois

OWNER = "671f688f"
OWNER_UUID = f"3c1d9e2a-5b7f-4e01-9a2b-c0de{OWNER}"
OWNER_NAME = "🌐 CTO (Kavin) — CTO Main"
OWNER_PID = 4242
UDS = f"uds:/tmp/cc-socks-0/{OWNER_PID}.sock"


def row(name=OWNER_NAME, role="cto", sid=OWNER, host="contabo", uuid=None, verified=True, stale=False,
        pid=OWNER_PID):
    return {"host": host, "uuid": uuid or f"11111111-2222-3333-4444-5555{sid}", "sid": sid, "role": role,
            "name": name, "address": name, "status": "stale" if stale else "running", "pid": pid,
            "verified": verified, "age": 4.0, "stale": stale}


def owner_row(**kw):
    return row(uuid=OWNER_UUID, **kw)


ROWS = [
    owner_row(),
    row("💻 CMO (Ging)", role="cmo", sid="ef04792e", host="mac", pid=777),
    row("🌐 PH#7cf (CTO) - OrgRestructure", role="project_head", sid="7cf528f0", pid=900),
]


@pytest.fixture
def locks(tmp_path, monkeypatch):
    """state/locks as live_sessions reads it; the owner's launcher has written its .uuid file."""
    monkeypatch.setattr(ls, "LOCKS_DIR", tmp_path)
    (tmp_path / f"cto-{OWNER}.uuid").write_text(OWNER_UUID + "\n")
    return tmp_path


@pytest.fixture
def hub(monkeypatch, locks):
    """whois.main() reads rows from `whois._snapshot` on host `whois._here()`."""
    def serve(rows, here="contabo"):
        def snap():
            if isinstance(rows, BaseException):
                raise rows
            return rows
        monkeypatch.setattr(whois, "_snapshot", snap)
        monkeypatch.setattr(whois, "_here", lambda: here)
    return serve


def verdict(rows, from_=UDS, owner=OWNER_UUID, role="cto", here="contabo"):
    return whois.verify_owner(rows, owner, whois.parse_from(from_), here, role)


# --- --from: only two shapes ---------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("uds:/tmp/cc-socks/3097.sock", ("uds", "3097")),
    ("uds:/tmp/cc-socks-0/2003810.sock", ("uds", "2003810")),
    ("uds:/tmp/cc-socks-1000/7.sock", ("uds", "7")),
    ("bridge:session_01BAWu5etWFPGhMoysn1KQyj", ("bridge", "01BAWu5etWFPGhMoysn1KQyj")),
])
def test_the_two_accepted_shapes(text, want):
    assert whois.parse_from(text) == want


@pytest.mark.parametrize("text", [
    "", " uds:/tmp/cc-socks/3097.sock", "uds:/tmp/cc-socks/3097.sock ", "uds:/tmp/cc-socks/3097.sock\n",
    "uds:/tmp/cc-socks/3097.sock;id", "uds:/tmp/cc-socks/3097.sock$(id)", "uds:/tmp/cc-socks/3097.sock'x",
    'uds:/tmp/cc-socks/3097.sock"', "uds:/tmp/cc-socks/`id`.sock", "uds:/tmp/cc-socks/3097.sock && id",
    "uds:/tmp/cc-socks/../etc/1.sock", "uds:/tmp/cc-socks//3097.sock", "uds:/tmp/cc-socks-/3097.sock",
    "uds:/tmp/cc-socks-a/3097.sock", "uds:/tmp/other/3097.sock", "uds:/tmp/cc-socks/3097.sockx",
    "uds:/tmp/cc-socks/abc.sock", "uds:/tmp/cc-socks/٣٠٩٧.sock", "uds:/tmp/cc-socks-٠/3097.sock",
    "uds:/tmp/cc-socks/0.sock", f"uds:/tmp/cc-socks/{2 ** 31}.sock", "uds:/tmp/cc-socks/12345678901.sock",
    "UDS:/tmp/cc-socks/3097.sock", "uds:/tmp/cc-socks/3097.sock\x00",
    "bridge:session_", "bridge:session_ab cd", "bridge:session_ab;id", "bridge:session_ab-cd",
    "bridge:session_é", "bridge:sessionab", "bridge:session_" + "a" * 101, "bridge:session_x\n",
    "🌐 CTO (Kavin) — CTO Main", "-h", "--help", "tcp:1.2.3.4:80",
])
def test_anything_else_is_not_accepted(text):
    assert whois.parse_from(text) is None


def test_a_from_that_is_not_text_is_not_accepted():
    assert whois.parse_from(None) is None and whois.parse_from(3097) is None


# --- the owner verdict: the transport, not the name ---------------------------------

def test_the_owner_is_the_row_on_this_host_with_the_senders_pid(locks):
    got = verdict(ROWS)
    assert got["ok"] is True and got["why"] == "owner confirmed: contabo pid 4242 is cto #671f688f"
    [m] = got["matches"]
    assert (m["host"], m["pid"], m["uuid"]) == ("contabo", OWNER_PID, OWNER_UUID)


def test_a_session_with_another_pid_is_not_the_owner_whatever_it_is_called(locks):
    """F4: the attacker copies the owner's exact name and sends, then renames away. The verdict never
    reads the name, so nothing to race: its pid is its pid."""
    attacker = row(OWNER_NAME, role="unknown", sid="0badc0de", verified=False, pid=5151,
                   uuid="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
    got = verdict([owner_row(), attacker], from_="uds:/tmp/cc-socks-0/5151.sock")
    assert got["ok"] is False and got["why"].startswith("id differs") and "unknown #0badc0de" in got["why"]
    renamed = {**attacker, "name": "Helper", "address": "Helper"}
    assert verdict([owner_row(), renamed], from_="uds:/tmp/cc-socks-0/5151.sock")["ok"] is False


def test_no_row_on_this_host_has_that_pid(locks):
    got = verdict(ROWS, from_="uds:/tmp/cc-socks-0/31337.sock")
    assert got["ok"] is False and got["why"] == "no match: no live session on contabo has pid 31337"
    assert got["matches"] == []


def test_the_pid_is_read_on_this_host_only(locks):
    """pids repeat across hosts: the owner's pid on another host's row is not this host's socket."""
    elsewhere = [owner_row(host="mac")]
    assert verdict(elsewhere, here="contabo")["ok"] is False
    assert verdict(elsewhere, here="mac")["ok"] is True


def test_two_rows_with_one_pid_are_ambiguous(locks):
    twin = row("x", role="unknown", sid="0badc0de", uuid="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
               verified=False, pid=OWNER_PID)
    got = verdict([owner_row(), twin])
    assert got["ok"] is False and got["why"].startswith("ambiguous: 2 rows on contabo claim pid 4242")


@pytest.mark.parametrize("minted", ["00000000-0000-4000-8000-0000671f688f",     # ends in the id
                                    "671f688f-0000-4000-8000-000000000000"])     # starts with it
def test_a_uuid_that_only_starts_or_ends_with_the_owners_id_is_not_the_owner(locks, minted):
    """F5: the whole UUID is compared. 32 known bits are not a secret."""
    fake = row("Helper", role="cto", uuid=minted, verified=True, host="contabo", pid=6000)
    got = verdict([owner_row(), fake], from_="uds:/tmp/cc-socks-0/6000.sock")
    assert got["ok"] is False and got["why"].startswith("id differs")


def test_the_owner_uuid_is_compared_whatever_its_case(locks):
    assert verdict(ROWS, owner=OWNER_UUID.upper())["ok"] is False      # the CLI lowercases it first
    assert whois.parse_args(["--owner", OWNER_UUID.upper(), "--from", UDS]).owner == OWNER_UUID


def test_a_dead_owner_is_not_the_owner(locks):
    got = verdict([owner_row(stale=True)])
    assert got["ok"] is False and got["why"].startswith("not alive")


def test_a_row_no_launcher_tmux_claims_is_not_the_owner(locks):
    """F5: the role of an unclaimed row is read from its name, which any session can set."""
    got = verdict([owner_row(verified=False)])
    assert got["ok"] is False and got["why"].startswith("not verified: no launcher tmux claims")


def test_the_row_must_hold_the_owners_c_level_role(locks):
    assert verdict([owner_row(role="cmo")])["why"] == "role differs: that session is cmo, the owner is a cto"
    assert verdict([owner_row(role="project_head")])["ok"] is False
    assert verdict([owner_row(role="developer")], role=None)["why"] == \
        "role differs: that session is developer, the owner is a C-level"
    assert verdict([owner_row(role="cmo")], role=None)["ok"] is False      # no .uuid lock for cmo-671f688f


def test_the_launchers_uuid_lock_must_name_the_session(locks):
    (locks / f"cto-{OWNER}.uuid").write_text("99999999-9999-4999-8999-999999999999\n")
    got = verdict(ROWS)
    assert got["ok"] is False and got["why"] == "not verified: the launcher's .uuid lock does not name that session"
    (locks / f"cto-{OWNER}.uuid").unlink()
    assert verdict(ROWS)["ok"] is False                                   # no lock at all: fail closed


def test_a_bridge_sender_cannot_be_verified_because_the_hub_keeps_no_bridge_id(locks):
    for sender in ("bridge:session_01BAWu5etWFPGhMoysn1KQyj", f"bridge:session_{OWNER}"):
        got = verdict(ROWS, from_=sender)
        assert got["ok"] is False and got["why"].startswith("cannot verify: a bridge: sender"), got
        assert got["matches"] == []


def test_the_title_is_never_in_a_verdict(locks):
    text = whois.format_text(verdict(ROWS))
    assert "title:" not in text and OWNER_NAME not in text
    assert text.splitlines()[-1] == "owner: YES — owner confirmed: contabo pid 4242 is cto #671f688f"


# --- owner id -> full uuid (what spawn_ph writes into the brief) -----------------------

def test_owner_candidates_are_live_launcher_claimed_rows_of_that_role_and_id():
    rows = [owner_row(), owner_row(host="mac", verified=False), owner_row(role="cmo"),
            owner_row(stale=True), row(sid="deadbeef", role="cto")]
    assert [r["uuid"] for r in whois.owner_candidates(rows, "cto", OWNER)] == [OWNER_UUID]
    assert whois.owner_candidates(rows[1:], "cto", OWNER) == []


# --- information only: a name can find a row, never confirm an owner -------------------------

@pytest.mark.parametrize("query", [
    OWNER_NAME, "CTO (Kavin) — CTO Main", "cto (kavin) — cto main", "  🌐   CTO (Kavin)  —  CTO Main ",
    "⏸ 🌐 CTO (Kavin) — CTO Main",
])
def test_a_name_finds_one_row(query):
    got = whois.lookup(ROWS, query)
    assert got["ok"] is True and got["mode"] == "info"
    [m] = got["matches"]
    assert (m["host"], m["role"], m["sid"], m["title"]) == ("contabo", "cto", OWNER, OWNER_NAME)
    assert (m["alive"], m["c_level"], m["tmux_claimed"], m["claims"]) == (True, True, True, None)


def test_a_query_that_looks_like_an_id_is_a_name_and_finds_nothing():
    """F1: only --id reads an id. The old code turned "cto-671f688f" into a UUID lookup."""
    for q in (OWNER, f"#{OWNER}", f"cto-{OWNER}", OWNER_UUID):
        assert whois.lookup(ROWS, q)["matches"] == [], q
    [m] = whois.lookup(ROWS, ident=whois.parse_id(f"cto-{OWNER}"))["matches"]
    assert m["uuid"] == OWNER_UUID


def test_no_match_and_ambiguous_in_info_mode():
    for q in ("CTO (Nobody)", "cto", ""):
        got = whois.lookup(ROWS, q)
        assert got["ok"] is False and got["why"].startswith("no match") and got["matches"] == [], q
    copy = row(OWNER_NAME, role="unknown", sid="0badc0de", verified=False, pid=1)
    got = whois.lookup(ROWS + [copy], OWNER_NAME)
    assert got["ok"] is False and got["why"].startswith("ambiguous: 2 live sessions")
    assert "contabo #671f688f" in got["why"] and "contabo #0badc0de" in got["why"]


def test_a_title_claim_is_reported_for_a_row_that_is_not_that_c_level():
    liar = row("🌐 Dev·S#49b Org — CTO Main", role="unknown", sid="49b00000", verified=False)
    got = whois.lookup([liar], "Dev·S#49b Org — CTO Main")
    [m] = got["matches"]
    assert m["claims"] == "CTO Main" and m["c_level"] is False and m["tmux_claimed"] is False
    assert "WARNING: the title says CTO Main but the role is unknown" in whois.format_text(got)


def test_info_mode_can_never_print_an_owner_verdict():
    for result in (whois.lookup(ROWS, OWNER_NAME), whois.lookup(ROWS, "nobody")):
        text = whois.format_text(result)
        assert "owner:" not in text and "YES" not in text and "NO " not in text
        assert text.splitlines()[-1].startswith("info: ")


# --- the command --------------------------------------------------------------------------

def test_exit_0_only_for_the_owner(hub, capsys):
    hub(ROWS)
    assert whois.main(["--owner", OWNER_UUID, "--role", "cto", "--from", UDS]) == 0
    assert "owner: YES — owner confirmed: contabo pid 4242 is cto #671f688f" in capsys.readouterr().out
    for args in (["--owner", OWNER_UUID, "--from", "uds:/tmp/cc-socks-0/777.sock"],             # the CMO
                 ["--owner", OWNER_UUID, "--from", "uds:/tmp/cc-socks-0/31337.sock"],           # no such pid
                 ["--owner", OWNER_UUID, "--role", "cmo", "--from", UDS],                        # wrong role
                 ["--owner", "99999999-9999-4999-8999-999999999999", "--from", UDS],             # other owner
                 ["--owner", OWNER_UUID, "--from", "bridge:session_01BAWu5etWFPGhMoysn1KQyj"]):  # bridge
        assert whois.main(args) == 1, args
        assert "owner: NO — " in capsys.readouterr().out


def test_exit_1_when_the_hub_cannot_be_read_and_nothing_secret_is_printed(hub, capsys):
    hub(ls.HubUrlUnset())
    assert whois.main(["--owner", OWNER_UUID, "--from", UDS]) == 1
    out = capsys.readouterr().out
    assert "hub unreachable (HubUrlUnset): cannot verify" in out and "owner: NO" in out
    hub(RuntimeError("postgresql://user:NOT-A-PASSWORD@hub.invalid/db"))
    assert whois.main(["--owner", OWNER_UUID, "--from", UDS]) == 1
    out = capsys.readouterr().out
    assert "NOT-A-PASSWORD" not in out and "hub.invalid" not in out and "RuntimeError" in out


def test_exit_1_when_this_host_has_no_name(hub, monkeypatch, capsys):
    hub(ROWS)
    def nameless():
        raise RuntimeError("cannot resolve self_host: env=None")
    monkeypatch.setattr(whois, "_here", nameless)
    assert whois.main(["--owner", OWNER_UUID, "--from", UDS]) == 1
    assert "host unknown (RuntimeError): cannot verify" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [
    [],                                                       # nothing to do
    ["-h"], ["--help"], ["--he"], ["--h"], ["-help"],         # F2: no help, no abbreviation
    ["--ow", OWNER_UUID, "--from", UDS], ["--fr", UDS, "--owner", OWNER_UUID],
    ["--owner", OWNER_UUID], ["--from", UDS],                  # one half of the pair
    ["--owner", OWNER_UUID, "--from", "-h"], ["--owner", "-h", "--from", UDS],
    ["--owner", OWNER, "--from", UDS], ["--owner", f"cto-{OWNER}", "--from", UDS],      # not a full UUID
    ["--owner", OWNER_UUID[:-1], "--from", UDS], ["--owner", OWNER_UUID + "0", "--from", UDS],
    ["--owner", OWNER_UUID, "--from", "uds:/tmp/cc-socks/3097.sock;true"],
    ["--owner", OWNER_UUID, "--from", "uds:/tmp/cc-socks/3097.sock$(id)"],
    ["--owner", OWNER_UUID, "--from", OWNER_NAME],            # a from-name is not an address
    ["--owner", OWNER_UUID, "--role", "ceo", "--from", UDS], ["--owner", OWNER_UUID, "--role", "x;id", "--from", UDS],
    ["--owner", OWNER_UUID, "--role", "developer", "--from", UDS],
    ["--owner", OWNER_UUID, "--from", UDS, "Helper"],         # a name beside the verdict flags
    ["--owner", OWNER_UUID, "--from", UDS, "--id", OWNER],
    ["Helper", "--id", OWNER], ["--id", "1234567"], ["--id", "zzzzzzzz"],
    ["a", "b"], ["--bogus"], ["--owner"], ["--json", "--owner", OWNER_UUID, "--from"],
])
def test_a_bad_command_line_exits_2_and_never_0(hub, capsys, argv):
    hub(ROWS)
    assert whois.main(argv) == 2
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("whois: usage error: ") and len(err) < 300


def test_nothing_in_the_parser_can_exit_0(hub, monkeypatch):
    """Belt and braces: if argparse ever calls sys.exit(0) (a help action added later), it is a 2."""
    hub(ROWS)
    def exits(self, *a, **k):
        raise SystemExit(0)
    monkeypatch.setattr(whois._Parser, "parse_args", exits)
    assert whois.main(["--owner", OWNER_UUID, "--from", UDS]) == 2


def test_info_mode_prints_the_fields_and_exits_0_for_one_match(hub, capsys):
    hub(ROWS)
    assert whois.main(["--", OWNER_NAME]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "host: contabo", "role: cto (C-level)", "sid: 671f688f", f"uuid: {OWNER_UUID}",
        f"title: {OWNER_NAME}", "alive: yes", "tmux-claimed: yes", "",
        "info: FOUND — one live session (information only: this is not a sender check)"]
    assert whois.main(["--", "CTO (Nobody)"]) == 1
    assert whois.main(["--id", f"cto-{OWNER}"]) == 0
    assert whois.main(["--", "-h"]) == 1          # after `--` a dash is a name, and no row is called that


def test_json_carries_the_verdict_and_the_matches(hub, capsys):
    hub(ROWS)
    assert whois.main(["--owner", OWNER_UUID, "--from", UDS, "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["mode"] == "owner" and out["matches"][0]["uuid"] == OWNER_UUID
    assert whois.main(["--json", "--", "CTO (Nobody)"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "info" and out["matches"] == []
