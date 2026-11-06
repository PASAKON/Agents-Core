"""Model-free PH telemetry. Production writers use the shared ORG_DB_URL hub.

The turn wrapper is deliberately runner-agnostic; a new brain must use it too.
Only the originating host may probe a PID. Watch never probes remote PIDs.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import hashlib
import time
import uuid

from lib import db

SCHEMA = db.PH_STATE_SCHEMA
ICONS = {"thinking": "🧠", "waiting": "⏳", "idle": "💤", "silent": "🔴"}


def init():
    with db.get_conn() as conn:
        conn.execute(SCHEMA)


def host_name():
    from lib.config import self_host
    return self_host()


def require_hub():
    if not db.pg_url():
        raise db.HubUnavailable('PH telemetry requires ORG_DB_URL; refusing a local split-brain')


@contextmanager
def turn(*, session_id, project, brain, model, doing, owner, lane, host=None):
    """Record before invoking any runner, and on every exit including exceptions.

    PID is the supervising turn process: it owns the synchronous brain call.
    Refuse to start an unrecorded production turn if the hub is unavailable.
    """
    host = host or host_name()
    require_hub()
    init()
    token, now = uuid.uuid4().hex, time.time()
    with db.get_conn() as conn:
        conn.execute("""INSERT INTO ph_state
            (session_id,host,project,brain,model,doing,owner,lane,turn_id,pid,
             started,updated,ended,exit_code,phase,wait_ref,alerted)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,'thinking',NULL,0)
            ON CONFLICT(session_id,host) DO UPDATE SET
            project=excluded.project,brain=excluded.brain,model=excluded.model,
            doing=excluded.doing,owner=excluded.owner,lane=excluded.lane,
            turn_id=excluded.turn_id,pid=excluded.pid,started=excluded.started,
            updated=excluded.updated,ended=NULL,exit_code=NULL,phase='thinking',
            wait_ref=NULL,alerted=0""",
            (session_id, host, project, brain, model, " ".join(doing.split())[:160],
             owner or f"{lane}-main", lane, token, os.getpid(), now, now))
    result = {"returncode": 1}
    try:
        yield result
    finally:
        now = time.time()
        with db.get_conn() as conn:
            conn.execute("""UPDATE ph_state SET ended=?,updated=?,exit_code=?,
                phase='idle',pid=NULL WHERE session_id=? AND host=? AND turn_id=?""",
                (now, now, result.get("returncode"), session_id, host, token))


def pid_alive(pid):
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def phase(row, *, now, local_host=None, alive=pid_alive):
    if row["phase"] == "thinking":
        if now - row["updated"] > 600:
            return "silent"
        if row.get('brain') != 'claude-native' and row["host"] == local_host and not alive(row["pid"]):
            return "silent"
    return row["phase"]


def pane_phase(screen):
    from lib.pane_screen import pane_busy, pane_waiting, prompt_ready
    if pane_waiting(screen):
        return "waiting"
    if pane_busy(screen):
        return "thinking"
    return "idle" if prompt_ready(screen) else None


def wait(session_id, reference, *, host=None):
    """Explicit task/card wait; the reference is checked by the observer."""
    with db.get_conn() as conn:
        conn.execute("""UPDATE ph_state SET phase='waiting',wait_ref=?,updated=?
            WHERE session_id=? AND host=? AND phase <> 'thinking'""",
            (reference, time.time(), session_id, host or host_name()))


def card_pending(reference):
    from tools import ask_run
    record = ask_run._unwrap(ask_run._call('GET', ask_run._record_path(reference)))
    terminal = (ask_run.GROUP_TERMINAL_STATES if reference.startswith('QG-') else
                ask_run.QUESTION_TERMINAL_STATES if reference.startswith('Q-') else
                ask_run.TERMINAL_STATES)
    return record.get('status') not in terminal


def observe(rows, *, now, local_host, tasks=(), pending_card=card_pending):
    """Reconcile task waits and local death, atomically enqueue one lane letter.

    A letter and its dedup bit commit together; the existing hub mail dispatcher
    delivers it. Never send to an arbitrary host inferred from a PID.
    """
    active = {t['owner_cto'] for t in tasks
              if t.get('owner_cto') and t.get('status') not in
              {'done', 'merged', 'failed', 'cancelled', 'reverted'}}
    for row in rows:
        state = phase(row, now=now, local_host=local_host)
        reference = str(row.get('wait_ref') or '')
        if row.get('brain') != 'claude-native' and state in ('idle', 'waiting'):
            card_wait = reference.startswith(('Q-', 'QG-', 'RUN-')) and pending_card(reference)
            state = 'waiting' if card_wait or row['session_id'] in active else 'idle'
        elif state == 'idle' and row['session_id'] in active:
            state = 'waiting'
        with db.get_conn() as conn:
            if state == 'silent':
                changed = conn.execute("""UPDATE ph_state SET alerted=1,phase='silent'
                    WHERE session_id=? AND host=? AND turn_id=? AND alerted=0
                    AND phase=? AND updated=?""",
                    (row['session_id'], row['host'], row['turn_id'], row['phase'], row['updated'])).rowcount
                if changed:
                    role, _, sid = row['owner'].partition('-')
                    owner = conn.execute("""SELECT host FROM c_level_sessions
                        WHERE role=? AND session_id=? AND status='open'""", (role, sid)).fetchone()
                    conn.execute("""INSERT INTO letters
                        (to_host,to_role,to_session,from_role,from_session,from_host,body,status,created_at)
                        VALUES (?,?,?,?,?,?,?,'pending',?)""",
                        ((owner['host'] if owner else None) or local_host, role,
                         sid or None, 'run_watch', local_host, local_host,
                         f"🔴 PH #{row['session_id']} {row['project']} · {row['host']}: brain silent or PID gone",
                         db.now_iso()))
            elif state != row['phase']:
                conn.execute("""UPDATE ph_state SET phase=?,updated=?,
                    wait_ref=CASE WHEN ?='idle' THEN NULL ELSE wait_ref END
                    WHERE session_id=? AND host=? AND turn_id=? AND phase=?""",
                    (state, now, state, row['session_id'], row['host'], row['turn_id'], row['phase']))
        row['phase'] = state
    return rows


def observe_native(session, screen, *, now):
    """A native Claude PH is sampled from its own pane, never renamed."""
    state = pane_phase(screen)
    if state is None:
        return
    sid, host = session['session_id'], session['host']
    with db.get_conn() as conn:
        conn.execute("""INSERT INTO ph_state
            (session_id,host,project,brain,model,doing,owner,lane,turn_id,
             started,updated,phase)
            VALUES (?,?,?,'claude-native','pane',? ,? ,? ,'native',?,?,?)
            ON CONFLICT(session_id,host) DO UPDATE SET
            phase=CASE WHEN ph_state.phase='silent' AND ph_state.doing=excluded.doing
                       AND excluded.phase='thinking' THEN 'silent' ELSE excluded.phase END,
            doing=excluded.doing,
            updated=CASE WHEN ph_state.phase <> excluded.phase OR ph_state.doing <> excluded.doing THEN excluded.updated
                         ELSE ph_state.updated END
            WHERE ph_state.brain='claude-native'""",
            (sid, host, session.get('project') or session.get('charter') or sid, hashlib.sha256(screen.encode()).hexdigest(),
             session.get('owner') or 'cto-main', session.get('lane') or 'cto', now, now, state))


def suffix(rows):
    return ' · PH ' + ' '.join(f"{ICONS[s]}{sum(r['phase'] == s for r in rows)}"
                              for s in ('thinking', 'waiting', 'silent'))


def signature(snapshot):
    """Ignore elapsed seconds: printing time alone must not create chatter."""
    return [bool(snapshot.get('error')), [
        [r.get(k) for k in ('session_id', 'project', 'host', 'phase')]
        for r in snapshot.get('rows', [])]]


def render(snapshot, *, now):
    if not snapshot or now - snapshot.get('at', 0) > 180:
        return '⚠️ Watch data older than 3 min'
    if snapshot.get('error'):
        return '⚠️ Watch hub unavailable'
    lines = []
    for row in snapshot.get('rows', []):
        age = max(0, int(now - row['updated']))
        project = ' '.join(row['project'].split())[:40]
        lines.append(f"{ICONS[row['phase']]} #{row['session_id'][:3]} {project} · {row['host']} · {age//60}:{age%60:02}")
    return '\n'.join(lines) or '💤 no PHs'
