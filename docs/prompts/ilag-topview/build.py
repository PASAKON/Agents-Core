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
    # @Runner (turquoise, ref-Runner-blue.png) is retired: THE ELDER is blue too (CEO 2026-09-25, round 11 #1).
    "@RunnerY": ("Character/char_runner_yellow_A.png",
                 "THE RUNNER, a tall thin young man of the same people: mustard-yellow skin with faint darker "
                 "golden-brown freckles, dark chocolate-brown gill frills, a coiled kelp rope over one shoulder, a "
                 "necklace of small shells, a woven kelp belt. Face, body and colours only; take nothing of the white "
                 "background."),
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
    "DARK_GLOW": "Colour grade, the dark with the child's light: pitch-black water in steady rain, the warm golden glow "
                 "of THE YOUNG ONE the only light, deep indigo water inside its 2-metre circle, deep true blacks "
                 "everywhere else. Photographed, not rendered: fine film grain.",
    "DARK": "Colour grade, the dark: pitch-black water and a purple-black storm, violet lightning as the key light, "
            "cyan and magenta glints, deep true blacks. Photographed, not rendered: fine film grain.",
}

HOUSE_NEG = ("House negatives: no humans, no human faces, no human hands; no land, no island, no beach, no rocks "
             "above the water; no boats, no ships, no oars, no sails; no metal, no plastic, no modern objects; no text, "
             "no subtitles, no captions, no logos, no watermark; no grid, no split screen, no panels, no white studio "
             "background; no cartoon, no anime, no plastic skin; no music, no score; no dutch angle, no lens flare.")
DIALOGUE_NEG = ("no stage directions spoken aloud, no narration of anyone's feelings, no speaking anything outside "
                "the quotation marks, no extra lines, no voiceover")
# CEO 2026-09-25 (cut 4): words nobody wrote were spoken in shots with no dialogue.
NO_WORDS = "no words spoken by anyone, no talking, no shouted words, no voiceover"
# CEO 2026-09-25: in the dark the child is the only light, a 2-metre circle that turns the water to the turning.
TURNING_IN_CIRCLE = ("THE TURNING LIGHT, a colour reference only: the deep indigo of the water INSIDE the "
                     "child's circle of light; nothing of its sky, its light or its composition.")

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
    dict(n=4, slug="leaving", title="LEAVING", s=8, grade="DAY",
         series="cut 4 (CEO 2026-09-25: every rider acts; left to right as take 1)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A wide side-on tracking shot moving with THE MOUNT from the left of frame "
              "to the right; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Pole", "@Lantern", "@Dock"],
         heading="THE THREE LEAVE THE VILLAGE on THE MOUNT, out over the clearest water, each busy with the start of the "
                 "journey.",
         frame="Wide, side on: THE MOUNT moving from the left of frame to the right across glass-clear turquoise water, "
               "the village of giant trees behind them on the left; the seat order is THE STRONG ONE on the front perch, THE YOUNG ONE in the middle, THE ELDER at the back, and it never changes in "
               "this film.",
         particles="spray from the wing tips, the wake sparkling, a few glowing specks drifting in the air.",
         actions=["THE STRONG ONE, front perch: works THE POLE in long strong strokes, steering, then glances back over "
                  "his shoulder and grins at the other two.",
                  "THE YOUNG ONE, middle: kneels up to look back at the village and waves one last time, then turns "
                  "forward, leans over the edge and trails one hand through the water, delighted.",
                  "THE ELDER, back: reaches up and straightens THE LANTERN on its hook so it hangs steady, then sits on "
                  "the edge of the seat and lets both feet dangle so his toes skim the water, eyes half closed."],
         beats=["[0s] THE MOUNT glides from left to right over glass-clear turquoise water, wings rippling; THE LANTERN "
                "glows gold, hanging from the seat. THE STRONG ONE steers with THE POLE.",
                "[2.5s] THE YOUNG ONE waves back at the village one last time; THE ELDER straightens THE LANTERN on its "
                "hook.",
                "[5s] THE YOUNG ONE trails a hand through the water, laughing; THE STRONG ONE grins back at the child; "
                "THE ELDER sits on the edge of the seat, toes skimming the water."],
         audio="-",
         sound="THE YOUNG ONE's delighted laugh and the splash of the child's hand and THE ELDER's toes in the water, "
               "nothing else",
         crit="no dialogue, no fourth rider, no boat, no oars, no second mount beside them, no movement right to left",
         review=["Left to right, side on.", "Each rider doing their own action.", "THE LANTERN is glowing."],
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
    dict(n=6, slug="the-storm-pillars", title="THE STORM PILLARS", s=8, grade="TURNING",
         series="cut 4 (CEO 2026-09-25: every rider acts; still moving away from the camera, Turning)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. From behind THE MOUNT, following it as it moves away from the camera "
              "into the pillars ahead; the camera never gets in front of it; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Pillars", "@Turning"],
         heading="BETWEEN THE STORM PILLARS. THE MOUNT bursts up from the dive, drops back onto the sea and swims away "
                 "from us, into silent columns of cloud taller than anything they know.",
         frame="Behind THE MOUNT: we see its back, its tail and the backs of THE THREE RIDERS; ahead of them the thin "
               "straight pillars stand on the sea and rise beyond the top of the frame. After the burst, THE MOUNT is "
               "IN the water: its body half under the surface, its wing tips slicing the water, a wake churning behind "
               "it. Evening turning light.",
         particles="spray from the wings, water streaming off the riders, whirlpool mist at the pillar bases.",
         actions=["THE STRONG ONE, front perch: as they burst up he shakes his head hard so water flies off his gills, "
                  "spits out a mouthful of sea, grips the steering pole and steers between the pillars, leaning left, "
                  "then right.",
                  "THE YOUNG ONE, middle: laughs and slaps the surface of the water beside the seat with one hand, "
                  "splashing, then stops, looks up at the tallest pillar and tugs THE ELDER's arm, pointing.",
                  "THE ELDER, back: squeezes the water out of his long gill frills with both hands, then follows the "
                  "child's pointing arm and scans the pillars left and right, wary."],
         beats=["[0s] THE MOUNT bursts up through the surface from below, water pouring off its wings and off THE THREE "
                "RIDERS, then drops back down onto the sea with a splash and swims on at the surface, wing tips slicing "
                "the water, away from the camera toward the pillars ahead; small whirlpools turn at their bases.",
                "[2.5s] THE STRONG ONE shakes his head hard, spits out sea water and grips the steering pole; THE YOUNG "
                "ONE laughs and slaps the water beside the seat; THE ELDER wrings the water out of his gill frills.",
                "[5s] THE YOUNG ONE looks up, tugs THE ELDER's arm and points at the tallest pillar; THE ELDER follows the "
                "arm, wary; THE STRONG ONE steers between the first two pillars, leaning into the turn, heading deeper "
                "in, away from us, wake churning behind."],
         audio="-", sound="the riders' sharp breaths as they burst up, THE STRONG ONE spitting water, THE YOUNG ONE's "
                          "laugh and splash; nobody speaks",
         crit="no one facing the camera, no mount turning toward the camera, no mount floating above the water, no mount "
              "flying, no gap between the mount and the sea, no tornado, no funnel, no cone shape, no debris, no "
              "dialogue, no storm, no lightning, no rain",
         review=["Burst up as take 2 (approved), then IN the water, never hovering above it.",
                 "Each rider reacts in their own way: head shake and spit, splash, wring the gills.",
                 "Moving away from camera, never facing it."],
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
         series="new opening take 4 (CEO 2026-09-25 cut 3: the run is approved; at the end THE STRONG ONE is worried "
                "too, the net is empty, everyone truly afraid)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A long lateral tracking shot that runs alongside THE RUNNER the whole "
              "way; no cut, no zoom, no slow motion.",
         refs=["@RunnerY", "@Chief", "@Strong", "@Village", "@Villagers"],
         heading="MORNING IN THE VILLAGE. A young fisherman runs in panic across the village to THE CHIEF, who is out "
                 "hauling the fishing net with THE STRONG ONE.",
         frame="Tracking beside THE RUNNER at his height, the village streaming past behind him: wooden walkways, "
               "rope bridges, glowing grass, glass-clear water below; villagers only far off and soft.",
         particles="water flicking up from his feet, sea spray glinting, a few glowing specks drifting in the air.",
         actions=["THE RUNNER: runs flat out in panic the whole way, then stops doubled over, gasping, pleading with "
                  "both open hands.",
                  "THE STRONG ONE: hauls the net hand over hand, sees it come up empty and stares into it, brow knotted, "
                  "jaw clenched, worried; then looks from THE RUNNER to THE CHIEF with fear in his eyes. THE STRONG ONE never smiles.",
                  "THE CHIEF: hauls the net beside THE STRONG ONE, then lets go of it and turns to THE RUNNER, his face falling."],
         beats=["[0s] THE RUNNER bursts onto a wooden walkway running flat out from the left of frame to the right, "
                "face twisted with fear, panting hard, gill frills flared pale, then leaps the gap between two "
                "platforms and races across a swaying rope bridge while far-off villagers turn to watch.",
                "[7s] The camera keeps pace as THE RUNNER sprints up a short ramp to a wide platform where THE CHIEF and "
                "THE STRONG ONE are hauling a woven kelp fishing net up out of the water: it comes up empty and "
                "dripping. THE STRONG ONE stares into the empty net, brow knotted, jaw clenched, gill frills fading pale.",
                "[10s] THE RUNNER stumbles to a stop, chest heaving. Out of breath: \"Chief! There are no fish. None "
                "left.\" THE STRONG ONE's eyes snap to THE RUNNER; THE CHIEF lets go of the net.",
                "[12.5s] Then, desperate: \"We're starving. Please, do something.\" THE STRONG ONE lets the empty net "
                "sag and looks at THE CHIEF, afraid; all three faces are frightened."],
         audio="-",
         sound="THE RUNNER's loud, ragged panting, clearly heard all through the run, then the two lines above, "
               "gasped out between breaths; THE STRONG ONE's heavy, worried breath",
         crit=DIALOGUE_NEG + ", no cut, no slow motion, no second runner, no one falling into the water, no weapon, no "
              "orange skin on the runner, no blue skin on the runner, no calm faces, no smile, no grin, no fish in the "
              "net, no fish trap, no basket",
         review=["Camera as take 2 (approved).", "THE RUNNER mustard-yellow, not orange, not blue.",
                 "At the end THE STRONG ONE is worried, never smiling; the net is empty.", "Panting clearly audible; two lines."],
         end="THE RUNNER, THE CHIEF and THE STRONG ONE on the platform, the empty net between them."),
    dict(prefix="o", n=2, slug="the-chief-decides", title="THE CHIEF DECIDES", s=9, grade="DAY",
         series="new opening take 3 (CEO 2026-09-25 cut 3: THE STRONG ONE backs the runner up, worried; everyone "
                "truly afraid)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A slow push-in from a three-shot to a close-up of THE CHIEF; no cut.",
         refs=["@Chief", "@Strong", "@RunnerY", "@Village"],
         heading="THE EMPTY NET. THE STRONG ONE backs THE RUNNER up, and THE CHIEF, afraid, decides.",
         frame="Medium three-shot on the platform: THE RUNNER on the left, THE CHIEF in the middle, THE STRONG ONE on "
               "the right holding the empty, dripping net; the empty sea behind them.",
         particles="sea spray drifting, water dripping from the net, a few glowing specks in the air.",
         actions=["THE STRONG ONE: holds the empty net up toward THE CHIEF and shakes it once so the water runs out, grim "
                  "and worried; after he speaks he searches THE CHIEF's face; at the last line he swallows and gives "
                  "one tense nod.",
                  "THE RUNNER: hugs his own arms, shaking, eyes darting between the other two; nods hard when THE STRONG "
                  "ONE backs him up; flinches at THE CHIEF's last words.",
                  "THE CHIEF: grips his staff with both hands, looks from the net to the empty sea, jaw trembling, gill "
                  "frills fading pale; after the last line he closes his eyes for a moment."],
         beats=["[0s] THE STRONG ONE holds the empty dripping net up toward THE CHIEF. Grim, to THE CHIEF: \"He's right. "
                "Not one fish, all week.\" THE RUNNER nods hard, shaking.",
                "[3s] THE CHIEF looks from the net to the empty sea; fear rises in his face, his jaw trembles. Heavy "
                "with dread: \"So... the day has come.\"",
                "[6s] The camera has pushed in close on THE CHIEF. Barely a whisper, eyes wet: \"We need the child with "
                "the gift.\" THE STRONG ONE and THE RUNNER stare at THE CHIEF, frightened; THE STRONG ONE gives one tense nod."],
         audio="-",
         sound="THE STRONG ONE's grim line, then THE CHIEF's two lines, his voice shaking with fear and despair; THE "
               "RUNNER's shaky breathing",
         crit=DIALOGUE_NEG + ", no calm face, no smile, no second chief, no crowd close, no fish in the net",
         review=["Three lines in order: THE STRONG ONE once, then THE CHIEF twice; transcribe.",
                 "Everyone afraid; nobody smiles.", "THE STRONG ONE holds the empty net."],
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
         beats=["[0s] Soft lamp light; THE YOUNG ONE sits on the floor arranging small shells. The door flap is "
                "pulled open; daylight floods in; THE CHIEF stoops inside. Behind THE CHIEF, THE STRONG "
                "ONE and THE ELDER stay standing just outside the open doorway and do not come in.",
                "[4s] THE CHIEF kneels in front of THE YOUNG ONE. Softly: \"It's time.\"",
                "[5.5s] Gently: \"You are the chosen one.\" The gill frills of THE YOUNG ONE flash gold, once.",
                "[7.5s] THE CHIEF turns his head toward the doorway. Firmly: \"You two will go with the child.\" "
                "THE STRONG ONE and THE ELDER nod."],
         audio="-",
         sound="the three lines above, THE YOUNG ONE's small surprised breath, the flap swishing open",
         crit=DIALOGUE_NEG + ", no camera move, no second child, no crying, THE STRONG ONE and THE ELDER never "
              "inside the hut, no third person inside, no land or island seen through the doorway, only sea and sky",
         review=["Two inside; THE STRONG ONE and THE ELDER outside the doorway.", "Gills flash gold once.",
                 "Three lines, in order; transcribe."],
         end="THE YOUNG ONE stands to go; the two men wait at the door."),
    dict(prefix="o", n=4, slug="the-farewell", title="THE FAREWELL", s=8, grade="DAY",
         series="new opening take 3 (CEO 2026-09-25 cut 3, 0:32: THE STRONG ONE appeared twice, on the mount and on "
                "the dock; now the riders are on the mount from the first frame, 7 references, no pole push off the dock)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. An extreme wide shot on a wide lens from the far end of the dock, a slow "
              "crane up as THE MOUNT pulls away; no cut, no zoom.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@Dock", "@Chief", "@Villagers"],
         heading="THE FAREWELL AT THE MANTA DOCK, WIDE. THE THREE RIDERS are already on THE MOUNT; the whole village sees "
                 "them off from the dock.",
         frame="Extreme wide: the dock and the crowd small in the left foreground, THE MOUNT in the water to the right of "
               "the dock with THE THREE RIDERS already on its seat, the village of giant trees and the open sea filling "
               "the frame; the seat order is THE STRONG ONE on the front perch, THE YOUNG ONE in the middle, THE ELDER at the back. THE STRONG ONE is on THE MOUNT from the first frame to the last; the "
               "only people on the dock are THE CHIEF and the villagers.",
         particles="sea spray glinting, glowing specks drifting in the air, the wake sparkling.",
         actions=["THE STRONG ONE, front perch: plants his long pale bone steering pole on the sea floor beside the dock "
                  "and shoves off with his whole body, then steers, leaning into the pole, eyes on the open sea.",
                  "THE YOUNG ONE, middle: kneels up on the seat facing the dock and waves both arms at the crowd, "
                  "bouncing, then grabs the backrest as THE MOUNT surges forward.",
                  "THE ELDER, back: raises one open hand to THE CHIEF in a slow farewell, then rests that hand on the "
                  "child's shoulder to steady the child."],
         beats=["[0s] THE MOUNT floats beside the dock with THE THREE RIDERS already on its seat; the villagers crowd the "
                "edge of the dock, calling out.",
                "[2s] THE STRONG ONE shoves off with the pole and THE MOUNT glides away from the dock over the "
                "glass-clear water; THE YOUNG ONE waves both arms.",
                "[4s] On the dock the villagers wave; a small girl waves with both hands; THE CHIEF raises his crystal "
                "staff high; THE ELDER raises a hand back to him.",
                "[6s] THE MOUNT pulls away toward the open sea, THE YOUNG ONE still waving, THE ELDER's hand on the "
                "child's shoulder, THE STRONG ONE steering."],
         audio="-",
         sound="the villagers' wordless calls of goodbye and THE YOUNG ONE's excited breath, nothing else",
         crit="no dialogue, no second STRONG ONE, nobody green or muscular on the dock, nobody on the dock holding a "
              "pole, no rider stepping onto the dock, no boat, no fourth rider, no one crying, no crowd lined up in a "
              "row, no weapon, no close-up",
         review=["Only ONE STRONG ONE, on the mount the whole time.", "Riders on the mount from the first frame.",
                 "Each rider doing their own action.", "Wide lens, extreme wide."],
         end="Seat order fixed; they head for open sea."),
    # ---- CEO notes round 2 (MAC CTO letter ...-ceo-notes-round2.md): N1-N5 take 2 + the new ending N6-N9 ----
    dict(prefix="n", n=1, slug="leaving-the-village-high", title="LEAVING THE VILLAGE, FROM HIGH ABOVE", s=6, grade="DAY",
         series="round 2: take 2 (0:43, the model got confused: character pictures removed, aerial only)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A high aerial shot looking down for the whole shot, slowly rising; "
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
         series="cut 4 (CEO 2026-09-25: every rider acts; left to right, parallel tracking, no tilt)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A parallel side-on tracking shot that moves left to right with THE MOUNT "
              "and follows it down under the surface; the camera stays level the whole time, no tilt, no cut.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@OpenSea"],
         heading="THE DIVE. THE MOUNT carries THE THREE RIDERS from the surface down into the sea, travelling left to "
                 "right.",
         frame="Side on and level, THE MOUNT moving from the left of frame to the right; first half above the "
               "waterline, then below it, the camera sinking with it and staying level.",
         particles="a burst of silver bubbles as they go under, small bubbles rising, drifting specks in the water, "
                   "shafts of light from the surface.",
         actions=["THE STRONG ONE, front perch: looks back at the other two and lifts one fist, the signal to dive, then "
                  "crouches low over the perch as they go under.",
                  "THE YOUNG ONE, middle: sucks in a huge breath, cheeks puffed, grinning, and grabs the backrest; "
                  "underwater the child's eyes go wide, looking all around.",
                  "THE ELDER, back: nods at the signal, takes one slow calm breath and wraps an arm round the child; "
                  "underwater his gill frills fan out and he points ahead."],
         beats=["[0s] On the surface, THE MOUNT glides from left to right. THE STRONG ONE looks back and lifts a fist; THE "
                "ELDER nods; THE YOUNG ONE sucks in a huge breath, cheeks puffed, gill frills flaring open.",
                "[2s] THE MOUNT tips its wings and slides under the surface, still moving left to right; the camera "
                "follows it down, level, side on; THE STRONG ONE crouches low.",
                "[4s] Underwater in clear blue water: THE YOUNG ONE's eyes go wide, looking all around; THE ELDER points "
                "ahead; THE MOUNT glides on to the right."],
         audio="-", sound="THE THREE RIDERS' deep breath before the dive, THE YOUNG ONE's excited squeak as they go "
                          "under, then silence underwater",
         crit="no dialogue, no camera tilt, no dutch angle, no movement right to left, no rider left behind",
         review=["Left to right, parallel, level.", "Surface to underwater in one move.",
                 "Each rider doing their own action."],
         end="Underwater, heading right."),
    dict(prefix="n", n=3, slug="the-glass-sea-wide", title="THE GLASS SEA, WIDE", s=10, grade="TURNING",
         series="cut 4 (CEO 2026-09-25: every rider acts; the child says wow underwater, bubbles from the mouth)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. An extreme wide shot on a wide lens, a slow lateral track from left to "
              "right keeping pace with THE MOUNT; no cut, no zoom.",
         refs=["@Manta", "@Young", "@Strong", "@Elder", "@GlassSpiral", "@GlassCathedral", "@GlassHalo", "@GlassBloom"],
         heading="THE GLASS SEA, LATE IN THE DAY. THE THREE RIDERS cross a vast underwater space, tiny, among giant glass "
                 "creatures.",
         frame="Extreme wide: THE MOUNT small in the middle band moving from left to right; below them the sea falls "
               "away into deep blue then indigo; the glass creatures drift at different depths.",
         particles="countless drifting plankton specks, small bubbles, long shafts of dimming violet-grey light from the "
                   "surface.",
         actions=["THE STRONG ONE, front perch: steers THE MOUNT in a slow curve around THE SPIRAL, then turns and points "
                  "out THE BLOOM to the child.",
                  "THE YOUNG ONE, middle: follows the pointing arm, gasps and stretches one hand toward THE BLOOM as it "
                  "passes; bubbles pour from the child's mouth.",
                  "THE ELDER, back: turns his head slowly to follow THE DOME drifting overhead, then looks down at the "
                  "child and smiles."],
         beats=["[0s] Wide and deep: THE MOUNT glides in from the left carrying THE THREE RIDERS, small in the vastness; "
                "THE STRONG ONE steers it in a slow curve around THE SPIRAL.",
                "[3s] Around them and far below, THE SPIRAL, THE DOME, THE RINGS and THE BLOOM drift, each bigger than a "
                "house, rainbow light moving through their clear bodies. THE STRONG ONE points at THE BLOOM; THE ELDER "
                "turns his head to follow THE DOME.",
                "[6s] THE YOUNG ONE stretches a hand toward THE BLOOM, mouth open; a burst of bubbles pours out. Amazed, "
                "underwater: \"Wowww.\" THE ELDER smiles at the child.",
                "[8.5s] THE MOUNT keeps on toward the right of frame, the deep blue opening beneath them."],
         audio="-",
         sound="THE YOUNG ONE's muffled, bubbling underwater \"Wowww\", sounding truly underwater, and nothing else",
         crit=DIALOGUE_NEG + ", no jellyfish, no squid, no octopus, no fish, no movement right to left, no bright noon "
              "light underwater",
         review=["Bubbles from the child's mouth with the Wowww.", "Left to right, wide.",
                 "Each rider doing their own action."],
         end="THE MOUNT heading right."),
    dict(prefix="n", n=4, slug="the-line-they-stop", title="THE LINE: THEY STOP", s=7, grade="TURNING",
         series="cut 5 (CEO 2026-09-25: the near side is the Turning with the storm pillars on the left, not clear "
                "water; left to right, stopping exactly at the line; the talk is N12)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A wide side-on tracking shot moving with THE MOUNT from the left of frame "
              "to the right, then holding as it stops; no cut, no zoom.",
         refs=["@Pillars", "@Turning", "@BlackSea", "@Manta", "@Strong", "@Young", "@Elder"],
         ref_override={"@Pillars": "THE PILLARS: the storm pillars standing on the violet-grey sea on the left side of "
                                   "the frame, behind THE MOUNT; take the pillars and their light.",
                       "@Turning": "THE TURNING LIGHT, a colour and light reference only: the left half of the frame, "
                                   "deep indigo water under a violet-grey bruised evening sky; nothing of its "
                                   "composition.",
                       "@BlackSea": "THE BLACK SEA: the right half of the frame only, pitch-black water under a "
                                    "purple-black storm."},
         heading="THE LINE, AT EVENING. Out of the storm pillars THE MOUNT arrives from the left and stops exactly at "
                 "the edge of the black water.",
         frame="Wide, side on: the left half of the frame is the turning, deep indigo water under a violet-grey bruised "
               "evening sky, the tall storm pillars standing on the sea behind; the right half is pitch-black water "
               "under a churning purple-black storm; between them a razor-sharp straight line runs away from the camera "
               "to the horizon. The seat order is THE STRONG ONE on the front perch, THE YOUNG ONE in the middle, THE "
               "ELDER at the back.",
         particles="spray off the wing tips, wind-blown mist along the line, whirlpool mist drifting from the pillars.",
         actions=["THE STRONG ONE, front perch: steers in from the left in long pole strokes, sees the black water ahead, "
                  "hauls back on the steering pole with his whole weight to stop, and holds THE MOUNT there, braced.",
                  "THE YOUNG ONE, middle: kneels up to see past THE STRONG ONE, grips the edge of the seat with both hands "
                  "as they slow, then leans forward, staring at the black water with round eyes.",
                  "THE ELDER, back: reaches forward and rests one hand on THE STRONG ONE's shoulder as they stop, his gill "
                  "frills lifting in the storm wind."],
         beats=["[0s] THE MOUNT glides in from the left of frame over the deep indigo water, the storm pillars behind it, "
                "THE STRONG ONE working the steering pole in long strokes.",
                "[2.5s] Ahead, the pitch-black water; THE STRONG ONE hauls back hard on the pole; THE MOUNT slows, water "
                "piling up at its wing edges; THE YOUNG ONE grips the edge of the seat with both hands.",
                "[4.5s] THE MOUNT stops exactly at the line, its nose at the edge of the black water; THE ELDER rests a "
                "hand on THE STRONG ONE's shoulder; THE YOUNG ONE leans forward, staring; thunder rolls beyond the line."],
         audio="-", sound="THE STRONG ONE's grunt as he hauls on the pole and THE YOUNG ONE's sharp breath at the "
                          "thunder; no words",
         crit=NO_WORDS + ", no crossing, no part of THE MOUNT over the line, no movement right to left, no mount facing "
              "the camera, no blurred line, no gradient between the waters, no turquoise water, no bright daylight, no "
              "rain on the near side",
         review=["Left half the turning with the pillars; right half black.", "Left to right; stops exactly at the line.",
                 "Each rider doing their own action."],
         end="Stopped with its nose at the line, facing right, toward the black water; the pillars behind."),
    dict(prefix="n", n=5, slug="the-crossing", title="THE CROSSING", s=6, grade="DARK",
         series="cut 5 (CEO 2026-09-25: they cross from the turning, not clear water; EVERY light flickers and dies; "
                "darkness)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. From behind THE MOUNT, moving with it as it crosses away from the camera; "
              "no cut, no zoom.",
         refs=["@Manta", "@Lantern", "@LanternDark", "@BlackSea", "@Strong", "@Elder", "@Young", "@Turning"],
         ref_override={"@Turning": "THE TURNING LIGHT, a colour reference only: the deep indigo water under THE MOUNT "
                                   "before the line; nothing of its composition."},
         heading="THE CROSSING. THE MOUNT slips over the line into the black water, and every light they carry dies.",
         frame="Behind THE MOUNT: THE THREE RIDERS with their backs to us; THE LANTERN hangs lit from the seat and the "
               "small seed-pod lamps glow along the seat; under them the deep indigo water of the turning; ahead, beyond "
               "the razor-sharp line, pitch-black water under the storm.",
         particles="rain beginning to fall as they cross, drops streaking through the last of the lamp light.",
         actions=["THE STRONG ONE, front perch: drives the steering pole down and pushes THE MOUNT over the line, then "
                  "keeps steering through the dark, never stopping.",
                  "THE YOUNG ONE, middle: looks up in alarm at the flickering lantern and reaches toward it, then huddles "
                  "against THE ELDER when the last light dies.",
                  "THE ELDER, back: cups one hand around the nearest seed-pod lamp as if to shield it; when it dies he "
                  "wraps both arms around the child."],
         beats=["[0s] THE STRONG ONE drives the steering pole down and THE MOUNT glides forward from the deep indigo water "
                "over the razor-sharp line, away from us, into the pitch-black water; rain falls on them.",
                "[2s] THE LANTERN and every seed-pod lamp on the seat flicker hard, stutter, flicker again; THE YOUNG ONE "
                "looks up in alarm and reaches toward THE LANTERN; THE ELDER cups a hand around the nearest lamp.",
                "[3.5s] One by one they all go out. THE LANTERN is dead and dark. Every light is gone. THE YOUNG ONE "
                "huddles against THE ELDER, who wraps both arms around the child.",
                "[4.5s] Darkness: only faint grey outlines in the rain, THE STRONG ONE still steering."],
         audio="-", sound="the riders' sharp, frightened breaths as the lights die; no words",
         crit=NO_WORDS + ", no light left burning, no glow from the child yet, no one facing the camera, no fire, no "
              "flames, no explosion, no turquoise water",
         review=["All lights flicker and die, very clearly.", "Ends in darkness.", "Moving away from the camera.",
                 "Each rider doing their own action."],
         end="THE MOUNT in darkness just past the line; every light dead."),
    dict(prefix="n", n=6, grade_override="DARK_GLOW", slug="the-light", title="THE LIGHT", s=8, grade="DARK",
         series="cut 5 (CEO 2026-09-25: the light comes only from the child, a 2-metre circle that turns the water "
                "from black to the turning)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A three-quarter view from behind THE MOUNT, slowly rising; no cut, no zoom.",
         refs=["@Young", "@Turning", "@Strong", "@Elder"],
         ref_override={"@Turning": TURNING_IN_CIRCLE},
         heading="THE LIGHT. In the black rain, THE YOUNG ONE lights up, the only light they have.",
         frame="Behind and a little above THE MOUNT on pitch-black water in the rain; THE THREE RIDERS barely visible "
               "in the dark until the child's light comes.",
         particles="rain streaks falling through the light, warm golden motes rising from THE YOUNG ONE.",
         actions=["THE STRONG ONE, front perch: turns round on the perch toward the child and speaks; when the light "
                  "comes, grins with relief, turns forward and steers on.",
                  "THE YOUNG ONE, middle: looks from one to the other, nods, takes a deep breath, closes both eyes and "
                  "lights up.",
                  "THE ELDER, back: lays a hand on the child's back, encouraging; when the light blooms he leans back, "
                  "face lit gold, in awe."],
         beats=["[0s] Darkness and rain. THE STRONG ONE turns round on the perch toward THE YOUNG ONE. Quietly: \"We need "
                "your light now.\" THE ELDER lays a hand on the child's back.",
                "[3s] THE YOUNG ONE looks from one to the other, nods, takes a deep breath and closes both eyes; GLOW",
                "[5.5s] THE STRONG ONE grins with relief and turns forward to steer; THE ELDER leans back, face lit gold, "
                "in awe; THE MOUNT glides on into the dark, away from us, carrying its small moving circle of light."],
         audio="-", sound="the line above, spoken once, then THE YOUNG ONE's slow breath as the light blooms",
         crit=DIALOGUE_NEG + ", no words before or after the line, no light wider than 2 metres around the child, no "
              "beam into the sky, no other light source",
         review=["One line, THE STRONG ONE, nothing added; transcribe.", "The 2-metre circle; indigo water inside, black "
                 "outside.", "Each rider reacts to the line and to the light."],
         end="THE YOUNG ONE glowing, the moving circle of light, from here to the end."),
    dict(prefix="n", n=7, grade_override="DARK_GLOW", slug="the-giant-wave", title="THE GIANT WAVE", s=8, grade="DARK",
         series="cut 5 (CEO 2026-09-25: the wave throws them off THE MOUNT, not far, and the screen goes black; the wave "
                "picture dropped, its own glow broke the light rule)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. Low behind THE MOUNT, looking past it at the wave rising ahead; camera "
              "shake; it ends with the water over the lens; no cut, no zoom.",
         refs=["@Strong", "@Pole", "@Elder", "@Young", "@Turning"],
         ref_override={"@Turning": TURNING_IN_CIRCLE},
         heading="THE WAVE. Out of the dark ahead, a wall of black water as tall as a mountain rises over them.",
         frame="Low behind THE MOUNT, small in the lower frame with THE YOUNG ONE glowing on it; the wave rears up ahead "
               "and fills everything above, black, its face lit gold only where it comes inside the child's circle.",
         particles="heavy rain, spray torn off the wave, foam tumbling through the gold light.",
         actions=["THE STRONG ONE, front perch: drives THE POLE down, shouts, and is torn off the perch by the wave, still "
                  "gripping the pole.",
                  "THE YOUNG ONE, middle, glowing: stares up at the wave, throws both arms around the bone-rib backrest, "
                  "and is swept off with THE ELDER still holding on.",
                  "THE ELDER, back: wraps his arms around the child from behind and holds on as the wave sweeps them both "
                  "off."],
         beats=["[0s] GLOW Out of the dark ahead a colossal wave of black water rears up over THE MOUNT, its face lit gold "
                "only where it enters the circle, its top lost in the black above. THE YOUNG ONE stares up, mouth open.",
                "[2.5s] THE STRONG ONE drives THE POLE down. A shout: \"Hold on!\" THE YOUNG ONE throws both arms round "
                "the backrest; THE ELDER wraps his arms around the child.",
                "[4.5s] The wave crashes down on them: THE THREE RIDERS are torn off THE MOUNT and thrown into the water "
                "only a few metres away, the child's light tumbling with them.",
                "[6.5s] The water surges over the camera; the frame goes completely black."],
         audio="-", sound="the shout above, spoken once, the riders' gasps as the wave hits, then silence in the black",
         crit=DIALOGUE_NEG + ", no one facing the camera, no movement toward the camera, no light wider than 2 metres "
              "around the child, no other light source, no one thrown far away",
         review=["A colossal black wave, lit only inside the circle.", "One shout; transcribe.",
                 "All three knocked off into the water close by.", "Ends on a black screen."],
         end="Black screen."),
    dict(prefix="n", n=8, grade_override="DARK_GLOW", slug="the-school", title="THE SCHOOL", s=8, grade="DARK",
         series="cut 4 (CEO 2026-09-25: every rider acts; excitement at the school; the mount stops)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. Side on at the surface, moving left to right with THE MOUNT, then "
              "settling as it stops; no cut, no zoom.",
         refs=["@Strong", "@Young", "@Elder", "@Turning"],
         heading="FISH. At the surface, inside the child's small light, the water under them is suddenly full of fish.",
         frame="Side on at the surface: THE MOUNT moving left to right, THE YOUNG ONE glowing on the seat; the lit "
               "circle of water around them is the only thing visible; beyond it, black.",
         particles="rain dimpling the flat surface, the glint of fish passing just below it.",
         actions=["THE YOUNG ONE, middle, glowing: spots the fish first, gasps, bounces on the seat and points down with "
                  "both hands.",
                  "THE STRONG ONE, front perch: leans over the edge to look, sees them, laughs out loud and slaps his "
                  "thigh, then raises a hand to slow THE MOUNT.",
                  "THE ELDER, back: leans out beside the child, eyes wide, then grips the child's shoulder and laughs, "
                  "shaking his head in disbelief."],
         beats=["[0s] GLOW THE MOUNT glides from left to right on water that is growing flat and calm in the rain.",
                "[2s] In the lit circle below the surface, many small dark fish shadows dart past, dozens of them; THE "
                "YOUNG ONE gasps, bounces on the seat and points down with both hands.",
                "[4s] THE STRONG ONE and THE ELDER lean over the edge; THE STRONG ONE laughs out loud and slaps his "
                "thigh; THE ELDER grips the child's shoulder, laughing.",
                "[6s] THE STRONG ONE raises a hand; THE MOUNT slows and stops on the flat water; THE STRONG ONE winks at the "
                "child; THE YOUNG ONE giggles and hugs THE ELDER's arm; THE ELDER shakes his head, smiling."],
         audio="-", sound="the riders' excited gasps, THE STRONG ONE's big laugh and THE ELDER's soft laugh, nothing else",
         crit="no dialogue, no colourful fish, no big fish, no underwater camera, no waves, no light wider than two "
              "metres, no lamps lit on the seat",
         review=["Surface only; fish as small dark shadows in the lit circle.", "Each rider reacts: point, laugh, grip.",
                 "Left to right, then the mount stops."],
         end="THE MOUNT stopped on flat water among the fish."),
    dict(prefix="n", n=9, grade_override="DARK_GLOW", slug="one-fish", title="ONE FISH", s=8, grade="DARK",
         series="cut 5 (CEO 2026-09-25: plays straight after the waking; no net, a quick chase and a grab by hand; "
                "everyone cheers; the light only from the child)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A medium shot beside THE MOUNT at the surface; no cut, no zoom.",
         refs=["@Strong", "@Young", "@Elder", "@Turning"],
         ref_override={"@Turning": TURNING_IN_CIRCLE},
         heading="ONE FISH, CAUGHT BY HAND.",
         frame="Medium, beside THE MOUNT at the surface: THE STRONG ONE leaning over the edge of the seat, THE YOUNG ONE "
               "glowing beside him, THE ELDER behind.",
         particles="rain, water splashing up as the hands go in, golden motes around THE YOUNG ONE.",
         actions=["THE STRONG ONE, front perch: leans far over the edge, chases a fish shadow with both hands, lunges and "
                  "snatches it out, then holds it up, laughing.",
                  "THE YOUNG ONE, middle, glowing: leans out beside THE STRONG ONE, holding the light low over the water so "
                  "THE STRONG ONE can see, pointing where the fish goes; at the catch, jumps up and down on the seat, "
                  "cheering.",
                  "THE ELDER, back: grips THE STRONG ONE's kelp belt with both hands so THE STRONG ONE cannot fall in; at "
                  "the catch, claps THE STRONG ONE on the back and cheers."],
         beats=["[0s] GLOW THE STRONG ONE leans far over the edge, eyes on a fish shadow darting along the side; THE ELDER "
                "grabs THE STRONG ONE's kelp belt with both hands; THE YOUNG ONE leans out beside THE STRONG ONE and "
                "points.",
                "[2s] Quick: THE STRONG ONE's hands chase it through the water, once, twice; THE YOUNG ONE points again, "
                "urgent.",
                "[4s] THE STRONG ONE lunges and snatches it out: one dark glossy silver-black fish, flapping in his hands.",
                "[5.5s] They cheer, each in their own way: THE YOUNG ONE jumps up and down on the seat; THE ELDER claps "
                "THE STRONG ONE on the back; THE STRONG ONE holds the fish up, laughing."],
         audio="-", sound="splashes of the hands, THE STRONG ONE's effort, then wordless cheering and laughter",
         crit=NO_WORDS + ", no net, no spear, no hook, no second fish, no one falling in, no other light source, no light "
              "wider than 2 metres around the child",
         review=["Caught by hand, no net.", "No words, only cheering.", "Only the child's light; indigo water inside."],
         end="THE STRONG ONE holding one fish, all three happy."),
    dict(prefix="n", n=10, grade_override="DARK_GLOW", slug="the-shadow", title="THE SHADOW", s=8, grade="DARK",
         series="cut 5 (CEO 2026-09-25: the tiny speck is the child's 2-metre circle, the only light; the mount picture "
                "dropped, its lamps are lit)",
         spec="ONE LOCKED SHOT, NO CUTS. Straight down from very high above; the camera never moves.",
         refs=["@Young", "@Turning"],
         ref_override={"@Turning": TURNING_IN_CIRCLE},
         heading="THE SHADOW. From very high: the mount is a tiny speck of light, and something enormous passes beneath.",
         frame="Top-down from very high: THE MOUNT a tiny speck with its tiny circle of light in the centre of a vast "
               "black sea; the sea surface flat and calm under the rain.",
         particles="rain falling toward the flat water, a faint shimmer across the surface.",
         beats=["[0s] GLOW Seen from very high, THE MOUNT is a tiny glowing speck on a flat black sea in the rain.",
                "[2s] Beneath it, deep down, an enormous dark shadow slides slowly past, hundreds of times bigger than THE "
                "MOUNT, covering most of the frame, its edges lost in the dark.",
                "[4s] The tiny fish shadows around the speck of light scatter in every direction and vanish.",
                "[6s] The shadow is gone. The flat sea is empty. Only the tiny speck of light remains."],
         audio="-", sound="the faintest startled gasp; no words",
         crit=NO_WORDS + ", no camera move, no creature shape, no eye, no fin, no surfacing, no waves, only a shadow, no "
              "other light source",
         review=["Top-down from very high; the speck is the child's circle.", "A shadow only, enormous.",
                 "The fish vanish."],
         end="Flat black sea, rain, THE MOUNT alone."),
    dict(prefix="n", n=11, grade_override="DARK_GLOW", slug="the-mountain-rises", title="THE MOUNTAIN RISES", s=14, grade="DARK",
         series="cut 5 (CEO 2026-09-25: busy fishing; one sees it and stares; another notices and shakes the one still "
                "fishing; TWO eyes open; the light only from the child)",
         spec="ONE LOCKED SHOT, NO CUTS. A wide shot from behind and above THE MOUNT; the camera never moves.",
         refs=["@Mountain", "@Eye", "@Strong", "@Young", "@Elder", "@Turning"],
         ref_override={"@Turning": TURNING_IN_CIRCLE,
                       "@Eye": "THE CREATURE, the only picture of it: take its broad flat smooth dark head, its two "
                               "enormous pale yellow-green eyes with thin vertical slit pupils and its scale exactly; "
                               "nothing of the light around it."},
         light_extra="Far beyond the circle the rising mountain is only a vast blacker shape against the dark; its two "
                     "eyes, when they open, glow pale yellow-green on their own, the only other light in this shot.",
         heading="THE MOUNTAIN RISES. Ahead of them, where no land can be, a mountain comes up out of the flat sea while "
                 "they are busy fishing.",
         frame="Wide from behind and above: THE MOUNT small in the lower third on flat black water in the rain, lit only "
               "by THE YOUNG ONE; the far black water ahead of it fills the upper frame.",
         particles="rain, a thin mist over the flat water, water pouring off the rising shape.",
         actions=["THE STRONG ONE, front perch: lies on his belly across the front of the seat with both arms in the water "
                  "to the elbows, grabbing at the fish in the lit circle, completely absorbed and splashing; he only "
                  "looks up when THE YOUNG ONE shakes his shoulder, and his hands stop in the water.",
                  "THE YOUNG ONE, middle, glowing: sits on the edge and kicks both feet in the water to herd the fish "
                  "toward THE STRONG ONE, giggling; notices THE ELDER staring for a long time, follows THE ELDER's gaze, goes "
                  "still, then shakes THE STRONG ONE's shoulder hard.",
                  "THE ELDER, back: rinses their one fish over the side, then stops, slowly lifts his head and stares "
                  "ahead at the far water, the fish forgotten in his hands."],
         beats=["[0s] GLOW On the flat black water THE THREE RIDERS are busy fishing: THE STRONG ONE lies across the front "
                "of the seat grabbing at fish with both arms in the water; THE YOUNG ONE kicks both feet in the water, "
                "giggling; THE ELDER rinses their one fish over the side.",
                "[3s] Far ahead the flat water bulges; a vast smooth dark shape slowly rises out of the sea like a "
                "mountain until it fills the whole upper half of the frame, water pouring off it. THE ELDER stops, lifts "
                "his head and stares at it; the other two keep fishing.",
                "[7s] THE YOUNG ONE notices THE ELDER staring for a long time, follows THE ELDER's gaze, goes still, then shakes "
                "THE STRONG ONE's shoulder hard; THE STRONG ONE, still splashing, looks up.",
                "[10s] High on the dark mountain, two enormous eyes open: pale yellow-green, thin vertical slit pupils, "
                "each bigger than their whole village, looking down at them. THE STRONG ONE's hands stop in the water."],
         # Wan 3.0 caps the Direction box at 3,500 characters: the same four beats, fewer words (wan3_prompt.py).
         wan3_beats=["[0s] GLOW All three are busy fishing: THE STRONG ONE lies across the front grabbing at fish with "
                     "both arms in the water; THE YOUNG ONE kicks both feet in the water, giggling; THE ELDER rinses "
                     "their one fish.",
                     "[3s] Far ahead the flat sea bulges and a vast dark shape rises like a mountain until it fills the "
                     "upper half of the frame. THE ELDER stops and stares at it; the other two keep fishing.",
                     "[7s] THE YOUNG ONE notices THE ELDER staring, follows the gaze, goes still, then shakes THE STRONG "
                     "ONE's shoulder; THE STRONG ONE looks up.",
                     "[10s] High on the mountain two enormous pale yellow-green eyes with thin slit pupils open, each "
                     "bigger than their village, looking down at them. THE STRONG ONE's hands stop in the water."],
         audio="-", sound="splashing hands and feet and THE YOUNG ONE's giggle, then THE YOUNG ONE's sharp gasp, then "
                          "total silence as the eyes open; no words",
         crit=NO_WORDS + ", no roar, no teeth, no third eye, no camera move, no waves, no light wider than 2 metres "
              "around the child, no eyes before the last beat",
         review=["Busy fishing, each in a different way.", "THE ELDER sees it first and stares; the child notices and "
                 "shakes THE STRONG ONE.", "Two eyes open only at the end; the child the only other light."],
         end="Both eyes open, all three looking up at them; cut to space (M13, take 1)."),
    dict(prefix="n", n=12, slug="the-elder-speaks", title="AT THE LINE: THE ELDER SPEAKS", s=8, grade="TURNING",
         series="cut 5 (CEO 2026-09-25: behind them the turning and the storm pillars, not clear water; plays after N4)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A medium three-shot from the front and a little to the side, low over the "
              "black water, looking back at THE THREE RIDERS on the seat; a slow push-in; no cut.",
         refs=["@Manta", "@Elder", "@Strong", "@Young", "@Turning", "@Pillars"],
         ref_override={"@Pillars": "THE PILLARS: the storm pillars standing on the violet-grey sea far behind THE THREE "
                                   "RIDERS; take the pillars and their light."},
         heading="AT THE LINE. Before they cross, THE ELDER says what everyone is thinking, and they decide.",
         frame="Medium three-shot from the front: THE THREE RIDERS on the seat, THE STRONG ONE on the front perch turned "
               "half round toward the others, THE YOUNG ONE in the middle, THE ELDER at the back; their faces in cool "
               "violet-grey evening light with the flicker of far lightning; behind them, the deep indigo water of the "
               "turning and the tall storm pillars they came through.",
         particles="wind-blown mist, spray drifting across, the first cold drops in the air.",
         actions=["THE ELDER, back: looks past the camera at the black water, then rises slowly on the back seat and "
                  "speaks, low; afterwards he looks each of the others in the eye.",
                  "THE STRONG ONE, front perch: listens with his jaw tight, meets THE ELDER's eyes, then looks at the "
                  "child, nods once and turns to grip the steering pole, ready.",
                  "THE YOUNG ONE, middle: looks up at THE ELDER while THE ELDER speaks and swallows; then takes a breath "
                  "and nods, small and brave, both hands tight on the satchel strap."],
         beats=["[0s] THE ELDER looks past the camera at the black water, then rises slowly on the back seat. Low: \"So "
                "this is it. The line of death.\"",
                "[3.5s] THE STRONG ONE meets THE ELDER's eyes, jaw tight; THE YOUNG ONE looks up at THE ELDER and "
                "swallows, both hands tight on the satchel strap.",
                "[5.5s] THE ELDER looks each of them in the eye; THE YOUNG ONE takes a breath and nods, small and brave; "
                "THE STRONG ONE nods once and turns to grip the steering pole. Lightning flickers on their faces."],
         audio="-", sound="the line above, spoken once, and THE YOUNG ONE's small nervous breath",
         crit=DIALOGUE_NEG + ", no words before or after the line, no second line spoken, no line spoken twice, no "
              "crossing yet, no rain yet, no smiling, no turquoise water, no bright daylight",
         review=["One line, THE ELDER, once, nothing added; transcribe.", "The turning and the pillars behind them.",
                 "Eye contact, then the two nods: the decision to cross."],
         end="Ready to cross; THE STRONG ONE's hands on the pole."),
    dict(prefix="n", n=13, grade_override="DARK_GLOW", slug="the-waking", title="THE WAKING", s=10, grade="DARK",
         series="cut 5, new (CEO 2026-09-25: after the black screen they lie on THE MOUNT's back as if saved from "
                "drowning; fish come; the child wakes first, sees them and wakes the others; plays after N7)",
         spec="ONE CONTINUOUS TAKE, NO CUTS. A high angle looking down on THE MOUNT, slowly lowering to a medium shot; "
              "no cut, no zoom.",
         refs=["@Strong", "@Young", "@Elder", "@Turning"],
         ref_override={"@Turning": TURNING_IN_CIRCLE},
         heading="AFTER THE WAVE. The storm has passed; THE THREE RIDERS lie on the back of THE MOUNT like survivors "
                 "pulled from the sea.",
         frame="High angle, looking down on THE MOUNT floating on flat black water in light rain: THE THREE RIDERS "
               "sprawled across its back and the seat, soaked, eyes closed; the child's light faint at first.",
         particles="light rain dimpling the flat water, water trickling off their bodies, golden motes once the child "
                   "wakes.",
         actions=["THE YOUNG ONE, middle: lies curled on the seat, the glow faint and flickering; the first to stir: "
                  "coughs up water, opens both eyes, sees the fish, and the glow swells back to the full circle; "
                  "scrambles over and shakes the other two awake.",
                  "THE STRONG ONE, front: lies face down across the front of THE MOUNT, one arm hanging in the water; "
                  "when shaken he coughs, rolls over and pushes himself up on one elbow, blinking.",
                  "THE ELDER, back: lies on his back beside the seat, chest rising slowly; when the child shakes his "
                  "shoulder he coughs, lifts his head and sees the child pointing at the water."],
         beats=["[0s] Flat black water, light rain. THE THREE RIDERS lie sprawled on the back of THE MOUNT, soaked, "
                "breathing slowly; THE YOUNG ONE's glow is faint and flickering.",
                "[2.5s] Beneath the surface, small dark fish shadows slide in toward the faint light. THE YOUNG ONE coughs "
                "up water and opens both eyes.",
                "[4.5s] THE YOUNG ONE sees the fish and the glow swells: GLOW THE YOUNG ONE scrambles over and shakes "
                "THE STRONG ONE and THE ELDER. Urgent, hoarse: \"Wake up... look!\"",
                "[7.5s] THE STRONG ONE coughs, rolls over and pushes up on one elbow; THE ELDER lifts his head; both see "
                "the fish darting through the lit water around them."],
         audio="-", sound="coughing and ragged breaths, the line above, spoken once, then THE STRONG ONE's surprised "
                          "gasp",
         crit=DIALOGUE_NEG + ", no second line, no one in the water, no storm, no waves, no other light source, no light "
              "wider than 2 metres around the child",
         review=["They lie on THE MOUNT's back, not in the water.", "The child wakes first, the glow swells, one line; "
                 "transcribe.", "Fish shadows in the lit circle."],
         end="All three awake on THE MOUNT, fish all around them in the light."),
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
    "@RunnerY": ["mustard-yellow", "chocolate-brown", "kelp rope"],
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


DEAD_LAMPS = ("Every seed-pod lamp on the seat and THE LANTERN are dead and dark; the only light anywhere is "
              "THE YOUNG ONE.")
WET = "Their skin, the seat and the back of THE MOUNT are wet and glistening with rain."
# Cut 3 (2026-09-25): the @Manta picture has its lamps lit, and the picture beat "dead and dark" in N6-N11. A dark
# picture (round 12) failed to generate twice, so after the crossing THE MOUNT is described in words, with no picture.
# Cut 4: naming the dead lamps still drew a lit lantern on the seat in N8/N9, so the words name no lamp at all now
# (CTO_Film_PromptFormat rule 6: never describe what must not be seen).
MOUNT_DARK = ("THE MOUNT, described here because no picture of it is attached after the crossing: a manta-like sea "
              "creature about 4 m across the wings, a sea-green mottled back, a long thin whip tail, a hand-built seat of "
              "weathered driftwood lashed with kelp rope, pale bone ribs for a backrest, seashells tied along it; nothing "
              "on THE MOUNT gives off any light.")
STATE = {("m", 6): "THE MOUNT and THE THREE RIDERS stream with water from the dive, skin wet and glistening.",
         ("n", 5): WET, **{("n", k): MOUNT_DARK + " " + WET for k in (6, 7, 8, 9, 10, 11, 13)}}
# CEO 2026-09-25 (cut 4): "แสงนั้นมาจากเด็กเพียงอย่างเดียวเท่านั้น ... เป็นวงรัศมีเท่าไหร่ ที่ทำให้น้ำรอบๆ เปลี่ยนจาก Dark เป็น
# Turning ... บางฉากลืมใส่ส่วนนี้ไป". Every shot in the dark after the child lights up carries THE LIGHT, word for word.
LIGHT = ("Once THE YOUNG ONE is glowing, the only light in the whole frame comes from the child: a warm golden glow "
         "from the child's whole body, gill frills blazing gold. It lights a circle exactly 2 metres in radius around "
         "the child and nothing beyond it. Inside the circle the black water turns to the deep indigo water of the "
         "turning, and the riders and THE MOUNT are lit gold; outside the circle everything is pitch black. Nothing else "
         "in the frame gives off light.")
DARK_LIT = {("n", k) for k in (6, 7, 8, 9, 10, 11, 13)}
# CEO 2026-09-25 (cut 3): "ตัวละคร 3 ตัวไม่มีสิ่งที่เขากระทำเลย ทุกตัวอยู่นิ่งหมดเลย" and "ห้ามเหมือนกันทุกคน มันจะดูปลอม".
# Every shot with the three riders on THE MOUNT carries one action line per rider, and no line that freezes them.
ON_MOUNT = {("m", 4), ("m", 6), ("o", 4), ("n", 2), ("n", 3), ("n", 4), ("n", 5), ("n", 6), ("n", 7), ("n", 8),
            ("n", 9), ("n", 11), ("n", 12), ("n", 13)}
RIDERS = ("THE STRONG ONE", "THE YOUNG ONE", "THE ELDER")
STATIC = ("nobody moves", "without moving", "stand still", "stands still", "sit still", "sits still", "motionless",
          "stare at it without", "the three look at each other")
HOUSE_NEG_MOUNTAIN = HOUSE_NEG.replace("no land, no island, no beach, no rocks above the water; ", "no beach, no shore; ")


GLOW = ("THE YOUNG ONE glows warm gold from the whole body, lighting the circle of water 2 metres around the child, "
        "indigo inside, pitch black outside.")


def tag(sc):
    return f"{sc.get('prefix', 'm').upper()}{sc['n']}"


def paste_block(sc):
    lines = [f"{sc['s']}s · 360p · 16:9 · {sc['spec']}", "", sc["heading"], "", "REFERENCES, each with a job:"]
    for h in sc["refs"]:
        lines.append(f"{h}: {sc.get('ref_override', {}).get(h, REF[h][1])}")
    sc = dict(sc, beats=[b.replace("GLOW", GLOW) for b in sc["beats"]])
    lines += ["", "THE FRAME: " + sc["frame"]]
    if STATE.get((sc.get("prefix", "m"), sc["n"])):
        lines += ["", "STATE: " + STATE[(sc.get("prefix", "m"), sc["n"])]]
    if (sc.get("prefix", "m"), sc["n"]) in DARK_LIT:
        lines += ["", "THE LIGHT: " + LIGHT + (" " + sc["light_extra"] if sc.get("light_extra") else "")]
    if sc.get("particles"):
        lines += ["", "PARTICLES: " + sc["particles"]]
    if sc.get("actions"):
        lines += ["", "EACH CHARACTER, ALL THROUGH THE SHOT (each busy with their own action, never all the same, "
                      "reacting to what is said and done):"]
        lines += ["- " + a for a in sc["actions"]]
    lines += ["", "WHAT HAPPENS:"]
    lines += sc["beats"]
    snd = sc.get("sound") or SOUND.get((sc.get("prefix", "m"), sc["n"]), "silence; nobody speaks")
    lines += ["", "overall_soundscape: only the sounds the characters themselves make (voices, breathing, effort, the touch "
              "and splash of their own hands and bodies): " + snd +
              ". No ambient bed: no wind, no water, no rain, no birds, no crowd murmur, no room tone.",
              "non_diegetic_music: none.", "", GRADE[sc.get("grade_override", sc["grade"])], "",
              "CRITICAL NEGATIVES: " + sc["crit"] + ".", "",
              HOUSE_NEG_MOUNTAIN if (sc.get("prefix", "m"), sc["n"]) in (("n", 11), ("m", 11)) else HOUSE_NEG]
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
        if (sc.get("prefix", "m"), sc["n"]) in ON_MOUNT:
            acts = sc.get("actions") or []
            for r in RIDERS:
                assert sum(a.startswith(r) for a in acts) == 1, (tag(sc), "needs one action line for", r)
            assert len(set(acts)) == len(acts), (tag(sc), "two riders given the same action")
            bad = [w for w in STATIC if w in body.lower()]
            assert not bad, (tag(sc), "a line freezes the riders", bad)
        if (sc.get("prefix", "m"), sc["n"]) in DARK_LIT - {("n", 8)}:
            other = [w for w in ("lamp", "lantern", "lightning", "moon") if w in body.lower()]
            assert not other, (tag(sc), "the child is the only light: a word invites another source", other)
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
