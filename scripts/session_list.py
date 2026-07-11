#!/usr/bin/env python3
"""session_list.py — list past CTO/CXO sessions as a table, EXCLUDING the
iTerm2 tabs currently open. Read-only; backs the /session-list skill.

Source of truth = state/tab-titles/<role>-<id>.title — each holds a session's
last tab glyph + summary (written by scripts/tab-title.sh on every status flip).
Glyph = state:  ⏳ working · ✅ pending · 🔴 blocked · 💤 idle/parked · 🏁 closed.

Companion to session_tree.py (which lists DB *tasks* across projects). This one
lists *chat sessions* and their close-state.

Usage:
  python3 scripts/session_list.py          # default: NOT-yet-closed only (closed are done)
  python3 scripts/session_list.py --all     # include 🏁 closed sessions too
  python3 scripts/session_list.py --verify  # + cross-check title against log/transcript
                                             #   (catches title-sync bugs: title stuck at
                                             #   "⏳ เริ่ม session" while real work happened,
                                             #   or was never touched at all)
"""
import os
import re
import subprocess
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB_DIR = os.path.join(REPO, "state", "tab-titles")
LOG_DIR = os.path.join(REPO, "state", "logs")
CLAUDE_PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
PLACEHOLDER_SUMMARY = "เริ่ม session"

GLYPHS = {
    "🏁": "closed",
    "🔗": "merged",
    "💤": "idle/parked",
    "🔴": "blocked",
    "✅": "pending",
    "⏳": "working",
}
# check order: a 🏁 wins over a stray ✅ in the same string; 🔗 (also terminal)
# checked right after 🏁 so it doesn't get shadowed by an active-state glyph
GLYPH_ORDER = ["🏁", "🔗", "💤", "🔴", "✅", "⏳"]
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


def human_size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}GB"


def find_transcript(sid):
    """Real Claude Code transcript whose filename ends in this short id
    (pre-rollout sessions used the session uuid's last 8 hex as the short
    id — see scripts/spawn-cto.sh). Returns (path, size) or (None, 0)."""
    if not os.path.isdir(CLAUDE_PROJECTS_DIR):
        return None, 0
    for root, _dirs, files in os.walk(CLAUDE_PROJECTS_DIR):
        for f in files:
            if f.endswith(".jsonl") and sid in f.lower():
                p = os.path.join(root, f)
                try:
                    return p, os.path.getsize(p)
                except OSError:
                    continue
    return None, 0


def transcript_save_file(path):
    """Tail-scan a transcript for a /session-save write, so a stale-titled
    session can be reported as parked+resumable instead of just 'stale'."""
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, os.path.getsize(path) - 300_000))
            tail = fh.read().decode("utf-8", errors="ignore")
    except OSError:
        return None
    m = re.search(r"session-data/([\w.\-]+\.tmp)", tail)
    return m.group(1) if m else None


def log_lines(role, sid):
    path = os.path.join(LOG_DIR, f"{role}-{sid}.log")
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
        return lines
    except OSError:
        return []


def looks_like_fixture(lines):
    """All-identical timestamps across >=2 lines is a strong 'synthetic test
    data' signal — real event logs never land two distinct events in the
    same wall-clock second more than once."""
    ts = [m.group(1) for ln in lines
          for m in [re.match(r"\[([^\]]+)\]", ln)] if m]
    return len(ts) >= 2 and len(set(ts)) == 1


def verify_row(r):
    """Deep-check a title stuck at the spawn placeholder against the log
    and the real Claude transcript. Only called for --verify candidates."""
    role_lower = r["role"].lower()
    lines = log_lines(role_lower, r["id"])

    if lines:
        if looks_like_fixture(lines):
            return f"log {len(lines)}L, identical timestamps", "🗑 suspect (test data?)"
        merged = any("merging" in ln or "merged" in ln.lower() for ln in lines)
        evidence = f"log {len(lines)}L" + (", merge event" if merged else "")
        flag = "⚠ stale-title→done" if merged else "⚠ stale-title (real activity)"
        return evidence, flag

    tpath, tsize = find_transcript(r["id"])
    if tpath:
        save = transcript_save_file(tpath)
        if save:
            return f"transcript {human_size(tsize)}, saved: {save}", "💤 parked (resumable)"
        return f"transcript {human_size(tsize)}, no save", "⚠ stale-title (transcript, not parked)"

    return "no log/transcript found", "🗑 ghost-candidate"


def main():
    show_all = "--all" in sys.argv          # include 🏁 closed too (default hides them)
    verify = "--verify" in sys.argv         # cross-check title vs log/transcript
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
        if glyph == "🏁":
            blocker = "—"                       # closed → no live blocker
        elif glyph == "🔴":
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
            "summary": summary, "blocker": blocker, "created": created,
            "last_active": last_active, "live": sid in live,
        })

    out = [r for r in rows if not r["live"]]
    if not show_all:
        # default: closed and merged-away are both done, drop them
        out = [r for r in out if r["glyph"] not in ("🏁", "🔗")]
    out.sort(key=lambda r: r["last_active"], reverse=True)

    n_live = sum(1 for r in rows if r["live"])
    note = "" if live_ok else "  ⚠ iTerm query failed — live tabs NOT excluded"
    scope = "all incl closed" if show_all else "not-yet-closed"
    print(f"# Past sessions ({scope}, excluding {n_live} live iTerm tab(s)){note}\n")

    if not out:
        print("_none_")
        return

    if verify:
        for r in out:
            if r["glyph"] == "⏳" and r["summary"] == PLACEHOLDER_SUMMARY:
                r["evidence"], r["flag"] = verify_row(r)
                if r["flag"].startswith(("⚠", "🗑")):
                    r["blocker"] = "(title stale)"
            else:
                r["evidence"], r["flag"] = "title-only", "✓"
        print("| session | state | blocker | created | last active (ago) "
              "| evidence | flag |")
        print("|---|---|---|---|---|---|---|")
    else:
        print("| session | state | blocker | created | last active (ago) |")
        print("|---|---|---|---|---|")

    for r in out:
        c = datetime.fromtimestamp(r["created"]).strftime("%Y-%m-%d %H:%M")
        la = datetime.fromtimestamp(r["last_active"]).strftime("%m-%d %H:%M")
        age = fmt_age(now - r["last_active"])
        b = r["blocker"].replace("|", "/")
        row = (f"| {r['role']} #{r['id']} | {r['glyph']} {r['state']} "
               f"| {b} | {c} | {la} ({age}) |")
        if verify:
            row += f" {r['evidence']} | {r['flag']} |"
        print(row)

    # breakdown by state
    counts = {}
    for r in out:
        counts[r["glyph"] or "?"] = counts.get(r["glyph"] or "?", 0) + 1
    tally = " · ".join(f"{g} {n}" for g, n in
                       sorted(counts.items(), key=lambda kv: -kv[1]))
    print(f"\n**{len(out)} session(s)** — {tally}")

    if verify:
        fcounts = {}
        for r in out:
            key = r["flag"].split(" ", 1)[0]
            fcounts[key] = fcounts.get(key, 0) + 1
        ftally = " · ".join(f"{g}{n}" for g, n in
                            sorted(fcounts.items(), key=lambda kv: -kv[1]))
        print(f"**verify** — {ftally}")


if __name__ == "__main__":
    main()
