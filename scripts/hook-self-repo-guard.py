#!/usr/bin/env python3
"""PreToolUse hook — a DEV may not mutate the runtime that is running it.

ADR 0020 (`org:decisions/0020-runtime-self-protection-guards.md`). DEVs work in
`worktrees/mooniex-agents__<role>__task-XXXXXXXX/` — git worktrees of the org
runtime itself. A DEV given a task in `mooniex-agents` is editing the code that
spawned it, the code that will review it, and the code that will merge it.
Nothing refused a write to a load-bearing path before this hook. Related
incidents: `git add -A` smuggling destructive diffs into a merge (2026-07-18),
`merge_task` deleting a branch while merging nothing yet reporting merged=true.

The escape hatch IS the design: a write is allowed if the task's declared
`touches` names the path. `touches` is written by a C-level at `create_task`
time, before any agent runs. An undeclared write to a load-bearing path is by
definition unplanned, and unplanned writes to the runtime are the failure mode.

Scope: only acts when the session cwd is inside a DEV worktree. A C-level
session in the repo root is unaffected — the hook exits 0 immediately.

Fails CLOSED. If it cannot decide (DB unreadable, task id unparseable,
malformed payload) it refuses: a false block is loud, a false allow is silent.

Reads the Claude Code hook event from stdin:
  {"session_id": "...", "cwd": "...", "tool_name": "Edit",
   "tool_input": {"file_path": "...", ...}, ...}

Exit 0 = allow (silent). Exit 2 = block, stderr goes back to the model.

There is deliberately NO environment escape hatch. Disabling this guard is the
CEO's call at the settings.json level, not an agent's at runtime.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import sqlite3
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from lib import db as db_lib  # noqa: E402

# Per-call fail-open budget for the (now possibly remote, tailnet-hop) hub --
# docs/design/tasks-db-hub.md §2: blocking every Edit/Write/Bash because the
# hub is briefly slow/unreachable is worse than skipping this guard once.
HUB_TIMEOUT_S = 3.0

# A worktree is ".../worktrees/mooniex-agents__<role>__task-XXXXXXXX".
WORKTREE_PARENT_DIR = "worktrees"
WORKTREE_PREFIX = "mooniex-agents__"
TASK_ID_RE = re.compile(r"(task-[0-9a-zA-Z]+)$")

TOOLS_WATCHED = {"Edit", "Write", "Bash"}

# --- protected, repo-relative to the DEV's own worktree (ADR 0020) ---
PROTECTED_PREFIXES = (
    "lib/", "runners/", "tools/", "policies/", "config/", "state/locks/",
)
PROTECTED_EXACT = (
    ".claude/settings.json", "state/tasks.db",
)
PROTECTED_GLOBS = (
    "scripts/hook-*.py",
    "state/tasks.db*",      # -wal / -shm are the same database
)
# A path component named any of these is protected wherever it appears, so a
# venv or a git dir is covered no matter how deep it is nested.
PROTECTED_COMPONENTS = {".venv", "venv", ".git"}

# Destructive command words whose arguments we inspect. Not exhaustive by
# design — the test module lists what slips past.
_ARG_DESTRUCTIVE = {"rm", "mv", "cp", "truncate", "shred", "tee", "sed", "dd",
                    "install", "unlink", "rmdir"}
# Marker for commands that ignore their arguments and hit the whole tree.
_WHOLE_TREE = "\x00whole-tree"

_FLAG_WITH_VALUE = {"-s", "--size", "-e", "--expression", "-f", "--file",
                    "-t", "--target-directory", "-S", "--suffix"}
_SKIP_LEADING = {"sudo", "env", "nohup", "time", "command", "exec", "builtin"}
_REDIRECT_RE = re.compile(r"\d?>>?\s*([^\s;&|<>()]+)")


class GuardError(Exception):
    """Raised when the guard cannot decide. Always becomes a refusal."""


class HubUnreachable(Exception):
    """ORG_DB_URL is set and the registry could not even be connected to
    within HUB_TIMEOUT_S. Handled as fail-OPEN by decide() -- distinct from
    GuardError (fail-CLOSED), which stays for every case where the hub
    answered but something about the data was wrong (see load_touches)."""


# --------------------------------------------------------------------------
# location
# --------------------------------------------------------------------------

def worktree_root(cwd: str | os.PathLike) -> Path | None:
    """The DEV worktree containing `cwd`, or None if cwd is not in one."""
    p = Path(cwd)
    for candidate in (p, *p.parents):
        if (candidate.parent.name == WORKTREE_PARENT_DIR
                and candidate.name.startswith(WORKTREE_PREFIX)):
            return candidate
    return None


def task_id_of(root: Path) -> str:
    m = TASK_ID_RE.search(root.name)
    if not m:
        raise GuardError(
            f"worktree directory name {root.name!r} does not end in a task id "
            "(expected ...__task-XXXXXXXX), so the declared `touches` cannot "
            "be looked up"
        )
    return m.group(1)


def db_path_for(root: Path) -> Path:
    """Canonical tasks.db of the checkout this worktree belongs to.

    `<checkout>/worktrees/<name>` -> `<checkout>/state/tasks.db`. On the Mac
    that resolves to /Users/gob/Projects/Agents/state/tasks.db and on Contabo
    to /opt/mooniex-agents/state/tasks.db — never the worktree's own copy,
    which the DEV can edit.
    """
    return root.parent.parent / "state" / "tasks.db"


# --------------------------------------------------------------------------
# touches
# --------------------------------------------------------------------------

def load_touches(db: Path, task_id: str) -> list[str]:
    """Declared touches for `task_id`. Raises GuardError on any doubt --
    fails CLOSED, this hook's original contract -- once a connection to the
    registry actually exists. Raises HubUnreachable instead when ORG_DB_URL
    is set and the registry could not even be connected to within
    HUB_TIMEOUT_S; the caller (decide()) treats that one case as fail-OPEN
    (docs/design/tasks-db-hub.md #2) rather than a refusal.

    `db` is passed explicitly (db_path_for(root), this DEV worktree's own
    checkout) rather than trusting this process's ORG_ROOT/__file__
    resolution -- under SQLite that is the one thing that tells this hook
    which checkout's tasks.db to read (and lets its tests inject a fixture
    path); under Postgres it is ignored, since ORG_DB_URL names one global
    registry regardless of which checkout asks (see lib.db.get_conn).
    """
    connected = False
    try:
        with db_lib.get_conn(path=db, readonly=True, timeout=HUB_TIMEOUT_S) as conn:
            connected = True
            row = conn.execute(
                "SELECT touches FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
    except Exception as exc:              # noqa: BLE001 — any failure = refuse
        if not connected and os.environ.get("ORG_DB_URL", "").strip():
            raise HubUnreachable(str(exc)) from exc
        if not db.exists():
            raise GuardError(f"tasks.db not found at {db}") from exc
        raise GuardError(f"cannot read {db}: {exc}") from exc

    if row is None:
        raise GuardError(f"no task row {task_id!r} in {db}")
    try:
        declared = json.loads(row["touches"] or "[]")
    except Exception as exc:              # noqa: BLE001
        raise GuardError(f"touches for {task_id} is not valid JSON: {exc}") from exc
    if not isinstance(declared, list):
        raise GuardError(f"touches for {task_id} is not a list")
    return [str(t).strip().lstrip("/") for t in declared if str(t).strip()]


def is_declared(rel: str, touches: list[str]) -> bool:
    """Same coverage semantics as tools/git_ops._touches_violation.

    Exact match, a declared directory prefix, or a declared glob.
    """
    return any(
        rel == t or rel.startswith(t.rstrip("/") + "/") or fnmatch.fnmatch(rel, t)
        for t in touches
    )


# --------------------------------------------------------------------------
# path classification
# --------------------------------------------------------------------------

def protected_reason(rel: str) -> str | None:
    """Why `rel` (repo-relative, worktree-local) is load-bearing, else None."""
    rel = rel.strip().lstrip("/")
    if rel in ("", ".", "./"):
        return ("it is the worktree root itself, and a write there can hit "
                "every protected path under it")
    for comp in Path(rel).parts:
        if comp in PROTECTED_COMPONENTS:
            return (f"it contains a {comp!r} directory — the running "
                    f"interpreter / git state of this checkout")
    for pref in PROTECTED_PREFIXES:
        if rel == pref.rstrip("/") or rel.startswith(pref):
            return f"it is under {pref} — load-bearing org runtime"
    if rel in PROTECTED_EXACT:
        return f"{rel} is load-bearing org runtime"
    for pat in PROTECTED_GLOBS:
        if fnmatch.fnmatch(rel, pat):
            return f"it matches {pat} — load-bearing org runtime"
    return None


def _real(path: Path) -> Path:
    """realpath that tolerates a non-existent leaf but follows a symlinked one."""
    if path.is_symlink() or path.exists():
        return Path(os.path.realpath(str(path)))
    return Path(os.path.realpath(str(path.parent))) / path.name


def classify(raw: str, cwd: Path, root: Path) -> tuple[str, str] | None:
    """Classify a write target. Returns (shown_path, reason) if protected.

    Inside the worktree -> repo-relative protection check. Outside it but
    inside the parent checkout -> always refused: that is the live runtime the
    CTO reviews and merges from, and no worktree-relative `touches` can
    legitimately name it. Anywhere else -> refused only if it carries a
    protected component (.git / venv), so scratchpads and /tmp stay usable.
    """
    raw = raw.strip().strip("'\"")
    if not raw:
        return None
    abs_target = Path(os.path.normpath(os.path.join(str(cwd), raw)))
    real_target = _real(abs_target)
    real_root = Path(os.path.realpath(str(root)))
    real_parent = real_root.parent.parent

    if (real_target == real_root
            or str(real_target).startswith(str(real_root) + os.sep)):
        rel = os.path.relpath(str(real_target), str(real_root))
        reason = protected_reason(rel)
        return (rel, reason) if reason else None

    if (real_target == real_parent
            or str(real_target).startswith(str(real_parent) + os.sep)):
        return (str(real_target),
                f"it resolves OUTSIDE this worktree into the live checkout at "
                f"{real_parent} (written as {raw!r}) — that is the runtime the "
                f"CTO reviews and merges from, and it is never writable from "
                f"a DEV, declared or not")

    for comp in real_target.parts:
        if comp in PROTECTED_COMPONENTS:
            return (str(real_target),
                    f"it contains a {comp!r} directory — the running "
                    f"interpreter / git state")
    return None


# --------------------------------------------------------------------------
# bash inspection
# --------------------------------------------------------------------------

def _segments(command: str) -> list[str]:
    return [s for s in re.split(r"\|\||&&|[;\n|&]", command) if s.strip()]


def _tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _strip_leading(tokens: list[str]) -> list[str]:
    """Drop `sudo`, `env`, and VAR=value prefixes so tokens[0] is the command."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _SKIP_LEADING:
            i += 1
            continue
        head = tok.split("=", 1)[0]
        if "=" in tok and head and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", head):
            i += 1
            continue
        break
    return tokens[i:]


def _positional(tokens: list[str]) -> list[str]:
    """Non-flag arguments, skipping the value of flags known to take one."""
    out: list[str] = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        if tok.startswith("-") and tok != "-":
            if tok in _FLAG_WITH_VALUE:
                skip_next = True
            continue
        out.append(tok)
    return out


def _git_targets(args: list[str]) -> list[str]:
    """Destructive git subcommands. Whole-tree forms return the marker."""
    if not args:
        return []
    sub = next((a for a in args if not a.startswith("-")), "")
    if not sub:
        return []
    rest = args[args.index(sub) + 1:]
    if sub == "clean" and any(a.startswith("-") and ("f" in a or "x" in a)
                              for a in args):
        return [_WHOLE_TREE]
    if sub == "reset" and "--hard" in args:
        return [_WHOLE_TREE]
    if sub in ("checkout", "restore"):
        if "--" in args:
            paths = args[args.index("--") + 1:]
            return paths or [_WHOLE_TREE]
        if sub == "checkout" and any(a in ("-f", "--force") for a in args):
            return [_WHOLE_TREE]
        if sub == "restore":
            return _positional(rest) or [_WHOLE_TREE]
    return []


def bash_targets(command: str) -> list[str]:
    """Write/delete targets a shell command obviously aims at.

    Deliberately shallow — see the test module for what is NOT caught.
    """
    targets: list[str] = []
    for seg in _segments(command):
        # redirections, in any of `> f`, `>>f`, `2> f` forms
        for m in _REDIRECT_RE.finditer(seg):
            tgt = m.group(1).strip("'\"")
            if tgt and not tgt.startswith("&") and tgt != "/dev/null":
                targets.append(tgt)

        tokens = _strip_leading(_tokens(seg))
        if not tokens:
            continue
        cmd = Path(tokens[0]).name
        args = tokens[1:]

        if cmd == "git":
            targets.extend(_git_targets(args))
        elif cmd == "dd":
            targets.extend(a.split("=", 1)[1] for a in args if a.startswith("of="))
        elif cmd == "sed":
            if any(a == "-i" or (a.startswith("-i") and not a.startswith("--"))
                   or a.startswith("--in-place") for a in args):
                # every non-flag arg; the script expression is harmless noise
                targets.extend(_positional(args))
        elif cmd in _ARG_DESTRUCTIVE:
            targets.extend(_positional(args))
    return [t for t in targets if t]


# --------------------------------------------------------------------------
# decision
# --------------------------------------------------------------------------

def _refusal(target: str, reason: str, task_id: str, touches: list[str],
             tool: str) -> str:
    declared = ", ".join(touches) if touches else "(nothing declared)"
    return (
        f"BLOCKED by self_repo_guard (ADR 0020) — this {tool} would write to:\n"
        f"    {target}\n\n"
        f"Refused because {reason}.\n\n"
        f"You are running inside a git worktree OF THE ORG RUNTIME. That path "
        f"is part of the code that spawned you, will review you, and will "
        f"merge you. Task {task_id} declared touches: {declared}\n\n"
        f"THE FIX IS TO DECLARE THE PATH, NOT TO DISABLE THE HOOK. Report the "
        f"path to the C-level that assigned this task and ask for it to be "
        f"added to the task's `touches` — a declared path passes straight "
        f"through. Do not edit .claude/settings.json, do not work around this "
        f"guard, and do not retry the same write by another route.\n\n"
        f"If the write was incidental (a scratch file, a log), put it in your "
        f"scratchpad directory instead — anything outside the runtime is "
        f"untouched by this guard."
    )


def _refusal_undecidable(detail: str, tool: str) -> str:
    return (
        f"BLOCKED by self_repo_guard (ADR 0020) — the guard could not decide "
        f"whether this {tool} targets a protected runtime path, so it refused. "
        f"It fails closed on purpose: a false block is loud, a false allow is "
        f"silent.\n\n"
        f"Reason: {detail}\n\n"
        f"This is an org-runtime problem, not something to work around. Report "
        f"it to the C-level that assigned this task."
    )


def decide(event: dict | None, *, cwd: str | None = None,
           payload_ok: bool = True) -> tuple[int, str]:
    """Return (exit_code, stderr_message). 0 = allow, 2 = refuse."""
    event = event or {}
    here = cwd or event.get("cwd") or os.getcwd()
    root = worktree_root(here)
    if root is None:
        return 0, ""                      # not a DEV worktree — inert

    tool = str(event.get("tool_name") or event.get("tool") or "")
    if not payload_ok:
        return 2, _refusal_undecidable(
            "the hook payload on stdin was not readable JSON, so neither the "
            "tool nor its target path could be determined", tool or "tool call")
    if tool not in TOOLS_WATCHED:
        return 0, ""

    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 2, _refusal_undecidable(
            "the event carried no readable tool_input", tool)

    if tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            return 2, _refusal_undecidable(
                "the Bash event carried no command string", tool)
        raw_targets = bash_targets(command)
    else:
        raw = (tool_input.get("file_path") or tool_input.get("path")
               or tool_input.get("notebook_path"))
        if not isinstance(raw, str) or not raw.strip():
            return 2, _refusal_undecidable(
                f"the {tool} event carried no file_path", tool)
        raw_targets = [raw]

    if not raw_targets:
        return 0, ""

    try:
        task_id = task_id_of(root)
        touches = load_touches(db_path_for(root), task_id)
    except HubUnreachable as exc:
        print(f"[self_repo_guard] hub unreachable within {HUB_TIMEOUT_S}s, "
              f"failing OPEN (allow): {exc}", file=sys.stderr)
        return 0, ""
    except GuardError as exc:
        return 2, _refusal_undecidable(str(exc), tool)

    cwd_path = Path(here)
    for raw in raw_targets:
        whole_tree = raw == _WHOLE_TREE
        try:
            hit = classify("." if whole_tree else raw, cwd_path, root)
        except Exception as exc:          # noqa: BLE001 — undecidable = refuse
            return 2, _refusal_undecidable(
                f"could not resolve path {raw!r}: {exc}", tool)
        if hit is None:
            continue
        shown, reason = hit
        if whole_tree:
            reason = ("it rewrites the whole worktree, which contains protected "
                      "runtime paths — scope the command to specific files "
                      "instead")
        elif is_declared(shown, touches):
            continue                      # declared up front: allowed
        return 2, _refusal(shown, reason, task_id, touches, tool)
    return 0, ""


def main() -> int:
    payload_ok = True
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event, payload_ok = {}, False
    except Exception:                     # noqa: BLE001
        event, payload_ok = {}, False

    try:
        code, message = decide(event, payload_ok=payload_ok)
    except Exception as exc:              # noqa: BLE001 — never allow by accident
        if worktree_root(os.getcwd()) is None:
            return 0
        print(_refusal_undecidable(f"guard crashed: {exc!r}", "tool call"),
              file=sys.stderr)
        return 2
    if code:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
