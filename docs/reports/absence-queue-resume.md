# «Sorry, Sir» — queue resume (task-9ba8e06b)

## Worktree was stale — fast-forwarded to main

This worktree's branch was pinned 61 commits behind `main` (created before a
long stretch of same-day checklist/prompt updates landed). `docs/prompts/absence/`
was missing `s7-s9.txt`, `s6-s18.txt`, `s4-s5.txt`, `DIALOGUE.md` entirely, and
`CHECKLIST.md`/`VALDER.md`/the skill were stale. Read everything from `main`
via `git show main:<path>` (read-only — the self-repo-guard hook correctly
blocked a full `git reset --hard main` since this task's declared touch is only
`docs/reports/absence-queue-resume.md`). Flag for CTO: this worktree's branch
still needs a real sync/merge before it can safely carry commits beyond this
one report file.

## COLLECT — S7 and S8a

**S8a — COLLECTED.** Asset `5cdfc192-93a0-46d8-a62f-67508935daea`
(`hf_20260828_070257_5cdfc192-93a0-46d8-a62f-67508935daea.mp4`). Confirmed via
Details panel: Seedance 2.5, 720p, 1280x720, created Aug 28 2026 2:02 PM. No
rights-verification banner present. Downloaded, ffprobe-verified 1280x720 /
20.04s exact match to spec. Reviewed shot-by-shot via extracted frames:
establishing shot (Valder centre, gentleman in white suit left, woman in
cobalt, staff member right, Gold-V cap correct), the mustard swivel chair on
the blue rug, the woven fish-trap hanging form, the stone millstone ring on
its plinth — all three pieces match the prompt precisely, no defects seen.
Copied to Drive `All Scene/S8a/`, byte-exact verified, local copy deleted (see
below).

**S7 — NOT collected. Real defect found: it's 480p, not 720p.** Asset
`1a50c388-b55b-4992-8015-91ebd8395793` — confirmed via Details panel: Seedance
2.5, **480p, 854x480**, created Aug 28 2026 1:16 PM. This is the only asset
carrying that id (verified via `[data-asset-id="..."]` exact match, not a
substring/decoy match — I hit that decoy trap once on a different card first
and want to flag it: a thumbnail's `img[src]` can substring-match an unrelated
asset id; only `data-asset-id` and the opened preview's own UUID are
trustworthy). No rights-verification banner present on this card either — it
appears to have cleared itself, consistent with what the CTO found in a
separate tab.

This contradicts the checklist's claim that S7 "take 1 LANDED... at a true
20s... first correct duration since S3" (implying 720p, since 720p had just
been made a hard gate). Given the documented "composer silently resets its
settings" trap (resolution can revert same as the Unlimited toggle and
duration slider), I believe this take rendered off-spec without anyone
noticing at the time. **Per the CEO's standing rule ("480p was rejected...
Re-fire, discard the 480p take" — same treatment already applied to S8a),
I did not download it.** It needs a re-fire at 720p. Filed as part of the
blocker below since S7 also needs the gentleman reference, which is currently
dead.

## BLOCKER FILED — char_gentleman_c terminal Face/IP failure

GitHub issue: https://github.com/PASAKON/MoonieX-Agents/issues/119

`@char_gentleman_c` (the shipped v3 solo-portrait gentleman, no prefix) now
shows "Face/IP failed — ... cannot be used. Try another." with no re-check
button — the terminal state, not the transient pending-recheck kind (which I
cleared successfully on two other refs this session via "Check eligibility").
This is the second time this exact element has died today per the checklist's
own record.

**Blocks:** S7 (re-fire), S8b, S8c, S10, S6, S12, S15 — all reference
`char_gentleman`/`char_gentleman_c` directly.

**Not blocked, fired instead to keep the slot busy:** S5, S16 (neither scene's
reference list includes the gentleman).

I did not generate a replacement gentleman myself — that's a character/
continuity call, and there's a live alternate (`@gentleman_e`) but the
checklist explicitly describes it as a "deliberately different face" decoy,
so silently substituting it would change the character's face across six
scenes without anyone deciding that. Left to CTO/CEO.

## FIRED

All fires used Seedance 2.5 · 720p · 16:9 · High · Sound On · Unlimited
(verified struck-price-then-0 via zoom immediately before each click) ·
duration confirmed via the ARIA slider's `aria-valuenow` + visible label
before firing.

**S5 — FIRED**, 20s, references (10, all bound clean, no red/dead refs):
`loc_hall_big_d`, `char_woman`, `char_critic_b`, `char_oldman`,
`char_student_c`, `char_visitor_a`, `char_visitor_b`, `char_press_a`,
`char_press_b`, `char_cleaner_c`. Two refs (`char_press_a`, `char_press_b`)
showed the transient "needs an eligibility check" warning on attach — cleared
via "Check eligibility" before firing, per the skill's documented benign case.
Asset id not yet known — card still "Processing" as of this report; will
follow up.

**S16 — STAGED, not yet fired** (waiting on S5's render slot). 20s, 6
references bound clean: `loc_hall_big_d`, `char_valder`, `char_press_a`,
`char_press_b`, `char_guard_valder_six`, `char_cleaner_c`. Will re-verify the
zero-digit price and reference count fresh at the moment of firing, not reuse
this check.

## Element-name mapping used (confirmed against the live Elements panel,
`?elements=1`, not from docs — several docs disagree with each other)

- `char_gentleman` in scene text → `@char_gentleman_c` (no prefix) — DEAD, see
  blocker above
- `char_guard_valder` in scene text → `@project_absence_char_guard_valder_six`
  (no plain `char_guard_valder` element exists — only `_six` and `_single`
  variants)
- `char_press` in scene text → BOTH `@project_absence_char_press_a` AND
  `@project_absence_char_press_b` (per task brief instruction — the base
  `char_press` element is dead)
- Everything else maps straightforwardly to `@project_absence_<name>`

## Downloads

Copied `hf_20260828_070257_5cdfc192-93a0-46d8-a62f-67508935daea.mp4` (S8a) to
`~/Library/CloudStorage/GoogleDrive-pass.gob1@gmail.com/ไดรฟ์ของฉัน/ALL DRAFT/
YT: ILAG/Sorry, Sir/All Scene/S8a/`, verified byte-exact (md5 match), then
deleted the local `~/Downloads` copy.


## S5 asset id — committed before download

Asset `34b813c5-4bcc-4697-b828-e987dd7a29fd`, Seedance 2.5, 720p, 1280x720,
created Aug 28 2026 3:13 PM. Downloading next.

## CORRECTION — S5's real asset id

The `preview=` URL query param (`34b813c5-4bcc-4697-b828-e987dd7a29fd`) is NOT
the downloadable asset id — clicking Download produced a file carrying a
DIFFERENT id (`db2fc877-c30d-4357-a105-f9f6c2e43a6c`), and that id's embedded
timestamp (`hf_20260828_081312...` = 08:13:12 UTC = 3:13:12 PM ICT) matches
the "Created August 28, 2026 at 3:13 PM" shown in the Details panel exactly.
**S5's correct asset id is `db2fc877-c30d-4357-a105-f9f6c2e43a6c`**, not the
id in the previous entry. ffprobe-verified 1280x720 / 20.06s. Same decoy-id
family as the earlier substring-match trap — the `preview=` query param is a
navigation/job id, not the asset id; only the downloaded filename or a
verified `data-asset-id` DOM attribute can be trusted.

## S5 — COLLECTED

720p/1280x720/20.06s confirmed via ffprobe. Reviewed shot-by-shot via extracted
frames: the woman in cobalt (tall, dark cat-eye sunglasses, hair up, one
saturated cobalt-blue leather outfit) stands centred in the hall, room arced
around her — critic in dark green coat, journalist with a retrofuturist
shoulder camera behind her, others in maroon fur, teal coat, rust jacket, one
in burnt orange. Staff figure in white uniform visible mid-background
(Dupe/cleaner). Matches the prompt closely. **Minor, not flagged as a
defect:** only one journalist figure is clearly visible in the frames I
sampled, not both char_press_a/char_press_b distinctly — plausible they're
positioned close together per "a single shared camera between them," but
worth a second look if the CEO wants to check. No hard defects. Copied to
Drive `All Scene/S5/` (new folder, created), byte-exact verified, local
deleted.

## New CEO instructions received mid-session, several via truncated relays

Reconstructed from a mix of full and partial chat deliveries plus files
dropped directly into the worktree (`s2-accident.txt`, `s3-interpretations.txt`,
`s1-angles.txt`, `s13-the-back-door.txt`, updated `s7-s9.txt`):

- **char_critic_b now needs "fluent English with a Chinese accent" stated in
  every prompt she appears in.** Applied from S2 onward (too late for S5).
- **S9 gets re-shot**: Valder + the four who spoke are now visible deep
  background, thrown out of focus, per updated `s7-s9.txt`. Uses
  `char_gentleman_e` (not the dead `char_gentleman_c`).
- **S18 is ON HOLD** — do not re-shoot, cart design changing, waiting on
  `loc_mansion` regeneration first.
- **S2 REDO** (accident now comes from Dupe straightening a crooked painting,
  not deliberately taking it down) — needs `prop_cart_b` (new cart) + the
  `loc_wall_crack` reference plate, both now confirmed to exist.
- **S3 REDO**: `char_visitor_a` OUT, `char_husband` IN (the couple). Needs
  `loc_wall_pov_d` — **checked, does NOT exist yet. Still blocked.**
- **S13, new scene** (CTO draft, CEO-requested): Valder bribes the workman
  outside, workman refuses. References `loc_exterior`/`char_valder`/
  `char_workman`, all exist — **not blocked by anything.**
- **S1A–S1G, seven B-roll coverage angles for S1** — need `loc_hall_big_e`
  (new hall variant) — **checked, does NOT exist yet.** Per the CEO: fire the
  angles that barely show the hall first if it's still not ready (I do not
  have the exact "which three" from the relay — a message fragment named
  S1F specifically as one that "leans" least on the hall; the rest is my
  inference, not confirmed instruction — **asking rather than guessing**),
  then S1A/S1B as spares even though they lean on the hall, since a spare
  take costs nothing once the CEO said so explicitly.
- **CEO said "wait"** mid-session — held with nothing fired, Unlimited
  toggled but untouched, until confirming (via file checks) nothing further
  was pending, then resumed once "prop_cart_b" turned out to exist and S2
  was unambiguously ready.
- **ONE TAKE PER SCENE ONLY, no second takes anywhere** — standing order,
  applied throughout.

## S2 — FIRED

Seedance 2.5 · 720p · 16:9 · 20s · Unlimited (struck 140→0, verified by
zoom). 5 references bound clean: `loc_hall_big_d`, `char_cleaner_c`,
`prop_cart_b` (note: no `project_absence_` prefix on this one — confirmed via
Elements panel), `prop_valder_study`, `loc_wall_crack`. Asset id not yet
known — card still processing.

## S2 asset id — committed before download

Asset `06e97fd9-c26f-4b2d-bfaa-25fd0dbf3434` (via video currentSrc filename,
not the preview= URL param — same decoy pattern, confirmed correct by
matching the 5:10 PM Usage log timestamp exactly). Seedance 2.5, 720p.
Downloading next.

## QUEUE.md is now authoritative

CTO wrote `docs/prompts/absence/QUEUE.md` — supersedes all chat relays.
Element swaps confirmed: `char_gentleman` → `char_gentleman_e` (matches my
earlier finding that `char_gentleman_c` is dead), `char_woman_b` →
`char_woman_c`, `prop_cart` → `prop_cart_b`. New fire order: S13 → S1C → S1F
→ S1A → S1B → S1G first (none need a still-pending plate), then once
`loc_hall_big_e`/`loc_wall_pov_d` exist: S3→S4→S5→S6→S7→S8a→S8b→S8c→S9→S10→
S11→S12→S15→S16→S17→S18→S1D→S1E. Discarding my staged S9 prompt — moving to
S13 next per the new order.

## S2 — COLLECTED

720p/1280x720/20.04s confirmed. Shot-by-shot review clean: painting hangs on
the wall (new prop_cart_b visible, orange/red service cart with the same
colourful painting panel as the reference), Dupe reaches to straighten it,
it comes off the wall and leans against the base, small crack revealed
above matching the reference plate closely, final hold on the bare wall
with plaque legible ("THE ABSENCE OF MEANING / Valder / $2,000,000") as
Dupe exits frame. No defects. Note: existing S2 folder already held a
`v1-no-door` take from an earlier version — this redo filed alongside it,
not overwritten, per standing rule. Copied to Drive, byte-exact verified,
local deleted.

Moving to S13 next per QUEUE.md order.

## BLOCKER — loc_exterior also dead, S13 blocked

GH issue: https://github.com/PASAKON/MoonieX-Agents/issues/120

`@project_absence_loc_exterior` hit terminal Face/IP failure while staging
S13 (first item in QUEUE.md's fire order). Notable: this is a location plate
with explicitly zero people in its own spec — the scanner is now flagging
non-portrait assets too, third element to die this way today. Skipped S13,
moved to S1C per QUEUE.md order.

## S1C — FIRED

8s · 720p · 16:9 · Seedance 2.5 · Unlimited (struck 56→0, verified by zoom).
2 references bound clean: `loc_hall_big_d` (fallback, since `loc_hall_big_e`
still doesn't exist), `prop_cart_b`. Asset id not yet known, card processing.

## S1C asset id — committed before download

Asset `1014df24-5f7f-434e-8897-fbe3de4a091e` (via video currentSrc, not the
preview= param). Seedance 2.5, 720p. Downloading next.

## QUEUE.md update — all plates done, S18 off hold, S14 dialogue found

18:08 update: loc_wall_pov_d, loc_hall_big_e, loc_mansion_b, prop_cart_b,
char_woman_c, char_gentleman_e all exist. S18 no longer on hold. S14's
dialogue was found (mislaid, not missing) — Valder screams "STOP! You are
destroying a hundred million dollar artwork!", workman drops the plaster;
S15's "Sorry, sir." confession line belongs to DUPE, not the workman.

**loc_wall_pov_d then got REJECTED** (came back as the porthole-hole design
again, plaque misspelled "Value"). CTO hand-built a replacement PNG at
`.../Sorry, Sir/Element/Location/absence-loc-wall-pov-e.png` (fixed-seed
mirror of loc_hall_big_e with an identical crack every time) — my next job
is uploading it and filing it as Element `loc_wall_pov_e`.
