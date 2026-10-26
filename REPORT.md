# REPORT task-3c96bb47

## Summary
`tools/ilag_theme.py` now draws the v2 palette (gold, white, black, CEO 2026-10-26): the Story end card is a BLACK plate with a GOLD line 1, a WHITE line 2 and a MIST line 3, and the poster prompt asks ChatGPT for a pure BLACK panel with the v2 tokens filled in from the module. No navy or cream value is drawn on any render path; `tests/test_ilag_theme.py` (22 tests) pins the hex values and the absence of v1.

## Files Changed
- tools/ilag_theme.py: v2 tokens (BLACK, WHITE, GOLD, GOLD_METAL top to bottom, STAMP_GOLD, INK, MIST); NAVY, CARD_BG, CARD_GOLD, CARD_WHITE, CARD_CREAM removed, one comment names them as v1; poster prompt re-coloured and fed from the tokens; Story card moved out of `story()` into `card_image()` (same drawing code the test and the sample use); `_font()` falls back to the kit's OFL Taviraj where Sukhumvit Set is missing (Contabo, winbox); guillemets in Thai text replaced by straight quotes; em dashes removed from the file.
- tests/test_ilag_theme.py: new, 22 tests.
- REPORT.md: this file.

## Commits
- 494a30cd: ilag_theme: palette v2 (gold, white, black) for the poster prompt and the Story card
- 3331151f: ilag_theme: test the Story to ffmpeg hand-off, escape the guillemet check

## Tests
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ilag_theme.py -p no:cacheprovider`
- passed: 22
- failed: 0
- skipped: 0

Output tail:
```
......................                                                   [100%]
22 passed in 1.28s
```
Teeth, checked: against the v1 tool (`git checkout HEAD~1 -- tools/ilag_theme.py`) 15 of the 21 tests then in the file failed; with one line changed to draw the question in the old cream (#FFF4D6) 3 failed (`lines_are_gold_white_mist`, `draws_only_the_v2_colours`, `no_render_path_refers_to_a_v1_token`). Both restored; `-k "ilag or workdir"` over `tests/` also green.

## Sample
`/root/MoonieXHQ/Work/task-3c96bb47/out/ilag-v2-story-card-sample.png` (53 KB, 1080x1920 RGBA, the card overlay alone, transparent outside the plate; title "ขายฝากนาแม่", the EP4 question). Looked at over a grey frame: black plate, gold line 1, white line 2, mist question, tone marks intact. Font on this host is Taviraj (no Sukhumvit Set on Contabo), so the Mac render will differ in typeface only.

## Issues / Blockers
- None blocking. The brief says "PR when done" but Hard Rule 2 forbids `git push`; the branch `agent/developer-task-3c96bb47` (2 commits on origin/main 11fa53f6) is ready for the CTO or PH to push and open the PR. No PR was opened.

## Notes for Reviewer
Reach, checked before the first edit: `tools/ilag_theme.py` has no importer anywhere in the repo (grep over *.py); the removed names (CARD_BG, CARD_CREAM, CARD_GOLD, CARD_WHITE, NAVY) appear in no other module. Its three commands (`poster-job`, `logo`, `story`) are the only entry points; `logo` is untouched (it looks for the empty white circle, still drawn white on the black panel).

Decisions to confirm or flip (each is one constant or one line):
1. **Plate opacity.** v1 was `#0C0D1E` at 88 %. The brief says card grounds are BLACK #0A0A0A, so the plate is now opaque BLACK (the exact hex reaches the screen). If the CMO wants the film to show through, change the plate fill to `(10, 10, 10, 225)`.
2. **No gold border** on the plate: the brief named ground and line colours only.
3. **GOLD_METAL order** is top to bottom (#FDE165, #F7C440, #E49C1D) as the brief gives it; v1 listed it shadow first. Nothing in the tool read the tuple by index.
4. **Poster prompt**, untested on ChatGPT (n=0, as v1 was before its first run): panel pure black; headline gradient and number discs take the tokens; digits and tip text are INK #111111 on gold; the footer strip's "last orange light" became "a last thin line of gold light" (orange is not in the palette); a closing line "Colours: only black, white and gold." Footer line now `ดูละครสั้น "<title>" ได้ที่เพจ` with straight quotes.
5. **Font.** The v2 brief does not mention fonts. Sukhumvit Set stays primary where it exists; elsewhere Taviraj Bold (face 5) and Semi Bold (face 4) from `knowledge/brand-knowledge/brands/ilag/templates/fonts/`, which BRAND.md already proposes for the end card.
6. **STAMP_GOLD** is defined and tested but no render path of this tool draws a stamp, so nothing uses it yet.

Left on v1 (not mine to edit, CMO owns): `.claude/skills/CTO_ILAG_LakornTheme/SKILL.md` (description, "The tool has not moved yet", §Theme tokens table, §Poster layout navy panel and navy digit, §Story end card table with CARD_*, Workflow step 5 compares with the navy approved poster); `knowledge/brand-knowledge/brands/ilag/BRAND.md` §Palette in this tree (the v2 commit is not on origin); `templates/kit.tpl.html` (`--navy`, `--cream`); `.claude/skills/CMO_Procedure_ChatGPTImage_LakornCover/SKILL.md` line 98 and a field note that say the tool still draws navy; the approved reference files under Assets/Agents/Core/ilag-theme/ are navy renders. `docs/ops/thai-inventory-2026-10-14/` lists the old tool's strings (a dated snapshot, left alone).

## Not checked / risk
- The poster prompt was never sent to ChatGPT, and `story` was not run through a real ffmpeg encode (brief: no full renders; the hand-off is tested with a stubbed `subprocess.run`, the ffmpeg arguments are unchanged). First real poster and first real clip may need a tweak.
- Not run: the repo's full pytest suite (only `tests/test_ilag_theme.py` and `-k "ilag or workdir"`); the change touches one module that nothing else imports.
- The Mac Sukhumvit path of `_font` was not exercised (no Sukhumvit Set on Contabo); it is the old call moved into a function.

## Skill learning
- MISSING [CTO_ILAG_LakornTheme §Story end card] : the skill table already writes line 1 as `ดูเต็มเรื่อง "<title>"` with straight quotes, but the tool drew guillemets, so skill and tool disagreed and the IRON/CEO no-guillemet rule was broken in every card since 2026-09-28 · evidence: task-3c96bb47, tools/ilag_theme.py at 11fa53f6 (`«{a.title}»`) vs SKILL.md line 89
- MISSING [CTO_ILAG_LakornTheme §Model scope] : which font each host draws. Sukhumvit Set exists only on the Mac; on Contabo/winbox the card now uses Taviraj, so the same card differs in typeface by machine until the CMO picks one font · evidence: task-3c96bb47, `_font()` in tools/ilag_theme.py
- MISSING [CTO_ILAG_LakornTheme §Theme tokens] : the v2 table needs GOLD_METAL's order stated (top to bottom now, v1 tuple was shadow first) and the plate opacity decision (v1 88 %, v2 opaque BLACK) · evidence: task-3c96bb47 REPORT Notes 1 and 3
- COSTLY [no owner] : the v2 palette lives in a BRAND.md commit that is not on origin, so the worker had to take the values from the brief and could not diff against the source · prevented by: land the BRAND.md palette commit before delegating a tool change that must match it
