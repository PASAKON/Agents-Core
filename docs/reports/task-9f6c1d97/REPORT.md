# REPORT task-9f6c1d97 (runner=claude, video_editor)

## Summary
58 of 120 EP04 shot plates are made and checked by eye (S001-S061 except S029, S039, S040). ChatGPT's image quota ran out at EP04-S062 (runner exit 5, "ลองอีกครั้ง เวลา 22:30", winbox clock = 16:30 Berlin), so per the brief I stopped. Five retries are queued (S029, S039, S040 rejected; S019, S028 flagged) and S062-S120 (59 shots) are not started. No Flow, no fal, no paid API; no relay request raised; no winbox process killed.

## Where things are (media not in git)
- Plates: /opt/MoonieXHQ/Work/cn-series/stills/ep04/EP04-S###.png (1672x941, 16:9), 58 files. _incoming/ holds the raw pulls (incl. S039/S040 try 1).
- Ledger: plan/EP04-shots-ledger.json (shot, md5, bytes, chat url, tries, status); copy in this folder. Review notes: plan/EP04-shots-review.json.
- Sheets: plan/EP04-shots-sheet-1.jpg (S001-S040, numbered; the CMO checked it and passed it), plan/EP04-shots-sheet-2.jpg (S041-S080, only S041-S061 filled, rest marked pending). Sheet 3 does not exist yet.
- Rejected tries: plan/EP04-shots-rejected/ (S029, S039, S040 try 1; the *_final_copy files are duplicates of the S039/S040 try 1).
- Winbox staging, left in place for the resume: C:\mooniex\ep04-shots (runner staged from origin/main plus multi-attach patch, jobs.json with 120 jobs, jobs_retry.json, refs/ with 31 plates, out/ with the runner ledger). Remove it when the task is done.

## Per-shot table
| shot | type | status | tries | note |
|---|---|---|---|---|
| S001 | first | ok | 1 | envoy foreground, Luo Yi once far down the street, lantern still lit |
| S002 | first | ok | 1 | Luo Yi shields door, envoy looks past him |
| S003 | first | ok | 1 | envoy finger toward chest, both separate |
| S004 | first | ok | 1 | Luo Yi grips pouch, envoy hand motionless but not the focus |
| S005 | still | ok | 1 | empty threshold, hem, two overlapping boot prints (brief says one); no face |
| S006 | first | ok | 1 | envoy already crouched with stone touching the threshold (placing begun, not a pure pre-pose) |
| S007 | first | ok | 1 | boot already over the intact stone (contact moment, stone intact) |
| S008 | first | ok | 1 | Luo Yi scans window lattice, envoy at doorway; one each |
| S009 | first | ok | 1 | Luo Yi knocks, tea tray in other hand (teaboy detail), no scrape visible at floor yet |
| S010 | still | ok | 1 | still+fx: drag groove + straw bristle under door, no people |
| S011 | first | ok | 1 | envoy head tilted at door, Luo Yi braces hand |
| S012 | first | ok | 1 | tight close on listening face, pouch hand at chest |
| S013 | first | ok | 1 | Luo Yi presses wrapped abacus on a table, envoy out of focus behind |
| S014 | first | ok | 1 | envoy wrist scar visible (thin arc), face lower half only |
| S015 | still | ok | 1 | still+fx: scarred wrist against black fabric, no face |
| S016 | first | ok | 1 | Luo Yi shrug, envoy leans in |
| S017 | first | ok | 1 | envoy taps door, Luo Yi crouched at floor gap |
| S018 | first | ok | 1 | envoy open palm, Luo Yi opposite |
| S019 | first | ok_retry_pending | 1 | NOTE brief says covered beads; abacus is uncovered on table, corner cracked. retry candidate RETRY FLAG: brief says covered beads, abacus uncovered |
| S020 | first | ok | 1 | envoy hand toward chest, Luo Yi holds tea tray (teaboy detail) |
| S021 | first | ok | 1 | Luo Yi half-smile against door, envoy distant |
| S022 | still | ok | 1 | still+fx: shattered stone fragments + planted boot, no face |
| S023 | first | ok | 1 | Luo Yi holds pouch facing camera (not yet turned to the door sound) |
| S024 | first | ok | 1 | Luo Yi reaches for pouch sitting on envoy palm; palm steady |
| S025 | first | ok | 1 | purple wrapped bundle being untied, envoy watches |
| S026 | first | ok | 1 | fingertip near bead, envoy palm out, small smile hidden by hood shadow |
| S027 | still | ok | 1 | still+fx: macro cracked frame + fingertip, Luo Yi face partly in frame (brief: macro of frame and fingertip) |
| S028 | first | ok_retry_pending | 1 | abacus ALREADY glowing green before the flick (brief wants intact/dull first). retry candidate RETRY FLAG: abacus glows before the flick |
| S029 | first | retry_pending | 1 | try1: ignored abstract void, drew Luo Yi in street with apron (only ref was street plate) |
| S030 | first | ok | 1 | Luo Yi clamps bound abacus to chest against door; no white strand (pre-cost) |
| S031 | first | ok | 1 | envoy leans to temple, Luo Yi shields wrapped abacus; no strand |
| S032 | first | ok | 1 | both standing, pre-strand state |
| S033 | first | ok | 1 | after_cost white strand visible, tired; small reddish scrape on right cheek (scratch, not a blush) - CMO look |
| S034 | still | ok | 1 | still+fx: Luo Yi lap, wrapped abacus, pale strand visible; face in frame (brief: loose pale hair on wrap, not cropped) |
| S035 | first | ok | 1 | Luo Yi shoves door, envoy steps aside; no dust visible yet |
| S036 | first | ok | 1 | open door, overturned shelves, envoy finger to lips, mist; one person |
| S037 | first | ok | 1 | envoy holds token (not yet dropped), Luo Yi reaching on ground |
| S038 | first | ok | 1 | Luo Yi lifts shelf, Old Fang (round glasses) crawls and points; one each, coins on floor, no text |
| S039 | first | retry_pending | 1 | Luo Yi kneels, Luo Mei in blanket, hands held; Luo Mei faint cheek warmth inherited from plate 05 ref (not a deliberate blush) - CMO look / try1: Luo Mei cheeks read pink (CMO) |
| S040 | first | retry_pending | 1 | Luo Mei points at empty cushion, Luo Yi turns; vial present; same faint cheek warmth as plate 05 - CMO look / try1: Luo Mei cheeks read pink (CMO) |
| S041 | still | ok | 1 | still+fx: empty cushion, intact vial, dust, no people |
| S042 | first | ok | 1 | Luo Yi under bed, Luo Mei catches sleeve and points to rear exit; Luo Mei cheeks slightly warm like plate 05 (same risk as S039/S040) |
| S043 | first | ok | 1 | Luo Yi alone in ruined shop, white strand present |
| S044 | first | ok | 1 | Luo Yi lifts token with cloth, token on threshold board, blue tassel |
| S045 | first | ok | 1 | Fang with cane + key ring, Luo Yi at open drawer with pouch |
| S046 | still | ok | 1 | still+fx: black token three cloud ridges on cloth, no writing |
| S047 | first | ok | 1 | Fang stops Luo Yi, token on cloth; Fang closing cloth is not yet visible |
| S048 | first | ok | 1 | grain runner back to camera at counter, Fang + Luo Yi behind; runner palm not clearly empty-open |
| S049 | first | ok | 1 | Zhao retainer, shopkeeper, Fang; small background market extras (brief says only described cast); daylight reads closer to photoreal |
| S050 | first | ok | 1 | Fang reaches, shopkeeper draws parcel back |
| S051 | first | ok | 1 | Luo Yi offers bracelet, merchant, Fang between; background extras |
| S052 | first | ok | 1 | two retainers at street entrance, merchant gestures; background extras |
| S053 | still | ok | 1 | still+fx: empty basket, board leaning (not face down), no people |
| S054 | first | ok | 1 | officer with key and chain, sealed envelope (seal abstract), Luo Yi + Fang |
| S055 | first | ok | 1 | closed document + key on table, Fang and officer |
| S056 | first | ok | 1 | officer locks chain on door, Fang + Luo Yi watch |
| S057 | first | ok | 1 | Fang sits arms crossed, Luo Yi offers folded cloth, chained door |
| S058 | still | ok | 1 | still+fx: brass scale, empty pans, light shaft, no people |
| S059 | first | ok | 1 | Luo Yi gestures at auction hall, Fang closing cash box |
| S060 | first | ok | 1 | Luo Yi hand on bound abacus, Fang back to camera |
| S061 | first | ok | 1 | Fang sets reserve pouch apart from box, Luo Yi watches |
| S062 | first | stopped_quota | 0 | ChatGPT image quota hit, reset 22:30 (winbox clock) |
| S063 | first | not_started | 0 |  |
| S064 | first | not_started | 0 |  |
| S065 | still | not_started | 0 |  |
| S066 | first | not_started | 0 |  |
| S067 | first | not_started | 0 |  |
| S068 | first | not_started | 0 |  |
| S069 | first | not_started | 0 |  |
| S070 | still | not_started | 0 |  |
| S071 | first | not_started | 0 |  |
| S072 | first | not_started | 0 |  |
| S073 | first | not_started | 0 |  |
| S074 | first | not_started | 0 |  |
| S075 | first | not_started | 0 |  |
| S076 | first | not_started | 0 |  |
| S077 | first | not_started | 0 |  |
| S078 | still | not_started | 0 |  |
| S079 | first | not_started | 0 |  |
| S080 | first | not_started | 0 |  |
| S081 | first | not_started | 0 |  |
| S082 | still | not_started | 0 |  |
| S083 | first | not_started | 0 |  |
| S084 | first | not_started | 0 |  |
| S085 | first | not_started | 0 |  |
| S086 | first | not_started | 0 |  |
| S087 | first | not_started | 0 |  |
| S088 | first | not_started | 0 |  |
| S089 | still | not_started | 0 |  |
| S090 | first | not_started | 0 |  |
| S091 | first | not_started | 0 |  |
| S092 | first | not_started | 0 |  |
| S093 | first | not_started | 0 |  |
| S094 | still | not_started | 0 |  |
| S095 | first | not_started | 0 |  |
| S096 | first | not_started | 0 |  |
| S097 | first | not_started | 0 |  |
| S098 | first | not_started | 0 |  |
| S099 | first | not_started | 0 |  |
| S100 | first | not_started | 0 |  |
| S101 | still | not_started | 0 |  |
| S102 | first | not_started | 0 |  |
| S103 | first | not_started | 0 |  |
| S104 | first | not_started | 0 |  |
| S105 | first | not_started | 0 |  |
| S106 | first | not_started | 0 |  |
| S107 | first | not_started | 0 |  |
| S108 | first | not_started | 0 |  |
| S109 | first | not_started | 0 |  |
| S110 | first | not_started | 0 |  |
| S111 | first | not_started | 0 |  |
| S112 | first | not_started | 0 |  |
| S113 | still | not_started | 0 |  |
| S114 | first | not_started | 0 |  |
| S115 | first | not_started | 0 |  |
| S116 | first | not_started | 0 |  |
| S117 | first | not_started | 0 |  |
| S118 | first | not_started | 0 |  |
| S119 | first | not_started | 0 |  |
| S120 | first | not_started | 0 |  |

Status key: ok = kept; ok_retry_pending = kept but flagged for a retry; retry_pending = rejected try 1, file absent; stopped_quota = ChatGPT quota stop; not_started.

## Method
- One image at a time through a per-shot wrapper (resume-kit/run_shots.ps1): Available MBytes at least 1024 and no other chatgpt_images.py process before every image, wait up to 15 min else stop. Measured available RAM was 1.1 to 5.1 GB (lowest 1287 MB, before S041).
- Runner: tools/chatgpt_images.py from origin/main, staged on winbox. Two edits to the STAGED copy only (full copy in resume-kit): attach accepts a list, and a multi-file input is used when present (the first file input on the Thai UI is the single-file camera input and refused 3 files). origin/main is unchanged.
- Each shot attaches all its reference plates (1 to 5). Older 16:9 plates (pawn, ghost, market, alley, backroom, backgate) had the bottom 14% cropped before upload (the plate 03 watermark trap); the square and portrait plates looked clean in the bottom strip. Each prompt gets one prefix line naming each attached image's role (identity, setting only, prop) and "do not copy text, mark or composition".
- The CMO held home:winbox:9224; I took no lock. Chrome attach first failed: a hung unrelated tab ("Mage Sprite Sheet") did not answer Runtime.evaluate and blocked connect_over_cdp. The CMO closed it by id and the attach then worked.

## Checks done by eye
Every kept plate was viewed on a numbered contact sheet at 800 px per image (6 to 8 per sheet) and checked for: each named person once, no clones or face reflections, no readable text or hanzi, no watermark, adults only (Luo Mei only in family-room shots), no blush, stylized 3D not photoreal, first-frame pre-action pose, still+fx plates motionless. Zoomed: S033 and S034 faces (small scrapes on the cheek, not a blush), S039 and S040 Luo Mei face against the ref.

## Judgment calls
- Kept as ok with a note (not retried, retry cap and quota): S005 two overlapping boot prints instead of one; S006 and S007 already at the contact moment of the stone action (stone intact); S009 and S020 Luo Yi still carries the teaboy tray; S027 and S034 Luo Yi's face is in frame on a macro/insert plate; S049, S051, S052 small background market extras (brief: only the described cast) and the daylight market frames read closer to photoreal than the night frames; S053 board leans rather than lying face down; S048 runner faces away.
- Retry flags: S019 (brief says covered beads, abacus uncovered), S028 (abacus glows before the flick), S029 rejected (ChatGPT drew Luo Yi in a street instead of the abstract void, because the only ref was the street plate), S039 and S040 rejected at the CMO's order (Luo Mei cheeks read pink). Retry prompts are prepared in resume-kit/jobs_retry.json: S029 with no refs and "no person, no street"; S039 and S040 with "use only face shape, hair buns, ribbons and clothing from the ref, ignore its skin colour" plus "even natural skin tone, no rosy cheeks" (the word blush is not used).
- S042 (kept) also shows Luo Mei with slightly warm cheeks like the approved plate 05; same risk as S039 and S040, the CMO should look.

## Issues / Blockers
- ChatGPT image quota out at S062; usable again after 22:30 winbox time. I did not wait: the brief says stop and report.
- Still to do: retries S019, S028, S029, S039, S040 (5 images), then S062 to S120 (59 images), about 1.5 to 2 min each.
- Resume: from the staged folder run run_shots.ps1 with the retry names against jobs_retry.json (use a separate out folder), then the remaining names against jobs.json. Start it detached with Win32_Process.Create via Invoke-CimMethod (Start-Process dies with the ssh session). Record decisions with rev.py, rebuild the ledger with mkledger.py.

## Not checked / risk
- S062 to S120 and the five retries do not exist. Nothing about those shots is verified, including whether first-frame prompts for the later shots (Luo Mei, auction hall, bowls, letters) drift the way S029 did.
- Luo Mei's cheek tint comes from the approved ref itself; the retry clause may not remove it (plate 05 has the same tint). Not tested.
- Photoreal against stylized and identity continuity (Luo Yi, Fang, Envoy across shots) were judged on contact-sheet size only, not frame by frame against EP01-03. Face similarity between plates 06, 08, 10, 12 was not re-checked.
- Bottom-corner watermarks were not zoom-checked on every plate; the refs were cropped to lower that risk.
- "First frame = second 0" is a judgment per shot; several already sit at the contact moment (S006, S007, S037).

## Skill learning
- MISSING [CMO_Procedure_ChatGPTImage_LakornCover | no owner]: a hung ChatGPT tab (renderer not answering Runtime.evaluate) makes every Playwright connect_over_cdp time out after "ws connected"; diagnose with raw CDP Target.attachToTarget plus Runtime.evaluate per page via node on winbox, then ask the browser's lock holder to close that one tab. evidence: task-9f6c1d97 (cdpdiag.js).
- MISSING [CMO_Procedure_ChatGPTImage_LakornCover | no owner]: tools/chatgpt_images.py attaches one image per shot, and the Thai UI's first input[type=file] is the single-file camera input ("ถ่ายรูป"), so multi-ref shots need the multiple input or one set_input_files per file. evidence: task-9f6c1d97 run log "Non-multiple file input can only accept single file".
- MISSING [no owner]: a ChatGPT Plus image batch hits the image quota after roughly 60 images in about 2 hours (reset shown as "ลองอีกครั้ง เวลา 22:30" in winbox time); a 120-plate brief needs a planned pause or a split. evidence: EP04-S062 exit=5.
- COSTLY [no owner]: Start-Process from an ssh session dies with the session; Win32_Process.Create via Invoke-CimMethod survives. evidence: task-9f6c1d97 launch (first launch pid 17752 vanished, second pid 26768 ran 2 h).
- COSTLY [no owner]: a shot whose only ref is an environment plate and whose prompt is abstract (S029) gets a person drawn in; send no ref for abstract shots. evidence: EP04-S029 try 1.
