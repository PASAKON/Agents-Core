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
