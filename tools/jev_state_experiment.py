#!/usr/bin/env python3
"""jev_state_experiment.py -- does a more detailed state make Jev more accurate?

The CEO's hypothesis (2026-09-22): the pit case Jev got wrong 16 times out of 16
failed because the input was too thin, and richer input would fix it.

TypeSafe's own docs say two things that pull in opposite directions:

  "Jev is not a calculator and does not count reliably"
  "A large state full of irrelevant detail costs accuracy too. Filter first."

So "more detail" is really two different interventions, and this runs them
apart instead of letting one mask the other:

  L1  terse       -- object + distance, nothing else
  L2  medium      -- what jev_bench.py sent (the 16/16 failure came from here)
  L3  verbose     -- L2 plus everything else on screen: coins, score, pet, HP.
                     MORE detail, none of it relevant. Docs predict worse.
  L4  computed    -- only what matters, with the arithmetic already done:
                     time-to-contact, "will land inside the pit". This is what a
                     vision model upstream can compute and Jev cannot.
  L5  computed + better criteria -- L4's state, but the OPTION descriptions are
                     rewritten the way the docs recommend: situations instead
                     of degrees, one concrete example each, and an explicit
                     'other'. Isolates the criteria from the state.

Six scenarios with an unambiguous right answer. Two of them (S5, S6) are the
kind a thin state cannot even express: already clearing the spike, and a spike
that is real but too far away to jump for yet.

    python tools/jev_state_experiment.py --reps 2 --out results.json
"""
import argparse
import json
import statistics as st
import time
from pathlib import Path

import requests

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"
QUESTION = "Which control should the cookie press right now?"
MAX_CALLS = 120

CRITERIA_ORIGINAL = {
    "jump": "Press jump now: an obstacle at ground level is close enough to hit.",
    "slide": "Press slide now: an overhead obstacle is close enough to hit.",
    "double_jump": "Jump again while airborne: a pit or tall obstacle needs more height.",
    "none": "Press nothing: no obstacle is close enough to need a response yet.",
}
# The docs: "describe situations rather than degrees", one RELEVANT example each
# ("an unrelated example changed almost nothing"), and an explicit other "so the
# model can say nothing fits instead of picking the closest wrong thing".
CRITERIA_BETTER = {
    "jump": ("The cookie is on the ground and an obstacle sitting on the ground "
             "will be reached within about 0.35 seconds. Example: a low spike, "
             "contact in 0.24 seconds."),
    "slide": ("An obstacle hanging overhead, too low to run under, will be "
              "reached within about 0.35 seconds. Example: a hanging bar, contact "
              "in 0.11 seconds."),
    "double_jump": ("The cookie is already in the air and, without more height, "
                    "will land in a pit or on an obstacle. Example: falling, and "
                    "the landing point is inside a pit."),
    "none": ("Nothing needs pressing yet: either no obstacle arrives within about "
             "0.35 seconds, or the cookie will clear it as it is. Example: a spike "
             "0.9 seconds away."),
    "other": "None of the situations above describes the state.",
}

NOISE = ("score 4,812,330. coins this run 18,204. bonus-time gauge 62%. "
         "HP 71%. pet Tater Trader hovering behind the cookie. two coin "
         "jellies above, one bear jelly ahead at head height. background: "
         "Primeval Forest, dusk. combi bonus Mini Magnet active. ")

# answer, L1, L2, L4(object)
SCENARIOS = [
    ("S1", "jump",
     "spike 210px.",
     "cookie: on ground, not in air. next obstacle: low spike 210px ahead. "
     "after that: high bar 480px ahead. scroll speed: 880 px/s.",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "low spike on the ground", "contact_in_seconds": 0.24}}),
    ("S2", "double_jump",
     "pit 140px.",
     "cookie: in air, falling. next obstacle: pit 140px ahead, width 90px. "
     "after that: none within 600px. scroll speed: 880 px/s.",
     {"cookie": "in the air, falling, touches down in 0.15 seconds",
      "nearest_obstacle": {"type": "pit in the ground",
                           "cookie_would_land_inside_it": True}}),
    ("S3", "slide",
     "bar 95px.",
     "cookie: on ground. next obstacle: high bar 95px ahead (clearance too low "
     "to jump under). after that: low spike 330px ahead. scroll speed: 910 px/s.",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "bar hanging overhead, too low to run under",
                           "contact_in_seconds": 0.10}}),
    ("S4", "none",
     "clear.",
     "cookie: on ground. no obstacle within 1050px. scroll speed: 880 px/s.",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "none", "contact_in_seconds": None}}),
    ("S5", "none",
     "spike below.",
     "cookie: in air, rising, 140px above ground. next obstacle: low spike "
     "directly below, height 60px. scroll speed: 880 px/s.",
     {"cookie": "in the air, rising, already higher than the obstacle below",
      "nearest_obstacle": {"type": "low spike on the ground",
                           "cookie_will_clear_it": True}}),
    ("S6", "none",
     "spike 790px.",
     "cookie: on ground. next obstacle: low spike 790px ahead. scroll speed: "
     "880 px/s.",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "low spike on the ground", "contact_in_seconds": 0.90}}),
]


# HELD-OUT. The first run scored L5 12/12 -- but CRITERIA_BETTER's examples reuse
# the exact test values (the 'none' example IS S6's 0.9 s spike, 'jump' IS S1's
# 0.24 s, 'double_jump' IS S2's pit). That is the answer key sitting in the
# question. These scenarios use values and situations the examples never show,
# so a win here is the rule generalising, not the example being recognised.
# S-shape: (id, truth, unused, unused, L4-object)
HELDOUT = [
    ("H1", "jump", "", "",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "low spike on the ground", "contact_in_seconds": 0.18}}),
    ("H2", "slide", "", "",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "bar hanging overhead, too low to run under",
                           "contact_in_seconds": 0.28}}),
    ("H3", "double_jump", "", "",
     {"cookie": "in the air, falling, touches down in 0.12 seconds",
      "nearest_obstacle": {"type": "cluster of spikes on the ground",
                           "cookie_would_land_on_it": True}}),
    ("H4", "none", "", "",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "low spike on the ground", "contact_in_seconds": 0.55}}),
    ("H5", "none", "", "",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "bar hanging overhead, too low to run under",
                           "contact_in_seconds": 0.62}}),
    ("H6", "none", "", "",
     {"cookie": "in the air, falling, touches down in 0.20 seconds",
      "nearest_obstacle": {"type": "none", "landing_spot": "flat ground"}}),
    ("H7", "jump", "", "",
     {"cookie": "on the ground",
      "nearest_obstacle": {"type": "tall stack of crates on the ground",
                           "contact_in_seconds": 0.30}}),
]


def build(level: str, sc) -> tuple[object, dict]:
    _, _, l1, l2, l4 = sc
    if level == "L1":
        return l1, CRITERIA_ORIGINAL
    if level == "L2":
        return l2, CRITERIA_ORIGINAL
    if level == "L3":
        return NOISE + l2, CRITERIA_ORIGINAL
    if level == "L4":
        return l4, CRITERIA_ORIGINAL
    if level == "L5":
        return l4, CRITERIA_BETTER
    raise ValueError(level)


def load_key(env_file: str) -> str:
    for line in Path(env_file).read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--env-file", default="/home/secretary/.secretary.env")
    ap.add_argument("--out", required=True)
    ap.add_argument("--heldout", action="store_true",
                    help="L4 vs L5 on scenarios whose values the examples never show")
    a = ap.parse_args()

    global SCENARIOS
    if a.heldout:
        SCENARIOS = HELDOUT
    levels = ["L4", "L5"] if a.heldout else ["L1", "L2", "L3", "L4", "L5"]
    n = len(levels) * len(SCENARIOS) * a.reps
    if n > MAX_CALLS:
        print(f"refusing {n} calls (ceiling {MAX_CALLS})")
        return 2
    key = load_key(a.env_file)
    if not key:
        print("no key")
        return 2
    print(f"about to make {n + 1} paid calls; worst case ${(n + 1) * 700 / 1e6 * 0.042:.8f}",
          flush=True)

    s = requests.Session()
    h = {"Authorization": f"Bearer {key}"}
    s.post(URL, headers=h, json={"model": MODEL, "state": "warm", "questions": {
        "q": {"type": "choice", "instructions": "warm", "criteria": {"a": "a", "b": "b"}}}},
        timeout=20)

    rows = []
    for rep in range(a.reps):
        for sc in SCENARIOS:
            for lv in levels:
                state, crit = build(lv, sc)
                body = {"model": MODEL, "state": state, "questions": {
                    "control": {"type": "choice", "instructions": QUESTION, "criteria": crit}}}
                t0 = time.perf_counter()
                r = s.post(URL, headers=h, json=body, timeout=20)
                ms = (time.perf_counter() - t0) * 1000
                row = {"rep": rep, "scenario": sc[0], "truth": sc[1], "level": lv,
                       "ms": round(ms, 1), "http": r.status_code}
                if r.status_code == 200:
                    d = r.json()
                    ans = (d.get("answers") or {}).get("control") or {}
                    u = d.get("usage") or {}
                    row.update(choice=ans.get("choice"), confidence=ans.get("confidence"),
                               p_truth=(ans.get("probabilities") or {}).get(sc[1]),
                               tokens_in=u.get("input_tokens"), cost=u.get("cost"))
                else:
                    row["error"] = r.text[:160]
                rows.append(row)

    Path(a.out).write_text(json.dumps(rows, indent=1))

    print(f"\n{'level':<5}{'right':>9}{'p(truth)':>11}{'conf':>8}{'tokens':>8}"
          f"{'$/call':>15}{'ms p50':>9}")
    for lv in levels:
        rs = [r for r in rows if r["level"] == lv and r.get("choice")]
        right = sum(r["choice"] == r["truth"] for r in rs)
        pt = [r["p_truth"] or 0 for r in rs]
        cf = [r["confidence"] for r in rs if r.get("confidence") is not None]
        tk = [r["tokens_in"] for r in rs if r.get("tokens_in")]
        cs = [float(r["cost"]) for r in rs if r.get("cost") is not None]
        print(f"{lv:<5}{right:>4}/{len(rs):<4}{st.mean(pt):>11.3f}{st.mean(cf):>8.3f}"
              f"{st.mean(tk):>8.0f}{st.mean(cs):>15.10f}{st.median(r['ms'] for r in rs):>9.1f}")

    print("\nper scenario (choice at each level, rep 0):")
    for sc in SCENARIOS:
        cells = []
        for lv in levels:
            r = next((r for r in rows if r["rep"] == 0 and r["scenario"] == sc[0]
                      and r["level"] == lv), {})
            mark = "✓" if r.get("choice") == sc[1] else "✗"
            cells.append(f"{lv}:{r.get('choice')}{mark}")
        print(f"  {sc[0]} truth={sc[1]:<12} " + "  ".join(cells))
    total = sum(float(r["cost"]) for r in rows if r.get("cost") is not None)
    print(f"\nspent on measured calls: ${total:.10f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
