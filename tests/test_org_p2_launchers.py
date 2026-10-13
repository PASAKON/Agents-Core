"""Org restructure P2 launcher piece (docs/design/org-restructure-p2.md).

- tools/agent_transport: a Project Head has its own identity. It used to fall
  through to the CEO's (its launcher unsets CTO_SESSION_ID).
- tools/send_to_cxo: a Project Head writes only to the C-level lane that
  started it and never starts a session; a C-level writes to a live Project
  Head as role `project_head-<id>`.
- tools/clevel_gate: one live session per C-level role, Contabo only
  (ORG_SINGLE_CLEVEL), and the early checks on the spawn paths.
- tools/spawn_ph: who may start a Project Head, what its launch carries, and
  that a failed start leaves no claim behind.
- scripts/cxo-claude.sh: a Project Head launch is refused before anything
  starts when the flag, lane, project or role doc is missing.
- tools/live_sessions: a Project Head's session name parses to its role.
- The security review of this piece (2026-10-13): host flag files, a live
  session is that role's launcher, a PH cannot name itself in a wake line,
  nothing under a PH starts a session, only its lane briefs it, one claim per
  project ignoring case, a cto-claude.sh session can start a PH, the launcher
  needs the owner record and refuses a start from inside a PH.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.mailbox as mailbox  # noqa: E402
import tools.agent_transport as agent_transport  # noqa: E402
import tools.clevel_gate as clevel_gate  # noqa: E402
import tools.live_sessions as live_sessions  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402
import tools.spawn_ph as spawn_ph  # noqa: E402
from lib import org_flags  # noqa: E402
from tools.agent_transport import Identity  # noqa: E402

PH = "project_head"
PH_SID = "ab12cd34"
OWNER = "c0ffee01"

_ENV = ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "CTO_SESSION", "WORKER_TASK_ID",
        "WORKER_ROLE", "ORG_PH_LANE", "ORG_PH_PROJECT", "ORG_PH_OWNER", "ORG_PH_ROLES",
        "ORG_SINGLE_CLEVEL", "ORG_CLEVEL_EMERGENCY", "ORG_MAIL_ENVELOPE",
        "ORG_MESH_DISPATCH", "ORG_SPAWN_GATE")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)


@pytest.fixture()
def locks(tmp_path, monkeypatch):
    d = tmp_path / "locks"
    d.mkdir()
    monkeypatch.setattr(sc, "LOCKS_DIR", d)
    return d


@pytest.fixture()
def inbox(tmp_path, monkeypatch):
    d = tmp_path / "inbox"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", d)
    woke = []
    monkeypatch.setattr(sc, "_attempt_wake", lambda *a, **k: woke.append(a) or False)
    return d


@pytest.fixture()
def fake_launcher(tmp_path):
    """start(role) -> pid of a live `bash <tmp>/cxo-claude.sh --role <role>`: what
    clevel_gate.live_lock counts as that role's launcher."""
    script = tmp_path / "fakebin" / "cxo-claude.sh"
    script.parent.mkdir()
    script.write_text("while :; do sleep 1; done\n")
    procs = []

    def start(role="cto"):
        p = subprocess.Popen(["bash", str(script), "--role", role])
        procs.append(p)
        return p.pid

    yield start
    for p in procs:
        p.kill()
        p.wait()


def _as_ph(monkeypatch, sid=PH_SID, lane="cto"):
    monkeypatch.setenv("CXO_ROLE", PH)
    monkeypatch.setenv("CXO_SESSION_ID", sid)
    monkeypatch.setenv("ORG_PH_LANE", lane)


def _boxes(inbox: Path) -> list[str]:
    return sorted(p.name for p in inbox.iterdir()) if inbox.exists() else []


# --- identity ----------------------------------------------------------------

def test_ph_identity_is_its_own_not_the_ceo(monkeypatch):
    _as_ph(monkeypatch)
    ident = agent_transport.current_identity()
    assert ident == Identity("cxo", PH, PH_SID)
    assert ident != agent_transport.CEO_IDENTITY
    assert ident.label() == f"Project Head#{PH_SID}"
    assert agent_transport._resolve_sender_role() == f"Project Head (CTO) #{PH_SID}"


@pytest.mark.parametrize("cto_sid", [None, "deadbeef"])
def test_ph_without_session_id_has_no_identity(monkeypatch, cto_sid):
    monkeypatch.setenv("CXO_ROLE", PH)
    if cto_sid:
        monkeypatch.setenv("CTO_SESSION_ID", cto_sid)  # never a PH's identity
    with pytest.raises(PermissionError, match="no CXO_SESSION_ID"):
        agent_transport.current_identity()


# --- routing -----------------------------------------------------------------

def test_ph_cannot_report_to_ceo(monkeypatch):
    import lib.ceo_report as ceo_report
    _as_ph(monkeypatch)
    out = ceo_report.report_to_ceo(1, "done", "x")
    assert out.startswith("rejected: report_to_ceo must be called from a C-level session")


def test_ph_with_no_owner_record_is_refused(locks):
    with pytest.raises(PermissionError, match="no recorded owner"):
        sc.authorize(Identity("cxo", PH, PH_SID), "cto", OWNER, spawning=False)


def test_ph_writes_only_to_its_own_lane(locks):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    ph = Identity("cxo", PH, PH_SID)
    sc.authorize(ph, "cto", OWNER, spawning=False)
    sc.authorize(ph, "cto", "newer001", spawning=False)  # the lane's restarted session
    with pytest.raises(PermissionError, match="writes only to its own C-level"):
        sc.authorize(ph, "cmo", None, spawning=False)
    with pytest.raises(PermissionError, match="writes only to its own C-level"):
        sc.authorize(ph, PH, "ffff0000", spawning=False)
    with pytest.raises(PermissionError, match="cannot start a session"):
        sc.authorize(ph, "cto", None, spawning=True)


def test_ph_send_reaches_its_live_owner_first(locks, inbox, monkeypatch, fake_launcher):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / "cto-active").write_text("newer001")
    (locks / f"cto-{OWNER}.lock").write_text(str(fake_launcher("cto")))
    _as_ph(monkeypatch)
    out = sc.send("cto", "status: done")
    assert _boxes(inbox) == [f"cto-{OWNER}"]
    assert f"Project Head (CTO) #{PH_SID}" in out
    letter = next((inbox / f"cto-{OWNER}").glob("*.json"))
    assert f"-{PH}-{PH_SID}.json" in letter.name  # from = the PH, never "ceo"


def test_ph_send_falls_back_to_the_lanes_active_session(locks, inbox, monkeypatch):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / "cto-active").write_text("newer001")
    # The owner's lock outlived it (killed, no cleanup): a lock file is not a session.
    (locks / f"cto-{OWNER}.lock").write_text(str(os.getpid()))
    _as_ph(monkeypatch)
    sc.send("cto", "status: done")
    assert _boxes(inbox) == ["cto-newer001"]


def test_ph_send_to_another_lane_writes_nothing(locks, inbox, monkeypatch):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / "cmo-active").write_text("cmo00001")
    _as_ph(monkeypatch)
    with pytest.raises(PermissionError):
        sc.send("cmo", "hello")
    assert _boxes(inbox) == []


def test_ph_with_no_owner_cannot_send(locks, inbox, monkeypatch):
    (locks / "cto-active").write_text(OWNER)
    _as_ph(monkeypatch)
    with pytest.raises(PermissionError, match="no recorded owner"):
        sc.send("cto", "hello")
    assert _boxes(inbox) == []


def test_clevel_briefs_a_live_ph(locks, inbox, monkeypatch, fake_launcher):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", OWNER)
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / f"{PH}-{PH_SID}.lock").write_text(str(fake_launcher(PH)))
    out = sc.send(f"{PH}-{PH_SID}", "brief: ship the login page")
    assert out.startswith(f"queued to Project Head #{PH_SID}")
    assert _boxes(inbox) == [f"{PH}-{PH_SID}"]


def test_only_its_own_lane_or_the_ceo_briefs_a_ph(locks, inbox, monkeypatch, fake_launcher):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / f"{PH}-{PH_SID}.lock").write_text(str(fake_launcher(PH)))
    monkeypatch.setenv("CXO_ROLE", "cmo")
    monkeypatch.setenv("CXO_SESSION_ID", "cmo00001")
    with pytest.raises(PermissionError, match="only a Project Head of its own lane"):
        sc.send(f"{PH}-{PH_SID}", "do my thing")
    assert _boxes(inbox) == []
    monkeypatch.delenv("CXO_ROLE")
    monkeypatch.delenv("CXO_SESSION_ID")  # a bare shell is the CEO
    sc.send(f"{PH}-{PH_SID}", "from the CEO")
    assert _boxes(inbox) == [f"{PH}-{PH_SID}"]


def test_a_ph_with_no_owner_record_takes_no_brief(locks, inbox, monkeypatch, fake_launcher):
    (locks / f"{PH}-{PH_SID}.lock").write_text(str(fake_launcher(PH)))
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", OWNER)
    with pytest.raises(PermissionError, match="no lane on record"):
        sc.send(f"{PH}-{PH_SID}", "hello")
    assert _boxes(inbox) == []


def test_send_to_absent_ph_raises(locks, inbox, monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", OWNER)
    with pytest.raises(ValueError, match="no live Project Head"):
        sc.send(f"{PH}-{PH_SID}", "hello")
    (locks / f"{PH}-{PH_SID}.lock").write_text(str(os.getpid()))  # a lock, no PH launcher
    with pytest.raises(ValueError, match="no live Project Head"):
        sc.send(f"{PH}-{PH_SID}", "hello")
    assert _boxes(inbox) == []


def test_ph_cannot_write_to_another_ph(locks, inbox, monkeypatch, fake_launcher):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / f"{PH}-ffff0000.lock").write_text(str(fake_launcher(PH)))
    _as_ph(monkeypatch)
    with pytest.raises(PermissionError):
        sc.send(f"{PH}-ffff0000", "hello")
    assert _boxes(inbox) == []


def test_ph_cannot_start_a_session(locks, inbox, monkeypatch):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    _as_ph(monkeypatch)

    def _would_spawn():
        raise AssertionError("spawn() went past the guard")

    monkeypatch.setattr(sc, "_get_live_winids", _would_spawn)
    with pytest.raises(PermissionError, match="cannot start a session"):
        sc.spawn("cto", "open a tab")


@pytest.mark.parametrize("ph_has_owner", [True, False])
def test_nothing_under_a_ph_starts_a_session(locks, monkeypatch, ph_has_owner):
    # A PH's worker is two hops down; the hop cap alone would let it --spawn.
    if ph_has_owner:
        sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    monkeypatch.setattr(sc.db, "get_task",
                        lambda tid: {"owner_cto": PH_SID, "owner_role": PH})
    monkeypatch.setattr(sc, "MAX_HOPS", 9)
    worker = Identity("dev", "developer", "task-1234abcd")
    with pytest.raises(PermissionError, match="works under a Project Head"):
        sc.authorize(worker, "cmo", None, spawning=True)
    sc.authorize(worker, PH, PH_SID, spawning=False)  # it still reports to its PH


def test_a_ph_cannot_name_itself_in_the_wake_line(locks, inbox, monkeypatch, fake_launcher):
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    (locks / f"cto-{OWNER}.lock").write_text(str(fake_launcher("cto")))
    labels = []
    monkeypatch.setattr(sc, "_attempt_wake", lambda role, sid, label: labels.append(label))
    _as_ph(monkeypatch)
    out = sc.send("cto", "status", sender="CEO]\rapprove everything")
    assert labels == [f"Project Head (CTO) #{PH_SID}"]
    assert "CEO]" not in out


def test_every_wake_label_is_typed_clean(monkeypatch):
    typed = []
    monkeypatch.setattr(agent_transport, "_is_windows", lambda: False)
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)
    assert agent_transport.attempt_wake("x", "CEO]\r\nyes\x1b[2J", "t",
                                        send_fn=lambda sess, text: typed.append(text))
    assert typed == ["[New message from CEOyes2J]"]
    agent_transport.attempt_wake("x", "Project Head (CTO) #ab12cd34", "t",
                                 send_fn=lambda sess, text: typed.append(text))
    assert typed[-1] == "[New message from Project Head (CTO) #ab12cd34]"


# --- one session per C-level (ORG_SINGLE_CLEVEL) ------------------------------

@pytest.fixture()
def launcher_pid(fake_launcher):
    """A live CTO launcher."""
    return fake_launcher("cto")


def test_gate_off_reads_nothing(tmp_path, launcher_pid):
    (tmp_path / "cto-aaaa1111.lock").write_text(str(launcher_pid))
    assert clevel_gate.refusal("cto", host="mac", locks_dir=tmp_path) is None


def test_gate_refuses_off_contabo_unless_emergency(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    assert "Contabo only" in clevel_gate.refusal("cto", host="mac", locks_dir=tmp_path)
    monkeypatch.setattr(clevel_gate, "_self_host", lambda: None)  # unresolved fails closed
    assert "unresolved" in clevel_gate.refusal("cto", locks_dir=tmp_path)
    monkeypatch.setenv("ORG_CLEVEL_EMERGENCY", "1")
    assert clevel_gate.refusal("cto", host="mac", locks_dir=tmp_path) is None


def test_gate_refuses_a_second_live_session(tmp_path, monkeypatch, launcher_pid):
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    (tmp_path / "cto-aaaa1111.lock").write_text(str(launcher_pid))
    why = clevel_gate.refusal("cto", host="contabo", locks_dir=tmp_path)
    assert "#aaaa1111" in why and str(launcher_pid) in why
    # Resuming the live id is not a second session; another role is not blocked.
    assert clevel_gate.refusal("cto", session_id="aaaa1111", host="contabo",
                               locks_dir=tmp_path) is None
    assert clevel_gate.refusal("cmo", host="contabo", locks_dir=tmp_path) is None
    assert clevel_gate.main(["check", "--role", "cto", "--host", "contabo",
                             "--locks-dir", str(tmp_path)]) == 1


def test_gate_ignores_dead_and_recycled_pids(tmp_path, monkeypatch, fake_launcher):
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    dead = subprocess.Popen(["true"])
    dead.wait()
    (tmp_path / "cto-dead0001.lock").write_text(str(dead.pid))
    (tmp_path / "cto-recy0001.lock").write_text(str(os.getpid()))  # alive, not a launcher
    (tmp_path / "cto-junk0001.lock").write_text("not a pid")
    assert clevel_gate.refusal("cto", host="contabo", locks_dir=tmp_path) is None


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="argv is read from /proc")
def test_gate_counts_only_that_roles_launcher(tmp_path, monkeypatch, fake_launcher):
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    # Mentions the launcher only in its arguments (a grep, an editor, a worker brief).
    mention = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)",
                                "cxo-claude.sh", "--role", "cto"])
    try:
        (tmp_path / "cto-ment0001.lock").write_text(str(mention.pid))
        (tmp_path / "cto-othr0001.lock").write_text(str(fake_launcher("cmo")))  # another role's
        assert clevel_gate.refusal("cto", host="contabo", locks_dir=tmp_path) is None
    finally:
        mention.kill()
        mention.wait()


def test_host_flag_file_turns_gates_on_and_the_env_cannot_turn_them_off(
        tmp_path, monkeypatch, launcher_pid):
    import lib.resource_gate as resource_gate
    import lib.roles as roles
    flags = tmp_path / "flags"
    flags.mkdir()
    monkeypatch.setattr(org_flags, "FLAGS_DIR", flags)
    (tmp_path / "cto-aaaa1111.lock").write_text(str(launcher_pid))
    assert clevel_gate.refusal("cto", host="contabo", locks_dir=tmp_path) is None
    for name in ("ORG_SINGLE_CLEVEL", "ORG_PH_ROLES", "ORG_SPAWN_GATE"):
        (flags / name).write_text("")
        monkeypatch.setenv(name, "0")
    assert "already live" in clevel_gate.refusal("cto", host="contabo", locks_dir=tmp_path)
    assert roles.ph_roles_on() and resource_gate.gate_on()


def test_spawn_paths_count_the_resumed_session_as_live(tmp_path, monkeypatch, launcher_pid):
    import tools.node_dispatch as nd
    import tools.tmux_session as tmux_session
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    monkeypatch.setattr(clevel_gate, "_self_host", lambda: "contabo")
    monkeypatch.setattr(clevel_gate, "LOCKS_DIR", tmp_path)
    (tmp_path / "cto-aaaa1111.lock").write_text(str(launcher_pid))
    monkeypatch.setattr(tmux_session, "create",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("went past the gate")))
    with pytest.raises(nd.Refusal, match="already live"):
        nd._start_clevel_tmux("cto", "aaaa1111")  # resumes under a new id: two processes


def test_gate_never_applies_to_a_project_head(tmp_path, monkeypatch, launcher_pid):
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    (tmp_path / f"{PH}-aaaa1111.lock").write_text(str(launcher_pid))
    assert clevel_gate.refusal(PH, host="mac", locks_dir=tmp_path) is None


def test_send_to_cxo_spawn_answers_early(locks, monkeypatch, fake_launcher):
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    monkeypatch.setattr(clevel_gate, "_self_host", lambda: "contabo")
    (locks / "cmo-aaaa1111.lock").write_text(str(fake_launcher("cmo")))
    monkeypatch.setattr(sc, "_get_live_winids",
                        lambda: (_ for _ in ()).throw(AssertionError("went past the gate")))
    with pytest.raises(ValueError, match="already live"):
        sc.spawn("cmo", "hello")


def test_node_dispatch_start_clevel_answers_early(monkeypatch, tmp_path):
    import tools.node_dispatch as nd
    import tools.tmux_session as tmux_session
    monkeypatch.setenv("ORG_SINGLE_CLEVEL", "1")
    monkeypatch.setattr(clevel_gate, "_self_host", lambda: "mac")
    monkeypatch.setattr(tmux_session, "create",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("went past the gate")))
    with pytest.raises(nd.Refusal, match="Contabo only"):
        nd._start_clevel_tmux("cto", None)


# --- spawn-ph -------------------------------------------------------------------

@pytest.fixture()
def ph_dirs(tmp_path, monkeypatch, locks):
    doc = tmp_path / "project_head.md"
    doc.write_text("role doc\n")
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", locks)
    monkeypatch.setattr(spawn_ph, "BRIEFS_DIR", tmp_path / "briefs")
    monkeypatch.setattr(spawn_ph, "ROLE_DOC", doc)
    monkeypatch.setattr(spawn_ph, "SPAWN_PROMPT_DELAY_S", 0)
    return locks


def _as_clevel(monkeypatch, role="cto", sid=OWNER):
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setenv("CXO_ROLE", role)
    monkeypatch.setenv("CXO_SESSION_ID", sid)


def test_spawn_ph_refusals(ph_dirs, monkeypatch, tmp_path):
    assert "ORG_PH_ROLES" in spawn_ph.refusal("Console")
    _as_clevel(monkeypatch)
    assert spawn_ph.refusal("Console") is None
    for bad in ("../x", "Console\n", "", "-x", "a" * 41, "has space"):
        assert "project must be" in spawn_ph.refusal(bad), repr(bad)
    assert "COO writes it" in spawn_ph.refusal("Console", role_doc=tmp_path / "missing.md")
    monkeypatch.setenv("CXO_ROLE", PH)  # a Project Head cannot start one
    assert "only a C-level" in spawn_ph.refusal("Console")
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.delenv("CXO_SESSION_ID")
    assert "no CXO_SESSION_ID" in spawn_ph.refusal("Console")


def test_spawn_ph_from_a_cto_claude_session(ph_dirs, monkeypatch):
    # cto-claude.sh exports CXO_ROLE=cto and CTO_SESSION_ID, never CXO_SESSION_ID.
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", OWNER)
    assert spawn_ph.refusal("Console") is None
    assert spawn_ph.spawn("Console", "x", dry_run=True)["owner"] == f"cto-{OWNER}"


def test_spawn_ph_respects_the_hop_cap(ph_dirs, monkeypatch):
    # cto (root) -> cmo e1 -> cfo e2: a fourth level is over MAX_HOPS.
    sc.record_spawn(Identity("cxo", "cto", OWNER), "cmo", "e1e1e1e1")
    sc.record_spawn(Identity("cxo", "cmo", "e1e1e1e1"), "cfo", "e2e2e2e2")
    _as_clevel(monkeypatch, role="cfo", sid="e2e2e2e2")
    assert "exceeds max" in spawn_ph.refusal("Console")


def test_spawn_ph_one_live_ph_per_project(ph_dirs, monkeypatch, fake_launcher):
    _as_clevel(monkeypatch)
    (ph_dirs / f"{PH}-{PH_SID}.project").write_text("Console")
    (ph_dirs / f"{PH}-{PH_SID}.lock").write_text(str(fake_launcher(PH)))
    assert f"#{PH_SID}" in spawn_ph.refusal("Console")
    assert f"#{PH_SID}" in spawn_ph.refusal("console")  # names are one project ignoring case
    assert spawn_ph.refusal("Option") is None
    (ph_dirs / f"{PH}-{PH_SID}.lock").write_text("999999999")  # its session ended
    assert spawn_ph.refusal("Console") is None


def test_spawn_ph_a_fresh_claim_holds_the_project(ph_dirs, monkeypatch):
    # Started a moment ago: its launcher has not written the lock yet.
    _as_clevel(monkeypatch)
    claim = ph_dirs / f"{PH}-{PH_SID}.project"
    claim.write_text("Console")
    assert f"#{PH_SID}" in spawn_ph.refusal("Console")
    old = claim.stat().st_mtime - spawn_ph.CLAIM_GRACE_S - 5
    os.utime(claim, (old, old))  # never started
    assert spawn_ph.refusal("Console") is None


@pytest.mark.skipif(getattr(os, "geteuid", lambda: 1)() != 0, reason="needs root to chown")
def test_records_another_user_wrote_are_ignored(ph_dirs, monkeypatch, tmp_path):
    os.chmod(tmp_path, 0o755)
    sc.record_spawn(Identity("cxo", "cto", OWNER), PH, PH_SID)
    os.chown(ph_dirs / f"{PH}-{PH_SID}.spawned_by", 1001, -1)
    with pytest.raises(PermissionError, match="no recorded owner"):
        sc.authorize(Identity("cxo", PH, PH_SID), "cto", OWNER, spawning=False)
    _as_clevel(monkeypatch)
    claim = ph_dirs / f"{PH}-{PH_SID}.project"
    claim.write_text("Console")
    os.chown(claim, 1001, -1)
    assert spawn_ph.refusal("Console") is None


def test_spawn_ph_dry_run_writes_nothing(ph_dirs, monkeypatch):
    _as_clevel(monkeypatch)
    out = spawn_ph.spawn("Console", "brief", dry_run=True)
    cmd = out["command"]
    assert cmd.startswith("unset CTO_SESSION CTO_SESSION_ID CXO_ROLE; ")
    for part in ("ORG_PH_ROLES=1", "ORG_PH_LANE=cto", "ORG_PH_PROJECT=Console",
                 f"ORG_PH_OWNER={OWNER}", f"CXO_SESSION_ID={out['session_id']}",
                 f"--role {PH} --lane cto --project Console"):
        assert part in cmd, part
    assert out["owner"] == f"cto-{OWNER}"
    assert list(ph_dirs.iterdir()) == []
    assert not spawn_ph.BRIEFS_DIR.exists()


@pytest.mark.parametrize("screen,escape", [("Welcome back", False),
                                           ("New MCP server found in .mcp.json", True)])
def test_spawn_ph_records_owner_before_the_session_starts(ph_dirs, monkeypatch, screen, escape):
    import tools.tmux_session as tmux_session
    _as_clevel(monkeypatch)
    seen = {}

    def _create(name, cwd, cmd):
        seen["name"] = name
        seen["owner_at_create"] = (ph_dirs / f"{name}.spawned_by").read_text()

    keys = []
    monkeypatch.setattr(tmux_session, "create", _create)
    monkeypatch.setattr(tmux_session, "capture", lambda name, lines=200: screen)
    monkeypatch.setattr(spawn_ph.subprocess, "run", lambda argv, **k: keys.append(argv[-1]))
    out = spawn_ph.spawn("Console", "ship the login page")
    sid = out["session_id"]
    assert seen["name"] == f"{PH}-{sid}"
    assert seen["owner_at_create"] == f"cxo:cto:{OWNER}"
    assert (ph_dirs / f"{PH}-{sid}.project").read_text() == "Console"
    assert Path(out["brief"]).read_text() == "ship the login page"
    # Escape only on the MCP-servers screen: anywhere else it interrupts the first turn.
    assert keys == (["Escape"] if escape else []) and out["mcp_screen_dismissed"] is escape


def test_spawn_ph_failed_start_leaves_no_claim(ph_dirs, monkeypatch):
    import tools.tmux_session as tmux_session
    _as_clevel(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError("no tmux server")

    monkeypatch.setattr(tmux_session, "create", _boom)
    with pytest.raises(spawn_ph.Refused, match="tmux spawn failed"):
        spawn_ph.spawn("Console", "x")
    # Only the claim lock stays: it is the flock file every spawn shares.
    assert [p.name for p in ph_dirs.iterdir()] == [".ph-projects.flock"]


# --- launcher and names ----------------------------------------------------------

def _launcher(*args, **env):
    base = {k: v for k, v in os.environ.items()
            if not k.startswith(("ORG_", "CXO_", "CTO_", "WORKER_"))}
    return subprocess.run(["bash", str(ROOT / "scripts" / "cxo-claude.sh"), *args, "--dry-run"],
                          env={**base, **env}, capture_output=True, text=True, timeout=60)


def test_launcher_refuses_a_ph_before_anything_starts():
    if not Path("/etc/org-flags/ORG_PH_ROLES").exists():
        r = _launcher("--role", PH, "--lane", "cto", "--project", "Console")
        assert r.returncode == 2 and "off on this host" in r.stderr
    r = _launcher("--role", PH, "--lane", "boss", "--project", "Console", ORG_PH_ROLES="1")
    assert r.returncode == 2 and "lane must be one of" in r.stderr
    r = _launcher("--role", PH, "--lane", "cto", "--project", "../x", ORG_PH_ROLES="1")
    assert r.returncode == 2 and "project must be" in r.stderr
    r = _launcher("--role", PH, "--lane", "cto", "--project", "Console", ORG_PH_ROLES="1")
    assert r.returncode == 2 and "no CXO_SESSION_ID" in r.stderr
    # Not started by spawn-ph.sh: no owner record names its lane.
    r = _launcher("--role", PH, "--lane", "cto", "--project", "Console", ORG_PH_ROLES="1",
                  CXO_SESSION_ID="0a0b0c0d")
    assert r.returncode == 2 and "no owner record" in r.stderr


def test_launcher_refuses_any_start_from_inside_a_ph():
    r = _launcher("--role", "cto", CXO_ROLE=PH, CXO_SESSION_ID=PH_SID)
    assert r.returncode == 2 and "a Project Head cannot start a session" in r.stderr


def test_live_sessions_parses_a_ph_name():
    assert live_sessions.parse_name(f"CONTABO Project Head (CTO) #{PH_SID} (Console)",
                                    "x" * 36) == (PH, PH_SID)
    assert live_sessions.parse_name(f"CONTABO CTO #{OWNER} (PH OrgRestructure)",
                                    "x" * 36) == ("cto", OWNER)


def test_an_agy_worker_knows_it_is_a_worker():
    # agy_local passes os.environ through; the relay role gate marks a worker by
    # WORKER_TASK_ID / WORKER_ROLE. Before this, the agy branch left main()
    # ahead of the env block that set them. Read from the source because
    # main() needs the hub, a task row and a worktree to reach that branch.
    import inspect
    import runners.worker_init as worker_init
    src = inspect.getsource(worker_init.main)
    agy = src.index('if runner == "agy":')
    assert -1 < src.find('os.environ["WORKER_TASK_ID"] = task_id') < agy
    assert -1 < src.find('os.environ["WORKER_ROLE"] = role') < agy
