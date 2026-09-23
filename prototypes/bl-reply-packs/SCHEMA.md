# BL reply-pack schema

One YAML file per BLACK LIQUIDITY episode, named `EP<NN>.yaml`. It is the
single source of truth a comment/DM-reply bot reads to answer viewers
correctly for that episode — what the clip said, how solid each claim is,
where the CTA leads, and what to actually send. Built per CEO brief
2026-09-23 (EP54/EP55 shipped with no such pack; a viewer who commented the
CTA keyword got no reply). The engine that reads this format is a separate
`developer` task (see `prototypes/bl-reply-bot/`) — this schema is the
contract between the two.

Compliance for every field below is governed by
`.claude/skills/blackliquidity-script/SKILL.md` §Compliance — no broker
recommendation, no account/affiliate link, no rebate mention, no mention of
MoonieX or any IB. This is not a style note; it is the reason `never_say`
exists as a field a bot can check its own draft replies against.

```yaml
episode: EP55                # episode id, matches the pack's own filename
title: ชื่อดังไม่ได้แปลว่ามีใบอนุญาต   # episode title, for the bot to confirm it has the right pack
video_id: null                # TikTok video id, filled in after the clip is posted (unknown at write time)

summary:                      # 3 short lines — what the bot tells a viewer who asks "what was this episode about"
  - ...
  - ...
  - ...

claims:                       # every factual claim in the script that names a number, a person, or an outside source
  - text: ...                 # the claim itself, plain Thai, as a viewer would ask about it
    source: <url>              # where it came from; null only for a claim with no external source (channel's own reasoning)
    status: verified | attributed | opinion
      # verified   = independently checked by us against the primary source, holds up as fact
      # attributed = we are relaying someone else's claim/rating and saying whose it is ("WikiFX says…") — not our own verified fact
      # opinion    = the channel's own analysis or framing, not a checkable fact
    valid_until: 2026-10-23     # date after which this claim should be re-checked before the bot keeps citing it — ratings/scores/complaint counts go stale; use null for a claim that cannot go stale (e.g. a historical figure or a mechanic that doesn't change)

cta:
  keyword: เช็กก่อนฝาก          # the exact word the episode told viewers to comment
  variants: [เช็คก่อนฝาก, เช็กโบรก, เช็คโบรค, ...]
    # misspellings and near-matches real viewers actually type — the bot must match
    # against this list, not just the exact keyword string (EP54's "เช็คโบรค" comment
    # went unanswered specifically because nothing matched the literal CTA word)
  deliverable:
    title: ...                 # human-readable name of what gets sent
    text_file: EP55-regulator-sites.md   # path (relative to this pack) to the Thai-text deliverable
    image: EP55-card.png       # path (relative to this pack) to the 1080x1350 card image
  dm_message: ...              # the message text sent in the DM together with the deliverable
  comment_reply_dm_sent: "ขออนุญาตส่งข้อความให้ทาง Inbox นะครับ"
    # CEO's exact words — used as the public comment reply when the bot CAN
    # DM the commenter directly. Do not paraphrase; this is deliberately the
    # only line shown in public before the content is delivered via DM.
  comment_reply_dm_invite: ...
    # used instead of the line above when the bot CANNOT message the
    # commenter directly (TikTok requires the viewer to DM first — see
    # prototypes/bl-reply-bot/RESEARCH.md Q3a) — asks them to DM us the
    # keyword themselves so the conversation becomes viewer-initiated and
    # the bot can then legally reply

faq:                           # questions this episode will attract, with an answer already approved for the bot to use verbatim
  - q: ...
    a: ...

never_say: [...]               # phrases the bot must never produce in a draft reply for this episode — compliance list, see SKILL.md §Words for the base set; add episode-specific ones here (e.g. a broker name that appears in a claim but must never be recommended)

escalate_to_human: [...]       # situations the bot must hand to a human instead of auto-replying: a legal threat from a broker, a victim asking for money back, a request for personalized investment advice, anything not covered by faq
```

## Standing rule: no em dash in anything a viewer receives

IRON-RULES §39 bans the em dash (—) in public-facing text. Every field a
viewer can actually see or read — `summary`, `claims[].text`, everything
under `cta` (including `dm_message`, `comment_reply_dm_sent`,
`comment_reply_dm_invite`), `faq[].a`, and the two deliverable files a pack
points to — must use normal Thai punctuation instead: a line break, a colon,
or just a space where Thai would pause. `—` must also be in every pack's
`never_say`, so the bot's own compliance guard blocks a future draft that
carries one. This file (SCHEMA.md) is internal-only and may keep dashes.

## Field notes for the bot implementer

- `claims[].status` is the field the bot uses to hedge its own language: a
  `verified` claim can be stated flatly, an `attributed` claim must be
  phrased as "[source] says…", an `opinion` claim must be phrased as the
  channel's own view, never as established fact.
- `claims[].valid_until` in the past means the bot should not repeat that
  number/rating without a fresh check — flag it for a human instead of
  citing a stale score.
- `cta.variants` is not exhaustive by design — treat it as a seed list the
  bot's matcher should fuzzy-match against, not a closed set.
- `never_say` and `escalate_to_human` are the compliance guardrails the bot
  checks *before* sending, not after — a draft that trips either must be
  rewritten or routed to a human, never sent as-is.
