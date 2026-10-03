"""Build THE LAST BELL shot prompts, STORYBOARD.md, SCRIPT.md and the champa job list from one data table.

House format: CMO_Standard_Film_PromptFormat (two zones per file, tech header first, every reference declared
once with a job, [Ns] beats, manner tag of five words or fewer before dialogue, sound stated, one grade block per
look pasted verbatim, aimed negatives then the house wall). Camera and light words:
CMO_Knowledge_Cinematography_ShortMovie (Short Movie only). Engine: champa.io Seedance 2.0, multi-reference mode,
references named @ภาพ1..@ภาพ9 in upload order (9 is the measured cap, 2026-10-03).

Run: python3 docs/prompts/last-bell/build_shots.py
Writes: shots/<id>.txt, STORYBOARD.md, SCRIPT.md, jobs-wave1.json (shots that need no continue frames).
Never hand-edit the outputs; change the table here and rebuild.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

# champa refuses a prompt over 2,000 characters ("ข้อมูลไม่ถูกต้อง", measured 2026-10-03: 2,000 accepted,
# 2,001 / 2,500 / 3,000 / 4,000 / 8,000 refused), so every block here is written short and main() asserts the cap.
LIMIT = 2000
SHEET = "; ignore the sheet layout and background"
REF_JOB = {
    "loc_city": "SUWANNAWARI, the floating city: stilt houses, canals, the great white-and-gold chedi",
    "loc_canal": "THE CANAL and its long wooden footbridge",
    "loc_bell_pavilion": "THE BELL PAVILION atop the great chedi: stone, gold, naga rails",
    "loc_yai_house-2": "YAI'S HOUSE, a poor stilt house inside: rusted zinc roof, patched plank walls",
    "ch_kaew_a": "KAEW: face, hair, clothes, colours" + SHEET,
    "ch_yai_a": "YAI BUA: face, hair, clothes, colours" + SHEET,
    "ch_mek_a": "MEK: face, hair, clothes, colours" + SHEET,
    "ch_governor_a": "THE GOVERNOR: face, body, clothes, gold" + SHEET,
    "ch_naga_a-2": "PHAYA NAK: head, crest, jade-and-gold scales, amber eyes, bronze neck bands" + SHEET,
    "prop_great_bell": "THE GREAT BELL: shape, bronze, chained-naga engraving" + SHEET,
    "prop_mallet": "THE MALLET: dark wood, red thread on the handle" + SHEET,
}

WHO = {
    "KAEW": "KAEW, Thai girl about 12, crimson tunic, indigo chong kraben, black bob with a crimson-thread topknot, barefoot",
    "YAI": "YAI BUA, frail Thai grandmother about 78, silver bun with jasmine, faded indigo shirt, brass wrist bells",
    "MEK": "MEK, lanky Thai boy about 14, turquoise checked headband, turquoise vest, black trousers",
    "GOV": "THE GOVERNOR, heavyset Thai man in his fifties, white silk jacket, gold buttons, gold chain, gold fan",
    "NAGA": "PHAYA NAK, colossal one-headed Thai naga, jade scales rimmed gold, gold crest, amber eyes",
}

LENS = "35mm anamorphic, film grain."
GRADE = {
    "day": "Grade: surreal yellow-green; colour from the light: chartreuse sky, gold oil lamps and gold leaf, green haze, deep olive shadows, soft contrast, photoreal. NOT orange-and-teal, NOT blue. " + LENS,
    "omen": "Grade: sickly yellow-green: mustard-yellow water, flat chartreuse sky, olive shadows, photoreal. NOT orange-and-teal, NOT blue. " + LENS,
    "storm": "Grade: storm: black-green clouds, yellow lightning, rain lit chartreuse, gold only from lamps and the bell, high contrast, photoreal. NOT blue, NOT orange-and-teal. " + LENS,
    "memory": "Grade: memory: warm gold lamp light, soft haze, slightly faded honey-green, photoreal. NOT blue. " + LENS,
    "dawn": "Grade: dawn after the storm: pale gold-green, low soft sun through mist, wet gold surfaces, photoreal. NOT blue, NOT orange-and-teal. " + LENS,
}
HOUSE_NEG = "no text, no subtitles, no watermark; no sheet panels, no white backdrop, no split screen; nothing modern"
SPEECH_NEG = "no stage directions spoken aloud, nothing spoken outside the quotes"
ONE_TAKE = "ONE CONTINUOUS TAKE, NO CUTS, no zoom"

LULLABY_TH = "นอนเถิดนาคา ใต้ฟ้าสีทอง ระฆังจะร้อง กล่อมเจ้าหลับไป สามช้าหนึ่งเร็ว ดังลมพัดใบ นอนเถิดนะใจ นครยังรอ"

# One row per shot, in cut order. refs: upload order = @ภาพ1.. (location first, then people, then props).
# cont: the shot this one continues (its last 3 frames take the last 3 slots); None = fire in wave 1.
S = []
def shot(id, scene, cut, grade, refs, take, heading, frame, beats, sound, negs=(), lines=(), cont=None, state=None):
    S.append(dict(id=id, scene=scene, cut=cut, grade=grade, refs=list(refs), take=take, heading=heading, frame=frame,
                  beats=list(beats), sound=sound, negs=list(negs), lines=list(lines), cont=cont, state=state))

# ---- A · The city of bells (0:00-1:30) ----
shot("A01", "A", 12, "day", ["loc_city"], ONE_TAKE + ", a very slow aerial push-in",
     "Dawn over SUWANNAWARI, the floating city of bells. No people close to the camera.",
     "Extreme wide from high above the water, the great chedi at the centre of the frame, layers of yellow-green mist between the rooftops, canals catching the sky.",
     ["[0s] The mist moves slowly; the chedi's gold spire catches the first light.",
      "[5s] A breeze crosses the city; thousands of small brass bells under the eaves swing at once.",
      "[10s] The camera keeps pushing in toward the chedi over the rooftops."],
     "Thousands of small bells chiming in the wind, water, distant birds. No music.",
     ["no people in the foreground", "no boats with engines"])
shot("A02", "A", 7, "day", ["loc_city", "loc_canal"], ONE_TAKE + ", a slow rack focus",
     "Close on the bells of SUWANNAWARI, then the canal below.",
     "Extreme close-up of a string of small brass bells hanging from a carved teak eave at screen-left, dew on the brass; behind them, out of focus, THE CANAL with its long footbridge.",
     ["[0s] The bells swing in the breeze; drops of dew fall from them.",
      "[4s] Focus pulls from the bells to THE CANAL below, where a long-tail boat slides left to right under the footbridge."],
     "Close, clear bell chimes, water lapping, a boat paddle.")
shot("A03", "A", 10, "day", ["loc_canal", "ch_kaew_a"], ONE_TAKE + ", a side tracking shot moving screen-left to screen-right",
     "KAEW runs to work across the footbridges at dawn.",
     "Full shot from the side at waist height: KAEW in profile, running screen-left to screen-right along THE CANAL footbridge, a small plain wooden mallet in her right hand; neighbours on the porches behind her.",
     ["[0s] KAEW sprints barefoot along the planks, her crimson topknot thread bouncing.",
      "[4s] She leaps a gap between two footbridges, lands, keeps running; an old woman on a porch shakes her head and smiles.",
      "[9s] KAEW reaches a small teak bell tower at screen-right and grabs its ladder."],
     "Bare feet slapping wet planks, her brass anklet bell, bells on the eaves, morning birds.",
     ["no shoes on KAEW", "no mallet with red thread in this shot"])
shot("A04", "A", 10, "day", ["loc_city", "ch_kaew_a"], ONE_TAKE + ", a slow crane up from low angle",
     "KAEW rings the morning bell and the city wakes.",
     "Low angle from the foot of a small teak bell tower: KAEW at the top, three-quarter view facing screen-right, a bronze bell the size of a water jar in front of her; SUWANNAWARI behind and below.",
     ["[0s] KAEW swings her small wooden mallet and strikes the bell once, hard; the bronze shivers.",
      "[4s] She strikes twice more; the sound rolls out over the rooftops.",
      "[8s] The camera cranes up past her: shutters open across the city, smoke rises, long-tail boats push off."],
     "Three deep clear strikes of a bronze bell, then the whole city's small bells answering.")
shot("A05", "A", 15, "day", ["loc_yai_house-2", "ch_kaew_a", "ch_yai_a"], ONE_TAKE + ", a very slow push-in",
     "YAI'S HOUSE in the afternoon. YAI BUA teaches KAEW the rhythm of the bells.",
     "Medium two-shot at eye level: YAI BUA sits on a woven mat at screen-left in three-quarter view facing screen-right; KAEW kneels at screen-right in three-quarter view facing screen-left, toward YAI BUA; a bamboo rail of small brass bells between them; a betel box on the floor.",
     ["[0s] YAI BUA taps the bells with a thin stick: three slow strokes, one fast.",
      "[4s] YAI BUA, looking at KAEW, softly: \"Every bell in this city has a voice. The great one has only one song.\"",
      "[10s] KAEW, eyes on YAI BUA, curious: \"Which song?\" YAI BUA smiles and hums the first line of a slow Thai lullaby."],
     "The little bells, rain ticking on the zinc roof, YAI BUA's cracked old voice, KAEW's bright young voice.",
     [SPEECH_NEG, "no gold in the house", "no fan, no furniture"],
     lines=[("YAI BUA", "Every bell in this city has a voice. The great one has only one song."), ("KAEW", "Which song?")])
shot("A06", "A", 6, "day", ["loc_yai_house-2", "ch_kaew_a", "ch_yai_a"], ONE_TAKE + ", camera locked, the movement only in the hands",
     "Insert: the rhythm passes from YAI BUA's hand to KAEW's hand.",
     "Top-down close-up of the bamboo rail of small brass bells: YAI BUA's thin hand with brass wrist bells at screen-left, KAEW's small hand at screen-right.",
     ["[0s] YAI BUA's hand taps three slow, one fast.",
      "[3s] KAEW's hand copies it exactly: three slow, one fast."],
     "Two clear phrases of the bells, three slow and one fast, then soft humming.")
shot("A07", "A", 10, "day", ["loc_canal", "ch_mek_a", "ch_kaew_a"], ONE_TAKE + ", a slow lateral dolly following the boat",
     "MEK teases KAEW from his long-tail boat.",
     "Medium wide at water level: MEK stands in the stern of a wooden long-tail boat at screen-left, three-quarter view facing screen-right toward KAEW; KAEW sits on the edge of THE CANAL footbridge at screen-right, feet over the water, facing MEK.",
     ["[0s] MEK poles the boat close and grins at KAEW, cheeky: \"Late again, bell girl!\"",
      "[5s] KAEW flicks water at him with her foot; MEK laughs and dodges.",
      "[8s] KAEW stops, looking down past MEK at the water, uneasy."],
     "Water, a pole knocking wood, MEK's teenage voice, laughter, distant bells.",
     [SPEECH_NEG],
     lines=[("MEK", "Late again, bell girl!")])
shot("A08", "A", 10, "omen", ["loc_city"], ONE_TAKE + ", a slow pull-back",
     "The omen: the lagoon of SUWANNAWARI turns yellow and the fish flee.",
     "Wide over the lagoon at the edge of the city, the open sea at the top of the frame.",
     ["[0s] The water darkens from green to mustard-yellow in a spreading stain.",
      "[4s] Hundreds of silver fish leap out of the water together, all toward the open sea, away from the camera.",
      "[9s] Every bell in the city stops at once; the wind drops."],
     "Bells chiming, then a rush of splashing fish, then total silence except the water.",
     ["no people", "the fish swim away from the camera, toward the sea"])

# ---- B · The storm and the Governor (1:30-3:00) ----
shot("B01", "B", 12, "day", ["loc_canal", "ch_governor_a"], ONE_TAKE + ", a slow push-in from medium to medium close-up",
     "THE GOVERNOR announces the storm from his golden barge.",
     "Medium shot from slightly below: THE GOVERNOR on the deck of a golden barge at the centre, facing the camera three-quarter toward screen-left, where a crowd stands on THE CANAL footbridge off-screen; servants hold a gold parasol over him; the sky darker green behind.",
     ["[0s] THE GOVERNOR snaps open his gold lacquer fan and looks down at the crowd at screen-left.",
      "[3s] THE GOVERNOR, smooth and loud: \"The storm of a hundred years is coming. My barges leave at dusk, for those who can pay.\"",
      "[11s] He fans himself and smiles."],
     "Wind rising, the barge creaking, his amplified smooth voice, a murmuring crowd.",
     [SPEECH_NEG, "no crown, no royal umbrella with tiers, no royal regalia"],
     lines=[("THE GOVERNOR", "The storm of a hundred years is coming. My barges leave at dusk, for those who can pay.")])
shot("B02", "B", 8, "day", ["loc_canal", "ch_mek_a", "ch_kaew_a"], ONE_TAKE + ", camera locked low on the water",
     "MEK answers back from below; KAEW beside him.",
     "Low angle from the water: MEK standing in his long-tail boat at screen-left, three-quarter view facing up and screen-right toward the off-screen barge; KAEW sitting in the bow at screen-right, looking up at MEK, then at the barge.",
     ["[0s] MEK cups his hands and shouts up toward the barge, angry: \"And the rest of us?\"",
      "[4s] Silence from above; KAEW looks from MEK to the barge, her jaw tight."],
     "Wind, water slapping the hull, MEK's shout echoing, no answer.",
     [SPEECH_NEG],
     lines=[("MEK", "And the rest of us?")])
shot("B03", "B", 10, "day", ["loc_city", "ch_kaew_a"], ONE_TAKE + ", a slow push-in past the elder to KAEW",
     "Under a temple sala, an old boatman tells the legend; KAEW listens.",
     "Medium wide under an open wooden sala at the water: an OLD BOATMAN, white beard, bare-chested, faded loincloth, sits at screen-left in profile facing screen-right, pointing at the great chedi in the distance; KAEW sits on the steps at screen-right, three-quarter view, listening, eyes on the chedi.",
     ["[0s] The OLD BOATMAN raises a thin arm toward the chedi.",
      "[3s] OLD BOATMAN, low and sure: \"Ring the great bell, and the Naga will rise to hold back the sea.\"",
      "[9s] KAEW's eyes stay on the chedi; she grips her small wooden mallet."],
     "Wind in the sala, small bells, the old man's dry voice.",
     [SPEECH_NEG, "the OLD BOATMAN is not THE GOVERNOR and wears no gold"],
     lines=[("OLD BOATMAN", "Ring the great bell, and the Naga will rise to hold back the sea.")])
shot("B04", "B", 12, "storm", ["loc_canal", "ch_governor_a"], ONE_TAKE + ", a slow pan following the barges screen-left to screen-right",
     "The sky turns black-green. THE GOVERNOR's barges leave and his men cut the bridge.",
     "Wide over THE CANAL: the long footbridge to the chedi island crosses the frame; golden barges slide away screen-right; THE GOVERNOR stands at the rail of the last barge, his back to the camera, then turning his head over his shoulder.",
     ["[0s] Black-green clouds roll in; the first yellow lightning.",
      "[4s] Two of THE GOVERNOR's men slash the ropes of the long footbridge with long knives.",
      "[8s] The middle of the bridge sags and drops into the water; THE GOVERNOR looks back over his shoulder once and turns away."],
     "Thunder, ropes snapping, timber splashing, a crowd crying out off-screen.",
     ["no people on the falling section of the bridge"])
shot("B05", "B", 8, "storm", ["loc_canal", "ch_kaew_a"], ONE_TAKE + ", a slow push-in on KAEW",
     "KAEW on the broken bridge looks at the chedi across the water.",
     "Medium close-up: KAEW at the broken end of the footbridge, three-quarter view facing screen-left, the cut ropes hanging; behind her at screen-left, far across choppy water, the great chedi under the black-green sky.",
     ["[0s] Wind whips KAEW's hair; rain begins.",
      "[4s] She looks from the broken bridge to the chedi, and decides; she turns and runs out of frame screen-right."],
     "Rising wind, rain, a long thunder roll.")
shot("B06", "B", 12, "storm", ["loc_yai_house-2", "ch_yai_a", "ch_kaew_a", "prop_mallet"], ONE_TAKE + ", camera locked at mat height",
     "YAI'S HOUSE in the storm. YAI BUA, too weak to climb, gives KAEW THE MALLET.",
     "Close two-shot at floor level: YAI BUA lies on her mat at screen-left, head toward screen-right, in profile; KAEW kneels at screen-right facing screen-left toward her, soaked; an oil lamp between them; rain leaking through the zinc roof.",
     ["[0s] YAI BUA presses THE MALLET into KAEW's hands, holding on for a moment.",
      "[4s] YAI BUA, weak, looking into KAEW's eyes: \"If you ring it, ring it right.\"",
      "[9s] KAEW nods once, holding THE MALLET to her chest."],
     "Rain on zinc, drips into a tin bowl, the oil lamp fluttering, YAI BUA's thin voice.",
     [SPEECH_NEG, "YAI BUA does not stand up"],
     lines=[("YAI BUA", "If you ring it, ring it right.")], state="YAI BUA weak, lying on the mat; KAEW wet from the rain")
shot("B07", "B", 6, "storm", ["loc_yai_house-2", "ch_kaew_a", "prop_mallet"], ONE_TAKE + ", a slow tilt down",
     "Insert: THE MALLET in KAEW's hands.",
     "Extreme close-up of KAEW's hands closing around THE MALLET, the red thread wound on its handle, lamp light flickering.",
     ["[0s] Her fingers tighten on the red thread.",
      "[3s] She tucks THE MALLET into the waistband of her chong kraben."],
     "Rain, a heartbeat-slow drum of drips, the lamp.")

# ---- C · The crossing (3:00-5:00) ----
shot("C01", "C", 12, "storm", ["loc_canal", "ch_mek_a", "ch_kaew_a", "prop_mallet"], ONE_TAKE + ", a tracking shot ahead of the boat",
     "MEK rows KAEW through the flooded canals.",
     "Medium shot from the front of a long-tail boat moving toward the camera: MEK standing in the stern rowing hard, facing the camera; KAEW crouched in the bow, facing forward past the camera, THE MALLET in her waistband; flooded houses on both sides.",
     ["[0s] The boat surges forward through waves; rain lashes.",
      "[5s] At screen-right a stilt house folds into the water.",
      "[9s] MEK leans into the oar; KAEW points ahead, screen-left."],
     "Storm wind, waves on the hull, timber cracking, MEK's breath.",
     state="KAEW and MEK soaked and torn by the storm")
shot("C02", "C", 8, "storm", ["loc_city", "ch_kaew_a", "ch_mek_a"], ONE_TAKE + ", a slow lateral dolly screen-right to screen-left",
     "People cling to the rooftops of SUWANNAWARI.",
     "Wide: families on the rooftops of half-flooded houses, holding each other in the rain; the boat with MEK and KAEW small in the foreground passing screen-right to screen-left.",
     ["[0s] A family huddles on a roof ridge; a child clutches a small bell.",
      "[4s] KAEW looks up at them as the boat passes; she does not stop."],
     "Rain, wind, distant cries, a child's bell ringing faintly.")
shot("C03", "C", 8, "storm", ["loc_canal", "ch_mek_a", "ch_kaew_a"], ONE_TAKE + ", a handheld-feeling wide shot",
     "At the broken bridge a wave smashes the boat.",
     "Wide at water level: the broken footbridge at screen-right; the long-tail boat with MEK and KAEW coming from screen-left; a big wave rising behind it.",
     ["[0s] The boat reaches the broken bridge.",
      "[3s] The wave breaks over it; the boat splits against the bridge posts.",
      "[6s] MEK and KAEW are thrown into the water near the posts and grab the floating timbers."],
     "A roaring wave, wood splintering, splashes, a gasp.")
shot("C04", "C", 10, "storm", ["loc_canal", "ch_kaew_a", "prop_mallet"], ONE_TAKE + ", a slow crane following her climb",
     "KAEW climbs the floating wreckage to the island.",
     "Medium wide: a tangle of floating beams and roof panels between the broken bridge at screen-left and the chedi island's stone steps at screen-right; KAEW climbing across them, moving screen-left to screen-right, THE MALLET in her waistband.",
     ["[0s] KAEW pulls herself onto a heaving beam.",
      "[4s] She jumps from beam to roof panel; it tilts and she scrambles on.",
      "[8s] She reaches the stone steps of the island and looks up."],
     "Waves, groaning timber, rain, her breath.")
shot("C05", "C", 10, "storm", ["loc_bell_pavilion", "ch_kaew_a", "ch_mek_a"], ONE_TAKE + ", a slow tilt up the chedi",
     "KAEW begins the climb up the great chedi; MEK holds the line below.",
     "Low wide angle at the base of the great white-and-gold chedi: KAEW, her back to the camera, climbing the steep stair beside a white-and-gold naga rail; MEK at the bottom of the frame, three-quarter view facing up, holding a rope tied around her waist.",
     ["[0s] KAEW climbs, hand over hand; the rope pays out through MEK's hands.",
      "[5s] The camera tilts up the chedi toward THE BELL PAVILION at the top, lit by lightning."],
     "Gale, rain on stone, the rope creaking, thunder.")
shot("C06", "C", 7, "storm", ["loc_bell_pavilion", "ch_kaew_a"], ONE_TAKE + ", camera locked close to the rail",
     "The climb, close.",
     "Close-up from the side: KAEW's wet hands and face beside the carved naga head of the stair rail, rain streaming; she faces screen-left, upward.",
     ["[0s] A gust tears at her tunic; her foot slips.",
      "[3s] She grabs the naga rail's carved fangs, holds, breathes, climbs on."],
     "Howling wind, her gasp, rain hammering stone.")
shot("C07", "C", 8, "storm", ["loc_bell_pavilion", "ch_kaew_a", "prop_great_bell"], ONE_TAKE + ", a slow push-in",
     "THE BELL PAVILION at the top: the bell rope is gone.",
     "Medium wide inside THE BELL PAVILION: THE GREAT BELL hanging at the centre; the snapped end of its rope whipping in the wind; KAEW climbing in at screen-left, facing screen-right toward the bell.",
     ["[0s] KAEW reaches for the rope; it is snapped short, far above her.",
      "[4s] She looks up at THE GREAT BELL, then out past it at the sea, screen-right."],
     "Wind through the open pavilion, the bell humming faintly in the gale.",
     state="THE GREAT BELL whole, not cracked")
shot("C08", "C", 7, "storm", ["loc_city"], ONE_TAKE + ", camera locked",
     "From the top of the chedi: a wave as tall as a mountain on the horizon.",
     "Extreme wide from the chedi's height over the drowned rooftops of SUWANNAWARI to the open sea; on the horizon, a wall of water rising, taller than any mountain, lit by yellow lightning.",
     ["[0s] The wave rises along the whole horizon.",
      "[4s] Lightning shows its height; it is moving toward the city."],
     "A deep, endless roar under the wind.",
     ["no people in frame"])
shot("C09", "C", 14, "storm", ["loc_bell_pavilion", "ch_kaew_a", "prop_great_bell", "prop_mallet"], ONE_TAKE + ", a slow orbit clockwise around KAEW and the bell",
     "KAEW strikes THE GREAT BELL until her hands bleed.",
     "Medium shot: KAEW at THE GREAT BELL, three-quarter view facing screen-right toward the bell, THE MALLET raised in both hands.",
     ["[0s] KAEW strikes THE GREAT BELL with THE MALLET; a huge sound; rain jumps off the bronze.",
      "[5s] Again and again; the camera orbits; THE MALLET slips from her bloodied hands.",
      "[10s] She strikes the bell with her bare palms; the sound grows instead of fading."],
     "Enormous bronze strikes, each one longer than the last, the wind tearing, her cries of effort.",
     ["no blood spray, only red on her palms"])
shot("C10", "C", 8, "storm", ["loc_city", "loc_bell_pavilion"], ONE_TAKE + ", a fast aerial pull-back from the pavilion",
     "The sound of THE GREAT BELL fills the sky over SUWANNAWARI.",
     "Aerial: THE BELL PAVILION at the top of the chedi at the centre, the drowned city all around.",
     ["[0s] A visible ring of shock in the rain spreads out from THE BELL PAVILION.",
      "[4s] As it passes, every small bell in the city rings by itself; the rain hangs for an instant."],
     "One vast bell note, then thousands of small bells answering together.")

# ---- D · The chain (5:00-6:15) ----
shot("D01", "D", 15, "storm", ["loc_city", "ch_naga_a-2", "loc_bell_pavilion"], ONE_TAKE + ", an extreme wide with a slow push-in toward the head",
     "Silence, then PHAYA NAK rises from the sea.",
     "Extreme wide from the edge of SUWANNAWARI toward the sea, the great chedi at screen-right.",
     ["[0s] Silence. The sea beyond the city bulges into a dome.",
      "[4s] PHAYA NAK rises out of the water, colossal, taller than the chedi, water pouring off its jade-and-gold scales.",
      "[10s] Its amber eyes open; people on the rooftops raise their arms."],
     "Silence, then a deep rumble, rushing water, distant cheering.",
     ["only one head", "no wings, no legs", "no red or blue scales"], state="PHAYA NAK awake")
shot("D02", "D", 8, "storm", ["loc_city", "ch_mek_a", "ch_naga_a-2"], ONE_TAKE + ", camera locked",
     "MEK on the wreckage looks up at PHAYA NAK.",
     "Medium shot: MEK clinging to a floating beam at screen-left, three-quarter view facing up and screen-right; far behind him at screen-right, PHAYA NAK towering over the city.",
     ["[0s] MEK wipes rain from his eyes and stares up, mouth open.",
      "[4s] He laughs once in disbelief as rooftop crowds cheer behind him."],
     "Cheering, rain, the Naga's breath like wind.")
shot("D03", "D", 12, "storm", ["loc_canal", "ch_naga_a-2", "ch_governor_a"], ONE_TAKE + ", a wide tracking shot following the tail",
     "PHAYA NAK roars; its tail capsizes THE GOVERNOR's golden barge.",
     "Wide over open water: THE GOVERNOR's golden barge at screen-right, crowded with his men and chests of gold; the huge jade tail of PHAYA NAK rising from the water at screen-left.",
     ["[0s] PHAYA NAK roars off-screen; the storm doubles; waves rise.",
      "[4s] The tail sweeps from screen-left to screen-right and strikes the barge.",
      "[8s] The barge rolls over; THE GOVERNOR clings to the rail, gold chests sliding into the sea."],
     "A colossal roar, thunder, splintering gilt wood, screams.")
shot("D04", "D", 8, "storm", ["loc_bell_pavilion", "prop_great_bell", "ch_kaew_a"], ONE_TAKE + ", a slow push-in to the engraving",
     "KAEW sees the engraving on THE GREAT BELL.",
     "Close-up: KAEW's face at screen-left in profile facing screen-right; beside her the surface of THE GREAT BELL, lightning revealing an engraving of a naga bound in chains.",
     ["[0s] Lightning flashes; KAEW sees the engraving.",
      "[4s] The camera pushes in on the chained naga in the bronze."],
     "A low hum from the bell, thunder.")
shot("D05", "D", 10, "storm", ["loc_bell_pavilion", "prop_great_bell", "ch_kaew_a"], ONE_TAKE + ", camera locked",
     "KAEW understands; THE GREAT BELL cracks.",
     "Medium close-up: KAEW at screen-left, three-quarter view facing screen-right toward THE GREAT BELL, bloodied hands at her sides.",
     ["[0s] KAEW, barely a whisper: \"No... I woke it.\"",
      "[4s] A crack runs down one side of THE GREAT BELL with a sharp ringing snap.",
      "[7s] KAEW steps back."],
     "Her whisper, then a splitting crack of bronze and a dying tone.",
     [SPEECH_NEG], lines=[("KAEW", "No... I woke it.")], cont="D04")
shot("D06", "D", 8, "storm", ["loc_city", "ch_naga_a-2"], ONE_TAKE + ", a slow push-in on the neck",
     "The chain breaks: the bronze bands fall from PHAYA NAK's neck.",
     "Close on PHAYA NAK's neck against the storm sky, the old bronze bands sunk into its scales.",
     ["[0s] The bronze bands crack in the same instant as the bell.",
      "[4s] They burst apart and fall away into the sea; the scales beneath glow gold."],
     "Cracking metal, a deep exhale, rain.")

# ---- E · The lullaby (6:15-8:00) ----
shot("E01", "E", 12, "storm", ["loc_bell_pavilion", "ch_naga_a-2", "ch_kaew_a"], ONE_TAKE + ", camera locked",
     "PHAYA NAK lowers its head to the top of the chedi, eye to eye with KAEW.",
     "Wide inside THE BELL PAVILION: KAEW at screen-left, small, facing screen-right; the open side of the pavilion at screen-right filled by PHAYA NAK's descending head.",
     ["[0s] The head of PHAYA NAK sinks into frame from above, screen-right.",
      "[5s] One amber eye, bigger than KAEW, stops a few metres from her.",
      "[9s] KAEW does not move."],
     "The Naga's breath like a storm wind, rain, silence from the city.",
     state="PHAYA NAK listening, head low")
shot("E02", "E", 6, "storm", ["loc_bell_pavilion", "ch_mek_a"], ONE_TAKE + ", camera locked low",
     "MEK, far below, screams up at KAEW.",
     "Low angle from the base of the chedi: MEK at screen-centre, facing up and away from the camera at three-quarter rear view, his head tilted so his mouth shows, the rope slack in his hands.",
     ["[0s] MEK, desperate: \"Kaew, run!\""],
     "His shout, swallowed by wind.",
     [SPEECH_NEG], lines=[("MEK", "Kaew, run!")])
shot("E03", "E", 8, "memory", ["loc_yai_house-2", "ch_yai_a", "ch_kaew_a"], ONE_TAKE + ", a slow drift",
     "Memory: YAI BUA singing in her house.",
     "Medium close-up, warm lamp light: YAI BUA at screen-left facing screen-right toward KAEW, who is at screen-right, younger and dry, in three-quarter view.",
     ["[0s] YAI BUA taps the small bells: three slow, one fast.",
      "[3s] YAI BUA, gently, to KAEW: \"The great one has only one song.\""],
     "Soft bells, the lamp, YAI BUA's voice slightly echoing.",
     [SPEECH_NEG], lines=[("YAI BUA", "The great one has only one song.")], state="KAEW dry, a memory of the afternoon")
shot("E04", "E", 15, "storm", ["loc_bell_pavilion", "ch_kaew_a", "prop_great_bell", "prop_mallet", "ch_naga_a-2"], ONE_TAKE + ", a very slow push-in on KAEW",
     "KAEW taps the cracked bell and sings the lullaby to PHAYA NAK.",
     "Medium shot: KAEW beside THE GREAT BELL, now cracked down one side, three-quarter view facing screen-right toward the amber eye of PHAYA NAK, which fills the right edge of the frame.",
     ["[0s] KAEW lifts THE MALLET and taps the cracked bell: three slow, one fast.",
      "[4s] KAEW, singing softly in Thai, to the eye: \"" + LULLABY_TH + "\"",
      "[12s] She taps again: three slow, one fast."],
     "A small cracked bell tone, KAEW's thin clear singing voice in Thai, the wind falling.",
     [SPEECH_NEG, "she sings only the Thai words in the quotation marks"],
     lines=[("KAEW (sings, Thai)", LULLABY_TH)], state="THE GREAT BELL cracked down one side")
shot("E05", "E", 8, "storm", ["ch_naga_a-2", "loc_bell_pavilion"], ONE_TAKE + ", camera locked, extreme close-up",
     "PHAYA NAK listens and closes its eye.",
     "Extreme close-up of one amber eye of PHAYA NAK, rain running over the gold-rimmed scales around it, the cracked pavilion reflected in the eye.",
     ["[0s] The slit pupil widens.",
      "[4s] The eye slowly closes."],
     "Faint lullaby humming off-screen, a long slow breath, rain easing.")
shot("E06", "E", 12, "storm", ["loc_city", "ch_naga_a-2"], ONE_TAKE + ", a high aerial slowly circling clockwise",
     "PHAYA NAK coils around SUWANNAWARI and rises as a living wall.",
     "High aerial over the whole city: the great chedi at the centre, the sea all around.",
     ["[0s] The huge jade body of PHAYA NAK slides through the water around the outer edge of the city.",
      "[5s] It closes the ring and rises out of the water, a wall of scales higher than the rooftops.",
      "[10s] The wave arrives on the horizon."],
     "Rushing water, a deep steady breath, the approaching roar.")
shot("E07", "E", 10, "storm", ["loc_city", "ch_naga_a-2"], ONE_TAKE + ", camera locked wide from inside the city",
     "The great wave breaks on PHAYA NAK's body.",
     "Wide from a rooftop inside the city: the coiled wall of PHAYA NAK's body across the frame, the sky above it.",
     ["[0s] The wall of water rises behind the coil.",
      "[4s] It breaks against the scales and explodes into spray, falling back to the sea.",
      "[8s] Spray rains down on the rooftops; the coil holds."],
     "A thunderous crash, then falling water like heavy rain, then quiet.")
shot("E08", "E", 15, "dawn", ["loc_bell_pavilion", "loc_city", "ch_kaew_a", "ch_mek_a", "ch_naga_a-2", "prop_great_bell", "prop_mallet"], ONE_TAKE + ", a slow crane up",
     "Dawn after the storm. KAEW is the new keeper of PHAYA NAK.",
     "Medium wide in THE BELL PAVILION: the head of PHAYA NAK resting at screen-right; KAEW sitting at screen-left facing it, THE MALLET across her knees; THE GREAT BELL lying broken.",
     ["[0s] KAEW rests one hand on the Naga's scales.",
      "[5s] Far below, MEK rows a small boat toward the island and waves up.",
      "[9s] The camera cranes up: SUWANNAWARI standing, the sleeping coil around it."],
     "Dawn wind, water, small bells chiming, the Naga's slow breath.",
     state="PHAYA NAK asleep, eyes closed; KAEW's hands bound in crimson cloth")
shot("E09", "E", 7, "dawn", ["loc_yai_house-2", "ch_yai_a"], ONE_TAKE + ", camera locked",
     "YAI BUA hears the little bells at dawn.",
     "Medium close-up: YAI BUA on her mat at screen-left, propped up, facing screen-right toward a window where the bamboo rail of small brass bells catches the dawn light.",
     ["[0s] The little bells chime in the dawn breeze.",
      "[3s] YAI BUA smiles and closes her eyes, at peace."],
     "The little bells, three slow and one fast, by themselves.")
shot("E10", "E", 12, "dawn", ["loc_city", "ch_naga_a-2"], ONE_TAKE + ", a slow aerial pull-back and rise",
     "Final image: SUWANNAWARI and the sleeping PHAYA NAK.",
     "Aerial from above the chedi pulling back: the city, the coil of PHAYA NAK around it, the calm sea gold-green to the horizon; open sky at the top third left clear.",
     ["[0s] The camera pulls back and rises over the chedi.",
      "[6s] The whole city and the sleeping coil come into view; the sea is calm."],
     "Thousands of small bells in a light wind; one low bell note at the end.",
     ["no people close to the camera"])

def paste_block(s, with_cont=False):
    refs = list(s["refs"])
    out = [f"15 seconds · 720p · 16:9 · {s['take']}.", s["heading"]]
    decl = [f"@ภาพ{i} — {REF_JOB[r]}." for i, r in enumerate(refs, 1)]
    if with_cont and s["cont"]:
        n = len(refs)
        decl.append(f"@ภาพ{n+1}, @ภาพ{n+2}, @ภาพ{n+3} — the last three frames of the previous moment, oldest first: continue directly from @ภาพ{n+3}, same place, same light, same positions.")
    out.append("REFERENCES: " + " ".join(decl))
    names = [k for k, r in (("KAEW", "ch_kaew_a"), ("YAI", "ch_yai_a"), ("MEK", "ch_mek_a"), ("GOV", "ch_governor_a"), ("NAGA", "ch_naga_a-2")) if r in refs]
    if names:
        out.append("WHO: " + " ".join(WHO[n] + "." for n in names))
    out.append("THE FRAME: " + s["frame"])
    if s.get("state"):
        out.append("STATE: " + s["state"] + ".")
    out.append("WHAT HAPPENS: " + " ".join(s["beats"]))
    out.append("SOUND: " + s["sound"])
    out.append(GRADE[s["grade"]])
    out.append("CRITICAL NEGATIVES: " + "; ".join(s["negs"] + [HOUSE_NEG]) + ".")
    return "\n".join(out)

def main():
    (HERE / "shots").mkdir(exist_ok=True)
    jobs, sb, sc = [], [], []
    t = 0
    for s in S:
        block = paste_block(s, with_cont=True)
        n_refs = len(s["refs"]) + (3 if s["cont"] else 0)
        assert n_refs <= 9, f"{s['id']} needs {n_refs} reference slots; champa holds 9"
        assert len(block) <= LIMIT, f"{s['id']} prompt is {len(block)} characters; champa refuses over {LIMIT}"
        notes = [f"Shot {s['id']} · scene {s['scene']} · target length in the cut {s['cut']} s · grade {s['grade']}",
                 "References in upload order: " + ", ".join(f"@ภาพ{i}={r}" for i, r in enumerate(s["refs"], 1))
                 + (f", then the last 3 frames of {s['cont']} (-1.0 s, -0.5 s, last)" if s["cont"] else ""),
                 "Built by build_shots.py; edit the table there and rebuild."]
        (HERE / "shots" / f"{s['id']}.txt").write_text(
            "=== NOTES · DO NOT PASTE ANY OF THIS ===\n" + "\n".join(notes) + "\n=== END NOTES ===\n\n"
            "=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes, never paste it ===\n" + block +
            "\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes, never paste it ===\n")
        if not s["cont"]:
            jobs.append({"id": "lb-" + s["id"], "refs": s["refs"], "prompt": block})
        mm, ss = divmod(t, 60); t += s["cut"]
        sb.append(f"| {s['id']} | {mm}:{ss:02d} | {s['cut']} s | {s['heading']} | {s['take'].split(',')[-1].strip()} | "
                  + ", ".join(s["refs"]) + (f" + 3 frames of {s['cont']}" if s["cont"] else "") + " |")
        for who, line in s["lines"]:
            sc.append((s["id"], who, line))
    (HERE / "jobs-wave1.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=1))
    mm, ss = divmod(t, 60)
    (HERE / "STORYBOARD.md").write_text(
        "# STORYBOARD.md — THE LAST BELL (generated by build_shots.py, do not edit)\n\n"
        f"{len(S)} shots, {mm}:{ss:02d} of cut time. Each clip renders 15 s; the cut uses the target length.\n"
        "Reference slots: champa holds 9 (@ภาพ1..@ภาพ9, measured 2026-10-03). A continue shot spends 3 of them on the\n"
        "previous clip's last frames, so it carries at most 6 others. Prompt files: shots/<id>.txt.\n\n"
        "| Shot | Starts | Cut | What | Camera | References (upload order) |\n|---|---|---|---|---|---|\n" + "\n".join(sb) + "\n")
    (HERE / "SCRIPT.md").write_text(
        "# SCRIPT.md — THE LAST BELL, every spoken line (generated by build_shots.py, do not edit)\n\n"
        "English in-clip dialogue; the lullaby is sung in Thai. Story and beats: BIBLE.md §4; shots: STORYBOARD.md.\n\n"
        "| Shot | Who | Line |\n|---|---|---|\n" + "\n".join(f"| {i} | {w} | {l} |" for i, w, l in sc) + "\n")
    print(len(S), "shots,", f"{mm}:{ss:02d}", "cut time,", len(jobs), "wave-1 jobs,", len(sc), "lines")

if __name__ == "__main__":
    main()
