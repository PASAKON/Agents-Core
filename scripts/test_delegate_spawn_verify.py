"""GH #64 — the spawn watchdog must actually get to run.

`_verify_claimed` is the only thing standing between a DEV that never started
and a task row that sits `pending` forever while delegate logs "DEV spawned".
It sleeps CLAIM_VERIFY_DELAY_S (25s) before it checks anything, so it is
maximally exposed to the asyncio footgun it hit in production: the event loop
holds only a *weak* reference to what `create_task()` returns, and a task
nothing else references can be collected mid-await.

Not theoretical — it fired 4 times in a row on task-08c30235 on 2026-08-14.
Every attempt logged success, no warn/respawn/error ever appeared, and the row
never left `pending`.

These tests pin the fix (a strong reference held until completion). They do not
spawn iTerm, touch the real DB, or sleep for 25 seconds.
"""
from __future__ import annotations

import asyncio
import gc
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.delegate as delegate  # noqa: E402


def test_spawn_background_survives_garbage_collection() -> None:
    """The regression itself: a bare create_task() whose Task nobody holds can
    be collected before it finishes. _spawn_background must keep it alive."""
    ran: list[str] = []

    async def slow_worker() -> None:
        # Any await point is a chance for the GC to reclaim an unreferenced
        # task. The production coroutine sleeps 25s here.
        await asyncio.sleep(0.05)
        ran.append("finished")

    async def scenario() -> None:
        delegate._spawn_background(slow_worker())
        # Drop every local handle and force a collection — the exact
        # condition that killed _verify_claimed in production.
        gc.collect()
        await asyncio.sleep(0.2)

    asyncio.run(scenario())
    assert ran == ["finished"], (
        "background task did not finish — it was collected mid-await, which is "
        "the GH #64 failure mode"
    )


def test_spawn_background_registers_then_releases_the_reference() -> None:
    """Held while running (that is the point), released when done (so the set
    does not grow without bound in a long-lived MCP server process)."""
    async def scenario() -> None:
        async def worker() -> None:
            await asyncio.sleep(0.05)

        task = delegate._spawn_background(worker())
        assert task in delegate._BACKGROUND_TASKS, "reference not held while running"
        await task
        # done_callback runs on the next loop pass.
        await asyncio.sleep(0)
        assert task not in delegate._BACKGROUND_TASKS, "reference leaked after completion"

    asyncio.run(scenario())


def test_spawn_background_releases_the_slot_on_failure() -> None:
    """A crashing background task must still release its slot, or one bad
    kickoff pins an entry forever."""
    async def scenario() -> None:
        async def boom() -> None:
            raise RuntimeError("kaboom")

        task = delegate._spawn_background(boom())
        with pytest.raises(RuntimeError):
            await task
        await asyncio.sleep(0)
        assert task not in delegate._BACKGROUND_TASKS

    asyncio.run(scenario())


def test_no_bare_create_task_remains_at_the_fire_and_forget_sites() -> None:
    """Guard against a future edit reintroducing the bug. The only legitimate
    `asyncio.create_task(` in this module is the one inside _spawn_background;
    every other call site must go through the helper."""
    src = (ROOT / "tools" / "delegate.py").read_text(encoding="utf-8")
    assert src.count("asyncio.create_task(") == 1, (
        "found a bare asyncio.create_task() outside _spawn_background — "
        "fire-and-forget coroutines must hold a strong reference (GH #64)"
    )
    for name in ("_auto_kickoff", "_verify_claimed"):
        assert f"asyncio.create_task({name}(" not in src, (
            f"{name} is scheduled without a strong reference again (GH #64)"
        )
