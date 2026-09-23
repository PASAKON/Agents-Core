#!/bin/bash
# Run winbox's rclone with this Mac's stdin/stdout: the Drive token never leaves winbox (gdrive-filing rule 6).
RC='C:\Users\UsEr\AppData\Local\Microsoft\WinGet\Packages\Rclone.Rclone_Microsoft.Winget.Source_8wekyb3d8bbwe\rclone-v1.75.1-windows-amd64\rclone.exe'
for a in "$@"; do case "$a" in *" "*|*'"'*|*"&"*|*"|"*|*"<"*|*">"*|*"^"*) echo "rclone-via-winbox: unsafe arg for cmd.exe: $a" >&2; exit 2;; esac; done
exec ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 winbox "$RC $*"
