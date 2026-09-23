# Template index — job → shape

`design-templates/` holds 115 shapes copied from open-design. All of them are
kept; most of them this org will never open. This page is the shortcut: find
the row matching the task, open that one `SKILL.md`, ignore the rest.

Lives here rather than inside `design-templates/` on purpose — that directory
is a verbatim upstream copy and a refresh overwrites anything added to it (see
`PROVENANCE.md`).

Every template is `SKILL.md` (how to build the shape) plus `example.html` (a
working reference). Read both. Brand gates in
`../brand-knowledge/brands/<brand>/BRAND.md` still come first, always.

## The work this org actually does

| Task | Template |
|---|---|
| Trading tool / calculator surface | `trading-analysis-dashboard-template`, `dashboard` |
| Admin or ops screen (`/admin/*`) | `dashboard`, `live-dashboard`, `github-dashboard` |
| CFO / finance surface | `finance-report`, `invoice` |
| Rebate or campaign poster | `image-poster`, `magazine-poster` |
| Facebook / LINE carousel post | `social-carousel` |
| Lifecycle or campaign email | `email-marketing` |
| Short vertical video | `video-shortform`, `motion-frames` |
| Landing page | `saas-landing`, `open-design-landing` |
| Pricing page | `pricing-page` |
| Waitlist / pre-launch capture | `waitlist-page` |
| Article or guide page | `blog-post`, `docs-page` |
| Product docs surface | `docs-page` |
| Mobile screens | `mobile-app`, `mobile-onboarding` |
| Broker / IB partner deck | `ib-pitch-book`, `html-ppt-pitch-deck` |
| Feature launch deck | `html-ppt-product-launch` |
| Internal weekly / status deck | `html-ppt-weekly-report`, `weekly-update` |
| Sketch before building | `wireframe-sketch` → `wireframe-greybox` → `wireframe-annotated` |
| Mobile flow map | `wireframe-mobile-flow` |
| Spec handed to a developer | `pm-spec` |
| Design review of existing work | `critique` |

**Start at a wireframe for anything non-trivial.** `wireframe-greybox` costs
minutes and settles layout arguments before a single colour decision gets
made — the same "cheap mockup before paid generation" rule the org already
applies to image work.

## Present but not for us

Kept because the copy stays verbatim and refreshes stay clean, not because
they are useful here:

- **~35 `html-ppt-zhangzara-*` plus `guizang-ppt`** — slide themes for the
  Chinese market, differing by styling only (`retro-windows`,
  `sakura-chroma`, `pink-script`, `8-bit-orbit`, …). Read one and you have
  read them all.
- **`orbit-*`** (`gmail`, `notion`, `linear`, `github`, `general`) — SaaS
  integration surfaces for products this org does not ship.
- **`clinical-case-report`, `dcf-valuation`, `hr-onboarding`, `dating-web`,
  `gamified-app`, `sprite-animation`, `webgl-experience`** — wrong domain.

If a task genuinely needs one of these, use it. The point of the list is that
scanning 115 directories should not be a step anyone has to perform.

## Keeping this honest

The index is hand-maintained; the template set is not. After a refresh
(`PROVENANCE.md`), check what appeared:

```bash
cd /Users/gob/MoonieXHQ/Agents/Core/knowledge/design-knowledge
ls design-templates | wc -l      # was 115 on 2026-08-03
```

A new shape matching real MoonieX work belongs in the table above.
