"""Stop hook checks only the current user turn and bounded transcript tail."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('relay_hook', ROOT / 'scripts' / 'hook-ph-shell-relay.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

SHELL = {'ORG_PH_SHELL': '1'}


def user(text):
    return {'type': 'user', 'message': {'content': text}}


def assistant(*parts):
    return {'type': 'assistant', 'message': {'content': list(parts)}}


def bash(command):
    return {'type': 'tool_use', 'name': 'Bash', 'input': {'command': command}}


def run(tmp_path, records, **payload):
    path = tmp_path / 'transcript.jsonl'
    path.write_text(''.join(json.dumps(item) + '\n' for item in records), encoding='utf-8')
    return hook.decide({'transcript_path': str(path), **payload}, SHELL)


def test_relayed_turn_passes(tmp_path):
    assert run(tmp_path, [user('q'), assistant(bash('bash scripts/hub/org-python.sh tools/ph_brain.py turn --ph x'))]) is None
    assert run(tmp_path, [user('q'), assistant(bash('tools/ph_brain.py delegate --ph x'))]) is None
    assert run(tmp_path, [user('q'), assistant(bash('tools/ask_run.py ask --question q'))]) is None


def test_self_answer_blocked_once_and_prior_relay_does_not_count(tmp_path):
    records = [user('old'), assistant(bash('tools/ph_brain.py turn --ph x')),
               user('new'), {'type': 'user', 'message': {'content': [
                   {'type': 'tool_result', 'tool_use_id': 'x', 'content': 'ok'}]}},
               assistant({'type': 'text', 'text': 'I decided myself'})]
    result = run(tmp_path, records)
    assert result['decision'] == 'block'
    assert 'ph_brain.py turn' in result['reason']
    assert run(tmp_path, records, stop_hook_active=True) is None


def test_non_shell_and_malformed_fail_open(tmp_path, monkeypatch, capsys):
    assert hook.decide({'transcript_path': str(tmp_path / 'missing')}, {}) is None
    path = tmp_path / 'non_shell.jsonl'
    path.write_text(json.dumps(user('q')) + '\n' + json.dumps(assistant({'type': 'text', 'text': 'self answer'})) + '\n')
    assert hook.decide({'transcript_path': str(path)}, {}) is None
    assert run(tmp_path, [user('q'), assistant({'type': 'text', 'text': 'tools/ph_brain.py turn'})],
               stop_hook_active=True) is None
    path = tmp_path / 'broken.jsonl'
    path.write_text('{broken\n')
    import io
    monkeypatch.setattr(hook.sys, 'stdin', io.StringIO(json.dumps({'transcript_path': str(path)})))
    monkeypatch.setattr(hook.os, 'environ', SHELL)
    assert hook.main() == 0
    assert capsys.readouterr().out == ''


def test_huge_transcript_reads_only_tail(tmp_path, monkeypatch):
    path = tmp_path / 'huge.jsonl'
    path.write_bytes(b'x' * (3 * 1024 * 1024) + b'\n' +
                     (json.dumps(user('latest')) + '\n' + json.dumps(assistant({'type': 'text', 'text': 'answer'})) + '\n').encode())
    opened = []
    real_open = open

    class Tracked:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def seek(self, *args):
            opened.append(('seek', args))
            return self.stream.seek(*args)

        def read(self, size):
            opened.append(('read', size))
            return self.stream.read(size)

    monkeypatch.setattr('builtins.open', lambda *a, **k: Tracked(real_open(*a, **k)))
    assert hook.decide({'transcript_path': str(path)}, SHELL)['decision'] == 'block'
    assert ('read', hook.TAIL_BYTES) in opened
    assert any(kind == 'seek' and args[0] > 0 for kind, args in opened if args[1:] == ())


def test_readonly_lookup_answers_without_brain():
    import importlib.util, json, tempfile, os
    spec = importlib.util.spec_from_file_location("h", os.path.join(os.path.dirname(__file__), "..", "scripts", "hook-ph-shell-relay.py"))
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    def run(cmd):
        recs = [{"type": "user", "message": {"content": "งานถึงไหน"}},
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(json.dumps(r) for r in recs))
        return h.decide({"transcript_path": f.name}, env={"ORG_PH_SHELL": "1"})
    assert run("head -40 docs/plans/cndrama-STATUS.md") is None
    assert run("bash scripts/hub/org-python.sh tools/ph_brain.py status") is None
    assert run("bash scripts/live-sessions.sh") is None
    assert run("head docs/plans/cndrama-STATUS.md; rm -rf x") is not None
    assert run("python3 tools/delegate.py go") is not None
