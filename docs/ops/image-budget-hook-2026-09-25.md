# Image budget hook — 2026-09-25 (task-17f60167)

`scripts/hook-image-budget.py`, wired as a `PreToolUse` hook. IRON-RULES §42 +
CEO ruling 2026-09-25 (verbatim): "บังคับผ่าน hook ได้เลย แต่ ห้ามกันไม่ให้
c level ดูรูป ให้ดูได้เมื่อจำเป็น จริงๆ … กฏอ่อน ถ้าคำสั่ง จาก CEO ต้องการ
อันนั้นสูงกว่า" — soft rule. Never a hard block: the (threshold+1)th image in
a C-level session is blocked exactly once, asking the model to state in one
line why it needs to look (or that the CEO asked); the identical retried call
then passes, and so does every image after it in that session.

## Why

An image costs ~3k tokens and, unlike text, never leaves context — it is
re-sent on every later turn. One CTO session carried 76 images (~230k tokens
re-sent per turn, estimate); the EP57 worker's 39 images were 9.5% of its
bill. See `mooniex:research/2026-09-25-token-saving-techniques-caveman-survey.md`.

## Gated calls (verified against real transcripts, `~/.claude/projects/-Users-gob-MoonieXHQ-Agents-Core/*.jsonl`)

| Call | Condition | Evidence |
|---|---|---|
| `Read` | `file_path` ends in `.png`/`.jpg`/`.jpeg`/`.gif`/`.webp`/`.bmp` (case-insensitive) | sampled `Read` calls on `.png` screenshots all returned an `image` content block |
| `mcp__claude-in-chrome__computer` | `action` is `screenshot` or `zoom` | 4/4 sampled `screenshot` calls returned an image; `zoom` shares the same `scale`/`save_to_disk` params and its own description says "take a screenshot of a specific region" |
| `mcp__claude-in-chrome__browser_batch` | any nested `{"name":"computer","input":{"action":"screenshot"\|"zoom"}}` — counted per nested occurrence | sampled batches routinely nest a `computer` screenshot alongside `navigate`/`get_page_text` steps |

**Not gated, on evidence:**
- `left_click`/`type`/`key`/`wait` `computer` actions — 0/5 sampled `left_click` calls returned an image.
- `mcp__claude-in-chrome__upload_image` — takes an existing screenshot ID and uploads it to a page; returns no image to the model. Never appeared as an image-producing call in the sample.
- `mcp__claude-in-chrome__gif_creator` — records/exports frames already captured elsewhere; does not return image bytes to the model. Never appeared as an image-producing call in the sample.
- `mcp__claude-in-chrome__find` — returns element references (text), never an image.

**Known gap, documented not fixed:** one sampled `scroll` action (`computer`)
also returned an image tool_result, likely the extension auto-attaching a
post-scroll screenshot. Left ungated: the sample is n=1 against 0/5 for
`left_click`, and gating every `scroll` would produce far more false "Nth
image" nudges (scrolling is common, screenshotting is not) than the single
miss it would fix. Revisit if a future session shows this is systematic
rather than anomalous.

## Threshold and exemptions

- Threshold: env `ORG_IMAGE_BUDGET`, default **8** (so the 9th image in a
  session is the first one nudged). Raise it for one session:
  `ORG_IMAGE_BUDGET=20 <launch command>`.
- Exempt (nothing counted, no state written):
  - cwd contains `/worktrees/` — a DEV worker's own worktree.
  - env `WORKER_TASK_ID` set — the marker `runners/worker_init.py` exports on
    every DEV process before exec.
- A C-level session's cwd is the repo root (never a worktree) and carries no
  `WORKER_TASK_ID`, so neither exemption fires for it — this is the intended
  target of the hook.

## State

`state/image-budget/<session_id>.json` (gitignored via
`state/image-budget/.gitignore`):

```json
{"count": 9, "blocked_hashes": ["1ca5257f5501f85b2a0256d36b6a248bf6f1ebb8"]}
```

`blocked_hashes` is `sha1(tool_name + ":" + canonical_json(tool_input))` for
every call already shown the nudge once — so the identical retry (and only
the identical retry) passes silently. A genuinely different call past the
threshold gets its own single nudge.

Override the state directory with env `ORG_IMAGE_STATE_DIR` (used by the test
suite to point at `tmp_path`; never point it at the real `state/` or `$HOME`
outside tests).

## Rollback

Remove the `hook-image-budget.py` entry from `.claude/settings.json`'s
`PreToolUse` array (the block with
`"matcher": "Read|mcp__claude-in-chrome__computer|mcp__claude-in-chrome__browser_batch"`).
No other file needs to change — the script and its state directory are inert
once unwired.

## Verified manually (2026-09-25, `env -u WORKER_TASK_ID`)

8 `Read` calls of `.png` paths all exited 0; the 9th exited 2 with the Thai
nudge; the identical 9th retry exited 0; state file showed
`{"count": 9, "blocked_hashes": [...]}`. See `docs/reports/task-17f60167/REPORT.md`
for the full test run.
