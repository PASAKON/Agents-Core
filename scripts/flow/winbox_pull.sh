#!/usr/bin/env bash
# winbox_pull.sh <winbox dir> <mac dir> — pull finished Flow clips from
# winbox to the Mac over `ssh winbox`. Verifies size + sha256 per file,
# skips a file already identical on the Mac, prints a count at the end.
#
#   bash scripts/flow/winbox_pull.sh 'C:\Users\passg\Desktop\flow-out\ACT2' \
#       ~/Desktop/banchi-ACT2
#
# <winbox dir> is a Windows path (backslashes, as flow_shoot.py's --dest
# wrote it there); <mac dir> is a POSIX path the clips land in, created if
# missing. Bash 3.2 (macOS default) compatible: no arrays, no [[ -v ]].
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
WINBOX_PYTHON="${WINBOX_PYTHON:-python}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_SRC="$HERE/winbox_pull_helper.py"
REMOTE_DIR='C:\mooniex\flow-pull'
REMOTE_HELPER="$REMOTE_DIR\\winbox_pull_helper.py"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $# -eq 2 ]] || die "usage: $0 <winbox dir> <mac dir>"
WINBOX_DIR="$1"
MAC_DIR="$2"
[[ -f "$HELPER_SRC" ]] || die "missing $HELPER_SRC"

mkdir -p "$MAC_DIR"

sha256_local() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | cut -d' ' -f1
  else
    openssl dgst -sha256 "$1" | awk '{print $NF}'
  fi
}

size_local() {
  stat -f%z "$1" 2>/dev/null || stat -c%s "$1"
}

echo ">> Deploying remote helper to $HOST:$REMOTE_HELPER ..."
ssh -n "$HOST" "if not exist \"$REMOTE_DIR\" mkdir \"$REMOTE_DIR\"" >/dev/null 2>&1 || true
scp -q "$HELPER_SRC" "$HOST:$REMOTE_HELPER" || die "could not copy winbox_pull_helper.py to $HOST"

echo ">> Listing files under $WINBOX_DIR on $HOST ..."
listing="$(ssh -o ConnectTimeout=20 "$HOST" "$WINBOX_PYTHON \"$REMOTE_HELPER\" \"$WINBOX_DIR\"" | tr -d '\r')" \
  || die "remote listing failed — is $WINBOX_DIR present on $HOST, and $WINBOX_PYTHON on PATH?"

if [[ -z "$listing" ]]; then
  echo "0 file(s) found under $WINBOX_DIR on $HOST — nothing to pull"
  exit 0
fi

total=0
pulled=0
skipped=0
failed=0

while IFS=$'\t' read -r rel size sha; do
  [[ -n "$rel" ]] || continue
  total=$((total + 1))
  local_path="$MAC_DIR/$rel"
  mkdir -p "$(dirname "$local_path")"

  if [[ -f "$local_path" ]] \
      && [[ "$(size_local "$local_path")" == "$size" ]] \
      && [[ "$(sha256_local "$local_path")" == "$sha" ]]; then
    skipped=$((skipped + 1))
    continue
  fi

  # scp on this Mac transfers over SFTP, which wants "/" even for a Windows
  # remote path — a literal "\" survives ssh's own quoting but then confuses
  # the SFTP path parser (measured: scp reported "No such file or directory"
  # for a file that ssh could `type` moments earlier). Windows itself accepts
  # "/" as a separator, so normalize the whole remote spec to forward slashes.
  remote_path="${WINBOX_DIR//\\//}/$rel"
  if ! scp -q "$HOST:$remote_path" "$local_path"; then
    echo "FAILED (scp): $rel" >&2
    failed=$((failed + 1))
    continue
  fi

  got_sha="$(sha256_local "$local_path")"
  got_size="$(size_local "$local_path")"
  if [[ "$got_sha" != "$sha" ]] || [[ "$got_size" != "$size" ]]; then
    echo "FAILED (verify): $rel — want size=$size sha256=$sha, got size=$got_size sha256=$got_sha" >&2
    failed=$((failed + 1))
    continue
  fi
  pulled=$((pulled + 1))
  echo "pulled: $rel"
done <<< "$listing"

echo ">> $HOST:$WINBOX_DIR -> $MAC_DIR"
echo ">> total=$total pulled=$pulled skipped(identical)=$skipped failed=$failed"
[[ "$failed" -eq 0 ]]
