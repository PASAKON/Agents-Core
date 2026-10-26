"""Run ordered Colab takes from a JSON job, with an admission cap.

Usage: python3 tools/colab_batch.py --job /opt/MoonieXHQ/Work/job.json --max-credits 150
Job: {"takes": [absolute_directory, ...], "checkpoints": [{"after": glob_or_list,
      "scenes": 102, "max_cu_per_scene": 0.44}], "log": absolute_path,
      "run_take": {"root": absolute_ComfyRunpod_root, "python": absolute_venv_python}}
Exit: 0 done; 1 take failed; 2 invalid job/arguments (0 CU); 3 admission cap;
      4 unreadable balance; 5 checkpoint; 6 pin refusal (0 CU); 7 shutdown unconfirmed (spend unknown).

Only immutable, verified copies of the listed ComfyRunpod files execute. Specs and
reference images are snapshotted as job data before any balance query. Studio mode
is refused: it can load additional local assets and leave a billable warm VM.
No caller argv or environment overrides are forwarded. Batch logs contain counts/
codes, never specs, prompts, environment values or subprocess exception messages.
Child output goes only to each take's run.log, as requested.

Audit scope: file-based takes upload the pinned remote_take.py, take_tail.py and
vm_watchdog.py, plus compiled job data and snapshotted image references. No local
notebook is loaded. Workflow graphs come from PINNED. Studio-only external paths
(uploads_dir, data_dir, vm_dir and local LoRAs) are refused by rejecting studio.
No checkout absolute path is used in the supported path. CLI/auth and VM-installed
third-party packages/weights remain external services, not ComfyRunpod source pins.
The bootstrap is hashed separately. It uses -I -S (no site startup hooks).

IMPORTANT: admission uses budget.max_cu, not a provider-enforced reservation.
The pinned upstream guard polls every 30 seconds and stops AT the take cap; billing
lag and teardown can overshoot. This cannot certify the strict spend-tools header's
hard spending guarantee. Do not declare this tool cap-checked until upstream has a
provider-enforced ceiling. The batch also reserves each attempt's full budget to
avoid admitting extra work against a lagging balance (including retries).
"""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fnmatch
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

WORK = Path('/opt/MoonieXHQ/Work')
COLAB = '/root/.local/bin/colab'
ENTRY = 'scripts/colab/run_take.py'
EXIT_FAIL, EXIT_BAD, EXIT_CAP, EXIT_BALANCE, EXIT_CHECKPOINT, EXIT_PIN = range(1, 7)
PINNED_FROM = '4144ad1d7a67d28b8715adb5b7e9ba73ab4cea04'
# Generated from git objects at PINNED_FROM, not from potentially dirty working files.
PINNED = {'scripts/colab/run_take.py': 'd97ad9e1a7083c101db9e504af24f63877271098d007b8802a3fc34cf0fc349c',
    'scripts/colab/remote_take.py': 'ed1a63e55e67816b2d8df13fe0b54ea5b0232172d1bd388501da56536dd86967',
    'scripts/colab/colabctl.py': '2146ef0d797d622bcabe724470a0872c756a6c74d91074845bdea0e39095854c',
    'scripts/colab/guard.py': '2f8afc36e0e7287c63e76ea061d14446a655eddd873062c608f7a818bed26872',
    'scripts/colab/vm_watchdog.py': '6cf3ba2784787ac0480e0c3e4caef6df2668b680e6287c50a7defc73e83e5c12',
    'scripts/fetch_weights.py': '98370f5d86b6bbcc1d7997fe3da336fd77138cbd8752b02687d732688548fb0c',
    'scripts/render_job.py': '859dfd681aea35d8f765b2c33178e3587ea58071b9cd9b7dcc4cdb6b9c8e987e',
    'scripts/run_tests.py': '2cffa05014ee738e3aab90019ac8c47868cfae0c74aa5e7ce662c9c9f91b6457',
    'scripts/take_tail.py': 'c4a9bf3ae7f520805389a3980b74e4970cd5357c9b49bdade4d66acaf1aeb26b',
    'scripts/scan_frames.py': 'f4f863ad26ef4bb5f91042a93c2e6c7465d37ff7f5fcfe9e5dad4af8812ada8b',
    'scripts/scan_refs.py': 'cb3f95729f2bc0262cb6aa1f2e659acd1e4158db4408afb871c6d39947887210',
    'workflows/facerefine_top.json': '17505ed2880f93b0c45b4222b8c02678fa7240c45feb2b2d765cbe99756fae68',
    'workflows/green_t2v.json': 'f9ec7ecb427390d2d39c7d97caef01a26fe3994cb67331edafbb5f08e8a13db7',
    'workflows/i2v.json': 'eaf57b921dadb0beb04d08fd70b1f9b7cd186c44ac19600a1bdcb7e9e02775be',
    'workflows/i2v_max.json': '2c64525620582bb75dd8801b5490ffdebce37c3b04e9efdff99b5231ca1009fe',
    'workflows/r2v.json': '18bf2df90331f560c0fb0c412b366da3828b5ea5d6657233d07c3081f4c9bf17',
    'workflows/r2v_2pass.json': '21e5bb626c7f2798350f69c6dfbf148293fac2522580ceda8e6d0ff866f2e0ae',
    'workflows/r2v_max.json': 'a7671585807a93f38e4cafdd0f7c39086c51e2ff6dba581d22cedd0ffc30d12a',
    'workflows/r2v_max_hyperflow.json': 'dc64617f8009234cd751ed86116ff4adca5eec80224c0e7f6261175150d9ee6f',
    'workflows/t2v.json': 'f9ec7ecb427390d2d39c7d97caef01a26fe3994cb67331edafbb5f08e8a13db7'}
# Only stdlib is needed locally. -S additionally prevents site startup code from
# running before the bootstrap; -I ignores caller Python environment/settings.
TIMEOUT_MARGIN_S = 300
EXIT_SHUTDOWN = 7
BOOTSTRAP = """import pathlib, runpy, sys
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'scripts'))
sys.path.insert(0, str(root / 'scripts/colab'))
if sys.argv[1] == '--shutdown':
    import json
    from colabctl import Colab, ColabError, SESSION_RE, stop_vms
    class CheckedColab(Colab):
        def sessions(self):
            result = self.run('sessions', timeout=60)
            lines = result.stdout.strip().splitlines()
            if result.returncode or not lines:
                raise ColabError('sessions unreadable')
            if lines == ['[colab] No active sessions found on server.']:
                return []
            rows = [SESSION_RE.fullmatch(line.strip()) for line in lines]
            if not all(rows):
                raise ColabError('sessions unreadable')
            return [row.groupdict() for row in rows]
    directory = pathlib.Path(sys.argv[2])
    state_file = directory / 'take_state.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    config = directory / 'colab-sessions.json'
    result = stop_vms(CheckedColab(config=str(config)), state.get('names', []), state.get('endpoints', []))
    if result['remaining'] != 0:
        sys.exit(7)
    if state:
        state['closed'] = True
        state_file.write_text(json.dumps(state))
    sys.exit(0)
sys.argv = [str(root / 'scripts/colab/run_take.py'), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
BOOTSTRAP_SHA256 = hashlib.sha256(BOOTSTRAP.encode()).hexdigest()


def trusted_interpreter(python, source):
    """Check without importing site or executing any .pth/editable hook."""
    path = Path(python)
    for item in {path, path.resolve(), path.parent, path.resolve().parent}:
        st = item.stat()
        if st.st_uid != 0 or st.st_mode & 0o022:
            raise PinError('interpreter and its directory must be root-owned and not writable by others')
    probe = subprocess.run([python, '-I', '-S', '-c',
                            'import json,sys; print(json.dumps([sys.base_prefix, sys.version_info[:2]]))'],
                           capture_output=True, text=True, timeout=30, env=child_env(),
                           stdin=subprocess.DEVNULL, check=True)
    base, version = json.loads(probe.stdout)
    # Refuse all startup hooks, a conservative superset of checkout-pointing hooks.
    for prefix in {path.parent.parent, Path(base)}:
        for lib in ('lib', 'lib64'):
            site = prefix / lib / ('python%d.%d' % tuple(version)) / 'site-packages'
            if site.exists():
                if list(site.glob('*.pth')) or list(site.glob('*.egg-link')) or list(site.glob('__editable__*')):
                    raise PinError('site-packages startup/editable hook refused')


RETRY = re.compile(r'not found|failed vm|failed in provision|failed upload', re.I)


class JobError(ValueError):
    pass


class PinError(ValueError):
    pass


class BalanceError(ValueError):
    pass


def number(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', str(value)):
        raise ValueError('expected a nonnegative plain number')
    return Decimal(str(value))


def cap_number(value):
    try:
        return number(value)
    except ValueError:
        raise argparse.ArgumentTypeError('expected a nonnegative plain number') from None


def work_path(value):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise JobError('data paths must be absolute')
    path = Path(value).resolve()
    if WORK.resolve() not in path.parents:
        raise JobError('data paths must be under WORK')
    return path


def child_env():
    # No PYTHONPATH, COLAB_*, loader or shell overrides from the card environment.
    return {'PATH': '/usr/bin:/bin', 'HOME': '/root', 'LANG': 'C.UTF-8',
            'COLAB_BIN': COLAB}


def read_balance():
    try:
        result = subprocess.run([COLAB, 'usage'], capture_output=True, text=True,
                                timeout=60, stdin=subprocess.DEVNULL, env=child_env())
        if result.returncode:
            raise BalanceError('usage failed')
        matches = re.findall(r'Current balance\s*:?\s*([^\s]+)', result.stdout)
        if len(matches) != 1:
            raise BalanceError('balance missing or ambiguous')
        return number(matches[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        raise BalanceError('balance unreadable') from None


def balance(reader):
    try:
        return number(reader())
    except (OSError, ValueError, TypeError, InvalidOperation):
        raise BalanceError('balance unreadable') from None


@contextmanager
def pinned_tree(source):
    with tempfile.TemporaryDirectory(prefix='colab-batch-') as name:
        root = Path(name)
        root.chmod(0o700)
        try:
            for relative, digest in PINNED.items():
                rel = Path(relative)
                if rel.is_absolute() or '..' in rel.parts:
                    raise PinError('invalid pin path')
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                # Verify the COPY, not an earlier read of the source (TOCTOU).
                shutil.copyfile(source / rel, target)
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise PinError('pinned copy mismatch: ' + relative)
            if ENTRY not in PINNED:
                raise PinError('entry is not pinned')
        except OSError:
            raise PinError('pinned file missing or unreadable') from None
        bootstrap = root / 'bootstrap.py'
        bootstrap.write_bytes(BOOTSTRAP.encode())
        if hashlib.sha256(bootstrap.read_bytes()).hexdigest() != BOOTSTRAP_SHA256:
            raise PinError('bootstrap mismatch')
        yield root


def load_job(path):
    job = json.loads(path.read_text())
    if not isinstance(job, dict) or set(job) - {'takes', 'checkpoints', 'log', 'run_take'}:
        raise JobError('invalid job object')
    log = work_path(job['log'])
    run = job['run_take']
    if set(run) != {'root', 'python'}:
        raise JobError('run_take requires root and python')
    for key in ('root', 'python'):
        if not isinstance(run[key], str) or not Path(run[key]).is_absolute():
            raise JobError('run_take paths must be absolute')
    if not Path(run['root']).is_dir() or not Path(run['python']).is_file():
        raise JobError('run_take root or interpreter missing')
    if not isinstance(job['takes'], list) or not job['takes']:
        raise JobError('takes must be a nonempty ordered list')
    takes = []
    for value in job['takes']:
        directory = work_path(value)
        spec = json.loads((directory / 'spec.json').read_text())
        if not isinstance(spec, dict) or spec.get('studio'):
            raise JobError('only file-based non-studio specs are supported')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', directory.name):
            raise JobError('take directory must be a valid take_id')
        wf = spec.get('workflow')
        if not isinstance(wf, str) or not re.fullmatch(r'[A-Za-z0-9_]+', wf) or \
                f'workflows/{wf}.json' not in PINNED:
            raise JobError('workflow is not pinned')
        budget = number(spec['budget']['max_cu'])
        if not budget or not number(spec['budget']['max_minutes']):
            raise JobError('take budgets must be positive')
        if not isinstance(spec.get('scenes'), list) or not spec['scenes']:
            raise JobError('scenes must be a nonempty list')
        # Read data once; the child will receive only these bytes, never mutable originals.
        assets = {}
        for obj in [spec, *spec['scenes']]:
            if not isinstance(obj, dict) or not isinstance(obj.get('refs', []), list):
                raise JobError('invalid scene refs')
            for ref in obj.get('refs', []):
                if not isinstance(ref, str):
                    raise JobError('invalid reference path')
                p = work_path(str(directory / ref))
                assets[ref] = (p.suffix, p.read_bytes())
        spec['take_id'] = directory.name
        takes.append((directory, spec, budget, assets))
    paths = [str(t[0]) for t in takes]
    if len(paths) != len(set(paths)):
        raise JobError('duplicate takes')
    checkpoints = {}
    for cp in job.get('checkpoints', []):
        after = cp['after']
        if isinstance(after, str):
            members = [i for i, p in enumerate(paths) if fnmatch.fnmatchcase(p, after)]
        elif isinstance(after, list) and after:
            members = [paths.index(str(work_path(p))) for p in after]
        else:
            raise JobError('invalid checkpoint group')
        if not members or not isinstance(cp['scenes'], int) or isinstance(cp['scenes'], bool) or cp['scenes'] <= 0:
            raise JobError('empty checkpoint group or invalid scene count')
        checkpoints.setdefault(max(members), []).append((cp['scenes'], number(cp['max_cu_per_scene'])))
    return log, run, takes, checkpoints


def snapshot_spec(root, index, spec, assets):
    dest = root / 'data' / str(index)
    dest.mkdir(parents=True)
    names = {}
    for i, (ref, (suffix, data)) in enumerate(assets.items()):
        p = dest / f'ref_{i}{suffix}'
        p.write_bytes(data)
        names[ref] = str(p)
    spec = json.loads(json.dumps(spec))
    for obj in [spec, *spec['scenes']]:
        if 'refs' in obj:
            obj['refs'] = [names[r] for r in obj['refs']]
    path = dest / 'spec.json'
    path.write_text(json.dumps(spec))
    return path


def run_take(python, root, spec, directory, output, timeout):
    # Every child argument is a constant or validated job data, never card argv.
    proc = subprocess.Popen([python, '-I', '-S', str(root / 'bootstrap.py'), str(spec),
                             '--out', str(directory.parent)], cwd=root, env=child_env(),
                            stdin=subprocess.DEVNULL, stdout=output,
                            stderr=subprocess.STDOUT, start_new_session=True)
    try:
        return proc.wait(timeout=timeout)
    except BaseException:
        # Kill the process group, including a hung CLI descendant. The detached
        # upstream guard is left alive until shutdown confirms the VM is gone.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        raise


def shutdown(python, root, directory):
    """Pinned colabctl: absolute colab stop -s, then server verification and
    endpoint unassign fallback. Failure never becomes a zero-spend result."""
    try:
        result = subprocess.run([python, '-I', '-S', str(root / 'bootstrap.py'),
                                 '--shutdown', str(directory)], cwd=root, env=child_env(),
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=600)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def execute(job, cap, reader, runner, sleeper, emit, stopper, validator):
    _, run, takes, checkpoints = job
    try:
        validator(run['python'], Path(run['root']))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        raise PinError('interpreter trust check failed') from None
    with pinned_tree(Path(run['root'])) as root:
        specs = [snapshot_spec(root, i, spec, assets)
                 for i, (_, spec, _, assets) in enumerate(takes)]
        start = balance(reader)
        spent = reserved = Decimal(0)
        emit(f'BALANCE {start} spent 0 CU cap {cap}')
        for i, (directory, spec, budget, _) in enumerate(takes):
            emit(f'TAKE {i + 1}')
            for attempt in range(1, 4):
                current = balance(reader)
                spent = max(spent, start - current)
                emit(f'BALANCE {current} spent {spent} CU')
                if max(spent, reserved) + budget > cap:
                    emit(f'STOP cap spent {spent} reserved {reserved} next {budget}')
                    return EXIT_CAP
                reserved = max(spent, reserved) + budget
                (directory / 'progress.json').unlink(missing_ok=True)
                log_path = directory / 'run.log'
                emit(f'TRY {attempt} take {i + 1}')
                with log_path.open('ab') as output:
                    offset = output.tell()
                    timeout = float(number(spec['budget']['max_minutes']) * 60) + TIMEOUT_MARGIN_S
                    try:
                        rc = runner(run['python'], root, specs[i], directory, output, timeout)
                    except subprocess.TimeoutExpired:
                        emit(f'TIMEOUT take {i + 1}')
                        rc = 124
                    except (OSError, subprocess.SubprocessError):
                        rc = 125
                    finally:
                        stopped = stopper(run['python'], root, directory)
                        emit(f'SHUTDOWN confirmed {bool(stopped)}')
                    if not stopped:
                        emit('STOP shutdown unconfirmed; spend unknown')
                        return EXIT_SHUTDOWN
                emit(f'EXIT {rc} take {i + 1} try {attempt}')
                current = balance(reader)
                spent = max(spent, start - current)
                emit(f'BALANCE {current} spent {spent} CU')
                if spent > cap:
                    emit('STOP cap exceeded by upstream take')
                    return EXIT_CAP
                if rc == 0:
                    break
                with log_path.open('rb') as output:
                    output.seek(offset)
                    tail = b''.join(deque(output, maxlen=6)).decode(errors='replace')
                if attempt == 3 or not RETRY.search(tail):
                    return EXIT_FAIL
                emit('RETRY sleep 60 s')
                sleeper(60)
            for scenes, limit in checkpoints.get(i, []):
                emit(f'CHECKPOINT after take {i + 1} spent {spent} scenes {scenes} CU/scene {spent / scenes}')
                if spent / scenes > limit:
                    return EXIT_CHECKPOINT
        emit(f'DONE spent {spent} CU')
        return 0


def main(argv=None, *, balance_reader=None, take_runner=None, sleep=None,
         stop_runner=None, interpreter_validator=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], allow_abbrev=False)
    parser.add_argument('--job', required=True)
    parser.add_argument('--max-credits', required=True, type=cap_number)
    args = parser.parse_args(argv)
    try:
        job = load_job(work_path(args.job))
    except (OSError, ValueError, KeyError, TypeError):
        print('REFUSE invalid job/spec/reference; spent 0 CU', flush=True)
        return EXIT_BAD
    try:
        with job[0].open('a', encoding='utf-8') as log:
            try:
                fcntl.flock(log, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('REFUSE another batch holds the job log; spent 0 CU', flush=True)
                return EXIT_BAD
            def emit(message):
                line = time.strftime('%Y-%m-%d %H:%M:%S ') + message
                print(line, flush=True)
                log.write(line + '\n')
                log.flush()
            try:
                return execute(job, args.max_credits, balance_reader or read_balance,
                               take_runner or run_take, sleep or time.sleep, emit,
                               stop_runner or shutdown, interpreter_validator or trusted_interpreter)
            except PinError as exc:
                emit(f'REFUSE {exc}; spent 0 CU')
                return EXIT_PIN
            except BalanceError:
                emit('STOP balance unreadable')
                return EXIT_BALANCE
            except (OSError, subprocess.SubprocessError):
                emit('STOP local I/O or child process failure')
                return EXIT_FAIL
    except OSError:
        print('REFUSE log unavailable; spent 0 CU', flush=True)
        return EXIT_BAD


if __name__ == '__main__':
    sys.exit(main())
