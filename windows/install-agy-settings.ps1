# Install the winbox agy settings (config\agy-settings-winbox.json) as the agy user settings
# file, in one atomic step, with a backup and the sha256 printed. GH #634.
#
# Run it on winbox as the user that runs agy, from a checkout that holds this file and
# config\agy-settings-winbox.json. The first run is a dry run; the second pins the hash:
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\install-agy-settings.ps1 -DryRun
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\install-agy-settings.ps1 -ExpectSha256 <sha256 printed by the dry run>
#
# The file agy reads is %USERPROFILE%\.gemini\antigravity-cli\settings.json (the Windows form
# of ~/.gemini/antigravity-cli/settings.json in docs/ops/agent-runners.md and
# config/machine-contract.yaml). The folder must already exist: it is agy's own state folder,
# so a missing one means agy has not run as this user (or keeps its state elsewhere), and
# writing a file there would change nothing. Nothing is written in that case.
#
# What it does, in order, and stops at the first failure:
#   1. reads the source as bytes, refuses a BOM, prints and checks its sha256 (-ExpectSha256);
#   2. refuses a source without non-empty permissions.allow and permissions.deny arrays, or
#      with a command(*) allow rule;
#   3. the same bytes already installed: prints ALREADY_INSTALLED and stops;
#   4. an existing different file is copied to settings.json.bak-<yyyyMMdd-HHmmss> first
#      (an existing backup name is never overwritten);
#   5. writes the bytes to a temp file in the same folder, checks its sha256, then replaces
#      settings.json in one step (File.Replace, or File.Move when there is none);
#   6. reads settings.json back and prints SOURCE, DEST, BACKUP and SHA256.
# Rollback: copy the printed BACKUP over settings.json; with BACKUP=none, delete settings.json
# (agy then runs edit-only again).
# Exit codes: 0 done / already installed / dry run, 2 source refused, 3 agy folder missing,
# 4 the written file does not read back the same.
[CmdletBinding()]
param(
    [string]$Source = '',
    [string]$Destination = '',
    [string]$ExpectSha256 = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Get-BytesSha256([byte[]]$Bytes) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return (($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString('x2') }) -join '') }
    finally { $sha.Dispose() }
}

function Stop-Install([int]$Code, [string]$Message) {
    [Console]::Error.WriteLine("install-agy-settings: $Message")
    exit $Code
}

if (-not $Source) { $Source = Join-Path (Split-Path -Parent $PSScriptRoot) 'config\agy-settings-winbox.json' }
if (-not $Destination) { $Destination = Join-Path $env:USERPROFILE '.gemini\antigravity-cli\settings.json' }

# 1. the source bytes and their hash
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { Stop-Install 2 "source not found: $Source" }
$bytes = [System.IO.File]::ReadAllBytes($Source)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Stop-Install 2 "source starts with a BOM: $Source"
}
$srcHash = Get-BytesSha256 $bytes
if ($ExpectSha256 -and ($srcHash -ne $ExpectSha256.Trim().ToLowerInvariant())) {
    Stop-Install 2 "source sha256 is $srcHash, expected $($ExpectSha256.Trim().ToLowerInvariant()); nothing written"
}

# 2. the shape agy needs, and the one rule that must never be there
try { $doc = [System.Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json }
catch { Stop-Install 2 "source is not valid JSON: $Source" }
$allow = @($doc.permissions.allow)
$deny = @($doc.permissions.deny)
if ($allow.Count -eq 0 -or $deny.Count -eq 0) { Stop-Install 2 'source needs non-empty permissions.allow and permissions.deny' }
if ($allow -contains 'command(*)') { Stop-Install 2 'source allows command(*); refused' }

# the agy state folder must already exist
$destDir = Split-Path -Parent $Destination
if (-not (Test-Path -LiteralPath $destDir -PathType Container)) {
    Stop-Install 3 "agy folder not found: $destDir (agy has not run as this user, or keeps its state elsewhere); nothing written"
}

# 3./4. what is there now
$backup = 'none'
$exists = Test-Path -LiteralPath $Destination -PathType Leaf
if ($exists) {
    $oldHash = Get-BytesSha256 ([System.IO.File]::ReadAllBytes($Destination))
    if ($oldHash -eq $srcHash) {
        Write-Output "ALREADY_INSTALLED SHA256=$srcHash DEST=$Destination"
        exit 0
    }
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $backup = "$Destination.bak-$stamp"
    $n = 1
    while (Test-Path -LiteralPath $backup) { $backup = "$Destination.bak-$stamp-$n"; $n++ }
}

if ($DryRun) {
    Write-Output "DRY_RUN SOURCE=$Source DEST=$Destination BACKUP=$backup SHA256=$srcHash"
    exit 0
}

if ($exists) {
    Copy-Item -LiteralPath $Destination -Destination $backup
    if ((Get-BytesSha256 ([System.IO.File]::ReadAllBytes($backup))) -ne $oldHash) {
        Stop-Install 4 "backup $backup does not read back the same; settings.json left as it was"
    }
}

# 5. temp file in the same folder, then one replace
$tmp = Join-Path $destDir ('settings.json.tmp-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
try {
    [System.IO.File]::WriteAllBytes($tmp, $bytes)
    if ((Get-BytesSha256 ([System.IO.File]::ReadAllBytes($tmp))) -ne $srcHash) {
        Stop-Install 4 'the temp file does not read back the same; settings.json left as it was'
    }
    if ($exists) { [System.IO.File]::Replace($tmp, $Destination, [NullString]::Value) }
    else { [System.IO.File]::Move($tmp, $Destination) }
}
finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
}

# 6. read it back
$finalHash = Get-BytesSha256 ([System.IO.File]::ReadAllBytes($Destination))
if ($finalHash -ne $srcHash) { Stop-Install 4 "settings.json reads back as $finalHash, expected $srcHash" }
Write-Output "SOURCE=$Source"
Write-Output "DEST=$Destination"
Write-Output "BACKUP=$backup"
Write-Output "SHA256=$finalHash"
