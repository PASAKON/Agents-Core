"""C-level cross-talk: queue a message into another C-level's mailbox.

The sender (typically CTO/CMO/CGO/CFO acting on a request from CEO)
needs to ask a sibling C-level to do something (e.g. CTO → CFO for a
budget approval, CMO → CGO for an attribution check). This mirrors
`tools/send_to_dev.py` but targets C-level boxes identified by role +
session id (recorded by `scripts/cxo-claude.sh` in
`state/locks/<role>-active`).

Task task-de2cdc15 (CEO directive 2026-08-14, option A: queue only, no
wake attempt). `send()` used to type the message into a live terminal --
tmux-first, iTerm-fallback (GH #69) -- and that typing path is exactly
what failed silently three different ways in one day: GH #69 itself
(bytes landed in the *sender's own* session, `didSend` still true), a
swallowed Enter that left messages sitting unsubmitted in the composer,
and key-encoding differences that did nothing without raising. "Text is
on screen" was being read as "the message arrived" -- it is not the same
claim, and no fallback chain fixes that, because a fallback that can
silently misdeliver is worse than no fallback. `send()` now writes the
message into the recipient's `lib.mailbox` box and returns success on
that write alone; it no longer depends on tmux or iTerm succeeding, and
it does not attempt to wake the recipient (that is `spawn()`'s job, a
separate code path this task did not touch).

The message is prefixed with `[<SENDER-ROLE>]:` so the receiving
C-level (and any onlooking human) can tell who is talking.

Usage:
    python -m tools.send_to_cxo <role> "<message>"
    python -m tools.send_to_cxo cfo "ขอ budget $500 สำหรับ FB ads campaign X"
    python -m tools.send_to_cxo --from cgo cfo "ROAS hit 4.2 — request +$1k uplift"
    python -m tools.send_to_cxo --spawn cfo "budget review needed"

`<role>` = target C-level (cto|cmo|cgo|cfo).
Sender role auto-detected from $CXO_ROLE env when invoked from within a
C-level chat tab; falls back to "CEO" when nothing is set.

--spawn (default OFF for Phase 2): open a new ephemeral iTerm tab for
the request instead of typing into the primary tab. Dedupe-checked:
reuses an alive tab with same topic-slug if created within 10 minutes.

Routing guard (CEO 2026-08-14):
  a) Max 3 delegation hops, originator counted as level 1.
  b) A session may reply ONLY to whoever spawned it -- "ตัวที่ Spawn
     อะไรมา เป็นเจ้าของคนๆ นั้น Reply ได้เฉพาะเจ้าของ". Stated once: a
     session may send only to its OWNER, or to a session it spawned
     ITSELF. Everything else is refused.
  c) The ORIGINATOR of a chain owns the outcome. If you ask another
     C-level to do something and it goes wrong, YOU are accountable --
     delegating a request never transfers responsibility for it.
  d) Every hop is logged (lib.notify -> state/logs/cto*.log) so the CEO
     can see the whole chain. No approval gate, but never invisible.

Ownership is RECORDED at spawn time and resolved from that record, never
from the message envelope -- a lost or edited envelope must not be able
to unlock a direct reply. See `authorize()` below for the two stores this
reuses (tasks.owner_cto/owner_role for DEVs, a state/locks/ sidecar file
for ephemeral C-level sessions) and why neither needed a new DB column.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib import mailbox
from lib import notify
from lib.config import display_for, is_c_level
from lib.iterm_type import type_submit_fragment

ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = ROOT / "state" / "locks"


def _active_session_id(role: str) -> str | None:
    """Return the most-recent C-level session id for `role`, or None.

    Looks first at the `<role>-active` pointer that cxo-claude.sh writes
    on boot. Falls back to the newest matching `.winid` file so we still
    work for sessions started before this helper existed.
    """
    pointer = LOCKS_DIR / f"{role}-active"
    if pointer.exists():
        sid = pointer.read_text().strip()
        if sid:
            return sid
    candidates = sorted(
        LOCKS_DIR.glob(f"{role}-*.winid"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in candidates:
        sid = p.stem.split("-", 1)[1]
        if sid != "active":
            return sid
    return None


def _resolve_sender_role() -> str:
    """Best-effort sender label. CEO when no C-level env is set."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        return display_for(r)
    if os.environ.get("CTO_SESSION_ID"):
        return display_for("cto")
    return "CEO"


# ---------------------------------------------------------------------------
# Ownership + routing guard (Gap 3)
# ---------------------------------------------------------------------------
#
# Two independent, already-existing stores are reused -- neither needed a
# new DB column (IRON §30 / ADR 0008 "extend before create"):
#
#   * DEV ownership: `tasks.owner_role` / `tasks.owner_cto` (lib/db.py).
#     Stamped by create_task for every DEV task regardless of which
#     C-level created it. Untouched here, just read.
#
#   * C-level session ownership: `c_level_sessions` has no spawner-of
#     column and may not gain one, so an ephemeral C-level tab's spawner
#     is recorded as a plain sidecar file next to that session's existing
#     .lock/.winid/.tty/.uuid/.topic files in state/locks/ --
#     `<role>-<session_id>.spawned_by`, written once, at spawn time, by
#     the spawning call itself (`record_spawn`, called from `spawn()`).
#
# A PRIMARY session -- one launched directly (cto-claude.sh / cxo-claude.sh
# with no --session override), never reached through `spawn()` -- has no
# such file. That absence IS the root case: "no recorded owner" means
# "reports directly to the CEO", and any two root C-levels may message
# each other freely as peers -- the routine "CTO asks CFO for budget
# approval" case `send()` exists for. The 3-hop cap and reply-to-owner-only
# rule bite once a hop has actually gone through `spawn()`.
#
# Depth is NEVER trusted from an inbound envelope's own hop counter --
# `authorize()` takes no envelope/message argument at all. It recomputes
# depth by walking the recorded-ownership chain each time, so a forged or
# stripped envelope cannot buy a deeper reach than the real chain allows.
# The chain string in a refusal/log line exists purely for a human to read.

MAX_HOPS = 3


@dataclass(frozen=True)
class Identity:
    """A node in the ownership graph: a C-level session or a DEV task."""

    kind: str  # "cxo" | "dev" | "ceo"
    role: str  # cto/cmo/cgo/cfo for "cxo"; the DEV role key for "dev"
    session_id: str | None  # session id ("cxo") or task_id ("dev"); None for "ceo"

    def label(self) -> str:
        if self.kind == "ceo":
            return "CEO"
        disp = display_for(self.role) if self.kind == "cxo" else self.role
        return f"{disp}#{self.session_id}" if self.session_id else disp


CEO_IDENTITY = Identity("ceo", "CEO", None)


def _spawn_record_path(role: str, session_id: str) -> Path:
    return LOCKS_DIR / f"{role}-{session_id}.spawned_by"


def record_spawn(spawner: Identity, target_role: str, target_session_id: str) -> None:
    """Persist that `spawner` spawned the ephemeral C-level session
    (target_role, target_session_id). Called exactly once, at spawn time,
    by `spawn()` -- never inferred later from a message."""
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    _spawn_record_path(target_role, target_session_id).write_text(
        f"{spawner.kind}:{spawner.role}:{spawner.session_id or ''}"
    )


def _owner_of(identity: Identity) -> Identity | None:
    """Recorded owner of `identity`, or None if it is a root (CEO-owned)
    identity: a primary C-level session never reached through `spawn()`,
    or a DEV task with no owner_cto on record."""
    if identity.kind == "ceo":
        return None
    if identity.kind == "dev":
        t = db.get_task(identity.session_id) if identity.session_id else None
        if not t or not t.get("owner_cto"):
            return None
        return Identity("cxo", t.get("owner_role") or "cto", t["owner_cto"])
    # kind == "cxo"
    if not identity.session_id:
        return None
    p = _spawn_record_path(identity.role, identity.session_id)
    if not p.exists():
        return None
    parts = p.read_text().strip().split(":", 2)
    if len(parts) != 3:
        return None
    kind, role, sid = parts
    return Identity(kind, role, sid or None)


def _chain(identity: Identity) -> list[Identity]:
    """[root, ..., identity] by walking recorded ownership upward. Always
    terminates: spawning mints a fresh session/task id every time, so the
    ownership graph is a DAG -- the cycle guard is defensive only."""
    chain = [identity]
    seen = {(identity.kind, identity.role, identity.session_id)}
    cur = identity
    while True:
        owner = _owner_of(cur)
        if owner is None:
            break
        key = (owner.kind, owner.role, owner.session_id)
        if key in seen:
            break
        seen.add(key)
        chain.append(owner)
        cur = owner
    chain.reverse()
    return chain


def _chain_str(identity: Identity) -> str:
    return " -> ".join(i.label() for i in _chain(identity))


def current_identity() -> Identity:
    """Who is calling send_to_cxo right now, resolved from process env --
    never from anything the caller passes in."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        if sid:
            return Identity("cxo", r, sid)
    task_id = os.environ.get("DEV_TASK_ID")
    if task_id:
        return Identity("dev", os.environ.get("DEV_ROLE", "dev"), task_id)
    cto_sid = os.environ.get("CTO_SESSION_ID")
    if cto_sid:
        return Identity("cxo", "cto", cto_sid)
    return CEO_IDENTITY


def authorize(sender: Identity, target_role: str, target_session_id: str | None,
              *, spawning: bool) -> None:
    """Raise PermissionError if `sender` may not reach (target_role,
    target_session_id). Silent return means allowed.

    Rule, stated once: a session may send only to its OWNER, or to a
    session it spawned ITSELF. A root sender (no recorded owner -- a
    primary session, never reached through `spawn()`) additionally gets
    the peer exception: any primary C-level may reach any other C-level's
    primary session -- level 1 talking to level 1, not a delegation chain.
    """
    owner = _owner_of(sender)
    if owner is None:
        return  # root: free peer messaging, and free to spawn a level-2 child
    if spawning:
        depth = len(_chain(sender)) + 1
        if depth > MAX_HOPS:
            raise PermissionError(
                f"refused: hop {depth} exceeds max {MAX_HOPS} delegation "
                f"levels. Chain: {_chain_str(sender)} -> <new {target_role}>"
            )
        return
    target_label = (
        f"{display_for(target_role) if is_c_level(target_role) else target_role}"
        + (f"#{target_session_id}" if target_session_id else "")
    )
    if not (owner.role == target_role
            and (target_session_id is None or owner.session_id == target_session_id)):
        raise PermissionError(
            f"refused: {sender.label()} may reply only to its owner "
            f"{owner.label()}, not {target_label}. Chain: {_chain_str(sender)}"
        )


def _log_hop(sender: Identity, target_role: str, target_session_id: str | None) -> None:
    """One line per hop so the CEO can see the whole chain (rule d).
    Best-effort: a logging failure must never block a delivered message."""
    target_label = (
        f"{display_for(target_role) if is_c_level(target_role) else target_role}"
        + (f"#{target_session_id}" if target_session_id else "")
    )
    try:
        notify.info(f"[send_to_cxo] {_chain_str(sender)} -> {target_label}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Spawn-path helpers (--spawn flag, Phase 2)
# ---------------------------------------------------------------------------

def _make_topic_slug(message: str) -> str:
    """First 30 chars of message lowercased → kebab slug, ≤30 chars.

    Non-Latin messages (Thai is the org's working language) strip to an
    empty slug — every such request would then dedupe-collide with every
    other one for the same role within 10 minutes and get typed into the
    wrong tab. Fall back to a content hash so distinct topics stay distinct."""
    raw = message[:30].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")[:30]
    if not slug:
        digest = hashlib.sha1(message.strip().encode("utf-8")).hexdigest()[:8]
        slug = f"t-{digest}"
    return slug


def _get_live_winids() -> set[str]:
    """Return the set of live iTerm2 window ids as strings."""
    r = subprocess.run(
        ["osascript", "-e", 'tell application "iTerm2" to return id of windows'],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return set()
    return set(r.stdout.strip().replace(" ", "").split(","))


def _send_to_ephemeral_tab(tab_title: str, text: str,
                           slug: str | None = None) -> None:
    """Type `text` into an existing ephemeral tab.

    Match: full `tab_title` OR (when `slug` given) any tab carrying the
    same role prefix + topic slug — covers reuse when the original tab
    was spawned by a different sender ("CFO <- CMO: x" vs "CFO <- CTO: x")."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    submit = type_submit_fragment(escaped)
    escaped_title = tab_title.replace("\\", "\\\\").replace('"', '\\"')
    prefix = tab_title.split("<-")[0].strip()  # e.g. "CFO"
    escaped_prefix = prefix.replace("\\", "\\\\").replace('"', '\\"')
    escaped_slug = (slug or "").replace("\\", "\\\\").replace('"', '\\"')
    slug_clause = (
        f' or ((tabName contains "{escaped_prefix} <-") and (tabName contains ": {escaped_slug}"))'
        f' or ((sessName contains "{escaped_prefix} <-") and (sessName contains ": {escaped_slug}"))'
        if slug else ""
    )
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        try
          set tabName to ""
          try
            set tabName to name of t
          end try
          set sessName to ""
          try
            set sessName to name of current session of t
          end try
          if (tabName contains "{escaped_title}") or (sessName contains "{escaped_title}"){slug_clause} then
            tell w to select
            tell t to select
            tell current session
              {submit}
            end tell
            set didSend to true
          end if
        end try
      end tell
    end repeat
  end repeat
  if not didSend then error "no iTerm tab matched {escaped_title}"
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


def _spawn_new_ephemeral(
    role: str, session_id: str, tab_title: str, initial_text: str
) -> None:
    """Open a new iTerm window running cxo-claude.sh for role/session.

    Writes a temp shell script so Unicode / special chars in initial_text
    never need escaping inside an AppleScript string literal.
    """
    def _sh_sq(s: str) -> str:
        return "'" + s.replace("'", "'\"'\"'") + "'"

    cxo_sh = str(ROOT / "scripts" / "cxo-claude.sh")
    shell_cmd = " ".join([
        f"export CXO_SESSION_ID={_sh_sq(session_id)}",
        "&&",
        "bash", _sh_sq(cxo_sh),
        "--role", role,
        "--session", _sh_sq(session_id),
        "--tab-title", _sh_sq(tab_title),
        "--initial-prompt", _sh_sq(initial_text),
    ])

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, dir="/tmp"
    ) as tmp:
        tmp.write("#!/usr/bin/env bash\n")
        tmp.write(shell_cmd + "\n")
        tmp_path = tmp.name
    os.chmod(tmp_path, 0o755)

    title_as = tab_title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "iTerm"
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "{title_as}"
      write text "bash {tmp_path}"
    end tell
  end tell
end tell
'''
    try:
        subprocess.run(["osascript", "-e", script], check=True)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def spawn(role: str, message: str, sender: str | None = None) -> str:
    """Ephemeral-spawn path: open a new tab for this request.

    Dedupe-checked: if an alive ephemeral tab with the same topic-slug
    was created within the last 10 minutes, reuse it instead of opening
    a second tab. Does NOT write the `<role>-active` pointer.
    """
    if not is_c_level(role):
        raise ValueError(
            f"{role} is not a C-level role. Known C-level: cto, cmo, cgo, cfo"
        )
    sender_identity = current_identity()
    authorize(sender_identity, role, None, spawning=True)
    label = sender or _resolve_sender_role()
    display = display_for(role)
    topic_slug = _make_topic_slug(message)
    # Attribute the actual sender — a CMO→CFO request must not read "<- CTO".
    tab_title = f"{display.upper()} <- {label}: {topic_slug}"
    full_text = f"[{label}]: {message}"

    # Dedupe: scan existing ephemeral lock files for this role
    live_winids = _get_live_winids()
    ten_min_ago = time.time() - 600

    for lock_file in sorted(
        LOCKS_DIR.glob(f"{role}-req-*.winid"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        try:
            winid = lock_file.read_text().strip()
            if winid not in live_winids:
                continue  # stale — cleanup-zombies.sh handles removal
            if lock_file.stat().st_mtime < ten_min_ago:
                continue
            topic_file = lock_file.with_suffix(".topic")
            if not topic_file.exists():
                continue
            if topic_file.read_text().strip() != topic_slug:
                continue
            # Match: reuse this alive ephemeral tab. Ownership was recorded
            # when it was first created (by whoever spawned it, possibly a
            # different sender) — reuse never re-records or transfers it.
            # lock_file.stem is "<role>-req-XXXXXXXX"; strip the role prefix
            # to recover the session id for the hop-log line.
            reused_sid = lock_file.stem[len(role) + 1:]
            _send_to_ephemeral_tab(tab_title, full_text, slug=topic_slug)
            _log_hop(sender_identity, role, reused_sid)
            return f"reused {display} ephemeral tab {lock_file.stem}: {full_text}"
        except OSError:
            continue

    # No alive matching tab — spawn new
    session_id = f"req-{secrets.token_hex(4)}"
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    topic_path = LOCKS_DIR / f"{role}-{session_id}.topic"
    topic_path.write_text(topic_slug)

    try:
        _spawn_new_ephemeral(role, session_id, tab_title, full_text)
    except Exception:
        topic_path.unlink(missing_ok=True)
        raise

    record_spawn(sender_identity, role, session_id)
    _log_hop(sender_identity, role, session_id)
    return f"spawned new {display} tab [{session_id}]: {full_text}"


def _mailbox_identity(identity: Identity) -> tuple[str, str]:
    """(role, session_id) pair for a letter's `from` field / filename.

    CEO has no session id of its own -- fall back to the literal "ceo"
    placeholder, which can never collide with a real hex session id."""
    role = identity.role.lower()
    return (role, identity.session_id) if identity.session_id else (role, "ceo")


def _chain_ids(identity: Identity) -> list[str]:
    """The recorded-ownership chain as `role:session_id` strings, oldest
    (root) first -- for the letter's `chain` audit field only. Built from
    `_chain()`, the same recorded-ownership walk `authorize()` uses, never
    from anything a caller passes."""
    return [f"{i.role.lower()}:{i.session_id}" if i.session_id else i.role.lower()
            for i in _chain(identity)]


def send(role: str, message: str, sender: str | None = None) -> str:
    """Programmatic API (legacy path). Returns one-line summary string.

    Task task-de2cdc15 (CEO directive 2026-08-14, option A): queues the
    message into the recipient's `lib.mailbox` box and returns once that
    write succeeds -- it no longer types into a terminal, so it no longer
    depends on tmux or iTerm succeeding, and it does not attempt to wake
    the recipient. See the module docstring for why the old typed-message
    path (GH #69, tmux-first/iTerm-fallback) was removed rather than kept
    as a fallback.

    Contract: queued or raised, never "probably". Raises ValueError when
    the target role has no registered session (unchanged failure mode --
    see `_active_session_id()`). Raises PermissionError when the routing
    guard refuses the hop (see `authorize()`); a refusal writes nothing.
    """
    if not is_c_level(role):
        raise ValueError(
            f"{role} is not a C-level role. Known C-level: cto, cmo, cgo, cfo"
        )
    sid = _active_session_id(role)
    if not sid:
        raise ValueError(
            f"no active {display_for(role)} session found. "
            f"Spawn one first: bash scripts/spawn-cxo.sh --role {role}"
        )
    sender_identity = current_identity()
    authorize(sender_identity, role, sid, spawning=False)
    label = sender or _resolve_sender_role()
    _log_hop(sender_identity, role, sid)
    from_role, from_sid = _mailbox_identity(sender_identity)
    chain = _chain_ids(sender_identity) + [f"{role}:{sid}"]
    mailbox.send(role, sid, message, from_role, from_sid, chain=chain)
    return f"queued to {display_for(role)} #{sid}: [{label}]: {message}"


def main() -> int:
    argv = sys.argv[1:]
    sender_override = None
    do_spawn = False

    remaining: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--spawn":
            do_spawn = True
        elif a == "--from":
            if i + 1 >= len(argv):
                print("--from requires a role argument", file=sys.stderr)
                return 1
            r = argv[i + 1]
            sender_override = display_for(r) if is_c_level(r) else r
            i += 1
        else:
            remaining.append(a)
        i += 1
    argv = remaining

    if len(argv) < 2:
        print(
            'usage: python -m tools.send_to_cxo [--spawn] [--from <role>] <target_role> "<message>"',
            file=sys.stderr,
        )
        return 1
    role, message = argv[0], argv[1]
    try:
        if do_spawn:
            result = spawn(role, message, sender_override)
        else:
            result = send(role, message, sender_override)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except PermissionError as e:
        print(str(e), file=sys.stderr)
        return 4
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if hasattr(e, "stderr") else ""
        print(f"AppleScript failed: {stderr or e}", file=sys.stderr)
        return 3
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
