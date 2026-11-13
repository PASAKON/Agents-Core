"""The router never sends a job to headless agy when the job needs a command agy may not run.

13 Nov 2026: task-74363c69 and task-79bcc8af (developer, MoonieX-Console, npm/node) and task-502a032c
(video_editor, ssh + a python script) died with "headless run produced no output (a tool permission was
auto-denied)". agy runs only config/agy-settings.json's permissions.allow; plans.yaml `agy_skip` names the
jobs that need more (tools/route.agy_skip_reason).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.route as route  # noqa: E402
from tools.quota import Quota, load_plans  # noqa: E402

VENV_PYTEST = "/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_route_agy_skip.py"
BUCKETS = ("claude", "codex", "agy-gemini", "agy-claude")


@pytest.fixture
def cfg():
    """The real plans.yaml (classes, agy_skip), CEO order so no usage-budget file is read."""
    real = load_plans()
    assert real.get("agy_skip"), "config/plans.yaml lost its agy_skip block"
    return {**real, "router": {"order": "ceo", "tie_points": 5, "min_samples": 5}}


@pytest.fixture(autouse=True)
def _hosts_and_quotas(monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "codex", "agy"])


@pytest.fixture
def quotas():
    return {b: Quota(provider=b, weekly_remaining=0.9, daily_remaining=0.9) for b in BUCKETS}


def pick(cfg, quotas, role, **kw):
    return route.pick_runner(role, "contabo", cfg=cfg, quotas=quotas, skill={}, **kw)


# ---------------------------------------------------------------------------- the three tasks of the brief

def test_console_developer_task_skips_agy(cfg, quotas):
    """A developer task on a node project (MoonieX-Console: no test_command, stack node)."""
    choice = pick(cfg, quotas, "developer", project="mooniex-console",
                  brief="Fix the sessions list in server/routes.js, then run the tests.")
    assert choice is not None and choice.runner != "agy"
    assert "agy skipped: needs npm (project mooniex-console)" in choice.reason


def test_video_editor_task_skips_agy_by_role(cfg, quotas):
    choice = pick(cfg, quotas, "video_editor",
                  brief="Cut the b-roll into a 30 s promo and write the cut list.")
    assert choice is not None and choice.runner != "agy"
    assert "agy skipped: video_editor needs commands outside the agy list" in choice.reason


def test_agents_core_python_developer_task_keeps_agy(cfg, quotas):
    choice = pick(cfg, quotas, "developer", project="mooniex-agents",
                  brief=f"Edit tools/route.py. Run `{VENV_PYTEST}`, git diff and git status.")
    assert choice is not None and choice.runner == "agy"
    assert "agy skipped" not in choice.reason


def test_developer_without_a_project_keeps_agy(cfg, quotas):
    choice = pick(cfg, quotas, "developer", brief="Fix the typo in README.md.")
    assert choice is not None and choice.runner == "agy"


# ---------------------------------------------------------------------------- the brief names a command

@pytest.mark.parametrize("brief,cmd", [
    ("Edit the handler, then run `npm test` and fix what breaks.", "npm"),
    ("Run npx vitest run when you are done.", "npx"),
    ("Check the unit with node --test test/x.test.js", "node"),
    ("Run node scripts/check.mjs", "node"),
    ("Copy the file: `ssh winbox powershell -File x.ps1`", "ssh"),
    ("scp out.mp4 winbox:C:/clips/", "scp"),
    ("Then curl https://example.com/health", "curl"),
])
def test_a_brief_that_runs_a_command_outside_the_list_skips_agy(cfg, brief, cmd):
    assert route.agy_skip_reason("developer", "dev_general", brief, None, cfg) == f"needs {cmd}"


@pytest.mark.parametrize("brief", [
    "Add a node to the graph and keep node_modules out of the diff.",
    "Rename the SSH section in README.md.",
    f"Run `{VENV_PYTEST}` and git log.",
    "grep -n foo tools/x.py then cat the result",
    None,
    "",
])
def test_prose_and_allowed_commands_do_not_skip_agy(cfg, brief):
    assert route.agy_skip_reason("developer", "dev_general", brief, None, cfg) is None


def test_edit_only_header_lifts_the_command_and_project_checks(cfg):
    brief = "edit-only: the reviewer runs npm test\n\nEdit server/routes.js. Do not run npm test."
    assert route.agy_skip_reason("developer", "dev_general", brief, "mooniex-console", cfg) is None


def test_edit_only_header_does_not_lift_the_role_check(cfg):
    brief = "edit-only: write the cut list\n\nWrite the cut list."
    assert route.agy_skip_reason("video_editor", "dev_shell", brief, None, cfg)


def test_a_command_the_allow_list_allows_is_not_a_reason_to_skip(cfg, tmp_path, monkeypatch):
    settings = tmp_path / "agy-settings.json"
    settings.write_text(json.dumps({"permissions": {"allow": ["command(npm)"], "deny": []}}))
    monkeypatch.setattr(route, "AGY_SETTINGS", settings)
    brief = "Run npm test"
    assert route.agy_skip_reason("developer", "dev_general", brief, None, cfg) is None
    assert route.agy_skip_reason("developer", "dev_general", "Run npx vitest", None, cfg) == "needs npx"


def test_a_config_without_agy_skip_changes_nothing():
    assert route.agy_skip_reason("video_editor", "dev_shell", "npm test", "mooniex-console", {}) is None


# ---------------------------------------------------------------------------- the project's toolchain

@pytest.fixture
def projects(monkeypatch):
    table = {}
    from lib import config as lib_config
    monkeypatch.setattr(lib_config, "get_project", lambda key: table[key])
    return table


def test_project_with_a_node_test_command(cfg, projects):
    projects["web"] = {"path": "/nope", "stack": ["python"], "test_command": "npx vitest run"}
    assert route.agy_skip_reason("developer", "dev_general", "Fix it", "web", cfg) == "needs npx (project web)"


def test_a_python_test_command_beats_a_package_json(cfg, projects, tmp_path):
    (tmp_path / "package.json").write_text("{}")
    projects["py"] = {"path": str(tmp_path), "stack": ["python", "node"], "test_command": "python -m pytest"}
    assert route.agy_skip_reason("developer", "dev_general", "Fix it", "py", cfg) is None


def test_package_json_at_the_repo_root_marks_a_node_project(cfg, projects, tmp_path):
    (tmp_path / "package.json").write_text("{}")
    projects["web"] = {"path": "/nope", "paths": {"contabo": str(tmp_path)}, "stack": ["static"]}
    assert route.agy_skip_reason("developer", "dev_general", "Fix it", "web", cfg) == "needs npm (project web)"


def test_stack_words_are_the_last_resort(cfg, projects, tmp_path):
    projects["web"] = {"path": str(tmp_path), "stack": ["express", "node"]}
    assert route.agy_skip_reason("developer", "dev_general", "Fix it", "web", cfg) == "needs npm (project web)"
    projects["py"] = {"path": str(tmp_path), "stack": ["python", "typescript"]}
    assert route.agy_skip_reason("developer", "dev_general", "Fix it", "py", cfg) is None


def test_unknown_project_does_not_skip(cfg):
    assert route.agy_skip_reason("developer", "dev_general", "Fix it", "no-such-project", cfg) is None


def test_the_real_registry_marks_node_projects_and_not_agents_core(cfg):
    reason = lambda project: route.agy_skip_reason("developer", "dev_general", "Fix it", project, cfg)  # noqa: E731
    assert reason("mooniex-console") == "needs npm (project mooniex-console)"
    assert reason("mooniex-claudeflow") == "needs npm (project mooniex-claudeflow)"   # test_command npm
    assert reason("mooniex-webapp") == "needs npx (project mooniex-webapp)"           # test_command npx
    assert reason("mooniex-option") == "needs node (project mooniex-option)"          # test_command node
    # Next.js projects with no test_command: the stack word decides on a host with no checkout.
    assert reason("lungnote-webapp") == "needs npm (project lungnote-webapp)"
    assert reason("warpclip-webapp") == "needs npm (project warpclip-webapp)"
    assert reason("mooniex-agents") is None


# ---------------------------------------------------------------------------- the browser_agy lane (GH #188)

def test_browser_agy_lane_is_never_skipped(cfg, quotas):
    brief = ("Read the page. Browser Home: http://127.0.0.1:9280. "
             "Use `/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/agy_browse.py --port 9280 text body`.")
    skipping = {**cfg, "agy_skip": {**cfg["agy_skip"], "roles": ["video_editor", "browser_operator"]}}
    choice = pick(skipping, quotas, "browser_operator", brief=brief, project="mooniex-console")
    assert choice is not None and choice.runner == "agy"
    assert route.agy_skip_reason("browser_operator", route.BROWSER_AGY_CLASS, brief, None, skipping) is None


def test_a_plain_browser_brief_stays_on_claude(cfg, quotas):
    assert pick(cfg, quotas, "browser_operator", brief="use claude-in-chrome") is None


# ---------------------------------------------------------------------------- plan() and the router line

def test_plan_marks_every_agy_candidate_cannot_with_the_reason(cfg, quotas):
    plans = route.plan("developer", brief="Run `npm test`.", host="contabo", cfg=cfg, quotas=quotas, skill={})
    agy = [p for p in plans if p.choice.runner == "agy"]
    assert len(agy) >= 2
    assert all(p.verdict == "cannot" and p.why == "agy skipped: needs npm" for p in agy)
    assert any(p.verdict == "ok" for p in plans if p.choice.runner != "agy")
    assert route.plan_line(agy[0]).endswith("cannot: agy skipped: needs npm")


def test_plan_takes_the_worker_role_from_its_role_argument(cfg, quotas):
    plans = route.plan("video_editor", host="contabo", cfg=cfg, quotas=quotas, skill={})
    assert plans and all(p.verdict == "cannot" for p in plans if p.choice.runner == "agy")


def test_router_line_carries_the_skip_reason_when_claude_takes_the_job(cfg, quotas):
    quotas["codex"] = Quota(provider="codex", weekly_remaining=0.0, daily_remaining=0.0)
    choice = pick(cfg, quotas, "developer", project="mooniex-console", brief="Fix it.")
    assert choice is not None and choice.runner == "claude"
    assert choice.reason.endswith("agy skipped: needs npm (project mooniex-console)")


# ---------------------------------------------------------------------------- the allow-list, read from the real file

def _settings():
    return json.loads((ROOT / "config" / "agy-settings.json").read_text(encoding="utf-8"))["permissions"]


def test_agy_allows_reads_the_real_allow_list():
    for ok in ("ls", "ls -la", "git status", "git diff", "grep -n foo tools/x.py", "pwd", VENV_PYTEST):
        assert route.agy_allows(ok), ok
    for no in ("npm test", "node --test", "ssh winbox", "python tools/chatgpt_images.py", "git push",
               "rm -rf x", "echo a; rm x"):
        assert not route.agy_allows(no), no


def test_deny_wins_and_an_unreadable_file_allows_nothing(tmp_path):
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"permissions": {"allow": ["command(ls)", "command(regex:^echo( .*)?$)"],
                                             "deny": ["command(ls -R)"]}}))
    assert route.agy_allows("ls", f) and route.agy_allows("ls -la", f) and route.agy_allows("echo hi", f)
    assert not route.agy_allows("ls -R", f)
    assert not route.agy_allows("ls", tmp_path / "missing.json")
    f.write_text("{not json")
    assert not route.agy_allows("ls", f)


def test_every_command_in_agy_skip_is_refused_by_the_real_allow_list(cfg):
    """The mirror stays in step: allowing npm in agy-settings.json must be a decision, not a silent drift."""
    commands = cfg["agy_skip"]["commands"]
    assert commands
    for cmd in commands:
        assert not route.agy_allows(cmd), f"{cmd} is now allowed by config/agy-settings.json; drop it from plans.yaml agy_skip"
        assert not route.agy_allows(f"{cmd} x"), cmd


def test_every_denied_tool_command_is_known_to_the_router(cfg):
    """A new plain `command(foo)` deny rule in agy-settings.json must reach plans.yaml agy_skip.commands.
    rm and sudo are file/privilege commands no brief names as its job."""
    denied = {r[len("command("):-1] for r in _settings()["deny"]
              if r.startswith("command(") and " " not in r and not r.startswith("command(regex:")}
    assert denied >= {"curl", "ssh"}
    missing = denied - {"rm", "sudo"} - set(cfg["agy_skip"]["commands"])
    assert not missing, f"denied in config/agy-settings.json but not in plans.yaml agy_skip.commands: {sorted(missing)}"
