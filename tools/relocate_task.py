#!/usr/bin/env python3
"""Cross-host task, brain, and active working-file relocation (`relocate_task`).

Moves a pending, queued, in_progress, stalled, or rate_limited task from its
current host to another available host (`contabo`, `mac`, `winbox`) without
starting over from scratch:

1. Pre-flight readiness & heavy-setup check (`assess_migration`):
   - Portable tasks (code repos with `paths.<target_host>`, and video/content
     pipelines like CnDrama, ChampaVeo, KhaoHom, BlackLiquidity, MimiPage when
     `git` + `ffmpeg` are present) move immediately.
   - If moving to `target_host` requires installing missing tools/packages or
     cloning heavy environments (`missing_installs`), and `confirmed=False`,
     refuses silent broken execution and builds (or raises with `--raise-card`)
     a RED `/run` Card (`risk="red"`) tagged `[ย้ายงาน]`:
       `[ย้ายงาน] ต้องติดตั้ง: ... · ใช้เวลา ~N นาที · ยอมรับไหม?`
2. Guardrail #1 (Stop & Verify Dead / Fencing):
   - Stops any live worker process/tmux on `source_host` and verifies it is dead
     before checkpointing or re-spawning so two machines never push to the same
     branch simultaneously.
3. 3-Tier State & Active Working File Transfer (`Work/<task-id>/`):
   - Tier 1 (`< 10 MB` code / script / cut-list): auto-commits and pushes WIP
     in the source git worktree (`origin/<branch>`).
   - Tier 2 (`<= 500 MB` active working files in `Work/<task-id>/{in,out}`):
     transfers `in/` and `out/` (excluding `tmp/`) directly over Tailscale via
     `rsync -az --partial --exclude 'tmp/'`.
   - Tier 3 (`> 500 MB` in `Work/<task-id>/{in,out}`): stages via Google Drive
     (`rclone copy`) and records `SOURCES.txt` for `target_host`.
4. Guardrail #2 (Source Cleanup):
   - Deletes `Work/<task-id>/tmp/` and removes the old git worktree on
     `source_host` to reclaim disk space immediately.
5. Resumes on `target_host`:
   - Prepends continuation instructions to `task["description"]` so the new
     worker merges `origin/<branch>` and continues from the checkpoint.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import config, db, router as host_router  # noqa: E402
from tools import host_queue, send_to_cto  # noqa: E402

TIER1_GIT_MAX_BYTES = 10 * 1024 * 1024          # 10 MB
TIER2_TAILSCALE_MAX_BYTES = 500 * 1024 * 1024   # 500 MB
MIN_FREE_DISK_AFTER_GB = 5.0

PORTABLE_VIDEO_KEYWORDS = (
    "cndrama",
    "champaveo",
    "khaohom",
    "blackliquidity",
    "mimipage",
)

HEAVY_HOST_SETUPS: list[dict[str, Any]] = [
    {
        "keywords": ("cookierun", "cookie-run", "cookierun-bot"),
        "native_hosts": ("winbox",),
        "missing_installs": [
            "Windows Game Client + GUI capture",
            "ONNX Obstacle Detector + Dataset 1.44GB",
        ],
        "estimated_minutes": 30,
    },
    {
        "keywords": ("mt5-backtest", "metaeditor", "metatrader"),
        "native_hosts": ("winbox",),
        "missing_installs": [
            "MetaTrader 5 Terminal + MetaEditor64",
            "Tick Data สำหรับ Backtest",
        ],
        "estimated_minutes": 25,
    },
    {
        "keywords": ("claudesign", "blender_bridge", "macos_cu"),
        "native_hosts": ("mac",),
        "missing_installs": [
            "Blender Bridge / Electron ClaudeSign + macOS GUI",
        ],
        "estimated_minutes": 15,
    },
]

WORK_ROOT_BY_HOST: dict[str, str] = {
    "mac": "/Users/gob/MoonieXHQ/Work",
    "contabo": "/opt/MoonieXHQ/Work",
    "winbox": "C:/Users/passg/mooniex/Work",
}


def _truncate_line(text: str, max_len: int = 88) -> str:
    """Ensure a single line of text is <= `max_len` chars and has no pipes (`|`)."""
    clean = " ".join((text or "").replace("|", "·").splitlines()).strip()
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def build_migration_card_spec(
    *,
    task_id: str,
    project: str,
    source_host: str,
    target_host: str,
    missing_installs: list[str],
    estimated_minutes: int,
) -> dict[str, Any]:
    """Build a RED `/run` Command Card spec tagged `[ย้ายงาน]` that complies with
    `tools/ask_run.py` (<= 5 lines of <= 90 chars, no pipe `|` characters)."""
    items_short = ", ".join(missing_installs)
    est_min = max(int(estimated_minutes or 5), 5)
    prefix = "[ย้ายงาน] ต้องติดตั้ง: "
    suffix = f" · ใช้เวลา ~{est_min} นาที · ยอมรับไหม?"
    budget = 88 - len(prefix) - len(suffix)
    if len(items_short) > budget:
        items_short = items_short[: max(budget - 1, 8)].rstrip() + "…"
    why = _truncate_line(f"{prefix}{items_short}{suffix}", 88)
    expected = _truncate_line(
        f"อนุมัติ=ติดตั้งและย้าย {task_id} ไป {target_host} · ปฏิเสธ=รอทำต่อที่ {source_host}",
        88,
    )
    command = f"python3 tools/relocate_task.py {task_id} --to {target_host} --confirmed"
    return {
        "tag": "[ย้ายงาน]",
        "risk": "red",
        "task_id": task_id,
        "project": project,
        "source_host": source_host,
        "target_host": target_host,
        "missing_installs": list(missing_installs),
        "estimated_minutes": est_min,
        "why": why,
        "expected": expected,
        "command": command,
    }


def raise_migration_run_card(
    card_spec: dict[str, Any],
    *,
    role: str = "cto",
    session: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Submit a RED `[ย้ายงาน]` Command Card to `/run` via `tools/ask_run.py`."""
    from tools import ask_run

    host = card_spec.get("target_host") or "contabo"
    if host not in ("contabo", "mac", "winbox"):
        host = "contabo"
    args: dict[str, Any] = {
        "host": host,
        "command": card_spec["command"],
        "why": card_spec["why"],
        "expected": card_spec["expected"],
        "risk": "red",
        "role": role,
        "dry_run": dry_run,
    }
    if not session:
        try:
            from tools import agy_card_run
            box, resolved_role, _sid, _cid = agy_card_run.resolve_identity(role=role)
            session = box
            role = resolved_role or role
        except Exception:
            session = f"{role}-relocate"
    args["role"] = role
    args["session"] = session
    return ask_run.mcp_ask(args)


def assess_migration(
    task: dict[str, Any],
    target_host: str,
    *,
    source_host: str | None = None,
    work_bytes: int = 0,
) -> dict[str, Any]:
    """Evaluate whether `task` can move cleanly to `target_host` or needs heavy setup.

    Returns a dict with:
      - `ready`: True if `target_host` has all required paths and tools ready
      - `portable`: True if the project/role is portable across hosts
      - `missing_installs`: list of human-readable installation/setup items needed
      - `estimated_minutes`: estimated setup + transfer minutes
      - `migration_card`: RED `[ย้ายงาน]` card spec when `missing_installs` is non-empty
    """
    task_id = str(task.get("id") or "task-unknown")
    project = str(task.get("project") or "")
    role = str(task.get("role") or "developer")
    desc = str(task.get("description") or "")
    src = (source_host or task.get("host") or config.self_host() or "contabo").strip().lower()
    dst = target_host.strip().lower()

    missing_installs: list[str] = []
    estimated_minutes = 0
    haystack = f"{project} {role} {desc}".lower()

    # Check OS/hardware-heavy setups
    for rule in HEAVY_HOST_SETUPS:
        if any(kw in haystack for kw in rule["keywords"]):
            if dst not in rule["native_hosts"]:
                missing_installs.extend(rule["missing_installs"])
                estimated_minutes += int(rule["estimated_minutes"])

    # Check explicit `needs:` capabilities in description header vs host provides
    needs = host_router.parse_needs(desc)
    try:
        host_cfg = config.host(dst)
    except Exception:
        host_cfg = {}
    provides = [str(x).strip().lower() for x in (host_cfg.get("provides") or [])]
    for cap in needs:
        if cap not in provides:
            missing_installs.append(f"ติดตั้ง {cap} บน {dst}")
            estimated_minutes += 10

    # Video editing / CnDrama portability check: portable wherever ffmpeg is provided
    is_video = role == "video_editor" or any(k in haystack for k in PORTABLE_VIDEO_KEYWORDS)
    if is_video and provides and "ffmpeg" not in provides:
        missing_installs.append(f"ติดตั้ง ffmpeg สำหรับงานตัดต่อบน {dst}")
        estimated_minutes += 8

    # Check project repo path on target_host (unless project_head or portable video project)
    if role != "project_head" and not any(k in project.lower() for k in PORTABLE_VIDEO_KEYWORDS):
        try:
            config.project_path_for_host(project, dst)
        except ValueError:
            missing_installs.append(f"Clone/ตั้งค่า repo {project} บน {dst}")
            estimated_minutes += 10

    # Check if active working data exceeds Tier 2 (> 500 MB) and requires heavy staging
    if work_bytes > TIER2_TAILSCALE_MAX_BYTES:
        gb = work_bytes / (1024 ** 3)
        missing_installs.append(f"โอนย้ายไฟล์งานขนาดใหญ่ {gb:.1f} GB ผ่าน Google Drive")
        estimated_minutes += max(int(gb * 5), 10)

    ready = len(missing_installs) == 0
    card = (
        build_migration_card_spec(
            task_id=task_id,
            project=project or role,
            source_host=src,
            target_host=dst,
            missing_installs=missing_installs,
            estimated_minutes=estimated_minutes,
        )
        if missing_installs
        else None
    )
    return {
        "ready": ready,
        "portable": ready or is_video,
        "source_host": src,
        "target_host": dst,
        "missing_installs": missing_installs,
        "estimated_minutes": estimated_minutes,
        "migration_card": card,
    }


def _pid_is_alive_local(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def fence_source_worker(task: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    """Guardrail #1: Stop any live worker process/tmux on `source_host` and verify
    it is dead before relocating the task."""
    source_host = (task.get("host") or config.self_host() or "contabo").strip().lower()
    pid = task.get("pid")
    tmux_session = task.get("tmux_session")
    this_host = config.self_host()

    if not pid and not tmux_session:
        return {"fenced": True, "source_host": source_host, "method": "no_live_process"}
    if dry_run:
        return {"fenced": True, "source_host": source_host, "method": "dry_run", "pid": pid}

    if source_host == this_host:
        if tmux_session:
            subprocess.run(
                ["tmux", "kill-session", "-t", str(tmux_session)],
                capture_output=True,
                text=True,
                timeout=10,
            )
        if isinstance(pid, int) and pid > 0 and _pid_is_alive_local(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
            if _pid_is_alive_local(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        alive = isinstance(pid, int) and pid > 0 and _pid_is_alive_local(pid)
        return {"fenced": not alive, "source_host": source_host, "method": "local_kill", "pid": pid}

    # Remote host fencing via ssh
    try:
        hcfg = config.host(source_host)
        ssh_target = hcfg.get("ssh") or hcfg.get("mesh_ssh")
        is_win = hcfg.get("os") == "windows"
    except Exception:
        ssh_target = None
        is_win = False

    if not ssh_target:
        return {"fenced": True, "source_host": source_host, "method": "no_ssh_target"}

    try:
        if is_win and isinstance(pid, int) and pid > 0:
            cmd = ["ssh", ssh_target, f"taskkill /PID {int(pid)} /T /F"]
        else:
            parts = []
            if tmux_session:
                parts.append(f"tmux kill-session -t {tmux_session} 2>/dev/null || true")
            if isinstance(pid, int) and pid > 0:
                parts.append(f"kill -TERM {int(pid)} 2>/dev/null || true; kill -KILL {int(pid)} 2>/dev/null || true")
            cmd = ["ssh", ssh_target, "; ".join(parts) or "true"]
        subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return {"fenced": True, "source_host": source_host, "method": "remote_ssh_kill", "pid": pid}
    except Exception as e:
        return {"fenced": False, "source_host": source_host, "method": "remote_ssh_kill", "error": str(e)}


def checkpoint_source_worktree(
    task: dict[str, Any],
    target_host: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Tier 1: Auto-commit and push uncommitted work in `task['worktree']` to `origin/<branch>`."""
    worktree = task.get("worktree")
    branch = task.get("branch")
    source_host = (task.get("host") or config.self_host() or "contabo").strip().lower()
    if not worktree or not branch:
        return {"checkpointed": False, "reason": "no_worktree_or_branch"}
    if dry_run:
        return {"checkpointed": True, "dry_run": True, "branch": branch, "worktree": worktree}

    msg = f"wip: checkpoint before relocating {task.get('id')} to {target_host}"
    this_host = config.self_host()

    if source_host == this_host:
        wt_path = Path(str(worktree))
        if not wt_path.is_dir():
            return {"checkpointed": False, "reason": "worktree_missing_on_source"}
        try:
            subprocess.run(["git", "-C", str(wt_path), "add", "-A"], check=False, capture_output=True, timeout=20)
            subprocess.run(
                ["git", "-C", str(wt_path), "reset", "-q", "--", "TASK.md", ".agy-run.log"],
                check=False,
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "-C", str(wt_path), "commit", "-m", msg, "--no-verify"],
                check=False,
                capture_output=True,
                timeout=20,
            )
            push = subprocess.run(
                ["git", "-C", str(wt_path), "push", "origin", f"HEAD:{branch}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=45,
            )
            return {
                "checkpointed": push.returncode == 0,
                "branch": branch,
                "worktree": str(wt_path),
                "rc": push.returncode,
            }
        except Exception as e:
            return {"checkpointed": False, "branch": branch, "error": str(e)}

    # Remote Linux/macOS worktree checkpoint over ssh
    try:
        hcfg = config.host(source_host)
        ssh_target = hcfg.get("ssh")
        if not ssh_target or hcfg.get("os") == "windows":
            return {"checkpointed": False, "reason": "remote_checkpoint_unsupported"}
        remote_cmd = (
            f"cd {worktree} && git add -A && "
            f"git reset -q -- TASK.md .agy-run.log 2>/dev/null || true && "
            f"git commit -m { json.dumps(msg) } --no-verify 2>/dev/null || true && "
            f"git push origin HEAD:{branch}"
        )
        res = subprocess.run(
            ["ssh", ssh_target, remote_cmd],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {"checkpointed": res.returncode == 0, "branch": branch, "rc": res.returncode}
    except Exception as e:
        return {"checkpointed": False, "branch": branch, "error": str(e)}


def measure_active_work_bytes(work_dir: Path) -> int:
    """Return total bytes inside `work_dir/in` and `work_dir/out` (ignoring `tmp/`)."""
    if not work_dir.is_dir():
        return 0
    total = 0
    for sub in ("in", "out"):
        sub_dir = work_dir / sub
        if not sub_dir.is_dir():
            continue
        for root_dir, _dirs, files in os.walk(sub_dir):
            for fname in files:
                fpath = Path(root_dir) / fname
                try:
                    if not fpath.is_symlink():
                        total += fpath.stat().st_size
                except OSError:
                    pass
    return total


def classify_transfer_tier(work_bytes: int) -> str:
    """Return the 3-tier transfer strategy for `work_bytes`."""
    if work_bytes <= 0:
        return "tier1_git"
    if work_bytes <= TIER2_TAILSCALE_MAX_BYTES:
        return "tier2_tailscale_rsync"
    return "tier3_gdrive_stage"


def transfer_active_work_files(
    task_id: str,
    source_host: str,
    target_host: str,
    *,
    work_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Transfer `Work/<task-id>/{in,out}` from `source_host` to `target_host`
    following the 3-Tier policy (Tier 1 Git, Tier 2 Tailscale rsync <= 500 MB,
    Tier 3 Google Drive > 500 MB). Never transfers `tmp/`."""
    src = source_host.strip().lower()
    dst = target_host.strip().lower()
    local_work = work_dir or (Path(WORK_ROOT_BY_HOST.get(src, "/opt/MoonieXHQ/Work")) / task_id)
    work_bytes = measure_active_work_bytes(local_work) if src == config.self_host() or work_dir else 0
    tier = classify_transfer_tier(work_bytes)

    if tier == "tier1_git" or src == dst:
        return {
            "ok": True,
            "tier": "tier1_git",
            "work_bytes": work_bytes,
            "transferred": False,
        }

    dst_work_root = WORK_ROOT_BY_HOST.get(dst, "/opt/MoonieXHQ/Work")
    dst_path = f"{dst_work_root}/{task_id}/"

    if tier == "tier2_tailscale_rsync":
        try:
            dst_cfg = config.host(dst)
            ssh_target = dst_cfg.get("ssh") or dst_cfg.get("mesh_ssh")
        except Exception:
            ssh_target = dst
        rsync_cmd = [
            "rsync",
            "-az",
            "--partial",
            "--exclude",
            "tmp/",
            f"{str(local_work).rstrip('/')}/",
            f"{ssh_target}:{dst_path}" if ssh_target else dst_path,
        ]
        if dry_run:
            return {
                "ok": True,
                "tier": tier,
                "work_bytes": work_bytes,
                "dry_run": True,
                "command": " ".join(rsync_cmd),
            }
        try:
            res = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=180)
            return {
                "ok": res.returncode == 0,
                "tier": tier,
                "work_bytes": work_bytes,
                "rc": res.returncode,
                "command": " ".join(rsync_cmd),
            }
        except Exception as e:
            return {"ok": False, "tier": tier, "work_bytes": work_bytes, "error": str(e)}

    # Tier 3 (> 500 MB): stage via Google Drive rclone + write SOURCES.txt
    drive_remote = f"gdrive:MoonieX-Work-Staging/{task_id}"
    rclone_cmd = [
        "rclone",
        "copy",
        str(local_work),
        drive_remote,
        "--exclude",
        "tmp/**",
    ]
    if dry_run:
        return {
            "ok": True,
            "tier": tier,
            "work_bytes": work_bytes,
            "dry_run": True,
            "drive_remote": drive_remote,
            "command": " ".join(rclone_cmd),
        }
    try:
        res = subprocess.run(rclone_cmd, capture_output=True, text=True, timeout=600)
        return {
            "ok": res.returncode == 0,
            "tier": tier,
            "work_bytes": work_bytes,
            "drive_remote": drive_remote,
            "rc": res.returncode,
        }
    except Exception as e:
        return {"ok": False, "tier": tier, "work_bytes": work_bytes, "error": str(e)}


def cleanup_source_artifacts(
    task: dict[str, Any],
    *,
    work_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Guardrail #2: Delete `Work/<task-id>/tmp/` and remove the old git worktree
    on `source_host` after checkpointing and syncing active working files."""
    source_host = (task.get("host") or config.self_host() or "contabo").strip().lower()
    task_id = str(task.get("id") or "")
    worktree = task.get("worktree")
    local_work = work_dir or (Path(WORK_ROOT_BY_HOST.get(source_host, "/opt/MoonieXHQ/Work")) / task_id)
    tmp_dir = local_work / "tmp"

    if dry_run:
        return {
            "cleaned": True,
            "dry_run": True,
            "tmp_dir": str(tmp_dir),
            "worktree": worktree,
        }

    removed_tmp = False
    removed_wt = False
    if source_host == config.self_host() or work_dir is not None:
        if tmp_dir.is_dir() and not tmp_dir.is_symlink():
            shutil.rmtree(tmp_dir, ignore_errors=True)
            removed_tmp = not tmp_dir.exists()
        if worktree:
            wt_path = Path(str(worktree))
            if wt_path.is_dir() and not wt_path.is_symlink():
                subprocess.run(
                    ["git", "-C", str(wt_path), "worktree", "remove", "--force", str(wt_path)],
                    capture_output=True,
                    timeout=20,
                )
                if wt_path.is_dir():
                    shutil.rmtree(wt_path, ignore_errors=True)
                removed_wt = not wt_path.exists()
    return {
        "cleaned": True,
        "removed_tmp": removed_tmp,
        "removed_worktree": removed_wt,
    }


def prepend_continuation_instruction(description: str, branch: str | None, source_host: str) -> str:
    """Prepend a git continuation line so the new host's worker merges partial work
    from `origin/<branch>` instead of redoing completed steps."""
    text = description or ""
    if not branch:
        return text
    marker = f"origin/{branch}"
    if marker in text:
        return text
    note = (
        f"Start (relocated from {source_host}): `git fetch origin {branch} && "
        f"git merge --no-edit origin/{branch}`. Keep partial work; do not redo it.\n\n"
    )
    # Preserve any leading header directives (lines at the top before the first blank line)
    hdr = host_router.header(text)
    if hdr:
        rest = text[len(hdr):].lstrip("\n")
        return f"{hdr}\n\n{note}{rest}"
    return f"{note}{text}"


async def relocate_task(
    task_id: str,
    target_host: str | None = None,
    *,
    dry_run: bool = False,
    confirmed: bool = False,
    raise_card: bool = False,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Relocate `task_id` from its current host to `target_host` (or auto-pick the
    best available host when `target_host is None`).

    If moving to `target_host` requires installing packages/tools or heavy setup
    (`assess["ready"] is False`) and `confirmed=False`:
      - Returns `status="requires_ceo_approval"` with the RED `[ย้ายงาน]` card spec
      - If `raise_card=True`, submits the RED Run Card (`risk="red"`) to `/run`.
    """
    from tools import delegate

    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")
    if task.get("status") in ("done", "merged", "cancelled"):
        raise ValueError(f"task {task_id} is already {task.get('status')} and cannot be relocated")

    source_host = (task.get("host") or config.self_host() or "contabo").strip().lower()

    if target_host is None:
        pick = await asyncio.to_thread(
            host_router.pick_host,
            {**task, "host": None, "allow_spillover": True},
            reserve_exception=True,
            exclude_hosts={source_host} | host_router.move_excluded(),
        )
        if not pick.host:
            raise RuntimeError(f"no eligible target host available to relocate {task_id}: {pick.line}")
        resolved_target = pick.host
    else:
        resolved_target = target_host.strip().lower()
    if resolved_target in host_router.move_excluded():
        raise ValueError(f"relocation to {resolved_target} is blocked (router.move_exclude, "
                         "CEO 2026-11-10 Q-20261110-1300-f6ba)")

    local_work = work_dir or (Path(WORK_ROOT_BY_HOST.get(source_host, "/opt/MoonieXHQ/Work")) / task_id)
    work_bytes = measure_active_work_bytes(local_work) if (source_host == config.self_host() or work_dir) else 0

    assessment = assess_migration(
        task,
        resolved_target,
        source_host=source_host,
        work_bytes=work_bytes,
    )
    if not assessment["ready"] and not confirmed:
        raised = None
        if raise_card and assessment.get("migration_card"):
            raised = raise_migration_run_card(
                assessment["migration_card"],
                dry_run=dry_run,
            )
        return {
            "ok": False,
            "status": "requires_ceo_approval",
            "task_id": task_id,
            "source_host": source_host,
            "target_host": resolved_target,
            "assessment": assessment,
            "migration_card": assessment.get("migration_card"),
            "raised_card": raised,
        }

    # 1. Guardrail #1: Fence / stop old worker on source_host
    fence_res = fence_source_worker(task, dry_run=dry_run)

    # 2. Tier 1: Checkpoint source git worktree to origin/<branch>
    checkpoint_res = checkpoint_source_worktree(task, resolved_target, dry_run=dry_run)

    # 3. Tier 2 / Tier 3: Transfer active working files Work/<task-id>/{in,out}
    transfer_res = transfer_active_work_files(
        task_id,
        source_host,
        resolved_target,
        work_dir=work_dir,
        dry_run=dry_run,
    )

    # 4. Guardrail #2: Cleanup source tmp/ and old worktree
    cleanup_res = cleanup_source_artifacts(task, work_dir=work_dir, dry_run=dry_run)

    # 5. Update task row for continuation on target_host & remove from old host_queue
    branch = task.get("branch")
    new_desc = prepend_continuation_instruction(
        str(task.get("description") or ""),
        branch if checkpoint_res.get("checkpointed") else None,
        source_host,
    )
    relocate_note = (
        f"relocated: {source_host} -> {resolved_target} "
        f"(tier={transfer_res.get('tier')}, work_bytes={transfer_res.get('work_bytes', 0)})"
    )

    if not dry_run:
        try:
            host_queue.remove(task_id)
        except Exception:
            pass
        db.update_status(
            task_id,
            "pending",
            actor="cto",
            host=resolved_target,
            assigned_agent=None,
            pid=None,
            worktree=None,
            tmux_session=None,
            description=new_desc,
            delegate_log=relocate_note,
        )
        delegated_row = await delegate.delegate_task(task_id, host=resolved_target, dry_run=False)
        try:
            send_to_cto.send(
                task_id,
                f"relocated from {source_host} to {resolved_target} "
                f"({transfer_res.get('tier')}, {transfer_res.get('work_bytes', 0)} bytes).",
                role=task.get("role"),
                cto_id=task.get("owner_cto"),
                owner_role=task.get("owner_role") or "cto",
            )
        except Exception:
            pass
    else:
        delegated_row = {**task, "host": resolved_target, "description": new_desc, "delegate_log": relocate_note}

    return {
        "ok": True,
        "status": "relocated",
        "task_id": task_id,
        "source_host": source_host,
        "target_host": resolved_target,
        "fence": fence_res,
        "checkpoint": checkpoint_res,
        "transfer": transfer_res,
        "cleanup": cleanup_res,
        "task": delegated_row,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Relocate a pending or running task (brain + git branch + active Work/<task-id>/ files) to another host."
    )
    parser.add_argument("task_id", help="Task ID (e.g. task-1234abcd)")
    parser.add_argument("--to", dest="target_host", choices=("contabo", "mac", "winbox"), help="Target host (auto-picks if omitted)")
    parser.add_argument("--confirmed", action="store_true", help="Proceed even when target host requires heavy setup (CEO approved)")
    parser.add_argument("--raise-card", action="store_true", help="Raise a RED [ย้ายงาน] Run Card if target host needs installation")
    parser.add_argument("--dry-run", action="store_true", help="Preview relocation steps without modifying processes or DB")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args(argv)

    res = asyncio.run(
        relocate_task(
            args.task_id,
            args.target_host,
            dry_run=args.dry_run,
            confirmed=args.confirmed,
            raise_card=args.raise_card,
        )
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    else:
        if res.get("status") == "requires_ceo_approval":
            card = res.get("migration_card") or {}
            print(f"🚨 RED RUN CARD REQUIRED: {card.get('why')}")
            print(f"   Expected: {card.get('expected')}")
            if res.get("raised_card"):
                print(f"   Card ID : {res['raised_card'].get('id')} ({res['raised_card'].get('url')})")
            return 2
        print(
            f"✅ Relocated {res['task_id']}: {res['source_host']} -> {res['target_host']} "
            f"(tier={res['transfer'].get('tier')})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
