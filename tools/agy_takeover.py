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
import json, os, re, sys
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
            return res
    raise LookupError(f"Could not find any Claude Code session matching {target!r} on {search_hosts}")


def format_handoff_markdown(info: dict[str, Any]) -> str:
    """Format an inspected Claude Code session into a structured markdown handoff brief for AGY."""
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
    ]

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
        f"- **If work is on `mac`**: edit/run directly in `/Users/gob/MoonieXHQ`.",
        f"- **If work is on `contabo`**: run commands via `ssh mooniex-vps 'cd /opt/MoonieXHQ/Agents/Core && ...'` or delegate an AGY worker via `python3 tools/ph_brain.py delegate ...`.",
        f"- **If work is on `winbox`**: run commands via `ssh winbox ...` or inspect worktrees under `C:\\Users\\passg\\mooniex\\worktrees`.",
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

        if args.cmd == "handoff-to-brain":
            from tools import ph_brain
            info = inspect_target(args.target, host=args.host, max_turns=12)
            bundle_path = save_handoff_bundle(info)
            handoff_md = bundle_path.read_text(encoding="utf-8")
            prompt = (
                f"คุณกำลังรับช่วงงานต่อ (Emergency Takeover) จาก Claude Code session ที่โควตาเต็ม:\n\n"
                f"{handoff_md}\n\n"
                f"--- คำสั่งปัจจุบัน ---\n{args.message}"
            )
            res = ph_brain.run_turn(
                ph_id=info["short_id"],
                project=info.get("project") or info["short_id"],
                lane="cto",
                owner=info.get("owner") or None,
                message=prompt,
            )
            print(
                f"[Takeover -> PH#{res['ph_id']} ({res['project']}) | model={res['model_used']} | "
                f"conv={res['conversation_id']} | claude_code=0 tok]\n{res['response']}"
            )
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"agy_takeover error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
