"""Org Mesh dispatch client (W2.3): one call to run a node_dispatch verb on a host.

docs/design/org-mesh.md, W2. The server half is tools/node_dispatch.py: an
enumerated verb list (`probe`, `pid_alive`, `spawn_worker`, `kill_worker`,
`start_clevel`, `deliver_letter`, `publish_branch`) that a caller can only NAME
a hub row for, never send a shell to. This module is the client half:

    dispatch(host, verb, *args, timeout=None) -> dict

  host == self_host()   in-process, `tools.node_dispatch.dispatch(verb, args)`.
  any other host        `ssh -i ~/.ssh/org_dispatch -o BatchMode=yes
                        -o ConnectTimeout=10 <alias> <verb> <args...>`; the
                        remote `authorized_keys` line pins that key to
                        `python -m tools.node_dispatch` (docs/ops/node-dispatch.md,
                        installed in W2.8).

Two failure kinds stay apart, and callers depend on it:

  - a verb that refused or failed comes back as the dict node_dispatch printed,
    `{"ok": False, "verb": ..., "error": ...}`. The box was reached and it said no.
  - the box was NOT reached, timed out, or answered with something that is not
    node_dispatch's JSON line: `MeshUnreachable`. Unknown is never "no" -- a
    caller queues and retries, it does not fail the task.

Arguments are checked here, before ssh, with node_dispatch's own arg rules
(`_check_args`, `parse_command`), so an injection-looking value never leaves
this process. The remote checks again; that is a second lock, not a substitute.

Every node_dispatch verb reads its task from the ledger by id. Until each host
shares one ledger (W1.10) a remote verb cannot see a row this host created, so
callers wire this behind `enabled()` (env ORG_MESH_DISPATCH, default off).
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess

from lib import config

ENV_FLAG = "ORG_MESH_DISPATCH"
SSH_KEY = "~/.ssh/org_dispatch"
CONNECT_TIMEOUT_S = 10
DEFAULT_TIMEOUT_S = 30

# Wall-clock ceilings for the verbs that do real work on the far side. The
# numbers sit just above the ones node_dispatch and delegate already use
# (spawn script 120 s + prompt delay; git push 120 s; launcher 300 s).
VERB_TIMEOUT_S = {
    "spawn_worker": 300,
    "start_clevel": 180,
    "publish_branch": 150,
    "kill_worker": 60,
}

_SSH_FAILED = 255  # ssh's own exit code: no connection, no auth, no host


class MeshUnreachable(Exception):
    """The host did not answer with a node_dispatch reply: no route, ssh error,
    timeout, or output that is not JSON. Says nothing about whether the verb ran."""


def enabled() -> bool:
    """ORG_MESH_DISPATCH is 1/true/on. Default off: see the module docstring."""
    return os.environ.get(ENV_FLAG, "").strip().lower() in ("1", "true", "on")


def _node_dispatch():
    # Lazy: node_dispatch pulls in lib.db and mailbox, and enabled() must stay
    # importable from anywhere without that.
    from tools import node_dispatch
    return node_dispatch


def build_argv(host: str, verb: str, args: tuple[str, ...] | list[str]) -> list[str]:
    """The exact ssh argv for a remote call. Raises `node_dispatch.Refusal`
    (nothing built) for an unknown verb, a malformed argument or a command
    node_dispatch's parser would refuse. ValueError: unknown host.
    MeshUnreachable: the host has no ssh alias (the Mac's is null on purpose)."""
    nd = _node_dispatch()
    if verb not in nd.HANDLERS:
        raise nd.Refusal(f"unknown verb {nd._show(verb)}. Known: {', '.join(nd.HANDLERS)}")
    args = list(args)
    if not all(isinstance(a, str) for a in args):
        raise nd.Refusal("args must be a list of strings")
    nd._check_args(verb, args)
    command = shlex.join([verb, *args])
    # Round-trip through the server's own parser: length cap, control
    # characters, and a split that must give back exactly what we meant.
    if nd.parse_command(command) != [verb, *args]:
        raise nd.Refusal(f"{verb}: arguments do not survive quoting")
    alias = config.host(host).get("ssh")
    if not alias:
        raise MeshUnreachable(f"host {host!r} has no ssh alias; nothing to dial")
    return ["ssh", "-i", os.path.expanduser(SSH_KEY),
            "-o", "BatchMode=yes", "-o", f"ConnectTimeout={CONNECT_TIMEOUT_S}",
            alias, command]


def dispatch(host: str, verb: str, *args: str, timeout: float | None = None) -> dict:
    """Run `verb args...` on `host`. Returns node_dispatch's reply dict, refusals
    and failures included. Raises MeshUnreachable when the host gave no reply.

    A bad verb or argument is answered here with the same refusal dict the
    server would give, and never reaches ssh. `timeout` defaults per verb."""
    if host == config.self_host():
        return _node_dispatch().dispatch(verb, list(args))
    nd = _node_dispatch()
    try:
        argv = build_argv(host, verb, args)
    except nd.Refusal as e:
        return {"ok": False, "verb": verb, "error": str(e)}
    limit = timeout if timeout is not None else VERB_TIMEOUT_S.get(verb, DEFAULT_TIMEOUT_S)
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=limit,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise MeshUnreachable(f"{verb} on {host}: no reply in {limit}s") from None
    except OSError as e:
        raise MeshUnreachable(f"{verb} on {host}: cannot run ssh: {e}") from None
    if r.returncode == _SSH_FAILED:
        raise MeshUnreachable(f"{verb} on {host}: ssh failed: {(r.stderr or '').strip()[:200]}")
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    try:
        reply = json.loads(lines[-1]) if lines else None
    except ValueError:
        reply = None
    if not isinstance(reply, dict) or not isinstance(reply.get("ok"), bool):
        raise MeshUnreachable(
            f"{verb} on {host}: reply is not a node_dispatch JSON line "
            f"(exit {r.returncode}): {((r.stdout or '') + (r.stderr or ''))[-200:].strip()!r}")
    return reply
