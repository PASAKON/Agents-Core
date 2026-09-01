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
reads only the log_path/state_path handed to it. This module never opens
state/skill-usage.log, state/skill-usage.json, ~/.claude/skills/, or
anything under output/ (ADR 0021 §"tests must not write to real state").

Run standalone:   python scripts/test_skill_curator.py
Or under pytest:  pytest scripts/test_skill_curator.py
"""
from __future__ import annotations

import importlib.util
import json
import os
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


def _make_paths(tmp_path: Path) -> "curator.CuratorPaths":
    owned = tmp_path / "owned-skills"
    owned.mkdir()
    return curator.CuratorPaths(
        owned_skills_dir=owned,
        log_path=tmp_path / "state" / "skill-usage.log",
        state_path=tmp_path / "state" / "skill-usage.json",
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
    assert restored == original

    state = json.loads(paths.state_path.read_text(encoding="utf-8"))
    assert state["roundtrip-skill"]["lifecycle"] == "active"


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
    assert not paths.state_path.exists()
    assert not paths.archive_dir.exists()
    assert not paths.backup_dir.exists()

    proposals = curator.compute_proposals(paths)
    assert proposals, "sanity: the fixture should produce at least one proposal"

    after = _snapshot(paths.owned_skills_dir)
    assert before == after
    assert not paths.state_path.exists()
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
