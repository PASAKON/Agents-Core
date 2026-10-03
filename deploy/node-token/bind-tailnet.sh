#!/bin/sh
# Org Mesh W4.2b: run a command with NODE_TOKEN_BIND set to this machine's tailnet IPv4 address.
#
#     bind-tailnet.sh <command> [args...]
#
# org-node-token.service puts this at the very front of ExecStart, before the Infisical fetch, so a
# box that is not on the tailnet fails here and does not call Infisical every RestartSec. The
# exported variable travels through `infisical_setup.py run` and `setpriv` (both keep the
# environment) to `python -m tools.node_token_api`. The address is read when the service starts
# (`tailscale ip -4`), so the unit carries no address that can go stale. tools.node_token_api
# itself refuses anything outside 100.64.0.0/10, so a strange answer stops the service (exit 2)
# and never widens it: no 0.0.0.0, no loopback, no public address.
#
# Fail closed: tailscale missing, tailscaled down, or no IPv4 address is exit 1. systemd retries
# every 30 s (Restart=on-failure), at most 5 times in 10 minutes (StartLimitBurst=5), then the unit
# stays failed until `systemctl reset-failed org-node-token`. Nothing falls back to anything else.
set -eu

addr=$(tailscale ip -4 2>/dev/null | awk 'NF { print $1; exit }') || addr=""
if [ -z "$addr" ]; then
    echo "bind-tailnet: no tailnet IPv4 address (is tailscaled running and logged in?)" >&2
    exit 1
fi

NODE_TOKEN_BIND=$addr
export NODE_TOKEN_BIND
exec "$@"
