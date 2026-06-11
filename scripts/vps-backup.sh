#!/usr/bin/env bash
#
# vps-backup.sh — pull-based, resumable backup of the Hostinger VPS to this Mac.
#
# Gate #1 of the Hostinger -> Contabo migration (mooniex-claudeflow issue #140,
# "Migration plan v2"). Hostinger data is PERMANENTLY DESTROYED after 2026-06-18,
# so this is the only safety net. Implements the 11-item backup manifest.
#
#   Commands:
#     discover            Read-only inventory of the VPS -> writes inventory.txt
#     backup              Pull the full 11-item manifest (default command)
#     verify [RUN_DIR]    Walk the manifest of a run, write sha256-manifest.txt,
#                         print PASS/FAIL table, exit non-zero on any FAIL
#     mirror RUN_DIR DST  Copy a completed run dir to a 2nd location (rsync)
#
#   Options (backup):
#     --dry-run           Show what would be pulled; no transfers, no remote writes
#     --delta             New run dir, rsync --link-dest against the previous run
#                         (hardlinks unchanged files — for the Jun 18 final re-pull)
#     --skip-large        Skip the two big items (n8n_data ~1.5G, line-poster ~1.6G)
#                         so small/critical items land first; --only overrides this
#     --only <csv>        Pull only these item keys (see KEYS below)
#     --mirror <path>     After a successful backup, rsync the run dir to <path>
#     --no-pm2-save       Do not run `pm2 save` on the VPS (item 10)
#     --dest <path>       Backup root (default: ~/Backups/mooniex-vps)
#     --host <alias>      SSH alias / host (default: mooniex-vps)
#     -h, --help
#
#   Item KEYS (for --only / --skip-large):
#     claudeflow n8n-vol traefik-vol n8n-compose option line-automation
#     line-poster alphatrader env-bundle system dns
#
#   Destination layout:  <dest>/<UTC-timestamp>/  (OUTSIDE any git repo)
#   NEVER commit pulled data — the .env files hold ~163 production secrets.
#
# Tooling targets: macOS bash 3.2 + Apple rsync 2.6.9 (no -AX / --info=progress2).

set -uo pipefail   # NOT -e: we attempt every item and report all results.

# ---------------------------------------------------------------------------
# Config / defaults
# ---------------------------------------------------------------------------
HOST="mooniex-vps"
DEST_ROOT="${HOME}/Backups/mooniex-vps"
DRY_RUN=0
DELTA=0
SKIP_LARGE=0
NO_PM2_SAVE=0
ONLY_CSV=""
MIRROR_DST=""
SSH_OPTS="-o ConnectTimeout=20 -o BatchMode=yes"
EXPECTED_ENV_VARS=163   # informational target (item 9); real count printed at run

# Reconstructable dirs excluded from full-dir pulls (documented, not silent).
RSYNC_EXCLUDES=(
  --exclude 'node_modules' --exclude 'venv' --exclude '.venv'
  --exclude '__pycache__'  --exclude '.pytest_cache'
  --exclude '*.pyc'        --exclude '*.egg-info'
)

# The 5 .env files (label|remote-path). The 5th lives outside /root (item 4 dir).
ENV_FILES="\
claudeflow|/root/projects/mooniex-claudeflow/.env
option|/root/projects/mooniex-option/.env
line-automation|/root/projects/mooniex-line-automation/.env
alphatrader|/root/projects/mooniex-alphatrader/.env
docker-n8n|/docker/n8n/.env"

# DNS hostnames to snapshot (item 11). Old hstgr.cloud names die at cutover;
# the *.mooniex.com names are the post-migration replacements (plan v2).
DNS_HOSTS="\
mooniex.com
www.mooniex.com
webhook.srv1395225.hstgr.cloud
n8n.srv1395225.hstgr.cloud
webhook.mooniex.com
n8n.mooniex.com"

# Manifest table: key|item|class|relpath|description
#   class: required | optional | large  (large => skipped by --skip-large)
MANIFEST="\
claudeflow|1|required|claudeflow|claudeflow data/ + .env (state/ absent on VPS — Supabase SOT)
n8n-vol|2|large|volumes/n8n_data.tar.gz|n8n_data volume — workflows + creds + encryptionKey
traefik-vol|3|optional|volumes/traefik_data.tar.gz|traefik_data (acme.json) — nice-to-have
n8n-compose|4|required|docker-n8n|/docker/n8n compose + .env
option|5|required|option|mooniex-option repo + .env (33 vars)
line-automation|6|required|line-automation|queue.db + requirements + (unit in system/)
line-poster|7|large|line-poster|wineprefix ~1.5G + screenshots/ + launch_line.sh
alphatrader|8|required|alphatrader|alphatrader full dir + .env (26 vars)
env-bundle|9|required|_env-bundle|all 5 .env collected + counted (~163 vars)
system|10|required|system|crontab + pm2 dump + systemd + ufw + authorized_keys
dns|11|required|dns-snapshot.txt|DNS snapshot (dig from this Mac)"

ORDERED_KEYS="claudeflow n8n-vol traefik-vol n8n-compose option line-automation line-poster alphatrader env-bundle system dns"

# Per-item result tracking (parallel indexed arrays — bash 3.2 safe).
R_KEYS=(); R_STATUS=(); R_DETAIL=(); R_SECS=()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
if [ -t 1 ]; then C_R=$'\033[31m'; C_G=$'\033[32m'; C_Y=$'\033[33m'; C_B=$'\033[36m'; C_0=$'\033[0m'
else C_R=""; C_G=""; C_Y=""; C_B=""; C_0=""; fi

log()  { printf '%s[backup]%s %s\n' "$C_B" "$C_0" "$*"; }
ok()   { printf '%s[ ok ]%s %s\n'   "$C_G" "$C_0" "$*"; }
warn() { printf '%s[warn]%s %s\n'   "$C_Y" "$C_0" "$*" >&2; }
err()  { printf '%s[FAIL]%s %s\n'   "$C_R" "$C_0" "$*" >&2; }
die()  { err "$*"; exit 1; }

usage() { sed -n '2,46p' "$0" | sed 's/^# \{0,1\}//'; }

# SSH_OPTS is deliberately word-split into separate flags; remote cmd expands client-side (intended).
# shellcheck disable=SC2086,SC2029
ssh_run() { ssh $SSH_OPTS "$HOST" "$@"; }

# Most-recent run dir under DEST_ROOT (glob is sorted; timestamp names => last == newest).
latest_run_dir() {
  local d last=""
  for d in "$DEST_ROOT"/*/; do [ -d "$d" ] && last="$d"; done
  printf '%s' "${last%/}"
}
# Most-recent run dir excluding <arg> (for --delta link-dest base).
prev_run_dir() {
  local d prev="" cur="${1%/}"
  for d in "$DEST_ROOT"/*/; do [ -d "$d" ] || continue; [ "${d%/}" = "$cur" ] && continue; prev="$d"; done
  printf '%s' "${prev%/}"
}

# manifest lookups
mf_field() {  # mf_field <key> <col 1-based>
  printf '%s\n' "$MANIFEST" | awk -F'|' -v k="$1" -v c="$2" '$1==k{print $c; exit}'
}
mf_class()  { mf_field "$1" 3; }
mf_rel()    { mf_field "$1" 4; }
mf_desc()   { mf_field "$1" 5; }

# human-readable size of a local path ("-" if missing)
lsize() { [ -e "$1" ] && du -sh "$1" 2>/dev/null | cut -f1 || printf '%s' "-"; }
# remote size in human form ("?" if unknown)
rsize() { ssh_run "du -sh '$1' 2>/dev/null | cut -f1" 2>/dev/null || printf '%s' "?"; }

# is key selected given --only / --skip-large ?
selected() {
  local key="$1" class; class="$(mf_class "$key")"
  if [ -n "$ONLY_CSV" ]; then
    case ",$ONLY_CSV," in *",$key,"*) return 0 ;; *) return 1 ;; esac
  fi
  if [ "$SKIP_LARGE" -eq 1 ] && [ "$class" = "large" ]; then return 1; fi
  return 0
}

record() {  # record <key> <status> <detail> <secs>
  R_KEYS+=("$1"); R_STATUS+=("$2"); R_DETAIL+=("$3"); R_SECS+=("$4")
}

# rsync wrapper honouring dry-run + delta(--link-dest) + TTY progress.
# usage: do_rsync <relpath-in-run> <remote-src> [extra rsync args...]
# Dry-run reports the remote size instead of invoking rsync (Apple rsync 2.6.9
# --dry-run misbehaves on a not-yet-created dest dir; connectivity is proven by
# `discover` + the real pull, so dry-run is a planning view, not a probe).
do_rsync() {
  local rel="$1" src="$2"; shift 2
  local dest="$RUN_DIR/$rel"
  if [ "$DRY_RUN" -eq 1 ]; then
    log "  would pull $src  ($(rsize "$src"))  -> $rel"
    return 0
  fi
  local args=(-aH --partial -e "ssh $SSH_OPTS")
  [ -t 1 ] && args+=(--progress)
  if [ "$DELTA" -eq 1 ] && [ -n "${PREV_RUN:-}" ] && [ -e "$PREV_RUN/$rel" ]; then
    args+=(--link-dest "$PREV_RUN/$rel")
  fi
  args+=("$@")
  mkdir -p "$(dirname "$dest")"
  rsync "${args[@]}" "$HOST:$src" "$dest"
}

# ---------------------------------------------------------------------------
# discover (item 0) — read-only inventory, pins paths, writes inventory.txt
# ---------------------------------------------------------------------------
do_discover() {
  local out="$RUN_DIR/inventory.txt"
  mkdir -p "$RUN_DIR"; chmod 700 "$DEST_ROOT" "$RUN_DIR" 2>/dev/null || true
  log "discover: read-only inventory of $HOST -> $out"
  {
    echo "# VPS inventory  host=$HOST  generated=$TIMESTAMP (UTC)"
    echo "# read-only; used to pin exact manifest paths"
    echo
    ssh_run 'bash -s' <<'REMOTE'
echo "== host =="; hostname; uname -sr; uptime
echo; echo "== /root/projects =="; ls -la /root/projects/ 2>/dev/null
echo; echo "== docker volumes =="; docker volume ls 2>/dev/null
echo; echo "== /docker/n8n =="; ls -la /docker/n8n 2>/dev/null
echo; echo "== systemd mooniex-* =="; ls -la /etc/systemd/system/mooniex-* 2>/dev/null
echo; echo "== .env files =="
for f in /root/projects/mooniex-claudeflow/.env /root/projects/mooniex-option/.env \
         /root/projects/mooniex-line-automation/.env /root/projects/mooniex-alphatrader/.env \
         /docker/n8n/.env; do
  if [ -f "$f" ]; then
    printf '%4s  %s\n' "$(grep -cE '^[[:space:]]*[^#[:space:]]' "$f")" "$f"
  else printf '%4s  %s\n' "MISS" "$f"; fi
done
echo; echo "== wineprefix =="; ls -ld /root/projects/mooniex-line-poster/wineprefix 2>/dev/null
echo; echo "== sizes =="; du -sh /var/lib/docker/volumes/n8n_data/_data \
  /var/lib/docker/volumes/traefik_data/_data /root/projects/mooniex-line-poster/wineprefix \
  /root/projects/* 2>/dev/null
echo; echo "== sompong-user.json =="; ls -la /root/projects/mooniex-claudeflow/data/sompong-user.json 2>/dev/null || echo MISSING
echo; echo "== claudeflow state? =="; ls -ld /root/projects/mooniex-claudeflow/state 2>/dev/null || echo "state ABSENT (expected — Supabase SOT)"
echo; echo "== crontab (root) =="; crontab -l 2>/dev/null || echo "(empty)"
echo; echo "== pm2 =="; pm2 list 2>/dev/null || echo "(pm2 n/a)"
echo; echo "== ufw =="; ufw status verbose 2>/dev/null || echo "(ufw n/a)"
echo; echo "== authorized_keys =="; wc -l /root/.ssh/authorized_keys 2>/dev/null || echo MISSING
REMOTE
  } >"$out" 2>&1
  ok "inventory written: $out ($(wc -l <"$out" | tr -d ' ') lines)"
  [ "${1:-}" = "--quiet" ] || sed -n '1,60p' "$out"
}

# ---------------------------------------------------------------------------
# Per-item pull functions (each returns 0 ok / 1 fail, sets ITEM_DETAIL)
# ---------------------------------------------------------------------------
ITEM_DETAIL=""

pull_claudeflow() {
  local base="/root/projects/mooniex-claudeflow"
  do_rsync "claudeflow/data" "$base/data/" || return 1
  do_rsync "claudeflow/.env" "$base/.env"  || return 1
  if ssh_run "test -d '$base/state'"; then
    do_rsync "claudeflow/state" "$base/state/" || return 1
    ITEM_DETAIL="data+state+.env"
  else
    [ "$DRY_RUN" -eq 0 ] && printf 'state/ ABSENT on VPS (claudeflow uses Supabase SOT)\n' \
      >"$RUN_DIR/claudeflow/STATE-ABSENT.txt"
    ITEM_DETAIL="data+.env (state/ absent — noted)"
  fi
  return 0
}

pull_volume() {  # pull_volume <volname> <relpath>
  local vol="$1" rel="$2" dest="$RUN_DIR/$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    ITEM_DETAIL="would stream docker volume $vol (src $(rsize "/var/lib/docker/volumes/$vol/_data"))"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  log "streaming volume $vol -> $rel (not resumable; .partial until complete)"
  if ssh_run "docker run --rm -v ${vol}:/data:ro alpine tar czf - -C /data ." >"$dest.partial" 2>/dev/null; then
    mv "$dest.partial" "$dest"
    ITEM_DETAIL="streamed $(lsize "$dest")"
    return 0
  else
    rm -f "$dest.partial"
    ITEM_DETAIL="stream FAILED"
    return 1
  fi
}

pull_n8n_compose() { do_rsync "docker-n8n" "/docker/n8n/" || return 1; ITEM_DETAIL="compose + .env"; }

pull_option()  { do_rsync "option"  "/root/projects/mooniex-option/"  "${RSYNC_EXCLUDES[@]}" || return 1; ITEM_DETAIL="repo + .env (excl node_modules/venv)"; }
pull_alphatr() { do_rsync "alphatrader" "/root/projects/mooniex-alphatrader/" "${RSYNC_EXCLUDES[@]}" || return 1; ITEM_DETAIL="full dir (excl venv) incl traders.json/bot.log/.env"; }

pull_line_automation() {
  do_rsync "line-automation" "/root/projects/mooniex-line-automation/" "${RSYNC_EXCLUDES[@]}" || return 1
  if [ "$DRY_RUN" -eq 0 ]; then
    ssh_run "/root/projects/mooniex-line-automation/venv/bin/pip freeze 2>/dev/null" \
      >"$RUN_DIR/line-automation/requirements.freeze.txt" 2>/dev/null || true
  fi
  ITEM_DETAIL="queue.db + code + pip-freeze (unit in system/)"
}

pull_line_poster() {
  do_rsync "line-poster" "/root/projects/mooniex-line-poster/" "${RSYNC_EXCLUDES[@]}" || return 1
  ITEM_DETAIL="wineprefix + screenshots + launch_line.sh + code"
}

pull_env_bundle() {
  local rel="_env-bundle" dest="$RUN_DIR/_env-bundle" total=0 missing=0 label path n
  [ "$DRY_RUN" -eq 0 ] && { mkdir -p "$dest"; : >"$dest/env-counts.txt"; }
  while IFS='|' read -r label path; do
    [ -z "$label" ] && continue
    if [ "$DRY_RUN" -eq 1 ]; then
      if ssh_run "test -f '$path'"; then log "  env $label: present ($path)"; else warn "  env $label MISSING ($path)"; fi
      continue
    fi
    if do_rsync "$rel/$label.env" "$path" 2>/dev/null && [ -s "$dest/$label.env" ]; then
      chmod 600 "$dest/$label.env" 2>/dev/null || true
      n=$(grep -cE '^[[:space:]]*[^#[:space:]]' "$dest/$label.env" 2>/dev/null || echo 0)
      printf '%4d  %s.env\n' "$n" "$label" >>"$dest/env-counts.txt"
    else
      printf '%4s  %s.env (%s)\n' "MISS" "$label" "$path" >>"$dest/env-counts.txt"
    fi
  done <<EOF
$ENV_FILES
EOF
  if [ "$DRY_RUN" -eq 1 ]; then ITEM_DETAIL="would collect 5 .env (expect ~$EXPECTED_ENV_VARS vars)"; return 0; fi
  # tally outside the while-subshell from the counts file
  total=$(awk '/\.env$/{s+=$1} END{print s+0}' "$dest/env-counts.txt")
  missing=$(grep -c 'MISS' "$dest/env-counts.txt" 2>/dev/null || echo 0)
  printf 'TOTAL %d vars across 5 .env (expected ~%d)\n' "$total" "$EXPECTED_ENV_VARS" >>"$dest/env-counts.txt"
  ITEM_DETAIL="$total vars / 5 files; missing=$missing"
  [ "$missing" -eq 0 ] || return 1
  return 0
}

pull_system() {
  local d="$RUN_DIR/system" unit
  if [ "$DRY_RUN" -eq 1 ]; then
    ITEM_DETAIL="crontab+pm2 dump+systemd+ufw+authorized_keys"
    [ "$NO_PM2_SAVE" -eq 1 ] && ITEM_DETAIL="$ITEM_DETAIL (pm2 save skipped)"
    return 0
  fi
  mkdir -p "$d/systemd"
  # crontab (may be empty -> write a truthful marker so size>0)
  ssh_run "crontab -l 2>/dev/null" >"$d/crontab-root.txt" 2>/dev/null || true
  [ -s "$d/crontab-root.txt" ] || printf '# root crontab empty as of %s (UTC)\n' "$TIMESTAMP" >"$d/crontab-root.txt"
  # pm2 dump (refresh with `pm2 save` unless suppressed)
  if [ "$NO_PM2_SAVE" -eq 0 ]; then ssh_run "pm2 save >/dev/null 2>&1" || warn "pm2 save returned non-zero (continuing)"; fi
  do_rsync "system/dump.pm2" "/root/.pm2/dump.pm2" 2>/dev/null || warn "no dump.pm2 to pull"
  # systemd mooniex-* units — enumerate remotely + pull each (rsync 2.6.9
  # include/exclude is unreliable, and this pins exactly what exists).
  ssh_run "ls -1 /etc/systemd/system/mooniex-* 2>/dev/null" | while IFS= read -r unit; do
    [ -n "$unit" ] || continue
    do_rsync "system/systemd/$(basename "$unit")" "$unit" || warn "systemd unit not pulled: $unit"
  done
  # ufw + authorized_keys
  ssh_run "ufw status verbose 2>/dev/null" >"$d/ufw-status.txt" 2>/dev/null || echo "(ufw n/a)" >"$d/ufw-status.txt"
  do_rsync "system/authorized_keys" "/root/.ssh/authorized_keys" 2>/dev/null || warn "no authorized_keys"
  [ -f "$d/authorized_keys" ] && chmod 600 "$d/authorized_keys" 2>/dev/null
  ITEM_DETAIL="crontab+pm2+systemd+ufw+authorized_keys"
  return 0
}

pull_dns() {
  local f="$RUN_DIR/dns-snapshot.txt" h
  if [ "$DRY_RUN" -eq 1 ]; then
    ITEM_DETAIL="dig $(printf '%s\n' "$DNS_HOSTS" | grep -c .) hostnames (local)"
    return 0
  fi
  {
    echo "# DNS snapshot  generated=$TIMESTAMP (UTC)"
    echo "# old *.srv1395225.hstgr.cloud die at cutover; *.mooniex.com are replacements (plan v2)"
    for h in $DNS_HOSTS; do
      echo; echo "=== $h ==="
      echo "-- NS --";    dig +short NS    "$h" 2>/dev/null
      echo "-- A --";     dig +short A     "$h" 2>/dev/null
      echo "-- CNAME --"; dig +short CNAME "$h" 2>/dev/null
    done
  } >"$f" 2>&1
  ITEM_DETAIL="$(grep -c '^=== ' "$f") hostnames"
  return 0
}

dispatch_pull() {  # dispatch_pull <key>
  case "$1" in
    claudeflow)       pull_claudeflow ;;
    n8n-vol)          pull_volume n8n_data "volumes/n8n_data.tar.gz" ;;
    traefik-vol)      pull_volume traefik_data "volumes/traefik_data.tar.gz" ;;
    n8n-compose)      pull_n8n_compose ;;
    option)           pull_option ;;
    line-automation)  pull_line_automation ;;
    line-poster)      pull_line_poster ;;
    alphatrader)      pull_alphatr ;;
    env-bundle)       pull_env_bundle ;;
    system)           pull_system ;;
    dns)              pull_dns ;;
    *) ITEM_DETAIL="unknown key"; return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# backup driver
# ---------------------------------------------------------------------------
do_backup() {
  mkdir -p "$RUN_DIR"; chmod 700 "$DEST_ROOT" "$RUN_DIR" 2>/dev/null || true
  if [ "$DELTA" -eq 1 ]; then
    PREV_RUN="$(prev_run_dir "$RUN_DIR")"
    if [ -n "$PREV_RUN" ]; then log "delta mode: hardlinking unchanged files against $PREV_RUN"
    else warn "delta mode: no previous run found — full pull"; fi
  fi
  log "$([ "$DRY_RUN" -eq 1 ] && echo 'DRY-RUN ')backup -> $RUN_DIR  (host=$HOST)"
  do_discover --quiet
  : >"$RUN_DIR/MANIFEST.txt"

  local key class secs status
  for key in $ORDERED_KEYS; do
    class="$(mf_class "$key")"
    if ! selected "$key"; then
      record "$key" "SKIP" "$([ "$class" = large ] && echo 'large (--skip-large)' || echo 'not in --only')" 0
      printf '%-16s SKIP  %s\n' "$key" "$(mf_desc "$key")" >>"$RUN_DIR/MANIFEST.txt"
      continue
    fi
    ITEM_DETAIL=""; secs=$SECONDS
    log "item $(mf_field "$key" 2) [$key] — $(mf_desc "$key")"
    if dispatch_pull "$key"; then status="OK"; ok "$key — $ITEM_DETAIL"
    else status="FAIL"; err "$key — ${ITEM_DETAIL:-failed}"; fi
    record "$key" "$status" "$ITEM_DETAIL" "$((SECONDS - secs))"
    printf '%-16s %-4s  %s\n' "$key" "$status" "${ITEM_DETAIL:-$(mf_desc "$key")}" >>"$RUN_DIR/MANIFEST.txt"
  done

  write_summary
  if [ "$DRY_RUN" -eq 0 ] && [ -n "$MIRROR_DST" ]; then do_mirror "$RUN_DIR" "$MIRROR_DST"; fi
}

# ---------------------------------------------------------------------------
# verify — walk run dir, sha256 manifest, PASS/FAIL table
# ---------------------------------------------------------------------------
nonempty() {  # nonempty <path>  (file: size>0 ; dir: has >=1 file)
  if [ -f "$1" ]; then [ -s "$1" ]; return; fi
  if [ -d "$1" ]; then [ -n "$(find "$1" -type f -print 2>/dev/null | head -1)" ]; return; fi
  return 1
}

do_verify() {
  local run="${1:-}"
  [ -z "$run" ] && run="$(latest_run_dir)"
  run="${run%/}"
  [ -n "$run" ] && [ -d "$run" ] || die "verify: no run dir (give one explicitly)"
  log "verify $run"
  local key class rel path st fails=0 cnt
  printf '\n%-16s %-9s %-8s %s\n' "ITEM" "RESULT" "SIZE" "PATH/NOTE"
  printf '%s\n' "------------------------------------------------------------------------"
  for key in $ORDERED_KEYS; do
    class="$(mf_class "$key")"; rel="$(mf_rel "$key")"; path="$run/$rel"
    if nonempty "$path"; then
      st="PASS"
      if [ "$key" = "n8n-vol" ]; then
        if tar -tzf "$path" 2>/dev/null | grep -qE '(^|/)config$' && \
           tar -xzf "$path" -O ./config 2>/dev/null | grep -q 'encryptionKey'; then st="PASS"
        else st="FAIL"; fails=$((fails+1)); rel="$rel :: encryptionKey NOT found"; fi
      fi
      if [ "$key" = "env-bundle" ]; then
        cnt=0; for e in "$run"/_env-bundle/*.env; do [ -f "$e" ] && cnt=$((cnt+1)); done
        [ "$cnt" -eq 5 ] || { st="FAIL"; fails=$((fails+1)); rel="$rel :: $cnt/5 .env"; }
      fi
      printf '%-16s %-9s %-8s %s\n' "$key" "$st" "$(lsize "$run/$(mf_rel "$key")")" "$rel"
    else
      if [ "$class" = "optional" ]; then
        printf '%-16s %-9s %-8s %s\n' "$key" "WARN" "-" "$rel (optional, absent)"
      elif [ "$class" = "large" ]; then
        printf '%-16s %-9s %-8s %s\n' "$key" "WARN" "-" "$rel (large, not pulled — re-run w/o --skip-large)"
      else
        fails=$((fails+1))
        printf '%-16s %-9s %-8s %s\n' "$key" "FAIL" "-" "$rel (MISSING/empty)"
      fi
    fi
  done
  printf '%s\n' "------------------------------------------------------------------------"

  log "writing sha256-manifest.txt"
  ( cd "$run" && find . -type f ! -name 'sha256-manifest.txt' ! -name '*.partial' -print0 \
      | xargs -0 shasum -a 256 2>/dev/null ) >"$run/sha256-manifest.txt"
  ok "sha256-manifest.txt: $(wc -l <"$run/sha256-manifest.txt" | tr -d ' ') files hashed"

  if [ "$fails" -gt 0 ]; then err "VERIFY: $fails required item(s) FAILED"; return 1; fi
  ok "VERIFY: all required items present"
  return 0
}

# ---------------------------------------------------------------------------
# mirror — 2nd copy of a completed run dir
# ---------------------------------------------------------------------------
do_mirror() {
  local run="$1" dst="$2"
  [ -d "$run" ] || die "mirror: run dir not found: $run"
  [ -n "$dst" ] || die "mirror: destination required"
  mkdir -p "$dst"
  log "mirror $run -> $dst"
  if rsync -aH --partial "$run" "$dst/"; then ok "mirror complete: $dst/$(basename "$run")"
  else err "mirror failed"; return 1; fi
}

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
write_summary() {
  local f="$RUN_DIR/SUMMARY.txt" i total_k
  {
    echo "# Backup summary  run=$TIMESTAMP (UTC)  host=$HOST  dry_run=$DRY_RUN delta=$DELTA skip_large=$SKIP_LARGE"
    echo "# dest: $RUN_DIR"
    echo "# excluded from full-dir pulls (reconstructable): node_modules venv .venv __pycache__ .pytest_cache *.pyc *.egg-info"
    echo
    printf '%-16s %-6s %-10s %s\n' "ITEM" "STATUS" "DURATION" "DETAIL"
    printf '%s\n' "----------------------------------------------------------------------"
    i=0
    while [ "$i" -lt "${#R_KEYS[@]}" ]; do
      printf '%-16s %-6s %-10s %s\n' "${R_KEYS[$i]}" "${R_STATUS[$i]}" "${R_SECS[$i]}s" "${R_DETAIL[$i]}"
      i=$((i+1))
    done
    printf '%s\n' "----------------------------------------------------------------------"
    if [ "$DRY_RUN" -eq 0 ]; then
      total_k=$(du -sk "$RUN_DIR" 2>/dev/null | cut -f1)
      printf 'TOTAL on disk: %s (%s KB)\n' "$(lsize "$RUN_DIR")" "${total_k:-?}"
    fi
    echo
    echo "Next steps:"
    echo "  1. verify  : $0 verify \"$RUN_DIR\""
    echo "  2. 2nd copy: $0 mirror \"$RUN_DIR\" /Volumes/<external-disk>/mooniex-vps"
    [ "$SKIP_LARGE" -eq 1 ] && echo "  3. large skipped — re-run without --skip-large for n8n-vol + line-poster"
    echo "  4. Jun 18 final: $0 backup --delta --mirror /Volumes/<disk>/mooniex-vps"
  } | tee "$f"
  ok "summary -> $f"
}

# ---------------------------------------------------------------------------
# arg parsing + main
# ---------------------------------------------------------------------------
CMD=""
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    discover|backup|verify|mirror) if [ -z "$CMD" ]; then CMD="$1"; else ARGS+=("$1"); fi; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --delta)       DELTA=1; shift ;;
    --skip-large)  SKIP_LARGE=1; shift ;;
    --no-pm2-save) NO_PM2_SAVE=1; shift ;;
    --only)        ONLY_CSV="${2:-}"; shift 2 ;;
    --mirror)      MIRROR_DST="${2:-}"; shift 2 ;;
    --dest)        DEST_ROOT="${2:-}"; shift 2 ;;
    --host)        HOST="${2:-}"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    *)             ARGS+=("$1"); shift ;;
  esac
done
[ -z "$CMD" ] && CMD="backup"

# tooling check (local)
for t in ssh rsync dig shasum tar du awk; do
  command -v "$t" >/dev/null 2>&1 || die "missing required tool: $t"
done

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PREV_RUN=""

case "$CMD" in
  discover) RUN_DIR="$DEST_ROOT/$TIMESTAMP"; do_discover ;;
  backup)   RUN_DIR="$DEST_ROOT/$TIMESTAMP"; do_backup ;;
  verify)   RUN_DIR=""; do_verify "${ARGS[0]:-}" ;;
  mirror)
    [ "${#ARGS[@]}" -ge 2 ] || die "usage: $0 mirror <RUN_DIR> <DEST>"
    do_mirror "${ARGS[0]}" "${ARGS[1]}" ;;
  *) usage; exit 1 ;;
esac
