"""Execute SafeRestart plans locally. This tool never reboots the host.

Exit 3 means the safety gate is still blocked; exit 1 means partial failure.
Run prep outside the sessions it closes (for example from the Run card worker).

winbox (docs/ops/safe-restart.md §winbox): the sessions are claude.exe in Windows
Terminal tabs, not tmux panes. Typing goes through windows/wake.ps1 (console
session only, behind the PC lease gate), "saved" is the c_level_sessions record,
and resume opens one new tab per session with windows/cxo-claude.ps1. Every
winbox branch is below a `host == 'winbox'` test; the Contabo paths are untouched.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
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


# ---- winbox: the Windows twin of the tmux helpers ---------------------------------
# ASCII only: windows/wake.ps1 refuses any other byte in the text it types.
WIN_MESSAGE = 'System restart finished. Continue from where you stopped.'
# The tenant's lease lives where windows/pc_lease.py is deployed on the box.
WIN_LEASE = (r'C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe', r'C:\mooniex\pclease\pc_lease.py')
# The same string the PowerShell callers pass to `pc_lease.py take --who`: gate --as
# stays quiet only for the holder's own name.
WIN_LEASE_WHO = 'SafeRestart winbox'
WIN_GONE_WAIT_S = 15      # a winbox session cannot end itself; the reboot does, so do not wait long
WIN_SETTLE_S = 15         # a registered session may not be reading its input yet
WIN_TYPE_TIMEOUT_S = 120
_ASCII_TEXT = re.compile(r'[\x20-\x7e]{1,300}')


def win_session_id():
    """This process's Windows session id (0 = ssh/service, no desktop), None if unknown."""
    try:
        import ctypes
        out = ctypes.c_ulong()
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        if k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), ctypes.byref(out)):
            return int(out.value)
    except (OSError, AttributeError, ImportError):
        pass
    return None


def win_started(pid):
    """The process creation time as a FILETIME (what the registry's procStart holds), or None."""
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        k32.OpenProcess.restype = wintypes.HANDLE
        handle = k32.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return None
        try:
            times = [wintypes.FILETIME() for _ in range(4)]
            if not k32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
                return None
            return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        finally:
            k32.CloseHandle(handle)
    except (OSError, AttributeError, ImportError, ValueError):
        return None


def win_live():
    """(role, sid) of every winbox session that is really running.

    Windows reuses pids at once, so after a reboot a leftover ~/.claude/sessions/<pid>.json
    can name a pid that now belongs to another program; is_alive() would call that session
    live and resume would skip it. The record's procStart is the process creation FILETIME:
    a pid whose creation time differs is not the session."""
    dirs = live_sessions.session_dirs('winbox')
    out = set()
    for row in live_sessions.read_registry(dirs):
        recorded = None
        for directory in dirs:
            try:
                recorded = json.loads((Path(directory) / f"{row['pid']}.json").read_text(encoding='utf-8')).get('procStart')
                break
            except (OSError, ValueError, AttributeError):
                continue
        actual = win_started(row['pid'])
        try:
            if recorded is not None and actual is not None and int(recorded) != actual:
                continue
        except (TypeError, ValueError):
            pass
        out.add((row['role'], row['sid']))
    return out


def win_tab_token(row):
    """windows/cxo-claude.ps1 titles the tab "<display> #<sid>" and stops claude renaming it."""
    return '#' + identity(row)[1]


def win_gate():
    """pc_lease.py gate: True when the desktop may be touched (not the CEO's hold, and the
    farm is parked or we hold the lease). Run before every stage, never cached."""
    python, script = WIN_LEASE
    done = subprocess.run([python, script, 'gate', '--as', WIN_LEASE_WHO],
                          capture_output=True, text=True, errors='replace', timeout=60)
    if done.returncode != 0:
        print(f'pc_lease_refused: gate exit {done.returncode}: {(done.stderr or "").strip()[:200]}')
        return False
    return True


def win_wake(row, text, dry_run):
    """windows/wake.ps1 against this row's tab: (exit code, one-line output)."""
    command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               str(ROOT / 'windows' / 'wake.ps1'), '-Title', win_tab_token(row),
               '-Marker', text, '-Contains']
    if dry_run:
        command.append('-DryRun')
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                          errors='replace', timeout=WIN_TYPE_TIMEOUT_S)
    return done.returncode, ' '.join((done.stdout or '').split())[:200]


def win_send(row, text):
    """Type `text` + Enter into the row's tab. False (nothing typed, or Enter withheld)
    unless the lease gate and wake.ps1's own foreground check both pass."""
    print(f"type into tab {win_tab_token(row)}: {text}")
    if not _ASCII_TEXT.fullmatch(text):
        print(f"draft_or_not_ready: {row['name']}: wake.ps1 types printable ASCII only")
        return False
    if not win_gate():
        return False
    code, out = win_wake(row, text, False)
    if code != 0:
        print(f"draft_or_not_ready: {row['name']}: wake exit {code}: {out}")
        return False
    return True


def win_preflight(rows):
    """Before the first real keystroke: this is the console session, the desktop is ours,
    and every tab we will type into is found exactly once and in front (wake.ps1 -DryRun
    types nothing). One missing tab must stop the restart before any session is saved."""
    if win_session_id() in (None, 0):
        raise ValueError('winbox prep types into Windows Terminal tabs: run it in the console '
                         'session (scripts/winbox-restart.sh does), not over plain ssh')
    if not win_gate():
        return 3
    bad = False
    for row in rows:
        code, out = win_wake(row, 'preflight', True)
        if code != 0:
            print(f"tab_not_found: {row['name']} {win_tab_token(row)}: wake exit {code}: {out}")
            bad = True
    return 1 if bad else 0


def win_record(row, status, dry_run):
    """winbox has no session-kill: /session-save cannot end a claude.exe here. Record why the
    session is going down and leave the process to the reboot, so its .uuid, .lock and (for a
    Project Head) .project/.spawned_by files, which cxo-claude.ps1 deletes on a clean exit,
    are still there for resume."""
    role, sid = identity(row)
    print(f'record {status} in c_level_sessions: {role}-{sid} (process left running; the reboot ends it)')
    if not dry_run:
        session_status.record_close(role, sid, status, locks_dir=ROOT / 'state' / 'locks')


_OWNER_RECORD = re.compile(r'cxo:[a-z0-9_-]{1,40}:[A-Za-z0-9_-]{1,40}')


def win_owner(sid):
    """A Project Head's owner record, "cxo:<lane>:<owner>" as spawn_ph wrote it, else None.
    cxo-claude.ps1 refuses to start a Project Head without it and deletes it when claude
    exits, so prep keeps a copy in the manifest."""
    try:
        text = (ROOT / 'state/locks' / f'project_head-{sid}.spawned_by').read_text(encoding='utf-8').strip()
    except OSError:
        return None
    return text if _OWNER_RECORD.fullmatch(text) else None


def win_restore_owner(row, dry_run):
    """Put the owner record back if the session's last exit removed it (never overwrite one)."""
    role, sid = identity(row)
    record = row.get('spawned_by')
    if role != 'project_head' or not record or not _OWNER_RECORD.fullmatch(record):
        return
    path = ROOT / 'state/locks' / f'project_head-{sid}.spawned_by'
    if path.exists():
        return
    print(f'restore owner record: {path}')
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record + '\n', encoding='utf-8')


def win_hub_ph(sid):
    """(record, why): a Project Head's project, lane and owner as the hub's portfolio registry
    holds them (projects.ph_session = this session, the row tools/spawn_ph.py writes). The
    record is dict(project, lane, spawned_by) only when every field is known and well formed;
    otherwise None and one line saying what is missing. c_level_sessions holds none of these."""
    from lib import db
    if not db.pg_url():
        return None, 'ORG_DB_URL is unset, so the hub cannot be read'
    try:
        with db.get_conn() as conn:
            rows = [dict(r) for r in conn.execute(
                'SELECT id, name, lane, owner_session FROM projects WHERE ph_session IN (?, ?) ORDER BY id',
                (sid, f'{roles.PH_ROLE}-{sid}')).fetchall()]
    except Exception as exc:  # the hub is down, the snapshot has no such table, a driver error
        return None, f'the hub could not be read ({type(exc).__name__})'
    if not rows:
        return None, 'no portfolio project names this session as its Project Head'
    if len(rows) > 1:
        return None, 'several portfolio projects name this session: ' + ', '.join(r['id'] for r in rows)
    row = rows[0]
    lane = row.get('lane') or ''
    if roles.ph_lane_refusal(lane):
        return None, f"project {row['id']} has no usable lane (hub says {lane!r})"
    # tools/spawn_ph.py stores "<lane>-<owner session>". Only a real session id counts: the
    # hub also holds placeholders such as "cto-fresh", and an owner record naming a session
    # that does not exist would send the Project Head's reports nowhere.
    owner = row.get('owner_session') or ''
    owner_sid = owner[len(lane) + 1:] if owner.startswith(lane + '-') else ''
    if not re.fullmatch(r'[0-9a-f]{8}', owner_sid):
        return None, f"project {row['id']} has no owner session '<lane>-<8 hex>' (hub says {owner!r})"
    spawned_by = f'cxo:{lane}:{owner_sid}'
    # The name a spawner types comes first (spawn_ph's one-PH-per-project check compares it
    # case-folded); a name with a space cannot be one, so the registry id stands in.
    project = next((v for v in (row['name'], row['id']) if roles.ph_project_refusal(v) is None), None)
    if project is None:
        return None, f"project {row['id']} has no name that a Project Head can be started with"
    return dict(project=project, lane=lane, spawned_by=spawned_by), ''


def win_rebuild_owner(entry, dry_run):
    """Before `cannot_resume`: put back the .project / .spawned_by a Project Head lost (the
    temp respawn scripts of 2026-10-27 never wrote them). Writes only when the hub knows
    every field, only the file that is missing, and never over a file that exists. Prints
    which of rebuilt / not_rebuilt / owner_record_ok happened. Updates `entry` in place."""
    sid, name = entry['sid'], entry['name']
    if entry.get('project') and entry.get('spawned_by'):
        print(f'owner_record_ok: {name}')
        return
    locks = ROOT / 'state/locks'
    files = {'project': locks / f'{roles.PH_ROLE}-{sid}.project',
             'spawned_by': locks / f'{roles.PH_ROLE}-{sid}.spawned_by'}
    missing = [key for key in files if not entry.get(key)]
    for key in missing:
        if files[key].exists():
            print(f'not_rebuilt: {name}: {files[key].name} exists but is not usable; left alone')
            return
    found, why = win_hub_ph(sid)
    if found is None:
        print(f'not_rebuilt: {name}: {why}')
        return
    for key in missing:
        entry[key] = found[key]
        if not dry_run:
            files[key].parent.mkdir(parents=True, exist_ok=True)
            files[key].write_text(found[key], encoding='utf-8')
    entry['lane'] = found['lane']
    print(('would_rebuild' if dry_run else 'rebuilt') + f": {name}: wrote {', '.join(files[k].name for k in missing)}"
          f" from the hub (project={entry['project']} lane={entry['lane']} spawned_by={entry['spawned_by']})")


def win_plan_lines(plan, actions, cannot):
    """Dry run: what a real run does with each session. `actions` is the plan's action per
    sid before prep turned a forced `wait` into a resume; `cannot` maps sid -> why not."""
    lines = []
    for row in plan['sessions']:
        role, sid = identity(row)
        action = actions[sid]
        if managed(row):
            label = 'leave alone'
        elif worker(row):
            label = 'leave running'
        elif sid in cannot:
            label = 'cannot_resume'
        elif action == 'wait':
            label = 'wait'
        elif action == 'close':
            label = 'close (no reopen)'
        elif action == 'park':
            label = 'save only (park)'
        else:
            label = 'save+reopen'
        why = {'leave alone': 'service_managed', 'leave running': 'worker, owned by the task ledger',
               'cannot_resume': cannot.get(sid, ''), 'close (no reopen)': 'recorded closed, not typed into',
               'wait': 'mid-turn: a real run waits up to --wait-max, then stops with exit 3'}.get(label, '')
        if label == 'save+reopen':
            why = {'compact_then_resume': '/compact first', 'resume_lazy': 'lazy: no continue message'}.get(action, '')
        lines.append(f"  {label:<18} {role} #{sid}  {row['name']}" + (f'  ({why})' if why else ''))
    return lines


def win_boot_time():
    """Epoch seconds of the last boot, or None."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        k32.GetTickCount64.restype = ctypes.c_ulonglong
        return time.time() - k32.GetTickCount64() / 1000
    except (OSError, AttributeError, ImportError):
        return None


def win_clear_stale_lock(row, dry_run):
    """cxo-claude.ps1 refuses to start when <role>-<sid>.lock names a live pid, and after a
    reboot that pid may belong to anything. A lock written before the boot cannot be live."""
    role, sid = identity(row)
    lock = ROOT / 'state/locks' / f'{role}-{sid}.lock'
    boot = win_boot_time()
    try:
        if boot is None or lock.stat().st_mtime >= boot:
            return
    except OSError:
        return
    print(f'remove stale lock (written before the boot): {lock}')
    if not dry_run:
        lock.unlink(missing_ok=True)


def win_wt_running():
    try:
        return 'WindowsTerminal.exe' in (subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq WindowsTerminal.exe', '/NH'],
            capture_output=True, text=True, timeout=10).stdout or '')
    except (OSError, subprocess.SubprocessError):
        return False


def win_launcher(row):
    """argv that opens the session in a new Windows Terminal tab (windows/cxo-claude.ps1).

    -Session keeps the 8-hex id; --resume takes the full conversation uuid recorded at prep
    (the launcher also accepts the 8 hex and looks the uuid up, but that lookup needs the
    hub, which a bare launcher has no URL for). A Project Head needs its lane and project:
    the launcher rebuilds owner and first-prompt from the owner record, and does not
    re-submit the first prompt on --resume."""
    role, sid = identity(row)
    command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               str(ROOT / 'windows' / 'cxo-claude.ps1'), '-Role', role, '-Session', sid]
    if role == 'project_head':
        if not row.get('lane') or not row.get('project'):
            raise ValueError('no lane, project or owner record (state/locks/project_head-<sid>.spawned_by): '
                             'not started by windows\\cxo-claude.ps1 or tools.spawn_ph, so it cannot be reopened')
        command += ['-Lane', row['lane'], '-Project', row['project']]
    command += ['--resume', row.get('uuid') or sid]
    wt = str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'WindowsApps' / 'wt.exe')
    return [wt, '-w', '0' if win_wt_running() else 'new', 'nt', '--title', f'{role} #{sid}',
            '-d', str(ROOT)] + command


def send(row, text, dry=False, host='contabo'):
    if host == 'winbox':
        if dry:
            print(f"type into tab {win_tab_token(row)}: {text}")
            return True
        return win_send(row, text)
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
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


def when(value):
    """closed_at as an aware datetime (the hub returns a string or a datetime), else None."""
    try:
        stamp_ = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return stamp_ if stamp_.tzinfo else stamp_.replace(tzinfo=timezone.utc)


def saved(row, host='contabo', since=None):
    role, sid = identity(row)
    if host == 'winbox':
        # No tmux pane to disappear: only the hub record says /session-save finished, and
        # an old "saved" row of a session that is running again must not count, so the
        # record has to be newer than the moment we typed the command.
        record = session_status.get(role, sid)
        closed = when(record.get('closed_at')) if record else None
        return bool(record and record.get('status') == 'saved'
                    and (since is None or (closed is not None and closed >= since)))
    if not tmux_session.has_session(pane(row)):
        return True
    record = session_status.get(role, sid)
    return bool(record and record.get('status') == 'saved')


GONE_WAIT_S = 60


def gone(row, host='contabo'):
    """Wait until the saved pane is really closed. session-kill records 'saved'
    first and kills tmux a few seconds later; a resume that runs inside that gap
    sees the old pane, calls it already_live and never relaunches it (17 Oct 2026:
    0/6 came back).

    winbox: nothing here ends a claude.exe (cxo-claude.ps1 would delete the session's
    lock, .uuid and .project files on a clean exit, and resume needs them), so give it
    a moment, then say it stays up until the reboot."""
    if host == 'winbox':
        role, sid = identity(row)
        if until(lambda: (role, sid) not in win_live(), WIN_GONE_WAIT_S):
            return True
        print(f"live_until_reboot: {row['name']}")
        return False
    if until(lambda: not tmux_session.has_session(pane(row)), GONE_WAIT_S):
        return True
    subprocess.run([tmux_session.tmux_bin(), 'kill-session', '-t', pane(row)],
                   capture_output=True, text=True, timeout=30)
    if until(lambda: not tmux_session.has_session(pane(row)), 10):
        return True
    raise RuntimeError('saved pane did not close')


def launcher(row, host):
    role, sid = identity(row)
    if host == 'winbox' and (role == roles.PH_ROLE or (role in roles.c_level_roles() and role != 'coo')):
        return win_launcher(row)
    if role == 'project_head':
        return ['bash', 'scripts/spawn-ph.sh', '--resume', sid]
    if host != 'mac' and role in roles.c_level_roles() and role != 'coo':
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


# The words restart_plan.build_plan puts in its warnings about Run cards (pinned by a test).
CARDS_UNAVAILABLE = 'Run cards unavailable; a running card cannot be ruled out.'
CARD_RUNNING = 'Do not cut: run card '


def plan_for(args):
    plan = restart_plan.build_plan(args.host, now(), STATE)
    if getattr(args, 'cards_checked', False):
        # winbox has no Run Inbox token, and the restart card itself is a running card on
        # Contabo. The caller (scripts/winbox-restart.sh) listed the cards running on
        # this host from Contabo and found none; the warnings below are about every host.
        plan['warnings'] = [w for w in plan.get('warnings', [])
                            if w != CARDS_UNAVAILABLE and not w.startswith(CARD_RUNNING)]
    return plan


def prep(args):
    win = args.host == 'winbox'
    plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else plan_for(args)
    if plan.get('host') != args.host:
        raise ValueError('plan host does not match --host')
    for row in plan['sessions']:
        identity(row)
        if row['action'] not in restart_plan.ACTIONS:
            raise ValueError('unknown plan action')
    write_json(STATE / f'{args.host}-plan-{stamp()}.json', plan, args.dry_run)
    # What the planner decided, before a forced `wait` becomes a resume below.
    actions = {identity(r)[1]: r['action'] for r in plan['sessions']}
    blocked = False
    if blockers(plan) and not args.force:
        if not args.dry_run:
            def ready():
                nonlocal plan
                remeasure(plan)
                if not args.plan:
                    plan = plan_for(args)
                return not blockers(plan)
            until(ready, args.wait_max)
        if blockers(plan):
            for item in blockers(plan):
                print(f'ยังทำอยู่: {item}')
            if not (win and args.dry_run):
                return 3
            blocked = True   # a winbox dry run still says what each session would do
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
                project = path.read_text(encoding='utf-8').strip() if path.exists() else None
            entry = dict(sid=sid, role=role, name=row['name'], project=project,
                         mode='lazy' if action == 'resume_lazy' else 'full')
            if win:
                # cxo-claude.ps1 --resume takes the full conversation id, and a Project Head
                # needs its lane back: both are known now and gone with the session's files.
                owner = win_owner(sid) if role == 'project_head' else None
                entry.update(uuid=row.get('uuid'), lane=owner.split(':')[1] if owner else None,
                             spawned_by=owner)
            manifest.append(entry)
    if win:
        # A Project Head that lost its owner record gets it back from the hub if the hub
        # knows every field; only then is it left as cannot_resume.
        for entry in manifest:
            if entry['role'] == roles.PH_ROLE:
                win_rebuild_owner(entry, args.dry_run)
        # Never save (and so lose) a session that resume could not reopen.
        cannot = {}
        for entry in manifest:
            try:
                win_launcher(entry)
            except ValueError as exc:
                print(f"cannot_resume: {entry['name']}: {exc}")
                cannot[entry['sid']] = str(exc).split(':')[0]
        unreachable = bool(cannot)
        if args.dry_run:
            print('-- what a real run does, per session')
            print('\n'.join(win_plan_lines(plan, actions, cannot)) or '  (no sessions)')
        if blocked:
            return 3
        if unreachable:
            print('nothing was typed, saved or closed: fix the sessions above or leave them out of the restart')
            return 1
        typed = [r for r in plan['sessions'] if not managed(r) and not worker(r) and r['action'] != 'close']
        if args.dry_run:
            for row in typed:
                print(f"would preflight tab {win_tab_token(row)}: wake.ps1 -DryRun (types nothing)")
        elif typed:
            code = win_preflight(typed)
            if code:
                print('preflight failed: nothing was saved or closed and no marker was written')
                return code
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
                if win:
                    win_record(row, 'closed', args.dry_run)
                else:
                    run(['bash', 'scripts/session-kill.sh', '--status', 'closed', pane(row)], args.dry_run)
                continue
            compact_ok = True
            if action == 'compact_then_resume':
                before = None if args.dry_run else boundary(row)
                if not send(row, '/compact', args.dry_run, args.host):
                    failed = True
                    continue
                compact_ok = args.dry_run or until(lambda: boundary(row) not in (None, before), args.wait_max)
                if args.dry_run:
                    print(f"wait compact_boundary: {row['name']}")
            if compact_ok:
                typed_at = now()
                if not send(row, '/session-save', args.dry_run, args.host):
                    failed = True
                    continue
                if args.dry_run:
                    print('wait saved; on timeout: ' + (
                        f'record force_saved in c_level_sessions ({pane(row)})' if win else
                        f"bash scripts/session-kill.sh --status force_saved {pane(row)}"))
                    continue
                if until(lambda: saved(row, args.host, typed_at) if win else saved(row), args.wait_max):
                    gone(row, args.host)
                    continue
            if win:
                win_record(row, 'force_saved', args.dry_run)
            else:
                run(['bash', 'scripts/session-kill.sh', '--status', 'force_saved', pane(row)], args.dry_run)
            print(f"force_saved: {row['name']}")
            if not args.dry_run:
                gone(row, args.host)
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
    if host == 'winbox':
        return win_live()
    return {(r['role'], r['sid']) for r in live_sessions.read_registry(live_sessions.session_dirs(host))}


def resume(args):
    marker = STATE / f'pending-{args.host}.json'
    if not marker.exists():
        print('no pending restart marker; nothing to resume')
        return 0
    win = args.host == 'winbox'
    if win and not args.dry_run and win_session_id() in (None, 0):
        raise ValueError('winbox resume opens Windows Terminal tabs: run it in the console session')
    path = Path(json.loads(marker.read_text(encoding='utf-8'))['manifest'])
    if path.resolve() != (STATE / f'{args.host}-resume.json').resolve():
        raise ValueError('unexpected resume manifest path')
    entries = json.loads(path.read_text(encoding='utf-8'))
    # Only the dry run trusts the published registry: it can be minutes stale
    # and still list a session that was just saved and closed.
    # winbox has no panes to ask, and win_live() checks the process behind each record.
    existing = live(args.host) if args.dry_run or win else set()
    failed = False
    for row in entries:
        try:
            if managed(row):
                print(f"service_managed: {row['name']}; spawn-coo.sh cannot preserve session id")
                failed = True
                continue
            command = launcher(row, args.host)
            if identity(row) in existing or (not win and tmux_session.has_session(pane(row))):
                print(f"already_live: {row['name']}")
                continue
            if win:
                win_clear_stale_lock(row, args.dry_run)
                win_restore_owner(row, args.dry_run)
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
            if win:
                if not args.dry_run and not until(lambda: identity(row) in win_live(), args.wait_max):
                    raise RuntimeError('session did not become live')
                if row['mode'] == 'full':
                    if not args.dry_run:
                        time.sleep(WIN_SETTLE_S)   # registered is not yet reading its input
                    if not send(row, WIN_MESSAGE, args.dry_run, args.host):
                        failed = True
                continue
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


def ask_run(host, argv, dry):
    """tools/ask_run.py <argv>. On winbox: this interpreter (bash there is the WSL stub), and a
    card that cannot be raised (no Run Inbox token yet) is logged, never a failed report."""
    if host != 'winbox':
        run(['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', *argv], dry)
        return
    try:
        run([sys.executable, 'tools/ask_run.py', *argv], dry)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'notify_failed: {exc}')


def report(args):
    win = args.host == 'winbox'
    entries = json.loads(manifest_file(args.host).read_text(encoding='utf-8'))
    existing = live(args.host)
    # A pane that exists on this host counts; the registry alone lags by minutes.
    missing_rows = [r for r in entries
               if identity(r) not in existing and (win or not tmux_session.has_session(pane(r)))]
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
            cwd = '/opt/MoonieXHQ/Agents/Core'
            if win:
                command = r'powershell -NoProfile -ExecutionPolicy Bypass -File windows\org-resume-logon.ps1'
                cwd = str(ROOT)
            ask_run(args.host, ['create',
                 '--host', args.host, *requester, '--command', command,
                 '--cwd', cwd, '--risk', 'amber',
                 '--why', why, '--expected', f"กลับมา {result['total']}/{result['total']}"],
                args.dry_run)
            return 1
        question = f"Restart {'winbox' if win else 'Contabo'}: กลับมา {result['back']}/{result['total']}"
        details = ['ยังไม่กลับมา: ' + str(name).replace('\n', ' ')[:70] for name in missing[:3]]
        if len(missing) > 3:
            details.append(f'อีก {len(missing) - 3} รายชื่ออยู่ในรายงานบนเครื่อง')
        ask_run(args.host, ['ask',
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
    parser.add_argument('--cards-checked', action='store_true',
                        help='winbox: the caller already found no running Run card for this host')
    args = parser.parse_args(argv)
    if sys.platform == 'win32':   # a Windows console writes cp1252; the names are Thai
        for stream in (sys.stdout, sys.stderr):
            stream.reconfigure(encoding='utf-8', errors='replace')
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
