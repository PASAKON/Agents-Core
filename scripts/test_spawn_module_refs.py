"""Every `python -m <module>` the org spawns must name a real module.

Born from 2026-08-15, which cost about an hour. Commit df01c33 renamed
`runners/dev_init.py` -> `runners/worker_init.py` as a pure `git mv`. The
spawn command lives in `tools/delegate.py` as a *string*:

    f"... python -m runners.dev_init {role} {task_id}"

A string is invisible to imports, to the linter, and to every existing
test, so the rename passed review and CI while silently breaking the only
line that starts a worker. Nothing failed loudly: tmux dutifully created a
session, the command inside died in under a second with `No module named
runners.dev_init`, tmux tore the session down carrying the error with it,
and the org log printed `DEV spawned (fire-and-forget)`. Every delegation
failed 100% of the time and looked like success.

This test closes that gap at commit time: it extracts the module name from
every `python -m ...` string in the spawn-owning modules and asserts each
one is importable. A rename that misses a call site fails here instead of
in production at 3am.

It deliberately checks *resolvability*, not spelling: `importlib.util.
find_spec` follows the same rules the spawned interpreter will.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Files that build a `python -m ...` command line for something the org
# spawns. Add to this list when a new spawn site appears.
SPAWN_SITES = (
    "tools/delegate.py",
    "tools/resume_worker.py",
    "runners/worker_init.py",
    "runners/worker_resume.py",
    "scripts/spawn-worker.sh",
)

# The stable launcher delegate.py shells out to, and the line inside it that
# names the worker module. This indirection is the root-cause fix for stale
# in-process code (see the comment above WORKER_LAUNCHER in tools/delegate.py):
# delegate.py must NOT name the worker module itself, or the name gets frozen
# into every running session again and a rename breaks them all until restart.
LAUNCHER = "scripts/spawn-worker.sh"
_SH_MODULE = re.compile(r'^WORKER_MODULE="([A-Za-z_][A-Za-z0-9_.]*)"', re.M)

# `python -m runners.worker_init`, `python3 -m lib.foo`, and the f-string
# variants are all matched; the module itself is always a literal dotted
# name in this repo.
_PY_M = re.compile(r"python[0-9.]*\s+-m\s+([A-Za-z_][A-Za-z0-9_.]*)")


def _strip_comments(src: str) -> str:
    """Drop whole-line comments (`#`, shared by .py and .sh).

    Needed because these files *document* the rename incident in prose, and
    that prose contains a literal `python -m runners.dev_init`. Scanning it
    would fail the suite on a correct tree — an assertion firing on a comment
    is a false alarm that teaches people to ignore the test.
    """
    return "\n".join(
        ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
    )


def _module_refs() -> list[tuple[str, str]]:
    """(source file, module name) for every `python -m <mod>` in SPAWN_SITES."""
    found: list[tuple[str, str]] = []
    for rel in SPAWN_SITES:
        path = ROOT / rel
        if not path.is_file():
            continue  # a site can legitimately be renamed away
        code = _strip_comments(path.read_text(encoding="utf-8"))
        for mod in _PY_M.findall(code):
            found.append((rel, mod))
    return found


def test_spawn_sites_actually_reference_a_module() -> None:
    """Guard the guard: if the regex stops matching, every other assertion
    in this file passes vacuously and the protection is gone."""
    refs = _module_refs()
    assert refs, (
        "no `python -m <module>` found in any spawn site — either the spawn "
        "mechanism changed or _PY_M stopped matching. Both make this file's "
        "other tests pass while checking nothing."
    )


@pytest.mark.parametrize("rel,mod", _module_refs(),
                          ids=lambda v: str(v).replace("/", "."))
def test_spawned_module_is_importable(rel: str, mod: str) -> None:
    spec = importlib.util.find_spec(mod)
    assert spec is not None, (
        f"{rel} spawns `python -m {mod}`, but that module does not resolve. "
        f"A rename almost certainly missed this string. Every worker spawn "
        f"goes through it, so this breaks all delegation, silently — the "
        f"tmux session dies in under a second and the org log still reports "
        f"a successful spawn."
    )


def test_launcher_names_an_importable_worker_module() -> None:
    """The launcher holds the module name in a shell variable, so the
    `python -m <literal>` scan above cannot see it. Check it directly."""
    src = (ROOT / LAUNCHER).read_text(encoding="utf-8")
    m = _SH_MODULE.search(src)
    assert m, (
        f"{LAUNCHER} has no `WORKER_MODULE=\"...\"` line. That line is the "
        f"single place the worker module is named; without it the launcher "
        f"cannot be checked and the rename guard is gone."
    )
    mod = m.group(1)
    assert importlib.util.find_spec(mod) is not None, (
        f"{LAUNCHER} spawns `python -m {mod}`, which does not resolve. "
        f"Every worker spawn goes through this line."
    )


def test_delegate_does_not_name_the_worker_module_itself() -> None:
    """The whole point of the launcher: delegate.py is imported once per
    C-level session and cannot reload, so anything it names is frozen for that
    session's life. It must reference the launcher path, never the module."""
    code = _strip_comments((ROOT / "tools/delegate.py").read_text(encoding="utf-8"))
    assert "spawn-worker.sh" in code, (
        "tools/delegate.py no longer references scripts/spawn-worker.sh — the "
        "indirection that keeps a renamed worker module from breaking every "
        "already-running session has been removed."
    )
    offenders = _PY_M.findall(code)
    assert not offenders, (
        f"tools/delegate.py names worker modules directly ({offenders}). That "
        f"re-freezes the module name into every running session — the exact "
        f"bug that made all delegation fail for hours on 2026-08-15. Route "
        f"through {LAUNCHER} instead."
    )


def test_no_reference_to_the_pre_rename_worker_module() -> None:
    """`dev_init` is the specific name that broke; keep it from coming back
    through a copy-paste of an old snippet or a reverted hunk."""
    offenders = [rel for rel, mod in _module_refs() if mod.endswith("dev_init")]
    assert not offenders, (
        f"{offenders} still spawn `runners.dev_init`, renamed to "
        f"`runners.worker_init` in df01c33 (2026-08-15)."
    )
