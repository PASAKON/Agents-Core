"""Start a Project Head session (org restructure P2, plan §3.2).

    bash scripts/spawn-ph.sh --project <Name> [--brief-file <path> | --brief <text>] [--dry-run]

Run from inside a C-level session. The caller's role becomes the Project Head's
lane, and its session becomes the owner the PH reports to: the same identity
send_to_cxo uses (tools/agent_transport.current_identity), so a cto-claude.sh
session, which has only CTO_SESSION_ID, qualifies. Refused unless:

- the host flag ORG_PH_ROLES is on (lib/org_flags);
- the caller is a C-level session with a session id that send_to_cxo.authorize
  lets start a session (a PH, a worker, a bare shell or a C-level already at the
  hop cap cannot start one);
- the project name passes lib/roles.ph_project_refusal;
- no Project Head holds that project on this host, ignoring case: a live one,
  or a claim younger than CLAIM_GRACE_S whose launcher has not written its lock
  yet. The check and the claim are one step under a flock;
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
- dismisses Claude Code's new-MCP-servers screen when the pane shows it (a
  blind Escape would interrupt the PH's first turn).

On another host (M13b, CEO 2026-10-14 "ทำให้ CXO spawn PH บน Mac และ Windows ได้เลย"):
there is no ssh to the Mac by design, so a C-level raises a Run Inbox card for
that host and the CEO taps it (one tap per spawn):

    bash scripts/hub/org-python.sh -m tools.spawn_ph card --host mac --project <Name> \
        --brief-file <path> [--sha <pushed Agents-Core commit>] [--send]

prints (or, with --send, raises) `tools/ask_run.py create --host mac --script
Agents-Core@<sha>:scripts/spawn-ph.sh -- --project <Name> --from-card <nonce>
--brief <text>`. On the target host the card runs `spawn-ph.sh --from-card
<nonce>`, which has no C-level identity of its own: the owner is the requester
of the ONE running card on the hub whose host is this host, whose script is
spawn-ph.sh and whose args carry that nonce and that project. A run with no such
card, or no hub token on the host, is refused; a flag never names the owner.
"""
from __future__ import annotations

import argparse
import contextlib
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
CLAIM_GRACE_S = 60
SPAWN_SCRIPT = "scripts/spawn-ph.sh"
_NONCE_RE = re.compile(r"[0-9a-f]{16}")
MCP_SCREEN_RE = re.compile(r"MCP server", re.IGNORECASE)


class Refused(Exception):
    """The Project Head was not started; the message says why."""


def _caller() -> tuple[str, str]:
    """(lane, owner session id) of the C-level session running this."""
    from tools import send_to_cxo
    from tools.agent_transport import current_identity
    try:
        ident = current_identity()
    except PermissionError as e:
        raise Refused(f"only a C-level session starts a Project Head ({e})") from e
    if ident.kind == "ceo" and (os.environ.get("CXO_ROLE") or "").strip().lower() in roles.c_level_roles():
        raise Refused("this session has no CXO_SESSION_ID or CTO_SESSION_ID, so the Project "
                      "Head would have no owner")
    if ident.kind != "cxo" or ident.role not in roles.c_level_roles():
        raise Refused(f"only a C-level session starts a Project Head (this is {ident.label()})")
    sid = (ident.session_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", sid):
        raise Refused("this session's id is not usable, so the Project Head would have no owner")
    try:
        send_to_cxo.authorize(ident, roles.PH_ROLE, None, spawning=True)
    except PermissionError as e:
        raise Refused(str(e)) from e
    return ident.role, sid


def card_owner(nonce: str, project: str) -> tuple[str, str]:
    """(lane, owner session id) from the running Run Inbox card that started
    this spawn-ph.sh run on this host (M13b). The CEO's tap on that card is the
    authority; its requester is the owner."""
    if not _NONCE_RE.fullmatch(nonce or ""):
        raise Refused("--from-card takes the 16-hex nonce the card was raised with")
    from tools import ask_run
    try:
        from lib.config import self_host
        host = str(self_host()).strip().lower()
    except Exception as e:  # noqa: BLE001
        raise Refused(f"cannot tell which host this is, so no card can be matched ({e})") from e
    try:
        resp = ask_run._call("GET", ask_run.ASKS_PATH, query={"status": "running", "limit": "50"})
    except Exception as e:  # noqa: BLE001 - no token, hub down: refuse
        raise Refused(f"cannot read the Run Inbox hub to find the card ({e})") from e
    asks = resp.get("asks") if isinstance(resp, dict) else resp
    hits = []
    for a in asks or []:
        if not isinstance(a, dict):
            continue
        sc_ = a.get("script") if isinstance(a.get("script"), dict) else {}
        args = [str(x) for x in (sc_.get("args") or [])]
        pairs = dict(zip(args, args[1:]))
        if (a.get("status") == "running" and str(a.get("host", "")).lower() == host
                and a.get("kind") == "script" and sc_.get("repo") == "Agents-Core"
                and sc_.get("path") == SPAWN_SCRIPT and pairs.get("--from-card") == nonce
                and pairs.get("--project") == project):
            hits.append(a)
    if len(hits) != 1:
        raise Refused(f"no single running Run Inbox card on host {host} carries --from-card {nonce} "
                      f"for project {project} ({len(hits)} found); a C-level raises one with "
                      "`python -m tools.spawn_ph card`")
    req = hits[0].get("requester") if isinstance(hits[0].get("requester"), dict) else {}
    lane, _, sid = str(req.get("session", "")).partition("-")
    if lane not in roles.c_level_roles() or str(req.get("role", "")).lower() != lane:
        raise Refused(f"card {hits[0].get('id')} was not raised by a C-level session "
                      f"(requester {req.get('session')!r})")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", sid):
        raise Refused(f"card {hits[0].get('id')} names no usable owner session id")
    return lane, sid


def live_projects(locks_dir: Path | None = None) -> dict[str, str]:
    """{project, casefolded: session id} of every Project Head holding a project
    on this host: its launcher is live, or its claim is younger than
    CLAIM_GRACE_S and the launcher has not written its lock yet. A claim file
    that neither root nor this user wrote is ignored (state/locks is
    group-writable)."""
    from tools import clevel_gate
    from tools.send_to_cxo import _trusted_record
    d = Path(locks_dir or LOCKS_DIR)
    now = time.time()
    found = {}
    for proj in d.glob(f"{roles.PH_ROLE}-*.project"):
        sid = proj.name[len(roles.PH_ROLE) + 1:-len(".project")]
        try:
            age = now - proj.stat().st_mtime
            name = proj.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not _trusted_record(proj):
            continue
        lock = d / f"{roles.PH_ROLE}-{sid}.lock"
        if clevel_gate.live_lock(roles.PH_ROLE, sid, d) or (not lock.exists() and age < CLAIM_GRACE_S):
            found[name.casefold()] = sid
    return found


@contextlib.contextmanager
def _claim_lock(locks_dir: Path):
    """Check-then-claim as one step: two C-levels starting the same project in
    the same second must not both pass. No fcntl (Windows): no lock."""
    try:
        import fcntl
    except ImportError:
        yield
        return
    locks_dir.mkdir(parents=True, exist_ok=True)
    with open(locks_dir / ".ph-projects.flock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _owner(card: str | None, project: str) -> tuple[str, str]:
    return card_owner(card, project) if card is not None else _caller()


def refusal(project: str, *, locks_dir: Path | None = None,
            role_doc: Path | None = None, card: str | None = None) -> str | None:
    """None when this caller (or, with `card`, that card's requester) may start
    a Project Head for `project` now."""
    role_doc = Path(role_doc or ROLE_DOC)
    if not roles.ph_roles_on():
        return "Project Heads are off on this host (ORG_PH_ROLES=1 turns them on; org restructure P2)"
    try:
        _owner(card, project)
    except Refused as e:
        return str(e)
    why = roles.ph_project_refusal(project)
    if why:
        return why
    held = live_projects(locks_dir).get(project.casefold())
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
    return (f"unset CTO_SESSION CTO_SESSION_ID CXO_ROLE; export {exports} && "
            f"exec bash {shlex.quote(str(LAUNCHER))} --role {roles.PH_ROLE} "
            f"--lane {shlex.quote(lane)} --project {shlex.quote(project)} "
            f"--initial-prompt {shlex.quote(prompt)}")


def _plan(project: str, brief: str, card: str | None = None) -> dict:
    why = refusal(project, card=card)
    if why:
        raise Refused(why)
    lane, owner = _owner(card, project)
    if len(brief) > BRIEF_MAX:
        raise Refused(f"brief is {len(brief)} characters; keep it under {BRIEF_MAX} or point at a file")
    sid = uuid.uuid4().hex[:8]
    name = f"{roles.PH_ROLE}-{sid}"
    brief_path = BRIEFS_DIR / f"{name}.md"
    prompt = (f"You are {roles.ph_display(lane)} #{sid} for project {project}; you report to "
              f"{lane}-{owner}. Your brief is {brief_path}. Read it, run /session-open, then start.")
    return {"session_id": sid, "tmux_session": name, "lane": lane, "project": project,
            "owner": f"{lane}-{owner}", "brief": str(brief_path),
            "command": launch_command(sid, lane, project, owner, prompt)}


def spawn(project: str, brief: str = "", *, dry_run: bool = False,
          card: str | None = None) -> dict:
    if dry_run:
        return {**_plan(project, brief, card), "dry_run": True}

    from tools import send_to_cxo, tmux_session
    from tools.agent_transport import Identity

    with _claim_lock(LOCKS_DIR):
        plan = _plan(project, brief, card)
        name, lane = plan["tmux_session"], plan["lane"]
        owner = plan["owner"].split("-", 1)[1]
        BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        Path(plan["brief"]).write_text(brief or f"(no brief given — ask {plan['owner']} for one)\n",
                                       encoding="utf-8")
        LOCKS_DIR.mkdir(parents=True, exist_ok=True)
        (LOCKS_DIR / f"{name}.project").write_text(project, encoding="utf-8")
        # Before the session exists: its first send must already find its owner.
        send_to_cxo.record_spawn(Identity("cxo", lane, owner), roles.PH_ROLE, plan["session_id"])
    cmd = plan.pop("command")
    try:
        tmux_session.create(name, ROOT, cmd)
    except Exception as e:  # noqa: BLE001
        for p in (LOCKS_DIR / f"{name}.project", LOCKS_DIR / f"{name}.spawned_by"):
            p.unlink(missing_ok=True)
        raise Refused(f"tmux spawn failed: {e}") from e
    dismissed: bool | None = False
    try:
        time.sleep(SPAWN_PROMPT_DELAY_S)
        if MCP_SCREEN_RE.search(tmux_session.capture(name, 60)):
            subprocess.run([tmux_session.tmux_bin(), "send-keys", "-t", name, "Escape"],
                           capture_output=True, text=True, timeout=10)
            dismissed = True
    except (OSError, subprocess.SubprocessError):
        dismissed = None
    return {**plan, "mcp_screen_dismissed": dismissed}


def card_command(host: str, project: str, brief: str, sha: str, nonce: str | None = None) -> list[str]:
    """argv of the `tools/ask_run.py create` that asks the CEO to start a
    Project Head on `host` (M13b). Run it from the owning C-level session: the
    card's requester becomes the owner."""
    why = roles.ph_project_refusal(project)
    if why:
        raise Refused(why)
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha or ""):
        raise Refused(f"--sha must be a pushed Agents-Core commit id (got {sha!r})")
    if len(brief) > BRIEF_MAX:
        raise Refused(f"brief is {len(brief)} characters; keep it under {BRIEF_MAX}")
    nonce = nonce or uuid.uuid4().hex[:16]
    args = ["--project", project, "--from-card", nonce]
    if brief:
        args += ["--brief", brief]
    return [sys.executable, str(ROOT / "tools" / "ask_run.py"), "create", "--host", host,
            "--why", f"start a Project Head for {project} on {host} (spawn-ph, M13b)",
            "--expected", f"one JSON line naming tmux project_head-<id> for {project}",
            "--risk", "amber", "--timeout", "120",
            "--script", f"Agents-Core@{sha}:{SPAWN_SCRIPT}", "--", *args]


def _card_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.spawn_ph card")
    ap.add_argument("--host", required=True)
    ap.add_argument("--project", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--brief", default="")
    g.add_argument("--brief-file", default=None)
    ap.add_argument("--sha", default=None, help="pushed Agents-Core commit (default: origin/main)")
    ap.add_argument("--send", action="store_true", help="raise the card (default: print it)")
    args = ap.parse_args(argv)
    brief = Path(args.brief_file).read_text(encoding="utf-8") if args.brief_file else args.brief
    sha = args.sha or subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                                     capture_output=True, text=True).stdout.strip()
    try:
        cmd = card_command(args.host, args.project, brief, sha)
    except Refused as e:
        print(f"spawn-ph card: {e}", file=sys.stderr)
        return 1
    if not args.send:
        print(shlex.join(cmd))
        return 0
    return subprocess.run(cmd).returncode


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["card"]:
        return _card_main(argv[1:])
    ap = argparse.ArgumentParser(prog="bash scripts/spawn-ph.sh")
    ap.add_argument("--project", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--brief", default="")
    g.add_argument("--brief-file", default=None)
    ap.add_argument("--from-card", default=None,
                    help="run by a Run Inbox card: the card's requester is the owner (M13b)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    brief = args.brief
    if args.brief_file:
        brief = Path(args.brief_file).read_text(encoding="utf-8")
    try:
        print(json.dumps(spawn(args.project, brief, dry_run=args.dry_run, card=args.from_card),
                         ensure_ascii=False))
    except Refused as e:
        print(f"spawn-ph: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
