# mooniex-trading-psychology-test — video_editor cold-start report

Source: `/Users/gob/Downloads/5s4YPgZzVy6GUbae6TW2E_output.mp4` (40.0s, 640x1024, bt709 SDR).
Delivered: `~/Desktop/video-editor-test/{reel_clean.mp4, cover.jpg, caption.txt}`.
Authored: `output/reels/mooniex-trading-psychology-test/timeline.py` (this dir).

## Workflow followed

1. Read `mooniex-video-editor/SKILL.md`, then `reel-editor-th/SKILL.md` +
   `references/authoring-guide.md` + `references/cutaway-authoring.md`, in that order.
2. Extracted audio (`ffmpeg -vn -ar 16000 -ac 1`), transcribed with mlx-whisper
   (`whisper-large-v3-turbo`, `th`, `word_timestamps=True`, `condition_on_previous_text=False`).
3. Planned avatar/footage/animation beats against the real transcript (not assumed).
4. Authored `timeline.py` from scratch, ran `build.sh ... clean`.
5. Sampled a frame from every beat (15 timestamps across the full 40s) and looked at
   each one — caught and fixed 2 real bugs during this pass (see below).
6. Delivered to Desktop; left `timeline.py` + this report in the repo.

## Beats (final)

| Time (s) | Type | Content |
|---|---|---|
| 0.0-4.6 | avatar + HOOK | "90% นักเทรดขาดทุน / เพราะอารมณ์ ไม่ใช่ระบบ" |
| 4.6-7.32 | footage (video) | `frames-candlestorm-2.72s` — "แต่เพราะอารมณ์ชนะระบบ" (thesis reveal) |
| 7.74-10.3 | avatar | personal anecdote ("ผมเจอนักเทรดมาเยอะมาก...") |
| 10.3-13.18 | footage (video) | `frames-candleglow-2.88s` — "แบคเทสต์ผ่านมาหลายปี" (system looks good on paper) |
| 13.42-16.8 | avatar | "แต่พอเทรดจริง กดเข้าผิดไซส์..." |
| 16.8-18.9 | animation (kinetic) | "ตัด SL / ไม่ได้" (named mistake, red accent) |
| 18.9-21.3 | footage (photo) | `trader-laptop-cash-risk.jpg` — "พอร์ตยังหายอยู่ดี" |
| 21.3-24.48 | avatar | "ปัญหาอยู่ที่สภาวะทางอารมณ์ตอนเทรด" |
| 24.48-26.78 | animation (kinetic) | "มีสามกับดักหลัก / ที่ทุกคนเจอ" — **changed from the reference `card` cutaway, see judgment calls** |
| 26.78-27.22 | avatar | brief transition |
| 27.22-34.6 | avatar + COUNTER | "กับดัก: Revenge Trade" tag; photo `trader-silhouette-red-tradingfloor.jpg` 30.36-32.78; kinetic "กลับยิ่ง / ขาดทุนหนักขึ้น" 32.98-34.6 |
| 35.62-40.0 | avatar + COUNTER | "กับดัก: Overconfidence" tag; photo `trader-victory-confetti.jpg` 36.5-38.14; PUNCH_TEXT "อารมณ์คือกับดักจริง" 36.5-40.0; CTA (follow/bio) from 34.5 |

SFX: 4 events (chime at thesis reveal 5.46s, pop at the SL kinetic beat 16.8s, pop at
each COUNTER tag pop-in 27.22s/35.62s) — 2 distinct sounds, no per-cut whoosh.

## Assets used

All from `~/.claude/skills/reel-editor-th/assets/mooniex-broll/` (asset sourcing order
step 1 — nothing needed from Drive):
- `frames-candlestorm-2.72s/`, `frames-candleglow-2.88s/` (pre-extracted 9:16 PNG
  sequences — durations already match my beat windows exactly, did not need to
  re-extract from the raw broll mp4s)
- `trader-laptop-cash-risk.jpg`, `trader-silhouette-red-tradingfloor.jpg`,
  `trader-victory-confetti.jpg`
- Skipped `trader-stressed-BAKED-TEXT-avoid.jpg` (filename says why — has baked-in text).

## Brand-rule / source-truncation judgment calls

**The confirmed source-truncation case.** The speaker says "มีสามกับดักหลักที่ทุกคนเจอ"
(there are 3 main traps) at 24.48s, then only explains two — Revenge Trade (27.22-34.6s)
and Overconfidence (35.62-40.0s) — before the recording stops mid-sentence at 40.0s
("รู้สึกว่าตัวเองอ่านกราฟแม่น" has no closing clause). This is exactly the pattern
`mooniex-video-editor/SKILL.md`'s "Known source-truncation issue" section describes.
I did not invent a 3rd trap, complete Overconfidence's cut-off sentence, or add a
spoken CTA/close that wasn't in the audio.

**Dropped the reference `card` cutaway.** `cutaway-authoring.md`'s worked example (and
`render_captions.py`'s `draw_traps_card` + `render_cover.py`'s `cover_clean`, both
already pre-written for this exact clip) use a "3 กับดักจิตวิทยา" checklist card with
rows `["Revenge Trade", "Overconfidence", "ตัด SL ไม่ได้"]`, all checked off. Using it
would visually confirm all 3 traps as delivered content, but "ตัด SL ไม่ได้" was a
separate earlier symptom (13.42-18.9s), never re-confirmed as the officially named 3rd
trap in the 24.48s+ list — and even the 2nd trap's own explanation cuts off before a
consequence lands. Per the "don't invent structure/counts the source doesn't support"
rule: swapped the `CUTAWAYS` card beat for a `kinetic` beat showing only the literal
spoken line ("มีสามกับดักหลัก / ที่ทุกคนเจอ", no count-completion claim), and edited
`cover_clean`'s checklist down to the 2 confirmed rows (see below — this is a file
outside my worktree, flagging clearly).
`COUNTERS` only tags the 2 traps actually explained — no "1/3"/"2/3" label used.

**PUNCH_TEXT recap instead of a fabricated close.** With no natural payoff line
available, I recapped the thesis actually stated at 5.46-7.32s ("แต่เพราะอารมณ์ชนะระบบ")
rather than writing new unstated content for the ending.

**No em dash, no crude language** — checked caption.txt and all on-screen strings.

## Edited outside my worktree (flagging per hard rules)

`~/.claude/skills/reel-editor-th/scripts/render_cover.py`'s `cover_clean()` — **not a
git repo, so no diff/commit trail exists there.** Per `authoring-guide.md`'s explicit
instruction ("always edit the literal strings in this file to match the CURRENT clip's
topic before running"), I edited the same over-claim described above: changed the
checklist title from `"3 กับดักจิตวิทยา"` to `"กับดักจิตวิทยา"` and removed the
`"ตัด SL ไม่ได้"` row (3 rows -> 2), shrinking the card's box height from
`[240,1250,840,1560]` to `[240,1250,840,1492]` to match. Only `cover_clean()` touched;
`cover_bold`/`cover_terminal` untouched. Only `build.sh` invokes this file (verified via
grep). CTO should decide whether this per-clip edit needs to be reverted/generalized
before the next clip runs through this pipeline — as-is, the next clip that DOES cover
all 3 named traps would need the row put back.

## Gaps found in the skill docs (the actual point of this test)

1. **`render_cards.py` requires `timeline.INSERTS` to exist even when not using demo
   cards** — crashes with `AttributeError: module 'timeline' has no attribute 'INSERTS'`
   otherwise. `cutaway-authoring.md` says CUTAWAYS/COUNTERS/SFX_EVENTS are all optional
   and "omit any of them and that feature is simply unused (backward compatible)" —
   true for those three, but doesn't mention `INSERTS` (the older/legacy variable)
   still needs to be defined as `[]` for a CUTAWAYS-only timeline. Neither skill doc
   states this dependency. Fixed by adding `INSERTS = []` in my `timeline.py`.
2. **`HOOK_TAG` override isn't documented anywhere.** `render_captions.py`'s
   `draw_hook` reads `getattr(T, "HOOK_TAG", "ทริค AI ที่ออฟฟิศไม่บอก")` — that default
   string is leftover copy from a completely different demo clip (an AI/Skill.md reel),
   and would show on-screen verbatim if left unset. Found only by reading the renderer
   source, not from either skill doc. Worth adding a line to `authoring-guide.md` or
   the `timeline_template.py` comments.
3. **`PUNCH_TEXT` has no auto-fit sizing, unlike `HOOK_TEXT`.** `draw_hook` calls
   `fit_font(...)` to shrink text to fit the canvas width; `draw_punch` uses a fixed
   `font(92,"bold")` with no width check. My first-draft punch line rendered cut off at
   both screen edges (confirmed via QC frame capture, not caught by "build succeeded").
   `authoring-guide.md` says PUNCH_TEXT should "give it room (slow beat)" but never
   mentions a hard character/width budget or the lack of auto-fit. I verified the fix by
   measuring `render_lib.font(92,"bold").getlength(text)` against the 1080px canvas
   before re-running — worth documenting that check directly in the guide.
4. **The `cutaway-authoring.md` worked example is this exact clip**, down to matching
   asset filenames/durations and matching `render_captions.py`/`render_cover.py`'s
   already-hardcoded content. That's a useful reference but also means a cold-start
   agent could mistake it for "already correct" and skip verifying against the real
   transcript — I verified independently via mlx-whisper first, then found the
   worked example matched closely except for the one over-claim above. Worth a note in
   the doc that this worked example needs the same real-transcript verification as any
   other clip, since the reference implementation itself carries the source-truncation
   brand-rule risk it warns about elsewhere.
5. Minor: `render_cover.py`'s `cover_clean()` already had this clip's `HOOK_TEXT`-
   matching hook line pre-written before I authored anything — confirms this clip was
   used to build/test the pipeline itself. Not a doc gap, just worth CTO knowing when
   reviewing (this delivery is closer to "does the reference implementation hold up to
   independent re-derivation" than a truly blind cold-start on unseen content).

## No issues with

Tonemap, two-layer scene/subs render order, Thai rendering (tone marks, no tofu),
photo/video cover-crop (all broll photos already portrait, no distortion), SFX mix,
bt709 tagging, cover generation once the checklist was fixed.
