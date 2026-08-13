#!/usr/bin/env python3
"""UserPromptSubmit hook: cadenced memory self-nudge (ADR 0019 §1).

Every N turns, injects ONE line asking whether anything this session should be
persisted to memory. It does not call a model and does not write memory itself
— it emits the line; the C-level decides. That is the whole design: memory is
written only when the model thinks of it, so facts that should have been saved
are lost silently. This makes the question routine instead of lucky.

Shape deliberately matches scripts/hook-recall.py: gated on CTO_SESSION=1,
reads the event JSON from stdin, prints to stdout, and fails silent with
return 0 on any error — a hook must never block a prompt.

Cadence & floor:
  - N (MEMORY_NUDGE_N, default 10): nudge every N turns.
  - FLOOR (MEMORY_NUDGE_FLOOR, default 8): never nudge below this many turns,
    independent of N. Guards short exchanges when N is lowered — a 3-turn chat
    never gets nagged even with N=3.

Counter persistence: a small JSON at state/session-nudge-counters.json keyed by
session id. NOT in tasks.db (IRON §30 governs that schema). The counter file is
a runtime artifact; like state/session-search.db it should not be committed.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUNTER_PATH = ROOT / "state" / "session-nudge-counters.json"

DEFAULT_N = 10
FLOOR = 8


def _load_counters() -> dict:
    try:
        with open(COUNTER_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_counters(counters: dict) -> None:
    tmp = COUNTER_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(counters, fh)
    os.replace(tmp, COUNTER_PATH)


def main() -> int:
    if os.environ.get("CTO_SESSION") != "1":
        return 0

    n = DEFAULT_N
    floor = FLOOR
    try:
        n = int(os.environ.get("MEMORY_NUDGE_N", DEFAULT_N))
        floor = int(os.environ.get("MEMORY_NUDGE_FLOOR", FLOOR))
    except ValueError:
        pass
    if n < 1:
        n = DEFAULT_N

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    session_id = payload.get("session_id") or payload.get("sessionId") or ""
    if not session_id:
        return 0

    try:
        counters = _load_counters()
        turn = int(counters.get(session_id, 0)) + 1
        counters[session_id] = turn
        _save_counters(counters)
    except Exception:
        # A miscounted nudge is harmless; a blocked prompt is not. Stay silent.
        return 0

    if turn < floor or turn % n != 0:
        return 0

    # One line. Every line here is paid for on every turn of every session
    # (ADR 0016), so keep it short and self-explaining.
    print(
        f"[memory nudge] turn {turn} — if anything this session is worth keeping "
        f"in memory, write it now. (auto every {n} turns; you decide)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
