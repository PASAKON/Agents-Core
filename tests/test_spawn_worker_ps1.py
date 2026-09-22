"""task-adbc6f43: runner selection (claude|codex|agy) end to end.

Three layers, all testable on the Mac without winbox (per the task brief —
winbox was offline 2026-09-20 and this suite must never depend on it):

  1. windows/spawn-worker.ps1's -Runner dispatch — static text checks (no
     PowerShell on the Mac; same style as scripts/test_spawn_worker_ps1.py's
     existing GH #151/#152 checks). Proves claude's launch path is
     byte-identical to before -Runner existed, and codex/agy are shaped per
     docs/ops/agent-runners.md's measured table.
  2. tools.delegate's hub-side runner validation (_validate_runner,
     _runner_branch_name) — an unknown/unavailable runner must be rejected
     loudly before any ssh call.
  3. tools.delegate's artefact gate (artefact_gate / gate_commit_landed /
     gate_codex_turn_completed) — success is never the runner's own exit
     code; it's the branch's commit + the hub's own test run (+ codex's
     turn.completed event). Uses real local git repos standing in for
     GitHub (bare origin + clone), same no-network pattern
     tests/test_multihost.py's _FakeOrigin uses.

Run via:  pytest tests/test_spawn_worker_ps1.py
(tests/ is not in pytest.ini's default testpaths — run explicitly, same
convention as tests/test_multihost.py and tests/test_delegate_probe_gate.py.)
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.delegate as delegate  # noqa: E402
from lib.config import host as get_host  # noqa: E402

SCRIPT = ROOT / "windows" / "spawn-worker.ps1"


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _code_only() -> str:
    """`_text()` with full-line `#` comments stripped, matching
    scripts/test_spawn_worker_ps1.py's own helper — so a check for whether a
    pattern is actually USED can't be defeated (or falsely tripped) by a
    comment merely mentioning it."""
    return "\n".join(
        ln for ln in _text().splitlines() if not ln.strip().startswith("#")
    )


# ---------------------------------------------------------------------------
# 1. windows/spawn-worker.ps1 -Runner dispatch (static text checks)
# ---------------------------------------------------------------------------

def test_script_exists():
    assert SCRIPT.is_file()


def test_runner_param_has_validate_set():
    text = _text()
    assert re.search(
        r"\[ValidateSet\(\s*'claude',\s*'codex',\s*'agy'\s*\)\]\[string\]\$Runner\s*=\s*'claude'",
        text,
    ), "no -Runner param with ValidateSet('claude','codex','agy') and a 'claude' default"


def test_claude_launch_path_is_unchanged_regression():
    """The exact lines that launched claude.exe BEFORE -Runner existed must
    still all be present, verbatim — task-adbc6f43's own hard rule: 'the
    claude path must come out byte-identical to today.'"""
    code = _code_only()
    must_contain = [
        "$claude = Join-Path $env:USERPROFILE '.local\\bin\\claude.exe'",
        "if (-not (Test-Path $claude)) { $claude = 'claude' }",
        "$claudeArgsSplit = @($ClaudeArgs -split '\\s+' | Where-Object { $_ -ne '' })",
        "$argList = @([string]$taskContent, '-n', [string]$SessionName, "
        "'--append-system-prompt', [string]$systemPrompt) + $claudeArgsSplit",
    ]
    for snippet in must_contain:
        assert snippet in code, f"claude launch regression: missing {snippet!r}"


def test_claude_launcher_line_is_not_piped():
    """CTO review 2026-09-18 (unchanged since): the launcher's
    `& $claudeExe @argArray` call must be a bare invocation, never piped —
    Claude Code (Ink TUI) drops into --print mode and exits immediately on a
    non-TTY stdout, killing every winbox spawn."""
    text = _text()
    m = re.search(r"^&\s*`\$claudeExe\s+@argArray.*$", text, re.MULTILINE)
    assert m, "launcher invocation of $claudeExe not found"
    assert "|" not in m.group(0)


def test_claude_branch_is_still_wt_exe_windows_terminal():
    """codex/agy are headless and must NOT go through wt.exe — only claude's
    branch may reference it."""
    text = _text()
    claude_branch = text[text.index("if ($Runner -eq 'claude')"):text.index("elseif ($Runner -eq 'codex')")]
    assert "wt.exe" in claude_branch
    assert "Microsoft\\WindowsApps\\wt.exe" in claude_branch


def test_codex_argv_matches_measured_table():
    """docs/ops/agent-runners.md §1: `codex exec [PROMPT] -C <dir>
    -s workspace-write --skip-git-repo-check --json -o <file>` — no
    --model/--effort/--allowed-tools invented (codex has no such flags).
    Sliced from `_code_only()` (comments stripped) so a negative assertion
    like "no --model flag" can't be defeated by a comment merely
    mentioning the word."""
    code = _code_only()
    codex_start = code.index("elseif ($Runner -eq 'codex')")
    codex_branch = code[codex_start:code.index("else {", codex_start)]
    assert "'exec'" in codex_branch
    assert "'-C'" in codex_branch and "[string]$wt" in codex_branch
    assert "'-s', 'workspace-write'" in codex_branch
    assert "'--skip-git-repo-check'" in codex_branch
    assert "'--json'" in codex_branch
    assert "'-o'" in codex_branch
    assert "--model" not in codex_branch
    assert "--effort" not in codex_branch
    assert "--allowed-tools" not in codex_branch
    assert "codex.cmd" in codex_branch


def test_codex_never_gates_on_its_own_exit_code():
    code = _code_only()
    codex_start = code.index("elseif ($Runner -eq 'codex')")
    codex_branch = code[codex_start:code.index("else {", codex_start)]
    # EXITCODE is recorded for diagnostics only -- never read back and
    # compared against 0 anywhere in this branch.
    assert "LASTEXITCODE" in codex_branch
    assert "-eq 0" not in codex_branch
    assert "-ne 0" not in codex_branch


def test_agy_argv_matches_measured_table():
    """docs/ops/agent-runners.md §1/§6: `agy -p "<prompt>" --mode
    accept-edits --add-dir <dir>`. Sliced from `_code_only()` for the same
    comment-contamination reason as the codex test above."""
    code = _code_only()
    codex_start = code.index("elseif ($Runner -eq 'codex')")
    agy_start = code.index("else {", codex_start)
    agy_branch = code[agy_start:code.index("$stAct = New-ScheduledTaskAction")]
    assert "'-p'" in agy_branch
    assert "'--mode', 'accept-edits'" in agy_branch
    assert "'--add-dir', [string]$wt" in agy_branch
    assert "agy.exe" in agy_branch
    assert "--dangerously-skip-permissions" not in agy_branch


def test_agy_uses_pipe_not_angle_bracket_for_stdin():
    """PowerShell has no '<' input-redirect operator (that's cmd.exe syntax)
    -- a literal '< NUL' or '< $null' in a .ps1 here-string body would throw
    a parse error the moment launch.ps1 actually runs on winbox."""
    text = _text()
    agy_branch = text[text.index("else {\n        # agy"):text.index("$stAct = New-ScheduledTaskAction")]
    assert "< NUL" not in agy_branch
    assert "< $null" not in agy_branch
    assert "$null | & `$exe @argArray" in agy_branch


def test_pid_poll_filter_is_runner_specific():
    code = _code_only()
    assert re.search(r"codex\s*=\s*\"Name = 'node\.exe' OR Name = 'codex\.exe'\"", code)
    assert re.search(r"agy\s*=\s*\"Name = 'agy\.exe'\"", code)
    assert re.search(r"claude\s*=\s*\"Name = 'claude\.exe'\"", code)


def test_no_runner_ever_uses_dangerous_flags():
    """Hard Rule: no --dangerously-skip-permissions,
    no --dangerously-bypass-approvals-and-sandbox, anywhere in the launcher,
    for any runner."""
    code = _code_only()
    assert "--dangerously-skip-permissions" not in code
    assert "--dangerously-bypass-approvals-and-sandbox" not in code


def test_all_stale_files_named_for_cleanup():
    """GH #151 regression, unaffected by -Runner: all 4 stale-file names
    must still appear (worker.log is NOT one of them — nothing writes it)."""
    text = _text()
    for name in ("REPORT.md", "BLOCKER.md", "MAILBOX.md", "HEARTBEAT"):
        assert name in text


def test_dirty_worktree_refusal_still_present():
    text = _text()
    assert "SPAWN_REFUSED=dirty-worktree" in text


# ---------------------------------------------------------------------------
# 2. tools.delegate hub-side runner validation
# ---------------------------------------------------------------------------

def test_known_runners_are_exactly_claude_codex_agy():
    assert delegate.KNOWN_RUNNERS == ("claude", "codex", "agy")


def test_unknown_runner_rejected_at_the_hub():
    with pytest.raises(ValueError, match="unknown runner"):
        delegate._validate_runner("gpt5", "winbox")


def test_runner_rejected_before_any_host_lookup_for_bad_name():
    """An unknown runner must fail on the NAME itself, not "not available
    on this host" -- two different fixes, two different messages."""
    with pytest.raises(ValueError) as exc:
        delegate._validate_runner("not-a-runner", "mac")
    assert "not available on host" not in str(exc.value)


def test_runner_not_available_on_host_is_a_distinct_error():
    # config/hosts.yaml: mac's `runners:` list is [claude] only.
    with pytest.raises(ValueError, match="not available on host 'mac'"):
        delegate._validate_runner("codex", "mac")


def test_winbox_hosts_all_three_runners():
    assert set(delegate._host_runners("winbox")) == {"claude", "codex", "agy"}


def test_mac_hosts_only_claude():
    assert delegate._host_runners("mac") == ["claude"]


def test_host_with_no_runners_key_defaults_to_claude_only(monkeypatch):
    monkeypatch.setattr(delegate, "get_host", lambda name: {})
    assert delegate._host_runners("some-bare-host") == ["claude"]


def test_claude_branch_name_unchanged_regression():
    """Regression: claude's branch scheme must stay `agent/<role>-<task>` —
    every existing merge/poller path keys on it."""
    assert (delegate._runner_branch_name("claude", "developer", "task-xyz")
            == delegate.branch_name("developer", "task-xyz"))


def test_external_runner_branch_name_shape():
    assert delegate._runner_branch_name("codex", "developer", "task-xyz") == "agent/codex-task-xyz"
    assert delegate._runner_branch_name("agy", "developer", "task-xyz") == "agent/agy-task-xyz"


def test_render_remote_runner_args_claude_matches_original():
    """Regression: the claude branch of _render_remote_runner_args must
    render IDENTICALLY to the pre-task-adbc6f43 _render_remote_claude_args."""
    original = delegate._render_remote_claude_args("developer", "winbox")
    dispatched = delegate._render_remote_runner_args("developer", "winbox", "claude")
    assert dispatched == original


def test_render_remote_runner_args_codex_and_agy_are_empty():
    """No --model/--effort/--allowed-tools invented for codex/agy — neither
    CLI has claude's flag shape (docs/ops/agent-runners.md §1)."""
    assert delegate._render_remote_runner_args("developer", "winbox", "codex") == ""
    assert delegate._render_remote_runner_args("developer", "winbox", "agy") == ""


# ---------------------------------------------------------------------------
# 3. Artefact gate — real local git repos standing in for GitHub, no network
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {repo}\n{r.stderr}")
    return r.stdout.strip()


class _TinyOrigin:
    """A bare 'origin' + a 'work' clone (what the hub gate reads from) + a
    'worker' clone (what a runner's git push simulates)."""

    def __init__(self, tmp: Path):
        self.origin = tmp / "origin.git"
        self.work = tmp / "work"
        self.worker = tmp / "worker"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)],
                       check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)],
                       check=True, capture_output=True)
        _git(self.work, "config", "user.email", "t@test")
        _git(self.work, "config", "user.name", "test")
        (self.work / "README.md").write_text("base\n")
        _git(self.work, "add", "README.md")
        _git(self.work, "commit", "-q", "-m", "C0 base")
        _git(self.work, "push", "-q", "origin", "main")
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.worker)],
                       check=True, capture_output=True)
        _git(self.worker, "config", "user.email", "worker@test")
        _git(self.worker, "config", "user.name", "worker")

    def push_branch_with_commit(self, branch: str) -> None:
        _git(self.worker, "checkout", "-q", "-b", branch)
        (self.worker / "output.txt").write_text("did work\n")
        _git(self.worker, "add", "-A")
        _git(self.worker, "commit", "-q", "-m", f"push {branch}")
        _git(self.worker, "push", "-q", "origin", branch)
        _git(self.worker, "checkout", "-q", "main")

    def push_empty_branch(self, branch: str) -> None:
        """Branch exists on origin but carries ZERO commits ahead of main —
        the 'ran, exited 0, committed nothing' failure mode."""
        _git(self.worker, "checkout", "-q", "-b", branch)
        _git(self.worker, "push", "-q", "origin", branch)
        _git(self.worker, "checkout", "-q", "main")


@pytest.fixture()
def tiny_origin():
    with tempfile.TemporaryDirectory() as td:
        yield _TinyOrigin(Path(td))


def test_gate_commit_landed_true_with_a_real_commit(tiny_origin):
    tiny_origin.push_branch_with_commit("agent/codex-task-g01")
    ok, msg = delegate.gate_commit_landed(str(tiny_origin.work), "agent/codex-task-g01", "main")
    assert ok is True
    assert "1 commit(s) ahead" in msg


def test_gate_commit_landed_false_branch_never_pushed(tiny_origin):
    ok, msg = delegate.gate_commit_landed(str(tiny_origin.work), "agent/codex-task-g02", "main")
    assert ok is False
    assert "not found on origin" in msg


def test_gate_commit_landed_false_zero_commits_ahead(tiny_origin):
    """The exact case task-adbc6f43 asks for by name: a branch exists but
    carries no commit ahead of base."""
    tiny_origin.push_empty_branch("agent/codex-task-g03")
    ok, msg = delegate.gate_commit_landed(str(tiny_origin.work), "agent/codex-task-g03", "main")
    assert ok is False
    assert "0 commits ahead" in msg


def test_gate_codex_turn_completed_true():
    transcript = '{"type": "turn.started"}\n{"type": "turn.completed"}\n'
    ok, msg = delegate.gate_codex_turn_completed(transcript)
    assert ok is True


def test_gate_codex_turn_completed_false_when_failed_precedes():
    transcript = '{"type": "turn.failed"}\n{"type": "turn.completed"}\n'
    ok, msg = delegate.gate_codex_turn_completed(transcript)
    assert ok is False
    assert "turn.failed seen before turn.completed" in msg


def test_gate_codex_turn_completed_false_when_missing():
    ok, msg = delegate.gate_codex_turn_completed(None)
    assert ok is False
    assert "no codex --json transcript" in msg


def test_gate_codex_turn_completed_tolerates_stderr_noise():
    """Non-JSON lines (stderr merged in by the launcher's `*>` redirect)
    must be skipped, not treated as a parse error."""
    transcript = "some stderr garbage\n{\"type\": \"turn.completed\"}\n"
    ok, msg = delegate.gate_codex_turn_completed(transcript)
    assert ok is True


def test_gate_nested_msg_type_shape_also_recognised():
    """codex's real event shape may nest type under msg (both shapes
    documented in the wild for this class of CLI) -- support both rather
    than assuming only the flat one."""
    transcript = '{"msg": {"type": "turn.completed"}}\n'
    ok, _ = delegate.gate_codex_turn_completed(transcript)
    assert ok is True


def test_artefact_gate_refuses_a_run_that_exits_0_with_no_commit(tiny_origin):
    """THE required case: a runner process that exited 0 but committed
    nothing must fail the gate -- gate on the artefact, never the exit code.
    run_tests here returns (0, "all green") -- a clean exit -- and the gate
    must STILL refuse, because commit_landed fails first."""
    def run_tests_would_pass():
        return (0, "all green")

    result = delegate.artefact_gate(
        runner="codex", repo_path=str(tiny_origin.work),
        branch="agent/codex-task-g04", base="main",
        run_tests=run_tests_would_pass,
    )
    assert bool(result) is False
    assert any("not found on origin" in r for r in result.reasons)


def test_artefact_gate_refuses_zero_commits_even_with_passing_tests(tiny_origin):
    tiny_origin.push_empty_branch("agent/codex-task-g05")

    def run_tests_would_pass():
        return (0, "all green")

    result = delegate.artefact_gate(
        runner="codex", repo_path=str(tiny_origin.work),
        branch="agent/codex-task-g05", base="main",
        run_tests=run_tests_would_pass,
    )
    assert bool(result) is False
    assert any("0 commits ahead" in r for r in result.reasons)


def test_artefact_gate_never_calls_run_tests_when_no_commit(tiny_origin):
    """The test suite must not even be run against a branch with nothing
    committed -- it would just be testing `base` again."""
    calls = []

    def run_tests_spy():
        calls.append(1)
        return (0, "")

    delegate.artefact_gate(
        runner="claude", repo_path=str(tiny_origin.work),
        branch="agent/developer-task-g06", base="main",
        run_tests=run_tests_spy,
    )
    assert calls == []


def test_artefact_gate_codex_refuses_without_turn_completed_even_with_commit(tiny_origin):
    """A codex branch that committed real work but never produced a
    turn.completed event must still fail -- the transcript check is not
    optional just because git looks fine."""
    tiny_origin.push_branch_with_commit("agent/codex-task-g07")

    def run_tests_would_pass():
        return (0, "all green")

    result = delegate.artefact_gate(
        runner="codex", repo_path=str(tiny_origin.work),
        branch="agent/codex-task-g07", base="main",
        run_tests=run_tests_would_pass,
        codex_transcript=None,
    )
    assert bool(result) is False
    assert any("no codex --json transcript" in r for r in result.reasons)


def test_artefact_gate_passes_when_commit_and_tests_and_transcript_all_clean(tiny_origin):
    tiny_origin.push_branch_with_commit("agent/codex-task-g08")

    def run_tests_would_pass():
        return (0, "3 passed")

    result = delegate.artefact_gate(
        runner="codex", repo_path=str(tiny_origin.work),
        branch="agent/codex-task-g08", base="main",
        run_tests=run_tests_would_pass,
        codex_transcript='{"type": "turn.completed"}\n',
    )
    assert bool(result) is True


def test_artefact_gate_fails_when_test_suite_itself_fails(tiny_origin):
    tiny_origin.push_branch_with_commit("agent/agy-task-g09")

    def run_tests_would_fail():
        return (1, "2 failed, 1 passed")

    result = delegate.artefact_gate(
        runner="agy", repo_path=str(tiny_origin.work),
        branch="agent/agy-task-g09", base="main",
        run_tests=run_tests_would_fail,
    )
    assert bool(result) is False
    assert any("test suite failed" in r for r in result.reasons)


def test_artefact_gate_agy_does_not_require_codex_transcript(tiny_origin):
    """agy has no --json transcript concept -- the codex-only check must not
    apply to it."""
    tiny_origin.push_branch_with_commit("agent/agy-task-g10")

    def run_tests_would_pass():
        return (0, "ok")

    result = delegate.artefact_gate(
        runner="agy", repo_path=str(tiny_origin.work),
        branch="agent/agy-task-g10", base="main",
        run_tests=run_tests_would_pass,
    )
    assert bool(result) is True


# ---------------------------------------------------------------------------
# 4. config/hosts.yaml runners: list sanity (no winbox needed)
# ---------------------------------------------------------------------------

def test_hosts_yaml_winbox_lists_all_three_runners():
    assert set(get_host("winbox").get("runners", [])) == {"claude", "codex", "agy"}


def test_hosts_yaml_mac_lists_only_claude():
    assert get_host("mac").get("runners", ["claude"]) == ["claude"]
