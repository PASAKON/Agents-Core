"""Tests for scripts/wiki_split.py (ADR 0013 §"Rollout" Phase 4).

Run via:  python scripts/test_wiki_split.py

Every test builds throwaway temp git repos and points wiki_split at them
directly via in-memory registry/manifest dicts — this NEVER touches the
real MoonieX-Wikis / Agents-Wikis / LungNote-Wikis repos, including in the
--apply tests.
"""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import wiki_split as ws

_failures = 0
_total = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures, _total
    _total += 1
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _git_repo(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=root, check=True)


def _porcelain(root: Path) -> str:
    r = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    return r.stdout


def _build_fixture(tmp: Path):
    """A minimal but representative two-repo fixture:
    - IRON-RULES.md (root, out_of_scope, stays mooniex) has: a same-side
      link, a crossing bare-slash [[wikilink]], and a dangling link.
    - playbooks/stays.md stays in mooniex, no links.
    - playbooks/onboarding.md moves mooniex -> org; contains a `../`
      relative link with an anchor pointing back at IRON-RULES.md (stays
      mooniex) -- crosses, and must resolve the `../` before deciding that.
    - playbooks/cto-dev-orchestration.md moves mooniex -> org; referenced
      elsewhere via a bare-name (no slash) [[wikilink]], Obsidian-style.
    """
    mooniex_root = tmp / "mooniex-wiki"
    org_root = tmp / "org-wiki"

    mooniex_files = {
        "IRON-RULES.md": (
            "Same-side link: [Stays](playbooks/stays.md)\n"
            "Crossing wikilink: [[playbooks/onboarding.md]]\n"
            "Dangling link: [Nope](playbooks/does-not-exist.md)\n"
            "Bare-name crossing wikilink: [[cto-dev-orchestration]]\n"
        ),
        "playbooks/stays.md": "stays in mooniex, no links\n",
        "playbooks/onboarding.md": (
            "Relative-up crossing link: [IRON §5](../IRON-RULES.md#section-5)\n"
        ),
        "playbooks/cto-dev-orchestration.md": "cto orchestration content\n",
    }
    org_files = {
        "README.md": "org wiki root\n",
    }

    _git_repo(mooniex_root, mooniex_files)
    _git_repo(org_root, org_files)

    registry = {"org": org_root, "mooniex": mooniex_root}
    manifest = {
        "moves": [
            {"path": "playbooks/onboarding.md", "from": "mooniex", "to": "org"},
            {"path": "playbooks/cto-dev-orchestration.md", "from": "mooniex", "to": "org"},
        ],
        "destinations": {},
        "out_of_scope": ["IRON-RULES.md"],
    }
    return registry, manifest


# --- Test: same-side link left untouched ---
def test_same_side_link_untouched():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        result = ws.scan_wiki(registry, manifest)
    new_text = result.rewrites.get(("mooniex", "IRON-RULES.md"), "")
    _mark(
        "[Stays](playbooks/stays.md)" in new_text,
        "a same-side link (IRON-RULES.md -> playbooks/stays.md, both stay mooniex) keeps its relative form unchanged",
    )


# --- Test: crossing [[wikilink]] (slash form) converted to two-part form ---
def test_crossing_wikilink_slash_form_converted():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        result = ws.scan_wiki(registry, manifest)
    new_text = result.rewrites[("mooniex", "IRON-RULES.md")]
    expected = (
        "[playbooks/onboarding.md]"
        "(https://github.com/PASAKON/Agents-Wikis/blob/main/playbooks/onboarding.md) "
        "(`org:playbooks/onboarding.md`)"
    )
    _mark(expected in new_text, f"crossing [[playbooks/onboarding.md]] converted to two-part form, got: {new_text!r}")


# --- Test: crossing [[wikilink]] (bare-name, Obsidian vault search) converted ---
def test_crossing_wikilink_bare_name_converted():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        result = ws.scan_wiki(registry, manifest)
    new_text = result.rewrites[("mooniex", "IRON-RULES.md")]
    expected = (
        "[cto-dev-orchestration]"
        "(https://github.com/PASAKON/Agents-Wikis/blob/main/playbooks/cto-dev-orchestration.md) "
        "(`org:playbooks/cto-dev-orchestration.md`)"
    )
    _mark(
        expected in new_text,
        f"bare-name [[cto-dev-orchestration]] resolved by vault-wide search and converted, got: {new_text!r}",
    )


# --- Test: dangling link reported and NOT rewritten ---
def test_dangling_reported_and_not_rewritten():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        result = ws.scan_wiki(registry, manifest)
    new_text = result.rewrites[("mooniex", "IRON-RULES.md")]
    _mark("[Nope](playbooks/does-not-exist.md)" in new_text, "dangling link left byte-for-byte unchanged in output")
    hits = [d for d in result.dangling if d.file == "mooniex:IRON-RULES.md" and d.line == 3]
    _mark(
        len(hits) == 1 and hits[0].target == "[Nope](playbooks/does-not-exist.md)",
        f"dangling link reported as file:line -> target, got: {result.dangling}",
    )


# --- Test: `../` relative link resolved against the containing file's dir
# before the crossing decision is made (task's own example) ---
def test_dotdot_relative_resolved_before_crossing_decision():
    resolved = ws._resolve_relative("playbooks", "../IRON-RULES.md")
    _mark(resolved == "IRON-RULES.md", f"'../IRON-RULES.md' from playbooks/ resolves to root-level IRON-RULES.md, got {resolved!r}")


# --- Test: anchor preserved into the URL (and the crossing link is correct) ---
def test_anchor_preserved_and_relative_up_link_crosses():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        result = ws.scan_wiki(registry, manifest)
    new_text = result.rewrites[("mooniex", "playbooks/onboarding.md")]
    expected = (
        "[IRON §5](https://github.com/PASAKON/MoonieX-Wikis/blob/main/IRON-RULES.md#section-5) "
        "(`mooniex:IRON-RULES.md`)"
    )
    _mark(
        expected in new_text,
        f"'../IRON-RULES.md#section-5' from playbooks/onboarding.md (moving to org) crosses back to "
        f"mooniex, anchor survives into the URL, backtick ns:path omits it: {new_text!r}",
    )


# --- Test: --apply refuses to start on a dirty repo ---
def test_apply_refuses_dirty_repo():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        (registry["mooniex"] / "playbooks" / "stays.md").write_text("dirtied, unstaged\n", encoding="utf-8")
        buf = io.StringIO()
        rc = ws.cmd_apply(registry, manifest, out=buf)
        onboarding_moved = (registry["org"] / "playbooks" / "onboarding.md").exists()
    _mark(rc == 1, f"cmd_apply returns 1 when a repo has an unstaged modification, got {rc}")
    _mark("mooniex" in buf.getvalue(), f"refusal message names the dirty namespace, got: {buf.getvalue()!r}")
    _mark(not onboarding_moved, "no file was moved when apply refused to start")


# --- Test: --apply run twice is a no-op the second time ---
def test_apply_twice_is_noop_second_time():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))

        buf1 = io.StringIO()
        rc1 = ws.cmd_apply(registry, manifest, out=buf1)
        status1_mooniex = _porcelain(registry["mooniex"])
        status1_org = _porcelain(registry["org"])

        buf2 = io.StringIO()
        rc2 = ws.cmd_apply(registry, manifest, out=buf2)
        status2_mooniex = _porcelain(registry["mooniex"])
        status2_org = _porcelain(registry["org"])

        moved_ok = (
            (registry["org"] / "playbooks" / "onboarding.md").exists()
            and not (registry["mooniex"] / "playbooks" / "onboarding.md").exists()
        )

    _mark(rc1 == 0, f"first --apply succeeds, got rc={rc1}")
    _mark(rc2 == 0, f"second --apply succeeds — not blocked by its own staged-but-uncommitted output, got rc={rc2}")
    _mark("Moved: 2" in buf1.getvalue(), f"first run moves both manifest entries, got: {buf1.getvalue()!r}")
    _mark(
        "Already moved (no-op): 2" in buf2.getvalue(),
        f"second run finds both entries already moved and treats them as a no-op, got: {buf2.getvalue()!r}",
    )
    _mark(status1_mooniex == status2_mooniex, "second apply makes no further change to mooniex (working tree + index identical)")
    _mark(status1_org == status2_org, "second apply makes no further change to org (working tree + index identical)")
    _mark(moved_ok, "file physically present at destination (org), gone from source (mooniex)")


# --- Test: --plan never writes (shares the read-only scan_wiki() pass) ---
def test_plan_is_read_only():
    with tempfile.TemporaryDirectory() as td:
        registry, manifest = _build_fixture(Path(td))
        before_mooniex = _porcelain(registry["mooniex"])
        before_org = _porcelain(registry["org"])
        buf = io.StringIO()
        ws.cmd_plan(registry, manifest, out=buf)
        after_mooniex = _porcelain(registry["mooniex"])
        after_org = _porcelain(registry["org"])
    _mark(before_mooniex == after_mooniex == "", "cmd_plan leaves mooniex working tree clean (git status empty before and after)")
    _mark(before_org == after_org == "", "cmd_plan leaves org working tree clean (git status empty before and after)")


def main() -> int:
    print("Running wiki_split tests...\n")
    test_same_side_link_untouched()
    test_crossing_wikilink_slash_form_converted()
    test_crossing_wikilink_bare_name_converted()
    test_dangling_reported_and_not_rewritten()
    test_dotdot_relative_resolved_before_crossing_decision()
    test_anchor_preserved_and_relative_up_link_crosses()
    test_apply_refuses_dirty_repo()
    test_apply_twice_is_noop_second_time()
    test_plan_is_read_only()

    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'} ({_total - _failures}/{_total})")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
