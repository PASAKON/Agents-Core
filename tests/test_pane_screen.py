"""lib/pane_screen.py reading a `tmux capture-pane -p -e` capture (15 Oct 2026).

Claude Code draws its ghost prompt suggestion dim (SGR 2) after the ❯; a plain capture
shows it as typed text, so the rename sweep logged "prompt not empty" for four idle
sessions for 20+ minutes. The fixtures below are shaped like the bytes captured from the
live panes that day: `ESC[39m❯ ESC[2m<text>` for an idle box with a suggestion, a grey
`ESC[38;5;246m❯ ESC[39m` while a turn runs, `ESC[38;5;244m` rules, the footer with its
OSC 8 hyperlink."""
from __future__ import annotations

import pytest

from lib import pane_screen as ps

ESC = "\x1b"
NBSP = "\xa0"
RULE = f"{ESC}[38;5;244m" + "─" * 60 + f"{ESC}[39m"
LINK = f"{ESC}]8;id=122cghu;https://claude.ai/code/session_01Huf16pTySf{ESC}\\remote{ESC}]8;;{ESC}\\"
IDLE_FOOTER = (f"  {ESC}[38;5;220m⏵⏵ auto mode on{ESC}[38;5;246m (shift+tab to cycle) · ← for agents"
               f"{ESC}[39m   {ESC}[38;5;114m{LINK}{ESC}[39m")
BUSY_FOOTER = (f"  {ESC}[38;5;220m⏵⏵ auto mode on{ESC}[38;5;246m (shift+tab to cycle) · esc to interrupt"
               f" · ← for agents{ESC}[39m")
TRANSCRIPT = f"{ESC}[38;5;246m✻{ESC}[39m {ESC}[38;5;246mCrunched for 5m 53s · done 1:43 AM{ESC}[39m"


def pane(input_line: str, footer: str = IDLE_FOOTER, *rows_below_input: str) -> str:
    return "\n".join([TRANSCRIPT, "", RULE, input_line, *rows_below_input, RULE, footer, ""])


IDLE = f"{ESC}[39m❯{NBSP}"                      # an idle box: the default colour
GREY = f"{ESC}[38;5;246m❯{NBSP}{ESC}[39m"       # what Claude Code draws while a turn runs


@pytest.mark.parametrize("name,line", [
    ("a ghost suggestion, one dim span",
     f"{IDLE}{ESC}[2mรับยอดเกิน $1.78 ได้{ESC}[0m"),
    ("a ghost suggestion in several dim spans split by a plain space (as 36c49776 showed it)",
     f"{IDLE}{ESC}[2mgo{ESC}[0m {ESC}[2mยิง EP7 ด้วย Flow{ESC}[0m"),
    ("a dim span that SGR 22 ends, with nothing after",
     f"{IDLE}{ESC}[1;2mเช็ค PR เอง{ESC}[22m"),
    ("a dim span ended by a bare ESC[m",
     f"{IDLE}{ESC}[2mดูต่อเลย{ESC}[m"),
    ("a dim span with no reset at all before the line ends",
     f"{IDLE}{ESC}[2mดูต่อเลย"),
    ("the grey pointer alone (the brief's case 3)", GREY),
    ("the idle pointer alone", IDLE),
])
def test_a_ghost_suggestion_or_an_empty_box_is_ready(name, line):
    screen = pane(line)
    assert ps.box_empty(screen), name
    assert ps.typed_text(screen) == "", name
    assert ps.prompt_ready(screen), name
    assert ps.not_ready_reason(screen) is None


@pytest.mark.parametrize("name,line", [
    ("typed text, not dim", f"{IDLE}half a sentence the CEO is typing"),
    ("typed text, reset after the pointer", f"{IDLE}{ESC}[0mhalf a sentence"),
    ("typed text then a dim completion (real, then dim)", f"{IDLE}/ren{ESC}[2mame <name>{ESC}[0m"),
    ("a dim part then typed text", f"{IDLE}{ESC}[2mghost{ESC}[22m typed"),
    ("typed text under a truecolour: its 2 is a colour selector, not dim",
     f"{IDLE}{ESC}[38;2;10;20;30mtyped{ESC}[39m"),
    ("typed text under a 256-colour whose number is 2", f"{IDLE}{ESC}[38;5;2mtyped{ESC}[39m"),
    ("typed text under a colon-form truecolour", f"{IDLE}{ESC}[38:2::10:20:30mtyped{ESC}[39m"),
])
def test_real_text_after_the_pointer_is_a_draft(name, line):
    screen = pane(line)
    assert not ps.box_empty(screen), name
    assert not ps.prompt_ready(screen), name
    assert ps.not_ready_reason(screen) == "prompt not empty"


def test_a_second_row_of_a_draft_counts_even_after_a_dim_first_row():
    """Dim state is per row: a ghost row above does not blank the real row below it."""
    screen = pane(f"{IDLE}{ESC}[2mghost", "  " + IDLE_FOOTER, "  second row of a draft (Shift+Enter first)")
    assert ps.typed_text(screen) == "secondrowofadraft(Shift+Enterfirst)"
    assert not ps.prompt_ready(screen)


def test_a_running_turn_greys_the_pointer_and_is_never_ready():
    """The brief's case 3: the box is empty, the pointer grey, and the footer says "esc to
    interrupt": a turn is running, so the answer is "not ready: turn running", and the
    log says that instead of "prompt not empty"."""
    screen = pane(GREY, BUSY_FOOTER)
    assert ps.box_empty(screen)
    assert not ps.prompt_ready(screen)
    assert ps.not_ready_reason(screen) == "turn running"
    assert ps.pane_busy(screen)


def test_a_dim_busy_hint_still_counts():
    """Footer hints are often dim; busy and choice checks read the text WITH dim spans."""
    footer = f"  {ESC}[2mesc to interrupt{ESC}[22m"
    assert ps.pane_busy(pane(IDLE, footer))
    choice = (f" {ESC}[2mDo you want to proceed?{ESC}[22m\n {ESC}[36m❯{ESC}[39m 1. Yes\n   2. No\n"
              f" {ESC}[2mEsc to cancel{ESC}[22m\n")
    assert ps.pane_waiting(choice)


def test_a_choice_prompt_is_not_ready_with_or_without_attributes():
    plain = " Do you want to proceed?\n ❯ 1. Yes\n   2. No\n❯ \n"
    coloured = (f" Do you want to proceed?\n {ESC}[36m❯{ESC}[39m {ESC}[36m1. Yes{ESC}[39m\n   2. No\n"
                f"{IDLE}\n")
    for screen in (plain, coloured):
        assert not ps.prompt_ready(screen)
        assert ps.not_ready_reason(screen) == "choice prompt up"


def test_no_input_box_on_screen_is_not_ready():
    screen = f"{TRANSCRIPT}\nsomething else\n"
    assert not ps.prompt_ready(screen)
    assert ps.not_ready_reason(screen) == "prompt not empty"


def test_the_footers_hyperlink_does_not_leak_into_the_box():
    """OSC 8 (ESC ] 8 ; id=… ; url ST) carries printable characters in its payload; a
    box read that kept them would call the idle footer a draft."""
    for st in (f"{ESC}\\", "\x07"):
        link = f"{ESC}]8;id=1;https://claude.ai/x{st}remote{ESC}]8;;{st}"
        assert ps.strip_ansi(link) == "remote"
        assert ps.prompt_ready(pane(IDLE, f"  footer {link}"))


def test_a_capture_without_attributes_reads_as_it_did():
    plain = "out\n" + "─" * 40 + "\n❯ half a sentence\n" + "─" * 40 + "\n"
    assert ps.drop_ghost(plain) is plain and ps.strip_ansi(plain) is plain
    assert ps.typed_text(plain) == "halfasentence"
    assert ps.prompt_line(plain) == "half a sentence"
    empty = "out\n" + "─" * 40 + "\n❯ \n" + "─" * 40 + "\n"
    assert ps.prompt_ready(empty)


def test_the_pointer_and_the_rules_survive_when_the_app_draws_them_dim():
    screen = "\n".join([f"{ESC}[2m" + "─" * 40, f"{ESC}[2m❯ {ESC}[2mghost{ESC}[0m", f"{ESC}[2m" + "─" * 40, ""])
    assert ps.typed_text(screen) == ""
    assert ps.prompt_line(screen) == ""


def test_prompt_line_is_the_typed_part_only():
    assert ps.prompt_line(pane(f"{IDLE}{ESC}[2mghost{ESC}[0m")) == ""
    assert ps.prompt_line(pane(f"{IDLE}typed{ESC}[2m ghost{ESC}[0m")) == "typed"
    assert ps.prompt_line(f"{TRANSCRIPT}\n") is None
