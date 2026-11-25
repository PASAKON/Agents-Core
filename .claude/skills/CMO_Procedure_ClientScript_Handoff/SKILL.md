---
name: CMO_Procedure_ClientScript_Handoff
kind: procedure
description: 'PROCEDURE — Write, revise, and file client/broker video scripts as shared Google Docs, sending 1 pure Topic/Tags/Script block per clip to Telegram and chat on EVERY draft and revision round. Trigger on /CMO_Procedure_ClientScript_Handoff, "ส่งงานลูกค้า", "สคริปต์ลูกค้า", "ส่งให้โบรกตรวจ", "อันนี้จากลูกค้า".'
owner: CMO
audience: [cmo, content_strategist, script_writer, developer]
created_by: agent
author: {role: project_head, date: "2026-11-25"}
improved_by: []
aka: []
---

# Client / Broker Sponsored Script Production, Revision & Pure Handoff

Input: Client/broker campaign brief (PDF/images/text) or client revision notes · Output: `N` shared Google Docs (`anyoneWithLink` = `reader`) inside canonical `ALL DRAFT/<CHANNEL>/<CLIENT> [1..N] | <Topic>/` Drive folders + **`N` separate pure copy-ready `Topic / Tags / Script` messages delivered to BOTH Telegram (`@SSomPongBot`) and chat on every single round** · Tools: `scripts/gdrive-bridge/ilag_sync.py`, `lib/telegram_out.py` (`send_to_ceo`).

## When to invoke / when NOT to

- **Invoke** whenever writing a batch of sponsored video scripts for a client/broker (`Bitunix`, `Exness`, `AXI`, `Eightcap`, `EBC`, etc.) OR whenever the CEO relays revision feedback from the client (`"อันนี้จากลูกค้า"`, `"ลูกค้าขอเพิ่ม..."`, `"ส่งให้โบรกตรวจ"`).
- **Do NOT invoke** for internal non-sponsored episodes (`CMO_Standard_BlackLiquidity_Script`, `CMO_Workflow_KhaoHomEpisode`) or post-render TikTok video queuing (`CMO_Procedure_MoonieXPoster_Queue`).

## Steps

1. **Audit Brief Compliance & Channel Voice DNA**
   - Extract all mandatory talking points, CTA lines, slogans, and **strictly forbidden words** from the client brief (e.g., if a CFD brief forbids crypto terms like `"แพลตฟอร์มคริปโต"` / `"กระดานเทรดคริปโต"`, enforce a hard regex check with `0` hits).
   - Research current viral news/posts matching the channel's real style (e.g., `@mypasakon` 10-year trader storytelling: `[Hook 0-6s]` -> `[Context / Viral Insight]` -> `[Value / Real Trader Math]` -> `[Bridge & Live Product Review Tie-in]` -> `[CTA + Mandatory Brand Closing + CFD Risk Disclaimer]`).
   - Run `CMO_Standard_HumanVoice_TH` checks (zero em-dashes `—`, zero `« »`, short spoken breath lines).
   - Apply `CMO_Rules_TikTok_Hashtags`: **maximum 5 `#tags`**, Slot `#1` = `#MYPASAKON` (or channel brand), Slots `#2`–`#4` = 3 viral search-matched topic keywords, Slot `#5` = `#<ClientBrand>`.
   - *Stop if* any forbidden client word, banned AI punctuation, or `>5` hashtags remain.

2. **Create Shared Google Docs & Request Drive Folder Approval (`CXO_Rules_GDrive_Filing`)**
   - On Round 1 (before folder names are approved under `CXO_Rules_GDrive_Filing` Rule 3): create the `N` Google Docs (`application/vnd.google-apps.document`) temporarily in `UNKNOWN` (`1PIha6ByPigaVZQG89qZI9uCGW_Lw6ePA`, Rule 5) and enable `{"role": "reader", "type": "anyone"}` permission so share links (`https://docs.google.com/document/d/<doc_id>/edit?usp=sharing`) work immediately.
   - Raise a CardRun v2 Question Card (`tools/ask_run.py ask --project "<CHANNEL>" --lane "cmo" ...`) proposing the `N` canonical folder paths:
     `ALL DRAFT/<CHANNEL>/<CLIENT> [1..N] | <Topic>/` (`Script`, `Audio/`, `AI Drafts/`, `Finals/`, `_MANIFEST.json`).
   - Once approved: create the `N` folders + 3 subfolders (`Audio/`, `AI Drafts/`, `Finals/`), move each Google Doc from `UNKNOWN` into its folder and rename it `Script` (**preserving the exact same `doc_id` and share URL**), upload MD5-verified `_MANIFEST.json`, and update `CXO_Knowledge_GDrive_FolderMap` (tree + ID table) in the same turn.

3. **Apply Client Revisions In-Place (Round 2+)**
   - When the client sends revision feedback (e.g., adding a feature highlight, exact LINE CTA, or live-review shots):
     1. `PATCH` the HTML content of the **existing Google Docs in-place** (`https://www.googleapis.com/upload/drive/v3/files/<doc_id>?uploadType=media`) — **never create duplicate new Docs** unless asked, so old links never go stale.
     2. Export each Doc as `text/plain` via the Drive API to verify every client-requested phrase landed verbatim.
     3. Update `updated_at` and `notes` in `_MANIFEST.json` (verify MD5 read-back).

4. **Mandatory Pure Handoff Delivery (BOTH Initial Delivery AND Every Revision Round!)**
   - Send **`N` separate pure messages** to the CEO's Telegram via `lib.telegram_out.send_to_ceo(msg)` AND render **`N` separate code blocks in chat** using **ONLY** this exact 4-line format:
     ```text
     Topic: {Name}
     Tags: #{ChannelBrand} #{ViralTag1} #{ViralTag2} #{ViralTag3} #{ClientBrand}

     Script: https://docs.google.com/document/d/{doc_id}/edit?usp=sharing
     ```

## Rules

1. **HARD — Re-send the `N` pure `Topic / Tags / Script` blocks to Telegram (`@SSomPongBot`) AND chat on EVERY revision round, even when the Google Doc URLs did not change (CEO ruling 2026-11-25).**
   **Why hard:** operator workflow — the CEO forwards each block directly from Telegram/chat into his LINE conversation with the client/account manager (e.g., `GiiG`); telling him "the old links are updated" without re-sending the 4 ready-to-copy blocks forces him to scroll back through old chat history (`"ส่งมาแนวนี้เพราะฉันต้องส่งให้ลูกค้า ... จำ Pattern ไว้ด้วย เขียนเป็น Skills ได้"`).

2. **HARD — Each Telegram message and each copy block must contain ZERO extra text (no `[คลิป 1/4]` header, no greeting, no summary inside the message) (CEO rulings 2026-11-23 & 2026-11-25).**
   **Why hard:** 1-tap copy-paste into client LINE — any extra label inside the Telegram bubble has to be manually deleted before pasting to the client.

3. **HARD — Follow `CMO_Rules_TikTok_Hashtags` (`<= 5` `#tags`, `#ChannelBrand` in Slot `#1`) and `CXO_Rules_GDrive_Filing` (`IRON-RULES §27.2` 5-entry folder layout + MD5 verification) on every script.**
   **Why hard:** platform hashtag cap & org filing integrity.

## Verify

1. `export?mimeType=text/plain` on each `<doc_id>` returns `>200` chars, contains every required client CTA verbatim, and passes `0` forbidden-word hits.
2. `lib.telegram_out.send_to_ceo` returns `{"ok": True, "reason": None}` for all `N` messages, and each message matches `^Topic: .+\nTags: (#\S+\s*){1,5}\n\nScript: https://docs\.google\.com/document/d/\S+$`.

## Failure modes seen

- **2026-11-24 → 2026-11-25:** Updated all 4 Bitunix Google Docs in-place for Rev 2 (`คุณกิ๊ก` feedback) and listed only bare URLs `1..4` in chat without re-sending the 4 pure `Topic / Tags / Script` blocks to Telegram/chat; the CEO showed his LINE chat screenshot (`GiiG`) proving he copies the full `Topic / Tags / Script` block each round to send to the client. Fixed in Rule 1 & Step 4 above.

## Field notes
