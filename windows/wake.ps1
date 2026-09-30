# wake.ps1 - type a marker line + Enter into ONE Windows Terminal tab, found by
# its exact title. W3.5 spike (docs/design/org-mesh.md, C4 "wakes the pane").
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\wake.ps1 `
#       -Title "org-wake-test" -Marker "[New message from CTO]"
#
# ASCII only, like the other windows\*.ps1 (a non-ASCII byte in a script saved
# without a BOM is read as ANSI by Windows PowerShell 5.1 and fails to parse).
#
# MUST run in the desktop session (session 1 in the plan, whatever id the
# console session has). ssh lands in session 0, which has no desktop: there
# this script exits 4 and types nothing. The way in from ssh is a task that
# runs in the console session - see windows\register-org-tasks.ps1.
#
# THE ONE RULE. Keys typed into the wrong window on a desktop a person is
# using cannot be taken back. So immediately before every send, this script
# reads the foreground window (GetForegroundWindow + GetWindowText + class)
# and sends NOTHING unless it is the exact Windows Terminal window found for
# -Title. Any doubt -> exit 3, no key sent.
#
# How the tab is reached, in order (-Method auto keeps the first that passes):
#   appactivate  the WT window whose title is exactly -Title (Windows
#                Terminal shows the SELECTED tab's title as the window
#                title) is raised with WScript.Shell AppActivate, then
#                SetForegroundWindow / AttachThreadInput / SwitchToThisWindow.
#                Works only when the target is already the selected tab.
#   uia          System.Windows.Automation finds the TabItem named exactly
#                -Title, SelectionItemPattern.Select()s it, then the same
#                raise. Reaches a tab that is not selected.
# No synthetic ALT key is used to win the foreground: that is itself a key
# sent to whatever window is in front, before any guard could run.
#
# Exit codes:
#   0  keys sent to the verified target
#   2  no window/tab with exactly that title, or more than one
#   3  guard refused: the target was not the foreground window; NOTHING sent
#      (or, rarely, the marker was typed and the guard failed before Enter -
#      the message then says "Enter withheld")
#   4  no usable desktop (session 0, or UI Automation unavailable)
#  64  bad arguments
param(
    [Parameter(Mandatory = $true)] [string] $Title,
    [Parameter(Mandatory = $true)] [string] $Marker,
    [ValidateSet('auto', 'appactivate', 'uia')] [string] $Method = 'auto',
    [int] $TimeoutSec = 20,
    [string] $Log = '',
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$t0 = Get-Date
$WT_CLASS = 'CASCADIA_HOSTING_WINDOW_CLASS'

function Log([string] $m) {
    $line = '{0} wake pid={1} {2}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fff'), $PID, $m
    $path = $Log
    if (-not $path) {
        $dir = Join-Path $PSScriptRoot '..\state\logs'
        if (Test-Path -LiteralPath $dir) { $path = Join-Path $dir 'wake.log' }
    }
    if ($path) { try { Add-Content -LiteralPath $path -Value $line -Encoding ASCII } catch {} }
}

function Done([int] $code, [string] $msg) {
    $ms = [int]((Get-Date) - $t0).TotalMilliseconds
    $out = "WAKE exit=$code ms=$ms $msg"
    Log $out
    Write-Output $out
    exit $code
}

# --- arguments: printable ASCII only, so nothing here can be a SendKeys/shell surprise
if ($Title -cmatch '[^\x20-\x7E]' -or $Title.Length -lt 1 -or $Title.Length -gt 200) {
    Done 64 'bad -Title (printable ASCII, 1-200 chars)'
}
if ($Marker -cmatch '[^\x20-\x7E]' -or $Marker.Length -lt 1 -or $Marker.Length -gt 300) {
    Done 64 'bad -Marker (printable ASCII, 1-300 chars)'
}

$session = (Get-Process -Id $PID).SessionId
if ($session -eq 0) { Done 4 'session 0 has no desktop; run this through a task in the console session' }

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public class WakeWin {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool alt);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(int a, int b, bool attach);
    [DllImport("kernel32.dll")] public static extern int GetCurrentThreadId();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
    public static string Text(IntPtr h) { var sb = new StringBuilder(512); GetWindowTextW(h, sb, 512); return sb.ToString(); }
    public static string Cls(IntPtr h) { var sb = new StringBuilder(256); GetClassNameW(h, sb, 256); return sb.ToString(); }
    public static List<IntPtr> Windows() {
        var l = new List<IntPtr>();
        EnumWindows(delegate (IntPtr h, IntPtr p) { l.Add(h); return true; }, IntPtr.Zero);
        return l;
    }
}
'@

# The whole safety rule, in one place: is `$hwnd` the foreground window, is it a
# Windows Terminal window, and does its title equal -Title exactly (case and all)?
function Test-Foreground([IntPtr] $hwnd) {
    $fg = [WakeWin]::GetForegroundWindow()
    if ($fg -ne $hwnd) { return $false }
    if ([WakeWin]::Cls($fg) -cne $WT_CLASS) { return $false }
    return ([WakeWin]::Text($fg) -ceq $Title)
}

function Describe-Foreground {
    $fg = [WakeWin]::GetForegroundWindow()
    $fpid = 0
    [void][WakeWin]::GetWindowThreadProcessId($fg, [ref] $fpid)
    $name = try { (Get-Process -Id $fpid -ErrorAction Stop).ProcessName } catch { '?' }
    $t = [WakeWin]::Text($fg)
    if ($t.Length -gt 40) { $t = $t.Substring(0, 40) }
    $t = $t -replace '[^\x20-\x7E]', '?'
    return ('fg=proc:{0} class:{1} title:"{2}"' -f $name, [WakeWin]::Cls($fg), $t)
}

function Wait-Foreground([IntPtr] $hwnd, [int] $ms) {
    $end = (Get-Date).AddMilliseconds($ms)
    do {
        if (Test-Foreground $hwnd) { return $true }
        Start-Sleep -Milliseconds 50
    } while ((Get-Date) -lt $end)
    return $false
}

# Raise `$hwnd` and prove it is really in front. Every step is followed by a
# check, because SetForegroundWindow returns success and does nothing when
# Windows refuses a foreground steal (CTO_Knowledge_Winbox_DesktopGUI rule 2).
# Returns the name of the step that worked, or $null.
function Raise-Window([IntPtr] $hwnd, $wsh) {
    if ([WakeWin]::IsIconic($hwnd)) { [void][WakeWin]::ShowWindow($hwnd, 9) }   # SW_RESTORE
    if (Test-Foreground $hwnd) { return 'already' }

    try { [void]$wsh.AppActivate($Title) } catch {}
    if (Wait-Foreground $hwnd 1500) { return 'AppActivate' }

    $fg = [WakeWin]::GetForegroundWindow()
    $fgTid = 0
    $fgPid = 0
    if ($fg -ne [IntPtr]::Zero) { $fgTid = [WakeWin]::GetWindowThreadProcessId($fg, [ref] $fgPid) }
    $me = [WakeWin]::GetCurrentThreadId()
    $attached = $false
    if ($fgTid -ne 0 -and $fgTid -ne $me) { $attached = [WakeWin]::AttachThreadInput($me, $fgTid, $true) }
    try {
        [void][WakeWin]::BringWindowToTop($hwnd)
        [void][WakeWin]::SetForegroundWindow($hwnd)
    } finally {
        if ($attached) { [void][WakeWin]::AttachThreadInput($me, $fgTid, $false) }
    }
    if (Wait-Foreground $hwnd 1500) { return 'SetForegroundWindow+AttachThreadInput' }

    [WakeWin]::SwitchToThisWindow($hwnd, $true)
    if (Wait-Foreground $hwnd 1500) { return 'SwitchToThisWindow' }
    return $null
}

function ConvertTo-SendKeysText([string] $s) {
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $s.ToCharArray()) {
        if ('+^%~(){}[]'.IndexOf($ch) -ge 0) { [void]$sb.Append('{' + $ch + '}') } else { [void]$sb.Append($ch) }
    }
    $sb.ToString()
}

# Guard, send the text, guard again, send Enter. Returns 'sent', 'refused' (nothing
# typed) or 'enter-withheld' (text typed, the foreground changed before Enter).
function Send-Guarded([IntPtr] $hwnd, $wsh) {
    if (-not (Test-Foreground $hwnd)) { return 'refused' }
    if ($DryRun) { return 'dry-run' }
    $wsh.SendKeys((ConvertTo-SendKeysText $Marker))
    Start-Sleep -Milliseconds 300
    if (-not (Test-Foreground $hwnd)) { return 'enter-withheld' }
    $wsh.SendKeys('{ENTER}')
    return 'sent'
}

$wsh = New-Object -ComObject WScript.Shell
$tried = @()

# ---- (a) appactivate: a WT window whose own title is exactly -Title
if ($Method -eq 'auto' -or $Method -eq 'appactivate') {
    $hits = @([WakeWin]::Windows() | Where-Object {
        [WakeWin]::IsWindowVisible($_) -and [WakeWin]::Cls($_) -ceq $WT_CLASS -and [WakeWin]::Text($_) -ceq $Title })
    if ($hits.Count -gt 1) { Done 2 "ambiguous: $($hits.Count) windows titled exactly that" }
    if ($hits.Count -eq 1) {
        $hwnd = $hits[0]
        $how = Raise-Window $hwnd $wsh
        if ($how) {
            $r = Send-Guarded $hwnd $wsh
            if ($r -eq 'sent' -or $r -eq 'dry-run') { Done 0 "$r method=appactivate via=$how" }
            if ($r -eq 'enter-withheld') { Done 3 "Enter withheld: foreground changed after the text was typed; method=appactivate; $(Describe-Foreground)" }
        }
        $tried += 'appactivate:refused'
    } else {
        $tried += 'appactivate:no-window-titled-that'
    }
}

# ---- (b) uia: select the tab, then raise its window
if ($Method -eq 'auto' -or $Method -eq 'uia') {
    $AE = [System.Windows.Automation.AutomationElement]
    $TS = [System.Windows.Automation.TreeScope]
    try {
        $wins = $AE::RootElement.FindAll($TS::Children,
            (New-Object System.Windows.Automation.PropertyCondition ($AE::ClassNameProperty), $WT_CLASS))
    } catch { Done 4 "UI Automation failed: $($_.Exception.Message)" }
    $tabCond = New-Object System.Windows.Automation.PropertyCondition ($AE::ControlTypeProperty),
        ([System.Windows.Automation.ControlType]::TabItem)
    $found = @()
    foreach ($w in $wins) {
        foreach ($tab in $w.FindAll($TS::Descendants, $tabCond)) {
            if ($tab.Current.Name -ceq $Title) { $found += , @($w, $tab) }
        }
    }
    if ($found.Count -gt 1) { Done 2 "ambiguous: $($found.Count) tabs titled exactly that" }
    if ($found.Count -eq 0) { Done 2 "no tab titled exactly that ($($wins.Count) WT windows; tried: $($tried -join ','))" }
    $w = $found[0][0]; $tab = $found[0][1]
    $hwnd = [IntPtr]$w.Current.NativeWindowHandle
    try {
        $sel = $tab.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
        $sel.Select()
    } catch { Done 4 "cannot select the tab: $($_.Exception.Message)" }
    Start-Sleep -Milliseconds 150
    $how = Raise-Window $hwnd $wsh
    if ($how) {
        $r = Send-Guarded $hwnd $wsh
        if ($r -eq 'sent' -or $r -eq 'dry-run') { Done 0 "$r method=uia via=$how" }
        if ($r -eq 'enter-withheld') { Done 3 "Enter withheld: foreground changed after the text was typed; method=uia; $(Describe-Foreground)" }
    }
    $tried += 'uia:refused'
}

Done 3 "guard refused, nothing sent; tried: $($tried -join ','); $(Describe-Foreground)"
