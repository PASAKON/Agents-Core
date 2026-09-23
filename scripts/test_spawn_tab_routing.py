"""Smoke tests for the iTerm tab routing patches.

Covers:
  1. delegate._build_spawn_applescript embeds the owner_cto exactly so
     DEV tabs route to the spawning CTO's window (not whatever window
     happens to own the first "CTO" tab).
  2. The same script reuses an existing tab when one with the task_id
     already exists, instead of always opening a new tab.
  3. scripts/spawn-cto.sh picks a fresh CTO id when the previously
     chosen id is held by a live lock, and refuses an explicit id that
     is already live.

Run via:   python scripts/test_spawn_tab_routing.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.delegate import (  # noqa: E402
    _build_spawn_applescript,
    _owner_window_id,
)


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def test_owner_cto_routing() -> bool:
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-deadbeef", owner_cto="ctoaaaaa")
    return (
        'contains "CTO Chat #ctoaaaaa"' in script
        and 'contains "(task-deadbeef)"' in script
        and 'return "reused"' in script
        and 'return "spawned"' in script
    )


def test_owner_winid_targets_by_id() -> bool:
    """When the CTO's .winid file is present, AppleScript must target
    the iTerm window by id — name matching is unreliable due to session
    title flicker."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-w", owner_cto="ctoabcd",
        owner_winid="2354")
    return (
        "first window whose id is (2354)" in script
        and 'targetWin is missing value' in script
    )


def test_owner_winid_absent_falls_back_to_name() -> bool:
    """With no winid file, the by-id branch must be dead-code (gated by
    `if "" is not ""`) so the name match is what actually runs."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-w", owner_cto="ctoabcd",
        owner_winid=None)
    return (
        'if "" is not "" then' in script
        and 'first window whose id is (0)' in script
        and 'CTO Chat #ctoabcd' in script
    )


def test_owner_window_id_reader(tmp_path_like: Path | None = None) -> bool:
    """The reader returns the digits when the lock file exists and is
    well-formed, None otherwise. Uses the real lock dir but a synthetic
    CTO id so it doesn't collide with anything live."""
    fake_id = "testwin1"
    p = ROOT / "state" / "locks" / f"cto-{fake_id}.winid"
    try:
        p.write_text("9999\n")
        ok_present = _owner_window_id(fake_id) == "9999"
        p.unlink()
        ok_missing = _owner_window_id(fake_id) is None
        p.write_text("not-a-number\n")
        ok_garbage = _owner_window_id(fake_id) is None
        return ok_present and ok_missing and ok_garbage
    finally:
        if p.exists():
            p.unlink()


def test_checks_both_title_surfaces() -> bool:
    """Each lookup must check `name of t` (sticky tab title) AND
    `name of current session of t` (session badge). Without this the
    AppleScript can miss the CTO window during a session-name flicker."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-z", owner_cto="ctowxyzab")
    return (
        script.count("set tabName to name of t") >= 3
        and script.count("set sessName to name of current session of t") >= 3
        and "tabName contains \"(task-z)\"" in script
        and "sessName contains \"(task-z)\"" in script
        and "tabName contains \"CTO Chat #ctowxyzab\"" in script
    )


def test_no_owner_falls_through() -> bool:
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-1", owner_cto=None)
    return (
        '"" is not ""' in script
        and 'contains "CTO Chat #"' in script
    )


def test_cfo_owner_routing() -> bool:
    """CFO-owned tasks must match 'CFO Chat #<id>' / 'CFO #<id>' tabs —
    NOT 'CTO ...' — so a CFO's DEV spawns cluster into the CFO's own
    window instead of falling through to whatever CTO window is open."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-cfo1", owner_cto="cfo01234",
        owner_role="cfo")
    return (
        'contains "CFO Chat #cfo01234"' in script
        and 'contains "CFO #cfo01234"' in script
        and 'contains "CTO Chat #cfo01234"' not in script
        and 'contains "CTO #cfo01234"' not in script
    )


def test_cmo_and_cgo_owner_routing() -> bool:
    """Same check for CMO and CGO — the fix is role-generic, not a
    CFO-only special case."""
    ok = True
    for role, display in (("cmo", "CMO"), ("cgo", "CGO")):
        script = _build_spawn_applescript(
            cmd="echo hi", task_id=f"task-{role}", owner_cto=f"{role}9999a",
            owner_role=role)
        ok = ok and (
            f'contains "{display} Chat #{role}9999a"' in script
            and f'contains "{display} #{role}9999a"' in script
            and 'contains "CTO' not in script
        )
    return ok


def test_owner_window_id_role_aware() -> bool:
    """Same session id, different owner_role, must resolve to different
    lock files — proves the role prefix (not just the id) selects the
    window, so a CFO and a CTO never accidentally share one winid file."""
    shared_id = "shareid1"
    cto_p = ROOT / "state" / "locks" / f"cto-{shared_id}.winid"
    cfo_p = ROOT / "state" / "locks" / f"cfo-{shared_id}.winid"
    try:
        cto_p.write_text("1111\n")
        cfo_p.write_text("2222\n")
        ok = (
            _owner_window_id(shared_id, "cto") == "1111"
            and _owner_window_id(shared_id, "cfo") == "2222"
            and _owner_window_id(shared_id) == "1111"  # no role → legacy "cto" default
        )
        return ok
    finally:
        cto_p.unlink(missing_ok=True)
        cfo_p.unlink(missing_ok=True)


def test_multi_cto_concurrent_ids_isolated() -> bool:
    """Two CTO sessions open at once must never cross-match: each id's
    winid lookup and AppleScript owner_match stays scoped to its own
    session id, even though both share the 'cto' role prefix."""
    id_a, id_b = "ctoAAAA1", "ctoBBBB2"
    p_a = ROOT / "state" / "locks" / f"cto-{id_a}.winid"
    p_b = ROOT / "state" / "locks" / f"cto-{id_b}.winid"
    try:
        p_a.write_text("3001\n")
        p_b.write_text("3002\n")
        win_a = _owner_window_id(id_a, "cto")
        win_b = _owner_window_id(id_b, "cto")
        script_a = _build_spawn_applescript(
            cmd="echo a", task_id="task-multi-a", owner_cto=id_a,
            owner_role="cto", owner_winid=win_a)
        script_b = _build_spawn_applescript(
            cmd="echo b", task_id="task-multi-b", owner_cto=id_b,
            owner_role="cto", owner_winid=win_b)
        return (
            win_a == "3001" and win_b == "3002"
            and "first window whose id is (3001)" in script_a
            and "first window whose id is (3002)" in script_b
            and f"CTO #{id_a}" in script_a and id_b not in script_a
            and f"CTO #{id_b}" in script_b and id_a not in script_b
        )
    finally:
        p_a.unlink(missing_ok=True)
        p_b.unlink(missing_ok=True)


def test_delegate_task_threads_owner_role() -> bool:
    """delegate_task must read task.owner_role from the DB and pass it
    through to _spawn_iterm_tab / _verify_claimed — the actual wiring
    that was missing before this fix (owner_cto alone isn't enough to
    pick the right window; the role prefix is required too)."""
    import inspect
    from tools import delegate as _d

    src = inspect.getsource(_d.delegate_task)
    return (
        'task.get("owner_role")' in src
        and "owner_role=owner_role" in src
        and "_verify_claimed(task_id, role_name, owner_cto, owner_role" in src
    )


def test_resume_dev_owner_routing() -> bool:
    """tools.resume_worker must route resumed tabs to the owning C-level's
    window too — same bug class as delegate.py, same fix shape."""
    import unittest.mock as mock
    from tools.resume_worker import _spawn_resume_tab

    captured: list[str] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd[-1] if isinstance(cmd, list) else str(cmd))
        class R:
            returncode = 0
        return R()

    with mock.patch("tools.resume_worker.subprocess.run", side_effect=fake_run):
        _spawn_resume_tab("developer", "task-resume1",
                          owner_cto="cfo55555", owner_role="cfo")

    script = captured[-1] if captured else ""
    return (
        'contains "CFO Chat #"' in script
        and 'contains "CFO #"' in script
        and 'contains "CTO Chat #"' not in script
    )


def test_reuse_check_comes_first() -> bool:
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-xyz", owner_cto="ctobbbbb")
    reuse_idx = script.find('(task-xyz)')
    owner_idx = script.find('CTO Chat #ctobbbbb')
    return 0 <= reuse_idx < owner_idx


def _stage_fake_root(tmp: Path) -> Path:
    fake_root = tmp / "fake-root"
    fake_root.mkdir()
    (fake_root / ".venv").mkdir()
    (fake_root / "state").symlink_to(tmp / "state")
    scripts_dir = fake_root / "scripts"
    scripts_dir.mkdir()
    for stub in ("cto-claude.sh", "tail-dev-logs.sh"):
        (scripts_dir / stub).write_text("#!/usr/bin/env bash\nexit 0\n")
        (scripts_dir / stub).chmod(0o755)
    src = (ROOT / "scripts" / "spawn-cto.sh").read_text()
    patched = src.replace(
        'ROOT="/Users/gob/MoonieXHQ/Agents/Core"',
        f'ROOT="{fake_root}"',
    )
    patched_path = scripts_dir / "spawn-cto.patched.sh"
    patched_path.write_text(patched)
    patched_path.chmod(0o755)
    return patched_path


def _stage_osascript_shim(tmp: Path) -> Path:
    shim = tmp / "bin"
    shim.mkdir()
    (shim / "osascript").write_text("#!/usr/bin/env bash\nexit 0\n")
    (shim / "osascript").chmod(0o755)
    return shim


def test_spawn_cto_collision() -> bool:
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        locks = tmp / "state" / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        live_id = "livecto1"
        (locks / f"cto-{live_id}.lock").write_text(f"{os.getpid()}\n")

        patched_path = _stage_fake_root(tmp)
        shim = _stage_osascript_shim(tmp)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env.pop("CTO_SESSION_ID", None)

        proc = subprocess.run(
            ["bash", str(patched_path), "--id", live_id],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return (
            proc.returncode != 0
            and "already running" in (proc.stderr or "")
            and live_id in (proc.stderr or "")
        )


def test_spawn_cto_drops_inherited_env() -> bool:
    """spawn-cto.sh must NOT honor an inherited CTO_SESSION_ID. Running
    it from inside an existing CTO chat would otherwise clone that
    chat's id into the new tab — the real-world bug that motivated this
    patch."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        (tmp / "state" / "locks").mkdir(parents=True, exist_ok=True)
        patched_path = _stage_fake_root(tmp)
        shim = _stage_osascript_shim(tmp)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env["CTO_SESSION_ID"] = "parentcc"

        proc = subprocess.run(
            ["bash", str(patched_path)],
            env=env, capture_output=True, text=True, timeout=15,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "parentcc" not in out


def test_spawn_cto_reaps_stale_lock() -> bool:
    """Stale lock (pid no longer alive) should be reaped so the spawn
    succeeds when the explicit id is reused."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        locks = tmp / "state" / "locks"
        locks.mkdir(parents=True, exist_ok=True)

        dead_pid = 999999
        while dead_pid < 2_000_000:
            try:
                os.kill(dead_pid, 0)
                dead_pid += 1
            except (ProcessLookupError, OSError):
                break
        else:
            print("    (skipping stale-lock test: no dead PID found)")
            return True

        stale_id = "stalecto"
        (locks / f"cto-{stale_id}.lock").write_text(f"{dead_pid}\n")

        patched_path = _stage_fake_root(tmp)
        shim = _stage_osascript_shim(tmp)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env.pop("CTO_SESSION_ID", None)

        proc = subprocess.run(
            ["bash", str(patched_path), "--id", stale_id],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return proc.returncode == 0


def test_close_session_refuses_missing_lock() -> bool:
    """close_session returns False + writes refusal log when lock file absent."""
    from tools.itermtab import close_session, _LOCKS

    refusals_log = _LOCKS / "close-refusals.log"
    before = refusals_log.read_text() if refusals_log.exists() else ""

    result = close_session("fakecxo", "fakesession_unit_test")

    after = refusals_log.read_text() if refusals_log.exists() else ""
    new_lines = [l for l in (after[len(before):]).splitlines() if l.strip()]
    if not new_lines:
        return False
    try:
        entry = json.loads(new_lines[-1])
        return (
            result is False
            and entry.get("role") == "fakecxo"
            and entry.get("session_id") == "fakesession_unit_test"
            and "lock file missing" in entry.get("reason", "")
        )
    except (json.JSONDecodeError, KeyError):
        return False


def test_send_to_cxo_legacy_path_has_no_typing_helper() -> bool:
    """Pre-existing dead test replaced (task-093a3939): the old
    `_send`/tab_match/AppleScript-typing legacy path this used to check was
    already removed by task-de2cdc15 (CEO 2026-08-14, mailbox+wake) --
    `_send` hasn't existed since, so the old assertion here has been
    silently import-erroring (this file is pytest.ini-ignored, so nothing
    caught it). `send()` is the current legacy (no --spawn) path; its
    mailbox-not-AppleScript contract is already covered in depth by
    scripts/test_cxo_crosstalk.py. This just proves the dead name stays
    dead."""
    from tools import send_to_cxo as sc
    return not hasattr(sc, "_send")


def test_send_to_cxo_spawn_flag_on_calls_cxo_claude() -> bool:
    """--spawn path must start a REAL tmux-backed cxo-claude.sh session
    (mirrors scripts/spawn-cxo.sh's `tmux new-session -A` shape, task-093a3939)
    with --session and the initial message passed through as --initial-prompt
    -- embedded in the temp RUN_FILE, never typed via AppleScript."""
    import unittest.mock as mock
    from tools.send_to_cxo import _spawn_new_ephemeral

    written_scripts: list[str] = []
    as_calls: list = []

    class FakeFile:
        def __init__(self):
            self.name = "/tmp/fake_test.sh"
        def write(self, s):
            written_scripts.append(s)
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_nm(**kwargs):
        return FakeFile()

    def fake_run(cmd, **kwargs):
        as_calls.append(cmd)
        class R:
            returncode = 0
        return R()

    with mock.patch("tools.send_to_cxo.tempfile.NamedTemporaryFile", fake_nm), \
         mock.patch("tools.send_to_cxo.subprocess.run", side_effect=fake_run), \
         mock.patch("tools.send_to_cxo.os.chmod"), \
         mock.patch("tools.send_to_cxo.os.unlink"):
        _spawn_new_ephemeral(
            role="cfo",
            session_id="req-deadbeef",
            tab_title="CFO <- CTO: budget-review",
            initial_text="[CTO]: please review budget",
        )

    script_body = " ".join(written_scripts)
    osascript_body = " ".join(str(c) for c in as_calls)
    return (
        "cxo-claude.sh" in script_body
        and "--session" in script_body
        and "req-deadbeef" in script_body
        and "--initial-prompt" in script_body
        and "please review budget" in script_body
        and "type_submit_fragment" not in script_body
        and "tmux" in osascript_body
        and "new-session" in osascript_body
        and "cfo-req-deadbeef" in osascript_body
    )


def test_send_to_cxo_dedupe_reuses_recent_topic_match() -> bool:
    """spawn() with an alive lock + matching topic + recent mtime reuses the
    existing tab via mailbox+wake (task-093a3939) -- not typing -- and does
    NOT open a new one."""
    import unittest.mock as mock
    from tools.send_to_cxo import spawn, _make_topic_slug

    with tempfile.TemporaryDirectory() as tmp_s:
        locks = Path(tmp_s) / "locks"
        locks.mkdir()

        slug = _make_topic_slug("budget review needed")
        winid = "9001"
        lock_file = locks / "cfo-req-aabbccdd.winid"
        lock_file.write_text(winid + "\n")
        (locks / "cfo-req-aabbccdd.topic").write_text(slug)

        mailbox_calls: list = []
        wake_calls: list = []
        spawn_calls: list = []

        def fake_mailbox_send(to_role, to_sid, body, from_role, from_sid, **kwargs):
            mailbox_calls.append((to_role, to_sid, body))

        def fake_attempt_wake(role, sid, label):
            wake_calls.append((role, sid, label))

        def fake_spawn_new(role, session_id, tab_title, initial_text):
            spawn_calls.append((role, session_id))

        def fake_get_live():
            return {winid}

        with mock.patch("tools.send_to_cxo.LOCKS_DIR", locks), \
             mock.patch("tools.send_to_cxo.is_c_level", return_value=True), \
             mock.patch("tools.send_to_cxo.display_for", return_value="CFO"), \
             mock.patch("tools.send_to_cxo._get_live_winids", fake_get_live), \
             mock.patch("tools.send_to_cxo.mailbox.send", side_effect=fake_mailbox_send), \
             mock.patch("tools.send_to_cxo._attempt_wake", side_effect=fake_attempt_wake), \
             mock.patch("tools.send_to_cxo._spawn_new_ephemeral", fake_spawn_new):
            result = spawn("cfo", "budget review needed", sender="CTO")

    return (
        len(mailbox_calls) == 1
        and mailbox_calls[0][0] == "cfo"
        and mailbox_calls[0][1] == "req-aabbccdd"
        and mailbox_calls[0][2] == "budget review needed"
        and len(wake_calls) == 1
        and wake_calls[0][0] == "cfo"
        and wake_calls[0][1] == "req-aabbccdd"
        and len(spawn_calls) == 0
        and "reused" in result
    )


def test_send_to_cxo_dedupe_skips_stale_lock() -> bool:
    """spawn() with a lock whose winid is not in the live window list ignores
    the stale lock and opens a new (real tmux-backed) tab -- never falls back
    to a mailbox reuse for a tab that isn't actually alive."""
    import unittest.mock as mock
    from tools.send_to_cxo import spawn, _make_topic_slug

    with tempfile.TemporaryDirectory() as tmp_s:
        locks = Path(tmp_s) / "locks"
        locks.mkdir()

        slug = _make_topic_slug("stale test message")
        lock_file = locks / "cfo-req-deaddddd.winid"
        lock_file.write_text("9999\n")
        (locks / "cfo-req-deaddddd.topic").write_text(slug)

        spawn_calls: list = []

        def fake_get_live():
            return {"1111"}  # 9999 not present → stale

        def fake_spawn_new(role, session_id, tab_title, initial_text):
            spawn_calls.append((role, session_id))

        def fake_mailbox_send(*a, **kw):
            raise AssertionError("should not reuse stale tab")

        with mock.patch("tools.send_to_cxo.LOCKS_DIR", locks), \
             mock.patch("tools.send_to_cxo.is_c_level", return_value=True), \
             mock.patch("tools.send_to_cxo.display_for", return_value="CFO"), \
             mock.patch("tools.send_to_cxo._get_live_winids", fake_get_live), \
             mock.patch("tools.send_to_cxo.mailbox.send", side_effect=fake_mailbox_send), \
             mock.patch("tools.send_to_cxo._spawn_new_ephemeral", fake_spawn_new):
            result = spawn("cfo", "stale test message", sender="CTO")

    return (
        len(spawn_calls) == 1
        and spawn_calls[0][0] == "cfo"
        and "spawned" in result
    )


def test_cxo_claude_passes_initial_prompt_as_positional_arg() -> bool:
    """cxo-claude.sh with --initial-prompt must pass the prompt straight
    through to `claude` as the final positional argv (auto-submitted on
    start, task-093a3939) -- never typed via a backgrounded osascript call."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        (tmp / "state" / "locks").mkdir(parents=True, exist_ok=True)
        (tmp / "roles").mkdir()
        (tmp / "roles" / "cfo.md").write_text("You are CFO.")
        (tmp / "config").mkdir()
        (tmp / "config" / "cto.mcp.json").write_text("{}")
        venv_bin = tmp / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "activate").write_text("# fake activate\n")

        shim = tmp / "bin"
        shim.mkdir()
        osascript_log = tmp / "osascript.log"
        claude_log = tmp / "claude_argv.log"

        # osascript shim: append all args to log (still called for the
        # winid lookup / HIDETAB pref, never for prompt text now)
        osascript_shim = shim / "osascript"
        osascript_shim.write_text(
            f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "{osascript_log}"\nexit 0\n'
        )
        osascript_shim.chmod(0o755)

        # claude shim: record its argv (one per line), exit immediately.
        (shim / "claude").write_text(
            f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "{claude_log}"\nexit 0\n'
        )
        (shim / "claude").chmod(0o755)

        # python3 shim: return "CFO" for display_for lookup
        (shim / "python3").write_text("#!/usr/bin/env bash\necho CFO\n")
        (shim / "python3").chmod(0o755)

        src = (ROOT / "scripts" / "cxo-claude.sh").read_text()
        patched = src.replace(
            'ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"',
            f'ROOT="{tmp}"',
        )
        cxo_sh = tmp / "cxo-claude.patched.sh"
        cxo_sh.write_text(patched)
        cxo_sh.chmod(0o755)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env.pop("CXO_SESSION_ID", None)

        proc = subprocess.run(
            [
                "bash", str(cxo_sh),
                "--role", "cfo",
                "--session", "req-testtest",
                "--tab-title", "CFO <- CTO: test-prompt",
                "--initial-prompt", "[CTO]: hello world from test",
            ],
            env=env, capture_output=True, text=True, timeout=15,
        )

        claude_argv = claude_log.read_text() if claude_log.exists() else ""
        osascript_content = osascript_log.read_text() if osascript_log.exists() else ""
        argv_lines = [l for l in claude_argv.splitlines() if l.strip()]
        last_arg = argv_lines[-1] if argv_lines else ""
        return (
            proc.returncode == 0
            and last_arg == "[CTO]: hello world from test"
            and "hello world from test" not in osascript_content
        )


def test_cleanup_zombies_removes_sibling_files() -> bool:
    """Stale .winid + siblings (.topic/.lock/.watcher-pid) all removed."""
    with tempfile.TemporaryDirectory() as tmp_s:
        locks = Path(tmp_s) / "state" / "locks"
        locks.mkdir(parents=True)

        base = "cfo-req-stale1"
        (locks / f"{base}.winid").write_text("9999\n")
        (locks / f"{base}.topic").write_text("test-slug\n")
        (locks / f"{base}.lock").write_text("12345\n")
        (locks / f"{base}.watcher-pid").write_text("99999\n")  # dead pid

        shim = Path(tmp_s) / "bin"
        shim.mkdir()
        (shim / "osascript").write_text("#!/usr/bin/env bash\necho ''\n")
        (shim / "osascript").chmod(0o755)

        src = (ROOT / "scripts" / "cleanup-zombies.sh").read_text()
        patched = src.replace(
            'ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"',
            f'ROOT="{Path(tmp_s)}"',
        )
        sh = Path(tmp_s) / "cleanup-zombies.patched.sh"
        sh.write_text(patched)
        sh.chmod(0o755)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        r = subprocess.run(["bash", str(sh)], env=env, capture_output=True, text=True, timeout=10)

        removed = not (locks / f"{base}.winid").exists()
        no_topic = not (locks / f"{base}.topic").exists()
        no_lock_f = not (locks / f"{base}.lock").exists()
        no_pid = not (locks / f"{base}.watcher-pid").exists()
        return removed and no_topic and no_lock_f and no_pid and "1 stale lock set" in r.stdout


def test_cleanup_zombies_does_not_touch_live() -> bool:
    """Live winid + siblings left untouched."""
    with tempfile.TemporaryDirectory() as tmp_s:
        locks = Path(tmp_s) / "state" / "locks"
        locks.mkdir(parents=True)

        base = "cfo-req-live1"
        (locks / f"{base}.winid").write_text("8888\n")
        (locks / f"{base}.topic").write_text("live-slug\n")

        shim = Path(tmp_s) / "bin"
        shim.mkdir()
        (shim / "osascript").write_text("#!/usr/bin/env bash\necho '8888'\n")
        (shim / "osascript").chmod(0o755)

        src = (ROOT / "scripts" / "cleanup-zombies.sh").read_text()
        patched = src.replace(
            'ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"',
            f'ROOT="{Path(tmp_s)}"',
        )
        sh = Path(tmp_s) / "cleanup-zombies-live.patched.sh"
        sh.write_text(patched)
        sh.chmod(0o755)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        r = subprocess.run(["bash", str(sh)], env=env, capture_output=True, text=True, timeout=10)

        still_winid = (locks / f"{base}.winid").exists()
        still_topic = (locks / f"{base}.topic").exists()
        return still_winid and still_topic and "0 stale lock set" in r.stdout


def test_close_session_refuses_when_session_busy() -> bool:
    """close_session gate 4 refuses when c_level_sessions has active in-progress task."""
    import unittest.mock as mock
    from tools.itermtab import close_session, _LOCKS
    import lib.db as _db

    with tempfile.TemporaryDirectory() as tmp_s:
        orig_path = _db.DB_PATH
        _db.DB_PATH = Path(tmp_s) / "tasks.db"
        lock_file = _LOCKS / "cfo-sess-busy.winid"
        try:
            _db.init()
            with _db.get_conn() as conn:
                conn.execute(
                    "INSERT INTO tasks "
                    "(id,project,role,status,title,description,depends_on,touches,created_at,updated_at) "
                    "VALUES ('task-busytest','proj','cfo','in_progress','t','d','[]','[]','2026-01-01','2026-01-01')"
                )
                conn.execute(
                    "INSERT INTO c_level_sessions (role,session_id,active_task_id,spawned_at) "
                    "VALUES ('cfo','sess-busy','task-busytest','2026-01-01')"
                )
            lock_file.write_text("99998\n")

            with mock.patch("tools.itermtab.subprocess.run") as fake_run:
                fake_run.return_value = type("R", (), {
                    "returncode": 0, "stdout": "99998\n", "stderr": "",
                })()
                with mock.patch.dict(os.environ, {"CXO_ROLE": "cfo", "CXO_SESSION_ID": "sess-busy"}):
                    result = close_session("cfo", "sess-busy")
        finally:
            _db.DB_PATH = orig_path
            lock_file.unlink(missing_ok=True)

    return result is False


def test_register_cxo_session_idempotent() -> bool:
    """Calling register_cxo_session twice with same (role, sid) yields exactly one row."""
    import lib.db as _db
    with tempfile.TemporaryDirectory() as tmp_s:
        orig_path = _db.DB_PATH
        _db.DB_PATH = Path(tmp_s) / "tasks.db"
        try:
            _db.init()
            _db.register_cxo_session("cmo", "sess-idm1")
            _db.register_cxo_session("cmo", "sess-idm1")
            with _db.get_conn() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM c_level_sessions "
                    "WHERE role='cmo' AND session_id='sess-idm1'"
                ).fetchone()[0]
        finally:
            _db.DB_PATH = orig_path
    return count == 1


def test_bind_session_to_task_clears_with_null() -> bool:
    """bind_session_to_task sets active_task_id then clears it with None."""
    import lib.db as _db
    with tempfile.TemporaryDirectory() as tmp_s:
        orig_path = _db.DB_PATH
        _db.DB_PATH = Path(tmp_s) / "tasks.db"
        try:
            _db.init()
            _db.register_cxo_session("cgo", "sess-bind1")
            _db.bind_session_to_task("cgo", "sess-bind1", "task-abc123")
            with _db.get_conn() as conn:
                row = conn.execute(
                    "SELECT active_task_id FROM c_level_sessions "
                    "WHERE role='cgo' AND session_id='sess-bind1'"
                ).fetchone()
            bound = row[0] == "task-abc123"
            _db.bind_session_to_task("cgo", "sess-bind1", None)
            with _db.get_conn() as conn:
                row2 = conn.execute(
                    "SELECT active_task_id FROM c_level_sessions "
                    "WHERE role='cgo' AND session_id='sess-bind1'"
                ).fetchone()
            cleared = row2[0] is None
        finally:
            _db.DB_PATH = orig_path
    return bound and cleared


def test_idle_ping_watcher_cli_entry() -> bool:
    """tools/itermtab_close CLI exits 1 when lock file absent (gate 1 fails → False → exit 1)."""
    r = subprocess.run(
        [sys.executable, "-m", "tools.itermtab_close",
         "--role", "cfo", "--session", "no-such-sess-unit"],
        capture_output=True, text=True, timeout=10, cwd=str(ROOT),
    )
    return r.returncode == 1


def main() -> int:
    fails = 0
    r = test_owner_cto_routing(); fails += not r
    _mark(r, "owner_cto literal embedded in AppleScript")
    r = test_owner_winid_targets_by_id(); fails += not r
    _mark(r, "winid present -> AppleScript targets window by id")
    r = test_owner_winid_absent_falls_back_to_name(); fails += not r
    _mark(r, "winid absent -> AppleScript falls back to name match")
    r = test_owner_window_id_reader(); fails += not r
    _mark(r, "_owner_window_id reads digit content + rejects garbage")
    r = test_checks_both_title_surfaces(); fails += not r
    _mark(r, "AppleScript still checks tab name and session name")
    r = test_no_owner_falls_through(); fails += not r
    _mark(r, "absent owner_cto disables exact match branch")
    r = test_cfo_owner_routing(); fails += not r
    _mark(r, "CFO-owned task matches 'CFO ...' tabs, not 'CTO ...'")
    r = test_cmo_and_cgo_owner_routing(); fails += not r
    _mark(r, "CMO/CGO-owned tasks match their own display, not 'CTO'")
    r = test_owner_window_id_role_aware(); fails += not r
    _mark(r, "same session id + different owner_role -> different winid file")
    r = test_multi_cto_concurrent_ids_isolated(); fails += not r
    _mark(r, "two concurrent CTO sessions never cross-match each other's window")
    r = test_delegate_task_threads_owner_role(); fails += not r
    _mark(r, "delegate_task reads owner_role from DB and threads it through")
    r = test_resume_dev_owner_routing(); fails += not r
    _mark(r, "resume_worker routes resumed tab to owning C-level's window")
    r = test_reuse_check_comes_first(); fails += not r
    _mark(r, "tab-reuse check precedes owner-window lookup")
    r = test_spawn_cto_collision(); fails += not r
    _mark(r, "spawn-cto.sh rejects live duplicate via --id")
    r = test_spawn_cto_drops_inherited_env(); fails += not r
    _mark(r, "spawn-cto.sh ignores inherited CTO_SESSION_ID")
    r = test_spawn_cto_reaps_stale_lock(); fails += not r
    _mark(r, "spawn-cto.sh reaps stale lock and reuses id via --id")
    r = test_close_session_refuses_missing_lock(); fails += not r
    _mark(r, "close_session refuses when lock file missing + writes refusal log")
    r = test_send_to_cxo_legacy_path_has_no_typing_helper(); fails += not r
    _mark(r, "legacy _send typing helper stays gone (dead test replaced)")
    r = test_send_to_cxo_spawn_flag_on_calls_cxo_claude(); fails += not r
    _mark(r, "--spawn writes temp script with cxo-claude.sh + --session + prompt")
    r = test_send_to_cxo_dedupe_reuses_recent_topic_match(); fails += not r
    _mark(r, "dedupe: alive lock + matching topic → reuse, no new spawn")
    r = test_send_to_cxo_dedupe_skips_stale_lock(); fails += not r
    _mark(r, "dedupe: stale winid → skipped, new tab spawned")
    r = test_cxo_claude_passes_initial_prompt_as_positional_arg(); fails += not r
    _mark(r, "cxo-claude.sh --initial-prompt passed to claude as positional argv, never typed")
    r = test_cleanup_zombies_removes_sibling_files(); fails += not r
    _mark(r, "cleanup-zombies removes all 4 sibling files for stale lock set")
    r = test_cleanup_zombies_does_not_touch_live(); fails += not r
    _mark(r, "cleanup-zombies leaves live lock set untouched")
    r = test_close_session_refuses_when_session_busy(); fails += not r
    _mark(r, "close_session gate 4: refuses when c_level_sessions has in-progress task")
    r = test_register_cxo_session_idempotent(); fails += not r
    _mark(r, "register_cxo_session is idempotent (no duplicate rows)")
    r = test_bind_session_to_task_clears_with_null(); fails += not r
    _mark(r, "bind_session_to_task sets and clears active_task_id")
    r = test_idle_ping_watcher_cli_entry(); fails += not r
    _mark(r, "itermtab_close CLI exits 1 when lock file absent (gate 1)")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
