# LINE OA "สมพงษ์" — profile/cover images report (task-e2b869ee)

Generated on chatgpt.com (free tier, $0, already-logged-in session — no
account created, no login performed). Uploaded to LINE OA Manager for
account สมพงษ์ (Basic ID `@590jexxd`, per `state/sompong-line/oa-setup-report.md`).

## Spec changed twice mid-task

The brief's original persona/prompts were superseded twice by the CEO via
`CEO-SPEC-UPDATE.md` in this worktree, both received while this task was
already running:

1. First update (22:10): persona changed from "early-40s office look" to
   "~46, southern Thai, down-to-earth (บ้านๆ), very smart" — style unchanged
   (flat vector illustration).
2. Final update (22:12): style changed again — must be **photorealistic**
   (a real photo look), not flat vector illustration. Same persona as #1.

The old-spec images (flat-vector, early-40s office look) were generated and
briefly uploaded to LINE first, then discarded and redone per instruction
("if you already generated with the old prompts, discard and regenerate").
**Only the final photorealistic images are live / referenced below.**

## ChatGPT chat (final version)

- Chat title: "Portrait Prompt Writing"
- URL: https://chatgpt.com/c/6aa177ce-ebd8-83ec-bf79-4745d86e8f47
- Two prompts sent in this one chat, in order: profile (square 1:1
  photorealistic portrait) then cover ("same man as the previous image" —
  photorealistic wide porch/sea scene). Both generated first try, no
  retries needed, no refusal, no free-image-limit message.
- (An earlier chat, "Flat Vector Avatar Prompt" —
  https://chatgpt.com/c/6aa175cb-dbdc-83ec-8ead-772a313bb3da — holds the
  discarded old-spec illustration images; not used for the final upload.)

## Files (final, photorealistic)

| File | Path | Pixel size | File size |
|---|---|---|---|
| Profile | `~/Desktop/sompong-line/sompong-profile.png` | 1254×1254 | 2,156,214 bytes (~2.16 MB) |
| Cover | `~/Desktop/sompong-line/sompong-cover.png` | 1536×1024 (3:2) | 2,384,434 bytes (~2.38 MB) |

Both downloaded via ChatGPT's own download button (full-image view →
download icon), moved out of `~/Downloads` and renamed with Bash, verified
with `sips -g pixelWidth -g pixelHeight`. Both PNG, both under LINE's 3 MB
limit.

## Upload result

LINE OA Manager → account สมพงษ์ (`@590jexxd`) → หน้าหลัก → แก้ไข → opened
`page.line.biz` business-profile editor (`account-page/2035890605995513/profile`).

- **Cover image: SUCCEEDED.** Uploaded `sompong-cover.png` (final
  photorealistic version), default crop already matched the recommended
  frame, accepted as-is. Page showed a green "บันทึกแล้ว" (saved) toast.
  **Verified live after a full page reload** — the porch/sea photorealistic
  image is the one page.line.biz now serves.

- **Profile picture: BLOCKED — not the final image yet.** The very first
  upload attempt this task (with the old illustration-style image) succeeded
  and triggered LINE's own stated cooldown: the confirmation dialog reads
  "คุณจะไม่สามารถเปลี่ยนรูปโปรไฟล์ได้เป็นเวลา 1 ชั่วโมง" (you cannot change
  the profile picture again for 1 hour). Attempting to upload the new
  photorealistic `sompong-profile.png` afterward returned
  "เกิดข้อผิดพลาดชั่วคราว" (temporary error) on the confirm step.
  **Confirmed genuine, not a stale-render glitch**: reloaded the page and
  retried the full crop→confirm→activate flow a second time — identical
  error both times, and a fresh page load both times still shows the OLD
  illustration profile picture as the live one. This is LINE's real
  server-side rate limit, not a UI bug — no further retries attempted per
  the "one clean attempt then hands-off" policy for platform-level blocks.
  - **Current live profile picture is still the discarded old-spec
    illustration** (early-40s, office look) — not the final photorealistic
    persona.
  - **The correct final file is ready and waiting**:
    `~/Desktop/sompong-line/sompong-profile.png` (photorealistic, 1254×1254).
  - First profile-pic change was made ~22:11 (2026-09-09); the 1-hour lock
    should clear around **23:11 Bangkok time** the same day. Whoever retries
    should: LINE OA Manager → สมพงษ์ → แก้ไข → upload that file → accept the
    default crop → confirm.

Both images render correctly on the account's own settings/preview page
where already saved (cover); profile preview correctly still shows the old
image because the new one was never actually accepted by the server.

## Notes

- File-upload path: `mcp__claude-in-chrome__file_upload` refused the
  original `~/Desktop/sompong-line/` path (files must be session-shared).
  Worked around by copying both PNGs into the worktree's
  `state/sompong-line/` temporarily for each upload, then deleting those
  copies immediately after (per brief: PNGs are not committed — only this
  report is).
- No sticker/rich-menu work touched. No other LINE account touched. No
  money spent, no paid plan/model used, no ChatGPT Plus upsell accepted (a
  "อัปเกรดเป็น Plus" banner appeared once mid-generation and was dismissed,
  not clicked).
