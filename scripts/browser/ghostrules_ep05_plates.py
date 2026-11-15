#!/usr/bin/env python3
"""GhostRules EP5 plate prompts -> JSON for tools/chatgpt_images.py (task-ed742f4b).

Reads the accepted plan (PLAN.json, 131 shots) and writes one prompt per shot.
Text only; the images never go in git.

    python3 scripts/browser/ghostrules_ep05_plates.py --out <dir>

Writes <dir>/plates_all.json (+ plates_bNN.json, 30 per batch) and lint-checks
every prompt against the hard rules (no 'blush', one mention of each name, ...).
Method = EP4 (task-0ef63967): every item attaches key_scene.png as style ref.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLAN = "/opt/MoonieXHQ/Work/ghostrules-full/ep05/plan/PLAN.json"
ATTACH = "C:\\Users\\passg\\ghostrules-paper\\key_scene.png"

STYLE = ("Use the attached image as the exact style reference: layered cut-paper diorama, "
         "real paper fibre texture, crisp cut edges, quilled swirl details, charcoal and slate paper. "
         "16:9 wide frame.")
NONE = ("No text, no letters, no numbers, no readable writing anywhere: every sign, page, tag, label, "
        "book cover and clock face is blank paper or unreadable scribble lines. No watermark.")
COOL = ("Cool blue-grey and steel palette, yellow floor line, a little green light only where stated. "
        "Red only on the narrated talisman, lever, phone display or emergency lamp.")
SEPIA = ("Desaturated warm sepia-brown paper palette, low saturation, softer contrast, "
         "an old reconstruction look unlike the cool blue-grey present.")
GUARD = ("Old suburban Thai hospital, intact building and rooms, no cracks, no collapse. "
         "No rain, no raindrops, no moon, no red sky. "
         "Layer preparation: clean uncluttered background behind each moving element, crisp closed "
         "silhouettes, clear contour gaps, no baked-in motion blur or fused shadows; bodies connected, "
         "limbs and faces with distinct paper seams for later masks. Architecture stays locked. "
         "Adults only (18+) if any person appears. Stylised folk-horror paper art, no gore, no blood. "
         "Pale neutral skin tone. No red face. No red ears. No red cheeks.")

NON = ("Non, a slim 28-year-old Thai man with short black hair, pale teal scrub shirt, navy trousers, "
       "white sneakers (he appears exactly once in the picture)")
CHOD = ("Lung Chod, a thin 62-year-old Thai man with cropped grey hair, olive-brown work jacket, grey "
        "trousers and a pronounced limp (he appears exactly once in the picture)")
MORGUE = ("basement morgue with pale green-grey tiled walls, a row of twelve stainless-steel cold lockers, "
          "the ninth locker wrapped in iron chains with a red paper talisman strip, a yellow line painted "
          "on the floor")
DESK = "duty desk with a black leather logbook and a black desk telephone"
LIFT = "inner service lift with steel doors and a small green-lit cabin"
COLD = "cold room behind double swing doors with round glass windows, a steel gurney in the middle"

FR = {
    "medium": "Medium shot, whole action visible with clear space round it.",
    "close": "Close-up, tight crop on the key element with only a hint of the room at the edges.",
    "reverse": "Reverse angle, camera on the opposite side, showing the cause and the reaction.",
}

# key = first shot id of a beat. Value = list of (medium, close, reverse) texts, as many as shots.
B = {
 "S01-01": [f"Stainless-steel cold-storage locker door wrapped in heavy iron chains and a padlock, a torn red paper talisman across the seam, neighbouring lockers in a row, cold blue-grey light. No people.",
            "Chain links and padlock hanging across a locker seam, one link swung to the side, red talisman edge at the corner. No people.",
            f"Looking down a long corridor of twelve lockers toward the one chained locker at the far end, an empty gurney in the foreground. No people."],
 "S01-04": [f"Anonymous night orderly seen from behind in a teal scrub shirt, head turned away, shoulders tense, standing in the {MORGUE}. No face visible.",
            "Close on the anonymous orderly's turned-away head and tense shoulders, hands gripping a clipboard of blank pages. No face visible."],
 "S01-06": [f"A single hand in a teal sleeve pulling a heavy red emergency cooling lever on a steel wall panel, chained locker blurred behind, the locker stays shut. Only the hand and arm appear."],
 "S02-01": [f"Non walking up to the front entrance of an old suburban Thai hospital at night, the whole building intact with rows of dark windows and a short staircase, deep navy night sky paper, no moon, a few small paper stars. {NON}.",
            f"Close on Non at the hospital entrance steps, gripping a small bag strap, looking up at the glass doors, the building edge intact behind him. {NON}.",
            f"Reverse angle from inside the lit entrance hall looking out at Non approaching the glass doors, intact building frame, dark night. {NON}."],
 "S02-04": [f"Non sitting at the {DESK} in the basement, opening a thick temperature record book, lockers in the background. {NON}."],
 "S02-05": [f"Close on Non's hand writing with a pen in the open temperature book at the desk, twelve small blank boxes drawn in a grid, the ninth box left empty. Pen and hand only plus a hint of his sleeve."],
 "S03-01": [f"{CHOD} walking out of the open service lift into the morgue corridor, leaning to one side on his bad leg, leading the way. Non follows one step behind in the background (Non appears exactly once, Chod exactly once). {NON}.",
            f"Close on Lung Chod's limping legs and uneven steps on the tiled floor beside the yellow line, bad leg dragging slightly. Legs and shoes only.",
            f"Reverse angle from the lift looking back at {CHOD}, limping away down the corridor between the lockers."],
 "S03-04": [f"A black leather logbook being lowered by an older hand onto the {DESK}, the cover blank, dust lifting. Only the hand and the book appear."],
 "S03-05": [f"Brass key ring with several keys landing on the desk beside the black logbook, {CHOD} pointing toward the double doors in the background (Chod appears exactly once).",
            "Close on a bunch of old brass keys on a ring landing beside the black logbook on the desk, ring still swinging. No people.",
            f"Reverse angle from the double doors looking back at the desk: keys and logbook, {CHOD} pointing at the camera side while Non stands listening (each named person exactly once). {NON}."],
 "S04-01": [f"{CHOD} stepping into the front lift with a limp, the lift doors half open, a worn lift cabin with a single lamp (Chod appears exactly once)."],
 "S04-02": [f"Non at the {DESK} opening the black logbook to its first page, a hand-drawn rule box at the top drawn as plain lines, the chained locker visible behind him, still shut. {NON}.",
            f"Close on the open black logbook, page one with a plain boxed paragraph of unreadable scribble lines, Non's fingers holding the page edge. Hands and book only.",
            f"Reverse angle from the chained locker looking back at Non reading the logbook at the desk, his face lit by the desk lamp. {NON}."],
 "S04-05": [f"Non reading a boxed line in the logbook about the telephone, one hand held back from the black desk phone beside him, fingers curled away. {NON}."],
 "S05-01": [f"Illustrated rule scene: Non walking with a folder along the corridor toward the temperature log, his head turned away from a white-sheeted shape on a gurney against the wall. {NON}.",
            f"Close on Non's averted face in profile, eyes lowered, folder pressed to his chest, a blurred white shroud at the edge of the frame. {NON}."],
 "S05-03": [f"A hand gently turning a paper toe tag hanging from a string on a shrouded foot, the tag blank, the shroud covering everything above the ankle, no face shown.",
            "Close on the blank paper toe tag swinging on its string between two fingers, white shroud cloth beneath. No face."],
 "S05-05": [f"Non standing just behind the yellow floor line, reaching forward to pull the big red emergency lever on the wall panel, the chained locker beyond. {NON}.",
            f"Close on Non's hand gripping the red lever, the yellow line on the tile just in front of his shoes. Hand and lever only."],
 "S05-07": [f"Rule five: two plain silver coins mid-air flying into the open green-lit lift cabin just before the doors close, Non's arm withdrawing at the edge of the frame. {NON}."],
 "S06-01": [f"Water dripping from a rusty air-conditioning pipe along the ceiling onto the tiled morgue floor, a small puddle with ripple rings, indoors, dim cool light, no rain. No people.",
            "Close on one drop of water falling from the pipe tip toward a puddle on tile, ripple rings below. No people."],
 "S06-03": [f"The black desk telephone ringing once, receiver trembling slightly in its cradle, a dim red display light on its base, the desk and logbook around it. No people.",
            "Close on the receiver and cradle of the black phone, a small red display glowing, coiled cord loose. No people.",
            f"Reverse angle from behind the phone looking across the desk at Non frozen in his chair staring at it. {NON}."],
 "S06-06": [f"Non's hand reaching out toward the black telephone receiver despite the rule, fingers just short of the handle, his face tense in profile. {NON}."],
 "S07-01": [f"Non with the black receiver pressed to his ear, listening, face pale, ears pale skin tone, eyes wide. {NON}.",
            "Close on Non's pale face in profile with the receiver at his ear, pale skin, wide unfocused eyes.",
            f"Reverse angle from over the telephone looking at Non listening, the dark morgue corridor behind his shoulder. {NON}."],
 "S07-04": [f"The black receiver dropping from a hand onto its cradle with a small bounce, the phone's red display lit up, desk lamp light. No face."],
 "S07-05": [f"Coiled telephone cord whipping and recoiling after the receiver falls, dangling beside the desk edge, black phone above. No people.",
            "Close on the coiled cord swinging beneath the dropped receiver, floor tiles below. No people."],
 "S08-01": [f"Non carrying the temperature file toward the cold room doors at the end of the corridor, steps careful, lockers on one side. {NON}."],
 "S08-02": [f"The {COLD}: Non's hand pushing the double doors open, doors swinging inward on their hinges, cold mist spilling at his feet. {NON}.",
            "Close on the two swing doors' round glass windows and steel push plates as they yield, a faint white mist at the bottom edge. No people."],
 "S08-04": [f"Inside the cold room: low white mist drifting round a steel gurney, a paper toe tag lying upside down on the gurney, a white-sheeted shape on it. No people else.",
            "Close on the inverted blank toe tag on the gurney rail with thin white mist curling round it. No people.",
            f"Reverse angle from the far end of the cold room looking back at the swing doors with mist along the floor, the gurney foreground. No people."],
 "S09-01": [f"Non reaching with a pen toward the toe tag on the gurney, arm outstretched, head turned away and eyes down. {NON}.",
            "Close on the pen tip touching the blank toe tag, mist around. Pen and hand only.",
            f"Reverse angle from beside the gurney, Non's averted face and extended arm seen from the shrouded side, only the white sheet edge visible. {NON}."],
 "S09-04": [f"The paper toe tag rolling face-up on its string under a pen tip, blank, a white shroud beneath. Pen tip and tag only."],
 "S09-05": [f"Peripheral view: the white shroud on the gurney slowly rising at the far edge of the frame as if something beneath it breathes, mist round it, Non small and out of focus in the foreground, not looking. {NON}.",
            "Close on the edge of the white shroud cloth lifting slowly from the gurney, no face, no figure revealed, mist. No people."],
 "S10-01": [f"Non's trembling hand writing on the temperature file, the pen wobbling, the page marked with shaky scribble lines. Hand and page only.",
            "Close on the shaking pen tip and wavy ink scribble across a blank grid, nothing readable. Pen and paper only."],
 "S10-03": [f"Non stepping backward away from the gurney without turning his head toward the shroud, folder held low. {NON}."],
 "S10-04": [f"Non's hand pulling the cold-room double doors closed, the ninth locker visible through the round glass window beyond, chains faintly seen, his hand stays on the door. {NON}.",
            "Close on the round glass window of the closing door showing the chained locker as a small dark shape. No people.",
            f"Reverse angle from the corridor side of the doors: Non's pale face behind the glass window pulling the door shut. {NON}."],
 "S11-01": [f"Non at the {DESK} flipping through the black logbook, pages fanning under his fingers, desk lamp light. {NON}."],
 "S11-02": [f"A yellowed single record sheet stapled into the logbook, the staple intact, covered in unreadable faded scribble lines, held flat by two fingers. Hands and page only."],
 "S11-03": [f"{SEPIA} A reconstruction: seven years ago, a covered young woman's body on a gurney being wheeled into the morgue by two anonymous attendants seen from behind. The woman's face stays under the sheet.",
            f"{SEPIA} Close on a pale hand slipping from under a white sheet on a gurney in the morgue. No face."],
 "S11-05": [f"{SEPIA} A reconstruction: an anonymous orderly in a scrub shirt standing before the chained locker at night, one hand lifting toward the padlock but not touching it, his face turned away.",
            f"{SEPIA} Close on a hand hovering near the padlock on the chained locker, fingers trembling, the lock still closed."],
 "S12-01": [f"A plain wall clock with tick marks and no numerals, hands at about a quarter past three, Non sitting below it in the dim morgue holding the black logbook. {NON}.",
            f"Close on the clock face with tick marks only and its hands near a quarter past three. No people.",
            f"Reverse angle from the chained locker looking back at Non seated at the desk under the clock, logbook in his hands. {NON}."],
 "S12-04": [f"The iron chain on the ninth locker shaking taut as if pushed from inside, links jumping, the padlock rattling, talisman strip fluttering. No people.",
            "Close on two chain links pulled tight and jumping against the steel door, padlock shuddering. No people."],
 "S12-06": [f"The ninth locker door bulging outward in one spot as if pressed from inside, the rest of the cabinet bank fixed and flat. No people."],
 "S13-01": [f"A dark liquid seeping out of the gasket seam of the ninth locker door and spreading across the tile floor in a thin stream, cool light. No people.",
            "Close on the dark seep dripping from the locker gasket onto the tile, drops and a widening dark line. No people.",
            f"Reverse angle from the floor looking at the spreading dark seep toward Non's feet at the desk edge. Non's legs only (he appears exactly once)."],
 "S13-04": [f"The locker door bent into a curved bow under pressure, chain pulled tight across it, the rest of the wall unchanged. No people."],
 "S13-05": [f"The red paper talisman strip across the locker seam beginning to tear at the edge, a long split opening, no skin or face anywhere. Close framing on the talisman. No people."],
 "S13-06": [f"Non lunging across the room toward the red breaker lever beside the entrance, body leaning forward, arm reaching. {NON}."],
 "S13-07": [f"Non's hands pulling the big red emergency lever fully down to its lower stop on the wall panel, shoulders braced. {NON}."],
 "S14-01": [f"White frost thickening across the seam of the ninth locker and over the chain links, ice crystals spreading in paper layers, cold blue light. No people.",
            "Close on frost crystals crusting a single chain link and the steel seam. No people.",
            f"Reverse angle from the side along the locker bank, the frosted chained locker glowing pale at the end, Non small and breathing at the near edge (Non exactly once). {NON}."],
 "S14-04": [f"The bulging locker door settling back into its sealed seam, frost covering the seam, chain slack again. No people."],
 "S14-05": [f"Non breathing hard behind the yellow line, hands on knees, never crossing it, the frosted locker in the background. {NON}."],
 "S15-01": [f"Non turning toward the inner service lift as a warning bell sounds at four, the lift door lit by one green lamp above it, clock hint on the wall. {NON}.",
            "Close on the small green lamp and call button above the inner lift door, steel panels, a faint vibration. No people.",
            f"Reverse angle from inside the lift looking out at Non turning to face it in the corridor. {NON}."],
 "S15-04": [f"The inner lift doors sliding slowly open on an empty green-lit cabin, steel panels parting evenly. No people."],
 "S15-05": [f"Hold the empty green-lit lift cabin with Non in the foreground, seen from behind, standing outside the threshold. {NON}."],
 "S15-06": [f"Non looking down at the lift threshold from outside the cabin, feet fixed back beyond the line, head lowered. {NON}."],
 "S15-07": [f"Wet yellowish footprints appearing one by one across the lift cabin floor from the back corner toward the doorway, glossy and damp, no person visible. No people.",
            "Close on a single wet footprint on the steel threshold, next one forming just behind it. No people.",
            f"Reverse angle from inside the cabin at its rear corner looking toward the open doors and Non waiting in the corridor, the first footprints at the camera. {NON}."],
 "S15-CALM": [f"Non waiting outside the lift as the wet footprints reach the threshold, quiet and still, the mirror kept out of frame, only a plain steel wall inside the cabin. {NON}."],
 "S15-REVEAL": [f"THE ONE SCARE: a tall mirror at the back of the lift cabin shows a pale adult woman in a white hospital gown with faint grey-brown stains, long black hair hanging over her bowed face, one thin arm raised in a beckoning curl; big close crop on the mirror and her raised hand and hanging hair. Non is NOT in the mirror and not in the frame. Eerie but stylised, no gore."],
 "S15-10": [f"In the lift's rear mirror a pale woman in a white hospital gown with long black hair over her face, beckoning with one slow hand, her reflection alone in the mirror (Non is not reflected). The mirror edge frames her. No gore."],
 "S15-11": [f"Non's hand reaching into his trouser pocket for coins while he stays outside the lift, eyes fixed on the cabin. {NON}.",
            "Close on Non's hand pulling two plain silver coins from his pocket, only fingers and pocket edge."],
 "S15-13": [f"Exactly two plain silver coins rolling across the lift cabin floor and rolling in, two clear arcs and two small tracks, the cabin empty. No people."],
 "S15-14": [f"Non's finger pressing the exterior close button beside the lift door, repeated presses, button glowing white. {NON}."],
 "S15-15": [f"The lift doors sliding shut, a pale reflected shape of a patient approaching behind the narrowing gap, the shape small and distant. No gore."],
 "S15-16": [f"A distant side view behind the closing lift doors: a patient in a white gown rushing forward in the cabin, seen small through the last gap, long hair swinging, the doors meeting. No gore."],
 "S16-01": [f"Blackout in the morgue: one red emergency lamp lit on the wall, Non recoiling in its glow, skin staying pale beige not red-tinted, the lockers as dark shapes. {NON}.",
            f"Close on Non's pale face in the dim red emergency light, eyes wide, skin pale not red. {NON}."],
 "S16-03": [f"The cold room double doors shaking in their frames under knocking from inside, the round windows rattling, a dark corridor and red lamp glow. No people."],
 "S16-04": [f"The inner lift door panels rattling in their frame, the green lamp flickering, the corridor dark and still. No people.",
            "Close on the seam between the two lift panels trembling as if struck from inside. No people."],
 "S16-06": [f"Non crouching behind the {DESK}, the black logbook clutched to his chest, a red paper talisman stuck on the desk front, the dark morgue behind. {NON}.",
            "Close on Non's white-knuckled hands gripping the black logbook, the talisman strip at the desk edge. Hands and book only."],
 "S16-08": [f"Non crouched with his head bowed low into the book, refusing to look up, faint footprints of unseen steps circling as dark prints on the tile at the frame edge. {NON}."],
 "S16-09": [f"The black desk telephone ringing again and again, receiver shaking, the red display flashing, no hand near it. No people.",
            "Close on the red display and shaking cradle of the black phone, coiled cord twitching. No people.",
            f"Reverse angle from the desk's far side: the ringing phone in the foreground, Non crouched behind it staring at the floor (Non exactly once). {NON}."],
 "S16-12": [f"Non waiting behind the desk through the last hour of the vigil, back against the desk panel, exhausted, the dim morgue with the red lamp glowing. {NON}.",
            "Close on Non's tired face, eyes half closed, dark circles, pale skin tone. {}".format("(Non exactly once)"),
            f"Reverse angle from the dark corridor toward Non at the desk, wall clock above him with tick marks and no numerals. {NON}."],
 "S16-15": [f"The inner lift doors rattling once more then falling still at six in the morning, the green lamp steady, nothing else in the corridor. No people."],
 "S16-16": [f"The cold room going quiet: calm double doors, the mist gone, the ninth locker silent and frosted at the end, lights back to a plain cool glow. No people."],
 "S17-01": [f"{CHOD} limping out of the front lift carrying a steaming cup of hot coffee, morning light colder and calmer in the corridor, steam curling.",
            "Close on a paper cup of hot coffee with steam in an old hand, a trembling wrist, the morgue corridor soft behind it. Hand and cup only.",
            f"Reverse angle from the desk looking toward the lift as {CHOD} limps in with the coffee."],
 "S17-04": [f"Non sitting pale at the desk, nodding slowly while {CHOD} explains, a coffee cup between them (each named person exactly once). {NON}."],
 "S17-05": [f"{SEPIA} Reconstruction: a former night orderly, a middle-aged anonymous man seen from behind in an old scrub shirt, lifting the black desk phone receiver to his ear, the desk lamp dim."],
 "S17-06": [f"{SEPIA} Reconstruction: the same former orderly's hands unwinding the iron chain from the ninth locker, links falling slack, his face turned away.",
            f"{SEPIA} Close on hands lifting a loosened chain link off a locker door, the padlock hanging open."],
 "S18-01": [f"Non receiving two plain pale-grey banknotes from {CHOD} across the duty desk, notes blank without printing, his shift ending, morning light (each named person exactly once). {NON}."],
 "S18-02": [f"Non walking out of the old hospital's main entrance into pale grey-white morning, intact building behind him, short stairs, sky flat pale paper, not red, no moon. {NON}.",
            f"Close on Non's back and shoulders as he walks away down the road beyond the hospital gate, small bag over his shoulder, the intact building edge behind. {NON}.",
            f"Reverse angle from the gate looking back at the intact hospital entrance with Non descending the stairs toward the camera. {NON}."],
 "S18-05": [f"Closing warning vignette: an anonymous hand reaching toward the chained ninth locker and stopping a hand's width from the padlock, the chain still. The hand and cuff only.",
            "Close on a hand held back from the chained locker, fingers open, red talisman strip in the corner, chain still. Hand only."],
}


def build(plan):
    shots = []
    for sc in plan["scenes"]:
        for sh in sc["shots"]:
            shots.append(sh)
    beats = []  # (first_id, [shots])
    cur = None
    for sh in shots:
        k = (sh["source_row"], sh["phrase_anchor"], sh["beat"])
        if cur is None or cur[0] != k:
            cur = [k, []]
            beats.append(cur)
        cur[1].append(sh)
    out = []
    for k, group in beats:
        first = group[0]["id"]
        texts = B[first]
        assert len(texts) == len(group), (first, len(texts), len(group))
        n = len(group)
        for i, sh in enumerate(group):
            fr = sh["framing"].split()[0]  # medium|close|reverse
            fkey = "medium" if fr.startswith("medium") else ("close" if fr.startswith("close") else "reverse")
            grade = SEPIA if sh["grade"].startswith("flashback") else COOL
            body = texts[i]
            if body.startswith("{"):
                body = body
            prompt = f"{STYLE} {NONE} {FR[fkey] if sh['id'] not in ('S15-CALM','S15-REVEAL') else ''} {body} {grade} {GUARD}"
            prompt = re.sub(r"\s+", " ", prompt).strip()
            out.append({"name": sh["id"], "prompt": prompt, "attach": ATTACH})
    return out


def lint(items):
    bad = []
    for it in items:
        p = it["prompt"]
        if re.search(r"blush", p, re.I):
            bad.append((it["name"], "blush word"))
        if re.search(r"\brain\b", p, re.I) and "no rain" not in p.lower():
            bad.append((it["name"], "rain"))
        for nm in ("Non,", "Lung Chod,"):
            if p.count(nm) > 1:
                bad.append((it["name"], f"{nm} described twice"))
        if len(p) > 3500:
            bad.append((it["name"], f"long {len(p)}"))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch", type=int, default=30)
    a = ap.parse_args()
    plan = json.load(open(PLAN, encoding="utf-8"))
    items = build(plan)
    names = [i["name"] for i in items]
    assert len(names) == len(set(names)) == 131, len(names)
    prompts = [i["prompt"] for i in items]
    assert len(set(prompts)) == 131, "duplicate prompts"
    bad = lint(items)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "plates_all.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    for bi in range(0, len(items), a.batch):
        (out / f"plates_b{bi // a.batch:02d}.json").write_text(
            json.dumps(items[bi:bi + a.batch], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} prompts, lint problems: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
