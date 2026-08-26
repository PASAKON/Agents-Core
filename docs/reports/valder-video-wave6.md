# Valder video — wave 6 report

Continuing from wave5 (task-40dd8087, merged 18d537c, stopped cleanly at
194k tokens after S6). This wave's job, in order: **S7A**, then **S7B** —
the last two uncovered scenes. Full rules in
`docs/reports/valder-wave6-brief.md`.

State at handoff (wave5 → wave6): credits opened/closed 1,918 across all of
wave5, zero spent. No render in flight when wave5 stopped. Composer tab left
open at `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/` —
opening a FRESH tab before the first fire per the tab-staleness rule.

---

(Clip table below, one row per fire this wave.)

| Scene | Take | Clip asset id | Elements | Settings | Notes |
|---|---|---|---|---|---|
| S7A | 1 | `8b229925-7013-408f-b5c5-d0a9b8f011aa` | 8/8, 0 errors | Seedance 2.5 / 16:9 / 720p / 20s / High / Sound On / Unlimited ON | First-ever fire of this scene. Duration control is a slider (role="slider", aria-valuemin 4, aria-valuemax 30) on this root-composer surface, not a free-text field — arrow keys, not typed digits, set it to 20. All 8 reference thumbnails clean, no warning triangles. Paste verified 8/8 `data-beautiful-mention` chips + exact first/last-80-char match before firing. Button read `UNLIMITED / ~~140~~ / 0` at click time. Fired clean, "Generation started" toast, project asset count 273→274. Rendering — take confirmed complete before moving to S7B. |
