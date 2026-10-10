# REPORT task-2754b973

## Files changed
- tools/node_token_api.py: resolve the actual socket source with a replaceable, bounded `tailscale whois --json` subprocess using list arguments and a minimal environment. Validate Node.Name and compare its first DNS label with the requested hosts.host before reading host status or charging its grant window. Refuse mismatches as 403 node_mismatch and lookup failures as 403 whois_unavailable without exposing subprocess diagnostics. Also restrict the bridge exception to DRILL_HUB_ENV=1 in the service environment, 172.17.0.0/16, and the drill-YYYYMMDD-HHMMSS host format already used by scripts/drill-join.sh. All other non-tailnet sources are refused, including when the flag is unset, 0 or true; approval/status and sealing still apply.
- tools/node_token.py: map node_mismatch to exit 6 and whois_unavailable to exit 7, documented alongside existing exits; neither refusal retries.
- tests/test_w42b_node_token_api.py: explicitly simulate an authenticated caller in the existing database/route fixture; the new suite exercises the actual identity check.
- tests/test_w42b_node_token.py: simulate an authenticated caller for existing loopback end-to-end client tests.
- tests/test_w42b_node_token_whois.py: test match, mismatch, lookup errors/timeouts/malformed output, subprocess constraints, refusal before DB access or host rate charging, bridge flag/scope, left-row refusal, HTTP-handler responses and client exit mappings.

- docs/reports/task-2754b973/REPORT.md: record validation, registry evidence and unresolved drill/deployment blockers.

## Tests
- Final focused command: `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w42b_node_token_whois.py -o addopts="" -p no:warnings`
  - 31 passed in 3.66s. An intermediate run before the last two bridge-flag cases passed all 29 tests in 0.50s.
- Earlier focused run: same command, 3 failed, 26 passed in 1.12s. The three added HTTP tests attempted loopback sockets, which the sandbox denies. They now exercise the real HTTP handler with an in-memory response sink; the production socket path is unchanged.
- Full requested command: `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w42b_*.py tests/test_w47_drill_join.py -o addopts="" -p no:warnings`
  - 80 failed, 450 passed, 188 skipped, 3 errors in 431.31s (0:07:11). All 83 failure/error exceptions are PermissionError: [Errno 1] Operation not permitted from sandbox socket creation. The drill test file completed without failures. This run collected the initial 23 identity cases; the focused run above checks all 31 final cases. The later client loopback-fixture update cannot be exercised under the same socket restriction.
- `git diff --check`: passed.

## Not verified
- Actual Tailscale whois output and local API permissions under the org-node-token service account, including Mac and winbox names. config/hosts.yaml has host keys but no separate Tailscale node-name field. Existing join.sh and join.ps1 explicitly pass the registered host to `tailscale up --hostname`; the implementation uses that existing convention, without inventing a registry field.
- Live token delivery, real Docker bridge/subnet/source NAT behavior, PostgreSQL role integration and the full live join drill. No network, live service, SSH, secret files or service configuration was accessed or changed.

## Blockers
- The live-drill acceptance is NOT complete. The existing DRILL_HUB_ENV=1 flag is a re-exec marker in scripts/drill-join.sh and does not propagate to the separately running token service. Enabling this exception for a real drill requires a service-environment/lifecycle arrangement outside the permitted files (deploy/node-token/org-node-token.service or its deployment configuration). The CTO must review and provide that wiring; merely setting the variable in the drill process cannot enable the service exception.
- The drill's post-leave token_answer probe originates from the hub, not the bridge container, and currently requires 403 left. With caller binding it receives node_mismatch first. That probe needs an agreed authenticated drill source or revised verification semantics before the live drill can pass. Its existing left-status assertion was not weakened to accept any identity refusal.
- The fixed allow-list is Docker's default 172.17.0.0/16 only, not every RFC1918 range. The live subnet must be verified before enabling the exception.
- The PostgreSQL-only HTTP role test in tests/test_w42b_node_token_role.py also needs an explicit mocked identity for its loopback callers. That file is outside the edit allow-list; it was not modified. Those tests are skipped here because no throwaway PostgreSQL URL is configured.
- Sandbox socket creation is denied (PermissionError: Operation not permitted), so existing socket-based tests require the review environment. No approval escalation is available.

## Skill learning
- (none)
