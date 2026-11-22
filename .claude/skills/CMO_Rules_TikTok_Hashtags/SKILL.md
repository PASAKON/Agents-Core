---
name: CMO_Rules_TikTok_Hashtags
kind: rules
description: 'RULES — Mandatory 5-hashtag rule for every TikTok clip, script, and client brief: max 5 #tags, Slot #1 is always our channel/brand tag (#MYPASAKON, #BLACKLIQUIDITY), and Slots #2-#5 are viral search-matched keywords for that clip''s real topic. Trigger on /CMO_Rules_TikTok_Hashtags, "Tag ใน Tiktok", "ติดแท็ก TikTok", "5 แท็ก".'
owner: CMO
audience: [cmo, content_strategist, script_writer, video_editor, developer]
created_by: agent
author: {role: project_head, date: "2026-11-23"}
improved_by: []
aka: []
---

# TikTok 5-Hashtag Rule (`1 Brand + 4 Viral Search-Matched Tags`)

Binds every session, script writer, editor, and automated poster across all MoonieX TikTok channels (`MYPASAKON` `@mypasakon`, `BLACK LIQUIDITY` `@black_liquidity`, `TRADER UNCUT`, `ILAG`, `KhaoHom`) whenever writing `[Tags]` in a Google Doc `Script`, sending a `Topic / Tags / Script` block to a client/broker for approval, or preparing a `desc.txt` caption for `CMO_Procedure_MoonieXPoster_Queue` (`tools/mooniex_poster.py`). Established by CEO ruling on 2026-11-23.

## When to invoke / when NOT to

- **Invoke** before writing or reviewing the `Tags:` / `#hashtag` line of any TikTok video, Google Doc `Script`, broker/sponsor handoff message, or `MoonieX Poster` description file.
- **Do NOT invoke** for YouTube long-form metadata or multi-language A/B titles (`CMO_Rules_YouTube_MultiLangAB`).
- **Refusal precondition:** Refuse to send or queue any TikTok script or caption that carries more than 5 `#tags`, omits the channel's brand tag in Slot `#1`, or pads slots with generic filler tags (`#fyp`, `#foryou`, `#viral`) unrelated to what viewers actually type into TikTok Search.

## Rules

1. **HARD — Maximum 5 `#tags` per TikTok post or script (`1 + 4 = 5`), never 6 or more (CEO ruling 2026-11-23).**
   TikTok caps effective hashtag indexing at 5 tags per post (`tools/mooniex_poster.py` also enforces `<= 5`). Even when a sponsor/broker brief lists 5–10 campaign hashtags on its brief sheet, distill the final `Tags:` line to **at most 5 `#tags`** — never dump 8–10 tags onto a TikTok script or caption.
   **Why hard:** scope & platform mechanics — CEO ruling 2026-11-23 (*"Tiktok ใส่ Tag ได้สูงสุดแค่ 5 เท่านั้น #MYPASAKON ต้องมี และอีก 4 เอาที่ Viral และสอดคล้องกับเนื้อหาจริงเมื่อคนค้นหาต้องเจอเรา"*); exceeding 5 tags breaks TikTok's limit and triggers hard rejection in `MoonieX Poster`.

2. **HARD — Slot `#1` is ALWAYS our own Channel / Brand tag (CEO ruling 2026-11-23).**
   The very first hashtag in every `Tags:` line and caption must be the publishing channel's canonical brand tag:
   - `MYPASAKON` (`@mypasakon`) → `#MYPASAKON`
   - `BLACK LIQUIDITY` (`@black_liquidity`) → `#BLACKLIQUIDITY` (or `#blackliquidity` per channel preset)
   - `TRADER UNCUT` → `#TRADERUNCUT`
   - `ILAG` → `#ILAG`
   **Why hard:** scope — CEO ruling 2026-11-23 (*"เขาใช้แค่ 5 แท็ก แรกจะต้องเป็น แบรนด์ หรือ ชื่อช่องเรา อีก 4 ตามที่ฉันบอก"*); every post builds searchable brand equity for our channel first.

3. **HARD — Slots `#2`–`#5` (the remaining 4 tags) must be high-volume Viral + Search-Intent keywords that match the clip's exact topic so real searchers find our video (CEO ruling 2026-11-23).**
   - Pick words a Thai viewer actually types into the TikTok search bar when looking for that exact problem, news event, or technique (e.g. `#ราคาทองคำ`, `#XAUUSD`, `#เทรดทอง`, `#เทคนิคเทรดทอง`, `#จิตวิทยาการเทรด`, `#เตือนภัยลงทุน`).
   - Never waste one of the 4 slots on empty generic tags (`#fyp`, `#foryoupage`, `#viral`, `#tiktokuni`) that carry zero topic search intent.
   - **Sponsored / Broker Clips:** Keep Slot `#1` as `#MYPASAKON` (our channel), allocate 3 slots (`#2`–`#4`) to high-search viral keywords matching the episode's real hook/topic, and place the primary client brand tag (`#<ClientBrand>`, e.g. `#Bitunix`) in Slot `#5` so both organic topic searchers and brand-review searchers land on our clip without exceeding the 5-tag ceiling.
   **Why hard:** scope — CEO ruling 2026-11-23 (*"อีก 4 เอาที่ Viral และสอดคล้องกับเนื้อหาจริงเมื่อคนค้นหาต้องเจอเรา"*).

4. **HARD — Client/Broker Telegram handoffs carry ONLY the pure copy-ready block, with zero surrounding commentary (CEO ruling 2026-11-23).**
   When sending `Topic / Tags / Script` blocks to the CEO's Telegram (`lib.telegram_out.send_to_ceo`) for forwarding to a client or broker, send **1 separate Telegram message per video** in this exact 4-line pattern and **no other header, numbering, or greeting**:
   ```text
   Topic: {Name}
   Tags: #{ChannelBrand} #{ViralSearch1} #{ViralSearch2} #{ViralSearch3} #{ViralSearch4_or_Client}

   Script: {Link google drive share}
   ```
   **Why hard:** scope & operator speed — CEO ruling 2026-11-23 (*"ส่งมาใน Telegram นะ ทั้งหมด 4 ข้อความให้ Copy ได้ง่าย และห้ามมีข้อความอื่นนอกจากที่ต้องใช้จริงๆ"*).

## Quick verification check

Run before sending any `Tags:` line to Telegram, a Google Doc `Script`, or `tools/mooniex_poster.py`:
```python
tags = tags_line.strip().split()
assert 1 <= len(tags) <= 5 and all(t.startswith("#") for t in tags), f"Expected <=5 #tags, got {tags}"
assert tags[0].upper() in {"#MYPASAKON", "#BLACKLIQUIDITY", "#TRADERUNCUT", "#ILAG"}, f"Slot #1 must be channel brand: {tags[0]}"
assert not any(t.lower() in {"#fyp", "#foryou", "#foryoupage", "#viral"} for t in tags), f"No generic filler tags: {tags}"
```

## Good vs bad (real examples from Bitunix × MYPASAKON, 2026-11-23)

- **Good (5 tags = `#MYPASAKON` first + 3 high-intent topic search tags + `#Bitunix`):**
  - Topic: *เมื่อหุ้นสหรัฐร่วงหนัก ทำไมทองคำถึงโดนทุบตาม? ความลับเรื่องสภาพคล่องที่รายย่อยต้องรู้*
    `Tags: #MYPASAKON #ราคาทองคำ #XAUUSD #ข่าวเศรษฐกิจ #Bitunix`
  - Topic: *2 ความพลาดบนมือถือ ที่ทำนักเทรดทองขายหมูและเสียจุดเข้าสวยๆ ทุกสัปดาห์*
    `Tags: #MYPASAKON #เทคนิคเทรดทอง #สอนเทรดมือใหม่ #นักเทรด #Bitunix`
- **Bad (9 tags copied straight off a client brief, channel tag buried at the end):**
  - `Tags: #Bitunix #BitunixThailand #BitunixTH #BetterLiquidityBetterTrading #BeyondTraditionalTrading #ราคาทองคำ #XAUUSD #Forex #mypasakon` *(9 tags -> violates the 5-tag cap, wastes 4 slots on unsearched slogan tags, and puts `#mypasakon` last instead of `#1`).*

## When the CEO changes a rule

- **2026-11-23 (CEO, MYPASAKON × Bitunix session `5e00df47`):** *"เพิ่มเติมหน่อย Tiktok ใส่ Tag ได้สูงสุดแค่ 5 เท่านั้น #MYPASAKON ต้องมี และอีก 4 เอาที่ Viral และสอดคล้องกับเนื้อหาจริงเมื่อคนค้นหาต้องเจอเรา เขียนเป็น Skill สำหรับให้หน่อยเรื่อง Tag ใน Tiktok เขาใช้แค่ 5 แท็ก แรกจะต้องเป็น แบรนด์ หรือ ชื่อช่องเรา อีก 4 ตามที่ฉันบอก"*

## Field notes
