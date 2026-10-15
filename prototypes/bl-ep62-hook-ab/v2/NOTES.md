# Implementation Notes (BL EP62 Hook V2 — Remotion)

- Built the 1080×1920, 30 fps, 450-frame (`15.0 s`) `Hook` composition in `src/index.ts`, `src/Root.tsx`, `src/Hook.tsx`, `src/components/Overlays.tsx`, and `src/fonts.ts`, with `tsconfig.json`.
- Implemented all 7 beats (`OPEN`, `HOOK-1`, `HOOK-2`, `HOOK-3`, `HOOK-4`, `PATTERN-1`, `PATTERN-2`) at exact frame boundaries (`0`, `30`, `107`, `193`, `278`, `350`, `419`..`450`) with `OffthreadVideo` (muted), `Img`, and `Audio` (`audio-0-15.wav` from frame 0).
- Synchronized `avatar.mp4` in `HOOK-4` (`from={278}`, `9.27 s`) using `trimBefore={Math.round(9.27 * fps)}` (`278` frames) so media time matches timeline time and scales with `objectFit: 'cover'`.
- Placed the yellow highlight boxes in `HOOK-2` and `HOOK-3` inside the same `transformOrigin`/`scale` wrapper as the post stills so they move in lockstep with each zoom while drawing via SVG stroke + marker fill interpolation.
- Loaded local `Kanit` (600/800) and `Archivo` (800) `.woff2` files from `public/fonts/` via `getStaticFiles()`/`staticFile()`, `@font-face`, and `FontFace` gated by `delayRender`/`continueRender` so frame 0 renders with loaded fonts and full imagery.
- Enforced single-line Thai rendering (`whiteSpace: 'nowrap'`) and safe-area bounds (`x: 120..840`, `y <= 1500`) across all headlines, captions, and the legal disclaimer using canvas text measurement (`fitFontSize`) to shrink any overflowing line.
- All specifications in `SPEC.md` were implemented directly without compromises; in `PATTERN-1`, the `62%`-scaled `cxm-post-account.png` card is framed around the white post body (`670×340` at `y = 900`) so its black letterbox padding does not obscure `broll-29.mp4`.
- Fix 1: Resized PATTERN-1 card to 860×313 px at left 110, top 600 px with 24px border-radius, 2px white/20% border, cropping cxm-post-account.png directly to the post band (scaled by 860/1080 and shifted up 607.6 px), and raised broll-29 brightness to 60%.
