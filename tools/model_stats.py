"""Read-only runner and model statistics from finished task history."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib import db as db_lib  # noqa: E402


@dataclass
class RunnerStat:
    runner: str
    model: str
    task_class: str
    n: int
    passed: int
    failed: int
    mean_iteration: float
    score: float
    first_pass_y: int
    first_pass_n: int

    @property
    def first_pass_rate(self) -> float | None:
        total = self.first_pass_y + self.first_pass_n
        return self.first_pass_y / total if total else None


def _first_pass_by_task(conn) -> dict[str, bool]:
    """The reviewer's verdict per task: the newest runner_fit event (tools/runner_fit.py,
    CXO_Gate_RouteFirst Gate 5). A task nobody reviewed has no first-pass value."""
    out = {}
    for task_id, payload in conn.execute(
            "SELECT task_id, payload FROM events WHERE kind = 'runner_fit' ORDER BY ts").fetchall():
        try:
            value = json.loads(payload or "{}").get("first_pass")
        except (ValueError, TypeError, AttributeError):
            continue
        if task_id and isinstance(value, bool):
            out[task_id] = value
    return out


def _compute(db_path, task_class=None, *, by_class=False):
    """Aggregate in Python so the same code runs on SQLite and Postgres."""
    query = ("SELECT runner, runner_model, role, status, iteration, id FROM tasks "
             "WHERE status IN ('done', 'merged', 'failed')")
    params = []
    if task_class is not None:
        query += " AND role = ?"
        params.append(task_class)
    with db_lib.get_conn(path=Path(db_path), readonly=True) as conn:
        rows = conn.execute(query, params).fetchall()
        fit = _first_pass_by_task(conn)
    groups = defaultdict(list)
    for row in rows:
        runner, model, role, *_ = tuple(row)
        groups[(runner or "claude", model or "", role if by_class else task_class or "*")].append(tuple(row))
    result = []
    for (runner, model, role), tasks in sorted(groups.items()):
        passed = sum(t[3] in ("done", "merged") for t in tasks)
        failed = sum(t[3] == "failed" for t in tasks)
        iterations = [int(t[4] or 0) for t in tasks]
        first_pass = [fit[t[5]] for t in tasks if t[5] in fit]
        score = sum(1 / (1 + i) if t[3] in ("done", "merged") else 0
                    for t, i in zip(tasks, iterations)) / len(tasks)
        result.append(RunnerStat(runner, model, role, len(tasks), passed, failed,
                                 sum(iterations) / len(tasks), round(score, 4),
                                 first_pass.count(True), first_pass.count(False)))
    return result


def compute_stats(db_path, task_class: str | None = None) -> dict[tuple[str, str], RunnerStat]:
    return {(s.runner, s.model): s for s in _compute(db_path, task_class)}


def compute_stats_by_class(db_path) -> dict[tuple[str, str, str], RunnerStat]:
    return {(s.runner, s.model, s.task_class): s for s in _compute(db_path, by_class=True)}


def skill_scores(db_path, plans_cfg: dict, task_class: str | None = None) -> dict[tuple[str, str], tuple[float, int]]:
    """Return observed scores only for configured runner/model pairs."""
    stats = compute_stats(db_path, task_class)
    configured = {candidate for candidates in plans_cfg.get("roles", {}).values()
                  for candidate in candidates}
    if "codex:" in configured:
        configured.add("codex:gpt-6-astra:default")
    return {(runner, model): (stat.score, stat.n)
            for (runner, model), stat in stats.items()
            if f"{runner}:{model}" in configured}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "state" / "tasks.db")
    parser.add_argument("--by-class", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    stats = compute_stats_by_class(args.db) if args.by_class else compute_stats(args.db)
    if args.json:
        print(json.dumps([{**asdict(s), "first_pass_rate": s.first_pass_rate} for s in stats.values()]))
    else:
        for s in stats.values():
            print(f"{s.runner}:{s.model} {s.task_class} n={s.n} pass={s.passed} "
                  f"fail={s.failed} mean_iter={s.mean_iteration:.4f} "
                  f"score={s.score:.4f} first_pass={s.first_pass_y}/{s.first_pass_y + s.first_pass_n}")


if __name__ == "__main__":
    main()
