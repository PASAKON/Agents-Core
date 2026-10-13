# Thai → English: inventory and first landing (2026-10-14)

**Order:** CEO 14 Oct (relayed by SomPong, supervised by CONTABO CTO #e106b78b): internal text (skills,
code comments, docs, role files, CLAUDE.md files) moves to English to save tokens. Language-specific
content stays in its own language. A C-level verifies every translation before it merges.
**Done by:** CONTABO CTO #c1ee65d8.

`summary.md` and `rows.jsonl` are the **before** snapshot, taken before any translation landed. Two things in it are already out of date:
- after it was generated, the tool's last section was renamed "No git checkout on Contabo" and given an "on this box" column;
- AlphaTrader and LineAutomation are not absent from Contabo: they are deploy copies (folders without `.git`).

Files in this folder:
- `summary.md`: the per-repo, per-tier and per-kind totals, the always-loaded table, the top backlog and the repos with no git checkout on this box.
- `rows.jsonl`: one row per file with Thai. Public repos only (Agents-Core, Agents-Rules, Chatudo-Webapp), and only paths that are on the upstream branch.

Rerun from the Agents-Core root. Keep the private detail outside the repo.
```bash
.venv/bin/python tools/thai_inventory.py --out docs/ops/thai-inventory-<date> --detail-out <scratch dir>
.venv/bin/python tools/thai_inventory.py --explain <file> --repo-name <Repo> --rel <repo-relative path>
```

## Method
- **No model.** Thai means characters U+0E00–U+0E7F. Every git checkout under `/opt/MoonieXHQ` is scanned, plus the Rules and Wikis snapshots: 12 roots, 5,700 text files, 2,141 of them with Thai.
- **Kind** comes from a lexer per file type:
  - Python `tokenize`: comment and docstring vs string literal.
  - A C-like lexer for js, ts and go, a `#` lexer for shell and yaml, and HTML comments.
  - Markdown by paragraph: a quote counts as a CEO quote when its paragraph or heading names the CEO, and «…» marks a title.
  - Skill frontmatter `description`: anything in quotes there is a trigger phrase.
  - The file path marks tests, user-facing text (captions, prompts, scripts, `*_th.md`, …) and source material (transcripts, raw).
- **translate** kinds: always-loaded prose, skill body, doc, comment. **keep** kinds: CEO quote, trigger phrase, other quoted phrase, title/name, user-facing, source material, runtime string, data, test fixture. The split is a heuristic that says what to read. It never decides what to change: every diff is still read by a C-level.
- **Tier** follows what the launchers actually inject:
  - `T0_session`: CLAUDE.md files, the C-level role files, MEMORY.md.
  - `T0_worker`: worker role files.
  - `T1_start`: IRON-RULES, read at session start.
  - `T2_trigger`: skills.
  - `T3_demand`: everything else, paid only when opened.
- **Privacy.** Agents-Core is a public repo. Private repos appear as totals only. Their per-file rows go to `--detail-out` and are never committed.

## Measured tokens, before → after
Method: memory `reference_measure_tokens_free_claude_p_delta`. For each text, run `claude -p` with and without it (`--tools "" --no-session-persistence --disable-slash-commands --strict-mcp-config`). Total input = input + cache_creation + cache_read, and the cost of a text is the with-text total minus the baseline. Haiku 5.5 and Opus 5.5 gave identical counts for all four texts (same tokenizer), so the after-run used Opus only. **Control:** the old Tab Title section, measured again inside the after-run, gave 1,496 tokens, the same as before.

| text | chars | Thai | tokens before | chars | Thai | tokens after | saved |
|---|---:|---:|---:|---:|---:|---:|---:|
| Tab Title section (§32), identical in roles/cto, cmo, cgo, cfo | 2,148 | 887 | 1,496 | 2,413 | 17 | 986 | **−510 (−34 %)** |
| roles/cto.md, whole file | 12,041 | 949 | 5,343 | 12,306 | 79 | 4,833 | −510 (−9.5 %) |
| CTO always-loaded set: HQ CLAUDE.md + Core CLAUDE.md + roles/cto.md + MEMORY.md | 42,926 | 1,034 | 18,840 | 43,191 | 164 | 18,330 | −510 (−2.7 %) |
| MoonieX-ClaudeFlow CLAUDE.md | 8,977 | 780 | 4,535 | 9,326 | 25 | 4,029 | **−506 (−11 %)** |
| IRON-RULES §53 + the §1.5 ClaudeFlow quote, translated | 1,765 | 682 | 1,205 | 2,098 | 0 | 798 | −407 (−34 %) |
| IRON-RULES §56, amendment added (new rule text + CEO quote) | 1,583 | 52 | 562 | 3,273 | 279 | 1,327 | +765 |

How to read it:
- IRON-RULES is +358 tokens net per read: the §56 amendment costs more than §53 saves. CTO #e106b78b kept it, because rule 3 requires the CEO's words quoted in the original (they are evidence).
- The English is 12 % longer in characters but 34 % cheaper in tokens. Replacing 870 Thai characters saved 510 tokens, about 0.59 per Thai character net of the English added.
- An always-loaded file is paid once when the session starts and then read from the prompt cache on every turn. So each C-level session (CTO, CMO, CGO, CFO) now carries 510 fewer tokens on every turn. A ClaudeFlow session carries 506 fewer.

## Findings
1. **The always-loaded set was mostly English already.** T0 holds 7,502 translatable Thai characters in 9 files. SomPong's CLAUDE.md alone is 3,287 of them; the four C-level role files are 850 each; ClaudeFlow is 755.
2. **The real backlog is on-demand docs.** T3 holds 275,819 translatable Thai characters, paid only when a session opens the file. In public repos and on origin, that is docs 97,554 (262 files), skill bodies 8,353 (36 files) and code comments 10,693 (158 files).
3. **Keep is larger than translate.** About 1.5 M Thai characters must stay: user-facing scripts and captions, source transcripts, CEO quotes, runtime strings, data and test fixtures.
4. **Skill descriptions stay as they are.** They hold 2,203 Thai characters, 245 of them outside quotes. A read found trigger phrases written without quotes, proper names and UI labels, all of which are kept.
5. **IRON-RULES:** 805 translatable characters (most of it §53). Landed as Agents-Rules `d7f9026` after the CEO confirmed Q-20261013-1803-10b5 (option 1, 2026-10-13T18:52Z): §53 translated, the §1.5 ClaudeFlow quote refreshed, and §56 amended (rule 5, "no bulk translation", superseded). Edited in a clone of origin Agents-Rules; the Contabo snapshot was replaced only after it byte-matched the parent commit.
6. 46 files with Thai in public repos exist only in Contabo's unpushed local commits (57,306 Thai characters). They count in the repo totals but are left out of `rows.jsonl`.

## Always-loaded set: status
| file | Thai to translate | status |
|---|---:|---|
| Agents-Core roles/cto.md, cmo.md, cgo.md, cfo.md | 850 each | agy task-0ae05245, verified; landed on origin/main in merge `6ef89820` (CTO #e106b78b read it for meaning) |
| MoonieX-ClaudeFlow CLAUDE.md | 755 | agy task-3f99545e, verified; merged `12bc471` on ClaudeFlow main (hand merge, see below) |
| MoonieX-SomPong CLAUDE.md | 3,287 | translated by SomPong, approved by the CEO ("ใช้ได้"); `062a85b` on MoonieX-SomPong |
| Agents-Rules IRON-RULES.md | 805 | landed `d7f9026` (CEO card Q-20261013-1803-10b5) |
| roles/coo.md, MEMORY.md | 30 each | read: a name and labels inside CEO-quote paragraphs, so kept |
| SKILL.md descriptions | 245 | kept (finding 4) |

## How each change was verified
- **Role files.** The section is extracted by its headings from all four files:
  - the md5 is identical in all four;
  - text outside the section is byte-identical to origin/main;
  - the only Thai left is the kept example line (`✅ merge SEO ×3 รอ deploy`, `🏁 ครบทุกงาน ปิดได้`);
  - the meaning was read line by line against the Thai.
- **ClaudeFlow CLAUDE.md.**
  - The line count is the same, and every line without Thai is byte-identical.
  - The Thai left is exactly the two kept quotes, which are what the CEO types to Claude.
  - Every code span and table column count is preserved, and no invisible characters were found.
  - The meaning was read on all 56 lines.
  - **Tests.** The branch poller's artefact gate refused the branch on a red suite. ClaudeFlow's `npm test` was then run twice in one scratch worktree, once on origin/main and once with the branch's two files, under the same conditions: system node v20.20, the tracked `.env.example` as `.env`, outbound HTTP(S) sent to a dead proxy. Both runs gave 2,725 tests, 2,722 pass, 2 fail, 1 skipped, with **identical failure sets**, and both failures are already on main:
    - `g0Score` refuses to run with a `.env` in its working directory;
    - a `lineSompongGroup` routing assertion fails.

    No test reads CLAUDE.md or `docs/reports/`; every repo-walking test is limited to `src/` and `scripts/`. The branch was hand-merged as `12bc471` under CTO_Gate_MergeChecklist "Hand merge".

## runner_fit records
These live here until a writer exists: the merged `tools/tool_value.py` (8a6d2b21) has no runner_fit code yet. Kind = `doc-translate`.

| job | task | iter | runner · model | result | why |
|---|---|---:|---|---|---|
| Tab Title × 4 role files | task-0ae05245 | 0 | agy · gemini-3.8-flash-high | **fail**, 0 edits | the brief's Verdict told the worker to run git, md5sum and grep; headless agy refuses the "command" permission and the run ends |
| | | 1 | agy · gemini-3.8-flash-high | **partial** | structure perfect; one meaning error: `ทำอะไร` (what it is doing) became "what is done" (Thai verbs carry no tense) |
| | | 2 | agy · gemini-3.8-flash-high | **pass** | fixed that line only |
| ClaudeFlow CLAUDE.md | task-3f99545e | 0 | claude · claude-sonnet-5-5 (router) | **stopped by CTO** | the forecast set `needs_shell` because the brief named shell words as text to keep, so agy was ruled out. Stopped after about 2 minutes and re-pinned to agy with an `override:` line (CEO order) |
| | | 1 | agy · gemini-3.8-flash-high | **pass** | 56 lines, layout identical, both kept quotes intact, meaning right on every line; the worker flagged its own 3 open word choices |

Not used:
- **Jules.** Its key exists only on the Mac (`~/.config/mooniex/jules.env`), so there is no Jules lane on Contabo.
- **Haiku.** The Haiku 5.5 trial failed (0.66 / 0.72 of Sonnet against a 0.90 bar, 2026-10-11).

Cost: about 1 % of the agy-gemini bucket per job (router forecast), plus about 2 minutes of the stopped Sonnet run.

## Backlog (owners and dates are in the CEO's LungNote to-do)
Batches of 20 files or fewer, taken from the top of `rows.jsonl` or the private detail. An agy brief must use file tools only. A C-level verifies each batch as above.
- **Code comments** need a comment-only checker before the first batch (order step 4: an AST or token check that only comments and docstrings changed). It is not built yet; build it first.
- **Agents-Wikis** and **Agents-Rules** are snapshots on Contabo, so edits go through a clone of origin.
- **Repos with no git checkout here** are listed at the end of `summary.md`. AlphaTrader and LineAutomation are deploy copies (a folder without .git), so their translation starts from a clone.
