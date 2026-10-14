# BL62 headline (one look, EP62 is not part of the A/B)

Rules applied: at most 30 characters in total without spaces, the subject's name, one [[red]] word, attributed line or question, never a bare accusation. No poster name.

## Option 1 (top)

- line 1: เธอเล่าว่า CXM
- line 2: ไม่จ่าย[[กำไร]] 6 ล้าน
- characters without spaces: 25
- why: attributed ("เธอเล่าว่า") with the broker's name and the figure as the post rounds it. A report of her claim, no verdict.

## Option 2

- line 1: CXM: 3 คำถาม
- line 2: ที่ยัง[[ไร้]]คำตอบ
- characters without spaces: 21
- why: her three open questions are the angle. Softer, but no number in the first frame.

## Backdrop behind the avatar (real footage of this episode)

| t0 | file | what |
|---|---|---|
| 0 s | real/cxm-post-claim.png | 0 s, the post's headline line with CXM visible; her name, photo and title lines blurred. |
| 1 s | real/cxm-post-account.png | 1 s, the CXM Direct line of the post. |
| 2 s | real/cxm-post-full.png | 2 s, the whole post, censored. |

The AI infographic is NOT used as a backdrop.

## Label

- Small label under the headline: `ภาพจากโพสต์ต้นทาง` (the post carries Facebook's AI label on its header, kept visible in cxm-post-full).

## CMO format addendum (top option, exact)

```json
{"lines": ["เธอเล่าว่า CXM", "ไม่จ่ายกำไร 6 ล้าน"], "red": "กำไร", "backdrop": [{"t0": 0, "src": "real/cxm-post-claim.png"}, {"t0": 1, "src": "real/cxm-post-account.png"}, {"t0": 2, "src": "real/cxm-post-full.png"}]}
```

Option 2 as prose: CXM: 3 คำถาม / ที่ยังไร้คำตอบ, red word "ไร้". Same backdrop.
