"""A Project Head on the Mac (org restructure M13a, CEO 2026-10-14 "ทำให้ CXO spawn PH
บน Mac และ Windows ได้เลย").

The Mac has no /proc, no /proc/meminfo, no systemd-run and ships bash 3.2. These
tests run the spawn path with each of those taken away:

- tools/clevel_gate reads a launcher's argv from `ps` when there is no /proc, so
  a pid the OS reused after a Project Head ended does not keep its project held.
  When ps cannot say (no ps on Windows, a non-zero exit, `(name)` for another
  user's process on macOS) an alive pid still counts: fail closed.
- lib/org_flags: the host flag file turns Project Heads on without the env, the
  same file the Mac install creates (docs/plans/org-restructure-STATUS.md).
- lib/resource_gate: no /proc/meminfo means RAM unknown, which passes.
- tools/spawn_ph: a C-level on such a host gets the same launch command.
- the launchers parse under bash 3.2: no bash-4-only syntax (checked by pattern
  here; the real bash 3.2 run is in the M13a PR body).
"""
from __future__ import annotations

import json
import os
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



@pytest.mark.parametrize("rc,out", [(1, ""), (0, ""), (0, "(bash)\n"), (0, "(cxo-claude.sh)\n"),
                                    (1, "bash /x/cxo-claude.sh --role project_head\n")])
def test_when_ps_cannot_read_argv_an_alive_pid_counts(mac, procs, monkeypatch, rc, out):
    """macOS: a non-root ps prints `(name)` for another user's process, or exits
    non-zero. Not knowing is not "gone": the gate fails closed (review of #280, finding 4)."""
    pid = procs(["sleep", "300"])
    monkeypatch.setattr(clevel_gate.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, rc, out, ""))
    assert clevel_gate._ps_argv(pid) is None
    assert clevel_gate._pid_is_launcher(pid, PH)


# --- M13b: a Contabo C-level starts a Project Head on the Mac through one Run card ---
# (§2b review of #280: pinned code only, exact args, C-level raised, single-use nonce)

NONCE = "0123456789abcdef"
SHA = "d4ff2ae0" + "0" * 32
ARGS = ["--project", "LuminaSkies", "--from-card", NONCE, "--sha", SHA, "--brief", "b"]


def _card(**over):
    card = {"id": "RUN-20261014-1300-ab12", "status": "running", "host": "mac", "kind": "script",
            "created_via": "clevel",
            "script": {"repo": "Agents-Core", "sha": SHA, "path": "scripts/spawn-ph.sh", "args": list(ARGS)},
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
    monkeypatch.setattr(spawn_ph, "clone_refusal", lambda sha: None)   # tested on its own below
    return cards, seen


def test_the_card_requester_is_the_owner(mac, hub, monkeypatch):
    cards, seen = hub
    monkeypatch.setenv("ORG_PH_ROLES", "1")  # the executor has no C-level env at all
    cards.append(_card())
    assert spawn_ph.card_owner(ARGS) == ("cto", OWNER)
    assert seen["query"]["status"] == "running"
    out = spawn_ph.spawn("LuminaSkies", "b", dry_run=True, card=ARGS)
    assert out["owner"] == f"cto-{OWNER}"
    assert f"ORG_PH_OWNER={OWNER}" in out["command"]


def _script(**kw):
    return {"repo": "Agents-Core", "sha": SHA, "path": "scripts/spawn-ph.sh", "args": list(ARGS), **kw}


@pytest.mark.parametrize("over", [
    {"status": "approved"}, {"status": "pending"}, {"host": "winbox"}, {"kind": "command"},
    {"script": _script(path="scripts/other.sh")},
    {"script": _script(repo="Fork")},
    {"script": _script(sha="e" * 40)},                                   # another commit
    {"script": _script(args=ARGS[:-2])},                                 # the CEO saw no brief
    {"script": _script(args=ARGS[:-1] + ["a brief the CEO never saw"])},
    {"script": _script(args=["--project", "Other", *ARGS[2:]])},
    {"script": _script(args=[*ARGS[:3], "f" * 16, *ARGS[4:]])},
])
def test_a_card_that_is_not_exactly_this_run_is_refused(mac, hub, over):
    cards, _ = hub
    cards.append(_card(**over))
    with pytest.raises(spawn_ph.Refused, match="no single running Run Inbox card"):
        spawn_ph.card_owner(ARGS)


@pytest.mark.parametrize("over", [
    {"requester": {"session": f"project_head-{PH_SID}", "role": "project_head"}},
    {"requester": {"session": f"cmo-{OWNER}", "role": "cto"}},
    {"requester": {"session": "task-1234", "role": "worker"}},
    {"created_via": "worker"},                    # a role claim alone is not enough
    {"created_via": None},
])
def test_a_card_not_raised_by_a_c_level_is_refused(mac, hub, over):
    cards, _ = hub
    cards.append(_card(**over))
    with pytest.raises(spawn_ph.Refused, match="not raised by a C-level"):
        spawn_ph.card_owner(ARGS)


def test_two_matching_cards_are_refused(mac, hub):
    cards, _ = hub
    cards += [_card(), _card(id="RUN-2")]
    with pytest.raises(spawn_ph.Refused, match=r"\(2 found\)"):
        spawn_ph.card_owner(ARGS)


@pytest.mark.parametrize("argv", [
    ARGS + ["--dry-run"], ARGS[:4], ["--from-card", NONCE, "--project", "LuminaSkies", "--sha", SHA],
    [*ARGS[:6], "--brief-file", "/etc/passwd"], [*ARGS[:3], "x", *ARGS[4:]], [*ARGS[:5], "main"],
])
def test_a_card_run_takes_exactly_the_card_shape(argv):
    with pytest.raises(spawn_ph.Refused):
        spawn_ph.parse_card_args(argv)


def test_the_nonce_is_single_use(mac, hub, monkeypatch):
    cards, _ = hub
    cards.append(_card())
    spawn_ph.use_nonce(NONCE)
    with pytest.raises(spawn_ph.Refused, match="already used"):
        spawn_ph.use_nonce(NONCE)


def test_no_hub_is_refused(mac, monkeypatch):
    import lib.config
    import tools.ask_run as ask_run
    monkeypatch.setattr(lib.config, "self_host", lambda: "mac")
    monkeypatch.setattr(spawn_ph, "clone_refusal", lambda sha: None)

    def down(*a, **k):
        raise ask_run.HubError("no token")

    monkeypatch.setattr(ask_run, "_call", down)
    with pytest.raises(spawn_ph.Refused, match="cannot read the Run Inbox hub"):
        spawn_ph.card_owner(ARGS)


def test_card_command_shape():
    cmd = spawn_ph.card_command("mac", "LuminaSkies", "brief text", SHA, nonce=NONCE)
    i = cmd.index("create")
    assert cmd[i:i + 3] == ["create", "--host", "mac"]
    assert f"Agents-Core@{SHA}:scripts/spawn-ph.sh" in cmd
    assert cmd[cmd.index("--") + 1:] == [*ARGS[:-1], "brief text"]
    for bad in (dict(project="../x"), dict(sha="d4ff2ae0"), dict(sha="main"),
                dict(brief="line one\nline two"), dict(brief="x" * (spawn_ph.CARD_BRIEF_MAX + 1))):
        kw = {"project": "LuminaSkies", "brief": "", "sha": SHA, **bad}
        with pytest.raises(spawn_ph.Refused):
            spawn_ph.card_command("mac", kw["project"], kw["brief"], kw["sha"])


def test_raising_a_card_needs_a_c_level(mac, monkeypatch, capsys):
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    assert spawn_ph.main(["card", "--host", "mac", "--project", "LuminaSkies", "--sha", SHA]) == 1
    assert "only a C-level" in capsys.readouterr().err
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", OWNER)
    assert spawn_ph.main(["card", "--host", "mac", "--project", "LuminaSkies", "--sha", SHA]) == 0
    assert f"Agents-Core@{SHA}:scripts/spawn-ph.sh" in capsys.readouterr().out


def test_card_command_passes_ask_run_checks():
    import tools.ask_run as ask_run  # noqa: F401
    cmd = spawn_ph.card_command("mac", "LuminaSkies", "Read README.md.", SHA, nonce=NONCE)
    env = {"CXO_ROLE": "cto", "CTO_SESSION_ID": OWNER}
    r = subprocess.run([*cmd[:3], "--dry-run", *cmd[3:]], capture_output=True, text=True,
                       env={**__import__("os").environ, **env}, timeout=60)
    assert r.returncode == 0, r.stderr
    assert '"path": "scripts/spawn-ph.sh"' in r.stdout and NONCE in r.stdout


# The COPIED script (§2b review of #280, finding 1): the executor runs the pinned
# bytes from data/run-tmp/<id>/, next to whatever someone planted in data/run-tmp.

def _git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True,
                   env={**__import__("os").environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


@pytest.fixture()
def card_run(tmp_path):
    """A fixed clone (a tiny repo whose tools/spawn_ph.py says it ran), and the
    executor's run-tmp holding a copy of spawn-ph.sh pointed at that clone, plus
    planted look-alikes beside it."""
    clone = tmp_path / "clone"
    (clone / "tools").mkdir(parents=True)
    (clone / "lib").mkdir()
    (clone / "tools" / "spawn_ph.py").write_text(
        "import sys, json\nprint('CLONE RAN', json.dumps(sys.argv[1:]), 'isolated=%d' % sys.flags.isolated)\n")
    _git("init", "-q", cwd=clone)
    _git("add", "-A", cwd=clone)
    _git("commit", "-qm", "c", cwd=clone)
    sha = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    run_tmp = tmp_path / "data" / "run-tmp"
    (run_tmp / "RUN-1").mkdir(parents=True)
    text = (ROOT / "scripts" / "spawn-ph.sh").read_text()
    assert text.count("CLONE_LINUX=/opt/MoonieXHQ/Agents/Core\n") == 1
    text = text.replace("CLONE_LINUX=/opt/MoonieXHQ/Agents/Core\n", f"CLONE_LINUX={clone}\n")
    script = run_tmp / "RUN-1" / "spawn-ph.sh"
    script.write_text(text)
    for planted in (run_tmp / "tools" / "spawn_ph.py", run_tmp / ".venv" / "bin" / "python"):
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text("#!/bin/sh\necho PWNED\nprint('PWNED')\n")
        planted.chmod(0o755)

    def run(args):
        return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, timeout=30,
                              cwd=run_tmp / "RUN-1")

    run.clone, run.sha = clone, sha
    return run


def _card_args(sha):
    return ["--project", "LuminaSkies", "--from-card", NONCE, "--sha", sha]


def test_the_copied_script_runs_the_clone_isolated_never_a_planted_file(card_run):
    r = card_run(_card_args(card_run.sha))
    assert "PWNED" not in r.stdout + r.stderr
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("CLONE RAN") and "isolated=1" in r.stdout
    assert json.loads(r.stdout.split(" ", 2)[2].rsplit(" ", 1)[0]) == _card_args(card_run.sha)


def test_the_copied_script_refuses_a_clone_at_another_commit(card_run):
    r = card_run(_card_args("e" * 40))
    assert r.returncode == 2 and "the card is " + "e" * 40 in r.stderr and "CLONE RAN" not in r.stdout


def test_the_copied_script_refuses_a_changed_clone(card_run):
    (card_run.clone / "tools" / "spawn_ph.py").write_text("print('EDITED')\n")
    r = card_run(_card_args(card_run.sha))
    assert r.returncode == 2 and "changed tracked files" in r.stderr and "EDITED" not in r.stdout


@pytest.mark.parametrize("rel", ["json.py", "tools/clevel_gate.py", "lib/deep/x.py"])
def test_the_copied_script_refuses_untracked_python_it_would_import(card_run, rel):
    (card_run.clone / rel).parent.mkdir(parents=True, exist_ok=True)
    (card_run.clone / rel).write_text("print('PWNED')\n")
    r = card_run(_card_args(card_run.sha))
    assert r.returncode == 2 and "untracked Python" in r.stderr and "PWNED" not in r.stdout


def test_a_card_run_without_a_full_sha_is_refused(card_run):
    r = card_run(["--project", "LuminaSkies", "--from-card", NONCE])
    assert r.returncode == 2 and "needs --sha" in r.stderr


def test_the_python_side_checks_the_clone_too(card_run, monkeypatch):
    monkeypatch.setattr(spawn_ph, "ROOT", card_run.clone)
    assert spawn_ph.clone_refusal(card_run.sha) is None
    assert "the card is " + "e" * 40 in spawn_ph.clone_refusal("e" * 40)
    (card_run.clone / "tools" / "spawn_ph.py").write_text("x = 1\n")
    assert "changed tracked files" in spawn_ph.clone_refusal(card_run.sha)


def test_a_spawn_must_use_the_cards_project_and_brief(mac, hub):
    cards, _ = hub
    cards.append(_card())
    for project, brief in (("Other", "b"), ("LuminaSkies", "another brief")):
        with pytest.raises(spawn_ph.Refused, match="must be the card's"):
            spawn_ph.spawn(project, brief, dry_run=True, card=ARGS)

# --- M13c: winbox ---

def test_windows_launch_argv_carries_no_environment_or_prompt():
    argv = spawn_ph.windows_launch_argv(PH_SID, "cto", "LuminaSkies", wt=r"C:\wt.exe",
                                        new_window=False)
    assert argv[:4] == [r"C:\wt.exe", "-w", "0", "nt"]
    assert argv[argv.index("-File") + 1].endswith("cxo-claude.ps1")
    assert argv[-8:] == ["-Role", PH, "-Lane", "cto", "-Project", "LuminaSkies", "-Session", PH_SID]
    assert not any(";" in a for a in argv)  # wt.exe splits its command line on ;
    assert spawn_ph.windows_launch_argv(PH_SID, "cto", "X", wt="wt", new_window=True)[2] == "new"


def test_windows_refuses_session_0_and_the_ceo_hold(tmp_path):
    hold = tmp_path / "CEO_HOLD.json"
    assert "session 0" in spawn_ph.windows_refusal(0, hold)
    assert "session 0" in spawn_ph.windows_refusal(None, hold)
    assert spawn_ph.windows_refusal(1, hold) is None
    hold.write_text("{}")
    assert "CEO is using this PC" in spawn_ph.windows_refusal(1, hold)


def test_first_prompt_is_the_same_on_every_host():
    p = spawn_ph.first_prompt(PH_SID, "cto", "LuminaSkies", OWNER)
    assert p.startswith(f"You are Project Head (CTO) #{PH_SID} for project LuminaSkies; "
                        f"you report to cto-{OWNER}.")
    assert f"project_head-{PH_SID}.md" in p and '"' not in p


def test_winbox_card_runs_the_powershell_twin(mac, hub, monkeypatch):
    cmd = spawn_ph.card_command("winbox", "LuminaSkies", "b", SHA, nonce=NONCE)
    assert f"Agents-Core@{SHA}:windows/spawn-ph.ps1" in cmd
    cards, _ = hub
    import lib.config
    card = _card(host="winbox")
    card["script"] = {**card["script"], "path": "windows/spawn-ph.ps1"}
    cards.append(card)
    monkeypatch.setattr(lib.config, "self_host", lambda: "winbox")
    assert spawn_ph.card_owner(ARGS) == ("cto", OWNER)
    # The bash script's card is not the winbox one, and the other way round.
    card["script"]["path"] = "scripts/spawn-ph.sh"
    with pytest.raises(spawn_ph.Refused, match="no single running"):
        spawn_ph.card_owner(ARGS)


def test_the_flag_directory_on_windows():
    assert org_flags.flags_dir_for("nt", r"C:\ProgramData") == r"C:\ProgramData\org-flags"
    assert org_flags.flags_dir_for("nt", None) == r"C:\ProgramData\org-flags"
    assert org_flags.flags_dir_for("posix", r"C:\ProgramData") == "/etc/org-flags"


def test_windows_launchers_are_ascii_and_keep_the_ph_rules():
    for name in ("cxo-claude.ps1", "spawn-ph.ps1"):
        raw = (ROOT / "windows" / name).read_bytes()
        assert raw.isascii(), f"{name}: PS 5.1 reads a BOM-less .ps1 as ANSI"
    ps = (ROOT / "windows" / "cxo-claude.ps1").read_text()
    for must in ("'project_head'", "org-flags\\ORG_PH_ROLES", "spawned_by", "roles\\project_head.md",
                 "Remove-Item Env:CTO_SESSION, Env:CTO_SESSION_ID", "Invoke-NativeExe -Exe $claude",
                 "$env:CXO_ROLE -eq 'project_head'"):
        assert must in ps, must
    # The inline python goes to python.exe as one native argument: no double quote in it.
    for block in re.findall(r"@'\r?\n(.*?)\r?\n'@", ps, re.S):
        assert '"' not in block


@pytest.mark.parametrize("role,lane,display", [("project_head", "cto", "Project Head (CTO)"),
                                               ("cto", "", None)])
def test_the_windows_role_line_splits_on_tabs(role, lane, display):
    ps = (ROOT / "windows" / "cxo-claude.ps1").read_text()
    code = re.search(r"\$pyRoleCode = @'\r?\n(.*?)\r?\n'@", ps, re.S).group(1)
    env = {**os.environ, "ROLE_ARG": role, "ROLE_ROOT": str(ROOT), "PH_LANE": lane}
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env,
                       timeout=60)
    assert r.returncode == 0, r.stderr
    parts = r.stdout.strip().split("\t")
    assert len(parts) == 4, parts
    if display:
        assert parts[0] == display
    assert parts[2] and parts[3]
