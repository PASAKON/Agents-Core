#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The one CDP-endpoint resolver every Flow tool uses (flow_shoot.py,
flow_upload_element.py, flow_music.py, flow_reupscale.py via FlowBrowser).

Order: the tool's own --cdp/--cdp-url flag, then $FLOW_CDP, then the winbox
Chrome default (see DEFAULT_CDP below).

CEO ruling 2026-09-26 (skill CTO_Flow_Omni1.1_Ops, section "Where Flow runs"):
"Generate คลิป Google Flow ทำบน Window ... ฉันจะใช้ MAC ตัดต่อ Video" — Flow runs
on winbox's Chrome, never the Mac; the Mac is for editing. That rule lives HERE,
in code, not only in the skill: enforce_platform() refuses on darwin unless the
override env var is set. platform/env are injectable so this is unit-testable
without actually running on a Mac — see tests/test_flow_cdp.py.
"""
from __future__ import annotations

import os
import sys
from typing import Mapping

# One Chrome, one profile, one CDP port on winbox for every Flow tool —
# unlike the old per-tool Mac ports (flow_shoot/flow_upload_element used
# 9223, flow_music used 9224), the winbox launcher (windows/flow-chrome-
# debug.cmd) opens a single debug Chrome that all four tools attach to and
# find their own tab in.
DEFAULT_CDP = "http://127.0.0.1:9226"

CEO_LINE = (
    "CEO 2026-09-26: \"Generate คลิป Google Flow ทำบน "
    "Window … ฉันจะใช้ MAC ตัดต่อ "
    "Video\" — Flow runs on winbox's Chrome, never the Mac; the Mac is for "
    "editing. Set FLOW_ALLOW_MAC=1 to override."
)


def pick_cdp_url(cli_arg: str | None = None, env: Mapping[str, str] | None = None) -> str:
    """--cdp/--cdp-url flag > $FLOW_CDP > DEFAULT_CDP. Pure — no platform
    check, so tools and tests can call it freely before a browser attaches."""
    environ = env if env is not None else os.environ
    return cli_arg or environ.get("FLOW_CDP") or DEFAULT_CDP


def enforce_platform(platform: str | None = None, env: Mapping[str, str] | None = None) -> None:
    """HARD (CEO ruling 2026-09-26): refuse to drive Flow from the Mac.

    Raises SystemExit(2) when `platform` (default: sys.platform) is "darwin",
    unless `env` (default: os.environ) has FLOW_ALLOW_MAC=1 — which prints a
    loud warning and lets the caller continue. Call this once, right before a
    real CDP connection is made (FlowBrowser.attach() and each tool's own
    attach()), never at import time: importing these modules must stay safe
    on the Mac (tests run here).
    """
    plat = platform if platform is not None else sys.platform
    environ = env if env is not None else os.environ
    if plat != "darwin":
        return
    if environ.get("FLOW_ALLOW_MAC") == "1":
        print(f"WARNING (FLOW_ALLOW_MAC=1 override): {CEO_LINE}", file=sys.stderr)
        return
    print(f"REFUSED: {CEO_LINE}", file=sys.stderr)
    raise SystemExit(2)


def resolve_cdp(cli_arg: str | None = None, env: Mapping[str, str] | None = None,
                 platform: str | None = None) -> str:
    """enforce_platform() then pick_cdp_url() — the single call each tool's
    real CLI entry point makes to get the CDP URL it will actually connect
    to. Internal control-flow tests (browser stubs, --dry-run of pure
    helpers) should call pick_cdp_url() directly instead, so they are never
    coupled to the machine they happen to run on."""
    enforce_platform(platform=platform, env=env)
    return pick_cdp_url(cli_arg, env=env)
