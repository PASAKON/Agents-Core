# WINDOWS CTO launcher -- thin wrapper (Org Mesh W3.2, task-3d392ab3).
#
# The real launcher logic (model/effort resolution, hub-mode org MCP gate,
# lock file, tab title, remote control, etc.) now lives in cxo-claude.ps1,
# generalized to any C-level role (cto/cmo/cgo/cfo). This file stays so
# existing shortcuts and scheduled tasks that point at win-cto.ps1 keep
# working unchanged.
#
# Usage:  powershell -ExecutionPolicy Bypass -File windows\win-cto.ps1
# (Any extra args, e.g. -Session/-InitialPrompt/-TabTitle, pass straight
# through to cxo-claude.ps1.)

param(
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$PassThroughArgs = @()
)

& (Join-Path $PSScriptRoot 'cxo-claude.ps1') -Role cto @PassThroughArgs
exit $LASTEXITCODE
