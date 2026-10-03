"""Org Mesh W4.7: scripts/drill-join.sh, the join drill.

The drill drives docker, the join door, hq_join, the Tailscale API, gh, git and ssh. None of that
is reachable here, and none of it may be: docker, curl, gh, git, ssh, free, the door, the hub
wrapper and the python that runs `-m tools.hq_join` are shell stubs in tmp_path, first on PATH,
and they keep their state in plain files. The script itself runs for real, under /bin/bash (3.2 on
the Mac, as the drill's author wrote it). Every secret the stubs hold is synthetic, and the tests
look for each of them in everything the script printed or wrote.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w47_drill_join.py
"""
from __future__ import annotations

import json
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools import mesh_check

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "drill-join.sh"
STAMP = "20261003-140000"
HOST = f"drill-{STAMP}"
TOKEN = "jointok-SECRET-0123456789abcdef"           # what `hq_join mint` prints in the stub
TS_ID, TS_SECRET = "ts-client-id-test", "ts-client-secret-test-0123456789"
TS_ACCESS = "ts-access-test-token-123"
JOIN_DSN_PASSWORD = "joinpw-" + "SECRET-0123456789"  # the password inside ORG_JOIN_DB_URL; built so no scanner reads it as one
JOIN_DSN = f"postgresql://org_join:{JOIN_DSN_PASSWORD}@hub.example:5432/org"
SEALED = "SEALED-BODY-MARKER-0123456789"            # what a 200 from the token service carries
TOKEN_URL = "http://100.64.0.9:8792/v1/token"
NODE_FP, HUB_FP = "abcd1234", "zzzz9999"            # the node prints the first; `status` shows the second
SECRETS = (TOKEN, TS_ID, TS_SECRET, TS_ACCESS, JOIN_DSN_PASSWORD, SEALED)
SHA = "0123456789abcdef0123456789abcdef01234567"
STEP_NAMES = re.search(r'^STEP_NAMES="([^"]+)"', SCRIPT.read_text(), re.M).group(1).split()

PRELUDE = r'''#!/bin/bash
S=$SHIM_STATE
H=drill-$DRILL_STAMP
f() { [ -e "$S/flags/$1" ]; }
'''

FREE = PRELUDE + r'''
echo "free $*" >>"$S/calls.log"
avail=$(cat "$S/avail_mb" 2>/dev/null || echo 4500)
echo "              total        used        free      shared  buff/cache   available"
echo "Mem:           7900        3000        1000         100        3000        $avail"
'''

DOOR = PRELUDE + r'''
echo "door $*" >>"$S/calls.log"
case $1 in
  status) if [ "$(cat "$S/door" 2>/dev/null)" = open ]; then echo "open until 2026-10-03T14:30:00Z"; else echo closed; fi ;;
  open) f door_open_fails && { echo "door: could not start org-join.service" >&2; exit 1; }
        echo open >"$S/door"; echo "open until 2026-10-03T14:30:00Z" ;;
  close) f door_stuck || echo closed >"$S/door"; echo closed ;;
esac
'''

# with-org-db-env.sh loads the root folder of Agents-Core prod: ORG_DB_URL only, no Tailscale client.
WRAP = r'''#!/bin/bash
echo "wrap $*" >>"$SHIM_STATE/calls.log"
exec "$@"
'''

# `infisical_setup.py run Agents-Core prod --path /org-join --`: the one folder that holds the Tailscale
# OAuth client and the join role's DSN (deploy/join/README.md).
JOINENV = r'''#!/bin/bash
echo "joinenv $*" >>"$SHIM_STATE/calls.log"
if [ ! -e "$SHIM_STATE/flags/no_ts_creds" ]; then
  export TAILSCALE_OAUTH_CLIENT_ID=ts-client-id-test TAILSCALE_OAUTH_CLIENT_SECRET=ts-client-secret-test-0123456789
fi
if [ ! -e "$SHIM_STATE/flags/no_join_dsn" ]; then
  export ORG_JOIN_DB_URL=postgresql://org_join:joinpw-SECRET-0123456789@hub.example:5432/org
fi
exec "$@"
'''

# `tailscale ip -4`: the hub's tailnet address, asked only when nothing set the token URL.
TAILSCALE = r'''#!/bin/bash
echo "tailscale $*" >>"$SHIM_STATE/calls.log"
[ -e "$SHIM_STATE/flags/no_tailnet_address" ] && exit 1
echo 100.64.0.9
'''

DOCKER = PRELUDE + r'''
echo "docker $*" >>"$S/calls.log"
cmd=$1; shift
case $cmd in
  ps)
    case "$*" in
      *"name=drill-"*) cat "$S/containers" 2>/dev/null ;;
      *"name=^"*) n=$(printf '%s' "$*" | sed 's/.*name=^\([^$]*\)\$.*/\1/'); grep -qx "$n" "$S/containers" 2>/dev/null && echo 4f1c2a9d7b3e ;;
    esac; exit 0 ;;
  volume)
    sub=$1; shift
    case $sub in
      ls) case "$*" in
            *"name=drill-"*) cat "$S/volumes" 2>/dev/null ;;
            *"name=^"*) n=$(printf '%s' "$*" | sed 's/.*name=^\([^$]*\)\$.*/\1/'); grep -qx "$n" "$S/volumes" 2>/dev/null && echo "$n" ;;
          esac ;;
      create) echo "$1" >>"$S/volumes"; echo "$1" ;;
      rm) f volume_stuck || { grep -vx "$2" "$S/volumes" >"$S/volumes.n" 2>/dev/null; mv "$S/volumes.n" "$S/volumes"; } ;;
    esac; exit 0 ;;
  run)
    f docker_run_fails && { echo "docker: Error response from daemon: no space left on device" >&2; exit 125; }
    while [ $# -gt 0 ]; do [ "$1" = --name ] && { echo "$2" >>"$S/containers"; break; }; shift; done
    echo deadbeefcafe; exit 0 ;;
  rm)
    f container_stuck && exit 0
    for n in "$@"; do case $n in -*) ;; *) grep -vx "$n" "$S/containers" >"$S/containers.n" 2>/dev/null; mv "$S/containers.n" "$S/containers" ;; esac; done
    exit 0 ;;
  exec) ;;
  *) echo "stub docker: unexpected $cmd" >&2; exit 99 ;;
esac
# docker exec [-d] [-i] [-e VAR] <container> <command...>
while [ $# -gt 0 ]; do
  case $1 in -d|-i) shift ;; -e) shift 2 ;; *) break ;; esac
done
shift                                   # the container name
joined="$*"
case "$joined" in
  "sh -c cat > /tmp/"*) name=$(printf '%s' "$joined" | sed 's#.*/tmp/\(.*\)\.sh#\1#'); mkdir -p "$S/scripts"; cat >"$S/scripts/$name.sh"; exit 0 ;;
  "sh -c apt-get"*) f prep_fails && { echo "E: Unable to locate package curl" >&2; exit 100; }; exit 0 ;;
  "sh -c while ! command -v tailscaled"*) exit 0 ;;
  "sh -c curl -fsSL"*)
    echo "env_token=${ORG_JOIN_TOKEN:+yes}" >>"$S/calls.log"
    printf '%s' "${ORG_JOIN_TOKEN:-}" >"$S/seen_token"
    : >"$S/joinstarted"
    f join_dies || echo pending >"$S/row_status"
    exit 0 ;;
  "cat /tmp/join.log")
    [ -e "$S/joinstarted" ] || exit 1
    echo "join: step 2 keys"
    if f join_dies; then echo "join: fatal: tailscale up failed with tskey-auth-kABCDEF123456789 and $(cat "$S/seen_token")"
    elif ! f no_fingerprint; then
      echo "join: fingerprint: $FP - the operator approves this in the Run Inbox"
      echo "join: waiting for the operator to approve fingerprint $FP in the Run Inbox (0 s)"
    fi
    f join_probe_fails && [ -e "$S/provisioned" ] && echo "join: probe: FAILED: no JSON answer (see the messages above)"
    exit 0 ;;
  "cat /tmp/join.rc")
    f join_dies && { echo 1; exit 0; }
    f join_hangs && exit 1
    [ -e "$S/provisioned" ] || exit 1
    if f join_probe_fails; then echo 2; else echo 0; fi
    exit 0 ;;
  "sh -c age-keygen"*) f age_fallback && echo "$FP"; exit 0 ;;
  "sh /tmp/token_worker.sh"*)
    f tw_fails && { echo "claude: Invalid API key"; exit 1; }
    for a in "$@"; do nonce=$a; done; echo "$nonce"; exit 0 ;;
  "sh /tmp/remote_control.sh"*)
    f rc_refused && { echo "Error: Remote Control requires a full-scope login. Run claude login."; echo "second line"; exit 1; }
    f rc_prints_url && echo "Remote Control ready: https://claude.ai/code/session_AbC123xyz connect from your phone"
    exit 124 ;;
  "sh /tmp/probe.sh"*)
    f probe_readonly && { echo "ERROR: The key you are using is read-only."; echo "fatal: Could not read from remote repository."; exit 6; }
    f probe_readonly_gh && { echo "ERROR: The key you are authenticating with has been marked as read only."; echo "fatal: Could not read from remote repository."; exit 6; }
    f probe_wrong_sha && { echo "sha=1111111111111111111111111111111111111111"; echo "$SHA" >"$S/remote_branch"; exit 0; }
    echo "$SHA" >"$S/remote_branch"; echo "sha=$SHA"; exit 0 ;;
esac
echo "stub docker exec: unexpected: $joined" >&2; exit 99
'''.replace("$FP", NODE_FP).replace("$SHA", SHA)

PY = PRELUDE + r'''
echo "py $* [w42=${ORG_W42_PROVISION:-unset}]" >>"$S/calls.log"
[ "$1" = "-m" ] || exit 99
mod=$2; verb=$3; shift 3
setrow() { f leave_keeps_token || echo "$1" >"$S/row_status"; }     # a hub that went on serving the host
case "$mod $verb" in
  "tools.join_api --check-db")                      # the join API's own start-up read with ORG_JOIN_DB_URL
    [ -n "${ORG_JOIN_DB_URL:-}" ] || { echo "join_api: ORG_JOIN_DB_URL is not set" >&2; exit 2; }
    f dsn_stale && { echo "join_api: cannot log in or read with ORG_JOIN_DB_URL (HubConnectError)" >&2; exit 1; }
    exit 0 ;;
  "tools.hq_join status")
    if [ "$1" = --host ]; then
      [ -e "$S/row_status" ] || { echo "hq_join: refused (unknown_host): host '$H' did not join through hq_join" >&2; exit 2; }
      echo "$H  $(cat "$S/row_status")  linux  fingerprint $HUB_FP  approved 2026-10-03T14:05:00Z"
    else
      [ -e "$S/hosts" ] && cat "$S/hosts" || echo "hq_join: no node has joined through hq_join"
      [ -e "$S/row_status" ] && echo "$H  $(cat "$S/row_status")  linux  fingerprint $HUB_FP  -"
    fi
    exit 0 ;;
  "tools.hq_join mint")
    f mint_fails && { printf 'hq_join: refused (db): "quoted" back\\slash \001 tskey-auth-kLEAK1234567890 end\n' >&2; exit 2; }
    echo "hq_join: token for $H valid until 2026-10-03T14:20:00Z; shown once, single use" >&2
    echo "$TOKEN"; exit 0 ;;
  "tools.hq_join approve")
    f approve_fails && { echo "hq_join: refused (fingerprint_mismatch): the key on file does not match" >&2; exit 2; }
    [ "$4" = "$FP" ] || { echo "hq_join: refused (fingerprint_mismatch): the key on file does not match" >&2; exit 2; }
    : >"$S/approved"; echo '{"ok": true, "status": "pending_identity"}'; exit 0 ;;
  "tools.hq_join provision")
    [ "${ORG_W42_PROVISION:-}" = 1 ] || { echo "hq_join: refused (not_enabled): live provisioning is off" >&2; exit 2; }
    [ -e "$S/approved" ] || { echo "hq_join: refused (not_approved)" >&2; exit 2; }
    [ -n "${ORG_NODE_TOKEN_URL:-}" ] || { echo "hq_join: refused (no_token_url): the hub's token URL is not set" >&2; exit 2; }
    echo "token_url=$ORG_NODE_TOKEN_URL" >>"$S/calls.log"
    f provision_fails && { echo "hq_join: failed (JoinError): the bundle could not be sealed" >&2; exit 1; }
    : >"$S/provisioned"; : >"$S/ts_device_present"; : >"$S/deploy_key_present"; echo ready >"$S/row_status"
    echo '{"ok": true}'; exit 0 ;;
  "tools.hq_join leave")
    : >"$S/left_ran"
    setrow leaving                                  # the first step: no flag needed, the hub's own write
    if [ "${ORG_W42_PROVISION:-}" != 1 ]; then      # w42_enabled() is false: UNWIRED_REVOKERS, nothing removed
      echo "  [ok] status_leaving on $H: status leaving, token service refuses $H"
      echo "  [FAILED] tailscale_device on $H: not wired yet: needs ORG_W42_PROVISION=1 and TAILSCALE_OAUTH_CLIENT_ID + TAILSCALE_OAUTH_CLIENT_SECRET in the environment"
      echo "  [FAILED] github_deploy_key on $H: not wired yet: live revocation is off (set ORG_W42_PROVISION=1, W4.2)"
      for t in mac contabo winbox; do echo "  [FAILED] authorized_keys on $t: not wired yet: needs the W2.8 ssh mesh (forced-command keys)"; done
      echo "hq_join: $H NOT marked left; left behind: tailscale_device:$H, github_deploy_key:$H, authorized_keys:mac, authorized_keys:contabo, authorized_keys:winbox"
      exit 1
    fi
    f leave_keeps_device || rm -f "$S/ts_device_present"
    f leave_keeps_key || rm -f "$S/deploy_key_present"
    if f leave_tailscale_fails; then
      echo "  [ok] status_leaving on $H: status leaving, token service refuses $H"
      echo "  [FAILED] tailscale_device on $H: TailscaleError: boom"
      echo "  [ok] github_deploy_key on $H"
      echo "hq_join: $H NOT marked left; left behind: tailscale_device:$H"; exit 1
    fi
    echo "  [ok] status_leaving on $H: status leaving, token service refuses $H"; echo "  [ok] tailscale_device on $H"; echo "  [ok] github_deploy_key on $H"
    if f leave_all_ok; then
      for t in mac contabo winbox; do echo "  [ok] authorized_keys on $t"; done
      setrow left; echo "hq_join: $H is now \`left\`"; exit 0
    fi
    for t in mac contabo winbox; do echo "  [FAILED] authorized_keys on $t: not wired yet: needs the W2.8 ssh mesh (forced-command keys)"; done
    echo "hq_join: $H NOT marked left; left behind: authorized_keys:mac, authorized_keys:contabo, authorized_keys:winbox"
    exit 1 ;;
  "tools.mesh_check --join-drill")
    case $1 in
      task-create) echo "[db] WARNING: creating ownerless task" >&2; echo task-0123abcd ;;
      task-close) : >"$S/task_closed" ;;
      record) f record_fails && { echo "join-drill: refused: OperationalError: hub down" >&2; exit 2; }; cp "$2" "$S/recorded.json" ;;
    esac
    exit 0 ;;
esac
echo "stub py: unexpected: $mod $verb" >&2; exit 99
'''.replace("$TOKEN", TOKEN).replace("$FP", NODE_FP).replace("$HUB_FP", HUB_FP)

CURL = PRELUDE + r'''
echo "curl $*" >>"$S/calls.log"
[ -t 0 ] || cat >/dev/null
for a in "$@"; do case $a in http*) url=$a ;; esac; done
case $url in
  http://100.64.0.9:8792/health)                    # the token service
    f token_health_down && exit 7
    if f token_not_loaded; then echo '{"ok": true, "token_loaded": false, "db": true}'
    else echo '{"ok": true, "token_loaded": true, "db": true}'; fi
    exit 0 ;;
  http://100.64.0.9:8792/v1/token\?host=*)          # `-w '\n%{http_code}'`: the body, then the status
    f token_down && exit 7
    st=$(cat "$S/row_status" 2>/dev/null)
    case $st in
      ready|online) code=200; body='{"ciphertext": "SEALED-BODY-MARKER-0123456789"}' ;;
      leaving|left) code=403; body='{"error": "left"}' ;;
      pending)      code=403; body='{"error": "not_approved"}' ;;
      *)            code=403; body='{"error": "unknown_host"}' ;;
    esac
    printf '%s\n%s' "$body" "$code"; exit 0 ;;
esac
f ts_api_down && exit 22
case $url in
  */oauth/token) echo '{"access_token":"ts-access-test-token-123","token_type":"Bearer","expires_in":3600}' ;;
  */tailnet/-/devices)
    if [ -e "$S/ts_device_present" ]; then echo "{\"devices\":[{\"id\":\"n1\",\"hostname\":\"$H\",\"tags\":[\"tag:org-node\"]}]}"
    else echo '{"devices":[{"id":"n0","hostname":"contabo"}]}'; fi ;;
  *) echo "stub curl: unexpected $url" >&2; exit 99 ;;
esac
'''

GH = PRELUDE + r'''
echo "gh $*" >>"$S/calls.log"
f gh_down && { echo "gh: HTTP 401" >&2; exit 1; }
if [ -e "$S/deploy_key_present" ]; then echo "[{\"id\":1,\"title\":\"org-node:$H\",\"read_only\":true}]"; else echo '[{"id":2,"title":"ci"}]'; fi
'''

GIT = PRELUDE + r'''
echo "git $*" >>"$S/calls.log"
case "$*" in
  *rev-parse*)
    [ -s "$S/real_git" ] && exec "$(cat "$S/real_git")" "$@"      # a test that wants the real answer
    case "$*" in
      *"--show-toplevel"*) exit 128 ;;
      *"--short HEAD"*)      # git -C <dir> ...: the stub's commit is "c-" plus the directory's name
        [ "$1" = -C ] || exit 128; f no_git_here && exit 128; echo "c-$(basename "$2")"; exit 0 ;;
    esac ;;
  *ls-remote*) [ -e "$S/remote_branch" ] && printf '%s\t%s\n' "$(cat "$S/remote_branch")" "refs/heads/agent/probe-task-0123abcd" ;;
  *"push -q origin --delete"*) f branch_delete_fails && { echo "remote: Permission denied" >&2; exit 1; }; rm -f "$S/remote_branch" ;;
  *) echo "stub git: unexpected $*" >&2; exit 99 ;;
esac
exit 0
'''

SSH = PRELUDE + r'''
echo "ssh $*" >>"$S/calls.log"
f winbox_down && exit 255
case "$*" in
  *"/C:ssh-"*) f winbox_unreadable && exit 1; exit 0 ;;     # findstr: 1 = no match OR a file it cannot open
  *) f winbox_unreadable && exit 1; f winbox_line && exit 0; exit 1 ;;
esac
'''

STUBS = {"free": FREE, "docker": DOCKER, "curl": CURL, "gh": GH, "git": GIT, "ssh": SSH, "tailscale": TAILSCALE}


class Drill:
    """One tmp_path world for the script: stubs, a core checkout, a state dir, a state shim."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        self.shim = tmp_path / "shim"
        (self.shim / "flags").mkdir(parents=True)
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        self.live = tmp_path / "live"           # stand-in for /opt/MoonieXHQ/Agents/Core (the join service's code)
        self.live.mkdir()
        self.core = tmp_path / "core"
        (self.core / "state").mkdir(parents=True)
        (self.core / "tools").mkdir()
        self.mesh_check = self.core / "tools" / "mesh_check.py"
        self.mesh_check.write_text("# stand-in for the checkout's tool: the preflight only looks for this flag\n"
                                   "    ap.add_argument('--join-drill', nargs=2)\n")
        self.join_api = self.core / "tools" / "join_api.py"
        self.join_api.write_text("# stand-in for the checkout's tool: the preflight only looks for this flag\n"
                                 "    p.add_argument('--check-db', action='store_true')\n")
        self.state = tmp_path / "out" / "mesh-check"
        self.rows = self.core / "state" / "re-os-drills.jsonl"
        self.ak = tmp_path / "authorized_keys"
        self.ak.write_text("ssh-ed25519 AAAA placeholder org-dispatch:mac\n")
        for name, body in {**STUBS, "py": PY, "door.sh": DOOR, "wrap.sh": WRAP, "joinenv.sh": JOINENV}.items():
            p = self.bin / name
            p.write_text(body)
            p.chmod(0o755)
        self.env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "TMPDIR": str(tmp_path),
            "SHIM_STATE": str(self.shim),
            "DRILL_STAMP": STAMP,
            "DRILL_CORE": str(self.core),
            "DRILL_LIVE_CORE": str(self.live),
            "DRILL_STATE_DIR": str(self.state),
            "DRILL_ROWS_FILE": str(self.rows),
            "DRILL_PY": str(self.bin / "py"),
            "DRILL_DOOR": str(self.bin / "door.sh"),
            "DRILL_HUB_WRAP": str(self.bin / "wrap.sh"),
            "DRILL_JOIN_ENV_WRAP": str(self.bin / "joinenv.sh"),
            "DRILL_AUTHORIZED_KEYS": str(self.ak),
            "DRILL_ALLOW_NONROOT": "1",
            "DRILL_POLL_S": "0.1",
            "DRILL_FP_WAIT_S": "2",
            "DRILL_JOIN_WAIT_S": "3",
            "DRILL_PROBE_WAIT_S": "20",
            "DRILL_TOKEN_URL": TOKEN_URL,
        }

    def flag(self, *names: str) -> "Drill":
        for n in names:
            (self.shim / "flags" / n).touch()
        return self

    def put(self, name: str, text: str) -> "Drill":
        (self.shim / name).write_text(text)
        return self

    def popen(self, *args: str) -> subprocess.Popen:
        # A pytest run started as a background job inherits SIGINT as ignored, and a shell cannot
        # trap a signal that was ignored when it started: give the script the default back.
        return subprocess.Popen(["/bin/bash", str(SCRIPT), *args], env=self.env, cwd=self.root,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))

    def run(self, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run(["/bin/bash", str(SCRIPT), *args], env=self.env, cwd=self.root,
                              capture_output=True, text=True, timeout=timeout)

    def calls(self) -> list[str]:
        p = self.shim / "calls.log"
        return p.read_text().splitlines() if p.exists() else []

    def has(self, name: str) -> bool:
        return (self.shim / name).exists()

    def read(self, name: str) -> str:
        return (self.shim / name).read_text().strip()

    def result(self) -> dict:
        return json.loads((self.state / "join-drill.json").read_text())

    def step(self, name: str) -> dict:
        return next(s for s in self.result()["steps"] if s["name"] == name)

    def everything(self, cp: subprocess.CompletedProcess) -> str:
        """All the places a secret could land: output, the JSON, the row file, every stub call."""
        parts = [cp.stdout, cp.stderr, "\n".join(self.calls())]
        for p in (self.state / "join-drill.json", self.rows, self.shim / "recorded.json"):
            if p.exists():
                parts.append(p.read_text())
        return "\n".join(parts)

    def left_nothing(self) -> None:
        assert self.read("door") == "closed"
        assert self.read("containers") == "" and self.read("volumes") == ""
        assert not self.has("remote_branch")


@pytest.fixture
def drill(tmp_path):
    d = Drill(tmp_path)
    d.put("door", "closed\n").put("containers", "").put("volumes", "")
    d.flag("leave_all_ok")                       # the world where W2.8 wired authorized_keys
    return d


def started_nothing(d: Drill) -> bool:
    live = ("door open", "docker run", "docker volume create", " mint ", " approve ", " leave ")
    return not any(any(k in c for k in live) for c in d.calls())


# ------------------------------------------------------------------------------ static checks

def test_script_parses_under_bash_and_shellcheck_when_installed():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
    sc = shutil.which("shellcheck")
    if sc:
        out = subprocess.run([sc, "-s", "bash", str(SCRIPT)], capture_output=True, text=True)
        assert out.returncode == 0, out.stdout


def test_script_never_traces_and_never_puts_a_secret_on_a_command_line():
    text = SCRIPT.read_text()
    assert not re.search(r"^\s*set\s+-[a-z]*x", text, re.M) and "xtrace" not in text
    assert "docker exec -d -e ORG_JOIN_TOKEN" in text          # by environment, no value in argv
    assert not re.search(r"--token\b", text)
    # the OAuth token: never `NAME=$CLAUDE_CODE_OAUTH_TOKEN` (env(1), sh -c ...) on any command line
    assert not re.search(r"=\s*[\"']?\$\{?CLAUDE_CODE_OAUTH_TOKEN", text)
    assert not re.search(r"\benv\s+-i\b", text)


def test_every_live_provision_and_leave_runs_with_the_w42_flag():
    # hq_join wires its revokers and provisioner only when ORG_W42_PROVISION=1 (w42_enabled())
    lines = [l for l in SCRIPT.read_text().splitlines()
             if re.search(r"tools\.hq_join (provision|leave)\b", l) and not l.lstrip().startswith(("#", "provision ", "leave "))]
    assert len(lines) == 2 and all("ORG_W42_PROVISION=1" in l for l in lines), lines


# ------------------------------------------------------------------------------ the pass path

def test_pass_path_every_step_ok_and_nothing_left_behind(drill):
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    res = drill.result()
    assert res["ok"] is True and res["host"] == HOST and res["failed_step"] is None
    assert [s["name"] for s in res["steps"]][:len(STEP_NAMES)] == STEP_NAMES
    assert all(s["ok"] is True for s in res["steps"])
    assert res["probe"] == {"task": "task-0123abcd", "branch": "agent/probe-task-0123abcd",
                            "sha": SHA, "seconds": res["probe"]["seconds"]}
    assert res["w40"]["remote_control"] is True and res["w40"]["remote_control_error"] == ""
    drill.left_nothing()
    assert drill.has("task_closed") and drill.has("left_ran")
    assert not drill.rows.exists()                          # no --log-to-repo: nothing appended
    assert '"kind": "join-drill"' in cp.stdout and '"result": "PASS"' in cp.stdout


def test_the_fingerprint_comes_from_the_node_and_the_flag_is_set_only_for_provision_and_leave(drill):
    cp = drill.run()
    assert cp.returncode == 0
    approve = [c for c in drill.calls() if "hq_join approve" in c]
    assert len(approve) == 1 and f"--fingerprint {NODE_FP}" in approve[0] and HUB_FP not in approve[0]
    with_flag = [c for c in drill.calls() if c.startswith("py ") and "[w42=1]" in c]
    assert [("provision" in c, "leave" in c) for c in with_flag] == [(True, False), (False, True)]
    assert drill.read("seen_token") == TOKEN                 # the node got the token, by environment
    assert any(c == "env_token=yes" for c in drill.calls())


def test_the_fingerprint_falls_back_to_the_nodes_key_file_and_says_so(drill):
    drill.flag("no_fingerprint", "age_fallback")
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert any(f"--fingerprint {NODE_FP}" in c for c in drill.calls() if "hq_join approve" in c)
    assert any("age-keygen" in n for n in drill.result()["notes"])


def test_no_fingerprint_anywhere_fails_join(drill):
    drill.flag("no_fingerprint")
    assert drill.run().returncode == 1
    _failed(drill, "join")
    drill.left_nothing()


def test_the_hub_environment_wrapper_is_used_and_the_door_closes_before_the_probe(drill):
    assert drill.run().returncode == 0
    calls = drill.calls()
    assert calls[0].startswith("joinenv ")                    # re-exec through Infisical /org-join,
    assert calls[1].startswith("wrap ")                       # then through with-org-db-env.sh
    closes = [i for i, c in enumerate(calls) if c == "door close"]
    task = next(i for i, c in enumerate(calls) if "--join-drill task-create" in c)
    assert closes and closes[0] < task                        # the public endpoint is shut after the join



def test_the_tailscale_client_comes_from_the_org_join_leg_before_the_hub_wrapper(drill):
    """The hub wrapper loads only the root folder of Agents-Core prod (ORG_DB_URL); the Tailscale OAuth
    client is in /org-join. The first live card ran the script bare and refused at preflight
    (RUN-20261003-0029-5164): the script must load /org-join itself."""
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    first, second = drill.calls()[:2]
    leg, wrap, sh, script = first.split()
    assert (leg, wrap, sh) == ("joinenv", str(drill.bin / "wrap.sh"), "bash")
    assert script.endswith("scripts/drill-join.sh") and second == f"wrap bash {script}"


def test_a_caller_that_already_loaded_org_join_gets_no_second_leg(drill):
    # the shape of the second card: infisical_setup.py run ... --path /org-join -- bash scripts/drill-join.sh
    drill.env.update(TAILSCALE_OAUTH_CLIENT_ID=TS_ID, TAILSCALE_OAUTH_CLIENT_SECRET=TS_SECRET,
                     ORG_JOIN_DB_URL=JOIN_DSN)
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    calls = drill.calls()
    assert calls[0].startswith("wrap ") and not any(c.startswith("joinenv ") for c in calls)


def test_the_org_join_leg_is_infisical_run_on_the_folder_the_join_service_loads(drill):
    del drill.env["DRILL_JOIN_ENV_WRAP"]
    stub = drill.bin / "python3"                          # nothing else on the host runs a bare python3
    stub.write_text(JOINENV.replace('"joinenv $*"', '"python3 $*"').replace(
        'exec "$@"', 'while [ "$#" -gt 0 ] && [ "$1" != -- ]; do shift; done\n'
                     '[ "$#" -gt 0 ] || exit 97\nshift; exec "$@"'))
    stub.chmod(0o755)
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    leg = f"python3 {drill.core}/tools/infisical_setup.py run Agents-Core prod --path /org-join -- "
    assert drill.calls()[0].startswith(leg + f"{drill.bin / 'wrap.sh'} bash ")
    unit = (ROOT / "deploy" / "join" / "org-join.service").read_text(encoding="utf-8")
    assert "infisical_setup.py run Agents-Core prod --as contabo --path /org-join -- " in unit


def test_every_documented_leave_line_loads_org_join_first():
    """A recovery `leave` run through the hub wrapper alone has no Tailscale client and cannot delete
    the tailnet device."""
    lines, fenced = [], False
    for ln in (ROOT / "docs" / "ops" / "join-drill.md").read_text(encoding="utf-8").splitlines():
        if ln.startswith("```"):
            fenced = not fenced
        elif fenced and "tools.hq_join leave" in ln:
            lines.append(ln)
    assert lines, "the recovery section lost its leave line"
    leg = "python3 tools/infisical_setup.py run Agents-Core prod --path /org-join -- scripts/hub/with-org-db-env.sh "
    for ln in lines:
        assert ln.startswith(leg) and "ORG_W42_PROVISION=1" in ln and ln.rstrip().endswith("--live"), ln

def test_no_secret_reaches_output_json_row_or_any_command_line(drill):
    cp = drill.run("--log-to-repo")
    assert cp.returncode == 0
    blob = drill.everything(cp)
    for s in SECRETS:
        assert s not in blob, f"{s} leaked"
    assert "--token" not in blob and "Bearer" not in blob


def test_log_to_repo_appends_exactly_one_row_in_the_existing_shape(drill):
    drill.rows.write_text('{"date": "2026-09-24", "kind": "rehearsed"}\n')
    cp = drill.run("--log-to-repo")
    assert cp.returncode == 0
    lines = drill.rows.read_text().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[1])
    assert set(row) == {"date", "machine", "kind", "scope", "result", "minutes_to_remote_access",
                        "minutes_to_org_restore", "bytes_from_git_mb", "bytes_from_drive_mb",
                        "irreplaceable_lost_gb", "human_steps", "gaps_found", "by", "ref"}
    assert row["kind"] == "join-drill" and row["result"] == "PASS" and row["machine"] == "contabo"
    assert lines[1] in cp.stdout                              # the printed row is the appended row


def test_the_event_row_matches_the_file_and_l8_reads_both_green(drill, tmp_path):
    assert drill.run().returncode == 0
    recorded = json.loads(drill.read("recorded.json"))
    final = drill.result()
    assert recorded["host"] == final["host"] and recorded["ok"] is True
    assert [s["name"] for s in final["steps"]] == [s["name"] for s in recorded["steps"]] + ["record"]
    assert mesh_check.check_l8(drill.state)["ok"] is True
    cell = mesh_check.check_l8(tmp_path / "no-file-here", events=lambda: recorded)   # the Mac
    assert cell["ok"] is True and HOST in cell["note"]


# ------------------------------------------------------------------------------ failing steps

def _failed(d: Drill, step: str) -> dict:
    res = d.result()
    assert res["ok"] is False and res["failed_step"] == step
    assert d.step(step)["ok"] is False
    return res


def test_a_failed_join_still_cleans_up_and_names_the_step(drill):
    drill.flag("join_dies")
    cp = drill.run()
    assert cp.returncode == 1
    res = _failed(drill, "join")
    drill.left_nothing()
    assert drill.step("cleanup")["ok"] is True
    assert not drill.has("left_ran")                          # a minted token, no accepted node
    blob = drill.everything(cp)
    assert "tskey-auth-kABCDEF123456789" not in blob and TOKEN not in blob
    cell = mesh_check.check_l8(drill.state)
    assert cell["ok"] is False and "join" in cell["reason"]
    assert res["w40"]["remote_control"] is None               # never reached


def test_a_failed_approve_after_accept_still_revokes_what_it_made(drill):
    drill.flag("approve_fails")
    assert drill.run().returncode == 1
    _failed(drill, "approve")
    assert drill.has("left_ran")                              # the host row exists: leave runs
    drill.left_nothing()
    assert not any("hq_join provision" in c for c in drill.calls())


def test_a_failed_provision_stops_the_pipeline_and_closes_the_door(drill):
    drill.flag("provision_fails")
    assert drill.run().returncode == 1
    _failed(drill, "provision")
    drill.left_nothing()
    assert "probe" not in [s["name"] for s in drill.result()["steps"]]


def test_a_failed_container_step_is_cleaned(drill):
    drill.flag("prep_fails")
    assert drill.run().returncode == 1
    _failed(drill, "container")
    drill.left_nothing()


def test_door_that_will_not_open_fails_door_open_and_is_closed_anyway(drill):
    drill.flag("door_open_fails")
    assert drill.run().returncode == 1
    _failed(drill, "door_open")
    assert "door close" in drill.calls()


def test_join_probe_failure_is_a_finding_and_a_failed_step_but_the_run_goes_on(drill):
    drill.flag("join_probe_fails")
    assert drill.run().returncode == 1
    res = _failed(drill, "node_probe")
    assert "node_probe_failed" in res["findings"]
    assert drill.step("provision")["ok"] and drill.step("token_worker")["ok"] and drill.step("probe")["ok"]


def test_read_only_deploy_key_fails_probe_as_a_named_finding_not_a_silent_pass(drill):
    drill.flag("probe_readonly")
    assert drill.run().returncode == 1
    res = _failed(drill, "probe")
    assert "deploy_key_read_only" in res["findings"] and "read-only" in drill.step("probe")["detail"]
    assert res["probe"]["sha"] == "" and drill.step("leave")["ok"]      # leave and cleanup still ran
    drill.left_nothing()
    assert drill.has("task_closed")


def test_origin_sha_that_is_not_the_nodes_commit_fails_the_probe_and_the_branch_is_deleted(drill):
    drill.flag("probe_wrong_sha")
    assert drill.run().returncode == 1
    _failed(drill, "probe")
    assert not drill.has("remote_branch")


def test_branch_that_cannot_be_deleted_fails_cleanup_and_names_the_branch(drill):
    drill.flag("branch_delete_fails")
    assert drill.run().returncode == 1
    res = _failed(drill, "cleanup")
    assert "agent/probe-task-0123abcd" in drill.step("cleanup")["detail"] and res["probe"]["sha"] == SHA


def test_token_worker_failure_is_a_step_and_remote_control_is_a_separate_answer(drill):
    drill.flag("tw_fails", "rc_refused")
    assert drill.run().returncode == 1
    res = _failed(drill, "token_worker")
    assert res["w40"]["remote_control"] is False
    assert res["w40"]["remote_control_error"].startswith("Error: Remote Control requires")
    assert "remote_control" not in [s["name"] for s in res["steps"]]    # never a pass criterion


def test_a_remote_control_refusal_alone_does_not_fail_the_drill(drill):
    drill.flag("rc_refused")
    assert drill.run().returncode == 0
    res = drill.result()
    assert res["ok"] is True and res["w40"]["remote_control"] is False


def test_leave_that_really_fails_is_not_excused_as_unwired(drill):
    drill.flag("leave_tailscale_fails", "leave_keeps_device")
    assert drill.run().returncode == 1
    leave = drill.step("leave")
    assert leave["ok"] is False and "exit 1" in leave["detail"]
    assert drill.step("verify_tailnet")["ok"] is False
    assert drill.result()["failed_step"] == "leave"


@pytest.mark.parametrize("flag,step", [("leave_keeps_device", "verify_tailnet"),
                                       ("leave_keeps_key", "verify_deploy_key"),
                                       ("leave_keeps_token", "verify_token_refused"),
                                       ("winbox_line", "verify_authorized_keys"),
                                       ("winbox_down", "verify_authorized_keys")])
def test_each_verify_fails_on_the_thing_it_checks(drill, flag, step):
    drill.flag(flag)
    assert drill.run().returncode == 1
    assert drill.step(step)["ok"] is False
    drill.left_nothing()


def test_an_authorized_keys_line_on_contabo_fails_the_verify(drill):
    drill.ak.write_text(f"ssh-ed25519 AAAA org-dispatch:{HOST}\n")
    assert drill.run().returncode == 1
    assert "contabo" in drill.step("verify_authorized_keys")["detail"]


def test_partial_leave_is_flagged_and_the_host_row_check_is_not_waved_through(drill):
    (drill.shim / "flags" / "leave_all_ok").unlink()          # what leave() does today: authorized_keys unwired
    assert drill.run().returncode == 1
    res = _failed(drill, "verify_host_row")
    assert drill.step("leave")["ok"] is True                   # the 3 real revocations were ok
    assert "leave_partial_authorized_keys_unwired" in res["findings"]
    assert "W2.8" in drill.step("verify_host_row")["detail"]
    drill.left_nothing()


def test_hub_that_will_not_record_fails_the_drill_and_leaves_the_file(drill):
    drill.flag("record_fails")
    assert drill.run().returncode == 1
    res = _failed(drill, "record")
    assert res["steps"][-1]["name"] == "record" and not drill.has("recorded.json")


def test_leave_without_the_flag_would_revoke_nothing_and_the_drill_would_say_so(drill):
    """The stub is the real tool: no ORG_W42_PROVISION=1, no revocation. Dropping the flag from the
    script's leave call must turn this drill red at leave, never leave the node's credentials behind
    unnoticed."""
    script = drill.root / "drill-noflag.sh"
    script.write_text(SCRIPT.read_text().replace('ORG_W42_PROVISION=1 "$PY" -m tools.hq_join leave',
                                                 '"$PY" -m tools.hq_join leave'))
    cp = subprocess.run(["/bin/bash", str(script)], env=drill.env, cwd=drill.root, capture_output=True, text=True)
    assert cp.returncode == 1
    res = _failed(drill, "leave")
    assert "tailscale_device" in drill.step("leave")["detail"] or "not ok" in drill.step("leave")["detail"]
    assert drill.step("verify_tailnet")["ok"] is False and drill.step("verify_deploy_key")["ok"] is False
    assert res["failed_step"] == "leave"
    # status_leaving is the hub's own write and needs no flag: the token is refused from the first step
    assert drill.step("verify_token_refused")["ok"] is True


def test_leave_runs_with_the_flag_and_removes_what_provision_made(drill):
    assert drill.run().returncode == 0
    leave = [c for c in drill.calls() if "hq_join leave" in c]
    assert len(leave) == 1 and "--live" in leave[0] and leave[0].endswith("[w42=1]")
    assert not drill.has("ts_device_present") and not drill.has("deploy_key_present")
    assert drill.read("row_status") == "left"


def test_real_github_read_only_message_is_recorded_as_the_finding(drill):
    drill.flag("probe_readonly_gh")                  # "marked as read only": no hyphen
    assert drill.run().returncode == 1
    res = _failed(drill, "probe")
    assert "deploy_key_read_only" in res["findings"]


def test_an_unreadable_winbox_keys_file_is_never_read_as_no_line(drill):
    drill.flag("winbox_unreadable")                  # findstr exits 1: no match AND cannot open
    assert drill.run().returncode == 1
    detail = drill.step("verify_authorized_keys")["detail"]
    assert drill.step("verify_authorized_keys")["ok"] is False and "not readable" in detail
    ssh_calls = [c for c in drill.calls() if c.startswith("ssh ")]
    assert len(ssh_calls) == 1 and "/C:ssh-" in ssh_calls[0]       # it never got to the host search


def test_winbox_is_searched_for_the_host_only_after_the_file_proved_readable(drill):
    assert drill.run().returncode == 0
    ssh_calls = [c for c in drill.calls() if c.startswith("ssh ")]
    assert len(ssh_calls) == 2 and "/C:ssh-" in ssh_calls[0] and f"/C:{HOST}" in ssh_calls[1]


def test_remote_control_keeps_the_first_output_line_masks_urls_and_never_fails_the_drill(drill):
    drill.flag("rc_prints_url")
    cp = drill.run()
    assert cp.returncode == 0
    w40 = drill.result()["w40"]
    assert w40["remote_control"] is True and w40["remote_control_error"] == ""
    assert w40["remote_control_output"] == "Remote Control ready: [url] connect from your phone"
    assert "claude.ai/code/session_" not in drill.everything(cp)


def test_remote_control_output_is_empty_when_it_printed_nothing_and_kept_when_it_exited(drill):
    assert drill.run().returncode == 0
    assert drill.result()["w40"]["remote_control_output"] == ""


def test_remote_control_refusal_is_kept_as_the_output_too(drill):
    drill.flag("rc_refused")
    assert drill.run().returncode == 0
    w40 = drill.result()["w40"]
    assert w40["remote_control"] is False
    assert w40["remote_control_output"] == w40["remote_control_error"].strip() and w40["remote_control_output"]


CLEAN_EXEC = re.compile(r"python3 -I -c '([^']+)' ")


@pytest.mark.parametrize("name", ["token_worker", "remote_control"])
def test_the_node_scripts_hold_no_token_on_any_command_line_and_give_claude_a_clean_env(drill, tmp_path, name):
    assert drill.run().returncode == 0
    text = (drill.shim / "scripts" / f"{name}.sh").read_text()        # what the node was told to run
    assert "CLAUDE_CODE_OAUTH_TOKEN=" not in text and "env -i" not in text
    snippet = CLEAN_EXEC.search(text)
    assert snippet, "the node script must build claude's environment inside python, not in argv"
    # run the real snippet: only PATH, HOME and the token reach the child, cwd /tmp, token not in argv
    fake = tmp_path / "fakebin"
    fake.mkdir()
    out = tmp_path / "claude.out"
    (fake / "fakeclaude").write_text(f'#!/bin/sh\n/usr/bin/env > "{out}"\npwd -P >> "{out}"\necho "ARGV:$*" >> "{out}"\n')
    (fake / "fakeclaude").chmod(0o755)
    value = "placeholder" + "-for-the-test"             # not a secret; built so no scanner reads it as one
    env = {"PATH": f"{fake}:/usr/bin:/bin", "HOME": "/home/someone", "CLAUDE_CODE_OAUTH_TOKEN": value,
           "ORG_DB_URL": "postgres://nope", "JUNK": "x"}
    cp = subprocess.run([sys.executable, "-I", "-c", snippet.group(1), "fakeclaude", "-p", "say it"], env=env,
                        cwd=tmp_path, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    seen = out.read_text()
    assert f"CLAUDE_CODE_OAUTH_TOKEN={value}" in seen and "HOME=/root" in seen
    assert "JUNK" not in seen and "ORG_DB_URL" not in seen and "/home/someone" not in seen
    assert seen.strip().splitlines()[-2].endswith("/tmp") and seen.strip().splitlines()[-1] == "ARGV:-p say it"
    assert value not in seen.split("ARGV:")[1]


def test_the_oauth_token_is_missing_loudly_not_silently(drill, tmp_path):
    snippet = CLEAN_EXEC.search(SCRIPT.read_text()).group(1)
    cp = subprocess.run([sys.executable, "-I", "-c", snippet, "true"], env={"PATH": "/usr/bin:/bin"},
                        cwd=tmp_path, capture_output=True, text=True)
    assert cp.returncode != 0 and "CLAUDE_CODE_OAUTH_TOKEN" in cp.stderr


# ------------------------------------------------------------------------------ refusals

def test_a_stale_checkout_without_join_drill_is_refused_before_anything_starts(drill):
    drill.mesh_check.write_text("# an older mesh_check: no such verb\n")
    cp = drill.run()
    assert cp.returncode == 2 and "stale" in cp.stderr and "--join-drill" in cp.stderr
    assert started_nothing(drill) and not (drill.state / "join-drill.json").exists()
    assert not any(c.startswith("docker") or c.startswith("door") for c in drill.calls())


def test_a_checkout_with_no_mesh_check_at_all_is_refused_too(drill):
    drill.mesh_check.unlink()
    assert drill.run().returncode == 2


def test_a_checkout_whose_join_api_has_no_check_db_is_refused_as_stale(drill):
    drill.join_api.write_text("# an older join_api: no such flag\n")
    cp = drill.run()
    assert cp.returncode == 2 and "stale" in cp.stderr and "--check-db" in cp.stderr
    assert started_nothing(drill) and not any(c.startswith("door") for c in drill.calls())


# ------------------------------------------------------------------------------ W4.2b: the token service

def test_the_join_dsn_is_checked_before_the_door_opens_and_never_printed(drill):
    drill.flag("dsn_stale")
    cp = drill.run()
    assert cp.returncode == 2 and "rotate with deploy/join/org_join_role.py" in cp.stderr
    assert any(c.startswith("py -m tools.join_api --check-db") for c in drill.calls())
    assert not any(c.startswith(("door open", "docker run")) for c in drill.calls())
    assert JOIN_DSN_PASSWORD not in drill.everything(cp) and "hub.example" not in drill.everything(cp)
    assert started_nothing(drill) and not (drill.state / "join-drill.json").exists()


def test_a_join_dsn_that_logs_in_lets_the_drill_go_on(drill):
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    calls = drill.calls()
    check = next(i for i, c in enumerate(calls) if "tools.join_api --check-db" in c)
    assert check < next(i for i, c in enumerate(calls) if c.startswith("door open"))
    assert "join DSN logs in, token service ready" in drill.step("preflight")["detail"]


def test_the_token_service_is_asked_for_health_before_the_door_opens(drill):
    assert drill.run().returncode == 0
    calls = drill.calls()
    health = next(i for i, c in enumerate(calls) if c.startswith("curl") and "8792/health" in c)
    assert health < next(i for i, c in enumerate(calls) if c.startswith("door open"))


def test_provision_is_given_the_token_url_and_makes_no_infisical_call(drill):
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert f"token_url={TOKEN_URL}" in drill.calls()
    assert not any("infisical" in c.lower() and "joinenv" not in c for c in drill.calls())


def test_the_token_url_is_asked_of_tailscale_when_nothing_sets_it(drill):
    drill.env.pop("DRILL_TOKEN_URL")
    cp = drill.run()
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "tailscale ip -4" in drill.calls() and f"token_url={TOKEN_URL}" in drill.calls()


def test_the_environment_url_is_taken_before_asking_tailscale(drill):
    drill.env.pop("DRILL_TOKEN_URL")
    drill.env["ORG_NODE_TOKEN_URL"] = TOKEN_URL
    assert drill.run().returncode == 0
    assert "tailscale ip -4" not in drill.calls()


def test_the_node_scripts_go_through_node_token_and_name_no_infisical(drill):
    assert drill.run().returncode == 0
    for name in ("token_worker", "remote_control"):
        text = (drill.shim / "scripts" / f"{name}.sh").read_text()
        assert "python3 -I -B tools/node_token.py run --" in text, name
        assert "infisical" not in text.lower() and "Org-Node" not in text and "--as" not in text, name


def test_the_script_has_one_infisical_call_the_org_join_leg_and_no_node_identity_left():
    text = SCRIPT.read_text()
    calls = [l for l in text.splitlines() if not l.lstrip().startswith("#") and "infisical_setup.py" in l]
    assert len(calls) == 1 and "JOIN_ENV=(" in calls[0] and "--path /org-join" in calls[0], calls
    for gone in ("setup.env", "node-secrets", "Org-Node prod --as", "CRED_DIR", "verify_infisical"):
        assert gone not in text, gone


def test_verify_token_refused_passes_on_403_left_and_reads_no_body_it_could_print(drill):
    cp = drill.run()
    assert cp.returncode == 0
    detail = drill.step("verify_token_refused")["detail"]
    assert "403 left" in detail and HOST in detail
    assert SEALED not in drill.everything(cp)


def test_a_hub_that_still_serves_the_host_after_leave_fails_and_the_sealed_body_is_never_shown(drill):
    drill.flag("leave_keeps_token")
    cp = drill.run()
    assert cp.returncode == 1
    step = drill.step("verify_token_refused")
    assert step["ok"] is False and "HTTP 200" in step["detail"]
    assert SEALED not in drill.everything(cp)


def test_a_token_service_that_goes_silent_is_never_read_as_a_refusal(drill):
    drill.flag("token_down")                       # up for /health at preflight, then no answer to /v1/token
    cp = drill.run()
    assert cp.returncode == 1
    step = drill.step("verify_token_refused")
    assert step["ok"] is False and "did not answer" in step["detail"]


def test_a_node_that_never_registered_is_refused_by_the_hub_and_that_passes(drill):
    drill.flag("join_dies")                        # the stub writes no hosts row
    assert drill.run().returncode == 1
    step = drill.step("verify_token_refused")
    assert step["ok"] is True and "never accepted" in step["detail"] and "unknown_host" in step["detail"]


def test_a_node_that_registered_but_was_never_accepted_is_refused_not_approved(drill):
    drill.flag("no_fingerprint")                   # the stub's row stays pending
    assert drill.run().returncode == 1
    step = drill.step("verify_token_refused")
    assert step["ok"] is True and "not_approved" in step["detail"]


def test_the_script_piped_in_is_refused_because_it_cannot_re_run_itself(drill):
    cp = subprocess.run(["/bin/bash", "-s"], input=SCRIPT.read_text(), env=drill.env, cwd=drill.root,
                        capture_output=True, text=True)
    assert cp.returncode == 2 and "re-runs itself" in cp.stderr
    assert drill.calls() == []

def test_memory_below_the_floor_refuses_with_exit_2_and_starts_nothing(drill):
    drill.put("avail_mb", "1200\n")
    cp = drill.run()
    assert cp.returncode == 2
    assert "1200" in cp.stderr and "1500" in cp.stderr
    assert started_nothing(drill) and not (drill.state / "join-drill.json").exists()
    assert not any(c.startswith("docker") or c.startswith("door") for c in drill.calls())


def test_memory_exactly_at_the_floor_runs(drill):
    drill.put("avail_mb", "1500\n")
    assert drill.run().returncode == 0


@pytest.mark.parametrize("setup,needle", [
    (lambda d: d.put("door", "open\n"), "door is not closed"),
    (lambda d: d.put("containers", "drill-20250101-000000\n"), "container named drill-"),
    (lambda d: d.put("volumes", "drill-20250101-000000-ts\n"), "volume named drill-"),
    (lambda d: d.put("hosts", "drill-20250101-000000  ready  linux  fingerprint abcd1234  -\n"), "not 'left'"),
    (lambda d: d.flag("no_ts_creds"), "TAILSCALE_OAUTH"),
    (lambda d: d.flag("ts_api_down"), "Tailscale API"),
    (lambda d: d.flag("gh_down"), "gh api"),
    (lambda d: d.flag("no_join_dsn"), "ORG_JOIN_DB_URL is not in this environment"),
    (lambda d: d.flag("dsn_stale"), "rotate with deploy/join/org_join_role.py"),
    (lambda d: d.flag("token_health_down"), "token service did not answer"),
    (lambda d: d.flag("token_not_loaded"), "token_loaded or db is not true"),
    (lambda d: d.env.update(DRILL_TOKEN_URL="http://100.64.0.9:8792/other"), "token URL must look like"),
    (lambda d: (d.env.pop("DRILL_TOKEN_URL"), d.flag("no_tailnet_address")), "no token URL"),
])
def test_preflight_refusals_start_nothing(drill, setup, needle):
    setup(drill)
    cp = drill.run()
    assert cp.returncode == 2 and needle in cp.stderr, cp.stderr
    assert started_nothing(drill)
    assert not (drill.state / "join-drill.json").exists() and not drill.has("recorded.json")


def test_a_left_drill_host_from_an_earlier_run_is_not_a_leftover(drill):
    drill.put("hosts", "drill-20250101-000000  left  linux  fingerprint abcd1234  approved x\n")
    assert drill.run().returncode == 0


def test_bad_arguments_exit_2(drill):
    assert drill.run("--nope").returncode == 2
    drill.env["DRILL_STAMP"] = "tomorrow"
    assert drill.run().returncode == 2


# ------------------------------------------------------------------------------ dry run

def test_dry_run_prints_every_step_and_touches_nothing(drill):
    before = sorted(str(p.relative_to(drill.root)) for p in drill.root.rglob("*"))
    cp = drill.run("--dry-run")
    assert cp.returncode == 0
    for name in STEP_NAMES:
        assert re.search(rf"^\s+{name}\s", cp.stdout, re.M), f"{name} missing from the dry run"
    assert HOST in cp.stdout
    assert drill.calls() == []                                # not one stub was called
    assert sorted(str(p.relative_to(drill.root)) for p in drill.root.rglob("*")) == before
    assert not drill.state.exists() and not drill.rows.exists()


def test_dry_run_with_log_to_repo_still_writes_nothing(drill):
    assert drill.run("--dry-run", "--log-to-repo").returncode == 0
    assert not drill.rows.exists() and drill.calls() == []


# ------------------------------------------------------------------------------ every exit path

@pytest.mark.parametrize("sig,code", [(signal.SIGTERM, 143), (signal.SIGINT, 130)])
def test_a_signal_mid_drill_closes_the_door_and_removes_the_container(drill, sig, code):
    drill.flag("join_hangs")                                   # join.sh never ends: provision waits
    drill.env["DRILL_JOIN_WAIT_S"] = "60"
    p = drill.popen()
    deadline = time.time() + 30
    while time.time() < deadline and not drill.has("provisioned"):
        time.sleep(0.1)
    assert drill.has("provisioned"), "the drill never reached the provision wait"
    p.send_signal(sig)
    out, err = p.communicate(timeout=60)
    assert p.returncode == code, out + err
    drill.left_nothing()
    res = drill.result()
    assert res["ok"] is False and drill.has("left_ran")
    assert "stopped by a signal" in drill.step("provision")["detail"]


# ------------------------------------------------------------------------------ the JSON itself

def test_details_are_one_ascii_line_with_secret_shapes_masked_and_the_json_stays_valid(drill):
    drill.flag("mint_fails")
    cp = drill.run()
    assert cp.returncode == 1
    raw = (drill.state / "join-drill.json").read_text()
    res = json.loads(raw)                                     # valid despite quote, backslash, control char
    detail = drill.step("mint")["detail"]
    assert "tskey-auth-kLEAK1234567890" not in raw + cp.stdout + cp.stderr and "[redacted]" in detail
    assert detail.isascii() and "\n" not in detail and len(detail) <= 200
    assert res["failed_step"] == "mint"
    drill.left_nothing()


def test_l8_goes_red_on_a_failed_drill_and_names_the_step(drill):
    drill.flag("probe_readonly")
    drill.run()
    cell = mesh_check.check_l8(drill.state)
    assert cell["ok"] is False and "kind" not in cell and "probe" in cell["reason"]
    at = datetime.fromisoformat(drill.result()["at"].replace("Z", "+00:00"))
    assert at.tzinfo is not None and abs((datetime.now(timezone.utc) - at).total_seconds()) < 600


# ------------------------------------------------------------------------------ which code ran (addendum 7-10)

REAL_GIT = shutil.which("git", path="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin")


def _venv(drill: Drill, where: Path, name: str) -> None:
    """A venv python for `where` that says which venv and which directory it ran in, then acts as the PY stub."""
    py = where / ".venv" / "bin" / "python3"
    py.parent.mkdir(parents=True)
    py.write_text(f'#!/bin/bash\necho "{name} $(pwd -P)" >>"$SHIM_STATE/venv.log"\nexec "{drill.bin}/py" "$@"\n')
    py.chmod(0o755)


def _venv_log(drill: Drill) -> list[tuple[str, str]]:
    return sorted({tuple(line.split(" ", 1)) for line in drill.read("venv.log").splitlines()})


def _repo(path: Path) -> str:
    """A real git repo with one commit; returns its short sha."""
    path.mkdir(parents=True, exist_ok=True)
    git = ["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@invalid"]
    subprocess.run([REAL_GIT, "init", "-q", str(path)], check=True, capture_output=True)
    (path / "tools").mkdir(exist_ok=True)
    (path / "tools" / "mesh_check.py").write_text("ap.add_argument('--join-drill', nargs=2)\n")
    (path / "tools" / "join_api.py").write_text("p.add_argument('--check-db', action='store_true')\n")
    subprocess.run([REAL_GIT, *git[1:], "add", "-A"], check=True, capture_output=True)
    subprocess.run([REAL_GIT, *git[1:], "commit", "-q", "-m", f"fixture {path.name}"], check=True, capture_output=True)
    return subprocess.run([REAL_GIT, "-C", str(path), "rev-parse", "--short", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.mark.skipif(REAL_GIT is None, reason="no git on this machine")
def test_core_is_the_git_top_level_of_the_directory_the_card_runs_in(drill, tmp_path):
    wt = tmp_path / "worktree-of-origin-main"
    wt_sha = _repo(wt)
    live_sha = _repo(drill.live)
    (wt / "sub" / "dir").mkdir(parents=True)
    _venv(drill, wt, "worktree")
    drill.put("real_git", REAL_GIT)                       # the script's rev-parse calls are the real ones
    del drill.env["DRILL_CORE"], drill.env["DRILL_PY"]    # nothing tells it where CORE is
    cp = subprocess.run(["/bin/bash", str(SCRIPT)], env=drill.env, cwd=wt / "sub" / "dir", capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    assert {where for _, where in _venv_log(drill)} == {str(wt.resolve())}      # it ran in the top level, not in sub/dir
    assert drill.result()["code"] == {"drill": wt_sha, "join_service": live_sha}
    assert f"code under test: {wt.resolve()} at {wt_sha}" in cp.stdout
    assert f"drill {wt_sha}, join service {live_sha}" in drill.step("preflight")["detail"]


def test_with_no_git_checkout_around_core_falls_back_to_the_live_checkout(drill):
    del drill.env["DRILL_CORE"]                           # the stub git has no top level: the card ran outside any repo
    cp = drill.run()
    assert cp.returncode == 2 and f"the checkout at {drill.live} is stale" in cp.stderr    # the live stand-in has no tool
    assert started_nothing(drill)


@pytest.mark.parametrize("core_has_venv", [True, False])
def test_python_is_the_cores_venv_when_it_has_one_else_the_live_venv(drill, core_has_venv):
    _venv(drill, drill.live, "live")
    if core_has_venv:
        _venv(drill, drill.core, "core")
    del drill.env["DRILL_PY"]
    assert drill.run().returncode == 0
    want = ("core", str(drill.core.resolve())) if core_has_venv else ("live", str(drill.core.resolve()))
    assert _venv_log(drill) == [want]      # one venv only, and every call ran with the checkout under test as cwd


def test_drill_py_still_wins_over_both_venvs(drill):
    _venv(drill, drill.live, "live")
    _venv(drill, drill.core, "core")
    assert drill.run().returncode == 0                    # DRILL_PY (the stub) is still in the environment
    assert not drill.has("venv.log")


def test_both_code_commits_are_in_the_json_and_printed_at_preflight(drill):
    cp = drill.run()
    assert cp.returncode == 0
    assert drill.result()["code"] == {"drill": "c-core", "join_service": "c-live"}      # git stub: "c-" + directory name
    assert "drill c-core" in cp.stdout and "join service c-live" in cp.stdout
    assert any("live checkout at c-live" in n and "c-core" in n for n in drill.result()["notes"])


def test_no_note_when_the_drill_runs_in_the_live_checkout_itself(drill):
    drill.env["DRILL_LIVE_CORE"] = str(drill.core)
    assert drill.run().returncode == 0
    code = drill.result()["code"]
    assert code["drill"] == code["join_service"] == "c-core"
    assert not any("live checkout" in n for n in drill.result()["notes"])


def test_the_code_keys_are_there_even_when_git_cannot_name_a_commit(drill):
    drill.flag("no_git_here")
    assert drill.run().returncode == 0
    assert drill.result()["code"] == {"drill": "unknown", "join_service": "unknown"}


def test_a_refused_run_writes_no_code_record(drill):
    drill.mesh_check.write_text("")
    assert drill.run().returncode == 2
    assert not (drill.state / "join-drill.json").exists()


def test_the_dry_run_says_which_checkout_and_that_both_commits_are_recorded(drill):
    out = drill.run("--dry-run").stdout
    assert str(drill.core) in out and str(drill.live) in out and "code.drill" in out and "code.join_service" in out
