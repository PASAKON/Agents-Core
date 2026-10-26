# Rebuild kit v2 (overlays, sheet, demo)

Work in a task folder (`Work/<task-id>/`), never in this repo folder: the scripts write `kit.html`,
`overlays/`, `tiles/`, `seg/` and `out/` next to themselves. `K` below is that folder.

```bash
cp -r knowledge/brand-knowledge/brands/ilag/templates/. "$K"/ && mkdir -p "$K"/{footage,frames,sfx,out}
PY=/opt/MoonieXHQ/Agents/Core/.venv/bin/python        # has Playwright + PIL

# 0. Logo: logo.png is the Page's own profile picture lifted off its black square (never redrawn).
#    It is made here every time, not kept in git (1.4 MB; media over 1 MB stays out of git, ADR 0030):
$PY -I "$K"/cut_logo.py knowledge/brand-knowledge/brands/ilag/images/ilag-page-logo-1080.jpg "$K"/logo.png

# 1. Overlays: every element, or a comma list (e.g. "name,end")
$PY -I "$K"/render_kit.py "$K"

# 2. Footage: «ขายชื่อ» EP1 from our own Page (183.6 s, 1080x1920, 24 fps)
yt-dlp -f "2016235605762298v+2016235019095690a" --merge-output-format mp4 \
  -o "$K/footage/ep5-ep1.%(ext)s" "https://www.facebook.com/61594116376333/videos/1376542657800427/"
for t in 0 30 66 78 132 140.5 141.4; do
  ffmpeg -v error -y -ss $t -i "$K"/footage/ep5-ep1.mp4 -frames:v 1 "$K"/frames/f_$t.png; done

# 3. Contact sheet (20 tiles) → out/ilag-kit-sheet-v2.jpg
$PY -I "$K"/compose_sheet.py "$K"

# 4. Sound effects, synthesised (no library, nothing to license)
cd "$K"/sfx
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.55*sin(2*PI*(950*t-900*t*t))*exp(-2.5*t)+0.18*(random(0)*2-1)*exp(-5*t)':s=48000:d=0.5" scratch.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.95*sin(2*PI*52*t)*exp(-8*t)+0.5*sin(2*PI*104*t)*exp(-13*t)+0.35*(random(0)*2-1)*exp(-45*t)':s=48000:d=0.7" -af lowpass=f=1800 thud.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='(0.3*sin(2*PI*(1300+520*sin(2*PI*11*t))*t)+0.06*(random(0)*2-1))*(1-exp(-25*t))*exp(-0.6*t)':s=48000:d=1.0" rewind.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.95*sin(2*PI*46*t)*exp(-2.6*t)+0.35*(random(0)*2-1)*exp(-4.5*t)':s=48000:d=1.8" -af lowpass=f=260 boom.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.5*(random(0)*2-1)*pow(sin(PI*t/0.9),2)':s=48000:d=0.9" -af "highpass=f=500,lowpass=f=3500" whoosh.wav

# 5. Demo → out/ilag-kit-demo-v2.mp4 (44 s). The NG-slam frames need PIL, so draw them first;
#    the encode itself runs anywhere ffmpeg runs (winbox: ~1 min; Contabo: under the render lock).
$PY -I "$K"/build_demo.py "$K" frames
$PY -I "$K"/build_demo.py "$K"
```

The NG stamp and its tape line come in three cuts: `ng` (both, for the sheet), `ngs` (stamp only) and `ngt`
(tape only). `build_demo.py` animates the stamp in on its own and lays the tape over it 6 frames later. The
three source points of the demo sit inside one shot: the cut before the take is at src 139.5.

## Cut a full EP (`tools/ilag_cut.py`)

`build_demo.py` is the 44 s demo with its cuts written into the script. A full EP (10-12 min) is cut from a JSON
EDL by `tools/ilag_cut.py` in the Agents-Core repo; it uses this kit as it is and only sets each card's text.
`tests/fixtures/ilag_cut/demo_edl.json` is the 44 s demo written as an EDL (sources `footage/ep5-ep1.mp4` under `--root`).

Keep one work folder per EP (`Work/<ep>/`, never the repo): `cards/` (card PNGs, NG slam frames), `seg/<id>.mp4`
(one file per segment) and `out/<output>`. Cards are drawn on Contabo, the encode runs on winbox or Contabo, and
both read the same work folder (copy it over; the PNG names are hashes of the card text, so the machines agree).

| Verb | Runs where | Needs |
|---|---|---|
| `plan <edl>` | anywhere | Python stdlib only. Validates the EDL and prints a timeline (id, start, dur, cards) and the total. Exit 1 lists every error. |
| `cards <edl> --kit <templates> --out <work>` | Contabo (venv python) | Playwright + PIL + numpy. Draws each overlay with its own text, 1080x1920 RGBA, cached by sha256 of (element, texts); draws the NG slam frames; one PNG per subtitle line. `--force` redraws all. The logo comes from `--kit`: its `logo.png` (step 0 above), else `cut_logo.py` makes one from `../images/ilag-page-logo-1080.jpg`. |
| `encode <edl> --out <work> [--lock <file>]` | winbox, or Contabo under the lock | Python stdlib + ffmpeg/ffprobe. A segment whose inputs are unchanged is skipped; then concat copy and loudnorm (I=-16 TP=-1.5 LRA=11). Prints path, duration and the ffprobe pix_fmt / SAR / fps / audio rate. |

```bash
PY=/opt/MoonieXHQ/Agents/Core/.venv/bin/python
EDL=Work/ep1/ep1.json
$PY tools/ilag_cut.py plan  "$EDL"                                     # fix every ERROR line first
$PY tools/ilag_cut.py cards "$EDL" --kit "$K" --out Work/ep1/build     # Contabo
$PY tools/ilag_cut.py encode "$EDL" --out Work/ep1/build \
    --lock /opt/MoonieXHQ/Work/.bl-render.lock                          # Contabo: one render at a time
python tools/ilag_cut.py encode ep1.json --out build                    # winbox (no --lock: Linux only, it warns and goes on)
```

Re-run `cards` after editing any card text or sub, after swapping a source of an `ng` segment (its slam frames are
cut from the frozen frame), and after the kit changes (the old PNGs move to `cards/.old/`). Re-run `encode` after
any edit: only the segments whose command line or input files changed are encoded again.

EDL fields (paths are relative to `--root`, default the EDL's folder; times in seconds, gains linear):

- Top level: `fps` (24), `size` ([1080,1920], only this size), `sfx` (folder of `<name>.wav`, default `sfx`), `kit`
  (default for `cards --kit`), `output` (`ilag-ep.mp4`), `loudnorm` (-16), `segments`, `note`.
- Every segment: `id` (unique, `A-Za-z0-9_-`), `kind`, `note`, `cards`, `subs`, `sfx`.
  - `cards`: `[{el, at, dur, texts}]`, `el` is `skip`, `rewcard`, `flash`, `now`, `place`, `name` (wrongdoer, black),
    `namegood` (good character, white), `fact` ("รู้ไว้") or `lesson` ("ข้อคิดจากตอนนี้"). Fades 0.25 s in and out,
    `dur` at least 0.5, inside the segment. `texts`: `tct` (skip, rewcard, now), `fct` + `fsub` (flash),
    `pl1` + `pl2` (place), `nm1` + `nm2` + `nm3` (name, namegood), `body` (fact, lesson). All of them are required,
    except `tct` on `now` (kit default "ปัจจุบัน"). One line each, except `body` of fact and lesson: one `\n` in it
    becomes the kit's `<br>` (at most 2 lines).
  - `subs`: `[{at, dur, text}]`, one line each (kit element `sub`), no overlaps. `sfx`: `[{name, at, gain}]`.
- `clip`: `src in dur`, optional `speed` (0.25-4), `reverse`, `grade` (`none`, `flash`, `desat`), `blur`,
  `freeze_last`, `gain`, `wm`, `blooper`. `grade: flash` adds the black and white flashback grade and the "อดีต" tag.
- `still`: `src dur`, optional `grade blur wm blooper`.
- `ng`: `take {src,in,dur,gain,cards,subs,sfx}`, `take2 {src?,in,dur,...}`, `freeze_at` (default end of the take), `tape`
  (the line on the tape), `rewind_in`, `wm`. Expands to the take, freeze + NG stamp + tape, rewind, and take 2 with
  the "เทค 2" sticker, exactly as in `build_demo.py`.
- `title`: `src in dur blur gain` and `texts {season, ep, title, tagline}` (the episode title takes no quote marks).
- `end`: `src in dur blur gain` and `texts {e2, e3, e4}` (`e1`, `e5` optional).
- `blooper_header`: `src` (image or video) `freeze_at dur`. A `clip` or `still` with `blooper: true` gets the corner
  tag and no watermark; it must come after the `blooper_header`.

What `plan` and `encode` refuse: a story segment (`clip`, `still`, `ng`) without the watermark, a watermark on a
`title`, `end`, `blooper_header` or `blooper`; an em or en dash or a guillemet in any text (CEO 2026-10-26); a line
break outside `body` of fact and lesson; more than 2 `ng`; a card or sub that runs past its segment; overlapping subs;
a missing source, sfx, card PNG or NG frame (the message says "run `cards` first"). A hook (everything before the
`title`) outside 12-15 s, an EP outside 10-20 min, a missing `title` or `end`, and an EP with no `lesson` or no `fact`
card (BRAND.md hard rule 7, the four pillars) only warn. Every segment is encoded as 1080x1920, yuv420p, SAR 1:1, one
fps, 48 kHz stereo AAC (silent sources get `anullsrc`), which is what lets the concat be a stream copy. Segment lengths
round up to whole frames, so the total can differ from the sum of the EDL's `dur` by under one frame per segment.
