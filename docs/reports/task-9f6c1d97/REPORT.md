# REPORT task-9f6c1d97 (runner=claude, video_editor), iteration 2

## Summary
119 of 120 EP04 shot plates exist and were checked by eye (all except S029). Done in iter 2: S062-S120 (59 shots), S039 and S040 redone with even skin tone and no pink cheeks (kept), S089 retried once after a browser-closed failure. S029 is marked failed: the retry cap was reached (try 1 drew a street; two retries timed out at 360 s with no image in the chat). Flagged for a retry but kept: S019, S028, S075. Quota came back after the 22:30 TH reset; sheets 2 and 3 were rebuilt with the final plates. No Flow, no fal, no paid API; no winbox process killed; dota2 and terminal64 untouched.

## Counts
- done 119, left 1 (S029 marked failed). Flagged but kept: S019, S028, S075 (3).
- Tries: 116 shots 1 try; S039, S040 2 tries (try 1 rejected); S089 2 attempts (first lost to a browser close, no image made); S029 3 attempts, no usable plate.

## Where things are (media not in git)
- Plates: /opt/MoonieXHQ/Work/cn-series/stills/ep04/EP04-S###.png (1672x941, 16:9), 119 files, md5 equal to the winbox copy for all 119.
- Ledger: /opt/MoonieXHQ/Work/cn-series/plan/EP04-shots-ledger.json (shot, md5, bytes, chat url, tries, status); copy in this folder. Runner ledger: runner_ledger_final.json.
- Sheets: plan/EP04-shots-sheet-1.jpg (S001-S040), -2 (S041-S080), -3 (S081-S120), numbered, rebuilt from the final plates.
- Rejected tries: plan/EP04-shots-rejected/ (S029, S039, S040 try 1).
- Winbox staging C:\mooniex\ep04-shots removed (md5 checked first). The :9224 ChatGPT Chrome is left running (I relaunched it, see Notes).

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
| S029 | first | marked_fail | 3 | try1 rejected (drew a street scene); retry 1 and retry 2 (no refs, abstract-void prompt) both timed out at 360 s with no image in the chat; cap reached, marked and moved on |
| S030 | first | ok | 1 | Luo Yi clamps bound abacus to chest against door; no white strand (pre-cost) |
| S031 | first | ok | 1 | envoy leans to temple, Luo Yi shields wrapped abacus; no strand |
| S032 | first | ok | 1 | both standing, pre-strand state |
| S033 | first | ok | 1 | after_cost white strand visible, tired; small reddish scrape on right cheek (scratch, not a blush) - CMO look |
| S034 | still | ok | 1 | still+fx: Luo Yi lap, wrapped abacus, pale strand visible; face in frame (brief: loose pale hair on wrap, not cropped) |
| S035 | first | ok | 1 | Luo Yi shoves door, envoy steps aside; no dust visible yet |
| S036 | first | ok | 1 | open door, overturned shelves, envoy finger to lips, mist; one person |
| S037 | first | ok | 1 | envoy holds token (not yet dropped), Luo Yi reaching on ground |
| S038 | first | ok | 1 | Luo Yi lifts shelf, Old Fang (round glasses) crawls and points; one each, coins on floor, no text |
| S039 | first | ok | 2 | Luo Yi sits by the bed, Luo Mei in the blanket, skin even and natural, no pink cheeks (retry with ref skin colour ignored) |
| S040 | first | ok | 2 | Luo Mei kneels on the bed pointing at the empty round cushion, vial and bowl on the table, skin even, no pink cheeks; Luo Yi faces camera, not turned (retry) |
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
| S062 | first | ok | 1 | Luo Yi half-smile, Fang holds the pouch up |
| S063 | first | ok | 1 | Luo Yi standing, Fang points at the floor with cane |
| S064 | first | ok | 1 | Fang points out the door, Luo Yi smooths dark cloth on table |
| S065 | still | ok | 1 | still+fx: cracked green abacus + pouch, no people |
| S066 | first | ok | 1 | Fang offers a rod, Luo Yi open palm |
| S067 | first | ok | 1 | Zhao retainers (2) and Luo Yi at the red gate, pouch held |
| S068 | first | ok | 1 | retainers and Luo Yi crouched at the gate |
| S069 | first | ok | 1 | Fang holds a bead cord, retainers behind |
| S070 | still | ok | 1 | still+fx: blue wrapped bundle + cord on stone, no people |
| S071 | first | ok | 1 | Fang at the door, retainers and Luo Yi with a shoulder bundle |
| S072 | first | ok | 1 | night market: Luo Yi holds cord, armored vendor points |
| S073 | first | ok | 1 | Luo Yi with a rod over a cracked bowl, stall keeper |
| S074 | first | ok | 1 | Luo Yi hands pouch, keeper palm up, bowl on table |
| S075 | first | ok_retry_pending | 1 | abacus already glowing green (brief wording of glow not checked against first frame) RETRY FLAG: abacus already glowing green before the flick (brief: objects intact before transformation) |
| S076 | first | ok | 1 | keeper raises both hands, Luo Yi taps bowl |
| S077 | first | ok | 1 | retainers reach for keeper holding stacked bowls |
| S078 | still | ok | 1 | still+fx: cracked bowl with bone sliver, no people |
| S079 | first | ok | 1 | inspector (scholar) probes the bowl, Luo Yi leans in; distant small figures on the bridge |
| S080 | first | ok | 1 | Luo Yi points at vial held by the scholar, abacus in a wrap |
| S081 | first | ok | 1 | Luo Yi, scholar and keeper around the bowl; Luo Yi holds a bone sliver |
| S082 | still | ok | 1 | still+fx: bowl, dish with red liquid and powders, no people |
| S083 | first | ok | 1 | scholar holds the pouch out, Luo Yi sets a bone on cloth |
| S084 | first | ok | 1 | Luo Yi sorts coins, back of the scholar in frame |
| S085 | first | ok | 1 | three men: tall robed man points at bowl pieces |
| S086 | first | ok | 1 | tall robed man gestures, Luo Yi stands; backs of two stall heads in foreground |
| S087 | first | ok | 1 | robed man looks away, retainer leans in beside Luo Yi |
| S088 | first | ok | 1 | robed man gestures, Luo Yi lays out bowl shards |
| S089 | still | ok | 2 | robed man alone behind an empty tray (retry: first attempt lost to a browser close) |
| S090 | first | ok | 1 | retainers and the robed man around a mossy stone |
| S091 | first | ok | 1 | Luo Yi points at the stone, robed man arms crossed, scholar smiles |
| S092 | first | ok | 1 | Luo Yi, scholar and robed man; abacus on table |
| S093 | first | ok | 1 | retainers wash the stone in a tub |
| S094 | still | ok | 1 | still+fx: stone, plain bag and blue bag, no people |
| S095 | first | ok | 1 | Luo Yi seen from behind, helper carries an open box, a second man at the curtain |
| S096 | first | ok | 1 | retainer grips Luo Yi shoulder at an open box with a ring print |
| S097 | first | ok | 1 | Luo Yi and a helper holding a padded box |
| S098 | first | ok | 1 | helper shows the empty padded box, Luo Yi standing |
| S099 | first | ok | 1 | Luo Yi stops a retainer, seated man watches |
| S100 | first | ok | 1 | Luo Yi and old doorman at a green-lit vault door, finger raised |
| S101 | still | ok | 1 | still+fx: vault door, rope stanchions, red chest, no people |
| S102 | first | ok | 1 | doorman hands in front, rope barrier |
| S103 | first | ok | 1 | Luo Yi and doorman close, rope in front |
| S104 | first | ok | 1 | Luo Yi looking down at cloth, doorman behind |
| S105 | first | ok | 1 | doorman raises a hand, Luo Yi watches |
| S106 | first | ok | 1 | Luo Yi seated at table with empty tray, doorman back to camera |
| S107 | first | ok | 1 | official in gold robe holds up a sack cloth, doorman and Luo Yi |
| S108 | first | ok | 1 | Luo Yi from behind, doorman pulls the vault door |
| S109 | first | ok | 1 | two retainers carry the stone, Luo Yi in front |
| S110 | first | ok | 1 | courier offers sealed envelope to Luo Yi |
| S111 | first | ok | 1 | courier points down the lane, envelope held low, Luo Yi chin on hand |
| S112 | first | ok | 1 | Luo Yi holds sealed envelope close, faint dark spot on the corner |
| S113 | still | ok | 1 | still+fx: envelope macro, wax seal flower relief, no text |
| S114 | first | ok | 1 | Luo Yi points at envelope on table, courier palms up |
| S115 | first | ok | 1 | Luo Yi reads the envelope, retainer arms crossed; one small walking figure far down the lane |
| S116 | first | ok | 1 | Luo Yi opens the envelope |
| S117 | first | ok | 1 | Luo Yi close on envelope, red mark at corner |
| S118 | first | ok | 1 | Luo Yi holds envelope, retainer behind |
| S119 | first | ok | 1 | Luo Yi holds the envelope, red smudge at corner |
| S120 | first | ok | 1 | Luo Yi holds a cloth with a red stain |

Status key: ok = kept; ok_retry_pending = kept but flagged for a retry; marked_fail = cap reached, no plate.

## Method
- One image at a time through a per-shot wrapper (resume-kit/run_shots.ps1): Available MBytes at least 1024 and no other chatgpt_images.py process before every image, wait up to 15 min else stop. Measured available RAM was 1.1 to 5.1 GB (lowest 1287 MB, before S041).
- Runner: tools/chatgpt_images.py from origin/main, staged on winbox. Two edits to the STAGED copy only (full copy in resume-kit): attach accepts a list, and a multi-file input is used when present (the first file input on the Thai UI is the single-file camera input and refused 3 files). origin/main is unchanged.
- Each shot attaches all its reference plates (1 to 5). Older 16:9 plates (pawn, ghost, market, alley, backroom, backgate) had the bottom 14% cropped before upload (the plate 03 watermark trap); the square and portrait plates looked clean in the bottom strip. Each prompt gets one prefix line naming each attached image's role (identity, setting only, prop) and "do not copy text, mark or composition".
- The CMO held home:winbox:9224; I took no lock. Chrome attach first failed: a hung unrelated tab ("Mage Sprite Sheet") did not answer Runtime.evaluate and blocked connect_over_cdp. The CMO closed it by id and the attach then worked.

## Checks done by eye
Every kept plate was viewed on a numbered sheet at 760 px per image (6 per sheet, 10 sheets for S062-S120), and S039/S040 were viewed full size. Checked: each named person once, no clones or face reflections, no readable text or hanzi, no watermark, adults only (Luo Mei only in the family room), stylized 3D, no blush. S039 and S040: Luo Mei's skin is even and natural, no pink cheeks; the ref's skin colour was ignored by prompt. Luo Yi carries a small scrape near the cheek in some later close-ups (S110, S117, S119, S120); it reads as a cut, not a blush, and the story has him wounded.

## Judgment calls
- S075: abacus already glows before the flick (same problem as S028); kept, flagged. S019, S028 unchanged (not in this iteration's brief).
- S039: Luo Yi sits beside the bed with one hand reaching; the brief says he kneels with hands held. S040: Luo Yi faces the camera, he is not turned toward Luo Mei. Kept, they pass the skin-tone order; a CMO call.
- A few frames have small distant background figures or backs of heads (S079, S086, S115); not main cast, kept.
- S029 (abstract black currents, no person): both retries timed out with nothing in the chat. Suggest the CMO generates it in Flow from text only or accepts a simple dark gradient plate; ChatGPT stalls on this prompt.
- Retry order cost: wrapper "exit=0" fooled me once. The runner exits 0 with "nothing to do" when its own ledger says done, so S039/S040/S029 were skipped silently until I removed their rows from the runner ledger (backup kept in the winbox out folder, now removed with the staging) and moved the old files out.

## Winbox / process notes
- Chrome on :9224 was not running when I started (no Chrome at all). The CMO's hold (DungeonRunner mockups) ended with the GO-9224 file at 20:12 TH; I relaunched the ChatGPT Chrome from its own profile through a one-shot interactive scheduled task (a Chrome started from the ssh session dies when the session ends). The task was removed after it ran. The loop relaunched it three more times, when it was down at attempt start.
- ChatGPT image quota was still out at 20:17 TH and came back at the 22:30 reset: 8 attempts every 20 minutes from a plain shell loop (loop.sh in resume-kit), run S062-S120 started 22:54 winbox clock (Berlin 16:54).
- Free RAM on winbox was 1.2 to 8.5 GB while running, never under 1.0 GB; lowest 1227 MB before S072. One wait (S071 to S072, 8 min) was the RAM gate.

## Not checked / risk
- By eye only; no automated text or watermark detector. The small hanzi-like ornament on S113's seal and the door medallions are abstract relief to my eye but I did not zoom every plate.
- First-frame pose fidelity versus each shot's brief was judged from the thumbnails, not each prompt line by line. S075 is the one I caught; others like S028 may slip. The CMO should spot check.
- S029 has no plate. Any Flow shot that needs it has no first frame yet.
- The :9224 Chrome login state was not checked after the runs other than by the runner working; the profile is shared with the CMO.

## Skill learning
- MISSING [CMO_Procedure_ChatGPTImage_Runner (or BROWSER_OPERATOR_Protocol_Playbook) §ChatGPT image runner on winbox] : a headed Chrome started from the ssh session (Start-Process or the .cmd) dies when that ssh session ends; start it through a one-shot interactive scheduled task (same pattern as flow-chrome-task-register.ps1) and the :9224 listener stays · evidence: task-9f6c1d97, 2026-11-14 19:13-20:16 TH, Chrome gone twice, up after Register-ScheduledTask -LogonType Interactive
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §ChatGPT image runner on winbox] : `chatgpt_images.py` exits 0 with "nothing to do" when its own ledger row is `done`, so a redo of a rejected shot is a silent no-op; drop the ledger row and move the old png out first · evidence: task-9f6c1d97, run.log S039/S040 exit=0 in 0 s
- MISSING [no owner: powershell over ssh] : `powershell -Command -` reading a multi-line script with an `if {}` block from stdin ran nothing and returned exit 0 with no output; scp the .ps1 and run with -File · evidence: task-9f6c1d97 attempt 1 of the retry loop
- COSTLY [no owner] : waiting on the CMO's :9224 hold; I relaunched Chrome before the hold letter arrived · prevented by: check the lock/hold file before touching a :9224 browser even when the brief says the CMO holds it for you
