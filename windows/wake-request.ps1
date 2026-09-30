# wake-request.ps1 - body of the persistent MooniexOrgWake task (W3.5).
#
# ssh lands in session 0, which has no desktop, and registering a scheduled task
# from an ssh command was refused by the auto-mode classifier as "Unauthorized
# Persistence" (2026-09-30). So the CEO registers ONE task once, at the desktop
# (windows\register-org-tasks.ps1), and the remote side only does two things:
#
#   1. write  <checkout>\state\wake\requests\<id>.json   {"title":..,"marker":..,"contains":true}
#   2. run    schtasks /run /tn MooniexOrgWake
#
# This script is what that task runs, in the console session. It takes every
# request file, checks it, runs windows\wake.ps1 for it and writes
# <checkout>\state\wake\results\<id>.json {"id","exit","output","finished"}.
#
# ASCII only. The request folder is a TRUST BOUNDARY: whoever can drop a file
# there can make this type a line + Enter into a Windows Terminal tab. So it is
# not a general "type this" service. It accepts exactly one marker shape,
# "[New message from <LABEL>]" (the org's wake nudge), and a tab title made of
# a small safe alphabet; anything else is refused and no key is sent.
param([string] $Root = '')

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$wake = Join-Path $PSScriptRoot 'wake.ps1'
$reqDir = Join-Path $Root 'state\wake\requests'
$resDir = Join-Path $Root 'state\wake\results'
$logDir = Join-Path $Root 'state\logs'
foreach ($d in @($reqDir, $resDir, $logDir)) { if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d | Out-Null } }
$wakeLog = Join-Path $logDir 'wake.log'

$ID_RE     = '^[A-Za-z0-9_-]{1,64}$'
$TITLE_RE  = '^[A-Za-z0-9_.# -]{1,80}$'
$MARKER_RE = '^\[New message from [A-Za-z0-9_.#-]{1,40}\]$'
$MAX_AGE_S = 120        # a wake nobody served for two minutes is noise, not news
$RUN_BUDGET_S = 90      # one task run serves the whole queue, then exits

function Write-Result([string] $id, [int] $code, [string] $out) {
    $o = [ordered]@{ id = $id; exit = $code; output = (($out -replace '\s+', ' ').Trim() -replace '[^\x20-\x7E]', '?')
                     finished = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') }
    $tmp = Join-Path $resDir "$id.tmp"
    Set-Content -LiteralPath $tmp -Value ($o | ConvertTo-Json -Compress) -Encoding ASCII
    Move-Item -LiteralPath $tmp -Destination (Join-Path $resDir "$id.json") -Force
}

$deadline = (Get-Date).AddSeconds($RUN_BUDGET_S)
do {
    $files = @(Get-ChildItem -LiteralPath $reqDir -Filter '*.json' -File -ErrorAction SilentlyContinue | Sort-Object Name)
    foreach ($f in $files) {
        $id = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
        if ($id -cnotmatch $ID_RE) { Remove-Item -LiteralPath $f.FullName -Force; continue }
        $work = Join-Path $reqDir "$id.working"
        try { Move-Item -LiteralPath $f.FullName -Destination $work -ErrorAction Stop } catch { continue }   # claimed / gone
        try {
            if (((Get-Date) - $f.LastWriteTime).TotalSeconds -gt $MAX_AGE_S) { Write-Result $id 5 'request expired, nothing sent'; continue }
            try { $req = Get-Content -LiteralPath $work -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Write-Result $id 6 'request is not valid JSON, nothing sent'; continue }
            $title = [string]$req.title; $marker = [string]$req.marker
            if ($title -cnotmatch $TITLE_RE) { Write-Result $id 6 'title outside the allowed alphabet, nothing sent'; continue }
            if ($marker -cnotmatch $MARKER_RE) { Write-Result $id 6 'marker is not "[New message from <LABEL>]", nothing sent'; continue }
            $wa = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $wake, '-Title', $title, '-Marker', $marker, '-Log', $wakeLog)
            if ($req.contains -eq $true) { $wa += '-Contains' }
            $out = & powershell.exe @wa 2>&1 | Out-String
            Write-Result $id $LASTEXITCODE $out
        } catch {
            Write-Result $id 7 ("runner error: " + $_.Exception.Message)
        } finally {
            Remove-Item -LiteralPath $work -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Milliseconds 500
    $more = @(Get-ChildItem -LiteralPath $reqDir -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
} while ($more -gt 0 -and (Get-Date) -lt $deadline)
