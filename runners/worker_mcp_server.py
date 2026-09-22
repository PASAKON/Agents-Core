"""Stdio MCP server for DEV sessions running inside Claude Code TUI.

Reads WORKER_TASK_ID + WORKER_ROLE env to know which task it belongs to.
Exposes read-only wiki tools + submit_report (writes back to DB).

Registered in config/worker.mcp.json as server "org" — tools become
mcp__org__<tool_name> inside Claude Code.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from lib import db
from lib import toon
from lib.logger import get_logger
from lib.notify import info
from tools import decide as decide_tool
from tools import wiki as wiki_tools
from tools.gh_issue import create_issue as gh_create_issue
from tools.skill_objection import raise_objection as _raise_skill_objection

TASK_ID = os.environ.get("WORKER_TASK_ID", "")
ROLE = os.environ.get("WORKER_ROLE", "dev")
log = get_logger(ROLE, TASK_ID or None, stdout=False)

mcp = FastMCP("org")


@mcp.tool()
def wiki_read(path: str) -> str:
    """Read a wiki page. Namespaced ("org:x.md") or unprefixed (default namespace)."""
    try:
        return wiki_tools.wiki_read(path)[:8000]
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def wiki_list(prefix: str = "") -> str:
    """List wiki pages under an optional prefix."""
    try:
        return "\n".join(wiki_tools.wiki_list(prefix)[:200])
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def wiki_search(query: str) -> str:
    """Grep wiki for a query string."""
    try:
        return toon.encode(wiki_tools.wiki_search(query))
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def decide(site: str, state: str, provider: str = "") -> str:
    """Answer a fixed-schema typed question from unstructured text — 'what
    state is this page in', 'which skill fires', 'route this message' —
    via config/decisions/<site>.yaml's declared options, instead of
    reasoning it out in context. See docs/design/decision-layer.md.

    `site` must be a declared decision site (python tools/decide.py sites
    lists them). `state` is the smallest sufficient text state — never a
    screenshot; Jev/System One models take no images. `provider` optionally
    forces one rung of the site's provider ladder (rules|openrouter|jev).

    Tries `rules` (free, regex, always on) first; the paid rungs
    (openrouter, jev) are OFF by default and only run when their own env
    gates are explicitly set — a bare call never spends money.

    Every call writes one row to the decision ledger
    (state/decisions/<month>.jsonl), tagged with this task's WORKER_TASK_ID.
    Returns the Decision as a JSON string.
    """
    try:
        d = decide_tool.decide(site, state, provider=(provider.strip() or None))
        return json.dumps(d.to_dict())
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def submit_report(report: str) -> str:
    """Submit final task report. Sets task status=review for CTO review.

    Call this exactly once when work on the task is complete. The report
    should follow the role's REQUIRED report format (files changed, tests
    run, blockers). After calling this the DEV session can be closed.
    """
    if not TASK_ID:
        return "ERROR: WORKER_TASK_ID env var not set"
    db.update_status(TASK_ID, "review", report=report, actor=ROLE)
    summary_line = report.strip().splitlines()[0][:200] if report.strip() else "(empty)"
    info(f"submitted report — {summary_line}")
    log.info(f"REPORT submitted ({len(report)} chars)")
    return f"OK — task {TASK_ID} status=review. CTO will review and merge."


@mcp.tool()
def file_blocker_issue(title: str, body: str) -> str:
    """File a GitHub issue on the current project so a blocker is durable.

    MANDATORY any time you cannot proceed (missing secret, ambiguous spec,
    broken dependency, external service down). The issue lets work resume
    after a closed tab, sleeping mac, or dropped network — without it the
    blocker dies with the session.

    Body is auto-prefixed with task id + worktree path so a future agent
    can reattach. Returns the issue URL, which is also logged so the CTO
    sees it.
    """
    if not TASK_ID:
        return "ERROR: WORKER_TASK_ID env var not set"
    task = db.get_task(TASK_ID)
    if not task:
        return f"ERROR: task {TASK_ID} not found"
    project_key = task["project"]
    worktree = task.get("worktree") or "(no worktree)"
    enriched_body = (
        f"**Task**: `{TASK_ID}`\n"
        f"**Role**: `{ROLE}`\n"
        f"**Worktree**: `{worktree}`\n"
        f"**Branch**: `{task.get('branch') or '(none)'}`\n\n"
        "---\n\n"
        f"{body}"
    )
    try:
        url = gh_create_issue(project_key, title, enriched_body,
                              labels=["blocker", "agent"])
    except Exception as e:
        info(f"file_blocker_issue FAILED: {e}")
        return f"ERROR: {e}"
    info(f"blocker issue filed: {url}")
    return url


@mcp.tool()
def request_human_handoff(
    kind: str,
    novnc_url: str = "",
    hint: str = "",
    page_url: str = "",
    session_id: str = "",
) -> str:
    """Pause the task and request the CEO to take over the browser.

    Use when the AI cannot proceed alone — captcha, login form, 2FA SMS,
    WebAuthn prompt, consent banner that hides the next button. The CEO
    will attach via noVNC at `novnc_url`, solve the blocker in the live
    Chromium session, and resume the task via a dev_message reply.

    Side effects:
      - Files a GH issue (durable record) labelled blocker + human-handoff.
      - Flips task status to `blocked_human` so the watchdog stops
        treating silence as a stall (24h human-grace window applies).
      - Types a prominent line into the CTO chat so the CEO sees the
        noVNC URL without scrolling through logs.

    Args:
      kind: one of {captcha, login, 2fa, webauthn, consent, auth_refresh,
            other}. Routes the GH issue title + chat prefix.
      novnc_url: e.g. http://127.0.0.1:6080/vnc.html?autoconnect=true
      hint: short note for the CEO ("solve captcha then close any modal")
      page_url: the page the agent is stuck on (https://...)
      session_id: Auto Browser session id, for log correlation
    """
    if not TASK_ID:
        return "ERROR: WORKER_TASK_ID env var not set"
    task = db.get_task(TASK_ID)
    if not task:
        return f"ERROR: task {TASK_ID} not found"

    kind = (kind or "other").lower().strip() or "other"
    project_key = task["project"]
    worktree = task.get("worktree") or "(no worktree)"

    title = f"human handoff: {kind} — task {TASK_ID}"
    body = (
        f"**Task**: `{TASK_ID}`\n"
        f"**Role**: `{ROLE}`\n"
        f"**Worktree**: `{worktree}`\n"
        f"**Branch**: `{task.get('branch') or '(none)'}`\n"
        f"**Kind**: `{kind}`\n"
        f"**Page**: {page_url or '(unspecified)'}\n"
        f"**noVNC**: {novnc_url or '(none — no live session)'}\n"
        f"**Auto Browser session**: `{session_id or '(none)'}`\n\n"
        "---\n\n"
        f"{hint or 'AI is paused; CEO action required.'}\n\n"
        "Resume protocol: CEO solves the blocker in the noVNC window, "
        "then types a one-line `mcp__org__dev_message` reply such as "
        "`captcha solved, resume`. The agent will re-observe the page "
        "and continue.\n"
    )
    try:
        issue = gh_create_issue(project_key, title, body,
                                labels=["blocker", "human-handoff", kind])
    except Exception as e:
        info(f"request_human_handoff GH issue failed: {e}")
        issue = ""

    # Flip status so watchdog gives the human a 24h grace window
    # instead of pinging / stalling on the 30-min rule.
    try:
        db.update_status(TASK_ID, "blocked_human", actor=ROLE,
                         review=json.dumps({
                             "handoff": kind,
                             "novnc_url": novnc_url,
                             "page_url": page_url,
                             "session_id": session_id,
                             "issue": issue,
                             "hint": hint,
                         }))
    except Exception as e:
        info(f"request_human_handoff status flip failed: {e}")

    # Surface a prominent line into the CTO chat (relayed via send_to_cto).
    try:
        from tools.send_to_cto import send as send_to_cto
        attn = (
            f"NEEDS HUMAN ({kind}): {hint or 'see issue'}\n"
            f"  noVNC: {novnc_url or '(no live session)'}\n"
            f"  page:  {page_url or '(unspecified)'}\n"
            f"  issue: {issue or '(none)'}\n"
            "  Reply `resume` after solving."
        )
        from lib import cto_session
        send_to_cto(TASK_ID, attn, role=ROLE, cto_id=cto_session.current_id(),
                    owner_role=os.environ.get("WORKER_CTO_ROLE", "cto"))
    except Exception as e:
        info(f"request_human_handoff chat relay failed: {e}")

    info(f"HUMAN HANDOFF requested kind={kind} novnc={novnc_url} issue={issue}")
    return (
        f"OK — task {TASK_ID} status=blocked_human. "
        f"CEO will take over at {novnc_url or '(no live session)'}. "
        f"Issue: {issue or '(none)'}. Wait for `resume` reply."
    )


# One-line console/cto.log cap for dev_message (GH #54). The old 300 was
# under two sentences and silently ate everything past it; observed useful
# reports run 400-900 chars. 700 covers the bulk of those single-paragraph
# reports without letting one dev_message call dominate the CTO's scrolling
# log -- the console constraint is deliberate, so raise generously but keep
# a cap. Nothing is actually lost at this cap anymore: the FULL text always
# lands in tasks.last_checkpoint (see below), and any overflow past 700 is
# marked, not silently dropped.
DEV_MESSAGE_LOG_CAP = 700


@mcp.tool()
def dev_message(text: str) -> str:
    """Broadcast a short progress message to the CTO log (one line).

    Use sparingly to surface meaningful checkpoints — e.g. "reading wiki",
    "found N test failures", "blocker: missing API key". Each call appends
    one prefixed line to cto.log which the CTO surfaces in chat.

    The full text is always persisted (see tasks.last_checkpoint); only the
    one-line console/log rendering is capped. If the console line had to be
    trimmed (extra lines dropped and/or the first line cut), both the log
    line and the returned ack carry a truncation marker (GH #54) — nothing
    is silently lost, only the console rendering is short.

    NOT a replacement for submit_report — final hand-off must still use
    submit_report.
    """
    if not TASK_ID:
        return "ERROR: WORKER_TASK_ID env var not set"
    stripped = text.strip()
    if not stripped:
        line = "(empty)"
        ack = "ack"
    else:
        lines = stripped.splitlines()
        first_line = lines[0]
        extra_lines = len(lines) - 1
        char_over = len(first_line) > DEV_MESSAGE_LOG_CAP
        console_line = first_line[:DEV_MESSAGE_LOG_CAP]
        if extra_lines > 0 or char_over:
            bits = []
            if extra_lines > 0:
                bits.append(f"+{extra_lines} lines")
            if char_over:
                bits.append(f"{len(first_line)}→{DEV_MESSAGE_LOG_CAP} chars")
            line = f"{console_line} […{', '.join(bits)}, truncated]"
            ack = (
                f"ack (truncated: {len(lines)} lines, {len(stripped)} chars "
                f"→ {DEV_MESSAGE_LOG_CAP})"
            )
        else:
            line = console_line
            ack = "ack"
    info(line)
    # Reporting IS the liveness signal. runners/watchdog.py measures silence
    # as `now - tasks.updated_at` and reaps anything past its threshold — but
    # nothing here ever wrote to the DB, so updated_at stayed frozen at spawn
    # time no matter how diligently a DEV reported, and every long-running DEV
    # was guaranteed to be reaped eventually. Measured 2026-08-13 on
    # task-cda4f469: four dev_message calls between 03:36 and 04:25, and the
    # watchdog still saw 5518s of "silence", counted from its 03:04 spawn.
    # Four operators died this way in one night. Touching the row here is what
    # makes the watchdog's silence measure mean what it claims to mean.
    #
    # Persist the FULL text (GH #54) -- not the capped console `line`. Before
    # this fix, last_checkpoint stored the same truncated-to-300 single line
    # the log got, so a re-send or a "what did the DEV last say" lookup hit
    # the same data loss twice. last_checkpoint already exists (no schema
    # change, IRON §30) and is already written on this path since 80f002e.
    try:
        db.set_fields(TASK_ID, actor="dev", last_checkpoint=stripped or "(empty)")
    except Exception as e:  # bookkeeping must never break the DEV's report
        info(f"(dev_message: could not touch task row: {e})")
    return ack


@mcp.tool()
def skill_objection(skill: str, conflict: str, did_instead: str, blocked: bool = False) -> str:
    """Report a skill conflict back to its author (CEO rule 8 / ADR 0022 §6).

    Call this when a skill you did NOT write gave you wrong or conflicting
    guidance. Writes one skill_objection event and adds a LungNote to-do
    addressed to the skill's author (no author on record -> cto). Author and
    user then improve the skill together — this is not a way to silently
    patch the skill yourself. There is no resolve verb: completing the
    LungNote to-do IS the resolution.

    Args:
      skill: skill name exactly as it appears under .claude/skills, or the
        plugin-prefixed form ("<plugin>:<name>").
      conflict: what the skill told you to do that was wrong or contradictory.
      did_instead: what you actually did instead.
      blocked: True if the conflict stopped you from proceeding at all.
    """
    try:
        result = _raise_skill_objection(skill, conflict, did_instead, blocked)
    except Exception as e:
        return f"ERROR: {e}"
    return f"OK — objection raised for {skill!r}, routed to {result['author']}"


if __name__ == "__main__":
    db.init()
    mcp.run()
