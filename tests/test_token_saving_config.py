"""task-9f6fec26: every session auto-compacts at 300k, not the 1M-model
default (~967K). Verifies the two places that set it -- claude-home/
settings.json's `autoCompactWindow` key and the guarded
CLAUDE_CODE_AUTO_COMPACT_WINDOW export in all six launchers -- plus the
Compact instructions section added to claude-home/CLAUDE.md.

Reads repo files by path only; never touches $HOME or ~/.claude, so it is
safe to run on a box where install-claude-home.sh has not (yet) linked
anything.

Run: .venv/bin/python -m pytest tests/test_token_saving_config.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "claude-home" / "settings.json"
CLAUDE_MD = ROOT / "claude-home" / "CLAUDE.md"

LAUNCHERS = (
    "scripts/spawn-cto.sh",
    "scripts/spawn-cxo.sh",
    "scripts/cto-claude.sh",
    "scripts/cxo-claude.sh",
    "scripts/spawn-worker.sh",
    "scripts/spawn-worker-remote.sh",
)

GUARD_RE = re.compile(
    r'^\s*:\s*"\$\{CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000\}"\s*$', re.M
)
EXPORT_RE = re.compile(r"^\s*export CLAUDE_CODE_AUTO_COMPACT_WINDOW\s*$", re.M)


def test_settings_json_parses_and_carries_autocompact_window():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    assert data["autoCompactWindow"] == 300000


def test_settings_json_keeps_existing_keys():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    # A handful of pre-existing keys from the CEO's live config -- proves
    # the edit only added a key rather than replacing the file.
    assert "model" in data  # value is the CEO's live choice (changes via /model); presence is the invariant
    assert "hooks" in data
    assert "permissions" in data


def test_each_launcher_exports_autocompact_window_guarded():
    for rel in LAUNCHERS:
        path = ROOT / rel
        assert path.is_file(), f"missing launcher: {rel}"
        text = path.read_text(encoding="utf-8")
        assert GUARD_RE.search(text), (
            f"{rel}: missing guarded default "
            '`: "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000}"`'
        )
        assert EXPORT_RE.search(text), (
            f"{rel}: missing `export CLAUDE_CODE_AUTO_COMPACT_WINDOW`"
        )


def test_claude_md_has_compact_instructions_section():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "## Compact instructions" in text
