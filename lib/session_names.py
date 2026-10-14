"""Session-name shapes (CEO 2026-10-15, plan state/handoff/2026-10-15/plan-names-watch-macoff.md
§N): the one place that writes and reads them. Stdlib only, so tools/live_sessions.py
(imported by a hook under the system python3) can use it; lib.config re-exports the writers.

Order: host emoji, role, model, #sid, job. The phone app cuts a name from the END, so
what says who it is comes first. The body after the host emoji is at most NAME_BODY_MAX
characters, the "…" that marks a cut included.

  C-level  "<ROLE>#<id3> <topic>"                     "CTO#c34 Main"   (topic defaults to Main)
  COO      "COO <topic>"  (no org sid, no #id)        "COO SomPong"    (topic defaults to its persona)
  PH       "PH#<id3> <Project>[+<Project>]"           "PH#7cf OrgRestructure"
  worker   "<Short>·<M>#<id3> <Head>: <job>"          "Dev·S#49b Org: sparse worktrees"   (M = O/S/H)
  Watch    "Watch#<id3> Runs: <N><light>"             "Watch#a1b Runs: 2🟢"

A topic given to session-rename.sh replaces the PH's project ("PH#7cf test"). The persona
(Kavin, Ging) and the PH's lane are not in the name: the persona only tuned the tone, and
the project says which lane a PH is in. NAME_BODY_MAX is the one number to change when the
CEO's phone shows the list; the old shapes ("CTO (Kavin) — topic", "PH#7cf (CTO) - Project",
"Dev#49b - Head: job", "MAC CTO #671f688f (topic)") are still READ so a live session that
has not been renamed yet is recognised, and rule_problem calls each one "old shape".

Each starts with the emoji of the host the session runs on (CEO 2026-10-14, relayed by COO
SomPong): "🌐 CTO#c34 Main". HOST_EMOJI holds them; the host comes from lib.config.self_host()
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
NAME_BODY_MAX = 32        # CEO 2026-10-15; the "…" of a cut name counts
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


# --- the shapes, as patterns: every reader takes the OLD and the NEW one ----------------
# PH: new "PH#7cf OrgRestructure"; old "PH#7cf (CTO) - OrgRestructure[ — topic]" (group "lane").
PH_NAME_RE = re.compile(
    r"^[\W_]*PH#(?P<id3>[0-9a-f]{3}) "
    r"(?:\((?P<lane>[A-Z]{3})\)(?: - (?P<proj>.*?))?(?: — (?P<otopic>.*))?|(?P<text>(?!\()\S.*))$")
# worker: new "Dev·S#49b Org: job" / "Dev.S#49b …" on Windows / "Dev#49b Org: job" when the model
# is not Opus, Sonnet or Haiku; old "Dev#49b - Org: job" (no model letter, rest starts "- ").
WORKER_NAME_RE = re.compile(
    r"^[\W_]*(?P<short>[A-Z][A-Za-z]{1,9})(?:(?P<sep>[·.])(?P<model>[OSH]))?"
    r"#(?P<id3>[0-9a-f]{3})(?: (?P<rest>.*))?$")
# C-level body: new "CTO#c34 Main" / "COO SomPong"; old "CTO (Kavin) — topic" / "CFO" (no id, no topic group).
_C_LEVEL_BODY_RE = re.compile(
    r"^(?P<role>C[A-Z]O)(?:(?P<persona> \([A-Za-z]{2,32}\))?(?P<otopic> — .*)?"
    r"|(?:#(?P<id3>[0-9a-f]{3}))? (?P<topic>(?!\()\S.*))$")
# the first long form: "MAC CTO #671f688f (topic)", "CONTABO COO (SomPong) #a7eb4963" (same shape as
# tools/live_sessions._NAME_RE, plus the "( )" topic after the id)
_MACHINE_LONG_RE = re.compile(
    r"^[\W_]*(?:CONTABO|MAC|WINDOWS|WINBOX)\s+[A-Za-z][A-Za-z ]*?"
    r"(?:\s+\([A-Za-z]{2,32}\))?\s+#[0-9a-f]{6,12}\b(?:\s*\((?P<topic>.*)\))?")
_WATCH_RE = re.compile(r"^Watch#(?P<id3>[0-9a-f]{3}) \S")
_HEAD_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}")   # a Project Head's project: one word
_NO_ID_ROLES = ("COO",)    # SomPong has no org sid
_DOT = "\u00B7"           # the "·" between a worker's short word and its model letter


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


def clevel_name(role: str, sid: str | None, topic: str = "", host: str | None = None,
                persona: str = "") -> str:
    """"<emoji> <ROLE>#<id3> <topic>"; the topic defaults to "Main". The COO has no org sid,
    so no "#<id3>", and its default topic is its `persona` ("COO SomPong")."""
    role = role.upper()
    tag = role if (role in _NO_ID_ROLES or not sid) else f"{role}#{short_id(sid)}"
    default = persona if role in _NO_ID_ROLES and persona else "Main"
    return host_prefix(host) + fit(f"{tag} {(topic or '').strip() or default}")


def ph_session_name(sid: str, projects, host: str | None = None, topic: str = "") -> str:
    """"<emoji> PH#<id3> <Project>[+<Project>]"; a `topic` takes the projects' place. One
    project is the usual case, and no `host` (or an unknown one) gives no emoji."""
    if isinstance(projects, str):
        projects = [projects]
    names = "+".join(p for p in (str(x).strip() for x in projects) if p)
    text = (topic or "").strip() or names
    return host_prefix(host) + fit(f"PH#{short_id(sid)}" + (f" {text}" if text else ""))


def worker_name(short: str, task_id: str, head: str, job: str, model: str = "",
                windows: bool = False) -> str:
    """"<Short>·<M>#<id3> <Head>: <job>"; no head gives "<Short>·<M>#<id3> <job>", no job
    "<Short>·<M>#<id3> <Head>". `model` is a model id or its letter; one that is not Opus,
    Sonnet or Haiku leaves the letter out. `windows` writes "." for "·" and "..." for "…"."""
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
    """(state glyph lead, host emoji, body): "⏸ 🌐 CTO#c34 Main" -> ("⏸ ", "🌐", "CTO#c34 Main")."""
    name = name or ""
    lead = _STATE_LEAD_RE.match(name).group(0)
    rest = name[len(lead):]
    m = _HOST_LEAD_RE.match(rest)
    return lead, (m.group(1) if m else ""), (rest[m.end():] if m else rest)


def parse_short(name: str) -> tuple[str, str] | None:
    """(role, id3) from a PH, worker, C-level or Watch name, old or new shape, else None.
    A worker's short word must be one of WORKER_SHORT's, so "PH#…" and look-alikes never read
    as one. A name with no id (the COO's "COO SomPong") gives an empty id3; an old C-level
    name ("CTO (Kavin)") gives None: tools/live_sessions reads those by the record instead."""
    body = split_name(name)[2]
    if PH_NAME_RE.match(body):
        return "project_head", PH_NAME_RE.match(body).group("id3")
    m = WORKER_NAME_RE.match(body)
    if m and m.group("short") in SHORT_TO_ROLE:
        return SHORT_TO_ROLE[m.group("short")], m.group("id3")
    m = _WATCH_RE.match(body)
    if m:
        return "watch", m.group("id3")
    m = _C_LEVEL_BODY_RE.match(body)
    if m and m.group("topic") is not None and m.group("role") != "CEO":
        if m.group("id3") or m.group("role") in _NO_ID_ROLES:
            return m.group("role").lower(), m.group("id3") or ""
    return None


def _tidy_topic(topic: str, role: str) -> str:
    """A topic as the new shape wants it: "CTO Main" -> "Main" (the role is in the name
    already) and "PH LastBell + Scriptable" -> "LastBell+Scriptable" (a CTO that was
    labelled by the PH job it did)."""
    t = " ".join((topic or "").split())
    m = re.match(r"PH\s+(.+)$", t)
    if m:
        return re.sub(r"\s*\+\s*", "+", m.group(1))
    m = re.match(rf"{re.escape(role.upper())}\s+(.+)$", t, re.IGNORECASE)
    return m.group(1) if m else t


def clevel_topic(body: str, role: str) -> str:
    """The topic a C-level body carries in any shape ("" when it carries none)."""
    m = _C_LEVEL_BODY_RE.match(body)
    if m:
        topic = m.group("topic") or (m.group("otopic") or "")[len(" — "):]
    else:
        lm = _MACHINE_LONG_RE.match(body)
        topic = (lm.group("topic") or "") if lm else ""
    return _tidy_topic(topic, role)


def ph_topic(body: str) -> tuple[str, str]:
    """(projects, topic) a PH body carries: old "PH#7cf (CTO) - A + B — t" -> ("A+B", "t");
    new "PH#7cf text" -> ("", "text") (the project or a topic: the caller knows which)."""
    m = PH_NAME_RE.match(body)
    if not m:
        return "", ""
    if m.group("lane"):
        return re.sub(r"\s*\+\s*", "+", (m.group("proj") or "").strip()), (m.group("otopic") or "").strip()
    return "", m.group("text").strip()


def worker_parts(body: str) -> tuple[str, str, str] | None:
    """(Short, head, job) of a worker body in either shape, else None. Only a one-word
    text before the first ": " is a head ("Item 5: sparse" has none)."""
    m = WORKER_NAME_RE.match(body)
    if not m:
        return None
    rest = m.group("rest") or ""
    rest = rest[2:] if rest.startswith("- ") else rest
    head, sep, job = rest.partition(": ")
    if sep and _HEAD_TOKEN_RE.fullmatch(head):
        return m.group("short"), head, job.strip()
    return m.group("short"), "", rest.strip()


def _is_old_shape(body: str, role: str) -> bool:
    if _MACHINE_LONG_RE.match(body):
        return True
    if role == "project_head":
        m = PH_NAME_RE.match(body)
        return bool(m and m.group("lane"))
    if role in WORKER_SHORT:
        m = WORKER_NAME_RE.match(body)
        rest = m and m.group("rest")
        return bool(m and not m.group("model") and (rest is None or rest.startswith("- ")))
    m = _C_LEVEL_BODY_RE.match(body)
    return bool(m and m.group("role") == role.upper() and m.group("id3") is None
                and m.group("topic") is None)


def rule_problem(name: str, role: str, sid: str, host: str | None,
                 persona: str | None = None, windows: bool = False) -> str | None:
    """Why `name` is off the rule for a session of `role`/`sid` on `host`, or None.
    Roles with no rule ("unknown", "ceo") are never off it. An old-shape name is "old shape",
    whatever else it lacks: one rename fixes both. `persona` is unused since the persona left
    the name (15 Oct); it stays so callers do not change. `windows` is True on a Windows
    host, where a worker's name carries no emoji."""
    is_worker = role in WORKER_SHORT
    is_c_level = bool(re.fullmatch(r"c[a-z]o", role or "")) and role != "ceo"
    if role != "project_head" and not is_worker and not is_c_level:
        return None
    _lead, got, body = split_name(name)
    if _is_old_shape(body, role):
        return "old shape"
    want = "" if (is_worker and windows) else HOST_EMOJI.get(host or "", "")
    if want and not got:
        return "no host emoji"
    if got and got != want.rstrip("️"):
        return "wrong host emoji" if want else "a host emoji where none belongs"
    if role == "project_head":
        pm = PH_NAME_RE.match(body)
        if not pm or pm.group("lane"):
            return 'not "PH#<id3> <Project>"'
        if sid and pm.group("id3") != sid[:3]:
            return f"PH#{pm.group('id3')} is not this session (#{sid[:3]})"
    elif is_worker:
        wm = WORKER_NAME_RE.match(body)
        sep = "." if windows else _DOT
        if (not wm or wm.group("short") != WORKER_SHORT[role]
                or (wm.group("sep") and wm.group("sep") != sep)):
            return f'not "{WORKER_SHORT[role]}{sep}<O|S|H>#<id3> <Head>: <job>"'
        if sid and wm.group("id3") != sid[:3]:
            return f"{wm.group('short')}#{wm.group('id3')} is not this session (#{sid[:3]})"
    else:
        cm = _C_LEVEL_BODY_RE.match(body)
        no_id = role.upper() in _NO_ID_ROLES
        if (not cm or cm.group("topic") is None or cm.group("role") != role.upper()
                or bool(cm.group("id3")) == no_id):
            return f'not "{role.upper()}{"" if no_id else "#<id3>"} <topic>"'
        if sid and cm.group("id3") and cm.group("id3") != sid[:3]:
            return f"{role.upper()}#{cm.group('id3')} is not this session (#{sid[:3]})"
    if len(body) > NAME_BODY_MAX:
        return f"body is {len(body)} characters (max {NAME_BODY_MAX})"
    return None


if __name__ == "__main__":
    # `python lib/session_names.py prefix <host>`: the emoji, or nothing
    # `python lib/session_names.py clevel <role> <sid> <host> [persona]` / `ph <sid> <host> <project>`: the
    # birth name the launchers (cto-claude.sh, cxo-claude.sh) pass to `claude -n`, or nothing
    import sys
    argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == "prefix":
        sys.stdout.write(HOST_EMOJI.get(argv[1], ""))
        sys.exit(0)
    if len(argv) in (4, 5) and argv[0] == "clevel" and re.fullmatch(r"c[a-z]o", argv[1]) and argv[1] != "ceo":
        sys.stdout.write(clevel_name(argv[1], argv[2], "", argv[3], argv[4] if len(argv) == 5 else ""))
        sys.exit(0)
    if len(argv) == 4 and argv[0] == "ph" and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", argv[3]):
        sys.stdout.write(ph_session_name(argv[1], argv[3], argv[2]))
        sys.exit(0)
    sys.stderr.write("usage: session_names.py prefix <host> | clevel <role> <sid> <host> [persona] "
                     "| ph <sid> <host> <project>\n")
    sys.exit(2)
