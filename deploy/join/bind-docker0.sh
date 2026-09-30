#!/bin/sh
# Org Mesh W4.5: run a command with JOIN_API_BIND set to docker0's IPv4 address.
#
#     bind-docker0.sh <command> [args...]
#
# org-join.service puts this at the very front of ExecStart, before the Infisical fetch, so a
# box with no docker0 fails here and does not call Infisical every RestartSec. The exported
# variable travels through `infisical_setup.py run` and `setpriv` (both keep the environment)
# to `python -m tools.join_api`. The address is read when the service starts
# (`ip -4 -o addr show dev docker0`), so the unit carries no address that can go stale if
# docker is reinstalled with another bridge network.
# `host-gateway` in the proxy container resolves to this same address, which is how traefik's
# socat reaches the endpoint. tools.join_api itself refuses anything outside 127.0.0.0/8 and
# 172.16.0.0/12, so a strange docker0 address stops the service (exit 2) and never widens it.
#
# Fail closed: no docker0 or no IPv4 address on it is exit 1. systemd retries every 10 s
# (Restart=on-failure) until docker is up. Nothing falls back to 0.0.0.0 or to loopback.
set -eu

addr=$(ip -4 -o addr show dev docker0 2>/dev/null | awk '{ split($4, a, "/"); print a[1]; exit }')
if [ -z "$addr" ]; then
    echo "bind-docker0: docker0 has no IPv4 address (is docker running?)" >&2
    exit 1
fi

JOIN_API_BIND=$addr
export JOIN_API_BIND
exec "$@"
