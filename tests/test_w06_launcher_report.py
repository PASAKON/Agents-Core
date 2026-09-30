"""W0.6 (Org Mesh, runner-routing contract): every codex/agy run launched by
scripts/spawn-worker-remote.sh ends with its report committed on its branch at
docs/reports/<task-id>/REPORT.md, and the launcher never commits its own
bookkeeping files.

These tests EXECUTE the launcher, not just read it: the real script is run
against a local bare "origin" (clone, worktree, TASK.md, .org-task.json,
.worker.pid all get created by the script itself), with fake `tmux`, `codex`
and `agy` on PATH. The generated launch.sh is then run in the foreground and
the committed tree on the pushed branch is asserted. No real codex/agy/tmux is
ever started, nothing touches the network or ssh.

The Windows launcher (windows/spawn-worker.ps1) cannot run on the Mac; its
generated text is asserted in tests/test_spawn_worker_ps1_runners.py and
scripts/test_spawn_worker_ps1.py.

Run via:  pytest tests/test_w06_launcher_report.py
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"
BASH = "/bin/bash"
TASK = "task-w06abc01"
BRANCH = f"agent/developer-{TASK}"
REPORT_PATH = f"docs/reports/{TASK}/REPORT.md"

# Files a codex/agy run must never put on the branch (task brief, step 5).
NEVER_COMMITTED = (
    ".worker.pid", "TASK.md", ".org-task.json", ".org-worker.mcp.json",
    "CTO-FEEDBACK.md", "REPORT.md", "BLOCKER.md", "debug.log",
)
# ...and that the fake CLI / the launcher really put in the worktree, so the
# assertions above cannot pass vacuously.
LEFT_IN_WORKTREE = (
    ".worker.pid", "TASK.md", ".org-task.json", ".org-worker.mcp.json",
    "CTO-FEEDBACK.md", "BLOCKER.md", "debug.log",
)

# One script plays codex AND agy (installed under both names). FAKE_CASE picks
# what the "worker" leaves behind; every case also drops the hostile files a
# real run could leave (CTO scratch, MCP sidecar, a log, a BLOCKER.md).
FAKE_CLI = r"""#!/bin/bash
mode="${FAKE_CASE:-none}"
tid="${FAKE_TASK}"
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "-o" ]; then out="$a"; fi
  prev="$a"
done
echo scratch > CTO-FEEDBACK.md
echo '{}' > .org-worker.mcp.json
echo noise > debug.log
echo blocked > BLOCKER.md
if [ "${FAKE_CODE:-1}" = "1" ]; then mkdir -p src; echo feature > src/feature.txt; fi
case "$mode" in
  docs)
    mkdir -p "docs/reports/$tid"
    printf '# REPORT %s\n\nWORKER-DOCS-BODY\n' "$tid" > "docs/reports/$tid/REPORT.md" ;;
  root)
    printf '# REPORT %s\n\nWORKER-ROOT-BODY\n' "$tid" > REPORT.md ;;
  root_nohdr)
    printf 'WORKER-ROOT-NOHDR-BODY\n' > REPORT.md ;;
  both)
    mkdir -p "docs/reports/$tid"
    printf '# REPORT %s\n\nWORKER-DOCS-BODY\n' "$tid" > "docs/reports/$tid/REPORT.md"
    printf '# REPORT %s\n\nSTRAY-ROOT-BODY\n' "$tid" > REPORT.md ;;
  message)
    if [ -n "$out" ]; then printf 'FINAL-MESSAGE-TEXT\n' > "$out"; fi
    echo "AGY-OUTPUT-LINE" ;;
  flood)
    i=1
    while [ "$i" -le 500 ]; do printf 'L%03d\n' "$i"; i=$((i + 1)); done ;;
  none) : ;;
esac
exit "${FAKE_EXIT:-0}"
"""

FAKE_TMUX = """#!/bin/bash
# The test runs launch.sh itself, in the foreground: new-session starts nothing.
case "$1" in
  list-panes) echo 4242 ;;
esac
exit 0
"""


def _git(cwd: Path, *args: str, env: dict | None = None) -> str:
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"git {' '.join(args)} failed: {r.stderr}"
    return r.stdout


def _exe(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture()
def spoke(tmp_path):
    """A stand-in Linux spoke: local bare origin + a copy of the launcher next
    to the real roles/ docs (so LAUNCH_DIR lands in tmp, not in this repo)."""
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / "gitconfig"),
        "GIT_AUTHOR_NAME": "w06-test", "GIT_AUTHOR_EMAIL": "w06@test.invalid",
        "GIT_COMMITTER_NAME": "w06-test", "GIT_COMMITTER_EMAIL": "w06@test.invalid",
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
    _exe(bindir / "tmux", FAKE_TMUX)
    fake_codex = _exe(bindir / "codex", FAKE_CLI)
    fake_agy = _exe(bindir / "agy", FAKE_CLI)
    _exe(bindir / "claude", "#!/bin/sh\nexit 0\n")
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"

    return SimpleNamespace(
        tmp=tmp_path, env=env, origin=origin, agents=agents,
        script=agents / "scripts" / SCRIPT.name,
        repo=tmp_path / "repo", wt_root=tmp_path / "wt",
        fake_codex=fake_codex, fake_agy=fake_agy,
    )


def _spawn_args(sp, runner: str, task: str, extra: tuple = ()) -> list:
    meta = base64.b64encode(json.dumps({"touches": ["a"]}).encode()).decode()
    return [
        BASH, str(sp.script),
        "--task", task, "--project", "proj", "--role", "developer",
        "--branch", f"agent/developer-{task}", "--base", "main",
        "--repo-url", str(sp.origin), "--repo-path", str(sp.repo),
        "--worktree-root", str(sp.wt_root),
        "--claude-args", "", "--model", "m", "--effort", "high",
        "--session-name", "w06", "--runner", runner,
        "--task-meta-b64", meta, *extra,
    ]


def _spawn(sp, runner: str, task: str = TASK, extra: tuple = ()) -> SimpleNamespace:
    """Run the real launcher (no --dry-run); it writes launch.sh and starts the
    fake tmux. Returns paths to the worktree and the generated launch.sh."""
    r = subprocess.run(_spawn_args(sp, runner, task, extra), input="TASK BRIEF\n",
                       capture_output=True, text=True, env=sp.env, timeout=120)
    assert r.returncode == 0, f"spawn failed rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    assert r.stdout.strip().splitlines()[-1].startswith("SPAWNED pid=")
    launch = sp.agents / f".launch-{task}" / "launch.sh"
    assert launch.is_file()
    return SimpleNamespace(wt=sp.wt_root / f"proj__developer__{task}", launch=launch,
                           task=task, branch=f"agent/developer-{task}")


def _point_agy_at_fake(sp, launch: Path) -> None:
    """The launcher resolves agy as /root/.local/bin/agy first, then PATH. On a
    box that really has /root/.local/bin/agy (Contabo) the generated line would
    start the REAL agy, so aim that one line at the fake before running it."""
    text = launch.read_text(encoding="utf-8")
    new, n = re.subn(r"^(\S+)( -p \"\$\(cat TASK\.md\)\".*--mode accept-edits.*)$",
                     lambda m: f"'{sp.fake_agy}'{m.group(2)}", text, flags=re.MULTILINE)
    assert n == 1, "agy invocation line not found in launch.sh"
    assert "/root/.local/bin/agy" not in new
    launch.write_text(new, encoding="utf-8")


def _run_launch(sp, s, runner: str, *, case: str, exit_code: int = 0, code: bool = True,
                wipe_exclude: bool = False) -> subprocess.CompletedProcess:
    if runner == "agy":
        _point_agy_at_fake(sp, s.launch)
    if wipe_exclude:
        (sp.repo / ".git" / "info" / "exclude").write_text("", encoding="utf-8")
    env = dict(sp.env, FAKE_CASE=case, FAKE_TASK=s.task, FAKE_EXIT=str(exit_code),
               FAKE_CODE="1" if code else "0")
    r = subprocess.run([BASH, str(s.launch)], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"launch.sh failed rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    return r


def _committed(sp, s) -> SimpleNamespace:
    """What actually landed: the tree on the PUSHED branch (read from the bare
    origin), checked against the worktree's own HEAD."""
    remote = set(_git(sp.origin, "ls-tree", "-r", "--name-only", s.branch).splitlines())
    local = set(_git(s.wt, "ls-tree", "-r", "--name-only", "HEAD", env=sp.env).splitlines())
    assert remote == local, "push did not land the worktree's HEAD"
    report = _git(sp.origin, "show", f"{s.branch}:docs/reports/{s.task}/REPORT.md")
    ahead = _git(s.wt, "rev-list", "--count", "origin/main..HEAD", env=sp.env).strip()
    return SimpleNamespace(tree=remote, report=report, ahead=int(ahead))


def _assert_report_committed_and_clean(sp, s, *, code: bool) -> SimpleNamespace:
    got = _committed(sp, s)
    assert f"docs/reports/{s.task}/REPORT.md" in got.tree
    assert got.report.splitlines()[0] == f"# REPORT {s.task}"
    for name in NEVER_COMMITTED:
        assert name not in got.tree, f"{name} was committed"
    assert not any(p.endswith(".log") for p in got.tree)
    assert got.ahead == 1, "expected exactly one commit on the branch"
    assert ("src/feature.txt" in got.tree) is code
    for name in LEFT_IN_WORKTREE:
        assert (s.wt / name).exists(), f"{name} was never in the worktree; the test proves nothing"
    return got


RUNNERS = ("codex", "agy")


# --- the four cases in the brief -------------------------------------------

@pytest.mark.parametrize("runner", RUNNERS)
def test_worker_wrote_docs_path_report_is_kept(spoke, runner):
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="docs")
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    assert "WORKER-DOCS-BODY" in got.report
    assert "Runner:" not in got.report, "a worker's own report must not be rebuilt"


@pytest.mark.parametrize("runner", RUNNERS)
def test_worker_wrote_root_report_is_moved_to_docs_path(spoke, runner):
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="root")
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    assert "WORKER-ROOT-BODY" in got.report
    assert not (s.wt / "REPORT.md").exists(), "root REPORT.md must be moved, not copied"


@pytest.mark.parametrize("runner", RUNNERS)
def test_root_report_without_header_gets_the_header_prepended(spoke, runner):
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="root_nohdr")
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    lines = got.report.splitlines()
    assert lines[0] == f"# REPORT {s.task}"
    assert "WORKER-ROOT-NOHDR-BODY" in got.report
    assert got.report.count(f"# REPORT {s.task}") == 1


@pytest.mark.parametrize("runner", RUNNERS)
def test_no_report_builds_one_from_the_final_message(spoke, runner):
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="message")
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    lines = got.report.splitlines()
    assert lines[0] == f"# REPORT {s.task}"
    assert f"Runner: {runner}" in lines
    assert "Exit code: 0" in lines
    assert ("FINAL-MESSAGE-TEXT" if runner == "codex" else "AGY-OUTPUT-LINE") in got.report


@pytest.mark.parametrize("runner", RUNNERS)
def test_no_report_and_no_final_message_still_commits_a_report(spoke, runner):
    """A run must never end without a report file -- here the worker changed no
    code either, so the report alone is the commit."""
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="none", exit_code=3, code=False)
    got = _assert_report_committed_and_clean(spoke, s, code=False)
    assert "no final message; exit=3" in got.report
    assert f"Runner: {runner}" in got.report.splitlines()
    assert "Exit code: 3" in got.report.splitlines()


# --- second guard, detail cases ---------------------------------------------

@pytest.mark.parametrize("runner", RUNNERS)
def test_reset_guard_alone_keeps_bookkeeping_off_the_branch(spoke, runner):
    """info/exclude emptied: `git add -A` now stages TASK.md, .worker.pid, the
    logs and the stray root files, and only the `git reset` after it stands
    between them and the commit."""
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="message", wipe_exclude=True)
    _assert_report_committed_and_clean(spoke, s, code=True)


@pytest.mark.parametrize("runner", RUNNERS)
def test_root_report_beside_a_docs_report_is_not_committed(spoke, runner):
    s = _spawn(spoke, runner)
    _run_launch(spoke, s, runner, case="both")
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    assert "WORKER-DOCS-BODY" in got.report
    assert "STRAY-ROOT-BODY" not in got.report


def test_agy_report_built_from_the_last_200_log_lines(spoke):
    s = _spawn(spoke, "agy")
    _run_launch(spoke, s, "agy", case="flood")
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    assert "L500" in got.report and "L301" in got.report
    assert "L300" not in got.report


def test_codex_stale_final_message_is_not_reused(spoke):
    """codex-final.txt lives in the per-task launch dir and survives a relaunch;
    a message from an earlier run must not become this run's report."""
    s = _spawn(spoke, "codex")
    stale = spoke.agents / f".launch-{s.task}" / "codex-final.txt"
    stale.write_text("STALE-MESSAGE\n", encoding="utf-8")
    _run_launch(spoke, s, "codex", case="none", exit_code=1)
    got = _assert_report_committed_and_clean(spoke, s, code=True)
    assert "STALE-MESSAGE" not in got.report
    assert "no final message; exit=1" in got.report


def test_info_exclude_is_anchored_and_spares_root_reports(spoke):
    """An unanchored `REPORT.md` line would hide docs/reports/<id>/REPORT.md,
    and root REPORT.md/BLOCKER.md must stay committable for claude workers
    that share this clone (info/exclude is shared by every worktree)."""
    _spawn(spoke, "codex")
    lines = (spoke.repo / ".git" / "info" / "exclude").read_text(encoding="utf-8").splitlines()
    for wanted in (".worker.pid", "/TASK.md", "/.org-task.json", "/.org-worker.mcp.json",
                   "/CTO-FEEDBACK.md", "/*.log", "HEARTBEAT", "MAILBOX.md"):
        assert wanted in lines, f"{wanted} missing from info/exclude: {lines}"
    assert not [ln for ln in lines if "REPORT" in ln or "BLOCKER" in ln]


def test_claude_launch_sh_has_no_report_step(spoke):
    s = _spawn(spoke, "claude")
    text = s.launch.read_text(encoding="utf-8")
    assert "docs/reports" not in text
    assert "git add" not in text
    assert text.splitlines()[-1].startswith("exec ")


# --- --org-host ---------------------------------------------------------------

@pytest.mark.parametrize("runner", ("claude", "codex", "agy"))
def test_org_host_defaults_to_contabo(spoke, runner):
    s = _spawn(spoke, runner)
    lines = s.launch.read_text(encoding="utf-8").splitlines()
    assert "export ORG_HOST=contabo" in lines


@pytest.mark.parametrize("runner", ("claude", "codex", "agy"))
def test_org_host_flag_reaches_launch_sh(spoke, runner):
    s = _spawn(spoke, runner, extra=("--org-host", "hub-linux.2"))
    lines = s.launch.read_text(encoding="utf-8").splitlines()
    assert "export ORG_HOST=hub-linux.2" in lines
    assert "export ORG_HOST=contabo" not in lines


@pytest.mark.parametrize("bad", ("a b", "x;y", "$(id)", "a/b", ""))
def test_org_host_flag_rejects_anything_that_is_not_a_plain_name(spoke, bad):
    r = subprocess.run(_spawn_args(spoke, "codex", TASK, ("--org-host", bad, "--dry-run")),
                       capture_output=True, text=True, env=spoke.env)
    assert r.returncode == 2
    assert "--org-host" in r.stderr and "must match" in r.stderr


# --- dry-run describes the new step -------------------------------------------

def _dry(spoke, runner: str, extra: tuple = ()) -> str:
    r = subprocess.run(_spawn_args(spoke, runner, TASK, ("--dry-run", *extra)),
                       capture_output=True, text=True, env=spoke.env)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.mark.parametrize("runner", RUNNERS)
def test_dry_run_describes_the_report_step(spoke, runner):
    out = _dry(spoke, runner, ("--org-host", "hub-linux"))
    assert "[dry-run] org_host=hub-linux" in out
    report_line = next(ln for ln in out.splitlines() if ln.startswith("[dry-run] report_step:"))
    assert f"/docs/reports/{TASK}/REPORT.md" in report_line
    assert f"'# REPORT {TASK}'" in report_line
    assert f"Runner: {runner}" in report_line
    assert "no final message; exit=<n>" in report_line
    never = next(ln for ln in out.splitlines() if ln.startswith("[dry-run] never_committed:"))
    for name in (".worker.pid", "TASK.md", ".org-task.json", ".org-worker.mcp.json",
                 "CTO-FEEDBACK.md", "REPORT.md", "BLOCKER.md", "*.log"):
        assert name in never


def test_claude_dry_run_is_untouched_by_the_report_step(spoke):
    out = _dry(spoke, "claude")
    assert "report_step" not in out
    assert "never_committed" not in out
    assert "org_host" not in out
