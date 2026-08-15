"""Mandatory parity proof (task-724cff99, Do-4): lib/org_tools_registry.py's
REGISTRY is the single source of truth for the 19 CTO org tools. This
asserts all 3 production surfaces actually expose exactly REGISTRY's tool
names — introspected from the REAL objects each surface builds at import
time, never hand-copied into this file — so a tool added to the registry
alone makes this test FAIL until every surface picks it up. That's the
whole point: it's the structural guarantee that a 4th tool-name list can
never again silently fall behind (the shape of audit finding W1).

Surfaces checked:
  - runners/cto_mcp_server.py: FastMCP's OWN `mcp.list_tools()` introspection
    API (not `mcp._tool_manager` or any other guess at internals).
  - runners/cto.py: the real `ALL_TOOLS` dict its run() builds the SDK
    server + allowed_tools from.
  - runners/cto_chat.py: the real `ClaudeAgentOptions.allowed_tools` list
    `_build_options()` produces (mcp__org__* entries only — the lungnote/
    Read/Grep/Glob entries are intentionally unrelated, filtered out).

Manual verification that this test actually has teeth (not committed, per
the task's instruction not to leave scratch changes in the diff): appended
a fake 18th ToolSpec to org_tools_registry.REGISTRY/BY_NAME in a throwaway
script, re-ran test_parity() and confirmed it goes from PASS to FAIL
because none of the 3 surfaces' introspected sets include the fake name,
then discarded the change. See the task's final report for the transcript.

Run via:  python scripts/test_tool_parity.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import org_tools_registry as reg  # noqa: E402
from runners import cto  # noqa: E402
from runners import cto_chat  # noqa: E402
from runners import cto_mcp_server as srv  # noqa: E402

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _expected() -> set[str]:
    return {spec.name for spec in reg.REGISTRY}


def _cto_mcp_server_names() -> set[str]:
    tools = asyncio.run(srv.mcp.list_tools())
    return {t.name for t in tools}


def _cto_py_names() -> set[str]:
    return set(cto.ALL_TOOLS)


def _cto_chat_org_names() -> set[str]:
    opts = cto_chat._build_options()
    return {
        name.removeprefix("mcp__org__")
        for name in opts.allowed_tools
        if name.startswith("mcp__org__")
    }


# The `_*_ok` helpers return bools for main()'s hand-run report. The `test_*`
# wrappers below ASSERT, because pytest treats a test function that *returns* a
# value as passing no matter what that value is — it only warns
# (PytestReturnNotNoneWarning), and the default run silences warnings. This
# guard therefore reported green under pytest for every drift it exists to
# catch. Proven 2026-08-15: `report_to_ceo` was in REGISTRY with no FastMCP
# stub in cto_mcp_server.py; standalone printed "1 FAILURE(S)" and exited 1,
# while the same check under pytest passed.


def _parity_ok() -> bool:
    expected = _expected()
    mcp_names = _cto_mcp_server_names()
    cto_names = _cto_py_names()
    chat_names = _cto_chat_org_names()

    ok = expected == mcp_names == cto_names == chat_names
    if not ok:
        print(f"    expected (registry):      {sorted(expected)}")
        print(f"    cto_mcp_server.py diff:   {sorted(expected ^ mcp_names)}")
        print(f"    cto.py ALL_TOOLS diff:    {sorted(expected ^ cto_names)}")
        print(f"    cto_chat.py allowed diff: {sorted(expected ^ chat_names)}")
    return ok


def _names_unique() -> bool:
    return len(reg.REGISTRY) == len(reg.BY_NAME)


def test_parity() -> None:
    expected = _expected()
    mcp_names = _cto_mcp_server_names()
    cto_names = _cto_py_names()
    chat_names = _cto_chat_org_names()
    assert expected == mcp_names, (
        "cto_mcp_server.py (FastMCP) is missing a stub for: "
        f"{sorted(expected ^ mcp_names)}"
    )
    assert expected == cto_names, (
        f"cto.py ALL_TOOLS drift: {sorted(expected ^ cto_names)}"
    )
    assert expected == chat_names, (
        f"cto_chat.py allowed_tools drift: {sorted(expected ^ chat_names)}"
    )


def test_registry_names_unique() -> None:
    assert _names_unique(), "duplicate tool name in REGISTRY"


def main() -> int:
    print("== tool-name parity across all 3 production surfaces vs REGISTRY ==")
    _mark(
        _names_unique(),
        f"registry itself has {len(reg.REGISTRY)} entries, no duplicate names",
    )
    _mark(
        _parity_ok(),
        "REGISTRY == cto_mcp_server.py (FastMCP introspection) == "
        "cto.py (ALL_TOOLS) == cto_chat.py (allowed_tools org names)",
    )
    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
