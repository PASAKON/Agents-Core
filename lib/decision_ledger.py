"""Append-only JSONL ledger for tools/decide.py.

One row per decide() call, written to state/decisions/<YYYY-MM>.jsonl —
runtime state (gitignored), never source. Read back by
`python tools/decide.py report` and by the openrouter provider's monthly
budget check (month_paid_cost_usd).

LEDGER_DIR is a module global re-read on every call (not captured at import
time), matching the LOG_PATH pattern in tools/flow_shoot.py / its test suite
— tests monkeypatch `decision_ledger.LEDGER_DIR` to a tmp_path and every
function here picks that up without extra plumbing.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER_DIR = ROOT / "state" / "decisions"


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _ledger_path(month: str | None = None) -> Path:
    return LEDGER_DIR / f"{month or _current_month()}.jsonl"


def append(row: dict, month: str | None = None) -> str:
    """Write one ledger row, atomically appended. Returns the row's
    ledger_id (generated here if the caller didn't already set one)."""
    ledger_id = row.get("ledger_id") or uuid.uuid4().hex[:16]
    row = {**row, "ledger_id": ledger_id}
    path = _ledger_path(month)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    return ledger_id


def read_month(month: str | None = None) -> list[dict]:
    path = _ledger_path(month)
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def month_paid_cost_usd(month: str | None = None) -> float:
    """Sum of cost_usd across every row this month — the figure the
    openrouter provider's budget gate compares DECIDE_BUDGET_USD against.
    Includes $0 rule/jev rows too (they just add nothing), which keeps this
    a plain "spend so far" total rather than a provider-filtered one."""
    return sum(float(r.get("cost_usd") or 0.0) for r in read_month(month))


def summarize_month(month: str | None = None) -> dict[str, dict]:
    """Per-site rollup for `tools/decide.py report`: calls, provider mix,
    tokens in/out, cost, counterfactual, and the derived 'saved' column."""
    out: dict[str, dict] = {}
    for r in read_month(month):
        site = r.get("site", "?")
        s = out.setdefault(site, {
            "calls": 0, "provider_mix": {}, "tokens_in": 0, "tokens_out": 0,
            "cost_usd": 0.0, "counterfactual_usd": 0.0,
        })
        s["calls"] += 1
        prov = r.get("provider", "?")
        s["provider_mix"][prov] = s["provider_mix"].get(prov, 0) + 1
        s["tokens_in"] += int(r.get("tokens_in") or 0)
        s["tokens_out"] += int(r.get("tokens_out") or 0)
        s["cost_usd"] += float(r.get("cost_usd") or 0.0)
        s["counterfactual_usd"] += float(r.get("counterfactual_usd") or 0.0)
    for s in out.values():
        s["saved_usd"] = s["counterfactual_usd"] - s["cost_usd"]
    return out
