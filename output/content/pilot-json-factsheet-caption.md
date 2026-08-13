# Pilot: JSON fact-sheet → FB caption (rebate-copy)

Source: `knowledge/content-knowledge/skills/rebate-copy/facts.json` (locked, `updated_at: 2026-07-18`)

## Fact trace (not part of the postable caption)

| Claim used in caption | facts.json field | Value |
|---|---|---|
| "XM คืนรีเบท $15 ต่อลอต" | `brokers[0].name` / `brokers[0].rate_usd_per_lot` | XM / 15 |
| "(gold-standard lot)" | `brokers[0].basis` | "gold-standard lot" |
| "Exness คืนรีเบท $8 ต่อลอต" | `brokers[1].name` / `brokers[1].rate_usd_per_lot` | Exness / 8 |
| "(ปิดออเดอร์ 1 standard lot)" | `brokers[1].basis` | "gold-based, per closed standard lot" |
| Disclaimer line | `required_disclaimer` | "รีเบทขึ้นกับปริมาณการเทรดจริง" |
| LINE CTA handle | `line_cta_id` | "@mooniebox" |
| No % rebate figure stated | `forbidden_claims[0]` | "percentage-based rebate figure" — avoided; `ib_share_pct` (80) deliberately omitted from copy since it describes IB structure not the rebate figure itself, and the SKILL rule says lead with $/lot not %. |
| No "unlimited"/"infinite" language | `forbidden_claims[1,2]` | avoided |

All figures pulled verbatim from `facts.json` — none re-typed from memory or recomputed.

---

เทรดทอง XM หรือ Exness อยู่ไหม? รีเบทคืนทุกลอตที่เทรด

XM คืนรีเบท $15 ต่อลอต (gold-standard lot) ผ่านโปรแกรม XM IB
Exness คืนรีเบท $8 ต่อลอต (ปิดออเดอร์ 1 standard lot) ผ่านโปรแกรม Exness IB

ทักแชท LINE: @mooniebox 🙏

รีเบทขึ้นกับปริมาณการเทรดจริง
#MoonieX #รีเบท #XM #Exness
