#!/usr/bin/env python3
"""Cross-host Claude <-> Antigravity (AGY CLI & Desktop App) messaging and discovery.

CEO 19 Nov: Claude sessions and AGY sessions (AGY CLI on any host, and the AGY
desktop App on the Mac) must message each other like Claude messages a DEV
worker today. Which session gets the message depends on the topic.

Reuses (does not duplicate):
- `tools/agy_card_run.py`: registers `state/agy-sessions/<box>.json`, resolves
  AGY identity, and wakes via `agentapi send-message` or `agy -p --conversation <uuid>`.
- `tools/mail_wake.py`: wakes local Claude/PH/AGY boxes (`mail_wake.wake`).
- `tools/agy_takeover.py`: cross-host SSH probe pattern across `mac`, `contabo`, `winbox`.
- `lib/mailbox.py` & `lib/notify.py`: letter storage (`state/inbox/<box>/`) and
  CTO event logging (`state/logs/cto.log`).

Subcommands:
1. `list [--host all|mac|contabo|winbox] [--limit N] [--local] [--json]`
   Lists every AGY conversation across `mac`, `contabo`, and `winbox`:
   box, host, conversation uuid, cwd, last activity, title/first user line, App vs CLI.
2. `send <box|uuid> "<msg>" [--from <role>-<sid>] [--host <host>]`
   Writes the letter to `state/inbox/<box>/` (same letter shape as `send_to_cxo`)
   and resumes that conversation ON ITS OWN HOST (local when on the target host;
   `ssh mac` / `ssh winbox` / `ssh mooniex-vps` using the host map when remote)
   with `agy -p ... --conversation <uuid>`, detached, logged to the CTO event log.
   The prompt tells AGY who sent it and how to answer:
   `bash scripts/hub/org-python.sh tools/send_to_cxo.py <from> "<reply>"`
   (and cross-host `bash scripts/hub/org-python.sh tools/send_to_agy.py reply <from> "<reply>" --from <box>`).
3. `reply <to_box> "<reply>" [--from <agy_box>] [--host <host>]`
   AGY -> Claude reply route that works from an AGY conversation on every host
   (`contabo`, `mac`, `winbox`), resolving `<role>-<sid>` or `<role>`, delivering
   locally or over SSH to the Claude session's host, and waking the recipient pane.
4. `live-sessions [--all] [--id <sid>] [--json] [--local]`
   Used by `scripts/live-sessions.sh` to include AGY rows (`kind: "agy"`) so
   senders can see and address them alongside live Claude sessions.
"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import contextlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import mailbox, notify  # noqa: E402
from lib.config import display_for, is_c_level  # noqa: E402
from lib.roles import PH_ROLE, c_level_roles  # noqa: E402
from tools import agent_transport, agy_card_run, live_sessions, mail_wake, ph_brain, send_to_cxo  # noqa: E402

HOSTS: tuple[str, ...] = ("contabo", "mac", "winbox")

# Host map extending tools/agy_takeover.py so any host can reach the other two over SSH
# while executing locally when target_host == current_host().
HOST_MAP: dict[str, dict[str, str]] = {
    "contabo": {
        "ssh": "mooniex-vps",
        "python": "python3",
        "agents_root": "/opt/MoonieXHQ/Agents/Core",
        "agy_bin": "/root/.local/bin/agy",
    },
    "mac": {
        "ssh": "mac",
        "python": "python3",
        "agents_root": "/Users/gob/MoonieXHQ/Agents/Core",
        "agy_bin": "/Users/gob/.local/bin/agy",
    },
    "winbox": {
        "ssh": "winbox",
        "python": r"C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe",
        "agents_root": r"C:\Users\passg\mooniex\repo\MoonieX-Agents",
        "agy_bin": r"C:\Users\passg\AppData\Local\agy\bin\agy.exe",
    },
}

CTO_LOG_PATH: Path = ROOT / "state" / "logs" / "cto.log"
AGY_FOOTER = (
    'send (agy): bash scripts/hub/org-python.sh tools/send_to_agy.py send <box|uuid> "<msg>" '
    "[--from <role>-<sid>]"
)

_UUID_RE = agy_card_run._UUID_RE
_BOX_RE = agy_card_run._BOX_RE
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_WORKTREE_RE = re.compile(r"([A-Za-z0-9._-]+)__([A-Za-z0-9_]+)__(task-[0-9a-f]{8})")
_TASK_ID_RE = re.compile(r"\b(task-[0-9a-f]{8})\b")


class TargetNotFoundError(LookupError, ValueError):
    """Raised when no AGY conversation or box matches the target specifier."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current_host(env: dict[str, str] | None = None) -> str:
    """Return canonical host name (`contabo`, `mac`, `winbox`)."""
    env_map = os.environ if env is None else env
    explicit = (env_map.get("ORG_HOST") or "").strip().lower()
    if explicit in HOSTS:
        return explicit
    return agy_card_run.detect_host(env_map)


def _extract_first_user_line(raw_text: str) -> str:
    """Extract a clean one-line title / first user line from a transcript USER_INPUT step."""
    text = (raw_text or "").strip()
    if not text:
        return ""
    if "<USER_REQUEST>" in text:
        text = text.split("<USER_REQUEST>", 1)[1]
        if "</USER_REQUEST>" in text:
            text = text.split("</USER_REQUEST>", 1)[0]
        text = text.strip()

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""

    first = lines[0]
    if first.startswith("# Task task-"):
        desc = ""
        for idx, ln in enumerate(lines[1:], 1):
            if ln.lower().startswith("## description") and idx + 1 < len(lines):
                desc = lines[idx + 1]
                break
            if not ln.startswith(("#", "Project:", "Stack:", "Repo path", "Branch:", "Default branch")):
                desc = ln
                break
        combined = f"{first} — {desc}" if desc else first
        return " ".join(combined.split())[:140]

    if first.startswith(("[Project Head Identity:", "[RUN-INBOX / MAILBOX WAKE", "[MESSAGE for AGY session")):
        for marker in ("--- Task / Message ---", "--- คำสั่งปัจจุบัน ---"):
            if marker in text:
                after = text.split(marker, 1)[1].strip().splitlines()
                if after and after[0].strip():
                    return " ".join(f"{first} · {after[0].strip()}".split())[:140]
        if len(lines) > 1:
            return " ".join(f"{first} · {lines[1]}".split())[:140]

    return " ".join(first.split())[:140]


def _infer_cwd_from_text(text: str) -> str | None:
    """Infer working directory from transcript prompt or system metadata lines."""
    if not text:
        return None
    patterns = (
        r"Repo path[^:\n]*:\s*(/[^\s\n]+|[A-Za-z]:\\[^\s\n]+)",
        r"Command Working Directory:\s*(/[^\s\n]+|[A-Za-z]:\\[^\s\n]+)",
        r"Active Workspaces:\s*\n-\s*(/[^\s\n]+|[A-Za-z]:\\[^\s\n]+)",
        r"- \*\*Working Directory:\*\*\s*`([^`\n]+)`",
    )
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return None


def _extract_step_text(obj: dict[str, Any]) -> str:
    content = obj.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(obj.get("text"), str) and obj["text"].strip():
        return obj["text"]
    msg = obj.get("message")
    if isinstance(msg, dict):
        mc = msg.get("content")
        if isinstance(mc, str):
            return mc
        if isinstance(mc, list):
            parts = [
                str(it.get("text") or "")
                for it in mc
                if isinstance(it, dict) and it.get("type") == "text"
            ]
            return "\n".join(p for p in parts if p)
    return ""


def _parse_brain_dir(brain_path: Path) -> dict[str, Any]:
    """Read transcript and metadata from `<app_data>/brain/<uuid>`."""
    info: dict[str, Any] = {
        "title": "",
        "cwd": None,
        "last_ts": None,
        "mtime": 0.0,
    }
    try:
        info["mtime"] = brain_path.stat().st_mtime
    except OSError:
        pass

    candidates = (
        brain_path / ".system_generated" / "logs" / "transcript.jsonl",
        brain_path / ".system_generated" / "logs" / "transcript_full.jsonl",
        brain_path / "transcript.jsonl",
    )
    transcript_file: Path | None = None
    for cand in candidates:
        try:
            if cand.is_file() and not cand.is_symlink():
                transcript_file = cand
                info["mtime"] = max(info["mtime"], cand.stat().st_mtime)
                break
        except OSError:
            continue

    if transcript_file is not None:
        try:
            sz = transcript_file.stat().st_size
            with transcript_file.open("rb") as fh:
                head_bytes = fh.read(min(sz, 131072))
                tail_bytes = b""
                if sz > 131072:
                    fh.seek(max(0, sz - 65536))
                    fh.readline()
                    tail_bytes = fh.read()
            head_lines = [ln for ln in head_bytes.decode("utf-8", errors="replace").splitlines() if ln.strip()]
            tail_lines = [ln for ln in tail_bytes.decode("utf-8", errors="replace").splitlines() if ln.strip()]

            for ln in head_lines:
                try:
                    obj = json.loads(ln)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                if not info["cwd"] and isinstance(obj.get("cwd"), str) and obj["cwd"].strip():
                    info["cwd"] = obj["cwd"].strip()
                ts = obj.get("created_at") or obj.get("timestamp")
                if isinstance(ts, str) and ts.strip():
                    info["last_ts"] = ts.strip()

                step_text = _extract_step_text(obj)
                if not info["cwd"] and step_text:
                    info["cwd"] = _infer_cwd_from_text(step_text)

                step_type = str(obj.get("type") or "").upper()
                step_source = str(obj.get("source") or "").upper()
                msg_role = str((obj.get("message") or {}).get("role") or obj.get("role") or "").lower()
                is_user = (
                    step_type in ("USER_INPUT", "USER")
                    or step_source == "USER_EXPLICIT"
                    or msg_role == "user"
                )
                if is_user and not info["title"] and step_text:
                    info["title"] = _extract_first_user_line(step_text)

            for ln in tail_lines:
                try:
                    obj = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    ts = obj.get("created_at") or obj.get("timestamp")
                    if isinstance(ts, str) and ts.strip():
                        info["last_ts"] = ts.strip()
        except OSError:
            pass

    if not info["title"]:
        try:
            for md in sorted(brain_path.glob("*.md")):
                if md.is_file() and not md.is_symlink():
                    info["mtime"] = max(info["mtime"], md.stat().st_mtime)
                    first_ln = (md.read_text(encoding="utf-8", errors="replace").splitlines() or [""])[0].strip()
                    if first_ln:
                        info["title"] = first_ln.lstrip("# ").strip()[:140]
                        break
        except OSError:
            pass

    return info


def _infer_box_from_context(
    conv_id: str,
    cwd: str | None,
    title: str | None,
    sess_rec: dict[str, Any] | None,
    ph_rec: dict[str, Any] | None,
) -> tuple[str, str, str]:
    """Return `(box, role, session_id)` for a discovered AGY conversation."""
    if sess_rec and isinstance(sess_rec.get("box"), str) and sess_rec["box"].strip():
        box = sess_rec["box"].strip()
        role = str(sess_rec.get("role") or "").strip()
        sid = str(sess_rec.get("session_id") or "").strip()
        if not role or not sid:
            r_part, _, s_part = box.partition("-")
            role = role or r_part or "cto"
            sid = sid or s_part or f"agy-{conv_id[:8].lower()}"
        return box, role, sid

    if ph_rec and isinstance(ph_rec.get("ph_id"), str) and ph_rec["ph_id"].strip():
        ph_id = ph_rec["ph_id"].strip()
        return f"project_head-{ph_id}", "project_head", ph_id

    for text in (cwd or "", title or ""):
        m = _WORKTREE_RE.search(text)
        if m:
            w_role = m.group(2).lower()
            w_task = m.group(3).lower()
            return f"{w_role}-{w_task}", w_role, w_task
        m2 = _TASK_ID_RE.search(text)
        if m2:
            w_task = m2.group(1).lower()
            return f"dev-{w_task}", "dev", w_task

    short = conv_id[:8].lower()
    return f"cto-agy-{short}", "cto", f"agy-{short}"


def _detect_surface(
    found_in_app: bool,
    found_in_cli: bool,
    sess_rec: dict[str, Any] | None,
) -> str:
    """Return `'App'` (Mac Desktop App) or `'CLI'` (headless / terminal `agy`)."""
    if found_in_app:
        return "App"
    if sess_rec:
        if sess_rec.get("ls_address") or sess_rec.get("csrf_token"):
            if "Antigravity.app" in str(sess_rec.get("agentapi_exe") or ""):
                return "App"
            app_dir = str(sess_rec.get("app_data_dir") or "").rstrip("/\\")
            if app_dir.endswith("antigravity") and not app_dir.endswith("antigravity-cli"):
                return "App"
            if sess_rec.get("host") == "mac" and not found_in_cli:
                return "App"
        app_dir = str(sess_rec.get("app_data_dir") or "").rstrip("/\\")
        if app_dir.endswith("antigravity") and not app_dir.endswith("antigravity-cli"):
            return "App"
    return "CLI"


def scan_local_host(
    host: str | None = None,
    *,
    agents_root: Path | None = None,
    home_dir: Path | None = None,
    sessions_dir: Path | None = None,
    brains_dir: Path | None = None,
    app_brain_dir: Path | None = None,
    app_conv_dir: Path | None = None,
    cli_brain_dir: Path | None = None,
    cli_conv_dir: Path | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Discover all AGY conversations on the local filesystem."""
    resolved_host = (host or current_host()).lower().strip()
    root_dir = Path(agents_root or ROOT)
    home = Path(home_dir) if home_dir is not None else Path.home()
    sdir = Path(sessions_dir) if sessions_dir is not None else (root_dir / "state" / "agy-sessions")
    bdir = Path(brains_dir) if brains_dir is not None else (root_dir / "state" / "ph-brains")

    a_brain = Path(app_brain_dir) if app_brain_dir is not None else (home / ".gemini" / "antigravity" / "brain")
    a_conv = Path(app_conv_dir) if app_conv_dir is not None else (home / ".gemini" / "antigravity" / "conversations")
    c_brain = Path(cli_brain_dir) if cli_brain_dir is not None else (home / ".gemini" / "antigravity-cli" / "brain")
    c_conv = Path(cli_conv_dir) if cli_conv_dir is not None else (home / ".gemini" / "antigravity-cli" / "conversations")

    sessions_by_uuid: dict[str, dict[str, Any]] = {}
    if sdir.is_dir() and not sdir.is_symlink():
        for f in sorted(sdir.glob("*.json")):
            if f.is_symlink():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            cid = str(data.get("conversation_id") or "").strip().lower()
            if not _UUID_RE.fullmatch(cid):
                continue
            rec_host = str(data.get("host") or "").strip().lower()
            if rec_host and rec_host != resolved_host:
                continue
            prev = sessions_by_uuid.get(cid)
            if prev is None:
                sessions_by_uuid[cid] = data
            else:
                # Prefer unparked session record, then newer updated_at
                if prev.get("parked") and not data.get("parked"):
                    sessions_by_uuid[cid] = data
                elif bool(prev.get("parked")) == bool(data.get("parked")):
                    if str(data.get("updated_at") or "") >= str(prev.get("updated_at") or ""):
                        sessions_by_uuid[cid] = data

    ph_by_uuid: dict[str, dict[str, Any]] = {}
    if bdir.is_dir() and not bdir.is_symlink():
        for f in sorted(bdir.glob("*.json")):
            if f.is_symlink():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            cid = str(data.get("conversation_id") or "").strip().lower()
            if _UUID_RE.fullmatch(cid):
                ph_by_uuid[cid] = data

    discovered: dict[str, dict[str, Any]] = {}

    def _touch(cid: str) -> dict[str, Any]:
        cid = cid.lower()
        if cid not in discovered:
            discovered[cid] = {
                "found_in_app": False,
                "found_in_cli": False,
                "brain_dirs": [],
                "mtime": 0.0,
            }
        return discovered[cid]

    for base, is_app, kind in (
        (a_brain, True, "dir"),
        (a_conv, True, "pb"),
        (c_brain, False, "dir"),
        (c_conv, False, "pb"),
    ):
        if not base.is_dir() or base.is_symlink():
            continue
        try:
            for child in base.iterdir():
                if child.is_symlink():
                    continue
                if kind == "dir" and child.is_dir() and _UUID_RE.fullmatch(child.name):
                    entry = _touch(child.name)
                    if is_app:
                        entry["found_in_app"] = True
                    else:
                        entry["found_in_cli"] = True
                    entry["brain_dirs"].append(child)
                    with contextlib.suppress(OSError):
                        entry["mtime"] = max(entry["mtime"], child.stat().st_mtime)
                elif kind == "pb" and child.is_file() and child.suffix == ".pb" and _UUID_RE.fullmatch(child.stem):
                    entry = _touch(child.stem)
                    if is_app:
                        entry["found_in_app"] = True
                    else:
                        entry["found_in_cli"] = True
                    with contextlib.suppress(OSError):
                        entry["mtime"] = max(entry["mtime"], child.stat().st_mtime)
        except OSError:
            continue

    for cid in sessions_by_uuid:
        _touch(cid)
    for cid in ph_by_uuid:
        _touch(cid)

    results: list[dict[str, Any]] = []
    for cid, raw in discovered.items():
        sess_rec = sessions_by_uuid.get(cid)
        ph_rec = ph_by_uuid.get(cid)

        title = ""
        inferred_cwd: str | None = None
        last_ts: str | None = None
        mtime = float(raw["mtime"])

        for bpath in raw["brain_dirs"]:
            parsed = _parse_brain_dir(bpath)
            mtime = max(mtime, float(parsed.get("mtime") or 0.0))
            if not title and parsed.get("title"):
                title = str(parsed["title"])
            if not inferred_cwd and parsed.get("cwd"):
                inferred_cwd = str(parsed["cwd"])
            if parsed.get("last_ts"):
                last_ts = str(parsed["last_ts"])

        cwd = (
            (str(sess_rec["cwd"]).strip() if sess_rec and sess_rec.get("cwd") else None)
            or inferred_cwd
            or HOST_MAP.get(resolved_host, {}).get("agents_root")
            or str(root_dir)
        )

        if not title:
            if ph_rec:
                proj = ph_rec.get("project") or ph_rec.get("ph_id") or ""
                summ = str(ph_rec.get("last_summary") or "").replace("\n", " ").strip()
                title = f"PH#{ph_rec.get('ph_id')} ({proj}): {summ}"[:140] if summ else f"PH#{ph_rec.get('ph_id')} ({proj})"
            elif sess_rec and sess_rec.get("last_response_preview"):
                title = " ".join(str(sess_rec["last_response_preview"]).split())[:140]

        box, role, sid = _infer_box_from_context(cid, cwd, title, sess_rec, ph_rec)
        if not title:
            title = box

        surface = _detect_surface(
            bool(raw["found_in_app"]),
            bool(raw["found_in_cli"]),
            sess_rec,
        )

        if mtime > 0:
            mtime_iso = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            mtime_iso = ""
        rec_ts = (
            (sess_rec.get("last_wake_at") or sess_rec.get("updated_at") if sess_rec else None)
            or (ph_rec.get("updated_at") if ph_rec else None)
            or ""
        )
        candidates_ts = [t for t in (last_ts, mtime_iso, str(rec_ts)) if t]
        last_activity = max(candidates_ts) if candidates_ts else _now_iso()

        app_data_dir = (
            (sess_rec.get("app_data_dir") if sess_rec else None)
            or (str(a_brain.parent) if surface == "App" else str(c_brain.parent))
        )
        model = (
            (sess_rec.get("model") if sess_rec else None)
            or (ph_rec.get("active_model") if ph_rec else None)
            or agy_card_run.DEFAULT_MODEL
        )
        mode = (sess_rec.get("mode") if sess_rec else None) or agy_card_run.DEFAULT_MODE
        parked = bool(sess_rec.get("parked")) if sess_rec else False

        results.append(
            {
                "kind": "agy",
                "box": box,
                "host": resolved_host,
                "conversation_id": cid,
                "uuid": cid,
                "role": role,
                "session_id": sid,
                "cwd": cwd,
                "last_activity": last_activity,
                "title": title,
                "first_user_line": title,
                "app_vs_cli": surface,
                "surface": surface,
                "model": model,
                "mode": mode,
                "parked": parked,
                "app_data_dir": app_data_dir,
                "ls_address": sess_rec.get("ls_address") if sess_rec else None,
                "csrf_token": sess_rec.get("csrf_token") if sess_rec else None,
                "agentapi_exe": sess_rec.get("agentapi_exe") if sess_rec else None,
                "project_id": sess_rec.get("project_id") if sess_rec else None,
            }
        )

    results.sort(key=lambda r: (not bool(r.get("parked")), str(r.get("last_activity") or "")), reverse=True)
    return results[: max(1, int(limit))]


# Self-contained remote script executed over SSH on mac / contabo / winbox
# for `list` (discovery), `send` (mailbox write + detached `agy -p --conversation`),
# and `reply` (AGY -> Claude cross-host mailbox write + wake).
_REMOTE_AGY_PY = r'''
import base64, contextlib, json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

mode = sys.argv[1] if len(sys.argv) > 1 else "list"
home = Path.home()
candidates = [
    Path("/opt/MoonieXHQ/Agents/Core"),
    Path("/Users/gob/MoonieXHQ/Agents/Core"),
    Path(r"C:\Users\passg\mooniex\repo\MoonieX-Agents"),
    Path(r"C:\Users\passg\mooniex"),
]
agents_root = next((p for p in candidates if p.exists()), home)
if str(agents_root) not in sys.path:
    sys.path.insert(0, str(agents_root))

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

if mode == "list":
    limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 25
    host_arg = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        from tools import send_to_agy
        convs = send_to_agy.scan_local_host(host=host_arg, agents_root=agents_root, home_dir=home, limit=limit)
        print(json.dumps({"ok": True, "agents_root": str(agents_root), "conversations": convs}, ensure_ascii=True))
    except Exception as exc:
        # Fallback inline scanner if send_to_agy is not yet pulled on the remote host
        uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
        convs = []
        seen = set()
        for surf, bdir in (("App", home / ".gemini" / "antigravity" / "brain"),
                           ("CLI", home / ".gemini" / "antigravity-cli" / "brain"),
                           ("CLI", home / ".gemini" / "antigravity-cli" / "conversations")):
            if not bdir.is_dir():
                continue
            for ch in sorted(bdir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                cid = ch.name.lower() if ch.is_dir() else (ch.stem.lower() if ch.suffix == ".pb" else "")
                if not uuid_re.fullmatch(cid) or cid in seen:
                    continue
                seen.add(cid)
                mtime = datetime.fromtimestamp(ch.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                box = f"cto-agy-{cid[:8]}"
                convs.append({
                    "kind": "agy", "box": box, "host": host_arg or "remote",
                    "conversation_id": cid, "uuid": cid, "role": "cto", "session_id": f"agy-{cid[:8]}",
                    "cwd": str(agents_root), "last_activity": mtime, "title": box,
                    "first_user_line": box, "app_vs_cli": surf, "surface": surf,
                })
                if len(convs) >= limit:
                    break
        print(json.dumps({"ok": True, "agents_root": str(agents_root), "conversations": convs}, ensure_ascii=True))

elif mode in ("send", "resume"):
    b64_data = sys.argv[-1]
    payload = json.loads(base64.b64decode(b64_data.encode("ascii")).decode("utf-8"))
    box = payload["box"]
    to_role = payload["to_role"]
    to_sid = payload["to_sid"]
    from_role = payload["from_role"]
    from_sid = payload["from_sid"]
    message = payload["message"]
    prompt = payload["prompt"]
    conv_id = payload["conversation_id"]
    model = payload.get("model") or "gemini-4-argon-high"
    agy_mode = payload.get("mode") or "accept-edits"
    cwd = payload.get("cwd") or str(agents_root)
    surface = payload.get("app_vs_cli") or "CLI"
    app_data_dir = payload.get("app_data_dir")
    agy_bin = payload.get("agy_bin") or str(home / ".local" / "bin" / "agy")
    if not Path(agy_bin).is_file():
        for cand in (home / ".local" / "bin" / "agy", Path("/root/.local/bin/agy"),
                     Path("/Users/gob/.local/bin/agy"),
                     Path(r"C:\Users\passg\AppData\Local\agy\bin\agy.exe")):
            if cand.is_file():
                agy_bin = str(cand)
                break

    from lib import mailbox
    letter_path = mailbox.send(
        to_role, to_sid, message, from_role, from_sid,
        chain=[f"{from_role}:{from_sid}", f"{to_role}:{to_sid}"],
    )
    sdir = agents_root / "state" / "agy-sessions"
    sdir.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(Exception):
        from tools import agy_card_run
        rec = agy_card_run.register_session(
            box=box, role=to_role, conversation_id=conv_id,
            model=model, mode=agy_mode, cwd=cwd, sessions_dir=sdir,
        )
        rec["last_from"] = f"{from_role}-{from_sid}"
        rec["last_from_host"] = payload.get("from_host")
        (sdir / f"{box}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    run_cwd = cwd if Path(cwd).is_dir() else str(agents_root)
    cmd = [
        agy_bin, "-p", prompt, "--conversation", conv_id,
        "--model", model, "--mode", agy_mode, "--output-format", "json",
        "--add-dir", run_cwd,
    ]
    if str(agents_root) != run_cwd and agents_root.is_dir():
        cmd.extend(["--add-dir", str(agents_root)])

    child_env = dict(os.environ)
    child_env["AGY_CONVERSATION_ID"] = conv_id
    child_env["AGY_BOX"] = box
    child_env["CXO_ROLE"] = "cto" if to_role == "project_head" else to_role
    child_env["CXO_SESSION_ID"] = to_sid
    if app_data_dir:
        child_env["ANTIGRAVITY_APP_DATA_DIR"] = str(app_data_dir)
    elif surface == "App":
        child_env["ANTIGRAVITY_APP_DATA_DIR"] = str(home / ".gemini" / "antigravity")

    log_path = sdir / f"send-{box}.log"
    fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600)
    popen_kw = {"cwd": run_cwd, "env": child_env, "stdin": subprocess.DEVNULL, "stdout": fd, "stderr": fd, "close_fds": True}
    if sys.platform == "win32":
        popen_kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        popen_kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **popen_kw)
        pid = proc.pid
    finally:
        os.close(fd)
    print(json.dumps({"ok": True, "box": box, "conversation_id": conv_id, "pid": pid, "letter": str(letter_path)}, ensure_ascii=True))

elif mode == "reply":
    b64_data = sys.argv[-1]
    payload = json.loads(base64.b64decode(b64_data.encode("ascii")).decode("utf-8"))
    to_role = payload["to_role"]
    to_sid = payload["to_sid"]
    from_role = payload["from_role"]
    from_sid = payload["from_sid"]
    from_box = payload["from_box"]
    message = payload["message"]
    from lib import mailbox
    from tools import mail_wake, send_to_cxo
    if to_sid == "active" or not to_sid:
        to_sid = send_to_cxo._active_session_id(to_role) or "fresh"
    to_box = f"{to_role}-{to_sid}"
    letter_path = mailbox.send(
        to_role, to_sid, message, from_role, from_sid,
        chain=[f"{from_role}:{from_sid}", f"{to_role}:{to_sid}"],
    )
    wake_res = mail_wake.wake(to_box, label=from_box)
    print(json.dumps({"ok": True, "to_box": to_box, "letter": str(letter_path), "wake": wake_res}, ensure_ascii=True))
'''


def _probe_remote_host(host: str, limit: int = 25) -> dict[str, Any]:
    """Query `host` over SSH using `HOST_MAP` and return its AGY conversations."""
    host = host.lower().strip()
    cfg = HOST_MAP.get(host)
    if not cfg:
        return {"host": host, "ok": False, "error": f"unknown host {host!r}", "conversations": []}

    cmd = [
        "ssh",
        "-o",
        "ConnectTimeout=6",
        "-o",
        "BatchMode=yes",
        cfg["ssh"],
        cfg["python"],
        "-",
        "list",
        str(limit),
        host,
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=_REMOTE_AGY_PY,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return {"host": host, "ok": False, "error": str(exc)[:300], "conversations": []}

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()[:300]
        return {"host": host, "ok": False, "error": err, "conversations": []}

    out = (proc.stdout or "").strip()
    if not out:
        return {"host": host, "ok": True, "conversations": []}
    try:
        lines = [ln for ln in out.splitlines() if ln.strip()]
        parsed = json.loads(lines[-1])
    except ValueError as exc:
        return {"host": host, "ok": False, "error": f"bad json: {exc}", "conversations": []}

    if isinstance(parsed, list):
        convs = parsed
    elif isinstance(parsed, dict):
        convs = parsed.get("conversations") or parsed.get("sessions") or []
    else:
        convs = []

    for c in convs:
        if isinstance(c, dict):
            c["host"] = host
            c.setdefault("kind", "agy")
            if "conversation_id" in c and "uuid" not in c:
                c["uuid"] = c["conversation_id"]
            elif "uuid" in c and "conversation_id" not in c:
                c["conversation_id"] = c["uuid"]
            surf = c.get("app_vs_cli") or c.get("surface") or "CLI"
            c["app_vs_cli"] = surf
            c["surface"] = surf
            title = c.get("title") or c.get("first_user_line") or c.get("box") or ""
            c["title"] = title
            c["first_user_line"] = title
    return {"host": host, "ok": True, "conversations": convs}


def scan_host(
    host: str,
    *,
    limit: int = 25,
    env: dict[str, str] | None = None,
    sessions_dir: Path | None = None,
    brains_dir: Path | None = None,
    home_dir: Path | None = None,
) -> dict[str, Any]:
    """Scan a single host (`contabo`, `mac`, or `winbox`) for AGY conversations."""
    host = host.lower().strip()
    here = current_host(env)
    if host == here:
        convs = scan_local_host(
            host,
            sessions_dir=sessions_dir,
            brains_dir=brains_dir,
            home_dir=home_dir,
            limit=limit,
        )
        return {"host": host, "ok": True, "conversations": convs}

    res = _probe_remote_host(host, limit=limit)
    # Merge any locally-registered `state/agy-sessions/*.json` entries pinned to `host`
    sdir = Path(sessions_dir or agy_card_run.AGY_SESSIONS_DIR)
    seen_uuids = {str(c.get("conversation_id") or "").lower() for c in res.get("conversations") or []}
    if sdir.is_dir() and not sdir.is_symlink():
        for f in sorted(sdir.glob("*.json")):
            if f.is_symlink():
                continue
            with contextlib.suppress(OSError, ValueError):
                data = json.loads(f.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                if str(data.get("host") or "").lower() != host:
                    continue
                cid = str(data.get("conversation_id") or "").strip().lower()
                if not _UUID_RE.fullmatch(cid) or cid in seen_uuids:
                    continue
                seen_uuids.add(cid)
                surf = _detect_surface(False, False, data)
                title = str(data.get("last_response_preview") or data.get("box") or cid[:8])[:140]
                res.setdefault("conversations", []).append(
                    {
                        "kind": "agy",
                        "box": data.get("box") or f"cto-agy-{cid[:8]}",
                        "host": host,
                        "conversation_id": cid,
                        "uuid": cid,
                        "role": data.get("role") or "cto",
                        "session_id": data.get("session_id") or f"agy-{cid[:8]}",
                        "cwd": data.get("cwd") or HOST_MAP.get(host, {}).get("agents_root") or str(ROOT),
                        "last_activity": data.get("last_wake_at") or data.get("updated_at") or _now_iso(),
                        "title": title,
                        "first_user_line": title,
                        "app_vs_cli": surf,
                        "surface": surf,
                        "model": data.get("model") or agy_card_run.DEFAULT_MODEL,
                        "mode": data.get("mode") or agy_card_run.DEFAULT_MODE,
                        "parked": bool(data.get("parked")),
                        "app_data_dir": data.get("app_data_dir"),
                        "ls_address": data.get("ls_address"),
                        "csrf_token": data.get("csrf_token"),
                        "agentapi_exe": data.get("agentapi_exe"),
                        "project_id": data.get("project_id"),
                    }
                )
    return res


def list_conversations(
    hosts: tuple[str, ...] = HOSTS,
    *,
    limit_per_host: int = 25,
    env: dict[str, str] | None = None,
    sessions_dir: Path | None = None,
    brains_dir: Path | None = None,
    home_dir: Path | None = None,
) -> dict[str, Any]:
    """List AGY conversations across `hosts` (`contabo`, `mac`, `winbox`)."""
    if len(hosts) == 1:
        h = hosts[0]
        host_results = {
            h: scan_host(
                h,
                limit=limit_per_host,
                env=env,
                sessions_dir=sessions_dir,
                brains_dir=brains_dir,
                home_dir=home_dir,
            )
        }
    else:
        with ThreadPoolExecutor(max_workers=len(hosts)) as pool:
            futures = {
                h: pool.submit(
                    scan_host,
                    h,
                    limit=limit_per_host,
                    env=env,
                    sessions_dir=sessions_dir,
                    brains_dir=brains_dir,
                    home_dir=home_dir,
                )
                for h in hosts
            }
        host_results = {h: futures[h].result() for h in hosts}

    flat: list[dict[str, Any]] = []
    for h in hosts:
        for conv in host_results.get(h, {}).get("conversations") or []:
            flat.append(conv)

    flat.sort(key=lambda c: (not bool(c.get("parked")), str(c.get("last_activity") or "")), reverse=True)
    return {
        "scanned_at": _now_iso(),
        "hosts": host_results,
        "conversations": flat,
    }


def resolve_sender(
    explicit_from: str | None = None,
    *,
    env: dict[str, str] | None = None,
) -> tuple[str, str, str]:
    """Resolve `(from_box, from_role, from_sid)` from `--from <role>-<sid>` or process env."""
    if explicit_from and explicit_from.strip():
        clean = explicit_from.strip()
        if "-" in clean:
            role_part, _, sid_part = clean.partition("-")
            role_clean = role_part.strip().lower()
            sid_clean = sid_part.strip()
            if not role_clean or not sid_clean:
                raise ValueError(f"invalid --from value {explicit_from!r}; expected <role>-<sid>")
            return f"{role_clean}-{sid_clean}", role_clean, sid_clean
        role_clean = clean.lower()
        sid_clean = send_to_cxo._active_session_id(role_clean) or "fresh"
        return f"{role_clean}-{sid_clean}", role_clean, sid_clean

    env_map = os.environ if env is None else env
    if env is not None:
        # Respect explicit env dictionary passed in tests/callers
        r = (env_map.get("CXO_ROLE") or "").strip().lower()
        if r:
            sid = (env_map.get("CXO_SESSION_ID") or env_map.get("CTO_SESSION_ID") or "").strip()
            if sid:
                return f"{r}-{sid}", r, sid
        wt = (env_map.get("WORKER_TASK_ID") or "").strip()
        if wt:
            wr = (env_map.get("WORKER_ROLE") or "dev").strip().lower()
            return f"{wr}-{wt}", wr, wt
        cto_sid = (env_map.get("CTO_SESSION_ID") or "").strip()
        if cto_sid:
            return f"cto-{cto_sid}", "cto", cto_sid
        if agent_transport._is_ceo_env(env_map):
            return "ceo-ceo", "ceo", "ceo"
        if env_map.get("AGY_CONVERSATION_ID") or env_map.get("ANTIGRAVITY_CONVERSATION_ID"):
            box, role, sid, _ = agy_card_run.resolve_identity(env=env_map)
            return box, role, sid

    try:
        ident = agent_transport.current_identity()
        role = ident.role.lower()
        sid = ident.session_id or "ceo"
        return f"{role}-{sid}", role, sid
    except PermissionError:
        conv_id = agy_card_run.detect_conversation_id(env=env_map)
        if conv_id and ("PYTEST_CURRENT_TEST" not in env_map or env_map.get("AGY_CONVERSATION_ID")):
            box, role, sid, _ = agy_card_run.resolve_identity(conversation_id=conv_id, env=env_map)
            return box, role, sid
        raise


def resolve_target(
    target: str,
    *,
    host: str | None = None,
    sessions_dir: Path | None = None,
    brains_dir: Path | None = None,
    home_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve `<box|uuid>` to a conversation metadata dictionary."""
    needle = (target or "").strip()
    if not needle:
        raise TargetNotFoundError("target box or conversation UUID cannot be empty")
    needle_low = needle.lower()

    sdir = Path(sessions_dir or agy_card_run.AGY_SESSIONS_DIR)
    # 1. Check local state/agy-sessions/<box>.json directly
    if sdir.is_dir() and not sdir.is_symlink():
        direct = sdir / f"{needle}.json"
        if direct.is_file() and not direct.is_symlink():
            with contextlib.suppress(OSError, ValueError):
                data = json.loads(direct.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("conversation_id"):
                    cid = str(data["conversation_id"]).strip().lower()
                    thost = (host or data.get("host") or current_host(env)).lower()
                    surf = _detect_surface(False, False, data)
                    return {
                        **data,
                        "box": data.get("box") or needle,
                        "host": thost,
                        "conversation_id": cid,
                        "uuid": cid,
                        "app_vs_cli": surf,
                        "surface": surf,
                    }

        for f in sorted(sdir.glob("*.json")):
            if f.is_symlink():
                continue
            with contextlib.suppress(OSError, ValueError):
                data = json.loads(f.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                cid = str(data.get("conversation_id") or "").strip().lower()
                box_name = str(data.get("box") or f.stem).strip()
                if (
                    box_name.lower() == needle_low
                    or cid == needle_low
                    or (len(needle_low) >= 8 and cid.startswith(needle_low))
                ):
                    thost = (host or data.get("host") or current_host(env)).lower()
                    surf = _detect_surface(False, False, data)
                    return {
                        **data,
                        "box": box_name,
                        "host": thost,
                        "conversation_id": cid,
                        "uuid": cid,
                        "app_vs_cli": surf,
                        "surface": surf,
                    }

    # 2. Scan hosts (local host first, then remote hosts)
    here = current_host(env)
    search_hosts: tuple[str, ...]
    if host and host.lower() in HOSTS:
        search_hosts = (host.lower(),)
    else:
        search_hosts = (here, *[h for h in HOSTS if h != here])

    for h in search_hosts:
        hres = scan_host(
            h,
            env=env,
            sessions_dir=sessions_dir,
            brains_dir=brains_dir,
            home_dir=home_dir,
        )
        for conv in hres.get("conversations") or []:
            cid = str(conv.get("conversation_id") or "").lower()
            cbox = str(conv.get("box") or "").lower()
            csid = str(conv.get("session_id") or "").lower()
            if (
                cbox == needle_low
                or csid == needle_low
                or cid == needle_low
                or (len(needle_low) >= 8 and cid.startswith(needle_low))
            ):
                return conv

    # 3. If caller passed a valid full UUID directly (e.g. a fresh conversation ID)
    if _UUID_RE.fullmatch(needle_low):
        thost = (host or here).lower()
        short = needle_low[:8]
        box = f"cto-agy-{short}"
        return {
            "kind": "agy",
            "box": box,
            "host": thost,
            "conversation_id": needle_low,
            "uuid": needle_low,
            "role": "cto",
            "session_id": f"agy-{short}",
            "cwd": HOST_MAP.get(thost, {}).get("agents_root") or str(ROOT),
            "app_vs_cli": "CLI",
            "surface": "CLI",
            "model": agy_card_run.DEFAULT_MODEL,
            "mode": agy_card_run.DEFAULT_MODE,
        }

    raise TargetNotFoundError(f"no AGY conversation or session matching {target!r} found across {search_hosts}")


def format_send_prompt(
    *,
    box: str,
    from_box: str,
    message: str,
    from_host: str | None = None,
    target_host: str | None = None,
) -> str:
    """Format the prompt delivered to `agy -p ... --conversation <uuid>`."""
    host_note = f" (on `{from_host}`)" if from_host else ""
    return (
        f"[MESSAGE for AGY session `{box}` from `{from_box}`{host_note}]\n\n"
        f"{message}\n\n"
        f"---\n"
        f"Sender: `{from_box}`{host_note}\n"
        f"To answer `{from_box}`, run:\n"
        f'  bash scripts/hub/org-python.sh tools/send_to_cxo.py {from_box} "<reply>"\n'
        f'(or cross-host: `bash scripts/hub/org-python.sh tools/send_to_agy.py reply {from_box} "<reply>" --from {box}`)'
    )


def _log_cto_event(msg: str, *, cto_log_path: Path | None = None) -> None:
    """Log hop to `lib.notify.info` and ensure it lands in `state/logs/cto.log`."""
    with contextlib.suppress(Exception):
        notify.info(msg)
    target = cto_log_path
    if target is None:
        if notify._under_test() and CTO_LOG_PATH == (ROOT / "state" / "logs" / "cto.log"):
            return
        target = CTO_LOG_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        line = f"[{ts}] CTO-event[INFO]: {msg}\n"
        with target.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def _spawn_detached_local_agy(
    prompt: str,
    *,
    box: str,
    to_role: str,
    to_sid: str,
    conversation_id: str,
    model: str,
    mode: str,
    cwd: str | Path,
    add_dirs: list[str] | None = None,
    app_data_dir: str | None = None,
    surface: str = "CLI",
    sessions_dir: Path | None = None,
    agy_bin: str | None = None,
    env: dict[str, str] | None = None,
) -> int | None:
    """Start `agy -p <prompt> --conversation <uuid>` detached on the local host."""
    sdir = Path(sessions_dir or agy_card_run.AGY_SESSIONS_DIR)
    sdir.mkdir(parents=True, exist_ok=True)
    log_path = sdir / f"send-{box}.log"
    if log_path.is_symlink():
        raise OSError(f"refusing symlinked log path {log_path}")

    binary = agy_bin or ph_brain.resolve_agy_bin()
    run_cwd = str(cwd) if cwd and Path(cwd).is_dir() else str(ROOT)
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
    dirs = list(add_dirs or [run_cwd, str(ROOT)])
    seen_dirs: list[str] = []
    for d in dirs:
        if d and d not in seen_dirs and Path(d).exists():
            seen_dirs.append(d)
            cmd.extend(["--add-dir", str(d)])

    child_env = dict(os.environ if env is None else env)
    child_env["AGY_CONVERSATION_ID"] = conversation_id
    child_env["AGY_BOX"] = box
    child_env["CXO_ROLE"] = "cto" if to_role == "project_head" else (to_role if to_role in c_level_roles() else "cto")
    child_env["CXO_SESSION_ID"] = to_sid
    if app_data_dir:
        child_env["ANTIGRAVITY_APP_DATA_DIR"] = str(app_data_dir)
    elif surface == "App":
        child_env["ANTIGRAVITY_APP_DATA_DIR"] = str(Path.home() / ".gemini" / "antigravity")

    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | _NOFOLLOW, 0o600)
    popen_kw: dict[str, Any] = {
        "cwd": run_cwd,
        "env": child_env,
        "stdin": subprocess.DEVNULL,
        "stdout": fd,
        "stderr": fd,
        "close_fds": True,
    }
    if sys.platform == "win32":
        popen_kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        popen_kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **popen_kw)
        return getattr(proc, "pid", None)
    finally:
        os.close(fd)


def _resume_remote_agy(
    *,
    target_host: str,
    box: str,
    to_role: str,
    to_sid: str,
    from_box: str,
    from_role: str,
    from_sid: str,
    from_host: str,
    message: str,
    prompt: str,
    conversation_id: str,
    model: str,
    mode: str,
    cwd: str,
    surface: str,
    app_data_dir: str | None,
) -> dict[str, Any]:
    """Write the letter and spawn `agy -p ... --conversation <uuid>` detached on `target_host` over SSH."""
    cfg = HOST_MAP.get(target_host)
    if not cfg:
        raise ValueError(f"unknown target host {target_host!r}")

    payload = {
        "box": box,
        "to_role": to_role,
        "to_sid": to_sid,
        "from_box": from_box,
        "from_role": from_role,
        "from_sid": from_sid,
        "from_host": from_host,
        "message": message,
        "prompt": prompt,
        "conversation_id": conversation_id,
        "model": model,
        "mode": mode,
        "cwd": cwd,
        "app_vs_cli": surface,
        "app_data_dir": app_data_dir,
        "agy_bin": cfg["agy_bin"],
    }
    b64_payload = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    cmd = [
        "ssh",
        "-o",
        "ConnectTimeout=6",
        "-o",
        "BatchMode=yes",
        cfg["ssh"],
        cfg["python"],
        "-",
        "send",
        "agy",
        "-p",
        "--conversation",
        conversation_id,
        "--box",
        box,
        "--from",
        from_box,
        "--b64",
        b64_payload,
    ]
    proc = subprocess.run(
        cmd,
        input=_REMOTE_AGY_PY,
        capture_output=True,
        text=True,
        timeout=25,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()[:400]
        raise RuntimeError(f"remote AGY resume on {target_host} ({cfg['ssh']}) failed: {detail}")

    out_lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if out_lines:
        with contextlib.suppress(ValueError):
            parsed = json.loads(out_lines[-1])
            if isinstance(parsed, dict):
                return parsed
    return {"ok": True, "host": target_host, "box": box, "conversation_id": conversation_id}


def send(
    target: str,
    message: str,
    *,
    from_box: str | None = None,
    host: str | None = None,
    model: str | None = None,
    mode: str | None = None,
    cwd: str | Path | None = None,
    sessions_dir: Path | None = None,
    brains_dir: Path | None = None,
    home_dir: Path | None = None,
    inbox_root: Path | None = None,
    cto_log_path: Path | None = None,
    agy_bin: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Queue a letter to `state/inbox/<box>/` and resume the target AGY conversation on its own host."""
    clean_msg = (message or "").strip()
    if not clean_msg:
        raise ValueError("message cannot be empty")

    resolved_from_box, from_role, from_sid = resolve_sender(from_box, env=env)
    here = current_host(env)

    info = resolve_target(
        target,
        host=host,
        sessions_dir=sessions_dir,
        brains_dir=brains_dir,
        home_dir=home_dir,
        env=env,
    )
    box = str(info["box"])
    conv_id = str(info["conversation_id"]).lower()
    target_host = str(host or info.get("host") or here).lower()
    target_cwd = str(cwd or info.get("cwd") or HOST_MAP.get(target_host, {}).get("agents_root") or ROOT)
    target_model = str(model or info.get("model") or agy_card_run.DEFAULT_MODEL)
    target_mode = str(mode or info.get("mode") or agy_card_run.DEFAULT_MODE)
    surface = str(info.get("app_vs_cli") or info.get("surface") or "CLI")
    app_data_dir = info.get("app_data_dir")

    to_role, sep, to_sid = box.partition("-")
    if not sep or not to_sid:
        to_role, to_sid = "cto", box

    # 1. Write the letter to local state/inbox/<box>/ (same letter shape as send_to_cxo)
    chain = [f"{from_role}:{from_sid}", f"{to_role}:{to_sid}"]
    letter_path = mailbox.send(
        to_role,
        to_sid,
        message,
        from_role,
        from_sid,
        chain=chain,
        root=inbox_root,
        **send_to_cxo._envelope_kw(None),
    )

    # 2. Register/update state/agy-sessions/<box>.json
    sdir = Path(sessions_dir or agy_card_run.AGY_SESSIONS_DIR)
    rec = agy_card_run.register_session(
        box=box,
        role=to_role,
        conversation_id=conv_id,
        model=target_model,
        mode=target_mode,
        cwd=target_cwd,
        sessions_dir=sdir,
        env={**(os.environ if env is None else env), "ORG_HOST": target_host},
    )
    rec["host"] = target_host
    rec["last_from"] = resolved_from_box
    rec["last_from_host"] = here
    if app_data_dir:
        rec["app_data_dir"] = app_data_dir
    try:
        spath = agy_card_run.session_path(box, sessions_dir=sdir)
        spath.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass

    # 3. Build prompt with sender + reply route
    prompt = format_send_prompt(
        box=box,
        from_box=resolved_from_box,
        message=message,
        from_host=here,
        target_host=target_host,
    )

    # 4. Log to CTO event log
    _log_cto_event(
        f"[send_to_agy] {resolved_from_box} ({here}) -> {box} ({target_host} {surface} conv={conv_id}): "
        f"{' '.join(clean_msg.split())[:120]}",
        cto_log_path=cto_log_path,
    )

    # 5. Resume the conversation ON ITS OWN HOST (local if target_host == here, else over SSH)
    pid: int | None = None
    remote_res: dict[str, Any] | None = None
    if target_host == here:
        pid = _spawn_detached_local_agy(
            prompt,
            box=box,
            to_role=to_role,
            to_sid=to_sid,
            conversation_id=conv_id,
            model=target_model,
            mode=target_mode,
            cwd=target_cwd,
            add_dirs=rec.get("add_dirs"),
            app_data_dir=app_data_dir,
            surface=surface,
            sessions_dir=sdir,
            agy_bin=agy_bin,
            env=env,
        )
    else:
        remote_res = _resume_remote_agy(
            target_host=target_host,
            box=box,
            to_role=to_role,
            to_sid=to_sid,
            from_box=resolved_from_box,
            from_role=from_role,
            from_sid=from_sid,
            from_host=here,
            message=message,
            prompt=prompt,
            conversation_id=conv_id,
            model=target_model,
            mode=target_mode,
            cwd=target_cwd,
            surface=surface,
            app_data_dir=app_data_dir,
        )
        pid = remote_res.get("pid") if isinstance(remote_res, dict) else None

    return {
        "ok": True,
        "box": box,
        "to_role": to_role,
        "to_sid": to_sid,
        "from_box": resolved_from_box,
        "from_role": from_role,
        "from_sid": from_sid,
        "host": target_host,
        "conversation_id": conv_id,
        "app_vs_cli": surface,
        "letter_path": str(letter_path),
        "prompt": prompt,
        "pid": pid,
        "remote": target_host != here,
    }


def _claude_box_live_locally(role: str, sid: str, *, locks_dir: Path | None = None) -> bool:
    """Return True if Claude session `<role>-<sid>` has a live lock or tmux pane on this host."""
    ldir = Path(locks_dir or send_to_cxo.LOCKS_DIR)
    for ext in ("lock", "winid", "uuid", "project"):
        if (ldir / f"{role}-{sid}.{ext}").is_file():
            return True
    if (ldir / f"{role}-active").is_file():
        with contextlib.suppress(OSError):
            if (ldir / f"{role}-active").read_text(encoding="utf-8").strip() == sid:
                return True
    if locks_dir is None or Path(locks_dir) == Path(send_to_cxo.LOCKS_DIR):
        with contextlib.suppress(Exception):
            from tools import session_name, tmux_session
            if tmux_session.has_session(session_name.tmux_name(role, sid)):
                return True
    return False


def _resolve_claude_target_host(
    to_role: str,
    to_sid: str,
    *,
    explicit_host: str | None = None,
    from_box: str | None = None,
    sessions_dir: Path | None = None,
    locks_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Determine which host (`contabo`, `mac`, `winbox`) holds the target Claude session."""
    if explicit_host and explicit_host.lower() in HOSTS:
        return explicit_host.lower()

    here = current_host(env)
    if _claude_box_live_locally(to_role, to_sid, locks_dir=locks_dir):
        return here

    # Check if the AGY session record recorded `last_from_host` when it received a message
    if from_box:
        rec = agy_card_run.load_session(from_box, sessions_dir=sessions_dir)
        if rec and rec.get("last_from_host") in HOSTS:
            if not rec.get("last_from") or rec.get("last_from") in (f"{to_role}-{to_sid}", to_role):
                return str(rec["last_from_host"])

    # CEO rule (AGENTS.md): The CTO runs only on Contabo
    if to_role == "cto":
        return "contabo"

    return "contabo" if here != "contabo" else here


def reply_to_claude(
    target_box: str,
    message: str,
    *,
    from_box: str | None = None,
    host: str | None = None,
    sessions_dir: Path | None = None,
    locks_dir: Path | None = None,
    inbox_root: Path | None = None,
    cto_log_path: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """AGY -> Claude reply route across `contabo`, `mac`, and `winbox`."""
    clean_msg = (message or "").strip()
    if not clean_msg:
        raise ValueError("reply message cannot be empty")

    env_map = os.environ if env is None else env
    if from_box and from_box.strip():
        resolved_from_box, from_role, from_sid = resolve_sender(from_box, env=env_map)
    else:
        conv_id = agy_card_run.detect_conversation_id(env=env_map)
        if conv_id:
            resolved_from_box, from_role, from_sid, _ = agy_card_run.resolve_identity(
                conversation_id=conv_id,
                env=env_map,
            )
            # If a registered session exists for conv_id in sessions_dir, use its box
            sdir = Path(sessions_dir or agy_card_run.AGY_SESSIONS_DIR)
            if sdir.is_dir() and not sdir.is_symlink():
                for f in sorted(sdir.glob("*.json")):
                    if f.is_symlink():
                        continue
                    with contextlib.suppress(OSError, ValueError):
                        data = json.loads(f.read_text(encoding="utf-8"))
                        if isinstance(data, dict) and str(data.get("conversation_id") or "").lower() == conv_id.lower():
                            resolved_from_box = str(data.get("box") or f.stem)
                            r_p, _, s_p = resolved_from_box.partition("-")
                            from_role = str(data.get("role") or r_p or "cto")
                            from_sid = str(data.get("session_id") or s_p or f"agy-{conv_id[:8]}")
                            break
        else:
            resolved_from_box, from_role, from_sid = resolve_sender(None, env=env_map)

    clean_target = (target_box or "").strip()
    if not clean_target:
        raise ValueError("target Claude session (<role>-<sid> or <role>) cannot be empty")

    if "-" in clean_target:
        r_part, _, s_part = clean_target.partition("-")
        to_role = send_to_cxo.resolve_target_role(r_part.strip().lower())
        to_sid = s_part.strip()
    else:
        to_role = send_to_cxo.resolve_target_role(clean_target.lower())
        ldir = Path(locks_dir or send_to_cxo.LOCKS_DIR)
        to_sid = agent_transport._active_session_id(to_role, ldir) or "fresh"

    to_box = f"{to_role}-{to_sid}"
    here = current_host(env_map)
    target_host = _resolve_claude_target_host(
        to_role,
        to_sid,
        explicit_host=host,
        from_box=resolved_from_box,
        sessions_dir=sessions_dir,
        locks_dir=locks_dir,
        env=env_map,
    )

    _log_cto_event(
        f"[send_to_agy:reply] {resolved_from_box} ({here}) -> {to_box} ({target_host}): "
        f"{' '.join(clean_msg.split())[:120]}",
        cto_log_path=cto_log_path,
    )

    if target_host == here:
        chain = [f"{from_role}:{from_sid}", f"{to_role}:{to_sid}"]
        letter_path = mailbox.send(
            to_role,
            to_sid,
            message,
            from_role,
            from_sid,
            chain=chain,
            root=inbox_root,
            **send_to_cxo._envelope_kw(None),
        )
        wake_res = mail_wake.wake(to_box, label=resolved_from_box)
        return {
            "ok": True,
            "from_box": resolved_from_box,
            "to_box": to_box,
            "host": target_host,
            "remote": False,
            "letter_path": str(letter_path),
            "wake": wake_res,
        }

    cfg = HOST_MAP.get(target_host)
    if not cfg:
        raise ValueError(f"unknown target host {target_host!r}")
    payload = {
        "to_role": to_role,
        "to_sid": to_sid,
        "from_role": from_role,
        "from_sid": from_sid,
        "from_box": resolved_from_box,
        "message": message,
    }
    b64_payload = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    cmd = [
        "ssh",
        "-o",
        "ConnectTimeout=6",
        "-o",
        "BatchMode=yes",
        cfg["ssh"],
        cfg["python"],
        "-",
        "reply",
        "--to",
        to_box,
        "--from",
        resolved_from_box,
        "--b64",
        b64_payload,
    ]
    proc = subprocess.run(
        cmd,
        input=_REMOTE_AGY_PY,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()[:400]
        raise RuntimeError(f"remote reply to {to_box} on {target_host} ({cfg['ssh']}) failed: {detail}")

    wake_res: dict[str, Any] = {}
    out_lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if out_lines:
        with contextlib.suppress(ValueError):
            parsed = json.loads(out_lines[-1])
            if isinstance(parsed, dict):
                wake_res = parsed.get("wake") or {}

    return {
        "ok": True,
        "from_box": resolved_from_box,
        "to_box": to_box,
        "host": target_host,
        "remote": True,
        "wake": wake_res,
    }


def format_live_agy_line(conv: dict[str, Any]) -> str:
    """Format one AGY row (`kind: agy`) for `scripts/live-sessions.sh` text output."""
    box = str(conv.get("box") or "?")
    host = str(conv.get("host") or "?")
    surf = str(conv.get("app_vs_cli") or conv.get("surface") or "CLI")
    cid = str(conv.get("conversation_id") or conv.get("uuid") or "?")
    cwd = str(conv.get("cwd") or "?")
    title = " ".join(str(conv.get("title") or conv.get("first_user_line") or box).split())[:90]
    return f"agy      {box}  ({host} {surf} {cid[:8]})  {cwd} — {title}"


def render_live_sessions_with_agy(
    argv: list[str] | None = None,
    *,
    agy_conversations: list[dict[str, Any]] | None = None,
    claude_text: str | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Combine `tools.live_sessions` output with AGY rows (`kind: agy`)."""
    args = live_sessions._parser().parse_args(argv or [])
    base_text = claude_text if claude_text is not None else live_sessions._read_text(args)

    if agy_conversations is not None:
        agy_rows = list(agy_conversations)
    elif args.local:
        agy_rows = scan_local_host(current_host(env))
    else:
        agy_rows = list_conversations(env=env)["conversations"]

    if args.sid:
        want = args.sid.strip().lstrip("#").lower()
        agy_rows = [
            r
            for r in agy_rows
            if want
            and (
                str(r.get("box") or "").lower() == want
                or str(r.get("session_id") or "").lower() == want
                or str(r.get("conversation_id") or "").lower() == want
                or str(r.get("conversation_id") or "").lower().startswith(want)
                or str(r.get("conversation_id") or "").lower().endswith(want)
            )
        ]
    else:
        agy_rows = [r for r in agy_rows if not r.get("parked")]

    if args.json:
        try:
            doc = json.loads(base_text)
        except ValueError:
            return base_text
        if not isinstance(doc, dict):
            return base_text
        sessions = doc.setdefault("sessions", [])
        for r in agy_rows:
            sessions.append(
                {
                    "kind": "agy",
                    "host": r.get("host"),
                    "sid": r.get("session_id"),
                    "box": r.get("box"),
                    "uuid": r.get("conversation_id"),
                    "conversation_id": r.get("conversation_id"),
                    "role": r.get("role") or "agy",
                    "status": "agy",
                    "address": r.get("box"),
                    "app_vs_cli": r.get("app_vs_cli") or r.get("surface") or "CLI",
                    "cwd": r.get("cwd"),
                    "last_activity": r.get("last_activity"),
                    "title": r.get("title") or r.get("first_user_line"),
                    "verified": True,
                    "claims": None,
                    "age_s": 0,
                    "stale": False,
                }
            )
        return json.dumps(doc, ensure_ascii=False)

    if args.sid:
        agy_lines = [format_live_agy_line(r) for r in agy_rows]
        if base_text.strip() == "not live (no fresh row)":
            return "\n".join(agy_lines) if agy_lines else base_text
        if agy_lines:
            return base_text.rstrip("\n") + "\n" + "\n".join(agy_lines)
        return base_text

    if not agy_rows:
        return base_text

    agy_lines = [format_live_agy_line(r) for r in agy_rows]
    lines = base_text.splitlines()
    if live_sessions.FOOTER in lines:
        idx = lines.index(live_sessions.FOOTER)
        merged = lines[:idx] + agy_lines + [lines[idx], AGY_FOOTER] + lines[idx + 1 :]
        return "\n".join(merged)
    return base_text.rstrip("\n") + "\n" + "\n".join(agy_lines) + "\n" + AGY_FOOTER


def print_list_table(data: dict[str, Any]) -> None:
    """Print human-readable table of AGY conversations across hosts."""
    convs = data.get("conversations") or []
    for h, hres in (data.get("hosts") or {}).items():
        if not hres.get("ok"):
            print(f"[{h.upper()}] warning: host unreachable ({hres.get('error')})", file=sys.stderr)
    if not convs:
        print("(no AGY conversations found)")
        return
    print(
        f"{'BOX':<26} {'HOST':<8} {'SURFACE':<7} {'CONVERSATION UUID':<36} "
        f"{'LAST ACTIVITY':<20} {'CWD':<34} {'TITLE / FIRST USER LINE'}"
    )
    print(f"{'-'*26} {'-'*8} {'-'*7} {'-'*36} {'-'*20} {'-'*34} {'-'*40}")
    for c in convs:
        box = str(c.get("box") or "")[:26]
        host = str(c.get("host") or "")[:8]
        surf = str(c.get("app_vs_cli") or c.get("surface") or "CLI")[:7]
        cid = str(c.get("conversation_id") or c.get("uuid") or "")[:36]
        last = str(c.get("last_activity") or "")[:20]
        cwd = str(c.get("cwd") or "")
        if len(cwd) > 34:
            cwd = "…" + cwd[-33:]
        title = " ".join(str(c.get("title") or c.get("first_user_line") or "").split())[:70]
        print(f"{box:<26} {host:<8} {surf:<7} {cid:<36} {last:<20} {cwd:<34} {title}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "live-sessions":
        rest = argv[1:]
        if rest and rest[0] == "publish":
            return live_sessions.main(rest)
        print(render_live_sessions_with_agy(rest))
        return 0

    parser = argparse.ArgumentParser(prog="tools/send_to_agy.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser(
        "list",
        help="List every AGY conversation on mac/contabo/winbox (box, host, uuid, cwd, last activity, title, App vs CLI)",
    )
    p_list.add_argument("--host", choices=("all", *HOSTS), default="all")
    p_list.add_argument("--limit", type=int, default=25)
    p_list.add_argument("--local", action="store_true", help="Scan current host only")
    p_list.add_argument("--json", action="store_true")

    p_send = sub.add_parser(
        "send",
        help="Write a letter to state/inbox/<box>/ and resume that AGY conversation on its own host",
    )
    p_send.add_argument("target", help="AGY mailbox <box> (e.g. cto-agy-64ad6099) or conversation <uuid>")
    p_send.add_argument("message", help="Message body to deliver")
    p_send.add_argument("--from", dest="from_box", help="Sender <role>-<sid> (e.g. cto-fresh)")
    p_send.add_argument("--host", choices=HOSTS, help="Explicit target host override")
    p_send.add_argument("--model", help="AGY model override")
    p_send.add_argument("--mode", help="AGY mode override")
    p_send.add_argument("--cwd", help="Working directory override")
    p_send.add_argument("--json", action="store_true")

    p_reply = sub.add_parser(
        "reply",
        help="Reply from an AGY conversation on any host back to a Claude session (<role>-<sid> or <role>)",
    )
    p_reply.add_argument("to_box", help="Recipient Claude box <role>-<sid> (e.g. cto-fresh) or <role>")
    p_reply.add_argument("message", help="Reply message body")
    p_reply.add_argument("--from", dest="from_box", help="AGY sender box <role>-<sid>")
    p_reply.add_argument("--host", choices=HOSTS, help="Explicit target Claude host override")
    p_reply.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "list":
            if args.local:
                hosts = (current_host(),)
            elif args.host == "all":
                hosts = HOSTS
            else:
                hosts = (args.host,)
            data = list_conversations(hosts=hosts, limit_per_host=args.limit)
            if args.json:
                print(json.dumps(data["conversations"], indent=2, ensure_ascii=False))
            else:
                print_list_table(data)
            return 0

        if args.cmd == "send":
            res = send(
                args.target,
                args.message,
                from_box=args.from_box,
                host=args.host,
                model=args.model,
                mode=args.mode,
                cwd=args.cwd,
            )
            if args.json:
                print(json.dumps(res, indent=2, ensure_ascii=False))
            else:
                print(
                    f"sent to AGY {res['box']} ({res['conversation_id']}) on {res['host']} "
                    f"[{res['app_vs_cli']}]: [{res['from_box']}] : {args.message}"
                )
            return 0

        if args.cmd == "reply":
            res = reply_to_claude(
                args.to_box,
                args.message,
                from_box=args.from_box,
                host=args.host,
            )
            if args.json:
                print(json.dumps(res, indent=2, ensure_ascii=False))
            else:
                print(
                    f"replied to {res['to_box']} on {res['host']}: [{res['from_box']}] : {args.message}"
                )
            return 0
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (TargetNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"send_to_agy error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
