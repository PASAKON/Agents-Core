#!/usr/bin/env bash
# drill-join.sh - Org Mesh W4.7, the join drill. Run as root on Contabo, from a checkout of
# origin/main (the live /opt/MoonieXHQ/Agents/Core, or a worktree the card names with --cwd), as ONE
# Run Inbox card (docs/ops/join-drill.md has the card lines).
# The CEO's tap on that card is the human approval of the throwaway node: nothing else is typed.
#
#   bash scripts/drill-join.sh [--dry-run] [--log-to-repo]
#
#   --dry-run       print every step and touch nothing: no door, no docker, no hub write, no API
#   --log-to-repo   also append the state/re-os-drills.jsonl row to the repo file (default: print it)
#
# What one run does (the step names are the names in join-drill.json, mesh_check L8 reads them):
#   preflight        refuse (exit 2, nothing started) unless the box can carry the drill
#   door_open        open the hub's join door for the drill only; a trap closes it on every exit
#   container        ubuntu:24.04, tailscaled in userspace networking, state in a volume
#   mint             `hq_join mint` a one-use token for drill-<stamp>
#   join             the one command a new machine runs; the fingerprint is read from the NODE
#   approve          `hq_join approve` with that fingerprint
#   provision        `hq_join provision`; the node takes its sealed identity; node_probe = join.sh's own
#   token_worker     the node answers a nonce through `claude -p` with only CLAUDE_CODE_OAUTH_TOKEN (W4.0)
#   probe            a probe task for the node completes: its commit is on origin on the task's branch
#   leave            `hq_join leave --live`, then verify_* each thing it should have removed
#   cleanup          branch, task, container, volume and door; JSON, event row and jsonl row written
# A failed step still runs leave, the verifies and cleanup, and writes ok=false naming the step.
#
# Exit: 0 pass, 1 the drill ran and failed, 2 refused (nothing started, nothing written).
#
# No secret is printed, put in argv, in the JSON or on disk. The join token lives in one shell
# variable and reaches the container by `docker exec -e ORG_JOIN_TOKEN` (environment, not argv).
# No `set -x`. Every detail string is cut to one printable-ASCII line with token shapes masked.
#
# Overrides (tests and odd boxes; every one has a default that is right on Contabo):
#   DRILL_CORE DRILL_LIVE_CORE DRILL_STATE_DIR DRILL_ROWS_FILE DRILL_PY DRILL_DOOR DRILL_HUB_WRAP DRILL_JOIN_URL
#   DRILL_IMAGE DRILL_MIN_MB DRILL_CONTAINER_MB DRILL_DOOR_MIN DRILL_FP_WAIT_S DRILL_JOIN_WAIT_S
#   DRILL_PROBE_WAIT_S DRILL_POLL_S DRILL_GH_REPO DRILL_AUTHORIZED_KEYS DRILL_WINBOX_SSH
#   DRILL_TS_API DRILL_STAMP DRILL_ALLOW_NONROOT INFISICAL_CRED_DIR
set -uo pipefail

STEP_NAMES="preflight door_open container mint join approve provision node_probe token_worker probe leave verify_tailnet verify_deploy_key verify_infisical verify_host_row verify_authorized_keys cleanup"

SELF=""                                         # stays empty when the script is piped in: no file to re-run
[ -n "${BASH_SOURCE[0]:-}" ] && SELF=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")
# LIVE_CORE is what deploy/join/org-join.service runs: the join API, and door.sh's own approve leg, run its
# code whatever checkout this script runs in. CORE is the code under test: the checkout the card runs in
# (a detached worktree of origin/main when the live checkout is behind), else the live one.
LIVE_CORE=${DRILL_LIVE_CORE:-/opt/MoonieXHQ/Agents/Core}
CORE=${DRILL_CORE:-$(git rev-parse --show-toplevel 2>/dev/null || echo "$LIVE_CORE")}
STATE_DIR=${DRILL_STATE_DIR:-$CORE/state/mesh-check}
ROWS_FILE=${DRILL_ROWS_FILE:-$CORE/state/re-os-drills.jsonl}
# A fresh worktree has no .venv: borrow the live one. The tools still load from $CORE, because the
# script changes into $CORE and runs `python -m`.
if [ -n "${DRILL_PY:-}" ]; then PY=$DRILL_PY
elif [ -f "$CORE/.venv/bin/python3" ]; then PY=$CORE/.venv/bin/python3
else PY=$LIVE_CORE/.venv/bin/python3
fi
DOOR=${DRILL_DOOR:-$CORE/deploy/join/door.sh}
HUB_WRAP=${DRILL_HUB_WRAP:-$CORE/scripts/hub/with-org-db-env.sh}
JOIN_URL=${DRILL_JOIN_URL:-https://webhook.mooniex.com/org-join/join.sh}
IMAGE=${DRILL_IMAGE:-ubuntu:24.04}
MIN_MB=${DRILL_MIN_MB:-1500}
CONTAINER_MB=${DRILL_CONTAINER_MB:-1200}
DOOR_MIN=${DRILL_DOOR_MIN:-30}
FP_WAIT_S=${DRILL_FP_WAIT_S:-420}
JOIN_WAIT_S=${DRILL_JOIN_WAIT_S:-900}
PROBE_WAIT_S=${DRILL_PROBE_WAIT_S:-900}
POLL_S=${DRILL_POLL_S:-5}
GH_REPO=${DRILL_GH_REPO:-PASAKON/Agents-Core}
AK_FILE=${DRILL_AUTHORIZED_KEYS:-/root/.ssh/authorized_keys}
WINBOX_SSH=${DRILL_WINBOX_SSH:-winbox}
TS_API=${DRILL_TS_API:-https://api.tailscale.com}
CRED_DIR=${INFISICAL_CRED_DIR:-/etc/infisical}
STAMP=${DRILL_STAMP:-$(date -u +%Y%m%d-%H%M%S)}
HOST=drill-$STAMP
C_CONF=/root/.config/mooniex                  # inside the container: join.sh runs there as root
C_CORE=/opt/MoonieXHQ/Agents/Core             # where join.sh clones as root

DRY=0
LOG_TO_REPO=${DRILL_LOG_TO_REPO:-0}               # the re-exec below hands the flag over by env: the loop shifted "$@" away
TOKEN=""
FP=""
WORK=""
STEPS=""; NOTES=""; FINDINGS=""
CUR_STEP=preflight
FINISHED=0
STARTED=$SECONDS
T_JOINED=""
T_PROBE=""
DOOR_OPENED=0
CONTAINER=""
VOLUME=""
MINTED=0
ACCEPTED=0
LEAVE_PARTIAL=0
TASK_ID=""
BRANCH=""
PROBE_SHA=""
PROBE_SECS=""
RC_STATE=null
RC_ERR=""
RC_OUT=""
RC_CMD="claude remote-control"
PREFLIGHT_DETAIL=""
CODE_DRILL=""; CODE_JOIN=""                     # the two commits that ran, set by code_commits

# Short commit of a checkout, "unknown" when it is not a git checkout.
code_rev() { git -C "$1" rev-parse --short HEAD 2>/dev/null || printf unknown; }
code_commits() { CODE_DRILL=$(code_rev "$CORE"); CODE_JOIN=$(code_rev "$LIVE_CORE"); }

say() { printf 'drill: %s\n' "$*"; }
refuse() { printf 'drill: REFUSED: %s\n' "$*" >&2; exit 2; }

usage() { sed -n '2,/^set -uo/p' "$SELF" | sed -e '$d' -e 's/^# \{0,1\}//'; }

# ------------------------------------------------------------------------------------ arguments
while [ $# -gt 0 ]; do
  case $1 in
    --dry-run) DRY=1 ;;
    --log-to-repo) LOG_TO_REPO=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'drill: unknown argument %s (try --help)\n' "$1" >&2; exit 2 ;;
  esac
  shift
done
case $STAMP in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]) ;;
  *) printf 'drill: DRILL_STAMP must look like 20261003-140000\n' >&2; exit 2 ;;
esac

# ------------------------------------------------------------------------------------ dry run
if [ "$DRY" -eq 1 ]; then
  cat <<EOF
drill: DRY RUN for $HOST. Nothing below is run: no door, no docker, no hub write, no API call.
  preflight        root; free -m available >= $MIN_MB MB else exit 2; docker, curl, gh, git, perl;
                   door status is "closed"; no container, volume or non-left host named drill-*;
                   $CRED_DIR/setup.env exists (provision needs the admin identity);
                   TAILSCALE_OAUTH_CLIENT_ID/_SECRET set; the Tailscale, gh and node-secrets readers answer;
                   tools/mesh_check.py has --join-drill. Code under test = this checkout ($CORE, venv from
                   $PY); the join API and door.sh approve run $LIVE_CORE. Both commits are printed and
                   written to the JSON as code.drill / code.join_service
  door_open        bash $DOOR open --minutes $DOOR_MIN        (trap closes it on every exit path)
  container        docker run $IMAGE --hostname $HOST --memory ${CONTAINER_MB}m, volume $HOST-ts, tailscaled --tun=userspace-networking
  mint             python -m tools.hq_join mint --host $HOST
  join             in the container: curl -fsSL $JOIN_URL, sh join.sh --host $HOST (token by env); fingerprint read from the node's output
  approve          python -m tools.hq_join approve --host $HOST --fingerprint <the 8 chars the node printed>
  provision        ORG_W42_PROVISION=1 python -m tools.hq_join provision --host $HOST; wait for join.sh to end (<= ${JOIN_WAIT_S}s)
  node_probe       join.sh's own step 9 must have passed (exit 0)
  token_worker     node: infisical run Org-Node prod --as $HOST -- python3 -I -c <exec with a clean env> claude -p <nonce>
                   (the token reaches claude by environment only, never on a command line)
                   question (not a pass criterion, key "w40"): does \`$RC_CMD\` start on that token alone?
                   its first output line is kept as w40.remote_control_output
  probe            hub: probe task for $HOST (pending); node: commit + push agent/probe-<task> within ${PROBE_WAIT_S}s;
                   hub: git ls-remote shows the same sha. Never merged. The branch is deleted at cleanup.
  leave            ORG_W42_PROVISION=1 python -m tools.hq_join leave --host $HOST --live (authorized_keys "not wired yet" is the only accepted failure)
  verify_tailnet   Tailscale API: no device named $HOST
  verify_deploy_key  gh api repos/$GH_REPO/keys: no key titled org-node:$HOST
  verify_infisical node-secrets: no live client secret org-node:$HOST
  verify_host_row  hq_join status --host $HOST: row is "left"
  verify_authorized_keys  no line naming $HOST in $AK_FILE (contabo) or on winbox; mac skipped until G2
  cleanup          origin branch deleted, task cancelled, container + volume removed, door closed;
                   writes $STATE_DIR/join-drill.json, a join_drill events row, prints the re-os-drills row
EOF
  exit 0
fi

# ------------------------------------------------------------------------------------ re-exec
# The hub URL and the Agents-Core prod secrets (Tailscale OAuth, gh) reach this process through the
# same wrapper every Contabo consumer uses; never a .env.
if [ "${DRILL_HUB_ENV:-}" != 1 ]; then
  if [ ! -f "$SELF" ] || [ ! -r "$SELF" ]; then
    refuse "cannot read this script as a file ($SELF): the drill re-runs itself, run it from a file, not a pipe"
  fi
  [ -x "$HUB_WRAP" ] || refuse "$HUB_WRAP is not executable: the drill needs the hub environment"
  DRILL_HUB_ENV=1 DRILL_LOG_TO_REPO=$LOG_TO_REPO exec "$HUB_WRAP" bash "$SELF"
fi
cd "$CORE" 2>/dev/null || refuse "no checkout at $CORE"

# ------------------------------------------------------------------------------------ text helpers
# One printable-ASCII line, the join token masked wherever it appears, token shapes masked, 200 chars.
scrub() {
  sed -E -e 's#tskey-[A-Za-z0-9_-]+#[redacted]#g' -e 's#sk-ant-[A-Za-z0-9_-]+#[redacted]#g' \
         -e 's#AGE-SECRET-KEY-[A-Z0-9]+#[redacted]#g' -e 's#(ghp|gho|ghs|github_pat)_[A-Za-z0-9_]+#[redacted]#g' \
         -e 's#([Bb]earer|[Tt]oken|[Ss]ecret|[Pp]assword)[=: ]+[A-Za-z0-9._~+=-]{16,}#\1 [redacted]#g'
}
clean() {
  local s
  s=$(LC_ALL=C tr '\n\t\r' '   ' | LC_ALL=C tr -cd '\040-\176')
  [ -n "$TOKEN" ] && s=${s//"$TOKEN"/[token]}
  printf '%s' "$s" | scrub | sed -E 's/^ +//; s/ +$//' | cut -c1-200
}
jstr() { printf '"%s"' "$(printf '%s' "$1" | clean | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"; }
first_line() { LC_ALL=C tr -d '\r' | sed -n '/[^[:space:]]/{p;q;}'; }
minutes() { echo $(( ($1 + 30) / 60 )); }

rec() { printf '%s\t%s\t%s\n' "$1" "$2" "$(printf '%s' "${3:-}" | clean)" >>"$STEPS"; }
step_ok() { rec "$1" 1 "${2:-}"; say "$1: ok${2:+ ($(printf '%s' "$2" | clean))}"; }
step_fail() { rec "$1" 0 "${2:-}"; say "$1: FAILED ($(printf '%s' "${2:-}" | clean))"; return 1; }
note() { printf '%s\n' "$(printf '%s' "$1" | clean)" >>"$NOTES"; }
finding() { printf '%s\n' "$1" >>"$FINDINGS"; }

run_limited() { local secs=$1; shift; perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$secs" "$@"; }

# Run a script (stdin) in the container: c_run <name> <seconds> [args...]. Output -> $WORK/<name>.out.
# rc 97 = could not copy the script in, 142 = timed out.
c_run() {
  local name=$1 secs=$2
  shift 2
  docker exec -i "$CONTAINER" sh -c "cat > /tmp/$name.sh" || return 97
  run_limited "$secs" docker exec "$CONTAINER" sh "/tmp/$name.sh" "$@" >"$WORK/$name.out" 2>&1
}
c_cat() { docker exec "$CONTAINER" cat "$1" 2>/dev/null; }

# ------------------------------------------------------------------------------------ readers
# Each answers 0 (yes), 1 (no) or 2 (could not read). A reader that cannot read is never "no".

ts_curl() { # ts_curl <path>: a GET with a bearer token read from stdin, never in argv
  local tok
  tok=$(printf 'client_id=%s&client_secret=%s&grant_type=client_credentials' \
          "${TAILSCALE_OAUTH_CLIENT_ID:-}" "${TAILSCALE_OAUTH_CLIENT_SECRET:-}" \
        | curl -fsS --max-time 30 -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
            --data-binary @- "$TS_API/api/v2/oauth/token" 2>/dev/null \
        | sed -n 's/.*"access_token" *: *"\([^"]*\)".*/\1/p') || return 2
  [ -n "$tok" ] || return 2
  printf 'Authorization: Bearer %s\n' "$tok" | curl -fsS --max-time 30 -H @- "$TS_API$1" 2>/dev/null
}
tailnet_has_device() {
  local out
  out=$(ts_curl /api/v2/tailnet/-/devices) || return 2
  printf '%s' "$out" | grep -q '"devices"' || return 2
  printf '%s' "$out" | grep -Eq "\"hostname\" *: *\"$HOST\""
}
deploy_key_present() {
  local out
  out=$(gh api --paginate "repos/$GH_REPO/keys" 2>/dev/null) || return 2
  printf '%s' "$out" | grep -Fq -- "\"org-node:$HOST\""
}
infisical_live_secret() {
  local out
  out=$("$PY" "$CORE/tools/infisical_setup.py" node-secrets 2>/dev/null) || return 2
  printf '%s\n' "$out" | grep -F -- "org-node:$HOST " | grep -Eq ' live$'
}
host_row_status() { "$PY" -m tools.hq_join status --host "$HOST" 2>/dev/null | awk -v h="$HOST" '$1 == h {print $2; exit}'; }
door_state() { bash "$DOOR" status 2>/dev/null | first_line; }

# ------------------------------------------------------------------------------------ 0 preflight
preflight() {
  [ "$(id -u)" = 0 ] || [ "${DRILL_ALLOW_NONROOT:-}" = 1 ] || refuse "run as root on Contabo"
  # The card runs this script at a pushed sha, but the tools it drives come from this checkout.
  # A stale checkout would get through the door, the join and the provision before it failed.
  grep -q -- '--join-drill' "$CORE/tools/mesh_check.py" 2>/dev/null \
    || refuse "the checkout at $CORE is stale: tools/mesh_check.py has no --join-drill (or this is not an Agents-Core checkout); update it (git pull) or run the card with --cwd in a worktree of origin/main"
  code_commits
  command -v free >/dev/null 2>&1 || refuse "no free(1): this drill runs on Contabo (Linux)"
  local avail c d st
  avail=$(free -m | awk '/^Mem:/ {print $7}')
  case $avail in ''|*[!0-9]*) refuse "could not read available memory from free -m" ;; esac
  [ "$avail" -ge "$MIN_MB" ] \
    || refuse "only $avail MB memory available, need $MIN_MB: Contabo runs one render at a time, wait and run again"
  for c in docker curl gh git perl; do command -v "$c" >/dev/null 2>&1 || refuse "$c is not installed"; done
  [ -f "$DOOR" ] || refuse "no door script at $DOOR"
  docker ps -a >/dev/null 2>&1 || refuse "docker does not answer"
  d=$(door_state)
  [ "$d" = closed ] || refuse "the join door is not closed (status: ${d:-no answer}); someone may be using it, run again when it is closed"
  [ -z "$(docker ps -a --filter name=drill- --format '{{.Names}}' 2>/dev/null)" ] \
    || refuse "a container named drill-* exists: remove it (docker rm -f) first"
  [ -z "$(docker volume ls -q --filter name=drill- 2>/dev/null)" ] \
    || refuse "a volume named drill-* exists: remove it (docker volume rm) first"
  st=$("$PY" -m tools.hq_join status 2>/dev/null) || refuse "hq_join status failed: no hub or no .venv ($PY)"
  printf '%s\n' "$st" | awk '$1 ~ /^drill-/ && $2 != "left" {bad=1} END {exit bad}' \
    || refuse "a host named drill-* is not 'left' in the hub: run hq_join leave --live for it first"
  [ -e "$CRED_DIR/setup.env" ] \
    || refuse "no $CRED_DIR/setup.env: provision needs the Infisical admin identity, and this box does not hold it"
  { [ -n "${TAILSCALE_OAUTH_CLIENT_ID:-}" ] && [ -n "${TAILSCALE_OAUTH_CLIENT_SECRET:-}" ]; } \
    || refuse "TAILSCALE_OAUTH_CLIENT_ID / _SECRET are not in this environment: provision and leave need them"
  # The readers the end of the drill relies on must work NOW, or the drill would join a node it
  # cannot then prove gone.
  tailnet_has_device; [ $? -eq 2 ] && refuse "the Tailscale API did not answer (token or device list)"
  deploy_key_present; [ $? -eq 2 ] && refuse "gh api repos/$GH_REPO/keys failed: gh has no access to the deploy keys"
  infisical_live_secret; [ $? -eq 2 ] && refuse "infisical_setup.py node-secrets failed: no admin read of org-node client secrets"
  PREFLIGHT_DETAIL="$avail MB available, door closed, no drill-* leftovers; code: drill $CODE_DRILL, join service $CODE_JOIN"
}

# ------------------------------------------------------------------------------------ 1 door
close_door() {
  [ "$DOOR_OPENED" -eq 1 ] || return 0
  bash "$DOOR" close >/dev/null 2>&1 && DOOR_OPENED=0
}
step_door_open() {
  CUR_STEP=door_open
  DOOR_OPENED=1                                 # set first: a half-open door is closed too
  bash "$DOOR" open --minutes "$DOOR_MIN" >"$WORK/door.out" 2>&1 \
    || step_fail door_open "door.sh open failed: $(first_line <"$WORK/door.out")" || return 1
  step_ok door_open "$(first_line <"$WORK/door.out")"
}

# ------------------------------------------------------------------------------------ 2 container
step_container() {
  CUR_STEP=container
  VOLUME=$HOST-ts
  CONTAINER=$HOST
  docker volume create "$VOLUME" >/dev/null 2>"$WORK/c.err" \
    || step_fail container "docker volume create: $(first_line <"$WORK/c.err")" || return 1
  docker run -d --name "$CONTAINER" --hostname "$HOST" --memory "${CONTAINER_MB}m" \
      --memory-swap "${CONTAINER_MB}m" --cpus 1.5 -v "$VOLUME:/var/lib/tailscale" \
      "$IMAGE" sleep infinity >/dev/null 2>"$WORK/c.err" \
    || step_fail container "docker run: $(first_line <"$WORK/c.err")" || return 1
  docker exec "$CONTAINER" sh -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates >/dev/null' \
      >"$WORK/c.out" 2>&1 \
    || step_fail container "installing curl in the container failed: $(tail -n 1 "$WORK/c.out")" || return 1
  # join.sh installs tailscale (step 4) and runs `tailscale up` (step 6); it never starts the daemon.
  docker exec -d "$CONTAINER" sh -c 'while ! command -v tailscaled >/dev/null 2>&1; do sleep 2; done; mkdir -p /var/run/tailscale /var/lib/tailscale; exec tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock >/tmp/tailscaled.log 2>&1' \
    || step_fail container "could not start the tailscaled loop" || return 1
  step_ok container "$IMAGE as $HOST, ${CONTAINER_MB} MB, userspace tailscaled"
}

# ------------------------------------------------------------------------------------ 3 mint + join
step_mint() {
  CUR_STEP=mint
  local rc
  TOKEN=$("$PY" -m tools.hq_join mint --host "$HOST" --ttl-min 20 2>"$WORK/mint.err")
  rc=$?
  case $TOKEN in ''|*[[:space:]]*) TOKEN=""; rc=1 ;; esac
  [ $rc -eq 0 ] || step_fail mint "hq_join mint failed: $(first_line <"$WORK/mint.err")" || return 1
  MINTED=1
  step_ok mint "token minted (value not shown)"
}

step_join() {
  CUR_STEP="join"
  ORG_JOIN_TOKEN=$TOKEN docker exec -d -e ORG_JOIN_TOKEN "$CONTAINER" sh -c \
    'curl -fsSL "$1" -o /tmp/join.sh || { echo "join: could not fetch $1" >/tmp/join.log; echo 1 >/tmp/join.rc; exit 0; }
     sh /tmp/join.sh --host "$2" >/tmp/join.log 2>&1 </dev/null; echo $? >/tmp/join.rc' sh "$JOIN_URL" "$HOST" \
    || step_fail join "could not start join.sh in the container" || return 1
  local until=$((SECONDS + FP_WAIT_S)) fp="" rc
  while [ "$SECONDS" -lt "$until" ]; do
    fp=$(c_cat /tmp/join.log | sed -n 's/.*fingerprint: \([a-z0-9]\{8\}\)[^a-z0-9].*/\1/p' | head -n 1)
    [ -n "$fp" ] && break
    rc=$(c_cat /tmp/join.rc | first_line)
    [ -z "$rc" ] || step_fail join "join.sh ended (exit $rc) before printing a fingerprint: $(c_cat /tmp/join.log | tail -n 1)" || return 1
    sleep "$POLL_S"
  done
  if [ -z "$fp" ]; then          # the node's own key file, the same 8 chars
    fp=$(docker exec "$CONTAINER" sh -c "age-keygen -y $C_CONF/age-identity.txt | tail -c 9" 2>/dev/null | tr -d '[:space:]')
    case $fp in [a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9]) ;; *) fp="" ;; esac
    [ -z "$fp" ] || note "fingerprint came from age-keygen -y, join.sh printed none"
  fi
  [ -n "$fp" ] || step_fail join "no fingerprint in join.sh's output after ${FP_WAIT_S}s: $(c_cat /tmp/join.log | tail -n 1)" || return 1
  FP=$fp
  ACCEPTED=1
  step_ok join "node accepted; fingerprint $FP read from the node's own output"
}

# ------------------------------------------------------------------------------------ 4 approve, 5 provision
step_approve() {
  CUR_STEP=approve
  "$PY" -m tools.hq_join approve --host "$HOST" --fingerprint "$FP" >"$WORK/approve.out" 2>"$WORK/approve.err" \
    || step_fail approve "hq_join approve: $(first_line <"$WORK/approve.err")" || return 1
  step_ok approve "approved with the node's fingerprint"
}

step_provision() {
  CUR_STEP=provision
  ORG_W42_PROVISION=1 "$PY" -m tools.hq_join provision --host "$HOST" >"$WORK/prov.out" 2>"$WORK/prov.err" \
    || { close_door; step_fail provision "hq_join provision: $(first_line <"$WORK/prov.err")"; return 1; }
  local until=$((SECONDS + JOIN_WAIT_S)) rc=""
  while [ "$SECONDS" -lt "$until" ]; do
    rc=$(c_cat /tmp/join.rc | first_line)
    [ -z "$rc" ] || break
    sleep "$POLL_S"
  done
  close_door                                    # the public endpoint is not needed past the join
  case $rc in
    0|2) T_JOINED=$SECONDS
         step_ok provision "provisioned; join.sh ended with exit $rc" ;;
    '')  step_fail provision "join.sh did not finish in ${JOIN_WAIT_S}s: $(c_cat /tmp/join.log | tail -n 1)"; return 1 ;;
    *)   step_fail provision "join.sh stopped (exit $rc): $(c_cat /tmp/join.log | tail -n 1)"; return 1 ;;
  esac
  # join.sh's step 9 measured the node through its own identity; exit 2 = joined but that failed.
  if [ "$rc" = 0 ]; then
    step_ok node_probe "join.sh step 9 passed"
  else
    finding node_probe_failed
    step_fail node_probe "join.sh step 9 failed: $(c_cat /tmp/join.log | grep -i 'probe' | tail -n 1)"
  fi
  return 0
}

# ------------------------------------------------------------------------------------ 6 W4.0
step_token_worker() {
  CUR_STEP=token_worker
  local nonce rc
  nonce="drill-$(date -u +%s)-$RANDOM"
  c_run token_worker 240 "$HOST" "$nonce" <<'EOS'
set -u
cd /opt/MoonieXHQ/Agents/Core || exit 3
[ -e /root/.claude/.credentials.json ] && { echo "a login file exists in the node"; exit 4; }
exec env HOME=/root ORG_HOST="$1" python3 -I -B tools/infisical_setup.py run Org-Node prod --as "$1" -- \
  python3 -I -c 'import os,sys; e={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": "/root", "CLAUDE_CODE_OAUTH_TOKEN": os.environ["CLAUDE_CODE_OAUTH_TOKEN"]}; os.chdir("/tmp"); os.execvpe(sys.argv[1], sys.argv[1:], e)' claude -p "Reply with exactly this text and nothing else: $2"
EOS
  rc=$?
  if [ $rc -eq 0 ] && grep -Fq -- "$nonce" "$WORK/token_worker.out"; then
    step_ok token_worker "claude -p answered the nonce with CLAUDE_CODE_OAUTH_TOKEN only"
  else
    step_fail token_worker "exit $rc: $(tail -n 1 "$WORK/token_worker.out" 2>/dev/null)"
  fi
  # The W4.0 question, outside `steps` on purpose: it is an answer, not a pass criterion.
  c_run remote_control 120 "$HOST" <<'EOS'
set -u
cd /opt/MoonieXHQ/Agents/Core || exit 3
exec env HOME=/root ORG_HOST="$1" python3 -I -B tools/infisical_setup.py run Org-Node prod --as "$1" -- \
  python3 -I -c 'import os,sys; e={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": "/root", "CLAUDE_CODE_OAUTH_TOKEN": os.environ["CLAUDE_CODE_OAUTH_TOKEN"]}; os.chdir("/tmp"); os.execvpe(sys.argv[1], sys.argv[1:], e)' timeout 25 claude remote-control
EOS
  rc=$?
  # The first output line is kept whatever happened: exit 124 only says the process was still
  # running at 25 s, so what it printed is the evidence. URLs are masked.
  RC_OUT=""
  [ -f "$WORK/remote_control.out" ] \
    && RC_OUT=$(first_line <"$WORK/remote_control.out" | sed -E 's#https?://[^[:space:]]+#[url]#g' | clean)
  if [ $rc -eq 97 ]; then RC_STATE=null; RC_ERR="could not reach the container"
  elif [ $rc -eq 124 ]; then RC_STATE=true          # still running when timeout cut it: not proof of a session
  else
    RC_STATE=false
    RC_ERR=${RC_OUT:-"exit $rc, no output"}
  fi
  return 0
}

# ------------------------------------------------------------------------------------ 7 probe
step_probe() {
  CUR_STEP=probe
  local t0=$SECONDS rc remote
  TASK_ID=$("$PY" -m tools.mesh_check --join-drill task-create "$HOST" 2>"$WORK/task.err" | tail -n 1)
  case $TASK_ID in
    task-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
    *) TASK_ID=""; step_fail probe "no probe task was created: $(first_line <"$WORK/task.err")"; return 1 ;;
  esac
  BRANCH=agent/probe-$TASK_ID
  c_run probe "$PROBE_WAIT_S" "$HOST" "$BRANCH" "docs/ops/mesh-probe/contabo-$HOST.md" "$C_CORE" "$C_CONF" <<'EOS'
set -u
HOST=$1; BRANCH=$2; FILE=$3; CORE=$4; CONF=$5
cd "$CORE" || exit 3
git checkout -q -b "$BRANCH" || exit 4
mkdir -p "$(dirname "$FILE")"
printf 'mesh-probe contabo->%s %s\n' "$HOST" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$FILE"
git add -- "$FILE"
git -c user.name=drill-join -c user.email=drill-join@invalid commit -q -m "mesh-probe: join drill $HOST" || exit 5
GIT_SSH_COMMAND="ssh -i $CONF/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$CONF/known_hosts" \
  git push -q origin "HEAD:refs/heads/$BRANCH" || exit 6
echo "sha=$(git rev-parse HEAD)"
EOS
  rc=$?
  PROBE_SECS=$((SECONDS - t0))
  if [ $rc -ne 0 ]; then
    # GitHub says "The key you are authenticating with has been marked as read only."
    if grep -Eqi 'read[- ]only|denied to deploy key|permission denied|403' "$WORK/probe.out" 2>/dev/null; then
      finding deploy_key_read_only
      step_fail probe "the node's push was refused: its deploy key is read-only (hq_join registers read_only=true), so a node cannot return work to origin"
    elif [ $rc -eq 142 ]; then
      step_fail probe "the node did not finish the probe in ${PROBE_WAIT_S}s"
    else
      step_fail probe "node probe exit $rc: $(tail -n 1 "$WORK/probe.out" 2>/dev/null)"
    fi
    return 1
  fi
  PROBE_SHA=$(sed -n 's/^sha=\([0-9a-f]\{40\}\)$/\1/p' "$WORK/probe.out" | tail -n 1)
  [ -n "$PROBE_SHA" ] || step_fail probe "the node's probe printed no commit sha" || return 1
  remote=$(GIT_TERMINAL_PROMPT=0 git -C "$CORE" ls-remote origin "refs/heads/$BRANCH" 2>"$WORK/lsr.err" | awk '{print $1; exit}')
  [ "$remote" = "$PROBE_SHA" ] \
    || step_fail probe "origin does not show the node's commit on $BRANCH (origin: ${remote:-nothing}) $(first_line <"$WORK/lsr.err")" || return 1
  [ "$PROBE_SECS" -le 900 ] || step_fail probe "the probe took ${PROBE_SECS}s, limit 900" || return 1
  T_PROBE=$SECONDS
  step_ok probe "task $TASK_ID done by the node: $BRANCH @ $(printf '%s' "$PROBE_SHA" | cut -c1-8) on origin in ${PROBE_SECS}s, not merged"
}

# ------------------------------------------------------------------------------------ 8 leave + verify
step_leave() {
  CUR_STEP=leave
  if [ "$ACCEPTED" -eq 0 ]; then
    step_ok leave "the node was never accepted: nothing to revoke"
    return 0
  fi
  local rc failed unwired real bad=""
  # Without the flag hq_join wires none of the three real revokers (w42_enabled()): it would answer
  # "not wired yet" for each and remove nothing.
  ORG_W42_PROVISION=1 "$PY" -m tools.hq_join leave --host "$HOST" --live >"$WORK/leave.out" 2>"$WORK/leave.err"
  rc=$?
  failed=$(grep -c '^  \[FAILED\]' "$WORK/leave.out")
  unwired=$(grep '^  \[FAILED\] authorized_keys' "$WORK/leave.out" | grep -c 'not wired yet')
  for real in infisical_client_secret tailscale_device github_deploy_key; do
    grep -q "^  \[ok\] $real " "$WORK/leave.out" || bad="$bad $real"
  done
  if [ "$rc" -eq 0 ]; then
    step_ok leave "all revocations done"
  elif [ "$rc" -eq 1 ] && [ -z "$bad" ] && [ "$failed" -gt 0 ] && [ "$failed" -eq "$unwired" ]; then
    LEAVE_PARTIAL=1
    finding leave_partial_authorized_keys_unwired
    step_ok leave "3 real revocations ok; $failed authorized_keys steps 'not wired yet' (W2.8), as designed"
  else
    step_fail leave "hq_join leave exit $rc, not ok:${bad:- none missing} $(grep '^  \[FAILED\]' "$WORK/leave.out" | grep -v 'not wired yet' | head -n 1) $(first_line <"$WORK/leave.err")"
  fi
  return 0
}

verify_all() {
  local r st
  tailnet_has_device; r=$?
  case $r in 1) step_ok verify_tailnet "no device named $HOST" ;;
             0) step_fail verify_tailnet "the tailnet still has a device named $HOST" ;;
             *) step_fail verify_tailnet "the Tailscale API could not be read" ;; esac
  deploy_key_present; r=$?
  case $r in 1) step_ok verify_deploy_key "no key titled org-node:$HOST on $GH_REPO" ;;
             0) step_fail verify_deploy_key "the deploy key org-node:$HOST is still on $GH_REPO" ;;
             *) step_fail verify_deploy_key "gh api repos/$GH_REPO/keys could not be read" ;; esac
  infisical_live_secret; r=$?
  case $r in 1) step_ok verify_infisical "no live client secret org-node:$HOST" ;;
             0) step_fail verify_infisical "a live client secret org-node:$HOST remains under org-node" ;;
             *) step_fail verify_infisical "node-secrets could not be read" ;; esac
  st=$(host_row_status)
  if [ "$ACCEPTED" -eq 0 ] && [ -z "$st" ]; then
    step_ok verify_host_row "the host never registered, so there is no row"
  elif [ "$st" = left ]; then
    step_ok verify_host_row "hosts row is left"
  elif [ "$LEAVE_PARTIAL" -eq 1 ]; then
    step_fail verify_host_row "hosts row is '${st:-missing}', not left: leave() marks left only when every step is ok, and authorized_keys is not wired (W2.8)"
  else
    step_fail verify_host_row "hosts row is '${st:-missing}', not left"
  fi
  verify_authorized_keys
}

verify_authorized_keys() {
  local bad="" rc
  if [ -e "$AK_FILE" ]; then
    grep -Fq -- "$HOST" "$AK_FILE"; rc=$?
    case $rc in 1) ;; 0) bad="$bad contabo:line-found" ;; *) bad="$bad contabo:unreadable" ;; esac
  fi
  # findstr exits 1 for "no match" AND for a file it cannot open, so a "no" is only believed after
  # a probe that must match (any key line) has proved the file is readable.
  win_findstr() {
    ssh -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=yes "$WINBOX_SSH" \
        "findstr /C:$1 "'C:\ProgramData\ssh\administrators_authorized_keys' >/dev/null 2>&1
  }
  win_findstr ssh-; rc=$?
  if [ $rc -ne 0 ]; then
    bad="$bad winbox:unverifiable(administrators_authorized_keys not readable, ssh $WINBOX_SSH exit $rc)"
  else
    win_findstr "$HOST"; rc=$?
    case $rc in 1) ;; 0) bad="$bad winbox:line-found" ;; *) bad="$bad winbox:unverifiable(ssh $WINBOX_SSH exit $rc)" ;; esac
  fi
  note "authorized_keys on mac not checked: Remote Login stays closed until G2"
  if [ -z "$bad" ]; then step_ok verify_authorized_keys "no line for $HOST on contabo or winbox; mac skipped until G2"
  else step_fail verify_authorized_keys "$(printf '%s' "$bad" | sed 's/^ //')"; fi
}

# ------------------------------------------------------------------------------------ 9 cleanup
remote_sha() { GIT_TERMINAL_PROMPT=0 git -C "$CORE" ls-remote origin "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1; exit}'; }

cleanup() {
  CUR_STEP=cleanup
  local bad=""
  case $BRANCH in
    ''|agent/probe-task-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
    *) BRANCH="" ;;                             # never delete a name that is not ours
  esac
  if [ -n "$BRANCH" ] && [ -n "$(remote_sha)" ]; then
    GIT_TERMINAL_PROMPT=0 git -C "$CORE" push -q origin --delete "$BRANCH" >/dev/null 2>&1
    [ -z "$(remote_sha)" ] || bad="$bad origin-branch:$BRANCH-still-there"
  fi
  if [ -n "$TASK_ID" ]; then
    "$PY" -m tools.mesh_check --join-drill task-close "$TASK_ID" >/dev/null 2>&1 || bad="$bad task:$TASK_ID-not-cancelled"
  fi
  if [ -n "$CONTAINER" ]; then
    docker rm -f -v "$CONTAINER" >/dev/null 2>&1
    [ -z "$(docker ps -a -q --filter "name=^${CONTAINER}\$" 2>/dev/null)" ] || bad="$bad container:$CONTAINER-still-there"
  fi
  if [ -n "$VOLUME" ]; then
    docker volume rm -f "$VOLUME" >/dev/null 2>&1
    [ -z "$(docker volume ls -q --filter "name=^${VOLUME}\$" 2>/dev/null)" ] || bad="$bad volume:$VOLUME-still-there"
  fi
  close_door
  [ "$(door_state)" = closed ] || bad="$bad door:not-closed"
  if [ -z "$bad" ]; then step_ok cleanup "branch, task, container, volume removed; door closed"
  else step_fail cleanup "left behind:$bad"; fi
}

# ------------------------------------------------------------------------------------ outputs
has_step() { cut -f1 "$STEPS" | grep -qx "$1"; }
all_ok() {
  local n
  [ -z "$(awk -F'\t' '$2 == 0 {print $1; exit}' "$STEPS")" ] || return 1
  for n in $STEP_NAMES; do has_step "$n" || return 1; done
}
first_failed() {
  local n f
  f=$(awk -F'\t' '$2 == 0 {print $1; exit}' "$STEPS")
  if [ -z "$f" ]; then for n in $STEP_NAMES; do has_step "$n" || { f=$n; break; }; done; fi
  printf '%s' "$f"
}
json_list() { # json_list <file>: lines -> ["a", "b"]
  local first=1 line
  printf '['
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    [ $first -eq 1 ] || printf ', '
    first=0
    printf '%s' "$(jstr "$line")"
  done <"$1"
  printf ']'
}
steps_json() {
  local first=1 n ok d b
  printf '['
  while IFS=$'\t' read -r n ok d; do
    [ -n "$n" ] || continue
    [ $first -eq 1 ] || printf ', '
    first=0
    if [ "$ok" = 1 ]; then b=true; else b=false; fi
    printf '{"name": %s, "ok": %s, "detail": %s}' "$(jstr "$n")" "$b" "$(jstr "$d")"
  done <"$STEPS"
  printf ']'
}
num_or_null() { case ${1:-} in ''|*[!0-9]*) printf null ;; *) printf '%s' "$1" ;; esac; }
mins_or_null() { if [ -n "$1" ]; then minutes $(($1 - STARTED)); else printf null; fi; }

write_json() { # write_json <path>
  local ok=false failed=null rcj=null
  all_ok && ok=true
  [ "$ok" = true ] || failed=$(jstr "$(first_failed)")
  [ "$RC_STATE" = null ] || rcj=$RC_STATE
  {
    printf '{"ok": %s, "at": "%s", "host": %s, "stamp": "%s",\n' "$ok" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(jstr "$HOST")" "$STAMP"
    printf ' "steps": %s,\n' "$(steps_json)"
    printf ' "failed_step": %s,\n' "$failed"
    printf ' "w40": {"remote_control": %s, "remote_control_cmd": %s, "remote_control_error": %s, "remote_control_output": %s},\n' \
      "$rcj" "$(jstr "$RC_CMD")" "$(jstr "$RC_ERR")" "$(jstr "$RC_OUT")"
    printf ' "probe": {"task": %s, "branch": %s, "sha": %s, "seconds": %s},\n' \
      "$(jstr "$TASK_ID")" "$(jstr "$BRANCH")" "$(jstr "$PROBE_SHA")" "$(num_or_null "$PROBE_SECS")"
    printf ' "findings": %s,\n "notes": %s,\n' "$(json_list "$FINDINGS")" "$(json_list "$NOTES")"
    printf ' "minutes": {"to_joined": %s, "to_probe": %s, "total": %s},\n' \
      "$(mins_or_null "$T_JOINED")" "$(mins_or_null "$T_PROBE")" "$(minutes $((SECONDS - STARTED)))"
    printf ' "code": {"drill": %s, "join_service": %s},\n' "$(jstr "$CODE_DRILL")" "$(jstr "$CODE_JOIN")"
    printf ' "by": "scripts/drill-join.sh", "version": 1}\n'
  } >"$1.tmp" && mv "$1.tmp" "$1"
}

jsonl_row() {
  local result=PASS gaps="$WORK/gaps"
  all_ok || result="FAIL (step $(first_failed))"
  { cat "$FINDINGS"; awk -F'\t' '$2 == 0 {print "step " $1 ": " $3}' "$STEPS"; } >"$gaps"
  printf '{"date": "%s", "machine": "contabo", "kind": "join-drill", "scope": %s, "result": %s, "minutes_to_remote_access": %s, "minutes_to_org_restore": %s, "bytes_from_git_mb": null, "bytes_from_drive_mb": 0, "irreplaceable_lost_gb": 0, "human_steps": ["CEO taps the drill card"], "gaps_found": %s, "by": "scripts/drill-join.sh", "ref": %s}\n' \
    "$(date -u +%Y-%m-%d)" \
    "$(jstr "throwaway node $HOST in a $IMAGE container on contabo: join, approve, provision, token_worker, probe, leave, verify")" \
    "$(jstr "$result")" "$(mins_or_null "$T_JOINED")" "$(mins_or_null "$T_PROBE")" \
    "$(json_list "$gaps")" "$(jstr "state/mesh-check/join-drill.json host=$HOST")"
}

finish() {
  [ "$FINISHED" -eq 0 ] || return 0
  FINISHED=1
  local out="$STATE_DIR/join-drill.json" row
  if [ "$MINTED" -eq 1 ]; then step_leave; verify_all; fi
  cleanup
  mkdir -p "$STATE_DIR" 2>/dev/null
  write_json "$out" || say "WARNING: could not write $out"
  if "$PY" -m tools.mesh_check --join-drill record "$out" >"$WORK/record.out" 2>&1; then
    rec record 1 "join_drill event written"
  else
    rec record 0 "could not record the event: $(first_line <"$WORK/record.out")"
  fi
  write_json "$out" || say "WARNING: could not write $out"
  row=$(jsonl_row)
  if [ "$LOG_TO_REPO" -eq 1 ]; then printf '%s\n' "$row" >>"$ROWS_FILE"; say "row appended to $ROWS_FILE"; fi
  say "result: $(all_ok && echo PASS || echo "FAIL at $(first_failed)") in $(minutes $((SECONDS - STARTED))) min, written to $out"
  say "re-os-drills row:"
  printf '%s\n' "$row"
  all_ok
  local rc=$?
  rm -rf "$WORK"
  return $rc
}

# shellcheck disable=SC2317,SC2329  # runs from the EXIT trap (0.9 reports SC2317, 0.10+ SC2329)
on_exit() {
  local rc=$?
  if [ "$FINISHED" -eq 0 ]; then
    rec "$CUR_STEP" 0 "stopped by a signal or an unexpected error (exit $rc)"
    finish >/dev/null 2>&1
  fi
  exit "$rc"
}

# ------------------------------------------------------------------------------------ main
preflight
WORK=$(mktemp -d "${TMPDIR:-/tmp}/drill-join.XXXXXX") || refuse "no temp dir"
STEPS=$WORK/steps; NOTES=$WORK/notes; FINDINGS=$WORK/findings
: >"$STEPS"; : >"$NOTES"; : >"$FINDINGS"
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
trap on_exit EXIT
say "drill for $HOST; $PREFLIGHT_DETAIL"
say "code under test: $CORE at $CODE_DRILL (python $PY); join service and door.sh approve: $LIVE_CORE at $CODE_JOIN"
if [ "$CODE_DRILL" != "$CODE_JOIN" ]; then
  note "the join API and door.sh's approve leg run the live checkout at $CODE_JOIN; the drill's tools run $CODE_DRILL"
fi
step_ok preflight "$PREFLIGHT_DETAIL"

if step_door_open && step_container && step_mint && step_join && step_approve && step_provision; then
  step_token_worker
  step_probe
fi
finish && exit 0
exit 1
