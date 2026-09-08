# S2S-B — A Hundred Million, Reverse Angle — take 3

Task: task-b80a20a9. Sheet: `docs/prompts/absence/s2s-b-fix1-a-hundred-million-reverse.txt`.

## Fire

Pipelined behind S2S (task-20f5c644), which held the single Unlimited slot at task start.
Composer built completely first (Video tab, Seedance 2.5, 16:9, 720p, 20s via the ARIA
duration slider — `ArrowRight` x15 from a 5s default, batch 1/4, High, Sound On), Unlimited
toggled ON last and zoom-verified `UNLIMITED · ~~140~~ · 0` on the real pixels (not a JS
scrape — this composer's Generate button has a known stale-duplicate-element decoy).

Prompt entered via sha256-verified synthetic `ClipboardEvent` paste: paste-block sha256
`00ee18ec7fec2fd1f64869892cd1926ffa6f4c710ff904066a9c088cd7c6ad54`, 11962 bytes, computed in
Bash from the sheet, base64-chunked, reassembled and hash-compared in the page before
dispatch — match confirmed before touching the composer. Dispatched into the real (visible)
contenteditable node, decoy filtered by `getComputedStyle(el).visibility`.

13/13 unique Element chips bound (0 red/unresolved):
`@gentleman_e`, `@project_absence_char_guard_private_v2`, `@project_absence_char_valder`,
`@project_absence_char_woman_c`, `@char_registrar`, `@project_absence_char_visitor_a`,
`@project_absence_char_visitor_b`, `@project_absence_char_woman`,
`@project_absence_char_grandmother`, `@loc_hall_big_e`,
`@project_absence_char_guard_valder_two`, `@project_absence_char_student_c`,
`@project_absence_prop_cart_a_painted`. No previz (`@Video 1`) was attached to this sheet —
the paste block only describes what a video reference would carry, it does not mention one.

Two refusal toasts ("1 unlimited generation at a time") at ~20:52 and ~20:55 ICT while S2S
still held the slot — confirmed each time via `tab_registry.py list`, cost nothing. Third
click at **20:56:59 ICT** returned "Generation started" + asset count 727→728 (+1 exactly).

## The wait

Chrome was minimized by the CEO (Safari frontmost) for most of the ~113-minute render.
Per the CTO's live direction, polling continued via `javascript_tool` only
(`document.visibilityState`, asset-count text scrape) — no screenshots, no resize, no new
tabs — until the card landed. Identification, download, md5 check and frame extraction were
all done with the tab still `hidden`; only the final review-frame inspection needed the
downloaded file on disk, not the live page.

One background-sleep attempt was killed by the harness for low memory partway through
(matches the known "background sleeps get killed" trap) — recovered by returning to
foreground bounded ~90s polling.

One CDP tab-target glitch (`Tab X is not in Claude's tab group`) self-resolved via a fresh
`tabs_context_mcp` read; one apparent "0x0 window" turned out to be the same minimization
event, confirmed read-only via `osascript` (OS-level window bounds were fine at 1024×793 —
the 0×0 reading was the tab's own `hidden` layout state, not a broken window). One `[role=dialog]`
mix-up after an extension reconnect (Info-tab click landed on a different asset) was caught
by re-verifying the prompt text before trusting anything, and fixed by navigating directly to
the confirmed-correct `?preview=<uuid>` URL.

## Landing

Asset id `ad847559-da50-4133-ae9a-5a482a52e1c1`. Prompt text in the Asset-details modal
matched the sheet's paste block word-for-word (spot-checked opening + position map). No
NSFW/rejection flag. Downloaded via the modal's Download button (JS-dispatched click, no
viewport needed): `hf_20260908_135641_ad847559-da50-4133-ae9a-5a482a52e1c1.mp4`,
20,910,186 bytes. md5 `f330cc82eadaf30aab19b2d4d33a7ba7` — checked against every other mp4
already in `~/Downloads`, no collision (rules out a wrong-card mixup). `ffprobe`:
1280×720, 20.04s video, 19.97s audio — matches spec exactly (720p / 20s).

## Review

Frames pulled at 0.1, 0.5, 1, 3, 5, 7, 10, 13, 15, 16, 18, 19s plus a 0.2s sweep across the
whole clip for the cut check.

**1 — WE ARE BEHIND HER, face never seen: PASS.** Every sampled frame (0.1s through 19s)
shows only the back of her head / grey knit headscarf. No profile, no reflection, no cut to
her front.

**2 — THE CHAIR GOES AWAY FROM US: PASS.** Confirmed by direction of travel across the
frame sequence — she recedes from the lens, never approaches it.

**5 — THE DISTANCE HOLDS: PASS, with the mechanism worth recording.** A fixed-pixel-crop
comparison across 9 timestamps (0.5–19s) shows the **far group's apparent size and position
are visually identical in every panel** — they never get bigger, never get closer, the
camera never moves. What does change dramatically is how close *she* starts: at 0.5–5s she
fills the frame (the sheet's own "close to the lens, near foreground"), and by 16–19s the
chair has receded to a more normal framing. That recession is the scripted "[7s] the chair
starts moving... away from the camera" beat — not the group closing the gap. This is the
exact failure mode that sank S2S take 2 (fired without previz, distance collapsed); this take
avoided it despite also firing without a previz reference.

**3 — THE MASS TURN AT 3s: UNVERIFIED.** The group already reads as loosely facing
forward/toward camera even at 0.1s, so a hard synchronized snap-turn distinct from their
resting pose can't be confirmed from still frames alone. Not called a fail — just not
confirmable this way.

**4 — THE TWO WHO LEAVE walk past without looking down:** consistent with the frames
sampled, though both passes are heavily motion-blurred this close to the lens (matches the
cut-sweep's two high-motion clusters below) — no slowdown or glance-down visible in the
frames either side of each pass.

**6 — ONE line, hers, close to the mic:** present in the audio track (19.97s audio stream,
matches the "one line only" spec); not independently transcribed.

**7 — THIRTEEN people, no nurse: PASS.** Full headcount across the wide frames: Dupe, art
student, Carrington, bodyguard, two navy guards, Valder, woman in green, registrar, man in
maroon, woman in fur, woman in cobalt, plus the grandmother in the near foreground = 13,
each appearing once. No nurse, no attendant, no fourteenth figure.

**NEW — grey knit headscarf/cardigan, no purple, registrar cream-white: PASS.** Confirmed
across every sampled frame — grey wool head to shoulders, no sunglasses on her, no purple
anywhere. The registrar's suit reads cream in every frame he's visible.

**Cuts (0.2s sweep, whole clip): clean.** Median frame-to-frame step 0.91 (greyscale
mean-abs-diff on 160×90 downsamples). Two elevated clusters, both broad multi-frame regions
rather than single-frame spikes: ~15.2–17.2s (peak 11.6× at 16.6s) and ~18.4–19.8s (peak
6.3× at 18.8s) — these align exactly with the art-student (scripted 13s) and fur-woman
(scripted 16s) walk-past-camera beats, i.e. real close-up motion, not a hidden edit. No
spike exceeded the >15× single-frame cut threshold. ONE CONTINUOUS SHOT holds.

**FLAG — position-map deviation (non-blocking).** The sheet's position map puts both navy
guards together on Valder's left (numbers 5–6) with the registrar to the right of the woman
in green (number 9, after number 8). The render instead placed the **registrar directly to
the right of Valder**, and the **second navy guard further right, past the registrar** —
guard #2 and the registrar are effectively swapped in the row order. Everyone is present
exactly once, correctly costumed (navy guards in their uniforms, registrar in cream with
ledger); this is an ordering deviation, not a missing/duplicate character. Reported to the
CTO for a judgment call; the CTO's own explicit gate for this take was items 1 and 5 only,
both of which passed, so the take was filed per that instruction.

## Filing

Filed to `All Scene/Fix-2/` (per the CEO's 2026-09-08 Fix-2 ruling) as `S2S-B-Fix1.MP4`:
https://drive.google.com/file/d/1Z7e2h_KJup7ZR4FhgPdDv7ah_XD8yrMK/view — uploaded via
`scripts/gdrive-bridge/upload_fix1.py` (logs.txt line appended automatically).

## Money

Unlimited video only, $0 confirmed at the moment of the click (`UNLIMITED · ~~140~~ · 0`,
zoomed pixels). No other spend this task.
