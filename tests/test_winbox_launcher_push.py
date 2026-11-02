"""Tests for task-8999a401: winbox launcher local-publish when ORG_MESH_DISPATCH is off."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tools import remote_maintenance as rm

ROOT = Path(__file__).resolve().parent.parent
PS1_SCRIPT = ROOT / "windows" / "spawn-worker.ps1"
SH_SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"
BRANCH = "agent/agy-task-1234abcd"
TASK_ID = "task-1234abcd"


def _run_git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


class FakeGitleaks:
    def __init__(self, monkeypatch, tmp_path):
        self.dir = tmp_path / "fakebin"
        self.dir.mkdir()
        monkeypatch.setenv("PATH", str(self.dir) + os.pathsep + os.environ["PATH"])
        self.set()

    def set(self, code=0, findings=()):
        cfg = json.dumps({"code": code, "findings": list(findings)})
        script = self.dir / "gitleaks"
        script.write_text(
            f"#!{sys.executable}\n"
            + textwrap.dedent(
                """\
                import json, sys
                cfg = json.loads(%r)
                argv = sys.argv[1:]
                report = argv[argv.index('--report-path') + 1]
                with open(report, 'w') as stream:
                    json.dump(cfg['findings'], stream)
                sys.exit(cfg['code'])
                """
            )
            % cfg
        )
        script.chmod(0o755)


@pytest.fixture(autouse=True)
def fake_gitleaks(monkeypatch, tmp_path):
    return FakeGitleaks(monkeypatch, tmp_path)


@pytest.fixture
def worktree_fixture(monkeypatch, tmp_path):
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    trees = tmp_path / "trees"
    trees.mkdir()
    _run_git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _run_git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _run_git(repo, "config", "user.email", "test@example.test")
    _run_git(repo, "config", "user.name", "Test")
    (repo / "base.py").write_text("base = 1\n", encoding="utf-8")
    _run_git(repo, "add", "base.py")
    _run_git(repo, "commit", "-q", "-m", "base")
    _run_git(repo, "remote", "add", "origin", str(origin))
    _run_git(repo, "push", "-q", "origin", "main")

    wt = trees / f"mooniex-agents__developer__{TASK_ID}"
    _run_git(repo, "worktree", "add", "-q", "-b", BRANCH, str(wt))
    _run_git(wt, "config", "user.email", "test@example.test")
    _run_git(wt, "config", "user.name", "Test")
    (wt / "feature.py").write_text("feature = 1\n", encoding="utf-8")
    report_dir = wt / "docs" / "reports" / TASK_ID
    report_dir.mkdir(parents=True)
    (report_dir / "REPORT.md").write_text(f"# REPORT {TASK_ID}\n\nDone\n", encoding="utf-8")
    _run_git(wt, "add", "feature.py", f"docs/reports/{TASK_ID}/REPORT.md")
    _run_git(wt, "commit", "-q", "-m", "work")

    monkeypatch.setattr(rm, "publish_url", lambda w: str(origin))
    return wt, origin


def _render_report_step(*, mesh_dispatch_on: bool, github_route: str = "github.com:22") -> str:
    """Simulate PowerShell's New-ReportStepBody evaluation for flag on vs flag off."""
    text = PS1_SCRIPT.read_text(encoding="utf-8")
    assert "[ValidateSet('', '0', '1')][string]$MeshDispatch = ''" in text
    assert (
        "$meshDispatchOn = if ($MeshDispatch -ne '') { $MeshDispatch -eq '1' } else { [bool]$AgentsRoot }"
        in text
    )
    start = text.index("function New-ReportStepBody")
    end = text.index("if ($Runner -eq 'claude')", start)
    func_text = text[start:end]

    # Extract the return @" ... "@ template and the $localPublishStep template
    local_match = re.search(
        r'\$localPublishStep\s*=\s*@"(\r?\n.*?\r?\n)"@', func_text, flags=re.S
    )
    assert local_match, "could not find $localPublishStep here-string in New-ReportStepBody"
    ret_match = re.search(r'return\s+@"(\r?\n.*?\r?\n)"@', func_text, flags=re.S)
    assert ret_match, "could not find return here-string in New-ReportStepBody"

    git_ssh_cmd = (
        "ssh -o HostName=ssh.github.com -p 443 -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"
        if github_route == "ssh.github.com:443"
        else "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    )
    local_step = ""
    if not mesh_dispatch_on:
        local_step = (
            local_match.group(1)
            .replace("$gitSshCmd", git_ssh_cmd)
            .replace("$agentsRootLit", r"C:\Users\passg\mooniex")
            .replace("$orgCheckoutLit", r"C:\Users\passg\mooniex\org")
            .replace("$wt", r"C:\Users\passg\mooniex\worktrees\mooniex-agents__developer__task-1234abcd")
            .replace("$Branch", BRANCH)
            .replace("$Task", TASK_ID)
            .replace("`$", "$")
        )
    rendered = (
        ret_match.group(1)
        .replace("$localPublishStep", local_step)
        .replace("$wt", r"C:\Users\passg\mooniex\worktrees\mooniex-agents__developer__task-1234abcd")
        .replace("$Task", TASK_ID)
        .replace("${Base}", "main")
        .replace("${Runner}", "agy")
        .replace("$Runner", "agy")
        .replace("`$", "$")
    )
    return rendered


def test_generated_launch_ps1_flag_on_writes_marker_only():
    body = _render_report_step(mesh_dispatch_on=True)
    assert "org-publish-ready" in body
    assert "tools.remote_maintenance" not in body
    assert "local-publish" not in body


def test_generated_launch_ps1_flag_off_writes_marker_and_calls_local_publish():
    body = _render_report_step(mesh_dispatch_on=False, github_route="ssh.github.com:443")
    ready_idx = body.index("org-publish-ready")
    pub_idx = body.index(
        f"-m tools.remote_maintenance local-publish 'C:\\Users\\passg\\mooniex\\worktrees\\mooniex-agents__developer__{TASK_ID}' '{BRANCH}' '{TASK_ID}'"
    )
    assert ready_idx < pub_idx
    assert "HostName=ssh.github.com -p 443" in body
    assert r"C:\Users\passg\mooniex\org" in body


def test_worker_md_excluded_and_reset_in_launchers_and_scratch():
    ps_text = PS1_SCRIPT.read_text(encoding="utf-8")
    assert "'/WORKER.md'" in ps_text
    reset_line = next(ln for ln in ps_text.splitlines() if "reset -q --" in ln)
    assert "WORKER.md" in reset_line
    assert "WORKER.md" in rm.SCRATCH
    assert "WORKER.md" in rm.BRIEF_FILES


def test_linux_launcher_pushes_when_mesh_dispatch_off():
    sh_text = SH_SCRIPT.read_text(encoding="utf-8")
    assert 'if [ "${ORG_MESH_DISPATCH:-0}" != 1 ]' in sh_text


def test_local_publish_succeeds_and_pushes_to_hub_url(worktree_fixture, tmp_path, monkeypatch):
    wt, origin = worktree_fixture
    decoy = tmp_path / "decoy.git"
    _run_git(tmp_path, "init", "-q", "--bare", str(decoy))
    _run_git(wt, "config", "remote.origin.url", str(decoy))

    head = _run_git(wt, "rev-parse", "HEAD").strip()
    res = rm.local_publish(str(wt), BRANCH, TASK_ID)
    assert res == {"branch": BRANCH, "head": head, "pushed": True}
    assert _run_git(origin, "rev-parse", f"refs/heads/{BRANCH}").strip() == head
    assert _run_git(decoy, "branch", "--list").strip() == ""


def test_local_publish_refuses_gitleaks_hit(worktree_fixture, fake_gitleaks):
    wt, origin = worktree_fixture
    fake_gitleaks.set(
        code=1,
        findings=[{"RuleID": "github-pat", "File": "feature.py", "StartLine": 1}],
    )
    with pytest.raises(ValueError, match=r"gitleaks: 1 finding.*not publishing"):
        rm.local_publish(str(wt), BRANCH, TASK_ID)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


@pytest.mark.parametrize("filename", ["clip.mp4", "shot.png"])
def test_local_publish_refuses_media_file(worktree_fixture, filename):
    wt, origin = worktree_fixture
    (wt / filename).write_bytes(b"x" * 64)
    _run_git(wt, "add", filename)
    _run_git(wt, "commit", "-q", "-m", "add media")
    with pytest.raises(ValueError, match="outgoing media"):
        rm.local_publish(str(wt), BRANCH, TASK_ID)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


def test_local_publish_refuses_blob_over_1mb(worktree_fixture):
    wt, origin = worktree_fixture
    (wt / "big.txt").write_bytes(b"a" * 1048577)
    _run_git(wt, "add", "big.txt")
    _run_git(wt, "commit", "-q", "-m", "add >1MB blob")
    with pytest.raises(ValueError, match="outgoing object exceeds 1 MB"):
        rm.local_publish(str(wt), BRANCH, TASK_ID)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


@pytest.mark.parametrize("bad_branch", ["main", "master", "develop", "feature/foo", f"agent/agy-{TASK_ID}-extra"])
def test_local_publish_refuses_base_or_non_agent_branch(worktree_fixture, bad_branch):
    wt, origin = worktree_fixture
    with pytest.raises(ValueError, match="non-agent branch refused"):
        rm.local_publish(str(wt), bad_branch, TASK_ID)
    with pytest.raises(ValueError, match="non-agent branch refused"):
        rm.outgoing_check(wt, bad_branch, push=True)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


@pytest.mark.parametrize(
    "force_ref",
    [
        f"+{BRANCH}",
        f"+refs/heads/{BRANCH}",
        f"{BRANCH}:main",
        f"{BRANCH}:refs/heads/main",
        "--force",
    ],
)
def test_local_publish_refuses_force_push_ref(worktree_fixture, force_ref):
    wt, origin = worktree_fixture
    with pytest.raises(ValueError, match="force or refspec push refused"):
        rm.local_publish(str(wt), force_ref, TASK_ID)
    with pytest.raises(ValueError, match="force or refspec push refused"):
        rm.outgoing_check(wt, force_ref, push=True)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


@pytest.mark.parametrize(
    "brief_file",
    ["TASK.md", "WORKER.md", ".org-task.json", ".org-worker.mcp.json", "CTO-FEEDBACK.md"],
)
def test_local_publish_refuses_committed_brief_file(worktree_fixture, brief_file):
    wt, origin = worktree_fixture
    (wt / brief_file).write_text("brief content\n", encoding="utf-8")
    _run_git(wt, "add", "-f", brief_file)
    _run_git(wt, "commit", "-q", "-m", f"accidentally committed {brief_file}")
    with pytest.raises(ValueError, match="outgoing brief file"):
        rm.local_publish(str(wt), BRANCH, TASK_ID)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


def test_local_publish_enforces_4gb_ram_floor_on_windows(worktree_fixture, monkeypatch):
    from tools import node_dispatch as nd

    wt, origin = worktree_fixture
    monkeypatch.setattr(rm, "_native_windows", lambda: True)
    monkeypatch.setattr(nd, "_win_avail_phys_bytes", lambda: 3 * 1024**3)
    with pytest.raises(ValueError, match="winbox requires 4 GB free RAM"):
        rm.local_publish(str(wt), BRANCH, TASK_ID)
    assert _run_git(origin, "branch", "--list", BRANCH).strip() == ""


def test_scratch_repo_writes_lf_alternates(worktree_fixture):
    wt, origin = worktree_fixture
    head = _run_git(wt, "rev-parse", "HEAD").strip()
    with rm.scratch_repo(wt, str(origin), head) as repo:
        raw = (repo / "objects" / "info" / "alternates").read_bytes()
        assert raw.endswith(b"/objects\n")
        assert b"\r" not in raw

