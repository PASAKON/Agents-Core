"""scripts/sompong-supervise.sh and deploy/systemd/mooniex-sompong.service.

The supervisor keeps tmux session `sompong` running the COO launcher. Every
test here puts a FAKE tmux / ps / sleep first on PATH (built in a tmp dir), so
none of it can reach a real tmux server, systemd, a real `claude` or a real
sleep. The fake tmux also encodes what a probe of tmux 3.4 showed (2026-10-01):
has-session / kill-session need `-t =name`, pane commands need `-t =name:`, and
a bare `-t sompong` would prefix-match `sompong-anything` -- the fake refuses it
(exit 99) so a regression to the loose form fails a test instead of working by
luck.

Pane texts are modelled on the startup screens seen in the 2026-10-01 probes
(this task's WORKLOG and SomPong task-179acf77's WORKLOG); the exact wording of
the "Teach auto mode" and "New MCP server" screens is an assumption (see the
WORKLOG), only the phrases the classifier keys on are asserted.

Run: .venv/bin/python -m pytest tests/test_sompong_supervise.py
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SUPERVISE = ROOT / "scripts" / "sompong-supervise.sh"
UNIT = ROOT / "deploy" / "systemd" / "mooniex-sompong.service"

pytestmark = pytest.mark.skipif(
    subprocess.run(["bash", "-c", "exit 0"]).returncode != 0, reason="no bash"
)

# --- the fakes ---------------------------------------------------------------

FAKE_TMUX = r'''#!__PY__
import os, re, sys

d = os.environ["FAKE_TMUX_DIR"]


def rd(name, default=""):
    try:
        with open(os.path.join(d, name)) as f:
            return f.read()
    except OSError:
        return default


def wr(name, text, mode="w"):
    with open(os.path.join(d, name), mode) as f:
        f.write(text)


args = sys.argv[1:]
fd9 = "  [fd9]" if os.path.exists("/proc/self/fd/9") else ""
wr("calls", " ".join(args) + fd9 + "\n", "a")
sub = args[0] if args else ""


def opt(flag):
    return args[args.index(flag) + 1] if flag in args else None


names = [n for n in rd("sessions").split("\n") if n]
t = opt("-t")
as_session = re.fullmatch(r"=([^:]+)", t or "")
as_pane = re.fullmatch(r"=([^:]+):", t or "")


def refuse():
    sys.stderr.write("fake tmux: inexact or missing target %r for %s\n" % (t, sub))
    sys.exit(99)


if sub in ("has-session", "kill-session"):
    if not as_session:
        refuse()
    name = as_session.group(1)
    if sub == "has-session":
        sys.exit(0 if name in names else 1)
    wr("sessions", "".join(n + "\n" for n in names if n != name))
    sys.exit(0 if name in names else 1)
elif sub in ("list-panes", "capture-pane", "send-keys", "display-message"):
    if not as_pane:
        refuse()
    if as_pane.group(1) not in names:
        sys.stderr.write("can't find pane\n")
        sys.exit(1)
    if sub == "list-panes":
        sys.stdout.write(rd("pane_pid").strip() + "\n")
    elif sub == "capture-pane":
        sys.stdout.write(rd("pane"))
    elif sub == "display-message":
        sys.stdout.write(rd("created", "0").strip() + "\n")
    else:  # send-keys
        keys = args[args.index("-t") + 2:]
        if "Down" in keys and os.path.exists(os.path.join(d, "after_down")):
            wr("pane", rd("after_down"))
        if "/exit" in keys and os.path.exists(os.path.join(d, "exit_on_exit")):
            wr("sessions", "".join(n + "\n" for n in names if n != as_pane.group(1)))
elif sub == "list-sessions":
    sys.stdout.write("".join(n + "\n" for n in names))
elif sub == "new-session":
    name = opt("-s")
    if os.path.exists(os.path.join(d, "new_session_fails")):
        sys.exit(1)
    wr("sessions", "".join(n + "\n" for n in names + [name]))
    if os.path.exists(os.path.join(d, "new_pane")):
        wr("pane", rd("new_pane"))
else:
    sys.stderr.write("fake tmux: unexpected subcommand %r\n" % sub)
    sys.exit(98)
'''

FAKE_PS = '#!/bin/sh\ncat "$FAKE_TMUX_DIR/ps" 2>/dev/null\n'

# sleep returns at once and counts calls; past FAKE_SLEEP_LIMIT it drops the stop
# flag, which every loop in the supervisor honours -- a bounded loop test.
FAKE_SLEEP = """#!/bin/sh
f="$FAKE_TMUX_DIR/sleeps"
n=$(cat "$f" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "$f"
if [ -n "$FAKE_SLEEP_LIMIT" ] && [ "$n" -ge "$FAKE_SLEEP_LIMIT" ] && [ -n "$SOMPONG_STATE_DIR" ]; then
  : > "$SOMPONG_STATE_DIR/stop"
fi
exit 0
"""


def _exe(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Sim:
    """A tmp dir holding the fake binaries and the fake tmux's state files."""

    def __init__(self, tmp: Path) -> None:
        self.dir = tmp / "sim"
        self.bin = tmp / "bin"
        self.state = tmp / "state"
        for p in (self.dir, self.bin, self.state):
            p.mkdir(parents=True, exist_ok=True)
        _exe(self.bin / "tmux", FAKE_TMUX.replace("__PY__", sys.executable))
        _exe(self.bin / "ps", FAKE_PS)
        _exe(self.bin / "sleep", FAKE_SLEEP)
        self.sessions: list[str] = []

    def put(self, name: str, text: str) -> None:
        (self.dir / name).write_text(text, encoding="utf-8")

    def set_sessions(self, *names: str) -> None:
        self.put("sessions", "".join(n + "\n" for n in names))

    def raw_calls(self) -> list[str]:
        """Every tmux call; one that inherited the supervisor's flock fd 9 ends in "[fd9]"."""
        f = self.dir / "calls"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    def calls(self) -> list[str]:
        return [re.sub(r"\s+\[fd9\]$", "", c) for c in self.raw_calls()]

    def calls_of(self, sub: str) -> list[str]:
        return [c for c in self.calls() if c.split(" ", 1)[0] == sub]

    def env(self, **extra: str) -> dict[str, str]:
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.dir),
            "FAKE_TMUX_DIR": str(self.dir),
            "SOMPONG_STATE_DIR": str(self.state),
            "SOMPONG_KEY_DELAY_S": "0",
            "SOMPONG_NOW": "1000000",
            "TZ": "UTC",
        }
        env.update(extra)
        return env

    def fn(self, snippet: str, **extra: str) -> subprocess.CompletedProcess:
        """Source the supervisor (no main) and run `snippet`."""
        script = f'SOMPONG_SUPERVISE_SOURCE_ONLY=1 . "{SUPERVISE}"\n{snippet}\n'
        return subprocess.run(
            ["bash", "-c", script], env=self.env(**extra), capture_output=True, text=True, timeout=60
        )

    def run(self, *argv: str, **extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(SUPERVISE), *argv], env=self.env(**extra), capture_output=True, text=True, timeout=60
        )


@pytest.fixture()
def sim(tmp_path: Path) -> Sim:
    return Sim(tmp_path)


# --- pane texts ---------------------------------------------------------------

DEVCHAN = """\
WARNING: Loading development channels

--dangerously-load-development-channels is for local channel development only.
Channels: server:sompong

 ❯ 1. I am using this for local development
   2. Exit

Enter to confirm · Esc to cancel
"""
DEVCHAN_ON_EXIT = DEVCHAN.replace("❯ 1.", "  1.").replace("   2. Exit", " ❯ 2. Exit")

TRUST_ON_NO = """\
Quick safety check: Is this a project you created or one you trust?

 /opt/MoonieXHQ/Projects/MoonieX/SomPong

 ❯ 1. No, exit
   2. Yes, I trust this folder

Enter to confirm · Esc to cancel
"""
TRUST_ON_YES = TRUST_ON_NO.replace("❯ 1. No, exit", "  1. No, exit").replace(
    "  2. Yes, I trust this folder", "❯ 2. Yes, I trust this folder"
)

TEACH = """\
Teach auto mode about your environment?

 ❯ 1. Yes, teach it
   2. Not now
   3. No, never ask again

Enter to confirm · Esc to cancel
"""
MCPJSON = """\
New MCP server found in this project: sompong

 ❯ 1. Use this MCP server
   2. Use all MCP servers in this project
   3. Don't use this MCP server

Enter to confirm · Esc to cancel
"""
LOGIN = "Welcome to Claude Code\n\nSelect login method:\n ❯ 1. Claude account\n"
READY = (
    "● SomPong ready\n\n❯ \n  ⏵⏵ auto mode on (shift+tab to cycle)\n"
    "  Channels (experimental) messages from server:sompong inject directly in this session\n"
)
READY_NO_BANNER = "● SomPong ready\n\n❯ \n  ⏵⏵ auto mode on (shift+tab to cycle)\n"


# --- classify_pane / pane_ready ----------------------------------------------


@pytest.mark.parametrize(
    "pane,kind",
    [
        (DEVCHAN, "devchan"),
        (DEVCHAN_ON_EXIT, "devchan"),
        (TRUST_ON_NO, "trust"),
        (TEACH, "teach"),
        (MCPJSON, "mcpjson"),
        (LOGIN, "login"),
        ("Please run /login to continue\n", "login"),
        (READY, "none"),
        ("", "none"),
        # A chat that only QUOTES a prompt's sentence has no menu on screen: never answered.
        ("the docs say: Teach auto mode about your environment? (it is a setting)\n", "none"),
        ("> WARNING: Loading development channels is what the flag does\n", "none"),
        ("do you trust this folder? Yes, I trust this folder is the second option\n", "none"),
    ],
)
def test_classify_pane(sim: Sim, pane: str, kind: str) -> None:
    sim.put("pane_in", pane)
    r = sim.fn(f'classify_pane < "{sim.dir}/pane_in"')
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == kind


@pytest.mark.parametrize(
    "pane,ready",
    [
        (READY, True),
        (READY_NO_BANNER, True),  # footer alone = idle session
        (DEVCHAN + READY, False),  # a prompt still on screen wins
        ("", False),
        ("Loading…\n", False),
    ],
)
def test_pane_ready(sim: Sim, pane: str, ready: bool) -> None:
    sim.put("pane_in", pane)
    r = sim.fn(f'pane_ready < "{sim.dir}/pane_in"; echo rc=$?')
    assert r.stdout.strip() == ("rc=0" if ready else "rc=1")


# --- restart budget -------------------------------------------------------------


def _launches(sim: Sim, *times: int) -> None:
    (sim.state).mkdir(parents=True, exist_ok=True)
    (sim.state / "launches").write_text("".join(f"{t}\n" for t in times), encoding="utf-8")


def test_backoff_allows_under_budget(sim: Sim) -> None:
    _launches(sim, 100, 200, 300, 400)  # 4 < 5
    r = sim.fn("backoff_wait 500", SOMPONG_MAX_RESTARTS="5", SOMPONG_WINDOW_S="600")
    assert r.stdout.strip() == "0"


def test_backoff_blocks_the_fifth_launch_until_the_oldest_ages_out(sim: Sim) -> None:
    _launches(sim, 100, 200, 300, 400, 450)  # 5 launches inside the window
    r = sim.fn("backoff_wait 500", SOMPONG_MAX_RESTARTS="5", SOMPONG_WINDOW_S="600")
    # oldest (100) + window (600) - now (500) + 1 = 201 s
    assert r.stdout.strip() == "201"


def test_backoff_forgets_launches_older_than_the_window(sim: Sim) -> None:
    _launches(sim, 1, 2, 3, 4, 5)
    r = sim.fn("backoff_wait 2000; wc -l < \"$RESTART_FILE\"", SOMPONG_MAX_RESTARTS="5", SOMPONG_WINDOW_S="600")
    assert r.stdout.split() == ["0", "0"]


def test_backoff_ignores_garbage_lines(sim: Sim) -> None:
    (sim.state).mkdir(parents=True, exist_ok=True)
    (sim.state / "launches").write_text("junk\n\n100\n-5\n", encoding="utf-8")
    r = sim.fn("backoff_wait 200; cat \"$RESTART_FILE\"", SOMPONG_MAX_RESTARTS="2", SOMPONG_WINDOW_S="600")
    assert r.stdout.split() == ["0", "100"]


def test_record_launch_appends(sim: Sim) -> None:
    r = sim.fn("record_launch 111; record_launch 222; cat \"$RESTART_FILE\"")
    assert r.stdout.split() == ["111", "222"]


# --- answer budget --------------------------------------------------------------


def test_answer_budget_gap_and_cap(sim: Sim) -> None:
    # at most 3 answers per kind per start, never twice within 15 s; reset starts a new budget
    snippet = """
    for t in 0 5 20 40 60; do
      SOMPONG_NOW=$t; export SOMPONG_NOW
      answer_allowed teach && printf 'ok ' || printf 'no '
    done
    reset_answer_budget
    SOMPONG_NOW=61; answer_allowed teach && printf 'ok' || printf 'no'
    """
    r = sim.fn(snippet, SOMPONG_ANSWER_GAP_S="15", SOMPONG_MAX_ANSWERS="3")
    assert r.returncode == 0, r.stderr
    # The gap is measured from T=0 at the start: t=0 and t=5 are inside it; t=20, 40, 60
    # are the three allowed answers (the third spends the cap); the reset gives a new budget.
    assert r.stdout.split() == ["no", "no", "ok", "ok", "ok", "ok"]


def test_answer_budget_cap_blocks_the_fourth(sim: Sim) -> None:
    snippet = """
    for t in 100 200 300 400; do
      SOMPONG_NOW=$t; export SOMPONG_NOW
      answer_allowed trust && printf 'ok ' || printf 'no '
    done
    """
    r = sim.fn(snippet, SOMPONG_ANSWER_GAP_S="15", SOMPONG_MAX_ANSWERS="3")
    assert r.stdout.split() == ["ok", "ok", "ok", "no"]


def test_answer_allowed_refuses_an_unknown_kind(sim: Sim) -> None:
    r = sim.fn("answer_allowed login; echo rc=$?")
    assert r.stdout.strip() == "rc=1"


# --- claude_alive ---------------------------------------------------------------


def test_claude_alive_finds_claude_anywhere_under_the_pane_pid(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("pane_pid", "100\n")
    sim.put("ps", "1 0 systemd\n100 1 bash\n101 100 bash\n102 101 claude\n300 1 claude\n")
    assert sim.fn("claude_alive; echo rc=$?").stdout.strip() == "rc=0"


def test_claude_alive_false_when_the_launcher_outlived_claude(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("pane_pid", "100\n")
    # a bash left behind, and a claude that belongs to somebody else's tree
    sim.put("ps", "1 0 systemd\n100 1 bash\n101 100 sleep\n300 1 claude\n")
    assert sim.fn("claude_alive; echo rc=$?").stdout.strip() == "rc=1"


def test_claude_alive_false_without_a_session_or_a_pane(sim: Sim) -> None:
    sim.put("ps", "100 1 claude\n")
    assert sim.fn("claude_alive; echo rc=$?").stdout.strip() == "rc=1"  # no session at all
    sim.set_sessions("sompong")
    assert sim.fn("claude_alive; echo rc=$?").stdout.strip() == "rc=1"  # no pane pid


def test_tmux_targets_are_exact(sim: Sim) -> None:
    """The fake refuses a bare `-t sompong`; every call the supervisor makes must be accepted."""
    sim.set_sessions("sompong", "sompong-other")
    sim.put("pane_pid", "100\n")
    sim.put("pane", READY)
    sim.put("ps", "100 1 bash\n101 100 claude\n")
    r = sim.fn("session_exists; claude_alive; capture >/dev/null; startup_step; echo STEP=$STEP")
    assert r.returncode == 0, r.stderr
    assert "STEP=ready" in r.stdout
    assert "fake tmux:" not in r.stderr  # the fake refuses an inexact target
    for c in sim.calls():
        assert re.search(r"-t =sompong:?( |$)", c), c
    # and `sompong` must not be satisfied by a session that merely starts with it
    sim.set_sessions("sompong-other")
    assert sim.fn("session_exists; echo rc=$?").stdout.strip() == "rc=1"


# --- startup_step ---------------------------------------------------------------


def _step(sim: Sim, pane: str, *, after_down: str | None = None, **extra: str):
    sim.set_sessions("sompong")
    sim.put("pane", pane)
    if after_down is not None:
        sim.put("after_down", after_down)
    return sim.fn("startup_step; echo STEP=$STEP", **extra)


def _keys(sim: Sim) -> list[str]:
    return sim.calls_of("send-keys")


def test_devchan_selected_gets_enter(sim: Sim) -> None:
    r = _step(sim, DEVCHAN)
    assert "STEP=answered" in r.stdout
    assert _keys(sim) == ["send-keys -t =sompong: Enter"]
    assert "answered startup prompt: devchan" in r.stderr


def test_devchan_with_the_cursor_on_exit_gets_no_enter(sim: Sim) -> None:
    r = _step(sim, DEVCHAN_ON_EXIT)
    assert _keys(sim) == []
    assert "NOT pressing Enter" in r.stderr


def test_trust_prompt_moves_down_then_confirms(sim: Sim) -> None:
    r = _step(sim, TRUST_ON_NO, after_down=TRUST_ON_YES)
    assert _keys(sim) == ["send-keys -t =sompong: Down", "send-keys -t =sompong: Enter"]
    assert "answered startup prompt: trust" in r.stderr


def test_trust_prompt_already_on_yes_just_confirms(sim: Sim) -> None:
    _step(sim, TRUST_ON_YES)
    assert _keys(sim) == ["send-keys -t =sompong: Enter"]


def test_trust_prompt_never_presses_enter_on_no_exit(sim: Sim) -> None:
    # Down does not take (the pane never changes): Enter would choose "No, exit".
    r = _step(sim, TRUST_ON_NO)
    assert _keys(sim) == ["send-keys -t =sompong: Down"]
    assert "NOT pressing Enter" in r.stderr


def test_teach_auto_mode_is_answered_3(sim: Sim) -> None:
    _step(sim, TEACH)
    assert _keys(sim) == ["send-keys -t =sompong: 3"]


def test_mcpjson_is_answered_1(sim: Sim) -> None:
    _step(sim, MCPJSON)
    assert _keys(sim) == ["send-keys -t =sompong: 1"]


def test_login_screen_is_reported_once_and_never_typed_at(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("pane", LOGIN)
    r = sim.fn("startup_step; startup_step; echo STEP=$STEP")
    assert _keys(sim) == []
    assert "STEP=wait" in r.stdout
    assert r.stderr.count("asking for a LOGIN") == 1


def test_a_prompt_that_keeps_coming_back_is_left_alone(sim: Sim) -> None:
    # SOMPONG_NOW is fixed, so the second look is inside the 15 s gap.
    sim.set_sessions("sompong")
    sim.put("pane", TEACH)
    r = sim.fn("startup_step; startup_step", SOMPONG_NOW="1000", SOMPONG_ANSWER_GAP_S="15")
    assert len(_keys(sim)) == 1
    assert "answer budget" in r.stderr and "leaving the pane alone" in r.stderr


def test_ready_pane_ends_the_startup(sim: Sim) -> None:
    r = _step(sim, READY)
    assert "STEP=ready" in r.stdout
    assert "channel banner" not in r.stderr


def test_ready_without_the_channel_banner_is_loud(sim: Sim) -> None:
    r = _step(sim, READY_NO_BANNER)
    assert "STEP=ready" in r.stdout
    assert "will NOT arrive until the dev channel loads" in r.stderr


def test_a_blank_pane_just_waits(sim: Sim) -> None:
    r = _step(sim, "")
    assert "STEP=wait" in r.stdout and _keys(sim) == []


# --- preflight, start_session ------------------------------------------------------


def test_preflight_failure_reaches_the_journal(sim: Sim) -> None:
    r = sim.fn("preflight; echo rc=$?", SOMPONG_PREFLIGHT="echo 'unix user sompong does not exist'; exit 1")
    assert "rc=1" in r.stdout
    assert "launcher preflight failed (not starting)" in r.stderr
    assert "unix user sompong does not exist" in r.stderr


def test_preflight_pass(sim: Sim) -> None:
    assert sim.fn("preflight; echo rc=$?", SOMPONG_PREFLIGHT="true").stdout.strip() == "rc=0"


@pytest.mark.skipif(not Path("/proc/self/fd").exists(), reason="needs /proc")
def test_start_session_runs_the_launcher_and_does_not_leak_the_lock_fd(sim: Sim, tmp_path: Path) -> None:
    r = sim.fn(
        f'exec 9>"{tmp_path}/lock"; start_session; echo rc=$?',
        SOMPONG_LAUNCH="bash /x/cxo-claude.sh --role coo",
        SOMPONG_WORKDIR="/opt/somewhere/SomPong",
    )
    assert "rc=0" in r.stdout, r.stderr
    (call,) = sim.calls_of("new-session")
    assert call == "new-session -d -s sompong -x 200 -y 50 -c /opt/somewhere/SomPong bash /x/cxo-claude.sh --role coo"
    assert not [c for c in sim.raw_calls() if c.startswith("new-session") and c.endswith("[fd9]")]


# --- the loop ---------------------------------------------------------------------------


def _loop(sim: Sim, **extra: str) -> subprocess.CompletedProcess:
    base = {
        "SOMPONG_PREFLIGHT": "true",
        "SOMPONG_LAUNCH": "launcher-stub",
        "SOMPONG_START_TIMEOUT_S": "0",
        "SOMPONG_POLL_S": "1",
        "FAKE_SLEEP_LIMIT": "40",
    }
    base.update(extra)
    env = sim.env(**base)
    env.pop("SOMPONG_NOW", None)  # the loop must read the real clock to make progress
    return subprocess.run(["bash", str(SUPERVISE)], env=env, capture_output=True, text=True, timeout=60)


@pytest.mark.skipif(subprocess.run(["bash", "-c", "command -v flock"], capture_output=True).returncode != 0, reason="no flock")
def test_loop_restarts_a_dead_session_and_stops_at_the_crash_budget(sim: Sim) -> None:
    sim.put("ps", "1 0 systemd\n")  # never a claude: every start looks like a crash
    r = _loop(sim, SOMPONG_MAX_RESTARTS="2", SOMPONG_WINDOW_S="600")
    assert r.returncode == 0, r.stderr
    assert len(sim.calls_of("new-session")) == 2  # not 3: the budget held
    # the tmux server the supervisor starts must not hold the supervisor's flock
    assert not [c for c in sim.raw_calls() if c.startswith("new-session") and c.endswith("[fd9]")]
    assert "CRASH LOOP: 2 launches in the last 600s" in r.stderr
    assert "is up but no claude process is under it" in r.stderr
    assert "supervisor exiting" in r.stderr
    assert len((sim.state / "launches").read_text().split()) == 2
    # the dead session was removed with an exact target before the next start
    assert "kill-session -t =sompong" in sim.calls()


@pytest.mark.skipif(subprocess.run(["bash", "-c", "command -v flock"], capture_output=True).returncode != 0, reason="no flock")
def test_loop_leaves_a_live_session_alone(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("pane_pid", "100\n")
    sim.put("pane", READY)
    sim.put("ps", "100 1 bash\n101 100 claude\n")
    r = _loop(sim, FAKE_SLEEP_LIMIT="3")
    assert r.returncode == 0, r.stderr
    assert sim.calls_of("new-session") == []
    assert sim.calls_of("kill-session") == []
    assert not (sim.state / "launches").exists() or (sim.state / "launches").read_text() == ""


@pytest.mark.skipif(subprocess.run(["bash", "-c", "command -v flock"], capture_output=True).returncode != 0, reason="no flock")
def test_loop_does_not_start_when_the_launcher_preflight_fails(sim: Sim) -> None:
    r = _loop(sim, SOMPONG_PREFLIGHT="echo 'SomPong repo not found'; exit 1", FAKE_SLEEP_LIMIT="3")
    assert r.returncode == 0, r.stderr
    assert sim.calls_of("new-session") == []
    assert "launcher preflight failed" in r.stderr and "SomPong repo not found" in r.stderr


@pytest.mark.skipif(subprocess.run(["bash", "-c", "command -v flock"], capture_output=True).returncode != 0, reason="no flock")
def test_loop_answers_the_startup_prompts_then_reports_up(sim: Sim) -> None:
    sim.put("new_pane", TRUST_ON_NO)
    sim.put("after_down", TRUST_ON_YES)
    sim.put("pane_pid", "100\n")
    sim.put("ps", "100 1 bash\n101 100 claude\n")
    # (the fake screen does not change on Enter, so the second look finds the prompt again
    # and the answer budget holds it back: one Down + one Enter, then "leaving the pane alone")
    r = _loop(sim, SOMPONG_START_TIMEOUT_S="1", FAKE_SLEEP_LIMIT="6")
    assert r.returncode == 0, r.stderr
    assert "starting SomPong" in r.stderr
    assert "answered startup prompt: trust" in r.stderr
    assert "send-keys -t =sompong: Down" in sim.calls()


@pytest.mark.skipif(subprocess.run(["bash", "-c", "command -v flock"], capture_output=True).returncode != 0, reason="no flock")
def test_a_second_supervisor_does_not_start(sim: Sim) -> None:
    import fcntl

    sim.state.mkdir(parents=True, exist_ok=True)
    with open(sim.state / "supervisor.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r = sim.run()
    assert r.returncode == 0
    assert "another supervisor holds" in r.stderr
    assert sim.calls_of("new-session") == []


# --- --stop -----------------------------------------------------------------------------


def test_stop_ends_the_session_with_exit_and_no_kill(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("exit_on_exit", "1")
    r = sim.run("--stop", SOMPONG_STOP_GRACE_S="3")
    assert r.returncode == 0, r.stderr
    assert "send-keys -t =sompong: /exit Enter" in sim.calls()
    assert sim.calls_of("kill-session") == []
    assert "session ended cleanly" in r.stderr
    assert (sim.state / "stop").exists()  # a supervisor that is still looping sees it and stops


def test_stop_kills_a_session_that_ignores_exit(sim: Sim) -> None:
    sim.set_sessions("sompong")
    r = sim.run("--stop", SOMPONG_STOP_GRACE_S="2")
    assert r.returncode == 0
    assert "kill-session -t =sompong" in sim.calls()
    assert "still up after 2s — killing it" in r.stderr


def test_stop_with_no_session_is_a_noop(sim: Sim) -> None:
    r = sim.run("--stop")
    assert r.returncode == 0
    assert sim.calls_of("send-keys") == [] and sim.calls_of("kill-session") == []
    assert "no tmux session" in r.stderr
    assert (sim.state / "stop").exists()


def test_usage_on_an_unknown_argument(sim: Sim) -> None:
    r = sim.run("--bogus")
    assert r.returncode == 2 and "usage:" in r.stderr


# --- the files themselves ------------------------------------------------------------------


@pytest.mark.parametrize("name", ["sompong-supervise.sh", "spawn-coo.sh", "cxo-claude.sh", "spawn-cxo.sh"])
def test_scripts_parse(name: str) -> None:
    r = subprocess.run(["bash", "-n", str(ROOT / "scripts" / name)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("name", ["sompong-supervise.sh", "spawn-coo.sh"])
def test_mac_reachable_scripts_avoid_bash4_and_gnu_only_tools(name: str) -> None:
    """spawn-coo.sh runs on the Mac (bash 3.2, BSD userland) and sources the supervisor."""
    src = (ROOT / "scripts" / name).read_text(encoding="utf-8")
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    for banned in ("declare -A", "mapfile", "readarray"):
        assert banned not in code, f"{name}: {banned!r} needs bash 4"
    assert not re.search(r"\$\{[A-Za-z_]+(,,|\^\^)\}", code), "case-modifying expansion needs bash 4"
    assert not re.search(r"(^|[\s;|&(])timeout\s", code), "no `timeout` on the Mac"


def test_unit_file_shape() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert re.search(r"^Type=simple$", text, re.M)
    assert re.search(r"^User=root$", text, re.M)  # tmux must live in root's server; the SESSION is unprivileged
    assert "scripts/sompong-supervise.sh\n" in text
    assert re.search(r"^ExecStop=/bin/bash /opt/MoonieXHQ/Agents/Core/scripts/sompong-supervise.sh --stop$", text, re.M)
    assert re.search(r"^Restart=always$", text, re.M)
    assert re.search(r"^Environment=ORG_HOST=contabo$", text, re.M)
    assert re.search(r"^TimeoutStopSec=\d+$", text, re.M)
    # no secrets and no .env in a unit that is committed
    assert not re.search(r"(KEY|TOKEN|SECRET|PASSWORD)=", text)
    assert "EnvironmentFile" not in text
