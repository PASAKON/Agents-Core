"""Turn a built H3 shot into a Wan 3.0 (TopView) prompt: positional image references, at most 3,500 characters.

    python3 wan3_prompt.py n01 [n02 ...] [--token at|angle] [--out DIR]

For each shot key (o01, m04, n13, ...) writes <out>/<key>.wan3.json:
    {key, title, seconds, images: [Drive paths under Element/, in upload order], prompt, chars}
CTO_Wan3.0_TopView §5 is the checklist this follows: uploads in first-mention order, each @Handle replaced by
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
        text = sc.get("ref_override", {}).get(h, B.REF[h][1])
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
    "g2": ["o03", "o04", "m04"],          # paid
    "g7": ["n01", "n10", "m13"],          # paid, natural length (the three wide/aerial shots)
}
LONG_TAKE = dict(
    prefix="x", n=0, slug="the-catch-to-the-eyes", title="ONE LONG TAKE: THE CATCH UNTIL THE EYES OPEN", s=30,
    grade="DARK", grade_override="DARK_GLOW",
    spec="ONE CONTINUOUS TAKE, NO CUTS. It starts as a medium shot beside THE MOUNT at the surface and, without any cut, "
         "slowly pulls back and rises until THE MOUNT is small in the lower third with the far black water filling "
         "the frame above; then it holds.",
    refs=["@Strong", "@Young", "@Elder", "@Turning", "@Mountain", "@Eye"],
    ref_override={"@Turning": B.TURNING_IN_CIRCLE,
                  "@Eye": "THE CREATURE, the only picture of it: take its broad flat smooth dark head, its two enormous "
                          "pale yellow-green eyes with thin vertical slit pupils and its scale exactly; nothing of the "
                          "light around it."},
    light_extra="Far beyond the circle the rising mountain is only a vast blacker shape against the dark; its two eyes, "
                "when they open, glow pale yellow-green on their own, the only other light in this shot.",
    heading="THE CATCH, AND WHAT WAS WATCHING. One unbroken take from their first fish to the creature's eyes.",
    frame="Starts medium, beside THE MOUNT at the surface: THE STRONG ONE leaning over the edge of the seat, THE YOUNG "
          "ONE glowing beside him, THE ELDER behind; ends wide from behind and above, THE MOUNT small on flat black "
          "water in the rain.",
    particles="rain, water splashing up as hands go in, golden motes around THE YOUNG ONE, mist over the flat water.",
    actions=["THE STRONG ONE, front perch: chases a fish shadow with both hands and snatches it out, holds it up "
             "laughing, then lies across the front of the seat grabbing at more fish with both arms in the water, "
             "completely absorbed; he only looks up when THE YOUNG ONE shakes his shoulder, and his hands stop.",
             "THE YOUNG ONE, middle, glowing: points where the fish goes, jumps up and down cheering at the catch, "
             "then sits on the edge kicking both feet in the water to herd fish, giggling; notices THE ELDER staring "
             "for a long time, follows THE ELDER's gaze, goes still, then shakes THE STRONG ONE's shoulder hard.",
             "THE ELDER, back: grips THE STRONG ONE's kelp belt so THE STRONG ONE cannot fall in, claps him on the back "
             "at the catch, rinses the fish over the side, then stops, slowly lifts his head and stares ahead at the "
             "far water, the fish forgotten in his hands."],
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
           "[26s] High on the mountain two enormous eyes open: pale yellow-green, thin vertical slit pupils, each "
           "bigger than their whole village, looking down at them. Hold."],
    sound="splashes, THE STRONG ONE's effort, wordless cheering and laughter, THE YOUNG ONE's giggle, then THE YOUNG "
          "ONE's sharp gasp, then total silence as the eyes open; no words",
    crit=B.NO_WORDS + ", no cut, no net, no spear, no hook, no one falling in, no roar, no teeth, no third eye, no waves, "
         "no light wider than 2 metres around the child, no eyes before the last beat",
)
GROUP_LENGTHS = {"g5": {"n06": 7, "n07": 13, "n13": 10}}
GROUP_NATURAL = {"g7"}  # paid: no stretch, fewer seconds, fewer credits
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
    if gkey not in GROUP_NATURAL:
        scs = stretch(scs, GROUP_SECONDS, GROUP_LENGTHS.get(gkey))
    order, jobs = [], {}
    for sc in scs:
        for h in sc["refs"]:
            if h not in order:
                order.append(h)
            jobs.setdefault(h, set()).add(sc.get("ref_override", {}).get(h, B.REF[h][1]))
    if len(order) > 10:
        raise SystemExit(f"{[tag(s) for s in scs]}: {len(order)} pictures, the Wan3 cap is 10")
    refs = []
    for i, h in enumerate(order, 1):
        text = next(iter(jobs[h])) if len(jobs[h]) == 1 else B.REF[h][1]
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
        sec = [f"SHOT {i} of {len(scs)}, from {start:g}s to {end:g}s: {sc['title']}. {_inside_shot(sc['spec'])}",
               sc["heading"], "THE FRAME: " + sc["frame"]]
        if B.STATE.get(key):
            sec.append("STATE: " + B.STATE[key])
        if key in B.DARK_LIT:
            sec.append("THE LIGHT: " + B.LIGHT + (" " + sc["light_extra"] if sc.get("light_extra") else ""))
        if sc.get("particles"):
            sec.append("PARTICLES: " + sc["particles"])
        if MOOD.get(tag(sc)):
            sec.append(MOOD[tag(sc)])
        if sc.get("actions"):
            sec.append("EACH CHARACTER, ALL THROUGH THE SHOT (each busy with their own action, never all the same):\n"
                       + "\n".join("- " + a for a in sc["actions"]))
        sec += ["WHAT HAPPENS:\n" + "\n".join(beats),
                f"Sound in this shot: only the sounds the characters make themselves: {snd}. No music, no ambient sound.",
                B.GRADE[sc.get("grade_override", sc["grade"])],
                # CEO 2026-09-26 ("No Music แบบ Seedance"): the house-negatives wall is dropped for Wan3, so its music
                # ban is repeated in every shot's own negatives, not only in the sound line.
                "Avoid in this shot: " + _inside_shot(sc["crit"]) + ", no music, no score, no background music."]
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
    for k in a.keys:
        if k in GROUPS:
            text, order, total = render_group([by_key[x] for x in GROUPS[k]], a.token, k)
            if len(text) > CAP:
                raise SystemExit(f"{k}: {len(text)} characters > {CAP}")
            job = {"key": k, "title": " + ".join(by_key[x]["title"] for x in GROUPS[k]), "seconds": total,
                   "shots": GROUPS[k], "images": [B.REF[h][0] for h in order], "prompt": text, "chars": len(text)}
            (a.out / f"{k}{a.suffix}.wan3.json").write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"{k} {len(text):5d} chars {len(order)} images {total}s {GROUPS[k]}")
            continue
        sc = by_key[k]
        if a.seconds:
            keep = [b for b in sc["beats"] if float(re.match(r"\[([\d.]+)s\]", b).group(1)) < a.seconds]
            sc = dict(sc, s=int(a.seconds) if a.seconds == int(a.seconds) else a.seconds, beats=keep)
        # CTO_Wan3.0_TopView §5 step 3, in order: short references, the dialogue negatives and the grade tail, the mount
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
        job = {"key": k, "title": sc["title"], "seconds": sc["s"], "images": [B.REF[h][0] for h in sc["refs"]],
               "prompt": text, "chars": len(text)}
        (a.out / f"{k}{a.suffix}.wan3.json").write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{k} {len(text):5d} chars {len(sc['refs'])} images {sc['s']}s trim-level {level}")


if __name__ == "__main__":
    main()
