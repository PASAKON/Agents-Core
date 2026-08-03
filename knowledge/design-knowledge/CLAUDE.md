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
2. **`craft/`** — universal don'ts. Skim all files; a rule here can reject the
   task before work starts.
3. **`system/`** — the design system actually in use: tokens, components,
   spacing, email and LINE Flex templates. Match existing tokens; do not
   invent a colour or spacing value when a token exists.
4. **`skills/<format>/SKILL.md`** — the artifact shape the task asks for
   (poster, fb-ad, thumbnail, landing). Read the SKILL plus the `example.*`
   beside it.

If several skills apply, take the most specific. Skills do not stack — one
task, one primary skill.

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

Created when `assets/brand-refs/` moved into `brand-knowledge/brands/`.
`craft/`, `system/` and `skills/` are **not yet populated**. The audit that day
found design knowledge spread across nine places — this repo, the design-system
repo, `mooniex-claudesign`, two skill scopes, the ECC plugin, and four wiki
playbooks. Consolidating them is separate work; until it lands, a designer
still has to reach for the wiki playbooks below.

## See also

- `knowledge/brand-knowledge/` — brand truth, theme, and the CMO's brief
- `LLMs/playbooks/v4-ui-components.md`, `web-designer.md`
- `MoonieX-ClaudeSkills` → `mooniex-tool-builder` (frontend design + web tools)
- `roles/web_designer.md`
