"""Offline spend admission, immutable execution and teardown tests. No Colab calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools import colab_batch as cb


@pytest.fixture(autouse=True)
def no_external_process(monkeypatch):
    monkeypatch.setattr(cb.subprocess, 'run', lambda *a, **k: pytest.fail('unexpected subprocess'))
    monkeypatch.setattr(cb.subprocess, 'Popen', lambda *a, **k: pytest.fail('unexpected child'))


@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, 'WORK', tmp_path)
    source = tmp_path / 'source'
    files = {cb.ENTRY: b'pass\n', 'workflows/r2v.json': b'{}'}
    for rel, data in files.items():
        p = source / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    monkeypatch.setattr(cb, 'PINNED', {k: hashlib.sha256(v).hexdigest() for k, v in files.items()})
    takes = []
    for i in range(2):
        take = tmp_path / f'take{i}'
        take.mkdir()
        (take / 'ref.png').write_bytes(b'image')
        (take / 'spec.json').write_text(json.dumps({'workflow': 'r2v',
            'budget': {'max_cu': 4, 'max_minutes': 2}, 'scenes': [{'refs': ['ref.png']}]}))
        takes.append(str(take))
    data = {'takes': takes, 'checkpoints': [], 'log': str(tmp_path / 'batch.log'),
            'run_take': {'root': str(source), 'python': sys.executable}}
    path = tmp_path / 'job.json'
    path.write_text(json.dumps(data))
    return path


def invoke(job, balances=(100, 100, 98, 98, 96), cap='10', outcomes=(0, 0), messages=None,
           stop=True, seen=None, on_balance=None, on_run=None):
    reads, calls, stops, sleeps = [], [], [], []
    values, results = iter(balances), iter(outcomes)
    def reader():
        reads.append('balance')
        if on_balance:
            on_balance(reads.count('balance'))
        return next(values)
    def runner(python, root, spec, directory, output, timeout):
        assert root.stat().st_mode & 0o777 == 0o700
        assert not (directory / 'progress.json').exists()
        assert timeout == 420
        calls.append(root)
        if seen is not None:
            seen.append(('run', spec, directory, Path(spec).read_bytes()))
        if on_run:
            on_run(len(calls), directory)
        output.write((messages or 'ok\n').encode())
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result
    def stopper(*args):
        if seen is not None:
            seen.append(('stop', args[2]))
        stops.append('stop')
        reads.append('stop')
        return stop
    rc = cb.main(['--job', str(job), '--max-credits', cap], balance_reader=reader,
                 take_runner=runner, stop_runner=stopper, sleep=sleeps.append,
                 interpreter_validator=lambda *a: None)
    assert all(not root.exists() for root in calls)
    return rc, calls, stops, sleeps, reads


def test_happy(job, capsys):
    rc, calls, stops, _, events = invoke(job)
    assert rc == 0 and len(calls) == len(stops) == 2
    assert events == ['balance', 'balance', 'stop', 'balance', 'balance', 'stop', 'balance']
    assert 'DONE spent 4 CU' in capsys.readouterr().out


def test_cap(job):
    # Take 1 spends 5, more than its 4 + 0.5 reservation, so take 2 no longer fits under 9.
    rc, calls, *_ = invoke(job, balances=(100, 100, 95, 95), cap='9')
    assert rc == cb.EXIT_CAP and len(calls) == 1


def test_overshoot_reserve_refuses_at_zero_cu(job):
    # Budgets 4 + 4 fit a cap of 8; with 0.5 reserved per take (9) they do not: nothing runs, no balance read.
    rc, calls, stops, _, events = invoke(job, cap='8')
    assert rc == cb.EXIT_CAP and not calls and not stops and 'balance' not in events


@pytest.mark.parametrize('value', ['', None, 'unreadable', 'nan', 'inf', -1])
def test_balance_refuses(job, value):
    rc, calls, *_ = invoke(job, balances=(100, value))
    assert rc == cb.EXIT_BALANCE and not calls


def test_checkpoint(job):
    data = json.loads(job.read_text())
    data['checkpoints'] = [{'after': data['takes'][:1], 'scenes': 2, 'max_cu_per_scene': 0.4}]
    job.write_text(json.dumps(data))
    rc, calls, *_ = invoke(job)
    assert rc == cb.EXIT_CHECKPOINT and len(calls) == 1


@pytest.mark.parametrize('bad', ['spec', 'ref', 'json'])
def test_preflight_zero_cu(job, bad):
    take = job.parent / 'take1'
    if bad == 'json':
        (take / 'spec.json').write_text('not json')
    else:
        (take / ('spec.json' if bad == 'spec' else 'ref.png')).unlink()
    rc, calls, _, _, reads = invoke(job, balances=())
    assert rc == cb.EXIT_BAD and not calls and not reads


@pytest.mark.parametrize('missing', [False, True])
def test_pin_refuses_zero_cu(job, missing):
    entry = job.parent / 'source' / cb.ENTRY
    if missing:
        entry.unlink()
    else:
        entry.write_text('changed')
    rc, calls, _, _, reads = invoke(job, balances=())
    assert rc == cb.EXIT_PIN and not calls and not reads


def test_source_changed_during_copy(job, monkeypatch):
    copy = cb.shutil.copyfile
    def raced(src, dest):
        src.write_text('changed after preflight')
        return copy(src, dest)
    monkeypatch.setattr(cb.shutil, 'copyfile', raced)
    assert invoke(job, balances=())[0] == cb.EXIT_PIN


@pytest.mark.parametrize('message', ['not found', 'FAILED VM', 'failed in provision', 'failed upload'])
def test_provision_retry(job, message):
    rc, calls, stops, sleeps, _ = invoke(job, balances=(100,) * 7, cap='20',
                                       outcomes=(1, 0, 0), messages=message)
    assert rc == 0 and len(calls) == len(stops) == 3 and sleeps == [60]


def test_other_failure_not_retried(job):
    rc, calls, _, sleeps, _ = invoke(job, outcomes=(1,), messages='render error')
    assert rc == cb.EXIT_FAIL and len(calls) == 1 and not sleeps


def test_retry_limit_and_last_six_lines(job):
    result = invoke(job, balances=(100,) * 7, outcomes=(1, 1, 1), cap='20', messages='failed vm')
    assert result[0] == cb.EXIT_FAIL and len(result[1]) == 3 and result[3] == [60, 60]
    result = invoke(job, outcomes=(1,), messages='failed vm\n' + 'render error\n' * 6)
    assert result[0] == cb.EXIT_FAIL and len(result[1]) == 1


@pytest.mark.parametrize('outcome', [-9, subprocess.TimeoutExpired('fake', 1)])
def test_dead_or_hung_child_stops_before_balance(job, outcome):
    result = invoke(job, outcomes=(outcome,))
    assert result[0] == cb.EXIT_FAIL and result[4] == ['balance', 'balance', 'stop', 'balance']


def test_shutdown_unknown_never_counts_spend_or_retries(job):
    result = invoke(job, balances=(100, 100), outcomes=(1,), stop=False, messages='failed vm')
    assert result[0] == cb.EXIT_SHUTDOWN and result[4] == ['balance', 'balance', 'stop']


def test_retry_cap(job):
    # The failed try spent 5, over its 4 + 0.5 reservation, so the retry no longer fits the cap of 9.
    result = invoke(job, cap='9', balances=(100, 100, 95, 95), outcomes=(1,), messages='failed vm')
    assert result[0] == cb.EXIT_CAP and len(result[1]) == 1


@pytest.mark.parametrize('args', [['--max-c', '10'], ['--max-credits', '10', '--probe-only'],
                                  ['--max-credits', 'nan']])
def test_exact_arguments(job, args):
    with pytest.raises(SystemExit) as exc:
        cb.main(['--job', str(job), *args])
    assert exc.value.code == 2


def test_unpinned_import_fails(job, monkeypatch):
    # Restore subprocess only for this local, harmless fake entry.
    monkeypatch.undo()
    source = job.parent / 'source'
    (source / cb.ENTRY).write_text('import unpinned_module\n')
    (source / 'scripts/colab/unpinned_module.py').write_text("raise RuntimeError('executed')\n")
    monkeypatch.setattr(cb, 'PINNED', {cb.ENTRY: hashlib.sha256((source / cb.ENTRY).read_bytes()).hexdigest()})
    with cb.pinned_tree(source) as root:
        result = subprocess.run([sys.executable, '-I', '-S', str(root / 'bootstrap.py'), 'unused'],
                                cwd=root, capture_output=True, text=True)
        assert result.returncode != 0 and 'ModuleNotFoundError' in result.stderr
        assert 'RuntimeError' not in result.stderr


def test_parent_timeout_kills_process_group(job, monkeypatch):
    killed = []
    class Process:
        pid = 12345
        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired('fake', timeout)
            return -9
    def popen(argv, **kwargs):
        assert argv[1:3] == ['-I', '-S'] and kwargs['start_new_session']
        return Process()
    monkeypatch.setattr(cb.subprocess, 'Popen', popen)
    monkeypatch.setattr(cb.os, 'killpg', lambda *a: killed.append(a))
    with pytest.raises(subprocess.TimeoutExpired):
        cb.run_take(sys.executable, job.parent, job, job.parent, None, 1)
    assert killed == [(12345, cb.signal.SIGKILL)]


def test_bootstrap_shutdown_uses_pinned_colabctl(job, monkeypatch):
    monkeypatch.undo()
    source = job.parent / 'source'
    module = source / 'scripts/colab/colabctl.py'
    module.write_text("import re\nSESSION_RE = re.compile('unused')\nclass ColabError(Exception): pass\nclass Colab:\n def __init__(self, config): pass\ndef stop_vms(c, names, endpoints):\n return {'remaining': 0}\n")
    monkeypatch.setattr(cb, 'PINNED', {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in source.rglob('*.py')})
    with cb.pinned_tree(source) as root:
        assert cb.shutdown(sys.executable, root, job.parent)


def test_interpreter_permissions(job, monkeypatch):
    executable = job.parent / 'python'
    executable.write_text('')
    executable.chmod(0o777)
    with pytest.raises(cb.PinError):
        cb.trusted_interpreter(str(executable), job.parent)


def test_site_hook_refused(job, monkeypatch):
    executable = job.parent / 'bin/python'
    executable.parent.mkdir()
    executable.write_text('')
    executable.chmod(0o755)
    site = job.parent / 'lib/python3.12/site-packages'
    site.mkdir(parents=True)
    (site / 'checkout.pth').write_text(str(job.parent / 'source'))
    monkeypatch.setattr(cb.subprocess, 'run', lambda *a, **k:
                        subprocess.CompletedProcess(a, 0, json.dumps([str(job.parent), [3, 12]])))
    with pytest.raises(cb.PinError):
        cb.trusted_interpreter(str(executable), job.parent / 'source')


@pytest.mark.parametrize('text,code,expected', [
    ('Current balance: 150.25 CU\n', 0, '150.25'),
    ('', 0, None), ('Current balance: unknown', 0, None),
    ('Current balance: 150', 1, None), ('Current balance: NaN', 0, None),
])
def test_usage_parser_is_offline(monkeypatch, text, code, expected):
    def fake(argv, **kwargs):
        assert argv == ['/root/.local/bin/colab', 'usage']
        assert kwargs['timeout'] == 60
        return subprocess.CompletedProcess(argv, code, text, '')
    monkeypatch.setattr(cb.subprocess, 'run', fake)
    if expected is None:
        with pytest.raises(cb.BalanceError):
            cb.read_balance()
    else:
        assert str(cb.read_balance()) == expected


def test_progress_deleted_before_each_try(job):
    for name in ('take0', 'take1'):
        (job.parent / name / 'progress.json').write_text('{}')
    assert invoke(job)[0] == 0


def test_checkpoint_glob(job):
    data = json.loads(job.read_text())
    data['checkpoints'] = [{'after': str(job.parent / 'take*'), 'scenes': 2, 'max_cu_per_scene': 1}]
    job.write_text(json.dumps(data))
    result = invoke(job)
    assert result[0] == cb.EXIT_CHECKPOINT and len(result[1]) == 2


def test_caller_environment_is_not_forwarded(monkeypatch):
    monkeypatch.setenv('PYTHONPATH', '/untrusted')
    monkeypatch.setenv('COLAB_BIN', '/untrusted')
    monkeypatch.setenv('COLAB_WATCHDOG_RELEASE_CMD', 'unsafe')
    assert cb.child_env() == {'PATH': '/usr/bin:/bin', 'HOME': '/root', 'LANG': 'C.UTF-8',
                              'COLAB_BIN': '/root/.local/bin/colab'}


def test_stdlib_only():
    import ast
    tree = ast.parse(Path(cb.__file__).read_text())
    imports = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imports |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imports <= sys.stdlib_module_names


# ---- studio specs: the narrow path (uploads_dir + renders in place, hashed, no warm VM) ----

@pytest.fixture
def studio(job):
    """Two studio takes laid out like the EP02 render: spec.json in colab_up/<folder>, take_id != folder."""
    up = job.parent / 'colab_up'
    data = json.loads(job.read_text())
    takes = []
    for i in range(2):
        folder = up / f'take_ep2_a{i}_x'
        folder.mkdir(parents=True)
        plate = up / f'plate{i}.png'
        plate.write_bytes(b'plate%d' % i)
        scenes = []
        for n in (1, 2):
            out = up / 'renders' / f'x{i}' / f's{n}'
            out.mkdir(parents=True)
            scenes.append({'index': n, 'job_id': f'j{i}{n}', 'out_dir': str(out), 'prompt': 'p',
                           'seconds': 5, 'aspect': '16:9', 'quality': 'fast', 'seed': n,
                           'refs': [str(plate)]})
        spec = {'take_id': f'ep02-a{i}', 'studio': True, 'uploads_dir': str(up), 'idle_stop_min': 0,
                'progress': str(folder / 'progress.json'), 'h3_model': 'studio_bf16', 'gpu': 'G4', 'fallback_gpus': [],
                'budget': {'max_cu': 4, 'max_minutes': 2}, 'scenes': scenes}
        (folder / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')   # not compact: the child must get these bytes
        takes.append(str(folder))
    data.update(takes=takes, uploads_dir=str(up))
    job.write_text(json.dumps(data))
    return type('Studio', (), {'job': job, 'up': up, 'takes': [Path(t) for t in takes],
                               'work': job.parent})


def edit_spec(studio, change, i=0):
    path = studio.takes[i] / 'spec.json'
    spec = json.loads(path.read_text())
    change(spec)
    path.write_text(json.dumps(spec, indent=1) + '\n')


def refused_at_load(studio, reason):
    with pytest.raises(cb.JobError, match=reason):
        cb.load_job(studio.job)
    rc, calls, stops, _, reads = invoke(studio.job, balances=())
    assert rc == cb.EXIT_BAD and not calls and not stops and not reads


def test_studio_happy_path(studio):
    seen = []
    rc, calls, stops, *_ = invoke(studio.job, seen=seen)
    assert rc == 0 and len(calls) == len(stops) == 2
    runs = [s for s in seen if s[0] == 'run']
    for (_, spec, directory, data), folder in zip(runs, studio.takes):
        assert directory == folder
        assert data == (folder / 'spec.json').read_bytes()     # the hashed bytes, nothing rewritten
        assert Path(spec) != folder / 'spec.json'              # but read from the pinned temp tree
    # shutdown targets the folder run_take really writes: <parent>/<spec take_id>, not the take folder
    assert [s[1] for s in seen if s[0] == 'stop'] == [studio.up / 'ep02-a0', studio.up / 'ep02-a1']
    for n, i in ((1, 0), (2, 1)):
        out = studio.up / 'renders' / f'x{i}' / f's{n}'
        assert (out / cb.OUT_MARK).read_text() == f'ep02-a{i}'


def test_studio_accepts_null_and_empty_optional_keys(studio):
    def nulls(spec):
        spec.update(lora_dir=None, vm_dir=None, data_dir=None, slot=None)
        spec['scenes'][0]['loras'] = []
        spec['scenes'][1]['loras'] = None
    edit_spec(studio, nulls)
    assert invoke(studio.job)[0] == 0


def test_studio_references_all_kinds_are_checked_and_hashed(studio):
    clip = studio.up / 'clip.mp4'
    clip.write_bytes(b'clip')
    def more(spec):
        spec['scenes'][1].update(ref_videos=[str(clip)], first_frame=str(studio.up / 'plate0.png'),
                                 chain={'mode': 'continue', 'prev_clip': str(clip)})
    edit_spec(studio, more)
    log, run, takes, _ = cb.load_job(studio.job)
    assert str(clip) in takes[0].studio['inputs']
    assert len(takes[0].studio['inputs']) == 2                 # plate0 (refs and first_frame) and the clip
    assert takes[0].studio['inputs'][str(clip)][1] == hashlib.sha256(b'clip').hexdigest()


@pytest.mark.parametrize('where', ['different', 'outside', 'relative', 'missing', 'not_a_string'])
def test_studio_refuses_other_uploads_dir(studio, where):
    value = {'different': str(studio.up / 'renders'), 'outside': '/etc', 'relative': 'colab_up',
             'not_a_string': ['x']}.get(where)
    def change(spec):
        if where == 'missing':
            del spec['uploads_dir']
        else:
            spec['uploads_dir'] = value
    edit_spec(studio, change)
    refused_at_load(studio, 'uploads_dir')


def test_studio_refuses_a_job_without_uploads_dir(studio):
    data = json.loads(studio.job.read_text())
    del data['uploads_dir']
    studio.job.write_text(json.dumps(data))
    refused_at_load(studio, 'job uploads_dir')


@pytest.mark.parametrize('value', ['/etc', 'elsewhere'])
def test_studio_refuses_a_job_uploads_dir_outside_work(studio, value):
    data = json.loads(studio.job.read_text())
    data['uploads_dir'] = value
    studio.job.write_text(json.dumps(data))
    with pytest.raises(cb.JobError):
        cb.load_job(studio.job)
    assert invoke(studio.job, balances=())[0] == cb.EXIT_BAD


@pytest.mark.parametrize('value', [10, 0.5, 1, True, False, '0', None, 'absent'])
def test_studio_refuses_idle_stop_other_than_zero(studio, value):
    def change(spec):
        if value == 'absent':
            del spec['idle_stop_min']
        else:
            spec['idle_stop_min'] = value
    edit_spec(studio, change)
    refused_at_load(studio, 'idle_stop_min')


@pytest.mark.parametrize('key', ['lora_dir', 'vm_dir', 'data_dir', 'slot'])
def test_studio_refuses_each_extra_location(studio, key):
    edit_spec(studio, lambda spec: spec.update({key: str(studio.up)}))
    refused_at_load(studio, key)


@pytest.mark.parametrize('loras', [[{'path': 'x.safetensors'}], ['x'], 'x', {'a': 1}])
def test_studio_refuses_scene_loras(studio, loras):
    edit_spec(studio, lambda spec: spec['scenes'][1].update(loras=loras))
    refused_at_load(studio, 'loras')


def link(path, target):
    path.unlink(missing_ok=True)
    path.symlink_to(target)


@pytest.mark.parametrize('how', ['abs_outside', 'symlink_out', 'relative', 'missing', 'directory', 'traversal'])
def test_studio_refuses_a_reference_outside_uploads(studio, how):
    outside = studio.work / 'outside.png'
    outside.write_bytes(b'x')
    plate = studio.up / 'plate0.png'
    refs = {'abs_outside': str(outside), 'relative': 'plate0.png', 'missing': str(studio.up / 'gone.png'),
            'directory': str(studio.up / 'renders'), 'traversal': str(studio.up / 'renders' / '..' / '..' / 'outside.png'),
            'symlink_out': str(plate)}[how]
    if how == 'symlink_out':
        link(plate, outside)
    edit_spec(studio, lambda spec: spec['scenes'][0].update(refs=[refs]))
    refused_at_load(studio, 'reference|absolute')


@pytest.mark.parametrize('key', ['ref_videos', 'ref_audios', 'first_frame', 'last_frame', 'prev_clip'])
def test_studio_refuses_every_kind_of_file_key_outside_uploads(studio, key):
    outside = studio.work / 'outside.bin'
    outside.write_bytes(b'x')
    def change(spec):
        scene = spec['scenes'][0]
        if key == 'prev_clip':
            scene['chain'] = {'mode': 'continue', 'prev_clip': str(outside)}
        elif key in ('first_frame', 'last_frame'):
            scene[key] = str(outside)
        else:
            scene[key] = [str(outside)]
    edit_spec(studio, change)
    refused_at_load(studio, 'reference')


@pytest.mark.parametrize('how', ['elsewhere', 'renders_itself', 'traversal', 'relative', 'symlink_out'])
def test_studio_refuses_an_out_dir_outside_renders(studio, how):
    renders = studio.up / 'renders'
    value = {'elsewhere': str(studio.up / 'elsewhere'), 'renders_itself': str(renders),
             'traversal': str(renders / 'x0' / '..' / '..' / 'plain'), 'relative': 'renders/x0/s1',
             'symlink_out': str(renders / 'x0' / 's1')}[how]
    if how == 'symlink_out':
        (renders / 'x0' / 's1').rmdir()
        (renders / 'x0' / 's1').symlink_to(studio.work)
    edit_spec(studio, lambda spec: spec['scenes'][0].update(out_dir=value))
    refused_at_load(studio, 'out_dir')


def test_studio_refuses_progress_elsewhere(studio):
    edit_spec(studio, lambda spec: spec.update(progress=str(studio.up / 'progress.json')))
    refused_at_load(studio, 'progress')


@pytest.mark.parametrize('value', ['yes', 1, 'true', [True]])
def test_studio_must_be_exactly_true(studio, value):
    edit_spec(studio, lambda spec: spec.update(studio=value))
    refused_at_load(studio, 'studio must be exactly true')


@pytest.mark.parametrize('value', ['../x', 'a b', '', 'x' * 41, 7, None])
def test_studio_refuses_a_bad_take_id(studio, value):
    edit_spec(studio, lambda spec: spec.update(take_id=value))
    refused_at_load(studio, 'take_id')


def test_studio_refuses_two_takes_with_one_take_id(studio):
    edit_spec(studio, lambda spec: spec.update(take_id='ep02-a0'), i=1)
    refused_at_load(studio, 'collide')


def test_studio_refuses_a_take_id_that_is_another_take_folder(studio):
    edit_spec(studio, lambda spec: spec.update(take_id=studio.takes[1].name))
    refused_at_load(studio, 'collide')


@pytest.mark.parametrize('nested', [False, True])
def test_studio_refuses_two_takes_sharing_an_out_dir(studio, nested):
    shared = json.loads((studio.takes[0] / 'spec.json').read_text())['scenes'][0]['out_dir']
    value = str(Path(shared) / 'inner') if nested else shared
    edit_spec(studio, lambda spec: spec['scenes'][0].update(out_dir=value), i=1)
    refused_at_load(studio, 'out_dir')


def test_studio_refuses_an_out_dir_two_scenes_of_one_take_share_only_through_the_marker(studio):
    # one take may reuse its own folder for two scenes; the marker is its id either way
    first = json.loads((studio.takes[0] / 'spec.json').read_text())['scenes'][0]['out_dir']
    edit_spec(studio, lambda spec: spec['scenes'][1].update(out_dir=first))
    assert invoke(studio.job)[0] == 0


@pytest.mark.parametrize('content', ['ep02-a1', 'other', ''])
def test_studio_refuses_an_out_dir_marked_by_another_take(studio, content):
    out = studio.up / 'renders' / 'x0' / 's1'
    (out / cb.OUT_MARK).write_text(content)
    refused_at_load(studio, 'out_dir')


def test_studio_refuses_an_out_dir_holding_unmarked_files(studio):
    (studio.up / 'renders' / 'x0' / 's2' / 'colab_01.mp4').write_bytes(b'old')
    refused_at_load(studio, 'out_dir')


def test_studio_refuses_an_out_dir_whose_marker_is_a_symlink(studio):
    out = studio.up / 'renders' / 'x0' / 's1'
    (out / cb.OUT_MARK).symlink_to(studio.up / 'plate0.png')
    refused_at_load(studio, 'out_dir')


def test_studio_scene_index_must_be_its_position(studio):
    edit_spec(studio, lambda spec: spec['scenes'][1].update(index=5))
    refused_at_load(studio, 'index')


def test_studio_never_mixes_into_the_file_based_checks(job):
    # a studio-looking spec in a job without uploads_dir, and a file-based spec in a studio job
    spec = {'studio': True, 'budget': {'max_cu': 4, 'max_minutes': 2}, 'scenes': [{'refs': []}]}
    (job.parent / 'take0' / 'spec.json').write_text(json.dumps(spec))
    with pytest.raises(cb.JobError, match='uploads_dir'):
        cb.load_job(job)


# ---- the pre-take re-check: hashes and output folders, then nothing starts ----

def mutate_at(n, change):
    return lambda count: count == n and change()


@pytest.mark.parametrize('what', ['ref_bytes', 'ref_deleted', 'ref_symlinked', 'spec_bytes', 'spec_deleted'])
def test_studio_input_changed_after_load_stops_before_the_take(studio, what, capsys):
    plate = studio.up / 'plate0.png'
    other = studio.up / 'other.png'
    other.write_bytes(b'different')
    def change():
        if what == 'ref_bytes':
            plate.write_bytes(b'swapped')
        elif what == 'ref_deleted':
            plate.unlink()
        elif what == 'ref_symlinked':
            plate.unlink()
            plate.symlink_to(other)
        elif what == 'spec_bytes':
            (studio.takes[0] / 'spec.json').write_text(json.dumps({'studio': True}))
        else:
            (studio.takes[0] / 'spec.json').unlink()
    rc, calls, stops, _, reads = invoke(studio.job, on_balance=mutate_at(2, change))
    assert rc == cb.EXIT_PIN and not calls and not stops
    assert reads == ['balance', 'balance']                      # initial read, then the one before take 1
    out = capsys.readouterr().out
    assert 'changed since load' in out and 'take not started' in out and 'spent 0' in out


def test_studio_reference_retargeted_to_identical_bytes_still_stops(studio):
    plate = studio.up / 'plate0.png'
    twin = studio.up / 'twin.png'
    twin.write_bytes(plate.read_bytes())
    def retarget():
        plate.unlink()
        plate.symlink_to(twin)
    rc, calls, *_ = invoke(studio.job, on_balance=mutate_at(2, retarget))
    assert rc == cb.EXIT_PIN and not calls


def test_studio_change_after_the_first_take_stops_the_second_before_its_runner(studio, capsys):
    def change():
        (studio.up / 'plate1.png').write_bytes(b'swapped')
    # reads: 1 initial, 2 before take 1, 3 after take 1, 4 before take 2
    rc, calls, stops, *_ = invoke(studio.job, on_balance=mutate_at(4, change))
    assert rc == cb.EXIT_PIN and len(calls) == 1 and len(stops) == 1
    assert 'spent 2' in capsys.readouterr().out


def test_studio_unchanged_by_a_take_that_wrote_into_an_unrelated_ref_is_not_blamed(studio):
    # the first take rewriting take 2's plate would be caught; one that does not touch it is fine
    assert invoke(studio.job, on_run=lambda n, d: None)[0] == 0


def test_studio_stray_file_in_an_out_dir_after_load_stops_before_the_take(studio):
    stray = studio.up / 'renders' / 'x0' / 's2' / 'colab_01.mp4'
    rc, calls, *_ = invoke(studio.job, on_balance=mutate_at(2, lambda: stray.write_bytes(b'old')))
    assert rc == cb.EXIT_PIN and not calls


def test_studio_another_takes_marker_in_an_out_dir_after_load_stops_before_the_take(studio):
    mark = studio.up / 'renders' / 'x1' / 's1' / cb.OUT_MARK
    rc, calls, *_ = invoke(studio.job, on_balance=mutate_at(4, lambda: mark.write_text('ep02-a0')))
    assert rc == cb.EXIT_PIN and len(calls) == 1


def test_studio_out_dir_swapped_for_a_link_after_load_stops_before_the_take(studio):
    out = studio.up / 'renders' / 'x0' / 's1'
    empty = studio.work / 'empty_elsewhere'
    empty.mkdir()
    def swap():
        out.rmdir()
        out.symlink_to(empty)
    rc, calls, *_ = invoke(studio.job, on_balance=mutate_at(2, swap))
    assert rc == cb.EXIT_PIN and not calls and not list(empty.iterdir())


def test_studio_a_retry_keeps_its_own_partial_output(studio):
    partial = studio.up / 'renders' / 'x0' / 's1' / 'colab_01.mp4'
    written = []
    def on_run(n, directory):
        if n == 1:
            partial.write_bytes(b'half')
            written.append(n)
    rc, calls, _, sleeps, _ = invoke(studio.job, balances=(100,) * 6 + (99,), cap='20',
                                     outcomes=(1, 0, 0), messages='Session not found\n', on_run=on_run)
    assert rc == 0 and len(calls) == 3 and sleeps == [60] and written == [1]
    assert partial.read_bytes() == b'half'
    assert (partial.parent / cb.OUT_MARK).read_text() == 'ep02-a0'


def test_studio_spends_nothing_on_a_refused_spec_even_with_a_good_first_take(studio):
    edit_spec(studio, lambda spec: spec.update(idle_stop_min=10), i=1)
    refused_at_load(studio, 'idle_stop_min')                    # take 1 is fine; the job still starts nothing


@pytest.mark.parametrize('change', [
    lambda s: s.update(gpu='H100'),
    lambda s: s.pop('gpu'),
    lambda s: s.update(fallback_gpus=['H100']),
    lambda s: s.pop('fallback_gpus'),   # run_take would then fall back to H100 and A100
])
def test_studio_refuses_other_gpus(studio, change):
    edit_spec(studio, change)
    rc, calls, *_ = invoke(studio.job)
    assert rc == cb.EXIT_BAD and not calls
