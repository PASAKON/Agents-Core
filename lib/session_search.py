"""Full-text search over past Claude Code session transcripts.

Closes the "discussed but never written down" gap (ADR 0019 §2). ``lib.recall``
searches ``tasks.db`` (task titles + DEV reports); it never touches the
conversation transcripts at ``~/.claude/projects/``. So anything that was only
said in chat is gone the moment the context window rolls. This module builds a
SQLite FTS5 index over those transcripts and answers a free-text query with a
date, a session id, and a snippet — invoked when a C-level suspects a thing was
discussed before.

Pull, not push: this is deliberately NOT wired into a hook. ``hook-recall.py``
already spends context on every prompt (see ADR 0016 on what a turn costs);
session search costs nothing until a C-level calls it.

Design rules (ADR 0019 §2, ADR 0021):

- **Read-only over the corpus.** Never writes into ``~/.claude/projects/``.
- **The index is derived.** Lives at ``state/session-search.db``; deleting it
  loses nothing — ``reindex()`` rebuilds it fully from the corpus.
- **Incremental by mtime.** Each file's ``(mtime, size)`` is tracked in the
  ``files`` side table; only changed files are re-parsed. A full rescan of the
  ~2.4 GB corpus on every call is unacceptable.
- **Never index a file still being written.** A file whose mtime is within a
  grace window of "now" is skipped — the live session appends to its ``.jsonl``
  continuously, and reading a half-flushed line misindexes or crashes. This is
  the same class of bug as the 2026-08-06 dedup that reported "no match" for
  ~20 GB that was simply not there *yet*.
- **Keyword/FTS5 only, no embeddings.** Same rationale as ``lib.recall``: at
  this scale keyword search is enough and keeps memory transparent and
  correctable rather than hidden in a vector store.

Scope: the Agents project transcripts only (ADR 0019 §2). Widen only if it
earns it.

Only ``user`` / ``assistant`` **text** parts are indexed. ``tool_result`` /
``tool_use`` / ``thinking`` / ``attachment`` / ``image`` are skipped — they are
the bulk of the bytes and carry little of what was actually *discussed*.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The index is a derived artifact. Overridable for tests; never commit it
# (state/session-search.db is a build product — a checkout's copy would always
# be stale, so it must not enter the repo).
DEFAULT_INDEX = ROOT / "state" / "session-search.db"

# Scope to the Agents project transcripts (ADR 0019 §2). 132 project dirs exist
# under ~/.claude/projects/; only this one is indexed in this task.
DEFAULT_CORPUS = Path(os.environ.get(
    "SESSION_TRANSCRIPTS_DIR",
    str(Path.home() / ".claude" / "projects" / "-Users-gob-Projects-Agents"),
))

# A file modified within this many seconds of "now" is treated as still being
# written (the live session appends continuously) and skipped this pass. Once it
# goes quiet it is picked up on the next call. See module docstring.
LIVE_WRITE_GRACE_SECONDS = 120

# Index only these record types. attachment/queue-operation/file-history-*/
# custom-title/mode/etc. are metadata or bulk tool output — not conversation.
_INDEXED_TYPES = {"user", "assistant"}

# Query tokeniser. FTS5 unicode61 splits on non-alphanumeric by default, so this
# mirrors it: keep runs of [0-9A-Za-z]. Lower-cased to match unicode61 folding.
_QUERY_TOKEN_RE = re.compile(r"[0-9A-Za-z]+")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path        TEXT PRIMARY KEY,   -- basename of the .jsonl in the corpus
    mtime       REAL NOT NULL,
    size        INTEGER NOT NULL,
    session_id  TEXT,
    first_ts    TEXT,
    indexed_at  TEXT NOT NULL
);

-- FTS5 over one row per indexed message-text part.
-- path/session_id/date are UNINDEXED (stored, retrievable, not searched): we
-- filter by path when re-indexing a changed file, and return session_id+date
-- with each hit. Only `text` is searchable.
CREATE VIRTUAL TABLE IF NOT EXISTS transcripts USING fts5(
    path        UNINDEXED,
    session_id  UNINDEXED,
    date        UNINDEXED,
    text,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _open(index_path: Path) -> sqlite3.Connection:
    """Open (creating the parent dir) the index DB. No WAL pragma: keeps the
    index a single file under state/ (no -wal/-shm sidecars to clean up).

    Own database (a derived FTS5 index, not the task registry) -- lib.db
    .sqlite_connect just centralises the raw sqlite3 connect() call, it
    does not follow ORG_DB_URL."""
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    from lib import db as db_lib
    return db_lib.sqlite_connect(index_path)


def _drop_index(index_path: Path) -> None:
    """Remove the derived index so the next ``reindex(full=True)`` rebuilds it
    from scratch. The index is a build product — a delete loses nothing because
    the corpus is the source of truth (module docstring) — and this is also the
    recovery path for a corrupt DB: ``unlink`` removes the file regardless of
    its contents, after which ``_open`` + the schema script recreate it empty.
    No WAL pragma is set, so there are no ``-wal``/``-shm`` sidecars to chase.
    """
    try:
        Path(index_path).unlink()
    except FileNotFoundError:
        pass


def _iter_message_text(jsonl_path: Path):
    """Yield ``(timestamp, session_id, text)`` for each user/assistant TEXT part
    in a transcript file. Corrupt/truncated JSON lines are skipped silently — a
    half-flushed line at the tail must never crash the indexer. Returns nothing
    if the file cannot be opened."""
    session_fallback = jsonl_path.stem
    try:
        fh = open(jsonl_path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue  # corrupt/truncated line — skip, keep going
            if not isinstance(obj, dict):
                continue
            if obj.get("type") not in _INDEXED_TYPES:
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            ts = obj.get("timestamp") or ""
            sid = obj.get("sessionId") or session_fallback
            content = msg.get("content")
            if isinstance(content, str):
                if content.strip():
                    yield ts, sid, content
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict) or part.get("type") != "text":
                        continue
                    text = part.get("text") or ""
                    if text.strip():
                        yield ts, sid, text


def reindex(
    corpus_dir: str | Path | None = None,
    index_path: str | Path | None = None,
    *,
    now: float | None = None,
    live_grace_seconds: int = LIVE_WRITE_GRACE_SECONDS,
    full: bool = False,
) -> dict:
    """Bring the index up to date with the corpus.

    By default this is incremental: each file's ``(mtime, size)`` is tracked in
    the ``files`` side table and only changed files are re-parsed.

    With ``full=True`` it rebuilds from scratch — the existing index is dropped
    first and every eligible file is re-read, so ``indexed`` reflects the files
    actually read rather than reporting 0 work on an already-current index. A
    rebuild is also the recovery path for a corrupt or schema-mismatched DB: the
    bad derived artifact is replaced with a fresh one (a delete loses nothing —
    the corpus is the source of truth; see module docstring). An incremental
    reindex cannot recover that way; it would keep reading the bad file.

    The live-write guard applies either way: a file whose mtime is within
    ``live_grace_seconds`` of ``now`` is skipped even on a full rebuild, so a
    half-flushed live transcript is never read (the 2026-08-06 ~20 GB dedup miss
    was exactly that mistake).

    Scans ``corpus_dir`` for ``*.jsonl``, and for each file:
      - skips it if its mtime is within ``live_grace_seconds`` of ``now`` (the
        live session is still writing it);
      - skips it if ``(mtime, size)`` matches what is already indexed (no work —
        unless ``full`` dropped the index, in which case nothing matches);
      - otherwise deletes that file's rows and re-parses it.

    Files that no longer exist on disk are pruned from the index. Returns a
    counts dict so callers (and tests) can prove what actually happened rather
    than trust silence — "no work" is ``indexed == 0`` on a second incremental
    call.
    """
    corpus_dir = Path(corpus_dir or DEFAULT_CORPUS)
    index_path = Path(index_path or DEFAULT_INDEX)
    now = time.time() if now is None else float(now)
    live_cutoff = now - live_grace_seconds

    if full:
        _drop_index(index_path)

    conn = _open(index_path)
    try:
        conn.executescript(_SCHEMA)
        known = {
            r["path"]: (r["mtime"], r["size"])
            for r in conn.execute("SELECT path, mtime, size FROM files")
        }

        scanned = indexed = unchanged = skipped_live = 0
        on_disk: set[str] = set()
        for jf in sorted(corpus_dir.glob("*.jsonl")):
            scanned += 1
            on_disk.add(jf.name)
            try:
                st = jf.stat()
            except OSError:
                continue
            mtime, size = st.st_mtime, st.st_size

            if mtime > live_cutoff:
                # Still being written (or just was). Leave any prior snapshot
                # indexed; the tail lands once the session goes quiet.
                skipped_live += 1
                continue

            if known.get(jf.name) == (mtime, size):
                unchanged += 1
                continue

            # (Re)index this file: drop its old rows first, then re-parse.
            conn.execute("DELETE FROM transcripts WHERE path = ?", (jf.name,))
            first_ts: str | None = None
            sid = jf.stem
            batch = []
            for ts, s, text in _iter_message_text(jf):
                batch.append((jf.name, s, ts, text))
                if first_ts is None:
                    first_ts = ts
                sid = s or sid
            if batch:
                conn.executemany(
                    "INSERT INTO transcripts (path, session_id, date, text) "
                    "VALUES (?, ?, ?, ?)",
                    batch,
                )
            conn.execute(
                """INSERT INTO files (path, mtime, size, session_id, first_ts, indexed_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(path) DO UPDATE SET
                       mtime=excluded.mtime, size=excluded.size,
                       session_id=excluded.session_id, first_ts=excluded.first_ts,
                       indexed_at=excluded.indexed_at""",
                (jf.name, mtime, size, sid, first_ts, _now_iso()),
            )
            indexed += 1

        # Prune index entries for files that have vanished from the corpus.
        pruned = 0
        for stale in set(known) - on_disk:
            conn.execute("DELETE FROM transcripts WHERE path = ?", (stale,))
            conn.execute("DELETE FROM files WHERE path = ?", (stale,))
            pruned += 1

        conn.commit()
        return {
            "scanned": scanned,
            "indexed": indexed,        # files actually (re)parsed
            "unchanged": unchanged,    # files already current — no work
            "skipped_live": skipped_live,
            "pruned": pruned,
        }
    finally:
        conn.close()


def _build_match(query: str) -> str:
    """Turn a free-text query into a safe FTS5 MATCH expression.

    FTS5's default join is AND over space-separated tokens, and a double-quoted
    token is a string literal (no wildcard / operator interpretation), so we
    split the query on alphanumerics — mirroring the unicode61 tokeniser — and
    quote each piece. ``higgsfield`` -> ``"higgsfield"``;
    ``self_repo_guard`` -> ``"self" "repo" "guard"`` (AND). Returns "" for an
    all-noise query, which the caller treats as "no search".
    """
    seen: set[str] = set()
    out: list[str] = []
    for tok in _QUERY_TOKEN_RE.findall((query or "").lower()):
        if tok not in seen:
            seen.add(tok)
            out.append(f'"{tok}"')
    return " ".join(out)


def search(
    query: str,
    limit: int = 5,
    *,
    corpus_dir: str | Path | None = None,
    index_path: str | Path | None = None,
    now: float | None = None,
) -> list[dict]:
    """Search past transcripts for ``query``. Returns up to ``limit`` hits,
    each ``{session_id, date, snippet}``, best FTS5 rank first.

    Refreshes the index (incrementally) first, so new sessions are findable
    without a manual rebuild. An empty/noise query returns ``[]`` without
    touching the index.
    """
    match = _build_match(query)
    if not match:
        return []

    reindex(corpus_dir, index_path, now=now)
    index_path = Path(index_path or DEFAULT_INDEX)
    conn = _open(index_path)
    try:
        # snippet(transcripts, <text-col-index=3>, start, end, ellipsis, tokens)
        rows = conn.execute(
            "SELECT session_id, date, "
            "       snippet(transcripts, 3, '>>', '<<', ' … ', 10) AS snippet, "
            "       rank "
            "FROM transcripts WHERE transcripts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (match, limit),
        ).fetchall()
        return [
            {"session_id": r["session_id"], "date": r["date"], "snippet": r["snippet"]}
            for r in rows
        ]
    finally:
        conn.close()


def _cli() -> int:
    """``python -m lib.session_search <query> [--limit N]`` builds the index
    (incrementally) and prints results.

    ``--rebuild`` drops the index and re-indexes the whole corpus from scratch,
    then prints the report — the path to run when the FTS5 schema changed or the
    index is corrupt. ``--reindex`` runs the incremental path and prints its
    report. The flags do what they say: a rebuild shows ``indexed`` equal to the
    files it actually read (not 0), while an incremental reindex over an
    already-current corpus shows ``indexed: 0``.
    """
    import sys

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("usage: python -m lib.session_search <query> [--limit N]")
        print("       python -m lib.session_search --rebuild    # drop + re-index all")
        print("       python -m lib.session_search --reindex    # incremental only")
        print("       index: " + str(DEFAULT_INDEX))
        print("       corpus: " + str(DEFAULT_CORPUS))
        return 0

    if args[0] in ("--rebuild", "--reindex"):
        full = args[0] == "--rebuild"
        label = "rebuild" if full else "reindex"
        t0 = time.time()
        report = reindex(full=full)
        dt = time.time() - t0
        size = DEFAULT_INDEX.stat().st_size if DEFAULT_INDEX.exists() else 0
        print(f"{label}: {report} in {dt:.1f}s; index {size} bytes")
        return 0

    limit = 5
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        else:
            rest.append(args[i])
            i += 1
    query = " ".join(rest)
    hits = search(query, limit=limit)
    if not hits:
        print(f'no matches: "{query}"')
        return 0
    print(f'{len(hits)} match(es) for "{query}":')
    for h in hits:
        print(f'- [{h["date"]}] {h["session_id"]}')
        print(f'    {h["snippet"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
