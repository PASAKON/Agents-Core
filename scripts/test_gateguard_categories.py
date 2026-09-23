"""Tests for the GateGuard category-bypass wrapper.

Run via:  python scripts/test_gateguard_categories.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gateguard_categories as gc

# Sample path under a real registered wiki root, read from config/wikis.yaml
# rather than hardcoded — this test must keep working no matter which repo
# backs the default namespace.
_wiki_registry = yaml.safe_load((ROOT / "config" / "wikis.yaml").read_text())
_default_ns = _wiki_registry["default"]
_MOONIEX_WIKI_ROOT = next(w["path"] for w in _wiki_registry["wikis"] if w["ns"] == _default_ns)
_SAMPLE_WIKI_FILE = f"{_MOONIEX_WIKI_ROOT}/IRON-RULES.md"

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _isolate_state(tmp_root: Path):
    """Context manager that redirects STATE_DIR and pins the session key."""
    class _Ctx:
        def __enter__(self):
            self.old_dir = gc.STATE_DIR
            # Use the same path the subprocess will compute: HOME/.claude/state
            self.state_dir = tmp_root / ".claude" / "state"
            gc.STATE_DIR = self.state_dir
            self.backup = {k: os.environ.pop(k, None)
                           for k in ("CLAUDE_SESSION_ID", "ECC_SESSION_ID", "CLAUDE_PROJECT_DIR")}
            os.environ["CLAUDE_SESSION_ID"] = "test-session-fixed"
            return self.state_dir

        def __exit__(self, *_):
            gc.STATE_DIR = self.old_dir
            for k, v in self.backup.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)
    return _Ctx()


# --- Test 1 ---
def test_fresh_state_returns_false():
    with tempfile.TemporaryDirectory() as td:
        with _isolate_state(Path(td)):
            result = gc.is_category_presented("wiki_edit")
    _mark(result is False,
          "fresh state → is_category_presented('wiki_edit') is False")


# --- Test 2 ---
def test_mark_then_check_returns_true():
    with tempfile.TemporaryDirectory() as td:
        with _isolate_state(Path(td)):
            gc.mark_category_presented("wiki_edit")
            result = gc.is_category_presented("wiki_edit")
    _mark(result is True,
          "after mark_category_presented → is_category_presented returns True")


# --- Test 3 ---
def test_expired_state_returns_false():
    with tempfile.TemporaryDirectory() as td:
        with _isolate_state(Path(td)):
            gc.mark_category_presented("wiki_edit")
            future_time = time.time() + 31 * 60
            with patch("gateguard_categories.time") as mock_time:
                mock_time.time.return_value = future_time
                result = gc.is_category_presented("wiki_edit")
    _mark(result is False,
          "state older than 30min → is_category_presented returns False (expired)")


# --- Test 4 ---
def test_category_for_wiki_path():
    result = gc.category_for(_SAMPLE_WIKI_FILE)
    _mark(result == "wiki_edit",
          f"category_for({_SAMPLE_WIKI_FILE!r}) == 'wiki_edit'")


# --- Test 5 ---
def test_category_for_unknown_path():
    result = gc.category_for("/Users/gob/random/file.md")
    _mark(result is None,
          "category_for('/Users/gob/random/file.md') is None")


# --- ADR 0028 step 4b hazard #2: logical vs physical ------------------------

def test_agents_config_pattern_is_root_derived_not_hardcoded():
    """The old code hardcoded '/Users/gob/MoonieXHQ/Agents/Core/config/' as a
    literal regex; it must now be built from ROOT (this repo's own actual
    location, wherever that is), so a path under the CURRENT root's config/
    matches regardless of what ROOT happens to resolve to on this machine."""
    sample = str(gc.ROOT / "config" / "sample.yaml")
    _mark(gc.category_for(sample) == "agents_config",
          f"category_for({sample!r}) == 'agents_config' (ROOT-derived, not hardcoded)")


def _rebuild_categories():
    gc.CATEGORIES[:] = [
        ("wiki_edit", gc._wiki_edit_pattern()),
        ("agents_config", gc._agents_subdir_pattern("config")),
        ("agents_roles", gc._agents_subdir_pattern("roles")),
        ("memory", gc.CATEGORIES[3][1]),
        ("claudemd", gc.CATEGORIES[4][1]),
    ]


def test_category_for_agents_config_via_symlink_alias():
    """A config/ file reached through a compat symlink alias (the OLD
    logical path kept working after a migration step) must classify the
    same as the physical path — checked via the file's own realpath."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        physical_root = td_path / "physical-agents"
        (physical_root / "config").mkdir(parents=True)
        (physical_root / "config" / "sample.yaml").write_text("k: v\n")
        logical_alias = td_path / "logical-agents"
        logical_alias.symlink_to(physical_root)

        old_root = gc.ROOT
        try:
            gc.ROOT = physical_root
            _rebuild_categories()
            via_logical = str(logical_alias / "config" / "sample.yaml")
            result = gc.category_for(via_logical)
        finally:
            gc.ROOT = old_root
            _rebuild_categories()
    _mark(result == "agents_config",
          "category_for(logical-symlink path) == 'agents_config' (realpath fallback)")


# --- Test 6a ---
def test_session_key_uses_claude_session_id():
    backup = {k: os.environ.pop(k, None)
              for k in ("CLAUDE_SESSION_ID", "ECC_SESSION_ID")}
    os.environ["CLAUDE_SESSION_ID"] = "abc-123"
    try:
        key = gc.session_key()
        _mark(key == "abc-123",
              "CLAUDE_SESSION_ID='abc-123' → session_key() == 'abc-123'")
    finally:
        for k, v in backup.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


# --- Test 6b ---
def test_session_key_proj_hash_fallback():
    backup = {k: os.environ.pop(k, None)
              for k in ("CLAUDE_SESSION_ID", "ECC_SESSION_ID", "CLAUDE_PROJECT_DIR")}
    try:
        key = gc.session_key()
        expected_prefix = "proj-"
        _mark(key.startswith(expected_prefix) and len(key) == len(expected_prefix) + 24,
              f"no env vars → session_key() has 'proj-<24hex>' shape: {key!r}")
    finally:
        for k, v in backup.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


def _run_pre_hook(payload: dict, home_dir: str) -> str:
    """Run the pre-hook script with a given HOME, return stripped stdout."""
    pre_hook = SCRIPTS / "hook-gateguard-category-pre.py"
    env = {
        "CLAUDE_SESSION_ID": "test-session-fixed",
        "HOME": home_dir,
        "PATH": os.environ.get("PATH", ""),
    }
    result = subprocess.run(
        [sys.executable, str(pre_hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


# --- Test 7 ---
def test_pre_hook_allows_when_category_presented():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        with _isolate_state(home):
            gc.mark_category_presented("wiki_edit")

        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": _SAMPLE_WIKI_FILE},
        }
        stdout = _run_pre_hook(payload, str(home))

    try:
        data = json.loads(stdout)
        decision = (data.get("hookSpecificOutput") or {}).get("permissionDecision")
        _mark(decision == "allow",
              "pre-hook with presented category → permissionDecision == 'allow'")
    except Exception:
        _mark(False, f"pre-hook with presented category → bad stdout: {stdout!r}")


# --- Test 8 ---
def test_pre_hook_passthrough_when_category_not_presented():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": _SAMPLE_WIKI_FILE},
        }
        stdout = _run_pre_hook(payload, str(home))

    _mark(stdout == "",
          "pre-hook before marking → empty stdout (pass-through to ECC)")


# --- Test 9 ---
def test_pre_hook_passthrough_mixed_paths():
    """MultiEdit with one presented wiki path + one unknown-category path → pass-through."""
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        with _isolate_state(home):
            gc.mark_category_presented("wiki_edit")

        payload = {
            "tool_name": "MultiEdit",
            "tool_input": {
                "edits": [
                    {"file_path": _SAMPLE_WIKI_FILE},
                    {"file_path": "/Users/gob/random/unknown-file.py"},
                ]
            },
        }
        stdout = _run_pre_hook(payload, str(home))

    _mark(stdout == "",
          "multi-edit with one unknown-category path → empty stdout (no short-circuit)")


def main() -> int:
    print("Running GateGuard category tests...\n")
    test_fresh_state_returns_false()
    test_mark_then_check_returns_true()
    test_expired_state_returns_false()
    test_category_for_wiki_path()
    test_category_for_unknown_path()
    test_agents_config_pattern_is_root_derived_not_hardcoded()
    test_category_for_agents_config_via_symlink_alias()
    test_session_key_uses_claude_session_id()
    test_session_key_proj_hash_fallback()
    test_pre_hook_allows_when_category_presented()
    test_pre_hook_passthrough_when_category_not_presented()
    test_pre_hook_passthrough_mixed_paths()

    total = 12
    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'} ({total - _failures}/{total})")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
