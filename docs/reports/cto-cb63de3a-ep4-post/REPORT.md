# EP4 «ขายฝากนาแม่» — Facebook Reel post, 2026-09-28

CEO: "หลังจากนี้ โพส ลง Facebook ได้เลย" (posting approved, 2026-09-28).

| step | result |
|---|---|
| composer identity | `ละครสั้นคุณธรรม by ILAG Studio` |
| video | `ep4-FINAL-v1.mp4` 1080x1920, upload 100 % confirmed |
| caption | `docs/scripts/ep4-reels-caption.txt` (45145aac), read back: match |
| cover | `poster-b-rice.png` (CEO pick), set: True |
| audience | Public |
| publish | clicked "แชร์" exactly once |
| permalink | VERIFIED https://www.facebook.com/61594116376333/videos/1973008630041783/ |
| first comment | **REFUSED, exit 7**: the comment box read `Dorsine Gobb`, not the Page. Nothing was typed or posted. |

Screenshots: `dryrun.png`, `publish.png` (this folder, untracked).

## Open

- First comment (`docs/scripts/ep4-first-comment.txt`) still to post as the Page:
  switch the Mac Chrome :9230 session to the Page ("สลับเลย" on the Page), then
  `tools/fb_reel_post.py --comment-only --permalink <above> --first-comment-file docs/scripts/ep4-first-comment.txt`.
  The identity switch was blocked by the permission classifier on 2026-09-28 and waits for the CEO's approval.
- AI label: the composer showed no AI-content-disclosure control.
