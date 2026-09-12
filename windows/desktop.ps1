# desktop.ps1 — the small things browser automation cannot reach on winbox.
#
# A browser driver can click inside a page. It cannot touch a native Windows
# dialog, and the one that matters most is the file picker: every upload on
# every site ends at an "Open" dialog that lives outside the browser entirely.
# On 2026-09-12 that stopped a YouTube upload dead — the operator tried a local
# HTTP server and then chunked the file, and was right to stop rather than keep
# routing around a deliberate limit. The dialog was the whole problem, and the
# dialog is ten lines of PowerShell.
#
# Runs in session 1 via an interactive scheduled task; see winbox-desktop-gui.
param(
    [ValidateSet('shot', 'pickfile', 'click', 'scroll', 'paste')] [string] $Mode = 'shot',
    [string] $Path = '',
    # The path arrives in a FILE, not as an argument: a path containing a quote
    # terminates the single-quoted -Argument string and the task dies with
    # 0x8007010B before it can report anything (measured twice, 2026-09-12).
    [string] $PathFile = '',
    [int] $X = 0,
    [int] $Y = 0,
    [int] $Notches = -6,
    [switch] $SelectAll,
    [string] $DialogTitle = 'Open',
    [string] $OutDir = 'C:\mooniex\desktop'
)

$ErrorActionPreference = 'Stop'
if ($PathFile -and (Test-Path $PathFile)) { $Path = (Get-Content -Raw -Encoding UTF8 $PathFile).Trim() }
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class D {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string c, string n);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool alt);
    // Focus a named top-level window and PROVE it came forward. The task's own
    // PowerShell wins the foreground even with -WindowStyle Hidden, so a paste
    // aimed at a dialog lands in nothing at all unless this runs first.
    public static bool Focus(string title) {
        IntPtr h = FindWindow(null, title);
        if (h == IntPtr.Zero) return false;
        for (int i = 0; i < 4; i++) {
            if (i == 1) SwitchToThisWindow(h, true); else SetForegroundWindow(h);
            System.Threading.Thread.Sleep(500);
            if (GetForegroundWindow() == h) return true;
        }
        return false;
    }
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, int e);
    public static string Title() {
        var sb = new StringBuilder(512);
        GetWindowText(GetForegroundWindow(), sb, 512);
        return sb.ToString();
    }
    // One wheel notch is 120. Negative scrolls down, which is what reading a
    // long settings page needs.
    public static void Wheel(int x, int y, int notches) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(120);
        mouse_event(0x0800, 0, 0, (uint)(notches * 120), 0);
    }
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(150);
        mouse_event(0x0002, 0, 0, 0, 0);
        System.Threading.Thread.Sleep(60);
        mouse_event(0x0004, 0, 0, 0, 0);
    }
}
'@

function Shot([string] $tag) {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
    $p = Join-Path $OutDir "$tag.png"
    $bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    $p
}

function Result([string] $s) {
    Set-Content -Path (Join-Path $OutDir 'out.txt') -Value $s -Encoding UTF8
    Write-Output $s
}

switch ($Mode) {
    'shot' {
        $p = Shot 'shot'
        Result "OK shot=$p foreground='$([D]::Title())' session=$((Get-Process -Id $PID).SessionId)"
    }
    'click' {
        [D]::Click($X, $Y)
        Start-Sleep -Milliseconds 1200
        $p = Shot 'click'
        Result "OK clicked=$X,$Y foreground='$([D]::Title())' shot=$p"
    }
    'scroll' {
        [D]::Wheel($X, $Y, $Notches)
        Start-Sleep -Milliseconds 1200
        $p = Shot 'scroll'
        Result "OK scrolled $Notches at $X,$Y shot=$p"
    }
    'paste' {
        # Replace a field's contents from a FILE, never by typing: SendKeys
        # mangles anything non-ASCII, and this text carries middle dots and an
        # em dash. -SelectAll clears what is already in the field first.
        if (-not (Test-Path $Path)) { Result "FAIL no such file: $Path"; exit 3 }
        $txt = Get-Content -Raw -Encoding UTF8 $Path
        Set-Clipboard -Value $txt
        Start-Sleep -Milliseconds 400
        if ((Get-Clipboard -Raw) -ne $txt) { Result 'FAIL clipboard mismatch'; exit 4 }
        $before = Shot 'paste-before'
        # Click the field first. One click both brings the owning window forward
        # and puts the caret where the text goes — without it the task's own
        # PowerShell holds the foreground and 1,461 characters land nowhere
        # (measured 2026-09-12).
        if ($X -gt 0 -and $Y -gt 0) { [D]::Click($X, $Y); Start-Sleep -Milliseconds 600 }
        if ([D]::Title() -like '*PowerShell*') {
            Result "FAIL target window not focused (foreground is PowerShell) - pass -X/-Y"
            exit 7
        }
        if ($SelectAll) { [System.Windows.Forms.SendKeys]::SendWait('^a'); Start-Sleep -Milliseconds 300 }
        [System.Windows.Forms.SendKeys]::SendWait('^v')
        Start-Sleep -Milliseconds 1500
        $after = Shot 'paste-after'
        Result "OK pasted $($txt.Length) chars into '$([D]::Title())' before=$before after=$after"
    }
    'pickfile' {
        # The Open dialog's File-name box already has focus when it opens, so the
        # path only has to reach the clipboard. Typing it would mangle anything
        # non-ASCII, the same way a task brief does.
        if (-not (Test-Path $Path)) { Result "FAIL no such file: $Path"; exit 3 }
        $before = Shot 'pick-before'
        if (-not [D]::Focus($DialogTitle)) {
            Result "FAIL could not focus a window titled '$DialogTitle' (foreground is '$([D]::Title())')"
            exit 6
        }
        $title = [D]::Title()
        Set-Clipboard -Value ((Get-Item $Path).FullName)
        Start-Sleep -Milliseconds 400
        [System.Windows.Forms.SendKeys]::SendWait('^v')
        Start-Sleep -Milliseconds 900
        $typed = Shot 'pick-typed'
        [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
        Start-Sleep -Milliseconds 2500
        $after = Shot 'pick-after'
        Result "OK picked='$Path' dialogWas='$title' now='$([D]::Title())' before=$before typed=$typed after=$after"
    }
}
