"""The 10 real jobs of the Argon trial (CEO order 14 Oct 2026 via SomPong, CTO cto-d1a121af).

Each job is a real open item: a GitHub issue or a line of LungNote todo f2209b5b (the English
backlog). Both runners get the same brief plus the same edit-only CONTRACT; neither may run a
command (Contabo agy is headless: a command request ends the run, CXO_Protocol_DevSpawn §3d).
The CTO runs the checks in `test.py` on both outputs; the blind judge sees brief, diff, report
and those check results.
"""
AC = "/opt/MoonieXHQ/Agents/Core"
CONSOLE = "/opt/MoonieXHQ/Projects/MoonieX/Console"
CF = "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow"

CONTRACT = """
## How to work (every worker in this round gets this same section)
- Work only inside {wt}. Read, search, create and edit files there with your file tools.
- Run no shell command of any kind: no git, no tests, no ls, no python, no node, no npm. A command
  request ends your run and your work is lost. The CTO runs the tests after you finish.
- Do not commit. Change only what the task needs.
- When finished, write REPORT.md at the worktree root with three headings: Files changed,
  What was done, Blockers. Under Blockers, name what you could not verify because you could
  not run anything.
"""

TRANSLATE_RULES = """Rules (CEO order 14 Oct: internal text moves to English to save tokens; language-specific
content stays in its own language):
- Translate the Thai prose written for agents and operators: sentences, headings, list items,
  table cells, notes.
- Keep exactly as it is, in Thai: the CEO's own words when quoted (in quotes and attributed to the
  CEO), trigger phrases (quoted words a person types to start a skill), titles and proper names
  (in «…» or quotes), text customers or viewers see, Thai UI labels as they appear on screen, and
  everything inside backticks, code blocks, commands and paths.
- Where a kept Thai quote would leave an English sentence unclear, you may add a short English
  gloss after it in parentheses.
- Every line that has no Thai stays byte-identical. Keep the Markdown structure exactly: headings,
  list markers, table columns, code fences, blank lines, links, emphasis.
- Thai verbs carry no tense: take it from context (a standing rule in the present tense, a past
  event in the past tense).
- Plain, short English. Add nothing, summarise nothing, reorder nothing.
- Edit the file in place. In REPORT.md, list every line where you were unsure about the meaning
  or about keep vs translate."""

JOBS = [
    {
        "id": "D1", "repo": "Agents-Core", "src": AC, "kind": "dev", "job_type": "code", "size": "M",
        "source": "LungNote f2209b5b item 1 (due 16 Oct)",
        "brief": """Task: build a comment-only checker for the Thai-to-English translation work.

Why: the org is translating Thai code comments and docstrings to English. Before any comment batch
lands, a reviewer needs a machine check that a diff changed ONLY comments and docstrings, never
code or string literals (backlog todo f2209b5b item 1, CEO order 14 Oct).

Build:
1. `tools/comment_only_check.py`
   - Core function `code_changed(old_text: str, new_text: str, path: str) -> bool`: True when
     anything other than comments or docstrings differs between two versions of one file. The
     lexer is picked by the file extension of `path`:
     - Python (.py): use `tokenize`. Ignore COMMENT tokens and docstrings (a string literal that
       is the first statement of a module, class or function body). Comment-only lines must not
       count through the NL/NEWLINE/INDENT tokens around them. Everything else counts, including
       string literals that are not docstrings.
     - C-like (.js .mjs .cjs .ts .tsx .jsx .go): ignore `//` and `/* */` comments, but not inside
       string, template or character literals.
     - Hash (.sh .bash .yaml .yml .toml): ignore `#` comments, but not inside quotes; a shebang
       line is code.
     - Any other extension: raise ValueError (unsupported) instead of guessing.
     - Whitespace-only differences inside code may be ignored; a changed token is a change.
   - CLI: `python tools/comment_only_check.py --base <git-rev> [--head <git-rev>] [paths ...]`.
     For every file that differs between base and head (the working tree when --head is
     omitted), limited to `paths` when given, print `OK <path>`, `CODE <path>` or
     `UNSUPPORTED <path>`. Exit 0 only when every file is OK, else 1. Read file versions with
     `git show <rev>:<path>` and list files with `git diff --name-only`, through subprocess.
     An added or deleted file counts as CODE.
   - `tools/thai_inventory.py` already has lexers (`lex_python`, `lex_clike`, `lex_hash`) that
     split a file into kinds; reuse them if they fit, or write your own. Do not edit
     thai_inventory.py.
2. `tests/test_comment_only_check.py` (pytest). Per language: a comment-only change passes; a
   docstring-only change passes (Python); a changed string literal fails; a changed identifier or
   number fails; `//` inside a JS string is not a comment; `#` inside a quoted shell string is
   not a comment; an unsupported extension raises. Test the core function with in-memory strings.
   One CLI test may build a throwaway git repo under pytest's `tmp_path`.

Interpreter: /opt/MoonieXHQ/Agents/Core/.venv/bin/python (Python 3.12). Standard library only.""",
    },
    {
        "id": "D2", "repo": "Console", "src": CONSOLE, "kind": "dev", "job_type": "fix", "size": "S",
        "source": "PASAKON/MoonieX-Console#11",
        "brief": """Task: fix MoonieX-Console issue #11 — ORG_ROOT example and boot error still point at old paths.

Issue text:
`.env.example:24-26` and the boot error in `src/config.js:36-37` tell the operator to set
`ORG_ROOT=/Users/gob/Projects/Agents` (Mac) or `/opt/mooniex-agents` (Contabo). Both are compat
links that are being removed: PASAKON/Agents-Core#172 on the Mac, and #173 on Contabo around
2026-10-01. The live Mac `.env` already uses `/Users/gob/MoonieXHQ/Agents/Core`.

Fix: show `/Users/gob/MoonieXHQ/Agents/Core` (Mac) and `/opt/MoonieXHQ/Agents/Core` (Contabo) in
both places. Change text only; the logic stays the same.

Done when: `git grep -n 'Projects/Agents\\|/opt/mooniex-agents' -- .env.example src/` returns nothing.""",
    },
    {
        "id": "D3", "repo": "Console", "src": CONSOLE, "kind": "dev", "job_type": "fix", "size": "M",
        "source": "PASAKON/MoonieX-Console#27",
        "brief": """Task: fix MoonieX-Console issue #27 — Run Inbox command cards have no per-session or hourly create cap.

Issue text:
Found by the security review of the question-card landing (2026-10-13, Console PR #25). Question
cards now cap creates: 5 pending and 10 per hour per `requester.session`, 50 pending and 30 per
hour in all. Command cards (`run_asks`) have no matching per-session or hourly cap. A create →
cancel loop can therefore queue any number of `new` mails, and each mail buzzes the CEO's phone.

Fix: give `src/run/create.js` the same open and hourly caps (counted over every status, as in
`src/run/questions.js` `overCap`), with tests: an 11-iteration create/cancel loop is refused,
and a refused create queues no mail.

Pointers: the question-card caps live in `src/run/questions.js` (`MAX_*` constants,
`countCreatedSince`, `overCap`). Existing Run Inbox tests are in `test/run-*.test.js` with
shared helpers in `test/run-fixtures.js`. Tests run under vitest (`npx vitest run <file>`) on
Node 22. Keep the refusal shape consistent with how create.js already refuses a bad request.""",
    },
    {
        "id": "D4", "repo": "ClaudeFlow", "src": CF, "kind": "dev", "job_type": "fix", "size": "S",
        "source": "PASAKON/MoonieX-ClaudeFlow#213",
        "brief": """Task: fix MoonieX-ClaudeFlow issue #213 — perf scripts and .env.example hardcode pre-HQ paths.

Issue text:
These work only through compat symlinks that PASAKON/Agents-Core#172 is removing:
- `scripts/perf-lunar-vs-flash.js:15,376` and `scripts/perf-lunar-vs-flash-v2.js:17,342` load
  dotenv from `/Users/gob/Projects/mooniex-claudeflow/.env` and write their output JSON there.
- `.env.example:260` `BROLL_CATALOG_DIR=/Users/gob/Projects/Agents/prototypes/bl-broll-catalog`.
  The catalog now lives at `/Users/gob/MoonieXHQ/Agents/Core/prototypes/bl-broll-catalog`.

Fix: resolve both perf-script paths from `__dirname` (`path.join(__dirname, '..', ...)`), and
update the `.env.example` value.

Out of scope: the one-off poster/seed scripts (`post-musk-poster.js`, `seed-*.js`) point at image
files that no longer exist at either path. They are historical and are left alone.""",
    },
    {
        "id": "D5", "repo": "ClaudeFlow", "src": CF, "kind": "dev", "job_type": "fix", "size": "S",
        "source": "PASAKON/MoonieX-ClaudeFlow#227",
        "brief": """Task: fix MoonieX-ClaudeFlow issue #227 — deploy.sh drops the SomPong session overlay.

Issue text:
`scripts/deploy.sh` rebuilds the webhook with `docker compose -f docker-compose.webhook.yml -p
mooniex-claudeflow up -d --build` only. The live container has run with **two** files since
2026-10-01 (`docker-compose.webhook.yml,docker-compose.sompong-session.yml`, per its compose
label), and the overlay's names reach compose only through `infisical run`. A plain `bash
scripts/deploy.sh` would therefore recreate the container without the SomPong session overlay:
`SOMPONG_BRAIN` unset, and SomPong falls off session mode.

Found 2026-10-10 by the Contabo CTO while deploying task-0b069067 (db2bc2a). That deploy used the
overlay's own header command instead:

    python3 /opt/MoonieXHQ/Agents/Core/tools/infisical_setup.py run MoonieX-ClaudeFlow prod --as contabo -- \\
      docker compose -p mooniex-claudeflow -f docker-compose.webhook.yml -f docker-compose.sompong-session.yml up -d --build claudeflow-webhook

Fix: deploy.sh step 2 runs that command (both files, under `infisical run`), and a test pins that
`COMPOSE_FILE` covers both files.

Note: ClaudeFlow's `npm test` script in package.json lists every test file by name; a new test
file must be added there. Tests use `node --test` (CommonJS).""",
    },
    {
        "id": "T1", "repo": "Agents-Core", "src": AC, "kind": "doc", "job_type": "docs", "size": "S",
        "source": "LungNote f2209b5b item 5 (Agents-Core docs)", "file": "docs/runbooks/winbox-recovery.md",
        "brief": "Task: translate the Thai in `docs/runbooks/winbox-recovery.md` to English.\n\n" + TRANSLATE_RULES,
    },
    {
        "id": "T2", "repo": "Agents-Core", "src": AC, "kind": "doc", "job_type": "docs", "size": "S",
        "source": "LungNote f2209b5b item 5 (Agents-Core docs)", "file": "docs/runbooks/winbox-checklist.md",
        "brief": "Task: translate the Thai in `docs/runbooks/winbox-checklist.md` to English.\n\n" + TRANSLATE_RULES,
    },
    {
        "id": "T3", "repo": "Agents-Core", "src": AC, "kind": "doc", "job_type": "skill", "size": "S",
        "source": "LungNote f2209b5b item 4 (skill bodies)", "file": ".claude/skills/session-worktree/SKILL.md",
        "brief": ("Task: translate the Thai in the body of `.claude/skills/session-worktree/SKILL.md` to English.\n\n"
                  "Do not change the frontmatter (everything between the first two `---` lines) at all: its "
                  "Thai is trigger phrases and stays.\n\n" + TRANSLATE_RULES),
    },
    {
        "id": "A1", "repo": "Agents-Core", "src": AC, "kind": "analysis", "job_type": "research", "size": "M",
        "source": "LungNote f2209b5b item 5 (batch plan, due 23 Oct)",
        "brief": """Task: plan the batches (PRs) for translating Agents-Core's on-demand docs and code comments from
Thai to English (backlog todo f2209b5b item 5, due 23 Oct).

Input, all in `docs/ops/thai-inventory-2026-10-14/`: `rows.jsonl` (one JSON row per file with Thai:
repo, path, tier, chars, thai, translate, keep, est_tokens, kinds = Thai characters per kind),
`README.md` (method, what is already done, rules) and `summary.md`.

Scope: rows with repo "Agents-Core" whose `kinds` has a "doc" or a "comment" key.

Write `docs/ops/thai-inventory-2026-10-14/batches.md`:
- A batch is one PR: at most 20 files and roughly 8,000 translatable Thai characters, from one
  area (for example docs/runbooks, docs/ops/letters, tools/*.py comments), so one reviewer can
  verify it in one sitting.
- Code-comment batches (files whose Thai to translate is comments) wait for the comment-only
  checker `tools/comment_only_check.py`: put them last and mark them "needs comment-only check".
- Every in-scope file appears in exactly one batch or in a Skip list with its reason (for example:
  almost all keep-kinds, a generated report, a source transcript, an archived letter not worth the
  review). State the skip rules you used.
- Per batch: id, area, file count, translate characters, keep characters, the file list, and a
  risk note for the reviewer (CEO quotes, user-facing text, test fixtures, mixed files).
- A totals line that reconciles with rows.jsonl: in-scope files, translate characters, number of
  batches, number skipped.
- Order batches by value: files agents open more often (runbooks, docs/ops, docs/design, skills'
  references) before archives (docs/reports, letters, output/).
Do not edit rows.jsonl or any other existing file.""",
    },
]

JOBS_BY_ID = {j["id"]: j for j in JOBS}
