#!/bin/sh
# join.sh - make this Linux or macOS machine a MoonieX org node (Org Mesh W4.3).
#
#   curl -fsSL https://<hub>/org-join/join.sh | sh -s -- --token <t> --host <name> [--hq-root <path>]
#
# Better, so the token is not in `ps` for the whole run (it is single use and dies after 15
# minutes, but it IS the credential until step 4 has used it):
#
#   curl -fsSL https://<hub>/org-join/join.sh | ORG_JOIN_TOKEN=<t> sh -s -- --host <name>
#
# Arguments
#   --token <t>      the one-time token from `hq_join mint` (or env ORG_JOIN_TOKEN)
#   --host <name>    this machine's node name, the one the token was minted for
#   --hq-root <p>    where the HQ folder goes (default: /opt/MoonieXHQ as root, else ~/MoonieXHQ)
#   --hub <url>      the hub, https://<hub>. Default: the hub this script was fetched from
#   --dry-run        print every step, change nothing, contact nothing
#
# The nine steps, in order. Each is safe to repeat: run the same command again after a failure.
#   1 check the arguments             6 wait for the hub to seal this node's identity to its key
#   2 install what is missing         7 clone Agents-Core over the deploy key, build the venv
#   3 make the node's keys            8 open the sealed identity, save it, write node.yaml
#   4 accept: hand the hub the token  9 probe
#   5 join the tailnet
# The deploy key only works once the hub has provisioned this node (step 6), and the save in
# step 8 is a script from the clone, so the clone comes between the wait and the save.
#
# No secret is typed, written to disk by this script, or put on a command line of a process that
# lives longer than a moment. The token travels in a request body on stdin. The node's identity
# (client id + secret) is age-encrypted to a key that never leaves this machine; it flows
# age -> python -> infisical_setup.py through pipes and is stored only by that last program,
# under /etc/infisical (root, 0600).
#
# Needs root for: installing packages, `tailscale up`, and saving the identity. On Linux and
# macOS that is sudo (asked for once, up front). Run it as your own user, not as root, on a Mac.

set -u

TOTAL=9
HUB_DEFAULT="@@ORG_JOIN_HUB@@"
DRY_RUN=0
TOKEN=""
HOST=""
HQ_ROOT=""
HUB=""
OS=""
PY=""
AGE_PUB=""
DEPLOY_PUB=""
TS_KEY=""
CIPHER=""
HTTP_CODE=""
HTTP_BODY=""
CONF_DIR=""
AGE_ID=""
DEPLOY_KEY=""
DISPATCH_KEY=""
CORE=""
GH_REPO_SSH="git@github.com:PASAKON/Agents-Core.git"
POLL_S=15
POLL_MAX_S=900

say() { printf '    %s\n' "$*"; }
step() { printf '\n[%s/%s] %s\n' "$1" "$TOTAL" "$2"; }
die() { printf '\njoin: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  printf '%s\n' \
    "join.sh --token <t> --host <name> [--hq-root <path>] [--hub <url>] [--dry-run]" \
    "  --token <t>     one-time join token (or env ORG_JOIN_TOKEN, which keeps it out of ps)" \
    "  --host <name>   this machine's node name; the token was minted for it" \
    "  --hq-root <p>   HQ folder (default /opt/MoonieXHQ as root, else ~/MoonieXHQ)" \
    "  --hub <url>     https://<hub> (default: the hub this script was fetched from)" \
    "  --dry-run       print every step, change nothing, contact nothing"
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
}

root_prefix() {
  if [ "$(id -u)" -eq 0 ]; then printf ''; else printf 'sudo '; fi
}

# act: show the command, run it unless --dry-run. stdin is closed: a package manager must never
# read the rest of this script when it is piped into sh.
act() {
  printf '    $ %s\n' "$*"
  if [ "$DRY_RUN" -eq 0 ]; then "$@" </dev/null || die "failed: $*"; fi
}

act_root() {
  printf '    $ %s%s\n' "$(root_prefix)" "$*"
  if [ "$DRY_RUN" -eq 0 ]; then as_root "$@" </dev/null || die "failed: $*"; fi
}

# ---------------------------------------------------------------- 1: arguments

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --token) [ $# -ge 2 ] || die "--token needs a value"; TOKEN=$2; shift 2 ;;
      --token=*) TOKEN=${1#--token=}; shift ;;
      --host) [ $# -ge 2 ] || die "--host needs a value"; HOST=$2; shift 2 ;;
      --host=*) HOST=${1#--host=}; shift ;;
      --hq-root) [ $# -ge 2 ] || die "--hq-root needs a value"; HQ_ROOT=$2; shift 2 ;;
      --hq-root=*) HQ_ROOT=${1#--hq-root=}; shift ;;
      --hub) [ $# -ge 2 ] || die "--hub needs a value"; HUB=$2; shift 2 ;;
      --hub=*) HUB=${1#--hub=}; shift ;;
      --dry-run) DRY_RUN=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown argument starting '$(printf '%.6s' "$1")' (see --help)" ;;
    esac
  done
}

normalize_hub() {
  _h=${1%/}
  _h=${_h%/org-join}
  printf '%s/org-join' "$_h"
}

check_args() {
  [ -n "${HOME:-}" ] || die "HOME is not set"
  case "$(uname -s)" in
    Linux) OS=linux ;;
    Darwin) OS=darwin ;;
    *) die "unsupported OS $(uname -s): this script is for Linux and macOS (Windows: join.ps1)" ;;
  esac
  if [ -z "$TOKEN" ] && [ -n "${ORG_JOIN_TOKEN:-}" ]; then TOKEN=$ORG_JOIN_TOKEN; fi
  unset ORG_JOIN_TOKEN   # do not hand it to every child process we start
  [ -n "$TOKEN" ] || die "no token: pass --token <t> or set ORG_JOIN_TOKEN"
  printf '%s' "$TOKEN" | grep -Eq '^hqj_[A-Za-z0-9_-]{43}$' \
    || die "the token is not in the expected shape (hqj_ and 43 more characters); copy it again"
  [ -n "$HOST" ] || die "no --host <name>"
  printf '%s' "$HOST" | grep -Eq '^[a-z][a-z0-9-]{1,29}[a-z0-9]$' \
    || die "--host must be 3-31 characters: a-z, 0-9, '-', starting with a letter, not ending in '-'"
  if [ -z "$HQ_ROOT" ]; then
    if [ "$OS" = linux ] && [ "$(id -u)" -eq 0 ]; then HQ_ROOT=/opt/MoonieXHQ; else HQ_ROOT=$HOME/MoonieXHQ; fi
  fi
  case "$HQ_ROOT" in /*) ;; *) die "--hq-root must be an absolute path" ;; esac
  HQ_ROOT=${HQ_ROOT%/}
  [ -n "$HUB" ] || HUB=$HUB_DEFAULT
  case "$HUB" in
    ""|@@*) die "no hub URL: this copy was not fetched from the hub. Pass --hub https://<hub>" ;;
  esac
  HUB=$(normalize_hub "$HUB")
  printf '%s' "$HUB" | grep -Eq '^https?://[A-Za-z0-9.-]+(:[0-9]+)?/org-join$' \
    || die "--hub must look like https://<hub>"
  case "$HUB" in
    https://*|http://127.0.0.1[:/]*|http://localhost[:/]*) ;;
    *) die "the hub URL must be https (plain http is for localhost only): the token would cross the network in clear text" ;;
  esac
  CONF_DIR=$HOME/.config/mooniex
  AGE_ID=$CONF_DIR/age-identity.txt
  DEPLOY_KEY=$CONF_DIR/deploy_key
  DISPATCH_KEY=$HOME/.ssh/org_dispatch   # the path lib/mesh.py reads
  CORE=$HQ_ROOT/Agents/Core
}

root_need_text() {
  if [ "$(id -u)" -eq 0 ]; then printf 'Running as root: fine.'
  elif have sudo; then printf 'Uses sudo: it will ask for your password now.'
  else printf 'NOT root and no sudo here: this will stop.'; fi
}

banner() {
  step 1 "check the arguments"
  say "host $HOST ($OS), hub $HUB"
  say "HQ root $HQ_ROOT  (checkout: $CORE)"
  say "keys go under $CONF_DIR (age identity, deploy key) and $HOME/.ssh (dispatch key)"
  say "ROOT NEEDED for three steps: installing packages (2), tailscale up (5), saving the node's"
  say "identity under /etc/infisical (8). $(root_need_text)"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY RUN: every step below is printed, nothing is changed, nothing is contacted"
  fi
}

ensure_root_access() {
  [ "$(id -u)" -eq 0 ] && return 0
  if ! have sudo; then
    [ "$DRY_RUN" -eq 1 ] && { say "WARNING: not root and no sudo: a real run would stop here"; return 0; }
    die "not root and sudo is not installed: run as root, or install sudo"
  fi
  [ "$DRY_RUN" -eq 1 ] || sudo -v || die "sudo did not accept the password"
}

# ---------------------------------------------------------------- 2: install

find_python() {
  for _c in python3.13 python3.12 python3.11 python3; do
    _p=$(command -v "$_c" 2>/dev/null) || continue
    if "$_p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PY=$_p
      return 0
    fi
  done
  return 1
}

node_major() { node -p 'process.versions.node.split(".")[0]' 2>/dev/null; }
have_node22() { have node && [ "$(node_major || echo 0)" -ge 22 ] 2>/dev/null; }

install_node_linux() {
  case "$(uname -m)" in
    x86_64) _na=x64 ;;
    aarch64|arm64) _na=arm64 ;;
    *) die "no Node 22 build for $(uname -m): install Node 22 yourself, then re-run" ;;
  esac
  _base=https://nodejs.org/dist/latest-v22.x
  say "Node 22 from nodejs.org: fetch SHASUMS256.txt, download the linux-$_na tarball, verify its sha256, extract into /usr/local"
  [ "$DRY_RUN" -eq 1 ] && return 0
  _sums=$(curl -fsSL "$_base/SHASUMS256.txt" </dev/null) || die "could not fetch $_base/SHASUMS256.txt"
  _file=$(printf '%s\n' "$_sums" | awk -v s="-linux-$_na.tar.xz" 'length($2) > length(s) && substr($2, length($2) - length(s) + 1) == s {print $2; exit}')
  _want=$(printf '%s\n' "$_sums" | awk -v f="$_file" '$2 == f {print $1; exit}')
  [ -n "$_file" ] && [ -n "$_want" ] || die "no linux-$_na tarball in $_base/SHASUMS256.txt"
  _tmp=$(mktemp -d) || die "mktemp failed"
  curl -fsSL "$_base/$_file" -o "$_tmp/$_file" </dev/null || { rm -rf "$_tmp"; die "download of $_file failed"; }
  _got=$(sha256sum "$_tmp/$_file" | awk '{print $1}')
  [ "$_got" = "$_want" ] || { rm -rf "$_tmp"; die "sha256 of $_file does not match SHASUMS256.txt; not installing it"; }
  as_root tar -xJf "$_tmp/$_file" -C /usr/local --strip-components=1 </dev/null || { rm -rf "$_tmp"; die "could not extract Node into /usr/local"; }
  rm -rf "$_tmp"
}

install_tailscale_linux() {
  [ -r /etc/os-release ] || die "no /etc/os-release: install Tailscale yourself, then re-run"
  # shellcheck disable=SC1091
  _id=$(. /etc/os-release && printf '%s' "${ID:-}")
  # shellcheck disable=SC1091
  _code=$(. /etc/os-release && printf '%s' "${VERSION_CODENAME:-}")
  case "$_id" in ubuntu|debian) ;; *) die "Tailscale repo setup here covers Debian and Ubuntu only ($_id): install Tailscale yourself, then re-run" ;; esac
  _repo=https://pkgs.tailscale.com/stable/$_id/$_code
  say "Tailscale apt repository for $_id $_code ($_repo.*), then apt-get install tailscale"
  [ "$DRY_RUN" -eq 1 ] && return 0
  curl -fsSL "$_repo.noarmor.gpg" </dev/null | as_root tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null \
    || die "could not fetch the Tailscale signing key"
  curl -fsSL "$_repo.tailscale-keyring.list" </dev/null | as_root tee /etc/apt/sources.list.d/tailscale.list >/dev/null \
    || die "could not fetch the Tailscale apt list"
  as_root apt-get update -qq </dev/null || die "apt-get update failed"
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y tailscale </dev/null || die "apt-get install tailscale failed"
}

install_linux() {
  if ! have apt-get; then
    [ "$DRY_RUN" -eq 1 ] && { say "WARNING: no apt-get: a real run would stop here (Debian and Ubuntu only)"; return 0; }
    die "no apt-get: this script installs on Debian and Ubuntu. Install git, python3.11+, Node 22, age, tailscale and claude yourself, then re-run"
  fi
  _missing=""
  have git || _missing="$_missing git"
  have curl || _missing="$_missing curl ca-certificates"
  have ssh-keygen || _missing="$_missing openssh-client"
  { have age && have age-keygen; } || _missing="$_missing age"
  if find_python; then
    "$PY" -c 'import ensurepip, venv' 2>/dev/null || _missing="$_missing python3-venv"
  else
    _missing="$_missing python3 python3-venv"
  fi
  have_node22 || have xz || _missing="$_missing xz-utils"
  if [ -n "$_missing" ]; then
    act_root apt-get update -qq
    # shellcheck disable=SC2086  # package names, no spaces
    act_root env DEBIAN_FRONTEND=noninteractive apt-get install -y $_missing
  else
    say "apt packages: git, curl, openssh-client, age, python3 + venv present"
  fi
  find_python || [ "$DRY_RUN" -eq 1 ] || die "python 3.11 or newer is required (this machine has: $(python3 --version 2>&1)); install it, then re-run"
  if have_node22; then say "node $(node --version): present"; else install_node_linux; fi
  if have tailscale; then say "tailscale: present"; else install_tailscale_linux; fi
  if have claude; then say "claude: present"; else act_root npm install -g @anthropic-ai/claude-code; fi
}

install_darwin() {
  if ! have brew && [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
  if ! have brew; then
    [ "$DRY_RUN" -eq 1 ] && { say "WARNING: Homebrew is not installed: a real run would stop here"; return 0; }
    die "Homebrew is not installed: install it from https://brew.sh, then re-run (this script does not pipe a second installer into your shell)"
  fi
  [ "$(id -u)" -ne 0 ] || die "on macOS run this as your own user, not as root: Homebrew refuses to run as root"
  _missing=""
  have git || _missing="$_missing git"
  { have age && have age-keygen; } || _missing="$_missing age"
  find_python || _missing="$_missing python@3.12"
  have_node22 || _missing="$_missing node@22"
  have tailscale || _missing="$_missing tailscale"
  if [ -n "$_missing" ]; then
    # shellcheck disable=SC2086  # formula names, no spaces
    act brew install $_missing
  else
    say "brew packages: git, age, python 3.11+, node 22, tailscale present"
  fi
  case "$_missing" in
    *node@22*) act brew link --overwrite --force node@22 ;;
  esac
  case "$_missing" in
    *tailscale*) act_root brew services start tailscale ;;
  esac
  find_python || [ "$DRY_RUN" -eq 1 ] || die "python 3.11 or newer is required; install it, then re-run"
  if have claude; then say "claude: present"; else act npm install -g @anthropic-ai/claude-code; fi
}

do_install() {
  step 2 "install what is missing (git, python 3.11+, node 22, age, tailscale, claude)"
  ensure_root_access
  if [ "$OS" = linux ]; then install_linux; else install_darwin; fi
  find_python || true
  [ -n "$PY" ] || PY=python3   # dry run on a machine without one
}

# ---------------------------------------------------------------- 3: keys

do_keys() {
  step 3 "make the node's keys (kept if they already exist), 0600"
  say "age identity    $AGE_ID"
  say "deploy key      $DEPLOY_KEY (ssh ed25519, read-only on GitHub once the hub registers it)"
  say "dispatch key    $DISPATCH_KEY (ssh ed25519, what lib/mesh.py uses to call other nodes)"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "would create whichever of the three is missing; only the public halves are ever shown"
    AGE_PUB="age1<the public half of the identity>"
    return 0
  fi
  mkdir -p "$CONF_DIR" "$HOME/.ssh" || die "could not create $CONF_DIR"
  chmod 700 "$CONF_DIR" "$HOME/.ssh"
  if [ ! -f "$AGE_ID" ]; then
    ( umask 077 && age-keygen -o "$AGE_ID" >/dev/null 2>&1 ) || die "age-keygen failed"
  fi
  chmod 600 "$AGE_ID"
  AGE_PUB=$(age-keygen -y "$AGE_ID") || die "could not read the age recipient from $AGE_ID"
  if [ ! -f "$DEPLOY_KEY" ]; then
    ssh-keygen -q -t ed25519 -N '' -C "org-node:$HOST" -f "$DEPLOY_KEY" </dev/null || die "ssh-keygen (deploy key) failed"
  fi
  if [ ! -f "$DISPATCH_KEY" ]; then
    ssh-keygen -q -t ed25519 -N '' -C "org_dispatch-$HOST" -f "$DISPATCH_KEY" </dev/null || die "ssh-keygen (dispatch key) failed"
  fi
  chmod 600 "$DEPLOY_KEY" "$DISPATCH_KEY"
  DEPLOY_PUB=$(cat "$DEPLOY_KEY.pub") || die "no $DEPLOY_KEY.pub"
  say "keys ready"
}

# ---------------------------------------------------------------- hub calls

# Field values arrive one per line on stdin, never as arguments.
json_accept() {
  "$PY" -c 'import json, sys
f = sys.stdin.read().split("\n")
d = {"token": f[0], "host": f[1], "os": f[2], "hq_root": f[3], "pubkey": f[4]}
if f[5]:
    d["deploy_pubkey"] = f[5]
sys.stdout.write(json.dumps(d))'
}

json_sealed() {
  "$PY" -c 'import json, sys
f = sys.stdin.read().split("\n")
sys.stdout.write(json.dumps({"host": f[0], "token": f[1]}))'
}

json_get() {
  "$PY" -c 'import json, sys
try:
    v = json.load(sys.stdin).get(sys.argv[1], "")
except Exception:
    v = ""
sys.stdout.write(v if isinstance(v, str) else "")' "$1"
}

# hub_post <route> <json body>. Sets HTTP_CODE and HTTP_BODY (000 when the hub is unreachable).
# The body goes to curl on stdin and the answer comes back through a variable: no file, and
# the token is never on a command line.
hub_post() {
  _out=$(printf '%s' "$2" | curl -sS --max-time 30 -X POST -H 'Content-Type: application/json' \
    --data-binary @- -w '\n%{http_code}' "$HUB/$1" 2>/dev/null) || { HTTP_CODE=000; HTTP_BODY=""; return 1; }
  HTTP_CODE=$(printf '%s\n' "$_out" | tail -n 1)
  HTTP_BODY=$(printf '%s\n' "$_out" | sed '$d')
  _out=""
}

sealed_body() { printf '%s\n%s\n' "$HOST" "$TOKEN" | json_sealed; }

# ---------------------------------------------------------------- 4: accept

do_accept() {
  step 4 "accept: give the hub the token and this node's public keys"
  say "POST $HUB/accept  (host, os, hq_root, age recipient, deploy public key; the token is in the body)"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "a used token is refused; step 6's answer then tells 'already joined' from 'wrong token'"
    return 0
  fi
  _body=$(printf '%s\n%s\n%s\n%s\n%s\n%s\n' "$TOKEN" "$HOST" "$OS" "$HQ_ROOT" "$AGE_PUB" "$DEPLOY_PUB" | json_accept) \
    || die "could not build the request"
  hub_post accept "$_body" || die "could not reach the hub at $HUB"
  _body=""
  case "$HTTP_CODE" in
    200)
      say "accepted: the hub now lists $HOST as pending_identity"
      TS_KEY=$(printf '%s' "$HTTP_BODY" | json_get tailscale_authkey)
      ;;
    400) die "the hub refused the request: $(printf '%s' "$HTTP_BODY" | json_get message)" ;;
    403)
      # Used, expired, wrong host or unknown all look the same here. The sealed call tells
      # "this token already joined this host" (202/200) from "never valid" (403).
      hub_post sealed "$(sealed_body)" || die "could not reach the hub at $HUB"
      case "$HTTP_CODE" in
        200|202) say "already joined with this token: continuing with the steps that are left" ;;
        *) die "the hub refused this token: it is unknown, already used for another machine, expired (15 min), or minted for a different host name. Ask for a new one." ;;
      esac
      ;;
    409) die "the hub already has a node called $HOST. Pick another name, or leave the old one first" ;;
    429) die "the hub is rate limiting this address: wait a minute and run the same command again" ;;
    000) die "could not reach the hub at $HUB" ;;
    *) die "unexpected answer from the hub: HTTP $HTTP_CODE" ;;
  esac
}

# ---------------------------------------------------------------- 5: tailnet

on_tailnet() { have tailscale && tailscale ip -4 >/dev/null 2>&1; }

do_tailscale() {
  step 5 "join the tailnet (tag:org-node), or confirm this machine is already on it"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "if the hub sent a pre-auth key: $(root_prefix)tailscale up --auth-key <key from the hub> --hostname $HOST --advertise-tags=tag:org-node"
    say "else the machine must already be on the tailnet; if it is not, this step stops with instructions"
    return 0
  fi
  if on_tailnet; then
    say "already on the tailnet as $(tailscale ip -4 | head -n 1)"
  elif [ -n "$TS_KEY" ]; then
    # The key is single use and short lived, and `up` returns in seconds. It is the one secret
    # that has to be an argument: tailscale up has no stdin form.
    as_root tailscale up --auth-key "$TS_KEY" --hostname "$HOST" --advertise-tags=tag:org-node </dev/null \
      || die "tailscale up failed. The key was single use: join the tailnet by hand ($(root_prefix)tailscale up --hostname $HOST), then run this command again"
    say "joined the tailnet"
  else
    die "this machine is not on the tailnet and the hub sent no Tailscale key (it has none configured yet). Join it yourself with:  $(root_prefix)tailscale up --hostname $HOST  and run this command again"
  fi
  TS_KEY=""
}

# ---------------------------------------------------------------- 6: wait for the sealed identity

do_wait_sealed() {
  step 6 "wait for the hub to seal this node's identity (polls every ${POLL_S} s, up to $((POLL_MAX_S / 60)) min)"
  say "POST $HUB/sealed  -> pending until the Mac provisions it, then the age ciphertext"
  say "the ciphertext is held in memory only; only the identity in $AGE_ID can open it"
  [ "$DRY_RUN" -eq 1 ] && return 0
  _waited=0
  while :; do
    if hub_post sealed "$(sealed_body)"; then
      case "$HTTP_CODE" in
        200)
          CIPHER=$(printf '%s' "$HTTP_BODY" | json_get ciphertext)
          [ -n "$CIPHER" ] || die "the hub said ready but sent no ciphertext"
          say "sealed identity received"
          return 0
          ;;
        202) say "pending (${_waited} s)" ;;
        403) die "the hub will not release the sealed identity for this token (expired after 24 h, or the node left). Ask for a new token" ;;
        429) say "rate limited, waiting" ;;
        *) say "hub answered HTTP $HTTP_CODE, retrying" ;;
      esac
    else
      say "hub not reachable, retrying"
    fi
    [ "$_waited" -lt "$POLL_MAX_S" ] || die "gave up waiting ($_waited s): the hub did not provision $HOST. Run the same command again to keep waiting"
    sleep "$POLL_S"
    _waited=$((_waited + POLL_S))
  done
}

# ---------------------------------------------------------------- 7: clone + venv

git_ssh() {
  printf 'ssh -i %s -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=%s' \
    "'$DEPLOY_KEY'" "'$CONF_DIR/known_hosts'"
}

do_clone() {
  step 7 "clone Agents-Core over the deploy key, build the venv"
  say "$GH_REPO_SSH -> $CORE  (GIT_SSH_COMMAND: the deploy key only, nothing from ~/.ssh)"
  say "then: $PY -m venv $CORE/.venv and pip install -r requirements.txt"
  [ "$DRY_RUN" -eq 1 ] && return 0
  if [ ! -d "$HQ_ROOT/Agents" ]; then
    mkdir -p "$HQ_ROOT/Agents" 2>/dev/null || {
      as_root mkdir -p "$HQ_ROOT/Agents" </dev/null || die "could not create $HQ_ROOT/Agents"
      as_root chown "$(id -u):$(id -g)" "$HQ_ROOT" "$HQ_ROOT/Agents" </dev/null || die "could not take ownership of $HQ_ROOT"
    }
  fi
  _gsc=$(git_ssh)
  if [ -d "$CORE/.git" ]; then
    say "already cloned: updating"
    GIT_SSH_COMMAND=$_gsc git -C "$CORE" pull --ff-only </dev/null || die "git pull failed in $CORE"
  else
    GIT_SSH_COMMAND=$_gsc git clone "$GH_REPO_SSH" "$CORE" </dev/null \
      || die "git clone failed. If it says 'Permission denied (publickey)', the hub registered no deploy key for this node"
  fi
  if [ ! -x "$CORE/.venv/bin/python" ]; then
    "$PY" -m venv "$CORE/.venv" </dev/null || die "python -m venv failed"
  fi
  "$CORE/.venv/bin/python" -m pip install -q -r "$CORE/requirements.txt" </dev/null || die "pip install -r requirements.txt failed"
}

# ---------------------------------------------------------------- 8: identity + node.yaml

yq() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/''/g")"; }

write_node_yaml() {
  _f=$CONF_DIR/node.yaml
  if [ -f "$_f" ] && ! grep -Eq "^host: '?$HOST'?\$" "$_f"; then
    die "$_f already names another host; remove it if this machine really is $HOST"
  fi
  { printf 'host: %s\n' "$(yq "$HOST")"; printf 'os: %s\n' "$OS"; printf 'hq_root: %s\n' "$(yq "$HQ_ROOT")"; } > "$_f.tmp" \
    || die "could not write $_f"
  mv "$_f.tmp" "$_f" || die "could not write $_f"
}

do_identity() {
  step 8 "open the sealed identity, save it under /etc/infisical, write node.yaml"
  say "age -d -i $AGE_ID | (json: client_id, client_secret) | $(root_prefix)python3 tools/infisical_setup.py save $HOST --stdin"
  say "the plaintext only ever flows through those pipes"
  say "node.yaml: host, os, hq_root -> $CONF_DIR/node.yaml (where lib/config.py reads it)"
  [ "$DRY_RUN" -eq 1 ] && return 0
  [ "$(id -u)" -eq 0 ] || sudo -v || die "sudo did not accept the password"
  # No pipefail in sh: if age or the extractor fails, `save` reads nothing (or a login that
  # fails) and exits non-zero itself ("empty input" / "login failed"), so the status of the
  # last stage is the status of the whole.
  printf '%s\n' "$CIPHER" \
    | age -d -i "$AGE_ID" \
    | "$PY" -c 'import json, sys
d = json.load(sys.stdin)
print(d["client_id"])
print(d["client_secret"])' 2>/dev/null \
    | as_root "$PY" "$CORE/tools/infisical_setup.py" save "$HOST" --stdin \
    || die "could not save the node's identity (the decrypt, the parse or the Infisical login failed; nothing was stored)"
  CIPHER=""
  write_node_yaml
}

# ---------------------------------------------------------------- 9: probe

# Returns 0 when the probe passed, 1 when it did not. Not fatal: by now the node IS joined and
# its identity is saved, and the probe's own message says what is left to fix.
do_probe() {
  step 9 "probe: measure this node through its own identity"
  say "$(root_prefix)python3 tools/infisical_setup.py run Agents-Core prod --as $HOST -- .venv/bin/python -m tools.node_dispatch probe"
  [ "$DRY_RUN" -eq 1 ] && return 0
  # ORG_HOST is passed because under sudo the HOME is often root's, where node.yaml is not.
  # The probe's stderr is left on the terminal; only its one JSON line is read.
  _res=$(cd "$CORE" && as_root env ORG_HOST="$HOST" PYTHONDONTWRITEBYTECODE=1 "$PY" tools/infisical_setup.py run Agents-Core prod --as "$HOST" \
    -- "$CORE/.venv/bin/python" -m tools.node_dispatch probe </dev/null) || true
  printf '%s\n' "$_res" | "$PY" -c 'import json, sys
last = [l for l in sys.stdin.read().splitlines() if l.strip()][-1:]
try:
    d = json.loads(last[0])
except Exception:
    print("probe: FAILED: no JSON answer (see the messages above)")
    sys.exit(1)
if d.get("ok"):
    r = d.get("result", {})
    print("probe: ok host=%s os=%s free_gb=%s runners=%s" % (r.get("host"), r.get("os"), r.get("free_gb"), r.get("runners")))
else:
    print("probe: FAILED: %s" % str(d.get("error"))[:300])
    sys.exit(1)'
}

# ---------------------------------------------------------------- main

finish() {
  printf '\n'
  if [ "$DRY_RUN" -eq 1 ]; then
    printf 'join: dry run finished. Nothing was changed.\n'
    return 0
  fi
  if [ "$1" -eq 0 ]; then
    printf 'join: %s is a node.\n' "$HOST"
  else
    printf 'join: %s is joined and its identity is saved, but the probe did not pass (above).\n' "$HOST"
  fi
  say "dispatch public key (for the ssh mesh, W2.8): $DISPATCH_KEY.pub"
  say "claude: nothing to sign in to here. The node reads CLAUDE_CODE_OAUTH_TOKEN at run time through"
  say "  infisical_setup.py run Agents-Core prod --as $HOST -- <command>   (once the CEO has put it there)"
}

main() {
  parse_args "$@"
  check_args
  banner
  do_install
  do_keys
  do_accept
  do_tailscale
  do_wait_sealed
  do_clone
  do_identity
  _probe=0
  do_probe || _probe=1
  finish "$_probe"
  # 0 = a node; 2 = joined, probe failed; 1 (die) = stopped before the node existed
  [ "$_probe" -eq 0 ] || exit 2
}

# ORG_JOIN_LIB=1 lets tests source this file and call one step at a time. A real run never sets it.
if [ "${ORG_JOIN_LIB:-}" != 1 ]; then
  main "$@"
  exit $?
fi
