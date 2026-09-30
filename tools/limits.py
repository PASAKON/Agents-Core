"""Quota limits management tool.

Handles loading, validating, rendering, and atomically setting quota limits
and reserve thresholds for AI provider buckets.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import load_plans

LIMITS_PATH = ROOT / "config" / "limits.yaml"

DEFAULT_LIMITS: dict[str, dict[str, int | float]] = {
    "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
    "codex": {"plan_usd": 20, "reserve_pct": 20, "min_5h_pct": 0},
    "agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    "agy-claude": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
}

ORDER = ["claude", "codex", "agy-gemini", "agy-claude"]

HEADER = """# Quota limits and reserve thresholds per bucket.
# plan_usd: bucket's subscription cost in USD (scales seed cost estimates).
# reserve_pct: weekly quota % kept back (for claude: protects C-level sessions).
# min_5h_pct: minimum 5h/daily quota % required; bucket skipped while below this.
# change with: .venv/bin/python tools/limits.py set <bucket>.<key> <value>
"""


def _fmt_num(val: int | float | None) -> str:
    if val is None:
        return "0"
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def load_limits(path: Path | str | None = None) -> dict[str, dict]:
    """Load limits mapping from YAML file or return DEFAULT_LIMITS if missing."""
    p = Path(path) if path is not None else LIMITS_PATH
    if not p.is_file():
        return copy.deepcopy(DEFAULT_LIMITS)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "buckets" in data and isinstance(data["buckets"], dict):
            return data["buckets"]
        if isinstance(data, dict) and data:
            return data
    except Exception:
        pass
    return copy.deepcopy(DEFAULT_LIMITS)


def validate(limits: dict[str, dict], cfg: dict | None = None) -> list[str]:
    """Validate limits against plans.yaml buckets and valid key/range specifications.

    Errors returned if:
    - bucket not found in plans.yaml `buckets:`
    - keys other than plan_usd (>0), reserve_pct (0..100), min_5h_pct (0..100)
    """
    if cfg is None:
        try:
            cfg = load_plans()
        except Exception:
            cfg = {}

    allowed_buckets = set((cfg.get("buckets") or {}).keys())
    allowed_keys = {"plan_usd", "reserve_pct", "min_5h_pct"}
    errors: list[str] = []

    if not isinstance(limits, dict):
        return ["limits must be a dictionary"]

    for bucket, row in limits.items():
        if allowed_buckets and bucket not in allowed_buckets:
            errors.append(f"bucket {bucket!r} not in plans.yaml buckets")
        if not isinstance(row, dict):
            errors.append(f"bucket {bucket!r} entry must be a dictionary")
            continue

        for k in row:
            if k not in allowed_keys:
                errors.append(f"bucket {bucket!r} has invalid key {k!r}")

        for req in ("plan_usd", "reserve_pct", "min_5h_pct"):
            if req not in row:
                errors.append(f"bucket {bucket!r} missing key {req!r}")

        if "plan_usd" in row:
            v = row["plan_usd"]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
                errors.append(f"bucket {bucket!r} plan_usd must be a number > 0, got {v!r}")

        if "reserve_pct" in row:
            v = row["reserve_pct"]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v > 100:
                errors.append(f"bucket {bucket!r} reserve_pct must be between 0 and 100, got {v!r}")

        if "min_5h_pct" in row:
            v = row["min_5h_pct"]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v > 100:
                errors.append(f"bucket {bucket!r} min_5h_pct must be between 0 and 100, got {v!r}")

    return errors


def render(limits: dict[str, dict]) -> str:
    """Render limits as YAML with header comment and one flow line per bucket."""
    lines = [HEADER.rstrip(), "buckets:"]
    sorted_buckets = sorted(
        limits.keys(),
        key=lambda b: (ORDER.index(b) if b in ORDER else 999, b),
    )
    for b in sorted_buckets:
        row = limits[b]
        p = _fmt_num(row.get("plan_usd"))
        r = _fmt_num(row.get("reserve_pct"))
        m = _fmt_num(row.get("min_5h_pct"))
        b_key = f"  {b}:"
        lines.append(f"{b_key:<14} {{plan_usd: {p},  reserve_pct: {r}, min_5h_pct: {m}}}")
    return "\n".join(lines) + "\n"


def set_limit(
    bucket: str,
    key: str,
    value: str | int | float,
    path: Path | str | None = None,
) -> dict[str, dict]:
    """Atomically set a limit key on bucket. Validate first; invalid raises ValueError."""
    try:
        val = float(value)
        if val.is_integer():
            parsed_val = int(val)
        else:
            parsed_val = val
    except (ValueError, TypeError):
        raise ValueError(f"invalid numeric value: {value!r}")

    p = Path(path) if path is not None else LIMITS_PATH
    current = load_limits(p)
    if bucket not in current:
        raise ValueError(f"unknown bucket: {bucket!r}")
    if key not in ("plan_usd", "reserve_pct", "min_5h_pct"):
        raise ValueError(f"invalid limit key: {key!r}")

    updated = copy.deepcopy(current)
    updated[bucket][key] = parsed_val

    errors = validate(updated)
    if errors:
        raise ValueError("; ".join(errors))

    p.parent.mkdir(parents=True, exist_ok=True)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, encoding="utf-8") as f:
            temp_file = Path(f.name)
            f.write(render(updated))
        os.replace(temp_file, p)
    except Exception:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise

    return updated


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    cmd = argv[0] if argv else "show"

    if cmd == "show":
        limits = load_limits()
        sorted_buckets = sorted(
            limits.keys(),
            key=lambda b: (ORDER.index(b) if b in ORDER else 999, b),
        )
        header = f"{'bucket':<12} {'plan_usd':>8} {'reserve_pct':>11} {'min_5h_pct':>10}"
        print(header)
        for b in sorted_buckets:
            row = limits[b]
            print(f"{b:<12} {_fmt_num(row.get('plan_usd')):>8} {_fmt_num(row.get('reserve_pct')):>11} {_fmt_num(row.get('min_5h_pct')):>10}")
        return 0

    elif cmd == "validate":
        limits = load_limits()
        errors = validate(limits)
        if errors:
            for err in errors:
                print(err)
            return 1
        return 0

    elif cmd == "set":
        if len(argv) < 3:
            print("usage: limits.py set <bucket>.<key> <value>", file=sys.stderr)
            return 1
        target = argv[1]
        val_str = argv[2]
        if "." not in target:
            print("target must be in format <bucket>.<key>", file=sys.stderr)
            return 1
        bucket, key = target.split(".", 1)
        try:
            set_limit(bucket, key, val_str)
            return 0
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
