#!/usr/bin/env python3
"""The Old Telling EP1 ACT 3 (about 2:41 to 4:26, Thai): 18 new shots as DATA, one template, no paid call unless --fire.

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act3.py                    # write shots3/*.txt + cards-act3.json
    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act3.py --fire [--only s03,s04]   # queue on the studio

Picture plan = one shot per sentence group of the Thai ACT 3 (SCRIPT-TH-FULL.md, ids 3.01 to 3.16), lengths on the measured H3 grid
(4 s request = 107 f = 4.46 s, 5 = 124 f, 6 = 141 f, 7 = 175 f, 8 = 192 f, 15 = 362 f at 24 fps). Narration is never bound to H3; only s09
carries the Orpheus line as <Audio 1> (path B: H3 voices the hint itself and lip-syncs to it; the edit mutes that and lays the real line on
each mouth burst, as for ACT 2 s12). Rules reused from build.py: each @ref exactly once, adults 18+ and no child in any picture (the dead are
adult silhouettes even where the narration says children), no blush or red ears, the studio h3Model must equal --model (CEO owns it),
`--fire` prints ONLY ids of the rows it creates, never the queue (the shared Colab belongs to the CEO too).
CEO 2026-10-10: 'ทำ ARC3 ต่อเลยได้อณุมติงบ'; Colab cap 100 CU for this series' pictures (11.86 spent by ACT 2).
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import build  # REFS, GRADE, HOUSE_NEG
import h3_setup as h

OUT = HERE / "shots3"; OUT.mkdir(exist_ok=True)
QUALITY, ASPECT = "1080p", "16:9"
GRID = {4: 107, 5: 124, 6: 141, 7: 175, 8: 192, 15: 362}  # request seconds -> frames (rules.ts, measured)
LINE = HERE / "voice-th/out-act3/act3_309_orpheus_liam.mp3"  # 5.72 s
HINT = OUT / "act3_309_hint.mp3"
ORPH_FROM, ORPH_TO = 0.6, 6.4

SPEECH = ("<Audio 1> is the finished dialogue track of this shot.\n"
          "<Audio 1>: fully_copy - the soundtrack plays <Audio 1> exactly as given: the same voice, the same line, the same timing.\n"
          f"Speech timing: ORPHEUS speaks from {ORPH_FROM} s to {ORPH_TO} s. ORPHEUS moves the lips only inside that window and keeps the mouth closed at every other moment.")

CAVERN = {"STAIR": "@STAIR: THE CAVERN LOOK ONLY: the wet dark rough-cut rock, the cold mist and the cold verdigris light of THE STAIR's cavern. Take nothing else from it: no stair, no steps, no daylight opening."}
COLD = "There is no warm light at all: the only light is a faint cold verdigris glow."

SHOTS = [
    dict(key="s01", title="S01 THE ROAD DOWN TO THE STYX", sec=7, refs=["STAIR"], refover=CAVERN, line="3.01",
         header="7s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera drifting slowly forward; no zoom, no cut.",
         heading="THE ROAD DOWN INTO THE LAND OF THE DEAD, ENDING AT A BLACK RIVER THAT CIRCLES THE WORLD BELOW NINE TIMES.",
         frame=("Wide shot down a long black cavern passage that opens onto a vast underground river of still black water. The river bends round in a great ring, then another ring inside it, coiling away into the mist, "
                "the far bank only a dark line. No person, no boat, no bridge. " + COLD),
         beats=["[0s] Mist drifts along the passage floor toward the camera; the black water lies perfectly still.",
                "[2s] The camera drifts slowly forward; the first great ring of the black river comes into view, a faint cold glow along its surface.",
                "[4.5s] The inner rings of the river appear in the mist, coiling one inside another into the distance.",
                "[6s] Hold: nothing new appears; only drifting mist."],
         sound="overall_soundscape: only the sounds of the place: a deep hollow cavern tone, slow drips, a faint breath of cold wind. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no person, no boat, no skulls, no bones, no fire, no lava, no demons, nothing new starts after 6 seconds.", hold="6s"),
    dict(key="s02", title="S02 THE SHORE OF THE DEAD", sec=7, refs=["STAIR"], refover=CAVERN, line="3.02",
         header="7s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera low, drifting slowly along the shore; no zoom, no cut.",
         heading="THE DEAD STAND ALONG THE BANK OF THE BLACK RIVER, PALE AND SILENT.",
         frame=("Wide low shot along a misty bank of black stone beside the still black river. A long line of pale grey translucent silhouettes of ADULT dead stand shoulder to shoulder at the water's edge: "
                "women in long plain robes, men in plain cloaks, young women in long simple dresses; each is a soft featureless grey outline fading into the mist, no faces, no detail, no children. " + COLD),
         beats=["[0s] The silhouettes stand motionless along the bank; mist moves around their feet.",
                "[2s] The camera drifts slowly along the line; a few silhouettes turn their heads together toward screen-right, as if hearing something far away.",
                "[5s] Hold: the figures stay where they are, no new action; only drifting mist."],
         sound="overall_soundscape: only the sounds of the place: a deep hollow cavern tone, slow drips, a faint sigh of cold wind. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face detail, no child, no skulls, no bones, no blood, no fire, no demons, no speech or singing, nothing new starts after 5 seconds.", hold="5s"),
    dict(key="s03", title="S03 ORPHEUS WALKS THROUGH THE DEAD", sec=8, refs=["ORPHEUS", "LYRE", "THRONES"], line="3.03",
         header="8s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera low behind him, following slowly; no zoom, no cut.",
         heading="ORPHEUS WALKS ALONG A LONG AISLE OF THE DEAD TO THE TWO THRONES AT ITS END AND STOPS BEFORE THEM.",
         frame=("Wide low shot from behind and slightly to the side down a long dark stone hall. ORPHEUS walks away from the camera along the centre, THE LYRE in his left hand, his dark cloak over one shoulder; his face is never visible. "
                "On both sides stand rows of the adult dead as pale ash-grey figures in long plain robes down to the ankles, hoods up, their faces in deep shadow, no bare skin shown except hands and feet. At the far end, small in the distance, THE THRONES stand side by side with the two seated figures. "
                "ORPHEUS is no taller than one third of the frame height and is already walking in the middle of the frame at the very first moment; THE LYRE is only a small shape in his hand and is never shown in close-up. The only warm light falls faintly on ORPHEUS and THE LYRE; the hall is cold verdigris dark."),
         beats=["[0s] ORPHEUS walks forward down the aisle between the rows; the silhouettes turn their heads to watch him pass.",
                "[4s] He keeps walking steadily toward THE THRONES at the far end, the camera following slowly.",
                "[6.5s] He stops a few paces before THE THRONES and stands still, THE LYRE held in his hand.",
                "[7s] Hold: everyone stays where they are, no new action; only drifting mist."],
         sound="overall_soundscape: only the sounds of the place: slow footsteps on stone, a deep hollow hall tone, a faint cold wind. No voices, no speech, no singing, no lyre notes.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face visible on ORPHEUS, no face detail on the dead, no bare chests, no nudity, no bald muscular bodies, no lyre close-up, no lyre filling the frame, no child, no skulls, no bones, no fire, no demons, no speech or singing, nothing new starts after 7 seconds.", hold="7s"),
    dict(key="s04", title="S04 THE KING WHO DOES NOT SOFTEN", sec=6, refs=["KING"], line="3.04",
         header="6s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static with a very slow push-in; no zoom, no cut.",
         heading="THE KING OF THE DEAD, HARD AND STILL.",
         frame=("Close shot of THE KING OF THE DEAD seated on a black stone throne in a dark hall, his stern lean face half in shadow, his black stone crown and high-collared black robe, "
                "looking straight ahead and a little down. He is completely still. The only light is a cold dim glow on one side of his face."),
         beats=["[0s] The king sits motionless, only his robe's collar stirring in a faint cold draught.",
                "[3s] His eyes move slowly toward screen-left, toward someone out of frame, and stop there; his face does not change.",
                "[5s] Hold: he stays where he is, no new action."],
         sound="overall_soundscape: only the sounds of the place: a deep hollow hall tone, a faint cold wind. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no smile, no speech, no second person in frame, no skulls, no fire, nothing new starts after 5 seconds.", hold="5s"),
    dict(key="s05", title="S05 THE HANDS ON THE STRINGS", sec=4, refs=["ORPHEUS", "LYRE"], line="3.05",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, close; no zoom, no cut.",
         heading="ORPHEUS'S HANDS TOUCH THE STRINGS OF THE LYRE.",
         frame=("Close shot of ORPHEUS's two hands on the strings of THE LYRE, his dark cloak sleeve at the edge of the frame; no face and no body above the wrists. "
                "Behind him, far out of focus, the cold dark hall. The only warm light is a soft ember glow on his hands and THE LYRE."),
         beats=["[0s] The fingers rest on the strings, still.",
                "[1.2s] The right hand plucks one slow string; the note rings; the fingers begin to move across the strings.",
                "[3.5s] Hold: the hands keep playing slowly, no new action."],
         sound="overall_soundscape: only the sounds of the place and ORPHEUS's own lyre: slow plucked notes of one ancient lyre, a faint hall tone. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face, no body above the wrists, no second person, no speech or singing, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s06", title="S06 HE SINGS BEFORE THE THRONES", sec=7, refs=["ORPHEUS", "LYRE", "THRONES"], line="3.06",
         header="7s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera low behind his shoulder, static; no zoom, no cut.",
         heading="ORPHEUS PLAYS AND SINGS BEFORE THE KING AND QUEEN OF THE DEAD.",
         frame=("Medium shot from behind and slightly to the side: ORPHEUS stands in the left third of the frame with his back mostly to the camera, THE LYRE in both hands, his face never visible. "
                "In front of him, across the dark hall, THE THRONES with THE KING OF THE DEAD and THE QUEEN OF THE DEAD seated, both looking at him. "
                "ORPHEUS is no taller than one third of the frame height. The only warm light falls on ORPHEUS and THE LYRE."),
         beats=["[0s] ORPHEUS plays THE LYRE and sings; his shoulders rise and fall; the king and queen sit motionless, looking at him.",
                "[3s] The queen's head turns very slightly toward the king, then back toward ORPHEUS.",
                "[6s] Hold: everyone stays where they are, no new action; only the last notes of THE LYRE."],
         sound="overall_soundscape: only the sounds of the place and ORPHEUS's own lyre: slow plucked notes of one ancient lyre, a deep hall tone. No voices, no speech, no words sung aloud.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face visible on ORPHEUS, no speech or words, no skulls, no fire, no demons, nothing new starts after 6 seconds.", hold="6s"),
    dict(key="s07", title="S07 THE KING LISTENS", sec=15, refs=["THRONES", "KING"], line="3.07",
         header="15s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera slow push-in toward the thrones; no zoom, no cut.",
         heading="THE KING OF THE DEAD LISTENS AND, FOR THE FIRST TIME, LOOKS AT THE MAN WHO SINGS.",
         frame=("Medium-wide shot of THE THRONES in the dark hall, THE KING OF THE DEAD on the left throne and THE QUEEN OF THE DEAD on the right, both facing the camera a little to screen-left, toward someone out of frame. "
                "The king is rigid and cold; the queen watches him. The only light is cold verdigris; a faint ember glow reaches the king's face from the left."),
         beats=["[0s] The king sits rigid, looking down; the queen's eyes rest on him.",
                "[5s] The king slowly lifts his eyes toward screen-left and looks straight at the singer out of frame; his face does not soften yet.",
                "[9s] The queen turns her head toward the king and looks at him for a long moment.",
                "[12s] Hold: both stay where they are, no speech, no new action."],
         sound="overall_soundscape: only the sounds of the place and a lyre far off screen: slow plucked notes of one ancient lyre, a deep hall tone. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no smile, no speech, no singing, no extra person in frame, no skulls, no fire, no demons, nothing new starts after 12 seconds.", hold="12s"),
    dict(key="s08", title="S08 THE EMPTY HAND", sec=15, refs=["ORPHEUS", "LYRE", "THRONES"], line="3.08",
         header="15s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera low behind his shoulder, very slow push-in; no zoom, no cut.",
         heading="ORPHEUS ASKS ONLY FOR A LITTLE TIME AND HOLDS OUT AN EMPTY HAND TO THE KING AND QUEEN.",
         frame=("Medium shot from behind and low at ORPHEUS's shoulder: ORPHEUS stands in the left third of the frame with his back to the camera, THE LYRE hanging from his left hand, his face never visible. "
                "Across the dark hall THE THRONES with THE KING OF THE DEAD and THE QUEEN OF THE DEAD, looking at him. ORPHEUS is no taller than one third of the frame height. "
                "The only warm light falls on ORPHEUS."),
         beats=["[0s] ORPHEUS stands still, THE LYRE hanging from his left hand, his head raised toward the thrones.",
                "[5s] He slowly raises his right hand toward the thrones with the palm open and empty, and holds it there.",
                "[9s] The queen lowers her eyes, then lifts them to the king; the king does not move.",
                "[12s] Hold: everyone stays where they are, no speech, no new action."],
         sound="overall_soundscape: only the sounds of the place: a deep hall tone, a faint cold wind, cloth moving. No voices, no speech, no singing, no lyre notes.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face visible on ORPHEUS, no speech or singing, no skulls, no fire, no demons, nothing new starts after 12 seconds.", hold="12s"),
    dict(key="s09", title="S09 ORPHEUS: IF YOU REFUSE", sec=8, refs=["ORPHEUS", "LYRE"], line="3.09", audio=True,
         header="8s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static with a very slow push toward ORPHEUS; no zoom, no cut.",
         heading="ORPHEUS, FACING THE KING OF THE DEAD, SPEAKS HIS LAST WORDS TO HIM IN ONE TAKE.",
         frame=("Medium close shot in a dark stone hall. ORPHEUS stands in the left third of the frame in three-quarter view toward screen-right, THE LYRE held low in his left hand. "
                "His face and lips are visible, his eyes steady on someone out of frame at screen-right. He fills about half of the frame height. "
                "The only warm light falls on his face and THE LYRE; the hall behind him is cold verdigris dark."),
         beats=["[0s] ORPHEUS stands still, looking steadily toward screen-right.",
                f"[{ORPH_FROM}s] ORPHEUS speaks his line toward screen-right in a low even voice: his lips move, his eyes do not leave the king; his hands stay still.",
                f"[{ORPH_TO}s] He stops speaking and his lips close; he stays looking at the king.",
                "[6.8s] Hold: he stays where he is, no speech, no new action."],
         sound=("overall_soundscape: only the sounds of the place and of ORPHEUS: a deep hall tone, a faint cold wind, and the one spoken line from <Audio 1>. "
                "No other voices, no singing, no lyre notes.\nnon_diegetic_music: none."),
         crit=("CRITICAL NEGATIVES: no second person in frame, no lyre played, no speaking anything except the line in <Audio 1>, no stage directions spoken aloud, "
               "no singing, nothing new starts after 6.8 seconds."), hold="6.8s"),
    dict(key="s10", title="S10 THE DEAD WEEP", sec=4, refs=["STAIR"], refover=CAVERN, line="3.10",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, wide; no zoom, no cut.",
         heading="THE PALE DEAD ON THE BANK BOW THEIR HEADS AND WEEP.",
         frame=("Wide shot of the misty bank of black stone: a line of pale grey translucent silhouettes of ADULT dead at the water's edge, featureless, no faces. " + COLD),
         beats=["[0s] The silhouettes stand still, heads raised toward screen-right.",
                "[1.2s] They bow their heads one after another; some raise a hand toward their faces; single drops of water fall from them into the black river and ring on its surface.",
                "[3.5s] Hold: they stay bowed, no new action."],
         sound="overall_soundscape: only the sounds of the place: slow drips of water on still water, a deep hollow tone, a faint sigh of cold wind. No voices, no crying sounds, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face detail, no child, no skulls, no blood, no fire, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s11a", title="S11A THE WATER THAT RUNS AWAY", sec=4, refs=["STAIR"], refover=CAVERN, line="3.11",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, medium; no zoom, no cut.",
         heading="A THIRSTY DEAD MAN STANDS IN A BLACK POOL; THE WATER SINKS AWAY FROM HIS HAND. THIS TIME HIS HAND STOPS.",
         frame=("Medium shot in the cavern, painterly and lit like the rest of the film: a gaunt adult man with pale ash-grey skin like cold marble, seen from behind and the side with his face turned away, a ragged grey cloth wrapped from his waist to his knees, stands waist-deep in a black pool, one arm reaching down toward the water; above him a bare branch hangs with pale fruit just out of his reach. " + COLD),
         beats=["[0s] He cups his hand toward the black water; the surface sinks away from his fingers.",
                "[2s] His arm stops; he holds his open hand still above the water and does not reach again.",
                "[3.5s] Hold: he stays where he is, no new action."],
         sound="overall_soundscape: only the sounds of the place: slow dripping water, a deep hollow tone. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no flat cutout, no flat vector shape, no face, no nudity, no child, no blood, no skulls, no fire, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s11b", title="S11B THE WHEEL STOPS", sec=4, refs=["STAIR"], refover=CAVERN, line="3.11",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, wide; no zoom, no cut.",
         heading="A GREAT WOODEN WHEEL TURNS IN THE DARK AND SLOWS TO A STOP.",
         frame=("Wide shot in the cavern: one huge upright wooden wheel with an iron rim, taller than a house, a grey translucent silhouette of an adult bound to its rim, turning slowly in the cold dark. No face, no detail. " + COLD),
         beats=["[0s] The wheel turns slowly, its rim creaking.",
                "[1.5s] The turning slows, slows, and the wheel comes to a complete stop.",
                "[3.5s] Hold: the wheel and the silhouette stay perfectly still, no new action."],
         sound="overall_soundscape: only the sounds of the place: the slow creak of a great wooden wheel dying to silence, a deep hollow tone. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no flames, no fire, no blood, no wounds, no face detail, no skulls, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s11c", title="S11C THE STONE HE NO LONGER PUSHES", sec=4, refs=["STAIR"], refover=CAVERN, line="3.11",
         header="4s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, wide; no zoom, no cut.",
         heading="A GREAT BOULDER ON A DARK SLOPE; THE DEAD MAN WHO PUSHES IT SITS DOWN ON IT AT LAST.",
         frame=("Wide shot of a dark cavern slope with one huge round boulder resting on it, and beside it a large grey translucent silhouette of an adult man with both hands on the stone, no face, no detail. " + COLD),
         beats=["[0s] The silhouette stands beside the boulder with both hands on it.",
                "[1.5s] He lets go, turns and slowly sits down on the boulder.",
                "[3.5s] Hold: he sits still, no new action."],
         sound="overall_soundscape: only the sounds of the place: a deep hollow tone, slow drips, one long breath. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face detail, no blood, no skulls, no fire, nothing new starts after 3.5 seconds.", hold="3.5s"),
    dict(key="s12", title="S12 THE THREE-HEADED DOG", sec=5, refs=["STAIR"], refover=CAVERN, line="3.12",
         header="5s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, low; no zoom, no cut.",
         heading="THE THREE-HEADED DOG THAT GUARDS THE GATE STANDS FROZEN, ALL THREE MOUTHS OPEN.",
         frame=("Low wide shot at a black cavern gate: a huge dark dog silhouette crouched in the mist, with exactly three separate heads on three thick necks, all facing the camera, "
                "grey fur, no detail in the faces. " + COLD),
         beats=["[0s] The three heads move restlessly, turning side to side.",
                "[2s] All three heads stop and lift; the three mouths open wide and stay open, motionless.",
                "[4s] Hold: the dog stays frozen, no new action."],
         sound="overall_soundscape: only the sounds of the place: a deep hollow tone, a low heavy breath dying to silence. No barking, no growling, no voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: exactly three heads, no fourth head, no teeth in detail, no blood, no skulls, no fire, no person, nothing new starts after 4 seconds.", hold="4s"),
    dict(key="s13", title="S13 THE FURY WEEPS", sec=8, refs=["STAIR"], refover=CAVERN, line="3.13",
         header="8s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static with a very slow push-in; no zoom, no cut.",
         heading="THREE HARD WOMEN OF VENGEANCE STAND STIFF IN THE DARK. ONE OF THEM WEEPS A SINGLE TEAR.",
         frame=("Medium-wide shot in the cavern: three tall dark female figures stand in a row, stiff as statues in long black robes; their hair is a mass of small living snakes. "
                "Their faces are in deep shadow, no detail. The middle one is slightly in front. " + COLD),
         beats=["[0s] The three stand rigid, the small snakes in their hair stirring slowly.",
                "[3s] The middle figure's head tilts down a little; the snakes in her hair go still.",
                "[4.5s] One single drop of water runs down her shadowed cheek and catches the cold light.",
                "[7s] Hold: the three stay where they are, no new action."],
         sound="overall_soundscape: only the sounds of the place: a deep hollow tone, a faint hiss dying to silence, one drop of water. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face detail, no blood, no wounds, no weapons, no skulls, no fire, no more than three figures, nothing new starts after 7 seconds.", hold="7s"),
    dict(key="s14", title="S14 EURYDICE IS CALLED", sec=7, refs=["EURYDICE", "THRONES"], line="3.14",
         header="7s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, wide; no zoom, no cut.",
         heading="A WOMAN'S SILHOUETTE WALKS SLOWLY OUT OF THE MIST TOWARD THE THRONES, DRAGGING ONE FOOT.",
         frame=("Wide low shot across the dark hall with THE THRONES at the far right and the two seated figures, small in the distance. "
                "From the mist at the far left a woman walks slowly toward them as a dark silhouette in THE DRESS, a long pale linen dress with a long pale veil, no face and no detail. "
                "She is no taller than one fifth of the frame height. " + COLD),
         beats=["[0s] The pale silhouette appears out of the mist at the far left, standing still.",
                "[1.5s] She walks slowly toward the thrones; her left foot drags a little at every step, a slight limp.",
                "[5s] She keeps walking, slow and uneven, toward the thrones.",
                "[6s] Hold: she keeps her place in the frame, no new action; only mist."],
         sound="overall_soundscape: only the sounds of the place: one slow uneven footstep at a time on stone, a deep hall tone, a faint cold wind. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face on the silhouette, no blood, no visible wound, no second person other than the distant thrones, no speech or singing, nothing new starts after 6 seconds.", hold="6s"),
    dict(key="s15", title="S15 THE KING AGREES", sec=6, refs=["THRONES", "KING"], line="3.15",
         header="6s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera static, medium; no zoom, no cut.",
         heading="THE KING OF THE DEAD GIVES IN: ONE SLOW NOD.",
         frame=("Medium shot of THE THRONES in the dark hall: THE KING OF THE DEAD on the left throne and THE QUEEN OF THE DEAD on the right, both facing a little toward screen-left. "
                "The only light is cold verdigris with a faint ember glow on the king's face."),
         beats=["[0s] The king sits still; the queen looks at him.",
                "[1.5s] The king lowers his chin in one slow nod.",
                "[3s] He lifts one hand a little toward screen-left, toward the way out, and lowers it.",
                "[5s] Hold: both stay where they are, no speech, no new action."],
         sound="overall_soundscape: only the sounds of the place: a deep hall tone, a faint cold wind, cloth moving. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no speech, no smile, no extra person, no skulls, no fire, nothing new starts after 5 seconds.", hold="5s"),
    dict(key="s16", title="S16 THE SILENT CLIMB", sec=6, refs=["STAIR", "ORPHEUS", "LYRE", "EURYDICE"], line="3.16",
         header="6s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera at the side of the stair, tracking slowly toward screen-right and rising with him; no zoom, no cut.",
         heading="A DARK STEEP STAIR. ORPHEUS STARTS TO CLIMB; A SILENT SILHOUETTE FOLLOWS TWO STEPS BEHIND HIM. NO ONE SPEAKS.",
         frame=("Side view of THE STAIR, climbing from the lower left up toward the upper right, the top far above, a tiny pale spot of daylight. "
                "ORPHEUS climbs toward screen-right and upward, THE LYRE hanging from one hand, his head facing forward, never turned. "
                "Two steps below him at screen-left, a woman's dark silhouette in THE DRESS follows, a pale outline in the mist, no face, no detail. "
                "ORPHEUS is no taller than one third of the frame height. The only warm light falls on ORPHEUS and THE LYRE."),
         beats=["[0s] ORPHEUS starts up the wet steps toward screen-right, steady, his head always facing forward; the silhouette follows two steps behind, silent.",
                "[3s] They keep climbing, the distance between them unchanged; mist drifts across the stone.",
                "[5s] Hold: they keep climbing slowly, no look back, no speech, no new action."],
         sound="overall_soundscape: only the sounds of the place and ORPHEUS's own: slow footsteps on wet stone, dripping water, his breath. No voices, no speech, no singing.\nnon_diegetic_music: none.",
         crit="CRITICAL NEGATIVES: no face on the silhouette, ORPHEUS never turns his head, no second ORPHEUS, no speech or singing, no skulls, no bones, nothing new starts after 5 seconds.", hold="5s"),
]


def paste_block(s):
    parts = [s["header"], "", s["heading"], ""]
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
    if "—" in text:
        sys.exit(f"{s['key']}: em dash in the paste block")


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
        audios = ["act3_309_hint.mp3"] if s.get("audio") else []
        notes = (f"=== NOTES · DO NOT PASTE ANY OF THIS ===\n{s['title']} · {s['sec']}s request ({frames} frames, {frames/24:.2f} s) · {QUALITY} · {ASPECT} · The Old Telling EP1 ACT 3 · covers sentences {s['line']}\n"
                 f"Entities (group 'The Old Telling'): {', '.join('@' + k for k in s['refs']) or 'none'}. Audio bound: {audios or 'none'}.\nNarration is NOT in this clip; it is mixed in the edit.\n=== END NOTES ===\n\n")
        (OUT / f"{s['key']}.txt").write_text(notes + "=== ↓↓↓ PASTE FROM HERE ↓↓↓ ===\n\n" + text + "\n\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ ===\n", encoding="utf-8")
        cards.append(dict(key=s["key"], batchTitle=f"The Old Telling EP1 ACT3 {s['key']}", aspect=ASPECT,
                          card=dict(originalIndex=1, title=s["title"], prompt=text, include=True, linkAbove=False, seconds=s["sec"], quality=QUALITY,
                                    rating="safe", ratedSha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), audios=audios)))
        print(f"{s['key']}: {s['sec']}s -> {frames} f {frames/24:.2f} s · {len(text.split())} words · refs {s['refs']} · audios {len(audios)}")
    (OUT / "cards-act3.json").write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total requested picture {total_s:.2f} s in {len(SHOTS)} shots · est CU at 0.10 per second {total_s * 0.10:.1f} (+ about 0.5 VM start)")
    if not LINE.exists():
        sys.exit(f"missing {LINE}")
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
        h.record("h3-fired-act3.json", [rows[-1]])
    q = h.api("/api/queue")[1]
    q = q if isinstance(q, list) else q.get("items", q.get("queue", []))
    mine = {i for r in rows for i in r["ids"]}
    for it in q:
        if it.get("id") in mine:
            print(f"item {it['id']} status {it.get('status')} savedRefs {len(it.get('savedRefs') or [])} quality {it.get('quality')} seconds {it.get('seconds')} frames {it.get('frames')}")


main()
