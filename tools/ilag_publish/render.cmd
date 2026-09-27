@echo off
rem THE SHADOW BELOW finish on winbox (CTO cto-e1e3d3ef, 2026-09-27): Glow LUT -> Sorry-Sir-style subs -> TopView mark
rem top-right over the whole film incl. credits -> credits appended. %1 = test | master | topview | master2 | topview2
cd /d C:\mooniex\ilag-final
set G=[0:v]lut3d=file=TSB_Glow.cube:interp=trilinear,ass=TSB.en.ass,format=yuv420p[g];[2:v]scale=653:-1,split[wm1][wm2];[1:v]fps=30,format=yuv420p[c];[g][wm1]overlay=W-w-96:96:shortest=1[gw];[c][wm2]overlay=W-w-96:96:shortest=1[cw];[3:a]aresample=48000[a0];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];[gw][a0][cw][a1]concat=n=2:v=1:a=1[v][a]
if "%1"=="test" (
  ffmpeg -v error -y -t 28 -i 0926.mov -t 3 -i ILAG-Credits-4K.mp4 -loop 1 -i TopView-Watermark.png -t 28 -i 0926.WAV -filter_complex "%G%" -map [v] -map [a] -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k -movflags +faststart test.mp4
)
if "%1"=="master" (
  ffmpeg -v error -y -i 0926.mov -i ILAG-Credits-4K.mp4 -loop 1 -i TopView-Watermark.png -i 0926.WAV -filter_complex "%G%" -map [v] -map [a] -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart THE-SHADOW-BELOW-4K-master.mp4
)
if "%1"=="topview" (
  ffmpeg -v error -y -i THE-SHADOW-BELOW-4K-master.mp4 -c:v libx264 -preset medium -b:v 11500k -maxrate 13500k -bufsize 23000k -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart THE-SHADOW-BELOW-4K-topview.mp4
)
rem v2 (CEO 2026-09-27 evening): the CEO's CapCut cut already ENDS WITH ITS OWN CREDITS ROLL + music (229-271 s, the fade
rem reaches digital silence on its last frame, 275.800 s), so v1 showed the credits twice, the appended one silent. v2 is
rem the cut alone: same grade/subs/mark, nothing appended, frame-exact (8274 frames). A stream-copy trim of v1 cannot land
rem on that frame (B-frame reorder keeps 1-2 frames of the second roll), hence a render from the source.
set G2=[0:v]lut3d=file=TSB_Glow.cube:interp=trilinear,ass=TSB.en.ass,format=yuv420p[g];[1:v]scale=653:-1[wm];[g][wm]overlay=W-w-96:96:shortest=1[v];[2:a]aresample=48000[a]
if "%1"=="master2" (
  ffmpeg -v error -y -i 0926.mov -loop 1 -i TopView-Watermark.png -i 0926.WAV -filter_complex "%G2%" -map [v] -map [a] -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart THE-SHADOW-BELOW-4K-master-v2.mp4
)
if "%1"=="topview2" (
  ffmpeg -v error -y -i THE-SHADOW-BELOW-4K-master-v2.mp4 -c:v libx264 -preset medium -b:v 11500k -maxrate 13500k -bufsize 23000k -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart THE-SHADOW-BELOW-4K-topview-v2.mp4
)
echo EXIT %ERRORLEVEL%
