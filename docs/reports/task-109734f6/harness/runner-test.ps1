param([string] $Repo)
$sp = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Join-Path $sp 'wakeroot'
$req = Join-Path $root 'state\wake\requests'; $res = Join-Path $root 'state\wake\results'
foreach ($d in @($req, $res)) { if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null } }
$runner = Join-Path $Repo 'windows\wake-request.ps1'
$logT = Join-Path $sp 'test-tab.log'

function Put($id, $json, [int] $ageSec = 0) {
    $p = Join-Path $req "$id.json"
    Set-Content -LiteralPath $p -Value $json -Encoding ASCII
    if ($ageSec -gt 0) { (Get-Item $p).LastWriteTime = (Get-Date).AddSeconds(-$ageSec) }
}
$m = 'RUNNER' + (Get-Random -Maximum 9999)
Put "t1-ok"      "{`"title`":`"-wake-test`",`"marker`":`"[New message from $m]`",`"contains`":true}"
Put "t2-marker"  '{"title":"-wake-test","marker":"hello there","contains":true}'
Put "t3-title"   '{"title":"x\" ; calc","marker":"[New message from X]","contains":false}'
Put "t4-expired" "{`"title`":`"-wake-test`",`"marker`":`"[New message from EXPIRED$m]`",`"contains`":true}" 300
Put "t5-json"    'not json at all'
Set-Content -LiteralPath (Join-Path $req 'bad id !.json') -Value '{}' -Encoding ASCII
$before = @(Get-Content $logT).Count
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -Root $root 2>&1 | Out-Null
Start-Sleep -Milliseconds 800
foreach ($id in 't1-ok', 't2-marker', 't3-title', 't4-expired', 't5-json') {
    $rf = Join-Path $res "$id.json"
    if (Test-Path $rf) { $o = Get-Content $rf -Raw | ConvertFrom-Json; "{0,-11} exit={1} :: {2}" -f $id, $o.exit, $o.output } else { "{0,-11} NO RESULT" -f $id }
}
"bad-id file left in requests: " + (Test-Path (Join-Path $req 'bad id !.json'))
"requests left: " + @(Get-ChildItem $req).Count
"marker t1 received in test tab: " + ((Get-Content $logT | Select-String -SimpleMatch "[New message from $m]").Count)
"marker t4 (expired) received:   " + ((Get-Content $logT | Select-String -SimpleMatch "EXPIRED$m").Count)
"new test-tab log lines: " + (@(Get-Content $logT).Count - $before) + " (expected 1)"
