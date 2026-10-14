"""Blind judge for the Argon trial: Opus 5.5 (effort high) grades the two outputs of one job as A and B.

A seeded coin per job decides which runner is A; the key goes to DATA/judge/key.json and only
score.py reads it. The judge sees the brief, each output's diff and REPORT.md, and the CTO's check
results for each output. It never sees a runner or model name.

    python3 judge.py --job D2 [--force]
"""
import argparse
import json
import random
import re
import subprocess
import tempfile
import time

from jobs import JOBS_BY_ID
from run import DATA

JUDGE_MODEL = "claude-opus-5-5"
SEED = 20261014
PAIR = ("argon", "sonnet")
DIFF_CAP = 60000

RUBRIC = """You grade two outputs, A and B, made by two workers from the same task brief in the same repository.
You do not know who made either. Judge each on its own against the brief, then compare.

Each output is a diff, the worker's REPORT.md, and the CHECKS the reviewer ran on that output (workers could not
run any command; the reviewer ran tests, linters and mechanical layout checks afterwards; for a translation the
check lists non-Thai lines that changed, structure differences and every line that still has Thai).

Labels:
- USABLE: does what the brief asks, correctly and completely; checks pass (or a failure is clearly not the
  worker's fault); nothing out of scope; a reviewer could merge it as is, at most a trivial touch.
- CORRECT: nothing false or harmful, but it needs a real edit before merging: a missed requirement, a weak or
  missing test, a translation slip in meaning, a kept/translated mistake, a report claim that overstates.
- WRONG: broken or harmful: a failing check caused by the change, a wrong fix, changed meaning or code
  where only text should change, invented facts, out-of-scope damage, or nothing done.
Also give each a score from 0 to 10 for overall quality (10 = what a strong senior would merge without comment),
and say which output is better overall (A, B or tie). A report that claims something the checks or diff
contradict counts against that output.

Return JSON only, no prose around it:
{"A":{"label":"USABLE|CORRECT|WRONG","score":0,"reason":"<= 40 words"},"B":{"label":"...","score":0,"reason":"..."},"better":"A|B|tie","why_better":"<= 30 words"}"""


def bundle(job_id: str, runner: str) -> str:
    d = DATA / "runs" / job_id
    patch = (d / f"{runner}.patch").read_text()
    if len(patch) > DIFF_CAP:
        patch = patch[:DIFF_CAP] + f"\n[... diff cut at {DIFF_CAP} chars of {len(patch)}]"
    report = (d / f"{runner}.report.md").read_text() or "(no REPORT.md written)"
    chk = json.loads((d / f"{runner}.checks.json").read_text())
    if not chk.get("applied"):
        checks = f"NOT APPLIED / EMPTY: {chk.get('apply_error')}"
    else:
        checks = "\n\n".join(f"$ {c['cmd']}\nexit {c['exit']}" + (f" ({c['note']})" if c.get("note") else "")
                             + f"\n{c['tail'][-3500:]}" for c in chk["checks"])
    return f"--- DIFF ---\n{patch or '(empty)'}\n\n--- REPORT.md ---\n{report[:6000]}\n\n--- CHECKS ---\n{checks}"


def call(system: str, user: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="argon-judge-") as cwd:
        t0 = time.time()
        p = subprocess.run(["claude", "-p", "--model", JUDGE_MODEL, "--effort", "high", "--output-format", "json",
                            "--no-session-persistence", "--tools", "", "--strict-mcp-config",
                            "--setting-sources", "user", "--system-prompt", system],
                           input=user, capture_output=True, text=True, cwd=cwd, timeout=1200)
    rec = {"exit": p.returncode, "wall_s": round(time.time() - t0, 1), "stderr_tail": p.stderr[-500:]}
    try:
        out = json.loads(p.stdout)
        rec.update(text=out.get("result", ""), is_error=out.get("is_error"),
                   served=sorted((out.get("modelUsage") or {}).keys()))
    except ValueError:
        rec["text"] = p.stdout[-2000:]
    return rec


def parse(text: str):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    job = JOBS_BY_ID[a.job]
    out = DATA / "judge"
    out.mkdir(parents=True, exist_ok=True)
    keyf = out / "key.json"
    key = json.loads(keyf.read_text()) if keyf.exists() else {}
    if a.job not in key:
        r = random.Random(f"{SEED}-{a.job}")
        key[a.job] = list(PAIR) if r.random() < 0.5 else list(PAIR[::-1])
        keyf.write_text(json.dumps(key, indent=1))
    f = out / f"{a.job}.json"
    if f.exists() and not a.force:
        raise SystemExit(f"{a.job} already judged")
    ra, rb = key[a.job]
    user = (f"=== TASK BRIEF (both workers got this, plus an edit-only contract: file tools only, no commands, "
            f"write REPORT.md) ===\n{job['brief']}\n\n=== OUTPUT A ===\n{bundle(a.job, ra)}\n\n"
            f"=== OUTPUT B ===\n{bundle(a.job, rb)}\n")
    rec = call(RUBRIC, user)
    rec["job"], rec["verdict"] = a.job, parse(rec.get("text", ""))
    f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    v = rec["verdict"] or {}
    print(f"{a.job} served={rec.get('served')} A={v.get('A', {}).get('label')}/{v.get('A', {}).get('score')} "
          f"B={v.get('B', {}).get('label')}/{v.get('B', {}).get('score')} better={v.get('better')} wall={rec['wall_s']}s")


if __name__ == "__main__":
    main()
