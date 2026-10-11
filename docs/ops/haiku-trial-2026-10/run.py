"""Run one model over one job's items for the Haiku 5.5 shadow trial (LungNote 6f825cac).

Every call is the same for both models: `claude -p`, one fixed system prompt, no
tools, no MCP, no session file, the same effort, cwd in an empty dir (no CLAUDE.md).
Per call it records the model the API says it served (assistant `message.model`),
tokens, thinking tokens, wall/API time and the plan's rate-limit utilisation.
Shadow only: outputs land under state/haiku-trial-2026-10/runs/, nothing is filed.

    python3 docs/ops/haiku-trial-2026-10/run.py --job 1 --model claude-haiku-5-5 [--items j1-01,j1-02] [--jobs 2]
"""
import argparse
import json
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[2] / "state" / "haiku-trial-2026-10"
EFFORT = "high"            # the Sonnet worker standard in policies/agents.yaml; same for both models
STOP_AT = 0.92            # the plan's 7-day meter: stop starting calls at this utilisation
HALT = threading.Event()   # set once any call reports the 7-day meter at STOP_AT or above


def note_quota(rec: dict) -> None:
    if any((r.get("seven_day") or 0) >= STOP_AT for r in rec.get("rate", [])):
        HALT.set()

SYS_JOB1 = """You draft skill Field notes for the MoonieX org's skill-learning loop (ADR 0026). A worker finished a task and wrote a "Skill learning" block. Turn each typed line into the note a C-level would append to a skill, or route it away from skills.

Rules:
1. One sighting is a Field note, never a rule. Every note ends "· status: pending". Never write promoted/rejected/superseded, never propose editing a skill's rule body, never mark a rule contested or flipped.
2. Note format, exactly one line per note:
   - <DATE> [WRONG|MISSING|COSTLY] §<section> — <what, one or two plain sentences> · evidence: <task-id / sha / path from the block> · status: pending
   Keep the type the worker gave. A COSTLY note says what ate the time and what would have prevented it.
3. File a note only into a skill that exists in the catalogue (map an aka/old name to the current name). A brief, a doc, a task, a tool or an unclear owner is not a skill.
4. A line marked "no owner", or naming something that is not a skill in the catalogue, goes under "No owner" with its routing word: memory or new-skill.
5. Never invent facts, numbers, paths or evidence ids; copy ids exactly. Always include the task id in evidence.
6. Drop "(none)" lines. If the block has no typed line, output only: No notes.

Output this and nothing else:
### <SkillName>
- <note line>
(one heading per skill that gets notes; the file is .claude/skills/<SkillName>/SKILL.md)
### No owner
- <memory|new-skill>: <one line>"""

SYS_JOB2 = """You write a worker's REPORT.md for the MoonieX org from what the branch shows: the task brief, the branch's commit log and its diff. A C-level reads this report to decide whether to merge.

Rules:
- State only what the brief, log or diff shows. Never invent test runs, results, numbers, deploys or verifications. If the log/diff does not show tests being run, write "not shown in the log"; tests the diff ADDS can be listed as added.
- Name files by their real paths.
- Plain language, short lines, 40 lines at most.

Output exactly these sections and nothing else:
## Summary
(2-4 lines: what was done and whether it meets the brief)
## Files changed
(one line per file or group: path — what changed)
## Tests
(added / run as evidenced, or "not shown in the log")
## Blockers / open items
(what the brief asked for that the diff does not show done, risks, follow-ups; or "none shown")"""


def prompt_for(job: int, it: dict, skills: str) -> tuple[str, str]:
    if job == 1:
        return SYS_JOB1, (f"DATE: {it['date']}\nTASK: {it['task_id']} (role {it['role']}, project {it['project']})\n\n"
                          f"SKILL CATALOGUE:\n{skills}\n\nSKILL LEARNING BLOCK:\n{it['block']}\n")
    return SYS_JOB2, (f"TASK {it['task_id']}: {it['title']}\n\nBRIEF{' (truncated)' if it['brief_truncated'] else ''}:\n"
                      f"{it['brief']}\n\nCOMMIT LOG:\n{it['log']}\n\nDIFFSTAT:\n{it['diffstat']}\n\n"
                      f"DIFF{' (truncated at 30000 chars)' if it['diff_truncated'] else ''}:\n{it['diff']}\n")


def call(model: str, system: str, user: str, effort: str = EFFORT, timeout: int = 600) -> dict:
    with tempfile.TemporaryDirectory(prefix="haiku-trial-") as cwd:
        t0 = time.time()
        p = subprocess.run(
            ["claude", "-p", "--model", model, "--effort", effort, "--output-format", "stream-json",
             "--verbose", "--no-session-persistence", "--tools", "", "--strict-mcp-config",
             "--system-prompt", system],
            input=user, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        wall = time.time() - t0
    rec = {"model_asked": model, "effort": effort, "exit": p.returncode, "wall_s": round(wall, 2),
           "stderr_head": p.stderr.strip().splitlines()[:3], "served": [], "rate": []}
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            rec["served"].append(ev["message"].get("model"))
        elif ev.get("type") == "rate_limit_event":
            w = ev.get("rate_limit_info", {}).get("unifiedWindows", {})
            rec["rate"].append({k: v.get("utilization") for k, v in w.items()})
        elif ev.get("type") == "result":
            mu = next(iter(ev.get("modelUsage", {}).values()), {})
            rec.update(text=ev.get("result", ""), api_ms=ev.get("duration_api_ms"),
                       is_error=ev.get("is_error"), usage_key=list(ev.get("modelUsage", {})),
                       input_tokens=mu.get("inputTokens", 0), output_tokens=mu.get("outputTokens", 0),
                       cache_read=mu.get("cacheReadInputTokens", 0),
                       cache_write=mu.get("cacheCreationInputTokens", 0),
                       thinking_tokens=mu.get("thinkingTokens", 0))
    rec["served"] = sorted(set(rec["served"]))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", type=int, choices=[1, 2], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", default="all")
    ap.add_argument("--jobs", type=int, default=2, help="parallel CLI processes (Contabo has 8 GB)")
    ap.add_argument("--force", action="store_true", help="re-run items that already have an output")
    a = ap.parse_args()
    items = json.loads((DATA / f"job{a.job}_items.json").read_text())
    if a.items != "all":
        want = set(a.items.split(","))
        items = [i for i in items if i["item"] in want]
    skills = (DATA / "skills.txt").read_text()
    out = DATA / "runs" / f"job{a.job}" / a.model
    out.mkdir(parents=True, exist_ok=True)

    def one(it: dict) -> str:
        f = out / f"{it['item']}.json"
        if f.exists() and not a.force:
            return f"{it['item']} skip"
        if HALT.is_set():
            return f"{it['item']} HALTED: 7-day quota at {STOP_AT:.0%}+"
        system, user = prompt_for(a.job, it, skills)
        rec = call(a.model, system, user)
        note_quota(rec)
        rec["item"] = it["item"]
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        return (f"{it['item']} exit={rec['exit']} served={rec['served']} out={rec.get('output_tokens')} "
                f"think={rec.get('thinking_tokens')} wall={rec['wall_s']}s rate={rec['rate'][-1:] }")

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for line in ex.map(one, items):
            print(line, flush=True)


if __name__ == "__main__":
    main()
