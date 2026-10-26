"""Session-name shapes (CEO 2026-10-14, card QG-20261014-0326-8968; 2026-10-15 ruling): the
one place that writes and reads them. Stdlib only, so tools/live_sessions.py (imported by a
hook under the system python3) can use it; lib.config re-exports the writers.

  C-level  "<ROLE> (<Name>)[ — <topic>]"                "CTO (Kavin) — CTO Main", bare "CFO"
  PH       "PH#<id3> (<LANE>) - <Project>[ + <Project>…][ — <topic>]"   "PH#7cf (CTO) - OrgRestructure"
  worker   "<Short>·<M>#<id3> <Head>: <job>"            "Dev·S#49b Org: sparse worktrees"   (M = O/S/H)
  Watch    "Watch#<id3> Runs: <N><light>"               "Watch#a1b Runs: 2🟢"

A session that already has a name keeps it, every part (CEO 2026-10-15, who renamed two live
sessions by hand to "🌐 CTO (Kavin) — CTO Main" and "🌐 PH#7cf (CTO) - OrgRestructure": the persona
and the PH's lane stay). The rename service's sweep only ever adds the host emoji to it. The compact
shape of the 15 Oct plan (state/handoff/2026-10-15/plan-names-watch-macoff.md §N: the phone app cuts
a name from the END, so what says who it is comes first, in NAME_BODY_MAX characters) is for the
kinds that had no older name: Watch, and workers, whose old shape was "<Short>#<id3> - <Head>: <job>".
Only those new names are cut to NAME_BODY_MAX, the "…" of a cut included; an existing name is never.
The readers take the old shapes, the compact ones and the C-level / PH shapes above; so do the
checks in rule_problem.

Each starts with the emoji of the host the session runs on (CEO 2026-10-14, relayed by COO
SomPong): "🌐 CTO (Kavin)". HOST_EMOJI holds them; the host comes from lib.config.self_host()
(or the worker's host), never a guess, and an unknown host gets none. A worker started on
Windows gets none either, writes "." for "·" and "..." for "…": its name crosses cmd.exe
(tools/delegate.py) and node_dispatch's ASCII-only pattern. Readers strip_host() first.

<id3> is the first 3 hex of the 8-hex id, for the eye only: 4096 values can
collide, so the full id stays in the hub, the tmux name and the session UUID, and
live-sessions prints host + full id when two rows share a name. The tmux session names
(cto-<id>, project_head-<id>, wd-<id>, sompong) are NOT display names and never change.
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
WORKER_JOB_MAX = 40       # callers cut a free-text title this far before windows_safe(); fit() does the rest
NAME_BODY_MAX = 32        # a NEW worker or Watch name, after the host emoji; the "…" of a cut counts
HEAD_MAX = 10
# The "<Head>" of a worker's name: a Project Head's project, shortened (CEO 2026-10-15).
# lib.config.head_short() reads `short:` in config/projects.yaml first.
HEAD_SHORT = {"OrgRestructure": "Org", "SpendGuard": "Spend", "BlackLiquidity": "BlackLiq",
              "MimiPage": "Mimi"}
LIGHTS = ("\U0001F7E2", "\U0001F7E1", "\U0001F534", "⚪")   # Watch: 🟢 running, 🟡 quiet, 🔴 failed or dead, ⚪ idle
HOST_EMOJI = {"mac": "\U0001F4BB", "contabo": "\U0001F310", "winbox": "\U0001F5A5️"}
# one leading host emoji, with or without U+FE0F, and the spaces after it; a state
# glyph in front ("⏸ 🌐 CTO …", session-rename.sh's prefix) is kept
_HOST_EMOJI_RE = re.compile(r"^([^\w\U0001F4BB\U0001F310\U0001F5A5]*?)"
                            r"(?:\U0001F4BB|\U0001F310|\U0001F5A5)️? *")
# A worker name that goes to winbox crosses cmd.exe and PowerShell (tools/delegate.py,
# tools/node_dispatch.py): keep only these characters of the free text in it.
_WINDOWS_UNSAFE_RE = re.compile(r"[^A-Za-z0-9 ._-]")


def windows_safe(text: str, limit: int | None = None) -> str:
    """`text` with every character outside [A-Za-z0-9 ._-] removed, cut to `limit`."""
    out = _WINDOWS_UNSAFE_RE.sub("", text or "")
    return (out[:limit] if limit else out).strip()


# --- the shapes, as patterns: every reader takes the old, the compact and the ruling ones ---
# PH: "PH#7cf (CTO) - OrgRestructure[ — topic]" (group "lane"), or compact "PH#7cf OrgRestructure".
PH_NAME_RE = re.compile(
    r"^[\W_]*PH#(?P<id3>[0-9a-f]{3}) "
    r"(?:\((?P<lane>[A-Z]{3})\)(?: - (?P<proj>.*?))?(?: — (?P<otopic>.*))?|(?P<text>(?!\()\S.*))$")
# worker: compact "Dev·S#49b Org: job" / "Dev.S#49b …" on Windows / "Dev#49b Org: job" when the model is
# not Opus, Sonnet or Haiku; old "Dev#49b - Org: job" (no model letter, the rest starts "- ").
WORKER_NAME_RE = re.compile(
    r"^[\W_]*(?P<short>[A-Z][A-Za-z]{1,9})(?:(?P<sep>[·.])(?P<model>[OSH]))?"
    r"#(?P<id3>[0-9a-f]{3})(?: (?P<rest>.*))?$")
# C-level: "CTO (Kavin) — topic" / "CFO" (no id, no topic group), or compact "CTO#c34 Main" / "COO SomPong".
_C_LEVEL_BODY_RE = re.compile(
    r"^(?P<role>C[A-Z]O)(?:(?: \((?P<persona>[A-Za-z]{2,32})\))?(?P<otopic> — .*)?"
    r"|(?:#(?P<id3>[0-9a-f]{3}))? (?P<topic>(?!\()\S.*))$")
# the first long form: "MAC CTO #671f688f (topic)", "CONTABO COO (SomPong) #a7eb4963" (same shape as
# tools/live_sessions._NAME_RE, plus the "( )" topic after the id)
_MACHINE_LONG_RE = re.compile(
    r"^[\W_]*(?:CONTABO|MAC|WINDOWS|WINBOX)\s+(?P<role>[A-Za-z][A-Za-z ]*?)"
    r"(?:\s+\([A-Za-z]{2,32}\))?\s+#(?P<id>[0-9a-f]{6,12})\b(?:\s*\((?P<topic>.*)\))?")
_WATCH_RE = re.compile(r"^Watch#(?P<id3>[0-9a-f]{3}) \S")
_NO_ID_ROLES = ("COO",)    # SomPong has no org sid
_DOT = "·"           # the "·" between a worker's short word and its model letter


# --- host emoji -----------------------------------------------------------------------

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


# --- the writers ----------------------------------------------------------------------

def fit(body: str, ascii_only: bool = False) -> str:
    """`body` cut to NAME_BODY_MAX characters, the mark of the cut included ("…", or "..."
    where the name must stay ASCII). Cutting what already fits changes nothing."""
    body = (body or "").strip()
    if len(body) <= NAME_BODY_MAX:
        return body
    mark = "..." if ascii_only else "…"
    return body[:NAME_BODY_MAX - len(mark)].rstrip() + mark


def model_letter(model: str | None) -> str:
    """O, S or H for an Opus, Sonnet or Haiku model id (or the letter itself); "" for any other."""
    m = str(model or "").strip().lower()
    if m in ("o", "s", "h"):
        return m.upper()
    for word, letter in (("opus", "O"), ("sonnet", "S"), ("haiku", "H")):
        if word in m:
            return letter
    return ""


def head_short(project: str | None) -> str:
    """A Project Head's project as a worker's "<Head>": HEAD_SHORT's word, else the first
    HEAD_MAX characters. Shortening a short head changes nothing."""
    p = (project or "").strip()
    return HEAD_SHORT.get(p) or p[:HEAD_MAX]


def clevel_name(role: str, persona: str = "", host: str | None = None) -> str:
    """"<emoji> <ROLE> (<Name>)", the bare "<emoji> <ROLE>" without a persona. session-rename.sh
    appends " — <topic>" later. Never cut: it is the one name a C-level has."""
    return host_prefix(host) + role.upper() + (f" ({persona})" if persona else "")


def ph_session_name(sid: str, lane: str, projects, host: str | None = None) -> str:
    """"<emoji> PH#<id3> (<LANE>) - <Project> + <Project>"; one project is the usual
    case, and no `host` (or an unknown one) gives no emoji."""
    if isinstance(projects, str):
        projects = [projects]
    names = " + ".join(p for p in (str(x).strip() for x in projects) if p)
    return host_prefix(host) + f"PH#{short_id(sid)} ({lane.upper()}){' - ' + names if names else ''}"


def worker_name(short: str, task_id: str, head: str, job: str, model: str = "",
                windows: bool = False) -> str:
    """"<Short>·<M>#<id3> <Head>: <job>"; no head gives "<Short>·<M>#<id3> <job>", no job
    "<Short>·<M>#<id3> <Head>". `model` is a model id or its letter; one that is not Opus,
    Sonnet or Haiku leaves the letter out. `windows` writes "." for "·" and "..." for "…".
    At most NAME_BODY_MAX characters."""
    letter = model_letter(model)
    head, job = head_short(head), (job or "").strip()
    tail = f"{head}: {job}" if head and job else (head or job)
    base = f"{short}{('.' if windows else _DOT) + letter if letter else ''}#{short_id(task_id)}"
    return fit(f"{base} {tail}" if tail else base, ascii_only=windows)


def watch_name(sid: str, n: int, light: str, host: str | None = None) -> str:
    """"<emoji> Watch#<id3> Runs: <N><light>"; `light` is one of LIGHTS."""
    return host_prefix(host) + fit(f"Watch#{short_id(sid)} Runs: {n}{light}")


# --- the readers ----------------------------------------------------------------------

# A state glyph from session-rename.sh's --prefix ("⏸ ", "✅ ") may lead; it is not part of the rule.
_STATE_LEAD_RE = re.compile(r"^[^\w\U0001F4BB\U0001F310\U0001F5A5]*")
_HOST_LEAD_RE = re.compile(r"(\U0001F4BB|\U0001F310|\U0001F5A5)️? ?")


def split_name(name: str) -> tuple[str, str, str]:
    """(state glyph lead, host emoji, body): "⏸ 🌐 CTO (Kavin)" -> ("⏸ ", "🌐", "CTO (Kavin)")."""
    name = name or ""
    lead = _STATE_LEAD_RE.match(name).group(0)
    rest = name[len(lead):]
    m = _HOST_LEAD_RE.match(rest)
    return lead, (m.group(1) if m else ""), (rest[m.end():] if m else rest)


def parse_short(name: str) -> tuple[str, str] | None:
    """(role, id3) from a PH, worker, C-level or Watch name in any shape, else None. A
    worker's short word must be one of WORKER_SHORT's, so "PH#…" and look-alikes never read
    as one. A name with no id (the COO's, the C-level "CTO (Kavin)") gives an empty id3:
    tools/live_sessions takes those ids from the record instead. The long machine form
    ("MAC CTO #671f688f (topic)") gives the first 3 hex of its id."""
    body = split_name(name)[2]
    m = PH_NAME_RE.match(body)
    if m:
        return "project_head", m.group("id3")
    m = WORKER_NAME_RE.match(body)
    if m and m.group("short") in SHORT_TO_ROLE:
        return SHORT_TO_ROLE[m.group("short")], m.group("id3")
    m = _WATCH_RE.match(body)
    if m:
        return "watch", m.group("id3")
    m = _MACHINE_LONG_RE.match(body)
    if m and m.group("role").strip().upper() != "CEO":
        return m.group("role").strip().lower().replace(" ", "_"), m.group("id")[:3]
    m = _C_LEVEL_BODY_RE.match(body)
    if m and m.group("role") != "CEO":
        if m.group("id3"):
            return m.group("role").lower(), m.group("id3")
        if m.group("topic") is None or m.group("role") in _NO_ID_ROLES:   # "CTO (Kavin)", "CFO", "COO SomPong"
            return m.group("role").lower(), ""
    return None


def rule_problem(name: str, role: str, sid: str, host: str | None,
                 persona: str | None = None, windows: bool = False) -> str | None:
    """Why `name` is off the rule for a session of `role`/`sid` on `host`, or None.
    Roles with no rule ("unknown", "ceo") are never off it. A C-level or PH name in the old,
    the compact or the ruling shape passes, whatever its length (an existing name is never
    cut); the host emoji, the role, the id and, when the caller knows it (`persona`, from
    policies/agents.yaml), a C-level's "(<Name>)" must be right. A worker name in the compact
    shape is cut to NAME_BODY_MAX; its old shape is not. `windows` is True on a Windows host,
    where a worker's name carries no emoji."""
    is_worker = role in WORKER_SHORT
    is_c_level = bool(re.fullmatch(r"c[a-z]o", role or "")) and role != "ceo"
    if role != "project_head" and not is_worker and not is_c_level:
        return None
    _lead, got, body = split_name(name)
    want = "" if (is_worker and windows) else HOST_EMOJI.get(host or "", "")
    if want and not got:
        return "no host emoji"
    if got and got != want.rstrip("️"):
        return "wrong host emoji" if want else "a host emoji where none belongs"
    if role == "project_head":
        pm = PH_NAME_RE.match(body)
        if not pm:
            return 'not "PH#<id3> (<LANE>) - <Project>"'
        if sid and pm.group("id3") != sid[:3]:
            return f"PH#{pm.group('id3')} is not this session (#{sid[:3]})"
        return None
    if is_worker:
        wm = WORKER_NAME_RE.match(body)
        sep = "." if windows else _DOT
        if (not wm or wm.group("short") != WORKER_SHORT[role]
                or (wm.group("sep") and wm.group("sep") != sep)):
            return f'not "{WORKER_SHORT[role]}{sep}<O|S|H>#<id3> <Head>: <job>"'
        if sid and wm.group("id3") != sid[:3]:
            return f"{wm.group('short')}#{wm.group('id3')} is not this session (#{sid[:3]})"
        old = (wm.group("rest") or "").startswith("- ")
        if not old and len(body) > NAME_BODY_MAX:
            return f"body is {len(body)} characters (max {NAME_BODY_MAX})"
        return None
    cm = _C_LEVEL_BODY_RE.match(body)
    no_id = role.upper() in _NO_ID_ROLES
    if not cm or cm.group("role") != role.upper():
        return f'not "{role.upper()} ({persona or "<Name>"})"'
    if cm.group("topic") is None:                       # old shape: "CTO (Kavin)[ — topic]"
        if persona and cm.group("persona") != persona:
            return f'not "{role.upper()} ({persona})"'
    elif bool(cm.group("id3")) == no_id:                # compact: "CTO#c34 Main" / the COO's "COO SomPong"
        return f'not "{role.upper()}{"" if no_id else "#<id3>"} <topic>"'
    elif sid and cm.group("id3") and cm.group("id3") != sid[:3]:
        return f"{role.upper()}#{cm.group('id3')} is not this session (#{sid[:3]})"
    return None


if __name__ == "__main__":   # `python lib/session_names.py prefix <host>`: the emoji, or nothing
    import argparse
    import json
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "prefix":
        sys.stdout.write(HOST_EMOJI.get(sys.argv[2], ""))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "name":
        from lib import config

        parser = argparse.ArgumentParser(prog="python -m lib.session_names name")
        parser.add_argument("--host", required=True)
        parser.add_argument("--role", required=True)
        parser.add_argument("--sid", required=True)
        parser.add_argument("--lane")
        parser.add_argument("--project")
        args = parser.parse_args(sys.argv[2:])
        if args.role == "project_head":
            if not (args.lane and args.lane.strip() and args.project and args.project.strip()):
                parser.error("project_head requires --lane and --project")
            name = ph_session_name(args.sid, args.lane, args.project, args.host)
        elif config.is_c_level(args.role):
            name = clevel_name(args.role, config.persona_for(args.role), args.host)
        else:
            parser.error("unknown role: " + args.role)
        print(json.dumps(name, ensure_ascii=True))
        sys.exit(0)
    sys.stderr.write("usage: session_names.py prefix <host> | name --host <host> --role <role> --sid <sid> [--lane <lane>] [--project <Project>]\n")
    sys.exit(2)
