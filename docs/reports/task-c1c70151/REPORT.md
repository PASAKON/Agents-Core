# REPORT task-c1c70151

Iteration 8 of PR #584 (C4 + C5, continuing task-c4939966), Claude Sonnet 5.5.

The PH branch `origin/ph-a08/c4c5-remote-publish-steward` is merged into `agent/agy-task-c1c70151` (clean). On top of it:

- the outgoing check and the push use a scratch repository the hub builds, fetch the public history from one URL the dispatcher holds, refuse a `pushurl` that differs from `url`, and scan merge commits;
- `hub_reap` and PH publish need the mesh flag; the PH publish check reads the project stage from the hub;
- every winbox verb needs 4 GiB of free RAM before it starts git;
- the recovery commit runs the repository's commit hooks; the reap stamp files are opened without following links or waiting on pipes;
- `.gitignore` lists the mesh audit directory and the reap stamp files; `conftest.py` clears the mesh env flags;
- the task-c4939966 report is corrected (status, coverage statement, patch file removed).

Details, test tails, the fail-without-fix check and `## Not checked / risk` are in `docs/reports/task-c4939966/REPORT.md` ("Iteration 8").

## Not checked / risk

- Nothing ran on winbox or the Mac; `publish_url` (project key from the worktree directory name, ssh form of the project remote) is untested live.
- Only targeted test files ran, one at a time; the rest of the suite is CI on PR #584.
