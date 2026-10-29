"""Read-only SafeRestart planner; never executes a suggested action.

Run on the selected host (Contabo: bash scripts/hub/org-python.sh -m
tools.restart_plan --host contabo). Only the output JSON is written.
in_turn is a heuristic: the last conversational entry is a user/tool_result
or an assistant with stop_reason=tool_use, younger than 15 minutes. Metadata
entries do not finish a turn. This cannot prove that an external operation ended.
Costs are in millions of tokens: C is divided by 1e6 before the equations.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.live_sessions import session_dirs, read_registry, is_alive
from lib import roles

UTC = timezone.utc
RUN_CARDS_TIMEOUT_S = 30
ACTIONS = {'wait', 'close', 'park', 'resume_lazy', 'resume_full', 'compact_then_resume'}
OPEN = {'pending', 'in_progress', 'rate_limited'}


def timestamp(value):
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def tail_entries(path, chunk_size=65536):
    """Yield JSON objects newest first, seeking in chunks; cap single lines at 8MiB.

    Oversized or malformed records are skipped, never buffered without a bound.
    """
    with Path(path).open('rb') as stream:
        pos = stream.seek(0, 2)
        carry = b''
        dropping = False
        while pos:
            size = min(pos, chunk_size)
            pos -= size
            stream.seek(pos)
            pieces = stream.read(size).split(b'\n')
            pieces[-1] += carry
            for line in reversed(pieces[1:]):
                if not dropping:
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            yield obj
                    except (ValueError, UnicodeDecodeError):
                        pass
                dropping = False
            carry = pieces[0]
            if len(carry) > 8 * 1024 * 1024:
                carry = b''
                dropping = True
        if carry and not dropping:
            try:
                obj = json.loads(carry)
                if isinstance(obj, dict):
                    yield obj
            except (ValueError, UnicodeDecodeError):
                pass


def measure(path, now):
    result = {'C': None, 'last_active': None, 'in_turn': False}
    last = None
    request_id = None
    for entry in tail_entries(path):
        kind = entry.get('type')
        if kind in ('user', 'assistant') and last is None:
            last = entry
            dt = timestamp(entry.get('timestamp'))
            result['last_active'] = dt.isoformat() if dt else None
            msg = entry.get('message') or {}
            working = kind == 'user' or msg.get('stop_reason') == 'tool_use'
            result['in_turn'] = bool(working and dt and timedelta(0) <= now - dt < timedelta(minutes=15))
        if kind == 'system' and entry.get('subtype') == 'compact_boundary':
            if result['C'] is None:
                result['C'] = 110000
            if last is not None:
                break
            continue
        if kind == 'assistant':
            msg = entry.get('message') or {}
            mid = msg.get('id')
            if request_id is not None and mid != request_id:
                break
            request_id = mid
            usage = msg.get('usage')
            if result['C'] is None and isinstance(usage, dict):
                result['C'] = sum(usage.get(k, 0) or 0 for k in
                                  ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
            # Duplicate content blocks are one request, never summed.
            if result['C'] is not None and last is not None:
                break
    return result


def recent(row, now):
    dt = timestamp(row.get('last_active'))
    return dt is not None and now - dt <= timedelta(minutes=60)


def decide(row, now):
    """Pure policy, including explicit override and conservative unknown data."""
    if row.get('override') in ACTIONS:
        return row['override'], 'explicit override'
    if row.get('in_turn'):
        return 'wait', f"still working: {row['name']}"
    if row.get('status') == 'closed':
        return 'close', 'session marked done'
    # Not 'saved': a live session keeps that hub status from its last /session-save after
    # it was resumed (CMO Main and most PHs on Contabo, 29 Oct), so it says nothing now.
    if row.get('parked') or row.get('status') == 'parked':
        return 'park', 'session explicitly parked'
    if row.get('incomplete'):
        return 'wait', 'incomplete evidence; inspect warnings'
    tasks = row.get('open_tasks', [])
    work = any(t.get('kind', 'task') == 'task' for t in tasks)
    if not work and (row.get('only_waiting_on_ceo') or not row.get('charter')):
        if (not tasks and row.get('live') and
                row.get('role') in (*roles.c_level_roles(), roles.PH_ROLE)):
            return 'resume_lazy', 'live leadership session without charter or task'
        return 'park', 'only waiting on a CEO card' if tasks else 'no open charter or task'
    if not recent(row, now):
        return 'resume_lazy', 'has work; idle more than 60 minutes'
    if row['C'] <= 140000:
        return 'resume_full', 'has work; active within 60 minutes; C <= 140000'
    return 'compact_then_resume', 'has work; active within 60 minutes; C > 140000'


def load_overrides(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or any(not re.fullmatch('[0-9a-f]{8}', k) or v not in ACTIONS
                                         for k, v in data.items()):
        raise ValueError('invalid restart overrides')
    return data


def read_hub():
    """SELECT only; no init/migrations. Optional tables are discovered first."""
    from lib import db
    with db.get_conn(readonly=True, timeout=3) as conn:
        tables = {r['name'] for r in conn.execute(
            "SELECT table_name AS name FROM information_schema.tables WHERE table_schema=current_schema()"
            ).fetchall()} if db.pg_url() else {r['name'] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        result = {}
        for table in ('tasks', 'c_level_sessions', 'run_cards', 'question_cards', 'cards', 'questions',
                      'paid_generations', 'generations', 'merges'):
            if table in tables:
                result[table] = [dict(r) for r in conn.execute(f'SELECT * FROM {table}').fetchall()]
        if not {'tasks', 'c_level_sessions'} <= result.keys():
            raise RuntimeError('required hub tables unavailable')
        return result


def read_running_cards():
    """Run cards the Console is executing now, or None when they cannot be read.

    They live in the Console hub, not the org hub: tools/ask_run.py asks
    /api/run/asks. mooniex-console.service runs them, so a restart kills one.
    """
    env = dict(os.environ)
    env.setdefault('HOME', '/root')
    try:
        done = subprocess.run(
            ['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', 'list', '--status', 'running', '--json'],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=RUN_CARDS_TIMEOUT_S)
        if done.returncode:
            return None
        cards = json.loads(done.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return cards if isinstance(cards, list) and all(isinstance(c, dict) for c in cards) else None


def owned(item, row):
    return any(item.get(k) in (row['session_id'], row['uuid']) for k in
               ('owner_cto', 'creator_session_id', 'owner_session_id', 'from_session_id', 'raised_by', 'creator', 'owner'))


def build_plan(host, now, out_dir):
    from lib import config
    if config.self_host() != host:
        raise ValueError('run this command on the selected host; local PIDs cannot verify a remote host')
    warnings = []
    try:
        hub = read_hub()
    except Exception:
        hub = None
        warnings.append('Hub unavailable; ownership, cards, paid generations and merges cannot be verified.')
    overrides = load_overrides(out_dir / 'overrides.json')
    dirs = session_dirs(host)
    rows = []
    live_rows = read_registry(dirs)
    if not live_rows:
        warnings.append('No live registry sessions visible; this is not proof the host is safe to restart.')
    for live in live_rows:
        row = {k: live[k] for k in ('role', 'name', 'uuid')}
        sid = live['sid']
        row['session_id'] = sid if re.fullmatch('[0-9a-f]{8}', sid) else live['uuid'][-8:]
        row['live'] = True  # read_registry includes only live local processes
        pane = f"{row['role']}-{row['session_id']}"
        row['parked'] = any((ROOT / 'state/locks' / f'{pane}.{suffix}.parked').exists()
                            for suffix in ('project', 'spawned_by'))
        paths = [p for d in dirs for p in (d.parent / 'projects').glob(f"*/{live['uuid']}.jsonl")]
        row.update(transcript_path=str(paths[0]) if paths else None, C=None,
                   last_active=None, in_turn=False, open_tasks=[], charter=None, status=None)
        try:
            if len(paths) != 1:
                raise ValueError('missing or ambiguous transcript')
            row.update(measure(paths[0], now))
        except (OSError, ValueError, TypeError):
            warnings.append(f"{row['session_id']}: transcript unavailable or invalid")
        row['incomplete'] = hub is None or row['C'] is None or row['last_active'] is None
        if hub:
            for session in hub['c_level_sessions']:
                if session.get('session_id') == row['session_id'] and session.get('role') == row['role']:
                    row.update(status=session.get('status'), charter=session.get('charter'))
            for table, items in hub.items():
                if table in ('c_level_sessions', 'paid_generations', 'generations', 'merges'):
                    continue
                for item in items:
                    if owned(item, row) and item.get('status') in OPEN:
                        row['open_tasks'].append({'id': item.get('id'), 'status': item['status'],
                                                  'kind': 'task' if table == 'tasks' else 'ceo_card'})
            row['only_waiting_on_ceo'] = bool(row['open_tasks']) and all(
                t['kind'] == 'ceo_card' for t in row['open_tasks'])
        row['override'] = overrides.get(row['session_id'])
        row['action'], row['reason'] = decide(row, now)
        c = (row['C'] or 0) / 1e6
        row['est_cost_M'] = {'resume_full': 2*c, 'compact_then_resume': .1*c+.05+.22,
                             'park': .03}.get(row['action'], 0)
        rows.append(row)
    workers = []
    for table, items in (hub or {}).items():
        for item in items:
            if item.get('host') and item['host'] != host:
                continue
            if (item.get('host') or item.get('dispatcher_host')) == host and item.get('runner') in ('codex', 'agy') and item.get('pid'):
                if is_alive(int(item['pid'])):
                    workers.append({k: item.get(k) for k in ('id', 'runner', 'pid', 'status')})
            if item.get('status') in ('running', 'in_progress', 'merging', 'generating'):
                warnings.append(f"Do not cut: {table} {item.get('id', '?')} ({item['status']})")
    if workers:
        warnings.append('Do not cut: worker processes are still running.')
    cards = read_running_cards()
    if cards is None:
        warnings.append('Run cards unavailable; a running card cannot be ruled out.')
    for card in cards or []:
        warnings.append(f"Do not cut: run card {card.get('id', '?')} (running)")
    return {'host': host, 'generated_at': now.isoformat(), 'sessions': rows,
            'running_workers': workers, 'warnings': warnings,
            'extra_cost_M': sum(1.9*(r['C'] or 0)/1e6 for r in rows if recent(r, now))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, choices=('contabo', 'mac', 'winbox'))
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--now')
    parser.add_argument('--out-dir', type=Path, default=Path('state/restart'))
    args = parser.parse_args(argv)
    now = timestamp(args.now) if args.now else datetime.now(UTC)
    if now is None:
        parser.error('--now must be an ISO timestamp')
    try:
        plan = build_plan(args.host, now, args.out_dir)
        encoded = json.dumps(plan, indent=2) + '\n'
        args.out_dir.mkdir(parents=True, exist_ok=True)
        output = args.out_dir / f"{args.host}-{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"
        with output.open('x') as stream:
            stream.write(encoded)
    except (OSError, ValueError, RuntimeError):
        parser.exit(1, 'restart plan failed; check host, overrides and output permissions\n')
    if args.json:
        print(encoded, end='')
    else:
        print('SESSION   ROLE             C       ACTION                 REASON')
        for row in plan['sessions']:
            print(f"{row['session_id']:8}  {row['role']:15}  {str(row['C']):7} {row['action']:22} {row['reason']}")
        for warning in plan['warnings']:
            print(f'WARNING: {warning}')
        print(f'Output: {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
