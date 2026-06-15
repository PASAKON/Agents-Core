#!/usr/bin/env python3
"""Week-1 funnel review — READ-ONLY pull from webapp_user_events (Supabase PostgREST).
Reads creds from webapp/.env.local, never prints secret values. No writes."""
import urllib.request, urllib.error, json
from pathlib import Path

ENV = Path("/Users/gob/Projects/mooniex-webapp/.env.local")
SINCE = "2026-06-05T00:00:00Z"

def load_env(p):
    d = {}
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        v = v.strip().strip('"').strip("'")
        v = v.replace("\\n", "").replace("\\r", "").strip()  # strip literal \n (echo-written env)
        d[k.strip()] = v
    return d

env = load_env(ENV)
URL = env["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/")
KEY = env["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

def req(path, prefer=None):
    h = dict(H)
    if prefer:
        h["Prefer"] = prefer
    r = urllib.request.Request(f"{URL}/rest/v1/{path}", headers=h)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return resp.read().decode(), resp.headers.get("Content-Range", "")

def count(event):
    _, cr = req(f"webapp_user_events?select=id&event_name=eq.{event}&created_at=gte.{SINCE}&limit=1",
                prefer="count=exact")
    tot = cr.split("/")[-1] if "/" in cr else ""
    return int(tot) if tot.isdigit() else 0

def distinct_sessions(event):
    body, _ = req(f"webapp_user_events?select=session_id&event_name=eq.{event}&created_at=gte.{SINCE}&limit=50000")
    return len({r.get("session_id") for r in json.loads(body) if r.get("session_id")})

try:
    funnel = ["page_view", "tool_viewed", "tool_used", "rebate_calc_completed", "auth_signup"]
    surfaces = ["indicator_viewed", "indicator_access_clicked", "hero_signup_clicked",
                "cta_indicator_clicked", "rebate_poster_clicked", "link_in_bio_clicked"]
    print(f"=== FUNNEL — since {SINCE} ===")
    fc = {}
    for e in funnel:
        fc[e] = count(e)
        flag = "  ⚠️ ZERO" if fc[e] == 0 else ""
        print(f"  {e:26} {fc[e]:>6}{flag}")
    print("\n=== NEW SURFACES (live 2026-06-11 — directional) ===")
    for e in surfaces:
        n = count(e)
        flag = "  ⚠️ ZERO (instrumentation?)" if n == 0 else ""
        print(f"  {e:26} {n:>6}{flag}")

    pv_sess = distinct_sessions("page_view")
    tu_sess = distinct_sessions("tool_used")
    print(f"\n=== DISTINCT SESSIONS ===")
    print(f"  page_view sessions : {pv_sess}")
    print(f"  tool_used sessions : {tu_sess}")
    if pv_sess:
        print(f"  logged-out tool_used rate (ADR metric) ≈ {tu_sess}/{pv_sess} = {100*tu_sess/pv_sess:.1f}%")

    body, _ = req(f"webapp_user_events?select=event_name,event_props&event_name=in.(tool_viewed,tool_used)&created_at=gte.{SINCE}&limit=50000")
    rows = json.loads(body)
    tools = ["pip-calculator", "position-size", "risk-reward", "rebate-calc", "xau-alert", "economic-calendar"]
    tally = {t: {"viewed": 0, "used": 0} for t in tools}
    other = {}
    for r in rows:
        slug = str((r.get("event_props") or {}).get("tool", "")).strip()
        if not slug:
            continue
        d = tally.get(slug)
        if d is None:
            d = other.setdefault(slug, {"viewed": 0, "used": 0})
        if r["event_name"] == "tool_viewed":
            d["viewed"] += 1
        elif r["event_name"] == "tool_used":
            d["used"] += 1
    print(f"\n=== PER-TOOL (6 baselines) — total {len(rows)} tool events ===")
    for t in tools:
        d = tally[t]
        conv = f"{100*d['used']/d['viewed']:.0f}%" if d["viewed"] else "—"
        zero = "  ⚠️ ZERO" if d["viewed"] == 0 and d["used"] == 0 else ""
        print(f"  {t:20} viewed={d['viewed']:>4}  used={d['used']:>4}  use/view={conv}{zero}")
    if other:
        print("  -- unexpected slugs (not in 6 baselines) --")
        for s, d in sorted(other.items()):
            print(f"  {s:20} viewed={d['viewed']:>4}  used={d['used']:>4}")

    # Completion-depth lives in the OTHER table (webapp_user_activity_log),
    # emitted by useToolTracking as tool_submit/tool_result (the ADR's "completed").
    print(f"\n=== USAGE DEPTH — webapp_user_activity_log (tool_result = the real 'completed') ===")
    body, _ = req(f"webapp_user_activity_log?select=event_name,tags&event_name=in.(tool_submit,tool_result)&created_at=gte.{SINCE}&limit=50000")
    arows = json.loads(body)
    dtally = {}
    for r in arows:
        tool = str((r.get("tags") or {}).get("tool", "")).strip()
        if not tool:
            continue
        d = dtally.setdefault(tool, {"submit": 0, "result": 0})
        if r["event_name"] == "tool_submit":
            d["submit"] += 1
        elif r["event_name"] == "tool_result":
            d["result"] += 1
    print(f"  ({len(arows)} depth events total)")
    for tool in sorted(dtally):
        d = dtally[tool]
        print(f"  {tool:20} submit={d['submit']:>4}  result/completed={d['result']:>4}")
    if not dtally:
        print("  ⚠️ no tool_submit/tool_result rows — completion not tracked, or table/tag wrong")
except urllib.error.HTTPError as e:
    print(f"❌ HTTP {e.code} {e.reason} — {e.read().decode()[:200]}")
    print("→ creds/access issue = BLOCKER (รอ verify key)")
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")
