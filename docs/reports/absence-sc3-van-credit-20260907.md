# SC3 — Carrington Arrival, Credit Lane (2026-09-07)

Task: task-cacab8c6. CEO order 2026-09-07 13:45. Van plate take 4 approved by
CTO at 16:02 ("[CTO] APPROVED — take 4 (project_absence_prop_van_take4.png)
is the van").

## Part 1 — free image plate (van, take 4)

- Image tab → Kling O1 → Unlimited toggle ON → 16:9 → 1/4 → synthetic paste +
  End/space/Backspace bind tap → zoomed GENERATE button confirmed bare
  `UNLIMITED`, zero digits → clicked ONCE.
- "Generation started" toast + new card. Asset count 697→698.
- Credits before/after: 409 → 409 (unchanged, confirmed via account menu).
- Downloaded, saved as
  `docs/prompts/absence/generated/project_absence_prop_van_take4.png`
  (1360x768 PNG). Committed 43a8ac3.

## Part 2 — approval, Element registration, SC3 fire

**(a) Copy to Desktop:** `project_absence_prop_van_take4.png` copied to
`/Users/gob/Desktop/Fix-1-Elements/project_absence_prop_van.png`.

**(b) Element registration:** via the card's detail-modal `...` menu →
"Create Element" (grid hover menu was unreliable, per skill). Name and
Element ID both set to `project_absence_prop_van` via native value setter +
input/change events (coordinate clicks don't bind on these inputs).
"Element created." toast confirmed. Verified it resolves: pasted the SC3
prompt and all 4 `@`-mentions bound as lime chips, including
`@project_absence_prop_van` — 4/4 bound, 0 error chips.

**(c) `git merge main`** — already up to date, no new commits.

**SC3 fire (credit lane):**

- Prompt-lint clean (`scripts/prompt-lint.py --shot SC3` and `--chips`,
  4 expected chips, all matched).
- Composer: Video tab → Seedance 2.5 (switched from default Cinema Studio
  4.0) → 16:9 → 720p (was 1080p) → 8s (ARIA slider, ArrowRight x3 from 5)
  → High → Sound On → Unlimited toggle OFF (confirmed `aria-checked=false`)
  → batch 1/4.
- Prompt pasted via synthetic ClipboardEvent + End/space/Backspace bind tap.
  4/4 chips bound: `@project_absence_loc_exterior_front`,
  `@project_absence_prop_van`, `@gentleman_e`,
  `@project_absence_char_guard_private_v2`. No previz attached (none exists
  for this shot, per brief).
- Generate button read `GENERATE · ~~56~~ 52` — zoomed and confirmed visually
  (matches the brief's "~52 credits" exactly).
- Credits before: 409 (last confirmed reading, right after Part 1 — no other
  paid action happened between then and the fire; Element creation is free).
- Clicked Generate ONCE. "Generation started" toast + new processing card.
  Asset count 698→699. **No "protected-content" toast appeared** — all 4
  chips fired as staged, no fallback to prose needed.
- Credits after: **357** (confirmed via account menu, Credits "357 left").
  409 → 357 = **-52**, exactly as the brief predicted.

## Render / identification

- Polled every ~10 min with a fresh tab (open → check → close), per brief.
- Render finished within ~20 min of firing.
- Identified via Info panel: prompt text matches the SC3 sheet exactly
  ("8s · 720p · 16:9 · TWO SHOTS, one hard cut at 3s..."), Model
  `Seedance 2.5`, Quality `720p`, Bitrate `High`, Size `1280x720`, Created
  `September 7, 2026 at 4:14 PM`.

## Download & verification

- Downloaded: `hf_20260907_091434_7a48673e-3322-43fc-938b-7203459cbc5a.mp4`
  (7.7 MB / 8,031,982 bytes).
- md5: `ef12add6c7127ac6e7b05f08668a7082` — checked against every other .mp4
  in `~/Downloads` via Python (chunked md5), **no duplicates found**.
- ffprobe: `codec_name=h264, width=1280, height=720, duration=8.041667s` —
  matches spec (8s, 1280x720).
- Frames extracted at 1s and 6s → `docs/reports/frames-sc3/sc3-1s.png`,
  `docs/reports/frames-sc3/sc3-6s.png`. **No verdict given** — the CEO
  reviews this clip himself, per the sheet's own note.

## Filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` to
`All Scene/Fix-1/SC3-Carrington-Arrival-Credit.MP4`:
<https://drive.google.com/file/d/1Qqe4jDOM0b2yTC_TPcLqHdphlRU97Vy6/view>
(7.7 MB). Logged to the project's `logs.txt` by the script.

## Credits summary

| Checkpoint | Balance |
|---|---|
| Before Part 1 (image plate) | 409 |
| After Part 1 | 409 |
| Before SC3 fire | 409 |
| After SC3 fire | **357** |

Total spend this task: 52 credits (SC3 only; the image plate was free
Unlimited).

## Notes

- Zero other paid actions taken. Never touched a `SEEDANCE 2.5 CREDIT` card
  belonging to the CEO.
- Screenshot capture (`Page.captureScreenshot`) intermittently timed out on
  both tabs used this session while `document.readyState` stayed
  `"complete"` and JS execution kept working — worked around by driving the
  composer entirely via `javascript_tool` reads/writes and `find()` refs,
  falling back to `zoom`/`screenshot` only when it recovered. No data lost;
  every money-gate check (price, chip count, settings) was independently
  confirmed via DOM before the fire.
- Tab hygiene: every tab claimed via `tab_registry.py claim`, released via
  `done` before closing, per the two-tab cap in the task brief.
