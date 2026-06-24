#!/usr/bin/env bash
# Claude Code subscription usage → iPhone widget feed
# ดึง % session(5h)/weekly จาก OAuth usage endpoint (token ใน Keychain ของ Claude Code)
# แล้วเขียน claude-usage.json ลงโฟลเดอร์ iCloud ของ Scriptable ให้ widget บน iPhone อ่าน
# เรียกโดย: ~/Library/LaunchAgents/com.mooniex.claude-usage-sync.plist (ทุก 10 นาที)
set -euo pipefail

OUT_DIR="$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents"
OUT="$OUT_DIR/claude-usage.json"

[ -d "$OUT_DIR" ] || exit 0  # Scriptable iCloud ยังไม่พร้อม — ข้ามรอบนี้

JQ=/opt/homebrew/bin/jq
[ -x "$JQ" ] || JQ=$(command -v jq)

TOKEN=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null \
  | "$JQ" -r '.claudeAiOauth.accessToken // empty')
[ -n "$TOKEN" ] || exit 1

RESP=$(curl -sf --max-time 20 "https://api.anthropic.com/api/oauth/usage" \
  -H "Authorization: Bearer $TOKEN" \
  -H "anthropic-beta: oauth-2025-04-20" \
  -H "User-Agent: claude-cli/2.1.187 (external, cli)") || exit 1
# หมายเหตุ: ถ้า token หมดอายุ (401) จะ exit 1 — Claude Code จะ refresh token เองรอบถัดไปที่ CEO ใช้งาน

# launchd context: iCloud Drive (~/Library/Mobile Documents) is TCC-protected.
# A LaunchAgent run by /bin/bash needs Full Disk Access, or every write EPERMs
# ("Operation not permitted"). Interactive shells inherit FDA from the terminal,
# so this works by hand but dies silently under launchd until /bin/bash is granted
# Full Disk Access in System Settings > Privacy & Security > Full Disk Access.
BODY=$(echo "$RESP" | "$JQ" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{generated_at: $ts, five_hour, seven_day, seven_day_opus, seven_day_sonnet, extra_usage}')
[ -n "$BODY" ] || exit 1
rm -f "$OUT" "$OUT.tmp" 2>/dev/null || true
# subshell isolates the redirect-open error so a TCC denial is reported, not raw
if ( printf '%s\n' "$BODY" > "$OUT" ) 2>/dev/null; then
  printf '%s claude-usage-sync: wrote %s (5h=%s%% 7d=%s%%)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$OUT" \
    "$(printf '%s' "$BODY" | "$JQ" -r '.five_hour.utilization // "?"')" \
    "$(printf '%s' "$BODY" | "$JQ" -r '.seven_day.utilization // "?"')"
else
  printf '%s claude-usage-sync: WRITE FAILED to iCloud — grant Full Disk Access to /bin/bash, then it heals\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >&2
  exit 1
fi
