"""Build/check prompt-only artwork handoff; never invokes generation services."""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path('/opt/MoonieXHQ')
PLAN = ROOT / 'Agents/Core/worktrees/mooniex-agents__video_editor__task-c7065d2a/docs/reports/task-aa0081cd/ep02_paper_plan.md'
LEGACY = ROOT / 'Agents/Core/worktrees/mooniex-agents__video_editor__task-aa0081cd/docs/reports/task-aa0081cd/ep02_paper_plan.json'
REFERENCE = ROOT / 'Work/ghostrules-full/ep01/paper'
FB = 'Flashback color grade: desaturated sepia, lifted blacks, cold shadows, fine grain, soft vignette; retain the same layered cut-paper material and characters.'


def build():
    constants = {}
    for node in ast.parse((REFERENCE / 'make_scenes.py').read_text()).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('HEAD', 'TAIL'):
                constants[node.targets[0].id] = ast.literal_eval(node.value)
    head, tail = constants['HEAD'], constants['TAIL']
    attach = json.loads((REFERENCE / 'prompts_chatgpt.json').read_text())[0]['attach']
    assert attach == r'C:\Users\passg\ghostrules-paper\key_scene.png'
    scenes = json.loads(LEGACY.read_text())['scenes']
    pattern = r'\*\*(s\d+)\*\*.*?\n- io: \*\*(.*?)\*\*.*?grade: \*\*(.*?)\*\*.*?\n- plate `(.*?)`: (.*)'
    corrected = re.findall(pattern, PLAN.read_text())
    assert len(corrected) == len(scenes) == 77
    rows = []
    for (sid, io, grade, plate, brief), source in zip(corrected, scenes):
        # Confirm the corrected document retains the original visual plan.
        assert (sid, io, grade, plate, brief) == (source['id'], source['io'], source['grade'], source['plate']['id'], source['plate']['brief'])
        scene = brief.removeprefix('FLASHBACK: ').rstrip('. ') + '.'
        additions = []
        if 'young man' in scene:
            additions.append('The young man is Non, a Thai man about 24 in a work shirt; keep his appearance consistent with the other plates.')
        if io == 'indoor':
            additions.append('No drawn rain in this indoor view.')
        if grade == 'FB':
            additions.append(FB)
        elif grade == 'CCTV':
            additions.append('Monochrome green-grey CCTV monitor grade, not a flashback; no screen labels or digits.')
        elif grade == 'D':
            additions.append('Warm golden dawn grade.')
        else:
            additions.append('Normal story grade; preserve the lighting described in the scene.')
        additions.append('All signs, clocks, currency, packaging and equipment remain without readable letters or numerals.')
        prompt = head + scene + ' ' + ' '.join(additions) + tail
        assert prompt.startswith(head) and prompt.endswith(tail)
        assert not re.search(r'\bEP\d*\b|\bepisode\b|ตอนที่\s*\d', prompt, re.I)
        assert not any(char in prompt for char in '«»‹›—')
        assert not re.search(r'blush|red face|red ears', prompt.removesuffix(tail), re.I)
        assert 'No blushing, no red face, no red ears.' in prompt
        rows.append({'name': sid, 'prompt': prompt, 'attach': attach})
    assert len({p[3] for p in corrected}) == 77
    assert len({r['name'] for r in rows}) == len({r['prompt'] for r in rows}) == 77
    assert [r['name'] for r in rows if FB in r['prompt']] == ['s06', 's07', 's40']
    return rows


if __name__ == '__main__':
    rows = build()
    if '--check' in sys.argv:
        assert json.loads(Path(__file__).with_name('prompts_chatgpt.json').read_text()) == rows
        print('PASS: 77 entries, 77 unique plates/prompts, exact EP1 HEAD/TAIL/attach, FB only s06/s07/s40, prompt exclusions.')
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
