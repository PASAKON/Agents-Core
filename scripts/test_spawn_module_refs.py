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
)

# `python -m runners.worker_init`, `python3 -m lib.foo`, and the f-string
# variants are all matched; the module itself is always a literal dotted
# name in this repo.
_PY_M = re.compile(r"python[0-9.]*\s+-m\s+([A-Za-z_][A-Za-z0-9_.]*)")


def _module_refs() -> list[tuple[str, str]]:
    """(source file, module name) for every `python -m <mod>` in SPAWN_SITES."""
    found: list[tuple[str, str]] = []
    for rel in SPAWN_SITES:
        path = ROOT / rel
        if not path.is_file():
            continue  # a site can legitimately be renamed away
        for mod in _PY_M.findall(path.read_text(encoding="utf-8")):
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


def test_no_reference_to_the_pre_rename_worker_module() -> None:
    """`dev_init` is the specific name that broke; keep it from coming back
    through a copy-paste of an old snippet or a reverted hunk."""
    offenders = [rel for rel, mod in _module_refs() if mod.endswith("dev_init")]
    assert not offenders, (
        f"{offenders} still spawn `runners.dev_init`, renamed to "
        f"`runners.worker_init` in df01c33 (2026-08-15)."
    )
