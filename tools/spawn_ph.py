"""Start a Project Head session (org restructure P2, plan §3.2).

    bash scripts/spawn-ph.sh --project <Name> [--brief-file <path> | --brief <text>] [--dry-run]

Run from inside a C-level session. The caller's CXO_ROLE becomes the Project
Head's lane, and its CXO_SESSION_ID becomes the owner the PH reports to. Refused unless:

- ORG_PH_ROLES=1 in the caller's environment;
- the caller is a C-level session with a session id (a PH, a worker or a bare
  shell cannot start one);
- the project name passes lib/roles.ph_project_refusal;
- no live Project Head already holds that project on this host;
- roles/project_head.md exists (the COO writes it, plan §13);
- the resource gate passes (lib/resource_gate, ORG_SPAWN_GATE).

On success it starts tmux `project_head-<id>`, which runs `cxo-claude.sh --role
project_head`. The command exports ORG_PH_LANE, ORG_PH_PROJECT, ORG_PH_OWNER and
ORG_PH_ROLES=1 itself, because a new tmux session takes the server's environment,
not this process's. It also:

- records the spawn (tools/send_to_cxo.record_spawn), so the PH may write only
  to the session that started it;
- writes the brief to state/ph-briefs/project_head-<id>.md and passes a
  one-line prompt that points at it;
- dismisses Claude Code's new-MCP-servers screen, as tools/node_dispatch does.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import resource_gate  # noqa: E402
from lib import roles  # noqa: E402

LOCKS_DIR = ROOT / "state" / "locks"
BRIEFS_DIR = ROOT / "state" / "ph-briefs"
LAUNCHER = ROOT / "scripts" / "cxo-claude.sh"
ROLE_DOC = ROOT / "roles" / f"{roles.PH_ROLE}.md"
SPAWN_PROMPT_DELAY_S = float(os.environ.get("SPAWN_PH_PROMPT_DELAY_S", "12"))
_SID_RE = re.compile(r"[0-9a-f]{8}")
BRIEF_MAX = 20_000


class Refused(Exception):
    """The Project Head was not started; the message says why."""


def _caller() -> tuple[str, str]:
    """(lane, owner session id) of the C-level session running this."""
    role = (os.environ.get("CXO_ROLE") or "").strip().lower()
    sid = (os.environ.get("CXO_SESSION_ID") or "").strip()
    if role not in roles.c_level_roles():
        raise Refused(f"only a C-level session starts a Project Head (CXO_ROLE is {role or 'unset'})")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", sid):
        raise Refused("this session has no CXO_SESSION_ID, so the Project Head would have no owner")
    return role, sid


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def live_projects(locks_dir: Path | None = None) -> dict[str, str]:
    """{project: session id} of every live Project Head on this host."""
    found = {}
    for proj in Path(locks_dir or LOCKS_DIR).glob(f"{roles.PH_ROLE}-*.project"):
        sid = proj.name[len(roles.PH_ROLE) + 1:-len(".project")]
        lock = proj.with_suffix(".lock")
        try:
            pid = int(lock.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            continue
        if pid > 1 and _pid_alive(pid):
            found[proj.read_text(encoding="utf-8").strip()] = sid
    return found


def refusal(project: str, *, locks_dir: Path | None = None,
            role_doc: Path | None = None) -> str | None:
    """None when this caller may start a Project Head for `project` now."""
    role_doc = Path(role_doc or ROLE_DOC)
    if not roles.ph_roles_on():
        return "Project Heads are off on this host (ORG_PH_ROLES=1 turns them on; org restructure P2)"
    try:
        _caller()
    except Refused as e:
        return str(e)
    why = roles.ph_project_refusal(project)
    if why:
        return why
    held = live_projects(locks_dir).get(project)
    if held:
        return (f"project {project} already has a live Project Head #{held}; brief it instead "
                f"(send_to_cxo role=project_head-{held})")
    if not role_doc.is_file():
        return f"roles/{role_doc.name} does not exist yet — the COO writes it (plan §13)"
    return resource_gate.check()


def launch_command(sid: str, lane: str, project: str, owner: str, prompt: str) -> str:
    env = {
        "CXO_SESSION_ID": sid, "ORG_PH_ROLES": "1",
        "ORG_PH_LANE": lane, "ORG_PH_PROJECT": project, "ORG_PH_OWNER": owner,
    }
    exports = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
    return (f"unset CTO_SESSION CTO_SESSION_ID; export {exports} && "
            f"exec bash {shlex.quote(str(LAUNCHER))} --role {roles.PH_ROLE} "
            f"--lane {shlex.quote(lane)} --project {shlex.quote(project)} "
            f"--initial-prompt {shlex.quote(prompt)}")


def spawn(project: str, brief: str = "", *, dry_run: bool = False) -> dict:
    why = refusal(project)
    if why:
        raise Refused(why)
    lane, owner = _caller()
    if len(brief) > BRIEF_MAX:
        raise Refused(f"brief is {len(brief)} characters; keep it under {BRIEF_MAX} or point at a file")
    sid = uuid.uuid4().hex[:8]
    name = f"{roles.PH_ROLE}-{sid}"
    brief_path = BRIEFS_DIR / f"{name}.md"
    prompt = (f"You are {roles.ph_display(lane)} #{sid} for project {project}; you report to "
              f"{lane}-{owner}. Your brief is {brief_path}. Read it, run /session-open, then start.")
    cmd = launch_command(sid, lane, project, owner, prompt)
    out = {"session_id": sid, "tmux_session": name, "lane": lane, "project": project,
           "owner": f"{lane}-{owner}", "brief": str(brief_path)}
    if dry_run:
        return {**out, "dry_run": True, "command": cmd}

    from tools import send_to_cxo, tmux_session
    from tools.agent_transport import Identity

    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief or f"(no brief given — ask {lane}-{owner} for one)\n", encoding="utf-8")
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    (LOCKS_DIR / f"{name}.project").write_text(project, encoding="utf-8")
    # Before the session exists: its first send must already find its owner.
    send_to_cxo.record_spawn(Identity("cxo", lane, owner), roles.PH_ROLE, sid)
    try:
        tmux_session.create(name, ROOT, cmd)
    except Exception as e:  # noqa: BLE001
        for p in (LOCKS_DIR / f"{name}.project", LOCKS_DIR / f"{name}.spawned_by"):
            p.unlink(missing_ok=True)
        raise Refused(f"tmux spawn failed: {e}") from e
    dismissed = True
    try:
        time.sleep(SPAWN_PROMPT_DELAY_S)
        subprocess.run([tmux_session.tmux_bin(), "send-keys", "-t", name, "Escape"],
                       capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        dismissed = False
    return {**out, "prompt_dismissed": dismissed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bash scripts/spawn-ph.sh")
    ap.add_argument("--project", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--brief", default="")
    g.add_argument("--brief-file", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    brief = args.brief
    if args.brief_file:
        brief = Path(args.brief_file).read_text(encoding="utf-8")
    try:
        print(json.dumps(spawn(args.project, brief, dry_run=args.dry_run), ensure_ascii=False))
    except Refused as e:
        print(f"spawn-ph: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
