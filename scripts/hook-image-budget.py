#!/usr/bin/env python3
"""PreToolUse hook — soft budget on images entering a C-level session.

IRON-RULES §42 + CEO ruling 2026-09-25 (verbatim, task-17f60167): "บังคับผ่าน
hook ได้เลย แต่ ห้ามกันไม่ให้ c level ดูรูป ให้ดูได้เมื่อจำเป็น จริงๆ … กฏอ่อน
ถ้าคำสั่ง จาก CEO ต้องการ อันนั้นสูงกว่า" — this must never be a hard block. It
is a SOFT nudge: the (threshold+1)th image in a session is blocked exactly
once, with a message asking the model to state in one line why it needs to
look (or that the CEO asked), then the identical retried call passes and every
image after that in the session passes too.

Why images specifically: an image costs ~3k tokens and, unlike text, is
re-sent on every later turn of the session — it never leaves context. One CTO
session measured 76 images (~230k tokens re-sent per turn, estimate); the
EP57 worker's 39 images were 9.5% of its bill (see
mooniex:research/2026-09-25-token-saving-techniques-caveman-survey.md).
`hook-browser-guard.py` already caps raw chrome-tool-call volume; this hook
is narrower and orthogonal — it only counts calls that actually return image
bytes into the model's context, whichever tool produces them.

Gated calls (verified against real transcripts under
~/.claude/projects/-Users-gob-MoonieXHQ-Agents-Core/*.jsonl, task-17f60167):
  - `Read` where `file_path` ends in an image extension.
  - `mcp__claude-in-chrome__computer` with `action` in {"screenshot", "zoom"}
    — the two actions whose own tool description says they capture an image
    (screenshot: "Take a screenshot"; zoom: "Take a screenshot of a specific
    region"), and both accept the same `scale`/`save_to_disk` params.
  - `mcp__claude-in-chrome__browser_batch` — inspected recursively: each
    nested `{"name": "computer", "input": {"action": "screenshot"|"zoom"}}`
    counts as one image, since a single batch call commonly carries several.

NOT gated, on evidence: `left_click`/`type`/`key`/`wait` computer actions (0
image tool_results across 5 sampled `left_click` calls); `upload_image` (takes
an existing screenshot ID, returns no image to the model) and `gif_creator`
(records/exports, does not return image bytes) never appeared as an
image-producing tool_use in the sampled transcripts. One anomaly: a single
sampled `scroll` action did return an image tool_result (probably the
extension auto-attaching a post-scroll screenshot) — left ungated because the
sample is n=1 against 0/5 for click, and counting every scroll would produce
far more false "Nth image" nudges than the one it would catch. Documented in
docs/ops/image-budget-hook-2026-09-25.md.

Exemptions (exit 0, nothing counted, no state written):
  - cwd contains `/worktrees/` — a DEV worker's own worktree.
  - env `WORKER_TASK_ID` is set — the marker `runners/worker_init.py` exports
    onto every DEV process before exec.
A C-level session's cwd is the repo root, never a worktree, and it has no
WORKER_TASK_ID — so neither exemption fires for it.

State: state/image-budget/<session_id>.json — {"count": int,
"blocked_hashes": [sha1, ...]}. `blocked_hashes` remembers which exact calls
(sha1 of tool_name + canonical JSON of tool_input) have already been shown
the nudge once, so the identical retry — and only the identical retry — is
let through without asking twice.

Reads the Claude Code hook event from stdin:
  {"session_id": "...", "cwd": "...", "tool_name": "Read",
   "tool_input": {"file_path": "..."}, ...}

Exit 0 = allow (silent). Exit 2 = block once, stderr goes back to the model
so it can retry. FAIL-OPEN: any exception, or malformed/missing stdin,
exits 0 silently — a broken guard must never stop a C-level session from
doing its job.

Threshold: env `ORG_IMAGE_BUDGET`, default 8 (so the 9th image is the first
one nudged). Raise it for one session with `ORG_IMAGE_BUDGET=<n>`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

STATE_DIR_ENV = os.environ.get("ORG_IMAGE_STATE_DIR")
if STATE_DIR_ENV:
    STATE_DIR = Path(STATE_DIR_ENV)
else:
    STATE_DIR = Path(__file__).resolve().parent.parent / "state" / "image-budget"

DEFAULT_THRESHOLD = 8
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
IMAGE_ACTIONS = {"screenshot", "zoom"}

NUDGE_TEMPLATE = (
    "รูปที่ {n} ใน C-level session นี้ (≈3k token/รูป ส่งซ้ำทุก turn) — "
    "ถ้าต้องตัดสินด้วยตาเอง หรือ CEO สั่งให้ดู ให้เขียนเหตุผล 1 บรรทัดแล้วเรียกซ้ำ "
    "ไม่งั้น delegate browser_operator / contact sheet / อ่านเป็น text (IRON §42)\n"
)


def _threshold() -> int:
    raw = os.environ.get("ORG_IMAGE_BUDGET")
    if not raw:
        return DEFAULT_THRESHOLD
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_THRESHOLD


def _images_in_call(tool_name: str, tool_input: dict) -> int:
    if tool_name == "Read":
        path = str(tool_input.get("file_path") or "")
        return 1 if path.lower().endswith(IMAGE_EXTENSIONS) else 0

    if tool_name == "mcp__claude-in-chrome__computer":
        action = tool_input.get("action")
        return 1 if action in IMAGE_ACTIONS else 0

    if tool_name == "mcp__claude-in-chrome__browser_batch":
        count = 0
        for item in tool_input.get("actions") or []:
            if not isinstance(item, dict) or item.get("name") != "computer":
                continue
            sub_input = item.get("input")
            if isinstance(sub_input, dict) and sub_input.get("action") in IMAGE_ACTIONS:
                count += 1
        return count

    return 0


def _call_hash(tool_name: str, tool_input: dict) -> str:
    canon = json.dumps(tool_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(f"{tool_name}:{canon}".encode("utf-8")).hexdigest()


def main() -> int:
    try:
        event = json.load(sys.stdin)

        cwd = str(event.get("cwd") or "")
        if "/worktrees/" in cwd:
            return 0
        if os.environ.get("WORKER_TASK_ID"):
            return 0

        tool_name = str(event.get("tool_name") or event.get("tool") or "")
        tool_input = event.get("tool_input")
        if not isinstance(tool_input, dict):
            tool_input = {}

        n_images = _images_in_call(tool_name, tool_input)
        if n_images <= 0:
            return 0

        session = str(event.get("session_id") or "unknown").replace("/", "_")
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_path = STATE_DIR / f"{session}.json"

        try:
            state = json.loads(state_path.read_text())
        except Exception:
            state = {}
        count = int(state.get("count", 0))
        blocked_hashes = set(state.get("blocked_hashes") or [])

        new_count = count + n_images
        threshold = _threshold()

        if new_count <= threshold:
            state["count"] = new_count
            state_path.write_text(json.dumps(state))
            return 0

        call_hash = _call_hash(tool_name, tool_input)
        if call_hash in blocked_hashes:
            state["count"] = new_count
            state_path.write_text(json.dumps(state))
            return 0

        blocked_hashes.add(call_hash)
        state["blocked_hashes"] = sorted(blocked_hashes)
        state_path.write_text(json.dumps(state))

        sys.stderr.write(NUDGE_TEMPLATE.format(n=new_count))
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
