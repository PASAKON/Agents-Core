# BL61 headline (arm A of the 1-week A/B)

Arm A = a 2-line headline at frame 0 + a topical picture behind the avatar. Arm B is today's look.
Rules applied: at most 30 characters in total without spaces, the subject's name, one [[red]] word, a question or an attributed line, never a bare accusation.

## Option 1 (top)

- line 1: Tickmill 1 ล็อต
- line 2: จ่ายจริง[[เท่าไหร่]]?
- characters without spaces: 30
- why: A question with the subject's name and the unit of the example (1 lot). No claim about the broker, no figure.

## Option 2

- line 1: Tickmill: ศูนย์
- line 2: [[ไม่ได้]]แปลว่าฟรี
- characters without spaces: 29
- why: States the episode's point (a zero in a headline is not the total). The colon ties "ศูนย์" to the broker's page, but the line reads as a comment on the number, so the CMO may prefer Option 1.

## Backdrop behind the avatar (real footage of this episode)

| t0 | file | what |
|---|---|---|
| 0 s | real/tm-classic.png | 0 s, the Classic card: Tickmill's own "Zero Commissions" and "Spreads From 1.6 pips". |
| 1 s | real/tm-raw.png | 1 s, the Raw card: "Spreads From 0.0 pips" and "$3 per lot per side". |
| 2 s | real/tm-formula.png | 2 s, Tickmill's own cost formula (Spread x Trade Size x Pip Value). |

## Date-stamp text

- Text: `ข้อมูลจากหน้าเว็บของ Tickmill ณ 13 ต.ค. 2569` (capture date, from the manifest).
- Posting day: `{{POST_DATE}}` (CMO fills in). If the post goes out later than the capture date, re-capture first: the pages and the numbers on them move.
- Placement: small, under the headline. The editor owns the font, the colour and the position; none of it goes in the JSON.

## CMO format addendum (top option, exact)

```json
{"lines": ["Tickmill 1 ล็อต", "จ่ายจริงเท่าไหร่?"], "red": "เท่าไหร่", "backdrop": [{"t0": 0, "src": "real/tm-classic.png"}, {"t0": 1, "src": "real/tm-raw.png"}, {"t0": 2, "src": "real/tm-formula.png"}]}
```

Option 2 as prose: Tickmill: ศูนย์ / ไม่ได้แปลว่าฟรี, red word "ไม่ได้". Same backdrop.
