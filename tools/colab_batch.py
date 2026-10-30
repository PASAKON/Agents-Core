"""Run ordered Colab takes from a JSON job, with an admission cap.

Usage: python3 tools/colab_batch.py --job /opt/MoonieXHQ/Work/job.json --max-credits 175
Job: {"takes": [absolute_directory, ...], "checkpoints": [{"after": glob_or_list,
      "scenes": 102, "max_cu_per_scene": 0.52}], "log": absolute_path,
      "run_take": {"root": absolute_ComfyRunpod_root, "python": absolute_venv_python},
      "uploads_dir": absolute_directory_under_WORK}   # uploads_dir only for studio takes
Exit: 0 done; 1 take failed; 2 invalid job/arguments (0 CU); 3 admission cap;
      4 unreadable balance; 5 checkpoint; 6 pin refusal, or a studio take's spec, reference
      or output folder, or a file take's snapshot, changed since load (0 CU for that take);
      7 shutdown unconfirmed (spend unknown).

Only immutable, verified copies of the listed ComfyRunpod files execute. File-based
specs, reference images and an Openjutsu take's source video are snapshotted as job data
before any balance query, hashed at load, re-hashed before each attempt, and deleted once
the take is done.
No caller argv or environment overrides are forwarded. Batch logs contain counts/
codes, never specs, prompts, environment values or subprocess exception messages.
Child output goes only to each take's run.log, as requested.

Studio specs ("studio": true) are accepted only on a narrow path, else refused at 0 CU:
uploads_dir must be the job's uploads_dir (under WORK); idle_stop_min must be 0 (no warm VM);
lora_dir, vm_dir, data_dir and slot must be absent or null and no scene may carry loras;
every reference file (refs, ref_videos, ref_audios, first_frame, last_frame, chain.prev_clip)
must resolve inside uploads_dir and every scene out_dir inside uploads_dir/renders; progress
must be <take dir>/progress.json. run_take requires those files in place, so they are not
snapshotted: spec.json and every reference are hashed at load and re-hashed right before each
attempt, and a mismatch stops before the take (exit 6, 0 CU for that take). The child reads a
byte-identical copy of the hashed spec from the pinned temp dir. Each out_dir must be empty or
carry this take's id in a .colab_batch_take marker, and no out_dir may be shared with another
take; a folder holding files of unknown origin or another take is refused. The child writes its
state to <parent>/<spec take_id>/, so shutdown is verified against that folder, not the spec's.

Audit scope: file-based takes upload the pinned remote_take.py, take_tail.py and
vm_watchdog.py, plus compiled job data and snapshotted image references. No local
notebook is loaded. Workflow graphs come from PINNED; the file takes openjutsu_object and
openjutsu_people use the pinned third_party/openjutsu graphs and, like studio takes, must be
gpu G4 with fallback_gpus []. Their photo and clip can show a real person, so the pinned tree
and every snapshot (named ref_N / src_N, which run_take prints) sit in a 0700 temp dir under the
first take's parent (WORK), never /tmp, deleted on exit; the batch log never names a file.
Studio takes also upload their references from uploads_dir (hashed as above) and run the
pinned scan_frames.py.
No checkout absolute path is used in the supported path. CLI/auth and VM-installed
third-party packages/weights remain external services, not ComfyRunpod source pins.
The bootstrap is hashed separately. It uses -I -S (no site startup hooks).

IMPORTANT: admission uses budget.max_cu, not a provider-enforced reservation.
The pinned upstream guard polls every 30 seconds and stops AT the take cap; billing
lag and teardown can overshoot. Colab has no provider-enforced ceiling. Bound: each attempt is admitted
only if spent-or-reserved + budget.max_cu + OVERSHOOT_CU fits under --max-credits, and that
sum is reserved (retries included), so a lagging balance cannot admit extra work.
OVERSHOOT_CU (0.5) covers one guard poll plus stop latency plus the largest late-posting
charge seen on G4 in EP01 (about 0.4 CU, estimated: no EP01 take reached its cap).
Studio takes must be gpu G4 with fallback_gpus [] because no other GPU's rate is measured.
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
from typing import NamedTuple

WORK = Path('/opt/MoonieXHQ/Work')
COLAB = '/root/.local/bin/colab'
ENTRY = 'scripts/colab/run_take.py'
ID_RE = re.compile(r'[A-Za-z0-9_-]{1,40}')
OUT_MARK = '.colab_batch_take'
EXIT_FAIL, EXIT_BAD, EXIT_CAP, EXIT_BALANCE, EXIT_CHECKPOINT, EXIT_PIN = range(1, 7)
# Reserved per attempt on top of budget.max_cu: G4 overshoot estimate (about 0.4 CU), rounded up.
OVERSHOOT_CU = Decimal('0.5')
PINNED_FROM = 'c0eb0d94756fa2952114efcf4da127b85870e349'
# Generated from git objects at PINNED_FROM, not from potentially dirty working files.
PINNED = {'scripts/colab/run_take.py': 'b877da8ba2e8c8de034c28837284a5891df749c97673851679b21a06bfebd53e',
    'scripts/colab/remote_take.py': 'a268c6cf73b4ff313c4179d98bcc3cf4b17ce60c256d2cc96971d9fe488133d4',
    'scripts/colab/colabctl.py': 'a949d3c664d936d39a807d97aba9ec6a7def3c775acd8542e8a0f769db1c1b1b',
    'scripts/colab/guard.py': '47e6f6845bf7d94e4c897517d19216516af95208afb9c362e043b37a4137901b',
    'scripts/colab/vm_watchdog.py': '6cf3ba2784787ac0480e0c3e4caef6df2668b680e6287c50a7defc73e83e5c12',
    'scripts/fetch_weights.py': '98370f5d86b6bbcc1d7997fe3da336fd77138cbd8752b02687d732688548fb0c',
    'scripts/render_job.py': '859dfd681aea35d8f765b2c33178e3587ea58071b9cd9b7dcc4cdb6b9c8e987e',
    'scripts/run_tests.py': '2cffa05014ee738e3aab90019ac8c47868cfae0c74aa5e7ce662c9c9f91b6457',
    'scripts/take_tail.py': 'c4a9bf3ae7f520805389a3980b74e4970cd5357c9b49bdade4d66acaf1aeb26b',
    'scripts/scan_frames.py': 'e2367f62c5fa62656712225ada1e8997e9d7c44e8658adb3695928e1ae89075a',
    'scripts/scan_refs.py': 'cb3f95729f2bc0262cb6aa1f2e659acd1e4158db4408afb871c6d39947887210',
    'third_party/openjutsu/object.api.json': 'fbfec05071d7f6d9986ba2650d58db9a0e5810a1e13f8efba36afbbf0f67eee2',
    'third_party/openjutsu/simple.api.json': '24dc5b8ef45788c839beb96b617b404308ddfd8921e89cfd9008442ad29a666a',
    'workflows/facerefine_top.json': '17505ed2880f93b0c45b4222b8c02678fa7240c45feb2b2d765cbe99756fae68',
    'workflows/green_t2v.json': 'f9ec7ecb427390d2d39c7d97caef01a26fe3994cb67331edafbb5f08e8a13db7',
    'workflows/i2v.json': 'eaf57b921dadb0beb04d08fd70b1f9b7cd186c44ac19600a1bdcb7e9e02775be',
    'workflows/i2v_max.json': '2c64525620582bb75dd8801b5490ffdebce37c3b04e9efdff99b5231ca1009fe',
    'workflows/r2v.json': '18bf2df90331f560c0fb0c412b366da3828b5ea5d6657233d07c3081f4c9bf17',
    'workflows/r2v_2pass.json': '21e5bb626c7f2798350f69c6dfbf148293fac2522580ceda8e6d0ff866f2e0ae',
    'workflows/r2v_max.json': 'a7671585807a93f38e4cafdd0f7c39086c51e2ff6dba581d22cedd0ffc30d12a',
    'workflows/r2v_max_hyperflow.json': 'dc64617f8009234cd751ed86116ff4adca5eec80224c0e7f6261175150d9ee6f',
    'workflows/t2v.json': 'f9ec7ecb427390d2d39c7d97caef01a26fe3994cb67331edafbb5f08e8a13db7'}
# The two Openjutsu file takes and the pinned graph run_take loads for each (its OPENJUTSU_*_GRAPH paths).
OPENJUTSU = {'openjutsu_object': 'third_party/openjutsu/object.api.json',
             'openjutsu_people': 'third_party/openjutsu/simple.api.json'}
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


class StaleError(PinError):
    """A studio take's spec, reference or output folder is not what was hashed or checked at load."""


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
def pinned_tree(source, parent=None):
    """The hashed copies the child runs. They live in a 0700 temp dir under `parent` (the takes' folder
    under WORK, never /tmp) beside data/, where the snapshots of a real person's photo and clip go.
    The tree is <temp>/tree and the data <temp>/data: run_take refuses a people file inside its own root."""
    with tempfile.TemporaryDirectory(prefix='.colab-batch-', dir=parent) as name:
        Path(name).chmod(0o700)
        root = Path(name) / 'tree'
        root.mkdir()
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


class Take(NamedTuple):
    directory: Path
    spec: dict
    budget: Decimal
    assets: dict
    studio: dict | None

    @property
    def home(self):
        # run_take writes take_state.json and colab-sessions.json to <--out>/<spec take_id>/.
        # For file-based takes take_id is the folder name; a studio spec brings its own.
        return self.directory.parent / self.spec['take_id']


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def studio_files(scene):
    """Every local file the pinned run_take reads for one studio scene."""
    found = []
    for key in ('refs', 'ref_videos', 'ref_audios'):
        if scene.get(key) is not None:
            if not isinstance(scene[key], list):
                raise JobError(key + ' must be a list')
            found += scene[key]
    found += [scene[key] for key in ('first_frame', 'last_frame') if scene.get(key) is not None]
    chain = scene.get('chain')
    if chain is not None and not isinstance(chain, dict):
        raise JobError('invalid chain')
    if chain and chain.get('prev_clip'):
        found.append(chain['prev_clip'])
    if not all(isinstance(p, str) and Path(p).is_absolute() for p in found):
        raise JobError('studio file paths must be absolute strings')
    return found


def studio_spec(directory, spec, raw, uploads):
    """The narrow studio path (docstring), or JobError. Nothing is copied: run_take needs the
    references in place inside uploads_dir, so they are hashed here and checked again per take."""
    if uploads is None:
        raise JobError('a studio take needs the job uploads_dir')
    if spec['studio'] is not True:
        raise JobError('studio must be exactly true')
    given = spec.get('uploads_dir')
    if not isinstance(given, str) or not Path(given).is_absolute() or Path(given).resolve() != uploads:
        raise JobError('uploads_dir is not the job uploads_dir')
    idle = spec.get('idle_stop_min')
    if isinstance(idle, bool) or not isinstance(idle, (int, float)) or idle != 0:
        raise JobError('idle_stop_min must be 0')
    if spec.get('gpu') != 'G4' or spec.get('fallback_gpus') != []:
        raise JobError('studio takes must be gpu G4 with fallback_gpus []')
    for key in ('lora_dir', 'vm_dir', 'data_dir', 'slot'):
        if spec.get(key) is not None:
            raise JobError(key + ' is refused in studio mode')
    if not isinstance(spec.get('take_id'), str) or not ID_RE.fullmatch(spec['take_id']):
        raise JobError('studio take_id invalid')
    progress = spec.get('progress')
    if not isinstance(progress, str) or not Path(progress).is_absolute() or \
            Path(progress).name != 'progress.json' or Path(progress).parent.resolve() != directory:
        raise JobError('progress must be <take dir>/progress.json')
    renders = (uploads / 'renders').resolve()
    if uploads not in renders.parents:
        raise JobError('renders must resolve inside uploads_dir')
    inputs, outs, hashes = {}, set(), {}
    for position, scene in enumerate(spec['scenes'], 1):
        if not isinstance(scene, dict) or type(scene.get('index')) is not int or scene['index'] != position:
            raise JobError('scene index must be its 1-based position')
        if scene.get('loras') not in (None, []):
            raise JobError('scene loras are refused in studio mode')
        for given in studio_files(scene):
            resolved = Path(given).resolve()
            if uploads not in resolved.parents or not resolved.is_file():
                raise JobError('reference is not a file inside uploads_dir')
            if resolved not in hashes:
                hashes[resolved] = sha256_file(resolved)
            inputs[given] = (str(resolved), hashes[resolved])
        out = scene.get('out_dir')
        if not isinstance(out, str) or not Path(out).is_absolute() or renders not in Path(out).resolve().parents:
            raise JobError('out_dir must be inside uploads_dir/renders')
        outs.add(Path(out).resolve())
    return {'raw': raw, 'sha': hashlib.sha256(raw).hexdigest(), 'inputs': inputs,
            'outs': outs, 'renders': renders}


def check_outputs(studio, take_id, mark):
    """Refuse an out_dir that holds files of another take or of unknown origin. With mark, create
    the folder and stamp it with this take's id, which is what lets a retry reuse its own folder."""
    for out in sorted(studio['outs']):
        if out.resolve() != out or studio['renders'] not in out.parents:
            raise StaleError('out_dir moved')
        if mark:
            out.mkdir(parents=True, exist_ok=True)
        elif not out.exists():
            continue
        names = os.listdir(out)
        stamp = out / OUT_MARK
        if OUT_MARK in names:
            if stamp.is_symlink() or not stamp.is_file():
                raise StaleError('out_dir marker is not a file')
            with open(stamp, 'rb') as handle:
                if handle.read(64) != take_id.encode():
                    raise StaleError('out_dir belongs to another take')
        elif names:
            raise StaleError('out_dir holds files of unknown origin')
        elif mark:
            fd = os.open(stamp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as handle:
                handle.write(take_id)


def studio_ready(directory, studio, take_id):
    """Right before an attempt: spec and every reference still hash to what was loaded, and the
    output folders are this take's alone. Raises StaleError (exit 6, nothing started) otherwise."""
    try:
        if sha256_file(directory / 'spec.json') != studio['sha']:
            raise StaleError('spec.json changed')
        for given, (resolved, digest) in studio['inputs'].items():
            if str(Path(given).resolve()) != resolved or sha256_file(given) != digest:
                raise StaleError('reference changed')
    except OSError:
        raise StaleError('spec or reference unreadable') from None
    check_outputs(studio, take_id, mark=True)


def load_job(path):
    job = json.loads(path.read_text())
    if not isinstance(job, dict) or set(job) - {'takes', 'checkpoints', 'log', 'run_take', 'uploads_dir'}:
        raise JobError('invalid job object')
    log = work_path(job['log'])
    uploads = None
    if job.get('uploads_dir') is not None:
        uploads = work_path(job['uploads_dir'])
        if not uploads.is_dir():
            raise JobError('uploads_dir is not a directory')
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
        raw = (directory / 'spec.json').read_bytes()
        spec = json.loads(raw)
        if not isinstance(spec, dict):
            raise JobError('invalid spec object')
        if not ID_RE.fullmatch(directory.name):
            raise JobError('take directory must be a valid take_id')
        if not spec.get('studio'):
            wf = spec.get('workflow')
            if not isinstance(wf, str) or not re.fullmatch(r'[A-Za-z0-9_]+', wf) or \
                    OPENJUTSU.get(wf, f'workflows/{wf}.json') not in PINNED:
                raise JobError('workflow is not pinned')
            # OVERSHOOT_CU is sized for G4, the only GPU whose rate is measured (as for studio takes).
            if wf in OPENJUTSU and (spec.get('gpu') != 'G4' or spec.get('fallback_gpus') != []):
                raise JobError('openjutsu takes must be gpu G4 with fallback_gpus []')
        budget = number(spec['budget']['max_cu'])
        if not budget or not number(spec['budget']['max_minutes']):
            raise JobError('take budgets must be positive')
        if not isinstance(spec.get('scenes'), list) or not spec['scenes']:
            raise JobError('scenes must be a nonempty list')
        if spec.get('studio'):
            takes.append(Take(directory, spec, budget, {}, studio_spec(directory, spec, raw, uploads)))
            continue
        # Read data once; the child will receive only these bytes, never mutable originals.
        assets = {}
        for obj in [spec, *spec['scenes']]:
            if not isinstance(obj, dict) or not isinstance(obj.get('refs', []), list):
                raise JobError('invalid scene refs')
            files = list(obj.get('refs', []))
            if obj.get('source') is not None:    # the video an Openjutsu take changes, snapshotted like a ref
                files.append(obj['source'])
            for ref in files:
                if not isinstance(ref, str):
                    raise JobError('invalid reference path')
                p = work_path(str(directory / ref))
                data = p.read_bytes()
                assets[ref] = (p.suffix, data, hashlib.sha256(data).hexdigest())
        spec['take_id'] = directory.name
        takes.append(Take(directory, spec, budget, assets, None))
    paths = [str(t.directory) for t in takes]
    if len(paths) != len(set(paths)):
        raise JobError('duplicate takes')
    # Each take owns <parent>/<take_id>/ for its state and its out_dirs; no two takes may share either.
    homes = [t.home for t in takes]
    if len(homes) != len(set(homes)) or any(t.home != t.directory and str(t.home) in paths for t in takes):
        raise JobError('take ids collide with each other or with another take folder')
    owned = [(out, i) for i, t in enumerate(takes) if t.studio for out in t.studio['outs']]
    for a, i in owned:
        for b, j in owned:
            if i != j and (a == b or a in b.parents):
                raise JobError('two takes share or nest an out_dir')
    for t in takes:
        if t.studio:
            try:
                check_outputs(t.studio, t.spec['take_id'], mark=False)
            except StaleError as exc:
                raise JobError(str(exc)) from None
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


def snapshot_spec(data_dir, index, spec, assets):
    """Write the take's data under data_dir/<index>/. Returns the spec path and (path, sha256) for every file
    written, the hashes taken at load, which snapshot_ready checks again before each attempt."""
    dest = data_dir / str(index)
    dest.mkdir(parents=True)
    held, names = [], {}

    def copy(kind, given):
        # run_take prints these names, so they are ref_0.jpg / src_0.mp4: nothing of the original's name.
        if (kind, given) not in names:
            suffix, data, digest = assets[given]
            p = dest / f'{kind}_{sum(k == kind for k, _ in names)}{suffix}'
            p.write_bytes(data)
            if sha256_file(p) != digest:
                raise PinError('snapshot copy mismatch')
            held.append((p, digest))
            names[kind, given] = str(p)
        return names[kind, given]

    spec = json.loads(json.dumps(spec))
    for obj in [spec, *spec['scenes']]:
        if 'refs' in obj:
            obj['refs'] = [copy('ref', r) for r in obj['refs']]
        if obj.get('source') is not None:
            obj['source'] = copy('src', obj['source'])
    path = dest / 'spec.json'
    raw = json.dumps(spec).encode()
    path.write_bytes(raw)
    held.append((path, hashlib.sha256(raw).hexdigest()))
    return path, held


def snapshot_studio_spec(data_dir, index, studio):
    # The exact bytes that were hashed at load; the child never reads the mutable original.
    dest = data_dir / str(index)
    dest.mkdir(parents=True)
    path = dest / 'spec.json'
    path.write_bytes(studio['raw'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != studio['sha']:
        raise PinError('studio spec copy mismatch')
    return path, [(path, studio['sha'])]


def snapshot_ready(held):
    """Right before an attempt: every snapshot file still hashes to what was read at load. Raises StaleError
    (exit 6, nothing started) otherwise."""
    try:
        for path, digest in held:
            if sha256_file(path) != digest:
                raise StaleError('snapshot changed')
    except OSError:
        raise StaleError('snapshot unreadable') from None


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
    need = sum(t.budget + OVERSHOOT_CU for t in takes)
    if need > cap:
        # The whole job must fit before anything runs; the tail goes on another card.
        emit(f'STOP cap job needs {need} CU (budgets + {OVERSHOOT_CU} per take) over cap {cap}; 0 CU spent')
        return EXIT_CAP
    try:
        validator(run['python'], Path(run['root']))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        raise PinError('interpreter trust check failed') from None
    # Under the first take's parent, not /tmp: the snapshots can hold a real person's photo and clip.
    with pinned_tree(Path(run['root']), takes[0].directory.parent) as root:
        data = root.parent / 'data'
        snaps = [snapshot_studio_spec(data, i, t.studio) if t.studio else
                 snapshot_spec(data, i, t.spec, t.assets) for i, t in enumerate(takes)]
        specs = [path for path, _ in snaps]
        start = balance(reader)
        spent = reserved = Decimal(0)
        emit(f'BALANCE {start} spent 0 CU cap {cap}')
        for i, take in enumerate(takes):
            directory, spec, budget = take.directory, take.spec, take.budget
            emit(f'TAKE {i + 1}')
            for attempt in range(1, 4):
                current = balance(reader)
                spent = max(spent, start - current)
                emit(f'BALANCE {current} spent {spent} CU')
                if max(spent, reserved) + budget + OVERSHOOT_CU > cap:
                    emit(f'STOP cap spent {spent} reserved {reserved} next {budget} + {OVERSHOOT_CU}')
                    return EXIT_CAP
                if take.studio:
                    try:
                        studio_ready(directory, take.studio, spec['take_id'])
                    except StaleError:
                        emit(f'REFUSE take {i + 1} spec, reference or output folder changed since load; '
                             f'take not started; spent {spent} CU so far')
                        return EXIT_PIN
                try:
                    snapshot_ready(snaps[i][1])
                except StaleError:
                    emit(f'REFUSE take {i + 1} snapshot changed since load; '
                         f'take not started; spent {spent} CU so far')
                    return EXIT_PIN
                reserved = max(spent, reserved) + budget + OVERSHOOT_CU
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
                        stopped = stopper(run['python'], root, take.home)
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
            shutil.rmtree(data / str(i), ignore_errors=True)    # this take's snapshot is done with
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
