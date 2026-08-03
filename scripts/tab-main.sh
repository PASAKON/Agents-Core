#!/usr/bin/env bash
# tab-main.sh — set this C-level session's MAIN tab (the window titlebar):
# the session goal + a progress bar + elapsed time.
#
#   🎯 <goal> ▓▓▓▓▓▓░░░░ 62% · ⏱ 2h14m
#
# Companion to scripts/tab-title.sh, which owns the SUB tab (the colored tab
# strip: "<base> <glyph> <what I'm doing now>"). Two surfaces, two jobs:
#
#   Main tab (here)     = where this session is GOING  — slow, strategic
#   Sub tab (tab-title) = what it is doing RIGHT NOW   — fast, colored
#
# They are genuinely independent (verified 2026-08-03): OSC 2 sets the window
# titlebar, OSC 1 sets the tab strip. Never use OSC 0 — it writes BOTH, so one
# surface silently eats the other.
#
# Usage:
#   bash scripts/tab-main.sh "<goal>"                 # goal only
#   bash scripts/tab-main.sh "<goal>" 12/13           # goal + progress
#   bash scripts/tab-main.sh "" 12/13                 # progress only, keep goal
#   bash scripts/tab-main.sh --status                 # daemon pid + all lines
#   bash scripts/tab-main.sh --stop                   # stop the refresh daemon
#
# Progress: pass DONE/TOTAL (e.g. 12/13) — the same counts /session-worktree
# reports, so the percentage stays countable rather than a vibe. A bare number
# is treated as a raw percent.
#
# The clock is driven by a single shared daemon on a 60s tick (one wakeup per
# minute for ALL sessions), started automatically here. `--stop` kills it; it
# also exits on its own once no live session is left.
#
# Update this after every finished work batch, alongside tab-title.sh
# (IRON-RULES §32).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[ -d .venv ] && . .venv/bin/activate 2>/dev/null || true

case "${1:-}" in
  --status) exec python3 -m tools.maintab status ;;
  --stop)   exec python3 -m tools.maintab stop-daemon ;;
  --push)   exec python3 -m tools.maintab push ;;
esac

GOAL="${1:-}"
PROGRESS="${2:-}"

# An EMPTY goal is legal and means "keep the current goal, update progress"
# (`tab-main.sh "" 12/13`) — so emptiness alone must not trigger usage. Only
# a call that would change nothing does.
if [ -z "$GOAL" ] && [ -z "$PROGRESS" ]; then
  echo 'usage: tab-main.sh "<goal>" [DONE/TOTAL] | "" DONE/TOTAL | --status | --stop' >&2
  exit 2
fi

set -- set
[ -n "$GOAL" ] && set -- "$@" --goal "$GOAL"
if [ -n "$PROGRESS" ]; then
  case "$PROGRESS" in
    */*) set -- "$@" --progress "$PROGRESS" ;;
    *)   set -- "$@" --percent  "$PROGRESS" ;;
  esac
fi

exec python3 -m tools.maintab "$@"
