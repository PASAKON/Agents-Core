# REPORT — task-9c6daaf7 (caveman: plugin, default mode ultra, report-length rule)

## Summary

Installed `JuliusBrussee/caveman` v2.7.0 as a Claude Code plugin, replacing
the four standalone hook files with the plugin's own hook wiring. Default
mode set to `ultra` via `~/.config/caveman/config.json`. Added an add-only
"Report length" block to the four C-level role files. Full suite: 1130
passed, 1 failed (pre-existing), 16 skipped.

## Facts verified first (README quotes)

Install commands (README.md, "More doors into the cave"):
> ```bash
> # Claude Code
> claude plugin marketplace add JuliusBrussee/caveman && claude plugin install caveman@caveman
> ```

Mode names + switching (README.md, "The first five minutes"):
> `/caveman lite` for tight-but-polite. `/caveman ultra` for grunts. `/caveman wenyan` for classical Chinese, because someone asked.

Mode names, full list (skills/caveman-help/SKILL.md — the actual installed skill card):
> One rule file, one talking style, plus a small toolbox. `/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra` sets intensity. `/caveman off` or `normal mode` turns it off.

Default mode resolution (skills/caveman-help/SKILL.md):
> **Environment variable** (highest priority): `export CAVEMAN_DEFAULT_MODE=ultra`
> **Config file** (`~/.config/caveman/config.json`): `{ "defaultMode": "lite" }`
> Resolution: env var > config file > `full`.

Hooks (docs/technical/skills-hooks-and-plugins.md):
> Hook package supports agent lifecycle events including: session start; user prompt submission; command or pre-tool execution; status-line updates. Hooks can add mode reminders, expose recovery context, and compact command output.

`.claude-plugin/plugin.json` (the actual manifest `claude plugin install` reads) wires exactly two hooks — `SessionStart` → `src/hooks/caveman-activate.js`, `UserPromptSubmit` → `src/hooks/caveman-mode-tracker.js` — same two names as our standalone files, confirming they are drop-in replacements.

## SessionStart injection size, before vs after (measured, not estimated)

Ran the actual hook scripts with `CLAUDE_CONFIG_DIR` pointed at a scratch dir so nothing touched real `~/.claude`:

| | Mode | Source of ruleset | Output size |
|---|---|---|---|
| Before (old standalone hook, this repo's copy) | lite (no `SKILL.md` installed) | hardcoded fallback string in `caveman-activate.js` | 1828 chars (~457 tokens @ 4 chars/tok) |
| After (plugin hook, `SKILL.md` present) | ultra | `SKILL.md`, filtered to the `ultra` row + only-ultra examples | 5827 chars (~1457 tokens @ 4 chars/tok) |

**The injection got ~3.2x bigger, not smaller.** The plugin's own code comments explain why (`caveman-activate.js`): the old 2-sentence fallback summary was found too weak — models drifted back to verbose mid-session — so the plugin now injects the full filtered `SKILL.md` ruleset (with examples) every session instead of a short fallback. The savings this plugin claims are on the *output* side (shorter replies), not the SessionStart injection — see README's own numbers table, which is explicit that this trade-off is a deliberate bet, not free.

## Thai smoke test (3 headless runs, `claude -p ... --model claude-sonnet-5`, mode=ultra confirmed via `~/.claude/.caveman-active`)

**(a) Thai explanation question** — prompt: "อธิบายให้ฟังหน่อยว่า HTTP status code 404 กับ 500 ต่างกันยังไง แล้วเวลาเจอ error ไหนควรแก้ตรงฝั่งไหน (client หรือ server)"

Reply (verbatim):
```
404: resource not found. URL/route wrong, or item deleted/never existed. Fix client side — bad link, wrong ID, typo in path.

500: server crashed handling request. Server-side bug — unhandled exception, DB down, null ref, bad config. Fix server side, check server logs/stack trace.

Quick test: change request (fix URL/params) → still fails same way? 500 stays server's problem. 404 goes away with correct URL → confirms client-side.
```
**Note: reply came back entirely in English despite the Thai question.**

**(b) Bug-fix, 10-line Python snippet** — prompt: "โค้ด python นี้มีบั๊ก ช่วยหาที่ผิดแล้วบอกวิธีแก้หน่อย" + a `get_average`/`process_scores` snippet that divides by zero on an empty list.

Reply (verbatim):
```
Bug: empty list crashes with `ZeroDivisionError` (`total / len(numbers)` → `total / 0`).

Fix — guard empty case in `get_average`:

def get_average(numbers):
    if not numbers:
        return 0  # or None, or raise ValueError, depending on what caller wants
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)

Pick behavior per your need: `0`, `None`, or raise `ValueError("empty list")` if empty input should be an error, not silently averaged to 0.
```
**Note: also came back entirely in English.**

**(c) "สรุปย่อหน้านี้" over a 15-line Thai paragraph** (paragraph written by me — a coffee-shop-owner story) —

Reply (verbatim):
```
ร้านกาแฟเล็กมุมถนนเงียบ เจ้าของเป็นผู้หญิงวัยกลางคน ลาออกจากงานออฟฟิศตามฝัน ใช้เมล็ดออร์แกนิกจากเชียงราย คั่วเองทุกเช้าตีห้า จุดขายคือบรรยากาศอบอุ่น+จำลูกค้าได้ ไม่มีโฆษณาแต่อยู่รอด 5 ปีด้วยปากต่อปาก เพิ่งเริ่มขายกาแฟคั่วบดออนไลน์ให้ลูกค้าต่างจังหวัด
```
**This one stayed in Thai and compressed well** (dropped particles/connectors, kept every fact — coffee origin, 5-years-by-word-of-mouth, online expansion).

**CTO judgment call needed:** 2 of 3 replies (a, b — the more "technical/Western" framed prompts) switched to English despite the caveman skill's explicit "preserve the user's dominant language" rule; only (c), a pure-Thai literary-style prompt, stayed in Thai. This looks like language-preservation getting weaker under `ultra` compression when the topic is technical (HTTP codes, Python), possibly because the model leans on English technical-writing habits once terseness is maximized. Worth a second, larger sample before trusting `ultra` for Thai technical Q&A — flagged, not fixed (out of this task's scope).

## Files changed

- `claude-home/plugins.txt` — added `marketplace caveman=JuliusBrussee/caveman` + `plugin caveman@caveman`.
- `claude-home/settings.json` — removed the two standalone caveman hook entries (`SessionStart`/`UserPromptSubmit`); added `caveman@caveman` to `enabledPlugins` + `caveman` to `extraKnownMarketplaces`. Every other hook, `statusLine`, and the `"model"` line untouched. Valid JSON (verified with `python3 -c "import json; json.load(...)"`).
- `claude-home/hooks/caveman-activate.js`, `caveman-config.js`, `caveman-mode-tracker.js`, `caveman-statusline.sh` — `git rm`'d (superseded by the plugin's own hooks).
- `roles/cto.md`, `roles/cmo.md`, `roles/cgo.md`, `roles/cfo.md` — added-only `## Report length (CEO 2026-09-25)` block after the existing Skill learning section.
- `docs/ops/caveman-plugin-2026-09-25.md` — new. Install steps, mode switching, settings.json diff, known statusline-badge regression, rollback.
- `docs/reports/task-9c6daaf7/WORKLOG.md`, `REPORT.md` — this report.

Outside the repo (per task, no installer mechanism covers it): `~/.config/caveman/config.json` → `{"defaultMode":"ultra"}` (was `{"defaultMode":"lite"}`).

## Tests

- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests -p no:warnings` (no venv inside this worktree — used the main checkout's `.venv`, same interpreter as `pytest.ini` targets)
- passed: 1130
- failed: 1
- skipped: 16

Failure (pre-existing, on the task's known list): `tests/test_machine_doctor.py::test_detect_machine_by_unique_os_when_hostname_does_not_match` — asserts Linux-hostname-fallback behavior; this Mac resolves `macbox` instead of `linuxbox`, an environment (OS) mismatch, not something this change touched.

Also ran in isolation, per the task's other two named pre-existing failures — **both passed clean in this run**, did not reproduce:
- `tests/test_multihost.py::test_browser_operator_cap_reached_sets_conflict` — passed
- `tests/test_worktree_sparse.py` — passed (no ERROR), likely disk-state-dependent per the task's own note

Also ran individually, both green:
- `tests/test_token_saving_config.py` — 4 passed (still reads `settings.json` fine; the entries it asserts on were not among the ones removed)
- `scripts/test_install_claude_home.py` (via `pytest`, not direct execution — the file's own docstring says `.venv/bin/python -m pytest scripts/test_install_claude_home.py`) — 7 passed. Its fixture carries no `plugins.txt`, so it doesn't exercise the new caveman rows directly — confirmed via the file's own docstring.

## Issues / Blockers

- **Statusline badge regression** (not fixed, per instructions not to touch `scripts/statusline.sh`): it looks for the badge script at `$CLAUDE_CONFIG_DIR/hooks/caveman-statusline.sh`, which we just removed. The plugin ships its own `caveman-statusline.sh` but at `$CLAUDE_PLUGIN_ROOT/src/hooks/` (`~/.claude/plugins/cache/caveman/caveman/2.7.0/src/hooks/` on this machine), never linked into `~/.claude/hooks/`. Net effect: the `[CAVEMAN:xxx]` badge in the terminal statusline goes silently empty (guarded with `[ -f ... ]`, so nothing crashes — the SID tag still renders). Full detail in `docs/ops/caveman-plugin-2026-09-25.md`.
- **Language drift under `ultra`** (see Thai smoke test above) — 2/3 replies switched to English on technical prompts. Flagged for CEO/CTO judgment, not something this task asked me to fix.

## Notes for Reviewer

- `claude plugin marketplace add` / `claude plugin install` were run for real against GitHub (network access, matches task's explicit ask) — confirmed live via `claude plugin list` showing `caveman@caveman ... Status: ✔ enabled`.
- The plugin's actual runtime hook path (`$CLAUDE_PLUGIN_ROOT`) resolves to `~/.claude/plugins/cache/caveman/caveman/2.7.0/`, not the marketplace checkout at `~/.claude/plugins/marketplaces/caveman/` — worth knowing if debugging hook behavior later; the marketplace checkout is the *source*, the cache dir under a pinned version is what actually executes.
- Diff stat for the commit: `12 files changed, 123 insertions(+), 449 deletions(-)`.

## Skill learning
- WRONG   : (none)
- MISSING [no owner] : no skill covers reproducing a plugin's *external* (non-`~/.claude`) config file (`~/.config/caveman/config.json`) on a fresh machine — `scripts/install-claude-home.sh`'s `ENTRIES` array only links things under `~/.claude`. Evidence: task-9c6daaf7, `scripts/install-claude-home.sh` lines 35/117-133. Any future plugin with an XDG-style config dir hits the same gap — worth a line in `hq-filing` or a new "external tool config" convention.
- COSTLY  [no owner] : finding the *actual* runtime hook path for an installed Claude Code plugin took three lookups (marketplace checkout → `.claude-plugin/plugin.json` manifest → `installed_plugins.json`'s `installPath` under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`) because `CLAUDE_PLUGIN_ROOT` does not equal the marketplace checkout path. Evidence: task-9c6daaf7, this report's "Notes for Reviewer". Prevented by: a one-line note in a Claude Code plugin-authoring skill (none exists in this org's skill list) that `$CLAUDE_PLUGIN_ROOT` = the versioned cache dir, not the marketplace source.
