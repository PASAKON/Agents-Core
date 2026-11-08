"""Emergency Cross-Host Claude Code -> AGY Takeover Engine (`mac`, `contabo`, `winbox`).

Allows AGY CLI (`agy`) to discover, inspect, and seamlessly resume any stalled or
quota-stopped Claude Code session (C-level, Project Head, or Worker) across:
- `mac` (local `/Users/gob/MoonieXHQ/Agents/Core` & `~/.claude/projects`)
- `contabo` (`ssh mooniex-vps`, `/opt/MoonieXHQ/Agents/Core` & `/root/.claude/projects`)
- `winbox` (`ssh winbox`, `C:\\Users\\passg\\mooniex` & `C:\\Users\\passg\\.claude\\projects`)

Also recovers drained mailbox letters (`UserPromptSubmit` hook payloads) that arrived
on the exact turn Claude Code hit `"You've hit your weekly limit"`, and maps any
referenced `.claude/skills/<SkillName>/SKILL.md` so AGY can use Claude's skills directly.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKILLS_DIR = ROOT / ".claude" / "skills"
TAKEOVER_DIR = ROOT / "state" / "takeover"

HOSTS = ("mac", "contabo", "winbox")

# This self-contained Python snippet runs locally on Mac or over SSH stdin on Contabo/Winbox
# so it works identically on Linux, macOS, and Windows (cmd.exe -> python.exe -).
_REMOTE_PROBE_PY = r'''
import json, os, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

mode = sys.argv[1]
arg = sys.argv[2] if len(sys.argv) > 2 else ""
max_turns = int(sys.argv[3]) if len(sys.argv) > 3 else 10

home = Path.home()
claude_projects = home / ".claude" / "projects"

# Locate Agents/Core root on this host
candidates = [
    Path("/opt/MoonieXHQ/Agents/Core"),
    Path("/Users/gob/MoonieXHQ/Agents/Core"),
    Path(r"C:\Users\passg\mooniex\repo\MoonieX-Agents"),
]
agents_root = next((p for p in candidates if p.exists()), home)
locks_dir = agents_root / "state" / "locks"
briefs_dir = agents_root / "state" / "ph-briefs"

def _find_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    extra = [
        home / ".local" / "bin" / name,
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
        Path("/Applications/Antigravity.app/Contents/Resources/app/bin") / name,
        home / "AppData" / "Roaming" / "npm" / f"{name}.cmd",
        home / "AppData" / "Local" / "Programs" / "Antigravity" / "bin" / f"{name}.cmd",
    ]
    for p in extra:
        if p.exists():
            return str(p)
    return ""

def _probe_env_readiness(cwd_str: str) -> dict:
    cwd_path = Path(cwd_str) if cwd_str else agents_root
    exists = cwd_path.exists()
    probe_dir = cwd_path if exists else (cwd_path.parent if cwd_path.parent.exists() else agents_root)

    # Locate existing pre-installed Python .venv (never reinstall packages from 0)
    venv_candidates = [
        cwd_path / ".venv" / "bin" / "python",
        cwd_path / ".venv" / "Scripts" / "python.exe",
        cwd_path.parent / ".venv" / "bin" / "python",
        cwd_path.parent / ".venv" / "Scripts" / "python.exe",
        agents_root / ".venv" / "bin" / "python",
        agents_root / ".venv" / "Scripts" / "python.exe",
        Path(r"C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe"),
    ]
    venv_py = next((str(p) for p in venv_candidates if p.exists()), sys.executable)

    has_pkg_json = (cwd_path / "package.json").exists() if exists else False
    has_node_modules = (
        (cwd_path / "node_modules").exists()
        or (cwd_path.parent / "node_modules").exists()
    ) if exists else False

    git_ready = (cwd_path / ".git").exists() if exists else False
    try:
        disk_free_gb = round(shutil.disk_usage(str(probe_dir)).free / (1024 ** 3), 2)
    except OSError:
        disk_free_gb = -1.0

    tools = {}
    for tname in ("git", "python3", "python", "node", "ffmpeg", "agy"):
        loc = _find_tool(tname)
        if loc:
            tools[tname] = loc

    # Detect local-only large data folders / files (>1 MB) that must stay in-place
    local_large_items = []
    if exists:
        for special in ("label_review", "vision/from_pod", "Work", "studio/data", "data"):
            sp = cwd_path / special
            if sp.exists():
                local_large_items.append(f"{special}/ (local data dir)")
        try:
            for child in list(cwd_path.iterdir())[:60]:
                if child.is_file():
                    sz_mb = child.stat().st_size / (1024 * 1024)
                    if sz_mb > 1.0:
                        local_large_items.append(f"{child.name} ({sz_mb:.1f} MB)")
        except OSError:
            pass

    return {
        "cwd": str(cwd_path),
        "cwd_exists": exists,
        "git_ready": git_ready,
        "venv_python": venv_py,
        "has_package_json": has_pkg_json,
        "node_modules_ready": (not has_pkg_json) or has_node_modules,
        "disk_free_gb": disk_free_gb,
        "tools": tools,
        "local_large_items": local_large_items[:10],
    }


# Map short session id -> project name & owner
projects_map = {}
owners_map = {}
uuid_map = {}
if locks_dir.exists():
    for p in locks_dir.glob("project_head-*.project*"):
        sid = p.name.split("project_head-", 1)[1].split(".")[0]
        try:
            projects_map[sid] = p.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            pass
    for p in locks_dir.glob("project_head-*.spawned_by*"):
        sid = p.name.split("project_head-", 1)[1].split(".")[0]
        try:
            owners_map[sid] = p.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            pass
    for p in locks_dir.glob("*.uuid"):
        stem = p.stem  # e.g. cto-fresh, cmo-e785343f, project_head-3511068d
        try:
            u = p.read_text(encoding="utf-8", errors="replace").strip()
            uuid_map[u] = stem
        except OSError:
            pass

def _extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("type")
                if t == "text":
                    parts.append(item.get("text", ""))
                elif t == "tool_use":
                    name = item.get("name", "")
                    inp = item.get("input", {})
                    if name == "Skill":
                        parts.append(f"[Skill: {inp.get('skill')}]")
                    elif name == "Bash":
                        parts.append(f"[Bash: {str(inp.get('command', ''))[:140]}]")
                    else:
                        parts.append(f"[Tool: {name} {str(inp)[:100]}]")
        return "\n".join(p for p in parts if p)
    return str(content or "")

def _tail_lines(path: Path, max_bytes: int = 262144):
    try:
        sz = path.stat().st_size
        with path.open("rb") as fh:
            if sz > max_bytes:
                fh.seek(sz - max_bytes)
                fh.readline()  # discard partial line
            raw = fh.read().decode("utf-8", errors="replace")
        return [ln for ln in raw.splitlines() if ln.strip()]
    except OSError:
        return []

def _summarize_jsonl(f: Path, detailed: bool = False):
    stem = f.stem
    short8 = stem[-8:]
    parent_name = f.parent.name
    task_match = re.search(r"(task-[0-9a-f]{8})", parent_name)

    role_label = uuid_map.get(stem, "")
    project = projects_map.get(short8, "")
    owner = owners_map.get(short8, "")
    kind = "session"
    if project or role_label.startswith("project_head-"):
        kind = "project_head"
        if not role_label:
            role_label = f"project_head-{short8}"
    elif task_match:
        kind = "worker"
        role_label = task_match.group(1)
        m_role = re.search(r"--([a-z0-9_-]+)--task-[0-9a-f]{8}", parent_name)
        if m_role:
            project = m_role.group(1)
    elif role_label:
        kind = "clevel"
    elif stem.startswith("d405e3e2"):
        kind = "clevel"
        role_label = "cto-fresh"
        project = "CTO Main"

    lines = _tail_lines(f, max_bytes=600000 if detailed else 180000)
    turns = []
    drained_mail = []
    skills_seen = set()
    quota_stopped = False
    last_ts = None
    cwd = None
    git_branch = None

    for ln in lines:
        try:
            obj = json.loads(ln)
        except ValueError:
            continue
        if not cwd and obj.get("cwd"):
            cwd = obj.get("cwd")
        if not git_branch and obj.get("gitBranch"):
            git_branch = obj.get("gitBranch")
        if obj.get("timestamp"):
            last_ts = obj.get("timestamp")
        t = obj.get("type")
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        role = msg.get("role")
        txt = _extract_text(msg.get("content"))

        # Detect skills referenced in tool uses or text
        for sm in re.findall(r"(?:ALL|CTO|CMO|CFO|CGO|COO|BROWSER_OPERATOR)_[A-Za-z0-9_.-]+|session-(?:open|close|merge)", ln):
            skills_seen.add(sm)

        if t == "api-request-blob" and "Mailbox —" in txt:
            drained_mail.append(txt.strip())
        elif t in ("user", "assistant") and txt.strip():
            low_t = txt.lower()
            if "hit your weekly limit" in low_t or "hit your usage limit" in low_t or "hit your 5-hour limit" in low_t:
                quota_stopped = True
            turns.append({"role": role or t, "text": txt.strip(), "ts": obj.get("timestamp")})

    mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    last_NonLimit = ""
    for tr in reversed(turns):
        low_tr = tr["text"].lower()
        if "hit your weekly limit" not in low_tr and "hit your 5-hour limit" not in low_tr and "hit your usage limit" not in low_tr:
            last_NonLimit = tr["text"].replace("\n", " ")[:180]
            break

    brief_text = ""
    brief_file = briefs_dir / f"project_head-{short8}.md"
    if brief_file.exists():
        try:
            brief_text = brief_file.read_text(encoding="utf-8", errors="replace")[:4000]
            for sm in re.findall(r"(?:ALL|CTO|CMO|CFO|CGO|COO|CXO|BROWSER_OPERATOR)_[A-Za-z0-9_.-]+|session-(?:open|close|merge)", brief_text):
                skills_seen.add(sm)
        except OSError:
            brief_text = ""

    info = {
        "uuid": stem,
        "short_id": short8,
        "kind": kind,
        "role_label": role_label or f"session-{short8}",
        "project": project or role_label or parent_name[-36:],
        "owner": owner,
        "jsonl_path": str(f),
        "cwd": cwd or str(agents_root),
        "git_branch": git_branch or "",
        "mtime": mtime,
        "last_ts": last_ts or mtime,
        "quota_stopped": quota_stopped,
        "last_summary": last_NonLimit,
        "skills": sorted(skills_seen),
        "drained_mailbox_count": len(drained_mail),
    }
    if detailed:
        info["recent_turns"] = turns[-max_turns:]
        info["drained_mailbox"] = drained_mail[-3:]
        info["brief"] = brief_text
        info["env_probe"] = _probe_env_readiness(info["cwd"])
    return info

all_jsonl = []
if claude_projects.exists():
    all_jsonl = sorted(claude_projects.rglob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)

if mode == "scan":
    limit = int(arg or "12")
    results = []
    seen_short = set()
    # Always include active project_head locks first, then most recent jsonl files
    for f in all_jsonl[:40]:
        s8 = f.stem[-8:]
        if s8 in projects_map or len(results) < limit:
            if s8 in seen_short:
                continue
            seen_short.add(s8)
            results.append(_summarize_jsonl(f, detailed=False))
            if len(results) >= limit and not (set(projects_map.keys()) - seen_short):
                break
    print(json.dumps({"agents_root": str(agents_root), "sessions": results}, ensure_ascii=True))
elif mode == "env":
    print(json.dumps(_probe_env_readiness(arg), ensure_ascii=True))
elif mode == "inspect":
    needle = arg.strip().lower()
    matched_file = None
    for f in all_jsonl:
        s8 = f.stem[-8:].lower()
        proj = projects_map.get(f.stem[-8:], "").lower()
        lbl = uuid_map.get(f.stem, "").lower()
        if (
            needle in f.stem.lower()
            or needle == s8
            or (proj and needle in proj)
            or (lbl and needle in lbl)
            or needle in f.parent.name.lower()
        ):
            matched_file = f
            break
    if not matched_file:
        print(json.dumps({"error": f"no session matching {arg!r} found"}, ensure_ascii=True))
    else:
        print(json.dumps(_summarize_jsonl(matched_file, detailed=True), ensure_ascii=True))
'''


# ---------------------------------------------------------------------------
# Transfer & Large-File Limits + Host-Affinity Registry
# ---------------------------------------------------------------------------

TRANSFER_LIMITS: dict[str, Any] = {
    "takeover_context_max_kb": 600,
    "takeover_brief_max_kb": 4,
    "project_files_copied_bytes": 0,
    "git_binary_max_mb": 1.0,
    "sparse_worktree_media_min_kb": 100,
    "work_dir_big_download_gb": 1.0,
    "keep_free_disk_gb": {
        "mac": 5.0,
        "contabo": 5.0,
        "winbox": 15.0,
    },
    "policy_summary": (
        "Takeover transfers ONLY the conversation state (~10-50 KB text, capped at 600 KB JSONL tail) "
        "and switches the brain/runner to AGY IN-PLACE on the original host. "
        "0 bytes of project files or media are copied across machines. "
        "Git commits block binaries > 1 MB and all media (.mp4/.png/.wav/.onnx) unless in .media-allow. "
        "Sparse worktrees skip tracked media > 100 KB. "
        "Large files (> 1 MB to multi-GB) stay in-place on their host (referenced by path pointer) "
        "or move via Google Drive / rclone bridge (CXO_Procedure_GDrive_BulkTransfer)."
    ),
}

# Host-pinned projects & workloads where moving to another machine is forbidden
# because the runtime, game client, MT5 terminal, IP address, or dataset only exists there.
HOST_AFFINITY_RULES: list[dict[str, Any]] = [
    {
        "match_keywords": ("cookierun", "cookierun-bot", "cookie-run"),
        "project_key": "cookierun-bot",
        "pinned_host": "winbox",
        "allowed_hosts": ("winbox",),
        "blocked_hosts": ("mac", "contabo"),
        "default_cwd": r"C:\Users\passg\cookierun-bot",
        "reason": (
            "CookieRun game client, Windows GUI capture, ONNX obstacle detector, "
            "and 1.44 GB training dataset (label_review/) exist ONLY on winbox "
            "(C:\\Users\\passg\\cookierun-bot). Never move execution to mac or contabo."
        ),
    },
    {
        "match_keywords": ("expertadvisor", "mooniex-expertadvisor", "mt5", "moonpulse", "moonx"),
        "project_key": "mooniex-expertadvisor",
        "pinned_host": "contabo",
        "runtime_host": "winbox",
        "allowed_hosts": ("contabo", "winbox"),
        "blocked_hosts": ("mac",),
        "default_cwd": "/opt/MoonieXHQ/Projects/MoonieX/ExpertAdvisor",
        "reason": (
            "EA MQL5 git repository lives on contabo (/opt/MoonieXHQ/Projects/MoonieX/ExpertAdvisor; "
            "config/hosts.yaml never_on blocks git worktrees on winbox), while MetaTrader 5 (MT5) "
            "compilation & live/backtest terminal run ONLY on winbox via scp+ssh."
        ),
    },
    {
        "match_keywords": ("mooniex-option", "iqoption", "iq-option"),
        "project_key": "mooniex-option",
        "pinned_host": "winbox",
        "allowed_hosts": ("winbox", "contabo", "mac"),
        "blocked_hosts": (),
        "default_cwd": "/opt/MoonieXHQ/Projects/MoonieX/Option",
        "reason": (
            "IQ Option live trader MUST run on winbox (residential IP required; broker bans "
            "Contabo datacenter IP). Signal listener/channel runs on contabo."
        ),
    },
    {
        "match_keywords": (
            "mooniex-console",
            "sompong",
            "mooniex-sompong",
            "cndrama",
            "champaveo",
            "khaohomsurvival",
            "blackliquidity",
            "mimipage",
        ),
        "project_key": "contabo-service-or-ph",
        "pinned_host": "contabo",
        "allowed_hosts": ("contabo",),
        "blocked_hosts": ("winbox",),
        "default_cwd": "/opt/MoonieXHQ/Agents/Core",
        "reason": (
            "Project Head state, 24/7 systemd services, ffmpeg, rclone Drive bridge, "
            "and Browser Homes (9280/9281/9224) are provisioned on contabo (/opt/MoonieXHQ)."
        ),
    },
    {
        "match_keywords": ("claudesign", "mooniex-claudesign", "blender"),
        "project_key": "mac-gui-or-design",
        "pinned_host": "mac",
        "allowed_hosts": ("mac",),
        "blocked_hosts": ("contabo", "winbox"),
        "default_cwd": "/Users/gob/MoonieXHQ",
        "reason": "Blender bridge, macOS Computer Use, and ClaudeSign live on mac.",
    },
]


def resolve_host_affinity(project: str, cwd: str = "", source_host: str = "") -> dict[str, Any]:
    """Return the host-affinity policy for `project` / `cwd` / `source_host`.

    Every takeover defaults to `stay_on_host=True` on `source_host` so a worker never
    moves to an unprovisioned machine and never reinstalls packages from scratch.
    """
    haystack = f"{project or ''} {cwd or ''}".lower()
    for rule in HOST_AFFINITY_RULES:
        if any(kw in haystack for kw in rule["match_keywords"]):
            pinned = rule["pinned_host"]
            # If the session was already running on an allowed host (e.g. winbox for EA runtime),
            # keep it pinned to that exact host.
            effective_host = source_host if (source_host and source_host in rule["allowed_hosts"]) else pinned
            return {
                "stay_on_host": True,
                "project_key": rule["project_key"],
                "pinned_host": effective_host,
                "runtime_host": rule.get("runtime_host") or effective_host,
                "default_cwd": rule.get("default_cwd") or "",
                "allowed_hosts": list(rule["allowed_hosts"]),
                "blocked_hosts": list(rule["blocked_hosts"]),
                "reason": rule["reason"],
                "explicit_pin": True,
            }

    effective = (source_host or "contabo").lower()
    return {
        "stay_on_host": True,
        "project_key": project or "session",
        "pinned_host": effective,
        "runtime_host": effective,
        "default_cwd": cwd or "",
        "allowed_hosts": [effective],
        "blocked_hosts": [h for h in HOSTS if h != effective],
        "reason": (
            f"Session originated on '{effective}' at '{cwd or '(host root)'}' where its "
            f"worktree, .venv, and packages are already installed. Stay on '{effective}' "
            f"(switch Runner to AGY in-place; do NOT copy repo or reinstall packages on another host)."
        ),
        "explicit_pin": False,
    }


def evaluate_preflight(
    info: dict[str, Any],
    *,
    requested_host: str | None = None,
) -> dict[str, Any]:
    """Verify Host-Affinity + In-Place Environment Readiness + Transfer Limits before resuming work."""
    source_host = (info.get("host") or "").lower().strip()
    project = str(info.get("project") or info.get("role_label") or "")
    cwd = str(info.get("cwd") or "")
    affinity = resolve_host_affinity(project=project, cwd=cwd, source_host=source_host)
    pinned_host = affinity["pinned_host"]

    # If a Project Head coordinator on Contabo manages a host-pinned project (e.g. CookieRun on winbox),
    # the execution host is `pinned_host` unless an explicit `requested_host` was passed.
    effective_source_host = (
        pinned_host
        if (affinity.get("explicit_pin") and source_host not in affinity["allowed_hosts"])
        else (source_host or pinned_host)
    )
    effective_cwd = (
        affinity.get("default_cwd") or cwd
        if effective_source_host != source_host
        else (cwd or affinity.get("default_cwd") or "")
    )
    target_host = (requested_host or effective_source_host).lower().strip()

    # 1. Check Host-Affinity (block cross-host drift to unprepared machines)
    wrong_host = False
    block_reasons: list[str] = []
    if target_host in affinity["blocked_hosts"] or (
        affinity["allowed_hosts"] and target_host not in affinity["allowed_hosts"]
    ):
        wrong_host = True
        block_reasons.append(
            f"Host-Affinity Violation: '{project}' is pinned to {affinity['allowed_hosts']} "
            f"(requested '{target_host}'). {affinity['reason']}"
        )
    elif effective_source_host and target_host != effective_source_host:
        wrong_host = True
        block_reasons.append(
            f"Cross-Host Drift Blocked: Session #{info.get('short_id')} belongs to '{effective_source_host}' "
            f"at '{effective_cwd}', not '{target_host}'. Takeover must switch the Brain/Runner to AGY "
            f"IN-PLACE on '{effective_source_host}' so no packages or dependencies are reinstalled from 0."
        )

    # 2. Probe environment readiness on the pinned/source host
    probe_host = effective_source_host
    env_probe = info.get("env_probe") if effective_source_host == source_host else None
    if not isinstance(env_probe, dict) or not env_probe.get("cwd"):
        probe_res = _run_probe_on_host(probe_host, "env", effective_cwd)
        env_probe = probe_res if probe_res.get("ok") else {
            "cwd": effective_cwd,
            "cwd_exists": False,
            "git_ready": False,
            "venv_python": "",
            "node_modules_ready": False,
            "disk_free_gb": -1.0,
            "tools": {},
            "local_large_items": [],
        }

    min_disk = TRANSFER_LIMITS["keep_free_disk_gb"].get(probe_host, 5.0)
    disk_free = float(env_probe.get("disk_free_gb", -1.0))
    disk_ok = (disk_free < 0) or (disk_free >= min_disk)
    cwd_ok = bool(env_probe.get("cwd_exists", False))
    node_ok = bool(env_probe.get("node_modules_ready", True))

    if not cwd_ok:
        block_reasons.append(
            f"Working directory '{effective_cwd}' does not exist on host '{probe_host}' — "
            f"refusing to start in an unprovisioned directory."
        )
    if not disk_ok:
        block_reasons.append(
            f"Disk free space on '{probe_host}' is {disk_free} GB (below safety floor {min_disk} GB)."
        )

    if wrong_host:
        status = "BLOCKED_WRONG_HOST"
        ready = False
    elif not cwd_ok or not disk_ok:
        status = "MISSING_ENV"
        ready = False
    else:
        status = "READY"
        ready = True

    venv_py = env_probe.get("venv_python") or "python3"
    no_reinstall_rule = (
        f"HARD RULE (STAY ON '{probe_host.upper()}' / ZERO PACKAGE REINSTALL): "
        f"Execute all commands IN-PLACE on host '{probe_host}' inside '{effective_cwd}'. "
        f"Use pre-installed Python '{venv_py}'"
        + (" and existing 'node_modules'." if env_probe.get("has_package_json") and node_ok else ".")
        + " NEVER copy this project to another host and NEVER run pip install / npm install from scratch."
    )

    return {
        "status": status,
        "ready": ready,
        "source_host": probe_host,
        "requested_host": target_host,
        "pinned_host": pinned_host,
        "stay_on_host": True,
        "affinity": affinity,
        "env": env_probe,
        "disk_ok": disk_ok,
        "min_disk_free_gb": min_disk,
        "block_reasons": block_reasons,
        "no_reinstall_rule": no_reinstall_rule,
        "transfer_limits": TRANSFER_LIMITS,
    }


def _run_probe_on_host(host: str, mode: str, arg: str = "", max_turns: int = 10) -> dict[str, Any]:
    """Run `_REMOTE_PROBE_PY` on `mac`, `contabo`, or `winbox` and return parsed JSON."""
    host = host.lower().strip()
    try:
        if host == "mac":
            cmd = [sys.executable, "-c", _REMOTE_PROBE_PY, mode, str(arg), str(max_turns)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        elif host == "contabo":
            cmd = [
                "ssh",
                "-o",
                "ConnectTimeout=6",
                "-o",
                "BatchMode=yes",
                "mooniex-vps",
                "python3",
                "-",
                mode,
                str(arg),
                str(max_turns),
            ]
            proc = subprocess.run(cmd, input=_REMOTE_PROBE_PY, capture_output=True, text=True, timeout=20)
        elif host == "winbox":
            cmd = [
                "ssh",
                "-o",
                "ConnectTimeout=6",
                "-o",
                "BatchMode=yes",
                "winbox",
                r"C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe",
                "-",
                mode,
                str(arg),
                str(max_turns),
            ]
            proc = subprocess.run(cmd, input=_REMOTE_PROBE_PY, capture_output=True, text=True, timeout=20)
        else:
            return {"host": host, "ok": False, "error": f"unknown host {host!r}"}

        if proc.returncode != 0:
            return {"host": host, "ok": False, "error": (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()[:300]}
        out = (proc.stdout or "").strip()
        data = json.loads(out)
        data["host"] = host
        data["ok"] = "error" not in data
        return data
    except Exception as exc:  # noqa: BLE001
        return {"host": host, "ok": False, "error": str(exc)[:300]}


def resolve_local_skill_paths(skill_names: list[str]) -> list[dict[str, str]]:
    """Map skill names used by a Claude session to local `.claude/skills/<name>/SKILL.md` paths."""
    resolved = []
    for name in skill_names:
        skill_md = SKILLS_DIR / name / "SKILL.md"
        if skill_md.is_file():
            resolved.append({"name": name, "path": str(skill_md)})
    return resolved


def scan_all_hosts(hosts: tuple[str, ...] = HOSTS, limit_per_host: int = 10) -> dict[str, Any]:
    """Scan Mac, Contabo, and Winbox in parallel for active/stalled Claude Code sessions."""
    with ThreadPoolExecutor(max_workers=len(hosts)) as pool:
        futures = {h: pool.submit(_run_probe_on_host, h, "scan", str(limit_per_host)) for h in hosts}
    host_results = {h: futures[h].result() for h in hosts}
    flat_sessions = []
    for h, res in host_results.items():
        for s in res.get("sessions") or []:
            s["host"] = h
            flat_sessions.append(s)
    return {
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hosts": host_results,
        "sessions": flat_sessions,
    }


def inspect_target(target: str, *, host: str | None = None, max_turns: int = 12) -> dict[str, Any]:
    """Find and extract the full context of a Claude Code session matching `target` across hosts."""
    search_hosts = (host.lower(),) if host and host.lower() in HOSTS else ("contabo", "mac", "winbox")
    for h in search_hosts:
        res = _run_probe_on_host(h, "inspect", target, max_turns=max_turns)
        if res.get("ok"):
            res["resolved_skills"] = resolve_local_skill_paths(res.get("skills") or [])
            res["preflight"] = evaluate_preflight(res)
            return res
    raise LookupError(f"Could not find any Claude Code session matching {target!r} on {search_hosts}")


def format_handoff_markdown(info: dict[str, Any]) -> str:
    """Format an inspected Claude Code session into a structured markdown handoff brief for AGY."""
    preflight = info.get("preflight")
    if not isinstance(preflight, dict):
        preflight = evaluate_preflight(info)
    env = preflight.get("env") or {}
    affinity = preflight.get("affinity") or {}

    lines = [
        f"# Emergency AGY Takeover Brief: {info.get('project')} ({info.get('role_label')})",
        "",
        f"- **Source Host:** `{info.get('host')}`",
        f"- **Claude Session UUID:** `{info.get('uuid')}` (`#{info.get('short_id')}`)",
        f"- **Role / Kind:** `{info.get('kind')}` / `{info.get('role_label')}`",
        f"- **Owner:** `{info.get('owner') or '(primary/direct)'}`",
        f"- **Working Directory:** `{info.get('cwd')}`",
        f"- **Git Branch:** `{info.get('git_branch') or 'main'}`",
        f"- **Quota Stopped (`weekly limit`):** `{info.get('quota_stopped')}`",
        f"- **Last Activity:** `{info.get('last_ts')}`",
        "",
        "## 🛡️ Host-Affinity & Pre-Flight Environment Readiness (NO Package Reinstall)",
        f"- **Pre-Flight Status:** `{preflight.get('status')}` (Ready: `{preflight.get('ready')}`)",
        f"- **Pinned Host (`stay_on_host`):** `{preflight.get('pinned_host')}` (Allowed: `{affinity.get('allowed_hosts')}`)",
        f"- **Host-Affinity Reason:** {affinity.get('reason')}",
        f"- **In-Place Directory Ready:** `{env.get('cwd_exists')}` (`{env.get('cwd') or info.get('cwd')}`)",
        f"- **Pre-Installed Python (`.venv`):** `{env.get('venv_python') or 'python3'}`",
        f"- **Pre-Installed `node_modules` Ready:** `{env.get('node_modules_ready', True)}`",
        f"- **Disk Free Space:** `{env.get('disk_free_gb', 'unknown')} GB` (Safety floor: `{preflight.get('min_disk_free_gb')} GB`)",
        f"- **Execution Rule:** **{preflight.get('no_reinstall_rule')}**",
    ]
    if env.get("local_large_items"):
        lines.append(f"- **In-Place Large/Data Items (Keep on `{info.get('host')}` — DO NOT copy):** `{', '.join(env['local_large_items'])}`")
    if preflight.get("block_reasons"):
        for br in preflight["block_reasons"]:
            lines.append(f"- **⚠️ BLOCKED:** {br}")
    lines.extend([
        "",
        "## 📦 Transfer & Large-File Limits (Pointer-Only / Zero File Copy)",
        f"- **Takeover Context Limit:** `<= {TRANSFER_LIMITS['takeover_context_max_kb']} KB` JSONL tail + `<= {TRANSFER_LIMITS['takeover_brief_max_kb']} KB` brief (`0 bytes` of project files or media copied across hosts).",
        f"- **Git Commit Binary/Media Limit:** `<= {TRANSFER_LIMITS['git_binary_max_mb']} MB` per binary; all media extensions (`.mp4`, `.mov`, `.png`, `.wav`, `.onnx`) blocked unless listed in `.media-allow`.",
        f"- **Sparse Worktree Filter (`ADR 0030`):** Tracked media `> {TRANSFER_LIMITS['sparse_worktree_media_min_kb']} KB` automatically skipped on worker checkout.",
        f"- **Large Files (`> 1 MB` to multi-GB):** Keep in-place on `{info.get('host')}` (`~/MoonieXHQ/Work/<task>/` or project data dir) and reference by path pointer, or transfer deliverables via Google Drive / `rclone` (`CXO_Procedure_GDrive_BulkTransfer`).",
        "",
    ])

    if info.get("resolved_skills"):
        lines.append("## Active Claude Skills (Available Natively in AGY)")
        for sk in info["resolved_skills"]:
            lines.append(f"- **`{sk['name']}`**: `{sk['path']}`")
        lines.append("")

    if info.get("brief"):
        lines.extend([
            "## Original Session Brief",
            "```markdown",
            info["brief"].strip(),
            "```",
            "",
        ])

    if info.get("drained_mailbox"):
        lines.extend([
            "## ⚠️ Drained Mailbox Messages (Arrived Right Before Quota Stop)",
        ])
        for idx, mb in enumerate(info["drained_mailbox"], 1):
            lines.extend([
                f"### Mailbox Delivery {idx}",
                "```text",
                mb[:2500],
                "```",
            ])
        lines.append("")

    lines.append("## Recent Conversation Turns (Before Takeover)")
    for idx, tr in enumerate(info.get("recent_turns") or [], 1):
        role = tr.get("role", "turn").upper()
        ts = tr.get("ts") or ""
        text = (tr.get("text") or "").strip()
        if len(text) > 1200:
            text = text[:1200] + "\n...[truncated]..."
        lines.extend([
            f"### Turn {idx} — `{role}` ({ts})",
            "```text",
            text,
            "```",
            "",
        ])

    lines.extend([
        "## How to Execute Next Steps from AGY",
        f"- **If work is on `mac`**: edit/run directly in `{info.get('cwd')}` using `{env.get('venv_python') or 'python3'}`.",
        f"- **If work is on `contabo`**: run commands in-place via `ssh mooniex-vps 'cd {info.get('cwd')} && ...'` or delegate via `python3 tools/ph_brain.py`.",
        f"- **If work is on `winbox`**: run commands in-place via `ssh winbox` inside `{info.get('cwd')}` using `{env.get('venv_python') or 'python'}`.",
        "- **Read any listed Claude Skill (`SKILL.md`) above** before executing specialized gates or procedures.",
    ])
    return "\n".join(lines) + "\n"


def save_handoff_bundle(info: dict[str, Any], takeover_dir: Path | None = None) -> Path:
    base = Path(takeover_dir or TAKEOVER_DIR)
    base.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{info.get('host')}-{info.get('project')}-{info.get('short_id')}").strip("-")
    out_path = base / f"{slug}.md"
    latest_path = base / "latest-handoff.md"
    md = format_handoff_markdown(info)
    out_path.write_text(md, encoding="utf-8")
    latest_path.write_text(md, encoding="utf-8")
    return out_path


def resume_in_place(
    target: str,
    *,
    host: str | None = None,
    target_host: str | None = None,
    message: str = "สรุปงานค้างจาก Claude Code session นี้ แล้วทำ Step ถัดไปต่อทันทีในโฟลเดอร์เดิมโดยห้ามลงแพ็กเกจใหม่",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Verify pre-flight readiness & host-affinity, then resume the session IN-PLACE on its native host."""
    info = inspect_target(target, host=host, max_turns=12)
    preflight = evaluate_preflight(info, requested_host=target_host)
    info["preflight"] = preflight
    if not preflight["ready"]:
        reasons = "; ".join(preflight["block_reasons"]) or preflight["status"]
        raise ValueError(f"Pre-flight check failed [{preflight['status']}]: {reasons}")

    bundle_path = save_handoff_bundle(info)
    source_host = preflight["source_host"]
    cwd = info.get("cwd") or ""
    venv_py = (preflight.get("env") or {}).get("venv_python") or "python3"
    no_reinstall = preflight["no_reinstall_rule"]

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "target": target,
            "source_host": source_host,
            "cwd": cwd,
            "venv_python": venv_py,
            "status": preflight["status"],
            "no_reinstall_rule": no_reinstall,
            "bundle_path": str(bundle_path),
        }

    # For Contabo Project Heads (or any Contabo session), run via ph_brain on Contabo/local bridge
    from tools import ph_brain
    handoff_md = bundle_path.read_text(encoding="utf-8")
    prompt = (
        f"คุณกำลังรับช่วงงานต่อ (Emergency In-Place Takeover) บนเครื่อง `{source_host}`:\n"
        f"{no_reinstall}\n\n"
        f"{handoff_md}\n\n"
        f"--- คำสั่งปัจจุบัน ---\n{message}"
    )
    res = ph_brain.run_turn(
        ph_id=info["short_id"],
        project=info.get("project") or info["short_id"],
        lane="cto",
        owner=info.get("owner") or None,
        message=prompt,
    )
    return {
        "ok": True,
        "dry_run": False,
        "target": target,
        "source_host": source_host,
        "cwd": cwd,
        "venv_python": venv_py,
        "status": preflight["status"],
        "bundle_path": str(bundle_path),
        "brain_result": res,
    }


def print_scan_table(scan_data: dict[str, Any]) -> None:
    print(f"=== AGY Emergency Takeover Scan ({scan_data['scanned_at']}) ===")
    for h, hres in scan_data["hosts"].items():
        if not hres.get("ok"):
            print(f"[{h.upper()}] ⚠️ offline/error: {hres.get('error')}")
            continue
        sessions = hres.get("sessions") or []
        print(f"\n[{h.upper()}] ({len(sessions)} recent sessions)")
        print(f"  {'ID':<10} {'KIND':<13} {'PROJECT / ROLE':<24} {'STOPPED?':<10} {'SKILLS':<6} {'LAST ACTIVITY'}")
        print(f"  {'-'*10} {'-'*13} {'-'*24} {'-'*10} {'-'*6} {'-'*45}")
        for s in sessions:
            stopped = "🚨 LIMIT" if s.get("quota_stopped") else "ok"
            sk_cnt = str(len(s.get("skills") or []))
            proj = (s.get("project") or "")[:24]
            summary = (s.get("last_summary") or "")[:65]
            print(f"  {s['short_id']:<10} {s['kind']:<13} {proj:<24} {stopped:<10} {sk_cnt:<6} {summary}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Scan Mac, Contabo, and Winbox for stalled Claude Code sessions")
    p_scan.add_argument("--host", choices=("all", "mac", "contabo", "winbox"), default="all")
    p_scan.add_argument("--limit", type=int, default=10)
    p_scan.add_argument("--json", action="store_true")

    p_insp = sub.add_parser("inspect", help="Extract full context, mailbox, and skills from a Claude Code session")
    p_insp.add_argument("target", help="Project name (e.g. CnDrama), session id (e.g. 3511068d), or task id")
    p_insp.add_argument("--host", choices=("mac", "contabo", "winbox"))
    p_insp.add_argument("--turns", type=int, default=12)
    p_insp.add_argument("--save", action="store_true", help="Save markdown handoff bundle to state/takeover/")
    p_insp.add_argument("--json", action="store_true")

    p_pre = sub.add_parser("preflight", help="Check Host-Affinity, In-Place Environment Readiness, and Transfer Limits")
    p_pre.add_argument("target", help="Project name (e.g. CookieRun, CnDrama) or session id")
    p_pre.add_argument("--host", choices=("mac", "contabo", "winbox"), help="Host to search session on")
    p_pre.add_argument("--target-host", choices=("mac", "contabo", "winbox"), help="Verify if moving to this host is allowed")
    p_pre.add_argument("--json", action="store_true")

    p_res = sub.add_parser("resume", help="Verify pre-flight readiness and resume session IN-PLACE on its native host")
    p_res.add_argument("target", help="Project name or session id")
    p_res.add_argument("--host", choices=("mac", "contabo", "winbox"))
    p_res.add_argument("--target-host", choices=("mac", "contabo", "winbox"))
    p_res.add_argument("--message", default="สรุปงานค้างจาก Claude Code session นี้ แล้วทำ Step ถัดไปต่อทันทีในโฟลเดอร์เดิมโดยห้ามลงแพ็กเกจใหม่")
    p_res.add_argument("--dry-run", action="store_true")
    p_res.add_argument("--json", action="store_true")

    p_hand = sub.add_parser("handoff-to-brain", help="Import a stalled Claude Code session directly into AGY ph_brain.py")
    p_hand.add_argument("target", help="Project name or session id to import into tools/ph_brain.py")
    p_hand.add_argument("--host", choices=("mac", "contabo", "winbox"))
    p_hand.add_argument("--message", default="สรุปงานค้างจาก Claude Code session นี้ แล้วบอก Step ถัดไปที่ต้องทำต่อทันที")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "scan":
            hosts = HOSTS if args.host == "all" else (args.host,)
            data = scan_all_hosts(hosts=hosts, limit_per_host=args.limit)
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print_scan_table(data)
            return 0

        if args.cmd == "inspect":
            info = inspect_target(args.target, host=args.host, max_turns=args.turns)
            saved_path = save_handoff_bundle(info) if args.save else None
            if args.json:
                if saved_path:
                    info["saved_bundle"] = str(saved_path)
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print(format_handoff_markdown(info))
                if saved_path:
                    print(f"\n[Saved handoff bundle to: {saved_path}]")
            return 0

        if args.cmd == "preflight":
            try:
                info = inspect_target(args.target, host=args.host, max_turns=4)
            except LookupError:
                # Allow preflight by project keyword (e.g. CookieRun, ExpertAdvisor) even without a live session
                aff = resolve_host_affinity(args.target, source_host=args.host or "")
                probe_host = args.host or aff["pinned_host"]
                default_cwd = ""
                for r in HOST_AFFINITY_RULES:
                    if r["project_key"] == aff["project_key"]:
                        default_cwd = r.get("default_cwd", "")
                        break
                env_res = _run_probe_on_host(probe_host, "env", default_cwd)
                info = {
                    "host": probe_host,
                    "short_id": "preflight",
                    "project": args.target,
                    "role_label": args.target,
                    "cwd": env_res.get("cwd") or default_cwd,
                    "env_probe": env_res if env_res.get("ok") else {},
                }
            pf = evaluate_preflight(info, requested_host=args.target_host)
            if args.json:
                print(json.dumps(pf, indent=2, ensure_ascii=False))
            else:
                print(f"=== Pre-Flight Readiness & Host-Affinity Check: {info.get('project')} ===")
                print(f"Status          : {pf['status']} (Ready={pf['ready']})")
                print(f"Source/Pinned   : {pf['source_host']} (Requested={pf['requested_host']})")
                print(f"Working Dir     : {pf['env'].get('cwd')} (Exists={pf['env'].get('cwd_exists')})")
                print(f"Pre-installed Py: {pf['env'].get('venv_python')}")
                print(f"Disk Free       : {pf['env'].get('disk_free_gb')} GB (Min={pf['min_disk_free_gb']} GB)")
                print(f"Affinity Reason : {pf['affinity'].get('reason')}")
                print(f"Execution Rule  : {pf['no_reinstall_rule']}")
                if pf["block_reasons"]:
                    for br in pf["block_reasons"]:
                        print(f"❌ BLOCKED      : {br}")
            return 0 if pf["ready"] else 2

        if args.cmd == "resume":
            res = resume_in_place(
                args.target,
                host=args.host,
                target_host=args.target_host,
                message=args.message,
                dry_run=args.dry_run,
            )
            if args.json:
                print(json.dumps(res, indent=2, ensure_ascii=False))
            elif args.dry_run:
                print(
                    f"[READY DRY-RUN] Target={res['target']} | Host={res['source_host']} | "
                    f"CWD={res['cwd']} | Python={res['venv_python']}\n{res['no_reinstall_rule']}"
                )
            else:
                br = res["brain_result"]
                print(
                    f"[In-Place Takeover -> PH#{br['ph_id']} ({br['project']}) on {res['source_host']} | "
                    f"model={br['model_used']} | conv={br['conversation_id']} | claude_code=0 tok]\n{br['response']}"
                )
            return 0

        if args.cmd == "handoff-to-brain":
            res = resume_in_place(
                args.target,
                host=args.host,
                message=args.message,
                dry_run=False,
            )
            br = res["brain_result"]
            print(
                f"[Takeover -> PH#{br['ph_id']} ({br['project']}) | model={br['model_used']} | "
                f"conv={br['conversation_id']} | claude_code=0 tok]\n{br['response']}"
            )
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"agy_takeover error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
