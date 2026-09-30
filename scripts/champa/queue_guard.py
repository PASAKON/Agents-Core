"""Queue guard for champa.io Unlimited generation runner (CEO 2026-10-01).

Guards parallel jobs (up to 8 in flight) and ensures only free Unlimited
jobs are submitted to prevent credit spend.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class Refused(Exception):
    """Raised when queue guard refuses an action (not free or cap reached)."""


def is_free_label(label: str | None) -> bool:
    """True only when the submit label says Unlimited AND its last integer is 0.

    Example: "ส่งเข้าคิว Unlimited 0" -> True.
    Anything else (a price, no number, empty) is False.
    """
    if not label or not isinstance(label, str):
        return False
    if "unlimited" not in label.lower():
        return False
    integers = re.findall(r"\d+", label)
    if not integers:
        return False
    return int(integers[-1]) == 0


class QueueGuard:
    """Tracks and limits in-flight jobs on champa.io using a jsonl ledger."""

    def __init__(self, max_in_flight: int, ledger: str | Path):
        if isinstance(max_in_flight, bool) or not isinstance(max_in_flight, int):
            raise TypeError(
                f"max_in_flight must be an integer, got {type(max_in_flight).__name__}"
            )
        if not (1 <= max_in_flight <= 8):
            raise ValueError(
                f"max_in_flight must be between 1 and 8, got {max_in_flight}"
            )
        self.max_in_flight = max_in_flight
        self.ledger = Path(ledger)

    def _read_ledger(self) -> tuple[set[str], set[str]]:
        submitted: set[str] = set()
        done: set[str] = set()
        if not self.ledger.exists():
            return submitted, done
        try:
            with open(self.ledger, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        event = row.get("event")
                        cid = str(row.get("clip_id"))
                        if event == "submit":
                            submitted.add(cid)
                        elif event == "done":
                            done.add(cid)
                    except Exception:
                        pass
        except Exception:
            pass
        return submitted, done

    def in_flight(self) -> int:
        """Return the number of submitted jobs that have not finished (no done event)."""
        submitted, done = self._read_ledger()
        return len(submitted - done)

    def submitted_ids(self) -> set[str]:
        """Return the set of all clip IDs that have been submitted."""
        submitted, _ = self._read_ledger()
        return submitted

    def done_ids(self) -> set[str]:
        """Return the set of all clip IDs that have completed."""
        _, done = self._read_ledger()
        return done

    def check(self, label: str) -> None:
        """Verify the label indicates a free job and the queue is not full."""
        if not is_free_label(label):
            raise Refused(f"Label is not free: {label!r}")
        if self.in_flight() >= self.max_in_flight:
            raise Refused(
                f"Queue cap reached: {self.in_flight()} in flight >= {self.max_in_flight}"
            )

    def record_submit(self, clip_id: str, label: str) -> None:
        """Append a submit event to the ledger."""
        row = {
            "event": "submit",
            "clip_id": str(clip_id),
            "label": label,
            "ts": datetime.now().astimezone().isoformat(),
        }
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def record_done(self, clip_id: str, path: str | Path) -> None:
        """Append a done event to the ledger."""
        row = {
            "event": "done",
            "clip_id": str(clip_id),
            "path": str(path),
            "ts": datetime.now().astimezone().isoformat(),
        }
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
