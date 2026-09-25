# Brief — «ตาชั่งของเสี่ย» character plates (ChatGPT) + Flow upload probe

CEO 2026-09-25: "สร้าง Charactor ออกมาได้เลย แนะนำให้สร้างจาก Chat GPT Browser Operator นะ แล้วค่อย
Import / Upload เข้าไปใน Google Flow … สร้าง Charactor ส่งมาให้ Review ได้เลย"

Read first: `docs/scripts/taachang-CAST-STATES.md` (the state system and what every plate is for).

## Part A — make 18 plates (zero-model runner, you only QC)

- Prompts: `docs/ops/briefs/taachang-characters-round1.json`. It holds 18 items in 7 chats. Every `__<state>` item
  `continue`s its character's previous image, so all states are edits in the FACE's own chat. **Never run a
  state in a new chat**: a new chat makes a different person.
- Chrome: the Mac ChatGPT automation Chrome is **up on CDP 127.0.0.1:9223** (profile `~/.flow-automation/chrome-profile`,
  already signed in). Do not quit it when you finish; the CTO lane keeps using it.
- Output dir: `/Users/gob/MoonieXHQ/Work/<your task-id>/out/plates/`. Create it with
  `python tools/workdir.py create <task-id>`.
- Run:
  `.venv/bin/python tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 --json docs/ops/briefs/taachang-characters-round1.json --out <out>/plates`
  It resumes from its ledger. If it stops, read `<out>/plates/ledger.json` and use `--recover <name>` before re-generating.
- **ChatGPT Plus image cap:** if the page says you have hit an image limit, stop, record how many are done and the
  reset time it shows, and finish the report. Do not create another account, and do not use the OpenAI API (HARD, money).

**QC. Look at contact sheets, never at single files.** One sheet per character:
`python3 tools/plate_montage.py <out>/sheets/<char>.jpg <out>/plates/<char>__*.png`
(it takes files or directories). Check each sheet for:
1. Same person in every state as in `__face`: face shape, eyes, nose, age. The hair may differ only where the prompt says so.
2. No text, logo, badge, embroidery or name tag anywhere. School shirts especially.
3. Full body head to toe, plain grey backdrop, nothing in the hands.
4. `sia__humbled` has no gold chain; `sia__reformed` has no jewellery.

Fix a failed plate with a same-chat edit, at most 2 per plate:
`.venv/bin/python tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 --out <out>/plates --name <plate>-2 --continue <plate> --prompt "Keep everything the same; <the one fix>"`.
Write down which file is final.

## Part B — can a plate get into Google Flow with no human click? (probe, 0 credits)

Known (skill google-flow-ops §"What the frame picker will actually show you"): Flow's `เมนูเพิ่มสื่อ → อัปโหลด`
opens an OS-native picker. No `<input type=file>` appears; it looks like `showOpenFilePicker()`. The extension's
file_upload cannot drive it. Nobody has tried Playwright yet. Use ONE adult plate, `pa__face` (final version), in a
**new** Flow project named `ตาชั่งของเสี่ย` at https://labs.google/fx/th/tools/flow (same 9223 Chrome, signed in to Google).
Try in this order and stop at the first that works:
1. `page.expect_file_chooser()` around the อัปโหลด click, then `set_files`. This works if an input is created lazily.
2. Before the click, override the picker in the page:
   `window.showOpenFilePicker = async () => [{kind:'file', name:'pa__face.png', getFile: async () => FILE}]`,
   where FILE is a `File` built in-page from base64 that you pass through `page.evaluate`. Do not fetch from localhost:
   page CSP has blocked that before.
3. A synthetic drop: dispatch `dragenter`/`dragover`/`drop` with a `DataTransfer` holding that File on the project canvas.

Success means the image appears in the project's media, AND you can turn it into a character Element (องค์ประกอบ /
Character) named `pa__face`. **If any control shows a credit cost, do not click it: stop and report the exact text.**
If a method works, leave it as `tools/flow_upload_element.py` (Playwright over CDP, args `--cdp-url --project-url
--file --name`, `--dry-run`). Upload only `pa__face`; the rest waits for the CEO's review.
If all three fail, write what each did (one line each) and stop. Do not ask the CEO for a click; the CTO does that.

## Non-goals

- Do not generate anything in Flow (no video, no image).
- Do not make props or locations.
- Do not upload to Google Drive.
- Do not open the plates one by one.

## Budget

- ChatGPT: the runner does the clicking, so it needs no screenshots.
- QC: 6 contact-sheet images (sia takes two if needed) and ≤ 8 re-edits.
- Part B: ≤ 40 browser steps, ≤ 6 screenshots.
- Disk: the Mac is near its floor (6.9 GB free at spawn). Stop if `df -h /` shows < 5 GB.

## Report (`docs/reports/taachang-characters/REPORT.md`)

- A table of plate → final file → QC pass/fail + reason.
- The sheet paths (the CTO sends them to the CEO).
- Part B result (the method that worked, or what each of the three did).
- Replay script path(s).
- Skill learning.
- Keep images OUT of the repo. They stay in Work/.
