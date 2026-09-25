# Global Personal Instructions

## Language and tone (permanent — CEO 2026-06-15)

Talk like a normal person chatting. Casual and direct is fine; **never use crude
Thai pronouns (มึง / กู) or swear words.** This is not a demand for stiff
formality — no need for ผม/คุณ on every line — just an everyday conversational
register. Brevity (including caveman mode) still applies; brevity is not
crudeness. Code, commits, and PRs keep their normal professional register.
Mirrors IRON-RULES §37.

**Language lock (CEO 2026-09-25, caveman `ultra`):** answer in the language the CEO wrote in — a Thai prompt gets a Thai reply (technical terms may stay English). caveman shortens; it never switches language. Measured 2026-09-25: under `ultra`, 2 of 3 Thai technical prompts came back in English (task-9c6daaf7).


## Spawning the virtual org

On "spawn cto", "spawn agent", "เปิด CTO", "เรียก CTO", "open the org", "fire up
the agents" — run it, do not ask:

```bash
bash /Users/gob/MoonieXHQ/Agents/Core/scripts/spawn-cto.sh   # --new | --last | --resume <id>
```

"chat with cto" means inline in the current terminal instead:
`cd /Users/gob/MoonieXHQ/Agents/Core && source .venv/bin/activate && python -m runners.cto_chat`

## Paths

Canonical projects dir is `/Users/gob/Projects/` (capital P). APFS is
case-insensitive, so lowercase resolves to the same inode — always write the
cap-P form in code, configs, and docs.

- Org runtime: `/Users/gob/MoonieXHQ/Agents/Core/` (dashboard: `python dashboard.py`)
- Wikis, C-level write only: `org:` → `Agents-Wikis/`, `mooniex:` → `LLMs/`

## GateGuard fact protocol (ECC hook)

`gateguard-fact-force` blocks a tool call until facts are stated. It records
what it has already cleared in `~/.gateguard/state-<session-id>.json`, shaped
`{"checked": ["<abs path>", …, "__bash_session__"], "last_active": <epoch ms>}`.
That file is the authority on when it re-arms:

- **Bash** clears once per session — a single key, `__bash_session__`.
- **Edit / Write** clear **per absolute file path.** A new file arms it again,
  no matter how many files you have already cleared.
- **Everything resets after an idle gap** (`last_active`), so a long session
  that pauses gets gated from scratch. Expect several rounds in a working day.

**You cannot pre-empt it — budget one error per new file.** It is a PreToolUse
hook: it inspects the call, not the prose above it. Stating the facts in the
message immediately before the first `Edit` on a file was measured (2026-08-17)
to still produce the error. State them, retry the identical call, then edit
that same file freely.

**The three fact lists differ. Answer the one in the error you just got, not
the closest-looking one** — Edit and Write ask different questions, and giving
Write's answers at an Edit gate is rejected.

- **Bash** (2): the current request in one sentence; what this command verifies
  or produces.
- **Write**, a new file (4): name the file(s) and line(s) that will **call** it;
  confirm no existing file serves the same purpose (use **Glob**); field names,
  structure and date format if it touches data (redacted); the user's
  instruction verbatim.
- **Edit**, an existing file (4): list all files that **import or require** it
  (use **Grep**); list the **public functions or classes** the change affects;
  field names, structure and date format if it touches data (redacted); the
  user's instruction verbatim.

Escape hatch for genuine setup or repair only: `ECC_GATEGUARD=off`, or add
`pre:bash:gateguard-fact-force` / `pre:edit-write:gateguard-fact-force` to
`ECC_DISABLED_HOOKS`. Never to bypass for production work.

## Skill routing

Every org-owned skill now carries its own `scope` plus an explicit "Use instead
of X" clause in its `description`, so per-domain routing (SEO, growth, content,
KPI, retention, finance, tool-building, image prompts) lives in the skill itself
and is no longer repeated here. What remains are the conflicts involving skills
we do not own:

- **Google Drive — any action at all** (upload, backup, move, rename, delete,
  create folder; via rclone, the gdrive-bridge, the Drive MCP, or a synced
  folder) → read `gdrive-filing` FIRST, every session, before the first Drive
  call. It is the CEO's rule (2026-09-06) and a PreToolUse hook in the Agents
  repo (`scripts/hook-gdrive-skill-gate.py`) blocks Drive-touching calls until
  the skill has been read. Google's own limits are not the rules; the skill is.
- **Debugging** (bug report, stack trace, "broken", "throwing", "crash") →
  `debug-mantra`. Not `ecc:silent-failure-hunter` unless explicitly typed.
- **Review / audit / second opinion** → `scrutinize`. Not `ecc:code-review`,
  `ecc:review-pr`, or `review` on auto.
- **Diagram / ผัง / schematic as a deliverable** (architecture, flow, sequence,
  swimlane, kanban, timeline, org chart …) → `diagram-design` (external skill,
  ADR 0023). `artifact-diagramming` only for a figure inside an Artifact page you
  are already building; never Mermaid for a shipped visual.
- **Bug RCA / post-mortem** → `post-mortem`. `ecc:architecture-decision-records`
  is for ADRs (decisions), not bug writeups.
- **Planning big work** → `ecc:plan`. Skip `ecc:prp-plan` and `ecc:feature-dev`
  unless named.
- **Stack** → `ecc:python-review` may auto-fire on Python review; use the
  `ecc:typescript-reviewer` agent for TS/Next; `ecc:postgres-patterns` is
  reference only.
- **Never auto** — ECC domain skills irrelevant to this stack: `ecc:kotlin-*`,
  `cpp-*`, `rust-*`, `go-*`, `swift-*`, `flutter-*`, `csharp-*`, `fsharp-*`,
  `perl-*`, `laravel-*`, `django-*`, `quarkus-*`, `springboot-*`, `nestjs-*`,
  `angular-*`, `nuxt4-*`, `dotnet-*`, `scientific-*`, `healthcare-*`,
  `logistics-*`, `inventory-*`, `network-*`, `cisco-*`, `homelab-*`, `defi-*`,
  `evm-*`. Explicit slash only.
- **Only when asked for that kind of work** — `hyperframes*`, `gsap`,
  `video-use`, `remotion-to-hyperframes`, `website-to-hyperframes`, `paperclip*`,
  `para-memory-files`.

If two skills both match, prefer the one named above. If none match, reason
plainly rather than guessing at an `ecc:*` whose name merely sounds close.

## What belongs in this file

Only what is true and needed in **every** session regardless of task. Anything
task-specific belongs in a skill, which loads on demand — this file is paid for
on every turn, a skill body is not.

## Compact instructions (CEO 2026-09-25, task-9f6fec26)

When `/compact` (or auto-compact) summarizes this session, KEEP:
session charter / entry problem + its Definition of Done; every task-id
mentioned with its current status and branch; file paths already touched;
open questions still waiting on the CEO; the last CTO-FEEDBACK verbatim;
any number already measured (cost, tokens, latency, counts) — never
re-measure something already captured. DROP: raw tool output (file
contents, command stdout, search results) once its finding is already
acted on or recorded above — keep the conclusion, not the transcript.
