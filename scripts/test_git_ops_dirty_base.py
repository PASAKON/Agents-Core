"""tools.git_ops._blocking_dirty_paths — the merge pre-flight's dirty-base split.

Born 2026-09-18: two unrelated merges were refused because another CTO session
was writing an untracked scratch directory in the shared main checkout.
Untracked paths never make `git merge` fail unless the branch brings the same
path, so only those (plus any tracked modification) may block.
"""
from tools.git_ops import _blocking_dirty_paths


def test_tracked_modification_always_blocks():
    b, i = _blocking_dirty_paths(" M lib/db.py\n", {"tools/x.py"})
    assert b == ["lib/db.py"] and i == []


def test_untracked_non_colliding_is_ignored():
    b, i = _blocking_dirty_paths(
        "?? prototypes/bl51-first30/\n", {"lib/db.py", "scripts/test_hook_inbox.py"}
    )
    assert b == [] and i == ["prototypes/bl51-first30/"]


def test_untracked_dir_colliding_with_branch_path_blocks():
    b, i = _blocking_dirty_paths(
        "?? prototypes/bl51-first30/\n", {"prototypes/bl51-first30/index.html"}
    )
    assert b == ["prototypes/bl51-first30/"] and i == []


def test_untracked_file_same_path_blocks():
    b, _ = _blocking_dirty_paths("?? scripts/test_new.py\n", {"scripts/test_new.py"})
    assert b == ["scripts/test_new.py"]


def test_mixed_keeps_order_and_skips_blank_lines():
    b, i = _blocking_dirty_paths("?? a/\n\n M b.py\n?? c.txt\n", {"b.py"})
    assert b == ["b.py"] and i == ["a/", "c.txt"]


def test_untracked_prefix_is_a_directory_boundary():
    # "?? proto/" must not swallow "prototypes/x.py" (a different directory).
    b, i = _blocking_dirty_paths("?? proto/\n", {"prototypes/x.py"})
    assert b == [] and i == ["proto/"]


def test_staged_addition_blocks_even_if_branch_untouched():
    b, i = _blocking_dirty_paths("A  new.py\n", {"lib/db.py"})
    assert b == ["new.py"] and i == []
