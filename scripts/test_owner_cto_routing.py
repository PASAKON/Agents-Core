"""End-to-end smoke for multi-CTO routing.

Verifies:
  1. owner_cto column exists + is settable on create_task.
  1b. create_task falls back to CXO_SESSION_ID+CXO_ROLE env (issue #15).
  2. list_tasks(owner_cto=) filter works.
  3. _is_mine / _foreign_msg gate cross-CTO mutations in cto_mcp_server.
  4. send_to_cto accepts cto_id kwarg without raising.
  5. notify._append_cto_log writes to per-CTO file when env set.
  6. hook-log-dev-reply._log_for picks per-CTO path.

Inserts synthetic rows (owner_cto = ctoaaaaa / ctobbbbb), deletes on exit.
Run via:   python scripts/test_owner_cto_routing.py
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db, cto_session, notify  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {msg}")


def _cleanup(task_ids: list[str]) -> None:
    if not task_ids:
        return
    conn = sqlite3.connect(str(db.DB_PATH))
    try:
        placeholders = ",".join("?" * len(task_ids))
        conn.execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", task_ids)
        conn.execute(f"DELETE FROM events WHERE task_id IN ({placeholders})", task_ids)
        conn.commit()
    finally:
        conn.close()


def test_db_column() -> bool:
    cols = {r[1] for r in sqlite3.connect(str(db.DB_PATH))
            .execute("PRAGMA table_info(tasks)").fetchall()}
    return "owner_cto" in cols


def test_create_and_filter() -> tuple[bool, list[str]]:
    cto_a = "ctoaaaaa"
    cto_b = "ctobbbbb"
    t1 = db.create_task("mooniex-claudeflow", "developer",
                        "smoke A1", "test", owner_cto=cto_a)
    t2 = db.create_task("mooniex-claudeflow", "developer",
                        "smoke A2", "test", owner_cto=cto_a)
    t3 = db.create_task("mooniex-claudeflow", "developer",
                        "smoke B1", "test", owner_cto=cto_b)
    tids = [t1, t2, t3]
    rows_a = db.list_tasks(owner_cto=cto_a)
    rows_b = db.list_tasks(owner_cto=cto_b)
    a_ids = {r["id"] for r in rows_a}
    b_ids = {r["id"] for r in rows_b}
    ok = (t1 in a_ids and t2 in a_ids and t3 not in a_ids
          and t3 in b_ids and t1 not in b_ids)
    return ok, tids


def test_create_with_cxo_env() -> bool:
    """A non-CTO C-level session exports only CXO_SESSION_ID + CXO_ROLE.
    create_task must fall back to those and stamp owner_cto + owner_role so
    CFO/CMO-spawned tasks are no longer ownerless (issue #15)."""
    saved = {k: os.environ.get(k) for k in
             ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE")}
    os.environ.pop("CTO_SESSION_ID", None)  # CXO session has no CTO_SESSION_ID
    os.environ["CXO_SESSION_ID"] = "cfo01234"
    os.environ["CXO_ROLE"] = "cfo"
    tid = None
    try:
        tid = db.create_task("mooniex-claudeflow", "data_analyst",
                             "cxo-env smoke", "test")
        row = db.get_task(tid)
        ok = (row is not None
              and row["owner_cto"] == "cfo01234"
              and row["owner_role"] == "cfo")
    finally:
        if tid:
            _cleanup([tid])
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return ok


def test_cross_cto_gate(tids: list[str]) -> bool:
    os.environ["CTO_SESSION_ID"] = "ctoaaaaa"
    from runners import cto_mcp_server as srv  # noqa: WPS433
    t_a = db.get_task(tids[0])
    t_b = db.get_task(tids[2])
    msg = srv._foreign_msg(t_b)
    ok = ("Refusing cross-CTO" in msg
          and not srv._is_mine(t_b)
          and srv._is_mine(t_a))
    del os.environ["CTO_SESSION_ID"]
    return ok


def test_cto_py_delegate_merge_reopen_gate(tids: list[str]) -> bool:
    """W2: cto.py's t_delegate/t_merge/t_reopen previously called the
    underlying mutation ops with no ownership check at all (unlike
    cto_mcp_server.py's delegate_task/merge_task/reopen_task). Same
    ownership-violation setup as test_cross_cto_gate, but drives the
    actual tool handlers cto_chat.py's REPL (and main.py's one-shot mode)
    wire up, and confirms the foreign task was left untouched."""
    import asyncio
    from runners import cto  # noqa: WPS433

    os.environ["CTO_SESSION_ID"] = "ctoaaaaa"
    t_b_id = tids[2]  # owned by ctobbbbb
    before = db.get_task(t_b_id)

    async def _run():
        d = await cto.t_delegate.handler({"task_id": t_b_id})
        m = await cto.t_merge.handler({"task_id": t_b_id})
        r = await cto.t_reopen.handler({"task_id": t_b_id, "feedback": "x"})
        return d, m, r

    try:
        d_res, m_res, r_res = asyncio.run(_run())
    finally:
        del os.environ["CTO_SESSION_ID"]

    after = db.get_task(t_b_id)

    def _text(res: dict) -> str:
        return res["content"][0]["text"]

    return (
        "Refusing cross-CTO" in _text(d_res)
        and "Refusing cross-CTO" in _text(m_res)
        and "Refusing cross-CTO" in _text(r_res)
        and after["status"] == before["status"]
        and after["iteration"] == before["iteration"]
    )


def test_send_to_cto_kwarg() -> bool:
    from tools import send_to_cto
    # No iTerm in test env — just confirm signature + constant.
    assert send_to_cto.CTO_TAB_FALLBACK_MATCH == "CTO Chat"
    sig = send_to_cto.send.__code__.co_varnames[:4]
    return "cto_id" in sig


def test_per_cto_log() -> bool:
    cto_id = "smoketst"
    os.environ["CTO_SESSION_ID"] = cto_id
    os.environ["CTO_SESSION"] = "1"
    target = ROOT / "state" / "logs" / f"cto-{cto_id}.log"
    if target.exists():
        target.unlink()
    notify.info("smoke ping")
    ok = target.exists() and "smoke ping" in target.read_text()
    if target.exists():
        target.unlink()
    del os.environ["CTO_SESSION"]
    del os.environ["CTO_SESSION_ID"]
    return ok


def test_hook_log_path() -> bool:
    spec = importlib.util.spec_from_file_location(
        "hook_log_dev_reply",
        ROOT / "scripts" / "hook-log-dev-reply.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    p = mod._log_for("abcd1234")
    return p.name == "cto-abcd1234.log" and mod._log_for(None).name == "cto.log"


def main() -> int:
    db.init()
    created: list[str] = []
    fails = 0
    try:
        r = test_db_column(); fails += not r
        _mark(r, "owner_cto column present")

        r, created = test_create_and_filter(); fails += not r
        _mark(r, "list_tasks(owner_cto=) filters")

        r = test_create_with_cxo_env(); fails += not r
        _mark(r, "create_task stamps owner_cto+owner_role from CXO_* env")

        r = test_cross_cto_gate(created); fails += not r
        _mark(r, "_is_mine + _foreign_msg gate cross-CTO mutation")

        r = test_cto_py_delegate_merge_reopen_gate(created); fails += not r
        _mark(r, "cto.py t_delegate/t_merge/t_reopen gate cross-CTO mutation")

        r = test_send_to_cto_kwarg(); fails += not r
        _mark(r, "send_to_cto.send accepts cto_id kwarg")

        r = test_per_cto_log(); fails += not r
        _mark(r, "notify._append_cto_log writes per-CTO file")

        r = test_hook_log_path(); fails += not r
        _mark(r, "hook-log-dev-reply._log_for picks per-CTO path")
    finally:
        _cleanup(created)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
