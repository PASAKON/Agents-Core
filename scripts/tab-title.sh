#!/usr/bin/env bash
# tab-title.sh — set this C-level session's iTerm tab title (Header) + an
# optional background badge (Subtitle) so the CEO can scan the tab bar/desktop
# and see what each session needs from them, without opening it.
#
# Usage (from inside a C-level claude session — env carries role + id):
#   bash scripts/tab-title.sh "<glyph> <summary>"              # Header only (unchanged, existing callers)
#   bash scripts/tab-title.sh "<glyph> <summary>" "<subtitle>" # + free-text Badge detail (2026-07-20)
#   bash scripts/tab-title.sh --reassert                       # re-apply saved title
#
# Header vs Subtitle (2026-07-20, CEO-designed): Header = tab title, short,
# always visible even when the tab column is narrow. Subtitle = the iTerm
# background badge, one line, free text — says what the CEO specifically
# needs to do right now ("ขอ key", "รออนุมัติงบ", "รอคำตอบ: ...", etc), not a
# fixed enum. Badge font is a single auto-sized size (iTerm limitation,
# verified against docs) — Header stays visually prominent because tab-bar
# text and badge text are different rendering surfaces, not because of a
# font-size difference within one surface.
#
# Status glyphs (IRON-RULES §32) — pick exactly one, always first:
#   ⏳ working on something now
#   ✅ latest batch done — more queued / awaiting review / DEVs in flight
#   🔴 blocked — waiting on CEO or external
#   💤 idle — nothing queued
#   🏁 ALL assigned work done, zero blockers — session safe to close
#
# Title = "<base> <glyph> <summary>" truncated to 60 chars. <base> comes from
# state/tab-titles/<role>-<sid>.base (seeded by the launcher) and is a stable
# prefix — send_to_cto / send_to_cxo / delegate route messages by substring
# of it, so the summary part may change freely without breaking routing.
#
# NEVER put a task-id (task-xxxxxxxx) in the summary: tools/itermtab.py
# close_tab() closes tabs whose title contains a finished task's id.
#
# Targeting order:
#   1. printf OSC-0 directly to the tty saved by the launcher
#      (state/locks/<role>-<sid>.tty) — works from claude Bash tool
#      subshells, which have no controlling tty of their own.
#   2. AppleScript fallback: find the tab via saved window id
#      (state/locks/<role>-<sid>.winid) matching the base / "#<sid>",
#      skipping "<X> Log #" side tabs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ROLE="${CXO_ROLE:-cto}"
SID="${CXO_SESSION_ID:-${CTO_SESSION_ID:-}}"
if [ -z "$SID" ]; then
  echo "tab-title: no CXO_SESSION_ID / CTO_SESSION_ID in env" >&2
  exit 2
fi
ROLE_UPPER="$(printf '%s' "$ROLE" | tr '[:lower:]' '[:upper:]')"

TITLE_DIR="$ROOT/state/tab-titles"
BASE_FILE="$TITLE_DIR/$ROLE-$SID.base"
TITLE_FILE="$TITLE_DIR/$ROLE-$SID.title"
TTY_FILE="$ROOT/state/locks/$ROLE-$SID.tty"
WINID_FILE="$ROOT/state/locks/$ROLE-$SID.winid"

BASE=""
[ -f "$BASE_FILE" ] && BASE="$(head -1 "$BASE_FILE" 2>/dev/null || true)"
# Pre-rollout sessions have no .base file — synthesize the standard prefix.
[ -n "$BASE" ] || BASE="$ROLE_UPPER #$SID"

SUBTITLE_FILE="$TITLE_DIR/$ROLE-$SID.subtitle"
SUBTITLE=""

if [ "${1:-}" = "--reassert" ]; then
  [ -f "$TITLE_FILE" ] || exit 0
  TITLE="$(head -1 "$TITLE_FILE" 2>/dev/null || true)"
  [ -n "$TITLE" ] || exit 0
  [ -f "$SUBTITLE_FILE" ] && SUBTITLE="$(head -1 "$SUBTITLE_FILE" 2>/dev/null || true)"
else
  SUMMARY="${1:-}"
  SUBTITLE="${2:-}"
  if [ -z "$SUMMARY" ]; then
    echo "usage: tab-title.sh \"<glyph> <summary>\" [\"<subtitle>\"] | --reassert" >&2
    exit 2
  fi
  TITLE="$(python3 - "$BASE" "$SUMMARY" <<'PYEOF'
import sys
base, summary = sys.argv[1], sys.argv[2]
summary = " ".join(summary.split())  # collapse newlines / repeated spaces
title = f"{base} {summary}"
MAX = 60
if len(title) > MAX:
    title = title[: MAX - 1] + "…"
print(title)
PYEOF
)"
  mkdir -p "$TITLE_DIR"
  printf '%s\n' "$TITLE" >"$TITLE_FILE"
  # Subtitle (Badge) is saved separately from Header so /session-list and
  # other tools can still read Header without parsing badge text out of it.
  if [ -n "$SUBTITLE" ]; then
    SUBTITLE="$(printf '%s' "$SUBTITLE" | tr '\n' ' ')"
    printf '%s\n' "$SUBTITLE" >"$SUBTITLE_FILE"
  else
    rm -f "$SUBTITLE_FILE"
  fi
fi

# Set the title via tty OSC first, AppleScript fallback second; THEN run the
# attention + arrange hook (section 3) so it reads the new glyph, not the old.
_TITLE_SET=0
WINID=""
[ -f "$WINID_FILE" ] && WINID="$(tr -d '[:space:]' <"$WINID_FILE" 2>/dev/null || true)"

# 1) Direct escape to the saved tty.
#    OSC 1 (icon/tab name), NOT OSC 0. OSC 0 sets the tab name AND the window
#    title, which would wipe the Main Tab (goal + progress + clock) that
#    scripts/tab-main.sh owns via OSC 2 — see tools/maintab.py "Ownership
#    rule". Changed 2026-08-03 when the two-layer tab landed.
if [ -f "$TTY_FILE" ]; then
  TTY_DEV="$(tr -d '[:space:]' <"$TTY_FILE" 2>/dev/null || true)"
  if [ -n "$TTY_DEV" ] && [ -w "$TTY_DEV" ]; then
    if printf '\033]1;%s\007' "$TITLE" >"$TTY_DEV" 2>/dev/null; then
      _TITLE_SET=1
    fi
  fi
fi

# 2) AppleScript fallback by window id + title-substring match (only if the
#    direct tty write didn't land).
if [ "$_TITLE_SET" != "1" ]; then
osascript - "$TITLE" "$BASE" "#$SID" "${WINID:-0}" <<'APPLEEOF' >/dev/null 2>&1 || true
on run argv
  set newTitle to item 1 of argv
  set baseMatch to item 2 of argv
  set sidMatch to item 3 of argv
  set winId to item 4 of argv
  tell application "iTerm"
    if winId is not "0" then
      try
        set w to (first window whose id is (winId as integer))
        repeat with t in tabs of w
          try
            set nm to ""
            try
              set nm to name of t
            end try
            set sn to ""
            try
              set sn to name of current session of t
            end try
            if ((nm contains baseMatch) or (sn contains baseMatch) or (nm contains sidMatch) or (sn contains sidMatch)) and not (nm contains " Log #") and not (sn contains " Log #") then
              set name of current session of t to newTitle
              return
            end if
          end try
        end repeat
      end try
    end if
    repeat with w in windows
      repeat with t in tabs of w
        try
          set nm to ""
          try
            set nm to name of t
          end try
          set sn to ""
          try
            set sn to name of current session of t
          end try
          if ((nm contains baseMatch) or (sn contains baseMatch) or (nm contains sidMatch) or (sn contains sidMatch)) and not (nm contains " Log #") and not (sn contains " Log #") then
            set name of current session of t to newTitle
            return
          end if
        end try
      end repeat
    end repeat
  end tell
end run
APPLEEOF
fi

# 3) Tab color/badge + auto-arrange hook — runs AFTER the title is set so it
#    reads the NEW glyph. One combined iTerm API connection (color/badge on
#    $BASE by status glyph + arrange this window) keeps connection churn
#    low; the earlier two-calls-per-update burst was timing the API out.
#    Backgrounded so it never slows the title set; own window only (saved
#    winid), no-op on single-tab windows / when the API is down.
#    Trial opened 2026-06-16, review 2026-06-23. Extended to full glyph->color
#    table (was 🔴-only mark/clear) 2026-08-03 — see tools/itermtab.py
#    _STATUS_STYLE for the ⏳/✅/🔴/💤/🏁 -> RGB mapping.
case "$TITLE" in
  *🔴*) _GLYPH="🔴" ;;
  *⏳*) _GLYPH="⏳" ;;
  *✅*) _GLYPH="✅" ;;
  *🏁*) _GLYPH="🏁" ;;
  *💤*) _GLYPH="💤" ;;
  *)    _GLYPH=""   ;;
esac
(
  cd "$ROOT" || exit 0
  [ -d .venv ] && . .venv/bin/activate 2>/dev/null
  if [ "$_GLYPH" = "🔴" ] && [ -n "$SUBTITLE" ]; then
    # Subtitle (free text, e.g. "🎨 ขอ design เรื่อง storage") drives the
    # badge instead of the fixed "🔴 รอ CEO" fallback — see tools/itermtab.py
    # mark_attention(badge=...). Falls back to the old fixed badge when no
    # subtitle was given (existing single-arg callers, unaffected).
    python3 -m tools.itermtab mark "$BASE" "$SUBTITLE" "${TTY_DEV:-}" "$TITLE" >/dev/null 2>&1
    [ -n "${WINID:-}" ] && [ "${WINID:-0}" != "0" ] && python3 -m tools.itermtab arrange "$WINID" >/dev/null 2>&1 || true
  else
    python3 -m tools.itermtab status "$BASE" "${WINID:-0}" "$_GLYPH" "${TTY_DEV:-}" "$TITLE" >/dev/null 2>&1
  fi
  # Keep the Main Tab clock alive without touching the spawn scripts: this is
  # a pidfile check that no-ops when the daemon is already up (the normal
  # case), so it costs nothing per status update. See tools/maintab.py.
  python3 -m tools.maintab ensure-daemon >/dev/null 2>&1 || true
) &

exit 0
