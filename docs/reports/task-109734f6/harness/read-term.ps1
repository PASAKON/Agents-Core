# Read-only: dump the text of the SELECTED tab's terminal in the orgwake window + what has keyboard focus.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]; $TS = [System.Windows.Automation.TreeScope]
$wins = $AE::RootElement.FindAll($TS::Children, (New-Object System.Windows.Automation.PropertyCondition ($AE::ClassNameProperty), 'CASCADIA_HOSTING_WINDOW_CLASS'))
foreach ($w in $wins) {
    $tabs = $w.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition ($AE::ControlTypeProperty), ([System.Windows.Automation.ControlType]::TabItem)))
    $mine = $false; foreach ($t in $tabs) { if ($t.Current.Name -ceq 'org-wake-test' -or $t.Current.Name -ceq 'org-wake-decoy') { $mine = $true } }
    if (-not $mine) { continue }   # never read anybody else's window
    "window title=[{0}] tabs={1}" -f $w.Current.Name, $tabs.Count
    $all = $w.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($e in $all) {
        $cn = $e.Current.ClassName
        if ($cn -match 'TermControl') {
            "  TermControl class=$cn ctype=$($e.Current.ControlType.ProgrammaticName) hasKbFocus=$($e.Current.HasKeyboardFocus) offscreen=$($e.Current.IsOffscreen)"
            try {
                $tp = $e.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
                $txt = $tp.DocumentRange.GetText(-1)
                ($txt -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -Last 8) | ForEach-Object { "    | $_" }
            } catch { "    (no TextPattern: $($_.Exception.Message))" }
        }
    }
    $fe = $AE::FocusedElement
    "  FocusedElement: class=$($fe.Current.ClassName) ctype=$($fe.Current.ControlType.ProgrammaticName) pid=$($fe.Current.ProcessId) name.len=$($fe.Current.Name.Length)"
}
