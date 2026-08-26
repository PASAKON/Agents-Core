# Valder video wave 5 (task-40dd8087)

Takes over from `task-581d5c05` (wave 4). Wave 4 fired: S2 (variant take 1,
canonical take 1) and S-V (take 1). Full wave4 handoff lives on that branch
at `docs/reports/valder-video-wave4.md` (uncommitted to main as of wave5
start — read via `git show agent/browser_operator-task-581d5c05:docs/reports/valder-video-wave4.md`).

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/`

Standing fire sequence, per task brief: attach elements → paste prompt →
scan reference strip for warning triangles, click every one → verify N/N
bound, 0 errors → verify composer settings (Seedance 2.5 / 20s / 720p / 16:9
/ Sound On / Unlimited ON) → zoom Generate button, confirm struck-through
price resolving to 0 → click.

Prompt files already synced with `main` at wave5 start (diffed all 15, zero
drift).

## Queue plan

Pass 1 (skip S2, S-V — already covered wave4): S1, S1B, S-MU, S3, S4A, S4,
S4B, S4C, S5, S5B, S6, S7A, S7B — in story order.
Then pass 2: all 15 scenes, second take, top to bottom.
Then pass 3: all 15 scenes, third take, top to bottom.

## Credits

Opening balance: **1,918** (confirmed via account menu, matches task brief exactly).

## Clip table

(updated after every fire)

| Scene | Take | Clip asset id | Elements | Settings | Notes |
|---|---|---|---|---|---|
| S1 | 1 | `05261d07-4547-479e-97f7-a9fc14703ba0` | 9/9, 0 errors | Seedance 2.5 / 16:9 / 720p / 20s / High / Sound On / Unlimited ON | Composer settings rebuilt fresh from a cold project-root load (Cinema Studio 4.0/1080p/16:9/5s default → switched model to Seedance 2.5 first, then 720p, then duration slider ArrowRight x15 to reach 20s, then Unlimited toggle ON, verified `aria-checked=true`). Real-clipboard paste (`pbcopy` + real Cmd+V), verified exact match: 31,322 normalized chars, first/last 80 chars identical to source. 9/9 mention chips bound (the ceiling), 0 errors. Reference strip zoomed: all 9 cards clear, zero warning triangles — no eligibility clicks needed this fire. Generate button zoom-confirmed `UNLIMITED / ~~140~~ / 0` immediately before click. Fired clean, "Generation started" toast, credits 1,918 unchanged (Unlimited, 0 cost). Rendering — needs visual review for the crowd rule (loose/scattered, not rally-formation) once complete.
