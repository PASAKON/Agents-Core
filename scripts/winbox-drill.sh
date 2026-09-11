#!/usr/bin/env bash
# winbox-drill.sh — prove every pipe to the Windows box actually works, right now.
#
# Written 2026-09-11, three hours before the CEO left for seven days. The point is not to
# read configuration and believe it: every check below USES the pipe it is testing, because
# a service marked "Automatic" that is in fact wedged looks identical from the registry.
#
#   bash scripts/winbox-drill.sh          full drill
#   bash scripts/winbox-drill.sh --quick  skip the Astra call (costs ChatGPT tokens)

set -uo pipefail
HOST="${WINBOX_HOST:-winbox}"
QUICK="${1:-}"
pass=0; fail=0; warn=0

ok()   { echo "  ✅ $*"; pass=$((pass+1)); }
bad()  { echo "  ❌ $*"; fail=$((fail+1)); }
note() { echo "  ⚠️  $*"; warn=$((warn+1)); }
hd()   { echo; echo "── $* ──"; }

ps1() { ssh -o ConnectTimeout=15 -n "$HOST" "powershell -NoProfile -Command \"$1\"" 2>&1; }

echo "WINBOX DRILL · $(TZ=Asia/Bangkok date '+%F %H:%M') Thai · host=$HOST"

hd "1. Network + SSH"
if out=$(ssh -o ConnectTimeout=15 -n "$HOST" 'echo UP' 2>&1) && [[ "$out" == *UP* ]]; then
  ok "SSH reachable"
else
  bad "SSH DEAD — $out"
  echo; echo "Nothing else can be tested. Recovery: see docs/runbooks/winbox-recovery.md"; exit 1
fi
hn=$(ps1 'hostname' | tr -d '\r')
ok "host answers as $hn"

hd "2. Services that must survive a reboot"
for s in Tailscale sshd; do
  st=$(ps1 "(Get-Service $s).StartType" | tr -d '\r ')
  ru=$(ps1 "(Get-Service $s).Status"    | tr -d '\r ')
  [[ "$st" == "Automatic" ]] && ok "$s StartType=Automatic" || bad "$s StartType=$st (must be Automatic)"
  [[ "$ru" == "Running"   ]] && ok "$s is running"          || bad "$s is $ru"
done

hd "3. The box must not sleep or lock itself away"
sl=$(ps1 'powercfg /q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE' | grep -i 'Current AC' | head -1)
[[ "$sl" == *0x00000000* ]] && ok "sleep on AC = never" || bad "sleep on AC is SET — $sl"
# Test the thing that actually matters — is somebody logged in at the console right now —
# not the AutoAdminLogon flag. Measured 2026-09-11: the flag reads 0, and the box still
# came back to a logged-in desktop after a real reboot in 125 s, because the account has
# no password. Checking the flag produced a warning that was simply false.
cu=$(ps1 '(Get-CimInstance Win32_ComputerSystem).UserName' | tr -d '\r' | tr -d ' ')
if [[ -n "$cu" ]]; then ok "desktop session live as $cu — GUI work is possible"
else bad "NOBODY logged in at the console — Chrome, Resolve and any GUI worker are dead until someone logs in"; fi

hd "4. Disk and load"
fr=$(ps1 '[math]::Round((Get-PSDrive C).Free/1GB,1)' | tr -d '\r ')
if   (( $(echo "$fr > 30" | bc -l) )); then ok "C: ${fr} GB free"
elif (( $(echo "$fr > 10" | bc -l) )); then note "C: only ${fr} GB free"
else bad "C: ${fr} GB free — too low"; fi

hd "5. Machine lock (who owns the box)"
lk=$(ps1 'Get-Content C:\mooniex\MACHINE-LOCK.txt -Raw -ErrorAction SilentlyContinue' | tr -d '\r')
if [[ -z "${lk// /}" ]]; then ok "lock is FREE"; else note "lock held by: ${lk}"; fi

hd "6. Codex is installed and still authenticated"
cv=$(ssh -o ConnectTimeout=20 -n "$HOST" 'codex --version' 2>&1 | tr -d '\r')
[[ "$cv" == *codex* ]] && ok "$cv" || bad "codex not found — $cv"
ls=$(ssh -o ConnectTimeout=20 -n "$HOST" 'codex login status' 2>&1 | tr -d '\r')
[[ "$ls" == *"Logged in"* ]] && ok "$ls" || bad "NOT LOGGED IN — $ls"

hd "7. Astra answers (the real end-to-end test)"
if [[ "$QUICK" == "--quick" ]]; then
  note "skipped (--quick)"
else
  a=$(ssh -o ConnectTimeout=30 -n "$HOST" \
      'codex exec -s read-only --skip-git-repo-check -C C:\mooniex\astra-workspace "Reply with exactly: DRILL OK"' 2>&1)
  [[ "$a" == *"DRILL OK"* ]] && ok "Astra replied DRILL OK" || bad "Astra did not answer — $(echo "$a" | tail -3)"
fi

hd "8. Remote hands — can a human get a screen?"
vnc=$(ps1 'Get-Service -Name "*vnc*","*tvnserver*" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Status' | tr -d '\r ')
if [[ -n "$vnc" ]]; then ok "VNC service present and $vnc"
else bad "NO VNC — if a login screen appears, nobody can reach it from a phone"; fi

echo
echo "═══ PASS $pass · WARN $warn · FAIL $fail ═══"
[[ $fail -eq 0 ]] && echo "All pipes up." || echo "SOMETHING IS DOWN — docs/runbooks/winbox-recovery.md"
exit $fail
