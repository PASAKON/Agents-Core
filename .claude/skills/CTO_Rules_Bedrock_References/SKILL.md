---
name: CTO_Rules_Bedrock_References
kind: rules
description: "RULES — Every link, picture, video, pack or data file handed over as a reference for Minecraft Bedrock work is recorded with its URL and our analysis in MoonieX-Bedrock docs/reference/links.jsonl, in the same turn. Trigger on any URL or image the CEO or a peer sends during Bedrock work, on \"Reff\", \"ref\", \"ดูอันนี้\", \"เก็บลิงก์\", \"จดไว้\", and before any web search on a Bedrock topic (search the ledger first). Downloaded asset files stay in CTO_Standard_Bedrock_WorkLayout / docs/reference/assets."
owner: CTO
created_by: agent
author: {role: cto, date: "2026-10-07", session: cto-369faf85}
audience: [cto, worker]
---

# Every reference gets a row: URL + what we learned

The CEO, 2026-10-07:
- *"จดไว้เป็น Skill ให้หน่อย ว่าการทำ Bedrock ทุกข้อมูลลิ้งที่ส่งให้ เซฟ URL + ข้อมูลที่วิเคาะห์มาแล้ว
  เก็บไว้เป็นความรู้ให้หน่อย"*
- *"และบังคับใช้กับทุกลิ้งที่เป็น Reff และข้อมูล"*

Binding on every session and worker that touches Bedrock work. The place is repo `PASAKON/MoonieX-Bedrock`:

| File | Holds |
|---|---|
| `docs/reference/links.jsonl` | one row per reference: URL, licence, status, what it is, analysis, what we take and never take |
| `docs/reference/links.md` | this rule and the field table |
| `tools/refs.py` | `find`, `add`, `note`, `check` |
| `tests/test_reference_links.py` | fails on an empty field, a repeated URL, an unexplained "not read", or media in a row |

## The rules

1. **Search the ledger before anything else.** Run `python3 tools/refs.py find <word>`, then the wiki `research/`,
   then the web. A link that already has a row gets `refs.py note <id> "<what is new>"`, never a second row.
2. **Record in the same turn as the analysis.** Do it before replying to the CEO about the link. Run
   `python3 tools/refs.py add --url … --title … --kind … --source … --licence … --status … --what … --analysis …`.
   Fill every field.
3. **A link you could not open still gets a row.**
   - Write `status: "not read: <why>"`, or `"partly read: <what, through which URL>"`.
   - minecraft.net Marketplace pages load by script only, so curl and headless return an empty shell.
   - Read the same offer at `https://www.bedrockexplorer.com/marketplace-offer/<creator>/<name>`. It has the
     description, price, rating and promo image URLs (row L001).
4. **Text only in the repo.**
   - Pictures, packs and videos behind a link never go into git (HQ rule: media goes to `Assets/`). A row names
     a local picture by its path.
   - Concept images are read in place only, never copied, uploaded or traced.
   - Promo images fetched to look at stay in the session scratchpad.
5. **Licence on every row.** "All Rights Reserved" means ideas only: never copy or trace pixels. A paid product (price
   in Minecoins or $) is not bought to study without the CEO's OK (money).
   **Exception, CEO ruling 2026-10-11 05:1x** (Dreamy Skies, Re-imagined Visuals): *"สามารถ Copy ของเขาได้ไหม ทำได้แค่บางตัวเลข
   ปรับเลขเป็นของเราเอง ขยับจุดไปใกล้เคียงได้"*. A studied pack's NUMBERS (lighting, atmospherics, colour grading) may
   seed our own files. Our generator writes them in our own structure, values resampled onto our grid and rounded, then
   tuned in game. Never ship a whole file, a texture, a cubemap or any art of theirs. Each provenance row names the pack
   and this ruling. It covers that one pack and that layer; another pack needs the CEO again.
6. **The analysis says what we learned and what we could not see.** For example: the technique, how it is attached,
   numbers, and what would settle an open question. A long write-up goes in a design doc or a wiki research note,
   and `notes` points at it.
7. **Workers too.** A brief that hands a worker a reference link quotes this rule. The worker's report lists the rows
   it added (`L0xx`).
8. **Ours from the start, and what is ours is stated from the files.** CEO ruling 2026-10-11 05:2x, after my account
   of the tour look cost a rebuild: *"ทุกๆ สิ่งทุกๆ อย่างที่เราทำมันคือของเราหมดเลย"* · *"อย่าหใ้เกิดเหตุการแบบนี้อีกนะมันเสียเวลามาก"* ·
   *"รอบหน้าเวลาจะเริ่มทำอะไร ให้ทำเป็นของเราตั้งแต่ต้น ของคนอื่นดูได้เอามาเป็น ไอเดียได้ และเอามา Build ในแบบของเรา ดีกว่าเยอะ"*.
   - Start every piece of work in our own files. Never install or load someone else's pack as the base we tune on.
     Look at theirs, take the idea, build it our way. Rule 5's number exception still stands: numbers go into our
     generator, never their pack under ours.
   - A test build that loads a studied pack (the RV demo and tour rig) is a test rig, not our pack. Never say our pack
     is built on, uses or takes from a studied pack.
   - Before any sentence to the CEO about what our pack contains or where it came from, run the copy check on the
     shipping ref and give him the table: files, files of theirs, licence text. The check is `rvbase_review.py <repo>
     <ref>` (sha256, reformatted JSON, renamed ids, number overlap against the studied pack's original archive). It
     sits in Assets `sky/scratch-cto-369faf85-2026-10-10/rvmap/`, not yet in a repo.
   - Never propose a rebuild or a change of direction on such a claim before that check has printed.

   **Why:** time. On 10-11 04:3x "the approved look ran on RV's base" led to a rebuild from 0 against a 12:00 deadline.
   The ship pack 6c7824f then measured 604 files: 0 of RV's and 0 licence text.

## The check

- `python3 tools/refs.py check` prints `ok: N rows`, and the gate `pytest tests/test_reference_links.py` passes.
- Every link the CEO sent in the session appears in `refs.py find`.
- The hook `scripts/hook-skill-suggest.py` reminds you when a prompt carries a URL or an image.

## Field notes

- 2026-10-07 [MISSING] §3 — minecraft.net Marketplace pages return only an app shell to curl (title "Minecraft DLC Marketplace"), and a headless Chromium navigation timed out; bedrockexplorer.com served the same offer as plain HTML with price, rating and image URLs · evidence: ledger row L001, session cto-369faf85 · status: pending
