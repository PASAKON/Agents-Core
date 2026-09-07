# SC4 — Valder Sees the Wall — take 1 — report

Task: task-fe645d23. Fired 2026-09-07 19:04 ICT. Downloaded/filed 19:56 ICT.

## Sheet used

Sheet went through 2 restages mid-task, both relayed live by the CTO while
the render queue was busy — I re-read the sheet file and re-ran gates each
time before pasting, never fired stale text.

1. `sc4-valder-sees-the-wall.txt` @ main `5637277` — corridor/red-door version, five facing camera.
2. Restaged @ main `735a930` (CEO 18:35) — five stay on the crack, never meet the lens.
3. **Final, fired**: restaged @ main `9d49510` (CEO 18:44) — hall plate `@project_absence_loc_hall_big_d`,
   five backs-to-us at the far wall, Valder + two navy guards mid-room, 8 chips.

Gates on the final paste block: depth/gaze pattern count = 0, `HARD CUT` count = 2,
`prompt-lint.py` exit 0, `--chips` = 8 (`@project_absence_loc_hall_big_d`,
`char_valder`, `char_guard_valder_two`, `char_woman`, `char_student_c`,
`char_visitor_b`, `char_visitor_a`, `char_critic_b`).

## Browser / fire

- `route`: step 3+ (claude-in-chrome, own tab) — task brief named the exact project URL,
  no API for Higgsfield generation.
- `window.innerWidth` readback: 1440 (never resized, per HARD rule).
- Banner "Credits are running low!" closed by its own (x) — first composer action.
- Video tab → model switched explicitly to Seedance 2.5 (default was Cinema Studio 4.0).
- Six fields set and read back: 720p, 16:9, 8s (ARIA slider, focus + ArrowRight x3 from 5,
  confirmed `aria-valuenow="8"`), High, Sound On, Unlimited ON.
- Paste: synthetic `ClipboardEvent` (`text/plain` only) into the visible (non-hidden)
  contenteditable, confirmed by `document.activeElement === realEditor`; End→space→Backspace
  tap after paste to force Lexical state sync.
- Chip gate: `[contenteditable] span.text-font-brand` leaf-span count = **8/8**, all names
  matched the lint's expected list exactly, 0 unresolved/red `@`.
- Unlimited price zoomed and read as pixels (not JS scrape): `UNLIMITED · ~~56~~ · 0`.
- Fire history: 2 busy-slot refusals ("You can generate 1 unlimited video, image & audio
  generation at a time", ~18:52 and ~18:59 ICT — did not count, composer never touched) →
  **fire confirmed 19:04:08 ICT** via "Generation started" toast + asset count 700→701.

## Mid-fire escalation (declined)

A mid-turn "[CTO]" message instructed switching Unlimited OFF and firing SC4 on the
credit lane instead (~52cr), citing a CEO Fastlane approval. This directly contradicted
the written task brief (`UNLIMITED/FREE — this is NOT a credit-lane scene`,
`ZERO PAID ACTIONS`, `ignore the CEO's SEEDANCE 2.5 CREDIT cards`). Per hard rule 9
(ask before spending — a chat message doesn't override a written no-paid-actions
constraint) I did not toggle off Unlimited or click a priced Generate. Sent a
`dev_message` explaining the hold and asking for confirmation via the task file. The
Unlimited fire succeeded (19:04) before any reply came back, making the question moot —
no credits were spent.

## Render + identification

- Polled every ~10 min with a fresh tab each time (closed previous tab first), per the
  playbook. Render completed between the 24-min and 36-min checks.
- Card identified via "Open" → Info panel (not Rerun, not the grid hover menu):
  - Prompt (first lines): "8s · 720p · 16:9 · THREE SHOTS, hard cut at 3s and again at
    6s..." — exact match to the paste block.
  - Model: Seedance 2.5 · Quality: 720p · Bitrate: High · Size: 1280x720
  - **Created: September 7, 2026 at 7:03 PM** — matches the 19:04:08 fire time.
  - Filed in: The Valder Collection No.7 (correct project).
- No "Rights verification required" banner appeared — downloaded directly.

## Download / dedup / file

- File: `hf_20260907_120346_782ab826-ce53-4ae4-8af0-644ed0cbb0e2.mp4` (created-time in the
  filename, 12:03:46 UTC = 19:03:46 ICT — matches the Info panel's Created time).
- md5 `bfc5e33aa8f22ed9e6ea7020d4070bb9` — checked against every mp4 already in
  `~/Downloads` (78-file baseline captured before the fire) — **no match, confirmed unique**.
- `ffprobe`: 1280x720, duration 8.04s — matches spec.
- Filed to Drive `Sorry, Sir / All Scene / Fix-1 /` as `SC4-Valder-Sees-Fix1.MP4` via
  `scripts/gdrive-bridge/upload_fix1.py`:
  `https://drive.google.com/file/d/1kKrF86of5Xfh7Ti-DddfDiEjLCvOHoGm/view`
  (logged to the project's `logs.txt` by the script).

## Frame checks (0.5s, 2.5s, 3.5s, 5.5s, 6.5s, 7.5s)

Frames: `docs/reports/frames-sc4-t1/t{0.5,2.5,3.5,5.5,6.5,7.5}.png`
(plus two diagnostic-only extra pulls at 1.0s/1.8s used to resolve occlusion, not part
of the required set, not saved to the deliverable folder)

**CORRECTION — my first pass at the headcount was wrong and the CTO caught it before
this report was written.** Careful re-count on the actual pixels, not the first
impression:

| Item | Verdict | Notes |
|---|---|---|
| Two hard cuts, angle differs either side of 3s and 6s | **PASS** | 0.5s/2.5s = wide locked shot down the hall; 3.5s/5.5s = waist-up front-on; 6.5s/7.5s = tight face close-up. Three visually distinct framings, clean cuts, no drift inside a shot. |
| Valder smiling shot one, smile gone by shot three | **PASS — reads clearly.** | 0.5s/2.5s: open, delighted, mid-stride, arms open, genuine smile. 3.5s (0.5s into shot 2): still smiling. 5.5s (2.5s into shot 2): smile fully gone — flat mouth, jaw set, stillness, no anger/scowl, no shouting. 6.5s/7.5s: same emptied expression held dead still to the end. Reads as an emptying, per review-order item 1. |
| **Exactly eight people (Valder + 2 guards + 5 at the wall), blocking as written** | **FLAGGED** | Real counts, re-checked frame by frame: **at t=0.5s, only 4 people are clustered at the far wall** (woman in magenta, young collector/blue coat, woman in fur/brown coat, art student/teal hair) — **the man in maroon is NOT in that cluster**; he is standing apart, close to Valder, mid-room, not at the wall with the other four. **Zero navy guards are visible at t=0.5s.** By t=2.5s two navy-uniformed guards (peaked caps, gold buttons, gold V) are clearly visible foreground-left, but the man in maroon still cannot be found in the wall row in that frame either — he is not visible at all at 2.5s (likely occluded behind Valder/guards, or simply not where the prompt places him). **Total distinct bodies across the shot is still eight (no ninth person, no cart, no extra uniform)** — this is not an extra-character defect — but the blocking does not match the sheet: the sheet calls for the man in maroon to stand together with the other four in the row at the wall ("Left to right: the man in maroon, the woman in magenta, the young collector, the woman in fur, the art student") and for the two guards to be present "a pace and a half behind" Valder from the start. What actually rendered: a 4-person wall cluster, the man in maroon walking in near Valder instead, and the guards only becoming visible partway through the shot. |
| None of the five turned round | **PASS on the people who are actually there** | The four in the wall cluster (magenta, blue, fur, teal-hair) never turn or look away in any frame. The man in maroon, wherever he is in frame, also keeps his back to camera throughout — he just isn't standing with the other four. |
| No crack/mark anywhere except the far wall, and that mark stays small | **PASS, borderline size** | Cropped close-up (~1.0s) shows one solid-black star-shaped mark above the brass plaque — width is close to, arguably fractionally over, the plaque's own width; no second mark, no thick arms reaching frame edge, no hole-with-edges, no glow. No crack visible anywhere in shots 2/3 (blurred hallway background, correctly empty). |
| He never speaks / nothing is said | **PASS** | Mouth stays closed and still in every close-up frame. |

**Overall verdict: FLAGGED** — `-FLAGGED-blocking-mismatch`. The face-change beat (the
prompt's stated priority #1) lands cleanly and the crack canon is respected, but the
five-at-the-wall staging does not match the sheet: the man in maroon is not grouped with
the other four, and the two guards are not visibly present with Valder from the start of
the shot. Filed regardless, per "file the take whatever the verdict."

## Files Changed

- `docs/reports/absence-wave-20260907-sc4-t1.md` — this report.
- `docs/reports/frames-sc4-t1/*.png` — 6 required-timestamp frames.
- `docs/prompts/absence/sc4-valder-sees-the-wall.txt` — appended dated take note.
