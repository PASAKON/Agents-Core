"""Tests for H3: Runner model launch and media gate (PLAN-auto-dispatch.md row H3).

Verifies:
1. tools/delegate.py: _task_meta carries runner_model.
2. tools/delegate.py: _spawn_remote reads fresh task from db.get_task(task_id).
3. scripts/spawn-worker-remote.sh: dry-run shows the chosen model for agy and codex.
4. scripts/spawn-worker-remote.sh: empty runner_model falls back (agy -> gemini-3.8-flash-high, codex -> no -m).
5. scripts/spawn-worker-remote.sh: bad values ('x; rm -rf /', a space, 65 chars) refuse to launch (exit 2).
6. scripts/spawn-worker-remote.sh: media gate unstages a .mp4 and a 2 MB binary and keeps a 2 MB .txt,
   appending to REPORT.md under "## Blockers" without deleting the files from disk.
7. windows/spawn-worker.ps1: text assertions for validation, fallback, and media gate.
"""
from __future__ import annotations

import base64
import contextlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import lib.db as db
import tools.delegate as delegate
import tools.wiki as wiki_tools

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"
PS1_SCRIPT = ROOT / "windows" / "spawn-worker.ps1"
BASH = "/bin/bash"

FAKE_TMUX = """#!/bin/bash
case "$1" in
  list-panes) echo 4242 ;;
esac
exit 0
"""


def _b64_meta(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("ascii")


def _run_script(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    base_args = [
        BASH, str(SCRIPT),
        "--task", "task-h3test",
        "--project", "mooniex-agents",
        "--role", "developer",
        "--branch", "agent/developer-task-h3test",
        "--base", "main",
        "--repo-url", "git@github.com:example/repo.git",
        "--repo-path", "/tmp/repo",
        "--worktree-root", "/tmp/wt",
        "--claude-args", "",
        "--model", "claude-sonnet-5-5",
        "--effort", "high",
        "--session-name", "test-session",
    ]
    return subprocess.run(
        [*base_args, *args],
        capture_output=True,
        text=True,
        env=env or os.environ,
    )


# ==============================================================================
# 1. tools/delegate.py: _task_meta carries runner_model
# ==============================================================================

def test_task_meta_carries_runner_model():
    task = {
        "id": "task-test01",
        "project": "mooniex-agents",
        "role": "developer",
        "owner_cto": "e6754203",
        "touches": json.dumps(["scripts/a.sh"]),
        "runner_model": "claude-sonnet-4-6",
    }
    meta = delegate._task_meta(task, "contabo")
    assert meta["runner_model"] == "claude-sonnet-4-6"
    assert meta["task_id"] == "task-test01"
    assert meta["touches"] == ["scripts/a.sh"]


def test_task_meta_runner_model_empty_or_none():
    task = {
        "id": "task-test02",
        "project": "mooniex-agents",
        "role": "developer",
        "owner_cto": "e6754203",
        "touches": "[]",
    }
    meta = delegate._task_meta(task, "contabo")
    assert meta["runner_model"] is None


def test_spawn_remote_refreshes_task_from_db(tmp_path, monkeypatch):
    """Verify that _spawn_remote reads fresh task from db.get_task(task_id)."""
    import asyncio
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init()

    task_id = "task-fresh01"
    with db.get_conn() as conn:
        now = db.now_iso()
        conn.execute(
            """INSERT INTO tasks (id, project, role, status, title, description, touches,
               depends_on, branch, host, runner, runner_model, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, "mooniex-agents", "developer", "pending", "Test", "Desc", "[]",
             "[]", "agent/developer-task-fresh01", "contabo", "agy", "claude-sonnet-4-6", now, now),
        )
        conn.commit()

    # Stale dict: the full row as the caller holds it, before the router's
    # set_fields wrote runner_model (real callers pass the whole row).
    stale_dict = dict(db.get_task(task_id))
    stale_dict["runner_model"] = None

    res = asyncio.run(delegate._spawn_remote(stale_dict, "contabo", dry_run=True))
    assert res is not None

    # Verify delegate_log dry-run output contains task_meta_b64 decoding to runner_model
    log_text = res.get("delegate_log") or ""
    m = re.search(r"--task-meta-b64\s+(\S+)", log_text)
    assert m, f"task-meta-b64 not found in dry-run ssh_cmd: {log_text}"
    decoded = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    assert decoded.get("runner_model") == "claude-sonnet-4-6"



def _insert_task(task_id, runner, runner_model, host):
    with db.get_conn() as conn:
        now = db.now_iso()
        conn.execute(
            """INSERT INTO tasks (id, project, role, status, title, description, touches,
               depends_on, branch, host, runner, runner_model, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, "mooniex-agents", "developer", "pending", "Test", "Desc", "[]",
             "[]", f"agent/developer-{task_id}", host, runner, runner_model, now, now),
        )
        conn.commit()


def test_winbox_ssh_command_carries_runner_model_for_agy(tmp_path, monkeypatch):
    """CTO review: the winbox leg must hand the router's model to spawn-worker.ps1."""
    import asyncio
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()
    _insert_task("task-winrm01", "agy", "claude-sonnet-4-6", "winbox")
    task = dict(db.get_task("task-winrm01"))
    task["runner_model"] = None if "agy" != "claude" else task["runner_model"]
    task["runner"] = "agy"
    res = asyncio.run(delegate._spawn_remote(task, "winbox", dry_run=True))
    log_text = res.get("delegate_log") or ""
    assert '-RunnerModel "claude-sonnet-4-6"' in log_text, log_text


def test_winbox_ssh_command_has_no_runner_model_for_claude(tmp_path, monkeypatch):
    import asyncio
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()
    _insert_task("task-winrm02", "claude", "claude-sonnet-4-6", "winbox")
    task = dict(db.get_task("task-winrm02"))
    task["runner_model"] = None if "claude" != "claude" else task["runner_model"]
    task["runner"] = "claude"
    res = asyncio.run(delegate._spawn_remote(task, "winbox", dry_run=True))
    assert "-RunnerModel" not in (res.get("delegate_log") or "")


def test_fresh_read_keeps_the_callers_other_fields(tmp_path, monkeypatch):
    """Only runner_model is read back; a field the caller set in memory survives."""
    import asyncio
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()
    _insert_task("task-keep01", None, "gpt-5.5", "contabo")
    task = dict(db.get_task("task-keep01"))
    task["runner_model"] = None if "codex" != "claude" else task["runner_model"]
    task["runner"] = "codex"
    res = asyncio.run(delegate._spawn_remote(task, "contabo", dry_run=True))
    log_text = res.get("delegate_log") or ""
    assert "--runner codex" in log_text or "--runner 'codex'" in log_text, log_text

# ==============================================================================
# 2. scripts/spawn-worker-remote.sh: dry-run shows model chosen & empty falls back
# ==============================================================================

def test_dry_run_shows_chosen_model_agy():
    meta = _b64_meta({"runner_model": "claude-sonnet-4-6"})
    r = _run_script("--runner", "agy", "--task-meta-b64", meta, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "[dry-run] runner_model=claude-sonnet-4-6" in r.stdout
    assert "--model claude-sonnet-4-6" in r.stdout


def test_dry_run_shows_chosen_model_codex():
    meta = _b64_meta({"runner_model": "o3-mini"})
    r = _run_script("--runner", "codex", "--task-meta-b64", meta, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "[dry-run] runner_model=o3-mini" in r.stdout
    assert "codex exec" in r.stdout
    assert "-m 'o3-mini'" in r.stdout  # same quoting as the real launch.sh (PR #228)


def test_dry_run_empty_runner_model_falls_back_agy():
    meta = _b64_meta({"touches": []})
    r = _run_script("--runner", "agy", "--task-meta-b64", meta, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "[dry-run] runner_model=gemini-3.8-flash-high" in r.stdout
    assert "--model gemini-3.8-flash-high" in r.stdout


def test_dry_run_empty_runner_model_falls_back_codex():
    meta = _b64_meta({"touches": []})
    r = _run_script("--runner", "codex", "--task-meta-b64", meta, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "[dry-run] runner_model=(none)" in r.stdout
    cmd_line = next(ln for ln in r.stdout.splitlines() if ln.startswith("[dry-run] cmd="))
    assert " -m " not in cmd_line


# ==============================================================================
# 3. scripts/spawn-worker-remote.sh: validation refuses bad values
# ==============================================================================

@pytest.mark.parametrize("bad_val", [
    "x; rm -rf /",
    "model with spaces",
    "a" * 65,
    "model$bad",
    "model`bad`",
    "model|bad",
])
def test_bad_runner_model_refused(bad_val):
    meta = _b64_meta({"runner_model": bad_val})
    r = _run_script("--runner", "agy", "--task-meta-b64", meta, "--dry-run")
    assert r.returncode == 2
    assert "invalid runner_model" in r.stderr or "exceeds 64 chars" in r.stderr


# ==============================================================================
# 4. Media gate in scripts/spawn-worker-remote.sh
# ==============================================================================

def _git(cwd: Path, *args: str, env: dict | None = None) -> str:
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"git {' '.join(args)} failed: {r.stderr}"
    return r.stdout


@pytest.fixture()
def media_gate_env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / "gitconfig"),
        "GIT_AUTHOR_NAME": "h3-test", "GIT_AUTHOR_EMAIL": "h3@test.invalid",
        "GIT_COMMITTER_NAME": "h3-test", "GIT_COMMITTER_EMAIL": "h3@test.invalid",
    }

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True, env=env)
    _git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", str(seed)], check=True, env=env)
    _git(seed, "checkout", "-q", "-b", "main", env=env)
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "-A", env=env)
    _git(seed, "commit", "-q", "-m", "seed", env=env)
    _git(seed, "remote", "add", "origin", str(origin), env=env)
    _git(seed, "push", "-q", "origin", "main", env=env)

    agents = tmp_path / "agents_root"
    (agents / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, agents / "scripts" / SCRIPT.name)
    shutil.copytree(ROOT / "roles", agents / "roles")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    tmux_bin = bindir / "tmux"
    tmux_bin.write_text(FAKE_TMUX, encoding="utf-8")
    tmux_bin.chmod(0o755)

    fake_runner = bindir / "fake_runner"
    fake_runner.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    fake_runner.chmod(0o755)
    # --runner codex makes the script look for a `codex` before it writes launch.sh and, when there is
    # none, print SPAWN_REFUSED=codex-not-found on STDOUT and exit 1. The Mac has one, ubuntu CI does not.
    (bindir / "codex").symlink_to(fake_runner)

    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"

    return SimpleNamespace(
        tmp=tmp_path, env=env, origin=origin, agents=agents,
        script=agents / "scripts" / SCRIPT.name,
        repo=tmp_path / "repo", wt_root=tmp_path / "wt",
        fake_runner=fake_runner,
    )


def _media_spawn(sp, task_id, branch, env=None):
    """Run the spawn script (creates the worktree and launch.sh) against the fixture's origin."""
    spawn_cmd = [
        BASH, str(sp.script),
        "--task", task_id,
        "--project", "proj",
        "--role", "developer",
        "--branch", branch,
        "--base", "main",
        "--repo-url", str(sp.origin),
        "--repo-path", str(sp.repo),
        "--worktree-root", str(sp.wt_root),
        "--claude-args", "",
        "--model", "claude-sonnet-5-5",
        "--effort", "high",
        "--session-name", "media-test",
        "--runner", "codex",
    ]
    return subprocess.run(spawn_cmd, input="TASK BRIEF\n", capture_output=True, text=True, env=env or sp.env)


def test_spawn_refuses_the_codex_runner_on_stdout_when_no_codex_is_installed(media_gate_env):
    # What ubuntu CI saw as "exit 1 right after Preparing worktree": the refusal is a stdout line, and
    # stderr only holds git's clone/worktree chatter. The probe list is PATH, /usr/bin/codex,
    # /usr/local/bin/codex, then ~/.local/bin and ~/.npm-global/bin (HOME is a tmp dir here).
    sp = media_gate_env
    (sp.tmp / "bin" / "codex").unlink()
    env = {**sp.env, "PATH": f"{sp.tmp / 'bin'}{os.pathsep}/usr/bin{os.pathsep}/bin"}
    r = _media_spawn(sp, "task-h3nocodex", "agent/developer-task-h3nocodex", env=env)
    if any(Path(p).exists() for p in ("/usr/bin/codex", "/usr/local/bin/codex")):
        assert r.returncode == 0, f"{r.stderr}\n{r.stdout}"  # this machine has a codex at an absolute probe path
    else:
        assert r.returncode == 1
        assert "SPAWN_REFUSED=codex-not-found" in r.stdout
        assert "SPAWN_REFUSED" not in r.stderr


def test_media_gate_unstages_mp4_and_large_binary_and_keeps_large_text(media_gate_env):
    sp = media_gate_env
    task_id = "task-h3media01"
    branch = f"agent/developer-{task_id}"

    # Spawn worker (creates worktree and launch.sh)
    r = _media_spawn(sp, task_id, branch)
    assert r.returncode == 0, f"{r.stderr}\n{r.stdout}"

    wt = sp.wt_root / f"proj__developer__{task_id}"
    launch_sh = sp.agents / f".launch-{task_id}" / "launch.sh"
    assert launch_sh.is_file()

    # Create worker files in the worktree:
    # 1. A media file (.mp4)
    (wt / "clip.mp4").write_bytes(b"fake-mp4-video-data-12345")
    # 2. A large binary (> 1 MB, e.g. 2 MB)
    (wt / "large.bin").write_bytes(b"\x00\x01\x02\x03\xff" * (2 * 1024 * 1024 // 5))
    # 3. A large text file (> 1 MB, e.g. 2 MB)
    (wt / "large.txt").write_text("Hello world text data!\n" * (2 * 1024 * 1024 // 23), encoding="utf-8")
    # 4. Standard code file
    (wt / "app.py").write_text("print('ok')\n", encoding="utf-8")

    # Create a base REPORT.md
    report_dir = wt / "docs" / "reports" / task_id
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "REPORT.md").write_text(
        f"# REPORT {task_id}\n\n## Files changed\n- app.py\n\n## What was done\nBuilt feature.\n\n## Blockers\n- None\n",
        encoding="utf-8",
    )

    # Point codex exec at fake_runner to exit immediately and run the report step
    launch_text = launch_sh.read_text(encoding="utf-8")
    launch_text = launch_text.replace("codex exec", f"'{sp.fake_runner}'")
    launch_sh.write_text(launch_text, encoding="utf-8")

    # Run launch.sh (foreground)
    lr = subprocess.run([BASH, str(launch_sh)], capture_output=True, text=True, env=sp.env)
    assert lr.returncode == 0, f"launch.sh failed: {lr.stderr}\n{lr.stdout}"

    # Verify git committed tree on origin
    committed_files = set(_git(sp.origin, "ls-tree", "-r", "--name-only", branch).splitlines())

    # large.txt and app.py and REPORT.md MUST be committed
    assert "large.txt" in committed_files, "2 MB text file must be committed"
    assert "app.py" in committed_files
    assert f"docs/reports/{task_id}/REPORT.md" in committed_files

    # clip.mp4 and large.bin MUST NOT be committed
    assert "clip.mp4" not in committed_files, "mp4 must be unstaged by media gate"
    assert "large.bin" not in committed_files, "2 MB binary must be unstaged by media gate"

    # Files must NOT be deleted from disk
    assert (wt / "clip.mp4").is_file(), "clip.mp4 must remain on disk"
    assert (wt / "large.bin").is_file(), "large.bin must remain on disk"
    assert (wt / "large.txt").is_file()

    # Check REPORT.md content
    report_content = _git(sp.origin, "show", f"{branch}:docs/reports/{task_id}/REPORT.md")
    assert "## Blockers" in report_content
    assert "media not committed: clip.mp4" in report_content
    assert "media not committed: large.bin" in report_content
    assert "upload per CXO_Rules_GDrive_Filing and put the link here" in report_content
    assert "media not committed: large.txt" not in report_content


# ==============================================================================
# 5. windows/spawn-worker.ps1: text assertions
# ==============================================================================

def test_spawn_worker_ps1_text_assertions():
    text = PS1_SCRIPT.read_text(encoding="utf-8")

    # Regex validation for runner_model
    assert "RunnerModel" in text
    assert "TaskMetaB64" in text
    assert r"^[A-Za-z0-9._:-]{1,64}$" in text

    # Model flag handling
    assert "gemini-3.8-flash-high" in text
    assert "'-m'" in text or "'-m'," in text
    assert "--model" in text

    # Media gate in New-ReportStepBody
    assert "mediaExts" in text
    for ext in ["png", "jpg", "mp4", "mov", "wav", "flac"]:
        assert f"'{ext}'" in text

    assert "1048576" in text
    assert "media not committed:" in text
    assert "upload per CXO_Rules_GDrive_Filing and put the link here" in text
    assert "git -C '$wt' reset -q --" in text


# ==============================================================================
# 6. Syntax and related script verifications
# ==============================================================================

def test_bash_n_spawn_worker_remote():
    r = subprocess.run([BASH, "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, f"bash -n failed: {r.stderr}"


def test_script_mcp_role_config_verdict():
    import sys
    script = ROOT / "scripts" / "test_mcp_role_config.py"
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert r.returncode == 0, f"test_mcp_role_config.py failed: {r.stderr}\n{r.stdout}"
    assert "OK — 0 failure(s)" in r.stdout


def test_script_org_tools_registry_verdict():
    import sys
    script = ROOT / "scripts" / "test_org_tools_registry.py"
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert r.returncode == 0, f"test_org_tools_registry.py failed: {r.stderr}\n{r.stdout}"
    assert "ALL PASS" in r.stdout


@contextlib.contextmanager
def _org_wiki_at(root: Path):
    """Point WIKI_ROOT_ORG at `root` for one block; the cached root table is rebuilt on the way in and out."""
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("WIKI_ROOT_ORG", str(root))
            wiki_tools._roots.cache_clear()
            yield
    finally:
        wiki_tools._roots.cache_clear()


def test_wiki_list_is_sorted_whatever_order_the_filesystem_lists(tmp_path):
    # ext4 lists a directory in hash order, APFS sorted; the registry and cto_mcp_server.py must still
    # answer identically. Force the worst order (reversed) instead of trusting the runner's filesystem.
    from lib import toon
    from runners import cto_mcp_server as srv
    org = tmp_path / "org"
    (org / "decisions").mkdir(parents=True)
    for name in ("0013-c.md", "0001-a.md", "0009-b.md"):
        (org / "decisions" / name).write_text(f"# {name}\n", encoding="utf-8")
    real_rglob = Path.rglob
    expected = toon.encode([f"org:decisions/{n}" for n in ("0001-a.md", "0009-b.md", "0013-c.md")])
    with _org_wiki_at(org), pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "rglob", lambda self, pattern: iter(sorted(real_rglob(self, pattern), reverse=True)))
        assert srv.wiki_list("org:decisions") == expected


def test_wiki_list_without_an_org_wiki_is_the_same_error_on_both_sides(tmp_path):
    # ubuntu CI has no Agents/Rules checkout: both sides return this string, so an equivalence check that
    # also wants a "[" list back fails there unless it builds its own wiki (scripts/test_org_tools_registry.py).
    from lib import org_tools_registry as reg
    from runners import cto_mcp_server as srv
    with _org_wiki_at(tmp_path / "no-such-wiki"):
        got = srv.wiki_list("org:decisions")
        assert got == reg.dispatch_sync("wiki_list", prefix="org:decisions")
        assert got == "ERROR: wiki 'org' not available in this environment"


def test_ps1_generated_strings_are_ascii():
    """PowerShell 5.1 reads a BOM-less script as ANSI: an em dash (E2 80 94)
    becomes a cp1252 right double quote and ends the string literal. Only
    comment lines may carry non-ASCII."""
    text = (ROOT / "windows" / "spawn-worker.ps1").read_text(encoding="utf-8")
    bad = [ (n, ln) for n, ln in enumerate(text.splitlines(), 1)
            if any(ord(c) > 127 for c in ln) and not ln.lstrip().startswith("#") ]
    assert not bad, bad
