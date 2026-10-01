#!/usr/bin/env python3
"""scripts/flow-lint.py -- lint the flow.yaml beside every `kind: workflow` skill.

A Workflow skill carries two files: SKILL.md (the prose an agent reads) and
flow.yaml (the graph the Console's Flow board draws and the run events key
on). The contract, rules F1-F14 and the computed values (depth, effective
stage, auto %, cost per run) are written in
.claude/skills/ALL_Protocol_SkillAuthor/references/workflow-flow.md
(CEO ruling 2026-10-02: bind the Control Room to the Workflow skill).

`scripts/skill-lint.py` runs the per-skill rules as its code 18; this tool
adds what needs the whole corpus (F3: one flow id per workflow) or git
(`--base`: a node id that vanished without a `replaces:`), and `export`,
the reference implementation of the board's numbers.

**This is a lint, not a gate** -- the same ruling as skill-lint (ADR 0022
decisions 4 and 10): it never refuses a write and has no --strict mode.

Verbs:
  check [<skill> ...] [--json] [--base REV]   lint every workflow skill, or the named ones
  export <skill>                              the flow as JSON, with depth, order, stage and stats

Run via:  .venv/bin/python scripts/flow-lint.py check   (needs PyYAML)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENTS_YAML = ROOT / "policies" / "agents.yaml"

SCHEMA = "mooniex.flow/v1"
FLOW_FILE = "flow.yaml"
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A path in another repo: `claudeflow:pipelines/tts.py`. Not checked (F11).
FOREIGN_RE = re.compile(r"^[a-z][a-z0-9_-]+:(?!//)")
TZ_RE = re.compile(r"^(UTC|[A-Z][A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$")
WATCHER_RE = re.compile(r"^[A-Za-z_]+@[a-z0-9_-]+$")
STEP_RE = re.compile(r"^### Step (\d+) · (.+?)(?: \[node: ([^\]]*)\])?\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

TOP_KEYS = {"schema", "flow", "name", "skill", "owner", "goal", "output", "host",
            "trigger", "watcher", "budget", "phases", "nodes"}
NODE_KEYS = {"id", "name", "does", "phase", "kind", "after", "tool", "provider", "model",
             "role", "skill", "approver", "unit_cost", "output", "verify", "gate", "on_fail",
             "blockers", "stage", "graduate", "release", "replaces", "host", "expect_min",
             "measured"}
SUB_KEYS = {
    "trigger": {"kind", "by", "cron", "tz", "source"},
    "budget": {"cash_usd", "plan_usd_eq"},
    "phases": {"id", "name"},
    "unit_cost": {"usd", "per", "source", "date"},
    "verify": {"cmd", "check", "human"},
    "on_fail": {"retry", "retry_from", "max"},
    "graduate": {"candidate", "scorer", "bar"},
    "measured": {"date", "cost_usd", "turns", "minutes", "source"},
}
NODE_KINDS = ("code", "api", "model", "agent", "human")
REQUIRED_BY_KIND = {
    "code": ("tool",),
    "api": ("tool", "provider"),
    "model": ("tool", "provider"),
    "agent": ("role", "skill"),
    "human": ("approver",),
}
AGENT_STAGES = ("agent", "shadow", "auto_review")
TRIGGER_KINDS = ("manual", "cron", "queue", "event")
BLOCKERS_CEO = ("credit", "login", "key", "quota", "money", "account")
BLOCKERS_AGENT = ("bug", "verify_fail", "upstream", "input", "rate_limit")
VERIFY_KEYS = ("cmd", "check", "human")
LIMITS = {"flow_name": 40, "goal": 160, "node_name": 24, "does": 120}
SECRET_RES = [re.compile(p) for p in (
    r"sk-[A-Za-z0-9_-]{16,}", r"sk_live_[A-Za-z0-9]{8,}", r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"xox[abpr]-[A-Za-z0-9-]{10,}",
    r"AIza[0-9A-Za-z_-]{30,}", r"-----BEGIN [A-Z ]*PRIVATE KEY",
    r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s<{]{8,}",
)]


@dataclass
class Finding:
    skill: str
    rule: str
    message: str


# --- reading ---------------------------------------------------------------

def read_frontmatter(skill_md: Path) -> Optional[dict]:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def is_live_workflow(data: Optional[dict]) -> bool:
    """kind: workflow, not archived, not a redirect stub (skill-curator.py's test)."""
    if not data or str(data.get("kind", "")).strip().lower() != "workflow":
        return False
    if data.get("lifecycle") == "archived":
        return False
    desc = " ".join(str(data.get("description") or "").split())
    if data.get("disable-model-invocation") is True and desc.startswith("MOVED"):
        return False
    return True


def workflow_skills(skills_dir: Path = SKILLS_DIR) -> list[str]:
    if not skills_dir.is_dir():
        return []
    return [p.name for p in sorted(skills_dir.iterdir(), key=lambda p: p.name)
            if p.is_dir() and not p.is_symlink() and is_live_workflow(read_frontmatter(p / "SKILL.md"))]


def load_roles(agents_yaml: Path = AGENTS_YAML) -> set[str]:
    try:
        data = yaml.safe_load(agents_yaml.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    return {str(k).lower() for k in (data.get("roles") or {})}


def load_flow(skill_dir: Path) -> tuple[Optional[dict], Optional[str]]:
    path = skill_dir / FLOW_FILE
    if not path.is_file():
        return None, f"no {FLOW_FILE} beside SKILL.md -- every workflow carries one (references/workflow-flow.md)"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, f"{FLOW_FILE} does not parse: {exc}"
    if not isinstance(data, dict):
        return None, f"{FLOW_FILE} did not parse to a mapping"
    return data, None


def _nodes(flow: dict) -> list[dict]:
    raw = flow.get("nodes")
    return [n for n in raw if isinstance(n, dict)] if isinstance(raw, list) else []


def _after(node: dict) -> list[str]:
    a = node.get("after")
    if a is None:
        return []
    return [str(x) for x in a] if isinstance(a, list) else [str(a)]


# --- graph -----------------------------------------------------------------

def topo_order(nodes: list[dict]) -> tuple[list[str], set[str]]:
    """(order, ids on a cycle). Kahn's algorithm; ties keep the file's order.
    Unknown `after` ids are ignored here (F5 reports them)."""
    ids = [str(n.get("id")) for n in nodes]
    known = set(ids)
    indeg = {i: 0 for i in ids}
    children: dict[str, list[str]] = {i: [] for i in ids}
    for n in nodes:
        nid = str(n.get("id"))
        for a in _after(n):
            if a in known:
                indeg[nid] += 1
                children[a].append(nid)
    pos = {i: k for k, i in enumerate(ids)}
    ready = deque(sorted((i for i in ids if indeg[i] == 0), key=pos.get))
    order: list[str] = []
    while ready:
        cur = ready.popleft()
        order.append(cur)
        for c in sorted(children[cur], key=pos.get):
            indeg[c] -= 1
            if indeg[c] == 0:
                ready.append(c)
    return order, {i for i in ids if i not in order}


def ancestors(nodes: list[dict]) -> dict[str, set[str]]:
    parents = {str(n.get("id")): set(_after(n)) for n in nodes}
    memo: dict[str, set[str]] = {}

    def walk(i: str, seen: frozenset) -> set[str]:
        if i in memo:
            return memo[i]
        out: set[str] = set()
        for p in parents.get(i, ()):
            if p in seen or p not in parents:
                continue
            out |= {p} | walk(p, seen | {p})
        memo[i] = out
        return out

    return {i: walk(i, frozenset({i})) for i in parents}


def depths(nodes: list[dict], order: list[str]) -> dict[str, int]:
    parents = {str(n.get("id")): _after(n) for n in nodes}
    d: dict[str, int] = {}
    for i in order:
        ps = [d[p] for p in parents.get(i, []) if p in d]
        d[i] = 1 + max(ps) if ps else 0
    return d


def effective_stage(node: dict) -> str:
    kind = node.get("kind")
    if kind == "human":
        return "human"
    if kind == "agent":
        return str(node.get("stage") or "agent")
    return "auto"


def last_cost(node: dict) -> Optional[float]:
    m = node.get("measured")
    if not isinstance(m, list) or not m:
        return None
    last = m[-1]
    c = last.get("cost_usd") if isinstance(last, dict) else None
    return float(c) if isinstance(c, (int, float)) else None


# --- the rules -------------------------------------------------------------

def _strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for k, v in enumerate(obj):
            yield from _strings(v, f"{path}[{k}]")
    elif isinstance(obj, str):
        yield path, obj


def _path_exists(repo_root: Path, value) -> Optional[bool]:
    """True/False for a path in this repo; None for another repo's path."""
    s = str(value).split()[0] if str(value).split() else ""
    if not s or FOREIGN_RE.match(s):
        return None
    return (repo_root / s).exists()


def step_headings(skill_md_text: str) -> list[tuple[int, int, str, Optional[str]]]:
    """(line, n, name, node id or None) for each `### Step` heading outside fenced code."""
    out = []
    fenced = False
    for ln, line in enumerate(skill_md_text.splitlines(), 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced or not line.startswith("### Step "):
            continue
        m = STEP_RE.match(line)
        if m:
            out.append((ln, int(m.group(1)), m.group(2).strip(), (m.group(3) or "").strip() or None))
        else:
            out.append((ln, -1, line[len("### Step "):].strip(), None))
    return out


def lint_flow(
    name: str, skill_dir: Path, *, repo_root: Optional[Path] = None,
    skills_dir: Optional[Path] = None, roles: Optional[set[str]] = None,
    base: Optional[str] = None,
) -> list[Finding]:
    """Every per-skill rule (F1, F2, F4-F14) for one workflow skill. F3's
    uniqueness half needs the corpus and lives in check()."""
    skills_dir = skills_dir or skill_dir.parent
    repo_root = repo_root or skills_dir.parent.parent
    roles = load_roles() if roles is None else roles
    out: list[Finding] = []

    def f(rule: str, msg: str) -> None:
        out.append(Finding(name, rule, msg))

    flow, err = load_flow(skill_dir)
    if err:
        f("F1", err)
        return out
    if flow.get("skill") != name:
        f("F1", f"skill={flow.get('skill')!r} != the folder {name!r}")

    # F2 -- schema and keys
    if flow.get("schema") != SCHEMA:
        f("F2", f"schema={flow.get('schema')!r}, expected {SCHEMA!r}")
    for k in sorted(set(flow) - TOP_KEYS):
        f("F2", f"unknown top-level key {k!r}")
    for sub in ("trigger", "budget"):
        if isinstance(flow.get(sub), dict):
            for k in sorted(set(flow[sub]) - SUB_KEYS[sub]):
                f("F2", f"unknown key {sub}.{k}")
    phases = flow.get("phases") or []
    phase_ids = set()
    if isinstance(phases, list):
        for p in phases:
            if isinstance(p, dict):
                phase_ids.add(str(p.get("id")))
                for k in sorted(set(p) - SUB_KEYS["phases"]):
                    f("F2", f"unknown key phases[].{k}")
    nodes = _nodes(flow)
    if not nodes:
        f("F2", "no nodes -- `nodes:` is a list of mappings")
        return out
    for n in nodes:
        nid = n.get("id", "?")
        for k in sorted(set(n) - NODE_KEYS):
            f("F2", f"node {nid}: unknown key {k!r}")
        for sub in ("unit_cost", "verify", "on_fail", "graduate"):
            if isinstance(n.get(sub), dict):
                for k in sorted(set(n[sub]) - SUB_KEYS[sub]):
                    f("F2", f"node {nid}: unknown key {sub}.{k}")
        for m in n["measured"] if isinstance(n.get("measured"), list) else []:
            if isinstance(m, dict):
                for k in sorted(set(m) - SUB_KEYS["measured"]):
                    f("F2", f"node {nid}: unknown key measured[].{k}")

    # F3 -- the flow id's shape (uniqueness: check())
    if not ID_RE.match(str(flow.get("flow") or "")):
        f("F3", f"flow={flow.get('flow')!r} must match [a-z][a-z0-9_]*")

    # F4 -- node ids
    ids = [str(n.get("id")) for n in nodes]
    seen: set[str] = set()
    for i in ids:
        if not ID_RE.match(i):
            f("F4", f"node id {i!r} must match [a-z][a-z0-9_]*")
        if i in seen:
            f("F4", f"node id {i!r} is used twice")
        seen.add(i)
    replaced = set()
    for n in nodes:
        for r in n.get("replaces") or []:
            replaced.add(str(r))
            if str(r) in seen:
                f("F4", f"node {n.get('id')}: replaces {r!r}, which is still a live node")
    if base:
        old_ids = _ids_at(repo_root, skill_dir, base)
        for gone in sorted((old_ids or set()) - seen - replaced):
            f("F4", f"node {gone!r} existed at {base} and is gone -- run history keys on it; "
                    f"give its successor `replaces: [{gone}]`")

    # F5 -- the graph
    known = set(ids)
    for n in nodes:
        for a in _after(n):
            if a not in known:
                f("F5", f"node {n.get('id')}: after {a!r}, which is not a node")
    order, cyclic = topo_order(nodes)
    if cyclic:
        f("F5", f"cycle through {', '.join(sorted(cyclic))} -- loops are on_fail.retry_from, not edges")
    releases = {str(n.get("id")) for n in nodes if n.get("release") is True}
    if not releases:
        f("F5", "no node has `release: true` -- a workflow ends at a public release")
    anc = ancestors(nodes)
    if releases and not cyclic:
        reach = set(releases)
        for r in releases:
            reach |= anc.get(r, set())
        for i in ids:
            if i not in reach:
                f("F5", f"node {i}: no path to a release node (a dead end)")
    for n in nodes:
        of = n.get("on_fail")
        if isinstance(of, dict) and of.get("retry_from") is not None:
            rf = str(of["retry_from"])
            nid = str(n.get("id"))
            if rf != nid and rf not in anc.get(nid, set()):
                f("F5", f"node {nid}: on_fail.retry_from {rf!r} is not this node or one before it")

    # F6 -- kinds, required keys, phases, on_fail, blockers, owner, watcher
    skill_owner = (read_frontmatter(skill_dir / "SKILL.md") or {}).get("owner")
    if flow.get("owner") != skill_owner:
        f("F6", f"owner={flow.get('owner')!r} != the skill's owner: {skill_owner!r}")
    if not WATCHER_RE.match(str(flow.get("watcher") or "")):
        f("F6", f"watcher={flow.get('watcher')!r} must be <role>@<host> (CMO@contabo)")
    for n in nodes:
        nid = n.get("id")
        kind = n.get("kind")
        if kind not in NODE_KINDS:
            f("F6", f"node {nid}: kind={kind!r} is not one of {', '.join(NODE_KINDS)}")
        else:
            for k in REQUIRED_BY_KIND[kind]:
                if not n.get(k):
                    f("F6", f"node {nid}: a {kind} node needs `{k}`")
        if phase_ids and str(n.get("phase")) not in phase_ids:
            f("F6", f"node {nid}: phase={n.get('phase')!r} is not a declared phase")
        of = n.get("on_fail")
        if of is not None:
            if not isinstance(of, dict) or not ({"retry"} <= set(of) or {"retry_from"} <= set(of)):
                f("F6", f"node {nid}: on_fail is {{retry: n}} or {{retry_from: <id>, max: n}}")
        bl = n.get("blockers")
        if bl is not None:
            for b in bl if isinstance(bl, list) else [bl]:
                if b not in BLOCKERS_CEO + BLOCKERS_AGENT:
                    f("F6", f"node {nid}: blocker {b!r} is not a known code")

    # F7 -- verify
    for n in nodes:
        v = n.get("verify")
        keys = [k for k in VERIFY_KEYS if isinstance(v, dict) and str(v.get(k) or "").strip()]
        if len(keys) != 1:
            f("F7", f"node {n.get('id')}: verify needs exactly one of cmd | check | human")

    # F8 -- money
    paid = [n for n in nodes if n.get("kind") in ("api", "model")]
    budget = flow.get("budget") if isinstance(flow.get("budget"), dict) else {}
    if paid and not isinstance(budget.get("cash_usd"), (int, float)):
        f("F8", f"{len(paid)} api/model node(s) and no budget.cash_usd")

    # F9 -- trigger
    t = flow.get("trigger") if isinstance(flow.get("trigger"), dict) else {}
    tk = t.get("kind")
    if tk not in TRIGGER_KINDS:
        f("F9", f"trigger.kind={tk!r} is not one of {', '.join(TRIGGER_KINDS)}")
    elif tk == "cron":
        if len(str(t.get("cron") or "").split()) != 5:
            f("F9", "a cron trigger needs a 5-field `cron`")
        if not TZ_RE.match(str(t.get("tz") or "")):
            f("F9", f"a cron trigger needs an IANA `tz` (Asia/Bangkok), got {t.get('tz')!r}")
    elif tk == "manual" and not t.get("by"):
        f("F9", "a manual trigger needs `by` (who starts a run)")
    elif tk in ("queue", "event") and not t.get("source"):
        f("F9", f"a {tk} trigger needs `source`")

    # F10 -- stage and graduation
    for n in nodes:
        nid, kind, stage = n.get("id"), n.get("kind"), n.get("stage")
        if kind == "agent":
            if stage not in AGENT_STAGES:
                f("F10", f"node {nid}: an agent node's stage is one of {', '.join(AGENT_STAGES)}, got {stage!r}")
            elif stage != "agent":
                g = n.get("graduate") if isinstance(n.get("graduate"), dict) else {}
                for k in ("candidate", "scorer"):
                    if not g.get(k):
                        f("F10", f"node {nid}: stage {stage} needs graduate.{k} -- no scorer, no promotion")
        elif stage not in (None, "auto"):
            f("F10", f"node {nid}: a {kind} node is always auto; drop stage={stage!r}")

    # F11 -- paths, skills, roles
    for n in nodes:
        nid = n.get("id")
        g = n.get("graduate") if isinstance(n.get("graduate"), dict) else {}
        for label, val in (("tool", n.get("tool")), ("graduate.candidate", g.get("candidate")),
                           ("graduate.scorer", g.get("scorer"))):
            if val and _path_exists(repo_root, val) is False:
                f("F11", f"node {nid}: {label} {val!r} does not exist in this repo")
        sk = n.get("skill")
        if sk and not (skills_dir / str(sk) / "SKILL.md").is_file():
            f("F11", f"node {nid}: skill {sk!r} is not an org skill")
        if roles:
            if n.get("role") and str(n["role"]).lower() not in roles:
                f("F11", f"node {nid}: role {n['role']!r} is not in policies/agents.yaml")
            if n.get("approver") and str(n["approver"]).lower() not in roles:
                f("F11", f"node {nid}: approver {n['approver']!r} is neither CEO nor a role")

    # F12 -- the binding to SKILL.md
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        text = ""
    heads = step_headings(text)
    by_id = {str(n.get("id")): n for n in nodes}
    pos: dict[str, int] = {}
    prev_n = None
    for k, (ln, num, hname, hid) in enumerate(heads):
        if hid is None:
            f("F12", f"SKILL.md:{ln}: `### Step {hname}` has no `[node: <id>]` tag "
                     "(### Step <n> · <name> [node: <id>])")
            continue
        if hid not in by_id:
            f("F12", f"SKILL.md:{ln}: [node: {hid}] is not a node in {FLOW_FILE}")
            continue
        if hid in pos:
            f("F12", f"SKILL.md:{ln}: node {hid} has a second Step heading")
            continue
        pos[hid] = k
        if prev_n is not None and num != prev_n + 1:
            f("F12", f"SKILL.md:{ln}: Step {num} follows Step {prev_n} -- count up by one")
        prev_n = num
        if hname != by_id[hid].get("name"):
            f("F12", f"SKILL.md:{ln}: heading name {hname!r} != node {hid}'s name {by_id[hid].get('name')!r}")
    for i in ids:
        if i not in pos:
            f("F12", f"node {i} has no `### Step <n> · <name> [node: {i}]` in SKILL.md")
    for n in nodes:
        nid = str(n.get("id"))
        for a in _after(n):
            if nid in pos and a in pos and pos[a] > pos[nid]:
                f("F12", f"SKILL.md: Step for {nid} comes before the step for {a}, which it waits on")

    # F13 -- sizes
    def too_long(label, val, limit):
        if isinstance(val, str) and len(val) > limit:
            f("F13", f"{label} is {len(val)} chars (≤{limit})")
    too_long("name", flow.get("name"), LIMITS["flow_name"])
    too_long("goal", flow.get("goal"), LIMITS["goal"])
    for n in nodes:
        nid = n.get("id")
        too_long(f"node {nid}: name", n.get("name"), LIMITS["node_name"])
        too_long(f"node {nid}: does", n.get("does"), LIMITS["does"])
        if not str(n.get("does") or "").strip():
            f("F13", f"node {nid}: `does` is empty -- one sentence")
        elif "\n" in str(n.get("does")).strip():
            f("F13", f"node {nid}: `does` is one line")

    # F14 -- money carries a source, nothing looks like a secret
    for n in nodes:
        nid = n.get("id")
        entries = []
        if isinstance(n.get("unit_cost"), dict):
            entries.append(("unit_cost", n["unit_cost"]))
        if isinstance(n.get("measured"), list):
            entries += [(f"measured[{k}]", m) for k, m in enumerate(n["measured"])]
        for label, e in entries:
            if not isinstance(e, dict) or not e.get("source") or not DATE_RE.match(str(e.get("date") or "")):
                f("F14", f"node {nid}: {label} needs `source` and a YYYY-MM-DD `date`")
    for where, s in _strings(flow):
        if any(r.search(s) for r in SECRET_RES):
            f("F14", f"{where}: the value looks like a secret -- secrets live in Infisical, never here")

    return out


def _ids_at(repo_root: Path, skill_dir: Path, rev: str) -> Optional[set[str]]:
    try:
        rel = (skill_dir / FLOW_FILE).resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    try:
        raw = subprocess.run(["git", "-C", str(repo_root), "show", f"{rev}:{rel}"],
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
        data = yaml.safe_load(raw)
    except (subprocess.CalledProcessError, OSError, yaml.YAMLError):
        return None
    return {str(n.get("id")) for n in _nodes(data)} if isinstance(data, dict) else None


def check(
    names: Optional[list[str]] = None, *, skills_dir: Path = SKILLS_DIR,
    repo_root: Optional[Path] = None, agents_yaml: Path = AGENTS_YAML, base: Optional[str] = None,
) -> list[Finding]:
    repo_root = repo_root or skills_dir.parent.parent
    roles = load_roles(agents_yaml)
    every = workflow_skills(skills_dir)
    targets = names or every
    out: list[Finding] = []
    for name in targets:
        if name not in every:
            out.append(Finding(name, "F1", "not a live `kind: workflow` skill under .claude/skills"))
            continue
        out += lint_flow(name, skills_dir / name, repo_root=repo_root, skills_dir=skills_dir,
                         roles=roles, base=base)
    owners: dict[str, list[str]] = {}
    for name in every:
        flow, _err = load_flow(skills_dir / name)
        if flow and flow.get("flow"):
            owners.setdefault(str(flow["flow"]), []).append(name)
    for fid, skills in owners.items():
        if len(skills) > 1:
            for name in skills:
                if name in targets:
                    others = ", ".join(s for s in skills if s != name)
                    out.append(Finding(name, "F3", f"flow id {fid!r} is also used by {others}"))
    return out


def export(name: str, skills_dir: Path = SKILLS_DIR) -> dict:
    """The flow with the computed values of references/workflow-flow.md §9."""
    flow, err = load_flow(skills_dir / name)
    if err:
        raise SystemExit(f"{name}: {err}")
    nodes = _nodes(flow)
    order, cyclic = topo_order(nodes)
    if cyclic:
        raise SystemExit(f"{name}: cycle through {', '.join(sorted(cyclic))}")
    depth = depths(nodes, order)
    rank = {i: k for k, i in enumerate(order)}
    out_nodes = []
    for n in sorted(nodes, key=lambda n: rank[str(n.get("id"))]):
        nid = str(n.get("id"))
        out_nodes.append({**n, "order": rank[nid], "depth": depth[nid],
                          "effective_stage": effective_stage(n), "last_cost_usd": last_cost(n)})
    work = [n for n in out_nodes if n["effective_stage"] != "human"]
    auto = [n for n in work if n["effective_stage"] in ("auto", "auto_review")]
    costed = [n for n in out_nodes if n["last_cost_usd"] is not None]
    total = sum(n["last_cost_usd"] for n in costed)
    auto_cost = sum(n["last_cost_usd"] for n in costed if n["effective_stage"] in ("auto", "auto_review"))
    stats = {
        "nodes": len(out_nodes),
        "auto_pct_steps": round(100 * len(auto) / len(work), 1) if work else None,
        "cost_per_run_usd": round(total, 4) if costed else None,
        "auto_pct_cost": round(100 * auto_cost / total, 1) if total else None,
        "cost_unknown": [n["id"] for n in out_nodes if n["last_cost_usd"] is None and n["effective_stage"] != "human"],
    }
    edges = [[a, str(n.get("id"))] for n in nodes for a in _after(n)]
    header = {k: v for k, v in flow.items() if k != "nodes"}
    return {**header, "nodes": out_nodes, "edges": edges, "stats": stats}


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="flow-lint.py", description="Lint flow.yaml beside every workflow skill. "
                                "Lint only -- never blocks authoring.")
    sub = p.add_subparsers(dest="verb", required=True)
    c = sub.add_parser("check", help="lint every workflow skill, or the named ones")
    c.add_argument("skills", nargs="*")
    c.add_argument("--json", action="store_true")
    c.add_argument("--base", help="a git rev: report node ids that vanished since it (F4)")
    c.add_argument("--skills-dir", type=Path, default=SKILLS_DIR, help="override (tests only)")
    e = sub.add_parser("export", help="the flow as JSON with depth, order, stage and stats")
    e.add_argument("skill")
    e.add_argument("--skills-dir", type=Path, default=SKILLS_DIR, help="override (tests only)")
    args = p.parse_args(argv)

    if args.verb == "export":
        print(json.dumps(export(args.skill, args.skills_dir), indent=2, ensure_ascii=False, default=str))
        return 0
    findings = check(args.skills or None, skills_dir=args.skills_dir, base=args.base)
    if args.json:
        print(json.dumps({"findings": [asdict(x) for x in findings]}, indent=2, ensure_ascii=False))
    elif not findings:
        print("flow-lint: clean -- no findings.")
    else:
        for x in findings:
            print(f"[{x.rule}] {x.skill}: {x.message}")
        print(f"\n{len(findings)} finding(s). A lint, not a gate -- it does not block authoring.")
    return 1 if findings else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
