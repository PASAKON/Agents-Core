# WINDOWS CTO launcher — Phase 1 (standalone: no org MCP, no tmux).
# Runs Claude Code with the Windows-outpost CTO role + Remote Control on,
# named "WINDOWS CTO #<id>" so the mobile app list says which box this is.
#
# Lives in the Agents repo under windows\; deployed to winbox at
#   C:\Users\UsEr\mooniex\win-cto.ps1   (+ roles\cto-windows.md beside it)
# via scp from the Mac — re-deploy after edits, there is no git clone on
# the box in Phase 1.
#
# Usage:  powershell -ExecutionPolicy Bypass -File win-cto.ps1
# The Desktop shortcut "WINDOWS CTO" wraps exactly that inside Windows
# Terminal with a blue tab.

$ErrorActionPreference = 'Stop'

# 8-hex session id, same shape as the Mac/Contabo launchers.
$sid = -join ((1..8) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })

# Role prompt sits next to this script on the box (repo layout differs).
$roleFile = Join-Path $PSScriptRoot 'cto-windows.md'
if (-not (Test-Path $roleFile)) {
    $roleFile = Join-Path $PSScriptRoot '..\roles\cto-windows.md'   # repo layout
}
$role = Get-Content -Raw $roleFile

$claude = "$env:USERPROFILE\.local\bin\claude.exe"
if (-not (Test-Path $claude)) { $claude = 'claude' }   # PATH fallback

& $claude `
    -n "WINDOWS CTO #$sid" `
    --remote-control `
    --permission-mode auto `
    --append-system-prompt $role
exit $LASTEXITCODE
