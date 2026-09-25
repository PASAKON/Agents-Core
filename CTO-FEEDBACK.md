# CTO feedback 2026-09-26 — the frame-390 stall

You hit the same failure EP57 hit on the Mac on 2026-09-24: one render stops at the same frame (about 400) every time, no matter what you retry. What fixed it there:

- Render your range in **windows of 9 s or less**.
- Each window is a **separate, fresh render process**: `bl_compose.py --t0 <a> --t-max <b>` with a ≤ 9 s span.
- Cut windows on beat boundaries, or on any frame boundary; both concat cleanly because every range render uses the same encoder settings.
- Concat the window mp4s with ffmpeg `-f concat -c copy` into `seg03.mp4`, then check the frame count equals your segment's frames (1161).
- Keep each window render inside `flock /tmp/bl-render.lock`.

Do not spend more attempts on the single full-range render. Log the attempt count and the switch in RUNLOG.md and REPORT.md (the CTO counts them). Then finish exactly as your brief says.
