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
    [ValidateSet('peek', 'send', 'attach', 'clip')] [string] $Mode = 'peek',
    [string] $MsgFile = 'C:\mooniex\line\line_msg.txt',
    [string] $AttachFile = '',
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

$line = Get-Process -Name LINE -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $line) { Say 'FAIL no LINE window'; Write-Output 'FAIL no LINE window'; exit 2 }

[void][Win]::ShowWindow($line.MainWindowHandle, 9)     # SW_RESTORE
[void][Win]::SetForegroundWindow($line.MainWindowHandle)
Start-Sleep -Milliseconds 900

$r = New-Object Win+RECT
[void][Win]::GetWindowRect($line.MainWindowHandle, [ref] $r)
$W = $r.Right - $r.Left; $H = $r.Bottom - $r.Top
Say "LINE window $($r.Left),$($r.Top) ${W}x${H}"
if ($W -lt 400 -or $H -lt 300) { Say 'FAIL window too small'; Write-Output 'FAIL window geometry'; exit 6 }

# The composer sits at the bottom of the right-hand chat pane. Ratios, not fixed
# pixels, so moving or resizing the window does not silently mis-click.
$clickX = [int]($r.Left + $W * 0.72)
$clickY = [int]($r.Top + $H * 0.90)
# The chat transcript is the area above it; that is what must change on send.
$chat = @{ x0 = [int]($r.Left + $W * 0.42); y0 = [int]($r.Top + $H * 0.10)
           x1 = [int]($r.Left + $W * 0.98); y1 = [int]($r.Top + $H * 0.85) }
$box  = @{ x0 = [int]($r.Left + $W * 0.42); y0 = [int]($r.Top + $H * 0.85)
           x1 = [int]($r.Left + $W * 0.98); y1 = [int]($r.Top + $H * 0.96) }

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
    Write-Output "OK clip at=$clipX,$clipY diff=$d shot=$p"
    exit 0
}

if ($Mode -eq 'peek') {
    $s = Grab; $p = Keep $s 'peek'; $s.Dispose()
    Say "peek shot $p"
    Write-Output "OK peek window=${W}x${H} composer=$clickX,$clickY shot=$p"
    exit 0
}

# --- attach: go through the paperclip, not the clipboard -------------------
# LINE's composer ignores a file drop pasted with Ctrl+V (measured: the box
# stays empty). The paperclip opens a plain Windows "Open" dialog whose File
# name box already has focus, so the path can simply be pasted there.
if ($Mode -eq 'attach') {
    if (-not (Test-Path $AttachFile)) { Say "FAIL missing $AttachFile"; Write-Output 'FAIL missing attachment'; exit 5 }
    $item = Get-Item $AttachFile
    $tag = "attach-$($item.BaseName)"
    $clipX = [int]($r.Left + $W * 0.457)
    $clipY = [int]($r.Top + $H * 0.978)

    $before = Grab
    [System.Windows.Forms.SendKeys]::SendWait('{ESC}')      # clear any stray dialog
    Start-Sleep -Milliseconds 500
    [void][Win]::SetForegroundWindow($line.MainWindowHandle)
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
        Write-Output "FAIL paperclip did not open a dialog shot=$dPath"
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
        Write-Output "FAIL file did not reach the chat shot=$aPath"
        exit 10
    }
    Write-Output "OK sent file $($item.Name) ($($item.Length) bytes) dialog=$dPath sent=$aPath chatDiff=$chatDiff"
    exit 0
}

if ($true) {
    if (-not (Test-Path $MsgFile)) { Say "FAIL missing $MsgFile"; Write-Output 'FAIL missing message'; exit 3 }
    $text = Get-Content -Raw -Encoding UTF8 $MsgFile
    $md5 = (Get-FileHash $MsgFile -Algorithm MD5).Hash
    Set-Clipboard -Value $text
    Start-Sleep -Milliseconds 400
    if ((Get-Clipboard -Raw) -ne $text) { Say 'FAIL clipboard mismatch'; Write-Output 'FAIL clipboard'; exit 4 }
    $what = "message $($text.Length) chars md5=$md5"
    $tag = 'msg'
}
Say "clipboard holds $what"

# --- click the composer, paste, and PROVE the paste landed ----------------
$before = Grab
[void][Win]::SetForegroundWindow($line.MainWindowHandle)
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
    Write-Output "FAIL paste did not land (composer unchanged) shot=$pPath"
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
    Write-Output "FAIL enter did not send (chat unchanged) shot=$aPath"
    exit 8
}

Write-Output "OK sent $what pasted=$pPath sent=$aPath chatDiff=$chatDiff"
