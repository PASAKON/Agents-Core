"""EP01 v3: write the arc edit config and the music bed for one arc from v3/<key>/timing.json.
Usage: make_cfg_music.py <th1|th3|en1|en3>
The picture config is the v2 no-text config with the new voice, section starts and end; mood beds move with the sections (bed.py)."""
import json, subprocess, sys
W = "/opt/MoonieXHQ/Work/cn-series"; key = sys.argv[1]; lang, n = key[:2], key[2]
t = json.load(open(f"{W}/voice/v3/{key}/timing.json")); sec, end = t["sec_new"], t["end_new"]
nt = {"th1": "arc1_cfg_nt", "en1": "arc1_en_cfg_nt", "th3": "arc3_th_cfg_nt", "en3": "arc3_en_cfg_nt"}[key]
cfg = f"{W}/cut/{nt.replace('_nt', '_v3')}.py"
open(cfg, "w").write(
    f'exec(open("{W}/cut/{nt}.py").read())\n# EP01 v3: v2 (no on-screen text) + narrator inserts; voice, section starts and end moved by the inserts\n'
    f'VO = "{W}/voice/v3/{key}/{key}_voice.wav"\nSEC = {sec!r}\nEND = {end!r}\nTMP = TMP[:-3] + "_v3"\n')
MOOD = {"1": [(0, "playful"), (5, "sad"), (8, "playful"), (10, "tense"), (14, "playful"), (19 if lang == "th" else 20, "tense")],
        "3": [(0, "sad"), (1, "playful"), (3, "tense"), (6, "playful"), (7, "tense")]}[n]
music = {"th1": "arc1_music", "en1": "en1_music", "th3": "arc3_th_music", "en3": "arc3_en_music"}[key]
out = f"{W}/music/{music}_v3.wav"
subprocess.run(["/opt/MoonieXHQ/Agents/Core/.venv/bin/python", f"{W}/music/bed.py", out, str(end), *[f"{m}:{sec[i]}" for i, m in MOOD]], check=True)
print(cfg, out)
