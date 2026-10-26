# REPORT task-aeb9af11

## Done
- Wrote `docs/research/2026-10-26-human-writing-checkers-th.md`: Thai CEO summary (7 lines, no guillemets, no em dash), 14-row tool table (Thai-path tools ranked first), then questions 2 to 5 in English.
- Main findings:
  - Only TLTK and PyThaiNLP have a Thai path, and neither judges "sounds human".
  - Detectors are unreliable on Thai and on short text. They are a hint at best, never a gate.
  - Our rule 3 ("small typos are fine") conflicts with the CEO's 26 Oct aim.
  - The Royal Society standard uses curly double quotes, and our gate bans them for keyboard reasons only.
- Recommendation: a Thai pattern lint (hard character check plus soft phrase warnings) and a fresh-reader "restate in one line" test, 5 to 8 h, free, no install.

## Files changed
- `docs/research/2026-10-26-human-writing-checkers-th.md` (new)
- `docs/reports/task-aeb9af11/REPORT.md` (this report)

## Validation performed
- Read the local files the brief names (WRITING-RULES.md, check-post-text.sh, humanizer and de-ai-ify SKILL.md).
- Re-read the note for banned characters in the Thai summary; replaced the guillemets I had put in it. No shell run (AGY contract), so no grep over the whole file.

## Limitations
- Web search returns written summaries with redirect links. I could not open any README, paper, commit list or the Royal Society book. So every external claim is marked R (reported), none V.
- No last-commit date was obtained for any repo.
- Source URLs come from summaries and memory, unopened.

## Blockers
- (none)

## Not checked / risk
- `.claude/skills/CMO_Standard_HumanVoice_TH/SKILL.md` is missing in this worktree. Gap analysis is against WRITING-RULES.md and the script, so a few gaps may already be covered by that skill's 10 tells.
- `check-post-text.sh` in this worktree has no guillemets yet (added elsewhere).
- Royal Society spacing details (sentence-end spacing, comma, ๆ) are summary-level and need one read of the original.
- Thai detector evidence is thin: no Thai-specific paper surfaced. Vendor accuracy numbers for Thai are self-reported.
- The comprehension-test idea has no tested source. It is a pilot, with a same-family-model bias risk.
- Effort estimates are my own.

## Skill learning
- MISSING [CMO_Standard_HumanVoice_TH]: not present in this task worktree, so the research could not compare against its 10 tells. Evidence: file read returned "does not exist".
- WRONG [WRITING-RULES §rule 3]: "small typos are fine, too perfect is a warning sign" pushes imitation, not clarity. It contradicts the CEO's 26 Oct order.
- WRONG [WRITING-RULES §rule 2 wording]: curly quotes are banned for keyboard reasons. The Royal Society standard for printed Thai uses them (reported). Do not describe them as "not Thai".
- MISSING [de-ai-ify §Scoring]: the score and Flesch targets are unsourced and English-based. Do not use on Thai.
- COSTLY [research tooling]: the web search tool only returns summaries, so nothing could reach "verified". A researcher with page-fetch access would close the R claims in about 1 h.
