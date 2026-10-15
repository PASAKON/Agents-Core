# BL EP62 Hook (V1 — HyperFrames) Notes

- Built the 15.0 s (1080×1920, 30 fps) HyperFrames + GSAP composition in `index.html` wired to `media/audio-0-15.wav` (`#va`, `data-duration="15"`) and `#root` (`data-duration="15"`).
- Implemented all 7 beats (`OPEN`, `HOOK-1`..`HOOK-4`, `PATTERN-1`, `PATTERN-2`) with exact cut timings, brightness filters, push-in/zoom transforms, and hard cuts on the single paused GSAP timeline `tl`.
- Added the persistent top-band 2-line headline (`0.00..9.27`s, visible from frame 0 with a 0.4 s slide-up/scale-down landing) and the smaller 1-line headline (`11.67..15.00`s), hidden during the full-bleed lip-synced `avatar.mp4` beat (`9.27..11.67`s, `data-media-start="9.27"`).
- Built the `0:00 -> 2:00 ชม.` clock count-up (`HOOK-1`), the `0 -> 6` million baht count-up (`HOOK-2`), the `TOXIC TRADING?` red stamp slam (`HOOK-3`), the popping `3` (`HOOK-4`), and the 62% rounded card entrance over `broll-29.mp4` (`PATTERN-1`).
- Placed the 6 px `#FFD60A` highlight boxes inside the scaled still wrappers (`#wrap-hook2`, `#wrap-hook3`) so their still-space coordinates (`120,850,720,60` and `120,818,720,55`) track the zoom.
- Enforced single-line Thai rendering (`white-space: nowrap`) and safe-area sizing via `fitKineticLine()` on every headline, clock, stamp, and caption line.
- Kept the kit's `.bl-legal` and `#bug` CSS untouched per `BRIEF.md` (updating `#bug` date to `14 ต.ค. 69`), and constrained the headline width (`x: 120..756`) so it sits cleanly to the left of `#bug`.
- Fix 1 (PATTERN-1): Replaced 62% scaled still with an 860×313 px cropped wrapper card (showing y 763..1156 of cxm-post-account.png at left 110, top 600, border-radius 24px, 2px 20% white border, soft shadow) with an 80 px slide-up entrance over 0.35 s, and boosted broll-29 brightness to 60%.
