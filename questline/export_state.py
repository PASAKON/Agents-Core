#!/usr/bin/env python3
"""Questline data layer — merges org tasks.db + a LungNote personal-todos
snapshot into questline/state.json for the grid renderer.

Run: python3 export_state.py
"""
import json
import sqlite3
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS_DB = ROOT.parent / "state" / "tasks.db"
LIFE_SNAPSHOT = ROOT / "data" / "personal_todos_snapshot.json"
ENV_PATH = ROOT / ".env"
OUT_PATH = ROOT / "state.json"

HQ_TIER_THRESHOLDS = [(0, 1), (20, 2), (60, 3), (150, 4), (400, 5)]

DONE_STATUSES = {"done", "merged"}
BACKLOG_STATUSES = {"pending", "review", "in_progress"}
DEV_ROLES = {
    "developer", "web_designer", "backend_dev", "frontend_dev",
    "devops_engineer", "tester", "qa", "security_engineer",
}
GROWTH_ROLES = {
    "content_strategist", "ads_manager", "prompt_engineer", "data_analyst",
}

TIER_THRESHOLDS = [(0, 1), (5, 2), (15, 3), (40, 4), (100, 5)]


def tier_for(completed: int) -> int:
    tier = 1
    for threshold, level in TIER_THRESHOLDS:
        if completed >= threshold:
            tier = level
    return tier


def load_tasks():
    con = sqlite3.connect(str(TASKS_DB))
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT role, status, updated_at FROM tasks").fetchall()
    con.close()
    return rows


def district_stats(rows, roles):
    filtered = [r for r in rows if r["role"] in roles]
    status_counts = Counter(r["status"] for r in filtered)
    completed = sum(status_counts[s] for s in DONE_STATUSES)
    backlog = sum(status_counts[s] for s in BACKLOG_STATUSES)

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_completed = 0
    for r in filtered:
        if r["status"] not in DONE_STATUSES or not r["updated_at"]:
            continue
        try:
            ts = datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            recent_completed += 1

    return {
        "completed": completed,
        "backlog": backlog,
        "tier": tier_for(completed),
        "recent_completed_7d": recent_completed,
        "belt_speed": round(recent_completed / 7, 2),
    }


def life_district_stats():
    snap = json.loads(LIFE_SNAPSHOT.read_text())
    completed = snap["done_count"]

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_completed = 0
    for ts_str in snap.get("completed_timestamps", []):
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            recent_completed += 1

    return {
        "completed": completed,
        "backlog": snap["pending_count"],
        "tier": tier_for(completed),
        "recent_completed_7d": recent_completed,
        "belt_speed": round(recent_completed / 7, 2),
        "note": "snapshot is a manual re-fetch via LungNote MCP tool, not a live DB connection — see README Phase 4",
        "fetched_at": snap["fetched_at"],
        "recent_pending": snap["recent_pending"],
    }


def load_env():
    if not ENV_PATH.exists():
        return {}
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def fetch_exact_count(base_url, service_key, table, query):
    """PostgREST exact-count trick: Range 0-0 + Prefer:count=exact returns the
    total in Content-Range without transferring matching rows."""
    url = f"{base_url}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers={
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Prefer": "count=exact",
        "Range-Unit": "items",
        "Range": "0-0",
    })
    with urllib.request.urlopen(req, timeout=10) as res:
        content_range = res.headers.get("Content-Range", "")
    return int(content_range.split("/")[-1]) if "/" in content_range else 0


def fetch_distribution_kpis():
    """Real org throughput, reused from the same tables that already back
    mooniex-webapp /api/office/automation-events (read-only counts only)."""
    env = load_env()
    base_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")
    if not base_url or not service_key:
        return None

    # "Z" suffix, not "+00:00" — the "+" needs URL-encoding or PostgREST's
    # date parser sees it decoded back to a literal space and rejects it
    # (confirmed via the actual 400 body: "...132664 00:00").
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    kpis = {}
    queries = {
        "news_posts_7d": ("webapp_content_posts", f"select=id&automated=eq.true&type=eq.news&published_at=gte.{cutoff}"),
        "images_7d": ("webapp_image_generations", f"select=id&created_at=gte.{cutoff}"),
        "social_connections_active": ("webapp_social_connections", "select=id&status=eq.active"),
    }
    for name, (table, query) in queries.items():
        try:
            kpis[name] = fetch_exact_count(base_url, service_key, table, query)
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            kpis[name] = None
            kpis[f"{name}_error"] = str(e)
    return kpis


def hq_tier_for(total):
    tier = 1
    for threshold, level in HQ_TIER_THRESHOLDS:
        if total >= threshold:
            tier = level
    return tier


def main():
    rows = load_tasks()
    kpis = fetch_distribution_kpis()
    if kpis:
        throughput = sum(v for k, v in kpis.items() if not k.endswith("_error") and v)
        hq = {
            "level": hq_tier_for(throughput),
            "kpis": kpis,
            "note": "news/images = last 7d count, social = current active connections — read-only, same tables as mooniex-webapp /api/office/automation-events",
        }
    else:
        hq = {
            "level": 1,
            "kpis": None,
            "note": "questline/.env missing SUPABASE_URL / SUPABASE_SERVICE_KEY — HQ stubbed at level 1",
        }

    state = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "districts": {
            "dev": district_stats(rows, DEV_ROLES),
            "growth": district_stats(rows, GROWTH_ROLES),
            "life": life_district_stats(),
        },
        "hq": hq,
    }
    OUT_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
