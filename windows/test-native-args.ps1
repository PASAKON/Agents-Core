# Self-test for windows/native-args.ps1 (M12). Run ON WINBOX (needs node.exe):
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\test-native-args.ps1
# Prints one PASS/FAIL line per check, exits 1 on any FAIL. Side effects: a temp dir,
# removed at the end; a check that a '&' did not run looks for a marker file there.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'native-args.ps1')
$d = Join-Path $env:TEMP ('native-args-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $d | Out-Null
$fails = 0
function Check([string]$Name, [bool]$Ok, [string]$Detail = '') {
    if ($Ok) { "PASS $Name" } else { "FAIL $Name $Detail"; $script:fails++ }
}
try {
    $node = (Get-Command node.exe).Source
    $marker = Join-Path $d 'MARKER.txt'
    $corpus = @('plain', 'a "b" c', 'x" --dangerously-skip-permissions "y', 'C:\dir\', 'C:\my dir\', 'a\"b',
        'a\\"b c', "$([char]0x0E17)$([char]0x0E33) `"q`"", "line1`nline2 `"q`"`n/exit", '"', '\', "tab`there",
        '%PATH% & echo hi | x ^ <y> !x!', "fix it `"& echo INJECTED> `"$marker`" & rem `"", 'ends with space ',
        '""', ' lead', 'a\\\\" b\\')
    $argvJs = Join-Path $d 'argv.js'
    'require("fs").writeFileSync(process.argv[2],JSON.stringify(process.argv.slice(3)),"utf8")' |
        Set-Content -Path $argvJs -Encoding ASCII
    $got = Join-Path $d 'argv.json'
    # args.json written and read back exactly as spawn-worker.ps1 and its launchers do
    $argsJson = Join-Path $d 'args.json'
    [IO.File]::WriteAllText($argsJson, ((@($argvJs, $got) + $corpus) | ConvertTo-Json -Depth 2),
                            (New-Object Text.UTF8Encoding $false))
    $argArray = @(Get-Content -Raw -Path $argsJson -Encoding UTF8 | ConvertFrom-Json)
    Invoke-NativeExe -Exe $node -Arguments $argArray
    $back = [IO.File]::ReadAllText($got, [Text.Encoding]::UTF8) | ConvertFrom-Json
    $back = @($back | ForEach-Object { $_ })
    $same = $back.Count -eq $corpus.Count
    for ($i = 0; $same -and $i -lt $corpus.Count; $i++) { $same = $back[$i] -ceq $corpus[$i] }
    Check 'exe: every hostile argument arrives whole' $same "got $($back.Count) of $($corpus.Count)"
    Check 'exe: exit code in LASTEXITCODE' ($LASTEXITCODE -eq 0)

    $logJs = Join-Path $d 'log.js'
    'let n=0;process.stdin.on("data",c=>n+=c.length);process.stdin.on("end",()=>{console.log("out "+n);console.error("err");process.exit(3)})' |
        Set-Content -Path $logJs -Encoding ASCII
    $log = Join-Path $d 'run.log'
    Invoke-NativeExe -Exe $node -Arguments @($logJs) -LogPath $log -NullStdin
    $text = [IO.File]::ReadAllText($log)
    Check 'exe -LogPath -NullStdin: output logged, stdin empty, exit 3' ($text -match 'out 0' -and $text -match 'err' -and $LASTEXITCODE -eq 3) $text

    $stdinJs = Join-Path $d 'stdin.js'
    'let b=[];process.stdin.on("data",c=>b.push(c));process.stdin.on("end",()=>require("fs").writeFileSync(process.argv[2],Buffer.concat(b)))' |
        Set-Content -Path $stdinJs -Encoding ASCII
    $shim = Join-Path $d 'shim.cmd'
    "@echo off`r`n`"$node`" `"$stdinJs`" %*" | Set-Content -Path $shim -Encoding ASCII
    $out = Join-Path $d 'stdin.out'
    $prompt = $corpus -join "`n"
    $shimArgs = Join-Path $d 'shim-args.json'
    [IO.File]::WriteAllText($shimArgs, (@($out, '--two') | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
    Invoke-WithStdin -Exe $shim -Arguments @(Get-Content -Raw -Path $shimArgs -Encoding UTF8 | ConvertFrom-Json) -Text $prompt
    $sent = [IO.File]::ReadAllText($out, [Text.Encoding]::UTF8).TrimEnd("`r", "`n")
    Check 'cmd shim: stdin text arrives whole (Thai, quotes, &)' ($sent -ceq $prompt)
    Check 'cmd shim: no & in the text ran' (-not (Test-Path $marker))

    $refused = $false; try { Invoke-NativeExe -Exe $shim -Arguments @('x') } catch { $refused = $true }
    Check 'Invoke-NativeExe refuses a .cmd' $refused
    $refused = $false; try { Assert-CmdSafe @('ok', 'C:\a b\c', 'x & y') } catch { $refused = $true }
    Check 'Assert-CmdSafe refuses a cmd metacharacter' $refused
    $refused = $false; try { Assert-CmdSafe @('exec', '-', 'C:\Users\x\wt', 'gpt-5.5-codex') } catch { $refused = $true }
    Check 'Assert-CmdSafe passes plain paths and model names' (-not $refused)
} finally {
    Remove-Item -Recurse -Force $d -ErrorAction SilentlyContinue
}
if ($fails) { exit 1 }
