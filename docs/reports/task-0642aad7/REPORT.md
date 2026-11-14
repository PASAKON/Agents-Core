# REPORT task-0642aad7

## Summary

Completed read-only Org Queue Audit A1 (CEO order `O-20261114-1701-56fb`) across `tools/`, `scripts/`, `lib/` of `Agents/Core`, plus `/opt/MoonieXHQ/Projects/MoonieX/Console/src`, `/opt/MoonieXHQ/Projects/MoonieX/ComfyRunpod`, and `/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/src`.

Delivered `docs/reports/org-queue-audit/A1-resources.md` containing:
1. **Master Resource Inventory Table** covering 36 shared resources across 8 categories (logged-in Chrome/CDP ports & Browser Homes, winbox screen/desktop/named-pipe, GPU/Colab/RunPod/Blender, paid credits, API quotas & runner buckets, Contabo renders, winbox MT5, and host capacity / path locks / merge gates / Run Inbox / daemon locks) with `name`, `users (file:line)`, `how it is guarded today` (`none` / `rule only` / `lock` / `queue`), `limit shape` (number and source `file:line`), `what a collision costs`, and `suggested kind` (`mutex` / `pool` / `rate`).
2. **Existing Lock Stores & Structural Flaws** (`lib/db.py:1360` `locks` TOCTOU `SELECT` then `INSERT OR REPLACE`, `Console/src/relay/locks.js` / `tools/home_lock.py` advisory-only `data/relay-locks.json`, `tools/pc_lease.py` vs. `session_guard.py` split-brain lock files on winbox, `ComfyRunpod` `vm_dir/lock`, and `.bl-render.lock` only acquired by `ilag_cut.py`).
3. **Existing Queue Stores & Structural Flaws** (`state/host_queue.jsonl`, `state/budget_queue.jsonl`, `state/disk_queue.jsonl` unlocked JSONL read-modify-writes and poll-only draining, Console `data/relay-requests.json` superseding instead of queuing, `ComfyRunpod` in-process `withQueueLock`, and `ClaudeFlow` `lineQueue.js`).
4. **`## Not checked / risk`** and **`## Skill learning`** sections.

## Files Changed

- `docs/reports/org-queue-audit/A1-resources.md` (created)
- `docs/reports/task-0642aad7/REPORT.md` (created)

## Validation Performed

- Verified every `file:line` citation directly against source files in `Agents/Core`, `MoonieX/Console/src`, `MoonieX/ComfyRunpod`, and `MoonieX/ClaudeFlow/src` using `read_file`.
- Confirmed all required sections and columns (`name`, `users (file:line)`, `how it is guarded today`, `limit shape`, `what a collision costs`, `suggested kind`, `## Not checked / risk`, `## Skill learning`) are present in `docs/reports/org-queue-audit/A1-resources.md`.
- Confirmed no code, config, or state files were modified, and no network, spend, or secret files (`.env`, Infisical machine identities, process envs, Codex auth) were accessed.

## Limitations

- Read-only static audit of the four repositories named in the brief (`Agents/Core`, `Console/src`, `ComfyRunpod`, `ClaudeFlow/src`); external sibling repos (`LinePoster`, `LineAutomation`, `ExpertAdvisor`, and Mac-only `mooniex-webapp`) were referenced via their caller boundaries.

## Blockers

- (none)

## Skill learning

- `CTO_Knowledge_AGY`: Using `read_file` with targeted line ranges across multi-repo paths (`/opt/MoonieXHQ/Projects/MoonieX/...`) completes cross-repo audits cleanly under the AGY file-tool contract without risking command allow-list termination.
- `ALL_Rules_Winbox_PCLease`: `tools/pc_lease.py:124-174` (`C:\Users\passg\PC_LEASE.json`), `windows/cookie-play-worktree/scripts/session_guard.py:30,86-123` (`exclusive.lock`), and `tools/winbox_desktop.py:135,160` (`MoonieX-GUI` scheduled task) operate independently today and should be unified under a single `winbox:screen` mutex lease.
