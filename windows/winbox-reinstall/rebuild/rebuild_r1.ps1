# winbox rebuild R1: base tools via winget + Claude Code CLI. Idempotent; logs to C:\mooniex\rebuild\r1.log
$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path C:\mooniex\rebuild | Out-Null
$log = 'C:\mooniex\rebuild\r1.log'
function L($m) { $line = "{0} {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Add-Content -Path $log -Value $line }
L "R1 start user=$env:USERNAME"
$pkgs = @('Git.Git','Python.Python.3.11','Python.Launcher','Rclone.Rclone','OpenJS.NodeJS.LTS','GitHub.cli',
          'Gyan.FFmpeg','yt-dlp.yt-dlp','Google.Chrome','Microsoft.VisualStudioCode','Google.Antigravity','BlueStack.BlueStacks')
foreach ($p in $pkgs) {
  $have = (& winget list --id $p --exact --accept-source-agreements 2>&1 | Out-String)
  if ($have -match [regex]::Escape($p)) { L "SKIP $p (installed)"; continue }
  L "INSTALL $p"
  $out = & winget install --id $p --exact --silent --accept-source-agreements --accept-package-agreements --disable-interactivity --source winget 2>&1 | Out-String
  L ("  rc=$LASTEXITCODE " + (($out -split "`n" | Where-Object { $_ -match 'Successfully|Found|error|fail|already' } | Select-Object -Last 2) -join ' | ').Trim())
}
# Claude Code CLI (native Windows installer)
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  L "INSTALL claude code"
  try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression 2>&1 | Out-Null; L "  claude installer ran" } catch { L "  claude installer error: $($_.Exception.Message)" }
}
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
foreach ($c in 'git','python','py','rclone','node','npm','gh','ffmpeg','yt-dlp','claude','code','agy') {
  $w = Get-Command $c -ErrorAction SilentlyContinue; L ("have {0}: {1}" -f $c, $(if ($w) { $w.Source } else { '-' }))
}
L ("python: " + (& py -3.11 --version 2>&1)); L ("git: " + (& git --version 2>&1)); L ("claude: " + (& claude --version 2>&1))
L "R1 done"; Set-Content C:\mooniex\rebuild\r1.done (Get-Date -Format s)
