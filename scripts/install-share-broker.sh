#!/usr/bin/env bash
# Install / uninstall the Drive SHARE broker (runners/drive_share_broker.py) as a systemd service on
# Contabo -- task-1c07d46b (contract of record: org wiki `mooniex:projects/sompong-ea.md` section D,
# ADR 0032), re-done without a credential file in task-e71026a4. The broker is the ONLY thing on the
# box that reads the Drive OAuth credential this feature uses; SomPong's inbox talks to it over a
# unix socket and can only ask it to share a file into ONE CEO-approved fixed folder, `SomPong Share/`.
#
#   scripts/install-share-broker.sh install [--dry-run]
#   scripts/install-share-broker.sh uninstall [--dry-run]
#   scripts/install-share-broker.sh status
#
# NO SECRET FILE (CEO rule: every secret lives in Infisical, never create or extend a .env). `install`
# takes no credential argument and writes none. The unit (deploy/share-broker/mooniex-share-broker.service)
# has root run `tools/infisical_setup.py run MoonieX-SomPong prod --as contabo --path /drive-share`, which
# puts the three GOOGLE_OAUTH_* values in the environment of a setpriv'd process running as `shareup`.
# This script never reads, copies or prints a secret.
#
# `install` does, in order: create the system user/group `shareup` if missing (no home, no shell);
# create the staging dir /var/lib/sompong-share/staging (root:shareup 2770) and the log dir; render the
# unit for THIS checkout (@ROOT@) and install it; daemon-reload; enable; restart; print `status`.
# Installing twice re-renders the unit and restarts, never duplicates. It refuses a checkout that root
# cannot trust (root runs tools/infisical_setup.py from it; the broker code runs with the Drive
# credential): every ancestor directory and the runtime sources must be root-owned and not
# group/world-writable. `--dry-run` prints each step and the rendered unit and changes nothing (the
# trust check is skipped, so a worktree can be reviewed).
#
# ONE-TIME SECRET STEP -- not done by this script; the PH runs it on a CEO card, before or after
# `install` (with the folder empty the unit exits 2 and is NOT retried; restart it after the import):
#   python3 tools/infisical_setup.py mkdir MoonieX-SomPong prod drive-share --as <writer>
#   python3 tools/infisical_setup.py import-env MoonieX-SomPong prod <existing-source-env-file> \
#       --as <writer> --path /drive-share \
#       --only GOOGLE_OAUTH_CLIENT_ID,GOOGLE_OAUTH_CLIENT_SECRET,GOOGLE_OAUTH_REFRESH_TOKEN \
#       --comment "<purpose>" --meta provider_name=<..> --meta console_url=<..> \
#       --meta scope=<..> --meta expires=<YYYY-MM-DD> --meta owner=<..>
#   python3 tools/infisical_setup.py last4 MoonieX-SomPong prod GOOGLE_OAUTH_REFRESH_TOKEN --path /drive-share --as <writer>
#   systemctl restart mooniex-share-broker
# <writer> is an Infisical identity with write on MoonieX-SomPong (`contabo` is read-only everywhere,
# docs/design/gmail-broker.md). import-env prints names and last4 only, never a value; --only keeps any
# other line of the source file out of Infisical. SomPong's inbox must stage files as root (uid 0, the
# only allowed caller) readable by group shareup: mode 0640 inside /var/lib/sompong-share/staging.
#
# Modelled on scripts/install-gmail-broker.sh (no secret files, root fetches, setpriv drops) and the
# deploy/coo-gate unit (the "+" ExecStartPre install -d pattern); NOT on the retired version of this
# file, which copied the OAuth lines into an env file and added `sompong` to the broker's group.
set -euo pipefail

SERVICE="mooniex-share-broker"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/deploy/share-broker/${SERVICE}.service"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
BROKER_USER="shareup"
BROKER_GROUP="shareup"
STAGING_PARENT="/var/lib/sompong-share"
STAGING_DIR="${STAGING_PARENT}/staging"          # contract-fixed path, org wiki section D
LOG_DIR="/var/log/mooniex-share-broker"
SOCKET_PATH="/run/mooniex-share-broker/broker.sock"   # contract-fixed path; the unit's ExecStartPre creates the dir every start
SECRET_HOME="MoonieX-SomPong/prod/drive-share"   # where the credential lives; only used in messages

usage() { echo "usage: $0 {install|uninstall} [--dry-run] | status" >&2; exit 2; }

ACTION="${1:-}"
[[ $# -gt 0 ]] && shift
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "ERROR: unexpected argument (install takes no credential file; the secret is in Infisical)" >&2; usage ;;
  esac
done
[[ "$ACTION" =~ ^(install|uninstall|status)$ ]] || usage

run() {
  printf '+'; printf ' %q' "$@"; printf '\n'
  if ! "$DRY_RUN"; then "$@"; fi
}

if [[ "$ACTION" != status ]] && ! "$DRY_RUN" && [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: $ACTION needs root (creates a user, writes $UNIT_PATH, runs systemctl) -- rerun with sudo, or use --dry-run" >&2
  exit 1
fi

# The path goes into the unit through sed: keep it to characters that cannot break the substitution.
render_unit() { sed -e "s|@ROOT@|${ROOT}|g" "$TEMPLATE"; }

trusted_checkout() {
  local check="$ROOT"
  while [[ "$check" != / ]]; do
    [[ "$(stat -c %u "$check")" == 0 ]] && [[ -z "$(find "$check" -maxdepth 0 -perm /022 -print)" ]] \
      || { echo "ERROR: checkout ancestor $check must be root-owned and not group/world writable" >&2; return 1; }
    check="$(dirname "$check")"
  done
  local dirs=("$ROOT/tools" "$ROOT/runners" "$ROOT/lib" "$ROOT/scripts/gdrive-bridge" "$ROOT/deploy/share-broker")
  [[ -z "$(find "${dirs[@]}" -not -user root -print -quit)" ]] \
    || { echo "ERROR: runtime sources (tools, runners, lib, scripts/gdrive-bridge, deploy/share-broker) must be root-owned" >&2; return 1; }
  [[ -z "$(find "${dirs[@]}" -not -type l -perm /022 -print -quit)" ]] \
    || { echo "ERROR: runtime sources must not be group/world writable" >&2; return 1; }
}

do_install() {
  [[ "$ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo "ERROR: unsupported checkout path (letters, digits, _ . / - only): $ROOT" >&2; exit 2; }
  [[ -f "$TEMPLATE" ]] || { echo "ERROR: unit template missing: $TEMPLATE" >&2; exit 1; }
  [[ -f "$ROOT/runners/drive_share_broker.py" && -f "$ROOT/tools/infisical_setup.py" ]] \
    || { echo "ERROR: runners/drive_share_broker.py or tools/infisical_setup.py missing under $ROOT" >&2; exit 1; }
  if "$DRY_RUN"; then
    echo "(dry-run: checkout trust check skipped)"
  else
    trusted_checkout || exit 1
  fi

  echo "== 1. ${BROKER_USER} system user/group (runs the broker; holds no file credential) =="
  if getent group "$BROKER_GROUP" >/dev/null; then
    echo "  group '$BROKER_GROUP' already exists"
  else
    run groupadd --system "$BROKER_GROUP"
  fi
  if id -u "$BROKER_USER" >/dev/null 2>&1; then
    echo "  user '$BROKER_USER' already exists"
  else
    run useradd --system --gid "$BROKER_GROUP" --home-dir /nonexistent --no-create-home \
        --shell /usr/sbin/nologin "$BROKER_USER"
  fi

  echo "== 2. staging dir (root stages, ${BROKER_USER} reads and removes) =="
  [[ -d "$STAGING_PARENT" ]] || run install -d -m 0755 -o root -g root "$STAGING_PARENT"
  run install -d -m 0770 -o root -g "$BROKER_GROUP" "$STAGING_DIR"
  run chmod 2770 "$STAGING_DIR"   # setgid: files staged here stay group ${BROKER_GROUP}

  echo "== 3. log dir =="
  run install -d -m 0750 -o "$BROKER_USER" -g "$BROKER_GROUP" "$LOG_DIR"

  echo "== 4. systemd unit (rendered from deploy/share-broker/${SERVICE}.service) =="
  if "$DRY_RUN"; then
    printf '+ write unit %s (0644 root:root); rendered:\n' "$UNIT_PATH"
    render_unit
  else
    render_unit > "${UNIT_PATH}.new"
    chmod 0644 "${UNIT_PATH}.new"
    chown root:root "${UNIT_PATH}.new"
    mv "${UNIT_PATH}.new" "$UNIT_PATH"
    echo "  wrote $UNIT_PATH"
  fi

  echo "== 5. start =="
  run systemctl daemon-reload
  run systemctl enable "$SERVICE"
  run systemctl reset-failed "$SERVICE" || true   # a unit that hit its start limit refuses a restart until cleared
  run systemctl restart "$SERVICE"

  echo
  echo "credential: ${SECRET_HOME} (Infisical, fetched at start; no file on disk)."
  echo "If that folder is still empty the unit exits 2 and stays down: do the one-time secret step"
  echo "(header of this script), then 'systemctl restart ${SERVICE}'."
  if ! "$DRY_RUN"; then
    sleep 3
    do_status
  fi
}

do_uninstall() {
  run systemctl disable --now "$SERVICE" || true
  run rm -f "$UNIT_PATH"
  run systemctl daemon-reload
  echo "uninstalled: $SERVICE"
  echo "(left in place: user/group ${BROKER_USER}, ${STAGING_DIR}, ${LOG_DIR}, and the Infisical folder ${SECRET_HOME} --"
  echo " the staging dir may hold an in-flight staged file, never delete it without checking first)"
}

do_status() {
  if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then echo "active:  yes"; else echo "active:  no"; fi
  if systemctl is-enabled --quiet "$SERVICE" 2>/dev/null; then echo "enabled: yes"; else echo "enabled: no"; fi
  if [ -f "$UNIT_PATH" ]; then echo "unit:    $UNIT_PATH"; else echo "unit:    (missing)"; fi
  if [ -S "$SOCKET_PATH" ]; then echo "socket:  $SOCKET_PATH ($(stat -c '%U:%G %a' "$SOCKET_PATH" 2>/dev/null || stat -f '%Su:%Sg %Lp' "$SOCKET_PATH"))"; else echo "socket:  (not present)"; fi
  echo "credential: ${SECRET_HOME} in Infisical (no file)"
  echo "recent log lines:"
  journalctl -u "$SERVICE" -n 10 --no-pager 2>/dev/null || echo "  (journalctl unavailable)"
}

case "$ACTION" in
  install)   do_install ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
esac
