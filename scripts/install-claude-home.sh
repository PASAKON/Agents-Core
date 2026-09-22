#!/usr/bin/env bash
# scripts/install-claude-home.sh — make ~/.claude a DERIVED folder (ADR 0027).
#
# Everything the org needs in ~/.claude lives in this repo under claude-home/
# (and org skills under .claude/skills/). This script links it into place, so
# "rm -rf ~/.claude && reinstall Claude Code" is recoverable with:
#
#     claude login
#     bash scripts/install-claude-home.sh          # link + plugins + venv + launchd
#
#     bash scripts/install-claude-home.sh --check  # doctor: report drift, change nothing (exit 1 on drift)
#
# Rules it enforces (same shape as gdrive-filing / the HQ map):
#   * every org-owned entry in ~/.claude is a symlink into this repo — a REAL
#     file/dir where a link should be is DRIFT. On install, a differing real
#     settings.json/CLAUDE.md is CAPTURED into the repo first (your /config edits
#     survive), then backed up under ~/.claude/backups/claude-home-<ts>/ and linked.
#   * ~/.claude/skills/<name> is a link only if claude-home/skills.txt has a row —
#     a real dir with no row is UNMAPPED (report it; the map decides, not the disk).
#   * settings.local.json is local: copied from the .example only when absent, never linked.
#
# Env overrides (tests): CLAUDE_HOME (default ~/.claude), CLAUDE_HOME_SRC (default
# <repo>/claude-home), PROJECTS (default /Users/gob/Projects).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${CLAUDE_HOME:-$HOME/.claude}"
SRC="${CLAUDE_HOME_SRC:-$REPO/claude-home}"
PROJECTS="${PROJECTS:-/Users/gob/Projects}"
MODE="install"
[ "${1:-}" = "--check" ] && MODE="check"
TS="$(date +%Y%m%dT%H%M%S)"
BACKUP="$HOME_DIR/backups/claude-home-$TS"
DRIFT=0
ENTRIES=(CLAUDE.md settings.json hooks commands mcp/mooniex-coord tools)

say()  { printf '  %s\n' "$*"; }
bad()  { printf '  \033[31m%s\033[0m\n' "$*"; DRIFT=$((DRIFT+1)); }
ok()   { printf '  \033[32m%s\033[0m\n' "$*"; }

expand() {  # $PROJECTS / $HOME / $SRC in skills.txt targets
  local t="$1"; t="${t//\$PROJECTS/$PROJECTS}"; t="${t//\$HOME/$HOME}"; t="${t//\$SRC/$SRC}"; printf '%s' "$t"
}

same_target() {  # $1 = existing symlink, $2 = wanted target; true when they resolve to the same path
  python3 -c 'import os,sys; sys.exit(0 if os.path.realpath(sys.argv[1]) == os.path.realpath(sys.argv[2]) else 1)' "$1" "$2"
}

link_entry() {  # $1 = relative entry; links $HOME_DIR/$1 -> $SRC/$1
  local rel="$1" live="$HOME_DIR/$1" want="$SRC/$1"
  [ -e "$want" ] || { bad "MISSING in repo: $want (nothing to link)"; return; }
  if [ -L "$live" ]; then
    if same_target "$live" "$want"; then ok "linked   $rel"; else
      if [ "$MODE" = check ]; then bad "DRIFT    $rel -> $(readlink "$live") (want $want)"; else
        ln -sfn "$want" "$live"; ok "relinked $rel"; fi
    fi
    return
  fi
  if [ -e "$live" ]; then
    if [ "$MODE" = check ]; then
      if diff -rq "$live" "$want" >/dev/null 2>&1; then bad "DRIFT    $rel is a real copy (identical) — should be a symlink"
      else bad "DRIFT    $rel is a real copy and DIFFERS from repo — install would capture it"; fi
      return
    fi
    if ! diff -rq "$live" "$want" >/dev/null 2>&1; then
      if [ -d "$live" ]; then cp -R "$live/." "$want/"; else cp "$live" "$want"; fi
      say "CAPTURED $rel (live differed) -> $want   [git status will show it]"
    fi
    mkdir -p "$BACKUP/$(dirname "$rel")"; mv "$live" "$BACKUP/$rel"
    say "backed up real $rel -> $BACKUP/$rel"
  fi
  [ "$MODE" = check ] && { bad "MISSING  $rel (not linked)"; return; }
  mkdir -p "$(dirname "$live")"; ln -s "$want" "$live"; ok "linked   $rel"
}

echo "claude-home ($MODE): HOME=$HOME_DIR  SRC=$SRC"
[ -d "$SRC" ] || { echo "no $SRC — wrong repo?" >&2; exit 2; }
mkdir -p "$HOME_DIR/skills"

echo "— core entries"
for e in "${ENTRIES[@]}"; do link_entry "$e"; done

echo "— settings.local.json (local, never linked)"
if [ -f "$HOME_DIR/settings.local.json" ]; then ok "present  settings.local.json"
elif [ -f "$SRC/settings.local.json.example" ]; then
  if [ "$MODE" = check ]; then bad "MISSING  settings.local.json (install copies the example)"
  else cp "$SRC/settings.local.json.example" "$HOME_DIR/settings.local.json"; ok "seeded   settings.local.json from example"; fi
fi

echo "— skills (claude-home/skills.txt is the map)"
MAPPED=" "   # space-delimited: macOS ships bash 3.2, no associative arrays
if [ -f "$SRC/skills.txt" ]; then
  while IFS=$'\t' read -r name target; do
    [ -z "$name" ] && continue; case "$name" in \#*) continue;; esac
    MAPPED="$MAPPED$name "
    live="$HOME_DIR/skills/$name"; want="$(expand "$target")"
    if [ ! -e "$want" ]; then
      say "WARN     $name: target missing ($want) — reinstall its source, then rerun"; continue
    fi
    if [ -L "$live" ]; then
      if same_target "$live" "$want"; then ok "linked   skills/$name"
      elif [ "$MODE" = check ]; then bad "DRIFT    skills/$name -> $(readlink "$live") (want $want)"
      else ln -sfn "$want" "$live"; ok "relinked skills/$name"; fi
    elif [ -e "$live" ]; then
      bad "DRIFT    skills/$name is a REAL dir but the map says link -> $want (move it by hand or run scripts/claude_home_migrate.py)"
    elif [ "$MODE" = check ]; then bad "MISSING  skills/$name"
    else ln -s "$want" "$live"; ok "linked   skills/$name"; fi
  done < "$SRC/skills.txt"
fi
for d in "$HOME_DIR"/skills/*; do
  [ -e "$d" ] || continue
  n="$(basename "$d")"; case "$n" in synced|learned) continue;; esac
  [ -L "$d" ] && continue
  case "$MAPPED" in *" $n "*) ;; *) bad "UNMAPPED real dir skills/$n — add a row to claude-home/skills.txt (and move it into the repo) or delete it";; esac
done

echo "— plugins (claude-home/plugins.txt)"
if [ -f "$SRC/plugins.txt" ] && command -v claude >/dev/null 2>&1; then
  installed="$HOME_DIR/plugins/installed_plugins.json"
  while IFS=$'\t' read -r kind value; do
    [ -z "$kind" ] && continue; case "$kind" in \#*) continue;; esac
    if [ "$kind" = marketplace ]; then
      mname="${value%%=*}"; msrc="${value#*=}"
      if claude plugin marketplace list 2>/dev/null | grep -q "$mname"; then ok "market   $mname"
      elif [ "$MODE" = check ]; then bad "MISSING  marketplace $mname ($msrc)"
      else claude plugin marketplace add "$msrc" >/dev/null 2>&1 && ok "added    marketplace $mname" || bad "FAILED   marketplace add $msrc — run by hand"; fi
    elif [ "$kind" = plugin ]; then
      if [ -f "$installed" ] && grep -q "\"$value\"" "$installed"; then ok "plugin   $value"
      elif [ "$MODE" = check ]; then bad "MISSING  plugin $value"
      else claude plugin install "$value" >/dev/null 2>&1 && ok "installed plugin $value" || bad "FAILED   plugin install $value — run by hand"; fi
    fi
  done < "$SRC/plugins.txt"
fi

echo "— launchd (claude-home/launchd/*.plist)"
if [ -d "$SRC/launchd" ]; then
  for p in "$SRC"/launchd/*.plist; do
    [ -e "$p" ] || continue
    dst="$HOME/Library/LaunchAgents/$(basename "$p")"
    if [ -f "$dst" ]; then ok "plist    $(basename "$p")"
    elif [ "$MODE" = check ]; then bad "MISSING  $dst"
    else mkdir -p "$(dirname "$dst")"; cp "$p" "$dst"; ok "copied   $dst   (load: launchctl bootstrap gui/$(id -u) \"$dst\")"; fi
  done
fi

echo "— reel-editor-th (venv from requirements.txt; assets are NOT in git)"
RE="$REPO/.claude/skills/reel-editor-th"
if [ -d "$RE" ]; then
  if [ -x "$RE/.venv/bin/python" ]; then ok "venv     reel-editor-th/.venv"
  elif [ -f "$RE/requirements.txt" ]; then
    if [ "$MODE" = check ]; then bad "MISSING  reel-editor-th/.venv (install builds it from requirements.txt)"
    else py="$(command -v python3.12 || command -v python3)"; "$py" -m venv "$RE/.venv" && "$RE/.venv/bin/pip" -q install -r "$RE/requirements.txt" && ok "built    reel-editor-th/.venv ($py)" || bad "FAILED   venv build"; fi
  fi
  if [ -d "$RE/assets/mooniex-broll" ]; then ok "assets   reel-editor-th/assets/mooniex-broll"
  else bad "MISSING  reel-editor-th/assets/mooniex-broll (210 MB, not in git — restore from Drive per gdrive-filing / Assets/)"; fi
fi

echo
if [ "$DRIFT" -gt 0 ]; then echo "claude-home: $DRIFT problem(s) — see red lines above"; exit 1
else echo "claude-home: clean — ~/.claude is fully derived from $SRC"; fi
