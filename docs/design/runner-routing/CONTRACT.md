# Runner routing — the contract between the router and the mesh

CEO 2026-09-29: delegation by usage belongs to CTO #24ca1c0a; talking across machines belongs to
CTO #e6754203 (Org Mesh, `docs/design/org-mesh.md`). This file is the one place both sides read.
Neither side's brief restates it; briefs link here.

## Who owns what

| | owner | files |
|---|---|---|
| WHICH runner (claude / codex / agy) and model, by quota and skill | router — CTO #24ca1c0a | `config/plans.yaml`, `tools/quota.py`, `tools/route.py`, `tools/model_stats.py`, `runners/agy_local.py`, the runner hook in `tools/delegate.py` (§3) |
| WHERE it runs (host), transport, liveness, report return, cross-host letters | mesh — CTO #e6754203 | `scripts/spawn-worker-remote.sh`, `windows/spawn-worker.ps1`, `runners/branch_poller.py`, `runners/worker_init.py` host logic, node agent, hub ledger |

A change inside the other side's files is asked for, not made — except a one-line fix that
unblocks a live run, which is announced to the owner the same hour.

## 1. What the router needs from the mesh

1. **Runners per host, measured.** A host lists a runner only when its CLI is on PATH and signed
   in (today `config/hosts.yaml runners:` is typed by hand and was wrong for winbox after the
   2026-09-29 reset). Mesh W4 `provides` probe replaces it; until then hosts.yaml is the source.
2. **`delegate_task(host=H)` works from any hub for runner claude, codex and agy.** Today only the
   Mac is a hub.
3. **The report comes back to the row.** When a remote worker finishes, the hub row reaches
   `review` with the report text, for every runner:
   - claude: REPORT.md on the branch (exists today, but the row stays `in_progress`; CTO flips it by hand);
   - codex: the final message file (`.launch-<task>/codex-final.txt` on the spoke) is not pushed today;
   - agy on a spoke: the launcher keeps REPORT.md out of the commit, so the report never leaves the box.
4. **Launchers never commit their own files** (`.worker.pid`, TASK.md, `.org-task.json`, logs).
   Fixed for `.worker.pid` in e59cb64f.

## 2. What the mesh gets from the router

`tools/route.py`:

```python
def pick_runner(role: str, host: str, *, cfg: dict | None = None,
                quotas: dict | None = None, skill: dict | None = None) -> Choice | None
```

- `role` = the worker role on the task row (`developer`, `tester`, ...). `config/plans.yaml`
  `role_classes:` maps it to a router class (`dev_general`, ...). A role with no mapping returns
  `None` (= stay on claude, no routing).
- Returns the top `Choice` of `rank(class, quotas, skill, host, cfg)` (fields `candidate, runner,
  model, weekly, daily, skill, reason`), or `None` when no candidate is available on `host`.
- Never raises: any error returns `None`.
- Quotas are cached in-process for 300 s (`fetch_all_quotas` costs an ssh and a CLI call).

## 3. The hook in `delegate_task`

Right before the runner pre-flight (`resolved_runner = ...`):

- runs only when `tasks.runner` is NULL, `tasks.model_hint` is not `claude`, and env
  `ORG_ROUTER` is not `off`;
- calls `route.pick_runner(role, resolved_host)`; a `Choice` writes `tasks.runner` and a
  `delegate_log` line `router: <runner> — <reason>`; `None` or any exception leaves the row
  unchanged (claude);
- an explicit runner on the row is never overridden.

## 4. Status (update in place)

| item | state |
|---|---|
| Mac hub → Mac agy | live, task-8adeaa3c 2026-09-29 |
| Mac hub → Contabo codex | live, task-419e6c8c 2026-09-29 (row closed by hand) |
| Mac hub → Contabo agy | code in, not run live |
| Mac hub → winbox codex/agy | CLIs lost in the 2026-09-29 reset |
| any hub other than the Mac | mesh W0/W2 |
| §2 `pick_runner` + §3 hook | building 2026-09-29 (agy + codex workers) |
