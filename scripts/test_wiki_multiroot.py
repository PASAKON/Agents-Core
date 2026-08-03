"""Tests for multi-root/namespaced wiki tools (ADR 0013 — wiki scope boundary).

Run via:  python scripts/test_wiki_multiroot.py

Builds a throwaway two-namespace registry under a temp dir per test and
points tools.wiki at it, so these tests never touch the real wiki repos.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import wiki

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)


class _FakeWiki:
    """Points tools.wiki at a temp two-namespace registry for the `with` block.

    org root exists by default (pass with_org=False to simulate the
    not-yet-created Agents-Wikis repo). mooniex root always exists unless
    the caller deletes it after construction (used for the all-roots-missing
    case).
    """

    def __init__(self, tmp: Path, *, with_org: bool = True):
        self.org_root = tmp / "org-wiki"
        self.mooniex_root = tmp / "mooniex-wiki"
        self.config_path = tmp / "wikis.yaml"

        if with_org:
            _git_init(self.org_root)
            (self.org_root / "playbooks").mkdir(parents=True)
            (self.org_root / "playbooks" / "x.md").write_text("org playbook content\n")

        _git_init(self.mooniex_root)
        (self.mooniex_root / "IRON-RULES.md").write_text("mooniex iron rules content\n")

        self.config_path.write_text(
            "default: mooniex\n"
            "wikis:\n"
            f"  - ns: org\n    name: Org\n    path: {self.org_root}\n"
            f"  - ns: mooniex\n    name: MoonieX\n    path: {self.mooniex_root}\n"
        )

    def __enter__(self):
        import os
        self._old_config = wiki.WIKIS_CONFIG
        self._old_wiki_root_env = os.environ.pop("WIKI_ROOT", None)
        wiki.WIKIS_CONFIG = self.config_path
        wiki._registry.cache_clear()
        wiki._roots.cache_clear()
        return self

    def __exit__(self, *exc):
        import os
        wiki.WIKIS_CONFIG = self._old_config
        if self._old_wiki_root_env is not None:
            os.environ["WIKI_ROOT"] = self._old_wiki_root_env
        wiki._registry.cache_clear()
        wiki._roots.cache_clear()


# --- Test 1: namespaced read ---
def test_namespaced_read():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td)):
            result = wiki.wiki_read("org:playbooks/x.md")
    _mark(result.strip() == "org playbook content",
          'wiki_read("org:playbooks/x.md") reads from the org root')


# --- Test 1b: a BARE namespace prefix scopes to that root ---
# Regression: "org" carries no ":", so _split_ns fell through to the default
# namespace and looked for a directory literally named "org" inside it —
# returning [] instead of the org root's pages. Silent wrong answer, and the
# docstring already promised `"ns" or "ns:subpath" -> that root only`.
def test_bare_namespace_prefix_lists_that_root():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td)):
            bare = wiki.wiki_list("org")
            colon = wiki.wiki_list("org:")
    _mark(bare == ["org:playbooks/x.md"],
          f'wiki_list("org") (bare ns) lists the org root, got {bare}')
    _mark(bare == colon,
          'wiki_list("org") and wiki_list("org:") agree')


# --- Test 1c: WIKI_ROOT_<NS> overrides any namespace's path ---
# config/wikis.yaml carries Mac absolute paths. Contabo needs to point the org
# root at its own checkout, and the legacy WIKI_ROOT only ever covered the
# default namespace. Added for ADR 0013 Phase 5.
def test_per_namespace_env_override():
    import os
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with _FakeWiki(tmp):
            elsewhere = tmp / "org-elsewhere"
            _git_init(elsewhere)
            (elsewhere / "playbooks").mkdir(parents=True)
            (elsewhere / "playbooks" / "x.md").write_text("relocated org content\n")
            os.environ["WIKI_ROOT_ORG"] = str(elsewhere)
            wiki._roots.cache_clear()
            try:
                moved = wiki.wiki_read("org:playbooks/x.md")
                default_untouched = wiki.wiki_read("IRON-RULES.md")
            finally:
                del os.environ["WIKI_ROOT_ORG"]
                wiki._roots.cache_clear()
    _mark(moved.strip() == "relocated org content",
          "WIKI_ROOT_ORG repoints the org root away from config/wikis.yaml")
    _mark(default_untouched.strip() == "mooniex iron rules content",
          "WIKI_ROOT_ORG leaves the default namespace alone")


# --- Test 2: unprefixed read hits the default namespace ---
def test_unprefixed_read_hits_default_ns():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td)):
            result = wiki.wiki_read("IRON-RULES.md")
    _mark(result.strip() == "mooniex iron rules content",
          'wiki_read("IRON-RULES.md") (no prefix) resolves against the default (mooniex) namespace')


# --- Test 3: missing root skipped by list/search ---
def test_missing_root_skipped_by_list_and_search():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td), with_org=False):
            pages = wiki.wiki_list()
            hits = wiki.wiki_search("mooniex iron rules")
    org_listed = any(p.startswith("org:") for p in pages)
    mooniex_listed = any(p.startswith("mooniex:") for p in pages)
    _mark(not org_listed and mooniex_listed,
          "wiki_list() skips the missing org root but still lists the mooniex root")
    _mark(len(hits) == 1 and hits[0]["path"].startswith("mooniex:"),
          "wiki_search() skips the missing org root but still returns the mooniex hit")


# --- Test 3b: ALL roots missing -> legacy single-root-missing behavior ---
def test_all_roots_missing_raises_generic_error():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fw = _FakeWiki(tmp, with_org=False)
        shutil.rmtree(fw.mooniex_root)  # now every registered root is missing
        with fw:
            try:
                wiki.wiki_list()
                caught = None
            except wiki.WikiError as e:
                caught = str(e)
    _mark(caught == "wiki not available in this environment",
          "wiki_list() with ALL roots missing raises the same generic message the "
          "single-root version always raised")


# --- Test 4: missing root raises a named WikiError on read ---
def test_missing_root_raises_named_error_on_read():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td), with_org=False):
            try:
                wiki.wiki_read("org:playbooks/x.md")
                caught = None
            except wiki.WikiError as e:
                caught = str(e)
    _mark(caught == "wiki 'org' not available in this environment",
          "wiki_read() against the missing org root raises a WikiError naming the namespace")


# --- Test 5: both traversal attacks blocked ---
def test_path_traversal_blocked():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td)):
            blocked_unprefixed = False
            blocked_namespaced = False
            try:
                wiki.wiki_read("../../../etc/passwd")
            except wiki.WikiError:
                blocked_unprefixed = True
            try:
                wiki.wiki_read("org:../../etc/passwd")
            except wiki.WikiError:
                blocked_namespaced = True
    _mark(blocked_unprefixed,
          'wiki_read("../../../etc/passwd") raises WikiError, does not read')
    _mark(blocked_namespaced,
          'wiki_read("org:../../etc/passwd") raises WikiError, does not read')


# --- Test 6: ns:relpath from wiki_search round-trips into wiki_read ---
def test_search_round_trips_into_read():
    with tempfile.TemporaryDirectory() as td:
        with _FakeWiki(Path(td)):
            hits = wiki.wiki_search("mooniex iron rules")
            hit_path = hits[0]["path"] if hits else None
            content = wiki.wiki_read(hit_path) if hit_path else ""
    _mark(hit_path == "mooniex:IRON-RULES.md",
          f"wiki_search() hit path is 'mooniex:IRON-RULES.md' (got {hit_path!r})")
    _mark("mooniex iron rules content" in content,
          "wiki_search() hit's ns:relpath round-trips straight back into wiki_read()")


def main() -> int:
    print("Running wiki multi-root tests...\n")
    test_namespaced_read()
    test_bare_namespace_prefix_lists_that_root()
    test_per_namespace_env_override()
    test_unprefixed_read_hits_default_ns()
    test_missing_root_skipped_by_list_and_search()
    test_all_roots_missing_raises_generic_error()
    test_missing_root_raises_named_error_on_read()
    test_path_traversal_blocked()
    test_search_round_trips_into_read()

    total = 13
    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'} ({total - _failures}/{total})")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
