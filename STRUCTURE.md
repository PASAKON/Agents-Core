# MoonieX Repository Structure

This document defines what belongs in this repository and, just as importantly,
what does not. It is an additive safety boundary for the current repository; it
does not move existing production files.

## One repository, one responsibility

This repository is the **MoonieX Agent control plane**: orchestration, adapters,
policies, shared configuration templates, operational scripts, and tests.

Personal knowledge, customer work, media projects, credentials, and live runtime
state have different owners and retention rules. They should not share the
control-plane Git history.

## Recommended workspace layout

The directories below are siblings. Only `mooniex-agents` is this Git repository.

```text
MoonieX/
├── mooniex-agents/       # shared control-plane source (this repository)
├── mooniex-private/      # private knowledge/config; private repository or vault
├── projects/             # one repository or directory per user project
│   ├── project-a/
│   └── project-b/
├── runtime/              # databases, logs, queues, locks, sessions; not Git
└── worktrees/            # disposable task worktrees; not Git
```

The same logical layout can be used on macOS, Windows, Contabo, or worker nodes.
Absolute paths belong in machine-local configuration, never in shared source.

## Repository zones

| Zone | Purpose | Examples | Rule |
|---|---|---|---|
| Core source | Product behavior | `lib/`, `runners/`, `tools/` | Reviewed and tested |
| Shared configuration | Safe defaults and policy | `config/`, `policies/`, `roles/` | No secrets or personal paths |
| Operations | Install, launch, migration and diagnostics | `scripts/`, `windows/` | Must be repeatable |
| Documentation | Architecture and operating guides | `docs/` | Shared facts only |
| Tests | Automated verification | `tests/` | Must not touch live state |
| Runtime state | Ephemeral machine/session data | `state/`, generated `output/` | Move outside Git over time |
| Personal/project content | User knowledge and deliverables | current `data/`, `research/`, project TSVs | Move to sibling private/project roots |
| Legacy mixed | Existing content that crosses boundaries | see manifest | Do not add more; migrate deliberately |

The authoritative machine-readable classification is
[`config/repository-boundaries.yaml`](config/repository-boundaries.yaml).

## Source migration target

The current imports are intentionally left untouched. After the CTO approves a
migration plan, source can be moved in small compatibility-preserving phases:

```text
src/mooniex/
├── core/                 # domain models, task/session lifecycle
├── orchestration/        # delegation, scheduling, routing
├── adapters/             # Claude, Codex, MCP, terminal and provider bridges
├── node/                 # worker-node and remote execution contracts
└── policy/               # authorization and capability checks
```

This target keeps MoonieX as the connector/control plane. It does not duplicate
the full feature set of the external agent applications it connects to.

## Separation rules

1. Shared source may reference project roots through IDs and interfaces, not
   hard-coded personal paths.
2. Secrets live in environment variables or a secret store; example files contain
   placeholders only.
3. Runtime databases, logs, locks, session files, generated media, and worktrees
   are disposable from the source repository's perspective.
4. A project owns its prompts, assets, research, knowledge and deliverables unless
   they are intentionally promoted into reusable MoonieX product material.
5. Private knowledge must never be required to run the shared test suite.
6. Every new top-level path must be classified before it is committed.

## Migration order

1. Enforce classification without moving files (this branch).
2. Make paths configurable and remove hard-coded machine paths.
3. Move runtime state outside the checkout with backward-compatible fallbacks.
4. Extract personal and project content into sibling roots.
5. Move Python modules under `src/mooniex/` in isolated, tested batches.

Items marked `legacy_mixed` are acknowledged debt, not approved destinations for
new content. Run `python scripts/check_repo_boundaries.py` to check the boundary.
