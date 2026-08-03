# Provenance — where `craft/` and `design-templates/` came from

Both directories are a **verbatim copy** from the open-design project. They are
not authored here and should not be hand-edited: a local edit is silently lost
on the next refresh, and worse, it makes the diff below useless for seeing what
upstream actually changed.

| | |
|---|---|
| Upstream | `https://github.com/nexu-io/open-design` |
| Copied from | `upstream/main` @ `e1c277c5` |
| Upstream version | **0.16.1** |
| Copied on | 2026-08-03 |
| Contents | `craft/` 13 files · `design-templates/` 115 templates (~38 MB) |

The SHA is also in `.upstream-sha` so a script can read it.

## Why a copy and not a submodule

The org fork lives at `/Users/gob/Projects/mooniex-claudesign`
(`PASAKON/mooniex-claudesign`), forked 2026-05-05 and **2,790 commits behind**
upstream at the time of this copy (fork is v0.4.0, upstream v0.16.1). Closing
that gap means taking twelve minor versions of `apps/` plus a full dependency
bump — a project of its own.

This bank needs the *knowledge*, not the engine. Copying `craft/` and
`design-templates/` gives the designer everything useful today at near-zero
risk and leaves the fork rebase as separate work.

## Refreshing

```bash
cd /Users/gob/Projects/mooniex-claudesign
git fetch upstream

# what changed since the copy
git diff --stat "$(cat /Users/gob/Projects/Agents/knowledge/design-knowledge/.upstream-sha)" \
  upstream/main -- craft design-templates

# take the new state
git archive upstream/main craft design-templates \
  | tar -x -C /Users/gob/Projects/Agents/knowledge/design-knowledge
git rev-parse upstream/main \
  > /Users/gob/Projects/Agents/knowledge/design-knowledge/.upstream-sha
```

Then update the table above. Upstream moves fast — 425 commits in the 30 days
before this copy, 376 contributors in 90 days — so expect real change between
refreshes.

## State at copy time

Upstream had not touched `anti-ai-slop.md`, `color.md`, `typography.md`,
`animation-discipline.md` or `state-coverage.md` since the 2026-05-05 fork;
those five were already current. Everything else in `craft/` is new since then:

- `laws-of-ux.md` — 18+ UX laws, each cited to its original paper
- `accessibility-baseline.md` — WCAG mapped to the actual legal floor per
  jurisdiction (EU EAA, ADA Title II/III, Section 508, ISO/IEC 40500:2025);
  working target is WCAG 2.2 AA
- `form-validation.md` — input state machine, validation timing, the
  Constraint Validation API, Baymard findings, WCAG 3.3.x
- `typography-hierarchy.md` / `-editorial.md` — hierarchy vectors, the flat vs
  noise failure modes, editorial rhythm
- `rtl-and-bidi.md` — logical properties, `<bdi>`, what mirrors and what does
  not. Still relevant to Thai work although Thai is LTR: the logical-property
  discipline is what keeps mixed Thai / English / numeral runs sane.
- `FUTURE_SECTIONS.md` — planned slugs (`motion-discipline`,
  `pixel-discipline`, `typographic-rhythm`), not yet written

## Worth stealing later

Upstream's `craft/README.md` documents a four-axis split — `craft/` (rules),
`skills/` (capabilities), `design-templates/` (artifact shapes),
`design-systems/` (brand packages) — enforced by a `pnpm lint:craft` guard: a
skill declaring `od.craft.requires: [typography, typography-hierarchy]` fails
the build when a slug does not resolve to a real file. That guard is the direct
answer to design knowledge drifting apart, which is the problem this bank was
created to fix.
