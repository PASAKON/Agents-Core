# Brief: add the ILAG TopView trailer's 24 Elements to the H3 studio (Mac, localhost:4000)

Requested by CTO cto-e1e3d3ef (Contabo) for the CEO, 2026-09-25. CEO, verbatim: "Localhost:4000 ส่ง worker เข้าไป
add Character + Location + Prop ไว้ก่อนเลย หรือจะแอดผ่าน Coding ก็ได้ ห้ามยุ่งหรือดูรูปอื่นๆ ที่แอดไว้นะ อันนั้นงาน
ของคนอื่น · แอดเสร็จแล้ว รอฉันตื่นจะเปิด pod ให้ รันเอา footage จริง".

## Where

Project `comfy-runpod-worker` (LOCAL-ONLY, never give it a remote): `/Users/gob/MoonieXHQ/Projects/MoonieX/ComfyRunpod`,
its `studio/` Next app, running at http://localhost:4000. The Entities page is `/`. Per the org's notes the
store is `studio/data/entities.json` (atomic write), uploads go to `studio/data/uploads/`, and an entity has
`kind` (character | location | prop), a pool of `refs` with a purpose `label`, and an `atId` (the `@handle`
a prompt types). Read the studio's own code to find how an entity is created (API route or store function),
and create through that path, never by hand-editing someone else's rows.

## Job

Create **24 new entities**, one per row of `docs/prompts/ilag-topview/h3-entities.json` (Agents-Core, origin/main):
- `atId` exactly as given (`Young`, `Elder`, … so prompts type `@Young`), `kind` as given, `name` as given.
- ONE image ref each: download the Drive file by `drive_file_id` (the Mac's Drive bridge or the Drive REST API),
  check its md5 equals `md5` in the manifest, attach it as the entity's only ref with label `reference`.
- Put `description` into the entity's notes/description field if the studio has one; skip it if not.

## HARD rules

1. **Do not open, view, list, print, download, move, rename, edit or delete any existing entity, ref or upload.**
   They are other people's work (CEO's words above). To check an `atId` is free, compare the strings only,
   print nothing about any other entity, and do not open any other image.
   **Why hard:** scope. The CEO drew this line explicitly.
2. If one of the 24 `atId`s is already taken, STOP for that row and report the collision. Never rename theirs.
   Never pick a different handle yourself: the 13 prompt files already type these exact handles.
   **Why hard:** a silent rename breaks every prompt that uses the handle, and a collision may be someone else's row.
3. **Render nothing, start no pod, spend nothing.** The CEO starts the pod himself when he wakes.
   **Why hard:** money. RunPod bills by the hour.

## Done when

Report (as `docs/reports/h3-studio-ilag-entities-<date>/REPORT.md` in Agents-Core) with:
- the 24 atIds, and for each the new entity id, the ref filename and its md5 (matching the manifest);
- proof that `@Young @Manta @Village` in a test string resolves to three pictures through the studio's own
  `@handle` expansion (`expandAtIds` or the Shots page), with no render fired;
- any row you could not create, and why.

The prompts that use these handles: `docs/prompts/ilag-topview/m01..m13` (P1, 13 main scenes).
