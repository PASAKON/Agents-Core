# REPORT task-d4c1f234

# task-d4c1f234 — EP58 geometry measurement; production blocked

Status: INCOMPLETE. No v3 final, test render, or production geometry change. The new measurement tool and regression tests are implemented in this worktree. No claim of visual or face-gate acceptance is made.

## Implementation

- `tools/bl_face_box.py`: imports safely; reads `.avatar-comp` height, bottom, left and translateX from template CSS; transforms source envelopes with outward rounding; samples the three matte takes at 0.5-second intervals; records alpha row profiles and 60/64/68% candidates. Missing frames/alpha and unsupported CSS fail explicitly.
- `prototypes/bl-ep58/armA/face_box.py`: delegates to the shared tool, removing the fixed S=0.56 and y+845 transform. CLI now requires `--matte-dir` and `--output`; see `--help`.
- `tests/test_bl_face_box.py`: CSS scale/shift extraction, bottom-anchored scaling, outward rounding, early-neck false-pass regression, empty alpha and unsupported CSS.
- `face-measurements.json`: sampled source envelopes, per-frame profiles and candidate canvas boxes. A supplied chin bound is not automatically certified by the tool.

## Measurement and visual diagnosis

Read the three preceding reports and the BL cut skill. Inspected source RGB frames lip_a at take 9.3 s, lip_b at take 5 s, lip_c at take 11 s, plus lip_a alpha at 9.3 s (half-resolution PNGs under /tmp). These are decoded source frames, not test renders.

- lip_a 9.3: mouth/chin extends well below the old search endpoint; silhouette narrows through the jaw/neck and widens at shoulders. Old early minimum is not a reliable chin landmark.
- lip_b 5.0: chin is around source y=1020; source y=1100 is below it in this inspected frame.
- lip_c 11.0: chin is around source y=1040; source y=1100 is below it in this inspected frame.
- lip_a alpha 9.3: connected face/neck silhouette has no semantic chin boundary. Alpha alone cannot certify chin position.

Measured 32 lip_a, 34 lip_b and 13 lip_c alpha frames. The legacy selected row ranges were 224–883, 354–893 and 402–811 respectively: some minima are on the hat/head, not the neck.

Used source y=1100 inclusive as a conservative lower bound for the candidate calculation. This has NOT been visually validated across every frame; JSON explicitly says `chin_verified: false`. The old heuristic searches only top+120 through top+519; it can stop above the mouth. Do not use its original boxes as certified face coverage.

The fixed two-line pill top is 1218; required avatar box bottom is <=1198. With the conservative bound, all three takes have candidate bottom 1429 at 60% (clearance -211), 1396 at 64% (-178), and 1364 at 68% (-146). NONE qualifies. Exact per-take boxes (conservative head envelope, possibly including hands/shoulders at the lower rows):

| Take | 60% box x,y,w,h | 64% box | 68% box |
|---|---|---|---|
| lip_a | [-27, 830, 572, 599] | [-29, 757, 610, 639] | [-30, 685, 647, 679] |
| lip_b | [-7, 908, 617, 521] | [-7, 840, 657, 556] | [-8, 773, 699, 591] |
| lip_c | [67, 937, 418, 492] | [71, 871, 447, 525] | [76, 806, 474, 558] |

Next candidate for a test render: 68% plus bottom:166px (an additional upward shift), yielding conservative box bottom <=1198. This is a geometric proposal, not an accepted design: it raises the head/evidence collision risk and moves the torso's lower edge. It must be inspected in the two requested windows before editing production geometry or proceeding to all-window renders. Scale alone would need approximately 88.16% with this conservative envelope, which is substantially larger than the proposed range.

## Coupling audit / remaining build work

- Template `.avatar-comp` is still 56%; both arms still share it.
- `scripts/bl_edl.py:42` has another coupled constant: AVATAR_BOX x0=0,y0=845,x1=480,y1=1920. Tests in `tests/test_bl_compose.py` also describe it. Include this in the eventual geometry update.
- `bl_checker.placed_box()` already subtracts COMP evidence shift; `bl_compose.emit_pieces()` shifts both the image and spotlight. Keep these transformations consistent when selecting new evidence placements.
- Checker caption band remains its existing conservative 0.62–0.72H; no gate was weakened to pass the candidate.
- Template, evidence shifts, arm-B goldens, beats and old render metadata have not been modified without the required test-render decision. Arm B 16.7/opening crop and MAIN-13/CONTEXT-4 work remains pending in the specified sequence.

## Environment blockers

The enforced filesystem policy allows writes only inside this worktree and /tmp, and explicitly disallows escalation (`approval_policy=never`). Both required Work v3 directories and `/opt/MoonieXHQ/Work/.bl-render.lock` are outside those roots. User authorization does not extend the enforced sandbox. No Work write or render was attempted, and no v2 final was overwritten. A session with those output directories and the shared lock writable is required to execute steps 3–5.

The worktree `.git` points to `/opt/MoonieXHQ/Agents/Core/.git/worktrees/mooniex-agents__developer__task-d4c1f234`, outside writable roots; `.git` is explicitly read-only. Therefore commits/push cannot be completed within this policy. Changes remain in the requested worktree on `agent/codex-task-d4c1f234`.

No `mcp__org__wiki_read` or `mcp__org__submit_report` tool is exposed in the available tool catalog, and no tool-search capability is exposed. Wiki reading and CTO submission could not be performed. This report is the local handoff; task completion has not been submitted.

## Acceptance — one status per requirement

- text_over_face, both arms, real per-take COMP/FF boxes: NOT PASSED / NOT RUN. Candidate measurements are not full-frame FF boxes; do not apply a COMP box to arm B SUMMARY-7..9 FF.
- Per-box beat list: NOT CERTIFIED. lip_a COMP: HOOK-1..4, PATTERN-1..3; lip_b COMP: MAIN-5..11; lip_c COMP: arm A SUMMARY-7..9 only. Arm B SUMMARY-7..9 requires a separately measured FF box. Sampled windows use the original script's 0–15.9, 39.28–55.9, 88.69–95.0 bounds; clip/beat tail coverage must be checked before acceptance.
- Brand mark >=95% on every frame, t=0 and seams, both arms: NOT RUN for v3.
- bl_merge --beats gates, both arms: NOT RUN for v3.
- bl_tools verify with three original lip seats, both arms: NOT RUN for v3.
- bl_checker --video --beats with face boxes, both arms: NOT RUN for v3.
- Requested final-frame visual review and per-seam review: NOT RUN; no v3 frames exist. No old-render verdict is substituted.
- Same avatar geometry in both arms: existing shared geometry preserved; proposed replacement not applied.
- v3 MP4s and contact sheets at requested Work paths: NOT CREATED.
- Required source changes, commits, push, per-arm v3 render metadata: INCOMPLETE; no old render metadata relabeled as v3.

## Validation

Command: `PATH=/opt/MoonieXHQ/Agents/Core/.venv/bin:$PATH python -m pytest tests/test_bl_*.py` from this worktree. PASS, exit 0 (all collected BL tests; console log saved alongside this report as `pytest.txt`). `git diff --check` also passed. Bare `python` is absent from the original shell PATH.

## Skill learning

- WRONG — CMO_Procedure_BlackLiquidity_Cut, face-box gate field notes: the EP58 early alpha minimum is not a certified chin boundary; its search can end above the mouth. Preserve a reviewed chin bound and report sample scope before accepting scale changes.
- MISSING — CMO_Procedure_BlackLiquidity_Cut, §9: production tasks need writable Work output directories and shared render lock, plus writable worktree git metadata, before dispatch into a restricted session.
