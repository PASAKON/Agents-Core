# REPORT task-a4a427a7

## Changes

Restored the reviewed implementation from commit 26c6485b because the supplied
branch actually started at 3a3036ed. The winbox kit_paths fix is preserved exactly.
Git metadata is read-only, so preserving that commit as an ancestor requires
the launcher to reconcile branch history before committing these working files.

Files changed:
- tools/mesh_check.py: KIT w5 collector and table; only skills_repo requires 120.
  For linked task worktrees without a venv, MCP names use the primary checkout's
  generator, resolved read-only through git rev-parse --git-common-dir.
- config/hosts.yaml: preserved the CTO's winbox kit_paths.
- docs/ops/mesh-check.md: Contabo collector, KIT and corrected skill threshold,
  plus documentation of the primary-launcher interpretation for worktrees.
- scripts/install-claude-home.sh: preserved read-only --check.
- tests/test_mesh_check.py and tests/test_mesh_check_l9.py: preserved prior updates.
- tests/test_mesh_check_kit.py: fixture repositories, revised failure cases,
  informational home skills and linked-worktree MCP regression coverage.
- This report.

MCP diagnosis: _names_for("project_head") returns org and lungnote, and the
three-argument _build signature is correct. The task worktree lacks .venv,
so _build("org", worktree, "project_head") returns None. The generator refuses
a role configuration without org. Inspecting the primary checkout's launcher
config in memory returns lungnote and org. No config files or servers are created;
only names are returned, never environment or credential values.

## Validation

- Repository virtualenv pytest: tests/test_mesh_check.py,
  tests/test_mesh_check_l9.py, tests/test_mesh_check_kit.py,
  scripts/test_install_claude_home.py: **226 passed in 26.54s**.
- bash -n scripts/install-claude-home.sh: passed.
- git diff --check: passed.
- Fresh python3 -B -m tools.mesh_check --local --json: exit 0.
- KIT sample: core.behind=0; rules=n/a; wikis=n/a; memory=n/a;
  skills_repo=120; skills_home=11; role=true; launcher=true; hooks=true;
  mcp_names=["lungnote","org"]; claude_home="drift 32 lines".
- KIT verdict: rules:n/a; wikis:n/a; memory:n/a.
- Gitleaks stdin --redact on the tracked diff plus both new files: no leaks.

## Limitations

No live Windows/macOS or cross-host run. System Python cannot resolve the
configured companion checkouts here, so their facts remain n/a.
MCP names represent launch configuration, not a running-session assertion.
Freshness uses the last fetched origin/main; no fetch was requested.
Read-only default, L4 behind --live, and no snapshot writes remain unchanged
from the accepted implementation.

## Blockers

- PR number: unavailable; no PR opened.
- Current HEAD: 3a3036ed8b7b38727ef5b6171d43e2fa1770a489 (pre-change).
- git merge --ff-only 26c6485b failed because shared Git metadata is read-only.
  No commit or push is possible in this sandbox.
- gh auth status reports invalid GitHub credentials. No sign-in attempted.
- Launcher must preserve 26c6485b in branch history, commit and push the
  validated working files, then open the PR from agent/codex-task-a4a427a7
  against main. Do not push local main.

## Ready PR body

Title: Add w5 KIT parity checks to mesh_check

Adds diagonal KIT checks and a compact facts table for the Contabo collector.
KIT checks repository freshness, checkout skills, PH role/launcher and hooks.
Home skills are informational. Linked worktrees without a venv inspect their
primary checkout's PH launcher config in memory and return server names only.

Behaviour change: default collection is read-only, L4 now requires --live,
and mesh_check no longer writes snapshots. Fetch requires --kit-fetch.

Preserves the winbox kit_paths fix from 26c6485b. Validation: 226 tests passed,
shell syntax, diff whitespace and Gitleaks checks passed. Fresh Contabo sample reports
120 checkout skills, 11 home skills, and MCP names lungnote/org; companion
checkout facts are unavailable in this worker environment.

## Skill learning

- (none)
