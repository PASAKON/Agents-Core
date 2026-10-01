# BL59 headline (arm A of the 1-week A/B)

Arm A = a 2-line headline at frame 0 + a topical picture behind the avatar. Arm B is today's look.
Rules applied: at most 30 characters in total without spaces, the subject's name, one [[red]] word, a question or an attributed line, never a bare accusation.

## Option 1 (top)

- line 1: [[ใครตรวจ]] WikiFX
- line 2: เว็บให้คะแนนโบรก?
- characters without spaces: 30
- why: A question. Matches the CMO's example (ใครตรวจเว็บให้คะแนนโบรก?) and carries the subject's name. No allegation, no figure.

## Option 2

- line 1: โพสต์หนึ่งถาม
- line 2: WikiFX [[สี่ข้อ]]
- characters without spaces: 25
- why: Describes what the video is about: a post asks WikiFX four questions. Not a claim about WikiFX. If the CMO wants the attribution word, swap line 1 for "เขาอ้างว่า..." only with the post's label visible.

## Backdrop behind the avatar (real footage of this episode)

| t0 | file | what |
|---|---|---|
| 0 s | real/wfx-about-top.png | 0 s, the WikiFX name and logo from the real About-page header. |
| 1 s | real/fb-post-head.png | 1 s, the post's title with the Facebook label เนื้อหาที่สร้างโดย AI visible (page and author censored). |
| 2 s | real/wfx-stmt-title.png | 2 s, WikiFX's own statement title, its answer to the topic. |

## Date-stamp text

- Text: `ข้อมูลสาธารณะ ณ 1 ต.ค. 2569` (capture date, from the manifest).
- Posting day: `{{POST_DATE}}` (CMO fills in). If the post goes out later than the capture date, re-capture first: the pages and the numbers on them move.
- Placement: small, under the headline. The editor owns the font, the colour and the position; none of it goes in the JSON.

## CMO format addendum (top option, exact)

```json
{"lines": ["ใครตรวจ WikiFX", "เว็บให้คะแนนโบรก?"], "red": "ใครตรวจ", "backdrop": [{"t0": 0, "src": "real/wfx-about-top.png"}, {"t0": 1, "src": "real/fb-post-head.png"}, {"t0": 2, "src": "real/wfx-stmt-title.png"}]}
```

Option 2 as prose: โพสต์หนึ่งถาม / WikiFX สี่ข้อ, red word "สี่ข้อ". Same backdrop.
