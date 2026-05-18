# Source this from ~/.zshrc:    source /Users/gob/projects/Agents/scripts/aliases.sh
AGENTS_ROOT="/Users/gob/projects/Agents"

alias agents="cd $AGENTS_ROOT"
alias agents-watch="bash $AGENTS_ROOT/scripts/watch.sh"
alias agents-dash="cd $AGENTS_ROOT && python dashboard.py"
alias agents-status="cd $AGENTS_ROOT && python -m lib.db list"
alias agents-stats="cd $AGENTS_ROOT && python -m lib.db stats"
alias agents-cto="tail -F $AGENTS_ROOT/state/logs/cto.log"
alias agents-logs="ls -lt $AGENTS_ROOT/state/logs/ | head -15"
alias agents-run="cd $AGENTS_ROOT && python main.py"
alias agents-init="cd $AGENTS_ROOT && python main.py --init"
