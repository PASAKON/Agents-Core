#!/usr/bin/env python3
"""The Old Telling EP1 ACT 2 (1:00 to 2:40, Thai): 14 new shots as DATA, one template, no paid call unless --fire.

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act2.py                    # write shots2/*.txt + cards-act2.json
    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act2.py --fire [--only s03,s04]   # queue on the studio (needs CEO CU OK)

Picture plan = one shot per sentence group of the passed Thai ACT 2 (SCRIPT-TH-FULL.md), lengths on the H3 grid 5+17k frames at 24 fps
(4 s request = 107 f = 4.46 s, 5 = 124 f, 6 = 158 f, 7 = 175 f, 8 = 192 f, 15 = 362 f). 2.04 (field, cave, river) is cut from the four clips
we already own, so it is not here. Narration is never bound to H3; only s12 carries the Orpheus line as <Audio 1> (path B: H3 voices the hint
itself and lip-syncs to it; the edit mutes that and lays the real line on each mouth burst, as for the king).
Rules reused from build.py: each @ref exactly once, adults 18+, no blush or red ears, the studio h3Model must equal --model (CEO owns it),
`--fire` prints ONLY ids of the rows it creates, never the queue, never anybody's prompt (the shared Colab belongs to the CEO too).
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import build  # REFS, GRADE, HOUSE_NEG
import h3_setup as h

OUT = HERE / "shots2"; OUT.mkdir(exist_ok=True)
QUALITY, ASPECT = "1080p", "16:9"
GRID = {4: 107, 5: 124, 6: 158, 7: 175, 8: 192, 15: 362}  # request seconds -> frames (rules.ts)
SCRATCH = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
LINE = SCRATCH / "voice2/out/act2_215_orpheus_liam.mp3"  # 5.88 s: bursts 0-0.49, 1.0-3.06, 3.6-5.64
HINT = OUT / "act2_215_hint.mp3"
ORPH_FROM, ORPH_TO = 0.6, 6.5

SPEECH = ("<Audio 1> is the finished dialogue track of this shot.\n"
          "<Audio 1>: fully_copy - the soundtrack plays <Audio 1> exactly as given: the same voice, the same line, the same timing.\n"
          f"Speech timing: ORPHEUS speaks from {ORPH_FROM} s to {ORPH_TO} s. ORPHEUS moves the lips only inside that window and keeps the mouth closed at every other moment.")

BEACH = ("a flat pebble shore beside a still grey sea under a pale sky, one weathered driftwood log, nothing else on the shore and no other person")

SHOTS = [
    dict(key="s01", title="S01 THE TWO SCROLLS", sec=15, refs=["TELLER_ROOM"], line="2.01-2.03",
         header="15s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static with a very slow push-in on the table; no zoom, no cut.",
         heading="THE TELLER'S ROOM, LIT BY ONE LAMP. Two aged hands unroll two old scrolls, one after the other, and point down three lines.",
         frame=("Close shot across the worn wooden table in THE TELLER'S ROOM: two aged, weathered hands, no face and no body, ink-stained fingertips and one plain iron ring on the right ring finger. "
                "One rolled scroll lies at screen-left and a second, darker rolled scroll at screen-right; the small oil lamp stands at the back right; the shelf of blank books is dark behind. "
                "The only warm light is the lamp on the hands and the scrolls."),
         beats=["[0s] The aged hands pick up the left scroll and unroll it slowly across the table; dust drifts in the lamplight.",
                "[4s] The hands set it flat, then take the second scroll from screen-right and unroll it beside the first; it is darker with age.",
                "[9s] The ink-stained right forefinger moves down the second scroll and touches it three times in a row, each time a little lower, slowly.",
                "[12s] Hold: the hands stay on the scrolls, no new action; only the lamp flame flickers."],
         sound="overall_soundscape: only the sounds of the place: dry paper unrolling, the lamp's soft hiss, a faint creak of wood. No voices, no singing.\nnon_diegetic_music: none.",
         crit=("CRITICAL NEGATIVES: no face, no body, no hands other than the two aged hands, no readable writing or letters on the scrolls (only soft dark ink marks), "
               "no speech or singing, nothing new starts after 12 seconds."), hold="12s"),
    dict(key="s03", title="S03 THE WEDDING GUESTS", sec=6, refs=["MEADOW", "EURYDICE"], line="2.05-2.06",
         header="6s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Low wide camera drifting very slowly toward screen-right; no zoom, no cut.",
         heading="A WEDDING AT DUSK BESIDE THE SLOW RIVER. The guests stand as dark silhouettes. The god of marriage arrives with a torch, and nobody smiles.",
         frame=("Wide and low across THE RIVER MEADOW at dusk. Near the river in the middle of the frame, about twenty wedding guests stand in a loose half circle as dark silhouettes with no faces and no detail; "
                "at the centre the bride stands in THE DRESS, a long pale linen dress with a long pale veil, only a silhouette. "
                "At the right edge a tall dark silhouette, THE GOD OF MARRIAGE in a long dark cloak, steps into the meadow holding one unlit torch, his face in deep shadow. "
                "Every figure is no taller than one fifth of the frame height. The only warm light is a faint ember glow on the river and on the torch."),
         beats=["[0s] The guests stand still in the half circle, the bride at the centre; the grass moves in the wind.",
                "[2s] THE GOD OF MARRIAGE walks slowly in from screen-right, the torch held low; no guest moves or lifts a hand to greet him.",
                "[4s] He stops at the edge of the group and raises the torch a little.",
                "[5s] Hold: everyone stays where they are, no speech, no new action; only wind in the grass and the slow river."],
         sound="overall_soundscape: only the sounds of the place: wind in tall grass, slow river water, cloth moving. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit=("CRITICAL NEGATIVES: no faces on any silhouette, no smiles, no kiss, no second bride, no animals, no speech or singing, nothing new starts after 5 seconds."), hold="5s"),
    dict(key="s04", title="S04 THE TORCH THAT WILL NOT LIGHT", sec=7, refs=["MEADOW"], line="2.07",
         refover={"MEADOW": "@MEADOW: THE RIVER MEADOW AT DUSK, used only as the far, soft, out-of-focus background behind the torch: its dusk sky, its light and its tall grass. Nothing of it is in sharp focus; the torch and the hand are the subject."},
         header="7s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, close; no zoom, no cut.",
         heading="A TORCH THAT WILL NOT CATCH FIRE. Thick smoke, weak sparks, and no flame however it is waved.",
         frame=("Close shot, slightly low, of one wooden torch held upright in a bare dark hand against a dusk sky; the head of the torch is wrapped in pitch-soaked cloth. "
                "It gives off thick grey-black smoke and a few weak sparks but never catches into a flame. Behind it, far out of focus, the dark silhouettes of wedding guests stand in a row. "
                "The only warm light is the faint ember sparks."),
         beats=["[0s] The torch head sputters, small sparks jump, thick grey smoke rolls upward.",
                "[2s] The hand sweeps the torch slowly left and right through the air; the smoke streams out along the sweep; no flame appears.",
                "[5s] The hand lowers the torch; the smoke drifts across the lens and fills the upper half of the frame.",
                "[6s] Hold: the hand stays where it is, no flame, no new action; only drifting smoke."],
         sound="overall_soundscape: only the sounds of the place: the dry crackle and hiss of a torch that will not light, a soft breath of wind. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit=("CRITICAL NEGATIVES: no flame, no face, no body beyond the hand, no fire anywhere in the frame, no speech or singing, nothing new starts after 6 seconds."), hold="6s"),
    dict(key="s05", title="S05 THE BRIDE FALLS IN THE GRASS", sec=8, refs=["MEADOW", "EURYDICE"], line="2.08",
         header="8s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Low wide camera drifting very slowly toward screen-left; no zoom, no cut.",
         heading="IN THE TALL GRASS ON THE RIVER BANK THE BRIDE WALKS WITH A COMPANION. She stops, bends to her ankle, sinks into the grass and does not rise.",
         frame=("Wide and low across THE RIVER MEADOW at dusk. In the middle distance, in tall grass, two women walk side by side as dark silhouettes with no faces and no detail: "
                "the bride in THE DRESS, a long pale linen dress with a long pale veil, and beside her a companion in a long darker dress. "
                "Each is no taller than one fifth of the frame height. The only warm light is a faint ember glow on the river."),
         beats=["[0s] The two silhouettes walk slowly side by side through the tall grass toward screen-left, their long dresses brushing the grass.",
                "[3s] The pale silhouette stops and bends forward, one hand reaching down toward her ankle; the companion turns toward her.",
                "[4.5s] The pale silhouette sinks to her knees and then lies down in the grass out of sight; the companion stands over her, lifts both arms and steps back.",
                "[6.5s] Hold: only the companion stands; everything else is still; only grass swaying in the wind."],
         sound="overall_soundscape: only the sounds of the place: wind in tall grass, slow river water, soft cloth. No voices, no screams, no speech, no singing.\nnon_diegetic_music: none.",
         crit=("CRITICAL NEGATIVES: no snake visible, no bite shown, no blood, no face on any silhouette, no third person, no speech or screams, nothing new starts after 6.5 seconds."), hold="6.5s"),
    dict(key="s06", title="S06 THE SECOND SCROLL", sec=4, refs=["TELLER_ROOM"], line="2.09",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, close; no zoom, no cut.",
         heading="THE TELLER'S ROOM. The aged hands push one scroll away and draw the other into the lamplight.",
         frame=("Close shot across the worn wooden table in THE TELLER'S ROOM: two aged, weathered hands, no face and no body, ink-stained fingertips and one plain iron ring; "
                "one unrolled scroll at screen-left and a darker second scroll at screen-right; the small oil lamp at the back right. The only warm light is the lamp."),
         beats=["[0s] The hands push the left scroll away to screen-left and slide the darker scroll into the lamplight.",
                "[1.5s] The ink-stained forefinger rests on the darker scroll near its top and stays there.",
                "[3.5s] Hold: the hands stay where they are, no new action; only the lamp flame flickers."],
         sound="overall_soundscape: only the sounds of the place: dry paper sliding, the lamp's soft hiss. No voices, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face, no body, no hands other than the two aged hands, no readable writing, no speech or singing, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s07", title="S07 THE RUN ALONG THE RIVER", sec=4, refs=["MEADOW", "EURYDICE"], line="2.10",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Low wide camera tracking slowly toward screen-left; no zoom, no cut.",
         heading="THE BRIDE RUNS ALONG THE RIVER BANK. A man far behind her follows. Nothing violent happens.",
         frame=("Wide and low along the bank of THE RIVER MEADOW at dusk. In the middle distance a woman runs toward screen-left as a dark silhouette in THE DRESS, "
                "a long pale linen dress with a long pale veil streaming behind her, no face and no detail. Far behind her at the right, much smaller, a man's dark silhouette runs after her and never gets closer. "
                "Neither is taller than one fifth of the frame height. The only warm light is a faint ember glow on the river."),
         beats=["[0s] She runs along the bank toward screen-left, the veil streaming, her head turned ahead, not back.",
                "[1.5s] The man's tiny silhouette runs after her at the far right; the distance between them stays the same.",
                "[3.5s] Hold: both keep their places in the frame, no new action; only wind in the grass."],
         sound="overall_soundscape: only the sounds of the place: running steps on soft ground, wind in tall grass, slow river water. No voices, no screams, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face on any silhouette, no violence, no grabbing, no weapon, no third person, no speech or screams, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s08", title="S08 THE SNAKE IN THE GRASS", sec=5, refs=["MEADOW"], line="2.11",
         header="5s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera at ground level inside the grass, static; no zoom, no cut.",
         heading="AT GROUND LEVEL IN THE TALL GRASS. A huge water snake lies hidden, and a bare foot comes closer without seeing it.",
         frame=("Ground-level shot inside the tall grass of THE RIVER MEADOW at dusk, the stems filling the foreground. In the middle distance a huge dark water snake lies coiled and still among the stems, "
                "thick as a man's arm, its scales dull and wet. From screen-right the hem of a long pale linen dress and one bare foot step into the frame; nothing else of the woman is visible. "
                "The only warm light is a faint ember glow far behind."),
         beats=["[0s] The snake lies still, only its tongue flicking; the grass sways.",
                "[1.5s] The pale hem and the bare foot step closer through the grass, unaware, toward the coil.",
                "[3s] The foot comes down a hand's width from the snake. The snake does not move.",
                "[4.2s] Hold: the foot, the hem and the snake stay where they are, no new action; only grass swaying."],
         sound="overall_soundscape: only the sounds of the place: wind in tall grass, a soft footstep, a faint dry hiss of scales on stone. No voices, no screams, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no bite shown, no blood, no face, no body above the hem, no second snake, no speech or screams, nothing new starts after 4.2 seconds.", hold="4.2s"),
    dict(key="s09", title="S09 THE EMPTY MEADOW", sec=4, refs=["MEADOW"], line="2.12",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Low wide camera drifting very slowly; no zoom, no cut.",
         heading="THE RIVER MEADOW AT LAST LIGHT, EMPTY. Wind moves the grass; nobody is there.",
         frame=("Wide and low across THE RIVER MEADOW at last light, completely empty: no person, no animal, only the tall grass, the slow river, the flat grey stone and the far ridge. "
                "The only warm light is a faint ember glow on the river."),
         beats=["[0s] Wind moves through the tall grass in long slow waves.",
                "[1.5s] The ember glow on the river dims a little.",
                "[3.5s] Hold: nothing new appears; only the grass and the river."],
         sound="overall_soundscape: only the sounds of the place: wind in tall grass, slow river water. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no person, no animal, no silhouette, no bird, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s10", title="S10 THE DEAD HIVES", sec=6, refs=["MEADOW_GREY"], line="2.13",
         header="6s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera drifting slowly along the row toward screen-right; no zoom, no cut.",
         heading="A ROW OF EMPTY BEEHIVES. Dead bees lie thick on the boards. Nothing is alive.",
         frame=("Medium shot of a row of old woven-straw beehives on a long low wooden stand at the edge of THE RIVER MEADOW AFTER THE SUN IS GONE, beside the old olive trees. The hives are silent; hundreds of dead bees lie scattered on the boards and the ground in front of them as small dark specks; "
                "no living bee flies. The only warm light is a faint ember glow low at the left."),
         beats=["[0s] The row stands still; the wind stirs the dry straw.",
                "[2s] The camera drifts slowly along the row; a few dead bees roll on the boards in the wind.",
                "[5s] Hold: nothing new appears; only drifting dust and the wind."],
         sound="overall_soundscape: only the sounds of the place: wind over dry straw, a faint rattle of dead bees on wood. No humming, no voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no living bee, no person, no animal, no smoke, nothing new starts after 5 seconds.", hold="5s"),
    dict(key="s11", title="S11 THE LONE SHORE", sec=4, refs=["ORPHEUS", "LYRE"], line="2.14",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, extreme wide; no zoom, no cut.",
         heading="A LONE SHORE AT GREY DAWN. ORPHEUS sits alone with the lyre on his knees and lifts his head toward the sea.",
         frame=(f"Extreme wide shot across {BEACH}. ORPHEUS sits on the driftwood log at the far left, in profile facing the sea at screen-right, THE LYRE across his knees, his head bowed. "
                "He is tiny: no taller than one eighth of the frame height. The only warm light is a faint ember glow on the horizon of the sea."),
         beats=["[0s] ORPHEUS sits motionless, head bowed; small waves wash the pebbles.",
                "[1.5s] He lifts his head slowly toward the sea.",
                "[3.5s] Hold: he stays where he is, no new action; only the waves."],
         sound="overall_soundscape: only the sounds of the place: small waves on pebbles, a thin sea wind. No voices, no speech, no singing, no lyre notes.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no second person, no boat, no birds, no speech or singing, no lyre played, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s12", title="S12 ORPHEUS SINGS TO HER", sec=8, refs=["ORPHEUS", "LYRE"], line="2.15", audio=True,
         header="8s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static with a very slow push toward ORPHEUS; no zoom, no cut.",
         heading="THE SAME LONE SHORE. ORPHEUS speaks low to the sea, to her, at dawn and then at dusk, in one take.",
         frame=(f"Medium-wide shot of {BEACH}. ORPHEUS sits on the driftwood log in the left third of the frame, in three-quarter view toward the sea at screen-right, THE LYRE across his knees, both hands resting still on it. "
                "His face and lips are visible. He fills about one third of the frame height. At the start the light is pale grey dawn with a faint ember glow on the horizon."),
         beats=["[0s] ORPHEUS sits still in the pale dawn, looking at the sea.",
                f"[{ORPH_FROM}s] ORPHEUS speaks his line to the sea in a low voice: his lips move, his eyes on the horizon; his hands stay still on THE LYRE.",
                "[3.5s] Within the same take the light turns: the sky darkens to ember dusk over the sea while ORPHEUS goes on speaking, his eyes on the horizon.",
                "[6.8s] Hold: he lowers his head, his hands stay on THE LYRE, no speech, no new action; only the waves in the dusk."],
         sound=("overall_soundscape: only the sounds of the place and of ORPHEUS: small waves on pebbles, a thin sea wind, and the one spoken line from <Audio 1>. "
                "No other voices, no singing, no lyre notes.\nnon_diegetic_music: none."),
         crit=("CRITICAL NEGATIVES: no second person, no boat, no birds, no lyre played, no speaking anything except the line in <Audio 1>, no stage directions spoken aloud, "
               "no singing, nothing new starts after 6.8 seconds."), hold="6.8s"),
    dict(key="s13", title="S13 HE GETS UP", sec=4, refs=["ORPHEUS", "LYRE"], line="2.16",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, wide; no zoom, no cut.",
         heading="THE SAME SHORE AT DUSK. ORPHEUS gets up, takes the lyre and turns his back on the sea.",
         frame=(f"Wide shot across {BEACH}, in ember dusk. ORPHEUS sits on the driftwood log left of centre, in profile toward the sea, THE LYRE across his knees. "
                "He is no taller than one quarter of the frame height. The only warm light is a faint ember glow on the sea."),
         beats=["[0s] ORPHEUS sits, head bowed, the lyre on his knees.",
                "[1s] He stands, lifts THE LYRE from his knees and holds it hanging from one hand.",
                "[2.2s] He turns his back on the sea and faces the land at screen-left.",
                "[3.5s] Hold: he stays where he is, no new action; only the waves."],
         sound="overall_soundscape: only the sounds of the place: small waves on pebbles, pebbles shifting under sandals, a thin sea wind. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no second person, no speech or singing, no lyre played, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s14", title="S14 THE CAVE AT TAENARUS", sec=7, refs=["MEADOW_GREY"], line="2.17",
         refover={"MEADOW_GREY": "@MEADOW_GREY: LIGHT AND SKY ONLY: the dull grey-green sky and the one last faint ember glow on dark water. Take nothing else from it: no grass, no stone, no olive trees, no river, no ridge."},
         header="7s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera drifting slowly toward the cliff; no zoom, no cut.",
         heading="THE SOUTHERN TIP OF GREECE AT LAST LIGHT. A sea cliff with a black cave mouth that the old tellers call a gate to the dead.",
         frame=("Wide shot of a tall grey sea cliff at the southern tip of Greece at last light: the rock face rises from a dark sea, waves break white-grey at its foot, "
                "and in the rock face is one black cave mouth, tall and narrow, darker than any shadow around it. Nobody is in the frame. "
                "The only warm light is a thin ember line on the horizon."),
         beats=["[0s] The waves break at the foot of the cliff; the cave mouth stays black.",
                "[2s] The camera drifts slowly closer; a thin mist moves out of the cave mouth along the rock.",
                "[6s] Hold: nothing new appears; only the waves and the mist."],
         sound="overall_soundscape: only the sounds of the place: waves breaking on rock, a low hollow wind in the cave mouth. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no person, no animal, no boat, no skulls, no bones, no fire, no demons, nothing new starts after 6 seconds.", hold="6s"),
    dict(key="s15", title="S15 INTO THE CAVE", sec=4, refs=["ORPHEUS", "LYRE"], line="2.18",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, low, behind him; no zoom, no cut.",
         heading="ORPHEUS, SEEN FROM BEHIND, WALKS INTO THE BLACK CAVE MOUTH WITH ONLY HIS LYRE. The last light leaves him.",
         frame=("Medium-wide shot from behind and low, at the foot of a grey sea cliff at last light. ORPHEUS walks away from the camera toward a tall narrow black cave mouth in the rock, "
                "THE LYRE in his left hand, his dark cloak over one shoulder; his face is never visible. He is no taller than one third of the frame height. "
                "The only warm light is the last ember light on his shoulders and THE LYRE."),
         beats=["[0s] ORPHEUS walks slowly toward the cave mouth, seen from behind.",
                "[1.5s] He reaches the entrance; the last ember light lies on his back and THE LYRE.",
                "[2.5s] He steps into the dark; the light on him fades out as the darkness takes him.",
                "[3.5s] Hold: the empty cave mouth and a thin mist; no new action."],
         sound="overall_soundscape: only the sounds of the place: footsteps on stone, waves, a low hollow wind in the cave. No voices, no speech, no singing, no lyre notes.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face visible, no second person, no speech or singing, no skulls, no bones, no fire, nothing new starts after 3.5 seconds.", hold="3.5s"),
]


def paste_block(s):
    parts = [s["header"], "", s["heading"], ""]
    if s["refs"]:
        over = s.get("refover", {})
        parts += ["REFERENCES, each with a job:", "\n".join(over.get(k, build.REFS[k]) for k in s["refs"]), ""]
    parts += ["THE FRAME: " + s["frame"], "", "WHAT HAPPENS:", "\n".join(s["beats"]), "", s["sound"]]
    if s.get("audio"):
        parts += ["", SPEECH]
    parts += ["", build.GRADE, "", s["crit"], "", build.HOUSE_NEG]
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
    if f"[{s['hold']}] Hold" not in text:
        sys.exit(f"{s['key']}: no hold beat at {s['hold']} (rule 13)")
    if text.count("@") != len(s["refs"]):
        sys.exit(f"{s['key']}: stray @ in the paste block")
    if s["sec"] not in GRID:
        sys.exit(f"{s['key']}: {s['sec']} s is not a request length we planned")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fire", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default="cobijada")
    a = ap.parse_args()
    only = [x for x in a.only.split(",") if x]
    cards, total_s = [], 0.0
    for s in SHOTS:
        text = paste_block(s); check(s, text)
        frames = GRID[s["sec"]]; total_s += frames / 24
        audios = ["act2_215_hint.mp3"] if s.get("audio") else []
        notes = (f"=== NOTES · DO NOT PASTE ANY OF THIS ===\n{s['title']} · {s['sec']}s request ({frames} frames, {frames/24:.2f} s) · {QUALITY} · {ASPECT} · The Old Telling EP1 ACT 2 · covers sentences {s['line']}\n"
                 f"Entities (group 'The Old Telling'): {', '.join('@' + k for k in s['refs']) or 'none'}. Audio bound: {audios or 'none'}.\nNarration is NOT in this clip; it is mixed in the edit.\n=== END NOTES ===\n\n")
        (OUT / f"{s['key']}.txt").write_text(notes + "=== ↓↓↓ PASTE FROM HERE ↓↓↓ ===\n\n" + text + "\n\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ ===\n", encoding="utf-8")
        cards.append(dict(key=s["key"], batchTitle=f"The Old Telling EP1 {s['key']}", aspect=ASPECT,
                          card=dict(originalIndex=1, title=s["title"], prompt=text, include=True, linkAbove=False, seconds=s["sec"], quality=QUALITY,
                                    rating="safe", ratedSha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), audios=audios)))
        print(f"{s['key']}: {s['sec']}s -> {frames} f {frames/24:.2f} s · {len(text.split())} words · refs {s['refs']} · audios {len(audios)}")
    (OUT / "cards-act2.json").write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total requested picture {total_s:.2f} s in {len(SHOTS)} shots")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(LINE), "-af",
                    f"adelay={int(ORPH_FROM*1000)}|{int(ORPH_FROM*1000)},apad=whole_dur={GRID[8]/24:.3f}", "-t", f"{GRID[8]/24:.3f}",
                    "-ar", "44100", "-ac", "1", "-b:a", "128k", str(HINT)], check=True)
    if not a.fire:
        return
    code, st = h.api("/api/settings")
    cur = st.get("h3Model", "stock")
    if cur != a.model:
        sys.exit(f"STOP: studio h3Model is {cur!r}, --model says {a.model!r}. The CEO owns that setting; nothing queued.")
    created = {r["atId"] for r in json.loads((HERE / "h3-entities-created.json").read_text(encoding="utf-8")) if r.get("id")}
    miss = sorted({k for s in SHOTS for k in s["refs"]} - created)
    if miss:
        sys.exit(f"no entity of ours for {miss}")
    rows = []
    for c in cards:
        if only and c["key"] not in only:
            continue
        body_card = dict(c["card"])
        if body_card["audios"]:
            body_card["audios"] = [h.upload(HINT, "audio/mpeg")]
        code, res = h.api("/api/scenes/enqueue", {"batchTitle": c["batchTitle"], "aspect": ASPECT, "cards": [body_card]})
        if code != 200:
            sys.exit(f"{c['key']}: enqueue answered HTTP {code}: {str(res)[:200]}")
        ids = [i.get("id") for i in (res.get("queued") or []) if isinstance(i, dict)]  # `items` is everybody's queue: never printed
        rows.append({"clip": c["key"], "ids": ids, "routes": res.get("routes"), "routeCostUsd": res.get("routeCostUsd"), "h3Model": cur})
        print(f"{c['key']}: queued {len(ids)} ids {ids} · routes {res.get('routes')} · routeCostUsd {res.get('routeCostUsd')}")
        h.record("h3-fired-act2.json", [rows[-1]])
    q = h.api("/api/queue")[1]
    q = q if isinstance(q, list) else q.get("items", q.get("queue", []))
    mine = {i for r in rows for i in r["ids"]}
    for it in q:
        if it.get("id") in mine:
            print(f"item {it['id']} status {it.get('status')} savedRefs {len(it.get('savedRefs') or [])} quality {it.get('quality')} seconds {it.get('seconds')} frames {it.get('frames')}")


main()
