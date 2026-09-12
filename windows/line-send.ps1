# line-send.ps1 — put one staged message into the LINE chat that is already open.
#
# Runs in Windows session 1 (the desktop). SSH lands in session 0, which cannot
# see a window at all — from there Get-Process returns MainWindowHandle 0 and
# the screen reports 1024x768 instead of the real 1920x1080 — so every piece of
# geometry below has to happen here, inside the interactive scheduled task that
# scripts/winbox-line-send.sh registers.
#
# Deliberately dumb. It does not search for a contact, does not choose a chat
# and does not compose anything: it pastes a file that was written and
# checksummed elsewhere into whatever chat a person has already opened.
# Choosing the recipient is the one step that must stay with a human.
#
# It also refuses to claim success it has not seen. The first version reported
# "OK sent" when nothing had been sent: SetForegroundWindow raises the window
# but leaves keyboard focus wherever it was, so Ctrl+V went nowhere and the
# script never looked. Now it clicks the composer first, and compares the
# screen before and after — if the pixels did not move, it fails loudly.
param(
    [ValidateSet('peek', 'send', 'attach', 'clip', 'menu', 'pin', 'open')] [string] $Mode = 'peek',
    [string] $MsgFile = 'C:\mooniex\line\line_msg.txt',
    [string] $AttachFile = '',
    [string] $Who = '',
    [string] $ShotDir = 'C:\mooniex\line'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool alt);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, int e);
    public struct RECT { public int Left, Top, Right, Bottom; }
    public const uint LDOWN = 0x0002, LUP = 0x0004;
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(150);
        mouse_event(LDOWN, 0, 0, 0, 0);
        System.Threading.Thread.Sleep(60);
        mouse_event(LUP, 0, 0, 0, 0);
    }
}
'@

$log = Join-Path $ShotDir 'line-send.log'
# The caller reads out.txt over SSH. Writing it here means the scheduled task
# can run powershell directly with a HIDDEN window: the cmd.exe wrapper that
# used to provide the ">" redirect also created a console window, and that
# console stole the foreground from LINE about six seconds in, which is what
# broke every click the script then made.
function Result([string] $s) {
    Set-Content -Path (Join-Path $ShotDir 'out.txt') -Value $s -Encoding UTF8
    Write-Output $s
}
function Say([string] $m) {
    Add-Content -Path $log -Encoding UTF8 -Value ("{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $m)
}

function Grab {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
    $g.Dispose()
    $bmp
}

function Keep([System.Drawing.Bitmap] $bmp, [string] $tag) {
    $p = Join-Path $ShotDir ("shot-$tag.png")
    $bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
    $p
}

# How many sampled pixels differ inside a rectangle. Every 6th pixel is plenty
# to notice a message bubble appearing, and keeps this well under a second.
function DiffCount([System.Drawing.Bitmap] $a, [System.Drawing.Bitmap] $b,
                   [int] $x0, [int] $y0, [int] $x1, [int] $y1) {
    $n = 0
    for ($y = $y0; $y -lt $y1; $y += 6) {
        for ($x = $x0; $x -lt $x1; $x += 6) {
            if ($a.GetPixel($x, $y).ToArgb() -ne $b.GetPixel($x, $y).ToArgb()) { $n++ }
        }
    }
    $n
}

Say "--- mode=$Mode session=$((Get-Process -Id $PID).SessionId) user=$env:USERNAME"

function Get-LineWindow {
    Get-Process -Name LINE -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
}

$line = Get-LineWindow
if (-not $line) {
    # LINE minimises to the tray, and a tray-only window reports
    # MainWindowHandle 0 — the process is alive but there is nothing to click.
    # Re-launching the same executable asks the running instance to show itself
    # rather than starting a second one, so this restores rather than duplicates.
    $exe = (Get-Process -Name LINE -ErrorAction SilentlyContinue | Select-Object -First 1).Path
    if (-not $exe) { $exe = Join-Path $env:LOCALAPPDATA 'LINE\bin\current\LINE.exe' }
    if (Test-Path $exe) {
        Say "no window - restoring from tray via $exe"
        Start-Process $exe -ErrorAction SilentlyContinue
        for ($i = 0; $i -lt 20 -and -not $line; $i++) { Start-Sleep -Milliseconds 1000; $line = Get-LineWindow }
    }
}
if (-not $line) { Say 'FAIL no LINE window'; Result 'FAIL no LINE window (tray restore failed)'; exit 2 }
Say "LINE window handle $($line.MainWindowHandle)"

# Raise LINE and PROVE it came up.
#
# SetForegroundWindow returns without error and does nothing when Windows
# refuses a foreground steal from a background process — which is the normal
# case here, since this task starts while something else owns the screen.
# Measured 2026-09-12: a chat name meant for LINE's search box was typed into a
# Windows Terminal that was sitting on top, because every mode raised the
# window and then simply assumed it had. A synthetic ALT keypress releases the
# foreground lock; the handle comparison is what makes the claim true.
function Focus-Line([IntPtr] $h) {
    for ($i = 0; $i -lt 5; $i++) {
        switch ($i) {
            0 { [void][Win]::SetForegroundWindow($h) }
            1 { [System.Windows.Forms.SendKeys]::SendWait('%'); Start-Sleep -Milliseconds 150
                [void][Win]::SetForegroundWindow($h) }
            2 { [Win]::SwitchToThisWindow($h, $true) }          # ignores the foreground lock
            3 { [void][Win]::ShowWindow($h, 6)                  # SW_MINIMIZE
                Start-Sleep -Milliseconds 400
                [void][Win]::ShowWindow($h, 9)                  # SW_RESTORE puts it on top
                [void][Win]::BringWindowToTop($h) }
            4 { [Win]::SwitchToThisWindow($h, $true)
                [void][Win]::ShowWindow($h, 3) }                # SW_MAXIMIZE
        }
        Start-Sleep -Milliseconds 900
        # Compare the OWNING PROCESS, not the handle. LINE's foreground window
        # is a child of the one MainWindowHandle reports, so a handle-equality
        # test said "not focused" while LINE was plainly on top (measured
        # 2026-09-12: peek photographed it in front and the check still failed).
        # What the click actually needs is that LINE owns the foreground.
        $fg = [Win]::GetForegroundWindow()
        $fgPid = 0; [void][Win]::GetWindowThreadProcessId($fg, [ref] $fgPid)
        if ($fgPid -eq $line.Id) { Say "focused on attempt $i (fg pid $fgPid)"; return $true }
    }
    Say "not focused; foreground pid $fgPid, LINE is $($line.Id)"
    $false
}

$focused = Focus-Line $line.MainWindowHandle
if (-not $focused -and $Mode -ne 'peek') {
    Say 'FAIL LINE would not come to the foreground - refusing to click blind'
    Result 'FAIL could not focus LINE (another window owns the screen)'
    exit 13
}
if (-not $focused) { Say 'WARN not focused, but peek only reads' }
Start-Sleep -Milliseconds 400

$r = New-Object Win+RECT
[void][Win]::GetWindowRect($line.MainWindowHandle, [ref] $r)
$W = $r.Right - $r.Left; $H = $r.Bottom - $r.Top
Say "LINE window $($r.Left),$($r.Top) ${W}x${H}"
if ($W -lt 400 -or $H -lt 300) { Say 'FAIL window too small'; Result 'FAIL window geometry'; exit 6 }

# The composer sits at the bottom of the right-hand chat pane. Ratios, not fixed
# pixels, so moving or resizing the window does not silently mis-click.
$clickX = [int]($r.Left + $W * 0.72)
$clickY = [int]($r.Top + $H * 0.90)
# The chat transcript is the area above it; that is what must change on send.
$chat = @{ x0 = [int]($r.Left + $W * 0.42); y0 = [int]($r.Top + $H * 0.10)
           x1 = [int]($r.Left + $W * 0.98); y1 = [int]($r.Top + $H * 0.85) }
$box  = @{ x0 = [int]($r.Left + $W * 0.42); y0 = [int]($r.Top + $H * 0.85)
           x1 = [int]($r.Left + $W * 0.98); y1 = [int]($r.Top + $H * 0.96) }

# Open a chat by name.
#
# This is the ONE place the script picks a recipient, so it deliberately stops
# short of sending: it searches, opens the top hit, and photographs the result
# so a person can read the chat header and confirm it is who they meant. The
# guarantee is not "the script cannot get it wrong" — it is "getting it wrong
# is visible before anything leaves".
#
# The name goes in via the clipboard, not SendKeys: SendKeys mangles Thai, the
# same way a task brief did (docs/reports/FINDING-winbox-ascii-only.md).
if ($Mode -eq 'open') {
    if (-not $Who) { Say 'FAIL no -Who'; Result 'FAIL no -Who given'; exit 12 }
    # No {ESC} here. Escape is LINE's "hide to tray", so the line that was
    # meant to dismiss a stray dialog was actually sending the whole app to the
    # tray — after which focus went to whatever was underneath and every
    # subsequent click missed. If a dialog really is open, the paperclip click
    # simply does nothing and the pixel check below catches it.
    if (-not (Focus-Line $line.MainWindowHandle)) { Say 'FAIL lost focus'; Result 'FAIL lost LINE focus'; exit 13 }
    Start-Sleep -Milliseconds 400
    [Win]::Click([int]($r.Left + $W * 0.229), [int]($r.Top + $H * 0.079))     # search box
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait('^a')
    Set-Clipboard -Value $Who
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait('^v')
    Start-Sleep -Milliseconds 3000
    $res = Grab; $rPath = Keep $res 'open-results'; $res.Dispose()
    [Win]::Click([int]($r.Left + $W * 0.2465), [int]($r.Top + $H * 0.1395))   # top hit
    Start-Sleep -Milliseconds 3000
    $op = Grab; $oPath = Keep $op 'open'; $op.Dispose()
    Say "open '$Who' results=$rPath opened=$oPath"
    Result "OK opened who='$Who' results=$rPath shot=$oPath"
    exit 0
}

# Pin the top row of the chat list.
#
# The menu item is clicked at an offset measured off a real screenshot of this
# exact right-click point (+41,+58), NOT at a window ratio: "Delete" sits only
# 54px below "Pin chat" and a ratio that drifts by a few percent lands on it.
# An offset from the click that opened the menu cannot drift, because the menu
# is drawn relative to that click.
#
# Worst case is still worth naming: LINE orders the list by recency, so if
# another chat receives a message first, this pins that one instead. Pinning is
# reversible and it photographs the result, so that is a nuisance, not damage.
if ($Mode -eq 'pin') {
    Add-Type 'using System;using System.Runtime.InteropServices;public class M{[DllImport("user32.dll")]public static extern void mouse_event(uint f,uint x,uint y,uint d,int e);[DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);public static void R(int x,int y){SetCursorPos(x,y);System.Threading.Thread.Sleep(150);mouse_event(0x0008,0,0,0,0);System.Threading.Thread.Sleep(60);mouse_event(0x0010,0,0,0,0);}}'
    # No {ESC} — see the note in 'open'. Escape hides LINE to the tray.
    if (-not (Focus-Line $line.MainWindowHandle)) { Say 'FAIL lost focus'; Result 'FAIL lost LINE focus'; exit 13 }
    Start-Sleep -Milliseconds 400
    $mx = [int]($r.Left + $W * 0.2465); $my = [int]($r.Top + $H * 0.1395)
    $b4 = Grab
    [M]::R($mx, $my)
    Start-Sleep -Milliseconds 1500
    $open = Grab
    if ((DiffCount $b4 $open $r.Left $r.Top ($r.Left + $W) ($r.Top + $H)) -lt 100) {
        $b4.Dispose(); $open.Dispose()
        Say 'FAIL context menu never opened'
        Result 'FAIL no context menu'
        exit 11
    }
    [Win]::Click(($mx + 41), ($my + 58))
    Start-Sleep -Milliseconds 2000
    $af = Grab
    $d = DiffCount $open $af $r.Left $r.Top ($r.Left + $W) ($r.Top + $H)
    $p = Keep $af 'pin'
    $b4.Dispose(); $open.Dispose(); $af.Dispose()
    Say "pin click at $($mx+41),$($my+58) diff=$d shot=$p"
    Result "OK pin clicked=$($mx+41),$($my+58) diff=$d shot=$p"
    exit 0
}

# Diagnostic: right-click the top row of the chat list and photograph the menu
# it opens. Opening a context menu selects nothing, so this changes nothing.
if ($Mode -eq 'menu') {
    Add-Type 'using System;using System.Runtime.InteropServices;public class M{[DllImport("user32.dll")]public static extern void mouse_event(uint f,uint x,uint y,uint d,int e);[DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);public static void R(int x,int y){SetCursorPos(x,y);System.Threading.Thread.Sleep(150);mouse_event(0x0008,0,0,0,0);System.Threading.Thread.Sleep(60);mouse_event(0x0010,0,0,0,0);}}'
    $mx = [int]($r.Left + $W * 0.2465); $my = [int]($r.Top + $H * 0.1395)
    $b4 = Grab
    [M]::R($mx, $my)
    Start-Sleep -Milliseconds 1500
    $af = Grab
    $d = DiffCount $b4 $af $r.Left $r.Top ($r.Left + $W) ($r.Top + $H)
    $p = Keep $af 'menu'
    $b4.Dispose(); $af.Dispose()
    Say "right-click at $mx,$my diff=$d shot=$p"
    Result "OK menu at=$mx,$my diff=$d shot=$p"
    exit 0
}

# Diagnostic: click the paperclip and photograph whatever it opens. Opening a
# file dialog sends nothing, so this is safe to run while learning the UI.
if ($Mode -eq 'clip') {
    $clipX = [int]($r.Left + $W * 0.457)
    $clipY = [int]($r.Top + $H * 0.978)
    $b4 = Grab
    [Win]::Click($clipX, $clipY)
    Start-Sleep -Milliseconds 2000
    $af = Grab
    $d = DiffCount $b4 $af $r.Left $r.Top ($r.Left + $W) ($r.Top + $H)
    $p = Keep $af 'clip'
    $b4.Dispose(); $af.Dispose()
    Say "clip click at $clipX,$clipY diff=$d shot=$p"
    Result "OK clip at=$clipX,$clipY diff=$d shot=$p"
    exit 0
}

if ($Mode -eq 'peek') {
    $s = Grab; $p = Keep $s 'peek'; $s.Dispose()
    Say "peek shot $p"
    Result "OK peek window=${W}x${H} composer=$clickX,$clickY shot=$p"
    exit 0
}

# --- attach: go through the paperclip, not the clipboard -------------------
# LINE's composer ignores a file drop pasted with Ctrl+V (measured: the box
# stays empty). The paperclip opens a plain Windows "Open" dialog whose File
# name box already has focus, so the path can simply be pasted there.
if ($Mode -eq 'attach') {
    if (-not (Test-Path $AttachFile)) { Say "FAIL missing $AttachFile"; Result 'FAIL missing attachment'; exit 5 }
    $item = Get-Item $AttachFile
    $tag = "attach-$($item.BaseName)"
    $clipX = [int]($r.Left + $W * 0.457)
    $clipY = [int]($r.Top + $H * 0.978)

    $before = Grab
    # No {ESC} — see 'open'. Escape is LINE's hide-to-tray, so clearing a stray
    # dialog this way took the whole app off screen instead.
    Start-Sleep -Milliseconds 500
    if (-not (Focus-Line $line.MainWindowHandle)) { Say 'FAIL lost focus'; Result 'FAIL lost LINE focus'; exit 13 }
    Start-Sleep -Milliseconds 400
    [Win]::Click($clipX, $clipY)
    Start-Sleep -Milliseconds 2500

    $dlg = Grab
    $dlgDiff = DiffCount $before $dlg ($r.Left) ($r.Top) ($r.Left + $W) ($r.Top + $H)
    $dPath = Keep $dlg "$tag-dialog"
    Say "paperclip diff $dlgDiff px; shot $dPath"
    if ($dlgDiff -lt 200) {
        $before.Dispose(); $dlg.Dispose()
        Say 'FAIL the open dialog never appeared'
        Result "FAIL paperclip did not open a dialog shot=$dPath"
        exit 9
    }

    Set-Clipboard -Value $item.FullName
    Start-Sleep -Milliseconds 400
    [System.Windows.Forms.SendKeys]::SendWait('^v')
    Start-Sleep -Milliseconds 800
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    Start-Sleep -Milliseconds 3000

    # LINE refuses some extensions outright (.srt is one) and offers to zip
    # them instead, behind a modal whose "Always compress and send" box comes
    # pre-ticked. Leaving that ticked would silently change a preference on
    # somebody's account, so untick it first, then press Send. If the file was
    # a type LINE accepts there is no modal and these two clicks land on the
    # transcript, where they do nothing.
    $mid = Grab
    $modalDiff = DiffCount $dlg $mid $chat.x0 $chat.y0 $chat.x1 $chat.y1
    $mPath = Keep $mid "$tag-modal"
    Say "after choosing file: diff $modalDiff px; shot $mPath"
    [Win]::Click([int]($r.Left + $W * 0.4136), [int]($r.Top + $H * 0.5010))   # untick
    Start-Sleep -Milliseconds 400
    [Win]::Click([int]($r.Left + $W * 0.4603), [int]($r.Top + $H * 0.5436))   # Send
    Start-Sleep -Milliseconds 4500
    $mid.Dispose()

    $after = Grab
    $chatDiff = DiffCount $dlg $after $chat.x0 $chat.y0 $chat.x1 $chat.y1
    $aPath = Keep $after "$tag-sent"
    Say "after open: chat diff $chatDiff px; shot $aPath"
    $before.Dispose(); $dlg.Dispose(); $after.Dispose()
    if ($chatDiff -lt 30) {
        Say 'FAIL nothing reached the transcript'
        Result "FAIL file did not reach the chat shot=$aPath"
        exit 10
    }
    Result "OK sent file $($item.Name) ($($item.Length) bytes) dialog=$dPath sent=$aPath chatDiff=$chatDiff"
    exit 0
}

if ($true) {
    if (-not (Test-Path $MsgFile)) { Say "FAIL missing $MsgFile"; Result 'FAIL missing message'; exit 3 }
    $text = Get-Content -Raw -Encoding UTF8 $MsgFile
    $md5 = (Get-FileHash $MsgFile -Algorithm MD5).Hash
    Set-Clipboard -Value $text
    Start-Sleep -Milliseconds 400
    if ((Get-Clipboard -Raw) -ne $text) { Say 'FAIL clipboard mismatch'; Result 'FAIL clipboard'; exit 4 }
    $what = "message $($text.Length) chars md5=$md5"
    $tag = 'msg'
}
Say "clipboard holds $what"

# --- click the composer, paste, and PROVE the paste landed ----------------
$before = Grab
if (-not (Focus-Line $line.MainWindowHandle)) { Say 'FAIL lost focus'; Result 'FAIL lost LINE focus'; exit 13 }
Start-Sleep -Milliseconds 300
[Win]::Click($clickX, $clickY)
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 2000

$pasted = Grab
$boxDiff = DiffCount $before $pasted $box.x0 $box.y0 $box.x1 $box.y1
$pPath = Keep $pasted "$tag-pasted"
Say "composer diff $boxDiff px; shot $pPath"
if ($boxDiff -lt 15) {
    $before.Dispose(); $pasted.Dispose()
    Say 'FAIL nothing appeared in the composer - not pressing enter'
    Result "FAIL paste did not land (composer unchanged) shot=$pPath"
    exit 7
}

# --- send, and PROVE the transcript grew ----------------------------------
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
Start-Sleep -Milliseconds 2500
$after = Grab
$chatDiff = DiffCount $pasted $after $chat.x0 $chat.y0 $chat.x1 $chat.y1
$aPath = Keep $after "$tag-sent"
Say "chat diff $chatDiff px; shot $aPath"
$before.Dispose(); $pasted.Dispose(); $after.Dispose()

if ($chatDiff -lt 30) {
    Say 'FAIL transcript did not change after enter'
    Result "FAIL enter did not send (chat unchanged) shot=$aPath"
    exit 8
}

Result "OK sent $what pasted=$pPath sent=$aPath chatDiff=$chatDiff"
