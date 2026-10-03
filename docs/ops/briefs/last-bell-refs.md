# Brief: THE LAST BELL, reference images round 1 (ChatGPT on winbox, zero-model runner)

This file is the source of truth. Ignore any partial pane message that disagrees with it.

CEO, 2026-10-03: "สั่ง worker ไป generate Image มาให้เลือกได้เลย". The CEO chose ChatGPT on winbox (plan, no
extra money). Read the film first, 2 minutes: `docs/prompts/last-bell/CAST.md` and `docs/prompts/last-bell/REFS.md`.

## The job

Generate 18 reference images with `tools/chatgpt_images.py` from the ready-made prompt list
`docs/ops/briefs/last-bell-refs-round1.json` (built by `docs/prompts/last-bell/build_refs.py`; do not edit
prompts by hand). Then make contact sheets so the CEO can choose by number. You do not judge taste and you do
not redo anything for taste. Pairs `_a` / `_b` are deliberately the same prompt in two new chats: two castings.

## Steps (winbox, repo `C:\Users\passg\mooniex\repo\MoonieX-Agents`, python `C:\mooniex\pwvenv\Scripts\python.exe`)

1. `git pull` so you have this brief and the JSON.
2. PC lease: `python windows\pc_lease.py status`, then take it ("browser_operator: Last Bell refs", 120 min).
   Cookie Run is already on a human ESC hold: never clear or touch that hold. Give the lease back at the end,
   also on failure.
3. The ChatGPT Chrome on CDP 9224 is down. Start it with `schtasks /Run /TN MooniexRelayChrome9224` (desktop
   Chrome, profile `C:\Users\passg\.chatgpt-automation\chrome-profile`). Wait until
   `curl -s http://127.0.0.1:9224/json/version` answers. Never `taskkill` Chrome by name.
4. Output dir `C:\mooniex\last-bell\refs\` (create it). Dry run first, then the real run:
   `C:\mooniex\pwvenv\Scripts\python.exe tools\chatgpt_images.py --json docs\ops\briefs\last-bell-refs-round1.json --out C:\mooniex\last-bell\refs --dry-run`
   then the same without `--dry-run`. It resumes from its ledger; re-run the same command after a stop.
5. If the runner stops on "logged out": stop, give back the lease, and write in the report one line
   `relay-login: winbox:9224 — <tab title> · account: ChatGPT · why: reference images` (skill relay-login).
   Print tab titles only, never URLs.
6. If it stops on a usage or image limit: record how many are done and the reset time shown, then finish the
   report. Never use the OpenAI API, fal, or another account (money).
7. A refusal on one image: copy ChatGPT's reply text verbatim into the report and continue with the rest
   (re-run skips done names). Do not rewrite the prompt.
8. Contact sheets, numbered, with `tools/plate_montage.py` (looks at files, labels by name):
   - `C:\mooniex\last-bell\sheets\characters.jpg` from the ten `ch_*` files
   - `C:\mooniex\last-bell\sheets\world.jpg` from `loc_*`, `prop_*`, `key_*`
   Look at each sheet once. Check only the hard rules: character sheets on a plain white background with
   numbered panels plus one full-body panel; location plates with no people; no watermark. Write pass/fail per
   image with a reason. One same-chat fix per failed image at most:
   `... tools\chatgpt_images.py --out C:\mooniex\last-bell\refs --name <name>-2 --continue <name> --prompt "Keep everything the same; <the one fix>"`.

## Non-goals

- Do not generate video. Do not open champa, Flow or Higgsfield.
- Do not upload to Google Drive. The CTO files the picks after the CEO chooses.
- Do not open the 18 images one by one; look at the two sheets.
- Images and sheets never go into git.

## Budget

Runner does the clicking: no screenshots for generation. QC: 2 sheet views, at most 4 re-edits. Stop if the
`C:` drive has under 5 GB free.

## Report: `docs/reports/last-bell-refs-r1/REPORT.md` (commit and push on your branch)

- Table: name, final file, pixel size, bytes, MD5, QC pass/fail + reason, ChatGPT reply text if any.
- The two sheet paths on winbox.
- Lease taken and given back (times).
- Skill learning section.
