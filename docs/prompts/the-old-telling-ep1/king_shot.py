#!/usr/bin/env python3
"""The Old Telling EP1 ACT 1: the ONE new shot, the king's line (4 s request = 107 frames = 4.46 s, 1080p).

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/king_shot.py            # write files, no studio call
    .venv/bin/python -I docs/prompts/the-old-telling-ep1/king_shot.py --fire     # also upload the line + enqueue

CEO 2026-10-10: "อนุมัติงบ ทำ ACT 1 ออกมาได้เลย"; "Colab ถูกเปิดอยู่ ฉัน Generate หนังของฉันไว้อยู่ ห้ามแอบดู Prompt และ ภาพ
คุณใส่คิวต่อจากนั้นได้เลย". So: this script prints ONLY ids of the row it creates, never the queue, never anyone's prompt.
Rules reused from build.py / h3_setup.py: each @ref exactly once, adult 18+, no blush/red ears, refuses unless the
studio h3Model equals --model (the CEO owns that setting), narration is never bound to H3.
The line in <Audio 1> is the Thai king take (Brian); H3's own voicing is muted in the edit and the real line is laid at the mouth window.
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import build  # REFS, GRADE, HOUSE_NEG
import h3_setup as h

SCRATCH = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
LINE = SCRATCH / "voice2/out/act1_c1_king_brian.mp3"
AUDIO = HERE / "shots" / "king_line_4s.mp3"
SECONDS, QUALITY, ASPECT = 4, "1080p", "16:9"  # studio rules: 4 s rounds to 107 frames = 4.46 s
SPEAK_FROM, SPEAK_TO = 0.6, 3.4
REFS = ["THRONES", "KING"]

SPEECH = ("<Audio 1> is the finished dialogue track of this shot.\n"
          "<Audio 1>: fully_copy - the soundtrack plays <Audio 1> exactly as given: the same voice, the same line, the same timing.\n"
          f"Speech timing: THE KING OF THE DEAD speaks from {SPEAK_FROM} s to {SPEAK_TO} s. He moves the lips only inside that window and keeps the mouth closed at every other moment.")

TEXT = "\n".join([
    f"4s · {QUALITY} · {ASPECT} · ONE CONTINUOUS TAKE, NO CUTS. Camera static, very slow drift toward the king; no zoom, no cut.",
    "",
    "THE HALL OF THE DEAD. THE KING OF THE DEAD sits on his black stone throne, looks at a visitor we do not see, and speaks one short line.",
    "",
    "REFERENCES, each with a job:",
    build.REFS["THRONES"],
    build.REFS["KING"],
    "",
    ("THE FRAME: Medium shot across a vast dark cavern hall. THE KING OF THE DEAD sits on the left black stone throne, centre-left of the frame, "
     "seen from the knees up, his body and face in three-quarter view toward screen-left, toward a visitor who is out of frame. "
     "THE QUEEN OF THE DEAD sits on the right throne at the right edge, still, her face half in shadow, also turned toward screen-left. "
     "THE KING fills about half of the frame height. The only warm light is a faint ember glow from screen-left on THE KING's face; the hall is cold verdigris dark."),
    "",
    "WHAT HAPPENS:",
    "[0s] THE KING sits still and stern, his eyes on the visitor at screen-left; THE QUEEN does not move. A cold wind stirs the hem of his robe.",
    f"[{SPEAK_FROM}s] THE KING speaks one line to the visitor: his jaw and lips move, his eyes toward screen-left, his voice low and even. His right hand rests on the arm of the throne.",
    f"[{SPEAK_TO}s] THE KING lowers his chin in one slow nod; his right hand lifts a little toward screen-left and settles again.",
    "[3.8s] Hold: everyone stays where they are, no speech, no new action; only a low cold wind.",
    "",
    "overall_soundscape: only the sounds of the place and of THE KING: a low cold wind in a stone hall, the faint move of heavy cloth, and the one spoken line from <Audio 1>. No other voices, no singing.\nnon_diegetic_music: none.",
    "",
    SPEECH,
    "",
    build.GRADE,
    "",
    ("CRITICAL NEGATIVES: no ORPHEUS in the shot, no third person, no second king, no skulls, no bones, no fire pits, no demons, "
     "no speaking anything except the line in <Audio 1>, no stage directions spoken aloud, no singing, nothing new starts after 3.8 seconds."),
    "",
    build.HOUSE_NEG,
])


def check(text):
    for k in REFS:
        n = len(re.findall(r"@" + k + r"\b", text))
        if n != 1:
            sys.exit(f"@{k} appears {n} times (rule 2: exactly once)")
    for bad in ("blush", "flushed", "red cheek", "red ear", "หน้าแดง", "หูแดง"):
        for m in re.finditer(bad, text):
            if "no " not in text[max(0, m.start() - 4):m.start()]:
                sys.exit(f"'{bad}' outside the closing negation")
    if "[3.8s] Hold" not in text:
        sys.exit("no hold beat")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fire", action="store_true"); ap.add_argument("--model", default="cobijada")
    a = ap.parse_args()
    check(TEXT)
    notes = (f"=== NOTES · DO NOT PASTE ANY OF THIS ===\nE05 THE KING SPEAKS · {SECONDS}s request (107 frames, 4.46 s) · {QUALITY} · {ASPECT} · The Old Telling EP1 ACT 1\n"
             f"Entities (group 'The Old Telling'): {', '.join('@' + k for k in REFS)}. Audio bound: king_line_4s.mp3 (Thai king take, speech {SPEAK_FROM} to {SPEAK_TO} s).\n"
             "Narration is NOT in this clip; it is mixed in the edit. H3's own voicing is muted there.\n=== END NOTES ===\n\n")
    (HERE / "shots" / "e05.txt").write_text(notes + "=== ↓↓↓ PASTE FROM HERE ↓↓↓ ===\n\n" + TEXT + "\n\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ ===\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(LINE), "-af", f"adelay={int(SPEAK_FROM*1000)}|{int(SPEAK_FROM*1000)},apad=whole_dur=4.46",
                    "-t", "4.46", "-ar", "44100", "-ac", "1", "-b:a", "128k", str(AUDIO)], check=True)
    card = dict(batchTitle="The Old Telling EP1 e05", aspect=ASPECT,
                card=dict(originalIndex=1, title="E05 THE KING SPEAKS", prompt=TEXT, include=True, linkAbove=False, seconds=SECONDS, quality=QUALITY,
                          rating="safe", ratedSha256=hashlib.sha256(TEXT.encode("utf-8")).hexdigest(), audios=["king_line_4s.mp3"]))
    (HERE / "shots" / "cards-e05.json").write_text(json.dumps([card], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"e05: {len(TEXT.split())} words, refs {REFS}, audio {AUDIO.stat().st_size} bytes, seconds {SECONDS}")
    if not a.fire:
        return
    code, st = h.api("/api/settings")
    cur = st.get("h3Model", "stock")
    if cur != a.model:
        sys.exit(f"STOP: studio h3Model is {cur!r}, --model says {a.model!r}. The CEO owns that setting; nothing queued.")
    created = {r["atId"]: r for r in json.loads((HERE / "h3-entities-created.json").read_text(encoding="utf-8")) if r.get("id")}
    miss = [k for k in REFS if k not in created]
    if miss:
        sys.exit(f"no entity of ours for {miss}")
    up = h.upload(AUDIO, "audio/mpeg")
    h.record("h3-audio-king.json", [{"source": AUDIO.name, "md5": h.md5(AUDIO), "upload": up}], replace=True)
    c = dict(card["card"]); c["audios"] = [up]
    body = {"batchTitle": card["batchTitle"], "aspect": ASPECT, "cards": [c]}
    code, res = h.api("/api/scenes/enqueue", body)
    if code != 200:
        sys.exit(f"enqueue answered HTTP {code}: {str(res)[:200]}")
    ids = [i.get("id") for i in (res.get("queued") or []) if isinstance(i, dict)]  # `items` is everybody's queue: never printed
    print(f"e05: queued {len(ids)} ids {ids} · routes {res.get('routes')} · routeCostUsd {res.get('routeCostUsd')} · warnings {len(res.get('warnings') or [])}")
    q = h.api("/api/queue")[1]
    q = q if isinstance(q, list) else q.get("items", q.get("queue", []))
    for it in q:
        if it.get("id") in ids:
            print(f"e05: item {it['id']} status {it.get('status')} savedRefs {len(it.get('savedRefs') or [])} quality {it.get('quality')} seconds {it.get('seconds')} frames {it.get('frames')} h3Model {it.get('h3Model')}")
    h.record("h3-fired.json", [{"clip": "e05", "ids": ids, "routes": res.get("routes"), "routeCostUsd": res.get("routeCostUsd"), "h3Model": cur}])


main()
