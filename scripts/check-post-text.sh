#!/usr/bin/env bash
# check-post-text.sh — refuse text that reads as AI-written before it is published.
#
#   ./scripts/check-post-text.sh <file>...
#   cat draft.txt | ./scripts/check-post-text.sh -
#
# CEO 2026-09-17: every post goes out in his name, so it has to read like he
# typed it. The em dash is the clearest tell there is — a Thai phone keyboard
# has no key for it, so it only ever appears when something inserted it. Same
# for the other characters below. A written rule was not enough (this repo has
# lost that bet before), so the check lives in a script every draft must pass.
#
# Scope: text meant for publication. Internal docs and code are exempt — pass
# only the draft, not the whole repo.
set -uo pipefail

# char | name | what to use instead
BANNED=$'—|em dash|เว้นวรรค หรือขึ้นบรรทัดใหม่
–|en dash|-
…|ellipsis|... (จุดสามจุดพิมพ์เอง)
“|smart quote|"
”|smart quote|"
‘|smart quote|'"'"'
’|smart quote|'"'"'
·|middle dot|- หรือ /
→|arrow|-> หรือเขียนเป็นคำ
←|arrow|<- หรือเขียนเป็นคำ
×|multiplication sign|x'

scan() {          # $1=label  $2=path
  local label="$1" path="$2" bad=0
  while IFS='|' read -r ch name fix; do
    [ -z "$ch" ] && continue
    local hits
    hits=$(grep -n -- "$ch" "$path" 2>/dev/null) || continue
    [ -z "$hits" ] && continue
    bad=1
    printf '\033[31m  ✗ %s\033[0m  (%s)  ใช้แทน: %s\n' "$ch" "$name" "$fix"
    echo "$hits" | head -5 | sed 's/^/      /'
    local n; n=$(echo "$hits" | wc -l)
    [ "$n" -gt 5 ] && echo "      ... อีก $((n-5)) บรรทัด"
  done <<< "$BANNED"
  if [ "$bad" -eq 0 ]; then
    printf '\033[32m  ✓ %s ผ่าน\033[0m\n' "$label"; return 0
  fi
  printf '\033[31m  → %s ไม่ผ่าน\033[0m\n' "$label"; return 1
}

[ $# -eq 0 ] && { echo "usage: $0 <file>... | -" >&2; exit 2; }
rc=0
for f in "$@"; do
  if [ "$f" = "-" ]; then
    tmp=$(mktemp); cat > "$tmp"; echo "stdin:"; scan "stdin" "$tmp" || rc=1; rm -f "$tmp"
  else
    [ -f "$f" ] || { echo "ไม่พบไฟล์: $f" >&2; rc=2; continue; }
    echo "$f:"; scan "$f" "$f" || rc=1
  fi
done
exit $rc
