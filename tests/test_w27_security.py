"""Org Mesh W2.7 (task-42fdcda7): security pins for the dispatch mesh, taken
before any org_dispatch key is installed (W2.8) or ORG_MESH_DISPATCH goes live.

1. Verb parser fuzz: >= 5,000 seeded hostile commands through
   node_dispatch.run_command. Each one is refused before any backend or
   subprocess runs, with exactly one audit row written and nothing else, or it
   is an allow-listed verb whose arguments match an independent copy of the
   grammar and carry no character a shell or PowerShell could act on.
2. The PowerShell allow-lists (CTO-FEEDBACK item 2): an exhaustive BMP scan for
   a quote, newline, `$`, backtick or command separator, then >= 5,000 cases
   through _ps_safe, _one_shot_task_script and _spawn_worker_script, and the
   win32 start_clevel path end to end. lib.mesh.build_argv: >= 5,000 cases.
3. No shell in node_dispatch or lib.mesh (AST), and every authorized_keys line
   in docs/ops/node-dispatch.md keeps command=, from= and restrict.
4. Letters: two overlapping deliver_letter calls write the letter once.
5. queued_remote: one retry per row per pass, with several rows queued.
6. Audit rows: fixed keys, bounded values, credentials redacted, no env canary.
7. spawn_worker on Windows re-checks the hub's gating; MAILBOX.md links refused.

Nothing here reaches ssh, tmux, schtasks, PowerShell, git or create_worktree.
Each is a tripwire that records the attempt and raises, and the tests assert
the record is empty: node_dispatch._run catches every exception, so a raise on
its own would be swallowed into an ok:false reply. lib.db is a tmp_path SQLite
ledger (ADR 0021).

Run:  .venv/bin/python -m pytest tests/test_w27_security.py
"""
from __future__ import annotations

import ast
import collections
import json
import os
import random
import re
import shlex
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config as config_mod  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import mailbox, mesh  # noqa: E402
from lib import notify as notify_mod  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
from tools import agent_transport, delegate, send_to_cxo, session_status  # noqa: E402
from tools import tmux_session, worker_reap, worktree  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402

SEED = 0x42FDCDA7
FUZZ_CASES = 6000
CANARY = "canary-SECRET-7f3a9c0d"  # stands in for a token in the environment
UUID = "12345678-1234-1234-1234-123456789abc"


# ---------------------------------------------------------------------------
# isolation
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    for var in ("ORG_DB_URL", "CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "SSH_ORIGINAL_COMMAND", "SSH_CLIENT", mesh.ENV_FLAG):
        monkeypatch.delenv(var, raising=False)
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))
    for var in ("GH_TOKEN", "GITHUB_TOKEN", "ANTHROPIC_API_KEY", "INFISICAL_TOKEN"):
        monkeypatch.setenv(var, CANARY)
    monkeypatch.setattr(notify_mod, "notify", lambda *a, **kw: None)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(nd, "SPAWN_PROMPT_DELAY_S", 0)
    monkeypatch.setattr(nd, "_worktrees_root", lambda: tmp_path / "worktrees")
    (tmp_path / "worktrees").mkdir()
    config_mod.self_host.cache_clear()
    yield
    config_mod.self_host.cache_clear()


class Tripwire:
    """Everything that could leave this process. Records the attempt, then raises."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def arm(self, name: str):
        def fire(*a, **kw):
            self.calls.append((name, repr(a)[:200]))
            raise AssertionError(f"{name} must not be reached")
        return fire


@pytest.fixture
def wire(monkeypatch) -> Tripwire:
    w = Tripwire()
    for mod, attr in ((subprocess, "run"), (subprocess, "Popen"), (os, "system"),
                      (tmux_session, "create"), (tmux_session, "has_session"),
                      (worktree, "create_worktree"), (delegate, "delegate_task"),
                      (worker_reap, "close_dev"), (send_to_cxo, "attempt_wake"),
                      (agent_transport, "attempt_wake"), (nd, "_run_powershell")):
        monkeypatch.setattr(mod, attr, w.arm(f"{getattr(mod, '__name__', mod)}.{attr}"))
    if hasattr(delegate, "create_worktree"):
        monkeypatch.setattr(delegate, "create_worktree", w.arm("delegate.create_worktree"))
    return w


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _events() -> list[dict]:
    with db_mod.get_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM events ORDER BY id")]
    for r in rows:
        r["payload"] = json.loads(r["payload"])
    return rows


def _update(tid: str, **cols) -> None:
    sets = ", ".join(f"{k}=?" for k in cols)
    with db_mod.get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*cols.values(), tid))


def _task(project: str = "projA", role: str = "developer", **cols) -> str:
    tid = db_mod.create_task(project, role, "t", "d")
    if cols:
        _update(tid, **cols)
    return tid


# ---------------------------------------------------------------------------
# 1. verb parser fuzz
# ---------------------------------------------------------------------------

_HEX8 = "[0-9a-f]{8}"
# The W2 grammar written out again from docs/design/org-mesh.md, not imported
# from node_dispatch: if the server's patterns loosen, this copy disagrees.
_GRAMMAR = {
    "probe": (),
    "pid_alive": (rf"task-{_HEX8}",),
    "spawn_worker": (rf"task-{_HEX8}",),
    "kill_worker": (rf"task-{_HEX8}",),
    "publish_branch": (rf"task-{_HEX8}",),
    "deliver_letter": (r"[0-9]{1,12}",),
}
_TOKEN_OK = re.compile(r"[a-z0-9_-]{1,64}", re.ASCII)


def _oracle(raw: str) -> list[str] | None:
    """The tokens of an allow-listed call, or None when it must be refused."""
    if not raw.strip() or len(raw) > 256:
        return None
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        return None
    try:
        parts = shlex.split(raw)
    except ValueError:
        return None
    if not parts:
        return None
    verb, args = parts[0], parts[1:]
    if verb == "start_clevel":
        roles = set(config_mod.live_c_level_roles())
        if len(args) == 1 and args[0] in roles:
            return parts
        if (len(args) == 3 and args[0] in roles and args[1] == "--resume"
                and re.fullmatch(_HEX8, args[2], re.ASCII)):
            return parts
        return None
    spec = _GRAMMAR.get(verb)
    if spec is None or len(args) != len(spec):
        return None
    if all(re.fullmatch(p, a, re.ASCII) for p, a in zip(spec, args)):
        return parts
    return None


_UNICODE = [
    "\u0430", "\uff53", "\u2018", "\u2019", "\u201a", "\u201b", "\u201c", "\u201d",
    "\u2013", "\u2014", "\u00a0", "\u2028", "\u2029", "\u0085", "\u200b", "\ufeff",
    "\u202e", "\u0e2a", "\u0661", "\uff11", "\u00e9", "\U0001f600", "\udcff", "\ud800",
]
_CONTROL = [chr(i) for i in range(32)] + ["\x7f"]
_METAS = list(";|&$()<>`'\"\\*?[]{}~!#%^=,:@ ")
_SUFFIXES = ["; id", " && id", " || id", " | id", "$(id)", "`id`", "\nid", "\r\nid",
             " --", " -x", " -oProxyCommand=sh", " --resume", "\x00", " \u200b",
             " %COMSPEC%", " !x!", " ^& id", " > x", "'", '"', "\\"]
_NEAR_VERBS = ["Probe", "PROBE", "probe\u200b", "spawn-worker", "spawnworker",
               "spawn_worker;", "./probe", "/bin/sh", "sh", "bash", "cmd", "powershell",
               "-c", "--", "python", "exec", "start_clevel\u00a0", "deliver_letters",
               "publish", "pr\u043ebe", "\uff50robe", ""]
_ARG_POOL = ["task-1234abcd", "task-1234ABCD", "task-1234abc", "task-1234abcde",
             "task-\u0661\u0662\u0663\u0664abcd", "task-1234abcd\n", "../task-1234abcd",
             "task-1234abcd;id", "-rf", "--", "-", "--resume", "-o", "ProxyCommand=sh",
             "-oProxyCommand=sh", "--force", "abcd1234", "ABCD1234", "abcd123", "42",
             "4" * 12, "4" * 13, "-1", "0x2a", "\u0664\u0662", "cto", "cmo", "ceo", "CTO",
             "cto ", "$(id)", "`id`", "'", '"', "\\", "*", "~", "%COMSPEC%", "!x!", "^&",
             "C:\\Windows", "\u2019", "a" * 300, ""]


def _valid_command(rng: random.Random) -> str:
    hex8 = "".join(rng.choice("0123456789abcdef") for _ in range(8))
    roles = config_mod.live_c_level_roles()
    return rng.choice([
        "probe",
        f"pid_alive task-{hex8}", f"spawn_worker task-{hex8}", f"kill_worker task-{hex8}",
        f"publish_branch task-{hex8}", f"deliver_letter {rng.randint(0, 10 ** 12 - 1)}",
        f"start_clevel {rng.choice(roles)}",
        f"start_clevel {rng.choice(roles)} --resume {hex8}",
    ])


def _hostile_char(rng: random.Random) -> str:
    pool = rng.random()
    if pool < 0.3:
        return rng.choice(_METAS)
    if pool < 0.5:
        return rng.choice(_UNICODE)
    if pool < 0.65:
        return rng.choice(_CONTROL)
    return chr(rng.randint(32, 126))


def _mutate(rng: random.Random, s: str) -> str:
    for _ in range(rng.randint(1, 3)):
        op = rng.randrange(6)
        pos = rng.randint(0, len(s))
        if op == 0:
            s = s[:pos] + _hostile_char(rng) + s[pos:]
        elif op == 1 and s:
            s = s[:pos] + s[pos + 1:]
        elif op == 2 and s:
            s = s[:pos] + _hostile_char(rng) + s[pos + 1:]
        elif op == 3:
            s = s + rng.choice(_SUFFIXES)
        elif op == 4:
            s = s.translate(str.maketrans("0123456789", "\u0660\u0661\u0662\u0663\u0664"
                                                        "\u0665\u0666\u0667\u0668\u0669"))
        else:
            s = s.upper() if rng.random() < 0.5 else s.replace(" ", rng.choice(["\t", "  ", "\u00a0"]))
    return s


def _structured(rng: random.Random) -> str:
    verb = rng.choice(list(nd.HANDLERS) + _NEAR_VERBS)
    args = [rng.choice(_ARG_POOL) for _ in range(rng.randint(0, 4))]
    if rng.random() < 0.3:
        hex8 = "".join(rng.choice("0123456789abcdef") for _ in range(8))
        args = [f"task-{hex8}"] + args[:rng.randint(0, 1)]
    parts = [verb, *args]
    return shlex.join(parts) if rng.random() < 0.6 else " ".join(parts)


def _hostile_command(rng: random.Random, i: int) -> str:
    kind = i % 6
    if kind == 0:
        return "".join(_hostile_char(rng) for _ in range(rng.randint(0, 40)))
    if kind in (1, 2):
        return _mutate(rng, _valid_command(rng))
    if kind == 3:
        return _structured(rng)
    if kind == 4:
        if rng.random() < 0.5:  # around the 256-character cap
            base = _valid_command(rng)
            return base + " " * max(0, rng.randint(250, 260) - len(base))
        return "".join(_hostile_char(rng) for _ in range(rng.randint(200, 3000)))
    return _valid_command(rng)


def test_fuzz_run_command_refuses_or_runs_exactly_the_allow_listed_call(monkeypatch, wire):
    seen: list[tuple] = []

    def stub(verb):
        def handler(*args):
            seen.append((verb, list(args)))
            return {"stub": verb}
        return handler

    monkeypatch.setattr(nd, "HANDLERS", {v: stub(v) for v in nd.HANDLERS})
    rng = random.Random(SEED)
    ro = sqlite3.connect(db_mod.DB_PATH)
    accepted = refused = 0
    for i in range(FUZZ_CASES):
        raw = _hostile_command(rng, i)
        events_before, calls_before = _count(ro, "events"), len(seen)

        out, code = nd.run_command(raw)

        line = json.dumps(out, ensure_ascii=True, default=str)
        assert "\n" not in line and line.isascii(), raw
        assert _count(ro, "events") == events_before + 1, raw
        expect = _oracle(raw)
        if expect is None:
            refused += 1
            assert (code, out["ok"]) == (2, False), (raw, out)
            assert len(seen) == calls_before, raw
            continue
        accepted += 1
        assert (code, out["ok"]) == (0, True), (raw, out)
        verb, args = expect[0], expect[1:]
        if verb == "start_clevel":
            args = [args[0], args[2] if len(args) == 3 else None]
        assert seen[calls_before:] == [(verb, args)], raw
        for token in expect:
            assert _TOKEN_OK.fullmatch(token), (raw, token)
    assert wire.calls == []
    for table in ("tasks", "letters", "locks", "hosts"):
        assert _count(ro, table) == 0, table
    ro.close()
    assert accepted + refused == FUZZ_CASES >= 5000
    assert accepted >= 500 and refused >= 3000, (accepted, refused)
    events = _events()
    assert {(e["actor"], e["kind"]) for e in events} == {(nd.ACTOR, "dispatch")}
    assert not any(CANARY in json.dumps(e["payload"]) for e in events)


def test_fuzz_real_handlers_refuse_unknown_rows_before_any_backend(wire):
    """Same generator, real handlers. The ledger is empty, so every task and
    letter verb must refuse at the row lookup, before anything runs or writes."""
    rng = random.Random(SEED + 7)
    ro = sqlite3.connect(db_mod.DB_PATH)
    ran = 0
    for i in range(1500):
        raw = _hostile_command(rng, i)
        expect = _oracle(raw)
        if expect is None or expect[0] in ("probe", "start_clevel"):
            continue  # probe and start_clevel act without a row; covered above
        out, code = nd.run_command(raw)
        ran += 1
        assert (code, out["ok"]) == (2, False), (raw, out)
        assert out["error"].startswith(("no such task", "no such letter")), out
    assert ran >= 200
    assert wire.calls == []
    for table in ("tasks", "letters", "locks"):
        assert _count(ro, table) == 0
    ro.close()


def test_fuzz_the_ssh_entry_prints_one_ascii_json_line(monkeypatch, capfd, wire):
    """main() as sshd runs it: SSH_ORIGINAL_COMMAND in, one JSON line out."""
    monkeypatch.setattr(nd, "HANDLERS", {v: (lambda *a: {}) for v in nd.HANDLERS})
    rng = random.Random(SEED + 3)
    checked = 0
    for i in range(400):
        raw = _hostile_command(rng, i)
        try:
            monkeypatch.setenv("SSH_ORIGINAL_COMMAND", raw)
        except (ValueError, UnicodeEncodeError):
            continue  # NUL or an unpaired surrogate: no environment can carry it
        code = nd.main([])
        out = capfd.readouterr().out
        assert out.endswith("\n") and out.count("\n") == 1 and out.isascii(), repr(raw)
        reply = json.loads(out)
        assert code == (2 if _oracle(raw) is None else 0), (raw, reply)
        checked += 1
    assert checked >= 300
    assert wire.calls == []


# ---------------------------------------------------------------------------
# 2. PowerShell allow-lists and builders (CTO-FEEDBACK item 2)
# ---------------------------------------------------------------------------

_PS_FORBIDDEN = (set("'`$;&|<>%!^\"") | {"\u2018", "\u2019", "\u201a", "\u201b"}
                 | {chr(i) for i in range(32)} | {"\x7f"})
_PS_PATTERNS = {
    "_PS_SAFE_RE": (nd._PS_SAFE_RE, r"C:\Users\x\mooniex"),
    "_PS_ARGUMENT_RE": (nd._PS_ARGUMENT_RE, '-File "C:\\x.ps1" -Role cto'),
    "_PS_TOKEN_RE": (nd._PS_TOKEN_RE, "claude-sonnet-5-5"),
    "_PS_REF_RE": (nd._PS_REF_RE, "main"),
    "_PS_REPO_URL_RE": (nd._PS_REPO_URL_RE, "git@github.com:PASAKON/Agents-Core"),
    "_PS_CLAUDE_ARGS_RE": (nd._PS_CLAUDE_ARGS_RE, "--model x --effort high"),
    "_PS_SESSION_NAME_RE": (nd._PS_SESSION_NAME_RE, "winbox developer (task-1234abcd) #1"),
    "_PS_MODEL_RE": (nd._PS_MODEL_RE, "openai/gpt-5:high"),
    "TASK_ID_RE": (nd.TASK_ID_RE, "task-1234abcd"),
    "BRANCH_RE": (nd.BRANCH_RE, "agent/developer-task-1234abcd"),
}


def test_every_spawn_parameter_is_held_to_a_scanned_pattern():
    scanned = {id(p) for p, _ in _PS_PATTERNS.values()}
    assert all(id(p) in scanned for _, p in nd._SPAWN_PARAMS)


@pytest.mark.parametrize("name", list(_PS_PATTERNS))
def test_no_powershell_pattern_admits_a_quote_newline_or_dollar(name):
    """Every BMP character, alone and inside a valid sample at three places."""
    pattern, sample = _PS_PATTERNS[name]
    mid = len(sample) // 2
    admitted = set()
    for cp in range(0x10000):
        c = chr(cp)
        if (pattern.fullmatch(c) or pattern.fullmatch(c + sample)
                or pattern.fullmatch(sample[:mid] + c + sample[mid:])
                or pattern.fullmatch(sample[:mid] + c + sample[mid + 1:])
                or pattern.fullmatch(sample + c)):
            admitted.add(c)
    assert admitted, name
    assert all(" " <= c <= "~" for c in admitted), sorted(c for c in admitted if not " " <= c <= "~")
    bad = admitted & _PS_FORBIDDEN
    if name == "_PS_ARGUMENT_RE":  # the quote around the launcher path, nothing else
        bad -= {'"'}
    assert not bad, (name, sorted(bad))
    assert not pattern.fullmatch(sample + "$(id)") and not pattern.fullmatch(sample + "\n")


def _ps_value(rng: random.Random, valid: str) -> str:
    r = rng.random()
    if r < 0.35:
        return valid
    if r < 0.8:
        return _mutate(rng, valid)
    return "".join(_hostile_char(rng) for _ in range(rng.randint(0, 30)))


_SPAWN_VALUES = {
    "Task": "task-1234abcd", "Project": "mooniex-agents", "Role": "developer",
    "Branch": "agent/developer-task-1234abcd", "Base": "main",
    "RepoUrl": "git@github.com:PASAKON/Agents-Core", "RepoPath": r"C:\Users\x\repo",
    "WorktreeRoot": r"C:\Users\x\worktrees", "ClaudeArgs": "--model x --effort high",
    "Model": "claude-sonnet-5-5", "Effort": "high",
    "SessionName": "winbox developer (task-1234abcd)", "TaskFile": r"C:\x\state\t.md",
    "Runner": "claude", "RunnerModel": "", "AgentsRoot": r"C:\Users\x\mooniex",
}
_SPAWN_SHAPE = re.compile(r"& '([^']*)'((?: -[A-Za-z]+ '[^']*')*); exit \$LASTEXITCODE")


def _no_forbidden(value: str, allow: frozenset = frozenset()) -> bool:
    return not (set(value) & (_PS_FORBIDDEN - allow))


def test_fuzz_powershell_builders_never_embed_a_value_that_ends_its_literal():
    rng = random.Random(SEED + 11)
    template = nd._one_shot_task_script("Q1Q1Q1", "Q2Q2Q2")
    built = refused = 0
    for i in range(FUZZ_CASES):
        kind = i % 3
        try:
            if kind == 0:
                value = _ps_value(rng, r"C:\Users\x\mooniex\windows\cxo-claude.ps1")
                assert nd._ps_safe("v", value) == value and _no_forbidden(value)
            elif kind == 1:
                name = _ps_value(rng, "mooniex-cxo-cto-abcd1234")
                arg = _ps_value(rng, '-NoProfile -File "C:\\x\\cxo-claude.ps1" -Role cto -Session abcd1234')
                script = nd._one_shot_task_script(name, arg)
                assert script == template.replace("Q1Q1Q1", name).replace("Q2Q2Q2", arg)
                assert _no_forbidden(name) and _no_forbidden(arg, frozenset('"'))
            else:
                values = dict(_SPAWN_VALUES)
                field = rng.choice(list(values))
                values[field] = _ps_value(rng, values[field])
                launcher = _ps_value(rng, r"C:\Users\x\mooniex\windows\spawn-worker.ps1") \
                    if rng.random() < 0.2 else r"C:\Users\x\mooniex\windows\spawn-worker.ps1"
                script = nd._spawn_worker_script(launcher, values)
                m = _SPAWN_SHAPE.fullmatch(script)
                assert m and m.group(1) == launcher, script
                pairs = re.findall(r" -([A-Za-z]+) '([^']*)'", m.group(2))
                want = [(n, values[n]) for n, _ in nd._SPAWN_PARAMS
                        if not (n == "RunnerModel" and not values.get(n))]
                assert pairs == want, script
                assert all(_no_forbidden(v) for _, v in pairs) and _no_forbidden(launcher)
            built += 1
        except nd.Refusal:
            refused += 1
    assert built + refused == FUZZ_CASES >= 5000
    assert built >= 1000 and refused >= 1000, (built, refused)


def test_fuzz_start_clevel_on_windows_builds_only_the_fixed_argument(monkeypatch, wire):
    """The win32 verb end to end: the only thing PowerShell sees is the fixed
    template with an allow-listed role, a generated id and a stored UUID."""
    monkeypatch.setenv("ORG_HOST", "winbox")
    config_mod.self_host.cache_clear()
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    monkeypatch.setattr(session_status, "resume_target", lambda role, sid: UUID)
    scripts = []

    def fake_ps(script, timeout=None):
        scripts.append(script)
        return subprocess.CompletedProcess(["powershell.exe"], 0, "STARTED Running\r\n", "")

    monkeypatch.setattr(nd, "_run_powershell", fake_ps)
    roles = "|".join(map(re.escape, config_mod.live_c_level_roles()))
    shape = re.compile(rf'-NoProfile -ExecutionPolicy Bypass -File "[^"]*" '
                       rf"-Role ({roles}) -Session [0-9a-f]{{8}}( --resume {UUID})?")
    rng = random.Random(SEED + 5)
    accepted = 0
    for i in range(1000):
        roles_list = config_mod.live_c_level_roles()
        base = f"start_clevel {rng.choice(roles_list)}"
        if rng.random() < 0.5:
            base += " --resume " + "".join(rng.choice("0123456789abcdef") for _ in range(8))
        raw = base if i % 3 == 0 else _mutate(rng, base)
        before = len(scripts)
        out, code = nd.run_command(raw)
        if _oracle(raw) is None:
            assert code == 2 and len(scripts) == before, (raw, out)
            continue
        assert code == 0, (raw, out)
        accepted += 1
        (script,) = scripts[before:]
        argument = re.search(r"-Argument '([^']*)'", script).group(1)
        assert shape.fullmatch(argument), argument
        assert _no_forbidden(argument, frozenset('"'))
    assert accepted >= 300
    assert wire.calls == []


def test_fuzz_mesh_build_argv_sends_only_validated_plain_tokens():
    rng = random.Random(SEED + 13)
    prefix = mesh.build_argv("contabo", "probe", ())[:-1]
    assert prefix[0] == "ssh" and prefix[-1] == config_mod.host("contabo")["ssh"]
    built = refused = 0
    for i in range(FUZZ_CASES):
        if i % 2:
            parts = shlex.split(_valid_command(rng))
            if rng.random() < 0.5:
                j = rng.randrange(len(parts))
                parts[j] = _mutate(rng, parts[j])
        else:
            parts = [rng.choice(list(nd.HANDLERS) + _NEAR_VERBS)] + \
                    [rng.choice(_ARG_POOL) for _ in range(rng.randint(0, 3))]
        verb, args = parts[0], tuple(parts[1:])
        try:
            argv = mesh.build_argv("contabo", verb, args)
        except nd.Refusal:
            refused += 1
            continue
        built += 1
        assert argv[:-1] == prefix, argv
        command = argv[-1]
        # Plain tokens only: nothing a remote shell would re-read, even if the
        # forced command were ever missing.
        assert re.fullmatch(r"[a-z_]+( [a-z0-9_-]+)*", command, re.ASCII), command
        assert _oracle(command) == [verb, *args]
    assert built + refused == FUZZ_CASES >= 5000
    assert built >= 1000 and refused >= 1000, (built, refused)


# ---------------------------------------------------------------------------
# 3. no shell, and the authorized_keys lines
# ---------------------------------------------------------------------------

_SHELL_ATTRS = {"system", "popen", "getoutput", "getstatusoutput", "execl", "execle",
                "execlp", "execv", "execve", "execvp", "execvpe", "spawnl", "spawnv",
                "startfile"}


@pytest.mark.parametrize("rel", ["tools/node_dispatch.py", "lib/mesh.py"])
def test_the_dispatch_path_never_hands_a_string_to_a_shell(rel):
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    runs = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword):
            assert node.arg != "shell", f"{rel}:{node.value.lineno} shell="
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in ("os", "subprocess"):
                assert node.attr not in _SHELL_ATTRS, f"{rel}:{node.lineno} {node.attr}"
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
                and node.func.attr in ("run", "Popen", "call", "check_call", "check_output")):
            runs += 1
            first = node.args[0]
            assert not isinstance(first, (ast.Constant, ast.JoinedStr, ast.BinOp)), \
                f"{rel}:{node.lineno} passes a string"
    assert runs >= 1


def test_every_authorized_keys_line_pins_command_from_and_restrict():
    text = (ROOT / "docs" / "ops" / "node-dispatch.md").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines()
             if ln.strip().startswith("command=") and "ssh-ed25519" in ln]
    assert len(lines) >= 2, lines
    for ln in lines:
        opts = ln.split(" ssh-ed25519", 1)[0]
        assert re.search(r'(^|,)from="[^"]+"(,|$)', opts), ln
        assert re.search(r"(^|,)restrict(,|$)", opts), ln
        assert "tools.node_dispatch" in opts, ln
        assert "SSH_ORIGINAL_COMMAND" not in opts, ln  # the caller's text is never on it


# ---------------------------------------------------------------------------
# 4. letters: one delivery per letter
# ---------------------------------------------------------------------------

def _clevel_letter() -> int:
    return db_mod.create_letter("mac", "cto", "hello", to_session="abcd1234",
                                from_role="cmo", from_session="beef0001", from_host="contabo")


def _letter_locks() -> list[dict]:
    with db_mod.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM locks WHERE key LIKE 'letter:%'")]


def _inbox_files(tmp_path) -> list[Path]:
    return [p for p in (tmp_path / "inbox").rglob("*") if p.is_file()]


@pytest.fixture
def live_cto(monkeypatch):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: True)
    monkeypatch.setattr(send_to_cxo, "attempt_wake", lambda *a, **kw: None)


def test_two_overlapping_deliveries_write_the_letter_once(monkeypatch, tmp_path, live_cto):
    real_send = mailbox.send
    entered, release = threading.Event(), threading.Event()
    writes = []

    def slow_send(*a, **kw):
        writes.append(threading.current_thread().name)
        entered.set()
        assert release.wait(10)
        return real_send(*a, **kw)

    monkeypatch.setattr(mailbox, "send", slow_send)
    lid = _clevel_letter()
    first = {}
    a = threading.Thread(name="first", target=lambda: first.update(
        r=nd._run("deliver_letter", [str(lid)])))
    a.start()
    assert entered.wait(10)
    try:
        out, code = nd._run("deliver_letter", [str(lid)])  # while the first is writing
    finally:
        release.set()
        a.join(10)

    assert (code, out["ok"]) == (2, False) and "being delivered by another call" in out["error"]
    assert first["r"][1] == 0 and first["r"][0]["result"]["delivered"] is True
    assert writes == ["first"]
    assert len(_inbox_files(tmp_path)) == 1
    row = db_mod.get_letter(lid)
    assert (row["status"], row["attempts"]) == ("delivered", 0)
    assert _letter_locks() == []
    out, code = nd._run("deliver_letter", [str(lid)])  # a retry after the fact
    assert code == 0 and out["result"] == {"letter_id": lid, "already_delivered": True}
    assert len(_inbox_files(tmp_path)) == 1


def test_a_live_slot_refuses_without_writing_or_counting(tmp_path, live_cto):
    lid = _clevel_letter()
    with db_mod.get_conn() as conn:
        conn.execute("INSERT INTO locks (key, owner, expires_at) VALUES (?,?,?)",
                     (f"letter:{lid}:delivery", "other", "2999-01-01T00:00:00+00:00"))
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 2 and "being delivered" in out["error"]
    row = db_mod.get_letter(lid)
    assert (row["status"], row["attempts"]) == ("pending", 0)
    assert _inbox_files(tmp_path) == []
    assert [r["owner"] for r in _letter_locks()] == ["other"]


def test_a_slot_left_by_a_dead_call_expires(tmp_path, live_cto):
    lid = _clevel_letter()
    with db_mod.get_conn() as conn:
        conn.execute("INSERT INTO locks (key, owner, expires_at) VALUES (?,?,?)",
                     (f"letter:{lid}:delivery", "dead", "2000-01-01T00:00:00+00:00"))
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 0 and out["result"]["delivered"] is True
    assert len(_inbox_files(tmp_path)) == 1 and _letter_locks() == []


def test_a_failed_write_counts_one_attempt_and_frees_the_slot(monkeypatch, tmp_path):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    lid = _clevel_letter()
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 1 and "no live session" in out["error"]
    row = db_mod.get_letter(lid)
    assert (row["status"], row["attempts"]) == ("pending", 1)
    assert _letter_locks() == []


# ---------------------------------------------------------------------------
# 5. queued_remote: one retry per row per pass
# ---------------------------------------------------------------------------

class FakeMesh:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, args))
        raise mesh.MeshUnreachable(f"{verb} on {host}: no route")


def test_every_queued_row_is_retried_exactly_once_per_pass(monkeypatch):
    monkeypatch.setenv(mesh.ENV_FLAG, "1")
    queued = [db_mod.create_task("mooniex-agents", "developer", f"t{i}", "d") for i in range(4)]
    for tid in queued:
        monkeypatch.setattr(mesh, "dispatch", FakeMesh())
        delegate.mesh_spawn_worker(tid, "contabo")
        assert db_mod.get_task(tid)["status"] == "queued_remote"
    foreign = _task("mooniex-agents", status="queued_remote", host="winbox",
                    dispatcher_host="contabo")
    fake = FakeMesh()
    monkeypatch.setattr(mesh, "dispatch", fake)

    for n in (1, 2, 3):
        watchdog._retry_queued_remote()
        per_row = collections.Counter(c[2][0] for c in fake.calls)
        assert per_row == {tid: n for tid in queued}, per_row
    assert all(c[:2] == ("contabo", "spawn_worker") for c in fake.calls)
    assert foreign not in {c[2][0] for c in fake.calls}
    for tid in queued:
        assert db_mod.get_task(tid)["status"] == "queued_remote"
        assert delegate._queued_remote_attempts(tid) == 4


# ---------------------------------------------------------------------------
# 6. audit rows
# ---------------------------------------------------------------------------

def test_audit_rows_keep_fixed_keys_bounded_values_and_no_secret(monkeypatch, wire):
    monkeypatch.setenv("SSH_CLIENT", "100.64.1.2 50000 22")
    cases = ["probe extra", "nope", "spawn_worker task-1234abcd", "deliver_letter 7",
             "pid_alive " + "x" * 240, "a " * 120, "'unbalanced", "x" * 300,
             f"pid_alive {CANARY}", "start_clevel ceo", " ".join(["pid_alive"] + ["a"] * 20)]
    for raw in cases:
        nd.run_command(raw)
    nd.dispatch("pid_alive", ["b" * 1000] * 20)
    events = _events()
    assert len(events) == len(cases) + 1
    for e in events:
        p = e["payload"]
        assert {"verb", "args", "caller", "ok", "error"} <= set(p) <= {
            "verb", "args", "caller", "ok", "error", "raw"}
        assert p["caller"] == "100.64.1.2" and p["ok"] is False
        assert len(p["args"]) <= nd.MAX_LOG_ARGS
        assert all(len(a) <= nd.MAX_COMMAND_CHARS for a in p["args"])
        assert len(p["error"]) <= nd.MAX_ERROR_CHARS
        assert len(p.get("raw") or "") <= nd.MAX_COMMAND_CHARS
    # The canary appears only where the caller typed it, never from the environment.
    assert os.environ["GITHUB_TOKEN"] == CANARY
    typed = [e for e in events if CANARY in json.dumps(e["payload"])]
    assert len(typed) == 1 and typed[0]["payload"]["args"] == [CANARY]
    assert wire.calls == []


def _review_task(tmp_path) -> str:
    tid = _task()
    wt = tmp_path / "worktrees" / f"wt-{tid}"
    wt.mkdir(parents=True)
    _update(tid, host="mac", status="review", branch=f"agent/developer-{tid}", worktree=str(wt))
    return tid


def test_a_token_git_prints_never_reaches_the_reply_or_the_audit_row(monkeypatch, tmp_path):
    token = "ghp_" + "A1b2C3d4" * 5
    stderr = ("remote: Invalid username or password.\n"
              f"fatal: Authentication failed for 'https://x-access-token:{token}"
              "@github.com/PASAKON/Agents-Core.git/'")
    monkeypatch.setattr(subprocess, "run",
                        lambda argv, **kw: subprocess.CompletedProcess(argv, 128, "", stderr))
    tid = _review_task(tmp_path)

    out, code = nd.run_command(f"publish_branch {tid}")

    assert code == 1 and "https://***@github.com" in out["error"]
    blob = json.dumps(out) + json.dumps([e["payload"] for e in _events()])
    assert token not in blob and "x-access-token" not in blob


def test_a_credential_in_an_unparseable_command_is_redacted_in_the_audit_row():
    nd.run_command("probe 'https://user:p4ssw0rd-9f8e@example.com/x")
    (e,) = _events()
    assert "p4ssw0rd-9f8e" not in json.dumps(e["payload"])
    assert "https://***@example.com/x" in e["payload"]["raw"]


@pytest.mark.parametrize("text, secret", [
    ("push to https://bob:hunter2hunter2@github.com/a/b failed", "hunter2hunter2"),
    ("token ghp_" + "Z" * 36, "ghp_" + "Z" * 36),
    ("github_pat_" + "a1_" * 10, "github_pat_" + "a1_" * 10),
    ("key sk-" + "q" * 30 + " rejected", "sk-" + "q" * 30),
    ("Authorization: Bearer " + "e" * 40, "e" * 40),
])
def test_redact_removes_credentials(text, secret):
    assert secret not in nd._redact(text)


@pytest.mark.parametrize("text", [
    "task task-1234abcd is on host 'winbox', this host is 'mac'",
    "git push exit 1: ! [rejected] agent/developer-task-1234abcd (non-fast-forward)",
    "letter 42 is being delivered by another call",
    "git@github.com:PASAKON/Agents-Core.git",
])
def test_redact_leaves_ordinary_errors_alone(text):
    assert nd._redact(text) == text


# ---------------------------------------------------------------------------
# 7. Windows: spawn gating and MAILBOX.md links (CTO-FEEDBACK items 3 and 4)
# ---------------------------------------------------------------------------

@pytest.fixture
def winbox(monkeypatch, wire):
    monkeypatch.setenv("ORG_HOST", "winbox")
    config_mod.self_host.cache_clear()
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    spawned: list[str] = []

    def fake_spawn(task):
        spawned.append(task["id"])
        _update(task["id"], status="in_progress", pid=4242)

    monkeypatch.setattr(nd, "_spawn_worker_windows", fake_spawn)
    return spawned


def test_windows_spawn_refuses_a_row_without_this_host(winbox):
    tid = _task(status="pending")
    out, code = nd._run("spawn_worker", [tid])
    assert code == 2 and "has no host" in out["error"]
    assert winbox == []


@pytest.mark.parametrize("dep_status, allowed", [
    ("pending", False), ("in_progress", False), ("review", False), ("missing", False),
    ("done", True), ("merged", True),
])
def test_windows_spawn_waits_for_unfinished_dependencies(winbox, dep_status, allowed):
    dep = "task-00000000" if dep_status == "missing" else _task(status=dep_status)
    tid = _task(status="pending", host="winbox", depends_on=json.dumps([dep]))
    out, code = nd._run("spawn_worker", [tid])
    if allowed:
        assert code == 0, out
        assert winbox == [tid]
    else:
        assert code == 2 and "unfinished dependencies" in out["error"], out
        assert winbox == []


@pytest.mark.parametrize("other_status, allowed", [
    ("in_progress", False), ("queued_remote", False), ("conflict", False),
    ("review", True), ("done", True),
])
def test_windows_spawn_refuses_touches_that_overlap_a_task_in_flight(
        winbox, other_status, allowed):
    _task(status=other_status, touches=json.dumps(["lib/db.py"]))
    tid = _task(status="pending", host="winbox", touches=json.dumps(["lib/db.py", "x.py"]))
    out, code = nd._run("spawn_worker", [tid])
    assert (code == 0) is allowed, out
    assert winbox == ([tid] if allowed else [])


def test_windows_spawn_passes_a_row_the_hub_gated(winbox):
    tid = _task(status="pending", host="winbox", touches=json.dumps(["x.py"]))
    out, code = nd._run("spawn_worker", [tid])
    assert code == 0 and out["result"]["status"] == "in_progress"
    assert winbox == [tid]


def _worker_with_letter(tmp_path) -> tuple[str, Path, int]:
    tid = _task(host="winbox", status="in_progress")
    wt = tmp_path / "worktrees" / f"projA__developer__{tid}"
    wt.mkdir(parents=True)
    _update(tid, worktree=str(wt))
    lid = db_mod.create_letter("winbox", "developer", "please push", to_session=tid,
                               from_role="cto", from_session="abcd1234")
    return tid, wt, lid


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
def test_mailbox_md_that_is_a_link_is_never_written_through(winbox, tmp_path, link):
    tid, wt, lid = _worker_with_letter(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"keep\n")
    if link == "symlink":
        (wt / "MAILBOX.md").symlink_to(outside)
    else:
        os.link(outside, wt / "MAILBOX.md")

    out, code = nd._run("deliver_letter", [str(lid)])

    assert code == 1 and "is a link" in out["error"], out
    assert outside.read_bytes() == b"keep\n"
    row = db_mod.get_letter(lid)
    assert (row["status"], row["attempts"]) == ("pending", 1)


def test_mailbox_md_plain_file_still_takes_the_letter(winbox, tmp_path):
    tid, wt, lid = _worker_with_letter(tmp_path)
    (wt / "MAILBOX.md").write_bytes(b"earlier\r\n")
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 0, out
    lines = (wt / "MAILBOX.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "earlier" and lines[1].endswith(" | cto-abcd1234 | please push")
