"""Tests that scripts/cto-claude.sh and scripts/cxo-claude.sh always build a
`claude` invocation carrying --remote-control while their host opts in
(task-bbdfa8d1, CEO 2026-09-11: "เช็คไม่ได้เลยว่ามี session เปิดจริงไหม" —
two live Contabo CTO sessions were invisible in the CEO's Claude app because
these two launchers built their `claude` argv without the flag).

Two layers, both must hold:

  1. STATIC — read each launcher's source and assert:
       a. it computes the flag via `runners.worker_init.remote_control_args`
          (reused, not a second hand-copied per-host switch), and
       b. the actual final claude-invocation block references the computed
          REMOTE_CONTROL_ARGS array (catches "computed but never wired in").
       c. no OTHER, unconditional `--remote-control` literal exists outside
          that one computed assignment (catches "hardcoded, ignores the
          per-host switch" -- the exact bug _render_remote_claude_args in
          tools/delegate.py has today, which this task deliberately does
          NOT copy).

  2. DYNAMIC — extract the exact HOST_KEY/REMOTE_CONTROL_ARGS block each
     script runs and execute it for real (real repo root, real .venv, real
     config/hosts.yaml, real runners.worker_init.remote_control_args) for
     every host in config/hosts.yaml, asserting REMOTE_CONTROL_ARGS ends up
     containing "--remote-control" whenever that host's `remote_control`
     flag is true (every host today). This is as close to "build a claude
     invocation" as a test can get without actually launching claude (which
     needs a TUI/auth/network) -- and it runs the launcher's OWN literal
     bash, not a reimplementation of it, so a syntax typo in that snippet
     fails this test too.

Run via:   pytest scripts/test_session_remote_control.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.config import hosts as get_hosts  # noqa: E402

LAUNCHERS = ["scripts/cto-claude.sh", "scripts/cxo-claude.sh"]

_HAS_VENV = (ROOT / ".venv" / "bin" / "python3").exists()

# The two pieces the dynamic test needs, extracted SEPARATELY and then joined:
# the HOST_KEY case block, and the REMOTE_CONTROL_ARGS computation. They used
# to be adjacent, so one span-regex worked; task-9ff9263f moved the case block
# up (reconcile/register_cxo need HOST_KEY first), and a span from `case` to
# the `fi` then swallowed ~200 lines of launcher in between -- reconcile,
# register, the memory pull -- which reference $ROOT/$LOCKFILE and blew up
# under `set -u` (2026-09-17, first seen after the merges landed on main).
# Matching each block on its own keeps the test about what it claims to test
# and makes it indifferent to where the launcher puts them.
_CASE_RE = re.compile(r'case "\$MACHINE_LABEL" in.*?\nesac\n', re.S)
_RC_RE = re.compile(
    r'REMOTE_CONTROL_ARGS=\(\).*?REMOTE_CONTROL_ARGS=\(--remote-control\)\nfi\n',
    re.S,
)


# ---------------------------------------------------------------------------
# 1. static
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_reuses_worker_init_remote_control_args_not_hardcoded(launcher: str) -> None:
    src = (ROOT / launcher).read_text()
    assert "from runners.worker_init import remote_control_args" in src, (
        f"{launcher} must reuse runners.worker_init.remote_control_args() -- "
        "the SAME per-host switch workers use -- not hand-roll its own"
    )


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_final_claude_invocation_carries_the_computed_flag(launcher: str) -> None:
    src = (ROOT / launcher).read_text()
    # The actual `claude \ ... \` launch block, up to `exit $?`.
    m = re.search(r"\nclaude \\\n(.*?)\nexit \$\?", src, re.S)
    assert m, f"could not locate the final `claude \\` invocation in {launcher}"
    invocation = m.group(1)
    assert "REMOTE_CONTROL_ARGS" in invocation, (
        f"{launcher}: REMOTE_CONTROL_ARGS is computed but never appears in "
        "the actual claude invocation -- a claude session can be built "
        "without --remote-control"
    )


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_no_second_unconditional_remote_control_literal(launcher: str) -> None:
    """Exactly one line may contain the bare `--remote-control` token: the
    conditional array assignment inside the computed block. A second,
    unconditional occurrence would mean the flag is hardcoded somewhere and
    the per-host opt-out (config/hosts.yaml `remote_control: false`) is
    silently ignored for that occurrence."""
    src = (ROOT / launcher).read_text()
    hits = [
        ln for ln in src.splitlines()
        if "--remote-control" in ln and not ln.strip().startswith("#")
    ]
    assert hits == ['  REMOTE_CONTROL_ARGS=(--remote-control)'], (
        f"{launcher}: expected exactly one conditional --remote-control "
        f"assignment, found: {hits!r}"
    )


# ---------------------------------------------------------------------------
# 2. dynamic — run the launcher's OWN bash snippet for real
# ---------------------------------------------------------------------------

def _extract_block(launcher: str) -> str:
    src = (ROOT / launcher).read_text()
    case_m = _CASE_RE.search(src)
    assert case_m, f"could not extract the HOST_KEY case block from {launcher}"
    rc_m = _RC_RE.search(src)
    assert rc_m, f"could not extract the REMOTE_CONTROL_ARGS block from {launcher}"
    return case_m.group(0) + "\n" + rc_m.group(0)


def _run_block(block: str, machine_label: str) -> list[str]:
    script = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'cd "{ROOT}"\n'
        f'MACHINE_LABEL="{machine_label}"\n'
        + block
        + '\nprintf "%s\\n" "${REMOTE_CONTROL_ARGS[@]+${REMOTE_CONTROL_ARGS[@]}}"\n'
    )
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"block failed: {r.stderr}"
    return [ln for ln in r.stdout.splitlines() if ln]


_MACHINE_FOR_HOST = {"mac": "MAC", "contabo": "CONTABO", "winbox": "WINDOWS"}


@pytest.mark.skipif(not _HAS_VENV, reason="needs a real .venv at repo root")
@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_flag_present_for_every_host_that_opts_in(launcher: str) -> None:
    block = _extract_block(launcher)
    real_hosts = get_hosts()
    assert real_hosts, "config/hosts.yaml declared no hosts -- nothing to verify against"
    for host_name, cfg in real_hosts.items():
        machine_label = _MACHINE_FOR_HOST.get(host_name)
        if machine_label is None:
            continue  # only hosts this launcher's uname-case block recognizes
        args = _run_block(block, machine_label)
        opts_in = cfg.get("remote_control", True)
        if opts_in:
            assert args == ["--remote-control"], (
                f"{launcher}: host={host_name!r} opts into remote_control in "
                f"config/hosts.yaml but the built claude invocation would carry "
                f"REMOTE_CONTROL_ARGS={args!r} -- a claude invocation can be "
                f"built without --remote-control"
            )
        else:
            assert args == [], (
                f"{launcher}: host={host_name!r} opts OUT of remote_control "
                f"but REMOTE_CONTROL_ARGS={args!r} anyway"
            )


def test_every_declared_host_covered_by_this_test() -> None:
    """Guard against config/hosts.yaml growing a host this test's uname-label
    map doesn't know how to simulate -- silently untested is as bad as
    untested and known."""
    real_hosts = get_hosts()
    unknown = set(real_hosts) - set(_MACHINE_FOR_HOST)
    assert not unknown, (
        f"config/hosts.yaml declares host(s) {sorted(unknown)} this test cannot "
        "simulate -- add a MACHINE_LABEL mapping to _MACHINE_FOR_HOST"
    )
