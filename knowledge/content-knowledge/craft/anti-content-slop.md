# Anti-content-slop rules

Concrete, checkable rules for MoonieX content work. Every rule traces to a
real incident or a documented brand decision — no abstract theory.

## P0 — Auto-reject (must fix before shipping)

1. **AI trope words** — any occurrence of these in published copy is an
   automatic reject: "unlock", "elevate", "delve", "harness the power of",
   "in today's fast-paced world", "tapestry of", "seamless",
   "game-changer", "leverage" (as verb), "empower", "transform your
   journey".
   *Incident: 2026-05 auto-generated rebate posts read like SaaS landing
   pages; user trust dropped.*

2. **Em-dash in Thai copy** — Thai text uses no em-dash (—). Use period
   or middle-dot (·) instead. English-only sections may use em-dash
   sparingly (max 1 per 200 words).
   *Checkable: `grep '—' <file>` on Thai-language files.*

3. **Percentage-based rebate claim** — MoonieX rebates are stated as
   $/lot (XM $15/lot, Exness $8/lot). Never convert to a percentage.
   "คืน 80%" is wrong; "รับคืน $15/lot (80% IB share)" is correct.
   *Incident: percentage claims attract DSI scrutiny (wiki DSI
   crackdown).*

4. **Crude Thai pronouns** — มึง, กู, มั้ย (as มึง+อะ) in any published
   copy. Casual register is fine (ครับ, ค่ะ, นะ, เนอะ); crude is not.
   *Checkable: `grep -E 'มึง|กู' <file>`.*

## P1 — Should fix

5. **Mid-sentence emoji** — Emoji inside a sentence ("รับคืน💰$15/lot")
   breaks the FB caption standard. One trailing 🙏 on the CTA line is
   the sole permitted exception.
   *Checkable: `grep -Pn '[\x{1F300}-\x{1F9FF}]' <file>` on non-CTA
   lines.*

6. **Bare "unlimited" / "infinite"** — Rebates accrue only on closed
   lots. "รับคืนไม่จำกัด" is misleading. Use "รับคืนตามปริมาณการเทรดจริง".
   *Incident: user complained expected vs actual rebate mismatch.*

7. **Missing disclaimer on financial claims** — Any post mentioning
   $/lot, returns, or savings must include: "รีเบทขึ้นกับปริมาณการเทรดจริง"
   or equivalent. Zero exceptions.
   *Checkable: if `$` or `lot` appears in copy, disclaimer must follow.*

## P2 — Nice to fix

8. **Headline >10 words** — FB hook lines over 10 words get truncated in
   feed. Keep hook ≤10 Thai words.

9. **Hashtag count >5** — FB caption standard caps at 5 tags. Extra tags
   are noise, not reach.

10. **English acronym without Thai gloss** — First use of IB, CFD, P&L
    should include Thai explanation in parentheses: "IB (Introducing
    Broker)".
