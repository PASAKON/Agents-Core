#!/usr/bin/env bash
# Install / upgrade yt-dlp on Contabo WITH browser impersonation (curl_cffi).
#
# Why (2026-10-10, CEO order via SomPong "Download Auto ยังไม่รองรับลิ้งค์"):
# TikTok answers yt-dlp's plain HTTP request with "Unexpected response from
# webpage request" unless yt-dlp can impersonate a browser, and impersonation
# needs the curl_cffi package. The old /usr/local/bin/yt-dlp was the single-
# file zipapp (2026.07.04), which runs on the system python and so had no
# curl_cffi -- every TikTok grab failed, short links (tt.site/t/..., vt.tiktok.com)
# included. Measured: the same two links download with yt-dlp 2026.08.19 +
# curl_cffi, and fail without it even on 2026.08.19.
#
#   scripts/install-yt-dlp.sh install   # create or upgrade /opt/yt-dlp, point /usr/local/bin/yt-dlp at it
#   scripts/install-yt-dlp.sh status    # version + impersonate targets
#   scripts/install-yt-dlp.sh rollback  # put the saved zipapp back
#
# Every caller that runs `yt-dlp` from PATH (lib/video_grab.py -> relay
# grab_video, scripts/video_to_drive.py, threads-grab.sh, tiktok-grab.sh) picks
# the new one up with no code change. The venv is world-readable so the
# `secretary` and `sompong` accounts can run it. Re-run `install` to upgrade:
# TikTok breaks yt-dlp every few weeks and the fix is a newer release.
# Needs root (writes /opt and /usr/local/bin).
set -euo pipefail

VENV="/opt/yt-dlp"
LINK="/usr/local/bin/yt-dlp"
SAVED="/usr/local/bin/yt-dlp.zipapp-saved"
PKG="yt-dlp[default,curl-cffi]"

status() {
  echo "yt-dlp -> $(readlink -f "$LINK" 2>/dev/null || echo missing)"
  "$LINK" --version
  local n
  n=$("$LINK" --list-impersonate-targets 2>/dev/null | grep -c curl_cffi || true)
  echo "impersonate targets (curl_cffi): $n"
  [ "$n" -gt 0 ]
}

case "${1:-}" in
  install)
    [ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
    [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q --upgrade "$PKG"
    chmod -R a+rX "$VENV"
    # Keep the zipapp once, for rollback; never overwrite an earlier save.
    if [ -f "$LINK" ] && [ ! -L "$LINK" ] && [ ! -e "$SAVED" ]; then
      mv "$LINK" "$SAVED"
    fi
    ln -sfn "$VENV/bin/yt-dlp" "$LINK"
    status
    ;;
  status)
    status
    ;;
  rollback)
    [ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
    [ -f "$SAVED" ] || { echo "no saved zipapp at $SAVED" >&2; exit 1; }
    rm -f "$LINK" && cp -p "$SAVED" "$LINK"
    "$LINK" --version
    ;;
  *)
    echo "usage: $0 install|status|rollback" >&2
    exit 2
    ;;
esac
