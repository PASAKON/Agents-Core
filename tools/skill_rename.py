"""Rename org skills in one phase, the way `skill-author` §6 says: move the directory, patch the frontmatter
(name, kind, owner, aka, audience, the kind word first in the description), repoint every live reference,
and leave a redirect stub at the old name for 30 days. Nothing is committed: lint, run the suite, then commit.

    python tools/skill_rename.py PLAN.json            dry run: what would move and which files would change
    python tools/skill_rename.py PLAN.json --apply    do it

PLAN.json is a list of {"old", "new", "kind", "owner", "audience_add": [..]}. Built 2026-09-27 for the CEO's
approved rename phases (docs/org/SKILL-KINDS-2026-09-27.md, "Rename plan").

Live references are rewritten in the directories below; dated history (reports, ops letters, research, state)
keeps the old names, and the stub answers for them. A name matches only as a whole token, so
`CMO_Knowledge_Film_Production` never touches `CMO_Standard_Film_PromptFormat`. Files in KEEP_OLD_NAMES record the mapping itself
and are never rewritten.
"""
import argparse, datetime, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
KINDS = {"rules", "knowledge", "workflow", "procedure", "standard", "gate", "protocol"}
INCLUDE = [".claude/skills", ".claude/skills-archive", "roles", "scripts", "tools", "runners", "lib", "config",
           "policies", "claude-home", "tests", "CLAUDE.md", "docs"]
EXCLUDE_PARTS = {".git", "node_modules", "worktrees", "__pycache__"}
EXCLUDE_PREFIX = ("docs/reports", "docs/ops", "docs/research")
KEEP_OLD_NAMES = {"docs/org/SKILL-KINDS-2026-09-27.md"}
TEXT_SUFFIX = {".md", ".py", ".sh", ".js", ".mjs", ".ts", ".json", ".yaml", ".yml", ".txt", ".toml", ".cmd", ""}
NAME_RE = re.compile(r"^(CTO|CMO|CGO|CFO|COO|CXO|ALL|[A-Z]+(?:_[A-Z]+)*)_"
                     r"(Rules|Knowledge|Workflow|Procedure|Standard|Gate|Protocol)_[A-Za-z0-9.]+(?:_[A-Za-z0-9.]+)*$")


def token_re(name):
    return re.compile(r"(?<![A-Za-z0-9_.\-])" + re.escape(name) + r"(?![A-Za-z0-9_\-])")


def live_files():
    for inc in INCLUDE:
        base = ROOT / inc
        paths = [base] if base.is_file() else (base.rglob("*") if base.is_dir() else [])
        for p in paths:
            if not p.is_file() or p.is_symlink() or p.suffix not in TEXT_SUFFIX:
                continue
            rel = p.relative_to(ROOT).as_posix()
            if EXCLUDE_PARTS & set(p.relative_to(ROOT).parts) or rel.startswith(EXCLUDE_PREFIX) \
                    or rel in KEEP_OLD_NAMES or ".launch-task" in rel:
                continue
            yield p


def read(p):
    if p.stat().st_size > 5_000_000:
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def patch_frontmatter(text, e):
    if not text.startswith("---"):
        raise SystemExit(f"STOP: {e['new']}: no frontmatter")
    end = text.index("\n---", 3)
    fm, body = text[:end], text[end:]
    lines = fm.split("\n")

    def find(key):
        return next((i for i, l in enumerate(lines) if l.startswith(key + ":")), None)

    lines[find("name")] = f"name: {e['new']}"
    at = find("name") + 1
    if find("kind") is None:
        lines.insert(at, f"kind: {e['kind']}")
    else:
        lines[find("kind")] = f"kind: {e['kind']}"
    if find("owner") is None:
        lines.insert(find("kind") + 1, f"owner: {e['owner']}")
    else:
        lines[find("owner")] = f"owner: {e['owner']}"
    i = find("aka")
    if i is None:
        lines.insert(find("owner") + 1, f"aka: [{e['old']}]")
    elif lines[i].strip().endswith("]"):
        inner = lines[i].split("[", 1)[1].rsplit("]", 1)[0].strip()
        items = [x.strip() for x in inner.split(",") if x.strip()]
        if e["old"] not in items:
            items.append(e["old"])
        lines[i] = f"aka: [{', '.join(items)}]"
    else:
        lines.insert(i + 1, f"  - {e['old']}")
    i = find("audience")
    add = e.get("audience_add", [])
    if i is None:
        lines.insert(find("aka") + 1, f"audience: [{', '.join(add + ['worker'])}]")
    elif lines[i].strip().endswith("]"):
        inner = lines[i].split("[", 1)[1].rsplit("]", 1)[0]
        items = [x.strip() for x in inner.split(",") if x.strip()]
        lines[i] = f"audience: [{', '.join([a for a in add if a not in items] + items)}]"
    prefix = e["kind"].upper() + " — "
    i = find("description")
    head = lines[i][len("description:"):].strip()
    if head in (">", ">-", "|", "|-"):
        j = i + 1
        while not lines[j].strip():
            j += 1
        ind = len(lines[j]) - len(lines[j].lstrip())
        if not lines[j].lstrip().startswith(prefix):
            lines[j] = lines[j][:ind] + prefix + lines[j][ind:]
    elif head[:1] in "\"'":
        if not head[1:].startswith(prefix):
            lines[i] = "description: " + head[0] + prefix + head[1:]
    elif not head.startswith(prefix):
        lines[i] = "description: " + prefix + head
    return "\n".join(lines) + body


def stub(e, today):
    until = (today + datetime.timedelta(days=30)).isoformat()
    return (f"---\nname: {e['old']}\nkind: {e['kind']}\ndescription: MOVED to {e['new']} on {today}. Read that skill; "
            f"this stub is removed after {until}.\ndisable-model-invocation: true\ncreated_by: agent\n"
            f"lifecycle: active\n---\n\nMOVED: this skill is now `{e['new']}` (renamed {today}, "
            f"docs/org/SKILL-KINDS-2026-09-27.md). Remove after {until} or once no live file names it.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text(encoding="utf-8"))
    for e in plan:
        if not (SKILLS / e["old"] / "SKILL.md").is_file():
            raise SystemExit(f"STOP: {e['old']} not found")
        if (SKILLS / e["new"]).exists():
            raise SystemExit(f"STOP: {e['new']} already exists")
        if not NAME_RE.match(e["new"]) or e["kind"] not in KINDS:
            raise SystemExit(f"STOP: {e['new']} / {e['kind']} breaks the naming rule")
    pats = [(token_re(e["old"]), e["new"]) for e in plan]
    changes = {}
    for p in live_files():
        s = read(p)
        n = sum(len(r.findall(s)) for r, _ in pats)
        if n:
            changes[p] = n
    print(f"{len(plan)} skills · {len(changes)} files · {sum(changes.values())} mentions to rewrite")
    for p, n in sorted(changes.items(), key=lambda x: -x[1])[:25]:
        print(f"  {n:4d}  {p.relative_to(ROOT)}")
    if not a.apply:
        print("dry run: nothing changed")
        return
    today = datetime.date.today()
    for e in plan:
        subprocess.run(["git", "-C", str(ROOT), "mv", f".claude/skills/{e['old']}", f".claude/skills/{e['new']}"],
                       check=True)
    # repoint first (the moved files are walked under their new names), THEN patch the frontmatter, so the
    # `aka: [<old>]` line the patch adds is not itself rewritten to the new name
    for p in list(live_files()):
        s = read(p)
        t = s
        for r, new in pats:
            t = r.sub(new, t)
        if t != s:
            p.write_text(t, encoding="utf-8")
    for e in plan:
        f = SKILLS / e["new"] / "SKILL.md"
        f.write_text(patch_frontmatter(f.read_text(encoding="utf-8"), e), encoding="utf-8")
    for e in plan:
        d = SKILLS / e["old"]
        d.mkdir()
        (d / "SKILL.md").write_text(stub(e, today), encoding="utf-8")
    print("applied: moved, patched, repointed, stubbed — now lint, run the suite, commit")


if __name__ == "__main__":
    main()
