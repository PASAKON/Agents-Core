# Kit hub: one source for skills and org files on every machine

The CEO, 30 Oct 2026, relayed by PH#a2c (ChampaVeo, Mac):
"ให้ Contabo เป็นศูนย์กลางในการ merge โดย MAC และ Winbox สามารถเขียน skill หรืออื่นๆ ได้ และจะต้องส่งไปให้ CTO บน Contabo
ช่วยตรวจสอบว่า Conflict ไหม หรือทับกับของใครไหม ก่อน merge · และหลังจาก merge แล้ว เครื่องอื่นก่อนเริ่มทำงานต้องเช็ค Diff ของ
Github repo ของงานที่เกี่ยวข้องก่อนเสมอ". Owner: CTO Main (Contabo).

## What went wrong (measured 30 Oct)
- There were three different Agents-Core trees:
  - Contabo's live checkout was 462 commits ahead of `origin/main` and 6 behind;
  - the Mac's main checkout was 48 behind.
- 31 skills with the same name had different content on the Mac and Contabo. Two skills existed only on Contabo: `CMO_Knowledge_CinematicPrompts` and `CMO_Standard_HumanVoice_TH`.
- Causes:
  1. Contabo sessions commit to the live checkout's main.
     - A push hold on a60f1744 (10–27 Oct) and the rule "never push Contabo's local main" kept those commits off GitHub.
     - Nothing published them after the hold was lifted.
  2. `tools/kit_sync.py pull` at launch pulls Agents-Rules and Agents-Wikis only, never Agents-Core, where `.claude/skills` lives.
  3. Nothing told a session that its skills were stale. Sessions opened from the Claude app skip the launchers entirely.
- Fixed first: PR #570 publishes the 462 commits.

## Rules
1. **One source: `origin/main` on GitHub.** A skill, role, tool or doc exists for the org once it is on `origin/main`, and not before.
2. **One merger: CTO Main on Contabo.** A Mac or winbox session changes a shared file (skills, roles, tools, docs, config) this way:
   - work on a branch `kit/<host>/<sid8>-<topic>`, push it and open a PR to `main`;
   - send CTO Main one `report` letter with the PR number;
   - never commit a shared file on its own main.
3. **Contabo sessions keep committing on the live checkout's main** (it is what the org runs). The hub sync publishes those commits:
   - `tools/hub_sync.py` builds the branch `sync/contabo-main-<stamp>` as a merge of local main and `origin/main`, using `git merge-tree` and `git commit-tree`. It never touches the live checkout's tree or index.
   - Before the push it runs gitleaks over the range and `tools/publish_scan.py`. A finding stops the push and sends CTO Main a `blocker` letter.
   - Each run pushes a new branch (never a force push) and opens a PR. It closes the PR that the new one supersedes, then sends CTO Main one `report` letter.
   - A systemd timer runs it every 2 hours. A run does nothing while local main has no commit that origin lacks.
4. **The merge pass** (CTO job 5, one card per batch):
   - Each PR is checked: open, mergeable, CI fail-set ⊆ main's, head sha pinned.
   - `tools/kit_overlap.py` lists every file that two open PRs change, counting the hub sync PR. For a file on that list, CTO Main reads both diffs first (job 2). When two PRs change the same skill, one merges and the other author rebases.
   - The card merges in order with `--match-head-commit`. It then live-syncs Contabo (ff, else merge) and fast-forwards the winbox clone.
5. **Every session starts on `origin/main`.**
   - `tools/kit_sync.py pull` also pulls the Agents-Core checkout the session runs from.
     - The pull is ff-only, and is skipped when a tracked file is modified. Untracked files do not block it.
     - Contabo's live checkout is skipped: the merge card syncs it.
   - The SessionStart hook (`scripts/session-deadline-check.py`) prints one kit line from `tools/kit_sync.py check`. The hook also runs for sessions opened from the Claude app.
     - `kit ok`: HEAD contains `origin/main`.
     - `KIT STALE: N behind origin/main; skills that differ: …`: run `git pull --ff-only` before any work that needs those skills, or tell your C-level when you cannot.
     - `KIT UNPUBLISHED: N local commits` on the Mac or winbox: open the PR (rule 2).
   - A worker needs no check: its worktree is cut from `origin/main` when it spawns.
   - A PH whose brief names a skill checks that skill against `origin/main` first:
     `git fetch -q origin main && git diff --stat HEAD origin/main -- .claude/skills/<name>`.

## Build
| Step | Who | Done when |
|---|---|---|
| Publish the 462 commits | CTO Main, PR #570 | merged; Contabo's live checkout contains `origin/main` |
| Mac checkout to `origin/main` | Mac CTO | Mac HEAD contains `origin/main`; its local-only commits sent as a PR |
| winbox clone | CTO Main card after the T8 reboot test (30 Oct, 07:00 TH) | clone HEAD = `origin/main` |
| Core pull + kit line at SessionStart | worker task A | tests pass; a stale tree prints `KIT STALE` |
| `hub_sync`, `publish_scan`, `kit_overlap` + timer | worker task B | tests pass; a dry run on Contabo prints the plan; timer installed by a card |
| These rules in `CLAUDE.md` and `roles/cto.md` | CTO Main | merged |
