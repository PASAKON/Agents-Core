#!/usr/bin/env python3
"""The Old Telling EP1, first minute (Thai): the four shot prompts as DATA, written to files by one template.

Run:  python3 docs/prompts/the-old-telling-ep1/build.py
Writes shots/e01..e04.txt (notes + paste block) and shots/cards.json (the body of the four
POST /api/scenes/enqueue calls, one card each: the clips change room, so no chain).
Refuses when an @reference appears twice in a paste block (CMO_Standard_Film_PromptFormat rule 2).
Spec: CMO_Standard_Film_PromptFormat, CMO_Knowledge_MiniMax_H3. Narration is NEVER bound to H3.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
OUT = HERE / "shots"
OUT.mkdir(exist_ok=True)

SECONDS, QUALITY, ASPECT = 15, "1080p", "16:9"

REFS = {
    "ORPHEUS": "@ORPHEUS: ORPHEUS, an adult man in his late twenties, a Thracian musician: dark curly shoulder-length hair held by a band of olive leaves, short dark beard, plain undyed wool tunic with a rope belt, dark wool cloak over one shoulder with a narrow amber-ochre border stripe, leather sandals. Face, body and clothes only; take nothing of the background.",
    "ORPHEUS_ASHEN": "@ORPHEUS_ASHEN: ORPHEUS after the climb out of the cave, an adult man in his late twenties: the same face, curly hair and short dark beard as always, the olive-leaf band slipped a little to one side, the plain wool tunic and the dark cloak with its amber-ochre border stripe now dusted grey with cave dust and damp at the hem, a faint grey smudge on one cheek, leather sandals. Face, body and clothes only; take nothing of the background.",
    "ANIMALS": "@ANIMALS: THE THREE WILD ANIMALS: a red-brown roe deer with a pale underside and no antlers, a grey wolf with a pale chest, and a rust-orange fox with a white-tipped tail. Their coats, shapes and sizes only; take nothing of the background.",
    "EURYDICE": "@EURYDICE: HER DRESS: a long pale undyed linen ancient Greek dress with a long pale veil draped over it. Cloth shape and colour only; she is only ever a dark silhouette with no face and no detail; take nothing of the background.",
    "LYRE": "@LYRE: THE LYRE, his ancient Greek lyre: aged dark-amber wood, a deep rounded body, two curved arms ending in small scrolls, a straight crossbar, seven strings. Shape and wood only; take nothing of the background.",
    "MEADOW": "@MEADOW: THE RIVER MEADOW: a wide river meadow at dusk, a slow river bending through tall grass, a few old olive trees on the bank, a long low ridge on the far horizon, one large flat grey stone lying in the tall grass in the left third near the camera. Take the whole place and its light from it.",
    "MEADOW_GREY": "@MEADOW_GREY: THE RIVER MEADOW AFTER THE SUN IS GONE: the same meadow, the same flat grey stone, olive trees and far ridge, the sky grey-green and dull, the river dull grey with one last faint ember glow on the water, the grass dark and muted. Take the whole place and its light from it.",
    "STAIR": "@STAIR: THE STAIR: a narrow rough-cut wet stone stair climbing steeply through a dark cavern toward a small opening of pale daylight at the top. Take the whole place and its light from it.",
    "THRONES": "@THRONES: THE THRONES: two tall rough-cut black stone thrones side by side in a dark hall, THE KING OF THE DEAD seated on the left one and THE QUEEN OF THE DEAD on the right one, both in plain black stone crowns and long black robes, ash-grey skin. Take the thrones, the two seated figures and the hall's light from it.",
    "KING": "@KING: THE KING OF THE DEAD, a tall pale adult man in his forties, ash-grey skin, stern lean face, short dark hair, plain black stone crown, long black robe with a high collar. Face and clothes only; take nothing of the background.",
    "TELLER_ROOM": "@TELLER_ROOM: THE TELLER'S ROOM: a dark room, a small oil lamp on a worn wooden table, a tall shelf of identical leather-bound books with blank spines, two aged hands with ink-stained fingertips and one plain iron ring on the right ring finger resting on an open book. Take the whole place and its light from it.",
}

GRADE = ("Colour grade: a moving classical oil painting. Hearth-ember orange firelight is the only warm light; "
         "cold deep verdigris green-black everywhere else; parchment-cream highlights; near-black shadows; "
         "no pure white, no pure black. Fine film grain, soft anamorphic edges. Photographed, not glossy CGI.")

HOUSE_NEG = ("House negatives: no text, no subtitles, no captions, no logos, no watermark; no grid, no split screen, no panels, no collage; "
             "no cartoon, no anime, no plastic skin, no glossy CGI; no gore, no blood, no wounds, no skulls; no nudity; "
             "no child, no minor; no modern objects; no neon; no music, no score, no choir; no lens flare, no dutch angle; "
             "no blush, no red cheeks, no red ears, even natural skin tone.")

SPEECH = ("<Audio 1> is the finished dialogue track of this shot.\n"
          "<Audio 1>: fully_copy - the soundtrack plays <Audio 1> exactly as given: the same voice, the same word, the same timing.\n"
          "Speech timing: ORPHEUS speaks from 9.5 s to 10.6 s. ORPHEUS moves the lips only inside that window and keeps the mouth closed at every other moment.")

SHOTS = [
    dict(
        key="e01", title="E01 THE LYRE AND THE SNAKE", refs=["ORPHEUS", "LYRE", "MEADOW", "ANIMALS", "EURYDICE"],
        header="15s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Low wide camera drifting very slowly toward screen-right; no zoom, no cut.",
        heading="AT DUSK BESIDE A SLOW RIVER IN ANCIENT GREECE. ORPHEUS plays THE LYRE and the wild animals stand still to listen. Then the woman he loves is lost in the tall grass.",
        frame=("Wide and low across THE RIVER MEADOW. ORPHEUS sits on a flat stone in the left third of the frame, in profile, facing screen-right, "
               "THE LYRE on his knees, both hands on the strings. A deer, a wolf and a fox stand in the grass in the middle of the frame, all facing him. "
               "The river behind them, the low sun gold on the water; tall grass fills the right third. ORPHEUS is no taller than one fifth of the frame height. "
               "The only warm light falls on ORPHEUS and THE LYRE."),
        beats=[
            "[0s] ORPHEUS plays THE LYRE, his fingers moving across the strings, eyes half closed, face toward screen-right. The deer, the wolf and the fox stay motionless, ears forward, facing him.",
            "[6s] Far away in the tall grass at the right, a woman's dark silhouette in a long pale dress walks toward screen-left, toward ORPHEUS, seen from the side, no face, no detail.",
            "[9s] A thin dark snake slides through the grass toward her feet in one S-curve. The silhouette stops, then sinks below the tops of the grass and is gone; only the grass sways where she stood. At 11 seconds ORPHEUS stops playing, lifts his head and looks toward screen-right, hands raised off the strings.",
            "[12s] Hold: everyone stays where they are, no speech, no singing, no new action; only wind in the grass and the slow river.",
        ],
        sound=("overall_soundscape: only the sounds of the place and of ORPHEUS's own lyre: slow plucked notes of one ancient lyre until 10 seconds, wind in tall grass, slow river water, soft animal breath. "
               "No voices, no speech, no singing. After 12 seconds only wind and river.\nnon_diegetic_music: none."),
        crit=("CRITICAL NEGATIVES: no face on the silhouette, no snake bite shown, no blood, no second ORPHEUS, no people other than ORPHEUS and the one silhouette, "
              "no speech or singing, nothing new starts after 12 seconds."),
        audios=[],
    ),
    dict(
        key="e02", title="E02 THE LAND OF THE DEAD", refs=["TELLER_ROOM", "ORPHEUS", "LYRE", "THRONES", "KING"],
        header="15s · 1080p · 16:9 · TWO SHOTS JOINED BY ONE HARD CUT at 5 seconds. Shot one is static. Shot two is one continuous take with a slow pull-back; no zoom.",
        heading="A DARK ROOM LIT BY ONE LAMP, THEN THE LAND OF THE DEAD. Two aged hands rest on an open book. Then ORPHEUS stands before the king and queen of the dead, plays, and the king lets him go.",
        frame=("SHOT ONE: close shot across a worn wooden table in THE TELLER'S ROOM: two aged, weathered hands, no face and no body, rest on an open book; "
               "the small oil lamp at screen-right; the shelf of blank books dark behind. "
               "SHOT TWO: a vast dark cavern hall. ORPHEUS stands in the left third of the frame, in profile, facing screen-right, THE LYRE in his hands. "
               "At screen-right on two dark stone thrones sit THE KING OF THE DEAD, a tall pale man with ash-grey skin, a plain black stone crown and a long black robe, "
               "and THE QUEEN OF THE DEAD beside him, a pale woman with ash-grey skin, long black hair, a plain black stone crown and a long dark robe; "
               "both face three-quarter toward screen-left, toward ORPHEUS. ORPHEUS is no taller than one quarter of the frame height. "
               "The only warm light falls on ORPHEUS and THE LYRE; the thrones sit in cold verdigris dark."),
        beats=[
            "[0s] SHOT ONE: the aged hands turn one page of the open book, slowly. The lamp flame flickers; dust drifts in the lamplight. The camera does not move.",
            "[5s] HARD CUT to SHOT TWO, wide and low: ORPHEUS walks in from screen-left through the hall toward the thrones, the camera pulling back slowly in front of him.",
            "[8s] ORPHEUS stops in front of the thrones, lifts THE LYRE and plays. The stern face of THE KING OF THE DEAD softens and he lowers his chin. At 11 seconds THE KING lifts one hand toward screen-left and nods once; ORPHEUS lowers THE LYRE.",
            "[12s] Hold: everyone stays where they are, no speech, no singing, no new action; only a low cold wind and the last faint note of THE LYRE.",
        ],
        sound=("overall_soundscape: only the sounds of the place and of ORPHEUS's own lyre: a lamp's soft hiss and a paper page in shot one; in shot two slow footsteps on stone, a low cold wind, "
               "slow plucked notes of one ancient lyre from 8 to 11 seconds. No voices, no speech, no singing.\nnon_diegetic_music: none."),
        crit=("CRITICAL NEGATIVES: no face in shot one, no body in shot one, no hands other than the two aged hands, no skulls, no bones, no fire pits, no demons, "
              "no second ORPHEUS, no speech or singing, nothing new starts after 12 seconds."),
        audios=[],
    ),
    dict(
        key="e03", title="E03 THE LOOK BACK", refs=["STAIR", "ORPHEUS_ASHEN", "LYRE", "EURYDICE"],
        header="15s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera at the side of the stair, tracking slowly toward screen-right and rising with him; no zoom, no cut.",
        heading="A DARK STAIR OUT OF THE LAND OF THE DEAD, THE LAST STEPS BELOW THE DAYLIGHT. ORPHEUS climbs with a silhouette behind him. He turns to look back, speaks one word, and she dissolves.",
        frame=("Side view of THE STAIR, climbing from the lower left up to the pale opening of daylight at the upper right. "
               "ORPHEUS climbs toward screen-right and upward, THE LYRE hanging from one hand, his shoulder toward the camera. "
               "Two steps below him at screen-left, a woman's dark silhouette follows, a pale outline in the mist, no face, no detail. "
               "ORPHEUS is no taller than one third of the frame height. The only warm light falls on ORPHEUS and THE LYRE; the daylight opening is cold and pale."),
        beats=[
            "[0s] ORPHEUS climbs the wet steps toward screen-right and upward, steady, THE LYRE in his hand; the silhouette follows two steps behind him, silent. Mist drifts across the stone.",
            "[5s] Near the top, daylight reaches ORPHEUS. He slows and stops; his shoulders tighten and his free hand closes. The silhouette stays two steps behind, motionless.",
            "[8s] ORPHEUS turns his head and shoulders toward screen-left and looks down at the silhouette, his face in three-quarter profile toward screen-left, lips visible. From 9.5 to 10.6 seconds he speaks one word, his eyes on her, not on the camera.",
            "[11s] The silhouette comes apart like smoke and drifts down the stair. ORPHEUS reaches toward screen-left with his free hand; his fingers close on empty mist.",
            "[12s] Hold: ORPHEUS stays where he is, no speech, no new action; only drips of water and a thin wind from the opening.",
        ],
        sound=("overall_soundscape: only the sounds of the place and ORPHEUS's own: slow footsteps on wet stone, dripping water, a thin wind from the opening above, his breath, and the one spoken word from <Audio 1>. "
               "No other voices, no singing.\nnon_diegetic_music: none."),
        crit=("CRITICAL NEGATIVES: no face on the silhouette, no second ORPHEUS, no people other than ORPHEUS and the one silhouette, no skulls, no bones, "
              "no speaking anything except the one word in <Audio 1>, no stage directions spoken aloud, no singing, nothing new starts after 12 seconds."),
        audios=["orpheus_word_15s.mp3"],
        speech=True,
    ),
    dict(
        key="e04", title="E04 THE EMPTY RIVER", refs=["MEADOW_GREY", "ORPHEUS_ASHEN", "LYRE"],
        header="15s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Low wide camera pulling back slowly and rising; no zoom, no cut.",
        heading="THE SAME RIVER MEADOW, NOW GREY AND EMPTY. ORPHEUS sits alone with the lyre he no longer plays. Far away, on the ridge, a line of torches appears.",
        frame=("Wide and low across THE RIVER MEADOW after the sun is gone: the sky grey-green, the river dull, no animals. "
               "ORPHEUS sits on the flat stone in the left third of the frame, in profile, facing screen-right toward the river, THE LYRE lying unplayed in the grass beside him. "
               "ORPHEUS is no taller than one seventh of the frame height. The only warm light is one last ember glow on the river and on ORPHEUS."),
        beats=[
            "[0s] ORPHEUS sits motionless on the stone, facing the river at screen-right, THE LYRE lying in the grass beside him. Grass moves in the wind.",
            "[2s] ORPHEUS bows his head slowly and covers his face with both hands. The light dims a little. The camera begins to pull back and rise.",
            "[7s] On the far ridge at the horizon a row of small torch flames appears, with tiny dark silhouettes of people carrying them, too far to show faces. The camera keeps rising until the ridge fills the top of the frame.",
            "[12s] Hold: ORPHEUS and the torch line stay where they are, no speech, no new action; only wind over the grass and the dull river.",
        ],
        sound=("overall_soundscape: only the sounds of the place: wind over grass, slow river water, far thin crackle of torches. No voices, no speech, no singing, no lyre notes.\nnon_diegetic_music: none."),
        crit=("CRITICAL NEGATIVES: no animals, no second ORPHEUS, no face detail on the torch carriers, no weapons visible, no blood, no violence on screen, "
              "no speech or singing, nothing new starts after 12 seconds."),
        audios=[],
    ),
]


def paste_block(s):
    refs = "\n".join(REFS[k] for k in s["refs"])
    parts = [
        s["header"], "",
        s["heading"], "",
        "REFERENCES, each with a job:", refs, "",
        "THE FRAME: " + s["frame"], "",
        "WHAT HAPPENS:", "\n".join(s["beats"]), "",
        s["sound"],
    ]
    if s.get("speech"):
        parts += ["", SPEECH]
    parts += ["", GRADE, "", s["crit"], "", HOUSE_NEG]
    return "\n".join(parts)


def check(s, text):
    for k in s["refs"]:
        n = len(re.findall(r"@" + k + r"\b", text))
        if n != 1:
            sys.exit(f"{s['key']}: @{k} appears {n} times (rule 2: exactly once)")
    for bad in ("blush", "flushed", "red cheek", "red ear", "หน้าแดง", "หูแดง"):
        for m in re.finditer(bad, text):
            if "no " not in text[max(0, m.start() - 4):m.start()]:
                sys.exit(f"{s['key']}: '{bad}' outside the closing negation")
    if "[12s] Hold" not in text:
        sys.exit(f"{s['key']}: no [12s] hold beat (rule 13)")


def main():
    cards = []
    for s in SHOTS:
        text = paste_block(s)
        check(s, text)
        notes = (f"=== NOTES · DO NOT PASTE ANY OF THIS ===\n{s['title']} · {SECONDS}s · {QUALITY} · {ASPECT} · The Old Telling EP1 first minute (Thai)\n"
                 f"Entities (group 'The Old Telling'): {', '.join('@' + k for k in s['refs'])}. Audio bound: {s['audios'] or 'none'}.\n"
                 f"Narration is NOT in this clip; it is mixed in the edit.\n=== END NOTES ===\n\n")
        body = ("=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes, never paste it ===\n\n" + text +
                "\n\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes, never paste it ===\n")
        (OUT / f"{s['key']}.txt").write_text(notes + body, encoding="utf-8")
        cards.append(dict(
            batchTitle=f"The Old Telling EP1 {s['key']}", aspect=ASPECT,
            card=dict(originalIndex=1, title=s["title"], prompt=text, include=True, linkAbove=False,
                      seconds=SECONDS, quality=QUALITY, rating="safe",
                      ratedSha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      audios=s["audios"]),
        ))
        print(f"{s['key']}: {len(text.split())} words, refs {len(s['refs'])}, audios {len(s['audios'])}")
    (OUT / "cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
