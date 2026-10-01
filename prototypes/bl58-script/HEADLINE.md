# BL58 headline (arm A of the 1-week A/B)

Arm A = a 2-line headline at frame 0 + a topical picture behind the avatar. Arm B is today's look.
Rules applied: at most 30 characters in total without spaces, the subject's name, one [[red]] word, a question or an attributed line, never a bare accusation.

## Option 1 (top)

- line 1: Weltrade ถูก[[ร้องเรียน]]
- line 2: ถอนไม่ออก?
- characters without spaces: 30
- why: Attributed: complaints exist on WikiFX (the card on screen says so), and the second line is a question. Names the subject, says what it is about, claims nothing as fact.

## Option 2

- line 1: WikiFX [[เตือน]] Weltrade
- line 2: จริงไหม?
- characters without spaces: 27
- why: Names the source (WikiFX) and asks. Weaker on the topic word, stronger on attribution.

## Backdrop behind the avatar (real footage of this episode)

| t0 | file | what |
|---|---|---|
| 0 s | real/weltrade-header.png | 0 s, the WikiFX tile with the Weltrade name and logo (the real header). |
| 1 s | real/weltrade-warning.png | 1 s, WikiFX's red warning card with its date (the visible proof of the first line). |
| 2 s | real/wikifx-article-sep.png | 2 s, the 30 Sep WikiFX article title (a second, dated source). |

## Date-stamp text

- Text: `ข้อมูลจากวิกิเอฟเอ็กซ์ ณ 1 ต.ค. 2569` (capture date, from the manifest).
- Posting day: `{{POST_DATE}}` (CMO fills in). If the post goes out later than the capture date, re-capture first: the pages and the numbers on them move.
- Placement: small, under the headline. The editor owns the font, the colour and the position; none of it goes in the JSON.

## CMO format addendum (top option, exact)

```json
{"lines": ["Weltrade ถูกร้องเรียน", "ถอนไม่ออก?"], "red": "ร้องเรียน", "backdrop": [{"t0": 0, "src": "real/weltrade-header.png"}, {"t0": 1, "src": "real/weltrade-warning.png"}, {"t0": 2, "src": "real/wikifx-article-sep.png"}]}
```

Option 2 as prose: WikiFX เตือน Weltrade / จริงไหม?, red word "เตือน". Same backdrop.
