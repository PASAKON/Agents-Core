"""Wakes SomPong to digest C-level replies for the CEO (task-67ba0c4f D2).

task-df6de4d4 built the reply half: a C-level finishing a CEO order calls
`report_to_ceo(order_id, status, detail)`, which drops a letter into
`state/inbox/secretary-sompong/`. Nothing reads that box -- SomPong is
`claude -p`, spawned per Telegram message and gone between messages, so it
can never have a `hook-inbox.py` the way a live C-level session does.

This loop is what reads it:

    C-level finishes -> report_to_ceo(...) -> letter in secretary-sompong/
                                                    |
                                            this loop sees it
                                                    |
                                    invokes SomPong with the letters
                                                    |
                                      SomPong composes for the CEO
                                                    |
                                            Telegram -> CEO

Order of operations per tick, and why:

  1. **Peek, do not drain.** `lib.mailbox.drain()` deletes everything it
     returns; if the Telegram send then failed, those replies would be gone
     with no record. Read with a peek that also keeps each letter's file
     path, remember exactly which files were consumed, delete only those,
     only after the send succeeds. A letter that arrives mid-cycle (or past
     the batch cap) survives untouched to the next tick.
  2. **Batch.** Several C-levels reporting at once is one message to the
     CEO, not several -- capped at MAX_BATCH, with the digest saying so
     when some were held over.
  3. **Invoke SomPong over HTTP**, through the exact same
     `/v1/chat/completions` endpoint the Telegram webhook uses -- never a
     direct `import run_secretary_turn`. Going through the server means
     this loop shares its `max_concurrent=1` slot, so a waker turn can
     never run concurrently with a turn the CEO is waiting on. Uses the
     CEO's own conversation_id so the digest lands in the same resumable
     session and SomPong remembers having reported it.
  4. **Send SomPong's reply to the CEO** via lib.telegram_out, then delete
     the consumed letters. In that order -- a letter is only removed once
     it has actually reached the CEO.

Robustness, matching runners/mac_agent.py::main's discipline (read that
file -- this loop is a sibling of it):

  - Single-flight: a non-blocking flock so two ticks can never overlap.
  - Poison-letter cap: a letter that fails MAX_RETRIES times in a row is
    moved to a `failed/` subdirectory instead of retried forever against a
    paid API.
  - One bad tick logs and sleeps; the loop itself never crashes.

Run:  python -m runners.secretary_waker          (loop)
      python -m runners.secretary_waker --once   (single tick, for testing)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover -- POSIX only; this org runs Mac + Linux
    fcntl = None  # type: ignore[assignment]

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
from lib import telegram_out  # noqa: E402
from lib.logger import get_logger  # noqa: E402
from runners import secretary_server  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
POLL_SECONDS = int(os.environ.get("SECRETARY_WAKER_POLL_SECONDS", "60"))
MAX_BATCH = int(os.environ.get("SECRETARY_WAKER_MAX_BATCH", "5"))
MAX_RETRIES = int(os.environ.get("SECRETARY_WAKER_MAX_RETRIES", "5"))
# Default derived from secretary_server's OWN claude-subprocess timeout, with
# margin -- a client timeout merely equal to the server's internal ceiling
# can fire in the same instant the server would have answered, turning an
# in-flight success into a false failure. Still independently overridable.
SECRETARY_TIMEOUT_SECONDS = int(
    os.environ.get("SECRETARY_WAKER_TIMEOUT_SECONDS")
    or secretary_server.SECRETARY_TIMEOUT_SECONDS + 30
)

# SomPong's own mailbox identity -- same values lib/ceo_report.py's
# report_to_ceo writes reply letters to (SECRETARY_TO_ROLE/
# SECRETARY_TO_SESSION_ID there). Duplicated rather than imported:
# ceo_report.py documents this exact independence reasoning for its own
# constants (it runs inside a C-level session process); the same reasoning
# applies here in the other direction.
SECRETARY_ROLE = "secretary"
SECRETARY_SESSION_ID = "sompong"

# State this loop owns, kept OUTSIDE the mailbox box on purpose: a sidecar
# file living inside state/inbox/secretary-sompong/ would risk being picked
# up by the letter scan below if it ever collided with the *.json pattern.
STATE_DIR = Path(os.environ.get("SECRETARY_WAKER_STATE_DIR") or ROOT / "state" / "secretary_waker")
LOCK_PATH = STATE_DIR / "waker.lock"
FAILCOUNT_PATH = STATE_DIR / "failcounts.json"

_LOGGER = None


def _log():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("secretary_waker")
    return _LOGGER


# ---------------------------------------------------------------------------
# Single-flight -- non-blocking flock, released by the kernel on exit (even
# `kill -9`) so a wedged holder can never lock out every future tick. Same
# idiom tools/maintab.py's _try_lock uses; reimplemented as one small
# function here rather than imported, since that module is iTerm-tab-titling
# specific and carries far more than this file needs.
# ---------------------------------------------------------------------------

def _try_lock(path: Path):
    """Non-blocking exclusive flock. Returns an open fd on success, or None
    if another tick already holds it (or flock is unavailable)."""
    if fcntl is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _unlock(fd) -> None:
    if fd is None:
        return
    try:
        os.close(fd)  # releases the flock too
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Mailbox read -- peek, but keep each letter's file path alongside its
# content. lib.mailbox.peek() only returns parsed bodies; deleting EXACTLY
# the letters actually consumed needs the path too. Reimplements peek()'s
# own directory scan (glob + parse, skip on failure) rather than reaching
# into mailbox._letters (private, no compatibility guarantee) -- still
# resolves the box through mailbox.INBOX_ROOT, the module global read at
# call time, so a test that monkeypatches it is honoured, never a
# hardcoded path.
# ---------------------------------------------------------------------------

def _box(root: Path | None = None) -> Path:
    base = root if root is not None else mailbox.INBOX_ROOT
    return base / f"{SECRETARY_ROLE}-{SECRETARY_SESSION_ID}"


def _peek_with_paths(root: Path | None = None) -> list[tuple[Path, dict]]:
    box = _box(root)
    if not box.is_dir():
        return []
    out: list[tuple[Path, dict]] = []
    for p in sorted(box.glob("*.json")):
        try:
            letter = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append((p, letter))
    return out


# ---------------------------------------------------------------------------
# Poison-letter cap -- a JSON sidecar under STATE_DIR (never inside the
# mailbox box itself), keyed by filename: mailbox.send()'s microsecond-
# timestamp names are already unique per box, so the filename alone is a
# stable key across ticks and process restarts.
# ---------------------------------------------------------------------------

def _load_failcounts(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_failcounts(path: Path, counts: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts), encoding="utf-8")


def _quarantine(letter_path: Path, box: Path) -> None:
    failed_dir = box / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    try:
        letter_path.rename(failed_dir / letter_path.name)
    except OSError as e:
        _log().error("could not quarantine %s: %s", letter_path, e)


def _record_failure(paths: list[Path], box: Path, failcount_path: Path,
                     max_retries: int) -> None:
    """Bump the consecutive-failure count for every letter in a failed batch
    attempt. Any that reach the cap move to failed/ instead of being retried
    forever -- the failure mode to design out against a paid API."""
    counts = _load_failcounts(failcount_path)
    for p in paths:
        n = counts.get(p.name, 0) + 1
        if n >= max_retries:
            _log().error("letter %s failed %s times in a row -- quarantining", p.name, n)
            _quarantine(p, box)
            counts.pop(p.name, None)
        else:
            counts[p.name] = n
    _save_failcounts(failcount_path, counts)


def _clear_failures(paths: list[Path], failcount_path: Path) -> None:
    counts = _load_failcounts(failcount_path)
    changed = False
    for p in paths:
        if counts.pop(p.name, None) is not None:
            changed = True
    if changed:
        _save_failcounts(failcount_path, counts)


# ---------------------------------------------------------------------------
# Digest formatting
# ---------------------------------------------------------------------------

def _format_letter(letter: dict) -> str:
    frm = letter.get("from") or {}
    role = frm.get("role", "?")
    sid = frm.get("session_id", "?")
    sent_at = letter.get("sent_at", "?")
    body = letter.get("body", "")
    return f"จาก {role} (session {sid}) เมื่อ {sent_at}:\n{body}"


def _build_digest_prompt(letters: list[dict], held: int) -> str:
    parts = [
        secretary_server.DIGEST_TURN_MARKER,
        f"จดหมายจาก C-level {len(letters)} ฉบับ:",
    ]
    for i, letter in enumerate(letters, 1):
        parts.append(f"\n--- {i} ---\n{_format_letter(letter)}")
    if held:
        parts.append(f"\n(เก็บไว้อีก {held} ฉบับ รอส่งรอบถัดไป)")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# SomPong invocation -- over HTTP, through the SAME /v1/chat/completions
# endpoint the Telegram webhook uses (never a direct `import
# run_secretary_turn`), so this shares secretary_server's own
# SECRETARY_MAX_CONCURRENT=1 slot. Host/port/key are read off the
# runners.secretary_server module rather than re-declared here, so the two
# can never point at different addresses; read at call time (module
# attribute access) so a test can monkeypatch secretary_server.SECRETARY_*
# the same way scripts/test_secretary_server.py already does.
# ---------------------------------------------------------------------------

def _ceo_conversation_id() -> str | None:
    """The CEO's own conversation_id, so the digest lands in the same
    resumable `claude --resume` session the CEO already talks to SomPong in
    (secretary_server.py's `user` field -> session_id map).

    mooniex-claudeflow's webhook (src/webhook/agents/hermes.js) sends the
    Telegram sender's `from.id` as `user` on every turn. In the CEO's own
    1:1 chat with the bot that value equals `chat.id` -- Telegram gives a
    private chat the same numeric id as its one human member -- which is
    exactly TELEGRAM_CEO_CHAT_ID (lib/telegram_out.py's own env var).
    Reused here rather than inventing a second identifier for the same chat.
    """
    return os.environ.get("TELEGRAM_CEO_CHAT_ID")


def _invoke_secretary(prompt: str) -> tuple[bool, str]:
    api_key = secretary_server.SECRETARY_API_KEY
    if not api_key:
        return False, "SECRETARY_API_KEY is not set"

    conversation_id = _ceo_conversation_id()
    if not conversation_id:
        return False, "TELEGRAM_CEO_CHAT_ID is not set (needed as the CEO's conversation_id)"

    url = (f"http://{secretary_server.SECRETARY_HOST}:{secretary_server.SECRETARY_PORT}"
           "/v1/chat/completions")
    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "secretary",
                "messages": [{"role": "user", "content": prompt}],
                "user": conversation_id,
                "stream": False,
            },
            timeout=SECRETARY_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        return False, f"secretary request failed: {e}"

    if not r.ok:
        return False, f"secretary HTTP {r.status_code}: {(r.text or '')[:300]}"

    try:
        data = r.json()
    except ValueError:
        return False, "secretary returned non-JSON response"

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return False, f"secretary response missing content: {json.dumps(data)[:300]}"

    if not content or not str(content).strip():
        return False, "secretary returned empty content"

    return True, str(content)


# ---------------------------------------------------------------------------
# One tick
# ---------------------------------------------------------------------------

def tick() -> int:
    """One drain pass. Returns how many letters were sent to the CEO (0 on
    an empty box, a failure, or a lock miss)."""
    fd = _try_lock(LOCK_PATH)
    if fd is None:
        _log().info("previous tick still in flight -- skipping")
        return 0
    try:
        return _tick_locked()
    finally:
        _unlock(fd)


def _tick_locked() -> int:
    box = _box()
    pending = _peek_with_paths()
    if not pending:
        return 0

    batch = pending[:MAX_BATCH]
    held = len(pending) - len(batch)
    batch_paths = [p for p, _ in batch]
    batch_letters = [letter for _, letter in batch]

    prompt = _build_digest_prompt(batch_letters, held)

    ok, result = _invoke_secretary(prompt)
    if not ok:
        _log().error("secretary invocation failed: %s", result)
        _record_failure(batch_paths, box, FAILCOUNT_PATH, MAX_RETRIES)
        return 0

    sent = telegram_out.send_to_ceo(result)
    if not sent["ok"]:
        _log().error("telegram send failed, letters kept: %s", sent["reason"])
        _record_failure(batch_paths, box, FAILCOUNT_PATH, MAX_RETRIES)
        return 0

    # Delete only the letters actually consumed -- one that arrived mid-cycle
    # (or past MAX_BATCH) survives untouched to the next tick.
    for p in batch_paths:
        p.unlink(missing_ok=True)
    _clear_failures(batch_paths, FAILCOUNT_PATH)
    _log().info("digest sent: %s letter(s), %s held over", len(batch_paths), held)
    return len(batch_paths)


def main() -> None:
    once = "--once" in sys.argv
    _log().info("secretary_waker starting (poll=%ss max_batch=%s once=%s)",
                POLL_SECONDS, MAX_BATCH, once)
    while True:
        try:
            tick()
        except Exception as e:  # one bad tick must never kill the loop
            _log().error("tick failed: %s", e)
        if once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
