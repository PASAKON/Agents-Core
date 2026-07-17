---
name: fb-caption
description: |
  Produce a Facebook post caption following the MoonieX fixed skeleton.
  Every FB caption must use the standard structure (hook → value → CTA →
  disclaimer → hashtag block). Use when the brief says "FB caption",
  "Facebook post", "โพสต์ FB", or "caption".
triggers:
  - "FB caption"
  - "Facebook post"
  - "โพสต์ FB"
  - "caption"
  - "facebook caption"
acceptance:
  - Follows fixed skeleton: hook line → value/body lines → CTA line → disclaimer → hashtag block
  - CTA line contains LINE ID: @mooniebox
  - Hashtag block uses base set: #MoonieX + topic tags (max 5 total)
  - No emoji mid-sentence (one trailing 🙏 on CTA line is the only exception)
  - Disclaimer present when content involves financial claims
  - No crude Thai pronouns (มึง / กู)
---

# FB Caption Skill

Produce a Facebook post caption using the MoonieX standard skeleton.

## Fixed skeleton

```
<hook line — attention-grabbing, ≤10 words>
<body — 2-3 lines of value/proof/offer>
<CTA — ทักแชท LINE: @mooniebox 🙏>

<disclaimer if financial claims>
<hashtag block — #MoonieX + up to 4 topic tags>
```

## Rules

1. **One trailing emoji only** — 🙏 on the CTA line. No mid-sentence emoji.
2. **Casual Thai, no crudeness** — ครับ/ค่ะ OK, มึง/กู banned.
3. **Number format** — English digits for figures ($15, 80%, 1,000).
4. **Hashtag base** — always start with `#MoonieX`. Max 5 tags total.
5. **Disclaimer required** when mentioning rebates, returns, or earnings.

## Workflow

1. Read the brief for topic and target broker (if applicable).
2. Draft following skeleton above.
3. Count: hook ≤10 words? body 2-3 lines? CTA has LINE ID? disclaimer?
4. Verify no mid-sentence emoji, no crude pronouns.

## Output contract

Plain text, 5-8 lines total (including blank line before hashtags).
