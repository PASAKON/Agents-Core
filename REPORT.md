# task-ad534f86 — HQ step ② migration (LungNote + WarpClip umbrellas)

## Outcome summary

Script, tests, and path repoints are done. The real `--apply` run correctly
**stopped before moving anything**, because `/Users/gob/Projects/WarpClip-webapp`
(the duplicate clone the CEO approved deleting) has 4 local branches that are
**not on GitHub and not merged** — real unpushed work, not a stale pointer.
Deleting that clone as originally planned would have destroyed it. This needs
a CTO decision before the migration can complete (options below).

## Before / after table (real machine, before this task's `--apply`)

| path (current) | branch | HEAD sha | dirty | ahead of upstream |
|---|---|---|---|---|
| `/Users/gob/LungNote Projects/webapp` | main | `24a337c9` | 1 | 0 |
| `/Users/gob/LungNote Projects/wikis` | main | `18291ccb` | 1 | 0 |
| `/Users/gob/LungNote Projects/design` | main | `f8454391` | 5 | 0 |
| `/Users/gob/LungNote Projects/mcp` | main | `fa36fef2` | 1 | 0 |
| `/Users/gob/WarpClip Projects/webapp` | main | `8e9fca00` | 0 | 8 → **pushed** |
| `/Users/gob/WarpClip Projects/wikis` | wiki/cfo-budget-workflow | `66de2530` | 2 | 0 |
| `/Users/gob/WarpClip Projects/design` | main | `8bcf931e` | 1 | 0 |

**After**: identical — no row moved (Phase A validation failed before Phase B).
The one real, deliberate change: `WarpClip Projects/webapp`'s `main` was pushed
(fast-forward, no force) — origin now has `8e9fca00` (verified via
`git ls-remote --heads origin`).

## Duplicate-clone safety check (live `ls-remote`, not cached refs)

- `/Users/gob/Projects/WarpClip-design` → **safe, would be trashed**: both
  feature branches are exact matches on origin; `main` is an ancestor of
  origin's current `main` (already merged/superseded).
- `/Users/gob/Projects/WarpClip-webapp` → **UNSAFE, blocks the whole run**:
  4 branches (`feat/hero-headline-marker-fix`, `feat/sections-v3-lime-redesign`,
  `feat/service-icons-og-tokens` — its own checked-out branch — and
  `feature/logo-integration`) exist **only** in this local clone, are **not**
  on origin under any name, and are **not** ancestors of origin's current
  `main`. Deleting this clone today would permanently lose that work.

## Pushes made

- `/Users/gob/WarpClip Projects/webapp` branch `main`, +8 commits, fast-forward,
  no force — CEO pre-approved in the task brief. Confirmed on GitHub via
  `git ls-remote --heads origin` (sha matches local `8e9fca00`).

## Trash / manifest

- No Trash writes occurred (Phase A stopped before Phase B, so no duplicate or
  umbrella leftover was ever moved).
- Manifest: `state/hq-step2-migration-20260922T210757.json` (8 ops: 7
  preflight records + 1 push record). Notes include the exact STOP reason.
  `--rollback` against it is a no-op beyond re-confirming the push (which, per
  the script, is never auto-reverted — see script docstring).

## `hq doctor` output (current, real machine — unmigrated)

```
✗ Projects/WarpClip/Webapp: duplicate clone still present: /Users/gob/Projects/WarpClip-webapp
✗ Projects/WarpClip/Design: duplicate clone still present: /Users/gob/Projects/WarpClip-design
hq doctor: 2 problem(s)
```

Expected — nothing moved yet. `hq.yaml` was not touched.

## MCP proof (Deliverable 3 — best-effort, see blocker)

The new path (`/Users/gob/MoonieXHQ/Projects/LungNote/Mcp/index.js`) does not
exist yet because step ② did not apply. Ran the required initialize probe
against the **current** (pre-move) path instead, to confirm the MCP itself is
healthy and will work identically once moved:

```
$ printf '...' | node "/Users/gob/LungNote Projects/mcp/index.js"
{"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":true}},"serverInfo":{"name":"lungnote","version":"1.2.0"}},"jsonrpc":"2.0","id":1}
```

No `.env`/secrets were needed — the server answered directly. Once step ②
completes, the identical command against the new path should behave the same
(same file, `shutil.move` preserves it byte-for-byte, verified by the script's
own `git rev-parse HEAD` check after every move in tests).

## Files changed

**New**
- `scripts/hq_migrate_step2.py` — reversible plan/apply/rollback migration script.
- `scripts/test_hq_migrate_step2.py` — 11 tests against real git repos + bare origins.

**Path repoints (12 lines, all found via `git grep`)**
- `config/cto.mcp.json`, `config/secretary.mcp.json`, `config/worker.mcp.json` (LungNote MCP `index.js`)
- `config/projects.yaml` (LungNote Webapp, WarpClip Webapp)
- `config/wikis.yaml`, `config/wiki-split-manifest.yaml` (LungNote Wikis)
- `runners/cto_chat.py`, `runners/secretary_server.py`, `scripts/lib/cxo_mcp_config.py` (LungNote MCP `index.js`)
- `scripts/session-deadline-check.py` (LungNote MCP dir)
- `docs/briefs/account-split-plan.md` (LungNote Webapp path in prose)

`git grep -c -E 'LungNote Projects|WarpClip Projects' -- .` over the tracked
tree (excluding `docs/reports/**` and this report) → **0**. No test pins the
old paths (`git grep -n 'LungNote Projects' -- '*test*'` → empty). Every
touched JSON/YAML re-parses clean.

## Tests

- ran: `.venv/bin/python -m pytest scripts/test_hq_migrate_step2.py -q`
  → **11 passed, 0 failed**
- ran: `.venv/bin/python -m pytest scripts/ -q --ignore=scripts/test_skill_doctrine_lint.py`
  → **3 failed** (all pre-existing, unrelated — see below), ~1158 passed,
  3 skipped, ~1224 collected. Doctrine test (#139) excluded per task instruction.

### The 3 unrelated pre-existing failures

All three are in `scripts/test_install_claude_home.py`, a file this task never
touched (its script `install-claude-home.sh` landed in commit `0918dcd5`,
before this task started). Root cause: the fixture/real-machine check for
`reel-editor-th/assets/mooniex-broll` (a 210 MB non-git asset dir) reports it
missing on this machine — an environment/asset-restore issue, not a code
regression from this branch. Confirmed via `git log`/`git diff main` that this
task made zero changes to that script or its test file.

## Issues / Blockers

1. **The real blocker**: `/Users/gob/Projects/WarpClip-webapp` has 4 unpushed,
   unmerged local branches. The migration cannot safely delete this duplicate
   as originally planned. Needs a CTO call — options:
   - push those 4 branches to `PASAKON/WarpClip-Webapp` first, then re-run
     `--apply` (everything else — all 7 moves, both dup checks — will then
     complete in one shot); or
   - confirm those branches are disposable (abandoned experiments) and the CTO
     explicitly authorizes deleting them; or
   - keep the duplicate clone in place for now and re-scope step ② to the 6
     unaffected rows (would need a script change — today's script is
     intentionally all-or-nothing across all step-2 rows, see design note below).
2. Deliverable 3 (MCP proof at the *new* path) is undeliverable until the above
   is resolved and `--apply` completes — see best-effort substitute above.
3. `hq doctor` is not clean (2 pre-existing problems, unchanged by this task —
   see output above).

### Design note: why the whole run stops, not just the WarpClip row

The task brief says the script "STOPS at the first failure ... nothing
half-moved." I read that as a global gate rather than per-row: Phase A
validates *every* step-2 row (including the push) before Phase B moves
*anything*. Real consequence on this machine: LungNote's 4 clean rows did not
move either, even though they have no problem of their own. Tradeoff was
deliberate — a partial migration (4 of 7 rows moved, `hq.yaml` half-updated)
would itself be a new kind of "half-moved" state to reason about later, and
the task's own umbrella-diff step uses the same "STOP, CTO decides" pattern
for exactly this kind of judgment call. Re-running `--apply` after the
WarpClip-webapp duplicate is resolved completes all 7 rows in one pass.

## Notes for Reviewer

- The push to `WarpClip Projects/webapp` `main` (+8, real GitHub write) already
  happened — this task treated it as pre-authorized per the brief. Everything
  else on disk is unchanged from before this task started.
- `scripts/hq_migrate_step2.py`'s duplicate-safety check treats a branch as
  safe if its sha is either an *exact* match on a live origin head, or an
  *ancestor* of one (already merged/superseded) — checked with a live
  `git ls-remote --heads origin`, never cached remote-tracking refs (those
  can list branches origin no longer has, which is what made the first,
  naive version of this check look wrong during development).
- Full plan output is reproducible any time via
  `.venv/bin/python scripts/hq_migrate_step2.py --plan` — read-only, safe to
  re-run.

## Skill learning
- MISSING [hq-filing §Migration] : no guidance on what to do when a
  CEO-approved "safe to delete" duplicate clone turns out to have real
  unpushed branches — the skill's duplicate rule (ADR 0028) assumes the CEO's
  read of "safe" is accurate; this run found it wasn't, for one of two dup
  clones · evidence: `/Users/gob/Projects/WarpClip-webapp`, branches
  `feat/hero-headline-marker-fix`/`feat/sections-v3-lime-redesign`/
  `feat/service-icons-og-tokens`/`feature/logo-integration`, none on
  `PASAKON/WarpClip-Webapp` origin and none ancestors of its current `main`.
- WRONG [none — self-caught in this session] : an early test-fixture draft put
  the fake `git init --bare` "origin" repos *inside* the fake umbrella dirs;
  Phase C's leftover-sweep then trashed them as leftovers, breaking `ls-remote`
  for a later assertion. Not a skill bug, a fixture-design mistake, fixed
  before commit · evidence: `scripts/test_hq_migrate_step2.py` `origins_dir`
  parameter, kept outside the umbrella dirs.
- COSTLY [no owner] : confirming the WarpClip-webapp duplicate's branches were
  genuinely unmerged (not just "behind") took a `git fetch` + per-branch
  `merge-base --is-ancestor` against live origin heads, since
  `ls-remote --heads` alone doesn't distinguish "deleted from origin" from
  "never existed on origin" · evidence: manual investigation before writing
  the script, ~15 Bash calls · prevented by: nothing to prevent — this is
  exactly the check the task asked the script to encode, now it's in
  `check_duplicate_safe()` for every future run.
