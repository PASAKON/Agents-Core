"""Org Mesh acceptance test (docs/design/org-mesh.md).

Prints the wiring matrix from the design doc's §1 measured tables and exits
1 when a cell that is expected green for the given `--expect` wave is red.
Every later wave adds its own level; this file builds the frame + L0-L9, the
SEC (dispatch-key security) row and the one-poller invariant.

    python3 -m tools.mesh_check --expect w0 [--live] [--no-merge]
    python3 -m tools.mesh_check --local --json          # this host only, no ssh
    python3 -m tools.mesh_check --get-task <id> --json  # local ledger read, for L4

See docs/ops/mesh-check.md for what each level proves and the design
rationale behind the EXPECT table below.

Levels:
  L0 identity  — which host am I (self_host() / tailscale / ROOT-vs-checkout
                 agreement: a host's agents_root OR its registered checkout of
                 this repo). Diagonal only (from == to).
  L1 ssh       — `ssh -o BatchMode=yes ... <alias> true` to every other host.
                 This host's own cell makes no ssh call and is "n/a".
  L2 org MCP   — start the org MCP server over stdio, tools/list includes
                 create_task + delegate_task. Diagonal only.
  L3 delegate  — --live only: create a probe task, delegate it to a target
                 host, poll to review/done, merge, verify on origin + clean
                 worktree. Only ever run for from == the host this process is
                 actually executing on (a host can prove its own outbound
                 delegate, never another host's).
  L4 ledger    — create a task on this host's ledger, ask another host
                 (read-only ssh, `--get-task`) whether it sees it. Same
                 from-== self restriction as L3.
  L5 letters   — --live only: a hub letter for a probe worker on B, delivered
                 by `mesh.dispatch(B, "deliver_letter", id)`. When L3 is claimed
                 for the same pair it runs INSIDE L3's window, on L3's probe
                 task, and also proves the wake: `woke: true` in the reply and
                 a nonce from the letter in the probe file read back from origin.
  L6 liveness  — --live only: `probe` answers in < 60 s and the hub's
                 `hosts.probed_at` is fresh by the router's own rule.
  L7 router    — --live only: `router.pick_host` on synthetic tasks
                 (`needs: always_on` -> contabo, `needs: win_gui` -> winbox).
  L8 join drill— reads state/mesh-check/join-drill.json, or with no file the newest
                 `join_drill` events row (scripts/drill-join.sh writes both); > 7 days = red.
  L9 spawn+resume — --live only: start a CTO probe, give it a turn, stop, resume,
                 and stop again. Skip at the cap of 3. Transcripts are not compared;
                 refusal without a resumable UUID proves resume found a conversation.
  SEC          — --live only: the dispatch key gets `probe` and no shell.
  INV          — read-only: every in-progress remote row has exactly one poller.

A mesh cell (SEC, L5, L6, L9) keeps three answers apart: green, red (the far side
answered wrong) and unreachable (`lib.mesh.MeshUnreachable`: no answer, so
nothing is known). Unknown is never green. A mesh cell whose target has no
`mesh_ssh` in config/hosts.yaml renders "closed (by design)" and never counts.

L0/L1/L2 are cheap, stateless, one-shot checks, so a peer host's copy of
them is collected via `--local --json`, either from an already-deployed
checkout or piped raw over ssh stdin when the tool isn't deployed there yet
(imports of repo modules are guarded — a piped script with no filesystem
context for lib/config.py degrades to "n/a" instead of crashing). L3/L4 need
either a long-lived MCP session (L3) or a real cross-host round trip (L4),
so they are never collected remotely — only computed for this process's own
host. The same own-seat rule covers SEC, L5, L9 and the L6 of a remote host: they
are computed from the host this process runs on, for its outbound row.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import copy
import importlib.util
import json
import ntpath
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Under a normal `python -m tools.mesh_check` / `python tools/mesh_check.py`
# invocation, __file__ is the real script path and ROOT is two dirs up. But
# the peer-collection fallback pipes this file over ssh stdin
# (`ssh <alias> python3 - --local --json < tools/mesh_check.py`) so it runs
# on a box that hasn't pulled this branch yet — there, __file__ is the
# literal string "<stdin>", and Path(__file__).resolve() silently resolves
# it as a file named "<stdin>" *inside* the caller's cwd, landing ROOT one
# directory above the real repo root (confirmed empirically: cwd is set
# correctly via the ssh command's `cd "<agents_root>" &&`, but the stray
# ".resolve().parent.parent" then walks past it). Detect that case and use
# cwd directly instead — the ssh command already cd'd into agents_root.
_this_file = Path(__file__).resolve()
if _this_file.name == "<stdin>":
    ROOT = Path.cwd()
else:
    ROOT = _this_file.parent.parent
sys.path.insert(0, str(ROOT))

try:
    import lib.config as config  # noqa: E402
    HAVE_CONFIG = True
    HOSTS: list[str] = list(config.hosts().keys())
except Exception:
    HAVE_CONFIG = False
    HOSTS = []

# The config/projects.yaml entry whose `paths.<host>` registers this repo's checkout.
AGENTS_PROJECT_KEY = "mooniex-agents"

WAVES = ["w0", "w1", "w2", "w3", "w4", "w5"]
LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "SEC", "INV"]

# Levels whose cells are one verdict for the whole hub, not a from x to matrix.
# Their one cell is keyed (level, "all", "all").
SINGLE_LEVELS = {"L8": "join drill", "INV": "one poller per remote row"}
# Off-diagonal levels that dial the target through its `mesh_ssh`: a target
# with none (the Mac until G2) is "closed (by design)", whoever runs the tool.
MESH_PAIR_LEVELS = ("SEC", "L5", "L9")


def _wave_index(w: str) -> int:
    return WAVES.index(w)


# ---------------------------------------------------------------------------
# EXPECT = {(level, from_host, to_host): first_wave_green}
#
# A cell key absent from this dict is never applicable (e.g. an L0/L2
# diagonal-only level has no off-diagonal entries) and always renders "n/a".
# A cell present but whose wave is later than --expect also renders "n/a"
# (not FAIL) — not yet claimed, so not yet judged.
#
# Sourced from docs/design/org-mesh.md §1 (measured 2026-09-28) + §5 (wave
# table) plus three literal examples the task brief gave verbatim:
#   ('L1','contabo','mac') -> 'w2'
#   ('L3','contabo','contabo') -> 'w0'
#   ('L3','contabo','winbox') -> 'w3'
# Every other entry below is this build's own judgment call, reasoned the
# same way (which wave's "done when" criterion first makes the cell true) —
# see docs/ops/mesh-check.md for the reasoning behind each one that isn't a
# straight "already ok today, w0".
# ---------------------------------------------------------------------------
EXPECT: dict[tuple[str, str, str], str] = {
    # L0 identity — diagonal only. Checkable today (self_host() missing is
    # tolerated as an absent source, not a disagreement) — gated at w0 so a
    # real mismatch (e.g. running from a worktree instead of the registered
    # checkout) is visible now, not hidden behind a wave.
    ("L0", "mac", "mac"): "w0",
    ("L0", "winbox", "winbox"): "w0",
    ("L0", "contabo", "contabo"): "w0",

    # L1 ssh — measured ok today for every pair except anything targeting
    # mac (sshd closed by design, no alias). The task brief's literal
    # instruction: that cell renders "closed (by design)" and only counts
    # against the exit code from w2 on.
    ("L1", "mac", "contabo"): "w0",
    ("L1", "mac", "winbox"): "w0",
    ("L1", "contabo", "winbox"): "w0",
    ("L1", "winbox", "contabo"): "w0",
    ("L1", "contabo", "mac"): "w2",
    ("L1", "winbox", "mac"): "w2",

    # L2 org MCP — diagonal only. mac + contabo already run it; winbox has
    # no launcher/venv until W3 ("winbox as a full node").
    ("L2", "mac", "mac"): "w0",
    ("L2", "contabo", "contabo"): "w0",
    ("L2", "winbox", "winbox"): "w3",

    # L3 delegate — --live only, and only ever computed for from == the
    # host actually running this process (see module docstring). mac's
    # outbound delegates already work today (1c). contabo->contabo is
    # broken today (ssh's itself with no self alias) but is explicitly the
    # W0 "done when" criterion (C1+C5 default host = self). contabo->mac
    # needs W2 (pull-model delegate without ssh). contabo->winbox is given
    # literally as w3 in the brief, despite merge-anywhere (C5) landing in
    # W0 — taken as-is rather than re-derived. winbox as a "from" needs W3
    # (org MCP on winbox) before it can delegate anywhere at all.
    ("L3", "mac", "mac"): "w0",
    ("L3", "mac", "contabo"): "w0",
    ("L3", "mac", "winbox"): "w0",
    ("L3", "contabo", "contabo"): "w0",
    ("L3", "contabo", "mac"): "w2",
    ("L3", "contabo", "winbox"): "w3",
    ("L3", "winbox", "mac"): "w3",
    ("L3", "winbox", "contabo"): "w3",
    ("L3", "winbox", "winbox"): "w3",

    # L4 ledger — red today by design (one sqlite per host), green from w1
    # (Postgres hub cutover), per the brief's literal ('L4',*,*) example.
    # Diagonal not applicable (a host trivially sees its own task; that's
    # not the federation question being tested).
    ("L4", "mac", "contabo"): "w1",
    ("L4", "mac", "winbox"): "w1",
    ("L4", "contabo", "mac"): "w1",
    ("L4", "contabo", "winbox"): "w1",
    ("L4", "winbox", "mac"): "w1",
    ("L4", "winbox", "contabo"): "w1",

    # L5 letters — a hub letter delivered through the dispatch key. Mac <->
    # Contabo is the W2 "done when" line; anything touching winbox waits for
    # W3 (node_dispatch on Windows). Into the Mac the cell is "closed (by
    # design)" until its hosts.yaml gets a mesh_ssh, whatever the wave.
    ("L5", "mac", "contabo"): "w2",
    ("L5", "contabo", "mac"): "w2",
    ("L5", "mac", "winbox"): "w3",
    ("L5", "winbox", "mac"): "w3",
    ("L5", "contabo", "winbox"): "w3",
    ("L5", "winbox", "contabo"): "w3",

    # L6 liveness — diagonal: "is this host answering, as seen from here".
    # winbox needs node_dispatch on Windows (W3).
    ("L6", "mac", "mac"): "w2",
    ("L6", "contabo", "contabo"): "w2",
    ("L6", "winbox", "winbox"): "w3",

    # L7 router — diagonal on the host the task must land on:
    # `needs: always_on` -> contabo (W2.6), `needs: win_gui` -> winbox (W3).
    ("L7", "contabo", "contabo"): "w2",
    ("L7", "winbox", "winbox"): "w3",

    # L8 join drill — one verdict for the hub; the drill is W4.7.
    ("L8", "all", "all"): "w4",

    # SEC — the dispatch key gets `probe` and no shell, every direction. Mac
    # <-> Contabo is W2 ("the security cell is green"); anything touching
    # winbox waits for W3, like L5/L6/L7: node_dispatch on Windows and the
    # winbox forced-command line are W3.3/W3.4 (docs/ops/node-dispatch.md).
    # The cells into the Mac are closed (by design) until it has a mesh_ssh.
    ("SEC", "mac", "contabo"): "w2",
    ("SEC", "contabo", "mac"): "w2",
    ("SEC", "mac", "winbox"): "w3",
    ("SEC", "contabo", "winbox"): "w3",
    ("SEC", "winbox", "contabo"): "w3",
    ("SEC", "winbox", "mac"): "w3",

    # INV — "every in-progress remote row is polled by exactly one host" is a
    # statement about the shared hub ledger (the W1.5 duty split), so it is
    # claimed with the hub, w1. Read-only.
    ("INV", "all", "all"): "w1",
}


# ---------------------------------------------------------------------------
# Small helpers shared by every level
# ---------------------------------------------------------------------------

EXPECT.update({("L9", frm, to): wave for (level, frm, to), wave in list(EXPECT.items())
               if level == "L5"})


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def _org_server_launch(root: Path, python: Path) -> tuple[str, list[str]]:
    """(command, args) for the org MCP server, built by the generator every real
    session uses (scripts/lib/cxo_mcp_config.py), so a probe reaches the same
    ledger: wrapped when `org_db: hub` is set on this host and its env file
    exists, plain otherwise. Only a MISSING generator falls back to the plain
    launch (a peer box that has not pulled it yet); any error in it propagates."""
    plain = (str(python), ["-m", "runners.cto_mcp_server"])
    src = ROOT / "scripts" / "lib" / "cxo_mcp_config.py"
    if not src.is_file():
        return plain
    spec = importlib.util.spec_from_file_location("cxo_mcp_config", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    entry = mod._build("org", str(root))
    if not entry:
        return plain
    return entry["command"], list(entry.get("args", []))


def _ssh_run(alias: str, remote_cmd: str, *, timeout: int,
             stdin_path: Path | None = None) -> str | None:
    """Run `remote_cmd` on `alias` over ssh. Returns stdout, or None on any
    failure (unreachable, timeout, non-zero exit) — never raises."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", alias, remote_cmd]
    try:
        if stdin_path is not None:
            with open(stdin_path, "rb") as f:
                r = subprocess.run(cmd, stdin=f, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout)
        else:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def _try_json(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _norm_cell(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return {"ok": bool(raw.get("ok")), "reason": raw.get("reason")}


def _to_cell(pair: tuple[bool, str | None]) -> dict:
    ok, reason = pair
    return {"ok": ok, "reason": reason}


def _na() -> dict:
    """A cell with nothing to judge (L1 from a host to itself). `ok` is True so
    a reader that only looks at `ok` never sees a failure; `kind` "n/a" makes
    render() print "n/a" and never count it."""
    return {"ok": True, "reason": "n/a", "kind": "n/a"}


def _l1_cell(target_host_key: str, me: str | None) -> dict:
    """The L1 cell for `target_host_key`, from the host the caller calls `me`.
    A target equal to `me` makes NO ssh call (a host cannot always resolve its
    own alias: winbox cannot) and is n/a, like the L1 diagonal in the matrix;
    every other target is the ssh answer.

    `me` is the ONE identity of the run: the host the matrix labels its row
    with (`_running_host_guess`). It is never read from `self_host()` here: a
    second source that disagrees (a worktree, a box whose node.yaml says
    something else) would turn a red L1 cell into an uncounted n/a. `me` None
    (identity unknown) dials every target, so nothing is ever skipped."""
    if me is not None and target_host_key == me:
        return _na()
    return _to_cell(check_l1(target_host_key))


def _tailscale_guess_host() -> str | None:
    """Best-effort: match `tailscale status --json` Self.HostName/DNSName
    against a host key or its ssh alias. None if tailscale is unavailable,
    unparsable, or nothing matches — never raises."""
    if not HAVE_CONFIG:
        return None
    try:
        r = subprocess.run(["tailscale", "status", "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    data = _try_json(r.stdout)
    if not data:
        return None
    self_info = data.get("Self") or {}
    haystack = f"{self_info.get('HostName', '')} {self_info.get('DNSName', '')}".lower()
    if not haystack.strip():
        return None
    for h, cfg in config.hosts().items():
        candidates = {h.lower()}
        alias = cfg.get("ssh")
        if alias:
            candidates.add(str(alias).lower())
        if any(c and c in haystack for c in candidates):
            return h
    return None


def _path_key(p) -> str | None:
    """Comparable form of a configured checkout path. A path that exists on
    this machine is symlink-resolved first. A drive-letter path (winbox) then
    goes through ntpath, so case and `/` vs `\\` stop mattering; anything
    else is normalised the POSIX way and stays case-sensitive."""
    s = str(p) if p else ""
    if not s:
        return None
    try:
        if os.path.exists(s):
            s = os.path.realpath(s)
    except (OSError, ValueError):
        pass
    if re.match(r"^[A-Za-z]:", s):
        return ntpath.normcase(ntpath.normpath(s))
    return os.path.normpath(s)


def _registered_checkouts() -> dict[str, str]:
    """host key -> where config/projects.yaml registers this repo's checkout
    (`paths.<host>` of the `mooniex-agents` entry), through lib.config. {} when
    the project or its `paths` is missing, so L0 then falls back to agents_root."""
    try:
        entry = config.projects().get(AGENTS_PROJECT_KEY) or {}
    except Exception:
        return {}
    return {h: p for h, p in (entry.get("paths") or {}).items() if p}


def _root_match_host(root: Path) -> str | None:
    """Which host, if any, has `root` as its `agents_root` (config/hosts.yaml)
    OR as its registered checkout of this repo (`paths.<host>` of the
    `mooniex-agents` entry in config/projects.yaml). The second source is
    needed where `agents_root` is the spawn directory, not this checkout
    (winbox). Always contributes a real answer (never "unavailable") — a
    checkout that matches neither is itself a meaningful (disagreeing) signal,
    e.g. running from a worktree."""
    if not HAVE_CONFIG:
        return None
    want = _path_key(root)
    if want is None:
        return None
    checkouts = _registered_checkouts()
    for h, cfg in config.hosts().items():
        if want in (_path_key(cfg.get("agents_root")), _path_key(checkouts.get(h))):
            return h
    return None


def _running_host_guess(root: Path) -> str | None:
    """Best single guess at which host this process is on, for matrix
    labeling only — not the strict multi-source agreement L0 itself checks."""
    return _root_match_host(root) or _tailscale_guess_host()


# ---------------------------------------------------------------------------
# L0 — identity
# ---------------------------------------------------------------------------

def check_l0(root: Path) -> tuple[bool, str | None]:
    if not HAVE_CONFIG:
        return False, "no repo access"
    sources: dict[str, str] = {}
    try:
        sh = config.self_host()
        if sh:
            sources["self_host"] = sh
    except (AttributeError, ValueError, RuntimeError):
        # AttributeError: pre-W0.1 config.py (self_host() didn't exist yet).
        # ValueError/RuntimeError: self_host() itself can't resolve (bad
        # ORG_HOST/node.yaml, unregistered box) — check_l0 is a diagnostic
        # and must degrade to "source absent", never crash or false-flag a
        # disagreement just because self_host() had nothing to say.
        pass
    ts = _tailscale_guess_host()
    if ts is not None:
        sources["tailscale"] = ts
    sources["root_match"] = _root_match_host(root) or "(unregistered)"
    if not sources:
        return False, "no identity source available"
    if len(set(sources.values())) == 1:
        return True, None
    detail = ", ".join(f"{k}={v}" for k, v in sorted(sources.items()))
    return False, f"sources disagree: {detail}"


# ---------------------------------------------------------------------------
# L1 — ssh
# ---------------------------------------------------------------------------

def check_l1(target_host_key: str) -> tuple[bool, str | None]:
    if not HAVE_CONFIG:
        return False, "no repo access"
    try:
        cfg = config.host(target_host_key)
    except ValueError as e:
        return False, str(e)[:200]
    alias = cfg.get("ssh")
    if not alias:
        return False, "closed (by design)"
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", alias, "true"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=15)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if r.returncode == 0:
        return True, None
    if cfg.get("os") == "windows":
        cmd2 = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", alias,
                "cmd", "/c", "exit", "0"]
        try:
            r2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=15)
        except subprocess.TimeoutExpired:
            return False, "timeout"
        if r2.returncode == 0:
            return True, None
        return False, (r2.stderr or r2.stdout or "ssh failed").strip()[:200]
    return False, (r.stderr or r.stdout or "ssh failed").strip()[:200]


# ---------------------------------------------------------------------------
# L2 — org MCP
# ---------------------------------------------------------------------------

async def check_l2(root: Path) -> tuple[bool, str | None]:
    python = _venv_python(root)
    if not python.exists():
        return False, ".venv missing"
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        return False, f"mcp package unavailable: {e}"[:200]

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    try:
        command, args = _org_server_launch(root, python)
        params = StdioServerParameters(command=command, args=args, cwd=str(root), env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=20)
                result = await asyncio.wait_for(session.list_tools(), timeout=20)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]

    names = {t.name for t in result.tools}
    missing = {"create_task", "delegate_task"} - names
    if missing:
        return False, f"missing tools: {sorted(missing)}"
    return True, None


# ---------------------------------------------------------------------------
# L3 — delegate (--live only)
# ---------------------------------------------------------------------------

def _first_text(call_tool_result) -> str:
    for block in getattr(call_tool_result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            return text
    return ""


def _toon_field(text: str, key: str) -> str | None:
    """Pull `key: value` out of a TOON-encoded scalar field (lib/toon.py's
    dict encoding) — no decoder exists for the format, and a regex on one
    known field is simpler than writing one for this narrow use."""
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _role_exists(name: str) -> bool:
    if not HAVE_CONFIG:
        return False
    try:
        return name in config.agents().get("roles", {})
    except Exception:
        return False


def _register_probe_session(session_id: str, host: str) -> None:
    """Same code path tools/session_charter.py uses — register a
    c_level_sessions row + a one-line charter so create_task's charter gate
    (lib/db.py _require_charter) doesn't refuse the probe task. Never
    ORG_CHARTER_GATE=off (that's a setup/repair escape hatch only)."""
    from lib import db as db_mod
    from tools import session_charter
    os.environ["CTO_SESSION_ID"] = session_id
    db_mod.register_cxo_session("cto", session_id, host=host)
    session_charter.set_charter(f"mesh_check L3 org-mesh probe on {host} ({session_id})")


def _git_ls_remote_has(root: Path, sha: str) -> bool:
    try:
        r = subprocess.run(["git", "ls-remote", "origin"], cwd=str(root),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return r.returncode == 0 and sha in r.stdout


_GIT_STATUS_FAILED = "git status failed"


def _git_status_porcelain(root: Path) -> str:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return _GIT_STATUS_FAILED
    return r.stdout.strip()


def _new_tracked_dirt(before: str, after: str) -> list[str]:
    """`git status --porcelain` lines in `after` that `before` did not have,
    untracked (`??`) entries left out.

    L3 asks whether ITS cycle dirtied this host's runtime checkout, not
    whether that checkout is clean. A live checkout can carry another
    session's WIP, or the harness's model line in claude-home/settings.json,
    for days, and other sessions keep writing untracked state files while
    the probe runs. merge_task can only change tracked files there (the
    best-effort fast-forward, or an in-place merge on a project with no
    origin), so a new tracked entry is the signal."""
    seen = set(before.splitlines())
    return [line for line in after.splitlines()
            if line not in seen and not line.startswith("??")]


def _git_show_from_origin(root: Path, rev: str, path: str) -> tuple[str | None, str]:
    """(file text, "") for `path` at `rev` after a `git fetch origin`, else
    (None, why). `rev` is a merge sha (it is on origin: L3 checked) or
    `origin/<branch>`. A failed fetch is not an answer by itself: the show
    decides, and names the fetch when it fails too."""
    fetch_note = ""
    try:
        f = subprocess.run(["git", "fetch", "--quiet", "origin"], cwd=str(root),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60)
        if f.returncode != 0:
            fetch_note = f" (git fetch origin failed: {(f.stderr or '').strip()[:100]})"
    except (subprocess.TimeoutExpired, OSError) as e:
        fetch_note = f" (git fetch origin failed: {type(e).__name__})"
    try:
        r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=str(root),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, f"git show failed: {type(e).__name__}{fetch_note}"
    if r.returncode != 0:
        return None, f"git show {rev[:20]}:{path}: {(r.stderr or '').strip()[:150]}{fetch_note}"
    return r.stdout, ""


async def run_l3_probe(from_host: str, to_host: str, root: Path, expect: str,
                       no_merge: bool, l5: "L5Window | None" = None) -> tuple[bool, str | None]:
    """The L3 cell for (from_host, to_host): (ok, reason). With `l5` (an
    L5Window) the L5 letter is sent inside this window and the L5 cell is left
    in `l5.cell`; it never changes what this function returns."""
    ok, reason = await _l3_cycle(from_host, to_host, root, expect, no_merge, l5)
    if l5 is not None:
        l5.close(reason)
    return ok, reason


async def _l3_cycle(from_host: str, to_host: str, root: Path, expect: str,
                    no_merge: bool, l5: "L5Window | None") -> tuple[bool, str | None]:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        return False, f"mcp package unavailable: {e}"[:200]

    session_id = f"mesh-check-{uuid.uuid4().hex[:8]}"
    try:
        _register_probe_session(session_id, from_host)
    except Exception as e:
        return False, f"charter registration failed: {type(e).__name__}: {e}"[:200]

    python = _venv_python(root)
    if not python.exists():
        return False, ".venv missing"
    dirt_before = _git_status_porcelain(root)
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["CTO_SESSION_ID"] = session_id
    try:
        command, args = _org_server_launch(root, python)
        params = StdioServerParameters(command=command, args=args, cwd=str(root), env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=20)

                role = "probe" if _role_exists("probe") else "developer"
                probe_path = f"docs/ops/mesh-probe/{from_host}-{to_host}.md"
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                description = (
                    f"mesh-check L3 probe ({from_host} -> {to_host}, expect={expect}).\n\n"
                    f"Overwrite {probe_path} with exactly one line:\n"
                    f"`mesh-probe {from_host}->{to_host} {ts}`\n\n"
                    f"{l5.instructions() if l5 is not None else ''}"
                    f"Commit with a message starting `mesh-probe:`. Then report."
                )
                create_result = await asyncio.wait_for(
                    session.call_tool("create_task", {
                        "project": "mooniex-agents", "role": role,
                        "title": f"mesh-probe {from_host}->{to_host}",
                        "description": description, "touches": probe_path,
                        "host": from_host,
                    }), timeout=30)
                task_id = _first_text(create_result).strip()
                if not task_id.startswith("task-"):
                    return False, f"create_task did not return a task id: {task_id[:100]}"

                deleg_result = await asyncio.wait_for(
                    session.call_tool("delegate_task", {"task_id": task_id, "host": to_host}),
                    timeout=60)
                deleg_status = _toon_field(_first_text(deleg_result), "status")
                if deleg_status == "conflict":
                    return False, f"delegate conflict: {_first_text(deleg_result)[:200]}"

                deadline = time.monotonic() + 25 * 60
                final_status = None
                branch = None
                while time.monotonic() < deadline:
                    get_result = await asyncio.wait_for(
                        session.call_tool("get_task", {"task_id": task_id}), timeout=30)
                    get_text = _first_text(get_result)
                    final_status = _toon_field(get_text, "status")
                    branch = _toon_field(get_text, "branch") or branch
                    if l5 is not None and not l5.sent and final_status == "in_progress":
                        # The far side's reply can take a minute (ssh, wake): off the loop.
                        await asyncio.to_thread(l5.send, task_id, role)
                    if final_status in ("review", "done"):
                        break
                    if final_status in ("failed", "blocked_human", "conflict"):
                        return False, f"task ended in status={final_status}"
                    await asyncio.sleep(15)
                else:
                    return False, "timeout waiting for review/done (25 min)"

                if no_merge:
                    if l5 is not None:  # nothing was merged: the worker's branch is the proof
                        await asyncio.to_thread(l5.read_probe, root,
                                                f"origin/{branch}" if branch else None, probe_path)
                    return True, None

                merge_result = await asyncio.wait_for(
                    session.call_tool("merge_task", {"task_id": task_id}), timeout=120)
                merge_text = _first_text(merge_result)
                if _toon_field(merge_text, "merged") != "true":
                    return False, f"merge failed: {merge_text[:200]}"
                merge_sha = _toon_field(merge_text, "merge_sha")
                if not merge_sha:
                    return False, "merge succeeded but no merge_sha in result"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]

    if not _git_ls_remote_has(root, merge_sha):
        return False, f"merge_sha {merge_sha[:12]} not found on origin"
    if l5 is not None:
        await asyncio.to_thread(l5.read_probe, root, merge_sha, probe_path)
    dirt_after = _git_status_porcelain(root)
    if dirt_after == _GIT_STATUS_FAILED:
        return False, "git status failed after merge"
    new_dirt = _new_tracked_dirt(dirt_before, dirt_after)
    if new_dirt:
        return False, f"merge left the runtime checkout dirty: {'; '.join(new_dirt)[:200]}"
    return True, None


# ---------------------------------------------------------------------------
# L4 — ledger
# ---------------------------------------------------------------------------

def l4_probe(from_host: str, to_host: str) -> tuple[bool, str | None]:
    if not HAVE_CONFIG:
        return False, "no repo access"
    from lib import db as db_mod
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        task_id = db_mod.create_task(
            project="mooniex-agents", role="developer",
            title=f"mesh-check L4 probe {from_host}->{to_host} {ts}",
            description="mesh_check L4 ledger-federation probe. Safe to ignore/close.",
            host=from_host,
        )
    except Exception as e:
        return False, f"local create_task failed: {type(e).__name__}: {e}"[:200]

    try:
        return _l4_read_back(to_host, task_id)
    finally:
        # The probe only has to be seen. Since the hub cutover every host
        # shares one ledger, and a probe left pending is clutter in all of them.
        try:
            db_mod.update_status(task_id, "cancelled", actor="mesh_check")
        except Exception:
            pass


def _l4_read_back(to_host: str, task_id: str) -> tuple[bool, str | None]:
    try:
        cfg = config.host(to_host)
    except ValueError as e:
        return False, str(e)[:200]
    alias = cfg.get("ssh")
    if not alias:
        return False, "target unreachable (no ssh alias)"
    remote_root = cfg.get("agents_root")
    if not remote_root:
        return False, "target has no agents_root configured"
    if cfg.get("os") == "windows":
        python = f"{remote_root}\\.venv\\Scripts\\python.exe"
        cmd = f'cd "{remote_root}" && "{python}" -m tools.mesh_check --get-task {task_id} --json'
    else:
        # After the hub cutover an ssh shell has no ORG_DB_URL and
        # state/tasks.db is a tombstone; org-python.sh brings the URL.
        cmd = (f'cd "{remote_root}" && bash scripts/hub/org-python.sh '
               f'-m tools.mesh_check --get-task {task_id} --json')
    out = _ssh_run(alias, cmd, timeout=20)
    if out is None:
        return False, "read-only ssh to target failed"
    data = _try_json(out)
    if not data or data.get("id") != task_id:
        return False, "target does not see task (separate ledger)"
    return True, None


# ---------------------------------------------------------------------------
# Mesh levels (SEC, L5-L8, INV): cells with three answers.
#
# A cell here is a dict {"ok": bool, "reason": str | None, "kind": ..., "note": ...}.
# `kind` is absent for a plain green / red ("the far side answered, and the
# answer was wrong"). Otherwise it is one of:
#   "unreachable"  MeshUnreachable: nothing answered, so nothing is known
#   "closed"       the target has no mesh_ssh (config/hosts.yaml): never dialled
#   "not_run"      L8 only: no drill has ever written its file
#   "n/a"          L1 to this host itself: nothing to judge, never counts
# Unreachable and not_run are never green: render() counts them as failing
# when the cell is in scope, and labels them apart from a red.
# ---------------------------------------------------------------------------

def _red(reason: str) -> dict:
    return {"ok": False, "reason": reason[:300]}


def _green(note: str | None = None) -> dict:
    return {"ok": True, "reason": None, **({"note": note} if note else {})}


def _unreachable(reason: str) -> dict:
    return {"ok": False, "reason": reason[:300], "kind": "unreachable"}


def _closed() -> dict:
    return {"ok": False, "reason": "closed (by design)", "kind": "closed"}


def _mesh():
    """lib.mesh, imported late: a piped copy of this file (--local) has no repo."""
    from lib import mesh
    return mesh


def _self_host_or_none() -> str | None:
    try:
        return config.self_host()
    except (AttributeError, ValueError, RuntimeError):
        return None


def _mesh_ssh_for(host: str) -> str | None:
    """config/hosts.yaml `mesh_ssh` for `host`: a string, None when it has
    none, "?" when the config cannot say (unknown host, no repo)."""
    if not HAVE_CONFIG:
        return "?"
    try:
        return config.host(host).get("mesh_ssh")
    except ValueError:
        return "?"


def _in_scope(level: str, frm: str, to: str, expect: str) -> bool:
    first_green = EXPECT.get((level, frm, to))
    return first_green is not None and _wave_index(first_green) <= _wave_index(expect)


def _node_reply_ok(reply: dict, host: str | None = None) -> str | None:
    """Why a `probe` reply from node_dispatch is not a good one, else None."""
    if reply.get("ok") is not True:
        return f"probe refused: {str(reply.get('error'))[:200]}"
    if host is not None:
        got = (reply.get("result") or {}).get("host")
        if got != host:
            return f"probe answered as host {got!r}, expected {host!r}"
    return None


# ---------------------------------------------------------------------------
# SEC — the dispatch key gets `probe`, and no shell
# ---------------------------------------------------------------------------

# docs/ops/node-dispatch.md, "W2.8 acceptance checks", check 2, plus a bare shell.
SEC_PAYLOADS = ("probe; id", "probe && id", "$(id)", "`id`", "probe | id", "bash")


def check_sec(to_host: str) -> dict:
    """(a) a remote `probe` answers ok and says it is `to_host`; (b) each of
    SEC_PAYLOADS, sent as the raw ssh command text, is refused by node_dispatch
    and no `uid=` shows up in its stdout or stderr.

    lib.mesh refuses a bad verb before ssh, so (b) never goes through
    mesh.dispatch: it takes the argv build_argv makes for `probe`, drops the
    command and puts the payload in its place. Only an answer that is
    node_dispatch's own JSON line with ok false counts as the far side's
    refusal. A refusal made here, or no answer at all, never does."""
    if not HAVE_CONFIG:
        return _red("no repo access")
    mesh = _mesh()
    if not _mesh_ssh_for(to_host):
        return _closed()
    if to_host == _self_host_or_none():
        return _red("target is this host: an in-process call says nothing about the key")
    try:
        reply = mesh.dispatch(to_host, "probe")
    except mesh.MeshUnreachable as e:
        return _unreachable(str(e))
    except ValueError as e:
        return _red(str(e))
    why = _node_reply_ok(reply, to_host)
    if why:
        return _red(why)

    try:
        prefix = mesh.build_argv(to_host, "probe", ())[:-1]
    except mesh.MeshUnreachable as e:
        return _unreachable(str(e))
    except Exception as e:  # a Refusal: nothing was dialled, so nothing was tested
        return _red(f"argv for the shell probes was refused here, far side not tested: "
                    f"{type(e).__name__}: {e}")
    for payload in SEC_PAYLOADS:
        try:
            r = subprocess.run(prefix + [payload], capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=mesh.DEFAULT_TIMEOUT_S, stdin=subprocess.DEVNULL)
        except (subprocess.TimeoutExpired, OSError) as e:
            return _unreachable(f"{payload!r}: {type(e).__name__}")
        if r.returncode == mesh._SSH_FAILED:
            return _unreachable(f"{payload!r}: ssh failed: {(r.stderr or '').strip()[:150]}")
        if "uid=" in (r.stdout or "") or "uid=" in (r.stderr or ""):
            return _red(f"{payload!r} ran in a shell (uid= in its output)")
        lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
        try:
            answer = json.loads(lines[-1]) if lines else None
        except ValueError:
            answer = None
        if not isinstance(answer, dict) or answer.get("ok") is not False:
            return _red(f"{payload!r} was not refused by node_dispatch "
                        f"(exit {r.returncode}): {((r.stdout or '') + (r.stderr or ''))[-150:].strip()!r}")
    return _green()


# ---------------------------------------------------------------------------
# L5 — letters
# ---------------------------------------------------------------------------

L5_ROLE = "probe"
L5_FROM_ROLE = "mesh_check"


def _abandon_letter(db_mod, letter_id: int) -> None:
    """A probe letter that did not land must not wait for the watchdog's retry
    (it would reach the probe worker later, out of context). Only a `pending`
    row moves; a letter the far side did deliver stays delivered."""
    try:
        with db_mod.get_conn() as conn:
            conn.execute("UPDATE letters SET status='failed', last_error=? "
                         "WHERE id=? AND status='pending'",
                         ("mesh_check probe abandoned", letter_id))
    except Exception:
        pass


def l5_probe(from_host: str, to_host: str) -> dict:
    """A hub letter from `from_host` for the newest in-progress `probe` worker
    on `to_host`, delivered by `mesh.dispatch(to_host, "deliver_letter", id)`.

    Pass = the reply says delivered or already_delivered, names the recipient
    (`to`), the hub row is `delivered`, and the reply does not report a failed
    wake. The wake fields in a reply are `woke` / `why` (tools/node_dispatch.py:
    `_posix_wake` for the POSIX worker and C-level paths, `_windows_wake` for a
    Windows C-level letter). A worker letter on Windows reports `woke: false`
    and no `why`. This standalone form accepts an absent or bare `woke` and says
    "wake not reported"; the form that PROVES the wake is L5Window, which runs
    inside L3's window and also demands `woke: true` and the nonce in the probe
    file. This form is what runs when L3 is not claimed with L5."""
    if not HAVE_CONFIG:
        return _red("no repo access")
    from lib import db as db_mod
    mesh = _mesh()
    if not _mesh_ssh_for(to_host):
        return _closed()
    try:
        workers = [t for t in db_mod.list_tasks(status="in_progress", role=L5_ROLE, limit=100)
                   if t.get("host") == to_host]
    except Exception as e:
        return _unreachable(f"hub read failed: {type(e).__name__}: {e}")
    if not workers:
        return _red(f"no in_progress {L5_ROLE} worker on {to_host} to receive the letter")
    tid = workers[0]["id"]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = (f"mesh-check probe letter {from_host}->{to_host} {ts}. "
            "Automated Org Mesh L5 test. Ignore it: nothing to answer or do.")
    try:
        lid = db_mod.create_letter(to_host, L5_ROLE, body, to_session=tid,
                                   from_role=L5_FROM_ROLE,
                                   from_session=f"mesh-check-{uuid.uuid4().hex[:8]}",
                                   from_host=from_host)
    except Exception as e:
        return _unreachable(f"hub write failed: {type(e).__name__}: {e}")

    cell = _l5_deliver(db_mod, mesh, to_host, lid, tid)
    if not cell["ok"]:
        _abandon_letter(db_mod, lid)
    return cell


def l9_probe(from_host: str, to_host: str) -> dict:
    """Own-seat spawn/resume acceptance, with best-effort cleanup on every exit."""
    if from_host != _self_host_or_none():
        return _na()
    if not _mesh_ssh_for(to_host):
        return _closed()
    from lib import db as db_mod
    from tools import session_status
    mesh = _mesh()
    if not mesh.enabled():
        return _red("ORG_MESH_DISPATCH is disabled")
    started, stopped, stop_errors = [], set(), []
    lid = None
    cell = _red("probe incomplete")

    def stop(sid):
        try:
            reply = mesh.dispatch(to_host, "stop_clevel", "cto", sid)
            if reply.get("ok") is not True or (reply.get("result") or {}).get("stopped") is not True:
                raise ValueError("stop refused or session not stopped")
            stopped.add(sid)
            return True
        except Exception as e:
            detail = f"stop {sid}: {type(e).__name__}: {str(e)[:200]}"
            stop_errors.append(detail)
            print(f"L9 {to_host}: {detail}", file=sys.stderr)
            return False

    def start(*args):
        reply = mesh.dispatch(to_host, "start_clevel", "cto", *args, "--probe")
        result = reply.get("result") or {}
        sid = result.get("session_id")
        if isinstance(sid, str) and re.fullmatch(r"[0-9a-f]{8}", sid):
            started.append(sid)
        if reply.get("ok") is not True or sid not in started:
            raise ValueError("start_clevel refused or missing session_id")
        return sid, result

    def registered(sid):
        deadline = time.monotonic() + 120
        while True:
            row = session_status.get("cto", sid)
            if row and row.get("host") == to_host:
                return
            if time.monotonic() >= deadline:
                raise ValueError(f"session {sid} not registered on {to_host} within 120s")
            time.sleep(5)

    try:
        live = [r for r in session_status.list_sessions(status="open")
                if r.get("role") == "cto" and r.get("host") == to_host]
        if len(live) >= 3:
            return {"ok": False, "kind": "skip", "reason": "cap"}
        s1, _ = start()
        registered(s1)
        lid = db_mod.create_letter(
            to_host, "cto", "mesh_check L9 probe: reply with the single word ok, run no tools, do nothing else.",
            to_session=s1, from_role=L5_FROM_ROLE,
            from_session=f"mesh-check-{uuid.uuid4().hex[:8]}", from_host=from_host)
        reply = mesh.dispatch(to_host, "deliver_letter", str(lid))
        if reply.get("ok") is not True:
            raise ValueError("probe letter delivery refused")
        time.sleep(60)
        if not stop(s1):
            raise ValueError("first session could not be stopped")
        s2, result = start("--resume", s1)
        if s2 == s1 or result.get("resumed_from") != s1:
            raise ValueError("resume did not fork the requested session")
        registered(s2)
        cell = _green(f"spawn {s1}, resume {s1} -> {s2}, both stopped")
    except mesh.MeshUnreachable as e:
        cell = _unreachable(str(e))
    except Exception as e:
        cell = _red(f"{type(e).__name__}: {e}")
    finally:
        for sid in dict.fromkeys(started):
            if sid not in stopped:
                stop(sid)
        if lid is not None:
            _abandon_letter(db_mod, lid)
    if stop_errors:
        return _red("; ".join(stop_errors))
    return cell


def _is_windows_host(host: str) -> bool:
    try:
        return config.host(host).get("os") == "windows"
    except Exception:
        return False


def _l5_deliver(db_mod, mesh, to_host: str, lid: int, tid: str, role: str = L5_ROLE,
                need_wake: bool = False) -> dict:
    """Deliver letter `lid` for worker `tid` on `to_host` and judge the reply.
    `need_wake` (the L5Window form) also demands `woke: true`."""
    try:
        reply = mesh.dispatch(to_host, "deliver_letter", str(lid))
    except mesh.MeshUnreachable as e:
        return _unreachable(str(e))
    except ValueError as e:
        return _red(str(e))
    if reply.get("ok") is not True:
        return _red(f"deliver_letter refused: {str(reply.get('error'))[:200]}")
    result = reply.get("result") or {}
    if result.get("letter_id") != lid:
        return _red(f"reply is for letter {result.get('letter_id')!r}, sent {lid}")
    if result.get("delivered") is not True and result.get("already_delivered") is not True:
        return _red(f"reply says neither delivered nor already_delivered: {str(result)[:150]}")
    if result.get("delivered") is True and result.get("to") != f"{role}-{tid}":
        return _red(f"delivered to {result.get('to')!r}, expected {role}-{tid}")
    try:
        row = db_mod.get_letter(lid)
    except Exception as e:
        return _unreachable(f"hub read failed: {type(e).__name__}: {e}")
    status = (row or {}).get("status")
    if status != "delivered":
        return _red(f"reply says delivered but the hub row is {status!r}")
    # `woke: False` with a `why` is a wake that was tried and failed. A bare
    # `woke: False` (worker letter on Windows) and no field at all (a node_dispatch
    # older than task-f9d23d0b) report nothing: without `need_wake` the cell is ok
    # and says what it did not see; with it, only the Windows worker is let off.
    woke = result.get("woke")
    if woke is False and result.get("why"):
        return _red(f"letter delivered, wake failed: {str(result['why'])[:150]}")
    if need_wake and woke is not True:
        if woke is False and _is_windows_host(to_host):
            # node_dispatch never wakes a Windows worker (it reads MAILBOX.md before
            # every tool call) and says so with a bare `woke: false`: not applicable.
            return _green("wake n/a: Windows worker reads MAILBOX.md")
        seen = "no woke field" if woke is None else f"woke={woke!r}"
        return _red(f"letter delivered, but the reply does not say woke: true ({seen}): "
                    "the wake is not proven")
    return _green("woke" if woke is True else "wake not reported")


# ---------------------------------------------------------------------------
# L5 inside L3's window: the wake, proven by a nonce
# ---------------------------------------------------------------------------

L5_NONCE_PREFIX = "MESH-NONCE-"
L5_NONCE_WAIT_S = 120  # how long the probe worker waits for the letter


class L5Window:
    """L5 for one (A, B) pair, run inside L3's window.

    The standalone L5 needs an `in_progress` probe worker on B, but a `--live`
    run's L3 creates the only one and finishes it before the mesh levels run.
    So L3 hands its task to this object the moment it is `in_progress` on B
    (`send`). The letter body carries a fresh nonce that appears nowhere else:
    not in the task description, not in the hub row of the task. The probe
    worker is told to wait for the letter and write `nonce=<token>` on its
    probe-file line. A POSIX worker only sees a letter on its next prompt, and
    the prompt comes from the wake, so the nonce in the file read back from
    origin proves the wake end to end, not just the mailbox write.

    Green = the reply delivered THIS letter to the worker, the hub row is
    `delivered`, the reply says `woke: true` and the file on origin has the
    nonce. Anything less is a red or unreachable cell that says which step."""

    def __init__(self, from_host: str, to_host: str):
        self.from_host, self.to_host = from_host, to_host
        self.nonce = f"{L5_NONCE_PREFIX}{uuid.uuid4().hex[:16]}"
        self.sent = False                    # send() was called (once at most)
        self.delivery: dict | None = None    # the cell for the letter itself
        self.probe_text: str | None = None
        self.probe_why = "L3 never got as far as reading the probe file"
        self.cell: dict | None = None        # final; set by close()

    def instructions(self) -> str:
        """The paragraph L3 adds to the probe task's description. It never
        contains the nonce: the worker can only get it from the letter."""
        return (
            "A letter from mesh_check is on its way to your mailbox. It holds one token: "
            f"`{L5_NONCE_PREFIX}` followed by 16 hex digits. It may already be in your "
            "messages (it can arrive with the kickoff): look there first. If it is not there, "
            "wait for it before you write "
            f"the line: run `sleep 15` and look for the letter, for at most {L5_NONCE_WAIT_S} s "
            "in all. It reaches you as a mailbox block on your next message. When it comes, "
            "copy the whole token and add ` nonce=<token>` to the end of the line. If "
            f"nothing came after {L5_NONCE_WAIT_S} s, write the line without a nonce and say "
            "in your report that no letter came. Never invent a token.\n\n"
        )

    def body(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return (f"mesh-check probe letter {self.from_host}->{self.to_host} {ts}. "
                f"Your nonce is {self.nonce}. Add ` nonce={self.nonce}` to the end of the line "
                "you write in your probe file, as your task says. Nothing else to do.")

    def send(self, task_id: str, role: str) -> None:
        """Write the letter for `task_id` and have B deliver it. Once only; the
        outcome is in `self.delivery`. Never raises: an L5 problem must not fail L3."""
        self.sent = True
        try:
            if not HAVE_CONFIG:
                self.delivery = _red("no repo access")
                return
            from lib import db as db_mod
            mesh = _mesh()
            try:
                lid = db_mod.create_letter(self.to_host, role, self.body(), to_session=task_id,
                                           from_role=L5_FROM_ROLE,
                                           from_session=f"mesh-check-{uuid.uuid4().hex[:8]}",
                                           from_host=self.from_host)
            except Exception as e:
                self.delivery = _unreachable(f"hub write failed: {type(e).__name__}: {e}")
                return
            cell = _l5_deliver(db_mod, mesh, self.to_host, lid, task_id, role=role, need_wake=True)
            if not cell["ok"]:
                _abandon_letter(db_mod, lid)
            self.delivery = cell
        except Exception as e:
            self.delivery = _red(f"L5 letter step failed: {type(e).__name__}: {e}")

    def read_probe(self, root: Path, rev: str | None, path: str) -> None:
        """Read the probe file back from origin at `rev`. Skipped when there is
        no delivered letter to look for."""
        if self.delivery is None or not self.delivery["ok"]:
            return
        if not rev:
            self.probe_why = "the task has no branch or merge sha to read the file from"
            return
        try:
            self.probe_text, self.probe_why = _git_show_from_origin(root, rev, path)
        except Exception as e:
            self.probe_why = f"{type(e).__name__}: {e}"

    def close(self, l3_reason: str | None) -> None:
        """Fix the final cell. Called once, when L3 is over, whatever it ended in."""
        if self.cell is not None:
            return
        tail = f" (L3: {l3_reason})" if l3_reason else ""
        if self.delivery is None:
            self.cell = _red(f"no letter was sent: the probe worker was never seen in_progress "
                             f"on {self.to_host}{tail}")
        elif not self.delivery["ok"]:
            self.cell = self.delivery
        elif self.probe_text is None:
            self.cell = _red(f"letter delivered ({self.delivery.get('note')}), but the probe file "
                             f"could not be read back from origin: {self.probe_why}{tail}")
        else:
            self.cell = self._judge_file()

    def _judge_file(self) -> dict:
        note = self.delivery.get("note")
        if f"nonce={self.nonce}" in (self.probe_text or ""):
            return _green(f"{note}, nonce read back from origin")
        m = re.search(r"nonce=(\S{0,40})", self.probe_text or "")
        if m:
            return _red(f"letter delivered ({note}), but the probe file on origin carries "
                        f"nonce={m.group(1)!r}, not the one in the letter")
        return _red(f"letter delivered ({note}), but the probe file on origin has no nonce: "
                    "the worker did not read the letter (or did not copy it)")


def l5_window_for(from_host: str, to_host: str, expect: str) -> L5Window | None:
    """An L5Window when L3 and L5 are both claimed for (from, to) and B can be
    dialled; else None, and L5 keeps the standalone form. A target with no
    `mesh_ssh` is "closed (by design)": no letter, so no window."""
    if not HAVE_CONFIG or from_host == to_host:
        return None
    if not (_in_scope("L3", from_host, to_host, expect) and _in_scope("L5", from_host, to_host, expect)):
        return None
    if _mesh_ssh_for(to_host) in (None, "", "?"):
        return None
    return L5Window(from_host, to_host)


# ---------------------------------------------------------------------------
# L6 — liveness
# ---------------------------------------------------------------------------

L6_MAX_S = 60


def l6_probe(host: str) -> dict:
    """`probe` answers within L6_MAX_S, and afterwards the hub's `hosts` row for
    `host` is fresh by the router's own rule (`router._probe_problem`, whose
    constant is PROBE_MAX_AGE_S): the verb writes `probed_at` on the far side,
    so a fresh stamp shows the write reached the shared hub. The running host
    answers in-process; a host with no mesh_ssh is closed (by design)."""
    if not HAVE_CONFIG:
        return _red("no repo access")
    mesh = _mesh()
    if host != _self_host_or_none() and not _mesh_ssh_for(host):
        return _closed()
    from lib import db as db_mod
    from lib import router
    t0 = time.monotonic()
    try:
        reply = mesh.dispatch(host, "probe", timeout=L6_MAX_S)
    except mesh.MeshUnreachable as e:
        return _unreachable(str(e))
    except ValueError as e:
        return _red(str(e))
    took = time.monotonic() - t0
    why = _node_reply_ok(reply, host)
    if why:
        return _red(why)
    if took >= L6_MAX_S:
        return _red(f"probe took {took:.0f} s (limit {L6_MAX_S} s)")
    try:
        row = db_mod.get_host(host)
    except Exception as e:
        return _unreachable(f"hub read failed: {type(e).__name__}: {e}")
    why = router._probe_problem(row, datetime.now(timezone.utc))
    if why:
        return _red(f"probe answered in {took:.1f} s but the hosts row is not fresh: {why}")
    return _green()


# ---------------------------------------------------------------------------
# L7 — router
# ---------------------------------------------------------------------------

# (host the task must land on, `needs:` name, also prove "stale probe -> no_host")
L7_CASES = (("contabo", "always_on", False), ("winbox", "win_gui", True))
L7_PROJECT = "mooniex-agents"


def _l7_task(need: str) -> dict:
    """A synthetic task row for pick_host. Never stored. `runner` is pinned so
    the check does not depend on tools/route.py's plans."""
    return {"id": "task-00000000", "project": L7_PROJECT, "role": "developer",
            "runner": "claude", "status": "pending", "host": None,
            "description": f"needs: {need}\n\nmesh-check L7 synthetic task. Never stored."}


def check_l7(host: str, need: str, check_stale: bool, rows: list[dict]) -> dict:
    """`pick_host` on a task that `needs: <need>` picks `host`. With
    `check_stale`, a COPY of `rows` whose `host` probe is older than the
    router's limit must give no_host: the router has no fallback host. `rows`
    is never written back, and the hosts table is never written at all."""
    from lib import router
    now = datetime.now(timezone.utc)
    task = _l7_task(need)
    pick = router.pick_host(task, hosts_rows=rows, now=now)
    if pick.host != host:
        return _red(f"needs {need}: picked {pick.host!r}, expected {host!r}: {pick.line[:200]}")
    if not check_stale:
        return _green()
    stale_rows = copy.deepcopy(rows)
    old = (now - timedelta(seconds=router.PROBE_MAX_AGE_S + 60)).isoformat()
    for r in stale_rows:
        if r.get("host") == host:
            r["probed_at"] = old
    pick = router.pick_host(task, hosts_rows=stale_rows, now=now)
    if pick.host is not None or not pick.line.startswith("no_host"):
        return _red(f"needs {need} with {host} stale: expected no_host, got "
                    f"{pick.host!r}: {pick.line[:200]}")
    return _green()


def l7_probe(cases=L7_CASES) -> dict[str, dict]:
    """host -> L7 cell, from the live `hosts` rows (read-only). A hub that cannot
    be read makes every cell unreachable: the router's verdict is not known."""
    if not HAVE_CONFIG:
        return {h: _red("no repo access") for h, _, _ in cases}
    from lib import db as db_mod
    try:
        rows = db_mod.list_hosts()
    except Exception as e:
        cell = _unreachable(f"hub read failed: {type(e).__name__}: {e}")
        return {h: cell for h, _, _ in cases}
    return {h: check_l7(h, need, stale, rows) for h, need, stale in cases}


# ---------------------------------------------------------------------------
# L8 — join drill
# ---------------------------------------------------------------------------

JOIN_DRILL_FILE = "join-drill.json"
JOIN_DRILL_MAX_AGE_S = 7 * 24 * 3600
JOIN_DRILL_KIND = "join_drill"       # the events row scripts/drill-join.sh records beside the file
JOIN_DRILL_ACTOR = "drill-join"


def latest_join_drill() -> dict | None:
    """The newest `join_drill` events row (the drill's JSON), or None when there is none. Raises
    when the hub cannot be read: check_l8 turns that into its own answer."""
    from lib import db as db_mod
    with db_mod.get_conn() as conn:
        row = conn.execute("SELECT payload FROM events WHERE kind = ? ORDER BY id DESC LIMIT 1",
                           (JOIN_DRILL_KIND,)).fetchone()
    if row is None:
        return None
    data = json.loads(row["payload"])
    return data if isinstance(data, dict) else None


def check_l8(state_dir: Path, now: datetime | None = None, *, events=None) -> dict:
    """state/mesh-check/join-drill.json, written by the W4.7 drill (not by this
    tool): {"ok": bool, "at": ISO-8601, "host": str, "steps": [{"name", "ok"}]}.
    The drill also records the same JSON as a `join_drill` events row, and with no file
    here (the Mac never runs the drill) the newest row is judged instead: `events()`
    returns it, default latest_join_drill().
    No file and no row = not run. Malformed, failed, empty or older than 7 days = red."""
    now = now or datetime.now(timezone.utc)
    path = state_dir / JOIN_DRILL_FILE
    src = JOIN_DRILL_FILE
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return _red(f"{JOIN_DRILL_FILE} unreadable: {type(e).__name__}")
    else:
        src = f"{JOIN_DRILL_KIND} event"
        try:
            data = (events or latest_join_drill)()
        except Exception as e:
            return {"ok": False, "kind": "not_run",
                    "reason": f"no drill recorded ({JOIN_DRILL_FILE} missing, hub read failed: "
                              f"{type(e).__name__})"}
        if data is None:
            return {"ok": False, "reason": f"no drill recorded ({JOIN_DRILL_FILE} missing, "
                                           f"no {JOIN_DRILL_KIND} event)", "kind": "not_run"}
    if not isinstance(data, dict):
        return _red(f"{src} is not a JSON object")
    steps = data.get("steps")
    if (not isinstance(data.get("ok"), bool) or not isinstance(data.get("host"), str)
            or not data["host"] or not isinstance(steps, list)):
        return _red(f"{src} lacks ok (bool), at, host (str) or steps (list)")
    try:
        at = datetime.fromisoformat(str(data.get("at")).strip().replace("Z", "+00:00"))
    except ValueError:
        return _red(f"{src}: at {str(data.get('at'))[:40]!r} is not ISO-8601")
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    age = (now - at).total_seconds()
    if age < -600:
        return _red(f"drill dated in the future ({data['at']})")
    if age > JOIN_DRILL_MAX_AGE_S:
        return _red(f"last drill is {int(age // 86400)} days old (limit "
                    f"{JOIN_DRILL_MAX_AGE_S // 86400}), host {data['host']}")
    failed = [str(s.get("name", "?")) for s in steps if isinstance(s, dict) and s.get("ok") is not True]
    if data["ok"] is not True:
        return _red(f"last drill failed on {data['host']}"
                    + (f": step {', '.join(failed)}" if failed else ""))
    if not steps:
        return _red("drill says ok but recorded no steps")
    if failed:
        return _red(f"drill says ok but step {', '.join(failed)} is not ok")
    return _green(f"{data['host']}, {int(age // 3600)} h ago")


# The hub side of scripts/drill-join.sh, as `--join-drill <verb> <arg>`. The drill is a shell
# script; these are the three things it needs from lib.db, kept here beside the L8 reader so the
# row's shape is written in one place.

JOIN_DRILL_MAX_BYTES = 64 * 1024


def join_drill_probe_path(host: str) -> str:
    """Where the node writes its probe line, in the L3 shape docs/ops/mesh-probe/<from>-<to>.md."""
    return f"docs/ops/mesh-probe/contabo-{host}.md"


def join_drill_task_create(host: str) -> str:
    """A task for the throwaway node. It stays `pending` on purpose: no poller adopts a pending
    row, so nothing can pick up the node's probe branch and merge it."""
    from lib import config as config_mod
    from lib import db as db_mod
    if not config_mod.HOST_NAME_RE.fullmatch(host):
        raise ValueError("bad host name")
    path = join_drill_probe_path(host)
    return db_mod.create_task(
        project="mooniex-agents", role="developer",
        title=f"mesh-probe contabo->{host} (join drill)",
        description=(f"W4.7 join drill probe for the throwaway node {host}. Overwrite {path} with "
                     f"one line and commit it with a message starting `mesh-probe:`. The drill "
                     f"deletes the branch and cancels this task; nothing is merged."),
        touches=[path], host=host)


def join_drill_task_close(task_id: str) -> bool:
    from lib import db as db_mod
    return db_mod.update_status(task_id, "cancelled", actor=JOIN_DRILL_ACTOR)


def join_drill_record(data: object) -> None:
    """One `join_drill` events row: the drill JSON exactly as written to join-drill.json."""
    from lib import db as db_mod
    if not isinstance(data, dict) or not isinstance(data.get("host"), str):
        raise ValueError("drill JSON must be an object with a host")
    if len(json.dumps(data)) > JOIN_DRILL_MAX_BYTES:
        raise ValueError(f"drill JSON is over {JOIN_DRILL_MAX_BYTES} bytes")
    with db_mod.get_conn() as conn:
        db_mod.log_event(conn, None, JOIN_DRILL_ACTOR, JOIN_DRILL_KIND, data)


def join_drill_cli(verb: str, arg: str) -> int:
    """Exit 0 ok, 1 ran and changed nothing, 2 refused (bad verb or argument)."""
    try:
        if verb == "task-create":
            print(join_drill_task_create(arg))
        elif verb == "task-close":
            if not join_drill_task_close(arg):
                print(f"join-drill: {arg} was not changed (already closed?)", file=sys.stderr)
                return 1
        elif verb == "record":
            join_drill_record(json.loads(Path(arg).read_text(encoding="utf-8")))
        else:
            print(f"join-drill: unknown verb {verb!r} (task-create, task-close, record)",
                  file=sys.stderr)
            return 2
        return 0
    except (ValueError, OSError) as e:
        print(f"join-drill: refused: {type(e).__name__}: {str(e)[:160]}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# INV — one poller per remote row
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _self_host_as(host: str):
    """Make lib.config.self_host() answer `host`, for code that already holds
    that function by name (runners.branch_poller, tools.worker_reap bind it with
    `from lib.config import self_host`, so replacing the module attribute would
    not reach them). self_host() reads ORG_HOST first and is cached: set the
    variable, clear the cache, and put both back on the way out."""
    old = os.environ.get("ORG_HOST")
    os.environ["ORG_HOST"] = host
    config.self_host.cache_clear()
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("ORG_HOST", None)
        else:
            os.environ["ORG_HOST"] = old
        config.self_host.cache_clear()


def check_invariant() -> dict:
    """For every in_progress row that is remote (its host is not its dispatcher)
    or is a codex/agy launcher run, count the hosts whose
    `branch_poller.in_poller_set(row)` is true with self_host() pinned to each
    host of config/hosts.yaml in turn. Exactly 1 is correct: 0 means nobody
    watches the row, more than 1 means two pollers flip it twice. Read-only."""
    if not HAVE_CONFIG:
        return _red("no repo access")
    from lib import db as db_mod
    try:
        tasks = db_mod.list_tasks(status="in_progress", limit=500)
    except Exception as e:
        return _unreachable(f"hub read failed: {type(e).__name__}: {e}")
    try:
        from runners import branch_poller
    except Exception as e:
        return _red(f"cannot load runners.branch_poller: {type(e).__name__}: {e}")

    def candidate(t: dict) -> bool:
        host, disp = t.get("host") or None, t.get("dispatcher_host") or None
        runner = (t.get("runner") or "claude").strip().lower()
        return (host is not None and host != disp) or runner in branch_poller.EXTERNAL_RUNNERS

    rows = [t for t in tasks if candidate(t)]
    pollers: dict[str, list[str]] = {t["id"]: [] for t in rows}
    for h in config.hosts():
        with _self_host_as(h):
            for t in rows:
                if branch_poller.in_poller_set(t):
                    pollers[t["id"]].append(h)
    offenders = [f"{tid} ({len(p)} pollers" + (f": {', '.join(p)})" if p else ")")
                 for tid, p in pollers.items() if len(p) != 1]
    if offenders:
        shown = ", ".join(offenders[:10]) + (f" (+{len(offenders) - 10} more)" if len(offenders) > 10 else "")
        return {"ok": False, "reason": f"{len(offenders)} of {len(rows)} rows: {shown}",
                "offenders": offenders, "rows": len(rows)}
    return {**_green(f"{len(rows)} rows"), "rows": len(rows)}


# ---------------------------------------------------------------------------
# --local: this host's L0-L2 cells only, no ssh, writes nothing
# ---------------------------------------------------------------------------

async def local_payload() -> dict:
    """This host's L0-L2 cells. The L1 cell to this host is n/a, where "this
    host" is `_running_host_guess(ROOT)`, the source build_matrix labels its row
    with: one identity per run. When it cannot say (None) every host is dialled,
    this one included, so an unknown identity never hides a red cell."""
    payload: dict = {}
    if HAVE_CONFIG:
        me = _running_host_guess(ROOT)
        payload["l0"] = _to_cell(check_l0(ROOT))
        payload["l1"] = {h: _l1_cell(h, me) for h in HOSTS}
        payload["l2"] = _to_cell(await check_l2(ROOT))
    else:
        payload["l0"] = {"ok": False, "reason": "no repo access"}
        payload["l1"] = {}
        payload["l2"] = {"ok": False, "reason": "no repo access"}
    return payload


def _collect_peer_local(alias: str, cfg: dict, script_path: Path) -> dict | None:
    """Get a peer host's L0-L2 cells: try its already-deployed checkout
    first, else pipe this file's own source over ssh stdin (the box may not
    have pulled this branch yet)."""
    remote_root = cfg.get("agents_root")
    is_windows = cfg.get("os") == "windows"
    if remote_root:
        python = f"{remote_root}\\.venv\\Scripts\\python.exe" if is_windows \
            else f"{remote_root}/.venv/bin/python"
        deployed_cmd = f'cd "{remote_root}" && "{python}" -m tools.mesh_check --local --json'
        data = _try_json(_ssh_run(alias, deployed_cmd, timeout=30))
        if data is not None:
            return data

    piped_cmd = "python - --local --json" if is_windows else "python3 - --local --json"
    if remote_root:
        piped_cmd = f'cd "{remote_root}" && {piped_cmd}'
    return _try_json(_ssh_run(alias, piped_cmd, timeout=30, stdin_path=script_path))


# ---------------------------------------------------------------------------
# Default mode: own cells + collect peers + render + write state
# ---------------------------------------------------------------------------

async def build_matrix(args: argparse.Namespace) -> tuple[dict, str | None]:
    combined: dict = {lvl: ({"all": {}} if lvl in SINGLE_LEVELS else {h: {} for h in HOSTS})
                      for lvl in LEVELS}
    running_host = _running_host_guess(ROOT)

    if running_host and HAVE_CONFIG:
        combined["L0"][running_host][running_host] = _to_cell(check_l0(ROOT))
        combined["L2"][running_host][running_host] = _to_cell(await check_l2(ROOT))
        for h in HOSTS:
            if h == running_host:
                continue
            combined["L1"][running_host][h] = _l1_cell(h, running_host)

    if HAVE_CONFIG:
        script_path = Path(__file__).resolve()
        for h in HOSTS:
            if h == running_host:
                continue
            cfg = config.host(h)
            alias = cfg.get("ssh")
            if not alias:
                continue  # unreachable from here (e.g. mac when we are not mac)
            peer = _collect_peer_local(alias, cfg, script_path)
            if not peer:
                continue
            l0 = _norm_cell(peer.get("l0"))
            if l0:
                combined["L0"][h][h] = l0
            l2 = _norm_cell(peer.get("l2"))
            if l2:
                combined["L2"][h][h] = l2
            for to, raw in (peer.get("l1") or {}).items():
                if to in HOSTS and to != h:
                    cell = _norm_cell(raw)
                    if cell:
                        combined["L1"][h][to] = cell

    if args.live and running_host:
        for target in HOSTS:
            # L5 for this pair runs inside L3's window when both are claimed: the
            # probe worker L3 creates is the only one there is (see L5Window).
            window = l5_window_for(running_host, target, args.expect)
            ok, reason = await run_l3_probe(running_host, target, ROOT, args.expect,
                                            args.no_merge, window)
            combined["L3"][running_host][target] = {"ok": ok, "reason": reason}
            if window is not None and window.cell is not None:
                combined["L5"][running_host][target] = window.cell

    if running_host and HAVE_CONFIG and _wave_index(args.expect) >= _wave_index("w1"):
        for target in HOSTS:
            if target == running_host:
                continue
            ok, reason = l4_probe(running_host, target)
            combined["L4"][running_host][target] = {"ok": ok, "reason": reason}

    if args.live and running_host and HAVE_CONFIG:
        _run_mesh_levels(combined, running_host, args.expect)
    if HAVE_CONFIG:
        # Read-only, so no --live: L8 reads a file, INV reads the hub.
        if _in_scope("L8", "all", "all", args.expect):
            combined["L8"]["all"]["all"] = check_l8(ROOT / "state" / "mesh-check")
        if _in_scope("INV", "all", "all", args.expect):
            combined["INV"]["all"]["all"] = check_invariant()

    return combined, running_host


def _run_mesh_levels(combined: dict, running_host: str, expect: str) -> None:
    """SEC, L5, L6, L7 and L9, only the cells `expect`
    already claims (a cell not claimed yet is never dialled and writes no
    letter). Order matters: L6's probes write the `hosts` rows L7 then reads."""
    for to in HOSTS:
        if to == running_host:
            continue
        if _in_scope("SEC", running_host, to, expect):
            combined["SEC"][running_host][to] = check_sec(to)
        # A pair whose L5 already ran inside L3's window is not asked twice.
        if _in_scope("L5", running_host, to, expect) and combined["L5"][running_host].get(to) is None:
            combined["L5"][running_host][to] = l5_probe(running_host, to)
        if _in_scope("L9", running_host, to, expect):
            combined["L9"][running_host][to] = l9_probe(running_host, to)
    for h in HOSTS:
        if _in_scope("L6", h, h, expect):
            combined["L6"][h][h] = l6_probe(h)
    wanted = tuple(c for c in L7_CASES if _in_scope("L7", c[0], c[0], expect))
    if wanted:
        for h, cell in l7_probe(wanted).items():
            combined["L7"][h][h] = cell


def _l1_alias_for(to_host: str) -> str | None:
    if not HAVE_CONFIG:
        return "?"
    try:
        return config.host(to_host).get("ssh")
    except ValueError:
        return "?"


def _judge(computed: dict) -> tuple[str, str]:
    """(text, outcome) for one computed cell. outcome: "ok", "fail" or "skip".

    Red, unreachable and not-run all fail (unknown is never green) but read
    differently, so a down host is not mistaken for a wrong answer. A closed
    cell (target has no mesh_ssh) is "closed (by design)" and never counts; an
    "n/a" cell (L1 to this host itself) reads "n/a" and never counts either."""
    kind = computed.get("kind")
    if kind == "skip":
        return f"skip: {computed['reason']}", "skip"
    if kind == "n/a":
        return "n/a", "skip"
    if kind == "closed":
        return "closed (by design)", "skip"
    if computed["ok"]:
        note = computed.get("note")
        return (f"ok ({note})" if note else "ok"), "ok"
    if kind == "unreachable":
        return f"UNREACHABLE({computed['reason']})", "fail"
    if kind == "not_run":
        return f"not run ({computed['reason']})", "fail"
    return f"FAIL({computed['reason']})", "fail"


def render(combined: dict, expect: str) -> tuple[str, bool, int, int]:
    """Returns (markdown, any_fail_in_scope, n_ok, n_fail). n_fail counts every
    in-scope cell that is not green: red, UNREACHABLE and not run alike."""
    expect_idx = _wave_index(expect)
    lines: list[str] = []
    tally = {"ok": 0, "fail": 0}

    def cell_text(level: str, frm: str, to: str) -> str:
        key = (level, frm, to)
        first_green = EXPECT.get(key)
        computed = (combined.get(level, {}).get(frm, {}) or {}).get(to)
        if first_green is None:
            return "n/a"
        if level in MESH_PAIR_LEVELS and _mesh_ssh_for(to) is None:
            return "closed (by design)"
        if _wave_index(first_green) > expect_idx:
            if level == "L1" and _l1_alias_for(to) is None:
                return "closed (by design)"
            return "n/a"
        if computed is None:
            return "n/a"
        text, outcome = _judge(computed)
        if outcome in tally:
            tally[outcome] += 1
        return text

    for level in LEVELS:
        lines.append(f"## {level}")
        lines.append("")
        if level in SINGLE_LEVELS:
            lines.append("| check | result |")
            lines.append("|---|---|")
            lines.append(f"| {SINGLE_LEVELS[level]} | {cell_text(level, 'all', 'all')} |")
            lines.append("")
            continue
        lines.append("| from \\ to | " + " | ".join(HOSTS) + " |")
        lines.append("|---|" + "---|" * len(HOSTS))
        for frm in HOSTS:
            lines.append("| " + " | ".join([frm] + [cell_text(level, frm, to) for to in HOSTS]) + " |")
        lines.append("")

    return "\n".join(lines), tally["fail"] > 0, tally["ok"], tally["fail"]


def write_state(combined: dict, args: argparse.Namespace, running_host: str | None) -> Path:
    state_dir = ROOT / "state" / "mesh-check"
    state_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_at": ts, "expect": args.expect, "live": args.live,
        "running_host": running_host, "matrix": combined,
    }
    text = json.dumps(payload, indent=2)
    (state_dir / f"{ts}.json").write_text(text)
    latest = state_dir / "latest.json"
    latest.write_text(text)
    return latest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--expect", choices=WAVES, help="wave to judge cells against (e.g. w0)")
    ap.add_argument("--live", action="store_true",
                    help="run real L3 delegate probes and dispatch-key levels (SEC, L5, L6, L7, L9); "
                         "L9 starts/stops CTO probes; transcripts are not compared, resume's "
                         "refusal without a resumable UUID proves it found the conversation")
    ap.add_argument("--no-merge", action="store_true", help="L3: skip merge_task after delegate")
    ap.add_argument("--local", action="store_true", help="print this host's L0-L2 cells only")
    ap.add_argument("--json", action="store_true", help="with --local, JSON output (default)")
    ap.add_argument("--get-task", metavar="TASK_ID", help="print db.get_task(TASK_ID) as JSON")
    ap.add_argument("--join-drill", nargs=2, metavar=("VERB", "ARG"),
                    help="hub side of scripts/drill-join.sh: task-create <host>, task-close <id>, "
                         "record <drill.json>")
    args = ap.parse_args(argv)
    if not args.local and not args.get_task and not args.join_drill and not args.expect:
        ap.error("--expect is required outside --local/--get-task/--join-drill")
    return args


async def amain(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.join_drill:
        return join_drill_cli(*args.join_drill)

    if args.get_task:
        if not HAVE_CONFIG:
            print(json.dumps({"error": "no repo access"}))
            return 0
        from lib import db as db_mod
        t = db_mod.get_task(args.get_task)
        print(json.dumps(t or {}))
        return 0

    if args.local:
        payload = await local_payload()
        print(json.dumps(payload))
        return 0

    combined, running_host = await build_matrix(args)
    markdown, any_fail, n_ok, n_fail = render(combined, args.expect)
    latest = write_state(combined, args, running_host)

    print(markdown)
    print(f"mesh-check: expect={args.expect} running_host={running_host or '?'} "
          f"live={args.live} ok={n_ok} fail={n_fail} state={latest}")

    return 1 if any_fail else 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(amain(argv))


if __name__ == "__main__":
    sys.exit(main())
