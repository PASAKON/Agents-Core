$ErrorActionPreference = 'Continue'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
foreach ($p in 'Microsoft.VCRedist.2015+.x64','Microsoft.VCRedist.2015+.x86') {
  $o = & winget install --id $p --exact --silent --accept-source-agreements --accept-package-agreements --disable-interactivity --source winget 2>&1 | Out-String
  "vcredist $p rc=$LASTEXITCODE " + (($o -split "`n" | Where-Object { $_ -match 'Successfully|already|error|fail' } | Select-Object -Last 1) -join '').Trim()
}
$py = 'C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe'
"onnxruntime: " + (& $py -c "import onnxruntime as o; print('ok', o.__version__)" 2>&1 | Select-Object -Last 1)
"--- LINE store: " + ((Get-Content C:\mooniex\rebuild\line.log -ErrorAction SilentlyContinue | Where-Object { $_ -match 'Success|LINE|error|fail|No package|done' } | Select-Object -Last 3) -join ' | ')
"--- task actions:"
foreach ($t in 'CookieRunAppSrc','CookieRunAsk','CookieRun-DiskSense','CookieRunStreamRetry','MooniexPCLease','MooniexPCLeaseClear','MooniexCookieRunProbe','MooniexCookieRunRevive','MooniexCtoRun') {
  $a = (Get-ScheduledTask $t -ErrorAction SilentlyContinue).Actions | Select-Object -First 1
  $exe = $a.Execute -replace '"',''; $arg = $a.Arguments
  $file = if ($arg -match '(C:\\[^ "]+\.(py|bat|ps1|json))') { $matches[1] } else { '' }
  "{0,-24} exe={1} args-file={2} trig={3}" -f $t, $(Test-Path $exe), $(if ($file) { "$file " + (Test-Path $file) } else { $arg.Substring(0,[Math]::Min(40,$arg.Length)) }), ((Get-ScheduledTask $t).Triggers | ForEach-Object { $_.CimClass.CimClassName -replace 'MSFT_Task','' }) -join '+'
}
foreach ($t in 'MooniexCookieRunRevive','CookieRunStreamRetry') { schtasks /Change /TN $t /DISABLE | Out-Null; "$t disabled until the game is back" }
