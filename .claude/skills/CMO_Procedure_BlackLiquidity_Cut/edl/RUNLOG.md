# EDL build log — task-42e3b6af

2026-09-23. Layered EDL per CEO's 2026-09-23 ruling: no single AI writes the
whole cut's HTML any more — P1-P4 JSON layers, a deterministic composer.

- Read `SKILL.md` (full, incl. §6d avatar-composite section and its field
  notes), `template/index.html`, `scripts/bl_tools.py`, and the EP55 worked
  example `prototypes/bl55-cut/index.html` + `prototypes/bl55-realfootage/`
  before designing the schema.
- `edl/SCHEMA.md` + `edl/event_types.json` (P2-P4 open-but-checked-in type
  registry, seeded with the 12 types from §6d) + `edl/example/` (tiny 4-layer
  "epXX" made-up episode showing id cross-refs P1->P2->P4) written and
  committed.
- `scripts/bl_edl.py` (shared pure functions), `scripts/bl_compose.py`
  (layers -> index.html, P1 only; P2-P4 validated, unknown type / dangling id
  fails loudly), `scripts/bl_check.py p1` (the P1 gate: coverage, media
  exists, lipsync seated, avatar-mode legality, §6d evidence-box HARD rule).
  Import bug caught by the test suite before commit: bl_compose/bl_check
  imported `bl_edl` as a bare module while tests import `scripts.bl_edl` —
  two different module objects, so `isinstance` checks against `EDLError`
  silently failed across the boundary. Fixed by putting the repo root (not
  scripts/) on sys.path and importing via `from scripts import bl_edl`
  everywhere, matching how tests import it.
- Found mid-build: "every second covered, no gaps" (deliverable 3) is
  unsatisfiable for a real episode as originally scoped — SKILL.md measures
  the channel's approved cuts running roughly half their length as kinetic
  text on the plain kit background, no footage at all (BL51: 61%). Added
  `role: "bg"` (no media, avatar_mode must be `"none"`) so a text-only
  stretch tiles the timeline explicitly instead of being an unrepresentable
  hole. `bl_compose.py` emits nothing for it (`#bg` is already always-on).
- `tests/test_bl_compose.py`: 43/43 green, stdlib+pytest only (no numpy/
  Pillow import — deliverable 5's "import only what requirements.txt has").
  Also smoke-tested both CLIs directly (`python scripts/bl_compose.py ...`,
  `python scripts/bl_check.py p1 ...`) against `edl/example/` with throwaway
  placeholder media, not just via pytest.
- `prototypes/bl55-cut/edl/p1_layout.json`: EP55's approved cut's P1 layer,
  reverse-derived from `prototypes/bl55-cut/index.html`'s 24 `<video>` plates
  plus 5 text-only `role:"bg"` gaps (the kinetic-text stretches the original
  file's `<script>` section renders separately). `lipsync_offsets` (A=0.00,
  B=58.72, C=115.44) cross-checked against the original file's own
  `data-media-start` values for every avatar plate — exact match. Coverage
  tiles 0.00 -> 133.13s with zero gaps/overlaps
  (`bl_edl.check_coverage` clean). `real_source` for every real-footage plate
  cross-referenced against `prototypes/bl55-realfootage/REAL_MANIFEST.json`
  by the html's own inline comments (e.g. "L11 — real: WikiFX score profile
  (1.69/10)" -> `real/wikifx-profile-score.png`); no avatar-composite events
  in this episode (confirmed by grep — EP55 never uses `.avatar-comp`), so
  the §6d evidence-box check has nothing to flag on this fixture; it is
  exercised instead by `tests/test_bl_compose.py`'s synthetic overlap tests.
- No real Drive project folder was available to this worker for EP55 (the
  task gives the already-cut `prototypes/bl55-cut/index.html` as source of
  truth, not a Drive link) — generated throwaway solid-colour 1080x1920@30fps
  placeholder clips at each real clip's exact filename+duration into
  `$WORK_DIR/out/bl55-media/` (never committed) so `bl_compose.py`,
  `bl_check.py p1`, `npx hyperframes check` and `bl_tools.py sheet` could all
  run for real, not just be argued about. `bl_check.py p1` PASSED once the
  media set was complete. `npx hyperframes check` on the composed project:
  0 lint/runtime/motion errors, layout clean across 9 samples, 10/10
  contrast checks pass.
- Structural diff (composed `index.html` vs. the original approved
  `prototypes/bl55-cut/index.html`): all 24 `<video class="clip">` plates
  match exactly on `src`/`data-start`/`data-duration`/`data-media-start` (0
  diffs), `<audio>` tag matches exactly, bug date matches exactly. One real
  difference found: the original hand-authored file's `#root` carries
  `data-duration="133.2"` (a rounding slip against the audio track's real
  133.13s), while the composer correctly derives `133.13` from P1's own
  `duration` field — see the submitted report for the full list.
