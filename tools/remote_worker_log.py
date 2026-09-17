"""Read a remote worker's own Claude Code session transcript for "what is
it doing" visibility (GH #152 iteration 2 -- replaces the worker.log tee
that killed every winbox spawn; see windows/spawn-worker.ps1's iteration-1
revert comment and docs/design/multi-host-workers.md section 8).

Claude Code writes a full JSONL transcript per session under
    <home>\\.claude\\projects\\<cwd-slug>\\<session-uuid>.jsonl
where <cwd-slug> is the worktree's absolute path with every `\\`, `/`, `:`,
`_` replaced 1:1 with `-` (measured on winbox 2026-09-18, see `_cwd_slug`,
re-verified 2026-09-18 with `ssh winbox dir C:\\Users\\UsEr\\.claude\\projects`
-- task-424077a4's directory matches the rule exactly). <home> is resolved
live over ssh via $env:USERPROFILE, never hardcoded.

Usage:
    python -m tools.remote_worker_log <task_id_or_prefix> [-n 30] [--raw]

Exit codes (never "probably" -- GH #60's contract, reused here):
    0  printed something
    1  usage error: bad/unknown task id, or the task's host has no ssh
       alias (e.g. host=mac -- the transcript is already local, no ssh
       needed), or the host's OS isn't wired yet (only windows today)
    2  ssh reached the box, but no transcript exists yet for this task
    3  ssh itself failed (unreachable host, timeout, auth failure)
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import host as get_host
from runners.watchdog import _remote_worktree_dir

_REMOTE_SSH_TIMEOUT_S = 30

# Same value the CTO's review specified verbatim: sk-/ghp_/eyJ-shaped runs
# of 8+ token chars are almost certainly an API key, a GitHub PAT, or a JWT.
_SECRET_RE = re.compile(r"(sk|ghp|eyJ)[A-Za-z0-9_\-]{8,}")


def _mask_secrets(text: str) -> str:
    return _SECRET_RE.sub("***", text)


def _cwd_slug(path: str) -> str:
    """Claude Code's own transcript-directory slugification: every `\\`,
    `/`, `:`, `_` in an absolute path becomes `-`, one character for one
    character, nothing collapsed. Measured on winbox 2026-09-18:
    `C:\\Users\\UsEr\\mooniex\\worktrees\\mooniex-agents__browser_operator__task-424077a4`
    -> `C--Users-UsEr-mooniex-worktrees-mooniex-agents--browser-operator--task-424077a4`
    (same rule visible in this very session's own scratchpad path on the Mac
    side: `/Users/gob/Projects/...` -> `-Users-gob-Projects-...`)."""
    return re.sub(r"[\\/:_]", "-", path)


def _resolve_task(needle: str) -> dict:
    """Exact id, else a unique `LIKE '<needle>%'` prefix match -- same
    two-step lookup `tools.send_to_worker.send()` uses. Raises ValueError
    (exit 1) when nothing matches; never guesses among several matches."""
    db.init()
    task = db.get_task(needle)
    if task:
        return task
    from lib.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM tasks WHERE id LIKE ? LIMIT 2", (f"{needle}%",),
        ).fetchall()
    if not rows:
        raise ValueError(f"no task matching {needle!r}")
    if len(rows) > 1:
        raise ValueError(f"ambiguous prefix {needle!r} -- matches multiple tasks")
    return db.get_task(rows[0][0])


def _fetch_transcript_tail(task: dict) -> str:
    """Raw JSONL text of the newest transcript file for `task`'s worker,
    read over one ssh round trip. Raises ValueError for a usage-shaped
    problem (exit 1), LookupError when no transcript exists yet (exit 2),
    or ConnectionError when ssh itself failed (exit 3) -- never returns a
    guess."""
    host_name = task.get("host") or "mac"
    host_cfg = get_host(host_name)
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        raise ValueError(
            f"task {task['id']} is host={host_name!r} (local) -- its "
            f"transcript is already on this machine, read it directly, "
            f"no ssh needed"
        )
    if host_cfg.get("os") != "windows":
        raise ValueError(
            f"remote transcript reading not wired for os={host_cfg.get('os')!r} "
            f"(only windows/winbox today -- see module docstring)"
        )
    worktree = _remote_worktree_dir(host_cfg, task)
    if not worktree:
        raise ValueError(
            f"could not build a worktree path for task {task['id']} -- "
            f"missing project/role/id on the row, or hosts.yaml has no "
            f"'worktrees' root for {host_name!r}"
        )
    slug = _cwd_slug(worktree)
    script = (
        "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false\n"
        f'$dir = Join-Path $env:USERPROFILE ".claude\\projects\\{slug}"\n'
        "if (-not (Test-Path $dir)) { Write-Output 'NO_TRANSCRIPT'; exit 2 }\n"
        "$f = Get-ChildItem $dir -Filter *.jsonl -ErrorAction SilentlyContinue |"
        " Sort-Object LastWriteTime -Descending | Select-Object -First 1\n"
        "if (-not $f) { Write-Output 'NO_TRANSCRIPT'; exit 2 }\n"
        "Get-Content -LiteralPath $f.FullName -Encoding UTF8\n"
    )
    # -EncodedCommand (base64 of UTF-16LE), not -Command with the raw script:
    # ssh joins its remaining argv into ONE string that the remote host's
    # shell re-parses BEFORE powershell.exe ever sees it. Measured live on
    # winbox 2026-09-18: with a raw `-Command <script containing |>`, the
    # pipe characters were consumed by that outer shell first --
    # `Sort-Object`/`Select-Object` got split off as their own "commands"
    # and failed with "'Sort-Object' is not recognized...". Base64 has no
    # shell-special characters at all, so nothing downstream can misparse it.
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = ["ssh", ssh_alias, "powershell", "-NoProfile", "-EncodedCommand", encoded]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=_REMOTE_SSH_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise ConnectionError(f"ssh to {host_name} failed: {e}") from e

    out = r.stdout or ""
    if r.returncode == 2 or out.strip() == "NO_TRANSCRIPT":
        raise LookupError(
            f"no transcript exists yet for task {task['id']} on {host_name} "
            f"(.claude\\projects\\{slug} missing or empty)"
        )
    if r.returncode != 0:
        # 255 is OpenSSH's own "could not connect" code; any other nonzero
        # exit here is the remote powershell itself failing -- both are
        # "ssh/remote side broke", never "no transcript".
        raise ConnectionError(
            f"ssh to {host_name} failed (exit {r.returncode}): "
            f"{(r.stderr or out).strip()[:300]}"
        )
    return out


def _preview(text: str, n: int) -> str:
    text = " ".join(text.split())
    return _mask_secrets(text[:n])


def _entries_from_jsonl(raw: str) -> list[tuple[str, str, str]]:
    """Flatten raw JSONL transcript text into (hhmmss, type_label, summary)
    tuples -- one per CONTENT BLOCK, not one per raw JSONL row, since a
    single assistant turn can carry both a text block and a tool_use block.
    Malformed lines are skipped, not fatal -- a corrupt trailing line must
    never hide every entry before it."""
    out: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        ts = obj.get("timestamp") or ""
        hhmmss = ts[11:19] if len(ts) >= 19 else "??:??:??"
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            if content.strip():
                out.append((hhmmss, "user", _preview(content, 80)))
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                label = "assistant-text" if obj.get("type") == "assistant" else "user"
                out.append((hhmmss, label, _preview(block.get("text") or "", 80)))
            elif btype == "tool_use":
                name = block.get("name") or "?"
                input_preview = _preview(json.dumps(block.get("input") or {}), 80)
                out.append((hhmmss, "tool_use", f"{name}, {input_preview}"))
            elif btype == "tool_result":
                is_error = bool(block.get("is_error"))
                result_content = block.get("content")
                if isinstance(result_content, list):
                    result_text = " ".join(
                        b.get("text", "") for b in result_content if isinstance(b, dict)
                    )
                else:
                    result_text = str(result_content or "")
                verdict = "error" if is_error else "ok"
                out.append((hhmmss, "tool_result", f"{verdict}, {_preview(result_text, 80)}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Read a remote worker's own Claude Code transcript")
    ap.add_argument("task_id", help="task id or unique prefix")
    ap.add_argument("-n", type=int, default=30, help="how many entries to show (default 30)")
    ap.add_argument("--raw", action="store_true", help="dump the raw JSONL tail instead")
    args = ap.parse_args()

    try:
        task = _resolve_task(args.task_id)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        raw = _fetch_transcript_tail(task)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 2
    except ConnectionError as e:
        print(str(e), file=sys.stderr)
        return 3

    if args.raw:
        for ln in raw.splitlines()[-args.n:]:
            print(_mask_secrets(ln))
        return 0

    entries = _entries_from_jsonl(raw)
    if not entries:
        print(f"transcript found for task {task['id']} but no readable "
              f"entries yet", file=sys.stderr)
        return 0
    for hhmmss, label, summary in entries[-args.n:]:
        print(f"{hhmmss} {label} {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
