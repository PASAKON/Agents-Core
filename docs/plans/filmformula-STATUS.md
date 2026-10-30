# FilmFormula — STATUS (notes only; milestones live in the registry, id `filmformula`)

PH: project_head-3f2bd16a (CMO lane, owner cmo-e785343f). Brief: state/ph-briefs/project_head-3f2bd16a.md.
Goal: study popular one-episode short films, turn their structure into our own ILAG genre formula and film workflow.

## Notes
- 2026-10-28 22:40 TH: opened. Milestones M0-M4 in the registry (M0 due 29 Oct 12:00 TH).
- M0 research → task-78f450d6 (researcher, metadata only, no video download). Queued behind budget (1 ahead).
- Prior method for metadata-only study: CMO scratchpad siam/ (pw.py reads ytInitialPlayerResponse, parse.py reads search pages).
- 2026-10-29 13:00 TH: task-78f450d6 gc-cancelled (stale pending 30 min); refiled as task-a0587d1c, deferred again (7 ahead), cancelled; PH did M0 itself with yt-dlp metadata ($0).
- 2026-10-29 13:08 TH: M0 done. Report docs/reports/filmformula/M0-genres.md; CEO card Q-20261029-0608-6729 (rec: scam exposed + karma). All Thai candidates standard licence → storyboard only; CC-BY set for M1: Tears of Steel, Sintel, Fallout Tuesday, INTERVIEW, Shift.
- 2026-10-29 13:10 TH: M1 task-50731531 (tools/film_breakdown.py, test on Tears of Steel CC-BY) tier_defer 8 ahead; blocker to CMO (critical tier, or PH writes it). Registry blocked on resource.
- Org note: create_task with project=filmformula fails at delegate ("unknown project"); file worker tasks under mooniex-agents.
- 2026-10-29 13:12 TH: CMO: hold M1 until the CEO picks a genre; then delegate if a bucket is under, else PH writes a thin PySceneDetect CLI wrapper. task-50731531 left to gc.
- 2026-10-29 14:19 TH: CEO on Q-…6729: Western audience, mass genres (superhero, disaster, fire, blockbuster). M0b in the report (rec: disaster + true-disaster series; AI-made disaster/survival shorts reach 0.6-2.9M on small channels). New card Q-20261029-0719-c40b.
- 2026-10-29 14:25 TH: CEO pick Q-20261029-0719-c40b = disaster + true-disaster series (logged as decided). He asked for real links to judge: watchlist https://claude.ai/artifact/3owp18NUHiynKx6WgATozH, card Q-20261029-0725-ab36 (which film is the main model; non-blocking). M1 refiled task-98b6816d (agy-gemini under), queued 1 ahead.
- 2026-10-29 14:26 TH: CEO Q-20261029-0725-ab36: main models = Sydney Mega Tsunami + 1761 shipwreck (true-story series). M2 studies these two by storyboard frames (no download) + CC-BY shot baseline.
- 2026-10-29 15:24 TH: M1 done. PR #556 merged a0961048 (Codex wrote, PH reviewed; Codex had no network so PH ran ToS + opened PR; CI fail-set = osv-scanner, same as main). ToS 720p: 156 shots, avg 4.7 s, median 3.0 s → docs/reports/filmformula/tos-baseline/. WORK_DIR closed + ledger line. Shot-label model pass moved to M2 (labels the 2 picked films).
- 2026-10-29 15:35 TH: M2 inputs in Work/task-bfc3ea80/in (storyboard sb0 split: A 144 frames @4.94 s, B 135 @9.9 s; subs A en-US, B en-orig auto (en hit 429); ToS baseline). Storyboards too coarse for cut length; formula uses beats + speech density + ToS shot baseline. task-bfc3ea80 (researcher) queued, 0 ahead.
- 2026-10-29 21:50 TH: task-bfc3ea80 never left tier_defer (6 h); PH did M2 by hand (4 contact sheets + captions). Formula knowledge/brand-knowledge/brands/ilag/disaster-formula.md, report docs/reports/filmformula/M2-report.md; PR #564 (also carries M0 report + ToS baseline, never committed before). Review task-6ef888dc on agy-claude.
- 2026-10-30 00:15 TH: CMO approved PR #564 (2 rules added) and #568 (M3 Step 1b, 2 adds); merging when CI ends. M4: CMO picked Lituya Bay 1958 (10-13 min, chapters refit to one night). Script v1 docs/reports/filmformula/M4/ (10:17, 962 words, 97 shots = 10 Flow cards); sent to CMO, no card raised.
- 2026-10-30 00:40 TH: #564 merged d116d13e, M2 done. Script v1.1 (USGS fact check: 2 dead not 5, Sunmore couple unnamed) on cmo/filmformula-m4 11478ae3. Look test = 3 shots S002/S011/S038 cap 40 cr, sheet Work/filmformula-m4-looktest/in/sheet.md. CMO: 16:9 required (CTO adds --aspect by 10:00 TH); PH makes Flow project "ILAG Lituya" on winbox 9226 after ~08:15 reboot-back line; card 08:30-10:00 TH.
- 2026-10-30 00:50 TH: #568 merged e410f5e7, M3 done (80%). M2/M3 worktrees removed.

## 30 Oct 03:40 TH (CMO letter)
- New rule CMO_Workflow_PromptFormula: disaster-formula.md indexed as ilag F1/F2 v0; after the Lituya pilot proves it, move the rules to formulas/F2-true-disaster.md as v1.
- Look-test sheet: a source line per shot added (formula ilag/F2-true-disaster v0 · rewritten); parse_sheet still reads 3 shots.
- CTO: --aspect 16:9 merged (#569, 1375a27f), never run on real Flow; the look test is its first check. Render/video work goes to host=winbox (Q-20261029-1843-c03c).

## 30 Oct 09:55 TH
- host_fill 09:39: Contabo 84%+, winbox open (6.7 GB free). Flow runs on winbox Chrome 9226; nothing rendered on Contabo.
- Flow project "ILAG Lituya" made by me over CDP (0 credits): https://flow.google.com/project/98308833-a2a4-4f9d-9531-2f2dc5e82a83 ; the one Flow tab now points at it.
- Look-test card RUN-20261030-0242-4e34 (task-602110af): shots 2,11,38, 16:9, 720p, cap 40 cr, kind test. Expires 10:42 TH.

## 30 Oct 11:15 TH: look test shot
- RUN-20261030-0242-4e34 tapped 11:01, ran 9 min: spent 36 of 40 cr (9650 → 9614). Exit 1, 0 verified: every download failed (editor save_as canceled → "1080p upscale requires /edit/<id> route").
- Clips pulled free as 720p originals from the project page over CDP: out/shot02.mp4, shot11.mp4, shot38.mp4 (1280x720, 8 s each) + looktest_sheet.jpg. 16:9 works on real Flow.
- By eye: 11 strong; 2 trimline faint (reads as a road); 38 wave at water level, no ridge climb, scale lost. Asked the CMO: pass, or rewrite 2 + 38 and reshoot (~24 cr). Download bug passed to the CMO for the CTO.
- 11:20 TH CMO: S011 passes and is the look reference. S002 + S038 rewritten per the CMO (in/sheet_r2.md, source lines name the change). Card RUN-20261030-0314-2c8c, cap 24 cr, kind reshoot, expires 11:14 TH. CTO Main has the download bug; until fixed, pull 720p over CDP and log it.
- ffprobe round 1: shot02 = 918f18f2e513 (7.96 s), shot11 = a4de07151eb3 (8.01 s), shot38 = d663025a6186 (7.96 s); all 1280x720.
- CMO 11:16 TH: download fix is CTO Main's (pull 720p from the page, ffprobe check, upscale optional), merge today by 17:00 TH or tomorrow morning (Q-20261030-0315-9f03). Batches hold until the merge; then `flow_shoot pull` on the 3 look-test clips must give 3/3 verified before the first batch card.

## 30 Oct 10:20 TH: round 2
- RUN-20261030-0314-2c8c: spent 24 of 24 cr (9614 → 9590), exit 1 at download (same bug). Pulled 720p over CDP: out/shot02_r2.mp4 (f3df31d687e2, 1280x720, 7.96 s), out/shot38_r2.mp4 (a70e2d53918e, 1280x720, 7.96 s), sheet out/looktest_r2_sheet.jpg. CDP pull needs scrollIntoView before hover (off-screen thumbnails do not load).
- Look test total: 60 cr (36 + 24).
- 10:26 TH CMO: S002 r2 passes (aftermath plate). S038 one last try r3 (in/sheet_r3.md, cap 12 cr): if r3 still reads downhill, no 4th try; S038 becomes the S002 scar with a slow push-in + narration. out/bad-shot-02.mp4 was not made by me (not the CMO's either); left in place.
- Download fix = task-027b976a, merge by 17:00 TH. Before each card: Contabo job slot free (one job at a time across lanes, ram_free_gb ≥ 1.6). 10:2x TH: Contabo 1/3 busy, waited; 10:29 TH slot 0/3, 2.4 GB → r3 card RUN-20261030-0329-60eb (cap 12, expires 11:29 TH).

## 30 Oct 10:35 TH: round 3, look test done
- RUN-20261030-0329-60eb: 12/12 cr (9590 → 9578), exit 0, verified 1080p (1920x1080, 7.98 s, sha 35c34b68496f) → out/shot38_r3.mp4. The download worked with the fix not merged: the bug is intermittent (1 of 6 shots).
- By eye S038 r3 climbs uphill from the bay; camera closer than asked. Look set: S002 r2, S011 r1, S038 r3. Look test total 72 cr (36 + 24 + 12).
- Next: batches hold for task-027b976a; then `flow_shoot pull` 3/3 verified on the look-test clips, then batch cards ≤10 shots.
- 13:15 TH PR #589 merged as 600386f3: 2 Flow field notes (intermittent download = 2nd sighting of 2026-10-03; uphill-water prompt). CMO reviewed.
- 13:30 TH: after CTO #591 (4c3c608f), `flow_shoot pull` on winbox (0 cr, card bundle from 5e46343b, folder C:\mooniex\flowcard\pull_lituya) = 0/3. Without --search: "no dialogue line to search for" (narrated shots). With --search per shot: card found, then "original pull failed; refusing to reuse a prior clip URL". Sent to the CMO as a blocker for the CTO. Batches stay held.
- 13:40 TH CMO: free work while held. Worker task-4d9aa87d (agy gemini-4-argon-high, Contabo 73%) writes the 95-shot sheet with a search: line per shot, look rules from S011/S002/S038 (WORK_DIR /opt/MoonieXHQ/Work/filmformula-m4-sheet).
- 14:40 TH: task-4d9aa87d (agy) dead run "tool permission auto-denied" (runner_fit: crash). Retry task-558b7d22 (Sonnet, override agy-dead-run) wrote out/sheet_m4.md first pass: 95 shots (S007 + S097 are local cards), 588 s, parse_sheet 95, 95 unique search phrases each in its own prompt, S002/S011/S038 verbatim from the look set, 67-101 words, no guillemets/em dash. I fixed S095's ending (double "no text", "no modern objects" against the modern boat the script wants). Risk: 18 moving-water shots untested for direction.
- 14:40 TH CMO: CTO fix is task-18ff8da2 (editor → ดาวน์โหลดสื่อ → 720p ขนาดดั้งเดิม 0 cr; never 4K 50 cr), ETA 15:00-15:30 TH, CTO sends the re-run line. 95-shot sheet approved (~1,140 cr) once pull = 3/3: 10 cards in order, one at a time in the Contabo slot. A direction shot that fails twice → aftermath plate, no 3rd try. Field-note update PR #593 open.
- PR #593 merged as ad2abf07 (CMO ok; osv-scanner red as on main).

## 30 Oct 14:56 TH · pull fixed (#595 553f221d)
- `flow_shoot pull --only 2,11,38 --aspect 16:9 --download-resolution 720p` on winbox, no --search: 3/3 verified, 1280x720, 8.0 s each, 0 cr (clips 8191321f, 72b12af2, 7fd0cc28).
- Shoot task task-446c4044. WORK_DIR /opt/MoonieXHQ/Work/filmformula-m4-shoot/ (ledger.tsv, out/). Shots 2, 11, 38 are locked from the look test, so 92 shots in 10 cards of <=10, cap 120 cr each.
- Contabo slot busy at 14:56 (1 running, 1.4 GB free); card 1 waits for the slot.

## 30 Oct 15:57 TH · card 1 (RUN-20261030-0805-b942): 4/10, 44 cr
- Verified: shots 1 (8 s), 5, 6 (6 s), 8 (8 s), all 1920x1080. Balance 9578 -> 9534.
- 6 shots (3, 4, 9, 10, 12, 13) failed at 0 cr: Flow Omni offers only 4/6/8/10 s, the sheet had 7 s. Probe over CDP read the toggles: 4, 6, 8, 10 วินาที.
- Fix: sheet_m4.md durations rounded up (7->8 x25, 5->6 x16, 3->4 x1; old copy tmp/sheet_m4.pre-dur.md); trim in the edit. Ledger kept to verified rows so the rest re-init from the sheet (card-1 ledger kept as ledger.card1.tsv).
- Card 2 = 3, 4, 9, 10, 12, 13, 14, 15, 16, 17; waits for the slot (2/3 running at 15:57).

## PARKED 30 Oct 18:4x TH (CEO order via CMO: free Contabo RAM) · resume with spawn_ph --resume
- Pull: fixed by #595 (553f221d); 3/3 look-set clips verified 720p, 0 cr. Look set locked: S002 r2, S011 r1, S038 r3 (/opt/MoonieXHQ/Work/filmformula-m4-looktest/out).
- Shoot: task-446c4044, WORK_DIR /opt/MoonieXHQ/Work/filmformula-m4-shoot (ledger.tsv = 4 verified: 1, 5, 6, 8; out/). Card 1 RUN-20261030-0805-b942 done (44 cr, balance 9534). No card open; no worker running.
- Sheet: /opt/MoonieXHQ/Work/filmformula-m4-sheet/out/sheet_m4.md, durations now 4/6/8/10 s only. Skip 2, 11, 38 (locked).
- Next: check host_fill (contabo 0 running, ram_free_gb >= 1.6), then card 2 = shots 3,4,9,10,12,13,14,15,16,17, cap 120, --aspect 16:9 --resolution 720p, template state/handoff/2026-10-29/cto-flow-real-card.md. Then cards 3-10 in order (~88 shots left). Direction shot fails twice -> aftermath plate.
- Also open: PR for branch cmo/filmformula-m4 (11478ae3, worktree /opt/MoonieXHQ/Work/task-bfc3ea80/tmp/wt4); milestone 5 done after the shoot; Flow skill field note: Omni durations are 4/6/8/10 s only (7 s fails at 0 cr); F2-true-disaster.md v1 after the pilot.
