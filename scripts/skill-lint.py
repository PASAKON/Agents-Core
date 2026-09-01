#!/usr/bin/env python3
"""scripts/skill-lint.py -- frontmatter lint for org-authored skills (ADR 0022 Wave 1).

Checks every skill under `.claude/skills/` against the Wave 1 frontmatter
contract (ADR 0022 section 3): `audience`, `created_by`, `author`,
`improved_by`, `aka`. Five finding codes:

  1. missing SKILL.md
  2. unparseable frontmatter
  3. `name` != directory basename
  4. `created_by` outside {human, agent}
  5. `audience` token not a known role or group (all|cxo|worker)

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


def lint_skill(name: str, skill_dir: Path, known_audience: set[str]) -> list[Finding]:
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
    owned_dir: Optional[Path] = None, agents_yaml: Path = AGENTS_YAML
) -> tuple[list[Finding], list[str]]:
    curator = _load_curator()
    if owned_dir is None:
        owned_dir = curator.CuratorPaths.default().owned_skills_dir
    known_audience = _known_audience_tokens(agents_yaml)
    names, refused = discover_skills(owned_dir, curator)
    findings: list[Finding] = []
    for name in names:
        findings.extend(lint_skill(name, owned_dir / name, known_audience))
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
        "--skills-dir", type=Path, default=None,
        help="override the owned skills dir (tests only)",
    )
    args = parser.parse_args(argv)

    findings, refused = run_check(owned_dir=args.skills_dir)

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
