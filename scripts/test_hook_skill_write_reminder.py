"""Tests for scripts/hook-skill-write-reminder.py (CEO "Ok ลุย" 2026-09-28).

The PostToolUse hook that reminds the author of ALL_Protocol_SkillAuthor when
a `.claude/skills/<name>/SKILL.md` is written:
  - a skill path -> one PostToolUse JSON with additionalContext (≤12 lines):
    §4 / §5, the Field-note line, the commit prefix, the index, the lint
  - any other path, an imported skill, malformed stdin -> no output, exit 0
  - no PyYAML -> the reminder still goes out, without lint findings

Every fixture repo lives under tmp_path (its own config/skill-kinds.yaml and
policies/agents.yaml, copied read-only from the real ones); this module never
writes to the real .claude/skills/ or docs/.

Run standalone:   python scripts/test_hook_skill_write_reminder.py
Or under pytest:  pytest scripts/test_hook_skill_write_reminder.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "scripts" / "hook-skill-write-reminder.py"

_n = 0


def _load_hook():
    global _n
    _n += 1
    spec = importlib.util.spec_from_file_location(f"hook_skill_write_reminder_{_n}", HOOK)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    (root / "policies").mkdir()
    shutil.copy(ROOT / "config" / "skill-kinds.yaml", root / "config" / "skill-kinds.yaml")
    shutil.copy(ROOT / "policies" / "agents.yaml", root / "policies" / "agents.yaml")
    return root


def _skill(root: Path, name: str, frontmatter: str) -> Path:
    d = root / ".claude" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    md = d / "SKILL.md"
    md.write_text(f"---\nname: {name}\n{frontmatter}\n---\n\n# {name}\n\nbody\n", encoding="utf-8")
    return md


_GOOD = ('kind: gate\nowner: CTO\naudience: [cto]\ncreated_by: agent\n'
         'description: "GATE — A fixture gate. Trigger on /CTO_Gate_Thing."')


def _run(event, *, python: str = sys.executable) -> subprocess.CompletedProcess:
    stdin = event if isinstance(event, str) else json.dumps(event)
    env = dict(os.environ, SKILL_WRITE_HOOK_BUDGET_S="15")  # the 0.8 s budget has its own test below
    return subprocess.run([python, str(HOOK)], input=stdin, capture_output=True, text=True, timeout=30, env=env)


def _context(stdout: str) -> str:
    payload = json.loads(stdout)
    out = payload["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    return out["additionalContext"]


def test_skill_path_gets_the_reminder(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    md = _skill(root, "CTO_Gate_Thing", _GOOD)
    r = _run({"tool_name": "Write", "tool_input": {"file_path": str(md), "content": "x"}})
    assert r.returncode == 0 and r.stderr == ""
    ctx = _context(r.stdout)
    assert "CTO_Gate_Thing" in ctx
    assert "§4 Create" in ctx and "§5 Update" in ctx
    assert "[WRONG|MISSING|COSTLY] §<section> — <what> · evidence: <task-id / sha / path> · status: pending" in ctx
    assert "skill(CTO_Gate_Thing): note | rule | flip | new — <what> — evidence <…>" in ctx
    assert "skill-curator.py index" in ctx
    assert "skill-lint for CTO_Gate_Thing: clean." in ctx
    assert len(ctx.splitlines()) <= 12


def test_findings_for_that_skill_only_are_listed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _skill(root, "CTO_Gate_Other", 'description: "no kind"')          # would be dirty too -- must not show
    md = _skill(root, "CTO_Gate_Thing", 'audience: [cto]\ndescription: "no prefix here"')
    r = _run({"tool_name": "Edit", "tool_input": {"file_path": str(md)}})
    ctx = _context(r.stdout)
    assert "skill-lint for CTO_Gate_Thing: 3 finding(s):" in ctx
    assert "[11] bad-kind" in ctx and "[13] bad-owner" in ctx and "[14] description-kind-prefix" in ctx
    assert "CTO_Gate_Other" not in ctx


def test_many_findings_stay_within_twelve_lines(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    md = _skill(root, "not-a-name", 'audience: [qa, ghost, nobody]\ncreated_by: cto\ndescription: "x"')
    r = _run({"tool_name": "Edit", "tool_input": {"file_path": str(md)}})
    ctx = _context(r.stdout)
    assert len(ctx.splitlines()) == 12
    assert "more: `.venv/bin/python scripts/skill-lint.py check`" in ctx


def test_stale_and_fresh_index_are_named(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    md = _skill(root, "CTO_Gate_Thing", _GOOD)
    index = root / "docs" / "org" / "SKILL-INDEX.md"
    index.parent.mkdir(parents=True)
    index.write_text("old\n", encoding="utf-8")
    stale = _context(_run({"tool_input": {"file_path": str(md)}}).stdout)
    assert "SKILL-INDEX.md is now stale" in stale

    curator_spec = importlib.util.spec_from_file_location("_cur_for_hook_test", ROOT / "scripts" / "skill-curator.py")
    cur = importlib.util.module_from_spec(curator_spec)
    sys.modules[curator_spec.name] = cur
    curator_spec.loader.exec_module(cur)
    index.write_text(cur.render_skill_index(root / ".claude" / "skills",
                                            cur.load_skill_kinds(root / "config" / "skill-kinds.yaml")),
                     encoding="utf-8")
    fresh = _context(_run({"tool_input": {"file_path": str(md)}}).stdout)
    assert "SKILL-INDEX.md still matches" in fresh


@pytest.mark.parametrize("path", [
    "/somewhere/scripts/skill-lint.py",
    "/somewhere/.claude/skills/CTO_Gate_Thing/references/notes.md",
    "/somewhere/.claude/skills/CTO_Gate_Thing/sub/SKILL.md",
    "/somewhere/.claude/skills/SKILL.md",
    "/somewhere/skills/CTO_Gate_Thing/SKILL.md",
    "",
])
def test_non_skill_path_prints_nothing(path: str) -> None:
    r = _run({"tool_name": "Edit", "tool_input": {"file_path": path}})
    assert r.returncode == 0 and r.stdout == ""


def test_imported_skill_prints_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    md = _skill(root, "de-ai-ify", 'description: "Remove AI jargon."')
    r = _run({"tool_name": "Edit", "tool_input": {"file_path": str(md)}})
    assert r.returncode == 0 and r.stdout == ""


@pytest.mark.parametrize("stdin", ["", "{not json", "[1, 2]", '"a string"', '{"tool_input": "nope"}',
                                   '{"tool_input": {"file_path": 42}}'])
def test_malformed_stdin_exits_zero_silently(stdin: str) -> None:
    r = _run(stdin)
    assert r.returncode == 0 and r.stdout == ""


def test_relative_path_resolves_against_cwd(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _skill(root, "CTO_Gate_Thing", _GOOD)
    r = _run({"cwd": str(root), "tool_input": {"file_path": ".claude/skills/CTO_Gate_Thing/SKILL.md"}})
    assert "skill-lint for CTO_Gate_Thing: clean." in _context(r.stdout)


def test_without_pyyaml_the_reminder_still_goes_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                    capsys: pytest.CaptureFixture) -> None:
    """Bare python3 on the Mac has no PyYAML: `import yaml` fails inside
    skill-lint, the hook degrades to the reminder and names why."""
    root = _repo(tmp_path)
    md = _skill(root, "CTO_Gate_Thing", _GOOD)
    hook = _load_hook()
    monkeypatch.setenv("SKILL_WRITE_HOOK_BUDGET_S", "15")
    monkeypatch.setitem(sys.modules, "yaml", None)  # any `import yaml` now raises ImportError
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"file_path": str(md)}})))
    assert hook.main() == 0
    ctx = _context(capsys.readouterr().out)
    assert "§4 Create" in ctx and "skill-lint not run here (no yaml for this python)" in ctx

    imported = _skill(root, "de-ai-ify", 'description: "x"')
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"file_path": str(imported)}})))
    assert hook.main() == 0
    assert capsys.readouterr().out == ""   # the imported list is read without yaml too


def test_plain_list_reader_matches_yaml_on_the_real_config() -> None:
    import yaml

    hook = _load_hook()
    text = (ROOT / "config" / "skill-kinds.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    for key in ("kinds", "c_levels", "imported", "ceo_commands"):
        assert hook._plain_list(text, key) == data[key], key


def test_lint_over_budget_degrades_to_the_reminder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    hook = _load_hook()
    monkeypatch.setattr(hook, "lint_report", lambda name, root: time.sleep(1) or {"findings": []})
    report = hook.lint_report_within("CTO_Gate_Thing", tmp_path, budget_s=0.05)
    assert "error" in report and "took over" in report["error"]
    assert "skill-lint not run here (took over" in hook.build_context("CTO_Gate_Thing", report)


def test_registered_as_a_posttooluse_hook_on_edits() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["PostToolUse"]
    hits = [e for e in entries for h in e["hooks"] if "hook-skill-write-reminder.py" in h["command"]]
    assert len(hits) == 1
    assert set(hits[0]["matcher"].split("|")) == {"Edit", "Write", "MultiEdit"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
