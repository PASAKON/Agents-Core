# BL60 headline (arm A of the 1-week A/B)

Arm A = a 2-line headline at frame 0 + a topical picture behind the avatar. Arm B is today's look.
Rules applied: at most 30 characters in total without spaces, the subject's name, one [[red]] word, a question or an attributed line, never a bare accusation.

## Option 1 (top)

- line 1: WikiFX: GB เคยมีใบ
- line 2: ถูก[[เพิกถอน]]แล้ว
- characters without spaces: 30
- why: Attributed to WikiFX by the colon, and it is WikiFX's own article title (เคยอยู่ใต้ CySEC แต่ใบอนุญาตถูกเพิกถอน). The licence status is not checked at the regulator, so the source is on screen.

## Option 2

- line 1: GB ยังมี[[ใบอนุญาต]]
- line 2: อยู่ไหม?
- characters without spaces: 23
- why: A question, no source word. Safer if the CMO does not want any status word on screen.

## Backdrop behind the avatar (real footage of this episode)

| t0 | file | what |
|---|---|---|
| 0 s | real/gb-header.png | 0 s, the WikiFX profile header with the GB name, the Goldenburg logo and the red label. |
| 1 s | real/gb-warning.png | 1 s, WikiFX's red warning card with its date. |
| 2 s | real/gb-article-oct.png | 2 s, the WikiFX article title that carries the headline's claim. |

## Date-stamp text

- Text: `ข้อมูลจากวิกิเอฟเอ็กซ์ ณ 1 ต.ค. 2569` (capture date, from the manifest).
- Posting day: `{{POST_DATE}}` (CMO fills in). If the post goes out later than the capture date, re-capture first: the pages and the numbers on them move.
- Placement: small, under the headline. The editor owns the font, the colour and the position; none of it goes in the JSON.

## CMO format addendum (top option, exact)

```json
{"lines": ["WikiFX: GB เคยมีใบ", "ถูกเพิกถอนแล้ว"], "red": "เพิกถอน", "backdrop": [{"t0": 0, "src": "real/gb-header.png"}, {"t0": 1, "src": "real/gb-warning.png"}, {"t0": 2, "src": "real/gb-article-oct.png"}]}
```

Option 2 as prose: GB ยังมีใบอนุญาต / อยู่ไหม?, red word "ใบอนุญาต". Same backdrop.
