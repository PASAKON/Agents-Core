"""Read-only, model-free resource summary: python -m tools.host_fill [--json]."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import config, mesh
from tools import node_dispatch

HOSTS = ("contabo", "winbox", "mac")


def fill(facts: dict) -> tuple[float | None, str | None, list[str]]:
    """Return the maximum known sensor, explicitly naming missing readings."""
    values = {}
    for name, free_key, total_key in (
        ("ram", "ram_free_gb", "ram_total_gb"),
        ("disk", "free_gb", "disk_total_gb"),
    ):
        try:
            free, total = float(facts[free_key]), float(facts[total_key])
            if math.isfinite(total) and math.isfinite(free) and total > 0 and 0 <= free <= total:
                values[name] = 100 * (1 - free / total)
        except (KeyError, TypeError, ValueError):
            pass
    try:
        cpu = facts.get("cpu_pct")
        if cpu is None:
            cpu = float(facts["load_per_core"]) * 100
        cpu = float(cpu)
        if math.isfinite(cpu) and cpu >= 0:
            values["cpu"] = cpu
    except (KeyError, TypeError, ValueError):
        pass
    missing = [key for key in ("ram", "cpu", "disk") if key not in values]
    if not values:
        return None, None, missing
    highest = max(values, key=values.get)
    return round(values[highest], 1), highest, missing


def probe(host: str) -> dict:
    row = {"name": host, "online": False, "fill_pct": None, "highest": None,
           "running": None, "max_workers": config.host(host)["max_workers"],
           "ram_free_gb": None, "missing": ["ram", "cpu", "disk"]}
    try:
        if host == config.self_host():
            facts = node_dispatch._fill_facts()
            try:
                facts["running"] = node_dispatch._running_workers(host)
            except Exception:
                facts["running"] = None
        else:
            reply = mesh.dispatch(host, "probe", timeout=10)
            if not reply.get("ok") or not isinstance(reply.get("result"), dict):
                return row
            facts = reply["result"]
        pct, highest, missing = fill(facts)
        row.update(online=True, fill_pct=pct, highest=highest, missing=missing,
                   running=facts.get("running"), ram_free_gb=facts.get("ram_free_gb"))
    except (mesh.MeshUnreachable, OSError, ValueError):
        pass
    return row


def collect() -> list[dict]:
    with ThreadPoolExecutor(max_workers=3) as pool:
        return list(pool.map(probe, HOSTS))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = collect()
    if args.json:
        print(json.dumps(rows, allow_nan=False))
    else:
        for row in rows:
            pct = row["fill_pct"]
            usage = "unknown" if pct is None else f'{pct:.1f}% ({row["highest"]})'
            missing = f' · missing: {", ".join(row["missing"])}' if row["missing"] else ""
            ram = row["ram_free_gb"]
            ram = "unknown" if ram is None else f"{ram:.2f}"
            print(f'{row["name"]} · {"online" if row["online"] else "offline"} · '
                  f'{usage} · {row["running"] if row["running"] is not None else "?"}/'
                  f'{row["max_workers"]} · ram_free_gb={ram}{missing}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
