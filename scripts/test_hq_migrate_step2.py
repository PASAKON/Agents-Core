"""Tests for scripts/hq_migrate_step2.py (HQ migration step 2, ADR 0028).

Every test runs against a fake HQ_ROOT/TRASH_ROOT/state-dir under tmp_path via
env-var overrides (HQ_ROOT, TRASH_ROOT, HQ_STEP2_STATE_DIR) — never touches the
real ~/MoonieXHQ or ~/.Trash. The fixture builds real git repos with real bare
"origin" remotes so ahead/behind and ls-remote checks are real git, not mocks.

Run: .venv/bin/python -m pytest scripts/test_hq_migrate_step2.py -q
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "hq_migrate_step2.py"
sys.path.insert(0, str(ROOT / "scripts"))
import hq_migrate_step2 as mod  # noqa: E402  (pure-function unit tests use this directly)

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
    # bare "origin" lives OUTSIDE the umbrella dir (it stands in for GitHub, a
    # remote, never a local sibling) so Phase C's leftover sweep never touches it.
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


def _files(repo: Path) -> set[str]:
    out = subprocess.run(["find", ".", "-type", "f", "-not", "-path", "./.git/*"], cwd=str(repo), capture_output=True, text=True).stdout
    return set(out.splitlines())


def _build_fixture(tmp: Path, unsafe_dup: bool, ahead: bool) -> dict:
    """3 rows: Alpha/One (clean), Alpha/Two (has `duplicates`), Beta/Three
    (ahead-of-origin branch when ahead=True). Returns a dict of paths + the
    hq.yaml text, ready to be written and driven via the CLI."""
    hq = tmp / "hq"
    hq.mkdir()
    umbrella_a = tmp / "UmbrellaAlpha"
    umbrella_b = tmp / "UmbrellaBeta"
    umbrella_a.mkdir()
    umbrella_b.mkdir()
    origins_dir = tmp / "origins"  # stands in for GitHub — never inside an umbrella dir

    # source dir names deliberately differ from their HQ target suffix (One/Two/
    # Three) by more than case: APFS is case-insensitive, so "one" and "One"
    # would alias to the same inode once the umbrella dir becomes a symlink.
    one, _ = _make_repo_with_origin(umbrella_a, "repo-alpha-one", origins_dir)
    two, two_origin = _make_repo_with_origin(umbrella_a, "repo-alpha-two", origins_dir)
    three, three_origin = _make_repo_with_origin(umbrella_b, "repo-beta-three", origins_dir)

    # duplicate clone of "two": safe by default (exact clone of origin)
    dup = tmp / "dup-two"
    _git(["clone", str(two_origin), str(dup)], tmp)
    if unsafe_dup:
        _add_local_commit(dup, "unpushed.txt")  # branch now ahead of anything on origin, never pushed

    if ahead:
        _add_local_commit(three, "extra.txt")  # local main ahead of its own origin/main

    (umbrella_a / "CLAUDE.md").write_text("alpha umbrella doc\n")
    (umbrella_a / ".DS_Store").write_text("junk\n")
    (umbrella_b / "README.md").write_text("beta umbrella doc\n")

    hq_yaml_text = f"""version: 1
root: {hq}
repo: TEST/hq
folders:
  - path: Projects/Alpha/One
    kind: own
    repo: TEST/alpha-one
    owner: CTO
    current: "{one}"
    step: 2
  - path: Projects/Alpha/Two
    kind: own
    repo: TEST/alpha-two
    owner: CTO
    current: "{two}"
    duplicates: [{dup}]   # feature clone, keep this comment
    step: 2
  - path: Projects/Beta/Three
    kind: own
    repo: TEST/beta-three
    owner: CTO
    current: "{three}"
    step: 2
dropped:
  - {{current: "/pre/existing", why: already dropped before this run}}
"""
    (hq / "hq.yaml").write_text(hq_yaml_text)
    return {
        "hq": hq, "one": one, "two": two, "three": three, "dup": dup,
        "two_origin": two_origin, "three_origin": three_origin,
        "umbrella_a": umbrella_a, "umbrella_b": umbrella_b,
    }


def _run_cli(tmp: Path, hq: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    env.update({
        "HQ_ROOT": str(hq),
        "TRASH_ROOT": str(tmp / "Trash"),
        "HQ_STEP2_STATE_DIR": str(tmp / "state"),
    })
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True)


def _manifest(tmp: Path) -> dict:
    files = sorted((tmp / "state").glob("hq-step2-migration-*.json"))
    assert files, "no manifest written"
    return json.loads(files[-1].read_text())


# ─────────────────────────── plan ────────────────────────────────────────────

def test_plan_changes_nothing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    r = _run_cli(tmp_path, f["hq"], "--plan")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MOVE" in r.stdout and str(f["one"]) in r.stdout
    assert f["one"].is_dir() and f["two"].is_dir() and f["three"].is_dir() and f["dup"].is_dir()
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    assert not (tmp_path / "state").exists() or not list((tmp_path / "state").glob("*.json"))


# ─────────────────────────── successful full apply ──────────────────────────

def test_apply_moves_repos_and_verifies_sha(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    one_sha = _head(f["one"])
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Projects" / "Alpha" / "One"
    assert target.is_dir()
    assert not f["one"].exists()
    assert _head(target) == one_sha


def test_apply_pushes_ahead_branch(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=True)
    local_sha = _head(f["three"])
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    origin_heads = _git(["ls-remote", "--heads", "origin"], f["hq"] / "Projects" / "Beta" / "Three").stdout
    assert local_sha in origin_heads


def test_apply_trashes_safe_duplicate(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not f["dup"].exists()
    trashed = list((tmp_path / "Trash").glob("hq-step2-*/dup-two"))
    assert trashed, "duplicate not found in trash"


def test_apply_creates_symlink_and_trashes_umbrella_leftovers(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f["umbrella_a"].is_symlink()
    assert os.readlink(f["umbrella_a"]) == str(f["hq"] / "Projects" / "Alpha")
    assert f["umbrella_b"].is_symlink()
    trashed = list((tmp_path / "Trash").glob("hq-step2-*/UmbrellaAlpha/CLAUDE.md"))
    assert trashed, "umbrella leftover CLAUDE.md not trashed"


def test_apply_updates_yaml_and_writes_manifest(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    rows = {row["path"]: row for row in data["folders"]}
    assert rows["Projects/Alpha/One"]["current"] == str(f["hq"] / "Projects/Alpha/One")
    assert "duplicates" not in rows["Projects/Alpha/Two"]
    assert rows["Projects/Alpha/Two"]["current"] == str(f["hq"] / "Projects/Alpha/Two")
    assert any(d.get("why") == "already dropped before this run" for d in data["dropped"])  # preserved
    assert any(str(f["one"]) == d.get("current") for d in data["dropped"])
    # comment on the (now-removed) duplicates line must not have leaked into another field
    text = (f["hq"] / "hq.yaml").read_text()
    assert "feature clone, keep this comment" not in text

    m = _manifest(tmp_path)
    ops = [o["op"] for o in m["ops"]]
    assert ops.count("move") >= 5  # 2 leftovers(x2 umbrellas) + dup + 3 repo moves, at least
    assert "yaml_edit" in ops and "symlink" in ops


# ─────────────────────────── stop-before-any-move ────────────────────────────

def test_apply_stops_before_any_move_when_duplicate_branch_missing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=True, ahead=True)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "STOP" in r.stdout
    # nothing moved anywhere, not even the unrelated clean rows
    assert f["one"].is_dir() and f["two"].is_dir() and f["three"].is_dir() and f["dup"].is_dir()
    assert not (f["hq"] / "Projects").exists()
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    # the ahead branch (unrelated to the bad duplicate) still gets pushed —
    # push is authorized per-row in Phase A, independent of a later row's failure
    origin_heads = _git(["ls-remote", "--heads", "origin"], f["three"]).stdout
    assert _head(f["three"]) in origin_heads
    m = _manifest(tmp_path)
    assert any("BLOCKER" in n for n in m["notes"])
    assert not any(o["op"] == "move" and "Projects" in o.get("to", "") for o in m["ops"])


# ─────────────────────────── rollback ────────────────────────────────────────

def test_rollback_restores_everything_byte_for_byte(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    before = {
        "one_sha": _head(f["one"]), "two_sha": _head(f["two"]), "three_sha": _head(f["three"]),
        "dup_sha": _head(f["dup"]), "one_files": _files(f["one"]), "dup_files": _files(f["dup"]),
    }
    r = _run_cli(tmp_path, f["hq"], "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest_path = sorted((tmp_path / "state").glob("hq-step2-migration-*.json"))[-1]

    rb = _run_cli(tmp_path, f["hq"], "--rollback", str(manifest_path))
    assert rb.returncode == 0, rb.stdout + rb.stderr

    assert not f["umbrella_a"].is_symlink()
    assert f["one"].is_dir() and f["two"].is_dir() and f["three"].is_dir() and f["dup"].is_dir()
    assert _head(f["one"]) == before["one_sha"]
    assert _head(f["two"]) == before["two_sha"]
    assert _head(f["three"]) == before["three_sha"]
    assert _head(f["dup"]) == before["dup_sha"]
    assert _files(f["one"]) == before["one_files"]
    assert _files(f["dup"]) == before["dup_files"]
    assert (f["umbrella_a"] / "CLAUDE.md").read_text() == "alpha umbrella doc\n"
    assert (f["umbrella_b"] / "README.md").read_text() == "beta umbrella doc\n"
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before


# ─────────────────────────── unit tests on pure helpers ─────────────────────

def test_check_duplicate_safe_flags_unmerged_branch(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=True, ahead=False)
    safe, notes = mod.check_duplicate_safe(f["dup"])
    assert safe is False
    assert any("UNSAFE" in n for n in notes)


def test_check_duplicate_safe_accepts_exact_and_ancestor_matches(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    safe, notes = mod.check_duplicate_safe(f["dup"])
    assert safe is True
    assert any("exact match" in n for n in notes)
    # advance origin's main past the dup's sha: dup's main is now an ancestor, still safe
    _add_local_commit(f["two"], "advance.txt")
    _git(["push"], f["two"])
    safe2, notes2 = mod.check_duplicate_safe(f["dup"])
    assert safe2 is True
    assert any("ancestor" in n for n in notes2)


def test_patch_yaml_row_preserves_comments_and_only_edits_target_row(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path, unsafe_dup=False, ahead=False)
    lines = (f["hq"] / "hq.yaml").read_text().splitlines(keepends=True)
    out = mod.patch_yaml_row(lines, "Projects/Alpha/Two", "/new/path/Two", drop_duplicates=True)
    text = "".join(out)
    assert "current: /new/path/Two" in text
    assert "duplicates:" not in text
    assert f'current: "{f["one"]}"' in text  # untouched row unaffected
    assert "dropped:" in text and "already dropped before this run" in text
    yaml.safe_load(text)  # still valid yaml
