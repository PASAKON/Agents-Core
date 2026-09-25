# RUNLOG task-9a4f1029 (tool-gap fixes found by Arm 1 pilot task-1a5eb073)

- start: read task-1a5eb073's REPORT.md/RUNLOG.md (origin/agent/video_editor-task-1a5eb073),
  SKILL.md (blackliquidity-cut), TOOLING.md, tools/bl_compose.py, tools/bl_checker.py,
  tools/bl_ab_run.py, build_cut.py/assemble.py/index.html at
  /opt/MoonieXHQ/Work/bl-split-ep57/generator. Confirmed `tools/bl_compose.py` (not
  `scripts/bl_compose.py`, a different tool from an unrelated task-42e3b6af) is the one
  TOOLING.md/BRIEF-*.md actually route through.
- item 2 root-cause check: pulled frames from final-arm1.mp4 at the pilot's own KIN beats
  (ffmpeg + PIL/numpy, .venv at /opt/MoonieXHQ/Agents/Core/.venv). Confirmed by eye: kinetic()
  currently has NO nowrap, so a too-long single `lines[]` entry silently multi-line-wraps
  inside its own `.wipe` span, breaking Thai mid-syllable ("วิกิ"/"เอฟเอ็กซ์" at 56s wrapped
  into 3 lines; "เช็"/"ก" split at 67s) — not a literal off-screen clip, but exactly the §6b
  defect class the task described.
- calibrated a kinetic-line width estimator from REAL pixel measurements (PIL bounding-box on
  ffmpeg frame grabs of final-arm1.mp4, both frames confirmed 1080x1920 = 1:1 with canvas px):
    "สรุปแบบไม่โลกสวย" (14 visual chars, one line, no wrap) -> 660px @82px (.bl-lg)
    "เช็กต่อว่ามีใบ"/"อนุญาตซื้อขาย"/"ฟอเร็กซ์ไหม" (10/10/9 visual chars, the SAME sentence
      Chrome itself wrapped into 3 lines) -> 445/510/411px @82px
  -> 44.5-51.0 px/visual-char (mean ~47.1); picked KINETIC_CHAR_WIDTH_RATIO=0.58 (47.6px@82px,
  a hair over the mean so the estimate over- not under-calls). "Visual" chars = Unicode
  category != Mn (excludes Thai vowel/tone marks that stack with no horizontal advance) —
  verified this matches the measured 16->14 / 10/10/9 codepoint counts exactly.
  Sanity-checked the estimator against all 15 of the pilot's real kinetic() calls
  (arm1/build/index.html): 14/15 flagged as overflow, the one genuinely-short line
  ("สรุปแบบไม่โลกสวย") passes clean — matches ground truth by eye.
- item 4 window numbers verified from the REAL generator's build_cut.py (not trusted blind):
  pick_lip()/lip_offset()/LIP_DUR give lip_a valid t0 in [0,14.9), lip_b in [68.3,82.95),
  lip_c in [137.16,152.51) — matches the task brief's own numbers exactly.
- implemented:
  1. .claude/skills/blackliquidity-cut/template/index.html: kinetic() now forces
     white-space:nowrap per line, shrinks font-size to fit the safe box down to a 32px floor
     (fitKineticLine()), throws if still over at the floor. Never mid-word wrap by construction
     (nowrap means it can only ever overflow horizontally, never re-wrap).
  2. tools/bl_compose.py:
     - load_script_line_map()/default_kin_broll(): KIN beat with no `extra["broll"]` key
       defaults to media/broll/S{n:02d}.mp4 (n from generator-dir's own SCRIPT.tsv tag->line
       map), darkened via the existing .plate-darkened class. Explicit `broll` (including a
       falsy one, to opt out) still wins. Missing SCRIPT.tsv -> no default, no crash (old
       fixtures unaffected).
     - SPOTLIGHT_EXIT_LEAD=0.08: COMP/EVID's spotlight() call now gets `t1-0.08` as its own
       `out` arg instead of `t1` -- assemble.py (off-limits, never edited) has spotlight()
       call hide(id, out-0.1) and hide()'s own duration is a hard-coded 0.18s, so the fade
       finishes at out+0.08 unless tuned from the CALLER side. Verified this matches the
       pilot's measured empty-frame cluster durations (~0.06-0.08s, 5 clusters, all
       EVID/COMP->KIN cuts) almost exactly.
     - check_avatar_window(): FF/COMP beat's t0 checked against pick_lip/lip_offset/LIP_DUR
       BEFORE composing; raises ComposeError naming the beat, its chosen lipname, and every
       valid window, instead of letting hyperframes fail after a real render attempt.
  3. tools/bl_checker.py: check_kinetic_overflow() -- regex-extracts kinetic() calls +
     their `lines[]` entries from the composed HTML (bl_compose.py now also appends a
     trailing `// TAG` comment per kinetic() call for identification), strips HTML tags,
     estimates width per the calibration above, flags anything over the 720px safe box
     (1080 - --safe-left 120 - --safe-right 240, kinetic() never applies .wide). Wired into
     run_checker()'s pass/fail and result dict (new "kinetic_overflow" key).
  4. tools/bl_ab_run.py: build_full_generator() now also copies audio-hq.mp3 to
     dest/media/voice.mp3 (assemble.py hardcodes that path; fixture-full never staged it,
     the CTO had copied it by hand for the pilot).
  5. docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md + BRIEF-seg.md: identical new bullet in
     each "Source material" list naming the 3 avatar windows verbatim (byte-for-byte
     identical wording in both, verified by a new pytest regression test comparing the
     shared spans of both files).
  6. TOOLING.md: new "task-9a4f1029 changes" section summarizing all of the above.
- tests: extended tests/test_bl_compose.py (avatar-window check, KIN default broll,
  spotlight exit-lead — 2 pre-existing short-lip tests' placeholder A2 beat changed from FF
  to KIN, since with the new avatar-window check their t0=4.0 FF placeholder would now
  (correctly) raise — that placeholder's own mode was never the point of those two tests),
  tests/test_bl_checker.py (check_kinetic_overflow, incl. a regression test reading the
  REAL pilot composition at /opt/MoonieXHQ/Work/bl-split-ep57/arm1/build/index.html --
  skips off-Contabo), tests/test_bl_ab_run.py (voice.mp3 staging, brief identity + avatar
  window wording). All green: 166 passed across test_bl_compose/bl_checker/bl_ab_run/
  bl_merge/bl_split.
