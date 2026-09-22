#!/usr/bin/env python3
"""scripts/skill-lint.py -- frontmatter lint for org-authored skills (ADR 0022 Wave 1).

Checks every skill under `.claude/skills/` against the Wave 1 frontmatter
contract (ADR 0022 section 3: `audience`, `created_by`, `author`,
`improved_by`, `aka`) plus the Wave 2 lifecycle keys (ADR 0022 section 4.3:
`pinned`, `lifecycle`, `archived_at` — moved out of the deleted
state/skill-usage.json sidecar into each skill's own frontmatter). Seven
finding codes:

  1. missing SKILL.md
  2. unparseable frontmatter
  3. `name` != directory basename
  4. `created_by` outside {human, agent}
  5. `audience` token not a known role or group (all|cxo|worker)
  6. `pinned` present but not a boolean
  7. `lifecycle` present but not "active" or "archived"
  8. a `## Field notes` bullet is malformed (ADR 0026: date, [KIND], evidence, status)
  9. `--staged` only: the rule body changed but no Field note was added in the same diff
 10. ≥2 `skill(<name>): flip` commits on one skill inside 30 days — CONTESTED, CEO rules

`archived_at` is not format-checked — it is a free-form timestamp stamped
by skill-curator.py itself, never hand-typed.

Role tokens are derived at runtime from `policies/agents.yaml` -- never
hardcoded, so this does not drift when a role is added or removed.

**This is a lint, not a gate.** Exit non-zero on findings is fine (that's
what makes `check` useful standalone and in CI); it must never refuse to
write a skill, and it must never grow a `--strict` mode another tool could
gate on (CEO decisions 4 and 10 in ADR 0022 -- no approval gate, in any
form). The pre-commit wiring in `scripts/install-git-hooks.sh` calls this
tool and ignores its exit code for exactly that reason.

Reuses `scripts/skill-curator.py`'s `_resolve_within()` / `CuratorError` for
the symlink refusal rather than reimplementing it, so the two tools agree:
neither ever looks inside a symlink under `.claude/skills/`, even one that
points back inside the same directory.

Verbs:
  check           human-readable report to stdout
  check --json    same findings, machine-readable

Run via:  python scripts/skill-lint.py check
Or:       .venv/bin/python scripts/skill-lint.py check   (needs PyYAML --
          bare `python3` on PATH has none, see scripts/install-git-hooks.sh)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_YAML = ROOT / "policies" / "agents.yaml"

_CURATOR_PATH = Path(__file__).resolve().parent / "skill-curator.py"

CODES = {
    1: "missing-skill-md",
    2: "unparseable-frontmatter",
    3: "name-mismatch",
    4: "bad-created-by",
    5: "unknown-audience",
    6: "bad-pinned",
    7: "bad-lifecycle",
    8: "field-note-malformed",
    9: "body-edit-without-field-note",
    10: "contested-rule",
}

# The two additional group tokens `audience:` may use besides a real role key.
# "all" is added at read time from the roles derived below.
_EXTRA_GROUPS = ("cxo", "worker")


def _load_curator():
    """Import scripts/skill-curator.py by path (hyphenated filename, no `import`).

    Reused rather than duplicated: `_resolve_within` / `CuratorError` are the
    single place the symlink-refusal invariant lives. Duplicating it here
    would let the two tools quietly disagree the next time one is edited.
    """
    spec = importlib.util.spec_from_file_location("_skill_curator", _CURATOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_CUR = None


def _cur():
    """The curator module, loaded once — `parse_field_notes` / `flip_commits_for`
    live there so `skill-curator.py notes` and this lint can never disagree
    about what a well-formed note is."""
    global _CUR
    if _CUR is None:
        _CUR = _load_curator()
    return _CUR


def _git_out(cwd: Path, *args: str) -> Optional[str]:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _frontmatter_end(lines: list[str]) -> int:
    """1-based line number of the closing `---`, or 0 when there is no frontmatter."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return 0


def staged_body_edit_without_note(skill_md: Path) -> Optional[str]:
    """Code 9. Looks at the STAGED version of SKILL.md: a hunk that touches the
    rule body (after the frontmatter, before `## Field notes`) with no `+` line
    landing in the Field notes section = a learning written straight into the
    manual with nothing to show for it. A brand-new skill is exempt (nothing to
    fold yet); a frontmatter-only edit (curator pin/archive) is exempt. Returns
    the finding message, or None. Not a repo / nothing staged → None."""
    top = _git_out(skill_md.parent, "rev-parse", "--show-toplevel")
    if top is None:
        return None
    # Every git call below runs from the repo ROOT with a root-relative
    # pathspec. A pathspec is cwd-relative: run from the skill dir it silently
    # matches nothing, the diff comes back empty, and this check can never
    # fire (the first cut of this function did exactly that, 2026-09-22).
    root = Path(top.strip()).resolve()
    rel = skill_md.resolve().relative_to(root).as_posix()
    added = _git_out(root, "diff", "--cached", "--name-only", "--diff-filter=A", "--", rel)
    if added and added.strip():
        return None
    diff = _git_out(root, "diff", "--cached", "-U0", "--", rel)
    if not diff or not diff.strip():
        return None
    staged = _git_out(root, "show", f":{rel}")
    if staged is None:
        return None
    lines = staged.splitlines()
    fm_end = _frontmatter_end(lines)
    notes_start, _ = _cur().field_notes_section(staged)
    if not notes_start:
        notes_start = len(lines) + 1
    body_changed = False
    note_added = False
    start = end = 0
    for line in diff.splitlines():
        if line.startswith("@@"):
            hm = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if not hm:
                continue
            start = int(hm.group(1))
            count = int(hm.group(2)) if hm.group(2) is not None else 1
            end = start + max(count, 1) - 1
            if start <= notes_start - 1 and end >= fm_end + 1:
                body_changed = True
            continue
        if line.startswith("+") and not line.startswith("+++") and start and end >= notes_start:
            note_added = True
    if body_changed and not note_added:
        return (
            "staged diff changes the rule body but adds no `## Field notes` line "
            "-- a learning goes in as a note first (ADR 0026); a rule change carries "
            "its evidence as a note in the same commit"
        )
    return None


@dataclass
class Finding:
    skill: str
    code: int
    code_name: str
    message: str


def load_role_groups(agents_yaml: Path = AGENTS_YAML) -> tuple[set[str], set[str], set[str]]:
    """Derive (all_tokens, cxo_tokens, worker_tokens) from policies/agents.yaml.

    A role only counts as a valid `audience:` token if it can actually run a
    Claude session -- `model` is not null. CEO's `model` is null ("the user --
    no LLM"), so CEO is `level: c` but is excluded from every group here, the
    same way ADR 0022 skills that name their C-level audience explicitly
    (`session-change-model`, `higgsfield-unlimited-gen`) list CTO/CFO/CGO/CMO
    and never CEO. This is a property test (has a model), not a hardcoded
    exclusion of the name "ceo" -- it holds for any future role shaped the
    same way.
    """
    data = yaml.safe_load(agents_yaml.read_text(encoding="utf-8")) or {}
    roles = data.get("roles", {}) or {}
    runnable = {
        key: cfg for key, cfg in roles.items()
        if isinstance(cfg, dict) and cfg.get("model") is not None
    }
    all_tokens = set(runnable.keys())
    cxo_tokens = {k for k, cfg in runnable.items() if cfg.get("level") == "c"}
    worker_tokens = {k for k, cfg in runnable.items() if cfg.get("level") == "w"}
    return all_tokens, cxo_tokens, worker_tokens


def _known_audience_tokens(agents_yaml: Path = AGENTS_YAML) -> set[str]:
    all_tokens, _cxo, _worker = load_role_groups(agents_yaml)
    return all_tokens | {"all"} | set(_EXTRA_GROUPS)


def _parse_frontmatter(skill_md: Path) -> tuple[Optional[dict], Optional[str]]:
    """(data, error) -- data is None iff error is set.

    Deliberately does NOT swallow a YAML error into `{}` the way
    `skill-curator.py:_read_frontmatter` does (that fits the curator's
    fail-closed default; it would hide the "unparseable frontmatter" finding
    a lint exists to surface).
    """
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, "no frontmatter block (file does not start with '---')"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "no closing '---' for frontmatter block"
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter did not parse to a mapping"
    return data, None


def lint_skill(name: str, skill_dir: Path, known_audience: set[str], *, staged: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        findings.append(Finding(name, 1, CODES[1], f"{skill_md} does not exist"))
        return findings

    data, err = _parse_frontmatter(skill_md)
    if err is not None:
        findings.append(Finding(name, 2, CODES[2], f"{skill_md}: {err}"))
        return findings

    fm_name = data.get("name")
    if fm_name != name:
        findings.append(Finding(
            name, 3, CODES[3],
            f"frontmatter name={fm_name!r} != directory basename {name!r}",
        ))

    if "created_by" in data:
        cb = data.get("created_by")
        if cb not in ("human", "agent"):
            findings.append(Finding(
                name, 4, CODES[4],
                f"created_by={cb!r} is not 'human' or 'agent' "
                "(a role belongs in author:, never here -- ADR 0022 section 3)",
            ))

    if "audience" in data:
        aud = data.get("audience")
        tokens = aud if isinstance(aud, list) else [aud]
        for tok in tokens:
            if tok not in known_audience:
                findings.append(Finding(
                    name, 5, CODES[5],
                    f"audience token {tok!r} is not a known role or group "
                    f"(known: {', '.join(sorted(known_audience))})",
                ))

    if "pinned" in data and not isinstance(data.get("pinned"), bool):
        findings.append(Finding(
            name, 6, CODES[6],
            f"pinned={data.get('pinned')!r} is not a boolean (true/false)",
        ))

    if "lifecycle" in data:
        lc = data.get("lifecycle")
        if lc not in ("active", "archived"):
            findings.append(Finding(
                name, 7, CODES[7],
                f"lifecycle={lc!r} is not 'active' or 'archived'",
            ))

    # --- ADR 0026: the learning loop's field notes -------------------------
    for note in _cur().parse_field_notes(name, skill_md.read_text(encoding="utf-8")):
        if note.problems:
            findings.append(Finding(
                name, 8, CODES[8],
                f"SKILL.md:{note.line_no}: {'; '.join(note.problems)} "
                "(canonical: `- YYYY-MM-DD [WRONG|MISSING|COSTLY|SUPERSEDED] <what> "
                "· evidence: <task-id / sha / path> · status: pending`)",
            ))
    if staged:
        msg = staged_body_edit_without_note(skill_md)
        if msg:
            findings.append(Finding(name, 9, CODES[9], msg))
    flips = _cur().flip_commits_for(skill_md)
    if flips is not None and len(flips) >= _cur().FLIP_CONTESTED_AT:
        findings.append(Finding(
            name, 10, CODES[10],
            f"{len(flips)} `skill({name}): flip` commits in the last {_cur().FLIP_WINDOW_DAYS} days "
            "-- CONTESTED: the rule is frozen until the CEO rules (ADR 0026 section 3)",
        ))

    return findings


def discover_skills(owned_dir: Path, curator) -> tuple[list[str], list[str]]:
    """(names, refused). `refused` holds any entry directly under `owned_dir`
    that is itself a symlink -- consistent with the curator's invariant 3,
    which refuses ANY symlink there, not only one that escapes the dir.
    """
    names: list[str] = []
    refused: list[str] = []
    if not owned_dir.is_dir():
        return names, refused
    for child in sorted(owned_dir.iterdir(), key=lambda p: p.name):
        try:
            curator._resolve_within(child.name, owned_dir)
        except curator.CuratorError as exc:
            refused.append(f"{child.name}: {exc}")
            continue
        if child.is_dir():
            names.append(child.name)
    return names, refused


def run_check(
    owned_dir: Optional[Path] = None, agents_yaml: Path = AGENTS_YAML,
    staged: bool = False,
) -> tuple[list[Finding], list[str]]:
    curator = _load_curator()
    if owned_dir is None:
        owned_dir = curator.CuratorPaths.default().owned_skills_dir
    known_audience = _known_audience_tokens(agents_yaml)
    names, refused = discover_skills(owned_dir, curator)
    findings: list[Finding] = []
    for name in names:
        findings.extend(lint_skill(name, owned_dir / name, known_audience, staged=staged))
    return findings, refused


def _print_human(findings: list[Finding], refused: list[str]) -> None:
    if not findings and not refused:
        print("skill-lint: clean -- no findings.")
        return
    for f in findings:
        print(f"[{f.code}] {f.code_name}: {f.skill}: {f.message}")
    for r in refused:
        print(f"[refused] {r} (symlink under .claude/skills/ -- never followed, consistent with skill-curator.py invariant 3)")
    if findings:
        print(
            f"\n{len(findings)} finding(s), {len(refused)} refused entr"
            f"{'y' if len(refused) == 1 else 'ies'}. This is a lint, not a gate "
            "-- it does not block authoring."
        )
    else:
        print(
            f"\n0 findings -- clean. {len(refused)} refused entr"
            f"{'y' if len(refused) == 1 else 'ies'} (informational; a symlink "
            "was never an owned skill to begin with, same as skill-curator.py's "
            "own scan)."
        )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skill-lint.py",
        description="Frontmatter lint for org-authored skills (ADR 0022 Wave 1). "
        "Lint only -- never blocks authoring.",
    )
    parser.add_argument("verb", choices=["check"], help="check: lint every skill under .claude/skills/")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--staged", action="store_true",
        help="also run code 9 against the staged diff (pre-commit wiring passes this)",
    )
    parser.add_argument(
        "--skills-dir", type=Path, default=None,
        help="override the owned skills dir (tests only)",
    )
    args = parser.parse_args(argv)

    findings, refused = run_check(owned_dir=args.skills_dir, staged=args.staged)

    if args.json:
        print(json.dumps({
            "findings": [asdict(f) for f in findings],
            "refused": refused,
        }, indent=2))
    else:
        _print_human(findings, refused)

    # Exit status reflects contract findings only. A refused (symlinked)
    # entry is informational -- it was never an owned skill to begin with,
    # the same way skill-curator.py's own status/propose scan silently
    # excludes symlinks rather than treating them as a lifecycle problem.
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
