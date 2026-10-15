"""Direction-agnostic transport primitives shared by tools/send_to_worker.py,
tools/send_to_cto.py, and tools/send_to_cxo.py.

Task task-eb0d9863 (CEO asked why the 3 send_to_*.py files aren't one file).
Real answer: they already shared code, but wrongly -- send_to_worker.py and
send_to_cto.py both imported underscore-prefixed private names
(`current_identity`, `_resolve_sender_role`, `_active_session_id`,
`_wake_tmux_send`, `_WAKE_MARKER_TEMPLATE`) straight out of send_to_cxo.py,
which only became "the shared library" by being written first -- its own
module docstring/purpose (C-level peer-to-peer send + `--spawn`
ephemeral-tab cold-start) has nothing to do with being a dependency of the
other two. A full merge into one file/one CLI was explicitly out of scope
(19 files reference the 3 modules by name; renaming call sites for a
cosmetic win isn't worth the risk). This module holds only the genuinely
shared, direction-agnostic pieces; each send_to_*.py file keeps its own
logic for RESOLVING which session name/id to act on -- see each file's own
`attempt_wake`/`_attempt_wake` wrapper.

No external caller's import path changes: `tools.send_to_worker` /
`tools.send_to_cto` / `tools.send_to_cxo` still expose every name they did
before this task, either by defining it locally (unchanged) or re-exporting
it from here.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from lib import notify
from lib.config import display_for, is_c_level
from lib.pane_screen import _squash, box_empty, pane_waiting, typed_text
from tools import session_name, tmux_session

ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = ROOT / "state" / "locks"


def _active_session_id(role: str, locks_dir: Path | None = None) -> str | None:
    """Return the most-recent C-level session id for `role`, or None.

    Looks first at the `<role>-active` pointer that cxo-claude.sh writes
    on boot. Falls back to the newest matching `.winid` file so we still
    work for sessions started before this helper existed.

    `locks_dir` defaults to this module's own `LOCKS_DIR`. `send_to_cxo.py`
    passes its own `LOCKS_DIR` explicitly instead (its own thin wrapper of
    this function) so tests that isolate `tools.send_to_cxo.LOCKS_DIR`
    (several do -- e.g. `runners/mac_agent.py`'s relay tests) keep working
    unchanged: a bare-name global lookup only sees a monkeypatch on the
    module it's actually looked up in.
    """
    base = locks_dir if locks_dir is not None else LOCKS_DIR
    pointer = base / f"{role}-active"
    if pointer.exists():
        sid = pointer.read_text().strip()
        if sid:
            return sid
    candidates = sorted(
        base.glob(f"{role}-*.winid"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in candidates:
        sid = p.stem.split("-", 1)[1]
        if sid != "active":
            return sid
    return None


# A Project Head (org restructure P2) is neither a C-level nor the CEO. Its
# launcher unsets CTO_SESSION_ID, so without these branches it fell through to
# "CEO" here and to CEO_IDENTITY in current_identity(): its letters went out as
# the CEO's and passed authorize() as root.
PH_ROLE = "project_head"  # lib/roles.PH_ROLE


def _is_ph_env() -> bool:
    return (os.environ.get("CXO_ROLE") or "").strip().lower() == PH_ROLE


# The CEO is never the default. A process whose env named no session used to
# resolve to CEO_IDENTITY here and to "CEO" in _resolve_sender_role(), so a cron
# job, a hook or any bare shell sent as the CEO and passed authorize() as root
# (docs/design/org-restructure-p2.md, "Next security item"). Such a process is
# refused now. The CEO's own command names itself with CEO_MARKER=1, written into
# the command line he approves on a Run Inbox card. The mark counts only in an
# env that holds none of _SESSION_ENV_KEYS, whatever their value: every key a
# launcher gives a C-level, a Project Head or a worker, plus CLAUDECODE, which
# Claude Code sets in every command it runs. So no session, and nothing a session
# starts, carries it by accident.
CEO_MARKER = "ORG_AS_CEO"
_SESSION_ENV_KEYS = (
    "CXO_ROLE", "CXO_SESSION_ID", "CXO_SESSION", "CTO_SESSION_ID", "CTO_SESSION",
    "ORG_SESSION_ID", "ORG_PH_LANE", "ORG_PH_PROJECT", "ORG_PH_OWNER",
    "WORKER_TASK_ID", "WORKER_ROLE", "WORKER_CTO_ID", "WORKER_CTO_ROLE",
    "CLAUDECODE",
)


def _is_ceo_env(env=None) -> bool:
    """True only for the CEO's own marked command (see CEO_MARKER above)."""
    env = os.environ if env is None else env
    if (env.get(CEO_MARKER) or "").strip() != "1":
        return False
    return not any(k in env for k in _SESSION_ENV_KEYS)


def _no_identity() -> PermissionError:
    r = (os.environ.get("CXO_ROLE") or "").strip()
    if r and is_c_level(r):
        return PermissionError(
            f"refused: CXO_ROLE={r} but this process has no CXO_SESSION_ID or "
            f"CTO_SESSION_ID, so it has no identity and cannot send")
    return PermissionError(
        "refused: this process has no org identity (no CXO_ROLE with a session id, "
        "no WORKER_TASK_ID, no CTO_SESSION_ID), so it cannot send. A session gets "
        "these from its launcher; a bare process is not the CEO "
        "(tools/agent_transport.py, CEO_MARKER)")


def _resolve_sender_role() -> str:
    """Sender label. "CEO" only for the CEO's marked command (_is_ceo_env);
    a process with no identity is refused, as in current_identity()."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        return display_for(r)
    if _is_ph_env():
        lane = (os.environ.get("ORG_PH_LANE") or "").strip().upper()
        sid = (os.environ.get("CXO_SESSION_ID") or "").strip()
        return f"Project Head ({lane or '?'}) #{sid or '?'}"
    if os.environ.get("CTO_SESSION_ID"):
        return display_for("cto")
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:  # a worker's letter used to read "CEO" too
        return Identity("dev", os.environ.get("WORKER_ROLE", "dev"), task_id).label()
    if _is_ceo_env():
        return "CEO"
    raise _no_identity()


@dataclass(frozen=True)
class Identity:
    """A node in the ownership graph: a C-level session or a DEV task."""

    kind: str  # "cxo" | "dev" | "ceo" | "secretary"
    role: str  # cto/cmo/cgo/cfo/coo for "cxo"; the DEV role key for "dev"
    session_id: str | None  # session id ("cxo") or task_id ("dev"); None for "ceo"

    def label(self) -> str:
        if self.kind == "ceo":
            return "CEO"
        if self.kind == "cxo" and self.role == PH_ROLE:
            disp = "Project Head"
        else:
            disp = display_for(self.role) if self.kind == "cxo" else self.role
        return f"{disp}#{self.session_id}" if self.session_id else disp


CEO_IDENTITY = Identity("ceo", "CEO", None)


def current_identity() -> Identity:
    """Who is calling send_to_cxo/send_to_worker/send_to_cto right now,
    resolved from process env -- never from anything the caller passes in.
    Raises PermissionError for a process with no identity: CEO_IDENTITY only
    for the CEO's marked command (_is_ceo_env)."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        if sid:
            return Identity("cxo", r, sid)
    if _is_ph_env():
        sid = (os.environ.get("CXO_SESSION_ID") or "").strip()
        if not sid:
            raise PermissionError("a Project Head session with no CXO_SESSION_ID cannot "
                                  "send: it would have no identity (org restructure P2)")
        return Identity("cxo", PH_ROLE, sid)
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:
        return Identity("dev", os.environ.get("WORKER_ROLE", "dev"), task_id)
    cto_sid = os.environ.get("CTO_SESSION_ID")
    if cto_sid:
        return Identity("cxo", "cto", cto_sid)
    if _is_ceo_env():
        return CEO_IDENTITY
    raise _no_identity()


# ---------------------------------------------------------------------------
# Wake nudge -- the org's ONE low-level tmux-send-keys primitive
# (`_wake_tmux_send`) plus the ONE generic wrap/log/never-raise wrapper
# (`attempt_wake`), replacing the 3 near-identical copy-pasted versions that
# used to live one in each of send_to_cxo.py, send_to_worker.py, send_to_cto.py.
# Each direction file keeps its OWN logic for resolving which session name
# to wake -- it just passes the resolved name in here.
# ---------------------------------------------------------------------------

_WAKE_MARKER_TEMPLATE = "[New message from {label}]"
_LABEL_PUNCT = frozenset(" _.#()-:/@+")


def _safe_label(label: str) -> str:
    """The label as it may be typed into a pane: letters, marks, digits, spaces
    and a little punctuation, at most 80 characters. No control character (a
    CR would submit the line early and type the rest as a new prompt) and no
    bracket (a label cannot close the marker and start text of its own)."""
    import unicodedata
    out = "".join(c for c in (label or "")
                  if c in _LABEL_PUNCT or unicodedata.category(c)[0] in "LMN")
    return " ".join(out.split())[:80] or "?"


class WakeHeld(RuntimeError):
    """`_wake_tmux_send` typed nothing, or pressed no Enter, because of what the
    target pane shows or because it could not read the pane. `attempt_wake`
    catches it like any other wake failure: one "wake failed: <session>: <why>"
    log line, False, never raised to the sender. The letter is already in the
    mailbox; the target's UserPromptSubmit hook (scripts/hook-inbox.py) drains
    it on that session's next prompt."""


_WAKE_CAPTURE_TIMEOUT_S = 5


def _why_not_type(screen: str) -> str | None:
    """None when the wake may type: no choice prompt is up and the whole input
    box is empty. A busy pane (a turn running) passes: typed text queues as a
    mid-turn message."""
    if pane_waiting(screen):
        return "choice prompt on screen"
    if typed_text(screen) is None:
        return "no input box on screen"
    if not box_empty(screen):
        return "draft in the input box"
    return None


def _why_not_enter(screen: str, typed: str) -> str | None:
    """None when Enter may be pressed: no choice prompt is up and the input box
    holds nothing but (the start of) what this wake typed, or nothing at all
    (the first Enter already submitted it; the rescue Enter then lands on an
    empty box). Anything else in the box is somebody's keys, which Enter would
    submit."""
    if pane_waiting(screen):
        return "choice prompt on screen"
    shown = typed_text(screen)
    if shown is None:
        return "no input box on screen"
    if not box_empty(screen) and not _squash(typed).startswith(shown):
        return "draft in the input box"
    return None


def _look(tmux: str, session: str, typed: str | None, held: str) -> None:
    """Capture the pane (`capture-pane -p`, on the same target the keys go to)
    and raise WakeHeld(held.format(why=...)) unless the next key may go: before
    the typing (`typed` None) `_why_not_type`, before an Enter `_why_not_enter`.
    Fails closed: a capture that exits non-zero or times out is a reason too."""
    try:
        r = subprocess.run(
            [tmux, "capture-pane", "-p", "-t", session],
            capture_output=True, text=True, timeout=_WAKE_CAPTURE_TIMEOUT_S,
        )
        if r.returncode != 0:
            why = f"could not read the pane (tmux exit {r.returncode})"
        elif typed is None:
            why = _why_not_type(r.stdout or "")
        else:
            why = _why_not_enter(r.stdout or "", typed)
    except (OSError, subprocess.SubprocessError) as e:
        why = f"could not read the pane ({type(e).__name__})"
    if why:
        raise WakeHeld(held.format(why=why))


def _wake_tmux_send(session: str, text: str) -> None:
    """Type `text` into tmux `session` and submit it with a settle-delay +
    rescue Enter -- NOT via `tools.tmux_session.send_keys()`.

    GH #70: `send_keys()` sends typed text then `C-m` back-to-back with
    zero settle delay, suspected of hitting the same bracketed-paste
    Enter-swallow `lib.iterm_type` already documents and fixed for iTerm --
    found live when a message typed via that exact function sat unsubmitted
    in a CMO composer, and a later bare `Enter` (tmux keyname, not `C-m`),
    sent as its own separate command after the composer had settled,
    worked. This is that settle-delay+rescue sequence, mirroring
    `lib.iterm_type.type_submit_fragment`'s pattern (type, delay 0.4, key,
    delay 0.3, key again as rescue) rather than the unproven zero-delay path
    GH #70 flagged. `tools.tmux_session.send_keys()` is untouched -- fixing
    it is GH #70's job, out of scope here.

    It looks first (2026-10-14). Enter on a pane showing a Claude Code choice
    prompt picks the highlighted option, usually "1. Yes", so a peer's letter
    could approve a permission prompt meant for the CEO; text typed onto his
    draft would be submitted with it. So the pane is captured (lib.pane_screen,
    the predicates tools/rename_service.py uses) right before the typing and
    again right before EACH Enter:
      * a choice prompt up, a draft in the box, no input box, or a capture
        that fails or times out before typing -> no key at all;
      * the same after typing -> no Enter (the marker stays in the box).
    Either way it raises WakeHeld with the reason. A busy pane (a turn
    running) with an empty box is woken exactly as before: the typed marker
    queues as a mid-turn message.
    """
    tmux = tmux_session.tmux_bin()
    _look(tmux, session, None, "not woken: {why}; nothing typed")
    subprocess.run(
        [tmux, "send-keys", "-t", session, "-l", text],
        capture_output=True, text=True, check=True, timeout=5,
    )
    time.sleep(0.4)
    _look(tmux, session, text, "not woken: {why} after typing; no Enter")
    subprocess.run(
        [tmux, "send-keys", "-t", session, "Enter"],
        capture_output=True, text=True, check=True, timeout=5,
    )
    time.sleep(0.3)
    _look(tmux, session, text, "not confirmed: {why} before the rescue Enter; no second Enter")
    subprocess.run(
        [tmux, "send-keys", "-t", session, "Enter"],
        capture_output=True, text=True, check=True, timeout=5,
    )


# ---------------------------------------------------------------------------
# Windows wake (W3.5) -- the tmux path above has no Windows equivalent, and ssh
# lands in session 0, which has no desktop. So the sender only WRITES A REQUEST
# FILE and runs `schtasks /run /tn MooniexOrgWake`; that task (registered once
# by the CEO, windows/register-org-tasks.ps1) runs in the console session, and
# windows/wake-request.ps1 -> windows/wake.ps1 types the marker into the target
# Windows Terminal tab -- and refuses to send a key unless that tab is verifiably
# in front with keyboard focus in it. docs/ops/windows-wake.md has the numbers.
# ---------------------------------------------------------------------------

WAKE_TASK_NAME = "MooniexOrgWake"
WAKE_DIR = ROOT / "state" / "wake"
_WAKE_WAIT_S = 15.0
_WAKE_RUN_TIMEOUT_S = 15  # the `schtasks /run` call
# The longest wake_windows_tab can block: the schtasks call, then the wait for
# the result. lib/mesh.py sizes the deliver_letter timeout from it.
WAKE_WORST_CASE_S = _WAKE_RUN_TIMEOUT_S + _WAKE_WAIT_S
_WAKE_LABEL_RE = re.compile(r"[A-Za-z0-9_.#-]{1,40}")
_WAKE_SID_RE = re.compile(r"[A-Za-z0-9_-]{6,40}")


def _is_windows() -> bool:
    return sys.platform == "win32"


def wake_windows_tab(session: str, label: str, *, wait_s: float = _WAKE_WAIT_S,
                     wake_dir: Path | None = None, run=subprocess.run,
                     sleep=time.sleep) -> dict:
    """Ask the Windows box to type the wake marker into C-level `session`'s tab.

    `session` is `<role>-<sid>` (the same name the tmux path uses). A live
    session's tab is titled `<Role> #<sid> (<topic>)`, and the topic changes,
    so the request names the stable token `#<sid>` and wake.ps1 runs in
    -Contains mode. Returns {"woke": bool, "why": str}; True only when
    wake.ps1 reported that the keys went to the verified tab. Ordinary failures
    (no task registered, tab not found, tab not in front) come back as
    woke=False, they do not raise."""
    m = session_name.ROLE_RE.match(session or "")
    if not m or not _WAKE_SID_RE.fullmatch(m.group(2)):
        return {"woke": False, "why": f"session name is not <role>-<sid>: {session!r}"}
    if not _WAKE_LABEL_RE.fullmatch(label or ""):
        return {"woke": False, "why": f"label outside the wake marker alphabet: {label!r}"}
    base = wake_dir if wake_dir is not None else WAKE_DIR
    req_dir, res_dir = base / "requests", base / "results"
    req_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    req_id = f"{int(time.time() * 1000)}-{secrets.token_hex(4)}"
    req_path = req_dir / f"{req_id}.json"
    tmp = req_dir / f"{req_id}.tmp"
    tmp.write_text(json.dumps({
        "title": f"#{m.group(2)}",
        "marker": _WAKE_MARKER_TEMPLATE.format(label=label),
        "contains": True,
    }), encoding="ascii")
    os.replace(tmp, req_path)  # the runner only ever sees a complete *.json

    def _withdraw() -> None:
        try:
            req_path.unlink()
        except OSError:
            pass

    try:
        r = run(["schtasks", "/run", "/tn", WAKE_TASK_NAME],
                capture_output=True, text=True, timeout=_WAKE_RUN_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as e:
        _withdraw()
        return {"woke": False, "why": f"schtasks /run failed: {e}"}
    if r.returncode != 0:
        _withdraw()  # never leave a request that fires whenever the task appears
        detail = ((r.stderr or r.stdout or "").strip().replace("\n", " "))[:120]
        return {"woke": False, "why": (f"task {WAKE_TASK_NAME} did not start (rc {r.returncode}: "
                                       f"{detail}); has the CEO run windows/register-org-tasks.ps1?")}

    res_path = res_dir / f"{req_id}.json"
    deadline = time.monotonic() + wait_s
    while True:
        if res_path.is_file():
            try:
                res = json.loads(res_path.read_text(encoding="ascii", errors="replace"))
            except ValueError:
                res = None
            if res is not None:
                try:
                    res_path.unlink()
                except OSError:
                    pass
                if res.get("exit") == 0:
                    return {"woke": True, "why": "keys sent to the verified tab"}
                return {"woke": False, "why": f"wake.ps1 exit {res.get('exit')}: {str(res.get('output', ''))[:120]}"}
        if time.monotonic() >= deadline:
            _withdraw()
            return {"woke": False, "why": f"no result from {WAKE_TASK_NAME} within {wait_s:g}s"}
        sleep(0.25)


def _attempt_wake_windows(session: str, label: str, log_prefix: str) -> bool:
    """attempt_wake's Windows body: same never-raise, same log lines. True only
    when wake_windows_tab reported that the keys went to the verified tab."""
    woke = False
    try:
        try:
            notify.info(f"[{log_prefix}] wake attempted: {session}")
        except Exception:
            pass
        r = wake_windows_tab(session, label)
        woke = r["woke"] is True
        try:
            notify.info(f"[{log_prefix}] wake {'succeeded' if r['woke'] else 'failed'}: {session}: {r['why']}")
        except Exception:
            pass
    except Exception as e:
        try:
            notify.info(f"[{log_prefix}] wake failed: {session}: {e}")
        except Exception:
            pass
    return woke


def attempt_wake(session: str | None, label: str, log_prefix: str, *,
                  send_fn=_wake_tmux_send) -> bool:
    """Best-effort attention nudge for a just-delivered letter's recipient.
    The one hard rule (task-cf325742): NOTHING from this step may
    propagate or change the caller's notion of success -- no tmux session,
    a tmux error, a timeout, anything. The mailbox write already succeeded
    before this is ever called; this is strictly on top of it.

    Returns True only when the nudge reached a live session (every tmux call
    exited 0; on Windows, wake.ps1 reported keys sent to the verified tab).
    False for everything else: no session, not live, a tmux error, a timeout.
    The value is information for a caller that wants to report the wake
    (tools/node_dispatch.py does); a caller that ignores it behaves exactly as
    before, and False never means the letter was not delivered.

    `session` is already resolved by the caller -- each send_to_*.py file
    has its own logic for that (task row lookup for DEVs,
    `tools.session_name.lock_basename()` for C-level sessions). Does
    nothing (silently) if `session` is falsy or not live -- the letter is
    already queued; there's just no live process to poke right now.

    `log_prefix` names the caller in `state/logs/*.log` lines (e.g.
    "send_to_cxo") so a human watching the log can still tell which
    direction a wake came from.

    `send_fn` defaults to this module's own `_wake_tmux_send`, but every
    current caller passes its OWN imported reference explicitly
    (`send_fn=_wake_tmux_send`, resolved in the CALLER's own module
    globals) -- Python resolves a bare name via the *defining* module's
    globals, never the caller's, so without this indirection a test that
    monkeypatches e.g. `tools.send_to_worker._wake_tmux_send` would silently
    have no effect on what actually runs.
    """
    if not session:
        return False
    # W3.5 win32 branch -- additive; everything after the end marker is unchanged.
    if _is_windows():
        return _attempt_wake_windows(session, _safe_label(label), log_prefix)
    # end W3.5 win32 branch
    try:
        if not tmux_session.has_session(session):
            try:
                notify.info(f"[{log_prefix}] wake skipped (no live session): {session}")
            except Exception:
                pass
            return False
        try:
            notify.info(f"[{log_prefix}] wake attempted: {session}")
        except Exception:
            pass
        marker = _WAKE_MARKER_TEMPLATE.format(label=_safe_label(label))
        send_fn(session, marker)
        try:
            notify.info(f"[{log_prefix}] wake succeeded: {session}")
        except Exception:
            pass
        return True
    except Exception as e:
        try:
            notify.info(f"[{log_prefix}] wake failed: {session}: {e}")
        except Exception:
            pass
        return False
