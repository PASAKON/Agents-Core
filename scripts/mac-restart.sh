#!/usr/bin/env bash
# mac-restart.sh --sha <40-hex> [--host-alias <ssh target>] [--repo <path on the Mac>] [--dry-run]
#
# Safe restart of the Mac, driven from Contabo by a Run card (docs/ops/safe-restart-mac.md):
#   1. the Mac checkout's HEAD must equal --sha (the Mac has the code this card was written for)
#   2. prep on the Mac: save and close its sessions, write state/restart/pending-mac.json
#   3. only if prep exited 0: `sudo -n shutdown -r +1` on the Mac
# The LaunchAgent com.mooniex.org-resume brings the sessions back at login.
#
#   --dry-run     steps 1 and 2 with `prep --dry-run`; nothing is closed, written or shut down
#   --host-alias  ssh target, default macbook-pro--gob (the tailnet name). A bare name gets
#                 gob@ in front: the Mac sshd refuses root (PermitRootLogin no, AllowUsers gob@...).
#                 Pass user@host to use another account.
#   --repo        the Mac checkout, default /Users/gob/Projects/Agents
#
# Exit  0 done (or dry run ok) · 2 usage · 4 Mac HEAD differs from --sha · 5 cannot read the Mac's
#       HEAD (ssh failed) · 6 prep ok but `sudo -n shutdown` was refused (the sessions are saved and
#       closed; the instructions are printed) · anything else: prep's own exit code (3 = a session
#       is mid-turn, nothing closed; 255 = ssh itself failed).
set -euo pipefail
# A systemd-run unit starts with no HOME (scripts/org-restart.sh learned this on 17 Oct 2026).
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"

sha=""
alias_="macbook-pro--gob"
repo="/Users/gob/Projects/Agents"
dry=0

usage() { echo "usage: mac-restart.sh --sha <40-hex> [--host-alias <ssh target>] [--repo <path on the Mac>] [--dry-run]" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --sha|--host-alias|--repo)
      [ $# -ge 2 ] || usage
      case "$1" in
        --sha) sha=$2 ;;
        --host-alias) alias_=$2 ;;
        --repo) repo=$2 ;;
      esac
      shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) echo "unknown option: $1" >&2; usage ;;
  esac
done

# Every value below ends up in a command the Mac's shell parses, or in ssh's argv: allow-list them.
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "--sha must be the full 40-hex commit id (git rev-parse HEAD)" >&2; usage; }
[[ "$alias_" =~ ^[A-Za-z0-9][A-Za-z0-9._@-]*$ ]] || { echo "--host-alias: letters, digits, . _ - @ only" >&2; usage; }
[[ "$repo" =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "--repo must be an absolute path of letters, digits, . _ - /" >&2; usage; }

case "$alias_" in *@*) target=$alias_ ;; *) target="gob@$alias_" ;; esac
account=${target%%@*}

# -n: ssh never reads our stdin. BatchMode: a password prompt would hang a card.
# ServerAlive: a dead link ends the call instead of leaving prep waiting for a reader.
mac_ssh() {
  ssh -n -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=10 \
    "$target" "$@"
}
# A non-interactive ssh on macOS has PATH=/usr/bin:/bin:/usr/sbin:/sbin: no Homebrew tools.
in_repo="export PATH=/opt/homebrew/bin:/usr/local/bin:\$PATH && cd $repo"
resume_cmd="ssh $target '$in_repo && bash scripts/hub/org-python.sh tools/restart_run.py --host mac resume'"

# 1. The Mac must be on the commit this run was written for.
if ! mac_head=$(mac_ssh "cd $repo && git rev-parse HEAD"); then
  echo "Restart refused: could not read the Mac's HEAD over ssh ($target:$repo). Nothing was changed." >&2
  exit 5
fi
mac_head=$(printf '%s' "$mac_head" | tr -d '[:space:]')
if [ "$mac_head" != "$sha" ]; then
  echo "Restart refused: the Mac is on ${mac_head:-<nothing>}, expected $sha. Pull on the Mac, then run again. Nothing was changed." >&2
  exit 4
fi
echo "Mac HEAD matches $sha"

# 2. Prep: save and close the sessions. --wait-max 600 is the mid-turn safety gate.
prep_flags="--wait-max 600"
[ "$dry" -eq 0 ] || prep_flags="$prep_flags --dry-run"
status=0
mac_ssh "$in_repo && bash scripts/hub/org-python.sh tools/restart_run.py --host mac prep $prep_flags" || status=$?
if [ "$status" -ne 0 ]; then
  echo "Restart refused: prep exited $status on the Mac; review the output above. No shutdown was sent." >&2
  if [ "$status" -ne 3 ]; then
    echo "If prep closed some sessions before it failed, bring them back (and read the report) with:" >&2
    echo "  $resume_cmd" >&2
  fi
  exit "$status"
fi

if [ "$dry" -eq 1 ]; then
  echo "dry run: would now run 'sudo -n shutdown -r +1' on $target; nothing was closed or shut down"
  exit 0
fi

# 3. Shut down in a minute. stdin and output go to /dev/null on the Mac so that ssh does not
# wait for a backgrounded shutdown to let go of the pipe; the reason for a refusal is printed below.
if mac_ssh "sudo -n shutdown -r +1 </dev/null >/dev/null 2>&1"; then
  echo "Mac restart scheduled in 1 minute. The LaunchAgent com.mooniex.org-resume resumes the sessions at login."
  exit 0
fi

cat >&2 <<EOF
Prep succeeded but the Mac was NOT told to restart: 'sudo -n shutdown -r +1' was refused on $target
(sudo needs a password, or shutdown failed). The sessions are already saved and closed, and
state/restart/pending-mac.json is set. Do ONE of these:
  A. Restart it yourself: at the Mac, or in any ssh session on it, run
         sudo shutdown -r +1
     (or Apple menu > Restart). The LaunchAgent resumes the sessions at login.
  B. Let this card do it next time. On the Mac, once:
         echo '$account ALL=(root) NOPASSWD: /sbin/shutdown -r +1' > /tmp/mooniex-restart.sudoers && sudo visudo -cf /tmp/mooniex-restart.sudoers && sudo install -m 0440 -o root -g wheel /tmp/mooniex-restart.sudoers /etc/sudoers.d/mooniex-restart
  C. Keep the Mac up and bring the sessions back now, from Contabo:
         $resume_cmd
EOF
exit 6
