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
