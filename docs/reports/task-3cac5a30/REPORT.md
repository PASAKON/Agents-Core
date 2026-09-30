# task-3cac5a30 — Org Mesh W2.11: directives count only in the description header

Developer, 2026-10-01. Branch `agent/developer-task-3cac5a30`. Closes W2.7 finding F11
(`docs/reports/task-42fdcda7/REPORT.md`). Not touched: `tools/node_dispatch.py`, `lib/mesh.py`,
`lib/db.py`, `create_task`'s signature.

## What changed

A `needs:` / `override:` line counts only in the description's **header**: the leading lines
up to the first blank line, at most 5 (`MAX_HEADER_LINES`). A directive after that is text;
it is ignored, never an error.

- `lib/router.py` — `header(description)` is the one definition (blank = empty after
  `str.strip()`, so spaces, tabs, `\r` and Unicode spaces end the header; lines split on `\n`
  only). `parse_needs` runs `_NEEDS_RE` over `header(...)` instead of the whole text.
  `add_needs_line` (what `create_task(needs=...)` calls) now writes the line **into** the header via
  `add_header_line`, at the end of the block, so no existing header line moves. A header that
  already has 5 lines raises `ValueError`.
- `tools/route.py` — `check_override` runs `_OVERRIDE_RE` over `lib.router.header(...)`. The regex
  itself is tightened from `^\s*override:\s*\S` to `^[ \t]*override:[ \t]*\S`: the old `\s*`
  crossed newlines, so `override:` with nothing after it plus any pasted next line counted as
  "a reason". `_IRON_59_MSG` now tells the C-level the line belongs in the first block.
  The import is top-level on purpose: `check_override` swallows every exception and returns
  `None` (= allow), so a lazy import that failed would have silently opened the gate.
- `lib/org_tools_registry.py` — comment and the `create_task` tool description only (they now say
  "end of the description's first block" and that a later `needs:`/`override:` is ignored).
- `tests/test_w211_directives.py` (new, 56 collected cases) and
  `tests/fixtures/w211_task_descriptions.json` (copies of the 20 newest real descriptions, no live DB read).

## Evidence: what real descriptions look like (state/tasks.db, read-only, 1176 rows, 2026-05-17 to 2026-09-30)

| measure | count |
|---|---|
| descriptions | 1176 |
| carry an `override:` line (old regex) | 10, **all on line 1** (first seen 2026-09-30 08:43; all inside the 20 newest) |
| carry a `needs:` line (old regex) | 1 — `task-10136806`, **line 15**: prose `NEEDS: there is no \`needs\` column...`, not a directive |
| real `needs:` directive lines in the ledger | 0 (`create_task(needs=)` shipped 2026-09-30, no caller yet) |
| first block (non-blank lines before the first blank) of 1 line | 850 |
| ... of 2 / 3 / 4 lines | 184 / 41 / 17 |
| ... of exactly 5 lines | 23 |
| ... of 6 or more lines (max 14) | 29 |
| start with a blank line (empty header) | 32 |
| contain `\r` | 0 |

So every real `override:` sits where the new rule reads it. The one `needs:` hit is a false
positive today: the old parser took the sentence for a capability list and invented names from it;
on such a task with `ORG_HOST_ROUTER` on, every host would be rejected `provides lacks ...`.

The 20 newest descriptions (the fixture): 10 with `override:` on line 1 and 10 without. Behaviour
pinned against the pre-change regexes (copied into the test as `OLD_*`): the gate verdict is
identical on all 20; `parse_needs` is identical on 19 and differs only on `task-10136806`
(old: bogus names, new: `[]`). The fixture was scanned for secrets (one prose hit, `secret: args`,
harmless) and invisible characters (none) before it was committed.

## Callers (grep, worktree)

- `_NEEDS_RE`: `lib/router.py` `parse_needs` only.
- `_OVERRIDE_RE`: `tools/route.py` `check_override` only.
- `parse_needs`: `lib/router.py` `pick_host` (line ~240), reached from `tools/delegate.py:1868`
  (`host_router.pick_host`, ORG_HOST_ROUTER on); tests `test_w26_pick_host.py`.
- `add_needs_line`: `lib/org_tools_registry.py` `_h_create_task`, reached from `runners/cto_mcp_server.py`,
  `runners/cto.py`, `runners/cto_chat.py` through the registry; tests `test_w26_pick_host.py`.
- `check_override`: `tools/delegate.py:1820` `_route_runner`; tests `test_route_override.py`,
  `test_delegate_router.py` (this test prepends `override: test\n` via SQL, so it stays in the header).
- Description writers that could push a header line down: `tools/git_ops.py:462` (gate_tests failure)
  **appends** to the description; nothing prepends. No other writer found in `lib/ tools/ runners/`.

## Is `create_task` the place to normalise?

Partly, and only the part it already owns. `create_task(needs=...)` is the one place the **system**
writes a directive, so `add_needs_line` now puts it in the header (before, it appended at the end of
the text, which the new parser would ignore on any description with a blank line, silently). Signature
unchanged. I did **not** make `create_task` move a `needs:`/`override:` line "passed later in the text"
up into the header: text that arrived later is exactly what a pasted block looks like, and a
normaliser cannot tell a C-level's own trailing line from a quoted one. Rejecting or re-homing it
would re-open F11 by another door. A C-level who writes `override:` after a blank line gets the
IRON §59 refusal, whose text now says where the line belongs.

## Verification

- Full suite, once, from the worktree: `python -m pytest` (pytest.ini supplies `-q`; none added).
  **4804 passed, 28 skipped, 0 failed, 429.83 s.**
- Standalone scripts: `scripts/test_tool_parity.py` -> `ALL PASS`; `scripts/test_org_tools_registry.py` -> `ALL PASS`.
- Probe, not mutation of the guard: with `lib.router.header` and `tools.route._description_header`
  replaced by the identity in a throwaway interpreter, `test_needs_after_the_header_is_ignored`
  fails immediately, so the new tests do detect the old behaviour.
- Invisible-character scan (Cf / Cc / Zl / Zp / non-ASCII Zs / `\r`) over the 5 changed files:
  0 flagged in each.
- `git status`: clean after the commit.

## Things the CTO should decide or check

- **5% of descriptions have a full first block.** 52 of 1176 (23 with exactly 5 lines, 29 with more)
  have no blank line within their first 5 lines. For those, `create_task(needs=...)` now returns
  `ERROR: the description's first block already has 5 lines ...` and creates no row (tested). The alternative
  (prepend `needs:` and push line 5 out) would silently drop an `override:` sitting on line 5, which I judged worse.
- **A leading blank line empties the header** (32 of 1176 real descriptions start that way; none carried a directive).
  Strict reading of "before the first blank line". If you want leading blank lines skipped, it is one line in `header`.
- **IRON §59 card / `CXO_Protocol_DevSpawn` §0 do not say where the `override:` line goes.** C-levels already
  write it as line 1 (10 of 10), so nothing breaks, but the card should say "first block, max 5 lines".
  I cannot write the wiki or the skill; see Skill learning.
- The fixture is 86 KB of real task briefs (private repo). Trim `tests/fixtures/w211_task_descriptions.json`
  to headers plus directive positions if you would rather not keep the bodies; the tests that need full
  text are the two `..._unchanged` ones.
- `lib/directives.py` would have been the natural home for `header`; `self_repo_guard` refused the new file
  because it was not in `touches`, so the helper lives in `lib/router.py` (declared) and `tools/route.py`
  imports it from there.

## Skill learning

- MISSING [CXO_Protocol_DevSpawn §2 touches] : a brief whose natural fix adds a shared helper module should list that new file in `touches`; `self_repo_guard` refused `lib/directives.py` (not declared) and the helper had to move into `lib/router.py` · evidence: task-3cac5a30, guard message at the first Write
- MISSING [CXO_Protocol_DevSpawn §0 | IRON-RULES §59 card] : the rule says a C-level needs an `override: <reason>` line but not where; it must now sit in the first block (before the first blank line, max 5 lines) · evidence: task-3cac5a30 e747a140, 10 of 10 real `override:` lines are on line 1
- COSTLY [no owner] : root `conftest.py:88` sets `ORG_ROUTER=off` for every test, so any new test of `check_override` that forgets `monkeypatch.delenv("ORG_ROUTER")` passes or fails for the wrong reason (12 false failures on the first run) · evidence: task-3cac5a30, tests/test_w211_directives.py `_router_on` · prevented by: one line in the test-writing note that gate tests must delenv ORG_ROUTER
- COSTLY [no owner] : a full `pytest` run is 7 min 10 s (429.83 s) in a worktree; run it once, in the background, and do not poll · evidence: task-3cac5a30 · prevented by: starting it with `run_in_background` and a Monitor on the summary line
