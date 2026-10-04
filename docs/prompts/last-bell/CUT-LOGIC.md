# THE LAST BELL — cut logic (2026-10-04)

The CEO's test (2026-10-04): every cut from shot A to shot B needs a reason the viewer can follow; if it cannot be
explained, the film is not done well. His example: Kaew sits with her grandmother, and the next shot has her in a boat.
Rule: `CMO_Workflow_ShortFilm` §Step 4 (8f059680). This table covers the single main line; the film's parallel lines
(the Governor, the Naga, Mek below) are switches, checked for a reason rather than a bridge.

Checked against the real first and last frames of the locked takes (`lb_out/qc/inout.tsv` in the work set), not the
storyboard. Two takes differ from the board: A05 is lit as morning, not afternoon; in A07 Kaew sits on a landing,
not in the boat.

| Cut | Reason the viewer gets | Verdict | Fix |
|---|---|---|---|
| A01 → A02 → A03 | dawn town, the bells on Yai's eave, Yai's porch | OK | |
| A03 → A04 | Kaew runs to work, then rings the morning bell | OK | |
| A04 → A05 | bell pavilion to Yai's house: nothing brings her there | GAP | bridge A04b: she comes home; Yai: "I heard the bell. You rang it well." |
| A05 → A05b → A06 | same lesson continued; hands insert | OK | |
| A06 → A07 | sitting with Yai, then by Mek's boat: the CEO's example | GAP | bridge A06b: Mek calls from outside, Yai nods, Kaew runs out |
| A07 → A08 | Kaew on the landing, then a yellow lagoon nobody looks at | GAP | bridge A07b: she drops into the boat, the water turns yellow, both stare down |
| A08 → B01 | dawn omen to the Governor at dusk (switch, time jump) | edit | gong over the cut, dissolve |
| B01 → B02 | the kids look up at the Governor (switch, eyeline) | OK | |
| B02 → B03 | in the boat, then on the temple sala | GAP | bridge B02b: Mek brings her to the sala; the old boatman: "Sit, child. Listen." |
| B03 → B04 | the legend, then the Governor's men cut the bridge (switch) | edit | thunder over the cut |
| B04 → B05 | the bridge falls, then Kaew is standing on it | GAP | bridge B04b: she runs along the footbridge and finds it cut |
| B05 → B06 | the broken bridge, then home with Yai | GAP | bridge B05b: she bursts in from the storm: "Yai! They cut the bridge!" |
| B06 → B07 | Yai gives the mallet; insert on the mallet | OK | |
| B07 → C01 | indoors with the mallet, then already in Mek's boat | GAP | bridge B07b: she shouts for Mek from the ladder and climbs into his boat |
| C01 → C06 | what they pass, the wave, the wreck, the stairs, the climb | OK | |
| C06 → C08 | climbing, then already at the top (C07 was cut) | GAP | bridge C07-v2: she climbs into the pavilion, sees the bell, a roar turns her to the sea |
| D01 → D06 | the Naga, Mek below, Kaew at the bell: the same moment in three places (switches) | OK | |
| E01 → E02 | eye to eye with the Naga; Mek screams from below (switch) | OK | |
| E02 → E03 | Mek screaming, then Yai's memory with no trigger | GAP | bridge E02b: she closes her eyes; faint wrist bells like Yai's |
| E07 → E08 | the wave, then dawn | edit | dissolve |

Nine bridges are queued on the free lane (`lb_build_v3.py`), each cut to 4–7 s, about 36–63 s in all. Three of them
(A06b, A07b, C07-v2) continue from the last three frames of the shot before, the method T1-A proved on A05b-A.
