#!/usr/bin/env python3
"""PostToolUse hook (Edit|Write|MultiEdit) -- remind the author of the skill
procedure at the moment a SKILL.md is written (CEO "Ok ลุย" 2026-09-28;
docs/org/SKILL-KINDS-2026-09-27.md, "Where the kind lives" item 3).

Reads the hook event JSON on stdin (Claude Code hook contract):
  {"tool_name": "Edit", "tool_input": {"file_path": "...", ...}, "cwd": "...", ...}

Acts only when `tool_input.file_path` is `<anything>/.claude/skills/<name>/SKILL.md`
and <name> is not an imported public skill (config/skill-kinds.yaml `imported:`).
Then prints ONE PostToolUse JSON object whose
`hookSpecificOutput.additionalContext` (≤12 lines) carries:
  - which procedure applies -- a hook cannot tell reliably whether the file
    existed before the edit, so it names both: §4 Create for a new skill,
    §5 Update otherwise (.claude/skills/ALL_Protocol_SkillAuthor/SKILL.md)
  - the canonical Field-note line and the commit prefix
  - whether docs/org/SKILL-INDEX.md is now stale (skill-lint code 16)
  - skill-lint's findings for THAT skill only (skill-lint.py's own functions)

Never blocks, never fails: exit 0 on every path, silent on anything it does
not understand. Bare `python3` may lack PyYAML (the Mac's does): the lint
half then degrades to "not run here" and the reminder still goes out -- the
imported list is read with a stdlib fallback so that check never needs yaml.
The lint half runs under a time budget so the hook stays under a second.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LINT_PATH = HERE / "skill-lint.py"
MAX_FINDINGS_SHOWN = 5          # 7 fixed lines + 5 = the 12-line ceiling
FINDING_WIDTH = 220


def _budget() -> float:
    """Seconds the lint half may take; the tests raise it so a loaded box cannot flake them."""
    try:
        return float(os.environ.get("SKILL_WRITE_HOOK_BUDGET_S", "0.8"))
    except ValueError:
        return 0.8


def skill_target(file_path: str, cwd: Optional[str] = None) -> Optional[tuple[str, Path]]:
    """(skill name, repo root) for `<root>/.claude/skills/<name>/SKILL.md`, else None."""
    if not isinstance(file_path, str) or not file_path:
        return None
    p = Path(file_path)
    if not p.is_absolute() and cwd:
        p = Path(cwd) / p
    parts = p.parts
    if len(parts) < 4 or parts[-1] != "SKILL.md" or tuple(parts[-4:-2]) != (".claude", "skills"):
        return None
    return parts[-2], Path(*parts[:-4]) if len(parts) > 4 else Path(".")


def _plain_list(text: str, key: str) -> list[str]:
    """Stdlib-only reader for a top-level `key: [a, b]` or `key:` + `  - a` list."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).split("#", 1)[0].strip()
        if rest.startswith("["):
            buf, j = rest, i
            while "]" not in buf and j + 1 < len(lines):
                j += 1
                buf += " " + lines[j].split("#", 1)[0].strip()
            inner = buf[1:buf.index("]")] if "]" in buf else buf[1:]
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
        items: list[str] = []
        for later in lines[i + 1:]:
            s = later.split("#", 1)[0].rstrip()
            if not s.strip():
                continue
            mm = re.match(r"^\s+-\s+(.+)$", s)
            if not mm:
                break
            items.append(mm.group(1).strip().strip("'\""))
        return items
    return []


def config_list(config: Path, key: str) -> list[str]:
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        import yaml  # noqa: PLC0415 - optional: bare python3 may not have it
    except ImportError:
        return _plain_list(text, key)
    try:
        value = (yaml.safe_load(text) or {}).get(key) or []
    except Exception:  # noqa: BLE001
        return _plain_list(text, key)
    return [str(v) for v in value] if isinstance(value, list) else []


def _config_for(root: Path) -> Path:
    own = root / "config" / "skill-kinds.yaml"
    return own if own.is_file() else REPO / "config" / "skill-kinds.yaml"


def _load_lint():
    spec = importlib.util.spec_from_file_location("_skill_lint_for_write_hook", LINT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # imports yaml: raises ImportError without PyYAML
    return mod


def lint_report(name: str, root: Path) -> dict:
    """{"findings": [...], "index": "stale"|"fresh"|None} or {"error": "..."}.
    Everything the lint can raise is caught here -- no PyYAML, a broken
    frontmatter, a missing file -- and comes back as "error"."""
    try:
        lint = _load_lint()
        agents = root / "policies" / "agents.yaml"
        agents = agents if agents.is_file() else lint.AGENTS_YAML
        rules = lint.load_naming_rules(_config_for(root), agents)
        skills_dir = root / ".claude" / "skills"
        findings = lint.lint_skill(name, skills_dir / name, lint._known_audience_tokens(agents), rules=rules)
        index_md = root / "docs" / "org" / "SKILL-INDEX.md"
        index_state = None
        if index_md.is_file():
            index_state = "stale" if lint.index_finding(skills_dir, index_md, rules) else "fresh"
        return {"findings": [(f.code, f.code_name, f.message) for f in findings], "index": index_state}
    except ImportError as exc:
        return {"error": f"no {getattr(exc, 'name', None) or 'module'} for this python"}
    except Exception as exc:  # noqa: BLE001 - a reminder hook must never fail
        return {"error": f"{exc.__class__.__name__}: {str(exc)[:80]}"}


def lint_report_within(name: str, root: Path, budget_s: Optional[float] = None) -> dict:
    budget_s = _budget() if budget_s is None else budget_s
    box: dict = {}
    worker = threading.Thread(target=lambda: box.update(lint_report(name, root)), daemon=True)
    worker.start()
    worker.join(budget_s)
    if worker.is_alive() or not box:
        return {"error": f"took over {budget_s:g} s"}
    return box


def build_context(name: str, report: dict) -> str:
    lines = [
        f"SKILL.md written: {name} -- ALL_Protocol_SkillAuthor applies (a reminder; nothing is blocked).",
        "- New skill -> §4 Create: search for an owner first, one kind, <ROLE>_<Kind>_<Topic>, lint, commit `new`.",
        "- Existing skill -> §5 Update: one sighting = one Field note; the rule body changes only on >=2 runs, "
        "a CEO ruling or an artefact.",
        "- Field note: `- YYYY-MM-DD [WRONG|MISSING|COSTLY] §<section> — <what> · evidence: <task-id / sha / path> "
        "· status: pending`",
        f"- Commit: `skill({name}): note | rule | flip | new — <what> — evidence <…>` (stage named paths only).",
    ]
    index = report.get("index")
    if index == "stale":
        lines.append("- docs/org/SKILL-INDEX.md is now stale: run `.venv/bin/python scripts/skill-curator.py index` "
                     "and commit it with the skill.")
    elif index == "fresh":
        lines.append("- docs/org/SKILL-INDEX.md still matches; if name, kind or description change, "
                     "re-run `scripts/skill-curator.py index`.")
    else:
        lines.append("- If name, kind or description changed: `.venv/bin/python scripts/skill-curator.py index` "
                     "and commit docs/org/SKILL-INDEX.md.")
    if "error" in report:
        lines.append(f"- skill-lint not run here ({report['error']}): `.venv/bin/python scripts/skill-lint.py check`.")
        return "\n".join(lines)
    findings = report.get("findings") or []
    if not findings:
        lines.append(f"- skill-lint for {name}: clean.")
        return "\n".join(lines)
    lines.append(f"- skill-lint for {name}: {len(findings)} finding(s):")
    shown = findings if len(findings) <= MAX_FINDINGS_SHOWN else findings[: MAX_FINDINGS_SHOWN - 1]
    for code, code_name, message in shown:
        line = f"  [{code}] {code_name}: {message}"
        lines.append(line if len(line) <= FINDING_WIDTH else line[: FINDING_WIDTH - 1] + "…")
    if len(shown) < len(findings):
        lines.append(f"  … {len(findings) - len(shown)} more: `.venv/bin/python scripts/skill-lint.py check`")
    return "\n".join(lines)


def main() -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        tool_input = event.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return 0
        target = skill_target(tool_input.get("file_path"), event.get("cwd"))
        if target is None:
            return 0
        name, root = target
        if name in config_list(_config_for(root), "imported"):
            return 0
        context = build_context(name, lint_report_within(name, root))
        sys.stdout.write(json.dumps({
            "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context},
        }) + "\n")
        sys.stdout.flush()
    except Exception:  # noqa: BLE001 - never fail, never block
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
