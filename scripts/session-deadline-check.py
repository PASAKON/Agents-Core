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
- Reads creds from the LungNote-MCP checkout's .env (SUPABASE_URL,
  SUPABASE_SECRET_KEY, LUNGNOTE_USER_ID). Never prints them.
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

# lungnote-mcp was split out to its own repo (PASAKON/LungNote-MCP) on
# 2026-08-03, so its .env now sits beside that checkout instead of inside this
# repo. Override with LUNGNOTE_MCP_DIR when the checkout lives elsewhere.
#
# The default is the Mac's path, so on Contabo this script found no .env, took
# the silent `return` below, and printed nothing — on every session since the
# split. That is indistinguishable from "no deadlines", which is why nobody
# noticed for six weeks: the hook looked healthy because a hook that says
# nothing is what a clear calendar looks like. Same shape as the CLAUDE.md wiki
# roots, which cto-claude.sh already repoints per machine. Measured 2026-09-14
# with 208 open todos and 51 overdue sitting unseen.
_CANDIDATES = [
    "/Users/gob/LungNote Projects/mcp",   # Mac
    "/opt/lungnote-mcp",                  # Contabo
]
LUNGNOTE_MCP_DIR = os.environ.get("LUNGNOTE_MCP_DIR") or next(
    (d for d in _CANDIDATES if os.path.exists(os.path.join(d, ".env"))),
    _CANDIDATES[0],
)
ENV_PATH = os.path.join(LUNGNOTE_MCP_DIR, ".env")
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
        # Say so. Silence here reads exactly like "no deadlines due", and that
        # false all-clear is the failure this script is supposed to prevent.
        # Still exits 0 — it warns, it never blocks.
        print(f"[deadline-check] ⚠️ cannot read LungNote creds at {ENV_PATH} "
              "— deadlines NOT checked. This is not an all-clear. "
              "Set LUNGNOTE_MCP_DIR or run /session-open.")
        return

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


def box_disk_warning():
    """Surface the Cookie Run data steward's disk warning from the Windows box.

    tools/disksense.py on winbox writes ledger/DISK-WARNING.txt when C: runs low or
    the training data grows fast (CEO 2026-09-06: warn, never auto-delete). The
    file is the whole message; this only relays it. Fails quiet: no ssh, no box,
    no file → prints nothing.
    """
    import subprocess
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "winbox",
             "cmd /c type C:\\Users\\UsEr\\Documents\\CookieRunScript\\ledger\\DISK-WARNING.txt"],
            capture_output=True, text=True, timeout=12)
    except Exception:
        return
    body = (r.stdout or "").strip()
    if r.returncode == 0 and body and "DISK WARNING" in body:
        print("💽 WINBOX DISK WARNING (Cookie Run data — steward brief: cookierun-bot/docs/DATA-STEWARD.md):")
        for line in body.splitlines()[:8]:
            print("  " + line)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never block session start
    try:
        box_disk_warning()
    except Exception:
        pass
    sys.exit(0)
