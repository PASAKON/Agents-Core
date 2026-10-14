Count and guard Agent/Task dev calls that bypass delegate_task, and flag code writes in Project Head sessions. The Agent hook reuses the §59 parser, logs every decision without prompts, and refuses missing/invalid codes when enforcement is active. PH reminders are capped at one per session per 30 minutes; every detected write is still counted.

Add a Bangkok-day runner-share CLI with worker counts, Codex/AGY share, and per-session Agent/PH counts. Existing hooks and permissions are unchanged. No timer or mail delivery is added.

Validation: new stdin fixtures and all tests/test_route*.py; see REPORT.md for final counts and secret-scan evidence.

Merge requirement: set config/agent-route.yaml enforce_after to actual merge time plus 24 hours. The checked-in value is provisional. Scan the launcher's final commits with gitleaks before opening this single PR to PASAKON/Agents-Core main.

🤖 Generated with [Claude Code](https://claude.ai/code)
