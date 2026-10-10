#!/usr/bin/env python3
"""The Old Telling EP1 ACT 4 to 6 (Thai): picture of the H3 shots (clipsN/<key>.mp4) + Thai narration (Daniel) + voice-only character lines. No paid call.

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act456_edit.py --act 4 [--dry] [--est]
    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act456_edit.py --join        # ACT 1-3 master + ACT 4, 5, 6 masters -> EP1 full cut (concat, no re-encode)

Same method as build_act3_edit.py. Picture is the master, hard cuts. Each shot carries the narration sentences it was planned for (act*_shots.py `line`, split into
sub-sentences by SUBS where one sentence spans two or three shots), the first sentence LEAD seconds after the cut, the rest at their natural gaps. No time-stretch (CEO 2026-10-09):
a sentence longer than its shot makes the shot hold its last frame for at most HOLD_MAX seconds, a shorter one leaves air; a shot longer than its sentence is cut at DUR
when the action is finished. Character lines (Eurydice, the Thracian woman, the head) have no lips on screen (voice only, CEO 2026-10-10): they are laid after the
narration sentence that introduces them, token "@name" at the end of a group. No picture text in ACT 4 to 6 (BRAND.md: text that carries story meaning is spoken).
--est: no purchased voice yet, estimate timings from reading speed (about 10.15 characters per second + 0.35 s per sentence); prints the plan only, never renders.
"""
import argparse, difflib, json, math, pathlib, subprocess, sys
import numpy as np

S = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
OUT = S / "edit7"; OUT.mkdir(exist_ok=True)
V = S / "voice456"
FPS, LEAD, TAIL, HOLD_MAX = 24, 0.35, 0.15, 1.0
CPS, GAP = 10.15, 0.35
CROP = "crop=1840:1035:40:26,scale=1920:1080:flags=lanczos"  # new H3 clips carry black rounded corners
CROP_S09 = "crop=1680:945:200:26,scale=1920:1080:flags=lanczos"  # ACT 4 s09: two small skulls bottom-left; drop left 200 px and the bottom


def clip(n, key):
    return S / f"clips{n}" / f"{key}.mp4"


# sentence -> sub-sentences (each a substring of the sentence text in voice-th/make_voice_act456.py) where one sentence spans two or three shots
SUBS = {
    "4.03a": "เวอร์จิลเขียนว่า ความบ้าอย่างหนึ่งจู่ ๆ ก็ครอบงำเขา.", "4.03b": "เป็นความผิดที่น่าให้อภัย ถ้ายมโลกรู้จักให้อภัย.",
    "4.04a": "เขาหยุด. เขาหันกลับ.", "4.04b": "เขามองยูริไดซี ผู้เป็นของเขาอีกครั้ง.",
    "4.12a": "เขาเล่าเรื่องของตนในถ้ำเย็น เสียงนั้นทำให้เสือใจอ่อน", "4.12b": "และพาต้นโอ๊กเดินตามมา.",
    "5.04a": "วันหนึ่ง หญิงชาวเทรซกลุ่มหนึ่ง", "5.04b": "นุ่งห่มหนังสัตว์ เห็นเขาจากยอดเนิน กำลังดีดพิณ.",
    "5.08a": "แต่ความบ้าของพวกนางยิ่งแรงขึ้น. ปี่ กลอง ฉาบ และเสียงกรีดร้อง", "5.08b": "กลบเสียงพิณและเสียงร้องของเขาจนหมด.",
    "5.09a": "เมื่อหินไม่ได้ยินเพลงอีก มันก็ตกลงมา", "5.09b": "เปื้อนเลือดของกวีแห่งเทรซ.",
    "5.16a": "กระแสพาไปถึงเมืองเมทิมนา บนเกาะเลสบอส.", "5.16b": "งูตัวหนึ่งพุ่งเข้าใส่. อะพอลโลทำให้ขากรรไกรของมันแข็งเป็นหิน.",
    "6.02a": "เงาของออร์เฟียสลงไปใต้ดิน ผ่านแดนที่เขาเคยเห็น.", "6.02b": "เขาตามหายูริไดซีในทุ่งของผู้มีสุข และพบเธอ.",
    "6.03a": "เขากอดเธอ. ทั้งสองเดินเคียงกัน.", "6.03b": "บางครั้งเขาเดินนำ และหันกลับมามองเธอได้ อย่างปลอดภัย.",
    "6.07a": "เหตุผลคือ เขาไม่มีใจกล้า. เขาไม่กล้าตายเพื่อความรัก", "6.07b": "เหมือนอัลเคสติส ที่ยอมตายแทนสามี.",
    "6.11a": "เวอร์จิลให้เขาเสียเธอไปเพราะความรัก.", "6.11b": "โอวิดให้เขาได้เธอคืน.", "6.11c": "เพลโตให้เขาไม่ได้อะไรเลย.",
}
# character line tokens: file stem prefix in voice456/
LINES = {"@eurydice": "act4_406_eurydice", "@thrace": "act5_505_thrace_woman", "@head": "act5_514_head_liam"}


def g(key, f, in_s, dur, sids, lead=LEAD, crop=CROP):
    return dict(key=key, file=f, in_s=in_s, dur=dur, sids=sids, lead=lead, crop=crop)


GROUPS = {
    4: [
        g("s01", clip(4, "s01"), 0.0, None, ["4.01"]),
        g("s02", clip(4, "s02"), 0.0, None, ["4.02"]),
        g("s03a", clip(4, "s03a"), 0.0, None, ["4.03a"]),
        g("s03b", clip(4, "s03b"), 0.0, None, ["4.03b"]),
        g("s04a", clip(4, "s04a"), 0.0, None, ["4.04a"], lead=1.4),   # he turns his head back at about 3 s
        g("s04b", clip(4, "s04b"), 0.0, None, ["4.04b"]),
        g("s05", clip(4, "s05"), 0.0, None, ["4.05"]),
        g("s06", clip(4, "s06"), 0.0, None, ["4.06", "@eurydice"]),
        g("s07", clip(4, "s07"), 0.0, None, ["4.07"]),
        g("s08", clip(4, "s08"), 0.0, None, ["4.08"]),
        g("s09", clip(4, "s09"), 0.0, None, ["4.09"], crop=CROP_S09),
        g("s10", clip(4, "s10"), 0.0, None, ["4.10"]),
        g("s11", clip(4, "s11"), 0.0, None, ["4.11"]),
        g("s12a", clip(4, "s12a"), 0.0, None, ["4.12a"]),
        g("s12b", clip(4, "s12b"), 0.0, None, ["4.12b"]),
        g("s13", clip(4, "s13"), 0.0, None, ["4.13"]),
    ],
    5: [
        g("s01", clip(5, "s01"), 0.0, None, ["5.01"]),
        g("s02", clip(5, "s02"), 0.0, None, ["5.02"]),
        g("s03", clip(5, "s03"), 0.0, None, ["5.03"]),
        g("s04a", clip(5, "s04a"), 0.0, None, ["5.04a"]),
        g("s04b", clip(5, "s04b"), 0.0, None, ["5.04b"]),
        g("s05", clip(5, "s05"), 0.0, None, ["5.05", "@thrace"]),
        g("s06", clip(5, "s06"), 0.0, None, ["5.06"]),
        g("s07", clip(5, "s07"), 0.0, None, ["5.07"]),
        g("s08a", clip(5, "s08a"), 0.0, None, ["5.08a"]),
        g("s08b", clip(5, "s08b"), 0.0, None, ["5.08b"]),
        g("s09a", clip(5, "s09a"), 0.0, None, ["5.09a"]),
        g("s09b", clip(5, "s09b"), 0.0, None, ["5.09b"]),
        g("s10", clip(5, "s10"), 0.0, None, ["5.10"]),
        g("s11", clip(5, "s11"), 0.0, None, ["5.11"]),
        g("s12", clip(5, "s12"), 0.0, 12.5, ["5.12", "5.13", "@head"]),
        g("s14", clip(5, "s14"), 0.0, None, ["5.15"]),
        g("s15a", clip(5, "s15a"), 0.0, None, ["5.16a"]),
        g("s15b", clip(5, "s15b"), 0.0, None, ["5.16b"], lead=0.2),
        g("s16", clip(5, "s16"), 0.0, None, ["5.17"]),
    ],
    6: [
        g("s01", clip(6, "s01"), 0.0, None, ["6.01"]),
        g("s02a", clip(6, "s02a"), 0.0, None, ["6.02a"]),
        g("s02b", clip(6, "s02b"), 0.0, None, ["6.02b"]),
        g("s03a", clip(6, "s03a"), 1.2, None, ["6.03a"]),   # her face is faintly visible in profile before about 1 s; the embrace hides it
        g("s03b", clip(6, "s03b"), 0.0, None, ["6.03b", "6.04"]),
        g("s05", clip(6, "s05"), 0.0, None, ["6.05"]),
        g("s06a", clip(6, "s06a"), 0.0, None, ["6.06"]),
        g("s07b", clip(6, "s07b"), 0.0, None, ["6.07a"]),
        g("s07a", clip(6, "s07a"), 0.0, None, ["6.07b"]),
        g("s08", clip(6, "s08"), 0.0, None, ["6.08"]),
        g("s09", clip(6, "s09"), 0.0, None, ["6.09"]),
        g("s10", clip(6, "s10"), 0.0, None, ["6.10"]),
        g("v11a", clip(4, "s07"), 0.5, 4.2, ["6.11a"]),     # reuse: Virgil lost her (smoke) from ACT 4
        g("v11b", clip(6, "s03b"), 0.0, 2.8, ["6.11b"]),    # reuse: Ovid got her back (walking together)
        g("v11c", clip(6, "s06b"), 0.0, 3.2, ["6.11c"]),    # Plato: the empty hand
        g("s11", clip(6, "s11"), 0.0, None, ["6.12"]),
        g("s12a", clip(6, "s12a"), 0.0, None, ["6.13"]),
        g("s12b", clip(6, "s12b"), 0.0, None, ["6.14"]),
    ],
}


def probe(p, what="format=duration"):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", what, "-of", "csv=p=0", str(p)]).split()[0])


def nframes(p):
    return int(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(p)]).split()[0])


def voice_span(path, rel=0.03, pad=0.04):
    """first and last moment of a spoken line (envelope above rel x peak), so silence around it never shifts the lay."""
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout, dtype=np.int16).astype(np.float32) / 32768
    hop = 0.01; n = int(16000 * hop); k = len(x) // n
    e = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1)); act = np.nonzero(e > rel * e.max())[0]
    return max(0.0, act[0] * hop - pad), min(len(x) / 16000, (act[-1] + 1) * hop + pad)


def timings(act, est):
    sents = json.loads((V / "sentences-act456.json").read_text(encoding="utf-8"))[f"act{act}"]
    full = " ".join(t for _, t in sents)
    tsf = V / f"act{act}_teller_daniel.timestamps.json"
    if est or not tsf.exists():
        if not est:
            sys.exit(f"no {tsf.name}: the voice is not bought yet; use --est for a plan from reading speed")
        st, en, brk = [], [], 0
        for i, ch in enumerate(full):
            st.append(i / CPS + brk * GAP); en.append((i + 1) / CPS + brk * GAP)
            if ch in ".?!" and i + 1 < len(full) and full[i + 1] == " ":
                brk += 1
        idx = list(range(len(full)))
    else:
        ts = json.loads(tsf.read_text(encoding="utf-8"))
        ch, st, en = [], [], []
        for c in ts:
            ch += c["characters"]; st += c["character_start_times_seconds"]; en += c["character_end_times_seconds"]
        joined = "".join(ch)
        if joined == full:
            idx = list(range(len(full)))
        else:
            idx = [None] * len(full)
            for a, b, size in difflib.SequenceMatcher(None, full, joined, autojunk=False).get_matching_blocks():
                for d in range(size):
                    idx[a + d] = b + d
            prev = 0
            for i in range(len(idx)):
                if idx[i] is None:
                    idx[i] = prev
                prev = idx[i]
    TH, pos = {}, 0
    for sid, text in sents:
        a = full.find(text, pos); assert a >= 0, sid
        TH[sid] = dict(start=round(st[idx[a]], 3), end=round(en[idx[a + len(text) - 1]], 3), text=text)
        for sub_id, sub in SUBS.items():
            if sub_id[:-1] == sid and sub_id[-1].isalpha():
                b = full.find(sub, a); assert b >= 0 and b + len(sub) <= a + len(text), (sub_id, "not inside", sid)
                TH[sub_id] = dict(start=round(st[idx[b]], 3), end=round(en[idx[b + len(sub) - 1]], 3), text=sub)
        pos = a + len(text)
    return TH


def line_file(token):
    hits = sorted(V.glob(LINES[token] + "*.mp3"))
    return hits[0] if hits else None


def plan(act, est):
    TH = timings(act, est)
    segs, place, notes, t = [], {}, [], 0.0
    lines = []
    for grp in GROUPS[act]:
        f = grp["file"]
        if not f.exists():
            sys.exit(f"{grp['key']}: {f} is not rendered yet")
        n_full = nframes(f); a = int(round(grp["in_s"] * FPS)); n = int(round(grp["dur"] * FPS)) if grp["dur"] else n_full - a
        assert a + n <= n_full, (grp["key"], "asks past the end of the clip", a + n, n_full)
        seg = dict(key=grp["key"], file=str(f), a=a, n=n, hold=0.0, start=round(t, 3), crop=grp["crop"])
        seg_end = t + n / FPS
        at = t + grp["lead"]; prev = None; last_end = 0.0
        for k_sid, sid in enumerate(grp["sids"]):
            if sid.startswith("@"):
                lf = line_file(sid)
                if lf is None and not est:
                    sys.exit(f"{sid}: no {LINES[sid]}*.mp3 in {V}")
                span = voice_span(lf) if lf else (0.0, 4.0)
                at_l = last_end + 0.30
                lines.append(dict(token=sid, file=str(lf) if lf else None, a0=round(span[0], 3), a1=round(span[1], 3), at=round(at_l, 3)))
                last_end = at_l + span[1] - span[0]; prev = None; at = last_end + 0.40
                continue
            if prev is not None:
                at = place[prev] + (TH[sid]["start"] - TH[prev]["start"])
            if k_sid:
                at = max(at, last_end + 0.30)
            place[sid] = round(at, 3); last_end = at + TH[sid]["end"] - TH[sid]["start"]; prev = sid
        need = last_end + TAIL - seg_end
        if need > 0:
            seg["hold"] = min(HOLD_MAX, math.ceil(need * FPS) / FPS)
            if need > HOLD_MAX:
                notes.append(f"{grp['key']}: narration runs {need - HOLD_MAX:.2f} s past the shot even after a {HOLD_MAX} s hold")
        air = seg_end + seg["hold"] - last_end
        if air > 3.0:
            notes.append(f"{grp['key']}: {air:.1f} s of air after the last sentence (consider a shorter dur)")
        segs.append(seg); t = seg_end + seg["hold"]
    order = sorted(place, key=lambda x: place[x])
    for a_, b_ in zip(order, order[1:]):
        end = place[a_] + TH[a_]["end"] - TH[a_]["start"]
        if end > place[b_] + 0.001:
            notes.append(f"narration overlap {a_} ends {end:.2f}, {b_} starts {place[b_]:.2f}")
    return dict(act=act, total=round(t, 3), segments=segs, narration_at=place, lines=lines, notes=notes, est=bool(est)), TH


def render(P, TH, act):
    segs, place, lines, total = P["segments"], P["narration_at"], P["lines"], P["total"]
    files = []
    for s in segs:
        if s["file"] not in files:
            files.append(s["file"])
    narr = V / f"act{act}_teller_daniel.mp3"
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in files:
        cmd += ["-i", f]
    i_narr = len(files); cmd += ["-i", str(narr)]
    extra = {}
    for ln in lines:
        extra[ln["token"]] = len(files) + 1 + len(extra); cmd += ["-i", ln["file"]]
    fc, vl, al = [], [], []
    for k, s in enumerate(segs):
        i = files.index(s["file"]); a0, dur = s["a"] / FPS, s["n"] / FPS + s["hold"]
        v = f"[{i}:v]trim=start_frame={s['a']}:end_frame={s['a'] + s['n']},setpts=PTS-STARTPTS,{s['crop']},setsar=1,fps=24,format=yuv420p"
        if s["hold"]:
            v += f",tpad=stop_mode=clone:stop_duration={s['hold']:.4f}"
        fc.append(v + f"[v{k}]"); vl.append(f"[v{k}]")
        au = f"[{i}:a]atrim=start={a0:.4f}:end={a0 + s['n'] / FPS:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo"
        fc.append(au + f",apad=whole_dur={dur:.4f},atrim=end={dur:.4f}[a{k}]"); al.append(f"[a{k}]")
    fc.append("".join(vl) + f"concat=n={len(vl)}:v=1:a=0[base]")
    fc.append(f"[base]fade=t=in:st=0:d=0.4,fade=t=out:st={total - 1.0:.3f}:d=1.0,format=yuv420p[vout]")
    fc.append("".join(al) + f"concat=n={len(al)}:v=0:a=1,volume=4dB[ambient]")
    parts = []
    for sid in sorted(place, key=lambda x: place[x]):
        r = TH[sid]; a0, a1 = max(0.0, r["start"] - 0.03), r["end"] + 0.10; ms = int(round((place[sid] - 0.03) * 1000))
        lab = "n" + sid.replace(".", "_")
        fc.append(f"[{i_narr}:a]atrim=start={a0:.3f}:end={a1:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[{lab}]")
        parts.append(f"[{lab}]")
    for k, ln in enumerate(lines):
        ms = int(round(ln["at"] * 1000))
        fc.append(f"[{extra[ln['token']]}:a]atrim=start={ln['a0']:.3f}:end={ln['a1']:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.02,adelay={ms}|{ms}[ln{k}]")
        parts.append(f"[ln{k}]")
    fc.append("".join(parts) + f"amix=inputs={len(parts)}:normalize=0:duration=longest,apad=whole_dur={total:.3f}[bus]")
    fc.append("[bus]asplit=2[bus_sc][bus_mix]")
    fc.append("[ambient][bus_sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=450:makeup=1[duck]")
    fc.append(f"[duck][bus_mix]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st={total - 1.0:.3f}:d=1.0[aout]")
    master = OUT / f"ACT{act}_th_1080p.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(master)]
    (OUT / f"ffmpeg_cmd_act{act}.txt").write_text(" ".join(cmd), encoding="utf-8")
    subprocess.run(cmd, check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vf", "scale=960:540:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(OUT / f"ACT{act}_th_540p.mp4")], check=True)
    print("done", master.name, "total", round(total, 3))


def join():
    parts = [S / "edit6" / "ACT1-3_th_1080p.mp4"] + [OUT / f"ACT{n}_th_1080p.mp4" for n in (4, 5, 6)]
    for p in parts:
        assert p.exists(), p
    lst = OUT / "join_1080p.txt"; lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    full = OUT / "EP1_th_full_1080p.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(full)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-vf", "scale=960:540:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(OUT / "EP1_th_full_540p.mp4")], check=True)
    print("joined", full.name, round(probe(full), 2), "s;", " + ".join(f"{p.name} {probe(p):.2f}" for p in parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", type=int, choices=[4, 5, 6]); ap.add_argument("--dry", action="store_true"); ap.add_argument("--est", action="store_true"); ap.add_argument("--join", action="store_true")
    a = ap.parse_args()
    if a.join:
        return join()
    if not a.act:
        sys.exit("--act 4|5|6 or --join")
    P, TH = plan(a.act, a.est)
    (OUT / f"placement-act{a.act}{'-est' if a.est else ''}.json").write_text(json.dumps(P, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: P[k] for k in ("total", "lines", "notes")}, indent=1, ensure_ascii=False))
    print("narration_at", json.dumps(P["narration_at"], ensure_ascii=False))
    if a.dry or a.est:
        return
    render(P, TH, act=a.act)


main()
