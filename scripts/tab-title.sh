#!/usr/bin/env bash
# tab-title.sh — set this C-level session's iTerm tab title to a live work
# summary so the CEO can scan the tab bar and see what each session is doing.
#
# Usage (from inside a C-level claude session — env carries role + id):
#   bash scripts/tab-title.sh "<glyph> <summary>"   # set + persist
#   bash scripts/tab-title.sh --reassert            # re-apply saved title
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

if [ "${1:-}" = "--reassert" ]; then
  [ -f "$TITLE_FILE" ] || exit 0
  TITLE="$(head -1 "$TITLE_FILE" 2>/dev/null || true)"
  [ -n "$TITLE" ] || exit 0
else
  SUMMARY="${1:-}"
  if [ -z "$SUMMARY" ]; then
    echo "usage: tab-title.sh \"<glyph> <summary>\" | --reassert" >&2
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
fi

# Loud-attention hook (idea from JasperSui/claude-code-iterm2-tab-status):
# when the status glyph is 🔴 (blocked — needs CEO) make this tab shout via
# the iTerm2 Python API — red tab color + badge — so the CEO spots it in the
# tab bar without reading titles. Any other glyph clears it. Backgrounded
# (with the venv) so it never slows the title set; match is "$BASE", this
# tab's stable prefix, so it only ever touches this one tab.
case "$TITLE" in
  *🔴*) _ATTN=mark ;;
  *)    _ATTN=clear ;;
esac
_WINID=""
[ -f "$WINID_FILE" ] && _WINID="$(tr -d '[:space:]' <"$WINID_FILE" 2>/dev/null || true)"
(
  cd "$ROOT" || exit 0
  [ -d .venv ] && . .venv/bin/activate 2>/dev/null
  python3 -m tools.itermtab "$_ATTN" "$BASE" >/dev/null 2>&1
  # Auto-arrange (trial opened 2026-06-16, review 2026-06-23): reorder THIS
  # window's tabs by status glyph so a 🔴 C-level chat jumps ahead of its DEV
  # tabs. Own window only (via saved winid) so it stays cheap, and a no-op on
  # single-tab windows. Verified harmless: async_set_tabs keeps the selected
  # tab + window focus, so the CEO can keep typing while tabs reorder.
  if [ -n "$_WINID" ] && [ "$_WINID" != "0" ]; then
    python3 -m tools.itermtab arrange "$_WINID" >/dev/null 2>&1
  fi
) &

# 1) Direct escape to the saved tty.
if [ -f "$TTY_FILE" ]; then
  TTY_DEV="$(tr -d '[:space:]' <"$TTY_FILE" 2>/dev/null || true)"
  if [ -n "$TTY_DEV" ] && [ -w "$TTY_DEV" ]; then
    if printf '\033]0;%s\007' "$TITLE" >"$TTY_DEV" 2>/dev/null; then
      exit 0
    fi
  fi
fi

# 2) AppleScript fallback by window id + title-substring match.
WINID=""
[ -f "$WINID_FILE" ] && WINID="$(tr -d '[:space:]' <"$WINID_FILE" 2>/dev/null || true)"
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
exit 0
