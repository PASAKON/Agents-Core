# WINDOWS CTO launcher -- v2 (2026-09-28): the Mac C-level launch shape
# (scripts/cxo-claude.sh) ported to PowerShell 5.1, minus tmux/iTerm.
# ASCII only on purpose: PS 5.1 reads a BOM-less .ps1 as ANSI.
#
# Runs Claude Code with the Windows CTO role + Remote Control on, named
# "WINDOWS CTO #<id>" so the mobile app list says which box this is.
#
# What v2 adds over Phase 1:
#   * cwd = this git clone, so the repo's CLAUDE.md, .claude\skills and
#     .claude\settings.json hooks load exactly as on the Mac. The hooks call
#     `python3`, which on Windows is the Microsoft Store stub; the launcher
#     puts .venv\Scripts (with a python3.exe copy) first on PATH so every
#     hook runs on the venv interpreter. All 15 hooks measured exit 0 here
#     2026-09-28.
#   * model / effort from policies/agents.yaml (same source as the Mac).
#   * org MCP + LungNote, ONLY when %USERPROFILE%\.config\mooniex\org-db.env
#     exists. That file points the org server at the Postgres hub on Contabo
#     (docs/design/tasks-db-hub.md). Without it the session starts in
#     standalone mode, exactly like Phase 1: winbox has no tasks.db of its
#     own and must never grow one (split brain). The file is dropped in by
#     the Mac over `ssh winbox` once the hub cutover (W1) is done.
#
# Usage:  powershell -ExecutionPolicy Bypass -File windows\win-cto.ps1
# First run needs a person at the desk: /login, then accept folder trust.

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvScripts = Join-Path $root '.venv\Scripts'
$venvPy = Join-Path $venvScripts 'python.exe'

# 8-hex session id, same shape as the Mac/Contabo launchers.
$sid = -join ((1..8) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })

$role = Get-Content -Raw -Encoding UTF8 (Join-Path $root 'roles\cto-windows.md')

$claude = "$env:USERPROFILE\.local\bin\claude.exe"
if (-not (Test-Path $claude)) { $claude = 'claude' }   # PATH fallback

# --- venv on PATH, python3 resolvable for the repo hooks ---------------------
if (Test-Path $venvPy) {
    $py3 = Join-Path $venvScripts 'python3.exe'
    if (-not (Test-Path $py3)) { Copy-Item $venvPy $py3 }
    $env:PATH = "$venvScripts;$env:PATH"
} else {
    Write-Host "[win-cto] no .venv yet -- hooks will no-op. Create it with:" -ForegroundColor Yellow
    Write-Host "          python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
}

# --- model / effort from policies/agents.yaml ---------------------------------
$model = 'claude-opus-5-5[1m]'; $effort = 'xhigh'
if (Test-Path $venvPy) {
    try {
        $line = & $venvPy -c "import sys; sys.path.insert(0, r'$root'); from lib.config import role; r = role('cto'); print(r.get('model') or '', r.get('effort') or '')" 2>$null
        $parts = "$line".Trim() -split '\s+'
        if ($parts[0]) { $model = $parts[0] }
        if ($parts.Count -gt 1 -and $parts[1]) { $effort = $parts[1] }
    } catch {}
}

# --- org MCP (hub mode) or standalone -----------------------------------------
$claudeArgs = @()
$orgEnv = Join-Path $env:USERPROFILE '.config\mooniex\org-db.env'
$mcpConfig = $null
if ((Test-Path $orgEnv) -and (Test-Path $venvPy)) {
    # KEY=VALUE lines, same file format scripts/hub/with-org-db-env.sh sources.
    foreach ($l in Get-Content -Encoding UTF8 $orgEnv) {
        if ($l -match '^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            Set-Item -Path "env:$($Matches[1])" -Value ($Matches[2].Trim().Trim('"').Trim("'"))
        }
    }
    $env:CXO_ROLE = 'cto'; $env:CXO_SESSION = '1'; $env:CXO_SESSION_ID = $sid
    $env:CTO_SESSION = '1'; $env:CTO_SESSION_ID = $sid
    $env:ORG_HOST = 'winbox'

    $mcpConfig = Join-Path $env:TEMP "cto-mcp-$sid.json"
    & $venvPy (Join-Path $root 'scripts\lib\cxo_mcp_config.py') --role cto --root $root --out $mcpConfig
    if ($LASTEXITCODE -ne 0) { throw "cxo_mcp_config failed (exit $LASTEXITCODE)" }
    $claudeArgs += @('--mcp-config', $mcpConfig, '--strict-mcp-config')

    # Register in c_level_sessions on the hub; never block the launch on it.
    Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath $venvPy `
        -ArgumentList @('-m', 'tools.register_cxo', '--role', 'cto', '--session', $sid, '--host', 'winbox')
    Write-Host "[win-cto] hub mode: org MCP on (session $sid)" -ForegroundColor Green
} else {
    Write-Host "[win-cto] standalone mode: no org-db.env -> no org MCP (see roles\cto-windows.md)" -ForegroundColor Yellow
}

# Same two env guards cxo-claude.sh sets (IRON-RULES 45, task-9f6fec26).
$env:DISABLE_AUTOUPDATER = '1'
if (-not $env:CLAUDE_CODE_AUTO_COMPACT_WINDOW) { $env:CLAUDE_CODE_AUTO_COMPACT_WINDOW = '300000' }

Set-Location $root
$code = 1
try {
    & $claude `
        -n "WINDOWS CTO #$sid" `
        --model $model --effort $effort `
        --remote-control `
        --permission-mode auto `
        --append-system-prompt $role `
        @claudeArgs
    $code = $LASTEXITCODE
} finally {
    if ($mcpConfig) { Remove-Item -Force -ErrorAction SilentlyContinue $mcpConfig }
}
exit $code
