#!/usr/bin/env python3
"""
SessionStart deadline surfacer — Mooniex virtual org.

Prints LungNote to-dos that are OVERDUE or due soon so EVERY session sees the
CEO's live deadlines at start, without depending on anyone remembering to run
/session-open. Wired as a SessionStart hook in .claude/settings.json.

Why this exists
---------------
LungNote is the CEO's to-do store, but nothing loads it automatically — a
session only sees it if /session-open (or a manual list_todos) runs. On
2026-07-16 that gap nearly buried a hard, load-bearing deadline (the 21 Jul
Supabase purge, GH mooniex-webapp#85): miss the day and prod login loops. This
hook makes the deadlines unmissable — they are injected as context at every
session start.

Design
------
- LungNote is backed by its OWN Supabase project (qkaxvockysyazmtormvf),
  SEPARATE from the mooniex app project (tlokhyqpthvxabweekps). So this keeps
  working even while the mooniex project is quota-restricted (402).
- Reads creds from mcp/lungnote-mcp/.env (SUPABASE_URL, SUPABASE_SECRET_KEY,
  LUNGNOTE_USER_ID). Never prints them.
- Fails OPEN and quiet: any error prints one short line and exits 0, so a
  LungNote outage never blocks a session from starting.
- Surfacing is NOT acting. It lists deadlines; whether to work a deadline is
  always the CEO's decision (stated in the nudge line).
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, "mcp", "lungnote-mcp", ".env")
WINDOW_DAYS = int(os.environ.get("DEADLINE_WINDOW_DAYS", "7"))


def load_env(path):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


def main():
    env = load_env(ENV_PATH)
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SECRET_KEY")
    uid = env.get("LUNGNOTE_USER_ID")
    if not (url and key and uid):
        return  # nothing to query — stay silent, never block

    now = datetime.now(timezone.utc)
    horizon = (now + timedelta(days=WINDOW_DAYS)).isoformat()

    # not done, has a due date, due within the window (or already overdue)
    query = {
        "user_id": f"eq.{uid}",
        "done": "eq.false",
        "due_at": f"lte.{horizon}",
        "select": "text,due_at,due_text",
        "order": "due_at.asc",
    }
    req = urllib.request.Request(
        f"{url}/rest/v1/lungnote_todos?" + urllib.parse.urlencode(query),
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            rows = json.load(resp)
    except Exception as exc:
        print(f"[deadline-check] LungNote unreachable ({exc.__class__.__name__}) "
              "— run /session-open to load todos manually")
        return

    if not rows:
        print(f"[deadline-check] ✅ no LungNote deadlines within {WINDOW_DAYS}d. "
              "Run /session-open to charter the session (loads full LungNote + GH issues).")
        return

    # Rows come ordered by due_at asc: oldest-overdue first, due-soon last.
    # To keep every-session context lean we show the most URGENT window — the
    # items nearest to (and just past) now — and collapse the deep-overdue tail
    # into a count. Show up to CAP, prioritising the tail of the list (due-soon
    # + freshly-overdue) since a 30-day-overdue item is usually already handled.
    cap = int(os.environ.get("DEADLINE_MAX_SHOWN", "12"))
    shown = rows[-cap:] if len(rows) > cap else rows
    hidden = len(rows) - len(shown)

    out = [f"🔔 LUNGNOTE DEADLINES (overdue or due ≤ {WINDOW_DAYS}d) — auto-surfaced at session start:"]
    if hidden:
        out.append(f"  (+{hidden} more overdue not shown — run /session-open for the full list)")
    for row in shown:
        label = "?"
        due = row.get("due_at")
        if due:
            try:
                d = datetime.fromisoformat(due.replace("Z", "+00:00"))
                days = (d - now).days
                if days < 0:
                    label = f"OVERDUE {-days}d"
                elif days == 0:
                    label = "TODAY"
                else:
                    label = f"in {days}d"
            except ValueError:
                label = due[:10]
        text = " ".join((row.get("text") or "").split())
        if len(text) > 160:
            text = text[:157] + "..."
        out.append(f"  • [{label}] {text}")
    out.append("→ Run /session-open to review these + open GitHub issues before starting. "
               "Whether to work a deadline now is the CEO's call — surface, don't auto-act.")
    print("\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never block session start
    sys.exit(0)
