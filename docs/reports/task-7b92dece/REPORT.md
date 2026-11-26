# REPORT task-7b92dece

## Finding / root cause

The historical exit-2 cause cannot be established uniquely from the permitted evidence. Missing/invalid startup configuration is consistent with the code; claiming a particular missing secret would be speculation. The reason an exit-2 failure remains failed is explicit: the installed unit has `RestartPreventExitStatus=2`, overriding `Restart=on-failure`. The failure date (3 November) and rotated journal are supplied by the brief, not independently verified here.

No demonstrated code defect warrants a fix. No service was started, restarted, reset, or changed; no credential file or secret value was read, and no Infisical command was executed.

## Evidence

- `id org-node-token` succeeded: uid 993, gid 983, supplementary group 983. The account exists now.
- Read `/etc/systemd/system/org-node-token.service`: its ExecStart matches the brief's nested fetches, privilege drop and explicit `--port 8792`. It uses `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` for the API and `/usr/bin/python3` for the two Infisical wrappers.
- `systemctl show org-node-token.service` with selected state/ExecStart properties failed: `Failed to connect to bus: Operation not permitted`. Loaded state and drop-ins remain unverified.
- `/bin/sh deploy/node-token/bind-tailnet.sh /bin/true` returned 1 with the no-tailnet-address diagnostic. A separate `tailscale ip -4` identified the actual probe limitation: connecting to `/var/run/tailscale/tailscaled.sock` was denied (`operation not permitted`). This does **not** establish that the host lacks a tailnet address. The launcher hides tailscale stderr; its no-address branch is exit 1, not the reported exit 2.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m tools.node_token_api --help` exited 0 from this worktree. Imports and argument parser work with the requested interpreter; no listener or database connection was started. This was run as the worker, not as the service account.
- Read-only `git diff --no-index` comparisons confirmed the live checkout and worktree copies of `tools/infisical_setup.py`, `tools/node_token_api.py`, and `deploy/node-token/bind-tailnet.sh` are identical now. This does not prove their contents on 3 November.
- Deployment drift: the repository unit uses port 792 and setpriv bind capabilities; the installed unit uses 8792 without those capabilities. The explicit port is accepted by the parser, so this drift alone does not explain exit 2. Do not overwrite the installed unit as a speculative fix.

## Exit-2 paths reviewed

| Component | Exit-2 path / distinction |
| --- | --- |
| `bind-tailnet.sh` | No explicit exit 2; missing address exits 1. `exec` propagates the downstream status. Shell syntax/usage failures can also return 2, but none was demonstrated. |
| `infisical_setup.py:1168` | `cmd_run` exits `EXIT_NO_SECRETS` (2, defined at line 934) if a folder returns no named secrets: either Agents-Core prod `/node-token` or Org-Node prod `/` can stop the chain. |
| `infisical_setup.py:1203` | argparse rejects malformed arguments with 2. The visible unit arguments match the supported syntax, including splitting at the first `--`. Missing credentials, API errors, missing project, or missing child command use string `sys.exit`, hence 1. |
| `node_token_api.py:434` | argparse errors and startup validation use exit 2: absent/invalid tailnet bind, missing/blank required token, invalid token (over 4096 characters or internal whitespace/control characters), missing/blank `ORG_NODE_TOKEN_DB_URL`. |
| Later API startup | Database, age and socket startup failures return 1, not 2. |

The nested wrappers preserve the inherited environment and overlay fetched keys. A nonempty folder does not prove the required variable exists. Startup validation remains necessary even if both fetches succeeded. Neither actual folder content nor inherited configuration was inspected.

## Next action / exact Run-card command

First obtain the read-only unit-state and tailnet checks from an authorized host context; this sandbox cannot provide them. No secret-changing command is justified by current evidence.

If the owner elects to reproduce the failure under CEO approval, the exact one-line **Run-card payload**, not executed here, is:

```sh
systemctl restart org-node-token.service
```

This is a diagnostic restart, not a proven fix: it fetches secrets and may bring the service online. Before approving/executing, follow the repository's tmux cgroup restart check and review the loaded unit/drop-ins. Afterward inspect state and restricted startup diagnostics without exposing secret values. If a start-limit refusal is observed, prepare a separate reviewed recovery command; none was established here. No card was created (the worker contract provides no org tools).

## Files changed

- `docs/reports/task-7b92dece/REPORT.md` only. No production code or unit changes.

## Validation performed

- Account, unit-file inspection, venv help import, live/worktree comparisons and safe bind wrapper probe as above.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts='' -ra tests/test_w42b_node_token_api.py -k 'main or bind_tailnet or exit_2 or command_line_bind'`: **19 passed, 19 skipped, 250 deselected**. These cover startup refusal, bind forwarding/fail-closed behavior and exit-2 retry policy using fixtures; they do not launch the production service.
- An initial invocation without `-o addopts='' -ra` had the same totals. Repeated with configured quiet defaults disabled to expose skip reasons. All 19 skips are PostgreSQL parameter variants requiring an unset `ORG_TEST_DB_URL`; no live database was used.

## Not checked / risk

- Historical root cause remains unconfirmed because the original diagnostics are unavailable; current code alone cannot distinguish the exit-2 branches.
- Loaded systemd state, drop-ins, current tailnet address and historical failure time were not verifiable through this sandbox.
- No secret files, environment dump, Infisical access, database connectivity, age preflight, socket binding, or service-account execution was attempted. Help import success does not validate service-account permissions or the systemd sandbox.
- Port 8792 differs from the repository's privileged-port design. Unprivileged-port takeover risk described in the repository unit remains relevant; changing that deployment requires separate review.

## Blockers

- Sandbox denies systemd bus and tailscaled socket access. An authorized host-context read is needed to finish those checks; no permission workaround was attempted.
- A definitive failure diagnosis needs original startup diagnostics or an explicitly approved diagnostic restart. Secret presence cannot be inferred from filenames or code.
- The final worker-contract instruction assigns committing and pushing to the launcher; changes are left for it, with no default-branch mutation. If it commits this report, use `git commit -F` as requested in the brief.

## Skill learning

- (none)
