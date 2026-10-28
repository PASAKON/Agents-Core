import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def hub(tmp_path):
    target = tmp_path / 'disk-hub.py'
    shutil.copyfile(ROOT / 'tests/fixtures/disk_hub/disk-hub.py', target)
    subprocess.run(['patch', '-p1', '-i', str(ROOT / 'deploy/disk-hub/disk-hub-steward.patch')],
                   cwd=tmp_path, check=True, capture_output=True)
    spec = importlib.util.spec_from_file_location('patched_disk_hub', target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DATA_DIR = tmp_path / 'data'
    module.PUSH_TOKEN = 'test-only'
    return module


def post(hub, body):
    handler = object.__new__(hub.Handler)
    handler.path = '/disk?k=test-only&host=mac'
    raw = json.dumps(body).encode()
    handler.headers = {'Content-Length': str(len(raw))}
    handler.rfile = io.BytesIO(raw)
    replies = []
    handler._send = lambda code, payload: replies.append((code, payload))
    handler.do_POST()
    return replies[0]


def body():
    return {'volumes': [{'name': '/', 'mount': '/', 'size_bytes': 100, 'free_bytes': 50}]}


def test_old_new_and_regular_push_preserves_last_tick(hub):
    assert post(hub, body())[0] == 200
    latest = hub.DATA_DIR / 'mac.json'
    assert 'steward' not in json.loads(latest.read_text())
    steward = dict(band='green', tick_at='2026-10-28T12:00:00+00:00', actions=3)
    assert post(hub, {**body(), 'steward': steward})[0] == 200
    assert json.loads(latest.read_text())['steward'] == steward
    history = hub.DATA_DIR / 'mac.hist.jsonl'
    assert json.loads(history.read_text().splitlines()[-1])['band'] == 'green'
    assert post(hub, body())[0] == 200
    assert json.loads(latest.read_text())['steward'] == steward


@pytest.mark.parametrize('bad', [None, [], {}, {'extra': 1},
    dict(band=1, tick_at='2026-10-28T00:00:00Z', actions=0),
    dict(band='x'*11, tick_at='2026-10-28T00:00:00Z', actions=0),
    dict(band='red', tick_at='invalid', actions=0),
    dict(band='red', tick_at='2026-10-28', actions=0),
    dict(band='red', tick_at='x'*41, actions=0),
    dict(band='red', tick_at='2026-10-28T00:00:00Z', actions=True),
    dict(band='red', tick_at='2026-10-28T00:00:00Z', actions=-1)])
def test_strict_validation(hub, bad):
    assert post(hub, {**body(), 'steward': bad})[0] == 400
    assert not (hub.DATA_DIR / 'mac.json').exists()
