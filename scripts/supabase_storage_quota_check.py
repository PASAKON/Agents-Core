"""Alert-only Supabase Storage quota checker.

Read-only guardrail requested in GH mooniex-webapp#85 step 5 ("consider a
guardrail so this doesn't silently recur") — the project has hit its
Free-tier storage quota twice already (2026-07-13, escalated 2026-07-19)
and each time was only caught by the CEO hitting a broken login page.

This script NEVER deletes anything. It sums object sizes in a bucket via
the Storage REST API and prints a WARNING if usage crosses a threshold
(default 80% of the 1GB free-tier cap) so a cron can catch it before the
project gets restricted again — deleting/archiving old media stays a
human-reviewed action (see the existing LungNote purge task), same
reasoning as merge_task's touches gate: catch the problem automatically,
require a human for the destructive fix.

NOTE ON LIVE VERIFICATION: as of 2026-07-20 the project (tlokhyqpthvxabweekps)
is CURRENTLY restricted (exceed_storage_size_quota, confirmed via a live
`GET /storage/v1/bucket` -> HTTP 402) — the same outage GH #85 tracks. That
means this script's real-usage path cannot be exercised against live data
right now; the API itself is blocked until the restriction lifts (tracked
LungNote item, ~2026-07-21). scripts/test_supabase_storage_quota_check.py
proves the parsing/threshold/402-handling logic with mocked HTTP responses;
re-run this script for real once the restriction lifts to get a live number.

Usage:
    python scripts/supabase_storage_quota_check.py [--bucket NAME] [--threshold-pct N]

Suggested cron (daily, alert-only — add to crontab or a systemd timer):
    0 9 * * * cd /Users/gob/MoonieXHQ/Agents/Core && \
        source .venv/bin/activate && \
        python scripts/supabase_storage_quota_check.py >> state/logs/storage-quota-check.log 2>&1
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

CLAUDEFLOW_ENV = Path("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")
DEFAULT_BUCKET = "claudeflow-media"
DEFAULT_QUOTA_BYTES = 1 * 1024 * 1024 * 1024  # 1 GiB, Supabase free-tier cap
DEFAULT_THRESHOLD_PCT = 80


def _load_env(path: Path) -> dict[str, str]:
    """Minimal .env reader — no python-dotenv dependency, strips inline # comments."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.split(" #", 1)[0].strip().strip('"').strip("'")
        out[key.strip()] = val
    return out


class RestrictedError(Exception):
    """Project is already restricted (402) — the alert condition itself."""


def bucket_usage_bytes(base_url: str, service_key: str, bucket: str) -> int:
    """Sum object sizes in `bucket` via the Storage REST API. Read-only —
    only ever issues GET/POST list calls, never DELETE."""
    headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
    total = 0
    offset = 0
    limit = 1000
    while True:
        r = requests.post(
            f"{base_url}/storage/v1/object/list/{bucket}",
            headers=headers,
            json={"limit": limit, "offset": offset, "sortBy": {"column": "name", "order": "asc"}},
            timeout=30,
        )
        if r.status_code == 402:
            raise RestrictedError(r.json().get("message", "storage quota exceeded"))
        r.raise_for_status()
        page = r.json()
        if not page:
            break
        for obj in page:
            meta = obj.get("metadata") or {}
            total += int(meta.get("size") or 0)
        if len(page) < limit:
            break
        offset += limit
    return total


def check(bucket: str, threshold_pct: int) -> int:
    """Returns process exit code: 0 = OK, 1 = WARNING (over threshold),
    2 = CRITICAL (already restricted), 3 = could not check (missing creds/error)."""
    env = _load_env(CLAUDEFLOW_ENV)
    base_url = os.environ.get("SUPABASE_URL") or env.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_SERVICE_KEY")
    if not base_url or not service_key:
        print(f"ERROR: missing SUPABASE_URL/SUPABASE_SERVICE_KEY (checked env + {CLAUDEFLOW_ENV})")
        return 3

    threshold_bytes = DEFAULT_QUOTA_BYTES * threshold_pct // 100
    try:
        used = bucket_usage_bytes(base_url, service_key, bucket)
    except RestrictedError as e:
        print(f"CRITICAL: project already restricted — {e}")
        print("Action: see GH mooniex-webapp#85 (archive/purge plan already tracked there).")
        return 2
    except requests.RequestException as e:
        print(f"ERROR: could not reach Storage API — {e}")
        return 3

    used_mb = used / (1024 * 1024)
    pct = used / DEFAULT_QUOTA_BYTES * 100
    print(f"bucket={bucket} used={used_mb:.1f}MB ({pct:.1f}% of {DEFAULT_QUOTA_BYTES // (1024*1024)}MB quota)")
    if used >= threshold_bytes:
        print(f"WARNING: {bucket} is over {threshold_pct}% of quota — archive/purge before it hits 100% and restricts the project again.")
        return 1
    print("OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", default=DEFAULT_BUCKET)
    ap.add_argument("--threshold-pct", type=int, default=DEFAULT_THRESHOLD_PCT)
    args = ap.parse_args()
    return check(args.bucket, args.threshold_pct)


if __name__ == "__main__":
    sys.exit(main())
