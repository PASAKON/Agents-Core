$exe = 'C:\Users\passg\.local\bin\claude.exe'
"exists: " + (Test-Path $exe) + "  size: " + ((Get-Item $exe -ErrorAction SilentlyContinue).Length)
$p = Start-Process -FilePath $exe -ArgumentList '--version' -NoNewWindow -PassThru -RedirectStandardOutput C:\mooniex\rebuild\claude_ver.txt -RedirectStandardError C:\mooniex\rebuild\claude_err.txt
if (-not $p.WaitForExit(30000)) { "claude --version did not exit in 30 s -> killed"; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } else { "exit " + $p.ExitCode }
"stdout: " + ((Get-Content C:\mooniex\rebuild\claude_ver.txt -ErrorAction SilentlyContinue) -join ' | ')
"stderr: " + (((Get-Content C:\mooniex\rebuild\claude_err.txt -ErrorAction SilentlyContinue) -join ' | ').Substring(0, [Math]::Min(300, ((Get-Content C:\mooniex\rebuild\claude_err.txt -ErrorAction SilentlyContinue) -join ' | ').Length)))
"claude procs left: " + ((Get-Process claude -ErrorAction SilentlyContinue | Measure-Object).Count)
Get-Process claude -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
"user PATH has .local\bin: " + (([Environment]::GetEnvironmentVariable('Path','User')) -like '*\.local\bin*')
"github.com key test: " + ((& ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1) -join ' ')
