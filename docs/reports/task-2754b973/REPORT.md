# REPORT task-2754b973

## Files changed
- tools/node_token_api.py: restore the fail-closed whois check from round 1; replace DRILL_HUB_ENV with the CTO-approved exception for DRILL_HOST_RE hosts originating in DRILL_BRIDGE, from the accepted socket's local address, or from 127.0.0.0/8. Approval/status checks and sealing still apply. Document in two lines why core-host tailnet names do not matter and joined hosts match the first MagicDNS label.
- tools/node_token.py: restore distinct, documented exits 6 (node_mismatch) and 7 (whois_unavailable).
- tests/test_w42b_node_token_api.py: restore the authenticated-caller mock and accommodate the local socket address argument.
- tests/test_w42b_node_token.py: restore the authenticated-caller mock for loopback client tests and accommodate the local socket address argument.
- tests/test_w42b_node_token_role.py: give loopback role tests the same authenticated-caller mock, as authorized in round 2.
- tests/test_w42b_node_token_whois.py: replace flag-based cases with bridge/local/loopback exception coverage, another tailnet node's mismatch, non-drill bridge refusal and non-drill local-address whois checks. Verify left rows still return 403 left for bridge and hub probes; retain lookup failure, malformed output, timeout, rate-window and client-exit coverage.
- docs/reports/task-2754b973/REPORT.md: replace round 1 report with round 2 changes, validation and remaining review work.

## Tests
- `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w42b_node_token_whois.py tests/test_w42b_node_token_role.py tests/test_w42b_node_token_cards.py tests/test_w42b_join_check_db.py tests/test_w47_drill_join.py -o addopts="" -p no:warnings`
  - 177 passed, 44 skipped in 333.20s (0:05:33). Includes all 35 final identity cases and the unchanged stubbed drill suite; PostgreSQL role integration skips without ORG_TEST_DB_URL and psql.
- `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w42b_node_token.py -k 'not end_to_end and not test_the_environment_cannot_route_the_request_through_a_proxy and not test_a_redirect_is_not_followed' -o addopts="" -p no:warnings`
  - 215 passed, 9 deselected in 70.56s (0:01:10).
- `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w42b_node_token_api.py -k 'bind or load_tokens or missing_or_empty_token or value_that_is_not_a_token or main or unit or start_that_keeps_failing or exit_2_is_not_retried or service_port or default_sealer or age_that_hangs or age_child_gets' -o addopts="" -p no:warnings`
  - 41 passed, 41 skipped, 206 deselected in 16.59s. PostgreSQL variants skip without the throwaway database configuration.
- `git diff --check`: passed.

## Not verified
- Socket-based tests in tests/test_w42b_node_token_api.py and tests/test_w42b_node_token.py, plus PostgreSQL HTTP integration in tests/test_w42b_node_token_role.py, require CTO review outside the socket-denying sandbox. No socket restriction workaround was attempted; the full tests/test_w42b_*.py command was not rerun in round 2.
- Live Tailscale identity lookup/service-account permissions, actual Docker bridge routing, live token delivery and the full live join/leave drill still require the hub review environment. Mac/winbox live behavior was not exercised. scripts/drill-join.sh is unchanged.

## Blockers
- No remaining code blocker. The unavailable restore ref origin/agent/codex-task-task-2754b973 was a naming mismatch: the fetched origin/agent/codex-task-2754b973 points to first-round commit 71f8267d and contains all six requested files. Restored those files with git show from that ref without modifying .git.
- Final socket/live integration validation remains with the CTO. No services were changed, and no commit or push was made.

## Skill learning
- (none)
