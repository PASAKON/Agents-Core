"""Session-name shapes (CEO 2026-10-14, card QG-20261014-0326-8968): the one place
that writes and reads them. Stdlib only, so tools/live_sessions.py (imported by a
hook under the system python3) can use it; lib.config re-exports the writers.

  C-level  "<ROLE> (<Name>)"                                  "CTO (Kavin)", "CFO"
  PH       "PH#<id3> (<LANE>) - <Project>[ + <Project>…]"     "PH#6c4 (CTO) - SpendGuard"
  worker   "<Short>#<id3> - <Head>: <job>"                    "Dev#afe - OrgRestructure: identity strict"

Each starts with the emoji of the host the session runs on (CEO 2026-10-14, relayed
by COO SomPong): "🌐 CTO (Kavin)". HOST_EMOJI holds them; the host comes from
lib.config.self_host() (or the worker's host), never a guess, and an unknown host
gets none. A worker started on Windows gets none either: its name crosses cmd.exe
(tools/delegate.py) and node_dispatch's ASCII-only pattern. Readers strip_host() first.

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
HOST_EMOJI = {"mac": "\U0001F4BB", "contabo": "\U0001F310", "winbox": "\U0001F5A5\uFE0F"}
# one leading host emoji, with or without U+FE0F, and the spaces after it; a state
# glyph in front ("⏸ 🌐 CTO …", session-rename.sh's prefix) is kept
_HOST_EMOJI_RE = re.compile(r"^([^\w\U0001F4BB\U0001F310\U0001F5A5]*?)"
                            r"(?:\U0001F4BB|\U0001F310|\U0001F5A5)\uFE0F? *")
# A worker name that goes to winbox crosses cmd.exe and PowerShell (tools/delegate.py,
# tools/node_dispatch.py): keep only these characters of the free text in it.
_WINDOWS_UNSAFE_RE = re.compile(r"[^A-Za-z0-9 ._-]")


def windows_safe(text: str, limit: int | None = None) -> str:
    """`text` with every character outside [A-Za-z0-9 ._-] removed, cut to `limit`."""
    out = _WINDOWS_UNSAFE_RE.sub("", text or "")
    return (out[:limit] if limit else out).strip()

PH_NAME_RE = re.compile(r"^[\W_]*PH#([0-9a-f]{3}) \(([A-Z]{3})\)(?: - .*)?$")
WORKER_NAME_RE = re.compile(r"^[\W_]*([A-Z][A-Za-z]{1,9})#([0-9a-f]{3})(?: - .*)?$")


def host_prefix(host: str | None) -> str:
    """"<emoji> " for a known host key, else ""."""
    emoji = HOST_EMOJI.get(host or "")
    return f"{emoji} " if emoji else ""


def strip_host(name: str) -> str:
    """`name` without its one leading host emoji (U+FE0F optional) and the space."""
    return _HOST_EMOJI_RE.sub(r"\1", name or "", count=1)


def with_host(host: str | None, name: str) -> str:
    """`name` with `host`'s emoji in front, replacing any host emoji it had."""
    return host_prefix(host) + strip_host(name)


def short_id(sid: str) -> str:
    """The 3-hex id a name shows: "task-afe57b21" or "afe57b21" -> "afe"."""
    sid = sid[len("task-"):] if sid.startswith("task-") else sid
    return sid[:3]


def ph_session_name(sid: str, lane: str, projects, host: str | None = None) -> str:
    """"<emoji> PH#<id3> (<LANE>) - <Project> + <Project>"; one project is the usual
    case, and no `host` (or an unknown one) gives no emoji."""
    if isinstance(projects, str):
        projects = [projects]
    names = " + ".join(p for p in (str(x).strip() for x in projects) if p)
    return host_prefix(host) + f"PH#{short_id(sid)} ({lane.upper()}){' - ' + names if names else ''}"


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
    name = strip_host(name)
    m = PH_NAME_RE.match(name)
    if m:
        return "project_head", m.group(1)
    m = WORKER_NAME_RE.match(name)
    if m and m.group(1) in SHORT_TO_ROLE:
        return SHORT_TO_ROLE[m.group(1)], m.group(2)
    return None


if __name__ == "__main__":   # `python lib/session_names.py prefix <host>`: the emoji, or nothing
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "prefix":
        sys.stdout.write(HOST_EMOJI.get(sys.argv[2], ""))
        sys.exit(0)
    sys.stderr.write("usage: session_names.py prefix <host>\n")
    sys.exit(2)
