# `knowledge/` — per-role knowledge banks

Each subdirectory is a knowledge repo for one worker role, modeled after
[`mooniex-claudesign`](https://github.com/PASAKON/mooniex-claudesign) (the
web_designer's knowledge bank that lives at
`/Users/gob/Projects/mooniex-claudesign/`).

These directories are **dual-access**:
- **Workers** read via symlink injected into their worktree on
  `delegate_task` (see `runners/dev_init.py::KNOWLEDGE_MAP` and
  `_symlink_knowledge()`).
- **C-level** (CTO/CMO/CGO/CFO) read directly from this path during
  planning, task brief authoring, or review.

## Directory shape (universal)

Every `<role>-knowledge/` directory follows the three-layer claudesign
anatomy:

```
<role>-knowledge/
  ├─ skills/                # artifact-shape playbooks (one folder per skill)
  │  └─ <skill-name>/
  │     ├─ SKILL.md         # frontmatter + body + acceptance
  │     └─ example.*        # reference output
  ├─ <brand-tier-dir>/      # role-specific dimension:
  │  ├─ campaigns/   (ads)       # brand × channel mix
  │  ├─ voices/      (content)   # brand voice docs
  │  ├─ models/      (data)      # KPI definitions + formulas
  │  └─ envelopes/   (finance)   # current budget per project
  ├─ craft/                 # universal anti-patterns + linted rules
  │  └─ *.md
  ├─ AGENTS.md              # how agents should use this repo
  └─ CLAUDE.md              # rules + read-order for this role
```

## Current roles

| Role | Path | Status |
|---|---|---|
| web_designer | `/Users/gob/Projects/mooniex-claudesign/` (external, unchanged) | live, used by claudesign workers |
| ads_manager | `knowledge/ads-knowledge/` | scaffolded, content TBD |
| content_strategist | `knowledge/content-knowledge/` | live — skills (rebate-copy, fb-caption) + craft (anti-content-slop) populated |
| data_analyst | `knowledge/data-knowledge/` | scaffolded, content TBD |
| CFO + (CFO-borrow worker) | `knowledge/finance-knowledge/` | scaffolded, content TBD |

## KNOWLEDGE_MAP

`runners/dev_init.py` defines `KNOWLEDGE_MAP` — a dict mapping role name to
the relative path under `knowledge/`:

```python
KNOWLEDGE_MAP = {
    "ads_manager": "knowledge/ads-knowledge",
    "content_strategist": "knowledge/content-knowledge",
    "data_analyst": "knowledge/data-knowledge",
    "cfo": "knowledge/finance-knowledge",
    "finance": "knowledge/finance-knowledge",
}
```

During worktree setup (`delegate_task` → `dev_init`), `_symlink_knowledge()`
creates a symlink at `<worktree>/knowledge/<bank-name>` pointing to the
shared bank directory. The symlink is read-only-intent (workers must not
write back into the shared bank). The same wiring runs on resume
(`dev_resume.py`).

Roles not in `KNOWLEDGE_MAP` (developer, tester, devops_engineer, etc.)
are silently skipped — no error.

## Read this before contributing

- Wiki playbook: [`LLMs/playbooks/knowledge-structure.md`](../../LLMs/playbooks/knowledge-structure.md)
- Reference: [`mooniex-claudesign/CLAUDE.md`](/Users/gob/Projects/mooniex-claudesign/CLAUDE.md)
- Anti-AI rules to mirror: [`mooniex-claudesign/craft/anti-ai-slop.md`](/Users/gob/Projects/mooniex-claudesign/craft/anti-ai-slop.md)

## Adding a skill

1. `mkdir <role>-knowledge/skills/<skill-name>`
2. Write `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: <one sentence — used by triggers + grep>
   triggers: ["keyword1", "phrase 2"]
   acceptance:
     - <criterion 1>
     - <criterion 2>
   ---
   # Body
   ```
3. Add reference output as `example.<ext>` next to `SKILL.md`.
4. Update role md (`roles/<role>.md`) if this skill changes the pre-work checklist.

## Adding a craft file

Use sparingly. Craft files are universal anti-patterns or invariants
that apply to **every** task of that role. Each rule should:
- Be checkable (auto-lintable or one-line manual check).
- Reference a real incident or concrete principle (no theory).
- Stay <300 lines per file.

## Adding a brand-tier doc

| Role | Dir | One file per |
|---|---|---|
| ads_manager | `campaigns/<brand>/CAMPAIGN.md` | brand |
| content_strategist | `voices/<brand>/VOICE.md` | brand |
| data_analyst | `models/<brand>/MODEL.md` | brand |
| finance | `envelopes/<brand>-FY<year>.md` | brand-year |
