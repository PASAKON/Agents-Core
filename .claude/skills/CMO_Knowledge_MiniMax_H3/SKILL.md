---
name: CMO_Knowledge_MiniMax_H3
kind: knowledge
owner: CMO
aka: [CTO_MiniMax_H3]
description: >-
  KNOWLEDGE — Everything measured about generating video with MiniMax H3 through our own ComfyRunpod studio (the Mac,
  reached over the tailnet): adding Elements, queueing shots headless, the pod and its money, reference
  rules that are specific to H3, the audio marker, and what the first real renders showed. Trigger on
  /CMO_Knowledge_MiniMax_H3 and whenever a task says MiniMax, H3, "localhost:4000", ComfyRunpod, the studio queue,
  previz on RunPod, "ยิง H3", "เปิด pod", "คิว H3", or fires h3_fire.py / h3_add_entities.py. Do NOT fire for
  Seedance/Higgsfield (CMO_Knowledge_Seedance2.5_Higgsfield), Google Flow (CMO_Knowledge_Flow_Omni1.1) or Wan 3.0 on
  TopView (CMO_Knowledge_Wan3.0_TopView); prompt-file layout lives in CMO_Standard_Film_PromptFormat.
created_by: agent
author: {role: cto, date: "2026-09-25"}
audience: [cmo, cto, browser_operator, developer]
---

# MiniMax H3 · our ComfyRunpod studio

Only what was measured on H3 lives here. How a prompt file is laid out is `CMO_Standard_Film_PromptFormat`; how a
film is run is `CMO_Knowledge_Film_Production`. Where this skill says nothing, do not assume a Seedance or Flow rule
holds on H3: measure it.

**Why we use it (CEO 2026-09-25):** H3 at 360p is the cheap rehearsal. Shots are crafted here, then the
prompts go to Wan 3.0 on TopView for the real footage (`CMO_Knowledge_Wan3.0_TopView`, conversion checklist).

## 1 · Where it is

- The studio (Next app) runs only on the Mac, project `comfy-runpod-worker` at
  `/Users/gob/MoonieXHQ/Projects/MoonieX/ComfyRunpod`, LOCAL-ONLY on purpose (never give it a remote).
- From Contabo it answers on the tailnet at **`http://100.64.2.37:4100`** (the CEO calls it "localhost:4000").
  Contabo has no ssh route to the Mac; everything goes through the HTTP API.
- Lanes (CEO 2026-09-25, to the Mac CTO: "คุณรับผิดชอบแค่การ Update web ui localhost + API Comfyui runpod minimax
  ... ส่วนงาน หนังสั้น ให้เป็นหน้าที่ของ CTO บน CONTABO"): the Mac CTO who built the studio owns only its UI and the
  H3 API; the films and their prompts belong to the Contabo CTO. The Mac CTO's reply channel is a file in
  `docs/ops/letters/` (it did not read the Contabo mailbox on 2026-09-25).

## 2 · Rules

1. **HARD: the CEO opens and pays for the pod; ask him with the exact $ before any run.** (org rule: `ALL_Rules_Approvals`)
   **Why hard:** money. RunPod bills by the hour; the permission layer also refuses `POST /api/pod/start`
   from an agent as a real-money transaction (2026-09-25).
2. **HARD: never open, print, edit or delete anyone else's Entity, upload or queue item.**
   **Why hard:** scope. CEO: "ห้ามยุ่งหรือดูรูปอื่นๆ ที่แอดไว้นะ อันนั้นงานของคนอื่น". `POST /api/entities` without
   `?return=saved` answers with the WHOLE list, other people's included; discard it unread. Yours are the
   entities in your film's group (`ILAG TopView`); the CEO's sit in `Character 18+ Group`.
3. Your own queue items are yours to add, replace and delete without asking (CEO 2026-09-25); only the pod
   run needs him.
4. **Every reference picture is ONE photograph.** A multi-panel sheet in = a grid video out, for the whole
   clip; no prompt wording prevents it (measured on a live H100, 2026-09-03). Crop single panels from
   design sheets, and remove labels and numbers from the crop.
5. **HARD: no red face and no red ears, on any character, in any shot.** H3 renders a blush as an
   unnatural red patch. Never write blush, flushed, red cheeks, red ears, หน้าแดง or หูแดง in a prompt, a
   story beat or an entity note, not even for embarrassment, heat or arousal; show those through action
   (looks away, bites the lip, rubs the back of the neck). Close every prompt with the negation
   `no blush, no red cheeks, no red ears, even natural skin tone` (H3 follows negations, §5).
   **Why hard:** CEO ruling 2026-09-28: "ห้ามหน้าแดงหูแดงนะ อันนี้เป็น Rules เลย ใน MiniMax H3 ทำหน้าแดงออกมาได้ผิดธรรมชาติมากๆ".

## 3 · Elements (the @handle library)

- Upload: `POST /api/upload` multipart `file=@x.png;type=image/png` → `{"file": "<id>.png"}` (wrong MIME = 415).
- Create: `POST /api/entities?return=saved` `{kind: character|location|prop, name, atId, notes, group, refs:
  [{id, kind: "image", file, label}]}`. `atId` is the `@handle` a prompt types; the server sanitises it and
  makes it unique silently, so check for a collision first (read the atIds into memory, print nothing) and
  verify the returned atId. Pass `group` on every new entity (an unknown group is created). A name already
  taken (case and extra spaces ignored) returns 409 with the clashing entity's id: treat it as "already
  exists, use that id", never retry with a suffix.
- Update: same POST with `id` (fields merge). Delete: `DELETE /api/entities?id=`.
- Every entity write runs under one lock since ComfyRunpod 662d9b8 (2026-09-25), so two creates can no longer
  both pass the duplicate-name check; still send one request at a time.
  [SUPERSEDED 2026-09-25] "The API has no lock": 662d9b8 added it.
- Groups (ComfyRunpod 08cabed, 2026-09-26): `GET /api/groups` (name, description, count, kinds, plus the
  ungrouped) · `POST /api/groups {name, description}` (409 on a duplicate, 400 on the reserved name Ungrouped) ·
  `PATCH /api/groups/<urlencoded name>` `{name?, description?, merge?}` · `DELETE /api/groups/<urlencoded name>`
  ungroups the entities and never deletes one. Change only your own group.
- Tool: `docs/prompts/ilag-topview/h3_add_entities.py` (md5 against Drive, collision check, `?return=saved`,
  the group, a 409 read as "exists").

## 4 · Queueing shots headless

- `POST /api/shots/render` `{name, prompt, resolution: "360p"|"720p"|"1080p" (required), seconds|duration_s
  4-15, aspect, seed?, chain?}` → `{job_id, label, name, refs, tags, position, pod_state, queued_offline}`.
  With the pod off it still queues (`queued_offline: true`); `require_pod: true` restores the old 409.
- 400 means this shot's own input: unknown `@handle`, over the 9-image cap, bad seconds/aspect, or no
  reference at all. Log it and keep queueing the rest.
- `GET /api/shots/render?id=<job_id>` → `{status: pending|running|done|error|skipped, files, download_url}`;
  `download_url` is relative to the base URL.
- **The queue runner stops the pod the moment the queue is empty.** Queue every shot back to back before
  the pod opens; firing one at a time closes the pod after the first clip. It renders up to 2 ahead.
- `GET /api/queue` → `{items: [...]}` (holds other people's prompts: print only your own rows).
  `DELETE /api/queue?id=<id>` removes exactly one item (verified 14 → 13). Delete only your own pending items,
  one at a time, and check the count dropped by exactly that id.
- Tool: `docs/prompts/ilag-topview/h3_fire.py` (`--series`, `--retake`, `--cancel`, `--run-all` waits for a
  ready pod, collects to Drive, confirms the pod is off, stops it past a $3 cap).

## 5 · How H3 reads a prompt

- The studio expands each `@Handle`: the entity's pictures become `<Picture N>`, the entity gets a
  `<Subject N>` identity block, and the `@handle` in the prose is replaced by the entity's name. So the
  entity name should be the fixed name the prompt uses (`THE YOUNG ONE`).
- **At most 9 images per shot** (12 files with video/audio). Slots go in **first-mention order**: the first
  handle named claims them first. More references render slower (reference tokens ride every step).
- `ref_image_size: max` = 2048 px short edge; larger pictures gain nothing.
- `@refs` are conditioning and cannot be combined with an i2v start frame. `chain: true` continues the
  previous item and needs an `@handle` in every link, or that link drops every reference.
- **Audio:** the studio appends a standing block ("wind and room tone…") unless the prompt carries the marker
  `non_diegetic_music: none`. For no background sound, put your own block in the prompt:
  `overall_soundscape: only the sounds the characters themselves make (...); no ambient bed ...` followed by
  `non_diegetic_music: none.`
- H3 reads prompts through Qwen3-VL, which follows negations (MAC CTO, ComfyRunpod `docs/PROMPT-QUALITY.md` §7b).

## 6 · What the first real renders showed (ILAG trailer, 2026-09-25, 360p)

- Output: 640x352, 24 fps, 5-6 s, audio on.
- **Dialogue:** 9 dialogue clips transcribed, every line spoken as written, no stage direction spoken, with
  manner tags of 5 words or fewer. One name drifted ("Chief" → "Chieftain").
- **An aerial shot with full-body character references drifted into a medium shot of the characters
  standing** (N1 take 1). Fix that was queued: keep character references out of wide location shots and
  describe tiny riders in words.
- **One character drawn twice** (O4 take 2: THE STRONG ONE on the mount and again on the dock) when one beat
  moved him from the dock onto the mount with the dock crowd in frame and 9 references. Take 3 put the riders
  on the mount from the first frame with 7 references and no push-off (e1b6dd16); its result was not written down.
- Not done when asked: a tilt-up (M6 take 1); a mountain too dark to read (M11); a single-step beat that
  switched framing mid-shot (M6, N1). Characters turned to the camera unless the prompt said where they face.
- Costs: 13 shots ≈ $0.71 (pod stop reading); 9 shots ≈ 11 min pod ≈ $0.60 (estimate from runtime).

## 7 · Money and the pod

- H100 80GB $3.29/h in the studio's table; fallback H200 $4.59/h. Stock in AP-JP-1 comes and goes within
  minutes and runs short on Friday into the weekend (CEO 2026-09-25).
- Boot about 7 min; 360p: a 12 s clip about 51 s warm, about 155 s for the first after boot.
- `GET /api/pod/status` → `{state, gpu, costSoFar, hourlyRate, stockStatus, retry}` (read-only).

## 8 · Deeper references (memory)

`reference_h3_studio_api_tailnet`, `reference_h3_grid_ref_fails`, `reference_h3_studio_architecture`
(Turbo LoRA, render poll fix, orphan recovery from ComfyUI history, identity drift and LoRA),
`reference_h3_max_config`, `reference_h3_pod_boot`.

## Field notes
- 2026-09-25 [MISSING] §3: coming in ComfyRunpod task-78c03f7b (not live when written): an entity `group` field (this film's entities go in group `ILAG TopView`; pass `"group"` on every new entity; rename via `POST /api/entities/groups {"action":"rename",...}`) and duplicate names refused with 409 plus the clashing id (treat as "already exists, use that id", never retry with a suffix); ownership per the CEO: the Mac CTO owns only the Studio UI + H3 API, the film and its prompts belong to the Contabo CTO · evidence: docs/ops/letters/2026-09-25-cto-6bfdc084-to-cto-e1e3d3ef-film-is-yours-entity-groups.md → §3 group + 409, §1 lanes (CEO words in the letter), merged with the 662d9b8 note (live 3a2787c7) · status: promoted
- 2026-09-25 [WRONG] §3 'The API has no lock' — since ComfyRunpod 662d9b8 (task-78c03f7b, live on :4100 2026-09-25 ~20:40 ICT), every entity writer (`POST`/`DELETE /api/entities`, `/api/image/adopt`, `/api/entities/groups`) runs under `withEntitiesLock`, so two concurrent creates can no longer both pass the duplicate-name check. The field note above is now LIVE: `group` field + 409 on a duplicate name. All 29 ILAG entities are already in `ILAG TopView`, and the CEO's 12 are in `Character 18+ Group` (touch only your group). One request at a time is still the polite rule. · evidence: merge 662d9b8, `POST /api/entities/groups` assign → updated 29 + 12, missing [] → §3 (old line kept [SUPERSEDED 2026-09-25]), §2 rule 2 groups; merged with the note above · status: promoted
- 2026-09-26 [MISSING] §3 — groups are first-class since ComfyRunpod 08cabed (task-b215ec3b): `GET /api/groups` (name, description, count, kinds, plus ungrouped), `POST /api/groups {name, description}` (409 on a duplicate, 400 on the reserved name Ungrouped), and `PATCH /api/groups/<urlencoded>` {name?, description?, merge?}. `DELETE /api/groups/<urlencoded>` ungroups the entities and never deletes one. `Character%2018%2B%20Group` is the CEO's; touch only your own. Assigning an entity to an unknown group creates it · evidence: live counts ILAG TopView 30, Character 18+ Group 12 → §3 Groups · status: promoted
- 2026-09-25 [MISSING] §6 — H3 drew THE STRONG ONE twice in O4 (one on the mount, one on the dock holding the pole) when the beat said he pushes off the dock with the pole and the dock crowd was in frame with 9 references; fix queued: riders on the mount from frame one, a negative for a second copy, 7 references · evidence: docs/prompts/ilag-topview/o04-the-farewell.txt take 2 vs take 3, e1b6dd16 → §6 (take 3's result not recorded) · status: promoted
- 2026-09-26 [MISSING] studio /images (Venice) — every Venice edit model caps its reference images: `model_spec.constraints.maxInputImages` from `GET /models?type=inpaint` (6 on seedream-v4/v5, nano-banana, gpt-image; ABSENT on qwen-edit-uncensored, which enforced 3). The integration (7be6287) was written from docs with no multi-image probe and sent up to 6 → every multi-ref run 400'd. Fixed ae60397: refs up to the cap go single, the overflow becomes one `compositeSheet()`; default cap 3 when absent. Uncensored edit models with 6: seedream-v4-edit $0.05, seedream-v5-lite/pro-edit (anonymized, not private) · evidence: ComfyRunpod ae60397, mock-Venice test 6/6, CEO report 2026-09-26 — rejected: not H3 (this skill holds only what was measured on H3), and the studio handles the cap itself since ComfyRunpod ae60397, so there is no agent action · status: rejected
- 2026-09-26 [MISSING] studio /images (Venice) — Venice's output moderation returns `422 Your prompt violates the content policy` AFTER generating and still CHARGES the full price ($0.31 → $0.27 for one blocked qwen-edit-uncensored run with 5 refs → sheet). A retry loop on Venice burns money; CEO moved 18+ reference edits to Runware (`alibaba:qwen-image-edit@2511`, 1-3 refs, ~$0.0063, `safety.checkContent:false`, adults line appended inside `runwareImage()`) · evidence: dev4100.log `[venice] … 422`, rate_limits balance, ComfyRunpod 516bb62 (task-7affa61d) · status: pending
- 2026-09-28 [MISSING] studio Scene Generator drafts — `POST /api/scenes/draft {"data": "<DraftPayload JSON string>"}` keeps only the last 5 (`MAX_SCENE_DRAFTS`); a 6th evicts the oldest, and `/scenes` restores ONLY the latest. So a headless draft hides the CEO's current work behind it, and every autosave (2.5 s debounce) after he opens it pushes one more of his out. Before posting: count drafts (ids + savedAt only, never `data`), copy the sealed `studio/data/scene_drafts.json` aside, and tell the CEO which of his drafts drops. DraftPayload = `{presetId, model, batchTitle, characters, focus, setting, story, sceneCount, batchSeconds, batchQuality, aspect, cards:[{originalIndex,title,prompt,include,seconds,quality}], mode:"fixed"|"auto", plan, planLines, planEstimate, planCostUsd, jobId}` · evidence: CMO test draft gdilnpa9, evicted CEO autosave 7tc9datx · status: pending
- 2026-09-28 [MISSING] §4 — a whole scene batch queues in one call: `POST /api/scenes/enqueue {batchTitle, aspect, cards:[{originalIndex, title, prompt, include, linkAbove, seconds, quality}]}`; `linkAbove` false on the first card and true on the rest (it chains each card to the one above); one bad card refuses the whole batch; it works with the pod off; the reply is `queued[]` (each with `chainFromId`) plus `warnings` · evidence: CMO gym batch y40gziiu → mflabe5k → o0ftknb3, 2026-09-28 · status: pending
- 2026-09-28 [MISSING] §4 — a queued item's quality cannot be changed: `PATCH /api/queue` only resets an item for retry. To change 540p to 720p, `DELETE /api/queue?id=` each of your own items (it unchains dependents) and enqueue the batch again · evidence: CMO gym batch re-queued at 720p, 2026-09-28 · status: pending
- 2026-09-28 [MISSING] §7 — GPU time per 15 s clip (362 frames) on H100 at $3.29/h, from `studio/data/render_stats.json` (132 renders): 360p median 129 s ≈ $0.12 · 540p 263 s ≈ $0.24 · 720p (r2v_max) 1,033 s ≈ $0.94 (range $0.80–1.23); 720p costs 8× 360p; boot ≈ $0.38 per pod session on top. Quote these numbers, not a guess (my guess of ~$1.10 for three 720p clips was wrong by 2.5×) · evidence: Wikis research/2026-09-28-video-gen-api-price-vs-h3-selfhost.md (37d5360) · status: pending
- 2026-09-28 [MISSING] §3 — reference pictures without an upload: `/api/image` with provider ninjachat, model seedream, is text-to-image at $0.04 per image; every Runware route needs input images, so it cannot start from nothing. Read from the route code, not yet fired; NinjaChat refuses 18+ prompts (memory project_h3_image_providers) · evidence: CMO BL session 2026-09-28 · status: pending
- 2026-09-28 [WRONG] §7 my note above ('720p (r2v_max) 1,033 s ≈ $0.94') — a batch queued at `quality: 720p` rendered as mode `r2v_720`, not r2v_max: 572 / 444 / 446 s = $1.34 for 3 clips (≈ $0.41–0.52 each). One batch only (n=3); quote 720p as $0.45–0.95 per clip and name the mode until more r2v_720 rows land · evidence: render_stats.json last 3 rows, queue y40gziiu/mflabe5k/o0ftknb3 files top_00238–240.mp4 · status: pending
- 2026-09-28 [MISSING] §5 — to check that an `@handle` resolved, count the queue item's `savedRefs` against the entities' ref counts (FRIST 4 + USA_MEN 2 = 6 on every shot). Do not grep the stored `prompt`: the studio has already replaced `@USA_MEN` with the name `USA_MEN`, so the tag is absent even when it worked · evidence: queue y40gziiu…m77wmytw, CEO question "@USA_MAN หรือ USA_MEN" · status: pending
- 2026-09-28 [WRONG] §2 rule 2 was read too narrowly. CEO ruling: never look at entity pictures, including the characters named for the scene, and never describe them anywhere. That covers the API, files under `studio/data/uploads/` on disk, frames grabbed from renders, and other entities' notes. Debug by counts only (`savedRefs` against the ref count, the compiled `subject_definitions`); if a likeness looks wrong, say so and let the CEO look · evidence: CEO 2026-09-28 · status: pending
- 2026-09-28 [MISSING] §2 rule 5 — no red face or red ears on H3: the CEO ruled it a HARD rule after H3 kept rendering blushes as an unnatural red patch; blush words stay out of prompts, story beats and entity notes, embarrassment is shown by action, and every prompt closes with `no blush, no red cheeks, no red ears, even natural skin tone` · evidence: CEO ruling 2026-09-28 (CMO session, adult POV script), rule commit 14c6e429 · status: promoted
- 2026-09-28 [MISSING] §2 rule 5 — ComfyRunpod `docs/PROMPT-QUALITY.md` §2a and the §4 template ask for "faint freckles" and "natural redness across the cheeks nose and knuckles"; pasted as written they break rule 5 and the CEO's no-freckles casting. Take the pores and matte-skin tokens, drop those two, and write "one clear, even tone across the face, ears, neck and body" instead · evidence: PROMPT-QUALITY.md lines 120-121 and 189-190; CMO draft ip3r2r6b · status: pending
- 2026-09-28 [MISSING] §2 — a character stated as 19 years old (CEO order) contradicts the house negative `teen` (19 is a teen in English), and a negative that forbids what the body asks for is a defect (CTO_Film_PromptFormat rule 8). Draft ip3r2r6b dropped `teen` and kept `no child, no minor, no underage, no schoolboy, no school uniform, no childlike face or body`, with "19-year-old adult" in the body; not rendered yet · evidence: CMO draft ip3r2r6b, 2026-09-28 · status: pending
- 2026-09-28 [MISSING] §4 — `POST /api/scenes/enqueue` wants a **1-based** `originalIndex` (0 → 400 "each card needs a 1-based originalIndex") and `quality` from 360p/540p/720p/1080p only (a CEO "500p" means 540p). It fills `{ }` blocks itself: the filled card keeps `promptTemplate`, the others do not. Verify without reading prompts: `savedRefs` count, `promptTemplate` present, no bare `{ }` left in `prompt` · evidence: studio/src/app/api/scenes/enqueue/route.ts:34-43; CMO queue ew9u1rxx/huo22nyq/700ccjrf savedRefs 2/2/2 · status: pending
