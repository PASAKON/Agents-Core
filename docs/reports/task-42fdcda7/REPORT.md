# task-42fdcda7 — Org Mesh W2.7 security review of the dispatch mesh

Security engineer, 2026-09-30. Branch `agent/security_engineer-task-42fdcda7`.
Reviewed before any `org_dispatch` key is installed (W2.8) and before
`ORG_MESH_DISPATCH` goes live. Read-and-test only on the Mac: nothing installed,
no key generated, nothing under `~/.ssh` or `/etc/ssh` touched, no real ssh, tmux,
schtasks or create_worktree reached by any test.

## Trust model this review assumed

- The `org_dispatch` key protects a host against **off-box** callers: another
  dispatcher, or whoever copies the key. The verb table and argument patterns are
  that boundary.
- Workers, C-level sessions and node_dispatch run as **the same OS account** on
  each host. A worker can already do anything node_dispatch can; nothing here is
  a privilege boundary between them. Findings that need a same-account attacker
  are rated low for that reason.
- The hub ledger (SQLite today, Postgres through `ORG_DB_URL` later) is shared.
  Anything that can write a row can steer what reads it; a row is data, never a
  command.

## Findings

Severity is for the mesh as designed (flag on, keys installed). Iteration 1 fixed
what was inside the first touches; iteration 2 (CTO-FEEDBACK, touches widened to
12 paths) fixed F2 POSIX, F4, F9, F10, F12 and F14. The two deferred rows carry
their one-line fix.

| id | severity | file:line | failure scenario | fix | status |
|---|---|---|---|---|---|
| F1 | medium | `tools/node_dispatch.py` `verb_deliver_letter` (was :794) | Two overlapping `deliver_letter` calls for one letter (send_to_cxo's first dial and the watchdog retry, or a retry after lib.mesh gave up at 30 s while the far side still wrote) both passed the "not delivered" read and both wrote. Measured on the old code: **20 of 20** overlapping pairs wrote twice (40 inbox files for 20 letters); one delivery holds the window open for at least **0.71 s** (the wake's own sleeps), up to ~15.7 s with three 5 s tmux timeouts. The agent gets the same order twice. | Claim one `locks` row `letter:<id>:delivery` by `INSERT ... ON CONFLICT(key) DO NOTHING RETURNING` (SQLite and Postgres), TTL 120 s, re-read status under the claim; an overlapping call is refused (exit 2) and counts no attempt on the far side. | fixed 34a8edb3. After: **0 of 20** double writes, 20 files for 20 letters. Pinned by 4 tests. |
| F2 | medium | `tools/node_dispatch.py:311` `_task_on_this_host(task_id, allow_null_host=True)` | Any holder of an `org_dispatch` key can start the worker of **any** `pending` task whose `host` is NULL on the box it dials, including rows the hub never routed there. The only real caller, `delegate.mesh_spawn_worker` (`tools/delegate.py:1265`), always writes `host` first, so the NULL branch serves nobody. | `spawn_worker` requires `tasks.host == this host` on every OS. | fixed: Windows 34a8edb3, POSIX 68be41cf (CTO, iteration 2). `_task_on_this_host` has no NULL-host branch; `tests/test_node_dispatch.py` now expects a refusal for an unrouted row. |
| F3 | medium | `tools/node_dispatch.py` `verb_spawn_worker` win32 branch (CTO-FEEDBACK item 3) | The win32 path skipped all of `delegate_task`'s gating. On the normal path the hub already gated and took the path locks, so it passed. A direct key-holder call, or a row the hub never gated, started a worker with an unfinished dependency or with touches that overlap a task in flight (two workers on the same files, a stale base). | Read-only re-check before any PowerShell: host is this host, `db.unmet_dependencies`, `db.find_conflicts`. Locks stay the hub's. | fixed 34a8edb3, 13 tests. **Answer to item 3:** skipping the gating over ssh is acceptable only with this re-check; the hub's gate is the primary, this is the second lock. Browser cap and disk floor are not re-checked: F3b. |
| F3b | low | same | A direct call could start a worker on a box below the disk floor or over the browser-operator cap. The hub checks both before it dispatches. | Re-check the disk floor with `shutil.disk_usage` against the configured floor. | deferred to W2.8/W3 (CTO, iteration 2) |
| F4 | medium | `lib/mesh.py` `build_argv` (argv list at the end of the function) | `ssh` reads `~/.ssh/config` for the alias. With `ControlMaster`/`ControlPath` for `mooniex-vps` or `winbox`, a mesh call rides an admin connection that is already open and runs as a plain command under the **admin** key; the forced command is never used. Agent keys and config `IdentityFile`s are also offered when `org_dispatch` is refused, so W2.8's check can pass with the forced command missing. The command itself is plain validated tokens (fuzz below), so no injection. | Add `-o IdentitiesOnly=yes -o IdentityAgent=none -o ControlMaster=no -o ControlPath=none -o ForwardAgent=no -o ForwardX11=no -o ClearAllForwardings=yes -o PermitLocalCommand=no -o StrictHostKeyChecking=yes`. Residual after that: `IdentitiesOnly` still tries `IdentityFile`s named in the config for that alias, so give the mesh its own alias whose only identity is the dispatch key. | fixed 17efcc75: `lib/mesh.SSH_OPTIONS`, all 11 options on every call; `ssh -G -F none` parses them locally with no error. The dedicated `<host>-mesh` alias is written in `docs/ops/node-dispatch.md` for W2.8; `build_argv` reading a separate `mesh_ssh` field is a W2.8 code change. |
| F5 | low | `tools/node_dispatch.py` `verb_publish_branch` (`git push` stderr into the Failure), `_run`, `_audit` | `git push` over https prints the remote URL with its token on an auth failure (`https://x-access-token:ghp_...@github.com/...`). That text went to the reply (the dispatcher's logs and `delegate_log`) and the shared `events` row. Remotes are `git@` today, so no token is present now. | `_redact()` (URL userinfo, `ghp_`/`github_pat_`/`sk-` tokens, bearer values) on the reply error, the audit `error` and `raw`, `letters.last_error`, and the Windows spawn `delegate_log`. | fixed 34a8edb3 + bd14c721, 11 tests. |
| F6 | low | `tools/node_dispatch.py` `_append_worker_mailbox` (CTO-FEEDBACK item 4) | The `.resolve()` + `parents` check covers the worktree directory only (and realpath resolves a junctioned worktree on Python >= 3.8). The file itself was followed: a worker replaces `MAILBOX.md` with a symlink or hard link to any file the account can write (another worker's MAILBOX.md, a launcher `.cmd`), and `deliver_letter` appends a line there. Same account, so no privilege gain. | Refuse a symlink before opening; after opening require `st_nlink == 1` and `samestat(fstat, lstat)`. | fixed 34a8edb3, 3 tests (symlink, hard link, plain file still works). Hard-link check relies on Windows `st_nlink`; **not run on Windows**. |
| F7 | low | `docs/ops/node-dispatch.md:35` (old winbox line) | `command="cmd /c cd /d X && python -m tools.node_dispatch"`: Win32-OpenSSH runs a forced command as `cmd.exe /c <command>` (DefaultShell). The outer cmd splits on `&&`: the inner `cmd /c cd /d X` changes only its own directory, python starts in the profile directory and cannot import. Every mesh call to winbox would fail closed (MeshUnreachable). Not steerable: the line never references `SSH_ORIGINAL_COMMAND`. **Not verified on winbox.** | Absolute-path script with no shell syntax: `...\python.exe -E -s C:\...\tools\node_dispatch.py` (the module puts its repo root on `sys.path` itself; verified on the Mac from another cwd). | fixed cc23dab3 (doc), pinned by a doc test. |
| F8 | medium | `docs/ops/node-dispatch.md:32,35` (old) | One shared `org_dispatch` key with `from="100.64.0.0/10"`: every tailnet device (phones, shared nodes) is in range, so a key copied off any dispatcher works from any of them, and revoking it cuts every dispatcher at once. | One key per dispatcher; `from=` pinned to that dispatcher's tailnet address; `-E -s` on python. | fixed cc23dab3 (doc; W2.8 installs). Pinned: the doc test fails on `100.64.0.0/10`. |
| F9 | medium | `runners/watchdog.py:496` (`_remote_worktree_dir` :467) | `read_remote_heartbeat` runs `ssh <alias> type <root>\<project>__<role>__<task-id>\HEARTBEAT` under the **admin** key. ssh joins the argv into one string that cmd.exe (winbox) or the remote shell parses. `project` and `role` come from the task row unvalidated (`create_task`, `lib/org_tools_registry.py:148`, does not check them). A row with project `x & <command> &`, in_progress on winbox, runs `<command>` as the admin account on the next watchdog pass. Needs write access to the shared ledger (a compromised box, a prompt-injected agent with `create_task`). | Return None unless project and role fullmatch `[A-Za-z0-9_-]{1,64}` and id fullmatches `task-[0-9a-f]{8}`; later, move the read to a node_dispatch verb. | fixed 5416135f. Every token check fails closed before `subprocess.run`: 18 hostile values x 3 fields x 2 OS styles, zero ssh calls. The strict id pattern sits in `read_remote_heartbeat`; `_remote_worktree_dir` checks plain tokens only, because `scripts/test_watchdog_remote_heartbeat.py` (outside touches) builds a transcript path from id `task-abc123`. `tools/remote_worker_log.py` gets the token check through `_remote_worktree_dir`. |
| F10 | medium | `runners/relay_mcp_server.py:1137` `_spawn_c_level_mesh`; `tools/node_dispatch.py` `verb_start_clevel` | No cap and no rate limit. A prompt-injected or looping C-level calling `spawn_c_level` starts one paid Claude session per call on any host, until RAM or the plan runs out. | `start_clevel` refuses when the host already has N live sessions of that role; the relay rate-limits per caller. | fixed 8c58df45. N = 3 (CTO). `start_clevel` counts live `state/locks/<role>-<sid>.lock` files (pid alive, well-formed name) under a `locks` row `clevel:<host>:<role>:start` (TTL 300 s), so two overlapping starts cannot both pass; the 4th is exit 2. a7911a9a: a successful start keeps that row 60 s, because the launcher writes its lock file only after the verb returns; before that, 5 back-to-back starts with 2 live all launched (pinned: now 1 of 5). Relay: 3 `spawn_c_level` attempts that pass validation per 10 min per relay process; the 4th returns `rate_limited` with `retry_after_s`. Residuals under Not verified. |
| F11 | low | `lib/router.py:47` `_NEEDS_RE`; `tools/route.py:589` `_OVERRIDE_RE` | Both parse any line of the free-text description (`re.MULTILINE`). Text pasted into a description (a web page, a letter) can pin a task to a host (`needs:`) or satisfy the IRON §59 override gate (`override:`). Steering and denial of service only; nothing executes. | Parse directives only from a header block `create_task` writes, or store them in columns. | deferred to W2.8/W3 (CTO, iteration 2) |
| F12 | low | `runners/watchdog.py:534` `_retry_queued_remote` | Exactly one attempt per row per pass: confirmed and now pinned with 4 rows over 3 passes. But there is no per-host break: a host that times out instead of refusing (10 s connect timeout, up to 300 s for `spawn_worker`) costs rows x timeout per pass and stalls the watchdog. | After the first MeshUnreachable for a host in a pass, skip that host's other rows (as `_retry_letters` does). | fixed 5416135f. A pass stops dialling a host after one row comes back still `queued_remote` (`mesh_spawn_worker` swallows MeshUnreachable, so the status is the signal). Pinned: 3 rows per host on 2 silent hosts, one dial per host per pass; a host that answers keeps its turn. |
| F13 | low | `tools/node_dispatch.py` `_one_shot_task_script` | With `$ErrorActionPreference = 'Stop'`, a `Start-ScheduledTask` that threw skipped `Unregister-ScheduledTask`; the interactive task stayed registered and the same account could start it again later. | `try { Start; wait } finally { Unregister }`. | fixed bd14c721 (the commit message says "any worker on the box", meaning the same account). Rendered on the Mac; **not run under PowerShell**. |
| F14 | low | `lib/db.py:1399-1402` `record_letter_attempt` | The flip to `failed` at 5 attempts has no status guard, so a late count (a timeout while the far side delivered, or F1's new "being delivered" refusal counted by `send_to_cxo.dispatch_letter`) can turn a `delivered` letter into `failed`. No second delivery (`dispatch_letter` skips non-pending rows); the row just lies. | `UPDATE letters SET status='failed' WHERE id=? AND status='pending'`. | fixed 30748923. `lib/db_pg.py` has no copy of this function (it only translates SQL), so nothing is left outside touches. |
| F15 | low | `tools/node_dispatch.py` `_start_clevel_tmux` | `role` was put unquoted into the bash string for tmux. It only ever comes from `config.live_c_level_roles()`, never from the caller, so it takes a config edit to matter. | `shlex.quote(role)` (output unchanged for today's roles). | fixed 34a8edb3 |
| D1 | decision | `tools/node_dispatch.py` `_one_shot_task_script` / `_start_clevel_schtask` (CTO-FEEDBACK item 1) | One-shot interactive task per call vs a persistent CEO-registered task (MooniexCxoLaunch) that reads a request file. | **Keep the one-shot.** Same principal either way (Interactive, the logged-in account, Limited), so no privilege difference. The persistent task moves argument checking out of Python, where the allow-lists are fuzz-tested, into PowerShell that parses a file every same-account worker can write: any worker could plant a request and launch a C-level. It is also a standing trigger, while the one-shot exists for seconds and is now always unregistered (F13). | no change (CTO accepted, iteration 2) |

No finding is critical or high. After iteration 2 every medium row is fixed.
Two low rows stay open by CTO decision, deferred to W2.8/W3: F3b (disk floor and
browser cap on a direct `spawn_worker`) and F11 (directives parsed from free
text).

## CTO-FEEDBACK items

1. One-shot vs persistent scheduled task: D1. Keep the one-shot.
2. PowerShell allow-lists: confirmed, and pinned. An exhaustive scan of every BMP
   character, alone and at three places inside a valid sample, against all ten
   patterns (`_PS_SAFE_RE`, `_PS_ARGUMENT_RE`, `_PS_TOKEN_RE`, `_PS_REF_RE`,
   `_PS_REPO_URL_RE`, `_PS_CLAUDE_ARGS_RE`, `_PS_SESSION_NAME_RE`,
   `_PS_MODEL_RE`, `TASK_ID_RE`, `BRANCH_RE`) admits only printable ASCII, and
   none admits `'`, U+2018-U+201B, a newline or any control character, `$`, a
   backtick, `;`, `&`, `|`, `<`, `>`, `%`, `!` or `^`. `"` is admitted only by
   `_PS_ARGUMENT_RE`, and every value placed inside that argument passes
   `_ps_safe` first, so the only double quotes are the two around the launcher
   path. A test also fails if a future `_SPAWN_PARAMS` entry uses a pattern the
   scan does not cover. The builders were fuzzed with 6,000 cases (counts below).
3. win32 `spawn_worker` without gating: F3. Acceptable only with the read-only
   re-check, now in place.
4. `_append_worker_mailbox` containment: F6. The directory check was sound; the
   file was followed through a link. Fixed.

## CTO-FEEDBACK, iteration 2

Accepted as they stood: F1, F3, F5, F6, F7, F8, F13, F15 and D1. Decisions and
where each landed:

| item | decision | commit |
|---|---|---|
| F2 | `spawn_worker` needs `tasks.host == this host` on every OS; the POSIX pin in `tests/test_node_dispatch.py` flipped to a refusal | 68be41cf |
| F4 | the 11 ssh options in `lib/mesh.build_argv`, exactly as listed; `tests/test_w23_mesh_dispatch.py` updated; `<host>-mesh` alias note for W2.8 | 17efcc75 |
| F10 | N = 3 live sessions per role per host for `start_clevel`; relay 3 calls per caller session per 10 min, in memory | 8c58df45, a7911a9a |
| F9 | project and role `[A-Za-z0-9_-]{1,64}`, id `task-[0-9a-f]{8}`, else None; hostile values make zero ssh calls | 5416135f |
| F12 | per-host break in `_retry_queued_remote` after the first unanswered row in a pass | 5416135f |
| F14 | the `failed` flip only `WHERE status='pending'`; `lib/db_pg.py` has no copy | 30748923 |
| F3b, F11 | deferred to W2.8/W3 | open |
| docs | node-dispatch.md: NULL-host refusal, `start_clevel` cap, relay limit | aace4749 |

## Required checks

1. **Verb parser fuzz** (`tests/test_w27_security.py`, seeded `random.Random(0x42FDCDA7)`;
   hypothesis is not installed). Counts from the committed seed:

   | test | cases | accepted / built | refused |
   |---|---|---|---|
   | `run_command` with stubbed handlers (hostile strings, mutations of valid commands, structured) | 6,000 | 1,444 | 4,556 |
   | real handlers on an empty ledger (task and letter verbs the grammar accepts) | 1,500 | 224 reached a handler; all 224 refused at the row lookup | the other 1,276 are parser refusals or `probe`/`start_clevel`, covered above |
   | `main()` through `SSH_ORIGINAL_COMMAND`: exactly one ASCII JSON line, exit code as the grammar says | 400 | 346 checked | 54 skipped: NUL or a lone surrogate, which no environment can carry |
   | PowerShell builders (`_ps_safe`, `_one_shot_task_script`, `_spawn_worker_script`) | 6,000 | 2,201 | 3,799 |
   | win32 `start_clevel` end to end | 1,000 | 379 | 621 |
   | `lib/mesh.build_argv` | 6,000 | 1,664 | 4,336 |

   Every case: refused with exit 2 before any backend, exactly one audit row
   and nothing else in the ledger; or the exact allow-listed call, matching an
   independent copy of the W2 grammar, with every token plain ASCII
   `[a-z0-9_-]`. `subprocess.run`, `Popen`, `os.system`, `tmux_session.create`
   and `has_session`, `create_worktree`, `delegate_task`, `close_dev`, both
   `attempt_wake`s and `_run_powershell` are tripwires; zero reached.
   Mutation check: six deliberate regressions in node_dispatch (claim always
   wins, `\w` in the task id pattern, `'` in `_PS_SAFE_RE`, no win32 gate, no
   reply redaction, no control-character check) each fail 1 to 8 tests.
2. **The dispatch key gets no shell and no forwarding.** Server side: `restrict`
   = no port, agent or X11 forwarding, no pty, no `~/.ssh/rc`, plus any future
   restriction (sshd(8) line 413, OpenSSH_9.4p1 on this Mac), and `from=`.
   Inside the command: an AST test finds no `shell=`, no `os.system`/`popen`/
   `exec*`, and no string argv in `tools/node_dispatch.py` or `lib/mesh.py`. The
   only shell strings are the tmux command (every value allow-listed or
   generated; role now quoted) and PowerShell (`-EncodedCommand`, every value
   allow-listed). `lib/mesh.build_argv` only ever sends `[a-z_]+( [a-z0-9_-]+)*`,
   so even a host with the forced command missing receives nothing a shell would
   act on (6,000 cases). Client side: F4.
3. **Letters are idempotent under two concurrent `deliver_letter`**: F1. Measured
   20/20 double writes before, 0/20 after; the claim is a single `INSERT ... ON
   CONFLICT DO NOTHING RETURNING` on the primary key.
4. **`queued_remote` is retried exactly once per pass**: yes, and since F12 at
   most one dial per silent host per pass. The test queues 3 rows on contabo, 2 on
   winbox and one row of another dispatcher, and runs 3 passes against hosts that
   never answer: one dial per host per pass, no row dialled twice in a pass, the
   foreign row never. Against hosts that refuse, every row is dialled each pass.
5. **Audit rows never carry a secret**: payload keys are exactly `verb, args,
   caller, ok, error` (+ `raw` for an unparseable command); args are at most 8,
   each at most 256 characters; error at most 500. Nothing from the environment
   is ever written: canary values in `GH_TOKEN`, `GITHUB_TOKEN`,
   `ANTHROPIC_API_KEY` and `INFISICAL_TOKEN` never appear in any of the fuzz
   rows. What the child prints is redacted (F5), and a caller-typed credential
   in an unparseable command is redacted in `raw`.

## Mac sshd drop-in

`docs/ops/mac-sshd-hardening.md`: key-only (`AuthenticationMethods publickey`,
password and keyboard-interactive off, needed because macOS keeps `UsePAM yes`),
`AllowUsers gob@<dispatcher address>`, `DisableForwarding yes`, named `000-...` so
it wins over `100-macos.conf` (sshd keeps the first value), and a pf anchor for
tailnet-only. `ListenAddress` cannot do it on this Mac: launchd owns the ssh
socket on every interface (`ssh.plist`, inetd mode, Bonjour `ssh`/`sftp-ssh`).
Document only; nothing applied.

## Not verified

- Anything on winbox: DefaultShell, how the forced command line is parsed, `restrict`
  no-pty under ConPTY, Windows `st_nlink` for the hard-link check, the new
  `try/finally` under PowerShell (no PowerShell on this Mac). The W2.8 checks in
  `docs/ops/node-dispatch.md` cover each.
- The letter claim against Postgres. The SQL is standard (`ON CONFLICT DO NOTHING
  RETURNING`, placeholders translated by `lib/db_pg.py`), but `ORG_DB_URL` was not
  set and no Postgres was reached.
- The pf anchor in the Mac doc (read-only review).
- Contabo's sshd exposure on its public address: out of scope.
- F4 against a real server. `ssh -G -F none` parses every option on this Mac
  (OpenSSH_9.4p1) with no connection made. No mesh call was dialled.
  `StrictHostKeyChecking=yes` means W2.8 must record each far host's key in the
  dispatcher's `known_hosts` first, or every call is MeshUnreachable.
- F4 residual: until W2.8 gives `build_argv` a separate `mesh_ssh` alias, the
  admin alias's config `IdentityFile` lines are still offered when
  `org_dispatch` is refused (`IdentitiesOnly` does not drop them).
- F10 relay limit: it is per relay process. A C-level's relay lives as long as
  its session. The secretary starts `claude -p` per turn, so there the limit
  resets each turn. The node-side cap of 3 per role per host is the durable bound.
- F10 lock-file lag: every backend (iTerm tab, tmux session, scheduled task)
  returns before the launcher writes `state/locks/<role>-<sid>.lock`. The 60 s
  hold (a7911a9a) covers that gap only if the launcher reaches its lock line
  within 60 s. How long it takes was not measured live on any host. Side effect
  (CTO may veto): one successful start per role per host per 60 s.

## Tests

- `tests/test_w27_security.py`: 53 passed (about 10 s). The seven test files
  next to the change, run together after the code fixes: 813 passed.
- Full suite, once, sequentially, `.venv/bin/python -m pytest -p no:warnings`
  with `ORG_DB_URL` unset: **4661 passed, 14 failed, 28 skipped** in 869 s.
  All 14 failures are `tests/test_agy_browse.py::test_live_*`: a headless
  Chromium over CDP timed out (`TimeoutError`) under full-suite load. That file
  and its module are not in this branch's diff. The same file run alone right
  after: **80 passed** in 17.6 s. The failure is a load-dependent flake in that
  test's fixture, not a regression here.
- `scripts/test_org_tools_registry.py`: 29 PASS, 0 FAIL, "ALL PASS", exit 0.
- `scripts/test_mcp_role_config.py`: 57 PASS, 0 FAIL, "OK — 0 failure(s)", exit 0.
- Mutation check (above): 6 of 6 injected regressions caught.
- Letter race script (scratch, not committed): 20/20 double writes before F1,
  0/20 after.

Dependency audit: no `pip-audit`, `osv-scanner` or `safety` on this Mac, and the
task forbids installing one, so none was run. The branch changes no dependency
(`requirements.txt` untouched): CVEs introduced 0, removed 0.
