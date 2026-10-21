"""The probes of the second review of PR #416 (task-75da90d4, F1-F5), as regression tests (OrgMesh P8c).

Each test is one attack from that review. Before P8c every one of them made `whois` answer "owner"
(exit 0) or ran a command. Now every one is refused: exit 1 (not verified) or 2 (usage error), never 0.
F2 and F3 go through the real command line (`python -m tools.whois` in a subprocess, no hub); F1, F4 and
F5 need hub rows, so they call the verdict with rows built here. F6 (the reserved-title regex) is in
scripts/test_live_sessions.py beside `reserved_claim`.

The original probe script is docs/reports/task-75da90d4/probe_whois.py in the reviewer's worktree.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import live_sessions as ls
from tools import spawn_ph
from tools import whois

ROOT = Path(__file__).resolve().parent.parent
OWNER = "671f688f"
OWNER_UUID = "3c1d9e2a-5b7f-4e01-9a2b-c0de671f688f"
OWNER_NAME = "🌐 CTO (Kavin) — CTO Main"
OWNER_PID = 4242
UDS = f"uds:/tmp/cc-socks-0/{OWNER_PID}.sock"


def row(name, role="unknown", uuid="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", host="contabo", sid=None,
        verified=False, stale=False, pid=1, bridge_id=None):
    return {"host": host, "uuid": uuid, "sid": sid or uuid[-8:], "role": role, "name": name,
            "address": name, "status": "running", "pid": pid, "verified": verified, "age": 4.0,
            "stale": stale, "bridge_id": bridge_id}


OWNER_BRIDGE = "session_01OwnerBridgeAAAAAAAAAAAA"
OWNER_ROW = row(OWNER_NAME, role="cto", uuid=OWNER_UUID, verified=True, pid=OWNER_PID, bridge_id=OWNER_BRIDGE)


@pytest.fixture
def locks(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "LOCKS_DIR", tmp_path)
    (tmp_path / f"cto-{OWNER}.uuid").write_text(OWNER_UUID + "\n")


def verdict(rows, from_):
    return whois.verify_owner(rows, OWNER_UUID, whois.parse_from(from_), "contabo", "cto")


def cli(*args: str, shell: str | None = None) -> subprocess.CompletedProcess:
    """`python -m tools.whois <args>` (or a shell line) with no hub: ORG_DB_URL is removed."""
    env = {k: v for k, v in os.environ.items() if k != "ORG_DB_URL"}
    env["PYTHONPATH"] = str(ROOT)
    if shell is not None:
        return subprocess.run(["bash", "-c", shell], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    return subprocess.run([sys.executable, "-m", "tools.whois", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=60)


# --- F1: a sender whose name looks like an id was matched against the owner's UUID -------------------

@pytest.mark.parametrize("name", ["cto-671f688f", "#671f688f", "671f688f", "Kavin-671f688f", "CTO-671F688F"])
def test_f1_a_name_shaped_like_the_owners_id_is_never_read_as_an_id(locks, name):
    attacker = row(name, pid=5151)
    # the information lookup treats it as a name: it finds the attacker's own row at most, never the owner's
    for m in whois.lookup([OWNER_ROW, attacker], name)["matches"]:
        assert m["uuid"] != OWNER_UUID
    # and the verdict has no name input at all: the name is not even a valid --from
    assert whois.parse_from(name) is None
    assert cli("--owner", OWNER_UUID, "--role", "cto", "--from", name).returncode == 2
    # the sender's transport is its own row, which is not the owner
    got = verdict([OWNER_ROW, attacker], "uds:/tmp/cc-socks-0/5151.sock")
    assert got["ok"] is False and got["why"].startswith("id differs")


# --- F2: a sender named -h / --help made argparse print help and exit 0 --------------------------------

@pytest.mark.parametrize("name", ["-h", "--help", "--he", "--h"])
def test_f2_a_sender_named_like_an_option_cannot_make_whois_exit_0(name):
    for args in ([name, "--owner", OWNER_UUID], ["--owner", OWNER_UUID, name],
                 ["--owner", OWNER_UUID, "--from", name], [name]):
        got = cli(*args)
        assert got.returncode == 2, (args, got.stdout, got.stderr)
        assert "usage: " not in got.stdout and "owner: YES" not in got.stdout
    # after `--` it is a plain name for the information lookup: exit 1 here (no hub), and no "owner" line
    got = cli("--", name)
    assert got.returncode != 0 and "owner:" not in got.stdout


# --- F3: the brief pasted an attacker-chosen string inside a shell double quote -----------------------

WIN_PREFIX = ["C:/Users/passg/mooniex/repo/MoonieX-Agents/.venv/Scripts/python.exe", "-E", "-s",
              "C:/Users/passg/mooniex/repo/MoonieX-Agents/tools/infisical_setup.py", "run", "Agents-Core", "prod",
              "--as", "winbox", "--"]


@pytest.mark.parametrize("windows", [False, True])
def test_f3_the_command_in_the_brief_has_no_place_for_a_sender_name(monkeypatch, windows):
    monkeypatch.setattr(spawn_ph, "_windows_hub_prefix", lambda: WIN_PREFIX)
    brief = spawn_ph.mesh_brief(f"cto-{OWNER}", OWNER_UUID, "cto", windows=windows)
    command = brief.split("and run: ", 1)[1].splitlines()[0]
    tail = f"-m tools.whois --owner {OWNER_UUID} --role cto --from '<the from= attribute>'"
    assert command.endswith(tail) and command.count("--from") == 1
    assert command.startswith("bash scripts/hub/org-python.sh " if not windows else WIN_PREFIX[0])
    assert '"' not in command and "<sender>" not in command and "from-name" not in command and "`" not in command
    assert "A name proves nothing" in brief and "never from-name" in brief


@pytest.mark.parametrize("payload", [
    'x"; true; : "', "Helper $(echo INJECTED-RAN >&2)", "`echo INJECTED-RAN`", "a;echo INJECTED-RAN",
    "uds:/tmp/cc-socks/1.sock; echo INJECTED-RAN", "$(echo INJECTED-RAN)", "x\ny",
])
def test_f3_a_hostile_string_in_the_single_quoted_from_slot_is_inert_and_refused(payload):
    line = (f"{sys.executable} -m tools.whois --owner {OWNER_UUID} --role cto --from '{payload}'")
    got = cli(shell=line)
    assert got.returncode == 2, (got.stdout, got.stderr)
    assert "INJECTED-RAN" not in got.stdout + got.stderr.replace(payload, "")
    assert got.stdout == "" and got.stderr.startswith("whois: usage error: ")


# --- F4: the name was checked when whois ran, not when the message was sent ------------------------------

def test_f4_copying_the_owners_name_and_renaming_away_proves_nothing(locks):
    attacker_then = row(OWNER_NAME, pid=5151)           # at send time: the owner's exact name
    attacker_now = row("Helper", pid=5151)              # 5 s later: renamed, the owner is alone with that name
    for rows in ([OWNER_ROW, attacker_then], [OWNER_ROW, attacker_now]):
        got = verdict(rows, "uds:/tmp/cc-socks-0/5151.sock")
        assert got["ok"] is False and got["why"].startswith("id differs"), got
    assert verdict([OWNER_ROW, attacker_now], UDS)["ok"] is True      # the owner's own socket still passes


def test_f4_a_bridge_sender_is_the_row_with_its_id_whatever_the_name(locks):
    """P8d: the bridge id is issued to the sender's session, not chosen by it. An attacker that copies the
    owner's exact name sends under its own id; its row (any name, before or after a rename) is not the owner's."""
    sender = "bridge:session_01AttackerSessionDDDDDDD"
    for name in (OWNER_NAME, "Helper"):
        attacker = row(name, host="mac", pid=5151, bridge_id="session_01AttackerSessionDDDDDDD")
        got = verdict([OWNER_ROW, attacker], sender)
        assert got["ok"] is False and got["why"].startswith("id differs"), got
    assert verdict([OWNER_ROW], sender)["why"].startswith("no match")            # an id nobody published
    assert verdict([OWNER_ROW], f"bridge:{OWNER_BRIDGE}")["ok"] is True          # the owner's own id still passes


# --- F5: any UUID starting or ending with the 8 hex id, on any host, any role, unverified ---------------

@pytest.mark.parametrize("minted", ["00000000-0000-4000-8000-0000671f688f", "671f688f-0000-4000-8000-000000000000"])
def test_f5_a_minted_uuid_with_the_owners_short_id_is_not_the_owner(locks, minted):
    helper = row("Helper", role="unknown", uuid=minted, host="mac", verified=False, pid=6000)
    assert verdict([OWNER_ROW, helper], "uds:/tmp/cc-socks-0/6000.sock")["ok"] is False
    here_too = row("Helper", role="unknown", uuid=minted, host="contabo", verified=False, pid=6000)
    assert verdict([OWNER_ROW, here_too], "uds:/tmp/cc-socks-0/6000.sock")["ok"] is False
    # the 8-hex id is no longer an --owner at all
    assert cli("--owner", OWNER, "--from", UDS).returncode == 2


def test_f5_even_the_full_uuid_needs_a_tmux_claim_the_role_and_the_launchers_lock(locks):
    """A row that copies the owner's UUID but is not what the launcher started still fails."""
    for forged, why in ((row("Helper", uuid=OWNER_UUID, role="unknown", verified=False, pid=6000), "not verified"),
                        (row("Helper", uuid=OWNER_UUID, role="developer", verified=True, pid=6000), "role differs"),
                        (row("Helper", uuid=OWNER_UUID, role="cto", verified=True, pid=6000, stale=True), "not alive")):
        got = verdict([forged], "uds:/tmp/cc-socks-0/6000.sock")
        assert got["ok"] is False and got["why"].startswith(why), got
