#!/usr/bin/env bash
# Emergency Shortcut: Open AGY CLI to take over stalled Claude Code work across Mac, Contabo, or Winbox.
#
# Usage:
#   agy-takeover                     # Scan Mac/Contabo/Winbox & open interactive AGY CLI with /takeover
#   agy-takeover CnDrama             # Inspect CnDrama session & open interactive AGY CLI with full handoff context
#   agy-takeover --scan              # Only print cross-host scan table (non-interactive)
#   agy-takeover --inspect <target>  # Only print the session handoff brief (non-interactive)
#   agy-takeover --brain <target>    # Hand off session directly into headless AGY ph_brain.py
set -euo pipefail

# Resolve Agents/Core root on Mac or Contabo
if [ -d "/Users/gob/MoonieXHQ/Agents/Core" ]; then
  ROOT="/Users/gob/MoonieXHQ/Agents/Core"
elif [ -d "/opt/MoonieXHQ/Agents/Core" ]; then
  ROOT="/opt/MoonieXHQ/Agents/Core"
else
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

AGY_BIN="${AGY_BIN:-$HOME/.local/bin/agy}"
[ -x "$AGY_BIN" ] || AGY_BIN="$(command -v agy 2>/dev/null || echo "$HOME/.local/bin/agy")"

# Pick best available AGY model (Opus 5.5 primary -> Argon High automatic fallback)
MODEL="$("$PY" -c "
import sys
sys.path.insert(0, '$ROOT')
from tools.ph_brain import select_model_chain
print(select_model_chain()[0])
" 2>/dev/null || echo "claude-opus-5-5-high")"

cd "$ROOT"

case "${1:-}" in
  --scan|-s)
    shift
    exec "$PY" "$ROOT/tools/agy_takeover.py" scan "$@"
    ;;
  --inspect|-i)
    shift
    exec "$PY" "$ROOT/tools/agy_takeover.py" inspect "$@" --save
    ;;
  --brain|-b)
    shift
    exec "$PY" "$ROOT/tools/agy_takeover.py" handoff-to-brain "$@"
    ;;
  --help|-h)
    sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
esac

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "🔍 Scanning Mac, Contabo, and Winbox for stalled Claude Code sessions..."
  "$PY" "$ROOT/tools/agy_takeover.py" scan --limit 8 || true
  echo ""
  echo "🚀 Launching AGY CLI (model=$MODEL) with /takeover skill..."
  exec "$AGY_BIN" \
    --model "$MODEL" \
    --mode accept-edits \
    --add-dir "$ROOT" \
    -i "/takeover สรุปรายการงานค้างที่มีเครื่องหมาย 🚨 LIMIT จากผลสแกนด้านบน แล้วถามฉันว่าจะให้รับช่วงโปรเจกต์ไหนต่อ"
else
  echo "📥 Extracting Claude Code session state for '$TARGET'..."
  "$PY" "$ROOT/tools/agy_takeover.py" inspect "$TARGET" --turns 12 --save > /dev/null
  BUNDLE="$ROOT/state/takeover/latest-handoff.md"
  echo "✅ Saved handoff bundle to $BUNDLE"
  echo "🚀 Launching AGY CLI (model=$MODEL) to continue '$TARGET'..."
  exec "$AGY_BIN" \
    --model "$MODEL" \
    --mode accept-edits \
    --add-dir "$ROOT" \
    -i "/takeover อ่านไฟล์ $BUNDLE และ Skill ที่เกี่ยวข้องใน .claude/skills/ แล้วสรุปสถานะล่าสุดของ '$TARGET' พร้อมเริ่มทำ Step ถัดไปต่อจาก Claude Code ทันที"
fi
