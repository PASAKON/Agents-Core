#!/usr/bin/env bash
# spawn-ph.sh — start a Project Head for one project (org restructure P2, plan §3.2).
#
#   bash scripts/spawn-ph.sh --project <Name> --kind finite --due <when> [--brief-file <path>]
#   bash scripts/spawn-ph.sh --project <Name> --kind loop --cadence <hours>
#   bash scripts/spawn-ph.sh --resume <session> [--dry-run]
#
# Run it from inside a C-level session. The Project Head's lane is your role and
# its owner is your session; it reports to you and to no one else. Refused unless
# ORG_PH_ROLES=1, roles/project_head.md exists (the COO writes it) and the
# resource gate passes. Prints one JSON line: session id, tmux session, brief path.
# The logic and every refusal live in tools/spawn_ph.py.
#
# Run by a Run Inbox card on another host (M13b): `--project P --from-card N --sha S
# [--brief B]`. The executor runs a pinned COPY of this file from a temp dir, so its
# own location is no checkout. It uses this host's fixed clone instead, only when
# that clone is exactly the card's commit with no changed tracked file and no
# untracked .py where Python would import it, and runs Python isolated (-I, an empty
# pycache_prefix) so nothing outside that commit is loaded (§2b review of #280).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# This host's fixed clone for a card run (never taken from the environment).
CLONE_LINUX=/opt/MoonieXHQ/Agents/Core
CLONE_DARWIN=/Users/gob/MoonieXHQ/Agents/Core

CARD_SHA=""
prev=""
for a in "$@"; do
  if [ "$prev" = "--sha" ]; then CARD_SHA="$a"; fi
  prev="$a"
done
case " $* " in
  *" --from-card "*|*" --sha "*)
    case "$(uname -s)" in
      Darwin) ROOT="$CLONE_DARWIN" ;;
      *) ROOT="$CLONE_LINUX" ;;
    esac
    if ! [[ "$CARD_SHA" =~ ^[0-9a-f]{40}$ ]]; then
      echo "spawn-ph: a card run needs --sha <the card's 40-hex commit>" >&2; exit 2
    fi
    HEAD="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
    if [ "$HEAD" != "$CARD_SHA" ]; then
      echo "spawn-ph: $ROOT is at ${HEAD:-?}, the card is $CARD_SHA: run 'git -C $ROOT pull --ff-only' there first" >&2; exit 2
    fi
    if ! git -C "$ROOT" diff --quiet HEAD --; then
      echo "spawn-ph: $ROOT has changed tracked files; a card runs only a clean checkout" >&2; exit 2
    fi
    STRAY="$(git -C "$ROOT" ls-files --others -- ':(glob)*.py' ':(glob)lib/**/*.py' ':(glob)tools/**/*.py')"
    if [ -n "$STRAY" ]; then
      echo "spawn-ph: untracked Python in $ROOT would be imported: $(echo "$STRAY" | head -3 | tr '\n' ' ')" >&2; exit 2
    fi
    PY="$ROOT/.venv/bin/python"
    [ -x "$PY" ] || PY=python3
    PYC="$(mktemp -d)"
    trap 'rm -rf "$PYC"' EXIT
    cd "$ROOT"
    "$PY" -I -X pycache_prefix="$PYC" "$ROOT/tools/spawn_ph.py" "$@"
    exit $?
    ;;
esac

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=python3
cd "$ROOT"
exec "$PY" -m tools.spawn_ph "$@"
