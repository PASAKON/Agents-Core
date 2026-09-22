"""Tests for scripts/hq_migrate_step3.py (HQ migration step 3, ADR 0028).

Every test runs against a fake HQ_ROOT/state-dir/plists under tmp_path via env-var
overrides (HQ_ROOT, HQ_STEP3_STATE_DIR, HQ_STEP3_PLISTS, HQ_SURVEY_ROOTS, HQ_PYTHON) —
never touches the real ~/MoonieXHQ, ~/Library/LaunchAgents or /Users/gob/Projects. The
fixture builds real git repos with real bare "origin"/"custom" remotes so upstream/
ahead/behind checks and pushes are real git, not mocks.

Run: .venv/bin/python -m pytest scripts/test_hq_migrate_step3.py -q
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "hq_migrate_step3.py"
sys.path.insert(0, str(ROOT / "scripts"))
import hq_migrate_step3 as mod  # noqa: E402  (pure-function unit tests use this directly)

REAL_HQ_PY = Path("/Users/gob/MoonieXHQ/scripts/hq.py")

GIT_ENV_EXTRA = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    r = subprocess.run(["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} in {cwd} failed: {r.stdout}{r.stderr}"
    return r


def _make_repo_with_origin(base: Path, name: str, origins_dir: Path) -> tuple[Path, Path]:
    origin = origins_dir / f"{name}-origin.git"
    origin.mkdir(parents=True)
    _git(["init", "--bare", "-b", "main"], origin)
    repo = base / name
    repo.mkdir(parents=True)
    _git(["init", "-b", "main"], repo)
    (repo / "README.md").write_text(f"{name}\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)
    _git(["remote", "add", "origin", str(origin)], repo)
    _git(["push", "-u", "origin", "main"], repo)
    return repo, origin


def _add_local_commit(repo: Path, fname: str) -> str:
    (repo / fname).write_text("more\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", f"add {fname}"], repo)
    return _git(["rev-parse", "HEAD"], repo).stdout.strip()


def _head(repo: Path) -> str:
    return _git(["rev-parse", "HEAD"], repo).stdout.strip()


PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{repo}/scripts/run.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{repo}</string>
</dict>
</plist>
"""


def _build_fixture(tmp: Path) -> dict:
    """4 rows: Alpha/One (plain), Alpha/Two (has an attached worktree), Beta/Three
    (tracking remote is `custom`, not origin, and ahead), Beta/Four (no upstream)."""
    hq = tmp / "hq"
    (hq / "scripts").mkdir(parents=True)
    if REAL_HQ_PY.exists():
        shutil.copy2(REAL_HQ_PY, hq / "scripts" / "hq.py")
    origins_dir = tmp / "origins"
    projects = tmp / "Projects"
    projects.mkdir()

    one, _ = _make_repo_with_origin(projects, "repo-one", origins_dir)
    two, _ = _make_repo_with_origin(projects, "repo-two", origins_dir)
    three, _ = _make_repo_with_origin(projects, "repo-three", origins_dir)
    four, _ = _make_repo_with_origin(projects, "repo-four", origins_dir)

    wt_path = tmp / "external-worktree-two"
    _git(["worktree", "add", str(wt_path), "-b", "wt-branch"], two)

    custom_origin = origins_dir / "repo-three-custom.git"
    custom_origin.mkdir(parents=True)
    _git(["init", "--bare", "-b", "main"], custom_origin)
    _git(["remote", "add", "custom", str(custom_origin)], three)
    _git(["push", "-u", "custom", "main"], three)
    _add_local_commit(three, "extra.txt")  # now ahead of `custom` by 1

    _git(["branch", "--unset-upstream", "main"], four)

    hq_yaml_text = f"""version: 1
root: {hq}
repo: TEST/hq
folders:
  - path: Projects/Alpha/One
    kind: own
    owner: CTO
    current: {one}
    step: 3
  - path: Projects/Alpha/Two
    kind: own
    owner: CTO
    current: {two}
    step: 3
  - path: Projects/Beta/Three
    kind: own
    owner: CTO
    current: {three}
    step: 3
  - path: Projects/Beta/Four
    kind: own
    owner: CTO
    current: {four}
    step: 3
"""
    (hq / "hq.yaml").write_text(hq_yaml_text)

    plist = tmp / "fake.plist"
    plist.write_text(PLIST_TEMPLATE.format(repo=two))
    plist2 = tmp / "fake-untouched.plist"
    plist2.write_text(PLIST_TEMPLATE.format(repo=tmp / "unrelated"))

    return {
        "hq": hq, "one": one, "two": two, "three": three, "four": four,
        "wt_path": wt_path, "plist": plist, "plist2": plist2,
        "projects": projects, "custom_origin": custom_origin,
    }


def _run_cli(tmp: Path, f: dict, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    env.update({
        "HQ_ROOT": str(f["hq"]),
        "HQ_STEP3_STATE_DIR": str(tmp / "state"),
        "HQ_STEP3_PLISTS": f'{f["plist"]}:{f["plist2"]}',
        "HQ_SURVEY_ROOTS": str(f["projects"]),
        "HQ_PYTHON": sys.executable,
    })
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True)


def _manifest(tmp: Path) -> dict:
    files = sorted((tmp / "state").glob("hq-step3-migration-*.json"))
    assert files, "no manifest written"
    return json.loads(files[-1].read_text())


# ─────────────────────────── plan ────────────────────────────────────────────

def test_plan_changes_nothing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    r = _run_cli(tmp_path, f, "--plan")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MOVE" in r.stdout and str(f["one"]) in r.stdout
    assert str(f["wt_path"]) in r.stdout
    assert f["one"].is_dir() and f["two"].is_dir() and f["three"].is_dir() and f["four"].is_dir()
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    assert not (tmp_path / "state").exists() or not list((tmp_path / "state").glob("*.json"))


# ─────────────────────────── successful full apply ──────────────────────────

def test_apply_moves_repos_and_verifies_sha(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    one_sha = _head(f["one"])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Projects" / "Alpha" / "One"
    assert target.is_dir()
    assert not f["one"].exists() or f["one"].is_symlink()
    assert _head(target) == one_sha


def test_apply_repairs_attached_worktree(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Projects" / "Alpha" / "Two"
    st = _git(["status"], f["wt_path"])
    assert st.returncode == 0
    gitdir = _git(["rev-parse", "--git-dir"], f["wt_path"]).stdout.strip()
    gitdir_path = Path(gitdir)
    if not gitdir_path.is_absolute():
        gitdir_path = (f["wt_path"] / gitdir_path).resolve()
    assert str(gitdir_path).startswith(str((target / ".git" / "worktrees").resolve()))


def test_apply_pushes_to_non_origin_tracking_remote(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    local_sha = _head(f["three"])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Projects" / "Beta" / "Three"
    heads = _git(["ls-remote", "--heads", "custom"], target).stdout
    assert local_sha in heads


def test_apply_records_no_upstream_without_pushing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    m = _manifest(tmp_path)
    assert any("not pushed: no upstream" in n and "Beta/Four" in n for n in m["notes"])
    target = f["hq"] / "Projects" / "Beta" / "Four"
    assert target.is_dir()
    up = subprocess.run(["git", "-C", str(target), "rev-parse", "--abbrev-ref", "main@{upstream}"], capture_output=True, text=True)
    assert up.returncode != 0  # still no upstream after the move


def test_apply_creates_compat_symlinks_and_updates_yaml(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Projects" / "Alpha" / "One"
    assert f["one"].is_symlink()
    assert os.readlink(f["one"]) == str(target)

    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    rows = {row["path"]: row for row in data["folders"]}
    assert rows["Projects/Alpha/One"]["current"] == str(target)
    links = {c["path"]: c for c in data["compat_links"]}
    assert links[str(f["one"])]["target"] == str(target)
    assert links[str(f["one"])]["remove_at_step"] == 4


def test_apply_rewrites_plist_in_place_and_lints(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    target = f["hq"] / "Projects" / "Alpha" / "Two"
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    text = f["plist"].read_text()
    assert str(target) in text
    assert str(f["two"]) not in text
    lint = subprocess.run(["plutil", "-lint", str(f["plist"])], capture_output=True, text=True)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    # plist2 has no matching old path literal — left untouched
    assert f["plist2"].read_text() == PLIST_TEMPLATE.format(repo=tmp_path / "unrelated")


@pytest.mark.skipif(not REAL_HQ_PY.exists(), reason="real ~/MoonieXHQ/scripts/hq.py not present on this machine")
def test_hq_doctor_clean_on_fixture(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    env = dict(os.environ)
    env.update({"HQ_ROOT": str(f["hq"]), "HQ_SURVEY_ROOTS": str(f["projects"])})
    doc = subprocess.run([sys.executable, str(f["hq"] / "scripts" / "hq.py"), "doctor"], cwd=f["hq"], env=env, capture_output=True, text=True)
    assert "clean" in doc.stdout, doc.stdout + doc.stderr
    assert doc.returncode == 0, doc.stdout + doc.stderr


# ─────────────────────────── stop-before-any-move ────────────────────────────

def test_apply_stops_before_any_move_when_push_fails(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    shutil.rmtree(f["custom_origin"])  # push to `custom` will now fail
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "STOP" in r.stdout
    assert f["one"].is_dir() and f["two"].is_dir() and f["three"].is_dir() and f["four"].is_dir()
    assert not f["one"].is_symlink()
    assert not (f["hq"] / "Projects").exists()
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    m = _manifest(tmp_path)
    assert any("BLOCKER" in n for n in m["notes"])
    assert not any(o["op"] == "move" for o in m["ops"])


# ─────────────────────────── rollback ────────────────────────────────────────

def test_rollback_restores_dirs_symlinks_and_worktree_pointer(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    before_one_sha = _head(f["one"])
    before_two_sha = _head(f["two"])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest_path = sorted((tmp_path / "state").glob("hq-step3-migration-*.json"))[-1]

    rb = _run_cli(tmp_path, f, "--rollback", str(manifest_path))
    assert rb.returncode == 0, rb.stdout + rb.stderr

    assert not f["one"].is_symlink() and f["one"].is_dir()
    assert not f["two"].is_symlink() and f["two"].is_dir()
    assert _head(f["one"]) == before_one_sha
    assert _head(f["two"]) == before_two_sha

    st = _git(["status"], f["wt_path"])
    assert st.returncode == 0
    gitdir = _git(["rev-parse", "--git-dir"], f["wt_path"]).stdout.strip()
    gitdir_path = Path(gitdir)
    if not gitdir_path.is_absolute():
        gitdir_path = (f["wt_path"] / gitdir_path).resolve()
    assert str(gitdir_path).startswith(str((f["two"] / ".git" / "worktrees").resolve()))


def test_rollback_restores_yaml_and_plist_byte_for_byte(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    plist_before = f["plist"].read_text()
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest_path = sorted((tmp_path / "state").glob("hq-step3-migration-*.json"))[-1]

    rb = _run_cli(tmp_path, f, "--rollback", str(manifest_path))
    assert rb.returncode == 0, rb.stdout + rb.stderr

    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    assert f["plist"].read_text() == plist_before


# ─────────────────────────── unit tests on pure helpers ─────────────────────

def test_list_attached_worktrees(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    assert mod.list_attached_worktrees(f["one"]) == []
    wts = mod.list_attached_worktrees(f["two"])
    assert len(wts) == 1
    assert Path(wts[0]).resolve() == f["wt_path"].resolve()


def test_build_path_mapping(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    rows = mod.step3_rows(f["hq"] / "hq.yaml")
    mapping = mod.build_path_mapping(f["hq"], rows)
    assert mapping[str(f["one"])] == str(f["hq"] / "Projects" / "Alpha" / "One")
    assert mapping[str(f["four"])] == str(f["hq"] / "Projects" / "Beta" / "Four")


def test_append_compat_links_preserves_existing_and_appends(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    lines = (f["hq"] / "hq.yaml").read_text().splitlines(keepends=True)
    lines = mod.append_compat_links(lines, [{"path": "/old/a", "target": "/new/a", "remove_at_step": 4}])
    text = "".join(lines)
    assert 'compat_links:' in text
    assert '{path: "/old/a", target: "/new/a", remove_at_step: 4}' in text
    yaml.safe_load(text)
    # calling again appends a second block rather than clobbering the first
    lines2 = mod.append_compat_links(lines, [{"path": "/old/b", "target": "/new/b", "remove_at_step": 4}])
    text2 = "".join(lines2)
    assert '/old/a' in text2 and '/old/b' in text2
    yaml.safe_load(text2)


def test_repoint_rewrites_tracked_files_and_leaves_docs_alone(tmp_path: Path) -> None:
    repo = tmp_path / "fake-agents-repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    # deliberately NOT one of the eleven real step-3 repo names — this test
    # exercises the rewrite mechanism itself, and a real name here would get
    # caught by this task's own verification grep against these fixtures.
    old = "/Users/gob/Projects/widget-service"
    new = "/Users/gob/MoonieXHQ/Projects/MoonieX/WidgetService"
    (repo / "config").mkdir()
    (repo / "config" / "projects.yaml").write_text(f"webapp:\n  path: {old}\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "README.md").write_text(f"see {old}\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    mapping = {old: new}
    changed = mod.rewrite_repoint_files(repo, mapping)
    assert changed == ["config/projects.yaml"]
    assert new in (repo / "config" / "projects.yaml").read_text()
    assert old in (repo / "docs" / "README.md").read_text()  # .md left untouched
    assert mod.repoint_files_clean(repo, mapping)
    yaml.safe_load((repo / "config" / "projects.yaml").read_text())


def test_repoint_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "fake-agents-repo2"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    old, new = "/Users/gob/Projects/gadget-service", "/Users/gob/MoonieXHQ/Projects/MoonieX/GadgetService"
    (repo / "lib.py").write_text(f'ROOT = "{old}"\n')
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    mapping = {old: new}
    first = mod.rewrite_repoint_files(repo, mapping)
    assert first == ["lib.py"]
    second = mod.rewrite_repoint_files(repo, mapping)
    assert second == []  # nothing left to change
