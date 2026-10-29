#!/usr/bin/env bash
# winbox-restart.sh --sha <40-hex> [--dry-run] [--wait-max SECONDS]
# winbox-restart.sh --register-logon-task   --sha <40-hex> [--dry-run]
# winbox-restart.sh --unregister-logon-task --sha <40-hex> [--dry-run]
#
# SafeRestart for winbox, run on Contabo by a CEO-approved Run card:
#   1. the winbox clone must be exactly at --sha with no changed tracked file;
#   2. no Run card may be running on winbox;
#   3. MooniexOrgResume (windows\register-org-resume.ps1) must be registered, or the
#      sessions would be saved and then never come back;
#   4. take the PC lease (the night's farm parks; the CEO's hold refuses the whole run);
#   5. `restart_run.py --host winbox prep` saves every winbox Claude session. It types
#      into Windows Terminal tabs, so it runs in the console session through a one-shot
#      interactive task (ssh lands in session 0, which has no desktop);
#   6. ONLY when prep exits 0: `shutdown /r /t 60`. At logon MooniexOrgResume reopens
#      each saved session in its own tab (windows\org-resume-logon.ps1).
# A prep that fails does not reboot; it brings back what it closed (`resume`), like
# scripts/org-restart.sh does on Contabo.
#
#   --dry-run   print everything this would do; run `prep --dry-run` only (over plain
#               ssh, session 0: no task is registered, no key is typed, no lease is
#               taken, nothing is rebooted). A wrong --sha or a missing logon task is a
#               warning here and a refusal in a real run.
#
# --register-logon-task / --unregister-logon-task (one Run card each, the CEO taps it on his
# phone; nobody goes to the winbox desk): after the same clone == --sha check, run
# windows\register-org-resume.ps1 (with -Remove for unregister) in the console session
# through the same one-shot interactive task prep uses, then print the state of
# MooniexOrgResume. The .ps1 itself refuses to run in session 0. No lease and no keystroke:
# nothing here touches the desktop. A restart is not part of either mode.
#
# Env: WINBOX_HOST (ssh alias, default winbox), WINBOX_REPO (the clone, default
# C:\Users\passg\mooniex\repo\MoonieX-Agents).
# WINBOX_POLL_SEC (default 5) paces the wait for the console-session task; tests lower it.
# Exit: 0 done (rebooting; or the logon task is now in the state asked for) | 1 prep/rollback failed | 2 usage or the clone is wrong |
#       3 refused (CEO hold, running card, safety gate) | 4 the logon task is missing.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
REPO_DEFAULT='C:\Users\passg\mooniex\repo\MoonieX-Agents'
REPO_WIN="${WINBOX_REPO:-$REPO_DEFAULT}"
WORK_WIN='C:\mooniex\restart'      # the one-shot task's scratch: script, output, exit code
TASK='mooniex-restart-run'
LOGON_TASK='MooniexOrgResume'
LEASE_WHO='SafeRestart winbox'     # the same string windows\org-resume-logon.ps1 and restart_run.py use
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

sha=''
dry=0
wait_max=240
mode=restart                       # restart | register | unregister
poll="${WINBOX_POLL_SEC:-5}"
while (( $# )); do
  case "$1" in
    --register-logon-task) [[ "$mode" == restart ]] || { echo "give only one of --register-logon-task / --unregister-logon-task"; exit 2; }; mode=register; shift ;;
    --unregister-logon-task) [[ "$mode" == restart ]] || { echo "give only one of --register-logon-task / --unregister-logon-task"; exit 2; }; mode=unregister; shift ;;
    --sha) sha="${2:?--sha needs a value}"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    --wait-max) wait_max="${2:?--wait-max needs a value}"; shift 2 ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
done

die()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit "${2:-1}"; }
warn() { printf '\033[33m! %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
# Real runs refuse; a dry run says so and goes on, so it can show everything else.
refuse() { if (( dry )); then warn "dry run: would refuse: $1"; else die "$1" "${2:-3}"; fi; }

[[ "$wait_max" =~ ^[0-9]+$ ]] || die "--wait-max must be a whole number of seconds" 2
[[ "$poll" =~ ^[1-9][0-9]*$ ]] || die "WINBOX_POLL_SEC must be a whole number of seconds, at least 1" 2
[[ "$REPO_WIN" =~ ^[A-Za-z]:\\[A-Za-z0-9_.\\-]+$ ]] || die "WINBOX_REPO must be a plain Windows path without spaces: $REPO_WIN" 2
if [[ -n "$sha" ]]; then
  [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || die "--sha must be 40 lowercase hex characters" 2
elif (( ! dry )); then
  die "--sha <the commit the card was approved for> is required" 2
fi

# shellcheck source=lib/winbox_deploy.sh
. "$HERE/scripts/lib/winbox_deploy.sh"      # winbox_ps: PowerShell over ssh as -EncodedCommand

mkdir -p state/restart
exec 9>state/restart/operation-winbox.lock
flock -n 9 || die "another winbox restart is running" 1

ssh_out() { ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" "$@" | tr -d '\r'; }

label=''; (( dry )) && label=' (dry run)'
case "$mode" in register) label=" --register-logon-task$label" ;; unregister) label=" --unregister-logon-task$label" ;; esac
echo "== winbox SafeRestart$label host=$HOST clone=$REPO_WIN sha=${sha:-none}"

# ---- 1. the clone is the commit the card names --------------------------------------
head=$(ssh_out "git -C $REPO_WIN rev-parse HEAD" 2>/dev/null || true)
dirty=$(ssh_out "git -C $REPO_WIN status --porcelain --untracked-files=no" 2>/dev/null || true)
if [[ -z "$sha" ]]; then
  warn "no --sha: clone is at ${head:-unknown}; a real run needs --sha"
elif [[ "$head" != "$sha" ]]; then
  refuse "$REPO_WIN is at ${head:-unknown}, the card names $sha: on winbox run  git -C $REPO_WIN pull --ff-only" 2
else
  ok "clone is at $sha"
fi
[[ -z "$dirty" ]] || refuse "$REPO_WIN has changed tracked files; a restart runs only a clean checkout:
$dirty" 2

if [[ "$mode" == restart ]]; then
# ---- 2. no Run card is using winbox (including work over ssh from another host) --------
# winbox has no Run Inbox token, so prep cannot look; this side does, and tells prep with
# --cards-checked. The restart card itself runs on Contabo and is not in the way.
cards_json=$(bash scripts/hub/org-python.sh tools/ask_run.py list --status running --json 2>/dev/null) || cards_json=''
if [[ -z "$cards_json" ]]; then
  refuse "Run cards unreadable here (no Run Inbox token?): a card running on winbox cannot be ruled out" 3
else
  busy=$(CARDS_JSON="$cards_json" python3 -c '
import json, os, shlex, sys
try:
    cards = json.loads(os.environ["CARDS_JSON"])
except ValueError:
    sys.exit(1)
if not isinstance(cards, list):
    sys.exit(1)
# ask_run.cmd_list preserves hub fields; _what also accepts serialized script_json.
# Alias and mesh address from config/hosts.yaml; passg@ covers direct user@host ssh.
patterns = ("winbox", "flow_shoot", "passg@", "100.124.196.11")
restart = "scripts/winbox-restart.sh"

def restart_words(words):
    if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
        return False
    # Only a direct invocation or bash/sh script invocation, never an arbitrary
    # mention in an argument/cwd, a suffixed filename, or a compound shell command.
    if any(any(c in w for c in ";|&<>`$\n") for w in words):
        return False
    if words and words[0] in ("bash", "sh", "/bin/bash", "/bin/sh"):
        words = words[1:]
    return bool(words) and words[0] in (restart, "./" + restart)

def is_restart(card):
    script = card.get("script") or card.get("script_json")
    if isinstance(script, str):
        try:
            script = json.loads(script)
        except ValueError:
            pass
    if isinstance(script, dict) and script.get("path") == restart:
        return True
    command = card.get("command")
    if isinstance(command, str):
        if any(c in command for c in ";|&<>`$\n"):
            return False
        try:
            return restart_words(shlex.split(command))
        except ValueError:
            return False
    return restart_words(card.get("argv"))

for card in cards:
    if not isinstance(card, dict) or is_restart(card):
        continue
    host = card.get("host")
    text = json.dumps([card.get(key) for key in
                       ("command", "script", "script_json", "argv", "cwd")]).lower()
    reasons = []
    if host in ("winbox", None, ""):
        reasons.append("host=" + repr(host))
    reasons.extend("pattern=" + pattern for pattern in patterns if pattern in text)
    if reasons:
        print(str(card.get("id", "?")) + " (" + ", ".join(reasons) + ")")
') || { refuse "Run cards unreadable here: ask_run answered with something that is not a card list" 3; busy=''; }
  if [[ -n "$busy" ]]; then
    refuse "a Run card is running on winbox, and the restart would kill it: $(echo "$busy" | tr '\n' ' ')" 3
  else
    ok "no Run card is running on winbox"
  fi
fi

# ---- 3. the logon task exists ---------------------------------------------------------
if ssh_out "schtasks /query /tn $LOGON_TASK" >/dev/null 2>&1; then
  ok "$LOGON_TASK is registered"
else
  refuse "$LOGON_TASK is not registered on winbox: sessions would be saved and never reopened. Register it first with a CEO card: bash scripts/winbox-restart.sh --register-logon-task --sha ${sha:-<40-hex>}" 4
fi
fi   # mode == restart

# ---- the one-shot interactive task: restart_run.py in the console session ---------------
# $1 = prep | resume | register | unregister. Prints the output; returns the exit code of
# restart_run.py (prep, resume) or of windows\register-org-resume.ps1 (register; unregister = -Remove).
inner_script() {
  cat <<'PSEOF'
# restart-inner.ps1 - written by scripts/winbox-restart.sh; runs once, in the console session.
param([string]$Root, [string]$Verb, [int]$WaitMax = 240)
$ErrorActionPreference = 'Continue'
$dir = 'C:\mooniex\restart'
$out = Join-Path $dir 'run.out'
$exitFile = Join-Path $dir 'run.exit'
Remove-Item -LiteralPath $out, $exitFile -ErrorAction SilentlyContinue
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch {}
$code = 98
try {
    Set-Location -LiteralPath $Root
    if ($Verb -eq 'register' -or $Verb -eq 'unregister') {
        # The logon task. register-org-resume.ps1 refuses session 0 itself (exit 2).
        $psArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $Root 'windows\register-org-resume.ps1'))
        if ($Verb -eq 'unregister') { $psArgs += '-Remove' }
        & powershell.exe @psArgs 2>&1 | ForEach-Object { "$_" } | Out-File -LiteralPath $out -Encoding utf8
        $code = $LASTEXITCODE
    } else {
        $py = Join-Path $Root '.venv\Scripts\python.exe'
        $runArgs = @('--host', 'winbox', $Verb, '--wait-max', "$WaitMax")
        if ($Verb -eq 'prep') { $runArgs += '--cards-checked' }
        & $py -E -s (Join-Path $Root 'tools\infisical_setup.py') run Agents-Core prod --as winbox -- $py -I -X utf8 (Join-Path $Root 'tools\restart_run.py') @runArgs 2>&1 |
            ForEach-Object { "$_" } | Out-File -LiteralPath $out -Encoding utf8
        $code = $LASTEXITCODE
    }
} catch {
    "inner error: $_" | Out-File -LiteralPath $out -Append -Encoding utf8
    $code = 98
}
Set-Content -LiteralPath $exitFile -Value $code -Encoding ASCII
exit $code
PSEOF
}

task_registered=0
lease_taken=0
give_back() { if (( lease_taken )); then bash scripts/pc-lease.sh give-back || true; lease_taken=0; fi; }
unregister_run_task() {
  if (( task_registered )); then
    winbox_ps "Unregister-ScheduledTask -TaskName '$TASK' -Confirm:\$false -ErrorAction SilentlyContinue" >/dev/null 2>&1 || true
    task_registered=0
  fi
}
# Whatever happens (a refusal, ^C, the card being cancelled): the one-shot task goes, the PC is given back.
trap 'unregister_run_task; give_back' EXIT

console_run() {
  local verb="$1" tmp code i n limit=3300
  tmp=$(mktemp)
  inner_script > "$tmp"
  winbox_ps "New-Item -ItemType Directory -Force -Path '$WORK_WIN' | Out-Null" >/dev/null
  scp -q -o BatchMode=yes "$tmp" "$HOST:C:/mooniex/restart/restart-inner.ps1" || { rm -f "$tmp"; die "could not copy the runner script to $HOST"; }
  rm -f "$tmp"
  task_registered=1
  winbox_ps "
\$ErrorActionPreference='Stop'
\$me=[Security.Principal.WindowsIdentity]::GetCurrent().Name
Unregister-ScheduledTask -TaskName '$TASK' -Confirm:\$false -ErrorAction SilentlyContinue
Remove-Item '$WORK_WIN\\run.out','$WORK_WIN\\run.exit' -ErrorAction SilentlyContinue
\$a=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File $WORK_WIN\\restart-inner.ps1 -Root $REPO_WIN -Verb $verb -WaitMax $wait_max'
\$p=New-ScheduledTaskPrincipal -UserId \$me -LogonType Interactive -RunLevel Limited
\$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 60) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName '$TASK' -Action \$a -Principal \$p -Settings \$s -Force | Out-Null
Start-ScheduledTask -TaskName '$TASK'
'started'" | grep -qx started || die "could not start the console-session task on $HOST"
  echo "$verb is running on $HOST in the console session ..."
  code=''
  n=0
  while (( n * poll < limit )); do
    sleep "$poll"
    n=$((n + 1))
    code=$(winbox_ps "if (Test-Path '$WORK_WIN\\run.exit') { (Get-Content -Raw '$WORK_WIN\\run.exit').Trim() }" 2>/dev/null || true)
    [[ "$code" =~ ^[0-9]+$ ]] && break
    code=''
    (( n * poll % 60 )) || echo "  ... still running ($((n * poll / 60)) min)"
  done
  [[ -n "$code" ]] || { echo "no result from $HOST after $((limit / 60)) min; the task is left unregistered, state is on the box under $WORK_WIN"; return 1; }
  local out; out=$(mktemp)
  scp -q -o BatchMode=yes "$HOST:C:/mooniex/restart/run.out" "$out" && sed '1s/^\xEF\xBB\xBF//' "$out" || echo "(no output file)"
  rm -f "$out"
  unregister_run_task
  return "$code"
}

# ---- --register-logon-task / --unregister-logon-task ---------------------------------------
# State of MooniexOrgResume as the box reports it: Ready | Running | Disabled | not registered.
logon_state() {
  winbox_ps "\$t = Get-ScheduledTask -TaskName '$LOGON_TASK' -ErrorAction SilentlyContinue; if (\$t) { [string]\$t.State } else { 'not registered' }" 2>/dev/null | tail -1
}

if [[ "$mode" != restart ]]; then
  ps1_line="powershell -NoProfile -ExecutionPolicy Bypass -File $REPO_WIN\\windows\\register-org-resume.ps1"
  [[ "$mode" == unregister ]] && ps1_line="$ps1_line -Remove"
  echo "-- $mode the logon task: in the console session, as the one-shot task '$TASK' (Interactive, no elevation, no lease, no keystroke):"
  echo "   $ps1_line"
  echo "-- $LOGON_TASK now: $(logon_state)"
  if (( dry )); then
    echo "dry run finished: nothing was changed"
    exit 0
  fi
  status=0
  console_run "$mode" || status=$?
  state=$(logon_state)
  echo "-- $LOGON_TASK state: ${state:-unknown}"
  (( status == 0 )) || die "register-org-resume.ps1 exited $status (output above): $LOGON_TASK is $state" 1
  if [[ "$mode" == register ]]; then
    [[ "$state" == Ready || "$state" == Running ]] || die "$LOGON_TASK is '${state:-unknown}' after register; expected Ready" 1
    ok "$LOGON_TASK is registered ($state): at the next logon it reopens the sessions saved by a restart"
  else
    [[ "$state" == 'not registered' ]] || die "$LOGON_TASK is still '${state:-unknown}' after unregister" 1
    ok "$LOGON_TASK is removed: a restart would refuse (exit 4) until it is registered again"
  fi
  exit 0
fi

# ---- dry run: prep --dry-run over plain ssh, then say what a real run adds ---------------
run_prep_dry() {
  ssh -o BatchMode=yes -n "$HOST" "cd /d $REPO_WIN && .venv\\Scripts\\python.exe -E -s tools\\infisical_setup.py run Agents-Core prod --as winbox -- .venv\\Scripts\\python.exe -I -X utf8 tools\\restart_run.py --host winbox prep --dry-run --wait-max 0 --cards-checked" 2>&1 | tr -d '\r'
}

if (( dry )); then
  echo "-- prep --dry-run (session 0: nothing is typed, saved, closed or registered)"
  status=0
  run_prep_dry || status=${PIPESTATUS[0]}
  echo "-- prep --dry-run exited $status"
  cat <<EOF
-- a real run would also:
   take the PC lease:        bash scripts/pc-lease.sh take --who "$LEASE_WHO" --minutes 45   (give-back at the end)
   register + start (then remove) the one-shot task '$TASK' (Interactive, no elevation) that runs
     $REPO_WIN\\.venv\\Scripts\\python.exe -E -s tools\\infisical_setup.py run Agents-Core prod --as winbox -- ... -I -X utf8 tools\\restart_run.py --host winbox prep --wait-max $wait_max --cards-checked
     in the console session (wake.ps1 types /session-save into each session's tab behind the lease gate)
   if prep exits 0:           ssh $HOST shutdown /r /t 60
   if prep fails:             no reboot; the same task runs 'resume' to reopen what prep closed
   at logon:                  $LOGON_TASK -> windows\\org-resume-logon.ps1 -> restart_run.py resume, then report --notify
   the logon task itself:     bash scripts/winbox-restart.sh --register-logon-task   --sha <40-hex>   (CEO card)
                              bash scripts/winbox-restart.sh --unregister-logon-task --sha <40-hex>   (CEO card)
EOF
  echo "dry run finished: nothing was changed (prep --dry-run exit $status)"
  exit "$status"
fi

# ---- 4. the PC lease ---------------------------------------------------------------------
if bash scripts/pc-lease.sh take --who "$LEASE_WHO" --minutes 45; then
  lease_taken=1
else
  die "could not take the PC lease (the CEO holds the PC, or the lease tool failed): nothing was changed" 3
fi

# ---- 5. prep -------------------------------------------------------------------------------
status=0
console_run prep || status=$?
if (( status )); then
  echo "Restart refused: prep exited $status; review the safety-gate output above. No reboot."
  # Bring back only what prep closed: it wrote the marker only after it passed the tab check.
  if ssh_out "if exist $REPO_WIN\\state\\restart\\pending-winbox.json echo marker" | grep -qx marker; then
    echo "-- rollback: resume"
    console_run resume || warn "rollback resume exited $?; check $REPO_WIN\\state\\restart on winbox"
  fi
  give_back
  exit "$status"
fi

# ---- 6. reboot ---------------------------------------------------------------------------------
give_back
ok "prep exited 0: every winbox session is saved. Rebooting in 60 s."
ssh -o BatchMode=yes -n "$HOST" 'shutdown /r /t 60 /c "SafeRestart: sessions saved"' || die "shutdown /r failed: the sessions are saved but winbox did not reboot; run  ssh $HOST shutdown /r /t 60  or resume them with the logon script" 1
echo "winbox restarts at $(date -u +%H:%M:%S)Z + 60 s. At logon $LOGON_TASK reopens the sessions; its log:"
echo "  ssh $HOST dir $REPO_WIN\\state\\restart\\resume-logon-*.log"
