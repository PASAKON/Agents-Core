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
    [ValidateSet('shot', 'pickfile', 'click')] [string] $Mode = 'shot',
    [string] $Path = '',
    [int] $X = 0,
    [int] $Y = 0,
    [string] $OutDir = 'C:\mooniex\desktop'
)

$ErrorActionPreference = 'Stop'
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
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, int e);
    public static string Title() {
        var sb = new StringBuilder(512);
        GetWindowText(GetForegroundWindow(), sb, 512);
        return sb.ToString();
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
    'pickfile' {
        # The Open dialog's File-name box already has focus when it opens, so the
        # path only has to reach the clipboard. Typing it would mangle anything
        # non-ASCII, the same way a task brief does.
        if (-not (Test-Path $Path)) { Result "FAIL no such file: $Path"; exit 3 }
        $before = Shot 'pick-before'
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
