"""Regression coverage for the worker-editable browse guard incident."""
import base64
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import agy_browse as ab, delegate
from tools.guard_commit import gate


@pytest.mark.parametrize("verb", ["click", "type", "key", "upload"])
def test_flow_refuses_writes_before_touching_page(verb):
    policy = ab.load_policy()[9226]
    assert policy.label == "flow" and policy.allowed_hosts == ["labs.google"]
    with pytest.raises(ab.Refused, match="read-only"):
        ab.run_verb(None, policy, None, verb, [])


@pytest.mark.parametrize("verb", ["tabs", "goto", "text", "count", "state", "button-label",
                                  "wait-text", "chips", "shot", "mute"])
def test_read_only_verbs_are_permitted(verb):
    ab.check_read_only(ab.load_policy()[9226], verb)


def test_flow_cli_refuses_without_attaching(monkeypatch, capsys):
    monkeypatch.setattr(ab, "append_log", lambda *args: None)
    def no_session(port):
        pytest.fail("read-only refusal must happen before attaching")
    assert ab.main(["--port", "9226", "click", "button"], session_factory=no_session) == ab.REFUSED
    assert "read-only" in capsys.readouterr().out


def test_existing_port_policies_unchanged():
    import yaml
    old = yaml.safe_load(subprocess.check_output(
        ["git", "show", "HEAD:config/agy-browse.yaml"], cwd=ROOT))
    new = yaml.safe_load(ab.POLICY_PATH.read_text())
    for port in (9224, 9280, 9281):
        assert new["ports"][port] == old["ports"][port]


def test_winbox_does_not_allow_worker_python_or_relative_guard():
    import re
    from test_agy_settings_winbox import NAMED_PY, WT
    rules = json.loads((ROOT / "config/agy-settings-winbox.json").read_text())["permissions"]["allow"]
    patterns = [re.compile(rule[len("command(regex:"):-1]) for rule in rules
                if rule.startswith("command(regex:")]
    guard = r"C:\Users\passg\mooniex\agy-browse\tools\agy_browse.py"
    for cmd in (f"{NAMED_PY} tools/agy_browse.py tabs",
                f"{NAMED_PY} {WT}\\tools\\agy_browse.py tabs",
                f"{WT}\\.venv\\Scripts\\python.exe {guard} tabs"):
        assert not any(p.fullmatch(cmd) for p in patterns)


def test_wildcard_invalidates_whole_policy(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text('ports:\n  9226:\n    allowed_hosts: ["*"]\n')
    with pytest.raises(ab.Refused, match="wildcard"):
        ab.load_policy(p)


def test_policy_is_paired_with_executable_not_worker_cwd_or_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGY_BROWSE_CONFIG", str(tmp_path / "evil.yaml"))
    (tmp_path / "config").mkdir()
    (tmp_path / "config/agy-browse.yaml").write_text('ports: {}')
    assert ab.POLICY_PATH == Path(ab.__file__).resolve().parents[1] / "config/agy-browse.yaml"
    assert ab.load_policy()[9226].read_only


def test_relative_and_worktree_tools_are_never_allowed():
    py = "/opt/MoonieXHQ/Agents/Core/.venv/bin/python"
    for path in ("tools/agy_browse.py", "/tmp/wt/tools/agy_browse.py",
                 "/opt/MoonieXHQ/Agents/Core/worktrees/task/tools/agy_browse.py"):
        assert not ab.allowed_command(f"{py} {path} tabs")


def test_winbox_deploy_pins_origin_bytes_by_hash(monkeypatch, tmp_path):
    blobs = {p: p.encode() for p, _ in delegate._REMOTE_DEPLOY_FILES}
    blobs["roles/browser_operator.md"] = b"role"
    monkeypatch.setattr(delegate, "_fetch_origin", lambda base: None)
    monkeypatch.setattr(delegate, "_origin_blob", lambda base, path: blobs[path])
    monkeypatch.setattr(delegate, "_remote_sha256", lambda *a: None)
    sent = {}
    def run(argv, **kwargs):
        if argv[0] == "scp":
            sent[argv[2]] = Path(argv[1]).read_bytes()
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(delegate.subprocess, "run", run)
    cfg = {"ssh": "winbox", "agents_root": r"C:\Users\passg\mooniex", "os": "windows"}
    delegate._ensure_remote_deploy(cfg, "browser_operator", base="main")
    for rel in ("tools/agy_browse.py", "config/agy-browse.yaml", "tools/guard_commit.py"):
        target = "winbox:" + cfg["agents_root"] + "\\agy-browse\\" + rel.replace("/", "\\")
        assert sent[target] == blobs[rel]
    sent.clear()
    monkeypatch.setattr(delegate, "_remote_sha256", lambda host, path: delegate._bytes_sha256(
        next(blobs[src] for src, dest in (*delegate._REMOTE_DEPLOY_FILES,
             ("roles/browser_operator.md", "roles/browser_operator.md"))
             if path.endswith(dest.replace("/", "\\")))))
    delegate._ensure_remote_deploy(cfg, "browser_operator", base="main")
    assert not sent


PROTECTED = ["tools/agy_browse.py", "config/agy-browse.yaml", "config/agy-settings-winbox.json",
             "windows/new.ps1", "scripts/spawn-worker-remote.sh", "scripts/hook-example.py",
             ".claude/settings.local.json", ".github/workflows/check.yml"]


@pytest.mark.parametrize("operation", ["modify", "delete", "add", "rename"])
def test_staged_guard_edits_never_reach_commit(tmp_path, operation):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args]).decode()
    git("init", "-q")
    git("config", "user.name", "test")
    git("config", "user.email", "test@example.invalid")
    (tmp_path / "README").write_text("base")
    for p in PROTECTED:
        path = tmp_path / p
        path.parent.mkdir(parents=True, exist_ok=True)
        if operation != "add":
            path.write_text("trusted")
    git("add", "-A")
    git("commit", "-m", "base")
    for p in PROTECTED:
        path = tmp_path / p
        if operation == "delete":
            path.unlink()
        elif operation == "rename":
            path.rename(path.with_name(path.name + ".moved"))
        else:
            path.write_text("worker edit")
    report = tmp_path / "REPORT.md"
    report.write_text("# report\n")
    # A worker's rewritten sidecar is deliberately ignored.
    (tmp_path / ".org-task.json").write_text(json.dumps({"touches": ["*"]}))
    git("add", "-A")
    assert set(PROTECTED) <= set(gate(tmp_path, report, ""))
    git("commit", "-m", "worker result")
    changed = git("diff", "HEAD^", "HEAD", "--name-only").splitlines()
    assert not set(PROTECTED) & set(changed)
    for p in PROTECTED:
        assert f"guard file reverted: {p}" in report.read_text()
        if operation != "add":
            assert (tmp_path / p).read_text() == "trusted"
        else:
            assert not (tmp_path / p).exists()


def test_declared_guard_edit_is_kept(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    path = tmp_path / "windows/new.ps1"
    path.parent.mkdir()
    path.write_text("authorized")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    meta = base64.b64encode(json.dumps({"touches": ["windows/"]}).encode()).decode()
    assert gate(tmp_path, tmp_path / "REPORT.md", meta) == []
    assert path.read_text() == "authorized"


def test_both_launchers_gate_before_commit_with_captured_metadata():
    shell = (ROOT / "scripts/spawn-worker-remote.sh").read_text()
    ps = (ROOT / "windows/spawn-worker.ps1").read_text()
    assert '"$GUARD_TASK_META" || exit 1' in shell
    assert '$(sh_quote "$TASK_META_B64")' in shell
    assert shell.index('"$GUARD_COMMIT_TOOL" "$PWD"') < shell.index('commit -q -m')
    assert "`$reportPath '$TaskMetaB64'" in ps
    assert "throw 'guard commit gate failed'" in ps
    assert ps.index("agy-browse\\tools\\guard_commit.py") < ps.index('commit -q -m')
    assert 'Use this pinned absolute path for every browser call' in shell
