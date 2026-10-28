#!/usr/bin/env bash
# Local Mac launcher. Inputs are validated here as well as by mac-restart.sh.
set -euo pipefail
sha= repo= dry=0 cards=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sha|--repo)
      [ $# -ge 2 ] || exit 2
      case "$1" in --sha) sha=$2 ;; --repo) repo=$2 ;; esac
      shift 2 ;;
    --dry-run) dry=1; shift ;;
    --cards-checked) cards=1; shift ;;
    *) exit 2 ;;
  esac
done
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$repo" =~ ^/[A-Za-z0-9._/-]+$ ]] || exit 2
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$repo"
head=$(git rev-parse HEAD) || exit 5
[ "$head" = "$sha" ] || { echo 'Restart refused: HEAD differs from --sha' >&2; exit 4; }
flags='--wait-max 600'
[ "$dry" -eq 0 ] || flags="$flags --dry-run"
[ "$cards" -eq 0 ] || flags="$flags --cards-checked"
# A unique timestamp/PID label; also refuse an existing job before creating any files.
stamp=$(date -u +%Y%m%dT%H%M%SZ)-$$
label="com.mooniex.mac-prep-$stamp"
if launchctl list "$label" >/dev/null 2>&1; then
  echo "Restart refused: job $label already exists" >&2
  exit 7
fi
mkdir -p state/restart
log="$repo/state/restart/mac-prep-$stamp.log"
job=$(mktemp "$repo/state/restart/mac-prep-job.XXXXXX")
chmod 700 "$job"
# All interpolated command inputs above are allow-listed; quote filesystem paths anyway.
cat > "$job" <<EOF
#!/bin/bash
set -euo pipefail
trap 'status=\$?; echo "job exit: \$status"; rm -f "$job"; launchctl remove "$label"' EXIT
export PATH=/opt/homebrew/bin:/usr/local/bin:\$PATH
cd '$repo'
[ "\$(git rev-parse HEAD)" = '$sha' ] || exit 4
bash scripts/hub/org-python.sh tools/restart_run.py --host mac prep $flags
if [ '$dry' -eq 0 ]; then
  sudo -n shutdown -r +1 || exit 6
fi
EOF
if ! launchctl submit -l "$label" -o "$log" -e "$log" -- /bin/bash "$job"; then
  rm -f "$job"
  echo 'Restart refused: launchctl submission failed' >&2
  exit 7
fi
echo "Submitted $label; follow $log (submission is not prep success)"
