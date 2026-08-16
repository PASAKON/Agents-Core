#!/usr/bin/env bash
# The one place that knows HOW to start a worker process.
#
# Why this file exists
# --------------------
# A C-level session runs the org MCP server in-process. It imports
# tools/delegate.py once, at session start, and cannot reload itself. So
# anything delegate.py holds as a literal is frozen in that session's memory
# for its whole life -- including, until now, the worker's module name.
#
# On 2026-08-15 `runners/dev_init.py` was renamed to `runners/worker_init.py`
# (df01c33). Every session started before that rename kept spawning
# `python -m runners.dev_init`, which no longer existed. The worker died in
# under a second, tmux tore the session down carrying the error with it, and
# the org log still printed "DEV spawned". Every delegate failed, identically,
# for hours, across multiple sessions -- and restarting was the only cure.
#
# The fix is indirection: delegate.py now holds only the STABLE path to this
# script. This script is read from disk at spawn time, so a rename inside
# runners/ is picked up immediately by every running session, stale or not.
# Keep this file's path and its argument contract stable; put the churn inside.
#
# Usage: spawn-worker.sh <role> <task_id>
set -euo pipefail

ROLE="${1:?usage: spawn-worker.sh <role> <task_id>}"
TASK_ID="${2:?usage: spawn-worker.sh <role> <task_id>}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# The module that actually runs a worker. If this is ever renamed again, this
# single line is the only thing that changes -- and no session needs a restart.
WORKER_MODULE="runners.worker_init"

if [ ! -x ".venv/bin/python" ]; then
  echo "spawn-worker: .venv/bin/python missing or not executable in $ROOT" >&2
  echo "spawn-worker: the worker cannot start; recreate the venv." >&2
  exit 78
fi

# Fail LOUDLY and specifically if the module is gone, rather than letting
# python's own one-line error scroll past inside a tmux pane that is about to
# be destroyed. That is the exact failure that hid for hours.
if ! .venv/bin/python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$WORKER_MODULE') else 1)"; then
  echo "spawn-worker: module '$WORKER_MODULE' does not exist." >&2
  echo "spawn-worker: it was probably renamed. Fix WORKER_MODULE in" >&2
  echo "spawn-worker:   $ROOT/scripts/spawn-worker.sh" >&2
  echo "spawn-worker: no session restart is needed once that line is right." >&2
  exit 78
fi

exec .venv/bin/python -m "$WORKER_MODULE" "$ROLE" "$TASK_ID"
