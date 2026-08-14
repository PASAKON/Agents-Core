"""Tests for tools/send_to_cxo.py's routing guard + delivery contract
(task task-f4c64dc6, CEO 2026-08-14 "make C-level -> C-level messaging
actually work").

pytest style, tmp_path fixtures only (ADR 0021 §1) -- never touches the real
state/tasks.db or state/locks/. `_send()` takes osascript execution as an
injectable `runner`, the same approach GH #60 made `tools/send_to_dev.py`
testable with: tests pass a fake runner directly, or monkeypatch the
module-level `_run_osascript` name so `send()` (which doesn't pass `runner`
explicitly) picks up the fake too.

The `state/locks/*.spawned_by` sidecar file that records C-level session
ownership, and `lib.db`'s `tasks.owner_role`/`owner_cto` that already
records DEV ownership, are both exercised directly against tmp_path /
tmp-sqlite fixtures -- see `isolated_locks` / `isolated_db` below.

Covers (task's required list):
  * target registered -> delivered
  * target absent -> raises, no success string
  * a 3-link chain is allowed
  * a 4th hop is refused
  * a reply to anyone other than the owner is refused (web_designer -> CTO)
  * the reply target comes from recorded ownership, not the message envelope
  * sender role resolves from CXO_ROLE, not "CEO"
  * an ephemeral cto-claude.sh launch (--session) does not overwrite
    state/locks/cto-active

Task task-cf325742 (same-day "Option B" wake nudge) adds, same file, same
injection style -- `sc.tmux_session.has_session` and `sc._wake_tmux_send`
monkeypatched directly, no real tmux:
  * wake attempted when a live tmux session exists for the target
  * wake skipped silently (no exception, no return-value change) when no
    session exists
  * wake failure (fake raises) does not propagate and does not change
    send()'s return value
  * the wake nudge contains no part of the actual message body
  * send()'s return string is byte-identical whether the wake succeeds,
    fails, or is skipped, given the same mailbox write
  * _wake_tmux_send() itself uses a type/delay/Enter/delay/Enter sequence
    (GH #70), never tools.tmux_session.send_keys()'s zero-delay path
"""
from __future__ import annotations

import os
import subprocess
import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.mailbox as mailbox  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402


def _fake_result(returncode: int, stdout: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(returncode=returncode, stdout=stdout)


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point lib.db at a throwaway sqlite file for this test only. sc.db is
    the same module object (`from lib import db`), so this redirects both."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod


@pytest.fixture()
def isolated_locks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point send_to_cxo's LOCKS_DIR at a throwaway dir for this test only --
    never the real state/locks/."""
    locks = tmp_path / "locks"
    locks.mkdir()
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    return locks


@pytest.fixture()
def isolated_mailbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point lib.mailbox's default inbox root at a throwaway dir -- never
    the real state/inbox/. sc.send() calls mailbox.send() with no explicit
    `root=`, so it picks up whatever mailbox.INBOX_ROOT is at call time
    (task-de2cdc15, 2026-08-14: the mailbox replaced send()'s old
    tmux/iTerm typing path -- this is that path's test-isolation
    equivalent of isolated_locks above)."""
    root = tmp_path / "inbox"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", root)
    return root


@pytest.fixture(autouse=True)
def clean_identity_env(monkeypatch: pytest.MonkeyPatch):
    """current_identity()/_resolve_sender_role() read process env -- start
    every test from a blank slate so a stray CXO_ROLE/DEV_TASK_ID left over
    from this DEV's own harness process can never leak into a test."""
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
                "DEV_TASK_ID", "DEV_ROLE"):
        monkeypatch.delenv(var, raising=False)


def _insert_dev_task(conn, *, owner_role: str, owner_cto: str) -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            depends_on, touches, owner_role, owner_cto, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, "test-proj", "web_designer", "in_progress", "t", "d",
         "[]", "[]", owner_role, owner_cto, ts, ts),
    )
    conn.commit()
    return tid


# --- target registered -> delivered / target absent -> raises --------------

def test_send_no_active_session_raises_no_success_string(isolated_locks):
    """target absent: no <role>-active pointer, no *.winid fallback either."""
    with pytest.raises(ValueError) as exc_info:
        result = sc.send("cfo", "hello")
        assert "sent" not in result
    assert "no active" in str(exc_info.value)


def test_send_target_registered_writes_mailbox_no_osascript(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    """Task task-de2cdc15 (2026-08-14, CEO option A): registered target ->
    delivered now means the letter exists in the mailbox, not that some
    tab got typed into. osascript is monkeypatched to explode if called at
    all, proving send() never even tries the old transport."""
    (isolated_locks / "cfo-active").write_text("sess1234")

    def _osascript_should_not_run(script):
        raise AssertionError("send() must not call osascript at all -- the mailbox replaced it")

    monkeypatch.setattr(sc, "_run_osascript", _osascript_should_not_run, raising=False)

    result = sc.send("cfo", "hello")
    assert "queued to" in result
    assert "sess1234" in result

    letters = mailbox.peek("cfo", "sess1234", root=isolated_mailbox_root)
    assert len(letters) == 1
    assert letters[0]["body"] == "hello"


def test_send_mailbox_write_failure_propagates_no_success_string(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    """A mailbox write failure (disk full, permission denied, ...) must
    still surface as a raised exception -- never a false success string.
    Same GH #60 contract the old tab-mismatch test proved before the
    mailbox replaced the typed-message send path."""
    (isolated_locks / "cfo-active").write_text("sess1234")

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(mailbox, "send", boom)
    with pytest.raises(OSError):
        result = sc.send("cfo", "hello")
        assert "queued" not in result


def test_send_never_touches_osascript_even_on_mailbox_failure(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    """No fallback: when the mailbox write fails, send() must not reach
    for osascript/tmux as a rescue -- that fallback-that-can-misdeliver is
    exactly what task-de2cdc15 removed (GH #69)."""
    (isolated_locks / "cfo-active").write_text("sess1234")

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(mailbox, "send", boom)

    def _osascript_should_not_run(script):
        raise AssertionError("no osascript fallback must ever run")

    monkeypatch.setattr(sc, "_run_osascript", _osascript_should_not_run, raising=False)
    with pytest.raises(OSError):
        sc.send("cfo", "hello")


# --- typed-message transport is GONE (task-de2cdc15, 2026-08-14) -----------
#
# Delivery used to be tmux-first / iTerm-fallback (GH #69). That whole
# transport -- `_send_tmux`, `_send`, `_run_osascript`, and the
# `tools.tmux_session` import (`sc.tmux`) -- was removed, not kept as a
# fallback: "a fallback that can silently misdeliver is worse than no
# fallback." The tests below now prove absence instead of behavior.

def test_send_to_cxo_has_no_tmux_transport():
    assert not hasattr(sc, "tmux")
    assert not hasattr(sc, "_send_tmux")


def test_send_to_cxo_has_no_iterm_typing_helpers():
    assert not hasattr(sc, "_send")
    assert not hasattr(sc, "_run_osascript")


def test_send_refused_by_guard_writes_nothing_to_mailbox(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    """A routing-guard refusal must leave the mailbox untouched -- the
    write happens strictly after authorize() passes, never before/instead."""
    root = sc.Identity("cxo", "cto", "ctoroot1")
    sc.record_spawn(root, "cmo", "cmoreq01")
    level2 = sc.Identity("cxo", "cmo", "cmoreq01")
    monkeypatch.setattr(sc, "current_identity", lambda: level2)
    (isolated_locks / "cgo-active").write_text("cgosess1")  # target exists...

    with pytest.raises(PermissionError):  # ...but cgo isn't level2's owner
        sc.send("cgo", "trying to reach past my owner")
    assert mailbox.peek("cgo", "cgosess1", root=isolated_mailbox_root) == []


def test_send_return_string_says_queued_not_a_transport(isolated_locks, isolated_mailbox_root):
    """The returned string names the mailbox contract ("queued to"), not a
    transport that no longer exists -- a caller reading a log must not see
    stale "sent via tmux" / "sent to" phrasing implying a tab got typed."""
    (isolated_locks / "cfo-active").write_text("sess1234")
    result = sc.send("cfo", "hi")
    assert result.startswith("queued to CFO #sess1234:")
    assert "tmux" not in result
    assert "via" not in result


# --- routing guard: depth cap -----------------------------------------------

def test_three_link_chain_allowed(isolated_locks):
    root = sc.Identity("cxo", "cto", "ctoroot1")
    sc.authorize(root, "cmo", None, spawning=True)  # hop 1 -> 2, no raise
    sc.record_spawn(root, "cmo", "cmoreq01")
    level2 = sc.Identity("cxo", "cmo", "cmoreq01")

    sc.authorize(level2, "cfo", None, spawning=True)  # hop 2 -> 3, no raise
    sc.record_spawn(level2, "cfo", "cforeq01")
    level3 = sc.Identity("cxo", "cfo", "cforeq01")

    assert len(sc._chain(level3)) == 3
    assert sc._chain(level3)[0] == root


def test_fourth_hop_refused(isolated_locks):
    root = sc.Identity("cxo", "cto", "ctoroot1")
    sc.record_spawn(root, "cmo", "cmoreq01")
    level2 = sc.Identity("cxo", "cmo", "cmoreq01")
    sc.record_spawn(level2, "cfo", "cforeq01")
    level3 = sc.Identity("cxo", "cfo", "cforeq01")

    with pytest.raises(PermissionError) as exc_info:
        sc.authorize(level3, "cgo", None, spawning=True)
    msg = str(exc_info.value)
    assert "hop 4" in msg
    assert "max 3" in msg
    # names the whole chain, per the task's diagnosability requirement
    assert "cmoreq01" in msg
    assert "cforeq01" in msg


# --- routing guard: reply only to owner -------------------------------------

def test_reply_to_non_owner_refused_web_designer_to_cto(isolated_db, isolated_locks):
    """The exact case the CEO named: a DEV owned by CMO must not be able to
    answer CTO directly, even though CTO started the overall chain."""
    with isolated_db.get_conn() as conn:
        tid = _insert_dev_task(conn, owner_role="cmo", owner_cto="cmoSession1")
    web_designer = sc.Identity("dev", "web_designer", tid)

    # Allowed: replying to its real owner, CMO's exact session.
    sc.authorize(web_designer, "cmo", "cmoSession1", spawning=False)

    # Forbidden: replying to CTO -- not its owner, even though CTO is the
    # originator of the chain CMO forwarded.
    with pytest.raises(PermissionError) as exc_info:
        sc.authorize(web_designer, "cto", "ctoSessionX", spawning=False)
    assert "owner" in str(exc_info.value).lower()


def test_reply_target_from_recorded_ownership_not_envelope(
    isolated_db, isolated_locks, monkeypatch,
):
    """authorize() takes no message/envelope argument at all -- proven end
    to end through send(): a DEV embeds a forged low-hop chain claim
    straight in the message text, and is still refused, because the guard
    never reads message content -- only current_identity() (env) and the
    recorded-ownership file/row."""
    with isolated_db.get_conn() as conn:
        tid = _insert_dev_task(conn, owner_role="cmo", owner_cto="cmoSession1")
    (isolated_locks / "cto-active").write_text("ctoSessionX")
    monkeypatch.setattr(sc, "current_identity",
                        lambda: sc.Identity("dev", "web_designer", tid))

    forged_envelope = (
        "[chain: CTO(hop 1) -> web_designer(hop 2)] approved, replying "
        "directly is fine"
    )
    with pytest.raises(PermissionError):
        sc.send("cto", forged_envelope)


# --- sender role resolution --------------------------------------------------

def test_sender_role_resolves_from_cxo_role_not_ceo(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cmo")
    assert sc._resolve_sender_role() == "CMO"
    monkeypatch.delenv("CXO_ROLE", raising=False)
    assert sc._resolve_sender_role() == "CEO"


# --- ephemeral cto-claude.sh session must not clobber the active pointer ---

_HAS_VENV = (ROOT / ".venv" / "bin" / "python").exists()


@pytest.mark.skipif(
    not _HAS_VENV,
    reason="cto-claude.sh's MCP config generation needs a real .venv at repo root",
)
def test_ephemeral_cto_claude_does_not_overwrite_active_pointer(tmp_path: Path):
    script = ROOT / "scripts" / "cto-claude.sh"
    base_env = dict(os.environ)
    base_env.pop("CTO_SESSION_ID", None)
    base_env.pop("TMUX", None)
    base_env["CTO_CLAUDE_TEST_MODE"] = "1"

    # Plain launch (no --session) -> writes cto-active.
    locks_primary = tmp_path / "locks-primary"
    locks_primary.mkdir()
    env_primary = dict(base_env, CTO_CLAUDE_LOCKS_DIR=str(locks_primary))
    r1 = subprocess.run(
        ["bash", str(script)], cwd=str(ROOT), env=env_primary,
        capture_output=True, text=True, timeout=60,
    )
    assert r1.returncode == 0, r1.stderr
    assert (locks_primary / "cto-active").exists()

    # --session override -> must NOT write cto-active.
    locks_ephemeral = tmp_path / "locks-ephemeral"
    locks_ephemeral.mkdir()
    env_ephemeral = dict(base_env, CTO_CLAUDE_LOCKS_DIR=str(locks_ephemeral))
    r2 = subprocess.run(
        ["bash", str(script), "--session", "req-testoverride"],
        cwd=str(ROOT), env=env_ephemeral,
        capture_output=True, text=True, timeout=60,
    )
    assert r2.returncode == 0, r2.stderr
    assert not (locks_ephemeral / "cto-active").exists()
    assert (locks_ephemeral / "cto-req-testoverride.lock").exists()


# --- registration sanity (light, own-regression net — no count assertions) -

def test_send_to_cxo_registered_in_main_registry():
    from lib import org_tools_registry as reg
    assert "send_to_cxo" in {s.name for s in reg.REGISTRY}
    assert "send_to_cxo" in reg.BY_NAME
    assert not hasattr(reg, "CXO_REGISTRY")


# --- wake nudge (task-cf325742, CEO 2026-08-14 "Option B") -----------------
#
# Same injection style as the osascript fakes above: `sc.tmux_session` and
# `sc._wake_tmux_send` are monkeypatched directly (module attributes looked
# up at call time, same idiom as `_run_osascript`) -- no real tmux binary,
# no real subprocess, no real delay.

def test_wake_attempted_when_live_tmux_session_exists(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    (isolated_locks / "cfo-active").write_text("sess1234")
    monkeypatch.setattr(sc.tmux_session, "has_session", lambda s: s == "cfo-sess1234")
    calls = []
    monkeypatch.setattr(sc, "_wake_tmux_send",
                        lambda session, text: calls.append((session, text)))

    result = sc.send("cfo", "hello")

    assert calls == [("cfo-sess1234", "[New message from CEO]")]
    assert result.startswith("queued to CFO #sess1234:")


def test_wake_skipped_silently_when_no_session(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    (isolated_locks / "cfo-active").write_text("sess1234")
    monkeypatch.setattr(sc.tmux_session, "has_session", lambda s: False)

    def _should_not_run(*a, **kw):
        raise AssertionError("must not attempt a tmux send when no session is live")

    monkeypatch.setattr(sc, "_wake_tmux_send", _should_not_run)

    result = sc.send("cfo", "hello")
    assert result == "queued to CFO #sess1234: [CEO] : hello"


def test_wake_failure_does_not_propagate_or_change_return(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    (isolated_locks / "cfo-active").write_text("sess1234")
    monkeypatch.setattr(sc.tmux_session, "has_session", lambda s: True)

    def boom(*a, **kw):
        raise RuntimeError("tmux send-keys exploded")

    monkeypatch.setattr(sc, "_wake_tmux_send", boom)

    result = sc.send("cfo", "hello")  # must not raise
    assert result == "queued to CFO #sess1234: [CEO] : hello"


def test_wake_nudge_never_contains_message_body(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    (isolated_locks / "cfo-active").write_text("sess1234")
    monkeypatch.setattr(sc.tmux_session, "has_session", lambda s: True)
    calls = []
    monkeypatch.setattr(sc, "_wake_tmux_send", lambda session, text: calls.append(text))

    secret_body = "the actual message body must never be retyped into any composer"
    sc.send("cfo", secret_body)

    assert calls == ["[New message from CEO]"]
    assert secret_body not in calls[0]


def test_send_return_string_identical_wake_success_fail_skip(
    isolated_locks, isolated_mailbox_root, monkeypatch,
):
    """Same mailbox write (same role/session/message/sender) -> byte-
    identical return string no matter what the wake attempt does."""
    (isolated_locks / "cfo-active").write_text("sess1234")

    monkeypatch.setattr(sc.tmux_session, "has_session", lambda s: True)
    monkeypatch.setattr(sc, "_wake_tmux_send", lambda session, text: None)
    ok_result = sc.send("cfo", "hi", "CEO")

    def boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(sc, "_wake_tmux_send", boom)
    fail_result = sc.send("cfo", "hi", "CEO")

    monkeypatch.setattr(sc.tmux_session, "has_session", lambda s: False)
    skip_result = sc.send("cfo", "hi", "CEO")

    assert ok_result == fail_result == skip_result


def test_wake_tmux_send_uses_settle_delay_rescue_sequence_not_send_keys(monkeypatch):
    """GH #70: `tools.tmux_session.send_keys()` sends typed text then `C-m`
    back-to-back with zero settle delay, suspected of hitting the same
    bracketed-paste Enter-swallow `lib.iterm_type` already fixed for iTerm.
    `_wake_tmux_send` must NOT call `send_keys()` -- it builds its own
    type / delay 0.4 / Enter / delay 0.3 / Enter (rescue) sequence,
    mirroring `lib.iterm_type.type_submit_fragment`'s proven pattern."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    sleeps = []
    monkeypatch.setattr(sc.subprocess, "run", fake_run)
    monkeypatch.setattr(sc.time, "sleep", lambda s: sleeps.append(s))

    sc._wake_tmux_send("cfo-sess1234", ".")

    assert calls == [
        ["tmux", "send-keys", "-t", "cfo-sess1234", "-l", "."],
        ["tmux", "send-keys", "-t", "cfo-sess1234", "Enter"],
        ["tmux", "send-keys", "-t", "cfo-sess1234", "Enter"],
    ]
    assert sleeps == [0.4, 0.3]


def test_attempt_wake_public_with_private_alias_same_function():
    """task-18241f1d: the wake was promoted to public `attempt_wake` (the
    org's ONE implementation, imported by runners/relay_mcp_server.py).
    The old private name stays as an alias to the SAME function object, so
    every existing caller and every monkeypatch on either name observes
    the other too."""
    assert sc._attempt_wake is sc.attempt_wake


def test_secretary_is_explicit_ceo_proxy_in_authorize(isolated_locks):
    """task-18241f1d: the secretary (SomPong) is the CEO's Telegram-side
    proxy, not a C-level. authorize() must carry it as its own explicit
    entry -- allowed to reach any C-level primary session -- rather than
    letting it pass incidentally as a root peer."""
    sompong = sc.Identity("secretary", "secretary", "sompong")
    assert sc._owner_of(sompong) is None  # root-tier by definition
    sc.authorize(sompong, "cto", "ctosess1", spawning=False)  # no raise
    sc.authorize(sompong, "cfo", "cfosess9", spawning=False)  # any C-level


def test_secretary_entry_beats_a_forged_spawn_record(isolated_locks):
    """The allow must be the explicit secretary branch, not the root-peer
    fallback: plant a forged `secretary-sompong.spawned_by` claiming a
    C-level spawned the secretary. A kind=="cxo" identity with that record
    would be owned and refused cross-peer sends -- the secretary must
    still pass, proving it never walks the C-level ownership path at all
    (never dressed up as a C-level to satisfy the gate)."""
    (isolated_locks / "secretary-sompong.spawned_by").write_text("cxo:cto:ctoroot1")
    sompong = sc.Identity("secretary", "secretary", "sompong")
    sc.authorize(sompong, "cmo", "cmosess1", spawning=False)  # no raise

    # Contrast: the SAME record on a C-level-shaped identity does bind.
    disguised = sc.Identity("cxo", "secretary", "sompong")
    with pytest.raises(PermissionError):
        sc.authorize(disguised, "cmo", "cmosess1", spawning=False)


def test_secretary_to_non_c_level_target_is_refused(isolated_locks):
    """task-02d0e863 D2: the docstring promises the secretary 'may reach any
    C-level primary session' — the branch must enforce exactly that, not
    'anything'. Nothing exploits the gap today (the only secretary Identity
    constructor validates first), but authorize() is reachable from Telegram
    and a docstring/enforcement gap is the kind that gets discovered later
    by something going wrong. Refusal uses the same PermissionError the
    rest of authorize() raises."""
    sompong = sc.Identity("secretary", "secretary", "sompong")

    with pytest.raises(PermissionError, match="C-level"):
        sc.authorize(sompong, "dev", "task-abcdef12", spawning=False)

    with pytest.raises(PermissionError, match="C-level"):
        sc.authorize(sompong, "", None, spawning=False)  # no target at all

    # And the allowed side stays allowed: any C-level target passes.
    for role in ("cto", "cfo", "cmo", "cgo"):
        sc.authorize(sompong, role, f"{role}sess1", spawning=False)
