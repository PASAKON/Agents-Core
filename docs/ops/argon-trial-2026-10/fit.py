"""Write one runner_fit record per job per runner, through tools/runner_fit.py's own build() and record().

Paired jobs: result is the judge's label on the runner's FIRST output (USABLE -> pass, CORRECT -> redo, WRONG -> fail/wrong);
iteration = redo rounds that runner got (only the landing output is ever redone); first_pass is computed by
runner_fit.build(). `why` carries the judge's score, the quota meter moves (before -> after) and the trial id.
Argon-only jobs: result, redo count and reviewer_fix come from review/<job>.json; minutes include the redo rounds.

    bash scripts/hub/org-python.sh <harness>/fit.py [--write]      # dry run without --write
"""
import json
import sys
from pathlib import Path

CORE = Path("/tmp/claude-0/-opt-MoonieXHQ-Agents-Core/381826cd-bc49-487d-a946-08e0d1a121af/scratchpad/core-origin")
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import db  # noqa: E402
from tools import runner_fit  # noqa: E402
from tools.quota import load_plans  # noqa: E402

from jobs import JOBS  # noqa: E402
from run import DATA  # noqa: E402

MODEL = {"argon": ("agy", "gemini-4-argon-high"), "sonnet": ("claude", "claude-sonnet-5-5")}
RESULT = {"USABLE": ("pass", None), "CORRECT": ("redo", None), "WRONG": ("fail", "wrong")}


def meters_line(rec: dict) -> str:
    b, a = rec["meters_before"], rec["meters_after"]
    if rec["runner"] == "argon":
        return "agy gemini-5h {}→{} weekly {}→{} (remaining %)".format(
            b["agy"].get("gemini-5h"), a["agy"].get("gemini-5h"), b["agy"].get("gemini-weekly"), a["agy"].get("gemini-weekly"))
    r = (rec.get("rate") or [{}])
    return "claude 5h used {}→{} 7d used {}→{} (usage.json %, CLI at start {})".format(
        b["claude"].get("five_hour_used"), a["claude"].get("five_hour_used"), b["claude"].get("seven_day_used"),
        a["claude"].get("seven_day_used"), r[0])


def main() -> None:
    write = "--write" in sys.argv
    key = json.loads((DATA / "judge" / "key.json").read_text())
    landing = json.loads((DATA / "landing.json").read_text()) if (DATA / "landing.json").exists() else {}
    cfg = load_plans()
    out = []
    for job in JOBS:
        jf, rf = DATA / "judge" / f"{job['id']}.json", DATA / "review" / f"{job['id']}.json"
        if not jf.exists() and rf.exists():
            # Argon alone (CEO 14 Oct ~03:40): the reviewer's pass / redo / fail is the score.
            rv = json.loads(rf.read_text())
            rec = json.loads((DATA / "runs" / job["id"] / "argon.json").read_text())
            land = landing.get(job["id"], {})
            redo_min = sum(json.loads(f.read_text()).get("minutes") or 0
                           for f in (DATA / "runs" / job["id"]).glob("argon-r*.json"))
            why = (f"argon-trial-2026-10 {job['id']} ({job['source']}): Argon alone, reviewer {rv['result']}"
                   f"{' + reviewer fix' if rv['reviewer_fix'] else ''}: {rv['note'][:300]}; {meters_line(rec)}; "
                   f"{'landed ' + land['sha'] if land.get('sha') else 'landing pending'}")
            p = runner_fit.build(runner="agy", model="gemini-4-argon-high",
                                 bucket=runner_fit.bucket_for("agy", "gemini-4-argon-high", cfg),
                                 size=job["size"], job_type=job["job_type"], result=rv["result"],
                                 fail_reason=rv.get("fail_reason"), why=why,
                                 minutes=round(rec["minutes"] + redo_min, 2), iteration=rv["redo"],
                                 reviewer_fix=rv["reviewer_fix"], source="manual", reviewer="cto-d1a121af")
            out.append((f"argon-trial-{job['id']}", p))
            continue
        if not jf.exists():
            continue
        v = json.loads(jf.read_text())["verdict"]
        ra, rb = key[job["id"]]
        lab = {ra: v["A"], rb: v["B"]}
        for r in ("argon", "sonnet"):
            rec = json.loads((DATA / "runs" / job["id"] / f"{r}.json").read_text())
            runner, model = MODEL[r]
            result, reason = RESULT[lab[r]["label"]]
            land = landing.get(job["id"], {})
            redo = land.get("redo", 0) if land.get("runner") == r else 0
            why = (f"argon-trial-2026-10 {job['id']} ({job['source']}): judge {lab[r]['label']} {lab[r]['score']}/10 blind vs "
                   f"{'Sonnet' if r == 'argon' else 'Argon'}; {meters_line(rec)}; "
                   f"{'landed ' + land.get('sha', '') if land.get('runner') == r else 'discarded' if land else 'landing pending'}")
            p = runner_fit.build(runner=runner, model=model, bucket=runner_fit.bucket_for(runner, model, cfg),
                                 size=job["size"], job_type=job["job_type"], result=result, fail_reason=reason,
                                 why=why, minutes=rec["minutes"], iteration=redo,
                                 reviewer_fix=bool(land.get("reviewer_fix")) and land.get("runner") == r,
                                 source="manual", reviewer="cto-d1a121af")
            out.append((f"argon-trial-{job['id']}", p))
    for tid, p in out:
        print(tid, json.dumps(p, ensure_ascii=False))
    if write:
        with db.get_conn() as conn:
            for tid, p in out:
                runner_fit.record(conn, tid, "runner_fit", p)
        print(f"written: {len(out)}")


if __name__ == "__main__":
    main()
