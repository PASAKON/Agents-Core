# openhiggsfield STATUS (PH#81f3a010, CMO lane)
Milestones live in the registry (`tools/portfolio.py show openhiggsfield`). Notes only here.
- 29 Oct 12:50 TH: read wide-trace/open-higgsfield b16a0ef + D3voz/openjutsu 47c3724 (MIT). Openjutsu = likely "OpenJetsu".
- REPORT: docs/reports/openhiggsfield/REPORT.md. Research cache: Wikis research/2026-10-29-open-higgsfield-repo-and-higgsfield-api-price.md (uncommitted in Wikis).
- Clones deleted from /opt/MoonieXHQ/Work/openhiggsfield after the read.
- 29 Oct 12:21 TH: card Q-20261029-0520-783a raised (study only recommended); waiting.
- 29 Oct 12:25 TH: CEO answered Q-…-783a: study time+cost per GPU first, Colab suggested for a test. task-43a3c5c2 briefed (task-0628170b was a dead duplicate: unknown project) (study, $0).
- 30 Oct 03:40 TH: task-43a3c5c2 cancelled by queue GC (never ran, budget defer); PH wrote GPU-STUDY.md itself. Card Q-20261029-2037-4576 raised (Colab A100 1-clip test recommended). Wikis ce445db.
- 30 Oct 03:50 TH: CEO Q-…-4576 = Colab A100 1-clip test on MyPasakon IMG_6014 (MG → Porsche). Answer card Q-20261029-2042-5a76 (setup estimate corrected: ~5-8 min, our Colab runner measured 168 s cold). Worker task-ca40560b (ComfyRunpod branch ph81f/openjutsu-colab-take) tier-deferred; blocker to CMO for tier.
- 30 Oct 03:55 TH: CEO Q-…-5a76 = go. CMO set tier normal; task-ca40560b re-delegated, still in budget queue (router picked codex, bucket over). Zero-model watcher running.
- 30 Oct 04:20 TH: CEO in chat: switch to Sonnet, wants the clip today; shut the Colab VM after use. task-7280b72c (override: ceo-order, claude-sonnet-5-5) spawned; task-ca40560b cancelled. config/projects.yaml got paths.contabo for comfy-runpod-worker.
- 30 Oct 05:35 TH: task-7280b72c done (461 tests, PH re-ran). Spec retargeted car → steering wheel (clip has no exterior), ref n1_cockpit_redwheel_v2. PR #41 opened; my gh pr merge refused by classifier → CEO cards RUN-20261029-2232-f1b0 (merge+pull) then RUN-20261029-2233-bb09 (run, cap 4 CU, unlabelled: run_take has no --max-credits; colab_batch pins pre-#41 files). Ready list: state/handoff/2026-10-30/ph-81f3a010-merge-ready-list.md.
- 30 Oct 09:20 TH: merge #41 landed (3eff1c5, pull 02:18:36Z). bb09 ran 10 s earlier on old code: spec error, exit 2, 0 CU. Live dry run passes. Retry card RUN-20261030-0219-7768.
- 30 Oct 09:27 TH: RUN-20261030-0219-7768 exit 0. RTX PRO 6000 96 GB, setup 218 s (52 GB weights), render ~53 s, wall 346 s, 0.69 CU (677.30→676.61). VM stopped, still listed 0. Clip sent to CEO. Wheel swapped to red/black Porsche-style with crest (red from the ref, spec said black).
- 30 Oct 09:45 TH: project closed in registry. Clip kept at /opt/MoonieXHQ/Work/task-7280b72c/ (214 MB) pending CEO verdict (Drive or delete). Branch agent/developer-task-7280b72c left in ComfyRunpod (holds only REPORT.md commit 299aa04).
- 30 Oct 12:52 TH: resumed by CMO (CEO asked). Registry row closed for good; work logged here. Verdict card Q-20261030-0551-f9a0 (clip as media, ใช้ได้/แก้/ไม่เอา). Keep /opt/MoonieXHQ/Work/task-7280b72c.
- 30 Oct 12:55 TH: CEO Q-20261030-0551-f9a0 = ใช้ได้ ("พอได้นะแต่คิดว่าคุณทำได้ดีกว่านี้ ขอลิ้งแชร์ให้เพื่อน"). Clip on Drive UNKNOWN id 1_GENrIuXDyND3E9hKJWTs6rROZ6gQB4J, md5 ea933f4f… matches. My public-share call refused [Permission Grant] → card RUN-20261030-0555-8669 (share_link.py sha256 eda1410f…).
- 30 Oct 12:56 TH: RUN-20261030-0555-8669 exit 0; link public (anyone reader), checked by permissions read + HTTP 200 logged out.
- 30 Oct 13:35 TH: CMO relays CEO order (friend consented, private, never posted): build openjutsu_people. Worker task-80d3eb98 (contabo, router → agy). Private dir /opt/MoonieXHQ/Work/openhiggsfield-people (700): photo + outputs only there and on the VM, never git/Drive/logs/cards.
- 30 Oct 13:40 TH: task-80d3eb98 (agy) failed at once: headless agy cannot run shell (command permission auto-denied). Re-created as task-0c010b41, Sonnet, override quota-handoff (codex out to 4 Nov).
- 30 Oct 14:25 TH: task-0c010b41 PR #43 (head e34e69f): simple.api.json @d7e405c, 1 ref, VM scrub. PH re-ran tests: all passed (worker: 548). Spec budget set 30 min / 4 CU. My merge refused [Merge Without Review] → card RUN-20261030-0725-2de3. Ready list state/handoff/2026-10-30/ph-81f3a010-merge-ready-list-people.md.
- 30 Oct 14:55 TH: merge card 2de3 exit 0 (c0eb0d9 live, dry run passes). Run card refused: hub spend label now ENFORCED (spend_label_required; labelled spend needs a script card for a listed cap reader; colab_batch pins 4144ad1 and refuses openjutsu). Blocker to CMO with options A (extend colab_batch) / B (run_take --max-credits + declared cap reader). Worker task-0c010b41 closed to free RAM.
- 30 Oct 15:10 TH: route B dropped (script cards: Agents-Core only; .json graphs not written). Route A: task-d9603926 (Sonnet, winbox; Mac has no launcher, Contabo >80%) extends colab_batch for openjutsu. CTO review checks sent to the worker.
- 30 Oct 15:15 TH: CTO pre-review: openjutsu takes G4 only; spec now G4/[] 60 min / 8 CU (CMO call); card --max-credits 8.5, expected ~2-4 CU. Checklist passed to worker d96.
- 30 Oct 15:50 TH: #596 merged (b3c787a). 0-CU check: job loads, interpreter trusted, pins match c0eb0d9, temp tree under take dir and removed. Run card RUN-20261030-0847-fff5 (labelled script, colab_batch --max-credits 8.5, est 2-4 CU, balance 676.61).
- 30 Oct 15:57 TH: RUN-20261030-0847-fff5 exit 0, wall 475 s, 1.00 CU (676.61→675.61). Clip 14.4 s 480x864 24 fps + audio, private path sent to CMO (not viewed). VM scrub removed 5, teardown still listed 0, no snapshot dir left. DMAD rank-128 substitute. task-d9603926 merged/closed (winbox claude 7120 stopped).
- 30 Oct 16:15 TH: CEO: round 1 likeness weak. 2a (720p single daylight face ref) prepared + dry-run ok (takes2/ohf-people-2, waits for CEO photo). 2b task-8b0f5fea (winbox Sonnet: multi-ref ≤4, steps 4-12, face_refine) queued: tier_defer budget (2 ahead).
- 30 Oct 16:25 TH: 2a card RUN-20261030-0913-c8ff (720p, ref_3, cap 4.5) CANCELLED on CTO hold: task-8b0f5fea worker holds the CPU-exception slot, swap 4031/4095. Re-raise when the worker ends or Contabo <80%.
- 30 Oct 16:25 TH: 2a RUN-20261030-0913-c8ff ran (CEO tapped before the hold): exit 0, 578 s, 0.85 CU (→674.76). Clip 736x1312 14.4 s + audio, private path to CMO. Scrub 5, still listed 0. 2b task-8b0f5fea on contabo (Codex) in progress.
- 30 Oct 16:45 TH: CEO 2a 'ไม่เหมือน'. 2b done by Codex (e98114c pushed, no PR; multi-ref = separate subject slots; face pass 100 GB). New A: task-3edba499 faceswap (inswapper+GFPGAN, yaw pick), stacked on 2b, queued tier_defer → asked CMO/CTO for critical.
- 30 Oct 16:55 TH: PH re-ran 2b tests in its worktree (e98114c): all passed.

## Parked 2026-10-30 ~18:40 TH (CMO order: Contabo RAM for CTO)
- State: Phase 2 friend swap. Rounds 1 (ref_1, 1.00 CU) and 2a (ref_3, 0.85 CU) ran; CEO: not alike. Balance 674.76.
- B (multi-ref, steps, face_refine): task-8b0f5fea, branch agent/codex-task-8b0f5fea @ e98114c, pushed, tests pass, no PR.
- A (faceswap: InsightFace + inswapper + GFPGAN): task-3edba499, in review. Must stack on e98114c.
- Not done: one combined B+A PR to MoonieX-ComfyRunpod, merge+pull card, colab_batch re-pin PR (CTO Main merges).
- Next on resume: review task-3edba499 diff + privacy/scrub, run tests in its worktree, open the PR, merge card,
  re-pin, then faceswap take in <W>/takes3 (ref_3 + ref_4, G4, max_cu 2, --max-credits 2.5). B run only if CEO asks.
- Open cards: none pending. Colab VM: none assigned (round 2a torn down, still listed 0).
- Private files stay in /opt/MoonieXHQ/Work/openhiggsfield-people/ only.
