#!/usr/bin/env python3
"""Audit PROMPTS.md before queueing anything for generation.

Every check here exists because the corresponding mistake cost a re-render.
Run it after editing a prompt block and before handing the file to an operator:

    python3 scripts/audit_prompts.py

Exit code is the number of problems found, so it can gate a queue release.
"""
import re
import sys

PROMPTS = '/Users/gob/Projects/Agents/PROMPTS.md'

# Plates that block generation or were cancelled by the CEO.
FORBIDDEN = [
    # '@Motel-Walkway' — UNBLOCKED 2026-08-14 (CEO): replaced the reference
    # image, plate now renders. Was copyright-flagged, blocked the render
    # outright in Scenes 4/6/7/8/9A before the fix. Left this line as a
    # marker in case the new image ever regresses.
    # '@Room-Clean-Rev' — UNBLOCKED 2026-08-17 (CEO): he rebuilt the plate.
    # It was cancelled 08-13 as redundant with @Room-Clean; Scene 8D needs the
    # reverse angle of the room, so it is live again. Left as a marker in case
    # the new plate ever regresses, same as @Motel-Walkway above.
    '@Room-Wreck-Rev',
    '@Room-DoorOut-Down',
    '@Prop-Glasses',       # CEO removed reading glasses from the film
]

# Scenes whose clips are already delivered. Their prompt text is frozen: most
# still carry @Motel-Walkway (unrenderable) and several tag no room at all.
# Both are real defects, but fixing them would restage footage the editor
# already has, so they are reported as QUARANTINED rather than as problems to
# go fix. Nothing in this range may be queued without the CEO.
QUARANTINED = ('4', '5', '6', '7', '8')

MAX_ELEMENTS = 9  # Confirmed 2026-08-14 (task-0ee4a20a): 10 fails 3/3 with a
# generic Higgsfield error indistinguishable from a content rejection; 9
# generates first try, same beat, same plates. Treat 10 as unusable.

# Seedance 2.5 accepts up to 50 reference images (CEO, 2026-08-14) - the
# 9-cap above is a Seedance 2.0 limit only. Scenes generated on 2.5 carry
# "Seedance 2.5" somewhere in their title; give them the real cap instead.
MAX_ELEMENTS_SEEDANCE_25 = 50

TAG = re.compile(r'@[A-Za-z][A-Za-z0-9-]*')


def scene_of(title):
    return title.split()[1].rstrip('—').strip()


def main():
    src = open(PROMPTS).read()
    body = src.split('## The rule for every shot', 1)[1]
    blocks = re.split(r'\n## (?=Scene )', body)

    problems = 0
    quarantined = 0
    for b in blocks[1:]:
        title = b.split('\n', 1)[0].strip()
        code = ''.join(re.findall(r'```(.*?)```', b, re.S))
        if not code:
            continue

        scene = scene_of(title)
        tags = sorted(set(TAG.findall(code)))
        # Exact match, not startswith. Every delivered block in this range is
        # labelled with a bare digit ("4".."8"), but a prefix test also swept
        # in any NEW scene whose label merely starts with one -- Scene 8B, a
        # fresh insert, came out FROZEN on its first audit and would have been
        # silently excluded from generation while still reporting PROBLEMS: 0.
        frozen = scene in QUARANTINED
        flags = []

        if frozen:
            quarantined += 1
            why = []
            if '@Motel-Walkway' in tags:
                why.append('blocked plate')
            if not any(t.startswith('@Room-') for t in tags):
                why.append('no room tag')
            detail = ', '.join(why) or 'delivered'
            print(f'{len(tags):>2}  {title[:56]:<56}   ... FROZEN ({detail})')
            continue

        for f in FORBIDDEN:
            if f in tags:
                flags.append('FORBIDDEN ' + f)
                problems += 1

        cap = MAX_ELEMENTS_SEEDANCE_25 if 'Seedance 2.5' in title else MAX_ELEMENTS
        if len(tags) > cap:
            flags.append(f'OVER CAP ({len(tags)} > {cap})')
            problems += 1

        # The daughter appears in Scene 9 only as the child inside the
        # photograph. Tagging her puts the character in the room and
        # destroys the premise that the mother is alone.
        if scene.startswith('9') and '@Daughter' in tags:
            flags.append('@Daughter must not appear in Scene 9')
            problems += 1

        # Scenes 9, 10 and 11 all happen in room 214, never in a guest room.
        if scene.startswith(('9', '10', '11')) and '@Room-Guest' in tags:
            flags.append('WRONG ROOM — 214 scenes never use @Room-Guest')
            problems += 1

        # A room named in plain words is a room the model invents. Only flag
        # it when the block tags no room at all, so a line that names 214 and
        # then tags it properly does not trip.
        if not any(t.startswith('@Room-') for t in tags):
            if re.search(r'\broom 214\b|\bguest room\b', code, re.I):
                flags.append('UNTAGGED ROOM — names a room but tags none')
                problems += 1

        mark = '   <<< ' + ' | '.join(flags) if flags else ''
        print(f'{len(tags):>2}  {title[:56]:<56}{mark}')

    print()
    if quarantined:
        print(f'{quarantined} block(s) FROZEN (scenes {"/".join(QUARANTINED)}) '
              '— clips already delivered. Their text is knowingly defective; '
              'ask the CEO before queueing or rewriting any of them.')
    print(f'PROBLEMS: {problems}')
    return problems


if __name__ == '__main__':
    sys.exit(min(main(), 125))
