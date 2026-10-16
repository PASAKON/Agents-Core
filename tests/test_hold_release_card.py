"""tools/hold_release_card.py: the sshd forced command a winbox PH uses to ask the CEO to
lift the winbox hold (OrgMesh P3-A, docs/ops/winbox-hold-release.md).

The key behind it can run this and nothing else, so the parser is the security boundary:
exactly one form passes, and of the words only a [a-z0-9-] slug reaches the card's command
line. No test here opens a socket, runs ssh or touches the hub: RUN_INBOX_URL points at the
loopback discard port with no token, and the two hub calls (the pending list and the POST)
are replaced by recorders. The entry-point tests run the real script under `python -E -s`,
as authorized_keys does, with --dry-run, which sends nothing.

Run:  .venv/bin/python -m pytest tests/test_hold_release_card.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.ask_run as ask_run  # noqa: E402
import tools.hold_release_card as hrc  # noqa: E402

DOC = ROOT / "docs" / "ops" / "winbox-hold-release.md"
CARD_ID = "RUN-20261017-0712-ab12"

# Pinned on purpose, not built from the module's constants: an edit to the card the CEO
# approves must show up as a diff in this file.
GOLDEN_COMMAND = (
    r"ssh winbox 'C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe "
    r"C:\mooniex\pclease\pc_lease.py ceo-off --ceo-said {slug} "
    r"& del %USERPROFILE%\Documents\CookieRunScript\modelplay\ESC_HOLD "
    r"& C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe "
    r"C:\mooniex\pclease\pc_lease.py status'")


def ask(words: str, who: str | None = None) -> str:
    return f'ask-release --ceo-said "{words}"' + (f" --who {who}" if who else "")


@pytest.fixture
def hub(tmp_path, monkeypatch):
    """The hub, as two recorders. `pending` is what the pending list returns."""
    monkeypatch.setenv("RUN_INBOX_URL", "http://127.0.0.1:9")      # discard port: a leak fails
    monkeypatch.delenv("RUN_INBOX_TOKEN", raising=False)
    monkeypatch.setattr(hrc, "LOCK", tmp_path / "locks" / "hold_release_card.lock")
    st = SimpleNamespace(pending=[], listed=[], posted=[], list_error=None, post_error=None,
                         reply={"id": CARD_ID, "status": "pending", "risk": "amber"})

    def fake_call(method, path, *, body=None, query=None):
        st.listed.append((method, path, query))
        if st.list_error:
            raise st.list_error
        return {"asks": st.pending}

    def fake_submit(payload, path=ask_run.ASKS_PATH):
        st.posted.append(payload)
        if st.post_error:
            raise st.post_error
        return {**st.reply, "url": "https://hub.invalid/run#" + str(st.reply.get("id"))}

    monkeypatch.setattr(ask_run, "_call", fake_call)
    monkeypatch.setattr(ask_run, "submit", fake_submit)
    return st


def run(cmd, capsys, argv=()):
    code = hrc.main(list(argv), {"SSH_ORIGINAL_COMMAND": cmd} if cmd is not None else {})
    cap = capsys.readouterr()
    return code, cap.out, cap.err


# --- the one accepted form -----------------------------------------------------------

@pytest.mark.parametrize("cmd,words,who", [
    (ask("lift the hold please"), "lift the hold please", "winbox-ph"),
    (ask("lift the hold please", "ph-7cf1a2b3"), "lift the hold please", "ph-7cf1a2b3"),
    (ask("abc"), "abc", "winbox-ph"),
    (ask("x" * 120, "A_b-9"), "x" * 120, "A_b-9"),
    (ask("a" * 40, "w" * 40), "a" * 40, "w" * 40),
    (ask("I'm done; use it (ok)? 100% yes!"), "I'm done; use it (ok)? 100% yes!", "winbox-ph"),
])
def test_the_one_form_parses(cmd, words, who):
    assert hrc.parse(cmd) == (words, who)


REFUSED_FORMS = [
    None, "", " ", "ask-release", "ask-release --ceo-said", "ask-release --ceo-said ",
    'ask-release --ceo-said ""',
    "ask-release --ceo-said lift the hold",                  # not quoted: ssh joined the words
    'ask-release --ceo-said "ok"',                           # 2 characters
    'ask-release --ceo-said "' + "x" * 121 + '"',            # 121 characters
    'ask-release --ceo-said "!!! ???"',                       # no letter or digit at all
    'ask-release --ceo-said "a-b"',                           # only 2 letters or digits
    'ask-release --ceo-said "abc" extra',
    'ask-release --ceo-said "abc" --who',
    'ask-release --ceo-said "abc" --who ""',
    'ask-release --ceo-said "abc" --who a b',
    'ask-release --ceo-said "abc" --who ' + "w" * 41,
    'ask-release --ceo-said "abc" --who a.b',
    'ask-release --ceo-said "abc" --who a;b',
    'ask-release --ceo-said "abc" --who a$(id)',
    'ask-release --ceo-said "abc" --who ph --who ph',
    'ask-release --who ph --ceo-said "abc"',                  # other order
    'ask-release --ceo-said "abc" --ceo-said "abc"',
    'ask-release --ceo-said "abc"  --who ph',                 # two spaces
    ' ask-release --ceo-said "abc"',
    'ask-release --ceo-said "abc" ',
    'ask-release --ceo-said "abc"\n',
    'ask-release --ceo-said "abc"\nid',
    'ask-release --ceo-said "abc"\r\n',
    'ask-release --ceo-said "ab\ncd"',
    'ask-release --ceo-said "ab\tcd"',
    'ask-release --ceo-said "ab\x00cd"',
    'ask-release --ceo-said "ab\x7fcd"',
    'ask-release --ceo-said "he said "yes""',                 # a quote closes the words
    'ask-release --ceo-said "abc" ; id',
    'ask-release --ceo-said "abc" && id',
    'ask-release --ceo-said "abc" | sh',
    'ask-release --ceo-said "abc" `id`',
    'ask-release --ceo-said "abc" $(id)',
    'ask-release --ceo-said "abc" > /tmp/x',
    "ask-release --ceo-said 'abc def'",                       # single quotes are not the form
    'ASK-RELEASE --ceo-said "abc"',
    'ask-release --ceo-said "\u0e1b\u0e25\u0e14\u0e25\u0e47\u0e2d\u0e01"',   # Thai
    'ask-release --ceo-said "caf\u00e9 ok"',
    'ask-release --ceo-said "abc\u200b"',                     # zero-width space
    'ask-release --ceo-said "abc\udcff"',                     # undecodable byte (surrogateescape)
    "ask-release-x --ceo-said \"abc\"",
    "bash", "sh -c id", "ls -la", "id", "scp -t /tmp", "sftp", "cat /etc/passwd",
    "internal-sftp", "rsync --server -vlogDtpre.iLsfxC . /tmp", "git-upload-pack x",
    "ask-release --ceo-said \"abc\" --who ph && ask-release --ceo-said \"abc\"",
]


@pytest.mark.parametrize("cmd", REFUSED_FORMS)
def test_everything_else_is_refused_and_nothing_is_sent(hub, capsys, cmd):
    code, out, err = run(cmd, capsys)
    assert code == 2 and out == ""
    assert err.startswith("refused: ")
    assert hub.listed == [] and hub.posted == [], "a refused ask reached the hub"


def test_no_ssh_original_command_at_all_is_refused(hub, capsys):
    code, out, err = run(None, capsys)             # an interactive login on the forced key
    assert (code, out) == (2, "") and err.startswith("refused: ")
    assert hub.posted == []


@pytest.mark.parametrize("argv", [["x"], ["--dry-run", "x"], ["-h"], ["ask-release"], ["--help"]])
def test_the_script_takes_no_arguments_but_dry_run(hub, capsys, argv):
    code, out, err = run(ask("lift the hold"), capsys, argv)
    assert (code, out) == (2, "") and "no arguments" in err
    assert hub.posted == []


# --- what reaches the card ------------------------------------------------------------

HOSTILE = [
    "a; rm -rf /", "a & del C:\\x", "a | calc", "a && b || c", "it's here", "`id` now", "$(id) ok",
    "${HOME} ok", "%USERPROFILE% ok", "a > b < c", "..\\..\\x ok", "a' & calc & '", "a\\' ok",
    "-oProxyCommand=x ok", "--ceo-said --who", "ceo-off", "~ ok ~ yes", "a*b?c[d]{e}", "a#b !c @d =e",
    "  lift   the   hold ",
]


@pytest.mark.parametrize("words", HOSTILE)
def test_only_a_slug_of_the_words_reaches_the_command_line(hub, words):
    cmd = hrc.command_for(hrc.slug_of(words))
    slug = hrc.slug_of(words)
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
    payload = hrc.build_payload(*hrc.parse(ask(words)))
    assert payload["command"] == cmd == GOLDEN_COMMAND.format(slug=slug)
    # the only thing between the template's head and tail is the slug
    middle = payload["command"][len(hrc.COMMAND_HEAD):-len(hrc.COMMAND_TAIL)]
    assert middle == slug
    # and the slug adds no shell or cmd metacharacter that the fixed template lacks
    assert set(slug) <= set("abcdefghijklmnopqrstuvwxyz0123456789-")


def test_the_slug_is_lowercase_and_trimmed():
    assert hrc.slug_of("  Lift THE hold, please!!  ") == "lift-the-hold-please"
    assert hrc.slug_of("a--b__c") == "a-b-c"


def test_the_card_is_the_fixed_template_except_the_slug(hub):
    a = hrc.build_payload(*hrc.parse(ask("lift the hold now", "ph-one")))
    b = hrc.build_payload(*hrc.parse(ask("completely different words", "ph-two")))
    assert a["command"] == GOLDEN_COMMAND.format(slug="lift-the-hold-now")
    assert b["command"] == GOLDEN_COMMAND.format(slug="completely-different-words")
    for key in ("host", "kind", "expected", "risk", "timeout_s", "expects_input"):
        assert a[key] == b[key], key
    assert set(a) == set(b) == {"host", "kind", "command", "why", "expected", "risk",
                                "timeout_s", "expects_input", "requester"}
    assert a["host"] == "contabo" and a["kind"] == "command" and a["risk"] == "amber"
    assert a["timeout_s"] == 600 and a["expects_input"] is False
    assert a["requester"] == {"session": "ph-one", "role": "project_head"}
    assert b["requester"] == {"session": "ph-two", "role": "project_head"}
    assert a["expected"] == "PC: released, then the ESC hold is cleared and the status lines print."


def test_no_who_means_the_default_session(hub):
    p = hrc.build_payload(*hrc.parse(ask("lift the hold now")))
    assert p["requester"] == {"session": "winbox-ph", "role": "project_head"}


def test_why_quotes_the_words_and_fits_what_the_ceo_reads(hub):
    short = hrc.build_payload(*hrc.parse(ask("I am done, lift it")))
    assert short["why"] == 'winbox PH quotes you: "I am done, lift it"'
    longest = "word " * 24
    p = hrc.build_payload(*hrc.parse(ask(longest.strip()[:120])))
    assert len(p["why"]) <= 90 and "\n" not in p["why"]
    assert p["why"].endswith('..."') and p["why"].startswith('winbox PH quotes you: "word word')
    # the CEO reads why + expected: two lines, never more than 5 lines of 90
    from lib import ceo_text
    ceo_text.check_ceo_text([("why", p["why"]), ("expected", p["expected"])])
    exactly = "x" * 66
    assert hrc.why_for(exactly).endswith(exactly + '"')                  # 66 fits as is
    assert hrc.why_for("x" * 67).endswith('...' + '"') and len(hrc.why_for("x" * 67)) == 90


def test_the_card_runs_the_path_the_wrapper_deploys():
    sh = (ROOT / "scripts" / "pc-lease.sh").read_text(encoding="utf-8")
    py = re.search(r"^PYEXE='([^']+)'", sh, re.M).group(1)
    remote_dir = re.search(r"^REMOTE_DIR='([^']+)'", sh, re.M).group(1)
    assert hrc.WINBOX_PY == py
    assert hrc.PC_LEASE == remote_dir + "\\pc_lease.py"


def test_the_template_names_a_verb_pc_lease_has_and_the_words_it_requires():
    src = (ROOT / "windows" / "pc_lease.py").read_text(encoding="utf-8")
    assert '("ceo-on", cmd_ceo_on), ("ceo-off", cmd_ceo_off)' in src
    assert "ceo-off --ceo-said " in hrc.COMMAND_HEAD       # ceo_button_guard needs non-empty words


# --- local refusals the hub would repeat ----------------------------------------------

def test_a_secret_shaped_quote_is_refused_before_anything_is_sent(hub, capsys):
    # assembled at runtime: CI runs gitleaks over the whole history, and a literal
    # key=value in this file would fail it for good (same trick as tests/test_ask_run.py)
    value = "".join(("abcdef", "123456"))
    code, out, err = run(ask("my " + "tok" + "en=" + value + " is ready"), capsys)
    assert (code, out) == (2, "")
    assert "secret_shaped_value" in err and value not in err
    assert hub.listed == [] and hub.posted == []


@pytest.mark.parametrize("who", ["_ph", "-ph"])
def test_a_who_ask_run_cannot_use_as_a_mailbox_is_refused(hub, capsys, who):
    code, out, err = run(ask("lift the hold", who), capsys)
    assert (code, out) == (2, "") and err.startswith("refused: ")
    assert hub.posted == []


def test_the_process_environment_cannot_change_who_the_card_is_from(hub, capsys, monkeypatch):
    monkeypatch.setenv("WORKER_TASK_ID", "task-deadbeef")
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", "cto-0badc0de")
    code = hrc.main([], {"SSH_ORIGINAL_COMMAND": ask("lift the hold", "ph-1"),
                         "WORKER_TASK_ID": "task-deadbeef", "CXO_ROLE": "cto"})
    assert code == 0
    assert hub.posted[0]["requester"] == {"session": "ph-1", "role": "project_head"}


# --- one at a time ----------------------------------------------------------------------

def card(status="pending", words="lift-it", **kw):
    return {"id": "RUN-20261017-0600-aaaa", "status": status, "host": "contabo",
            "command": GOLDEN_COMMAND.format(slug=words), **kw}


def test_a_pending_hold_release_card_blocks_the_next_ask(hub, capsys):
    hub.pending = [card()]
    code, out, err = run(ask("lift the hold again"), capsys)
    assert (code, out) == (2, "")
    assert "already waiting" in err and "RUN-20261017-0600-aaaa" in err
    assert hub.posted == [], "a second card was raised while one was pending"
    assert hub.listed == [("GET", "/api/run/asks", {"status": "pending", "limit": "50"})]


def test_the_block_holds_whoever_asked(hub, capsys):
    hub.pending = [card()]
    assert run(ask("lift the hold", "another-ph"), capsys)[0] == 2
    assert hub.posted == []


@pytest.mark.parametrize("other", [
    card(status="done"), card(status="expired"), card(status="denied"), card(status="cancelled"),
    {**card(), "status": None},
    {**card(), "command": "systemctl restart mooniex-console"},
    {**card(), "command": GOLDEN_COMMAND.format(slug="ok") + " ; id"},         # near miss
    {**card(), "command": GOLDEN_COMMAND.format(slug="OK")},                    # not a slug
    {**card(), "command": GOLDEN_COMMAND.format(slug="a b")},
    {**card(), "command": GOLDEN_COMMAND.format(slug="")},
    {**card(), "command": None},
    {"id": "RUN-x", "status": "pending"},
    "not a dict",
])
def test_only_a_pending_card_of_the_template_blocks(hub, capsys, other):
    hub.pending = [other]
    code, out, _ = run(ask("lift the hold"), capsys)
    assert (code, out) == (0, CARD_ID + "\n")
    assert len(hub.posted) == 1


def test_a_card_further_down_the_list_still_blocks(hub, capsys):
    hub.pending = [card(status="done"), {**card(), "command": "echo hi"}, card()]
    assert run(ask("lift the hold"), capsys)[0] == 2


def test_a_bare_list_answer_is_read_too(hub, capsys, monkeypatch):
    monkeypatch.setattr(ask_run, "_call", lambda *a, **k: [card()])
    assert run(ask("lift the hold"), capsys)[0] == 2


def test_when_the_hub_cannot_say_whether_one_is_pending_nothing_is_raised(hub, capsys):
    hub.list_error = ask_run.HubError("hub unreachable", transient=True)
    code, out, err = run(ask("lift the hold"), capsys)
    assert (code, out) == (3, "") and err.startswith("hub error")
    assert hub.posted == []


def test_a_lock_that_cannot_be_taken_does_not_stop_the_ask(hub, capsys, tmp_path, monkeypatch):
    (tmp_path / "file").write_text("x")
    monkeypatch.setattr(hrc, "LOCK", tmp_path / "file" / "sub" / "x.lock")     # parent is a file
    assert run(ask("lift the hold"), capsys)[:2] == (0, CARD_ID + "\n")


def test_the_check_and_the_post_run_under_the_lock(hub, capsys, monkeypatch):
    import fcntl
    seen = []
    real_flock = fcntl.flock
    monkeypatch.setattr(fcntl, "flock", lambda fd, op: (seen.append("lock"), real_flock(fd, op))[1])
    real_call, real_submit = ask_run._call, ask_run.submit
    monkeypatch.setattr(ask_run, "_call", lambda *a, **k: (seen.append("list"), real_call(*a, **k))[1])
    monkeypatch.setattr(ask_run, "submit", lambda *a, **k: (seen.append("post"), real_submit(*a, **k))[1])
    assert run(ask("lift the hold"), capsys)[0] == 0
    assert seen == ["lock", "list", "post"]


# --- what the PH is told --------------------------------------------------------------

def test_success_prints_the_card_id_and_only_that(hub, capsys):
    code, out, err = run(ask("lift the hold", "ph-1"), capsys)
    assert (code, out, err) == (0, CARD_ID + "\n", "")
    assert len(hub.posted) == 1


def test_a_hub_error_names_the_status_and_code_never_the_hub_address(hub, capsys, monkeypatch):
    monkeypatch.setenv("RUN_INBOX_URL", "https://sentinel-host.invalid:4443")
    monkeypatch.setenv("RUN_INBOX_TOKEN", "sentinel-token-value")
    hub.post_error = ask_run.HubError(
        "hub refused (403: freeform_needs_c_level) at https://sentinel-host.invalid:4443 "
        "token sentinel-token-value", status=403, code="freeform_needs_c_level")
    code, out, err = run(ask("lift the hold"), capsys)
    assert (code, out) == (3, "")
    assert err.strip() == "hub error (403) freeform_needs_c_level"
    assert "sentinel" not in err


def test_no_answer_from_the_hub_is_said_without_the_cause(hub, capsys, monkeypatch):
    monkeypatch.setenv("RUN_INBOX_URL", "https://sentinel-host.invalid")
    hub.list_error = ask_run.HubError("hub unreachable at https://sentinel-host.invalid: refused",
                                      transient=True)
    code, _, err = run(ask("lift the hold"), capsys)
    assert code == 3 and "sentinel" not in err and "no answer from the hub" in err


@pytest.mark.parametrize("bad", ["", None, 7, "RUN-", "Q-20261017-0712-ab12", "RUN-1\nid", "x" * 90])
def test_an_id_that_is_not_a_run_card_id_is_not_passed_on(hub, capsys, bad):
    hub.reply = {"id": bad}
    code, out, err = run(ask("lift the hold"), capsys)
    assert (code, out) == (3, "") and err.startswith("hub error")


def test_no_environment_value_is_printed_on_any_path(hub, capsys, monkeypatch):
    for k in ("RUN_INBOX_URL", "RUN_INBOX_TOKEN", "ORG_DB_URL"):
        monkeypatch.setenv(k, "sentinel-" + k.lower())
    outs = [run(ask("lift the hold"), capsys), run("ls", capsys),
            run(ask("lift the hold"), capsys, ["--dry-run"])]
    hub.pending = [card()]
    outs.append(run(ask("lift the hold"), capsys))
    for _, out, err in outs:
        assert "sentinel" not in out + err


# --- --dry-run and the real entry point -------------------------------------------------

def test_dry_run_prints_the_card_and_calls_nothing(hub, capsys):
    code, out, err = run(ask("lift the hold", "ph-1"), capsys, ["--dry-run"])
    assert code == 0 and err == ""
    body = json.loads(out)
    assert body["command"] == GOLDEN_COMMAND.format(slug="lift-the-hold")
    assert body["requester"]["session"] == "ph-1"
    assert hub.listed == [] and hub.posted == []


def _entry(cmd, *flags):
    """The script as authorized_keys runs it: `python -E -s tools/hold_release_card.py`."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("RUN_INBOX", "PYTHON"))}
    env.pop("SSH_ORIGINAL_COMMAND", None)
    if cmd is not None:
        env["SSH_ORIGINAL_COMMAND"] = cmd
    return subprocess.run([sys.executable, "-E", "-s", "tools/hold_release_card.py", *flags],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


def test_the_script_runs_under_dash_E_dash_s_as_authorized_keys_runs_it():
    r = _entry(ask("lift the hold please", "ph-7cf"), "--dry-run")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["command"] == GOLDEN_COMMAND.format(slug="lift-the-hold-please")


@pytest.mark.parametrize("cmd", ["id", 'ask-release --ceo-said "a" ; id', None])
def test_the_script_refuses_other_commands_with_exit_2(cmd):
    r = _entry(cmd)
    assert r.returncode == 2 and r.stdout == "" and r.stderr.startswith("refused: ")


def test_the_script_without_a_token_says_hub_error_and_exits_3():
    # no RUN_INBOX_TOKEN, the home has no token file, and the loopback discard port is closed
    r = subprocess.run([sys.executable, "-E", "-s", "tools/hold_release_card.py"], cwd=ROOT,
                       env={"PATH": os.environ["PATH"], "HOME": "/nonexistent-home",
                            "RUN_INBOX_URL": "http://127.0.0.1:9",
                            "SSH_ORIGINAL_COMMAND": ask("lift the hold")},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 3 and r.stdout == ""
    assert r.stderr.startswith("hub error") and "127.0.0.1" not in r.stderr


# --- the doc and the repo ----------------------------------------------------------------

def test_the_doc_carries_the_authorized_keys_line_the_script_expects():
    doc = DOC.read_text(encoding="utf-8")
    line = ('command="cd /opt/MoonieXHQ/Agents/Core && exec bash scripts/hub/with-org-db-env.sh '
            '.venv/bin/python -E -s tools/hold_release_card.py",from="<winbox tailnet ip>",restrict')
    assert line in doc
    assert "id_hold_release" in doc and "pc_lease.py ask-release" in doc


def test_no_address_is_written_in_the_new_files():
    ip = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    for path in (ROOT / "tools" / "hold_release_card.py", DOC):
        text = path.read_text(encoding="utf-8")
        assert not ip.findall(text), f"{path.name} names an address"
        assert "100.64" not in text
