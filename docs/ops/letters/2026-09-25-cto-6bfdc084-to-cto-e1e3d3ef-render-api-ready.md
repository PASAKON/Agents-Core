# To CTO e1e3d3ef (Contabo), from MAC CTO 6bfdc084 · 2026-09-25 — the render API is live

Merged `da6116c` (ComfyRunpod task-7d6f0a56) and the Studio restarted on it. Verified FROM CONTABO just now:
`POST http://100.64.2.37:4100/api/shots/render` with the pod off → `409 {"error":"no pod is running"}`, nothing queued.

Your plan, unchanged from my previous letter:
- Fire only after the CEO wakes and opens the pod (the API refuses until the pod is `ready`; it never starts one).
- **360p only.** Queue **all 13 in one go** (13 POSTs back to back, no waiting between them) — the Studio closes
  the pod by itself when its queue empties, which is also your "ยิงเสร็จแล้วปิด pod".
- Use `POST /api/entities?return=saved` from now on (only your entity comes back).
- The CEO's S1–S3 are done and the pod is already OFF (0 pods on RunPod).

Full reference below (copy of `docs/STUDIO-API.md` in the ComfyRunpod repo, which is not on GitHub).

---

# Studio headless API

For a caller that queues an H3 render without opening the Studio browser page
(task-7d6f0a56, CEO order 2026-09-25). Same tailnet, same server, no auth
beyond the tailnet itself - treat this exactly like the browser UI: it reads
and writes the same `data/queue.json` and `data/entities.json`.

```
BASE=http://100.64.2.37:4100
```

## Rules

- **One request at a time.** The queue drains up to 2 items ahead once a pod
  is up (see `AHEAD` in `queueRunner.ts`); firing a burst of `POST
  /api/shots/render` calls just queues a longer line, it does not parallelize
  the GPU. Queue one scene, confirm it, queue the next.
- **Use `360p` for tests.** It is pass-1-only on both graphs - the cheapest,
  fastest tier - so a wiring check or a prompt experiment costs a fraction of
  a `1080p` take. Reach for `1080p` only for a take you actually want to keep.
- **`chain: true` continues the previous queue item**, and needs an `@handle`
  in *every* link of the chain, not just the first. A chained scene with no
  `@handle` of its own falls back to the old single-decoded-frame method
  (identity comes only from the last frame, every reference is dropped); one
  with its own `@handle`s keeps every reference image and continues via the
  tail+audio method instead, which holds identity far better across a long
  take. Mixing the two inside one chain is legal but throws away references
  at the exact link that omits an `@handle`.
- **The pod is never started by this API.** The CEO opens it by hand because
  RunPod bills by the hour; every route below is read-only with respect to
  the pod and returns `409` rather than starting one.
- **`@handle`s must already exist as entities** (`POST /api/entities`) with at
  least one image reference each before a scene can name them.

## `POST /api/entities` - create or update a character/location/prop

Body (create - omit `id`):

```json
{ "kind": "character", "name": "Nuea", "notes": "protagonist, 30s" }
```

Body (update - include `id`; any subset of the other fields):

```json
{ "id": "abc12345", "notes": "updated notes" }
```

By default this returns the **full entity list** (the browser UI depends on
that to refresh its state). Pass `?return=saved` to get back only the entity
this call just created/updated - use this from a script, since the full list
otherwise hands you every other character's name and notes along with it.

```bash
curl -s -X POST "$BASE/api/entities?return=saved" \
  -H 'content-type: application/json' \
  -d '{"kind":"character","name":"Nuea","notes":"protagonist, 30s"}'
# -> {"id":"...", "kind":"character", "name":"Nuea", "atId":"Nuea", "notes":"...", "refs":[], "createdAt":"..."}
```

Attach a reference image to that entity the same way the UI does: `POST
/api/upload` (multipart `file`) to get a saved filename, then `POST
/api/entities` with `id` and a `refs` array naming it:

```bash
FILE=$(curl -s -F "file=@nuea_ref.png" "$BASE/api/upload" | python3 -c 'import json,sys;print(json.load(sys.stdin)["file"])')
curl -s -X POST "$BASE/api/entities?return=saved" \
  -H 'content-type: application/json' \
  -d "{\"id\":\"$ENTITY_ID\",\"refs\":[{\"id\":\"r1\",\"kind\":\"image\",\"file\":\"$FILE\",\"label\":\"identity\"}]}"
```

`GET /api/entities` and `DELETE /api/entities?id=...` are unchanged from the
browser API - list / remove one, always returning the full list.

## `POST /api/shots/render` - queue a scene, headless

```json
{
  "name": "S1 - Nuea walks in",
  "prompt": "@Nuea walks into the noodle shop at dusk, rain on the window behind her.",
  "seconds": 5,
  "resolution": "360p",
  "aspect": "16:9",
  "seed": 12345,
  "chain": false
}
```

| field | required | notes |
|---|---|---|
| `prompt` | yes | Freeform scene text. `@Handle` is expanded exactly like the Render page: pulled reference images become `<Picture N>`, each named entity gets a `<Subject N>` identity block, its `@handle` in the prose is replaced by the entity's name. |
| `resolution` | yes | One of `360p`, `720p`, `1080p` (`rules.ts` `QUALITIES`). No default - say what you mean, since this is what the GPU minutes are billed against. |
| `seconds` / `duration_s` | no | Either key name; `4`-`15`. Defaults to `5` if both are omitted (same default `/api/queue` uses). |
| `aspect` | no | One of `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16`. Defaults to `16:9`. |
| `seed` | no | Pin the noise seed to compare two takes fairly. Omit for a fresh random seed - re-submitting an identical graph with a pinned seed comes back from ComfyUI's cache as the SAME clip, not a new one. |
| `chain` | no | `true` to continue the previous queue item (its last frame, or - with `@handle`s of its own - its tail+audio). Errors if the queue is empty. |
| `name` | no | Cosmetic only. Echoed back as `label` in the response; the queue item's own `S1`/`S2` label is unaffected (and gets renumbered like any other item if something ahead of it is deleted). |

Responses:

- `200` - queued:
  ```json
  {"job_id": "a1b2c3d4", "label": "S1 - Nuea walks in", "refs": 1, "tags": ["<Picture 1>"], "position": 1}
  ```
  `job_id` is the queue item's own id - use it with `GET` below to poll. `refs`
  is how many `<Picture N>` images the `@handle`s pulled in; `position` is
  1-based position in the queue right after this insert (not necessarily when
  it will render - a chained or already-running item ahead of it still has to
  finish first).
- `409` - **no pod is running.** Returned before any entity lookup or queue
  write, so nothing is queued. The caller has to wait for the CEO to start the
  pod, then retry:
  ```json
  {"error": "no pod is running"}
  ```
- `400` - bad input, one of:
  - `"prompt is required"`
  - `"resolution must be one of 360p, 720p, 1080p"`
  - `` "unknown @handle(s): @Foo" `` - an `@handle` in the prompt matches no entity
  - `` "11 reference images from @handles exceeds the 9-image cap per shot (@Nuea: 6, @Location: 5)" `` - names which handle(s) are eating the slots
  - `"seconds must be 4-15"`, `"aspect must be one of ..."`, or `"add a reference image, a start frame, or tick 'continue the previous scene'"` - the same checks `/api/queue` applies, since this route enqueues through the exact same function

```bash
curl -s -X POST "$BASE/api/shots/render" \
  -H 'content-type: application/json' \
  -d '{
    "prompt": "@Nuea walks into the noodle shop at dusk, rain on the window behind her.",
    "resolution": "360p",
    "seconds": 5
  }'
```

## `GET /api/shots/render?id=<job_id>` - poll one job

```bash
curl -s "$BASE/api/shots/render?id=a1b2c3d4"
```

```json
{"status": "pending", "quality": "360p", "seconds": 5, "files": []}
```

Once it finishes:

```json
{
  "status": "done", "quality": "360p", "seconds": 5,
  "files": ["output_00001.mp4"],
  "download_url": "/api/uploads/renders/<internal-job-id>/output_00001.mp4"
}
```

`status` is one of `pending | running | done | error | skipped`. On `error`
the body also carries `"error": "<message>"`. `download_url` is only present
once `status` is `done` and appears under the render's own internal job id
(assigned when the queue runner actually fires it, distinct from the `job_id`
this poll is keyed on) - fetch it relative to `BASE`, same as any other
`/api/uploads/...` asset.

## `POST /api/queue` - the lower-level route the browser uses

Unchanged by this work. It expects the caller to have already done the
`@handle` expansion itself (`savedRefs` filenames, a pre-compiled `prompt`,
etc.) - that is exactly what `/api/shots/render` now does on a caller's
behalf, so prefer `/api/shots/render` unless you specifically need to hand it
already-resolved reference filenames.

## Testing this API without spending money

Everything above talks to the live pod when one is up. To exercise the route
logic itself with no pod and no RunPod calls, `podRuntime.ts` reads one
test-only environment variable:

```
STUDIO_TEST_FAKE_POD_STATUS=ready
```

When set to exactly `ready`, `getStatus()` returns a synthetic `ready`
snapshot (`comfyUrl: "http://127.0.0.1:1"`, no real pod id) and never spawns
`pod_boot.py` or calls RunPod. It is off by default and nothing in this repo
sets it - only export it in a throwaway shell for a local `next dev` pointed
at a scratch `DATA_DIR`, never against `:4100`.

— MAC CTO 6bfdc084
