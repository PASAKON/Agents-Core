#!/usr/bin/env python3
"""File a completed research workflow into the org research library (IRON §47).

A research sweep that lives only in a temp file is research the org will pay for
twice. On 2026-09-03 two sweeps — one of them ten agents and roughly 1.1M tokens
— existed nowhere but /tmp until someone noticed. This exists so nobody has to
notice.

Usage:
    python3 scripts/research-file.py <task-id> --title "..." --question "..." \
        [--method "..."] [--keys comparison,critic] [--dry-run]

    task-id     the Workflow tool's task id, e.g. wmamv83fu
    --title     the page title
    --question  the question this research answers, one line, for the index
    --method    how it was run; defaults to a summary read off the run itself
    --keys      which keys of the workflow's return value to include, in order.
                Defaults to every string-valued key, longest first.

Writes YYYY-MM-DD-<slug>.md into the research library and prints the path.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import sys

LIBRARY = os.environ.get(
    "RESEARCH_LIBRARY", "/Users/gob/MoonieXHQ/Agents/Rules/research"
)
TASK_DIRS = glob.glob(
    "/private/tmp/claude-501/-Users-gob-Projects-Agents/*/tasks"
) + glob.glob(os.path.expanduser("~/.claude/projects/*/tasks"))


def find_output(task_id: str) -> str:
    """Locate a workflow's output file across session scratch directories."""
    for d in TASK_DIRS:
        p = os.path.join(d, f"{task_id}.output")
        if os.path.exists(p):
            return p
    raise SystemExit(
        f"no output file for {task_id}\n"
        f"looked in:\n  " + "\n  ".join(TASK_DIRS)
    )


def load(path: str) -> tuple[dict, dict]:
    """Return (envelope, result). The result may be a JSON string or an object."""
    env = json.loads(open(path).read())
    res = env.get("result")
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except json.JSONDecodeError:
            res = {"result": res}
    if not isinstance(res, dict):
        res = {"result": str(res)}
    return env, res


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "-".join(s.split("-")[:8]) or "research"


def build(env: dict, res: dict, args, task_id: str) -> str:
    usage = env.get("usage") or {}
    agents = usage.get("agent_count") or env.get("agentCount")
    tokens = usage.get("subagent_tokens") or env.get("totalTokens")

    if args.method:
        method = args.method
    else:
        bits = []
        if agents:
            bits.append(f"{agents} agents")
        if tokens:
            bits.append(f"~{round(int(tokens) / 1_000_000, 1)}M tokens")
        method = ", ".join(bits) or "not recorded"

    if args.keys:
        keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    else:
        keys = sorted(
            (k for k, v in res.items() if isinstance(v, str) and len(v) > 200),
            key=lambda k: -len(res[k]),
        )
    if not keys:
        raise SystemExit(
            "nothing substantial to file — the workflow returned no long string "
            "values. Pass --keys explicitly if the content is nested."
        )

    today = _dt.date.today().isoformat()
    out = [
        f"# {args.title}\n",
        f"**Question** {args.question}  ",
        f"**Researched** {today} · workflow run `{task_id}`  ",
        f"**Method** {method}\n",
        "> Agents were instructed to return empty rather than invent sources.",
        "> Evidence levels are stated per finding: official / practitioner /",
        "> secondhand / inference. See `README.md` for why that matters.\n",
        "---\n",
    ]
    for k in keys:
        out.append(f"\n## {k.replace('_', ' ').upper()}\n\n{res[k]}\n")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id")
    ap.add_argument("--title", required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--method")
    ap.add_argument("--keys")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = find_output(args.task_id)
    env, res = load(src)
    page = build(env, res, args, args.task_id)

    name = f"{_dt.date.today().isoformat()}-{slugify(args.question)}.md"
    dest = os.path.join(LIBRARY, name)

    if args.dry_run:
        print(f"would write {dest}  ({len(page) // 1024}KB)")
        print(page[:700])
        return 0

    if os.path.exists(dest):
        raise SystemExit(
            f"{dest} already exists.\n"
            "IRON §47: update the existing page in place rather than writing a "
            "second page on the same question."
        )

    os.makedirs(LIBRARY, exist_ok=True)
    with open(dest, "w") as fh:
        fh.write(page)
    print(f"filed {dest}  ({len(page) // 1024}KB, from {src})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
