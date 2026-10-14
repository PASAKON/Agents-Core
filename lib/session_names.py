"""Session-name shapes (CEO 2026-10-14, card QG-20261014-0326-8968): the one place
that writes and reads them. Stdlib only, so tools/live_sessions.py (imported by a
hook under the system python3) can use it; lib.config re-exports the writers.

  C-level  "<ROLE> (<Name>)"                                  "CTO (Kavin)", "CFO"
  PH       "PH#<id3> (<LANE>) - <Project>[ + <Project>…]"     "PH#6c4 (CTO) - SpendGuard"
  worker   "<Short>#<id3> - <Head>: <job>"                    "Dev#afe - OrgRestructure: identity strict"

<id3> is the first 3 hex of the 8-hex id, for the eye only: 4096 values can
collide, so the full id stays in the hub, the tmux name and the session UUID, and
live-sessions prints host + full id when two rows share a name.
"""
from __future__ import annotations

import re

WORKER_SHORT = {
    "developer": "Dev", "tester": "Test", "web_designer": "Web",
    "browser_operator": "Browser", "video_editor": "Edit", "devops_engineer": "Ops",
    "security_engineer": "Sec", "data_analyst": "Data", "researcher": "Res",
    "prompt_engineer": "Prompt", "ads_manager": "Ads", "content_strategist": "Content",
    "script_writer": "Script", "probe": "Probe",
}
SHORT_TO_ROLE = {v: k for k, v in WORKER_SHORT.items()}
WORKER_JOB_MAX = 40

PH_NAME_RE = re.compile(r"^[\W_]*PH#([0-9a-f]{3}) \(([A-Z]{3})\)(?: - .*)?$")
WORKER_NAME_RE = re.compile(r"^[\W_]*([A-Z][A-Za-z]{1,9})#([0-9a-f]{3})(?: - .*)?$")


def short_id(sid: str) -> str:
    """The 3-hex id a name shows: "task-afe57b21" or "afe57b21" -> "afe"."""
    sid = sid[len("task-"):] if sid.startswith("task-") else sid
    return sid[:3]


def ph_session_name(sid: str, lane: str, projects) -> str:
    """"PH#<id3> (<LANE>) - <Project> + <Project>"; one project is the usual case."""
    if isinstance(projects, str):
        projects = [projects]
    names = " + ".join(p for p in (str(x).strip() for x in projects) if p)
    return f"PH#{short_id(sid)} ({lane.upper()}){' - ' + names if names else ''}"


def worker_name(short: str, task_id: str, head: str, job: str) -> str:
    """"<Short>#<id3> - <Head>: <job>"; no head gives "<Short>#<id3> - <job>",
    no job "<Short>#<id3> - <Head>"."""
    job = (job or "").strip()
    if len(job) > WORKER_JOB_MAX:
        job = job[:WORKER_JOB_MAX].rstrip() + "…"
    head = (head or "").strip()
    tail = f"{head}: {job}" if head and job else (head or job)
    base = f"{short}#{short_id(task_id)}"
    return f"{base} - {tail}" if tail else base


def parse_short(name: str) -> tuple[str, str] | None:
    """(role, id3) from a PH or worker short name, else None. A worker's short
    word must be one of WORKER_SHORT's, so "PH#…" and look-alikes never read as one."""
    m = PH_NAME_RE.match(name or "")
    if m:
        return "project_head", m.group(1)
    m = WORKER_NAME_RE.match(name or "")
    if m and m.group(1) in SHORT_TO_ROLE:
        return SHORT_TO_ROLE[m.group(1)], m.group(2)
    return None
