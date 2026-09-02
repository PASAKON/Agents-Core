"""Tests for scripts/hook-skill-log.py (Wave 0 skill-governance telemetry).

Covers the three Wave 0 defects (org:decisions/0022-skill-governance-visibility-
authorship-audit.md, org:playbooks/skill-governance-implementation.md §Wave 0):

  0.1 log destination — ORG_SKILL_LOG env override, and proof that the
      worktree-relative default is *derived* from the script's own __file__
      rather than a hardcoded repo root (hard constraint: never hardcode
      /Users/gob/Projects/Agents — the same repo also lives at
      /opt/mooniex-agents on the Contabo VPS).
  0.3 role column — WORKER_ROLE first, CXO_ROLE fallback, "-" when neither is
      set; and that scripts/skill-report.py's reader still parses the 422
      legacy 3-field lines (role padded to "-") alongside new 4-field ones.

Also guards the hard constraint that the hook must never import yaml (bare
`python3` has no PyYAML — only .venv does) and must never raise.

Run standalone:   python scripts/test_hook_skill_log.py
Or under pytest:  pytest scripts/test_hook_skill_log.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = ROOT / "scripts" / "hook-skill-log.py"
SKILL_REPORT_SRC = ROOT / "scripts" / "skill-report.py"


def _counter():
    n = 0
    while True:
        n += 1
        yield n


_next_id = _counter().__next__


def _load_module(script_path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_hook(script_path: Path = HOOK_SRC):
    # Fresh module name per call so monkeypatched env vars from a previous
    # test can't leak in via a cached sys.modules entry.
    return _load_module(script_path, f"hook_skill_log_under_test_{_next_id()}")


def _copy_hook_into(dest_root: Path) -> Path:
    """Copy the real hook script under dest_root/scripts/, so its own
    __file__ resolves somewhere that is neither /Users/gob/Projects/Agents
    nor /opt/mooniex-agents — proving the default log path is derived from
    __file__, not hardcoded to either known repo root.
    """
    scripts_dir = dest_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    dest = scripts_dir / "hook-skill-log.py"
    dest.write_text(HOOK_SRC.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _feed_stdin(monkeypatch: pytest.MonkeyPatch, event: dict) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))


# --------------------------------------------------------------------------
# hard constraints — regression guards
# --------------------------------------------------------------------------

def test_hook_never_imports_yaml() -> None:
    """PyYAML is only in .venv; the hook runs as a bare `python3` PostToolUse
    subprocess. Measured this session: both /opt/homebrew/bin/python3 and
    /usr/bin/python3 raise ModuleNotFoundError: No module named 'yaml'.
    """
    source = HOOK_SRC.read_text(encoding="utf-8")
    assert "import yaml" not in source
    assert "from yaml" not in source


# --------------------------------------------------------------------------
# 0.1 — log destination
# --------------------------------------------------------------------------

def test_default_log_path_derives_from_script_location_not_hardcoded(tmp_path: Path) -> None:
    fake_root = tmp_path / "opt" / "some-other-checkout"
    script_copy = _copy_hook_into(fake_root)
    mod = _load_hook(script_copy)

    resolved = mod._default_log_path()
    assert resolved == fake_root / "state" / "skill-usage.log"
    assert "/Users/gob/Projects/Agents" not in str(resolved)
    assert "/opt/mooniex-agents" not in str(resolved)


def test_default_log_path_differs_across_two_fake_roots(tmp_path: Path) -> None:
    """Same script content, two different install locations -> two different
    derived paths. Proves derivation, not a cached/hardcoded constant.
    """
    root_a = tmp_path / "checkout-a"
    root_b = tmp_path / "checkout-b"
    mod_a = _load_hook(_copy_hook_into(root_a))
    mod_b = _load_hook(_copy_hook_into(root_b))

    assert mod_a._default_log_path() == root_a / "state" / "skill-usage.log"
    assert mod_b._default_log_path() == root_b / "state" / "skill-usage.log"
    assert mod_a._default_log_path() != mod_b._default_log_path()


def test_org_skill_log_env_overrides_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "shared" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(custom))
    mod = _load_hook()
    assert mod._log_path() == custom


def test_log_path_falls_back_to_default_when_env_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORG_SKILL_LOG", raising=False)
    script_copy = _copy_hook_into(tmp_path / "checkout")
    mod = _load_hook(script_copy)
    assert mod._log_path() == mod._default_log_path()


def test_main_writes_to_org_skill_log_from_inside_a_worktree_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates the exact bug scenario: the hook script is a worktree's own
    copy (so its default path would strand the fire in the worktree), but
    ORG_SKILL_LOG — as the user-level ~/.claude/settings.json registration
    would set it — routes the write to the single shared main-repo log.
    """
    worktree_copy = _copy_hook_into(tmp_path / "worktrees" / "some-repo__dev__task-abc")
    shared_log = tmp_path / "main-repo" / "state" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(shared_log))
    monkeypatch.setenv("WORKER_ROLE", "developer")

    mod = _load_hook(worktree_copy)
    _feed_stdin(monkeypatch, {
        "tool_name": "Skill",
        "tool_input": {"skill": "debug-mantra"},
        "session_id": "sess-abc",
    })

    assert mod.main() == 0
    assert shared_log.is_file()
    stray = worktree_copy.parent.parent / "state" / "skill-usage.log"
    assert not stray.exists()

    line = shared_log.read_text(encoding="utf-8").splitlines()[0]
    parts = line.split("\t")
    assert parts[1] == "debug-mantra"
    assert parts[2] == "sess-abc"
    assert parts[3] == "developer"


# --------------------------------------------------------------------------
# 0.3 — role column
# --------------------------------------------------------------------------

def test_role_prefers_worker_role_over_cxo_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ROLE", "browser_operator")
    monkeypatch.setenv("CXO_ROLE", "cto")
    mod = _load_hook()
    assert mod._role() == "browser_operator"


def test_role_falls_back_to_cxo_role_for_c_level_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKER_ROLE", raising=False)
    monkeypatch.setenv("CXO_ROLE", "cto")
    mod = _load_hook()
    assert mod._role() == "cto"


def test_role_is_dash_when_neither_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKER_ROLE", raising=False)
    monkeypatch.delenv("CXO_ROLE", raising=False)
    mod = _load_hook()
    assert mod._role() == "-"


def test_main_appends_four_field_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "state" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(log_path))
    monkeypatch.setenv("WORKER_ROLE", "developer")
    monkeypatch.delenv("CXO_ROLE", raising=False)
    mod = _load_hook()

    _feed_stdin(monkeypatch, {
        "tool_name": "Skill",
        "tool_input": {"skill": "scrutinize"},
        "session_id": "sess-1",
    })
    assert mod.main() == 0

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parts = lines[0].split("\t")
    assert len(parts) == 4
    assert parts[1] == "scrutinize"
    assert parts[2] == "sess-1"
    assert parts[3] == "developer"


def test_main_c_level_fire_records_dash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "state" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(log_path))
    monkeypatch.delenv("WORKER_ROLE", raising=False)
    monkeypatch.delenv("CXO_ROLE", raising=False)
    mod = _load_hook()

    _feed_stdin(monkeypatch, {
        "tool_name": "Skill",
        "tool_input": {"skill": "post-mortem"},
        "session_id": "sess-2",
    })
    mod.main()

    parts = log_path.read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert parts[3] == "-"


def test_main_appends_without_clobbering_prior_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "state" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(log_path))
    monkeypatch.setenv("WORKER_ROLE", "developer")
    mod = _load_hook()

    for i in range(3):
        _feed_stdin(monkeypatch, {
            "tool_name": "Skill",
            "tool_input": {"skill": f"skill-{i}"},
            "session_id": "sess",
        })
        mod.main()

    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 3


# --------------------------------------------------------------------------
# never raises / silent on non-Skill and malformed input
# --------------------------------------------------------------------------

def test_main_ignores_non_skill_tool_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "state" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(log_path))
    mod = _load_hook()

    _feed_stdin(monkeypatch, {"tool_name": "Bash", "tool_input": {}, "session_id": "sess"})
    assert mod.main() == 0
    assert not log_path.exists()


def test_main_malformed_json_never_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "state" / "skill-usage.log"
    monkeypatch.setenv("ORG_SKILL_LOG", str(log_path))
    mod = _load_hook()

    monkeypatch.setattr(sys, "stdin", io.StringIO("not json{{{"))
    assert mod.main() == 0
    assert not log_path.exists()


def test_main_unwritable_log_dir_never_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file sitting where the log's parent directory needs to be created
    makes mkdir() raise — main() must swallow it (existing try/except
    discipline), not propagate, since this is a PostToolUse hook.
    """
    blocker = tmp_path / "blocked-parent"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setenv("ORG_SKILL_LOG", str(blocker / "state" / "skill-usage.log"))
    mod = _load_hook()

    _feed_stdin(monkeypatch, {
        "tool_name": "Skill",
        "tool_input": {"skill": "debug-mantra"},
        "session_id": "sess",
    })
    assert mod.main() == 0


# --------------------------------------------------------------------------
# scripts/skill-report.py — the other reader, must pad legacy 3-field lines
# --------------------------------------------------------------------------

def _load_skill_report():
    return _load_module(SKILL_REPORT_SRC, f"skill_report_under_test_{_next_id()}")


def test_skill_report_load_log_pads_legacy_three_field_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "skill-usage.log"
    log_path.write_text(
        "2026-08-01T00:00:00+00:00\tdebug-mantra\tlegacy-session\n"
        "2026-09-01T00:00:00+00:00\tscrutinize\tnew-session\tdeveloper\n",
        encoding="utf-8",
    )
    mod = _load_skill_report()
    monkeypatch.setattr(mod, "LOG", log_path)
    # Stub the worktree fold-in (ADR 0022 Wave 4). Without this the assertion
    # below counts whatever worktrees/*/state/skill-usage.log happen to exist
    # on this machine, so the test's result changes when an unrelated session
    # creates or reaps a worktree.
    monkeypatch.setattr(mod, "_worktree_logs", lambda: [])

    entries = mod._load_log()
    assert len(entries) == 2

    _legacy_ts, legacy_skill, legacy_session, legacy_role = entries[0]
    assert legacy_skill == "debug-mantra"
    assert legacy_session == "legacy-session"
    assert legacy_role == "-"

    _new_ts, new_skill, new_session, new_role = entries[1]
    assert new_skill == "scrutinize"
    assert new_session == "new-session"
    assert new_role == "developer"


def test_skill_report_summarize_still_counts_across_mixed_field_widths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "skill-usage.log"
    log_path.write_text(
        "2026-08-01T00:00:00+00:00\tdebug-mantra\tlegacy-session\n"
        "2026-08-02T00:00:00+00:00\tdebug-mantra\tanother-legacy\n"
        "2026-09-01T00:00:00+00:00\tdebug-mantra\tnew-session\tdeveloper\n",
        encoding="utf-8",
    )
    mod = _load_skill_report()
    monkeypatch.setattr(mod, "LOG", log_path)

    entries = mod._load_log()
    count, _last, sessions = mod._summarize(entries)
    assert count["debug-mantra"] == 3
    assert len(sessions["debug-mantra"]) == 3


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
