"""Quota-aware Claude/Z.ai provider routing (GH mooniex-agents#38, phase 2).

At DEV-spawn time, compares live remaining headroom on both providers and
picks whichever has more room, instead of a human flipping the static
DEV_MODEL_PROVIDER flag by hand whenever one pool runs low (the exact
manual toggle in .env as of 2026-08-03, disabled that day because Z.ai's
7-day window hit 100% utilization).

Data sources (both already deployed, both read-only):
  - Claude: SSH to the VPS usage monitor — refreshes independently every
    4 min via systemd timer. Read-only SSH diagnostics on this VPS already
    has standing CEO approval.
  - Z.ai: the deployed usage webhook (already-parsed CREDIT_LIMIT/unit
    response — do not re-parse the raw api.z.ai endpoint here, that
    parsing already lives in mooniex-scriptable/server/zai-usage/monitor.py
    and duplicating it risks getting the unit codes wrong).

Fails safe to "claude" whenever either source is unreachable, slow, or
returns something unparseable — this must never block or crash a spawn.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from urllib.error import URLError

CLAUDE_SSH_HOST = "mooniex-vps"
CLAUDE_SSH_CMD = "python3 /opt/claude-usage-monitor/monitor.py --status"
ZAI_USAGE_URL = "https://webhook.mooniex.com/zai-usage"
_TIMEOUT_SECONDS = 8


def _headroom(utilization_pct: float) -> float:
    return 100.0 - float(utilization_pct)


def fetch_claude_headroom() -> dict | None:
    """{"five_hour": headroom_pct, "seven_day": headroom_pct} or None."""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes",
             CLAUDE_SSH_HOST, CLAUDE_SSH_CMD],
            capture_output=True, text=True, timeout=_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return {
            "five_hour": _headroom(data["five_hour"]["utilization"]),
            "seven_day": _headroom(data["seven_day"]["utilization"]),
        }
    except (subprocess.SubprocessError, ValueError, KeyError, OSError):
        return None


def fetch_zai_headroom(usage_token: str | None) -> dict | None:
    """{"five_hour": headroom_pct, "seven_day": headroom_pct} or None."""
    if not usage_token:
        return None
    try:
        url = f"{ZAI_USAGE_URL}?k={usage_token}"
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read())
        return {
            "five_hour": _headroom(data["five_hour"]["utilization"]),
            "seven_day": _headroom(data["seven_day"]["utilization"]),
        }
    except (URLError, TimeoutError, ValueError, KeyError, OSError):
        return None


def pick_provider(
    zai_usage_token: str | None,
    *,
    _claude_fetch=fetch_claude_headroom,
    _zai_fetch=fetch_zai_headroom,
) -> str:
    """Return "zai" or "claude".

    A provider's effective headroom is the tighter (lower) of its own two
    windows (5h / 7d) — a provider that's exhausted on either axis is out,
    regardless of how much room it has on the other. Whichever provider
    has more effective headroom wins; ties, or any fetch failure on
    either side, fall back to "claude" (the safe default — never blocks
    the spawn on a network blip).

    _claude_fetch / _zai_fetch are injectable for tests only.
    """
    claude = _claude_fetch()
    zai = _zai_fetch(zai_usage_token)
    if claude is None or zai is None:
        return "claude"
    claude_effective = min(claude["five_hour"], claude["seven_day"])
    zai_effective = min(zai["five_hour"], zai["seven_day"])
    return "zai" if zai_effective > claude_effective else "claude"
