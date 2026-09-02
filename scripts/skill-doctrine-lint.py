#!/usr/bin/env python3
"""scripts/skill-doctrine-lint.py -- HARD-rule doctrine lint (ADR 0022 Wave 5, section 5.3).

Hand-run only. Lists every HARD-tagged rule block across `.claude/skills/`
that is missing its required `Why hard:` clause -- the ADR 0022 section 7
binary contract: a rule block is either **HARD**, and then it carries a
**`Why hard:`** clause, or it is advice the model may override. One
absolute defect count, threshold zero.

Explicitly NOT built, per the ADR: no `--strict` mode, no ratio/score.
`cage_ratio` was proposed for this org and rejected -- it had no variance
(all 22 org skills scored identically), its 0.30 threshold was derived from
nothing, its Thai mandate-word matcher (`ต้อง` / `ห้าม`) produced
unvalidated false positives, and it had no consumer. This tool does not
resurrect it under another name, and it does not match on mandate
vocabulary ("must", "never", "always", ...) at all -- FACT/WHY advice is
free and unmeasured by design (ADR 0022 section 7), so counting how forceful
its prose sounds would be exactly the metric that got rejected. This tool
checks exactly one thing: does a HARD tag have a `Why hard:` clause nearby.

**This is a lint, not a gate.** It is never wired into pre-commit (unlike
`scripts/skill-lint.py`, which is) and must never block authoring -- ADR
0022 CEO decisions 4 and 10 forbid any approval gate, and a blocking linter
in the authoring flow is an approval gate wearing a different hat. Run it by
hand, read the findings, fix the ones that are real.

Detection: a "HARD" tag is the literal Markdown bold-open `**HARD` followed
(after optional whitespace) by a colon or a dash/em-dash -- the exact shape
every real rule tag in this corpus uses: `**HARD --` opening a numbered rule
line. This is deliberately narrow. Two looser patterns were tried and
rejected by testing against the real corpus:
  - Bare `HARD` (any case/position) matched "hardware", "HARD LIMIT" (an
    unrelated concept in another skill), and plain narrative use of the word
    ("a skill with zero HARD rules is not a defect").
  - `HARD` followed by whitespace/colon/dash with no bold-prefix requirement
    still matched narrative sentences *about* the tag itself
    ("...either HARD-with-a-reason, or...").
Requiring the bold-open immediately before HARD is what a real rule tag
always has and narrative prose about the concept never does, in this corpus.
A future skill that tags a HARD rule without the `**` bold-open will be
missed by this heuristic -- that is a known limitation of a hand-run,
regex-based lint, not a hidden gate; use the `**HARD --` convention this
file and `skill-author` document.

Heading lines ("#...") are never treated as a rule tag. Once a tag is found,
the "block" it must justify runs from that line up to (not including) the
next numbered list item or the next heading -- the same boundary a human
reads the rule by. A defect is a block with no `Why hard:` (case-insensitive)
anywhere in that range.

Verbs:
  check           human-readable report to stdout
  check --json    same findings, machine-readable

Run via: .venv/bin/python scripts/skill-doctrine-lint.py check
(No third-party imports -- unlike skill-lint.py this one never touches
YAML, so a bare `python3` on PATH works too.)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

_CURATOR_PATH = Path(__file__).resolve().parent / "skill-curator.py"

# See module docstring "Detection" for the exact contract these implement.
_HARD_TAG = re.compile(r"\*\*HARD\b(?=\s*[:—-])")
_WHY_HARD = re.compile(r"why\s+hard\s*:", re.IGNORECASE)
_NEW_RULE_BOUNDARY = re.compile(r"^\s{0,3}\d+[.)]\s")
_HEADING = re.compile(r"^#{1,6}\s")


@dataclass
class Finding:
    skill: str
    file: str
    line: int
    snippet: str


def _load_curator():
    """Import scripts/skill-curator.py by path, same pattern as skill-lint.py.

    Reused rather than duplicated so this tool and skill-lint.py never
    disagree about which entries under `.claude/skills/` are symlinks --
    neither ever follows one, even one pointing back inside the same dir.
    """
    spec = importlib.util.spec_from_file_location("_skill_curator_doctrine", _CURATOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover_skill_md_files(owned_dir: Path, curator) -> list[Path]:
    """SKILL.md paths for every owned (non-symlink) skill dir, sorted by name."""
    files: list[Path] = []
    if not owned_dir.is_dir():
        return files
    for child in sorted(owned_dir.iterdir(), key=lambda p: p.name):
        try:
            curator._resolve_within(child.name, owned_dir)
        except curator.CuratorError:
            continue  # symlink under .claude/skills/ -- never followed
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.is_file():
            files.append(skill_md)
    return files


def _rule_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) 0-indexed [start, end) ranges, one per HARD-tag hit.

    `end` is the next rule boundary after `start` (a new numbered list item
    or a heading), or len(lines) if the tag is the last rule in the file.
    """
    blocks: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        if _HEADING.match(line):
            continue
        if not _HARD_TAG.search(line):
            continue
        j = i + 1
        while j < len(lines) and not (_NEW_RULE_BOUNDARY.match(lines[j]) or _HEADING.match(lines[j])):
            j += 1
        blocks.append((i, j))
    return blocks


def lint_skill_md(skill_md: Path, skill_name: str) -> list[Finding]:
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    findings: list[Finding] = []
    for start, end in _rule_blocks(lines):
        block = lines[start:end]
        if any(_WHY_HARD.search(l) for l in block):
            continue
        snippet = lines[start].strip()
        if len(snippet) > 100:
            snippet = snippet[:97] + "..."
        try:
            file_display = str(skill_md.relative_to(ROOT))
        except ValueError:
            # Fixture/test paths (tmp_path, a copied fake repo) live outside
            # ROOT -- fall back to the absolute path rather than crashing.
            file_display = str(skill_md)
        findings.append(Finding(
            skill=skill_name,
            file=file_display,
            line=start + 1,
            snippet=snippet,
        ))
    return findings


def run_check(owned_dir: Optional[Path] = None) -> list[Finding]:
    curator = _load_curator()
    if owned_dir is None:
        owned_dir = curator.CuratorPaths.default().owned_skills_dir
    findings: list[Finding] = []
    for skill_md in discover_skill_md_files(owned_dir, curator):
        findings.extend(lint_skill_md(skill_md, skill_md.parent.name))
    return findings


def _print_human(findings: list[Finding]) -> None:
    if not findings:
        print("skill-doctrine-lint: clean -- 0 HARD blocks missing a reason.")
        return
    for f in findings:
        print(f"{f.file}:{f.line}: HARD block with no 'Why hard:' clause -- {f.snippet}")
    print(
        f"\n{len(findings)} defect(s). Threshold is zero, but this is a lint, not a "
        "gate -- it does not block authoring (ADR 0022 CEO decisions 4 and 10). "
        "Fix the ones that are real."
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skill-doctrine-lint.py",
        description=(
            "Hand-run doctrine lint: HARD rule blocks missing a Why hard: clause "
            "(ADR 0022 section 7). Lint only -- never blocks authoring."
        ),
    )
    parser.add_argument("verb", choices=["check"], help="check: scan every skill under .claude/skills/")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--skills-dir", type=Path, default=None,
        help="override the owned skills dir (tests only)",
    )
    args = parser.parse_args(argv)

    findings = run_check(owned_dir=args.skills_dir)

    if args.json:
        print(json.dumps({"findings": [asdict(f) for f in findings]}, indent=2))
    else:
        _print_human(findings)

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
