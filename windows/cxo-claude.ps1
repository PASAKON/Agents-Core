# Windows launcher for any C-level (cto/cmo/cgo/cfo) -- Org Mesh W3.2
# (docs/design/org-mesh.md). PowerShell port of scripts/cxo-claude.sh (bash,
# Mac/Contabo) for winbox. PowerShell 5.1 syntax only (this box has no pwsh
# 7). ASCII only on purpose: PS 5.1 reads a BOM-less .ps1 as ANSI, same rule
# windows/win-cto.ps1 already follows.
#
# Later (W3.3) `node_dispatch start_clevel` calls this script on Windows, so
# it must also run unattended from a scheduled task in session 1, not just
# interactively -- see windows/spawn-worker.ps1's session-0/session-1 note
# for why an SSH-launched process needs that.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File windows\cxo-claude.ps1 -Role cto
#   powershell -ExecutionPolicy Bypass -File windows\cxo-claude.ps1 -Role cmo `
#       -Session req-1234abcd -InitialPrompt "..." -TabTitle "CMO ephemeral"
#
# First run needs a person at the desk: /login, then accept folder trust.
#
# Dropped relative to scripts/cxo-claude.sh (winbox has none of these):
#   - iTerm window capture via osascript (.winid file) -- iTerm-only; no
#     Windows Terminal equivalent, and delegate.py does not route Windows
#     CXO tabs by window id the way it does iTerm ones.
#   - tmux session-name adoption for CXO_SESSION_ID -- winbox never runs
#     tmux; a fresh 8-hex id is always generated unless -Session overrides.
#   - .tty file + scripts/tab-title.sh's 60s title-keeper loop, plus
#     tools/maintab.py's Main Tab (OSC 2 titlebar) seeding and the iTerm
#     HIDE_TAB_BAR_WHEN_ONLY_ONE_TAB preference push -- all iTerm-specific.
#     The tab title here is set once via $Host.UI.RawUI.WindowTitle, which
#     Windows Terminal reads for its own tab strip; no keeper loop is needed
#     because there is no zsh precmd / iTerm profile write clobbering it.
#   - scripts/idle-ping-watcher.sh (auto-close an idle ephemeral tab) --
#     polls iTerm tab contents via osascript; no Windows port exists yet.
#     An ephemeral -Session spawn on winbox does not auto-close. Flagged as
#     a follow-up for whoever builds W3.3's ephemeral ephemeral-spawn path.
#   - LUNGNOTE_MCP_NODE / node-v22 override -- Contabo-only (system node 20
#     lacks native WebSocket); winbox's node is current enough already.
#
# Review fixes vs the cherry-picked windows/win-cto.ps1 v2 (6edac472), now
# folded into this generalized launcher instead of patching that one:
#   - win-cto.ps1:72-74 only exported CXO_ROLE/CXO_SESSION/CXO_SESSION_ID/
#     CTO_SESSION/CTO_SESSION_ID inside the hub-mode branch, so a standalone
#     launch (the box's default state pre-W1) had NONE of them set even
#     though a session id had already been generated. Exported unconditionally
#     here, matching scripts/cxo-claude.sh.
#   - win-cto.ps1 never generated or passed --allowed-tools, so a hub-mode
#     session had no role tool whitelist at all (the exact bug
#     scripts/lib/cxo_mcp_config.py's own docstring calls out as G1: a
#     server that loads but whose tools aren't allow-listed pays the process
#     cost then prompts on every call). Added via --print-allowed here.
#   - win-cto.ps1's `(Test-Path $orgEnv) -and (Test-Path $venvPy)` collapsed
#     two different failure reasons into one "standalone: no org-db.env"
#     message, which is wrong when org-db.env exists but the venv doesn't.
#     Split into two checks with distinct log lines below.
#   - win-cto.ps1 had no lock file, so a second launch under the same
#     role+session id was never refused (Mac/Contabo always refuse). Ported
#     the lock file + the persisted .uuid file + the <role>-active pointer,
#     none of which existed in v2.
#   - win-cto.ps1 never registered/reconciled against c_level_sessions
#     (tools.register_cxo / tools.session_reconcile), so gate 4 could never
#     see a Windows CTO session even in hub mode. Added, hub-mode only.
#
# Deployed to the Agents clone under this Windows user's own profile --
# never a hardcoded profile name; see $root below, which resolves from this
# script's own location instead.

param(
    [Parameter(Mandatory = $true)][ValidateSet('cto', 'cmo', 'cgo', 'cfo')][string]$Role,
    [string]$Session = '',
    [string]$InitialPrompt = '',
    [string]$TabTitle = '',
    # Any claude.exe flags not recognized above (e.g. -r/--resume) ride
    # through here, same job cxo-claude.sh's manual ARGS[] loop does.
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$RemainingArgs = @()
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvScripts = Join-Path $root '.venv\Scripts'
$venvPy = Join-Path $venvScripts 'python.exe'

if (-not (Test-Path $venvPy)) {
    Write-Host "[cxo-claude] no .venv at $venvPy -- create it with:" -ForegroundColor Red
    Write-Host "             python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 2
}

# Resolve explicit resume targets before writing session state or tab titles.
$uuidPattern = '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
for ($i = 0; $i -lt $RemainingArgs.Count; $i++) {
    if ($RemainingArgs[$i] -notin @('-r', '--resume')) { continue }
    if ($i + 1 -ge $RemainingArgs.Count -or $RemainingArgs[$i + 1].StartsWith('-')) { continue }
    $i++
    $resumeId = $RemainingArgs[$i]
    if ($resumeId -cmatch $uuidPattern) { continue }
    if ($resumeId -cnotmatch '^[0-9a-f]{8}$') {
        [Console]::Error.WriteLine('refuse to resume: expected 8 lowercase hex characters or a full UUID')
        exit 2
    }
    $resumeFile = Join-Path $root "state\locks\$Role-$resumeId.uuid"
    $resumeTarget = ''
    if (Test-Path $resumeFile) {
        $resumeTarget = (Get-Content -Raw -Path $resumeFile -ErrorAction SilentlyContinue) -replace '\s', ''
    }
    if ($resumeTarget -cnotmatch $uuidPattern) {
        Push-Location $root
        try {
            $resumeTarget = (& $venvPy -m tools.session_status resume --role $Role --session-id $resumeId 2>$null) -join "`n"
            $resumeTarget = $resumeTarget.Trim()
        } catch {
            $resumeTarget = ''
        } finally {
            Pop-Location
        }
    }
    if ($resumeTarget -cnotmatch $uuidPattern) {
        [Console]::Error.WriteLine("refuse to resume $Role-${resumeId}: no resumable UUID found; checked $resumeFile and c_level_sessions.resume_uuid via tools.session_status resume (role=$Role, session_id=$resumeId)")
        exit 2
    }
    $RemainingArgs[$i] = $resumeTarget
}

# venv on PATH, python3 resolvable for the repo hooks (same as win-cto.ps1):
# the hooks call `python3`, which on Windows is the Microsoft Store stub.
$py3 = Join-Path $venvScripts 'python3.exe'
if (-not (Test-Path $py3)) { Copy-Item $venvPy $py3 }
$env:PATH = "$venvScripts;$env:PATH"

# Role doc: prefer a Windows-specific doc (roles\<role>-windows.md, e.g. the
# existing cto-windows.md) and fall back to the shared one used on Mac/Contabo.
$roleDocPath = Join-Path $root "roles\$Role-windows.md"
if (-not (Test-Path $roleDocPath)) { $roleDocPath = Join-Path $root "roles\$Role.md" }
if (-not (Test-Path $roleDocPath)) {
    Write-Host "[cxo-claude] role doc not found: $roleDocPath" -ForegroundColor Red
    exit 2
}
$rolePrompt = Get-Content -Raw -Encoding UTF8 $roleDocPath

# Display name / model / fallback-model / effort from policies/agents.yaml --
# same source of truth as cxo-claude.sh -- and the same is_c_level guard, so
# an unknown/mistyped role fails loudly here instead of launching with made-up
# defaults. ValidateSet above already narrows -Role to real C-level keys, so
# this mainly guards the day that set drifts from policies/agents.yaml's own
# `c_level:` list.
$pyRoleCode = @"
import sys
sys.path.insert(0, r'$root')
from lib.config import display_for, is_c_level, role as get_role
if not is_c_level('$Role'):
    print('role $Role is not a C-level role', file=sys.stderr)
    sys.exit(2)
r = get_role('$Role')
model = r.get('model') or 'claude-opus-5-5[1m]'
fallback = r.get('fallback_model') or 'claude-fable-5'
effort = r.get('effort') or 'xhigh'
print(display_for('$Role'), model, fallback, effort)
"@
$roleLine = & $venvPy -c $pyRoleCode 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[cxo-claude] $roleLine" -ForegroundColor Red
    exit 2
}
$roleParts = "$roleLine".Trim() -split '\s+'
$display = $roleParts[0]
$model = $roleParts[1]
$fallbackModel = $roleParts[2]
$effort = $roleParts[3]

# Session id: -Session override (ephemeral spawn, ADR 2026-05-26 Decision 2),
# else a fresh 8-hex id. No tmux adoption on Windows (winbox never runs tmux).
if ($Session) { $sid = $Session } else {
    $sid = -join ((1..8) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
}

# CXO_* are the canonical env keys for any C-level session, exported
# unconditionally (hub or standalone) -- see the review-fix note above for
# why win-cto.ps1 v2's hub-only placement of this was a bug.
$env:CXO_ROLE = $Role
$env:CXO_SESSION = '1'
$env:CXO_SESSION_ID = $sid
$env:ORG_HOST = 'winbox'
$hostKey = 'winbox'
if ($Role -eq 'cto') {
    $env:CTO_SESSION = '1'
    $env:CTO_SESSION_ID = $sid
}

$locksDir = Join-Path $root 'state\locks'
New-Item -ItemType Directory -Force -Path $locksDir | Out-Null

# Persisted .uuid file: a full RFC4122 uuid whose trailing 8 hex chars equal
# $sid (rest random) -- same construction as cxo-claude.sh, so a resume-by-
# short-id tool can look up the real Claude Code session uuid later. Only
# ids shaped like the standard 8 lowercase hex chars support this; an
# ephemeral "req-xxxxxxxx" id (send_to_cxo.py --spawn) falls back to a fully
# random uuid instead of crashing the hex constructor.
if ($sid -match '^[0-9a-f]{8}$') {
    $cxoUuid = & $venvPy -c "import uuid, sys`nsuffix = sys.argv[1]`nfull = uuid.uuid4().hex[:-8] + suffix`nprint(uuid.UUID(hex=full))" $sid
} else {
    $cxoUuid = & $venvPy -c "import uuid; print(uuid.uuid4())"
}
$cxoUuid = "$cxoUuid".Trim()
$uuidFile = Join-Path $locksDir "$Role-$sid.uuid"
Set-Content -Path $uuidFile -Value $cxoUuid -Encoding ASCII -NoNewline

# Lock file: refuse a second launch under the same role+session id while the
# earlier process is still alive -- Get-Process is the Windows equivalent of
# cxo-claude.sh's `kill -0 $existing_pid` liveness check.
$lockFile = Join-Path $locksDir "$Role-$sid.lock"
if (Test-Path $lockFile) {
    $existingPidText = (Get-Content -Raw -Path $lockFile -ErrorAction SilentlyContinue)
    if ($existingPidText) { $existingPidText = $existingPidText.Trim() }
    $existingProc = $null
    if ($existingPidText) {
        try { $existingProc = Get-Process -Id ([int]$existingPidText) -ErrorAction SilentlyContinue } catch {}
    }
    if ($existingProc) {
        Write-Host "[cxo-claude] $display id $sid already running as pid $existingPidText -- refuse to start a second one." -ForegroundColor Red
        exit 1
    }
    Remove-Item -Force $lockFile
}
Set-Content -Path $lockFile -Value "$PID" -Encoding ASCII -NoNewline

# Active-session pointer: only for non-ephemeral launches (no -Session
# override) -- an ephemeral spawn must never clobber the CEO's primary tab
# pointer (same rule cxo-claude.sh enforces).
$activeFile = Join-Path $locksDir "$Role-active"
$wroteActive = $false
if (-not $Session) {
    Set-Content -Path $activeFile -Value $sid -Encoding ASCII -NoNewline
    $wroteActive = $true
}

# Tab title: -TabTitle override, else the default "$display #$sid" shape.
# Set once via the console title, which Windows Terminal reads for its own
# tab strip -- no iTerm-style keeper loop needed here (see header note).
if ($TabTitle) { $resolvedTabTitle = $TabTitle } else { $resolvedTabTitle = "$display #$sid" }
try { $Host.UI.RawUI.WindowTitle = $resolvedTabTitle } catch {}
# Keep claude CLI from overwriting the title we just set (no-op on builds
# without this env, same guard cxo-claude.sh sets).
$env:CLAUDE_CODE_DISABLE_TERMINAL_TITLE = '1'

# Org MCP (+ LungNote) only in hub mode. winbox reaches the hub through its
# Infisical machine identity (W3.4, CEO approval 2026-10-03):
# cxo_mcp_config.py --hub-route answers "infisical" only when node.yaml says
# `org_db: hub` and the winbox credential file exists, and the config it
# then generates starts the org server under
# `tools\infisical_setup.py run Agents-Core prod --as winbox`, so ORG_DB_URL
# lives in that process only. There is never an org-db.env on winbox.
# Anything else is standalone, as the CEO's 2026-09-28 ruling ("wait for
# both W1s") requires: org MCP and lungnote left out cleanly, one clear log
# line each, never a crash, never a prompt for a secret. This also generates
# --allowed-tools from the same generator (missing in v2 -- see the
# review-fix note above).
$mcpConfig = $null
$allowedTools = @()
$hubRoute = 'none'
try {
    $hubRoute = "$(& $venvPy (Join-Path $root 'scripts\lib\cxo_mcp_config.py') --root $root --hub-route)".Trim()
} catch {}
if (-not $hubRoute) { $hubRoute = 'none' }
if ($hubRoute -eq 'infisical') {
    $mcpConfig = Join-Path $env:TEMP "cxo-mcp-$sid.json"
    & $venvPy (Join-Path $root 'scripts\lib\cxo_mcp_config.py') --role $Role --root $root --out $mcpConfig
    if ($LASTEXITCODE -ne 0) { throw "cxo_mcp_config failed (exit $LASTEXITCODE)" }
    $allowedLine = & $venvPy (Join-Path $root 'scripts\lib\cxo_mcp_config.py') --role $Role --root $root --print-allowed
    if ($LASTEXITCODE -ne 0) { throw "cxo_mcp_config --print-allowed failed (exit $LASTEXITCODE)" }
    $allowedTools = @("$allowedLine".Trim() -split '\s+' | Where-Object { $_ -ne '' })

    # Register + reconcile against c_level_sessions on the hub, hub mode
    # only: both tools write through lib.db, which falls back to a LOCAL
    # sqlite state\tasks.db when ORG_DB_URL is unset -- exactly the
    # split-brain winbox must never create. So both start under the same
    # `infisical_setup.py run` as the org server. Backgrounded + best-effort,
    # same as cxo-claude.sh -- neither may delay or block this launch.
    $hubRun = @('-E', '-s', (Join-Path $root 'tools\infisical_setup.py'), 'run', 'Agents-Core', 'prod', '--as', 'winbox', '--', $venvPy)
    try {
        Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath $venvPy `
            -ArgumentList ($hubRun + @('-m', 'tools.session_reconcile', '--apply')) | Out-Null
    } catch {}
    try {
        Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath $venvPy `
            -ArgumentList ($hubRun + @('-m', 'tools.register_cxo', '--role', $Role, '--session', $sid, '--host', $hostKey)) | Out-Null
    } catch {}
    Write-Host "[cxo-claude] hub mode: org MCP on (session $sid, ORG_DB_URL via Infisical as winbox)" -ForegroundColor Green
} else {
    Write-Host "[cxo-claude] standalone: hub route '$hubRoute' (needs org_db: hub in node.yaml + the winbox Infisical credential) -> org MCP skipped" -ForegroundColor Yellow
    Write-Host "[cxo-claude] standalone: no hub route -> LungNote MCP skipped" -ForegroundColor Yellow
}

# Without --strict-mcp-config the session also loads Agents/.mcp.json,
# ~/.claude.json and every enabled plugin's servers -- some of which read a
# secret from the environment that does not exist on winbox pre-W1, which is
# exactly the "prompt for a secret" failure this launcher must never cause.
# Applied in BOTH modes (unlike --mcp-config, which only exists in hub mode)
# so a standalone launch ends up with zero MCP servers, not an inherited,
# half-configured set. tools/delegate.py's _render_remote_claude_args already
# establishes this exact pattern for remote workers (--strict-mcp-config with
# no --mcp-config at all when a box "can't have" org MCP).
$mcpArgs = @()
if ($mcpConfig) { $mcpArgs += @('--mcp-config', $mcpConfig) }
$strictMcp = if ($env:CXO_STRICT_MCP) { $env:CXO_STRICT_MCP } else { '1' }
if ($strictMcp -eq '1') { $mcpArgs += @('--strict-mcp-config') }
$allowedToolsArgs = @()
if ($allowedTools.Count -gt 0) { $allowedToolsArgs = @('--allowed-tools') + $allowedTools }

# Remote Control registration (task-bbdfa8d1, CEO 2026-09-11): every C-level
# session must show in the CEO's Claude app. Reuses runners.worker_init's
# remote_control_args() -- the same per-host switch (config/hosts.yaml
# `remote_control`, default true) win-cto.ps1 already hardcoded for cto --
# generalized here so a config change governs every role without a launcher
# edit. Fails open (flag included) on any lookup error, same as the function
# it calls.
$remoteControlArgs = @()
$rcCheck = & $venvPy -c "import sys; sys.path.insert(0, r'$root'); from runners.worker_init import remote_control_args; print('1' if remote_control_args('$hostKey') else '0')" 2>$null
if ($LASTEXITCODE -ne 0 -or "$rcCheck".Trim() -ne '0') { $remoteControlArgs = @('--remote-control') }

# --session-id + --resume/--continue is only legal combined with
# --fork-session (claude CLI refuses otherwise) -- detect -r/--resume/
# -c/--continue in the pass-through args and add it, same as cxo-claude.sh.
$forkArgs = @()
foreach ($a in $RemainingArgs) {
    if ($a -eq '-r' -or $a -eq '--resume' -or $a -eq '-c' -or $a -eq '--continue') { $forkArgs = @('--fork-session') }
}

# An "update available" prompt is a startup-level interrupt that can block an
# unattended session on a keypress nobody is there to press (IRON-RULES #45).
$env:DISABLE_AUTOUPDATER = '1'
if (-not $env:CLAUDE_CODE_AUTO_COMPACT_WINDOW) { $env:CLAUDE_CODE_AUTO_COMPACT_WINDOW = '300000' }

# Pull the auto-memory repo before claude starts (task-8d37c0f1): the harness
# loads MEMORY.md into context at process start, before any skill can run, so
# this is the only place a fresh pull lands in time. Never fails the launch --
# memory_sync.pull() degrades to "stale memory" on any error, and the
# CTO_CLAUDE_TEST_MODE guard mirrors cxo-claude.sh's own (skips the pull
# during automated tests of this launcher).
if ($env:CTO_CLAUDE_TEST_MODE -ne '1') {
    try { & $venvPy -m tools.memory_sync pull 2>$null | Out-Null } catch {}
}

$claude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
if (-not (Test-Path $claude)) { $claude = 'claude' }

# INITIAL_PROMPT (ephemeral --spawn) rides in as claude's final positional
# argv, same as the pass-through args -- a `claude` process started with a
# positional prompt auto-submits it instantly. Passed as one array element
# via splat (@fullArgs below), so -- unlike spawn-worker.ps1's wt.exe/
# scheduled-task path, which goes through THREE layers of shell re-quoting
# and needs a JSON-file indirection -- this single direct invocation needs
# none of that; win-cto.ps1 already appends --append-system-prompt (often
# several KB of text) the same direct way.
$positional = @()
foreach ($a in $RemainingArgs) { $positional += $a }
if ($InitialPrompt) { $positional += $InitialPrompt }

$modelArgs = @('--model', $model, '--fallback-model', $fallbackModel, '--effort', $effort)
$machineLabel = 'WINDOWS'

# Same flag order as cxo-claude.sh: mcp-config, strict, remote-control,
# allowed-tools (variadic -- must be immediately followed by a "--flag", not
# by another bare token, so it stops consuming at --session-id), session-id,
# fork, positional prompt.
$fullArgs = @('-n', "$machineLabel $resolvedTabTitle") + $modelArgs +
    @('--permission-mode', 'auto', '--append-system-prompt', $rolePrompt) +
    $mcpArgs + $remoteControlArgs + $allowedToolsArgs +
    @('--session-id', $cxoUuid) + $forkArgs + $positional

# `exec` has no PowerShell equivalent that still lets the finally block below
# run -- claude runs as a child, matching cxo-claude.sh's own comment on why
# it never execs claude either (stale lock on exit otherwise).
$code = 1
try {
    & $claude @fullArgs
    $code = $LASTEXITCODE
} finally {
    if ($mcpConfig) { Remove-Item -Force -ErrorAction SilentlyContinue $mcpConfig }
    Remove-Item -Force -ErrorAction SilentlyContinue $lockFile
    Remove-Item -Force -ErrorAction SilentlyContinue $uuidFile
    if ($wroteActive -and (Test-Path $activeFile)) {
        $current = (Get-Content -Raw -Path $activeFile -ErrorAction SilentlyContinue)
        if ($current) { $current = $current.Trim() }
        if ($current -eq $sid) { Remove-Item -Force -ErrorAction SilentlyContinue $activeFile }
    }
}
exit $code
