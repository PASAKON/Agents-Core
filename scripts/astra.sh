#!/usr/bin/env bash
# Talk to Astra (GPT-6 Astra via Codex CLI on winbox) from a C-level session, headlessly.
#
#   scripts/astra.sh <task-file.md> [report-name]
#   scripts/astra.sh --ask "one-line question"
#
# Why this exists: Astra runs as Codex on winbox and the CEO is usually not at that
# keyboard. `codex login status` reports "Logged in using ChatGPT" and `codex exec` runs
# with `approval: never`, so no human has to click anything — but Codex must be invoked
# on that box, and the file channel in AGENTS.md assumes someone is sitting there.
#
# MEASURED LIMIT (2026-09-11, codex-cli 0.153.4): over SSH, Astra can READ the workspace
# and reply on stdout, but CANNOT WRITE files. Its sandbox helper cannot start outside an
# interactive Windows desktop session:
#     exec_command failed: timed out after 15000ms connecting runner pipe-in
#     apply patch -> Failed to write file ...
# So this script inverts the AGENTS.md channel: WE write the task file, Astra reads it,
# and WE capture its reply into REPORT-NN.md. Astra never writes. That is enough for the
# judgement role it was given (read the measurements, say which shots are wrong) and NOT
# enough for driving Resolve, which needs the desktop session anyway.
#
# Do not reach for --dangerously-bypass-approvals-and-sandbox to fix the write path
# without the CEO's say-so: it removes sandboxing entirely on that box.

set -euo pipefail

HOST="${ASTRA_HOST:-winbox}"
REMOTE_WS='C:\mooniex\astra-workspace'
LOCAL_WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs/astra-workspace"
SANDBOX="${ASTRA_SANDBOX:-read-only}"

die() { echo "astra: $*" >&2; exit 1; }

if [[ "${1:-}" == "--ask" ]]; then
  [[ -n "${2:-}" ]] || die "usage: astra.sh --ask \"question\""
  exec ssh "$HOST" "codex exec -s $SANDBOX --skip-git-repo-check -C $REMOTE_WS \"${2//\"/\\\"}\""
fi

TASK="${1:-}"
[[ -n "$TASK" && -f "$TASK" ]] || die "usage: astra.sh <task-file.md> [report-name]"

base="$(basename "$TASK")"
report="${2:-REPORT-${base#TASK-}}"
report="${report%.md}.md"

# 1. Push the task (and anything else that changed) into Astra's workspace on the box.
scp -q "$TASK" "$HOST:$REMOTE_WS\\$base" || die "could not copy $TASK to $HOST"
for f in AGENTS.md REFERENCE.md; do
  [[ -f "$LOCAL_WS/$f" ]] && scp -q "$LOCAL_WS/$f" "$HOST:$REMOTE_WS\\$f" || true
done

echo "astra: sent $base -> $HOST:$REMOTE_WS (sandbox=$SANDBOX)" >&2
echo "astra: Astra cannot write; its reply is captured here as $report" >&2

# 2. Run it. Its whole answer comes back on stdout — that IS the report.
out="$LOCAL_WS/$report"
{
  echo "# ${report%.md} — captured from Astra's stdout"
  echo
  echo "Sent: \`$base\` · host \`$HOST\` · sandbox \`$SANDBOX\` · $(date -Is)"
  echo "Astra cannot write files over SSH (see scripts/astra.sh); this file is its reply, captured."
  echo
  echo '```'
} > "$out"

ssh "$HOST" "codex exec -s $SANDBOX --skip-git-repo-check -C $REMOTE_WS \
  \"Read $base in this folder and carry it out. You cannot write files - your entire answer must be in your reply text. Be complete; nobody can ask you a follow-up.\"" \
  2>&1 | tee -a "$out"

echo '```' >> "$out"
echo "astra: captured -> $out" >&2
