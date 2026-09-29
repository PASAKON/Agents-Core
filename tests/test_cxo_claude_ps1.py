"""Static checks on windows/cxo-claude.ps1 + windows/win-cto.ps1 (task-3d392ab3,
Org Mesh W3.2). Same style as scripts/test_spawn_worker_ps1.py's GH #151/#152
checks: this box has no PowerShell, no Windows Terminal, no winbox, so what
CAN be verified here is that the .ps1 TEXT actually contains the required
steps -- a regression that silently deletes one of these is exactly the kind
of thing a human skimming a large diff misses. A live smoke test on winbox
is out of scope for this task (task brief: "No ssh to winbox; nothing live.
The live launch is task W3.4.").

Run via: pytest tests/test_cxo_claude_ps1.py
(tests/ IS in pytest.ini's default testpaths, unlike scripts/test_spawn_worker_ps1.py's
own note about scripts/ -- this one is picked up by a bare `pytest` run.)
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CXO_SCRIPT = ROOT / "windows" / "cxo-claude.ps1"
WINCTO_SCRIPT = ROOT / "windows" / "win-cto.ps1"

# Literal profile-name paths that must never appear (task constraint: derive
# paths from the script's own location / $env:USERPROFILE, never hardcode a
# profile name -- W3.0 fixes config/*.yaml in parallel).
HARDCODED_PROFILE_PATHS = ("C:\\Users\\UsEr", "C:\\Users\\passg")

DROPPED_MECHANISMS = ("osascript", "tmux", "iTerm")


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _code_only(p: Path) -> str:
    """`_text()` with full-line `#` comments stripped -- so a check for
    whether some pattern is actually USED can't be defeated (or falsely
    tripped) by an explanatory comment merely mentioning it. Matches
    scripts/test_spawn_worker_ps1.py's own helper."""
    return "\n".join(
        ln for ln in _text(p).splitlines() if not ln.strip().startswith("#")
    )


def test_scripts_exist():
    assert CXO_SCRIPT.is_file()
    assert WINCTO_SCRIPT.is_file()


def test_ascii_only():
    """PS 5.1 reads a BOM-less .ps1 as ANSI (win-cto.ps1's own header rule) --
    a stray non-ASCII character (a smart quote, an em dash, Thai text) is
    exactly the kind of thing that silently mangles on winbox."""
    for p in (CXO_SCRIPT, WINCTO_SCRIPT):
        raw = p.read_bytes()
        bad = [b for b in raw if b > 0x7F]
        assert not bad, f"{p.name} has non-ASCII byte(s): {bad[:5]!r}..."


def test_param_block_has_the_four_flags():
    text = _text(CXO_SCRIPT)
    m = re.search(r"param\s*\((.*?)\n\)", text, re.S)
    assert m, "no param() block found in cxo-claude.ps1"
    block = m.group(1)
    for flag in ("$Role", "$Session", "$InitialPrompt", "$TabTitle"):
        assert flag in block, f"param block missing {flag}"
    assert "ValidateSet" in block and "'cto'" in block and "'cmo'" in block \
        and "'cgo'" in block and "'cfo'" in block, \
        "param block must restrict -Role to cto/cmo/cgo/cfo"


def test_calls_cxo_mcp_config_generator():
    code = _code_only(CXO_SCRIPT)
    assert "cxo_mcp_config.py" in code
    assert "--print-allowed" in code, (
        "must derive --allowed-tools from the generator, not hand-copy a tool list"
    )
    assert "--role" in code and "$Role" in code


def test_no_dropped_mechanisms():
    """Task brief: 'Drop iTerm, osascript and tmux; the tab title is set
    with the Windows Terminal/console title instead.' Checks actual usage,
    not a comment merely explaining why something was dropped."""
    code = _code_only(CXO_SCRIPT)
    for name in DROPPED_MECHANISMS:
        assert name not in code, f"{name!r} found in cxo-claude.ps1 code (should be dropped)"


def test_no_hardcoded_profile_path():
    for p in (CXO_SCRIPT, WINCTO_SCRIPT):
        text = _text(p)
        for bad in HARDCODED_PROFILE_PATHS:
            assert bad not in text, f"{p.name} hardcodes profile path {bad!r}"


def test_win_cto_delegates_to_cxo_claude():
    text = _text(WINCTO_SCRIPT)
    assert re.search(r"cxo-claude\.ps1['\"]?\s*\)?\s*-Role\s+cto", text) or (
        "cxo-claude.ps1" in text and "-Role" in text and "cto" in text
    ), "win-cto.ps1 must delegate to cxo-claude.ps1 -Role cto"
    assert "osascript" not in text and "tmux" not in text and "iTerm" not in text


def test_org_mcp_and_lungnote_each_get_a_skip_log_line():
    """CEO 2026-09-28 constraint: standalone mode (no org-db.env) must leave
    org MCP and lungnote out with one clear log line EACH, never a crash."""
    text = _text(CXO_SCRIPT)
    assert re.search(r"org MCP skipped", text)
    assert re.search(r"LungNote MCP skipped", text)


def test_standalone_branch_never_calls_cxo_mcp_config():
    """The org-db.env gate must be a real if/else: the generator call sits
    only in the branch that found org-db.env, not unconditionally before the
    check (which would attempt the org MCP server, and its local-sqlite
    fallback, before winbox is allowed to have one)."""
    text = _text(CXO_SCRIPT)
    if_idx = text.index("if (Test-Path $orgEnv)")
    else_idx = text.index("} else {", if_idx)
    gen_idx = text.index("cxo_mcp_config.py", if_idx)
    assert if_idx < gen_idx < else_idx, (
        "cxo_mcp_config.py call must be inside the org-db.env present branch"
    )


def test_strict_mcp_config_applies_in_both_modes():
    """Standalone must still pass --strict-mcp-config (with no --mcp-config
    at all) so the session never inherits another server's half-configured
    secret and prompts for it -- see tools.delegate._render_remote_claude_args
    for the existing precedent of this exact combination."""
    code = _code_only(CXO_SCRIPT)
    assert "--strict-mcp-config" in code
    # Must not be gated inside the hub-mode branch only.
    if_idx = _text(CXO_SCRIPT).index("if (Test-Path $orgEnv)")
    else_close_idx = _text(CXO_SCRIPT).index("\n}\n", if_idx)
    strict_idx = _text(CXO_SCRIPT).index("--strict-mcp-config", else_close_idx)
    assert strict_idx > else_close_idx


def test_cxo_env_vars_exported_unconditionally():
    """Review-fix regression guard: win-cto.ps1 v2 (6edac472) only exported
    CXO_ROLE/CXO_SESSION/CXO_SESSION_ID inside the hub-mode branch. Must be
    set before the org-db.env check, not after/inside it."""
    text = _text(CXO_SCRIPT)
    export_idx = text.index('$env:CXO_SESSION_ID = $sid')
    orgenv_check_idx = text.index("if (Test-Path $orgEnv)")
    assert export_idx < orgenv_check_idx, (
        "CXO_SESSION_ID must be exported before the hub/standalone branch, "
        "not only inside the hub-mode branch"
    )


def test_lock_file_and_active_pointer_present():
    code = _code_only(CXO_SCRIPT)
    assert "$lockFile" in code and "state\\locks" in code
    assert "$activeFile" in code and "-active" in code
    assert "$uuidFile" in code and ".uuid" in code


def test_uuid_hex_suffix_construction_with_nonhex_fallback():
    code = _code_only(CXO_SCRIPT)
    assert re.search(r"\^\[0-9a-f\]\{8\}\$", code), (
        "must gate the hex-suffix uuid construction on an 8-lowercase-hex match"
    )
    assert "uuid.uuid4()" in code


def test_fork_session_detection():
    code = _code_only(CXO_SCRIPT)
    assert "--fork-session" in code
    assert "--resume" in code and "--continue" in code


def test_remote_control_lookup():
    code = _code_only(CXO_SCRIPT)
    assert "remote_control_args" in code


def test_memory_sync_pull_before_launch():
    text = _text(CXO_SCRIPT)
    pull_idx = text.index("tools.memory_sync")
    launch_idx = text.index("& $claude @fullArgs")
    assert pull_idx < launch_idx


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh not installed on this box")
def test_parses_with_zero_errors():
    for script in (CXO_SCRIPT, WINCTO_SCRIPT):
        proc = subprocess.run(
            [
                "pwsh", "-NoProfile", "-Command",
                "$errors = $null; "
                f"[System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$null, [ref]$errors) | Out-Null; "
                "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Output $_.ToString() }; exit 1 } else { exit 0 }",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"{script.name} failed to parse:\n{proc.stdout}\n{proc.stderr}"
