# task-ee1dbcf0 iteration 3: ILAG hook demo, three ElevenLabs v4 takes

$0 spend: local files and ffmpeg only. Render ran on Contabo, one take at a time, under `flock /opt/MoonieXHQ/Work/.bl-render.lock`, `nice -n 19`, `free -m` before each (available memory 2.7 to 3.0 GB).

## Per take

Measured with ffmpeg ebur128 (`peak=true`) on the delivered files by `video/hookdemo/take_stats.py`.

| take | voice end | total length | LUFS (720p / master) | true peak dBTP (720p / master) | 720p size |
|---|---|---|---|---|---|
| t1_Brian_s0.5 | 19.84 s | 23.17 s | -16.5 / -16.4 | -1.4 / -1.5 | 6.4 MiB |
| t2_George_s0.5 | 19.28 s | 22.62 s | -16.5 / -16.5 | -1.9 / -2.2 | 6.3 MiB |
| t3_George_s0.3 | 19.44 s | 22.79 s | -16.5 / -16.4 | -1.5 / -1.5 | 6.3 MiB |

Total = voice end + 0.34 s tail, then title 2 s, then rewcard 1 s. No atempo anywhere.

## Holds under 0.8 s

The subtitle shows one whole line of lines.txt at a time, so "phrase on screen" has three readings. All are listed.

| take | subtitle line hold under 0.8 s | spoken phrase under 0.8 s | cut under 0.8 s |
|---|---|---|---|
| t1 | none (shortest 2.34 s, line 4) | 5.1 "แต่วันนี้" 0.76 s | cut 3 (S1) 0.71 s |
| t2 | none (shortest 2.22 s, line 4) | 5.1 "แต่วันนี้" 0.80 s (at the limit) | cut 3 (S1) 0.62 s |
| t3 | none (shortest 2.34 s, line 4) | 2.1 "ใครแตะ" 0.68 s | none (shortest 0.88 s) |

Cut 3 is anchored to the end of phrase 1.2 minus 0.25 s, so a quick delivery of "ตำส้มตำเก็บแปดหมื่น" shortens it. If the pick is t1 or t2 and cut 3 reads too jumpy, move that anchor to a gap fraction in `make_edl.py` CUTS. Not changed here, to keep the three takes on identical rules.

## Phrase starts (seconds, first phrase of each line)

| take | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| t1 | 0.00 | 3.52 | 7.28 | 10.40 | 12.76 | 16.72 |
| t2 | 0.00 | 3.52 | 7.28 | 10.24 | 12.48 | 16.28 |
| t3 | 0.00 | 3.72 | 7.28 | 10.24 | 12.60 | 16.44 |

Full per-phrase times: `out/v4/<take>/timing.json`.

## fal loader (`video/hookdemo/align.py`)

`load_alignment(path, narration)` accepts a plain ElevenLabs alignment or a fal file. A fal file is joined chunk by chunk (10 chunks per take), then checked, then handed to the existing parser. It exits non-zero and says why on:

- a chunk missing a key: `fal chunk 3 lacks 'character_end_times_seconds' (has [...])`
- a negative or non-numeric time, or an end before its start
- a start time that goes backwards across the joined characters: `time goes backwards at character 52 ...`
- joined characters not equal to narration.txt (whitespace and "..." ignored): `... do not match the narration ... at offset 18: alignment has 'ส้มตำเก็กแปดหมื่' , narration has 'ส้มตำเก็บแปดหมื่น'`
- a truncated take (length 163 vs 177), empty `timestamps`, not JSON, or any other shape

All 3 takes load and map all 15 phrases. 8 unit tests pass: `python3 -m unittest video/hookdemo/test_align.py`. Eight hand-made bad files were also run through the CLI, all exit 2.

## One command

`video/hookdemo/make_hook.sh <take-name>`, for example `make_hook.sh t2` or `make_hook.sh t2_George_s0.5`. It resolves the take, prints `free -m` and refuses below 1200 MB available, validates the json first, waits for the lock, runs under nice 19, and writes `hookdemo/out/v4/<take>/`.

## Seen by eye

t1 contact sheet read frame by frame: subtitles wrap between phrases, line changes land with the voice, title card has no watermark, rewcard follows the title, last montage frame is the blank-card fan (S17) as in the rehearsal. t2 and t3 were not looked at frame by frame; they run the same chain and their numbers are in the tables above.

## Not checked / risk

- Voice quality, pronunciation and delivery were not judged: I did not listen. The CEO picks by ear.
- The sample-peak/true-peak above is on the AAC output; a different player's decoder can differ by a fraction of a dB.
- Alignment times are quantised to 0.04 s steps by fal, so a cut can sit up to 0.04 s off a word.
- The alignment ends 0.04 to 0.05 s after the mp3's own duration on every take (e.g. 19.84 vs 19.80 s). make_edl accepts up to 0.3 s; the last word may be clipped by that much.
- `ilag_cut.py` and the kit come from branch agent/developer-task-b7e13b61 (PR #468, md5 70029b37), unpacked into `hookdemo/_tool`. A newer review-fix version exists on agent/developer-task-4edacf73 and was not tried.
- `hookdemo/work/` (125 MB of segment cache) was left in place so a rerun is fast; delete it to free disk (Contabo is at 89%).
