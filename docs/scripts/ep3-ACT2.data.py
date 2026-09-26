# -*- coding: utf-8 -*-
"""«น้ำไม่เลือกบ้าน» (film 3) ACT2 = EP3 + EP4, shots 24-53 (3:04-7:04).
Source of truth for tools/build_shotsheet.py.

Loads ACT1 for every shared block (cast, states, voices, locations, negatives, the script
reader). Adds the first-day afternoon (S24-S38) and the next morning, waist-deep (S39-S53):
เฮียกิจ in his day-2 state, มิ้นท์ in her rain jacket. S24-S28 continue S23 without a cut in
story time, so they keep ACT1's late-morning light.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "ep3_act1", Path(__file__).with_name("ep3-ACT1.data.py"))
_a1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a1)

STYLE = _a1.STYLE
CHAR = dict(_a1.CHAR)
WARDROBE = dict(_a1.WARDROBE)
VOICE = dict(_a1.VOICE)
LOC = dict(_a1.LOC)
NOT = dict(_a1.NOT)
PROP_FOR_NOT = dict(_a1.PROP_FOR_NOT)

PROPS_BY_SHOT = {
    29: ["@water_pack"], 30: ["@water_pack"], 31: ["@water_pack"],
    39: ["@rowboat"], 44: ["@water_pack"], 45: ["@rowboat"], 46: ["@rowboat"],
}

T2 = _a1.T2
T3 = "the first day of the flood, afternoon, overcast daylight"
T4 = "the next morning, grey overcast daylight, the power out all along the lane"

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 24: (8, "Close-up, the young woman stepping out from behind her father, the woman in the "
         "checked apron at the open door behind",
      ["mint_h", "kij1", "noi"], "kij0", T2,
      "the young woman, trembling but clear, steps out from behind her father toward the woman "
      "at the door while she speaks; the stocky man, shocked, eyes wide, whips his head round "
      "and snaps her name; at the door the woman in the checked apron stares at the cartons",
      ["nologo", "nosubs"]),
 25: (8, "Medium two-shot inside, by the glass front door",
      ["kij1", "mint_h"], "kij0", T2,
      "the stocky man, furious, face red, veins standing out on his neck, pushes the glass "
      "front door shut and turns on his daughter shouting while he speaks; the young woman, "
      "shocked, steps back one pace and shouts back", ["notouch", "nologo", "nosubs"]),
 26: (8, "Medium shot in the lane outside the shut glass door of the white townhouse",
      ["noi"], "soi1", T2,
      "the woman in the checked apron, hurt but defiant, eyes red, stands in the ankle-deep "
      "water in front of the shut glass door, one hand flat on the glass, and calls through it "
      "while she speaks, her face turned three-quarters to camera", ["nosubs"]),
 27: (8, "Medium two-shot beside the stacked cartons",
      ["mint_h", "kij1"], "kij0", T2,
      "the young woman, crying, tears streaming, voice cracking, points at the pile of cartons "
      "while she speaks; the stocky man, hard-voiced, arms crossed, refuses to look at her and "
      "answers", ["notouch", "nologo", "nosubs"]),
 28: (8, "Medium shot at the foot of the white staircase",
      ["kij1", "mint_h"], "kij0", T2,
      "the stocky man, cold, climbs the white staircase while he speaks, his face turned back "
      "toward her over his shoulder; at the bottom of the stairs the young woman, sobbing, "
      "watches him go", ["nosubs"]),
 29: (8, "Medium shot by the stacked cartons",
      ["mint_h"], "kij0", T3,
      "the young woman, resolute, jaw set, wipes the tears from her cheeks with one hand and "
      "heaves a shrink-wrapped water pack onto her shoulder while she speaks to herself",
      ["nologo", "nosubs"]),
 30: (8, "Medium wide from the porch end looking back up the lane: the young woman wading "
         "toward camera, the upstairs window of the white townhouse behind her",
      ["kij1", "mint_h"], "soi1", T3,
      "the stocky man, furious, leans out of the upstairs window and shouts at full voice "
      "while he speaks; below, the young woman, tears running, keeps wading toward camera "
      "through the ankle-deep water with the water pack on her shoulder and answers without "
      "stopping, her face to camera", ["notouch", "nologo", "nosubs"]),
 31: (8, "Medium two-shot on the porch bench",
      ["mint_h", "yen"], "porch1", T3,
      "the young woman, tired, smiling through tears, sets the water pack down beside the old "
      "woman on the bench while she speaks; the old woman, deeply moved, takes the young "
      "woman's hand and answers", ["nosubs"]),
 32: (8, "Medium two-shot on the porch",
      ["noi", "mint_h"], "porch1", T3,
      "the woman in the checked apron, proud, eyes red, puts an arm around the young woman's "
      "shoulders while she speaks; the young woman, sniffling softly, nods and answers",
      ["nosubs"]),
 33: (8, "Medium shot at the porch edge, the concrete lamp post in the lane beside it",
      ["noi", "mint_h"], "soi1", T3,
      "the woman in the checked apron, worried and serious, points at the dirty water line on "
      "the concrete lamp post while she speaks; the young woman listens closely, nodding",
      ["nosubs"]),
 34: (8, "Medium shot at the high wooden shelf on the porch",
      ["noi", "mint_h"], "porch1", T3,
      "the woman in the checked apron, brisk and breathing hard, lifts a plain white rice sack "
      "up onto the high wooden shelf while she explains; beside her the young woman strains to "
      "lift another sack up after her", ["nologo", "nosubs"]),
 35: (8, "Medium two-shot at the porch table",
      ["noi", "yen"], "porch1", T3,
      "the woman in the checked apron, caring, seals a clear zip bag around the old woman's "
      "small pill box while she speaks; the old woman, admiring, smiles and answers",
      ["nosubs"]),
 36: (8, "Medium shot from the lane up at the upstairs window of the white townhouse",
      ["kij1"], "soi1", T3,
      "the stocky man, sneering, stands at his upstairs window chewing a slice of bread and "
      "looks down the lane toward the porch kitchen while he talks to himself, chewing as he "
      "speaks", ["nosubs"]),
 37: (8, "Medium shot at the pot, the young woman beside the woman in the checked apron",
      ["noi", "mint_h"], "porch1", T3,
      "the woman in the checked apron, calm but loud, keeps stirring the big pot while she "
      "looks up and calls toward the townhouse window; beside her the young woman looks up "
      "toward her father's window", ["nosubs"]),
 38: (8, "Medium close-up at the upstairs window",
      ["kij1"], "soi1", T3,
      "the stocky man, furious, shouting, face red, yells down into the lane while he speaks "
      "and slams the window shut on the last word", ["nosubs"]),
 39: (8, "Wide shot down the waist-deep flooded lane, steam rising from the pot on the dry "
         "porch",
      ["noi", "mint_f"], "soi3", T4,
      "the woman in the checked apron, urgent and busy, kneels at the porch edge handing the "
      "covered pot down into the old wooden rowboat while she speaks; the young woman, sitting "
      "in the boat gripping a paddle, focused and excited, takes it and answers", ["nosubs"]),
 40: (8, "Medium shot on the flooded ground floor",
      ["kij2"], "kij2", T4,
      "the stocky man, panicking, eyes bulging, voice hoarse, wades through knee-deep brown "
      "water in his own house grabbing at a floating soaked carton while he speaks",
      ["nologo", "nosubs"]),
 41: (8, "Close-up on his face and hands",
      ["kij2"], "kij2", T4,
      "the stocky man, despairing, lips trembling, squeezes soggy instant-noodle packets that "
      "fall apart into pulp in his hands while he speaks", ["nologo", "nosubs"]),
 42: (8, "Medium shot at the dark open fridge",
      ["kij2"], "kij2", T4,
      "the stocky man, disgusted and grimacing, pulls the dark fridge door open and covers his "
      "nose with one hand while he speaks", ["nologo", "nosubs"]),
 43: (8, "Close-up at the kitchen counter",
      ["kij2"], "kij2", T4,
      "the stocky man, frustrated, jabs the dead microwave's buttons again and again and bangs "
      "its side with his fist while he speaks; nothing lights up", ["nologo", "nosubs"]),
 44: (8, "Medium shot on the staircase just above the water",
      ["kij2"], "kij2", T4,
      "the stocky man, exhausted and panting, legs shaking, drags a sealed water pack up the "
      "stairs out of the water while he speaks", ["nologo", "nosubs"]),
 45: (8, "Medium shot from the lane: the stocky man at the upstairs window, the young woman "
         "in the rowboat below, both faces visible",
      ["kij2", "mint_f"], "soi3", T4,
      "the stocky man, awkward, forcing a stern voice, leans out of the upstairs window and "
      "calls down while he speaks; below, the young woman in the rowboat with the covered pot "
      "stops paddling, hesitant, eyes red, looks up and answers", ["nosubs"]),
 46: (8, "Close-up, the young woman in the rowboat",
      ["mint_f"], "soi3", T4,
      "the young woman, hurt but resolute, eyes red, grips the paddle hard with the covered "
      "pot in front of her and looks up toward the window while she speaks", ["nosubs"]),
 47: (8, "Medium shot on the staircase just above the water",
      ["kij2"], "kij2", T4,
      "the stocky man, starving but proud, sits alone on the stairs just above the knee-deep "
      "water clutching his stomach and mutters while he speaks", ["nosubs"]),
 48: (8, "Medium two-shot at the porch table",
      ["yen", "noi"], "porch3", T4,
      "the old woman, cheerful and stronger, counts the bowls lined up on the table, touching "
      "each one while she speaks; the woman in the checked apron, smiling, writes in her "
      "notebook and answers", ["nosubs"]),
 49: (8, "Medium two-shot at the porch edge",
      ["noi", "yen"], "porch3", T4,
      "the woman in the checked apron, thoughtful and worried, looks across the water toward "
      "the white townhouse while she speaks; beside her the old woman slowly sets a bowl down "
      "and answers kindly", ["nosubs"]),
 50: (8, "Medium shot on the staircase",
      ["kij2"], "kij2", T4,
      "the stocky man, pathetic, tears open the one dry instant-noodle packet and bites into "
      "the hard uncooked noodle block, chewing hard and coughing while he speaks",
      ["nologo", "nosubs"]),
 51: (8, "Medium shot at the upstairs window of the white townhouse",
      ["kij2"], "soi3", T4,
      "the stocky man, starving, leans on the window sill sniffing the air toward the steaming "
      "pot across the lane and swallows hard while he speaks", ["nosubs"]),
 52: (8, "Medium shot at the townhouse's front door",
      ["kij2"], "soi3", T4,
      "the stocky man, ashamed, head down but hungrier still, wades out of his front door into "
      "waist-deep brown water holding an empty bowl while he talks to himself", ["nosubs"]),
 53: (8, "Medium wide at the porch steps: the man in the orange T-shirt in the queue, the "
         "woman in the checked apron at the pot, the stocky man arriving at the bottom",
      ["noi", "kij2", "nb"], "porch3", T4,
      "the woman in the checked apron, steady and firm, stands at the pot looking the stocky "
      "man in the eye while she speaks; at the same moment the stocky man, humiliated, face "
      "numb, arrives at the bottom of the porch steps in waist-deep water holding an empty "
      "bowl and answers in a small voice; the man in the orange T-shirt, waiting on the steps "
      "with his own bowl, turns and raises his eyebrows", ["nosubs"]),
}

_NAME = dict(_a1._NAME)
SHOTS = _a1._build(_META)
