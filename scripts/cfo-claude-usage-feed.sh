#!/usr/bin/env bash
# CFO Claude Max usage feed → Supabase (daily, 1 row/day)
#
# Claude Max subscription = องค์กรจ่ายก้อนใหญ่สุด (~$100-200/mo) แต่ไม่มี telemetry
# ใน CFO DB. Script นี้ดึง % utilization จาก OAuth usage endpoint (token ใน Keychain
# ของ Claude Code — pattern เดียวกับ claude-usage-sync.sh ที่ feed iPhone widget) แล้ว
# POST 1 row/วัน เข้า webapp_cfo_api_events.
#
# *** cost_usd = null เสมอ ***
# Max เป็น fixed subscription ที่อยู่ใน webapp_cfo_subscriptions อยู่แล้ว — ใส่ $ ที่นี่
# = double count. row นี้บันทึก "การใช้งาน" (utilization %) ไม่ใช่ "ค่าใช้จ่าย".
#
# Row schema ต้องตรงกับ _post() ใน mooniex-webapp/src/lib/cfo/track.py (ห้ามเปลี่ยน field list).
# Called by: ~/Library/LaunchAgents/com.mooniex.cfo-claude-usage.plist (daily 06:30 local,
#   ก่อน cfo-rollup cron 00:05 UTC = 07:05 ICT).
#
# Secrets: อ่าน SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY จาก ~/.config/mooniex/cfo.env (chmod 600).
#   ไม่มีไฟล์/key → สร้าง template ว่าง + exit 0 (no-op, ไม่ error spam ใน launchd log).
#   ห้าม hardcode / ห้าม commit key. service-role key ห้ามโผล่ใน log.
#
# Usage:
#   cfo-claude-usage-feed.sh            # fetch + POST 1 row
#   cfo-claude-usage-feed.sh --dry-run  # print row ที่จะ POST โดยไม่ยิงจริง (ไม่แตะ config)
set -euo pipefail

CONFIG_DIR="$HOME/.config/mooniex"
CONFIG="$CONFIG_DIR/cfo.env"
TABLE="webapp_cfo_api_events"
USAGE_URL="https://api.anthropic.com/api/oauth/usage"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# single-line, key-free log → stdout (launchd StandardOutPath); no `set -x`, never echo the key.
log() { printf '%s cfo-claude-usage: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

JQ=/opt/homebrew/bin/jq
[ -x "$JQ" ] || JQ=$(command -v jq) || { log "jq not found — no-op"; exit 0; }

# --- 1. OAuth token from Keychain (same source as claude-usage-sync.sh) ----
TOKEN=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null \
  | "$JQ" -r '.claudeAiOauth.accessToken // empty' 2>/dev/null) || true
[ -n "$TOKEN" ] || { log "no Claude Code credentials in Keychain — no-op"; exit 0; }

# --- 2. fetch usage payload ------------------------------------------------
RESP=$(curl -sf --max-time 20 "$USAGE_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "anthropic-beta: oauth-2025-04-20") \
  || { log "usage fetch failed (token expired / network?) — no-op, retry tomorrow"; exit 0; }

# --- 3. build the row (field list LOCKED to track.py _post) ----------------
# cost_usd:null on purpose (see header). utilization % lives in tags only.
ROW=$(printf '%s' "$RESP" | "$JQ" -c '{
  provider: "anthropic",
  project_key: "agents",
  model: null,
  agent_role: "org",
  agent_id: "claude-max",
  request_id: null,
  prompt_tokens: null,
  completion_tokens: null,
  cost_usd: null,
  latency_ms: null,
  status: "success",
  tags: {
    kind: "subscription_utilization",
    five_hour_pct: .five_hour.utilization,
    seven_day_pct: .seven_day.utilization,
    seven_day_opus_pct: .seven_day_opus.utilization,
    seven_day_sonnet_pct: .seven_day_sonnet.utilization
  }
}') || { log "row build failed (unexpected payload shape) — no-op"; exit 0; }

# --- 4. dry-run: print the row, no POST, no config side-effects ------------
if [ "$DRY_RUN" -eq 1 ]; then
  log "DRY-RUN — row that would POST to $TABLE (no request sent):"
  printf '%s' "$ROW" | "$JQ" '.'
  exit 0
fi

# --- 5. secrets (never hardcoded / committed) ------------------------------
if [ ! -f "$CONFIG" ]; then
  # bootstrap an empty 600 template so the CEO has a discoverable place to fill keys
  mkdir -p "$CONFIG_DIR" && chmod 700 "$CONFIG_DIR"
  ( umask 177; cat > "$CONFIG" <<'TEMPLATE'
# Mooniex CFO feed secrets — fill these in (then this file stays chmod 600).
# Service-role key bypasses RLS; keep private, NEVER commit, never paste in chat.
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
TEMPLATE
  )
  chmod 600 "$CONFIG"
  log "created template $CONFIG — fill SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY, then it feeds (no-op this run)"
  exit 0
fi

# shellcheck disable=SC1090
set -a; . "$CONFIG"; set +a

if [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  log "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY empty in $CONFIG — no-op (fill keys to enable)"
  exit 0
fi

# --- 6. POST (headers mirror track.py _post) -------------------------------
RESP_FILE=$(mktemp)
trap 'rm -f "$RESP_FILE"' EXIT
HTTP=$(curl -sS -o "$RESP_FILE" -w '%{http_code}' --max-time 15 \
  -X POST "${SUPABASE_URL%/}/rest/v1/$TABLE" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  --data "$ROW") || { log "POST curl error (network?) — exit 1"; exit 1; }

case "$HTTP" in
  2*)
    PCTS=$(printf '%s' "$ROW" | "$JQ" -rc '.tags | "5h=\(.five_hour_pct) 7d=\(.seven_day_pct) opus=\(.seven_day_opus_pct) sonnet=\(.seven_day_sonnet_pct)"')
    log "inserted 1 row into $TABLE http $HTTP ($PCTS, cost_usd=null)"
    ;;
  *)
    log "insert REJECTED http $HTTP: $(tr -d '\n' < "$RESP_FILE" | cut -c1-300)"
    exit 1
    ;;
esac
