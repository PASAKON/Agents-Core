# «ตาชั่งของเสี่ย» character plates (ChatGPT) + Flow upload probe — REPORT

task-c2723478, 2026-09-25. Brief: `docs/ops/briefs/taachang-characters.md` (main @29d809e0).

## Part A — 18 plates, zero-model runner

Ran `.venv/bin/python tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 --json
docs/ops/briefs/taachang-characters-round1.json --out <out>/plates` against the Mac
ChatGPT automation Chrome (CDP 127.0.0.1:9223, already signed in). **18/18 completed,
exit 0, ledger clean, zero errors, zero recoveries needed.** Chrome left running.

Output dir: `/Users/gob/MoonieXHQ/Work/task-c2723478/out/plates/` (created via
`tools/workdir.py create task-c2723478`).

| plate | final file | size | QC |
|---|---|---|---|
| `yai__face` | `yai__face.png` | 2.7 MB | **PASS** |
| `yai__collect` | `yai__collect.png` | 2.1 MB | **PASS** |
| `yai__home` | `yai__home.png` | 2.1 MB | **PASS** |
| `sia__face` | `sia__face.png` | 2.4 MB | **PASS** |
| `sia__boss` | `sia__boss.png` | 2.1 MB | **PASS** |
| `sia__factory` | `sia__factory.png` | 1.8 MB | **PASS** |
| `sia__humbled` | `sia__humbled.png` | 1.9 MB | **PASS** — no gold chain, confirmed on sheet |
| `sia__reformed` | `sia__reformed.png` | 1.9 MB | **PASS** — no jewellery at all, confirmed on sheet |
| `kla__face` | `kla__face.png` | 2.1 MB | **PASS** |
| `kla__school` | `kla__school.png` | 1.8 MB | **PASS** — plain white shirt, no badge/embroidery |
| `kla__work` | `kla__work.png` | 2.0 MB | **PASS** |
| `tor__face` | `tor__face.png` | 2.3 MB | **PASS** |
| `tor__school` | `tor__school.png` | 1.8 MB | **PASS** — plain dark backpack, no print |
| `tor__home` | `tor__home.png` | 1.8 MB | **PASS** |
| `pa__face` | `pa__face.png` | 2.6 MB | **PASS** |
| `pa__collect` | `pa__collect.png` | 2.0 MB | **PASS** |
| `scaleman__work` | `scaleman__work.png` | 2.0 MB | **PASS** |
| `worker__work` | `worker__work.png` | 2.0 MB | **PASS** |

**QC method:** one contact sheet per character (`tools/plate_montage.py`), looked at
each sheet once (per the tool's own doctrine — a script written from memory drifts,
looking at the tiled sheet is the check). Checked: same face/eyes/nose/age across
states vs. `__face`; no text/logo/badge/embroidery/name tag anywhere (school
uniforms especially); full body head-to-toe, plain grey backdrop, nothing held in
the hands; `sia__humbled` no gold chain, `sia__reformed` no jewellery.

**Result: 18/18 pass on first generation. Zero same-chat fixes needed** (budget was
≤2 per plate / ≤8 total). No re-edit runs were made.

### Sheet paths (for the CTO to send the CEO)

```
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/yai.jpg        (1600x2444, 3 plates)
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/sia.jpg        (1599x1644, 5 plates)
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/kla.jpg        (1600x2444, 3 plates)
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/tor.jpg        (1600x2444, 3 plates)
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/pa.jpg         (1600x1222, 2 plates)
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/scaleman.jpg   (1600x1558, 1 plate)
/Users/gob/MoonieXHQ/Work/task-c2723478/out/sheets/worker.jpg     (1600x1558, 1 plate)
```

Images stay in `Work/`, never committed to the repo, per the brief.

## Part B — Flow upload probe (0 credits)

**Result: Method 1 worked on the first try. `pa__face` (final) is now uploaded,
renamed, and attached as a composer Element in a new Flow project
"ตาชั่งของเสี่ย"** at
`https://flow.google.com/project/3366f1f0-c07e-4338-a316-7435d7975193`.

| method | tried | result |
|---|---|---|
| 1. `page.expect_file_chooser()` around the อัปโหลด click, then `set_files()` | yes | **WORKED** — Playwright intercepts the lazily-created `<input type=file>`; the image uploads and appears in the project's media grid with a progress % that clears |
| 2. override `window.showOpenFilePicker` with an in-page File | no | not needed |
| 3. synthetic `dragenter`/`dragover`/`drop` with a `DataTransfer` | no | not needed |

**"Turning it into a character Element" did NOT mean Flow's separate "สร้างตัวละคร"
(Create Character) flow** — that opens a generator (model-group picker,
"เริ่มสร้าง" submit) that would *re-render* a face from a text prompt, which is
exactly the identity drift this whole plate system exists to avoid, and its cost
was never checked (never clicked เริ่มสร้าง). Instead, the working, confirmed-free
path is:

1. Upload as a plain image (method 1 above).
2. Right-click the tile → **เปลี่ยนชื่อ** (rename) → type the handle (`pa__face`).
3. Right-click again → **เพิ่มไปยังพรอมต์** (add to prompt) — this is Flow's actual
   reference-chip/Element mechanism (the same action the composer's `+` picker's
   own "เพิ่มไปยังพรอมต์" button performs). Confirmed: a
   `<img alt="รูปภาพองค์ประกอบ">` chip appeared in the composer immediately after.

**No control at any point showed a credit cost.** The only priced control on the
page is "เริ่มสร้าง" (Start creating / Submit), which this tool never touches. A
`scan_for_price()` guard in the replay script checks page text for
เครดิต/credit before every click and raises rather than clicking through one —
it never fired.

**Sequence actually run (2026-09-25):**
- Probed with a throwaway synthetic 64x64 dummy PNG first (not `pa__face`, which
  the ChatGPT runner hadn't produced yet) to validate the three-method ladder
  without risking the real plate on an unproven click path.
- Confirmed method 1 end-to-end with the dummy: upload → rename → attach chip, all
  free.
- Deleted the dummy asset (moved to Flow's own recoverable ถังขยะ, not a hard
  delete) so the review project wasn't polluted with test data.
- Ran the finished `tools/flow_upload_element.py` against the real, final
  `pa__face.png` plate. Output:
  ```
  PROJECT: https://flow.google.com/project/3366f1f0-c07e-4338-a316-7435d7975193
  UPLOADED: pa__face.png
  RENAMED: pa__face.png -> pa__face
  ELEMENT_CHIP_BOUND: True
  EXIT=0
  ```

Only `pa__face` was uploaded, as instructed — the other 17 plates wait for the
CEO's review of the contact sheets before anything else goes into Flow.

## Replay script

`tools/flow_upload_element.py` — Playwright over CDP, args `--cdp-url
--project-url --project-name --file --name [--dry-run]`. Encodes the proven
method (file-chooser upload → rename → add-to-prompt attach) plus the credit
guard. Selectors used, and their fragility:

- `page.get_by_label("เมนูเพิ่มสื่อ")` — stable aria-label, unlikely to break.
- `page.get_by_text("อัปโหลด" / "เปลี่ยนชื่อ" / "เพิ่มไปยังพรอมต์", exact=False)` —
  Thai menu-item text inside `[role="menuitem"]`. Brittle if Google changes the
  Thai copy; the English UI (untested) would need different strings.
- `input.editable-text-input` for project rename — worked, but **`Control+A` does
  NOT select-all on this Mac Chrome** (it moves the caret to line-start, an emacs
  binding); the script uses `Meta+A`. This cost one wasted rename in the probe
  (`ตาชั่งของเสี่ยก.ย. 25 - 17:15` before the fix) — noted below as a skill field
  note.
- `img[alt="รูปภาพองค์ประกอบ"]` to verify a chip bound — matches the
  google-flow-ops skill's own documented pattern for a real reference chip.

Browser session cleanup: closed all 13 stray `flow.google.com` tabs this task's
recon left open, kept one at the project URL for review. Never touched the
`chatgpt.com` tab (belongs to Part A / "leave it running").

## Chrome / tab state left behind

- ChatGPT automation Chrome (9223): still running, per instruction. One
  `chatgpt.com` tab open (the runner's own, untouched).
- One `flow.google.com` tab open at the project URL, muted, showing the
  uploaded `pa__face` Element ready for the CEO to look at.
- No `tab_registry.py claim` was made: all browser driving in this task was via
  standalone Playwright-over-CDP scripts (same pattern as `tools/flow_shoot.py`
  and `tools/chatgpt_images.py`), not the `mcp__claude-in-chrome__*` MCP tools,
  so the MCP tab-ownership registry doesn't apply here.

## Files Changed

- `tools/flow_upload_element.py` — new. The Part B replay script.
- `docs/reports/taachang-characters/REPORT.md` — this file.

No repo images. `/Users/gob/MoonieXHQ/Work/task-c2723478/out/{plates,sheets}/`
holds all 18 PNGs and 7 contact sheets, outside the repo.

## Commits

- (see git log — tools/flow_upload_element.py + this report)

## Tests

- ran: `tools/chatgpt_images.py` (the runner itself, not a unit test) — 18/18
  images, exit 0
- ran: `tools/flow_upload_element.py` against the real `pa__face.png` — exit 0
- no pytest suite exists for either tool; not modified beyond the new file

## Issues / Blockers

- none — both parts completed within budget with no re-edits and no priced
  control ever clicked.
- Disk: `df -h /` read 5.7 GB free at spawn (brief's floor was 5 GB); the 18
  plates (~36 MB total) did not push it under the floor. Re-checked after: still
  clear.

## Notes for Reviewer

- The 17 remaining plates are **not yet in Flow** — only `pa__face` was uploaded,
  as the brief required. Once the CEO approves the contact sheets, the same
  `tools/flow_upload_element.py --project-url <this project> --file <plate> --name
  <handle>` call uploads each remaining one.
- `tools/flow_upload_element.py`'s Method-2/3 code paths are **not implemented**
  (only documented in the docstring) since Method 1 worked on the first live try
  and the brief says stop at the first method that works. If Method 1 ever
  regresses (Google changes the upload flow), Methods 2/3 need to be written from
  scratch against the docstring's description.
- SKILL-OVERRIDE: none. Followed the brief's method order and stop conditions
  exactly.

## Skill learning
- WRONG [google-flow-ops §"What the frame picker will actually show you"] : implies uploading into Flow with no human click is unproven ("Whether an uploaded file then appears in the frame picker is plausible but unverified. Do not plan around disk upload until someone proves it.") · evidence: task-c2723478, `tools/flow_upload_element.py`, live run exit 0 with `ELEMENT_CHIP_BOUND: True` · fix: `page.expect_file_chooser()` around the อัปโหลด click works on the first try — no override, no synthetic drop needed. This unblocks disk-upload planning generally, not just for pa__face.
- MISSING [google-flow-ops §Renaming a Character] : the file documents `input.editable-text-input` for project/character renames but never says `Control+A` fails to select-all on this Mac Chrome (it moves the caret to line-start instead, an emacs binding) — only `Meta+A` (Cmd+A) selects all · evidence: task-c2723478, first rename attempt produced `ตาชั่งของเสี่ยก.ย. 25 - 17:15` instead of `ตาชั่งของเสี่ย`.
- MISSING [google-flow-ops §Anything that must look a specific way needs an Element] : no documented path exists for turning a plain uploaded image into a "Character" category asset — right-click on an uploaded image offers `ทำให้เคลื่อนไหว / เพิ่มไปยังพรอมต์ / ตั้งเป็นรายการโปรด / ดาวน์โหลด / ย้ายไปที่ถังขยะ / เปลี่ยนชื่อ / ตั้งค่าปกโปรเจ็กต์` — no "convert to character" item. The functional equivalent (attachable as a reference chip via "เพิ่มไปยังพรอมต์") works without ever touching the separate generative "สร้างตัวละคร" flow, and is free · evidence: task-c2723478, right-click menu items captured live.
- (none) for everything else — Part A's runner and QC tooling worked exactly as documented in their own docstrings and the brief, nothing to report there.
