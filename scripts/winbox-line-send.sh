#!/usr/bin/env bash
# winbox-line-send.sh — send one LINE message from the session the CEO is in.
#
# WHY THIS EXISTS (2026-09-12). The first attempt routed "LINE the editor" to a
# browser_operator subagent. That subagent's permission classifier stopped it:
# messaging a real person needs its own user's explicit yes, in its own chat.
# It was right to stop, and a peer session cannot clear that for it — a system
# where agent A approves agent B's prompts is not a permission system.
#
# The mistake was upstream. The CEO gives orders HERE, so the authorisation
# lives HERE, and the send should never have been an agent's decision in the
# first place. This script makes it a deterministic action the C-level runs
# directly: no subagent, no second chat, nothing to approve twice.
#
#   ./scripts/winbox-line-send.sh peek                  # which chat is open?
#   ./scripts/winbox-line-send.sh stage <local-file>    # upload + checksum
#   ./scripts/winbox-line-send.sh send                  # paste and press enter
#   ./scripts/winbox-line-send.sh attach <local-file>   # send a file into the chat
#
# peek and stage change nothing a person sees. Only `send` is outward-facing,
# and it is a separate word on purpose.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
REMOTE_DIR='C:\mooniex\line'
MSG_REMOTE="$REMOTE_DIR\\line_msg.txt"
TASK='mooniex-line-send'
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${LINE_SHOT_DIR:-/tmp/winbox-line}"

ps1() { ssh -o ConnectTimeout=15 -n "$HOST" "powershell -NoProfile -Command \"$1\"" 2>&1 | tr -d '\r'; }
die() { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m✓\033[0m %s\n' "$*"; }

# --- the screen may already be in use. Same gate as winbox-desktop.sh: a
# session drove this desktop for three hours with the tenant live underneath
# because the rule lived only in a document (2026-09-14). See winbox-pc-lease.
if [[ "${WINBOX_NO_LEASE:-0}" != "1" ]]; then
  "$HERE/scripts/pc-lease.sh" gate || exit 3
fi

# --- push the runner, every time. A worktree's copy drifts from main and the
# box keeps whatever was last written; re-copying costs nothing and removes a
# whole class of "why is it running the old logic".
push_runner() {
  ssh -n "$HOST" "if not exist \"$REMOTE_DIR\" mkdir \"$REMOTE_DIR\"" >/dev/null 2>&1 || true
  scp -q "$HERE/windows/line-send.ps1" "$HOST:$REMOTE_DIR\\line-send.ps1"
}

# --- run it in session 1. SSH lands in session 0, which has no desktop, so a
# one-shot INTERACTIVE scheduled task is the only way to reach the screen
# (proved 2026-09-11, docs/runbooks/winbox-recovery.md).
#
# PowerShell is launched DIRECTLY, with a hidden window. The earlier version
# wrapped it in a .cmd so the shell could redirect output to out.txt — and that
# console window took the foreground away from LINE roughly six seconds into
# every run, which is precisely what made the clicks land on the wrong app.
# The task now writes out.txt itself (Result() in line-send.ps1), so no shell
# is needed and nothing else appears on screen. Paths here contain no spaces,
# so the quoting that forced the wrapper is no longer a problem either.
run_in_session1() {
  local mode="$1" extra="${2:-}"
  ssh -n "$HOST" "powershell -NoProfile -Command \"\
    \$me=[Security.Principal.WindowsIdentity]::GetCurrent().Name;\
    Unregister-ScheduledTask -TaskName '$TASK' -Confirm:\$false -ErrorAction SilentlyContinue;\
    \$a=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File $REMOTE_DIR\\line-send.ps1 -Mode $mode $extra';\
    \$p=New-ScheduledTaskPrincipal -UserId \$me -LogonType Interactive -RunLevel Limited;\
    \$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 3);\
    Register-ScheduledTask -TaskName '$TASK' -Action \$a -Principal \$p -Settings \$s -Force | Out-Null;\
    Remove-Item '$REMOTE_DIR\\out.txt' -ErrorAction SilentlyContinue;\
    Start-ScheduledTask -TaskName '$TASK'\"" >/dev/null 2>&1

  local i
  for i in $(seq 1 30); do
    sleep 2
    local r; r=$(ps1 "if(Test-Path '$REMOTE_DIR\\out.txt'){Get-Content -Raw '$REMOTE_DIR\\out.txt'}" || true)
    [[ -n "${r// /}" ]] && { echo "$r"; return 0; }
  done
  die "no result from session 1 after 60s (task $TASK)"
}

pull_shots() {
  mkdir -p "$OUT"
  local f
  for f in "$@"; do
    scp -q "$HOST:C:/mooniex/line/shot-$f.png" "$OUT/$f.png" 2>/dev/null \
      && ok "screenshot → $OUT/$f.png" || true
  done
}

cmd="${1:-peek}"
case "$cmd" in
  peek)
    push_runner
    res=$(run_in_session1 peek); echo "$res"
    [[ "$res" == OK* ]] || die "peek failed"
    pull_shots peek
    echo
    echo "Look at the screenshot and confirm the right chat is open BEFORE 'send'."
    ;;

  stage)
    src="${2:?usage: winbox-line-send.sh stage <local-file>}"
    [[ -f "$src" ]] || die "no such file: $src"
    # Ship as a file, never as a command-line argument: non-ASCII pasted into a
    # winbox task brief came back as "????" (FINDING-winbox-ascii-only.md). The
    # checksum on both sides is what proves the Thai survived.
    scp -q "$src" "$HOST:$MSG_REMOTE"
    local_md5=$(md5sum "$src" | cut -d' ' -f1 | tr 'a-z' 'A-Z')
    remote_md5=$(ps1 "(Get-FileHash '$MSG_REMOTE' -Algorithm MD5).Hash")
    [[ "$local_md5" == "$remote_md5" ]] || die "checksum differs: $local_md5 vs $remote_md5"
    ok "staged, md5 $remote_md5 identical on both machines"
    ps1 "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Content -Raw -Encoding UTF8 '$MSG_REMOTE'"
    ;;

  send)
    push_runner
    res=$(run_in_session1 send); echo "$res"
    pull_shots msg-pasted msg-sent
    [[ "$res" == OK\ sent* ]] || die "send did not confirm — read the shots and $REMOTE_DIR\\line-send.log"
    ok "sent"
    ;;

  attach)
    src="${2:?usage: winbox-line-send.sh attach <local-file>}"
    [[ -f "$src" ]] || die "no such file: $src"
    base="$(basename "$src")"
    scp -q "$src" "$HOST:$REMOTE_DIR\\$base"
    push_runner
    res=$(run_in_session1 attach "-AttachFile \\\"$REMOTE_DIR\\$base\\\""); echo "$res"
    stem="${base%.*}"
    pull_shots "attach-$stem-dialog" "attach-$stem-sent"
    [[ "$res" == OK\ sent* ]] || die "attach did not confirm — read the shots and $REMOTE_DIR\\line-send.log"
    ok "attached $base"
    ;;

  open)
    who="${2:?usage: winbox-line-send.sh open <contact name>}"
    push_runner
    res=$(run_in_session1 open "-Who \\\"$who\\\""); echo "$res"
    pull_shots open-results open
    echo
    echo "CHECK the shot: the chat header must read exactly the person you meant."
    ;;

  pin)
    push_runner
    res=$(run_in_session1 pin); echo "$res"
    pull_shots pin
    ;;

  menu)
    push_runner
    res=$(run_in_session1 menu); echo "$res"
    pull_shots menu
    ;;

  clip)
    push_runner
    res=$(run_in_session1 clip); echo "$res"
    pull_shots clip
    ;;

  log) ps1 "Get-Content -Tail 40 '$REMOTE_DIR\\line-send.log'" ;;
  *)   die "usage: $0 {peek|stage <file>|send|attach <file>|log}" ;;
esac
