"""A Project Head on the Mac (org restructure M13a, CEO 2026-10-14 "ทำให้ CXO spawn PH
บน Mac และ Windows ได้เลย").

The Mac has no /proc, no /proc/meminfo, no systemd-run and ships bash 3.2. These
tests run the spawn path with each of those taken away:

- tools/clevel_gate reads a launcher's argv from `ps` when there is no /proc, so
  a pid the OS reused after a Project Head ended does not keep its project held;
  with no ps either (Windows) an alive pid still counts.
- lib/org_flags: the host flag file turns Project Heads on without the env, the
  same file the Mac install creates (docs/plans/org-restructure-STATUS.md).
- lib/resource_gate: no /proc/meminfo means RAM unknown, which passes.
- tools/spawn_ph: a C-level on such a host gets the same launch command.
- the launchers parse under bash 3.2: no bash-4-only syntax (checked by pattern
  here; the real bash 3.2 run is in the M13a PR body).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.clevel_gate as clevel_gate  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402
import tools.spawn_ph as spawn_ph  # noqa: E402
from lib import org_flags, resource_gate  # noqa: E402

PH = "project_head"
PH_SID = "ab12cd34"
OWNER = "c0ffee01"

_ENV = ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "CTO_SESSION", "ORG_PH_ROLES",
        "ORG_PH_LANE", "ORG_PH_PROJECT", "ORG_PH_OWNER", "ORG_SPAWN_GATE")


@pytest.fixture()
def mac(tmp_path, monkeypatch):
    """This host, with /proc and /proc/meminfo gone and no host flags yet."""
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(clevel_gate, "PROC", tmp_path / "no-proc")
    monkeypatch.setattr(org_flags, "FLAGS_DIR", tmp_path / "etc-org-flags")
    locks = tmp_path / "locks"
    locks.mkdir()
    doc = tmp_path / "project_head.md"
    doc.write_text("role doc\n")
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", locks)
    monkeypatch.setattr(spawn_ph, "BRIEFS_DIR", tmp_path / "briefs")
    monkeypatch.setattr(spawn_ph, "ROLE_DOC", doc)
    # This box's disk is not the Mac's; the gate itself is tested below.
    monkeypatch.setattr(spawn_ph.resource_gate, "check", lambda *a, **k: None)
    return locks


@pytest.fixture()
def procs(tmp_path):
    started = []

    def start(argv):
        p = subprocess.Popen(argv)
        started.append(p)
        return p.pid

    yield start
    for p in started:
        p.kill()
        p.wait()


def _launcher(tmp_path: Path, name: str = "cxo-claude.sh") -> Path:
    script = tmp_path / "fakebin" / name
    script.parent.mkdir(exist_ok=True)
    script.write_text("while :; do sleep 1; done\n")
    return script


def _wait_for_argv(pid: int) -> None:
    # ps can show the pre-exec argv for a moment right after Popen.
    for _ in range(200):
        if "--role" in (clevel_gate._ps_argv(pid) or []):
            return
        subprocess.run(["sleep", "0.01"])


def test_without_proc_ps_names_the_launcher(mac, tmp_path, procs):
    pid = procs(["bash", str(_launcher(tmp_path)), "--role", PH])
    _wait_for_argv(pid)
    assert clevel_gate._pid_is_launcher(pid, PH)
    assert not clevel_gate._pid_is_launcher(pid, "cto")


def test_without_proc_a_reused_pid_does_not_hold_the_project(mac, tmp_path, procs, monkeypatch):
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", OWNER)
    other = procs(["sleep", "300"])  # alive, but not a launcher
    (mac / f"{PH}-{PH_SID}.project").write_text("Console")
    (mac / f"{PH}-{PH_SID}.lock").write_text(str(other))
    assert not clevel_gate._pid_is_launcher(other, PH)
    assert spawn_ph.refusal("Console") is None

    live = procs(["bash", str(_launcher(tmp_path)), "--role", PH])
    _wait_for_argv(live)
    (mac / f"{PH}-{PH_SID}.lock").write_text(str(live))
    assert f"#{PH_SID}" in spawn_ph.refusal("Console")


def test_without_proc_or_ps_an_alive_pid_counts(mac, procs, monkeypatch):
    pid = procs(["sleep", "300"])

    def no_ps(*a, **k):
        raise FileNotFoundError("ps")

    monkeypatch.setattr(clevel_gate.subprocess, "run", no_ps)
    assert clevel_gate._ps_argv(pid) is None
    assert clevel_gate._pid_is_launcher(pid, PH)


def test_a_dead_pid_is_never_a_launcher(mac):
    p = subprocess.Popen(["true"])
    p.wait()
    assert not clevel_gate._pid_is_launcher(p.pid, PH)


def test_the_host_flag_file_turns_project_heads_on(mac, monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", OWNER)
    assert "ORG_PH_ROLES" in spawn_ph.refusal("Console")
    org_flags.FLAGS_DIR.mkdir()
    (org_flags.FLAGS_DIR / "ORG_PH_ROLES").touch()
    assert spawn_ph.refusal("Console") is None


def test_no_meminfo_means_ram_unknown_and_the_gate_passes(tmp_path):
    reading = resource_gate.read(str(tmp_path), meminfo=tmp_path / "no-meminfo")
    assert reading.ram_available_mb is None
    assert resource_gate.Reading(None, 50.0, reading.ram_floor_mb,
                                 reading.disk_max_pct).refusal() is None


def test_spawn_ph_dry_run_on_the_mac(mac, monkeypatch):
    # A Mac CTO is started by cto-claude.sh: CXO_ROLE=cto and CTO_SESSION_ID.
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", OWNER)
    out = spawn_ph.spawn("LuminaSkies", "brief", dry_run=True)
    assert out["owner"] == f"cto-{OWNER}"
    assert "--role project_head --lane cto --project LuminaSkies" in out["command"]
    assert list(mac.iterdir()) == []


# Bash 4+ only: associative arrays, mapfile/readarray, case-changing expansion,
# |& , ;;& , coproc, wait -n, ${var@Q}, EPOCHSECONDS/EPOCHREALTIME, [[ -v ]].
_BASH4 = re.compile(r"declare -A|local -A|\bmapfile\b|\breadarray\b|\$\{[A-Za-z_]+(,,|\^\^|@Q)"
                    r"|\|&|;;&|\bcoproc\b|\bwait -n\b|EPOCHREALTIME|EPOCHSECONDS|\[\[ -v ")


@pytest.mark.parametrize("script", ["cxo-claude.sh", "cto-claude.sh", "spawn-ph.sh",
                                    "session-rename.sh", "live-sessions.sh"])
def test_launchers_use_no_bash4_syntax(script):
    path = ROOT / "scripts" / script
    if not path.exists():
        pytest.skip(f"{script} not in this tree")
    hits = [f"{i}: {line.strip()}" for i, line in enumerate(path.read_text().splitlines(), 1)
            if not line.lstrip().startswith("#") and _BASH4.search(line)]
    assert hits == [], f"macOS ships bash 3.2; {script} has bash-4-only syntax: {hits}"


# --- M13b: a Contabo C-level starts a Project Head on the Mac through one Run card ---

NONCE = "0123456789abcdef"


def _card(**over):
    card = {"id": "RUN-20261014-1300-ab12", "status": "running", "host": "mac", "kind": "script",
            "script": {"repo": "Agents-Core", "sha": "d4ff2ae0", "path": "scripts/spawn-ph.sh",
                       "args": ["--project", "LuminaSkies", "--from-card", NONCE, "--brief", "b"]},
            "requester": {"session": f"cto-{OWNER}", "role": "cto"}}
    card.update(over)
    return card


@pytest.fixture()
def hub(monkeypatch):
    import lib.config
    import tools.ask_run as ask_run
    cards = []
    seen = {}

    def call(method, path, *, body=None, query=None):
        seen.update(method=method, path=path, query=query)
        return {"asks": cards}

    monkeypatch.setattr(ask_run, "_call", call)
    monkeypatch.setattr(lib.config, "self_host", lambda: "mac")
    return cards, seen


def test_the_card_requester_is_the_owner(mac, hub, monkeypatch):
    cards, seen = hub
    monkeypatch.setenv("ORG_PH_ROLES", "1")  # the executor has no C-level env at all
    cards.append(_card())
    assert spawn_ph.card_owner(NONCE, "LuminaSkies") == ("cto", OWNER)
    assert seen["query"]["status"] == "running"
    out = spawn_ph.spawn("LuminaSkies", "b", dry_run=True, card=NONCE)
    assert out["owner"] == f"cto-{OWNER}"
    assert f"ORG_PH_OWNER={OWNER}" in out["command"]


@pytest.mark.parametrize("over", [
    {"status": "approved"}, {"status": "pending"}, {"host": "winbox"}, {"kind": "command"},
    {"script": {"repo": "Agents-Core", "sha": "d4ff2ae0", "path": "scripts/other.sh",
                "args": ["--project", "LuminaSkies", "--from-card", NONCE]}},
    {"script": {"repo": "Fork", "sha": "d4ff2ae0", "path": "scripts/spawn-ph.sh",
                "args": ["--project", "LuminaSkies", "--from-card", NONCE]}},
    {"script": {"repo": "Agents-Core", "sha": "d4ff2ae0", "path": "scripts/spawn-ph.sh",
                "args": ["--project", "Other", "--from-card", NONCE]}},
    {"script": {"repo": "Agents-Core", "sha": "d4ff2ae0", "path": "scripts/spawn-ph.sh",
                "args": ["--project", "LuminaSkies", "--from-card", "f" * 16]}},
])
def test_no_matching_running_card_is_refused(mac, hub, over):
    cards, _ = hub
    cards.append(_card(**over))
    with pytest.raises(spawn_ph.Refused, match="no single running Run Inbox card"):
        spawn_ph.card_owner(NONCE, "LuminaSkies")


@pytest.mark.parametrize("req", [{"session": f"project_head-{PH_SID}", "role": "project_head"},
                                 {"session": f"cmo-{OWNER}", "role": "cto"},
                                 {"session": "task-1234", "role": "worker"}])
def test_a_card_not_raised_by_a_c_level_is_refused(mac, hub, req):
    cards, _ = hub
    cards.append(_card(requester=req))
    with pytest.raises(spawn_ph.Refused, match="not raised by a C-level"):
        spawn_ph.card_owner(NONCE, "LuminaSkies")


def test_two_matching_cards_are_refused(mac, hub):
    cards, _ = hub
    cards += [_card(), _card(id="RUN-2")]
    with pytest.raises(spawn_ph.Refused, match=r"\(2 found\)"):
        spawn_ph.card_owner(NONCE, "LuminaSkies")


def test_no_hub_is_refused(mac, monkeypatch):
    import lib.config
    import tools.ask_run as ask_run
    monkeypatch.setattr(lib.config, "self_host", lambda: "mac")

    def down(*a, **k):
        raise ask_run.Refused("no token")

    monkeypatch.setattr(ask_run, "_call", down)
    with pytest.raises(spawn_ph.Refused, match="cannot read the Run Inbox hub"):
        spawn_ph.card_owner(NONCE, "LuminaSkies")
    with pytest.raises(spawn_ph.Refused, match="16-hex nonce"):
        spawn_ph.card_owner("x", "LuminaSkies")


def test_card_command_shape():
    cmd = spawn_ph.card_command("mac", "LuminaSkies", "brief text", "d4ff2ae0", nonce=NONCE)
    i = cmd.index("create")
    assert cmd[i:i + 3] == ["create", "--host", "mac"]
    assert "Agents-Core@d4ff2ae0:scripts/spawn-ph.sh" in cmd
    assert cmd[cmd.index("--") + 1:] == ["--project", "LuminaSkies", "--from-card", NONCE,
                                         "--brief", "brief text"]
    with pytest.raises(spawn_ph.Refused):
        spawn_ph.card_command("mac", "../x", "", "d4ff2ae0")
    with pytest.raises(spawn_ph.Refused):
        spawn_ph.card_command("mac", "LuminaSkies", "", "main")


def test_card_command_passes_ask_run_checks():
    import tools.ask_run as ask_run
    cmd = spawn_ph.card_command("mac", "LuminaSkies", "Read README.md.", "d4ff2ae0", nonce=NONCE)
    env = {"CXO_ROLE": "cto", "CTO_SESSION_ID": OWNER}
    r = subprocess.run([*cmd[:3], "--dry-run", *cmd[3:]], capture_output=True, text=True,
                       env={**__import__("os").environ, **env}, timeout=60)
    assert r.returncode == 0, r.stderr
    assert '"path": "scripts/spawn-ph.sh"' in r.stdout and NONCE in r.stdout
