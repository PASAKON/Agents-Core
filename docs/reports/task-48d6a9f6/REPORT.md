# task-48d6a9f6 — OrgMesh P7: `kit` node_dispatch verb, mesh_check reads the Mac's KIT through it

**Update, task-5bbeca9c: the patch below is applied in the code, and the patch file is removed from the
tree.** The text that follows is the original report from before that, kept for the record.

**Status: PARTIAL, by the guard, not by choice.** Everything outside `tools/` and `lib/` is committed
on this branch. The three guarded files are NOT edited here; their exact, tested diff is below and in
`guarded-paths.patch` (same directory). A new task with `touches` for those three paths continues from
this branch: `git apply docs/reports/task-48d6a9f6/guarded-paths.patch` and the work is done.

## What blocked it

`scripts/hook-self-repo-guard.py` (ADR 0020) refused the first Edit to `tools/node_dispatch.py`:
"under tools/ — load-bearing org runtime. Task task-48d6a9f6 declared touches: (nothing declared)".
`touches` cannot be widened on a live task (Project Head, 2026-10-21 06:22Z). I did not route around the
guard: no Bash/Write into `tools/` or `lib/`. Refused paths:

| path | intended change |
|---|---|
| `tools/node_dispatch.py` | new `verb_kit()`, registered in `HANDLERS` and `_ARGSPEC` (no arguments) |
| `tools/mesh_check.py` | `_collect_peer_kit()` + `_kit_fail()`; `build_matrix` uses it for a peer with `mesh_ssh` and no `ssh` alias |
| `lib/mesh.py` | `kit` in the module docstring's verb list; `VERB_TIMEOUT_S["kit"] = 30` |

## Committed on this branch (allowed paths)

| path | change |
|---|---|
| `docs/ops/node-dispatch.md` | one table row for `kit` |
| `docs/ops/mesh-check.md` | one paragraph in the KIT section |
| `tests/test_node_dispatch.py` | 4 tests (+ params) for the verb: facts, host fallback, no args (5 shapes, exit 2), real `kit_facts` runs no `git fetch` and names no path |
| `tests/test_mesh_check_kit.py` | `_Peers` fixture + 8 tests (+ params): Mac KIT from a monkeypatched `mesh.dispatch`; `MeshUnreachable` / `ok:false` / no-facts reply = `FAIL(<reason>)`; winbox/contabo and hosts with an alias never use the verb; a peer with neither alias nor `mesh_ssh` is not dialled |
| `tests/test_mesh_check.py` | the autouse `isolate_kit` fixture also stubs `_collect_peer_kit`, so no existing matrix test can reach ssh once the patch lands |
| `tests/test_w27_security.py` | the file keeps its own copy of the verb grammar (`_GRAMMAR`); added `"kit": ()` to it and to `_valid_command`, and skipped `kit` in the "real handlers refuse unknown rows" test (it acts without a ledger row) |
| `tests/test_w23_mesh_dispatch.py` | `kit` goes out as the bare verb with a 30 s timeout; `kit` + argument refused before ssh |

**WARNING for whoever merges this branch alone:** until `guarded-paths.patch` is applied, 21 of the new or
changed tests fail (the 3 `test_w27_security` fuzz tests among them: their oracle now accepts `kit`, the
handler does not exist yet). Do not merge the branch without the patch.

## Verification (done in a scratch copy outside the runtime; nothing under `tools/` or `lib/` was touched here)

Scratch copy of this worktree minus `.git`, patch applied with `git apply` to the pristine `HEAD` versions
of the three files (applies cleanly; result byte-identical to the tested files).

- With the patch: `pytest tests/test_mesh_check.py tests/test_mesh_check_kit.py tests/test_mesh_check_l9.py
  tests/test_node_dispatch.py tests/test_node_dispatch_clevel_host.py tests/test_node_dispatch_spawn_ph.py
  tests/test_w23_mesh_dispatch.py tests/test_w33_node_dispatch_windows.py tests/test_w27_security.py
  tests/test_mesh_followups.py tests/test_l5_e2e.py tests/test_h1_node_probe.py` → **1339 passed, 0 failed,
  0 skipped** (285 s).
- Without the patch (the 3 files restored to `HEAD`, same tests): **21 failed**, all of them tests added or
  changed here: 9 in `test_mesh_check_kit.py`, 8 in `test_node_dispatch.py`, 1 in `test_w23_mesh_dispatch.py`,
  3 in `test_w27_security.py`. The baseline (before any edit) of the seven mesh/dispatch files was green.
  Two new regression guards (`test_a_host_with_an_ssh_alias_never_uses_the_verb`,
  `test_a_peer_with_neither_alias_nor_mesh_ssh_is_not_dialled`) and the `kit`+argument cases in the w23
  injection list pass either way: they pin behaviour that must not change.
- Real smoke, `verb_kit()` in-process (real `kit_facts`, no audit row): 8.2 s, 959 bytes; keys are
  `claude_home core deadline_hook deadline_script hooks iron_rules launcher mcp_names memory memory_pull
  memory_script role rules session_close session_open skills_home skills_repo wikis`; values are statuses,
  shas, counts and booleans; no `/root` or `/opt` path in the reply.

## Design notes the reviewer should look at

1. **Read-only and argument-free by construction.** `_ARGSPEC["kit"] = ()` makes any argument a refusal
   (exit 2) before the handler runs. The handler calls `kit_facts(host=...)` with no `fetch` and no
   `path_overrides`, so the dispatch key cannot choose a directory or trigger a network fetch. The tests pin
   the exact kwargs (`{"host": "mac"}`). What `kit_facts` itself runs is unchanged from `--local`: read-only
   `git` calls, `python3 --version`, the in-memory MCP-name build, and `install-claude-home.sh --check` only
   when the script has its no-mkdir guard.
2. **Host key** = `mesh_check._running_host_guess(ROOT)` (what `--local` uses), falling back to
   `config.self_host()` when it cannot say; if both fail the verb fails with that error rather than guessing
   a host's `kit_paths`.
3. **A refused or unreachable Mac is `FAIL(<reason>)`, not `UNREACHABLE(...)`.** The brief says "KIT FAIL
   with the reason", so the cell has no `kind`. Other mesh levels use `kind: "unreachable"` for that case;
   if the CTO prefers the other label it is one word in `_kit_fail`/`_collect_peer_kit`.
4. **The reason is sanitised** to one line with no `|`: it comes from remote stderr and is printed in a
   markdown table (a newline or pipe would break the KIT row).
5. **No identity check on the reply.** `probe` answers with its host name and `_node_reply_ok` compares it;
   `kit` returns the facts dict as the brief asks, so a mis-dialled `mesh_ssh` would be attributed to the
   dialled host. Same trust as the existing alias path, which also takes `peer["kit"]` as is.
6. **Old Mac, no `kit` verb yet:** it answers `ok:false, unknown verb 'kit'`, which shows as
   `FAIL(kit refused: unknown verb 'kit'. Known: ...)`. Deploy the verb to the Mac before relying on the row.

## The exact intended diff for the guarded paths

Also at `docs/reports/task-48d6a9f6/guarded-paths.patch`. Apply from the repo root with
`git apply docs/reports/task-48d6a9f6/guarded-paths.patch`.

```diff
--- a/lib/mesh.py
+++ b/lib/mesh.py
@@ -1,7 +1,7 @@
 """Org Mesh dispatch client (W2.3): one call to run a node_dispatch verb on a host.
 
 docs/design/org-mesh.md, W2. The server half is tools/node_dispatch.py: an
-enumerated verb list (`probe`, `pid_alive`, `spawn_worker`, `kill_worker`,
+enumerated verb list (`probe`, `kit`, `pid_alive`, `spawn_worker`, `kill_worker`,
 `start_clevel`, `deliver_letter`, `publish_branch`) that a caller can only NAME
 a hub row for, never send a shell to. This module is the client half:
 
@@ -69,6 +69,7 @@
 # numbers sit just above the ones node_dispatch and delegate already use
 # (spawn script 120 s + prompt delay; git push 120 s; launcher 300 s).
 VERB_TIMEOUT_S = {
+    "kit": 30,              # read-only git facts on the far side, no fetch (OrgMesh P7)
     "spawn_worker": 300,
     "start_clevel": 180,
     "spawn_ph": 120,        # ssh dial + the scheduled task's wait to reach Running (90 s cap)
--- a/tools/mesh_check.py
+++ b/tools/mesh_check.py
@@ -1890,6 +1890,30 @@
     return _try_json(_ssh_run(alias, piped_cmd, timeout=30, stdin_path=script_path))
 
 
+def _kit_fail(reason: str) -> dict:
+    # One markdown table cell: remote stderr can carry newlines and pipes.
+    return {"ok": False, "reason": " ".join(reason.split()).replace("|", "/")[:300], "facts": {}}
+
+
+def _collect_peer_kit(host: str) -> dict:
+    """KIT cell for a peer that has a `mesh_ssh` but no admin `ssh` alias (the
+    Mac, ADR 0034): its facts come from the read-only `kit` node_dispatch verb.
+    A host that does not answer, or answers ok:false, is a red cell with the
+    reason. Only KIT is collected this way; every other level for the host
+    stays as it is."""
+    mesh = _mesh()
+    try:
+        reply = mesh.dispatch(host, "kit")
+    except (mesh.MeshUnreachable, ValueError) as e:
+        return _kit_fail(str(e))
+    if reply.get("ok") is not True:
+        return _kit_fail(f"kit refused: {str(reply.get('error'))[:200]}")
+    facts = reply.get("result")
+    if not isinstance(facts, dict):
+        return _kit_fail("kit reply carried no facts")
+    return check_kit(facts)
+
+
 # ---------------------------------------------------------------------------
 # Default mode: own cells + collect peers + render + write state
 # ---------------------------------------------------------------------------
@@ -1920,7 +1944,11 @@
             cfg = config.host(h)
             alias = cfg.get("ssh")
             if not alias:
-                continue  # unreachable from here (e.g. mac when we are not mac)
+                # No admin alias (the Mac): only its KIT is read, through the
+                # `kit` verb. Its other levels stay as they are.
+                if cfg.get("mesh_ssh"):
+                    combined["KIT"][h][h] = _collect_peer_kit(h)
+                continue
             peer = _collect_peer_local(alias, cfg, script_path)
             if not peer:
                 continue
--- a/tools/node_dispatch.py
+++ b/tools/node_dispatch.py
@@ -474,6 +474,20 @@
     return facts
 
 
+def verb_kit() -> dict:
+    """This host's KIT facts (OrgMesh P7), for a peer that has no admin `ssh`
+    alias: the Mac reports its kit through here instead of a remote shell.
+
+    Read-only. tools.mesh_check.kit_facts is called with no `fetch`, so the
+    git facts describe the last fetched origin/main, and with no path
+    overrides: the verb takes no arguments, so the caller cannot point it at
+    a directory. Nothing is written beyond the audit row every verb leaves.
+    """
+    from tools import mesh_check  # lazy: a large module no other verb needs
+    host = mesh_check._running_host_guess(mesh_check.ROOT) or _self_host()
+    return mesh_check.kit_facts(host=host)
+
+
 # ---------------------------------------------------------------------------
 # workers
 # ---------------------------------------------------------------------------
@@ -1490,6 +1504,7 @@
 
 HANDLERS = {
     "probe": verb_probe,
+    "kit": verb_kit,
     "pid_alive": verb_pid_alive,
     "spawn_worker": verb_spawn_worker,
     "kill_worker": verb_kill_worker,
@@ -1503,6 +1518,7 @@
 # Exact argument patterns, in order. start_clevel has its own parser above.
 _ARGSPEC = {
     "probe": (),
+    "kit": (),
     "pid_alive": (TASK_ID_RE,),
     "spawn_worker": (TASK_ID_RE,),
     "kill_worker": (TASK_ID_RE,),
```
