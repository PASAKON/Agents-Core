"""Spawn resource gate (org restructure P2, plan §7.3).

Before a new session starts on this host -- a Project Head (scripts/spawn-ph.sh)
or a worker (tools/delegate.py) -- the host must have at least
`ORG_SPAWN_RAM_FLOOR_MB` (800) MB of RAM available. Disk uses the host bands
in storage-policy.yaml; ORG_SPAWN_DISK_MAX_PCT explicitly overrides them.
Red refuses all sessions; orange refuses video/download kinds. One session costs about
330-520 MB (measured on Contabo 2026-10-13: 325-525 MB per session tree), and
on 2026-10-01 one OOM kill took every Contabo session down at once.

Off unless the host flag ORG_SPAWN_GATE is on (`/etc/org-flags/ORG_SPAWN_GATE` or
`ORG_SPAWN_GATE=1`; lib/org_flags): `check()` then returns None without
reading anything, so a host that has not opted in behaves exactly as before.

RAM is MemAvailable from /proc/meminfo, the kernel's own estimate of what a new
process can get without swapping (`free -m`'s "available" column). Where there
is no /proc/meminfo (the Mac, Windows) RAM is unknown and the RAM half passes:
the hosts this gate exists for are Linux. Disk is computed the way `df` prints
Use%: used / (used + available to unprivileged users), on `/` unless told
otherwise.

CLI, for shell launchers:
    python -m lib.resource_gate check [--path /]   # exit 0 ok, 1 refused (reason on stderr)
    python -m lib.resource_gate show  [--path /]   # one JSON line, exit 0
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import shutil
import math
from tools.storage_policy import host_band
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RAM_FLOOR_MB = 800
DEFAULT_DISK_MAX_PCT = 90.0
MEMINFO = Path("/proc/meminfo")


def gate_on() -> bool:
    """True when this host gates spawns on resources (host flag ORG_SPAWN_GATE,
    lib/org_flags: the file /etc/org-flags/ORG_SPAWN_GATE or the env)."""
    from lib import org_flags
    return org_flags.on("ORG_SPAWN_GATE")


def _env_number(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def ram_floor_mb() -> float:
    return _env_number("ORG_SPAWN_RAM_FLOOR_MB", DEFAULT_RAM_FLOOR_MB)


def disk_max_pct() -> float:
    return _env_number("ORG_SPAWN_DISK_MAX_PCT", DEFAULT_DISK_MAX_PCT)


def ram_available_mb(meminfo: Path = MEMINFO) -> int | None:
    """MemAvailable in MB, or None when this host has no /proc/meminfo."""
    try:
        text = meminfo.read_text(encoding="ascii", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            try:
                return int(parts[1]) // 1024   # the kernel reports kB
            except (IndexError, ValueError):
                return None
    return None


def disk_used_pct(path: str = "/") -> float | None:
    """Use% of the filesystem holding `path`, as `df` computes it."""
    try:
        st = os.statvfs(path)
    except (OSError, AttributeError):   # AttributeError: Windows has no statvfs
        try:
            import shutil
            u = shutil.disk_usage(path)
        except OSError:
            return None
        return 100.0 * u.used / u.total if u.total else None
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    avail = st.f_bavail * st.f_frsize
    return 100.0 * used / (used + avail) if used + avail else None


@dataclass(frozen=True)
class Reading:
    ram_available_mb: int | None
    disk_used_pct: float | None
    ram_floor_mb: float
    disk_max_pct: float
    band: str | None = None
    kind: str = ''

    def refusal(self) -> str | None:
        """Why a spawn must wait, or None when it may go."""
        reasons = []
        if self.ram_available_mb is not None and self.ram_available_mb < self.ram_floor_mb:
            reasons.append(f"RAM available {self.ram_available_mb} MB is under the "
                           f"{self.ram_floor_mb:g} MB floor")
        if self.band == 'red' or (self.band == 'orange' and any(k in self.kind.lower() for k in ('video', 'download'))):
            reasons.append(f'disk {self.band}: {self.kind or "all spawns"} must wait')
        if self.band is None and self.disk_used_pct is not None and self.disk_used_pct > self.disk_max_pct:
            reasons.append(f"disk {self.disk_used_pct:.0f}% used is over the "
                           f"{self.disk_max_pct:g}% ceiling")
        if not reasons:
            return None
        return ("spawn refused by the resource gate (plan §7.3): " + "; ".join(reasons)
                + ". Free memory or disk first (close an idle session, ALL_Rules_DiskHygiene).")

    def as_dict(self) -> dict:
        return {
            "ram_available_mb": self.ram_available_mb,
            "disk_used_pct": None if self.disk_used_pct is None else round(self.disk_used_pct, 1),
            "ram_floor_mb": self.ram_floor_mb,
            "disk_max_pct": self.disk_max_pct,
            "band": self.band,
        }


def read(path: str = "/", *, meminfo: Path = MEMINFO, kind: str = '', host=None) -> Reading:
    override = _env_number('ORG_SPAWN_DISK_MAX_PCT', float('nan'))
    band = None
    if not math.isfinite(override):
        band = host_band(shutil.disk_usage(path).free / 1024**3, host=host)
    return Reading(ram_available_mb(meminfo), disk_used_pct(path), ram_floor_mb(), disk_max_pct(), band, kind)


def check(path: str = "/", *, meminfo: Path = MEMINFO, kind: str = '', host=None) -> str | None:
    """None when a spawn may go (or the gate is off), else the refusal text."""
    if not gate_on():
        return None
    return read(path, meminfo=meminfo, kind=kind, host=host).refusal()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lib.resource_gate")
    ap.add_argument("verb", choices=("check", "show"))
    ap.add_argument("--path", default="/")
    ap.add_argument('--kind', default='')
    ap.add_argument('--host', default=None)
    args = ap.parse_args(argv)
    if args.verb == "show":
        r = read(args.path, kind=args.kind, host=args.host)
        print(json.dumps({**r.as_dict(), "gate_on": gate_on(), "refusal": r.refusal()}))
        return 0
    why = check(args.path, kind=args.kind, host=args.host)
    if why:
        print(why, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
