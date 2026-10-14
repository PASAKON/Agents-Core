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

import os
import re

# Only for when policies/agents.yaml cannot be read here (no PyYAML under a
# system python3, or no policy file on this box). tests/test_c_level_roles.py
# asserts it holds the same roles as the policy, so it cannot drift silently.
STATIC_C_LEVEL_ROLES: tuple[str, ...] = ("cto", "cmo", "cgo", "cfo", "coo")


# C-levels that are ONE session ever, started only by their own command and never
# opened per request. coo = SomPong (CEO 2026-10-01): one always-on session on
# Contabo, tmux `sompong`, started by /spawn-coo (scripts/spawn-coo.sh).
# send_to_cxo --spawn and the relay's spawn_c_level refuse these; the launcher
# (scripts/cxo-claude.sh --role coo) refuses a second one itself.
SINGLETON_ROLES: tuple[str, ...] = ("coo",)


def singleton_refusal(role: str) -> str | None:
    """Why `role` cannot be spawned ad hoc, or None when it can."""
    if role not in SINGLETON_ROLES:
        return None
    return (
        "SomPong (COO) is ONE always-on session on Contabo and is never spawned "
        "per request. If it is down, run /spawn-coo (bash scripts/spawn-coo.sh); "
        "then send the letter with send_to_cxo, without --spawn."
    )


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


# --- Project Head (org restructure P2, plan §3.2) ------------------------------
# A Project Head is neither a C-level nor a worker: one session per project,
# owned by its lane's C-level. Its session carries CXO_ROLE=project_head plus
# ORG_PH_LANE (the owning C-level role) and ORG_PH_PROJECT (the project name);
# docs/design/org-restructure-p2.md is the contract. Nothing here is live
# unless the host flag ORG_PH_ROLES is on (lib/org_flags).
PH_ROLE = "project_head"
# Anchored as well as used with fullmatch: a later .match() must not accept "Name;x".
PH_PROJECT_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,39}\Z")


def ph_roles_on() -> bool:
    """True when this host runs the Project Head layer (host flag ORG_PH_ROLES)."""
    from lib import org_flags
    return org_flags.on("ORG_PH_ROLES")


def is_project_head(role: str | None) -> bool:
    return (role or "").strip().lower() == PH_ROLE


def ph_display(lane: str) -> str:
    """The label a Project Head shows everywhere: `Project Head (CTO)`."""
    return f"Project Head ({(lane or '').strip().upper()})"


def ph_lane_refusal(lane: str) -> str | None:
    """Why `lane` cannot own a Project Head, or None when it can."""
    if lane in c_level_roles():
        return None
    return f"lane must be one of {', '.join(c_level_roles())} (got {lane!r})"


def ph_project_refusal(project: str) -> str | None:
    """Why `project` is not a usable Project Head project name, or None."""
    if PH_PROJECT_RE.fullmatch(project or ""):
        return None
    return ("project must be 1-40 chars of letters, digits, _ or -, starting "
            f"with a letter or digit (got {project!r})")


# browser_operator and Project Head (org restructure P2: a PH does short one-off
# browser jobs itself; CEO 2026-10-13 "เอาตามนี้" on the peer proposal, relayed by
# CTO #e106b78b). Still narrower than the full Chrome surface: no gif_creator, no
# shortcuts_execute. select_browser/switch_browser stay (see the note at the end
# of the list); which Chrome a PH may use (one browser home per PH) is its role
# doc's rule, roles/project_head.md, written by the COO.
#
# Upload was withheld at first on exfiltration grounds and granted 2026-08-10
# (CEO) because reference images are the job — the C-level names the path in
# the task. Two guardrails make that safe enough: file_upload is restricted by
# the harness itself to files shared with the session, and the role doc forbids
# uploading any path the task did not name.
#
# resize_window is load-bearing, not optional — an image costs
# ceil(w/28) * ceil(h/28) visual tokens with no client-side cap (measured
# 2026-08-10: neither MAX_MCP_OUTPUT_TOKENS nor
# CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS truncates an image result), so
# shrinking the window is the only lever that bounds screenshot cost. It works
# — a 1024x768 resize produced a 1024x591 screenshot — but it can silently
# no-op on a window the OS will not resize (a fullscreen one) while still
# returning success, so the skill requires verifying the result.
CHROME_TOOLS: tuple[str, ...] = tuple((
    "mcp__claude-in-chrome__tabs_context_mcp "
    "mcp__claude-in-chrome__tabs_create_mcp "
    "mcp__claude-in-chrome__tabs_close_mcp "
    "mcp__claude-in-chrome__navigate "
    "mcp__claude-in-chrome__read_page "
    "mcp__claude-in-chrome__get_page_text "
    "mcp__claude-in-chrome__find "
    "mcp__claude-in-chrome__resize_window "
    "mcp__claude-in-chrome__computer "
    "mcp__claude-in-chrome__form_input "
    "mcp__claude-in-chrome__file_upload "
    "mcp__claude-in-chrome__upload_image "
    "mcp__claude-in-chrome__javascript_tool "
    "mcp__claude-in-chrome__browser_batch "
    "mcp__claude-in-chrome__read_console_messages "
    "mcp__claude-in-chrome__read_network_requests "
    # Browser selection: with several Chromes paired to the account the CLI
    # refuses every browser action until one is chosen (2026-09-07, winbox).
    "mcp__claude-in-chrome__list_connected_browsers "
    "mcp__claude-in-chrome__select_browser "
    "mcp__claude-in-chrome__switch_browser"
).split())
