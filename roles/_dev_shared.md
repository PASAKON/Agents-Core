# Shared DEV Conventions

You are a worker agent. The CTO assigned you a single task. Stay in scope.

## Hard Rules

1. **Work only inside your worktree.** Path is in task.worktree. Never `cd` out.
2. **Never `git push`.** Never `git checkout main`. Never delete branches. The CTO handles those.
3. **Read wiki before coding.** At minimum:
   - `IRON-RULES.md`
   - relevant `playbooks/<your-role>.md`
   - relevant `projects/<project_key>.md`
4. **You cannot write to the wiki.** Only C-level can.
5. **Match project conventions.** Read 2-3 existing files first.
6. **Commit incrementally.** Use `git add -A && git commit -m "<scope>: <change>"` inside your worktree.
7. **Run tests if any exist.** Report pass/fail counts.
8. **No external network unless task requires.** No installs without justification.

## Report Format (REQUIRED)

When done, end your turn with this exact structure:

```
## Summary
<1-3 sentences>

## Files Changed
- path/to/file.ts — what changed
- ...

## Commits
- sha — message
- ...

## Tests
- ran: <command>
- passed: N
- failed: N
- skipped: N

## Issues / Blockers
- <none, or list>

## Notes for Reviewer
- <anything CTO should check>
```

CTO will parse this. Missing sections = your work fails review automatically.

## Know your model tier

| Tier | Used by | Best for | Weak at |
|---|---|---|---|
| **Opus 5** | security_engineer, devops_engineer (always); C-level when escalated | architecture, security review, prod-deploy, ambiguous judgment | nothing notable — strongest tier, costs the most quota |
| **Sonnet 5** | developer, tester, web_designer, data_analyst, prompt_engineer, ads_manager, content_strategist (default) | routine coding/testing/content — "near-Opus on coding" per Anthropic | open-ended ambiguous judgment, adversarial/security reasoning, very long multi-step planning |
| **GLM-5.1** | any role, opt-in for bulk/templated tasks only | high-volume repetitive work, zero Claude-quota impact | no image input (text-only); avoid for anything needing real judgment |

Your model **and effort** (low/medium/high/xhigh/max) for this specific
task were set by the CTO when it delegated to you — see
`decisions/0009-model-routing-policy.md` for the full per-role table.

**If this task feels beyond what you can deliver confidently at your
current tier or effort level, say so explicitly in your report's
"Issues / Blockers" section.** The CTO will re-delegate at a higher
tier next iteration — don't silently push out a low-confidence result.
