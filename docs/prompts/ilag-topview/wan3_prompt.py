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
CAP = 3500

spec = importlib.util.spec_from_file_location("build", HERE / "build.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def token(i, style):
    return f"@Image {i}" if style == "at" else f"<<<Image{i}>>>"


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="+")
    ap.add_argument("--token", choices=["at", "angle"], default="at")
    ap.add_argument("--out", type=Path, default=HERE / "wan3")
    ap.add_argument("--seconds", type=float, help="a shorter test clip: drop the beats that start at or after it")
    ap.add_argument("--suffix", default="", help="added to the output name, e.g. -rehearsal")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    by_key = {f"{s.get('prefix', 'm')}{s['n']:02d}": s for s in B.SCENES}
    for k in a.keys:
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
