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
    "@Chief": ("Character/char_chief.png",
               "THE CHIEF, head of the village, older, tall and dignified, of the same people: pearl-white skin with "
               "faint silver freckles, deep sapphire-blue gill frills, a crown of raw uncut gemstones (amethyst, "
               "turquoise, opal, rose quartz) bound in pale driftwood, necklaces of polished natural stones, a long cloak "
               "of dark woven kelp covered in pearly shell scales, shell bands on both arms, a tall driftwood staff "
               "topped with a raw quartz crystal. Dressed unlike anyone else in the film. Face, body and costume only; "
               "take nothing of the grey background."),
    "@Runner": ("Character/ref-Runner-blue.png",
                "THE RUNNER, a tall thin young man of the same people: turquoise-blue skin with faint gold freckles, "
                "dark navy-blue gill frills, a coiled kelp rope over one shoulder, a necklace of small shells, a woven "
                "kelp belt. Face, body and colours only; take nothing of the white background."),
    "@Villagers2": ("Character/villagers_2.png",
                    "MORE VILLAGERS, six others of the same people: a stooped old man with slate-grey skin, a plump "
                    "woman in peach-coral, a tall thin young man in turquoise, a small girl in lilac, a stocky man in "
                    "olive-brown, a young mother in mint-green with a baby. Their look only; never lined up in a row."),
    "@Hut": ("Location/loc_hut_A.png",
             "THE HUT, the only interior reference: the inside of the child's small hut, built "
             "like the inside of a camping tent, a low sloping roof of woven leaves on a ridge pole, a hammock of "
             "knotted kelp net, a rolled sleeping mat, glowing golden seed-pod lamps hanging from the ridge, shells "
             "and small toys on the woven floor, a round doorway flap. Take the room and its light from it."),
    "@OpenSea": ("Location/loc_open_sea.png",
                 "THE OPEN SEA: calm open ocean on a planet with no land, glass-clear turquoise water, a bright "
                 "blue-white sky with faint stars, the huge close moon over the horizon."),
    "@Turning": ("Location/ref-Turning.png",
                 "THE TURNING LIGHT, a colour and light reference only: a violet-grey bruised evening sky, deep indigo "
                 "water, cool silver light. Take only its colour and light, nothing of its composition."),
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
         series="P1 take 2 (CEO round 2, 1:05: moving away from camera toward what lies ahead; Turning)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. From behind THE MOUNT, following it as it moves away from the camera "
              "into the pillars ahead; the camera never gets in front of it; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Pillars", "@Turning"],
         heading="BETWEEN THE STORM PILLARS. THE MOUNT heads away from us, into silent columns of cloud taller than "
                 "anything they know.",
         frame="Behind THE MOUNT: we see its back, its tail and the backs of THE THREE RIDERS; ahead of them the thin "
               "straight pillars stand on the sea and rise beyond the top of the frame. Evening turning light.",
         particles="spray from the wings, whirlpool mist at the pillar bases, a few drifting specks.",
         beats=["[0s] THE MOUNT bursts up through the surface from below, water pouring off its wings, and glides away "
                "from the camera toward the pillars ahead; small whirlpools turn at their bases.",
                "[2.5s] THE THREE RIDERS, still facing away from us, tip their heads back to look up at the pillars.",
                "[4s] THE MOUNT passes between the first two pillars, heading deeper in, away from us."],
         audio="-", sound="silence; nobody speaks",
         crit="no one facing the camera, no mount turning toward the camera, no faces to camera, no tornado, no funnel, "
              "no cone shape, no debris, no dialogue, no bright midday light, no storm, no lightning, no rain, calm air",
         review=["Moving away from camera, never facing it.", "Evening turning light.", "Pillars thin and straight."],
         end="Deeper among the pillars, heading on."),
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
    # ---- the new opening, CEO 2026-09-25, take 2 after his notes (letter ...-ceo-notes-p1-round1.md) ----
    dict(prefix="o", n=1, slug="the-runner", title="THE RUNNER", s=15, grade="DAY",
         series="new opening take 2 (CEO notes 2026-09-25: camera approved; runner blue; chief busy; real emotion)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A long lateral tracking shot that runs alongside THE RUNNER the whole "
              "way; no cut, no zoom, no slow motion.",
         refs=["@Runner", "@Chief", "@Strong", "@Village", "@Villagers"],
         heading="MORNING IN THE VILLAGE. A young fisherman runs in panic across the village to THE CHIEF, who is out "
                 "working with THE STRONG ONE.",
         frame="Tracking beside THE RUNNER at his height, the village streaming past behind him: wooden walkways, "
               "rope bridges, glowing grass, glass-clear water below; villagers only far off and soft.",
         particles="water flicking up from his feet, sea spray glinting, a few glowing specks drifting in the air.",
         beats=["[0s] THE RUNNER bursts onto a wooden walkway running flat out, face twisted with fear, mouth open, "
                "panting hard, gill frills flared pale.",
                "[3s] THE RUNNER leaps the gap between two platforms, lands hard and keeps running across a swaying rope "
                "bridge; far-off villagers turn to watch.",
                "[7s] The camera keeps pace as THE RUNNER sprints up a short ramp to a wide platform where THE CHIEF and "
                "THE STRONG ONE are busy together, hauling a woven fish trap up out of the water: it comes up empty.",
                "[10s] THE RUNNER stumbles to a stop, chest heaving. Out of breath: \"Chief! There are no fish. None "
                "left.\"",
                "[12.5s] Then, desperate: \"We're starving. Please, do something.\" THE CHIEF and THE STRONG ONE let the "
                "empty trap drop and turn to him."],
         audio="-",
         sound="THE RUNNER's loud, ragged panting, clearly heard the whole time he runs, then the two lines above, "
               "gasped out between breaths; the strain of the two men hauling",
         crit=DIALOGUE_NEG + ", no cut, no slow motion, no second runner, no one falling into the water, no weapon, no "
              "orange skin on the runner, no calm faces",
         review=["Camera as take 1 (approved).", "THE RUNNER is turquoise-blue with navy gills, not orange.",
                 "THE CHIEF and THE STRONG ONE are working, not standing still.", "Panting clearly audible; two lines."],
         end="THE RUNNER, THE CHIEF and THE STRONG ONE on the platform by the empty trap."),
    dict(prefix="o", n=2, slug="the-chief-decides", title="THE CHIEF DECIDES", s=6, grade="DAY",
         series="new opening take 2 (CEO: the time has truly come, fear and despair on his face)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A slow push-in to a close-up of THE CHIEF; no cut.",
         refs=["@Chief", "@Strong", "@Runner", "@Village"],
         heading="THE CHIEF understands what the empty sea means. THE CHIEF is afraid, and decides anyway.",
         frame="Close on THE CHIEF, the empty trap and the sea behind him, THE STRONG ONE and THE RUNNER soft at the "
               "edges of frame.",
         particles="sea spray drifting, a few glowing specks in the air.",
         beats=["[0s] THE CHIEF stares at the empty trap, then out at the empty sea; fear rises in his face, his jaw "
                "trembles, his gill frills fade pale.",
                "[2s] Heavy with dread: \"So... the day has come.\"",
                "[4s] Barely a whisper, eyes wet: \"We need the child with the gift.\" THE STRONG ONE turns to look "
                "at him."],
         audio="-",
         sound="the two lines above, THE CHIEF's voice shaking with fear and despair, and his unsteady breath",
         crit=DIALOGUE_NEG + ", no calm face, no smile, no second chief, no crowd close",
         review=["Fear and despair clearly on THE CHIEF's face.", "Two lines, in order; transcribe."],
         end="THE CHIEF turns to go to the child's hut; THE STRONG ONE follows."),
    dict(prefix="o", n=3, slug="the-hut", title="THE HUT", s=10, grade="DAY",
         series="round 3 (CEO answers 1, 4, C7: the elder waits outside too; gills flash; You two will go)",
         spec="ONE LOCKED SHOT, NO CUTS. The camera sits inside the hut at the child's height and never moves.",
         refs=["@Hut", "@Young", "@Chief", "@Strong", "@Elder"],
         heading="INSIDE THE CHILD'S HUT. THE CHIEF comes in for THE YOUNG ONE; THE STRONG ONE and THE ELDER wait "
                 "outside the door.",
         frame="Inside the hut looking toward the doorway; THE YOUNG ONE seated on the floor in the foreground, the "
               "doorway in the back of the frame. Only two are inside: THE YOUNG ONE and THE CHIEF. Outside the doorway "
               "stand THE STRONG ONE and THE ELDER.",
         particles="dust motes floating in the lamp light and in the beam of daylight from the doorway.",
         beats=["[0s] Inside the hut, soft lamp light. THE YOUNG ONE sits on the floor arranging small shells.",
                "[2s] The door flap is pulled open; daylight floods in; THE CHIEF stoops inside. Behind THE CHIEF, THE STRONG "
                "ONE and THE ELDER stay standing just outside the open doorway and do not come in.",
                "[4s] THE CHIEF kneels in front of THE YOUNG ONE. Softly: \"It's time.\"",
                "[5.5s] Then, gently: \"You are the chosen one.\" The gill frills of THE YOUNG ONE flash gold, once.",
                "[7.5s] THE CHIEF turns his head toward the doorway. Firmly: \"You two will go with the child.\" "
                "THE STRONG ONE and THE ELDER nod."],
         audio="-",
         sound="the three lines above, THE YOUNG ONE's small surprised breath, the flap swishing open",
         crit=DIALOGUE_NEG + ", no camera move, no second child, no fish, no crying, THE STRONG ONE and THE ELDER never "
              "inside the hut, no third person inside, no land or island seen through the doorway, only sea and sky",
         review=["Two inside; THE STRONG ONE and THE ELDER outside the doorway.", "Gills flash gold once.",
                 "Three lines, in order; transcribe."],
         end="THE YOUNG ONE stands to go; the two men wait at the door."),
    dict(prefix="o", n=4, slug="the-farewell", title="THE FAREWELL", s=8, grade="DAY",
         series="new opening take 2 (CEO: wide angle, wide lens)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. An extreme wide shot on a wide lens from the far end of the dock, a slow "
              "crane up as THE MOUNT pulls away; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Pole", "@Dock", "@Chief", "@Villagers", "@Villagers2"],
         heading="THE FAREWELL AT THE MANTA DOCK, WIDE. The whole village sees THE THREE RIDERS off.",
         frame="Extreme wide: the whole dock and the crowd small in the foreground, THE MOUNT in the water beyond, the "
               "village of giant trees and the open sea filling the frame; the seat order is THE STRONG ONE on the "
               "front perch, THE YOUNG ONE in the middle, THE ELDER at the back.",
         particles="sea spray glinting, glowing specks drifting in the air, the wake sparkling.",
         beats=["[0s] THE MOUNT waits at the dock with THE THREE RIDERS on its seat, a glowing shell lantern hanging "
                "from it; villagers crowd the edge of the dock.",
                "[2s] THE STRONG ONE pushes off with THE POLE and THE MOUNT glides out over the glass-clear water.",
                "[4s] The villagers wave; a small girl waves with both hands; THE CHIEF raises his crystal staff.",
                "[6s] THE YOUNG ONE turns on the seat and waves back as THE MOUNT pulls away over the clearest water, "
                "heading for the open sea."],
         audio="-",
         sound="the villagers' wordless calls of goodbye, nothing else",
         crit="no dialogue, no boat, no fourth rider, no one crying, no crowd lined up in a row, no weapon, no close-up",
         review=["Wide lens, extreme wide.", "THE THREE RIDERS in the fixed seat order.", "THE CHIEF raises the staff."],
         end="Seat order fixed; they head for open sea."),
    # ---- CEO notes round 2 (MAC CTO letter ...-ceo-notes-round2.md): N1-N5 take 2 + the new ending N6-N9 ----
    dict(prefix="n", n=1, slug="leaving-the-village-high", title="LEAVING THE VILLAGE, FROM HIGH ABOVE", s=6, grade="DAY",
         series="round 2: take 2 (0:43, the model got confused: character pictures removed, aerial only)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A high aerial shot looking down for the whole six seconds, slowly rising; "
              "the camera never comes down to the riders; no cut, no zoom.",
         refs=["@Manta", "@Village"],
         heading="FROM HIGH ABOVE, THE MOUNT LEAVES THE VILLAGE with three tiny riders on its back.",
         frame="Straight down from high above: THE MOUNT small in the lower middle of the frame, a long wake trailing "
               "back to the village of giant trees at the bottom edge; the rest of the frame is open glass-clear sea.",
         particles="sea spray glinting in the light, the wake sparkling.",
         beats=["[0s] From high above, THE MOUNT glides away from the village with three tiny riders on its seat.",
                "[2s] The camera keeps rising; the village shrinks at the bottom of the frame.",
                "[4s] Only open sea ahead, bright and calm, all the way to the horizon."],
         audio="-", sound="silence; nobody speaks",
         crit="no dialogue, no close-up, no medium shot, no people standing, no faces, no black water, no dark line, no "
              "storm, no land, no boat",
         review=["Aerial from start to end; never comes down to the riders.", "No dark line yet."],
         end="THE MOUNT out on the open sea."),
    dict(prefix="n", n=2, slug="the-dive", title="THE DIVE", s=6, grade="DAY",
         series="round 2: take 2 (0:49: left to right, parallel tracking, no tilt)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A parallel side-on tracking shot that moves left to right with THE MOUNT "
              "and follows it down under the surface; the camera stays level the whole time, no tilt, no cut.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@OpenSea"],
         heading="THE DIVE. THE MOUNT carries THE THREE RIDERS from the surface down into the sea, travelling left to "
                 "right.",
         frame="Side on and level, THE MOUNT moving from the left of frame to the right; first half above the "
               "waterline, then below it, the camera sinking with it and staying level.",
         particles="a burst of silver bubbles as they go under, small bubbles rising, drifting specks in the water, "
                   "shafts of light from the surface.",
         beats=["[0s] On the surface, THE MOUNT glides from left to right; THE THREE RIDERS draw a breath, gill frills "
                "flaring open.",
                "[2s] THE MOUNT tips its wings and slides under the surface, still moving left to right; the camera "
                "follows it down, level, side on.",
                "[4s] Underwater in clear blue water, THE MOUNT glides on to the right with all three on its seat."],
         audio="-", sound="THE THREE RIDERS' deep breath before the dive, then silence underwater",
         crit="no dialogue, no camera tilt, no dutch angle, no movement right to left, no rider left behind",
         review=["Left to right, parallel, level.", "Surface to underwater in one move."],
         end="Underwater, heading right."),
    dict(prefix="n", n=3, slug="the-glass-sea-wide", title="THE GLASS SEA, WIDE", s=10, grade="TURNING",
         series="round 2: take 2 (0:57: the child says wow underwater, bubbles from the mouth)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. An extreme wide shot on a wide lens, a slow lateral track from left to "
              "right keeping pace with THE MOUNT; no cut, no zoom.",
         refs=["@Manta", "@Young", "@Strong", "@Elder", "@GlassSpiral", "@GlassCathedral", "@GlassHalo", "@GlassBloom"],
         heading="THE GLASS SEA, LATE IN THE DAY. THE THREE RIDERS cross a vast underwater space, tiny, among giant glass "
                 "creatures.",
         frame="Extreme wide: THE MOUNT small in the middle band moving from left to right; below them the sea falls "
               "away into deep blue then indigo; the glass creatures drift at different depths.",
         particles="countless drifting plankton specks, small bubbles, long shafts of dimming violet-grey light from the "
                   "surface.",
         beats=["[0s] Wide and deep: THE MOUNT glides in from the left carrying THE THREE RIDERS, small in the vastness.",
                "[3s] Around them and far below, THE SPIRAL, THE DOME, THE RINGS and THE BLOOM drift, each bigger than a "
                "house, rainbow light moving through their clear bodies.",
                "[6s] THE YOUNG ONE stares at THE BLOOM, mouth open; a burst of bubbles pours out as the child says it. "
                "Amazed, underwater: \"Wowww.\"",
                "[8.5s] THE MOUNT keeps on toward the right of frame, the deep blue opening beneath them."],
         audio="-",
         sound="THE YOUNG ONE's muffled, bubbling underwater \"Wowww\", sounding truly underwater, and nothing else",
         crit=DIALOGUE_NEG + ", no jellyfish, no squid, no octopus, no fish, no movement right to left, no bright noon "
              "light underwater",
         review=["Bubbles from the child's mouth with the Wowww.", "Left to right, wide."],
         end="THE MOUNT heading right."),
    dict(prefix="n", n=4, slug="the-line-they-stop", title="THE LINE: THEY STOP", s=8, grade="TURNING",
         series="round 3 (CEO answers: only the elder speaks; thunder and moving clouds before the crossing)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. From high behind THE MOUNT, then a slow crane down behind THE THREE RIDERS; "
              "the camera stays behind them the whole time; no cut, no zoom.",
         refs=["@Line", "@Turning", "@Manta", "@Elder", "@Strong", "@Young"],
         heading="THE LINE, AT EVENING. THE MOUNT stops in front of it. We see it through their eyes, from behind them, "
                 "and the sky ahead is already moving.",
         frame="Behind and above THE MOUNT: THE THREE RIDERS and THE MOUNT all face away from the camera, toward the "
               "razor-sharp line ahead; clear water under them, pitch-black water beyond the line, where dark storm "
               "clouds roll and churn visibly across the sky. The light and colour are the evening turning.",
         particles="spray blowing off the line, the first drops of rain carried on the wind.",
         beats=["[0s] From high behind, THE MOUNT glides up to the line and stops at its edge, facing the black water.",
                "[2s] The camera cranes down behind THE THREE RIDERS; beyond the line the storm clouds churn and roll "
                "toward them, and thunder rumbles.",
                "[4s] THE ELDER, low: \"So this is it. The line of death.\"",
                "[6s] Nobody moves. A flash of violet lightning far beyond the line lights the black water."],
         audio="-", sound="the line above and nothing else; the riders' held breath",
         crit=DIALOGUE_NEG + ", no one facing the camera, no mount turning toward the camera, no crossing yet, no second "
              "line spoken, no bright midday sky, no sunset orange, no rain on the clear side yet",
         review=["Nobody faces the camera; all face the line.", "Clouds visibly moving; thunder.",
                 "One line, THE ELDER; transcribe."],
         end="Stopped at the line, facing it; storm rolling beyond."),
    dict(prefix="n", n=5, slug="the-crossing", title="THE CROSSING", s=6, grade="DARK",
         series="round 3 (CEO answers 10, 12: cross a little; EVERY light flickers and dies, very clearly; darkness)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. From behind THE MOUNT, moving with it as it crosses away from the camera; "
              "no cut, no zoom.",
         refs=["@Manta", "@Lantern", "@LanternDark", "@BlackSea", "@Strong", "@Elder", "@Young"],
         heading="THE CROSSING. THE MOUNT slips over the line into the black water, and every light they carry dies.",
         frame="Behind THE MOUNT: THE THREE RIDERS with their backs to us; THE LANTERN hangs lit from the seat and the "
               "small seed-pod lamps glow along the seat; ahead, pitch-black water under the storm.",
         particles="rain beginning to fall as they cross, drops streaking through the last of the lamp light.",
         beats=["[0s] THE MOUNT glides forward over the razor-sharp line, away from us, into the pitch-black water; rain "
                "starts to fall.",
                "[2s] THE LANTERN and every seed-pod lamp on the seat flicker hard, stutter, flicker again.",
                "[3.5s] One by one they all go out. THE LANTERN is dead and dark. Every light is gone.",
                "[4.5s] Darkness. Only a faint grey outline of THE THREE RIDERS in the rain."],
         audio="-", sound="the riders' sharp, frightened breaths as the lights die, nothing else",
         crit="no dialogue, no light left burning, no glow from the child yet, no one facing the camera, no fire, no "
              "flames, no explosion",
         review=["All lights flicker and die, very clearly.", "Ends in darkness.", "Moving away from the camera."],
         end="THE MOUNT in darkness just past the line; every light dead."),
    dict(prefix="n", n=6, slug="the-light", title="THE LIGHT", s=8, grade="DARK",
         series="round 3 (CEO answers 2, 12: in the dark, the strong one's line, then the light from the child)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A three-quarter view from behind THE MOUNT, slowly rising; no cut, no zoom.",
         refs=["@Young", "@Manta", "@BlackSea", "@Turning", "@Strong", "@Elder"],
         heading="THE LIGHT. In the black rain, THE YOUNG ONE becomes their lantern.",
         frame="Behind and a little above THE MOUNT on pitch-black water in the rain; THE THREE RIDERS face ahead, "
               "barely visible in the dark.",
         particles="rain streaks falling through the light, warm golden motes rising from THE YOUNG ONE.",
         beats=["[0s] Darkness and rain. THE STRONG ONE turns his head to THE YOUNG ONE. Quietly: \"We need your light "
                "now.\"",
                "[3s] THE YOUNG ONE closes both eyes; GLOW",
                "[5.5s] THE MOUNT glides on into the dark, away from us, carrying its small moving pool of light."],
         audio="-", sound="the line above, then THE YOUNG ONE's slow breath as the light blooms",
         crit=DIALOGUE_NEG + ", no wide ring of light, no light reaching more than two metres, no beam into the sky, no "
              "other light source, no lantern light, no lamps",
         review=["One line, THE STRONG ONE; transcribe.", "Glow radius about 1-2 m; Turning-coloured water inside it."],
         end="THE YOUNG ONE glowing, the moving lantern, from here to the end."),
    dict(prefix="n", n=7, slug="the-giant-wave", title="THE GIANT WAVE", s=8, grade="DARK",
         series="round 3 (CEO answer C3: after the light, the giant wave, before the fish)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. Low behind THE MOUNT, looking past it at the wave rising ahead; camera "
              "shake; no cut, no zoom.",
         refs=["@Waves", "@Manta", "@Strong", "@Pole", "@Elder", "@Young"],
         heading="THE WAVE. Ahead of them, in the black rain, a wall of water as tall as a mountain rises.",
         frame="Low behind THE MOUNT, small in the lower frame with THE YOUNG ONE glowing on it; the wave rises ahead "
               "and fills everything above.",
         particles="heavy rain, spray torn off the wave crest, bubbles as they go under.",
         beats=["[0s] GLOW Ahead of THE MOUNT a colossal wave rises against the wind, black water glowing faintly cyan "
                "and magenta inside, curling over them.",
                "[2.5s] THE STRONG ONE drives THE POLE down. A shout: \"Hold on!\"",
                "[4s] THE MOUNT dives straight into the base of the wave, away from us; THE THREE RIDERS cling on.",
                "[6s] The wave crashes over the place where they were; beyond it, a small glow keeps moving."],
         audio="-", sound="the shout above, the riders' gasps and effort, nothing else",
         crit=DIALOGUE_NEG + ", no rider falling off, no one facing the camera, no movement toward the camera, no light "
              "wider than two metres around the child",
         review=["The wave is colossal against them.", "One shout; transcribe.", "They go through, away from us."],
         end="Past the wave, THE MOUNT glides on in the rain."),
    dict(prefix="n", n=8, slug="the-school", title="THE SCHOOL", s=8, grade="DARK",
         series="round 3 (CEO answers 13, C3: excitement at the school; the sea goes still; the mount stops)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. Side on at the surface, moving left to right with THE MOUNT, then "
              "settling as it stops; no cut, no zoom.",
         refs=["@Strong", "@Young", "@Manta", "@Elder", "@BlackSea", "@Turning"],
         heading="FISH. At the surface, inside the child's small light, the water under them is suddenly full of fish.",
         frame="Side on at the surface: THE MOUNT moving left to right, THE YOUNG ONE glowing on the seat; the lit "
               "circle of water around them is the only thing visible; beyond it, black.",
         particles="rain dimpling the flat surface, the glint of fish passing just below it.",
         beats=["[0s] GLOW THE MOUNT glides from left to right on water that is growing flat and calm in the rain.",
                "[2s] In the lit circle below the surface, many small dark fish shadows dart past, dozens of them.",
                "[4s] THE THREE RIDERS lean over the edge, thrilled, pointing; THE STRONG ONE laughs.",
                "[6s] THE STRONG ONE raises a hand; THE MOUNT slows and stops on the flat water."],
         audio="-", sound="the riders' excited gasps and THE STRONG ONE's laugh, nothing else",
         crit="no dialogue, no colourful fish, no big fish, no underwater camera, no waves, no light wider than two metres",
         review=["Surface only; fish as small dark shadows in the lit circle.", "Water flat and calm, rain falling.",
                 "Left to right, then the mount stops."],
         end="THE MOUNT stopped on flat water among the fish."),
    dict(prefix="n", n=9, slug="one-fish", title="ONE FISH", s=7, grade="DARK",
         series="round 3 (CEO answers 13, C1: no net; a quick chase and a grab by hand; everyone cheers)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A medium shot beside THE MOUNT at the surface; no cut, no zoom.",
         refs=["@Strong", "@Young", "@Elder", "@Manta", "@BlackSea"],
         heading="ONE FISH. This is why they came: THE STRONG ONE catches a fish with his bare hands.",
         frame="Medium, beside THE MOUNT at the surface: THE STRONG ONE leaning over the edge of the seat, THE YOUNG ONE "
               "glowing beside him, THE ELDER behind.",
         particles="rain, water splashing up as the hands go in, golden motes around THE YOUNG ONE.",
         beats=["[0s] GLOW THE STRONG ONE leans far over the edge, eyes locked on a fish shadow darting along the side.",
                "[2s] Quick: his hands chase it through the water, once, twice.",
                "[3.5s] THE STRONG ONE lunges and snatches it out: one dark glossy silver-black fish, flapping in his hands.",
                "[5s] All three cheer; THE STRONG ONE holds it up, laughing."],
         audio="-", sound="splashes of the hands, THE STRONG ONE's effort, then all three cheering and laughing",
         crit="no dialogue, no net, no spear, no hook, no second fish, no one falling in",
         review=["Caught by hand, no net.", "Fast chase, then the grab.", "Everyone cheers."],
         end="THE STRONG ONE holding one fish, all three happy."),
    dict(prefix="n", n=10, slug="the-shadow", title="THE SHADOW", s=8, grade="DARK",
         series="round 3 (CEO answers 22, C2: from very high, the mount a tiny speck; the shadow only; flat water, rain)",
         spec="ONE LOCKED SHOT, NO CUTS. Straight down from very high above; the camera never moves.",
         refs=["@Manta", "@BlackSea", "@Young"],
         heading="THE SHADOW. From very high: the mount is a tiny speck of light, and something enormous passes beneath.",
         frame="Top-down from very high: THE MOUNT a tiny speck with its tiny circle of light in the centre of a vast "
               "black sea; the sea surface flat and calm under the rain.",
         particles="rain falling toward the flat water, a faint shimmer across the surface.",
         beats=["[0s] GLOW Seen from very high, THE MOUNT is a tiny glowing speck on a flat black sea in the rain.",
                "[2s] Beneath it, deep down, an enormous dark shadow slides slowly past, hundreds of times bigger than THE "
                "MOUNT, its edges lost in the dark.",
                "[4s] The tiny fish shadows around the speck of light scatter in every direction and vanish.",
                "[6s] The shadow is gone. The flat sea is empty. Only the tiny speck of light remains."],
         audio="-", sound="silence; nobody speaks; the faintest startled gasp",
         crit="no dialogue, no camera move, no creature shape, no eye, no fin, no surfacing, no waves, only a shadow",
         review=["Top-down from very high; the mount a speck.", "A shadow only, enormous.", "The fish vanish."],
         end="Flat black sea, rain, THE MOUNT alone."),
    dict(prefix="n", n=11, slug="the-mountain-rises", title="THE MOUNTAIN RISES", s=12, grade="DARK",
         series="round 3 (CEO answers 6, 14, C2: they turn back to their fish; the mountain rises; TWO eyes open)",
         spec="ONE LOCKED SHOT, NO CUTS. A wide shot from behind and above THE MOUNT; the camera never moves.",
         refs=["@Mountain", "@Eye", "@Manta", "@Strong", "@Young", "@Elder"],
         heading="THE MOUNTAIN RISES. Behind them, where no land can be, a mountain comes up out of the flat sea.",
         frame="THE MOUNT small in the lower third on flat black water in the rain, lit only by THE YOUNG ONE; the far "
               "water behind them fills the upper frame.",
         particles="rain, a thin mist over the flat water, water pouring off the rising shape.",
         beats=["[0s] GLOW THE THREE RIDERS glance around, shrug, and turn back to their one fish, laughing quietly, "
                "their backs to the far water.",
                "[3s] Far behind them the flat water bulges; a vast smooth dark shape slowly rises out of the sea like a "
                "mountain, water pouring off it. Nobody on THE MOUNT notices.",
                "[8s] High on the dark mountain, two enormous eyes open: pale yellow-green, thin vertical slit pupils, "
                "each bigger than their whole village.",
                "[10.5s] Both eyes stay open, looking down at them. Hold."],
         audio="-", sound="the riders' quiet happy laughter, then total silence as the eyes open",
         crit="no dialogue, no riders turning around, no roar, no teeth, no third eye, no camera move, no waves, no light "
              "wider than two metres around the child",
         review=["They turn back to the fish, unaware.", "The mountain rises slowly behind them.", "Two eyes open."],
         end="Both eyes open; cut to space (M13, take 1)."),
]


# ai-film-production §13: each character's reference text must carry its CAST.md row's key colours.
CAST_KEYS = {
    "@Young": ["coral-pink", "gold freckles", "orange-gold", "satchel"],
    "@Elder": ["teal-blue", "violet", "torn"],
    "@Strong": ["moss-green", "lime-green", "tipped gold", "kelp belt", "kelp rope"],
    "@Manta": ["sea-green", "lime-green", "driftwood", "bone ribs"],
    "@Villagers": ["mint", "lavender", "pale blue", "sand-yellow", "orange", "rose"],
    "@Eye": ["pale yellow-green", "slit pupils"],
    "@Chief": ["pearl-white", "sapphire-blue", "raw uncut gemstones", "shell scales", "quartz"],
    "@Runner": ["turquoise-blue", "navy-blue", "kelp rope"],
}
SEAT_ORDER = "THE STRONG ONE on the front perch, THE YOUNG ONE in the middle, THE ELDER at the back"


# CEO 2026-09-25: "Audio เราไม่เอาเสียง Background นะ". Our own block carries the Studio's marker
# `non_diegetic_music: none`, so the Studio does not append its standing "wind and room tone" block (MAC CTO letter).
SOUND = {
    ("m", 1): "silence; nobody speaks", ("m", 2): "THE STRONG ONE's effort breaths as he hauls the net",
    ("m", 3): "the two lines above and THE ELDER's quiet breath", ("m", 4): "silence; nobody speaks",
    ("m", 5): "silence; nobody speaks", ("m", 6): "silence; nobody speaks", ("m", 7): "the two lines above",
    ("m", 8): "the riders' sharp breaths as the lightning cracks",
    ("m", 9): "the whisper above and THE YOUNG ONE's shaky breathing",
    ("m", 10): "the shout above and the riders' gasps", ("m", 11): "the whisper above",
    ("m", 12): "silence", ("m", 13): "silence",
    ("n", 1): "silence; nobody speaks", ("n", 2): "THE THREE RIDERS' deep breath before the dive",
    ("n", 3): "silence; nobody speaks", ("n", 4): "the two lines above",
    ("n", 5): "THE YOUNG ONE's slow breath as the light blooms",
}


GLOW = ("THE YOUNG ONE glows like a living lantern: a warm golden light from the whole body, gill frills blazing "
        "gold, lighting only about one to two metres around the child; inside that small circle the black water "
        "turns to the lit deep-indigo water of the turning light, and beyond it everything stays pitch black.")


def tag(sc):
    return f"{sc.get('prefix', 'm').upper()}{sc['n']}"


def paste_block(sc):
    lines = [f"{sc['s']}s · 360p · 16:9 · {sc['spec']}", "", sc["heading"], "", "REFERENCES, each with a job:"]
    for h in sc["refs"]:
        lines.append(f"{h}: {REF[h][1]}")
    sc = dict(sc, beats=[b.replace("GLOW", GLOW) for b in sc["beats"]])
    lines += ["", "THE FRAME: " + sc["frame"]]
    if sc.get("particles"):
        lines += ["", "PARTICLES: " + sc["particles"]]
    lines += ["", "WHAT HAPPENS:"]
    lines += sc["beats"]
    snd = sc.get("sound") or SOUND.get((sc.get("prefix", "m"), sc["n"]), "silence; nobody speaks")
    lines += ["", "overall_soundscape: only the characters' own voices, breathing and effort sounds: " + snd +
              ". No ambient bed: no wind, no water, no rain, no birds, no crowd murmur, no room tone.",
              "non_diegetic_music: none.", "", GRADE[sc["grade"]], "",
              "CRITICAL NEGATIVES: " + sc["crit"] + ".", "", HOUSE_NEG]
    return "\n".join(lines)


def notes_top(sc):
    refs = "\n".join(f"  {h} -> Drive {DRIVE}{REF[h][0]}" for h in sc["refs"])
    return (f"{tag(sc)} · {sc['title']} · {sc['s']}s · {sc['grade']} · {sc.get('series', 'P1 main scenes (SCRIPT.md draft 2)')}\n\n"
            "Engine: our MiniMax H3 studio, 360p previz, 16:9. Type each @handle once (it already appears once in\n"
            "the paste block); the studio attaches its picture. Every picture is a SINGLE panel: a multi-panel\n"
            "sheet renders as a grid video on H3.\n"
            f"References ({len(sc['refs'])}):\n{refs}")


def notes_bottom(sc):
    review = "\n".join(f"{i}. {r}" for i, r in enumerate(sc["review"], 1))
    return (f"REVIEW ORDER:\n{review}\nFile the take whatever the verdict, as {tag(sc)}-H3-take<N>.mp4 in the\n"
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
        out = HERE / f"{sc.get('prefix', 'm')}{sc['n']:02d}-{sc['slug']}.txt"
        out.write_text(text, encoding="utf-8")
        print(out.name, len(body.split()), "words", len(sc["refs"]), "refs")


if __name__ == "__main__":
    main()
