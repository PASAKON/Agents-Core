# -*- coding: utf-8 -*-
"""«น้ำไม่เลือกบ้าน» (film 3) ACT3 = EP5 + EP6, shots 54-73 (7:04-9:44), the last act.
Source of truth for tools/build_shotsheet.py.

Loads ACT1 for every shared block. S54-S69 stay on the waist-deep day (เฮียกิจ day-2 state);
S70-S73 are five days later, the water down to the ankle (เฮียกิจ day-5, มิ้นท์ back home).

S73 is the one silent shot: the narrator's line goes on in the edit, so the prompt says
nobody speaks. S74 (insert of the high shelf) and S75 (the drying lane, title card) are not
generated in Flow: they are slow push-ins on the porch__kitchen and soi__after plates, made
in the edit at no credit cost. That also keeps the sheet inside MAX_SILENT_RUN = 1 without
a lint override.
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
    62: ["@rowboat", "@water_pack"], 63: ["@rowboat"], 64: ["@rowboat"], 65: ["@rowboat"],
    71: ["@porridge_pack"], 73: ["@rowboat"],
}

T5 = "the same day around noon, grey overcast daylight"
T6 = "five days later, warm sunny daylight"

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 54: (8, "Medium two-shot at the porch steps",
      ["noi", "kij2"], "porch3", T5,
      "the woman in the checked apron, calm and fair, points him to the end of the queue while "
      "she speaks; the stocky man, meek, shoulders dropping, nods and answers", ["nosubs"]),
 55: (8, "Medium shot from the water: the stocky man at the end of the queue, the old woman "
         "eating on the porch above him",
      ["kij2", "yen"], "porch3", T5,
      "the stocky man, remorseful, eyes reddening, stands waist-deep in the water at the end "
      "of the queue watching the old woman eat, and murmurs while he watches; up on the porch "
      "the old woman spoons rice porridge slowly into her mouth", ["nosubs"]),
 56: (8, "Medium close-up at the porch edge",
      ["yen", "kij2"], "porch3", T5,
      "the old woman, kind, a small smile, gets up and comes to the porch edge holding out her "
      "half-eaten bowl of porridge toward him while she speaks; below, the stocky man, "
      "startled, stares up at her", ["nosubs"]),
 57: (8, "Close-up on the stocky man, the bowl held out in the foreground",
      ["kij2", "yen"], "porch3", T5,
      "the stocky man, choked up, tears streaming, voice breaking, stares at the bowl the old "
      "woman holds out to him, his hands shaking, while he speaks; the old woman keeps holding "
      "it out, patient", ["nosubs"]),
 58: (8, "Medium two-shot",
      ["yen", "kij2"], "porch3", T5,
      "the old woman, gentle, presses the bowl into his hands while she speaks; the stocky "
      "man, sobbing openly, takes it", ["nosubs"]),
 59: (8, "Medium two-shot",
      ["kij2", "yen"], "porch3", T5,
      "the stocky man, sobbing, shaking his head, gently pushes the bowl back toward the old "
      "woman while he speaks; the old woman smiles and answers", ["nosubs"]),
 60: (8, "Medium two-shot",
      ["kij2", "noi"], "porch3", T5,
      "the stocky man, remorseful and hoarse, turns to the woman in the checked apron wiping "
      "the tears from his face with the back of his hand while he speaks; the woman in the "
      "checked apron listens, still and quiet", ["nosubs"]),
 61: (8, "Close-up at the pot",
      ["noi", "kij2"], "porch3", T5,
      "the woman in the checked apron, giving him her first smile but still firm, sets down "
      "the ladle while she speaks; the stocky man, embarrassed, quickly shakes his head and "
      "answers", ["nocash", "nosubs"]),
 62: (8, "Medium wide at the townhouse's front door, the rowboat alongside",
      ["kij2", "mint_f"], "soi3", T5,
      "the stocky man, ashamed but determined, hands a water pack down from his front door "
      "into the rowboat while he speaks to his daughter; the young woman in the boat, smiling "
      "through tears, takes it and answers", ["nologo", "nosubs"]),
 63: (8, "Medium two-shot in the rowboat",
      ["kij2", "mint_f"], "soi3", T5,
      "the stocky man, determined, a shy smile, steps down into the rowboat and takes the "
      "paddle from his daughter while he speaks; the young woman, laughing, hands it over and "
      "answers", ["nosubs"]),
 64: (8, "Medium shot from the porch edge down to the rowboat",
      ["noi", "kij2"], "porch3", T5,
      "the woman in the checked apron, trusting, kneels at the porch edge handing her notebook "
      "down into the rowboat while she explains; the stocky man, sitting in the boat with the "
      "paddle, listens and nods", ["nosubs"]),
 65: (8, "Medium wide, the rowboat gliding down the flooded lane toward camera",
      ["kij2", "mint_f"], "soi3", T5,
      "the stocky man, loud and warm for the first time, paddles the rowboat down the "
      "waist-deep lane calling out to the silent houses while he speaks; in front of him the "
      "young woman lifts the lid off the steaming pot, smiling", ["nosubs"]),
 66: (8, "Medium two-shot on the porch",
      ["yen", "noi"], "porch3", T5,
      "the old woman, delighted, laughing softly, watches the rowboat go down the lane while "
      "she speaks; beside her the woman in the checked apron shakes her head, smiling, and "
      "answers", ["nosubs"]),
 67: (8, "Medium two-shot on the porch bench",
      ["kij2", "yen"], "porch3", T5,
      "the stocky man, content and teary, sits beside the old woman on the bench eating rice "
      "porridge from a bowl while he speaks; the old woman, kind, spoons some greens into his "
      "bowl and answers", ["nosubs"]),
 68: (8, "Medium two-shot on the porch",
      ["kij2", "noi"], "porch3", T5,
      "the stocky man, serious and eager, stands up from the bench and turns to the woman in "
      "the checked apron while he speaks; the woman in the checked apron, surprised, puts down "
      "her ladle", ["nosubs"]),
 69: (8, "Medium two-shot on the porch",
      ["kij2", "noi"], "porch3", T5,
      "the stocky man, determined, points at the grey gas cylinder and the rice sacks on the "
      "high shelf while he speaks; the woman in the checked apron, moved, eyes red, raises a "
      "hand to her mouth and answers", ["nosubs"]),
 70: (8, "Medium wide on the porch, the drying lane behind",
      ["mint_h", "noi"], "porch5", T6,
      "the young woman, proud, writes in the notebook at the porch table while she speaks; the "
      "woman in the checked apron, bright, ladles rice into bowls lined up on the table and "
      "answers", ["nosubs"]),
 71: (8, "Medium two-shot on the porch",
      ["kij5", "yen"], "porch5", T6,
      "the stocky man, shy, smiling, holds out a clear plastic bag full of pale-orange porridge "
      "sachets to the old woman while he speaks; the old woman takes it and laughs out loud as "
      "she answers", ["nologo", "nosubs"]),
 72: (8, "Medium two-shot on the porch",
      ["mint_h", "kij5"], "porch5", T6,
      "the young woman, earnest and proud, hands her father the open notebook while she "
      "speaks; the stocky man, smiling, nods and answers", ["nosubs"]),
 73: (8, "Wide shot, the three of them eating together at the porch table, the rowboat tied "
         "at the steps",
      ["noi", "yen", "kij5"], "porch5", T6,
      "the woman in the checked apron, the old woman and the stocky man sit together at the "
      "porch table eating rice porridge, smiling and laughing; the old woman spoons rice into "
      "the stocky man's bowl. Nobody speaks at all in this shot: no dialogue, no words, no "
      "voices; the only sounds are spoons on bowls, birds and the lane", ["nosubs"]),
}

_NAME = dict(_a1._NAME)
SHOTS = _a1._build(_META)
