#!/usr/bin/env bash
# Deploy one commit of the SomPong repo as the root-owned release that sompong-inbox.service runs.
#
#   bash scripts/sompong-inbox-deploy.sh [<rev>]      (default rev: main)
#
# Why (CEO 2026-10-02): SomPong edits its own repo freely, but anything that runs as root needs the
# CEO's Face ID. The inbox runs as root (it alone holds the wake/internal keys), so it must never run
# the repo `sompong` owns. This script is the one door: it runs as root only through a red Run Inbox
# card, so every release the inbox runs was approved on the CEO's phone.
#
# What it does, in order:
#   1. Resolve <rev> and export it with `git archive`, run AS `sompong` (root never runs git inside a
#      repo that sompong controls: its .git/config can make git execute programs).
#   2. Extract the tar as root with Python's tarfile `data` filter, regular files and directories
#      only (symlinks and anything else are skipped), into /opt/sompong-inbox/releases/<sha>,
#      root:root, 0755 dirs / 0644 files.
#   3. Install deploy/systemd/sompong-inbox.service from this (root-owned) repo if it changed.
#   4. Point /opt/sompong-inbox/current at the release (atomic rename) and restart the inbox.
#   5. Health check (active for 3 s + socket present). On failure: point back at the previous release,
#      restart, exit 1.
#   6. Keep the newest 5 releases.
#
# Test seams (tests/test_sompong_inbox_deploy.py): SOMPONG_REPO, SOMPONG_USER, SOMPONG_INBOX_ROOT,
# SOMPONG_STATE_DIR, SOMPONG_UNIT_DEST, SYSTEMCTL, SOMPONG_DEPLOY_RUNAS (set it empty to run git as the
# current user), SOMPONG_DEPLOY_HEALTH_WAIT, SOMPONG_DEPLOY_ALLOW_NONROOT.
set -euo pipefail

CORE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${SOMPONG_REPO:-/opt/MoonieXHQ/Projects/MoonieX/SomPong}"
RUN_USER="${SOMPONG_USER:-sompong}"
INBOX_ROOT="${SOMPONG_INBOX_ROOT:-/opt/sompong-inbox}"
STATE_DIR="${SOMPONG_STATE_DIR:-/var/lib/sompong-inbox}"
UNIT_SRC="$CORE/deploy/systemd/sompong-inbox.service"
UNIT_DEST="${SOMPONG_UNIT_DEST:-/etc/systemd/system/sompong-inbox.service}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
UNIT=sompong-inbox.service
HEALTH_WAIT="${SOMPONG_DEPLOY_HEALTH_WAIT:-20}"
KEEP=5
REV="${1:-main}"

die() { echo "sompong-inbox-deploy: $*" >&2; exit 1; }

if [ "$(id -u)" != "0" ] && [ "${SOMPONG_DEPLOY_ALLOW_NONROOT:-0}" != "1" ]; then
  die "run as root (through a red Run Inbox card)"
fi
case "$REV" in
  ""|-*|*[!A-Za-z0-9._/-]*) die "bad rev: '$REV'" ;;
esac
[ "${#REV}" -le 100 ] || die "bad rev: too long"

# runuser with a clean environment, so nothing from root's environment reaches git.
if [ "${SOMPONG_DEPLOY_RUNAS+set}" = set ]; then
  read -r -a RUNAS <<<"$SOMPONG_DEPLOY_RUNAS"     # tests: empty = run git as the current user
else
  RUNAS=(runuser -u "$RUN_USER" -- env -i "HOME=$(getent passwd "$RUN_USER" | cut -d: -f6)" PATH=/usr/bin:/bin)
fi
as_user() { (cd / && "${RUNAS[@]}" "$@"); }

# 1. resolve + export as the repo owner
SHA="$(as_user git -C "$REPO" rev-parse --verify --quiet "$REV^{commit}" || true)"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || die "rev '$REV' is not a commit in $REPO"

mkdir -p "$INBOX_ROOT/releases"
chmod 755 "$INBOX_ROOT" "$INBOX_ROOT/releases"
REL="$INBOX_ROOT/releases/$SHA"
TMP="$(mktemp -d "$INBOX_ROOT/.incoming.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
as_user git -C "$REPO" archive --format=tar "$SHA" >"$TMP/release.tar"

# 2. extract as root: data filter, regular files + dirs only, then normalise ownership and modes
python3 - "$TMP/release.tar" "$TMP/tree" <<'PY'
import os, sys, tarfile
src, dest = sys.argv[1], sys.argv[2]
os.makedirs(dest, mode=0o755)
skipped = []
with tarfile.open(src) as tf:
    keep = []
    for m in tf.getmembers():
        if m.isfile() or m.isdir():
            keep.append(m)
        else:
            skipped.append(m.name)
    tf.extractall(dest, members=keep, filter="data")
for root, dirs, files in os.walk(dest):
    os.chmod(root, 0o755)
    for f in files:
        os.chmod(os.path.join(root, f), 0o644)
if skipped:
    print("skipped (not a regular file or directory): " + ", ".join(sorted(skipped)), file=sys.stderr)
PY
[ -d "$TMP/tree/inbox" ] || die "commit $SHA has no inbox/ package"
printf 'sha=%s\ndeployed_at=%s\n' "$SHA" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$TMP/tree/.release"
chmod 644 "$TMP/tree/.release"
if [ "$(id -u)" = "0" ]; then chown -R root:root "$TMP/tree"; fi
if [ -d "$REL" ]; then
  echo "release $SHA already present, reusing it"
else
  mv -T "$TMP/tree" "$REL"
fi

# 3. the unit file comes from this repo, never from the SomPong repo
if [ -f "$UNIT_SRC" ] && ! cmp -s "$UNIT_SRC" "$UNIT_DEST"; then
  install -m 644 "$UNIT_SRC" "$UNIT_DEST"
  "$SYSTEMCTL" daemon-reload
  echo "installed $UNIT_DEST from Agents-Core"
fi

# a restart must not take the shared tmux server with it (incident 2026-10-02 09:38 TH)
TMUX_PID="$(pgrep -x 'tmux: server' | head -n 1 || true)"
if [ -n "$TMUX_PID" ] && grep -q "$UNIT" "/proc/$TMUX_PID/cgroup" 2>/dev/null; then
  die "the tmux server lives in $UNIT's cgroup; a restart would kill every tmux session. Move it first."
fi

# 4. switch + restart
PREV="$(readlink "$INBOX_ROOT/current" 2>/dev/null || true)"
ln -sfn "$REL" "$INBOX_ROOT/current.new"
mv -Tf "$INBOX_ROOT/current.new" "$INBOX_ROOT/current"
"$SYSTEMCTL" restart "$UNIT"

# 5. health
healthy() {
  local ok=0 i
  for ((i = 0; i < HEALTH_WAIT; i++)); do
    if "$SYSTEMCTL" is-active --quiet "$UNIT" && [ -S "$STATE_DIR/inbox.sock" ]; then
      ok=$((ok + 1)); [ "$ok" -ge 3 ] && return 0
    else
      ok=0
    fi
    sleep 1
  done
  return 1
}
if ! healthy; then
  if [ -n "$PREV" ] && [ "$PREV" != "$REL" ] && [ -d "$PREV" ]; then
    ln -sfn "$PREV" "$INBOX_ROOT/current.new"
    mv -Tf "$INBOX_ROOT/current.new" "$INBOX_ROOT/current"
    "$SYSTEMCTL" restart "$UNIT" || true
    die "release $SHA did not come up; rolled back to $(basename "$PREV")"
  fi
  die "release $SHA did not come up and there is no previous release to roll back to"
fi

# 6. prune, never the live one
mapfile -t OLD < <(ls -1dt "$INBOX_ROOT"/releases/*/ 2>/dev/null | sed 's:/$::' | tail -n +$((KEEP + 1)))
for d in "${OLD[@]}"; do
  [ "$d" = "$REL" ] || rm -rf -- "$d"
done

echo "sompong-inbox: running release $SHA (from $REV)"
