#!/usr/bin/env python3
"""Assemble the MYPASAKON EP1 v2 fast-cut capture-first preview.

Real program recordings are passed with --capture-dir.  The zero-argument
fallback is conspicuously marked STAND-IN and exists only for local editorial
review.  The source voice is never edited or regenerated.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

WORK = Path("/opt/MoonieXHQ/Work/mypasakon-voice")
DURATION = 102.7
FPS = 30
SIZE = "1080x1920"

# This is the EP1 caption content from the original assembler, deliberately
# split to 2–4 Thai word display units.  *word* is the highlighted key word.
CAPTIONS = [
    (0.0, 7.5, "*AI* ที่ผมใช้"), (0.0, 7.5, "เทรดจริง มาแปดเดือน"),
    (0.0, 7.5, "คือ *Claude Code*"), (0.0, 7.5, "นะครับ เพื่อนๆ"),
    (7.5, 15.0, "ลองมา หมดแล้ว"), (7.5, 15.0, "แต่ตัวนี้ *ถูกใจที่สุด*"),
    (7.5, 15.0, "นะครับ เพื่อนๆ"),
    (15.0, 22.5, "ผู้ช่วย วิเคราะห์การเทรด"), (15.0, 22.5, "ทำสถิติ และคำนวณ"),
    (15.0, 22.5, "คำนวณ *ความเสี่ยง*"),
    (22.5, 32.0, "สั่งให้ ทดสอบ"), (22.5, 32.0, "ข้อมูลเก่า ย้อนหลัง"),
    (22.5, 32.0, "ได้ หมดเลย"),
    (32.0, 40.0, "ที่ชอบ ที่สุดคือ"), (32.0, 40.0, "มัน *ไม่หลับไม่นอน*"),
    (32.0, 40.0, "นะครับ เพื่อนๆ"),
    (40.0, 47.5, "ก่อนนอน ผมสั่งให้"), (40.0, 47.5, "วิจัย กลยุทธ์"),
    (40.0, 47.5, "ย้อนหลัง *ห้าปี*"),
    (47.5, 55.0, "แล้วผม ก็ไปนอน"), (47.5, 55.0, "รอผล ตอนเช้า"), (47.5, 55.0, "นะครับ เพื่อนๆ"),
    (55.0, 62.5, "ตื่นมา เจอกราฟ"), (55.0, 62.5, "ย้อนหลัง ที่มัน"),
    (55.0, 62.5, "ไล่ดู ให้ทั้งคืน"),
    (62.5, 72.5, "ทดสอบเป็น *หมื่นๆ รอบ*"), (62.5, 72.5, "แล้วสรุป เป็นตาราง"),
    (62.5, 72.5, "ให้ แล้ว"),
    (72.5, 85.0, "บอก ได้ว่า"), (72.5, 85.0, "กลยุทธ์ไหน *อยู่รอด*"),
    (72.5, 85.0, "และ พังตอนไหน"),
    (85.0, 92.5, "งานที่ทำ คนเดียว"), (85.0, 92.5, "เป็น เดือน"),
    (85.0, 92.5, "เสร็จได้ใน *คืนเดียว*"),
    (92.5, 100.0, "ต่อจากนี้ ผมจะสอน"), (92.5, 100.0, "ใช้ *AI* เป็นผู้ช่วย"),
    (92.5, 100.0, "ตัวเอง นะครับ"),
    (100.0, 102.7, "คอมเมนต์ คำว่า"), (100.0, 102.7, "*Claude* ไว้ได้เลย"),
    (100.0, 102.7, "นะครับ เพื่อนๆ"),
]
FACE_RANGES = ((0.0, 15.0), (40.0, 55.0), (85.0, 100.0))
BEATS = ("typing", "log burst", "candle build", "table reveal", "zoomed detail")

def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(str(x) for x in cmd))
    return subprocess.run(cmd, check=True, text=True, **kwargs)

def require(command: str) -> str:
    found = shutil.which(command)
    if not found: raise SystemExit(f"{command} is required")
    return found

def free_memory_ok() -> None:
    out = run(["free", "-m"], stdout=subprocess.PIPE).stdout
    row = next((line.split() for line in out.splitlines() if line.startswith("Mem:")), [])
    available = int(row[6]) if len(row) > 6 else 0
    if available < 3000: raise SystemExit(f"Need >= 3 GB available memory; free -m reports {available} MB")

def discover_captures(capture_dir: Path | None, work: Path) -> tuple[list[Path], bool]:
    if capture_dir:
        captures = sorted(p for p in capture_dir.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"})
        standin = False
    else:
        footage = work / "footage"
        captures = [footage / n for n in ("clip1_terminal.mp4", "clip2_log.mp4", "clip3_chart.mp4", "clip4_table.mp4")]
        standin = True
    missing = [str(p) for p in captures if not p.is_file()]
    if not captures or missing: raise SystemExit("Missing screen recordings:\n" + "\n".join("- " + p for p in missing))
    return captures, standin

def silence_boundaries(voice: Path) -> list[float]:
    """Use ffmpeg silencedetect, then use ends of small natural pauses as cuts."""
    p = run(["ffmpeg", "-hide_banner", "-i", str(voice), "-af", "silencedetect=noise=-36dB:d=0.055", "-f", "null", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return [float(v) for v in re.findall(r"silence_end: ([0-9.]+)", p.stderr) if 0 < float(v) < DURATION]

def make_cuts(boundaries: list[float]) -> list[float]:
    """Choose 42 shots (2–3s) nearest a detected phrase pause, never a fixed grid."""
    cuts=[0.0]; target_count=42
    for i in range(1, target_count):
        remaining = target_count - i
        lo, hi = cuts[-1] + 2.0, cuts[-1] + 3.0
        # Reserve a feasible 2–3 second interval for every remaining shot.
        lo=max(lo, DURATION-remaining*3.0); hi=min(hi, DURATION-remaining*2.0)
        candidates=[b for b in boundaries if lo <= b <= hi]
        if not candidates:
            raise SystemExit(f"No silencedetect phrase boundary in {lo:.2f}–{hi:.2f}s for cut {i}; refusing non-phrase cut")
        ideal=cuts[-1]+(DURATION-cuts[-1])/ (remaining+1)
        cuts.append(min(candidates, key=lambda b: abs(b-ideal)))
    cuts.append(DURATION)
    lengths=[b-a for a,b in zip(cuts,cuts[1:])]
    if len(lengths)!=42 or min(lengths)<2.0 or max(lengths)>3.0: raise SystemExit("Unable to form compliant 2–3 second cut list")
    return cuts

def ass_time(seconds: float) -> str:
    h, rem=divmod(seconds,3600); m, s=divmod(rem,60); return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def caption_for(t: float) -> str:
    choices=[row for row in CAPTIONS if row[0] <= t < row[1]]
    row=choices[int((t-(choices[0][0] if choices else 0))*1.7)%len(choices)] if choices else CAPTIONS[-1]
    return row[2]

def ass_markup(text: str) -> str:
    escaped=text.replace("{", r"\{").replace("}", r"\}")
    return re.sub(r"\*([^*]+)\*", r"{\\c&H30D8FF&}\1{\\c&HFFFFFF&}", escaped).replace("*", "")

def write_ass(path: Path, cuts: list[float], offset: float = 0.0) -> None:
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Cap,Noto Sans Thai,64,&H00FFFFFF,&H000000FF,&H00101820,&H00000000,1,0,0,0,100,100,0,0,1,3,2,2,120,140,385,1\n"
        "Style: Hook,Noto Sans Thai,82,&H00FFFFFF,&H000000FF,&H00101820,&H00000000,1,0,0,0,100,100,0,0,1,4,3,8,100,100,170,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    events=[]
    if offset == 0.0:
        events.append(f"Dialogue: 3,0:00:00.00,0:00:01.50,Hook,,0,0,0,,{ass_markup('AI ช่วย *เทรดจริง* ได้ไหม')}\n")
    for a,b in zip(cuts,cuts[1:]):
        events.append(f"Dialogue: 2,{ass_time(a-offset)},{ass_time(b-offset)},Cap,,0,0,0,,{ass_markup(caption_for((a+b)/2))}\n")
    path.write_text(header+"".join(events),encoding="utf-8")

def record_background(html: Path, out: Path, temp: Path) -> None:
    """The same screenshot-per-setTime recording method as record_footage.py."""
    try: from playwright.sync_api import sync_playwright
    except ImportError as e: raise SystemExit("Playwright Python package is required to record the deterministic background") from e
    frames=temp/"background_frames"; frames.mkdir()
    total=math.ceil(DURATION*FPS)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, chromium_sandbox=False, args=["--no-sandbox","--no-zygote","--disable-dev-shm-usage","--disable-gpu"])
        try:
            page=browser.new_page(viewport={"width":1080,"height":1920}, device_scale_factor=1)
            page.goto(html.resolve().as_uri(), wait_until="load")
            for n in range(total):
                page.evaluate("ms => window.__setTime(ms)", n*1000/FPS)
                page.screenshot(path=str(frames/f"frame_{n:05d}.png"), type="png")
        finally: browser.close()
    run(["ffmpeg","-y","-framerate",str(FPS),"-i",str(frames/"frame_%05d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-r",str(FPS),"-movflags","+faststart",str(out)])
    shutil.rmtree(frames, ignore_errors=True)

def is_face_slot(t: float, index: int) -> bool:
    return any(a <= t < b for a,b in FACE_RANGES) and index % 3 == 1

def filter_path(path: Path) -> str:
    """Escape the few characters special to an ffmpeg filter argument."""
    return str(path).replace("\\", r"\\\\").replace(":", r"\\:").replace("'", r"\\'")

def render_shot(bg: Path, capture: Path, standin: bool, start: float, end: float, beat: str, face: bool, ass: Path, out: Path) -> None:
    dur=end-start; common=["ffmpeg","-y","-ss",f"{start:.3f}","-i",str(bg),"-stream_loop","-1","-i",str(capture),"-t",f"{dur:.3f}"]
    if face:
        # Text-card face slot: lipsync is explicitly held; it is intercut, never a 15s block.
        card="color=c=0x11233d:s=860x760:d="+f"{dur:.3f}"
        graph=(f"[0:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS,drawbox=x=92:y=392:w=896:h=816:color=black@0.52:t=fill[base];"
               f"{card},drawtext=font='Noto Sans Thai':text='FACE SLOT\\nLIPSYNC ON HOLD':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=18[card];"
               f"[base][card]overlay=110:410,subtitles='{filter_path(ass)}'[v]")
        maps=["-filter_complex",graph,"-map","[v]"]
    else:
        tag=",drawtext=font='Noto Sans Thai':text='STAND-IN':fontcolor=white:fontsize=26:box=1:boxcolor=0xC23B3B@0.95:boxborderw=12:x=18:y=18" if standin else ""
        zoom="1.26" if start < 1.5 else "1.035"
        graph=(f"[0:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS,drawbox=x=110:y=410:w=900:h=840:color=black@0.62:t=fill[base];"
               f"[1:v]fps={FPS},scale=1150:1050:force_original_aspect_ratio=increase,crop=1150:1050,zoompan=z='min({zoom},zoom+0.00065)':x='iw/2-iw/zoom/2+sin(on/15)*9':y='ih/2-ih/zoom/2+cos(on/19)*7':d=1:s=900x820:fps={FPS},trim=duration={dur:.3f},setpts=PTS-STARTPTS,rotate=0.008:c=none{tag}[screen];"
               f"[base][screen]overlay=x=90:y=400:shortest=1,subtitles='{filter_path(ass)}'[v]")
        maps=["-filter_complex",graph,"-map","[v]"]
    print(f"render shot {start:.3f}–{end:.3f}: {'face slot' if face else beat}")
    run(common+maps+["-an","-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p","-r",str(FPS),str(out)])

def qc(output: Path, work: Path, cuts: list[float]) -> None:
    q=work/"v4"/"qc"; q.mkdir(parents=True,exist_ok=True)
    probe=run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,width,height,r_frame_rate","-of","json",str(output)],stdout=subprocess.PIPE).stdout
    (q/"ffprobe.json").write_text(probe,encoding="utf-8")
    for t in (0.5,15,35,50,70,95): run(["ffmpeg","-y","-ss",str(t),"-i",str(output),"-frames:v","1",str(q/f"still-{t:05.1f}s.png")],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    lengths=[b-a for a,b in zip(cuts,cuts[1:])]
    (q/"cut-summary.json").write_text(json.dumps({"cut_count":len(lengths)-1,"shots":len(lengths),"shortest":min(lengths),"longest":max(lengths),"cuts":cuts},indent=2),encoding="utf-8")
    print(probe); print(f"cuts={len(lengths)-1}; shots={len(lengths)}; shortest={min(lengths):.3f}; longest={max(lengths):.3f}")

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir",type=Path,default=WORK)
    ap.add_argument("--capture-dir",type=Path,help="Folder of real program screen recordings; disables STAND-IN tag.")
    ap.add_argument("--output",type=Path,help="Defaults to WORK_DIR/v4/mypasakon-ep1-v2-preview.mp4")
    args=ap.parse_args(); work=args.work_dir.resolve(); output=args.output or work/"v4"/"mypasakon-ep1-v2-preview.mp4"
    require("ffmpeg"); require("ffprobe"); free_memory_ok()
    voice=work/"v3"/"mypasakon-v3-voice-tight.mp3"
    if not voice.is_file(): raise SystemExit(f"Missing approved voice: {voice}")
    captures,standin=discover_captures(args.capture_dir.resolve() if args.capture_dir else None,work)
    cuts=make_cuts(silence_boundaries(voice)); output.parent.mkdir(parents=True,exist_ok=True)
    html=Path(__file__).with_name("ep1_v2_background.html")
    with tempfile.TemporaryDirectory(prefix="mypasakon-ep1-v2-") as raw:
        temp=Path(raw); bg=temp/"background.mp4"; record_background(html,bg,temp)
        shots=[]
        for i,(a,b) in enumerate(zip(cuts,cuts[1:])):
            shot=temp/f"shot-{i:02d}.mp4"; face=is_face_slot((a+b)/2,i)
            shot_ass=temp/f"captions-{i:02d}.ass"
            write_ass(shot_ass,[a,b],offset=a)
            render_shot(bg,captures[i % len(captures)],standin,a,b,BEATS[i % len(BEATS)],face,shot_ass,shot)
            shots.append(shot)
        listing=temp/"shots.txt"; listing.write_text("".join(f"file '{p}'\n" for p in shots),encoding="utf-8")
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-i",str(voice),"-map","0:v:0","-map","1:a:0","-t",str(DURATION),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-r",str(FPS),"-c:a","aac","-b:a","192k","-movflags","+faststart",str(output)])
    qc(output,work,cuts); print(f"Wrote {output}"); return 0

if __name__ == "__main__": raise SystemExit(main())
