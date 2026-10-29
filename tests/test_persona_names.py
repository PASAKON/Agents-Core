"""26 Oct persona migration; every test exercises behavior absent before migration."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lib import config, session_names as sn
from tools import live_sessions as ls, rename_service as rs, send_to_cxo, whois

PEOPLE = [
    ("cto", "Kavin", "\U0001F468\u200d\U0001F4BB"),
    ("coo", "SomPong", "\U0001F468\U0001F3FD\u200d\U0001F4BC"),
    ("cmo", "Ging", "\U0001F469\U0001F3FB\u200d\U0001F3A8"),
]


@pytest.mark.parametrize("role,persona,emoji", PEOPLE)
def test_builder_and_winbox_json(role, persona, emoji):
    assert config.persona_emoji_for(role) == emoji
    assert sn.clevel_name(role, persona, "contabo") == f"\U0001F310 {role.upper()} ({emoji}: {persona})"
    expected = f"\U0001F5A5\ufe0f {role.upper()} ({emoji}: {persona})"
    assert sn.clevel_name(role, persona, "winbox") == expected
    proc = subprocess.run(
        [sys.executable, "-m", "lib.session_names", "name", "--host", "winbox",
         "--role", role, "--sid", "abcdef12"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"}, check=True,
    )
    assert proc.stdout.isascii()
    assert json.loads(proc.stdout) == expected
    assert sn.clevel_name("cfo", host="contabo") == "\U0001F310 CFO"


@pytest.mark.parametrize("role,persona,emoji", PEOPLE)
def test_readers_and_old_peer_addresses(role, persona, emoji):
    old = f"\U0001F310 {role.upper()} ({persona}) — Main"
    new = f"\U0001F310 {role.upper()} ({emoji}: {persona}) — Main"
    row = {"name": new, "address": new}
    uuid = "00000000-0000-0000-0000-0000abcdef12"
    for name in (old, new):
        assert sn.parse_short(name) == (role, "")
        assert sn.split_name(name)[2].startswith(role.upper())
        assert ls.parse_name(name, uuid) == (role, "abcdef12")
        assert send_to_cxo.resolve_target_role(name) == role
        assert whois.resolve([row], name) == [row]
        assert whois.resolve([row], name.lower()) == [row]
        assert whois.resolve([row], "  " + name.replace(" ", "  ") + " ") == [row]
        assert ls._clean(name, 200) == name
        long = f"CONTABO {sn.split_name(name)[2].split(' — ')[0]} #abcdef12"
        assert ls.parse_name(long, uuid) == (role, "abcdef12")
        assert ls._clean(long, 200) == long
        assert sn.parse_short(long) == (role, "abc")
    assert sn.rule_problem(old, role, "abcdef12", "contabo", persona) == "wrong person emoji"
    assert sn.rule_problem(new, role, "abcdef12", "contabo", persona) is None
    assert send_to_cxo.resolve_target_role(f"CTO ({emoji}: Stranger)").startswith("CTO (")


def test_only_persona_zwj_is_typable():
    name = "\U0001F310 CTO (\U0001F468\u200d\U0001F4BB: Kavin)"
    assert rs._typable(name)
    assert not rs._typable(name + " — hidden\u200dtext")
    assert not rs._typable("\U0001F310 PH#abc (CTO) - hidden\u200dtext")


@pytest.mark.parametrize("role,persona,emoji", PEOPLE)
def test_send_resolves_both_generations_before_routing(monkeypatch, role, persona, emoji):
    monkeypatch.setattr(send_to_cxo, "_ph_owner_session", lambda role: None)

    def active(requested):
        assert requested == role
        raise RuntimeError("resolved target; stop before delivery")

    monkeypatch.setattr(send_to_cxo, "_active_session_id", active)
    for label in (persona, f"{emoji}: {persona}"):
        with pytest.raises(RuntimeError, match="resolved target"):
            send_to_cxo.send(f"\U0001F310 {role.upper()} ({label})", "test")


@pytest.mark.parametrize("name,role", [
    ("\U0001F5A5️ CTO (\U0001F468 \U0001F4BB: Kavin)", "cto"),
    ("\U0001F310 CMO (\U0001F469\U0001F3FB \U0001F3A8: Ging) — topic", "cmo"),
    ("\U0001F310 COO (\U0001F468\U0001F3FD \U0001F4BC: SomPong)", "coo"),
])
def test_persona_with_a_space_for_the_zwj_still_parses(name, role):
    # winbox 29 Oct: "CTO (👨 💻: Kavin)" read as role unknown, so a reboot would not resume it.
    uuid = "c8dfed53-0000-4000-8000-00005" + "7ec0d4e"
    assert ls.parse_name(name, uuid)[0] == role
    assert ls.parse_name("CTO (\U0001F468  \U0001F4BB: Kavin)", uuid)[0] != "cto"
