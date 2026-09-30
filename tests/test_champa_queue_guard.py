"""Acceptance spec for the champa.io Unlimited runner (CEO 2026-10-01: test champa,
cheapest first; the plan is Seedance 2.0 Unlimited, 8 parallel queues).

Written by the CTO before the worker starts. The worker makes these pass and must
not edit this file; the merge gate checks that it is byte-identical to main.

Contract under test:
  scripts/champa/queue_guard.py
    is_free_label(label) -> bool
        True only when the submit label says Unlimited AND its last integer is 0
        ("ส่งเข้าคิว Unlimited 0"). Anything else (a price, no number, empty) is False.
    Refused(Exception)
    QueueGuard(max_in_flight, ledger)
        max_in_flight: int 1..8, else ValueError/TypeError
        check(label) -> None           Refused when the label is not free or
                                       in_flight() >= max_in_flight
        record_submit(clip_id, label)  one JSON line, event "submit"
        record_done(clip_id, path)     one JSON line, event "done"
        in_flight() -> int             submits without a done, read back from the ledger
        submitted_ids() -> set[str]
  scripts/champa/champa_fire.py
    main(argv) -> int                  --fire without --max-jobs, or --max-jobs outside
                                       1..8, returns 2 before any browser is touched
"""
import json

import pytest

qg = pytest.importorskip("scripts.champa.queue_guard")


@pytest.mark.parametrize("label", [
    "ส่งเข้าคิว Unlimited 0",
    "ส่งเข้าคิว Unlimited\n0",
    "Queue Unlimited 0",
])
def test_free_label(label):
    assert qg.is_free_label(label) is True


@pytest.mark.parametrize("label", [
    "",
    "ส่งเข้าคิว",
    "ส่งเข้าคิว Unlimited",
    "ส่งเข้าคิว 120",
    "ส่งเข้าคิว Unlimited 40",
    "สร้าง 60",
])
def test_not_free_label(label):
    assert qg.is_free_label(label) is False


def test_guard_needs_a_sane_cap(tmp_path):
    for bad in [0, 9, -1, None]:
        with pytest.raises((ValueError, TypeError)):
            qg.QueueGuard(bad, tmp_path / "q.jsonl")


def test_guard_refuses_a_priced_label(tmp_path):
    g = qg.QueueGuard(8, tmp_path / "q.jsonl")
    with pytest.raises(qg.Refused):
        g.check("ส่งเข้าคิว 120")


def test_guard_caps_jobs_in_flight(tmp_path):
    g = qg.QueueGuard(2, tmp_path / "q.jsonl")
    g.check("ส่งเข้าคิว Unlimited 0")
    g.record_submit("c1", "ส่งเข้าคิว Unlimited 0")
    g.record_submit("c2", "ส่งเข้าคิว Unlimited 0")
    assert g.in_flight() == 2
    with pytest.raises(qg.Refused):
        g.check("ส่งเข้าคิว Unlimited 0")
    g.record_done("c1", "/tmp/c1.mp4")
    assert g.in_flight() == 1
    g.check("ส่งเข้าคิว Unlimited 0")


def test_ledger_survives_a_restart(tmp_path):
    ledger = tmp_path / "q.jsonl"
    g = qg.QueueGuard(8, ledger)
    g.record_submit("c1", "ส่งเข้าคิว Unlimited 0")
    g.record_submit("c2", "ส่งเข้าคิว Unlimited 0")
    g.record_done("c1", "/tmp/c1.mp4")
    again = qg.QueueGuard(8, ledger)
    assert again.in_flight() == 1
    assert again.submitted_ids() == {"c1", "c2"}
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [(r["event"], r["clip_id"]) for r in rows] == [("submit", "c1"), ("submit", "c2"), ("done", "c1")]


def test_fire_without_a_job_cap_is_refused_before_any_browser(tmp_path):
    cf = pytest.importorskip("scripts.champa.champa_fire")
    prompts = tmp_path / "p.csv"
    prompts.write_text("clip_id,prompt\nc1,A quiet lake at sunrise\n", encoding="utf-8")
    base = ["--prompts", str(prompts), "--cdp", "http://127.0.0.1:1"]   # nothing listens on :1
    assert cf.main(base + ["--fire"]) == 2
    assert cf.main(base + ["--fire", "--max-jobs", "0"]) == 2
    assert cf.main(base + ["--fire", "--max-jobs", "9"]) == 2
