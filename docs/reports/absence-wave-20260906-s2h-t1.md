# S2H-Fix1 "the first two" — take 1 — 2026-09-06

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The Valder Collection No.7)

## Gate (pre-fire)

- `git merge origin/main`: already up to date at `9a4cd08` (>= required `159dba7`). OK.
- Paste-block grep gate on `docs/prompts/absence/s2h-fix1-the-first-two.txt`: `NO WIDER THAN THE RED DOOR` = 1, `FACING THE CAMERA` = 1, banned depth/anchor words = 0. All match required counts.
- `scripts/prompt-lint.py --chips`: EXPECTED 5 Element chips (video ref not counted).
- `scripts/prompt-lint.py --shot S2H-Fix1`: exit 0, no findings.
- `docs/S2H-Render.MP4`: 2,434,783 bytes, present.

## Browser actions

- innerWidth readback: final successful fire happened at **1400×698** (well above 1280 floor). Two earlier attempts hit a real window-collapse bug (innerWidth read 1024, then 129×89 "MOBILE ACCESS COMING SOON" lockup, with `resize_window` reporting success but not changing anything) — recovered each time via close-tab + fresh-tab per the HARD rule ("A window can shrink on its own; resize_window can lie").
- Credits-running-low banner: closed by its own (x), every tab, before touching anything else.
- Six fields at fire: **Seedance 2.5 · 16:9 · 720p · 12s · High · Sound On**. Duration set via ARIA slider (click thumb → `ArrowRight` ×7, 5→12), never typed.
- Price zoom, immediately before click: `UNLIMITED` · struck **84** · **0**. Confirmed by pixel zoom (not DOM scrape — the DOM text query kept returning a stale decoy button reading `GENERATE8045`, matching the known decoy-button warning in the skill).
- Paste method: base64-encoded prompt block → synthetic `ClipboardEvent` paste (`DataTransfer.setData('text/plain', …)`) into the verified real (visible, focused, `contenteditable=true`) editor node → `End` → `space` → `Backspace` tap to force state sync.
- Chip count: **5/5 unique** bound, lime, 0 error chips — `@project_absence_char_visitor_b`, `@project_absence_char_woman`, `@project_absence_char_cleaner_c`, `@project_absence_loc_wall_pov_e`, `@project_absence_prop_cart_a_painted`.
- Previz attached: yes, `docs/S2H-Render.MP4`. Byte check: local file 2,434,783 bytes; attached asset's `fetch(HEAD)` content-length **2,434,783** — exact match, confirmed both before and immediately before the successful Generate click. First attach attempt produced the documented "broken video chip" symptom (black tile, hover shows only expand/× icons, `readyState:0`) — removed and re-attached fresh via Uploads → Videos → sort "Last created", which resolved cleanly (real thumbnail, `readyState` still 0 in JS but `fetch(HEAD)` proved the asset was real and fully served — the stall was a lazy-load/decoy quirk in the composer's own `<video>` element, not a broken upload).
- Fire time / how verified: clicked Generate at composer state above; confirmed via (1) `All assets` count going **675 → 676**, read fresh in a reloaded tab, and (2) a zoomed screenshot of the new top-left card showing an active spinner + "No status" tag immediately after. No screenshot-DOM ambiguity — both signals independent and consistent.
- Two earlier fire attempts in this session did **not** actually fire (asset count stayed 675 both times, confirmed via fresh-tab reload before assuming otherwise) — one where the click landed on the wrong element, one where the tab's CDP screenshot pipe degraded (`Page.captureScreenshot` timing out repeatedly) forcing a stop before Generate was ever clicked. **No unplanned spend occurred in any attempt** — Unlimited was verified $0 in every case, and no card/asset was ever produced from the failed attempts.

## Render

- Fired ~23:20 (2026-09-06, ICT). Higgsfield's own Info panel confirms "Created September 6, 2026 at 11:20 PM".
- Polled per the 20-min-then-5-min cadence (capped ~90s sleep chunks, reload + reread each check — never a single long sleep). First check ~20 min: still Processing. Two more 5-min checks: still Processing. Completed sometime before the next check — found finished, ~40 min total, matching the sheet's stated norm for this shot.
- No NSFW / credits-refunded / sensitive-content flag. No "Rights verification required" banner appeared on this card.
- Info panel confirmed: Model **Seedance 2.5**, Quality **720p**, Bitrate **High**, Size **1280×720**.
- `ffprobe` on the downloaded file: video stream 1280×720, duration 12.041667s; audio stream present, duration 11.968s. Matches spec (12s/720p).

## Review — frames at 0.5s, 3s, 6s, 11s

Frames extracted to `scratchpad/render/frame_{0.5,3,6,11}s.jpg` (session-local, not committed — ephemeral per scratchpad convention; findings recorded below).

0. **THE MARK**: cropped and inspected against the red door in the same frame — roughly **1x the door's width/height**, solid black, thin lines meeting at one point, sits squarely over the door, does not touch or cross any face. Well inside the acceptable range (today's rolls ranged 1x–3x; this is at the clean end, not a "5x monster").
0b. **THE TWO WOMEN FACE THE LENS**: yes, at all four checked timestamps both women face the camera dead-on, never in profile or turned toward the door.

1. **TWO WOMEN, NO MAN beside the crying one**: confirmed — only the crying woman (brown fur, rust dress — matches `@project_absence_char_visitor_b`) and her partner (cobalt coat, pearl necklace — matches `@project_absence_char_woman`) are present in that group; no third figure beside them at any checked frame.
2. **The man in maroon alone far off**: **not present in this clip, correctly** — the pasted prompt's own cast line reads "THE COMPLETE CAST OF THIS SHOT IS THREE PEOPLE AND NOT ONE MORE" and its negatives explicitly ban any man except the cleaner. No maroon-suited man appears anywhere in the render, which matches the prompt as authored (the task brief's WHAT section mentions him as scene context; the actual pasted/fired prompt text does not include him in this particular 12s beat).
3. **The crying small**: confirmed — visible tears from ~3s onward, undramatic, no shaking shoulders, no sound of sobbing, no hand-to-face/handkerchief business.
4. **Dupe working, never crossing to them**: confirmed at all four frames — stays at his cart on the far left, cloth in hand, never approaches the two women.
5. **Nobody speaks**: no mouth movement suggesting dialogue at any checked frame; consistent with the prompt's "NOBODY SPEAKS AT ALL" instruction. (Audio track exists per ffprobe but was not separately reviewed for dialogue — visual frames show no speaking.)

**Verdict: PASS.** No re-fire needed on this take.

## Filed to Drive

- Downloaded locally via direct CDN URL (curl), verified byte-for-byte: 10,870,868 bytes matching the CloudFront `content-length`.
- Uploaded via `scripts/gdrive-bridge/upload_fix1.py` (pre-approved script + pre-defined `All Scene/Fix-1` Drive folder for this film) as `S2H-Fix1.MP4`.
- Drive link: https://drive.google.com/file/d/1IJazQemN2TlKotjv6Y2PgUbhm5QoYeTM/view
- `logs.txt` line appended by the script (LOGGED).

## Anything odd

- Repeated CDP `Page.captureScreenshot` timeouts on two separate tabs mid-session (page/JS remained responsive throughout — confirmed via `document.title` reads). Resolved each time by closing the tab and opening a fresh one; never fired Generate while screenshot verification was unavailable.
- A genuine window-collapse bug reproduced twice: `window.innerWidth` read 1024 then later 129, with `resize_window` reporting success both times without changing anything. This is the documented HARD-rule trap ("A window can shrink on its own; resize_window can lie") — recovery (close tab → fresh tab → re-verify innerWidth) worked both times.
- The uploaded previz reference's `<video>` DOM node never reported `readyState > 0` in this session even after the asset was confirmed fully served via `fetch(HEAD)` — treated as a benign lazy-load quirk of the composer's own player, not a binding failure, since the reference thumbnail, chip count, and the final render's camera/blocking (which matches the previz) all confirm it bound correctly.
