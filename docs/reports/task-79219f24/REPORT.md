# task-79219f24 report: security review of the public join endpoint (Org Mesh W4.6)

## Summary

Review only. No code changed. The endpoint itself (tools/join_api.py) is in good shape: 256-bit
single-use tokens, stored as sha256 only, host-bound, one uniform 403, and bounded bodies. The
22 live requests confirmed every refusal path. The real risks sit around it:

- **Accept to provision has no human in the loop.** When `ORG_W42_PROVISION=1`, the watchdog
  auto-provisions whoever wins the accept race.
- **One node can read every Agents-Core secret.** The shared `org-node` identity is a viewer on
  all of Agents-Core.
- **The public process holds all Agents-Core prod secrets** in its environment, under a
  full-privilege database role.
- **Revocation depends on the `setup` identity**, which is due to be retired by 2026-10-10, and
  the client secrets never expire.
- **Windows credential files are readable by every local user**, and root on a node runs
  user-writable code.

Nothing is exploitable today without a leaked token. ORG_W42_PROVISION is OFF and no identity has
ever been minted. F1, F2 and F4 must be fixed before the flag goes on.

Reviewed at origin/main `d8a8a454`. **task-42aed98f (W4.4c) is NOT on origin/main.** Its four
commits exist only on `refs/heads/agent/developer-task-42aed98f`. The live `join.sh` is
byte-identical to main (request 1). I reviewed the 42aed98f diff where it touches this review
(join.sh step 9 `HOME="$HOME"`, NODE_HOST_RE); see F6.

## Findings

| id | severity | file:line | what | exploit sketch (one line) | fix (one line) |
|---|---|---|---|---|---|
| F1 | **high** (latent: live once ORG_W42_PROVISION=1) | runners/watchdog.py:800, tools/hq_join.py:634, tools/hq_join.py:290 | Every `pending_identity` row is auto-provisioned. Nothing checks that the age key and deploy key that arrived at /accept belong to the machine the operator is setting up. | Read the token during its 15-min window (Run Inbox card store, requester mailbox, node `ps`/history), then POST /accept first with your own age + ssh keys. The watchdog seals an org-node client secret (no TTL) to you and registers your read-only deploy key on PASAKON/Agents-Core. The real node's accept gets 403. Its `/sealed` fallback then says "already joined with this token" (same host, token used). It dies at the clone, because its own deploy key was never registered: a misleading error, not an alarm. | Add `hosts.approved_at`: join.sh prints the last 8 chars of its age recipient, and a Run Inbox approve card shows the same 8 chars. `provision_pending` skips unapproved rows. Also move accept ahead of the long install step. |
| F2 | **high** | tools/infisical_setup.py:407-436 (viewer at :433), PLAN.md §3 | `org-node` is viewer on Agents-Core. On Free a viewer sees dev and prod, so every node reads every Agents-Core secret. That includes ORG_DB_URL (role `org`), CLAUDE_CODE_OAUTH_TOKEN, Run Inbox tokens, OpenRouter, Drive OAuth/tokens and the LungNote client. | Compromise any one node (or prompt-inject one of its LLM workers: `run` puts every value in the worker's env). Now you hold the org's runtime secrets. This includes the hub DB, reachable as soon as the node is on the tailnet. | Create an Infisical project `Org-Node` holding only what a node needs (the Claude token; a least-privilege DB role if any). Give org-node viewer on that project only. |
| F3 | **medium** | deploy/join/org-join.service:36, tools/infisical_setup.py:691-708 | The public endpoint runs under `infisical_setup.py run Agents-Core prod`, so its environment holds every Agents-Core prod secret, not just ORG_DB_URL. It connects as the full `org` role. It runs as uid `secretary`, the same uid as the secretary service (same-uid `/proc/<pid>/environ`). There is no systemd sandboxing. | Any bug that leaks env or memory in join_api, or a compromise of the secretary service (same uid), yields every Agents-Core prod value plus full write on the hub. | Use `run ... --path /org-join` with a folder that holds only a DSN for a new role `org_join` (grants on join_tokens/hosts/node_secrets, `CONNECTION LIMIT 5`). Run as a dedicated system user. Add `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`. |
| F4 | **medium** | tools/infisical_setup.py:468, :97-98, :67; tools/hq_join.py:394-399 | Node client secrets have `ttl 0, numUsesLimit 0` (never expire). The only automated revoker (`wired_revokers` via `_live_org`) needs the `setup` org-admin credential, which PLAN §6 retires before 2026-10-10. After that, `leave --live` and `provision` fail with `not_admin_host`. org-node access tokens also renew to a 7-day max. | A node secret leaks after 2026-10-10. Nothing expires it, `leave --live` cannot revoke it, and it works from anywhere (Infisical Cloud is public) until the CEO finds it in the UI. | Before `retire-setup`, CEO rules which identity keeps "revoke org-node secrets". Set ttl to 90 d (radar row). Set org-node `accessTokenMaxTTL` = `accessTokenTTL` (1 d). Verify whether revoking a client secret kills access tokens already issued. |
| F5 | **medium** (default Windows ACL; not observed on winbox) | tools/infisical_setup.py:63, :146-157 (chmod :149), :169-171 | On Windows, `os.makedirs(mode=0o700)`, `os.chmod` and `os.open(...,0o600)` set no ACL. `C:\ProgramData\Infisical` inherits ProgramData's default `BUILTIN\Users:(OI)(CI)(RX)`. `require_root()` is a no-op on nt. | Any local non-admin account or low-privilege service on a Windows node (and on winbox) reads `C:\ProgramData\Infisical\<host>.env`: client id + secret. | In `write_cred` on nt: `icacls <dir> /inheritance:r /grant:r SYSTEM:F Administrators:F`. Same for the file. Check winbox now: `icacls C:\ProgramData\Infisical`. |
| F6 | **medium** | deploy/join/join.sh:532, :548 (+ `HOME="$HOME"` in 42aed98f) | Steps 8 and 9 run the user-owned clone (`$CORE/tools/infisical_setup.py`) as root. On macOS they also run the user-owned Homebrew python. With HOME kept (macOS sudoers default; explicit in 42aed98f), root python also loads the user's site-packages `.pth` files. The root-only 0600 credential therefore guards nothing against the node user, and `run` hands every secret to the child env anyway. | Any process running as the node user (an LLM worker included) edits `$CORE/tools/infisical_setup.py` or drops a `.pth`. The next root probe or `run` executes it as root, with the node's Infisical secret. | Pick one model. (a) A dedicated `orgnode` user owns the cred and runs workers; root never runs repo code. (b) `run` drops to `SUDO_USER` before exec, and `save` runs from a root-owned copy under `python3 -I`. At minimum add `-I` to root python calls. |
| F7 | **medium** | deploy/join/join.sh:472-474, deploy/join/join.ps1:400 | `StrictHostKeyChecking=accept-new` with a fresh, empty `$CONF_DIR/known_hosts`, so the first clone is trust-on-first-use. | A network MITM at join time (café Wi-Fi, ARP spoof) answers github.com:22 and serves a fake Agents-Core. Step 8 then runs its `tools/infisical_setup.py` as root with the decrypted identity on stdin. | Write GitHub's published host keys (api.github.com/meta `ssh_keys`) into `$CONF_DIR/known_hosts` before cloning. Use `StrictHostKeyChecking=yes`. |
| F8 | **medium** | tools/hq_join.py:672-688, :366-373 | `leave` revokes the node's own credentials only. Values the node already read stay valid: with F2 that is all of Agents-Core, including the shared CLAUDE_CODE_OAUTH_TOKEN. Nothing in the plan or output says so. | A compromised node is "left" (once G3/W2.8 land the status even reads `left`). The attacker keeps the Claude token, OpenRouter key and hub DSN they already copied. | Make `leave --live` print a "rotate what it could read" step (list from Infisical names), and treat a compromise-leave as a rotation event (procedure in area 6). |
| F9 | **low** | deploy/join/join.sh:4, :9; deploy/join/join.ps1:4; README.md:6,13 | Both documented forms put the token in shell history (`~/.bash_history`, `~/.zsh_history`, PS 5.1 `ConsoleHost_history.txt`). `sh -s -- --token` also keeps it in `sh` argv for the whole run, including step 2 installs before accept, so other local users can read it in `/proc/<pid>/cmdline`. | A local user on a shared box, or later disk access, reads the token. Before accept that is F1's race; after accept it opens only `/sealed` for 24 h (ciphertext). | When no token is given, prompt with `read` from `/dev/tty` (`stty -echo`), and document that form. Do accept before installs. |
| F10 | **low** | docs/ops/hq-join.md:156; tools/hq_join.py:204-221 | The Run Inbox mint card stores the token and mails it to the requester's session transcript. W4.1 asked W4.6 to rule. | Anyone with read access to the card store or that transcript during the 15 min has F1. | Ruling: acceptable only after F1's approval gate exists. Until then, purge or redact card output once `join_accept` is logged. |
| F11 | **low** | tools/join_api.py:344-345, lib/db_pg.py:426-458, deploy/join/docker-compose.join-proxy.yml:36 | Thread per request plus a thread-local pool means a new Postgres connection per request. Measured: 0.31-0.88 s for DB-path 403s vs 0.14-0.18 s for no-DB 403s. Up to ~127 concurrent requests (socat `pids_limit: 128`) can exceed Postgres `max_connections` (default 100), which the whole org shares. Slow-body connections can also fill the 128 socat slots. | Many source IPs (limit is 30/min/IP) send well-formed POSTs to /sealed: hub DB connections run out for every machine. Or ~5 IPs hold 127 slow connections and /org-join stops answering. | Put a `BoundedSemaphore(4)` around DB work in the routes, and set `CONNECTION LIMIT` on the F3 role. Add a traefik `buffering` or `inFlightReq` middleware on the router. |
| F12 | **low** | lib/config.py:353-358, :201 | `node.yaml` outranks the ROOT-path match in `self_host()`. A node.yaml on a core host that names another hosts.yaml host silently relabels that box. | Local write to the service user's `~/.config/mooniex/node.yaml` on Contabo or the Mac makes it act as another host (reaping, routing). This needs local write, so it is an integrity trap more than an attack. | Refuse node.yaml whose host is in hosts.yaml and disagrees with `_root_match_host()`. |
| F13 | **low** | tools/hq_join.py:189-199, :156-159 | Host names `setup` and `org-node` are mintable. A node named `setup` saves `/etc/infisical/setup.env`, the file `is_admin_host()` treats as the admin marker. | Confusion, not privilege: that node's code believes it is the admin host and tries admin calls with a node secret. | Reserve `setup`, `org-node`, and every `MACHINES` key in `_check_host`. |
| F14 | **low** (latent) | tools/hq_join.py:162-178 | `hq_root` allows `$`, backtick, `;`, quotes and spaces. It flows into `config_json` agents_root/worktrees. Readers use hosts.yaml today, but mesh_check/delegate build shell strings from agents_root once export-hosts feeds lib.config. | A token holder registers `hq_root=/x/$(cmd)`. Injection lands in whichever shell interpolates it; today that is the node's own shell. | Restrict to `[A-Za-z0-9 ._/\\:-]` at accept, and quote at every consumer. |
| F15 | **low** | tools/join_api.py:166-169; deploy/join/org-join.service:36 | The scripts are served from the live checkout's working tree. The unit's root leg (`bind-docker0.sh`, `infisical_setup.py`) runs from the same checkout. | Whoever can write `/opt/MoonieXHQ/Agents/Core` gets root on Contabo at the next restart, and root on the next node that joins. | Install a root-owned copy for the unit and served scripts. Put the sha256 of join.sh in the mint card. Verify now: `stat -c '%U:%G %a'` on those three files (root-owned, no g/o write). |
| F16 | info | tools/join_api.py:249-258 | Rate-limit key = last X-Forwarded-For entry. With traefik defaults (`forwardedHeaders` untrusted), traefik deletes the client's X-Forwarded-For and appends the peer. DNS is grey-cloud (A 194.233.80.26, no AAAA), so the peer is the real client. From the internet it cannot be spoofed. | Only a container on `n8n_default` (n8n workflows included) can reach 172.17.0.1:8791 directly and forge the header. Tokens are 256-bit, so this buys nothing. | Verify: `docker inspect n8n-traefik-1` args contain no `forwardedHeaders.insecure` or `trustedIPs`. |
| F17 | info (not wired) | tools/join_api.py:188-194; deploy/join/join.sh:430; join.ps1:354 | When G3 wires the minter, a tailnet pre-auth key is minted on every accept, before any approval. `tailscale up --auth-key <key>` puts it in argv. | With F1, the racer also joins the tailnet. Contabo `ts-input` accepts everything on tailscale0, which includes hub Postgres :5432. | Mint only after F1 approval. Add a tailnet ACL for `tag:org-node` (no :5432). Pass the key as `--auth-key=file:<path>` (check support on the pinned client). |
| F18 | info | (another service on webhook.mooniex.com) | Traefik normalises `/org-join/../../etc/passwd` and `/org-join/%2e%2e/...` before routing. Those requests went to another backend that echoes the path: `{"error":"Account etc/passwd not found"}`. | None for join_api, which never sees traversal. The other service reflects input. | Tell the owner of that router. Out of this lane. |

## Per-area verdicts

**1. Join token: OK.** One finding each: F1, F9, F10.

- **Entropy:** `token_urlsafe(32)` is 256 bits (hq_join.py:211). `TOKEN_RE` is checked with fullmatch.
- **TTL:** 15 min default, 60 max (:77-78, :208).
- **Single use:** one `UPDATE … WHERE used_at IS NULL AND expires_at > ? RETURNING` (:229-233).
- **Replay across hosts:** refused. `host` is in the WHERE, so a wrong host does not burn the token.
- **At rest:** sha256 only (:129).
- **Where it appears:**
  - Not in join_api logs: path, status and a validated host only (join_api.py:336).
  - Not in traefik access logs: body only, never the URL.
  - Not in curl argv: `hub_post` pipes the body on stdin.
  - It **is** in `sh` argv, shell history, the Run Inbox card store and the requester's transcript: F9, F10.
- **The real exposure is the pre-accept window.** Install (step 2) runs before accept (step 4), so the window is minutes. The auto-provision behind it turns a race into a full identity: F1.

**2. /sealed: OK.**

- **Uniform 403.** Every refusal is `403 {"error":"refused"}`. Confirmed live on five shapes: `sealed {}`, a bad-shape token, a random well-formed token with host `mac`, the same with `zz-none`, and accept with a random token (requests 3, 14-17).
- **No oracle between well-formed tokens.** Both queries always run (join_api.py:204-207). The only timing split is "shape valid → DB round trip" (~0.15-0.7 s extra, measured), and the token shape is public.
- **202/200/409 need a valid token.**
- **Leaked used token:** for 24 h the attacker learns pending vs ready and gets the armored ciphertext. That opens only with the node's age identity. It cannot re-accept: `used_at` is set.
- **Left hosts:** refused (:214). After revoke the ciphertext is NULL, so 403.
- **Hub outage:** the snapshot has no join tables, so the result is a uniform 500. It fails closed.

**3. Sealing: OK. The secret lifetime is a finding (F4).**

- **Recipients:** X25519 only, with bech32 checksum (hq_join.py:88, :145-153), re-checked in `seal()`.
- **Plaintext never leaves memory or pipes:**
  - It goes to `age` on stdin (sealed.py:87).
  - Error text is scrubbed (hq_join.py:532-536, sealed.py:73-74). The `mint_node_secret` error omits the body.
  - The node moves it `age -d | python | save --stdin` (join.sh:526-533). On Windows one python process does it.
  - No argv, no tempfile, no log.
- **`ttl 0 / numUsesLimit 0` is not acceptable as the steady state.** Two reasons:
  - The automated revoker dies with `setup` (≤ 2026-10-10).
  - Access tokens renew to 7 days.
- **Change:** ttl 90 d with a radar row, org-node `accessTokenMaxTTL = accessTokenTTL`, and a decided long-lived revoker identity (F4). Optionally, route node Infisical traffic via a Contabo exit node and set `accessTokenTrustedIps` to 194.233.80.26.

**4. Public surface: OK, apart from F3, F11 and F15.**

- **Rate limit:** 30/min per IP, in memory, per process. It is not spoofable through traefik defaults (F16). It is spoofable from `n8n_default` only.
- **Body:**
  - The 8 KB cap is enforced: live 9000 bytes → 413.
  - JSON only: text/plain → 415.
  - Chunked is refused: live → 411.
  - A JSON array → 400.
  - 3000-deep nesting → 400.
- **Paths:** exact dict match. `/org-joinX`, `join.sh.bak`, `GET sealed`, `OPTIONS` and `HEAD` all → 404 JSON. Traversal is normalised by traefik before routing (F18).
- **Host header:** ignored. `JOIN_API_PUBLIC_URL` is set, and the live script carries `HUB_DEFAULT="https://webhook.mooniex.com/org-join"`. The Host fallback builds `http://`, which join.sh refuses, so it fails closed.
- **Port 80:** 301 to https (live). There is no HSTS header; curl does not need one.
- **docker0 bind:** OK.
  - `check_bind` allows only loopback or 172.16/12.
  - Weak-host model: a Contabo L2 neighbour's packet to 172.17.0.1 arrives on eth0 and hits ufw's default-deny INPUT. The one allow rule is scoped to the n8n_default bridge interface.
  - Even an unscoped rule would leave a spoofed 172.18.x source blind: the SYN-ACK is routed to the bridge.
  - Confirm `ufw status verbose` shows `on br-…`.
- **socat container:** OK. It is read-only, uid 65534, `cap_drop ALL`, `no-new-privileges`, 32 MB, 128 pids, and publishes no ports. The tag is pinned but not by digest (noted in the file). `pids_limit` is also the connection cap (F11).

**5. Node side: findings F6, F7, F9, F12 and F17.**

- **Root:** join.sh runs as the user and uses sudo for install, `tailscale up`, `save` and the probe. Root then runs user-owned code (F6).
- **Tailscale key:** it is in argv, but the minter is not wired (F17).
- **Key modes:** OK.
  - The age identity uses umask 077 plus 600. The deploy and dispatch keys are 600. `CONF_DIR` and `~/.ssh` are 700.
  - Windows `Set-PrivateAcl` strips inheritance.
  - node.yaml holds nothing secret.
- **GIT_SSH_COMMAND:** it pins the deploy key only (`IdentitiesOnly`) with its own known_hosts. It is TOFU (F7).
- **node.yaml trust:** OK for a node, which can only lie to itself. It is a trap on core hosts (F12).

**6. Revocation: findings F4 and F8.**

- **`leave --live` with the flag and an admin host:**
  - It revokes the node's Infisical client secret by id, nulls the ciphertext, and deletes the GitHub deploy key.
  - It marks `left` only when every step is ok.
- **`_not_wired` steps:**
  - `tailscale_device` (G3).
  - `authorized_keys` on each other host (W2.8).
  - Today a live leave always ends `partial` (exit 1). Correct: no silent success.
- **Not revoked at all:**
  - Access tokens already issued (verify).
  - Everything the node already read (F8).
  - The node's clone of the private repo (unavoidable).

**Shared CLAUDE_CODE_OAUTH_TOKEN (one leak = every node).** Recommended procedure. Run it on any suspected leak, on every compromise-leave, and on a fixed cadence (90 d radar row):

1. **Mint the new token.** Run `claude setup-token` on the CEO's own machine, following CTO_Procedure_KeyFetch so no model sees the value. Pipe it straight into:
   `infisical_setup.py put Agents-Core prod CLAUDE_CODE_OAUTH_TOKEN --stdin`
   Metadata: `expires`, `owner`, `console_url`.
   After F2, the target is the `Org-Node` project.
2. **Verify it landed.** `infisical_setup.py last4 Agents-Core prod CLAUDE_CODE_OAUTH_TOKEN` must equal the last 4 characters the CEO saw.
3. **Restart every long-running holder.** A process that read the old value at start keeps it. `org-join.service` is one of them today (F3), plus the secretary and any `infisical run` unit. Nodes read the token per spawn, so new workers pick it up.
4. **Revoke the old token at claude.ai.** First confirm in the UI that claude.ai offers a per-token revoke for setup-tokens. If it offers none, the old token lives until its expiry. Write that down as the residual risk and tell the CEO.
5. **Record it.** On a leak, tag the Infisical secret `leaked` and add a rotation row with a `[LEAK]` tag (playbooks/secrets-rotation.md, "Compromise / leak procedure").

Better: give each node its own `setup-token`, stored as the same name under `/nodes/<host>` and read with `run --path`. On Free this does not isolate nodes from each other, but it lets you revoke one leaked token without cutting every node.

**7. Anything else:** F12 to F15, F18. Other things I checked and found fine:

- The accept race is serialized in SQL.
- The deploy-key comment is not stored.
- `_diagnose` codes never reach the wire.
- Exceptions are logged as class names only.
- The request line is never logged.
- `export-hosts` uses `yaml.safe_dump`.
- The `DEPLOY_PUBKEY_RE` shape is correct.
- The join scripts wrap everything in `main`, so a truncated `curl | sh` download does not execute.

## Live requests (22 of the 40 allowed; no real token; nothing written)

| # | request | status / body |
|---|---|---|
| 1 | GET join.sh | 200. `server: org-join`, `cache-control: no-store`, `nosniff`. Hub substituted as https. Identical to main's join.sh. |
| 2 | GET join.ps1 | 200 |
| 3 | POST sealed `{}` | 403 refused |
| 4 | POST accept `{}` | 400 bad_arg |
| 5 | GET sealed | 404 |
| 6 | GET `/org-join/../../etc/passwd` (path-as-is) | 404 from another backend: `Account etc/passwd not found` (F18) |
| 7 | GET `/org-join/%2e%2e/tools/join_api.py` | 404, same other backend |
| 8 | GET join.sh.bak | 404 |
| 9 | GET /org-joinX | 404 |
| 10 | OPTIONS join.sh | 404 |
| 11 | GET http:// join.sh | 301 |
| 12 | POST sealed text/plain | 415 |
| 13 | POST sealed chunked | 411 |
| 14 | sealed, random well-formed token, host=mac | 403 (0.88 s) |
| 15 | sealed, random well-formed token, host=zz-none | 403 (0.31 s) |
| 16 | sealed, bad-shape token | 403 (0.18 s) |
| 17 | accept, random token, valid fields | 403 (0.29 s) |
| 18 | sealed, 9000-byte body | 413 |
| 19 | sealed, `[]` | 400 |
| 20 | HEAD join.sh | 404 |
| 21 | sealed, 3000-deep nested JSON | 400 |
| 22 | GET http:// join.sh, redirect target | 301 to `https://webhook.mooniex.com/org-join/join.sh` |

Also: DNS A 194.233.80.26, no AAAA, NS Cloudflare with the record not proxied. No ssh, no Infisical, no GitHub writes.

## Files Changed
- docs/reports/task-79219f24/REPORT.md — this file (the only change).

## Commits
- (report commit follows this file)

## Tests
- ran: `git diff origin/main --stat` (proves only this report changed); 22 read-only HTTPS requests (table above)
- passed: 22 of 22 live checks behaved as the code says
- failed: 0
- skipped: dependency audit. No `pip-audit` or `osv-scanner` on this Mac or in `.venv`, and no install without justification. No dependency changed. Test suite not run (no code change, per brief).

## Issues / Blockers
- The brief says all W4.x work is merged on origin/main. task-42aed98f is not (`git merge-base --is-ancestor 1419b7d9 origin/main` → false). CTO: merge or drop it, and read F6 first, because it makes the root-with-user-HOME path explicit.
- Unverified without ssh; each needs one command on the box:
  - the traefik forwardedHeaders args (F16);
  - the `ufw` rule's interface scope (area 4);
  - checkout file ownership on Contabo (F15);
  - `icacls C:\ProgramData\Infisical` on winbox (F5);
  - whether Infisical revokes access tokens along with their client secret (F4).
- Model tier adequate for this review. Nothing here needs a higher tier.

## Notes for Reviewer
- threat model touched: yes. The trust boundary is the token plus the provision step (F1), and the Infisical project boundary (F2).
- secrets reviewed: yes, names and flows only. No value was read, printed or requested.
- CVEs introduced/removed: none (no dependency change; no scanner available).
- Order to fix before `ORG_W42_PROVISION=1`: F1 (approval gate), F2 (Org-Node project), F4 (revoker identity before retire-setup, 2026-10-10). F3 and F5 can follow in the same week.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §kickoff brief] : a review brief listed task-42aed98f's report as "merged on origin/main". It exists only on `refs/heads/agent/developer-task-42aed98f`. The brief should give the SHA each read is pinned to, and the worker should run `git merge-base --is-ancestor <sha> origin/main` before reviewing "merged" work · evidence: task-79219f24, commits 1419b7d9/088767df/fbe5bb2e/9e82df8f not ancestors of d8a8a454
- MISSING [shared DEV conventions §12 Shell scripts on this Mac] : two more zsh traps in one session. (1) `echo =====` fails with `(eval):1: ==== not found`, because zsh `=word` expands to a command path; use `echo '---'`. (2) `grep --include=*.py` fails with `no matches found` because zsh globs the unquoted pattern; quote it · evidence: task-79219f24, two failed Bash calls
- MISSING [no owner] : the Infisical secrets PLAN §6 retires `setup` by 2026-10-10. hq_join's revoke and provision both need that credential file, and no doc links the two. It belongs in the secrets-infisical PLAN or a skill before anyone runs `retire-setup` · evidence: tools/hq_join.py:394-399, docs/ops/infisical-p2-pilot-2026-09-28.md:57
