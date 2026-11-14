"""Shared queue storage. Errors propagate: never fall back to a local writer."""
import json
import os

from lib import db


def enabled():
    return os.environ.get("ORG_QUEUE_HUB") == "1"


def insert(conn, queue, entry):
    return conn.execute(
        "INSERT INTO org_queue(queue,task_id,payload,enqueued_at) VALUES (?,?,?,?) "
        "ON CONFLICT(queue,task_id) DO NOTHING",
        (queue, entry["task_id"], json.dumps(entry, ensure_ascii=False),
         entry.get("queued_at") or ""),
    ).rowcount


def load(queue):
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT payload FROM org_queue WHERE queue=? ORDER BY enqueued_at,task_id",
            (queue,),
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def enqueue(queue, entry, *, replace=False):
    with db.get_conn() as conn:
        if replace:
            conn.execute(
                "INSERT INTO org_queue(queue,task_id,payload,enqueued_at) VALUES (?,?,?,?) "
                "ON CONFLICT(queue,task_id) DO UPDATE SET "
                "payload=excluded.payload,enqueued_at=excluded.enqueued_at",
                (queue, entry["task_id"], json.dumps(entry, ensure_ascii=False), entry["queued_at"]),
            )
        else:
            insert(conn, queue, entry)
        rows = conn.execute(
            "SELECT task_id FROM org_queue WHERE queue=? ORDER BY enqueued_at,task_id",
            (queue,),
        ).fetchall()
        return next(i for i, row in enumerate(rows) if row["task_id"] == entry["task_id"])


def take(queue, task_id):
    """Atomically remove and return a row; concurrent drainers cannot both take it."""
    with db.get_conn() as conn:
        row = conn.execute(
            "DELETE FROM org_queue WHERE queue=? AND task_id=? RETURNING payload",
            (queue, task_id),
        ).fetchone()
    return json.loads(row["payload"]) if row else None
