#!/bin/sh
# Install org-tmux-adopt (scripts/org-tmux-adopt.sh) on a Linux box whose org sessions share
# root's tmux server: Contabo, since 2026-10-02.
#
# Copies the script to /usr/local/sbin/org-tmux-adopt and adds one run-shell line to
# /etc/tmux.conf, so every NEW tmux server moves itself into org-tmux.scope before its first
# pane starts. A running server is not touched; the script's header says how to move one.
# Safe to run again: the line is added once.
#
# Run as root:  sh scripts/install-org-tmux-adopt.sh
# Test overrides: ORG_TMUX_SBIN (install path), ORG_TMUX_CONF (tmux config file).
set -eu

sbin=${ORG_TMUX_SBIN:-/usr/local/sbin/org-tmux-adopt}
conf=${ORG_TMUX_CONF:-/etc/tmux.conf}
here=$(cd "$(dirname "$0")" && pwd)
line="run-shell '$sbin #{pid} #{socket_path} >/dev/null 2>&1 || true'"

install -m 0755 "$here/org-tmux-adopt.sh" "$sbin"
touch "$conf"
if ! grep -qxF "$line" "$conf"; then
  printf '%s\n%s\n' \
    "# org: keep the shared tmux server in its own cgroup (Agents-Core scripts/org-tmux-adopt.sh)" \
    "$line" >> "$conf"
fi
echo "installed $sbin; $conf runs it when a tmux server starts"
