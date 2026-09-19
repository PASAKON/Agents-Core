#!/usr/bin/env bash
# Provision the org task-registry Postgres on Contabo (the hub) -- tailnet-only.
# Design: docs/design/tasks-db-hub.md §3.2. Idempotent: safe to re-run.
#
# The CTO session cannot run this itself: the auto-mode classifier refuses remote
# shell writes over ssh (memory: feedback_ssh_mooniex_vps). The CEO runs it from
# the Mac in any CTO tab:
#
#     ! bash scripts/hub/contabo-postgres-up.sh
#
# Ran for real 2026-09-19 -- this file is kept as the rebuild + rollback record.
#
# On Contabo (root over ssh alias mooniex-vps):
#   1. /root/.config/mooniex/org-db.env (600) -- generated password, never printed
#   2. docker pull postgres:16 - volume org-pgdata - container org-postgres bound
#      to 100.118.171.23:5432 ONLY (tailscale0; ufw stays 22/80/443, and the
#      ts-input chain accepts anything arriving on tailscale0)
#   3. databases: org (the registry) + org_test (test runs from the spokes)
# On the Mac:
#   4. copy the credential file to ~/.config/mooniex/org-db.env (600) and append
#      ORG_DB_URL / ORG_TEST_DB_URL for the runtime and the tests
#   5. prove the port answers over the tailnet
#
# Never touches /opt/mooniex-agents or any running C-level session.
# Rollback:  ssh mooniex-vps 'docker rm -f org-postgres && docker volume rm org-pgdata'
set -euo pipefail
HOST_ALIAS="${HOST_ALIAS:-mooniex-vps}"
TAILNET_IP="${TAILNET_IP:-100.118.171.23}"
LOCAL_ENV="$HOME/.config/mooniex/org-db.env"

echo "== [contabo] postgres up (alias=$HOST_ALIAS bind=$TAILNET_IP) =="
ssh -o ConnectTimeout=15 -o BatchMode=yes "$HOST_ALIAS" "TAILNET_IP=$TAILNET_IP bash -s" <<'REMOTE'
set -euo pipefail
mkdir -p /root/.config/mooniex && chmod 700 /root/.config/mooniex
F=/root/.config/mooniex/org-db.env
if [ ! -s "$F" ]; then
  umask 077
  PW=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-32)
  printf 'POSTGRES_USER=org\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=org\n' "$PW" > "$F"
  unset PW
  echo "[secret] org-db.env created (600)"
else
  echo "[secret] org-db.env already present"
fi
chmod 600 "$F"
echo "[pull] postgres:16 ..."; docker pull -q postgres:16 >/dev/null && echo "[pull] ok"
docker volume create org-pgdata >/dev/null && echo "[volume] org-pgdata"
if docker ps -a --format '{{.Names}}' | grep -qx org-postgres; then
  echo "[run] org-postgres already exists"; docker start org-postgres >/dev/null || true
else
  docker run -d --name org-postgres --restart unless-stopped \
    --env-file "$F" -e POSTGRES_INITDB_ARGS="--data-checksums" \
    -v org-pgdata:/var/lib/postgresql/data \
    -p "${TAILNET_IP}:5432:5432" \
    --memory=1g --shm-size=256m \
    postgres:16 >/dev/null && echo "[run] org-postgres started (bind ${TAILNET_IP}:5432 only)"
fi
for i in $(seq 1 40); do docker exec org-postgres pg_isready -U org -d org >/dev/null 2>&1 && break; sleep 2; done
docker exec org-postgres pg_isready -U org -d org
if ! docker exec org-postgres psql -U org -d org -tAc "SELECT 1 FROM pg_database WHERE datname='org_test'" | grep -q 1; then
  docker exec org-postgres psql -U org -d org -c "CREATE DATABASE org_test OWNER org" >/dev/null && echo "[db] org_test created"
else echo "[db] org_test present"; fi
docker exec org-postgres psql -U org -d org -tAc "select version()"
docker exec org-postgres psql -U org -d org -tAc "show password_encryption"
docker ps --format '{{.Names}} | {{.Status}} | {{.Ports}}' | grep org-postgres
ss -ltn | grep ':5432' || echo "[warn] nothing listening on 5432?"
free -m | awk 'NR==2{print "[mem] free MB:", $4, "available:", $7}'
REMOTE

echo "== [mac] credential file (contents never printed) =="
mkdir -p "$(dirname "$LOCAL_ENV")"
scp -q -o BatchMode=yes "$HOST_ALIAS:/root/.config/mooniex/org-db.env" "$LOCAL_ENV"
chmod 600 "$LOCAL_ENV"
TAILNET_IP="$TAILNET_IP" LOCAL_ENV="$LOCAL_ENV" python3 - <<'PY'
import os, urllib.parse
p = os.environ["LOCAL_ENV"]; ip = os.environ["TAILNET_IP"]
raw = [l.rstrip("\n") for l in open(p) if l.strip()]
kv = dict(l.split("=", 1) for l in raw if "=" in l and not l.startswith("ORG_"))
pw = urllib.parse.quote(kv["POSTGRES_PASSWORD"], safe="")
lines = [l for l in raw if not l.startswith("ORG_")]
lines.append(f"ORG_DB_URL=postgresql://{kv['POSTGRES_USER']}:{pw}@{ip}:5432/org")
lines.append(f"ORG_TEST_DB_URL=postgresql://{kv['POSTGRES_USER']}:{pw}@{ip}:5432/org_test")
open(p, "w").write("\n".join(lines) + "\n")
print("[mac] org-db.env keys:", ", ".join(l.split("=")[0] for l in lines),
      "| password length:", len(kv["POSTGRES_PASSWORD"]))
PY
if nc -z -w 5 "$TAILNET_IP" 5432; then echo "[mac] tailnet reach ${TAILNET_IP}:5432 OK"; else echo "[mac] FAIL: ${TAILNET_IP}:5432 unreachable"; exit 1; fi
echo "== done -- next: scripts/hub/cutover-mac.sh --apply (Mac), then scripts/hub/contabo-cutover.sh =="
