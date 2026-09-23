"""Tests for tools/skill_objection.py (ADR 0022 §6, playbook Wave 4 §4.2).

pytest style, tmp_path fixtures only (ADR 0021 §1). Points `lib.db.DB_PATH`
at a tmp_path sqlite file -- same pattern as scripts/test_dev_message.py --
and stubs the LungNote call -- never touches the real state/tasks.db or the
real LungNote (hard constraint #4).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.skill_objection as so  # noqa: E402


def _write_skill(base: Path, name: str, author: dict | None) -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"name: {name}"]
    if author is not None:
        lines.append(f'author: {{role: {author["role"]}, date: "2026-09-01"}}')
    lines += ["description: fixture skill for skill_objection tests", "---", "",
              f"# {name}", ""]
    (d / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
    return d


@pytest.fixture(autouse=True)
def clean_identity_env(monkeypatch: pytest.MonkeyPatch):
    """Same var list as scripts/test_send_to_cto.py -- this DEV harness's own
    ambient WORKER_TASK_ID/WORKER_ROLE must not leak into a test's identity
    resolution; each test sets exactly what it needs."""
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
                "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return tmp_path


@pytest.fixture()
def no_lungnote(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub the LungNote write and record what it was called with, instead
    of shelling out to scripts/lib/mcp_call.py against the real server."""
    calls: list[str] = []
    monkeypatch.setattr(so, "_add_lungnote_todo", lambda text: calls.append(text))
    return calls


# --------------------------------------------------------------------------
# resolve_author — frontmatter resolution, absent -> cto
# --------------------------------------------------------------------------

def test_role_resolved_from_frontmatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill_dir = _write_skill(tmp_path, "some-skill", author={"role": "browser_operator"})
    monkeypatch.setattr(so, "_skill_dir", lambda name: skill_dir)
    assert so.resolve_author("some-skill") == "browser_operator"


def test_absent_author_field_routes_to_cto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill_dir = _write_skill(tmp_path, "some-skill", author=None)
    monkeypatch.setattr(so, "_skill_dir", lambda name: skill_dir)
    assert so.resolve_author("some-skill") == "cto"


def test_unresolvable_skill_routes_to_cto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(so, "_skill_dir", lambda name: None)
    assert so.resolve_author("no-such-skill") == "cto"


# --------------------------------------------------------------------------
# raise_objection — one event, one LungNote to-do
# --------------------------------------------------------------------------

def test_raise_objection_writes_exactly_one_event(
    isolated_db, no_lungnote, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(so, "_skill_dir", lambda name: None)  # -> cto
    monkeypatch.setenv("WORKER_TASK_ID", "task-abc12345")
    monkeypatch.setenv("WORKER_ROLE", "developer")

    payload = so.raise_objection("some-skill", "told me to do X", "did Y instead")

    assert payload["author"] == "cto"
    events = db_mod.recent_events(limit=10, task_id="task-abc12345")
    objection_events = [e for e in events if e["kind"] == "skill_objection"]
    assert len(objection_events) == 1
    logged = json.loads(objection_events[0]["payload"])
    assert logged == {
        "skill": "some-skill", "conflict": "told me to do X",
        "did_instead": "did Y instead", "blocked": False,
        "author": "cto", "raised_by": "developer/task-abc12345",
    }
    assert objection_events[0]["actor"] == "developer/task-abc12345"


def test_raise_objection_adds_lungnote_todo_addressed_to_author(
    isolated_db, no_lungnote, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill_dir = _write_skill(Path(isolated_db), "flaky-skill", author={"role": "cmo"})
    monkeypatch.setattr(so, "_skill_dir", lambda name: skill_dir)
    monkeypatch.setenv("WORKER_TASK_ID", "task-def67890")

    so.raise_objection("flaky-skill", "contradicts the brand voice", "wrote it my way",
                        blocked=True)

    assert len(no_lungnote) == 1
    assert "cmo" in no_lungnote[0]
    assert "flaky-skill" in no_lungnote[0]
    assert "BLOCKED" in no_lungnote[0]


def test_add_lungnote_todo_swallows_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*a, **kw):
        raise RuntimeError("lungnote is down")
    monkeypatch.setattr(so.subprocess, "run", _boom)
    so._add_lungnote_todo("some text")  # must not raise


def test_raise_objection_completes_when_lungnote_is_down(
    isolated_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The DB event is durable; a LungNote outage must not take the call
    down with it (fail-open, matches request_human_handoff's chat relay)."""
    monkeypatch.setattr(so, "_skill_dir", lambda name: None)

    def _boom(*a, **kw):
        raise RuntimeError("lungnote is down")
    monkeypatch.setattr(so.subprocess, "run", _boom)

    payload = so.raise_objection("some-skill", "conflict", "did instead")
    assert payload["author"] == "cto"


# --------------------------------------------------------------------------
# summary() / list_objections() — feed the `obj` column
# --------------------------------------------------------------------------

def test_summary_open_equals_total_and_keeps_last_conflict(
    isolated_db, no_lungnote, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(so, "_skill_dir", lambda name: None)
    monkeypatch.setenv("WORKER_TASK_ID", "task-aaa11111")

    so.raise_objection("skill-a", "conflict 1", "did 1")
    so.raise_objection("skill-a", "conflict 2", "did 2")
    so.raise_objection("skill-b", "conflict 3", "did 3")

    result = so.summary(days=30)
    assert result["skill-a"] == {"open": 2, "total": 2, "last_conflict": "conflict 2"}
    assert result["skill-b"] == {"open": 1, "total": 1, "last_conflict": "conflict 3"}


def test_summary_excludes_objections_older_than_the_window(
    isolated_db, no_lungnote, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(so, "_skill_dir", lambda name: None)
    monkeypatch.setenv("WORKER_TASK_ID", "task-bbb22222")
    so.raise_objection("skill-a", "conflict", "did")
    assert so.summary(days=0) == {}


def test_list_objections_newest_first(
    isolated_db, no_lungnote, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(so, "_skill_dir", lambda name: None)
    monkeypatch.setenv("WORKER_TASK_ID", "task-ccc33333")
    so.raise_objection("skill-a", "c1", "d1")
    so.raise_objection("skill-b", "c2", "d2")
    rows = so.list_objections(limit=10)
    assert [r["skill"] for r in rows[:2]] == ["skill-b", "skill-a"]


# --------------------------------------------------------------------------
# 4.4 — silence alone must never be sufficient to archive a skill
# --------------------------------------------------------------------------

def test_silence_alone_never_archives_a_skill(tmp_path: Path) -> None:
    """Hermes' own curator: "'use=0' is not evidence a skill is valuable;
    it's absence of evidence either way." A skill with zero fires and no
    git history to judge it by gets NO proposal at all -- not "stale", not
    "archived" -- because there is no basis to judge it, which is the
    invariant that keeps a quiet-but-vital skill from being swept away.
    Exercises the real, unmodified scripts/skill-curator.py logic."""
    curator = so._load("_curator_for_test", so._CURATOR_PATH)
    owned = tmp_path / "owned-skills"
    owned.mkdir()
    skill_dir = _write_skill(owned, "brand-new-skill", author=None)
    # force created_by: agent so a bug that ignored idle_days entirely would
    # still show up here as a false proposal (created_by absent -> "human"
    # -> non-actionable regardless, which would hide such a bug).
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text().replace(
            "name: brand-new-skill", "name: brand-new-skill\ncreated_by: agent"
        )
    )
    paths = curator.CuratorPaths(
        owned_skills_dir=owned,
        log_path=tmp_path / "state" / "skill-usage.log",  # never fired -- no file at all
        archive_dir=tmp_path / "skills-archive",
        backup_dir=tmp_path / "backups",
        merge_external=False,
    )
    assert curator.compute_proposals(paths) == []


# --------------------------------------------------------------------------
# hard constraint #1 — never hardcode /Users/gob/MoonieXHQ/Agents/Core
# --------------------------------------------------------------------------

def test_root_is_derived_from_file_location_not_hardcoded() -> None:
    """ROOT must be computed from this file's own location so the identical
    module is correct unchanged on Contabo at /opt/mooniex-agents."""
    assert so.ROOT == Path(__file__).resolve().parent.parent
