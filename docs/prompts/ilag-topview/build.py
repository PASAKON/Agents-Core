"""Build the ILAG TopView trailer prompt files in the «Sorry, Sir» house format.

Format and rules: docs/prompts/absence/PROMPT-STYLE.md + AUTHORING-RULES.md (two zones per file,
tech header first, every @ reference declared ONCE with a job, [Ns] beats, manner tags of five
words or fewer before a line of dialogue, AUDIO stated, colour grade block, CRITICAL NEGATIVES
first and the house wall after). Engine for P1: our MiniMax H3 studio (the @handle attaches the
picture). Run: python3 docs/prompts/ilag-topview/build.py  -> writes m01..m13 *.txt next to it.
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
DRIVE = "YT: ILAG/รอตั้งชื่อ (Topview Wan3 Challenge 2026)/Element/"

REF = {
    "@Young": ("Character/ref-Young.png",
               "THE YOUNG ONE, a child of an amphibious alien people, about 1.1 m tall: smooth coral-pink skin "
               "with tiny glowing gold freckles, large round glossy dark eyes with an orange ring, a wide mouth, "
               "a mane of feathery external gills around the head in orange-gold, webbed three-fingered hands, "
               "webbed feet, a short flat tail fin, a woven kelp satchel on a strap across the chest. Face, body "
               "and colours only; take nothing of the white background."),
    "@Elder": ("Character/ref-Elder.png",
               "THE ELDER, an old man of the same people, taller and thinner: deep teal-blue skin, violet gill "
               "frills with one frill torn, a small bead necklace, an upright, unhurried stance. Face, body and "
               "colours only; take nothing of the white background."),
    "@Strong": ("Character/ref-Strong.png",
                "THE STRONG ONE, the biggest man of the same people, about 1.9 m, broad and heavily muscled: deep "
                "moss-green skin with darker mottling on the shoulders and back, lime-green glowing freckles along "
                "the arms, emerald gill frills tipped gold, a woven kelp belt, a coiled kelp rope over one shoulder. "
                "Face, body and colours only; take nothing of the white background."),
    "@Villagers": ("Character/ref-Villagers.png",
                   "THE VILLAGERS, more of the same people in other soft colours: mint, lavender, pale blue, "
                   "sand-yellow, orange, rose. Their look only; they are spread through the place, never lined up."),
    "@Manta": ("Character/ref-Manta.png",
               "THE MOUNT, their ride: a manta-like sea creature about 4 m across the wings, a sea-green mottled back, "
               "a long thin whip tail, small calm dark eyes on the front edge, a soft lime-green glow on its "
               "underside. Strapped to its back is a hand-built seat of weathered driftwood lashed with green kelp "
               "rope, pale bone ribs for a backrest, seashells and small glowing seed-pod lamps tied along it, tufts "
               "of glowing green grass at the corners. Take nothing of the white background."),
    "@Lantern": ("Prop/ref-Lantern.png",
                 "THE LANTERN: a large pearly seashell with a woven kelp handle, three glowing golden seed pods "
                 "inside it, hanging from the seat."),
    "@LanternDark": ("Prop/ref-LanternDark.png",
                     "THE LANTERN once its light has died: the same shell, empty and dark."),
    "@Pole": ("Prop/ref-Pole.png",
              "THE POLE: a long pale bone steering pole carved with wave patterns, a kelp grip near the top."),
    "@Necklace": ("Prop/ref-Necklace.png",
                  "THE NECKLACE: dry brown seed husks strung on kelp twine."),
    "@GlassSpiral": ("Location/ref-GlassSpiral.png",
                     "THE SPIRAL: a giant turning corkscrew of glass-clear membrane with rainbow light running along it."),
    "@GlassCathedral": ("Location/ref-GlassCathedral.png",
                        "THE DOME: a giant drifting dome of layered transparent veils with a rainbow core."),
    "@GlassHalo": ("Location/ref-GlassHalo.png",
                   "THE RINGS: giant floating rings of clear membrane, one inside another, trailing threads of light."),
    "@GlassBloom": ("Location/ref-GlassBloom.png",
                    "THE BLOOM: a vast floating flower of transparent petals, seeds of light drifting from it."),
    "@Mountain": ("Location/crt_mountain_horizon_v3.png",
                  "THE MOUNTAIN, the only picture of the thing on the horizon: a vast smooth dark shape rising from "
                  "the black sea where no land can exist, water pouring off its flanks. Take its shape, its size in "
                  "the frame and its darkness exactly."),
    "@Eye": ("Location/crt_eye_v4a.png",
             "THE CREATURE, the only picture of it: a broad flat smooth dark head rising out of the black sea, two "
             "enormous pale yellow-green eyes with thin vertical slit pupils, water pouring off it, faint violet "
             "lightning behind. Take its face, its eyes and its scale exactly."),
    "@Village": ("Location/loc_village_above_A_v2.png",
                 "THE VILLAGE: giant mangrove-like trees standing in glass-clear turquoise water with no land "
                 "anywhere, long arching stilt roots, wooden houses lashed among the branches and grown over with "
                 "glowing neon-green grass, ladders and rope bridges, a huge close moon in a bright blue-white sky. "
                 "Take the whole place and its light from it."),
    "@Dock": ("Location/loc_village_above_B_v2.png",
              "THE DOCK: the floating driftwood landing at the foot of the village where glowing mantas are "
              "moored with kelp ropes, glass-clear water around it."),
    "@ClearWater": ("Location/ref-ClearWater.png",
                    "THE CLEAR WATER: glass-clear turquoise shallow water over a pale sandy seabed with coral."),
    "@Pillars": ("Location/loc_storm_pillars_A_v3.png",
                 "THE PILLARS, the only location reference: thin, perfectly straight columns of slowly swirling "
                 "cloud standing on a violet-grey sea and rising beyond the top of the sky, a small whirlpool at "
                 "each base, the dim moon. Take the place and its light."),
    "@Line": ("Location/loc_deep_line_v2.png",
              "THE LINE, the only location reference: a razor-sharp line across the sea from horizon to horizon. "
              "Near side: glass-clear turquoise water, a bright blue-white sky, the huge moon. Far side: pitch-black "
              "water under a purple-black storm with violet lightning. Take both sides and the line exactly."),
    "@BlackSea": ("Location/ref-BlackSea.png",
                  "THE BLACK SEA: pitch-black water under a purple-black storm, violet lightning reflected on it."),
    "@Waves": ("Location/loc_giant_waves_v2.png",
               "THE WAVE, the only location reference: a colossal curling wall of dark water hundreds of metres "
               "tall, glowing faintly cyan and magenta inside, violet lightning, the moon behind storm cloud."),
    "@Planet": ("Location/planet_from_space_v3.png",
                "THE PLANET, the only reference: an ocean world with no land, split into two hemispheres, one bright "
                "blue-white with turquoise sea and white cloud, one purple-black under a storm with violet lightning, "
                "a sharp line between them, a moon half its size beside it in black space."),
}

GRADE = {
    "DAY": "Colour grade, their daylight: bright blue-white, faint stars still visible in the bright sky, never orange, "
           "cool turquoise water, the neon-green grass as the one warm accent. Photographed, not rendered: fine film "
           "grain, gentle anamorphic softness at the edges.",
    "TURNING": "Colour grade, the turning: a violet-grey bruised sky, cool silver light, deep indigo water, the moon "
               "dim behind thin cloud. Photographed, not rendered: fine film grain.",
    "DARK": "Colour grade, the dark: pitch-black water and a purple-black storm, violet lightning as the key light, "
            "cyan and magenta glints, deep true blacks. Photographed, not rendered: fine film grain.",
}

HOUSE_NEG = ("House negatives: no humans, no human faces, no human hands; no land, no island, no beach, no rocks "
             "above the water; no boats, no ships, no oars, no sails; no metal, no plastic, no modern objects; no text, "
             "no subtitles, no captions, no logos, no watermark; no grid, no split screen, no panels, no white studio "
             "background; no cartoon, no anime, no plastic skin; no music, no score; no dutch angle, no lens flare.")
DIALOGUE_NEG = ("no stage directions spoken aloud, no narration of anyone's feelings, no speaking anything outside "
                "the quotation marks, no extra lines, no voiceover")

SCENES = [
    dict(n=1, slug="the-village-at-morning", title="THE VILLAGE AT MORNING", s=6, grade="DAY",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A slow push-in from water level; no pan, no tilt, no zoom.",
         refs=["@Village", "@Villagers"],
         heading="MORNING IN THE VILLAGE, the first image of the film. Nobody here knows yet that anything is wrong.",
         frame="Water level, wide: the trees fill the frame, the moon high on the right, the dock in the lower middle, "
               "mantas resting at it.",
         beats=["[0s] Wide shot from just above the water. The village stands in glass-clear water, the glowing grass "
                "bright on every roof, the huge moon close and sharp in the blue-white sky.",
                "[2s] THE VILLAGERS go about the morning: one climbs a rope ladder up a root, two cross a rope bridge, "
                "one sits at the dock with a foot in the water.",
                "[4s] The camera keeps its slow push towards the dock. Small ripples, calm."],
         audio="gentle lapping water, wind in the grass, far voices of the villagers without words. No music.",
         crit="no dialogue, no crowd in a row, no one looking at the lens, no night, no orange or red sky, no sunset, "
              "no sun, no second moon",
         review=["The village matches the picture: trees in water, glowing grass, the close moon.",
                 "Villagers are the alien species, several colours, busy, never lined up.",
                 "Blue-white daylight, never orange.", "One continuous push-in, no cut."],
         end="THE VILLAGE unchanged; mantas at the dock."),
    dict(n=2, slug="the-empty-net", title="THE EMPTY NET", s=6, grade="DAY",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A locked medium side shot; no pan, no zoom.",
         refs=["@Strong", "@Dock", "@ClearWater", "@Villagers"],
         heading="AT THE DOCK, THE SAME MORNING. THE STRONG ONE hauls in the village's net and the fish are gone.",
         frame="Side on to THE STRONG ONE at the edge of the dock, the net line running down into the water; two "
               "villagers a few paces behind him.",
         beats=["[0s] THE STRONG ONE braces his feet at the edge of the dock and hauls a woven kelp net up hand over hand "
                "out of the glass-clear water.",
                "[3s] The net comes up out of the water completely empty, streaming water. Below it the sandy seabed is "
                "bare and still.",
                "[4.5s] THE STRONG ONE stands holding the empty net. Two villagers behind look at it; their gill frills fade pale."],
         audio="water pouring off the net, creak of the dock, a quiet breath. No dialogue. No music.",
         crit="no fish anywhere, no fish in the net, no fish in the water, no dialogue, no second net, no boat",
         review=["The net is EMPTY and the seabed is bare.", "THE STRONG ONE matches his picture: moss-green, huge, gold-tipped gills.",
                 "Gills of the villagers fade pale.", "Locked camera."],
         end="THE STRONG ONE on the dock with the empty net."),
    dict(n=3, slug="the-elder-chooses-the-child", title="THE ELDER CHOOSES THE CHILD", s=6, grade="DAY",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A close two-shot, gentle handheld drift; no zoom.",
         refs=["@Elder", "@Young", "@Necklace", "@Village"],
         heading="ON A PLATFORM HIGH IN THE VILLAGE. THE ELDER tells THE YOUNG ONE why this journey needs a child's eyes.",
         frame="Close two-shot on a wooden platform: THE ELDER kneeling on the left, THE YOUNG ONE standing on the right, "
               "the glowing grass and the sea soft behind them.",
         beats=["[0s] THE ELDER kneels low and ties THE NECKLACE around the neck of THE YOUNG ONE.",
                "[2s] THE ELDER looks at THE YOUNG ONE. Quietly: \"The fish went past the line.\"",
                "[4s] The gill frills of THE YOUNG ONE glow faint gold. Then, softer: \"Only a child's eyes can still find them.\""],
         audio="wind, the grass rustling, the two lines above and nothing else. No music.",
         crit=DIALOGUE_NEG + ", no fish, no third person close, no crying",
         review=["Two lines, in order, spoken by THE ELDER; transcribe before keeping.",
                 "THE NECKLACE is tied on and stays on the child in every later scene.",
                 "The child's gills glow gold.", "THE ELDER has one torn violet frill."],
         end="THE YOUNG ONE wears THE NECKLACE."),
    dict(n=4, slug="leaving", title="LEAVING", s=6, grade="DAY",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A wide tracking shot from behind, moving with them; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Pole", "@Lantern", "@Dock"],
         heading="THE THREE LEAVE THE VILLAGE on THE MOUNT, out over the clearest water.",
         frame="From behind and a little above THE MOUNT and THE THREE RIDERS; the seat order from front to back is THE STRONG ONE on the "
               "front perch, THE YOUNG ONE in the middle, THE ELDER at the back, and it never changes in this film.",
         beats=["[0s] THE MOUNT glides away from the dock over glass-clear turquoise water, wings rippling. THE STRONG ONE "
                "steers with THE POLE; THE LANTERN glows gold, hanging from the seat.",
                "[3s] THE YOUNG ONE turns to look back at the village.",
                "[4s] The village of giant trees shrinks behind them under the huge close moon."],
         audio="the swish of the wings, water, wind. No dialogue. Music is added later, none here.",
         crit="no dialogue, no fourth rider, no boat, no oars, no second mount beside them",
         review=["Three riders in the fixed seat order.", "THE LANTERN is glowing.", "Clear water, village behind.",
                 "The mount matches its picture: driftwood seat, lime glow under the wings."],
         end="Seat order fixed: THE STRONG ONE front, THE YOUNG ONE middle, THE ELDER back; THE LANTERN lit."),
    dict(n=5, slug="the-glass-creatures", title="THE GLASS CREATURES", s=6, grade="TURNING",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A slow underwater drift alongside them; no cut, no zoom.",
         refs=["@Manta", "@Young", "@GlassSpiral", "@GlassCathedral", "@GlassHalo", "@GlassBloom"],
         heading="UNDERWATER, FURTHER OUT. The world is starting to be strange: giant creatures made of something like glass.",
         frame="Wide underwater: THE MOUNT small in the lower middle with THE YOUNG ONE on its back, the four glass "
               "creatures drifting around them at different distances, light from the surface above.",
         beats=["[0s] THE MOUNT glides through open blue water that is turning violet-grey, THE YOUNG ONE on its back.",
                "[2s] Around them drift THE SPIRAL, THE DOME, THE RINGS and THE BLOOM, each as big as a house, rainbow "
                "light moving through their clear bodies.",
                "[4s] THE YOUNG ONE reaches out a hand towards THE BLOOM as it passes, eyes wide."],
         audio="muffled underwater hush, a soft chime-like hum from the creatures. No dialogue. No music.",
         crit="no jellyfish, no squid, no octopus, no fish, no dialogue",
         review=["All four glass creatures present and NOT like Earth jellyfish.", "Scale: each as big as a house.",
                 "The water shifts towards violet-grey."],
         end="On the mount, heading on."),
    dict(n=6, slug="the-storm-pillars", title="THE STORM PILLARS", s=6, grade="TURNING",
         spec="ONE CONTINUOUS TAKE, NO CUTS. Low near the water, a slow tilt up; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Pillars"],
         heading="BETWEEN THE STORM PILLARS. Silent columns of cloud stand on the sea, taller than anything they know.",
         frame="Low near the water: THE MOUNT with THE THREE RIDERS in the middle distance between two pillars.",
         beats=["[0s] THE MOUNT glides between thin, perfectly straight pillars of swirling cloud; small whirlpools "
                "turn at their bases. The air is still.",
                "[2.5s] THE THREE RIDERS tip their heads back and look up.",
                "[4s] The camera tilts up with them along one pillar as it rises beyond the top of the sky."],
         audio="a low soft whirl of wind around the pillars, calm water. No dialogue. No music.",
         crit="no tornado, no funnel, no cone shape, no strong wind, no debris, no rain, no dialogue",
         review=["Pillars thin and straight, reaching past the frame top.", "Riders tiny against them.",
                 "Calm, not violent."],
         end="Riders still in the fixed seat order."),
    dict(n=7, slug="the-line", title="THE LINE", s=6, grade="TURNING",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A slow crane down from a high angle; no cut, no zoom.",
         refs=["@Line", "@Manta", "@Elder", "@Young", "@Strong"],
         heading="THE LINE. Clearest water on this side, black water and a storm on the other. Nobody crosses it.",
         frame="High above: the line across the frame, THE MOUNT stopped on the clear side, right at the edge.",
         beats=["[0s] From high above, THE MOUNT with THE THREE RIDERS has stopped at the razor-sharp line: clear water behind it, black "
                "water in front.",
                "[2s] The camera cranes slowly down towards THE THREE RIDERS.",
                "[3s] THE ELDER looks across into the dark. Low and steady: \"No one has crossed it in a hundred "
                "years.\" Then: \"Something sleeps out there.\""],
         audio="wind on one side, far thunder on the other, the two lines above and nothing else. No music.",
         crit=DIALOGUE_NEG + ", no blurred line, no gradient between the waters, no crossing yet",
         review=["The line is razor sharp in sea and sky.", "Two lines from THE ELDER, in order; transcribe.",
                 "The mount stays on the clear side."],
         end="THE MOUNT on the clear side at the line."),
    dict(n=8, slug="crossing", title="CROSSING", s=5, grade="DARK",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A side shot at water level, moving with them; no cut, no zoom.",
         refs=["@Manta", "@Lantern", "@LanternDark", "@BlackSea", "@Strong", "@Elder", "@Young"],
         heading="THEY CROSS. The clear water ends and the black sea begins, and their light goes out.",
         frame="At water level, side on: THE MOUNT moving left to right across the line into the black water.",
         beats=["[0s] THE MOUNT crosses from clear water into pitch-black water. Violet lightning cracks overhead; rain "
                "begins.",
                "[2s] THE LANTERN flickers, gutters and goes dark, and hangs there as the dead lantern.",
                "[3.5s] THE STRONG ONE grips the pole; THE ELDER and THE YOUNG ONE hold on."],
         audio="thunder, rain on water, the lantern's glow fading with a soft crackle. No dialogue. No music.",
         crit="no dialogue, no second lantern, no fire, no flame, no explosion",
         review=["The lantern goes from lit to dark on camera.", "The water turns black at the line.",
                 "Seat order unchanged."],
         end="THE LANTERN dark for the rest of the film."),
    dict(n=9, slug="the-empty-sea", title="THE EMPTY SEA", s=5, grade="DARK",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A close handheld shot; no cut, no zoom.",
         refs=["@Young", "@BlackSea", "@Manta"],
         heading="IN THE BLACK SEA. THE YOUNG ONE, who alone can see fish, looks and finds nothing.",
         frame="Close on THE YOUNG ONE leaning over the edge of the seat, the black water below.",
         beats=["[0s] THE YOUNG ONE leans over the edge of the seat and stares down into the black water. Nothing moves "
                "in it.",
                "[2s] The gill frills of THE YOUNG ONE drain from gold to pale white.",
                "[3s] A whisper: \"There's nothing here... not one.\""],
         audio="rain, the creak of the seat, the whisper above and nothing else. No music.",
         crit=DIALOGUE_NEG + ", no fish, no glow in the water, no creature in the water, no tears",
         review=["Gills go gold to pale.", "One whispered line; transcribe.", "Water is black and empty."],
         end="THE YOUNG ONE pale, still on the seat."),
    dict(n=10, slug="the-giant-wave", title="THE GIANT WAVE", s=6, grade="DARK",
         spec="ONE CONTINUOUS TAKE, NO CUTS. Low, looking up, with camera shake; no cut, no zoom.",
         refs=["@Waves", "@Manta", "@Strong", "@Pole", "@Elder", "@Young"],
         heading="THE WAVE. A wall of water as tall as a mountain rises against the wind. The small action of the film.",
         frame="Low and looking up: THE MOUNT small at the bottom of the frame, the wave filling everything above it.",
         beats=["[0s] THE WAVE rises against the wind, curling over THE MOUNT, glowing faintly cyan and magenta inside.",
                "[2s] THE STRONG ONE drives THE POLE down. A shout: \"Hold on!\"",
                "[3.5s] THE MOUNT dives; THE THREE RIDERS cling on as the wave crashes over the place they just were."],
         audio="a deep roar of water, the shout above and nothing else spoken, then muffled underwater silence. No music.",
         crit=DIALOGUE_NEG + ", no rider falling off, no surfing, no second wave in front",
         review=["The wave is colossal against the riders.", "One shouted line.", "They dive under, nobody falls."],
         end="THE MOUNT surfaces past the wave, all three on it."),
    dict(n=11, slug="the-mountain-that-should-not-be", title="THE MOUNTAIN THAT SHOULD NOT BE", s=6, grade="DARK",
         spec="ONE LOCKED SHOT, NO CUTS. The camera never moves, never pans, never zooms.",
         refs=["@Mountain", "@Manta", "@Strong", "@Elder", "@Young"],
         heading="PAST THE WAVE, THE STORM QUIETS. On a planet with no land, there is a mountain on the horizon.",
         frame="Wide, from behind THE THREE RIDERS: THE MOUNT small in the lower middle, THE MOUNTAIN across the horizon.",
         beats=["[0s] THE MOUNT floats still on black water. Ahead, across the horizon, stands THE MOUNTAIN.",
                "[2s] THE THREE RIDERS stare at it without moving.",
                "[3.5s] THE YOUNG ONE, a whisper: \"I can see them... inside it.\" For a moment a faint gold glow shows "
                "deep under the dark surface of THE MOUNTAIN, then fades."],
         audio="rain easing, a low distant rumble, the whisper above and nothing else. No music.",
         crit=DIALOGUE_NEG + ", no eyes on the mountain, no face on the mountain, no second mountain, no camera move",
         review=["No eyes, no face: it must read as land that cannot be.", "Faint gold glow, brief.",
                 "One whispered line; transcribe.", "Locked camera."],
         end="THE MOUNT facing THE MOUNTAIN."),
    dict(n=12, slug="the-eyes-open", title="THE EYES OPEN", s=5, grade="DARK",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A very slow push-in; no cut, no pan.",
         refs=["@Eye"],
         heading="THE MOUNTAIN IS A HEAD. It opens its eyes.",
         frame="Extreme close, square on to the face; the eyes fill the upper half of the frame.",
         beats=["[0s] Darkness, the wet dark skin of THE CREATURE, water streaming down it.",
                "[1.5s] Both eyes open, slowly: pale yellow-green, thin vertical slit pupils, each bigger than a whole "
                "village.",
                "[3.5s] The pupils narrow and fix on the camera. Violet lightning flickers behind."],
         audio="near silence, water running off stone-like skin, then one deep low rumble. No dialogue. No music.",
         crit="no dialogue, no roar, no mouth opening, no teeth, no third eye, no purple skin, no neon, no cartoon look",
         review=["Two eyes, pale yellow-green, slit pupils.", "Skin dark and natural, a touch of violet only in the light.",
                 "Slow and silent."],
         end="THE CREATURE's eyes open."),
    dict(n=13, slug="pull-out-to-space", title="PULL OUT TO SPACE", s=6, grade="DARK",
         spec="ONE CONTINUOUS TAKE, NO CUTS. One continuous pull-out upward; no cut, no dissolve.",
         refs=["@Planet"],
         heading="THE LAST IMAGE. We leave them and see the whole world they live on.",
         frame="Ends on THE PLANET centred, its moon beside it.",
         beats=["[0s] From the black stormy sea the camera pulls back and rises, up through the storm clouds.",
                "[2.5s] Out into space: the curve of the planet appears, then the whole globe.",
                "[4.5s] THE PLANET hangs in black space, split between its bright half and its storm half, the moon "
                "beside it. Hold."],
         audio="the storm fading into deep silence. No dialogue. No music.",
         crit="no dialogue, no land, no continents, no rings around the planet, no second moon, no text",
         review=["Two hemispheres, sharp line.", "Moon half the planet's size.", "One continuous pull-out."],
         end="End of the film's picture; the question card follows in the edit."),
]


# ai-film-production §13: each character's reference text must carry its CAST.md row's key colours.
CAST_KEYS = {
    "@Young": ["coral-pink", "gold freckles", "orange-gold", "satchel"],
    "@Elder": ["teal-blue", "violet", "torn"],
    "@Strong": ["moss-green", "lime-green", "tipped gold", "kelp belt", "kelp rope"],
    "@Manta": ["sea-green", "lime-green", "driftwood", "bone ribs"],
    "@Villagers": ["mint", "lavender", "pale blue", "sand-yellow", "orange", "rose"],
    "@Eye": ["pale yellow-green", "slit pupils"],
}
SEAT_ORDER = "THE STRONG ONE on the front perch, THE YOUNG ONE in the middle, THE ELDER at the back"


def paste_block(sc):
    lines = [f"{sc['s']}s · 360p · 16:9 · {sc['spec']}", "", sc["heading"], "", "REFERENCES, each with a job:"]
    for h in sc["refs"]:
        lines.append(f"{h}: {REF[h][1]}")
    lines += ["", "THE FRAME: " + sc["frame"], "", "WHAT HAPPENS:"]
    lines += sc["beats"]
    lines += ["", "AUDIO: " + sc["audio"], "", GRADE[sc["grade"]], "",
              "CRITICAL NEGATIVES: " + sc["crit"] + ".", "", HOUSE_NEG]
    return "\n".join(lines)


def notes_top(sc):
    refs = "\n".join(f"  {h} -> Drive {DRIVE}{REF[h][0]}" for h in sc["refs"])
    return (f"M{sc['n']} · {sc['title']} · {sc['s']}s · {sc['grade']} · P1 main scenes (SCRIPT.md draft 2)\n\n"
            "Engine: our MiniMax H3 studio, 360p previz, 16:9. Type each @handle once (it already appears once in\n"
            "the paste block); the studio attaches its picture. Every picture is a SINGLE panel: a multi-panel\n"
            "sheet renders as a grid video on H3.\n"
            f"References ({len(sc['refs'])}):\n{refs}")


def notes_bottom(sc):
    review = "\n".join(f"{i}. {r}" for i, r in enumerate(sc["review"], 1))
    return (f"REVIEW ORDER:\n{review}\nFile the take whatever the verdict, as M{sc['n']}-H3-take<N>.mp4 in the\n"
            f"project's Previz/ folder, and tell the CTO which take.\n\nEND POSITIONS, inherited by the next scene:\n- {sc['end']}")


def main():
    cast = " ".join((HERE / "CAST.md").read_text(encoding="utf-8").split())  # flattened: phrases wrap
    assert SEAT_ORDER in cast, "seat order in CAST.md changed: update SEAT_ORDER and the scenes"
    for h, keys in CAST_KEYS.items():
        assert h in cast, h
        for k in keys:
            assert k in REF[h][1], f"{h} reference text lacks CAST key {k!r}"
    for sc in SCENES:
        body = paste_block(sc)
        for h in sc["refs"]:
            k = len(re.findall(re.escape(h) + r"\b", body))
            assert k == 1, (sc["n"], h, k)
        assert "—" not in body
        text = ("=== NOTES · DO NOT PASTE ANY OF THIS ===\n\n" + notes_top(sc) + "\n\n=== END NOTES ===\n\n"
                "=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes, never paste it ===\n\n" + body +
                "\n\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes, never paste it ===\n\n"
                "=== NOTES · DO NOT PASTE ANY OF THIS ===\n\n" + notes_bottom(sc) + "\n\n=== END NOTES ===\n")
        out = HERE / f"m{sc['n']:02d}-{sc['slug']}.txt"
        out.write_text(text, encoding="utf-8")
        print(out.name, len(body.split()), "words", len(sc["refs"]), "refs")


if __name__ == "__main__":
    main()
