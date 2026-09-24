#!/usr/bin/env bash
# scripts/contabo_restore.sh — ordered, idempotent, registry-driven restore verb for a
# FRESH Debian/Ubuntu Contabo VPS (ADR 0031, IRON §58, config/machine-contract.yaml,
# docs/ops/briefs/machine-contract-phase3-restore.md, docs/ops/machine-contract-plan-2026-09-24.md).
#
# Input = the output of scripts/contabo_blueprint.sh, committed at
# state/contabo-blueprint-<date>/ (the latest one found is used), plus
# config/machine-contract.yaml (the registry — read as documentation here, never edited)
# and hq.yaml (the HQ folder map, cloned in step 2). Every step is numbered [n/N] and
# runs in order; a step that needs a human hand (a login, an external Drive/secrets
# fetch this script must never automate) prints a line starting with "HUMAN:" — the
# same steps are marked HUMAN in docs/ops/machine-contract-restore-runbook.md.
#
# Usage:
#   bash scripts/contabo_restore.sh --dry-run     # print every command; execute NOTHING
#                                                   # that changes state. Safe anywhere,
#                                                   # any user, any OS.
#   bash scripts/contabo_restore.sh                 # real run — FRESH Debian/Ubuntu VPS,
#                                                   # root, ONLY. Idempotent: safe to
#                                                   # re-run after a partial/failed pass.
#
# This file is meant to reach a brand-new VPS BEFORE Agents/Core is cloned onto it (copy
# it over by hand, scp, or curl the raw GitHub blob to e.g. /root/contabo_restore.sh) —
# step 2 clones the org repos; every step after that reads from the now-checked-out copy
# at $CORE ($HQ_ROOT/Agents/Core). Never touches Drive, docker, systemd state beyond
# `enable` (never `start`), crontab (without asking), secrets, or another machine — see
# "Not in scope" in the brief.
#
# Overridable via env (tests use this; a real run should never need to):
#   HQ_ROOT   default /opt/MoonieXHQ
#   CORE      default $HQ_ROOT/Agents/Core

set -uo pipefail

TOTAL=9
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

HQ_ROOT="${HQ_ROOT:-/opt/MoonieXHQ}"
CORE="${CORE:-$HQ_ROOT/Agents/Core}"

STEP_NUM=0
PASS=1

hdr() { STEP_NUM=$((STEP_NUM + 1)); printf '\n[%s/%s] %s\n' "$STEP_NUM" "$TOTAL" "$1"; }
say() { printf '    %s\n' "$*"; }
human() { printf '    HUMAN: %s\n' "$*"; }
# cmd: print the argv command, execute it only outside --dry-run (state-changing steps).
cmd() {
  printf '    $ %s\n' "$*"
  if [ "$DRY_RUN" -eq 0 ]; then
    "$@" || { printf '    ! FAILED: %s\n' "$*"; PASS=0; }
  fi
}
# cmd_sh: same as cmd, for a command that needs shell features (pipes, subshells) that
# a plain argv array cannot express.
cmd_sh() {
  printf '    $ %s\n' "$1"
  if [ "$DRY_RUN" -eq 0 ]; then
    bash -c "$1" || { printf '    ! FAILED: %s\n' "$1"; PASS=0; }
  fi
}

# Latest committed capture (may be empty on a box with no blueprint yet — every step
# below degrades gracefully, printing a WARN instead of crashing under set -u).
BLUEPRINT_DIR=$(ls -d "$CORE"/state/contabo-blueprint-*/ 2>/dev/null | sort | tail -1)
BLUEPRINT_DIR="${BLUEPRINT_DIR%/}"

# ============================================================ 1/9 — preflight
hdr "preflight: root, disk, packages, Tailscale (HUMAN: tailscale login)"
if [ "$(id -u)" -ne 0 ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    say "NOTE: not running as root right now (fine for --dry-run; a real run needs root)."
  else
    say "FATAL: this must run as root on the fresh VPS (apt/systemctl/docker all need it)."
    printf '\n[SUMMARY] FAIL — not root; nothing else attempted\n'
    exit 1
  fi
else
  say "root: OK (uid 0)"
fi

FREE_KB=$(df -Pk / 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "${FREE_KB:-}" ]; then
  FREE_GB=$((FREE_KB / 1024 / 1024))
  say "disk free on /: ${FREE_GB} GB"
  if [ "$FREE_GB" -lt 10 ]; then
    say "WARN: under 10 GB free — repos + venv + docker images need room; free space before continuing."
  fi
fi

cmd apt-get update
cmd apt-get install -y git curl ca-certificates python3 python3-venv python3-pip python3-yaml
if command -v docker >/dev/null 2>&1; then
  say "docker: present ($(command -v docker))"
else
  cmd_sh "curl -fsSL https://get.docker.com | sh"
fi

if command -v tailscale >/dev/null 2>&1; then
  say "tailscale: present ($(command -v tailscale))"
else
  cmd_sh "curl -fsSL https://tailscale.com/install.sh | sh"
fi
say "the captured apt BOM is replayed in step 2, once the Agents-Core clone (which carries it) exists"
human "'tailscale up' below prints a login URL — open it, sign in as pass.gob1@gmail.com and approve this machine. The script blocks until that happens."
cmd tailscale up

# ============================================= 2/9 — clone HQ + Agents-* repos
hdr "clone PASAKON/MoonieX-HQ + Agents-* (HUMAN: Rules/Wikis rsync runs on the Mac)"
# RESTORE_GIT_BASE lets a rehearsal (re-OS drill in a throwaway container/VM, ADR 0031) clone from
# local bare mirrors — e.g. RESTORE_GIT_BASE=/hqmirror/ with MoonieX-HQ.git, Agents-Core.git,
# Agents-Memory.git inside — instead of GitHub, which needs this box's deploy key. Default = GitHub.
GIT_BASE="${RESTORE_GIT_BASE:-git@github.com:PASAKON/}"
if [ -d "$HQ_ROOT/.git" ]; then
  say "$HQ_ROOT already a git checkout — skip clone (idempotent)"
else
  cmd git clone "${GIT_BASE}MoonieX-HQ.git" "$HQ_ROOT"
fi
if [ -d "$CORE/.git" ]; then
  say "$CORE already a git checkout — skip clone (idempotent)"
else
  cmd git clone "${GIT_BASE}Agents-Core.git" "$CORE"
fi
MEMORY_DIR="$HQ_ROOT/Agents/Memory"
if [ -d "$MEMORY_DIR/.git" ]; then
  say "$MEMORY_DIR already a git checkout — skip clone (idempotent)"
else
  cmd git clone "${GIT_BASE}Agents-Memory.git" "$MEMORY_DIR"
fi
say "Agents/Rules and Agents/Wikis are NOT cloned on Contabo — they are rsync snapshots"
say "pulled FROM the Mac (CLAUDE.md § Wiki access), read-only here."
human "run these two commands FROM THE MAC (not on this box) to (re-)populate them:"
say '  rsync -aH --delete --exclude '"'"'.git/'"'"' /Users/gob/MoonieXHQ/Agents/Wikis/         mooniex-vps:'"$HQ_ROOT"'/Agents/Wikis/'
say '  rsync -aH --delete --exclude '"'"'.git/'"'"' /Users/gob/MoonieXHQ/Agents/Rules/ mooniex-vps:'"$HQ_ROOT"'/Agents/Rules/'
# The blueprint lives INSIDE Agents-Core, so it only exists from this point on: resolve it now
# (the top-of-file lookup ran before the clone and was empty on a fresh box — found by the first
# container drill, 2026-09-24) and replay the apt BOM here. It runs AFTER the docker/tailscale
# installers of step 1 because those add the apt repos docker-ce / tailscale come from.
BLUEPRINT_DIR=$(ls -d "$CORE"/state/contabo-blueprint-*/ 2>/dev/null | sort | tail -1)
BLUEPRINT_DIR="${BLUEPRINT_DIR%/}"
if [ -n "$BLUEPRINT_DIR" ] && [ -s "$BLUEPRINT_DIR/apt-packages.txt" ]; then
  say "blueprint on disk: $BLUEPRINT_DIR"
  # captured OS vs this OS: the BOM is only exact on the same release (Ubuntu 24.04 on 2026-09-24)
  CAPTURED_OS=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("os") or d.get("pretty_name") or "")' "$BLUEPRINT_DIR/machine.json" 2>/dev/null || true)
  THIS_OS=$(. /etc/os-release 2>/dev/null && printf '%s' "${PRETTY_NAME:-}")
  say "captured OS: ${CAPTURED_OS:-?}  |  this OS: ${THIS_OS:-?}"
  [ -n "$CAPTURED_OS" ] && [ -n "$THIS_OS" ] && [ "$CAPTURED_OS" != "$THIS_OS" ] && say "WARN: different release — package names/versions may not match (drill run 2 on debian:12 lost 5 Ubuntu-only names + numpy for python 3.11)"
  # foreign architectures first (wine32:i386 needs i386 enabled or apt cannot even locate it)
  if [ -s "$BLUEPRINT_DIR/foreign-archs.txt" ]; then
    while read -r arch; do [ -n "$arch" ] && cmd dpkg --add-architecture "$arch"; done < "$BLUEPRINT_DIR/foreign-archs.txt"
    cmd apt-get update
  fi
  # replay only what THIS release can locate; a single unknown name makes `apt-get install` refuse the
  # whole list (found by drill run 2), so split the BOM into available / missing and report the misses.
  APT_AVAIL=""; APT_MISSING=""
  while read -r pkg; do
    [ -n "$pkg" ] || continue
    # apt-cache show does not take the "name:arch" form (wine32:i386 was reported missing on run 3
    # although the i386 index was there) — check the bare name, install the captured form.
    if apt-cache show "${pkg%%:*}" >/dev/null 2>&1; then APT_AVAIL="$APT_AVAIL $pkg"; else APT_MISSING="$APT_MISSING $pkg"; fi
  done < "$BLUEPRINT_DIR/apt-packages.txt"
  say "replaying $(echo $APT_AVAIL | wc -w) of $(grep -c . "$BLUEPRINT_DIR/apt-packages.txt") manually-installed apt packages (captured apt-mark showmanual)"
  [ -n "$APT_MISSING" ] && say "WARN: not available on this release, skipped:$APT_MISSING"
  [ -n "$APT_AVAIL" ] && cmd_sh "apt-get install -y$APT_AVAIL"
else
  say "WARN: no state/contabo-blueprint-<date>/apt-packages.txt after the clone — only step 1's base packages are installed"
fi
# 2b. every other HQ repo that lives on this box: hq.yaml rows with `repo:` and a `machines.contabo`
# path (2026-09-24: Projects/MoonieX/{ClaudeFlow,Console,AlphaTrader,Option,LineAutomation},
# Projects/LungNote/Mcp). Agents/Rules + Wikis are rsync snapshots (above); Core + Memory are already
# cloned. A contabo path string may carry a note in parentheses — its first token is the path. Found
# missing by the first container drill (hq.py doctor listed every Projects/* row as absent).
if [ -f "$HQ_ROOT/hq.yaml" ] && python3 -c 'import yaml' 2>/dev/null; then
  HQ_REPO_LIST=$(python3 - "$HQ_ROOT/hq.yaml" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
for r in d.get("folders") or []:
    m = r.get("machines") or {}
    raw = str(m.get("contabo") or "")
    p = raw.split()[0] if raw else ""
    if r.get("repo") and p and "snapshot" not in raw and r["path"] not in ("Agents/Core", "Agents/Memory", "Agents/Rules", "Agents/Wikis"):
        print(r["repo"], p)
PY
)
  while read -r repo dest; do
    [ -n "$repo" ] || continue
    if [ -d "$dest/.git" ]; then
      say "$dest already a git checkout — skip clone (idempotent)"
    elif [ -n "${RESTORE_GIT_BASE:-}" ] && [ -d "$RESTORE_GIT_BASE" ] && [ ! -d "${RESTORE_GIT_BASE}${repo##*/}.git" ]; then
      say "rehearsal: no local mirror for $repo — skipped ($dest)"
    else
      cmd git clone "${GIT_BASE}${repo##*/}.git" "$dest"
    fi
  done <<< "$HQ_REPO_LIST"
  say "each deployed project's .env comes from the secrets bundle (step 8), never from git"
else
  say "WARN: hq.yaml or python3-yaml missing — the Projects/* repos of this box were not cloned (hq.yaml rows with a contabo path)"
fi

# ==================================== 3/9 — Python venv, Node 22, npm globals
hdr "Python venv, Node 22, npm globals"
if [ -n "$BLUEPRINT_DIR" ]; then
  say "using blueprint: $BLUEPRINT_DIR"
else
  say "WARN: no state/contabo-blueprint-<date>/ found under $CORE yet — run scripts/contabo_blueprint.sh"
  say "on a live box first (or wait for step 2's clone to land it). Blueprint-driven parts below are skipped."
fi

if [ -f "$CORE/requirements.txt" ]; then
  cmd python3 -m venv "$CORE/.venv"
  cmd "$CORE/.venv/bin/pip" install -r "$CORE/requirements.txt"
else
  say "WARN: $CORE/requirements.txt not present yet — step 2 must complete first"
fi

if [ -n "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/pip-freeze-idm-venv.txt" ]; then
  cmd python3 -m venv /root/idm-venv
  # torch==x.y.z+cpu (and friends) only exist on PyTorch's own index; pip on PyPI alone fails the whole
  # file (drill run 2). numpy/torch pins are also python-version-bound: same release as the capture.
  IDM_EXTRA=""; grep -q "+cpu" "$BLUEPRINT_DIR/pip-freeze-idm-venv.txt" && IDM_EXTRA=" --extra-index-url https://download.pytorch.org/whl/cpu"
  cmd_sh "/root/idm-venv/bin/pip install -r '$BLUEPRINT_DIR/pip-freeze-idm-venv.txt'$IDM_EXTRA"
else
  say "no pip-freeze-idm-venv.txt in the latest blueprint — /root/idm-venv skipped (brief: only if that file exists)"
fi

NODE_VERSION="22.11.0"  # bump when a newer 22.x LTS ships: https://nodejs.org/en/download
NODE_TARBALL="node-v${NODE_VERSION}-linux-x64.tar.xz"
if [ -n "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/node-version.txt" ]; then
  say "previously captured node: $(cat "$BLUEPRINT_DIR/node-version.txt")"
fi
say "Node ${NODE_VERSION} tarball -> /opt/node-v22"
cmd_sh "curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/${NODE_TARBALL} -o /tmp/${NODE_TARBALL} && mkdir -p /opt/node-v22 && tar -xJf /tmp/${NODE_TARBALL} -C /opt/node-v22 --strip-components=1 && ln -sf /opt/node-v22/bin/node /usr/local/bin/node && ln -sf /opt/node-v22/bin/npm /usr/local/bin/npm"

if [ -n "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/npm-global.txt" ]; then
  NPM_PKGS=$(grep -oE '[A-Za-z0-9@/_.-]+@[0-9][A-Za-z0-9.+-]*' "$BLUEPRINT_DIR/npm-global.txt" | grep -Ev '^(npm|corepack)@' || true)
  if [ -n "$NPM_PKGS" ]; then
    for pkg in $NPM_PKGS; do
      cmd /opt/node-v22/bin/npm install -g "$pkg"
    done
  else
    say "npm-global.txt had nothing to reinstall beyond npm/corepack (bundled with Node)"
  fi
else
  say "no npm-global.txt in the latest blueprint — skipping npm globals"
fi

# ========================================== 4/9 — systemd units (never start)
hdr "systemd units: copy, enable, never start (HUMAN: EnvironmentFile from secrets bundle)"
if [ -n "$BLUEPRINT_DIR" ] && [ -d "$BLUEPRINT_DIR/systemd-mooniex-units" ]; then
  UNIT_FILES=$(find "$BLUEPRINT_DIR/systemd-mooniex-units" -maxdepth 1 -type f | sort)
  if [ -z "$UNIT_FILES" ]; then
    say "systemd-mooniex-units/ is empty in the latest blueprint — nothing to copy"
  fi
  for f in $UNIT_FILES; do
    cmd cp -p "$f" /etc/systemd/system/
  done
  cmd systemctl daemon-reload
  for f in $UNIT_FILES; do
    unit_name=$(basename "$f")
    case "$unit_name" in
      *.service | *.timer) cmd systemctl enable "$unit_name" ;;
    esac
  done
  for f in $UNIT_FILES; do
    envfile=$(grep -h '^EnvironmentFile=' "$f" 2>/dev/null | sed -e 's/^EnvironmentFile=-\{0,1\}//')
    if [ -n "$envfile" ]; then
      human "$(basename "$f") needs $envfile from the secrets bundle (step 8) before you start it."
    fi
  done
else
  say "WARN: no systemd-mooniex-units/ in the latest blueprint — skipping"
fi

# =================================== 5/9 — crontab (print, ask before install)
hdr "crontab: print, ask before installing (HUMAN: confirm before install)"
if [ -n "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/crontab-root.txt" ]; then
  say "captured root crontab ($BLUEPRINT_DIR/crontab-root.txt):"
  while IFS= read -r line; do say "  | $line"; done <"$BLUEPRINT_DIR/crontab-root.txt"
  human "review the crontab above before it is installed — nothing is installed without a yes."
  if [ "$DRY_RUN" -eq 1 ]; then
    say "\$ crontab $BLUEPRINT_DIR/crontab-root.txt   (only after a human says yes)"
  else
    printf '    Install this crontab now? [y/N] '
    read -r ans || ans="n"
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
      cmd crontab "$BLUEPRINT_DIR/crontab-root.txt"
    else
      say "skipped — crontab not installed"
    fi
  fi
else
  say "WARN: no crontab-root.txt in the latest blueprint — skipping"
fi

# ============================= 6/9 — Docker: compose pull/build; volume lines
hdr "Docker: compose pull/build, no up (HUMAN: volume tars come from Drive)"
if [ -n "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/docker-compose-files.txt" ]; then
  while IFS= read -r cf; do
    [ -z "$cf" ] && continue
    if [ -f "$cf" ]; then
      cmd docker compose -f "$cf" pull
      cmd docker compose -f "$cf" build
    else
      say "skip (not present on this box yet): $cf"
    fi
  done <"$BLUEPRINT_DIR/docker-compose-files.txt"
else
  say "WARN: no docker-compose-files.txt in the latest blueprint — skipping compose pull/build"
fi

human "the volume tars/dumps below come from Drive via winbox's rclone or the Mac bridge — this script never fetches them."
say "n8n_data (IRREPLACEABLE — workflows/creds/executions), from Drive BACKUP/MoonieX HQ/Docker-Volumes/contabo/n8n_data/<date>.tar:"
say '  $ docker volume create n8n_data'
say '  $ docker run --rm -i -v n8n_data:/data alpine sh -c "cd /data && tar xf -" < n8n_data-<date>.tar   # plain tar, as tools/drive_leg.py docker-volumes writes it'
say '  $ # the tar EXCLUDES /data/config (n8n encryptionKey = a secret): restore that one file from the secrets bundle (step 8), chmod 600, owner uid 1000'
say '  $ docker run --rm -v n8n_data:/data alpine cat /data/config   # sanity: encryptionKey must be present'
say "org-pgdata (IRREPLACEABLE — org coordination DB), from Drive BACKUP/MoonieX HQ/Docker-Volumes/contabo/org-pgdata/<date>.sql.gz:"
say '  $ docker volume create org-pgdata'
say '  $ gunzip -c org-pgdata-<date>.sql.gz | docker exec -i org-postgres psql -U org -d org   # pg_dumpall output; container org-postgres (postgres:16), superuser org (POSTGRES_USER), no "postgres" role — measured 2026-09-24'

# ====================================================== 7/9 — Claude Code
hdr "Claude Code: install, claude-home symlinks (HUMAN: login + re-trust)"
if command -v claude >/dev/null 2>&1; then
  say "claude: present ($(command -v claude))"
else
  cmd_sh "curl -fsSL https://claude.ai/install.sh | bash"
fi
human "run 'claude' and complete login interactively — this script does not automate it."

CCD="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
say "claude-home symlinks (scripts/claude_home_migrate.py pattern — repo is the source, \$CLAUDE_CONFIG_DIR gets the links):"
for entry in CLAUDE.md settings.json hooks commands mcp/mooniex-coord tools; do
  cmd mkdir -p "$(dirname "$CCD/$entry")"
  cmd ln -sfn "$CORE/claude-home/$entry" "$CCD/$entry"
done
if [ -d "$CORE/.claude/skills" ]; then
  cmd mkdir -p "$CCD/skills"
  for d in "$CORE/.claude/skills"/*/; do
    [ -d "$d" ] || continue
    skill_name=$(basename "$d")
    cmd ln -sfn "$CORE/.claude/skills/$skill_name" "$CCD/skills/$skill_name"
  done
else
  say "no $CORE/.claude/skills yet (step 2 must complete first) — skills symlinks skipped"
fi
say "per-project memory follows the same pattern once a project's slug exists: git clone"
say "PASAKON/Agents-Memory into $MEMORY_DIR (done in step 2), then symlink each"
say "\$CLAUDE_CONFIG_DIR/projects/<slug>/memory the same way (claude_home_migrate.py _legacy_memory())."
human "re-trust $CORE in Claude Code (accept the folder-trust dialog / hasTrustDialogAccepted) — required before hooks/skills run; cannot be automated."

# ============================================================ 8/9 — secrets
hdr "secrets: print locations only (HUMAN: fetch the bundle by hand)"
say "config/machine-contract.yaml CONFIG rows this machine cannot self-restore (secrets bundle):"
say "  /root/.ssh/**                    (private keys — the blueprint only carries the public half)"
say "  /root/.acme.sh/**                (Let's Encrypt account key + certs)"
say "  /home/secretary/.secretary.env   (OpenRouter key etc.)"
say "  unit EnvironmentFiles            (see each unit's HUMAN line in step 4, read live from the blueprint)"
human "fetch the bundle from another machine's Archive/ at 0600 — e.g. <mac-or-other-box>:$HQ_ROOT/Archive/contabo-secrets-<date>/ — then copy each file into place by hand and chmod 600. Never put secrets on Drive; never let this script fetch them."

# ====================================================== 9/9 — verify
hdr "verify: machine_doctor, hq.py doctor, unit-files, PASS/FAIL + drill template"
cmd "$CORE/.venv/bin/python3" "$CORE/tools/machine_doctor.py" --machine contabo check
# hq.py doctor is written against the Mac's `current:` paths (44 findings on the LIVE Contabo box on
# 2026-09-24, so a fresh one can only match that) — here it is information, never the gate.
say "\$ $CORE/.venv/bin/python3 $HQ_ROOT/scripts/hq.py doctor   (informational on Contabo: the map is Mac-centric)"
if [ "$DRY_RUN" -eq 0 ]; then "$CORE/.venv/bin/python3" "$HQ_ROOT/scripts/hq.py" doctor 2>&1 | tail -2 | sed 's/^/      /'; fi
cmd systemctl list-unit-files "mooniex-*"

if [ "$PASS" -eq 1 ]; then
  printf '\n[SUMMARY] PASS — no step above recorded a failure (dry-run=%s)\n' "$([ "$DRY_RUN" -eq 1 ] && echo yes || echo no)"
else
  printf '\n[SUMMARY] FAIL — see the "! FAILED" lines above\n'
fi

say "fill and append this line to state/re-os-drills.jsonl once the drill is scored (state/re-os-drills.jsonl already has the winbox 2026-09-24 example):"
say '  {"date": "<YYYY-MM-DD>", "machine": "contabo", "kind": "real|rehearsed", "scope": "<what was covered>", "result": "PASS|FAIL|PASS-with-known-loss", "minutes_to_remote_access": <n>, "minutes_to_org_restore": <n>, "bytes_from_git_mb": <n>, "bytes_from_drive_mb": <n>, "irreplaceable_lost_gb": <n>, "human_steps": ["..."], "gaps_found": ["..."], "by": "<session-id>", "ref": "docs/ops/machine-contract-restore-runbook.md"}'

# --dry-run never runs a state-changing command, so PASS is always still 1 here —
# exit 0 always. A real run's exit code reflects whether any "$ ..." command failed.
if [ "$DRY_RUN" -eq 1 ]; then
  exit 0
fi
if [ "$PASS" -eq 1 ]; then
  exit 0
else
  exit 1
fi
