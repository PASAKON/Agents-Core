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
GROUPS = {
    "g1": ["o01", "o02"],
    "g2": ["o03", "o04", "m04"],
    "g3": ["n01", "n02", "n03"],
    "g4": ["m06", "n04", "n12", "n05"],
    "g5": ["n06", "n07", "n13"],
    "g6": ["n09", "n10", "n11"],
    "g7": ["m13"],
}


def _inside_shot(text):
    """A shot's own 'no cut' rules apply inside that shot only; the group is joined by hard cuts."""
    text = re.sub(r"ONE CONTINUOUS TAKE, NO CUTS\.", "Within this shot: one continuous take.", text)
    text = re.sub(r"ONE LOCKED SHOT, NO CUTS\.", "Within this shot: one locked shot.", text)
    return re.sub(r"\bno cuts?\b", "no cut inside this shot", text)


def render_group(scs, style):
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
        beats = [re.sub(r"\[(\d+(?:\.\d+)?)s\]", lambda m: f"[{start + float(m.group(1)):g}s]", b) for b in beats]
        snd = sc.get("sound") or B.SOUND.get(key, "silence; nobody speaks")
        sec = [f"SHOT {i} of {len(scs)}, from {start}s to {end}s: {sc['title']}. {_inside_shot(sc['spec'])}",
               sc["heading"], "THE FRAME: " + sc["frame"]]
        if B.STATE.get(key):
            sec.append("STATE: " + B.STATE[key])
        if key in B.DARK_LIT:
            sec.append("THE LIGHT: " + B.LIGHT + (" " + sc["light_extra"] if sc.get("light_extra") else ""))
        if sc.get("particles"):
            sec.append("PARTICLES: " + sc["particles"])
        if sc.get("actions"):
            sec.append("EACH CHARACTER, ALL THROUGH THE SHOT (each busy with their own action, never all the same):\n"
                       + "\n".join("- " + a for a in sc["actions"]))
        sec += ["WHAT HAPPENS:\n" + "\n".join(beats),
                f"Sound in this shot: only the sounds the characters make themselves: {snd}. No music, no ambient sound.",
                B.GRADE[sc.get("grade_override", sc["grade"])],
                "Avoid in this shot: " + _inside_shot(sc["crit"]) + "."]
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
    for k in a.keys:
        if k in GROUPS:
            text, order, total = render_group([by_key[x] for x in GROUPS[k]], a.token)
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
