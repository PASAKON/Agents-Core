# CTO-FEEDBACK-4 — STOP all browser work (CEO 2026-09-26: "Worker วนลูป เปิด tab ไม่หยุด")

This replaces step 1-6 of CTO-FEEDBACK-3.
- Run NO more scripts against Chrome :9230. No exploration, no delete attempt, no new tabs.
  The CTO closed 10 extra tabs; one Business Suite tab is left open. Do not touch it.
- The test post (4116998775270501, [TEST-a151e260]) will be deleted by hand. Do not try.
- Now: commit what you have, then write docs/reports/task-cfdc75a8/REPORT.md and WORKLOG.md.
  Include: the leak-audit table (measured / not tested), both test-post runs with their exit
  codes, the comment-author bug (exit 7 on the real page), the three live bugs you fixed in
  e472e6d3, why Delete was not found (what you tried, which UI surfaces), how many tabs your
  scripts opened and why they were not closed, and the Skill learning section.
- A script that opens a tab must close it in a `finally`. Add that fix if it is small; if not,
  list it in REPORT.md as open.
