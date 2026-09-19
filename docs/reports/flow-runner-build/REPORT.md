# Flow shot runner — build report (task-6eabea66)

## What this branch was missing before it could start

My worktree branch had forked from an older `main` than the one that
actually holds this task's inputs. `docs/ops/flow-operator-design.md`,
`docs/scripts/BANCHI-SHOOT-BRIEF.md`, `.claude/skills/google-flow-ops/SKILL.md`,
`tools/check_replay_script.py` and `tools/assemble_act.py` all existed only on
local `main` (13 commits ahead), not on my branch. Merged `main` into my
branch (clean, no conflicts) before reading anything — otherwise half the
required reading list did not exist yet.

## Files changed

- `scripts/flow/launch-chrome-debug.sh` — new. Port of
  `scripts/higgsfield/launch-chrome-debug.sh`: dedicated profile
  `~/.flow-automation/chrome-profile`, port 9223 (never 9222/main Chrome).
- `tools/flow_ledger.py` — new. `parse_sheet()` (regex over the
  `### SHOT n · start–end · Ns · framing` / `**ATTACH**` / fenced-prompt
  format `tools/build_shotsheet.py` renders), `init_ledger()` (idempotent,
  atomic TSV write), `status_summary()`.
- `tools/flow_shoot.py` — new. `run` / `pull` / `status` subcommands. All
  browser/CDP calls live in the `FlowBrowser` class; every decision the
  runner makes (credit-cap math, refusal detection, zip-vs-mp4, duration
  tolerance, chip-retry count) is a free function above it.
- `tests/test_flow_shoot.py` — new, 37 tests.
- `docs/ops/flow-runner-USAGE.md` — new.
- `docs/ops/flow-operator-design.md` — amended one line: the ledger is
  per-act (`state/banchi/ACT<n>.tsv`), not the single `shots.tsv` the design
  sketched, matching the CLI usage the task brief itself specifies.

## Tests run

```
pytest tests/test_flow_shoot.py -v   -> 37 passed, 0 failed
pytest (full default suite, scripts+lib per pytest.ini) -> reached 100%,
  1 failure: scripts/test_skill_doctrine_lint.py::test_real_corpus_reports_zero_defects
  -- pre-existing on main before this task's merge (confirmed: the test file
  was already on my branch's original tip, unrelated to anything this task
  touches), not fixed here -- out of scope for a Flow-runner task.
```

`tools/check_replay_script.py` output:
```
ok   tools/flow_shoot.py
ok   tools/flow_ledger.py
ok   scripts/flow/launch-chrome-debug.sh
```
Exit code 0.

## What was validated live vs. only in unit tests — be exact

**Only in unit tests / CLI smoke, no browser involved:**
- Sheet parsing against the real `docs/scripts/banchi-ACT2.md` fixture: all
  24 shots, chip order, durations, prompt block byte-for-byte.
- Ledger idempotent init, atomic write (no `.tmp` left behind), status
  transitions, `status` summary text.
- Credit-cap arithmetic (`spent + estimate > cap`, boundary at exactly cap).
- Refusal-card detection (`ล้มเหลว` prefix / `อาจละเมิดนโยบาย`) against the
  exact card text quoted in the skill and the brief.
- zip-with-one-mp4 extraction, zip-with-wrong-count rejection, bare-mp4
  copy+rename.
- Duration verification: real `ffmpeg`/`ffprobe` calls (via `clip_review`'s
  own probes) against synthetic clips generated with `ffmpeg lavfi`, at the
  exact ±0.6s tolerance boundary, and a silent-clip -> `NO AUDIO` case.
- `tools/flow_ledger.py init`/`status` and `tools/flow_shoot.py status` run
  for real from the shell against the real sheet — TSV written and re-read
  correctly.
- `tools/flow_shoot.py run --dry-run` run for real from the shell with no
  Chrome listening on 9223: fails cleanly with a one-line message pointing
  at the launcher script, not a raw traceback (added this after the first
  attempt threw `ECONNREFUSED` uncaught).

**NOT validated — cannot be, without the CEO's login:**
- Every `FlowBrowser` method (`set_settings`, `attach_chip`, `paste_prompt`,
  `read_credit_estimate`, `submit`, `poll_result`, `download`,
  `find_card_by_dialogue`) — every selector in there is transcribed from
  `BANCHI-SHOOT-BRIEF.md` and the `google-flow-ops` skill, never run against
  the live DOM. The skill itself documents two different, contradictory
  chip-attach paths on different dates (⋮-menu vs. single-click-row); I wrote
  `attach_chip()` to try both in order rather than pick one blind. This is
  the first thing a `--dry-run` needs to check once Chrome is logged in.
- Whether `read_settings()`'s crude `innerText.includes(...)` check is
  precise enough (e.g. "8" appearing in unrelated page text) — a real
  `--dry-run` read-back will show if it needs tightening to a specific
  element locator instead of whole-body text search.

## Blockers

None for the build itself. The one real blocker, per the task brief, is
structural and expected: **the CEO has not yet logged into the automation
Chrome**, so no `--dry-run` against the live UI has run. Per the task's own
"what you cannot do" section, this is not mine to unblock — READY FOR LOGIN.

## Replay Script

`tools/flow_shoot.py`

## Notes for reviewer

- `tools/flow_shoot.py pull` takes `--sheet` in addition to `--ledger`/`--dest`
  (the task's usage line abbreviated it as `--ledger ... --dest ...`) — it
  needs the sheet to know each shot's dialogue line and expected duration,
  which the ledger alone doesn't carry. Documented in the USAGE doc.
- `run`'s exit code: 0 only if every row this run actually touched (status
  changed away from `todo`) ended `verified`; untouched rows (e.g. after a
  `CAP REACHED` stop) don't count against it.
- SKILL-OVERRIDE: none — I followed the brief's chip-attach path as the
  primary, and added the skill's newer single-click-row path as a fallback
  rather than picking one and dropping the other, since I have no way to
  test which is live today.

## Skill learning

- WRONG: none identified against `google-flow-ops` or `dev-spawn-protocol`
  itself — the contradiction I hit (⋮-menu vs. single-click-row chip attach)
  is already documented *inside* the skill as a dated correction, not
  something this run disproved.
- MISSING: the task's own worktree wasn't caught up with `main` when
  delegated — the design doc, the shoot brief, and `check_replay_script.py`
  itself (the gate this exact task is required to pass) all existed only on
  `main`, not on the branch I was handed. A pre-flight `git log HEAD..main
  --oneline` (or the CTO rebasing the worktree before delegating) would have
  caught this before burning a round-trip discovering it by hand.
- COSTLY: figuring out that the design doc/brief/skill referenced in the
  task didn't exist in my worktree, tracing it to a stale branch base, and
  merging `main` in — pure setup overhead unrelated to the actual build,
  and would recur on any task delegated shortly after a wiki/doc commit
  lands on `main`.
- (none) — no other gaps found.
