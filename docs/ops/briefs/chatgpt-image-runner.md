# Brief: a zero-model ChatGPT image runner on winbox

IRON 53: an operation repeated more than 3 times gets a runner, not an operator.
The ILAG trailer needs dozens more images (7 plates now, ~22 storyboard frames
next). Build the runner; after this task no model sits in the loop.

## What already exists (measured 2026-09-24 by the CTO)

- Click path, selectors verified: `docs/reports/ilag-trailer-chatgpt-characters-20260924/REPLAY.md`
  (new chat = navigate to https://chatgpt.com/, composer `#prompt-textarea`, paste
  via a synthetic paste event, wait, open the image, download).
- Round 2 proved attaching a reference image to the message works and keeps a
  character consistent: `docs/reports/ilag-trailer-chatgpt-round2-20260924/REPORT.md`.
- Pattern to copy: `tools/flow_shoot.py` (Playwright over CDP, one adapter class,
  resumable ledger, `_log`).
- On winbox: Playwright 1.47 in a separate venv `C:\mooniex\pwvenv` (never touch
  the Cookie Run venv). A dedicated Chrome profile
  `C:\Users\UsEr\.chatgpt-automation\chrome-profile` listening on CDP port **9224**,
  launched by `C:\mooniex\gpt-chrome.cmd` through an interactive scheduled task
  (a process started from ssh cannot reach the desktop). ChatGPT loads there with
  no Cloudflare challenge and `navigator.webdriver` false. The CEO is logging
  ChatGPT in to that profile; until he has, only the logged-out paths can be tested.

## Build

`tools/chatgpt_images.py` (runs ON winbox with the pwvenv python):

- Input: a brief markdown file whose prompts sit between `PROMPT START` / `PROMPT END`
  under `## Image N: <name>` headings (see `docs/ops/briefs/ilag-trailer-chatgpt-round3-village.md`),
  or a small JSON list `[{name, prompt, attach?}]`. Optional per image: a reference
  image path to attach.
- Per image: new chat, optional attach (file input + `set_input_files`), paste the
  prompt, submit, wait for the generated image to finish (detect completion, time out
  at 6 min), then **fetch the image bytes straight from the page (the `<img>` src,
  via the page's own fetch or `page.request`), not from the Downloads folder**:
  Downloads is shared with other workers and once handed a task someone else's file.
- Save to an output dir as `<name>.png`; never overwrite; refuse a result whose MD5
  equals any file already in the output dir. Ledger `<out>/ledger.json` (name, chat
  URL, md5, bytes, px, time) so a rerun skips finished names.
- Stop cleanly with a clear message on: logged out, usage limit, paywall, refusal
  (record ChatGPT's text in the ledger).
- `--dry-run` (parse the brief, print what it would do), `--one <name>`.
- Concurrency: one image at a time is fine.

## Test

1. `--dry-run` against the round-3 brief: lists 3 names and prompts, exits 0.
2. Once the CEO has logged in (check: `#prompt-textarea` present in the 9224
   Chrome): generate ONE image, e.g. a throwaway prompt "a single red apple on a
   white table, photo" into `C:\mooniex\ilag-trailer\runner-test\`. Report its md5,
   size and the ledger row. If he has not logged in when the code is ready, stop
   after the dry run and report that the live test is waiting on the login.
3. Take the pc-lease for the live test (`windows/pc_lease.py` with the Cookie Run
   venv python, since you are on winbox), give it back after.

## Report

REPORT.md: files changed, the dry-run output, the live test result (or why it did
not run), and the exact command the CTO runs for a batch. Budget: 90 minutes.
