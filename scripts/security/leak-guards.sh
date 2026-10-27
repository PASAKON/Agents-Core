#!/usr/bin/env bash
# scripts/security/leak-guards.sh -- every git repo under the given roots refuses a
# commit or a push that carries a secret, and this script says which ones do not.
# (HQSecurity M3, order O-20261027-1347-4e62.)
#
#   leak-guards.sh --check   <root>...   read-only: one line per repo
#   leak-guards.sh --install <root>...   idempotent: pre-commit + pre-push hooks
#   leak-guards.sh --install --dry-run <root>...   say what --install would do, change nothing
#   --skip NAME   (repeatable) also prune directories called NAME while looking for repos
#
# Repos are found by `.git` under each root. node_modules, .venv and worktrees are never
# entered (a linked worktree shares its main repo's hooks, so it is not a repo of its own).
#
# What --install writes, into the repo's EFFECTIVE hooks dir (core.hooksPath if set):
#   pre-commit  gitleaks on the staged changes.
#   pre-push    gitleaks on each pushed range <remote_sha>..<local_sha>; a new branch scans
#               the commits that are not on the remote yet.
# A hook that is already there is CHAINED, not overwritten: it is renamed <hook>.local and
# the new hook calls it first and stops on its non-zero exit (Contabo's Agents-Core
# pre-push, which refuses commit a60f1744, keeps working). The one exception: a pre-commit
# that already runs gitleaks (scripts/install-git-hooks.sh) is left alone.
# Re-running changes nothing. Every hook carries the marker "leak-guards:v1".
#
# Ownership: a repo whose .git, git dir or hooks dir is owned by another real account (not root,
# not whoever runs this) or is group/other-writable is SKIPPED ("skipped-not-owned"): nothing is
# written there, and --install exits 1 because that repo is still unguarded. It needs its own
# install, run as its owner. --check prints the real guard state and adds the same word.
#
# Fail-open on purpose: if gitleaks is not on PATH the hook warns loudly and lets the
# commit through (same as install-git-hooks.sh), so --check/--install exit 2 on a machine
# without gitleaks. ALLOW_NO_GITLEAKS=1 accepts that. A hook cannot stop `--no-verify`;
# the server-side guard is GitHub push protection.
#
# winbox: Git for Windows ships bash.exe and its own sh, so this script runs as-is under Git Bash
# (& 'C:\Program Files\Git\bin\bash.exe' scripts/security/leak-guards.sh --check C:\Users\UsEr\Projects)
# and the hooks it writes run under Git's sh. gitleaks.exe must be on PATH. There is no PowerShell
# twin. UNTESTED on winbox as of 2026-10-27 (tested on Linux only; written for bash 3.2 / BSD tools).
#
# Exit: 0 ok | 1 a repo has no guard (check) or could not be set up (install) |
#       2 gitleaks missing | 64 bad usage.
# Output is names and paths only. Bash 3.2 safe (macOS), runs under Git Bash on winbox.

MARK='leak-guards:v1'
SKIP_NAMES='node_modules .venv worktrees'

die() { echo "leak-guards: $*" >&2; exit 64; }

usage() { sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; }

# ---------------------------------------------------------------- hook bodies
emit_precommit() {
  cat <<'HOOK_EOF'
#!/bin/sh
# leak-guards:v1 pre-commit -- written by scripts/security/leak-guards.sh. Do not edit; re-run --install.
# 1. The hook that was here before is <this file>.local; it runs first and a failure stops the commit.
# 2. gitleaks on the staged changes. No gitleaks on PATH = loud warning, commit goes through.
#    False positive: add its fingerprint to .gitleaksignore (last resort: git commit --no-verify).
old="$0.local"
if [ -x "$old" ]; then
  "$old" "$@" || exit $?
fi
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "leak-guards: gitleaks NOT on PATH -- secret guard SKIPPED for this commit" >&2
  exit 0
fi
gl_new=1
case "$(gitleaks version 2>/dev/null | head -n 1 | sed 's/^[^0-9]*//')" in
  [0-7].*|8.[0-9].*|8.1[0-8].*) gl_new=0 ;;
esac
if [ "$gl_new" = 1 ]; then
  gitleaks git --staged --redact --no-banner
else
  gitleaks protect --staged --redact --no-banner
fi
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "" >&2
  echo "leak-guards: gitleaks exit $rc on the staged changes -- commit BLOCKED." >&2
  echo "   real secret?  remove it, put it in Infisical instead, then rotate it." >&2
  echo "   false positive?  add its fingerprint to .gitleaksignore." >&2
  exit 1
fi
exit 0
HOOK_EOF
}

emit_prepush() {
  cat <<'HOOK_EOF'
#!/bin/sh
# leak-guards:v1 pre-push -- written by scripts/security/leak-guards.sh. Do not edit; re-run --install.
# 1. The hook that was here before is <this file>.local; it runs first (same arguments, same
#    stdin) and a failure stops the push.
# 2. gitleaks on every pushed range <remote_sha>..<local_sha>. A new branch (or a remote sha
#    this clone does not have) scans the commits that are not on the remote yet.
#    No gitleaks on PATH = loud warning, push goes through.
old="$0.local"
tmp=$(mktemp "${TMPDIR:-/tmp}/leak-guards.XXXXXX") || exit 1
trap 'rm -f "$tmp"' EXIT HUP INT TERM
cat > "$tmp"
if [ -x "$old" ]; then
  "$old" "$@" < "$tmp" || exit $?
fi
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "leak-guards: gitleaks NOT on PATH -- secret guard SKIPPED for this push" >&2
  exit 0
fi
gl_new=1
case "$(gitleaks version 2>/dev/null | head -n 1 | sed 's/^[^0-9]*//')" in
  [0-7].*|8.[0-9].*|8.1[0-8].*) gl_new=0 ;;
esac
# "not on the remote yet" is judged against the remote being pushed to when $1 names one.
unpushed="--remotes"
if [ -n "${1:-}" ] && git remote 2>/dev/null | grep -Fxq -- "$1"; then
  unpushed="--remotes=$1"
fi
bad=0
while read -r lref lsha rref rsha; do
  case "$lsha" in *[!0]*) ;; *) continue ;; esac            # deleting a ref: nothing to scan
  range="$lsha --not $unpushed"
  case "$rsha" in
    *[!0]*) if git cat-file -e "$rsha^{commit}" 2>/dev/null; then range="$rsha..$lsha"; fi ;;
  esac
  if [ "$gl_new" = 1 ]; then
    gitleaks git --redact --no-banner --log-opts "$range" .
  else
    gitleaks detect --redact --no-banner --log-opts="$range" --source .
  fi || bad=1
done < "$tmp"
if [ "$bad" -ne 0 ]; then
  echo "" >&2
  echo "leak-guards: gitleaks flagged the commits being pushed -- push BLOCKED." >&2
  echo "   real secret?  take it out of the history (a revert commit is not enough), put it in Infisical, rotate it." >&2
  echo "   false positive?  add its fingerprint to .gitleaksignore." >&2
  exit 1
fi
exit 0
HOOK_EOF
}

# ---------------------------------------------------------------- repo discovery
# Print the working-tree path of every repo under the roots, one per line, de-duplicated.
# No find -L: LinePoster/wineprefix/dosdevices/z: points at / and walks the whole disk (measured
# 2026-10-27, killed at 280 s). A symlink is followed ONE step instead: if it points at a
# directory holding a .git, that directory is the repo (so a hub like /root/projects/x -> /opt/...
# does not make a repo vanish); anything else behind a symlink is ignored.
list_repos() {
  local root r g repo n first=1
  local prune=()
  for n in $SKIP_NAMES; do
    [ "$first" = 1 ] || prune+=(-o)
    prune+=(-name "$n")
    first=0
  done
  for root in "${roots[@]}"; do
    r=$(cd "$root" && pwd -P)
    find "$r" \( "${prune[@]}" \) -prune -o \( -name .git -prune -print0 \) -o \( -type l -print0 \) 2>/dev/null
  done | while IFS= read -r -d '' g; do
    if [ -L "$g" ] && [ "$(basename "$g")" != .git ]; then
      [ -e "$g/.git" ] || continue
      repo=$(cd "$g" && pwd -P) || continue
    else
      repo=$(cd "$(dirname "$g")" && pwd -P) || continue
    fi
    # a `.git` FILE is a linked worktree (shares its main repo's hooks: skip) or a submodule (a repo)
    if [ -f "$repo/.git" ] && [ "$(abs_dir "$repo" --git-dir)" != "$(abs_dir "$repo" --git-common-dir)" ]; then
      continue
    fi
    printf '%s\n' "$repo"
  done | sort -u
}

abs_dir() { # repo rev-parse-flag -> absolute directory
  local d
  d=$(git -C "$1" rev-parse "$2" 2>/dev/null) || return 1
  ( cd "$1" && cd "$d" 2>/dev/null && pwd -P )
}

hooks_dir() { # repo -> the directory git runs hooks from (honours core.hooksPath)
  local h
  h=$(git -C "$1" rev-parse --git-path hooks 2>/dev/null) || return 1
  case "$h" in
    /*|[A-Za-z]:*) printf '%s\n' "$h" ;;
    *) printf '%s/%s\n' "$1" "$h" ;;
  esac
}

# ---------------------------------------------------------------- who may write there
# --install can run as root over repos that other accounts own (SomPong's belongs to sompong).
# In a directory another account can write, that account can swap files under a root-run
# installer, so such a repo is skipped ("skipped-not-owned") and nothing in it is read or written.
# A path is unsafe when its owner is a real account that is neither root nor the user running
# this script, or when group/other can write it (mode & 022). An owner uid with no account
# (the Mac's 501 on this box) cannot log in, so it counts as safe.
owner_mode() { # path -> "uid octal-mode" (follows symlinks); GNU stat first, BSD stat second
  stat -L -c '%u %a' "$1" 2>/dev/null || stat -L -f '%u %Lp' "$1" 2>/dev/null
}

uid_has_account() {
  if command -v getent >/dev/null 2>&1; then getent passwd "$1" >/dev/null 2>&1
  else id -un "$1" >/dev/null 2>&1; fi
}

unsafe_path() { # path -> 0 when another account could write there
  local om uid mode
  [ -e "$1" ] || return 1
  om=$(owner_mode "$1") || return 0          # cannot tell = do not touch
  uid=${om%% *}; mode=${om##* }
  case "$uid$mode" in ''|*[!0-9]*) return 0 ;; esac
  [ $((8#$mode & 022)) -eq 0 ] || return 0
  [ "$uid" = 0 ] || [ "$uid" = "$(id -u)" ] || ! uid_has_account "$uid" || return 0
  return 1
}

repo_unsafe() { # repo hooks_dir -> 0 when .git, the real git dir or the hooks dir is unsafe
  local p hd="$2"
  [ -e "$hd" ] || hd=$(dirname "$hd")        # a hooks dir that does not exist yet: judge the dir it would be made in
  for p in "$1/.git" "$(abs_dir "$1" --git-common-dir)" "$hd"; do
    [ -n "$p" ] && unsafe_path "$p" && return 0
  done
  return 1
}

# ---------------------------------------------------------------- guard detection (textual)
has_foreign_guard() { # hook name -> 0 when a non-comment line runs gitleaks the way that hook needs
  local re='gitleaks[[:space:]]+(git|detect)'
  [ "$2" = pre-commit ] && re='gitleaks[[:space:]]+(protect|git|detect)'
  grep -v '^[[:space:]]*#' "$1" 2>/dev/null | grep -Eq "$re"
}

guard_state() { # hook name -> yes|no
  # git ignores a hook without the exec bit, so such a hook guards nothing
  if [ -f "$1" ] && [ -x "$1" ] && { grep -q "$MARK" "$1" 2>/dev/null || has_foreign_guard "$1" "$2"; }; then
    echo yes
  else
    echo no
  fi
}

# ---------------------------------------------------------------- install
put_file() { # src dst -> dst becomes an executable copy of src, atomically
  # mktemp creates the temp file exclusively under an unpredictable name, so a symlink planted
  # at a guessable name cannot redirect the write or the chmod; mv -f replaces dst itself.
  local t
  t=$(mktemp "$2.XXXXXX") || return 1
  { cat "$1" > "$t" && chmod 755 "$t" && mv -f "$t" "$2"; } || { rm -f "$t"; return 1; }
}

install_hook() { # hooks_dir name -> prints one status word; non-zero on ERROR
  local dir="$1" name="$2" target="$1/$2" body status
  body=$(mktemp "${TMPDIR:-/tmp}/leak-guards-body.XXXXXX") || { echo "ERROR(mktemp)"; return 1; }
  case "$name" in pre-commit) emit_precommit > "$body" ;; pre-push) emit_prepush > "$body" ;; esac
  if [ -e "$target" ] || [ -L "$target" ]; then
    if grep -q "$MARK" "$target" 2>/dev/null; then
      if cmp -s "$body" "$target"; then status=unchanged; else status=updated; fi
    elif has_foreign_guard "$target" "$name"; then
      rm -f "$body"; echo "kept-already-guarded"; return 0
    elif [ -e "$target.local" ] || [ -L "$target.local" ]; then
      rm -f "$body"; echo "ERROR($name.local-exists)"; return 1
    else
      status=chained
    fi
  else
    status=installed
  fi
  if [ "$status" != unchanged ] && [ "$dry" != 1 ]; then
    mkdir -p "$dir" || { rm -f "$body"; echo "ERROR(mkdir)"; return 1; }
    if [ "$status" = chained ]; then
      mv "$target" "$target.local" || { rm -f "$body"; echo "ERROR(rename-old-hook)"; return 1; }
    fi
    put_file "$body" "$target" || { rm -f "$body"; echo "ERROR(write)"; return 1; }
  fi
  rm -f "$body"
  if [ "$dry" = 1 ] && [ "$status" != unchanged ]; then echo "would-be-$status"; else echo "$status"; fi
}

# ---------------------------------------------------------------- main
mode=""; dry=0; roots=()
while [ $# -gt 0 ]; do
  case "$1" in
    --check|--install) [ -z "$mode" ] || die "give one verb only"; mode="${1#--}" ;;
    --dry-run) dry=1 ;;
    --skip) [ $# -ge 2 ] || die "--skip needs a directory name"; SKIP_NAMES="$SKIP_NAMES $2"; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unknown option: $1" ;;
    *) roots+=("$1") ;;
  esac
  shift
done
[ -n "$mode" ] || { usage >&2; exit 64; }
[ "${#roots[@]}" -gt 0 ] || die "give at least one root directory (there is no default)"
[ "$dry" = 0 ] || [ "$mode" = install ] || die "--dry-run goes with --install"
for r in "${roots[@]}"; do [ -d "$r" ] || die "not a directory: $r"; done
command -v git >/dev/null 2>&1 || die "git not found"

# a hook run from inside another git operation must not leak that repo's env into ours
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE

list=$(mktemp "${TMPDIR:-/tmp}/leak-guards-list.XXXXXX") || die "mktemp failed"
trap 'rm -f "$list"' EXIT
list_repos > "$list"

have_gl=no; command -v gitleaks >/dev/null 2>&1 && have_gl=yes
nrepo=0; nbad=0; nerr=0; ncustom=0; nskip=0; tab=$(printf '\t')

while IFS= read -r repo; do
  nrepo=$((nrepo + 1))
  unsafe=""
  if unsafe_path "$repo/.git"; then
    # judged BEFORE git reads this repo's config: git run as root inside a repo another account
    # controls is the very thing git's "dubious ownership" check exists to stop
    unsafe=skipped-not-owned; hd="$repo/.git/hooks"; hp=unknown
  else
    if ! hd=$(hooks_dir "$repo"); then
      printf '%s\tERROR=cannot-read-repo\n' "$repo"; nerr=$((nerr + 1)); continue
    fi
    hp=default
    if git -C "$repo" config --get core.hooksPath >/dev/null 2>&1; then hp=custom; ncustom=$((ncustom + 1)); fi
    if repo_unsafe "$repo" "$hd"; then unsafe=skipped-not-owned; fi
  fi
  [ -z "$unsafe" ] || nskip=$((nskip + 1))
  if [ "$mode" = check ]; then
    pc=$(guard_state "$hd/pre-commit" pre-commit); pp=$(guard_state "$hd/pre-push" pre-push)
    printf '%s\tpre-commit=%s\tpre-push=%s\tgitleaks=%s\thooksPath=%s%s\n' "$repo" "$pc" "$pp" "$have_gl" "$hp" "${unsafe:+$tab$unsafe}"
    if [ "$pc" = no ] || [ "$pp" = no ]; then nbad=$((nbad + 1)); fi
  elif [ -n "$unsafe" ]; then
    printf '%s\tpre-commit=%s\tpre-push=%s\thooksPath=%s\n' "$repo" "$unsafe" "$unsafe" "$hp"
  else
    pc=$(install_hook "$hd" pre-commit); rc1=$?
    pp=$(install_hook "$hd" pre-push);   rc2=$?
    printf '%s\tpre-commit=%s\tpre-push=%s\thooksPath=%s\n' "$repo" "$pc" "$pp" "$hp"
    if [ "$rc1" -ne 0 ] || [ "$rc2" -ne 0 ]; then nerr=$((nerr + 1)); fi
  fi
done < "$list"

printf '# %s repos=%s without-guard=%s skipped-not-owned=%s errors=%s custom-hooksPath=%s gitleaks=%s%s\n' \
  "$mode" "$nrepo" "$nbad" "$nskip" "$nerr" "$ncustom" "$have_gl" "$([ "$dry" = 1 ] && echo ' dry-run')"

# an install that skipped a repo left it unguarded: not a clean exit
if [ "$nbad" -gt 0 ] || [ "$nerr" -gt 0 ] || { [ "$mode" = install ] && [ "$nskip" -gt 0 ]; }; then exit 1; fi
if [ "$have_gl" = no ] && [ "${ALLOW_NO_GITLEAKS:-}" != 1 ]; then
  echo "leak-guards: gitleaks is NOT on PATH -- the guards do nothing on this machine until it is installed (ALLOW_NO_GITLEAKS=1 accepts that)." >&2
  exit 2
fi
exit 0
