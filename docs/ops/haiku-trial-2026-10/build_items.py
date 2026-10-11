"""Build the 2 x 50 item sets for the Haiku 5.5 shadow trial (LungNote 6f825cac).

Job 1 (field notes): a finished worker task's `## Skill learning` block with at
least one typed WRONG/MISSING/COSTLY line. The model drafts the Field note lines.
Job 2 (report):      a task merged into Agents-Core. The model writes REPORT.md from
the brief, the branch's commit log and its diff. The worker's own report is kept
as the reference the judge compares against; it never goes into the prompt, and
docs/reports/** + any REPORT.md / WORKER.md are cut from the diff so it cannot leak.

Reads the hub (run through scripts/hub/org-python.sh). Writes raw items under
state/haiku-trial-2026-10/ (self-gitignored: Agents-Core is public).

    bash scripts/hub/org-python.sh docs/ops/haiku-trial-2026-10/build_items.py
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import db  # noqa: E402

OUT = ROOT / "state" / "haiku-trial-2026-10"
SEED = 20261011
N = 50
DIFF_CAP = 30_000          # chars of diff shown to the model
DIFF_MAX = 45_000          # skip branches whose diff is bigger (truncation would bias)
BRIEF_CAP = 4_000
EXCLUDE = [":(exclude)docs/reports/**", ":(exclude)**/REPORT.md", ":(exclude)REPORT.md",
           ":(exclude)**/WORKER.md", ":(exclude)WORKER.md"]
TYPED = re.compile(r"(WRONG|MISSING|COSTLY)\s*\[")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                          text=True, check=True).stdout


def skill_learning_block(report: str) -> str | None:
    m = re.search(r"(?im)^#{1,4}\s*Skill[ -]learning.*$", report)
    if not m:
        return None
    rest = report[m.end():]
    n = re.search(r"(?m)^#{1,3}\s+\S", rest)
    return (rest[:n.start()] if n else rest).strip()


def strip_skill_learning(report: str) -> str:
    m = re.search(r"(?im)^#{1,4}\s*Skill[ -]learning.*$", report)
    if not m:
        return report.strip()
    rest = report[m.end():]
    n = re.search(r"(?m)^#{1,3}\s+\S", rest)
    return (report[:m.start()] + (rest[n.start():] if n else "")).strip()


def skill_catalogue() -> str:
    """One line per real skill: name, old names, kind word — what a drafter needs to file a note.

    The 2026-09-27 rename left "MOVED to <new>" stub folders; a stub is not a place to
    file a note, so it is listed only as an old name of its target.
    """
    real, old = {}, {}
    for f in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        head = f.read_text(errors="replace").split("\n---", 1)[0]
        desc = re.search(r"(?m)^description:\s*(?:[>|][-+]?\s*\n\s*)?[\"']?(.+)$", head)
        d = desc.group(1).strip() if desc else ""
        moved = re.match(r"MOVED to (\S+)", d)
        if moved:
            old.setdefault(moved.group(1), set()).add(f.parent.name)
            continue
        aka = re.search(r"(?m)^aka:\s*\[?([^\]\n]*)", head)
        real[f.parent.name] = ({a.strip() for a in aka.group(1).split(",") if a.strip()} if aka else set(),
                               d.split("—")[0].strip()[:12] if "—" in d else "")
    lines = []
    for name, (aka, kind) in real.items():
        names = sorted(aka | old.get(name, set()))
        lines.append(f"- {name}" + (f"  (old names: {', '.join(names)})" if names else "")
                     + (f"  [{kind}]" if kind else ""))
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with db.get_conn(readonly=True) as c:
        rows = c.execute(
            "select id, project, role, title, description, report, created_at, updated_at "
            "from tasks where status='done' and report is not null and length(report) > 300 "
            "order by id").fetchall()
    keys = ["id", "project", "role", "title", "description", "report", "created_at", "updated_at"]
    tasks = {r[0]: dict(zip(keys, r)) for r in rows}
    rng = random.Random(SEED)

    # ---- job 1: field notes -------------------------------------------------
    pool1 = sorted(t for t, x in tasks.items()
                   if TYPED.search(x["report"]) and skill_learning_block(x["report"]))
    pick1 = sorted(rng.sample(pool1, N))
    job1 = [{
        "item": f"j1-{i:02d}", "task_id": t, "role": tasks[t]["role"],
        "project": tasks[t]["project"], "date": tasks[t]["updated_at"][:10],
        "block": skill_learning_block(tasks[t]["report"]),
    } for i, t in enumerate(pick1, 1)]

    # ---- job 2: report summaries --------------------------------------------
    merges: dict[str, str] = {}
    for line in git("log", "--merges", "--format=%H|%s").splitlines():
        h, s = line.split("|", 1)
        for tid in re.findall(r"task-[0-9a-f]{8}", s):
            merges.setdefault(tid, h)
    cands = []
    for tid, h in sorted(merges.items()):
        x = tasks.get(tid)
        if not x or len(strip_skill_learning(x["report"])) < 600:
            continue
        diff = git("diff", f"{h}^1...{h}^2", "--", ".", *EXCLUDE)
        if not (300 <= len(diff) <= DIFF_MAX):
            continue
        cands.append((tid, h, x["role"], len(diff)))
    dev = [c for c in cands if c[2] == "developer"]
    bro = [c for c in cands if c[2] == "browser_operator"]
    oth = [c for c in cands if c[2] not in ("developer", "browser_operator")]
    quota = {"developer": 30, "browser_operator": 15, "other": 5}
    pick2 = (rng.sample(dev, min(quota["developer"], len(dev)))
             + rng.sample(bro, min(quota["browser_operator"], len(bro)))
             + rng.sample(oth, min(quota["other"], len(oth))))
    if len(pick2) < N:  # top up from whatever is left
        left = [c for c in cands if c not in pick2]
        pick2 += rng.sample(left, N - len(pick2))
    pick2.sort()
    job2 = []
    for i, (tid, h, role, _) in enumerate(pick2, 1):
        x = tasks[tid]
        diff = git("diff", f"{h}^1...{h}^2", "--", ".", *EXCLUDE)
        job2.append({
            "item": f"j2-{i:02d}", "task_id": tid, "merge": h, "role": role,
            "project": x["project"], "title": x["title"],
            "brief": x["description"][:BRIEF_CAP],
            "brief_truncated": len(x["description"]) > BRIEF_CAP,
            "log": git("log", "--format=%h %s%n%b", f"{h}^1..{h}^2").strip(),
            "diffstat": git("diff", "--stat=160", f"{h}^1...{h}^2", "--", ".", *EXCLUDE).strip(),
            "diff": diff[:DIFF_CAP], "diff_truncated": len(diff) > DIFF_CAP,
            "reference": strip_skill_learning(x["report"]),
        })

    (OUT / "skills.txt").write_text(skill_catalogue() + "\n")
    (OUT / "job1_items.json").write_text(json.dumps(job1, ensure_ascii=False, indent=1))
    (OUT / "job2_items.json").write_text(json.dumps(job2, ensure_ascii=False, indent=1))
    print(f"job1: {len(job1)} of {len(pool1)} eligible  job2: {len(job2)} of {len(cands)} eligible "
          f"(dev {len(dev)}, browser {len(bro)}, other {len(oth)})  skills: "
          f"{len(skill_catalogue().splitlines())}  -> {OUT}")


if __name__ == "__main__":
    main()
