#!/usr/bin/env python3
"""sshd forced command: a winbox Project Head asks the CEO to lift the winbox hold.

OrgMesh P3-A (CEO 2026-10-17, option A). The CEO's hold on the winbox screen
(windows/pc_lease.py ceo-on / ceo-off) must outlast every agent: a PH may not run
`ceo-off` itself, and an ad-hoc `ask_run` over ssh was refused as well. What it may do
is ASK. This is the one thing a winbox PH can ask for, over a key that can run nothing
else (docs/ops/winbox-hold-release.md):

    command="cd /opt/MoonieXHQ/Agents/Core && exec bash scripts/hub/with-org-db-env.sh \\
        .venv/bin/python -E -s tools/hold_release_card.py",from="<winbox ip>",restrict <key>

sshd puts what the client typed in SSH_ORIGINAL_COMMAND. Exactly one form is accepted:

    ask-release --ceo-said "<words>" [--who <ph id>]

Anything else is refused, exit 2. The words are printable ASCII, 3..120 characters, no
double quote, and are matched by a regex, never handed to a shell. Only a slug of them
([a-z0-9-]) reaches the card's command line; the card is a FIXED template (COMMAND_HEAD +
slug + COMMAND_TAIL), the shape of RUN-20261016-2056-4803. The card is risk amber, host
contabo, requester role project_head, session = --who. The CEO reads the exact bytes on
his phone and his tap is the only authority: this script has no verb that approves.

One card at a time: while a hold-release card is still pending the next ask is refused,
so a looping PH cannot fill his phone.

Prints the card id (and nothing from the environment) on success.
Exit: 0 card raised · 2 refused · 3 hub error (no token, unreachable, hub said no).

`--dry-run` (argv, which sshd never passes) prints the card body and sends nothing; it
needs no token. Stdlib only, plus tools/ask_run.py.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))            # the END, as in ask_run: never shadow what is importable
from lib import ceo_text  # noqa: E402
from tools import ask_run  # noqa: E402

EXIT_OK, EXIT_REFUSED, EXIT_HUB = 0, 2, 3

# --- the fixed card ----------------------------------------------------------
# Everything the CEO approves is here except the slug of the words. A change to any of
# these lines changes the bytes he is shown; tests/test_hold_release_card.py pins them.
CARD_HOST = "contabo"            # where `ssh winbox` works; winbox itself has no route out
WINBOX_ALIAS = "winbox"
WINBOX_PY = r"C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe"
PC_LEASE = r"C:\mooniex\pclease\pc_lease.py"
# pc_lease.py keeps its files under the ssh user's home (Path.home() / Documents / ...).
ESC_HOLD = r"%USERPROFILE%\Documents\CookieRunScript\modelplay\ESC_HOLD"
COMMAND_HEAD = f"ssh {WINBOX_ALIAS} '{WINBOX_PY} {PC_LEASE} ceo-off --ceo-said "
COMMAND_TAIL = f" & del {ESC_HOLD} & {WINBOX_PY} {PC_LEASE} status'"
RISK = "amber"
ROLE = "project_head"
# ceo-off releases first, then spends up to ~8 min putting Cookie Run back; the default 300 s
# kill would cut that resume short.
TIMEOUT_S = 600
WHY_LEAD = 'winbox PH quotes you: "'
EXPECTED = "PC: released, then the ESC hold is cleared and the status lines print."
DEFAULT_WHO = "winbox-ph"

# --- the one accepted form ---------------------------------------------------
WORDS_MIN, WORDS_MAX = 3, 120
ALNUM_MIN = 3                    # a slug of fewer than 3 letters or digits says nothing
# Printable ASCII except the double quote (0x22), which closes the words. No tab, no newline,
# nothing above 0x7E: they fail to match, they are not stripped.
_FORM = re.compile(r'ask-release --ceo-said "(?P<words>[ -!#-~]*)"'
                   r'(?: --who (?P<who>[A-Za-z0-9_-]{1,40}))?')
_SLUG_RUN = re.compile(r"[^A-Za-z0-9]+")
_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_COMMAND_RE = re.compile(re.escape(COMMAND_HEAD) + _SLUG + re.escape(COMMAND_TAIL))

# Two simultaneous asks could both pass the pending check; one lock makes it one at a time.
LOCK = ROOT / "state" / "locks" / "hold_release_card.lock"
PENDING_LIMIT = 50


class Refused(Exception):
    """The ask is not the one form, or one card is already waiting (exit 2)."""


def parse(original_command: str | None) -> tuple[str, str]:
    """(words, who) from SSH_ORIGINAL_COMMAND, or Refused. Nothing here reaches a shell."""
    if not original_command:
        raise Refused("this key runs one thing: ask-release --ceo-said \"<words>\" [--who <id>]")
    m = _FORM.fullmatch(original_command)
    if not m:
        raise Refused("not the accepted form: ask-release --ceo-said \"<words>\" [--who <id>]; "
                      "the words are printable ASCII without a double quote")
    words = m.group("words")
    if not WORDS_MIN <= len(words) <= WORDS_MAX:
        raise Refused(f"the words are {WORDS_MIN} to {WORDS_MAX} characters (got {len(words)})")
    if len(_SLUG_RUN.sub("", words)) < ALNUM_MIN:
        raise Refused(f"the words need at least {ALNUM_MIN} letters or digits")
    return words, m.group("who") or DEFAULT_WHO


def slug_of(words: str) -> str:
    """[a-z0-9-] only: the one piece of the words that reaches the command line."""
    return _SLUG_RUN.sub("-", words).strip("-").lower()


def command_for(slug: str) -> str:
    return COMMAND_HEAD + slug + COMMAND_TAIL


def why_for(words: str) -> str:
    """One line (a command card's `why` is one line, ask_run._one_line), at most 90 characters;
    the words are cut with `...` when they do not fit. The command line carries them in full."""
    shown = " ".join(words.split())
    room = ceo_text.MAX_CHARS - len(WHY_LEAD) - 1
    if len(shown) > room:
        shown = shown[:room - 3].rstrip() + "..."
    return f'{WHY_LEAD}{shown}"'


def build_payload(words: str, who: str) -> dict:
    """The POST /api/run/asks body, with every local refusal of ask_run already run.

    env={} on purpose: nothing in this process's environment (WORKER_TASK_ID, a stray
    CXO_ROLE) may change who the card says it is from.
    """
    args = argparse.Namespace(
        host=CARD_HOST, script=None, command=command_for(slug_of(words)), why=why_for(words),
        expected=EXPECTED, risk=RISK, timeout=TIMEOUT_S, expects_input=False, shell=None,
        cwd=None, env_key=None, task=None, session=who, role=ROLE, dry_run=False, json=False,
        spend=None, no_spend=None)
    try:
        return ask_run.prepare_ask(args, [], {})
    except ask_run.Refused as e:
        raise Refused(str(e)) from None


def is_hold_release_card(ask: object) -> bool:
    """True for a card this script made: its command is the template and nothing else."""
    return (isinstance(ask, dict) and isinstance(ask.get("command"), str)
            and _COMMAND_RE.fullmatch(ask["command"]) is not None)


def pending_card_id() -> str | None:
    """The id of a hold-release card still waiting for the CEO, else None. Raises HubError."""
    resp = ask_run._call("GET", ask_run.ASKS_PATH, query={"status": "pending",
                                                           "limit": str(PENDING_LIMIT)})
    asks = resp.get("asks") if isinstance(resp, dict) else resp
    for a in asks or []:
        if is_hold_release_card(a) and a.get("status") == "pending":
            return str(a.get("id") or "?")[:80]
    return None


@contextlib.contextmanager
def one_at_a_time():
    """Serialise check-then-create. A lock that cannot be taken does not stop the ask: the
    pending check still holds, and the worst a race can do is a second card."""
    fd = None
    try:
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError:
        if fd is not None:
            os.close(fd)
            fd = None
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)


def raise_card(payload: dict) -> str:
    """Refuse if one is pending, else POST the card. Returns its id."""
    with one_at_a_time():
        waiting = pending_card_id()
        if waiting:
            raise Refused(f"a hold-release card is already waiting for the CEO ({waiting}); "
                          "one at a time. Ask again once he has answered it or it has expired.")
        resp = ask_run.submit(payload)
    card_id = resp.get("id")
    if not isinstance(card_id, str) or not re.fullmatch(r"RUN-[A-Za-z0-9][A-Za-z0-9-]{3,63}", card_id):
        raise ask_run.HubError("the hub answered with an id that is not a Run card id")
    return card_id


def hub_message(e: ask_run.HubError) -> str:
    """What the PH is told. Never e's own text: that can carry the hub address or a path."""
    parts = ["hub error"]
    if e.status:
        parts.append(f"({e.status})")
    if isinstance(e.code, str) and re.fullmatch(r"[a-z_]{1,60}", e.code):
        parts.append(e.code)
    if not e.status:
        parts.append("- no answer from the hub, or no token on this box")
    return " ".join(parts)


def main(argv: list[str] | None = None, env: dict | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    dry_run = argv == ["--dry-run"]
    try:
        if argv and not dry_run:
            raise Refused("this command takes no arguments")
        words, who = parse(env.get("SSH_ORIGINAL_COMMAND"))
        payload = build_payload(words, who)
        if dry_run:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return EXIT_OK
        card_id = raise_card(payload)
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return EXIT_REFUSED
    except ask_run.HubError as e:
        print(hub_message(e), file=sys.stderr)
        return EXIT_HUB
    print(card_id)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
