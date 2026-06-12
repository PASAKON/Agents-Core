"""Shared iTerm typewriter helper: type a message into a claude TUI and submit.

Every iTerm "typewriter" (send_to_cto / send_to_dev / send_to_cxo /
inject_prompt) writes a message body then a carriage return to make the
claude TUI submit it. The naive sequence wrote the body and the CR
back-to-back:

    write text "<body>" newline NO
    write text (ASCII character 13) newline NO

Multi-line bodies trigger the claude TUI's *bracketed-paste* path. The CR
lands while the paste is still being consumed and gets swallowed, so the
message stays stuck in the composer as "[Pasted text #N +K lines]" and is
never submitted — the human has to press Enter by hand (CEO report,
recurring, 2026-06-12).

`type_submit_fragment` fixes this by inserting a settle `delay` before the
CR and sending a *second* CR as a rescue:

    write text "<body>" newline NO
    delay 0.4
    write text (ASCII character 13) newline NO
    delay 0.3
    write text (ASCII character 13) newline NO

Rationale:
  * `delay 0.4` lets the TUI finish consuming the paste before the first CR,
    so the CR is interpreted as Enter/submit rather than swallowed.
  * The second CR (after `delay 0.3`) is a no-op when the first already
    submitted — Enter on an empty claude composer does nothing — but rescues
    the message when the first CR was still swallowed.

Single-line senders (kickoff / idle pings) pay ~0.7s extra latency; that is
acceptable and deliberately not special-cased.

The two shell typewriters (scripts/idle-ping-watcher.sh,
scripts/cxo-claude.sh) inline the same delay/CR/delay/CR sequence rather than
import this module.
"""
from __future__ import annotations


def type_submit_fragment(escaped_var_or_literal: str) -> str:
    """Return the AppleScript write+submit fragment for one iTerm session.

    `escaped_var_or_literal` is the message body that goes inside the
    `write text "..."` quotes. Callers MUST pass it already escaped for an
    AppleScript double-quoted string literal (backslashes and double quotes
    backslash-escaped), exactly as the old inline `write text "{escaped}"`
    sites did.

    The returned fragment is meant to be interpolated where the old
    `write text "{escaped}" newline NO` + `write text (ASCII character 13)`
    pair used to live, inside a `tell current session ... end tell` block.
    AppleScript is whitespace-insensitive, so the flush-left lines run
    correctly regardless of the surrounding indentation.

    See the module docstring for why the extra delay + second CR are needed.
    """
    return (
        f'write text "{escaped_var_or_literal}" newline NO\n'
        "delay 0.4\n"
        "write text (ASCII character 13) newline NO\n"
        "delay 0.3\n"
        "write text (ASCII character 13) newline NO"
    )
