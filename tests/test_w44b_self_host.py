"""Org Mesh W4.4b (task-3f8a31ae): a joined node is itself.

deploy/join/join.sh writes ~/.config/mooniex/node.yaml {host, os, hq_root} and then runs
`tools.node_dispatch probe` with ORG_HOST set. The node is in the hub's `hosts` table and
never in config/hosts.yaml, so lib.config.self_host() refused it ("is not a known host") and
the last join step failed. Covered here:

  * node.yaml with host + os + hq_root, all well-formed, for a host hosts.yaml does not
    declare: self_host() returns it and hosts() carries an entry built from node.yaml;
  * hosts.yaml still wins for every name it declares, and every malformed node.yaml still raises;
  * one host-name rule: every name tools.hq_join accepts is a name `infisical_setup.py save`
    accepts;
  * the probe passes on such a node with no hosts.yaml entry.

Everything runs against tmp paths: NODE_CONFIG_PATH, HOME and the ledger are redirected, and
no detector, git, vm_stat or network call is made.

Run:  .venv/bin/python -m pytest tests/test_w44b_self_host.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, db  # noqa: E402
from tools import hq_join, infisical_setup  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402

# The example recipient from the age README: a real bech32 checksum.
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
JOINED = "node-a"
LINUX_ROOT = "/opt/MoonieXHQ"


@pytest.fixture(autouse=True)
def node_home(monkeypatch, tmp_path):
    """A temp HOME with no node.yaml in it. self_host() and hosts() are cached per
    process, so both are cleared on both sides of every test."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ORG_HOST", raising=False)
    monkeypatch.setattr(config, "NODE_CONFIG_PATH", tmp_path / ".config" / "mooniex" / "node.yaml")
    # W4.6a F12: a node.yaml naming a host hosts.yaml declares must agree with the checkout-path
    # match. This checkout is on the Mac, Contabo or a CI box, so pin "matches no host": nothing
    # here depends on where the suite runs. The disagreement cases are in test_w46a_hub_fixes.py.
    monkeypatch.setattr(config, "_root_match_host", lambda: None)
    config.self_host.cache_clear()
    config.hosts.cache_clear()
    yield tmp_path
    config.self_host.cache_clear()
    config.hosts.cache_clear()


def _write_node_yaml(data, raw: str | None = None) -> Path:
    path = config.NODE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw if raw is not None else yaml.safe_dump(data), encoding="utf-8")
    config.self_host.cache_clear()
    config.hosts.cache_clear()
    return path


def _joined(host=JOINED, os_name="linux", hq_root=LINUX_ROOT, **extra) -> dict:
    return {"host": host, "os": os_name, "hq_root": hq_root, **extra}


def _file_hosts() -> dict:
    """config/hosts.yaml as committed: what hosts() would be with no node.yaml."""
    return yaml.safe_load(config.HOSTS_CONFIG.read_text(encoding="utf-8"))["hosts"]


# ---------------------------------------------------------------- self_host()

def test_a_node_yaml_host_that_is_not_in_hosts_yaml_is_still_itself():
    assert JOINED not in _file_hosts()
    _write_node_yaml(_joined())
    assert config.self_host() == JOINED


def test_node_yaml_host_is_lowercased_and_stripped_like_a_known_one():
    _write_node_yaml(_joined(host="  Node-A "))
    assert config.self_host() == JOINED
    assert JOINED in config.hosts()


def test_org_host_naming_the_joined_node_resolves_when_node_yaml_says_so(monkeypatch):
    # join.sh step 9 runs the probe with ORG_HOST=<host>.
    _write_node_yaml(_joined())
    monkeypatch.setenv("ORG_HOST", "Node-A")
    assert config.self_host() == JOINED


def test_org_host_naming_some_other_unknown_host_still_raises(monkeypatch):
    _write_node_yaml(_joined())
    monkeypatch.setenv("ORG_HOST", "node-b")
    with pytest.raises(ValueError, match="node-b"):
        config.self_host()


def test_org_host_unknown_with_no_node_yaml_still_raises(monkeypatch):
    # No os and no hq_root to build an entry from: a name alone is not an identity.
    monkeypatch.setenv("ORG_HOST", JOINED)
    with pytest.raises(ValueError, match=JOINED):
        config.self_host()


def test_org_host_naming_a_known_host_still_wins_over_node_yaml(monkeypatch):
    _write_node_yaml(_joined())
    monkeypatch.setenv("ORG_HOST", "mac")
    assert config.self_host() == "mac"


def test_self_host_sources_shows_the_joined_node_and_never_raises(monkeypatch):
    _write_node_yaml(_joined())
    monkeypatch.setenv("ORG_HOST", "node-b")
    src = config.self_host_sources()
    assert src["node_yaml"] == JOINED
    assert "error" in src["env"] and "node-b" in src["env"]


# ---------------------------------------------------------------- hosts()

def test_hosts_carries_an_entry_built_from_node_yaml_and_leaves_the_rest_alone():
    before = _file_hosts()
    _write_node_yaml(_joined())
    got = config.hosts()
    assert got[JOINED] == {
        "os": "linux", "hq_root": LINUX_ROOT, "ssh": None,
        "agents_root": f"{LINUX_ROOT}/Agents/Core",
        "worktrees": f"{LINUX_ROOT}/Agents/Core/worktrees",
        "provides": [], "max_workers": 1, "runners": [],
    }
    assert {k: v for k, v in got.items() if k != JOINED} == before
    assert config.host(JOINED) is got[JOINED]
    # the file itself is not touched: the entry exists only in hosts()
    assert JOINED not in _file_hosts()


def test_a_windows_node_gets_backslash_paths_like_winbox():
    _write_node_yaml(_joined(host="win-a", os_name="windows", hq_root="C:\\Users\\x\\MoonieXHQ\\"))
    entry = config.hosts()["win-a"]
    assert entry["hq_root"] == "C:\\Users\\x\\MoonieXHQ"
    assert entry["agents_root"] == "C:\\Users\\x\\MoonieXHQ\\Agents\\Core"
    assert entry["worktrees"] == "C:\\Users\\x\\MoonieXHQ\\Agents\\Core\\worktrees"
    assert config.self_host() == "win-a"


def test_the_entry_is_the_one_the_hub_keeps_for_that_node(monkeypatch, tmp_path):
    """tools/hq_join.accept stores the entry the hub exports. The node's own view has
    the same keys and values; only `ssh` differs (a node never dials out to itself,
    as `mac` on the Mac has ssh: null)."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db.init()
    for os_name, root in (("linux", LINUX_ROOT), ("darwin", "/Users/x/MoonieXHQ"),
                          ("windows", "C:\\Users\\x\\MoonieXHQ")):
        host = f"n-{os_name}"
        token = hq_join.mint(host)["token"]
        hq_join.accept(token, host, os_name, root, PUB)
        hub_entry = json.loads(db.get_host(host)["config_json"])
        _write_node_yaml(_joined(host=host, os_name=os_name, hq_root=root))
        assert config.hosts()[host] == {**hub_entry, "ssh": None}, os_name


def test_the_keys_dispatch_and_delegate_index_directly_are_present():
    # tools/delegate reads host_cfg["ssh"], ["agents_root"], ["worktrees"];
    # tools/node_dispatch reads ["worktrees"] and .get("os").
    _write_node_yaml(_joined())
    entry = config.host(JOINED)
    for key in ("ssh", "agents_root", "worktrees", "os"):
        assert key in entry
    assert entry["ssh"] is None  # tools/worker_reap treats a truthy ssh as a remote box


def test_hosts_yaml_wins_for_a_known_host_and_node_yaml_cannot_override_it():
    before = _file_hosts()
    _write_node_yaml(_joined(host="mac", os_name="windows", hq_root="C:\\Elsewhere"))
    assert config.self_host() == "mac"
    assert config.hosts() == before
    assert config.host("mac")["os"] == "darwin"


@pytest.mark.parametrize("name", ["mac", "winbox", "contabo"])
def test_a_bare_host_key_for_a_known_host_behaves_as_today(name):
    _write_node_yaml({"host": name})
    assert config.self_host() == name
    assert config.hosts() == _file_hosts()


# ---------------------------------------------------------------- malformed node.yaml

_BAD = {
    "no os": {"host": JOINED, "hq_root": LINUX_ROOT},
    "no hq_root": {"host": JOINED, "os": "linux"},
    "unknown os": _joined(os_name="freebsd"),
    "os wrong type": _joined(os_name=["linux"]),
    "hq_root relative": _joined(hq_root="opt/MoonieXHQ"),
    "hq_root dotdot": _joined(hq_root="/opt/../etc"),
    "hq_root is /": _joined(hq_root="/"),
    "hq_root control char": _joined(hq_root="/opt/x\ny"),
    "hq_root windows path on linux": _joined(hq_root="C:\\MoonieXHQ"),
    "hq_root posix path on windows": _joined(os_name="windows", hq_root="/opt/MoonieXHQ"),
    "hq_root drive only": _joined(os_name="windows", hq_root="C:\\"),
    "hq_root wrong type": _joined(hq_root=["/opt/x"]),
    "hq_root too long": _joined(hq_root="/" + "a" * 240),
    "host too short": _joined(host="ab"),
    "host 32 chars": _joined(host="x" * 32),
    "host underscore": _joined(host="node_a"),
    "host trailing dash": _joined(host="node-"),
    "host wrong type": _joined(host=12345),
}


@pytest.mark.parametrize("case", sorted(_BAD))
def test_a_node_yaml_that_is_not_complete_and_well_formed_still_raises(case):
    data = _BAD[case]
    _write_node_yaml(data)
    with pytest.raises(ValueError, match="not a known host"):
        config.self_host()
    # hosts() never fails because of node.yaml, and adds nothing for it
    assert config.hosts() == _file_hosts()


@pytest.mark.parametrize("raw", ["host: [unclosed\n", "- a\n- b\n", "just a string\n"])
def test_an_unreadable_node_yaml_raises_from_self_host_but_not_from_hosts(raw):
    _write_node_yaml(None, raw=raw)
    with pytest.raises((ValueError, yaml.YAMLError)):
        config.self_host()
    assert config.hosts() == _file_hosts()


def test_a_node_yaml_with_no_host_key_is_ignored_as_today():
    _write_node_yaml({"os": "linux", "hq_root": LINUX_ROOT})
    assert config._node_yaml_host() is None
    assert config.hosts() == _file_hosts()


# ---------------------------------------------------------------- one host-name rule

def _name(n: int) -> str:
    return "a" + "b" * (n - 2) + "c" if n >= 2 else "a"


def test_hq_join_host_re_is_3_to_31_chars():
    assert hq_join.HOST_RE.pattern == "[a-z][a-z0-9-]{1,29}[a-z0-9]"
    accepted = [n for n in range(1, 41) if hq_join.HOST_RE.fullmatch(_name(n))]
    assert accepted == list(range(3, 32))


def test_every_host_name_hq_join_accepts_is_a_name_save_accepts():
    for n in range(1, 41):
        name = _name(n)
        if hq_join.HOST_RE.fullmatch(name):
            assert infisical_setup.NAME_RE.match(name), name
    # the old edge that minted and then failed at `save`
    assert not hq_join.HOST_RE.fullmatch(_name(32))
    assert not infisical_setup.NAME_RE.match(_name(32))


def test_name_re_is_untouched():
    assert infisical_setup.NAME_RE.pattern == r"^[a-z][a-z0-9-]{1,30}$"


def test_config_and_hq_join_share_the_one_rule():
    assert hq_join.HOST_RE is config.HOST_NAME_RE


@pytest.mark.parametrize("os_name,root", [
    ("linux", "/opt/MoonieXHQ"), ("linux", "/opt/MoonieXHQ/"), ("linux", "/"), ("linux", "opt/x"),
    ("linux", "/a/../b"), ("linux", "/a/..b"), ("linux", "C:\\x"), ("linux", "/x\x00y"),
    ("darwin", "/Users/x/MoonieXHQ"), ("darwin", ""), ("darwin", "/" + "a" * 239),
    ("darwin", "/" + "a" * 240),
    ("windows", "C:\\Users\\x"), ("windows", "C:/Users/x/"), ("windows", "C:\\"), ("windows", "C:"),
    ("windows", "/opt/x"), ("windows", "D:\\..\\x"), ("windows", "c:\\Users\\x\\\\"),
    # W4.6a F14: the character set. Allowed: letters, digits, space . _ - / \ :
    ("linux", "/opt/Moonie X_1.2-b"), ("windows", "C:\\Program Files\\Moonie_X-1.2"),
    ("linux", "/opt/$HOME"), ("linux", "/opt/`id`"), ("linux", "/opt/a;b"), ("linux", "/opt/a'b"),
    ("linux", '/opt/a"b'), ("linux", "/opt/a(b)"), ("linux", "/opt/a&b"), ("linux", "/opt/a|b"),
    ("linux", "/opt/a b>c"), ("linux", "/opt/\u0e44\u0e17\u0e22"), ("linux", "/opt/a\u00e9"),
    ("windows", "C:\\Users\\x (2)\\MoonieXHQ"), ("windows", "C:\\Users\\x~1"),
])
def test_node_hq_root_agrees_with_what_hq_join_accepts(os_name, root):
    """lib/config cannot import tools/hq_join (it imports lib/config), so the hq_root
    rule is written twice; this keeps the two from drifting."""
    try:
        want = hq_join._check_hq_root(os_name, root)
    except hq_join.JoinError:
        want = None
    assert config._node_hq_root(os_name, root) == want
    if want is not None:
        agents, worktrees = hq_join._layout(os_name, want)
        _write_node_yaml(_joined(host="n-x", os_name=os_name, hq_root=root))
        entry = config.hosts()["n-x"]
        assert (entry["agents_root"], entry["worktrees"]) == (agents, worktrees)


# ---------------------------------------------------------------- the probe

@pytest.fixture()
def probe_box(monkeypatch, tmp_path):
    """A joined node with nothing real under the probe: a tmp ledger, no detector, no git,
    no vm_stat, no CLI lookup."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "SSH_ORIGINAL_COMMAND", "SSH_CLIENT"):
        monkeypatch.delenv(var, raising=False)
    db.init()
    monkeypatch.setattr(nd, "_ram_free_gb", lambda: 8.0)
    monkeypatch.setattr(nd, "_git_version", lambda: "abc1234")
    monkeypatch.setattr(nd, "_PROVIDES_DETECTORS", ())
    monkeypatch.setattr(nd.shutil, "which", lambda name, *a, **kw: None)
    _write_node_yaml(_joined())
    assert JOINED not in _file_hosts()  # the whole point: no hosts.yaml entry
    return tmp_path


@pytest.mark.parametrize("org_host", [None, JOINED], ids=["node_yaml_only", "org_host_as_join_sh_sets_it"])
def test_the_probe_passes_on_a_joined_node_with_no_hosts_yaml_entry(probe_box, monkeypatch, org_host):
    if org_host:
        monkeypatch.setenv("ORG_HOST", org_host)

    assert config.self_host() == JOINED
    assert config.hosts()[JOINED]["os"] == "linux"

    out = nd.dispatch("probe", [])

    assert out["ok"] is True, out
    r = out["result"]
    assert r["host"] == JOINED
    assert r["provides_measured"] == [{"darwin": "macos"}.get(nd._os_name(), nd._os_name())]
    assert r["probe_errors"] == []
    row = db.get_host(JOINED)
    assert row["probed_at"] and row["free_gb"] == r["free_gb"]
    # the row is the probe's, not a join-state write: no status was invented
    assert row["status"] is None
    # the path node_dispatch reads the host entry through
    assert nd._worktrees_root() == Path(f"{LINUX_ROOT}/Agents/Core/worktrees")


def test_the_probe_prints_the_one_json_line_join_sh_reads(probe_box, monkeypatch, capsys):
    # join.sh: last non-empty stdout line -> json; d["ok"], d["result"]["host" | "os" | "free_gb" | "runners"]
    monkeypatch.setenv("ORG_HOST", JOINED)

    code = nd.main(["probe"])

    assert code == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    d = json.loads(lines[-1])
    assert d["ok"] is True
    for key in ("host", "os", "free_gb", "runners"):
        assert key in d["result"]
    assert d["result"]["host"] == JOINED


def test_the_probe_still_fails_for_a_host_node_yaml_cannot_vouch_for(probe_box, monkeypatch, capsys):
    monkeypatch.setenv("ORG_HOST", "node-b")

    code = nd.main(["probe"])

    d = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert code == 1 and d["ok"] is False
    assert "node-b" in d["error"]
    assert db.get_host("node-b") is None
