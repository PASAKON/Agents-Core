# EP01 v3 (task-7a7d1a66): v2 + 3 narrator lines. State: staged, NOT run past the $0 prep (spend gate open).

Scripts live in /opt/MoonieXHQ/Work/cn-series/voice/v3 (copies here). Work dir: /opt/MoonieXHQ/Work/cn-series.

## Narrator voice (proved from code + logs, not guessed)
- EN and TH narrator = fal `elevenlabs/tts/eleven-v4`, voice "Brian", stability 0.5, seed 7 (language_code th / en).
- voice/tts_chunks_lang.py defaults `VOICE = "Brian"`; every logged call (en1, en2, en3, TTS_LANG=en) passes no voice argument.
- en{1,2,3}/c*.mp3 were written 24 Oct 22:24-22:40; the "25 Oct" change was post-processing only (voice/rebuild_en_b.py, chain B), not a voice change.
- Prior session note: 'the raw ElevenLabs v4 "Brian" English is a normal ~14 chars/s'.
- Method check done at $0: rebuild_en chain from c*_b.wav reproduces en1_voice.wav and en3_voice.wav bit for bit; TH chain reproduces arc3_voice.wav bit for bit; bed.py reproduces arc3_th_music.wav and en1_music.wav bit for bit.

## Insert points (cut inside an existing pause of the raw chunk mp3; words confirmed with faster-whisper small)
| key | chunk | silence in raw chunk | words around it |
|---|---|---|---|
| th1 punch | arc1/c05 | 24.52-25.16 | ราคา (ends 24.46) | ทั้งหอ (25.06) |
| th1 title | arc1/c00 | 75.48-76.08 | ...เนี่ยนะ? | แล้วปากของเขา (0:12 block ends) |
| th3 reveal | arc3/c06 | 65.35-66.02 | กระพริบ (ends 65.34) | ตัวเลขอายุขัย (65.9) |
| en1 punch | en1/c13 | 23.65-24.28 | worth (ends 23.5) | The whole hall gapes |
| en1 title | after en1/c01 (chunk boundary) | - | "...bidding ten thousand on?" | c02 |
| en3 reveal | en3/c08 | 7.70-8.41 | flashing. (7.48) | Luo Yi's lifespan drains |
No pause is long enough for the line (0.6-0.7 s), so each insert holds the picture: the section holding it grows by the insert length, full.py fits the shots (slow <=1.3x, then filler), music beds move with the sections.

## Resume (after the CEO card RUN-20261026-1318-7bd8 shows done)
1. TTS, from /opt/MoonieXHQ/Agents/Core, one take per line first (<= 3 takes/line, cap $0.25 total):
   `.venv/bin/python tools/infisical_setup.py run Agents-Core prod --path /cmo-media --as contabo -- .venv/bin/python /opt/MoonieXHQ/Work/cn-series/voice/v3/tts_insert.py <th|en> <title|punch|reveal> <1|2|3>`
   Judge each take: duration (title <= 3 s), faster-whisper small transcript, level. EN title is ~56 chars: may need atempo or leaving out.
2. Voice: `python -I voice/v3/build_voice_v3.py <th1|th3|en1|en3> build --takes th_title=1,th_punch=1` (en_*: en_title=1,en_punch=1; th3/en3: <lang>_reveal=1). Prints d (added seconds) per insert; writes voice/v3/<key>/timing.json.
3. `python -I voice/v3/make_cfg_music.py <key>` writes cut/arc?_?_cfg_v3.py + music/*_v3.wav.
4. One encode at a time: `flock /opt/MoonieXHQ/Work/.bl-render.lock bash cut/chain.sh arc1_cfg_v3 arc1_TH_v3 music/arc1_music_v3.wav` (same for arc1_en_cfg_v3/arc1_EN_v3/en1_music_v3, arc3_th_cfg_v3/arc3_TH_v3/arc3_th_music_v3, arc3_en_cfg_v3/arc3_EN_v3/arc3_en_music_v3). `free -m` + `df -h /` first; stop under 2 GB free.
5. `bash cut/full_ep.sh TH arc1_TH_v3 arc2_TH_nt arc3_TH_v3 EP01_TH_full_v3` and `... EN arc1_EN_v3 arc2_EN_nt arc3_EN_v3 EP01_EN_full_v3` (prints the LINK lines; md5 by id inside final_up.py).
6. 12 s review clips around each insert into cut/v3_check/.
