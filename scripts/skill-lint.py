#!/usr/bin/env python3
"""scripts/skill-lint.py -- frontmatter lint for org-authored skills (ADR 0022 Wave 1).

Checks every skill under `.claude/skills/` against the Wave 1 frontmatter
contract (ADR 0022 section 3: `audience`, `created_by`, `author`,
`improved_by`, `aka`) plus the Wave 2 lifecycle keys (ADR 0022 section 4.3:
`pinned`, `lifecycle`, `archived_at` — moved out of the deleted
state/skill-usage.json sidecar into each skill's own frontmatter), the
ADR 0026 learning loop (8-10) and the skill naming contract the CEO approved
on 2026-09-27 and guarded on 2026-09-28 (11-16, "Ok ลุย"), and the
flow.yaml contract of a Workflow skill (18, CEO 2026-10-02). Eighteen
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
 11. org skill without `kind:`, or a kind that is not one of the seven
 12. name is not `<ROLE>_<Kind>_<Topic>`, or its Kind segment != `kind:`
     (case-insensitive); the commands the CEO types are exempt from 12 only
 13. `owner:` missing or not a C-level
 14. description does not start with the kind word in capitals + ` — `
 15. a redirect stub whose "removed after YYYY-MM-DD" date has passed
 16. docs/org/SKILL-INDEX.md differs from a fresh `skill-curator.py index`
     render (one finding for the file, not one per skill)
 17. more than one `## Field notes` heading outside fenced code -- code 8 and
     `skill-curator.py notes` read only the first, so the rest are invisible
     (CXO_Protocol_DevSpawn hid 32 pending notes that way, 2026-09-28)
 18. a live `kind: workflow` skill whose flow.yaml breaks a rule F1-F14 of
     ALL_Protocol_SkillAuthor/references/workflow-flow.md -- one finding per
     rule hit, the rule named first; run by scripts/flow-lint.py, which also
     holds the corpus check (F3, one flow id per workflow) and `--base`

Codes 11-14 skip imported public skills, redirect stubs
(`disable-model-invocation: true` + a description starting `MOVED`) and
`lifecycle: archived`; code 15 looks only at the stubs. The lists (seven
kinds, C-levels, imported skills, CEO commands) live in
config/skill-kinds.yaml, the procedure in
.claude/skills/ALL_Protocol_SkillAuthor/SKILL.md.

`archived_at` is not format-checked — it is a free-form timestamp stamped
by skill-curator.py itself, never hand-typed.

Role tokens are derived at runtime from `policies/agents.yaml` -- never
hardcoded, so this does not drift when a role is added or removed. The
same goes for the worker ROLE prefixes code 12 accepts (BROWSER_OPERATOR,
VIDEO_EDITOR, ...): every runnable level-w role, in capitals.

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
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_YAML = ROOT / "policies" / "agents.yaml"
KINDS_YAML = ROOT / "config" / "skill-kinds.yaml"
INDEX_MD = ROOT / "docs" / "org" / "SKILL-INDEX.md"

_CURATOR_PATH = Path(__file__).resolve().parent / "skill-curator.py"
_FLOW_LINT_PATH = Path(__file__).resolve().parent / "flow-lint.py"

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
    11: "bad-kind",
    12: "bad-name",
    13: "bad-owner",
    14: "description-kind-prefix",
    15: "stub-expired",
    16: "index-stale",
    17: "duplicate-field-notes-heading",
    18: "workflow-flow",
}

# The ROLE that means everyone, workers included -- part of the naming grammar
# itself (ALL_Protocol_SkillAuthor §2), like the `_` separator.
EVERYONE_ROLE = "ALL"
# One `_`-separated word of a Topic: starts with a capital or a digit; an
# engine keeps its version (`Omni1.1`, `Seedance2.5`, `Wan3.0`).
_TOPIC_WORD_RE = re.compile(r"^[A-Z0-9][A-Za-z0-9.]*$")

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


_FLOW = None


def _flow():
    """scripts/flow-lint.py, loaded once -- code 18 is its per-skill rules, so
    `flow-lint.py check` and this lint can never disagree about a flow.yaml."""
    global _FLOW
    if _FLOW is None:
        spec = importlib.util.spec_from_file_location("_flow_lint", _FLOW_LINT_PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _FLOW = mod
    return _FLOW


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


# --- the naming contract: codes 11-16 (CEO 2026-09-27, guarded 2026-09-28) ---

@dataclass(frozen=True)
class NamingRules:
    kinds: object   # skill-curator.py SkillKinds: kinds, c_levels, imported, ceo_commands
    roles: tuple    # every valid ROLE prefix, longest first so BROWSER_OPERATOR wins over a shorter match


def load_naming_rules(kinds_yaml: Path = KINDS_YAML, agents_yaml: Path = AGENTS_YAML) -> NamingRules:
    """config/skill-kinds.yaml + the worker roles of policies/agents.yaml.
    ROLE = ALL, a C-level, or a runnable level-w role in capitals -- derived,
    so a worker role added tomorrow is a valid prefix without an edit here."""
    kinds = _cur().load_skill_kinds(kinds_yaml)
    _all, _cxo, workers = load_role_groups(agents_yaml)
    roles = {EVERYONE_ROLE} | set(kinds.c_levels) | {w.upper() for w in workers}
    return NamingRules(kinds=kinds, roles=tuple(sorted(roles, key=lambda r: (-len(r), r))))


def split_name(name: str, roles: tuple) -> Optional[tuple[str, str, str]]:
    """(ROLE, Kind, Topic) of `<ROLE>_<Kind>_<Topic>`, or None when no known ROLE
    prefixes the name. Kind / Topic come back empty when missing."""
    for role in roles:
        if name.startswith(role + "_"):
            kind, _sep, topic = name[len(role) + 1:].partition("_")
            return role, kind, topic
    return None


def kind_findings(name: str, data: dict, rules: NamingRules, today: Optional[date] = None) -> list[Finding]:
    """Codes 11-15 for one skill whose frontmatter parsed."""
    cur = _cur()
    sk = rules.kinds
    if name in sk.imported or cur.is_archived(data):
        return []
    if cur.is_redirect_stub(data):
        removal = cur.stub_removal_date(data)
        if removal is None:
            return []
        try:
            removal_day = datetime.strptime(removal, "%Y-%m-%d").date()
        except ValueError:
            return []
        if (today or date.today()) > removal_day:
            return [Finding(
                name, 15, CODES[15],
                f"stub expired, delete it -- its removal date {removal} has passed "
                f"(`python scripts/skill-curator.py archive {name}`, ALL_Protocol_SkillAuthor §7; "
                "first sweep live files that still name it)",
            )]
        return []

    findings: list[Finding] = []
    seven = "|".join(sk.kinds)
    raw_kind = data.get("kind")
    kind = raw_kind.strip().lower() if isinstance(raw_kind, str) else None
    valid_kind = kind in sk.kinds
    if raw_kind is None:
        findings.append(Finding(name, 11, CODES[11], f"no `kind:` -- every org skill has exactly one of {seven}"))
    elif not valid_kind:
        findings.append(Finding(name, 11, CODES[11], f"kind={raw_kind!r} is not one of {seven}"))

    if name not in sk.ceo_commands:
        parts = split_name(name, rules.roles)
        if parts is None:
            findings.append(Finding(
                name, 12, CODES[12],
                f"name {name!r} is not <ROLE>_<Kind>_<Topic> -- ROLE is one of {', '.join(sorted(rules.roles))}",
            ))
        else:
            role, kind_seg, topic = parts
            if kind_seg.lower() not in sk.kinds:
                findings.append(Finding(
                    name, 12, CODES[12],
                    f"name {name!r}: segment after {role}_ is {kind_seg!r}, not one of the seven kinds "
                    f"({', '.join(k.capitalize() for k in sk.kinds)})",
                ))
            elif valid_kind and kind_seg.lower() != kind:
                findings.append(Finding(
                    name, 12, CODES[12],
                    f"name {name!r}: Kind segment {kind_seg!r} != kind: {kind}",
                ))
            if not topic or not all(_TOPIC_WORD_RE.match(w) for w in topic.split("_")):
                findings.append(Finding(
                    name, 12, CODES[12],
                    f"name {name!r}: Topic {topic!r} must be words that start with a capital or a digit, "
                    "joined by `_` (e.g. Seedance2.5_Higgsfield)",
                ))

    owner = data.get("owner")
    if owner not in sk.c_levels:
        what = "no `owner:`" if owner is None else f"owner={owner!r} is not a C-level"
        findings.append(Finding(name, 13, CODES[13], f"{what} -- one of {', '.join(sk.c_levels)}"))

    desc = cur.one_line(data.get("description"))
    words = [kind.upper()] if valid_kind else [k.upper() for k in sk.kinds]
    if not any(desc.startswith(w + " — ") for w in words):
        want = f"`{words[0]} — `" if valid_kind else "the kind word in capitals + ` — `"
        findings.append(Finding(
            name, 14, CODES[14],
            f"description must start with {want} (starts {desc[:30]!r})",
        ))
    return findings


def index_finding(owned_dir: Path, index_path: Path, rules: NamingRules) -> Optional[Finding]:
    """Code 16: the committed docs/org/SKILL-INDEX.md vs a fresh render of the
    same skills -- one finding for the file, never one per skill."""
    fresh = _cur().render_skill_index(owned_dir, rules.kinds)
    try:
        current = index_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        current = None
    if current == fresh:
        return None
    state = "stale (missing)" if current is None else "stale"
    return Finding(
        "SKILL-INDEX.md", 16, CODES[16],
        f"SKILL-INDEX.md is {state} — run skill-curator.py index "
        "(`.venv/bin/python scripts/skill-curator.py index`) and commit docs/org/SKILL-INDEX.md",
    )


def lint_skill(
    name: str, skill_dir: Path, known_audience: set[str], *, staged: bool = False,
    rules: Optional[NamingRules] = None, today: Optional[date] = None,
) -> list[Finding]:
    """Codes 1-10 always; codes 11-15 and 18 only when `rules` is given
    (run_check loads them from config/skill-kinds.yaml)."""
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
    headings = _cur().field_notes_headings(skill_md.read_text(encoding="utf-8"))
    if len(headings) > 1:
        findings.append(Finding(
            name, 17, CODES[17],
            f"more than one `## Field notes` heading (SKILL.md lines {', '.join(map(str, headings))}) "
            "— merge them, the tools read only the first",
        ))
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

    if rules is not None:
        findings.extend(kind_findings(name, data, rules, today))
        if name not in rules.kinds.imported and _flow().is_live_workflow(data):
            findings.extend(
                Finding(name, 18, CODES[18], f"{f.rule}: {f.message}")
                for f in _flow().lint_flow(name, skill_dir)
            )

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


_UNSET = object()


def run_check(
    owned_dir: Optional[Path] = None, agents_yaml: Path = AGENTS_YAML,
    staged: bool = False, kinds_yaml: Optional[Path] = KINDS_YAML,
    index_path=_UNSET, today: Optional[date] = None,
) -> tuple[list[Finding], list[str]]:
    """Lint every skill under `owned_dir` (default: this repo's .claude/skills).

    Codes 11-15 run whenever `kinds_yaml` exists (None or a missing file turns
    them off -- a checkout that predates the config). Code 16 compares
    `index_path` with a fresh render; by default that is docs/org/SKILL-INDEX.md
    for the real corpus and nothing for an overridden `owned_dir` (a fixture
    dir has no committed index to be stale against)."""
    curator = _load_curator()
    real_corpus = owned_dir is None
    if owned_dir is None:
        owned_dir = curator.CuratorPaths.default().owned_skills_dir
    if index_path is _UNSET:
        index_path = INDEX_MD if real_corpus else None
    rules = load_naming_rules(kinds_yaml, agents_yaml) if kinds_yaml is not None and kinds_yaml.is_file() else None
    known_audience = _known_audience_tokens(agents_yaml)
    names, refused = discover_skills(owned_dir, curator)
    findings: list[Finding] = []
    for name in names:
        findings.extend(lint_skill(name, owned_dir / name, known_audience, staged=staged, rules=rules, today=today))
    if rules is not None and index_path is not None:
        stale = index_finding(owned_dir, index_path, rules)
        if stale is not None:
            findings.append(stale)
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
