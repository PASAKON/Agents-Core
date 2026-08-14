"""Tests for the iTerm typewriter settle-delay submit fix.

A multi-line DEV report typed into the claude TUI used to stay stuck in the
composer ("[Pasted text #N +K lines]") because the submit CR was written
back-to-back with the body and got swallowed by the bracketed-paste path
(CEO report, recurring 2026-06-12). The fix adds a settle `delay` before the
CR plus a second rescue CR — see lib/iterm_type.type_submit_fragment.

Verifies:
  (a) the shared helper fragment carries both delays and two CRs, in order;
  (b) of the original 4 Python senders that used to type into a terminal
      (send_to_cto / send_to_dev / inject_prompt / send_to_cxo), only
      `inject_prompt` still does, and its generated AppleScript bakes the
      settle-delay+2CR sequence, using a genuinely multi-line message (the
      trigger condition). The other 3 were migrated off typing entirely by
      the mailbox+wake pattern: `send_to_cxo` first (task-de2cdc15, CEO
      2026-08-14 option A), then `send_to_cto` + `send_to_dev` together
      (task-2f04a8ca, CEO 2026-08-14, same-day org-wide extension —
      "ยกเลิกการส่งแบบที่ต้องใช้ Keyboard ถาวรได้เลย ... ทุกๆ ตำแหน่งในองกรณ์เลย").
      `test_send_to_cxo_sequence` / `test_send_to_cto_sequence` /
      `test_send_to_dev_sequence` below each prove the same shape for
      their sender: no osascript call, no leftover typing helper, a real
      letter in the mailbox instead. Full delivery-contract coverage
      (wake attempt/skip/fail isolation, GH #65 closure, etc.) lives in
      `scripts/test_send_to_cto.py` / `scripts/test_send_to_dev.py` — the
      three sequence tests here exist only to keep this file's own
      "did the typing get removed, not just moved" story honest;
  (c) the 2 shell sites (idle-ping-watcher.sh, cxo-claude.sh) inline the same
      delay / CR / delay / CR sequence.

subprocess.run is mocked everywhere — no real iTerm window is ever opened.
Every mailbox/DB write in the 3 non-typing sender tests below is redirected
to `tmp_path` (never `state/inbox/` or `state/tasks.db`), restored in a
`finally` block so this file's dual pytest/`python scripts/...` execution
mode (see `main()`) stays intact without a `monkeypatch` fixture.

Run via:   python scripts/test_iterm_typewriter.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest.mock as mock
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.iterm_type import type_submit_fragment  # noqa: E402

# A deliberately multi-line body — this is what trips the bracketed-paste
# path in the claude TUI, so every sender test exercises it.
MULTI = "line one\nline two\nline three"

# The ordered fingerprint of the fix: a body `write text ... newline NO`,
# then the settle delay, the first CR, the second settle, the rescue CR.
SEQUENCE = [
    "newline NO",
    "delay 0.4",
    "write text (ASCII character 13) newline NO",
    "delay 0.3",
    "write text (ASCII character 13) newline NO",
]


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _contains_in_order(haystack: str, needles: list[str]) -> bool:
    """True if every needle appears in haystack in the given order."""
    idx = 0
    for n in needles:
        found = haystack.find(n, idx)
        if found < 0:
            return False
        idx = found + len(n)
    return True


def _has_fix(script: str) -> bool:
    """A generated AppleScript carries the fix iff the ordered sequence is
    present and every settle block is well-formed: one `delay 0.4` paired with
    one `delay 0.3`, and exactly two CR writes per block. A script may embed
    the block more than once (send_to_dev has a primary + fallback path), so
    the counts are tied to each other rather than pinned to a literal 2."""
    cr = script.count("write text (ASCII character 13) newline NO")
    d4 = script.count("delay 0.4")
    d3 = script.count("delay 0.3")
    return (
        _contains_in_order(script, SEQUENCE)
        and d4 >= 1
        and d4 == d3
        and cr == 2 * d4
    )


# --- (a) helper -------------------------------------------------------------

def test_helper_fragment_shape() -> bool:
    frag = type_submit_fragment("BODY")
    return (
        'write text "BODY" newline NO' in frag
        and _contains_in_order(
            frag,
            ['write text "BODY" newline NO', "delay 0.4",
             "write text (ASCII character 13) newline NO", "delay 0.3",
             "write text (ASCII character 13) newline NO"],
        )
        and frag.count("write text (ASCII character 13) newline NO") == 2
        and frag.count("delay 0.4") == 1
        and frag.count("delay 0.3") == 1
    )


def test_helper_escapes_passthrough() -> bool:
    """The helper drops the caller-escaped body inside the quotes verbatim —
    it must not re-escape, exactly like the old inline `write text "{escaped}"`."""
    frag = type_submit_fragment('a\\"b')
    return 'write text "a\\"b" newline NO' in frag


# --- (b) Python senders -----------------------------------------------------

def _capture_osascript(fn) -> str | None:
    """Run `fn` with subprocess.run mocked; return the captured osascript -e
    script (cmd[2]) of the first osascript call, or None."""
    captured: list[str] = []

    def fake_run(cmd, **kwargs):
        if cmd and cmd[0] == "osascript":
            captured.append(cmd[2])
        r = mock.MagicMock()
        r.returncode = 0
        r.stdout = "1"
        return r

    with mock.patch("subprocess.run", side_effect=fake_run):
        fn()
    return captured[0] if captured else None


def test_send_to_cto_sequence(tmp_path: Path) -> bool:
    """Supersedes the old assertion (task-2f04a8ca, 2026-08-14): send_to_cto
    no longer types anything, so there is no AppleScript sequence to check
    here anymore -- full delivery-contract coverage moved to
    scripts/test_send_to_cto.py. Proves the same two things
    test_send_to_cxo_sequence already proved for its sender: send() writes
    the mailbox, not osascript; and the removed typing/window-lookup
    helper (`_read_winid`) is gone."""
    import lib.mailbox as mailbox
    import tools.send_to_cto as m

    if hasattr(m, "_read_winid") or hasattr(m, "_run_osascript"):
        return False  # the removed typing/winid-lookup helpers must not exist

    orig_state, orig_inbox = m.STATE_DIR, mailbox.INBOX_ROOT
    m.STATE_DIR = tmp_path
    mailbox.INBOX_ROOT = tmp_path / "inbox"
    try:
        script = _capture_osascript(
            lambda: m.send("task-x", MULTI, role="developer", cto_id="seq01")
        )
        letters = mailbox.peek("cto", "seq01", root=mailbox.INBOX_ROOT)
        return (
            script is None                # zero osascript calls
            and len(letters) == 1
            and letters[0]["body"] == MULTI
        )
    finally:
        m.STATE_DIR, mailbox.INBOX_ROOT = orig_state, orig_inbox


def test_send_to_dev_sequence(tmp_path: Path) -> bool:
    """Supersedes the old assertion (task-2f04a8ca, 2026-08-14): send_to_dev
    no longer types anything -- the `_send` helper this test used to import
    is deleted, not renamed. Full delivery-contract coverage (wake
    attempt/skip/fail isolation, GH #65 closure) moved to
    scripts/test_send_to_dev.py; this proves the same shape as the other
    two sequence tests above: no osascript call, no leftover typing
    helper, a real letter in the mailbox instead."""
    import lib.db as db_mod
    import lib.mailbox as mailbox
    import tools.send_to_dev as sd

    if hasattr(sd, "_send") or hasattr(sd, "_run_osascript"):
        return False  # the removed typing helper must not exist at all

    orig_db_path, orig_inbox = db_mod.DB_PATH, mailbox.INBOX_ROOT
    db_mod.DB_PATH = tmp_path / "tasks.db"
    mailbox.INBOX_ROOT = tmp_path / "inbox"
    db_mod.init()
    try:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db_mod.get_conn() as conn:
            conn.execute(
                """INSERT INTO tasks
                   (id, project, role, status, title, description,
                    depends_on, touches, tmux_session, owner_role, owner_cto,
                    created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("task-seqdev01", "test-proj", "developer", "in_progress",
                 "t", "d", "[]", "[]", None, None, None, ts, ts),
            )
            conn.commit()
        script = _capture_osascript(lambda: sd.send("task-seqdev01", MULTI))
        letters = mailbox.peek("developer", "task-seqdev01", root=mailbox.INBOX_ROOT)
        return (
            script is None
            and len(letters) == 1
            and letters[0]["body"] == MULTI
        )
    finally:
        db_mod.DB_PATH, mailbox.INBOX_ROOT = orig_db_path, orig_inbox


def test_send_to_cxo_sequence(tmp_path: Path) -> bool:
    """Supersedes the old assertion (task-de2cdc15, 2026-08-14): send_to_cxo
    no longer types anything, so there is no AppleScript sequence to check
    here anymore. Proves the opposite instead -- the exact two things CTO
    review round 1 asked for: send() writes the mailbox, not osascript; and
    the iTerm-typing helper this test used to import (`_send`) is gone."""
    import lib.mailbox as mailbox
    import tools.send_to_cxo as sc

    if hasattr(sc, "_send") or hasattr(sc, "_send_tmux") or hasattr(sc, "tmux"):
        return False  # the removed typing/tmux helpers must not exist at all

    locks = tmp_path / "locks"
    locks.mkdir()
    inbox = tmp_path / "inbox"
    sc.LOCKS_DIR = locks
    mailbox.INBOX_ROOT = inbox
    (locks / "cfo-active").write_text("sess1234")

    # current_identity() reads real process env (DEV_TASK_ID etc, set for
    # THIS harness's own DEV session) -- pin it to CEO-root so authorize()
    # takes its free-peer-messaging path without touching the real DB,
    # regardless of what env this file happens to run under.
    orig_identity = sc.current_identity
    sc.current_identity = lambda: sc.CEO_IDENTITY
    try:
        script = _capture_osascript(lambda: sc.send("cfo", MULTI, "CTO"))
    finally:
        sc.current_identity = orig_identity

    letters = mailbox.peek("cfo", "sess1234", root=inbox)
    return (
        script is None                # zero osascript calls, not even attempted
        and len(letters) == 1
        and letters[0]["body"] == MULTI
    )


def test_inject_prompt_sequence(tmp_path: Path) -> bool:
    from tools.inject_prompt import _send_pointer
    script = _capture_osascript(
        lambda: _send_pointer("task-abcd", tmp_path / "TASK.md")
    )
    return script is not None and _has_fix(script)


# --- (c) shell sites --------------------------------------------------------

def test_idle_ping_shell_sequence() -> bool:
    body = (ROOT / "scripts" / "idle-ping-watcher.sh").read_text()
    return _contains_in_order(body, SEQUENCE)


def test_cxo_claude_shell_sequence() -> bool:
    body = (ROOT / "scripts" / "cxo-claude.sh").read_text()
    return _contains_in_order(body, SEQUENCE)


def main() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)

        r = test_helper_fragment_shape(); fails += not r
        _mark(r, "helper fragment: body write + 2 delays + 2 CRs in order")
        r = test_helper_escapes_passthrough(); fails += not r
        _mark(r, "helper drops caller-escaped body inside quotes verbatim")

        r = test_send_to_cto_sequence(tmp); fails += not r
        _mark(r, "send_to_cto writes the mailbox, calls no osascript, has no typing helper left")
        r = test_send_to_dev_sequence(tmp); fails += not r
        _mark(r, "send_to_dev writes the mailbox, calls no osascript, has no typing helper left")
        r = test_send_to_cxo_sequence(tmp); fails += not r
        _mark(r, "send_to_cxo writes the mailbox, calls no osascript, has no typing helper left")
        r = test_inject_prompt_sequence(tmp); fails += not r
        _mark(r, "inject_prompt generated AppleScript carries the delay+2CR fix")

        r = test_idle_ping_shell_sequence(); fails += not r
        _mark(r, "idle-ping-watcher.sh inlines the delay+2CR sequence")
        r = test_cxo_claude_shell_sequence(); fails += not r
        _mark(r, "cxo-claude.sh inlines the delay+2CR sequence")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
