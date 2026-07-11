#!/usr/bin/env bash
# console-deploy.sh — deploy the MoonieX Console (console/) to the Contabo VPS,
# Tailscale-only. Staged + idempotent: run a stage, verify, run the next.
# Mirrors scripts/contabo-provision.sh style.
#
#   ./console-deploy.sh node       # install isolated Node 22 at /opt/node-v22
#   ./console-deploy.sh sync       # rsync console/ -> /opt/mooniex-console
#   ./console-deploy.sh install    # npm ci on the box (+ node-pty guard)
#   ./console-deploy.sh cert       # issue tailscale TLS cert + renewal timer
#   ./console-deploy.sh env        # write .env on the box (secret generated once)
#   ./console-deploy.sh service    # install + enable + start systemd unit
#   ./console-deploy.sh verify     # acceptance checks (bind IP, cert, public-refuse)
#   ./console-deploy.sh all        # node->sync->install->cert->env->service (not verify)
#
# HARD CONSTRAINT (CEO-locked): the console must be unreachable from the public
# internet. We guarantee this by binding the Node server to the tailnet IP only
# (HOST=100.118.171.23), NOT 0.0.0.0. No new public ufw port is opened.
#
# Node 22 note: system node on Contabo is 20.x, too old for the app's
# `node:sqlite` (needs >= 22.5). We install an isolated Node 22 under /opt so
# the system node is left untouched.
set -euo pipefail

STAGE="${1:?usage: $0 <stage>  (node|sync|install|cert|env|service|verify|all)}"

# --- constants ---------------------------------------------------------------
SSH_HOST="mooniex-vps"                       # ~/.ssh/config alias -> Contabo
TAILNET_IP="100.118.171.23"                  # console binds here ONLY
MAGIC_DNS="mooniex-contabo.tail400676.ts.net"
PORT="8443"                                  # 443 is taken by docker-proxy
REMOTE_DIR="/opt/mooniex-console"
CERT_DIR="$REMOTE_DIR/certs"
CRT="$CERT_DIR/$MAGIC_DNS.crt"
KEY="$CERT_DIR/$MAGIC_DNS.key"
NODE_VER="v22.11.0"
NODE_DIR="/opt/node-v22"
NODE_TARBALL="node-$NODE_VER-linux-x64"
NODE_URL="https://nodejs.org/dist/$NODE_VER/$NODE_TARBALL.tar.xz"
NODE_BIN="$NODE_DIR/bin/node"
NPM_BIN="$NODE_DIR/bin/npm"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CONSOLE="$(cd "$SCRIPT_DIR/../console" && pwd)"
SSH_OPTS=(-o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)

log(){ printf '\033[36m[console-deploy]\033[0m %s\n' "$*"; }
die(){ printf '\033[31m[FATAL]\033[0m %s\n' "$*" >&2; exit 1; }
rsh(){ ssh "${SSH_OPTS[@]}" "$SSH_HOST" "$@"; }
rcp(){ rsync -aH --delete -e "ssh ${SSH_OPTS[*]}" "$@"; }

# ---------------------------------------------------------------------------
stage_node(){
  log "installing isolated Node $NODE_VER at $NODE_DIR (system node untouched)"
  rsh bash -s <<EOF
set -euo pipefail
if [ -x "$NODE_BIN" ] && "$NODE_BIN" -v | grep -q "$NODE_VER"; then
  echo "[box] Node $NODE_VER already present"; exit 0
fi
cd /tmp
curl -fsSL "$NODE_URL" -o "$NODE_TARBALL.tar.xz"
rm -rf "$NODE_DIR" "/opt/$NODE_TARBALL"
tar -xf "$NODE_TARBALL.tar.xz" -C /opt
mv "/opt/$NODE_TARBALL" "$NODE_DIR"
rm -f "$NODE_TARBALL.tar.xz"
"$NODE_BIN" -v
EOF
}

stage_sync(){
  log "rsync $LOCAL_CONSOLE/ -> $SSH_HOST:$REMOTE_DIR (excluding node_modules/.env/db/certs)"
  rsh "mkdir -p $REMOTE_DIR"
  rcp \
    --exclude 'node_modules/' \
    --exclude '.env' \
    --exclude 'data/' \
    --exclude 'certs/' \
    --exclude '*.db' \
    "$LOCAL_CONSOLE/" "$SSH_HOST:$REMOTE_DIR/"
}

stage_install(){
  log "npm ci on the box with Node 22 (+ ensure-node-pty postinstall guard)"
  rsh bash -s <<EOF
set -euo pipefail
cd "$REMOTE_DIR"
export PATH="$NODE_DIR/bin:\$PATH"
"$NPM_BIN" ci
echo "[box] node-pty binary check:"
ls -la node_modules/node-pty/build/Release/pty.node 2>&1 || \
  echo "[box] WARN: pty.node missing — live terminal attach will not work (login/cert unaffected)"
EOF
}

stage_cert(){
  log "issuing tailscale TLS cert for $MAGIC_DNS + installing weekly renewal timer"
  rsh bash -s <<EOF
set -euo pipefail
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"
tailscale cert --cert-file "$CRT" --key-file "$KEY" "$MAGIC_DNS"
ls -la "$CRT" "$KEY"

cat > /etc/systemd/system/mooniex-console-cert-renew.service <<UNIT
[Unit]
Description=Renew MoonieX Console tailscale TLS cert and restart the service
After=network-online.target tailscaled.service
Requires=tailscaled.service

[Service]
Type=oneshot
WorkingDirectory=$CERT_DIR
ExecStart=/usr/bin/tailscale cert --cert-file $CRT --key-file $KEY $MAGIC_DNS
ExecStartPost=/usr/bin/systemctl restart mooniex-console.service
UNIT

cat > /etc/systemd/system/mooniex-console-cert-renew.timer <<UNIT
[Unit]
Description=Weekly renewal check for the MoonieX Console tailscale TLS cert

[Timer]
OnCalendar=weekly
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now mooniex-console-cert-renew.timer
systemctl list-timers mooniex-console-cert-renew.timer --no-pager || true
EOF
}

stage_env(){
  log "writing $REMOTE_DIR/.env on the box (session secret generated once, never printed)"
  rsh bash -s <<EOF
set -euo pipefail
cd "$REMOTE_DIR"
if [ -f .env ]; then
  echo "[box] .env already exists — preserving existing SESSION_SECRET"
  exit 0
fi
SECRET=\$("$NODE_BIN" -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
cat > .env <<ENV
PORT=$PORT
HOST=$TAILNET_IP
TLS_CERT_FILE=$CRT
TLS_KEY_FILE=$KEY
WEBAUTHN_RP_ID=$MAGIC_DNS
WEBAUTHN_RP_NAME=MoonieX Console
WEBAUTHN_ORIGIN=https://$MAGIC_DNS:$PORT
SESSION_SECRET=\$SECRET
COOKIE_SECURE=true
DB_PATH=./data/console.db
ORG_ROOT=$REMOTE_DIR
PYTHON_BIN=python3
ENV
chmod 600 .env
echo "[box] .env written (SESSION_SECRET redacted)"
EOF
}

stage_service(){
  log "installing + enabling + starting mooniex-console.service"
  rsh bash -s <<EOF
set -euo pipefail
cat > /etc/systemd/system/mooniex-console.service <<UNIT
[Unit]
Description=MoonieX Console (mobile iTerm2 web console, tailnet-only)
After=network-online.target tailscaled.service
Wants=network-online.target
Requires=tailscaled.service

[Service]
Type=simple
WorkingDirectory=$REMOTE_DIR
ExecStart=$NODE_BIN src/server.js
Restart=on-failure
RestartSec=3
ExecStartPre=/bin/sh -c 'until /usr/bin/tailscale ip -4 >/dev/null 2>&1; do sleep 1; done'
User=root
Group=root

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now mooniex-console.service
sleep 2
systemctl --no-pager status mooniex-console.service | head -12
EOF
}

stage_verify(){
  log "acceptance checks"
  echo "--- 1. service active/enabled ---"
  rsh "systemctl is-active mooniex-console; systemctl is-enabled mooniex-console"
  echo "--- 2. listener bound to $TAILNET_IP:$PORT (NOT 0.0.0.0 / public IP) ---"
  rsh "ss -tlnp | grep ':$PORT ' || echo 'NOTHING LISTENING ON $PORT'"
  echo "--- 3. HTTPS reachable over tailnet with valid (non -k) cert ---"
  curl -sS -o /dev/null -w 'HTTP %{http_code}\n' "https://$MAGIC_DNS:$PORT/login" \
    || die "tailnet HTTPS check failed"
  echo "--- 4. public interface refuses (should time out / refuse) ---"
  if curl -m5 -sS -o /dev/null "http://194.233.80.26:$PORT/" 2>/dev/null; then
    die "REACHABLE ON PUBLIC IP — hard constraint violated!"
  else
    echo "public IP:$PORT not reachable (expected)"
  fi
  echo
  log "bookmark for iPhone:  https://$MAGIC_DNS:$PORT/"
}

case "$STAGE" in
  node)     stage_node ;;
  sync)     stage_sync ;;
  install)  stage_install ;;
  cert)     stage_cert ;;
  env)      stage_env ;;
  service)  stage_service ;;
  verify)   stage_verify ;;
  all)      stage_node; stage_sync; stage_install; stage_cert; stage_env; stage_service ;;
  *)        die "unknown stage '$STAGE' (node|sync|install|cert|env|service|verify|all)" ;;
esac

log "stage '$STAGE' done."
