# WINBOX WORKER LAUNCHER — Phase 1 (docs/design/multi-host-workers.md).
#
# Invoked by tools/delegate.py's _spawn_remote() over:
#   ssh winbox powershell -NoProfile -ExecutionPolicy Bypass -File spawn-worker.ps1 ...
#
# Clones/fetches the project, adds a worktree on a fresh task branch, writes
# TASK.md + WORKER.md, and launches `claude.exe` --remote-control inside a
# visible Windows Terminal tab (ADDENDUM 1, CTO 2026-09-07: Remote Control
# needs an interactive console session, so a fully detached Start-Process
# would never show up in the CEO's Claude app — same reason win-cto.ps1
# runs the Windows CTO inside a wt.exe tab rather than detached). Prints the
# child pid as the LAST line of stdout so the Mac side can parse it with
# `lines[-1]`. Every other line this script prints is informational and
# must come BEFORE that one.
#
# PowerShell 5.1 syntax only (this box has no pwsh 7). Never prompts —
# every git/ssh call is forced non-interactive, so a bad credential or an
# unknown host key fails loudly instead of hanging the whole pipe.
#
# Deployed to $AgentsRoot (e.g. C:\Users\UsEr\mooniex\spawn-worker.ps1) by
# scp as part of tools/delegate.py's automatic deploy check — re-run that
# check (sha256 compare) after editing this file, there is no git clone of
# the Agents repo on this box.

param(
    [Parameter(Mandatory = $true)][string]$Task,
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$Role,
    [Parameter(Mandatory = $true)][string]$Branch,
    [Parameter(Mandatory = $true)][string]$Base,
    [Parameter(Mandatory = $true)][string]$RepoUrl,
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [Parameter(Mandatory = $true)][string]$WorktreeRoot,
    [Parameter(Mandatory = $true)][string]$ClaudeArgs,
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][string]$Effort,
    [Parameter(Mandatory = $true)][string]$SessionName,
    [string]$TaskFile = ''
)

$ErrorActionPreference = 'Stop'
$env:GIT_TERMINAL_PROMPT = '0'

# --- GitHub reachability: port 22 may be blocked from this box (measured
# 2026-09-07 — `ssh -T git@github.com` hung with no ConnectTimeout). Probe
# with a bounded timeout; on failure/hang, fall back to ssh.github.com:443
# (GitHub's documented SSH-over-443 endpoint) by writing a Host override
# into this user's ~/.ssh/config, unless one is already there. Reported on
# the line prefixed GITHUB_SSH_ROUTE= so the Mac side can log which path
# actually worked.
function Ensure-GithubSshRoute {
    # Probe GitHub with a bounded `git ls-remote`, NOT `ssh -T git@github.com`:
    # on Windows OpenSSH the -T login test never returns from PowerShell (three
    # hung probes found on winbox 2026-09-07), while git ls-remote with the same
    # key answers in ~3 s. Fallback to ssh.github.com:443 is process-scoped via
    # GIT_SSH_COMMAND; the user's ~/.ssh/config is never written.
    function Test-GitRoute([string]$sshCmd) {
        $old = $env:GIT_SSH_COMMAND
        if ($sshCmd) { $env:GIT_SSH_COMMAND = $sshCmd }
        try {
            $p = Start-Process -FilePath git -ArgumentList @('ls-remote','--exit-code',$RepoUrl,'HEAD') -NoNewWindow -PassThru -RedirectStandardOutput "$env:TEMP\gitprobe-out.txt" -RedirectStandardError "$env:TEMP\gitprobe-err.txt"
            # Windows PowerShell 5.1 quirk: unless the process handle is touched
            # BEFORE the process exits, $p.ExitCode stays $null afterwards, and
            # ($null -eq 0) is $false — so every probe read as "unreachable"
            # while the ls-remote had in fact succeeded (stdout held HEAD's sha).
            # Measured on winbox 2026-09-17: waited=True exit=<empty>. Caching
            # the handle makes the exit code observable.
            $null = $p.Handle
            if (-not $p.WaitForExit(20000)) { try { $p.Kill() } catch {}; return $false }
            return ($p.ExitCode -eq 0)
        } catch { return $false }
        finally { if (-not $sshCmd) { $env:GIT_SSH_COMMAND = $old } }
    }
    if (Test-GitRoute $null) { return 'github.com:22' }
    $fallback = 'ssh -o HostName=ssh.github.com -p 443 -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new'
    if (Test-GitRoute $fallback) {
        Write-Output 'GITHUB_SSH_ROUTE=fallback-443 (port 22 probe failed; user ssh config left untouched)'
        return 'ssh.github.com:443'
    }
    Write-Output 'GITHUB_SSH_ROUTE=unreachable (both port 22 and 443 probes failed)'
    return 'unreachable'
}

try {
    # PowerShell 5.1 + $ErrorActionPreference='Stop' turns ANY native stderr
    # line (git progress, "Preparing worktree", a harmless "branch not found"
    # from the idempotent branch -D) into a terminating error — even under
    # 2>$null. That failed the first real winbox spawn on 2026-09-07. Git's
    # success/failure is its exit code, so check $LASTEXITCODE explicitly and
    # let stderr flow.
    $ErrorActionPreference = 'Continue'
    function Assert-Git([string]$what) { if ($LASTEXITCODE -ne 0) { throw "git $what failed (exit $LASTEXITCODE)" } }

    $githubRoute = Ensure-GithubSshRoute
    Write-Output "GITHUB_SSH_ROUTE=$githubRoute"

    # Non-interactive SSH for every git network op below — an unknown host
    # key or a missing credential must fail, never prompt into a dead pipe.
    $env:GIT_SSH_COMMAND = 'ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new'

    # --- 1. Clone (first use) or fetch (repeat use) the canonical checkout ---
    if (-not (Test-Path (Join-Path $RepoPath '.git'))) {
        $parent = Split-Path $RepoPath -Parent
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        # blob:none skips the multi-GB media pack (docs/reports mp4/png); blobs stream in on checkout as needed
        git clone --filter=blob:none $RepoUrl $RepoPath 2>&1 | Select-Object -Last 2
        Assert-Git "clone"
    }
    git -C $RepoPath fetch origin

    # --- 2. Worktree on a fresh task branch (idempotent: this launcher may
    # run more than once for the same task while the pipe is being tested) ---
    $wt = Join-Path $WorktreeRoot "$Project`__$Role`__$Task"
    # GH #151: files a worker writes at its own worktree root and never
    # cleans up — a stale one here means a NEW worker inherits another
    # task's report/blocker/mailbox/heartbeat. worker.log is NOT in this list
    # (iteration 1 review, 2026-09-18): nothing writes it any more since the
    # Tee-Object launcher line was reverted (see step 6 below).
    $staleFiles = @('REPORT.md', 'BLOCKER.md', 'MAILBOX.md', 'HEARTBEAT')
    if (Test-Path $wt) {
        # GH #151: this path can be reused across tasks (same slug pattern).
        # If it still holds TRACKED, uncommitted changes, that's a previous
        # worker's real unfinished work -- refuse instead of silently force-
        # removing it. $staleFiles never count as dirty here even when
        # untracked: REPORT.md/BLOCKER.md are meant to be committed+pushed on
        # the WORKER's own branch (they ARE the hub's channel); HEARTBEAT/
        # MAILBOX.md are git-excluded (see info/exclude below) so `git status`
        # would show them as untracked anyway, never as a reason to refuse.
        if (Test-Path (Join-Path $wt '.git')) {
            $dirty = @(git -C $wt status --porcelain 2>$null |
                Where-Object { $_ -and -not $_.StartsWith('??') })
            if ($dirty.Count -gt 0) {
                Write-Output "SPAWN_REFUSED=dirty-worktree $wt"
                exit 1
            }
        }
        git -C $RepoPath worktree remove --force $wt 2>$null
        if (Test-Path $wt) { Remove-Item -Recurse -Force $wt }
    }
    git -C $RepoPath branch -D $Branch 2>$null
    if (-not (Test-Path $WorktreeRoot)) {
        New-Item -ItemType Directory -Path $WorktreeRoot -Force | Out-Null
    }
    git -C $RepoPath worktree add -b $Branch $wt "origin/$Base" 2>&1 | ForEach-Object { "$_" } | Select-Object -Last 3
    Assert-Git "worktree add"

    # GH #151 defense-in-depth: `worktree add` checks out whatever is
    # COMMITTED on $Base (a stale REPORT.md committed to main by mistake is
    # exactly how task-424077a4 inherited one) plus anything left over from
    # a prior occupant of this same path. Delete all four BEFORE TASK.md is
    # written, so a fresh worker never starts holding another task's
    # report/blocker/mailbox/heartbeat.
    foreach ($stale in $staleFiles) {
        $staleP = Join-Path $wt $stale
        if (Test-Path $staleP) { Remove-Item -Force $staleP }
    }

    # GH #150/#152 review (2026-09-18): HEARTBEAT and MAILBOX.md must NEVER be
    # committed. roles/_worker_remote.md tells the worker to `git add -A &&
    # git commit`; REPORT.md/BLOCKER.md are meant to be committed (they ARE
    # the hub's channel), but a HEARTBEAT touched before every tool call would
    # turn into a commit every time, and a committed MAILBOX.md would push the
    # hub's messages onto the worker's own branch and trip merge_task's touches
    # gate on every merge. `info/exclude` is per-CLONE (shared by every
    # worktree of $RepoPath, unlike .gitignore which lives in the tracked tree
    # itself) and is the right place for a machine-local exclusion that must
    # work for ANY project repo cloned on this box, not just this one.
    # `git -C $RepoPath rev-parse --git-path ...` returns a path RELATIVE TO
    # $RepoPath (its own -C target), not relative to this process's actual
    # working directory -- using it bare here resolved to
    # C:\Users\UsEr\.git\info\exclude (this ssh session's home dir) instead
    # of the repo's real .git\info\exclude, and Add-Content failed silently
    # under $ErrorActionPreference='Continue' (measured live on winbox
    # 2026-09-18: HEARTBEAT/MAILBOX.md still showed up in `git status`).
    # Resolve it against $RepoPath ourselves whenever it comes back relative.
    $excludeRel = git -C $RepoPath rev-parse --git-path info/exclude
    if ([System.IO.Path]::IsPathRooted($excludeRel)) {
        $excludePath = $excludeRel
    } else {
        $excludePath = Join-Path $RepoPath $excludeRel
    }
    $excludeLines = @()
    if (Test-Path $excludePath) { $excludeLines = @(Get-Content -Path $excludePath -Encoding ASCII) }
    $toAdd = @('HEARTBEAT', 'MAILBOX.md') | Where-Object { $excludeLines -notcontains $_ }
    if ($toAdd.Count -gt 0) {
        Add-Content -Path $excludePath -Value $toAdd -Encoding ASCII
    }

    # --- 3. TASK.md: from -TaskFile (scp'd ahead of this call) or stdin ---
    if ($TaskFile -and (Test-Path $TaskFile)) {
        # -Encoding UTF8 is load-bearing: Windows PowerShell 5.1's Get-Content
        # defaults to the ANSI codepage, so a UTF-8 brief comes back as mojibake
        # and the Set-Content below re-encodes that mojibake as UTF-8 — the
        # double-encoding that truncated the Thai dialogue in task-34350c98.
        $taskContent = Get-Content -Raw -Path $TaskFile -Encoding UTF8
    } else {
        [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
        $taskContent = [Console]::In.ReadToEnd()
    }
    Set-Content -Path (Join-Path $wt 'TASK.md') -Value $taskContent -NoNewline -Encoding UTF8

    # --- 4. WORKER.md: the remote-worker contract, read from the copy this
    # script's own deploy step scp'd alongside it ---
    $rolesDir = Join-Path (Split-Path $PSCommandPath -Parent) 'roles'
    $remoteContractPath = Join-Path $rolesDir '_worker_remote.md'
    $sharedDocPath = Join-Path $rolesDir '_worker_shared.md'
    $roleDocPath = Join-Path $rolesDir "$Role.md"
    $remoteContract = Get-Content -Raw -Path $remoteContractPath -Encoding UTF8
    Set-Content -Path (Join-Path $wt 'WORKER.md') -Value $remoteContract -NoNewline -Encoding UTF8

    # --- 5. System prompt: shared conventions + role doc + remote contract,
    # same composition runners/worker_init.py builds for a Mac-spawned DEV,
    # plus the remote contract appended (roles/_worker_remote.md). ---
    $sharedDoc = Get-Content -Raw -Path $sharedDocPath -Encoding UTF8
    $roleDoc = Get-Content -Raw -Path $roleDocPath -Encoding UTF8
    $systemPrompt = "$sharedDoc`n`n$roleDoc`n`n$remoteContract"

    # --- 6. Launch claude.exe --remote-control inside a Windows Terminal
    # tab (ADDENDUM 1). Prompt goes first (positional), --allowed-tools
    # (inside $ClaudeArgs, rendered on the Mac side via worker_tool_grants)
    # stays LAST with nothing after it — same rule runners/worker_init.py
    # documents: it is variadic and swallows every following argv element.
    #
    # The full arg list (including the system prompt, which can be
    # thousands of characters of quotes/newlines/non-ASCII) is written to a
    # JSON file and read back by a tiny generated launcher script, instead
    # of being inlined into the wt.exe command line — that line would go
    # through THREE layers of shell re-quoting (wt.exe -> `powershell
    # -Command` -> `& claude.exe`) and is not a safe place for that text. ---
    $claude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
    if (-not (Test-Path $claude)) { $claude = 'claude' }

    $claudeArgsSplit = @($ClaudeArgs -split '\s+' | Where-Object { $_ -ne '' })
    # Get-Content -Raw returns a string decorated with NoteProperties (PSPath,
    # ReadCount...). ConvertTo-Json serialises such a string as an OBJECT
    # {"value": "...", "PSPath": ...}, so claude.exe received the literal text
    # "@{value=# Task ..." as its first prompt (every Windows worker so far).
    # Cast both prompts to plain strings before serialising.
    $argList = @([string]$taskContent, '-n', [string]$SessionName, '--append-system-prompt', [string]$systemPrompt) + $claudeArgsSplit

    # $launchDir lives BESIDE this script (agents_root), never inside the
    # worktree -- a file dropped in the worktree gets swept up by the
    # worker's own `git add -A` and pushed onto its branch (it used to be
    # $wt\.launch, which had exactly that problem).
    $launchDir = Join-Path $PSScriptRoot ".launch-$Task"
    New-Item -ItemType Directory -Force -Path $launchDir | Out-Null
    $argsJsonPath = Join-Path $launchDir 'args.json'
    # UTF-8 WITHOUT a BOM: Set-Content -Encoding UTF8 emits one on PS5.1 and a
    # leading BOM makes ConvertFrom-Json fail on the read side below.
    [System.IO.File]::WriteAllText($argsJsonPath, ($argList | ConvertTo-Json -Depth 2),
                                   (New-Object System.Text.UTF8Encoding $false))

    # --- finish-<Task>.cmd/.ps1: how a worker ends ITSELF after pushing
    # (roles/_worker_remote.md runs %ORG_WORKER_FINISH% after `git push`).
    # The .ps1 re-resolves its own pid at call time with the same
    # Win32_Process + "CommandLine contains the task id" query step 7 below
    # runs -- launch.ps1 is generated here, before that pid is known (step 7
    # polls for it further down), so there is nothing to bake in yet. ---
    $finishPs1Path = Join-Path $launchDir "finish-$Task.ps1"
    $finishPs1Body = @"
`$procs = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" |
    Where-Object { `$_.CommandLine -and `$_.CommandLine -like "*$Task*" }
if (`$procs) {
    `$workerPid = (`$procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
    taskkill /PID `$workerPid /T /F
}
"@
    Set-Content -Path $finishPs1Path -Value $finishPs1Body -Encoding UTF8

    $finishCmdPath = Join-Path $launchDir "finish-$Task.cmd"
    $finishCmdBody = @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$finishPs1Path"
"@
    Set-Content -Path $finishCmdPath -Value $finishCmdBody -Encoding ASCII

    # GH #152 iteration 1 (REVERTED, CTO review 2026-09-18): piping claude.exe's
    # output through `| Tee-Object` makes stdout a non-TTY pipe. Claude Code is
    # an Ink TUI -- when stdout isn't a TTY it silently drops into --print mode
    # and immediately exits ("Input must be provided either through stdin or as
    # a prompt argument when using --print"), even though a prompt WAS given
    # positionally. Measured on the Mac 2026-09-18 with the same Ink code path:
    # `claude ... 2>&1 | tee tee.log` -> process gone within 12s. This killed
    # EVERY winbox spawn while the tee'd script was live. Never pipe this call;
    # #152's "what is it doing" need is served by tools/remote_worker_log.py
    # instead (reads Claude Code's own JSONL transcript, no launcher change).
    $launcherPath = Join-Path $launchDir 'launch.ps1'
    $launcherBody = @"
`$env:ORG_HOST = 'winbox'
`$env:ORG_WORKER_FINISH = '$finishCmdPath'
`$claudeExe = '$claude'
`$argArray = @(Get-Content -Raw -Path '$argsJsonPath' -Encoding UTF8 | ConvertFrom-Json)
& `$claudeExe @argArray
# Windows Terminal's default closeOnExit is "graceful": the tab stays open
# when its process exits NON-zero, which is exactly what a hub-side
# `taskkill /T /F` produces. Exit 0 here so the tab closes with the worker
# (CEO rule 2026-09-07: closing a worker closes its window).
exit 0
"@
    Set-Content -Path $launcherPath -Value $launcherBody -Encoding UTF8

    $logsDir = Join-Path (Split-Path $WorktreeRoot -Parent) 'logs'
    if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

    # No -NoExit (CTO correction 2026-09-07): the tab's lifetime must equal
    # claude.exe's lifetime — when the process ends (naturally, or via
    # `ssh winbox taskkill /PID <pid> /T /F` from the hub), this powershell
    # has nothing left to run and exits, and Windows Terminal closes the
    # tab with it. CEO rule: closing a worker closes its window too, never
    # just the process.
    # A process started from an SSH shell lives in Windows session 0 and never
    # reaches the logged-in desktop (session 1): wt.exe silently opened nothing
    # and claude.exe never appeared (2026-09-07, task-1289db7b). The only way in
    # from SSH is a one-shot scheduled task with an INTERACTIVE logon type run as
    # the desktop user. All quoting lives inside a wrapper .cmd so the task
    # action is one bare path (PowerShell -> schtasks quoting is unreliable).
    $SessionName = ($SessionName -replace "[^\x20-\x7E]", "-")   # .cmd is ASCII; keep the title readable
    $wtExe = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wt.exe'
    $wrapper = Join-Path $PSScriptRoot ("launch-" + $Task + ".cmd")   # beside this script, like win-cto.ps1
    @"
@echo off
start "" "$wtExe" -w 0 nt --title "$SessionName" --tabColor "#0078d4" -d "$wt" powershell -NoProfile -ExecutionPolicy Bypass -File "$launcherPath"
"@ | Set-Content -Path $wrapper -Encoding ASCII
    $stName = "mooniex-worker-" + $Task
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Unregister-ScheduledTask -TaskName $stName -Confirm:$false -ErrorAction SilentlyContinue
    $stAct = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$wrapper`""
    $stPri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
    $stSet = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $stName -Action $stAct -Principal $stPri -Settings $stSet -Force | Out-Null
    Start-ScheduledTask -TaskName $stName
    Write-Output "launched via interactive scheduled task $stName as $me"

    # --- 7. Capture the claude.exe pid. wt.exe hands the new-tab request to
    # the running Terminal instance and returns almost immediately — it is
    # not claude.exe's parent process, so there is no Start-Process handle
    # to read a pid from. Poll instead, matching on the task id, which
    # appears in claude's own command line (both the prompt text and -n). ---
    $workerPid = $null
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline -and -not $workerPid) {
        Start-Sleep -Milliseconds 500
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" |
            Where-Object { $_.CommandLine -and $_.CommandLine -like "*$Task*" }
        if ($procs) {
            $workerPid = ($procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
        }
    }
    if (-not $workerPid) {
        throw ("claude.exe did not appear within 60s for task $Task -- the " +
               "Windows Terminal tab may not have opened (wt.exe needs an " +
               "interactive desktop session; verify one exists over this " +
               "SSH connection type). See ADDENDUM 1 in the task brief.")
    }

    Unregister-ScheduledTask -TaskName $stName -Confirm:$false -ErrorAction SilentlyContinue
    # --- 8. .worker.json — what the Mac-side liveness poller reads back ---
    $startedAt = (Get-Date).ToUniversalTime().ToString('o')
    $workerInfo = @{ pid = $workerPid; started_at = $startedAt; host = 'winbox' } | ConvertTo-Json -Compress
    Set-Content -Path (Join-Path $wt '.worker.json') -Value $workerInfo -Encoding UTF8

    # LAST line of stdout, on purpose — the Mac side parses this with
    # lines[-1]. Nothing may print after this.
    Write-Output $workerPid
} catch {
    if ($stName) { Unregister-ScheduledTask -TaskName $stName -Confirm:$false -ErrorAction SilentlyContinue }
    Write-Error "spawn-worker.ps1 failed: $_"
    exit 1
}
