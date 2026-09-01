#!/bin/sh
# scripts/install-git-hooks.sh -- writes/updates the repo's git pre-commit
# hook. `.git/hooks/` is NOT tracked by git (task-d3df329f: "load-bearing
# files silently untracked" -- exactly this class of bug), so on a fresh
# clone nothing lives there until this script runs once. This script is the
# tracked source of truth; the hook it writes is disposable and regenerable.
#
# Idempotent: each stanza is guarded by a unique marker so re-running never
# duplicates it. Safe to run from the main checkout or any worktree -- both
# share the same common .git/hooks dir, resolved below via `git
# rev-parse --git-common-dir` rather than a hardcoded repo path (the same
# repo is /Users/gob/Projects/Agents on the Mac and /opt/mooniex-agents on
# Contabo).
#
# Install with:
#   sh scripts/install-git-hooks.sh
#
# Two stanzas land in .git/hooks/pre-commit:
#   1. gitleaks secret guard  -- matches what was already live in this repo's
#      hook (added 2026-07-20); reproduced here so it also survives a fresh
#      clone, not only the skill-lint half this task actually asked for.
#      Still BLOCKS the commit on a real finding, same as before.
#   2. skill-lint             -- ADR 0022 Wave 1. Runs scripts/skill-lint.py
#      only when staged paths touch .claude/skills/, and NEVER blocks the
#      commit regardless of what it finds (`|| true`) -- CEO decisions 4 and
#      10 forbid an authoring gate, and a blocking pre-commit hook is a gate
#      wearing a different hat.

set -eu

common_dir="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
if [ -z "$common_dir" ]; then
  # Older git without --path-format: --git-common-dir may be relative.
  raw="$(git rev-parse --git-common-dir)"
  case "$raw" in
    /*) common_dir="$raw" ;;
    *) common_dir="$(cd "$raw" && pwd)" ;;
  esac
fi

repo_root="$(dirname "$common_dir")"
hook="$common_dir/hooks/pre-commit"

mkdir -p "$common_dir/hooks"
[ -f "$hook" ] || printf '#!/bin/sh\n' > "$hook"

# Repair, every run: the hand-written hook this repo already had (added
# 2026-07-20, before this script existed) ends with a bare `exit 0`. Any
# stanza appended after that line is dead code -- git never reaches it. Drop
# a trailing standalone `exit 0` (if present) before appending anything; one
# gets re-added at the very end below so the hook still exits 0 by default.
last_line="$(tail -n 1 "$hook" 2>/dev/null || true)"
if [ "$last_line" = "exit 0" ]; then
  tmp="$(mktemp)"
  sed '$d' "$hook" > "$tmp" && mv "$tmp" "$hook"
fi

if ! grep -q -e 'BEGIN gitleaks guard' -e 'gitleaks protect --staged' "$hook" 2>/dev/null; then
  cat >> "$hook" <<'GITLEAKS_EOF'

# --- BEGIN gitleaks guard (Mooniex, added 2026-07-20; tracked via scripts/install-git-hooks.sh) ---
# `if command -v gitleaks` (not `command -v gitleaks || exit 0`): the
# original hand-written hook used the `|| exit 0` form, which was fine while
# this was the hook's only stanza but would silently skip every stanza after
# it -- skill-lint included -- on any machine without gitleaks on PATH
# (e.g. a fresh Contabo clone). Same behaviour when gitleaks IS present;
# independent of sibling stanzas when it is not.
if command -v gitleaks >/dev/null 2>&1; then
  if ! gitleaks protect --staged --redact --no-banner; then
    echo ""
    echo "gitleaks: possible secret in staged changes -- commit BLOCKED."
    echo "   - real secret?  remove it; put it in .env / Vercel env instead."
    echo "   - false positive (test fixture)?  bypass once: git commit --no-verify"
    exit 1
  fi
fi
# --- END gitleaks guard ---
GITLEAKS_EOF
  echo "installed: gitleaks guard stanza"
fi

if ! grep -q 'BEGIN skill-lint' "$hook" 2>/dev/null; then
  cat >> "$hook" <<'SKILLLINT_EOF'

# --- BEGIN skill-lint (ADR 0022 Wave 1; tracked via scripts/install-git-hooks.sh) ---
# Lint, not a gate: never blocks the commit, whatever it finds (`|| true`).
# Only runs when staged paths touch .claude/skills/.
if git diff --cached --name-only | grep -q '^\.claude/skills/'; then
  # Two different roots, deliberately not the same path:
  #   - the SCRIPT comes from the worktree actually being committed
  #     (`--show-toplevel`) -- a worktree can be on a branch whose
  #     .claude/skills/ or scripts/skill-lint.py differ from main's, and
  #     that's the content this commit is actually staging.
  #   - the INTERPRETER comes from the main checkout's .venv, which is the
  #     only place PyYAML lives -- .venv is gitignored, so it exists only
  #     wherever it was created (the main checkout), never per-worktree.
  worktree_root="$(git rev-parse --show-toplevel)"
  common_dir="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git rev-parse --git-common-dir)"
  case "$common_dir" in
    /*) : ;;
    *) common_dir="$(cd "$common_dir" && pwd)" ;;
  esac
  main_root="$(dirname "$common_dir")"
  lint_script="$worktree_root/scripts/skill-lint.py"
  # bare `python3` on PATH has no PyYAML -- only .venv does. Skip silently
  # (matching the gitleaks stanza's own `command -v` guard) if the main
  # checkout has no venv yet, or this worktree predates skill-lint.py,
  # rather than crash or fall back to a yaml-less bare python3.
  py="$main_root/.venv/bin/python"
  if [ -x "$py" ] && [ -f "$lint_script" ]; then
    "$py" "$lint_script" check || true
  fi
fi
# --- END skill-lint ---
SKILLLINT_EOF
  echo "installed: skill-lint stanza"
fi

last_line="$(tail -n 1 "$hook" 2>/dev/null || true)"
if [ "$last_line" != "exit 0" ]; then
  printf '\nexit 0\n' >> "$hook"
fi

chmod +x "$hook"
echo "pre-commit hook ready: $hook"
