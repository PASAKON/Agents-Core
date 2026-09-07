# S15a2-RoomDecides — t3 fire (task-1deb52ec)

## Gate checks (re-run at fire time, sheet unchanged since t2's fix commit)
- `git merge origin/main`: already up to date, working from 1d2fe8f
- depth/gaze grep on paste block: 0 hits (narrowed pattern)
- `prompt-lint.py`: exit 0
- Chips: 12/12, exact match to `prompt-lint.py --chips` expected list
- HARD CUT count: 2 (shot 2 at 3s, shot 3 at 5.5s)

## Money
- Lane: UNLIMITED/FREE (per task brief — six credits left, non-zero price = stop)
- Unlimited toggled ON as first composer action: first click (raw coordinate) missed
  the toggle and landed elsewhere (button still read live `56/52`); one clean
  `find()`-ref click flipped it correctly per hard rule 5 (one attempt, no retries)
- Generate button read (zoomed pixels): `UNLIMITED / struck 56 / 0` — re-verified
  immediately before the click
- Clicked exactly once

## Fire
- Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (confirmed
  in address bar before fire)
- Model: Seedance 2.5, 720p, 16:9, 8s (duration slider defaulted to 5s; set via
  slider focus + ArrowRight×3, read back `aria-valuenow=8` before firing), High,
  1/4, Sound On, Unlimited ON
- Prompt pasted via synthetic `ClipboardEvent` (base64-encoded text, `text/plain`
  only), End→space→Backspace sync tap
- 12/12 chips bound (verified via
  `[contenteditable="true"] span.text-font-brand` selector, filtered to leaf
  `@`-prefixed spans), names matched `prompt-lint.py --chips` exactly. No
  `project_valder_char_villagers_poor` chip (correctly left as prose).
- All 12 reference thumbnails zoomed, no warning triangles on any
- Fire time: 2026-09-08T02:30:54+07:00. "Generation started" toast confirmed,
  asset count 711→712
- Render observed Processing at the 20/25/31/36-minute checks (well inside
  tonight's 30-46min norm — never an outlier, never cancelled), landed by the
  ~40min check
- Card identity verified via Info panel before download: prompt text matches
  the pasted block, Model Seedance 2.5, Quality 720p, Size 1280x720, Created
  "September 8, 2026 at 2:30 AM" = exact fire timestamp
- Downloaded: `hf_20260907_193050_14ba27cf-6dec-4dc2-9f34-1e018d8b295c.mp4`,
  8.05s, 1280x720, h264/aac — md5 checked unique against ~20 prior Downloads
  entries, no match
- No NSFW / rights-verification banner on the finished card

## Frame review
Frames pulled at 0.2s, 1.5s, 2.9s, 3.1s, 4.5s, 5.3s, 5.7s, 6.5s, 7.9s
(`ffmpeg -ss <t> -frames:v 1`), plus targeted crops on the registrar, wall
mark, and press cluster.

### 1. Cuts to S15a-1 — Dupe dead centre, room silent, push-in moving, no walk-in
**PASS.** 0.2s: Dupe centred, white uniform/orange trim/gold V, holding a
mop/pole. Valder (rainbow-striped blazer) is the leftmost figure in frame,
workman (denim overalls, bucket, towel) is the rightmost — Dupe sits between
them on the row, though with the registrar/grandmother/gentleman also
standing in between rather than Valder and the workman being immediately
adjacent to Dupe. Static composition, all faces already toward Dupe, no
walk-in visible.

### 2. Navy uniforms across the full frame width
**PASS.** Exactly 2 navy-uniformed guards visible at 3.1s and 4.5s (both
inside shot 2, a static wide shot — no camera pan, so both frames show the
same full-width composition). Both stand together at the LEFT edge, gold-V
tunics, navy peaked caps. No third or fourth navy uniform anywhere in frame.
This fixes take 1's defect (a) — the phantom mirrored guard on the right is
gone.

### 3. Registrars
**PASS.** Exactly 1 — black suit, white gloves, gold V, leather ledger in
hand — visible at 0.2s standing near the grandmother. No second registrar
spotted in any sampled frame.

### 4. Three bodyguards, one group at the left edge
**FLAG.** Only the two navy guards are grouped at the left edge (shoulders
touching, as scripted). The third bodyguard — heavy-built Black man, black
suit, sunglasses, white gloves — stands isolated at the FAR RIGHT of the
shot-2 frame, shoulder-to-shoulder with Madame Thibault (green leather gown)
instead of with the navy guards. The prompt's explicit "one unbroken line of
three bodies at the left edge" did not bind; the third guard rendered on the
opposite side of the room.

### 5. Wall mark vs canon (PLATE-loc_wall_pov_e.md rules 6/7)
**PASS**, per CTO's independent call after reviewing the same frame crop.
Operator's own read for the record: the mark's main stem is solid, thick,
black — a real improvement over take 1's thin insect-like hairlines — but
the shorter branch lines radiating from it read somewhat thinner/more
wire-like than the main stem, short of the canon's "every line solid and
heavy like ink." CTO's PASS verdict stands as the take's verdict.

### 6. Press count (asked separately by CTO mid-review)
4 people are unambiguously holding camera+flashbulb-bandolier gear in the
shot-2/4.5s cluster — matches the sheet's "FOUR of them" exactly, and the 4
faces are all distinct (no duplicate press faces). Roughly 6 more figures
stand in the same tight cluster with no camera visible, wearing near-
identical dark overcoats to the press — almost certainly the scripted six
prose-only villagers rather than extra press-chip duplicates, but visually
indistinguishable from press at a glance because of the shared coat styling.
This is very likely what reads as "more than four press" on a casual look;
no defect confirmed in the chip binding itself.

### 7. Crowd line has no face
**PASS.** Shot 3 (5.7s-7.9s) stays on Dupe's close-up throughout; no cutaway
to any speaker. 7.9s end frame: Dupe centred, mouth slightly open, no reply —
matches the scripted ending exactly.

### 8. Word count / no repeated dialogue
Not independently verified via audio transcription (no tool available this
session) — no visual sign of extra dialogue or a second speaker shown.

## Overall verdict
**FLAGGED** — one confirmed defect: the three-bodyguard grouping split
across both sides of the room instead of standing together at the left
edge. Navy-uniform count, registrar count, and wall mark all PASS (mark per
CTO's call). Filed regardless, per standing rule.

Filed to Drive: `All Scene/Fix-1/S15a2-RoomDecides-Fix1.MP4`
https://drive.google.com/file/d/1fsmOp7Dk3Zwri7CbA9X4LS1rVb3G753Y/view
