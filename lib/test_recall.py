"""Tests for lib.recall. Plain-script style (no pytest dependency).

Run:  python -m lib.test_recall
Pure-function tests use synthetic task dicts (deterministic); one smoke test
exercises recall() against the live tasks.db read-only.
"""
from __future__ import annotations

from . import recall as r


def _check(name: str, cond: bool) -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return cond


def test_tokens() -> bool:
    ok = True
    ok &= _check("drops short + stopwords", r._tokens("the AI is on a leaderboard")
                 == ["leaderboard"])
    ok &= _check("lowercases + splits", set(r._tokens("Deploy ClaudeFlow VPS"))
                 == {"deploy", "claudeflow", "vps"})
    ok &= _check("empty -> []", r._tokens("") == [])
    return ok


def test_gist() -> bool:
    report = (
        "## Summary\n"
        "Built the leaderboard compute with dedup and rank.\n"
        "## Files Changed\n- a.ts\n- b.ts\n"
    )
    g = r._gist(report)
    ok = True
    ok &= _check("gist pulls Summary body", g.startswith("Built the leaderboard"))
    ok &= _check("gist stops before next heading", "Files Changed" not in g)
    ok &= _check("gist falls back when no Summary",
                 r._gist("just one plain line here") == "just one plain line here")
    ok &= _check("gist empty report -> ''", r._gist(None) == "")
    long = "x" * 500
    ok &= _check("gist truncates long", len(r._gist(long)) <= 220)
    return ok


def test_outcome() -> bool:
    merged = {"status": "done", "branch": "agent/x",
              "review": '{"merge_sha": "abc1234def", "branch": "agent/dev-1"}',
              "report": ""}
    ended = {"status": "cancelled", "branch": None, "review": None, "report": ""}
    sha_in_report = {"status": "done", "branch": None, "review": None,
                     "report": "merged at deadbeef1 finally"}
    ok = True
    ok &= _check("outcome merged sha (7-char)", r._outcome(merged)
                 == "merged sha:abc1234 · agent/dev-1")
    ok &= _check("outcome non-merged -> status", r._outcome(ended) == "ended cancelled")
    ok &= _check("outcome finds sha in report", "deadbee" in r._outcome(sha_in_report))
    return ok


def test_score() -> bool:
    task = {"title": "leaderboard ticket rule", "description": "ticket ticket",
            "report": "ticket " * 20, "project": "p", "role": "developer"}
    ok = True
    ok &= _check("title term weighted x3", r._score(task, ["leaderboard"]) == 3)
    ok &= _check("body hits capped at 5",
                 r._score({"title": "", "description": "ticket " * 50,
                           "report": "", "project": "", "role": ""}, ["ticket"]) == 5)
    ok &= _check("no terms -> 0", r._score(task, []) == 0)
    ok &= _check("absent term -> 0", r._score(task, ["zzznotpresent"]) == 0)
    return ok


def test_age_days() -> bool:
    from datetime import datetime, timezone, timedelta
    ok = True
    ok &= _check("age None -> None", r._age_days(None) is None)
    ok &= _check("age bad -> None", r._age_days("not-a-date") is None)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ok &= _check("age now -> 0", r._age_days(now) == 0)
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")
    ok &= _check("age 10d -> 10", r._age_days(old) == 10)
    return ok


def test_touch_set() -> bool:
    ok = True
    ok &= _check("parses + strips slash",
                 r._touch_set('["/src/a.ts", "src/b.ts"]') == {"src/a.ts", "src/b.ts"})
    ok &= _check("empty/None -> set()", r._touch_set(None) == set())
    ok &= _check("bad json -> set()", r._touch_set("{not json") == set())
    return ok


def test_superseded_by() -> bool:
    older = {"id": "task-old", "project": "p", "status": "done",
             "updated_at": "2026-06-01T00:00:00+00:00", "touches": '["src/x.ts"]'}
    newer = {"id": "task-new", "project": "p", "status": "done",
             "updated_at": "2026-06-05T00:00:00+00:00", "touches": '["src/x.ts"]'}
    other_proj = {"id": "task-q", "project": "q", "status": "done",
                  "updated_at": "2026-06-09T00:00:00+00:00", "touches": '["src/x.ts"]'}
    no_overlap = {"id": "task-z", "project": "p", "status": "done",
                  "updated_at": "2026-06-09T00:00:00+00:00", "touches": '["src/other.ts"]'}
    rows = [older, newer, other_proj, no_overlap]
    ok = True
    ok &= _check("newer same-file same-proj flagged",
                 r._superseded_by(older, rows) == ["task-new"])
    ok &= _check("newest task has no superseder",
                 r._superseded_by(newer, rows) == [])
    ok &= _check("cross-project ignored",
                 "task-q" not in r._superseded_by(older, rows))
    ok &= _check("non-overlapping ignored",
                 "task-z" not in r._superseded_by(older, rows))
    ok &= _check("no touches -> []",
                 r._superseded_by({"id": "t", "project": "p", "status": "done",
                                   "updated_at": "2026-06-01T00:00:00+00:00",
                                   "touches": "[]"}, rows) == [])
    return ok


def test_recall_smoke() -> bool:
    ok = True
    ok &= _check("nonsense query -> []",
                 r.recall("zzqxnonexistentterm9000") == [])
    hits = r.recall("leaderboard", limit=3)
    ok &= _check("limit respected", len(hits) <= 3)
    if hits:
        h = hits[0]
        ok &= _check("digest has required keys",
                     {"task_id", "project", "status", "title", "outcome",
                      "score", "age_days", "superseded_by"} <= set(h))
        ok &= _check("scores sorted desc",
                     all(hits[i]["score"] >= hits[i + 1]["score"]
                         for i in range(len(hits) - 1)))
    txt = r.recall_text("zzqxnonexistentterm9000")
    ok &= _check("recall_text no-match line", "no matching past work" in txt)
    return ok


def main() -> int:
    suites = [test_tokens, test_gist, test_outcome, test_score,
              test_age_days, test_touch_set, test_superseded_by, test_recall_smoke]
    all_ok = True
    for s in suites:
        print(f"{s.__name__}:")
        all_ok &= s()
    print("\n" + ("ALL PASS" if all_ok else "SOME FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
