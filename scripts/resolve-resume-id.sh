#!/usr/bin/env bash
# Resolve an org session id before passing it to claude -r.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-}"
VALUE="${2:-}"
UUID_PATTERN='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
if [[ "$VALUE" =~ $UUID_PATTERN ]]; then
  printf '%s\n' "$VALUE"
  exit 0
fi
if ! [[ "$VALUE" =~ ^[0-9a-f]{8}$ ]]; then
  echo "refuse to resume: expected 8 lowercase hex characters or a full UUID" >&2
  exit 2
fi

UUID_FILE="${RESOLVE_LOCKS_DIR:-$ROOT/state/locks}/$ROLE-$VALUE.uuid"
TARGET=""
HUB_ERR_LINE=""
if [ -f "$UUID_FILE" ]; then
  TARGET="$(tr -d '[:space:]' <"$UUID_FILE" 2>/dev/null || true)"
fi
if ! [[ "$TARGET" =~ $UUID_PATTERN ]]; then
  # The override is an executable path; keep paths containing spaces intact.
  ORG_PYTHON=(bash "$ROOT/scripts/hub/org-python.sh")
  if [ -n "${RESOLVE_ORG_PYTHON:-}" ]; then
    ORG_PYTHON=("$RESOLVE_ORG_PYTHON")
  fi
  HUB_ERR_FILE="$(mktemp "${TMPDIR:-/tmp}/resolve-resume-err.XXXXXX")"
  trap 'rm -f "$HUB_ERR_FILE"' EXIT
  TARGET="$(cd "$ROOT" && "${ORG_PYTHON[@]}" -m tools.session_status resume \
    --role "$ROLE" --session-id "$VALUE" 2>"$HUB_ERR_FILE" || true)"
  TARGET="$(printf '%s' "$TARGET" | tr -d '[:space:]')"
  if [ -s "$HUB_ERR_FILE" ]; then
    HUB_ERR_LINE="$(tail -n 1 "$HUB_ERR_FILE" | sed -nE 's/^([A-Za-z_][A-Za-z0-9_.]*(Error|Exception))\b.*/\1/p')"
    HUB_FAILED=1
  fi
  rm -f "$HUB_ERR_FILE"
fi
if [[ "$TARGET" =~ $UUID_PATTERN ]]; then
  printf '%s\n' "$TARGET"
  exit 0
fi
HUB_SUFFIX=""
if [ -n "${HUB_FAILED:-}" ]; then
  HUB_SUFFIX="; hub: error"
fi
if [ -n "$HUB_ERR_LINE" ]; then
  HUB_SUFFIX="; hub: unreachable or refused ($HUB_ERR_LINE)"
fi
echo "refuse to resume $ROLE-$VALUE: no resumable UUID found; checked $UUID_FILE and c_level_sessions.resume_uuid via tools.session_status resume (role=$ROLE, session_id=$VALUE)$HUB_SUFFIX" >&2
exit 2
