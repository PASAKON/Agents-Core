# task-3f8a31ae report: a joined node is itself (Org Mesh W4.4b)

## Summary
A node whose `node.yaml` carries a well-formed `host` + `os` + `hq_root` for a host that is not in `config/hosts.yaml` now resolves as itself, and `hosts()` carries an entry built from `node.yaml`. `ORG_HOST` naming that node resolves too, which mattered because `join.sh` step 9 sets it. `hq_join.HOST_RE` is now 3-31 chars, the one rule shared with `lib.config`.

## Files Changed
- lib/config.py — `hosts()` adds the synthesized entry for a valid node.yaml host that hosts.yaml does not declare; `_node_yaml_host()` and `_env_host()` resolve through `hosts()` only (no second "known host" test); new `HOST_NAME_RE`, `_load_node_yaml`, `_node_hq_root`, `_node_entry`, `_node_yaml_entry`; `import re`.
- tools/hq_join.py — `HOST_RE = config.HOST_NAME_RE` (pattern `[a-z][a-z0-9-]{1,29}[a-z0-9]`, 3-31); error text "3-31 chars".
- tests/test_w44b_self_host.py — new, 64 tests.
- tests/test_w41_hq_join.py — boundary: `"ab"` and `"x" * 32` refused, 3/31-char names accepted (mint + accept), accept refuses 32.

## Commits
- 67030be2 — config: a joined node's node.yaml host (host + os + hq_root) is itself, hosts() carries its entry; hq_join.HOST_RE 3-31
- 166c9df3 — config: one source of truth, self_host() resolves a node through hosts() only
- (report commit follows this file)

## Tests
- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (the worktree has no `.venv`; the main checkout's venv runs the worktree code, `config.__file__` checked)
- passed: 5214
- failed: 0
- skipped: 164 (63 of them the `pg` param of test_w41_hq_join, `ORG_TEST_DB_URL` unset, as before)
- new file alone: tests/test_w44b_self_host.py 64 passed; tests/test_w41_hq_join.py 63 passed, 63 skipped (was 33 test functions, now 35)
- scripts, run as scripts: `scripts/test_org_tools_registry.py` ALL PASS · `scripts/test_mcp_role_config.py` OK — 0 failure(s) · `scripts/test_tool_parity.py` ALL PASS
- mutation checks (each applied to a copy of lib/config.py, tests run, file restored): hosts() never synthesizes → 19 fail; hosts.yaml no longer wins (`if node:`) → 1 fail; hq_root not validated → 10 fail; rule back to 3-32 → 5 fail; `key not in hosts()` test removed → 22 fail. An earlier mutation (drop the redundant second "known host" clause) survived, which is why that clause is gone.

## What was synthesized, and why
`hosts()[<node host>]` =

| key | value | why |
|---|---|---|
| `os` | node.yaml `os` | read by `_platform_host`, `delegate` (launcher choice), `node_dispatch._spawn_worker_values` |
| `hq_root` | node.yaml `hq_root`, trailing separators cut | same key `hq_join.accept` stores in the hub's `config_json` |
| `agents_root` | `<hq_root>/Agents/Core` (`\` on windows) | `_root_match_host` matches ROOT against it; `delegate` indexes `host_cfg["agents_root"]`. Same layout as `hq_join._layout` and as Mac/Contabo. |
| `worktrees` | `<agents_root>/worktrees` | `node_dispatch._worktrees_root` and `delegate` index it |
| `ssh` | `None` | key must exist (`delegate` does `host_cfg["ssh"]`). `None`, not the host name the hub stores: a node never dials out to itself (`mac` has `ssh: null`), and a truthy `ssh` makes `tools/worker_reap` treat this box as a remote one. |
| `provides` | `[]` | same conservative default as `hq_join.accept`; the probe measures, it does not claim |
| `max_workers` | `1` | same as `hq_join.accept` |
| `runners` | `[]` | same as `hq_join.accept` |

A test (`test_the_entry_is_the_one_the_hub_keeps_for_that_node`) mints + accepts for linux, darwin and windows and asserts node view == hub `config_json` with `ssh` set to None.

Not copied into the entry: `remote_control`, `chrome_*` (hosts.yaml-only facts nobody measured on a joined node).

## Issues / Blockers
- **join.sh step 9 can still fail under sudo with a root HOME.** It runs `sudo env ORG_HOST=$HOST ... probe`; its own comment says root's HOME often lacks node.yaml. Then `ORG_HOST` names a host with no `os`/`hq_root` anywhere, so `_env_host` still raises "not a known host". That is deliberate (a bare name is not an identity; I did not guess os/hq_root from platform or ROOT). Fix is in `deploy/join/join.sh` (W4.3, outside my touches): pass `HOME="$HOME"` in the `env` of step 9. Not done by me.
- **`tools/infisical_setup.py:389` `NODE_HOST_RE` is still 3-32** (`{1,30}`), comment says "same shape as tools/hq_join.HOST_RE". Outside my touches, not edited. Harm today is nil (hq_join refuses 32 before `mint_node_secret` is reached), but it is a third copy of the rule and now off by one from the other two. Suggest `NODE_HOST_RE = config.HOST_NAME_RE` or `{1,29}` in a follow-up. I did not add a parity test for it because it would fail today.
- **`docs/ops/hq-join.md:34` says "3 to 32 chars".** Outside touches; one-word doc fix.
- **`lib/db.seed_hosts_from_config()` iterates `config.hosts()`** and writes `config_json`. No automatic caller exists (grep: none outside tests and the `hq_join` error text), so nothing runs it on a node. If someone ran it by hand on a joined node against the hub ledger, the synthesized entry (`ssh: None`, `provides: []`) would overwrite the hub's row for that node. Follow-up: skip names that are not in hosts.yaml. `lib/db.py` is outside touches.

## Notes for Reviewer
- `self_host()` precedence is unchanged: env > node.yaml > root > platform. Only what counts as "known" changed, and it is one test now, `key in hosts()`.
- `hosts()` is `lru_cache`d, as before. A node.yaml written after the first call is seen by the next process (join.sh step 9 is a fresh process). `hosts()` never raises because of node.yaml (bad file = no synthesized entry); `self_host()` still raises for it, so a bad node.yaml is reported where identity is asked for.
- Unreadable node.yaml: YAML syntax errors raise as before. A document that is not a mapping used to raise `AttributeError` by accident (`list.get`); it now raises `ValueError` with a message. Still raises.
- Side effect, safer: on a joined **linux** box `_platform_host()` used to answer `contabo` for any Linux machine (one linux entry). With the node's own entry there are two linux entries, so the platform source is ambiguous and returns None. node.yaml wins earlier anyway; Contabo itself has no synthesized entry and is unchanged.
- hq_root rule is written twice (lib/config cannot import tools/hq_join, which imports it). `test_node_hq_root_agrees_with_what_hq_join_accepts` compares both over 19 cases and also checks `agents_root`/`worktrees` against `hq_join._layout`.
- `HOST_RE` now lives in lib/config as `HOST_NAME_RE`; `hq_join.HOST_RE is config.HOST_NAME_RE` is asserted. `NAME_RE` in infisical_setup is untouched and pinned by a test (`^[a-z][a-z0-9-]{1,30}$`).
- Probe test: `nd.dispatch("probe")` and `nd.main(["probe"])` with node.yaml for `node-a`, `ORG_HOST` unset and set (as join.sh sets it), no hosts.yaml entry: ok, host == node-a, row written, last stdout line is the JSON join.sh parses. A host node.yaml cannot vouch for still fails the probe with exit 1. Detectors, git, vm_stat and `which` are stubbed; HOME, NODE_CONFIG_PATH and the ledger are tmp. No live contact; real `~/.config/mooniex/node.yaml` and `config/hosts.yaml` untouched.
- join.sh was not in my worktree (W4.3 unmerged); I read it with `git show agent/developer-task-e84797d7:deploy/join/join.sh`. Step 9 verb: `infisical_setup.py run Agents-Core prod --as $HOST -- python -m tools.node_dispatch probe`.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §kickoff brief] : the brief says `.venv/bin/python -m pytest`, but a worktree has no `.venv` (exit 127). The runnable interpreter is the main checkout's `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`; the worktree's own code still loads (tests put ROOT first on sys.path). The brief should name that path · evidence: task-3f8a31ae, `ls .venv` → "no such file"
- MISSING [CXO_Protocol_DevSpawn §kickoff brief] : task named `deploy/join/join.sh` as the thing to read, but it lives only on an unmerged sibling branch (`agent/developer-task-e84797d7`). A brief that depends on an unmerged sibling's file should name the branch to `git show` it from · evidence: task-3f8a31ae, `ls deploy` → `systemd` only
- MISSING [CXO_Protocol_DevSpawn §brief / identity tasks] : the brief framed the failure as node.yaml only; the real probe also sets `ORG_HOST`, so fixing node.yaml alone would have left the probe failing in the normal case. A brief for a resolution-order fix should list every source that can raise, not one · evidence: join.sh `do_probe` (`env ORG_HOST="$HOST"`), tests `org_host_as_join_sh_sets_it`
- COSTLY [no owner] : a mutation check ended with `git checkout lib/config.py`, which restored the last commit and silently dropped my uncommitted edits; found only because the next run's numbers did not match. Commit first, mutate a copy, restore by `cp` · evidence: task-3f8a31ae, between 67030be2 and 166c9df3
- COSTLY [no owner] : a mutation that survives is information: two "known host" tests in a row were redundant because `hosts()` already carried the entry. Dropping the survivor shrank the code · evidence: commit 166c9df3
