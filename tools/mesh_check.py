"""Org Mesh acceptance test (docs/design/org-mesh.md).

Prints the wiring matrix from the design doc's §1 measured tables and exits
1 when a cell that is expected green for the given `--expect` wave is red.
Every later wave adds its own level; this file builds the frame + L0-L4.

    python3 -m tools.mesh_check --expect w0 [--live] [--no-merge]
    python3 -m tools.mesh_check --local --json          # this host only, no ssh
    python3 -m tools.mesh_check --get-task <id> --json  # local ledger read, for L4

See docs/ops/mesh-check.md for what each level proves and the design
rationale behind the EXPECT table below.

Levels:
  L0 identity  — which host am I (self_host() / tailscale / ROOT-vs-agents_root
                 agreement). Diagonal only (from == to).
  L1 ssh       — `ssh -o BatchMode=yes ... <alias> true` to every other host.
  L2 org MCP   — start the org MCP server over stdio, tools/list includes
                 create_task + delegate_task. Diagonal only.
  L3 delegate  — --live only: create a probe task, delegate it to a target
                 host, poll to review/done, merge, verify on origin + clean
                 worktree. Only ever run for from == the host this process is
                 actually executing on ("one poller per remote row" — a host
                 can prove its own outbound delegate, never another host's).
  L4 ledger    — create a task on this host's ledger, ask another host
                 (read-only ssh, `--get-task`) whether it sees it. Same
                 from-== self restriction as L3.

L0/L1/L2 are cheap, stateless, one-shot checks, so a peer host's copy of
them is collected via `--local --json`, either from an already-deployed
checkout or piped raw over ssh stdin when the tool isn't deployed there yet
(imports of repo modules are guarded — a piped script with no filesystem
context for lib/config.py degrades to "n/a" instead of crashing). L3/L4 need
either a long-lived MCP session (L3) or a real cross-host round trip (L4),
so they are never collected remotely — only computed for this process's own
host, exactly like the invariant above.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
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

WAVES = ["w0", "w1", "w2", "w3", "w4", "w5"]
LEVELS = ["L0", "L1", "L2", "L3", "L4"]


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
}


# ---------------------------------------------------------------------------
# Small helpers shared by every level
# ---------------------------------------------------------------------------

def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def _ssh_run(alias: str, remote_cmd: str, *, timeout: int,
             stdin_path: Path | None = None) -> str | None:
    """Run `remote_cmd` on `alias` over ssh. Returns stdout, or None on any
    failure (unreachable, timeout, non-zero exit) — never raises."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", alias, remote_cmd]
    try:
        if stdin_path is not None:
            with open(stdin_path, "rb") as f:
                r = subprocess.run(cmd, stdin=f, capture_output=True, text=True, timeout=timeout)
        else:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, timeout=timeout)
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


def _tailscale_guess_host() -> str | None:
    """Best-effort: match `tailscale status --json` Self.HostName/DNSName
    against a host key or its ssh alias. None if tailscale is unavailable,
    unparsable, or nothing matches — never raises."""
    if not HAVE_CONFIG:
        return None
    try:
        r = subprocess.run(["tailscale", "status", "--json"],
                           capture_output=True, text=True, timeout=10)
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


def _root_match_host(root: Path) -> str | None:
    """Which host, if any, has `agents_root` == `root`. Always contributes a
    real answer (never "unavailable") — a checkout that matches nobody is
    itself a meaningful (disagreeing) signal, e.g. running from a worktree."""
    if not HAVE_CONFIG:
        return None
    for h, cfg in config.hosts().items():
        if cfg.get("agents_root") == str(root):
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
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if r.returncode == 0:
        return True, None
    if cfg.get("os") == "windows":
        cmd2 = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", alias,
                "cmd", "/c", "exit", "0"]
        try:
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
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
    params = StdioServerParameters(command=str(python), args=["-m", "runners.cto_mcp_server"],
                                   cwd=str(root), env=env)
    try:
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
                           capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return r.returncode == 0 and sha in r.stdout


def _git_status_porcelain(root: Path) -> str:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                           capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return "git status failed"
    return r.stdout.strip()


async def run_l3_probe(from_host: str, to_host: str, root: Path, expect: str,
                       no_merge: bool) -> tuple[bool, str | None]:
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
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["CTO_SESSION_ID"] = session_id
    params = StdioServerParameters(command=str(python), args=["-m", "runners.cto_mcp_server"],
                                   cwd=str(root), env=env)
    try:
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
                while time.monotonic() < deadline:
                    get_result = await asyncio.wait_for(
                        session.call_tool("get_task", {"task_id": task_id}), timeout=30)
                    final_status = _toon_field(_first_text(get_result), "status")
                    if final_status in ("review", "done"):
                        break
                    if final_status in ("failed", "blocked_human", "conflict"):
                        return False, f"task ended in status={final_status}"
                    await asyncio.sleep(15)
                else:
                    return False, "timeout waiting for review/done (25 min)"

                if no_merge:
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
    dirty = _git_status_porcelain(root)
    if dirty:
        return False, f"worktree not clean after merge: {dirty[:200]}"
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
        cfg = config.host(to_host)
    except ValueError as e:
        return False, str(e)[:200]
    alias = cfg.get("ssh")
    if not alias:
        return False, "target unreachable (no ssh alias)"
    remote_root = cfg.get("agents_root")
    if not remote_root:
        return False, "target has no agents_root configured"
    python = f"{remote_root}\\.venv\\Scripts\\python.exe" if cfg.get("os") == "windows" \
        else f"{remote_root}/.venv/bin/python"
    cmd = f'cd "{remote_root}" && "{python}" -m tools.mesh_check --get-task {task_id} --json'
    out = _ssh_run(alias, cmd, timeout=20)
    if out is None:
        return False, "read-only ssh to target failed"
    data = _try_json(out)
    if not data or data.get("id") != task_id:
        return False, "target does not see task (separate ledger)"
    return True, None


# ---------------------------------------------------------------------------
# --local: this host's L0-L2 cells only, no ssh, writes nothing
# ---------------------------------------------------------------------------

async def local_payload() -> dict:
    payload: dict = {}
    if HAVE_CONFIG:
        payload["l0"] = _to_cell(check_l0(ROOT))
        payload["l1"] = {h: _to_cell(check_l1(h)) for h in HOSTS}
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
    combined: dict = {lvl: {h: {} for h in HOSTS} for lvl in LEVELS}
    running_host = _running_host_guess(ROOT)

    if running_host and HAVE_CONFIG:
        combined["L0"][running_host][running_host] = _to_cell(check_l0(ROOT))
        combined["L2"][running_host][running_host] = _to_cell(await check_l2(ROOT))
        for h in HOSTS:
            if h == running_host:
                continue
            combined["L1"][running_host][h] = _to_cell(check_l1(h))

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
            ok, reason = await run_l3_probe(running_host, target, ROOT, args.expect, args.no_merge)
            combined["L3"][running_host][target] = {"ok": ok, "reason": reason}

    if running_host and HAVE_CONFIG and _wave_index(args.expect) >= _wave_index("w1"):
        for target in HOSTS:
            if target == running_host:
                continue
            ok, reason = l4_probe(running_host, target)
            combined["L4"][running_host][target] = {"ok": ok, "reason": reason}

    return combined, running_host


def _l1_alias_for(to_host: str) -> str | None:
    if not HAVE_CONFIG:
        return "?"
    try:
        return config.host(to_host).get("ssh")
    except ValueError:
        return "?"


def render(combined: dict, expect: str) -> tuple[str, bool, int, int]:
    """Returns (markdown, any_fail_in_scope, n_ok, n_fail)."""
    expect_idx = _wave_index(expect)
    lines: list[str] = []
    n_ok = 0
    n_fail = 0
    any_fail = False

    for level in LEVELS:
        lines.append(f"## {level}")
        lines.append("")
        lines.append("| from \\ to | " + " | ".join(HOSTS) + " |")
        lines.append("|---|" + "---|" * len(HOSTS))
        for frm in HOSTS:
            row = [frm]
            for to in HOSTS:
                key = (level, frm, to)
                first_green = EXPECT.get(key)
                computed = (combined.get(level, {}).get(frm, {}) or {}).get(to)
                if first_green is None:
                    row.append("n/a")
                    continue
                if _wave_index(first_green) > expect_idx:
                    if level == "L1" and _l1_alias_for(to) is None:
                        row.append("closed (by design)")
                    else:
                        row.append("n/a")
                    continue
                if computed is None:
                    row.append("n/a")
                    continue
                if computed["ok"]:
                    row.append("ok")
                    n_ok += 1
                else:
                    row.append(f"FAIL({computed['reason']})")
                    n_fail += 1
                    any_fail = True
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    return "\n".join(lines), any_fail, n_ok, n_fail


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
    ap.add_argument("--live", action="store_true", help="run real L3 delegate probes")
    ap.add_argument("--no-merge", action="store_true", help="L3: skip merge_task after delegate")
    ap.add_argument("--local", action="store_true", help="print this host's L0-L2 cells only")
    ap.add_argument("--json", action="store_true", help="with --local, JSON output (default)")
    ap.add_argument("--get-task", metavar="TASK_ID", help="print db.get_task(TASK_ID) as JSON")
    args = ap.parse_args(argv)
    if not args.local and not args.get_task and not args.expect:
        ap.error("--expect is required outside --local/--get-task")
    return args


async def amain(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

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
