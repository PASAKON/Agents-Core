"""Blind judge for the Haiku 5.5 shadow trial (LungNote 6f825cac).

For each item it shows Opus 5.5 the item's input and the two drafts as "A" and "B".
Which model is A is a seeded coin per item; the key goes to judge/job<N>/key.json and
is read only by score.py. The judge prompt never names a model. Each draft gets one
label: USABLE (correct and committable as is), CORRECT (nothing false, needs edits)
or WRONG; job 1 also flags rule_risk (committing it would change or wrongly attack a rule).

    python3 docs/ops/haiku-trial-2026-10/judge.py --job 1 [--items j1-01,...] [--jobs 2]
"""
import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from run import DATA, HALT, STOP_AT, SYS_JOB1, SYS_JOB2, call, note_quota, prompt_for

PAIR = ("claude-haiku-5-5", "claude-sonnet-5-5")
JUDGE_MODEL = "claude-opus-5-5"
SEED = 20261011

RUBRIC_1 = """You grade two drafts, A and B, of skill Field notes made from the same worker Skill-learning block. You do not know who wrote either. Judge each on its own against the block, the catalogue and the drafting rules the writers were given (quoted below).

Labels:
- USABLE: every typed line of the block is carried, faithfully, filed under the right skill from the catalogue (or correctly routed to No owner), in the exact line format, status pending. A C-level could commit it with no edits.
- CORRECT: nothing false and nothing filed in a wrong skill, but it needs an edit before committing: a format slip, a missing evidence id, a typed line dropped, two notes merged, wording that loses a detail that matters.
- WRONG: any false, invented or distorted fact; a note filed under a skill that is not in the catalogue or under an unrelated skill; a "no owner" line filed into a skill as if it were owned; a changed type (e.g. MISSING turned into WRONG); or anything that would change a rule (a status other than pending, a proposed edit to a rule body, a claim that a current rule is wrong that the block does not make).
rule_risk = true if committing that draft would change, flip or wrongly promote a rule, or would record a false claim that a current rule is wrong. Otherwise false.

Return JSON only, no prose around it:
{"A":{"label":"USABLE|CORRECT|WRONG","rule_risk":false,"reason":"<= 30 words"},"B":{"label":"...","rule_risk":false,"reason":"..."}}"""

RUBRIC_2 = """You grade two REPORT.md drafts, A and B, written from the same task brief, commit log and diff. You do not know who wrote either. Judge each on its own against the input and the writing rules the writers were given (quoted below).

The worker's own report is shown as REFERENCE. The worker did the work, so it may mention test runs or live checks that the brief, log and diff cannot show; a draft that says "not shown in the log" for those is right. A draft that claims a test ran or passed, a deploy happened or a check was done without evidence in the brief, log or diff is WRONG even when the reference happens to confirm it.

Labels:
- USABLE: accurate; covers what shipped (the main files and changes); right about tests and open items; a C-level could post it as the report with no edits.
- CORRECT: nothing false, but it misses a main point, gets the emphasis wrong, or needs edits before posting.
- WRONG: any false or invented claim (files, behaviour, tests, results, deploys), or it misstates what the branch does or whether it meets the brief.

Return JSON only, no prose around it:
{"A":{"label":"USABLE|CORRECT|WRONG","reason":"<= 30 words"},"B":{"label":"...","reason":"..."}}"""


def judge_prompt(job: int, it: dict, skills: str, a: str, b: str) -> tuple[str, str]:
    _, inp = prompt_for(job, it, skills)
    rules = SYS_JOB1 if job == 1 else SYS_JOB2
    ref = f"\n=== REFERENCE (the worker's own report) ===\n{it['reference']}\n" if job == 2 else ""
    user = (f"=== RULES THE WRITERS WERE GIVEN ===\n{rules}\n\n=== INPUT THE WRITERS WERE GIVEN ===\n{inp}{ref}\n"
            f"=== DRAFT A ===\n{a}\n\n=== DRAFT B ===\n{b}\n")
    return (RUBRIC_1 if job == 1 else RUBRIC_2), user


def parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", type=int, choices=[1, 2], required=True)
    ap.add_argument("--items", default="all")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    items = json.loads((DATA / f"job{a.job}_items.json").read_text())
    if a.items != "all":
        want = set(a.items.split(","))
        items = [i for i in items if i["item"] in want]
    skills = (DATA / "skills.txt").read_text()
    runs = DATA / "runs" / f"job{a.job}"
    out = DATA / "judge" / f"job{a.job}"
    out.mkdir(parents=True, exist_ok=True)
    keyf = out / "key.json"
    key = json.loads(keyf.read_text()) if keyf.exists() else {}

    todo = []
    for it in items:
        drafts = {m: runs / m / f"{it['item']}.json" for m in PAIR}
        if not all(f.exists() for f in drafts.values()):
            continue
        if it["item"] not in key:
            r = random.Random(f"{SEED}-{a.job}-{it['item']}")
            key[it["item"]] = list(PAIR) if r.random() < 0.5 else list(PAIR[::-1])
        todo.append(it)
    keyf.write_text(json.dumps(key, indent=1))

    def one(it: dict) -> str:
        f = out / f"{it['item']}.json"
        if f.exists() and not a.force:
            return f"{it['item']} skip"
        if HALT.is_set():
            return f"{it['item']} HALTED: 7-day quota at {STOP_AT:.0%}+"
        ma, mb = key[it["item"]]
        ta = json.loads((runs / ma / f"{it['item']}.json").read_text()).get("text", "")
        tb = json.loads((runs / mb / f"{it['item']}.json").read_text()).get("text", "")
        system, user = judge_prompt(a.job, it, skills, ta, tb)
        rec = call(JUDGE_MODEL, system, user)
        note_quota(rec)
        rec["item"] = it["item"]
        rec["verdict"] = parse(rec.get("text", ""))
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        v = rec["verdict"] or {}
        return (f"{it['item']} served={rec['served']} A={v.get('A', {}).get('label')} "
                f"B={v.get('B', {}).get('label')} wall={rec['wall_s']}s rate={rec['rate'][-1:]}")

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for line in ex.map(one, todo):
            print(line, flush=True)


if __name__ == "__main__":
    main()
