## Summary

Night chain 2 — five «Sorry, Sir» scenes on the winbox browser_operator lane
(`higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`, FREE/Unlimited lane).
Fired all five scenes in the assigned order after waiting out the other operator's
S18→S2X chain on the shared account-wide generation slot:

1. **S3a "The First Customer" take 2** — landed, camera-lock defect from take 1
   confirmed fixed (locked shot 2, single correct cut at 5s).
2. **S2AW "The Interpretations, Tableau"** — landed, locked shot, correct cast/order,
   Dupe+cart visible dead centre as specified.
3. **S2AP "The Interpretations, Portraits"** — landed, five correct portraits, no
   close-up defect (the sibling design's rejection reason).
4. **S2R-F Split "The Battle, Five Panels"** — **REJECTED by platform moderation**
   (copyright restrictions), the same outcome as its five-close-up sibling design.
   Never re-fired, per standing instruction. This is now a CEO/CTO decision point
   (two different framings of this scene have both failed moderation).
5. **S19 "The Painting Goes Back"** — landed after an unusually long ~3-hour queue
   wait (European/US daytime peak per the skill's documented schedule; confirmed
   genuinely queued, not stuck, via repeated fresh-tab checks). Beat-for-beat match
   to the sheet.

None of the four landed clips are self-certified — full evidence (settings,
chip-binding counts, frame-diff cut sweeps, beat-by-beat frame comparison against
each sheet) is in `docs/reports/absence-night-chain-2-winbox.md` for the CTO's
full-resolution review.

Two operational findings worth carrying forward (both written into the skill-facing
report in detail): (1) a reliable upload→diff→byte-verify method for identifying a
freshly-uploaded video reference in a shared/cluttered asset library, since sort
controls did not reliably reorder the picker; (2) the composer can silently drift
settings (duration, resolution) between scenes in the same tab/session — caught a
1080p resolution drift before firing S19 by re-verifying via pixel screenshot
(a same-moment JS/DOM text-scrape of the same control read a stale/decoy value).

## Files Changed
- `docs/reports/absence-night-chain-2-winbox.md` — full per-scene report (settings,
  chip verification, download/md5, frame-diff sweeps, beat-by-beat frame review)
- `docs/reports/frames-s3a-t2/`, `docs/reports/frames-s2aw/`, `docs/reports/frames-s2ap/`,
  `docs/reports/frames-s19/` — full-res review frames + 640px contact rows
- No sheets, previz files, or AB-LEDGER touched

## Commits
- `7d86b30` night chain 2 report skeleton, tab claimed, prompt blocks pre-staged
- `26b7cc1` S3a take 2 fired
- `e0f6f7b` S3a take 2 landed, harvested, frame-reviewed
- `6245fb9` S2AW tableau fired
- `16a66f8` S2AW landed, harvested, frame-reviewed
- `b270aa3` S2AP landed, harvested, frame-reviewed
- `386842c` S2R-F split fired
- `6b17055` S2R-F split REJECTED (copyright), never re-fired
- `aa868aa` S19 fired (caught 1080p settings drift, corrected to 720p)
- `86665b8` interim note, S19 queued ~3h
- (final) S19 landed, harvested, frame-reviewed; this REPORT.md

## Tests
N/A — browser_operator task, no application code changed. Every generation's spec
(model, duration, resolution, aspect ratio, chip binding) was verified by pixel
screenshot immediately before firing, and every landed download was verified by
md5 + ffprobe (codec/resolution/duration) + a frame-diff cut sweep + a beat-by-beat
full-resolution frame comparison against the sheet's REVIEW ORDER.

## Issues / Blockers
No blocker prevents closing this task. One open creative/moderation decision for
the CEO/CTO: S2R-F "The Battle" has now been rejected by platform moderation in
two different visual designs (five-close-up, and this task's five-panel-split).
Whether to attempt a third design or accept the scene as unshootable in video form
is not something a browser_operator should decide — flagged for the CTO in the
detailed report.

Downloaded MP4s are on `C:\Users\UsEr\Downloads\` (winbox has no Google Drive OAuth
token, so upload was not attempted, per repeated task/skill instruction) — exact
filenames and md5s are listed at the bottom of the detailed report for the CTO to
pull over SSH and file into Drive.
