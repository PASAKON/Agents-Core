#!/usr/bin/env python3
"""jev_lab.py -- measured experiments on Jev (typesafe/jev-1.13), one verb each.

Written 2026-09-23 for the CEO's brief: learn what Jev is good at, get the
most out of it for the least money, and write the skill from what was
MEASURED here, not from the vendor's post. Every call goes through Lab.ask(),
which keeps the provider-reported usage.cost of each answer, so the spend
reported at the end is the sum of what OpenRouter billed, not an estimate.

    python tools/jev_lab.py balance            # key usage before/after (no model call)
    python tools/jev_lab.py probe              # which question types / extra fields exist
    python tools/jev_lab.py anatomy            # what the input tokens are made of
    python tools/jev_lab.py determinism        # same request 10x
    python tools/jev_lab.py concurrency        # sequential vs parallel
    python tools/jev_lab.py batch              # 7 decisions in 1 call vs 7 calls
    python tools/jev_lab.py format             # JSON vs key: value vs prose state
    python tools/jev_lab.py options            # accuracy/latency as the option set grows
    python tools/jev_lab.py nav                # Cookie Run navigator fallback site

Raw rows land in docs/ops/jev-lab-2026-09-23/<verb>.json. A hard ceiling of
CEILING calls per process stops a runaway loop; at ~$0.00002 a call the
ceiling itself is worth about three US cents.
"""
import argparse
import concurrent.futures as cf
import json
import os
import statistics as st
import time
from pathlib import Path

import requests

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")
OUT = Path(__file__).resolve().parent.parent / "docs" / "ops" / "jev-lab-2026-09-23"
ENV_FILE = "/home/secretary/.secretary.env"
CEILING = 1500


def load_key(env_file: str) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    for line in Path(env_file).read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


class Lab:
    def __init__(self, key: str, verb: str):
        self.verb = verb
        self.h = {"Authorization": f"Bearer {key}"}
        self.s = requests.Session()
        self.calls = 0
        self.cost = 0.0
        self.rows: list[dict] = []
        self.first_raw = None

    def ask(self, state, questions: dict, meta: dict | None = None,
            extra: dict | None = None, session: requests.Session | None = None) -> dict:
        if self.calls >= CEILING:
            raise SystemExit(f"ceiling of {CEILING} calls reached")
        body = {"model": MODEL, "state": state, "questions": questions}
        body.update(extra or {})
        t0 = time.perf_counter()
        r = (session or self.s).post(URL, headers=self.h, json=body, timeout=30)
        ms = (time.perf_counter() - t0) * 1000
        self.calls += 1
        row = {"ms": round(ms, 1), "http": r.status_code, **(meta or {})}
        try:
            d = r.json()
        except ValueError:
            d = {"raw": r.text[:400]}
        if r.status_code == 200:
            if self.first_raw is None:
                self.first_raw = d
            u = d.get("usage") or {}
            row["usage"] = u
            self.cost += float(u.get("cost") or 0)
            row["answers"] = d.get("answers")
        else:
            err = d.get("error") if isinstance(d, dict) else None
            row["error"] = (json.dumps(err) if err else json.dumps(d))[:4000]
        self.rows.append(row)
        return row

    def save(self, summary: dict | None = None) -> Path:
        OUT.mkdir(parents=True, exist_ok=True)
        p = OUT / f"{self.verb}.json"
        p.write_text(json.dumps({
            "verb": self.verb, "model": MODEL,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "calls": self.calls, "cost_usd": round(self.cost, 10),
            "summary": summary or {}, "first_raw_response": self.first_raw,
            "rows": self.rows}, indent=1, ensure_ascii=False))
        print(f"\n{self.verb}: {self.calls} calls, billed ${self.cost:.10f} -> {p}")
        return p


def choice_q(instructions: str, criteria: dict) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def ans(row: dict, key: str) -> dict:
    return ((row.get("answers") or {}).get(key)) or {}


# ---------------------------------------------------------------- balance
def cmd_balance(key: str, _a) -> int:
    """The key's own usage counter. Prints numbers only, never the key."""
    h = {"Authorization": f"Bearer {key}"}
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    r = requests.get("https://openrouter.ai/api/v1/key", headers=h, timeout=15)
    d = (r.json() or {}).get("data") or {}
    for k in ("usage", "usage_daily", "usage_weekly", "usage_monthly", "limit",
              "limit_remaining", "is_free_tier"):
        if k in d:
            out["key_" + k] = d[k]
    r = requests.get("https://openrouter.ai/api/v1/credits", headers=h, timeout=15)
    if r.status_code == 200:
        c = (r.json() or {}).get("data") or {}
        out["account_total_credits"] = c.get("total_credits")
        out["account_total_usage"] = c.get("total_usage")
    else:
        out["credits_http"] = r.status_code
    print(json.dumps(out, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "balance.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(out) + "\n")
    return 0


# ---------------------------------------------------------------- probe
def cmd_probe(key: str, _a) -> int:
    """Which question types and request fields the endpoint accepts. A refused
    request is the cheapest way to learn the surface: the error names what is
    valid, and a 4xx is not billed (checked: cost is only read from 200s)."""
    lab = Lab(key, "probe")
    state = {"cookie": "on the ground", "obstacle": "low spike, contact in 0.2 s"}
    crit = {"jump": "an obstacle on the ground is about to be hit",
            "none": "nothing needs pressing"}
    lab.ask(state, {"q": choice_q("What should the cookie press?", crit)},
            {"case": "baseline choice"})
    for t in ("boolean", "bool", "binary", "yes_no", "number", "integer", "float",
              "score", "scale", "rating", "multi", "multi_choice", "multiple_choice",
              "multiselect", "tags", "rank", "ranking", "text", "string", "extract"):
        q = {"type": t, "instructions": "Is an obstacle about to be hit?"}
        if t not in ("text", "string", "extract", "number", "integer", "float"):
            q["criteria"] = crit
        lab.ask(state, {"q": q}, {"case": f"type={t}"})
    # extra top-level / per-question fields: accepted, refused, or silently ignored?
    for name, extra in (("temperature", {"temperature": 0}), ("seed", {"seed": 7}),
                        ("provider", {"provider": {"sort": "latency"}}),
                        ("examples_top", {"examples": [{"state": "spike 0.1 s", "answers": {"q": "jump"}}]}),
                        ("context", {"context": "Cookie Run: a side-scrolling runner."})):
        lab.ask(state, {"q": choice_q("What should the cookie press?", crit)},
                {"case": f"extra={name}"}, extra=extra)
    for name, qx in (("q.examples", {"examples": [{"state": "spike 0.1 s", "choice": "jump"}]}),
                     ("q.default", {"default": "none"}),
                     ("q.allow_other", {"allow_other": True})):
        q = choice_q("What should the cookie press?", crit)
        q.update(qx)
        lab.ask(state, {"q": q}, {"case": name})
    # state shapes
    for name, st_ in (("state=list", ["on the ground", "spike 0.2 s"]),
                      ("state=number", 42), ("state=empty", ""),
                      ("state=nested", {"a": {"b": {"c": "spike 0.2 s"}}})):
        lab.ask(st_, {"q": choice_q("What should the cookie press?", crit)}, {"case": name})
    # option-count edges
    for n in (1, 255, 256):
        c = {f"o{i}": f"option number {i}" for i in range(n)}
        lab.ask(state, {"q": choice_q("Pick the option for this state.", c)},
                {"case": f"options={n}"})
    for r in lab.rows:
        a0 = ans(r, "q")
        print(f"{r['case']:<22} http={r['http']} "
              + (f"choice={a0.get('choice')} conf={a0.get('confidence')} "
                 f"tok={r['usage'].get('input_tokens')} cost={r['usage'].get('cost')}"
                 if r["http"] == 200 else r.get("error", "")[:150]))
    lab.save()
    return 0


# ---------------------------------------------------------------- anatomy
def cmd_anatomy(key: str, _a) -> int:
    """What the billed input tokens are made of. usage is deterministic for a
    given body, so one call per point is enough."""
    lab = Lab(key, "anatomy")
    two = {"a": "the first situation", "b": "the second situation"}
    fill = ("The cookie runs along a stone path past lanterns and plum trees. ")

    def pt(case, state, qs):
        r = lab.ask(state, qs, {"case": case})
        print(f"{case:<34} tok={r.get('usage', {}).get('input_tokens')} "
              f"ms={r['ms']:.0f} http={r['http']}")

    for n in (0, 200, 800, 3200, 12800):
        pt(f"state_chars={n}", (fill * 200)[:n], {"q": choice_q("Which one?", two)})
    for k in (2, 8, 32, 128):
        pt(f"options={k} (short meaning)", "x",
           {"q": choice_q("Which one?", {f"o{i}": f"option number {i}" for i in range(k)})})
    for m in (20, 200, 800):
        pt(f"meaning_chars={m} x2 options", "x",
           {"q": choice_q("Which one?", {"a": ("a " + fill * 20)[:m], "b": ("b " + fill * 20)[:m]})})
    for m in (20, 400):
        pt(f"instructions_chars={m}", "x", {"q": choice_q(("Which one? " + fill * 10)[:m], two)})
    state800 = (fill * 20)[:800]
    for nq in (1, 2, 4, 8, 16):
        pt(f"questions={nq} over one 800-char state", state800,
           {f"q{i}": choice_q(f"Which one, question {i}?", two) for i in range(nq)})
    pt("type=noul", state800, {"q": {"type": "noul", "instructions": "Which one?"}})
    pt("type=choice 2", state800, {"q": choice_q("Which one?", two)})
    pt("type=score 2", state800, {"q": {"type": "score", "instructions": "Which one?",
                                        "criteria": ["the first situation", "the second situation"]}})
    en = "The cookie is on the ground. A low spike is 0.2 seconds ahead. Nothing overhead."
    th = "คุกกี้อยู่บนพื้น มีหนามเตี้ยอยู่ข้างหน้า 0.2 วินาที ไม่มีอะไรอยู่ด้านบน"
    pt("state English (same meaning)", en, {"q": choice_q("Which one?", two)})
    pt("state Thai (same meaning)", th, {"q": choice_q("Which one?", two)})
    obj = {"cookie": "on the ground", "obstacle": "low spike", "contact_in_seconds": 0.2}
    pt("state as JSON object", obj, {"q": choice_q("Which one?", two)})
    pt("state as the same JSON, string", json.dumps(obj), {"q": choice_q("Which one?", two)})
    lab.save()
    return 0


# ---------------------------------------------------------------- determinism
def cmd_determinism(key: str, a) -> int:
    from jev_state_experiment import CRITERIA_BETTER, HELDOUT, QUESTION
    lab = Lab(key, "determinism")
    sc = next(s for s in HELDOUT if s[0] == "H4")   # a 'none' case near the boundary
    for i in range(10):
        lab.ask(sc[4], {"q": choice_q(QUESTION, CRITERIA_BETTER)}, {"case": "choice H4", "i": i})
    for i in range(10):
        lab.ask(sc[4], {"q": {"type": "noul", "instructions":
                              "Must the cookie press a control right now?"}}, {"case": "noul H4", "i": i})
    for i in range(10):
        lab.ask(sc[4], {"q": {"type": "score", "instructions": "How urgent is a control press?",
                              "criteria": ["not urgent at all", "somewhat urgent", "must press now"]}},
                {"case": "score H4", "i": i})
    for case in ("choice H4", "noul H4", "score H4"):
        rs = [r for r in lab.rows if r["case"] == case and r["http"] == 200]
        vals = []
        for r in rs:
            x = ans(r, "q")
            vals.append(x.get("choice") or x.get("noul") if "noul" not in case else x.get("noul"))
            if "score" in case:
                vals[-1] = x.get("score")
        confs = [ans(r, "q").get("confidence") for r in rs]
        ms = [r["ms"] for r in rs]
        print(f"{case:<10} values={vals} conf={confs} ms p50={st.median(ms):.0f} "
              f"min={min(ms):.0f} max={max(ms):.0f}")
    lab.save()
    return 0


# ---------------------------------------------------------------- concurrency
def cmd_concurrency(key: str, _a) -> int:
    lab = Lab(key, "concurrency")
    q = {"q": {"type": "noul", "instructions": "Is there an obstacle ahead?"}}
    state = {"cookie": "on the ground", "obstacle": "low spike, contact in 0.3 s"}
    lab.ask(state, q, {"case": "warm"})
    t0 = time.perf_counter()
    for i in range(20):
        lab.ask(state, q, {"case": "sequential", "i": i})
    seq_wall = time.perf_counter() - t0
    sessions = [requests.Session() for _ in range(10)]
    for s_ in sessions:   # warm each connection so the parallel run is not TLS setup
        lab.ask(state, q, {"case": "warm-parallel"}, session=s_)
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(10) as ex:
        list(ex.map(lambda i: lab.ask(state, q, {"case": "parallel10", "i": i},
                                      session=sessions[i % 10]), range(20)))
    par_wall = time.perf_counter() - t0
    for case, wall in (("sequential", seq_wall), ("parallel10", par_wall)):
        rs = [r for r in lab.rows if r["case"] == case]
        ok = [r for r in rs if r["http"] == 200]
        ms = sorted(r["ms"] for r in ok)
        print(f"{case:<11} 20 calls wall={wall:.2f}s -> {20 / wall:.1f} decisions/s  "
              f"ok={len(ok)}/20  per-call p50={st.median(ms):.0f} p90={ms[int(len(ms) * .9) - 1]:.0f} ms  "
              f"errors={[r.get('http') for r in rs if r['http'] != 200]}")
    lab.save({"seq_wall_s": seq_wall, "par_wall_s": par_wall})
    return 0


# ---------------------------------------------------------------- noul
# (id, truth yes/no, state, question). Deliberately includes the shapes Jev is
# said to be weak at: comparing numbers, counting, negation.
NOUL_SET = [
    ("Y1", True, {"cookie": "on the ground", "obstacle": "low spike, contact in 0.2 s"},
     "Is an obstacle about to reach the cookie?"),
    ("N1", False, {"cookie": "on the ground", "obstacle": "none within 2 seconds"},
     "Is an obstacle about to reach the cookie?"),
    ("Y2", True, {"screen": "Result panel", "boxes_badge": "x3"},
     "Did this round collect more than one box?"),
    ("N2", False, {"screen": "Result panel", "boxes_badge": "x1"},
     "Did this round collect more than one box?"),
    ("Y3", True, {"template": "mystery", "match_score": 0.93, "threshold": 0.95},
     "Is the match score below the threshold?"),
    ("N3", False, {"template": "mystery", "match_score": 0.97, "threshold": 0.95},
     "Is the match score below the threshold?"),
    ("Y4", True, {"coins_per_round": [9120, 10480, 9950, 11200, 9710]},
     "Did every round earn more than 9,000 coins?"),
    ("N4", False, {"coins_per_round": [9120, 10480, 8950, 11200, 9710]},
     "Did every round earn more than 9,000 coins?"),
    ("Y5", True, {"events": ["restart", "round", "restart", "round", "restart"]},
     "Were there three or more restarts?"),
    ("N5", False, {"events": ["restart", "round", "round", "round", "restart"]},
     "Were there three or more restarts?"),
    ("Y6", True, {"cookie": "in the air, rising"},
     "Is the cookie NOT on the ground?"),
    ("N6", False, {"cookie": "on the ground, running"},
     "Is the cookie NOT on the ground?"),
]


def cmd_noul(key: str, a) -> int:
    lab = Lab(key, "noul")
    for rep in range(a.reps):
        for sid, truth, state, qtext in NOUL_SET:
            lab.ask(state, {"q": {"type": "noul", "instructions": qtext}},
                    {"case": "bare", "id": sid, "truth": truth, "rep": rep})
            lab.ask(state, {"q": {"type": "noul", "instructions": qtext, "criteria": {
                "true": "Yes: the statement in the question holds for this state.",
                "false": "No: the statement in the question does not hold for this state."}}},
                    {"case": "with_criteria", "id": sid, "truth": truth, "rep": rep})
            lab.ask(state, {"q": choice_q(qtext, {"yes": "The question's statement is true here.",
                                                   "no": "The question's statement is false here."})},
                    {"case": "as_choice", "id": sid, "truth": truth, "rep": rep})
    print(f"{'id':<4}{'truth':<7}{'bare':>7}{'crit':>7}{'choice':>8}")
    for sid, truth, *_ in NOUL_SET:
        cells = []
        for case in ("bare", "with_criteria", "as_choice"):
            r = next(r for r in lab.rows if r["id"] == sid and r["case"] == case and r["rep"] == 0)
            x = ans(r, "q")
            cells.append(x.get("choice") if case == "as_choice" else x.get("noul"))
        print(f"{sid:<4}{str(truth):<7}{str(cells[0]):>7}{str(cells[1]):>7}{str(cells[2]):>8}")
    for case in ("bare", "with_criteria", "as_choice"):
        rs = [r for r in lab.rows if r["case"] == case and r["http"] == 200]
        right = 0
        for r in rs:
            x = ans(r, "q")
            said = (x.get("choice") == "yes") if case == "as_choice" else (float(x.get("noul", 0.5)) >= 0.5)
            right += said == r["truth"]
        print(f"{case:<14} right {right}/{len(rs)}  ms p50={st.median(r['ms'] for r in rs):.0f}")
    lab.save()
    return 0


# ---------------------------------------------------------------- format
def _as_kv(obj, pre=""):
    out = []
    for k, v in obj.items():
        if isinstance(v, dict):
            out += _as_kv(v, pre + k + ".")
        else:
            out.append(f"{pre}{k}: {v}")
    return out


def _as_prose(obj) -> str:
    c = obj["cookie"]
    o = obj["nearest_obstacle"]
    s = f"The cookie is {c}. "
    if o.get("type") == "none":
        s += "There is no obstacle ahead"
        if o.get("landing_spot"):
            s += f", and it will land on {o['landing_spot']}"
        return s + "."
    s += f"The nearest obstacle is a {o['type']}"
    if o.get("contact_in_seconds") is not None:
        s += f", which it reaches in {o['contact_in_seconds']} seconds"
    if o.get("cookie_would_land_on_it"):
        s += ", and the cookie would land on it"
    if o.get("cookie_would_land_inside_it"):
        s += ", and the cookie would land inside it"
    return s + "."


def cmd_format(key: str, a) -> int:
    from jev_state_experiment import CRITERIA_BETTER, HELDOUT, QUESTION
    lab = Lab(key, "format")
    fmts = {"json_object": lambda o: o, "json_string": json.dumps,
            "key_value": lambda o: "\n".join(_as_kv(o)), "prose": _as_prose}
    for rep in range(a.reps):
        for sc in HELDOUT:
            for f, fn in fmts.items():
                lab.ask(fn(sc[4]), {"q": choice_q(QUESTION, CRITERIA_BETTER)},
                        {"case": f, "id": sc[0], "truth": sc[1], "rep": rep})
    for f in fmts:
        rs = [r for r in lab.rows if r["case"] == f and r["http"] == 200]
        right = sum(ans(r, "q").get("choice") == r["truth"] for r in rs)
        tok = st.mean(r["usage"]["input_tokens"] for r in rs)
        print(f"{f:<12} right {right}/{len(rs)}  tokens mean {tok:.0f}  "
              f"conf mean {st.mean(ans(r, 'q').get('confidence') or 0 for r in rs):.2f}  "
              f"ms p50 {st.median(r['ms'] for r in rs):.0f}")
    print("\nwrong answers:")
    for r in lab.rows:
        c = ans(r, "q").get("choice")
        if c != r["truth"]:
            print(f"  {r['case']:<12} {r['id']} truth={r['truth']} said={c} conf={ans(r, 'q').get('confidence')}")
    lab.save()
    return 0


# ---------------------------------------------------------------- nav (Cookie Run)
# The residual the navigator could not name, as a site Jev could answer. The
# 2026-09-23 EP6 farm produced every shape below: the Mystery Box judged while
# still animating (N15), a still Mystery Box that only near-matched (N2), the
# boost screen's Play! mis-read (N7), an event popup with an X (N3), a Result
# panel judged mid-slide (N1). Truth is the playbook the bot now follows.
NAV_Q = "The bot cannot name the current Cookie Run screen. What should it do next?"
NAV_CRIT = {
    "wait": ("The picture is still moving (a panel sliding in, a box opening, a loading "
             "bar), or it has been unrecognised for less than 8 seconds. Example: a panel "
             "still sliding in 3 seconds after the run ended."),
    "press_best_match": ("The picture is still, has stayed unrecognised for 8 seconds or "
                         "more, and one known screen nearly matches it. Press that "
                         "screen's own button. Example: a still reward screen that nearly "
                         "matches for 10 seconds."),
    "close_popup": ("The picture is still, has stayed unrecognised for 8 seconds or more, "
                    "no known screen nearly matches, and a close X or back arrow is "
                    "showing. Example: an advert for an event with an X in its corner."),
    "restart_game": ("The game looks hung: the picture has not changed for a minute or "
                     "more, pressing buttons has already failed at least twice, and the "
                     "game has not been restarted in the last 10 minutes."),
    "ask_human": ("Something a person must handle: an update or login demand, an account "
                  "error, or restarting has already failed twice in the last 10 minutes."),
    "other": "None of the situations above describes the state.",
}
# (id, truth, computed-state, raw-state)
NAV_SET = [
    ("N1", "wait",
     {"picture_still_moving": True, "unrecognised_for_seconds": 2.5,
      "nearest_known_screen": {"name": "result", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.31, "unrecognised_s": 2.5, "top": "result 0.61 (thr 0.95)",
      "x_score": 0.12, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N2", "press_best_match",
     {"picture_still_moving": False, "unrecognised_for_seconds": 11,
      "nearest_known_screen": {"name": "mystery box", "nearly_matches": True},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.004, "unrecognised_s": 11, "top": "mystery 0.941 (thr 0.95)",
      "x_score": 0.15, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N3", "close_popup",
     {"picture_still_moving": False, "unrecognised_for_seconds": 12,
      "nearest_known_screen": {"name": "result", "nearly_matches": False},
      "close_x_showing": True, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.003, "unrecognised_s": 12, "top": "result 0.42 (thr 0.95)",
      "x_score": 0.93, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N4", "restart_game",
     {"picture_still_moving": False, "unrecognised_for_seconds": 75,
      "nearest_known_screen": {"name": "lobby", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 3, "restarts_last_10_min": 0},
     {"frame_diff": 0.0, "unrecognised_s": 75, "top": "lobby 0.38 (thr 0.95)",
      "x_score": 0.1, "presses_no_effect": 3, "restarts_10m": 0}),
    ("N5", "ask_human",
     {"picture_still_moving": False, "unrecognised_for_seconds": 80,
      "nearest_known_screen": {"name": "lobby", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 4, "restarts_last_10_min": 2},
     {"frame_diff": 0.0, "unrecognised_s": 80, "top": "lobby 0.35 (thr 0.95)",
      "x_score": 0.08, "presses_no_effect": 4, "restarts_10m": 2}),
    ("N6", "wait",
     {"picture_still_moving": False, "unrecognised_for_seconds": 4,
      "nearest_known_screen": {"name": "boost", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.002, "unrecognised_s": 4, "top": "boost 0.55 (thr 0.95)",
      "x_score": 0.2, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N7", "press_best_match",
     {"picture_still_moving": False, "unrecognised_for_seconds": 9,
      "nearest_known_screen": {"name": "boost", "nearly_matches": True},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.001, "unrecognised_s": 9, "top": "boost 0.93 (thr 0.95)",
      "x_score": 0.18, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N8", "ask_human",
     {"picture_still_moving": False, "unrecognised_for_seconds": 20,
      "text_on_screen": "Update required. Please update the game from the store.",
      "nearest_known_screen": {"name": "lobby", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.001, "unrecognised_s": 20,
      "ocr": "Update required. Please update the game from the store.",
      "top": "lobby 0.30 (thr 0.95)", "x_score": 0.1, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N9", "close_popup",
     {"picture_still_moving": False, "unrecognised_for_seconds": 15,
      "nearest_known_screen": {"name": "lobby", "nearly_matches": False},
      "close_x_showing": True, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.002, "unrecognised_s": 15, "top": "lobby 0.52 (thr 0.95)",
      "x_score": 0.96, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N10", "wait",
     {"picture_still_moving": True, "unrecognised_for_seconds": 40,
      "nearest_known_screen": {"name": "lobby", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.22, "unrecognised_s": 40, "top": "lobby 0.33 (thr 0.95)",
      "x_score": 0.05, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N11", "restart_game",
     {"picture_still_moving": False, "unrecognised_for_seconds": 65,
      "nearest_known_screen": {"name": "result", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 2, "restarts_last_10_min": 0,
      "last_restart_minutes_ago": 30},
     {"frame_diff": 0.0, "unrecognised_s": 65, "top": "result 0.40 (thr 0.95)",
      "x_score": 0.1, "presses_no_effect": 2, "restarts_10m": 0, "last_restart_min_ago": 30}),
    ("N12", "ask_human",
     {"picture_still_moving": False, "unrecognised_for_seconds": 14,
      "text_on_screen": "Sign in with Google to continue.",
      "nearest_known_screen": {"name": "lobby", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.001, "unrecognised_s": 14, "ocr": "Sign in with Google to continue.",
      "top": "lobby 0.28 (thr 0.95)", "x_score": 0.1, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N13", "press_best_match",
     {"picture_still_moving": False, "unrecognised_for_seconds": 10,
      "nearest_known_screen": {"name": "result", "nearly_matches": True},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.002, "unrecognised_s": 10, "top": "result 0.948 (thr 0.95)",
      "x_score": 0.2, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N14", "close_popup",
     {"picture_still_moving": False, "unrecognised_for_seconds": 9,
      "nearest_known_screen": {"name": "boost", "nearly_matches": False},
      "close_x_showing": True, "failed_presses": 1, "restarts_last_10_min": 0},
     {"frame_diff": 0.001, "unrecognised_s": 9, "top": "boost 0.47 (thr 0.95)",
      "x_score": 0.91, "presses_no_effect": 1, "restarts_10m": 0}),
    ("N15", "wait",
     {"picture_still_moving": True, "unrecognised_for_seconds": 12,
      "nearest_known_screen": {"name": "mystery box", "nearly_matches": True},
      "close_x_showing": False, "failed_presses": 0, "restarts_last_10_min": 0},
     {"frame_diff": 0.27, "unrecognised_s": 12, "top": "mystery 0.94 (thr 0.95)",
      "x_score": 0.1, "presses_no_effect": 0, "restarts_10m": 0}),
    ("N16", "restart_game",
     {"picture_still_moving": False, "unrecognised_for_seconds": 90,
      "nearest_known_screen": {"name": "mystery box", "nearly_matches": False},
      "close_x_showing": False, "failed_presses": 5, "restarts_last_10_min": 0},
     {"frame_diff": 0.0, "unrecognised_s": 90, "top": "mystery 0.51 (thr 0.95)",
      "x_score": 0.1, "presses_no_effect": 5, "restarts_10m": 0}),
]


def _score_rows(rows, key="q"):
    ok = [r for r in rows if r["http"] == 200]
    return sum(ans(r, key).get("choice") == r["truth"] for r in ok), len(ok)


def cmd_nav(key: str, a) -> int:
    lab = Lab(key, "nav")
    for rep in range(a.reps):
        for sid, truth, comp, raw in NAV_SET:
            lab.ask(comp, {"q": choice_q(NAV_Q, NAV_CRIT)},
                    {"case": "computed", "id": sid, "truth": truth, "rep": rep})
            lab.ask(raw, {"q": choice_q(NAV_Q, NAV_CRIT)},
                    {"case": "raw", "id": sid, "truth": truth, "rep": rep})
    for case in ("computed", "raw"):
        rs = [r for r in lab.rows if r["case"] == case]
        right, n = _score_rows(rs)
        print(f"{case:<9} right {right}/{n}  tokens mean "
              f"{st.mean(r['usage']['input_tokens'] for r in rs if r['http'] == 200):.0f}  "
              f"ms p50 {st.median(r['ms'] for r in rs):.0f}")
    print("\nper id (rep 0): computed | raw")
    for sid, truth, *_ in NAV_SET:
        cells = []
        for case in ("computed", "raw"):
            r = next(r for r in lab.rows if r["id"] == sid and r["case"] == case and r["rep"] == 0)
            x = ans(r, "q")
            cells.append(f"{x.get('choice')}{'✓' if x.get('choice') == truth else '✗'}({x.get('confidence')})")
        print(f"  {sid:<4} {truth:<17} {cells[0]:<28} {cells[1]}")
    lab.save()
    return 0


# ---------------------------------------------------------------- batch
def cmd_batch(key: str, a) -> int:
    """Several decisions in ONE call: does it cost less, and is it still right?"""
    from jev_state_experiment import CRITERIA_BETTER, HELDOUT, QUESTION
    lab = Lab(key, "batch")
    for rep in range(a.reps):
        for sc in HELDOUT:
            lab.ask(sc[4], {"q": choice_q(QUESTION, CRITERIA_BETTER)},
                    {"case": "cookie_single", "id": sc[0], "truth": sc[1], "rep": rep})
        state = {sc[0]: sc[4] for sc in HELDOUT}
        qs = {sc[0]: choice_q(f"Which control should the cookie in situation {sc[0]} press right now?",
                              CRITERIA_BETTER) for sc in HELDOUT}
        lab.ask(state, qs, {"case": "cookie_batch7", "rep": rep,
                            "truths": {sc[0]: sc[1] for sc in HELDOUT}})
        state = {s[0]: s[2] for s in NAV_SET}
        qs = {s[0]: choice_q(f"Screen {s[0]}: the bot cannot name it. What should it do next?",
                             NAV_CRIT) for s in NAV_SET}
        lab.ask(state, qs, {"case": "nav_batch16", "rep": rep,
                            "truths": {s[0]: s[1] for s in NAV_SET}})
        # one state, three questions of three types about it
        sc = HELDOUT[0]
        lab.ask(sc[4], {"control": choice_q(QUESTION, CRITERIA_BETTER),
                        "danger": {"type": "noul", "instructions": "Will the cookie be hurt if it does nothing?"},
                        "urgency": {"type": "score", "instructions": "How urgent is a press?",
                                    "criteria": ["not urgent", "soon", "right now"]}},
                {"case": "one_state_3types", "rep": rep})
        for qk, q in (("control", choice_q(QUESTION, CRITERIA_BETTER)),
                      ("danger", {"type": "noul", "instructions": "Will the cookie be hurt if it does nothing?"}),
                      ("urgency", {"type": "score", "instructions": "How urgent is a press?",
                                   "criteria": ["not urgent", "soon", "right now"]})):
            lab.ask(sc[4], {qk: q}, {"case": "one_state_3types_split", "q": qk, "rep": rep})

    single = [r for r in lab.rows if r["case"] == "cookie_single"]
    right, n = _score_rows(single)
    print(f"cookie 7 single calls: right {right}/{n}  tokens/call "
          f"{st.mean(r['usage']['input_tokens'] for r in single):.0f}  "
          f"sum tokens per 7 = {sum(r['usage']['input_tokens'] for r in single) / a.reps:.0f}  "
          f"ms p50 {st.median(r['ms'] for r in single):.0f}")
    for case in ("cookie_batch7", "nav_batch16"):
        for r in [r for r in lab.rows if r["case"] == case]:
            if r["http"] != 200:
                print(case, "HTTP", r["http"], r.get("error", "")[:300])
                continue
            got = {k: (v or {}).get("choice") for k, v in (r["answers"] or {}).items()}
            ok = sum(got.get(k) == t for k, t in r["truths"].items())
            wrong = {k: (got.get(k), t) for k, t in r["truths"].items() if got.get(k) != t}
            print(f"{case} rep{r['rep']}: right {ok}/{len(r['truths'])}  tokens "
                  f"{r['usage']['input_tokens']}  ms {r['ms']:.0f}  wrong(said,truth)={wrong}")
    for r in lab.rows:
        if r["case"].startswith("one_state_3types"):
            print(f"{r['case']:<24} {r.get('q', 'all'):<8} tokens {r['usage'].get('input_tokens')}  "
                  f"ms {r['ms']:.0f}  answers {json.dumps(r['answers'])[:220]}")
    lab.save()
    return 0


# ---------------------------------------------------------------- options
# Skill routing: the org's own 47 skills are a real option set with real,
# overlapping descriptions. Truth is the skill a C-level would reach for.
ROUTE_SET = [
    ("อัปโหลดไฟล์นี้ขึ้น Google Drive ให้หน่อย จัดเข้าโฟลเดอร์ให้ถูก", "gdrive-filing"),
    ("C: drive on winbox is almost full, what can we delete safely?", "disk-hygiene"),
    ("เริ่มงานวันนี้ เปิด session ดูงานค้างกับ deadline ก่อน", "session-open"),
    ("wrap up this session and file what is still open", "session-close"),
    ("review the DEV's branch for task-1234 before I merge it", "cto-merge-checklist"),
    ("ทำภาพ reference ตัวละคร หน้าตรง ด้านข้าง ด้านหลัง", "character-reference-sheet"),
    ("send this announcement to the family LINE group", "line-messaging"),
    ("ขอจองเครื่อง winbox ใช้ 2 ชั่วโมง อย่าให้บอทแย่ง", "winbox-pc-lease"),
    ("switch this session's model to Opus at xhigh effort", "session-change-model"),
    ("this caption reads like ChatGPT wrote it, make it sound human", "de-ai-ify"),
    ("label the new Cookie Run frames for training", "cookierun-labeling"),
    ("ส่งงานแก้ test เล็ก ๆ นี้ให้ Jules ทำแทน DEV", "jules-ops"),
    ("เขียนสคริปต์คลิป Black Liquidity ตอนใหม่เรื่องทองคำ", "blackliquidity-script"),
    ("restart the terminal so the updated Claude binary loads", "terminal-restart"),
    ("generate 20 more takes on Higgsfield while the plan is unlimited", "higgsfield-unlimited-gen"),
    ("ทำใบแจ้งหนี้ให้ลูกค้า MoonieX เดือนนี้", "mooniex-finance"),
]


def _skills(desc_chars: int | None) -> dict:
    import re
    root = Path(__file__).resolve().parent.parent / ".claude" / "skills"
    out = {}
    for p in sorted(root.glob("*/SKILL.md")):
        t = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|^---)", t, re.S | re.M)
        d = " ".join((m.group(1) if m else p.parent.name).split()).strip("\"'>- ")
        out[p.parent.name] = d[:desc_chars] if desc_chars else d
    return out


def cmd_options(key: str, a) -> int:
    import random
    lab = Lab(key, "options")
    full, short = _skills(None), _skills(160)
    names = sorted(full)
    q = "Which skill should handle this request?"
    for req, truth in ROUTE_SET:
        assert truth in full, truth
        rnd = random.Random(truth)
        others = [n for n in names if n != truth]
        for k in (4, 12, 24):
            pick = rnd.sample(others, k - 1) + [truth]
            lab.ask(req, {"q": choice_q(q, {n: short[n] for n in sorted(pick)})},
                    {"case": f"K={k} short", "truth": truth, "k": k})
        lab.ask(req, {"q": choice_q(q, short)}, {"case": "K=47 short", "truth": truth, "k": 47})
        lab.ask(req, {"q": choice_q(q, full)}, {"case": "K=47 full", "truth": truth, "k": 47})
        lab.ask(req, {"q": choice_q(q, {**short, "other": "No skill covers this request."})},
                {"case": "K=47 short+other", "truth": truth, "k": 48})
    # latency/cost at the cardinality cap, accuracy not meaningful (synthetic)
    fake = {f"option_{i:03d}": f"Handles requests about topic number {i} and nothing else." for i in range(254)}
    for i, (req, truth) in enumerate(ROUTE_SET[:4]):
        lab.ask(req, {"q": choice_q(q, {**fake, truth: short[truth]})},
                {"case": "K=255 synthetic", "truth": truth, "k": 255})
    order = ["K=4 short", "K=12 short", "K=24 short", "K=47 short", "K=47 short+other",
             "K=47 full", "K=255 synthetic"]
    for case in order:
        rs = [r for r in lab.rows if r["case"] == case]
        right, n = _score_rows(rs)
        ok = [r for r in rs if r["http"] == 200]
        print(f"{case:<17} right {right}/{n}  tokens mean {st.mean(r['usage']['input_tokens'] for r in ok):.0f}  "
              f"$ mean {st.mean(float(r['usage']['cost']) for r in ok):.8f}  ms p50 {st.median(r['ms'] for r in ok):.0f}  "
              f"conf mean {st.mean(ans(r, 'q').get('confidence') or 0 for r in ok):.2f}")
    print("\nwrong at K=47 short / full:")
    for r in lab.rows:
        if r["case"] in ("K=47 short", "K=47 full", "K=47 short+other") and ans(r, "q").get("choice") != r["truth"]:
            print(f"  {r['case']:<17} truth={r['truth']:<26} said={ans(r, 'q').get('choice')} "
                  f"conf={ans(r, 'q').get('confidence')}")
    lab.save()
    return 0


# ---------------------------------------------------------------- count
def cmd_count(key: str, a) -> int:
    """Where counting / comparing breaks. noul passed 24/24 on lists of 5; the
    vendor says errors 'grow with scale'. Truth always sits one off the line."""
    import random
    lab = Lab(key, "count")
    rnd = random.Random(23)
    for rep in range(a.reps):
        for n in (5, 20, 60, 150):
            for want_yes in (True, False):
                line = max(2, n // 5)
                k = line + 1 if want_yes else line - 1
                ev = ["restart"] * k + ["round"] * (n - k)
                rnd.shuffle(ev)
                lab.ask({"events": ev}, {"q": {"type": "noul", "instructions":
                        f"Are there more than {line} restarts in the events?"}},
                        {"case": f"count n={n}", "truth": want_yes, "rep": rep})
                vals = [rnd.randint(1000, 9800) for _ in range(n)]
                if want_yes:
                    vals[rnd.randrange(n)] = 10150
                lab.ask({"coins_per_round": vals}, {"q": {"type": "noul", "instructions":
                        "Did any round earn more than 10,000 coins?"}},
                        {"case": f"max n={n}", "truth": want_yes, "rep": rep})
        for want_first, (d1, d2) in ((True, ("2026-09-03", "2026-09-21")),
                                     (False, ("2026-10-02", "2026-09-28")),
                                     (True, ("2025-12-30", "2026-01-02")),
                                     (False, ("2026-09-23 07:51", "2026-09-23 07:09"))):
            lab.ask({"farm_parked_at": d1, "last_restart_at": d2}, {"q": {"type": "noul",
                    "instructions": "Was the farm parked before the last restart?"}},
                    {"case": "date order", "truth": want_first, "rep": rep})
    cases = []
    for r in lab.rows:
        if r["case"] not in cases:
            cases.append(r["case"])
    for c in cases:
        rs = [r for r in lab.rows if r["case"] == c and r["http"] == 200]
        right = sum((float(ans(r, "q").get("noul", .5)) >= .5) == r["truth"] for r in rs)
        vals = [ans(r, "q").get("noul") for r in rs]
        print(f"{c:<12} right {right}/{len(rs)}  noul={vals}  tokens mean "
              f"{st.mean(r['usage']['input_tokens'] for r in rs):.0f}")
    lab.save()
    return 0


# ---------------------------------------------------------------- calibration
def cmd_calibration(_key: str, _a) -> int:
    """Pool every labelled choice answer from the saved runs: is 'confidence'
    worth anything as a gate? No calls."""
    pts = []
    for f in ("format", "nav", "options", "batch"):
        p = OUT / f"{f}.json"
        if not p.exists():
            continue
        for r in json.loads(p.read_text())["rows"]:
            if r.get("http") != 200:
                continue
            if "truth" in r and r.get("answers") and "q" in r["answers"]:
                x = r["answers"]["q"]
                pts.append((f, x.get("confidence") or 0, x.get("choice") == r["truth"]))
            elif "truths" in r:
                for k, t in r["truths"].items():
                    x = (r["answers"] or {}).get(k) or {}
                    pts.append((f + "-batch", x.get("confidence") or 0, x.get("choice") == t))
    print(f"{len(pts)} labelled answers")
    for lo, hi in ((0, .5), (.5, .7), (.7, .85), (.85, .95), (.95, 1.01)):
        b = [ok for _, c, ok in pts if lo <= c < hi]
        if b:
            print(f"confidence [{lo:.2f},{hi:.2f}): n={len(b):<4} accuracy {sum(b) / len(b):.2f}")
    for thr in (0.5, 0.7, 0.8, 0.9):
        kept = [ok for _, c, ok in pts if c >= thr]
        if kept:
            print(f"gate conf>={thr}: keeps {len(kept)}/{len(pts)} ({len(kept) / len(pts):.0%}), "
                  f"accuracy of kept {sum(kept) / len(kept):.2f}, "
                  f"wrong answers let through {len(kept) - sum(kept)}")
    return 0


VERBS = {"balance": cmd_balance, "probe": cmd_probe, "anatomy": cmd_anatomy,
         "determinism": cmd_determinism, "concurrency": cmd_concurrency,
         "noul": cmd_noul, "format": cmd_format, "nav": cmd_nav, "batch": cmd_batch,
         "options": cmd_options, "count": cmd_count, "calibration": cmd_calibration}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=sorted(VERBS))
    ap.add_argument("--env-file", default=ENV_FILE)
    ap.add_argument("--reps", type=int, default=1)
    a = ap.parse_args()
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))   # jev_state_experiment
    key = "" if a.verb == "calibration" else load_key(a.env_file)
    if not key and a.verb != "calibration":
        print("no OPENROUTER_API_KEY")
        return 2
    return VERBS[a.verb](key, a)


if __name__ == "__main__":
    raise SystemExit(main())
