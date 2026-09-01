"""Tests for scripts/skill-curator.py (ADR 0018).

Proves the five curator invariants:
  1. Never deletes — archive is restorable via restore.
  2. Only touches created_by: agent — human-authored (incl. absent field,
     which defaults to human) skills are read-only.
  3. Refuses any path that resolves through a symlink escaping the owned
     skills dir.
  4. Pinned skills are exempt from every transition, and from archive.
  5. Backs up before any mutation.

Every fixture lives under tmp_path via CuratorPaths(merge_external=False),
which skips the ~/.claude/skills + plugin-marketplace merge entirely and
reads only the log_path handed to it. This module never opens
state/skill-usage.log, state/skill-usage.json, ~/.claude/skills/, or
anything under output/ (ADR 0021 §"tests must not write to real state").

ADR 0022 Wave 2 -- git is the ledger. Every mutating verb (archive, restore,
pin, unpin, create) now ends with a real `git commit`, so `_make_paths` git
inits tmp_path as its own throwaway repo (hard constraint #4: a test that
commits to the real checkout is a defect even if it passes -- this file
never touches this repo's own .git).

Run standalone:   python scripts/test_skill_curator.py
Or under pytest:  pytest scripts/test_skill_curator.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "skill_curator", ROOT / "scripts" / "skill-curator.py"
)
assert _SPEC is not None and _SPEC.loader is not None
curator = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = curator  # dataclass needs this in sys.modules to resolve annotations
_SPEC.loader.exec_module(curator)


# --------------------------------------------------------------------------
# fixtures — everything lives under tmp_path.
# --------------------------------------------------------------------------

def _commit_path(path: Path, message: str, *, when: "datetime | None" = None) -> None:
    """Explicit fixture commit -- used only by tests that deliberately want
    a skill already tracked in git BEFORE a mutating verb runs on it (the
    realistic production case: `.claude/skills/` is git-tracked from Wave 0
    onward). Deliberately NOT wired into `_write_skill` below: most fixture
    skills here are `_backdate`d to look idle, and `_idle_since_unused`
    consults `_git_added_at`, which reads the FIRST "Added" commit for a
    path -- committing a fresh fixture for real would stamp that as "added
    today" and override the backdated idle clock. `when`, if given, stamps
    GIT_AUTHOR_DATE/GIT_COMMITTER_DATE so a fixture can be "added N days
    ago" (matching `_backdate`'s days) and still safely receive LATER
    mutation commits (pin/archive/etc, at the real current time) without
    resetting that first-added date -- those show up as "Modified", not
    "Added", once this initial commit exists."""
    env = dict(os.environ)
    if when is not None:
        env["GIT_AUTHOR_DATE"] = when.isoformat()
        env["GIT_COMMITTER_DATE"] = when.isoformat()
    subprocess.run(["git", "add", "-A", "--", str(path)], cwd=str(path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message, "--", str(path)],
        cwd=str(path), check=True, capture_output=True, env=env,
    )


def _write_skill(base: Path, name: str, *, created_by: "str | None" = "agent",
                  body: str = "content") -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---", f"name: {name}"]
    if created_by is not None:
        fm_lines.append(f"created_by: {created_by}")
    fm_lines += ["description: fixture skill for skill-curator tests", "---", "",
                 f"# {name}", "", body, ""]
    (d / "SKILL.md").write_text("\n".join(fm_lines), encoding="utf-8")
    return d


def _backdate(skill_md: Path, days: int) -> None:
    """Make a never-invoked fixture skill look `days` old to the curator.

    mtime alone no longer does this. The curator stopped trusting mtime because
    git rewrites it on every checkout, worktree creation, and rebase — in a
    fresh worktree every skill looked brand new and `propose` could never
    surface anything (measured 2026-08-13). For a skill with zero uses the idle
    clock is now "the later of: when telemetry started, and when the skill
    first entered git", so the fixture has to state when telemetry started.

    Under `tmp_path` there is no git, so `_git_added_at` returns None and the
    log's earliest entry decides. Seed one sentinel line at `now - days` for a
    skill that exists nowhere else: that sets `observation_start` without
    giving any fixture skill a use count.

    The `os.utime` call is kept — harmless, and it keeps the fixture honest if
    the clock ever consults mtime again.
    """
    old_dt = datetime.now(timezone.utc) - timedelta(days=days)
    os.utime(skill_md, (old_dt.timestamp(), old_dt.timestamp()))

    # <tmp_path>/owned-skills/<name>/SKILL.md -> <tmp_path>/state/skill-usage.log,
    # matching the layout _make_paths builds.
    log_path = skill_md.parent.parent.parent / "state" / "skill-usage.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel = f"{old_dt.isoformat()}\t_fixture-observation-start\tfixture\n"
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    if sentinel not in existing:
        log_path.write_text(sentinel + existing, encoding="utf-8")


def _git_init(repo_root: Path) -> None:
    """Throwaway git repo for a mutating-verb test (hard constraint #4).
    Local-only config (`--local`, never `--global`) so the fixture works
    with no user.email/name set and no GPG key configured, without touching
    the real checkout's git config at all."""
    for args in (
        ["git", "init", "-q"],
        ["git", "config", "--local", "user.email", "test@example.com"],
        ["git", "config", "--local", "user.name", "skill-curator-tests"],
        ["git", "config", "--local", "commit.gpgsign", "false"],
    ):
        subprocess.run(args, cwd=str(repo_root), check=True, capture_output=True)


def _make_paths(tmp_path: Path) -> "curator.CuratorPaths":
    owned = tmp_path / "owned-skills"
    owned.mkdir()
    _git_init(tmp_path)
    return curator.CuratorPaths(
        owned_skills_dir=owned,
        log_path=tmp_path / "state" / "skill-usage.log",
        archive_dir=tmp_path / "skills-archive",
        backup_dir=tmp_path / "backups",
        merge_external=False,
    )


def _snapshot(d: Path) -> dict:
    """name -> content for every regular file under d. Used to assert 'unchanged'."""
    if not d.exists():
        return {}
    return {
        str(p.relative_to(d)): p.read_bytes()
        for p in sorted(d.rglob("*"))
        if p.is_file()
    }


# --------------------------------------------------------------------------
# invariant 3 — symlink escape refusal
# --------------------------------------------------------------------------

def test_archive_refuses_symlinked_skill_even_if_stale_and_agent(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    external_dir = tmp_path / "external-repo"
    external_dir.mkdir()
    real_skill = _write_skill(external_dir, "real-skill", created_by="agent")
    _backdate(real_skill / "SKILL.md", days=200)  # well past the archive threshold

    (paths.owned_skills_dir / "sym-skill").symlink_to(real_skill, target_is_directory=True)

    with pytest.raises(curator.CuratorError, match="symlink"):
        curator.archive_skill(paths, "sym-skill")

    assert (paths.owned_skills_dir / "sym-skill").is_symlink()
    assert real_skill.is_dir()  # untouched at its real location
    assert not paths.archive_dir.exists()
    assert not paths.backup_dir.exists()


# --------------------------------------------------------------------------
# invariant 2 — only created_by: agent is mutable
# --------------------------------------------------------------------------

def test_archive_refuses_human_authored_skill(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    _write_skill(paths.owned_skills_dir, "human-skill", created_by="human")

    with pytest.raises(curator.CuratorError, match="human-authored"):
        curator.archive_skill(paths, "human-skill")

    assert (paths.owned_skills_dir / "human-skill").is_dir()


def test_archive_refuses_when_created_by_absent(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    _write_skill(paths.owned_skills_dir, "legacy-skill", created_by=None)

    with pytest.raises(curator.CuratorError, match="human-authored"):
        curator.archive_skill(paths, "legacy-skill")

    assert (paths.owned_skills_dir / "legacy-skill").is_dir()


def test_human_authored_stale_skill_is_informational_not_actionable(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    skill = _write_skill(paths.owned_skills_dir, "old-human-skill", created_by=None)
    _backdate(skill / "SKILL.md", days=200)

    proposals = curator.compute_proposals(paths)
    match = [p for p in proposals if p.name == "old-human-skill"]
    assert len(match) == 1
    assert match[0].actionable is False  # curator computes it, but cannot act


# --------------------------------------------------------------------------
# invariant 4 — pinned is exempt
# --------------------------------------------------------------------------

def test_pinned_skill_exempt_from_proposed_transition(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    pinned = _write_skill(paths.owned_skills_dir, "pinned-agent-skill", created_by="agent")
    _backdate(pinned / "SKILL.md", days=200)
    unpinned = _write_skill(paths.owned_skills_dir, "unpinned-agent-skill", created_by="agent")
    _backdate(unpinned / "SKILL.md", days=200)

    curator.pin_skill(paths, "pinned-agent-skill")

    names = {p.name for p in curator.compute_proposals(paths)}
    assert "pinned-agent-skill" not in names
    assert "unpinned-agent-skill" in names  # proves the harness would propose without the pin


def test_unpin_restores_transition_eligibility(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    skill = _write_skill(paths.owned_skills_dir, "toggle-skill", created_by="agent")
    _backdate(skill / "SKILL.md", days=200)
    # Commit the fixture at its backdated age FIRST -- otherwise pin_skill's
    # own commit below would be this file's first-ever git history, and
    # _git_added_at would (correctly, just not for this test) read that as
    # "added today", masking the staleness this test means to exercise.
    _commit_path(skill, "fixture: add toggle-skill", when=datetime.now(timezone.utc) - timedelta(days=200))

    curator.pin_skill(paths, "toggle-skill")
    assert "toggle-skill" not in {p.name for p in curator.compute_proposals(paths)}

    curator.unpin_skill(paths, "toggle-skill")
    assert "toggle-skill" in {p.name for p in curator.compute_proposals(paths)}


def test_archive_refuses_pinned_skill(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    _write_skill(paths.owned_skills_dir, "pinned-skill", created_by="agent")
    curator.pin_skill(paths, "pinned-skill")

    with pytest.raises(curator.CuratorError, match="pinned"):
        curator.archive_skill(paths, "pinned-skill")

    assert (paths.owned_skills_dir / "pinned-skill").is_dir()


# --------------------------------------------------------------------------
# invariant 1 — never deletes, archive/restore round-trip
# --------------------------------------------------------------------------

def test_archive_then_restore_round_trips_file_intact(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    skill_dir = _write_skill(paths.owned_skills_dir, "roundtrip-skill",
                              created_by="agent", body="unique body xyz")
    original = (skill_dir / "SKILL.md").read_bytes()

    curator.archive_skill(paths, "roundtrip-skill")
    assert not (paths.owned_skills_dir / "roundtrip-skill").exists()
    assert (paths.archive_dir / "roundtrip-skill" / "SKILL.md").is_file()

    curator.restore_skill(paths, "roundtrip-skill")
    assert not (paths.archive_dir / "roundtrip-skill").exists()
    restored = (paths.owned_skills_dir / "roundtrip-skill" / "SKILL.md").read_bytes()
    assert restored == original  # byte-for-byte: restore deletes the lifecycle/
    # archived_at lines archive() added, rather than writing lifecycle: active

    portfolio = curator.build_portfolio(paths)
    assert portfolio["roundtrip-skill"]["lifecycle"] == "active"


def test_restore_missing_name_refuses(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    with pytest.raises(curator.CuratorError, match="not found"):
        curator.restore_skill(paths, "does-not-exist")


def test_archive_missing_name_refuses(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    with pytest.raises(curator.CuratorError, match="not found"):
        curator.archive_skill(paths, "does-not-exist")


def test_archive_rejects_path_traversal_name(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    with pytest.raises(curator.CuratorError, match="invalid skill name"):
        curator.archive_skill(paths, "../evil")


# --------------------------------------------------------------------------
# invariant 5 — backs up before any mutation
# --------------------------------------------------------------------------

def test_archive_creates_backup_before_moving(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    _write_skill(paths.owned_skills_dir, "backed-up-skill", created_by="agent", body="backup me")

    curator.archive_skill(paths, "backed-up-skill")

    snapshots = list((paths.backup_dir / "backed-up-skill").iterdir())
    assert len(snapshots) == 1
    backup_skill_md = snapshots[0] / "SKILL.md"
    assert backup_skill_md.is_file()
    assert "backup me" in backup_skill_md.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# propose is read-only
# --------------------------------------------------------------------------

def test_propose_mutates_nothing(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    agent_skill = _write_skill(paths.owned_skills_dir, "agent-skill", created_by="agent")
    human_skill = _write_skill(paths.owned_skills_dir, "human-skill", created_by="human")
    _backdate(agent_skill / "SKILL.md", days=200)
    _backdate(human_skill / "SKILL.md", days=200)

    before = _snapshot(paths.owned_skills_dir)
    assert not paths.archive_dir.exists()
    assert not paths.backup_dir.exists()

    proposals = curator.compute_proposals(paths)
    assert proposals, "sanity: the fixture should produce at least one proposal"

    after = _snapshot(paths.owned_skills_dir)
    assert before == after
    assert not paths.archive_dir.exists()
    assert not paths.backup_dir.exists()


# --------------------------------------------------------------------------
# Wave 0.3 — role column: _load_log_tsv pads legacy 3-field lines
# --------------------------------------------------------------------------

def test_load_log_tsv_pads_legacy_lines_and_reads_role_column(tmp_path: Path) -> None:
    log_path = tmp_path / "skill-usage.log"
    log_path.write_text(
        "2026-08-01T00:00:00+00:00\tdebug-mantra\tlegacy-session\n"
        "2026-09-01T00:00:00+00:00\tscrutinize\tnew-session\tdeveloper\n",
        encoding="utf-8",
    )

    entries = curator._load_log_tsv(log_path)
    assert len(entries) == 2
    assert entries[0][1:] == ("debug-mantra", "legacy-session", "-")
    assert entries[1][1:] == ("scrutinize", "new-session", "developer")


# --------------------------------------------------------------------------
# ADR 0022 Wave 1 -- _created_by no longer coerces an invalid value silently
# --------------------------------------------------------------------------

def test_created_by_role_value_warns_on_stderr_but_still_coerces_to_human(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The exact incident ADR 0022 exists to fix: created_by: cto (a role,
    which belongs in author:, not here) used to coerce to "human" with no
    error and no log line. The coercion is correct and unchanged (invariant
    2's whole safety story depends on it staying fail-closed) -- what
    changes is that it is no longer silent."""
    skill = _write_skill(tmp_path, "role-created-by-skill", created_by="cto")

    result = curator._created_by(skill)

    assert result == "human"  # unchanged: still fail-closed
    err = capsys.readouterr().err
    assert "cto" in err
    assert str(skill / "SKILL.md") in err
    assert "WARNING" in err


@pytest.mark.parametrize("value", ["human", "agent"])
def test_created_by_valid_values_never_warn(
    tmp_path: Path, capsys: pytest.CaptureFixture, value: str
) -> None:
    skill = _write_skill(tmp_path, "valid-created-by-skill", created_by=value)

    result = curator._created_by(skill)

    assert result == value
    assert capsys.readouterr().err == ""


def test_created_by_absent_never_warns(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Absent is the normal, protected case for every skill written before
    this ADR -- it must default to human with no warning noise."""
    skill = _write_skill(tmp_path, "no-created-by-skill", created_by=None)

    result = curator._created_by(skill)

    assert result == "human"
    assert capsys.readouterr().err == ""


# --------------------------------------------------------------------------
# ADR 0022 Wave 2 -- git is the ledger, not a bespoke store
# --------------------------------------------------------------------------

def _log_text(paths: "curator.CuratorPaths") -> str:
    result = subprocess.run(
        ["git", "log", "--format=%B"], cwd=str(paths.owned_skills_dir), capture_output=True, text=True,
    )
    return result.stdout


def _head(paths: "curator.CuratorPaths") -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(paths.owned_skills_dir), capture_output=True, text=True,
    )
    return result.stdout.strip()


def _set_worker_identity(monkeypatch: pytest.MonkeyPatch, *, role: str, task_id: str) -> None:
    """Deterministic Skill-Actor identity for a test, regardless of this
    session's own ambient WORKER_TASK_ID/WORKER_ROLE (this dev task itself
    runs under the org runtime with those set)."""
    monkeypatch.setenv("WORKER_TASK_ID", task_id)
    monkeypatch.setenv("WORKER_ROLE", role)
    monkeypatch.delenv("CXO_ROLE", raising=False)
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)


def test_archive_commits_with_skill_actor_trailer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-abcdef12")
    paths = _make_paths(tmp_path)
    skill = _write_skill(paths.owned_skills_dir, "logged-skill", created_by="agent")
    _commit_path(skill, "fixture: add logged-skill")

    curator.archive_skill(paths, "logged-skill")

    log = _log_text(paths)
    assert "skill-curator: archive logged-skill" in log
    assert "Skill-Actor: developer/task-abcdef12" in log


def test_pin_then_unpin_each_produce_their_own_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-abcdef12")
    paths = _make_paths(tmp_path)
    skill = _write_skill(paths.owned_skills_dir, "pin-log-skill", created_by="agent")
    _commit_path(skill, "fixture: add pin-log-skill")

    curator.pin_skill(paths, "pin-log-skill")
    curator.unpin_skill(paths, "pin-log-skill")

    log = _log_text(paths)
    assert "skill-curator: pin pin-log-skill" in log
    assert "skill-curator: unpin pin-log-skill" in log
    assert log.count("Skill-Actor: developer/task-abcdef12") == 2


def test_noop_mutation_creates_no_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR 0022: git history should be real mutations, not noise -- unpin on
    an already-unpinned skill changes nothing on disk, so nothing commits."""
    _set_worker_identity(monkeypatch, role="developer", task_id="task-x")
    paths = _make_paths(tmp_path)
    skill = _write_skill(paths.owned_skills_dir, "already-unpinned", created_by="agent")
    _commit_path(skill, "fixture: add already-unpinned")

    before = _head(paths)
    curator.unpin_skill(paths, "already-unpinned")
    after = _head(paths)

    assert before == after


def test_create_skill_stamps_identity_and_passes_lint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="browser_operator", task_id="task-newskill1")
    paths = _make_paths(tmp_path)

    dest = curator.create_skill(
        paths, "cto-new-thing",
        description="A brand new org skill created by an agent.",
        audience=["cto"],
    )

    fm = curator._read_frontmatter(dest)
    assert fm["created_by"] == "agent"
    assert fm["author"]["role"] == "browser_operator"
    assert fm["audience"] == ["cto"]
    assert fm["name"] == "cto-new-thing"

    # Acceptance criterion: passes skill-lint.py on the first try.
    lint_spec = importlib.util.spec_from_file_location(
        "skill_lint_for_create_test", ROOT / "scripts" / "skill-lint.py"
    )
    assert lint_spec is not None and lint_spec.loader is not None
    skill_lint = importlib.util.module_from_spec(lint_spec)
    sys.modules[lint_spec.name] = skill_lint
    lint_spec.loader.exec_module(skill_lint)
    findings, refused = skill_lint.run_check(owned_dir=paths.owned_skills_dir)
    assert findings == []
    assert refused == []


def test_create_skill_commits_with_skill_actor_trailer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-newskill2")
    paths = _make_paths(tmp_path)

    curator.create_skill(paths, "worker-fresh-skill", description="desc", audience=["all"])

    log = _log_text(paths)
    assert "skill-curator: create worker-fresh-skill" in log
    assert "Skill-Actor: developer/task-newskill2" in log


def test_create_skill_refuses_existing_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-x")
    paths = _make_paths(tmp_path)
    _write_skill(paths.owned_skills_dir, "already-here", created_by="human")

    with pytest.raises(curator.CuratorError, match="already exists"):
        curator.create_skill(paths, "already-here", description="x", audience=["all"])


def test_create_skill_rejects_path_traversal_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-x")
    paths = _make_paths(tmp_path)
    with pytest.raises(curator.CuratorError, match="invalid skill name"):
        curator.create_skill(paths, "../evil", description="x", audience=["all"])


def test_skill_actor_defaults_to_ceo_when_no_identity_env_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for var in ("WORKER_TASK_ID", "WORKER_ROLE", "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    paths = _make_paths(tmp_path)

    curator.create_skill(paths, "ceo-authored-skill", description="d", audience=["all"])

    log = _log_text(paths)
    assert "Skill-Actor: CEO/-" in log


def test_history_skill_shows_commits_with_trailer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-hist1")
    paths = _make_paths(tmp_path)
    curator.create_skill(paths, "history-target", description="desc", audience=["all"])
    curator.pin_skill(paths, "history-target")

    log = curator.history_skill(paths, "history-target")
    assert "skill-curator: create history-target" in log
    assert "skill-curator: pin history-target" in log
    assert log.count("Skill-Actor: developer/task-hist1") == 2


def test_history_of_archived_skill_still_shows_earlier_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`history --skill NAME` targets the owned-dir path per the brief's own
    literal `git log --follow -- .claude/skills/<name>` spec -- this proves
    that still surfaces a skill's full history even after it has been moved
    to the archive dir (git log finds commits that touched the path
    historically; it need not exist at HEAD)."""
    _set_worker_identity(monkeypatch, role="developer", task_id="task-hist3")
    paths = _make_paths(tmp_path)
    curator.create_skill(paths, "archived-history", description="d", audience=["all"])
    curator.archive_skill(paths, "archived-history")

    log = curator.history_skill(paths, "archived-history")
    assert "skill-curator: create archived-history" in log
    assert "skill-curator: archive archived-history" in log


def test_history_without_skill_returns_whole_tree_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-hist2")
    paths = _make_paths(tmp_path)
    curator.create_skill(paths, "tree-one", description="d", audience=["all"])
    curator.create_skill(paths, "tree-two", description="d", audience=["all"])

    log = curator.history_skill(paths)
    assert "skill-curator: create tree-one" in log
    assert "skill-curator: create tree-two" in log


def test_undo_reverses_archive_and_restores_content_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The brief's own acceptance demonstration: archive a skill in a
    throwaway repo, then `undo` it, and show the content restored
    byte-for-byte -- via `git revert`, not the curator's own `restore` verb
    (which is a separate, non-git lifecycle action -- see its own docstring)."""
    _set_worker_identity(monkeypatch, role="developer", task_id="task-undo1")
    paths = _make_paths(tmp_path)

    dest = curator.create_skill(paths, "undo-me", description="original content here", audience=["all"])
    original = (dest / "SKILL.md").read_bytes()

    curator.archive_skill(paths, "undo-me")
    assert not (paths.owned_skills_dir / "undo-me").exists()

    archive_sha = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--grep=skill-curator: archive undo-me"],
        cwd=str(paths.owned_skills_dir), capture_output=True, text=True,
    ).stdout.strip()
    assert archive_sha, "sanity: the archive commit must be findable to undo it"

    curator.undo_mutation(paths, archive_sha)

    restored = (paths.owned_skills_dir / "undo-me" / "SKILL.md").read_bytes()
    assert restored == original
    assert not (paths.archive_dir / "undo-me").exists()


def test_undo_bad_sha_raises_curator_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-x")
    paths = _make_paths(tmp_path)
    curator.create_skill(paths, "some-skill", description="d", audience=["all"])

    with pytest.raises(curator.CuratorError, match="git revert"):
        curator.undo_mutation(paths, "0" * 40)


def test_drift_is_empty_right_after_a_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_worker_identity(monkeypatch, role="developer", task_id="task-drift0")
    paths = _make_paths(tmp_path)
    curator.create_skill(paths, "clean-skill", description="d", audience=["all"])

    assert curator.detect_drift(paths) == ""


def test_drift_detects_a_hand_edited_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """This is the whole detection story CEO rule 4 leaves us with: no gate
    can stop a skill being hand-edited outside the curator, so `drift` is
    how it's caught -- one `git status` call."""
    _set_worker_identity(monkeypatch, role="developer", task_id="task-drift1")
    paths = _make_paths(tmp_path)
    dest = curator.create_skill(paths, "drift-target", description="d", audience=["all"])

    (dest / "SKILL.md").write_text(
        (dest / "SKILL.md").read_text(encoding="utf-8") + "\nhand-edited line\n", encoding="utf-8"
    )

    drift = curator.detect_drift(paths)
    assert "drift-target" in drift
    assert " M " in drift  # git status --porcelain: modified, not staged


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
