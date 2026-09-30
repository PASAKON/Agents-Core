param(
    [Parameter(Mandatory = $true)] [ValidateSet('A', 'B', 'C', 'D', 'E')] [string] $Scenario,
    [Parameter(Mandatory = $true)] [ValidateSet('auto', 'appactivate', 'uia')] [string] $Method,
    [int] $Count = 5,
    [string] $WakeScript,
    [string] $Csv,
    [ValidateSet('term', 'tab')] [string] $Focus = 'term',  # where keyboard focus sits inside WT before the run
    [ValidateSet('direct', 'task', 's4u')] [string] $Via = 'direct', # task = one-shot Interactive task; s4u = session-0 outer task that then does the same
    [string] $TitleArg = 'org-wake-test',
    [switch] $Contains
)
# Trial harness for the W3.5 spike. Touches ONLY: the orgwake WT window (own tabs
# org-wake-test / org-wake-decoy) and an own notepad opened on org-wake-notepad.txt.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text;
public class HW {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(int a, int b, bool f);
    [DllImport("kernel32.dll")] public static extern int GetCurrentThreadId();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    public static string Text(IntPtr h) { var sb = new StringBuilder(512); GetWindowTextW(h, sb, 512); return sb.ToString(); }
}
'@
$sp = Split-Path -Parent $MyInvocation.MyCommand.Path
$logT = Join-Path $sp 'test-tab.log'
$logD = Join-Path $sp 'decoy-tab.log'
$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]

function Find-Tab([string] $name) {
    $wins = $AE::RootElement.FindAll($TS::Children, (New-Object System.Windows.Automation.PropertyCondition ($AE::ClassNameProperty), 'CASCADIA_HOSTING_WINDOW_CLASS'))
    $cond = New-Object System.Windows.Automation.PropertyCondition ($AE::ControlTypeProperty), ([System.Windows.Automation.ControlType]::TabItem)
    foreach ($w in $wins) { foreach ($t in $w.FindAll($TS::Descendants, $cond)) { if ($t.Current.Name -ceq $name) { return @($w, $t) } } }
    return $null
}
function Select-Own([string] $name) {
    $f = Find-Tab $name
    if (-not $f) { throw "own tab $name not found" }
    $f[1].GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
    Start-Sleep -Milliseconds 300
    if ($Focus -eq 'term') {   # a person who has been typing in the tab: terminal has focus
        $tc = $f[0].FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition ($AE::ClassNameProperty), 'TermControl'))
        foreach ($c in $tc) { if (-not $c.Current.IsOffscreen) { $c.SetFocus(); break } }
    } else {                   # adverse: focus on the tab item
        $f[1].SetFocus()
    }
    Start-Sleep -Milliseconds 300
    [IntPtr]$f[0].Current.NativeWindowHandle
}
function Raise([IntPtr] $h) {   # setup only, on my own windows
    if ([HW]::IsIconic($h)) { [void][HW]::ShowWindow($h, 9) }
    $fg = [HW]::GetForegroundWindow(); $p = 0
    $ft = [HW]::GetWindowThreadProcessId($fg, [ref] $p); $me = [HW]::GetCurrentThreadId()
    $a = $false; if ($ft -ne 0 -and $ft -ne $me) { $a = [HW]::AttachThreadInput($me, $ft, $true) }
    [void][HW]::SetForegroundWindow($h)
    if ($a) { [void][HW]::AttachThreadInput($me, $ft, $false) }
    Start-Sleep -Milliseconds 400
}
# Put my own notepad really in front, or say it failed. SetForegroundWindow alone lies.
function Raise-Verified([string] $needle) {
    $wsh = New-Object -ComObject WScript.Shell
    for ($try = 1; $try -le 4; $try++) {
        $np = Get-Notepad
        if (-not $np) { return $false }
        switch ($try) {
            1 { Raise $np.MainWindowHandle }
            2 { [void]$wsh.AppActivate('org-wake-notepad'); Start-Sleep -Milliseconds 500 }
            3 { [void][HW]::ShowWindow($np.MainWindowHandle, 6); Start-Sleep -Milliseconds 300; [void][HW]::ShowWindow($np.MainWindowHandle, 9); Start-Sleep -Milliseconds 500 }
            4 { Start-Process notepad.exe -ArgumentList (Join-Path $sp 'org-wake-notepad.txt'); Start-Sleep -Milliseconds 1200 }
        }
        if ((Fg-Desc) -like "*$needle*") { return $true }
    }
    return $false
}
function Get-Notepad {
    Get-Process notepad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like 'org-wake-notepad*' } | Select-Object -First 1
}
function Notepad-Text {
    $np = Get-Notepad
    if (-not $np) { return '<no notepad>' }
    $w = $AE::FromHandle($np.MainWindowHandle)
    $docs = $w.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition ($AE::ControlTypeProperty), ([System.Windows.Automation.ControlType]::Document)))
    foreach ($d in $docs) { try { return $d.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern).DocumentRange.GetText(-1) } catch {} }
    foreach ($d in $w.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition ($AE::ControlTypeProperty), ([System.Windows.Automation.ControlType]::Edit)))) {
        try { return $d.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch {}
    }
    return '<unreadable>'
}
function Fg-Desc { $fg = [HW]::GetForegroundWindow(); $t = [HW]::Text($fg); if ($t.Length -gt 30) { $t = $t.Substring(0, 30) }; ($t -replace '[^\x20-\x7E]', '?') }

$needNotepad = $Scenario -in 'C', 'D'
if ($needNotepad -and -not (Get-Notepad)) {
    $f = Join-Path $sp 'org-wake-notepad.txt'
    if (-not (Test-Path $f)) { Set-Content -Path $f -Value '' -Encoding ASCII }
    Start-Process notepad.exe -ArgumentList $f
    for ($i = 0; $i -lt 30 -and -not (Get-Notepad); $i++) { Start-Sleep -Milliseconds 300 }
    if (-not (Get-Notepad)) { throw 'own notepad did not appear' }
}

$n = 0; $attempts = 0
while ($n -lt $Count -and $attempts -lt ($Count * 3)) {
    $attempts++
    $os = Get-CimInstance Win32_OperatingSystem; $freeMB = [int]($os.FreePhysicalMemory / 1024)
    if ($freeMB -lt 1024) { Write-Output "ABORT free RAM $freeMB MB < 1024"; break }
    # --- setup (an invalid setup is skipped, never counted)
    $tabWin = $null; $setupOk = $true
    switch ($Scenario) {
        'A' { $tabWin = Select-Own 'org-wake-test';  Raise $tabWin }
        'B' { $tabWin = Select-Own 'org-wake-decoy'; Raise $tabWin }
        'C' { $tabWin = Select-Own 'org-wake-test';  $setupOk = Raise-Verified 'org-wake-notepad' }
        'D' { $tabWin = Select-Own 'org-wake-decoy'; $setupOk = Raise-Verified 'org-wake-notepad' }
        'E' {
            $tabWin = Select-Own 'org-wake-test'
            for ($k = 0; $k -lt 3 -and -not [HW]::IsIconic($tabWin); $k++) { [void][HW]::ShowWindow($tabWin, 6); Start-Sleep -Milliseconds 700 }
            $setupOk = [HW]::IsIconic($tabWin)   # verified, or the trial is not counted
        }
    }
    if (-not $setupOk) { Write-Output "  (setup invalid: scenario $Scenario precondition not reached, fg=[$(Fg-Desc)] - trial not counted)"; continue }
    $n++
    $fgBefore = Fg-Desc
    $marker = "W-$Method-$Scenario-$n-" + (Get-Random -Maximum 9999)
    $npBefore = if ($needNotepad) { Notepad-Text } else { '' }
    $linesT = @(Get-Content $logT -ErrorAction SilentlyContinue).Count
    # --- run, as its own process (like a task would)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $runLog = Join-Path $sp 'wake-run.log'
    if ($Via -eq 'direct') {
        $wa = @('-Title', $TitleArg, '-Marker', $marker, '-Method', $Method, '-Log', $runLog); if ($Contains) { $wa += '-Contains' }
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $WakeScript @wa 2>&1 | Out-String
        $exit = $LASTEXITCODE
    } elseif ($Via -eq 's4u') {
        $tn = 'mooniex-wake-spike-s4u-' + (Get-Random -Maximum 99999)
        $resF = Join-Path $sp 'hop-result.txt'; Remove-Item $resF -ErrorAction SilentlyContinue
        $arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$(Join-Path $sp 'hop-outer.ps1')`" -WakeScript `"$WakeScript`" -Marker $marker -Method $Method -Log `"$runLog`" -Result `"$resF`""
        $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
        $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType S4U -RunLevel Limited
        $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
        Register-ScheduledTask -TaskName $tn -Action $act -Principal $pri -Settings $set -Force | Out-Null
        try {
            $startAt = Get-Date
            Start-ScheduledTask -TaskName $tn
            do { Start-Sleep -Milliseconds 400 } while (-not (Test-Path $resF) -and (Get-Date) -lt $startAt.AddSeconds(45))
        } finally { Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue }
        $exit = if (Test-Path $resF) { 0 } else { 99 }
        $out = (Get-Content $runLog -Tail 1) + " [" + $(if (Test-Path $resF) { (Get-Content $resF) } else { 'no outer result' }) + "]"
    } else {
        # the spawn-worker / node_dispatch pattern: register, start, wait, unregister
        $tn = 'mooniex-wake-spike-' + (Get-Random -Maximum 99999)
        $arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WakeScript`" -Title `"$TitleArg`" -Marker $marker -Method $Method -Log `"$runLog`"" + $(if ($Contains) { ' -Contains' } else { '' })
        $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
        $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
        $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
        Register-ScheduledTask -TaskName $tn -Action $act -Principal $pri -Settings $set -Force | Out-Null
        try {
            $startAt = Get-Date
            Start-ScheduledTask -TaskName $tn
            do {
                Start-Sleep -Milliseconds 300
                $info = Get-ScheduledTaskInfo -TaskName $tn; $st = [string](Get-ScheduledTask -TaskName $tn).State
                $finished = ($st -ne 'Running' -and $info.LastRunTime -ge $startAt.AddSeconds(-2))
            } while (-not $finished -and (Get-Date) -lt $startAt.AddSeconds(30))
            $exit = $info.LastTaskResult
        } finally { Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue }
        $out = (Get-Content $runLog -Tail 1) + " [via task $tn, task result $exit]"
    }
    $scriptMs = $sw.ElapsedMilliseconds
    # --- did it arrive (<= 30 s)?
    $got = $false; $secs = $null
    while ($sw.Elapsed.TotalSeconds -lt 30) {
        if ((Get-Content $logT -ErrorAction SilentlyContinue | Select-String -SimpleMatch "[$marker]")) { $got = $true; $secs = [math]::Round($sw.Elapsed.TotalSeconds, 2); break }
        if ($exit -ne 0) { Start-Sleep -Milliseconds 700; if (-not (Get-Content $logT | Select-String -SimpleMatch "[$marker]")) { break } }
        Start-Sleep -Milliseconds 100
    }
    $leakDecoy = [bool](Get-Content $logD -ErrorAction SilentlyContinue | Select-String -SimpleMatch $marker)
    $leakNp = $false; if ($needNotepad) { $leakNp = (Notepad-Text) -match 'W-' }
    $row = [pscustomobject]@{ scenario = $Scenario; via = $Via; focus = $Focus; method = $Method; contains = [bool]$Contains; n = $n; fg_before = $fgBefore; exit = $exit; script_ms = $scriptMs
        received = $got; secs_to_marker = $secs; leak_decoy = $leakDecoy; leak_notepad = $leakNp; free_mb = $freeMB
        detail = ($out.Trim() -replace '\s+', ' '); invalid_setup = 'False' }
    Write-Output ("{0}/{1}/{2} #{3} fg=[{4}] exit={5} script={6}ms recv={7} t={8}s leakD={9} leakN={10} :: {11}" -f $Scenario, $Focus, $Method, $n, $fgBefore, $exit, $scriptMs, $got, $secs, $leakDecoy, $leakNp, $row.detail)
    if ($Csv) { $row | Export-Csv -Path $Csv -Append -NoTypeInformation -Encoding ASCII }
    Start-Sleep -Milliseconds 500
}
