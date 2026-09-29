"""Read-only runner skill statistics from reviewed task history."""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3


@dataclass
class RunnerStat:
    runner: str
    task_class: str
    n: int
    passed: int
    failed: int
    mean_iteration: float
    score: float


def _compute(db_path, task_class=None, *, by_class=False):
    role_expr = "role" if by_class else "?"
    params = [] if by_class else ["*" if task_class is None else task_class]
    query = f"""
        SELECT COALESCE(runner, 'claude'), {role_expr}, COUNT(*),
               SUM(status IN ('done', 'merged')), SUM(status = 'failed'),
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
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        return [
            RunnerStat(*row[:-1], round(row[-1], 4))
            for row in conn.execute(query, params)
        ]


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
