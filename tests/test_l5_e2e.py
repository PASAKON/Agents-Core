"""L5 inside L3's window (tools/mesh_check.py: L5Window, run_l3_probe(l5=...),
l5_window_for, build_matrix) -- the form of L5 that proves the WAKE.

Everything is replaced: the MCP session (a scripted fake), the far side
(`mesh.dispatch`, which also plays the probe worker: it reads the nonce out of
the letter and the scene decides whether the worker copies it into the probe
file), `git` (the probe-file read) and the hub (a tmp_path SQLite ledger).
Nothing dials a host, writes to the live hub or starts a worker.

Run:  .venv/bin/python -m pytest tests/test_l5_e2e.py
"""
from __future__ import annotations

import asyncio
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.mesh_check as m  # noqa: E402
from lib import config as hub_config  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import mesh  # noqa: E402

TID = "task-abc12345"
NONCE_RE = re.compile(r"MESH-NONCE-[0-9a-f]{16}")


@pytest.fixture
def hub(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))
    hub_config.self_host.cache_clear()
    yield db_mod
    hub_config.self_host.cache_clear()


def _letters() -> list[dict]:
    with db_mod.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM letters ORDER BY id").fetchall()]


class _Ctx:
    async def __aenter__(self):
        return (None, None)

    async def __aexit__(self, *exc):
        return False


class Scene:
    """One scripted L3 + L5 run: what the task does, what the far side answers
    and what the worker wrote into the probe file."""

    def __init__(self, monkeypatch, root: Path):
        self.mp = monkeypatch
        self.root = root
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
        self.statuses = ["in_progress", "in_progress", "review"]
        self.reply_extra: dict = {}              # fields merged over the far side's result
        self.drop_woke = False                   # an older node_dispatch: no woke field at all
        self.deliver_raises: Exception | None = None
        self.worker_copies_nonce = True          # does the probe worker write nonce=<token>?
        self.worker_nonce_override: str | None = None
        self.show_fails: str | None = None       # _git_show_from_origin's reason, if it fails
        self.merge_ok = True
        self.on_origin = True
        self.calls: list[tuple] = []             # MCP tool calls: (name, args)
        self.shows: list[tuple] = []             # _git_show_from_origin(rev, path)
        self.far_calls: list[tuple] = []         # mesh.dispatch(host, verb, *args)
        self.seen_nonce: str | None = None       # what the "worker" got from the letter
        self.desc: str | None = None
        self._install()

    # -- fakes -------------------------------------------------------------
    def _mcp(self, name: str, args: dict) -> str:
        self.calls.append((name, args))
        if name == "create_task":
            self.desc = args["description"]
            return TID
        if name == "delegate_task":
            return "status: in_progress"
        if name == "get_task":
            st = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return f"status: {st}\nbranch: agent/probe-{TID}\nhost: contabo"
        if name == "merge_task":
            return ("merged: true\nmerge_sha: deadbeef1234" if self.merge_ok
                    else "merged: false\nreason: conflict")
        raise AssertionError(name)

    def _far(self, host, verb, *args, timeout=None):
        self.far_calls.append((host, verb, args))
        if self.deliver_raises:
            raise self.deliver_raises
        lid = int(args[0])
        letter = db_mod.get_letter(lid)
        found = NONCE_RE.search(letter["body"])
        self.seen_nonce = found.group(0) if found else None
        db_mod.mark_letter_delivered(lid)
        result = {"letter_id": lid, "delivered": True,
                  "to": f"{letter['to_role']}-{letter['to_session']}", "woke": True}
        result.update(self.reply_extra)
        if self.drop_woke:
            result.pop("woke", None)
        return {"ok": True, "verb": verb, "result": result}

    def _show(self, root, rev, path):
        self.shows.append((rev, path))
        if self.show_fails:
            return None, self.show_fails
        line = f"mesh-probe 2026-10-02T00:00:00Z task={TID} ran_on=contabo"
        token = self.worker_nonce_override or self.seen_nonce
        if self.worker_copies_nonce and token:
            line += f" nonce={token}"
        return line + "\n", ""

    def _install(self):
        import mcp
        import mcp.client.stdio as mcp_stdio
        scene = self

        class _Session:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def initialize(self):
                return None

            async def call_tool(self, name, args):
                return types.SimpleNamespace(
                    content=[types.SimpleNamespace(type="text", text=scene._mcp(name, args))])

        async def no_wait(seconds):  # the 15 s poll interval
            return None

        mp = self.mp
        mp.setattr(mcp_stdio, "stdio_client", lambda params: _Ctx())
        mp.setattr(mcp, "ClientSession", _Session)
        mp.setattr(asyncio, "sleep", no_wait)
        mp.setattr(m, "_register_probe_session", lambda session_id, host: None)
        mp.setattr(m, "_git_ls_remote_has", lambda root, sha: self.on_origin)
        mp.setattr(m, "_git_status_porcelain", lambda root: "")
        mp.setattr(m, "_git_show_from_origin", self._show)
        mp.setattr(mesh, "dispatch", self._far)

    def run(self, no_merge: bool = False, to: str = "contabo"):
        window = m.L5Window("mac", to)
        ok, reason = asyncio.run(m.run_l3_probe("mac", to, self.root, "w3", no_merge, window))
        return ok, reason, window


@pytest.fixture
def scene(hub, monkeypatch, tmp_path):
    return Scene(monkeypatch, tmp_path)


# ---------------------------------------------------------------------------
# green
# ---------------------------------------------------------------------------

def test_green_when_the_letter_is_delivered_the_wake_is_true_and_the_nonce_is_on_origin(scene):
    ok, reason, window = scene.run()
    assert (ok, reason) == (True, None)
    assert window.cell == {"ok": True, "reason": None, "note": "woke, nonce read back from origin"}
    (letter,) = _letters()
    assert letter["status"] == "delivered"
    assert (letter["to_host"], letter["to_role"], letter["to_session"]) == ("contabo", "probe", TID)
    assert (letter["from_host"], letter["from_role"]) == ("mac", "mesh_check")
    assert NONCE_RE.search(letter["body"]).group(0) == window.nonce
    assert scene.shows == [("deadbeef1234", "docs/ops/mesh-probe/mac-contabo.md")]


def test_the_nonce_is_in_the_letter_and_never_in_the_probe_task_description(scene):
    _, _, window = scene.run()
    assert NONCE_RE.search(scene.desc) is None and window.nonce not in scene.desc
    # ... but the description tells the worker a letter is coming and what to do with it
    for needle in ("MESH-NONCE-", "nonce=<token>", "sleep 15", "120 s", "mailbox"):
        assert needle in scene.desc, needle
    assert "Commit with a message starting `mesh-probe:`" in scene.desc


def test_the_letter_goes_out_once_even_though_the_task_is_polled_in_progress_many_times(scene):
    scene.statuses = ["in_progress"] * 5 + ["review"]
    _, _, window = scene.run()
    assert len(_letters()) == 1 and len(scene.far_calls) == 1
    assert window.cell["ok"] is True


def test_the_letter_waits_for_in_progress_and_goes_out_before_review(scene):
    scene.statuses = ["pending", "in_progress", "review"]
    scene.run()
    assert [c[0] for c in scene.calls].count("get_task") == 3
    assert len(scene.far_calls) == 1 and scene.far_calls[0][:2] == ("contabo", "deliver_letter")


def test_the_letter_uses_the_role_the_probe_task_was_created_with(scene, monkeypatch):
    monkeypatch.setattr(m, "_role_exists", lambda name: False)  # no `probe` role: developer
    _, _, window = scene.run()
    assert {c[1]["role"] for c in scene.calls if c[0] == "create_task"} == {"developer"}
    assert _letters()[0]["to_role"] == "developer"
    assert window.cell["ok"] is True


# ---------------------------------------------------------------------------
# red: each step of the proof, alone
# ---------------------------------------------------------------------------

def test_red_when_the_reply_has_no_woke_field(scene):
    scene.drop_woke = True
    ok, _, window = scene.run()
    assert ok is True                                    # L3 is not L5's judge
    assert window.cell["ok"] is False and "kind" not in window.cell
    assert "does not say woke: true" in window.cell["reason"] and "no woke field" in window.cell["reason"]


def test_red_when_woke_is_false_with_a_reason(scene):
    scene.reply_extra = {"woke": False, "why": "tmux nudge not delivered (session gone)"}
    _, _, window = scene.run()
    assert window.cell["ok"] is False
    assert "wake failed" in window.cell["reason"] and "session gone" in window.cell["reason"]
    assert [r["status"] for r in _letters()] == ["delivered"]  # a delivered row is never rewritten
    assert scene.shows == []  # nothing to look for in the probe file


def test_red_when_woke_is_false_without_a_reason_on_a_posix_host(scene):
    scene.reply_extra = {"woke": False}
    _, _, window = scene.run()
    assert window.cell["ok"] is False and "woke=False" in window.cell["reason"]


def test_red_when_the_worker_never_copied_the_nonce(scene):
    scene.worker_copies_nonce = False
    ok, _, window = scene.run()
    assert ok is True
    assert window.cell["ok"] is False and "kind" not in window.cell
    assert "no nonce" in window.cell["reason"] and "did not read the letter" in window.cell["reason"]


def test_red_when_the_probe_file_carries_another_nonce(scene):
    scene.worker_nonce_override = "MESH-NONCE-0000000000000000"
    _, _, window = scene.run()
    assert window.cell["ok"] is False
    assert "not the one in the letter" in window.cell["reason"]
    assert "MESH-NONCE-0000000000000000" in window.cell["reason"]


def test_red_when_the_probe_file_cannot_be_read_back_from_origin(scene):
    scene.show_fails = "git show deadbeef1234:docs/ops/mesh-probe/mac-contabo.md: path does not exist"
    ok, _, window = scene.run()
    assert ok is True
    assert window.cell["ok"] is False
    assert "could not be read back from origin" in window.cell["reason"] and "does not exist" in window.cell["reason"]


def test_red_when_the_far_side_delivered_it_to_somebody_else(scene):
    scene.reply_extra = {"to": "probe-task-ffffffff"}
    _, _, window = scene.run()
    assert window.cell["ok"] is False and "expected probe-" in window.cell["reason"]


def test_red_when_the_hub_row_is_not_delivered_and_the_letter_is_abandoned(scene):
    scene.mp.setattr(db_mod, "mark_letter_delivered", lambda lid: True)  # the far side lies
    _, _, window = scene.run()
    assert window.cell["ok"] is False and "hub row is 'pending'" in window.cell["reason"]
    assert [r["status"] for r in _letters()] == ["failed"]


def test_red_when_the_far_side_says_already_delivered_because_no_wake_was_seen(scene):
    def far(host, verb, *args, timeout=None):
        db_mod.mark_letter_delivered(int(args[0]))
        return {"ok": True, "verb": verb, "result": {"letter_id": int(args[0]), "already_delivered": True}}

    scene.mp.setattr(mesh, "dispatch", far)
    _, _, window = scene.run()
    assert window.cell["ok"] is False and "no woke field" in window.cell["reason"]


def test_a_windows_worker_is_not_woken_by_design_so_a_bare_woke_false_is_not_a_red(scene):
    scene.reply_extra = {"woke": False}
    _, _, window = scene.run(to="winbox")
    assert window.cell == {"ok": True, "reason": None,
                           "note": "wake n/a: Windows worker reads MAILBOX.md, nonce read back from origin"}


def test_a_windows_worker_still_needs_the_nonce(scene):
    scene.reply_extra = {"woke": False}
    scene.worker_copies_nonce = False
    _, _, window = scene.run(to="winbox")
    assert window.cell["ok"] is False and "no nonce" in window.cell["reason"]


def test_a_windows_worker_with_a_failed_wake_reason_is_still_red(scene):
    scene.reply_extra = {"woke": False, "why": "wake raised OSError"}
    _, _, window = scene.run(to="winbox")
    assert window.cell["ok"] is False and "wake failed" in window.cell["reason"]


# ---------------------------------------------------------------------------
# unreachable and L3-failure shapes
# ---------------------------------------------------------------------------

def test_unreachable_when_the_far_side_gives_no_answer_and_the_letter_is_abandoned(scene):
    scene.deliver_raises = mesh.MeshUnreachable("deliver_letter on contabo: no reply in 60s")
    ok, reason, window = scene.run()
    assert (ok, reason) == (True, None)                  # L3 itself still passed
    assert window.cell["ok"] is False and window.cell["kind"] == "unreachable"
    assert [r["status"] for r in _letters()] == ["failed"]
    assert scene.shows == []


def test_unreachable_when_the_letter_cannot_be_written_to_the_hub(scene):
    def boom(*a, **kw):
        raise RuntimeError("hub down")

    scene.mp.setattr(db_mod, "create_letter", boom)
    ok, _, window = scene.run()
    assert ok is True
    assert window.cell["kind"] == "unreachable" and "hub write failed" in window.cell["reason"]
    assert scene.far_calls == []


def test_an_l5_bug_never_fails_l3(scene):
    def bug(*a, **k):
        raise ValueError("boom")

    scene.mp.setattr(m, "_l5_deliver", bug)
    ok, reason, window = scene.run()
    assert (ok, reason) == (True, None)
    assert window.cell["ok"] is False and "L5 letter step failed: ValueError" in window.cell["reason"]


def test_red_and_no_letter_when_the_task_never_gets_to_in_progress(scene):
    scene.statuses = ["failed"]
    ok, reason, window = scene.run()
    assert ok is False and "failed" in reason
    assert window.cell["ok"] is False and "kind" not in window.cell
    assert "no letter was sent" in window.cell["reason"] and "task ended in status=failed" in window.cell["reason"]
    assert _letters() == [] and scene.far_calls == []


def test_red_when_l3_fails_after_the_letter_and_the_file_never_reaches_origin(scene):
    scene.on_origin = False
    ok, reason, window = scene.run()
    assert ok is False and "not found on origin" in reason
    assert window.cell["ok"] is False
    assert "could not be read back from origin" in window.cell["reason"]
    assert scene.shows == []                     # no merge sha on origin: nothing to read from


def test_red_when_the_merge_fails(scene):
    scene.merge_ok = False
    ok, reason, window = scene.run()
    assert ok is False and "merge failed" in reason
    assert window.cell["ok"] is False and "could not be read back" in window.cell["reason"]


def test_no_merge_reads_the_probe_file_from_the_workers_branch_on_origin(scene):
    ok, reason, window = scene.run(no_merge=True)
    assert (ok, reason) == (True, None)
    assert not [c for c in scene.calls if c[0] == "merge_task"]
    assert scene.shows == [(f"origin/agent/probe-{TID}", "docs/ops/mesh-probe/mac-contabo.md")]
    assert window.cell["ok"] is True


def test_run_l3_probe_without_a_window_is_exactly_what_it_was(scene):
    ok, reason = asyncio.run(m.run_l3_probe("mac", "contabo", scene.root, "w3", False))
    assert (ok, reason) == (True, None)
    assert scene.far_calls == [] and scene.shows == [] and _letters() == []
    assert "nonce" not in scene.desc and "letter" not in scene.desc


# ---------------------------------------------------------------------------
# the probe-file read itself (git is faked at the subprocess edge)
# ---------------------------------------------------------------------------

class _Git:
    def __init__(self, fetch_rc=0, show_rc=0, show_out="line\n", raise_on=None):
        self.argvs, self.fetch_rc, self.show_rc = [], fetch_rc, show_rc
        self.show_out, self.raise_on = show_out, raise_on

    def __call__(self, argv, **kw):
        import subprocess
        self.argvs.append(list(argv))
        if self.raise_on == argv[1]:
            raise subprocess.TimeoutExpired(argv, 1)
        if argv[1] == "fetch":
            return subprocess.CompletedProcess(argv, self.fetch_rc, "", "fetch refused")
        return subprocess.CompletedProcess(argv, self.show_rc, self.show_out, "fatal: path missing")


def test_git_show_from_origin_fetches_then_shows_the_path_at_the_rev(monkeypatch, tmp_path):
    git = _Git()
    monkeypatch.setattr(m.subprocess, "run", git)
    assert m._git_show_from_origin(tmp_path, "abc123", "docs/x.md") == ("line\n", "")
    assert git.argvs == [["git", "fetch", "--quiet", "origin"], ["git", "show", "abc123:docs/x.md"]]


def test_git_show_from_origin_names_a_failed_fetch_only_when_the_show_fails_too(monkeypatch, tmp_path):
    monkeypatch.setattr(m.subprocess, "run", _Git(fetch_rc=1))
    assert m._git_show_from_origin(tmp_path, "abc123", "docs/x.md") == ("line\n", "")  # show decides
    monkeypatch.setattr(m.subprocess, "run", _Git(fetch_rc=1, show_rc=128))
    text, why = m._git_show_from_origin(tmp_path, "abc123", "docs/x.md")
    assert text is None and "path missing" in why and "git fetch origin failed" in why


@pytest.mark.parametrize("where", ["fetch", "show"])
def test_git_show_from_origin_never_raises_on_a_timeout(monkeypatch, tmp_path, where):
    monkeypatch.setattr(m.subprocess, "run", _Git(raise_on=where))
    text, why = m._git_show_from_origin(tmp_path, "abc123", "docs/x.md")
    if where == "show":
        assert text is None and "TimeoutExpired" in why
    else:
        assert text == "line\n"          # the fetch failed, the show still answered


def test_read_probe_is_skipped_when_no_letter_was_delivered(monkeypatch, tmp_path):
    w = m.L5Window("mac", "contabo")
    monkeypatch.setattr(m, "_git_show_from_origin", lambda *a: pytest.fail("read with no letter"))
    w.read_probe(tmp_path, "abc", "p.md")                         # never sent
    w.delivery = m._red("wake failed")
    w.read_probe(tmp_path, "abc", "p.md")


def test_read_probe_without_a_rev_says_why(monkeypatch, tmp_path):
    w = m.L5Window("mac", "contabo")
    w.delivery = m._green("woke")
    w.read_probe(tmp_path, None, "p.md")
    w.close(None)
    assert w.cell["ok"] is False and "no branch or merge sha" in w.cell["reason"]


def test_close_is_idempotent(hub):
    w = m.L5Window("mac", "contabo")
    w.close("task ended in status=failed")
    first = w.cell
    w.delivery = m._green("woke")
    w.close(None)
    assert w.cell is first


# ---------------------------------------------------------------------------
# which pairs get a window, and how build_matrix / _run_mesh_levels use it
# ---------------------------------------------------------------------------

def test_a_window_only_when_l3_and_l5_are_both_claimed_and_the_target_can_be_dialled():
    w = m.l5_window_for("mac", "contabo", "w2")
    assert isinstance(w, m.L5Window) and (w.from_host, w.to_host) == ("mac", "contabo")
    assert NONCE_RE.fullmatch(w.nonce)
    assert m.l5_window_for("mac", "contabo", "w1") is None      # L5 not claimed before w2
    assert m.l5_window_for("mac", "winbox", "w2") is None       # L5 into winbox is w3
    assert m.l5_window_for("mac", "winbox", "w3") is not None
    assert m.l5_window_for("contabo", "mac", "w2") is None      # mac has no mesh_ssh: closed
    assert m.l5_window_for("mac", "mac", "w3") is None          # nothing to deliver to yourself


def test_no_window_for_a_host_the_config_does_not_know(monkeypatch):
    monkeypatch.setattr(m, "_in_scope", lambda *a: True)
    assert m.l5_window_for("mac", "nowhere", "w5") is None


def test_each_window_gets_its_own_nonce():
    assert len({m.L5Window("mac", "contabo").nonce for _ in range(20)}) == 20


def _live_matrix(monkeypatch, expect, l3_stub):
    calls: list = []
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "mac")
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))

    async def l2(root):
        return (True, None)

    monkeypatch.setattr(m, "check_l2", l2)
    monkeypatch.setattr(m, "check_l1", lambda t: (True, None))
    monkeypatch.setattr(m, "l4_probe", lambda a, b: (True, None))
    monkeypatch.setattr(m, "_collect_peer_local", lambda alias, cfg, script_path: None)
    monkeypatch.setattr(m, "run_l3_probe", l3_stub)
    monkeypatch.setattr(m, "check_invariant", lambda: m._green("0 rows"))
    monkeypatch.setattr(m, "check_l8", lambda state_dir: m._green())
    monkeypatch.setattr(m, "check_sec", lambda to: m._green())
    monkeypatch.setattr(m, "l5_probe", lambda a, b: calls.append(("l5_probe", a, b)) or m._green("standalone"))
    monkeypatch.setattr(m, "l6_probe", lambda h: m._green())
    monkeypatch.setattr(m, "l7_probe", lambda cases: {c[0]: m._green() for c in cases})
    args = types.SimpleNamespace(live=True, expect=expect, no_merge=False)
    combined, _ = asyncio.run(m.build_matrix(args))
    return combined, calls


def test_build_matrix_takes_the_l5_cell_from_the_window_and_does_not_ask_l5_again(monkeypatch):
    seen: list = []

    async def l3(frm, to, root, expect, no_merge, l5=None):
        seen.append((to, l5))
        if l5 is not None:
            l5.cell = m._green("from the window")
        return True, None

    combined, calls = _live_matrix(monkeypatch, "w2", l3)
    assert combined["L5"]["mac"]["contabo"] == {"ok": True, "reason": None, "note": "from the window"}
    assert ("l5_probe", "mac", "contabo") not in calls          # not asked twice
    assert {to for to, w in seen if w is not None} == {"contabo"}   # not mac itself, not winbox (w3)
    assert "winbox" not in combined["L5"]["mac"]


def test_build_matrix_opens_a_window_for_winbox_once_w3_claims_it(monkeypatch):
    seen: dict = {}

    async def l3(frm, to, root, expect, no_merge, l5=None):
        seen[to] = l5
        return True, None

    _live_matrix(monkeypatch, "w3", l3)
    assert isinstance(seen["contabo"], m.L5Window) and isinstance(seen["winbox"], m.L5Window)
    assert seen["mac"] is None


def test_a_pair_whose_l3_left_no_l5_cell_falls_back_to_the_standalone_l5(monkeypatch):
    async def l3(frm, to, root, expect, no_merge, l5=None):
        return True, None                                       # window.cell stays None

    combined, calls = _live_matrix(monkeypatch, "w2", l3)
    assert ("l5_probe", "mac", "contabo") in calls
    assert combined["L5"]["mac"]["contabo"]["note"] == "standalone"


def test_without_l3_in_scope_l5_keeps_the_standalone_form(monkeypatch):
    """--expect w1 claims no L5 at all; the pair gets neither a window nor a letter."""
    seen: list = []

    async def l3(frm, to, root, expect, no_merge, l5=None):
        seen.append(l5)
        return True, None

    combined, calls = _live_matrix(monkeypatch, "w1", l3)
    assert seen and all(w is None for w in seen)
    assert calls == [] and combined["L5"]["mac"] == {}


def test_the_window_cell_renders_with_its_note_and_counts_as_ok():
    combined = {lvl: ({"all": {}} if lvl in m.SINGLE_LEVELS else {h: {} for h in m.HOSTS})
                for lvl in m.LEVELS}
    combined["L5"]["mac"]["contabo"] = m._green("woke, nonce read back from origin")
    md, any_fail, n_ok, n_fail = m.render(combined, "w2")
    assert "ok (woke, nonce read back from origin)" in md
    assert any_fail is False and n_fail == 0 and n_ok >= 1
