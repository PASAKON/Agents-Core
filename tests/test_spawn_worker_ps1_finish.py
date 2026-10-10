"""Text regressions for Claude's finish script and Terminal launch diagnostics."""

from pathlib import Path
import re


SCRIPT = Path(__file__).resolve().parents[1] / "windows" / "spawn-worker.ps1"


def _text():
    return SCRIPT.read_text(encoding="utf-8")


def _finish_body():
    return _text().split('$finishPs1Body = @"\n', 1)[1].split('\n"@', 1)[0]


def test_finish_stops_only_task_claude_pids_without_tree_kill():
    body = _finish_body()
    assert '/T' not in body
    assert 'taskkill' not in body.lower()
    assert 'Get-CimInstance Win32_Process -Filter "Name = \'claude.exe\'"' in body
    assert "`$_.Name -eq 'claude.exe'" in body
    assert '`$_.CommandLine -and `$_.CommandLine -like "*$Task*"' in body
    assert 'foreach (`$proc in `$procs)' in body
    assert 'Stop-Process -Id `$proc.ProcessId -Force' in body
    assert "`$_.Name -notin @('WindowsTerminal.exe', 'OpenConsole.exe', 'explorer.exe')" in body


def test_finish_runtime_variables_remain_escaped_in_here_string():
    body = _finish_body()
    assert re.findall(r'(?<!`)\$\w+', body) == ['$Task']


def test_terminal_window_selection_is_used_and_logged():
    text = _text()
    launch = text.split("$wtExe = Join-Path", 1)[1].split("elseif ($Runner", 1)[0]
    assert '$terminalCount = @(Get-Process -Name WindowsTerminal -ErrorAction SilentlyContinue).Count' in launch
    assert re.search(
        r"if \(\$terminalCount -gt 0\) \{\s*\$wtWindowArgs = '-w 0'\s*"
        r"\} else \{\s*\$wtWindowArgs = '-w new'", launch
    )
    assert 'start "" "$wtExe" $wtWindowArgs nt ' in launch
    assert 'Write-Output "WindowsTerminal launch: $wtWindowArgs; running=$($terminalCount -gt 0); count=$terminalCount"' in launch


def test_timeout_reports_observed_terminal_count_and_scheduled_task_result():
    failure = _text().split('if (-not $workerPid) {', 1)[1].split('\n    Unregister-ScheduledTask', 1)[0]
    assert '$terminalCount = @(Get-Process -Name WindowsTerminal -ErrorAction SilentlyContinue).Count' in failure
    assert "$lastTaskResult = 'unavailable'" in failure
    assert '(Get-ScheduledTaskInfo -TaskName $stName -ErrorAction Stop).LastTaskResult' in failure
    assert failure.index('Get-ScheduledTaskInfo') < failure.index('throw (')
    assert 'WindowsTerminal running=$($terminalCount -gt 0); count=$terminalCount;' in failure
    assert 'scheduled task=$stName; LastTaskResult=$lastTaskResult' in failure
    assert 'may not have' not in failure
