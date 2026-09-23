"""ADR 0022 §2 / playbook Wave 3 Phase 1 -- plugin-level skill visibility.

Scripts under scripts/ per pytest.ini (ADR 0021 §2/§3); no tests/ directory
exists and pytest never looks there.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.config import agents, role as get_role  # noqa: E402
from runners import worker_init  # noqa: E402

PROFILE_DIR = ROOT / "policies" / "skill-visibility"
WORKER_BASELINE = PROFILE_DIR / "worker-baseline.json"

# ecc@ecc ships GateGuard's gateguard-fact-force hook (and others) inside its
# own plugin bundle's hooks/hooks.json. `enabledPlugins: false` disables the
# whole bundle, hooks included, not just its skills -- verified live
# 2026-09-01 on Claude Code 2.1.252 (docs/WAVE3-SKILL-VISIBILITY.md). A
# worker-visibility profile must never disable it.
UNSAFE_TO_DISABLE = {"ecc@ecc"}


def _load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_worker_baseline_is_valid_json_shape():
    data = _load_profile(WORKER_BASELINE)
    assert set(data.keys()) == {"enabledPlugins"}
    plugins = data["enabledPlugins"]
    assert plugins, "profile must not be empty"
    for key, value in plugins.items():
        assert "@" in key, f"key {key!r} must be <plugin>@<marketplace>"
        assert value is False, f"{key} must be false -- Phase 1 only disables"


def test_worker_baseline_never_disables_gateguard_bundle():
    data = _load_profile(WORKER_BASELINE)
    hit = set(data["enabledPlugins"]) & UNSAFE_TO_DISABLE
    assert not hit, f"profile disables plugin(s) whose hooks we depend on: {hit}"


def test_worker_baseline_keys_are_subset_of_installed_plugins():
    """Keys must come verbatim from ~/.claude/plugins/installed_plugins.json,
    never synthesized. Skips if that file is absent -- a different
    machine/CI may have a different plugin set installed."""
    installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not installed_path.is_file():
        pytest.skip("no ~/.claude/plugins/installed_plugins.json on this machine")
    installed = set(json.loads(installed_path.read_text(encoding="utf-8")).get("plugins", {}))
    keys = set(_load_profile(WORKER_BASELINE)["enabledPlugins"])
    assert keys <= installed, f"keys not in installed_plugins.json: {keys - installed}"


def test_every_role_has_skills_profile():
    roles = agents()["roles"]
    missing = [r for r, v in roles.items() if "skills_profile" not in v]
    assert not missing, f"roles missing skills_profile: {missing}"
    valid = {"worker-baseline", "all"}
    bad = {r: v["skills_profile"] for r, v in roles.items() if v["skills_profile"] not in valid}
    assert not bad, f"unknown skills_profile values: {bad}"


def test_cto_profile_is_all():
    assert get_role("cto")["skills_profile"] == "all"


def test_all_profile_emits_no_overlay():
    """CEO decision (ADR 0022 §2): CTO sees everything, and that decision
    costs zero code -- 'all' produces no enabledPlugins key at all, not an
    empty dict and not every plugin set true."""
    assert worker_init.skill_visibility_overlay("cto") is None
    assert worker_init.skill_visibility_overlay("ceo") is None


def test_worker_baseline_profile_overlay_matches_file():
    overlay = worker_init.skill_visibility_overlay("developer")
    assert overlay == _load_profile(WORKER_BASELINE)["enabledPlugins"]


def test_unregistered_role_falls_back_to_all():
    assert worker_init.skill_visibility_overlay("totally-unknown-role-xyz") is None


def test_write_dev_settings_cto_emits_no_enabledplugins_key(tmp_path):
    """Proves the acceptance criterion literally: a cto-profile write is
    byte-identical to a plain call with no role at all."""
    worktree_a = tmp_path / "a"
    worktree_b = tmp_path / "b"
    worker_init._write_dev_settings(str(worktree_a), "cto")
    worker_init._write_dev_settings(str(worktree_b), None)
    settings_a = (worktree_a / ".claude" / "settings.local.json").read_text()
    settings_b = (worktree_b / ".claude" / "settings.local.json").read_text()
    assert settings_a == settings_b
    assert "enabledPlugins" not in settings_a


def test_write_dev_settings_developer_adds_overlay(tmp_path):
    worktree = tmp_path / "w"
    worker_init._write_dev_settings(str(worktree), "developer")
    settings = json.loads((worktree / ".claude" / "settings.local.json").read_text())
    assert settings["enabledPlugins"] == _load_profile(WORKER_BASELINE)["enabledPlugins"]


def test_skill_added_to_base_worker_tools():
    assert "Skill" in worker_init._BASE_WORKER_TOOLS
    allowed, _ = worker_init.worker_tool_grants("developer")
    assert allowed.count("Skill") == 1
    allowed_wd, _ = worker_init.worker_tool_grants("web_designer")
    assert allowed_wd.count("Skill") == 1  # not duplicated by the old append
    allowed_bo, _ = worker_init.worker_tool_grants("browser_operator")
    assert allowed_bo.count("Skill") == 1


def test_root_is_derived_not_hardcoded(monkeypatch, tmp_path):
    """Hard constraint: never hardcode /Users/gob/MoonieXHQ/Agents/Core (Contabo
    runs the same repo at /opt/mooniex-agents). Proves the profile lookup
    resolves relative to worker_init.ROOT by pointing ROOT at a fake root
    with different content and confirming that content -- not the real
    repo's -- comes back."""
    fake_root = tmp_path / "fake-root-not-a-real-agents-checkout"
    fake_profile_dir = fake_root / "policies" / "skill-visibility"
    fake_profile_dir.mkdir(parents=True)
    fake_payload = {"enabledPlugins": {"only-in-fake-root@nowhere": False}}
    (fake_profile_dir / "worker-baseline.json").write_text(json.dumps(fake_payload))

    monkeypatch.setattr(worker_init, "ROOT", fake_root)
    overlay = worker_init.skill_visibility_overlay("developer")
    assert overlay == fake_payload["enabledPlugins"]
    assert "only-in-fake-root@nowhere" not in _load_profile(WORKER_BASELINE)["enabledPlugins"]


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")
def test_enabledplugins_mechanism_still_honoured_in_local_settings(tmp_path):
    """VERSION GUARD.

    Exercises the real, installed `claude` binary's actual settings-merge
    behaviour (not a version-string check) so a Claude Code upgrade that
    silently changes how `enabledPlugins` merges across settings sources
    fails this test loudly instead of shipping a false sense of visibility
    control.

    If this test starts failing: STOP shipping worker-baseline profiles as
    load-bearing. Re-run the manual A/B in docs/WAVE3-SKILL-VISIBILITY.md
    ("Reproducing the measurement") against the new Claude Code version
    before trusting `enabledPlugins` again, and re-verify the
    GateGuard-hooks finding too -- a version bump could change plugin
    bundling behaviour independently of the settings-merge precedence.
    """
    installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not installed_path.is_file():
        pytest.skip("no plugins installed on this machine to test against")
    installed = json.loads(installed_path.read_text(encoding="utf-8")).get("plugins", {})
    candidates = [k for k in installed if k not in UNSAFE_TO_DISABLE]
    if not candidates:
        pytest.skip("no safe-to-disable plugin installed to test against")
    target = candidates[0]

    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir(parents=True)
    (settings_dir / "settings.local.json").write_text(
        json.dumps({"enabledPlugins": {target: False}})
    )
    out = subprocess.run(
        ["claude", "plugin", "list", "--json"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0, out.stderr
    plugins = json.loads(out.stdout)
    row = next((p for p in plugins if p["id"] == target), None)
    assert row is not None, f"{target} not found in `claude plugin list` output"
    assert row["enabled"] is False, (
        f"enabledPlugins:false in settings.local.json did not disable {target} -- "
        "the settings-merge mechanism this feature depends on has changed. "
        "See the version-guard docstring above."
    )
