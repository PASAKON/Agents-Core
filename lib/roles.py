"""The C-level roster: which roles can run a C-level session.

One source: the `c_level` list in policies/agents.yaml, minus ``ceo`` (the CEO
is C-level for authority but is a human at a terminal, never a spawned
session). The reading is `lib.config.live_c_level_roles()`; this module is its
front door for code that must stay import-light -- tools/session_name.py and
tools/itermtab.py are imported under the system `python3`, which may have no
PyYAML (spawn-cxo.sh's `python3 -m tools.session_gc`, cxo-claude.sh's
`python3 -m tools.maintab`) -- and for a box where the policy file is absent.
There it falls back to STATIC_C_LEVEL_ROLES.

Every tuple of C-level roles the code used to hardcode now comes from here, so
adding a C-level is one line in policies/agents.yaml. Wiring the COO (CEO
2026-09-27) took a grep across twenty files because it was not;
tests/test_c_level_roles.py fails if any collection misses a role again.
"""
from __future__ import annotations

# Only for when policies/agents.yaml cannot be read here (no PyYAML under a
# system python3, or no policy file on this box). tests/test_c_level_roles.py
# asserts it holds the same roles as the policy, so it cannot drift silently.
STATIC_C_LEVEL_ROLES: tuple[str, ...] = ("cto", "cmo", "cgo", "cfo", "coo")


def c_level_roles() -> tuple[str, ...]:
    """C-level roles that can own a session, in policies/agents.yaml order."""
    try:
        from lib.config import live_c_level_roles

        return live_c_level_roles()
    except (ImportError, OSError):
        return STATIC_C_LEVEL_ROLES


def c_level_displays() -> tuple[str, ...]:
    """Display labels (CTO, CMO, ...) for c_level_roles(), same order: the
    prefix every C-level tab title and chat label starts with."""
    roles = c_level_roles()
    try:
        from lib.config import display_for

        return tuple(display_for(r) for r in roles)
    except (ImportError, OSError):
        return tuple(r.upper() for r in roles)
