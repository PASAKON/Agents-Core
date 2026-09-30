"""Higgsfield credit guard (CEO 2026-10-01).

Zero-model pure Python credit guard. Enforces hard caps on paid Higgsfield video
generations and maintains an append-only JSONL spend ledger.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


PURCHASE_WORDS = ("buy", "purchase", "upgrade", "subscribe", "top up")


def parse_price(label: str | None) -> int | None:
    """Parse the charged price from the submit button label.

    The charged price is the LAST integer on the submit button label.
    - 'Generate 80 60' -> 60 (list 80, charged 60)
    - 'UNLIMITED · 140 0' -> 0
    - 'Generate Unlimited' -> 0 (Unlimited with no number = 0)
    - Labels with purchase words ('buy', 'purchase', 'upgrade', 'subscribe', 'top up'),
      or with no number and not unlimited, or empty/whitespace return None.
    """
    if not label or not isinstance(label, str) or not label.strip():
        return None

    lower = label.lower()
    for word in PURCHASE_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", lower):
            return None

    numbers = re.findall(r"\d+", label)
    if numbers:
        return int(numbers[-1])
    if "unlimited" in lower:
        return 0
    return None


class SpendRefused(Exception):
    """Raised when spending is refused due to cap breach or unreadable label."""


class SpendGuard:
    """Guards credit spending against per-clip and total budget caps."""

    def __init__(self, max_per_clip: int, budget: int, ledger: str | Path):
        if max_per_clip is None or budget is None:
            raise TypeError("max_per_clip and budget cannot be None")
        if isinstance(max_per_clip, bool) or isinstance(budget, bool):
            raise TypeError("max_per_clip and budget cannot be booleans")
        if not isinstance(max_per_clip, int) or not isinstance(budget, int):
            raise TypeError("max_per_clip and budget must be integers")
        if max_per_clip <= 0 or budget <= 0:
            raise ValueError("max_per_clip and budget must be positive integers")

        self.max_per_clip = max_per_clip
        self.budget = budget
        self.ledger = Path(ledger)

    def check(self, label: str) -> int:
        """Return the parsed price if within caps, or raise SpendRefused."""
        price = parse_price(label)
        if price is None:
            raise SpendRefused(f"unreadable submit button label: {label!r}")
        if price > self.max_per_clip:
            raise SpendRefused(
                f"price {price} exceeds per-clip cap {self.max_per_clip}"
            )
        current_spent = self.spent()
        if current_spent + price > self.budget:
            raise SpendRefused(
                f"price {price} + already spent {current_spent} exceeds budget {self.budget}"
            )
        return price

    def record(
        self,
        clip_id: str,
        price: int,
        balance_before: int | None = None,
        balance_after: int | None = None,
    ) -> None:
        """Record spend to the ledger, then verify actual balance delta."""
        row = {
            "clip_id": clip_id,
            "price": price,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

        if balance_before is not None and balance_after is not None:
            diff = balance_before - balance_after
            if diff > price:
                raise SpendRefused(
                    f"actual charge {diff} exceeded label price {price}"
                )

    def spent(self) -> int:
        """Return total spend read back from the ledger file."""
        if not self.ledger.exists():
            return 0
        total = 0
        with open(self.ledger, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    total += int(data.get("price", 0))
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
        return total

    def recorded_clip_ids(self) -> set[str]:
        """Return set of clip IDs already recorded in the ledger."""
        if not self.ledger.exists():
            return set()
        done = set()
        with open(self.ledger, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "clip_id" in data:
                        done.add(str(data["clip_id"]))
                except Exception:
                    pass
        return done
