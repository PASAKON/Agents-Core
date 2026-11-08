#!/usr/bin/env python3
"""CardRun requester & automatic session wake for Antigravity (AGY) CLI / IDE.

Bridges MoonieX Run Inbox (`tools/ask_run.py`, `terminal.mooniex.com/run`) and
`tools/mail_wake.py` to standalone, interactive, and `/takeover` AGY sessions across
Contabo, Mac, and Winbox — with zero Claude Code ($20 Pro) usage.

How it works:
1. Raising a card from AGY (`create` or `ask`):
   - Auto-detects the active AGY `--conversation <uuid>` (from `--conversation`,
     `AGY_CONVERSATION_ID`, or the newest `<uuid>` directory in
     `~/.gemini/antigravity/brain/`).
   - Auto-fills `--role` (default `cto` or `CXO_ROLE`/`AGY_ROLE`) and
     `--session <role>-<sid>` (default `<role>-agy-<uuid[:8]>`), so `ask_run.py`
     works out of the box without `cxo-claude.sh` env vars.
   - Registers `state/agy-sessions/<box>.json` binding the mailbox `<box>` to
     the AGY `conversation_id`, working directory, model, and mode.
   - Submits the Command Card (`RUN-...`) or Question Card (`Q-...` / `QG-...`)
     through `tools/ask_run.py`.
2. Automatic session wake when the CEO taps Run / Deny / Answer on `/run`:
   - On Contabo (the Hub): Console's `notify.js` drops the result letter into
     `state/inbox/<box>/` and runs `python -m tools.mail_wake <box>`.
     `mail_wake.py` detects `state/agy-sessions/<box>.json` and spawns a
     detached runner (`--run-agy`) that drains the letter (with full CEO notes
     and command output tail) and resumes the exact AGY conversation via
     `agy -p "<result>" --conversation <uuid>` with automatic model quota
     fallback (`claude-opus-5-5-high` -> `gemini-4-argon-high` ->
     `claude-sonnet-5-5-high` -> `gemini-3.8-flash-high`).
   - On Mac or Winbox (Peer Hosts): `create` and `ask` automatically spawn a
     detached background watcher (`watch <card_id> --box <box>`) that polls
     the hub (`ask_run.wait_result`), writes the verified result letter into the
     local `state/inbox/<box>/`, and wakes the local AGY conversation the moment
     the card finishes.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
from tools import ask_run, ph_brain  # noqa: E402

AGY_SESSIONS_DIR = ROOT / "state" / "agy-sessions"
DEFAULT_BRAIN_DIR = Path.home() / ".gemini" / "antigravity" / "brain"
DEFAULT_CLI_BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"
DEFAULT_CLI_CONV_DIR = Path.home() / ".gemini" / "antigravity-cli" / "conversations"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_BOX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CARD_ID_RE = re.compile(r"^(?:RUN-[A-Za-z0-9][A-Za-z0-9-]{3,63}|Q(?:G)?-[0-9]{8}-[0-9]{4}-[0-9a-f]{4})$")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

DEFAULT_MODEL = ph_brain.PRIMARY_MODEL
DEFAULT_MODE = "accept-edits"
WAKE_TIMEOUT_S = 300
NOTE_MAX = 2000
TAIL_MAX_CHARS = 3000


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_host(env: dict | None = None) -> str:
    """Return canonical host id (`contabo`, `mac`, `winbox`)."""
    env = os.environ if env is None else env
    h = (env.get("ORG_HOST") or "").strip().lower()
    if h in ("contabo", "mac", "winbox"):
        return h
    if sys.platform == "darwin":
        return "mac"
    if sys.platform == "win32":
        return "winbox"
    return "contabo"


def detect_conversation_id(
    explicit: str | None = None,
    *,
    env: dict | None = None,
    brain_dir: Path | None = None,
) -> str | None:
    """Resolve active AGY conversation UUID from flag, env, or ~/.gemini/antigravity(-cli)/brain/."""
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ if env is None else env
    for key in ("AGY_CONVERSATION_ID", "ANTIGRAVITY_CONVERSATION_ID"):
        val = (env.get(key) or "").strip()
        if val:
            return val
    raw_meta = (env.get("ANTIGRAVITY_SOURCE_METADATA") or "").strip()
    if raw_meta:
        try:
            meta = json.loads(raw_meta)
            meta_cid = ((meta.get("tool") or {}).get("conversationId") or "").strip()
            if meta_cid:
                return meta_cid
        except (ValueError, AttributeError):
            pass

    search_dirs: list[Path] = []
    if brain_dir is not None:
        search_dirs.append(Path(brain_dir))
    else:
        app_data = (env.get("ANTIGRAVITY_APP_DATA_DIR") or "").strip()
        if app_data:
            search_dirs.append(Path(app_data) / "brain")
        search_dirs.extend([DEFAULT_BRAIN_DIR, DEFAULT_CLI_BRAIN_DIR, DEFAULT_CLI_CONV_DIR])

    candidates: list[tuple[float, str]] = []
    for base in search_dirs:
        if not base.is_dir():
            continue
        try:
            for child in base.iterdir():
                if child.is_symlink():
                    continue
                if child.is_dir() and _UUID_RE.fullmatch(child.name):
                    try:
                        candidates.append((child.stat().st_mtime, child.name))
                    except OSError:
                        continue
                elif child.is_file() and child.suffix == ".pb" and _UUID_RE.fullmatch(child.stem):
                    try:
                        candidates.append((child.stat().st_mtime, child.stem))
                    except OSError:
                        continue
        except OSError:
            continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def resolve_identity(
    session: str | None = None,
    role: str | None = None,
    conversation_id: str | None = None,
    *,
    env: dict | None = None,
    brain_dir: Path | None = None,
    cwd: Path | None = None,
) -> tuple[str, str, str, str | None]:
    """Return `(box, role, session_id, conversation_id)` for an AGY session."""
    env = os.environ if env is None else env
    conv_id = detect_conversation_id(conversation_id, env=env, brain_dir=brain_dir)

    # Worker guard: if running as a delegated worker (env WORKER_TASK_ID or inside a worker worktree),
    # resolve as the worker role + task id so ask_run's role gates enforce worker boundaries.
    worker_task = (env.get("WORKER_TASK_ID") or "").strip()
    worker_role = (env.get("WORKER_ROLE") or "").strip().lower()
    if not worker_task and (cwd is not None or (env is os.environ and "PYTEST_CURRENT_TEST" not in env)):
        wt = ask_run._detect_worktree_worker(cwd)
        if wt:
            worker_role, worker_task = wt[0], wt[1]
    if worker_task and not session and not role:
        w_role = worker_role or "dev"
        return f"{w_role}-{worker_task}", w_role, worker_task, conv_id

    explicit_session = (session or env.get("ORG_SESSION_ID") or env.get("ORG_SESSION_NAME") or "").strip()
    explicit_role = (role or env.get("CXO_ROLE") or env.get("ORG_ROLE") or env.get("AGY_ROLE") or "").strip().lower()

    if explicit_session:
        part_role, sep, part_sid = explicit_session.partition("-")
        if sep and part_role and part_sid:
            resolved_role = explicit_role or part_role.lower()
            if explicit_session.startswith(resolved_role + "-"):
                box = explicit_session
                sid = explicit_session[len(resolved_role) + 1 :]
            else:
                box = f"{resolved_role}-{explicit_session}"
                sid = explicit_session
            return box, resolved_role, sid, conv_id
        resolved_role = explicit_role or "cto"
        sid = explicit_session
        return f"{resolved_role}-{sid}", resolved_role, sid, conv_id

    resolved_role = explicit_role or "cto"
    env_sid = (env.get("CXO_SESSION_ID") or env.get("CTO_SESSION_ID") or "").strip()
    if env_sid:
        sid = env_sid[len(resolved_role) + 1 :] if env_sid.startswith(resolved_role + "-") else env_sid
    elif conv_id:
        short = re.sub(r"[^A-Za-z0-9._-]", "", conv_id[:8]) or "session"
        sid = f"agy-{short}"
    else:
        sid = "agy-main"
    box = f"{resolved_role}-{sid}"
    return box, resolved_role, sid, conv_id


def _validate_box(box: str) -> str:
    clean = (box or "").strip()
    if not _BOX_RE.fullmatch(clean):
        raise ValueError(f"invalid mailbox name {box!r}")
    return clean


def session_path(box: str, sessions_dir: Path | None = None) -> Path:
    clean = _validate_box(box)
    base = Path(sessions_dir or AGY_SESSIONS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{clean}.json"


def load_session(box: str, sessions_dir: Path | None = None) -> dict[str, Any] | None:
    """Read `state/agy-sessions/<box>.json` safely (refuses symlinks)."""
    try:
        clean = _validate_box(box)
    except ValueError:
        return None
    base = Path(sessions_dir or AGY_SESSIONS_DIR)
    if base.is_symlink():
        return None
    path = base / f"{clean}.json"
    if path.is_symlink() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("parked"):
        return None
    conv_id = str(data.get("conversation_id") or "").strip()
    if not conv_id:
        return None
    return data


def register_session(
    *,
    box: str | None = None,
    role: str | None = None,
    conversation_id: str | None = None,
    model: str | None = None,
    mode: str | None = None,
    cwd: str | Path | None = None,
    add_dirs: list[str] | None = None,
    card_id: str | None = None,
    sessions_dir: Path | None = None,
    env: dict | None = None,
    brain_dir: Path | None = None,
) -> dict[str, Any]:
    """Create or update `state/agy-sessions/<box>.json`."""
    resolved_box, resolved_role, sid, conv_id = resolve_identity(
        session=box,
        role=role,
        conversation_id=conversation_id,
        env=env,
        brain_dir=brain_dir,
    )
    existing = load_session(resolved_box, sessions_dir=sessions_dir) or {}
    final_conv = conv_id or existing.get("conversation_id")
    if not final_conv:
        raise ValueError(
            f"cannot determine AGY conversation_id for {resolved_box}; "
            "pass --conversation <uuid> or set AGY_CONVERSATION_ID"
        )
    work_dir = str(Path(cwd or existing.get("cwd") or Path.cwd()).resolve())
    dirs = list(add_dirs or existing.get("add_dirs") or [work_dir, str(ROOT)])
    dedup_dirs: list[str] = []
    for d in dirs:
        if d and d not in dedup_dirs:
            dedup_dirs.append(d)

    cards = list(existing.get("cards") or [])
    if card_id and card_id not in cards:
        cards.append(card_id)
        cards = cards[-50:]

    record: dict[str, Any] = {
        **existing,
        "box": resolved_box,
        "role": resolved_role,
        "session_id": sid,
        "conversation_id": final_conv,
        "host": detect_host(env),
        "cwd": work_dir,
        "model": model or existing.get("model") or DEFAULT_MODEL,
        "mode": mode or existing.get("mode") or DEFAULT_MODE,
        "add_dirs": dedup_dirs,
        "cards": cards,
        "parked": False,
        "created_at": existing.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
    }

    path = session_path(resolved_box, sessions_dir=sessions_dir)
    if path.is_symlink():
        raise OSError(f"refusing symlinked session file {path}")
    tmp = path.with_suffix(f".json.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | _NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    except Exception:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    tmp.replace(path)
    return record


def extract_letter_extras(letter: dict[str, Any], shown_body: str = "") -> str:
    """Return full CEO notes and command output tail not already shown in `shown_body`."""
    lines: list[str] = []
    frm = letter.get("from")
    is_run_inbox = isinstance(frm, dict) and frm.get("role") == "run-inbox"

    if is_run_inbox:
        notes: list[tuple[str, str, str]] = []
        ans = letter.get("answer")
        if isinstance(ans, dict) and isinstance(ans.get("text"), str) and ans["text"].strip():
            notes.append(("note", str(letter.get("id") or "?"), ans["text"]))
        questions = letter.get("questions")
        if isinstance(questions, list):
            for q in questions:
                if isinstance(q, dict):
                    q_ans = q.get("answer")
                    if isinstance(q_ans, dict) and isinstance(q_ans.get("text"), str) and q_ans["text"].strip():
                        notes.append(("note", str(q.get("id") or "?"), q_ans["text"]))
        if isinstance(letter.get("question"), str) and letter["question"].strip():
            # For an ask-back letter, `question` is the CEO's question; for a Q- card, `body` already holds it
            if letter.get("kind") == "ask_back" or " asks on " in shown_body:
                notes.append(("question", str(letter.get("id") or "?"), letter["question"]))

        for what, card, text in notes:
            if text in shown_body:
                continue
            clean = text[:NOTE_MAX].encode("utf-8", "replace").decode("utf-8")
            lines.append(f"    > CEO {what} in full ({card}):")
            lines.extend(f"    > {ln}" for ln in clean.splitlines())
            if len(text) > NOTE_MAX:
                lines.append(f"    > ...[cut at {NOTE_MAX} of {len(text)} chars]")

    tail = letter.get("tail") or letter.get("output_tail")
    if isinstance(tail, str) and tail.strip() and tail.strip() not in shown_body:
        clean_tail = tail.strip()
        if len(clean_tail) > TAIL_MAX_CHARS:
            clean_tail = "...[truncated]\n" + clean_tail[-TAIL_MAX_CHARS:]
        lines.append("    --- command output tail ---")
        lines.extend(f"    {ln}" for ln in clean_tail.splitlines())

    return ("\n" + "\n".join(lines)) if lines else ""


def format_wake_prompt(box: str, letters: list[dict[str, Any]]) -> str:
    """Build the prompt sent to `agy --conversation <uuid>` when woken by mailbox letters."""
    blocks: list[str] = []
    for lt in letters:
        frm = lt.get("from") if isinstance(lt.get("from"), dict) else {}
        head = " ".join(
            f"[{lt.get('id', '?')}] {str(lt.get('kind') or 'message').upper()} from "
            f"{frm.get('role', '?')} {frm.get('session_id', '?')} · {lt.get('sent_at', '')}".split()
        )
        body = str(lt.get("body") or "")
        extra = extract_letter_extras(lt, body)
        blocks.append(f"{head}\n{body}{extra}")

    joined = "\n\n".join(blocks)
    if len(joined) > 6000:
        note = f"\n…[cut at 6000 chars; full letters are in state/inbox/{box}/read/]"
        joined = joined[: 6000 - len(note)] + note

    return (
        f"[RUN-INBOX / MAILBOX WAKE for AGY session `{box}`]\n"
        f"{len(letters)} new letter(s) arrived and were drained from `state/inbox/{box}/`:\n\n"
        f"{joined}\n\n"
        f"Continue the task in this session based on the CEO's response / command output above."
    )


def _call_agy_cli(
    prompt: str,
    *,
    conversation_id: str,
    model: str,
    mode: str = DEFAULT_MODE,
    cwd: str | Path = ROOT,
    add_dirs: list[str] | None = None,
    timeout_s: int = WAKE_TIMEOUT_S,
    agy_bin: str | None = None,
) -> dict[str, Any]:
    """Run one `agy -p <prompt> --conversation <uuid>` invocation and parse its output."""
    binary = agy_bin or ph_brain.resolve_agy_bin()
    cmd = [
        binary,
        "-p",
        prompt,
        "--conversation",
        conversation_id,
        "--model",
        model,
        "--mode",
        mode,
        "--output-format",
        "json",
    ]
    for d in add_dirs or [str(cwd), str(ROOT)]:
        if d and Path(d).exists():
            cmd.extend(["--add-dir", str(d)])

    run_cwd = str(cwd) if cwd and Path(cwd).is_dir() else str(ROOT)
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=run_cwd,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": 124,
            "model": model,
            "conversation_id": conversation_id,
            "response": f"agy timed out after {timeout_s}s",
            "limit_hit": None,
            "timed_out": True,
        }
    except OSError as e:
        return {
            "ok": False,
            "returncode": 127,
            "model": model,
            "conversation_id": conversation_id,
            "response": f"cannot start agy: {e}",
            "limit_hit": None,
        }

    parsed = ph_brain._parse_agy_json(proc.stdout)
    combined = "\n".join(
        p for p in (proc.stdout, proc.stderr, (parsed or {}).get("response") or "") if p
    )
    limit_hit = ph_brain.is_quota_limit_text(combined)
    conv_out = (parsed or {}).get("conversation_id") or conversation_id
    response = (parsed or {}).get("response")
    if response is None:
        response = (proc.stdout or proc.stderr or "").strip()

    ok = (
        proc.returncode == 0
        and limit_hit is None
        and bool(response)
        and "jetski: no output produced" not in combined
    )
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "model": model,
        "conversation_id": conv_out,
        "response": response,
        "limit_hit": limit_hit,
    }


def wake_session(
    box: str,
    *,
    letters: list[dict[str, Any]] | None = None,
    sessions_dir: Path | None = None,
    inbox_root: Path | None = None,
    snapshot_path: Path | None = None,
    agy_bin: str | None = None,
    timeout_s: int = WAKE_TIMEOUT_S,
) -> dict[str, Any]:
    """Drain `state/inbox/<box>/` (if `letters` not passed) and wake the registered AGY session."""
    rec = load_session(box, sessions_dir=sessions_dir)
    if rec is None:
        return {"ok": False, "box": box, "reason": "no-agy-session"}

    role, _, sid = box.partition("-")
    if not sid:
        return {"ok": False, "box": box, "reason": "invalid-box"}

    if letters is None:
        letters = mailbox._drain_envelope(role, sid, inbox_root)
    if not letters:
        return {"ok": True, "box": box, "reason": "idle", "woke": False}

    prompt = format_wake_prompt(box, letters)
    models = ph_brain.select_model_chain(
        rec.get("model") or DEFAULT_MODEL,
        snapshot_path=snapshot_path,
    )

    last_res: dict[str, Any] = {}
    for model in models:
        res = _call_agy_cli(
            prompt,
            conversation_id=rec["conversation_id"],
            model=model,
            mode=rec.get("mode") or DEFAULT_MODE,
            cwd=rec.get("cwd") or ROOT,
            add_dirs=rec.get("add_dirs"),
            timeout_s=timeout_s,
            agy_bin=agy_bin,
        )
        last_res = res
        if res["ok"]:
            rec["active_model"] = model
            rec["last_wake_at"] = _now_iso()
            rec["last_wake_ok"] = True
            rec["last_response_preview"] = (res.get("response") or "")[:500]
            try:
                path = session_path(box, sessions_dir=sessions_dir)
                path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            except OSError:
                pass
            return {
                "ok": True,
                "woke": True,
                "box": box,
                "reason": "ok",
                "model": model,
                "conversation_id": res.get("conversation_id") or rec["conversation_id"],
                "response": res.get("response") or "",
            }
        if not res.get("limit_hit"):
            break

    # Requeue so unread letters are never lost if AGY failed to run
    mailbox.send(
        role,
        sid,
        "[agy-wake fallback: AGY session could not take the turn; letters restored]\n" + prompt,
        "hub",
        "agy-wake",
        root=inbox_root,
    )
    return {
        "ok": False,
        "woke": False,
        "box": box,
        "reason": "failed",
        "error": last_res.get("response") or "agy invocation failed",
    }


def record_to_letter(card_id: str, rec: dict[str, Any], box: str, *, inbox_root: Path | None = None) -> Path | None:
    """Write a hub card result record (`RUN-...`, `Q-...`, `QG-...`) into local `state/inbox/<box>/`
    if no unread letter for `card_id` is already waiting there."""
    role, _, sid = box.partition("-")
    if not role or not sid:
        return None
    root = Path(inbox_root or mailbox.INBOX_ROOT)
    box_dir = root / box
    if box_dir.is_dir():
        for f in box_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("id") == card_id or card_id in str(data.get("body") or ""):
                    return f
            except (OSError, ValueError):
                continue

    status = str(rec.get("status") or "done")
    if card_id.startswith("Q-"):
        ans = rec.get("answer") if isinstance(rec.get("answer"), dict) else {}
        label = ans.get("label") or f"option {(ans.get('choice') or 0) + 1}"
        note = ans.get("text") or ""
        body = f"{card_id} {status}: {label}" + (f" — \"{note[:120]}\"" if note else "")
        extra = {"kind": "question", "question": rec.get("question"), "answer": ans}
    elif card_id.startswith("QG-"):
        qs = rec.get("questions") if isinstance(rec.get("questions"), list) else []
        answered = sum(1 for q in qs if isinstance(q, dict) and q.get("status") == "answered")
        body = f"{card_id} {status}: {answered}/{len(qs)} answered"
        extra = {"kind": "question_batch", "questions": qs}
    else:
        exit_code = rec.get("exit_code")
        tail = rec.get("output_tail") or ""
        code_str = f" (exit {exit_code})" if exit_code is not None else ""
        body = f"{card_id} {status}{code_str}: {rec.get('why') or rec.get('command') or ''}".strip()
        extra = {"kind": "result", "status": status, "exit_code": exit_code, "tail": tail}

    letter_path = mailbox.send(role, sid, body, "run-inbox", "hub", root=root)
    try:
        payload = json.loads(letter_path.read_text(encoding="utf-8"))
        payload.update(extra)
        payload["card_id"] = card_id
        letter_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError):
        pass
    return letter_path


def watch_card(
    card_id: str,
    box: str,
    *,
    interval_s: float = 5.0,
    max_wait_s: float = 86400.0,
    sessions_dir: Path | None = None,
    inbox_root: Path | None = None,
    agy_bin: str | None = None,
) -> dict[str, Any]:
    """Poll the hub until `card_id` reaches a terminal state, then deliver & wake `box`."""
    deadline = time.monotonic() + max(1.0, float(max_wait_s))
    last_rec: dict[str, Any] = {"id": card_id}
    while time.monotonic() < deadline:
        left = max(1.0, deadline - time.monotonic())
        chunk = min(600.0, left)
        try:
            res = ask_run.wait_result(card_id, max_wait_s=chunk, interval_s=interval_s)
        except Exception as e:
            return {"ok": False, "card_id": card_id, "box": box, "reason": f"wait_error: {e}"}
        last_rec = res
        if res.get("terminal"):
            record_to_letter(card_id, res, box, inbox_root=inbox_root)
            wake_res = wake_session(
                box,
                sessions_dir=sessions_dir,
                inbox_root=inbox_root,
                agy_bin=agy_bin,
            )
            return {
                "ok": bool(wake_res.get("ok")),
                "card_id": card_id,
                "box": box,
                "status": res.get("status"),
                "wake": wake_res,
            }
    return {"ok": False, "card_id": card_id, "box": box, "reason": "timeout", "last": last_rec}


def spawn_card_watcher(
    card_id: str,
    box: str,
    *,
    sessions_dir: Path | None = None,
) -> int | None:
    """Start a detached background watcher (`watch <card_id> --box <box>`) for peer hosts."""
    base = Path(sessions_dir or AGY_SESSIONS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / f"watch-{box}-{card_id}.log"
    if log_path.is_symlink():
        raise OSError(f"refusing symlinked watcher log {log_path}")
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | _NOFOLLOW, 0o600)
    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "watch",
                card_id,
                "--box",
                box,
            ],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=fd,
            stderr=fd,
            start_new_session=True,
            close_fds=True,
        )
        return proc.pid
    finally:
        os.close(fd)


def _extract_flag(argv: list[str], flag: str) -> tuple[str | None, list[str]]:
    """Extract `--flag val` or `--flag=val` from `argv`, returning `(value, remaining_argv)`."""
    val: str | None = None
    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--":
            out.extend(argv[i:])
            break
        if tok == flag and i + 1 < len(argv):
            val = argv[i + 1]
            i += 2
            continue
        if tok.startswith(flag + "="):
            val = tok.split("=", 1)[1]
            i += 1
            continue
        out.append(tok)
        i += 1
    return val, out


def _extract_bool_flag(argv: list[str], flag: str) -> tuple[bool, list[str]]:
    found = False
    out: list[str] = []
    for i, tok in enumerate(argv):
        if tok == "--":
            out.extend(argv[i:])
            break
        if tok == flag:
            found = True
            continue
        out.append(tok)
    return found, out


def _has_flag(argv: list[str], flag: str) -> bool:
    for tok in argv:
        if tok == "--":
            break
        if tok == flag or tok.startswith(flag + "="):
            return True
    return False


def _inject_before_double_dash(argv: list[str], extra: list[str]) -> list[str]:
    if "--" in argv:
        idx = argv.index("--")
        return argv[:idx] + extra + argv[idx:]
    return argv + extra


def _parse_created_card_id(stdout_text: str) -> str | None:
    """Extract `RUN-...`, `Q-...`, or `QG-...` from `ask_run.py` stdout."""
    text = (stdout_text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            cid = obj.get("id") or obj.get("group_id")
            if isinstance(cid, str) and _CARD_ID_RE.fullmatch(cid):
                return cid
    except ValueError:
        pass
    for line in text.splitlines():
        token = line.strip().split()[0] if line.strip() else ""
        if _CARD_ID_RE.fullmatch(token):
            return token
    return None


def run_passthrough(
    verb: str,
    raw_args: list[str],
    *,
    sessions_dir: Path | None = None,
    env: dict | None = None,
    brain_dir: Path | None = None,
) -> int:
    """Run `ask_run.py create|ask` with AGY identity injection, session registration & watcher."""
    conv_flag, args = _extract_flag(raw_args, "--conversation")
    model_flag, args = _extract_flag(args, "--agy-model")
    mode_flag, args = _extract_flag(args, "--agy-mode")
    force_watch, args = _extract_bool_flag(args, "--watch")
    no_watch, args = _extract_bool_flag(args, "--no-watch")

    # Peek at --session and --role if caller passed them
    peek_session, _ = _extract_flag(args, "--session")
    peek_role, _ = _extract_flag(args, "--role")
    is_dry_run = _has_flag(args, "--dry-run")

    box, role, _sid, conv_id = resolve_identity(
        session=peek_session,
        role=peek_role,
        conversation_id=conv_flag,
        env=env,
        brain_dir=brain_dir,
    )

    injected: list[str] = []
    if not _has_flag(args, "--role"):
        injected.extend(["--role", role])
    if not _has_flag(args, "--session"):
        injected.extend(["--session", box])

    final_args = _inject_before_double_dash(args, injected)

    if not is_dry_run and conv_id:
        register_session(
            box=box,
            role=role,
            conversation_id=conv_id,
            model=model_flag,
            mode=mode_flag,
            sessions_dir=sessions_dir,
            env=env,
            brain_dir=brain_dir,
        )

    buf_out = io.StringIO()
    prev_flag = os.environ.get("_AGY_PASSTHROUGH_ACTIVE")
    os.environ["_AGY_PASSTHROUGH_ACTIVE"] = "1"
    try:
        with contextlib.redirect_stdout(buf_out):
            rc = ask_run.main([verb, *final_args])
    finally:
        if prev_flag is None:
            os.environ.pop("_AGY_PASSTHROUGH_ACTIVE", None)
        else:
            os.environ["_AGY_PASSTHROUGH_ACTIVE"] = prev_flag

    out_text = buf_out.getvalue()
    if out_text:
        sys.stdout.write(out_text)
        sys.stdout.flush()

    if rc == 0 and not is_dry_run:
        card_id = _parse_created_card_id(out_text)
        if card_id and conv_id:
            rec = register_session(
                box=box,
                role=role,
                conversation_id=conv_id,
                model=model_flag,
                mode=mode_flag,
                card_id=card_id,
                sessions_dir=sessions_dir,
                env=env,
                brain_dir=brain_dir,
            )
            host = rec.get("host") or detect_host(env)
            should_watch = (force_watch or host != "contabo") and not no_watch
            if should_watch:
                pid = spawn_card_watcher(card_id, box, sessions_dir=sessions_dir)
                print(
                    f"[agy_card_run] Registered {box} -> AGY {conv_id} (watcher pid={pid} for {card_id})",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[agy_card_run] Registered {box} -> AGY {conv_id} (hub mail_wake active for {card_id})",
                    file=sys.stderr,
                )
    return rc


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        print(
            "\nSubcommands:\n"
            "  create [ask_run create flags...] [--conversation UUID] [--watch|--no-watch]\n"
            "  ask    [ask_run ask flags...]    [--conversation UUID] [--watch|--no-watch]\n"
            "  register [--session BOX] [--role ROLE] [--conversation UUID] [--model MODEL]\n"
            "  wake   <box> [--timeout SECONDS]\n"
            "  watch  <card_id> --box <box> [--interval SECONDS] [--max-wait SECONDS]\n"
            "  status [--json]\n"
            "  wait | list | cancel | tail  (passed through to tools/ask_run.py)"
        )
        return 0

    verb = argv[0]
    rest = argv[1:]

    if verb in ("create", "ask"):
        return run_passthrough(verb, rest)

    if verb in ("wait", "list", "cancel", "tail"):
        return ask_run.main([verb, *rest])

    if verb == "register":
        p = argparse.ArgumentParser(prog="tools/agy_card_run.py register")
        p.add_argument("--session", "--box", dest="box", help="mailbox name <role>-<id>")
        p.add_argument("--role", help="C-level or PH role (default: cto)")
        p.add_argument("--conversation", help="AGY conversation UUID (default: auto-detect)")
        p.add_argument("--model", default=None, help=f"preferred AGY model (default: {DEFAULT_MODEL})")
        p.add_argument("--mode", default=None, help=f"AGY mode (default: {DEFAULT_MODE})")
        p.add_argument("--cwd", default=None, help="working directory for wake runs")
        p.add_argument("--json", action="store_true")
        args = p.parse_args(rest)
        try:
            rec = register_session(
                box=args.box,
                role=args.role,
                conversation_id=args.conversation,
                model=args.model,
                mode=args.mode,
                cwd=args.cwd,
            )
        except Exception as e:
            print(f"agy_card_run: {e}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(rec, indent=2, ensure_ascii=False))
        else:
            print(f"Registered {rec['box']} -> conversation {rec['conversation_id']} ({rec['model']} on {rec['host']})")
        return 0

    if verb == "wake":
        p = argparse.ArgumentParser(prog="tools/agy_card_run.py wake")
        p.add_argument("box", help="mailbox name <role>-<id>")
        p.add_argument("--timeout", type=int, default=WAKE_TIMEOUT_S)
        p.add_argument("--json", action="store_true")
        args = p.parse_args(rest)
        res = wake_session(args.box, timeout_s=args.timeout)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"wake {args.box}: {res.get('reason')} (woke={res.get('woke')})")
        return 0 if res.get("ok") else 1

    if verb == "watch":
        p = argparse.ArgumentParser(prog="tools/agy_card_run.py watch")
        p.add_argument("card_id", help="RUN-... | Q-... | QG-...")
        p.add_argument("--box", required=True, help="mailbox name <role>-<id>")
        p.add_argument("--interval", type=float, default=5.0)
        p.add_argument("--max-wait", type=float, default=86400.0)
        args = p.parse_args(rest)
        res = watch_card(args.card_id, args.box, interval_s=args.interval, max_wait_s=args.max_wait)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if verb == "status":
        p = argparse.ArgumentParser(prog="tools/agy_card_run.py status")
        p.add_argument("--json", action="store_true")
        args = p.parse_args(rest)
        sessions: list[dict[str, Any]] = []
        if AGY_SESSIONS_DIR.is_dir():
            for f in sorted(AGY_SESSIONS_DIR.glob("*.json")):
                rec = load_session(f.stem)
                if rec:
                    sessions.append(rec)
        if args.json:
            print(json.dumps(sessions, indent=2, ensure_ascii=False))
        elif not sessions:
            print("(no registered AGY sessions)")
        else:
            for s in sessions:
                print(
                    f"{s['box']:<22} conv={s['conversation_id']}  model={s.get('model')}  "
                    f"host={s.get('host')}  cards={len(s.get('cards') or [])}"
                )
        return 0

    print(f"agy_card_run: unknown verb {verb!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
