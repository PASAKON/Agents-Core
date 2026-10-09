# ceo_button.ps1 -- the CEO's two buttons on the winbox desktop.
#
#   ใช้คอม.cmd      -> ceo_button.ps1 -Mode on   -> pc_lease.py ceo-on
#   เลิกใช้คอม.cmd  -> ceo_button.ps1 -Mode off  -> pc_lease.py ceo-off
#
# Twice (2026-10-07, 2026-10-09 13:36) an agent found the screen lease FREE and
# relaunched Minecraft over the Dota 2 game the CEO was playing. A FREE lease is
# not a free screen. These buttons give him an explicit hold that every agent
# tool respects. pc_lease.py does all the work; this only runs it and tells him,
# in Thai and in ONE message box, what happened.
#
# Saved as UTF-8 WITH a BOM. Windows PowerShell 5.1 reads a BOM-less script as
# ANSI and every Thai string below turns to mojibake that still "runs" (the
# silent-success #5 note in CTO_Knowledge_Winbox_DesktopGUI). The .cmd files
# stay pure ASCII for the sibling reason: cmd.exe reads a batch file in the OEM
# code page.
#
# pc_lease.py prints ASCII lines with fixed prefixes, and this reads them:
#   PC: CEO / PC: released     the hold is on / off
#   BUMPED: <who> ...          an agent lease that just lost the screen
#   FARM: <state> - ...        what happened to Cookie Run
#   NO HOLD: / WARNING: / FAILED:
# Change one side, change the other (tests/test_pc_lease_ceo_hold.py).
param(
    [Parameter(Mandatory = $true)] [ValidateSet('on', 'off')] [string] $Mode
)

$ErrorActionPreference = 'Stop'

$Py    = 'C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe'
$Lease = 'C:\mooniex\pclease\pc_lease.py'
$Verb  = if ($Mode -eq 'on') { 'ceo-on' } else { 'ceo-off' }
# ceo-off waits for Cookie Run to come back, and pc_lease's resume() allows up
# to ~8 minutes for that (a restarted game plus a preflight round). Past this,
# stop waiting and say so: a button that never answers is worse than a "no".
$LimitS = 900
$Tell   = 'กรุณาบอก CTO พร้อมข้อความด้านล่างนี้'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing


function New-Progress([string] $Text) {
    # A small "please wait" window. ceo-off can take minutes while Cookie Run
    # comes back, and a button that shows nothing for minutes gets pressed
    # again. Cosmetic only: if it cannot be drawn, the run goes on without it.
    try {
        $f = New-Object System.Windows.Forms.Form
        $f.Text = 'MoonieX'
        $f.FormBorderStyle = 'FixedDialog'
        $f.ControlBox = $false
        $f.StartPosition = 'CenterScreen'
        $f.TopMost = $true
        $f.ClientSize = New-Object System.Drawing.Size(460, 120)
        $l = New-Object System.Windows.Forms.Label
        $l.Dock = 'Fill'
        $l.TextAlign = 'MiddleCenter'
        $l.Font = New-Object System.Drawing.Font('Leelawadee UI', 12)
        $l.Text = $Text
        $f.Controls.Add($l)
        $f.Show()
        [System.Windows.Forms.Application]::DoEvents()
        return @{ Form = $f; Label = $l }
    } catch {
        return $null
    }
}


$waitText = if ($Mode -eq 'on') { 'กำลังล็อกจอให้คุณ รอสักครู่...' } else { 'กำลังปลดล็อกจอ รอสักครู่...' }
$progress = New-Progress $waitText

$out   = New-Object System.Collections.Generic.List[string]
$err   = ''
$code  = $null
$crash = $null
try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Py
    # -u: unbuffered, so "PC: released" arrives the moment it is printed and the
    # wait window can say the lock is already off while Cookie Run comes back.
    $psi.Arguments = "-u `"$Lease`" $Verb"
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $p = [System.Diagnostics.Process]::Start($psi)
    # stderr drains on its own task, or a chatty traceback could fill the pipe
    # and hang python while we wait on stdout.
    $errTask = $p.StandardError.ReadToEndAsync()
    $next = $p.StandardOutput.ReadLineAsync()
    $t0 = Get-Date
    while ($true) {
        if ($next.IsCompleted) {
            $line = $next.Result
            if ($null -eq $line) { break }
            $out.Add($line)
            if ($progress -and $line.StartsWith('PC: released')) {
                $progress.Label.Text = "ปลดล็อกแล้ว กำลังเปิด Cookie Run กลับมา`nอาจใช้เวลาสองสามนาที..."
            }
            $next = $p.StandardOutput.ReadLineAsync()
            continue
        }
        if (((Get-Date) - $t0).TotalSeconds -gt $LimitS) {
            try { $p.Kill() } catch { }
            $crash = "pc_lease.py did not finish within $LimitS s and was stopped."
            break
        }
        if ($progress) { [System.Windows.Forms.Application]::DoEvents() }
        Start-Sleep -Milliseconds 100
    }
    if (-not $crash) {
        $p.WaitForExit()
        $code = $p.ExitCode
    }
    if ($errTask.Wait(5000)) { $err = $errTask.Result }
} catch {
    $crash = $_.Exception.Message
}
if ($progress) { try { $progress.Form.Close() } catch { } }


# --- what to tell him ---------------------------------------------------------
$all = ($out -join "`n").Trim()
if ($err) {
    $e = $err.Trim()
    if ($e.Length -gt 800) { $e = '...' + $e.Substring($e.Length - 800) }
    $all = ($all + "`n" + $e).Trim()
}
$bumped = @($out | Where-Object { $_ -like 'BUMPED: *' } | ForEach-Object { $_.Substring(8) })
$farm = ''
foreach ($l in $out) { if ($l -match '^FARM: ([a-z-]+)') { $farm = $Matches[1] } }
$locked = [bool]($out | Where-Object { $_ -like 'PC: CEO*' })
$freed  = [bool]($out | Where-Object { $_ -like 'PC: released*' })
$nohold = [bool]($out | Where-Object { $_ -like 'NO HOLD:*' })

if ($crash) {
    $ok  = $false
    $msg = "ปุ่มนี้ทำงานไม่สำเร็จ`n$Tell`n`n$crash`n$all"
} elseif ($Mode -eq 'on') {
    if ($locked) {
        $ok  = ($code -eq 0)
        $msg = 'ล็อกจอให้คุณแล้ว เอเจนต์จะไม่ใช้จอจนกว่าคุณจะกด เลิกใช้คอม'
        if ($bumped.Count -gt 0) {
            $msg += "`n`nหยุดเอเจนต์ที่กำลังใช้จออยู่ไว้แล้ว: " + ($bumped -join ', ')
        }
        if ($farm -eq 'stopped') {
            $msg += "`nหยุด Cookie Run ไว้ให้แล้ว จะกลับมาเองตอนคุณกด เลิกใช้คอม"
        }
        if (-not $ok) { $msg += "`n`nแต่มีบางอย่างไม่เรียบร้อย $Tell`n`n$all" }
    } else {
        $ok  = $false
        $msg = "ล็อกจอไม่สำเร็จ เอเจนต์ยังใช้จอได้อยู่`n$Tell`n`n$all"
    }
} else {
    if ($nohold) {
        $ok  = ($code -eq 0)
        $msg = 'ตอนนี้ไม่ได้ล็อกจออยู่ ไม่ต้องทำอะไรเพิ่ม'
    } elseif ($freed) {
        $ok  = ($code -eq 0)
        $msg = 'ปลดล็อกแล้ว เอเจนต์กลับมาใช้จอได้'
        switch ($farm) {
            'back'    { $msg += "`nCookie Run กลับมาทำงานแล้ว" }
            'handed'  { $msg += "`nCookie Run จะกลับมาเองเมื่อเอเจนต์ที่ยืมจออยู่คืนจอ" }
            'off'     { $msg += "`nCookie Run ไม่ได้ทำงานอยู่ตอนที่คุณกด ใช้คอม เลยไม่ได้เปิดกลับ" }
            'unknown' { $msg += "`nไม่ได้เปิด Cookie Run กลับ เพราะไม่รู้ว่าก่อนหน้านี้มันทำงานอยู่หรือเปล่า" }
            'failed'  { $msg += "`nแต่ Cookie Run ไม่กลับมาทำงาน" }
        }
        if (-not $ok) { $msg += "`n$Tell`n`n$all" }
    } else {
        $ok  = $false
        $msg = "ปลดล็อกไม่สำเร็จ เอเจนต์ยังใช้จอไม่ได้`n$Tell`n`n$all"
    }
}

# An owner that is TopMost puts the box in front of whatever is on screen; a
# box with no owner can open behind a full-screen window and look like nothing
# happened.
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$icon = if ($ok) { [System.Windows.Forms.MessageBoxIcon]::Information } else { [System.Windows.Forms.MessageBoxIcon]::Warning }
[void][System.Windows.Forms.MessageBox]::Show($owner, $msg.Trim(), 'MoonieX', [System.Windows.Forms.MessageBoxButtons]::OK, $icon)
$owner.Dispose()
if ($ok) { exit 0 } else { exit 1 }
