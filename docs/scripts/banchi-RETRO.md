# «จุดจบของเจ้าหนี้นอกระบบ» (banchi) — retrospective, 2026-09-23

Shipped: 24:00, 186 shots, Veo 3.1 in Google Flow, posted 2026-09-23. CEO: "ผ่านแล้ว แต่ไม่
Perfect ไว้เรียนรู้ใหม่ในเรื่องต่อไป". Every rule below has its evidence in
`.claude/skills/google-flow-ops/SKILL.md` field notes / sections, dated 2026-09-18..23.

## 1. Characters and faces

| What happened | Rule for next time |
|---|---|
| A face seen in profile, as the SECOND reference (REF_1) in a close-up, lost its plate: ต้น's hair (106 ×2), the father's shirt (149, 150, 188, 189) | The character the shot is about goes first (REF_0); stage both faces 3/4 to camera |
| One full-body still of วิทย์ in uniform gave him the father's older face (149, 151) | Face plate + a separate wardrobe plate with no person in it (`WARDROBE` in the data files). Measured A/B |
| A description-only regenerated character is a different man (uniform arm B) | Always attach the face plate; change clothes in words or with a wardrobe plate |
| Office clothes by words alone worked (188-190) | Words are enough for ordinary clothes; a plate for a uniform or anything specific |
| ต้น wore grandma's nasal cannula when staged ON her bed (65, 169, 171) | Never stage a healthy character on a sickbed; a chair beside it. A negative ("no cannula") loses to the staging |

## 2. Scenes, props, what Flow refuses

| What happened | Rule |
|---|---|
| "No banknote with the King" lost to the Thai-shop context six times | Bind a prop Element (the envelope) — describe where the money IS, not what it is not |
| `NOT["ya"]` (her continuity rule) was used to mean "keep her out" and put her in frame | A continuity rule is not an exclusion (`noya`) |
| "night" appended to a lit-shop description rendered daylight in all 71 shop shots | **Not solved for the shop.** The alley shots (156, 187, 9207) came out genuinely dark — their plate (`@back_alley`) is a night plate. Next story: every location gets a DAY plate and a NIGHT plate, and night is described by its light (bulbs on, black street beyond the shutter), not one word. A/B it at 360p (≈8 credits) before the first night scene |
| Flow silently DELETES: uniform plate + the word "police"; handcuffs on anyone; uniform + police lights (even off frame) | Write around it: describe clothes not the institution; no handcuffs; police lights only in a shot without the officer. 11-arm A/B, section in the skill |
| Real-currency and law-enforcement imagery is where the filter lives | Check a new story's props against this list BEFORE the script is locked |

## 3. Sound and dialogue

| What happened | Rule |
|---|---|
| Lines said twice | Read the transcript (`tools/film_transcript.py`) before diagnosing; keep the speaker description on every line; dialogue early in the prompt |
| Mangled Thai subtitles burned into 3 shots; one re-fired 3× | Pixel-gate scan (`tools/burned_text_scan.py`) after every batch; "to himself / under his breath" invites them; 43 was fixed by 6 s → 8 s (fastest-spoken line in the film) |
| Diagnoses made by ear/guess were wrong three times (139, 122, "speaker hoisting") | Measure first. A detector is calibrated on known hits AND misses before its count is reported (the OCR scan said 14; it was 3) |

## 4. Process and tools — the mistakes that cost time

- Runner bugs found live: substring chip match (`@cop_wit` vs `_uniform_A`), silent shots had no card key, a stale card read as "done", `pull` fetched the OLD take of a re-shot scene, flaky picker clicks — all fixed and merged (93c93ec8 … 65c3fd27).
- The Mac hit 0 GB twice. Output now lives in `~/MoonieXHQ/Work/<task>/` (CEO ruling), `--expect-gb 0.2` on every run, superseded cuts deleted.
- The Element plates existed only on the Mac and were lost in a cleanup. Keep them on Drive too.
- Budget: an approved cap per round (300) and a running total in every report worked.

## 5. The review loop that worked — use it from day one next time

1. Shoot one act → mechanical audit (transcript + caption scan + duration), zero images.
2. One contact sheet per act (3 frames a shot, ~8 shots an image) → look only for faces, clothes, posture, who is in frame.
3. A 540p file per act (8–14 MB) straight into the chat → the CEO passes or marks it; a passed act is locked.
4. Full 1080p cut assembled once, at the end, from already-normalised clips (2 minutes).
5. Unsure about a prompt → A/B at 360p/4 s (4 credits an arm) before 720p.

## 6. Is the audit complete and cheap enough? — honest answer

- **Cheap: yes.** Transcript + caption scan read all 186 shots in ~10 min with no images; contact sheets cost one image per ~8 shots.
- **Complete: not yet.** The CEO still caught four visual defects the audit missed (106 hair, 149/151 wrong face, 171 on the bed). Faces, clothes and posture are only checked by eye, and only on shots someone suspected.
- **Next step (free, local):** a face-match check — embed the plate face and each shot's faces (e.g. InsightFace), flag any shot whose best match to the cast is below a threshold — and a "person lying on a bed" flag. That turns the last eye-only check into a mechanical shortlist.
