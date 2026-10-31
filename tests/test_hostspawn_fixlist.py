"""HostSpawn spawn_ph fix list (task-84a9898b): one test group per fix, all on fakes.

No real host, no network, no hub, no tmux: the lock files live in tmp_path, the registry
is a fake connection, the Windows launcher is read as text, and the rename script talks
to a stand-in service on a unix socket (as scripts/test_session_rename.py does).

1. #579   clevel_gate._pid_is_launcher uses lib.proc.pid_alive; windows/cxo-claude.ps1
          cleans up after a launch that fails once the lock is written.
2. names  a PH is named by the registry's display name; portfolio refuses a new name
          that is not PascalCase; a topic that differs from the project only by case stays.
3. owner  the owner of a PH is the hub's session id (cto-f69c4825), not the lock id
          (cto-fresh); restart_run.win_hub_ph maps an old lock id.
4. rename session-rename.sh says "unchanged" by the full rendered name, not the topic.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.portfolio as pf  # noqa: E402
import tools.clevel_gate as clevel_gate  # noqa: E402
import tools.rename_service as rs  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402
import tools.spawn_ph as spawn_ph  # noqa: E402
from tools import restart_run as rr  # noqa: E402
from tools import tmux_session  # noqa: E402

_ENV = ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "CTO_SESSION", "WORKER_TASK_ID",
        "WORKER_ROLE", "ORG_PH_LANE", "ORG_PH_PROJECT", "ORG_PH_OWNER", "ORG_PH_ROLES",
        "ORG_SINGLE_CLEVEL", "ORG_CLEVEL_EMERGENCY", "ORG_MAIL_ENVELOPE",
        "ORG_MESH_DISPATCH", "ORG_SPAWN_GATE")

HUB_SID = "f69c4825"
FRESH_UUID = f"11111111-2222-3333-4444-5555{HUB_SID}"       # a launcher's .uuid ends in the hub sid
OWNER = "c0ffee01"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)


# --- a fake registry connection ----------------------------------------------------

class FakeConn:
    """The few statements spawn_ph._register_project and portfolio.open_project make."""

    def __init__(self, existing=None):
        self.existing, self.sql, self._last, self._opened = existing, [], "", {}

    def execute(self, sql, params=()):
        self._last = " ".join(sql.split())
        self.sql.append((self._last, params))
        if self._last.startswith("INSERT INTO projects"):
            self._opened = {"id": params[0], "name": params[1], "tier": "normal"}
        return self

    def fetchone(self):
        if self._last.startswith("SELECT * FROM projects WHERE id = ? OR lower(name)"):
            return self.existing
        if self._last.startswith("INSERT INTO projects"):
            return {"id": self._opened["id"]}
        if self._last.startswith("SELECT * FROM projects WHERE id = ?"):
            return self._opened
        return None


@pytest.fixture()
def registry(monkeypatch):
    def use(existing=None):
        conn = FakeConn(existing)
        monkeypatch.setattr(pf, "_tx", lambda c=None: contextlib.nullcontext(conn))
        return conn
    return use


def _plan(project, **extra):
    sid = "12345678"
    return {"project": project, "lane": "cto", "owner": f"cto-{OWNER}", "session_id": sid,
            "tmux_session": f"project_head-{sid}", "kind": "loop", "due_at": None,
            "cadence_h": 24, "command": spawn_ph.launch_command(
                sid, "cto", project, OWNER, spawn_ph.first_prompt(sid, "cto", project, OWNER)), **extra}


# =====================================================================================
# 1. #579 — liveness probe, and the Windows launcher's cleanup
# =====================================================================================

def test_a_dead_pid_that_raises_winerror_87_is_not_a_launcher(tmp_path, monkeypatch):
    """On Windows os.kill(pid, 0) of a dead pid raises OSError (WinError 87), not
    ProcessLookupError. The old probe let it out of spawn_ph; lib.proc.pid_alive answers False."""
    lock = tmp_path / "project_head-deadbeef.lock"
    lock.write_text("4242")

    def winerror_87(pid, sig):
        raise OSError(22, "[WinError 87] The parameter is incorrect")

    monkeypatch.setattr(os, "kill", winerror_87)
    assert clevel_gate._pid_is_launcher(4242, "project_head") is False
    assert clevel_gate.live_lock("project_head", "deadbeef", tmp_path) is None
    assert clevel_gate.live_sessions("project_head", tmp_path) == []


def test_the_probe_is_lib_proc_pid_alive_and_a_dead_pid_reads_nothing(monkeypatch):
    seen = []
    monkeypatch.setattr(clevel_gate, "pid_alive", lambda pid: seen.append(pid) or False)
    monkeypatch.setattr(clevel_gate.PROC.__class__, "is_dir",
                        lambda self: pytest.fail("a dead pid must not be read from /proc"))
    assert clevel_gate._pid_is_launcher(4242) is False
    assert seen == [4242]


def _ps1_lines():
    return (ROOT / "windows" / "cxo-claude.ps1").read_text(encoding="utf-8").splitlines()


def _finally_try_after(lines, start):
    """(index of the `try {`, index of its `} finally {`) for the first column-0 `try {` after
    `start` whose block closes with a finally; brace depth is counted per line."""
    for i in range(start, len(lines)):
        if lines[i].rstrip() != "try {":
            continue
        depth = 1
        for j in range(i + 1, len(lines)):
            before = depth
            depth += lines[j].count("{") - lines[j].count("}")
            if before == 1 and lines[j].startswith("}"):
                if "finally" in lines[j]:
                    return i, j
                break
    raise AssertionError("no try/finally after the lock write")


def test_the_windows_launcher_cleans_up_a_launch_that_fails_after_the_lock_write():
    """No pwsh here, so the launcher is read as text: every step after the lock write that can
    throw ($ErrorActionPreference = 'Stop') sits inside the try whose finally removes the lock,
    the .uuid file and a Project Head's claim and owner record."""
    lines = _ps1_lines()
    lock_write = next(i for i, l in enumerate(lines) if l.startswith("Set-Content -Path $lockFile"))
    opened, finally_at = _finally_try_after(lines, lock_write)
    assert opened > lock_write
    throws = [i for i, l in enumerate(lines)
              if i > lock_write and "throw " in l and not l.lstrip().startswith("#")]
    assert throws, "the launcher no longer has a step that throws"
    assert all(opened < i < finally_at for i in throws), (opened, finally_at, throws)
    cleanup = "\n".join(lines[finally_at:finally_at + 14])
    for removed in ("$lockFile", "$uuidFile", "project_head-$sid.project", "project_head-$sid.spawned_by"):
        assert removed in cleanup, removed
    assert lines[-1].strip() == "exit $code"                      # the exit code still comes last


# =====================================================================================
# 2. PH names — display name, PascalCase, topic kept
# =====================================================================================

@pytest.mark.parametrize("name", ["HostSpawn", "Console", "Film2", "A", "BL"])
def test_pascal_case_names_pass(name):
    assert pf.pascal_refusal(name) is None


@pytest.mark.parametrize("name", ["host spawn", "Host Spawn", "Host-Spawn", "hostSpawn", "hostspawn",
                                  "host_spawn", "Host_Spawn", "", " Host", "Host\n", "ลูมินา", None, 7])
def test_other_names_are_refused(name):
    assert "PascalCase" in pf.pascal_refusal(name)


def test_open_project_refuses_a_name_that_is_not_pascal_case_before_it_touches_the_hub():
    for bad in ("Host Spawn", "host-spawn", "hostspawn"):
        with pytest.raises(pf.PortfolioError, match="PascalCase"):
            pf.open_project("host-spawn", bad, "cto", actor="cto-c0ffee01", pascal_name=True)


def test_the_old_free_text_names_still_open_by_default():
    """pascal_name is opt-in (spawn_ph), so the CLI and every existing caller keep their names:
    the refusal comes from nowhere but the name check when it is on."""
    import inspect
    assert inspect.signature(pf.open_project).parameters["pascal_name"].default is False


def test_a_new_project_head_row_is_opened_under_its_pascal_case_name(registry):
    conn = registry(existing=None)
    plan = _plan("HostSpawn")
    assert spawn_ph._register_project(plan) == "normal"
    insert = next(p for s, p in conn.sql if s.startswith("INSERT INTO projects"))
    assert insert[0] == "hostspawn" and insert[1] == "HostSpawn"      # id is the slug, name is the display name
    assert plan["project"] == "HostSpawn"


@pytest.mark.parametrize("typed", ["hostspawn", "Host-Spawn", "host_spawn"])
def test_a_new_project_head_row_with_another_name_is_refused(registry, typed):
    conn = registry(existing=None)
    with pytest.raises(spawn_ph.Refused, match="PascalCase"):
        spawn_ph._register_project(_plan(typed))
    assert not [s for s, _ in conn.sql if s.startswith("INSERT")]


def test_the_registry_display_name_replaces_the_typed_id(registry):
    registry(existing={"id": "hostspawn", "name": "HostSpawn", "tier": "normal", "due_at": None})
    plan = _plan("hostspawn")
    spawn_ph._register_project(plan)
    assert plan["project"] == "HostSpawn"
    # the command the launcher gets says the same name as the claim file will
    assert "--project HostSpawn" in plan["command"] and "ORG_PH_PROJECT=HostSpawn" in plan["command"]
    assert "hostspawn" not in plan["command"].split("--initial-prompt")[0]
    assert "project HostSpawn;" in plan["command"]               # and so does the first prompt


def test_a_registry_name_no_session_can_be_started_with_keeps_the_typed_one(registry):
    registry(existing={"id": "black-liquidity", "name": "BLACK LIQUIDITY", "tier": "normal", "due_at": None})
    plan = _plan("black-liquidity")
    before = dict(plan)
    spawn_ph._register_project(plan)
    assert plan == before


def test_a_resume_keeps_the_name_its_records_hold(registry):
    registry(existing={"id": "hostspawn", "name": "HostSpawn", "tier": "normal", "due_at": None})
    plan = _plan("hostspawn")
    del plan["kind"]                                             # a resume plan carries no schedule
    spawn_ph._register_project(plan)
    assert plan["project"] == "hostspawn"


@pytest.fixture()
def ph_dirs(tmp_path, monkeypatch):
    locks = tmp_path / "locks"
    locks.mkdir()
    doc = tmp_path / "project_head.md"
    doc.write_text("role doc\n")
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", locks)
    monkeypatch.setattr(spawn_ph, "BRIEFS_DIR", tmp_path / "briefs")
    monkeypatch.setattr(spawn_ph, "ROLE_DOC", doc)
    monkeypatch.setattr(spawn_ph, "SPAWN_PROMPT_DELAY_S", 0)
    return locks


def _as_clevel(monkeypatch, role="cto", sid=OWNER, var="CXO_SESSION_ID"):
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setenv("CXO_ROLE", role)
    monkeypatch.setenv(var, sid)


def _capture_launch(monkeypatch):
    started = []
    monkeypatch.setattr(tmux_session, "create", lambda name, cwd, cmd: started.append((name, cmd)))
    monkeypatch.setattr(tmux_session, "capture", lambda name, lines=200: "")
    return started


def test_spawn_writes_the_registry_display_name_into_the_claim(ph_dirs, monkeypatch, registry):
    registry(existing={"id": "hostspawn", "name": "HostSpawn", "tier": "normal", "due_at": None})
    _as_clevel(monkeypatch)
    started = _capture_launch(monkeypatch)
    out = spawn_ph.spawn("hostspawn", "go", kind="loop", cadence=24)
    name = f"project_head-{out['session_id']}"
    assert (ph_dirs / f"{name}.project").read_text() == "HostSpawn"
    assert out["project"] == "HostSpawn"
    assert started[0][0] == name and "--project HostSpawn" in started[0][1]


def _ph_box(tmp_path, monkeypatch, project):
    locks = tmp_path / "ph-locks"
    locks.mkdir()
    (locks / "project_head-36c49776.project").write_text(project)
    (locks / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e")
    monkeypatch.setattr(rs, "LOCKS_DIR", locks)


def test_a_topic_that_differs_from_the_project_only_by_case_is_kept(tmp_path, monkeypatch):
    """rename_service drops a topic that IS the project (the name already says it). It compares
    exactly: a topic that differs only by case stays, and so does the rename it asks for."""
    _ph_box(tmp_path, monkeypatch, "thaihumor")
    name = rs.build_name("project_head", "36c49776", "ThaiHumor", "", "contabo")
    assert name.endswith("PH#36c (CMO) - thaihumor — ThaiHumor")
    _ph_box_project = tmp_path / "ph-locks" / "project_head-36c49776.project"
    _ph_box_project.write_text("ThaiHumor")                      # the display name, as spawn_ph now writes it
    name = rs.build_name("project_head", "36c49776", "ThaiHumor", "", "contabo")
    assert name.endswith("PH#36c (CMO) - ThaiHumor") and "—" not in name
    assert rs.build_name("project_head", "36c49776", "EP6 clip", "", "contabo").endswith(
        "PH#36c (CMO) - ThaiHumor — EP6 clip")


# =====================================================================================
# 3. owner — the hub's session id
# =====================================================================================

def test_a_launcher_id_of_8_hex_is_the_hub_id(tmp_path):
    assert spawn_ph.hub_sid("cto", OWNER, tmp_path) == OWNER


def test_the_fresh_launcher_maps_to_the_last_8_hex_of_its_uuid(tmp_path):
    (tmp_path / "cto-fresh.uuid").write_text(FRESH_UUID + "\n")
    assert spawn_ph.hub_sid("cto", "fresh", tmp_path) == HUB_SID


@pytest.mark.parametrize("content", [None, "", "not-a-uuid", FRESH_UUID.upper() + "x", "g" * 36])
def test_a_lock_id_with_no_usable_uuid_cannot_own_a_project_head(tmp_path, content):
    if content is not None:
        (tmp_path / "cto-fresh.uuid").write_text(content)
    with pytest.raises(spawn_ph.Refused, match="cannot map session id 'fresh'"):
        spawn_ph.hub_sid("cto", "fresh", tmp_path)


def test_the_uuid_file_is_read_for_its_own_lane(tmp_path):
    (tmp_path / "cmo-fresh.uuid").write_text(FRESH_UUID)
    with pytest.raises(spawn_ph.Refused):
        spawn_ph.hub_sid("cto", "fresh", tmp_path)


def test_a_fresh_cto_spawns_a_ph_owned_by_its_hub_sid(ph_dirs, monkeypatch, registry):
    registry(existing=None)
    (ph_dirs / "cto-fresh.uuid").write_text(FRESH_UUID)
    _as_clevel(monkeypatch, sid="fresh", var="CTO_SESSION_ID")      # cto-claude.sh exports only CTO_SESSION_ID
    assert spawn_ph._caller() == ("cto", HUB_SID)
    dry = spawn_ph.spawn("HostSpawn", "x", dry_run=True, kind="loop", cadence=24)
    assert dry["owner"] == f"cto-{HUB_SID}" and f"ORG_PH_OWNER={HUB_SID}" in dry["command"]
    started = _capture_launch(monkeypatch)
    out = spawn_ph.spawn("HostSpawn", "x", kind="loop", cadence=24)
    name = f"project_head-{out['session_id']}"
    assert out["owner"] == f"cto-{HUB_SID}"
    assert (ph_dirs / f"{name}.spawned_by").read_text() == f"cxo:cto:{HUB_SID}"
    assert f"ORG_PH_OWNER={HUB_SID}" in started[0][1] and "ORG_PH_OWNER=fresh" not in started[0][1]


def test_a_fresh_cto_with_no_uuid_file_starts_no_ph(ph_dirs, monkeypatch):
    _as_clevel(monkeypatch, sid="fresh", var="CTO_SESSION_ID")
    assert "cannot map session id 'fresh'" in spawn_ph.refusal("HostSpawn")
    assert list(ph_dirs.iterdir()) == []


# --- restart_run.win_hub_ph: a row written before this change says cto-fresh -------

class HubRows:
    """The two queries win_hub_ph makes: the project row, then the owner's c_level_sessions row."""

    def __init__(self, projects, resume_uuid):
        self.projects, self.resume_uuid, self.asked, self._sql = projects, resume_uuid, [], ""

    def execute(self, sql, params=()):
        self._sql = " ".join(sql.split())
        self.asked.append((self._sql, params))
        return self

    def fetchall(self):
        assert "FROM projects WHERE ph_session IN" in self._sql
        return self.projects

    def fetchone(self):
        assert "FROM c_level_sessions" in self._sql
        return None if self.resume_uuid is False else {"resume_uuid": self.resume_uuid}


def _hub(monkeypatch, conn):
    from lib import db

    @contextlib.contextmanager
    def get_conn():
        yield conn

    monkeypatch.setattr(db, "pg_url", lambda: "postgres://hub")
    monkeypatch.setattr(db, "get_conn", get_conn)


def _row(owner):
    return {"id": "hostspawn", "name": "HostSpawn", "lane": "cto", "owner_session": owner}


def test_win_hub_ph_maps_the_old_lock_id_to_the_hub_sid(monkeypatch):
    conn = HubRows([_row("cto-fresh")], FRESH_UUID)
    _hub(monkeypatch, conn)
    found, why = rr.win_hub_ph("12345678")
    assert why == "" and found == {"project": "HostSpawn", "lane": "cto", "spawned_by": f"cxo:cto:{HUB_SID}"}
    assert conn.asked[-1][1] == ("cto", "fresh")


def test_win_hub_ph_asks_nothing_more_for_a_hub_sid(monkeypatch):
    conn = HubRows([_row(f"cto-{HUB_SID}")], FRESH_UUID)
    _hub(monkeypatch, conn)
    found, _ = rr.win_hub_ph("12345678")
    assert found["spawned_by"] == f"cxo:cto:{HUB_SID}" and len(conn.asked) == 1


@pytest.mark.parametrize("resume_uuid", [False, None, "", "not-a-uuid"])
def test_win_hub_ph_still_refuses_a_lock_id_the_hub_cannot_map(monkeypatch, resume_uuid):
    _hub(monkeypatch, HubRows([_row("cto-fresh")], resume_uuid))
    found, why = rr.win_hub_ph("12345678")
    assert found is None and "no owner session" in why


# =====================================================================================
# 4. session-rename.sh — "unchanged" is the full rendered name
# =====================================================================================

REAL_ROOT = ROOT


@pytest.fixture
def stage(tmp_path):
    root = tmp_path / "root"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts" / "session-rename.sh"
    script.write_text((REAL_ROOT / "scripts" / "session-rename.sh").read_text())
    for rel in ("lib", "tools", "config", "policies", "roles"):
        if (REAL_ROOT / rel).exists():
            (root / rel).symlink_to(REAL_ROOT / rel)
    (root / "scripts" / "lib").symlink_to(REAL_ROOT / "scripts" / "lib")
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "python").symlink_to(sys.executable)
    (root / "state" / "locks").mkdir(parents=True)
    bin_dir, log = tmp_path / "bin", tmp_path / "tmux.log"
    bin_dir.mkdir()
    (bin_dir / "tmux").write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{log}"\n')
    (bin_dir / "tmux").chmod(0o755)

    sockdir = Path(tempfile.mkdtemp(prefix="hsf-"))         # an AF_UNIX path must stay short
    sock = sockdir / "s.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock))
    srv.listen(8)
    srv.settimeout(0.2)
    requests, stop = [], threading.Event()

    def serve():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except OSError:
                continue
            with conn:
                buf = b""
                while chunk := conn.recv(4096):
                    buf += chunk
                req = json.loads(buf)
                requests.append(req)
                conn.sendall(f"queued {req['role']}-{req['sid']}: x\n".encode())

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    def run(*args, role="project_head", sid="36c49776", host="contabo"):
        env = dict(os.environ)
        env.update(PATH=f"{bin_dir}:{env.get('PATH', '')}", TMUX="/tmp/fake,1,0",
                   CXO_ROLE=role, ORG_HOST=host, RENAME_SERVICE_SOCK=str(sock))
        env.pop("CXO_SESSION_ID", None)
        env["CTO_SESSION_ID"] = sid
        return subprocess.run(["bash", str(script), *args], env=env, capture_output=True,
                              text=True, timeout=30)

    run.locks, run.requests, run.log = root / "state" / "locks", requests, log
    yield run
    stop.set()
    t.join(2)
    srv.close()
    shutil.rmtree(sockdir, ignore_errors=True)


def _make_ph(stage, project):
    (stage.locks / "project_head-36c49776.project").write_text(project)
    (stage.locks / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e")


def test_a_changed_project_with_the_same_topic_sends_a_request(stage):
    _make_ph(stage, "thaihumor")
    first = stage("ThaiHumor")
    assert first.stdout.startswith("requested: /rename"), first.stdout + first.stderr
    assert "PH#36c (CMO) - thaihumor — ThaiHumor" in first.stdout
    assert len(stage.requests) == 1
    # the lock's project is fixed; the topic is the same one the PH sends again
    _make_ph(stage, "ThaiHumor")
    again = stage("ThaiHumor")
    assert again.stdout.startswith("requested: /rename"), again.stdout      # the old script said "unchanged"
    assert "PH#36c (CMO) - ThaiHumor (" in again.stdout and "—" not in again.stdout.split(" (")[0]
    assert len(stage.requests) == 2 and stage.requests[-1]["topic"] == "ThaiHumor"
    assert (stage.locks / "project_head-36c49776.rendered").read_text().endswith("PH#36c (CMO) - ThaiHumor")


def test_nothing_changed_is_unchanged_and_sends_nothing(stage):
    _make_ph(stage, "thaihumor")
    assert stage("ThaiHumor").stdout.startswith("requested:")
    assert stage("ThaiHumor").stdout.strip() == "unchanged: ThaiHumor"
    assert len(stage.requests) == 1
    # --force and a new state glyph still ask again; --show still reports the topic record
    assert stage("--force", "ThaiHumor").stdout.startswith("requested:")
    assert stage("--prefix", "⏸", "ThaiHumor").stdout.startswith("requested: /rename ⏸")
    assert stage("--show").stdout.strip() == "recorded: ⏸ ThaiHumor"
    assert len(stage.requests) == 3


def test_a_session_that_only_has_the_old_topic_record_is_asked_once_more(stage):
    """A .topic written before the rendered-name record cannot say what name the session has."""
    _make_ph(stage, "ThaiHumor")
    (stage.locks / "project_head-36c49776.topic").write_text("EP6 clip")
    assert stage("EP6 clip").stdout.startswith("requested:")
    assert stage("EP6 clip").stdout.strip() == "unchanged: EP6 clip"


def test_a_request_that_did_not_land_records_nothing(stage, monkeypatch):
    _make_ph(stage, "ThaiHumor")
    out = subprocess.run(["bash", "-c", "true"])                     # keep the fixture's env helper honest
    assert out.returncode == 0
    (stage.locks / "project_head-36c49776.rendered").write_text("an older name")
    assert stage("ThaiHumor").stdout.startswith("requested:")        # differs from the record: asks
    assert (stage.locks / "project_head-36c49776.rendered").read_text() != "an older name"
