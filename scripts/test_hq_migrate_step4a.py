"""Tests for scripts/hq_migrate_step4a.py (HQ migration step 4a, ADR 0028).

Every test runs against a fake HQ_ROOT / Projects dir / state dir / memory
symlink under tmp_path via env-var overrides (HQ_ROOT, HQ_STEP4A_STATE_DIR,
HQ_STEP4A_EXTERNAL_DIR, HQ_STEP4A_MEMORY_LINK, HQ_STEP4A_REPO_ROOT, HQ_PYTHON)
— never touches the real ~/MoonieXHQ, ~/Projects or ~/.claude. The fixture
builds real git repos with real bare "origin" remotes (preflight/push are
real git, not mocks) and a real fake-GitHub bare remote for mooniex-nohuman
so verify_nohuman_brand does a real `git clone --depth 1`, not a mock.

Run: .venv/bin/python -m pytest scripts/test_hq_migrate_step4a.py -q
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "hq_migrate_step4a.py"
sys.path.insert(0, str(ROOT / "scripts"))
import hq_migrate_step4a as mod  # noqa: E402  (pure-function unit tests use this directly)

REAL_HQ_PY = Path("/Users/gob/MoonieXHQ/scripts/hq.py")

GIT_ENV_EXTRA = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    r = subprocess.run(["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} in {cwd} failed: {r.stdout}{r.stderr}"
    return r


def _make_repo_with_origin(base: Path, name: str, origins_dir: Path, files: dict[str, str] | None = None) -> tuple[Path, Path]:
    origin = origins_dir / f"{name}-origin.git"
    origin.mkdir(parents=True)
    _git(["init", "--bare", "-b", "main"], origin)
    repo = base / name
    repo.mkdir(parents=True)
    _git(["init", "-b", "main"], repo)
    (repo / "README.md").write_text(f"{name}\n")
    for rel, content in (files or {}).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)
    _git(["remote", "add", "origin", str(origin)], repo)
    _git(["push", "-u", "origin", "main"], repo)
    return repo, origin


def _head(repo: Path) -> str:
    return _git(["rev-parse", "HEAD"], repo).stdout.strip()


def _build_fixture(tmp: Path) -> dict:
    """4 step-4 rows (Agents/Rules, Agents/Wikis, Agents/Memory, Agents/Skills)
    + a step-4 Agents/Core row that must NEVER be touched; an External row
    with 2 git clones + 1 non-git clone (arb-refs) + paperclip; an Archive
    NoHumanCompany item with a brand/ dir matching its own origin; an UNKNOWN
    mooniex-school item (plain files, no git); a `.claude/skills`-style
    symlink pointing INTO an external clone; a memory-style symlink pointing
    at the Agents/Memory row's old path."""
    hq = tmp / "hq"
    (hq / "scripts").mkdir(parents=True)
    if REAL_HQ_PY.exists():
        shutil.copy2(REAL_HQ_PY, hq / "scripts" / "hq.py")
    origins_dir = tmp / "origins"
    projects = tmp / "Projects"
    projects.mkdir()

    rules, _ = _make_repo_with_origin(projects, "Agents-Wikis", origins_dir)
    wikis, _ = _make_repo_with_origin(projects, "LLMs", origins_dir)
    memory, _ = _make_repo_with_origin(projects, "Agents-Memory", origins_dir)
    skills, _ = _make_repo_with_origin(projects, "mooniex-claude-skills", origins_dir)
    core, _ = _make_repo_with_origin(projects, "Agents", origins_dir)  # step 4 too — must stay put

    external = projects / "external"
    external.mkdir()
    clone_a, _ = _make_repo_with_origin(external, "wondelai-skills", origins_dir)
    (clone_a / "obviously-awesome").mkdir()
    (clone_a / "obviously-awesome" / "SKILL.md").write_text("skill\n")
    _git(["add", "-A"], clone_a)
    _git(["commit", "-m", "add skill"], clone_a)
    clone_b, _ = _make_repo_with_origin(external, "diagram-design", origins_dir)
    arb_refs = external / "arb-refs"  # no .git — matches the real fixture (no remote)
    arb_refs.mkdir()
    (arb_refs / "notes.txt").write_text("no origin\n")

    skills_link = tmp / "claude-skills-link"  # stands in for ~/.claude/skills/obviously-awesome
    os.symlink(str(clone_a / "obviously-awesome"), str(skills_link))

    nohuman = projects / "mooniex-nohuman"
    nohuman.mkdir()
    _git(["init", "-b", "main"], nohuman)
    (nohuman / "brand").mkdir()
    (nohuman / "brand" / "logo.svg").write_text("<svg>logo</svg>\n")
    (nohuman / "paperclip").mkdir()
    _git(["init", "-b", "main"], nohuman / "paperclip")
    (nohuman / "paperclip" / "README.md").write_text("paperclip\n")
    _git(["add", "-A"], nohuman / "paperclip")
    _git(["commit", "-m", "init"], nohuman / "paperclip")
    (nohuman / ".gitignore").write_text("paperclip/\n")
    _git(["add", "-A"], nohuman)
    _git(["commit", "-m", "brand assets"], nohuman)
    nohuman_origin = origins_dir / "nohuman-origin.git"
    nohuman_origin.mkdir(parents=True)
    _git(["init", "--bare", "-b", "main"], nohuman_origin)
    _git(["remote", "add", "origin", str(nohuman_origin)], nohuman)
    _git(["push", "-u", "origin", "main"], nohuman)

    school = projects / "mooniex-school"
    school.mkdir()
    (school / "sample.pdf").write_text("pdf bytes\n")

    memory_link = tmp / "claude-memory-link"  # stands in for ~/.claude/projects/.../memory
    os.symlink(str(memory), str(memory_link))

    hq_yaml_text = f"""version: 1
root: {hq}
repo: TEST/hq
folders:
  - path: Agents
    kind: group
    owner: CTO
  - path: Agents/Rules
    kind: own
    owner: CTO
    current: {rules}
    step: 4
  - path: Agents/Wikis
    kind: own
    owner: CTO
    current: {wikis}
    step: 4
  - path: Agents/Memory
    kind: own
    owner: CTO
    current: {memory}
    step: 4
  - path: Agents/Skills
    kind: own
    owner: CTO
    current: {skills}
    step: 4
  - path: Agents/Core
    kind: own
    owner: CTO
    current: {core}
    step: 4
  - path: External
    kind: group
    owner: CTO
    items:
      - {{name: wondelai-skills, repo: wondelai/skills, current: {clone_a}}}
      - {{name: diagram-design, repo: cathrynlavery/diagram-design, current: {clone_b}}}
      - {{name: arb-refs, repo: null, current: {arb_refs}}}
      - {{name: paperclip, repo: paperclipai/paperclip, current: {nohuman / "paperclip"}}}
  - path: Archive
    kind: archive
    owner: CTO
    items:
      - {{name: NoHumanCompany, repo: TEST/nohuman, current: {nohuman}, action: delete local at step 2 (brand/ is on GitHub), status: retired}}
  - path: UNKNOWN
    kind: unknown
    owner: CEO
    items:
      - {{name: mooniex-school, current: {school}, note: 3 PDF/PPTX, not a repo}}
"""
    (hq / "hq.yaml").write_text(hq_yaml_text)

    return {
        "hq": hq, "rules": rules, "wikis": wikis, "memory": memory, "skills": skills, "core": core,
        "external": external, "clone_a": clone_a, "clone_b": clone_b, "arb_refs": arb_refs,
        "nohuman": nohuman, "nohuman_origin": nohuman_origin, "paperclip": nohuman / "paperclip",
        "school": school, "skills_link": skills_link, "memory_link": memory_link,
        "projects": projects,
    }


def _run_cli(tmp: Path, f: dict, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(GIT_ENV_EXTRA)
    env.update({
        "HQ_ROOT": str(f["hq"]),
        "HQ_STEP4A_STATE_DIR": str(tmp / "state"),
        "HQ_STEP4A_EXTERNAL_DIR": str(f["external"]),
        "HQ_STEP4A_MEMORY_LINK": str(f["memory_link"]),
        "HQ_STEP4A_REPO_ROOT": str(ROOT),
        "HQ_PYTHON": sys.executable,
    })
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True)


def _manifest(tmp: Path) -> dict:
    files = sorted((tmp / "state").glob("hq-step4a-migration-*.json"))
    assert files, "no manifest written"
    return json.loads(files[-1].read_text())


# ─────────────────────────── plan ────────────────────────────────────────────

def test_plan_changes_nothing(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    r = _run_cli(tmp_path, f, "--plan")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MOVE" in r.stdout and str(f["rules"]) in r.stdout
    assert f"{f['core']}  ->" not in r.stdout  # Agents/Core is never in scope (its path is a
    # prefix of Agents-Wikis' path, so a bare substring check would false-positive on that line)
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    assert not (tmp_path / "state").exists() or not list((tmp_path / "state").glob("*.json"))


# ─────────────────────────── full apply ──────────────────────────────────────

def test_apply_moves_the_four_repos_and_verifies_sha(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    rules_sha = _head(f["rules"])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Agents" / "Rules"
    assert target.is_dir()
    assert f["rules"].is_symlink()
    assert _head(target) == rules_sha
    # Agents/Core never moves
    assert f["core"].is_dir() and not f["core"].is_symlink()
    assert (f["hq"] / "Agents" / "Core").exists() is False


def test_apply_moves_external_clones_then_one_parent_symlink(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (f["hq"] / "External" / "wondelai-skills").is_dir()
    assert (f["hq"] / "External" / "diagram-design").is_dir()
    assert (f["hq"] / "External" / "arb-refs").is_dir()
    assert (f["hq"] / "External" / "arb-refs" / "notes.txt").read_text() == "no origin\n"
    # the shared parent got exactly ONE compat symlink, not one per clone
    assert f["external"].is_symlink()
    assert Path(os.readlink(f["external"])) == f["hq"] / "External"


def test_symlink_into_moved_external_clone_still_resolves(tmp_path: Path) -> None:
    """Stands in for a `~/.claude/skills/*` link: it still points at the OLD
    literal path, but resolves correctly once the parent (`external`) is a
    compat symlink (hq-filing field note, 2026-09-23)."""
    f = _build_fixture(tmp_path)
    content_before = (f["skills_link"] / "SKILL.md").read_text()
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f["skills_link"].is_symlink()
    assert os.readlink(f["skills_link"]) == str(f["clone_a"] / "obviously-awesome")  # unchanged
    assert (f["skills_link"] / "SKILL.md").read_text() == content_before  # still readable


def test_apply_moves_paperclip_out_before_trashing_nohuman(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (f["hq"] / "External" / "paperclip" / "README.md").read_text() == "paperclip\n"
    assert not f["paperclip"].exists()


def test_apply_trashes_nohuman_when_brand_matches_origin(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not f["nohuman"].exists()
    m = _manifest(tmp_path)
    trash_ops = [o for o in m["ops"] if o["op"] == "trash"]
    assert trash_ops and Path(trash_ops[0]["to"]).is_dir()
    assert (Path(trash_ops[0]["to"]) / "brand" / "logo.svg").exists()
    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    for r_ in data["folders"]:
        if r_["path"] == "Archive":
            nh = r_["items"][0]
            assert nh["current"] is None
            assert "trashed" in nh["action"]


def test_apply_refuses_to_trash_nohuman_when_brand_differs(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    (f["nohuman"] / "brand" / "logo.svg").write_text("<svg>TAMPERED locally, never pushed</svg>\n")
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr  # rest of the migration still succeeds
    assert f["nohuman"].exists()  # NOT trashed
    assert (f["nohuman"] / "brand" / "logo.svg").exists()
    m = _manifest(tmp_path)
    assert any("BLOCKER" in n and "brand/" in n for n in m["notes"])
    assert "differs from origin HEAD" in r.stdout or any("differs from origin HEAD" in n for n in m["notes"])
    # everything else still moved
    assert (f["hq"] / "Agents" / "Rules").is_dir()


def test_apply_moves_mooniex_school_to_unknown(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "UNKNOWN" / "mooniex-school"
    assert (target / "sample.pdf").is_file()
    assert not f["school"].exists()
    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    for r_ in data["folders"]:
        if r_["path"] == "UNKNOWN":
            assert r_["items"][0]["current"] == str(target)


def test_apply_repoints_memory_symlink(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f["memory_link"].is_symlink()
    assert Path(os.readlink(f["memory_link"])) == f["hq"] / "Agents" / "Memory"


def test_apply_creates_compat_symlinks_and_updates_yaml(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    target = f["hq"] / "Agents" / "Rules"
    assert f["rules"].is_symlink()
    assert os.readlink(f["rules"]) == str(target)

    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    rows = {row["path"]: row for row in data["folders"]}
    assert rows["Agents/Rules"]["current"] == str(target)
    links = {c["path"]: c for c in data["compat_links"]}
    assert links[str(f["rules"])]["target"] == str(target)
    assert links[str(f["rules"])]["remove_at_step"] == 5  # this task's instruction, not step2/3's 4
    assert links[str(f["external"])]["target"] == str(f["hq"] / "External")


# ─────────────────────────── stop-before-any-move ────────────────────────────

def test_apply_stops_before_any_move_when_push_fails(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    (f["rules"] / "extra.txt").write_text("more\n")
    _git(["add", "-A"], f["rules"])
    _git(["commit", "-m", "extra"], f["rules"])
    # break the only remote so the ahead-branch push fails
    _git(["remote", "set-url", "origin", "/no/such/path.git"], f["rules"])
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "STOP" in r.stdout
    assert f["rules"].is_dir() and not f["rules"].is_symlink()
    assert not (f["hq"] / "Agents" / "Rules").exists()
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before


# ─────────────────────────── resumability ────────────────────────────────────

def test_apply_resumes_after_a_row_already_migrated(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    rules_sha = _head(f["rules"])
    target_rules = f["hq"] / "Agents" / "Rules"
    target_rules.parent.mkdir(parents=True)
    shutil.move(str(f["rules"]), str(target_rules))
    os.symlink(str(target_rules), str(f["rules"]))  # simulate a prior completed row

    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already migrated" in r.stdout

    assert f["rules"].is_symlink() and os.readlink(f["rules"]) == str(target_rules)
    assert _head(target_rules) == rules_sha
    # the other rows still moved normally in this same run
    assert (f["hq"] / "Agents" / "Wikis").is_dir()
    data = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    rows = {row["path"]: row for row in data["folders"]}
    assert rows["Agents/Rules"]["current"] == str(target_rules)


def test_apply_resumes_after_external_clone_already_migrated(tmp_path: Path) -> None:
    """Real incident shape (2026-09-23, task-b5f61b47): --apply crashes after
    moving some but not all external clones. A re-run must not re-move the
    done ones nor error on them, and must still finish the rest + symlink."""
    f = _build_fixture(tmp_path)
    target_a = f["hq"] / "External" / "wondelai-skills"
    target_a.parent.mkdir(parents=True)
    shutil.move(str(f["clone_a"]), str(target_a))
    # no symlink left at the old per-clone path — matches what move_verified()
    # itself does (only the SHARED parent `external/` gets a symlink, once
    # every clone has moved and it is empty)

    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "external clone already migrated" in r.stdout
    assert (f["hq"] / "External" / "diagram-design").is_dir()  # the other clone still moved
    assert f["external"].is_symlink()  # the parent symlink still got created this run


def test_apply_is_a_full_noop_on_second_run(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    r1 = _run_cli(tmp_path, f, "--apply")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    yaml_after_first = (f["hq"] / "hq.yaml").read_text()
    r2 = _run_cli(tmp_path, f, "--apply")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "already migrated" in r2.stdout
    # nohuman's `current` is null after a completed trash — nothing left to
    # check or report for it, which is itself part of the noop invariant
    data2 = yaml.safe_load((f["hq"] / "hq.yaml").read_text())
    data1 = yaml.safe_load(yaml_after_first)
    assert data1["folders"] == data2["folders"]


# ─────────────────────────── rollback ────────────────────────────────────────

def test_rollback_restores_dirs_symlinks_and_yaml_byte_for_byte(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    before_rules_sha = _head(f["rules"])
    yaml_before = (f["hq"] / "hq.yaml").read_text()
    r = _run_cli(tmp_path, f, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest_path = sorted((tmp_path / "state").glob("hq-step4a-migration-*.json"))[-1]

    rb = _run_cli(tmp_path, f, "--rollback", str(manifest_path))
    assert rb.returncode == 0, rb.stdout + rb.stderr

    assert not f["rules"].is_symlink() and f["rules"].is_dir()
    assert _head(f["rules"]) == before_rules_sha
    assert not f["external"].is_symlink() and f["external"].is_dir()
    assert (f["external"] / "wondelai-skills").is_dir()
    assert f["nohuman"].exists()  # trash restored
    assert (f["nohuman"] / "brand" / "logo.svg").exists()
    assert f["school"].exists()
    assert (f["hq"] / "hq.yaml").read_text() == yaml_before
    assert Path(os.readlink(f["memory_link"])) == f["memory"]  # memory symlink restored too


# ─────────────────────────── repoint ─────────────────────────────────────────

def test_repoint_rewrites_tracked_files_including_markdown(tmp_path: Path) -> None:
    """Unlike step3's repoint (which excludes *.md), step4a's own grep
    includes CLAUDE.md — this task's own instruction."""
    repo = tmp_path / "fake-agents-repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    old = "/Users/gob/Projects/widget-wikis"
    new = "/Users/gob/MoonieXHQ/Agents/WidgetWikis"
    (repo / "config").mkdir()
    (repo / "config" / "projects.yaml").write_text(f"webapp:\n  path: {old}\n")
    (repo / "CLAUDE.md").write_text(f"see {old} for details\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "reports").mkdir()
    (repo / "docs" / "reports" / "old-report.md").write_text(f"ran against {old}\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    mapping = {old: new}
    changed = mod.rewrite_repoint_files(repo, mapping)
    assert set(changed) == {"config/projects.yaml", "CLAUDE.md"}
    assert new in (repo / "CLAUDE.md").read_text()
    assert old in (repo / "docs" / "reports" / "old-report.md").read_text()  # docs/reports excluded
    assert mod.repoint_files_clean(repo, mapping)
    yaml.safe_load((repo / "config" / "projects.yaml").read_text())


def test_rewrite_skills_txt_uses_literal_hq_paths(tmp_path: Path) -> None:
    skills_txt = tmp_path / "skills.txt"
    skills_txt.write_text(
        "# comment\n"
        "obviously-awesome\t$PROJECTS/external/wondelai-skills/obviously-awesome\n"
        "mooniex-seo\t$PROJECTS/mooniex-claude-skills/mooniex-seo\n"
        "gsap\t$HOME/.agents/skills/gsap\n"
    )
    mapping = {
        "/Users/gob/Projects/external": "/Users/gob/MoonieXHQ/External",
        "/Users/gob/Projects/mooniex-claude-skills": "/Users/gob/MoonieXHQ/Agents/Skills",
    }
    changed = mod.rewrite_skills_txt(skills_txt, mapping)
    assert set(changed) == {"obviously-awesome", "mooniex-seo"}
    text = skills_txt.read_text()
    assert "obviously-awesome\t/Users/gob/MoonieXHQ/External/wondelai-skills/obviously-awesome\n" in text
    assert "mooniex-seo\t/Users/gob/MoonieXHQ/Agents/Skills/mooniex-seo\n" in text
    assert "gsap\t$HOME/.agents/skills/gsap\n" in text  # untouched — not in the mapping
    assert "$PROJECTS" not in text.replace("# comment\n", "")


# ─────────────────────────── unit tests on pure helpers ─────────────────────

def test_external_clone_items_filters_by_prefix(tmp_path: Path) -> None:
    row = {"items": [
        {"name": "a", "current": "/Users/gob/Projects/external/a"},
        {"name": "paperclip", "current": "/Users/gob/Projects/mooniex-nohuman/paperclip"},
        {"name": "video-use", "current": "/Users/gob/Developer/video-use"},
    ]}
    items = mod.external_clone_items(row, external_dir="/Users/gob/Projects/external")
    assert [it["name"] for it in items] == ["a"]


def test_verify_nohuman_brand_clean_and_dirty(tmp_path: Path) -> None:
    f = _build_fixture(tmp_path)
    clean, diffs = mod.verify_nohuman_brand(f["nohuman"])
    assert clean and diffs == []
    (f["nohuman"] / "brand" / "new-file.png").write_text("not on origin\n")
    dirty, diffs2 = mod.verify_nohuman_brand(f["nohuman"])
    assert not dirty and diffs2
