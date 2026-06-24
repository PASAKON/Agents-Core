#!/usr/bin/env bash
# Deploy the Claude usage monitor to the always-on VPS (mooniex-vps = Contabo).
# Idempotent. Usage: bash scripts/vps-claude-usage/deploy.sh
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS="${VPS:-mooniex-vps}"
DEST="/opt/claude-usage-monitor"

# Safety: never deploy to the wrong box (mooniex-vps alias has pointed at a dead
# host before — see LLMs wiki / memory). Contabo prod = vmi3371421.
HN="$(ssh -o ConnectTimeout=12 "$VPS" hostname)"
[ "$HN" = "vmi3371421" ] || { echo "refusing: $VPS hostname=$HN (expected vmi3371421)"; exit 1; }

ssh "$VPS" "mkdir -p $DEST"
scp -q "$SRC/monitor.py"                      "$VPS:$DEST/monitor.py"
scp -q "$SRC/claude-usage-monitor.service"    "$VPS:/etc/systemd/system/claude-usage-monitor.service"
scp -q "$SRC/claude-usage-monitor.timer"      "$VPS:/etc/systemd/system/claude-usage-monitor.timer"

ssh "$VPS" "chmod 755 $DEST/monitor.py \
  && systemctl daemon-reload \
  && systemctl enable --now claude-usage-monitor.timer \
  && systemctl list-timers claude-usage-monitor.timer --no-pager"

echo "deployed to $VPS:$DEST"
