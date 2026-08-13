#!/bin/bash
# One-shot (CEO-run only): copy the 3 GMAIL_* cred lines from the prod VPS
# claudeflow .env into the local claudeflow .env so the TraderMindset email
# approval loop can send. Values are never printed. Safe to re-run (dedups).
set -euo pipefail
CF=/Users/gob/Projects/mooniex-claudeflow
cp "$CF/.env" "$CF/.env.bak-gmail" 2>/dev/null || true
# drop any half-applied lines from earlier attempts, then append fresh
grep -vE '^(GMAIL_CLIENT_ID|GMAIL_CLIENT_SECRET|GMAIL_REFRESH_TOKEN|TM_APPROVAL_EMAIL)=' "$CF/.env" > "$CF/.env.tmp"
mv "$CF/.env.tmp" "$CF/.env"
ssh mooniex-vps "grep ^GMAIL_ /root/projects/mooniex-claudeflow/.env" >> "$CF/.env"
echo 'TM_APPROVAL_EMAIL=pass.gob1@gmail.com' >> "$CF/.env"
echo "OK-done ($(grep -cE '^GMAIL_' "$CF/.env") gmail keys in local .env)"
