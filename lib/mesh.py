"""Org Mesh dispatch client (W2.3): one call to run a node_dispatch verb on a host.

docs/design/org-mesh.md, W2. The server half is tools/node_dispatch.py: an
enumerated verb list (`probe`, `pid_alive`, `spawn_worker`, `kill_worker`,
`start_clevel`, `deliver_letter`, `publish_branch`) that a caller can only NAME
a hub row for, never send a shell to. This module is the client half:

    dispatch(host, verb, *args, timeout=None) -> dict

  host == self_host()   in-process, `tools.node_dispatch.dispatch(verb, args)`.
  any other host        `ssh -F none -i ~/.ssh/org_dispatch -o BatchMode=yes
                        -o ConnectTimeout=10 <SSH_OPTIONS...> <mesh_ssh> <verb> <args...>`;
                        `mesh_ssh` is the host's user@tailnet-address in
                        config/hosts.yaml, and the remote `authorized_keys` line pins
                        that key to `python -m tools.node_dispatch`
                        (docs/ops/node-dispatch.md, installed in W2.8).

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
import re
import shlex
import subprocess

from lib import config
from tools.agent_transport import WAKE_WORST_CASE_S

ENV_FLAG = "ORG_MESH_DISPATCH"
ENV_MAX_ATTEMPTS = "ORG_MESH_MAX_ATTEMPTS"
SSH_KEY = "~/.ssh/org_dispatch"
CONNECT_TIMEOUT_S = 10
DEFAULT_TIMEOUT_S = 30

# A `queued_remote` row (a mesh spawn the host did not answer) is retried once
# per watchdog pass, INTERVAL_S = 300 s in runners/watchdog.py. The first
# attempt is at delegate time, so 12 attempts are 11 passes: about 55 minutes
# of silence (longer when a hung dial eats its full 300 s verb timeout). That
# rides out a reboot, a Windows update restart or a tailnet re-key, and it
# stops well before the row's path locks have blocked other work for hours.
# Past it the row is failed and the owner told (delegate.give_up_queued_remote).
MAX_ATTEMPTS = 12

# The Windows wake inside `deliver_letter` (agent_transport.wake_windows_tab:
# schtasks /run, then a wait for the result) can block up to WAKE_WORST_CASE_S.
# The ssh dial comes first and the far side then starts python, reads the
# ledger and writes the letter: that part gets this margin. A letter whose
# wake is slow is already on disk, so the timeout must not be the thing that
# reports the host unreachable.
LETTER_WRITE_MARGIN_S = 15

# Wall-clock ceilings for the verbs that do real work on the far side. The
# numbers sit just above the ones node_dispatch and delegate already use
# (spawn script 120 s + prompt delay; git push 120 s; launcher 300 s).
VERB_TIMEOUT_S = {
    "spawn_worker": 300,
    "start_clevel": 180,
    "publish_branch": 150,
    "kill_worker": 60,
    # ssh dial, then the far side's wake (up to WAKE_WORST_CASE_S), then the write.
    "deliver_letter": CONNECT_TIMEOUT_S + round(WAKE_WORST_CASE_S) + LETTER_WRITE_MARGIN_S,
}

_SSH_FAILED = 255  # ssh's own exit code: no connection, no auth, no host

# W2.7 F4 (task-42fdcda7): the dispatch key and only it, on a fresh
# connection, with nothing forwarded. Without these, ~/.ssh/config for the
# alias applies: a ControlMaster/ControlPath entry rides an admin connection
# that is already open (the verb then runs as a plain command under the admin
# key and the forced command is never used), and agent keys are offered when
# org_dispatch is refused. W2.8 goes further and reads no config file at all
# (MESH_SSH_CONFIG below).
SSH_OPTIONS = (
    "BatchMode=yes",
    f"ConnectTimeout={CONNECT_TIMEOUT_S}",
    "IdentitiesOnly=yes",
    "IdentityAgent=none",
    "ControlMaster=no",
    "ControlPath=none",
    "ForwardAgent=no",
    "ForwardX11=no",
    "ClearAllForwardings=yes",
    "PermitLocalCommand=no",
    "StrictHostKeyChecking=yes",
)

# W2.8: `ssh -F none` reads neither ~/.ssh/config nor /etc/ssh/ssh_config.
# IdentitiesOnly keeps every IdentityFile a config file names for the
# destination: the admin alias's own line, or a `Host *` default. If the far
# side refused org_dispatch, ssh would then offer the admin key, and the verb
# text would run as a plain command in a shell. With no config file the
# dispatch key is the only identity ssh has, whatever any dispatcher's config
# says. The design first gave each dispatcher a `<host>-mesh` alias (W2.7
# review); a Host block cannot rule out a `Host *` IdentityFile, and every
# dispatcher would need one block per target.
MESH_SSH_CONFIG = "none"

# config/hosts.yaml `mesh_ssh`: `user@address`, never the admin `ssh` alias.
# A config-free ssh cannot resolve an alias, and the address must be the
# host's TAILNET address: the authorized_keys `from=` pins the dispatcher's
# tailnet address, and the admin alias for Contabo dials its public one. The
# shape check also keeps the value from being read as an ssh option.
_MESH_DEST_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,31}@[A-Za-z0-9][A-Za-z0-9.-]{0,252}")


class MeshUnreachable(Exception):
    """The host did not answer with a node_dispatch reply: no route, ssh error,
    timeout, or output that is not JSON. Says nothing about whether the verb ran."""


def enabled() -> bool:
    """ORG_MESH_DISPATCH is 1/true/on. Default off: see the module docstring."""
    return os.environ.get(ENV_FLAG, "").strip().lower() in ("1", "true", "on")


def max_attempts() -> int:
    """How many unanswered spawn attempts a `queued_remote` row gets before it
    is failed: ORG_MESH_MAX_ATTEMPTS, else MAX_ATTEMPTS. A value that is not a
    whole number >= 1 falls back to the default: a typo must never turn the
    cap off, which is the unbounded retry this exists to stop."""
    try:
        n = int(os.environ.get(ENV_MAX_ATTEMPTS, "").strip())
    except ValueError:
        return MAX_ATTEMPTS
    return n if n >= 1 else MAX_ATTEMPTS


def _node_dispatch():
    # Lazy: node_dispatch pulls in lib.db and mailbox, and enabled() must stay
    # importable from anywhere without that.
    from tools import node_dispatch
    return node_dispatch


def mesh_destination(host: str) -> str:
    """The `user@address` a mesh call to `host` dials: config/hosts.yaml
    `mesh_ssh`. ValueError: unknown host. MeshUnreachable when the host has
    none (the Mac, whose sshd stays closed until G2) or the value is not a
    plain user@address. Nothing is dialled in either case."""
    dest = config.host(host).get("mesh_ssh")
    if not dest:
        raise MeshUnreachable(f"host {host!r} has no mesh_ssh destination; nothing to dial")
    if not isinstance(dest, str) or not _MESH_DEST_RE.fullmatch(dest):
        raise MeshUnreachable(f"host {host!r}: mesh_ssh {dest!r} is not user@address; "
                              "refusing to dial")
    return dest


def build_argv(host: str, verb: str, args: tuple[str, ...] | list[str]) -> list[str]:
    """The exact ssh argv for a remote call. Raises `node_dispatch.Refusal`
    (nothing built) for an unknown verb, a malformed argument or a command
    node_dispatch's parser would refuse. ValueError: unknown host.
    MeshUnreachable: the host has no usable mesh_ssh (mesh_destination)."""
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
    dest = mesh_destination(host)
    options = [part for opt in SSH_OPTIONS for part in ("-o", opt)]
    return ["ssh", "-F", MESH_SSH_CONFIG, "-i", os.path.expanduser(SSH_KEY), *options,
            dest, command]


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
