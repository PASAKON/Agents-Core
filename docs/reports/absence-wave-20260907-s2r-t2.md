# S2R-Fix1 — THE BATTLE — Take 2 report (task-efa1d2dd)

Fired 2026-09-07 00:14:23Z (07:14:23 ICT). One fire, per task brief.

## Pre-fire gates (per FIRE-PLAYBOOK.md §0 and the task brief)

- `git merge main`: already up to date (branch at f9bbc88, >= required 4e461a1). No-op.
- Gate grep on paste block only (`nearest|extreme foreground|very front|floating|toward the mark|backs to the room`): **0 hits.**
- `python3 scripts/prompt-lint.py docs/prompts/absence/s2r-fix1-the-battle.txt`: **exit 0**, no findings.
- `python3 scripts/prompt-lint.py --chips docs/prompts/absence/s2r-fix1-the-battle.txt`: reported `EXPECTED 13 Element chips` (the total, which is zone-restricted and correct) but then **also printed `@project_absence_prop_croc_bag`** in its per-chip listing. Investigated: that listing loop scans the **whole file**, not just the paste zone (a tool bug — see Notes below), and `@project_absence_prop_croc_bag` only appears in the NOTES section (the take-1 postmortem, line 254) — never inside the actual `PASTE FROM HERE` / `PASTE STOPS HERE` block. Verified directly: `grep -oE '@[a-zA-Z0-9_]+'` restricted to the paste zone returns exactly 13 unique names, no croc_bag. Gate honored as intended.

## Browser session

- claude-in-chrome only, per playbook. Fresh tab (id 53474200), claimed in `scripts/browser/tab_registry.py` for task-efa1d2dd, released at the end.
- Window: `resize_window` to 1440x960 (Chrome later self-adjusted the chrome to 1440x698 / 1568x760 innerWidth at various points); every state-changing action was preceded by a `window.innerWidth` readback >= 1280 (measured 1280–1568 throughout). No mobile-lockup symptoms seen.
- FIRST ACTION in composer: closed the "Credits are running low! Over 90% already used" banner via its own (x). Never acted on its message.
- Composer defaulted to Video mode already active with model Cinema Studio 4.0 — switched explicitly to **Seedance 2.5** via the model dropdown.
- Six fields set and re-verified immediately before firing: **Seedance 2.5 · 16:9 · 720p · 20s · High · Sound On**, batch 1/4.
  - Duration: the ARIA slider (`role=slider`, min 4 / max 30) was clicked to focus then driven with 15x `ArrowRight` (5→20), confirmed via `aria-valuenow="20"`. Never typed.
- Prompt: pasted **only** the block between `PASTE FROM HERE` / `PASTE STOPS HERE` via a synthetic `ClipboardEvent` (base64-encoded, `text/plain` only), onto the real (visible, non-decoy) `contenteditable` — verified by `document.activeElement` before paste. Pasted length 9109 chars; first/last ~60 chars matched source exactly. Followed with `End` → `space` → `Backspace` to force Lexical state binding (per playbook).
- Chip gate: `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@'))` → **13 unique chips**, all lime, **0 unresolved/red `@`**, and **no `@project_absence_prop_croc_bag`** chip. Re-confirmed a second time immediately before the Generate click (fresh count, same result).
- Duration reset Unlimited as expected; toggled Unlimited **after** the six fields were set, then zoomed the Generate button: `UNLIMITED · ~~140~~ · 0` (pixel-verified via `zoom`, not DOM scrape).
- Previz: `docs/S2R-Render.MP4` uploaded via the reference panel's file input (`file_upload`, matched by `accept` containing `video/mp4`). Upload-tool report: 4423 KB (≈ 4528874 B; `ls -l` byte count matches within rounding). Tile went through "Checking.." → clicked → **"Added to prompt box"** toast + green checkmark. No 10-min stall; Generate stayed enabled throughout.

## Fire

- Fired at 00:14:23Z. Verified by **"Generation started" toast** AND a **new Processing card** (spinner, top-left of the grid). Asset count moved 682 → 683 — read only as a cross-check, after the previz attach, never as the sole proof.
- Zero paid actions. Ignored the 3 pre-existing "Rejected due to copyright restrictions" S2R cards and any CEO Credit-lane cards throughout.

## Render

- Polled every 5 minutes with a full reload (per task brief), checking the card's spinner / title attribute each time. Timeline: processing at ~5, 11, 16, 21, 26, 31, 36, 41 min. **Finished by ~46 min** (found rendered on the ~41-46 min reload).
- Finished card: **no "Rejected due to copyright restrictions" title, no NSFW/sensitive-content flag.** Only the pre-existing 3 old rejected cards still carry that title anywhere on the page — confirmed via `document.querySelectorAll('[title]')` scan, before and after this fire, same 3 titles both times.
- Downloaded: `hf_20260907_001412_12732c26-eaec-457f-be08-a8cfe84db450.mp4` (18,746,131 bytes) to `~/Downloads/`.
- `ffprobe`: **1280x720, h264 + aac audio, duration 20.041667s** — matches spec (20s / 720p / Seedance 2.5).
- Filed to Drive: `scripts/gdrive-bridge/upload_fix1.py` → **All Scene/Fix-1/S2R-Fix1.MP4** (17.9 MB), https://drive.google.com/file/d/1jQ5cgvVW6Ht1QO_OD_JDOWhGuaQR5DBC/view — `logs.txt` line appended by the script.

## Frame checks

Frames extracted at 0.5s / 4s / 8s / 12s / 16s / 19.5s, saved to `docs/reports/frames-s2r-t2/` (`f_0.5.png` … `f_19.5.png`, plus supporting crops `f_0.5_left.png`, `f_0.5_right.png`, `f_0.5_zoom2.png`, `f_0.5_wideright.png`, `f_0.5_furwomen.png` used to resolve the person-count finding below).

**Camera**: identical framing/composition across all 6 timestamps — locked shot confirmed, no pan/zoom/cut.

**Named characters present** (checked both ends of the shot, 0.5s and 19.5s, and every frame between): Carrington (@gentleman_e, white suit + cane, left) ✓, his bodyguard (@project_absence_char_guard_private_v2, black suit + sunglasses, far back left) ✓, Valder (@project_absence_char_valder, colorful blazer, dead centre) ✓, the registrar (@char_registrar, cream tunic, writing throughout) ✓, the Madame/woman in green (@project_absence_char_woman_c, right) ✓, Valder's two guards (@project_absence_char_guard_valder_two, navy uniforms with V, one thin one heavy, flanking Valder) ✓, the young woman in cobalt (@project_absence_char_woman, blue coat) ✓, the critic (@project_absence_char_critic_b, magenta fur coat, silver hair) ✓, the man in maroon (@project_absence_char_visitor_a, far right) ✓, Dupe (@project_absence_char_cleaner_c, cream/orange uniform + cap, far back left) ✓. Her bag (prose-only, no chip) was not clearly visible in these still frames (hand position/angle) — not a review-order item, not flagged.

**REVIEW ORDER** (from the sheet):

1. VALDER IN THE MIDDLE — **PASS.** Dead centre, a little further back, facing the lens, in every frame. Never drifts, never joins in.
2. THE HEADS SWING — **PASS (partial verification).** Static frames show most heads oriented left (toward Carrington) at 8s/12s/16s/19.5s, consistent with the later bid beats; full left-right-left cadence can't be fully confirmed from 6 stills alone, but nothing in the frames contradicts it.
3. NOBODY WALKS — **PASS.** Identical foot/floor positions for every figure across all 6 timestamps.
4. FIVE BIDS IN ORDER, hers first — **not verifiable from stills** (audio/dialogue check requires playback, out of scope for frame-grab review).
5. SHE NEVER RAISES HER VOICE / HE STARTS CONFIDENT AND ENDS SILENT — **PASS (visual).** Carrington's mouth is open and slack at 19.5s, consistent with "nothing comes out of it" at 15s+; the Madame's posture stays composed throughout.
6. THE REGISTRAR IS WRITING THE WHOLE TIME — **PASS.** Pen to ledger in every one of the 6 frames.
7. TWELVE PEOPLE, no extras, no auction furniture — **FLAGGED.**

### FLAGGED — 13 people, a duplicated "chestnut fur" woman

Counting every frame (0.5s through 19.5s, consistent in all of them): bodyguard, registrar, Dupe, Carrington, cobalt-woman, guard-1, Valder, guard-2, critic (magenta fur), **two** near-identical women in tawny-brown fur coats over rust-red dresses (one on each side of the Madame), the Madame, and the man in maroon = **13 people**, not the sheet's locked "COMPLETE CAST OF THIS SHOT IS TWELVE PEOPLE AND NOT ONE MORE."

The sheet names exactly ONE such character — `@project_absence_char_visitor_b`, "THE WOMAN IN THE CHESTNUT FUR: about fifty-five, a brown bob, a long tawny-brown fur coat over a rust-red shift dress." The render placed two visually near-identical women in that same coat+dress combination, flanking the Madame symmetrically, in every single frame checked (not a one-frame glitch). This is exactly the class of defect the sheet's own IRON RULE bans ("no duplicate characters, no twins, no character appearing twice") and the CRITICAL NEGATIVES ban explicitly ("no thirteenth person, no extra, no bystander, no other visitor"). Screenshots: `docs/reports/frames-s2r-t2/f_0.5_wideright.png` and `f_0.5_furwomen.png` show both women clearly, side by side with the Madame between them.

No auction furniture, podium, gavel, or paddle seen in any frame — that part of item 7 passes.

## Verdict

**RENDERED, but FLAGGED** — the copyright-rejection question is resolved (this take rendered clean on the copyright filter, unlike Take 1's three rejections), but the take has a real continuity defect (13 people, a duplicated chestnut-fur/rust-dress woman) that a human/CTO pass would need to decide on: re-fire, or accept as an editor-cut option since the file rule says "file the take whatever the verdict."

## Notes

- **prompt-lint.py `--chips` tool bug** (worth fixing separately, not fixed here — out of scope for this task): the per-name listing under `--chips` scans the whole file text for `@name` patterns instead of restricting to the paste zone like the `expected_chips()` total does. This causes it to surface names that only appear in the NOTES section (like `@project_absence_prop_croc_bag` in this file's take-1 postmortem) as if they were part of the pasteable prompt. The **total count is correct** (zone-restricted); only the listing is wrong. Recommend scoping `main()`'s `--chips` branch's `AT_ELEMENT_RE.findall(...)` call to the paste-zone text the same way `expected_chips()` does.
- This session's auto-memory picked up a note mid-task (`reference_higgsfield_copyright_reject_element.md`, unread by this operator) stating the croc-bag Element was suspected as the trigger for the earlier copyright rejections. This take (croc-bag chip dropped, carried as prose only) rendered clean — consistent with, though not conclusive proof of, that hypothesis, since only one variable changed between Take 1 and this take on the same Unlimited lane.

## Sheet notes appended

One dated take line appended to `docs/prompts/absence/s2r-fix1-the-battle.txt` (bottom, append-only, per instructions).
