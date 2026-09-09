$env:ORG_HOST = 'winbox'
$claudeExe = 'C:\Users\UsEr\.local\bin\claude.exe'
$argArray = @(Get-Content -Raw -Path 'C:\Users\UsEr\mooniex\worktrees\mooniex-agents__browser_operator__task-34a6ce3a\.launch\args.json' -Encoding UTF8 | ConvertFrom-Json)
& $claudeExe @argArray
# Windows Terminal's default closeOnExit is "graceful": the tab stays open
# when its process exits NON-zero, which is exactly what a hub-side
# 	askkill /T /F produces. Exit 0 here so the tab closes with the worker
# (CEO rule 2026-09-07: closing a worker closes its window).
exit 0
