#!/usr/bin/env bash
# scripts/security/github-scan-report.sh -- READ-ONLY. For every repo of an owner (default PASAKON)
# print visibility and the two GitHub settings that stop a leaked key server-side:
# secret scanning and push protection. For each PUBLIC, non-archived repo where either one is not
# "enabled" it prints the exact `gh api -X PATCH` line that would turn both on.
# This script never runs a PATCH. The person who owns the settings pastes the lines they want.
#
#   github-scan-report.sh [owner]
#
# `security_and_analysis` is only returned to a token with admin rights on the repo; without them
# the two columns read "unknown" and no PATCH line is printed for that repo (the report says so).
# Output: repo names, visibility, and enabled/disabled/unknown. No secret values anywhere.

owner="${1:-PASAKON}"
command -v gh >/dev/null 2>&1 || { echo "github-scan-report: gh not found" >&2; exit 64; }

repos=$(gh repo list "$owner" --limit 200 --json name,visibility,isArchived \
  --jq '.[] | [.name, .visibility, (.isArchived|tostring)] | @tsv') || {
  echo "github-scan-report: gh repo list $owner failed (gh auth status?)" >&2; exit 1; }

n=0; open=0; unknown=0; patches=""
printf 'repo\tvisibility\tsecret_scanning\tpush_protection\tnote\n'
while IFS=$'\t' read -r name vis archived; do
  [ -n "$name" ] || continue
  n=$((n + 1))
  st=$(gh api "repos/$owner/$name" \
    --jq '[(.security_and_analysis.secret_scanning.status // "unknown"), (.security_and_analysis.secret_scanning_push_protection.status // "unknown")] | @tsv' 2>/dev/null) \
    || st=$'error\terror'
  ss=${st%%$'\t'*}; pp=${st##*$'\t'}
  note=""
  [ "$archived" = true ] && note="archived"
  if [ "$vis" = PUBLIC ] && [ "$archived" != true ]; then
    if [ "$ss" = unknown ] || [ "$pp" = unknown ] || [ "$ss" = error ]; then
      unknown=$((unknown + 1)); note="${note:+$note, }cannot read settings (token lacks admin?)"
    elif [ "$ss" != enabled ] || [ "$pp" != enabled ]; then
      open=$((open + 1)); note="${note:+$note, }PUBLIC and not fully protected"
      patches="${patches}gh api -X PATCH repos/$owner/$name -f 'security_and_analysis[secret_scanning][status]=enabled' -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'"$'\n'
    fi
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$vis" "$ss" "$pp" "$note"
done <<EOF
$repos
EOF

echo
echo "# repos=$n public-not-fully-protected=$open public-unreadable=$unknown owner=$owner"
if [ -n "$patches" ]; then
  echo "# NOT RUN -- to enable both on the public repos above, run (one per repo):"
  printf '%s' "$patches"
fi
