"""Test: knowledge bank symlink wiring for DEV worktrees.

Covers:
  - _symlink_knowledge creates a symlink for a mapped role
  - _symlink_knowledge is a no-op (no error) for an unmapped role
  - _symlink_knowledge is a no-op when the bank dir doesn't exist on disk
  - Stale symlinks are replaced on re-run

Run: .venv/bin/python scripts/test_knowledge_symlink.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runners.worker_init import KNOWLEDGE_MAP, _symlink_knowledge

ROOT = Path(__file__).resolve().parent.parent


def test_mapped_role_gets_symlink():
    """A role in KNOWLEDGE_MAP gets a working symlink if the bank dir
    exists on disk."""
    role = "content_strategist"
    assert role in KNOWLEDGE_MAP, f"{role} not in KNOWLEDGE_MAP"
    bank = ROOT / KNOWLEDGE_MAP[role][0]
    # Only run if the bank actually exists on this machine (it should in
    # the main repo checkout; might not in a minimal CI).
    if not bank.is_dir():
        print(f"SKIP: {bank} not present on disk")
        return

    with tempfile.TemporaryDirectory() as td:
        _symlink_knowledge(td, role)
        link = Path(td) / "knowledge" / bank.name
        assert link.is_symlink(), f"expected symlink at {link}"
        assert link.resolve().is_dir(), f"symlink target not a dir: {link.resolve()}"
        # Verify at least one file is reachable through the symlink
        assert any(link.resolve().iterdir()), "symlink target dir is empty"
    print("mapped role gets symlink: PASS")


def test_multi_bank_role_gets_every_bank():
    """A role mapped to several banks gets a symlink for each one.
    web_designer owns design-knowledge but also carries brand-knowledge so
    the CMO's theme travels with it — if only the first link appeared, the
    designer would silently work without the brand gates."""
    role = "web_designer"
    banks = KNOWLEDGE_MAP.get(role, [])
    assert len(banks) > 1, f"{role} should map to multiple banks, got {banks}"
    on_disk = [ROOT / b for b in banks if (ROOT / b).is_dir()]
    if len(on_disk) < 2:
        print(f"SKIP: fewer than 2 of {banks} present on disk")
        return

    with tempfile.TemporaryDirectory() as td:
        _symlink_knowledge(td, role)
        for bank in on_disk:
            link = Path(td) / "knowledge" / bank.name
            assert link.is_symlink(), f"expected symlink at {link}"
            assert link.resolve() == bank.resolve(), (
                f"{link} points at {link.resolve()}, expected {bank}")
    print("multi-bank role gets every bank: PASS")


def test_unmapped_role_no_error():
    """A role NOT in KNOWLEDGE_MAP causes no error — silent no-op."""
    with tempfile.TemporaryDirectory() as td:
        _symlink_knowledge(td, "developer")
        knowledge_dir = Path(td) / "knowledge"
        assert not knowledge_dir.exists(), "knowledge/ dir should not be created for unmapped role"
    print("unmapped role no error: PASS")


def test_missing_bank_dir_no_error():
    """If the bank dir doesn't exist on disk, silently skip — no error."""
    # Temporarily patch KNOWLEDGE_MAP to point at a non-existent dir
    original = KNOWLEDGE_MAP.get("content_strategist")
    KNOWLEDGE_MAP["content_strategist"] = ["knowledge/nonexistent-bank"]
    try:
        with tempfile.TemporaryDirectory() as td:
            _symlink_knowledge(td, "content_strategist")
            knowledge_dir = Path(td) / "knowledge"
            assert not knowledge_dir.exists(), "should not create dir for missing bank"
        print("missing bank dir no error: PASS")
    finally:
        KNOWLEDGE_MAP["content_strategist"] = original


def test_stale_symlink_replaced():
    """If a stale symlink already exists, it gets replaced."""
    role = "content_strategist"
    bank = ROOT / KNOWLEDGE_MAP[role][0]
    if not bank.is_dir():
        print("SKIP: stale symlink test (bank not on disk)")
        return

    with tempfile.TemporaryDirectory() as td:
        # Create a stale symlink pointing at /tmp/nothing
        dst = Path(td) / "knowledge" / bank.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to("/tmp/this-does-not-exist-12345")
        assert dst.is_symlink() and not dst.exists(), "precondition: stale symlink"

        _symlink_knowledge(td, role)
        assert dst.is_symlink(), "symlink should still exist"
        assert dst.resolve().is_dir(), "symlink should now point at real dir"
    print("stale symlink replaced: PASS")


if __name__ == "__main__":
    test_mapped_role_gets_symlink()
    test_multi_bank_role_gets_every_bank()
    test_unmapped_role_no_error()
    test_missing_bank_dir_no_error()
    test_stale_symlink_replaced()
    print("ALL PASS")
