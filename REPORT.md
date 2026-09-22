# task-ad534f86 — HQ step ② migration (LungNote + WarpClip umbrellas)

## Outcome summary — iteration 2: migration completed

Iteration 1 correctly stopped `--apply` before moving anything because
`/Users/gob/Projects/WarpClip-webapp` had 4 unpushed, unmerged branches. Per
CTO-FEEDBACK.md, the CTO pushed those 4 branches (no force, new refs) and
verified sha-for-sha on `PASAKON/WarpClip-Webapp`. I re-verified live via
`git ls-remote --heads origin` before touching anything, then re-ran the
migration: **`--plan` passed both duplicate checks, `--apply` moved all 7
repos, trashed both duplicates, trashed umbrella leftovers, created the
WarpClip compat symlink, and updated `hq.yaml`.**

The `--apply` process then crashed on the follow-up best-effort `hq.py
map`/`doctor` call with an unhandled `FileNotFoundError` — a real bug
(`HQ_PYTHON` defaulted to `<repo-root>/.venv/bin/python`, which doesn't exist
when the script runs from a worktree; the venv only exists in the main Agents
checkout). **The crash happened after all the real work had already
succeeded and been flushed to the manifest** — nothing was left half-done. I
fixed the bug (default now points at the real venv; the `hq.py` call is
wrapped so a follow-up tooling failure can never crash after a completed
migration), re-ran the equivalent `hq.py map`/`doctor` calls by hand to get
the required output, and fixed a related gap where some blocker messages
were only logged to the manifest in a final loop the crash had skipped.

**One real, unresolved item remains** (see Blockers): the LungNote umbrella's
703 MB stray worktree copy genuinely differs from the moved repos (91 diff
lines) — it was correctly left untouched and the LungNote symlink was
correctly skipped. `hq doctor` still reports **clean**, because its checks
don't cover this specific case (dotfile-prefixed leftovers are outside its
survey); I'm flagging it directly since doctor won't.

## Before / after table

| path | branch | HEAD sha | dirty | before | after |
|---|---|---|---|---|---|
| LungNote Webapp | main | `24a337c9` | 1 | `/Users/gob/LungNote Projects/webapp` | `/Users/gob/MoonieXHQ/Projects/LungNote/Webapp` |
| LungNote Wikis | main | `18291ccb` | 1 | `.../LungNote Projects/wikis` | `/Users/gob/MoonieXHQ/Projects/LungNote/Wikis` |
| LungNote Design | main | `f8454391` | 5 | `.../LungNote Projects/design` | `/Users/gob/MoonieXHQ/Projects/LungNote/Design` |
| LungNote Mcp | main | `fa36fef2` | 1 | `.../LungNote Projects/mcp` | `/Users/gob/MoonieXHQ/Projects/LungNote/Mcp` |
| WarpClip Webapp | main | `8e9fca00` | 0 | `/Users/gob/WarpClip Projects/webapp` | `/Users/gob/MoonieXHQ/Projects/WarpClip/Webapp` |
| WarpClip Wikis | wiki/cfo-budget-workflow | `66de2530` | 2 | `.../WarpClip Projects/wikis` | `/Users/gob/MoonieXHQ/Projects/WarpClip/Wikis` |
| WarpClip Design | main | `8bcf931e` | 1 | `.../WarpClip Projects/design` | `/Users/gob/MoonieXHQ/Projects/WarpClip/Design` |

All 7 verified post-move: `git status` works, `HEAD` sha unchanged, `git
remote -v` unchanged (script's own `move_and_verify` check, plus I re-checked
WarpClip Wikis by hand — branch `wiki/cfo-budget-workflow` and its dirty
state (1 modified + 1 untracked) survived the move byte-for-byte).

`/Users/gob/WarpClip Projects` is now a symlink → `/Users/gob/MoonieXHQ/Projects/WarpClip`.
`/Users/gob/LungNote Projects` is **still a real directory** (blocked — see below).

## Duplicate clones

Both trashed — every branch was either an exact match on live origin, or an
ancestor of origin's current default branch:

- `/Users/gob/Projects/WarpClip-webapp` → `~/.Trash/hq-step2-20260922T212639/WarpClip-webapp`
  (all 4 previously-unpushed branches now match origin exactly, per the CTO's push)
- `/Users/gob/Projects/WarpClip-design` → `~/.Trash/hq-step2-20260922T212639/WarpClip-design`

## Umbrella leftovers

Trashed unconditionally (loose metadata files, no diff-check needed):
`~/.Trash/hq-step2-20260922T212639/LungNote-Projects/{.DS_Store,.gitignore,.mcp.json,CLAUDE.md,README.md}`
and `~/.Trash/hq-step2-20260922T212639/WarpClip-Projects/{.DS_Store,.gitignore,CLAUDE.md,README.md}`.

**Not trashed — real blocker**: `/Users/gob/LungNote Projects/.claude/worktrees/fervent-noether-9ebf32`
(703 MB, confirmed not a git repo — `git status` fails there). Diffed its
`webapp/src` and `wikis` against the now-moved repos, excluding
node_modules/.next/.git/.obsidian:

```
webapp/src diff:  67 differing/only-in-one-side lines
wikis diff:       24 differing/only-in-one-side lines
```

Sample (full list in the manifest-adjacent blocker text, truncated to 5 by
the script): files only in the moved repo (`admin/`, `liff/`, `legal/`,
`MascotMark.tsx`, several `40-Decisions/*.md` entries added since the stray
copy was made) and files that differ (`layout.tsx`, `globals.css`,
`icon.svg`, several `40-Decisions` docs, etc.). This confirms iteration 1's
finding: **the stray worktree is a stale snapshot, not identical to the live
repo** — trashing it would not lose anything live-repo-side, but I'm not
auto-deleting 703 MB on a content mismatch without the CTO's yes. Because of
this, `/Users/gob/LungNote Projects` still exists as a real directory
containing only `.claude/worktrees/fervent-noether-9ebf32`, and the LungNote
compat symlink was correctly skipped.

## Manifest / yaml backup

- Manifest: `state/hq-step2-migration-20260922T212639.json` (28 ops: 7
  preflight, 9 repo/duplicate moves, 9 umbrella-leftover trashes, 1 symlink,
  1 yaml_backup, 1 yaml_edit).
- `hq.yaml` backup (pre-edit copy, for `--rollback`):
  `state/hq-step2-yaml-backup-20260922T212639.yaml`.
- `hq.yaml` rows for all 7 moved paths now have `current:` pointing at the
  new `/Users/gob/MoonieXHQ/Projects/...` paths, `duplicates:` removed from
  both WarpClip rows, and 7 new `dropped:` entries appended (existing
  comments/order/pre-existing `dropped:` entries preserved — verified by
  re-parsing with PyYAML and diffing the surrounding text by eye).
- **HQ repo (`~/MoonieXHQ`) was NOT committed**, per instruction — `git -C
  ~/MoonieXHQ status --short` shows `hq.yaml` and `MAP.md` modified,
  uncommitted, ready for the CTO.

## `hq.py map` / `hq.py doctor` (run by hand after fixing the crash)

```
$ .venv/bin/python scripts/hq.py map
MAP.md: 33 rows

$ .venv/bin/python scripts/hq.py doctor
hq doctor: clean — disk agrees with the map
```

**Caveat, read this**: doctor is clean by its own defined checks (every row's
`current` exists and matches its repo remote; no row lists a `duplicates`
path that's still present; no unmapped top-level dir under the 3 survey
roots). It does **not** check inside `/Users/gob/LungNote Projects` because
that directory's only remaining child (`.claude`) is dot-prefixed and
`hq.py`'s survey skips dotfiles. So "doctor clean" here does not mean the
LungNote umbrella is fully tidied — the 703 MB stray worktree above is real
and still there. I'm not silently trusting doctor's silence on this one.

## MCP proof (Deliverable 3 — now at the real new path)

```
$ printf '...' | node /Users/gob/MoonieXHQ/Projects/LungNote/Mcp/index.js
{"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":true}},"serverInfo":{"name":"lungnote","version":"1.2.0"}},"jsonrpc":"2.0","id":1}
```

No `.env`/secrets needed — the server answered directly from the new path.

## Files changed (this iteration, on top of iteration 1's commits)

- `scripts/hq_migrate_step2.py` — fixed `HQ_PYTHON` default (was a
  worktree-relative path that doesn't exist; now the real venv path),
  wrapped the `hq.py` map/doctor subprocess call so it can never crash after
  a completed migration, and fixed umbrella-leftover blockers to log to the
  manifest at detection time instead of only in a final summary loop.
- Real machine state (not repo files, listed for the record): 7 repos moved,
  2 duplicate clones + 9 umbrella-leftover files trashed, 1 symlink created,
  `~/MoonieXHQ/hq.yaml` + `MAP.md` modified (uncommitted, CTO's to commit).

## Tests

- ran: `.venv/bin/python -m pytest scripts/test_hq_migrate_step2.py -q`
  → **11 passed, 0 failed** (re-ran after the bugfix, still green)
- ran: `.venv/bin/python -m pytest scripts/ -q --ignore=scripts/test_skill_doctrine_lint.py`
  → same **3 pre-existing, unrelated failures** as iteration 1 (all in
  `scripts/test_install_claude_home.py`, a file this task never touched —
  see iteration 1 detail below), no new failures introduced by this
  iteration's script fix.

## Issues / Blockers

1. **LungNote stray worktree** (`/Users/gob/LungNote Projects/.claude/worktrees/fervent-noether-9ebf32`,
   703 MB) genuinely differs from the moved repos (91 diff lines across
   `webapp/src` + `wikis`) — left in place, not trashed, `/Users/gob/LungNote
   Projects` is not yet a symlink. CTO call needed: confirm the stray copy is
   safe to discard despite the differences (it's older/stale, nothing here
   suggests the live repo is missing anything from it) and I'll trash it +
   create the symlink on a follow-up, or the CTO does it directly with
   `mv "/Users/gob/LungNote Projects/.claude" ~/.Trash/... && rmdir
   "/Users/gob/LungNote Projects" && ln -s /Users/gob/MoonieXHQ/Projects/LungNote
   "/Users/gob/LungNote Projects"`.
2. `hq doctor`'s survey doesn't cover dotfile-prefixed leftovers (see caveat
   above) — not a blocker for this task, just flagging the gap since "doctor
   clean" could otherwise be misread as "fully tidied."

## Notes for Reviewer

- The `HQ_PYTHON` crash is a good example of why I'm glad the manifest writes
  incrementally (`Manifest._flush()` after every op) — every real op that
  happened before the crash was already on disk in the manifest, so nothing
  needed re-verifying from scratch; I could inspect the manifest and the real
  filesystem to confirm the migration was actually complete before touching
  anything further.
- I did not re-run `--apply` for this iteration's fix-and-verify pass —
  re-running it now would be unsafe (`hq.yaml`'s `current:` already points at
  the new locations, so a second `--apply` would try to move a repo onto
  itself and fail `move_and_verify`'s `dst.exists()` check). I instead ran
  `hq.py map`/`doctor` directly by hand once the script bug was fixed.
- 3 pre-existing test failures (iteration 1 detail, unchanged): all in
  `scripts/test_install_claude_home.py` (commit `0918dcd5`, predates this
  task), root cause a missing real asset dir `reel-editor-th/assets/mooniex-broll`
  — unrelated to HQ paths.

## Skill learning
- MISSING [hq-filing §Migration] : no guidance for when a CEO-approved "safe
  to delete" duplicate clone turns out to have real unpushed branches —
  resolved this run (CTO pushed them), but the skill still doesn't say what
  the follow-up verification step should be before trusting a "fixed" claim
  · evidence: this iteration re-verified all 4 shas live via
  `git ls-remote --heads origin` before running `--plan` again, rather than
  trusting CTO-FEEDBACK.md's claim at face value — worth writing down as the
  standard move.
- WRONG [none — caught by my own script's manifest, not by doctor] :
  `hq.py doctor`'s survey silently misses a real 703 MB leftover because it
  skips dotfile-prefixed top-level entries; "doctor clean" was true and
  still misleading about full umbrella-tidiness. Not this task's script to
  fix, but worth a line in `hq-filing` so a future reader doesn't treat
  "doctor clean" as "nothing left behind" · evidence:
  `/Users/gob/LungNote Projects/.claude/worktrees/fervent-noether-9ebf32`
  still present after a doctor run that printed "clean."
- COSTLY [no owner] : a subprocess call to a tool script (`hq.py`) that isn't
  the primary deliverable crashed the whole apply's exit path with an
  unhandled traceback, even though every consequential operation had already
  succeeded — cost one extra debugging round-trip that a bare
  `try/except OSError` around any "best-effort, nice-to-have" subprocess call
  would have prevented from the start · evidence: `hq_migrate_step2.py`
  commit `a6f63a86`, the fix.
