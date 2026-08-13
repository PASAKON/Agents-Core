---
name: rebate-copy
description: |
  Produce cashback/rebate marketing copy for MoonieX — short-form text
  (FB caption, LINE broadcast, landing hero) that communicates per-lot
  rebate amounts with zero ambiguity. Use when the brief asks for
  "rebate copy", "cashback copy", "คืนเงิน", "รีเบท", or "per-lot".
triggers:
  - "rebate"
  - "cashback"
  - "คืนเงิน"
  - "รีเบท"
  - "per-lot"
  - "คืนต้นทุน"
acceptance:
  - States exact $/lot figure (XM $15/lot, Exness $8/lot) — never a percentage
  - Named source for the figure: "XM IB programme" or "Exness IB programme"
  - Disclaimer present: "รีเบทขึ้นกับปริมาณการเทรดจริง" or equivalent
  - LINE CTA line matches FB caption standard (LINE ID: @mooniebox)
  - No percentage-based rebate claim anywhere in the copy
  - No "unlimited" or "infinite" rebate language
---

# Rebate Copy Skill

Produce short-form rebate/cashback copy for MoonieX brokers.

## Key facts (LOCKED — do not recompute from DB)

**Canonical source (JSON pilot, 2026-07-18): `facts.json` in this directory.**
Read it first — every $/lot figure, disclaimer string, and forbidden-claim
in the copy must trace back to that file verbatim, not be re-typed from
memory or paraphrased. The table below is the human-readable mirror of
the same data, kept for quick reference only.

| Broker | Rate | Basis | Note |
|--------|------|-------|------|
| XM | $15/lot | Gold-standard lot | 80% IB share to user |
| Exness | $8/lot | Gold-based + 80% share | Per closed standard lot |

These numbers are fixed. **Never** derive them from database max values
(BTC inflates them). See wiki ADR for source.

## Workflow

0. **Read `facts.json`** in this directory. Pull broker rates, the
   disclaimer text, and `forbidden_claims` from it — do not recompute or
   restate from memory. If `facts.json` and the table above ever disagree,
   `facts.json` wins (it's the canonical, machine-checkable copy).
1. **Read the brand voice** from `voices/mooniex/VOICE.md` (if present;
   otherwise use defaults: casual Thai, no crude pronouns, one trailing 🙏).
2. **Pick the format** from the brief:
   - FB caption → follow FB caption standard (fixed skeleton: hook →
     value → CTA → disclaimer → hashtag block)
   - LINE broadcast → shorter, punchier, LINE CTA
   - Landing hero → single headline + subhead, no hashtags
3. **Write the copy** following these rules:
   - Lead with the per-lot dollar figure, not a percentage
   - One claim per sentence; no stacking "earn X AND save Y"
   - Thai body text, English numbers ($15, $8)
4. **Self-check** against acceptance list above.

## Output contract

Plain text (no HTML). Length:
- FB caption: 3–5 lines + hashtag block
- LINE broadcast: 2–3 lines
- Landing hero: headline (≤8 words) + subhead (≤15 words)
