# Job: write the Remotion project for the BL EP62 hook (V2)

You only read and edit files in this folder. Do not run any command (no npm, npx, node, git, ffmpeg); I render it myself.
Remotion 4.0.532, React 18.3.1 and TypeScript are already installed in node_modules. The official Remotion agent skills are
installed in `.agents/skills/` (start with `.agents/skills/remotion-best-practices/SKILL.md`, then what it points to for
video, images, fonts, audio, text animation). Follow them.

Deliverable: the source under `src/` so that this command renders the 15.0 s video `SPEC.md` describes, beat for beat:
  `npx remotion render src/index.ts Hook out/hook-v2.mp4 --codec h264 --concurrency 1`
SPEC.md is the design; follow it exactly (timings, text, positions, motion). Write at least:
- `src/index.ts` (registerRoot), `src/Root.tsx` (one <Composition id="Hook" width={1080} height={1920} fps={30} durationInFrames={450}>),
  `src/Hook.tsx` and any components you want, plus `tsconfig.json` if you need one.

Media (in `public/`, use staticFile()): `audio-0-15.wav` (narration, 15 s, starts at frame 0), `avatar.mp4` (640x1024 lipsync:
its time must equal the timeline time, so in the HOOK-4 Sequence starting at 9.27 s use startFrom/trimBefore = 9.27 s in frames),
`broll-12.mp4` `broll-29.mp4` (1080x1920, 8 s, muted), `broll-28.mp4` `broll-39.mp4` (spare), `cxm-post-claim.png`
`cxm-post-account.png` `cxm-post-full.png` (1080x1920), `bl-logo.png`, `fonts/` (Kanit 600/800 and Archivo 800 woff2 files:
the file name says family and weight; load them with @font-face via a style tag or @remotion/fonts-free method from the skills,
and make sure the render waits for them, e.g. delayRender/continueRender).

Rules:
- Every motion is a pure function of useCurrentFrame() (interpolate / spring). No CSS animations, no setTimeout, no Math.random.
- Videos: OffthreadVideo (or what the skills recommend for render), muted. Audio: <Audio>.
- Thai lines: one line each, `white-space: nowrap`, shrink to fit the safe width (SPEC.md) rather than wrap.
- Use only the packages already installed (remotion, @remotion/cli, react). Do not add dependencies.

When done, write `NOTES.md` here: 5-10 lines on what you built and anything in SPEC.md you could not do exactly.
