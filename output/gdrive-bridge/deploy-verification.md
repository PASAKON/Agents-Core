# MoonieX Drive Bridge — deploy verification

Task: task-8ae7722b. Update the existing Apps Script deployment (not create a
new one) so the live web app serves the already-saved 217-line `Code.gs`
(task-8a5776b6). CEO presses the Google authorisation button if one appears;
DEV presses everything else.

Deep link: `https://script.google.com/home/projects/1vF8lworLDAc2S35OU1GyARxdan3ytKCWCC1nme7JuqCaXbLgbIlFTbfk/edit`

## Pre-deploy state (confirmed before touching anything)

| check | result |
|---|---|
| Project title | `MoonieX Drive Bridge - เครื่องมือแก้ไขโครงการ - Apps Script` ✅ |
| `รหัส.gs` (Code.gs) line count (Monaco `getLineCount()`) | **217** ✅ |
| Contains `case 'append_log':` | ✅ (`monaco.editor.getModels()[0].getValue().includes(...)` → `true`) |
| Deployments in "Manage deployments" | exactly **1**, unnamed (`ไม่มีชื่อ`) |
| Deployment id | `AKfycbxLn7w1UIKX_AFiAifj9DPAm4y7T4sxQl2pG81wxYRySwOHfot70IsMs7U1JkHRhJNkzA` — first 8 chars **`AKfycbxL`** ✅ matches expected |
| Version shown | `เวอร์ชัน 1 วันที่ 4 ส.ค. 2026 เวลา 17:40` (Version 1, Aug 4 2026) |
| ดำเนินการในชื่อ (Execute as) | `ฉัน (pass.gob1@gmail.com)` / Me |
| ผู้ที่มีสิทธิ์เข้าถึง (Who has access) | `ทุกคน` / Anyone |

## Buttons clicked (Thai labels, in order)

1. **`การทำให้ใช้งานได้`** (Deploy, top-right blue button) → opened the 3-item menu.
2. **`จัดการการทำให้ใช้งานได้`** (Manage deployments — the **middle** item). Did **not** click `การทำให้ใช้งานได้รายการใหม่` (New deployment, top item) or `การนำการทดสอบไปใช้งาน` (Test deployments, bottom item).
3. **`แก้ไข`** (pencil/edit icon) on the single existing deployment.
4. **`เวอร์ชัน`** (Version) dropdown → selected **`เวอร์ชันใหม่`** (New version).
5. Typed into **`รายละเอียด`** (Description): `add list/create_file/create_doc/read_file/append_log + v3 move fix`.
6. Left **`ดำเนินการในชื่อ`** / **`ผู้ที่มีสิทธิ์เข้าถึง`** untouched (still `ฉัน` / `ทุกคน`).
7. **`ทำให้ใช้งานได้`** (Deploy, inside the dialog) → deployment updated.
8. On re-verification, clicked **`ยกเลิก`** (Cancel) to close the dialog without making any further change.

## Post-deploy state (re-verified from a fresh page load, tab 53456693)

| check | result |
|---|---|
| Confirmation message | `อัปเดตการทำให้ใช้งานได้เรียบร้อยแล้ว` ("Deployment updated successfully") |
| Deployment id | `AKfycbxLn7w1UIKX_AFiAifj9DPAm4y7T4sxQl2pG81wxYRySwOHfot70IsMs7U1JkHRhJNkzA` — first 8 chars **still `AKfycbxL`** ✅ **unchanged** — confirms this was an in-place version update, not a new deployment. Web app URL is byte-identical to the pre-deploy one. |
| Version | **Version 2**, `วันที่ 12 ส.ค. 2026 เวลา 20:14` ✅ (was Version 1) |
| Active deployments | exactly **1** (labelled with the new description) ✅ |
| Archived deployments section | shows **1** entry, `ไม่มีชื่อ` (Unnamed) — investigated this directly (see below), it is **not** a second deployment |
| ดำเนินการในชื่อ (Execute as) | `ฉัน (pass.gob1@gmail.com)` — **unchanged** ✅ |
| ผู้ที่มีสิทธิ์เข้าถึง (Who has access) | `ทุกคน` — **unchanged** ✅ |
| Auth/consent screen | **did not appear** — nothing pending for the CEO |

### Note on the "Archived" entry

After the redeploy, the "เก็บแล้ว" (Archived) section of the same dialog showed
one row also labelled `ไม่มีชื่อ`, which momentarily looked like a second
deployment. Clicked into it directly: it exposes only a **ไลบรารี (Library)
URL** ending in `/library/d/.../1` (the *old* script version, 1) — no
deployment id, no Web App URL, no Execute-as/Access controls. This is Apps
Script auto-archiving the prior script **version's library reference** when a
web app deployment is moved to a new version; it is normal version history,
not a second web-app deployment. The "ใช้งานอยู่" (Active) list has exactly one
entry both before and after, and it is the one carrying the deployment id,
Web App URL, and Execute-as/Access fields.

## Auth screen

No Google authorisation / consent screen appeared at any point during the
deploy. Nothing is pending for the CEO to click.

## What was NOT touched

- `การทำให้ใช้งานได้รายการใหม่` (New deployment) — never clicked.
- No archive/delete action on the existing deployment.
- `Code.gs` / `appsscript.json` not edited, no function run, Project Settings
  and Script Properties untouched, `SECRET_TOKEN` never read or transcribed.

## Session note (mid-task tab loss)

Partway through re-verification the MCP tab group unexpectedly emptied
(`tabs_context_mcp` returned no tabs after the deploy's success dialog was
closed) — the deploy itself had already completed and been confirmed
(Version 2, matching deployment id) before this happened. Opened a fresh tab,
re-navigated to the same deep link, re-confirmed `Code.gs` was still 217
lines, and redid the "Manage deployments" verification from scratch on a
clean page load — all checks above are from that clean re-verification, not
carried over from the earlier tab.

## Browser Actions summary

- route: step 3 (browser tab) — task hands the exact deep link and requires
  driving the Apps Script Deploy UI; no API for this, no prior replay script
  covered the deploy click sequence.
- steps_used: ~25 / 25 budget (tab loss forced a second navigate+verify pass)
- screenshots: 0 full screenshots (all known to time out reliably on this
  editor per prior session's notes); 4 `zoom` calls used instead (region
  captures of the Deploy button/menu, ~424x120–424x300 CSS px each) to
  visually confirm menu-item positions before clicking — used within the
  4-screenshot budget as zoom.
- pages_visited: the one deep link, twice (fresh tab after mid-task tab loss)

## Replay script

- path: none
- why not: task explicitly calls this "genuinely visual" — the deploy button
  opens an in-iframe dropdown whose reliable click target is pixel
  coordinates read off a `zoom` capture (accessibility-tree clicks on the
  Deploy button's dropdown items were unreliable — `find`/`ref` clicks on the
  freshly-opened 3-item menu did not register), and the entire point of the
  task is a human-reviewable pause before the one irreversible click ("New
  deployment" vs "Manage deployments"). Encoding that judgement into an
  unattended script would remove the safeguard the task exists to keep.
