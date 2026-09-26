"""tools/flow_cdp.py — the single CDP-endpoint resolver every Flow tool uses.

Covers: --cdp/--cdp-url flag > $FLOW_CDP > default ordering, the darwin
refusal (CEO ruling 2026-09-26, task-9a33b2a3), and the FLOW_ALLOW_MAC=1
override. platform/env are injected everywhere so none of this depends on
the machine actually running the test.
"""
from __future__ import annotations

import pytest

from tools import flow_cdp


# ── pick_cdp_url: flag > env > default ──────────────────────────────────────

def test_pick_cdp_url_flag_wins_over_everything():
    assert flow_cdp.pick_cdp_url("http://flag:1", env={"FLOW_CDP": "http://env:2"}) == "http://flag:1"


def test_pick_cdp_url_env_wins_over_default():
    assert flow_cdp.pick_cdp_url(None, env={"FLOW_CDP": "http://env:2"}) == "http://env:2"


def test_pick_cdp_url_default_when_nothing_set():
    assert flow_cdp.pick_cdp_url(None, env={}) == flow_cdp.DEFAULT_CDP


def test_pick_cdp_url_empty_flag_falls_through_to_env():
    # argparse can hand back "" for an explicitly empty --cdp-url; treat it
    # the same as not-given rather than trying to connect to "".
    assert flow_cdp.pick_cdp_url("", env={"FLOW_CDP": "http://env:2"}) == "http://env:2"


def test_pick_cdp_url_reads_real_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("FLOW_CDP", "http://real-env:3")
    assert flow_cdp.pick_cdp_url(None) == "http://real-env:3"


# ── enforce_platform: the CEO's Mac rule ────────────────────────────────────

def test_enforce_platform_allows_non_darwin():
    flow_cdp.enforce_platform(platform="win32", env={})
    flow_cdp.enforce_platform(platform="linux", env={})  # winbox-via-ssh, Contabo


def test_enforce_platform_refuses_darwin_by_default():
    with pytest.raises(SystemExit) as exc_info:
        flow_cdp.enforce_platform(platform="darwin", env={})
    assert exc_info.value.code == 2


def test_enforce_platform_refusal_message_names_the_ceo_rule(capsys):
    with pytest.raises(SystemExit):
        flow_cdp.enforce_platform(platform="darwin", env={})
    err = capsys.readouterr().err
    assert "winbox" in err
    assert "never the Mac" in err


def test_enforce_platform_allow_mac_override_does_not_raise():
    flow_cdp.enforce_platform(platform="darwin", env={"FLOW_ALLOW_MAC": "1"})


def test_enforce_platform_allow_mac_override_prints_loud_warning(capsys):
    flow_cdp.enforce_platform(platform="darwin", env={"FLOW_ALLOW_MAC": "1"})
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "winbox" in err


@pytest.mark.parametrize("value", ["0", "true", "yes", "", "TRUE"])
def test_enforce_platform_only_exact_string_1_overrides(value):
    with pytest.raises(SystemExit):
        flow_cdp.enforce_platform(platform="darwin", env={"FLOW_ALLOW_MAC": value})


def test_enforce_platform_reads_real_sys_platform_by_default(monkeypatch):
    monkeypatch.setattr(flow_cdp.sys, "platform", "darwin")
    with pytest.raises(SystemExit):
        flow_cdp.enforce_platform(env={"FLOW_ALLOW_MAC": "0"})


# ── resolve_cdp: enforce_platform() then pick_cdp_url() ─────────────────────

def test_resolve_cdp_refuses_before_picking_a_url_on_darwin():
    with pytest.raises(SystemExit):
        flow_cdp.resolve_cdp("http://flag:1", env={}, platform="darwin")


def test_resolve_cdp_returns_picked_url_on_winbox():
    got = flow_cdp.resolve_cdp(None, env={"FLOW_CDP": "http://winbox:9226"}, platform="win32")
    assert got == "http://winbox:9226"


def test_resolve_cdp_allows_darwin_with_override_and_still_picks_url():
    got = flow_cdp.resolve_cdp(
        "http://mac-debug:9223", env={"FLOW_ALLOW_MAC": "1"}, platform="darwin")
    assert got == "http://mac-debug:9223"
