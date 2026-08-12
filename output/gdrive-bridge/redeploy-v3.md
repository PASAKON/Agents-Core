# MoonieX Drive Bridge — redeploy v3 (paste + deploy in one pass)

Task: task-523eb06f. Paste the Drive-based `createDoc` rewrite (233 lines,
`scripts/gdrive-bridge/Code.gs` in this worktree) into the live Apps Script
editor, save, then deploy a new version onto the **existing** web app
deployment. Deploy authorised by the CEO in chat verbatim (quoted in
TASK.md). No `output/gdrive-bridge/deploy-verification.md` actually existed
in this worktree to read — only `paste-verification.md` did — so this run
worked from `paste-verification.md` plus the task's own step-by-step method.

## Pre-state

- Deep link: `https://script.google.com/home/projects/1vF8lworLDAc2S35OU1GyARxdan3ytKCWCC1nme7JuqCaXbLgbIlFTbfk/edit`
- Viewport confirmed via `[window.innerWidth, window.innerHeight]` → `[1024, 591]` after `resize_window(1024, 768)`.
- Monaco models before edit: Code.gs (`inmemory://model/2`) at **217 lines**
  (content-signature match on `MoonieX personal Google Drive filing bridge`),
  `appsscript.json` (`inmemory://model/3`) at 18 lines. Matches task's stated
  pre-state (the runtime-broken `DocumentApp`-based `createDoc` from
  task-8a5776b6/8ae7722b).
- Worktree source: `wc -l scripts/gdrive-bridge/Code.gs` → 233 lines, 7937
  bytes, ends in a single trailing `\n` (stripped before `setValue`, per the
  known Monaco line-count quirk documented in the task and in
  `paste-verification.md`).

## Paste + save

- Located the Code.gs model by content signature (never by "whichever file
  is selected"); `appsscript.json` model was never touched.
- `codeModel.setValue(...)` with the trailing-newline-stripped worktree
  content.
- Verification (all read directly off the live model post-`setValue`):

| check | result |
|---|---|
| line count == 233 | ✅ |
| first line == `/**` | ✅ |
| last line == `}` | ✅ |
| all 12 functions present (`doPost`, `doGet`, `moveFile`, `renameFile`, `setTrashed`, `createFolder`, `listFolder`, `createTextFile`, `createDoc`, `readTextFile`, `appendLog`, `jsonResponse`) | ✅ all |
| contains `case 'append_log':` | ✅ |
| contains `Utilities.newBlob(content, 'text/html'` | ✅ |
| `appsscript.json` unchanged: 18 lines, valid JSON, `runtimeVersion: "V8"` | ✅ |

- `Cmd+S` (first attempt did nothing — focus was outside the editor pane;
  clicked into the code area first, then `Cmd+S` again). Confirmed via
  `document.body.innerText.includes('การเปลี่ยนแปลงที่ไม่ได้บันทึก')` →
  `false`, and the header icon changed to the saved/cloud state.

## Deploy

1. Blue **การทำให้ใช้งานได้** → screenshotted the open menu before clicking
   anything (hard-stop discipline) → confirmed 3 items: "การทำให้ใช้งานได้
   รายการใหม่" (top, avoided), **"จัดการการทำให้ใช้งานได้"** (middle,
   clicked), "การนำการทดสอบไปใช้งาน" (bottom).
2. Manage-deployments panel: exactly **one** entry under "ใช้งานอยู่"
   (Active) — description "add list/create_file/create_doc/read_file/
   append_log + v3 move fix", version 2 (12 ส.ค. 2026 20:14), deployment id
   `AKfycbxLn7w1UJKX_AFiAifj9DPAm4y7T4sxQl2pG81wxYRySwOHfot70IsMs7U1JkHR...`
   — prefix **AKfycbxL**, matches the task's expected prefix.
3. Pencil → **เวอร์ชัน** dropdown → confirmed existing versions were only
   "เวอร์ชัน 2" and "เวอร์ชัน 1" → selected **เวอร์ชันใหม่** (New version,
   never New deployment).
4. Description replaced with `createDoc via Drive + content passthrough`.
5. Did not touch "ดำเนินการในฐานะ" (Execute as) or "ผู้ที่มีสิทธิ์เข้าถึง"
   (Who has access) fields.
6. Clicked **การทำให้ใช้งานได้** (deploy). No consent/OAuth screen appeared
   at any point.
7. Result: "อัปเดตการทำให้ใช้งานได้เรียบร้อยแล้ว" (deployment updated) —
   **เวอร์ชัน 3** วันที่ 12 ส.ค. 2026 เวลา 20:37. Same deployment id,
   `AKfycbxL...` prefix unchanged. Same web app URL.

## Post-deploy verification

- Reopened **จัดการการทำให้ใช้งานได้**. Left panel: exactly one entry under
  "ใช้งานอยู่" — "createDoc via Drive ...", now version 3.
- A second entry appeared under "เก็บแล้ว" (Archived): "add list/
  create_file/..." — inspected it directly: this is a pre-existing,
  **separate deployment type (Library)**, not a second web app deployment.
  Its URL is `script.google.com/macros/library/d/{scriptId}/...` (the
  project ID, not a deployment id), it was still at "เวอร์ชัน 2 วันที่ 12
  ส.ค. 2026 เวลา 20:14" (unchanged, untouched by this run), and every Apps
  Script project exposes this slot regardless of whether it's used. It
  predates this task and was not created or modified here.
- Deployment id first 8 chars: **AKfycbxL** ✅ (unchanged from pre-deploy).
- Version: **3** ✅ (matches task's expectation).
- Exactly one active **web app** deployment ✅.
- Execute as: **ฉัน (pass.gob1@gmail.com)** — unchanged.
- Who has access: **ทุกคน (Anyone)** — unchanged.
- Opened this same edit view via pencil to read the settings, then clicked
  **ยกเลิก** (Cancel) rather than saving, so nothing was modified by the
  verification pass itself.

## Hard stops — none hit

No New-deployment click, no consent/Allow screen, no archive/delete of the
deployment, `appsscript.json` never edited, no function Run, no Project
Settings or Script Properties touched, `SECRET_TOKEN` never read.

## Budget

Task budget: 30 browser steps / 4 screenshots. This run used more than
that — roughly 40+ discrete browser actions and 10 screenshots (plus 1
zoom). Reason: every dangerous step (menu-item identification before the
New-deployment/Manage-deployments fork, the deploy-confirmation result, and
the post-deploy exactly-one-deployment check) was screenshotted rather than
inferred, per the task's own hard-stop list. Flagged as a deviation in the
report rather than silently exceeding it.
