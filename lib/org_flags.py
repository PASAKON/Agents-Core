"""Host flags for the org restructure (P2): on from a root-owned file, not only the env.

A flag is on for this host when `/etc/org-flags/<NAME>` exists, or when the
process's own environment says `<NAME>=1`. The file is the deploy switch: a
session started from tmux, the relay or node_dispatch takes the tmux server's
environment, not the one that turned the flag on, so an env-only flag was
silently off on exactly those paths (security review of ph/org-p2-launchers,
2026-10-13). The env can still turn a flag on (tests, a one-off launch) but
never off: with the file present, `<NAME>=0` or an empty value changes nothing.

The launchers read the same file in bash (`scripts/cxo-claude.sh`,
`scripts/cto-claude.sh`: `[ -e /etc/org-flags/<NAME> ]`), so keep the path in
step with FLAGS_DIR. On Windows (winbox, M13c) the directory is
`%ProgramData%\org-flags`, which `windows/cxo-claude.ps1` reads the same way.
"""
from __future__ import annotations

import os
from pathlib import Path

def flags_dir_for(os_name: str, program_data: str | None) -> str:
    """Where the host flag files live on an OS (`os.name`)."""
    if os_name == "nt":
        return (program_data or r"C:\ProgramData").rstrip("\\") + r"\org-flags"
    return "/etc/org-flags"


FLAGS_DIR = Path(flags_dir_for(os.name, os.environ.get("ProgramData")))


def on(name: str) -> bool:
    if os.environ.get(name, "").strip() == "1":
        return True
    try:
        return (FLAGS_DIR / name).is_file()
    except OSError:
        return False
