"""Path owners: lib/path_owners.py, tools/pr_owner_check.py, and the PH branch of check_collisions.

CEO 2026-10-14: each Project Head merges its own project's paths; a PR that touches another PH's paths
is a conflict for CTO Main. config/path-owners.yaml is the map; these tests pin the lookup rules, the
CLI's exit codes, the seeded map against the real PR 327, and that every caller of check_collisions
that is not a Project Head still gets the bare list it always did.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.org_tools_registry as reg  # noqa: E402
import tools.pr_owner_check as cli  # noqa: E402
from lib import path_owners as po  # noqa: E402
from lib import toon  # noqa: E402

TABLE = [
    ("tools/*", "Alpha"),
    ("tools/spend*", "SpendGuard"),
    ("tools/spend_guard.py", "SpendGuard"),
    ("tools/spend_guard_tests/**", "Beta"),
    ("roles/**", po.SHARED),
    ("roles/alpha.md", "Alpha"),
    ("docs/*", "Beta"),
]

# The 15 files of PR 327 (OrgRestructure's own PR: "hosts: terminal_window flag per host, Mac = off").
PR_327 = [
    ".claude/skills/terminal-open/SKILL.md", "config/hosts.yaml", "lib/config.py",
    "scripts/cto-claude.sh", "scripts/cxo-claude.sh", "scripts/lib/coo_host.py",
    "scripts/spawn-cto.sh", "scripts/spawn-cxo.sh", "scripts/tab-title.sh",
    "tests/test_delegate_disk_floor.py", "tests/test_delegate_workdir.py",
    "tests/test_reopen_live_worker.py", "tests/test_terminal_window.py",
    "tests/test_w03_self_host_spawn.py", "tools/delegate.py",
]


# --- owners_for ----------------------------------------------------------------------------------

def test_longest_glob_wins_over_a_broader_one():
    got = po.owners_for(["tools/spend_guard.py", "tools/other.py", "tools/spend_x.py"], TABLE)
    assert got == {"tools/spend_guard.py": "SpendGuard", "tools/other.py": "Alpha",
                   "tools/spend_x.py": "SpendGuard"}


def test_longest_glob_wins_whatever_the_file_order():
    # the narrow glob is listed BEFORE the broad one: order must not decide
    tbl = [("a/b/c.py", "Narrow"), ("a/*", "Broad")]
    assert po.owners_for(["a/b/c.py", "a/b/d.py"], tbl) == {"a/b/c.py": "Narrow", "a/b/d.py": "Broad"}


def test_equal_length_globs_go_to_the_first_listed():
    tbl = [("x/*.py", "First"), ("x/a.p?", "Second")]
    assert len("x/*.py") == len("x/a.p?")
    assert po.owners_for(["x/a.py"], tbl) == {"x/a.py": "First"}
    assert po.owners_for(["x/a.py"], tbl[::-1]) == {"x/a.py": "Second"}


def test_a_narrow_project_glob_beats_a_broad_shared_one_and_the_reverse():
    got = po.owners_for(["roles/cto.md", "roles/alpha.md"], TABLE)
    assert got == {"roles/cto.md": po.SHARED, "roles/alpha.md": "Alpha"}


def test_shared_paths_are_reported_as_shared():
    assert po.owners_for(["roles/project_head.md"], TABLE) == {"roles/project_head.md": "shared"}


def test_an_unknown_path_is_none():
    assert po.owners_for(["nothing/here.txt", "README.md"], TABLE) == {"nothing/here.txt": None,
                                                                       "README.md": None}


def test_star_crosses_slashes_so_dir_globs_cover_the_whole_tree():
    assert po.owners_for(["docs/a/b/c.md"], TABLE) == {"docs/a/b/c.md": "Beta"}


def test_paths_are_normalised_but_keyed_as_given():
    got = po.owners_for(["./tools/spend_guard.py", "/tools/spend_guard.py", "tools\\spend_guard.py"], TABLE)
    assert got == {"./tools/spend_guard.py": "SpendGuard", "/tools/spend_guard.py": "SpendGuard",
                   "tools\\spend_guard.py": "SpendGuard"}


# --- foreign_paths -------------------------------------------------------------------------------

def test_foreign_paths_lists_only_what_another_project_owns():
    paths = ["tools/spend_guard.py", "tools/other.py", "roles/cto.md", "README.md", "docs/x.md"]
    assert po.foreign_paths("Alpha", paths, TABLE) == [("tools/spend_guard.py", "SpendGuard"),
                                                       ("docs/x.md", "Beta")]


def test_a_project_never_sees_its_own_paths_as_foreign_ignoring_case():
    assert po.foreign_paths("spendguard", ["tools/spend_guard.py"], TABLE) == []


def test_shared_and_unowned_are_not_foreign():
    assert po.foreign_paths("Alpha", ["roles/cto.md", "nothing.txt"], TABLE) == []


def test_a_project_with_no_entry_sees_every_owned_path_as_foreign():
    assert po.foreign_paths("CooGate", ["tools/other.py", "roles/cto.md"], TABLE) == [("tools/other.py", "Alpha")]


def test_a_path_given_twice_is_listed_once():
    assert po.foreign_paths("Beta", ["tools/other.py", "tools/other.py"], TABLE) == [("tools/other.py", "Alpha")]


# --- load_table ----------------------------------------------------------------------------------

def test_load_table_reads_projects_and_shared_in_file_order(tmp_path):
    f = tmp_path / "o.yaml"
    f.write_text("A:\n  - a/*\nshared:\n  - s/*  # comment\nB:\n  - ./b/x\n", encoding="utf-8")
    tbl = po.load_table(f)
    assert tbl == [("a/*", "A"), ("s/*", "shared"), ("b/x", "B")]
    assert po.projects(tbl) == ["A", "B"]


@pytest.mark.parametrize("text", ["- a\n- b\n", "A: not-a-list\n", "A:\n  - 5\n", "A:\n  - ''\n"])
def test_load_table_rejects_a_malformed_file(tmp_path, text):
    f = tmp_path / "o.yaml"
    f.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        po.load_table(f)


# --- the seeded map ------------------------------------------------------------------------------

def test_the_seeded_map_has_the_five_projects_and_shared():
    tbl = po.load_table()
    assert set(po.projects(tbl)) == {"OrgRestructure", "SpendGuard", "CookieRun", "BlackLiquidity", "MimiPage"}
    assert any(o == po.SHARED for _, o in tbl)


def test_no_glob_is_listed_twice_in_the_seeded_map():
    globs = [g for g, _ in po.load_table()]
    assert len(globs) == len(set(globs)), sorted({g for g in globs if globs.count(g) > 1})


@pytest.mark.parametrize("path,owner", [
    ("tools/spend_guard.py", "SpendGuard"),
    ("deploy/spend-guard/unit.service", "SpendGuard"),
    ("tools/rename_service.py", "OrgRestructure"),
    ("lib/session_names.py", "OrgRestructure"),
    ("windows/cookierun_probe.py", "CookieRun"),
    ("prototypes/bl61-script/SCRIPT.tsv", "BlackLiquidity"),
    (".claude/skills/CMO_Procedure_BlackLiquidity_Cut/SKILL.md", "BlackLiquidity"),
    (".claude/skills/CMO_Workflow_MimiPage_Weekly/SKILL.md", "MimiPage"),
    ("config/hosts.yaml", "shared"),
    ("tools/delegate.py", "shared"),
    ("runners/watchdog.py", "shared"),
    ("scripts/cto-claude.sh", "shared"),
    ("tests/test_terminal_window.py", "OrgRestructure"),
    ("lib/config.py", "shared"),
    ("roles/project_head.md", "shared"),
    (".claude/settings.json", "shared"),
    ("README.md", None),
])
def test_the_seeded_map_resolves_the_briefs_examples(path, owner):
    assert po.owners_for([path]) == {path: owner}


# --- the CLI -------------------------------------------------------------------------------------

def _run(argv, capsys, runner=None):
    code = cli.main(argv, **({"runner": runner} if runner else {}))
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def test_cli_files_clean_exits_0(capsys):
    code, out, err = _run(["--files", "tools/spend_guard.py,tests/test_spend_guard.py,README.md",
                           "--project", "SpendGuard"], capsys)
    assert (code, out) == (0, "")
    assert "0 foreign, 0 shared" in err      # a clean run still says so, on stderr


def test_cli_files_with_a_foreign_path_exits_1_and_names_the_owner(capsys):
    code, out, _ = _run(["--files", "tools/spend_guard.py,tools/rename_service.py",
                         "--project", "SpendGuard"], capsys)
    assert code == 1
    assert out.splitlines() == ["FOREIGN  tools/rename_service.py  owned by OrgRestructure"]


def test_cli_shared_path_is_printed_but_exits_0(capsys):
    code, out, _ = _run(["--files", "config/hosts.yaml,tools/spend_guard.py", "--project", "SpendGuard"], capsys)
    assert code == 0
    assert out.splitlines() == ["SHARED   config/hosts.yaml  shared, tell CTO Main"]


def test_cli_foreign_and_shared_together_print_both_and_exit_1(capsys):
    code, out, _ = _run(["--files", "config/hosts.yaml,windows/cookierun_probe.py", "--project", "MimiPage"], capsys)
    assert code == 1
    assert out.splitlines() == ["FOREIGN  windows/cookierun_probe.py  owned by CookieRun",
                                "SHARED   config/hosts.yaml  shared, tell CTO Main"]


def test_cli_project_name_is_case_insensitive(capsys):
    code, out, _ = _run(["--files", "tools/spend_guard.py", "--project", "spendguard"], capsys)
    assert (code, out) == (0, "")


def test_cli_unknown_project_notes_it_on_stderr_and_still_reports(capsys):
    code, out, err = _run(["--files", "tools/spend_guard.py", "--project", "CooGate"], capsys)
    assert code == 1 and "owned by SpendGuard" in out
    assert "owns no paths" in err


@pytest.mark.parametrize("argv", [
    ["--project", "SpendGuard"],                                    # neither a PR nor files
    ["327", "--files", "a.py", "--project", "SpendGuard"],          # both
    ["--files", "a.py"],                                            # no project
    ["--files", "--repo=evil", "--project", "X"],                   # a flag as the file list
    ["--repo=evil/x", "--project", "SpendGuard"],                   # no PR, no files
    ["-1", "--project", "SpendGuard"],                              # not a number
    ["abc", "--project", "SpendGuard"],
])
def test_cli_bad_arguments_exit_2(argv, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(argv)
    assert e.value.code == 2


def test_cli_pr_number_cannot_smuggle_a_flag_into_gh(capsys):
    called = []
    with pytest.raises(SystemExit) as e:
        cli.main(["--repo", "x/y", "--project", "P", "--", "--web"], runner=lambda *a, **k: called.append(a))
    assert e.value.code == 2 and called == []


def _gh_runner(view_files, api_lines=None, fail=False):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        if fail:
            return SimpleNamespace(returncode=1, stdout="", stderr="HTTP 404: Not Found")
        if cmd[1] == "pr":
            return SimpleNamespace(returncode=0, stdout=json.dumps({"files": [{"path": p} for p in view_files]}),
                                   stderr="")
        return SimpleNamespace(returncode=0, stdout="\n".join(api_lines or []) + "\n", stderr="")
    run.calls = calls
    return run


LAUNCHERS_327 = ["scripts/cto-claude.sh", "scripts/cxo-claude.sh", "scripts/spawn-cto.sh",
                 "scripts/spawn-cxo.sh", "scripts/tab-title.sh"]


def _shared_lines(*paths):
    return [f"SHARED   {p}  shared, tell CTO Main" for p in paths]


def test_cli_pr_327_for_org_restructure_has_no_foreign_path_and_the_launchers_are_shared(capsys):
    run = _gh_runner(PR_327)
    code, out, err = _run(["327", "--project", "OrgRestructure"], capsys, run)
    assert code == 0, out
    assert not [ln for ln in out.splitlines() if ln.startswith("FOREIGN")]
    assert out.splitlines() == _shared_lines("config/hosts.yaml", "lib/config.py", *LAUNCHERS_327,
                                             "tools/delegate.py")
    assert run.calls == [["gh", "pr", "view", "327", "--repo", "PASAKON/Agents-Core", "--json", "files"]]
    assert "15 path(s), 0 foreign, 8 shared" in err


def test_cli_pr_327_for_another_project_flags_only_the_terminal_window_test(capsys):
    code, out, _ = _run(["#327", "--project", "SpendGuard"], capsys, _gh_runner(PR_327))
    assert code == 1
    assert out.splitlines() == (["FOREIGN  tests/test_terminal_window.py  owned by OrgRestructure"]
                                + _shared_lines("config/hosts.yaml", "lib/config.py", *LAUNCHERS_327,
                                                "tools/delegate.py"))


def test_cli_pr_with_100_files_is_re_read_through_the_paginated_api(capsys):
    first_100 = [f"docs/plans/spend-guard-{i}.md" for i in range(100)]
    full = first_100 + ["tools/rename_service.py"]      # file 101 only the API shows
    run = _gh_runner(first_100, api_lines=full)
    code, out, _ = _run(["286", "--project", "SpendGuard"], capsys, run)
    assert code == 1 and "FOREIGN  tools/rename_service.py  owned by OrgRestructure" in out
    assert run.calls[1][:3] == ["gh", "api", "--paginate"]
    assert "repos/PASAKON/Agents-Core/pulls/286/files" in run.calls[1][3]


def test_cli_gh_failure_exits_2_never_clean(capsys):
    code, out, err = _run(["999999", "--project", "SpendGuard"], capsys, _gh_runner([], fail=True))
    assert (code, out) == (2, "")
    assert "cannot check" in err and "404" in err


def test_cli_empty_file_list_exits_2(capsys):
    code, _, err = _run(["12", "--project", "SpendGuard"], capsys, _gh_runner([]))
    assert code == 2 and "no files" in err


def test_cli_unreadable_owners_file_exits_2(capsys, tmp_path, monkeypatch):
    bad = tmp_path / "o.yaml"
    bad.write_text("A: [unclosed\n", encoding="utf-8")
    monkeypatch.setattr(po, "OWNERS_CONFIG", bad)
    code, out, err = _run(["--files", "tools/spend_guard.py", "--project", "SpendGuard"], capsys)
    assert (code, out) == (2, "") and "cannot check" in err


# --- check_collisions ----------------------------------------------------------------------------

HIT = {"task_id": "task-1", "role": "developer", "status": "in_progress", "title": "t",
       "overlap": ["tools/spend_guard.py"]}


@pytest.fixture()
def collisions(monkeypatch):
    monkeypatch.delenv("ORG_PH_PROJECT", raising=False)
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setattr(reg.db, "find_conflicts", lambda project, paths: [dict(HIT)])


def test_check_collisions_without_a_ph_project_returns_the_old_bare_list(collisions):
    got = reg._h_check_collisions(project="mooniex-agents", touches='["tools/spend_guard.py"]')
    assert got == [HIT]                       # a list of the same dicts: the old fields, the old shape
    assert reg.dispatch_sync("check_collisions", project="mooniex-agents",
                             touches="tools/spend_guard.py") == toon.encode([HIT])


def test_check_collisions_empty_list_still_means_safe_for_a_non_ph(collisions, monkeypatch):
    monkeypatch.setattr(reg.db, "find_conflicts", lambda project, paths: [])
    assert reg._h_check_collisions(project="p", touches="tools/rename_service.py") == []


def test_check_collisions_for_a_ph_adds_path_owner_and_keeps_the_conflicts(collisions, monkeypatch):
    monkeypatch.setenv("ORG_PH_PROJECT", "OrgRestructure")
    got = reg._h_check_collisions(
        project="mooniex-agents",
        touches='["tools/spend_guard.py", "tools/rename_service.py", "config/hosts.yaml", "README.md"]')
    assert got["conflicts"] == [HIT]
    assert got["path_owner"] == [{"path": "tools/spend_guard.py", "owner": "SpendGuard"},
                                 {"path": "config/hosts.yaml", "owner": "shared"}]
    assert "path_owner_error" not in got


def test_check_collisions_for_a_ph_with_only_its_own_paths_has_an_empty_path_owner(collisions, monkeypatch):
    monkeypatch.setenv("ORG_PH_PROJECT", "OrgRestructure")
    got = reg._h_check_collisions(project="p", touches="tools/rename_service.py,README.md")
    assert got["path_owner"] == []


def test_check_collisions_ph_path_goes_through_the_registry_for_a_project_head(collisions, monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("ORG_PH_PROJECT", "SpendGuard")
    out = reg.dispatch_sync("check_collisions", project="p", touches="tools/rename_service.py")
    assert "OrgRestructure" in out and "path_owner" in out and "task-1" in out


def test_a_bad_owners_file_does_not_hide_the_conflicts(collisions, monkeypatch, tmp_path):
    bad = tmp_path / "o.yaml"
    bad.write_text("- just a list\n", encoding="utf-8")
    monkeypatch.setattr(po, "OWNERS_CONFIG", bad)
    monkeypatch.setenv("ORG_PH_PROJECT", "SpendGuard")
    got = reg._h_check_collisions(project="p", touches="tools/spend_guard.py")
    assert got["conflicts"] == [HIT] and got["path_owner"] == []
    assert got["path_owner_error"].startswith("ValueError")
