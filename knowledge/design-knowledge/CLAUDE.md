# `design-knowledge/` — web_designer knowledge bank

The execution side: the design system in use, craft rules that decide whether
an artifact is good, and per-format playbooks. Symlinked into `web_designer`
worktrees together with `brand-knowledge/`.

**The split:** the CMO decides *what the brand means and which theme is being
held*; this bank decides *how to build it well*. Where the two touch the same
pixel, `brand-knowledge/brands/<brand>/BRAND.md` wins.

## Read order (workers MUST follow on every task)

1. **`../brand-knowledge/brands/<brand>/BRAND.md`** — first, always. Palette,
   lockups, and any must-pass checklist are gates, not suggestions. For
   MoonieX that means the Poster Build Must-Pass Checklist before any render.
2. **`craft/`** — universal don'ts. Start at `craft/README.md`, then read the
   files your task touches. A rule here can reject the task before work
   starts. Thirteen sections, including `anti-ai-slop`, `color`, `typography`,
   `typography-hierarchy` (+ `-editorial`), `laws-of-ux`,
   `accessibility-baseline`, `form-validation`, `rtl-and-bidi`,
   `animation-discipline`, `state-coverage`.
3. **`design-templates/<shape>/`** — the artifact shape the task asks for.
   115 of them; the ones this org reaches for most:
   `trading-analysis-dashboard-template`, `dashboard`, `live-dashboard`,
   `finance-report`, `invoice`, `image-poster`, `magazine-poster`,
   `social-carousel`, `email-marketing`, `saas-landing`, `pricing-page`,
   `waitlist-page`, `blog-post`, `docs-page`, `mobile-app`,
   `mobile-onboarding`, `video-shortform`, and `wireframe-{annotated,
   greybox,mobile-flow,sketch}`.
4. **The MoonieX design system** — tokens, components, and the email / LINE
   Flex handoff specs. Lives in the `MoonieX-Design` repo (see below), not in
   this bank. Match existing tokens; do not invent a colour or spacing value
   when a token exists.

If several templates fit, take the most specific. They do not stack — one
task, one primary shape.

`craft/` and `design-templates/` are a **verbatim copy of upstream
open-design** — do not hand-edit them, the next refresh overwrites the change
and the upstream diff stops being readable. See `PROVENANCE.md` for the pinned
commit and the refresh procedure.

## Where the design system actually lives

The live system is **MoonieX Design System V6.1** in the `MoonieX-Design` repo
(`PASAKON/MoonieX-Design`, local `/Users/gob/Projects/mooniex-website-templete`)
under `current/` — design tokens, components, plus handoff specs for email,
LINE Flex, popups, guides, and the forex calendar.

That repo is the source of truth for tokens and components. `system/` here
holds the distilled read-order and anything that must travel into a worktree;
it does not fork the design system.

## Hard rules

1. **Brand gates beat craft preferences.** A prettier layout that misses a
   `BRAND.md` gate is a reject, not a trade-off.
2. **Match tokens, do not invent.** A new colour or spacing value needs a
   design-system change, not a one-off inside an artifact.
3. **Generate the scene, overlay the copy.** For brand-strict output, text is
   composited crisply on top; never let an image model render the headline.
4. **No em dash in public copy** (IRON-RULES §39) — including text baked into
   an artifact, not just prose.

## Status (2026-08-03)

Created when `assets/brand-refs/` moved into `brand-knowledge/brands/`, then
filled the same day from open-design v0.16.1: `craft/` (13 sections) and
`design-templates/` (115 shapes, ~38 MB).

Still outstanding from that day's audit, which found design knowledge spread
across nine places: the MoonieX design system itself stays in the
`MoonieX-Design` repo, `mooniex-claudesign` holds a fifth `BRAND.md`
(`design-templates/chatudo/`) plus the org's own two templates, and the ECC
plugin ships twelve overlapping design skills. Deciding which of those this
bank absorbs is separate work.

## See also

- `knowledge/brand-knowledge/` — brand truth, theme, and the CMO's brief
- `LLMs/playbooks/v4-ui-components.md`, `web-designer.md`
- `MoonieX-ClaudeSkills` → `mooniex-tool-builder` (frontend design + web tools)
- `roles/web_designer.md`
