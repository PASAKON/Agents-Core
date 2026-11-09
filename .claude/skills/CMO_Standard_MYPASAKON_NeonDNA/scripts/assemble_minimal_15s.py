import subprocess
from pathlib import Path

KIT_DIR = Path("/Users/gob/.gemini/antigravity/brain/5e00df47-82c6-4268-a12f-3377d70c2d23/scratch/mypasakon_neon_kit")
SCRATCH = Path("/Users/gob/.gemini/antigravity/brain/5e00df47-82c6-4268-a12f-3377d70c2d23/scratch")
ART_DIR = Path("/Users/gob/.gemini/antigravity/brain/5e00df47-82c6-4268-a12f-3377d70c2d23")
SP = KIT_DIR / "sprites_minimal"
FLOW_DIR = KIT_DIR / "flow_inputs"

AROLL = KIT_DIR / "assets" / "aroll_16s.mp4"
AUDIO = KIT_DIR / "assets" / "audio_15s.m4a"
CAP1 = SCRATCH / "capture1.mp4"
CAP3 = SCRATCH / "capture3.mp4"
FLOW_QUANT = FLOW_DIR / "flow_claude_quant.mp4"

OUT_VIDEO = KIT_DIR / "mypasakon-minimal-flow12-15s.mp4"
ART_VIDEO = ART_DIR / "mypasakon-minimal-flow12-15s.mp4"
ART_SHEET = ART_DIR / "mypasakon-minimal-flow12-sheet.png"

# Build filter_complex for 4 clean beats (30fps, 1080x1920, 15.0s)
fc = """
color=c=#040A07:s=1080x1920:r=30:d=15.0[bg_base];

[0:v]fps=30,scale=1080:1920,eq=contrast=1.12:brightness=-0.04:saturation=0.92,
curves=g='0/0 0.5/0.54 1/0.98':b='0/0 0.5/0.46 1/0.88'[aroll_full];

[aroll_full]split=4[ar_b1][ar_b2][ar_b3][ar_b4];

[ar_b1]null[b1_aroll];
[1:v]fps=30,crop=716:396:266:28,scale=912:480,
eq=contrast=1.22:saturation=1.25[b1_chart];
[b1_aroll][b1_chart]overlay=84:120[b1_comp0];
[b1_comp0][4:v]overlay=0:0[b1_comp1];
[b1_comp1][5:v]overlay=0:0:enable='between(t,0,1.85)'[b1_comp2];
[b1_comp2][6:v]overlay=0:0:enable='between(t,1.85,3.70)'[beat1];

[ar_b2]crop=1080:920:0:620,pad=1080:1920:0:0:#040A07[b2_aroll];
[2:v]fps=30,scale=936:1664,crop=936:800:0:380[b2_flow];
[b2_aroll][b2_flow]overlay=72:920[b2_comp0];
[b2_comp0][7:v]overlay=0:0[b2_comp1];
[b2_comp1][8:v]overlay=0:0:enable='between(t,3.70,5.58)'[b2_comp2];
[b2_comp2][9:v]overlay=0:0:enable='between(t,5.58,7.56)'[beat2];

[ar_b3]crop=960:960:95:570,scale=380:380,format=yuva420p,
geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':
a='if(lte((X-190)*(X-190)+(Y-190)*(Y-190),186*186),255,0)'[b3_avatar];
[bg_base][b3_avatar]overlay=350:90[b3_comp0];
[b3_comp0][10:v]overlay=0:0:enable='between(t,7.56,8.60)'[b3_comp1];
[b3_comp1][11:v]overlay=0:0:enable='between(t,8.60,9.65)'[b3_comp2];
[b3_comp2][12:v]overlay=0:0:enable='between(t,9.65,10.70)'[b3_comp3];
[b3_comp3][13:v]overlay=0:0:enable='between(t,10.70,11.93)'[beat3];

[ar_b4]crop=1080:940:0:640,pad=1080:1920:0:980:#040A07[b4_aroll];
[3:v]fps=30,crop=880:335:355:42,scale=840:320,eq=saturation=0.35:brightness=-0.12:contrast=1.1[b4_top];
[2:v]fps=30,scale=840:1493,crop=840:480:0:380[b4_hero];
[b4_aroll][b4_top]overlay=120:120[b4_c0];
[b4_c0][b4_hero]overlay=120:500[b4_c1];
[b4_c1][14:v]overlay=0:0[b4_c2];
[b4_c2][15:v]overlay=0:0:enable='between(t,11.93,13.50)'[b4_c3];
[b4_c3][16:v]overlay=0:0:enable='between(t,13.50,15.00)'[beat4];

[beat1]trim=0:3.70,setpts=PTS-STARTPTS[v1];
[beat2]trim=3.70:7.56,setpts=PTS-STARTPTS[v2];
[beat3]trim=7.56:11.93,setpts=PTS-STARTPTS[v3];
[beat4]trim=11.93:15.00,setpts=PTS-STARTPTS[v4];
[v1][v2][v3][v4]concat=n=4:v=1:a=0[vout]
""".replace("-LOOP_FLOW-", "")

cmd = [
    "ffmpeg", "-y",
    "-i", str(AROLL),                     # 0
    "-stream_loop", "-1", "-i", str(CAP3), # 1
    "-stream_loop", "-1", "-i", str(FLOW_QUANT), # 2
    "-stream_loop", "-1", "-i", str(CAP1), # 3
    "-i", str(SP / "beat1_frame.png"),     # 4
    "-i", str(SP / "sub_01.png"),          # 5
    "-i", str(SP / "sub_02.png"),          # 6
    "-i", str(SP / "beat2_frame.png"),     # 7
    "-i", str(SP / "sub_03.png"),          # 8
    "-i", str(SP / "sub_04.png"),          # 9
    "-i", str(SP / "beat3_step0.png"),     # 10
    "-i", str(SP / "beat3_step1.png"),     # 11
    "-i", str(SP / "beat3_step2.png"),     # 12
    "-i", str(SP / "beat3_step3.png"),     # 13
    "-i", str(SP / "beat4_frame.png"),     # 14
    "-i", str(SP / "sub_09.png"),          # 15
    "-i", str(SP / "sub_10.png"),          # 16
    "-i", str(AUDIO),                      # 17
    "-filter_complex", fc,
    "-map", "[vout]", "-map", "17:a",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-t", "15.0",
    str(OUT_VIDEO)
]

print("Running FFmpeg assembly...")
subprocess.run(cmd, check=True)
subprocess.run(["cp", str(OUT_VIDEO), str(ART_VIDEO)], check=True)

# Extract 6-frame verification contact sheet at key moments: 1.0s(30), 3.0s(90), 4.6s(138), 6.5s(195), 11.2s(336), 14.2s(426)
sheet_cmd = [
    "ffmpeg", "-y", "-i", str(OUT_VIDEO),
    "-vf", "select='eq(n\\,30)+eq(n\\,90)+eq(n\\,138)+eq(n\\,195)+eq(n\\,336)+eq(n\\,426)',scale=360:640,tile=3x2:padding=12:margin=12:color=#040A07",
    "-frames:v", "1", "-update", "1", str(ART_SHEET)
]
subprocess.run(sheet_cmd, check=True)
print("Saved video & sheet:", ART_VIDEO, ART_SHEET)
