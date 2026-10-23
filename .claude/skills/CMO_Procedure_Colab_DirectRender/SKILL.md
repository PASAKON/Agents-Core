---
owner: CMO
audience: [cmo, cto]
created_by: human
origin: mooniex-org
name: CMO_Procedure_Colab_DirectRender
kind: procedure
description: >-
  PROCEDURE — Render AI video clips (not 18+) on Google Colab straight from Contabo, with no studio and no Mac:
  write one take spec (JSON: scenes, refs, size, caps), run ComfyRunpod scripts/colab/run_take.py, check that no
  VM is left, then put the clips in Drive staging with colab_stage.py. Trigger on /CMO_Procedure_Colab_DirectRender,
  "คลิปจีน", "YT: คลิปจีน", "render บน Colab", "Generate คลิปผ่าน Colab", "ใช้โควต้า Colab". Do NOT use it for
  18+ / H3 scenes (those stay in the Mac studio and RunPod) or for Google Flow films (CMO_Workflow_ShortFilm).
---

# Render clips on Colab from Contabo (CEO 2026-10-23)

The CEO tells the story to the CMO, the CMO writes the script, and Colab renders it on the Ultra plan's
compute units (CU). Nothing else is used: no studio, no DeepSeek, no RunPod, and the Mac may be off. His words:
*"ฉันจะใ้ CMO เป็นคนใช้งาน ผ่าน API อย่างเดียวไม่ต้องใช้ตัวคุม"*. First channel: Drive `ALL DRAFT/YT: คลิปจีน/`
(the filing rules are in `CXO_Rules_GDrive_Filing` §YT: คลิปจีน).

**HARD — never 18+ here.** Colab runs on the CEO's own account (pass.gob1). Adult content can cost him the
account, so 18+ scenes stay on the Mac studio's guarded path (memory `project_h3_colab_safe_split`).
**Why hard:** scope. That account carries his whole Google life.

## Where things are (Contabo)

| What | Path |
|---|---|
| Runner | `/opt/MoonieXHQ/Projects/MoonieX/ComfyRunpod/scripts/colab/run_take.py` (docs: that repo's `docs/COLAB.md`) |
| Python | `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` |
| Colab CLI | `/root/.local/bin/colab` (signed in as pass.gob1; never open `~/.config/colab-cli/token.json`) |
| Takes | `ComfyRunpod/out/colab/<take_id>/` (spec, refs, then NN.mp4 + timings.json) |
| Drive staging | `scripts/gdrive-bridge/colab_stage.py` in Agents-Core |

## Steps

1. **Write one take per story or per batch of scenes.** One take = one VM. The weights load once, so every
   extra take pays the setup again (about 3 min). Put the spec and its ref images in
   `out/colab/<take_id>/`; relative paths resolve against the spec's folder.
   ```json
   {"take_id": "ep01-a", "workflow": "r2v", "gpu": "G4", "fallback_gpus": ["H100", "A100"],
    "width": 768, "height": 1344,
    "refs": ["hero.png", "teahouse.png"],
    "scenes": [{"prompt": "<Picture 1> walks into the tea house in <Picture 2> ...", "seed": 1, "seconds": 10}],
    "budget": {"max_minutes": 60, "max_cu": 8}}
   ```
   - **Size is per take.** 9:16 = `width 768, height 1344`. 16:9 = `width 1344, height 768`. Leave both out to use
     the workflow's own.
   - `seconds` or `frames`. Frames sit on the 5 + 17k grid, from 5 to 362 (24 fps, so about 15 s at most).
   - `seed` is required, so a take can be made again. Use at most 9 refs, called `<Picture 1>` … in the prompt.
   - Refs are your own images. Never take a picture from `studio/data`; the runner refuses it.
   - Set `budget`: the guard stops the VM at either cap. About 0.75 CU per 15 s scene at 540p (7 Oct), plus about
     0.45 CU of setup per take (3 min at G4's 8.9 CU/h). Give each take its own cap, never more than the CEO's batch cap.
2. **Dry-run first** (free, touches no VM):
   `cd /opt/MoonieXHQ/Projects/MoonieX/ComfyRunpod && <python> scripts/colab/run_take.py out/colab/<take_id>/spec.json --dry-run`
3. **Run it**, from that folder: `<python> scripts/colab/run_take.py out/colab/<take_id>/spec.json`. A long take
   goes in the background with its output in a file. It prints one `stage=` line per step and ends with
   `teardown: … still_listed 0`.
4. **Check that no VM is left:** `colab usage` must say `Active assignments: 0`. If it does not, run
   `colab sessions` and tell the CTO. Never leave a VM listed.
5. **Stage it on Drive:** `python3 scripts/gdrive-bridge/colab_stage.py <take dir> --clear`, run from Agents-Core.
   It checks every md5 by id and deletes only the local clips that matched.
6. **Sort for the edit:** move the clips you use from staging into `EP<nn> <ชื่อเรื่อง>/All Scene/`, and put the
   finished cut in `Final Draft/` (`CXO_Rules_GDrive_Filing` §YT: คลิปจีน).

## What stops a VM by itself (read in the code, measured live on 2026-10-23)

1. **The runner** stops the VM when the take ends, on an error and on Ctrl-C.
2. **guard.py** is a separate process on Contabo. It stops the VM when:
   - the runner dies;
   - `max_minutes` passes;
   - `max_cu` is reached, judged both by the balance drop and by rate × time.
   It leaves only after two polls in a row list nothing of the take's.
3. **vm_watchdog.py** runs on the VM itself. The VM releases itself after 15 min with no heartbeat, or when it
   is 240 min / 36 CU old.
4. **Colab's own session limit** is the last resort.

The live test was card RUN-20261023-0944-96fe:
- **Render:** one 5 s 9:16 scene. The cold setup took 168 s and the render 57 s, 313 s wall in all.
- **Teardown:** `still_listed 0`.
- **Dead-man check:** a bare G4 got no heartbeat and was gone 29 s after the last beat (the timeout was 180 s).
- **Cost:** the whole card cost 0.73 CU (1070.56 → 1069.83).

## Field notes
