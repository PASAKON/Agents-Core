"""Disk watch -- the yellow and orange bands of config/storage-policy.yaml,
acted on every watchdog tick instead of only when someone spawns a worker.

ADR 0030's gauge promises two things nobody ran on a schedule:
  yellow (< 20 GB free): notify the CEO once a day;
  orange (< 10 GB free): delete REBUILD automatically.
Before this file the only caller was tools/delegate.py at spawn time, and only
for the box doing the spawn -- a machine where nobody spawned could fill up
silently (Contabo sat at 7.8 GB free on 2026-09-28 with no letter to anyone).

`check()` runs once per runners/watchdog.py scan_once tick, on every machine
that runs the watchdog (the Mac's launchd job, Contabo's systemd unit):
  - orange or red: run the REBUILD reclaim (tools/storage_reclaim via
    delegate._run_storage_reclaim), at most once an hour;
  - yellow or worse: one letter to SomPong (lib.ceo_report.notify_ceo) a day,
    or straight away when the band got worse than the last letter said.
Never deletes anything itself beyond what storage_reclaim already may (its
REBUILD tier inside in-scope task worktrees).

    python -m tools.disk_watch            # one check, prints the result

ORG_DISK_WATCH=off turns the pass into a no-op (the test suite sets it, so no
test run ever reclaims a real worktree or writes the CEO a letter).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import storage_policy  # noqa: E402

STATE_PATH = ROOT / "state" / "disk_watch_state.json"
POLICY_PATH = ROOT / "config" / "storage-policy.yaml"
NOTIFY_EVERY = timedelta(hours=24)
RECLAIM_EVERY = timedelta(hours=1)
_RANK = {"green": 0, "yellow": 1, "orange": 2, "red": 3}


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _when(raw) -> datetime | None:
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None


def _host() -> str:
    try:
        from lib.config import self_host
        return self_host()
    except Exception:  # noqa: BLE001
        return "this machine"


def letter(host: str, free_gb: float, band: str, freed_bytes: int) -> str:
    reclaimed = (f" The automatic REBUILD reclaim freed {freed_bytes / 1024 ** 3:.1f} GB."
                 if freed_bytes else "")
    return (
        f"[disk-watch] {host}: {free_gb:.1f} GB free ({band} band, "
        f"config/storage-policy.yaml).{reclaimed} Below 5 GB no new worker spawns "
        f"there. What may go is in ALL_Rules_DiskHygiene (Green list runs without "
        f"asking; anything else needs your go)."
    )


def check(*, now: datetime | None = None, free_gb: float | None = None,
          state_path: Path = STATE_PATH, policy_path: Path = POLICY_PATH,
          notify=None, reclaim=None, host: str | None = None) -> dict:
    """One pass. `free_gb`, `notify(body)`, `reclaim() -> (bytes, count)` and
    `host` are injectable for tests. Returns what it saw and did."""
    if os.environ.get("ORG_DISK_WATCH", "on").lower() in ("0", "off", "false"):
        return {"skipped": "ORG_DISK_WATCH=off"}
    now = now or datetime.now(timezone.utc)
    policy = storage_policy.load(str(policy_path))
    free = shutil.disk_usage("/").free / 1024 ** 3 if free_gb is None else free_gb
    band = storage_policy.band(free, policy)
    host = host or _host()
    state = _load(state_path)
    result = {"host": host, "free_gb": round(free, 2), "band": band,
              "reclaimed_bytes": 0, "notified": False}

    if band in ("orange", "red"):
        last = _when(state.get("last_reclaim_at"))
        if last is None or now - last >= RECLAIM_EVERY:
            if reclaim is None:
                from tools import delegate
                reclaim = delegate._run_storage_reclaim
            try:
                freed, _count = reclaim()
                result["reclaimed_bytes"] = int(freed)
            except Exception as e:  # noqa: BLE001 -- a failed reclaim still alerts
                result["reclaim_error"] = str(e)
            state["last_reclaim_at"] = now.isoformat(timespec="seconds")

    if band == "green":
        state.pop("last_band", None)
    else:
        last = _when(state.get("last_notify_at"))
        worse = _RANK[band] > _RANK.get(state.get("last_band", "green"), 0)
        if worse or last is None or now - last >= NOTIFY_EVERY:
            if notify is None:
                from lib.ceo_report import notify_ceo
                notify = lambda body: notify_ceo(body, "watchdog", "disk-watch")  # noqa: E731
            notify(letter(host, free, band, result["reclaimed_bytes"]))
            result["notified"] = True
            state["last_notify_at"] = now.isoformat(timespec="seconds")
            state["last_band"] = band

    _save(state_path, state)
    return result


def main() -> int:
    print(json.dumps(check(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
