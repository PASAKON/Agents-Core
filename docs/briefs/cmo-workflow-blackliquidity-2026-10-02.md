# Brief — CMO writes `CMO_Workflow_BlackLiquidity` (SKILL.md + flow.yaml)

From: CTO (winbox) · To: CMO (BL lane) · 2026-10-02 · CEO ruling the same day: "ให้คุณ สั่งให้ CMO เขียน แต่เขียนออกมาในรูปแบบกฏที่คุณตั้งไว้ เพื่อง่ายต่อการ coding"
(the CMO writes the BL workflow, in the format the CTO set, so the Console can draw it as a Flow).

## Why

The CEO wants a Control Room for ClaudeFlow: an n8n-like board showing what each node does, whether it spends
tokens or API credit, when it runs, where a run is now, what is red (waits for the CEO) or orange (the watcher
fixes it), what one run costs, and how much of the flow is automatic. The board reads one file per workflow:
`flow.yaml` beside the Workflow skill. BL is the first: there is no BL Workflow skill yet. Four BL skills own
the parts (`CMO_Standard_BlackLiquidity_Script`, `CMO_Procedure_BlackLiquidity_JevEditor`,
`CMO_Procedure_BlackLiquidity_Cut` and its tools), and nothing ties them end to end.

## Read first (in this order)

1. `.claude/skills/ALL_Protocol_SkillAuthor/references/workflow-flow.md` — the contract: keys, node kinds,
   stages, blocker codes, the SKILL.md binding, rules F1–F14. **This is the format.** Do not invent keys.
2. `.claude/skills/ALL_Protocol_SkillAuthor/SKILL.md` §4 (create) and §9 (the Workflow template).
3. `.claude/skills/CMO_Workflow_ShortFilm/SKILL.md` — the prose model for a Workflow.

## Deliver

- `.claude/skills/CMO_Workflow_BlackLiquidity/SKILL.md` — `kind: workflow`, `owner: CMO`, scaffolded with
  `skill-curator.py create … --kind workflow --owner CMO`; the steps are `### Step <n> · <name> [node: <id>]`.
- `.claude/skills/CMO_Workflow_BlackLiquidity/flow.yaml` — `flow: bl`.
- `docs/org/SKILL-INDEX.md` regenerated (`skill-curator.py index`), committed with the skill.
- One commit `skill(CMO_Workflow_BlackLiquidity): new — BL end to end as a Flow — evidence <this brief + task>`.

## The starting graph — the CTO's draft; correct it from the source

17 nodes, ids fixed unless you have a reason (the Control Room mock-up already uses them). `?` = verify.

| id | kind | does (draft) | tool / skill / provider (draft) |
|---|---|---|---|
| `script` | agent | writes the episode script | role cmo, skill CMO_Standard_BlackLiquidity_Script |
| `approve` | human | the CEO approves the script | approver CEO |
| `drive` | code | files the approved script to the project folder | ClaudeFlow? |
| `tts` | api | the avatar's Thai voice | `claudeflow:<?>`, provider fal |
| `prompts` | api | image/scene prompts | `claudeflow:<?>`, provider openrouter |
| `transcript` | api | word timings | `claudeflow:<?>`, provider fal (whisper) |
| `lipsync` | api | lip-synced avatar plates | `claudeflow:<?>`, provider fal (sync-lipsync) |
| `scenes` | api | B-roll clips | `claudeflow:<?>`, provider fal (Kling) |
| `handoff` | code | `_MANIFEST.json` + the project hand-off | `claudeflow:<?>` |
| `jev` | model | per-line editorial calls | skill CMO_Procedure_BlackLiquidity_JevEditor, `tools/decide.py`?, provider jev |
| `footage` | agent | real footage | role browser_operator, skill ? |
| `scripter` | model | one-shot edit plan | `tools/bl_scripter.py`, provider ? |
| `compose` | code | builds the composition | `tools/bl_compose.py` |
| `checker` | code | the gates | `tools/bl_checker.py` |
| `editor` | agent | fixes and finishes the cut | role video_editor, skill CMO_Procedure_BlackLiquidity_Cut |
| `review` | human | the CEO watches the cut | approver CEO |
| `publish` | code? | posts to TikTok with the cart link | `tools/bl_tiktok_cta.py` / `tools/bl_tiktok_watch.py`?, `release: true` |

Draft edges: script→approve→drive→{tts, prompts}; tts→{transcript, lipsync, scenes}; prompts→scenes;
{transcript, lipsync, scenes}→handoff→{jev, footage}; jev→scripter→compose; footage→compose;
compose→checker→editor→review→publish.

## Verify at the source (do not guess — leave a `TODO(cmo)` in the step prose if you cannot)

1. **Who picks the topic**, and is it a node before `script` (an agent or the CEO)?
2. **Publish: manual or a tool?** If a person posts, `publish` is `kind: human`.
3. **The ClaudeFlow stage behind each api node.** Map them from `_MANIFEST.json` stages and the
   stage-runner on Contabo (`/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow`); write the tool as
   `claudeflow:<path>`.
4. **Trigger and watcher.** Manual by the CEO today? Which session watches (`CMO@contabo`)?
5. **`editor` stage.** `agent` today. `shadow` only if a candidate and a scorer already exist and run
   (`tools/bl_compose.py` + `tools/bl_score.py`?). The A/B of 2026-09-25 is the evidence
   (`docs/ops/bl-ab-2026-09-25/REPORT.md`, `docs/ops/bl-split-ab-2026-09-25/`): the scripter alone failed
   the checker in both runs.
6. **Hosts:** what runs on Contabo, what runs on the Mac.

## Numbers to carry (each with its source and date — F14)

- An EP57 full edit: 760 turns, ~4 h, $99.79 API-equivalent.
- The 30-second A/B (`bl_compose`): full edit $3.73 / 82 turns; blind fix $1.40 / 43 turns; scripter alone
  $0.26 / 3 calls / 88 s.
- fal for all of EP52: $0.71. Unit costs: TTS $0.00058/s, sync-lipsync $0.0117/s, Kling $0.56/clip,
  whisper ≈ $0.03/min.

Put a number under `measured` only when you can cite where it was measured. A unit price goes in `unit_cost`.
A node with no number stays without one: the board shows it as unknown, never as a guess.

## Rules for this job

- **No spend.** Writing the workflow runs no generation. If you think a run is needed to measure something,
  ask the CEO with the exact amount first (`ALL_Rules_Approvals`).
- **Pointers, not copies.** Each step's prose says how to work through it, and the owner skill keeps the
  rules. Never paste a BL rule into the workflow.
- **Do not change the BL tools or the other BL skills** in this task. A gap you find there becomes a Field
  note on the owner skill.

## Done when

```bash
.venv/bin/python scripts/flow-lint.py check CMO_Workflow_BlackLiquidity   # flow-lint: clean
.venv/bin/python scripts/skill-lint.py check | grep BlackLiquidity         # nothing new
.venv/bin/python scripts/flow-lint.py export CMO_Workflow_BlackLiquidity   # paste its "stats" in the report
```

Report to the CTO: the commit sha, the `stats` block, the answers to the six questions above, and every
`TODO(cmo)` left open. After the CTO reviews it, the CEO takes a one-glance look.
