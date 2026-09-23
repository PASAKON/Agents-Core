"""Tests for scripts/hq_migrate_step4b.py (HQ migration step 4b, ADR 0028).

Every test runs against a fake HQ_ROOT / repo root / state dir / launchd dir
/ claude projects dir / claude.json / tasks.db under tmp_path via env-var
overrides — never touches the real ~/MoonieXHQ, ~/Projects, ~/.claude or
~/.claude.json. The fixture builds a real git repo with a real bare "origin"
remote and a real attached `git worktree` (plus a dangling one) so
preflight/push/worktree-repair are real git, not mocks.

Run: /Users/gob/Projects/Agents/.venv/bin/python -m pytest scripts/test_hq_migrate_step4b.py -q
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "hq_migrate_step4b.py"
sys.path.insert(0, str(ROOT / "scripts"))
import hq_migrate_step4b as mod  # noqa: E402  (pure-function unit tests use this directly)

GIT_ENV_EXTRA = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
}

_TASKS_SCHEMA = """
CREATE TABLE tasks (
    id TEXT PRIMARY KEY, project TEXT NOT NULL, role TEXT NOT NULL,
    status TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
    touches TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    r = subprocess.run(["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} in {cwd} failed: {r.stdout}{r.stderr}"
    return r


def _head(repo: Path) -> str:
    return _git(["rev-parse", "HEAD"], repo).stdout.strip()


def _make_tasks_db(db_path: Path, rows: list[dict]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_TASKS_SCHEMA)
    for r in rows:
        conn.execute(
            "INSERT INTO tasks (id, project, role, status, title, description, touches, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (r["id"], "mooniex-agents", r.get("role", "developer"), r["status"],
             r.get("title", "t"), r.get("description", "d"), json.dumps(r.get("touches", [])),
             "2026-01-01", "2026-01-01"),
        )
    conn.commit()
    conn.close()


def _build_fixture(tmp: Path, *, task_rows: list[dict] | None = None) -> dict:
    hq = tmp / "hq"
    (hq / "scripts").mkdir(parents=True)

    origins_dir = tmp / "origins"
    origins_dir.mkdir()
    origin = origins_dir / "agents-origin.git"
    origin.mkdir()
    _git(["init", "--bare", "-b", "main"], origin)

    core = tmp / "Projects" / "Agents"
    core.mkdir(parents=True)
    _git(["init", "-b", "main"], core)
    (core / "README.md").write_text("agents-core\n")
    (core / "config").mkdir()
    (core / "config" / "sample.yaml").write_text(f"path: {core}\n")
    _git(["add", "-A"], core)
    _git(["commit", "-m", "init"], core)
    _git(["remote", "add", "origin", str(origin)], core)
    _git(["push", "-u", "origin", "main"], core)

    # a real attached worktree (must survive repair) + a dangling entry
    worktrees_dir = core / "worktrees"
    worktrees_dir.mkdir()
    live_wt = worktrees_dir / "mooniex-agents__developer__task-bbbbbbbb"
    _git(["worktree", "add", "-b", "agent/dev-b", str(live_wt)], core)
    dangling_wt = worktrees_dir / "mooniex-agents__developer__task-cccccccc"
    _git(["worktree", "add", "-b", "agent/dev-c", str(dangling_wt)], core)
    shutil.rmtree(dangling_wt)  # deleted without `git worktree remove` -> dangling

    state_dir = tmp / "state"
    tasks_db = state_dir / "tasks.db"
    _make_tasks_db(tasks_db, task_rows if task_rows is not None else [
        {"id": "task-95439aa8", "status": "in_progress", "title": "this migration"},
    ])

    launchd_dir = tmp / "LaunchAgents"
    launchd_dir.mkdir()
    (launchd_dir / "com.mooniex.agents-watchdog.plist").write_text(
        "<?xml version=\"1.0\"?><plist><dict>"
        f"<key>ProgramArguments</key><array><string>{core}/.venv/bin/python</string></array>"
        f"<key>WorkingDirectory</key><string>{core}</string>"
        "</dict></plist>\n"
    )
    (launchd_dir / "com.mooniex.cfo-claude-usage.plist").write_text(
        "<?xml version=\"1.0\"?><plist><dict>"
        f"<key>ProgramArguments</key><array><string>{core}/scripts/x.sh</string></array>"
        "</dict></plist>\n"
    )
    # com.mooniex.mac-agent.plist deliberately absent — must be skipped, not fatal

    claude_projects = tmp / "claude-projects"
    claude_projects.mkdir()
    old_slug = str(core).replace("/", "-")
    (claude_projects / old_slug).mkdir()
    (claude_projects / old_slug / "marker.txt").write_text("old slug dir\n")

    claude_json = tmp / "claude.json"
    claude_json.write_text(json.dumps({
        "numStartups": 5,
        "projects": {
            str(core): {"hasTrustDialogAccepted": True, "allowedTools": ["Bash(git *)"]},
            "/Users/gob/some/other/project": {"hasTrustDialogAccepted": True, "unrelatedField": 123},
        },
    }, indent=2))

    hq_yaml_text = f"""version: 1
root: {hq}
repo: TEST/hq
folders:
  - path: Agents
    kind: group
    owner: CTO
  - path: Agents/Core
    kind: own
    owner: CTO
    current: {core}
    step: 4
compat_links:
"""
    (hq / "hq.yaml").write_text(hq_yaml_text)

    return {
        "hq": hq, "core": core, "origin": origin, "live_wt": live_wt,
        "tasks_db": tasks_db, "launchd_dir": launchd_dir,
        "claude_projects": claude_projects, "old_slug_dir": claude_projects / old_slug,
        "claude_json": claude_json, "state_dir": state_dir,
    }


def _env(tmp: Path, f: dict, *, task_id: str | None = "task-95439aa8") -> dict:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    env.update({
        "HQ_ROOT": str(f["hq"]),
        "HQ_STEP4B_STATE_DIR": str(f["state_dir"]),
        "HQ_STEP4B_REPO_ROOT": str(ROOT),
        "HQ_STEP4B_TASKS_DB": str(f["tasks_db"]),
        "HQ_STEP4B_LAUNCHD_DIR": str(f["launchd_dir"]),
        "HQ_STEP4B_CLAUDE_PROJECTS_DIR": str(f["claude_projects"]),
        "HQ_STEP4B_CLAUDE_JSON": str(f["claude_json"]),
        "HQ_PYTHON": sys.executable,
    })
    if task_id is not None:
        env["ORG_TASK_ID"] = task_id
    else:
        env.pop("ORG_TASK_ID", None)
    return env


def _run_cli(tmp: Path, f: dict, *args: str, task_id: str | None = "task-95439aa8") -> subprocess.CompletedProcess:
    env = _env(tmp, f, task_id=task_id)
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True, cwd=str(tmp))


def _manifest(f: dict) -> dict:
    files = sorted(f["state_dir"].glob("hq-step4b-migration-*.json"))
    assert files, "no manifest written"
    return json.loads(files[-1].read_text())


# ─────────────────────────── plan ────────────────────────────────────────────

def test_plan_changes_nothing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    r = _run_cli(tmp_path, f, "--plan")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MOVE" in r.stdout and str(f["core"]) in r.stdout
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before


def test_plan_reports_gate_would_block(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, task_rows=[
        {"id": "task-95439aa8", "status": "in_progress"},
        {"id": "task-67f82679", "status": "in_progress", "title": "BL real-footage runner"},
    ])
    r = _run_cli(tmp_path, f, "--plan")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WOULD BLOCK" in r.stdout
    assert "task-67f82679" in r.stdout


# ─────────────────────────── the hard gate ───────────────────────────────────

def test_gate_blocks_apply_when_other_task_in_flight(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, task_rows=[
        {"id": "task-95439aa8", "status": "in_progress"},
        {"id": "task-67f82679", "status": "in_progress", "role": "developer", "title": "BL real-footage runner"},
        {"id": "task-77a2e043", "status": "rate_limited", "role": "developer", "title": "BL EP55 pipeline"},
    ])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "BLOCKED" in r.stdout
    assert "task-67f82679" in r.stdout and "task-77a2e043" in r.stdout
    # nothing touched
    assert f["core"].is_dir() and not f["core"].is_symlink()
    assert not (f["hq"] / "Agents" / "Core").exists()
    assert not list(f["state_dir"].glob("hq-step4b-*"))


def test_gate_allows_apply_when_other_tasks_are_terminal_or_self(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, task_rows=[
        {"id": "task-95439aa8", "status": "in_progress"},  # self — excluded
        {"id": "task-old1", "status": "done"},
        {"id": "task-old2", "status": "merged"},
        {"id": "task-old3", "status": "failed"},
    ])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (f["hq"] / "Agents" / "Core").is_dir()


def test_gate_refuses_when_tasks_db_missing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    f["tasks_db"].unlink()
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "BLOCKED" in r.stdout
    assert f["core"].is_dir() and not f["core"].is_symlink()


# ─────────────────────────── the one atomic step (unit) ──────────────────────

def test_atomic_move_and_link_moves_and_symlinks_in_one_call(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "f.txt").write_text("hi\n")
    dst = tmp_path / "nested" / "dst"
    mod.atomic_move_and_link(src, dst)
    assert dst.is_dir()
    assert (dst / "f.txt").read_text() == "hi\n"
    assert src.is_symlink()
    assert Path(os.readlink(src)) == dst


def test_atomic_move_and_link_refuses_cross_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "src2"
    src.mkdir()
    dst = tmp_path / "dst2"

    monkeypatch.setattr(mod, "_same_device", lambda a, b: False)
    with pytest.raises(RuntimeError, match="different volumes"):
        mod.atomic_move_and_link(src, dst)
    assert src.is_dir() and not src.is_symlink()
    assert not dst.exists()


def test_atomic_move_and_link_refuses_existing_target(tmp_path: Path) -> None:
    src = tmp_path / "src3"
    src.mkdir()
    dst = tmp_path / "dst3"
    dst.mkdir()
    with pytest.raises(RuntimeError, match="already exists"):
        mod.atomic_move_and_link(src, dst)


# ─────────────────────────── full apply ──────────────────────────────────────

def test_apply_moves_core_verifies_sha_and_symlinks(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    sha_before = _head(f["core"])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Agents" / "Core"
    assert target.is_dir()
    assert f["core"].is_symlink()
    assert Path(os.readlink(f["core"])) == target
    assert _head(target) == sha_before


def test_apply_repairs_live_worktree_and_prunes_dangling(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    st = subprocess.run(["git", "-C", str(f["live_wt"]), "status"], capture_output=True, text=True)
    assert st.returncode == 0, st.stdout + st.stderr
    m = _manifest(f)
    assert any(o["op"] == "worktree_repair" for o in m["ops"])
    repaired = [o["worktree"] for o in m["ops"] if o["op"] == "worktree_repair"]
    assert all("task-cccccccc" not in w for w in repaired)


def test_apply_rewrites_launchd_plists_and_lints(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Agents" / "Core"
    watchdog = (f["launchd_dir"] / "com.mooniex.agents-watchdog.plist").read_text()
    assert str(target) in watchdog and str(f["core"]) not in watchdog
    cfo = (f["launchd_dir"] / "com.mooniex.cfo-claude-usage.plist").read_text()
    assert str(target) in cfo
    assert not (f["launchd_dir"] / "com.mooniex.mac-agent.plist").exists()


def test_apply_creates_slug_alias(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Agents" / "Core"
    new_slug = f["claude_projects"] / str(target).replace("/", "-")
    assert new_slug.is_symlink()
    assert Path(os.readlink(new_slug)) == f["old_slug_dir"]
    assert (new_slug / "marker.txt").read_text() == "old slug dir\n"


def test_apply_is_idempotent_on_slug_alias_second_run(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r1 = _run_cli(tmp_path, f, "--apply")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    r2 = _run_cli(tmp_path, f, "--apply")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "already" in r2.stdout


def test_apply_adds_trust_entry_preserving_other_keys(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    before = json.loads(f["claude_json"].read_text())
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Agents" / "Core"
    after = json.loads(f["claude_json"].read_text())
    assert after["projects"][str(target)]["hasTrustDialogAccepted"] is True
    assert after["projects"][str(target)]["allowedTools"] == ["Bash(git *)"]
    assert after["projects"][str(f["core"])] == before["projects"][str(f["core"])]
    assert after["projects"]["/Users/gob/some/other/project"] == before["projects"]["/Users/gob/some/other/project"]
    assert after["numStartups"] == before["numStartups"]


def test_apply_updates_hq_yaml_current_and_compat_link(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    rows = {row["path"]: row for row in data["folders"]}
    target = f["hq"] / "Agents" / "Core"
    assert rows["Agents/Core"]["current"] == str(target)
    links = {c["path"]: c for c in data["compat_links"]}
    assert links[str(f["core"])]["target"] == str(target)
    assert links[str(f["core"])]["remove_at_step"] == 5


# ─────────────────────────── resumability / crash recovery ──────────────────

def test_apply_resumes_after_crash_right_after_atomic_step(tmp_path: Path) -> None:
    """Simulates a crash between the atomic move+link and everything after
    it: the rename+symlink already happened (by hand, standing in for a
    completed Phase B) but plists/slug/trust/yaml never ran. A re-run must
    not re-move anything, must not error on 'already migrated', and must
    still complete every later phase."""
    f = _build_fixture(tmp_path)
    sha_before = _head(f["core"])
    target = f["hq"] / "Agents" / "Core"
    target.parent.mkdir(parents=True)
    shutil.move(str(f["core"]), str(target))
    os.symlink(str(target), str(f["core"]))

    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already migrated" in r.stdout
    assert _head(target) == sha_before
    watchdog = (f["launchd_dir"] / "com.mooniex.agents-watchdog.plist").read_text()
    assert str(target) in watchdog
    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    rows = {row["path"]: row for row in data["folders"]}
    assert rows["Agents/Core"]["current"] == str(target)


def test_apply_is_a_full_noop_on_second_run(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r1 = _run_cli(tmp_path, f, "--apply")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    yaml_after_first = (f["hq"] / "hq.yaml").read_text()
    r2 = _run_cli(tmp_path, f, "--apply")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert (f["hq"] / "hq.yaml").read_text() == yaml_after_first


# ─────────────────────────── rollback ────────────────────────────────────────

def test_rollback_restores_dir_symlink_plists_and_yaml_byte_for_byte(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    plist_before = (f["launchd_dir"] / "com.mooniex.agents-watchdog.plist").read_text()
    claude_json_before = f["claude_json"].read_text()
    sha_before = _head(f["core"])

    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest_path = sorted(f["state_dir"].glob("hq-step4b-migration-*.json"))[-1]

    rb = _run_cli(tmp_path, f, "--rollback", str(manifest_path))
    assert rb.returncode == 0, rb.stdout + rb.stderr

    assert not f["core"].is_symlink() and f["core"].is_dir()
    assert _head(f["core"]) == sha_before
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    assert (f["launchd_dir"] / "com.mooniex.agents-watchdog.plist").read_text() == plist_before
    assert f["claude_json"].read_text() == claude_json_before
    new_slug = f["claude_projects"] / str(f["hq"] / "Agents" / "Core").replace("/", "-")
    assert not new_slug.exists() and not new_slug.is_symlink()


# ─────────────────────────── repoint (boundary safety) ───────────────────────

def test_repoint_rewrites_own_hardcoded_paths(tmp_path: Path) -> None:
    """rewrite_repoint_files always targets the literal production old-root
    string (/Users/gob/[Pp]rojects/Agents) — that is the whole point (a
    single, unambiguous acceptance grep), so the fixture content must use
    that literal string too, independent of where tmp_path happens to be."""
    repo = tmp_path / "fake-core-repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    old = "/Users/gob/Projects/Agents"
    (repo / "config").mkdir()
    (repo / "config" / "hosts.yaml").write_text(f"mac: {old}\n")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "run.sh").write_text(f'PY="{old}/.venv/bin/python"\n')
    (repo / "README.md").write_text(f"see {old} for details\n")  # .md must be left
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    target = "/Users/gob/MoonieXHQ/Agents/Core"
    changed = mod.rewrite_repoint_files(repo, target)
    assert set(changed) == {"config/hosts.yaml", "scripts/run.sh"}
    assert target in (repo / "config" / "hosts.yaml").read_text()
    assert old in (repo / "README.md").read_text()  # markdown left alone
    yaml.safe_load((repo / "config" / "hosts.yaml").read_text())
    assert mod.repoint_files_clean(repo)


def test_repoint_does_not_clobber_sibling_agents_prefixed_paths(tmp_path: Path) -> None:
    """The naive `.replace()` approach used by step2/3/4a would corrupt
    '/Users/gob/Projects/Agents-Wikis' into '.../CoreWikis' wherever it
    shares the '/Users/gob/Projects/Agents' prefix. step4b's boundary-aware
    regex must leave sibling Agents-* paths byte-for-byte untouched."""
    repo = tmp_path / "fake-core-repo-2"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    old_core = "/Users/gob/Projects/Agents"
    sibling = "/Users/gob/Projects/Agents-Wikis"
    (repo / "config").mkdir()
    (repo / "config" / "wikis.yaml").write_text(f"core: {old_core}\nwikis: {sibling}\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    new_core = "/Users/gob/MoonieXHQ/Agents/Core"
    changed = mod.rewrite_repoint_files(repo, new_core)
    assert changed == ["config/wikis.yaml"]
    text = (repo / "config" / "wikis.yaml").read_text()
    assert f"core: {new_core}\n" in text
    assert f"wikis: {sibling}\n" in text  # untouched — not a prefix match, a sibling


# ─────────────────────────── claude project slug alias (unit) ────────────────

def test_create_slug_alias_reports_denied_when_source_missing(tmp_path: Path) -> None:
    m = mod.Manifest("t")
    m.path = tmp_path / "manifest.json"
    result = mod.create_slug_alias(tmp_path / "no-such-old-slug", tmp_path / "new-slug", m)
    assert result.startswith("denied")
    assert not (tmp_path / "new-slug").exists()


# ─────────────────────────── item 2: logical vs physical guard cases ────────
# Full coverage lives in scripts/test_hook_cwd_guard.py and
# scripts/test_hook_self_repo_guard.py; these two are the cross-check that
# this task's own test module also exercises hazard #2 directly, per the
# task brief's own wording ("... incl. item 2's logical/physical guard
# cases").

def _load_sibling_hook(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"{name}_xcheck", ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_hook_cwd_guard_same_verdict_logical_vs_physical(tmp_path: Path) -> None:
    cwd_guard = _load_sibling_hook("hook-cwd-guard")
    physical = tmp_path / "MoonieXHQ" / "Agents" / "Core"
    physical.mkdir(parents=True)
    logical = tmp_path / "Projects" / "Agents"
    logical.parent.mkdir(parents=True)
    logical.symlink_to(physical)
    final, _ = cwd_guard.simulate_final_cwd(f"cd {physical} && pytest", str(logical))
    assert cwd_guard._paths_equivalent(final, str(logical))


def test_self_repo_guard_same_verdict_logical_vs_physical(tmp_path: Path) -> None:
    self_repo_guard = _load_sibling_hook("hook-self-repo-guard")
    checkout = tmp_path / "checkout"
    (checkout / "lib").mkdir(parents=True)
    (checkout / "lib" / "foo.py").write_text("x = 1\n")
    logical_checkout = tmp_path / "logical-checkout-alias"
    logical_checkout.symlink_to(checkout)
    root = checkout  # stands in for a worktree root one level below (real_parent)
    reason_physical = self_repo_guard.classify(str(checkout / "lib" / "foo.py"), checkout, root / "worktrees" / "wt")
    reason_logical = self_repo_guard.classify(str(logical_checkout / "lib" / "foo.py"), checkout, root / "worktrees" / "wt")
    assert (reason_physical is None) == (reason_logical is None)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))


def test_gate_ceo_override_idle_excludes_only_named_tasks(tmp_path, monkeypatch):
    """--ceo-override-idle (CEO 2026-09-23): a verified-idle task named on the
    command line no longer blocks; any other in-flight task still does."""
    import sqlite3
    db = tmp_path / "tasks.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE tasks (id TEXT, status TEXT, role TEXT, title TEXT)")
    con.executemany("INSERT INTO tasks VALUES (?,?,?,?)", [
        ("task-idle0001", "rate_limited", "developer", "idle one"),
        ("task-busy0002", "in_progress", "developer", "busy one"),
    ])
    con.commit(); con.close()
    with pytest.raises(mod.GateBlocked) as e:
        mod.check_no_other_tasks_in_flight(db, None, ("task-idle0001",))
    assert "task-busy0002" in str(e.value) and "task-idle0001" not in str(e.value)
    mod.check_no_other_tasks_in_flight(db, "task-busy0002", ("task-idle0001",))  # clear
