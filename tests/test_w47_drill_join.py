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
NODE_FP, HUB_FP = "abcd1234", "zzzz9999"            # the node prints the first; `status` shows the second
SECRETS = (TOKEN, TS_ID, TS_SECRET, TS_ACCESS)
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

WRAP = r'''#!/bin/bash
echo "wrap $*" >>"$SHIM_STATE/calls.log"
if [ ! -e "$SHIM_STATE/flags/no_ts_creds" ]; then
  export TAILSCALE_OAUTH_CLIENT_ID=ts-client-id-test TAILSCALE_OAUTH_CLIENT_SECRET=ts-client-secret-test-0123456789
fi
exec "$@"
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
    exit 124 ;;
  "sh /tmp/probe.sh"*)
    f probe_readonly && { echo "ERROR: The key you are using is read-only."; echo "fatal: Could not read from remote repository."; exit 6; }
    f probe_wrong_sha && { echo "sha=1111111111111111111111111111111111111111"; echo "$SHA" >"$S/remote_branch"; exit 0; }
    echo "$SHA" >"$S/remote_branch"; echo "sha=$SHA"; exit 0 ;;
esac
echo "stub docker exec: unexpected: $joined" >&2; exit 99
'''.replace("$FP", NODE_FP).replace("$SHA", SHA)

PY = PRELUDE + r'''
echo "py $* [w42=${ORG_W42_PROVISION:-unset}]" >>"$S/calls.log"
if [ "$1" != "-m" ]; then                           # tools/infisical_setup.py node-secrets
  [ "$2" = node-secrets ] || exit 99
  f node_secrets_down && { echo "infisical: login failed" >&2; exit 1; }
  if [ -e "$S/secret_live" ]; then echo "org-node:$H · id1 · created 2026-10-03T14:00:00Z · live"
  elif [ -e "$S/secret_revoked" ]; then echo "org-node:$H · id1 · created 2026-10-03T14:00:00Z · REVOKED"
  else echo "no client secrets under org-node"; fi
  exit 0
fi
mod=$2; verb=$3; shift 3
case "$mod $verb" in
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
    f provision_fails && { echo "hq_join: failed (ApiError): infisical 403" >&2; exit 1; }
    : >"$S/provisioned"; : >"$S/ts_device_present"; : >"$S/deploy_key_present"; : >"$S/secret_live"; echo ready >"$S/row_status"
    echo '{"ok": true}'; exit 0 ;;
  "tools.hq_join leave")
    : >"$S/left_ran"
    f leave_keeps_device || rm -f "$S/ts_device_present"
    f leave_keeps_key || rm -f "$S/deploy_key_present"
    f leave_keeps_secret || { rm -f "$S/secret_live"; : >"$S/secret_revoked"; }
    if f leave_tailscale_fails; then
      echo "  [ok] infisical_client_secret on $H"
      echo "  [FAILED] tailscale_device on $H: TailscaleError: boom"
      echo "  [ok] github_deploy_key on $H"
      echo "hq_join: $H NOT marked left; left behind: tailscale_device:$H"; exit 1
    fi
    echo "  [ok] infisical_client_secret on $H"; echo "  [ok] tailscale_device on $H"; echo "  [ok] github_deploy_key on $H"
    if f leave_all_ok; then
      for t in mac contabo winbox; do echo "  [ok] authorized_keys on $t"; done
      echo left >"$S/row_status"; echo "hq_join: $H is now \`left\`"; exit 0
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
  *ls-remote*) [ -e "$S/remote_branch" ] && printf '%s\t%s\n' "$(cat "$S/remote_branch")" "refs/heads/agent/probe-task-0123abcd" ;;
  *"push -q origin --delete"*) f branch_delete_fails && { echo "remote: Permission denied" >&2; exit 1; }; rm -f "$S/remote_branch" ;;
  *) echo "stub git: unexpected $*" >&2; exit 99 ;;
esac
exit 0
'''

SSH = PRELUDE + r'''
echo "ssh $*" >>"$S/calls.log"
f winbox_down && exit 255
f winbox_line && exit 0
exit 1
'''

STUBS = {"free": FREE, "docker": DOCKER, "curl": CURL, "gh": GH, "git": GIT, "ssh": SSH}


class Drill:
    """One tmp_path world for the script: stubs, a core checkout, a state dir, a state shim."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        self.shim = tmp_path / "shim"
        (self.shim / "flags").mkdir(parents=True)
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        self.core = tmp_path / "core"
        (self.core / "state").mkdir(parents=True)
        self.state = tmp_path / "out" / "mesh-check"
        self.rows = self.core / "state" / "re-os-drills.jsonl"
        self.cred = tmp_path / "cred"
        self.cred.mkdir()
        (self.cred / "setup.env").write_text("admin identity placeholder\n")
        self.ak = tmp_path / "authorized_keys"
        self.ak.write_text("ssh-ed25519 AAAA placeholder org-dispatch:mac\n")
        for name, body in {**STUBS, "py": PY, "door.sh": DOOR, "wrap.sh": WRAP}.items():
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
            "DRILL_STATE_DIR": str(self.state),
            "DRILL_ROWS_FILE": str(self.rows),
            "DRILL_PY": str(self.bin / "py"),
            "DRILL_DOOR": str(self.bin / "door.sh"),
            "DRILL_HUB_WRAP": str(self.bin / "wrap.sh"),
            "DRILL_AUTHORIZED_KEYS": str(self.ak),
            "DRILL_ALLOW_NONROOT": "1",
            "DRILL_POLL_S": "0.1",
            "DRILL_FP_WAIT_S": "2",
            "DRILL_JOIN_WAIT_S": "3",
            "DRILL_PROBE_WAIT_S": "20",
            "INFISICAL_CRED_DIR": str(self.cred),
        }

    def flag(self, *names: str) -> "Drill":
        for n in names:
            (self.shim / "flags" / n).touch()
        return self

    def put(self, name: str, text: str) -> "Drill":
        (self.shim / name).write_text(text)
        return self

    def popen(self, *args: str) -> subprocess.Popen:
        return subprocess.Popen(["/bin/bash", str(SCRIPT), *args], env=self.env, cwd=self.root,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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


def test_the_fingerprint_comes_from_the_node_and_the_flag_is_set_only_for_provision(drill):
    cp = drill.run()
    assert cp.returncode == 0
    approve = [c for c in drill.calls() if "hq_join approve" in c]
    assert len(approve) == 1 and f"--fingerprint {NODE_FP}" in approve[0] and HUB_FP not in approve[0]
    with_flag = [c for c in drill.calls() if c.startswith("py ") and "[w42=1]" in c]
    assert len(with_flag) == 1 and "hq_join provision" in with_flag[0]
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
    assert calls[0].startswith("wrap ")                       # re-exec through with-org-db-env.sh
    closes = [i for i, c in enumerate(calls) if c == "door close"]
    task = next(i for i, c in enumerate(calls) if "--join-drill task-create" in c)
    assert closes and closes[0] < task                        # the public endpoint is shut after the join


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
                                       ("leave_keeps_secret", "verify_infisical"),
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


# ------------------------------------------------------------------------------ refusals

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
    (lambda d: (d.cred / "setup.env").unlink(), "setup.env"),
    (lambda d: d.flag("no_ts_creds"), "TAILSCALE_OAUTH"),
    (lambda d: d.flag("ts_api_down"), "Tailscale API"),
    (lambda d: d.flag("gh_down"), "gh api"),
    (lambda d: d.flag("node_secrets_down"), "node-secrets"),
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
