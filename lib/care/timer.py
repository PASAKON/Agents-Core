"""Hourly care scheduler; no process spawning or network client.

The trusted host supplies a deduplicating session wake adapter and stop Event.
No timer is installed or started at import time.
"""
from datetime import timedelta

from .pipeline import TH, utc


def next_round(now):
    local = utc(now).astimezone(TH)
    candidate = local.replace(minute=0, second=0, microsecond=0)
    if candidate < local:
        candidate += timedelta(hours=1)
    if candidate.hour < 8:
        candidate = candidate.replace(hour=8)
    elif candidate.hour > 22:
        candidate = (candidate + timedelta(days=1)).replace(hour=8)
    return candidate


def run_timer(pipeline, wake, stop):
    """Wait interruptibly until the next round; stop.wait is injectable in tests.

    Failed wake calls leave durable pending rounds. The supervisor may restart
    this loop; the adapter deduplicates the stable round ID after ambiguity.
    """
    while not stop.is_set():
        now = utc(pipeline.clock())
        due = next_round(now)
        if stop.wait(max(0, (due - now).total_seconds())):
            return
        pipeline.tick(wake)
        # Move beyond this minute even when a frozen fixture clock is supplied.
        if stop.wait(60):
            return
