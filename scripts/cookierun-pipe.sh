#!/usr/bin/env bash
# cookierun-pipe.sh — drive the Cookie Run app on winbox through its HTTP pipe.
#
#   ./scripts/cookierun-pipe.sh status
#   ./scripts/cookierun-pipe.sh functions
#   ./scripts/cookierun-pipe.sh log [n]
#   ./scripts/cookierun-pipe.sh run <fn> '<json-args>'   # e.g. run bot_start '{"model":"v5","rounds":60}'
#
# The app (app.py) must be running in session 1 — start it with:
#   ssh winbox "powershell -NoProfile -Command \"Start-ScheduledTask -TaskName 'CookieRunAppSrc'\""
# The pipe only exists while that window is up; "PIPE DOWN" means the app is not running,
# NOT that the box is unreachable.
#
# Same idea as tools/appctl.py in the cookierun-bot repo, but callable from any
# machine with an `ssh winbox` alias (Contabo included) without needing the repo.
# The request body travels base64-encoded so no quoting layer can mangle it.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
TOKEN='$env:USERPROFILE\Documents\CookieRunScript\modelplay\pipe_token'

ps_run() {
  local script="$1"
  script="\$ProgressPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; $script"
  local enc
  enc=$(printf '%s' "$script" | iconv -f UTF-8 -t UTF-16LE | base64 -w0)
  ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" \
    "powershell -NoProfile -NonInteractive -EncodedCommand $enc" 2>&1 | tr -d '\r'
}

hdr="@{'X-Pipe-Token'=(Get-Content $TOKEN -Raw).Trim()}"

get() {
  ps_run "try { (Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8794$1' -Headers $hdr -TimeoutSec 20) | ConvertTo-Json -Depth 6 -Compress } catch { Write-Output ('PIPE DOWN: ' + \$_.Exception.Message) }"
}

case "${1:-status}" in
  status)    get /status ;;
  functions) get /functions ;;
  log)       get "/log?n=${2:-50}" ;;
  calls)     get /calls ;;
  run)
    fn="${2:?usage: $0 run <fn> '<json-args>'}"
    args="${3:-{\}}"
    body=$(printf '{"fn":"%s","args":%s,"who":"CTO"}' "$fn" "$args")
    b64=$(printf '%s' "$body" | base64 -w0)
    ps_run "\$b=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$b64')); try { (Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8794/run' -Headers $hdr -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes(\$b)) -TimeoutSec 90) | ConvertTo-Json -Depth 6 -Compress } catch { Write-Output ('PIPE DOWN: ' + \$_.Exception.Message) }"
    ;;
  *) echo "usage: $0 {status|functions|log [n]|calls|run <fn> '<json>'}" >&2; exit 1 ;;
esac
