# `brand-knowledge/` — CMO knowledge bank

The brand side of the house: what a brand means, who it talks to, what theme
is currently being held, and what the designer is being asked to make.
Symlinked into `cmo` worktrees, and into `web_designer` worktrees alongside
`design-knowledge/` so the theme travels with the execution.

**Ownership: the CMO writes this bank. The designer reads it and does not
redefine it.** A designer who thinks a `BRAND.md` rule is wrong raises it with
the CMO; it does not get quietly overridden inside an artifact.

## Read order (workers MUST follow on every task)

1. **`brands/<brand>/BRAND.md`** — the brand truth: palette, typography, logo
   lockups, layout cues, and any must-pass checklist. Locked values are
   locked; do not recompute or "improve" them. If the brand has no
   `BRAND.md`, stop and ask the CMO to write one before producing anything
   customer-facing.
2. **`brands/<brand>/images/`** — what shipped before. Match the established
   look rather than inventing a new one per task.
3. **`brands/<brand>/PLAYBOOK.md`** — where present, the brand's own
   execution notes (currently only `brandprompt-th`).

## Brands in this bank

| Brand | `BRAND.md` | Notes |
|---|---|---|
| `mooniex` | ✅ | Palette LOCKED. Carries the **Poster Build Must-Pass Checklist** (CEO rejects, 2026-06-16) — hard-fail gates, run before every render. |
| `tradonix` | ✅ | Dark + orange/copper/gold, XM co-brand, theme "ต้นทุน". |
| `axi` | ✅ | Broker co-brand. |
| `brandprompt-th` | ✅ | Also has `PLAYBOOK.md`, `templates/`, `ads/`, `social/`, and a competitor teardown. |
| `mooniex-indicators` | ❌ | Images only — **gap**, needs a `BRAND.md`. |
| `mooniex-rebate-posters` | ❌ | Images only — **gap**, needs a `BRAND.md`. |
| `khaihet` | ✅ | ไขเหตุ: AI news-reconstruction FB Page (CEO 2026-10-17). Teal/ink/amber LOCKED; "ภาพจำลอง" tag on every AI frame. |
| `mistergraph` | ✅ | Mr. Graph: the CEO's TikTok, free TradingView indicator lessons (CMO 2026-10-26). Orange/peach/slate LOCKED; no broker card; education only. |
| `ilag` | ✅ | ละครสั้นคุณธรรม by ILAG Studio (FB). Gold/white/black LOCKED (CEO 2026-10-26, replaces navy/gold of 2026-09-28); the Page's own logo, never redrawn; channel kit v2 PROPOSED (20 tiles, `templates/`), locks tile by tile on the CEO's answer. |
| `linkreed` | ✅ | New product (not Mooniex). AI link-in-bio builder. Warm ink/watercolor editorial mood, minimal mobile-first product UI. Palette LOCKED. |
| `jade-tally` | ✅ | Jade Tally (@JadeTally): the CEO's YouTube channel for ลูกคิดประเมินฟ้า (PH CnDrama #351). One channel, Thai main audio, English as an added track (CEO 2026-10-27). No text burned into an episode; hook-first titles. |

## Hard rules

1. **No `BRAND.md`, no customer-facing artifact.** Two brands above are
   image-only; treat a task against them as blocked until the CMO writes one.
2. **Locked is locked.** Palette and rebate figures marked LOCKED in a
   `BRAND.md` are decisions, not defaults. Never re-derive them from a
   database or a screenshot.
3. **No em dash in public copy** — posts, web, ads, any user-facing text
   (IRON-RULES §39). Internal docs are exempt.
   No `« »` in any Thai text, internal or public (CEO 2026-10-26): straight quotes "..." or none.
4. **Brand truth lives here, not in the artifact repo.** A brand rule
   discovered while building something gets written back into
   `brands/<brand>/BRAND.md`, not left as a comment in a script.
5. **The live logo wins.** Before any logo, emblem or mark work, open the
   brand's live mark: the site's asset, or the Page's profile picture for a
   brand that lives on a social Page. Use it as it is; never redraw one that
   exists (CEO 2026-10-26: "ILAG เรามี Logo อยู่แลวนะ ไม่ต้องทำใหม่", after kit
   v1 drew a new emblem).
6. **An asset over 1 MB stays out of git** (media_guard pre-commit, ADR 0030).
   Commit its source under 1 MB plus the script that makes it, and write the
   step in the brand's `templates/REBUILD.md` (ILAG: `cut_logo.py` makes
   `logo.png` from `images/ilag-page-logo-1080.jpg`).

## Known fragmentation (2026-08-03 audit)

A fifth `BRAND.md` sits outside this bank at
`mooniex-claudesign/design-templates/chatudo/BRAND.md`. It has not been pulled
in — decide whether Chatudo is an org brand before moving it.

## See also

- `knowledge/design-knowledge/` — the execution side (system, craft, skills)
- `LLMs/playbooks/brand-truth.md`, `mooniex-voice-guide.md`,
  `mooniex-fb-caption-style.md`, `mooniex-quote-poster.md`
- `roles/cmo.md`, `roles/web_designer.md`
