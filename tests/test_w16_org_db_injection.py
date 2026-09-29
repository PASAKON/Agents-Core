"""Org Mesh W1.6 (task-719e0c56): ORG_DB_URL reaches every org MCP server through
scripts/hub/with-org-db-env.sh, chosen by the generators, never written into a
tracked file (docs/design/tasks-db-hub.md §3.3).

Everything runs against a FAKE env file in tmp_path (MOONIEX_ORG_DB_ENV) and a
fake Agents root; the real ~/.config/mooniex/org-db.env is never opened, and an
autouse fixture points MOONIEX_ORG_DB_ENV at a missing file so a test that forgets
to set it cannot fall through to the real one.
"""
from __future__ import annotations

import builtins
import importlib.util
import json
import pathlib
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

import cxo_mcp_config as cxo  # noqa: E402
import lib.worker_mcp_config as wmc  # noqa: E402

SENTINEL = "SENTINEL-W16"
ENV_BODY = f"ORG_DB_URL=postgresql://fake:{SENTINEL}@127.0.0.1:1/x\n"


@pytest.fixture(autouse=True)
def _never_the_real_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MOONIEX_ORG_DB_ENV", str(tmp_path / "no-such-org-db.env"))


@pytest.fixture
def root(tmp_path):
    """A fake Agents root: venv python + the wrapper script, nothing else."""
    r = tmp_path / "agents"
    (r / ".venv" / "bin").mkdir(parents=True)
    (r / ".venv" / "bin" / "python").write_text("")
    (r / "scripts" / "hub").mkdir(parents=True)
    wrapper = r / "scripts" / "hub" / "with-org-db-env.sh"
    wrapper.write_text('#!/usr/bin/env bash\nexec "$@"\n')
    wrapper.chmod(0o755)
    return r


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    f = tmp_path / "org-db.env"
    f.write_text(ENV_BODY)
    monkeypatch.setenv("MOONIEX_ORG_DB_ENV", str(f))
    return f


def _wrapper(root: Path) -> str:
    return str(root / "scripts" / "hub" / "with-org-db-env.sh")


def _py(root: Path) -> str:
    return str(root / ".venv" / "bin" / "python")


def _plain_cxo_org(root: Path) -> dict:
    return {
        "command": _py(root),
        "args": ["-m", "runners.cto_mcp_server"],
        "cwd": str(root),
        "env": {"PYTHONUNBUFFERED": "1"},
    }


def _plain_worker_org(root: Path) -> dict:
    return {
        "command": _py(root),
        "args": [f"{root}/runners/worker_mcp_server.py"],
        "cwd": str(root),
        "env": {"PYTHONUNBUFFERED": "1"},
    }


def _worker(root: Path) -> dict:
    """Worker config for `root` from the real tracked template. The LungNote
    server is dropped (no index.js on the fake root) with one stderr line."""
    return wmc.generate(root, lungnote_js=str(root / "no-index.js"))


# ---------------------------------------------------------------- env file present

def test_cxo_org_entry_uses_the_wrapper_when_the_env_file_exists(root, env_file):
    entry = cxo._build("org", str(root))

    assert entry["command"] == _wrapper(root)
    assert entry["args"] == [_py(root), "-m", "runners.cto_mcp_server"]
    assert entry["cwd"] == str(root)
    assert entry["env"] == {"PYTHONUNBUFFERED": "1"}
    assert SENTINEL not in json.dumps(entry)


def test_cxo_generated_file_carries_no_secret(root, env_file, tmp_path, monkeypatch):
    out = tmp_path / "cto-mcp.json"
    monkeypatch.setattr(sys, "argv", ["cxo_mcp_config.py", "--servers", "org",
                                      "--root", str(root), "--out", str(out)])

    assert cxo.main() == 0

    text = out.read_text()
    assert SENTINEL not in text and "ORG_DB_URL" not in text
    assert json.loads(text)["mcpServers"]["org"]["command"] == _wrapper(root)


def test_worker_org_entry_uses_the_wrapper_when_the_env_file_exists(root, env_file):
    generated = _worker(root)

    org = generated["mcpServers"]["org"]
    assert org["command"] == _wrapper(root)
    assert org["args"] == [_py(root), f"{root}/runners/worker_mcp_server.py"]
    assert org["cwd"] == str(root)
    assert org["env"] == {"PYTHONUNBUFFERED": "1"}
    assert SENTINEL not in json.dumps(generated) and "ORG_DB_URL" not in json.dumps(generated)


def test_the_two_generators_agree_on_the_wrapper_and_the_python(root, env_file):
    cxo_org = cxo._build("org", str(root))
    worker_org = _worker(root)["mcpServers"]["org"]

    assert cxo_org["command"] == worker_org["command"]
    assert cxo_org["args"][0] == worker_org["args"][0]


def test_the_env_file_is_never_opened(root, env_file, monkeypatch):
    """Existence only: a read of the secret file would raise here."""
    real_open, real_path_open = builtins.open, pathlib.Path.open

    def guarded(path, *a, **kw):
        if str(path) == str(env_file):
            raise AssertionError("the env file was opened")
        return real_open(path, *a, **kw)

    def guarded_path_open(self, *a, **kw):
        if str(self) == str(env_file):
            raise AssertionError("the env file was opened")
        return real_path_open(self, *a, **kw)

    monkeypatch.setattr(builtins, "open", guarded)
    monkeypatch.setattr(pathlib.Path, "open", guarded_path_open)

    assert cxo._build("org", str(root))["command"] == _wrapper(root)
    assert _worker(root)["mcpServers"]["org"]["command"] == _wrapper(root)


# ----------------------------------------------------------------- env file absent

def test_no_env_file_leaves_both_entries_exactly_as_before(root):
    assert json.dumps(cxo._build("org", str(root))) == json.dumps(_plain_cxo_org(root))
    assert json.dumps(_worker(root)["mcpServers"]["org"]) == json.dumps(_plain_worker_org(root))


def test_env_file_without_a_wrapper_script_stays_unwrapped(root, env_file):
    (root / "scripts" / "hub" / "with-org-db-env.sh").unlink()

    assert json.dumps(cxo._build("org", str(root))) == json.dumps(_plain_cxo_org(root))
    assert json.dumps(_worker(root)["mcpServers"]["org"]) == json.dumps(_plain_worker_org(root))


def test_default_env_path_is_under_home_when_the_override_is_unset(root, tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".config" / "mooniex").mkdir(parents=True)
    (home / ".config" / "mooniex" / "org-db.env").write_text(ENV_BODY)
    monkeypatch.delenv("MOONIEX_ORG_DB_ENV", raising=False)
    monkeypatch.setenv("HOME", str(home))

    assert cxo._build("org", str(root))["command"] == _wrapper(root)

    (home / ".config" / "mooniex" / "org-db.env").unlink()
    assert cxo._build("org", str(root))["command"] == _py(root)


# --------------------------------------------------------------------------- Windows

def test_windows_stays_unwrapped_even_with_the_env_file(root, env_file, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    assert json.dumps(cxo._build("org", str(root))) == json.dumps(_plain_cxo_org(root))
    assert json.dumps(_worker(root)["mcpServers"]["org"]) == json.dumps(_plain_worker_org(root))


# ------------------------------------------------------------------ already wrapped

def test_an_already_wrapped_template_is_not_wrapped_twice(root, env_file, tmp_path):
    wrapped = {"mcpServers": {"org": {
        "command": f"{wmc.TEMPLATE_ROOT}/scripts/hub/with-org-db-env.sh",
        "args": [wmc.TEMPLATE_PYTHON, f"{wmc.TEMPLATE_ROOT}/runners/worker_mcp_server.py"],
        "cwd": wmc.TEMPLATE_ROOT,
        "env": {"PYTHONUNBUFFERED": "1"},
    }}}
    tpl = tmp_path / "worker.mcp.json"
    tpl.write_text(json.dumps(wrapped))

    org = wmc.generate(root, template=tpl, venv_python=_py(root))["mcpServers"]["org"]

    assert org["command"] == _wrapper(root)
    assert org["args"] == [_py(root), f"{root}/runners/worker_mcp_server.py"]


def test_wrap_org_entry_is_idempotent(root, env_file):
    once = cxo.wrap_org_entry(_plain_cxo_org(root), str(root))

    assert once["command"] == _wrapper(root)
    assert cxo.wrap_org_entry(once, str(root)) == once


def test_an_already_wrapped_entry_is_left_alone_on_a_host_with_no_env_file(root):
    """cutover_flip'd checkout, env file gone: still not touched, never double-wrapped."""
    flipped = {"command": _wrapper(root), "args": [_py(root), "-m", "x"], "cwd": str(root), "env": {}}

    assert cxo.wrap_org_entry(flipped, str(root)) == flipped


# --------------------------------------------------------------------- cutover_flip

TRACKED = ("config/cto.mcp.json", "config/worker.mcp.json", "scripts/cto-claude.sh")
PLIST = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<plist version="1.0">\n<dict>\n'
    "  <key>ProgramArguments</key>\n  <array>\n"
    "    <string>/usr/bin/python3</string>\n    <string>-m</string>\n  </array>\n"
    "</dict>\n</plist>\n"
)


def _flip_module_on_a_copy(tmp_path):
    """cutover_flip.py copied into a tmp tree with copies of the tracked files it
    used to rewrite, and its plists pointed at tmp files. Its ROOT is derived
    from __file__, so on the copy it can only ever see the copy."""
    copy = tmp_path / "copy"
    for rel in TRACKED + ("scripts/hub/cutover_flip.py",):
        (copy / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, copy / rel)
    spec = importlib.util.spec_from_file_location("cutover_flip_copy", copy / "scripts/hub/cutover_flip.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    plists = [tmp_path / "LaunchAgents" / "a.plist", tmp_path / "LaunchAgents" / "b.plist"]
    plists[0].parent.mkdir()
    for p in plists:
        p.write_text(PLIST)
    mod.PLISTS = plists
    return copy, mod, plists


def _snapshot(copy: Path) -> dict:
    return {rel: (copy / rel).read_bytes() for rel in TRACKED}


@pytest.mark.parametrize("argv", [[], ["--apply"]])
def test_cutover_flip_never_touches_tracked_files(tmp_path, capsys, argv):
    copy, mod, plists = _flip_module_on_a_copy(tmp_path)
    before = _snapshot(copy)

    assert mod.main(argv) == 0

    assert _snapshot(copy) == before
    out = capsys.readouterr().out
    assert "mcp.json" not in out and "cto-claude.sh" not in out


def test_cutover_flip_apply_still_flips_the_two_plists_and_dry_run_does_not(tmp_path):
    copy, mod, plists = _flip_module_on_a_copy(tmp_path)

    mod.main([])
    assert all(p.read_text() == PLIST for p in plists)

    mod.main(["--apply"])
    for p in plists:
        text = p.read_text()
        assert text.count(mod.WRAPPER) == 1
        assert text.index(mod.WRAPPER) < text.index("/usr/bin/python3")

    mod.main(["--apply"])  # second run: already flipped, no double insert
    assert all(p.read_text().count(mod.WRAPPER) == 1 for p in plists)


def test_the_shipped_launcher_inputs_carry_no_wrapper_or_env_path():
    """The tracked launcher inputs must not name the wrapper or the env file:
    the generators decide the wrapper per host."""
    for rel in TRACKED:
        text = (ROOT / rel).read_text()
        assert "with-org-db-env" not in text, rel
        assert "org-db.env" not in text, rel
