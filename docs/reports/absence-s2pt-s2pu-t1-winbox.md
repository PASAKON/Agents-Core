# S2PT + S2PU take 1 — winbox browser operator report (spawn 2, task-dcaef051)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The Valder Collection No.7")
Chrome device: `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome).

## Blocker from spawn 1 — root cause found and fixed

Spawn 1 (task-d188f5bc) uploaded through the composer's **direct reference-tray
file input** (the one reached straight from the "References" pill / the
`accept="image/*,video/mp4,..."` input embedded in the prompt-box container).
That input creates a `<video>` element bound to a local `blob:` URL that never
progresses past `readyState:0` / `networkState:2` (NETWORK_LOADING) — confirmed
independently in this session across **three readings** (original tab ~45s,
after reload ~10s, fresh tab ~30s), even with the re-encoded low-bitrate previz
(`S2PT-Render.MP4` ~605 kbps, well under the 1.6 Mbps that was the first
suspect). The blob simply never resolves through that input, on this account,
on this page, right now — not a bitrate problem.

**The working path** (per this task's brief, confirmed against
`docs/reports/absence-s2aj-t1-winbox.md` and `.claude/skills/higgsfield-unlimited-gen/SKILL.md`
§"Attaching a VIDEO reference" and §"Video-ref attach on the PROJECT composer"):
click the **"+" icon** left of the composer text box (not the "References"
mode pill) → opens the reference panel (Uploads/Elements/Generations/Liked
tabs) → **Uploads → Videos** sub-tab → its own `<input type=file>` (a *third*
file input on the page, broader `accept` list including `video/*`/`video/webm`)
→ upload there. Verification took ~1–2 minutes (toast "Your upload is being
verified" → real thumbnail in the Uploads grid, sorted "Last created"), matching
the S2AJ report's ~3-minute timing. Clicking the resolved tile fired "Added to
prompt box" directly — no separate hover "Check eligibility" pill appeared for
this tile (it may only show during an intermediate state this session didn't
catch). Attach verified byte-exact: `fetch(video.currentSrc, {method:'HEAD'})`
returned `content-length: 1518291`, matching the local `S2PT-Render.MP4` size
exactly. The reference-tray `<video>` itself stayed at `readyState:0` even
after successful attach — **that is a red herring, not a failure signal**; the
authoritative check is the "Added to prompt box" toast + byte-match, not the
tiny tray thumbnail's own decode state.

**Corrected guidance for the skill**: video-ref uploads on this composer
should go through the "+" → Uploads panel path, not the composer's own direct
file input. Flagging for the CTO to fold into
`.claude/skills/higgsfield-unlimited-gen/SKILL.md`.

## S2PT · "THE TOUR, TOGETHER" — take 1

- Sheet lint: `python scripts/prompt-lint.py docs/prompts/absence/s2pt-fix2-the-tour-together.txt` → clean (exit 0). `--chips` → EXPECTED 7 unique Element chips.
- Previz: `docs/S2PT-Render.MP4` (1,518,291 bytes, h264, 1280×720, 24fps, 20.000s) attached as Video 1, byte-verified as above.
- Chip binding: **7/7 unique** Element chips bound (`span.text-font-brand` leaf spans starting `@`) — `@project_absence_char_valder`, `@gentleman_e`, `@project_absence_char_guard_private_v2`, `@project_absence_char_guard_valder_two`, `@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`, `@loc_hall_big_e` (13 total mention spans — sheet references some names in both POSITION MAP and REFERENCES sections, matching the S2AJ pattern). **0 `.text-icon-error` chips.** 8 tray thumbnails visible (1 video + 7 elements).
- Text entry: pasted the exact `PASTE FROM HERE`…`PASTE STOPS HERE` block (9,656 bytes, base64-decoded to avoid transcription errors) via synthetic `ClipboardEvent` into the sole visible (non-decoy) contenteditable, followed by `End` → `space` → `Backspace` to force Lexical state sync. Only one visible contenteditable was present (no decoy ambiguity this session).
- Settings immediately before Generate: Seedance 2.5 · References · 16:9 · 720p · 20s · batch **1/4** · High · Sound **On** · window `1920×911` (well above the 1280 mobile-breakpoint floor). Unlimited switch `data-state="on"`. Generate button text (re-read the instant before click): `UNLIMITED / 140 / 0` — struck price then zero, correct.
- Grid check before fire: no "processing/generating/queued" text anywhere; only the two pre-existing `NSFW · Credits refunded` cards from the prior S2R-F take.
- **Fired 2026-09-09 22:21:5x ICT.** Asset count ticked **755 → 756** immediately after click, confirming exactly one job queued.
- Zero cost: Unlimited struck-140→0 the whole session; no priced control was clicked at any point.

**Render wait in progress — will update this file with harvest details (download path, md5, bytes, asset id, ffprobe, frame descriptions) once S2PT lands, then fire S2PU per the brief.**

## S2PU · "ARE YOU FOLLOWING US" — not yet started

Waiting for S2PT to leave the slot (finished or rejected) per the brief's "ONE SLOT" rule before firing.
