#!/usr/bin/env bash
# scripts/mac_restore.sh — ordered, idempotent, registry-driven restore verb for the Mac
# (ADR 0031, IRON §58, config/machine-contract.yaml, docs/ops/briefs/machine-contract-phase3-restore.md).
# Written on Contabo, where there is no macOS to test against — run for real only on the
# Mac, by the Mac CTO (config/machine-contract.yaml machines.mac.run_by). Same shape as
# scripts/contabo_restore.sh: numbered [n/N] steps, human-only steps marked "HUMAN:" (also
# marked in docs/ops/machine-contract-restore-runbook.md), input = the output of
# scripts/mac_blueprint.sh committed at state/mac-blueprint-<date>/ (latest one used).
#
# Usage:
#   bash scripts/mac_restore.sh --dry-run     # print every command; execute NOTHING that
#                                               # changes state. Safe on ANY box, any OS —
#                                               # this is what Contabo's own verification runs.
#   bash scripts/mac_restore.sh                 # real run — Mac (Darwin) ONLY, refuses
#                                               # otherwise. Idempotent: safe to re-run.
#
# Refuses a real (non---dry-run) run anywhere that is not Darwin, so a stray invocation on
# Contabo/winbox cannot half-execute Darwin-only commands (brew/launchctl/defaults) that do
# not exist there — same guard idiom as scripts/mac_blueprint.sh.
#
# Overridable via env (tests use this; a real run should never need to):
#   HOME_HQ   default $HOME/MoonieXHQ
#   CORE      default $HOME_HQ/Agents/Core

set -uo pipefail

TOTAL=8
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

if [ "$DRY_RUN" -eq 0 ] && [ "$(uname -s)" != "Darwin" ]; then
  echo "mac_restore.sh: refusing -- this is not macOS (uname -s = $(uname -s))." >&2
  echo "Run this only on the Mac (as the Mac CTO), or pass --dry-run to preview it anywhere." >&2
  exit 1
fi

HOME_HQ="${HOME_HQ:-$HOME/MoonieXHQ}"
CORE="${CORE:-$HOME_HQ/Agents/Core}"

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
# cmd_sh: same as cmd, for a command that needs shell features (pipes, subshells) that a
# plain argv array cannot express.
cmd_sh() {
  printf '    $ %s\n' "$1"
  if [ "$DRY_RUN" -eq 0 ]; then
    bash -c "$1" || { printf '    ! FAILED: %s\n' "$1"; PASS=0; }
  fi
}

# Latest committed capture (may be empty on a box with no blueprint yet — every step
# below degrades gracefully, printing a WARN instead of crashing under set -u).
BLUEPRINT_DIR=$(ls -d "$CORE"/state/mac-blueprint-*/ 2>/dev/null | sort | tail -1)
BLUEPRINT_DIR="${BLUEPRINT_DIR%/}"

# ================================================================ 1/8 — preflight
hdr "preflight: Darwin, disk, Homebrew, git"
say "uname -s: $(uname -s)"
FREE_KB=$(df -Pk / 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "${FREE_KB:-}" ]; then
  FREE_GB=$((FREE_KB / 1024 / 1024))
  say "disk free on /: ${FREE_GB} GB"
  if [ "$FREE_GB" -lt 10 ]; then
    say "WARN: under 10 GB free — repos + Homebrew casks need room; free space before continuing."
  fi
fi

if command -v brew >/dev/null 2>&1; then
  say "brew: present ($(command -v brew))"
else
  cmd_sh '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
fi
if command -v git >/dev/null 2>&1; then
  say "git: present ($(command -v git))"
else
  cmd brew install git
fi

# ============================== 2/8 — clone MoonieXHQ + Agents-{Core,Rules,Wikis,Memory}
hdr "clone MoonieXHQ + Agents-{Core,Rules,Wikis,Memory}"
if [ -d "$HOME_HQ/.git" ]; then
  say "$HOME_HQ already a git checkout — skip clone (idempotent)"
else
  cmd git clone git@github.com:PASAKON/MoonieX-HQ.git "$HOME_HQ"
fi
for pair in "Agents/Core:Agents-Core" "Agents/Rules:Agents-Rules" "Agents/Wikis:Agents-Wikis" "Agents/Memory:Agents-Memory"; do
  sub="${pair%%:*}"
  repo="${pair##*:}"
  dst="$HOME_HQ/$sub"
  if [ -d "$dst/.git" ]; then
    say "$dst already a git checkout — skip clone (idempotent)"
  else
    cmd git clone "git@github.com:PASAKON/$repo.git" "$dst"
  fi
done
say "unlike Contabo, the Mac IS the source of truth for Agents/Rules + Agents/Wikis (hq.yaml"
say "current: paths) — they are cloned here, not rsync'd."

# ==================================================== 3/8 — Homebrew bundle
hdr "Homebrew bundle from the captured Brewfile"
if [ -n "$BLUEPRINT_DIR" ]; then
  say "using blueprint: $BLUEPRINT_DIR"
else
  say "WARN: no state/mac-blueprint-<date>/ found under $CORE yet — run scripts/mac_blueprint.sh"
  say "on this Mac first (or wait for step 2's clone to land it). Blueprint-driven parts below are skipped."
fi
if [ -n "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/Brewfile" ]; then
  cmd brew bundle --file="$BLUEPRINT_DIR/Brewfile"
else
  say "WARN: no Brewfile in the latest blueprint — skipping"
fi

# ============================ 4/8 — LaunchAgents (HUMAN: redacted values)
hdr "LaunchAgents: copy, load (HUMAN: fill redacted values first)"
if [ -n "$BLUEPRINT_DIR" ] && [ -d "$BLUEPRINT_DIR/LaunchAgents" ]; then
  PLIST_FILES=$(find "$BLUEPRINT_DIR/LaunchAgents" -maxdepth 1 -name '*.plist' | sort)
  if [ -z "$PLIST_FILES" ]; then
    say "LaunchAgents/ is empty in the latest blueprint — nothing to copy"
  fi
  cmd mkdir -p "$HOME/Library/LaunchAgents"
  for f in $PLIST_FILES; do
    plist_name=$(basename "$f")
    cmd cp -p "$f" "$HOME/Library/LaunchAgents/$plist_name"
    if grep -q '<redacted>' "$f" 2>/dev/null; then
      human "$plist_name has <redacted> value(s) — hand-fill the real value in ~/Library/LaunchAgents/$plist_name before loading it."
    else
      cmd launchctl load "$HOME/Library/LaunchAgents/$plist_name"
    fi
  done
else
  say "WARN: no state/mac-blueprint-<date>/LaunchAgents/ found — skipping"
fi

# ================================================================ 5/8 — Tailscale
hdr "Tailscale (HUMAN: login click)"
if command -v tailscale >/dev/null 2>&1; then
  say "tailscale: present ($(command -v tailscale))"
else
  cmd brew install tailscale
fi
human "'tailscale up' below opens a login prompt — sign in as pass.gob1@gmail.com and approve this machine. The script blocks until that happens."
cmd tailscale up

# ============================ 6/8 — Claude Code
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
human "re-trust $CORE in Claude Code (accept the folder-trust dialog / hasTrustDialogAccepted) — required before hooks/skills run; cannot be automated."

# ============================ 7/8 — secrets
hdr "secrets: print locations only (HUMAN: fetch the bundle by hand)"
say "config/machine-contract.yaml CONFIG rows this machine cannot self-restore (secrets bundle):"
say '  $HOME/.config/mooniex/**                    (app secrets — never Drive)'
say '  $HOME/Library/LaunchAgents/com.gob.*.plist  (secret <string> values flagged in step 4)'
human "fetch the mac-secrets bundle from Contabo's Archive/ at 0600 (e.g. mooniex-vps:/opt/MoonieXHQ/Archive/mac-secrets-<date>/), then copy each file into place by hand. Never put secrets on Drive; never let this script fetch them."

# ============================ 8/8 — verify
hdr "verify: machine_doctor, hq.py doctor, PASS/FAIL + drill template"
cmd "$CORE/.venv/bin/python3" "$CORE/tools/machine_doctor.py" --machine mac check
cmd "$CORE/.venv/bin/python3" "$HOME_HQ/scripts/hq.py" doctor

if [ "$PASS" -eq 1 ]; then
  printf '\n[SUMMARY] PASS — no step above recorded a failure (dry-run=%s)\n' "$([ "$DRY_RUN" -eq 1 ] && echo yes || echo no)"
else
  printf '\n[SUMMARY] FAIL — see the "! FAILED" lines above\n'
fi

say "fill and append this line to state/re-os-drills.jsonl once the drill is scored (the Mac's real wipe is drill #2 — ADR 0031):"
say '  {"date": "<YYYY-MM-DD>", "machine": "mac", "kind": "real|rehearsed", "scope": "<what was covered>", "result": "PASS|FAIL|PASS-with-known-loss", "minutes_to_remote_access": <n>, "minutes_to_org_restore": <n>, "bytes_from_git_mb": <n>, "bytes_from_drive_mb": <n>, "irreplaceable_lost_gb": <n>, "human_steps": ["..."], "gaps_found": ["..."], "by": "<session-id>", "ref": "docs/ops/machine-contract-restore-runbook.md"}'

if [ "$DRY_RUN" -eq 1 ]; then
  exit 0
fi
if [ "$PASS" -eq 1 ]; then
  exit 0
else
  exit 1
fi
