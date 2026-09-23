# BLACK LIQUIDITY EP57 — เว็บหาย ไม่มีใบอนุญาต (XXLMARKETS)

Topic: XXLMARKETS, assigned by the CEO 2026-09-23 with a WikiFX Thailand
review card as the seed source
(`prototypes/bl57-realfootage/third-party/wikifx-xxlmarkets-review.jpg`,
see `third-party/SOURCES.md`). Card's claim: "XXLMARKETS ยังเปิดให้เทรดอยู่ไหม?
เว็บเข้าไม่ได้ แถมไร้หน่วยงานคุ้มครอง". Every number on it was re-checked live
2026-09-23 before entering the script — see the sources table below and the
full research writeup at `research/xxlmarkets-wikifx-fca-domain-202609.md`.

Angle vs EP55 (BingX): EP55 = a famous name with no license, real user
complaints on record. EP57 = the broker's OWN website has vanished from the
internet entirely — not "down", but no longer even registered (confirmed by
this channel independently, not just claimed by WikiFX). That "the site is
gone" finding is this episode's own original reporting, not a repeat of the
card.

Format: 40 tagged lines per `blackliquidity-script` skill (measured from
BL50) — one line = one tag = one idea = one breath. Phrases written
closed-up, spaced only at real breath points; numbers as closed-up Thai
words in the spoken column.

---

## Sources — every claim, checked live 2026-09-23

| claim | source | checked | result |
|---|---|---|---|
| Score 1.99/10, "ยังไม่มีการกำกับดูแล", UK, 2-5 years, "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์", warning banner text, website-inaccessible note | WikiFX Thailand dealer profile: https://www.wikifx.com/th/dealer/3697715948.html | WebFetch 2026-09-23, cross-checked against the EN page (same URL, `/en/`) | Matches the CEO's card exactly on every field. EN page adds: founded 2021, subscore breakdown (Regulation 2.69, Tech 4.54, Reputation 3.51, Business 6.31, Risk Control 2.79 — visible in full on the CEO's own card's radar chart), contact +44 7441427348 / support@xxlmarkets.com |
| xxlmarkets.com is inaccessible | this channel's own re-check: `dig`, `dig @8.8.8.8`, `whois -h whois.verisign-grs.com`, `curl -I`, and a live Claude-in-Chrome visit, all 2026-09-23T14:36 UTC | run live this session | **Stronger than the card's claim.** DNS returns NXDOMAIN and the .com registry itself returns "No match for domain XXLMARKETS.COM" — the domain is not merely down, it is not currently registered at all. Chrome's own visit renders a connection-error page with no content. |
| The domain WAS registered before and has since lapsed (2022-2026 history exists) | who.is public WHOIS lookup: https://who.is/whois/xxlmarkets.com | Claude-in-Chrome live visit 2026-09-23 | "We don't have a current record for xxlmarkets.com, but we hold 4 historical WHOIS/RDAP snapshots of it from 2022 to 2026." Confirms the domain existed and is now gone — used for MAIN-3/MAIN-4/CURIOSITY-2. (First tried ICANN's own Lookup tool; dropped after the contact sheet caught that its `?q=` URL param doesn't auto-run the search — see `shots.yaml` comments.) |
| "Even the local FCA shows no results about it" | WikiFX's own EN summary text, paraphrased by an automated page-read, not a literal on-page quote we could re-anchor for a screenshot | attempted independently: register.fca.org.uk (3 tries, page never rendered results — client-side issue, not a wrong URL) and fca.org.uk/scamsmart (blocked by a bot-detection challenge we will not bypass, per hard rule) | **Not independently verified today.** Scripted as WikiFX's attributed claim only (CONTEXT-4), with no real-footage shot behind it — see `research/xxlmarkets-wikifx-fca-domain-202609.md` for the full attempt log |

Full research writeup with every command and its raw output:
`research/xxlmarkets-wikifx-fca-domain-202609.md`.

## Hook — 3 options for the CEO to pick

**Option A — "เว็บหาย" (used in the TSV below; recommended: leads with our
own original finding, not just the card's claim)**
```
[HOOK-1] เว็บเทรดที่มึงอาจเคยฝากเงินไว้หายไปจากอินเทอร์เน็ตแล้ว
[HOOK-2] ไม่ใช่แค่เข้าเว็บไม่ได้ กูเช็กเองพบว่าโดเมนทั้งโดเมนไม่มีอยู่จริงด้วยซ้ำ
[HOOK-3] เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ วิกิเอฟเอ็กซ์บอกไว้แล้วว่าไม่มีใบอนุญาต ไม่มีหน่วยงานคุ้มครอง
[HOOK-4] เดี๋ยววันนี้กูจะพาไปดูของจริงทีละขั้นให้ฟัง
```

**Option B — EP55-bar style ("เป็นเรื่องแล้วไงอีกแล้ว")**
```
[HOOK-1] เป็นเรื่องแล้วไงอีกแล้ว
[HOOK-2] คราวนี้ไม่ใช่แค่ไม่มีใบอนุญาต แต่เว็บทั้งเว็บหายไปจากโลกออนไลน์เลย
[HOOK-3] เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ วิกิเอฟเอ็กซ์เช็กให้แล้วเจอทั้งไร้ใบอนุญาตและเว็บล่ม
[HOOK-4] กูไปเช็กต่อเองแล้วเจอว่ามันแย่กว่านั้นอีก
```

**Option C — curiosity/question opener**
```
[HOOK-1] ลองพิมพ์ชื่อเว็บนี้ในเบราว์เซอร์ดูสิ
[HOOK-2] เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ จะเจอแค่หน้าเว็บที่โหลดไม่ขึ้นเลย
[HOOK-3] วิกิเอฟเอ็กซ์เช็กไว้แล้วว่าไม่มีใบอนุญาต ไม่มีหน่วยงานคุ้มครองด้วย
[HOOK-4] กูเช็กต่อเองอีกที เจอเรื่องที่แย่กว่าที่วิกิเอฟเอ็กซ์เขียนไว้อีก
```

## Length forecast

- Total spoken characters: **2,308** (40 lines)
- Speech-only @ 16.6 chars/s: **139.0 s**
- Whole-track (with breath gaps between lines) @ 13.2-14.7 chars/s:
  **157.0 s – 174.8 s** (midpoint ≈ 166 s)
- For comparison, EP55 v1 ran 2,470 chars → 167.66 s. This script is
  shorter and should land at or under that.

## Structure / beat counts

- `hook`: 3 lines (HOOK-1, HOOK-2, HOOK-4 — HOOK-3 is `show`)
- `show` (avatar shrinks, real footage carries the line): **11 lines** —
  HOOK-3, PATTERN-1, PATTERN-2, CONTEXT-1, CONTEXT-2, CONTEXT-3, MAIN-3,
  MAIN-8, MAIN-9, MAIN-10, CURIOSITY-2
- `verdict` (avatar full frame, judgement/emotion): 22 lines
- `cta`: 4 lines (SUMMARY-4, 5, 6 — the checklist — and SUMMARY-8, the
  comment-keyword line)

## Brands

- เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ → `XXLMARKETS` (row already in `brand-display.yaml`)
- วิกิเอฟเอ็กซ์ → `WikiFX` (row already in `brand-display.yaml`)
- No new brand rows needed.

## Compliance checklist

- No broker the channel earns from is named (XXLMARKETS earns the channel
  nothing — same status check as EP55's BingX).
- No link, no account CTA, no rebate/income mention, no MoonieX mention.
- CTA points at knowledge only: SUMMARY-8, "คอมเมนต์คำว่า เช็กเว็บโบรก" — a
  new keyword for this episode (distinct from EP55's "เช็กก่อนฝาก"), since
  this episode's checklist is specifically about checking a site/domain is
  still real, not just a regulator lookup.
- No em dash anywhere in the spoken column.
- มึง/กู used (11 กู, 6 มึง — lighter than EP55's 24 total, since more of
  this script is original reporting in a measured register rather than
  quoting WikiFX directly).

## What the viewer should be able to check themselves

1. Type `xxlmarkets.com` into a browser right now — it will not load.
2. Look up the domain at a public WHOIS tool (e.g. who.is) — no current
   registration, only historical snapshots.
3. Search "XXLMARKETS" on WikiFX (wikifx.com) — same score, same "no
   license" finding.
4. Use the same two tools (WikiFX + a public WHOIS lookup) to check any
   other broker before depositing — this is exactly the checklist
   SUMMARY-4/5/6 walks through.

## Real footage note (CTO feedback, 2026-09-23 22:10 — evidence_box)

`REAL_MANIFEST.json` now carries an `evidence_box` array (px, 1080x1920 or
1080x1350 for the third-party still) on every entry, per the new §6d P1 gate
that refuses to composite the avatar over evidence with no box declared.
`tools/bl_realfootage.py` does not write this field yet — every box here was
measured by eye on the full-resolution still (`evidence_box_source:
"measured"` on every entry, none had DOM box data available to reuse). The
tool should be updated to export the DOM box it already computes internally
for `selector`/`text` crop anchors, so future episodes don't need this by-eye
pass — flagging for whoever owns `tools/bl_realfootage.py` next.

Two shots were caught and fixed during review, not before capture:
- `wikifx-profile-country-years` (originally covering PATTERN-2 alone) was
  dropped after the full-resolution still showed only the country, not the
  "2-5 ปี" years claim PATTERN-2 also makes — that combination only appears
  together in the profile header, which `wikifx-profile-score` already
  captures. PATTERN-2 now points there instead.
- The ICANN Lookup shot for MAIN-3/CURIOSITY-2 was replaced with a who.is
  capture after the contact sheet showed ICANN's tool never actually ran the
  search (its `?q=` URL param doesn't auto-trigger a client-side SPA) — the
  who.is capture is a direct server-rendered result and is, if anything,
  stronger evidence (it also surfaces the domain's registration history).
