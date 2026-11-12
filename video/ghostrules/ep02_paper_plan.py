#!/usr/bin/env python3
"""Ghost Rules EP2 paper-style M1 plan: scene list + mover/reason plan + validator.

M1 only: no render, no paid API. Reads words/cNN.json (ASR, Thai, one token per
character group) from the EP2 work folder, snaps every scene boundary to a pause
between words, and writes ep02_paper_plan.json + ep02_paper_plan.md.

    python3 video/ghostrules/ep02_paper_plan.py [out_dir]

Exit 1 when a CEO rule check fails. The checks are the 8 rules in
state/ph-briefs/project_head-f85ae4fe.md (rules 3, 6-cover, 8-cover are later milestones).
"""
import json, glob, os, re, sys, math

WORDS = "/opt/MoonieXHQ/Work/ghostrules-full/ep02/words"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/opt/MoonieXHQ/Work/ghostrules-full/ep02/paper"

# ---------------------------------------------------------------- global timing
INTRO = 1.4           # silent opening beat, as EP1 (plan_ep01.json intro f0..f1 = 42 frames)
GAP = 1.5             # animated chapter bumper before these takes (EP1 used 1.5 s beats)
TAIL = 1.0            # EP1: take length = last word end + ~1.1 s (c01 23.26 s words, 24.33 s take)
BUMPERS = {           # take -> story clock the bumper animates to (spoken in the take)
    "c04": "01:15", "c09": "02:25", "c12": "03:00", "c14": "03:35",
    "c18": "03:45", "c21": "04:30"}

# ---------------------------------------------------------------- movers
# kind must be a thing that really moves (CEO rule 5). Houses and big structures never appear here
# unless kind == story_event (the story itself breaks or shakes them).
KINDS = {"cloud", "lamp", "person", "tree", "grass", "smoke", "curtain", "water", "rain",
         "screen", "insect", "cloth", "vehicle", "hand_object", "story_event"}


def M(kind, name, reason):
    return dict(kind=kind, name=name, reason=reason)


TUBE = M("lamp", "tube light flicker", "faulty ballast, the light dips and buzzes as the story says it flickers")
TUBE_T = M("lamp", "teal tube light flicker", "same fluorescent tube after it turned cold teal, still unstable")
MON = M("screen", "CCTV monitor static", "a CCTV monitor is a live screen, it rolls and crackles")
REC = M("lamp", "red REC lamp blink", "recording lamp on the monitor blinks once a second")
MOTH = M("insect", "moth circling the light", "moths really circle a bright tube at night")
CLOUD = M("cloud", "clouds drift", "night clouds move with the wind over the road")
GRASS = M("grass", "roadside grass sway", "open field grass moves in the night wind")
DRIP = lambda what: M("water", what, "canal water runs off wet cloth and skin, drops fall under gravity")
SRC = "source: ASR of the take (words/cNN.json); wording is garbled, scene meaning is the CMO-readable story below"

# ---------------------------------------------------------------- scenes
# (chunk, a, b, name, io, rain, grade, light, plate, [movers], [sfx], story-note)
# a,b are requested chunk-local seconds; the generator snaps them to the nearest pause.
# io    = camera position: indoor (under a roof) or outdoor (open sky)
# rain  = visual rain: none | outdoor. Never "outdoor" on an indoor scene (rule 2).
# grade = N normal, FB flashback (desaturated sepia, cold shadow), CCTV (mono green-grey monitor look),
#         D dawn (warm, after the storm). Light state: warm | teal | dark | dawn | day | night-open.
S = []


def sc(chunk, a, b, name, io, rain, grade, light, plate, movers, sfx=(), note=""):
    S.append(dict(chunk=chunk, a=a, b=b, name=name, io=io, rain=rain, grade=grade, light=light,
                  plate=plate, movers=movers, sfx=list(sfx), note=note))


sc("intro", 0, INTRO, "empty old highway", "outdoor", "none", "N", "night-open",
   "very wide empty two lane old highway at night, one tiny lit store far away, canal edge and dark field, paper moon NOT red",
   [CLOUD, GRASS, M("insect", "moths near the far store lamp", "moths gather at the only light")],
   [(0.0, "night insects bed in", "ambient, nothing named; fades in under the first word")],
   "Opening beat. Dry: the story rain starts at 01:15.")

# c01 hook (general narration, no character yet)
sc("c01", 0, 12.8, "lonely store, hiring board", "outdoor", "none", "N", "night-open",
   "front of a lonely roadside convenience store at night from the car park, blank hiring board leaning on the window (scribble lines, no letters), canal behind",
   [M("insect", "moths at the canopy lamp", "moths circle the lamp above the entrance"),
    GRASS, CLOUD,
    M("lamp", "canopy lamp flicker", "a cheap canopy lamp buzzes and dips")],
   [], "'always posting hiring night staff, 3x pay, midnight to 6'")
sc("c01", 12.8, 23.1, "empty store, clock", "indoor", "none", "N", "warm",
   "inside the shop, empty bright aisle between snack shelves, round wall clock above the counter, nobody anywhere",
   [M("hand_object", "clock second hand", "a wall clock second hand ticks"), TUBE, MOTH],
   [(12.8, "clock tick bed", "story is about the long empty night; tick runs under the line")],
   "'no customer ever walks in'")
sc("c01", 23.1, 38.6, "counter and monitor", "indoor", "none", "N", "warm",
   "cash counter with register, small CCTV monitor and a dark back-room door ajar behind it, pen and blank notepad on the counter",
   [MON, REC, TUBE],
   [(23.1, "back-room door creak", "the 7 iron rules are 'behind the store': a door that is slightly open")],
   "'the pay is for the 7 rules, not for ringing up people'")

# c02 fact intro + backstory (flashback FB1)
sc("c02", 0, 7.6, "canal road, store far", "outdoor", "none", "N", "night-open",
   "narrow asphalt road between a deep irrigation canal and a black field, the store glowing alone far down the road, no house in view",
   [M("water", "canal surface ripple", "canal water moves slowly in the dark"), GRASS, CLOUD],
   [], "'store on the old irrigation canal road, no house within 2 km'")
sc("c02", 7.6, 15.4, "laid off at the gate", "outdoor", "none", "FB", "day",
   "FLASHBACK: factory gate in daylight, a young Thai man about 24 in a work shirt holding a cardboard box, a guard shed, seen from the road",
   [M("person", "young man walking away from the gate", "he leaves the job, a walking person"),
    CLOUD, M("tree", "roadside tree leaves", "leaves move in the daytime wind")],
   [(7.6, "FB sting: low tape-warble swell, 0.6 s", "marks the grade change so the flashback reads on the audio too")],
   "FLASHBACK: 'about 24, suddenly laid off'")
sc("c02", 15.4, 21.9, "mother's weekly visit", "indoor", "none", "FB", "day",
   "FLASHBACK: hospital ward by day, an older woman in a bed with a curtain, the young man sitting by the bed holding her hand",
   [M("curtain", "bed curtain sway", "ward curtain moves in the fan draft"),
    M("hand_object", "ward fan blades", "a ward fan turns"),
    DRIP("saline drip drops")],
   [(15.4, "ward ambience, soft monitor beep", "mother needs a hospital visit every week, said in the take")],
   "FLASHBACK: 'mother has to see the doctor every week'")
sc("c02", 21.9, 32.3, "walking to the store", "outdoor", "none", "N", "night-open",
   "the young man walking along the roadside from the near foreground toward the glowing store, canal on his left, dark field on his right, feet on the road with a long horizon",
   [M("person", "Non walking toward the store", "walker; scale shrinks with distance (perspective, feet on the road plane)"),
    GRASS, M("water", "canal ripple", "canal water moves"), CLOUD],
   [(21.9, "footsteps on asphalt, slow", "he walks to the job")],
   "back to the present. 'took the night job, 5,000 baht a night'")

# c03 the paper
sc("c03", 0, 8.4, "manager hands over the paper", "indoor", "none", "N", "warm",
   "inside the shop, a tired manager with dark under-eye shadows holds a sheet of paper out across the counter to the young man, register untouched between them",
   [M("hand_object", "paper passing across the counter", "the manager hands the sheet over"),
    TUBE, MOTH],
   [(2.0, "paper rustle", "the sheet changes hands")],
   "'did not teach the register, only handed a paper'")
sc("c03", 8.4, 20.1, "paper beside the monitor", "indoor", "none", "N", "warm",
   "close view of a paper sheet taped beside the CCTV monitor, red tape on its edges, rows of scribble lines (no legible letters)",
   [MON, REC, TUBE],
   [], "'red tape next to the CCTV monitor; do not leave the counter'")
sc("c03", 20.1, 29.7, "manager leaves", "indoor", "none", "N", "warm",
   "shop interior from behind the counter toward the glass door, the manager walking out into the dark, the young man alone at the counter",
   [M("person", "manager walking out", "he leaves for the night, a walking person"),
    M("story_event", "glass door slides open then shut", "automatic door follows the walker"),
    TUBE],
   [(20.9, "manager footsteps, door chime, auto door slide", "story: he walks out, 'someone will come at 6'")],
   "'at 6 a.m. someone will come to take over'")

# c04 rain starts, light changes, door opens
sc("c04", 0, 7.9, "first rain on the glass", "outdoor", "outdoor", "N", "night-open",
   "the shopfront from the car park, rain just starting, drops on the wet asphalt and on the glass, canopy lamp over the entrance, open sky above",
   [M("rain", "rain, two depths", "story: rain begins at 01:15"),
    M("water", "puddle ripples", "raindrops ring the puddles"),
    CLOUD, M("lamp", "canopy lamp flicker", "wet cheap lamp dips in the storm")],
   [(2.0, "rain bed fades in (3 s)", "story: rain begins; bed starts here and never drops out again until the dawn scene")],
   "RAIN SCENE, OUTDOOR. 'past midnight, 01:15, rain began tapping the glass'")
sc("c04", 7.9, 17.0, "tube lights turn teal", "indoor", "none", "N", "teal",
   "inside the shop, ceiling tubes dipping twice then turning cold green-blue, the young man looking up at the ceiling",
   [TUBE, M("person", "Non looks up", "he turns his head to the ceiling at the flicker"), MON, MOTH],
   [(8.0, "fluorescent buzz and click x2", "story: lights flicker twice"),
    (14.5, "hum shifts lower and colder", "light turns teal")],
   "INDOOR rain period: audio muffled only. 'tubes flicker out twice then turn blue-green'")
sc("c04", 17.0, 22.5, "the door opens by itself", "outdoor", "outdoor", "N", "teal",
   "low view across the wet car park toward the glass door sliding open by itself, cold teal light spilling onto the puddles, nobody there",
   [M("story_event", "glass door slides open", "story: it opens on its own"),
    M("rain", "rain, two depths", "continuing storm outside"),
    M("water", "puddle ripples in the spill light", "rain hits the puddles")],
   [(17.0, "door chime two tone", "story: the door chime rings"),
    (18.5, "auto door slide open", "story: the glass door slides open")],
   "RAIN SCENE, OUTDOOR. 'door chime, glass door slides open by itself'")
sc("c04", 22.5, 30.4, "nobody in the doorway", "indoor", "none", "N", "teal",
   "from behind the counter toward the open glass door, dark beyond, no one, the young man's hand frozen on the counter",
   [M("person", "Non turns toward the door", "he reacts to the chime"),
    M("story_event", "glass door slides shut again", "auto door closes after the empty pass"),
    TUBE_T],
   [(26.8, "door slide closed", "after the silence at the end of the take")],
   "INDOOR rain period: audio muffled only.")

# c05 wet footprints
sc("c05", 0, 9.6, "wet footprints at the door", "indoor", "none", "N", "teal",
   "tile floor just inside the glass door, black canal-water footprints appearing one by one across the threshold, nothing visible above them",
   [M("story_event", "footprints appear one at a time", "story: wet steps walk in"), DRIP("water drips off the invisible feet"), TUBE_T],
   [(2.8, "wet bare steps, slow, x6", "story: footsteps with canal water, one step at a time"),
    (4.0, "canal smell: low wet drone", "story names the smell of canal water")],
   "'footprints soaked in black canal water walk in slowly'")
sc("c05", 9.6, 19.3, "Non frozen", "indoor", "none", "N", "teal",
   "the young man behind the counter seen from the front, hands flat, jaw set, eyes fixed on the floor trail, teal light",
   [M("person", "Non's hand trembles", "fear, a person shaking"), TUBE_T, MON],
   [(10.8, "wet steps continue", "trail keeps coming")], "")
sc("c05", 19.3, 29.8, "steps cross the aisle", "indoor", "none", "N", "teal",
   "view along the snack aisle floor, a trail of wet black footprints crossing toward the counter, nothing visible",
   [M("story_event", "footprints appear one at a time", "story: the steps come closer"), DRIP("drips off the unseen body"), TUBE_T],
   [(19.3, "wet steps, slower, close", "10 s of narration silence in the take: the steps carry the beat")], "")
sc("c05", 29.8, 37.8, "bare wet feet", "indoor", "none", "N", "teal",
   "low floor level, bare feet streaming black water stepping onto the tile in front of the counter",
   [M("person", "feet step forward", "story: she walks in one step at a time"), DRIP("black water streams off the feet"), TUBE_T],
   [(29.8, "last step stops at the counter", "story: she is now inside")], "")

# c06 woman in red
sc("c06", 0, 13.0, "woman in red", "indoor", "none", "N", "teal",
   "a woman in a red Thai dress in the shop doorway, long wet hair over one side of her face, one pale eye visible through the hair, held wilted dark jasmine garland, black water pooling under her",
   [DRIP("water drips off the hem and hair"),
    M("cloth", "jasmine garland swings", "she holds it, it swings with her steps"),
    M("person", "woman walking in", "story: she walks in"), TUBE_T],
   [(0.0, "wet steps, canal smell drone", "story names the canal smell"),
    (5.4, "sharp breath in, cold", "her entrance")],
   "'woman in red, hair over half her face, one white eye, wilted jasmine'")
sc("c06", 13.0, 23.3, "bag of ice from the freezer", "indoor", "none", "N", "teal",
   "freezer chest at the end of the aisle, her pale wet hand lifting the lid and taking out a plastic bag of ice, cold mist rolling out",
   [M("hand_object", "freezer lid lifts", "her hand opens the freezer"),
    M("smoke", "cold mist from the freezer", "cold air meets warm air and fogs"),
    DRIP("water drips off her hand"), TUBE_T],
   [(13.0, "freezer lid open, ice bag rustle", "story: she takes a bag of ice from the freezer")],
   "'she takes a bag of ice from the freezer'")
sc("c06", 23.3, 33.6, "ice on the counter", "indoor", "none", "N", "teal",
   "counter close view, the bag of ice set down on the counter with a wet hand, jasmine petals dropping, a black puddle spreading",
   [M("hand_object", "ice bag set down", "story: she puts it on the counter"),
    M("water", "puddle spreads", "water leaks from the bag and her hand"),
    M("cloth", "jasmine petals fall", "dead petals drop from the garland"), MON],
   [(24.5, "ice bag thump on counter", "story: she places the ice on the counter")],
   "'places the bag of ice on the counter in front of him'")

# c07 rule 2, floating feet
sc("c07", 0, 15.0, "eyes down, ring it up", "indoor", "none", "N", "teal",
   "first person view from behind the counter, the register keypad under the young man's shaking hand, a strip of red dress at the edge of frame, eyes kept low",
   [M("hand_object", "hand pressing keys", "he rings up the ice, hand trembling"),
    M("screen", "register display blink", "a register display updates"),
    TUBE_T],
   [(8.0, "register beep x2", "he rings up the ice")],
   "'rule 2: ring her up normally, never look at her face, never meet her eyes'")
sc("c07", 15.0, 23.5, "monitor shows her at the counter", "indoor", "none", "CCTV", "teal",
   "close on the CCTV monitor, mono green-grey, the woman in the red dress at the counter from above, the clerk small beside her",
   [MON, M("screen", "monitor picture tear", "analog rolling tear"), REC],
   [(15.0, "monitor hum, tape hiss", "what he sees on the screen stops his breath")],
   "'what he sees on the monitor makes him stop breathing'")
sc("c07", 23.5, 38.2, "feet above the tile", "indoor", "none", "N", "teal",
   "low shot through the gap under the counter, her wet feet hovering a hand's width above the tile, a clean shadow gap, water drops falling through it",
   [M("person", "feet sway in the air", "story: her feet float above the floor"),
    DRIP("water drips fall through the gap"), TUBE_T],
   [(23.5, "held breath: air drops out, sub bass", "story: he stops breathing"),
    (28.3, "single drip echo", "feet do not touch the tile")],
   "'her feet do not touch the floor tiles, they float'")

# c08 banknote
sc("c08", 0, 10.5, "she walks through the glass", "indoor", "none", "N", "teal",
   "the woman in red turning from the counter and walking straight into the closed glass door, her back passing into the glass, the door panel stays shut, a wet banknote left on the counter",
   [M("person", "woman walking away", "story: she walks out"),
    DRIP("water drips off the hem"), M("hand_object", "banknote edge curls as it dries", "a wet paper note curls on the counter")],
   [(0.5, "wet banknote slap on the counter", "story: she puts down the note"),
    (4.0, "wet steps to the door", ""), (7.0, "no door slide at all; low cold whoosh", "story: the door does not open")],
   "'puts down a wet banknote, walks through the glass door without it opening'")
sc("c08", 10.5, 21.5, "old banknote", "indoor", "none", "N", "teal",
   "open cash drawer, the wet banknote lying in it, an old series note 20 years out of date, brown canal stain and a smell haze rising",
   [M("smoke", "smell haze rises from the note", "visual stand-in for the canal stench named in the take"),
    DRIP("note drips into the drawer"), TUBE_T],
   [(10.5, "cash drawer open ding", "he checks the drawer")],
   "'an old note from 20 years ago that stinks of canal'")

# c09 girl
sc("c09", 0, 10.6, "the girl at the counter", "indoor", "none", "N", "teal",
   "only the head and one hand of a small girl rising above the counter edge, skin violet-blue like a drowned child, black canal water dripping off her fingertips onto the counter, face turned down, hair wet",
   [DRIP("water drips off her fingertips"), M("person", "girl sways slightly", "small child standing in a draft of cold air"), TUBE_T],
   [(0.0, "door chime two tone", "story: the door chime rings again"),
    (3.5, "water drip on the counter, close", "story: black water falls from her fingertips")],
   "bumper 02:25 before. 'a small girl, violet skin like a drowned child, black water dripping'")
sc("c09", 10.6, 20.1, "her small voice", "indoor", "none", "N", "teal",
   "the girl's side profile as a paper cut-out against the cold light, mouth a thin line, wet hair strands dripping",
   [DRIP("hair drips"), M("cloth", "wet hair strands sway", "air moves the wet hair"), TUBE_T],
   [(11.0, "small child voice, trembling, dry (no reverb)", "story: she calls his real name softly")],
   "'calls his real name in a small trembling voice'")
sc("c09", 20.1, 29.6, "snack shelf", "indoor", "none", "N", "teal",
   "the snack shelf, a small gap in the row where a bag was taken, a child's wet handprint on the shelf edge",
   [DRIP("water drips off the shelf edge"), TUBE_T, MOTH],
   [(24.0, "plastic snack bag crinkle", "'buy snacks, please'")], "'big brother Non, buy snacks please'")
sc("c09", 29.6, 37.5, "begging", "indoor", "none", "N", "teal",
   "the young man seen over the counter, mouth shut, eyes wide, a small wet hand at the counter edge in the foreground",
   [M("person", "Non's eyes track and breath shakes", "fear, a person trembling"), DRIP("drips on the counter"), MON],
   [], "")

# c10 rule 3 coins
sc("c10", 0, 13.5, "do not answer", "indoor", "none", "N", "teal",
   "close on the young man's face, one hand pressed over his own mouth, sweat on the temple, teal tube light above",
   [M("water", "sweat drop slides", "a drop of sweat runs down the temple"), M("person", "hand trembles at the mouth", "fear"), TUBE_T],
   [(2.2, "breath held, ear ring tone, very low", "rule 3: never answer when called by name")],
   "'rule 3: never answer when called by name; never give change in wet coins'")
sc("c10", 13.5, 30.0, "three mud coins", "indoor", "none", "N", "teal",
   "top view of the counter, three ten baht coins side by side with canal mud and a strand of black hair stuck to them, a small wet hand pulling away",
   [M("hand_object", "small hand pulls back", "she sets the coins down and withdraws"),
    DRIP("mud water seeps from the coins"), TUBE_T],
   [(15.0, "coin clink x3, each on its own word", "story: three coins on the counter")],
   "'three ten baht coins with canal mud and hair: spirit money'")
sc("c10", 30.0, 38.1, "change means a trade", "indoor", "none", "N", "teal",
   "the young man's hand hovering over the till drawer above the coins, not touching",
   [M("hand_object", "hand hovers and shakes", "he almost gives change, the hand trembles"), TUBE_T, DRIP("drips on the counter")],
   [(30.0, "low sub bass swell", "if he gives change it is a trade of souls")], "")

# c11 smile
sc("c11", 0, 10.4, "snack slid across", "indoor", "none", "N", "teal",
   "counter close view, a snack bag sliding across the counter and the three muddy coins pushed back, the young man's hand and the small hand",
   [M("hand_object", "snack slides to her", "story: he slides the snack over"),
    M("hand_object", "coins pushed back", "story: he pushes the three coins back"), DRIP("drips on the counter"), TUBE_T],
   [(1.4, "snack slide on the counter", "story"), (4.5, "coins scrape back, clink x3", "story: coins pushed back")],
   "'slides the snack over and pushes all three coins back, no word'")
sc("c11", 10.4, 21.6, "wide smile", "indoor", "none", "N", "teal",
   "the girl's face as a paper cut-out in profile against the light, mouth stretched in a wide smile up to her ears, eyes dark",
   [DRIP("hair drips"), M("cloth", "wet hair stirs", "cold air"), TUBE_T],
   [(13.0, "wet slow smile: low cloth stretch, soft", ""), (14.5, "cold whisper, very close", "story: she whispers")],
   "'smiles wide up to the ears and whispers'")
sc("c11", 21.6, 29.6, "freezer behind the store", "indoor", "none", "N", "teal",
   "the glass freezer doors at the back of the shop, the end door frosted white, a dark shape pressed deep inside",
   [M("smoke", "cold mist at the door seams", "cold air leaks out"), TUBE_T, DRIP("frost melt drips")],
   [(22.0, "freezer compressor hum rises", "'the previous brother is in the freezer behind the store'")],
   "'the one before you is still in the freezer behind the store'")
sc("c11", 29.6, 37.7, "she is gone", "indoor", "none", "N", "teal",
   "the counter with a snack gone, only a black canal puddle on the tile where the girl stood",
   [M("water", "puddle settles in ripples", "last drops fall into it"), DRIP("a final drip"), TUBE_T],
   [(29.6, "blink: tiny cloth snap", ""), (31.0, "silence then single drip", "story: she is gone")],
   "'blink, she vanishes, only a puddle'")

# c12 flashback FB2
sc("c12", 0, 10.3, "03:00 flip the paper", "indoor", "none", "N", "teal",
   "the young man's hands turning the rule sheet over on the counter, the clock face above showing three, pressure in the posture",
   [M("hand_object", "sheet flips", "he turns the paper over"), M("hand_object", "clock second hand", "clock above ticks"), TUBE_T, MON],
   [(2.3, "paper flip", "story: he turns the paper over")],
   "bumper 03:00 before. 'pressure peaks at 3, he turns the paper over'")
sc("c12", 10.3, 20.0, "the previous clerk wrote it", "indoor", "none", "FB", "warm",
   "FLASHBACK: the same counter, a thin clerk in the same uniform hunched writing in pencil on the back of a sheet, hand shaking, glancing at the monitor",
   [M("hand_object", "pencil hand writing", "he writes the warning, the hand shaking"),
    M("lamp", "old tube light flicker", "the same faulty tube in the past"),
    M("person", "clerk glances at the monitor", "he is afraid of what he saw")],
   [(10.3, "FB sting: low tape-warble swell, 0.6 s", "grade change marker"), (11.0, "pencil scratching on paper", "story: pencil writing")],
   "FLASHBACK: 'in pencil, shaky, the one before who vanished'")
sc("c12", 20.0, 31.1, "do not trust the red ink", "indoor", "none", "N", "teal",
   "close on the pencil scribble lines on the back of the sheet, the young man's finger tracing under them (no legible letters)",
   [M("hand_object", "finger traces the line", "he reads it"), TUBE_T, MON],
   [(20.0, "back to present: tape-warble stops, hum returns", "grade returns to normal")],
   "'do not believe the rule in red ink, the store wrote it to lure us off the counter'")

# c13 rule 5 red
sc("c13", 0, 15.0, "all blue except rule 5", "indoor", "none", "N", "teal",
   "the front of the rule sheet, rows of blue scribble lines with only one row in red, his finger under the red row",
   [M("hand_object", "finger moves to the red row", "he finds rule 5"), TUBE_T, MON, REC],
   [(3.0, "paper rustle", "he flips back to the front")],
   "'all rules in blue except rule 5, in red'")
sc("c13", 15.0, 31.0, "more people than he can see", "indoor", "none", "CCTV", "teal",
   "CCTV monitor view of the shop interior with a small pictogram figure count in the corner (one stick figure), the counter empty-looking",
   [MON, M("screen", "monitor roll bar", "analog roll bar"), REC],
   [(15.0, "monitor hum rises", "rule 5: if the camera shows more people than you see, leave the counter")],
   "'if the camera shows more people than your eyes do, leave the counter at once'")

# c14 count 1 -> 2, alley figure
sc("c14", 0, 9.3, "the count goes to two", "indoor", "none", "CCTV", "teal",
   "CCTV monitor channel 3 close view, the stick figure count in the corner flicks from one figure to two, picture tearing",
   [M("screen", "count pictogram changes", "story: the number of people goes from 1 to 2"), MON, M("screen", "picture tear", "signal glitch")],
   [(0.5, "digital glitch burst, 0.4 s", "story: the image glitches while the count changes"), (2.6, "sub bass hit", "")],
   "bumper 03:35 before. 'camera 3, the count jumps from 1 to 2'")
sc("c14", 9.3, 14.5, "the alley behind", "outdoor", "outdoor", "CCTV", "night-open",
   "mono CCTV view of the back alley behind the shop, wet ground, a far lamp, rain falling, a very tall long limbed figure in a staff uniform standing still at the end",
   [M("rain", "rain, two depths", "the same storm behind the shop"), M("water", "puddle ripples", "rain hits puddles"), M("lamp", "alley lamp flicker", "wet lamp dips")],
   [(9.3, "rain louder, camera mic (full rain bed)", "outdoor shot, bed at full")],
   "RAIN SCENE, OUTDOOR (shown through the monitor). 'tall unnatural figure in a staff uniform at the end of the alley'")
sc("c14", 14.5, 27.6, "bent ninety degrees", "outdoor", "outdoor", "CCTV", "night-open",
   "same mono alley camera but tighter, the tall figure folded over ninety degrees at the waist, two white eyes staring up into the lens, rain streaking",
   [M("story_event", "figure folds over ninety degrees", "story: it bends over"), M("rain", "rain, two depths", "storm"), M("lamp", "alley lamp flicker", "wet lamp dips")],
   [(16.0, "bones crack, slow, x3", "story: unnatural limbs folding"), (22.6, "held low drone", "it does not blink")],
   "RAIN SCENE, OUTDOOR. 'bends 90 degrees, white eyes staring into the camera, not blinking'")
sc("c14", 27.6, 36.6, "Non in the monitor glow", "indoor", "none", "N", "teal",
   "the young man's face lit by the monitor, still, sweat on his lip, eyes locked on the screen",
   [M("water", "sweat drop slides", "fear"), MON, M("person", "his breath shakes", "a person holding down fear")],
   [(27.6, "monitor hum", "")], "")

# c15 rule 6 microwave
sc("c15", 0, 13.3, "microwave runs behind the counter", "indoor", "none", "N", "teal",
   "the microwave on its shelf behind the counter, the glass door lit, turntable and a cup turning slowly, glass shows a faint reflection of the dark aisle",
   [M("hand_object", "turntable turns", "microwave turntable rotates"), M("lamp", "microwave lamp glow flicker", "interior bulb"), TUBE_T],
   [(0.0, "microwave hum, constant until the ding", "story names the microwave running"), (5.0, "turntable low motor", "")],
   "'rule 6: while the microwave is on, face it, back to the shopfront, until it beeps'")
sc("c15", 13.3, 20.2, "back to the shopfront", "indoor", "none", "N", "teal",
   "the young man from behind facing the microwave, the dark shopfront behind him unseen, the shelves on both sides",
   [M("person", "Non turns to face the microwave", "he turns his back to the store as the rule says"), TUBE_T, M("hand_object", "turntable turns", "microwave runs")],
   [(14.5, "turn: shoe on tile squeak", "he turns around")], "")
sc("c15", 20.2, 32.7, "reflection in the glass", "indoor", "none", "N", "teal",
   "close on the microwave glass door, warped reflection of the shop and counter behind him, the cup turning",
   [M("hand_object", "turntable turns", "microwave runs"), M("lamp", "microwave lamp glow flicker", "interior bulb"), M("screen", "reflection shimmer", "curved glass wobbles the reflection")],
   [(20.2, "hum rises half a tone", "tension")], "")

# c16 approach
sc("c16", 0, 14.0, "it moves one aisle at a time", "indoor", "none", "CCTV", "teal",
   "side CCTV monitor beside the microwave, mono image of the shop, the tall figure twitching along the aisle toward the counter, neck broken to one side",
   [M("story_event", "tall figure advances in twitching steps", "story: it moves toward the counter one aisle at a time"),
    MON, M("hand_object", "turntable turns", "microwave runs")],
   [(0.0, "bones crack, irregular, x4", "story: neck cracks"), (8.0, "wet steps, approaching, slow", "story: wet steps")],
   "'neck twisted, jerking toward the counter, one aisle at a time'")
sc("c16", 14.0, 26.6, "it stops behind him", "indoor", "none", "N", "teal",
   "the young man from behind, a huge tall shadow rising up the wall behind him from the tube light, cold mist curling at his neck",
   [M("story_event", "shadow rises up the wall", "story: it stops right behind him"), M("smoke", "cold breath mist", "story: cold breath"), TUBE_T],
   [(14.0, "wet footsteps stop, 1 beat of silence", "story: stops right behind"), (18.0, "cold slow breath, close", "story"),
    (22.0, "rotten canal smell drone", "story names the smell")],
   "'stops right behind him, cold breath, canal stench'")
sc("c16", 26.6, 36.0, "bones by the ear", "indoor", "none", "N", "teal",
   "tight on the young man's ear and jaw, wet hair strands stirring, a faint pale shape at the edge of frame",
   [M("cloth", "wet hair strands stir", "cold breath moves them"), M("smoke", "cold breath mist", "story: cold breath"), TUBE_T],
   [(26.6, "bone crackling beside the ear", "story: bones clicking next to the ear"), (31.3, "whisper close, breathy, dry", "'turn around, look'")],
   "'bones crackling by his ear, whispering: turn around, look'")

# c17 ding
sc("c17", 0, 10.6, "eyes shut", "indoor", "none", "N", "teal",
   "close on the young man's shut eyes and clenched jaw, a tape line on the floor visible under his toes, his heel not moving",
   [M("water", "sweat drop slides", "fear"), M("person", "jaw and shoulders tremble", "fear"), TUBE_T],
   [(0.0, "held breath, heartbeat low", "story: he grits his teeth")], "'does not turn, does not step half a step'")
sc("c17", 10.6, 21.6, "ding", "indoor", "none", "N", "teal",
   "the microwave lamp going dark as the timer ends, the monitor beside it dropping back to one stick figure, cold air lifting off him",
   [M("lamp", "microwave lamp goes out", "story: the timer ends"), M("screen", "pictogram count returns to one", "story: the count drops back"), M("smoke", "cold air lifts away", "story: the cold behind him vanishes")],
   [(10.6, "microwave DING", "story: the microwave beeps"), (11.4, "cold air release, soft whoosh", "story: the cold leaves")],
   "'ding, the cold behind him disappears, the count returns to one'")

# c18 03:45 voice from the freezers
sc("c18", 0, 8.7, "03:45", "indoor", "none", "N", "teal",
   "the shop wide from the entrance, the young man small at the counter, teal light, the back freezer wall dark at the end",
   [TUBE_T, MON, DRIP("condensation drips off a freezer door")],
   [(0.0, "exhale, shaky breath", "story: he can breathe again")],
   "bumper 03:45 before. 'a cry for help'")
sc("c18", 8.7, 22.8, "a voice from the back", "indoor", "none", "N", "teal",
   "low view down the aisle to the freezer wall, the end door frosted, frost spreading, shadows between shelves",
   [M("smoke", "frost mist at the door seams", "cold air leaks out"), TUBE_T, DRIP("meltwater drips")],
   [(8.7, "muffled cry for help from far inside the freezer", "story: a voice calling for help (stock muffled voice, no paid TTS)"),
    (18.5, "cry repeats, weaker", "")],
   "'a voice begging for help'")
sc("c18", 22.8, 31.9, "half a step", "indoor", "none", "N", "teal",
   "the young man's feet at the edge of the counter zone, one toe lifting then settling",
   [M("person", "foot lifts and settles", "he nearly steps out and stops"), TUBE_T, DRIP("sweat drip on the floor")],
   [(22.8, "shoe sole scuff", "")], "")

# c19 freezer
sc("c19", 0, 9.6, "frosted glass", "indoor", "none", "CCTV", "teal",
   "CCTV view of the farthest freezer door fogging white with frost far faster than the others",
   [M("smoke", "frost spreads on the glass", "ice crystals form"), MON, M("screen", "picture tear", "signal glitch")],
   [(0.0, "ice crackle rising", "frost spreading")], "'the last freezer door fogs abnormally'")
sc("c19", 9.6, 19.4, "palms on the glass", "indoor", "none", "N", "teal",
   "inside shot of the frosted freezer glass, two violet-blue palms slamming against it from the inside, frost cracking around them",
   [M("story_event", "palms slam on the glass", "story: hands slam from inside"), M("smoke", "breath fog", "cold breath on the glass"), TUBE_T],
   [(9.6, "palm slap on glass x3 hard", "story: both hands slam the glass"), (13.0, "ice crack", "")],
   "'two hands slam the freezer glass'")
sc("c19", 19.4, 30.0, "face in the glass", "indoor", "none", "N", "teal",
   "close on the freezer glass, a pale thin face of a man in a staff uniform pressed against the frost, eyes huge, breath fog",
   [M("smoke", "breath fog", "story: face on the glass"), M("hand_object", "fingers slide down the glass", "story: fingers drag"), TUBE_T],
   [(19.4, "face squeak on glass", ""), (24.0, "fingernails drag on glass", "story: fingers dragging")],
   "'a face in uniform, the previous clerk'")
sc("c19", 30.0, 43.1, "fingers write on the ice", "indoor", "none", "N", "teal",
   "close on the frost, fingertips scratching reversed marks in the ice (no legible letters), ice dust falling",
   [M("hand_object", "fingers scratch the frost", "story: he writes on the glass"), M("cloth", "ice dust falls", "scratched ice falls"), TUBE_T],
   [(30.0, "finger scratch on ice, slow, 6 s", "story: writes 'help, it is cold inside'")],
   "'writes in reverse: help me, it is too cold in here'")

# c20 the rule 7
sc("c20", 0, 12.9, "not a drink room", "indoor", "none", "N", "teal",
   "the freezer door opened a crack onto an endless frozen corridor, rows of staff uniforms hanging in the cold, frost haze",
   [M("cloth", "hanging uniforms sway", "cold draft pushes the cloth"), M("smoke", "frost haze drifts", "cold air flows out"), TUBE_T],
   [(0.0, "deep sub drone, cold wind", "reveal: the back room is another dimension that swallowed clerks for 20 years")],
   "'it is not a drink room, it is a dimension that swallowed every clerk for 20 years'")
sc("c20", 12.9, 22.0, "peel the black tape", "indoor", "none", "N", "teal",
   "close on the bottom of the sheet, black tape over rule 7, his fingernail lifting its edge",
   [M("hand_object", "tape peels off", "he peels the tape"), TUBE_T, MON],
   [(12.9, "tape peel, slow, adhesive crackle", "story: he peels the black tape")],
   "'black tape covers rule 7, he peels it'")
sc("c20", 22.0, 31.8, "rule 7 text", "indoor", "none", "N", "teal",
   "the sheet with rule 7 uncovered in blue scribble lines, three tiny paper pictograms beside it: a switch lever, a shutter door, a bowed head",
   [M("hand_object", "finger moves along the line", "he reads"), TUBE_T, MON],
   [], "'if the shop lights go out after 4 a.m.: pull the breaker down, pull the small front door shut, sit head down behind the counter until 6; never open to a call'")
sc("c20", 31.8, 42.9, "pictograms", "indoor", "none", "N", "teal",
   "close on the breaker box on the back wall, an old switch lever, dust and a dead moth",
   [M("hand_object", "hand rests on the switch", "he looks at it, fingers twitch"), TUBE_T, MOTH],
   [(31.8, "breaker box hum", "")], "")

# c21 lights out
sc("c21", 0, 4.3, "all lights go out", "indoor", "none", "N", "dark",
   "wide shop interior, all the tubes cutting out at once, only the CCTV monitor still glowing, the young man a silhouette at the counter",
   [M("lamp", "tube lights cut out together", "story: every light goes out"), MON, M("person", "Non turns his head", "he reacts")],
   [(0.6, "breaker clunk, lights die, big sub drop", "story: lights go out at 04:30")], "bumper 04:30 before. 'lights go out all at once'")
sc("c21", 4.3, 11.0, "pull the shutter down", "indoor", "none", "N", "dark",
   "dark shop, the young man running to the small front door and dragging its shutter all the way down, monitor glow only",
   [M("person", "Non runs to the door and back", "he runs"), M("story_event", "small front door shutter rolls down", "story: he pulls it down"), MON],
   [(4.3, "running steps", "story: he runs"), (6.0, "shutter rattles down to the floor", "story: pulls the door to the bottom"),
    (9.5, "running steps back, sliding behind the counter", "story: runs back to hide")],
   "'pull the small front door all the way down, run back and crouch behind the counter'")
sc("c21", 11.0, 21.5, "pounding", "indoor", "none", "N", "dark",
   "dark, the young man crouched behind the counter head down, the shutter shaking in its frame, monitor glow",
   [M("story_event", "shutter shakes in its frame", "story: the door is pounded until it shakes"), M("person", "Non shivers", "fear"), MON],
   [(11.0, "pounding on the shutter, heavy, irregular", "story: the small door is hammered"), (17.8, "pounding keeps going, dry", "")],
   "'all night the small front door is pounded until it shakes'")
sc("c21", 21.5, 29.0, "mother's voice outside", "outdoor", "outdoor", "N", "night-open",
   "outside the dark shop front in the rain, a woman's silhouette from behind at the foot of the shutter, hand raised to knock, nothing else, shop lights off",
   [M("rain", "rain, two depths", "storm outside"), M("water", "puddle ripples", "raindrops ring the puddles"), M("person", "woman raises her hand and knocks", "story: she calls and pounds"), M("story_event", "shutter rattles", "she shakes it")],
   [(21.5, "rain full again (outdoor)", ""), (22.0, "woman's voice calling, his mother's voice, muffled (stock voice, no paid TTS)", "story: 'Non, my son, open the door for mom'")],
   "RAIN SCENE, OUTDOOR. 'a woman outside, in his mother's voice: Non, my son, open up'")
sc("c21", 29.0, 36.9, "mother is in the hospital", "indoor", "none", "N", "dark",
   "night ward 30 km away, his mother asleep in her bed under a dim lamp, curtain around the bed, a monitor line",
   [M("screen", "ward monitor line", "a heart monitor beeps"), M("curtain", "bed curtain sway", "ward curtain moves in the air"), DRIP("saline drip drops")],
   [(29.0, "ward monitor beep, soft", "he knows she is in the hospital")], "cutaway (simultaneous, not a flashback; normal grade). 'but she is in a hospital 30 km away'")

# c22 dawn and end
sc("c22", 0, 6.9, "ears covered", "indoor", "none", "N", "dark",
   "dark, the young man curled behind the counter, hands over his ears, eyes shut, praying, monitor glow",
   [M("person", "Non rocks and mouths a prayer", "he prays"), MON, M("story_event", "shutter trembles lightly", "the pounding goes on")],
   [(0.0, "pounding and whispers, muffled", "story: whispers and knocks")], "no bumper here: the dawn arrives inside this take (see next scene)")
sc("c22", 6.9, 16.6, "first sun ray", "indoor", "none", "D", "dawn",
   "the first golden sun ray through the gap under the small shutter lying across the floor and the counter, dust in the beam",
   [M("story_event", "sun beam widens across the floor", "story: the first ray comes in, sun rising"),
    M("person", "Non lowers his hands and looks up", "he hears the knocking stop"),
    M("cloth", "dust in the beam", "dust moves in the light"), MON],
   [(6.9, "rain bed crossfades out (>=2 s)", "storm over by dawn (story silent, flagged)"),
    (8.0, "pounding and whispers cut to silence", "story: they vanish at once"),
    (11.0, "first birds", "dawn")],
   "dawn wipe: 0.4 s warm light bloom on the cut, no gap (the take has no pause long enough for a bumper). 'at 6 the first ray of sun enters, all the pounding and whispers stop at once'")
sc("c22", 16.6, 20.8, "keys on the counter", "indoor", "none", "D", "dawn",
   "counter close view in warm dawn light, a key ring set down on the counter, dust in the beam",
   [M("hand_object", "keys set down", "story: he puts the keys down"), M("cloth", "dust in the beam", "dust moves in the light"), M("smoke", "steam from the dry-wet tile", "the wet floor warms in the sun")],
   [(17.0, "keys jingle and settle", "story: leaves the keys on the counter")],
   "'puts the shop keys on the counter'")
sc("c22", 20.8, 26.3, "walks out", "outdoor", "none", "D", "dawn",
   "the shop front at dawn, the small door up, the young man walking away along the wet road into the pale sky, long shadow, puddles",
   [M("person", "Non walking away", "walker; shrinks with distance on the road plane"), CLOUD, M("water", "puddle drips and ripples", "last drips from the canopy"), GRASS],
   [(20.8, "footsteps on wet asphalt, away", "story: leaves without looking back"), (22.0, "birds", "")],
   "OUTDOOR, no rain (storm over, flagged). 'leaves without looking back'")
sc("c22", 26.3, 39.7, "another lonely store", "outdoor", "none", "N", "night-open",
   "a different lonely roadside shop at dusk on another road, hiring board blank on the wall, one lit window, seen from the car park",
   [CLOUD, M("insect", "moths at the lamp", "moths gather at the only light"), M("lamp", "porch lamp flicker", "a cheap lamp buzzes"), GRASS],
   [(26.3, "night insects bed returns", "closing message to the viewer")],
   "'remember: a store on a lonely road hiring night staff at triple pay'")
sc("c22", 39.7, 46.3, "the one hiring", "outdoor", "none", "N", "night-open",
   "tight on a lit shop window at night from the car park, an empty chair behind the glass and nobody behind the counter, door closed",
   [M("insect", "moths hit the glass", "moths against the lit window"), M("lamp", "window lamp flicker", "cheap tube dips"), M("cloud", "thin cloud crosses the moon", "clouds move")],
   [(39.7, "single low note, then silence", "story ends in the episode, no outro beat")],
   "'the one who asks might not be human' (last line; ASR garbled, final words to be confirmed against the clean take)")

# ---------------------------------------------------------------- build
STYLE_HEAD = ("Use the attached image as the exact style reference: layered cut-paper diorama, real paper fibre texture, "
              "crisp cut edges, quilled swirl details, charcoal and slate paper, amber lights. No text, no letters, no numbers, "
              "no watermark. 16:9 wide frame. Modern rural Thai highway convenience store, NO apartment block, NO city skyline. ")
SKY = {"night-open": "Night sky, dark slate clouds, NO red sky, NO red moon. ",
       "warm": "Interior, bright white fluorescent tubes. ", "teal": "Interior, cold green-blue fluorescent tubes. ",
       "dark": "Interior almost dark, only a CCTV monitor glow. ", "dawn": "Dawn, warm gold light after the storm. ",
       "day": "Daylight, grey-white sky, NO moon, NO red sky. "}
STYLE_TAIL = " Adults only (18+) if adults appear. No blushing, no red face, no red ears. No gore, no blood."
GRADE_NOTE = {"N": "normal grade", "FB": "FLASHBACK grade: desaturated sepia, lifted blacks, cold shadows, film grain, soft vignette",
              "CCTV": "monitor grade: mono green-grey, scanlines (not a flashback)", "D": "dawn grade: warm gold after the storm"}


def load_chunks():
    ch = {}
    for f in sorted(glob.glob(WORDS + "/c*.json")):
        ws = json.load(open(f))
        ch[os.path.basename(f)[:-5]] = ws
    return ch


def snap(ws, t, end):
    """cut time on a pause: if t already sits inside a gap >= .15 s keep it (centred when the gap is short);
    else the nearest gap midpoint within 2.5 s, larger gaps preferred. Returns (time, gap)"""
    if t <= 0:
        return 0.0, 0.0
    if t >= end:
        return end, 0.0
    gaps = []
    for i in range(1, len(ws)):
        g = ws[i]["s"] - ws[i - 1]["e"]
        if g >= 0.15:
            gaps.append((ws[i - 1]["e"], ws[i]["s"], g))
    if not gaps:
        return t, 0.0
    for e0, s1, g in gaps:
        if e0 <= t <= s1:
            return (round((e0 + s1) / 2.0, 2) if g < 1.0 else round(t, 2)), round(g, 2)
    best = min(gaps, key=lambda c: abs((c[0] + c[1]) / 2.0 - t) - 0.3 * min(c[2], 1.5))
    return round((best[0] + best[1]) / 2.0, 2), round(best[2], 2)


def build():
    ch = load_chunks()
    order = sorted(ch)
    clen = {c: ch[c][-1]["e"] for c in order}
    off, cum = {}, INTRO
    for c in order:
        if c in BUMPERS:
            cum += GAP
        off[c] = round(cum, 2)
        cum += clen[c] + TAIL
    total = round(cum, 2)
    scenes, n = [], 0
    for s in S:
        n += 1
        sid = f"s{n:02d}"
        d = dict(s)
        d["id"] = sid
        if s["chunk"] == "intro":
            d["t0"], d["t1"], d["snap_gap"] = 0.0, INTRO, 0.0
            d["la"], d["lb"] = 0.0, INTRO
        else:
            ws, end = ch[s["chunk"]], clen[s["chunk"]]
            a, ga = snap(ws, s["a"], end)
            b, gb = snap(ws, s["b"], end) if s["b"] < end - 1.0 else (end + TAIL, 9.9)
            d["la"], d["lb"] = a, round(b, 2)
            d["t0"], d["t1"] = round(off[s["chunk"]] + a, 2), round(off[s["chunk"]] + b, 2)
            d["snap_gap"] = ga
        d["plate"] = dict(id=f"{sid}_plate", brief=s["plate"])
        d["scene_prompt"] = (STYLE_HEAD + SKY.get(s["light"], "") + s["plate"] + ". " + GRADE_NOTE[s["grade"]].split(":")[0] + "." + STYLE_TAIL
                             if s["grade"] != "FB" else
                             STYLE_HEAD + SKY.get(s["light"], "") + s["plate"].replace("FLASHBACK: ", "") + STYLE_TAIL)
        d["grade_note"] = GRADE_NOTE[s["grade"]]
        d["rain_audio"] = rain_audio(s)
        scenes.append(d)
    # chain scene ends to next starts inside a take (snap can leave gaps of 0)
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        if a["chunk"] == b["chunk"]:
            a["lb"] = b["la"]
            a["t1"] = b["t0"]
    return scenes, off, clen, total


def rain_audio(s):
    """rain bed state: off before the 01:15 rain, full on outdoor rain scenes, muffled bed on indoor rain-period scenes,
    off from the dawn crossfade."""
    return None


RAIN_FIRST = "c04"
RAIN_LAST = "c21"


def assign_rain_audio(scenes):
    on = False
    for s in scenes:
        if s["chunk"] == "c04" and s["la"] < 2.0:
            s["rain_audio"] = "off until 2.0 s then fades in 3 s (story: rain begins)"
            on = True
            continue
        if s["chunk"] in ("intro", "c01", "c02", "c03"):
            s["rain_audio"] = "off (before 01:15)"
        elif s["id"] and s["grade"] == "D":
            s["rain_audio"] = "off (storm over; bed already crossfaded out, >=2 s)" if s["name"] != "first sun ray" else "bed crossfades out over the first 2.5 s, then off"
        elif s["chunk"] == "c22" and s["name"] in ("another lonely store", "the one hiring"):
            s["rain_audio"] = "off (night insects bed)"
        elif s["rain"] == "outdoor":
            s["rain_audio"] = "FULL bed (outdoor rain scene)"
        else:
            s["rain_audio"] = "muffled bed, low pass ~1 kHz, -12 dB vs full (indoor; no rain drawn). CMO may switch to off"
    return scenes


# ---------------------------------------------------------------- checks
BAD_TEXT = [("em dash", "—"), ("left guillemet", "«"), ("right guillemet", "»"),
            ("blush word", "หน้าแดง"), ("blush word", "หูแดง")]
EP_PAT = re.compile(r"(\bEP\s*\d|\bepisode\s*\d|ตอนที่\s*\d|เอพ)", re.I)


def check(scenes, off, clen, total):
    errs, notes = [], []
    seen = set()
    for i, s in enumerate(scenes):
        sid = s["id"]
        mv = s["movers"]
        if not 3 <= len(mv) <= 5:
            errs.append(f"{sid}: {len(mv)} movers (need 3-5)")
        for m in mv:
            if m["kind"] not in KINDS:
                errs.append(f"{sid}: mover kind {m['kind']!r} not a real mover kind")
            if not m["reason"].strip() or "\n" in m["reason"]:
                errs.append(f"{sid}: mover {m['name']!r} has no one-line reason")
        if s["io"] not in ("indoor", "outdoor"):
            errs.append(f"{sid}: io not marked")
        if s["rain"] == "outdoor" and s["io"] != "outdoor":
            errs.append(f"{sid}: rain on an indoor scene (rule 2)")
        if any(m["kind"] == "rain" for m in mv) and (s["rain"] != "outdoor" or s["io"] != "outdoor"):
            errs.append(f"{sid}: a rain mover outside an outdoor rain scene")
        if s["plate"]["id"] in seen:
            errs.append(f"{sid}: plate repeated")
        seen.add(s["plate"]["id"])
        if len({x["name"] for x in mv}) != len(mv):
            errs.append(f"{sid}: duplicate mover name")
        txt = json.dumps(s, ensure_ascii=False)
        scan = txt.replace(STYLE_TAIL, "")
        for what, tok in BAD_TEXT:
            if tok in scan:
                errs.append(f"{sid}: {what} in plan text")
        if EP_PAT.search(scan):
            errs.append(f"{sid}: an EP / episode number in plan text")
        if s["grade"] == "FB" and "FLASHBACK" not in s["note"]:
            errs.append(f"{sid}: FB grade without a FLASHBACK note")
        if s["t1"] <= s["t0"]:
            errs.append(f"{sid}: empty or negative span {s['t0']}..{s['t1']}")
        if s["t1"] - s["t0"] > 16.5:
            notes.append(f"{sid}: long scene {s['t1'] - s['t0']:.1f}s")
        if s["snap_gap"] < 0.15 and s["chunk"] != "intro" and s["la"] > 0:
            errs.append(f"{sid}: cut not on a pause (gap {s['snap_gap']})")
    # flashback blocks must be bracketed by non-FB scenes
    fb = [s["id"] for s in scenes if s["grade"] == "FB"]
    for i, s in enumerate(scenes):
        if s["grade"] == "FB":
            nxt = scenes[i + 1] if i + 1 < len(scenes) else None
            if nxt is None or (nxt["grade"] == "FB" and (i + 2 >= len(scenes) or False)):
                pass
    for i, s in enumerate(scenes):
        if s["grade"] == "FB" and (i + 1 >= len(scenes)):
            errs.append("flashback runs to the end of the film")
    # rain scene all marked
    rain_scenes = [s for s in scenes if s["rain"] == "outdoor"]
    # rule 5 note: structures never move unless story_event
    for s in scenes:
        for m in s["movers"]:
            if re.search(r"\b(house|building|shop front|wall|roof)\b", m["name"], re.I) and m["kind"] != "story_event":
                errs.append(f"{s['id']}: structure mover {m['name']!r}")
    # coverage: scenes exactly tile each take
    for c, e in clen.items():
        sc_ = [s for s in scenes if s["chunk"] == c]
        if not sc_:
            errs.append(f"take {c}: no scenes")
            continue
        if abs(sc_[0]["la"]) > 0.01:
            errs.append(f"take {c}: first scene starts at {sc_[0]['la']}")
        if abs(sc_[-1]["lb"] - (e + TAIL)) > 0.05:
            errs.append(f"take {c}: last scene ends {sc_[-1]['lb']} (take {e + TAIL})")
    return errs, notes, fb, rain_scenes


def md(scenes, off, clen, total, errs, notes):
    L = []
    w = L.append
    w("# Ghost Rules EP2 (paper, 16:9) M1: scene list and mover plan\n")
    w("Generated by `video/ghostrules/ep02_paper_plan.py` from `words/c01..c22.json`. M1 only: no render, no paid API.\n")
    w("## How to read\n")
    w("- Times: `take-local` = seconds inside the voice take (from the ASR words file, snapped to a pause). `global` = estimated film time. Global is an estimate because the clean take wavs are not on this host (see Not checked).")
    w(f"- Film estimate: {total:.0f} s ({total / 60:.1f} min): intro {INTRO} s, {len(BUMPERS)} animated bumpers of {GAP} s, take length = last word + {TAIL} s.")
    w("- **io** = where the camera stands. **rain** = visual rain: only `outdoor` scenes get rain drawn (rule 2). Indoor scenes during the storm get no drawn rain, only a muffled audio bed (CMO call below).")
    w("- **grade**: N normal, **FB flashback grade** (desaturated sepia, lifted blacks, cold shadows, grain, vignette), CCTV (mono monitor look, not a flashback), D dawn. A flashback scene is always followed by an N scene.")
    w("- Every mover is a thing that really moves, and carries a one-line reason. Dust, light and shadow are extra layers on every scene and are not counted as movers.\n")
    w("## Counts\n")
    nfb = sum(1 for s in scenes if s["grade"] == "FB")
    nr = sum(1 for s in scenes if s["rain"] == "outdoor")
    nmv = sum(len(s["movers"]) for s in scenes)
    w(f"- {len(scenes)} scenes, {len(scenes)} unique plates (none repeated), {nmv} movers (avg {nmv / len(scenes):.1f} per scene, min 3, max 5).")
    w(f"- Flashback scenes (own grade): {nfb}. Outdoor rain scenes: {nr}. Indoor scenes in the rain period (no drawn rain): {sum(1 for s in scenes if s['rain'] == 'none' and s['rain_audio'].startswith('muffled'))}.")
    w(f"- Plan check: {'PASS' if not errs else 'FAIL'} ({len(errs)} errors).\n")
    w("## Chapter bumpers (animated, not freeze frames)\n")
    w("Each is a 1.5 s paper animation: a torn paper clock face, the hands sweep to the time, ink bleed wipe into the next scene. No digits, no text. Story clock times are spoken in the take; `02:25` is inferred because the ASR dropped the hour digit.\n")
    for c, t in BUMPERS.items():
        w(f"- before {c} at global ~{off[c] - GAP:.1f} s: clock sweeps to {t}")
    w("")
    w("## Scene list\n")
    cur = None
    for s in scenes:
        if s["chunk"] != cur:
            cur = s["chunk"]
            w(f"\n### take {cur}" + (f" (global {off[cur]:.1f} s, ASR length {clen[cur]:.1f} s)" if cur in off else "") + "\n")
        w(f"**{s['id']}** `{s['chunk']} {s['la']:.1f}-{s['lb']:.1f}` (global {s['t0']:.1f}-{s['t1']:.1f}, {s['t1'] - s['t0']:.1f} s) **{s['name']}**")
        w(f"- io: **{s['io']}** | rain drawn: **{s['rain']}** | rain bed: {s['rain_audio']} | grade: **{s['grade']}**" + (" FLASHBACK" if s["grade"] == "FB" else "") + f" | light: {s['light']}")
        w(f"- plate `{s['plate']['id']}`: {s['plate']['brief']}")
        for m in s["movers"]:
            w(f"  - mover ({m['kind']}) {m['name']}: {m['reason']}")
        for sf in s["sfx"]:
            w(f"  - sfx {sf[0] if isinstance(sf[0], str) else f'{sf[0]:.1f}'}: {sf[1]}" + (f" ({sf[2]})" if len(sf) > 2 and sf[2] else ""))
        if s["note"]:
            w(f"- story: {s['note']}")
        w("")
    w("## Rain bed plan (rule 3, built in M2)\n")
    w("- One continuous bed from s12 (take c04 2.0 s) to the first sun ray (s73, 2.5 s crossfade out). Built as one loop with >=1.5 s equal-power crossfades between loop copies, never a file end. State changes between scenes are gain and low-pass moves over >=1.5 s, never cuts: FULL on the 5 outdoor rain scenes, muffled (low pass ~1 kHz, -12 dB) under indoor scenes of the storm.")
    w("- M2 gate: `ffmpeg silencedetect` on the final mix (noise -50 dB, d=0.3) must report no gap inside s12..s73, plus an `astats` peak-jump scan for clicks at every loop seam and state change.\n")
    w("## Calls for the CMO (defaults taken, change on review)\n")
    w("1. Indoor scenes in the rain period: no rain is drawn (rule 2), the audio bed stays muffled so the night keeps its weather. If rule 2 also means no rain sound indoors, switch those scenes to off.")
    w("2. The take never says the rain stops. Default: it is over by the first sun ray at 06:00 (bed crossfades out in s73, dawn is dry).")
    w("3. Flashbacks: s06 and s07 (his lay-off and his mother's ward), s40 (the previous clerk writing the pencil warning). The take says the pencil note is by the clerk before him, but never shows it: s40 is my staging. Drop it if you want only what the voice says.")
    w("4. s14 + s45 + s46 + s70 are rain through a camera or door: s45 and s46 are the back-alley CCTV image, drawn as outdoor rain in the monitor grade. If you want the monitor to be an indoor object, change both to non-rain.")
    w("5. The thunder of EP1 is not planned: this take never names thunder. Say so if you want it back.")
    w("6. The woman in red keeps one pale eye visible through her hair because the take says so; the girl and the tall figure are shown without a readable face. The head-count on the monitor is stick figures (no numbers on any plate).")
    w("7. 77 scenes and 77 plates is 27 more than EP1's 50. Merging 4 to 6 pairs (c05, c09, c19 are the likeliest) lowers the plate count, not the story.")
    w("8. Names: the clerk is `Non` (the ASR reads it as several spellings) and the shop is on a canal road; confirm against the clean script.\n")
    if notes:
        w("## Notes from the checker\n")
        for n in notes:
            w(f"- {n}")
    return "\n".join(L) + "\n"


def apply_cmo_decisions(scenes):
    """Keep plate identity; subdivide long scene holds into distinct camera shots.

    Word timestamps are not a clean-script audit. Quarantine inherited SFX
    instead of silently treating speculative sounds as approved events.
    """
    for s in scenes:
        if s['rain_audio'].startswith('muffled'):
            s['rain_audio'] = 'continuous muffled bed, low pass ~1 kHz, -12 dB vs full; >=1.5 s state crossfade'
        s['sfx_candidates_unverified'] = s['sfx_cues']
        s['sfx_cues'] = []
        n = math.ceil(round(s['t1'] - s['t0'], 3) / 12)
        s['shots'] = []
        for i in range(n):
            a = round(s['t0'] + (s['t1'] - s['t0']) * i / n, 3)
            b = round(s['t0'] + (s['t1'] - s['t0']) * (i + 1) / n, 3)
            s['shots'].append(dict(id=f"{s['id']}_{i+1}", plate_id=s['plate']['id'],
                                   t0=a, t1=b, camera='wide' if i == 0 else 'detail crop',
                                   cut_note='visual reframe only; narration remains uncut'))
    assert len({s['plate']['id'] for s in scenes}) == 77
    assert all(0 < p['t1'] - p['t0'] <= 12.001 for s in scenes for p in s['shots'])


def main():
    scenes, off, clen, total = build()
    scenes = assign_rain_audio(scenes)
    # normalise sfx tuples (t, label, why) with global times
    for s in scenes:
        fixed = []
        for sf in s["sfx"]:
            t, name = sf[0], sf[1]
            why = sf[2] if len(sf) > 2 else ""
            fixed.append(dict(local_t=t, label=name, why=why,
                              global_t=round((off.get(s["chunk"], 0.0) + t), 2)))
        s["sfx_cues"] = fixed
    apply_cmo_decisions(scenes)
    errs, notes, fb, rain = check(scenes, off, clen, total)
    notes = [n for n in notes if 'long scene' not in n]
    os.makedirs(OUT, exist_ok=True)
    plan = dict(episode="ghostrules-paper-2", total_s=total, intro_s=INTRO, bumper_s=GAP, bumpers=BUMPERS,
                take_offsets=off, take_lengths_asr=clen, scenes=[{k: v for k, v in s.items() if k != "sfx"} for s in scenes],
                checks=dict(errors=errs, notes=notes, flashback_scenes=fb,
                            outdoor_rain_scenes=[s["id"] for s in rain]))
    plan['audio_policy'] = dict(rain_continuous=True, minimum_crossfade_s=1.5,
        indoor_lowpass_hz=1000, indoor_relative_db=-12,
        thunder='Optional low distant rumble, outdoor rain shots only, max 3; entire cue including tails outside dialogue; omit if no safe window',
        other_sfx='Only events explicitly named by the clean take, aligned to verified word times; candidates are NOT approved',
        character='Non (provisional fallback; clean script unavailable)',
        status='M2 blocked: clean narration, clean script and approved SFX assets required')
    json.dump(plan, open(os.path.join(OUT, "ep02_paper_plan.json"), "w"), ensure_ascii=False, indent=1)
    for s in scenes:
        s["sfx"] = [(c["local_t"], c["label"], c["why"]) for c in s["sfx_cues"]]
    text = md(scenes, off, clen, total, errs, notes)
    text = text.split('## Calls for the CMO')[0]
    text += '\n## CMO decisions applied\n\n'
    text += '- Keep muffled rain indoors throughout the storm, including chapter bumpers; draw rain outdoors only. No silence dips in the rain bed.\n'
    text += '- Thunder is optional low distant rumble only in outdoor rain shots, maximum three. Its full tail must avoid dialogue. Schedule zero until clean audio establishes safe windows.\n'
    text += '- Every other SFX must be an event explicitly named in the take, timed to verified words. All inherited cues are quarantined as `sfx_candidates_unverified` in JSON, not authorized playback cues. No smell drones, flashback stings, invented voices or other speculative sounds.\n'
    text += '- Character: Non provisionally. Clean script was not available, so absence of another name is NOT verified.\n'
    text += '- 77 unique plate assets retained. Shot subdivisions below change framing within the original scene, not plate identity. Narration is never cut at these visual boundaries.\n'
    text += '\n## Shot schedule (maximum 12 seconds)\n\n'
    for s in scenes:
        for p in s['shots']:
            text += f"- {p['id']}: {p['t0']:.3f}–{p['t1']:.3f} s; {p['plate_id']}; {p['camera']}\n"
    text += '\n## Not checked / risk\n\n'
    text += '- Clean script and clean c01–c22 narration were not present in the supplied EP2 directory. Names, ASR errors, exact event timing, take lengths and global sync remain unverified. Non is provisional, not a verified script name.\n'
    text += '- Timing remains ASR last-word plus tail estimates. Visual subshot boundaries need composition review; crops must preserve the required movers and story details.\n'
    text += '- No audio was mixed, listened to or scanned. Rain continuity, click-free seams, levels and thunder dialogue clearance are requirements, not measured passes.\n'
    text += '- Dawn rain fade remains a staging assumption; the narration does not explicitly say rain stops.\n'
    text += '- Drive helper could not access its credential file. No upload, remote MD5 verification or local media deletion was performed.\n'
    open(os.path.join(OUT, "ep02_paper_plan.md"), "w").write(text)
    print(f"{len(scenes)} scenes, total {total:.1f}s, flashback {len(fb)}, outdoor rain {len(rain)}")
    for e in errs:
        print("ERR", e)
    for n in notes:
        print("note", n)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
