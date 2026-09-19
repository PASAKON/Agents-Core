"""A rate-limited worker that is still alive must not be garbage-collected.

2026-09-19: task-2e5cd54e was mid-episode when its Claude WEEKLY quota was
reached. The API reports retry_after=300s for a weekly allowance too, so the
task sat in `rate_limited` while auto_resume retried and kept being refused.
Thirty minutes past that retry_after, the GC cancelled it and reclaimed its
worktree. Four commits of real fixes survived only because git had them.

Every other GC category already checked liveness first; this one did not.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gcmod", ROOT / "tools" / "gc_stale_tasks.py")
gcmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gcmod)


def _category3_source() -> str:
    src = (ROOT / "tools" / "gc_stale_tasks.py").read_text(encoding="utf-8")
    start = src.index("# Category 3: rate_limited")
    nxt = src.find("# Category", start + 10)
    return src[start:nxt if nxt != -1 else len(src)]


def test_category3_checks_liveness_before_cancelling():
    body = _category3_source()
    assert "_alive_for_gc(" in body, (
        "the rate_limited sweep must ask whether the worker is still running, "
        "the same way every other category does"
    )
    assert body.index("_alive_for_gc(") < body.index("db.update_status"), (
        "liveness must be checked BEFORE the cancel, not reported after it"
    )
    assert "alive is True" in body, (
        "only a definite True may spare the task — _alive_for_gc returns None "
        "for 'could not determine', which must not be read as alive"
    )


def test_a_dead_rate_limited_task_is_still_collected():
    body = _category3_source()
    assert "db.update_status" in body, "a genuinely dead rate_limited task must still be cancelled"
    assert "process not alive" in body, "and the log line should say why it was safe to cancel"


def test_alive_helper_treats_missing_pid_as_not_alive():
    # a task that never recorded a pid cannot be protected by this check
    assert gcmod._pid_alive(None) is False
