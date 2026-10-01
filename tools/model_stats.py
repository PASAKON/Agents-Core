"""Read-only runner skill statistics from reviewed task history."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
# Run as a script (`python tools/model_stats.py`), the repo root is not on
# sys.path; same fix as tools/workdir.py.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib import db as db_lib  # noqa: E402


@dataclass
class RunnerStat:
    runner: str
    task_class: str
    n: int
    passed: int
    failed: int
    mean_iteration: float
    score: float


def _stat(row) -> RunnerStat:
    # tuple() first: a Postgres row (lib.db_pg.Row) does not slice, and its
    # AVG()s come back as Decimal.
    v = tuple(row)
    return RunnerStat(v[0], v[1], int(v[2]), int(v[3] or 0), int(v[4] or 0),
                      None if v[5] is None else float(v[5]), round(float(v[6]), 4))


def _compute(db_path, task_class=None, *, by_class=False):
    """Read through lib.db, so the hub answers once ORG_DB_URL is set: after
    the G1 cutover state/tasks.db is a tombstone directory, and the raw
    sqlite3.connect() this used to do failed into route.load_skill_scores'
    `except` -- the router ran without skill scores (task-1b8ef857). The SQL
    is the subset SQLite and Postgres share (no SUM over a boolean, a typed
    parameter in the select list)."""
    role_expr = "role" if by_class else "CAST(? AS TEXT)"
    params = [] if by_class else ["*" if task_class is None else task_class]
    query = f"""
        SELECT COALESCE(runner, 'claude'), {role_expr}, COUNT(*),
               SUM(CASE WHEN status IN ('done', 'merged') THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END),
               AVG(iteration),
               AVG(CASE WHEN status IN ('done', 'merged')
                        THEN 1.0 / (1 + iteration) ELSE 0.0 END)
        FROM tasks
        WHERE status IN ('done', 'merged', 'failed')
    """
    if task_class is not None:
        query += " AND role = ?"
        params.append(task_class)
    query += " GROUP BY COALESCE(runner, 'claude')"
    if by_class:
        query += ", role"
    query += " ORDER BY 1, 2"
    with db_lib.get_conn(path=Path(db_path), readonly=True) as conn:
        return [_stat(row) for row in conn.execute(query, params).fetchall()]


def compute_stats(db_path, task_class: str | None = None) -> dict[str, RunnerStat]:
    """Pool reviewed tasks by runner, optionally restricting to one role."""
    return {stat.runner: stat for stat in _compute(db_path, task_class)}


def compute_stats_by_class(db_path) -> dict[tuple[str, str], RunnerStat]:
    """Aggregate reviewed tasks separately for each runner and role."""
    return {
        (stat.runner, stat.task_class): stat
        for stat in _compute(db_path, by_class=True)
    }


def skill_scores(
    db_path, plans_cfg: dict, task_class: str | None = None,
) -> dict[tuple[str, str], tuple[float, int]]:
    """Map configured candidates to reviewed scores and sample counts.

    V1 limitation: tasks has no model column, so all models of one runner
    share the runner's score.
    """
    stats = compute_stats(db_path, task_class)
    scores = {}
    for candidates in plans_cfg.get("roles", {}).values():
        for candidate in candidates:
            runner, model, *_ = candidate.split(":")
            if runner in stats:
                stat = stats[runner]
                scores[runner, model] = (stat.score, stat.n)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", type=Path,
        default=Path(__file__).resolve().parents[1] / "state" / "tasks.db",
    )
    parser.add_argument("--by-class", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    stats = (compute_stats_by_class(args.db) if args.by_class
             else compute_stats(args.db))
    if args.json:
        print(json.dumps([asdict(stat) for stat in stats.values()]))
    else:
        for stat in stats.values():
            print(
                f"{stat.runner} {stat.task_class} n={stat.n} pass={stat.passed} "
                f"fail={stat.failed} mean_iter={stat.mean_iteration:.4f} "
                f"score={stat.score:.4f}"
            )


if __name__ == "__main__":
    main()
