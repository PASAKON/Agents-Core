"""Read-side memory for the org.

The queue records everything — every task plus a long `events` trail — but
nothing ever reads it back, so prior work is a write-only graveyard. `recall()`
closes that loop: given a free-text query it ranks past tasks by term overlap
(title weighted over body) and returns a compact, human-readable digest of each
match — final status, merge sha, branch, and a short gist of the DEV report —
ready to drop into the CTO's context instead of relighting work already done.

Pure read. No external deps, no embeddings: at this scale (a few hundred tasks)
keyword ranking over SQLite is enough, and it keeps memory transparent and
correctable rather than hidden in a vector store.
"""
from __future__ import annotations

import json
import re

from . import db

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_STOP = {
    "the", "a", "an", "of", "to", "and", "for", "in", "on", "is", "it",
    "do", "does", "did", "was", "were", "are", "with", "this", "that",
    "what", "how", "why", "when", "we", "our", "you", "your",
}


def _tokens(s: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(s or "")
        if len(t) > 2 and t.lower() not in _STOP
    ]


def _gist(report: str | None, limit: int = 220) -> str:
    """One-line essence of a DEV report: the `## Summary` body if present,
    else the first non-heading line. Trimmed to `limit` chars."""
    if not report:
        return ""
    lines = [ln.strip() for ln in report.splitlines()]
    body: list[str] = []
    in_summary = False
    for ln in lines:
        low = ln.lower()
        if low.startswith("## "):
            if in_summary:
                break
            in_summary = low.startswith("## summary")
            continue
        if in_summary and ln:
            body.append(ln)
    if not body:
        body = [ln for ln in lines if ln and not ln.startswith(("#", "-", "*"))]
    text = " ".join(body).strip()
    return (text[: limit - 1] + "…") if len(text) > limit else text


def _outcome(task: dict) -> str:
    """Compact outcome line: merge sha + branch when merged, else status note.
    Pulls sha from the `review` JSON first, then any sha in report/review."""
    sha = None
    branch = task.get("branch")
    review = task.get("review")
    if review:
        try:
            rv = json.loads(review)
            sha = rv.get("merge_sha") or sha
            branch = rv.get("branch") or branch
        except Exception:
            pass
    if not sha:
        m = _SHA_RE.search(review or "") or _SHA_RE.search(task.get("report") or "")
        if m:
            sha = m.group(0)
    if sha:
        line = f"merged sha:{sha[:7]}"
        if branch:
            line += f" · {branch}"
        return line
    return f"ended {task['status']}"


def _score(task: dict, terms: list[str]) -> int:
    if not terms:
        return 0
    title = (task.get("title") or "").lower()
    body = " ".join(
        str(task.get(k) or "") for k in ("description", "report", "project", "role")
    ).lower()
    s = 0
    for t in terms:
        s += title.count(t) * 3
        s += min(body.count(t), 5)  # cap so one huge report can't dominate
    return s


def recall(query: str, project: str | None = None, limit: int = 5) -> list[dict]:
    """Rank past tasks against `query`. Returns up to `limit` digests, each:
    {task_id, project, role, status, title, updated_at, outcome, gist, score}.
    Highest term-overlap first; newer task breaks ties."""
    terms = _tokens(query)
    sql = (
        "SELECT id,project,role,status,title,description,report,review,"
        "branch,updated_at FROM tasks"
    )
    args: list = []
    if project:
        sql += " WHERE project=?"
        args.append(project)
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    scored = []
    for r in rows:
        sc = _score(r, terms)
        if sc > 0:
            scored.append((sc, r.get("updated_at") or "", r))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = []
    for sc, _ts, r in scored[:limit]:
        out.append({
            "task_id": r["id"],
            "project": r["project"],
            "role": r["role"],
            "status": r["status"],
            "title": r["title"],
            "updated_at": (r.get("updated_at") or "")[:10],
            "outcome": _outcome(r),
            "gist": _gist(r.get("report")),
            "score": sc,
        })
    return out


def recall_text(query: str, project: str | None = None, limit: int = 5) -> str:
    """Human-readable rendering of recall() for injection into CTO context."""
    hits = recall(query, project=project, limit=limit)
    if not hits:
        return f'recall: "{query}" — no matching past work.'
    head = f'recall: "{query}" — {len(hits)} match(es):\n'
    blocks = []
    for i, h in enumerate(hits, 1):
        b = (
            f"{i}. {h['task_id']}  [{h['project']}]  {h['status']} · {h['updated_at']}\n"
            f"   {h['title']}\n"
            f"   → {h['outcome']}"
        )
        if h["gist"]:
            b += f"\n   gist: {h['gist']}"
        blocks.append(b)
    return head + "\n".join(blocks)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "leaderboard event deploy"
    print(recall_text(q))
