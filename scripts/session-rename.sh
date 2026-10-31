#!/usr/bin/env bash
# Rename THIS C-level session's Claude display name (the one the mobile app /
# Remote Control list shows). The name is tools/rename_service.py's, built from
# lib/session_names with the host emoji first (CEO 2026-10-14): a C-level
# "<ROLE> (<person emoji>: <Name>) — <topic>", no machine and no #id; a
# Project Head "PH#<id3> (<LANE>) - <Project> — <topic>". Both keep the persona and the
# lane (CEO 2026-10-15, who renamed two live sessions that way by hand); the compact
# "<Short>·<M>#<id3> <Head>: <job>" is for workers only. The old form
# "<MACHINE> <ROLE> #<id> (<topic>)" is gone: a session with no org id gets nothing.
#
# Mechanism: /rename is a TUI-only command — an agent cannot call it as a tool,
# and a session may not type into its own pane (Agents-Core #272: an allow rule for
# that would let it type any slash command into its own prompt). So this script
# sends a rename REQUEST (topic + state glyph) over a unix socket to
# tools/rename_service.py, a root service, which checks that the caller belongs to
# that session and types "/rename <name>" into its pane when its prompt is empty.
# Name changes propagate to claude.ai + the mobile app (Claude Code v2.1.221+).
#
# Usage:  bash scripts/session-rename.sh "หัวข้อของ session"
#   → requested: /rename <host emoji> CTO (<person emoji>: Kavin) — หัวข้อของ session
#         bash scripts/session-rename.sh --force "<topic>"   # request again even if unchanged
#         bash scripts/session-rename.sh --show              # print the recorded topic, no send
#
# State (task-460f3eaf): this used to be write-only — every call queued a
# /rename keystroke with no record of what it last set, so a caller could not
# tell whether a rename had landed, and could not call it routinely (every
# invocation retyped the command). It now records the topic it sends to
# state/locks/<role>-<id>.topic — the SAME sibling-file convention every other
# `.topic` writer in this repo uses (tools/session_name.py LOCK_SUFFIXES;
# see also tools/send_to_cxo.py's ephemeral-spawn dedupe slug, a different use
# of the same suffix). Full format + recovery notes: docs/SESSION-RENAME-STATE.md.
#
# Called by /session-open step 3 (right after tab-title/tab-main), and now also
# by /session-worktree and /session-close so the display name tracks the topic
# without a caller having to remember to run it — the recorded-name check
# below makes repeat calls a no-op whenever the full rendered name is the same
# (not merely the topic: a PH whose project changed renders a new name).
#
# Guards:
#   - no org session id (a plain terminal, a worker) → nothing requested, exit 0;
#     never a hard failure, and no record is written.
#   - topic trimmed to 40 chars here; the service cleans it again (it trusts
#     nothing a session wrote).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS_DIR="$ROOT/state/locks"

FORCE=0
SHOW=0
PREFIX=""
TOPIC=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "--prefix" ]; then
    PREFIX="$arg"; prev=""; continue
  fi
  case "$arg" in
    --force) FORCE=1 ;;
    --show) SHOW=1 ;;
    --prefix) prev="--prefix" ;;
    *) TOPIC="$arg" ;;
  esac
done

ROLE="${CXO_ROLE:-cto}"
SID="${CTO_SESSION_ID:-${CXO_SESSION_ID:-}}"
# Only a live C-level session (one with an id) has a meaningful record — an
# ad-hoc/no-id invocation degrades to the old always-send behaviour below.
TOPIC_FILE=""
if [ -n "$SID" ]; then
  TOPIC_FILE="$LOCKS_DIR/$ROLE-$SID.topic"
fi

if [ "$SHOW" = "1" ]; then
  if [ -z "$TOPIC_FILE" ]; then
    echo "recorded: (none — no session id in CTO_SESSION_ID / CXO_SESSION_ID)"
    exit 0
  fi
  if [ -f "$TOPIC_FILE" ]; then
    echo "recorded: $(cat "$TOPIC_FILE")"
  else
    echo "recorded: (none)"
  fi
  exit 0
fi

if [ -z "$TOPIC" ]; then
  echo "usage: session-rename.sh [--force] [--show] [--prefix \"<glyph>\"] \"<topic>\"" >&2
  exit 1
fi
# Keep the list scannable; the full story lives in the session itself.
#
# Cut by CHARACTERS, not bytes. `cut -c1-40` counts bytes under a non-UTF-8
# locale, and Thai is 3 bytes per character -- so a Thai topic came back sliced
# through the middle of a character, ending in a replacement glyph
# ("Cookie Run ฟาร์มกู้ต<?>", measured 2026-09-16). The CEO names sessions in
# Thai, so that was every rename, not an edge case. Bash's ${var:0:n} is
# character-aware once the locale is, hence the explicit LC_ALL.
#
# ...but hardcoding C.UTF-8 did not fix it on the Mac: **macOS ships no
# C.UTF-8 locale** (`locale -a` has no such entry), so LC_ALL fell back to C,
# byte semantics returned, and the very next Thai rename came back as
# "ซ่อม SSH ข้ามเคร<?>" (measured 2026-09-17). C.UTF-8 is a glibc thing;
# this repo runs on macOS, Windows and Linux. Ask the box which UTF-8 locale it
# actually has instead of assuming, and fall back to en_US.UTF-8, which every
# macOS carries.
UTF8_LOCALE="$(locale -a 2>/dev/null | grep -ixE 'C\.UTF-?8|en_US\.UTF-?8' | head -1)"
: "${UTF8_LOCALE:=en_US.UTF-8}"
TOPIC="$(LC_ALL="$UTF8_LOCALE" bash -c 'printf "%s" "${1:0:40}"' _ "$TOPIC")"

# task-bbdfa8d1 (CEO 2026-09-11): a state glyph (✅ close · ⏸ save · ⛔
# merged) goes in front of the machine/role so the app list sorts and scans
# by state. Folded into the same dedupe/record key as TOPIC -- a prefix
# change alone (e.g. ⏸ -> ✅ on the same topic) must still send, and --show
# must still report exactly what was last sent.
RECORD_KEY="$TOPIC"
if [ -n "$PREFIX" ]; then
  RECORD_KEY="$PREFIX $TOPIC"
fi

# M10b (Agents-Core #272, CEO 2026-10-14): a session never types into its own pane.
# This script only sends a REQUEST (the topic and the state glyph, never a name)
# to /run/rename-service/sock; tools/rename_service.py (root, systemd) checks with
# SO_PEERCRED that this process descends from that session's Claude process, builds
# the name with lib/session_names and types "/rename <name>" into the pane once its
# prompt line is empty. No tmux call and no file under state/ for the request.
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
if [ -z "$SID" ] || ! [[ "$SID" =~ ^[0-9a-f]{8}$ ]] || ! [[ "$ROLE" =~ ^(c[a-z]o|project_head)$ ]]; then
  echo "no org session id here (CTO_SESSION_ID / CXO_SESSION_ID): nothing requested — rename by hand: /rename $TOPIC"
  exit 0
fi
PREVIEW="$(cd "$ROOT" && "$PY" tools/rename_service.py preview --role "$ROLE" --sid "$SID" \
  --topic "$TOPIC" --prefix "$PREFIX" --locks-dir "$LOCKS_DIR" 2>/dev/null)" || PREVIEW=""
if [ -z "$PREVIEW" ]; then
  echo "no rule name for $ROLE-$SID (a PH needs its .project/.spawned_by; --prefix is one of ✅ ⏸ ⛔): nothing requested" >&2
  exit 1
fi

# "unchanged" is decided by the FULL rendered name, not by the topic alone: the name is built from
# more than the topic (a PH's project in its .project file, the lane, the host, the persona), so
# the same topic can render a different name after one of those changed. The record is the
# rendered name this script last had accepted by the service (<role>-<id>.rendered). No record
# (a session from before it existed, or a request that never landed) asks again.
NAME_FILE="$LOCKS_DIR/$ROLE-$SID.rendered"
if [ "$FORCE" != "1" ] && [ -f "$NAME_FILE" ] && [ "$(cat "$NAME_FILE")" = "$PREVIEW" ]; then
  echo "unchanged: $RECORD_KEY"
  exit 0
fi
set +e
REPLY="$(cd "$ROOT" && "$PY" tools/rename_service.py request --role "$ROLE" --sid "$SID" \
  --topic "$TOPIC" --prefix "$PREFIX" 2>&1)"
RC=$?
set -e
if [ "$RC" -ne 0 ]; then
  # Not recorded: a later call with the same topic must try again.
  echo "not requested ($REPLY) — rename by hand: /rename $PREVIEW"
  exit 0
fi
echo "requested: /rename $PREVIEW (the rename service types it once this session's prompt is empty)"

if [ -n "$TOPIC_FILE" ]; then
  mkdir -p "$LOCKS_DIR"
  # state/locks is shared, so a record is never written through a link: refuse a path that
  # is a link or not a regular file, write a fresh temp file, and rename it into place (a
  # rename replaces a link, it never follows one).
  write_record() {
    local file="$1" value="$2" tmp
    if [ -L "$file" ] || { [ -e "$file" ] && [ ! -f "$file" ]; }; then
      echo "session-rename: not writing $file: not a regular file" >&2
      return 0
    fi
    tmp="$(mktemp "$LOCKS_DIR/.rename.XXXXXX")" || return 0
    printf '%s' "$value" > "$tmp" && mv -fT "$tmp" "$file" || rm -f "$tmp"
  }
  write_record "$TOPIC_FILE" "$RECORD_KEY"
  write_record "$NAME_FILE" "$PREVIEW"
fi
