1. GOAL: `INDEX.md` gains exactly one row linking `playbooks/claudeflow-tools-registry.md`, and `python3 tools/check_links.py` reports no broken link for that new row (its other, pre-existing findings are unchanged). `git diff --stat` shows 1 file, 1 line added.
2. FILES you may touch: `INDEX.md` only. No other file.
3. FORBIDDEN: any other edit to INDEX.md (no reformatting, no reordering, no fixing other rows); scratch/log/output files; editing tools/check_links.py.
4. WHAT IS KNOWN (verified 2026-09-23 on main): `playbooks/claudeflow-tools-registry.md` exists; INDEX.md does not mention it anywhere; the Playbooks table has the row `| Claudeflow ↔ webapp verify | [\`playbooks/claudeflow-verify-broker-handoff.md\`](playbooks/claudeflow-verify-broker-handoff.md) | Broker verify HTTP tools API contract |` (currently line 47). Insert directly AFTER that row, verbatim:
   `| **Claudeflow LLM tools registry** | [\`playbooks/claudeflow-tools-registry.md\`](playbooks/claudeflow-tools-registry.md) | Tool naming convention (UPPERCASE_PREFIX), prefix taxonomy, current registry, KB_LOOKUP usage, adding-new-tool checklist. Read before adding/renaming any Lunar/SomPong tool. |`
   Source: GitHub issue PASAKON/Agents-Wikis#4.
5. ENV NOTE: no test suite here; the verdict is the link checker's output (standard library only).
6. DELIVERABLE: one PR titled "INDEX.md: link claudeflow-tools-registry playbook (#4)"; description = the diff line and the check_links.py output line for the new link. Put "Closes #4" in the description.
7. FACTS, NOT GUESSES: cite the command output; anything not established is "unknown — not verified".
8. No questions needed; proceed. If a fact above is wrong, say which in the PR and continue with the correct one.
