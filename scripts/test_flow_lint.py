"""Tests for scripts/flow-lint.py -- the flow.yaml contract of a Workflow skill
(.claude/skills/ALL_Protocol_SkillAuthor/references/workflow-flow.md, CEO 2026-10-02).

One valid fixture flow passes clean; every rule F1-F14 is then broken one at a
time and must report under its own name. `export` is checked for the computed
values the Flow board draws (depth, order, effective stage, auto %, cost).

Every fixture lives under tmp_path: a fake repo with .claude/skills, tools/
and policies/agents.yaml. The real corpus is never read.

Run standalone:   python scripts/test_flow_lint.py
Or under pytest:  pytest scripts/test_flow_lint.py
"""
from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("flow_lint", ROOT / "scripts" / "flow-lint.py")
assert _SPEC is not None and _SPEC.loader is not None
flow_lint = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = flow_lint
_SPEC.loader.exec_module(flow_lint)

NAME = "CMO_Workflow_Demo"

FLOW = {
    "schema": "mooniex.flow/v1",
    "flow": "demo",
    "name": "Demo episode",
    "skill": NAME,
    "owner": "CMO",
    "goal": "Prove the flow contract end to end.",
    "output": "A public post.",
    "trigger": {"kind": "cron", "cron": "0 9 * * 1-5", "tz": "Asia/Bangkok"},
    "watcher": "CMO@contabo",
    "budget": {"cash_usd": 2.0},
    "phases": [{"id": "pre", "name": "Pre"}, {"id": "make", "name": "Make"}],
    "nodes": [
        {"id": "script", "name": "Script", "does": "Writes the script.", "phase": "pre", "kind": "agent",
         "after": [], "role": "cmo", "skill": "CMO_Standard_Demo", "stage": "agent",
         "verify": {"human": "CEO"},
         "measured": [{"date": "2026-09-30", "cost_usd": 3.0, "turns": 80, "source": "task-aaaa1111"}]},
        {"id": "approve", "name": "Approve", "does": "The CEO approves the script.", "phase": "pre",
         "kind": "human", "after": ["script"], "approver": "CEO", "verify": {"human": "CEO"}},
        {"id": "tts", "name": "Voice", "does": "Makes the voice track.", "phase": "make", "kind": "api",
         "after": ["approve"], "tool": "tools/tts.py", "provider": "fal",
         "unit_cost": {"usd": 0.00058, "per": "second", "source": "task-bbbb2222", "date": "2026-09-30"},
         "verify": {"cmd": "python tools/tts.py --check"}, "on_fail": {"retry": 2},
         "blockers": ["credit", "upstream"],
         "measured": [{"date": "2026-09-30", "cost_usd": 0.04, "source": "task-bbbb2222"}]},
        {"id": "cut", "name": "Cut", "does": "Cuts the episode.", "phase": "make", "kind": "agent",
         "after": ["tts"], "role": "video_editor", "skill": "CMO_Procedure_Demo", "stage": "shadow",
         "graduate": {"candidate": "tools/compose.py", "scorer": "tools/score.py", "bar": "10/10"},
         "verify": {"cmd": "python tools/score.py"}, "on_fail": {"retry_from": "tts", "max": 1}},
        {"id": "publish", "name": "Publish", "does": "Posts it.", "phase": "make", "kind": "code",
         "after": ["cut"], "tool": "claudeflow:pipelines/publish.py",
         "verify": {"check": "the post opens"}, "release": True},
    ],
}

STEPS = [("script", "Script"), ("approve", "Approve"), ("tts", "Voice"), ("cut", "Cut"), ("publish", "Publish")]


def _skill_md(steps=STEPS, start=0, extra="") -> str:
    lines = ["---", f"name: {NAME}", "kind: workflow", "owner: CMO",
             "description: WORKFLOW — demo. Trigger on /CMO_Workflow_Demo.", "---", "", "# Demo", "",
             "```", "### Step 9 · Inside a fence [node: nope]", "```", "", "## The steps", ""]
    for k, (nid, name) in enumerate(steps):
        lines += [f"### Step {start + k} · {name} [node: {nid}]", "Do: it.", ""]
    return "\n".join(lines) + extra + "\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    skills = tmp_path / ".claude" / "skills"
    for s in ("CMO_Standard_Demo", "CMO_Procedure_Demo"):
        (skills / s).mkdir(parents=True)
        (skills / s / "SKILL.md").write_text(f"---\nname: {s}\nkind: procedure\n---\n", encoding="utf-8")
    (skills / NAME).mkdir(parents=True)
    (skills / NAME / "SKILL.md").write_text(_skill_md(), encoding="utf-8")
    (tmp_path / "tools").mkdir()
    for t in ("tts.py", "compose.py", "score.py"):
        (tmp_path / "tools" / t).write_text("", encoding="utf-8")
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies" / "agents.yaml").write_text(
        "roles:\n  ceo: {model: null}\n  cmo: {model: x}\n  video_editor: {model: x}\n", encoding="utf-8")
    _write_flow(tmp_path, FLOW)
    return tmp_path


def _write_flow(repo: Path, flow: dict, name: str = NAME) -> None:
    (repo / ".claude" / "skills" / name / "flow.yaml").write_text(
        yaml.safe_dump(flow, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _run(repo: Path, **kw) -> list:
    return flow_lint.check(skills_dir=repo / ".claude" / "skills", repo_root=repo,
                           agents_yaml=repo / "policies" / "agents.yaml", **kw)


def _rules(findings) -> list[str]:
    return sorted({f.rule for f in findings})


def _with(mutate) -> dict:
    flow = copy.deepcopy(FLOW)
    mutate(flow)
    return flow


def _node(flow: dict, nid: str) -> dict:
    return next(n for n in flow["nodes"] if n["id"] == nid)


# --------------------------------------------------------------------------
# the valid fixture
# --------------------------------------------------------------------------

def test_valid_flow_is_clean(repo: Path) -> None:
    assert _run(repo) == []


def test_stub_and_non_workflow_skills_are_skipped(repo: Path) -> None:
    stub = repo / ".claude" / "skills" / "CTO_Old_Workflow"
    stub.mkdir()
    (stub / "SKILL.md").write_text(
        "---\nname: CTO_Old_Workflow\nkind: workflow\ndisable-model-invocation: true\n"
        "description: MOVED to X on 2026-09-27.\n---\n", encoding="utf-8")
    assert flow_lint.workflow_skills(repo / ".claude" / "skills") == [NAME]
    assert _run(repo) == []


# --------------------------------------------------------------------------
# one rule at a time
# --------------------------------------------------------------------------

def test_f1_missing_flow_yaml(repo: Path) -> None:
    (repo / ".claude" / "skills" / NAME / "flow.yaml").unlink()
    assert _rules(_run(repo)) == ["F1"]


def test_f1_skill_must_equal_folder(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: f.update(skill="CMO_Workflow_Other")))
    assert _rules(_run(repo)) == ["F1"]


def test_f2_schema_and_unknown_keys(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: (f.update(schema="v0", colour="red"),
                                       _node(f, "tts").update(tooll="x"),
                                       _node(f, "tts")["verify"].update(cmdd="y"))))
    msgs = [f.message for f in _run(repo)]
    assert _rules(_run(repo)) == ["F2"]
    assert any("colour" in m for m in msgs) and any("tooll" in m for m in msgs) and any("cmdd" in m for m in msgs)


def test_f3_flow_id_shape_and_uniqueness(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: f.update(flow="Demo-1")))
    assert _rules(_run(repo)) == ["F3"]
    _write_flow(repo, FLOW)
    twin = repo / ".claude" / "skills" / "CMO_Workflow_Twin"
    twin.mkdir()
    (twin / "SKILL.md").write_text(_skill_md().replace(NAME, "CMO_Workflow_Twin"), encoding="utf-8")
    _write_flow(repo, _with(lambda f: f.update(skill="CMO_Workflow_Twin")), "CMO_Workflow_Twin")
    found = _run(repo)
    assert _rules(found) == ["F3"] and {f.skill for f in found} == {NAME, "CMO_Workflow_Twin"}


def test_f4_duplicate_and_bad_ids(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: _node(f, "approve").update(replaces=["script"])))
    assert "F4" in _rules(_run(repo))


def test_f4_base_reports_a_vanished_id_unless_replaced(repo: Path) -> None:
    git = ["git", "-C", str(repo)]
    subprocess.run(git + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "."], check=True)
    subprocess.run(git + ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], check=True)

    def rename(f, replaces):
        n = _node(f, "tts")
        n["id"] = "voice"
        if replaces:
            n["replaces"] = ["tts"]
        _node(f, "cut")["after"] = ["voice"]
        _node(f, "cut")["on_fail"] = {"retry_from": "voice", "max": 1}
    _write_flow(repo, _with(lambda f: rename(f, False)))
    md = repo / ".claude" / "skills" / NAME / "SKILL.md"
    md.write_text(md.read_text(encoding="utf-8").replace("[node: tts]", "[node: voice]"), encoding="utf-8")
    assert _rules(_run(repo, base="HEAD")) == ["F4"]
    _write_flow(repo, _with(lambda f: rename(f, True)))
    assert _run(repo, base="HEAD") == []


def test_f5_unknown_after_cycle_no_release_dead_end(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: _node(f, "tts").update(after=["ghost"])))
    assert "F5" in _rules(_run(repo))
    _write_flow(repo, _with(lambda f: _node(f, "script").update(after=["cut"])))
    assert any("cycle" in x.message for x in _run(repo))
    _write_flow(repo, _with(lambda f: _node(f, "publish").pop("release")))
    assert any("release" in x.message for x in _run(repo))


def test_f5_dead_end_and_retry_from(repo: Path) -> None:
    def add_dead_end(f):
        f["nodes"].append({"id": "poster", "name": "Poster", "does": "Makes a poster.", "phase": "make",
                           "kind": "code", "after": ["approve"], "tool": "tools/tts.py",
                           "verify": {"check": "it exists"}})
    _write_flow(repo, _with(add_dead_end))
    md = repo / ".claude" / "skills" / NAME / "SKILL.md"
    md.write_text(_skill_md(STEPS + [("poster", "Poster")]), encoding="utf-8")
    assert any("dead end" in x.message for x in _run(repo))
    md.write_text(_skill_md(), encoding="utf-8")
    _write_flow(repo, _with(lambda f: _node(f, "tts").update(on_fail={"retry_from": "cut", "max": 1})))
    assert any("retry_from" in x.message for x in _run(repo))


def test_f6_kind_required_keys_phase_blockers_owner_watcher(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: (_node(f, "tts").pop("provider"), _node(f, "tts").update(phase="post"),
                                       _node(f, "tts").update(blockers=["meteor"]),
                                       f.update(owner="CTO", watcher="the CMO"))))
    msgs = [x.message for x in _run(repo) if x.rule == "F6"]
    assert len(msgs) == 5


def test_f7_verify_exactly_one(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: (_node(f, "tts").update(verify={"cmd": "a", "check": "b"}),
                                       _node(f, "cut").pop("verify"))))
    assert [x.rule for x in _run(repo)] == ["F7", "F7"]


def test_f8_paid_nodes_need_a_cash_budget(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: f.pop("budget")))
    assert _rules(_run(repo)) == ["F8"]


@pytest.mark.parametrize("trigger", [
    {"kind": "cron", "cron": "0 9 * * 1-5"},
    {"kind": "cron", "cron": "0 9 * *", "tz": "Asia/Bangkok"},
    {"kind": "manual"},
    {"kind": "queue"},
    {"kind": "hourly"},
])
def test_f9_trigger(repo: Path, trigger: dict) -> None:
    _write_flow(repo, _with(lambda f: f.update(trigger=trigger)))
    assert _rules(_run(repo)) == ["F9"]


def test_f10_stage_and_graduation(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: _node(f, "cut")["graduate"].pop("scorer")))
    assert _rules(_run(repo)) == ["F10"]
    _write_flow(repo, _with(lambda f: (_node(f, "cut").update(stage="auto"), _node(f, "tts").update(stage="shadow"))))
    assert [x.rule for x in _run(repo)] == ["F10", "F10"]


def test_f11_paths_skills_roles(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: (_node(f, "tts").update(tool="tools/missing.py"),
                                       _node(f, "script").update(skill="CMO_Nope", role="intern"),
                                       _node(f, "approve").update(approver="Boss"))))
    assert [x.rule for x in _run(repo)] == ["F11"] * 4


def test_f11_foreign_repo_path_is_not_checked(repo: Path) -> None:
    assert _node(FLOW, "publish")["tool"].startswith("claudeflow:")
    assert _run(repo) == []


def test_f12_binding(repo: Path) -> None:
    md = repo / ".claude" / "skills" / NAME / "SKILL.md"
    swapped = [STEPS[0], STEPS[2], STEPS[1], STEPS[3], STEPS[4]]
    md.write_text(_skill_md(swapped), encoding="utf-8")
    assert any("waits on" in x.message for x in _run(repo))
    md.write_text(_skill_md(STEPS[:4]) + "### Step 5 · Publish\n", encoding="utf-8")
    msgs = [x.message for x in _run(repo)]
    assert any("no `[node: <id>]`" in m for m in msgs) and any("node publish has no" in m for m in msgs)
    md.write_text(_skill_md([("script", "Script"), ("approve", "OK"), *STEPS[2:]]), encoding="utf-8")
    assert any("heading name" in x.message for x in _run(repo))
    md.write_text(_skill_md().replace("### Step 3 ·", "### Step 7 ·"), encoding="utf-8")
    assert any("count up by one" in x.message for x in _run(repo))


def test_f12_numbering_may_start_at_one(repo: Path) -> None:
    (repo / ".claude" / "skills" / NAME / "SKILL.md").write_text(_skill_md(start=1), encoding="utf-8")
    assert _run(repo) == []


def test_f13_sizes(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: (f.update(name="x" * 41), _node(f, "cut").update(does="x" * 121))))
    assert [x.rule for x in _run(repo)] == ["F13", "F13"]
    long_name = "A very long node name indeed"
    _write_flow(repo, _with(lambda f: _node(f, "tts").update(name=long_name)))
    md = repo / ".claude" / "skills" / NAME / "SKILL.md"
    md.write_text(_skill_md().replace("· Voice [", f"· {long_name} ["), encoding="utf-8")
    assert [x.rule for x in _run(repo)] == ["F13"]


def test_f14_money_source_and_secrets(repo: Path) -> None:
    _write_flow(repo, _with(lambda f: (_node(f, "tts")["unit_cost"].pop("source"),
                                       _node(f, "publish").update(gate="api_key=abcd1234efgh5678"))))
    assert [x.rule for x in _run(repo)] == ["F14", "F14"]


# --------------------------------------------------------------------------
# export -- the board's numbers (references/workflow-flow.md §9)
# --------------------------------------------------------------------------

def test_export_computes_depth_stage_and_stats(repo: Path) -> None:
    out = flow_lint.export(NAME, repo / ".claude" / "skills")
    by = {n["id"]: n for n in out["nodes"]}
    assert [n["id"] for n in out["nodes"]] == ["script", "approve", "tts", "cut", "publish"]
    assert [by[i]["depth"] for i in ("script", "approve", "tts", "cut", "publish")] == [0, 1, 2, 3, 4]
    assert by["tts"]["effective_stage"] == "auto" and by["approve"]["effective_stage"] == "human"
    assert by["cut"]["effective_stage"] == "shadow"
    s = out["stats"]
    assert s["auto_pct_steps"] == 50.0           # tts, publish auto of script, tts, cut, publish
    assert s["cost_per_run_usd"] == 3.04
    assert s["auto_pct_cost"] == round(100 * 0.04 / 3.04, 1)
    assert s["cost_unknown"] == ["cut", "publish"]
    assert ["approve", "tts"] in out["edges"]


def test_cli_check_exit_codes(repo: Path) -> None:
    skills = str(repo / ".claude" / "skills")
    assert flow_lint.main(["check", "--skills-dir", skills]) in (0, 1)  # real agents.yaml: roles may differ
    assert flow_lint.main(["check", "CMO_Workflow_Nope", "--skills-dir", skills]) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
