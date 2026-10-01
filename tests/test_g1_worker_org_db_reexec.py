"""G1 follow-up (task-1b8ef857, 2026-10-02): after the hub cutover a worker and
the org CLIs reach the ledger even when the shell that starts them has no
ORG_DB_URL.

A tmux pane gets the tmux SERVER's environment, so a worker spawned on a host
whose tmux server predates the cutover reached lib.db without ORG_DB_URL and
died on the archived state/tasks.db. Shell scripts called the system python3,
which has no psycopg. Covered here:

  * lib.worker_mcp_config.reexec_with_org_db_url: when it re-execs, with what,
    and the guard that stops a second pass;
  * env_without_org_db: the worker's claude process never inherits the URL or
    anything else the wrapper added;
  * worker_init / worker_resume call the re-exec before their first DB call
    (the guard is on the path, not only defined);
  * scripts/hub/org-python.sh: the venv interpreter, through the wrapper only
    when this host is on the hub.

Every hub file is FAKE (tmp_path). The root conftest already points
MOONIEX_ORG_DB_ENV and MOONIEX_NODE_YAML at missing files, so a test that sets
neither is "off the hub".
"""
from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.worker_mcp_config as wmc  # noqa: E402

SENTINEL = "SENTINEL-G1FIX"
FAKE_URL = f"postgresql://fake:{SENTINEL}@127.0.0.1:1/x"
HUB_VARS = ("MOONIEX_ORG_DB_ENV", "MOONIEX_NODE_YAML", "INFISICAL_CRED_DIR")


@pytest.fixture(autouse=True)
def _no_wrap_marker(monkeypatch):
    # setenv first so teardown restores the original state even when the code
    # under test sets the marker itself through os.environ.
    monkeypatch.setenv(wmc.PRE_WRAP_NAMES, "x")
    monkeypatch.delenv(wmc.PRE_WRAP_NAMES)


@pytest.fixture
def fake_root(tmp_path):
    """A fake Agents root holding the REAL hub scripts and cxo_mcp_config, and a
    `.venv/bin/python` that marks itself and runs this interpreter."""
    r = tmp_path / "agents"
    (r / "scripts" / "hub").mkdir(parents=True)
    (r / "scripts" / "lib").mkdir(parents=True)
    for rel in (
        "scripts/hub/with-org-db-env.sh",
        "scripts/hub/org-python.sh",
        "scripts/lib/cxo_mcp_config.py",
    ):
        shutil.copy(ROOT / rel, r / rel)
    venv_py = r / ".venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text(f'#!/usr/bin/env bash\nG1_VIA_VENV=1 exec "{sys.executable}" "$@"\n')
    venv_py.chmod(0o755)
    return r


@pytest.fixture
def hub_on(tmp_path, monkeypatch):
    """This host is cut over: env file present AND `org_db: hub` in the node file.
    No Infisical identity exists for the fake host. Returns the env file."""
    env_file = tmp_path / "org-db.env"
    env_file.write_text(f"ORG_DB_URL={FAKE_URL}\nG1_ADDED_BY_WRAPPER=1\n")
    node = tmp_path / "node.yaml"
    node.write_text("host: g1test\norg_db: hub\n")
    monkeypatch.setenv("MOONIEX_ORG_DB_ENV", str(env_file))
    monkeypatch.setenv("MOONIEX_NODE_YAML", str(node))
    monkeypatch.setenv("INFISICAL_CRED_DIR", str(tmp_path / "no-infisical"))
    return env_file


def _hub_env() -> dict[str, str]:
    return {k: os.environ[k] for k in HUB_VARS if k in os.environ}


class _Execd(Exception):
    pass


@pytest.fixture
def execvp_calls(monkeypatch):
    calls: list[tuple[str, list[str]]] = []

    def fake(file, args):
        calls.append((file, list(args)))
        raise _Execd()

    monkeypatch.setattr(wmc.os, "execvp", fake)
    return calls


# ------------------------------------------------------------ the re-exec rule


def test_off_the_hub_nothing_is_re_executed(fake_root, execvp_calls):
    wmc.reexec_with_org_db_url("runners.worker_init", ["developer", "task-g1"], root=fake_root)
    assert execvp_calls == []


def test_with_the_url_already_set_nothing_is_re_executed(fake_root, hub_on, execvp_calls, monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", FAKE_URL)
    wmc.reexec_with_org_db_url("runners.worker_init", ["developer", "task-g1"], root=fake_root)
    assert execvp_calls == []


def test_after_one_pass_through_the_wrapper_it_never_loops(fake_root, hub_on, execvp_calls, monkeypatch):
    monkeypatch.setenv(wmc.PRE_WRAP_NAMES, "PATH")
    wmc.reexec_with_org_db_url("runners.worker_init", ["developer", "task-g1"], root=fake_root)
    assert execvp_calls == []


def test_on_the_hub_without_the_url_it_re_execs_through_the_wrapper(
    fake_root, hub_on, execvp_calls, monkeypatch
):
    monkeypatch.setenv("G1_VALUE_CARRIER", SENTINEL)
    with pytest.raises(_Execd):
        wmc.reexec_with_org_db_url("runners.worker_init", ["developer", "task-g1"], root=fake_root)
    wrapper = str(fake_root / "scripts" / "hub" / "with-org-db-env.sh")
    assert execvp_calls == [
        ("bash", ["bash", wrapper, sys.executable, "-m", "runners.worker_init", "developer", "task-g1"])
    ]
    marker = os.environ[wmc.PRE_WRAP_NAMES]
    assert {"G1_VALUE_CARRIER", "PATH"} <= set(marker.split(","))
    assert SENTINEL not in marker  # names, never values


# ------------------------------------------------------- the claude child's env


def test_the_claude_env_drops_everything_the_wrapper_added():
    env = {
        wmc.PRE_WRAP_NAMES: "HOME,PATH,WORKER_X",
        "HOME": "/h",
        "PATH": "/bin",
        "WORKER_X": "1",
        "ORG_DB_URL": FAKE_URL,
        "G1_ADDED_BY_WRAPPER": "1",
    }
    assert wmc.env_without_org_db(env) == {"HOME": "/h", "PATH": "/bin", "WORKER_X": "1"}


def test_the_claude_env_without_a_wrap_loses_only_the_url():
    env = {"HOME": "/h", "ORG_DB_URL": FAKE_URL, "OTHER": "1"}
    assert wmc.env_without_org_db(env) == {"HOME": "/h", "OTHER": "1"}


def test_a_url_the_launcher_already_had_is_still_kept_from_claude():
    env = {wmc.PRE_WRAP_NAMES: "ORG_DB_URL,PATH", "ORG_DB_URL": FAKE_URL, "PATH": "/bin"}
    assert wmc.env_without_org_db(env) == {"PATH": "/bin"}


# ------------------------------------------------ the rule is on the spawn path


@pytest.mark.parametrize("module", ["runners.worker_init", "runners.worker_resume"])
def test_each_runner_re_execs_before_its_first_db_call(module, monkeypatch):
    mod = importlib.import_module(module)
    seen: list[tuple] = []

    def fake_reexec(name, args, *a, **k):
        seen.append(("reexec", name, list(args)))
        raise _Execd()

    monkeypatch.setattr(mod, "reexec_with_org_db_url", fake_reexec)
    monkeypatch.setattr(mod.db, "init", lambda: seen.append(("db.init",)))
    monkeypatch.setattr(mod.sys, "argv", [module, "developer", "task-g1"])
    with pytest.raises(_Execd):
        mod.main()
    assert seen == [("reexec", module, ["developer", "task-g1"])]


def test_both_runners_hand_claude_the_scrubbed_env():
    for rel in ("runners/worker_init.py", "runners/worker_resume.py"):
        src = (ROOT / rel).read_text()
        assert "env = env_without_org_db(os.environ.copy())" in src, rel
        assert "env = os.environ.copy()" not in src, rel


def test_the_hard_resume_fallback_keeps_this_interpreter():
    src = (ROOT / "runners" / "worker_resume.py").read_text()
    assert 'os.execvp("python"' not in src
    assert '[sys.executable, "-m", "runners.worker_init", role, task_id]' in src


# ------------------------------------- end to end, through the real wrapper

PROBE = """
import json, os, sys
sys.path.insert(0, os.environ["G1_REPO"])
from lib.worker_mcp_config import env_without_org_db, reexec_with_org_db_url
reexec_with_org_db_url("g1_probe", sys.argv[1:], root=os.environ["G1_FAKE_ROOT"])
print(json.dumps({
    "argv": sys.argv[1:],
    "has_url": bool(os.environ.get("ORG_DB_URL")),
    "child": sorted(env_without_org_db(dict(os.environ))),
}))
"""


def _run_probe(tmp_path: Path, fake_root: Path) -> subprocess.CompletedProcess:
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    (probe_dir / "g1_probe.py").write_text(PROBE)
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "G1_REPO": str(ROOT),
        "G1_FAKE_ROOT": str(fake_root),
        **_hub_env(),
    }
    return subprocess.run(
        [sys.executable, "-m", "g1_probe", "developer", "task-g1"],
        cwd=probe_dir, env=env, capture_output=True, text=True, timeout=60,
    )


def test_end_to_end_the_wrapper_supplies_the_url_and_claude_never_sees_it(tmp_path, fake_root, hub_on):
    r = _run_probe(tmp_path, fake_root)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["argv"] == ["developer", "task-g1"]
    assert out["has_url"] is True
    assert "ORG_DB_URL" not in out["child"]
    assert "G1_ADDED_BY_WRAPPER" not in out["child"]
    assert wmc.PRE_WRAP_NAMES not in out["child"]
    assert {"PATH", "HOME", "G1_FAKE_ROOT"} <= set(out["child"])
    assert SENTINEL not in r.stdout + r.stderr


def test_end_to_end_a_wrapper_that_cannot_supply_the_url_runs_once(tmp_path, fake_root, hub_on):
    hub_on.write_text("G1_ADDED_BY_WRAPPER=1\n")
    r = _run_probe(tmp_path, fake_root)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["has_url"] is False


# ---------------------------------------------------- scripts/hub/org-python.sh

HAS_URL = 'import os; print(bool(os.environ.get("ORG_DB_URL")))'


def _org_python(fake_root: Path, tmp_path: Path, code: str, extra: dict[str, str]):
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), **extra}
    return subprocess.run(
        ["bash", str(fake_root / "scripts" / "hub" / "org-python.sh"), "-c", code],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )


def test_org_python_on_the_hub_runs_through_the_wrapper(tmp_path, fake_root, hub_on):
    r = _org_python(fake_root, tmp_path, HAS_URL, _hub_env())
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "True"
    assert SENTINEL not in r.stdout + r.stderr


def test_org_python_with_the_switch_off_stays_plain_even_with_the_env_file(tmp_path, fake_root, hub_on):
    Path(os.environ["MOONIEX_NODE_YAML"]).write_text("host: g1test\n")
    r = _org_python(fake_root, tmp_path, HAS_URL, _hub_env())
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "False"


def test_org_python_keeps_a_url_the_caller_already_has(tmp_path, fake_root, hub_on):
    code = 'import os; print(os.environ.get("ORG_DB_URL") == "postgresql://preset")'
    r = _org_python(fake_root, tmp_path, code, {**_hub_env(), "ORG_DB_URL": "postgresql://preset"})
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "True"


def test_org_python_runs_the_venv_interpreter(tmp_path, fake_root):
    code = 'import os; print(os.environ.get("G1_VIA_VENV"))'
    r = _org_python(fake_root, tmp_path, code, {})
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "1"


@pytest.mark.parametrize(
    "rel", ["scripts/terminal-restart.sh", "scripts/cto-claude.sh", "scripts/cxo-claude.sh"]
)
def test_ledger_clis_in_shell_scripts_go_through_org_python(rel):
    src = (ROOT / rel).read_text()
    bare = re.findall(r"python3 -m tools\.(?:terminal_restart|register_cxo|session_reconcile)\b", src)
    assert bare == [], rel
    assert "scripts/hub/org-python.sh -m tools." in src, rel


@pytest.mark.parametrize(
    "rel", [".claude/skills/session-open/SKILL.md", ".claude/skills/session-close/SKILL.md"]
)
def test_the_charter_commands_go_through_org_python(rel):
    src = (ROOT / rel).read_text()
    assert "python3 -m tools.session_charter" not in src, rel
    assert "scripts/hub/org-python.sh -m tools.session_charter" in src, rel
