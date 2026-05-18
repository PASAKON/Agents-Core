"""Interactive CTO REPL. Multi-turn chat with the CTO from a terminal.

Usage:
    python -m runners.cto_chat              # new session, or pick from list
    python -m runners.cto_chat --new        # always start fresh
    python -m runners.cto_chat --resume ID  # resume specific session
    python -m runners.cto_chat --last       # resume most recent

Slash commands inside the REPL:
    /exit /quit       leave
    /new              start fresh session (drops current context)
    /list             show recent sessions
    /resume ID        switch to a different session
    /stats            print task stats
    /tasks            list recent tasks
    /help             show this list
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    create_sdk_mcp_server,
    list_sessions,
)

from lib import db
from lib.config import role as get_role
from lib.logger import get_logger
from lib.notify import info, success, warn, error, COLORS, RESET
from runners.cto import (
    t_wiki_read, t_wiki_list, t_wiki_search, t_wiki_write,
    t_create_task, t_delegate, t_delegate_parallel,
    t_get_task, t_review_diff, t_merge, t_reopen,
    t_list_projects, t_stats,
)

ROOT = Path(__file__).resolve().parent.parent
ROLE = "cto"
log = get_logger(ROLE)


def _system_prompt() -> str:
    base = (ROOT / "roles" / "cto.md").read_text()
    return base + (
        "\n\n## Interactive Mode\n"
        "You are running in an interactive REPL with the CEO. "
        "Conversation history persists across turns within this session. "
        "Be concise. Confirm scope before delegating expensive work. "
        "When delegating, summarize what you dispatched and to whom. "
        "When reporting back, lead with the bottom line, then key details."
    )


def _build_options(*, resume: str | None = None) -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="org-cto",
        version="1.0.0",
        tools=[
            t_wiki_read, t_wiki_list, t_wiki_search, t_wiki_write,
            t_create_task, t_delegate, t_delegate_parallel,
            t_get_task, t_review_diff, t_merge, t_reopen,
            t_list_projects, t_stats,
        ],
    )
    return ClaudeAgentOptions(
        model=get_role("cto")["model"],
        system_prompt=_system_prompt(),
        permission_mode="acceptEdits",
        mcp_servers={"org": server},
        allowed_tools=[
            "mcp__org__wiki_read", "mcp__org__wiki_list", "mcp__org__wiki_search",
            "mcp__org__wiki_write", "mcp__org__create_task",
            "mcp__org__delegate_task", "mcp__org__delegate_parallel",
            "mcp__org__get_task", "mcp__org__review_diff",
            "mcp__org__merge_task", "mcp__org__reopen_task",
            "mcp__org__list_projects", "mcp__org__stats",
            "Read", "Grep", "Glob",
        ],
        cwd=str(ROOT),
        resume=resume,
    )


def _print_banner(session_id: str | None, resumed: bool) -> None:
    c = COLORS["cto"]
    p = COLORS["ceo"]
    print(f"{c}=========================================================={RESET}")
    print(f"{c}  CTO Chat — Mooniex Virtual Org{RESET}")
    print(f"{c}  Model: claude-opus-4-7   |   Tools: 13{RESET}")
    print(f"{c}=========================================================={RESET}")
    if session_id:
        tag = "resumed" if resumed else "session"
        print(f"  {tag}: {session_id}")
    print(f"  type {p}/help{RESET} for commands, {p}/exit{RESET} to leave")
    print()


def _list_recent_sessions(limit: int = 10):
    try:
        sessions = list_sessions(directory=str(ROOT), limit=limit)
    except Exception as e:
        warn(f"list_sessions failed: {e}")
        return []
    return sessions


def _show_sessions(sessions) -> None:
    if not sessions:
        print("  no prior sessions")
        return
    print(f"  {'#':<3} {'session_id':<40} {'turns':<6} {'updated':<25} {'title'}")
    print(f"  {'-'*3} {'-'*40} {'-'*6} {'-'*25} {'-'*40}")
    for i, s in enumerate(sessions, 1):
        sid = getattr(s, "session_id", "?")
        turns = getattr(s, "num_turns", "?")
        upd = str(getattr(s, "updated_at", "?"))[:24]
        title = (getattr(s, "summary", "") or getattr(s, "title", "") or "")[:40]
        print(f"  {i:<3} {sid:<40} {str(turns):<6} {upd:<25} {title}")


def _pick_session_interactive() -> str | None:
    """Show recent sessions, let user resume one or start new. Returns session_id or None."""
    sessions = _list_recent_sessions()
    if not sessions:
        return None
    print("Recent CTO sessions:")
    _show_sessions(sessions)
    print()
    try:
        choice = input("Resume # (Enter for new): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not choice:
        return None
    if not choice.isdigit():
        return None
    idx = int(choice) - 1
    if 0 <= idx < len(sessions):
        return getattr(sessions[idx], "session_id", None)
    return None


async def _stream_response(client: ClaudeSDKClient) -> str | None:
    """Stream CTO response to stdout. Returns the session_id when done."""
    session_id = None
    c = COLORS["cto"]
    first = True
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    if first:
                        print(f"{c}CTO>{RESET} ", end="", flush=True)
                        first = False
                    print(block.text, end="", flush=True)
                    log.info(f"CTO: {block.text[:500]}")
                elif isinstance(block, ThinkingBlock):
                    pass  # silent
        elif isinstance(msg, ResultMessage):
            session_id = msg.session_id
    if not first:
        print()
    return session_id


HELP = """
Commands:
  /help            show this
  /exit /quit      leave the chat
  /new             start fresh session (drops current context)
  /list            show recent sessions
  /resume <id>     switch to a different session
  /stats           task counts by status
  /tasks           recent tasks
  /clear           clear screen

Multiline input: end a line with \\ to continue on the next.
Ctrl-C cancels current input. Ctrl-D exits.
"""


async def _read_multiline() -> str | None:
    """Read input, supporting \\ continuation. Returns None on EOF."""
    p = COLORS["ceo"]
    parts: list[str] = []
    prompt = f"{p}CEO>{RESET} "
    while True:
        try:
            line = await asyncio.to_thread(input, prompt)
        except EOFError:
            return None
        if line.endswith("\\"):
            parts.append(line[:-1])
            prompt = "...  "
            continue
        parts.append(line)
        return "\n".join(parts).strip()


async def chat(initial_session: str | None = None) -> None:
    current_id: str | None = initial_session
    resumed = bool(initial_session)

    while True:
        options = _build_options(resume=current_id)

        try:
            async with ClaudeSDKClient(options=options) as client:
                _print_banner(current_id, resumed)
                resumed = False

                while True:
                    try:
                        line = await _read_multiline()
                    except KeyboardInterrupt:
                        print("\n  (Ctrl-C — type /exit to leave)")
                        continue

                    if line is None:
                        print()
                        return

                    if not line:
                        continue

                    if line.startswith("/"):
                        cmd, *rest = line.split(maxsplit=1)
                        arg = rest[0] if rest else ""

                        if cmd in ("/exit", "/quit"):
                            return
                        if cmd == "/help":
                            print(HELP)
                            continue
                        if cmd == "/clear":
                            print("\033[2J\033[H", end="")
                            continue
                        if cmd == "/stats":
                            print(" ", db.stats())
                            continue
                        if cmd == "/tasks":
                            for t in db.list_tasks(limit=15):
                                print(f"  {t['id']}  {t['role']:14s} {t['status']:12s} {t['project']:25s} {t['title'][:50]}")
                            continue
                        if cmd == "/list":
                            _show_sessions(_list_recent_sessions())
                            continue
                        if cmd == "/new":
                            current_id = None
                            resumed = False
                            break
                        if cmd == "/resume":
                            if not arg:
                                warn("usage: /resume <session_id>")
                                continue
                            current_id = arg.strip()
                            resumed = True
                            break
                        warn(f"unknown command: {cmd}  (try /help)")
                        continue

                    log.info(f"CEO: {line[:200]}")
                    try:
                        await client.query(line)
                        sid = await _stream_response(client)
                        if sid:
                            current_id = sid
                    except KeyboardInterrupt:
                        print("\n  (cancelled — CTO response interrupted)")
                        break
                    except Exception as e:
                        error(f"CTO query failed: {e}")
                        break
        except Exception as e:
            error(f"client crashed: {e}")
            return


def main():
    ap = argparse.ArgumentParser(description="Interactive CTO chat")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--new", action="store_true", help="start fresh session")
    g.add_argument("--resume", metavar="ID", help="resume specific session id")
    g.add_argument("--last", action="store_true", help="resume most recent session")
    args = ap.parse_args()

    db.init()

    initial = None
    if args.resume:
        initial = args.resume
    elif args.last:
        recents = _list_recent_sessions(limit=1)
        if recents:
            initial = getattr(recents[0], "session_id", None)
        if not initial:
            warn("no prior sessions found — starting fresh")
    elif not args.new:
        initial = _pick_session_interactive()

    asyncio.run(chat(initial))
    success("CTO chat ended")


if __name__ == "__main__":
    main()
