#!/usr/bin/env bash
# Multi-pane tmux watcher for the org.
# Pane 0: CTO log         Pane 1: task queue (auto-refresh)
# Pane 2: dev log slot A  Pane 3: dev log slot B
set -euo pipefail

AGENTS_ROOT="/Users/gob/projects/Agents"
SESSION="agents-watch"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not installed. install with: brew install tmux"
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux attach -t "$SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -c "$AGENTS_ROOT"

# layout 2x2
tmux split-window -h -t "$SESSION":0 -c "$AGENTS_ROOT"
tmux split-window -v -t "$SESSION":0.0 -c "$AGENTS_ROOT"
tmux split-window -v -t "$SESSION":0.1 -c "$AGENTS_ROOT"

# pane 0: CTO log
tmux send-keys -t "$SESSION":0.0 \
  "touch state/logs/cto.log && tail -F state/logs/cto.log" C-m

# pane 1: live task queue (uses sqlite)
tmux send-keys -t "$SESSION":0.1 \
  "watch -n 2 -c \"python -m lib.db list 2>/dev/null || echo 'db not initialized'\"" C-m

# pane 2: latest backend_dev log
tmux send-keys -t "$SESSION":0.2 \
  "tail -F state/logs/backend_dev_latest.log 2>/dev/null & tail -F state/logs/frontend_dev_latest.log 2>/dev/null; wait" C-m

# pane 3: latest qa + devops log
tmux send-keys -t "$SESSION":0.3 \
  "tail -F state/logs/qa_latest.log 2>/dev/null & tail -F state/logs/devops_latest.log 2>/dev/null; wait" C-m

tmux select-pane -t "$SESSION":0.0
tmux attach -t "$SESSION"
