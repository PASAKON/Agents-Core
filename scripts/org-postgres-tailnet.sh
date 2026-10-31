#!/usr/bin/env bash
set -euo pipefail
# Match the provisioner's bind address; deployments may override TAILNET_IP.
TAILNET_IP="${TAILNET_IP:-100.118.171.23}"
deadline=$((SECONDS + 300))
until ip -4 -o addr show | awk -v target="$TAILNET_IP" '
  { split($4, address, "/"); if (address[1] == target) found=1 }
  END { exit !found }
'; do
  if (( SECONDS >= deadline )); then
    echo 'Postgres tailnet address unavailable after 5 minutes'
    exit 1
  fi
  sleep 5
done

listening() {
  ss -H -ltn | awk -v target="$TAILNET_IP:5432" '
    $4 == target { found=1 }
    END { exit !found }
  '
}
listening && exit 0
# Never recreate the container or alter its volume/network configuration.
docker restart org-postgres >/dev/null 2>&1 || exit 1
# Give Docker's listener a short bounded settling period after restart.
for attempt in {1..10}; do
  listening && exit 0
  sleep 1
done
echo 'Postgres listener unavailable after restart'
exit 1
