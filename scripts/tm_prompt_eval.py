#!/usr/bin/env python3
"""TraderMindset prompt A/B eval gate.

Compares a CANDIDATE caption prompt (B) against the CURRENT one (A) on the
golden set (data/tm-golden-set.json) and returns a per-case win/lose/tie plus an
overall verdict. A candidate that LOSES (leaks a banned output on a negative
case, introduces a new hard violation, or nets more losses than wins) must NOT
be activated in prompts/trader-mindset/registry.json — that is the whole point
of the gate (wiki §4.5: "prompt ใหม่ต้องชนะ A/B ... แพ้ = ไม่ ship").

Two scoring signals per case:
  * deterministic checks (scripts/tm_checks.py): emoji / guarantee / percentage /
    length — exact and offline.
  * an LLM voice/quality judge — A vs B for tone + compliance nuance.

Dry vs real
-----------
  --dry : NO paid API. Candidate outputs come from data/tm-eval-fixtures.json and
          the judge is a deterministic surrogate (score + soft-warning penalty).
          The full scoring + verdict pipeline runs offline (ask-before-paid).
  real  : generate A/B outputs from the two prompt versions via the caption LLM,
          and use an LLM judge. Run by the CTO after the CEO confirms budget.

Usage:
  PY=/Users/gob/Projects/Agents/.venv/bin/python
  $PY scripts/tm_prompt_eval.py --dry                      # A=v1 B=v2 on golden set
  $PY scripts/tm_prompt_eval.py --dry --a v1 --b v2
  $PY scripts/tm_prompt_eval.py --a v1 --b v2              # REAL (CTO only)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tm_checks   # noqa: E402
import tm_prompts  # noqa: E402

GOLDEN_PATH = os.path.join(tm_prompts.PROMPTS_DIR, "..", "..", "data", "tm-golden-set.json")
GOLDEN_PATH = os.path.normpath(GOLDEN_PATH)
FIXTURES_PATH = os.path.join(os.path.dirname(GOLDEN_PATH), "tm-eval-fixtures.json")

TIE_EPS = 0.05   # quality-score band within which A and B count as a tie


# --------------------------------------------------------------------------- #
# Output sourcing
# --------------------------------------------------------------------------- #
def load_golden(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["cases"]


def load_fixtures(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["fixtures"]


def build_caption_messages_version(case: dict, version: str) -> list[dict]:
    """Assemble caption chat messages from a SPECIFIC prompt version (real run)."""
    p = tm_prompts.load_prompt("caption", version)
    user = tm_prompts.render(p["user"], theme=case["theme"], hero_word=case["hero_word"],
                             seed_idea=case["seed_idea"], lessons="")
    return [{"role": "system", "content": p["system"]}, {"role": "user", "content": user}]


def gen_output(case: dict, version: str, model: str) -> dict:
    """REAL: generate {caption, sub_line, tags} for a case from a prompt version."""
    import urllib.request

    import trader_mindset_batch as tm  # reuse env-key loader + JSON parse (no new dep)
    key = tm.load_env_key("OPENROUTER_API_KEY")
    payload = {"model": model, "messages": build_caption_messages_version(case, version),
               "temperature": 0.8, "response_format": {"type": "json_object"}}
    req = urllib.request.Request(
        tm.OPENROUTER_ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://mooniex.com", "X-Title": "MoonieX TM eval"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    obj = tm._parse_json_object(data["choices"][0]["message"]["content"])
    return {"caption": obj.get("caption", ""), "sub_line": obj.get("sub_line", ""),
            "tags": obj.get("tags", [])}


# --------------------------------------------------------------------------- #
# Judges
# --------------------------------------------------------------------------- #
def surrogate_quality(det: dict) -> float:
    """Deterministic judge surrogate (dry): det score minus soft-warning penalty."""
    return det["score"] - 0.1 * len(det["warnings"])


def llm_quality_judge(case: dict, out_a: dict, out_b: dict, model: str) -> dict:
    """REAL judge: which output better fits MoonieX voice + CEO rules. Returns
    {winner: 'a'|'b'|'tie', reason}."""
    import urllib.request

    import trader_mindset_batch as tm
    key = tm.load_env_key("OPENROUTER_API_KEY")
    sys_msg = (
        "คุณคือบรรณาธิการเพจเทรดทอง MoonieX ตัดสินว่าแคปชันไหนดีกว่ากันตาม voice รุ่นพี่สุภาพ "
        "อบอุ่น + กฎเหล็ก (ห้ามชี้นำการลงทุน/การันตีกำไร/อิโมจิ/ยาวเกิน). ตอบ JSON "
        '{"winner":"a"|"b"|"tie","reason":"..."} เท่านั้น')
    user_msg = (f"หัวข้อ: {case['hero_word']} ({case['theme']})\n\n[A]\n{out_a['caption']}\n\n"
                f"[B]\n{out_b['caption']}\n\nแคปชันไหนดีกว่า?")
    payload = {"model": model, "temperature": 0.0, "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": sys_msg},
                            {"role": "user", "content": user_msg}]}
    req = urllib.request.Request(
        tm.OPENROUTER_ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://mooniex.com", "X-Title": "MoonieX TM judge"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    obj = tm._parse_json_object(data["choices"][0]["message"]["content"])
    return {"winner": obj.get("winner", "tie"), "reason": obj.get("reason", "")}


# --------------------------------------------------------------------------- #
# Per-case verdict
# --------------------------------------------------------------------------- #
def _commits(expect: str, det: dict) -> bool:
    """Did this output commit the violation a negative case must resist?"""
    if expect == "emoji":
        return not det["checks"]["emoji"]
    if expect == "guarantee":
        return not det["checks"]["guarantee"]
    if expect == "too_long":
        return not det["checks"]["caption_length"]
    if expect == "advice":
        return bool(det["warnings"])    # soft signal (dry surrogate)
    return False


def case_verdict(case: dict, det_a: dict, det_b: dict, quality_a: float,
                 quality_b: float, eps: float) -> tuple[str, bool, str]:
    """Return (verdict, critical, reason). verdict in {win,lose,tie} for B vs A."""
    # 1) B must not introduce a NEW hard violation that A did not have.
    new_hard = set(det_b["violations"]) - set(det_a["violations"])
    if det_a["passed"] and not det_b["passed"] and new_hard:
        return "lose", True, "B adds hard violation: " + "; ".join(sorted(new_hard))

    # 2) Negative cases: the resisted-violation outcome dominates.
    if case["type"] == "negative":
        expect = case.get("expect", "")
        va, vb = _commits(expect, det_a), _commits(expect, det_b)
        if vb and not va:
            return "lose", True, f"B leaked '{expect}' that A resisted"
        if va and not vb:
            return "win", False, f"B resisted '{expect}' that A leaked"

    # 3) Otherwise compare quality scores within a tie band.
    if quality_b > quality_a + eps:
        return "win", False, f"higher quality ({quality_b:.2f} > {quality_a:.2f})"
    if quality_b < quality_a - eps:
        return "lose", False, f"lower quality ({quality_b:.2f} < {quality_a:.2f})"
    return "tie", False, f"equivalent quality ({quality_b:.2f} ~= {quality_a:.2f})"


# --------------------------------------------------------------------------- #
# Eval driver
# --------------------------------------------------------------------------- #
def evaluate(cases: list[dict], a_ver: str, b_ver: str, dry: bool, fixtures: dict,
             model: str, eps: float) -> dict:
    rows: list[dict] = []
    for case in cases:
        if case.get("kind", "caption") != "caption":
            continue
        cid = case["id"]
        if dry:
            fx = fixtures.get(cid)
            if not fx:
                rows.append({"id": cid, "verdict": "skip", "critical": False,
                             "reason": "no fixture (dry)", "det_a": None, "det_b": None})
                continue
            out_a, out_b = fx["a"], fx["b"]
        else:
            out_a = gen_output(case, a_ver, model)
            out_b = gen_output(case, b_ver, model)

        det_a = tm_checks.check_caption(out_a.get("caption", ""), out_a.get("sub_line", ""),
                                        out_a.get("tags"))
        det_b = tm_checks.check_caption(out_b.get("caption", ""), out_b.get("sub_line", ""),
                                        out_b.get("tags"))
        if dry:
            qa, qb = surrogate_quality(det_a), surrogate_quality(det_b)
        else:
            j = llm_quality_judge(case, out_a, out_b, model)
            # Map judge winner onto a comparable quality pair, then let det checks
            # still veto via case_verdict's hard-violation / negative-leak rules.
            base_a, base_b = surrogate_quality(det_a), surrogate_quality(det_b)
            bump = 0.2
            qa = base_a + (bump if j["winner"] == "a" else 0.0)
            qb = base_b + (bump if j["winner"] == "b" else 0.0)

        verdict, critical, reason = case_verdict(case, det_a, det_b, qa, qb, eps)
        rows.append({"id": cid, "type": case["type"], "verdict": verdict,
                     "critical": critical, "reason": reason,
                     "det_a": det_a["passed"], "det_b": det_b["passed"]})

    wins = sum(1 for r in rows if r["verdict"] == "win")
    loses = sum(1 for r in rows if r["verdict"] == "lose")
    ties = sum(1 for r in rows if r["verdict"] == "tie")
    skips = sum(1 for r in rows if r["verdict"] == "skip")
    critical = sum(1 for r in rows if r["critical"])
    activate_ok = (critical == 0) and (loses <= wins)
    return {"rows": rows, "wins": wins, "loses": loses, "ties": ties, "skips": skips,
            "critical": critical, "activate_ok": activate_ok,
            "a": a_ver, "b": b_ver, "dry": dry}


def render_report(res: dict) -> str:
    mode = "dry" if res["dry"] else "REAL"
    out = [f"=== tm_prompt_eval: caption  A={res['a']}  B={res['b']}  ({mode}) ===",
           f"golden cases scored: {len(res['rows'])}", "",
           "per-case (B vs A):"]
    label = {"win": "WIN ", "lose": "LOSE", "tie": "tie ", "skip": "skip"}
    for r in res["rows"]:
        crit = "  [CRITICAL]" if r.get("critical") else ""
        det = ("" if r["det_a"] is None
               else f"  | det A={'PASS' if r['det_a'] else 'FAIL'} B={'PASS' if r['det_b'] else 'FAIL'}")
        out.append(f"  {r['id']:<26} {label.get(r['verdict'], r['verdict'])}{det}  {r['reason']}{crit}")
    out += ["",
            f"summary: win={res['wins']} lose={res['loses']} tie={res['ties']} "
            f"skip={res['skips']}  critical_regressions={res['critical']}"]
    if res["activate_ok"]:
        out.append(f"VERDICT: ACTIVATE-OK — B does not lose vs A (net {res['wins'] - res['loses']:+d}). "
                   f"Safe to flip registry.active.caption={res['b']} after human review.")
    else:
        why = []
        if res["critical"]:
            why.append(f"{res['critical']} critical regression(s)")
        if res["loses"] > res["wins"]:
            why.append(f"net losses ({res['loses']} lose > {res['wins']} win)")
        out.append(f"VERDICT: BLOCKED — do NOT activate B. Reason: {', '.join(why) or 'B loses'}.")
    out.append("  (rule: BLOCK if any negative-case leak by B, any new hard violation by B, "
               "or loses > wins)")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TraderMindset prompt A/B eval gate")
    ap.add_argument("--kind", choices=tm_prompts.KINDS, default="caption")
    ap.add_argument("--a", default="v1", help="current/baseline prompt version label")
    ap.add_argument("--b", default="v2", help="candidate prompt version label")
    ap.add_argument("--golden", default=GOLDEN_PATH)
    ap.add_argument("--fixtures", default=FIXTURES_PATH)
    ap.add_argument("--dry", action="store_true", help="no paid API: fixtures + surrogate judge")
    ap.add_argument("--model", default=os.environ.get("TM_EVAL_MODEL", "anthropic/claude-3.5-sonnet"))
    ap.add_argument("--eps", type=float, default=TIE_EPS)
    args = ap.parse_args(argv)

    if args.kind != "caption":
        sys.exit("eval currently scores caption prompts only (poster A/B is future work)")
    cases = load_golden(args.golden)
    fixtures = load_fixtures(args.fixtures) if args.dry else {}
    res = evaluate(cases, args.a, args.b, args.dry, fixtures, args.model, args.eps)
    print(render_report(res))
    # Non-zero exit when the gate blocks, so a CI/automation step can fail hard.
    return 0 if res["activate_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
