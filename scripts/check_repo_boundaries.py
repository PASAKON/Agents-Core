#!/usr/bin/env python3
"""Validate MoonieX's tracked top-level repository boundaries."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "config" / "repository-boundaries.yaml"


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("zones"), dict):
        raise ValueError("manifest must contain a 'zones' mapping")
    return manifest


def tracked_top_level(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        line.strip().replace("\\", "/").split("/", 1)[0]
        for line in result.stdout.splitlines()
        if line.strip()
    }


def validate(manifest: dict, tracked: Iterable[str]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    migrate: list[str] = []
    for zone_name, zone in manifest["zones"].items():
        if not isinstance(zone, dict) or not isinstance(zone.get("paths"), list):
            raise ValueError(f"zone {zone_name!r} must contain a paths list")
        for item in zone["paths"]:
            owners.setdefault(str(item), []).append(zone_name)
            if zone.get("lifecycle") == "migrate":
                migrate.append(str(item))

    tracked_set = set(tracked)
    duplicates = sorted(path for path, zones in owners.items() if len(zones) > 1)
    unclassified = sorted(tracked_set - owners.keys())
    stale = sorted(owners.keys() - tracked_set)

    patterns = manifest.get("policy", {}).get("new_root_file_patterns", [])
    explicitly_legacy = {
        path
        for zone in manifest["zones"].values()
        if zone.get("lifecycle") == "migrate"
        for path in zone.get("paths", [])
    }
    prohibited_new = sorted(
        path
        for path in tracked_set
        if any(fnmatch.fnmatch(path, pattern) for pattern in patterns)
        and path not in explicitly_legacy
    )
    return {
        "unclassified": unclassified,
        "duplicates": duplicates,
        "stale": stale,
        "prohibited_new": prohibited_new,
        "migration_backlog": sorted(set(migrate) & tracked_set),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="also fail while migration debt remains")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        report = validate(load_manifest(args.manifest), tracked_top_level(args.root))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"boundary check error: {exc}", file=sys.stderr)
        return 2

    failures = report["unclassified"] + report["duplicates"] + report["prohibited_new"]
    if args.strict:
        failures += report["stale"] + report["migration_backlog"]

    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        for key in ("unclassified", "duplicates", "prohibited_new", "stale"):
            values = report[key]
            print(f"{key}: {', '.join(values) if values else 'none'}")
        print(f"migration backlog: {len(report['migration_backlog'])} classified path(s)")
        print("result: FAIL" if failures else "result: PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
