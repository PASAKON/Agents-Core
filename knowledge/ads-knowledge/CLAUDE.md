# `ads-knowledge/` — ads_manager knowledge bank

Use this when producing paid-media work (Meta, Google, TikTok, etc.).
Shape mirrors `mooniex-claudesign/` (web_designer's bank).

## Read order (workers MUST follow on every task)

1. **`craft/`** — universal don'ts. Skim all files; specific rule may
   reject the task before any work starts.
2. **`campaigns/<brand>/CAMPAIGN.md`** — brand × channel objectives,
   audiences, KPIs, budget envelope. If file missing for the brand, ask
   CMO to create it before working.
3. **`skills/<format>/SKILL.md`** — the artifact shape your task asks for
   (e.g., `meta-feed-static`, `click-to-messenger`). Read the SKILL +
   open the `example.*` next to it.

If multiple skills apply, pick the most specific. Skills do not stack —
one task = one primary skill.

## How CTO/CMO use this bank (C-level access)

- **Authoring task brief:** CMO `cat campaigns/<brand>/CAMPAIGN.md` to
  copy KPI + budget facts into the task description.
- **Reviewing DEV report:** Cross-check the artifact against the
  matching `SKILL.md` acceptance list + `craft/anti-ads-slop.md`.
- **Updating brand strategy:** CMO writes `campaigns/<brand>/CAMPAIGN.md`
  (no CTO involvement). Treat that file as source of truth — when wiki
  ADRs and CAMPAIGN.md disagree, CAMPAIGN.md wins for execution.

## Hard rules

1. **No skill, no work.** If no `skills/<format>/SKILL.md` matches the
   request, stop and ask CMO to create one (or pick a closer skill).
2. **No campaign, no spend.** If `campaigns/<brand>/CAMPAIGN.md` is
   missing or stale (>30 days unmaintained), do not commit budget.
3. **Craft is final.** `craft/anti-ads-slop.md` rules are auto-reject.
   No exceptions for "the brief said so."
4. **No image-gen API for brand-strict output** (mirror
   `claudesign/craft/anti-ai-slop.md` rule). Use manual composition.

## See also

- `LLMs/playbooks/knowledge-structure.md`
- `LLMs/playbooks/cfo-spend-approval.md`
- `roles/ads_manager.md`
