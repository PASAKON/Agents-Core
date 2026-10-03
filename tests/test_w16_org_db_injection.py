"""Org Mesh W1.6 (task-719e0c56): ORG_DB_URL reaches every org MCP server through
scripts/hub/with-org-db-env.sh, chosen by the generators, never written into a
tracked file (docs/design/tasks-db-hub.md §3.3).

Iteration 2: the env file alone is NOT the cutover (it exists on the Mac and on
Contabo before it). The wrapper needs BOTH the env file AND `org_db: hub` in the
host's node file, so a session started before the CEO's cutover window can never
land on a different ledger than the watchdog, hooks and CLI writes.

Everything runs against a FAKE env file and a FAKE node file in tmp_path
(MOONIEX_ORG_DB_ENV, MOONIEX_NODE_YAML) and a fake Agents root; the real
~/.config/mooniex/org-db.env and node.yaml are never opened, and an autouse
fixture points both overrides at missing files so a test that forgets to set
one cannot fall through to the real one.
"""
from __future__ import annotations

import builtins
import importlib.util
import json
import pathlib
import shutil
import subprocess
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
def _never_the_real_host_files(tmp_path, monkeypatch):
    monkeypatch.setenv("MOONIEX_ORG_DB_ENV", str(tmp_path / "no-such-org-db.env"))
    monkeypatch.setenv("MOONIEX_NODE_YAML", str(tmp_path / "no-such-node.yaml"))
    # W3.4: the Windows route looks for an Infisical credential file; never a real one.
    monkeypatch.setenv("INFISICAL_CRED_DIR", str(tmp_path / "no-such-infisical"))
    monkeypatch.delenv("INFISICAL_USER_CRED_DIR", raising=False)


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


def _write_node(tmp_path, monkeypatch, body: str):
    f = tmp_path / "node.yaml"
    f.write_text(body)
    monkeypatch.setenv("MOONIEX_NODE_YAML", str(f))
    return f


@pytest.fixture
def hub_node(tmp_path, monkeypatch):
    """The switch only: a node file with `org_db: hub` (what cutover-mac.sh --apply writes)."""
    return _write_node(tmp_path, monkeypatch, "host: mac\norg_db: hub\n")


@pytest.fixture
def hub_on(env_file, hub_node):
    """A cut-over host: env file present AND the switch on. Returns the env file path."""
    return env_file


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


def _assert_both_plain(root: Path) -> None:
    assert json.dumps(cxo._build("org", str(root))) == json.dumps(_plain_cxo_org(root))
    assert json.dumps(_worker(root)["mcpServers"]["org"]) == json.dumps(_plain_worker_org(root))


# --------------------------------------------------- hub live: wrapped (both files)

def test_cxo_org_entry_uses_the_wrapper_when_the_hub_is_live(root, hub_on):
    entry = cxo._build("org", str(root))

    assert entry["command"] == _wrapper(root)
    assert entry["args"] == [_py(root), "-m", "runners.cto_mcp_server"]
    assert entry["cwd"] == str(root)
    assert entry["env"] == {"PYTHONUNBUFFERED": "1"}
    assert SENTINEL not in json.dumps(entry)


def test_cxo_generated_file_carries_no_secret(root, hub_on, tmp_path, monkeypatch):
    out = tmp_path / "cto-mcp.json"
    monkeypatch.setattr(sys, "argv", ["cxo_mcp_config.py", "--servers", "org",
                                      "--root", str(root), "--out", str(out)])

    assert cxo.main() == 0

    text = out.read_text()
    assert SENTINEL not in text and "ORG_DB_URL" not in text
    assert json.loads(text)["mcpServers"]["org"]["command"] == _wrapper(root)


def test_worker_org_entry_uses_the_wrapper_when_the_hub_is_live(root, hub_on):
    generated = _worker(root)

    org = generated["mcpServers"]["org"]
    assert org["command"] == _wrapper(root)
    assert org["args"] == [_py(root), f"{root}/runners/worker_mcp_server.py"]
    assert org["cwd"] == str(root)
    assert org["env"] == {"PYTHONUNBUFFERED": "1"}
    assert SENTINEL not in json.dumps(generated) and "ORG_DB_URL" not in json.dumps(generated)


def test_the_two_generators_agree_on_the_wrapper_and_the_python(root, hub_on):
    cxo_org = cxo._build("org", str(root))
    worker_org = _worker(root)["mcpServers"]["org"]

    assert cxo_org["command"] == worker_org["command"]
    assert cxo_org["args"][0] == worker_org["args"][0]


def test_the_env_file_is_never_opened(root, hub_on, monkeypatch):
    """Existence only: a read of the secret file would raise here."""
    env_file = hub_on
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


# ------------------------------------------- the switch: env file alone is not enough

def test_env_file_present_switch_absent_leaves_both_generators_plain(root, env_file):
    """The Mac and Contabo TODAY: the env file is there (it is the cutover's
    input) and no node file says org_db. Must not move a session to the hub."""
    _assert_both_plain(root)


def test_a_node_file_with_only_the_host_line_stays_plain(root, env_file, tmp_path, monkeypatch):
    _write_node(tmp_path, monkeypatch, "host: mac\n")

    _assert_both_plain(root)


def test_switch_on_but_env_file_absent_stays_plain(root, hub_node):
    _assert_both_plain(root)


def test_no_env_file_and_no_switch_leaves_both_entries_exactly_as_before(root):
    _assert_both_plain(root)


def test_hub_on_but_wrapper_script_missing_stays_plain(root, hub_on):
    (root / "scripts" / "hub" / "with-org-db-env.sh").unlink()

    _assert_both_plain(root)


@pytest.mark.parametrize("body", [
    "org_db: sqlite\n",                       # another value
    "org_db: hubx\n",                         # hub inside a longer token
    "org_db: xhub\n",
    "org_db: hub extra\n",
    "org_db: hub#x\n",                        # '#' without a space is part of the scalar
    'org_db: "hub"\n',                        # strict match: no quotes
    "org_db:\n",                              # empty
    "# org_db: hub\n",                        # commented out
    "  # org_db: hub\n",
    "  org_db: hub\n",                        # indented = nested under another key
    "cfg:\n  org_db: hub\n",
    "xorg_db: hub\n",                         # a different key
    "org_db: hub\norg_db: sqlite\n",          # the last line wins
    "",
])
def test_anything_but_a_bare_org_db_hub_line_is_not_live(root, env_file, tmp_path, monkeypatch, body):
    _write_node(tmp_path, monkeypatch, body)

    assert cxo.hub_is_live() is False
    _assert_both_plain(root)


@pytest.mark.parametrize("body", [
    "org_db: hub\n",
    "host: mac\norg_db: hub\n",
    "host: mac\norg_db: hub",                 # no trailing newline
    "org_db: hub   # live since the cutover\n",
    "host: mac\r\norg_db: hub\r\n",           # CRLF
    "org_db: sqlite\norg_db: hub\n",          # the last line wins
    "# node file\nhost: contabo\n\norg_db:   hub  \n",
])
def test_a_bare_org_db_hub_line_is_live(root, env_file, tmp_path, monkeypatch, body):
    _write_node(tmp_path, monkeypatch, body)

    assert cxo.hub_is_live() is True
    assert cxo._build("org", str(root))["command"] == _wrapper(root)
    assert _worker(root)["mcpServers"]["org"]["command"] == _wrapper(root)


def test_a_node_path_that_is_a_directory_is_not_live(root, env_file, tmp_path, monkeypatch):
    d = tmp_path / "a-dir"
    d.mkdir()
    monkeypatch.setenv("MOONIEX_NODE_YAML", str(d))

    assert cxo.hub_is_live() is False


def test_default_paths_are_under_home_when_the_overrides_are_unset(root, tmp_path, monkeypatch):
    home = tmp_path / "home"
    cfg = home / ".config" / "mooniex"
    cfg.mkdir(parents=True)
    (cfg / "org-db.env").write_text(ENV_BODY)
    (cfg / "node.yaml").write_text("host: mac\norg_db: hub\n")
    monkeypatch.delenv("MOONIEX_ORG_DB_ENV", raising=False)
    monkeypatch.delenv("MOONIEX_NODE_YAML", raising=False)
    monkeypatch.setenv("HOME", str(home))

    assert cxo._build("org", str(root))["command"] == _wrapper(root)

    (cfg / "node.yaml").write_text("host: mac\n")
    assert cxo._build("org", str(root))["command"] == _py(root)

    (cfg / "node.yaml").write_text("host: mac\norg_db: hub\n")
    (cfg / "org-db.env").unlink()
    assert cxo._build("org", str(root))["command"] == _py(root)


# ------------------------------------------------------------------ set_org_db (writer)

def test_set_org_db_replaces_in_place_never_duplicates_and_keeps_host():
    src = "host: mac\norg_db: sqlite\nhq_root: /x\norg_db: sqlite\n"

    out = cxo.set_org_db(src, "hub")

    assert out == "host: mac\norg_db: hub\nhq_root: /x\n"
    assert cxo.set_org_db(out, "hub") == out


def test_set_org_db_appends_when_absent_even_without_a_trailing_newline():
    assert cxo.set_org_db("host: mac", "hub") == "host: mac\norg_db: hub\n"
    assert cxo.set_org_db("host: mac\n", "hub") == "host: mac\norg_db: hub\n"
    assert cxo.set_org_db("", "hub") == "org_db: hub\n"


def test_set_org_db_none_removes_every_org_db_line_and_nothing_else():
    src = "host: mac\norg_db: hub\n# org_db: a comment stays\norg_db: hub\n"

    out = cxo.set_org_db(src, None)

    assert out == "host: mac\n# org_db: a comment stays\n"
    assert cxo.set_org_db(out, None) == out


# --------------------------------------------------------------------------- Windows

def test_windows_stays_unwrapped_even_with_the_hub_live(root, hub_on, monkeypatch):
    """An env file is not a route on Windows (bash wrapper, W3.4): without winbox's
    Infisical credential and tools/infisical_setup.py, both entries stay plain."""
    monkeypatch.setattr(sys, "platform", "win32")

    _assert_both_plain(root)


# W3.4 (CEO approval 2026-10-03): winbox has no bash and never an org-db.env. The org
# server starts under `infisical_setup.py run Agents-Core prod --as winbox` when the
# node file says `org_db: hub` AND winbox's Infisical credential file exists.

@pytest.fixture
def win(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")


@pytest.fixture
def win_root(root):
    """The fake root plus tools/infisical_setup.py (the generators test existence only)."""
    (root / "tools").mkdir(exist_ok=True)
    (root / "tools" / "infisical_setup.py").write_text("")
    return root


@pytest.fixture
def winbox_cred(tmp_path, monkeypatch):
    """A fake machine credential dir holding winbox.env."""
    d = tmp_path / "infisical"
    d.mkdir()
    f = d / "winbox.env"
    f.write_text(f"INFISICAL_CLIENT_SECRET={SENTINEL}\n")
    monkeypatch.setenv("INFISICAL_CRED_DIR", str(d))
    return f


def _win_prefix(root: Path) -> list[str]:
    return [_py(root), "-E", "-s", str(root / "tools" / "infisical_setup.py"),
            "run", "Agents-Core", "prod", "--as", "winbox", "--"]


def test_windows_routes_both_org_entries_through_infisical_run(win, win_root, hub_node, winbox_cred):
    prefix = _win_prefix(win_root)

    cxo_org = cxo._build("org", str(win_root))
    worker_org = _worker(win_root)["mcpServers"]["org"]

    plain = _plain_cxo_org(win_root)
    assert cxo_org == {**plain, "command": prefix[0], "args": [*prefix[1:], plain["command"], *plain["args"]]}
    plain_w = _plain_worker_org(win_root)
    assert worker_org == {**plain_w, "command": prefix[0], "args": [*prefix[1:], plain_w["command"], *plain_w["args"]]}


def test_windows_without_the_switch_stays_plain(win, win_root, winbox_cred):
    _assert_both_plain(win_root)


def test_windows_without_the_credential_stays_plain(win, win_root, hub_node):
    _assert_both_plain(win_root)


def test_windows_without_infisical_setup_stays_plain(win, root, hub_node, winbox_cred):
    _assert_both_plain(root)


def test_windows_user_scoped_credential_counts(win, win_root, hub_node, tmp_path, monkeypatch):
    """Option B (CEO 2026-10-02): the credential under the user's profile is enough."""
    user = tmp_path / "user-infisical"
    user.mkdir()
    (user / "winbox.env").write_text("x\n")
    monkeypatch.setenv("INFISICAL_USER_CRED_DIR", str(user))

    assert cxo._build("org", str(win_root))["args"][:9] == _win_prefix(win_root)[1:]


def test_windows_route_is_idempotent(win, win_root, hub_node, winbox_cred):
    once = cxo.wrap_org_entry(_plain_cxo_org(win_root), str(win_root))

    assert once["args"][:9] == _win_prefix(win_root)[1:]
    assert cxo.wrap_org_entry(once, str(win_root)) == once


def test_windows_credential_file_is_never_opened(win, win_root, hub_node, winbox_cred, monkeypatch, tmp_path):
    real_open = builtins.open

    def guarded(file, *a, **kw):
        assert Path(file) != winbox_cred, "the credential file must never be opened"
        return real_open(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", guarded)
    out = tmp_path / "cxo.json"
    monkeypatch.setattr(sys, "argv", ["cxo_mcp_config.py", "--servers", "org", "--root", str(win_root), "--out", str(out)])
    assert cxo.main() == 0
    assert SENTINEL not in out.read_text()


@pytest.mark.parametrize("setup, expected", [
    ("win-routed", "infisical"),
    ("win-no-cred", "none"),
    ("posix-hub", "wrapper"),
    ("posix-plain", "none"),
])
def test_hub_route_cli(setup, expected, root, tmp_path, monkeypatch, capsys):
    """windows/cxo-claude.ps1 decides hub vs standalone from this one line."""
    if setup.startswith("win"):
        monkeypatch.setattr(sys, "platform", "win32")
        (root / "tools").mkdir(exist_ok=True)
        (root / "tools" / "infisical_setup.py").write_text("")
        _write_node(tmp_path, monkeypatch, "host: winbox\norg_db: hub\n")
        if setup == "win-routed":
            d = tmp_path / "cred"
            d.mkdir()
            (d / "winbox.env").write_text("x\n")
            monkeypatch.setenv("INFISICAL_CRED_DIR", str(d))
    elif setup == "posix-hub":
        (tmp_path / "org-db.env").write_text(ENV_BODY)
        monkeypatch.setenv("MOONIEX_ORG_DB_ENV", str(tmp_path / "org-db.env"))
        _write_node(tmp_path, monkeypatch, "host: mac\norg_db: hub\n")
    monkeypatch.setattr(sys, "argv", ["cxo_mcp_config.py", "--root", str(root), "--hub-route"])

    assert cxo.main() == 0
    assert capsys.readouterr().out.strip() == expected


# ------------------------------------------------------------------ already wrapped

def test_an_already_wrapped_template_is_not_wrapped_twice(root, hub_on, tmp_path):
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


def test_wrap_org_entry_is_idempotent(root, hub_on):
    once = cxo.wrap_org_entry(_plain_cxo_org(root), str(root))

    assert once["command"] == _wrapper(root)
    assert cxo.wrap_org_entry(once, str(root)) == once


def test_an_already_wrapped_entry_is_left_alone_on_a_host_with_the_switch_off(root):
    """cutover_flip'd checkout, switch off: still not touched, never double-wrapped."""
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


def _flip_module_on_a_copy(tmp_path, monkeypatch, node_body: str = "host: mac\n"):
    """cutover_flip.py copied into a tmp tree with copies of the tracked files it
    used to rewrite, its plists pointed at tmp files and the node file at a tmp
    file. Its ROOT is derived from __file__, so on the copy it can only ever see
    the copy. Returns (copy_root, module, plists, node_file)."""
    copy = tmp_path / "copy"
    for rel in TRACKED + ("scripts/hub/cutover_flip.py", "scripts/lib/cxo_mcp_config.py"):
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
    node = _write_node(tmp_path, monkeypatch, node_body)
    return copy, mod, plists, node


def _snapshot(copy: Path) -> dict:
    return {rel: (copy / rel).read_bytes() for rel in TRACKED}


@pytest.mark.parametrize("argv", [[], ["--apply"], ["--rollback"], ["--rollback", "--apply"]])
def test_cutover_flip_never_touches_tracked_files(tmp_path, monkeypatch, capsys, argv):
    copy, mod, plists, node = _flip_module_on_a_copy(tmp_path, monkeypatch)
    before = _snapshot(copy)

    assert mod.main(argv) == 0

    assert _snapshot(copy) == before
    out = capsys.readouterr().out
    assert "mcp.json" not in out and "cto-claude.sh" not in out


def test_cutover_flip_dry_run_leaves_every_file_byte_identical_and_prints_the_node_line(
        tmp_path, monkeypatch, capsys):
    copy, mod, plists, node = _flip_module_on_a_copy(tmp_path, monkeypatch)
    node_before = node.read_bytes()

    mod.main([])

    assert node.read_bytes() == node_before == b"host: mac\n"
    assert all(p.read_text() == PLIST for p in plists)
    out = capsys.readouterr().out
    assert "+org_db: hub" in out and "dry-run" in out


def test_cutover_flip_apply_flips_the_plists_and_sets_the_switch(tmp_path, monkeypatch):
    copy, mod, plists, node = _flip_module_on_a_copy(tmp_path, monkeypatch)
    assert cxo.hub_is_live() is False

    mod.main(["--apply"])

    for p in plists:
        text = p.read_text()
        assert text.count(mod.WRAPPER) == 1
        assert text.index(mod.WRAPPER) < text.index("/usr/bin/python3")
    assert node.read_text() == "host: mac\norg_db: hub\n"
    assert cxo.hub_is_live() is True  # the line --apply wrote is the one the generators read


def test_cutover_flip_apply_is_idempotent_and_never_duplicates_org_db(tmp_path, monkeypatch, capsys):
    copy, mod, plists, node = _flip_module_on_a_copy(
        tmp_path, monkeypatch, "host: mac\norg_db: sqlite\nhq_root: /x\n")

    mod.main(["--apply"])
    first = node.read_bytes()
    assert first == b"host: mac\norg_db: hub\nhq_root: /x\n"

    capsys.readouterr()
    mod.main(["--apply"])  # second run: nothing left to change
    assert node.read_bytes() == first
    assert all(p.read_text().count(mod.WRAPPER) == 1 for p in plists)
    assert "no changes needed" in capsys.readouterr().out


def test_cutover_flip_apply_creates_a_missing_node_file_with_only_the_switch(tmp_path, monkeypatch):
    copy, mod, plists, node = _flip_module_on_a_copy(tmp_path, monkeypatch)
    node.unlink()

    mod.main(["--apply"])

    assert node.read_text() == "org_db: hub\n"


def test_cutover_flip_rollback_removes_the_switch_only(tmp_path, monkeypatch, capsys):
    copy, mod, plists, node = _flip_module_on_a_copy(
        tmp_path, monkeypatch, "host: mac\norg_db: hub\n")

    mod.main(["--rollback"])  # dry-run
    assert node.read_bytes() == b"host: mac\norg_db: hub\n"
    assert "-org_db: hub" in capsys.readouterr().out

    mod.main(["--rollback", "--apply"])
    assert node.read_text() == "host: mac\n"
    assert cxo.hub_is_live() is False
    assert all(p.read_text() == PLIST for p in plists)  # plists are not rolled back here

    mod.main(["--rollback", "--apply"])  # idempotent
    assert node.read_text() == "host: mac\n"


def test_cutover_mac_script_parses_and_step_4_tells_sessions_to_restart():
    script = ROOT / "scripts" / "hub" / "cutover-mac.sh"

    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    text = script.read_text()
    assert "org_db: hub" in text
    assert "until they restart" in text
    assert "cutover_flip.py --rollback --apply" in text


# --------------------------------------------------------------------- mesh_check

import asyncio  # noqa: E402
import types  # noqa: E402

import tools.mesh_check as mesh  # noqa: E402


def _capture_l2_params(monkeypatch, root: Path) -> dict:
    """Run check_l2 against a fake MCP client that records the launch params."""
    import mcp
    import mcp.client.stdio as mcp_stdio

    seen: dict = {}

    class _Ctx:
        async def __aenter__(self):
            return (None, None)

        async def __aexit__(self, *exc):
            return False

    class _Session:
        def __init__(self, *_a, **_k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def initialize(self):
            return None

        async def list_tools(self):
            return types.SimpleNamespace(tools=[types.SimpleNamespace(name=n)
                                                for n in ("create_task", "delegate_task")])

    def fake_stdio_client(params):
        seen["params"] = params
        return _Ctx()

    monkeypatch.setattr(mcp_stdio, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(mcp, "ClientSession", _Session)
    ok, reason = asyncio.run(mesh.check_l2(root))
    assert (ok, reason) == (True, None)
    return seen


def test_mesh_check_launch_uses_the_wrapper_when_the_hub_is_live(root, hub_on):
    command, args = mesh._org_server_launch(root, Path(_py(root)))

    assert command == _wrapper(root)
    assert args == [_py(root), "-m", "runners.cto_mcp_server"]


def test_mesh_check_launch_is_plain_with_the_switch_off(root, env_file):
    """env file present, no `org_db: hub`: the probe stays on the plain launch."""
    command, args = mesh._org_server_launch(root, Path(_py(root)))

    assert (command, args) == (_py(root), ["-m", "runners.cto_mcp_server"])


def test_mesh_check_l2_passes_the_wrapper_params_to_the_client(root, hub_on, monkeypatch):
    params = _capture_l2_params(monkeypatch, root)["params"]

    assert params.command == _wrapper(root)
    assert params.args == [_py(root), "-m", "runners.cto_mcp_server"]
    assert params.cwd == str(root)
    assert SENTINEL not in json.dumps(params.args) and "ORG_DB_URL" not in (params.env or {})


def test_mesh_check_l2_passes_plain_params_with_the_switch_off(root, env_file, monkeypatch):
    params = _capture_l2_params(monkeypatch, root)["params"]

    assert params.command == _py(root)
    assert params.args == ["-m", "runners.cto_mcp_server"]


def test_mesh_check_falls_back_to_plain_only_when_the_generator_file_is_missing(
        root, hub_on, tmp_path, monkeypatch):
    monkeypatch.setattr(mesh, "ROOT", tmp_path / "no-checkout-here")

    assert mesh._org_server_launch(root, Path(_py(root))) == (
        _py(root), ["-m", "runners.cto_mcp_server"])


def test_mesh_check_a_generator_error_is_a_red_result_not_a_silent_plain_probe(
        root, hub_on, monkeypatch):
    """The params are built inside check_l2's try: a broken generator must turn
    the cell red, never fall back to probing the wrong ledger."""
    def boom(*_a, **_k):
        raise RuntimeError("generator exploded")

    monkeypatch.setattr(mesh, "_org_server_launch", boom)
    import mcp
    import mcp.client.stdio as mcp_stdio
    monkeypatch.setattr(mcp_stdio, "stdio_client", lambda p: pytest.fail("client must not start"))
    monkeypatch.setattr(mcp, "ClientSession", object)

    ok, reason = asyncio.run(mesh.check_l2(root))

    assert ok is False
    assert "RuntimeError" in reason and "generator exploded" in reason


def test_the_shipped_launcher_inputs_carry_no_wrapper_or_env_path():
    """The tracked launcher inputs must not name the wrapper or the env file:
    the generators decide the wrapper per host."""
    for rel in TRACKED:
        text = (ROOT / rel).read_text()
        assert "with-org-db-env" not in text, rel
        assert "org-db.env" not in text, rel
