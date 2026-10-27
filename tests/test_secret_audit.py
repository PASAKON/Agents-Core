"""HQSecurity: the audit row at the one door (tools/infisical_setup.py cmd_run) and tools/secret_audit.py.

Every secret in here is an obviously fake literal. Nothing touches the real hub, Infisical or a wrapper:
run with the repo venv python directly and ORG_DB_URL unset. The Postgres tests run only when
AUDIT_TEST_PG_URL names a THROWAWAY server (docker run postgres:16 on 127.0.0.1:55432), never the hub.
"""
from __future__ import annotations

import json
import os
import stat
import string
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import secret_audit as sa  # noqa: E402

inf = sa.inf                          # the module secret_audit imported: patch THIS one, not tools.infisical_setup
FAKE = "FAKE-value-not-a-real-secret-0123456789"
FAKES = {"FAKE_API_KEY": FAKE, "FAKE_PORT": "5432", "FAKE_FLAG": "1"}
IDENTITY_ENV = ("CXO_ROLE", "ORG_ROLE", "WORKER_ROLE", "CTO_SESSION_ID", "CXO_SESSION_ID", "ORG_SESSION_ID",
                "CLAUDE_SESSION_ID", "ORG_TASK_ID", "WORKER_TASK_ID", "ORG_PH_PROJECT", "ORG_RUN_ID",
                "MOONIEX_RUN_ID", "RUN_ID", "ORG_DB_URL", "ORG_SECRET_AUDIT", "ORG_HOST")


@pytest.fixture(autouse=True)
def audit_env(monkeypatch, tmp_path):
    for k in IDENTITY_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(inf.AUDIT_DIR_ENV, str(tmp_path / "audit"))
    monkeypatch.setenv("ORG_HOST", "testhost")
    monkeypatch.setattr(sa, "TRANSCRIPT_GLOBS", ())
    monkeypatch.setattr(sa, "RUN_LEDGER", str(tmp_path / "no-ledger.jsonl"))
    return tmp_path / "audit"


def spool_lines(audit: Path) -> list[dict]:
    return [json.loads(x) for p in sorted(audit.glob("spool-*.jsonl")) for x in p.read_text().splitlines()]


# --- redaction ---------------------------------------------------------------------------------

def test_scrub_replaces_a_fetched_value_by_name_and_redacts_token_shaped_runs():
    suffix = string.ascii_uppercase + "0123"
    provider_shaped = "sk" + "_live_" + suffix                      # built at runtime: no provider-shaped literal in the source
    out = inf.scrub_command(["/opt/x/bin/python", "-m", "tools.run", FAKE, f"--url=pg://u:{FAKE}@h/db",
                             provider_shaped, "5432", "1"], FAKES)
    assert FAKE not in out and suffix[:22] not in out
    assert "<secret:FAKE_API_KEY>" in out and "<redacted>" in out
    assert "<secret:FAKE_PORT>" in out                             # an element equal to a fetched value is masked by name
    assert out.startswith("/opt/x/bin/python -m") and out.endswith(" 1")   # a path survives; a 1-char value is not masked
    assert len(inf.scrub_command(["echo", "a " * 400], {})) == inf.AUDIT_CMD_MAX


def test_scrub_cuts_after_redacting_so_a_cut_never_leaves_a_token_prefix():
    token = "TOK" + "A1b2C3d4" * 6                                   # 51 chars
    out = inf.scrub_command(["x"] * 140 + [token], {})              # token starts before the 300-char cut
    assert "A1b2C3d4" not in out


def test_audit_record_carries_names_and_context_but_no_value(monkeypatch):
    for k, v in {"CXO_ROLE": "cto", "CTO_SESSION_ID": "sess-fake", "WORKER_TASK_ID": "task-fake",
                 "ORG_PH_PROJECT": "HQSecurity", "ORG_RUN_ID": "RUN-20261027-1200-abcd"}.items():
        monkeypatch.setenv(k, v)
    rec = inf.audit_record("contabo", "Agents-Core", "prod", "/", FAKES, ["python3", "x.py", FAKE])
    assert rec["names"] == ["FAKE_API_KEY", "FAKE_FLAG", "FAKE_PORT"]
    assert (rec["role"], rec["session"], rec["task_id"], rec["ph_project"], rec["run_card"], rec["host"]) == \
        ("cto", "sess-fake", "task-fake", "HQSecurity", "RUN-20261027-1200-abcd", "testhost")
    assert rec["argv0"] == "python3" and "<secret:FAKE_API_KEY>" in rec["cmd"]
    assert FAKE not in json.dumps(rec)


# --- fail-open ---------------------------------------------------------------------------------

def test_kill_switch_writes_nothing(monkeypatch, audit_env):
    monkeypatch.setenv("ORG_SECRET_AUDIT", "off")
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "off"
    assert not audit_env.exists()


def test_no_hub_url_spools_with_private_modes(audit_env):
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x", FAKE]) == "spool"
    spool = audit_env / "spool-testhost.jsonl"
    assert stat.S_IMODE(spool.stat().st_mode) == 0o600 and stat.S_IMODE(audit_env.stat().st_mode) == 0o700
    assert (audit_env / ".gitignore").read_text() == "*\n"          # `git add -A` must never pick the spool up
    assert FAKE not in spool.read_text() and spool_lines(audit_env)[0]["names"] == sorted(FAKES)


def test_hub_failure_falls_back_to_the_spool(monkeypatch, audit_env):
    monkeypatch.setenv("ORG_DB_URL", "postgresql://127.0.0.1:1/none")
    monkeypatch.setattr(inf, "audit_insert", lambda rec, url: (_ for _ in ()).throw(OSError("hub down")))
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "spool"
    assert len(spool_lines(audit_env)) == 1


def test_hub_url_from_the_fetched_secrets_wins_and_the_row_goes_to_the_hub(monkeypatch, audit_env):
    seen = []
    monkeypatch.setattr(inf, "audit_insert", lambda rec, url: seen.append(url))
    monkeypatch.setenv("ORG_DB_URL", "from-environ")
    assert inf.audit_secret_read("c", "P", "prod", "/", {"ORG_DB_URL": "from-secrets"}, ["x"]) == "hub"
    assert seen == ["from-secrets"] and not audit_env.exists()


def test_unwritable_spool_never_raises(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv(inf.AUDIT_DIR_ENV, str(blocker / "sub"))      # mkdir under a file fails
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "lost"


# --- the door: cmd_run keeps its behaviour -----------------------------------------------------

class FakeOrg:
    def __init__(self, identity):
        self.identity = identity

    def get(self, path, **kw):
        return {"secrets": [{"secretKey": k, "secretValue": v} for k, v in FAKES.items()]}


@pytest.fixture
def door(monkeypatch):
    monkeypatch.setattr(inf, "Org", FakeOrg)
    monkeypatch.setattr(inf, "_project", lambda org, name: {"id": "p1", "name": name})
    execs = []
    monkeypatch.setattr(os, "execvpe", lambda f, a, e: execs.append((f, a, e)))
    return execs


def test_cmd_run_writes_one_row_and_still_execs_with_the_secrets(door, audit_env, capsys):
    inf.cmd_run("contabo", "Agents-Core", "prod", ["python3", "job.py", "--token", FAKE])
    (file, args, env), = door
    assert (file, args[:2]) == ("python3", ["python3", "job.py"]) and env["FAKE_API_KEY"] == FAKE
    rows = spool_lines(audit_env)
    assert len(rows) == 1 and rows[0]["project"] == "Agents-Core" and rows[0]["argv0"] == "python3"
    assert "<secret:FAKE_API_KEY>" in rows[0]["cmd"] and FAKE not in json.dumps(rows)
    err = capsys.readouterr().err
    assert err.startswith("[infisical run] Agents-Core/prod as contabo: FAKE_API_KEY") and FAKE not in err


def test_cmd_run_execs_even_when_the_audit_blows_up(door, monkeypatch):
    monkeypatch.setattr(inf, "audit_record", lambda *a, **k: 1 / 0)
    inf.cmd_run("contabo", "Agents-Core", "prod", ["python3", "job.py"])
    assert len(door) == 1


def test_cmd_run_kill_switch_skips_the_row(door, monkeypatch, audit_env):
    monkeypatch.setenv("ORG_SECRET_AUDIT", "off")
    inf.cmd_run("contabo", "Agents-Core", "prod", ["python3", "job.py"])
    assert len(door) == 1 and not audit_env.exists()


def test_cmd_run_windows_branch_keeps_its_exit_code(monkeypatch, audit_env):
    monkeypatch.setattr(inf, "Org", FakeOrg)
    monkeypatch.setattr(inf, "_project", lambda org, name: {"id": "p1", "name": name})
    monkeypatch.setattr(inf, "_is_nt", lambda: True)
    monkeypatch.setattr(inf.subprocess, "call", lambda argv, env: 7)
    with pytest.raises(SystemExit) as exc:
        inf.cmd_run("winbox", "Agents-Core", "prod", ["cmd.exe", "/c", "echo"])
    assert exc.value.code == 7 and len(spool_lines(audit_env)) == 1


def test_last4_audits_the_read_by_name(monkeypatch, audit_env, capsys):
    monkeypatch.setattr(inf, "_project", lambda org, name: {"id": "p1", "name": name})
    monkeypatch.setattr(inf, "_get_secret", lambda *a, **k: {"secretValue": FAKE})
    inf.cmd_last4(FakeOrg("contabo"), "Agents-Core", "prod", "FAKE_API_KEY")
    assert spool_lines(audit_env)[0]["names"] == ["FAKE_API_KEY"]
    assert FAKE not in capsys.readouterr().out and FAKE not in json.dumps(spool_lines(audit_env))


# --- who / flush / lookback --------------------------------------------------------------------

def test_who_reads_the_spool_and_filters_by_name_substring(audit_env, capsys):
    inf.audit_secret_read("c", "P", "prod", "/", {"ALPHA_TOKEN": "v-alpha-0001"}, ["a"])
    inf.audit_secret_read("c", "P", "prod", "/", {"BETA_TOKEN": "v-beta-00002"}, ["b"])
    assert sa.main(["who", "alpha", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["names"] for r in rows] == [["ALPHA_TOKEN"]] and rows[0]["source"] == "spool"
    assert sa.main(["who", "BETA_TOKEN"]) == 0
    human = capsys.readouterr().out
    assert "1 read(s) of *BETA_TOKEN*" in human and "v-beta-00002" not in human
    assert sa.main(["who", "alpha", "--host", "elsewhere", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_flush_without_a_hub_url_changes_nothing(audit_env, capsys):
    inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"])
    assert sa.main(["flush"]) == 2
    assert len(spool_lines(audit_env)) == 1
    assert "ORG_DB_URL is not set" in capsys.readouterr().err


def test_leak_hint_flags_literals_not_references_switches_or_paths():
    assert sa.leak_hint("FAKE_SERVICE_TOKEN=hunter2hunter2 run.sh") == "assign:FAKE_SERVICE_TOKEN"
    assert sa.leak_hint("curl -H x " + "Ab3Cd4Ef5G" * 4) == "token"
    for safe in ("FAKE_TOKEN=$FAKE_TOKEN x", 'FAKE_TOKEN="$(cat f)" x', "FAKE_TOKEN= x", "ORG_SECRET_AUDIT=off x",
                 "ls /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-039c3494/state",
                 "git rev-parse " + "a1b2c3d4e5" * 4, "sid 11111111-2222-3333-4444-555555555555",
                 "S=/tmp/claude-0/-opt-MoonieXHQ-Agents-Core-worktrees-mooniex-agents--developer--task-039c3494/x"):
        assert sa.leak_hint(safe) is None, safe


def write_transcript(tmp_path: Path, rows: list[dict]) -> str:
    d = tmp_path / "proj" / "-opt-fake-project"
    d.mkdir(parents=True)
    f = d / "11111111-2222-3333-4444-555555555555.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return str(tmp_path / "proj" / "*" / "*.jsonl")


def bash_use(ts: str, command: str) -> dict:
    return {"timestamp": ts, "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": command}}]}}


def test_lookback_reads_bash_inputs_only_and_flags_a_literal_without_printing_it(monkeypatch, tmp_path, capsys):
    now = sa.dt.datetime.now(sa.dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    leaked = "hunter2hunter2"
    pattern = write_transcript(tmp_path, [
        bash_use(now, "python3 tools/infisical_setup.py run Agents-Core prod -- python3 x.py"),
        bash_use(now, f"FAKE_SERVICE_TOKEN={leaked} bash scripts/hub/org-python.sh x.py"),
        bash_use(now, "echo FAKE_SERVICE_TOKEN=$FAKE_SERVICE_TOKEN | wc -c && ls .env"),
        {"timestamp": now, "message": {"content": [{"type": "tool_result", "content": f"infisical run FAKE_RESULT_TOKEN={leaked}"}]}},
    ])
    monkeypatch.setattr(sa, "TRANSCRIPT_GLOBS", (pattern,))
    out = tmp_path / "report.md"
    assert sa.main(["lookback", "--since", "1d", "--out", str(out)]) == 0
    text = out.read_text()
    assert "infisical_setup.py run Agents-Core/prod" in text
    assert text.count("possible leak:") == 1 and ".jsonl:2 (assign:FAKE_SERVICE_TOKEN)" in text
    assert leaked not in text and leaked not in capsys.readouterr().out
    assert "11111111-2222-3333-4444-555555555555" in text          # session id = file name, not redacted
    assert "none on the free plan" in text and "hub not read" in text


# --- redaction of short passwords (PH review 5) ------------------------------------------------

def test_scrub_masks_short_passwords_in_urls_assignments_flags_and_bearer():
    out = inf.scrub_command(["psql", "postgresql://org:pw1234@db.host/x", "PASSWORD=pw5678", "x_api_key=pw9012",
                             "-H", "Authorization: Bearer pw3456", "--password", "pw7890", "--user", "bob",
                             "TOKEN=$REF", "MODE=prod"], {})
    for short in ("pw1234", "pw5678", "pw9012", "pw3456", "pw7890"):
        assert short not in out, short
    assert "postgresql://org:<redacted>@db.host/x" in out and "PASSWORD=<redacted>" in out
    assert "Bearer <redacted>" in out and "--password <redacted>" in out
    assert "--user bob" in out and "TOKEN=$REF" in out and "MODE=prod" in out   # a reference and a plain setting stay


# --- the spool, the readers and the report must not be steered by what other users can plant ----

def test_planted_symlink_spool_is_not_written_through(audit_env, tmp_path):
    audit_env.mkdir(mode=0o700)
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched\n")
    (audit_env / "spool-testhost.jsonl").symlink_to(victim)
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "lost"
    assert victim.read_text() == "untouched\n"


def test_planted_symlink_gitignore_is_not_written_through(audit_env, tmp_path):
    audit_env.mkdir(mode=0o700)
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched\n")
    (audit_env / ".gitignore").symlink_to(victim)
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "spool"
    assert victim.read_text() == "untouched\n"


def test_group_writable_audit_dir_is_refused(audit_env):
    audit_env.mkdir(mode=0o700)
    audit_env.chmod(0o770)
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "lost"
    assert list(audit_env.iterdir()) == []


def test_symlinked_audit_dir_is_refused(audit_env, tmp_path):
    real = tmp_path / "elsewhere"
    real.mkdir(mode=0o700)
    audit_env.symlink_to(real)
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "lost"
    assert list(real.iterdir()) == []


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() != 0, reason="needs root to hand a dir to another uid")
def test_audit_dir_owned_by_someone_else_is_refused(audit_env):
    audit_env.mkdir(mode=0o700)
    os.chown(audit_env, 54321, 54321)
    assert inf.audit_secret_read("c", "P", "prod", "/", FAKES, ["x"]) == "lost"


def test_who_and_flush_ignore_a_symlinked_spool(audit_env, tmp_path, capsys):
    audit_env.mkdir(mode=0o700)
    real = tmp_path / "real-spool.jsonl"
    real.write_text(json.dumps({"ts": "2999-01-01T00:00:00+00:00", "host": "testhost", "user": "u",
                                "names": ["PLANTED_NAME"]}) + "\n")
    (audit_env / "spool-testhost.jsonl").symlink_to(real)
    assert sa.main(["who", "PLANTED", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert sa.main(["flush"]) == 2                            # no hub URL: nothing is read, moved or removed
    assert real.exists() and (audit_env / "spool-testhost.jsonl").is_symlink()


def test_open_regular_skips_fifo_symlink_and_directory(tmp_path):
    import signal
    if not hasattr(os, "mkfifo") or not hasattr(signal, "SIGALRM"):
        pytest.skip("POSIX only")
    real = tmp_path / "real.jsonl"
    real.write_text("x\n")
    (tmp_path / "link.jsonl").symlink_to(real)
    os.mkfifo(tmp_path / "pipe.jsonl")
    (tmp_path / "dir.jsonl").mkdir()
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("open_regular hung on a FIFO")))
    signal.alarm(10)
    try:
        assert sa.open_regular(str(tmp_path / "pipe.jsonl")) is None
        assert sa.open_regular(str(tmp_path / "link.jsonl")) is None
        assert sa.open_regular(str(tmp_path / "dir.jsonl")) is None
        with sa.open_regular(str(real)) as fh:
            assert fh.read() == "x\n"
    finally:
        signal.alarm(0)


def test_lookback_skips_fifo_symlinked_file_symlinked_dir_and_symlinked_ledger(monkeypatch, tmp_path):
    import signal
    if not hasattr(os, "mkfifo") or not hasattr(signal, "SIGALRM"):
        pytest.skip("POSIX only")
    now = sa.dt.datetime.now(sa.dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    pattern = write_transcript(tmp_path, [bash_use(now, "bash scripts/hub/org-python.sh x.py")])
    proj = tmp_path / "proj" / "-opt-fake-project"
    os.mkfifo(proj / "99999999-0000-0000-0000-000000000000.jsonl")
    (proj / "88888888-0000-0000-0000-000000000000.jsonl").symlink_to(next(proj.glob("11111111-*.jsonl")))
    (tmp_path / "proj" / "-linked-dir").symlink_to(proj)
    ledger = tmp_path / "ledger-real.jsonl"
    ledger.write_text(json.dumps({"id": "RUN-1", "ts": "2999-01-01T00:00:00Z", "state": "done"}) + "\n")
    (tmp_path / "ledger-link.jsonl").symlink_to(ledger)
    monkeypatch.setattr(sa, "TRANSCRIPT_GLOBS", (pattern,))
    monkeypatch.setattr(sa, "RUN_LEDGER", str(tmp_path / "ledger-link.jsonl"))
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("lookback hung on a FIFO")))
    signal.alarm(20)
    try:
        text, counts = sa.build_lookback("1d")
    finally:
        signal.alarm(0)
    assert counts["door_commands"] == 1 and counts["sessions"] == 1          # only the one real file
    assert "not reachable on this host" in text                              # the ledger is a link: not read


def test_lookback_prints_to_stdout_by_default_and_writes_no_file(monkeypatch, tmp_path, capsys):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    assert sa.main(["lookback", "--since", "1d"]) == 0
    assert capsys.readouterr().out.startswith("# HQSecurity lookback") and list(cwd.iterdir()) == []


def test_lookback_out_is_a_new_private_file_never_an_existing_one_or_a_link(tmp_path, capsys):
    new = tmp_path / "report.md"
    assert sa.main(["lookback", "--since", "1d", "--out", str(new)]) == 0
    assert stat.S_IMODE(new.stat().st_mode) == 0o600
    assert sa.main(["lookback", "--since", "1d", "--out", str(new)]) == 1     # exists: refused
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched\n")
    link = tmp_path / "link.md"
    link.symlink_to(victim)
    assert sa.main(["lookback", "--since", "1d", "--out", str(link)]) == 1
    assert victim.read_text() == "untouched\n"
    capsys.readouterr()


# --- Postgres (throwaway server only) ----------------------------------------------------------

PG = os.environ.get("AUDIT_TEST_PG_URL")


@pytest.mark.skipif(not PG, reason="AUDIT_TEST_PG_URL (throwaway postgres:16 on 127.0.0.1:55432) not set")
def test_hub_insert_who_flush_and_lookback_round_trip(monkeypatch, audit_env, tmp_path, capsys):
    import psycopg
    with psycopg.connect(PG, autocommit=True) as c:
        c.execute("DROP TABLE IF EXISTS events")
        c.execute("CREATE TABLE events (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, task_id TEXT, "
                  "actor TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT, ts TEXT NOT NULL)")
        c.execute("INSERT INTO events (actor, kind, payload, ts) VALUES ('x','note','mentions infisical here', %s)",
                  (sa._iso(sa.dt.datetime.now(sa.dt.timezone.utc)),))
    monkeypatch.setenv("ORG_DB_URL", PG)
    monkeypatch.setenv("WORKER_TASK_ID", "task-fake")
    assert inf.audit_secret_read("contabo", "P", "prod", "/", {"HUB_ROW_TOKEN": "v-hub-row-0001"}, ["x"]) == "hub"
    monkeypatch.setenv("ORG_DB_URL", "")                              # next row cannot reach the hub: spool
    assert inf.audit_secret_read("contabo", "P", "prod", "/", {"SPOOL_ROW_TOKEN": "v-spool-0001"}, ["y"]) == "spool"
    monkeypatch.setenv("ORG_DB_URL", PG)
    assert sa.main(["who", "_ROW_TOKEN", "--json"]) == 0
    got = {tuple(r["names"]): r["source"] for r in json.loads(capsys.readouterr().out)}
    assert got == {("HUB_ROW_TOKEN",): "hub", ("SPOOL_ROW_TOKEN",): "spool"}
    assert sa.main(["flush"]) == 0 and spool_lines(audit_env) == []
    with psycopg.connect(PG) as c:
        rows = c.execute("SELECT kind, task_id, actor FROM events WHERE kind='secret_read' ORDER BY id").fetchall()
    assert len(rows) == 2 and rows[0][1] == "task-fake" and rows[0][2].endswith("@testhost")
    out = tmp_path / "lb.md"
    assert sa.main(["lookback", "--since", "1d", "--out", str(out)]) == 0
    text = out.read_text()
    assert "| `HUB_ROW_TOKEN` | 1 |" in text and "| note | 1 | 1 |" in text and "mentions infisical" not in text


@pytest.mark.skipif(not PG, reason="AUDIT_TEST_PG_URL not set")
def test_flush_puts_the_spool_back_when_the_hub_refuses(monkeypatch, audit_env):
    import psycopg
    with psycopg.connect(PG, autocommit=True) as c:
        c.execute("DROP TABLE IF EXISTS events")                      # no table: the INSERT fails
    inf.audit_secret_read("contabo", "P", "prod", "/", FAKES, ["x"])
    monkeypatch.setenv("ORG_DB_URL", PG)
    assert sa.main(["flush"]) == 1 and len(spool_lines(audit_env)) == 1
