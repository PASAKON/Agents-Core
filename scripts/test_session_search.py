"""Tests for lib.session_search — FTS5 over past session transcripts (ADR 0019 §2).

pytest style, tmp_path fixtures only (ADR 0021 §1). Builds synthetic .jsonl
corpora under tmp_path; never touches the real ~/.claude/projects/, never
writes state/session-search.db, never touches output/. A full run leaves the
worktree's state/ and output/ byte-identical.

The clock is fixed (NOW) and fixture mtimes are set relative to it via os.utime,
so the live-write grace window is exercised deterministically — no real-time
dependency, no flake.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import session_search as ss  # noqa: E402

# Fixed "now". Fixture mtimes are NOW - <age>; the live-write grace window is
# 120s, so anything with age < 120 is treated as still being written.
NOW = 1_700_000_000.0


def _msg(rtype: str, role: str, text: str, *, ts: str = "2026-08-01T10:00:00Z",
         sid: str = "s") -> str:
    return json.dumps({
        "type": rtype,
        "timestamp": ts,
        "sessionId": sid,
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    })


def _write(corpus: Path, name: str, lines: list[str]) -> Path:
    p = corpus / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _age(path: Path, seconds: float) -> Path:
    """Force a file's mtime to NOW - seconds (deterministic, independent of the
    real clock). Returns the path so it chains: ``_age(_write(...), n)``."""
    os.utime(path, (NOW - seconds, NOW - seconds))
    return path


def test_found_and_absent(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    idx = tmp_path / "idx.db"
    _age(_write(corpus, "aaa.jsonl", [
        _msg("user", "user", "we discussed the higgsfield unlimited gen skill"),
        _msg("assistant", "assistant", "right, higgsfield is rerun-banned recreate-only",
             ts="2026-08-01T10:01:00Z"),
    ]), 10_000)

    hits = ss.search("higgsfield", corpus_dir=corpus, index_path=idx, now=NOW)
    assert hits, "a term present in a fixture transcript must be found"
    assert {"session_id", "date", "snippet"} <= set(hits[0])
    assert "higgsfield" in hits[0]["snippet"].lower()

    assert ss.search("zzznotpresentterm", corpus_dir=corpus, index_path=idx, now=NOW) == []
    assert ss.search("", corpus_dir=corpus, index_path=idx, now=NOW) == []
    assert ss.search("!!!", corpus_dir=corpus, index_path=idx, now=NOW) == []


def test_no_change_does_no_work(tmp_path: Path) -> None:
    """A second reindex with nothing changed must do NO work — assert it, not
    just claim it (ADR 0021 §1)."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    idx = tmp_path / "idx.db"
    _age(_write(corpus, "a.jsonl", [_msg("user", "user", "alpha higgsfield")]), 10_000)

    first = ss.reindex(corpus, idx, now=NOW)
    assert first["indexed"] == 1, first

    second = ss.reindex(corpus, idx, now=NOW)
    assert second["indexed"] == 0, second          # no file re-parsed
    assert second["unchanged"] == 1, second        # the file was already current
    assert second["skipped_live"] == 0, second


def test_incremental_picks_up_change(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    idx = tmp_path / "idx.db"
    p = _age(_write(corpus, "b.jsonl", [_msg("user", "user", "original content only")]), 10_000)
    ss.reindex(corpus, idx, now=NOW)
    assert ss.search("newtermlater", corpus_dir=corpus, index_path=idx, now=NOW) == []

    # Append a message carrying a new term + bump mtime/size -> must re-index.
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(_msg("assistant", "assistant", "the newtermlater appeared",
                      ts="2026-08-02T10:00:00Z") + "\n")
    _age(p, 5_000)  # still older than the grace window, but a new (mtime,size)

    r = ss.reindex(corpus, idx, now=NOW)
    assert r["indexed"] == 1, r
    hits = ss.search("newtermlater", corpus_dir=corpus, index_path=idx, now=NOW)
    assert hits and "newtermlater" in hits[0]["snippet"].lower()


def test_live_write_is_skipped(tmp_path: Path) -> None:
    """A file whose mtime is within the grace window of `now` is treated as
    still being written and skipped — the exact guard against indexing a
    half-flushed live transcript (ADR 0019 §2, citing the 2026-08-06 miss)."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    idx = tmp_path / "idx.db"
    live = _write(corpus, "live.jsonl", [_msg("user", "user", "uniqueliveterm here")])
    cold = _write(corpus, "cold.jsonl", [_msg("user", "user", "coldterm here")])
    _age(live, 10)       # 10s ago -> within 120s grace -> skipped
    _age(cold, 10_000)   # old -> indexed

    r = ss.reindex(corpus, idx, now=NOW)
    assert r["skipped_live"] == 1, r
    assert r["indexed"] == 1, r
    # The live file's unique term is NOT findable (it was skipped).
    assert ss.search("uniqueliveterm", corpus_dir=corpus, index_path=idx, now=NOW) == []
    # The cold file's term IS findable.
    hits = ss.search("coldterm", corpus_dir=corpus, index_path=idx, now=NOW)
    assert hits and "coldterm" in hits[0]["snippet"].lower()


def test_corrupt_line_does_not_crash(tmp_path: Path) -> None:
    """A truncated/garbled JSONL line must be skipped, not crash the indexer;
    well-formed lines around it are still indexed."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    idx = tmp_path / "idx.db"
    good1 = _msg("user", "user", "goodkeepsterm one")
    good2 = _msg("assistant", "assistant", "goodkeepsterm two",
                 ts="2026-08-01T10:01:00Z")
    # Middle line is not valid JSON (mimics a half-flushed tail write).
    p = corpus / "c.jsonl"
    p.write_text(good1 + "\n{this is not valid json\n" + good2 + "\n", encoding="utf-8")
    _age(p, 10_000)

    r = ss.reindex(corpus, idx, now=NOW)   # must not raise
    assert r["indexed"] == 1, r
    hits = ss.search("goodkeepsterm", corpus_dir=corpus, index_path=idx, now=NOW)
    assert hits, "good lines around a corrupt one must still be indexed"


def test_prunes_deleted_file(tmp_path: Path) -> None:
    """A file removed from the corpus is pruned from the index — derived
    artifact stays consistent with its source."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    idx = tmp_path / "idx.db"
    gone = _age(_write(corpus, "gone.jsonl", [_msg("user", "user", "ghostterm")]), 10_000)
    ss.reindex(corpus, idx, now=NOW)
    assert ss.search("ghostterm", corpus_dir=corpus, index_path=idx, now=NOW)

    gone.unlink()
    r = ss.reindex(corpus, idx, now=NOW)
    assert r["pruned"] == 1, r
    assert ss.search("ghostterm", corpus_dir=corpus, index_path=idx, now=NOW) == []
