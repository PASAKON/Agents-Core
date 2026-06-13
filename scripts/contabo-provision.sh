#!/usr/bin/env bash
# contabo-provision.sh — provision the new Contabo VPS and restore the Hostinger
# backup onto it. Staged + idempotent: run a stage, verify, run the next.
#
# Migration Gate #2 (issue claudeflow#140). Source backup = local pull made by
# scripts/vps-backup.sh. Tailnet join uses the auth key generated 2026-06-14.
#
#   ROOT_PW=... ./contabo-provision.sh <IP> bootstrap-key   # one-time: password -> SSH key
#   ./contabo-provision.sh <IP> tailscale                   # join tailnet
#   ./contabo-provision.sh <IP> stack                       # docker/node/python/wine/ufw/traefik
#   ./contabo-provision.sh <IP> restore                     # push + restore backup data
#   ./contabo-provision.sh <IP> harden                      # key-only SSH (LAST, after verify)
#   ./contabo-provision.sh <IP> all                         # tailscale+stack+restore (NOT harden)
#
# Notes:
# - bootstrap-key needs the root password ONCE (env ROOT_PW, never argv/commit).
#   Every later stage uses key auth via ~/.ssh/mooniex_contabo_claudeflow.
# - harden is deliberately separate + manual — never lock ourselves out mid-run.
set -euo pipefail

IP="${1:?usage: $0 <IP> <stage>}"
STAGE="${2:?usage: $0 <IP> <stage>  (bootstrap-key|tailscale|stack|restore|harden|all)}"

KEY="$HOME/.ssh/mooniex_contabo_claudeflow"
PUB="$KEY.pub"
ALIAS="mooniex-contabo"
DEST_ROOT="$HOME/Backups/mooniex-vps"
TS_AUTHKEY="${TS_AUTHKEY:-}"   # tailscale auth key; pass via env at runtime, never commit
SSH_OPTS=(-o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)

log(){ printf '\033[36m[provision]\033[0m %s\n' "$*"; }
die(){ printf '\033[31m[FATAL]\033[0m %s\n' "$*" >&2; exit 1; }

# key-auth ssh/rsync helpers (used by every stage except bootstrap-key)
rsh(){ ssh "${SSH_OPTS[@]}" -i "$KEY" "root@$IP" "$@"; }
rcp(){ rsync -aH -e "ssh ${SSH_OPTS[*]} -i $KEY" "$@"; }

latest_run(){ ls -d "$DEST_ROOT"/2*Z 2>/dev/null | sort | tail -1; }

# ---------------------------------------------------------------------------
bootstrap_key(){
  [ -f "$PUB" ] || die "missing $PUB — generate: ssh-keygen -t ed25519 -f $KEY -C mooniex-contabo"
  : "${ROOT_PW:?bootstrap-key needs ROOT_PW env (one-time root password)}"
  log "installing $PUB into root@$IP authorized_keys (one-time password auth)"
  if command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$ROOT_PW" ssh-copy-id -o StrictHostKeyChecking=accept-new -i "$PUB" "root@$IP" \
      || die "ssh-copy-id failed — check IP/password"
  else
    log "sshpass not installed. Run this ONE line manually (paste password when asked):"
    log "    ssh-copy-id -i $PUB root@$IP"
    die "install sshpass (brew install hudochenkov/sshpass/sshpass) or run the line above, then re-run stages"
  fi
  # add/refresh ssh config alias
  if ! grep -q "^Host $ALIAS\$" "$HOME/.ssh/config" 2>/dev/null; then
    log "adding ~/.ssh/config alias '$ALIAS' -> $IP"
    cat >> "$HOME/.ssh/config" <<CFG

Host $ALIAS
    HostName $IP
    User root
    IdentityFile $KEY
CFG
  fi
  rsh 'echo "key auth OK: $(hostname)"' || die "key auth verify failed"
  log "bootstrap-key done — later stages use key auth"
}

# ---------------------------------------------------------------------------
stage_tailscale(){
  : "${TS_AUTHKEY:?tailscale stage needs TS_AUTHKEY env (the tskey-auth-... key)}"
  log "installing + joining tailscale"
  rsh 'command -v tailscale >/dev/null 2>&1 || curl -fsSL https://tailscale.com/install.sh | sh'
  rsh "tailscale up --authkey '$TS_AUTHKEY' --hostname mooniex-contabo --ssh"
  rsh 'tailscale ip -4 || true'
  log "tailscale joined — check admin.tailscale.com machines list"
}

# ---------------------------------------------------------------------------
stage_stack(){
  log "installing base stack (idempotent) — docker, node20, python3, wine, ufw, git"
  rsh 'set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y ca-certificates curl git ufw python3 python3-venv python3-pip xvfb
    # docker + compose plugin
    if ! command -v docker >/dev/null 2>&1; then
      install -m0755 -d /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
      chmod a+r /etc/apt/keyrings/docker.asc
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
      apt-get update -y
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    systemctl enable --now docker
    # node 20 + pm2
    if ! command -v node >/dev/null 2>&1; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
      apt-get install -y nodejs
    fi
    command -v pm2 >/dev/null 2>&1 || npm install -g pm2
    # wine (line-poster) — i386 + winehq
    if ! command -v wine >/dev/null 2>&1; then
      dpkg --add-architecture i386 || true
      apt-get update -y
      apt-get install -y wine64 wine32 || apt-get install -y wine || true
    fi
    node --version; docker --version; python3 --version; (wine --version 2>/dev/null || echo "wine: check")
  '
  log "stack done"
}

# ---------------------------------------------------------------------------
stage_restore(){
  local run; run="$(latest_run)"
  [ -n "$run" ] && [ -d "$run" ] || die "no local backup run dir under $DEST_ROOT"
  log "restoring from $run"
  log "1/6 push backup -> /root/restore/ on VPS"
  rsh 'mkdir -p /root/restore'
  rcp "$run/" "root@$IP:/root/restore/"

  log "2/6 .env files -> repo paths (review the map below before enabling services)"
  rsh 'set -e
    mkdir -p /root/projects
    for f in /root/restore/_env-bundle/*.env; do
      [ -f "$f" ] || continue
      echo "  staged $f ($(grep -cE "^[^#[:space:]]" "$f") vars) — place at its repo .env manually per playbook"
    done
  '
  log "3/6 n8n_data volume restore (volume must exist BEFORE n8n starts)"
  rsh 'set -e
    if [ -f /root/restore/volumes/n8n_data.tar.gz ]; then
      docker volume inspect n8n_data >/dev/null 2>&1 || docker volume create n8n_data
      docker run --rm -v n8n_data:/data -v /root/restore/volumes:/b alpine \
        sh -c "cd /data && tar xzf /b/n8n_data.tar.gz" && echo "  n8n_data restored"
      docker run --rm -v n8n_data:/data alpine sh -c "ls /data | head"
    else echo "  no n8n_data.tar.gz — skip"; fi
    if [ -f /root/restore/volumes/traefik_data.tar.gz ]; then
      docker volume inspect traefik_data >/dev/null 2>&1 || docker volume create traefik_data
      docker run --rm -v traefik_data:/data -v /root/restore/volumes:/b alpine \
        sh -c "cd /data && tar xzf /b/traefik_data.tar.gz" && echo "  traefik_data restored"
    fi
  '
  log "4/6 systemd units + crontab (staged, enable manually after env in place)"
  rsh 'set -e
    if [ -d /root/restore/system/systemd ]; then
      cp -n /root/restore/system/systemd/mooniex-* /etc/systemd/system/ 2>/dev/null || true
      systemctl daemon-reload
      echo "  systemd units copied (NOT enabled — enable per service after .env placed)"
    fi
    [ -f /root/restore/system/crontab-root.txt ] && echo "  crontab staged at /root/restore/system/crontab-root.txt (install: crontab <file>)"
  '
  log "5/6 pm2 dump staged (resurrect after apps + .env present): pm2 resurrect /root/restore/system/dump.pm2"
  log "6/6 repo dirs staged under /root/restore — git clone/pull the live repos, then drop .env + data in"
  log "restore push complete. Finish service-by-service per migration waves (claudeflow#140)."
}

# ---------------------------------------------------------------------------
stage_harden(){
  log "HARDENING: install authorized_keys from backup + disable password SSH"
  log "Pre-check: confirming key auth works before we disable passwords..."
  rsh 'echo "key auth confirmed: $(hostname)"' || die "key auth not working — do NOT harden yet"
  rsh 'set -e
    mkdir -p /root/.ssh && chmod 700 /root/.ssh
    if [ -f /root/restore/system/authorized_keys ]; then
      # merge backup keys + current (our contabo key) without dupes
      cat /root/restore/system/authorized_keys /root/.ssh/authorized_keys 2>/dev/null | sort -u > /root/.ssh/authorized_keys.new
      mv /root/.ssh/authorized_keys.new /root/.ssh/authorized_keys
      chmod 600 /root/.ssh/authorized_keys
    fi
    sed -i "s/^#\?PasswordAuthentication.*/PasswordAuthentication no/" /etc/ssh/sshd_config
    sed -i "s/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/" /etc/ssh/sshd_config
    systemctl reload ssh || systemctl reload sshd
    echo "  password SSH disabled; key-only now"
  '
  log "harden done — the chat-pasted root password is now useless (good). ufw:"
  rsh 'ufw allow OpenSSH; ufw --force enable; ufw status verbose' || true
}

case "$STAGE" in
  bootstrap-key) bootstrap_key ;;
  tailscale)     stage_tailscale ;;
  stack)         stage_stack ;;
  restore)       stage_restore ;;
  harden)        stage_harden ;;
  all)           stage_tailscale; stage_stack; stage_restore;
                 log "ran tailscale+stack+restore. Verify, then run 'harden' separately." ;;
  *) die "unknown stage '$STAGE' (bootstrap-key|tailscale|stack|restore|harden|all)" ;;
esac
