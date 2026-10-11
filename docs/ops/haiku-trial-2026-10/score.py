"""Unblind and score the Haiku 5.5 shadow trial (LungNote 6f825cac).

Reads judge/job<N>/key.json + verdicts and the per-call run records, and prints the
tally per job and model: labels (USABLE 2, CORRECT 1, WRONG 0 points), Haiku's
points as a share of Sonnet's, job-1 rule_risk flags, time, tokens and the
list-price equivalent. Writes state/haiku-trial-2026-10/results.json.

Pass (todo 6f825cac): Haiku points >= 90% of Sonnet's on the job, and no Haiku
job-1 note with rule_risk. A job's verdict is computed per job.

    python3 docs/ops/haiku-trial-2026-10/score.py
"""
import json
import statistics as st

from judge import PAIR
from run import DATA

POINTS = {"USABLE": 2, "CORRECT": 1, "WRONG": 0}
# USD per MTok from platform.claude.com/docs/en/about-claude/pricing (read 2026-10-11).
# Claude Code writes the 1h cache, so cache writes use the 1h rate.
PRICE = {  # (input, 1h cache write, cache read, output)
    "claude-haiku-5-5": {"le100k": (0.10, 0.20, 0.01, 0.50), "gt100k": (0.50, 1.00, 0.05, 2.50)},
    "claude-sonnet-5-5": {"all": (2.00, 4.00, 0.10, 10.00)},
    "claude-opus-5-5": {"all": (4.00, 8.00, 0.20, 20.00)},
}


def usd(model: str, r: dict) -> float:
    prompt = r.get("input_tokens", 0) + r.get("cache_read", 0) + r.get("cache_write", 0)
    tiers = PRICE[model]
    p = tiers.get("all") or (tiers["le100k"] if prompt <= 100_000 else tiers["gt100k"])
    return (r.get("input_tokens", 0) * p[0] + r.get("cache_write", 0) * p[1]
            + r.get("cache_read", 0) * p[2] + r.get("output_tokens", 0) * p[3]) / 1e6


def runs_summary(recs: list[dict], model: str) -> dict:
    ok = [r for r in recs if r.get("exit") == 0 and not r.get("is_error")]
    rates = [x for r in recs for x in r.get("rate", [])]
    return {
        "calls": len(recs), "ok": len(ok),
        "served_as_asked": sum(r.get("served") == [model] for r in recs),
        "unrecognized_model_banner": sum(any("unrecognized_model" in s for s in r.get("stderr_head", []))
                                         for r in recs),
        "wall_s_median": round(st.median(r["wall_s"] for r in recs), 1) if recs else None,
        "wall_s_p90": round(sorted(r["wall_s"] for r in recs)[int(0.9 * (len(recs) - 1))], 1) if recs else None,
        "wall_s_total": round(sum(r["wall_s"] for r in recs), 1),
        "prompt_tokens": sum(r.get("input_tokens", 0) + r.get("cache_read", 0) + r.get("cache_write", 0)
                             for r in recs),
        "output_tokens": sum(r.get("output_tokens", 0) for r in recs),
        "thinking_tokens": sum(r.get("thinking_tokens", 0) for r in recs),
        "list_usd": round(sum(usd(model, r) for r in recs), 4),
        "meter_first": rates[0] if rates else None, "meter_last": rates[-1] if rates else None,
    }


def main() -> None:
    results = {}
    for job in (1, 2):
        items = [i["item"] for i in json.loads((DATA / f"job{job}_items.json").read_text())]
        jd = DATA / "judge" / f"job{job}"
        key = json.loads((jd / "key.json").read_text()) if (jd / "key.json").exists() else {}
        # CTO's blind audit (done before unblinding): {item: {"A"|"B": {label, rule_risk, note}}}
        audit = json.loads((jd / "audit.json").read_text()) if (jd / "audit.json").exists() else {}
        overridden = 0
        tally = {m: {"USABLE": 0, "CORRECT": 0, "WRONG": 0, "points": 0, "rule_risk": [], "wrong": []}
                 for m in PAIR}
        judged, judge_recs = 0, []
        for it in items:
            f = jd / f"{it}.json"
            if it not in key or not f.exists():
                continue
            rec = json.loads(f.read_text())
            judge_recs.append(rec)
            v = rec.get("verdict") or {}
            if not ("A" in v and "B" in v):
                continue
            judged += 1
            for slot, fix in audit.get(it, {}).items():
                v[slot] = {**v[slot], **fix}
                overridden += 1
            for slot, model in zip("AB", key[it]):
                lab = v[slot].get("label", "WRONG").upper()
                lab = lab if lab in POINTS else "WRONG"
                t = tally[model]
                t[lab] += 1
                t["points"] += POINTS[lab]
                if v[slot].get("rule_risk"):
                    t["rule_risk"].append(it)
                if lab == "WRONG":
                    t["wrong"].append({"item": it, "reason": v[slot].get("reason", "")})
        h, s = tally[PAIR[0]], tally[PAIR[1]]
        ratio = (h["points"] / s["points"]) if s["points"] else None
        runs = {}
        for m in PAIR:
            files = sorted((DATA / "runs" / f"job{job}" / m).glob("*.json"), key=lambda p: p.stat().st_mtime)
            recs = [json.loads(p.read_text()) for p in files]  # time order, so meter_first/last bracket the batch
            runs[m] = runs_summary(recs, m)
        results[f"job{job}"] = {
            "items": len(items), "judged": judged, "audit_overrides": overridden, "tally": tally,
            "haiku_share_of_sonnet": round(ratio, 3) if ratio is not None else None,
            "pass_quality": bool(ratio is not None and ratio >= 0.90),
            "pass_rule_risk": (not h["rule_risk"]) if job == 1 else True,
            "runs": runs,
            "judge": runs_summary(sorted(judge_recs, key=lambda r: (jd / f"{r['item']}.json").stat().st_mtime),
                                  "claude-opus-5-5"),
        }
        r = results[f"job{job}"]
        r["pass"] = r["pass_quality"] and r["pass_rule_risk"] and judged == len(items)
        print(f"\n== job {job}: judged {judged}/{len(items)} (audit overrides {overridden})  Haiku/Sonnet points = {r['haiku_share_of_sonnet']}"
              f"  pass={r['pass']}")
        for m in PAIR:
            t, u = tally[m], runs[m]
            print(f"  {m:18} U={t['USABLE']:2} C={t['CORRECT']:2} W={t['WRONG']:2} pts={t['points']:3} "
                  f"rule_risk={t['rule_risk']}  served_ok={u['served_as_asked']}/{u['calls']} "
                  f"wall med={u['wall_s_median']}s p90={u['wall_s_p90']}s  out={u['output_tokens']} "
                  f"(think {u['thinking_tokens']})  prompt={u['prompt_tokens']}  list=${u['list_usd']}")
    (DATA / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
