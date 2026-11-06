import json
from tools import kit_overlap
from tests.hub_sync_support import repository, stubs, commit


def test_overlap(repository, stubs):
    repo, _ = repository
    skill = '.claude/skills/demo/SKILL.md'
    commit(repo, skill, 'safe')
    (stubs / 'prs.json').write_text(json.dumps([
        {'number': 1, 'headRefName': 'one', 'files': [{'path': skill}, {'path': 'a.py'}]},
        {'number': 2, 'headRefName': 'two', 'files': [{'path': 'a.py'}, {'path': 'unique'}]},
    ]))
    output = []
    assert kit_overlap.run(repo, contabo=True, out=output.append) == 0
    assert output == [skill + ' | #1, contabo-local', 'a.py | #1, #2']
    output.clear()
    assert kit_overlap.run(repo, contabo=False, out=output.append) == 0
    assert output == ['a.py | #1, #2']


def test_errors_still_zero(repository, stubs):
    repo, _ = repository
    (stubs / 'prs.json').write_text('bad json')
    assert kit_overlap.run(repo, contabo=False, out=lambda s: None) == 0
