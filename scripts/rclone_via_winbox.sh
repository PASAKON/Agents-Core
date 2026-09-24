#!/bin/bash
# Run winbox's rclone with this machine's stdin/stdout: the Drive token never leaves winbox (gdrive-filing rule 6).
# Works from the Mac and from Contabo (both carry `Host winbox` in ~/.ssh/config). Since the 2026-09-24 reinstall
# the account is passg and rclone resolves through PATH via the WinGet Links shim
# (C:\Users\passg\AppData\Local\Microsoft\WinGet\Links\rclone.exe); the old UsEr package path no longer exists.
# Override with RCLONE_WINBOX_EXE if the shim ever moves. stdin is forwarded, so `tar ... | rclone_via_winbox.sh rcat ...` streams.
RC="${RCLONE_WINBOX_EXE:-rclone}"
for a in "$@"; do case "$a" in *" "*|*'"'*|*"&"*|*"|"*|*"<"*|*">"*|*"^"*) echo "rclone-via-winbox: unsafe arg for cmd.exe: $a" >&2; exit 2;; esac; done
exec ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 winbox "$RC $*"
