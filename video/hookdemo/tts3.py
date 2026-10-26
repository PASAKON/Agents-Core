import asyncio, json, subprocess, sys, edge_tts
from pathlib import Path
H = Path(sys.argv[1]); rate = sys.argv[2]; voice = "th-TH-NiwatNeural"
P = json.loads((H / "work/phrases.json").read_text(encoding="utf-8"))
trim = "silenceremove=start_periods=1:start_threshold=-50dB"
res = []
async def main():
    for i, ph in enumerate(P, 1):
        row = []
        for j, t in enumerate(ph, 1):
            mp3 = H / f"work/vo/{i}{j}.mp3"; wav = H / f"work/vo/{i}{j}.wav"
            await edge_tts.Communicate(t, voice, rate=rate).save(str(mp3))
            subprocess.run(["ffmpeg","-v","error","-y","-i",str(mp3),"-af",f"{trim},areverse,{trim},areverse","-ar","48000","-ac","1",str(wav)],check=True)
            d = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(wav)],capture_output=True,text=True).stdout)
            row.append(round(d, 3))
        res.append(row); print(i, row, round(sum(row), 2))
asyncio.run(main())
(H/"work/vo/durs.json").write_text(json.dumps(res))
