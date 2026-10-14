"""Unblind and score the Argon trial. Reads judge/key.json, the verdicts, review/*.json, landing.json and the
run records.

Two kinds of job (CEO order 14 Oct ~03:40 via SomPong: real jobs only, no wasted duplicate):
- paired: both runners ran the same brief; a blind Opus judge labelled both (USABLE 2, CORRECT 1, WRONG 0).
- argon-only: Argon ran alone; the reviewer's verdict (review/<job>.json: pass / redo / fail) is the score.

Per job type:
- points ratio: Argon's judge points as a share of Sonnet's. Paired jobs only. The pass bar is >= 0.90.
- first pass, strict: the definition in tools/runner_fit.py. A job passes when the reviewer accepted it with no
  redo and no reviewer fix, on every job Argon ran. A paired job where Sonnet's output landed counts for Argon
  when its diff was judged USABLE, because nobody had to fix it.
- phase-2 candidate: strict first pass >= 90 %, and points ratio >= 0.90 wherever paired jobs exist.

    python3 score.py            # prints the tables, writes DATA/results.json
"""
import json

from jobs import JOBS
from run import DATA

POINTS = {"USABLE": 2, "CORRECT": 1, "WRONG": 0}
GROUP = {"dev": "developer S/M", "doc": "docs / translation", "analysis": "shell-free analysis"}


def meter_move(rec: dict) -> dict:
    b, a = rec.get("meters_before", {}), rec.get("meters_after", {})
    out = {}
    for k in ("gemini-5h", "gemini-weekly", "3p-5h", "3p-weekly"):
        x, y = b.get("agy", {}).get(k), a.get("agy", {}).get(k)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            out[f"agy {k} remaining"] = round(y - x, 3)
    rate = rec.get("rate") or []
    if rate:
        out["claude 5h used (CLI, at start)"] = rate[0].get("five_hour")
        out["claude 7d used (CLI, at start)"] = rate[0].get("seven_day")
    return out


def run_rec(job: str, runner: str) -> dict:
    rec = json.loads((DATA / "runs" / job / f"{runner}.json").read_text())
    return {"minutes": rec.get("minutes"), "exit": rec.get("exit"),
            "tokens_in": (rec.get("input_tokens") or 0) + (rec.get("cache_read") or 0) + (rec.get("cache_write") or 0),
            "tokens_out": rec.get("output_tokens"), "meters": meter_move(rec)}


def redo_minutes(job: str) -> float:
    """Minutes spent on Argon's redo rounds (argon-r1.json, ...)."""
    return round(sum(json.loads(f.read_text()).get("minutes") or 0
                     for f in (DATA / "runs" / job).glob("argon-r*.json")), 2)


def main() -> None:
    key = json.loads((DATA / "judge" / "key.json").read_text())
    landing = json.loads((DATA / "landing.json").read_text()) if (DATA / "landing.json").exists() else {}
    rows = []
    for job in JOBS:
        jid = job["id"]
        jf, rf = DATA / "judge" / f"{jid}.json", DATA / "review" / f"{jid}.json"
        land = landing.get(jid, {})
        if jf.exists():
            v = json.loads(jf.read_text()).get("verdict") or {}
            ra, rb = key[jid]
            by = {ra: v.get("A", {}), rb: v.get("B", {})}
            row = {"job": jid, "kind": job["kind"], "source": job["source"], "mode": "paired",
                   "better": {"A": ra, "B": rb}.get(v.get("better"), "tie"), "why_better": v.get("why_better"),
                   "landed": land.get("runner"), "landed_sha": land.get("sha")}
            for r in ("argon", "sonnet"):
                row[r] = dict(run_rec(jid, r), label=by[r].get("label"), score=by[r].get("score"), reason=by[r].get("reason"))
            fixed = land.get("runner") == "argon" and (land.get("reviewer_fix") or land.get("redo", 0) > 0)
            row["argon"]["first_pass"] = row["argon"]["label"] == "USABLE" and not fixed
        elif rf.exists():
            rv = json.loads(rf.read_text())
            row = {"job": jid, "kind": job["kind"], "source": job["source"], "mode": "argon-only",
                   "landed": land.get("runner"), "landed_sha": land.get("sha"),
                   "argon": dict(run_rec(jid, "argon"), review=rv["result"], reviewer_fix=rv["reviewer_fix"],
                                 redo=rv["redo"], note=rv["note"], redo_minutes=redo_minutes(jid),
                                 first_pass=rv["result"] == "pass" and not rv["reviewer_fix"] and rv["redo"] == 0)}
        else:
            continue
        rows.append(row)

    groups = {}
    for row in rows:
        g = groups.setdefault(row["kind"], {"jobs": 0, "paired": 0, "argon_pts": 0, "sonnet_pts": 0,
                                            "argon_first_pass": 0, "argon_min": 0.0, "sonnet_min_paired": 0.0,
                                            "argon_min_paired": 0.0})
        g["jobs"] += 1
        g["argon_first_pass"] += row["argon"]["first_pass"]
        g["argon_min"] += (row["argon"]["minutes"] or 0) + row["argon"].get("redo_minutes", 0)
        if row["mode"] == "paired":
            g["paired"] += 1
            g["argon_pts"] += POINTS.get(row["argon"]["label"], 0)
            g["sonnet_pts"] += POINTS.get(row["sonnet"]["label"], 0)
            g["argon_min_paired"] += row["argon"]["minutes"] or 0
            g["sonnet_min_paired"] += row["sonnet"]["minutes"] or 0
    for g in groups.values():
        g["points_ratio"] = round(g["argon_pts"] / g["sonnet_pts"], 2) if g["sonnet_pts"] else None
        g["argon_first_pass_rate"] = round(g["argon_first_pass"] / g["jobs"], 2)
        g["passes_0_90"] = g["points_ratio"] is None or g["points_ratio"] >= 0.90
        g["phase2_candidate"] = g["passes_0_90"] and g["argon_first_pass_rate"] >= 0.90

    print("| job | type | mode | Argon | Sonnet | Argon first pass | landed | Argon min | Sonnet min |")
    print("|---|---|---|---|---|---|---|---:|---:|")
    for row in rows:
        a, s = row["argon"], row.get("sonnet")
        al = f"{a['label']} {a['score']}" if row["mode"] == "paired" else f"review: {a['review']}" + (" + fix" if a["reviewer_fix"] else "")
        print(f"| {row['job']} | {row['kind']} | {row['mode']} | {al} | {s['label'] + ' ' + str(s['score']) if s else '—'} "
              f"| {'yes' if a['first_pass'] else 'no'} | {row['landed'] or 'pending'} | {a['minutes']} | {s['minutes'] if s else '—'} |")
    print()
    print("| type | jobs (paired) | Argon pts / Sonnet pts | ratio | Argon first pass (strict) | min Argon / Sonnet (paired) | phase 2 |")
    print("|---|---|---|---:|---:|---|---|")
    for k, g in groups.items():
        print(f"| {GROUP[k]} | {g['jobs']} ({g['paired']}) | {g['argon_pts']} / {g['sonnet_pts']} | {g['points_ratio']} "
              f"| {g['argon_first_pass']}/{g['jobs']} | {round(g['argon_min_paired'], 1)} / {round(g['sonnet_min_paired'], 1)} "
              f"| {'yes' if g['phase2_candidate'] else 'no'} |")
    (DATA / "results.json").write_text(json.dumps({"jobs": rows, "groups": groups}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
