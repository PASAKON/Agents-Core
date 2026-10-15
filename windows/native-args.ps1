# Pass free text (TASK.md, prompts) to a Windows runner without a shell re-reading it (M12).
#
# Probe on winbox 2026-10-14 (Windows PowerShell 5.1.26100, no pwsh):
#  - `& claude.exe @argArray` handed the exe an argument holding a " unescaped, so the
#    text 'task says "hello world" -n fake' arrived as 3 arguments: a TASK.md could add
#    its own flags. 5.1 decides whether to quote an argument by counting " and ignoring
#    backslashes, so no pre-escaping survives it: the command line is built here.
#  - `& codex.cmd @argArray` runs through cmd.exe, which ran the "& echo ... > file" in
#    the text and wrote the marker file. The prompt goes on stdin instead.
# Dot-sourced by every generated launcher (spawn-worker.ps1 copies this file into the
# task's launch dir). Self-test: windows/test-native-args.ps1, run on winbox.

function ConvertTo-ArgStrings([object[]]$Arguments) {
    # The launchers read args.json with `@(Get-Content -Raw | ConvertFrom-Json)`; on 5.1
    # that is ONE element holding the whole array (ConvertFrom-Json does not unroll),
    # and a [string[]] parameter would join it into one string. Unroll, then stringify.
    return [string[]]@($Arguments | ForEach-Object { $_ } | ForEach-Object { [string]$_ })
}

function ConvertTo-NativeArg([AllowEmptyString()][string]$Value) {
    # One argument quoted for the MSVCRT / CommandLineToArgvW rules claude.exe, agy.exe
    # and node.exe parse with: wrapped in "" when empty or holding whitespace or a ",
    # backslashes before a " doubled and the " written \", trailing backslashes doubled
    # so they do not escape the closing ". \z, not $: in .NET $ also matches before a
    # final newline, which doubled the backslashes of 'C:\dir\' + LF (review #293 M-1).
    # A NUL would end the CreateProcess line there and drop every later flag.
    if ($Value.Contains([string][char]0)) { throw 'ConvertTo-NativeArg: an argument holds a NUL' }
    if ($Value -ne '' -and $Value -notmatch '[\s"]') { return $Value }
    $e = [regex]::Replace($Value, '(\\*)"', { param($m) ($m.Groups[1].Value * 2) + '\"' })
    $e = [regex]::Replace($e, '(\\+)\z', '$1$1')
    return '"' + $e + '"'
}

function Resolve-NativeExe([string]$Preferred, [string]$Name) {
    # The full path when it exists, else the first $Name.exe on PATH. A .cmd shim (an
    # npm install) is refused by name: CreateProcess would not find it, and cmd.exe
    # would re-parse the arguments if it did.
    if ($Preferred -and (Test-Path -LiteralPath $Preferred)) { return $Preferred }
    $hit = @(Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue |
             Where-Object { $_.Source -match '\.exe$' } | Select-Object -First 1)
    if ($hit.Count) { return $hit[0].Source }
    $other = @(Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1)
    $seen = if ($other.Count) { " (found only $($other[0].Source), not an .exe)" } else { '' }
    throw "no $Name.exe at $Preferred or on PATH$seen; install the native $Name.exe"
}

function Invoke-NativeExe {
    # Starts a real .exe (never a .cmd/.bat: cmd.exe would re-parse the line) with the
    # command line built by ConvertTo-NativeArg. Without -LogPath it inherits this
    # console, so a TUI (claude.exe) still has its TTY. -LogPath writes stdout then
    # stderr to that file (UTF-8, no BOM); -NullStdin gives it an empty, closed stdin.
    # Sets $global:LASTEXITCODE and returns nothing.
    param([Parameter(Mandatory)][string]$Exe, [object[]]$Arguments = @(),
          [string]$LogPath = '', [switch]$NullStdin)
    if ($Exe -match '\.(cmd|bat)$') { throw "Invoke-NativeExe: $Exe is a batch file; cmd.exe would re-parse its arguments" }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = (@(ConvertTo-ArgStrings $Arguments | ForEach-Object { ConvertTo-NativeArg $_ }) -join ' ')
    $psi.UseShellExecute = $false
    if ($LogPath) {
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding $false
        $psi.StandardErrorEncoding = New-Object System.Text.UTF8Encoding $false
    }
    if ($NullStdin) { $psi.RedirectStandardInput = $true }
    $p = [System.Diagnostics.Process]::Start($psi)
    if ($NullStdin) { $p.StandardInput.Close() }
    if ($LogPath) {
        $out = $p.StandardOutput.ReadToEndAsync()
        $err = $p.StandardError.ReadToEndAsync()
    }
    $p.WaitForExit()
    if ($LogPath) {
        [System.IO.File]::WriteAllText($LogPath, $out.Result + $err.Result,
                                       (New-Object System.Text.UTF8Encoding $false))
    }
    $global:LASTEXITCODE = $p.ExitCode
}

function Invoke-WithStdin([string]$Exe, [object[]]$Arguments, [string]$Text) {
    # Hands $Text to $Exe on stdin as UTF-8 (no BOM), so free text never reaches a .cmd
    # shim's cmd.exe parsing. The pipe uses the GLOBAL $OutputEncoding (a function-local
    # one left Thai as '?' in the probe). The other arguments must be Assert-CmdSafe.
    $prev = $global:OutputEncoding
    $global:OutputEncoding = New-Object System.Text.UTF8Encoding $false
    $argv = ConvertTo-ArgStrings $Arguments
    try { $Text | & $Exe @argv } finally { $global:OutputEncoding = $prev }
}

function Assert-CmdSafe([object[]]$Values) {
    # An argument that will pass through cmd.exe (a .cmd shim) may hold no character
    # cmd.exe treats specially. A path or model name with one is refused, not escaped.
    foreach ($v in (ConvertTo-ArgStrings $Values)) {
        if ($v -match '["&|<>^%!()\r\n]') { throw "refusing an argument cmd.exe would re-parse: $v" }
    }
}
