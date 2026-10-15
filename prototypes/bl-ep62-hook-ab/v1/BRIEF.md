# Job: write the HyperFrames composition for the BL EP62 hook (V1)

You only read and edit files in this folder. Do not run any command (no npm, npx, node, git, ffmpeg); I render it myself.

Deliverable: `index.html` in this folder, rewritten so that `npx hyperframes@0.8.40 render` produces the 15.0 s video that
`SPEC.md` describes, beat for beat. SPEC.md is the design; follow it exactly (timings, text, positions, motion).

What is here:
- `index.html`: the BLACK LIQUIDITY HyperFrames template (the "kit"). KEEP its head (fonts, gsap script tag, CSS for
  .bl-legal, .bug, .blk, caption pill, etc.), its `.bl-legal` div (text unchanged, every frame) and its `#bug` (change only
  the date text to `14 ต.ค. 69`). Replace the example content in the body's VIDEO TRACK and below "THE CUT" with this clip.
  Keep `window.__timelines["main"] = tl; tl.seek(0);` at the end and keep the root element's data-duration in line with 15 s
  (look at how the template declares the composition length and set it to 15).
- `media/`: `audio-0-15.wav` (narration, 15 s), `avatar.mp4` (640x1024 lipsync, play with data-media-start = data-start),
  `broll-12.mp4` `broll-29.mp4` (1080x1920, 8 s each, no sound), `broll-28.mp4` `broll-39.mp4` (spare, optional),
  `cxm-post-claim.png` `cxm-post-account.png` `cxm-post-full.png` (1080x1920 stills).
- `assets/`: logo + fonts (already wired in the template).

HyperFrames rules (from the template and how our tools emit it):
- A video plate: `<video class="clip" src="media/x.mp4" muted playsinline data-start="S" data-duration="D" data-media-start="M" data-track-index="0"></video>`.
  A still: `<img class="clip" src="media/x.png" style="top:0;left:0;width:1080px;height:1920px" data-start="S" data-duration="D" data-track-index="0">`.
  Higher data-track-index draws on top. The narration is the `<audio id="va">` element: point it at media/audio-0-15.wav with data-duration="15".
- Every animation goes on the ONE paused gsap timeline `tl` at absolute times (seconds). No setTimeout, no requestAnimationFrame,
  no CSS animations/transitions, no Date/random: the renderer seeks the timeline frame by frame, so only `tl` tweens show.
- Count-ups: tween a plain object's value on `tl` with an onUpdate that writes the formatted text into the element
  (the renderer seeks, so onUpdate must compute the text from the value only).
- Zoom/push-in on a still or video: tween its transform (scale, transformOrigin) on `tl`.
- Highlight boxes: absolutely positioned divs with a yellow (#FFD60A) 6 px border, drawn by tweening clip-path or scaleX on `tl`.
  When the still is zoomed, put the box inside the same wrapper that is scaled so it stays on the line.
- Thai lines: one line each, `white-space: nowrap`; the template has fitKineticLine() to shrink a line to the safe width: use it.

When done, write `NOTES.md` here: 5-10 lines on what you built and anything in SPEC.md you could not do exactly.
