"""Static checks on windows/spawn-worker.ps1 for W3.3 (task-782936c0).

Same approach as scripts/test_spawn_worker_ps1.py: this box has no PowerShell,
so what can be checked is the TEXT of the script. W3.3 adds `-AgentsRoot`:
node_dispatch runs the script in place from the repo checkout (where it sits in
windows\\ and roles\\ is one level up) instead of from a deploy copy.

Run:  .venv/bin/python -m pytest tests/test_spawn_worker_ps1.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "windows" / "spawn-worker.ps1"


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _code_only() -> str:
    return "\n".join(ln for ln in _text().splitlines() if not ln.strip().startswith("#"))


def test_ascii_only():
    # Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI; one em dash in a
    # string literal becomes three mojibake characters.
    bad = [(n, c) for n, ln in enumerate(_text().splitlines(), 1) for c in ln if ord(c) > 127]
    assert bad == [], f"non-ASCII characters at {bad[:5]}"


def test_agents_root_is_an_optional_string_param():
    m = re.search(r"param\s*\((.*?)\n\)", _text(), re.S)
    assert m, "no param() block"
    assert re.search(r"\[string\]\$AgentsRoot\s*=\s*''", m.group(1))
    assert not re.search(r"Mandatory\s*=\s*\$true\)\]\[string\]\$AgentsRoot", m.group(1))


def test_agents_root_falls_back_to_the_scripts_own_folder():
    assert re.search(
        r"\$agentsRootDir\s*=\s*if\s*\(\$AgentsRoot\)\s*\{\s*\$AgentsRoot\s*\}\s*else\s*\{\s*\$PSScriptRoot\s*\}",
        _code_only()), "the ssh deploy path must keep resolving beside the script"


def test_roles_and_launch_files_hang_off_the_one_root():
    code = _code_only()
    assert "Join-Path $agentsRootDir 'roles'" in code
    assert 'Join-Path $agentsRootDir ".launch-$Task"' in code
    assert re.search(r'Join-Path \$agentsRootDir \("launch-" \+ \$Task \+ "\.cmd"\)', code)
    # The only remaining reads of the script's own folder are the fallback line.
    assert len(re.findall(r"\$PSScriptRoot|\$PSCommandPath", code)) == 1


def test_still_launches_through_a_one_shot_interactive_scheduled_task():
    code = _code_only()
    for needle in ("New-ScheduledTaskPrincipal", "-LogonType Interactive",
                   "Register-ScheduledTask", "Start-ScheduledTask",
                   "Unregister-ScheduledTask"):
        assert needle in code, needle


def test_braces_and_parens_balance():
    """A cheap pwsh-free syntax guard: a dropped brace in a large edit is the
    typical way a .ps1 that cannot be run here goes wrong."""
    code = _code_only()
    assert code.count("{") == code.count("}"), (code.count("{"), code.count("}"))
    assert code.count("(") == code.count(")"), (code.count("("), code.count(")"))
