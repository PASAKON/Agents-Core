# WINBOX WORKER LAUNCHER -- Phase 1 (docs/design/multi-host-workers.md).
#
# Invoked by tools/delegate.py's _spawn_remote() over:
#   ssh winbox powershell -NoProfile -ExecutionPolicy Bypass -File spawn-worker.ps1 ...
#
# Clones/fetches the project, adds a worktree on a fresh task branch, writes
# TASK.md + WORKER.md, and launches `claude.exe` --remote-control inside a
# visible Windows Terminal tab (ADDENDUM 1, CTO 2026-09-07: Remote Control
# needs an interactive console session, so a fully detached Start-Process
# would never show up in the CEO's Claude app -- same reason win-cto.ps1
# runs the Windows CTO inside a wt.exe tab rather than detached). Prints the
# child pid as the LAST line of stdout so the Mac side can parse it with
# `lines[-1]`. Every other line this script prints is informational and
# must come BEFORE that one.
#
# PowerShell 5.1 syntax only (this box has no pwsh 7). Never prompts --
# every git/ssh call is forced non-interactive, so a bad credential or an
# unknown host key fails loudly instead of hanging the whole pipe.
#
# W3.3: tools/node_dispatch.py's spawn_worker verb runs this same file in place
# from the repo checkout when the hub IS this box (no ssh, no deploy copy), with
# -AgentsRoot <checkout>; see the param block.
#
# Deployed to the host's agents_root (e.g. C:\Users\UsEr\mooniex\spawn-worker.ps1) by
# scp as part of tools/delegate.py's automatic deploy check -- re-run that
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
    # AllowEmptyString: codex and agy have no claude-style flags, so
    # tools/delegate.py's _render_remote_runner_args returns '' for them -- and
    # a Mandatory [string] rejects '' at bind time, before the script runs a
    # single line. The first real agy spawn (task-22f3579a, 2026-09-22) died
    # here with "Cannot bind argument to parameter 'ClaudeArgs' because it is
    # an empty string". Static text tests could not see it; only a real spawn
    # could. Still Mandatory -- the hub must always pass the parameter, it just
    # may be empty.
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$ClaudeArgs,
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][string]$Effort,
    [Parameter(Mandatory = $true)][string]$SessionName,
    [string]$TaskFile = '',
    # task-adbc6f43: which CLI drives this worker. 'claude' is the default and
    # its entire launch path (below) is BYTE-IDENTICAL to before this param
    # existed -- every other step (worktree/git/clone/pid/teardown) is shared
    # by all three, only the launch line (step 6) and the pid-poll filter
    # (step 7) branch on this. ValidateSet is defense-in-depth: the hub
    # (tools/delegate.py's _validate_runner) already refuses an unknown
    # runner before ssh is ever called.
    [ValidateSet('claude', 'codex', 'agy')][string]$Runner = 'claude',
    [string]$TaskMetaB64 = '',
    [string]$RunnerModel = '',
    [string]$WorkDir = $env:WORK_DIR,
    # W3.3 (task-782936c0): the folder that holds roles\ and receives the
    # .launch-<task> dir + launch-<task>.cmd wrapper. Empty (the ssh deploy
    # path, unchanged) = this script's own folder, because the deploy step
    # copies the script and roles\ side by side. tools/node_dispatch.py's
    # spawn_worker runs THIS file out of the repo checkout, where the script sits
    # in windows\ and roles\ is one level up, so it passes the checkout root.
    [string]$AgentsRoot = ''
)

$ErrorActionPreference = 'Stop'
$env:GIT_TERMINAL_PROMPT = '0'
$agentsRootDir = if ($AgentsRoot) { $AgentsRoot } else { $PSScriptRoot }

# --- GitHub reachability: port 22 may be blocked from this box (measured
# 2026-09-07 -- `ssh -T git@github.com` hung with no ConnectTimeout). Probe
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
            # ($null -eq 0) is $false -- so every probe read as "unreachable"
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
    # from the idempotent branch -D) into a terminating error -- even under
    # 2>$null. That failed the first real winbox spawn on 2026-09-07. Git's
    # success/failure is its exit code, so check $LASTEXITCODE explicitly and
    # let stderr flow.
    $ErrorActionPreference = 'Continue'
    function Assert-Git([string]$what) { if ($LASTEXITCODE -ne 0) { throw "git $what failed (exit $LASTEXITCODE)" } }

    $githubRoute = Ensure-GithubSshRoute
    Write-Output "GITHUB_SSH_ROUTE=$githubRoute"

    # Non-interactive SSH for every git network op below -- an unknown host
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
    # cleans up -- a stale one here means a NEW worker inherits another
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

    # Sidecar (.org-task.json) and runner_model resolution
    $metaPath = Join-Path $wt '.org-task.json'
    if ($TaskMetaB64) {
        try {
            $metaBytes = [System.Convert]::FromBase64String($TaskMetaB64)
            [System.IO.File]::WriteAllBytes($metaPath, $metaBytes)
        } catch {}
    }

    if (-not $RunnerModel -and (Test-Path -LiteralPath $metaPath)) {
        try {
            $metaJsonStr = [System.IO.File]::ReadAllText($metaPath, [System.Text.Encoding]::UTF8)
            $metaObj = $metaJsonStr | ConvertFrom-Json
            if ($metaObj.runner_model) {
                $RunnerModel = [string]$metaObj.runner_model
            }
        } catch {}
    }

    if ($RunnerModel) {
        if ($RunnerModel -notmatch '^[A-Za-z0-9._:-]{1,64}$') {
            Write-Error "spawn-worker.ps1: invalid runner_model '$RunnerModel' (must match ^[A-Za-z0-9._:-]{1,64}$)"
            exit 2
        }
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
    # W0.6: plus every name a codex/agy run must never commit (note below).
    $toAdd = @('HEARTBEAT', 'MAILBOX.md', '.worker.pid', '.worker.json', '/TASK.md',
               '/.org-task.json', '/.org-worker.mcp.json', '/CTO-FEEDBACK.md', '/*.log') |
        Where-Object { $excludeLines -notcontains $_ }
    if ($toAdd.Count -gt 0) {
        Add-Content -Path $excludePath -Value $toAdd -Encoding ASCII
    }
    # W0.6 note: the codex/agy launcher below runs `git add -A` after the CLI
    # exits, so the launcher's own .worker.pid/.worker.json, the CTO's scratch
    # file and logs are excluded above. Root files are anchored with '/' -- an
    # unanchored REPORT.md would also hide docs/reports/<task>/REPORT.md. Root
    # REPORT.md/BLOCKER.md are NOT listed: info/exclude is shared by every
    # worktree of this clone and claude workers commit those two through
    # `git add -A`; the codex/agy launcher resets them itself instead (see
    # New-ReportStepBody below).

    # --- 3. TASK.md: from -TaskFile (scp'd ahead of this call) or stdin ---
    if ($TaskFile -and (Test-Path $TaskFile)) {
        # -Encoding UTF8 is load-bearing: Windows PowerShell 5.1's Get-Content
        # defaults to the ANSI codepage, so a UTF-8 brief comes back as mojibake
        # and the Set-Content below re-encodes that mojibake as UTF-8 -- the
        # double-encoding that truncated the Thai dialogue in task-34350c98.
        $taskContent = Get-Content -Raw -Path $TaskFile -Encoding UTF8
    } else {
        [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
        $taskContent = [Console]::In.ReadToEnd()
    }
    Set-Content -Path (Join-Path $wt 'TASK.md') -Value $taskContent -NoNewline -Encoding UTF8

    # --- 4. WORKER.md: the remote-worker contract, read from the copy this
    # script's own deploy step scp'd alongside it ---
    $rolesDir = Join-Path $agentsRootDir 'roles'
    $remoteContractPath = Join-Path $rolesDir '_worker_remote.md'
    $sharedDocPath = Join-Path $rolesDir '_worker_shared.md'
    $roleDocPath = Join-Path $rolesDir "$Role.md"
    $remoteContract = Get-Content -Raw -Path $remoteContractPath -Encoding UTF8
    $contracts = $remoteContract -split '<!-- NONCLAUDE CONTRACT -->\r?\n', 2
    $remoteContract = if ($Runner -ne 'claude') { $contracts[1] } else { $contracts[0] }
    Set-Content -Path (Join-Path $wt 'WORKER.md') -Value $remoteContract -NoNewline -Encoding UTF8

    # --- 5. System prompt: shared conventions + role doc + remote contract,
    # same composition runners/worker_init.py builds for a Mac-spawned DEV,
    # plus the remote contract appended (roles/_worker_remote.md). ---
    $sharedDoc = Get-Content -Raw -Path $sharedDocPath -Encoding UTF8
    $roleDoc = Get-Content -Raw -Path $roleDocPath -Encoding UTF8
    $systemPrompt = "$sharedDoc`n`n$roleDoc`n`n$remoteContract"
    if ($Runner -ne 'claude') {
        $remoteContract = $remoteContract.Replace('<task-id>', $Task)
        $systemPrompt = $remoteContract
        $taskContent = ($taskContent -split '(?m)^1\. Read your role doc \(already in your system prompt\)\.\r?$', 2)[0]
        $taskContent = $taskContent -replace 'mcp__org__\w+', 'unavailable org tool (use report file)'
    }

    # Literal runtime body shared by both external runners. finally stops and
    # waits for the heartbeat job even if invocation throws or returns nonzero.
    $heartbeatStart = @'
$heartbeatJob = Start-Job -ArgumentList $heartbeatPath, $PID -ScriptBlock {
    param($path, $launcherPid)
    while (Get-Process -Id $launcherPid -ErrorAction SilentlyContinue) {
        [System.IO.File]::WriteAllText($path, [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"))
        Start-Sleep -Seconds 60
    }
}
try {
'@
    $heartbeatStop = @'
} finally {
    Stop-Job -Job $heartbeatJob -ErrorAction SilentlyContinue
    Wait-Job -Job $heartbeatJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job -Job $heartbeatJob -Force -ErrorAction SilentlyContinue
}
'@
    $workDirLiteral = ([string]$WorkDir).Replace("'", "''")
    $heartbeatPathLiteral = (Join-Path $wt 'HEARTBEAT').Replace("'", "''")

    # --- 6. Launch the worker CLI via a one-shot interactive scheduled task
    # (session-0 rule: SSH lands in Windows session 0, never the logged-in
    # desktop/session 1 that wt.exe/claude.exe/codex/agy all need -- see
    # docs/ops/agent-runners.md sec.3). task-adbc6f43: -Runner dispatches
    # binary + argv here; 'claude' keeps its ORIGINAL Windows Terminal tab
    # launch byte-identical below. codex/agy are headless CLIs (no TUI, no
    # window needed) so they run straight inside the scheduled task via a
    # generated launcher.ps1 -- the same session-1 mechanism
    # windows/s1probe.ps1 proved for codex (2026-09-20), reused rather than
    # reinvented, not the wt.exe tab claude needs.
    #
    # $launchDir lives BESIDE this script (agents_root), never inside the
    # worktree -- a file dropped in the worktree gets swept up by the
    # worker's own `git add -A` and pushed onto its branch (it used to be
    # $wt\.launch, which had exactly that problem).
    $launchDir = Join-Path $agentsRootDir ".launch-$Task"
    New-Item -ItemType Directory -Force -Path $launchDir | Out-Null
    $logsDir = Join-Path (Split-Path $WorktreeRoot -Parent) 'logs'
    if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }
    $argsJsonPath = Join-Path $launchDir 'args.json'
    $finishPs1Path = Join-Path $launchDir "finish-$Task.ps1"
    $finishCmdPath = Join-Path $launchDir "finish-$Task.cmd"
    $launcherPath = Join-Path $launchDir 'launch.ps1'
    $wrapper = Join-Path $agentsRootDir ("launch-" + $Task + ".cmd")   # beside this script, like win-cto.ps1
    $stName = "mooniex-worker-" + $Task
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Unregister-ScheduledTask -TaskName $stName -Confirm:$false -ErrorAction SilentlyContinue

    # W0.6 (runner-routing contract): the tail every codex/agy launch.ps1 ends
    # with, after the CLI has exited and `$cliExit is set. Returns the runtime
    # code as text: (1) make sure docs/reports/<task>/REPORT.md exists with the
    # '# REPORT <task>' first line -- kept when the worker wrote it, else a root
    # REPORT.md is moved there (header prepended if missing), else it is built
    # from the runner's final message; (2) `git add -A`, then `git reset` the
    # never-commit files as a second guard behind info/exclude; (3) commit
    # (the report alone is a commit) and push. $finalMsg = codex's -o file,
    # $logTail = agy's events log; the other is ''. `$x below is runtime,
    # $x is filled in now. Files are written as UTF-8 WITHOUT a BOM: Set-Content
    # -Encoding UTF8 emits one on PS5.1 and branch_poller would then read
    # '<BOM># REPORT task-...' as a header mismatch.
    function New-ReportStepBody([string]$finalMsg, [string]$logTail) {
        return @"
`$noBom = New-Object System.Text.UTF8Encoding `$false
`$hdr = '# REPORT $Task'
`$nl = [string][char]10
`$reportDir = Join-Path '$wt' 'docs\reports\$Task'
`$reportPath = Join-Path `$reportDir 'REPORT.md'
`$rootReport = Join-Path '$wt' 'REPORT.md'
`$finalMsgPath = '$finalMsg'
`$logTailPath = '$logTail'
New-Item -ItemType Directory -Force -Path `$reportDir | Out-Null
function Test-ReportHdr([string]`$p) {
    if (-not (Test-Path -LiteralPath `$p)) { return `$false }
    `$txt = [System.IO.File]::ReadAllText(`$p, `$noBom)
    if (-not `$txt.Trim()) { return `$false }
    return ((`$txt -split '\r?\n')[0].TrimEnd() -eq `$hdr)
}
function Test-NonEmpty([string]`$p) {
    return ((Test-Path -LiteralPath `$p) -and ((Get-Item -LiteralPath `$p).Length -gt 0))
}
function Add-ReportHdr([string]`$p) {
    `$body = [System.IO.File]::ReadAllText(`$p, `$noBom)
    [System.IO.File]::WriteAllText(`$p, (`$hdr + `$nl + `$nl + `$body), `$noBom)
}
if (Test-ReportHdr `$reportPath) {
    # the worker already wrote its report where it belongs
}
elseif (Test-NonEmpty `$rootReport) {
    git -C '$wt' ls-files --error-unmatch REPORT.md *> `$null
    if (`$LASTEXITCODE -eq 0) { git -C '$wt' mv -f REPORT.md 'docs/reports/$Task/REPORT.md' }
    else { Move-Item -LiteralPath `$rootReport -Destination `$reportPath -Force }
    if ((Test-NonEmpty `$reportPath) -and -not (Test-ReportHdr `$reportPath)) { Add-ReportHdr `$reportPath }
}
elseif (Test-NonEmpty `$reportPath) {
    Add-ReportHdr `$reportPath
}
if (-not (Test-NonEmpty `$reportPath)) {
    `$msg = ''
    if (`$finalMsgPath -and (Test-Path -LiteralPath `$finalMsgPath)) {
        `$msg = [System.IO.File]::ReadAllText(`$finalMsgPath, `$noBom)
    }
    elseif (`$logTailPath -and (Test-Path -LiteralPath `$logTailPath)) {
        `$msg = (@(Get-Content -LiteralPath `$logTailPath -Tail 200) -join `$nl)
    }
    if (-not `$msg -or -not `$msg.Trim()) { `$msg = 'no final message; exit=' + `$cliExit }
    `$text = `$hdr + `$nl + `$nl + 'Runner: $Runner' + `$nl + 'Exit code: ' + `$cliExit + `$nl + `$nl + `$msg + `$nl
    [System.IO.File]::WriteAllText(`$reportPath, `$text, `$noBom)
}

git -C '$wt' add -A
git -C '$wt' reset -q -- .worker.pid .worker.json TASK.md .org-task.json .org-worker.mcp.json CTO-FEEDBACK.md REPORT.md BLOCKER.md HEARTBEAT MAILBOX.md ':(glob)*.log'

`$mediaExts = @('png','jpg','jpeg','gif','webp','heic','mp4','mov','webm','mkv','avi','mp3','wav','m4a','aac','flac','ogg')
`$stagedFiles = @(git -C '$wt' diff --cached --name-only)
`$mediaBlockers = @()
`$mediaKept = @()

`$allowFile = Join-Path `$reportDir '.media_allow_all'
`$allowLargeFile = Join-Path `$reportDir '.media_allow_large'
`$hasAllow = `$false
`$hasAllowLarge = `$false
Remove-Item -LiteralPath `$allowFile -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath `$allowLargeFile -Force -ErrorAction SilentlyContinue

`$allowRaw = @(git -C '$wt' show "origin/$Base:.media-allow" 2>`$null)
if (`$LASTEXITCODE -eq 0 -and `$allowRaw.Count -gt 0) {
    `$allPats = @()
    `$largePats = @()
    foreach (`$rawLine in `$allowRaw) {
        `$line = `$rawLine.Trim().Replace('\', '/')
        if (-not `$line -or `$line.StartsWith('#')) { continue }
        if (`$line -match '\s+!large$') {
            `$pat = (`$line -replace '\s+!large$', '').Trim()
            `$allPats += `$pat
            `$largePats += `$pat
        } else {
            `$allPats += `$line
        }
    }
    if (`$allPats.Count -gt 0) {
        [System.IO.File]::WriteAllLines(`$allowFile, `$allPats, `$noBom)
        `$hasAllow = `$true
    }
    if (`$largePats.Count -gt 0) {
        [System.IO.File]::WriteAllLines(`$allowLargeFile, `$largePats, `$noBom)
        `$hasAllowLarge = `$true
    }
}

foreach (`$f in `$stagedFiles) {
    if (-not `$f) { continue }
    `$fullPath = Join-Path '$wt' `$f
    if (-not (Test-Path -LiteralPath `$fullPath)) { continue }
    `$ext = [System.IO.Path]::GetExtension(`$f).TrimStart('.').ToLowerInvariant()
    `$fi = New-Object System.IO.FileInfo(`$fullPath)
    `$sz = `$fi.Length
    `$isMedia = `$mediaExts -contains `$ext
    `$isLargeBinary = `$false
    if (-not `$isMedia -and (`$sz -gt 1048576)) {
        `$numstat = git -C '$wt' diff --cached --numstat -- `$f
        if (`$numstat -and (`$numstat.StartsWith("-`t-") -or `$numstat.StartsWith("- -") -or `$numstat.StartsWith("-"))) {
            `$isLargeBinary = `$true
        }
    }
    if (`$isMedia -or `$isLargeBinary) {
        `$isAllowed = `$false
        if (`$hasAllow) {
            `$matched = git -C '$wt' ls-files --cached --ignored "--exclude-from=`$allowFile" -- `$f 2>`$null
            if (`$matched) {
                `$isAllowed = `$true
            }
        }
        if (`$isAllowed -and (`$sz -gt 1048576)) {
            `$hasLargeMatch = `$false
            if (`$hasAllowLarge) {
                `$matchedLarge = git -C '$wt' ls-files --cached --ignored "--exclude-from=`$allowLargeFile" -- `$f 2>`$null
                if (`$matchedLarge) {
                    `$hasLargeMatch = `$true
                }
            }
            if (-not `$hasLargeMatch) {
                `$isAllowed = `$false
            }
        }
        if (`$isAllowed) {
            `$mediaKept += `$f
        } else {
            git -C '$wt' reset -q -- `$f
            `$hsz = if (`$sz -ge 1048576) {
                "{0:0.0} MB" -f (`$sz / 1048576.0)
            } elseif (`$sz -ge 1024) {
                "{0:0.0} KB" -f (`$sz / 1024.0)
            } else {
                "`$sz B"
            }
            `$mediaBlockers += "media not committed: `$f (`$hsz) -- upload per CXO_Rules_GDrive_Filing and put the link here"
        }
    }
}

Remove-Item -LiteralPath `$allowFile -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath `$allowLargeFile -Force -ErrorAction SilentlyContinue

if (`$mediaBlockers.Count -gt 0) {
    `$repText = [System.IO.File]::ReadAllText(`$reportPath, `$noBom)
    if (`$repText -match '(?m)^## Blockers') {
        `$lines = `$repText -split '\r?\n'
        `$newLines = @()
        foreach (`$ln in `$lines) {
            `$newLines += `$ln
            if (`$ln -match '^## Blockers') {
                foreach (`$mb in `$mediaBlockers) {
                    `$newLines += "- `$mb"
                }
            }
        }
        `$repText = `$newLines -join `$nl
    } else {
        `$repText = `$repText.TrimEnd() + `$nl + `$nl + '## Blockers' + `$nl
        foreach (`$mb in `$mediaBlockers) {
            `$repText += "- `$mb" + `$nl
        }
    }
    [System.IO.File]::WriteAllText(`$reportPath, `$repText, `$noBom)
    git -C '$wt' add 'docs/reports/$Task/REPORT.md'
}

if (`$mediaKept.Count -gt 0) {
    `$repText = [System.IO.File]::ReadAllText(`$reportPath, `$noBom)
    `$keptLines = (`$mediaKept | ForEach-Object { "media kept: `$_" }) -join `$nl
    `$repText = `$repText.TrimEnd() + `$nl + `$nl + `$keptLines + `$nl
    [System.IO.File]::WriteAllText(`$reportPath, `$repText, `$noBom)
    git -C '$wt' add 'docs/reports/$Task/REPORT.md'
}

git -C '$wt' diff --cached --quiet
if (`$LASTEXITCODE -ne 0) {
    if (`$mediaKept.Count -gt 0) {
        `$keptBody = (`$mediaKept | ForEach-Object { "media kept: `$_" }) -join `$nl
        git -C '$wt' commit -q -m "${Runner}: task $Task" -m `$keptBody
    } else {
        git -C '$wt' commit -q -m "${Runner}: task $Task"
    }
}
git -C '$wt' push -q origin $Branch
"@
    }

    if ($Runner -eq 'claude') {
        # Prompt goes first (positional), --allowed-tools (inside
        # $ClaudeArgs, rendered on the Mac side via worker_tool_grants)
        # stays LAST with nothing after it -- same rule runners/worker_init.py
        # documents: it is variadic and swallows every following argv element.
        #
        # The full arg list (including the system prompt, which can be
        # thousands of characters of quotes/newlines/non-ASCII) is written to a
        # JSON file and read back by a tiny generated launcher script, instead
        # of being inlined into the wt.exe command line -- that line would go
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
        $finishPs1Body = @"
`$procs = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" |
    Where-Object { `$_.CommandLine -and `$_.CommandLine -like "*$Task*" }
if (`$procs) {
    `$workerPid = (`$procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
    taskkill /PID `$workerPid /T /F
}
"@
        Set-Content -Path $finishPs1Path -Value $finishPs1Body -Encoding UTF8

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

        # No -NoExit (CTO correction 2026-09-07): the tab's lifetime must equal
        # claude.exe's lifetime -- when the process ends (naturally, or via
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
        @"
@echo off
start "" "$wtExe" -w 0 nt --title "$SessionName" --tabColor "#0078d4" -d "$wt" powershell -NoProfile -ExecutionPolicy Bypass -File "$launcherPath"
"@ | Set-Content -Path $wrapper -Encoding ASCII
    }
    elseif ($Runner -eq 'codex') {
        # codex exec [PROMPT] -C <dir> -s workspace-write --skip-git-repo-check
        # --json -o <file> (docs/ops/agent-runners.md sec.1). No --model/
        # --effort/--allowed-tools equivalent exists for codex, so none are
        # invented here ($ClaudeArgs is empty for this runner --
        # tools/delegate.py's _render_remote_runner_args). codex also has no
        # --append-system-prompt flag, so the remote worker contract is
        # folded into the one prompt argument it does take instead of being
        # silently dropped.
        $codexExe = Join-Path $env:APPDATA 'npm\codex.cmd'
        if (-not (Test-Path $codexExe)) { $codexExe = 'codex' }
        $codexPrompt = "$taskContent`n`n$remoteContract"
        $codexFinalMsg = Join-Path $launchDir 'codex-final.txt'
        $codexJsonLog = Join-Path $launchDir 'codex-events.jsonl'
        $argList = @('exec', [string]$codexPrompt)
        if ($RunnerModel) {
            $argList += @('-m', [string]$RunnerModel)
        }
        # No writable root under .git (same as spawn-worker-remote.sh): codex's Linux sandbox
        # refuses to start with one (task-2f1a8586 probe); the commit step after codex exits
        # commits and pushes the worker's changes.
        if ($WorkDir) { $argList += @('--add-dir', [string]$WorkDir) }
        $argList += @('-C', [string]$wt, '-s', 'workspace-write',
                      '--skip-git-repo-check', '--json', '-o', [string]$codexFinalMsg)
        [System.IO.File]::WriteAllText($argsJsonPath, ($argList | ConvertTo-Json -Depth 2),
                                       (New-Object System.Text.UTF8Encoding $false))

        $finishPs1Body = @"
`$procs = Get-CimInstance Win32_Process -Filter "Name = 'node.exe' OR Name = 'codex.exe'" |
    Where-Object { `$_.CommandLine -and `$_.CommandLine -like "*$Task*" }
if (`$procs) {
    `$workerPid = (`$procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
    taskkill /PID `$workerPid /T /F
}
"@
        Set-Content -Path $finishPs1Path -Value $finishPs1Body -Encoding UTF8
        $finishCmdBody = @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$finishPs1Path"
"@
        Set-Content -Path $finishCmdPath -Value $finishCmdBody -Encoding ASCII

        # Never gate on this process's own exit code (docs/ops/agent-runners.md
        # sec.4: codex exits 0 after writing nothing) -- $codexJsonLog is the
        # artefact lib/artefact_gate.py actually reads (turn.completed /
        # turn.failed events). The EXITCODE line is diagnostic only, same
        # convention windows/s1probe.ps1 already uses.
        #
        # W0.6: after codex exits, THE HUB (this launcher, not codex) puts the
        # report at docs/reports/<task>/REPORT.md and commits + pushes -- the
        # codex-final.txt message becomes the report when codex wrote none.
        # A stale message from an earlier launch of this task is removed first.
        $reportStepBody = New-ReportStepBody $codexFinalMsg ''
        $launcherBody = @"
`$env:ORG_HOST = 'winbox'
`$env:ORG_WORKER_FINISH = '$finishCmdPath'
`$exe = '$codexExe'
`$argArray = @(Get-Content -Raw -Path '$argsJsonPath' -Encoding UTF8 | ConvertFrom-Json)
Remove-Item -LiteralPath '$codexFinalMsg' -Force -ErrorAction SilentlyContinue
`$env:WORK_DIR = '$workDirLiteral'
`$heartbeatPath = '$heartbeatPathLiteral'
$heartbeatStart
& `$exe @argArray *> '$codexJsonLog'
`$cliExit = `$LASTEXITCODE
$heartbeatStop
"EXITCODE=`$cliExit" | Add-Content -Path '$codexJsonLog'

$reportStepBody
exit 0
"@
        Set-Content -Path $launcherPath -Value $launcherBody -Encoding UTF8
        @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$launcherPath"
"@ | Set-Content -Path $wrapper -Encoding ASCII
    }
    else {
        # agy -p "<prompt>" --mode accept-edits --add-dir <dir>
        # (docs/ops/agent-runners.md sec.1/sec.6, sec.6b measured 2026-09-22) -- headless,
        # no TTY needed, never --dangerously-skip-permissions (Hard Rule).
        #
        # sec.6b, THE CONTRACT: agy in print mode cannot run ANY shell command --
        # a RunCommand step is soft-denied, and the denial is not partial, it
        # ABANDONS THE WHOLE TURN (asked to fix a bug AND `git commit`, it
        # committed nothing AND left the file unedited). The Claude contract
        # must never reach AGY (it instructs
        # `git add -A && git commit && git push`) or any part of $taskContent
        # that asks for a commit/test/submit_report -- that would silently
        # abandon the file edits too, not just the git step. Widening agy's
        # permissions to allow git was tried and is a dead end: a project-
        # scoped permission grant is discarded one line after being parsed
        # (sec.6b's own measured log line), and --dangerously-skip-permissions
        # stays banned regardless. So: agy edits ONLY; THE HUB (this script,
        # not agy) commits, pushes, and lets the artefact gate judge --
        # "external runners push agent/<runner>-<task> only" is enforced
        # properly this way (the hub does the pushing) rather than trusting
        # agy not to, which it structurally cannot even attempt anyway.
        $agyExe = Join-Path $env:LOCALAPPDATA 'agy\bin\agy.exe'
        if (-not (Test-Path $agyExe)) { $agyExe = 'agy' }
        $agyPrompt = @"
You are an EDIT-ONLY coding agent. Use ONLY your file-editing tool to make
changes. Do NOT run any shell command, and do NOT invoke git, a test
runner, or any other tool -- a single shell step abandons this entire turn,
including every file edit you planned alongside it. Ignore every
instruction below that tells you to commit, push, run tests, or submit a
report through a tool: a separate process (not you) does all of that after
you finish editing.

$remoteContract

---

$taskContent
"@
        $agyLog = Join-Path $launchDir 'agy-events.log'
        $agyModel = if ($RunnerModel) { $RunnerModel } else { 'gemini-3.8-flash-high' }
        $argList = @('-p', [string]$agyPrompt, '--model', [string]$agyModel, '--mode', 'accept-edits', '--add-dir', [string]$wt)
        [System.IO.File]::WriteAllText($argsJsonPath, ($argList | ConvertTo-Json -Depth 2),
                                       (New-Object System.Text.UTF8Encoding $false))

        # agy is honest about failure (non-zero exit + AGY_ERROR JSON on
        # stderr, docs/ops/agent-runners.md sec.6) but gets the SAME artefact
        # gate as codex regardless -- no runner is trusted on its own word.
        # There is no live agy.exe left to kill by the time a worker might
        # want to self-terminate (it never runs long enough to need it, and
        # it cannot call %ORG_WORKER_FINISH% itself -- that would be a shell
        # command), but the finish script is still generated for shape
        # parity with the other two runners and as a harmless safety net.
        $finishPs1Body = @"
`$procs = Get-CimInstance Win32_Process -Filter "Name = 'agy.exe'" |
    Where-Object { `$_.CommandLine -and `$_.CommandLine -like "*$Task*" }
if (`$procs) {
    `$workerPid = (`$procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
    taskkill /PID `$workerPid /T /F
}
"@
        Set-Content -Path $finishPs1Path -Value $finishPs1Body -Encoding UTF8
        $finishCmdBody = @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$finishPs1Path"
"@
        Set-Content -Path $finishCmdPath -Value $finishCmdBody -Encoding ASCII

        # sec.6b: THE HUB commits and pushes here, in this generated launcher,
        # immediately after agy's own process exits -- agy itself never runs
        # git. W0.6: the hub, not agy, also guarantees the report exists at
        # docs/reports/<task>/REPORT.md with the header branch_poller
        # requires -- agy is only ASKED for a REPORT.md (optional, best-effort,
        # a root REPORT.md is accepted and moved), never relied on to get it
        # right; with none written the report is built from the tail of
        # agy-events.log. `$x inside the body below is evaluated by THIS
        # LAUNCHER at ITS OWN runtime (backtick-escaped so this outer script
        # does not evaluate it now); $wt/$Task/$Branch are known-now values.
        $reportStepBody = New-ReportStepBody '' $agyLog
        $launcherBody = @"
`$env:ORG_HOST = 'winbox'
`$env:ORG_WORKER_FINISH = '$finishCmdPath'
`$exe = '$agyExe'
`$argArray = @(Get-Content -Raw -Path '$argsJsonPath' -Encoding UTF8 | ConvertFrom-Json)
# PowerShell has no '<' input-redirect operator (that's cmd.exe syntax) --
# piping `$null` in is the equivalent of the proven `< /dev/null`
# (docs/ops/agent-runners.md sec.6) that keeps agy from blocking on stdin.
`$env:WORK_DIR = '$workDirLiteral'
`$heartbeatPath = '$heartbeatPathLiteral'
$heartbeatStart
`$null | & `$exe @argArray *> '$agyLog'
`$cliExit = `$LASTEXITCODE
$heartbeatStop
"EXITCODE=`$cliExit" | Add-Content -Path '$agyLog'

$reportStepBody
exit 0
"@
        Set-Content -Path $launcherPath -Value $launcherBody -Encoding UTF8
        @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$launcherPath"
"@ | Set-Content -Path $wrapper -Encoding ASCII
    }

    $stAct = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$wrapper`""
    $stPri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
    $stSet = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $stName -Action $stAct -Principal $stPri -Settings $stSet -Force | Out-Null
    Start-ScheduledTask -TaskName $stName
    Write-Output "launched via interactive scheduled task $stName as $me"

    # --- 7. Capture the worker pid. wt.exe (claude only) hands the new-tab
    # request to the running Terminal instance and returns almost
    # immediately, and codex/agy run straight inside the scheduled task
    # itself -- neither is this process's own child, so there is no
    # Start-Process handle to read a pid from either way. Poll instead,
    # matching on the task id, which appears in every runner's own command
    # line one way or another (claude: prompt text + -n; codex/agy: the
    # -C/--add-dir worktree path, itself named "$Project__$Role__$Task"). ---
    $procFilter = @{
        claude = "Name = 'claude.exe'"
        codex  = "Name = 'node.exe' OR Name = 'codex.exe'"
        agy    = "Name = 'agy.exe'"
    }[$Runner]
    $workerPid = $null
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline -and -not $workerPid) {
        Start-Sleep -Milliseconds 500
        $procs = Get-CimInstance Win32_Process -Filter $procFilter |
            Where-Object { $_.CommandLine -and $_.CommandLine -like "*$Task*" }
        if ($procs) {
            $workerPid = ($procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId
        }
    }
    if (-not $workerPid) {
        throw ("$Runner did not appear within 60s for task $Task -- the " +
               "interactive scheduled task may not have started (needs an " +
               "interactive desktop session; verify one exists over this " +
               "SSH connection type). See ADDENDUM 1 in the task brief.")
    }

    Unregister-ScheduledTask -TaskName $stName -Confirm:$false -ErrorAction SilentlyContinue
    # --- 8. .worker.json -- what the Mac-side liveness poller reads back ---
    $startedAt = (Get-Date).ToUniversalTime().ToString('o')
    $workerInfo = @{ pid = $workerPid; started_at = $startedAt; host = 'winbox' } | ConvertTo-Json -Compress
    Set-Content -Path (Join-Path $wt '.worker.json') -Value $workerInfo -Encoding UTF8

    # LAST line of stdout, on purpose -- the Mac side parses this with
    # lines[-1]. Nothing may print after this.
    Write-Output $workerPid
} catch {
    if ($stName) { Unregister-ScheduledTask -TaskName $stName -Confirm:$false -ErrorAction SilentlyContinue }
    Write-Error "spawn-worker.ps1 failed: $_"
    exit 1
}
