"""Execute SafeRestart plans locally. This tool never reboots the host.

Exit 3 means the safety gate is still blocked; exit 1 means partial failure.
Run prep outside the sessions it closes (for example from the Run card worker).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import roles
from tools import live_sessions, restart_plan, session_status, tmux_session

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state/restart"
STALE_HOURS = 6
MESSAGE = "ระบบ restart เสร็จแล้ว ทำงานต่อจากเดิม"
SGR = re.compile(r"\x1b\[([0-9;]*)m")


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().strftime("%Y%m%dT%H%M%S%fZ")


def visible(text):
    """Remove ANSI styling and SGR-2 suggestions, preserving real input."""
    result, dim, start = [], False, 0
    for match in SGR.finditer(text):
        if not dim:
            result.append(text[start:match.start()])
        codes = iter(match[1].split(";"))
        for code in codes:
            if code in ('38', '48', '58'):
                # Extended colour payloads contain a literal 2 (RGB), which
                # is not the faint attribute. Consume the colour as a unit.
                mode = next(codes, '')
                for _ in range(3 if mode == '2' else 1):
                    next(codes, '')
                continue
            if code in ("", "0", "22"):
                dim = False
            elif code == "2":
                dim = True
        start = match.end()
    if not dim:
        result.append(text[start:])
    return "".join(result)


def empty_input(capture):
    """Require a visible prompt and no real text in its multiline input box."""
    lines = visible(capture).splitlines()
    prompts = [i for i, line in enumerate(lines) if line.lstrip().startswith("❯")]
    if not prompts:
        return False
    i = prompts[-1]
    if lines[i].lstrip()[1:].strip():
        return False
    for line in lines[i + 1:]:
        if re.fullmatch(r"\s*[─━—\-]{3,}\s*", line):
            break
        if line.strip():
            return False
    return True


def managed(row):
    return row.get("service_managed", False) or row["role"] == "coo"


def worker(row):
    """Workers belong to the task ledger: never typed into, killed or resumed here."""
    return (row.get('name', '').startswith('wd-') or
            (row["role"] != roles.PH_ROLE and row["role"] not in roles.c_level_roles()))


def identity(row):
    sid = row.get("sid", row.get("session_id"))
    role = row["role"]
    if not re.fullmatch(r"[0-9a-f]{8}", sid or "") or not re.fullmatch(r"[a-z][a-z_]{1,30}", role):
        raise ValueError("invalid session identity")
    return role, sid


def pane(row):
    role, sid = identity(row)
    return f"{role}-{sid}"


def run(command, dry=False):
    print(shlex.join(command))
    if not dry:
        subprocess.run(command, cwd=ROOT, check=True, timeout=300)


def send(row, text, dry=False):
    target = pane(row)
    if not dry and not empty_input(tmux_session.capture(target + ':0.0', escapes=True)):
        print(f"draft_or_not_ready: {row['name']}")
        return False
    # The shared typing primitive; its second Enter lands on an empty prompt.
    print(f"type into {target}:0.0: {text}")
    if not dry:
        tmux_session.send_keys(target + ':0.0', text)
    return True


def until(predicate, timeout):
    end = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        remaining = end - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(2, remaining))


def write_json(path, value, dry=False):
    if dry:
        print(f"write {path}: {json.dumps(value, ensure_ascii=False)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def blockers(plan):
    return ([r['name'] for r in plan['sessions'] if r['action'] == 'wait' and not managed(r)]
            + list(plan.get('warnings', [])))


def remeasure(plan):
    for row in plan['sessions']:
        if managed(row) or row['action'] != 'wait':
            continue
        try:
            row.update(restart_plan.measure(row['transcript_path'], now()))
            row['action'], row['reason'] = restart_plan.decide(row, now())
        except (OSError, ValueError, TypeError, KeyError):
            pass  # Unknown evidence remains blocked.


def boundary(row):
    path = row.get('transcript_path')
    if not path:
        return None
    try:
        for entry in restart_plan.tail_entries(path):
            if entry.get('subtype') == 'compact_boundary':
                return json.dumps(entry, sort_keys=True)
    except OSError:
        pass
    return None


def saved(row):
    if not tmux_session.has_session(pane(row)):
        return True
    role, sid = identity(row)
    record = session_status.get(role, sid)
    return bool(record and record.get('status') == 'saved')


GONE_WAIT_S = 60


def gone(row):
    """Wait until the saved pane is really closed. session-kill records 'saved'
    first and kills tmux a few seconds later; a resume that runs inside that gap
    sees the old pane, calls it already_live and never relaunches it (17 Oct 2026:
    0/6 came back)."""
    if until(lambda: not tmux_session.has_session(pane(row)), GONE_WAIT_S):
        return True
    subprocess.run([tmux_session.tmux_bin(), 'kill-session', '-t', pane(row)],
                   capture_output=True, text=True, timeout=30)
    if until(lambda: not tmux_session.has_session(pane(row)), 10):
        return True
    raise RuntimeError('saved pane did not close')


def launcher(row, host):
    role, sid = identity(row)
    if role == 'project_head':
        return ['bash', 'scripts/spawn-ph.sh', '--resume', sid]
    if host != 'mac' and role in roles.c_level_roles() and role != 'coo':
        if host == 'winbox':
            raise ValueError('C-level tmux resume requires a Linux host')
        variable = 'CTO_SESSION_ID' if role == 'cto' else 'CXO_SESSION_ID'
        command = (['bash', 'scripts/cto-claude.sh'] if role == 'cto' else
                   ['bash', 'scripts/cxo-claude.sh', '--role', role])
        return f'export {variable}={shlex.quote(sid)} && exec {shlex.join(command + ["--resume", sid])}'
    if role == 'cto':
        return ['bash', 'scripts/spawn-cto.sh', '--resume', sid, '--id', sid]
    if role in roles.c_level_roles() and role != 'coo':
        return ['bash', 'scripts/spawn-cxo.sh', '--role', role, '--resume', sid, '--id', sid]
    raise ValueError(f'{role}: launcher cannot preserve session id (COO is service_managed)')


def pending_since(marker, manifest_path):
    """When the pending restart began: the marker's timestamp, else the newest file mtime."""
    try:
        timestamp = datetime.fromisoformat(json.loads(marker.read_text())['timestamp'])
    except (OSError, ValueError, KeyError, TypeError):
        # A legacy or damaged marker still ages out by its file time.
        path = marker if marker.exists() else manifest_path
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)


def prep(args):
    plan = json.loads(args.plan.read_text()) if args.plan else restart_plan.build_plan(args.host, now(), STATE)
    if plan.get('host') != args.host:
        raise ValueError('plan host does not match --host')
    for row in plan['sessions']:
        identity(row)
        if row['action'] not in restart_plan.ACTIONS:
            raise ValueError('unknown plan action')
    write_json(STATE / f'{args.host}-plan-{stamp()}.json', plan, args.dry_run)
    if blockers(plan) and not args.force:
        if not args.dry_run:
            def ready():
                nonlocal plan
                remeasure(plan)
                if not args.plan:
                    plan = restart_plan.build_plan(args.host, now(), STATE)
                return not blockers(plan)
            until(ready, args.wait_max)
        if blockers(plan):
            for item in blockers(plan):
                print(f'ยังทำอยู่: {item}')
            return 3
    manifest = []
    for row in plan['sessions']:
        if managed(row) or worker(row):
            continue
        action = row['action']
        # Force bypasses the turn gate; conservatively preserve waiting work.
        if action == 'wait':
            row['action'] = action = 'resume_full'
        if action in ('resume_lazy', 'resume_full', 'compact_then_resume'):
            role, sid = identity(row)
            project = row.get('project')
            if role == 'project_head' and not project:
                path = ROOT / 'state/locks' / f'{pane(row)}.project'
                project = path.read_text().strip() if path.exists() else None
            manifest.append(dict(sid=sid, role=role, name=row['name'], project=project,
                                 mode='lazy' if action == 'resume_lazy' else 'full'))
    # Persist recovery intent before the first destructive operation.
    manifest_path = STATE / f'{args.host}-resume.json'
    marker = STATE / f'pending-{args.host}.json'
    if manifest_path.exists() or marker.exists():
        timestamp = pending_since(marker, manifest_path)
        if (now() - timestamp).total_seconds() <= STALE_HOURS * 3600:
            raise ValueError('pending resume manifest exists; resume/report it before another prep')
        stale_path = manifest_path.with_name(f'{args.host}-resume.stale-{stamp()}.json')
        if args.dry_run:
            print(f'would retire stale manifest: {manifest_path} -> {stale_path} '
                  f'(from {timestamp.isoformat()}); unlink {marker}')
        else:
            if manifest_path.exists():
                manifest_path.rename(stale_path)
            marker.unlink(missing_ok=True)
            print(f'retired stale manifest: {stale_path} (from {timestamp.isoformat()})')
    write_json(manifest_path, manifest, args.dry_run)
    write_json(STATE / f'pending-{args.host}.json',
               dict(manifest=str(manifest_path.resolve()), timestamp=now().isoformat()), args.dry_run)
    failed = False
    for row in plan['sessions']:
        if managed(row):
            print(f"service_managed: {row['name']}")
            continue
        if worker(row):
            print(f"worker_left_running: {row['name']}")
            continue
        action = row['action']
        try:
            if action == 'close':
                run(['bash', 'scripts/session-kill.sh', '--status', 'closed', pane(row)], args.dry_run)
                continue
            compact_ok = True
            if action == 'compact_then_resume':
                before = None if args.dry_run else boundary(row)
                if not send(row, '/compact', args.dry_run):
                    failed = True
                    continue
                compact_ok = args.dry_run or until(lambda: boundary(row) not in (None, before), args.wait_max)
                if args.dry_run:
                    print(f"wait compact_boundary: {row['name']}")
            if compact_ok:
                if not send(row, '/session-save', args.dry_run):
                    failed = True
                    continue
                if args.dry_run:
                    print(f"wait saved; on timeout: bash scripts/session-kill.sh --status force_saved {pane(row)}")
                    continue
                if until(lambda: saved(row), args.wait_max):
                    gone(row)
                    continue
            run(['bash', 'scripts/session-kill.sh', '--status', 'force_saved', pane(row)], args.dry_run)
            print(f"force_saved: {row['name']}")
            if not args.dry_run:
                gone(row)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            print(f"failed: {row['name']}: {exc}")
            failed = True
    return int(failed)


def manifest_file(host):
    pending = STATE / f'{host}-resume.json'
    if pending.exists():
        return pending
    done = sorted(STATE.glob(f'{host}-resume.done-*.json'))
    if not done:
        raise ValueError('no resume manifest found')
    return done[-1]


def live(host):
    return {(r['role'], r['sid']) for r in live_sessions.read_registry(live_sessions.session_dirs(host))}


def resume(args):
    marker = STATE / f'pending-{args.host}.json'
    if not marker.exists():
        print('no pending restart marker; nothing to resume')
        return 0
    path = Path(json.loads(marker.read_text())['manifest'])
    if path.resolve() != (STATE / f'{args.host}-resume.json').resolve():
        raise ValueError('unexpected resume manifest path')
    entries = json.loads(path.read_text())
    # Only the dry run trusts the published registry: it can be minutes stale
    # and still list a session that was just saved and closed.
    existing = live(args.host) if args.dry_run else set()
    failed = False
    for row in entries:
        try:
            if managed(row):
                print(f"service_managed: {row['name']}; spawn-coo.sh cannot preserve session id")
                failed = True
                continue
            command = launcher(row, args.host)
            if identity(row) in existing or tmux_session.has_session(pane(row)):
                print(f"already_live: {row['name']}")
                continue
            if isinstance(command, str):
                role, sid = identity(row)
                unit = f'org-{role}-{sid}.scope'
                active = subprocess.run(['systemctl', 'is-active', '--quiet', unit],
                                        capture_output=True, timeout=30)
                if active.returncode == 0:
                    try:
                        run(['systemctl', 'stop', unit], args.dry_run)
                    except (OSError, subprocess.SubprocessError) as exc:
                        raise RuntimeError(f'could not stop leftover scope: {unit}: {exc}') from exc
                    print(f'stopped leftover scope: {unit}')
                print(shlex.join(['tmux', 'new-session', '-d', '-s', pane(row),
                                  '-c', str(ROOT), command]))
                if not args.dry_run:
                    tmux_session.create(pane(row), str(ROOT), command)
            else:
                run(command, args.dry_run)
            if not args.dry_run and not until(lambda: tmux_session.has_session(pane(row)), args.wait_max):
                raise RuntimeError('session did not become live')
            if row['mode'] == 'full':
                if not args.dry_run and not until(lambda: empty_input(tmux_session.capture(pane(row) + ':0.0', escapes=True)), args.wait_max):
                    raise RuntimeError('input never became empty; no message sent')
                if not send(row, MESSAGE, args.dry_run):
                    failed = True
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"failed: {row['name']}: {exc}")
            failed = True
    # Keep failed entries retryable instead of marking a partial launch complete.
    if not failed:
        done = path.with_name(f'{args.host}-resume.done-{stamp()}.json')
        if args.dry_run:
            print(f'rename {path} -> {done}')
        else:
            path.replace(done)
            marker.unlink()
    return int(failed)


RELAY_CLI = Path('/opt/MoonieXHQ/Projects/MoonieX/Console/scripts/relay-request.mjs')


def relay_open():
    """Ask Console's relay CLI whether a login relay is open: True, False, or None if unknown."""
    try:
        out = subprocess.run(['node', str(RELAY_CLI), 'list'], check=True, timeout=30,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return out.strip() != '(no open requests)'


def memory():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('MemFree', 'MemAvailable', 'SwapFree', 'SwapTotal'):
            values[key + '_kB'] = int(value.split()[0])
    return values


def clean(args):
    if (STATE / f'pending-{args.host}.json').exists():
        raise ValueError('pending restart; resume/report it before cleaning')
    before = memory()
    plan = restart_plan.build_plan(args.host, now(), STATE)
    if plan.get('host') != args.host:
        raise ValueError('plan host does not match --host')
    events, failed = [], False
    for row in plan['sessions']:
        if (managed(row) or worker(row) or row['role'] in roles.c_level_roles()
                or row.get('in_turn') or row.get('incomplete')
                or row['action'] not in ('park', 'close')):
            continue
        # A parked session is closed only once it saved itself; one still waiting is left alone.
        if row['action'] == 'park' and row.get('status') != 'saved':
            continue
        status = 'closed' if row['action'] == 'close' else 'saved'
        command = ['bash', 'scripts/session-kill.sh', '--status', status, pane(row)]
        try:
            if not args.dry_run:
                subprocess.run(command, cwd=ROOT, check=True, timeout=300,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            events.append(('would run: ' if args.dry_run else 'ran: ') + shlex.join(command))
        except (OSError, subprocess.SubprocessError):
            events.append(f"failed: {pane(row)}")
            failed = True
    relay = relay_open()
    if relay is False or (relay is None and args.chrome):
        try:
            if not args.dry_run:
                subprocess.run(['docker', 'restart', 'neko-pilot'], check=True, timeout=300,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            events.append(('would restart' if args.dry_run else 'restarted') + ' neko-pilot')
        except (OSError, subprocess.SubprocessError):
            events.append('failed: neko-pilot restart')
            failed = True
    else:
        events.append('Chrome skipped: relay open' if relay else 'Chrome skipped: relay state unknown; use --chrome')
    result = dict(events=events, before=before, after=memory(), dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False) if args.json else
          '\n'.join(events + [f"RAM/swap before (kB): {before}", f"RAM/swap after (kB): {result['after']}"]))
    return int(failed)


def report(args):
    entries = json.loads(manifest_file(args.host).read_text())
    existing = live(args.host)
    # A pane that exists on this host counts; the registry alone lags by minutes.
    missing_rows = [r for r in entries
               if identity(r) not in existing and not tmux_session.has_session(pane(r))]
    missing = [r['name'] for r in missing_rows]
    result = dict(back=len(entries) - len(missing), total=len(entries), missing=missing)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"กลับมา {result['back']}/{result['total']}")
        for name in missing:
            print(name)
    if getattr(args, 'notify', False):
        owners = [r for r in entries if r['role'] in roles.c_level_roles()]
        requester = (['--role', owners[0]['role'], '--session', pane(owners[0])]
                     if owners else [])  # Empty manifests use the configured service requester.
        missing_owners = [r for r in missing_rows
                          if r['role'] in roles.c_level_roles() and r['role'] != 'coo']
        if missing_owners:
            suffix = f" ไม่กลับมา (กลับมา {result['back']}/{result['total']}) กด Run เพื่อเปิดใหม่"
            name = ' '.join(str(missing_owners[0]['name']).split())
            why = 'Restart: ' + name[:max(0, 90 - len('Restart: ') - len(suffix))] + suffix
            command = shlex.join(['bash', 'scripts/hub/org-python.sh', 'tools/restart_run.py',
                                  '--host', args.host, 'resume'])
            run(['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', 'create',
                 '--host', args.host, *requester, '--command', command,
                 '--cwd', '/opt/MoonieXHQ/Agents/Core', '--risk', 'amber',
                 '--why', why, '--expected', f"กลับมา {result['total']}/{result['total']}"],
                args.dry_run)
            return 1
        question = f"Restart Contabo: กลับมา {result['back']}/{result['total']}"
        details = ['ยังไม่กลับมา: ' + str(name).replace('\n', ' ')[:70] for name in missing[:3]]
        if len(missing) > 3:
            details.append(f'อีก {len(missing) - 3} รายชื่ออยู่ในรายงานบนเครื่อง')
        run(['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', 'ask',
             '--host', args.host, *requester,
             '--question', question, '--why', '\n'.join(details) or 'ทุก session ในรายการกลับมาแล้ว',
             '--option', 'รับทราบ', '--option', 'ดูรายชื่อที่ขาด' if missing else 'ดูรายงาน'], args.dry_run)
    return int(bool(missing))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prep', 'resume', 'report', 'clean'))
    parser.add_argument('--host', required=True, choices=('contabo', 'mac', 'winbox'))
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--wait-max', type=float, default=600)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--chrome', action='store_true', help='allow Chrome restart when relay state is unknown')
    parser.add_argument('--notify', action='store_true', help='send report as a Run Inbox question')
    args = parser.parse_args(argv)
    if args.wait_max < 0:
        parser.error('--wait-max must be nonnegative')
    try:
        from lib import config
        if config.self_host() != args.host:
            raise ValueError('run on the selected host')
        return {'prep': prep, 'resume': resume, 'report': report, 'clean': clean}[args.command](args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'restart_run failed: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
