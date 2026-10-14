"""PowerShell reads `"$Name:rest"` as a drive-scoped variable and the whole script fails to parse.

windows/spawn-worker.ps1 shipped `"origin/$Base:.media-allow"` (adf79743) and every winbox spawn died
with "Variable reference is not valid" (task-32436ad7, 2026-10-14). Write `${Name}:` instead.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPES = {"env", "script", "global", "local", "using", "private", "function", "variable", "alias"}
PATTERN = re.compile(r"(?<![`{])\$([A-Za-z_][A-Za-z0-9_]*):(?![:\\])")


def offenders(text: str) -> list[str]:
    return [m.group(0) for m in PATTERN.finditer(text) if m.group(1).lower() not in SCOPES]


def test_no_drive_scoped_variable_in_windows_scripts():
    bad = {}
    for p in sorted((ROOT / "windows").glob("*.ps1")):
        hits = offenders(p.read_text(encoding="utf-8", errors="replace"))
        if hits:
            bad[p.name] = hits
    assert not bad, f"use ${{Name}}: inside strings: {bad}"


def test_pattern_catches_the_shipped_bug_and_spares_scopes():
    assert offenders('show "origin/$Base:.media-allow"') == ["$Base:"]
    assert offenders('show "origin/${Base}:.media-allow"') == []
    assert offenders('$env:USERPROFILE and $script:x and `$Base:y') == []
