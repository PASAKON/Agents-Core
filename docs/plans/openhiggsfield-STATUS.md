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
