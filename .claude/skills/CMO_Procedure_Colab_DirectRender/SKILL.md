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

- 2026-10-25 [MISSING] §Spec — Use studio mode (`studio:true`, `h3_model:studio_bf16`, quality 1080p, G4 → H100, 5 s scenes, ≤5 refs, 1-based `index`, `chain.from` = the previous scene's index). `"workflow":"r2v"` gives the soft 1-pass draft · evidence: ep01-a1-pilot vs ep01-a1s-hallA2 · status: pending
- 2026-10-25 [MISSING] §Preflight — NudeNet must be installed in the runner venv. Without it `scan_failed` deletes a clip that was already paid for. Test with `scan_frames.py --clip <old clip>` first · evidence: ep01-s04-studio · status: pending
- 2026-10-25 [MISSING] §Cost — A 5 s scene on G4 costs ~0.44 CU and takes ~3 min wall, plus ~0.8 CU / ~5 min setup per take. Measured: hallB 29 scenes 12.86 CU, flash 33 scenes 14.06 CU · evidence: take_*/progress.json · status: pending
- 2026-10-25 [MISSING] §Scan — NudeNet scores fully-clothed robed crowds and red lantern rooms 0.26–0.74, so ~40–50% of scenes are quarantined. Since PR #33 the take continues; every quarantined clip is checked by eye at review · evidence: arc1_quarantine_sheet2.jpg · status: pending
- 2026-10-25 [WRONG] §Prompt — A builder that attaches only the refs a prompt cites as `<Picture N>` drops the hero when the prompt says "the boy". H3 then invents a child, and the location plate is lost, giving a grey studio background. Always attach the hero + location plate, write "young man", and add "adult young man of 18, never a child" · evidence: ep01 QC sheet, re-shoot take ep01-a1s-fix1 (19 scenes) · status: pending
- 2026-10-25 [WRONG] §Prompt — The negation tail "no red cheeks, no red ears" still let red cheeks through on emotional close-ups (S09a, S62). Use "no flushed or pink face; pale neutral skin" and check close-ups by eye · evidence: qc1_sheet, ep01-a1s-fix1 · status: pending
- 2026-10-25 [MISSING] §Chain — A continuation clip includes its 22 overlap frames (SSIM 0.993 against the tail of the previous clip). Trim `start_frame=22` and 0.9167 s of audio in the edit · evidence: cut/full.py · status: pending
- 2026-10-25 [MISSING] §Retry — "Session '…' not found" can come back at upload with 0 CU spent. Retry on it the same as on "failed vm" · evidence: take_hallB, take_flash run.log · status: pending
- 2026-10-25 [MISSING] §Plates — ChatGPT on winbox:9224 behind a Cloudflare page shows up as attach timeouts and then `signed_out`. Probe the tab title first. Also, run_take refuses refs that are symlinks pointing outside `uploads_dir` · evidence: rq-efc75fe6, arc23 dry-run · status: pending
- 2026-10-25 [MISSING] §prompt — an eye macro gives red cheeks / red lower lids even with the skin negation: 4 of 4 tries (B11a ×2, B55a, C58a). "Framed from the eyebrows to just below the eyes" passed once (C58a fix3) and once failed (B11a fix2); a mask over nose+cheeks still showed a red ear at the frame edge (cropped 1.15× for free). Safest: stage the beat without a face (B11a fix4: the glowing abacus at the belt, passed). Cropping an eye macro does not help, the red sits on the lower lid · evidence: takes fix2/fix3/fix4, ep01 arc2/arc3 · status: pending
- 2026-10-25 [MISSING] §QC — red cheeks can appear only in the clip's tail (C34a turned red from frame ~80 of 124); a free fix is to keep the clean head frames and stretch them (setpts 1.77, atempo 0.56) into a patch folder that the cut's OVERRIDE checks first · evidence: renders/patch3/C34a · status: pending
- 2026-10-25 [COSTLY] §queue — a waiter `while pgrep -f queue23.sh` matched its own command line and never ended; the next take sat idle ~1 h. Use a bracket pattern: `pgrep -f "[q]ueue23.sh"` · evidence: task bm4n1f9sg · status: pending
- 2026-10-27 [MISSING] §What stops a VM by itself — a batch whose stop counts take caps must also reserve each attempt's overshoot (30 s poll + balance lag + teardown, about 0.4 CU on G4), or `--max-credits` is a target the tail passes: EP02's caps summed 165.2 under a 170 stop and the worst case came to about 173. Reserve budget + 0.5 per attempt and size the flag from that sum (175). Every GPU a take may land on needs a measured CU rate, so an unmeasured fallback (all 19 EP02 specs carried `fallback_gpus: ['H100']`) leaves both the bound and the checkpoint unproven · evidence: PR #476 review (cf874a50), session cmo-fresh · status: pending
- 2026-10-27 [MISSING] §Steps — a Run card runs for 6 h at most (21600 s), and a batch's VM time is its CU over the GPU's rate (G4 about 8.9 CU/h), so EP02's 132 CU (about 15 h) cannot fit one card. Split the takes into job files whose max_cu sum fits 5 h (44 CU on G4), one card each, raised one at a time: a timeout or cancel SIGKILLs only colab_batch, while run_take and the guard finish the current take, so the next card waits for that take's verified shutdown · evidence: CTO answer on PR #476 (merged 89514c5a, 22:06Z), session cmo-fresh · status: pending
