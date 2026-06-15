#!/usr/bin/env python3
"""session_list.py — list past CTO/CXO sessions as a table, EXCLUDING the
iTerm2 tabs currently open. Read-only; backs the /session-list skill.

Source of truth = state/tab-titles/<role>-<id>.title — each holds a session's
last tab glyph + summary (written by scripts/tab-title.sh on every status flip).
Glyph = state:  ⏳ working · ✅ pending · 🔴 blocked · 💤 idle/parked · 🏁 closed.

Companion to session_tree.py (which lists DB *tasks* across projects). This one
lists *chat sessions* and their close-state.

Usage:
  python3 scripts/session_list.py          # all non-live sessions (incl 🏁 closed)
  python3 scripts/session_list.py --open    # only sessions NOT yet 🏁-closed
"""
import os
import re
import subprocess
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB_DIR = os.path.join(REPO, "state", "tab-titles")
LOG_DIR = os.path.join(REPO, "state", "logs")

GLYPHS = {
    "🏁": "closed",
    "💤": "idle/parked",
    "🔴": "blocked",
    "✅": "pending",
    "⏳": "working",
}
# check order: a 🏁 wins over a stray ✅ in the same string
GLYPH_ORDER = ["🏁", "💤", "🔴", "✅", "⏳"]
ID_RE = re.compile(r"#([0-9a-fA-F]{6,})")


def live_ids():
    """Session ids of iTerm2 tabs open right now (these get excluded).

    Returns (set_of_ids, ok). ok=False if iTerm couldn't be queried, so the
    caller can warn instead of silently treating every session as not-live.
    """
    script = (
        'tell application "iTerm2"\n'
        '  set out to ""\n'
        '  repeat with w in windows\n'
        '    repeat with t in tabs of w\n'
        '      repeat with s in sessions of t\n'
        '        set out to out & (name of s) & linefeed\n'
        '      end repeat\n'
        '    end repeat\n'
        '  end repeat\n'
        '  return out\n'
        'end tell'
    )
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15,
        )
        ids = {m.group(1).lower() for line in r.stdout.splitlines()
               for m in [ID_RE.search(line)] if m}
        return ids, True
    except Exception:
        return set(), False


def fmt_age(seconds):
    s = max(0, int(seconds))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


def birth(path):
    s = os.stat(path)
    return getattr(s, "st_birthtime", s.st_ctime)


def main():
    open_only = "--open" in sys.argv
    now = datetime.now().timestamp()
    live, live_ok = live_ids()

    if not os.path.isdir(TAB_DIR):
        print(f"no tab-titles dir at {TAB_DIR}")
        return

    rows = []
    for fn in os.listdir(TAB_DIR):
        if not fn.endswith(".title"):
            continue
        stem = fn[:-len(".title")]          # e.g. cto-3dcd82d3
        if "-" not in stem:
            continue
        role, sid = stem.rsplit("-", 1)
        sid = sid.lower()
        path = os.path.join(TAB_DIR, fn)
        try:
            content = open(path, encoding="utf-8").read().strip()
        except Exception:
            continue

        glyph = next((g for g in GLYPH_ORDER if g in content), "")
        state = GLYPHS.get(glyph, "?")
        summary = content.split(glyph, 1)[1].strip() if glyph else content
        if glyph == "🔴":
            blocker = summary or "(unspecified)"
        elif "รอ" in summary:
            blocker = "รอ" + summary.split("รอ", 1)[1]
        else:
            blocker = "—"

        # created = earliest birth across title/base/log (≈ spawn time)
        cands = []
        for p in (path,
                  os.path.join(TAB_DIR, stem + ".base"),
                  os.path.join(LOG_DIR, stem + ".log")):
            try:
                cands.append(birth(p))
            except Exception:
                pass
        created = min(cands) if cands else birth(path)

        # last active = latest mtime across title/log
        la = [os.stat(path).st_mtime]
        try:
            la.append(os.stat(os.path.join(LOG_DIR, stem + ".log")).st_mtime)
        except Exception:
            pass
        last_active = max(la)

        rows.append({
            "role": role.upper(), "id": sid, "glyph": glyph, "state": state,
            "blocker": blocker, "created": created, "last_active": last_active,
            "live": sid in live,
        })

    out = [r for r in rows if not r["live"]]
    if open_only:
        out = [r for r in out if r["glyph"] != "🏁"]
    out.sort(key=lambda r: r["last_active"], reverse=True)

    n_live = sum(1 for r in rows if r["live"])
    note = "" if live_ok else "  ⚠ iTerm query failed — live tabs NOT excluded"
    scope = "not-yet-closed" if open_only else "all"
    print(f"# Past sessions ({scope}, excluding {n_live} live iTerm tab(s)){note}\n")

    if not out:
        print("_none_")
        return

    print("| session | state | blocker | created | last active (ago) |")
    print("|---|---|---|---|---|")
    for r in out:
        c = datetime.fromtimestamp(r["created"]).strftime("%Y-%m-%d %H:%M")
        la = datetime.fromtimestamp(r["last_active"]).strftime("%m-%d %H:%M")
        age = fmt_age(now - r["last_active"])
        b = r["blocker"].replace("|", "/")
        print(f"| {r['role']} #{r['id']} | {r['glyph']} {r['state']} "
              f"| {b} | {c} | {la} ({age}) |")

    # breakdown by state
    counts = {}
    for r in out:
        counts[r["glyph"] or "?"] = counts.get(r["glyph"] or "?", 0) + 1
    tally = " · ".join(f"{g} {n}" for g, n in
                       sorted(counts.items(), key=lambda kv: -kv[1]))
    print(f"\n**{len(out)} session(s)** — {tally}")


if __name__ == "__main__":
    main()
