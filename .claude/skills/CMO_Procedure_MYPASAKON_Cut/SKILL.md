---
name: CMO_Procedure_MYPASAKON_Cut
kind: procedure
description: 'PROCEDURE — Cut a MYPASAKON (@mypasakon) 9:16 TikTok episode combining the channel''s measured viral visual grammar (2-layer RVM cutout Hook, headroom pop-up headlines above the RICH beanie, focal zoomed screen viewports with top-right circular PiP) and the Black Liquidity V7.8 HyperFrames/GSAP motion engine (emerald slash wipes, 2-part split chips, animated UI callouts, bespoke vector motion infographics, 17 curated SFX, -24dB BGM, and pixel-locked TikTok CTA motion). Trigger on /CMO_Procedure_MYPASAKON_Cut, "ตัดต่อคลิป MYPASAKON", "ตัดสไตล์ไวรัล MYPASAKON", "MYPASAKON cut". Do NOT use for BLACK LIQUIDITY (@black_liquidity -> CMO_Procedure_BlackLiquidity_Cut).'
owner: CMO
audience: [cmo, cto, project_head, video_editor, developer]
created_by: agent
author: {role: project_head, date: "2026-11-25"}
improved_by:
  - {role: project_head, date: "2026-11-25", note: "Added HARD Desktop Smart-Zoom rule (1:1 Full-Screen Establish -> cubic_in_out True-Center zoom at x=540 with 20-30% surrounding UI context & source-locked focus spotlight) per Q-20261125-1324-fa7a"}
aka: [mypasakon-cut]
---

# MYPASAKON — Cutting a Viral Episode (`@mypasakon` Viral × `BL V7.8` Motion Engine)

Input: Gate-1 CEO-approved trimmed master audio (`MYPASAKON_<EP>_Trimmed_Clean.mp3` + `edit_decision_list.json`), `3 × 15s` (or frame-locked) avatar Lipsync clips (`lip_1..3.mp4`), and episode screen capture / B-roll · Output: Finished `1080×1920 @ 30fps` (`-14.0 LUFS`) MP4 + `4×2` iPhone TikTok Viewer UI Simulation QC Sheet · Tools: `tools/mypasakon_audio_trim.py`, `tools/footage_catalog.py`, `tools/bgm_bed.py`, and GSAP `3.14` / HyperFrames (`1080×1920`).

Every visual constant in this procedure is measured directly from `@mypasakon`'s top viral TikTok clips (`7499778762058370322` `228.7K` views, `7606637998528089365` `107.7K` views, `7608147598175718677` `84.6K` views, `7636687482821676308` `59.4K` views, `7647208931168734485` `45.4K` views) fused with the battle-tested `CMO_Procedure_BlackLiquidity_Cut` (V6.3–V7.8) motion grammar, adapted to `MYPASAKON`'s Emerald-Lime (`#00E676` / `#7CFF00`) + Gold (`#FFD54F`) palette.

## When to invoke / when NOT to

- **Invoke** whenever cutting, re-cutting, or reviewing a vertical `9:16` (`1080×1920`) episode for **`MYPASAKON` (`@mypasakon`)** once `gate1_audio` in `CMO_Workflow_MYPASAKON` has passed.
- **Do NOT invoke** for `BLACK LIQUIDITY` (`@black_liquidity`, which uses crimson `#D4282D`, raw `กู / มึง` `Achird` TTS, and top-right `#bug` — see `CMO_Procedure_BlackLiquidity_Cut`), client script drafting (`CMO_Procedure_ClientScript_Handoff`), or raw audio Dead-Air trimming before Gate 1 (`CMO_Workflow_MYPASAKON` Step 4).

## Channel-Specific Rules (`MYPASAKON` vs `BLACK LIQUIDITY`)

1. **HARD — Polite `ผม / เพื่อนๆ / นะครับ` Register Only (`Agents/Memory/feedback_mypasakon_on_camera_register.md`).**
   **Why hard:** brand identity — the CEO appears as himself (`กอล์ฟ พัสกร`); `กู / มึง` belongs strictly to `BLACK LIQUIDITY` and must never appear in `MYPASAKON` audio, captions, or cards.
2. **HARD — Zero Top-Right `/MY PASAKON` Watermark and Zero Date Stamp (`Q-20261109-0447-822a`, `CMO_Standard_MYPASAKON_NeonDNA` §1.3).**
   **Why hard:** CEO ruling — explicitly rejected on `MYPASAKON` (`"ไม่เอา 9 พ.ย. 69 และไม่เอา /MY PASAKON ข้างบนขวา"`). Do not copy BL's `#bug` watermark onto `MYPASAKON`.
3. **HARD — Never Trap the Host Inside Cramped Static Boxes (`CEO feedback 2026-11-25`, `Q-20261125-1144-8cf6`).**
   **Why hard:** retention & channel authenticity — across `@mypasakon`'s `108K–228K` viral clips, talking-head beats are **full-screen natural shots** (with bold headlines in the headroom above the `RICH` beanie) or **RVM background-removed cutouts** (`PeterL1n/RobustVideoMatting` `mobilenetv3` on MPS) composited over full-bleed charts/screens — never boxed into a 50/50 split or static cyber-HUD grid.
4. **HARD — Ultra-Minimal Copy (`2–5 words` per card/headline) & Zero Unicode Emoji (`CMO_Standard_MYPASAKON_NeonDNA` §1.2 + BL V7.0 §7).**
   **Why hard:** mobile comprehension & luxury look — replace all Unicode emojis (`🔥`, `⚠️`, `✅`) with clean Vector SVG icons (`stroke-width: 2.4–3.0`, `#00E676` / `#7CFF00` / `#FFD54F` / `#FF5252`).
5. **HARD — Desktop Screen Footage: Full-Screen Establish -> True-Center `cubic_in_out` Smart-Zoom with `20–30%` Surrounding Context & Strict `1:1` Uniform Aspect Ratio (`CEO feedback 2026-11-25`, `Q-20261125-1324-fa7a`).**
   **Why hard:** viewer orientation & readability — never squash a desktop window into a fixed non-uniform box or crop paragraph edges; always establish the full `1:1` desktop browser window first (`แสดงเต็มจอก่อน`), then smoothly zoom (`3u² - 2u³`) so the exact mouse cursor / spoken UI target lands **dead-center at `x = 540px, y = stage_cy`** while keeping `20–30%` surrounding UI visible (`เว้นพื้นที่ให้เห็นรอบข้างบ้าง`) and zero sliced words.

## Steps — Six Beat Archetypes & Exact Pixel Geometry (`1080×1920`)

1. **Extract RVM MPS Cutouts for Hook & Composite Avatar Beats.**
   - Run `PeterL1n/RobustVideoMatting` (`mobilenetv3` on Apple Silicon `mps`, `downsample_ratio=0.4` at `540×960` with soft `35×35` Gaussian 3D contact drop shadow `opacity=0.68`) on the Hook and Composite spans of `sync_lip1` / `sync_lip3`.
   - *Stop if* any avatar clip is not frame-locked (`0`-frame drift) to `MYPASAKON_<EP>_Trimmed_Clean.mp3` via `tools/mypasakon_audio_trim.py sync-lip` (demo) or `chunks` (production).

2. **Build the Base Plate Track (`1080×1920 @ 30fps`) Using `@mypasakon`'s 6 Measured Viral Beat Archetypes:**
   - **Archetype 1 · 2-Layer RVM Parallax Viral Hook (`0.00–4.80s`, `v2_108k` `2.4s` & `v5_45k` `1.8s`):**
     - **Layer 1 (Background):** Full-bleed (`0..1080, 0..1920`, zero black margins) dark-emerald trading chart (`1.00 -> 1.055×` parallax zoom + headroom/bottom vignette).
     - **Layer 2 (Foreground):** RVM-matted CEO cutout (`width = 920 -> 948px`, `cx = 540px`, `RICH` beanie crown at `y ≈ 610px`, 3D contact shadow).
     - **Layer 3 (GSAP):** Giant 2-line `Kanit 800` (`62px`, heavy black stroke) Hook Headline in headroom (`top: 255px`, `expo.out` wipe) + 3 floating tilted market chips (`XAU/USD`, `FED · USD`, `AI REALTIME` popping in with `back.out(1.8)` around `y = 575–745px`).
   - **Archetype 2 · Smooth `sine.out` RVM Avatar Shrink Over Live Screen (`BL §6d` Measured Motion):**
     - Swap the zoomed live web/news viewport (`y = 260..1020px`) behind the full CEO cutout, then tween scale & position over **`24 frames` (`0.80s`, `sine.out`)** down to chest-up bottom-left (`width = 610–620px`, `cx = 310–315px`, flush to bottom `y = 1920px`), pairing with an animated Neon-Lime `calloutBox` on the upper evidence and a 2-part Split Keyword Chip (`top: 965px`, right-aligned clear of the shoulder).
   - **Archetype 3 · Full-Screen Natural Talking-Head + Headroom Headline (`v1_228k` `8.6s/70.1s` & `v2_108k` `20.1s/29.0s`):**
     - Shift close-up selfie plates (`1080×1920` where beanie crown is `y ≈ 380px`) down by **`+148px`** (extending vertical background lines seamlessly at top + smooth top headroom vignette `0.32× -> 1.0×`) so the `RICH` beanie crown sits at `y ≈ 530px`.
     - Place bold `Kanit 800` (`62px`) 2-line headlines OR crisp white/emerald pop cards (`.mp-hr-card`, `back.out(1.7)`) in **`y = 255..485px`** — never over the speaker's moving mic hand (`y = 1400..1880px`) and never under TikTok's bottom caption (`y > 1550px`).
   - **Archetype 4 · Smart-Zoom Desktop Camera + Top-Right Circular Neon-Emerald PiP (`v5_45k_tv_ai` `35.4s` × `Q-20261125-1324-fa7a`):**
     - Strip macOS top bar, Dock, and sidebar PII (`extract_clean_desktop_window`, attaching a clean `46px` dark browser header `[ ● ● ●  domain ]`), and render over a **full-bleed blurred dark-emerald ambient backdrop** (`GaussianBlur * 0.27`, `0..1080, 0..1920`, zero black margins; convert white `TradingView` charts to dark mode via `255 - bgr` + HSV `+90` hue rotation).
     - **Phase 1 (`0.00–1.15s` Establish):** Render the entire desktop window edge-to-edge (`stage_w = 1040px`, strict uniform `scale_x == scale_y == 1040 / W_win`) so viewers see what the real computer screen looks like first.
     - **Phase 2 (`1.15–2.05s` True-Center Smart-Zoom):** Smoothly tween (`cubic_in_out`) `(cx, cy, view_w)` so the exact mouse click / spoken UI element (`(cx, cy) == (focus_cx, focus_cy)`) lands at **exact true center (`x = 540px, y = stage_cy`)**. Measure real content column pixel width first (e.g., `1,680px` column -> `view_w = 2,020–2,040px`) so `100%` of Thai/English text fits uncut with `20–30%` surrounding browser context (`~180px` side margins), paired with a `24%` peripheral spotlight dim (`76%` outer brightness, `100%` target), a source-locked Neon-Emerald double-keyline focus frame (`#00FF7C`), and an animated click ripple. Pre-verify all screen beats on a crosshair (`540, stage_cy`) preview sheet before full encode.
     - During live Lipsync screen narration (`sync_lip2`), shift `stage_y` to `425..1245px` and overlay a **`264×264px` Circular Neon-Emerald PiP** at `(cx=868, cy=282)` (`5px` `#00E676` ring, fed by `860×860` face+beanie crop `[x=110..970, y=340..1200]`).
   - **Archetype 5 · Bespoke `BL V7.8` Minimal GSAP Motion Infographics (`#080D0A` Radial Emerald Studio Canvas):**
     - Transition in with a **`-8°` Diagonal Neon-Emerald Slash Wipe (`fireSlashWipe(at)`)**.
     - Build **100% distinct episode-specific GSAP frames** per concept (e.g., `3-Step Numbered Roadmap` with `expo.out` slide, `Myth vs Truth + USD ⟷ XAU Inverse Scale`, `Dual AI vs TradingView Chart Match`, `Head-to-Head VS Cards`, `50% / 50% Animated Progress Split Bar`).
   - **Archetype 6 · Real Moving Chart Cutaways + Pixel-Locked TikTok Ending CTA Motion:**
     - Pull real moving `XAUUSD` M5/M15 candle cutaways via `tools/footage_catalog.py search --channel MYPASAKON` (`broker=NONE` unless matching the episode's sponsor) so pure voice stretches never stall.
     - In the closing `6–8s`, fire `ctaSave` (`955, 1538`) and `ctaFollow` (`955, 1122`) from `CMO_Procedure_TikTok_CTAMotion` recolored in `MYPASAKON` Emerald (`#00E676`), keeping `.bl-legal` standing at `top = 1668px` and spoken `.cap` cards at `cy = 1375px` (`left: 90px, right: 130px`).

3. **Mix Curated 17-Pack SFX + `-24.0 dB` Sidechain-Ducked BGM (`-14.0 LUFS`).**
   - Pre-roll align sparse, purposeful SFX from `Assets/BlackLiquidity/sfx-mass-pack/curated-48k/manifest.json` (`t_start = t_visual - peak_time_ms / 1000`, `CMO_Standard_EditorSFX`), mix `BL07` (`104 BPM Sniper-Execution`) or situation-matched track via `tools/bgm_bed.py --ceiling-db -24.0 --speech-duck-db -3.0 --fade-in 4.0 --fade-out 4.0`, and master to **`-14.0 LUFS` / `-1.5 dBTP`**.

4. **Verify via `verify-cut` + `4×2` iPhone TikTok Viewer UI Simulation Sheet.**
   - Run `tools/mypasakon_audio_trim.py verify-cut --video <final.mp4> --audio <trimmed.mp3>`.
   - Composite 8 spread frames (including Hook, Composite, Headroom, Screen+PiP, Infographic, Dual Chart, and Ending CTA) onto the real iPhone TikTok viewer screenshot (`scale = 933/1920`, `54.34px` side crop, right-rail icons blended on top) and inspect via `read_file` before raising `gate2_video` on `/run`.

## Verify

```bash
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/mypasakon_audio_trim.py verify-cut \
  --video <final.mp4> --audio <trimmed.mp3> --sheet <qc_sheet.jpg>
```
Done looks like: `verify-cut` prints `"ok": true` (`1080×1920`, `30.0 fps`, `-16.5..-11.5 LUFS`), and visual inspection of the `4×2` iPhone TikTok UI Simulation Sheet confirms zero face/beanie overlap, zero TikTok right-rail/caption collision, zero desktop Dock/Launchpad leaks, and bullseye CTA ring alignment.

## Field notes
- 2026-11-25 [WRONG] Static cyber-HUD boxes (`Style A` 50/50 split & bottom `y=1610` chest subtitles) rejected on `Q-20261125-1144-8cf6` (`"ยังไม่ใช่ Style Mypasakon ที่ฉันอยากได้นะ ลองหาคลิป Viral อื่นๆ มาตัดตาม ... อีกอย่างคือ Skill ของ Black Liquidity ทำไว้ดีมากๆ เอาใช้และปรับให้เข้ากับเรา"`); measured 5 real `@mypasakon` viral hits (`228.7K`, `107.7K`, `84.6K`, `59.4K`, `45.4K`) and fused headroom talking-head + RVM cutout composite + circular PiP with BL V7.8 GSAP/HyperFrames motion · evidence: Q-20261125-1144-8cf6 · status: promoted
- 2026-11-25 [WRONG] Fixed-box non-uniform desktop crops (`1960×1440` squashed into `964×760` with no full-screen establish, slicing Thai paragraph edges and leaving right-column targets off-center) rejected on `Q-20261125-1324-fa7a` (`"ส่วนอื่นๆ ดีหมดแล้ว ยกเว้นแต่ภาพ จอจริง จาก footage ที่มาจากในคอม ... แสดงเต็มจอ ให้คนได้เห็นว่าจอจริงเป็นยังไง และ ใช้การ zoom เข้าในจุดที่ mouse และ ฉันพูดถึง ... เว้นพื้นที่ให้เห็นรอบข้างบ้าง ... ให้มันเป็น center จริง"`); replaced with `smart_screen_camera` (`1:1` uniform Full-Screen Establish -> `cubic_in_out` True-Center zoom at `x=540` with measured column margins + source-locked spotlight frame) · evidence: Q-20261125-1324-fa7a · status: promoted
