# Brief: build the TopView Wan 3.0 runner and fire ONE 4-second rehearsal clip

CEO 2026-09-26: "ลอง generate จริงได้เลย · อนุมัติ top view 29$ plan + 30$ credit · เดี๋ยวเราซ้อมใช้งาน browser + auto
script ซักคลิปก่อน 4s คุณภาพต่ำสุด". The ILAG trailer's final footage (about 19 shots) must be generated with Wan 3.0 on
TopView before the challenge closes **28 Sep 06:59 Thai time**. Repeating a browser operation 19 times is a runner's
job, not a model's (IRON-RULES §53), so the job is to BUILD the runner and prove it on one clip.

Read first: skill `CTO_Wan3.0_TopView` (everything known about TopView, all of it unmeasured) and the pattern to copy,
`tools/chatgpt_images.py` (Playwright over CDP, one adapter class, resumable JSON ledger, bytes fetched from the page,
never from the shared Downloads folder).

## Where

- Machine: winbox. Take the screen lease first (skill `winbox-pc-lease`), close every tab you opened, give it back.
- Browser: the dedicated automation Chrome with CDP on port 9224 (profile
  `C:\Users\UsEr\.chatgpt-automation\chrome-profile`, launched by `C:\mooniex\gpt-chrome.cmd`, or the scheduled task
  `MooniexRelayChrome9224` if it is not running). Python: `C:\mooniex\pwvenv\Scripts\python.exe`.
- TopView account: **pass.gob1@gmail.com via "Sign in with Google"** (it already exists; the free-credit application
  was filed from it on 2026-09-23). If that Chrome is not signed in to TopView, sign in with Google as pass.gob1. If
  Google asks for a password, a code or a passkey: STOP and report; the CEO signs in himself.
- Generator: find TopView's Wan 3.0 video page (start at https://www.topview.ai/ and look for Wan 3.0 / "Wan3" in the
  video tools; the challenge page https://www.topview.ai/activity/topview-wan3-challenge links to it). Write the deep
  link you end up on into the report.

## Input (already on winbox)

- `C:\mooniex\ilag-runner\wan3\n01-rehearsal.wan3.json`: `{key, title, seconds: 4, images: [...], prompt, chars}`.
  The prompt is 2,088 characters; its references are written `@Image 1`, `@Image 2` in upload order.
- The pictures, same order, by basename: `C:\mooniex\ilag-runner\wan3\refs\ref-Manta.png` (Image 1),
  `...\refs\loc_village_above_A_v2.png` (Image 2).
- The generator for these files is `docs/prompts/ilag-topview/wan3_prompt.py` in this repo (read it; do not change
  the prompts).

## Job

1. Build `tools/topview_wan3.py`: for each job JSON it opens the Wan 3.0 generator, uploads the images in order,
   puts the prompt in the Direction box, sets duration (the job's seconds), resolution (`--resolution`, default the
   lowest offered), aspect 16:9, **reads the credit cost shown on the Generate button**, generates only if that cost
   is at or under `--max-credits`, waits for the result, fetches the video bytes from the page into `--out`, and
   records every step in a resumable ledger (job key, generation URL or id, cost read, balance before and after,
   file path, md5). `--dry-run` does everything except the Generate click.
2. Run it with `--dry-run` on the rehearsal job first and read, as text: the resolutions and durations offered, the
   cost the button shows for 4 s at the lowest resolution, the credit balance, and **what the Direction box does with
   `@Image 1`**: does pasted text stay plain, does typing `@` open a picker that inserts a chip, is `<<<Image1>>>` the
   form it wants? If the pasted token stays plain text and the UI has a chip picker, make the runner insert the chips
   the way the UI does, and say so.
3. Then fire exactly ONE real generation of the rehearsal job, 4 s, lowest resolution, `--max-credits 3`. Collect the
   clip. Do not fire anything else.

## Money (HARD)

- Exactly one generation, and only if the button shows 3 credits or fewer. Anything above: do not click, report it.
- Never click Subscribe, Upgrade, Buy, Top up, a trial, or any payment or card screen. If the balance is too low or
  the generator needs a plan: stop and report the exact text on screen. The CEO buys the plan himself.
- Never click a "Regenerate"/"Retry" that fires again; if a generation fails, report it and stop.

## Report (REPORT.md in your worktree)

- The deep link to the Wan 3.0 generator, and the selectors that worked.
- Resolutions and durations offered; the cost read before the click; balance before and after.
- The reference token that works, and how the runner writes it.
- Whether the clip has sound, its real duration and resolution (`ffprobe`), the md5, and where it is on winbox.
- How long the generation took.
- `## Replay Script`: `tools/topview_wan3.py`, and `python tools/check_replay_script.py tools/topview_wan3.py` must
  exit 0.
- `## Skill learning` lines (`MISSING [CTO_Wan3.0_TopView §...] : ... · evidence: ...`): every fact you measured goes
  there, because that skill is still all claims.

Budget: 90 steps, 12 screenshots (the page is new to us; after the first map, use text and the DOM). Answer in text.
Commit the runner on your branch; do not push to main.
