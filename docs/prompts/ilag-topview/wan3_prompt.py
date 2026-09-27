"""Turn a built H3 shot into a Wan 3.0 (TopView) prompt: positional image references, at most 3,500 characters.

    python3 wan3_prompt.py n01 [n02 ...] [--token at|angle] [--out DIR]

For each shot key (o01, m04, n13, ...) writes <out>/<key>.wan3.json:
    {key, title, seconds, images: [Drive paths under Element/, in upload order], prompt, chars}
CMO_Knowledge_Wan3.0_TopView §5 is the checklist this follows: uploads in first-mention order, each @Handle replaced by
its position with the fixed name kept, the H3 studio markers replaced by a plain sound line, the house-negatives
wall dropped, and the reference descriptions shortened first if the prompt runs over 3,500 characters.
Which reference token the live Direction box accepts is not measured yet: --token picks "@Image 1" (at, the
default, what the UI inserts) or "<<<Image1>>>" (angle, TopView's own example prompts).
"""
import argparse, importlib.util, json, re
from pathlib import Path

HERE = Path(__file__).parent
# Measured 2026-09-26 on the board generator: the prompt counter reads "0 / 20000" (the 3,500 cap in the skill
# was a claim, not a measurement). Full prompts fit, so the trim levels below never trigger at this cap.
CAP = 20000

spec = importlib.util.spec_from_file_location("build", HERE / "build.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def token(i, style):
    # Measured 2026-09-26: pasted "@Image1" and "<<<Image1>>>" become reference chips; "@Image 1" with a space
    # stays plain text and attaches nothing.
    return f"@Image{i}" if style == "at" else f"<<<Image{i}>>>"


def short_ref(text):
    """The name and its job without the long look description: 'THE MOUNT, their ride' + the job sentence."""
    m = re.match(r"(THE [A-Z' ]+?)(?=[,:.]| the | a | an )", text)
    name = m.group(1).strip() if m else text.split(":")[0]
    job = re.search(r"(Take [^.]*\.|Face, body and colours only[^.]*\.|[^.]*reference only[^.]*\.)", text)
    jobtxt = job.group(1).strip() if job else "Take its look exactly."
    if jobtxt.startswith(name):
        jobtxt = jobtxt[len(name):].lstrip(" ,:").capitalize()
    return f"{name}. {jobtxt}"


SHORT_DIALOGUE_NEG = "no words beyond the quoted lines, no narration, no voiceover"
SHORT_MOUNT = ("THE MOUNT, the manta-like creature with its driftwood seat and bone-rib backrest; nothing on it gives off "
               "any light.")


def avoid(crit, level):
    if level >= 2:
        crit = crit.replace(B.DIALOGUE_NEG, SHORT_DIALOGUE_NEG)
    if level >= 6:  # THE LIGHT already says both
        for p in (", no light wider than 2 metres around the child", ", no other light source"):
            crit = crit.replace(p, "")
    return crit


def render(sc, style, shorten, level=0):
    shorten = shorten or level >= 1
    key = (sc.get("prefix", "m"), sc["n"])
    refs = []
    for i, h in enumerate(sc["refs"], 1):
        text = sc.get("ref_override", {}).get(h, REFS[h][1])
        refs.append(f"{token(i, style)}: {short_ref(text) if shorten else text}")
    beats = [b.replace("GLOW", B.GLOW) for b in (sc.get("wan3_beats") or sc["beats"])]
    snd = sc.get("sound") or B.SOUND.get(key, "silence; nobody speaks")
    parts = [f"{sc['s']} seconds, 16:9. {sc['spec']}", sc["heading"], "REFERENCES, each with a job:\n" + "\n".join(refs),
             "THE FRAME: " + sc["frame"]]
    if B.STATE.get(key):
        state = B.STATE[key].replace(B.MOUNT_DARK, SHORT_MOUNT) if level >= 3 else B.STATE[key]
        parts.append("STATE: " + state)
    if key in B.DARK_LIT:
        parts.append("THE LIGHT: " + B.LIGHT + (" " + sc["light_extra"] if sc.get("light_extra") else ""))
    if sc.get("particles") and level < 4:
        parts.append("PARTICLES: " + sc["particles"])
    # Level 7 keeps the actions only in the beats, and only when the beats name every rider.
    riders_in_beats = all(r in " ".join(beats) for r in B.RIDERS)
    if sc.get("actions") and not (level >= 7 and riders_in_beats):
        parts.append("EACH CHARACTER, ALL THROUGH THE SHOT (each busy with their own action, never all the same):\n"
                     + "\n".join("- " + (a.split(";")[0].rstrip(",") + "." if level >= 5 else a) for a in sc["actions"]))
    parts += ["WHAT HAPPENS:\n" + "\n".join(beats),
              f"Sound: only the sounds the characters make themselves: {snd}. No music, no ambient sound.",
              B.GRADE[sc.get("grade_override", sc["grade"])].split(" Photographed")[0] if level >= 2
              else B.GRADE[sc.get("grade_override", sc["grade"])],
              "Avoid: " + avoid(sc["crit"], level) + "."]
    return "\n\n".join(parts)


# CEO 2026-09-26: a free generation is counted per generation, not per second, so each one carries up to 30 s:
# several shots in cut order, joined by hard cuts (Wan3 shot-level direction), at most 10 pictures.
# CEO 2026-09-26 on the free five: "ฉากแรกยาว 30s ... ต่อมาคือฉากยาวดำน้ำเจอแมงกะพรุน ... Fantasy มากที่สุด ... Slow motion ...
# ฉากคลื่นซัดแบบรุนแรงเป็นฉากยาวได้เลย ... ฉากจับปลา Long Take จนอสุรกายโผล่ ... ที่เหลืออะไรก็ได้". The free five are g1, g3,
# g4, g5, g6 (fired first); g2 and g7 are paid. A group need not follow cut order: the edit puts every shot back.
GROUPS = {
    "g1": ["o01", "o02"],                 # free: the opening, no new story, stretched to 30 s
    "g3": ["n02", "n03"],                 # free: the dive into the glass sea, a fairy tale in slow motion
    "g4": ["m06", "n04", "n12", "n05"],   # free: the pillars, the line, the talk, the crossing
    "g5": ["n06", "n07", "n13"],          # free: the light, a long violent wave, the waking
    "g6": ["x_longtake"],                 # free: one long take, the catch until the creature's eyes open
    "g6r2": ["x_longtake"],               # retake (CEO 2026-09-26): take 1 had a boat, no mount; all three look up at the end
    "g2": ["o03", "o04", "m04"],          # paid
    "g7": ["n01", "n10", "m13"],          # paid, natural length (the three wide/aerial shots)
    "g8": ["x_shadow"],                   # CEO 2026-09-26: the shadow alone, full-frame, very slow, edge to edge
    # CEO 2026-09-26 ("ไม่มี กระเบน ถูกแอดมา ... ทำเฉพาะจุด ไม่แก้ 30s"): G5 carried no picture of THE MOUNT and came
    # back with the riders on a dark rock in all three shots. Each shot is refired alone, only as long as the cut needs.
    "g5a": ["n06"],
    "g5b": ["n07"],
    "g5c": ["n13"],
}
# Wan3-only pictures (not H3 entities). The creature seen from above: the CEO's design sheet creature_v2, panel
# "01 FROM ABOVE", cropped to one picture without its label (a sheet renders as a grid).
REFS = dict(B.REF, **{
    "@CreatureAbove": ("Character/crt_creature_above.png",
                       "THE CREATURE SEEN FROM ABOVE, the only picture of its body: take ONLY its broad, flat, rounded "
                       "outline and its size against the tiny mount, as a dark shadow deep under the water; nothing of "
                       "its eyes or their glow, which stay closed and unseen in this shot."),
})

# H3 cut 3 dropped the @Manta picture after the crossing (its lamps are lit) and described THE MOUNT in words
# (B.MOUNT_DARK). Wan3 does not draw a mount from words: G5 came back with the riders on a rock, G6 take 1 on a boat.
# On Wan3 every on-mount shot carries the picture, with the dead lantern beside it to show what "dead lamps" means.
MANTA_JOB = ("THE MOUNT, the manta the riders sit on: take its manta body, colours, whip tail and the driftwood seat "
             "with its bone backrest exactly; every lamp on the seat is dead and dark, like the dead shell in the "
             "picture of THE DEAD LANTERN, and nothing on THE MOUNT gives off any light.")
DEAD_LANTERN_JOB = ("THE DEAD LANTERN: how every lamp on THE MOUNT's seat looks now, an empty dark shell with no light "
                    "at all.")
MOUNT_SEEN = ("THE MOUNT is the manta in the picture of THE MOUNT, with its driftwood seat and bone backrest; every "
              "lamp on the seat is dead and dark and nothing on THE MOUNT gives off any light.")


def with_mount(sc):
    """Attach THE MOUNT's picture to an on-mount shot that lacks it (Wan3 only; the H3 files are untouched)."""
    key = (sc.get("prefix", "m"), sc["n"])
    if key not in B.ON_MOUNT or "@Manta" in sc["refs"]:
        return sc
    state = (sc.get("state") or B.STATE.get(key) or "").replace(B.MOUNT_DARK, MOUNT_SEEN)
    over = dict(sc.get("ref_override", {}), **{"@Manta": MANTA_JOB, "@LanternDark": DEAD_LANTERN_JOB})
    return dict(sc, refs=["@Manta", "@LanternDark"] + sc["refs"], ref_override=over, state=state,
                crit=sc["crit"] + ", no rock or reef under the riders, no boat, no raft, no canoe, no lit lamp")


SHADOW_TAKE = dict(
    prefix="x", n=1, slug="the-shadow-passes", title="THE SHADOW PASSES, FROM HIGH ABOVE", s=15,
    grade="DARK", grade_override="DARK_GLOW",
    spec="ONE LOCKED SHOT, NO CUTS. Straight down from very high above, the whole 15 seconds; the camera never moves.",
    refs=["@CreatureAbove", "@Manta", "@Young", "@Turning"],
    ref_override={"@Manta": "THE MOUNT: only its manta shape and the driftwood seat, tiny from this height; every lamp "
                            "on it is dead and dark and nothing on it glows.",
                  "@Young": "THE YOUNG ONE: only the child's warm golden glow, a tiny point of light from this height.",
                  "@Turning": B.TURNING_IN_CIRCLE},
    heading="THE SHADOW. From very high, THE MOUNT is a tiny speck of light on a black sea, and something as big as "
            "the whole frame slides beneath it, very slowly.",
    frame="Top-down from very high: a vast flat black sea in the rain fills the frame; THE MOUNT is a tiny speck in the "
          "centre inside its tiny circle of gold light.",
    state="THE MOUNT is the manta in the second picture, so small it is barely more than a point; nothing on it "
          "glows. The sea surface is flat and calm under the rain.",
    particles="rain falling toward the flat water, a faint shimmer across the surface, tiny fish glints in the circle.",
    beats=["[0s] GLOW Seen straight down from very high, THE MOUNT is a tiny glowing speck in the centre of a flat "
           "black sea in the rain; a few tiny fish shadows glint inside its circle of light.",
           "[2s] At the left edge of the frame, deep under the surface, an enormous dark shadow begins to slide in: the "
           "broad, flat, rounded body of THE CREATURE, so big that it covers the frame from top to bottom. It moves "
           "very, very slowly, left to right.",
           "[6s] The shadow passes directly beneath the tiny speck of light, filling the whole frame; the tiny fish "
           "shadows scatter in every direction and vanish; the speck is a grain of sand on its back.",
           "[10s] Still very slowly, the shadow's far edge crosses the frame and slides out past the right edge.",
           "[13s] The shadow is gone. The flat black sea is empty; only the tiny speck of light remains."],
    sound="the faintest startled gasp; no words",
    crit=B.NO_WORDS + ", no camera move, no cut, no ray shape, no wings, no fins, no tail, no fish shape, no eyes, no "
         "glow from the creature, no face, no surfacing, no waves, no boat, no other light source",
)
LONG_TAKE = dict(
    prefix="x", n=0, slug="the-catch-to-the-eyes", title="ONE LONG TAKE: THE CATCH UNTIL THE EYES OPEN", s=30,
    grade="DARK", grade_override="DARK_GLOW",
    spec="ONE CONTINUOUS TAKE, NO CUTS. It starts as a medium shot beside THE MOUNT at the surface and, without any cut, "
         "slowly pulls back and rises until THE MOUNT is small in the lower third with the far black water filling "
         "the frame above; then it holds.",
    refs=["@Manta", "@Strong", "@Young", "@Elder", "@Turning", "@Mountain", "@Eye"],
    ref_override={"@Manta": "THE MOUNT, their ride: take its manta-like body about 4 m across the wings, the sea-green "
                            "mottled back, the long thin whip tail and the hand-built driftwood seat with its bone-rib "
                            "backrest exactly. In this shot every lamp and grass tuft on the seat is dead and dark and "
                            "nothing on THE MOUNT glows.",
                  "@Turning": B.TURNING_IN_CIRCLE,
                  "@Eye": "THE CREATURE, the only picture of it: take its broad flat smooth dark head, its two enormous "
                          "pale yellow-green eyes with thin vertical slit pupils and its scale exactly; nothing of the "
                          "light around it."},
    light_extra="Far beyond the circle the rising mountain is only a vast blacker shape against the dark; its two eyes, "
                "when they open, glow pale yellow-green on their own, the only other light in this shot.",
    heading="THE CATCH, AND WHAT WAS WATCHING. One unbroken take from their first fish to the creature's eyes. THE "
            "THREE RIDERS are on the seat on the back of THE MOUNT, the manta, the whole time; there is no boat.",
    state="THE MOUNT is the manta in the first picture; every lamp and grass tuft on its seat is dead and dark and "
          "nothing on it glows. " + B.WET,
    frame="Starts medium, beside THE MOUNT at the surface: THE STRONG ONE leaning over the edge of the seat, THE YOUNG "
          "ONE glowing beside him, THE ELDER behind; ends wide from behind and above, THE MOUNT small on flat black "
          "water in the rain.",
    particles="rain, water splashing up as hands go in, golden motes around THE YOUNG ONE, mist over the flat water.",
    actions=["THE STRONG ONE, front perch: chases a fish shadow with both hands and snatches it out, holds it up "
             "laughing, then lies across the front of the seat grabbing at more fish with both arms in the water, "
             "completely absorbed; he only looks up when THE YOUNG ONE shakes his shoulder; when the eyes open he stops, "
             "rises onto his knees, hands dripping, and stares up at THE CREATURE.",
             "THE YOUNG ONE, middle, glowing: points where the fish goes, jumps up and down cheering at the catch, "
             "then sits on the edge kicking both feet in the water to herd fish, giggling; notices THE ELDER staring "
             "for a long time, follows THE ELDER's gaze, goes still, then shakes THE STRONG ONE's shoulder hard; when the "
             "eyes open the child clutches THE ELDER's arm and stares up at THE CREATURE.",
             "THE ELDER, back: grips THE STRONG ONE's kelp belt so THE STRONG ONE cannot fall in, claps him on the back "
             "at the catch, rinses the fish over the side, then stops, slowly lifts his head and stares ahead at the "
             "far water; when the eyes open he lets the fish slip from his hands into the water and stares up at THE "
             "CREATURE."],
    beats=["[0s] GLOW THE STRONG ONE leans far over the edge chasing a fish shadow with both hands; THE ELDER grips "
           "THE STRONG ONE's kelp belt; THE YOUNG ONE leans out beside THE STRONG ONE and points.",
           "[4s] THE STRONG ONE lunges and snatches out one dark glossy silver-black fish; they cheer, each in their own "
           "way: THE YOUNG ONE jumps up and down, THE ELDER claps THE STRONG ONE on the back, THE STRONG ONE holds the "
           "fish up, laughing.",
           "[9s] Without a cut the camera slowly pulls back and rises. THE STRONG ONE lies across the front grabbing "
           "at more fish with both arms in the water; THE YOUNG ONE kicks both feet in the water, giggling; THE ELDER "
           "rinses the fish over the side.",
           "[16s] Far ahead the flat sea bulges and a vast smooth dark shape slowly rises out of it like a mountain, "
           "until it fills the upper half of the frame, water pouring off it. THE ELDER stops and stares at it; the "
           "other two keep fishing.",
           "[22s] THE YOUNG ONE notices THE ELDER staring for a long time, follows the gaze, goes still, then shakes "
           "THE STRONG ONE's shoulder; THE STRONG ONE looks up, hands still in the water.",
           "[25s] High on the mountain two enormous eyes open: pale yellow-green, thin vertical slit pupils, each "
           "bigger than their whole village, looking down at them.",
           "[27s] All three stop what they are doing and stare up at THE CREATURE: THE STRONG ONE rises onto his "
           "knees, hands dripping; THE YOUNG ONE clutches THE ELDER's arm; THE ELDER lets the fish slip into the water. "
           "They stay like that, looking up, until the shot ends."],
    sound="splashes, THE STRONG ONE's effort, wordless cheering and laughter, THE YOUNG ONE's giggle, then THE YOUNG "
          "ONE's sharp gasp, then total silence as the eyes open; no words",
    crit=B.NO_WORDS + ", no boat, no raft, no canoe, no hull, no cut, no net, no spear, no hook, no one falling in, no "
         "roar, no teeth, no third eye, no waves, "
         "no light wider than 2 metres around the child, no eyes before the last beat",
)
# CEO 2026-09-26 on the opening: the run to THE CHIEF (about 9 s of G1, one lateral tracking take) becomes 30 s, "Multicut
# ตัดสลับแบบรวดเร็ว ที่ไม่ได้ Focus แต่ตัวเขา ... มุม Focus จุดเล็ก เป็น LongShot ... ใช้ 0.5 0.8". Many more obstacles, every
# cut 0.5-0.8 s, detail inserts and long shots between the shots of him. It ends where G1 is at about 9 s (he runs up
# onto the platform where THE CHIEF and THE STRONG ONE haul the net), so the edit cuts from this straight into G1's
# arrival and lines. Prefix "r" keeps it off the mount guard: nobody rides THE MOUNT here.
RUN_CUTS = [
    (0.0, "Extreme wide aerial from very high: the whole village of giant mangrove trees on glass-clear water under the "
          "huge moon; a tiny yellow figure bursts out onto a walkway."),
    (0.8, "Extreme close-up: THE RUNNER's bare webbed feet slam onto the wet planks, water flicking up."),
    (1.4, "Close-up, handheld: THE RUNNER's face twisted with fear, gill frills flared pale, panting."),
    (2.0, "Low angle from under the walkway, looking up between the planks: his feet flash over the gaps, drops falling "
          "toward the lens."),
    (2.6, "Medium, fast side tracking: THE RUNNER runs flat out left to right along the walkway."),
    (3.3, "Extreme close-up: his shell necklace bouncing against his chest."),
    (3.8, "Medium: a kelp net hung to dry right across the walkway; he ducks under it at full speed."),
    (4.5, "From behind: the net still swinging where he passed, THE RUNNER racing away."),
    (5.1, "Close-up: a villager's head snaps round as THE RUNNER blurs past in the foreground."),
    (5.6, "Wide, long lens from far across the water: a tiny figure running along a walkway between two giant trees."),
    (6.4, "Medium, low: two villagers carry a long wooden pole across the walkway; he slides under it on the wet planks."),
    (7.2, "Extreme close-up: his hands slap the planks as he springs back up."),
    (7.7, "Straight down from a drone, tracking: he zigzags between villagers crossing a platform."),
    (8.4, "Medium: shell pots stacked on the walkway; he vaults them and one topples."),
    (9.1, "Extreme close-up: the pot splashes into the glass-clear water."),
    (9.6, "Wide, side on: he leaps the gap between two platforms, a dark shape against the huge moon."),
    (10.4, "Underwater, looking up through the glass-clear water: his shadow flies across the bright surface above."),
    (11.1, "Extreme close-up: his feet land hard on the far edge; a loose plank drops away into the water."),
    (11.7, "His point of view, running: the walkway rushing at the lens, rope rails whipping past, a villager jumping aside."),
    (12.4, "Close-up: a hanging seed-pod lamp he clips with his shoulder, swinging hard."),
    (12.9, "Medium, low: a curved branch across the path; he ducks under it, gill frills brushing the leaves."),
    (13.5, "Wide, from a high branch looking down: he hits a swaying rope bridge and the whole bridge bucks under him."),
    (14.3, "Extreme close-up: a missing slat in the rope bridge; his foot skips over the gap."),
    (14.8, "Close-up from the front, the camera racing backward: panting, eyes wide, tearing across the bridge."),
    (15.4, "Medium: a small child runs the other way; he twists sideways to miss her."),
    (16.0, "Medium: he bursts through a hanging curtain of drying kelp strips beside a hut roof of glowing green grass."),
    (16.7, "Low angle: the bridge ends at a tall ladder lashed to a giant stilt root; he grabs it."),
    (17.3, "Extreme close-up: his hands grabbing the rungs, hand over hand."),
    (17.8, "Straight down: he climbs fast, the glass-clear water far below him."),
    (18.5, "Wide, long lens from across the water: a tiny figure high on the giant root."),
    (19.2, "Medium: at the top he grabs a kelp rope hanging from a branch and swings out over the water."),
    (20.0, "Wide, side on, tracking: the long arc of the swing over glass-clear water, the moon behind him."),
    (20.8, "Extreme close-up: the kelp rope creaking in his fist."),
    (21.3, "Low, from just above the water: he drops onto a lower walkway and skids, water spraying."),
    (22.0, "Close-up: an old grey villager steps back, startled."),
    (22.5, "Medium tracking: he gets his footing and sprints again."),
    (23.1, "Extreme close-up: his panting mouth, drops flying off his gill frills."),
    (23.6, "Wide aerial: the walkway runs ahead to a wide platform where two figures haul a net out of the water."),
    (24.4, "Medium: he leaps a coil of kelp rope lying across the planks."),
    (25.0, "Extreme close-up: his feet skid on the wet planks and push off again."),
    (25.5, "Close-up: THE STRONG ONE's big green hands hauling the wet net, hand over hand."),
    (26.2, "Close-up: THE CHIEF under his gemstone crown, hauling the net, not yet looking up."),
    (26.8, "Low, from the front, the camera racing backward: THE RUNNER sprinting straight at the lens, desperate."),
    (27.5, "Wide, from behind THE RUNNER: he runs up a short ramp onto the wide platform where THE CHIEF and THE STRONG ONE "
           "haul the fishing net out of the water, and slows, chest heaving. This last shot holds until the end."),
]
RUN_MULTICUT = dict(
    prefix="r", n=1, slug="the-run-multicut", title="THE RUN, FAST MULTI-CUT", s=30, grade="DAY", montage=True,
    spec=(f"A FAST-CUT ACTION MONTAGE of {len(RUN_CUTS)} shots joined by hard cuts at the times given: every cut 0.5 to "
          "0.8 seconds, only the last shot longer. Each shot is a new angle: extreme close-ups of small details, long "
          "shots from far away, low angles, straight-down drone shots, his point of view, underwater looking up; the "
          "camera is not only on his face. Real speed all through; no slow motion, no dissolve, no crossfade."),
    refs=["@RunnerY", "@Village", "@Villagers", "@Villagers2", "@Chief", "@Strong"],
    heading="MORNING IN THE VILLAGE. A young fisherman runs in panic across the whole village, over and under everything "
            "in his way, to reach THE CHIEF, who is out hauling the fishing net with THE STRONG ONE.",
    frame="The village in every shot: wooden walkways, rope bridges, ladders, glowing grass, glass-clear water below; "
          "the same THE RUNNER, mustard-yellow, in every shot of him.",
    particles="water flicking up from his feet, sea spray glinting, a few glowing specks drifting in the air.",
    beats=[f"[{t:g}s] {c}" for t, c in RUN_CUTS],
    sound="THE RUNNER's loud ragged panting all through, his bare feet slapping the wet planks, the splash of his "
          "steps, his grunt on each jump and landing; no words",
    crit=B.NO_WORDS + ", no slow motion, no dissolve, no crossfade, no second runner, no one falling into the water, no "
         "weapon, no orange skin on the runner, no blue skin on the runner, no calm faces, no smile, no grin, no fish, no "
         "boat, no metal, no split screen, no text",
)
# The same run as COVERAGE for the edit (researched 2026-09-26): Alibaba's Wan 3.0 guide says "4~6 seconds per shot, with
# timestamp annotations" and "Shot 1 [0-3 s] ..., Hard cut transition"; ByteDance advises chases and montages be made as
# separate shots and cut together in the edit; no vendor documents sub-second cuts, and no Wan3 clip of ours held more
# than 4. So ten 3-second shots, each a new angle with its own obstacle and a fast camera, which the CEO cuts to
# 0.5-0.8 s pieces and intercuts in CapCut, with G1's own 9 s of run as more pieces.
RUN_COVER_SHOTS = [
    "Extreme wide aerial from very high, the drone diving fast toward the village of giant mangrove trees on glass-clear "
    "water under the huge moon; a tiny yellow figure bursts out onto a walkway and the camera swoops down to him running.",
    "Low angle from under the walkway, looking up between the planks, tracking fast: his bare webbed feet slam over the "
    "gaps, drops falling toward the lens; then he ducks under a kelp net hung to dry right across the walkway.",
    "Fast side tracking at his height, handheld: two villagers carry a long wooden pole across his path; he slides under "
    "it on the wet planks and springs straight back up, shell necklace bouncing, villagers' heads snapping round.",
    "Straight down from a drone, tracking: he zigzags between villagers crossing a platform and vaults a stack of shell "
    "pots; one pot topples and splashes into the glass-clear water.",
    "Wide, side on, long lens from far across the water: he leaps the gap between two platforms, a dark shape against "
    "the huge moon, lands hard, and a loose plank drops away into the water behind him.",
    "Underwater, looking up through the glass-clear water: his shadow races across a swaying rope bridge above; the whole "
    "bridge bucks under him and one foot punches through a missing slat, then he is gone.",
    "His point of view, running: the walkway rushing at the lens, rope rails whipping past; he clips a hanging seed-pod "
    "lamp that swings hard, ducks under a low branch, and a small child darts across in front of him.",
    "Low angle up a giant stilt root: he climbs a tall ladder hand over hand, fast, grabs a kelp rope at the top and "
    "swings out over the water in a long arc.",
    "Close-up from the front, the camera racing backward: his face twisted with fear, panting, drops flying off his gill "
    "frills; he drops onto a lower walkway in a skid, water spraying, and sprints on.",
    "Wide, from behind THE RUNNER: he runs up a short ramp onto the wide platform where THE CHIEF and THE STRONG ONE "
    "haul the fishing net out of the water, and slows, chest heaving.",
]
RUN_COVER = dict(
    RUN_MULTICUT, n=2, slug="the-run-coverage", title="THE RUN, TEN FAST SHOTS",
    spec=(f"{len(RUN_COVER_SHOTS)} SHOTS joined by hard cuts (Hard cut transition), 3 seconds each; every shot a new "
          "angle and a new obstacle, the camera moving fast in every shot, the action never pausing. Real speed all "
          "through; no slow motion, no dissolve, no crossfade."),
    beats=[f"Shot {i} [{3 * (i - 1)}-{3 * i}s] {c}" for i, c in enumerate(RUN_COVER_SHOTS, 1)],
)
# CEO 2026-09-26, after seeing both: separate shots drift too much ("ถ่ายแยกไม่ได้มีโอกาสเพี้ยนสูงมาก"); ONE 30-s clip in the
# pacing of the Seedance parkour example he picked (youmind parkour-multi-character-rooftop-7868: 8 cuts in 14 s,
# 1.5-2 s each, wide-angle action lens, low rear tracking, handheld retreating, overhead, drone, a camera circling in
# mid-air). Ends when THE RUNNER reaches THE CHIEF and THE STRONG ONE, before any line is spoken. Every obstacle has a
# reason to be there (the morning's own work: nets drying after the dawn catch, a beam carried to mend a roof, rope
# being made, a bridge snapped in last night's wind). A broken bridge, a swimmer's racing dive, a streamline glide and
# a climb out on his own momentum (never floating up), one collision with "Sorry!" and on without losing speed.
RUN_PARKOUR_CUTS = [
    (0.0, 1.8, "Drone from diagonal rear above, dropping fast: the village of giant mangrove trees on glass-clear water in "
               "the morning; THE RUNNER sprints out along a wooden walkway and the camera dives in behind him."),
    (1.8, 3.6, "Low angle from the front, handheld, the camera racing backward just ahead of him: his face twisted with "
               "fear, gill frills flared pale, bare webbed feet pounding the planks."),
    (3.6, 5.4, "Lateral tracking, wide-angle lens: the fishermen's kelp nets hang across the walkway to dry after the dawn "
               "catch; he drops into a slide under the lowest net without slowing, the mesh brushing his back, and "
               "springs up running."),
    (5.4, 7.2, "Low-angle rear tracking: two villagers carry a long driftwood beam across the walkway to mend a hut roof; "
               "he plants both hands on the beam and kong-vaults over it, the two villagers flinching."),
    (7.2, 9.0, "Overhead moving camera, straight down: a villager is rolling a big coil of new kelp rope across the planks; "
               "he hurdles the coil and weaves between two more villagers."),
    (9.0, 11.0, "Front low angle, wide: ahead of him a rope bridge between two giant trees snapped in last night's wind; its "
                "middle is gone, torn slats and frayed ropes hanging down into the water. A villager at the near end, "
                "holding new planks for the repair, waves both arms at him to stop. He does not slow down."),
    (11.0, 12.8, "Fast side tracking: at the broken end he launches a competitive swimmer's racing dive: body stretched "
                 "long and straight, arms extended past his head, hands together, gill frills flat, flying out and down "
                 "at a shallow angle toward the water."),
    (12.8, 14.6, "The camera plunges in with him: a clean entry with little splash, then underwater in the glass-clear "
                 "turquoise water he glides in a tight streamline and gives two strong dolphin kicks, bubbles streaming "
                 "off him, sun shafts cutting down through the water."),
    (14.6, 16.4, "Low, at the water surface: carried by that speed he surfaces beside a giant stilt root on the far side, "
                 "grabs a ladder rung with both hands and, in one swing of his body, pulls himself up and out onto the "
                 "walkway, water pouring off him."),
    (16.4, 18.2, "Handheld, retreating in front of him: soaking wet, he is already running at full speed again, water "
                 "flying from his gill frills and his kelp belt."),
    (18.2, 20.0, "Tracking round the corner of a hut: he runs shoulder-first into a plump villager in peach-coral carrying "
                 "an armful of drying kelp; the kelp flies up; he catches her arm to steady her, gasps \"Sorry!\", and is "
                 "already running on."),
    (20.0, 21.8, "From behind the villager: she stands in the falling kelp staring after him as he races away down the "
                 "walkway without losing any speed."),
    (21.8, 23.6, "Drone from diagonal rear above: planks have been lifted out of the walkway for mending, leaving gaps; he "
                 "precision-jumps from beam to beam across them."),
    (23.6, 25.4, "Extreme close-up tracking at plank level: his wet bare feet slap the planks, skid round a turn and push "
                 "off again."),
    (25.4, 27.4, "Wide, long lens from far away: at the edge of the village THE CHIEF and THE STRONG ONE stand on a wide "
                 "fishing platform hauling a net out of the water; the tiny figure of THE RUNNER races along the walkway "
                 "toward them."),
    (27.4, 30.0, "Low-angle rear tracking, slowing down: he runs up onto the platform and stumbles to a stop in front of "
                 "THE CHIEF and THE STRONG ONE, chest heaving, dripping; the two of them stop hauling and turn to look at "
                 "him. Nobody speaks. Hold on the three of them to the end."),
]
RUN_PARKOUR = dict(
    RUN_MULTICUT, n=3, slug="the-run-parkour", title="THE RUN, PARKOUR CUTS",
    spec=(f"{len(RUN_PARKOUR_CUTS)} CUTS joined by hard cuts at the times given, about 2 seconds each, cinematic freerunning "
          "footage; a wide-angle action lens, the camera moving fast in every cut and following him, a new angle every "
          "cut. Real speed all through; no slow motion, no dissolve, no crossfade."),
    heading="MORNING IN THE VILLAGE. A young fisherman runs in panic across the whole village, through the morning's work "
            "going on around him, to reach THE CHIEF, who is out hauling the fishing net with THE STRONG ONE. Use the "
            "pictures as absolute character references: keep each character's face, body, height, skin colour, gill "
            "frills and outfit the same in every cut; never swap or blend two people.",
    frame="The village in every cut: wooden walkways, rope bridges, ladders, glowing grass, glass-clear water below; the "
          "same THE RUNNER, mustard-yellow, in every cut of him. From cut 8 on he is soaking wet.",
    quality=("Live-action film quality, world-class freerunning: real centre-of-gravity shifts, muscles working, natural "
             "landing impacts, kelp rope and shell necklace swinging; a sharp background, motion blur only in the fastest "
             "moves. The dive and the climb out are real athletic moves: he never floats, hovers or flies."),
    beats=[f"CUT {i} [{a:g}-{b:g}s] {c}" for i, (a, b, c) in enumerate(RUN_PARKOUR_CUTS, 1)],
    sound=("THE RUNNER's loud ragged panting all through, his bare feet slapping the planks, the splash of the dive and "
           "the rush of water, his grunt on each vault and landing, the thump of the collision, and one gasped word: "
           "\"Sorry!\""),
    crit=B.DIALOGUE_NEG + ", no slow motion, no dissolve, no crossfade, no floating, no hovering, no flying up out of the "
         "water, no belly flop, no unnatural landings, no face distortion, no extra limbs, no duplicate people, no body "
         "fusion, no warping, no second runner, no weapon, no orange skin on the runner, no blue skin on the runner, no "
         "smile, no grin, no fish, no boat, no metal, no split screen, no text, no anime style, no CG look",
)
# G9p came back with HUMAN villagers (the two carrying the beam, two behind the nets): Wan3 drops the house-negatives
# wall, and "two villagers" with no picture tied to them drew people. Every new Wan3 prompt carries this line.
NO_HUMANS = "no humans, no human faces, no human hair, no human skin; everyone is of the same gilled people"
# CEO 2026-09-27 on the wave (N7): "MultiCut 15s ... 3 ตัวละครนี้ ดูพยายามที่จะผ่านมันไปให้ได้ มีการจับเชือกไว้แน่น โต้คลื่นได้ 1 ลูก
# แต่ถัดไปมันใหญ่กว่านั้นมาก แล้วให้คลื่นซัดมาที่จอ ปิดจบด้วยจอดำ". Eight cuts of about 2 s in the parkour pacing he chose
# for the run. Prefix "x" puts it under the mount guard, so THE MOUNT's picture cannot be left out again (G5).
# The second wave needs something to show its size in the dark: violet lightning far behind it, taken from the wave
# plate itself, is the one light allowed besides the child.
WAVE_CUTS = [
    (0, 2, "GLOW Wide and low from the water behind THE MOUNT: in the black storm sea a big wave rises ahead of them; "
           "THE THREE RIDERS crouch low on the seat, bracing."),
    (2, 4, "Close-ups, hands on the ropes: THE STRONG ONE's big green hand wraps the kelp rope twice round his fist; "
           "THE ELDER's hand grips the seat's rope lashing; THE YOUNG ONE's small webbed hands clutch the bone-rib "
           "backrest, knuckles tight."),
    (4, 6, "Side tracking, wide-angle lens, the camera shaking hard: THE MOUNT climbs the steep face of the first wave; "
           "THE STRONG ONE drives THE POLE down and shouts \"Hold on!\"; all three lean forward into the climb."),
    (6, 8, "From above the crest: THE MOUNT bursts over the top and slams down the back of the wave, spray exploding "
           "through the gold light; the riders are thrown up off the seat and held on only by the ropes, then land "
           "back on it. They made it through."),
    (8, 10, "Close-up, THE YOUNG ONE's face lit gold, dripping: relief, then the eyes go wide as the child looks up past "
            "the camera."),
    (10, 12, "Low and wide from behind the riders, looking ahead: the next wave rises out of the dark, many times bigger "
             "than the first, a black wall as tall as a mountain filling the whole frame above them; far behind it "
             "violet lightning flashes and shows its size. THE MOUNT is tiny at its foot."),
    (12, 13.5, "From in front, low, looking back at THE THREE RIDERS with the wave curling high above them: its lip "
               "breaks and the whole wall crashes down toward the camera."),
    (13.5, 15, "The water slams straight into the lens and the frame goes completely black; it stays black to the end."),
]
WAVE_MULTICUT = dict(
    prefix="x", n=3, slug="the-wave-multicut", title="THE WAVES, FAST MULTI-CUT", s=15, montage=True, lit=True,
    grade="DARK", grade_override="DARK_GLOW",
    spec=(f"{len(WAVE_CUTS)} CUTS joined by hard cuts at the times given, about 2 seconds each; a wide-angle lens, the "
          "camera shaking and moving with the sea in every cut, a new angle every cut. Real speed; no slow motion, no "
          "dissolve, no crossfade."),
    refs=["@Manta", "@LanternDark", "@Strong", "@Young", "@Elder", "@Pole", "@Waves", "@Turning"],
    ref_override={"@Manta": MANTA_JOB, "@LanternDark": DEAD_LANTERN_JOB, "@Turning": B.TURNING_IN_CIRCLE,
                  "@Waves": "THE WAVES: take the colossal curling walls of dark water, their size and shape, and the "
                            "violet lightning far behind them; not the cyan and magenta glow inside them."},
    heading="THE WAVES. On the back of THE MOUNT, THE THREE RIDERS fight to get through a storm sea: they ride over "
            "one big wave, and the next is far bigger. Keep each rider's face, body and colours the same in every cut.",
    frame="THE MOUNT small on the black storm sea with THE THREE RIDERS on its seat: THE STRONG ONE on the front perch "
          "with THE POLE, THE YOUNG ONE glowing in the middle, THE ELDER at the back holding the child.",
    state=MOUNT_SEEN + " " + B.WET,
    light_extra="The only other light: violet lightning flashing far off behind the second wave, an instant at a time.",
    particles="heavy rain, spray torn off the wave crests, foam tumbling through the gold light.",
    quality=("Live-action film quality: real weight, the riders' bodies thrown by the sea and pulling themselves back "
             "down by the ropes, water pouring off everything; motion blur only in the fastest moves."),
    actions=["THE STRONG ONE, front perch: rope wrapped round one fist, drives THE POLE down to steer THE MOUNT up the "
             "wave, jaw clenched, shouting once; never lets go.",
             "THE YOUNG ONE, middle, glowing: clings to the bone-rib backrest with both hands, eyes squeezed shut on "
             "the first wave, then opens them and looks up at the second.",
             "THE ELDER, back: one arm round the child, the other hand locked on the seat's rope lashing, pulling them "
             "both down onto the seat."],
    beats=[f"CUT {i} [{a:g}-{b:g}s] {c}" for i, (a, b, c) in enumerate(WAVE_CUTS, 1)],
    sound="the shout above, spoken once; the riders' gasps and grunts of effort as the first wave throws them; THE YOUNG "
          "ONE's sharp gasp at the second wave; then silence in the black",
    crit=B.DIALOGUE_NEG + ", no slow motion, no dissolve, no crossfade, no boat, no raft, no rock, no lit lamp, no light "
         "wider than 2 metres around the child except the far lightning, no cyan or magenta glow in the water, no one "
         "falling off before the last cut, no floating, no extra limbs, no duplicate riders, no warping, no text, no "
         "split screen, " + NO_HUMANS,
)
GROUPS["g5w"] = ["x03"]

# CEO 2026-09-27, the last credits (6.8 on a fresh tab; he thought 10): the bookend that opens AND closes the film —
# black with rain and thunder, lightning reveals the storm sea from high above, a wave crashes over THE THREE RIDERS
# on THE MOUNT in slow motion, back to black. "ไม่มีบทพูด ไม่มี Background music มีแค่เสียง ... ฟ้าร้อง และฟ้าผ่า".
# 7 s at 720p + 4K = 6.3 credits, the most that fits. It is the one shot whose sound is not the characters' own.
STORM_BOOKEND = dict(
    prefix="x", n=4, slug="the-storm-bookend", title="THE STORM, FROM HIGH ABOVE, IN SLOW MOTION", s=7,
    grade="DARK", grade_override="DARK_GLOW", lit=True, longtake=True,
    spec="ONE CONTINUOUS TAKE, NO CUTS, ALL IN SLOW MOTION at about half speed. Straight down and steep from very high "
         "above the sea, the camera sinks very slowly toward the water; no cut, no zoom.",
    refs=["@Manta", "@LanternDark", "@Strong", "@Young", "@Elder", "@Waves", "@Turning"],
    ref_override={"@Manta": MANTA_JOB, "@LanternDark": DEAD_LANTERN_JOB, "@Turning": B.TURNING_IN_CIRCLE,
                  "@Waves": "THE WAVES: take the colossal walls of dark water, their size and shape, and the violet "
                            "lightning; not the cyan and magenta glow inside them."},
    heading="THE STORM. Out of total darkness, lightning shows a vast black storm sea from high above, and a wave as "
            "big as a hill falls on THE THREE RIDERS on THE MOUNT, tiny inside the child's gold light.",
    frame="From very high above, looking steeply down: black heaving water filling the frame, huge waves marching "
          "across it; THE MOUNT a tiny shape near the centre with THE THREE RIDERS on its seat inside a small circle "
          "of gold light.",
    state=MOUNT_SEEN + " " + B.WET,
    light_extra="The only other light: violet lightning, a few flashes, each lighting the whole sea for an instant.",
    particles="sheets of rain falling toward the sea, spray torn off the crests, foam hanging in the air in slow motion.",
    beats=["[0s] The frame is completely black; only rain and far thunder are heard.",
           "[1s] A flash of violet lightning lights everything for an instant: from very high above, a vast black storm "
                 "sea with huge waves marching across it, and near the centre THE MOUNT, tiny, THE THREE RIDERS "
                 "holding on, THE YOUNG ONE's small gold glow around them. GLOW",
           "[3s] In slow motion a colossal wave rears up beside them, taller than a hill, its crest curling over the "
                 "small circle of gold light.",
           "[4.5s] Another flash of lightning. The wave falls on THE MOUNT and THE THREE RIDERS in slow motion, spray "
                   "and foam exploding up toward the camera; the gold light vanishes under the water.",
           "[6s] Darkness returns; the frame goes completely black and stays black to the end."],
    sound_line="Sound: only the storm — heavy rain, rolling thunder and the crack of each lightning strike. No voices, "
               "no words, no music, no score.",
    crit=B.NO_WORDS + ", no music, no score, no cut, no boat, no raft, no rock, no lit lamp, no cyan or magenta glow in "
         "the water, no light wider than 2 metres around the child except the lightning, no text, no split screen, "
         + NO_HUMANS,
)
GROUPS["g10"] = ["x04"]

# CEO 2026-09-27: B-roll with the last ~35 credits — "B-roll + ตัวละคร + Prop + Location ไม่มีบทพูด ไม่มี Sound Music เน้นกิจกรรม
# ธรรมชาติ ความแปลกใหม่ ความอลังการ หลายๆ มุม ... แบบ LongTake". Plan ก approved: four 8-s long takes, each a different
# camera (low drone climb, deep water looking up, extreme wide flying, macro). All four sit before the crossing, so the
# lamps on THE MOUNT's seat are still lit, as in its picture.
B_SILENT = "silence; no voices, nobody speaks"
B_CRIT = (B.NO_WORDS + ", no cut, no slow motion, no text, no split screen, no metal, no plastic, " + NO_HUMANS)
BROLL = [
    dict(prefix="b", n=1, slug="broll-village-morning", title="B-ROLL: THE VILLAGE WAKES", s=8, grade="DAY", longtake=True,
         spec="ONE CONTINUOUS TAKE, NO CUTS. A drone skims low over the glass-clear water, glides under the arching stilt "
              "roots of a giant mangrove tree, then climbs smoothly up past walkways and roofs until the whole village "
              "and the huge moon fill the frame; no cut, no zoom, no slow motion.",
         refs=["@Village", "@Dock", "@Villagers", "@Villagers2", "@Manta"],
         ref_override={"@Manta": "THE MANTAS moored at the dock: take their manta bodies, colours and the driftwood "
                                 "seats with their softly glowing seed-pod lamps from this picture; several rest at the "
                                 "dock with nobody on them."},
         heading="MORNING IN THE VILLAGE: the village waking up and going about its work, seen in one sweeping flight.",
         frame="Starts a metre above the glass-clear turquoise water among the stilt roots; ends high above the village, "
               "the giant mangrove trees, walkways, rope bridges and glowing grass roofs spread out below, the huge moon "
               "over them.",
         particles="sunlight sparkling on the water, spray from a diving child, glowing specks drifting in the air.",
         beats=["[0s] Skimming low over the glass-clear water past the floating dock: several mantas are moored there with "
                "kelp ropes, their seed-pod lamps glowing softly; a villager coils a rope on the dock.",
                "[2s] The camera glides in under the arching stilt roots; above, two villagers sit on a walkway mending a "
                "big kelp net, and a small child dives from the walkway into the water with a clean splash.",
                "[4.5s] Climbing past a hut roof of glowing neon-green grass: a woman hangs strips of kelp to dry on a "
                "line; a young man crosses a swaying rope bridge with a bundle on his shoulder.",
                "[6.5s] Rising above the treetops: the whole village of giant mangrove trees standing in the glass-clear "
                "sea, the huge moon close over the horizon; the camera keeps rising slowly to the end."],
         sound=B_SILENT, crit=B_CRIT + ", no fish, no boat, no land, no island, no beach"),
    dict(prefix="b", n=2, slug="broll-glass-sea-below", title="B-ROLL: THE GLASS SEA FROM BELOW", s=8, grade="TURNING",
         longtake=True,
         spec="ONE CONTINUOUS TAKE, NO CUTS. From deep below, looking up toward the bright surface, the camera rises very "
              "slowly and turns a quarter circle; no cut, no zoom, no slow motion.",
         refs=["@Manta", "@Strong", "@Young", "@Elder", "@GlassSpiral", "@GlassCathedral", "@GlassHalo", "@GlassBloom"],
         heading="THE GLASS SEA, from far below: THE MOUNT swims through the water with THE THREE RIDERS holding on to its "
                 "seat, tiny, while the glass creatures, each many times bigger, drift around it.",
         frame="Looking up from deep water: the bright rippling surface fills the top of the frame; THE MOUNT is a small "
               "manta shape swimming across the light with THE THREE RIDERS on its back, gill frills streaming; the four "
               "glass creatures hang at different depths between it and the camera.",
         particles="rainbow caustics sweeping through the water, silver bubbles and glowing motes rising, seeds of light "
                   "drifting from THE BLOOM.",
         beats=["[0s] Deep below, looking up: THE SPIRAL turns slowly in the foreground, rainbow light running along it; "
                "far above, THE MOUNT swims into view against the bright surface.",
                "[2.5s] THE DOME drifts across between the camera and the surface, its layered veils rippling; THE MOUNT "
                "passes above it and its shadow slides over the veils.",
                "[5s] THE RINGS float past, one inside another, trailing threads of light; THE BLOOM opens its petals and "
                "releases seeds of light that rise toward THE MOUNT.",
                "[7s] THE MOUNT swims on, small among the giants, as the camera keeps rising slowly to the end."],
         sound=B_SILENT, crit=B_CRIT + ", no fish, no boat, no rider falling off, no stinging tentacles"),
    dict(prefix="b", n=3, slug="broll-storm-pillars", title="B-ROLL: BETWEEN THE PILLARS", s=8, grade="TURNING",
         longtake=True,
         spec="ONE CONTINUOUS TAKE, NO CUTS. Extreme wide; the camera flies slowly forward and rises between the pillars; "
              "no cut, no zoom, no slow motion.",
         refs=["@Pillars", "@Manta", "@Strong", "@Young", "@Elder", "@Turning"],
         heading="THE STORM PILLARS: thin, perfectly straight columns of slowly swirling cloud stand on the sea and rise "
                 "beyond the top of the sky; THE MOUNT weaves between them, tiny.",
         frame="Extreme wide from high behind: the violet-grey sea stretching away, the pillars standing on it at "
               "different distances and rising out of the top of the frame; THE MOUNT a tiny shape on the water with THE "
               "THREE RIDERS on its back.",
         particles="fine spray, mist curling round the base of each pillar, the small whirlpools turning.",
         beats=["[0s] From high behind: THE MOUNT glides across the violet-grey sea toward the nearest pillar, a column of "
                "slowly swirling cloud thin as a thread against its height, a small whirlpool turning at its foot.",
                "[3s] THE MOUNT curves around the whirlpool at the foot of the pillar, THE THREE RIDERS leaning into the "
                "turn.",
                "[5s] The camera rises and flies on between two more pillars; the columns stand in rows to the horizon, "
                "each rising beyond the top of the sky.",
                "[7s] THE MOUNT is a speck among the pillars as the camera keeps rising to the end."],
         sound=B_SILENT, crit=B_CRIT + ", no tornado, no lightning, no boat"),
    dict(prefix="b", n=4, slug="broll-the-seat", title="B-ROLL: THE SEAT, IN DETAIL", s=8, grade="TURNING",
         longtake=True,
         spec="ONE CONTINUOUS TAKE, NO CUTS. Macro, very close, the camera sliding slowly along the seat on THE MOUNT's "
              "back while it swims at the surface; shallow depth of field; no cut, no zoom, no slow motion.",
         refs=["@Manta", "@Lantern", "@Pole", "@Necklace", "@Young"],
         heading="THE SEAT, in close detail, as THE MOUNT swims on at the surface in the evening.",
         frame="Macro along the driftwood seat on THE MOUNT's back: kelp-rope lashings, seashells, the pale bone-rib "
               "backrest, the sea rushing past below.",
         particles="drops of spray, a fine mist off the water, the lamp's glow on the wet wood.",
         beats=["[0s] Macro on THE LANTERN hanging from the seat: the pearly seashell swings gently on its kelp handle, "
                "the three golden seed pods inside it glowing, drops of spray on the shell.",
                "[2.5s] The camera slides along the seat to THE POLE lying against it: water beads on the carved wave "
                "patterns of the pale bone, the kelp grip dark and wet.",
                "[5s] It slides on to THE YOUNG ONE's small webbed hand holding THE NECKLACE: dry brown seed husks on "
                "kelp twine turning between the fingers.",
                "[7s] Past the hand, out of focus, the sea rushes by under a violet-grey evening sky; the camera holds "
                "to the end."],
         sound=B_SILENT, crit=B_CRIT),
]
for _i, _sc in enumerate(BROLL, 1):
    GROUPS[f"b{_i}"] = [f"b{_i:02d}"]
GROUPS["g9"] = ["r01"]
GROUPS["g9c"] = ["r02"]
GROUPS["g9p"] = ["r03"]
GROUP_LENGTHS = {"g5": {"n06": 7, "n07": 13, "n13": 10},
                 # the spot refires: G5's own lengths, the wave cut to 10 s and the waking to 9 s
                 "g5a": {"n06": 7}, "g5b": {"n07": 10}, "g5c": {"n13": 9}}
GROUP_NATURAL = {"g7", "g8", "g9", "g9c", "g9p", "g5w", "b1", "b2", "b3", "b4", "g10"}  # paid: no stretch, fewer seconds, fewer credits
MOOD = {
    "n02": ("MOOD: the start of the most fantastical passage of the film, as if they slip into a fairy tale. From the "
            "moment THE MOUNT passes under the surface the shot runs in slow motion, about half speed: silver bubbles, "
            "gill frills and hands drift slowly; soft glowing motes and rainbow light ripple through the water."),
    "n03": ("MOOD: the most fantastical moment of the film, a fairy tale under the sea, all in slow motion, about half "
            "speed: the glass creatures shimmer like living stained glass, rainbow caustics sweep over THE THREE "
            "RIDERS, glowing motes float everywhere, dreamlike and luminous."),
    "n07": ("MOOD: violent and overwhelming. The wave is a brutal wall of water that slams down with crushing force; "
            "spray and foam explode across the frame; the camera shakes hard; nobody could stay on."),
}


def _inside_shot(text):
    """A shot's own 'no cut' rules apply inside that shot only; the group is joined by hard cuts."""
    text = re.sub(r"ONE CONTINUOUS TAKE, NO CUTS\.", "Within this shot: one continuous take.", text)
    text = re.sub(r"ONE LOCKED SHOT, NO CUTS\.", "Within this shot: one locked shot.", text)
    return re.sub(r"\bno cuts?\b", "no cut inside this shot", text)


GROUP_SECONDS = 30  # CEO 2026-09-26: fill every free generation to 30 s; the edit trims later


def stretch(scs, target, lengths=None):
    """Scale each shot's length (and so its beat times) so the group runs `target` seconds, in 0.5 s steps."""
    total = sum(sc["s"] for sc in scs)
    if lengths:
        return [dict(sc, s=lengths[tag(sc)], _f=lengths[tag(sc)] / sc["s"]) for sc in scs]
    if len(scs) == 1 or total >= target:
        return [dict(sc, _f=1.0) for sc in scs]
    out, used = [], 0.0
    for i, sc in enumerate(scs):
        s_new = (target - used) if i == len(scs) - 1 else round(sc["s"] * target / total * 2) / 2
        out.append(dict(sc, s=s_new, _f=s_new / sc["s"]))
        used += s_new
    return out


def render_group(scs, style, gkey=None):
    scs = [with_mount(sc) for sc in scs]
    if gkey not in GROUP_NATURAL:
        scs = stretch(scs, GROUP_SECONDS, GROUP_LENGTHS.get(gkey))
    order, jobs = [], {}
    for sc in scs:
        for h in sc["refs"]:
            if h not in order:
                order.append(h)
            jobs.setdefault(h, set()).add(sc.get("ref_override", {}).get(h, REFS[h][1]))
    if len(order) > 10:
        raise SystemExit(f"{[tag(s) for s in scs]}: {len(order)} pictures, the Wan3 cap is 10")
    refs = []
    for i, h in enumerate(order, 1):
        text = next(iter(jobs[h])) if len(jobs[h]) == 1 else REFS[h][1]
        refs.append(f"{token(i, style)}: {text}")
    total = sum(sc["s"] for sc in scs)
    head = (f"{total} seconds, 16:9. {len(scs)} SHOTS in one video, in this order, joined by hard cuts at the times "
            "given; each shot keeps its own camera, place and light; never blend two shots.") if len(scs) > 1 else \
        f"{total} seconds, 16:9."
    parts = [head, "REFERENCES, each with a job:\n" + "\n".join(refs)]
    t = 0
    for i, sc in enumerate(scs, 1):
        key = (sc.get("prefix", "m"), sc["n"])
        start, end = t, t + sc["s"]
        beats = [b.replace("GLOW", B.GLOW) for b in (sc.get("wan3_beats") or sc["beats"])]
        f = sc.get("_f", 1.0)
        beats = [re.sub(r"\[(\d+(?:\.\d+)?)s\]", lambda m: f"[{round(start + float(m.group(1)) * f, 1):g}s]", b)
                 for b in beats]
        snd = sc.get("sound") or B.SOUND.get(key, "silence; nobody speaks")
        label = (f"THE {'MONTAGE' if sc.get('montage') else 'SHOT'}, from {start:g}s to {end:g}s: {sc['title']}. "
                 f"{sc['spec']}" if sc.get("montage") or sc.get("longtake") else
                 f"SHOT {i} of {len(scs)}, from {start:g}s to {end:g}s: {sc['title']}. {_inside_shot(sc['spec'])}")
        sec = [label,
               sc["heading"], "THE FRAME: " + sc["frame"]]
        state = sc.get("state") or B.STATE.get(key)
        if state:
            sec.append("STATE: " + state)
        # CEO 2026-09-26: G6 take 1 came back with a boat and G5 with a rock. THE MOUNT's PICTURE must be in every shot
        # the riders sit on it; words alone (B.MOUNT_DARK) passed the old guard and failed twice.
        on_mount = key in B.ON_MOUNT or sc.get("prefix") == "x"
        if on_mount and "@Manta" not in sc["refs"]:
            raise SystemExit(f"{sc['title']}: riders on THE MOUNT but no @Manta picture")
        if key in B.DARK_LIT or sc.get("lit"):
            sec.append("THE LIGHT: " + B.LIGHT + (" " + sc["light_extra"] if sc.get("light_extra") else ""))
        if sc.get("particles"):
            sec.append("PARTICLES: " + sc["particles"])
        if sc.get("quality"):
            sec.append("QUALITY: " + sc["quality"])
        if MOOD.get(tag(sc)):
            sec.append(MOOD[tag(sc)])
        if sc.get("actions"):
            sec.append("EACH CHARACTER, ALL THROUGH THE SHOT (each busy with their own action, never all the same):\n"
                       + "\n".join("- " + a for a in sc["actions"]))
        sec += ["WHAT HAPPENS:\n" + "\n".join(beats),
                sc.get("sound_line") or
                f"Sound in this shot: only the sounds the characters make themselves: {snd}. No music, no ambient sound.",
                B.GRADE[sc.get("grade_override", sc["grade"])],
                # CEO 2026-09-26 ("No Music แบบ Seedance"): the house-negatives wall is dropped for Wan3, so its music
                # ban is repeated in every shot's own negatives, not only in the sound line.
                "Avoid in this shot: " + (sc["crit"] if sc.get("montage") or sc.get("longtake") else _inside_shot(sc["crit"]))
                + ", no music, no score, no background music."]
        parts.append("\n".join(sec))
        t = end
    return "\n\n".join(parts), order, total


def tag(sc):
    return f"{sc.get('prefix', 'm')}{sc['n']:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="+", help="shot keys (o01, n13) or group keys (g1..g7)")
    ap.add_argument("--token", choices=["at", "angle"], default="at")
    ap.add_argument("--out", type=Path, default=HERE / "wan3")
    ap.add_argument("--seconds", type=float, help="a shorter test clip: drop the beats that start at or after it")
    ap.add_argument("--suffix", default="", help="added to the output name, e.g. -rehearsal")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    by_key = {f"{s.get('prefix', 'm')}{s['n']:02d}": s for s in B.SCENES}
    by_key["x_longtake"] = LONG_TAKE
    by_key["x_shadow"] = SHADOW_TAKE
    by_key["r01"] = RUN_MULTICUT
    by_key["r02"] = RUN_COVER
    by_key["r03"] = RUN_PARKOUR
    by_key["x03"] = WAVE_MULTICUT
    by_key["x04"] = STORM_BOOKEND
    for sc in BROLL:
        by_key[tag(sc)] = sc
    for k in a.keys:
        if k in GROUPS:
            text, order, total = render_group([by_key[x] for x in GROUPS[k]], a.token, k)
            if len(text) > CAP:
                raise SystemExit(f"{k}: {len(text)} characters > {CAP}")
            job = {"key": k, "title": " + ".join(by_key[x]["title"] for x in GROUPS[k]), "seconds": total,
                   "shots": GROUPS[k], "images": [REFS[h][0] for h in order], "prompt": text, "chars": len(text)}
            (a.out / f"{k}{a.suffix}.wan3.json").write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"{k} {len(text):5d} chars {len(order)} images {total}s {GROUPS[k]}")
            continue
        sc = with_mount(by_key[k])
        if a.seconds:
            keep = [b for b in sc["beats"] if float(re.match(r"\[([\d.]+)s\]", b).group(1)) < a.seconds]
            sc = dict(sc, s=int(a.seconds) if a.seconds == int(a.seconds) else a.seconds, beats=keep)
        # CMO_Knowledge_Wan3.0_TopView §5 step 3, in order: short references, the dialogue negatives and the grade tail, the mount
        # description, the particles, then each action line to its first clause;
        # never the beats, the actions, the dialogue or the camera line.
        for level in range(8):
            text = render(sc, a.token, shorten=False, level=level)
            if len(text) <= CAP:
                break
        if len(text) > CAP:
            print(f"{k}: {len(text)} characters even trimmed; trim the shot by hand"); continue
        if len(sc["refs"]) > 10:
            raise SystemExit(f"{k}: {len(sc['refs'])} images, the Wan3 cap is 10")
        job = {"key": k, "title": sc["title"], "seconds": sc["s"], "images": [REFS[h][0] for h in sc["refs"]],
               "prompt": text, "chars": len(text)}
        (a.out / f"{k}{a.suffix}.wan3.json").write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{k} {len(text):5d} chars {len(sc['refs'])} images {sc['s']}s trim-level {level}")


if __name__ == "__main__":
    main()
