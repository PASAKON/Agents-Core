$log = "C:\mooniex\rebuild\line.log"
Add-Content $log ("{0} LINE store install start" -f (Get-Date -Format s))
& winget install --id XPFCC4CD725961 --source msstore --accept-source-agreements --accept-package-agreements --silent --disable-interactivity 2>&1 | Out-File $log -Append
& winget list --id XPFCC4CD725961 --accept-source-agreements 2>&1 | Out-File $log -Append
Add-Content $log ("{0} done rc=$LASTEXITCODE" -f (Get-Date -Format s))
